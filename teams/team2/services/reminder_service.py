"""
Business logic for the Reminder & Notification domain.

Rules enforced here:
    - Reminder time is validated against the user's quiet hours window.
    - Quiet hours can span midnight (e.g., 22:00 → 08:00).
    - A reminder in quiet hours is rejected UNLESS force=True is passed.
    - Users can only access/modify their own reminders.
    - Deletion is always soft (is_deleted = True).
    - NotificationSetting is auto-created with defaults on first access.
    - NotificationLog entries are append-only (never modified after creation).
    - Completing a reminder sets is_completed=True and is_active=False.
"""

from datetime import datetime, time as time_type

from ..models import Reminder, NotificationSetting, NotificationLog


# ---------------------------------------------------------------------------
# Default quiet hours (used when creating settings for a new user)
# ---------------------------------------------------------------------------

DEFAULT_QUIET_START = time_type(22, 0)   # 22:00
DEFAULT_QUIET_END = time_type(8, 0)      # 08:00


# ---------------------------------------------------------------------------
# Quiet Hours Logic
# ---------------------------------------------------------------------------

def is_in_quiet_hours(check_time: time_type,
                       quiet_start: time_type,
                       quiet_end: time_type) -> bool:
    """
    Determine whether a given time falls within the quiet hours window.

    Handles both same-day windows (e.g., 09:00 – 17:00)
    and overnight windows (e.g., 22:00 – 08:00).

    Args:
        check_time  : The time to evaluate (e.g., reminder_time).
        quiet_start : Start of the quiet hours window.
        quiet_end   : End of the quiet hours window.

    Returns:
        bool: True if check_time is inside the quiet window, False otherwise.
    """
    if quiet_start <= quiet_end:
        # Same-day window: e.g., 09:00 – 17:00
        return quiet_start <= check_time <= quiet_end
    else:
        # Overnight window: e.g., 22:00 – 08:00
        return check_time >= quiet_start or check_time <= quiet_end


def parse_time_string(time_str: str) -> tuple[time_type | None, str | None]:
    """
    Parse a time string in HH:MM or HH:MM:SS format into a time object.

    Args:
        time_str: String representation of time.

    Returns:
        (time_object, None)     on success
        (None, error_message)   on failure
    """
    if not time_str:
        return None, "Time value is required."

    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(str(time_str), fmt).time()
            return parsed, None
        except ValueError:
            continue

    return None, f"Invalid time format '{time_str}'. Use HH:MM or HH:MM:SS."


# ---------------------------------------------------------------------------
# Notification Settings Helpers
# ---------------------------------------------------------------------------

def get_or_create_notification_settings(user_id: int) -> NotificationSetting:
    """
    Retrieve the user's notification settings, creating defaults if none exist.
    """
    settings, _ = NotificationSetting.objects.get_or_create(
        user_id=user_id,
        defaults={
            "is_enabled": True,
            "quiet_hours_start": DEFAULT_QUIET_START,
            "quiet_hours_end": DEFAULT_QUIET_END,
            "is_deleted": False,
        },
    )
    return settings


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def serialize_reminder(reminder: Reminder) -> dict:
    """
    Convert a Reminder model instance to a JSON-serializable dict.
    """
    return {
        "id": reminder.id,
        "user_id": reminder.user_id,
        "title": reminder.title,
        "message": reminder.message,
        "reminder_time": reminder.reminder_time.strftime("%H:%M"),
        "recurrence_pattern": reminder.recurrence_pattern,
        "is_active": reminder.is_active,
        "is_completed": reminder.is_completed,
        "force_send_in_quiet_hours": reminder.force_send_in_quiet_hours,
        "created_at": reminder.created_at.isoformat(),
        "updated_at": reminder.updated_at.isoformat(),
    }


def serialize_notification_setting(settings: NotificationSetting) -> dict:
    """
    Convert a NotificationSetting instance to a JSON-serializable dict.
    """
    return {
        "user_id": settings.user_id,
        "is_enabled": settings.is_enabled,
        "quiet_hours_start": settings.quiet_hours_start.strftime("%H:%M"),
        "quiet_hours_end": settings.quiet_hours_end.strftime("%H:%M"),
        "updated_at": settings.updated_at.isoformat(),
    }


