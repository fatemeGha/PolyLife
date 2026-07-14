# Your team's data models go here. They live in YOUR database (the core's
# router routes "team7" models to the "team7" database automatically).
#
# Link rows to the logged-in user by their core id — store the id, do NOT add a
# ForeignKey to the core User (it lives in a different database).
#
# Example (uncomment and adapt):
#
# class Note(models.Model):
#     user_id = models.IntegerField(db_index=True)   # comes from X-User-Id
#     text = models.TextField()
#     created_at = models.DateTimeField(auto_now_add=True)

"""
MODEL LAYER
Owns: data schema (MongoDB collections via mongoengine) +
      entity-level business logic (methods tied to a single document).
Cross-entity business logic (queries spanning multiple collections)
belongs in services.py, not here.
"""

import uuid
from datetime import datetime, time as dt_time
import mongoengine as me


def gen_id():
    """Generate a unique string ID used as the primary key for every document."""
    return str(uuid.uuid4())


# ============================================================
# Progress Tracking collections
# ============================================================

class PhysicalRecord(me.Document):
    record_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True)
    weight = me.FloatField(required=True, min_value=0)
    height = me.FloatField(required=True, min_value=0)
    body_fat_percent = me.FloatField()
    muscle_mass = me.FloatField()
    bmi = me.FloatField()
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "physical_records",
        "indexes": ["user_id", ("user_id", "-created_at")],
    }

    def calculate_bmi(self):
        """
        Compute BMI from self.weight and self.height, store it on self.bmi.
        Formula: BMI = weight(kg) / height(m)^2
        Corresponds to UC01 / calculateBMI() in the phase-2 class diagram.

        NOTE: this method only computes and assigns self.bmi in memory.
        The caller (usually a service function) is responsible for calling
        self.save() afterwards, so this method can be reused in contexts
        where saving isn't wanted yet (e.g. a "preview" calculation).
        """
        # height must be a positive, non-zero value or the formula breaks
        if not self.height or self.height <= 0:
            raise ValueError("height must be greater than zero to calculate BMI")

        self.bmi = round(self.weight / (self.height ** 2), 2)
        return self.bmi

    def compare_with_goal(self, goal: "Goal") -> dict:
        """
        Compare this record against a Goal document.
        Return a dict describing distance-to-goal, e.g.:
            {
                "weight_diff": current_weight - target_weight,
                "body_fat_diff": current_body_fat - target_body_fat,
                "weight_goal_reached": bool,
                "body_fat_goal_reached": bool,
            }
        Corresponds to UC03 (progress vs. goal comparison).
        A None value in the goal field means "no target set for that metric",
        in which case the related diff/flag is also returned as None.
        """
        result = {
            "weight_diff": None,
            "body_fat_diff": None,
            "weight_goal_reached": None,
            "body_fat_goal_reached": None,
        }

        if goal.target_weight is not None:
            diff = round(self.weight - goal.target_weight, 2)
            result["weight_diff"] = diff
            # "reached" means the user's weight has come down to (or below)
            # the target weight. Adjust the comparison direction here if a
            # future feature supports weight-gain goals as well.
            result["weight_goal_reached"] = self.weight <= goal.target_weight

        if goal.target_body_fat is not None and self.body_fat_percent is not None:
            diff = round(self.body_fat_percent - goal.target_body_fat, 2)
            result["body_fat_diff"] = diff
            result["body_fat_goal_reached"] = self.body_fat_percent <= goal.target_body_fat

        return result


class Goal(me.Document):
    goal_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, unique=True)
    target_weight = me.FloatField()
    target_body_fat = me.FloatField()
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {"collection": "goals"}

    def is_reached(self, latest_record: "PhysicalRecord") -> bool:
        """
        Return True if latest_record meets or exceeds this goal on every
        metric that has a target set. If no target is set at all, we
        conservatively return False (nothing to "reach").
        """
        comparison = latest_record.compare_with_goal(self)

        checks = [
            comparison["weight_goal_reached"],
            comparison["body_fat_goal_reached"],
        ]
        # Ignore metrics with no target set (they come back as None)
        relevant_checks = [c for c in checks if c is not None]

        if not relevant_checks:
            return False

        return all(relevant_checks)


