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
