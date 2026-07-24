from rest_framework import serializers

from .models import (
    DifficultyLevel,
    Exercise,
    FitnessGoal,
    FitnessLevel,
    GroupExercise,
    GroupMembership,
    InjuryHistory,
    InjurySeverity,
    MembershipStatus,
    RiskAnalysis,
    RiskLevel,
    TrainingGroup,
    UserGoal,
    UserProfile,
    WorkoutPreference,
    WorkoutType,
)


class FitnessGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = FitnessGoal
        fields = [
            "id",
            "name",
            "description",
        ]


class WorkoutPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkoutPreference
        fields = [
            "workout_type",
            "available_days",
            "equipment",
            "preferred_start_time",
            "preferred_end_time",
        ]

    def validate(self, attrs):
        instance = getattr(self, "instance", None)

        start_time = attrs.get(
            "preferred_start_time",
            getattr(instance, "preferred_start_time", None),
        )
        end_time = attrs.get(
            "preferred_end_time",
            getattr(instance, "preferred_end_time", None),
        )

        if start_time and end_time and end_time <= start_time:
            raise serializers.ValidationError(
                {
                    "preferred_end_time": (
                        "End time must be later than start time."
                    )
                }
            )

        return attrs


class InjuryHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InjuryHistory
        fields = [
            "id",
            "injury_type",
            "body_part",
            "severity",
            "injury_date",
            "notes",
        ]
        read_only_fields = ["id"]


class UserProfileReadSerializer(serializers.ModelSerializer):
    goals = serializers.SerializerMethodField()
    workout_preference = serializers.SerializerMethodField()
    injury_history = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "core_user_id",
            "age",
            "height",
            "weight",
            "fitness_level",
            "goals",
            "workout_preference",
            "injury_history",
            "created_at",
            "updated_at",
        ]

    def get_goals(self, obj):
        user_goals = (
            UserGoal.objects
            .filter(user=obj)
            .select_related("goal")
            .order_by("goal__name")
        )

        goals = [user_goal.goal for user_goal in user_goals]

        return FitnessGoalSerializer(goals, many=True).data

    def get_workout_preference(self, obj):
        preference = WorkoutPreference.objects.filter(user=obj).first()

        if preference is None:
            return None

        return WorkoutPreferenceSerializer(preference).data

    def get_injury_history(self, obj):
        injuries = (
            InjuryHistory.objects
            .filter(user=obj)
            .order_by("-injury_date", "-id")
        )

        return InjuryHistorySerializer(injuries, many=True).data


class UserProfileWriteSerializer(serializers.Serializer):
    age = serializers.IntegerField(min_value=1)
    height = serializers.FloatField(min_value=0.01)
    weight = serializers.FloatField(min_value=0.01)

    fitness_level = serializers.ChoiceField(
        choices=FitnessLevel.choices,
    )

    goal_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )

    workout_preference = WorkoutPreferenceSerializer()

    injury_history = InjuryHistorySerializer(
        many=True,
        required=False,
        default=list,
    )

    def validate_goal_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate fitness goal IDs are not allowed."
            )

        existing_goal_ids = set(
            FitnessGoal.objects.filter(id__in=value)
            .values_list("id", flat=True)
        )

        missing_goal_ids = sorted(set(value) - existing_goal_ids)

        if missing_goal_ids:
            raise serializers.ValidationError(
                f"Fitness goals were not found: {missing_goal_ids}"
            )

        return value


class PhysicalLimitationSerializer(serializers.Serializer):
    body_part = serializers.CharField(max_length=100)

    severity = serializers.ChoiceField(
        choices=InjurySeverity.choices,
    )


