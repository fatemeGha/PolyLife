"""
Unit and lightweight endpoint tests for Team2.

The Team2 models are MongoEngine documents, so these tests use mongomock
instead of Django ORM's SQLite test database.
"""

import json
import os
import unittest
from datetime import date, datetime, time, timedelta

os.environ.setdefault("TESTING", "1")
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "teams.team2.config.settings",
)

import django
import mongoengine
import mongomock
from django.apps import apps

if not apps.ready:
    django.setup()

from django.test import Client
from django.utils import timezone

from ..models import (
    Goal,
    Notification,
    NotificationSettings,
    PhysicalRecord,
    Reminder,
)
from ..services.progress_service import (
    calculate_bmi,
    get_bmi_category,
    get_chart_data,
)
from ..services.reminder_service import (
    get_user_reminders,
    is_in_quiet_hours,
    soft_delete_reminder,
)


ALL_TEST_MODELS = (
    PhysicalRecord,
    Goal,
    Reminder,
    NotificationSettings,
    Notification,
)


def connect_test_database():
    """Connect MongoEngine's default alias to an isolated in-memory database."""
    mongoengine.disconnect(alias="default")
    mongoengine.connect(
        db="team2_test_views",
        alias="default",
        host="mongodb://localhost",
        mongo_client_class=mongomock.MongoClient,
        tz_aware=True,
        uuidRepresentation="standard",
    )


def make_physical_record(
    user_id: int = 1,
    weight: float = 80.0,
    height: float = 175.0,
    body_fat: float = None,
    muscle_mass: float = None,
) -> PhysicalRecord:
    """Create a PhysicalRecord with fields matching the MongoEngine model."""
    return PhysicalRecord(
        user_id=str(user_id),
        weight=weight,
        height=height,
        bmi=calculate_bmi(weight, height),
        body_fat_percent=body_fat,
        muscle_mass=muscle_mass,
    ).save()


def make_reminder(
    user_id: int = 1,
    title: str = "Test Reminder",
    reminder_time: time = time(9, 0),
    recurrence_pattern: str = "none",
) -> Reminder:
    """Create a scheduled Reminder without enqueuing a Celery task."""
    now = timezone.localtime(timezone.now())
    scheduled_time = datetime.combine(
        now.date(),
        reminder_time,
        tzinfo=timezone.get_current_timezone(),
    )
    return Reminder(
        user_id=str(user_id),
        title=title,
        scheduled_time=scheduled_time,
        repeat_type=recurrence_pattern,
        status="scheduled",
    ).save()


def make_notification_settings(
    user_id: int = 1,
    is_enabled: bool = True,
    quiet_start: time = time(22, 0),
    quiet_end: time = time(8, 0),
) -> NotificationSettings:
    """Create or update NotificationSettings using its current model fields."""
    settings = NotificationSettings.get_or_create_default(str(user_id))
    settings.push_enabled = is_enabled
    settings.dnd_start = quiet_start.strftime("%H:%M")
    settings.dnd_end = quiet_end.strftime("%H:%M")
    settings.save()
    return settings


class MongoTestCase(unittest.TestCase):
    def setUp(self):
        connect_test_database()

    def tearDown(self):
        for model in ALL_TEST_MODELS:
            model.drop_collection()
        mongoengine.disconnect(alias="default")


class BMICalculationTests(MongoTestCase):
    def test_bmi_formula_standard_case(self):
        self.assertAlmostEqual(
            calculate_bmi(weight_kg=80.0, height_cm=175.0),
            26.12,
            places=2,
        )

    def test_bmi_categories(self):
        cases = (
            (50.0, "Underweight"),
            (65.0, "Normal weight"),
            (80.0, "Overweight"),
            (100.0, "Obese"),
        )
        for weight, expected_category in cases:
            with self.subTest(weight=weight):
                bmi = calculate_bmi(weight, 175.0)
                self.assertEqual(
                    get_bmi_category(bmi),
                    expected_category,
                )

    def test_bmi_stored_correctly_in_database(self):
        record = make_physical_record(weight=80.0, height=175.0)
        self.assertAlmostEqual(
            record.bmi,
            calculate_bmi(80.0, 175.0),
            places=2,
        )

    def test_physical_record_uses_current_body_fat_field(self):
        record = make_physical_record(body_fat=18.5)
        self.assertEqual(record.body_fat_percent, 18.5)

    def test_bmi_recalculated_on_update(self):
        from ..services.progress_service import update_physical_record

        record = make_physical_record(weight=80.0, height=175.0)
        success, data, _ = update_physical_record(
            user_id=int(record.user_id),
            record_id=record.record_id,
            weight=70.0,
        )

        self.assertTrue(success)
        self.assertAlmostEqual(
            data["bmi"],
            calculate_bmi(70.0, 175.0),
            places=2,
        )

    def test_bmi_rejects_non_positive_height(self):
        for invalid_height in (0, -10):
            with self.subTest(height=invalid_height):
                with self.assertRaises(ValueError):
                    calculate_bmi(80.0, invalid_height)


