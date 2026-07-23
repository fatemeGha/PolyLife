from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class FitnessLevel(models.TextChoices):
    BEGINNER = "beginner", "Beginner"
    INTERMEDIATE = "intermediate", "Intermediate"
    ADVANCED = "advanced", "Advanced"


class WorkoutType(models.TextChoices):
    GYM = "gym", "Gym"
    RUNNING = "running", "Running"
    SWIMMING = "swimming", "Swimming"
    CYCLING = "cycling", "Cycling"
    YOGA = "yoga", "Yoga"
    HIIT = "hiit", "HIIT"
    CROSSFIT = "crossfit", "CrossFit"
    HOME_WORKOUT = "home_workout", "Home Workout"


class DifficultyLevel(models.TextChoices):
    EASY = "easy", "Easy"
    MEDIUM = "medium", "Medium"
    HARD = "hard", "Hard"


class RiskLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class InjurySeverity(models.TextChoices):
    MILD = "mild", "Mild"
    MODERATE = "moderate", "Moderate"
    SEVERE = "severe", "Severe"


class MembershipStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    ACTIVE = "active", "Active"
    LEFT = "left", "Left"
    REJECTED = "rejected", "Rejected"


class UserProfile(models.Model):
    """
    Team 6 fitness profile.

    The real user is managed by Core. We only store the trusted Core user ID
    received through the X-User-Id Gateway header.
    """

    core_user_id = models.PositiveBigIntegerField(
    unique=True,
    validators=[MinValueValidator(1)],
)
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1)],
    )
    height = models.FloatField(
        validators=[MinValueValidator(0.01)],
    )
    weight = models.FloatField(
        validators=[MinValueValidator(0.01)],
    )
    fitness_level = models.CharField(
        max_length=20,
        choices=FitnessLevel.choices,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(core_user_id__gt=0),
                name="team6_user_core_id_positive",
            ),
            models.CheckConstraint(
                condition=Q(age__gt=0),
                name="team6_user_age_positive",
            ),
            models.CheckConstraint(
                condition=Q(height__gt=0),
                name="team6_user_height_positive",
            ),
            models.CheckConstraint(
                condition=Q(weight__gt=0),
                name="team6_user_weight_positive",
            ),
        ]

    def __str__(self) -> str:
        return f"UserProfile(core_user_id={self.core_user_id})"


class FitnessGoal(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )
    description = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class UserGoal(models.Model):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="user_goals",
    )
    goal = models.ForeignKey(
        FitnessGoal,
        on_delete=models.PROTECT,
        related_name="user_goals",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_profile", "goal"],
                name="team6_unique_user_goal",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_profile.core_user_id} - {self.goal.name}"


class WorkoutPreference(models.Model):
    user_profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="workout_preference",
    )
    workout_type = models.CharField(
        max_length=30,
        choices=WorkoutType.choices,
    )
    available_days = models.JSONField(
        default=list,
    )
    equipment = models.JSONField(
        default=list,
        blank=True,
    )
    preferred_start_time = models.TimeField()
    preferred_end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    preferred_end_time__gt=F("preferred_start_time")
                ),
                name="team6_preference_valid_time_range",
            ),
        ]

    def __str__(self) -> str:
        return f"Preference({self.user_profile.core_user_id})"


class TrainingGroup(models.Model):
    name = models.CharField(
        max_length=150,
    )
    description = models.TextField(
        blank=True,
    )
    workout_type = models.CharField(
        max_length=30,
        choices=WorkoutType.choices,
        db_index=True,
    )
    difficulty_level = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
        db_index=True,
    )
    goal = models.ForeignKey(
        FitnessGoal,
        on_delete=models.PROTECT,
        related_name="training_groups",
    )
    max_members = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    available_days = models.JSONField(
        default=list,
    )
    equipment = models.JSONField(
        default=list,
        blank=True,
    )
    start_time = models.TimeField()
    end_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=Q(max_members__gt=0),
                name="team6_group_positive_capacity",
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="team6_group_valid_time_range",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class GroupMembership(models.Model):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="group_memberships",
    )
    group = models.ForeignKey(
        TrainingGroup,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_profile", "group"],
                name="team6_unique_group_membership",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.user_profile.core_user_id} - "
            f"{self.group.name} - {self.status}"
        )


class Exercise(models.Model):
    name = models.CharField(
        max_length=150,
        unique=True,
    )
    type = models.CharField(
        max_length=30,
        choices=WorkoutType.choices,
    )
    difficulty = models.CharField(
        max_length=20,
        choices=DifficultyLevel.choices,
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class GroupExercise(models.Model):
    group = models.ForeignKey(
        TrainingGroup,
        on_delete=models.CASCADE,
        related_name="group_exercises",
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="group_exercises",
    )
    intensity = models.CharField(
        max_length=50,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["group", "exercise"],
                name="team6_unique_group_exercise",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.group.name} - {self.exercise.name}"


class InjuryHistory(models.Model):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="injury_history",
    )
    injury_type = models.CharField(
        max_length=150,
    )
    body_part = models.CharField(
        max_length=100,
        db_index=True,
    )
    severity = models.CharField(
        max_length=20,
        choices=InjurySeverity.choices,
    )
    injury_date = models.DateField()
    notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["-injury_date"]

    def __str__(self) -> str:
        return (
            f"{self.user_profile.core_user_id} - "
            f"{self.body_part} - {self.severity}"
        )


class RiskAnalysis(models.Model):
    user_profile = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="risk_analyses",
    )
    group = models.ForeignKey(
        TrainingGroup,
        on_delete=models.CASCADE,
        related_name="risk_analyses",
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RiskLevel.choices,
        db_index=True,
    )
    score = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ],
    )
    recommendation = models.TextField(
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(score__gte=0) & Q(score__lte=100),
                name="team6_risk_score_range",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.user_profile.core_user_id} - "
            f"{self.group.name} - {self.score}"
        )