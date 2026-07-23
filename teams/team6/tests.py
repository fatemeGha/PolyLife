from rest_framework import status

from .exceptions import GroupNotFoundError
from .responses import error_response, success_response
from unittest.mock import patch

from django.test import SimpleTestCase

from .models import (
    FitnessLevel,
    InjurySeverity,
    WorkoutType,
)
from .serializers import (
    GroupRecommendationRequestSerializer,
    UserProfileWriteSerializer,
    WorkoutPreferenceSerializer,
)


class WorkoutPreferenceSerializerTests(SimpleTestCase):
    def test_valid_workout_preference(self):
        serializer = WorkoutPreferenceSerializer(
            data={
                "workout_type": WorkoutType.RUNNING,
                "available_days": ["saturday", "monday"],
                "equipment": ["exercise_mat"],
                "preferred_start_time": "16:00",
                "preferred_end_time": "18:00",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_end_time_must_be_after_start_time(self):
        serializer = WorkoutPreferenceSerializer(
            data={
                "workout_type": WorkoutType.RUNNING,
                "available_days": ["saturday"],
                "equipment": [],
                "preferred_start_time": "18:00",
                "preferred_end_time": "16:00",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "preferred_end_time",
            serializer.errors,
        )


class GroupRecommendationRequestSerializerTests(SimpleTestCase):
    @patch(
        "teams.team6.serializers."
        "FitnessGoal.objects.filter"
    )
    def test_valid_recommendation_request(
        self,
        mock_filter,
    ):
        mock_filter.return_value.exists.return_value = True

        serializer = GroupRecommendationRequestSerializer(
            data={
                "goal_id": 1,
                "fitness_level": FitnessLevel.BEGINNER,
                "workout_type": WorkoutType.RUNNING,
                "available_days": [
                    " Saturday ",
                    "MONDAY",
                ],
                "preferred_start_time": "16:00",
                "preferred_end_time": "18:00",
                "equipment": ["exercise_mat"],
                "physical_limitations": [
                    {
                        "body_part": "knee",
                        "severity": InjurySeverity.MILD,
                    }
                ],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        self.assertEqual(
            serializer.validated_data["available_days"],
            ["saturday", "monday"],
        )

    @patch(
        "teams.team6.serializers."
        "FitnessGoal.objects.filter"
    )
    def test_goal_must_exist(
        self,
        mock_filter,
    ):
        mock_filter.return_value.exists.return_value = False

        serializer = GroupRecommendationRequestSerializer(
            data={
                "goal_id": 999,
                "fitness_level": FitnessLevel.BEGINNER,
                "workout_type": WorkoutType.RUNNING,
                "available_days": ["saturday"],
                "preferred_start_time": "16:00",
                "preferred_end_time": "18:00",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("goal_id", serializer.errors)

    @patch(
        "teams.team6.serializers."
        "FitnessGoal.objects.filter"
    )
    def test_duplicate_available_days_are_rejected(
        self,
        mock_filter,
    ):
        mock_filter.return_value.exists.return_value = True

        serializer = GroupRecommendationRequestSerializer(
            data={
                "goal_id": 1,
                "fitness_level": FitnessLevel.BEGINNER,
                "workout_type": WorkoutType.RUNNING,
                "available_days": [
                    "saturday",
                    "SATURDAY",
                ],
                "preferred_start_time": "16:00",
                "preferred_end_time": "18:00",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "available_days",
            serializer.errors,
        )

    @patch(
        "teams.team6.serializers."
        "FitnessGoal.objects.filter"
    )
    def test_invalid_time_range_is_rejected(
        self,
        mock_filter,
    ):
        mock_filter.return_value.exists.return_value = True

        serializer = GroupRecommendationRequestSerializer(
            data={
                "goal_id": 1,
                "fitness_level": FitnessLevel.BEGINNER,
                "workout_type": WorkoutType.RUNNING,
                "available_days": ["saturday"],
                "preferred_start_time": "18:00",
                "preferred_end_time": "16:00",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn(
            "preferred_end_time",
            serializer.errors,
        )


class UserProfileWriteSerializerTests(SimpleTestCase):
    @patch(
        "teams.team6.serializers."
        "FitnessGoal.objects.filter"
    )
    def test_valid_profile_data(
        self,
        mock_filter,
    ):
        mock_filter.return_value.values_list.return_value = [1]

        serializer = UserProfileWriteSerializer(
            data={
                "age": 24,
                "height": 175.0,
                "weight": 72.5,
                "fitness_level": FitnessLevel.BEGINNER,
                "goal_ids": [1],
                "workout_preference": {
                    "workout_type": WorkoutType.RUNNING,
                    "available_days": [
                        "saturday",
                        "monday",
                    ],
                    "equipment": ["exercise_mat"],
                    "preferred_start_time": "16:00",
                    "preferred_end_time": "18:00",
                },
                "injury_history": [
                    {
                        "injury_type": "Previous knee injury",
                        "body_part": "knee",
                        "severity": InjurySeverity.MILD,
                        "injury_date": "2025-05-15",
                        "notes": "Occasional pain.",
                    }
                ],
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_duplicate_goal_ids_are_rejected(self):
        serializer = UserProfileWriteSerializer(
            data={
                "age": 24,
                "height": 175.0,
                "weight": 72.5,
                "fitness_level": FitnessLevel.BEGINNER,
                "goal_ids": [1, 1],
                "workout_preference": {
                    "workout_type": WorkoutType.RUNNING,
                    "available_days": ["saturday"],
                    "equipment": [],
                    "preferred_start_time": "16:00",
                    "preferred_end_time": "18:00",
                },
                "injury_history": [],
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("goal_ids", serializer.errors)
        
class ResponseHelperTests(SimpleTestCase):
    def test_success_response_structure(self):
        response = success_response(
            message="Data retrieved successfully",
            data={"id": 1},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["data"],
            {"id": 1},
        )

    def test_error_response_structure(self):
        error = GroupNotFoundError()

        response = error_response(
            code=error.code,
            message=error.message,
            details=error.details,
            status_code=error.status_code,
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertFalse(response.data["success"])
        self.assertEqual(
            response.data["error"]["code"],
            "GROUP_NOT_FOUND",
        )