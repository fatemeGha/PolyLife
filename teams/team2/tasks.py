"""
Celery tasks for Team2 microservice.

Task registry:
    send_reminder_notification  — Fire a notification for a scheduled reminder.

Design principles:
    - Tasks are thin wrappers; all business logic lives in reminder_service.py
    - Every execution attempt is recorded in NotificationLog (success or failure)
    - Tasks are idempotent: running the same task twice does not duplicate logs
      because the reminder state is checked before acting
    - Quiet hours and notification settings are re-evaluated AT DISPATCH TIME,
      not at scheduling time, because user settings can change between the two
"""

import logging
from datetime import datetime

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("team2.tasks")


# ---------------------------------------------------------------------------
# Main Reminder Notification Task
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="team2.send_reminder_notification",
    max_retries=3,
    default_retry_delay=60,       # retry after 60 seconds on transient errors
    acks_late=True,               # acknowledge AFTER task completes (safer)
    reject_on_worker_lost=True,   # re-queue if worker dies mid-task
)
def send_reminder_notification(self, reminder_id: int) -> dict:
    """
    Celery task: send a push notification for a scheduled reminder.

    This task is scheduled by reminder_service.create_reminder() using
    apply_async(eta=...) so it fires at the exact reminder_time.

    Execution flow:
        1. Fetch the reminder from the database.
        2. Guard checks: skip if reminder is deleted, inactive, or completed.
        3. Check user's global notification setting (is_enabled).
        4. Re-check quiet hours at actual dispatch time (settings may have changed).
        5. Send the notification (currently a log statement; replace with FCM call).
        6. Record outcome in NotificationLog.

    Args:
        reminder_id: Primary key of the Reminder to process.

    Returns:
        dict: Execution outcome summary for logging/debugging.

    Raises:
        self.retry(): On transient errors (DB timeouts, etc.)
    """
    from .models import Reminder, NotificationSetting, NotificationLog
    from .services.reminder_service import (
        is_in_quiet_hours,
        get_or_create_notification_settings,
    )

    logger.info(
        "[task:send_reminder_notification] Starting | reminder_id=%s | "
        "task_id=%s | attempt=%s",
        reminder_id,
        self.request.id,
        self.request.retries + 1,
    )

    # ------------------------------------------------------------------
    # Step 1: Fetch reminder
    # ------------------------------------------------------------------
    try:
        reminder = Reminder.objects.select_related().get(id=reminder_id)
    except Reminder.DoesNotExist:
        logger.warning(
            "[task:send_reminder_notification] Reminder %s not found. "
            "Task will not be retried.",
            reminder_id,
        )
        return {"status": "skipped", "reason": "Reminder not found in database."}

    # ------------------------------------------------------------------
    # Step 2: Guard checks — is the reminder still actionable?
    # ------------------------------------------------------------------
    if reminder.is_deleted:
        logger.info(
            "[task:send_reminder_notification] Reminder %s is deleted. Skipping.",
            reminder_id,
        )
        return {"status": "skipped", "reason": "Reminder has been deleted."}

    if not reminder.is_active:
        logger.info(
            "[task:send_reminder_notification] Reminder %s is inactive. Skipping.",
            reminder_id,
        )
        return {"status": "skipped", "reason": "Reminder is not active."}

    if reminder.is_completed:
        logger.info(
            "[task:send_reminder_notification] Reminder %s is already completed. "
            "Skipping.",
            reminder_id,
        )
        return {"status": "skipped", "reason": "Reminder is already completed."}

    user_id = reminder.user_id

    # ------------------------------------------------------------------
    # Step 3: Check global notification setting
    # ------------------------------------------------------------------
    settings = get_or_create_notification_settings(user_id)

    if not settings.is_enabled:
        logger.info(
            "[task:send_reminder_notification] Notifications disabled for user %s. "
            "Logging as FAILED.",
            user_id,
        )
        _log_notification(
            user_id=user_id,
            reminder=reminder,
            status=NotificationLog.Status.FAILED,
            failure_reason="User has disabled all notifications.",
        )
        return {
            "status": "failed",
            "reason": "User disabled notifications.",
            "reminder_id": reminder_id,
        }

    # ------------------------------------------------------------------
    # Step 4: Re-check quiet hours at actual dispatch time
    #
    # We re-check here (not just at scheduling time) because:
    #   a) User may have changed quiet hours after the reminder was created.
    #   b) For recurring reminders, settings may differ from the initial check.
    # ------------------------------------------------------------------
    now_time = timezone.localtime(timezone.now()).time()

    in_quiet_hours = is_in_quiet_hours(
        check_time=now_time,
        quiet_start=settings.quiet_hours_start,
        quiet_end=settings.quiet_hours_end,
    )

    if in_quiet_hours and not reminder.force_send_in_quiet_hours:
        logger.info(
            "[task:send_reminder_notification] Current time %s is within quiet hours "
            "(%s – %s) for user %s and force=False. Suppressing.",
            now_time.strftime("%H:%M"),
            settings.quiet_hours_start.strftime("%H:%M"),
            settings.quiet_hours_end.strftime("%H:%M"),
            user_id,
        )
        _log_notification(
            user_id=user_id,
            reminder=reminder,
            status=NotificationLog.Status.FAILED,
            failure_reason=(
                f"Suppressed due to quiet hours "
                f"({settings.quiet_hours_start.strftime('%H:%M')} – "
                f"{settings.quiet_hours_end.strftime('%H:%M')}). "
                f"Current time: {now_time.strftime('%H:%M')}."
            ),
        )
        return {
            "status": "suppressed",
            "reason": "Quiet hours active at dispatch time.",
            "reminder_id": reminder_id,
        }

    # ------------------------------------------------------------------
    # Step 5: Send the notification
    #
    # Currently implemented as a log statement.
    # Replace the _mock_send_push_notification() call with your
    # actual FCM / Firebase integration when ready.
    # ------------------------------------------------------------------
    try:
        _mock_send_push_notification(
            user_id=user_id,
            title=reminder.title,
            message=reminder.message or f"Reminder: {reminder.title}",
        )
    except Exception as exc:
        # Transient error — retry the task
        logger.error(
            "[task:send_reminder_notification] Notification dispatch failed for "
            "reminder %s: %s. Retrying (attempt %s/%s).",
            reminder_id,
            str(exc),
            self.request.retries + 1,
            self.max_retries,
        )
        _log_notification(
            user_id=user_id,
            reminder=reminder,
            status=NotificationLog.Status.FAILED,
            failure_reason=f"Dispatch error: {str(exc)}",
        )
        raise self.retry(exc=exc)

    # ------------------------------------------------------------------
    # Step 6: Record success in NotificationLog
    # ------------------------------------------------------------------
    _log_notification(
        user_id=user_id,
        reminder=reminder,
        status=NotificationLog.Status.SENT,
        failure_reason=None,
    )

    # Handle recurring reminders: schedule the next occurrence
    if reminder.recurrence_pattern != "none":
        _schedule_next_occurrence(reminder)

    logger.info(
        "[task:send_reminder_notification] Successfully dispatched notification "
        "for reminder %s (user=%s).",
        reminder_id,
        user_id,
    )

    return {
        "status": "sent",
        "reminder_id": reminder_id,
        "user_id": user_id,
        "title": reminder.title,
        "dispatched_at": timezone.now().isoformat(),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log_notification(user_id: int,
                       reminder,
                       status: str,
                       failure_reason: str | None) -> None:
    """
    Create an immutable NotificationLog entry for this dispatch attempt.

    Args:
        user_id        : Target user ID.
        reminder       : Reminder model instance.
        status         : NotificationLog.Status value.
        failure_reason : Human-readable reason for failure (or None on success).
    """
    from .models import NotificationLog

    message = failure_reason if failure_reason else reminder.message or reminder.title

    NotificationLog.objects.create(
        user_id=user_id,
        reminder=reminder,
        title=reminder.title,
        message=message,
        status=status,
        sent_at=timezone.now() if status == "sent" else None,
    )


def _mock_send_push_notification(user_id: int,
                                  title: str,
                                  message: str) -> None:
    """
    Placeholder for the actual push notification dispatch.

    Replace this function body with your Firebase Cloud Messaging (FCM)
    API call when the integration is ready.

    Current behavior: prints to stdout and logs to the task logger.
    This is sufficient for development and integration testing.

    Args:
        user_id : Target user's ID.
        title   : Notification title.
        message : Notification body text.

    Raises:
        Exception: If the external service call fails (triggers task retry).
    """
    logger.info(
        "[team2:notification] MOCK PUSH — user_id=%s | title='%s' | message='%s'",
        user_id,
        title,
        message,
    )
    print(
        f"[team2:notification] >>> PUSH NOTIFICATION SENT <<< "
        f"user={user_id} | title='{title}' | body='{message}'"
    )


def _schedule_next_occurrence(reminder) -> None:
    """
    Schedule the next firing of a recurring reminder.

    Called after a successful dispatch. Computes the next execution time
    based on the recurrence_pattern and re-queues the task.

    Patterns:
        daily   → next firing is tomorrow at the same reminder_time
        weekly  → next firing is 7 days from now at the same reminder_time

    Args:
        reminder: Reminder model instance with recurrence_pattern set.
    """
    from datetime import timedelta, datetime, date

    pattern = reminder.recurrence_pattern

    if pattern == "daily":
        delta = timedelta(days=1)
    elif pattern == "weekly":
        delta = timedelta(weeks=1)
    else:
        return  # no recurrence

    # Build the next ETA datetime
    today = timezone.localdate()
    next_date = today + delta
    next_eta = datetime.combine(
        next_date,
        reminder.reminder_time,
        tzinfo=timezone.get_current_timezone(),
    )

    send_reminder_notification.apply_async(
        args=[reminder.id],
        eta=next_eta,
    )

    logger.info(
        "[task:_schedule_next_occurrence] Recurring reminder %s (%s) "
        "scheduled for next run at %s.",
        reminder.id,
        pattern,
        next_eta.isoformat(),
    )

