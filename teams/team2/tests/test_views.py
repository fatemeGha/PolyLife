"""
Unit tests for Team2 microservice.

Test coverage:
    1. BMI calculation accuracy after creating a physical record
    2. Quiet hours (DND) logic — in-window and out-of-window scenarios
    3. gateway_auth_required decorator — 200 with headers, 401 without
    4. Soft delete for reminders — is_deleted=True, record persists in DB
    5. Chart data endpoint — valid/invalid query parameters
    6. Trainer view — access to student progress summary
    7. Goal upsert — create then update with same user_id

Running tests:
    python manage.py test teams.team2
    python manage.py test teams.team2 --verbosity=2

Test database:
    Django creates an isolated in-memory SQLite test database.
    No production data is affected.
"""

import json
from datetime import time, date, timedelta
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from ..models import PhysicalRecord, UserGoal, Reminder, NotificationSetting, NotificationLog
from ..services.progress_service import calculate_bmi, get_bmi_category, get_chart_data
from ..services.reminder_service import (
    is_in_quiet_hours,
    create_reminder,
    soft_delete_reminder,
    get_or_create_notification_settings,
)


# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------

def make_physical_record(user_id: int = 1,
                          weight: float = 80.0,
                          height: float = 175.0,
                          body_fat: float = None,
                          muscle_mass: float = None) -> PhysicalRecord:
    """
    Create and return a PhysicalRecord instance with auto-calculated BMI.
    Saves to the test database.
    """
    bmi = calculate_bmi(weight, height)
    return PhysicalRecord.objects.create(
        user_id=user_id,
        weight=weight,
        height=height,
        bmi=bmi,
        body_fat_percentage=body_fat,
        muscle_mass=muscle_mass,
    )


def make_reminder(user_id: int = 1,
                  title: str = "Test Reminder",
                  reminder_time: time = time(9, 0),
                  recurrence_pattern: str = "none") -> Reminder:
    """
    Create and return a Reminder instance.
    Saves to the test database.
    Bypasses the service layer to avoid Celery scheduling in tests.
    """
    return Reminder.objects.create(
        user_id=user_id,
        title=title,
        reminder_time=reminder_time,
        recurrence_pattern=recurrence_pattern,
    )


def make_notification_settings(user_id: int = 1,
                                is_enabled: bool = True,
                                quiet_start: time = time(22, 0),
                                quiet_end: time = time(8, 0)) -> NotificationSetting:
    """
    Create and return a NotificationSetting instance.
    """
    settings, _ = NotificationSetting.objects.get_or_create(
        user_id=user_id,
        defaults={
            "is_enabled": is_enabled,
            "quiet_hours_start": quiet_start,
            "quiet_hours_end": quiet_end,
        },
    )
    return settings


# ---------------------------------------------------------------------------
# 1. BMI Calculation Tests
# ---------------------------------------------------------------------------

