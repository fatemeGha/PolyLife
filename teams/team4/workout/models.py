from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class Exercise(BaseModel):

    LEVELS = [
        ("beginner","Beginner"),
        ("intermediate","Intermediate"),
        ("advanced","Advanced"),
    ]

    EQUIPMENT = [
        ("none","None"),
        ("dumbbell","Dumbbell"),
        ("barbell","Barbell"),
        ("machine","Machine"),
    ]

    title=models.CharField(max_length=200)

    description=models.TextField()

    target_muscle=models.CharField(max_length=100)

    difficulty=models.CharField(max_length=20,choices=LEVELS)

    equipment=models.CharField(max_length=50,choices=EQUIPMENT)

    duration=models.PositiveIntegerField()

    calories=models.PositiveIntegerField()

    image=models.ImageField(upload_to="exercise/images/",null=True,blank=True)

    video=models.URLField(blank=True)


class WorkoutProgram(BaseModel):

    title=models.CharField(max_length=200)

    description=models.TextField()

    difficulty=models.CharField(max_length=20)

    duration=models.PositiveIntegerField()


class WorkoutExercise(BaseModel):

    workout=models.ForeignKey(
        WorkoutProgram,
        on_delete=models.CASCADE,
        related_name="exercises"
    )

    exercise=models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE
    )

    order=models.PositiveIntegerField()

    repeat=models.PositiveIntegerField(default=1)

    sets=models.PositiveIntegerField(default=1)

class UserPreference(BaseModel):

    GOALS=[
        ("fat_loss","Fat Loss"),
        ("muscle_gain","Muscle Gain"),
        ("fitness","Fitness")
    ]

    user_id=models.IntegerField(unique=True)

    goal=models.CharField(max_length=30,choices=GOALS)

    level=models.CharField(max_length=30)

    equipment=models.CharField(max_length=50)


class Favorite(BaseModel):

    user_id=models.IntegerField()

    workout=models.ForeignKey(
        WorkoutProgram,
        on_delete=models.CASCADE
    )

class WorkoutHistory(BaseModel):

    user_id=models.IntegerField()

    workout=models.ForeignKey(
        WorkoutProgram,
        on_delete=models.CASCADE
    )

    completed=models.BooleanField(default=False)

    duration=models.PositiveIntegerField()

    completed_at=models.DateTimeField(null=True, blank=True)

