"""Comprehensive unit tests for models.py using mongomock."""

import unittest
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import mongoengine
import mongomock

from models import (
    DeviceToken,
    EventSubscription,
    Goal,
    Notification,
    NotificationSettings,
    PersonalBest,
    PhysicalRecord,
    Reminder,
    WorkoutSession,
    gen_id,
)


ALL_MODELS = (
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
    mongoengine.disconnect(alias="default")
    mongoengine.connect(
        db="team7_test",
        alias="default",
        host="mongodb://localhost",
        mongo_client_class=mongomock.MongoClient,
        tz_aware=True,
    )


def _drop_all_collections():
    for model in ALL_MODELS:
        model.drop_collection()


class MongoTestCase(unittest.TestCase):
    def setUp(self):
        _connect_test_db()

    def tearDown(self):
        _drop_all_collections()
        mongoengine.disconnect(alias="default")


class UtilityTests(MongoTestCase):
    def test_gen_id_returns_unique_valid_uuid_strings(self):
        first, second = gen_id(), gen_id()
        self.assertIsInstance(first, str)
        self.assertNotEqual(first, second)
        self.assertEqual(str(uuid.UUID(first)), first)


class PhysicalRecordTests(MongoTestCase):
    def test_defaults_and_generated_id_are_persisted(self):
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75).save()
        self.assertIsNotNone(record.record_id)
        self.assertIsNotNone(record.created_at)
        self.assertIsNone(record.updated_at)
        self.assertFalse(record.is_deleted)

    def test_calculate_bmi_computes_expected_value_without_saving(self):
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75)
        self.assertEqual(record.calculate_bmi(), 22.86)
        self.assertEqual(record.bmi, 22.86)
        self.assertEqual(PhysicalRecord.objects.count(), 0)

    def test_calculate_bmi_rejects_non_positive_height_or_weight(self):
        for kwargs in (
            {"weight": 70, "height": 0},
            {"weight": 70, "height": -1},
            {"weight": 0, "height": 1.75},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    PhysicalRecord(user_id="u1", **kwargs).calculate_bmi()

    def test_field_validation_rejects_invalid_values(self):
        invalid_records = (
            PhysicalRecord(user_id="", weight=70, height=1.75),
            PhysicalRecord(user_id="u1", weight=-1, height=1.75),
            PhysicalRecord(user_id="u1", weight=70, height=-1),
            PhysicalRecord(user_id="u1", weight=70, height=1.75, body_fat_percent=101),
        )
        for record in invalid_records:
            with self.subTest(record=record.to_mongo().to_dict()):
                with self.assertRaises(mongoengine.ValidationError):
                    record.validate()

    def test_compare_with_goal_for_loss_gain_and_maintenance(self):
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75)
        self.assertTrue(record.compare_with_goal(Goal(user_id="u1", target_weight=72))["weight_goal_reached"])
        self.assertTrue(record.compare_with_goal(Goal(user_id="u1", target_weight=68, weight_goal_type="gain"))["weight_goal_reached"])
        result = record.compare_with_goal(
            Goal(user_id="u1", target_weight=70.4, weight_goal_type="maintain", weight_tolerance=0.5)
        )
        self.assertTrue(result["weight_goal_reached"])

    def test_compare_with_goal_handles_missing_and_present_body_fat(self):
        record = PhysicalRecord(user_id="u1", weight=70, height=1.75, body_fat_percent=15)
        result = record.compare_with_goal(Goal(user_id="u1", target_body_fat=14))
        self.assertEqual(result["body_fat_diff"], 1)
        self.assertFalse(result["body_fat_goal_reached"])

        missing = PhysicalRecord(user_id="u1", weight=70, height=1.75)
        result = missing.compare_with_goal(Goal(user_id="u1", target_body_fat=14))
        self.assertIsNone(result["body_fat_diff"])
        self.assertFalse(result["body_fat_goal_reached"])

    def test_compare_with_goal_rejects_cross_user_comparison(self):
        with self.assertRaises(ValueError):
            PhysicalRecord(user_id="u1", weight=70, height=1.75).compare_with_goal(
                Goal(user_id="u2", target_weight=70)
            )


