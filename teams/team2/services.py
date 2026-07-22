"""
SERVICE LAYER
Business logic that spans multiple collections or talks to external
systems (Celery, Redis, Firebase). Controllers call these functions;
these functions call models.py, never the other way around.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import mongoengine as me
from dateutil.relativedelta import relativedelta

try:  # Package execution: teams.team2.services
    from .models import (
        DeviceToken,
        EventSubscription,
        Goal,
        Notification,
        NotificationSettings,
        PersonalBest,
        PhysicalRecord,
        Reminder,
        WorkoutSession,
        utc_now,
    )
except ImportError:  # Direct execution from inside teams/team2
    from models import (  # type: ignore
        DeviceToken,
        EventSubscription,
        Goal,
        Notification,
        NotificationSettings,
        PersonalBest,
        PhysicalRecord,
        Reminder,
        WorkoutSession,
        utc_now,
    )

logger = logging.getLogger("team2")

_UNSET = object()
_ALLOWED_PERIODS = {"week": 7, "month": 30, "year": 365}
_PHYSICAL_EDITABLE_FIELDS = {"weight", "height", "body_fat_percent", "muscle_mass"}
_REMINDER_EDITABLE_FIELDS = {"title", "message", "channel", "repeat_type", "scheduled_time"}
_SETTINGS_EDITABLE_FIELDS = {
    "push_enabled",
    "sms_enabled",
    "email_enabled",
    "dnd_start",
    "dnd_end",
    "timezone_name",
}


@dataclass(frozen=True)
class PushSendResult:
    """Describe the outcome of sending a push to all active device tokens."""

    message_id: Optional[str]
    sent_count: int
    failed_count: int


# ============================================================
# Progress Tracking services
# ============================================================


def register_physical_data(
    user_id: str,
    weight: float,
    height: float,
    body_fat_percent: Optional[float] = None,
    muscle_mass: Optional[float] = None,
) -> PhysicalRecord:
    """
    UC01 main flow: validate input, create a PhysicalRecord, compute BMI,
    save it, invalidate chart cache, and return the saved record.
    """
    record = PhysicalRecord(
        user_id=user_id,
        weight=weight,
        height=height,
        body_fat_percent=body_fat_percent,
        muscle_mass=muscle_mass,
    )
    record.calculate_bmi()
    record.save()
    _invalidate_chart_cache(user_id)
    return record


def edit_physical_data(record_id: str, **fields) -> PhysicalRecord:
    """
    UC02: update only editable PhysicalRecord fields, recompute BMI,
    save the document, and invalidate the user's chart cache.
    """
    unknown_fields = set(fields) - _PHYSICAL_EDITABLE_FIELDS
    if unknown_fields:
        raise ValueError(f"unsupported physical-data fields: {sorted(unknown_fields)}")

    record = PhysicalRecord.objects.get(record_id=record_id, is_deleted=False)
    for field_name in _PHYSICAL_EDITABLE_FIELDS:
        if field_name in fields:
            setattr(record, field_name, fields[field_name])

    record.calculate_bmi()
    record.updated_at = utc_now()
    record.save()
    _invalidate_chart_cache(record.user_id)
    return record


def delete_physical_data(record_id: str) -> PhysicalRecord:
    """UC02: soft-delete an active PhysicalRecord and invalidate its cache."""
    record = PhysicalRecord.objects.get(record_id=record_id, is_deleted=False)
    record.is_deleted = True
    record.updated_at = utc_now()
    record.save()
    _invalidate_chart_cache(record.user_id)
    return record


def get_progress_chart_data(user_id: str, period: str) -> dict:
    """
    UC03: return chronological progress-chart points for week/month/year.
    Redis is used as a best-effort five-minute cache.
    """
    if period not in _ALLOWED_PERIODS:
        raise ValueError(f"period must be one of {tuple(_ALLOWED_PERIODS)}")

    cache_key = f"chart:{user_id}:{period}"
    cached = _redis_get(cache_key)
    if cached is not None:
        try:
            return json.loads(cached)
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Discarding invalid chart cache value for %s", cache_key)
            _redis_delete(cache_key)

    since = utc_now() - timedelta(days=_ALLOWED_PERIODS[period])
    records = PhysicalRecord.objects(
        user_id=user_id,
        is_deleted=False,
        created_at__gte=since,
    ).order_by("created_at")
    goal = Goal.objects(user_id=user_id, is_deleted=False).first()

    points = []
    for record in records:
        point = {
            "date": _as_utc(record.created_at).isoformat(),
            "weight": record.weight,
            "bmi": record.bmi,
            "body_fat_percent": record.body_fat_percent,
        }
        if goal is not None:
            point["goal_comparison"] = record.compare_with_goal(goal)
        points.append(point)

    result = {"period": period, "points": points}
    _redis_set(cache_key, json.dumps(result), ttl_seconds=300)
    return result


def set_user_goal(
    user_id: str,
    target_weight=_UNSET,
    target_body_fat=_UNSET,
    weight_goal_type=_UNSET,
    weight_tolerance=_UNSET,
) -> Goal:
    """
    UC04: create or update the user's active Goal.

    Passing ``None`` explicitly clears an optional target; omitting a
    parameter leaves its existing value unchanged.
    """
    goal = Goal.objects(user_id=user_id, is_deleted=False).first()
    if goal is None:
        goal = Goal(user_id=user_id)

    if target_weight is not _UNSET:
        goal.target_weight = target_weight
    if target_body_fat is not _UNSET:
        goal.target_body_fat = target_body_fat
    if weight_goal_type is not _UNSET:
        goal.weight_goal_type = weight_goal_type
    if weight_tolerance is not _UNSET:
        goal.weight_tolerance = weight_tolerance

    if goal.target_weight is None and goal.target_body_fat is None:
        raise ValueError("at least one goal target must be configured")

    goal.updated_at = utc_now()
    goal.save()
    _invalidate_chart_cache(user_id)
    return goal


def get_mentor_report(
    trainer_id: str,
    athlete_id: str,
    authorization_checker: Optional[Callable[[str, str], bool]] = None,
) -> dict:
    """
    UC09: authorize the trainer and build the athlete's monthly report.

    Authorization fails closed until a real Core-service checker is supplied.
    """
    checker = authorization_checker or _is_trainer_authorized
    if not checker(trainer_id, athlete_id):
        raise PermissionError("trainer is not authorized to view this athlete's report")

    personal_bests = PersonalBest.objects(
        user_id=athlete_id, is_deleted=False
    ).order_by("exercise_name")
    return {
        "athlete_id": athlete_id,
        "chart_data": get_progress_chart_data(athlete_id, period="month"),
        "personal_bests": [
            {
                "exercise_name": pb.exercise_name,
                "max_weight": pb.max_weight,
                "achieved_date": _as_utc(pb.achieved_date).isoformat(),
            }
            for pb in personal_bests
        ],
    }


def detect_and_register_new_record(
    user_id: str,
    exercise_name: str,
    weight_lifted: float,
    session_id: str,
    notification_sender: Optional[Callable[..., object]] = None,
):
    """
    UC11: atomically register a better PersonalBest and create a notification.
    Returns None when the supplied weight does not improve the active record.
    """
    session = WorkoutSession.objects.get(
        session_id=session_id,
        user_id=user_id,
        is_deleted=False,
    )
    normalized_exercise = " ".join(exercise_name.split())
    if " ".join(session.exercise_name.split()) != normalized_exercise:
        raise ValueError("exercise_name does not match the workout session")
    if session.weight_lifted is not None and session.weight_lifted != weight_lifted:
        raise ValueError("weight_lifted does not match the workout session")

    personal_best, changed = PersonalBest.register_if_better(
        user_id=user_id,
        exercise_name=normalized_exercise,
        weight_lifted=weight_lifted,
        session_id=session_id,
        achieved_date=session.session_date,
    )
    if not changed:
        return None

    notification = Notification(
        user_id=user_id,
        type="record",
        title="رکورد جدید",
        content=f"تبریک! رکورد جدید در {normalized_exercise}: {weight_lifted} کیلوگرم",
    ).save()
    notification.send(sender=notification_sender or send_push_notification)
    return personal_best


# ============================================================
# Reminder & Notification services
# ============================================================


def check_dnd_window(
    scheduled_time: datetime,
    settings: NotificationSettings,
) -> bool:
    """
    UC05 subflow: check DND using the user's configured timezone.
    The interval is start-inclusive and end-exclusive.
    """
    local_time = _as_utc(scheduled_time).astimezone(_get_zone(settings.timezone_name))
    probe = Reminder(user_id="probe", title="probe", scheduled_time=local_time)
    return probe.is_in_dnd_window(settings.dnd_start, settings.dnd_end)


def create_reminder(
    user_id: str,
    title: str,
    message: Optional[str],
    channel: str,
    repeat_type: str,
    scheduled_time: datetime,
    confirm_dnd_override: bool = False,
    task=None,
) -> dict:
    """
    UC05: validate DND, save a Reminder, and enqueue exactly one Celery task.
    """
    scheduled_time = _as_utc(scheduled_time)
    if scheduled_time <= utc_now():
        raise ValueError("scheduled_time must be in the future")

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
    ).save()
    reminder.schedule(task=task or _get_process_due_task())
    return {"status": "created", "reminder": reminder}


def edit_reminder(
    reminder_id: str,
    confirm_dnd_override: bool = False,
    task=None,
    revoke_task: Optional[Callable[[str], None]] = None,
    **fields,
) -> Reminder:
    """
    UC05: update editable fields, cancel the old task, and schedule one new task.
    """
    unknown_fields = set(fields) - _REMINDER_EDITABLE_FIELDS
    if unknown_fields:
        raise ValueError(f"unsupported reminder fields: {sorted(unknown_fields)}")

    reminder = Reminder.objects.get(reminder_id=reminder_id, is_deleted=False)
    candidate_time = _as_utc(fields.get("scheduled_time", reminder.scheduled_time))
    if candidate_time <= utc_now():
        raise ValueError("scheduled_time must be in the future")

    settings = NotificationSettings.get_or_create_default(reminder.user_id)
    if check_dnd_window(candidate_time, settings) and not confirm_dnd_override:
        raise ValueError("scheduled_time falls inside the user's DND window")

    old_task_id = reminder.celery_task_id
    for field_name in _REMINDER_EDITABLE_FIELDS:
        if field_name in fields:
            value = candidate_time if field_name == "scheduled_time" else fields[field_name]
            setattr(reminder, field_name, value)

    if old_task_id:
        (revoke_task or _revoke_celery_task)(old_task_id)

    reminder.status = "created"
    reminder.celery_task_id = None
    reminder.last_error = None
    reminder.updated_at = utc_now()
    reminder.save()
    reminder.schedule(task=task or _get_process_due_task())
    return reminder


def delete_reminder(
    reminder_id: str,
    revoke_task: Optional[Callable[[str], None]] = None,
) -> Reminder:
    """UC05: cancel the queued task and soft-delete the active Reminder."""
    reminder = Reminder.objects.get(reminder_id=reminder_id, is_deleted=False)
    if reminder.celery_task_id:
        (revoke_task or _revoke_celery_task)(reminder.celery_task_id)
    reminder.is_deleted = True
    reminder.celery_task_id = None
    reminder.updated_at = utc_now()
    reminder.save()
    return reminder


def process_due_reminder(
    reminder_id: str,
    task=None,
    notification_sender: Optional[Callable[..., object]] = None,
):
    """
    UC12: atomically claim a due reminder, dispatch it once, and schedule
    the next future occurrence when repetition is enabled.
    """
    now = utc_now()
    reminder = Reminder.objects(
        reminder_id=reminder_id,
        is_deleted=False,
        status="scheduled",
        scheduled_time__lte=now,
    ).modify(
        set__status="sent",
        set__updated_at=now,
        new=True,
    )
    if reminder is None:
        return None

    settings = NotificationSettings.get_or_create_default(reminder.user_id)
    if check_dnd_window(now, settings):
        next_allowed = _next_dnd_end(now, settings)
        reminder.status = "created"
        reminder.scheduled_time = next_allowed
        reminder.celery_task_id = None
        reminder.updated_at = utc_now()
        reminder.save()
        reminder.schedule(task=task or _get_process_due_task())
        return None

    if not _channel_enabled(reminder.channel, settings):
        reminder.status = "failed"
        reminder.last_error = f"{reminder.channel} notifications are disabled"
        reminder.updated_at = utc_now()
        reminder.save()
        return None

    notification = Notification(
        user_id=reminder.user_id,
        reminder_id=reminder.reminder_id,
        type="reminder",
        title=reminder.title,
        content=reminder.message or reminder.title,
    ).save()

    try:
        if reminder.channel != "push":
            raise NotImplementedError(f"{reminder.channel} delivery is not configured")
        notification.send(sender=notification_sender or send_push_notification)
    except Exception as exc:
        reminder.status = "failed"
        reminder.last_error = str(exc)
        reminder.updated_at = utc_now()
        reminder.save()
        raise

    next_run = _next_occurrence(reminder.scheduled_time, reminder.repeat_type, now)
    if next_run is not None:
        reminder.scheduled_time = next_run
        reminder.status = "created"
        reminder.celery_task_id = None
        reminder.last_error = None
        reminder.updated_at = utc_now()
        reminder.save()
        reminder.schedule(task=task or _get_process_due_task())
    return notification


def send_push_notification(user_id: str, title: str, message: str) -> PushSendResult:
    """
    Send a push notification to every active FCM token.

    Invalid tokens are soft-deleted. Provider failures are raised so
    Notification.send() can record a failed delivery accurately.
    """
    tokens = DeviceToken.tokens_for_user(user_id)
    if not tokens:
        raise RuntimeError("no active device tokens for user")

    try:
        import firebase_admin
        from firebase_admin import messaging
    except ImportError as exc:
        raise RuntimeError("firebase_admin is not installed") from exc

    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()

    sent_count = 0
    failures = []
    message_ids = []
    for token in tokens:
        try:
            message_id = messaging.send(
                messaging.Message(
                    notification=messaging.Notification(title=title, body=message),
                    token=token,
                )
            )
            sent_count += 1
            message_ids.append(message_id)
        except Exception as exc:  # Provider SDK exposes several exception classes.
            failures.append((token, exc))
            if _is_invalid_fcm_token_error(exc):
                DeviceToken.objects(fcm_token=token, is_deleted=False).update_one(
                    set__is_deleted=True,
                    set__updated_at=utc_now(),
                )

    if sent_count == 0:
        details = "; ".join(str(exc) for _, exc in failures)
        raise RuntimeError(f"push delivery failed for all tokens: {details}")
    if failures:
        logger.warning(
            "Push partially failed for user %s: %s/%s tokens",
            user_id,
            len(failures),
            len(tokens),
        )

    return PushSendResult(
        message_id=message_ids[0] if len(message_ids) == 1 else None,
        sent_count=sent_count,
        failed_count=len(failures),
    )


def get_smart_reminder_suggestion(user_id: str):
    """
    UC13: suggest a workout reminder only when the user is inactive,
    push is enabled, and no active workout reminder already exists.
    """
    settings = NotificationSettings.get_or_create_default(user_id)
    if not settings.push_enabled:
        return None

    one_week_ago = utc_now() - timedelta(days=7)
    has_recent_session = WorkoutSession.objects(
        user_id=user_id,
        is_deleted=False,
        session_date__gte=one_week_ago,
    ).first()
    has_active_reminder = Reminder.objects(
        user_id=user_id,
        is_deleted=False,
        status__in=("created", "scheduled"),
    ).first()

    if has_recent_session is None and has_active_reminder is None:
        return {
            "title": "وقتشه که برگردی به تمرین!",
            "message": "این هفته هنوز تمرینی ثبت نکردی. یه یادآور برات تنظیم کنیم؟",
            "suggested_repeat_type": "daily",
        }
    return None


def get_notification_history(user_id: str, limit: int = 100) -> list[Notification]:
    """UC07: return the newest active notifications with a bounded result size."""
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    return list(
        Notification.objects(user_id=user_id, is_deleted=False)
        .order_by("-created_at")
        .limit(limit)
    )


def update_notification_settings(user_id: str, **fields) -> NotificationSettings:
    """UC06/UC08: validate and update only supported notification settings."""
    unknown_fields = set(fields) - _SETTINGS_EDITABLE_FIELDS
    if unknown_fields:
        raise ValueError(f"unsupported settings fields: {sorted(unknown_fields)}")

    settings = NotificationSettings.get_or_create_default(user_id)
    for field_name, value in fields.items():
        setattr(settings, field_name, value)
    settings.updated_at = utc_now()
    settings.save()
    return settings


def subscribe_to_event(
    user_id: str,
    event_type: str,
    reference_id: str,
) -> EventSubscription:
    """UC08: create, return, or reactivate one active event subscription."""
    active = EventSubscription.objects(
        user_id=user_id,
        event_type=event_type,
        reference_id=reference_id,
        is_deleted=False,
    ).first()
    if active is not None:
        return active

    deleted = EventSubscription.objects(
        user_id=user_id,
        event_type=event_type,
        reference_id=reference_id,
        is_deleted=True,
    ).first()
    if deleted is not None:
        deleted.is_deleted = False
        deleted.updated_at = utc_now()
        deleted.save()
        return deleted

    try:
        return EventSubscription(
            user_id=user_id,
            event_type=event_type,
            reference_id=reference_id,
        ).save()
    except me.NotUniqueError:
        return EventSubscription.objects.get(
            user_id=user_id,
            event_type=event_type,
            reference_id=reference_id,
            is_deleted=False,
        )


def notify_event_subscribers(
    event_type: str,
    reference_id: str,
    message: str,
    notification_sender: Optional[Callable[..., object]] = None,
    consume_subscriptions: bool = True,
) -> dict:
    """
    Fan an event notification out in batches and optionally consume
    one-shot subscriptions after successful delivery attempts.
    """
    subscriptions = EventSubscription.objects(
        event_type=event_type,
        reference_id=reference_id,
        is_deleted=False,
    ).only("subscription_id", "user_id")

    sent = 0
    failed = 0
    processed_ids = []
    for subscription in subscriptions:
        notification = Notification(
            user_id=subscription.user_id,
            type="event",
            title="رویداد جدید",
            content=message,
        ).save()
        try:
            notification.send(sender=notification_sender or send_push_notification)
            sent += 1
            processed_ids.append(subscription.subscription_id)
        except Exception:
            failed += 1
            logger.exception(
                "Event notification failed for subscription %s",
                subscription.subscription_id,
            )

    if consume_subscriptions and processed_ids:
        EventSubscription.objects(subscription_id__in=processed_ids).update(
            set__is_deleted=True,
            set__updated_at=utc_now(),
        )
    return {"sent": sent, "failed": failed}


# ============================================================
# Internal helpers (not part of the public service API)
# ============================================================


def _next_occurrence(
    previous_time: datetime,
    repeat_type: str,
    now: Optional[datetime] = None,
):
    """Return the first repeated occurrence strictly after ``now``."""
    if repeat_type == "none":
        return None

    current = _as_utc(previous_time)
    comparison_time = _as_utc(now or utc_now())
    while current <= comparison_time:
        if repeat_type == "daily":
            current += timedelta(days=1)
        elif repeat_type == "weekly":
            current += timedelta(weeks=1)
        elif repeat_type == "monthly":
            current += relativedelta(months=1)
        else:
            raise ValueError(f"unsupported repeat_type: {repeat_type}")
    return current


def _is_trainer_authorized(trainer_id: str, athlete_id: str) -> bool:
    """
    Fail-closed placeholder until Core provides trainer-athlete authorization.
    A real checker should be injected into get_mentor_report().
    """
    logger.warning(
        "Mentor report denied because no Core authorization checker is configured"
    )
    return False


def _as_utc(value: datetime) -> datetime:
    """Normalize naive or aware datetimes to timezone-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _get_zone(timezone_name: str) -> ZoneInfo:
    """Return a valid IANA timezone or raise a clear validation error."""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {timezone_name}") from exc


