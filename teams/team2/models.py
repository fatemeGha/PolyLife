"""MongoEngine models for Team 2.

The module contains document-level validation and entity-local behavior.
Operations involving external systems can receive dependencies explicitly,
which keeps the models testable while preserving convenient defaults.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, time as dt_time, timezone
from typing import Callable, Iterable, Optional

import mongoengine as me


_TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def gen_id() -> str:
    """Generate a unique UUID4 string."""
    return str(uuid.uuid4())


def _validate_positive(value: float) -> None:
    if value <= 0:
        raise me.ValidationError("value must be greater than zero")


def _validate_non_blank(value: str) -> None:
    if not value or not value.strip():
        raise me.ValidationError("value must not be blank")


def _validate_hhmm(value: str) -> None:
    if not _TIME_PATTERN.fullmatch(value or ""):
        raise me.ValidationError("time must use HH:MM in 24-hour format")


def _parse_hhmm(value: str) -> dt_time:
    _validate_hhmm(value)
    hour, minute = map(int, value.split(":"))
    return dt_time(hour, minute)


class PhysicalRecord(me.Document):
    record_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, validation=_validate_non_blank)
    weight = me.FloatField(required=True, validation=_validate_positive)
    height = me.FloatField(required=True, validation=_validate_positive)
    body_fat_percent = me.FloatField(min_value=0, max_value=100)
    muscle_mass = me.FloatField(min_value=0)
    bmi = me.FloatField(min_value=0)
    created_at = me.DateTimeField(default=utc_now, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "physical_records",
        "indexes": [("user_id", "-created_at")],
    }

    def calculate_bmi(self) -> float:
        if self.height is None or self.height <= 0:
            raise ValueError("height must be greater than zero to calculate BMI")
        if self.weight is None or self.weight <= 0:
            raise ValueError("weight must be greater than zero to calculate BMI")
        self.bmi = round(self.weight / (self.height**2), 2)
        return self.bmi

    def compare_with_goal(self, goal: "Goal") -> dict:
        if self.user_id != goal.user_id:
            raise ValueError("record and goal must belong to the same user")

        result = {
            "weight_diff": None,
            "body_fat_diff": None,
            "weight_goal_reached": None,
            "body_fat_goal_reached": None,
        }

        if goal.target_weight is not None:
            result["weight_diff"] = round(self.weight - goal.target_weight, 2)
            if goal.weight_goal_type == "gain":
                result["weight_goal_reached"] = self.weight >= goal.target_weight
            elif goal.weight_goal_type == "maintain":
                tolerance = goal.weight_tolerance
                result["weight_goal_reached"] = abs(self.weight - goal.target_weight) <= tolerance
            else:
                result["weight_goal_reached"] = self.weight <= goal.target_weight

        if goal.target_body_fat is not None:
            if self.body_fat_percent is not None:
                result["body_fat_diff"] = round(
                    self.body_fat_percent - goal.target_body_fat, 2
                )
                result["body_fat_goal_reached"] = (
                    self.body_fat_percent <= goal.target_body_fat
                )
            else:
                # A target exists but the record has no value to evaluate.
                result["body_fat_goal_reached"] = False

        return result


class Goal(me.Document):
    WEIGHT_GOAL_CHOICES = ("lose", "gain", "maintain")

    goal_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, validation=_validate_non_blank)
    target_weight = me.FloatField(validation=_validate_positive)
    target_body_fat = me.FloatField(min_value=0, max_value=100)
    weight_goal_type = me.StringField(
        choices=WEIGHT_GOAL_CHOICES, default="lose", required=True
    )
    weight_tolerance = me.FloatField(default=0.5, min_value=0)
    created_at = me.DateTimeField(default=utc_now, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "goals",
        "indexes": [
            {
                "fields": ["user_id"],
                "unique": True,
                "partialFilterExpression": {"is_deleted": False},
            }
        ],
    }

    def is_reached(self, latest_record: PhysicalRecord) -> bool:
        comparison = latest_record.compare_with_goal(self)
        checks = []
        if self.target_weight is not None:
            checks.append(comparison["weight_goal_reached"])
        if self.target_body_fat is not None:
            checks.append(comparison["body_fat_goal_reached"])
        return bool(checks) and all(check is True for check in checks)


class WorkoutSession(me.Document):
    session_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, validation=_validate_non_blank)
    exercise_name = me.StringField(required=True, validation=_validate_non_blank)
    weight_lifted = me.FloatField(min_value=0)
    reps = me.IntField(min_value=1)
    session_date = me.DateTimeField(required=True)
    created_at = me.DateTimeField(default=utc_now, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "workout_sessions",
        "indexes": [
            ("user_id", "-session_date"),
            ("user_id", "exercise_name", "-session_date"),
        ],
    }

    def clean(self) -> None:
        if self.exercise_name:
            self.exercise_name = " ".join(self.exercise_name.split())


class PersonalBest(me.Document):
    pb_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, validation=_validate_non_blank)
    exercise_name = me.StringField(required=True, validation=_validate_non_blank)
    max_weight = me.FloatField(required=True, min_value=0)
    achieved_date = me.DateTimeField(required=True)
    session_id = me.StringField(validation=_validate_non_blank)
    created_at = me.DateTimeField(default=utc_now, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "personal_bests",
        "indexes": [
            {
                "fields": ["user_id", "exercise_name"],
                "unique": True,
                "partialFilterExpression": {"is_deleted": False},
            }
        ],
    }

    def clean(self) -> None:
        if self.exercise_name:
            self.exercise_name = " ".join(self.exercise_name.split())

    @classmethod
    def is_new_record(
        cls, user_id: str, exercise_name: str, weight_lifted: float
    ) -> bool:
        if weight_lifted < 0:
            raise ValueError("weight_lifted must not be negative")
        normalized_name = " ".join(exercise_name.split())
        existing = cls.objects(
            user_id=user_id,
            exercise_name=normalized_name,
            is_deleted=False,
        ).first()
        return existing is None or weight_lifted > existing.max_weight

    def update_record(
        self,
        new_weight: float,
        session_id: str,
        achieved_date: Optional[datetime] = None,
    ) -> "PersonalBest":
        if new_weight <= self.max_weight:
            raise ValueError("new_weight must exceed the current personal best")
        self.max_weight = new_weight
        self.achieved_date = achieved_date or utc_now()
        self.session_id = session_id
        self.updated_at = utc_now()
        self.save()
        return self

    @classmethod
    def create_first_record(
        cls,
        user_id: str,
        exercise_name: str,
        weight_lifted: float,
        session_id: str,
        achieved_date: Optional[datetime] = None,
    ) -> "PersonalBest":
        record = cls(
            user_id=user_id,
            exercise_name=" ".join(exercise_name.split()),
            max_weight=weight_lifted,
            achieved_date=achieved_date or utc_now(),
            session_id=session_id,
        )
        record.save()
        return record

    @classmethod
    def register_if_better(
        cls,
        user_id: str,
        exercise_name: str,
        weight_lifted: float,
        session_id: str,
        achieved_date: Optional[datetime] = None,
    ) -> tuple["PersonalBest", bool]:
        """Atomically create or update the active personal best.

        Returns ``(record, changed)``. The implementation retries creation if
        another request wins the unique-index race.
        """
        normalized_name = " ".join(exercise_name.split())
        moment = achieved_date or utc_now()

        updated = cls.objects(
            user_id=user_id,
            exercise_name=normalized_name,
            is_deleted=False,
            max_weight__lt=weight_lifted,
        ).modify(
            set__max_weight=weight_lifted,
            set__session_id=session_id,
            set__achieved_date=moment,
            set__updated_at=utc_now(),
            new=True,
        )
        if updated is not None:
            return updated, True

        existing = cls.objects(
            user_id=user_id,
            exercise_name=normalized_name,
            is_deleted=False,
        ).first()
        if existing is not None:
            return existing, False

        try:
            return (
                cls.create_first_record(
                    user_id,
                    normalized_name,
                    weight_lifted,
                    session_id,
                    moment,
                ),
                True,
            )
        except me.NotUniqueError:
            existing = cls.objects(
                user_id=user_id,
                exercise_name=normalized_name,
                is_deleted=False,
            ).get()
            return existing, False


class Reminder(me.Document):
    STATUS_CHOICES = ("created", "scheduled", "sent", "completed", "expired", "failed")
    CHANNEL_CHOICES = ("push", "sms", "email")
    REPEAT_CHOICES = ("none", "daily", "weekly", "monthly")
    ALLOWED_TRANSITIONS = {
        "created": {"scheduled", "failed"},
        "scheduled": {"sent", "expired", "failed"},
        "sent": {"completed", "expired"},
        "completed": set(),
        "expired": set(),
        "failed": {"scheduled"},
    }

    reminder_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, validation=_validate_non_blank)
    title = me.StringField(required=True, validation=_validate_non_blank)
    message = me.StringField()
    channel = me.StringField(choices=CHANNEL_CHOICES, default="push", required=True)
    repeat_type = me.StringField(choices=REPEAT_CHOICES, default="none", required=True)
    scheduled_time = me.DateTimeField(required=True)
    status = me.StringField(choices=STATUS_CHOICES, default="created", required=True)
    celery_task_id = me.StringField(null=True)
    last_error = me.StringField(null=True)
    created_at = me.DateTimeField(default=utc_now, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "reminders",
        "indexes": [
            ("user_id", "is_deleted", "status", "scheduled_time"),
            "scheduled_time",
        ],
    }

    def is_in_dnd_window(self, dnd_start: str, dnd_end: str) -> bool:
        scheduled_clock = self.scheduled_time.timetz().replace(tzinfo=None)
        start_clock = _parse_hhmm(dnd_start)
        end_clock = _parse_hhmm(dnd_end)

        if start_clock == end_clock:
            return False
        if start_clock < end_clock:
            return start_clock <= scheduled_clock < end_clock
        return scheduled_clock >= start_clock or scheduled_clock < end_clock

    def transition_to(self, new_status: str) -> "Reminder":
        if new_status not in self.STATUS_CHOICES:
            raise ValueError(f"unknown reminder status: {new_status}")
        if new_status not in self.ALLOWED_TRANSITIONS[self.status]:
            raise ValueError(f"invalid reminder transition: {self.status} -> {new_status}")
        self.status = new_status
        self.updated_at = utc_now()
        self.save()
        return self

    def schedule(self, task=None) -> "Reminder":
        if self.pk is None:
            self.save()
        if self.status not in {"created", "failed"}:
            raise ValueError("only created or failed reminders can be scheduled")

        if task is None:
            from .tasks import process_due_reminder as task

        previous_status = self.status
        try:
            async_result = task.apply_async(
                args=[self.reminder_id], eta=self.scheduled_time
            )
            self.status = "scheduled"
            self.celery_task_id = getattr(async_result, "id", None)
            self.last_error = None
            self.updated_at = utc_now()
            self.save()
            return self
        except Exception as exc:
            self.status = "failed"
            self.last_error = str(exc)
            self.updated_at = utc_now()
            self.save()
            if previous_status == "failed":
                self.reload()
            raise

    def mark_sent(self) -> "Reminder":
        return self.transition_to("sent")

    def mark_completed(self) -> "Reminder":
        return self.transition_to("completed")

    def mark_expired(self) -> "Reminder":
        return self.transition_to("expired")


class NotificationSettings(me.Document):
    setting_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, validation=_validate_non_blank)
    push_enabled = me.BooleanField(default=True)
    sms_enabled = me.BooleanField(default=False)
    email_enabled = me.BooleanField(default=False)
    dnd_start = me.StringField(default="22:00", validation=_validate_hhmm)
    dnd_end = me.StringField(default="08:00", validation=_validate_hhmm)
    timezone_name = me.StringField(default="UTC", validation=_validate_non_blank)
    created_at = me.DateTimeField(default=utc_now, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "notification_settings",
        "indexes": [
            {
                "fields": ["user_id"],
                "unique": True,
                "partialFilterExpression": {"is_deleted": False},
            }
        ],
    }

    @classmethod
    def get_or_create_default(cls, user_id: str) -> "NotificationSettings":
        settings = cls.objects(user_id=user_id, is_deleted=False).first()
        if settings is not None:
            return settings
        try:
            return cls(user_id=user_id).save()
        except me.NotUniqueError:
            return cls.objects(user_id=user_id, is_deleted=False).get()


class Notification(me.Document):
    TYPE_CHOICES = ("reminder", "record", "system", "event")
    DELIVERY_STATUS_CHOICES = ("pending", "sent", "failed")

    notification_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, validation=_validate_non_blank)
    reminder_id = me.StringField(null=True)
    type = me.StringField(choices=TYPE_CHOICES, required=True)
    title = me.StringField(default="PolyLife", validation=_validate_non_blank)
    content = me.StringField(required=True, validation=_validate_non_blank)
    is_read = me.BooleanField(default=False)
    delivery_status = me.StringField(
        choices=DELIVERY_STATUS_CHOICES, default="pending", required=True
    )
    sent_at = me.DateTimeField(null=True)
    failed_at = me.DateTimeField(null=True)
    retry_count = me.IntField(default=0, min_value=0)
    last_error = me.StringField(null=True)
    provider_message_id = me.StringField(null=True)
    created_at = me.DateTimeField(default=utc_now, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "notifications",
        "indexes": [("user_id", "is_deleted", "is_read", "-created_at")],
    }

    def mark_as_read(self) -> "Notification":
        self.is_read = True
        self.updated_at = utc_now()
        self.save()
        return self

    def send(self, sender: Optional[Callable[..., object]] = None) -> "Notification":
        if sender is None:
            from .services.legacy_services import send_push_notification as sender
        try:
            result = sender(
                user_id=self.user_id,
                title=self.title,
                message=self.content,
            )
            self.delivery_status = "sent"
            self.sent_at = utc_now()
            self.failed_at = None
            self.last_error = None
            self.provider_message_id = getattr(result, "message_id", None)
            self.updated_at = utc_now()
            self.save()
            return self
        except Exception as exc:
            self.delivery_status = "failed"
            self.failed_at = utc_now()
            self.retry_count += 1
            self.last_error = str(exc)
            self.updated_at = utc_now()
            self.save()
            raise


class DeviceToken(me.Document):
    token_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, validation=_validate_non_blank)
    fcm_token = me.StringField(required=True, validation=_validate_non_blank, unique=True)
    created_at = me.DateTimeField(default=utc_now, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "device_tokens",
        "indexes": [("user_id", "is_deleted")],
    }

    @classmethod
    def tokens_for_user(cls, user_id: str) -> list[str]:
        return list(
            cls.objects(user_id=user_id, is_deleted=False).scalar("fcm_token")
        )


class EventSubscription(me.Document):
    EVENT_CHOICES = ("product_available", "challenge_start")

    subscription_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, validation=_validate_non_blank)
    event_type = me.StringField(choices=EVENT_CHOICES, required=True)
    reference_id = me.StringField(required=True, validation=_validate_non_blank)
    created_at = me.DateTimeField(default=utc_now, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "event_subscriptions",
        "indexes": [
            {
                "fields": ["user_id", "event_type", "reference_id"],
                "unique": True,
                "partialFilterExpression": {"is_deleted": False},
            },
            ("event_type", "reference_id", "is_deleted"),
        ],
    }

    @classmethod
    def subscribers_for(cls, event_type: str, reference_id: str) -> list[str]:
        return list(
            cls.objects(
                event_type=event_type,
                reference_id=reference_id,
                is_deleted=False,
            ).scalar("user_id")
        )
