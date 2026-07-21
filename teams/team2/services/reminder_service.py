"""
Business logic for the Reminder & Notification domain.

Rules enforced here:
    - Reminder time is validated against the user's quiet hours window.
    - Quiet hours can span midnight (e.g., 22:00 -> 08:00).
    - A reminder in quiet hours is rejected UNLESS force=True is passed.
    - Users can only access/modify their own reminders.
    - Deletion is always soft (is_deleted = True).
    - NotificationSettings is auto-created with defaults on first access.
    - Notification entries are append-only (never modified after creation).
    - Completing a reminder sets is_completed=True and is_active=False.
"""

from datetime import datetime, date, timedelta, time as time_type
from django.utils import timezone
from ..models import Reminder, NotificationSettings, Notification


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
    """
    if quiet_start <= quiet_end:
        return quiet_start <= check_time <= quiet_end
    else:
        return check_time >= quiet_start or check_time <= quiet_end


def parse_time_string(time_str: str) -> tuple[time_type | None, str | None]:
    """
    Parse a time string in HH:MM or HH:MM:SS format into a time object.
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
# Notification Settings Helpers (Updated to MongoEngine native classmethod)
# ---------------------------------------------------------------------------

def get_or_create_notification_settings(user_id: int) -> NotificationSettings:
    """
    Retrieve the user's notification settings, creating defaults if none exist.
    """
    return NotificationSettings.get_or_create_default(str(user_id))


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------

def serialize_reminder(reminder: Reminder) -> dict:
    """
    Convert a Reminder model instance to a JSON-serializable dict.
    """
    return {
        "id": str(reminder.id),
        "user_id": reminder.user_id,
        "title": reminder.title,
        "message": reminder.message,
        "reminder_time": reminder.scheduled_time.strftime("%H:%M"),
        "recurrence_pattern": reminder.repeat_type, # Map repeat_type field to recurrence_pattern in API
        "is_active": reminder.status == "scheduled", # active maps to scheduled status
        "is_completed": reminder.status == "completed",
        "force_send_in_quiet_hours": reminder.is_deleted, # Temporary placeholder
        "created_at": reminder.created_at.isoformat(),
    }


def serialize_notification_setting(settings: NotificationSettings) -> dict:
    """
    Convert a NotificationSettings instance to a JSON-serializable dict.
    """
    return {
        "user_id": settings.user_id,
        "is_enabled": settings.push_enabled, # Map push_enabled to is_enabled key
        "quiet_hours_start": settings.dnd_start, # Map dnd_start to quiet_hours_start
        "quiet_hours_end": settings.dnd_end, # Map dnd_end to quiet_hours_end
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else settings.created_at.isoformat(),
    }


