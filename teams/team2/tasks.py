"""
Celery tasks for the Reminder & Notification microservice.

This module is intentionally thin: every task here just calls into
services.py, which holds the actual business logic. Keeping tasks.py
thin means the same logic can be tested directly (see test_services.py)
without needing a running Celery worker or broker.
"""

from celery import shared_task

from . import services


@shared_task(name="team7.process_due_reminder", bind=True, max_retries=3)
def process_due_reminder(self, reminder_id: str):
    """
    Fired by Reminder.schedule() with an ETA equal to the reminder's
    scheduled_time. When it runs, it hands off to
    services.process_due_reminder(), which builds the Notification,
    sends it, and re-schedules the next occurrence for repeating
    reminders.

    UC12 NFR: delivery must happen within ~5 seconds of the scheduled
    time. Celery's ETA mechanism (set in Reminder.schedule()) is what
    guarantees the task fires close to that moment; this function itself
    does no additional waiting.

    Retries up to 3 times with a short backoff if something transient
    fails (e.g. a momentary DB hiccup), instead of silently dropping
    the reminder.
    """
    try:
        services.process_due_reminder(reminder_id)
    except Exception as exc:  # noqa: BLE001 - retry on any transient failure
        raise self.retry(exc=exc, countdown=5)
