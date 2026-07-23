from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView

from .exceptions import (
    AuthHeadersMissingError,
    ProfileAlreadyExistsError,
    ProfileNotFoundError,
    Team6ServiceError,
    ValidationServiceError,
)
from .models import (
    FitnessGoal,
    InjuryHistory,
    UserGoal,
    UserProfile,
    WorkoutPreference,
)
from .responses import (
    error_response,
    success_response,
    validation_error_response,
)
from .serializers import (
    UserProfileReadSerializer,
    UserProfileWriteSerializer,
)


def _service_error_response(error):
    return error_response(
        code=error.code,
        message=error.message,
        details=error.details,
        status_code=error.status_code,
    )


def _get_gateway_user(request):
    raw_user_id = request.headers.get("X-User-Id")
    username = request.headers.get("X-User-Username")

    missing_headers = []

    if not raw_user_id:
        missing_headers.append("X-User-Id")

    if not username:
        missing_headers.append("X-User-Username")

    if missing_headers:
        raise AuthHeadersMissingError(
            details={
                "missing_headers": missing_headers,
            }
        )

    try:
        core_user_id = int(raw_user_id)
    except (TypeError, ValueError) as exc:
        raise ValidationServiceError(
            message="X-User-Id must be a valid integer.",
            details={
                "X-User-Id": [
                    "A positive integer is required."
                ]
            },
        ) from exc

    if core_user_id <= 0:
        raise ValidationServiceError(
            message="X-User-Id must be greater than zero.",
            details={
                "X-User-Id": [
                    "A positive integer is required."
                ]
            },
        )

    return core_user_id, username


def _get_profile(core_user_id):
    try:
        return UserProfile.objects.get(
            core_user_id=core_user_id,
        )
    except UserProfile.DoesNotExist as exc:
        raise ProfileNotFoundError() from exc


def _replace_goals(*, profile, goal_ids):
    goals_by_id = FitnessGoal.objects.in_bulk(
        goal_ids
    )

    UserGoal.objects.filter(
        user=profile,
    ).delete()

    UserGoal.objects.bulk_create(
        [
            UserGoal(
                user=profile,
                goal=goals_by_id[goal_id],
            )
            for goal_id in goal_ids
        ]
    )


def _save_workout_preference(
    *,
    profile,
    preference_data,
):
    WorkoutPreference.objects.update_or_create(
        user=profile,
        defaults=preference_data,
    )


def _replace_injury_history(
    *,
    profile,
    injuries,
):
    InjuryHistory.objects.filter(
        user=profile,
    ).delete()

    InjuryHistory.objects.bulk_create(
        [
            InjuryHistory(
                user=profile,
                **injury_data,
            )
            for injury_data in injuries
        ]
    )


def _profile_summary(profile):
    return {
        "id": profile.id,
        "core_user_id": profile.core_user_id,
        "age": profile.age,
        "height": profile.height,
        "weight": profile.weight,
        "fitness_level": profile.fitness_level,
    }


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return success_response(
            message="Team 6 service is healthy",
            data={
                "service": "team6",
                "status": "healthy",
            },
        )


class ProfileView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        try:
            core_user_id, _ = _get_gateway_user(
                request
            )

            profile = _get_profile(core_user_id)

            serializer = UserProfileReadSerializer(
                profile
            )

            return success_response(
                message=(
                    "Fitness profile retrieved "
                    "successfully"
                ),
                data={
                    "profile": serializer.data,
                },
            )

        except Team6ServiceError as error:
            return _service_error_response(error)

    def post(self, request):
        try:
            core_user_id, _ = _get_gateway_user(
                request
            )

            if UserProfile.objects.filter(
                core_user_id=core_user_id,
            ).exists():
                raise ProfileAlreadyExistsError()

            serializer = UserProfileWriteSerializer(
                data=request.data
            )

            if not serializer.is_valid():
                return validation_error_response(
                    serializer.errors
                )

            validated_data = serializer.validated_data

            with transaction.atomic():
                profile = UserProfile.objects.create(
                    core_user_id=core_user_id,
                    age=validated_data["age"],
                    height=validated_data["height"],
                    weight=validated_data["weight"],
                    fitness_level=(
                        validated_data["fitness_level"]
                    ),
                )

                _replace_goals(
                    profile=profile,
                    goal_ids=validated_data["goal_ids"],
                )

                _save_workout_preference(
                    profile=profile,
                    preference_data=(
                        validated_data[
                            "workout_preference"
                        ]
                    ),
                )

                _replace_injury_history(
                    profile=profile,
                    injuries=validated_data.get(
                        "injury_history",
                        [],
                    ),
                )

            return success_response(
                message=(
                    "Fitness profile created "
                    "successfully"
                ),
                data={
                    "profile": _profile_summary(
                        profile
                    ),
                },
                status_code=status.HTTP_201_CREATED,
            )

        except Team6ServiceError as error:
            return _service_error_response(error)

    def patch(self, request):
        try:
            core_user_id, _ = _get_gateway_user(
                request
            )

            profile = _get_profile(core_user_id)

            serializer = UserProfileWriteSerializer(
                data=request.data,
                partial=True,
            )

            if not serializer.is_valid():
                return validation_error_response(
                    serializer.errors
                )

            validated_data = serializer.validated_data

            if not validated_data:
                return validation_error_response(
                    {
                        "non_field_errors": [
                            "At least one valid field "
                            "is required."
                        ]
                    }
                )

            with transaction.atomic():
                updated_fields = []

                for field_name in [
                    "age",
                    "height",
                    "weight",
                    "fitness_level",
                ]:
                    if field_name in validated_data:
                        setattr(
                            profile,
                            field_name,
                            validated_data[field_name],
                        )
                        updated_fields.append(field_name)

                if "goal_ids" in validated_data:
                    _replace_goals(
                        profile=profile,
                        goal_ids=(
                            validated_data["goal_ids"]
                        ),
                    )

                if (
                    "workout_preference"
                    in validated_data
                ):
                    _save_workout_preference(
                        profile=profile,
                        preference_data=(
                            validated_data[
                                "workout_preference"
                            ]
                        ),
                    )

                if "injury_history" in validated_data:
                    _replace_injury_history(
                        profile=profile,
                        injuries=(
                            validated_data[
                                "injury_history"
                            ]
                        ),
                    )

                profile.save(
                    update_fields=[
                        *updated_fields,
                        "updated_at",
                    ]
                )

            return success_response(
                message=(
                    "Fitness profile updated "
                    "successfully"
                ),
                data={
                    "profile": _profile_summary(
                        profile
                    ),
                },
            )

        except Team6ServiceError as error:
            return _service_error_response(error)

    def delete(self, request):
        try:
            core_user_id, _ = _get_gateway_user(
                request
            )

            profile = _get_profile(core_user_id)
            profile.delete()

            return success_response(
                message=(
                    "Fitness profile deleted "
                    "successfully"
                ),
                data={},
            )

        except Team6ServiceError as error:
            return _service_error_response(error)