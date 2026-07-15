"""
MODEL LAYER (continued)
Business logic that spans multiple collections or talks to external
systems (Celery, Redis, Firebase). Controllers call these functions;
these functions call models.py, never the other way around.
"""

import os
import json
import logging
from datetime import datetime, timedelta

from .models import (
    PhysicalRecord,
    Goal,
    WorkoutSession,
    PersonalBest,
    Reminder,
    NotificationSettings,
    Notification,
    DeviceToken,
    EventSubscription,
)

logger = logging.getLogger("team7")


# ============================================================
# Progress Tracking services
# ============================================================

def register_physical_data(user_id: str, weight: float, height: float,
                            body_fat_percent: float = None, muscle_mass: float = None):
    """
    UC01 main flow: validate input, create a PhysicalRecord, compute BMI,
    save it, and return the saved record.
    Raises ValueError on invalid input (caught by the controller, which
    turns it into a validation-error response - UC01 exception flow).
    """
    if weight is None or weight <= 0:
        raise ValueError("weight must be a positive number")
    if height is None or height <= 0:
        raise ValueError("height must be a positive number")
    if body_fat_percent is not None and not (0 <= body_fat_percent <= 100):
        raise ValueError("body_fat_percent must be between 0 and 100")

    record = PhysicalRecord(
        user_id=user_id,
        weight=weight,
        height=height,
        body_fat_percent=body_fat_percent,
        muscle_mass=muscle_mass,
    )
    record.calculate_bmi()  # sets record.bmi, does not save by itself
    record.save()

    # Invalidate any cached chart data for this user so the next chart
    # request picks up the freshly-saved record instead of stale cache.
    _invalidate_chart_cache(user_id)

    return record


def edit_physical_data(record_id: str, **fields):
    """
    UC02: update an existing PhysicalRecord with the given fields
    (any subset of weight / height / body_fat_percent / muscle_mass),
    recompute BMI, and save. Raises PhysicalRecord.DoesNotExist if the
    record_id is invalid or already soft-deleted.
    """
    record = PhysicalRecord.objects.get(record_id=record_id, is_deleted=False)

    for field_name, value in fields.items():
        if value is not None and hasattr(record, field_name):
            setattr(record, field_name, value)

    record.calculate_bmi()
    record.updated_at = datetime.utcnow()
    record.save()

    _invalidate_chart_cache(record.user_id)
    return record


def delete_physical_data(record_id: str):
    """UC02: soft-delete a PhysicalRecord (is_deleted = True, keep the row)."""
    record = PhysicalRecord.objects.get(record_id=record_id, is_deleted=False)
    record.is_deleted = True
    record.updated_at = datetime.utcnow()
    record.save()

    _invalidate_chart_cache(record.user_id)
    return record


def get_progress_chart_data(user_id: str, period: str) -> dict:
    """
    UC03: build the time series needed to render progress charts for the
    given period ('week' | 'month' | 'year'). Uses a Redis cache when
    available, per the NFR that charts must render in under ~2 seconds.
    Falls back transparently to a direct DB query if Redis isn't reachable
    (e.g. during local dev before Redis is wired up).
    """
    cache_key = f"chart:{user_id}:{period}"
    cached = _redis_get(cache_key)
    if cached is not None:
        return json.loads(cached)

    period_days = {"week": 7, "month": 30, "year": 365}.get(period, 30)
    since = datetime.utcnow() - timedelta(days=period_days)

    records = (
        PhysicalRecord.objects(
            user_id=user_id,
            is_deleted=False,
            created_at__gte=since,
        )
        .order_by("created_at")
    )

    goal = Goal.objects(user_id=user_id, is_deleted=False).first()

    series = []
    for record in records:
        point = {
            "date": record.created_at.isoformat(),
            "weight": record.weight,
            "bmi": record.bmi,
            "body_fat_percent": record.body_fat_percent,
        }
        if goal:
            point["goal_comparison"] = record.compare_with_goal(goal)
        series.append(point)

    result = {"period": period, "points": series}

    # Cache for 5 minutes - short enough that new data shows up quickly,
    # long enough to absorb repeated chart requests during one session.
    _redis_set(cache_key, json.dumps(result), ttl_seconds=300)

    return result