def _next_dnd_end(now: datetime, settings: NotificationSettings) -> datetime:
    """Compute the next end of the user's DND interval in UTC."""
    zone = _get_zone(settings.timezone_name)
    local_now = _as_utc(now).astimezone(zone)
    end_hour, end_minute = map(int, settings.dnd_end.split(":"))
    candidate = local_now.replace(
        hour=end_hour,
        minute=end_minute,
        second=0,
        microsecond=0,
    )
    if candidate <= local_now:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc)


def _channel_enabled(channel: str, settings: NotificationSettings) -> bool:
    """Return whether the selected notification channel is enabled."""
    return {
        "push": settings.push_enabled,
        "sms": settings.sms_enabled,
        "email": settings.email_enabled,
    }[channel]


def _get_process_due_task():
    """Import the Celery task without assuming one execution layout."""
    try:
        from .tasks import process_due_reminder as task
    except ImportError:
        from tasks import process_due_reminder as task  # type: ignore
    return task


def _revoke_celery_task(task_id: str) -> None:
    """Revoke a queued Celery task using the current Celery application."""
    try:
        from celery import current_app
    except ImportError as exc:
        raise RuntimeError("Celery is not installed") from exc
    current_app.control.revoke(task_id, terminate=False)


def _is_invalid_fcm_token_error(exc: Exception) -> bool:
    """Best-effort detection of provider errors that invalidate a token."""
    name = exc.__class__.__name__.lower()
    text = str(exc).lower()
    markers = ("unregistered", "invalidargument", "invalid registration token")
    return any(marker in name or marker in text for marker in markers)