class QuietHoursLogicTests(MongoTestCase):
    def test_overnight_window(self):
        cases = (
            (time(23, 30), True),
            (time(3, 0), True),
            (time(12, 0), False),
            (time(18, 0), False),
            (time(22, 0), True),
            (time(8, 0), True),
        )
        for check_time, expected in cases:
            with self.subTest(check_time=check_time):
                self.assertEqual(
                    is_in_quiet_hours(
                        check_time=check_time,
                        quiet_start=time(22, 0),
                        quiet_end=time(8, 0),
                    ),
                    expected,
                )

    def test_same_day_window(self):
        cases = (
            (time(12, 0), True),
            (time(8, 0), False),
            (time(20, 0), False),
        )
        for check_time, expected in cases:
            with self.subTest(check_time=check_time):
                self.assertEqual(
                    is_in_quiet_hours(
                        check_time=check_time,
                        quiet_start=time(9, 0),
                        quiet_end=time(17, 0),
                    ),
                    expected,
                )


class GatewayAuthDecoratorTests(MongoTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.auth_test_url = "/api/team2/auth-test/"
        self.health_url = "/api/team2/health/"

    def test_auth_test_returns_200_with_valid_headers(self):
        response = self.client.get(
            self.auth_test_url,
            HTTP_X_USER_ID="1",
            HTTP_X_USER_USERNAME="testuser",
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["user_id"], 1)
        self.assertEqual(body["data"]["username"], "testuser")

    def test_auth_test_rejects_invalid_or_missing_headers(self):
        cases = (
            {},
            {"HTTP_X_USER_USERNAME": "testuser"},
            {"HTTP_X_USER_ID": "1"},
            {
                "HTTP_X_USER_ID": "abc",
                "HTTP_X_USER_USERNAME": "testuser",
            },
            {
                "HTTP_X_USER_ID": "-1",
                "HTTP_X_USER_USERNAME": "testuser",
            },
        )
        for headers in cases:
            with self.subTest(headers=headers):
                response = self.client.get(
                    self.auth_test_url,
                    **headers,
                )
                self.assertEqual(response.status_code, 401)

    def test_health_check_is_public(self):
        response = self.client.get(self.health_url)
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["service"], "team2")

    def test_create_record_returns_401_without_headers(self):
        response = self.client.post(
            "/api/team2/progress/records/",
            data=json.dumps({"weight": 80, "height": 175}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)


class SoftDeleteReminderTests(MongoTestCase):
    def setUp(self):
        super().setUp()
        self.user_id = 1
        self.reminder = make_reminder(
            user_id=self.user_id,
            title="Morning Run",
        )

    def test_soft_delete_sets_deleted_and_expired(self):
        success, _, _ = soft_delete_reminder(
            user_id=self.user_id,
            reminder_id=self.reminder.reminder_id,
        )
        self.reminder.reload()

        self.assertTrue(success)
        self.assertTrue(self.reminder.is_deleted)
        self.assertEqual(self.reminder.status, "expired")

    def test_soft_delete_keeps_document_in_database(self):
        soft_delete_reminder(
            user_id=self.user_id,
            reminder_id=self.reminder.reminder_id,
        )
        stored = Reminder.objects(
            reminder_id=self.reminder.reminder_id
        ).first()
        self.assertIsNotNone(stored)

    def test_deleted_reminder_is_not_returned_in_list(self):
        make_reminder(
            user_id=self.user_id,
            title="Evening Walk",
            reminder_time=time(18, 0),
        )
        soft_delete_reminder(
            user_id=self.user_id,
            reminder_id=self.reminder.reminder_id,
        )

        reminder_ids = {
            item["id"]
            for item in get_user_reminders(user_id=self.user_id)
        }
        self.assertNotIn(
            self.reminder.reminder_id,
            reminder_ids,
        )

    def test_wrong_user_does_not_delete_reminder(self):
        success, _, _ = soft_delete_reminder(
            user_id=999,
            reminder_id=self.reminder.reminder_id,
        )
        self.reminder.reload()

        self.assertFalse(success)
        self.assertFalse(self.reminder.is_deleted)

    def test_second_or_unknown_delete_returns_error(self):
        soft_delete_reminder(
            user_id=self.user_id,
            reminder_id=self.reminder.reminder_id,
        )
        second_success, _, _ = soft_delete_reminder(
            user_id=self.user_id,
            reminder_id=self.reminder.reminder_id,
        )
        missing_success, _, _ = soft_delete_reminder(
            user_id=self.user_id,
            reminder_id="missing-reminder",
        )

        self.assertFalse(second_success)
        self.assertFalse(missing_success)


class ChartDataTests(MongoTestCase):
    def setUp(self):
        super().setUp()
        self.user_id = 1
        self.client = Client()
        self.url = "/api/team2/progress/charts/"
        self.auth_headers = {
            "HTTP_X_USER_ID": "1",
            "HTTP_X_USER_USERNAME": "testuser",
        }

        now = timezone.now()
        for days_ago in (1, 7, 15, 25, 40):
            record = make_physical_record(
                user_id=self.user_id,
                weight=80.0 - days_ago * 0.1,
            )
            PhysicalRecord.objects(
                record_id=record.record_id
            ).update(
                set__created_at=now - timedelta(days=days_ago)
            )

    def test_period_filters_and_sort_order(self):
        weekly_ok, weekly, _ = get_chart_data(
            self.user_id,
            "weight",
            "weekly",
        )
        monthly_ok, monthly, _ = get_chart_data(
            self.user_id,
            "weight",
            "monthly",
        )
        yearly_ok, yearly, _ = get_chart_data(
            self.user_id,
            "weight",
            "yearly",
        )

        self.assertTrue(weekly_ok)
        self.assertTrue(monthly_ok)
        self.assertTrue(yearly_ok)
        self.assertLessEqual(weekly["count"], 2)
        self.assertGreaterEqual(monthly["count"], 3)
        dates = [point["date"] for point in yearly["points"]]
        self.assertEqual(dates, sorted(dates))

    def test_invalid_chart_parameters(self):
        metric_ok, metric_errors, _ = get_chart_data(
            self.user_id,
            "invalid_metric",
            "monthly",
        )
        period_ok, period_errors, _ = get_chart_data(
            self.user_id,
            "weight",
            "last_decade",
        )

        self.assertFalse(metric_ok)
        self.assertIn("metric", metric_errors)
        self.assertFalse(period_ok)
        self.assertIn("period", period_errors)

    def test_chart_endpoint(self):
        response = self.client.get(
            self.url,
            {"metric": "weight", "period": "monthly"},
            **self.auth_headers,
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertIn("points", body["data"])

    def test_chart_endpoint_rejects_missing_metric_or_auth(self):
        missing_metric = self.client.get(
            self.url,
            {"period": "monthly"},
            **self.auth_headers,
        )
        missing_auth = self.client.get(
            self.url,
            {"metric": "weight", "period": "monthly"},
        )

        self.assertEqual(missing_metric.status_code, 400)
        self.assertEqual(missing_auth.status_code, 401)

    def test_bmi_metric_unit(self):
        success, data, _ = get_chart_data(
            self.user_id,
            "bmi",
            "yearly",
        )
        self.assertTrue(success)
        self.assertEqual(data["unit"], "kg/m²")


class TrainerStudentProgressTests(MongoTestCase):
    def setUp(self):
        super().setUp()
        self.client = Client()
        self.trainer_headers = {
            "HTTP_X_USER_ID": "10",
            "HTTP_X_USER_USERNAME": "trainer1",
        }
        self.student_id = 42

        make_physical_record(
            user_id=self.student_id,
            weight=75.0,
            height=180.0,
        )
        Goal(
            user_id=str(self.student_id),
            target_weight=70.0,
        ).save()

    def test_trainer_can_view_student_progress(self):
        response = self.client.get(
            (
                f"/api/team2/trainer/users/"
                f"{self.student_id}/progress/"
            ),
            **self.trainer_headers,
        )
        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["success"])
        self.assertEqual(
            body["data"]["current"]["weight"],
            75.0,
        )

    def test_student_without_data_returns_404(self):
        response = self.client.get(
            "/api/team2/trainer/users/9999/progress/",
            **self.trainer_headers,
        )
        self.assertEqual(response.status_code, 404)

    def test_trainer_view_requires_auth_headers(self):
        response = self.client.get(
            (
                f"/api/team2/trainer/users/"
                f"{self.student_id}/progress/"
            )
        )
        self.assertEqual(response.status_code, 401)


class GoalUpsertTests(MongoTestCase):
    def setUp(self):
        super().setUp()
        self.user_id = 1

    def test_first_goal_creates_and_second_updates_same_document(self):
        from ..services.progress_service import upsert_user_goal

        first_success, _, _ = upsert_user_goal(
            user_id=self.user_id,
            target_weight=75.0,
        )
        second_success, _, _ = upsert_user_goal(
            user_id=self.user_id,
            target_weight=70.0,
        )
        goal = Goal.objects.get(user_id=str(self.user_id))

        self.assertTrue(first_success)
        self.assertTrue(second_success)
        self.assertEqual(
            Goal.objects(user_id=str(self.user_id)).count(),
            1,
        )
        self.assertEqual(goal.target_weight, 70.0)

    def test_target_date_is_not_persisted_by_current_model(self):
        from ..services.progress_service import upsert_user_goal

        future_date = (date.today() + timedelta(days=90)).isoformat()
        success, data, _ = upsert_user_goal(
            user_id=self.user_id,
            target_weight=75.0,
            target_date=future_date,
        )

        self.assertTrue(success)
        self.assertIsNone(data["target_date"])
        self.assertNotIn("target_date", Goal._fields)


if __name__ == "__main__":
    unittest.main()