def serialize_notification_log(log: NotificationLog) -> dict:
    """
    Convert a NotificationLog instance to a JSON-serializable dict.
    """
    return {
        "id": log.id,
        "reminder_id": log.reminder_id,
        "title": log.title,
        "message": log.message,
        "status": log.status,
        "sent_at": log.sent_at.isoformat() if log.sent_at else None,
        "created_at": log.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Reminder Validation
# ---------------------------------------------------------------------------

def validate_reminder_data(title: str,
                            reminder_time_str: str,
                            recurrence_pattern: str = None) -> dict:
    """
    Validate the fields of a reminder before creating or updating.
    """
    errors = {}

    if not title or not str(title).strip():
        errors["title"] = "Title is required and cannot be blank."
    elif len(str(title)) > 255:
        errors["title"] = "Title cannot exceed 255 characters."

    if reminder_time_str is None:
        errors["reminder_time"] = "Reminder time is required."
    else:
        _, time_error = parse_time_string(str(reminder_time_str))
        if time_error:
            errors["reminder_time"] = time_error

    valid_patterns = [p.value for p in Reminder.RecurrencePattern]
    if recurrence_pattern is not None and recurrence_pattern not in valid_patterns:
        errors["recurrence_pattern"] = (
            f"Invalid recurrence pattern '{recurrence_pattern}'. "
            f"Allowed values: {', '.join(valid_patterns)}."
        )

    return errors


def check_quiet_hours_conflict(reminder_time: time_type,
                                user_id: int) -> tuple[bool, dict | None]:
    """
    Check whether the reminder time conflicts with the user's quiet hours.
    """
    settings = get_or_create_notification_settings(user_id)

    if not settings.is_enabled:
        return False, None

    conflict = is_in_quiet_hours(
        check_time=reminder_time,
        quiet_start=settings.quiet_hours_start,
        quiet_end=settings.quiet_hours_end,
    )

    if conflict:
        warning = {
            "quiet_hours_start": settings.quiet_hours_start.strftime("%H:%M"),
            "quiet_hours_end": settings.quiet_hours_end.strftime("%H:%M"),
            "reminder_time": reminder_time.strftime("%H:%M"),
            "hint": (
                "The reminder time falls within your quiet hours. "
                "To schedule it anyway, resend the request with "
                "'force_send_in_quiet_hours': true."
            ),
        }
        return True, warning

    return False, None


# ---------------------------------------------------------------------------
# Reminder CRUD Services (Updated with Celery Scheduling)
# ---------------------------------------------------------------------------

def create_reminder(user_id: int,
                    title: str,
                    reminder_time_str: str,
                    recurrence_pattern: str = "none",
                    message: str = "",
                    force: bool = False) -> tuple[bool, dict, str]:
    """
    Create and persist a new reminder, then schedule the Celery task.
    """
    from datetime import datetime, date
    import logging

    logger = logging.getLogger("team2.services.reminder")

    # Step 1: field validation
    errors = validate_reminder_data(title, reminder_time_str, recurrence_pattern)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    # Step 2: parse time
    reminder_time, _ = parse_time_string(str(reminder_time_str))

    # Step 3: quiet hours check
    if not force:
        conflict, warning = check_quiet_hours_conflict(reminder_time, user_id)
        if conflict:
            return (
                False,
                {"quiet_hours_conflict": warning},
                "Reminder time falls within your quiet hours. "
                "Set 'force_send_in_quiet_hours' to true to override.",
            )

    # Step 4: persist
    reminder = Reminder.objects.create(
        user_id=user_id,
        title=str(title).strip(),
        message=message or "",
        reminder_time=reminder_time,
        recurrence_pattern=recurrence_pattern or Reminder.RecurrencePattern.NONE,
        force_send_in_quiet_hours=force,
    )

    # Step 5: schedule Celery task
    _schedule_reminder_task(reminder)

    logger.info(
        "[reminder_service] Reminder %s created for user %s at %s (%s).",
        reminder.id,
        user_id,
        reminder_time.strftime("%H:%M"),
        recurrence_pattern,
    )

    return True, serialize_reminder(reminder), "Reminder created successfully."


def _schedule_reminder_task(reminder) -> None:
    """
    Compute the next ETA for a reminder and schedule the Celery task.
    """
    from datetime import datetime, date, timedelta
    from django.utils import timezone
    import logging

    logger = logging.getLogger("team2.services.reminder")

    # Import here to avoid circular imports at module load time
    from ..tasks import send_reminder_notification

    now = timezone.localtime(timezone.now())
    today = now.date()

    # Build the candidate ETA for today
    eta_today = datetime.combine(
        today,
        reminder.reminder_time,
        tzinfo=timezone.get_current_timezone(),
    )

    if eta_today > now:
        # Reminder time is still in the future today — schedule for today
        eta = eta_today
    else:
        # Reminder time has already passed today
        if reminder.recurrence_pattern == "none":
            # One-time reminder that's already past — skip scheduling
            logger.warning(
                "[reminder_service] One-time reminder %s has a past time (%s). "
                "Task will NOT be scheduled.",
                reminder.id,
                reminder.reminder_time.strftime("%H:%M"),
            )
            return
        elif reminder.recurrence_pattern == "daily":
            eta = eta_today + timedelta(days=1)
        elif reminder.recurrence_pattern == "weekly":
            eta = eta_today + timedelta(weeks=1)
        else:
            eta = eta_today + timedelta(days=1)

    # Queue the Celery task with the computed ETA
    send_reminder_notification.apply_async(
        args=[reminder.id],
        eta=eta,
    )

    logger.info(
        "[reminder_service] Task scheduled for reminder %s (user=%s) at %s.",
        reminder.id,
        reminder.user_id,
        eta.isoformat(),
    )


def reschedule_reminder_task(reminder) -> None:
    """
    Cancel the implicit old schedule and create a new one.
    """
    _schedule_reminder_task(reminder)


def get_user_reminders(user_id: int,
                        include_completed: bool = False) -> list[dict]:
    """
    Retrieve all active (non-deleted) reminders for a user.
    """
    queryset = Reminder.objects.filter(
        user_id=user_id,
        is_deleted=False,
    )

    if not include_completed:
        queryset = queryset.filter(is_completed=False)

    queryset = queryset.order_by("reminder_time")

    return [serialize_reminder(r) for r in queryset]


def update_reminder(user_id: int,
                    reminder_id: int,
                    title: str = None,
                    reminder_time_str: str = None,
                    recurrence_pattern: str = None,
                    message: str = None,
                    is_active: bool = None,
                    force: bool = False) -> tuple[bool, dict, str]:
    """
    Update an existing reminder owned by the user.
    """
    try:
        reminder = Reminder.objects.get(
            id=reminder_id,
            user_id=user_id,
            is_deleted=False,
        )
    except Reminder.DoesNotExist:
        return (
            False,
            {},
            "Reminder not found or you do not have permission to modify it.",
        )

    new_title = str(title).strip() if title is not None else reminder.title
    new_time_str = reminder_time_str if reminder_time_str is not None \
        else reminder.reminder_time.strftime("%H:%M")
    new_pattern = recurrence_pattern if recurrence_pattern is not None \
        else reminder.recurrence_pattern

    errors = validate_reminder_data(new_title, new_time_str, new_pattern)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    new_time, _ = parse_time_string(new_time_str)

    time_changed = (new_time != reminder.reminder_time)
    if time_changed and not force:
        conflict, warning = check_quiet_hours_conflict(new_time, user_id)
        if conflict:
            return (
                False,
                {"quiet_hours_conflict": warning},
                "Updated reminder time falls within your quiet hours. "
                "Set 'force_send_in_quiet_hours' to true to override.",
            )

    reminder.title = new_title
    reminder.reminder_time = new_time
    reminder.recurrence_pattern = new_pattern

    if message is not None:
        reminder.message = message
    if is_active is not None:
        reminder.is_active = is_active
    if force:
        reminder.force_send_in_quiet_hours = True

    reminder.save()

    # Reschedule the Celery task if the time changed
    if time_changed:
        reschedule_reminder_task(reminder)

    return True, serialize_reminder(reminder), "Reminder updated successfully."


def soft_delete_reminder(user_id: int,
                          reminder_id: int) -> tuple[bool, dict, str]:
    """
    Soft-delete a reminder.
    """
    try:
        reminder = Reminder.objects.get(
            id=reminder_id,
            user_id=user_id,
            is_deleted=False,
        )
    except Reminder.DoesNotExist:
        return (
            False,
            {},
            "Reminder not found or you do not have permission to delete it.",
        )

    reminder.is_deleted = True
    reminder.is_active = False
    reminder.save(update_fields=["is_deleted", "is_active", "updated_at"])

    return True, {"id": reminder_id}, "Reminder deleted successfully."


def complete_reminder(user_id: int,
                      reminder_id: int) -> tuple[bool, dict, str]:
    """
    Mark a reminder as completed.
    """
    try:
        reminder = Reminder.objects.get(
            id=reminder_id,
            user_id=user_id,
            is_deleted=False,
        )
    except Reminder.DoesNotExist:
        return (
            False,
            {},
            "Reminder not found or you do not have permission to complete it.",
        )

    if reminder.is_completed:
        return (
            False,
            {"is_completed": "This reminder has already been marked as completed."},
            "Reminder is already completed.",
        )

    reminder.is_completed = True
    reminder.is_active = False
    reminder.save(update_fields=["is_completed", "is_active", "updated_at"])

    from django.utils import timezone
    NotificationLog.objects.create(
        user_id=user_id,
        reminder=reminder,
        title=reminder.title,
        message=f"Reminder '{reminder.title}' was marked as completed by the user.",
        status=NotificationLog.Status.SENT,
        sent_at=timezone.now(),
    )

    return True, serialize_reminder(reminder), "Reminder marked as completed."


# ---------------------------------------------------------------------------
# Notification Settings Services
# ---------------------------------------------------------------------------

def get_notification_settings(user_id: int) -> tuple[bool, dict, str]:
    """
    Retrieve the user's notification settings.
    """
    settings = get_or_create_notification_settings(user_id)
    return True, serialize_notification_setting(settings), \
        "Notification settings retrieved successfully."


def update_notification_settings(user_id: int,
                                  is_enabled: bool = None,
                                  quiet_hours_start_str: str = None,
                                  quiet_hours_end_str: str = None) -> tuple[bool, dict, str]:
    """
    Update the user's notification settings.
    """
    errors = {}

    new_quiet_start = None
    new_quiet_end = None

    if quiet_hours_start_str is not None:
        new_quiet_start, err = parse_time_string(quiet_hours_start_str)
        if err:
            errors["quiet_hours_start"] = err

    if quiet_hours_end_str is not None:
        new_quiet_end, err = parse_time_string(quiet_hours_end_str)
        if err:
            errors["quiet_hours_end"] = err

    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    settings = get_or_create_notification_settings(user_id)

    if is_enabled is not None:
        settings.is_enabled = bool(is_enabled)
    if new_quiet_start is not None:
        settings.quiet_hours_start = new_quiet_start
    if new_quiet_end is not None:
        settings.quiet_hours_end = new_quiet_end

    settings.save()

    return True, serialize_notification_setting(settings), \
        "Notification settings updated successfully."


# ---------------------------------------------------------------------------
# Notification Log Services
# ---------------------------------------------------------------------------

def get_notification_history(user_id: int,
                              status_filter: str = None) -> tuple[bool, list, str]:
    """
    Retrieve the user's notification history.
    """
    valid_statuses = [s.value for s in NotificationLog.Status]
    if status_filter and status_filter not in valid_statuses:
        return (
            False,
            [],
            f"Invalid status filter '{status_filter}'. "
            f"Allowed values: {', '.join(valid_statuses)}.",
        )

    queryset = NotificationLog.objects.filter(
        user_id=user_id,
        is_deleted=False,
    ).select_related("reminder").order_by("-created_at")

    if status_filter:
        queryset = queryset.filter(status=status_filter)

    logs = [serialize_notification_log(log) for log in queryset]

    return True, logs, "Notification history retrieved successfully."