class BMICalculationTests(TestCase):
    """
    Tests for the BMI formula and its integration with PhysicalRecord creation.
    """
    databases = {"default", "team2"}  # Enables multi-database testing for Team 2

    def test_bmi_formula_standard_case(self):
        """
        BMI should equal weight / (height_in_meters ^ 2), rounded to 2 decimals.
        80 kg / (1.75 m)^2 = 26.12
        """
        result = calculate_bmi(weight_kg=80.0, height_cm=175.0)
        self.assertAlmostEqual(result, 26.12, places=2)

    def test_bmi_formula_underweight(self):
        """
        50 kg / (1.75 m)^2 = 16.33 → Underweight
        """
        result = calculate_bmi(weight_kg=50.0, height_cm=175.0)
        self.assertAlmostEqual(result, 16.33, places=2)
        self.assertEqual(get_bmi_category(result), "Underweight")

    def test_bmi_formula_normal_weight(self):
        """
        65 kg / (1.75 m)^2 = 21.22 → Normal weight
        """
        result = calculate_bmi(weight_kg=65.0, height_cm=175.0)
        self.assertAlmostEqual(result, 21.22, places=2)
        self.assertEqual(get_bmi_category(result), "Normal weight")

    def test_bmi_formula_overweight(self):
        """
        80 kg / (1.75 m)^2 = 26.12 → Overweight
        """
        result = calculate_bmi(weight_kg=80.0, height_cm=175.0)
        self.assertEqual(get_bmi_category(result), "Overweight")

    def test_bmi_formula_obese(self):
        """
        100 kg / (1.75 m)^2 = 32.65 → Obese
        """
        result = calculate_bmi(weight_kg=100.0, height_cm=175.0)
        self.assertAlmostEqual(result, 32.65, places=2)
        self.assertEqual(get_bmi_category(result), "Obese")

    def test_bmi_stored_correctly_in_database(self):
        """
        After creating a PhysicalRecord, the stored bmi should match the formula.
        """
        record = make_physical_record(weight=80.0, height=175.0)
        expected_bmi = calculate_bmi(80.0, 175.0)
        self.assertAlmostEqual(record.bmi, expected_bmi, places=2)

    def test_bmi_recalculated_on_update(self):
        """
        When weight changes via the service, BMI should be recalculated.
        """
        from ..services.progress_service import update_physical_record

        record = make_physical_record(weight=80.0, height=175.0)
        original_bmi = record.bmi

        success, data, _ = update_physical_record(
            user_id=record.user_id,
            record_id=record.id,
            weight=70.0,
        )

        self.assertTrue(success)
        new_expected_bmi = calculate_bmi(70.0, 175.0)
        self.assertAlmostEqual(data["bmi"], new_expected_bmi, places=2)
        self.assertNotAlmostEqual(data["bmi"], original_bmi, places=2)

    def test_bmi_raises_on_zero_height(self):
        """
        Height of 0 must raise a ValueError to prevent division by zero.
        """
        with self.assertRaises(ValueError):
            calculate_bmi(weight_kg=80.0, height_cm=0)

    def test_bmi_raises_on_negative_height(self):
        """
        Negative height must raise a ValueError.
        """
        with self.assertRaises(ValueError):
            calculate_bmi(weight_kg=80.0, height_cm=-10)


# ---------------------------------------------------------------------------
# 2. Quiet Hours (DND) Logic Tests
# ---------------------------------------------------------------------------

class QuietHoursLogicTests(TestCase):
    """
    Tests for the is_in_quiet_hours() function.
    """
    databases = {"default", "team2"}

    # ---- Overnight window (22:00 → 08:00) --------------------------------

    def test_overnight_window_inside_before_midnight(self):
        """23:30 is inside an overnight 22:00–08:00 quiet window."""
        result = is_in_quiet_hours(
            check_time=time(23, 30),
            quiet_start=time(22, 0),
            quiet_end=time(8, 0),
        )
        self.assertTrue(result)

    def test_overnight_window_inside_after_midnight(self):
        """03:00 is inside an overnight 22:00–08:00 quiet window."""
        result = is_in_quiet_hours(
            check_time=time(3, 0),
            quiet_start=time(22, 0),
            quiet_end=time(8, 0),
        )
        self.assertTrue(result)

    def test_overnight_window_outside_midday(self):
        """12:00 is outside an overnight 22:00–08:00 quiet window."""
        result = is_in_quiet_hours(
            check_time=time(12, 0),
            quiet_start=time(22, 0),
            quiet_end=time(8, 0),
        )
        self.assertFalse(result)

    def test_overnight_window_outside_early_evening(self):
        """18:00 is outside an overnight 22:00–08:00 quiet window."""
        result = is_in_quiet_hours(
            check_time=time(18, 0),
            quiet_start=time(22, 0),
            quiet_end=time(8, 0),
        )
        self.assertFalse(result)

    def test_overnight_window_exact_start_boundary(self):
        """22:00 exactly is AT the start boundary — should be inside."""
        result = is_in_quiet_hours(
            check_time=time(22, 0),
            quiet_start=time(22, 0),
            quiet_end=time(8, 0),
        )
        self.assertTrue(result)

    def test_overnight_window_exact_end_boundary(self):
        """08:00 exactly is AT the end boundary — should be inside."""
        result = is_in_quiet_hours(
            check_time=time(8, 0),
            quiet_start=time(22, 0),
            quiet_end=time(8, 0),
        )
        self.assertTrue(result)

    # ---- Same-day window (09:00 → 17:00) ---------------------------------

    def test_same_day_window_inside(self):
        """12:00 is inside a same-day 09:00–17:00 quiet window."""
        result = is_in_quiet_hours(
            check_time=time(12, 0),
            quiet_start=time(9, 0),
            quiet_end=time(17, 0),
        )
        self.assertTrue(result)

    def test_same_day_window_outside_before(self):
        """08:00 is outside a same-day 09:00–17:00 quiet window."""
        result = is_in_quiet_hours(
            check_time=time(8, 0),
            quiet_start=time(9, 0),
            quiet_end=time(17, 0),
        )
        self.assertFalse(result)

    def test_same_day_window_outside_after(self):
        """20:00 is outside a same-day 09:00–17:00 quiet window."""
        result = is_in_quiet_hours(
            check_time=time(20, 0),
            quiet_start=time(9, 0),
            quiet_end=time(17, 0),
        )
        self.assertFalse(result)