def set_user_goal(user_id: str, target_weight: float = None, target_body_fat: float = None):
    """UC04: create or update the user's single Goal document."""
    goal = Goal.objects(user_id=user_id, is_deleted=False).first()
    if goal is None:
        goal = Goal(user_id=user_id)

    if target_weight is not None:
        goal.target_weight = target_weight
    if target_body_fat is not None:
        goal.target_body_fat = target_body_fat

    goal.updated_at = datetime.utcnow()
    goal.save()
    return goal


def get_mentor_report(trainer_id: str, athlete_id: str) -> dict:
    """
    UC09: verify trainer_id has access to athlete_id, then build an
    aggregated progress report for the trainer's dashboard.

    NOTE: trainer-athlete assignment is managed by the Core service
    (user roles/relationships), not by this microservice's own database.
    _is_trainer_authorized() is a placeholder that should eventually call
    Core's API to confirm the relationship - for now it always allows
    the request, since the mentoring assignment model isn't defined yet.
    """
    if not _is_trainer_authorized(trainer_id, athlete_id):
        raise PermissionError("trainer is not authorized to view this athlete's report")

    chart_data = get_progress_chart_data(athlete_id, period="month")
    personal_bests = PersonalBest.objects(user_id=athlete_id, is_deleted=False)

    return {
        "athlete_id": athlete_id,
        "chart_data": chart_data,
        "personal_bests": [
            {
                "exercise_name": pb.exercise_name,
                "max_weight": pb.max_weight,
                "achieved_date": pb.achieved_date.isoformat(),
            }
            for pb in personal_bests
        ],
    }


def detect_and_register_new_record(user_id: str, exercise_name: str,
                                    weight_lifted: float, session_id: str):
    """
    UC11 main flow: after a WorkoutSession is saved, check whether
    weight_lifted beats the user's current PersonalBest. If so, update
    (or create) the PersonalBest and fire a congratulations Notification.
    Returns the updated/created PersonalBest, or None if no record was broken.
    """
    if not PersonalBest.is_new_record(user_id, exercise_name, weight_lifted):
        return None

    existing = PersonalBest.objects(
        user_id=user_id, exercise_name=exercise_name, is_deleted=False
    ).first()

    if existing is None:
        personal_best = PersonalBest.create_first_record(
            user_id, exercise_name, weight_lifted, session_id
        )
    else:
        personal_best = existing.update_record(weight_lifted, session_id)

    # UC11 step 5-6: build + send the congratulations notification.
    # Kept under 5 seconds per the NFR by doing this synchronously right
    # after the DB write, without waiting on any slow external call here
    # (send_push_notification itself is expected to be fire-and-forget).
    notification = Notification(
        user_id=user_id,
        type="record",
        content=f"تبریک! رکورد جدید در {exercise_name}: {weight_lifted} کیلوگرم",
    )
    notification.save()
    notification.send()

    return personal_best


# ============================================================
# Reminder & Notification services
# ============================================================

def check_dnd_window(scheduled_time: datetime, settings: NotificationSettings) -> bool:
    """
    UC05 subflow: True if scheduled_time falls inside the user's DND
    window (settings.dnd_start -> settings.dnd_end). This mirrors
    Reminder.is_in_dnd_window() but works on a raw datetime, for use
    before a Reminder document even exists yet.
    """
    # Build a throwaway Reminder just to reuse its DND-checking logic
    # instead of duplicating the overnight-window math here.
    probe = Reminder(
        user_id="probe",
        title="probe",
        scheduled_time=scheduled_time,
    )
    return probe.is_in_dnd_window(settings.dnd_start, settings.dnd_end)


