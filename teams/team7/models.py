from django.db import models

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
from datetime import datetime
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
        Corresponds to UC01 / calculateBMI() in the phase-2 class diagram.
        """
        pass

    def compare_with_goal(self, goal):
        """
        Compare this record against a Goal document.
        Return a dict describing distance-to-goal (e.g. {"weight_diff": ...}).
        Corresponds to UC03 (progress vs. goal comparison).
        """
        pass


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
        """Return True if latest_record meets or exceeds this goal."""
        pass


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
        """
        pass

    def update_record(self, new_weight: float, session_id: str):
        """Update max_weight/achieved_date/session_id after a new record. Corresponds to updateRecord()."""
        pass


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
        """
        pass

    def schedule(self):
        """Enqueue this reminder as a Celery task at self.scheduled_time."""
        pass

    def mark_sent(self):
        """Transition self.status to 'sent' (state diagram: scheduled -> sent)."""
        pass


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
        pass

    def send(self):
        """Dispatch this notification through Firebase (delegates to services.py)."""
        pass


class DeviceToken(me.Document):
    token_id = me.StringField(primary_key=True, default=gen_id)
    user_id = me.StringField(required=True)
    fcm_token = me.StringField(required=True)
    created_at = me.DateTimeField(default=datetime.utcnow, required=True)
    updated_at = me.DateTimeField(null=True)
    is_deleted = me.BooleanField(default=False, required=True)

    meta = {"collection": "device_tokens", "indexes": ["user_id"]}


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