class GoalTests(MongoTestCase):
    def test_is_reached_requires_every_configured_target(self):
        goal = Goal(user_id="u1", target_weight=72, target_body_fat=15)
        self.assertTrue(goal.is_reached(PhysicalRecord(user_id="u1", weight=70, height=1.75, body_fat_percent=14)))
        self.assertFalse(goal.is_reached(PhysicalRecord(user_id="u1", weight=70, height=1.75, body_fat_percent=16)))
        self.assertFalse(goal.is_reached(PhysicalRecord(user_id="u1", weight=70, height=1.75)))

    def test_is_reached_is_false_without_targets(self):
        self.assertFalse(
            Goal(user_id="u1").is_reached(
                PhysicalRecord(user_id="u1", weight=70, height=1.75)
            )
        )

    def test_active_goal_is_unique_but_soft_deleted_goal_does_not_block_new_one(self):
        Goal(user_id="u1", target_weight=70).save()
        with self.assertRaises(mongoengine.NotUniqueError):
            Goal(user_id="u1", target_weight=65).save()

        Goal.objects(user_id="u1").update(set__is_deleted=True)
        new_goal = Goal(user_id="u1", target_weight=65).save()
        self.assertEqual(new_goal.target_weight, 65)


class WorkoutSessionTests(MongoTestCase):
    def test_valid_session_is_normalized_and_saved(self):
        session = WorkoutSession(
            user_id="u1",
            exercise_name="  Bench   Press ",
            weight_lifted=80,
            reps=8,
            session_date=datetime.now(timezone.utc),
        ).save()
        self.assertEqual(session.exercise_name, "Bench Press")
        self.assertFalse(session.is_deleted)
        self.assertIsNotNone(session.created_at)

    def test_required_fields_and_numeric_constraints(self):
        invalid = (
            WorkoutSession(user_id="u1", exercise_name="Squat"),
            WorkoutSession(user_id="u1", exercise_name=" ", session_date=datetime.now(timezone.utc)),
            WorkoutSession(user_id="u1", exercise_name="Squat", reps=0, session_date=datetime.now(timezone.utc)),
            WorkoutSession(user_id="u1", exercise_name="Squat", weight_lifted=-1, session_date=datetime.now(timezone.utc)),
        )
        for session in invalid:
            with self.subTest(session=session.to_mongo().to_dict()):
                with self.assertRaises(mongoengine.ValidationError):
                    session.validate()


class PersonalBestTests(MongoTestCase):
    def test_create_first_record_and_is_new_record(self):
        pb = PersonalBest.create_first_record("u1", "  Squat ", 100, "s1")
        self.assertEqual(pb.exercise_name, "Squat")
        self.assertEqual(pb.max_weight, 100)
        self.assertTrue(PersonalBest.is_new_record("u1", "Squat", 105))
        self.assertFalse(PersonalBest.is_new_record("u1", "Squat", 100))
        self.assertFalse(PersonalBest.is_new_record("u1", "Squat", 90))

    def test_is_new_record_ignores_soft_deleted_record(self):
        PersonalBest.create_first_record("u1", "Squat", 200, "s1").update(is_deleted=True)
        self.assertTrue(PersonalBest.is_new_record("u1", "Squat", 100))

    def test_is_new_record_rejects_negative_weight(self):
        with self.assertRaises(ValueError):
            PersonalBest.is_new_record("u1", "Squat", -1)

    def test_update_record_persists_values_and_requires_improvement(self):
        pb = PersonalBest.create_first_record("u1", "Squat", 100, "s1")
        created_at = pb.created_at
        result = pb.update_record(110, "s2")
        self.assertIs(result, pb)
        reloaded = PersonalBest.objects.get(pb_id=pb.pb_id)
        self.assertEqual(reloaded.max_weight, 110)
        self.assertEqual(reloaded.session_id, "s2")
        self.assertIsNotNone(reloaded.updated_at)
        self.assertLess(abs((reloaded.created_at - created_at).total_seconds()), 0.001)
        with self.assertRaises(ValueError):
            pb.update_record(110, "s3")

    def test_active_personal_best_is_unique(self):
        PersonalBest.create_first_record("u1", "Squat", 100, "s1")
        with self.assertRaises(mongoengine.NotUniqueError):
            PersonalBest.create_first_record("u1", "Squat", 110, "s2")

    def test_register_if_better_creates_updates_and_ignores_lower_value(self):
        first, changed = PersonalBest.register_if_better("u1", "Squat", 100, "s1")
        self.assertTrue(changed)
        self.assertEqual(first.max_weight, 100)

        lower, changed = PersonalBest.register_if_better("u1", "Squat", 90, "s2")
        self.assertFalse(changed)
        self.assertEqual(lower.max_weight, 100)

        higher, changed = PersonalBest.register_if_better("u1", "Squat", 110, "s3")
        self.assertTrue(changed)
        self.assertEqual(higher.max_weight, 110)