def create_reminder(user_id: str, title: str, message: str, channel: str,
                     repeat_type: str, scheduled_time: datetime,
                     confirm_dnd_override: bool = False) -> dict:
    """
    UC05 main flow: validate DND, create+save a Reminder, and call
    reminder.schedule() to enqueue the Celery task.

    UC05 exception flow: if scheduled_time falls in the user's DND
    window and confirm_dnd_override is False, no Reminder is created -
    the caller (controller) gets back a warning so it can ask the user
    to confirm or pick another time.

    Returns:
        {"status": "dnd_warning"}                    -> needs confirmation
        {"status": "created", "reminder": Reminder}   -> saved + scheduled
    """
    settings = NotificationSettings.get_or_create_default(user_id)

    if check_dnd_window(scheduled_time, settings) and not confirm_dnd_override:
        return {"status": "dnd_warning"}

    reminder = Reminder(
        user_id=user_id,
        title=title,
        message=message,
        channel=channel,
        repeat_type=repeat_type,
        scheduled_time=scheduled_time,
        status="created",
    )
    reminder.save()
    reminder.schedule()  # moves status -> "scheduled" and enqueues the Celery task

    return {"status": "created", "reminder": reminder}


def edit_reminder(reminder_id: str, **fields):
    """UC05: update an existing Reminder's editable fields and re-schedule it."""
    reminder = Reminder.objects.get(reminder_id=reminder_id, is_deleted=False)

    for field_name in ("title", "message", "channel", "repeat_type", "scheduled_time"):
        if field_name in fields and fields[field_name] is not None:
            setattr(reminder, field_name, fields[field_name])

    reminder.updated_at = datetime.utcnow()
    reminder.save()

    # Re-scheduling: time may have changed, so re-enqueue the Celery task
    # at the (possibly new) scheduled_time.
    reminder.schedule()
    return reminder


def delete_reminder(reminder_id: str):
    """UC05: soft-delete a Reminder. The already-enqueued Celery task will
    simply no-op if it fires later and finds is_deleted=True."""
    reminder = Reminder.objects.get(reminder_id=reminder_id, is_deleted=False)
    reminder.is_deleted = True
    reminder.updated_at = datetime.utcnow()
    reminder.save()
    return reminder


def process_due_reminder(reminder_id: str):
    """
    UC12: called by the Celery task when a reminder's scheduled_time
    arrives. Builds the Notification, sends it, and - for repeating
    reminders - schedules the next occurrence.
    """
    reminder = Reminder.objects(reminder_id=reminder_id, is_deleted=False).first()
    if reminder is None:
        # Reminder was deleted after being scheduled - nothing to do.
        return

    notification = Notification(
        user_id=reminder.user_id,
        reminder_id=reminder.reminder_id,
        type="reminder",
        content=reminder.message or reminder.title,
    )
    notification.save()
    notification.send()

    reminder.mark_sent()

    next_run = _next_occurrence(reminder.scheduled_time, reminder.repeat_type)
    if next_run is not None:
        # Repeating reminder: roll it forward and re-schedule.
        reminder.scheduled_time = next_run
        reminder.status = "created"
        reminder.save()
        reminder.schedule()
    else:
        # One-off reminder: nothing more to do until the user marks it
        # completed from the notification (handled by the controller).
        pass


def send_push_notification(user_id: str, title: str, message: str):
    """
    Send a push notification via Firebase Cloud Messaging using the
    user's DeviceToken(s).

    UC11 exception flow: if Firebase is unreachable/misconfigured, the
    failure is logged and swallowed here rather than raised - the
    Notification document has already been saved to notification history,
    so the user can still see it there even if the push itself failed.

    NOTE: actual Firebase credentials/setup are not configured yet.
    firebase_admin is imported lazily and guarded so this function stays
    callable (and testable) before that integration is wired up.
    """
    tokens = DeviceToken.tokens_for_user(user_id)
    if not tokens:
        logger.info("send_push_notification: no device tokens for user %s", user_id)
        return

    try:
        import firebase_admin
        from firebase_admin import messaging

        if not firebase_admin._apps:
            # Expects GOOGLE_APPLICATION_CREDENTIALS env var to point at
            # the service-account JSON file, per the phase-3 external
            # requirements around Firebase.
            firebase_admin.initialize_app()

        for token in tokens:
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=message),
                token=token,
            )
            messaging.send(msg)

    except Exception as exc:  # noqa: BLE001 - deliberately broad: never crash the caller
        logger.warning("send_push_notification failed for user %s: %s", user_id, exc)


