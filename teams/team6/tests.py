from rest_framework import status
from types import SimpleNamespace
from .exceptions import GroupNotFoundError
from .responses import error_response, success_response
from contextlib import nullcontext
from unittest.mock import MagicMock, patch
from .services.risk_service import analyze_group_risk
from django.test import SimpleTestCase
from datetime import time
from .services.matching_service import recommend_groups
from rest_framework.test import APIRequestFactory
from .views import (
    GroupRecommendationView,
    HealthView,
    ProfileView,
    RiskAnalysisView,
    TrainingGroupDetailView,
    TrainingGroupListView,
)

from .models import (
    FitnessLevel,
    InjurySeverity,
    WorkoutType,
    DifficultyLevel,
    RiskLevel,
    MembershipStatus,
)
from .serializers import (
    GroupRecommendationRequestSerializer,
    UserProfileWriteSerializer,
    WorkoutPreferenceSerializer,
)

from .exceptions import (
    AlreadyMemberError,
    GroupFullError,
    GroupNotFoundError,
    HighRiskGroupError,
)
from .services.membership_service import (
    join_group,
    leave_group,
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
class RiskServiceTests(SimpleTestCase):
    @patch(
        "teams.team6.services.risk_service."
        "_get_user_injuries"
    )
    @patch(
        "teams.team6.services.risk_service."
        "_get_group_exercises"
    )
    def test_low_risk_without_injury(
        self,
        mock_group_exercises,
        mock_injuries,
    ):
        user = SimpleNamespace(
            id=1,
            fitness_level=FitnessLevel.BEGINNER,
        )

        group = SimpleNamespace(
            id=7,
            name="Beginner Running Group",
            workout_type=WorkoutType.RUNNING,
            difficulty_level=DifficultyLevel.EASY,
        )

        exercise = SimpleNamespace(
            id=4,
            name="Light Running",
            type=WorkoutType.RUNNING,
            risk_level=RiskLevel.LOW,
        )

        group_exercise = SimpleNamespace(
            exercise=exercise,
            intensity="low",
        )

        mock_group_exercises.return_value = [
            group_exercise
        ]
        mock_injuries.return_value = []

        result = analyze_group_risk(
            user=user,
            group=group,
            persist=False,
        )

        self.assertEqual(result["level"], RiskLevel.LOW)
        self.assertTrue(result["is_safe"])
        self.assertEqual(result["score"], 10)

    @patch(
        "teams.team6.services.risk_service."
        "_get_user_injuries"
    )
    @patch(
        "teams.team6.services.risk_service."
        "_get_group_exercises"
    )
    def test_high_risk_for_severe_injury(
        self,
        mock_group_exercises,
        mock_injuries,
    ):
        user = SimpleNamespace(
            id=1,
            fitness_level=FitnessLevel.BEGINNER,
        )

        group = SimpleNamespace(
            id=7,
            name="Advanced Running Group",
            workout_type=WorkoutType.RUNNING,
            difficulty_level=DifficultyLevel.HARD,
        )

        exercise = SimpleNamespace(
            id=4,
            name="High Intensity Running",
            type=WorkoutType.RUNNING,
            risk_level=RiskLevel.HIGH,
        )

        group_exercise = SimpleNamespace(
            exercise=exercise,
            intensity="high",
        )

        injury = SimpleNamespace(
            injury_type="Previous knee injury",
            body_part="knee",
            severity=InjurySeverity.SEVERE,
        )

        mock_group_exercises.return_value = [
            group_exercise
        ]
        mock_injuries.return_value = [injury]

        result = analyze_group_risk(
            user=user,
            group=group,
            persist=False,
        )

        self.assertEqual(result["level"], RiskLevel.HIGH)
        self.assertFalse(result["is_safe"])
        self.assertEqual(result["score"], 100)
        self.assertTrue(result["reasons"])

    @patch(
        "teams.team6.services.risk_service."
        "RiskAnalysis.objects.create"
    )
    @patch(
        "teams.team6.services.risk_service."
        "_get_user_injuries"
    )
    @patch(
        "teams.team6.services.risk_service."
        "_get_group_exercises"
    )
    def test_analysis_is_persisted(
        self,
        mock_group_exercises,
        mock_injuries,
        mock_create,
    ):
        user = SimpleNamespace(
            id=1,
            fitness_level=FitnessLevel.ADVANCED,
        )

        group = SimpleNamespace(
            id=7,
            name="Easy Yoga Group",
            workout_type=WorkoutType.YOGA,
            difficulty_level=DifficultyLevel.EASY,
        )

        exercise = SimpleNamespace(
            id=4,
            name="Light Yoga",
            type=WorkoutType.YOGA,
            risk_level=RiskLevel.LOW,
        )

        mock_group_exercises.return_value = [
            SimpleNamespace(
                exercise=exercise,
                intensity="low",
            )
        ]
        mock_injuries.return_value = []

        result = analyze_group_risk(
            user=user,
            group=group,
            persist=True,
        )

        mock_create.assert_called_once_with(
            user=user,
            group=group,
            risk_level=RiskLevel.LOW,
            score=10,
            recommendation=(
                "This group is suitable for the user."
            ),
        )

        self.assertEqual(result["level"], RiskLevel.LOW)
class MatchingServiceTests(SimpleTestCase):
    @patch(
        "teams.team6.services.matching_service."
        "analyze_group_risk"
    )
    @patch(
        "teams.team6.services.matching_service."
        "_get_active_member_count"
    )
    @patch(
        "teams.team6.services.matching_service."
        "_get_candidate_groups"
    )
    def test_exact_matching_group_is_recommended(
        self,
        mock_candidate_groups,
        mock_member_count,
        mock_risk_analysis,
    ):
        user = SimpleNamespace(
            id=1,
            fitness_level=FitnessLevel.BEGINNER,
        )

        group = SimpleNamespace(
            id=7,
            goal_id=1,
            name="Beginner Running Group",
            workout_type=WorkoutType.RUNNING,
            difficulty_level=DifficultyLevel.EASY,
            available_days=[
                "saturday",
                "monday",
            ],
            equipment=["exercise_mat"],
            start_time=time(16, 0),
            end_time=time(18, 0),
            max_members=15,
        )

        mock_candidate_groups.return_value = [group]
        mock_member_count.return_value = 8
        mock_risk_analysis.return_value = {
            "group_id": 7,
            "score": 20,
            "level": RiskLevel.LOW,
            "is_safe": True,
            "reasons": [],
            "recommendation": (
                "This group is suitable for the user."
            ),
        }

        results = recommend_groups(
            user=user,
            goal_id=1,
            fitness_level=FitnessLevel.BEGINNER,
            workout_type=WorkoutType.RUNNING,
            available_days=[
                "saturday",
                "monday",
            ],
            preferred_start_time=time(16, 0),
            preferred_end_time=time(18, 0),
            equipment=["exercise_mat"],
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(
            results[0]["match_score"],
            100,
        )
        self.assertEqual(
            results[0]["member_count"],
            8,
        )
        self.assertEqual(
            results[0]["group"],
            group,
        )

    @patch(
        "teams.team6.services.matching_service."
        "analyze_group_risk"
    )
    @patch(
        "teams.team6.services.matching_service."
        "_get_active_member_count"
    )
    @patch(
        "teams.team6.services.matching_service."
        "_get_candidate_groups"
    )
    def test_high_risk_group_is_excluded(
        self,
        mock_candidate_groups,
        mock_member_count,
        mock_risk_analysis,
    ):
        user = SimpleNamespace(
            id=1,
            fitness_level=FitnessLevel.BEGINNER,
        )

        group = SimpleNamespace(
            id=7,
            goal_id=1,
            name="Risky Running Group",
            workout_type=WorkoutType.RUNNING,
            difficulty_level=DifficultyLevel.EASY,
            available_days=["saturday"],
            equipment=[],
            start_time=time(16, 0),
            end_time=time(18, 0),
            max_members=15,
        )

        mock_candidate_groups.return_value = [group]
        mock_member_count.return_value = 5
        mock_risk_analysis.return_value = {
            "group_id": 7,
            "score": 85,
            "level": RiskLevel.HIGH,
            "is_safe": False,
            "reasons": [],
            "recommendation": (
                "Joining this group is not recommended."
            ),
        }

        results = recommend_groups(
            user=user,
            goal_id=1,
            fitness_level=FitnessLevel.BEGINNER,
            workout_type=WorkoutType.RUNNING,
            available_days=["saturday"],
            preferred_start_time=time(16, 0),
            preferred_end_time=time(18, 0),
            equipment=[],
        )

        self.assertEqual(results, [])

    @patch(
        "teams.team6.services.matching_service."
        "analyze_group_risk"
    )
    @patch(
        "teams.team6.services.matching_service."
        "_get_active_member_count"
    )
    @patch(
        "teams.team6.services.matching_service."
        "_get_candidate_groups"
    )
    def test_full_group_is_excluded(
        self,
        mock_candidate_groups,
        mock_member_count,
        mock_risk_analysis,
    ):
        user = SimpleNamespace(
            id=1,
            fitness_level=FitnessLevel.BEGINNER,
        )

        group = SimpleNamespace(
            id=7,
            goal_id=1,
            name="Full Running Group",
            workout_type=WorkoutType.RUNNING,
            difficulty_level=DifficultyLevel.EASY,
            available_days=["saturday"],
            equipment=[],
            start_time=time(16, 0),
            end_time=time(18, 0),
            max_members=15,
        )

        mock_candidate_groups.return_value = [group]
        mock_member_count.return_value = 15

        results = recommend_groups(
            user=user,
            goal_id=1,
            fitness_level=FitnessLevel.BEGINNER,
            workout_type=WorkoutType.RUNNING,
            available_days=["saturday"],
            preferred_start_time=time(16, 0),
            preferred_end_time=time(18, 0),
            equipment=[],
        )

        self.assertEqual(results, [])
        mock_risk_analysis.assert_not_called()
class MembershipServiceTests(SimpleTestCase):
    def test_user_can_join_safe_group(self):
        user = SimpleNamespace(id=1)

        group = SimpleNamespace(
            id=7,
            pk=7,
            max_members=15,
        )

        membership = SimpleNamespace(
            id=4,
            status=MembershipStatus.ACTIVE,
        )

        safe_risk = {
            "group_id": 7,
            "score": 20,
            "level": RiskLevel.LOW,
            "is_safe": True,
            "reasons": [],
            "recommendation": (
                "This group is suitable for the user."
            ),
        }

        with (
            patch(
                "teams.team6.services."
                "membership_service."
                "_get_existing_membership",
                side_effect=[None, None],
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "_get_active_member_count",
                side_effect=[5, 5],
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "analyze_group_risk",
                return_value=safe_risk,
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "_lock_group",
                return_value=group,
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "GroupMembership.objects.create",
                return_value=membership,
            ) as mock_create,
            patch(
                "teams.team6.services."
                "membership_service."
                "transaction.atomic",
                return_value=nullcontext(),
            ),
        ):
            result = join_group(
                user=user,
                group=group,
            )

        mock_create.assert_called_once_with(
            user=user,
            group=group,
            status=MembershipStatus.ACTIVE,
        )

        self.assertEqual(
            result["membership"],
            membership,
        )
        self.assertEqual(
            result["risk"],
            safe_risk,
        )

    def test_active_member_cannot_join_again(self):
        user = SimpleNamespace(id=1)

        group = SimpleNamespace(
            id=7,
            max_members=15,
        )

        existing_membership = SimpleNamespace(
            status=MembershipStatus.ACTIVE,
        )

        with (
            patch(
                "teams.team6.services."
                "membership_service."
                "_get_existing_membership",
                return_value=existing_membership,
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "analyze_group_risk",
            ) as mock_risk,
        ):
            with self.assertRaises(
                AlreadyMemberError
            ):
                join_group(
                    user=user,
                    group=group,
                )

        mock_risk.assert_not_called()

    def test_user_cannot_join_full_group(self):
        user = SimpleNamespace(id=1)

        group = SimpleNamespace(
            id=7,
            max_members=15,
        )

        with (
            patch(
                "teams.team6.services."
                "membership_service."
                "_get_existing_membership",
                return_value=None,
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "_get_active_member_count",
                return_value=15,
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "analyze_group_risk",
            ) as mock_risk,
        ):
            with self.assertRaises(GroupFullError):
                join_group(
                    user=user,
                    group=group,
                )

        mock_risk.assert_not_called()

    def test_user_cannot_join_high_risk_group(self):
        user = SimpleNamespace(id=1)

        group = SimpleNamespace(
            id=7,
            max_members=15,
        )

        high_risk = {
            "group_id": 7,
            "score": 85,
            "level": RiskLevel.HIGH,
            "is_safe": False,
            "reasons": [],
            "recommendation": (
                "Joining this group is not recommended."
            ),
        }

        with (
            patch(
                "teams.team6.services."
                "membership_service."
                "_get_existing_membership",
                return_value=None,
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "_get_active_member_count",
                return_value=5,
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "analyze_group_risk",
                return_value=high_risk,
            ),
        ):
            with self.assertRaises(
                HighRiskGroupError
            ) as context:
                join_group(
                    user=user,
                    group=group,
                )

        self.assertEqual(
            context.exception.details,
            {
                "risk_score": 85,
                "risk_level": RiskLevel.HIGH,
            },
        )

    def test_leave_group_changes_status_to_left(self):
        user = SimpleNamespace(id=1)

        membership = MagicMock()
        membership.status = MembershipStatus.ACTIVE

        with (
            patch(
                "teams.team6.services."
                "membership_service."
                "_get_membership_for_update",
                return_value=membership,
            ),
            patch(
                "teams.team6.services."
                "membership_service."
                "transaction.atomic",
                return_value=nullcontext(),
            ),
        ):
            result = leave_group(
                user=user,
                membership_id=4,
            )

        self.assertEqual(
            membership.status,
            MembershipStatus.LEFT,
        )
        membership.save.assert_called_once_with(
            update_fields=["status"]
        )
        self.assertEqual(result, membership)
class ProfileViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.gateway_headers = {
            "HTTP_X_USER_ID": "15",
            "HTTP_X_USER_USERNAME": "murteza",
        }

    def test_health_endpoint_returns_success(self):
        request = self.factory.get("/health")

        response = HealthView.as_view()(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(
            response.data["data"]["status"],
            "healthy",
        )

    def test_profile_requires_gateway_headers(self):
        request = self.factory.get("/profile")

        response = ProfileView.as_view()(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertFalse(response.data["success"])
        self.assertEqual(
            response.data["error"]["code"],
            "AUTH_HEADERS_MISSING",
        )

    @patch("teams.team6.views.UserProfileReadSerializer")
    @patch("teams.team6.views._get_profile")
    def test_get_profile_returns_profile_data(
        self,
        mock_get_profile,
        mock_read_serializer,
    ):
        profile = SimpleNamespace(
            id=3,
            core_user_id=15,
        )

        mock_get_profile.return_value = profile
        mock_read_serializer.return_value.data = {
            "id": 3,
            "core_user_id": 15,
            "age": 24,
            "height": 175.0,
            "weight": 72.5,
            "fitness_level": FitnessLevel.BEGINNER,
        }

        request = self.factory.get(
            "/profile",
            **self.gateway_headers,
        )

        response = ProfileView.as_view()(request)

        mock_get_profile.assert_called_once_with(15)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["data"]["profile"]["id"],
            3,
        )

    @patch("teams.team6.views.UserProfile.objects.filter")
    def test_duplicate_profile_is_rejected(
        self,
        mock_filter,
    ):
        mock_filter.return_value.exists.return_value = True

        request = self.factory.post(
            "/profile",
            {},
            format="json",
            **self.gateway_headers,
        )

        response = ProfileView.as_view()(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_409_CONFLICT,
        )
        self.assertEqual(
            response.data["error"]["code"],
            "PROFILE_ALREADY_EXISTS",
        )

    @patch("teams.team6.views.UserProfile.objects.filter")
    def test_invalid_profile_data_is_rejected(
        self,
        mock_filter,
    ):
        mock_filter.return_value.exists.return_value = False

        request = self.factory.post(
            "/profile",
            {},
            format="json",
            **self.gateway_headers,
        )

        response = ProfileView.as_view()(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["error"]["code"],
            "VALIDATION_ERROR",
        )

    @patch("teams.team6.views._get_profile")
    def test_empty_patch_is_rejected(
        self,
        mock_get_profile,
    ):
        mock_get_profile.return_value = SimpleNamespace(
            id=3,
            core_user_id=15,
        )

        request = self.factory.patch(
            "/profile",
            {},
            format="json",
            **self.gateway_headers,
        )

        response = ProfileView.as_view()(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            response.data["error"]["code"],
            "VALIDATION_ERROR",
        )

    @patch("teams.team6.views._get_profile")
    def test_delete_profile_returns_success(
        self,
        mock_get_profile,
    ):
        profile = MagicMock()
        mock_get_profile.return_value = profile

        request = self.factory.delete(
            "/profile",
            **self.gateway_headers,
        )

        response = ProfileView.as_view()(request)

        profile.delete.assert_called_once_with()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"], {})
class TrainingGroupViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.gateway_headers = {
            "HTTP_X_USER_ID": "15",
            "HTTP_X_USER_USERNAME": "murteza",
        }

    @patch(
        "teams.team6.views."
        "TrainingGroupListSerializer"
    )
    @patch(
        "teams.team6.views."
        "TrainingGroup.objects.select_related"
    )
    def test_group_list_returns_groups(
        self,
        mock_select_related,
        mock_serializer,
    ):
        groups = [SimpleNamespace(id=7)]

        mock_select_related.return_value\
            .order_by.return_value = groups

        mock_serializer.return_value.data = [
            {
                "id": 7,
                "name": "Beginner Running Group",
            }
        ]

        request = self.factory.get(
            "/groups",
            **self.gateway_headers,
        )

        response = (
            TrainingGroupListView
            .as_view()(request)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["data"]["groups"][0]["id"],
            7,
        )

    @patch(
        "teams.team6.views.analyze_group_risk"
    )
    @patch(
        "teams.team6.views."
        "TrainingGroupDetailSerializer"
    )
    @patch(
        "teams.team6.views._get_training_group"
    )
    @patch(
        "teams.team6.views._get_profile"
    )
    def test_group_details_include_risk(
        self,
        mock_get_profile,
        mock_get_group,
        mock_serializer,
        mock_risk,
    ):
        profile = SimpleNamespace(id=3)
        group = SimpleNamespace(id=7)

        mock_get_profile.return_value = profile
        mock_get_group.return_value = group

        mock_serializer.return_value.data = {
            "id": 7,
            "name": "Beginner Running Group",
        }

        mock_risk.return_value = {
            "score": 20,
            "level": RiskLevel.LOW,
            "is_safe": True,
            "reasons": [],
            "recommendation": (
                "This group is suitable for the user."
            ),
        }

        request = self.factory.get(
            "/groups/7",
            **self.gateway_headers,
        )

        response = (
            TrainingGroupDetailView
            .as_view()(request, group_id=7)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["data"]["group"][
                "risk"
            ]["score"],
            20,
        )

    @patch(
        "teams.team6.views.recommend_groups"
    )
    @patch(
        "teams.team6.views."
        "FitnessGoal.objects.filter"
    )
    @patch(
        "teams.team6.views._get_profile"
    )
    def test_recommendation_returns_groups(
        self,
        mock_get_profile,
        mock_goal_filter,
        mock_recommend_groups,
    ):
        profile = SimpleNamespace(id=3)

        goal = SimpleNamespace(
            id=1,
            name="Weight Loss",
        )

        group = SimpleNamespace(
            id=7,
            name="Beginner Running Group",
            description="Suitable for beginners",
            goal=goal,
            workout_type=WorkoutType.RUNNING,
            difficulty_level=DifficultyLevel.EASY,
            available_days=["saturday"],
            equipment=[],
            start_time=time(16, 0),
            end_time=time(18, 0),
            max_members=15,
        )

        mock_get_profile.return_value = profile

        mock_goal_filter.return_value\
            .exists.return_value = True

        mock_recommend_groups.return_value = [
            {
                "group": group,
                "member_count": 5,
                "match_score": 90,
                "risk": {
                    "score": 20,
                    "level": RiskLevel.LOW,
                    "is_safe": True,
                    "reasons": [],
                    "recommendation": (
                        "This group is suitable "
                        "for the user."
                    ),
                },
            }
        ]

        request = self.factory.post(
            "/groups/recommend",
            {
                "goal_id": 1,
                "fitness_level": (
                    FitnessLevel.BEGINNER
                ),
                "workout_type": (
                    WorkoutType.RUNNING
                ),
                "available_days": ["saturday"],
                "preferred_start_time": "16:00",
                "preferred_end_time": "18:00",
                "equipment": [],
                "physical_limitations": [],
            },
            format="json",
            **self.gateway_headers,
        )

        response = (
            GroupRecommendationView
            .as_view()(request)
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["data"]["groups"][0][
                "match_score"
            ],
            90,
        )

    @patch(
        "teams.team6.views.analyze_group_risk"
    )
    @patch(
        "teams.team6.views._get_training_group"
    )
    @patch(
        "teams.team6.views._get_profile"
    )
    def test_risk_analysis_returns_result(
        self,
        mock_get_profile,
        mock_get_group,
        mock_analyze_risk,
    ):
        mock_get_profile.return_value = (
            SimpleNamespace(id=3)
        )

        mock_get_group.return_value = (
            SimpleNamespace(id=7)
        )

        mock_analyze_risk.return_value = {
            "group_id": 7,
            "score": 85,
            "level": RiskLevel.HIGH,
            "is_safe": False,
            "reasons": [],
            "recommendation": (
                "Joining this group is not "
                "recommended."
            ),
        }

        request = self.factory.post(
            "/risk-analysis",
            {
                "group_id": 7,
            },
            format="json",
            **self.gateway_headers,
        )

        response = RiskAnalysisView.as_view()(
            request
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.data["data"]["analysis"][
                "level"
            ],
            RiskLevel.HIGH,
        )
        self.assertEqual(
            response.data["message"],
            "High injury risk detected",
        )