class WorkoutSession(me.Document):
    session_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True)
    exercise_name = me.StringField(required=True)
    weight_lifted = me.FloatField()
    reps = me.IntField()
    session_date = me.DateTimeField(required=True)
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "workout_sessions",
        "indexes": ["user_id", ("user_id", "exercise_name")],
    }


class PersonalBest(me.Document):
    pb_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True)
    exercise_name = me.StringField(required=True)
    max_weight = me.FloatField(required=True)
    achieved_date = me.DateTimeField(required=True)
    session_id = me.StringField()  # FK -> WorkoutSession.session_id
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "personal_bests",
        "indexes": [{"fields": ("user_id", "exercise_name"), "unique": True}],
    }

    @classmethod
    def is_new_record(cls, user_id: str, exercise_name: str, weight_lifted: float) -> bool:
        """
        Check whether weight_lifted beats the current PersonalBest
        for (user_id, exercise_name). Corresponds to UC11 / isNewRecord().

        If the user has no PersonalBest yet for this exercise, the very
        first logged weight always counts as a new record.
        """
        existing = cls.objects(
            user_id=user_id,
            exercise_name=exercise_name,
            is_deleted=False,
        ).first()

        if existing is None:
            return True

        return weight_lifted > existing.max_weight

    def update_record(self, new_weight: float, session_id: str):
        """
        Update max_weight/achieved_date/session_id after a new record.
        Corresponds to updateRecord() in the phase-2 class diagram.
        Saves the document immediately since a "record update" is always
        a single atomic step (no separate confirmation step needed).
        """
        self.max_weight = new_weight
        self.achieved_date = datetime.utcnow()
        self.session_id = session_id
        self.updated_at = datetime.utcnow()
        self.save()
        return self

    @classmethod
    def create_first_record(cls, user_id: str, exercise_name: str,
                             weight_lifted: float, session_id: str):
        """
        Helper used when is_new_record() is True but no PersonalBest
        document exists yet for this (user_id, exercise_name) pair —
        creates the very first PersonalBest row.
        """
        record = cls(
            user_id=user_id,
            exercise_name=exercise_name,
            max_weight=weight_lifted,
            achieved_date=datetime.utcnow(),
            session_id=session_id,
        )
        record.save()
        return record


# ============================================================
# Reminder & Notification collections
# ============================================================

class Reminder(me.Document):
    STATUS_CHOICES = ("created", "scheduled", "sent", "completed", "expired")
    CHANNEL_CHOICES = ("push", "sms", "email")
    REPEAT_CHOICES = ("none", "daily", "weekly", "monthly")

    reminder_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True)
    title = me.StringField(required=True)
    message = me.StringField()
    channel = me.StringField(choices=CHANNEL_CHOICES, default="push")
    repeat_type = me.StringField(choices=REPEAT_CHOICES, default="none")
    scheduled_time = me.DateTimeField(required=True)
    status = me.StringField(choices=STATUS_CHOICES, default="created")
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "reminders",
        "indexes": ["user_id", "scheduled_time"],
    }

    def is_in_dnd_window(self, dnd_start: str, dnd_end: str) -> bool:
        """
        Check whether self.scheduled_time falls inside the quiet hours
        [dnd_start, dnd_end). Corresponds to UC05 DND check.

        dnd_start / dnd_end are "HH:MM" strings (e.g. "22:00", "08:00").
        Handles the overnight case where dnd_start > dnd_end
        (e.g. 22:00 -> 08:00 wraps past midnight).
        """
        scheduled_clock = self.scheduled_time.time()
        start_h, start_m = map(int, dnd_start.split(":"))
        end_h, end_m = map(int, dnd_end.split(":"))
        start_clock = dt_time(start_h, start_m)
        end_clock = dt_time(end_h, end_m)

        if start_clock <= end_clock:
            # Simple same-day window, e.g. 13:00 -> 15:00
            return start_clock <= scheduled_clock < end_clock

        # Overnight window, e.g. 22:00 -> 08:00
        return scheduled_clock >= start_clock or scheduled_clock < end_clock

    def schedule(self):
        """
        Enqueue this reminder as a Celery task at self.scheduled_time,
        then move its status to "scheduled".

        The Celery task itself lives in tasks.py (not written yet by the
        team) and is looked up by name here to avoid a circular import
        between models.py and tasks.py.
        """
        self.status = "scheduled"
        self.updated_at = datetime.utcnow()
        self.save()

        # Deferred import: tasks.py will define a Celery task named
        # "team7.tasks.process_due_reminder" that calls
        # services.process_due_reminder(reminder_id) when it fires.
        from .tasks import process_due_reminder  # noqa: F401 (implemented later)
        process_due_reminder.apply_async(
            args=[self.reminder_id],
            eta=self.scheduled_time,
        )

    def mark_sent(self):
        """Transition self.status to 'sent' (state diagram: scheduled -> sent)."""
        self.status = "sent"
        self.updated_at = datetime.utcnow()
        self.save()
        return self

    def mark_completed(self):
        """Transition self.status to 'completed' (user acted on the reminder)."""
        self.status = "completed"
        self.updated_at = datetime.utcnow()
        self.save()
        return self

    def mark_expired(self):
        """Transition self.status to 'expired' (reminder window passed, unacted)."""
        self.status = "expired"
        self.updated_at = datetime.utcnow()
        self.save()
        return self