def get_smart_reminder_suggestion(user_id: str):
    """
    UC13: analyze the user's recent WorkoutSession history and suggest
    a new reminder (e.g. missing weekly cardio). Returns None if no
    suggestion applies.

    Simple heuristic for now: if the user has logged zero WorkoutSessions
    in the last 7 days, suggest a daily workout reminder. This can be
    made smarter later (per-exercise-type frequency, etc.) without
    changing the function's signature.
    """
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    recent_sessions = WorkoutSession.objects(
        user_id=user_id,
        is_deleted=False,
        session_date__gte=one_week_ago,
    ).count()

    if recent_sessions == 0:
        return {
            "title": "وقتشه که برگردی به تمرین!",
            "message": "این هفته هنوز تمرینی ثبت نکردی. یه یادآور برات تنظیم کنیم؟",
            "suggested_repeat_type": "daily",
        }

    return None


def get_notification_history(user_id: str) -> list:
    """UC07: return the user's notification history, newest first."""
    notifications = Notification.objects(
        user_id=user_id, is_deleted=False
    ).order_by("-created_at")
    return list(notifications)


def update_notification_settings(user_id: str, **fields) -> NotificationSettings:
    """UC06/UC08: create-or-update the user's NotificationSettings."""
    settings = NotificationSettings.get_or_create_default(user_id)

    for field_name in ("push_enabled", "sms_enabled", "email_enabled", "dnd_start", "dnd_end"):
        if field_name in fields and fields[field_name] is not None:
            setattr(settings, field_name, fields[field_name])

    settings.updated_at = datetime.utcnow()
    settings.save()
    return settings


def subscribe_to_event(user_id: str, event_type: str, reference_id: str) -> EventSubscription:
    """UC08: register the user's interest in a future event (e.g. product restock)."""
    subscription = EventSubscription(
        user_id=user_id,
        event_type=event_type,
        reference_id=reference_id,
    )
    subscription.save()
    return subscription


def notify_event_subscribers(event_type: str, reference_id: str, message: str):
    """
    Called by whichever part of the system detects that a subscribed-to
    event has occurred (e.g. the store microservice signals a product is
    back in stock). Fans the notification out to every subscriber.
    """
    user_ids = EventSubscription.subscribers_for(event_type, reference_id)

    for user_id in user_ids:
        notification = Notification(
            user_id=user_id,
            type="event",
            content=message,
        )
        notification.save()
        notification.send()


# ============================================================
# Internal helpers (not part of the public service API)
# ============================================================

def _next_occurrence(previous_time: datetime, repeat_type: str):
    """Compute the next scheduled_time for a repeating reminder, or None for one-off reminders."""
    if repeat_type == "daily":
        return previous_time + timedelta(days=1)
    if repeat_type == "weekly":
        return previous_time + timedelta(weeks=1)
    if repeat_type == "monthly":
        return previous_time + timedelta(days=30)  # simple approximation
    return None


def _is_trainer_authorized(trainer_id: str, athlete_id: str) -> bool:
    """
    Placeholder trainer-athlete authorization check.
    TODO: replace with a real call to Core once the trainer-athlete
    assignment model exists there. Always allows for now so the rest
    of the mentor-report flow can be built and tested.
    """
    return True


# ---- Redis helpers (soft-fail: caching is an optimization, not a requirement) ----

_redis_client = None


def _get_redis_client():
    """
    Lazily create a single shared Redis client using REDIS_URL from the
    environment. Returns None (instead of raising) if Redis isn't
    configured or reachable, so callers can treat caching as best-effort.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None

    try:
        import redis
        _redis_client = redis.from_url(redis_url)
        _redis_client.ping()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis unavailable, falling back to no cache: %s", exc)
        _redis_client = None

    return _redis_client


def _redis_get(key: str):
    client = _get_redis_client()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception:  # noqa: BLE001
        return None


def _redis_set(key: str, value: str, ttl_seconds: int):
    client = _get_redis_client()
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl_seconds)
    except Exception:  # noqa: BLE001
        pass


def _invalidate_chart_cache(user_id: str):
    """Drop cached chart data for a user after any write that could change it."""
    client = _get_redis_client()
    if client is None:
        return
    try:
        for period in ("week", "month", "year"):
            client.delete(f"chart:{user_id}:{period}")
    except Exception:  # noqa: BLE001
        pass
