"""
Unit tests for models.py.

These tests use mongomock (an in-memory fake MongoDB) instead of a real
MongoDB instance, so they run fast and don't require Docker/DB access.
Each test class connects to a fresh mongomock database and drops every
collection it touches in tearDown, so tests never leak state into each
other.
"""

import unittest
from datetime import datetime, timedelta

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


def _connect_test_db():
    """
    Connect mongoengine to an in-memory mongomock database.
    Safe to call multiple times: disconnects any previous connection
    first so tests don't accidentally share state with a real DB
    connection made elsewhere (e.g. by apps.py in a running server).
    """
    mongoengine.disconnect()
    mongoengine.connect(db="team7_test", host="mongomock://localhost")


def _drop_all_collections():
    """Clear every collection used by these models between tests."""
    for model in (
        PhysicalRecord, Goal, WorkoutSession, PersonalBest, Reminder,
        NotificationSettings, Notification, DeviceToken, EventSubscription,
    ):
        model.drop_collection()


class PhysicalRecordTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_calculate_bmi_computes_expected_value(self):
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75)
        bmi = record.calculate_bmi()
        # 70 / 1.75^2 = 22.857...
        self.assertAlmostEqual(bmi, 22.86, places=2)
        self.assertAlmostEqual(record.bmi, 22.86, places=2)

    def test_calculate_bmi_raises_on_zero_height(self):
        record = PhysicalRecord(user_id="u1", weight=70, height=0)
        with self.assertRaises(ValueError):
            record.calculate_bmi()

    def test_calculate_bmi_does_not_save_by_itself(self):
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75)
        record.calculate_bmi()
        # Nothing should be persisted until the caller explicitly saves.
        self.assertEqual(PhysicalRecord.objects.count(), 0)

    def test_compare_with_goal_weight_reached(self):
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75, body_fat_percent=15)
        goal = Goal(user_id="u1", target_weight=72, target_body_fat=14)

        result = record.compare_with_goal(goal)

        self.assertEqual(result["weight_diff"], -2)
        self.assertTrue(result["weight_goal_reached"])
        self.assertEqual(result["body_fat_diff"], 1)
        self.assertFalse(result["body_fat_goal_reached"])

    def test_compare_with_goal_ignores_unset_targets(self):
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75)
        goal = Goal(user_id="u1")  # no targets set at all

        result = record.compare_with_goal(goal)

        self.assertIsNone(result["weight_diff"])
        self.assertIsNone(result["weight_goal_reached"])
        self.assertIsNone(result["body_fat_diff"])
        self.assertIsNone(result["body_fat_goal_reached"])


class GoalTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_is_reached_true_when_all_targets_met(self):
        goal = Goal(user_id="u1", target_weight=72, target_body_fat=15)
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75, body_fat_percent=14)

        self.assertTrue(goal.is_reached(record))

    def test_is_reached_false_when_one_target_not_met(self):
        goal = Goal(user_id="u1", target_weight=72, target_body_fat=10)
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75, body_fat_percent=14)

        self.assertFalse(goal.is_reached(record))

    def test_is_reached_false_when_no_targets_set(self):
        goal = Goal(user_id="u1")
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75)

        self.assertFalse(goal.is_reached(record))


class PersonalBestTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_is_new_record_true_when_no_existing_record(self):
        self.assertTrue(PersonalBest.is_new_record("u1", "Squat", 100))

    def test_is_new_record_true_when_weight_exceeds_existing(self):
        PersonalBest.create_first_record("u1", "Squat", 100, session_id="s1")
        self.assertTrue(PersonalBest.is_new_record("u1", "Squat", 105))

    def test_is_new_record_false_when_weight_does_not_exceed_existing(self):
        PersonalBest.create_first_record("u1", "Squat", 100, session_id="s1")
        self.assertFalse(PersonalBest.is_new_record("u1", "Squat", 90))
        self.assertFalse(PersonalBest.is_new_record("u1", "Squat", 100))

    def test_update_record_persists_new_values(self):
        pb = PersonalBest.create_first_record("u1", "Squat", 100, session_id="s1")
        pb.update_record(new_weight=110, session_id="s2")

        reloaded = PersonalBest.objects.get(pb_id=pb.pb_id)
        self.assertEqual(reloaded.max_weight, 110)
        self.assertEqual(reloaded.session_id, "s2")
        self.assertIsNotNone(reloaded.updated_at)


class ReminderTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_is_in_dnd_window_same_day_window(self):
        reminder = Reminder(
            user_id="u1", title="t",
            scheduled_time=datetime(2026, 6, 1, 14, 0),  # 14:00
        )
        self.assertTrue(reminder.is_in_dnd_window("13:00", "15:00"))
        self.assertFalse(reminder.is_in_dnd_window("15:00", "16:00"))

    def test_is_in_dnd_window_overnight_window(self):
        # DND window 22:00 -> 08:00 wraps past midnight.
        late_night = Reminder(
            user_id="u1", title="t",
            scheduled_time=datetime(2026, 6, 1, 23, 30),  # 23:30
        )
        early_morning = Reminder(
            user_id="u1", title="t",
            scheduled_time=datetime(2026, 6, 1, 7, 0),  # 07:00
        )
        daytime = Reminder(
            user_id="u1", title="t",
            scheduled_time=datetime(2026, 6, 1, 12, 0),  # 12:00
        )

        self.assertTrue(late_night.is_in_dnd_window("22:00", "08:00"))
        self.assertTrue(early_morning.is_in_dnd_window("22:00", "08:00"))
        self.assertFalse(daytime.is_in_dnd_window("22:00", "08:00"))

    def test_status_transition_helpers(self):
        reminder = Reminder(
            user_id="u1", title="t", scheduled_time=datetime.utcnow(),
        )
        reminder.save()

        reminder.mark_sent()
        self.assertEqual(reminder.status, "sent")

        reminder.mark_completed()
        self.assertEqual(reminder.status, "completed")

        reminder.mark_expired()
        self.assertEqual(reminder.status, "expired")


class NotificationSettingsTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_get_or_create_default_creates_once(self):
        settings1 = NotificationSettings.get_or_create_default("u1")
        settings2 = NotificationSettings.get_or_create_default("u1")

        self.assertEqual(settings1.setting_id, settings2.setting_id)
        self.assertEqual(NotificationSettings.objects.count(), 1)
        self.assertTrue(settings1.push_enabled)
        self.assertEqual(settings1.dnd_start, "22:00")


class NotificationTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_mark_as_read(self):
        notification = Notification(user_id="u1", type="system", content="hello")
        notification.save()

        self.assertFalse(notification.is_read)
        notification.mark_as_read()

        reloaded = Notification.objects.get(notification_id=notification.notification_id)
        self.assertTrue(reloaded.is_read)


class DeviceTokenTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_tokens_for_user_excludes_deleted_and_other_users(self):
        DeviceToken(user_id="u1", fcm_token="tok-a").save()
        DeviceToken(user_id="u1", fcm_token="tok-b").save()
        DeviceToken(user_id="u1", fcm_token="tok-c", is_deleted=True).save()
        DeviceToken(user_id="u2", fcm_token="tok-d").save()

        tokens = DeviceToken.tokens_for_user("u1")

        self.assertCountEqual(tokens, ["tok-a", "tok-b"])


class EventSubscriptionTests(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect()

    def test_subscribers_for_matches_event_and_reference(self):
        EventSubscription(user_id="u1", event_type="product_available", reference_id="p1").save()
        EventSubscription(user_id="u2", event_type="product_available", reference_id="p1").save()
        EventSubscription(user_id="u3", event_type="product_available", reference_id="p2").save()

        subscribers = EventSubscription.subscribers_for("product_available", "p1")

        self.assertCountEqual(subscribers, ["u1", "u2"])


if __name__ == "__main__":
    unittest.main()