class ReminderTests(MongoTestCase):
    def _reminder(self, hour=12, minute=0):
        return Reminder(
            user_id="u1",
            title="Workout",
            scheduled_time=datetime(2026, 6, 1, hour, minute, tzinfo=timezone.utc),
        )

    def test_dnd_same_day_and_overnight_boundaries(self):
        self.assertTrue(self._reminder(13).is_in_dnd_window("13:00", "15:00"))
        self.assertFalse(self._reminder(15).is_in_dnd_window("13:00", "15:00"))
        self.assertTrue(self._reminder(22).is_in_dnd_window("22:00", "08:00"))
        self.assertTrue(self._reminder(7, 59).is_in_dnd_window("22:00", "08:00"))
        self.assertFalse(self._reminder(8).is_in_dnd_window("22:00", "08:00"))
        self.assertFalse(self._reminder(12).is_in_dnd_window("22:00", "22:00"))

    def test_dnd_rejects_invalid_time_strings(self):
        for invalid in ("25:00", "12:60", "abc", "12"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(mongoengine.ValidationError):
                    self._reminder().is_in_dnd_window(invalid, "08:00")

    def test_schedule_enqueues_and_persists_task_id(self):
        task = Mock()
        task.apply_async.return_value = SimpleNamespace(id="task-1")
        reminder = self._reminder().save()
        result = reminder.schedule(task=task)
        self.assertIs(result, reminder)
        task.apply_async.assert_called_once_with(
            args=[reminder.reminder_id], eta=reminder.scheduled_time
        )
        reminder.reload()
        self.assertEqual(reminder.status, "scheduled")
        self.assertEqual(reminder.celery_task_id, "task-1")
        self.assertIsNone(reminder.last_error)

    def test_schedule_failure_is_recorded_and_reraised(self):
        task = Mock()
        task.apply_async.side_effect = RuntimeError("broker down")
        reminder = self._reminder().save()
        with self.assertRaisesRegex(RuntimeError, "broker down"):
            reminder.schedule(task=task)
        reminder.reload()
        self.assertEqual(reminder.status, "failed")
        self.assertEqual(reminder.last_error, "broker down")

    def test_schedule_rejects_duplicate_scheduling(self):
        task = Mock()
        task.apply_async.return_value = SimpleNamespace(id="task-1")
        reminder = self._reminder().save().schedule(task=task)
        with self.assertRaises(ValueError):
            reminder.schedule(task=task)

    def test_valid_and_invalid_status_transitions(self):
        reminder = self._reminder().save()
        reminder.transition_to("scheduled").mark_sent().mark_completed()
        reminder.reload()
        self.assertEqual(reminder.status, "completed")
        with self.assertRaises(ValueError):
            reminder.mark_expired()

        another = self._reminder().save().transition_to("scheduled")
        another.mark_expired()
        self.assertEqual(another.status, "expired")

    def test_choices_are_validated(self):
        for field, value in (("channel", "fax"), ("repeat_type", "hourly"), ("status", "unknown")):
            reminder = self._reminder()
            setattr(reminder, field, value)
            with self.subTest(field=field):
                with self.assertRaises(mongoengine.ValidationError):
                    reminder.validate()


class NotificationSettingsTests(MongoTestCase):
    def test_get_or_create_default_creates_once_with_all_defaults(self):
        first = NotificationSettings.get_or_create_default("u1")
        second = NotificationSettings.get_or_create_default("u1")
        self.assertEqual(first.setting_id, second.setting_id)
        self.assertEqual(NotificationSettings.objects.count(), 1)
        self.assertTrue(first.push_enabled)
        self.assertFalse(first.sms_enabled)
        self.assertFalse(first.email_enabled)
        self.assertEqual(first.dnd_start, "22:00")
        self.assertEqual(first.dnd_end, "08:00")
        self.assertEqual(first.timezone_name, "UTC")

    def test_soft_deleted_settings_do_not_block_new_active_settings(self):
        NotificationSettings(user_id="u1", is_deleted=True).save()
        active = NotificationSettings.get_or_create_default("u1")
        self.assertFalse(active.is_deleted)
        self.assertEqual(NotificationSettings.objects(user_id="u1").count(), 2)

    def test_invalid_dnd_format_is_rejected(self):
        settings = NotificationSettings(user_id="u1", dnd_start="9:00")
        with self.assertRaises(mongoengine.ValidationError):
            settings.validate()


class NotificationTests(MongoTestCase):
    def test_mark_as_read_persists_and_returns_self(self):
        notification = Notification(user_id="u1", type="system", content="hello").save()
        self.assertIs(notification.mark_as_read(), notification)
        notification.reload()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.updated_at)

    def test_send_success_records_delivery_metadata(self):
        sender = Mock(return_value=SimpleNamespace(message_id="provider-1"))
        notification = Notification(
            user_id="u1", type="system", title="Hello", content="World"
        ).save()
        notification.send(sender=sender)
        sender.assert_called_once_with(user_id="u1", title="Hello", message="World")
        notification.reload()
        self.assertEqual(notification.delivery_status, "sent")
        self.assertEqual(notification.provider_message_id, "provider-1")
        self.assertIsNotNone(notification.sent_at)

    def test_send_failure_records_error_and_retry_count(self):
        sender = Mock(side_effect=RuntimeError("FCM error"))
        notification = Notification(user_id="u1", type="system", content="World").save()
        with self.assertRaisesRegex(RuntimeError, "FCM error"):
            notification.send(sender=sender)
        notification.reload()
        self.assertEqual(notification.delivery_status, "failed")
        self.assertEqual(notification.retry_count, 1)
        self.assertEqual(notification.last_error, "FCM error")
        self.assertIsNotNone(notification.failed_at)

    def test_required_fields_and_choices_are_validated(self):
        invalid = (
            Notification(user_id="u1", type="invalid", content="hello"),
            Notification(user_id="u1", type="system", content=" "),
            Notification(type="system", content="hello"),
        )
        for notification in invalid:
            with self.subTest(notification=notification.to_mongo().to_dict()):
                with self.assertRaises(mongoengine.ValidationError):
                    notification.validate()


