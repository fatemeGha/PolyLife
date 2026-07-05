from rest_framework import serializers

from .models import (
    Exercise,
    WorkoutProgram,
    WorkoutExercise,
    WorkoutHistory,
    Favorite,
    UserPreference,
)


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = "__all__"


class WorkoutExerciseSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)

    class Meta:
        model = WorkoutExercise
        fields = "__all__"


class WorkoutProgramSerializer(serializers.ModelSerializer):
    exercises = WorkoutExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutProgram
        fields = "__all__"


class WorkoutHistorySerializer(serializers.ModelSerializer):

    workout = WorkoutProgramSerializer(read_only=True)

    workout_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkoutProgram.objects.all(),
        source="workout",
        write_only=True
    )

    class Meta:

        model = WorkoutHistory

        fields = [

            "id",

            "user_id",

            "workout",

            "workout_id",

            "duration",

            "completed",

            "completed_at",

            "created_at",

            "updated_at",

        ]

        read_only_fields = (

            "id",

            "user_id",

            "completed_at",

            "created_at",

            "updated_at",

        )

class FavoriteSerializer(serializers.ModelSerializer):

    workout = WorkoutProgramSerializer(read_only=True)

    workout_id = serializers.PrimaryKeyRelatedField(
        queryset=WorkoutProgram.objects.all(),
        source="workout",
        write_only=True
    )

    class Meta:
        model = Favorite
        fields = (
            "id",
            "user_id",
            "workout",
            "workout_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user_id",
            "workout",
            "created_at",
            "updated_at",
        )

class UserPreferenceSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserPreference
        fields = "__all__"
        read_only_fields = ("user_id",)