class NotificationSettings(me.Document):
    setting_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True, unique=True)
    push_enabled = me.BooleanField(default=True)
    sms_enabled = me.BooleanField(default=False)
    email_enabled = me.BooleanField(default=False)
    dnd_start = me.StringField(default="22:00")
    dnd_end = me.StringField(default="08:00")
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {"collection": "notification_settings"}

    @classmethod
    def get_or_create_default(cls, user_id: str):
        """
        Return the user's NotificationSettings, creating a default one
        (push on, sms/email off, default DND hours) the first time a
        user is seen. Keeps callers from having to handle "no settings
        yet" as a special case everywhere.
        """
        settings = cls.objects(user_id=user_id, is_deleted=False).first()
        if settings is None:
            settings = cls(user_id=user_id)
            settings.save()
        return settings


class Notification(me.Document):
    TYPE_CHOICES = ("reminder", "record", "system", "event")

    notification_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True)
    reminder_id = me.StringField(null=True)  # FK -> Reminder.reminder_id
    type = me.StringField(choices=TYPE_CHOICES, required=True)
    content = me.StringField(required=True)
    is_read = me.BooleanField(default=False)
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "notifications",
        "indexes": ["user_id", ("user_id", "is_read")],
    }

    def mark_as_read(self):
        """Set is_read = True and save."""
        self.is_read = True
        self.updated_at = datetime.utcnow()
        self.save()
        return self

    def send(self):
        """
        Dispatch this notification through Firebase.
        The actual FCM call lives in services.py (send_push_notification),
        which is imported here lazily to avoid a circular import between
        models.py and services.py.
        """
        from .services import send_push_notification  # noqa: F401 (implemented later)
        send_push_notification(
            user_id=self.user_id,
            title="PolyLife",
            message=self.content,
        )


class DeviceToken(me.Document):
    token_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True)
    fcm_token = me.StringField(required=True)
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {"collection": "device_tokens", "indexes": ["user_id"]}

    @classmethod
    def tokens_for_user(cls, user_id: str) -> list:
        """Return all active (non-deleted) FCM token strings for a user."""
        return [
            dt.fcm_token
            for dt in cls.objects(user_id=user_id, is_deleted=False)
        ]


class EventSubscription(me.Document):
    EVENT_CHOICES = ("product_available", "challenge_start")

    subscription_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True)
    event_type = me.StringField(choices=EVENT_CHOICES, required=True)
    reference_id = me.StringField(required=True)
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {
        "collection": "event_subscriptions",
        "indexes": ["user_id", ("event_type", "reference_id")],
    }

    @classmethod
    def subscribers_for(cls, event_type: str, reference_id: str) -> list:
        """
        Return the list of user_ids subscribed to a given event
        (e.g. all users waiting on a specific product_id becoming
        available). Used by the system when the event actually fires.
        """
        return [
            sub.user_id
            for sub in cls.objects(
                event_type=event_type,
                reference_id=reference_id,
                is_deleted=False,
            )
        ]