"""
Unit tests for services.py.

Uses the same mongomock setup as test_models.py. Two external
dependencies aren't ready yet in the real project, so they're mocked
here instead of exercised for real:

  - Reminder.schedule() normally enqueues a Celery task by importing
    tasks.py, which doesn't exist yet -> we patch it out.
  - Notification.send() -> services.send_push_notification() normally
    calls Firebase, but since no DeviceToken exists in these tests it
    soft-fails and returns early anyway, so no patch is needed for it.
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import mongoengine

from ..models import (
    PhysicalRecord,
    Goal,
    WorkoutSession,
    PersonalBest,
    Reminder,
    NotificationSettings,
    Notification,
    DeviceToken,
    EventSubscription,
)
from .. import services


def _connect_test_db():
    mongoengine.disconnect()
    mongoengine.connect(db="team7_test", host="mongomock://localhost")


def _drop_all_collections():
    for model in (
        PhysicalRecord, Goal, WorkoutSession, PersonalBest, Reminder,
        NotificationSettings, Notification, DeviceToken, EventSubscription,
    ):
        model.drop_collection()


class RegisterPhysicalDataTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_creates_record_with_computed_bmi(self):
        record = services.register_physical_data(
            user_id="u1", weight=70, height=1.75, body_fat_percent=15,
        )

        self.assertIsNotNone(record.record_id)
        self.assertAlmostEqual(record.bmi, 22.86, places=2)
        self.assertEqual(PhysicalRecord.objects.count(), 1)

    def test_rejects_non_positive_weight(self):
        with self.assertRaises(ValueError):
            services.register_physical_data(user_id="u1", weight=0, height=1.75)

    def test_rejects_out_of_range_body_fat(self):
        with self.assertRaises(ValueError):
            services.register_physical_data(
                user_id="u1", weight=70, height=1.75, body_fat_percent=150,
            )


class EditDeletePhysicalDataTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_edit_updates_fields_and_recomputes_bmi(self):
        record = services.register_physical_data(user_id="u1", weight=70, height=1.75)

        updated = services.edit_physical_data(record.record_id, weight=68)

        self.assertEqual(updated.weight, 68)
        self.assertAlmostEqual(updated.bmi, 68 / (1.75 ** 2), places=2)

    def test_delete_soft_deletes_record(self):
        record = services.register_physical_data(user_id="u1", weight=70, height=1.75)

        services.delete_physical_data(record.record_id)

        reloaded = PhysicalRecord.objects.get(record_id=record.record_id)
        self.assertTrue(reloaded.is_deleted)
        # Soft-deleted records should be excluded from normal "active" queries.
        self.assertEqual(
            PhysicalRecord.objects(user_id="u1", is_deleted=False).count(), 0
        )


class GetProgressChartDataTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_returns_only_records_within_period_and_sorted(self):
        old = PhysicalRecord(
            user_id="u1", weight=80, height=1.75,
            created_at=datetime.utcnow() - timedelta(days=40),
        )
        old.calculate_bmi()
        old.save()

        recent = PhysicalRecord(
            user_id="u1", weight=75, height=1.75,
            created_at=datetime.utcnow() - timedelta(days=2),
        )
        recent.calculate_bmi()
        recent.save()

        result = services.get_progress_chart_data("u1", period="month")

        self.assertEqual(len(result["points"]), 1)
        self.assertEqual(result["points"][0]["weight"], 75)

    def test_includes_goal_comparison_when_goal_exists(self):
        services.set_user_goal("u1", target_weight=70)
        record = PhysicalRecord(user_id="u1", weight=75, height=1.75)
        record.calculate_bmi()
        record.save()

        result = services.get_progress_chart_data("u1", period="month")

        self.assertIn("goal_comparison", result["points"][0])
        self.assertEqual(result["points"][0]["goal_comparison"]["weight_diff"], 5)


class SetUserGoalTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_creates_goal_if_none_exists(self):
        goal = services.set_user_goal("u1", target_weight=70, target_body_fat=15)
        self.assertEqual(Goal.objects.count(), 1)
        self.assertEqual(goal.target_weight, 70)

    def test_updates_existing_goal_instead_of_duplicating(self):
        services.set_user_goal("u1", target_weight=70)
        services.set_user_goal("u1", target_weight=68)

        self.assertEqual(Goal.objects.count(), 1)
        self.assertEqual(Goal.objects.first().target_weight, 68)


class DetectAndRegisterNewRecordTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_returns_none_when_record_not_broken(self):
        PersonalBest.create_first_record("u1", "Squat", 100, session_id="s1")

        result = services.detect_and_register_new_record(
            user_id="u1", exercise_name="Squat", weight_lifted=90, session_id="s2",
        )

        self.assertIsNone(result)
        # No congratulations notification should have been created.
        self.assertEqual(Notification.objects(type="record").count(), 0)

    def test_creates_personal_best_and_notification_on_first_record(self):
        result = services.detect_and_register_new_record(
            user_id="u1", exercise_name="Squat", weight_lifted=100, session_id="s1",
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.max_weight, 100)
        self.assertEqual(Notification.objects(user_id="u1", type="record").count(), 1)

    def test_updates_personal_best_when_record_broken(self):
        PersonalBest.create_first_record("u1", "Squat", 100, session_id="s1")

        result = services.detect_and_register_new_record(
            user_id="u1", exercise_name="Squat", weight_lifted=110, session_id="s2",
        )

        self.assertEqual(result.max_weight, 110)
        self.assertEqual(PersonalBest.objects.count(), 1)  # updated, not duplicated


class CheckDndWindowTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_true_inside_overnight_window(self):
        settings = NotificationSettings(user_id="u1", dnd_start="22:00", dnd_end="08:00")
        scheduled_time = datetime(2026, 6, 1, 23, 0)

        self.assertTrue(services.check_dnd_window(scheduled_time, settings))

    def test_false_outside_window(self):
        settings = NotificationSettings(user_id="u1", dnd_start="22:00", dnd_end="08:00")
        scheduled_time = datetime(2026, 6, 1, 12, 0)

        self.assertFalse(services.check_dnd_window(scheduled_time, settings))


class CreateReminderTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    @patch.object(Reminder, "schedule")
    def test_creates_reminder_outside_dnd_window(self, mock_schedule):
        result = services.create_reminder(
            user_id="u1", title="Workout", message="Time to train",
            channel="push", repeat_type="daily",
            scheduled_time=datetime(2026, 6, 1, 16, 0),  # 16:00, outside default DND
        )

        self.assertEqual(result["status"], "created")
        mock_schedule.assert_called_once()
        self.assertEqual(Reminder.objects.count(), 1)

    def test_returns_dnd_warning_without_confirmation(self):
        result = services.create_reminder(
            user_id="u1", title="Workout", message="Time to train",
            channel="push", repeat_type="daily",
            scheduled_time=datetime(2026, 6, 1, 23, 0),  # inside default DND
        )

        self.assertEqual(result["status"], "dnd_warning")
        self.assertEqual(Reminder.objects.count(), 0)

    @patch.object(Reminder, "schedule")
    def test_creates_reminder_in_dnd_window_when_confirmed(self, mock_schedule):
        result = services.create_reminder(
            user_id="u1", title="Workout", message="Time to train",
            channel="push", repeat_type="daily",
            scheduled_time=datetime(2026, 6, 1, 23, 0),
            confirm_dnd_override=True,
        )

        self.assertEqual(result["status"], "created")
        self.assertEqual(Reminder.objects.count(), 1)


class ProcessDueReminderTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_one_off_reminder_marked_sent_and_not_rescheduled(self):
        reminder = Reminder(
            user_id="u1", title="Workout", message="Go train",
            repeat_type="none", scheduled_time=datetime.utcnow(),
        )
        reminder.save()

        services.process_due_reminder(reminder.reminder_id)

        reloaded = Reminder.objects.get(reminder_id=reminder.reminder_id)
        self.assertEqual(reloaded.status, "sent")
        self.assertEqual(Notification.objects(reminder_id=reminder.reminder_id).count(), 1)

    @patch.object(Reminder, "schedule")
    def test_daily_reminder_is_rescheduled(self, mock_schedule):
        original_time = datetime(2026, 6, 1, 8, 0)
        reminder = Reminder(
            user_id="u1", title="Workout", message="Go train",
            repeat_type="daily", scheduled_time=original_time,
        )
        reminder.save()

        services.process_due_reminder(reminder.reminder_id)

        reloaded = Reminder.objects.get(reminder_id=reminder.reminder_id)
        self.assertEqual(reloaded.scheduled_time, original_time + timedelta(days=1))
        mock_schedule.assert_called_once()

    def test_missing_reminder_is_a_no_op(self):
        # Should not raise even though no such reminder exists.
        services.process_due_reminder("does-not-exist")


class SmartReminderSuggestionTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_suggests_reminder_when_no_recent_workouts(self):
        suggestion = services.get_smart_reminder_suggestion("u1")
        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion["suggested_repeat_type"], "daily")

    def test_no_suggestion_when_recent_workout_exists(self):
        WorkoutSession(
            user_id="u1", exercise_name="Squat", weight_lifted=100, reps=5,
            session_date=datetime.utcnow() - timedelta(days=1),
        ).save()

        suggestion = services.get_smart_reminder_suggestion("u1")
        self.assertIsNone(suggestion)


class NotificationSettingsServiceTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_update_notification_settings_persists_changes(self):
        services.update_notification_settings("u1", push_enabled=False, dnd_start="23:00")

        settings = NotificationSettings.objects.get(user_id="u1")
        self.assertFalse(settings.push_enabled)
        self.assertEqual(settings.dnd_start, "23:00")


class EventSubscriptionServiceTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_notify_event_subscribers_creates_notification_per_subscriber(self):
        services.subscribe_to_event("u1", "product_available", "p1")
        services.subscribe_to_event("u2", "product_available", "p1")

        services.notify_event_subscribers("product_available", "p1", "Back in stock!")

        self.assertEqual(Notification.objects(type="event").count(), 2)


if __name__ == "__main__":
    unittest.main()