class DeviceTokenTests(MongoTestCase):
    def test_tokens_for_user_filters_deleted_and_other_users(self):
        DeviceToken(user_id="u1", fcm_token="tok-a").save()
        DeviceToken(user_id="u1", fcm_token="tok-b").save()
        DeviceToken(user_id="u1", fcm_token="tok-c", is_deleted=True).save()
        DeviceToken(user_id="u2", fcm_token="tok-d").save()
        self.assertCountEqual(DeviceToken.tokens_for_user("u1"), ["tok-a", "tok-b"])
        self.assertEqual(DeviceToken.tokens_for_user("missing"), [])

    def test_token_is_unique_and_non_blank(self):
        DeviceToken(user_id="u1", fcm_token="tok-a").save()
        with self.assertRaises(mongoengine.NotUniqueError):
            DeviceToken(user_id="u2", fcm_token="tok-a").save()
        with self.assertRaises(mongoengine.ValidationError):
            DeviceToken(user_id="u1", fcm_token=" ").validate()


class EventSubscriptionTests(MongoTestCase):
    def test_subscribers_for_filters_reference_type_and_soft_delete(self):
        EventSubscription(user_id="u1", event_type="product_available", reference_id="p1").save()
        EventSubscription(user_id="u2", event_type="product_available", reference_id="p1").save()
        EventSubscription(user_id="u3", event_type="product_available", reference_id="p2").save()
        EventSubscription(user_id="u4", event_type="challenge_start", reference_id="p1").save()
        EventSubscription(user_id="u5", event_type="product_available", reference_id="p1", is_deleted=True).save()
        self.assertCountEqual(
            EventSubscription.subscribers_for("product_available", "p1"),
            ["u1", "u2"],
        )

    def test_active_subscription_is_unique_but_deleted_one_does_not_block_new(self):
        EventSubscription(user_id="u1", event_type="product_available", reference_id="p1").save()
        with self.assertRaises(mongoengine.NotUniqueError):
            EventSubscription(user_id="u1", event_type="product_available", reference_id="p1").save()
        EventSubscription.objects(user_id="u1").update(set__is_deleted=True)
        EventSubscription(user_id="u1", event_type="product_available", reference_id="p1").save()

    def test_event_choice_and_reference_validation(self):
        with self.assertRaises(mongoengine.ValidationError):
            EventSubscription(user_id="u1", event_type="unknown", reference_id="p1").validate()
        with self.assertRaises(mongoengine.ValidationError):
            EventSubscription(user_id="u1", event_type="product_available", reference_id=" ").validate()


if __name__ == "__main__":
    unittest.main()