class GroupRecommendationRequestSerializer(serializers.Serializer):
    goal_id = serializers.IntegerField(min_value=1)

    fitness_level = serializers.ChoiceField(
        choices=FitnessLevel.choices,
    )

    workout_type = serializers.ChoiceField(
        choices=WorkoutType.choices,
    )

    available_days = serializers.ListField(
        child=serializers.CharField(max_length=20),
        allow_empty=False,
    )

    preferred_start_time = serializers.TimeField()
    preferred_end_time = serializers.TimeField()

    equipment = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )

    physical_limitations = PhysicalLimitationSerializer(
        many=True,
        required=False,
        default=list,
    )

    def validate_goal_id(self, value):
        if not FitnessGoal.objects.filter(id=value).exists():
            raise serializers.ValidationError(
                "Fitness goal was not found."
            )

        return value

    def validate_available_days(self, value):
        normalized_days = [
            day.strip().lower()
            for day in value
            if day.strip()
        ]

        if not normalized_days:
            raise serializers.ValidationError(
                "At least one available day is required."
            )

        if len(normalized_days) != len(set(normalized_days)):
            raise serializers.ValidationError(
                "Duplicate available days are not allowed."
            )

        return normalized_days

    def validate(self, attrs):
        start_time = attrs["preferred_start_time"]
        end_time = attrs["preferred_end_time"]

        if end_time <= start_time:
            raise serializers.ValidationError(
                {
                    "preferred_end_time": (
                        "End time must be later than start time."
                    )
                }
            )

        return attrs


class RiskAnalysisRequestSerializer(serializers.Serializer):
    group_id = serializers.IntegerField(min_value=1)


class MembershipCreateSerializer(serializers.Serializer):
    group_id = serializers.IntegerField(min_value=1)


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            "id",
            "name",
            "type",
            "difficulty",
            "risk_level",
        ]


class TrainingGroupListSerializer(serializers.ModelSerializer):
    goal = FitnessGoalSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    is_full = serializers.SerializerMethodField()

    class Meta:
        model = TrainingGroup
        fields = [
            "id",
            "name",
            "description",
            "goal",
            "workout_type",
            "difficulty_level",
            "available_days",
            "equipment",
            "start_time",
            "end_time",
            "member_count",
            "max_members",
            "is_full",
            "created_at",
        ]

    def get_member_count(self, obj):
        return GroupMembership.objects.filter(
            group=obj,
            status=MembershipStatus.ACTIVE,
        ).count()

    def get_is_full(self, obj):
        member_count = self.get_member_count(obj)
        return member_count >= obj.max_members


class TrainingGroupDetailSerializer(
    TrainingGroupListSerializer
):
    exercises = serializers.SerializerMethodField()

    class Meta(TrainingGroupListSerializer.Meta):
        fields = [
            *TrainingGroupListSerializer.Meta.fields,
            "exercises",
        ]

    def get_exercises(self, obj):
        group_exercises = (
            GroupExercise.objects
            .filter(group=obj)
            .select_related("exercise")
            .order_by("id")
        )

        return [
            {
                "id": group_exercise.exercise.id,
                "name": group_exercise.exercise.name,
                "type": group_exercise.exercise.type,
                "difficulty": (
                    group_exercise.exercise.difficulty
                ),
                "intensity": group_exercise.intensity,
                "risk_level": (
                    group_exercise.exercise.risk_level
                ),
            }
            for group_exercise in group_exercises
        ]


class TrainingGroupSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = TrainingGroup
        fields = [
            "id",
            "name",
            "workout_type",
        ]


class GroupMembershipReadSerializer(serializers.ModelSerializer):
    group = TrainingGroupSummarySerializer(read_only=True)

    class Meta:
        model = GroupMembership
        fields = [
            "id",
            "status",
            "joined_at",
            "group",
        ]


class RiskAnalysisReadSerializer(serializers.ModelSerializer):
    group_id = serializers.IntegerField(
        source="group.id",
        read_only=True,
    )

    class Meta:
        model = RiskAnalysis
        fields = [
            "id",
            "group_id",
            "score",
            "risk_level",
            "recommendation",
            "created_at",
        ]