def serialize_notification_log(log: Notification) -> dict:
    """
    Convert a Notification instance to a JSON-serializable dict.
    """
    return {
        "id": str(log.id),
        "reminder_id": str(log.reminder_id) if log.reminder_id else None,
        "title": log.title,
        "message": log.content, # Map 'content' on model to 'message' in API response
        "status": log.delivery_status, # Map 'delivery_status' on model to 'status' in API response
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

    if recurrence_pattern is not None and recurrence_pattern not in Reminder.REPEAT_CHOICES:
        errors["recurrence_pattern"] = (
            f"Invalid recurrence pattern '{recurrence_pattern}'. "
            f"Allowed values: {', '.join(Reminder.REPEAT_CHOICES)}."
        )

    return errors


def check_quiet_hours_conflict(reminder_time: time_type,
                                user_id: int) -> tuple[bool, dict | None]:
    """
    Check whether the reminder time conflicts with the user's quiet hours.
    """
    settings = get_or_create_notification_settings(user_id)

    # DND is honored if push_enabled is true
    if not settings.push_enabled:
        return False, None

    # Parse quiet hours strings to time objects
    q_start, _ = parse_time_string(settings.dnd_start)
    q_end, _ = parse_time_string(settings.dnd_end)

    conflict = is_in_quiet_hours(
        check_time=reminder_time,
        quiet_start=q_start,
        quiet_end=q_end,
    )

    if conflict:
        warning = {
            "quiet_hours_start": settings.dnd_start,
            "quiet_hours_end": settings.dnd_end,
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
    errors = validate_reminder_data(title, reminder_time_str, recurrence_pattern)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    reminder_time, _ = parse_time_string(str(reminder_time_str))

    if not force:
        conflict, warning = check_quiet_hours_conflict(reminder_time, user_id)
        if conflict:
            return (
                False,
                {"quiet_hours_conflict": warning},
                "Reminder time falls within your quiet hours. "
                "Set 'force_send_in_quiet_hours' to true to override.",
            )

    # Combine today's date with the time to create a DateTimeField expected by MongoEngine
    now = timezone.localtime(timezone.now())
    scheduled_datetime = datetime.combine(now.date(), reminder_time, tzinfo=timezone.get_current_timezone())

    reminder = Reminder.objects.create(
        user_id=str(user_id),
        title=str(title).strip(),
        message=message or "",
        scheduled_time=scheduled_datetime,
        repeat_type=recurrence_pattern or "none",
        status="created",
    )

    # Load process_due_reminder as send_reminder_notification to match Celery task naming
    from ..tasks import process_due_reminder as send_reminder_notification
    send_reminder_notification.apply_async(
        args=[str(reminder.id)],
        eta=scheduled_datetime,
    )

    return True, serialize_reminder(reminder), "Reminder created successfully."


def get_user_reminders(user_id: int,
                        include_completed: bool = False) -> list[dict]:
    """
    Retrieve all active (non-deleted) reminders for a user.
    """
    queryset = Reminder.objects.filter(
        user_id=str(user_id),
        is_deleted=False,
    )

    if not include_completed:
        queryset = queryset.filter(status__ne="completed")

    queryset = queryset.order_by("scheduled_time")

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
            reminder_id=str(reminder_id), # Query by key 'reminder_id'
            user_id=str(user_id),
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
        else reminder.scheduled_time.strftime("%H:%M")
    new_pattern = recurrence_pattern if recurrence_pattern is not None \
        else reminder.repeat_type

    errors = validate_reminder_data(new_title, new_time_str, new_pattern)
    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    new_time, _ = parse_time_string(new_time_str)

    time_changed = (new_time != reminder.scheduled_time.time())
    if time_changed and not force:
        conflict, warning = check_quiet_hours_conflict(new_time, user_id)
        if conflict:
            return (
                False,
                {"quiet_hours_conflict": warning},
                "Updated reminder time falls within your quiet hours. "
                "Set 'force_send_in_quiet_hours' to true to override.",
            )

    now = timezone.localtime(timezone.now())
    scheduled_datetime = datetime.combine(now.date(), new_time, tzinfo=timezone.get_current_timezone())

    reminder.title = new_title
    reminder.scheduled_time = scheduled_datetime
    reminder.repeat_type = new_pattern

    if message is not None:
        reminder.message = message
    if is_active is not None:
        reminder.status = "scheduled" if is_active else "created"

    reminder.save()

    if time_changed:
        from ..tasks import process_due_reminder as send_reminder_notification
        send_reminder_notification.apply_async(
            args=[str(reminder.id)],
            eta=scheduled_datetime,
        )

    return True, serialize_reminder(reminder), "Reminder updated successfully."


def soft_delete_reminder(user_id: int,
                          reminder_id: int) -> tuple[bool, dict, str]:
    """
    Soft-delete a reminder.
    """
    try:
        reminder = Reminder.objects.get(
            reminder_id=str(reminder_id),
            user_id=str(user_id),
            is_deleted=False,
        )
    except Reminder.DoesNotExist:
        return (
            False,
            {},
            "Reminder not found or you do not have permission to delete it.",
        )

    reminder.is_deleted = True
    reminder.status = "expired"
    reminder.save()

    return True, {"id": str(reminder_id)}, "Reminder deleted successfully."


def complete_reminder(user_id: int,
                      reminder_id: int) -> tuple[bool, dict, str]:
    """
    Mark a reminder as completed.
    """
    try:
        reminder = Reminder.objects.get(
            reminder_id=str(reminder_id),
            user_id=str(user_id),
            is_deleted=False,
        )
    except Reminder.DoesNotExist:
        return (
            False,
            {},
            "Reminder not found or you do not have permission to complete it.",
        )

    if reminder.status == "completed":
        return (
            False,
            {"is_completed": "This reminder has already been marked as completed."},
            "Reminder is already completed.",
        )

    reminder.status = "completed"
    reminder.save()

    # Log into Notification collection using correct MongoEngine fields
    Notification.objects.create(
        user_id=str(user_id),
        reminder_id=str(reminder.id),
        type="reminder", # Pass the required field
        title=reminder.title,
        content=f"Reminder '{reminder.title}' was marked as completed.", # Map message to content
        delivery_status="sent", # Map status to delivery_status
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

    if quiet_hours_start_str is not None:
        _, err = parse_time_string(quiet_hours_start_str)
        if err:
            errors["quiet_hours_start"] = err

    if quiet_hours_end_str is not None:
        _, err = parse_time_string(quiet_hours_end_str)
        if err:
            errors["quiet_hours_end"] = err

    if errors:
        return False, errors, "Validation failed. Please correct the errors and try again."

    settings = get_or_create_notification_settings(user_id)

    if is_enabled is not None:
        settings.push_enabled = bool(is_enabled)
    if quiet_hours_start_str is not None:
        settings.dnd_start = quiet_hours_start_str
    if quiet_hours_end_str is not None:
        settings.dnd_end = quiet_hours_end_str

    settings.save()

    return True, serialize_notification_setting(settings), \
        "Notification settings updated successfully."


# ---------------------------------------------------------------------------
# Notification Log Services (Updated for MongoEngine fields)
# ---------------------------------------------------------------------------

def get_notification_history(user_id: int,
                              status_filter: str = None) -> tuple[bool, list, str]:
    """
    Retrieve the user's notification history.
    """
    if status_filter and status_filter not in ["pending", "sent", "failed"]:
        return (
            False,
            [],
            f"Invalid status filter '{status_filter}'. Allowed values: pending, sent, failed.",
        )

    queryset = Notification.objects.filter(
        user_id=str(user_id),
        is_deleted=False,
    ).order_by("-created_at")

    if status_filter:
        queryset = queryset.filter(delivery_status=status_filter) # Use correct MongoEngine field

    logs = [serialize_notification_log(log) for log in queryset]

    return True, logs, "Notification history retrieved successfully."