# ---- Redis helpers (soft-fail: caching is an optimization, not a requirement) ----

_redis_client = None


def _get_redis_client():
    """
    Lazily create a shared Redis client using REDIS_URL.
    Return None when Redis is unavailable so caching remains optional.
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        return None

    try:
        import redis

        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        _redis_client.ping()
    except Exception as exc:
        logger.warning("Redis unavailable, falling back to no cache: %s", exc)
        _redis_client = None
    return _redis_client


def _reset_redis_client() -> None:
    """Drop the cached Redis client so the next call can reconnect."""
    global _redis_client
    _redis_client = None


def _redis_get(key: str):
    """Read one cache key and reset the client after connection failures."""
    client = _get_redis_client()
    if client is None:
        return None
    try:
        return client.get(key)
    except Exception as exc:
        logger.warning("Redis GET failed for %s: %s", key, exc)
        _reset_redis_client()
        return None


def _redis_set(key: str, value: str, ttl_seconds: int) -> None:
    """Write one cache key with a TTL and soft-fail on Redis errors."""
    client = _get_redis_client()
    if client is None:
        return
    try:
        client.set(key, value, ex=ttl_seconds)
    except Exception as exc:
        logger.warning("Redis SET failed for %s: %s", key, exc)
        _reset_redis_client()


def _redis_delete(key: str) -> None:
    """Delete one cache key and soft-fail on Redis errors."""
    client = _get_redis_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as exc:
        logger.warning("Redis DELETE failed for %s: %s", key, exc)
        _reset_redis_client()


def _invalidate_chart_cache(user_id: str) -> None:
    """Delete every known chart-cache key after progress-related writes."""
    for period in _ALLOWED_PERIODS:
        _redis_delete(f"chart:{user_id}:{period}")
