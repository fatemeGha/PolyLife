"""
Database models for Team2 microservice.
Covers Progress Tracking and Reminder/Notification domains.

Note:
    - All models use soft delete via `is_deleted` flag.
    - `user_id` is an integer referencing the Core service user,
      NOT a ForeignKey (cross-service boundary).
    - Timestamps are managed automatically.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


# ---------------------------------------------------------------------------
# Progress Tracking Models
# ---------------------------------------------------------------------------

class PhysicalRecord(models.Model):
    """
    Stores a single physical measurement snapshot for a user.

    One user can have multiple records over time (daily/weekly entries).
    BMI is calculated and stored automatically upon save.

    Constraints:
        - weight must be between 1 and 500 kg
        - height must be between 50 and 300 cm
        - body_fat_percentage must be between 1 and 100 (optional)
        - muscle_mass must be positive (optional)
        - user_id must be a positive integer (from Gateway header)
    """

    user_id = models.IntegerField(
        db_index=True,
        help_text="References the user in Core service. Not a FK (cross-service)."
    )

    weight = models.FloatField(
        validators=[MinValueValidator(1.0), MaxValueValidator(500.0)],
        help_text="Body weight in kilograms."
    )

    height = models.FloatField(
        validators=[MinValueValidator(50.0), MaxValueValidator(300.0)],
        help_text="Height in centimeters."
    )

    bmi = models.FloatField(
        editable=False,
        help_text="Body Mass Index, auto-calculated from weight and height."
    )

    body_fat_percentage = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1.0), MaxValueValidator(100.0)],
        help_text="Body fat percentage (optional)."
    )

    muscle_mass = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.1)],
        help_text="Muscle mass in kilograms (optional)."
    )

    notes = models.TextField(
        blank=True,
        default="",
        help_text="Optional free-text notes for this record."
    )

    # ------------------------------------------------------------------
    # Soft delete + timestamps
    # ------------------------------------------------------------------

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft delete flag. Records are never physically removed."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was created."
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this record was last updated."
    )

    class Meta:
        db_table = "team2_physical_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "is_deleted"], name="idx_physical_user_active"),
            models.Index(fields=["user_id", "-created_at"], name="idx_physical_user_date"),
        ]
        verbose_name = "Physical Record"
        verbose_name_plural = "Physical Records"

    def __str__(self):
        return f"PhysicalRecord(user={self.user_id}, weight={self.weight}kg, bmi={self.bmi:.1f})"


# ---------------------------------------------------------------------------

class UserGoal(models.Model):
    """
    Stores the active fitness goal for a user.

    One user has at most ONE active goal at a time.
    Creating a new goal via the API updates the existing one (upsert behavior).

    Constraints:
        - target_weight must be between 1 and 500 kg
        - target_date must be a future date (enforced at service layer)
        - user_id is unique (one goal per user)
    """

    user_id = models.IntegerField(
        unique=True,
        db_index=True,
        help_text="One goal per user. References Core service user."
    )

    target_weight = models.FloatField(
        validators=[MinValueValidator(1.0), MaxValueValidator(500.0)],
        help_text="Target body weight in kilograms."
    )

    target_date = models.DateField(
        null=True,
        blank=True,
        help_text="Target date to achieve the goal (optional)."
    )

    target_body_fat = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1.0), MaxValueValidator(100.0)],
        help_text="Target body fat percentage (optional)."
    )

    # ------------------------------------------------------------------
    # Soft delete + timestamps
    # ------------------------------------------------------------------

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft delete flag."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this goal was first created."
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this goal was last updated."
    )

    class Meta:
        db_table = "team2_user_goal"
        verbose_name = "User Goal"
        verbose_name_plural = "User Goals"

    def __str__(self):
        return f"UserGoal(user={self.user_id}, target={self.target_weight}kg)"

# ---------------------------------------------------------------------------
# Reminder & Notification Models
# ---------------------------------------------------------------------------

class Reminder(models.Model):
    """
    Stores a scheduled reminder for a user.

    A reminder can be one-time or recurring (daily/weekly).
    The system checks quiet hours before scheduling notifications.

    Constraints:
        - user_id must be a positive integer (from Gateway header)
        - title cannot be blank
        - reminder_time must be a valid time
        - recurrence_pattern must be one of: none, daily, weekly
        - Only the owner can view/modify/delete their reminders
    """

    class RecurrencePattern(models.TextChoices):
        NONE = "none", "No Recurrence"
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"

    user_id = models.IntegerField(
        db_index=True,
        help_text="References the user in Core service. Not a FK (cross-service)."
    )

    title = models.CharField(
        max_length=255,
        help_text="Short descriptive title for the reminder."
    )

    message = models.TextField(
        blank=True,
        default="",
        help_text="Optional body text for the reminder notification."
    )

    reminder_time = models.TimeField(
        help_text="Time of day when the reminder should fire (HH:MM:SS)."
    )

    recurrence_pattern = models.CharField(
        max_length=10,
        choices=RecurrencePattern.choices,
        default=RecurrencePattern.NONE,
        help_text="How often the reminder repeats."
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Whether this reminder is currently active and will fire."
    )

    is_completed = models.BooleanField(
        default=False,
        help_text="Marked True when the user acknowledges the reminder."
    )

    force_send_in_quiet_hours = models.BooleanField(
        default=False,
        help_text="If True, reminder fires even during the user's quiet hours."
    )

    # ------------------------------------------------------------------
    # Soft delete + timestamps
    # ------------------------------------------------------------------

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Soft delete flag. Reminders are never physically removed."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this reminder was created."
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this reminder was last updated."
    )

    class Meta:
        db_table = "team2_reminder"
        ordering = ["reminder_time"]
        indexes = [
            models.Index(
                fields=["user_id", "is_deleted"],
                name="idx_reminder_user_active"
            ),
            models.Index(
                fields=["user_id", "is_completed"],
                name="idx_reminder_user_completed"
            ),
        ]
        verbose_name = "Reminder"
        verbose_name_plural = "Reminders"

    def __str__(self):
        return (
            f"Reminder(user={self.user_id}, "
            f"title='{self.title}', "
            f"time={self.reminder_time}, "
            f"recurrence={self.recurrence_pattern})"
        )


# ---------------------------------------------------------------------------

class NotificationSetting(models.Model):
    """
    Stores per-user notification preferences.

    Each user has exactly ONE NotificationSetting row.
    It is created with sensible defaults on first access (get_or_create).

    Quiet hours define the window during which notifications are suppressed
    unless the reminder has force_send_in_quiet_hours=True.

    Default quiet hours: 22:00 – 08:00 (overnight window).

    Constraints:
        - user_id is unique (one settings row per user)
        - quiet_hours_start and quiet_hours_end are valid time values
    """

    user_id = models.IntegerField(
        unique=True,
        db_index=True,
        help_text="One settings row per user."
    )

    is_enabled = models.BooleanField(
        default=True,
        help_text="Master switch — if False, no notifications are sent to this user."
    )

    quiet_hours_start = models.TimeField(
        default="22:00",
        help_text="Start of quiet hours window (notifications suppressed after this time)."
    )

    quiet_hours_end = models.TimeField(
        default="08:00",
        help_text="End of quiet hours window (notifications resume after this time)."
    )

    # ------------------------------------------------------------------
    # Soft delete + timestamps
    # ------------------------------------------------------------------

    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this settings record was created."
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this settings record was last updated."
    )

    class Meta:
        db_table = "team2_notification_setting"
        verbose_name = "Notification Setting"
        verbose_name_plural = "Notification Settings"

    def __str__(self):
        return (
            f"NotificationSetting(user={self.user_id}, "
            f"enabled={self.is_enabled}, "
            f"quiet={self.quiet_hours_start}-{self.quiet_hours_end})"
        )


# ---------------------------------------------------------------------------

class NotificationLog(models.Model):
    """
    Audit log for every notification dispatched (or attempted) by the system.

    Records are append-only — they are never updated or deleted.
    The status field tracks the delivery lifecycle.

    Status lifecycle:
        pending → sent      (successful delivery)
        pending → failed    (delivery error)

    Constraints:
        - reminder FK is nullable so system-generated notifications
          (not tied to a reminder) can also be logged.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    user_id = models.IntegerField(
        db_index=True,
        help_text="Target user for this notification."
    )

    reminder = models.ForeignKey(
        Reminder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notification_logs",
        help_text="The reminder that triggered this notification (if applicable)."
    )

    title = models.CharField(
        max_length=255,
        help_text="Notification title as displayed to the user."
    )

    message = models.TextField(
        blank=True,
        default="",
        help_text="Notification body text as displayed to the user."
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current delivery status of this notification."
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Exact timestamp when the notification was successfully delivered."
    )

    # ------------------------------------------------------------------
    # Timestamps (no soft delete — logs are immutable)
    # ------------------------------------------------------------------

    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag (required by project standards)."
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this log entry was created."
    )

    updated_at = models.DateTimeField(
        null=True,
        blank=True,
        default=None,
        help_text="Timestamp of last status update."
    )

    class Meta:
        db_table = "team2_notification_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user_id", "status"],
                name="idx_notif_log_user_status"
            ),
            models.Index(
                fields=["user_id", "-created_at"],
                name="idx_notif_log_user_date"
            ),
        ]
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"

    def __str__(self):
        return (
            f"NotificationLog(user={self.user_id}, "
            f"title='{self.title}', "
            f"status={self.status})"
        )