# ---------------------------------------------------------------------------
# 3. Gateway Auth Decorator Tests
# ---------------------------------------------------------------------------

class GatewayAuthDecoratorTests(TestCase):
    """
    Integration tests for the gateway_auth_required decorator.
    """
    databases = {"default", "team2"}

    def setUp(self):
        """Set up the Django test client used across all tests in this class."""
        self.client = Client()
        self.auth_test_url = "/api/team2/auth-test/"
        self.health_url = "/api/team2/health/"

    def test_auth_test_returns_200_with_valid_headers(self):
        """
        GET /api/team2/auth-test/ with both headers → HTTP 200.
        Response body should contain user_id and username.
        """
        response = self.client.get(
            self.auth_test_url,
            HTTP_X_USER_ID="1",
            HTTP_X_USER_USERNAME="testuser",
        )
        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["user_id"], 1)
        self.assertEqual(body["data"]["username"], "testuser")

    def test_auth_test_returns_401_without_any_headers(self):
        """
        GET /api/team2/auth-test/ with no headers → HTTP 401.
        """
        response = self.client.get(self.auth_test_url)
        self.assertEqual(response.status_code, 401)

        body = json.loads(response.content)
        self.assertFalse(body["success"])
        self.assertIn("X-User-Id", body["errors"])

    def test_auth_test_returns_401_missing_user_id(self):
        """
        GET /api/team2/auth-test/ with only X-User-Username → HTTP 401.
        Both headers are required.
        """
        response = self.client.get(
            self.auth_test_url,
            HTTP_X_USER_USERNAME="testuser",
        )
        self.assertEqual(response.status_code, 401)

    def test_auth_test_returns_401_missing_username(self):
        """
        GET /api/team2/auth-test/ with only X-User-Id → HTTP 401.
        """
        response = self.client.get(
            self.auth_test_url,
            HTTP_X_USER_ID="1",
        )
        self.assertEqual(response.status_code, 401)

    def test_auth_test_returns_401_non_integer_user_id(self):
        """
        X-User-Id must be a valid positive integer.
        Sending 'abc' → HTTP 401.
        """
        response = self.client.get(
            self.auth_test_url,
            HTTP_X_USER_ID="abc",
            HTTP_X_USER_USERNAME="testuser",
        )
        self.assertEqual(response.status_code, 401)

    def test_auth_test_returns_401_negative_user_id(self):
        """
        X-User-Id must be a POSITIVE integer.
        Sending -1 → HTTP 401.
        """
        response = self.client.get(
            self.auth_test_url,
            HTTP_X_USER_ID="-1",
            HTTP_X_USER_USERNAME="testuser",
        )
        self.assertEqual(response.status_code, 401)

    def test_health_check_returns_200_without_headers(self):
        """
        GET /api/team2/health/ requires no authentication.
        Must return HTTP 200 even without Gateway headers.
        """
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["service"], "team2")

    def test_create_record_returns_401_without_headers(self):
        """
        Protected endpoints (POST /progress/records/) must return 401
        when Gateway headers are absent.
        """
        response = self.client.post(
            "/api/team2/progress/records/",
            data=json.dumps({"weight": 80, "height": 175}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)


# ---------------------------------------------------------------------------
# 4. Soft Delete Tests (Reminders)
# ---------------------------------------------------------------------------

class SoftDeleteReminderTests(TestCase):
    """
    Tests for the soft delete behaviour of Reminder records.
    """
    databases = {"default", "team2"}

    def setUp(self):
        self.user_id = 1
        self.reminder = make_reminder(user_id=self.user_id, title="Morning Run")

    def test_soft_delete_sets_is_deleted_true(self):
        """
        soft_delete_reminder() must set is_deleted=True on the record.
        """
        success, data, message = soft_delete_reminder(
            user_id=self.user_id,
            reminder_id=self.reminder.id,
        )
        self.assertTrue(success)

        # Reload from DB and check flag
        self.reminder.refresh_from_db()
        self.assertTrue(self.reminder.is_deleted)

    def test_soft_delete_sets_is_active_false(self):
        """
        soft_delete_reminder() must also set is_active=False.
        """
        soft_delete_reminder(user_id=self.user_id, reminder_id=self.reminder.id)
        self.reminder.refresh_from_db()
        self.assertFalse(self.reminder.is_active)

    def test_soft_delete_record_remains_in_database(self):
        """
        After soft delete, the record must still be physically present in the DB.
        """
        soft_delete_reminder(user_id=self.user_id, reminder_id=self.reminder.id)

        # Must still exist in raw queryset
        exists = Reminder.objects.filter(id=self.reminder.id).exists()
        self.assertTrue(exists)

    def test_soft_deleted_reminder_not_returned_in_list(self):
        """
        get_user_reminders() must exclude soft-deleted reminders.
        """
        from ..services.reminder_service import get_user_reminders

        # Create a second reminder to ensure list is not empty after deletion
        make_reminder(user_id=self.user_id, title="Evening Walk", reminder_time=time(18, 0))

        soft_delete_reminder(user_id=self.user_id, reminder_id=self.reminder.id)
        reminders = get_user_reminders(user_id=self.user_id)

        ids_in_list = [r["id"] for r in reminders]
        self.assertNotIn(self.reminder.id, ids_in_list)

    def test_soft_delete_wrong_user_returns_error(self):
        """
        A user cannot soft-delete another user's reminder.
        """
        different_user_id = 999

        success, data, message = soft_delete_reminder(
            user_id=different_user_id,
            reminder_id=self.reminder.id,
        )

        self.assertFalse(success)
        # Original reminder must still be active
        self.reminder.refresh_from_db()
        self.assertFalse(self.reminder.is_deleted)

    def test_soft_delete_twice_returns_error(self):
        """
        Attempting to soft-delete an already-deleted reminder must return
        success=False (the second call finds no active record to delete).
        """
        soft_delete_reminder(user_id=self.user_id, reminder_id=self.reminder.id)
        success, _, message = soft_delete_reminder(
            user_id=self.user_id,
            reminder_id=self.reminder.id,
        )
        self.assertFalse(success)

    def test_soft_delete_nonexistent_reminder_returns_error(self):
        """
        Deleting a reminder that does not exist returns success=False.
        """
        success, _, message = soft_delete_reminder(
            user_id=self.user_id,
            reminder_id=99999,
        )
        self.assertFalse(success)


# ---------------------------------------------------------------------------
# 5. Chart Data Tests
# ---------------------------------------------------------------------------

class ChartDataTests(TestCase):
    """
    Tests for the get_chart_data() service and the chart endpoint.
    """
    databases = {"default", "team2"}

    def setUp(self):
        self.user_id = 1
        self.client = Client()
        self.url = "/api/team2/progress/charts/"
        self.auth_headers = {
            "HTTP_X_USER_ID": "1",
            "HTTP_X_USER_USERNAME": "testuser",
        }

	# Create records spread across the last 40 days
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()
        for days_ago in [1, 7, 15, 25, 40]:
            record_time = now - timedelta(days=days_ago)
            record = PhysicalRecord.objects.create(
                user_id=self.user_id,
                weight=80.0 - days_ago * 0.1,
                height=175.0,
                bmi=calculate_bmi(80.0 - days_ago * 0.1, 175.0),
            )
            # Use update() to bypass auto_now_add for testing past dates
            PhysicalRecord.objects.filter(id=record.id).update(created_at=record_time)

    def test_weekly_period_returns_only_last_7_days(self):
        """
        period=weekly must include only records from the last 7 days.
        """
        success, data, _ = get_chart_data(
            user_id=self.user_id,
            metric="weight",
            period="weekly",
        )
        self.assertTrue(success)
        self.assertLessEqual(data["count"], 2)

    def test_monthly_period_returns_last_30_days(self):
        """
        period=monthly must include records from the last 30 days.
        """
        success, data, _ = get_chart_data(
            user_id=self.user_id,
            metric="weight",
            period="monthly",
        )
        self.assertTrue(success)
        self.assertGreaterEqual(data["count"], 3)

    def test_points_are_sorted_ascending_by_date(self):
        """
        Data points must be in chronological order (oldest first).
        """
        success, data, _ = get_chart_data(
            user_id=self.user_id,
            metric="weight",
            period="yearly",
        )
        self.assertTrue(success)

        dates = [p["date"] for p in data["points"]]
        self.assertEqual(dates, sorted(dates))

    def test_invalid_metric_returns_error(self):
        """
        An unrecognised metric name must return success=False.
        """
        success, data, message = get_chart_data(
            user_id=self.user_id,
            metric="invalid_metric",
            period="monthly",
        )
        self.assertFalse(success)
        self.assertIn("metric", data)

    def test_invalid_period_returns_error(self):
        """
        An unrecognised period name must return success=False.
        """
        success, data, message = get_chart_data(
            user_id=self.user_id,
            metric="weight",
            period="last_decade",
        )
        self.assertFalse(success)
        self.assertIn("period", data)

    def test_chart_endpoint_returns_200_with_valid_params(self):
        """
        GET /api/team2/progress/charts/?metric=weight&period=monthly
        """
        response = self.client.get(
            self.url,
            {"metric": "weight", "period": "monthly"},
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)
        self.assertTrue(body["success"])
        self.assertIn("points", body["data"])
        self.assertIn("unit", body["data"])

    def test_chart_endpoint_returns_400_missing_metric(self):
        """
        GET /api/team2/progress/charts/?period=monthly (no metric)
        """
        response = self.client.get(
            self.url,
            {"period": "monthly"},
            **self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)

    def test_chart_endpoint_returns_401_without_headers(self):
        """
        Chart endpoint must return 401 if Gateway headers are absent.
        """
        response = self.client.get(
            self.url,
            {"metric": "weight", "period": "monthly"},
        )
        self.assertEqual(response.status_code, 401)

    def test_bmi_metric_returns_correct_unit(self):
        """
        When metric=bmi, the unit label must be 'kg/m²'.
        """
        success, data, _ = get_chart_data(
            user_id=self.user_id,
            metric="bmi",
            period="yearly",
        )
        self.assertTrue(success)
        self.assertEqual(data["unit"], "kg/m²")


# ---------------------------------------------------------------------------
# 6. Trainer View Tests
# ---------------------------------------------------------------------------

class TrainerStudentProgressTests(TestCase):
    """
    Tests for GET /api/team2/trainer/users/<student_id>/progress/
    """
    databases = {"default", "team2"}

    def setUp(self):
        self.client = Client()
        self.trainer_headers = {
            "HTTP_X_USER_ID": "10",       # trainer's user_id
            "HTTP_X_USER_USERNAME": "trainer1",
        }
        self.student_id = 42

        # Give the student one physical record and one goal
        make_physical_record(user_id=self.student_id, weight=75.0, height=180.0)
        UserGoal.objects.create(
            user_id=self.student_id,
            target_weight=70.0,
        )

    def test_trainer_can_view_student_progress(self):
        """
        Trainer with valid auth headers can access any student's progress.
        """
        response = self.client.get(
            f"/api/team2/trainer/users/{self.student_id}/progress/",
            **self.trainer_headers,
        )
        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)
        self.assertTrue(body["success"])
        self.assertIn("current", body["data"])
        self.assertIn("goal", body["data"])
        self.assertEqual(body["data"]["user_id"], self.student_id)

    def test_trainer_student_with_no_data_returns_404(self):
        """
        If the student has no records and no goals, the endpoint returns 404.
        """
        no_data_student_id = 9999

        response = self.client.get(
            f"/api/team2/trainer/users/{no_data_student_id}/progress/",
            **self.trainer_headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_trainer_view_requires_auth_headers(self):
        """
        Trainer view must return 401 if Gateway headers are missing.
        """
        response = self.client.get(
            f"/api/team2/trainer/users/{self.student_id}/progress/",
        )
        self.assertEqual(response.status_code, 401)

    def test_trainer_view_returns_correct_student_weight(self):
        """
        The current weight in the response must match the student's latest record.
        """
        response = self.client.get(
            f"/api/team2/trainer/users/{self.student_id}/progress/",
            **self.trainer_headers,
        )
        body = json.loads(response.content)
        self.assertEqual(body["data"]["current"]["weight"], 75.0)


# ---------------------------------------------------------------------------
# 7. Goal Upsert Tests
# ---------------------------------------------------------------------------

class GoalUpsertTests(TestCase):
    """
    Tests for the upsert_user_goal() service.
    """
    databases = {"default", "team2"}

    def setUp(self):
        self.user_id = 1

    def test_first_goal_creates_new_record(self):
        """
        First call to upsert_user_goal() creates a UserGoal in the DB.
        """
        from ..services.progress_service import upsert_user_goal

        success, data, _ = upsert_user_goal(
            user_id=self.user_id,
            target_weight=75.0,
        )
        self.assertTrue(success)
        self.assertEqual(UserGoal.objects.filter(user_id=self.user_id).count(), 1)

    def test_second_call_updates_existing_goal(self):
        """
        Second call updates the existing goal — no duplicate rows created.
        """
        from ..services.progress_service import upsert_user_goal

        upsert_user_goal(user_id=self.user_id, target_weight=75.0)
        upsert_user_goal(user_id=self.user_id, target_weight=70.0)

        # Must still be exactly one row
        self.assertEqual(UserGoal.objects.filter(user_id=self.user_id).count(), 1)

        # And the target weight must be the updated value
        goal = UserGoal.objects.get(user_id=self.user_id)
        self.assertEqual(goal.target_weight, 70.0)

    def test_goal_with_past_date_fails_validation(self):
        """
        target_date set to yesterday must be rejected by the service.
        """
        from ..services.progress_service import upsert_user_goal

        yesterday = (date.today() - timedelta(days=1)).isoformat()
        success, data, _ = upsert_user_goal(
            user_id=self.user_id,
            target_weight=75.0,
            target_date=yesterday,
        )
        self.assertFalse(success)
        self.assertIn("target_date", data)

    def test_goal_with_future_date_succeeds(self):
        """
        target_date set to a future date must be accepted.
        """
        from ..services.progress_service import upsert_user_goal

        future_date = (date.today() + timedelta(days=90)).isoformat()
        success, data, _ = upsert_user_goal(
            user_id=self.user_id,
            target_weight=75.0,
            target_date=future_date,
        )
        self.assertTrue(success)
        self.assertEqual(data["target_date"], future_date)
