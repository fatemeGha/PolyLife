"""
Unit tests for services.py.

The suite uses mongomock instead of a real MongoDB server and replaces
external integrations such as Redis, Celery, and Firebase with small fakes.
It covers the public service API as well as important internal helper branches.

Run from inside teams/team7 with:
    python -m unittest tests.test_services -v

Run from the repository root with:
    python -m unittest teams.team7.tests.test_services -v
"""

from __future__ import annotations

import json
import os
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import mongoengine
import mongomock

# Support both execution layouts documented above.
if __package__ in (None, "", "tests"):
    import services
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
        utc_now,
    )
else:
    from .. import services
    from ..models import (
        DeviceToken,
        EventSubscription,
        Goal,
        Notification,
        NotificationSettings,
        PersonalBest,
        PhysicalRecord,
        Reminder,
        WorkoutSession,
        utc_now,
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
    """Connect MongoEngine to an isolated in-memory mongomock database."""
    mongoengine.disconnect()
    mongoengine.connect(
        db="team7_services_test",
        host="mongodb://localhost",
        mongo_client_class=mongomock.MongoClient,
        uuidRepresentation="standard",
    )


def _drop_all_collections():
    """Drop every collection touched by services.py between tests."""
    for model in ALL_MODELS:
        model.drop_collection()


class FakeAsyncResult:
    """Minimal Celery AsyncResult replacement used by Reminder.schedule()."""

    def __init__(self, task_id="task-1"):
        self.id = task_id


class FakeTask:
    """Record apply_async calls without requiring a Celery worker."""

    def __init__(self, task_id="task-1", error=None):
        self.task_id = task_id
        self.error = error
        self.calls = []

    def apply_async(self, *, args, eta):
        """Capture scheduling arguments and optionally raise an injected error."""
        self.calls.append({"args": args, "eta": eta})
        if self.error is not None:
            raise self.error
        return FakeAsyncResult(self.task_id)


class FakeRedis:
    """Small Redis-compatible fake supporting get, set, delete, and ping."""

    def __init__(self):
        self.data = {}
        self.set_calls = []
        self.deleted = []
        self.fail_get = False
        self.fail_set = False
        self.fail_delete = False

    def ping(self):
        """Pretend the Redis server is reachable."""
        return True

    def get(self, key):
        """Return a cached value or raise an injected connection failure."""
        if self.fail_get:
            raise RuntimeError("redis get failed")
        return self.data.get(key)

    def set(self, key, value, ex=None):
        """Store a value and remember its TTL."""
        if self.fail_set:
            raise RuntimeError("redis set failed")
        self.data[key] = value
        self.set_calls.append((key, value, ex))

    def delete(self, key):
        """Delete a key or raise an injected connection failure."""
        if self.fail_delete:
            raise RuntimeError("redis delete failed")
        self.deleted.append(key)
        self.data.pop(key, None)


class ServicesTestCase(unittest.TestCase):
    """Provide a clean database and reset module-level Redis state per test."""

    def setUp(self):
        """Connect to mongomock and reset shared service state."""
        _connect_test_db()
        services._reset_redis_client()

    def tearDown(self):
        """Drop test data and disconnect MongoEngine."""
        _drop_all_collections()
        services._reset_redis_client()
        mongoengine.disconnect()

    def make_session(
        self,
        *,
        user_id="u1",
        exercise_name="Squat",
        weight_lifted=100,
        session_id=None,
        days_ago=0,
    ):
        """Create a valid WorkoutSession with a predictable timestamp."""
        kwargs = {}
        if session_id is not None:
            kwargs["session_id"] = session_id
        return WorkoutSession(
            user_id=user_id,
            exercise_name=exercise_name,
            weight_lifted=weight_lifted,
            reps=5,
            session_date=utc_now() - timedelta(days=days_ago),
            **kwargs,
        ).save()


class PhysicalDataServiceTests(ServicesTestCase):
    """Cover physical-record create, edit, delete, and cache invalidation."""

    @patch.object(services, "_invalidate_chart_cache")
    def test_register_creates_bmi_and_invalidates_cache(self, invalidate):
        """A valid registration persists BMI and invalidates chart data."""
        record = services.register_physical_data("u1", 70, 1.75, 15, 30)
        self.assertAlmostEqual(record.bmi, 22.86)
        self.assertEqual(PhysicalRecord.objects.count(), 1)
        invalidate.assert_called_once_with("u1")

    def test_register_relies_on_model_validation(self):
        """Invalid physical input is rejected by model validation."""
        with self.assertRaises((ValueError, mongoengine.ValidationError)):
            services.register_physical_data("u1", 0, 1.75)
        with self.assertRaises(mongoengine.ValidationError):
            services.register_physical_data("u1", 70, 1.75, body_fat_percent=101)

    @patch.object(services, "_invalidate_chart_cache")
    def test_edit_allows_only_whitelisted_fields_and_can_clear_optional_value(self, invalidate):
        """Editing rejects protected fields and permits clearing optional metrics."""
        record = services.register_physical_data("u1", 70, 1.75, 15, 30)
        updated = services.edit_physical_data(
            record.record_id,
            weight=68,
            body_fat_percent=None,
        )
        self.assertEqual(updated.weight, 68)
        self.assertIsNone(updated.body_fat_percent)
        self.assertAlmostEqual(updated.bmi, round(68 / 1.75**2, 2))
        self.assertIsNotNone(updated.updated_at)
        self.assertGreaterEqual(invalidate.call_count, 2)

        with self.assertRaises(ValueError):
            services.edit_physical_data(record.record_id, user_id="other")

    @patch.object(services, "_invalidate_chart_cache")
    def test_delete_soft_deletes_and_invalidates(self, invalidate):
        """Deletion keeps the document while removing it from active queries."""
        record = services.register_physical_data("u1", 70, 1.75)
        deleted = services.delete_physical_data(record.record_id)
        self.assertTrue(deleted.is_deleted)
        self.assertEqual(PhysicalRecord.objects(is_deleted=False).count(), 0)
        self.assertIsNotNone(deleted.updated_at)
        self.assertGreaterEqual(invalidate.call_count, 2)


class ProgressChartTests(ServicesTestCase):
    """Cover cache hit, cache miss, corruption, filtering, sorting, and goals."""

    def _save_record(self, weight, days_ago):
        """Persist one chartable physical record at a relative date."""
        record = PhysicalRecord(
            user_id="u1",
            weight=weight,
            height=1.75,
            created_at=utc_now() - timedelta(days=days_ago),
        )
        record.calculate_bmi()
        return record.save()

    def test_invalid_period_is_rejected(self):
        """Unknown chart periods fail explicitly instead of defaulting silently."""
        with self.assertRaises(ValueError):
            services.get_progress_chart_data("u1", "quarter")

    @patch.object(services, "_redis_get")
    def test_valid_cache_hit_returns_without_database_query(self, redis_get):
        """A valid cached JSON document is returned directly."""
        redis_get.return_value = json.dumps({"period": "month", "points": [{"weight": 1}]})
        result = services.get_progress_chart_data("u1", "month")
        self.assertEqual(result["points"][0]["weight"], 1)

    @patch.object(services, "_redis_set")
    @patch.object(services, "_redis_delete")
    @patch.object(services, "_redis_get", return_value="not-json")
    def test_corrupt_cache_is_deleted_and_rebuilt(self, _get, redis_delete, redis_set):
        """Malformed cache content is discarded before rebuilding the result."""
        self._save_record(75, 2)
        result = services.get_progress_chart_data("u1", "month")
        self.assertEqual(len(result["points"]), 1)
        redis_delete.assert_called_once_with("chart:u1:month")
        redis_set.assert_called_once()

    @patch.object(services, "_redis_get", return_value=None)
    @patch.object(services, "_redis_set")
    def test_filters_sorts_and_includes_goal_comparison(self, redis_set, _get):
        """Only active in-range records are sorted and compared with the goal."""
        self._save_record(80, 40)
        self._save_record(76, 3)
        self._save_record(75, 1)
        deleted = self._save_record(74, 1)
        deleted.update(set__is_deleted=True)
        Goal(user_id="u1", target_weight=70).save()

        result = services.get_progress_chart_data("u1", "month")
        self.assertEqual([point["weight"] for point in result["points"]], [76, 75])
        self.assertEqual(result["points"][0]["goal_comparison"]["weight_diff"], 6)
        self.assertIn("+00:00", result["points"][0]["date"])
        redis_set.assert_called_once()
        self.assertEqual(redis_set.call_args.kwargs["ttl_seconds"], 300)


class GoalAndMentorTests(ServicesTestCase):
    """Cover goal sentinel behavior, clearing, caching, and mentor authorization."""

    @patch.object(services, "_invalidate_chart_cache")
    def test_set_goal_creates_updates_and_preserves_omitted_fields(self, invalidate):
        """Goal updates distinguish omitted values from explicit clearing."""
        goal = services.set_user_goal(
            "u1",
            target_weight=70,
            target_body_fat=15,
            weight_goal_type="lose",
            weight_tolerance=1,
        )
        updated = services.set_user_goal("u1", target_weight=68)
        self.assertEqual(goal.goal_id, updated.goal_id)
        self.assertEqual(updated.target_weight, 68)
        self.assertEqual(updated.target_body_fat, 15)
        self.assertEqual(updated.weight_tolerance, 1)
        self.assertEqual(invalidate.call_count, 2)

    def test_set_goal_allows_one_target_to_be_cleared_but_not_all(self):
        """An optional target can be cleared while an empty goal is rejected."""
        services.set_user_goal("u1", target_weight=70, target_body_fat=15)
        goal = services.set_user_goal("u1", target_body_fat=None)
        self.assertIsNone(goal.target_body_fat)
        self.assertEqual(goal.target_weight, 70)
        with self.assertRaises(ValueError):
            services.set_user_goal("u1", target_weight=None)

    def test_mentor_report_fails_closed_without_checker(self):
        """Mentor data is denied when no Core authorization checker is supplied."""
        with self.assertRaises(PermissionError):
            services.get_mentor_report("t1", "u1")

    @patch.object(services, "get_progress_chart_data", return_value={"period": "month", "points": []})
    def test_mentor_report_returns_sorted_personal_bests_when_authorized(self, chart):
        """An authorized trainer receives chart data and sorted personal bests."""
        PersonalBest.create_first_record("u1", "Squat", 100, "s1")
        PersonalBest.create_first_record("u1", "Bench", 80, "s2")
        report = services.get_mentor_report("t1", "u1", lambda trainer, athlete: True)
        self.assertEqual(report["athlete_id"], "u1")
        self.assertEqual(
            [item["exercise_name"] for item in report["personal_bests"]],
            ["Bench", "Squat"],
        )
        chart.assert_called_once_with("u1", period="month")


class PersonalBestServiceTests(ServicesTestCase):
    """Cover session verification, atomic PB updates, and notification dispatch."""

    def test_missing_or_cross_user_session_is_rejected(self):
        """A personal best cannot reference a missing or foreign session."""
        with self.assertRaises(WorkoutSession.DoesNotExist):
            services.detect_and_register_new_record("u1", "Squat", 100, "missing")
        session = self.make_session(user_id="u2", session_id="s1")
        with self.assertRaises(WorkoutSession.DoesNotExist):
            services.detect_and_register_new_record("u1", "Squat", 100, session.session_id)

    def test_session_exercise_and_weight_must_match(self):
        """The submitted exercise and weight must agree with the saved session."""
        session = self.make_session(exercise_name="Back   Squat", weight_lifted=100)
        with self.assertRaises(ValueError):
            services.detect_and_register_new_record("u1", "Bench", 100, session.session_id)
        with self.assertRaises(ValueError):
            services.detect_and_register_new_record("u1", "Back Squat", 101, session.session_id)

    def test_first_record_creates_pb_and_sent_notification(self):
        """A first personal best creates one delivered congratulations notification."""
        session = self.make_session(exercise_name="Back   Squat", weight_lifted=100)
        sender = MagicMock(return_value=services.PushSendResult("m1", 1, 0))
        pb = services.detect_and_register_new_record(
            "u1", "Back Squat", 100, session.session_id, sender
        )
        self.assertEqual(pb.exercise_name, "Back Squat")
        self.assertLess(
            abs(
                pb.achieved_date.replace(tzinfo=timezone.utc)
                - session.session_date.replace(tzinfo=timezone.utc)
            ),
            timedelta(milliseconds=1),
        )
        notification = Notification.objects.get(type="record")
        self.assertEqual(notification.delivery_status, "sent")
        sender.assert_called_once()

    def test_non_improving_record_returns_none_without_notification(self):
        """A lower or equal lift does not create a new notification."""
        PersonalBest.create_first_record("u1", "Squat", 110, "old")
        session = self.make_session(weight_lifted=100)
        result = services.detect_and_register_new_record(
            "u1", "Squat", 100, session.session_id, MagicMock()
        )
        self.assertIsNone(result)
        self.assertEqual(Notification.objects.count(), 0)

    def test_sender_failure_is_recorded_and_reraised(self):
        """Push failure leaves a failed notification and propagates the error."""
        session = self.make_session(weight_lifted=100)
        sender = MagicMock(side_effect=RuntimeError("provider down"))
        with self.assertRaisesRegex(RuntimeError, "provider down"):
            services.detect_and_register_new_record(
                "u1", "Squat", 100, session.session_id, sender
            )
        notification = Notification.objects.get(type="record")
        self.assertEqual(notification.delivery_status, "failed")
        self.assertEqual(notification.retry_count, 1)


class DndAndReminderCrudTests(ServicesTestCase):
    """Cover timezone-aware DND checks and reminder create/edit/delete flows."""

    def test_check_dnd_uses_timezone_and_rejects_unknown_zone(self):
        """DND comparison is performed in the configured IANA timezone."""
        settings = NotificationSettings(
            user_id="u1",
            dnd_start="22:00",
            dnd_end="08:00",
            timezone_name="Asia/Baku",
        )
        # 19:00 UTC is 23:00 in Baku during summer.
        self.assertTrue(
            services.check_dnd_window(datetime(2026, 6, 1, 19, tzinfo=timezone.utc), settings)
        )
        settings.timezone_name = "Mars/Olympus"
        with self.assertRaises(ValueError):
            services.check_dnd_window(utc_now(), settings)

    def test_create_rejects_past_warns_for_dnd_and_schedules_future(self):
        """Creation validates time, honors DND confirmation, and queues once."""
        with self.assertRaises(ValueError):
            services.create_reminder("u1", "T", None, "push", "none", utc_now() - timedelta(seconds=1))

        settings = NotificationSettings.get_or_create_default("u1")
        settings.dnd_start = "00:00"
        settings.dnd_end = "23:59"
        settings.save()
        future = utc_now() + timedelta(hours=1)
        warning = services.create_reminder("u1", "T", None, "push", "none", future)
        self.assertEqual(warning, {"status": "dnd_warning"})
        self.assertEqual(Reminder.objects.count(), 0)

        task = FakeTask("created-task")
        result = services.create_reminder(
            "u1", "T", "M", "push", "daily", future,
            confirm_dnd_override=True,
            task=task,
        )
        reminder = result["reminder"]
        self.assertEqual(reminder.status, "scheduled")
        self.assertEqual(reminder.celery_task_id, "created-task")
        self.assertEqual(len(task.calls), 1)

    def test_edit_rejects_unknown_past_and_dnd_without_mutating(self):
        """Invalid edits fail before protected state is changed."""
        reminder = Reminder(
            user_id="u1", title="Old", scheduled_time=utc_now() + timedelta(hours=2),
            status="scheduled", celery_task_id="old-task",
        ).save()
        with self.assertRaises(ValueError):
            services.edit_reminder(reminder.reminder_id, user_id="x")
        with self.assertRaises(ValueError):
            services.edit_reminder(reminder.reminder_id, scheduled_time=utc_now() - timedelta(minutes=1))

        settings = NotificationSettings.get_or_create_default("u1")
        settings.dnd_start = "00:00"
        settings.dnd_end = "23:59"
        settings.save()
        with self.assertRaises(ValueError):
            services.edit_reminder(reminder.reminder_id, title="New")
        reminder.reload()
        self.assertEqual(reminder.title, "Old")

    def test_edit_revokes_old_task_and_schedules_exactly_one_new_task(self):
        """A valid edit replaces the previous task instead of duplicating it."""
        reminder = Reminder(
            user_id="u1", title="Old", scheduled_time=utc_now() + timedelta(hours=2),
            status="scheduled", celery_task_id="old-task",
        ).save()
        revoke = MagicMock()
        task = FakeTask("new-task")
        updated = services.edit_reminder(
            reminder.reminder_id,
            title="New",
            scheduled_time=utc_now() + timedelta(hours=3),
            task=task,
            revoke_task=revoke,
        )
        revoke.assert_called_once_with("old-task")
        self.assertEqual(updated.title, "New")
        self.assertEqual(updated.status, "scheduled")
        self.assertEqual(updated.celery_task_id, "new-task")
        self.assertEqual(len(task.calls), 1)

    def test_delete_revokes_and_soft_deletes(self):
        """Deletion revokes any queued task and clears its identifier."""
        reminder = Reminder(
            user_id="u1", title="T", scheduled_time=utc_now() + timedelta(hours=1),
            status="scheduled", celery_task_id="task-x",
        ).save()
        revoke = MagicMock()
        result = services.delete_reminder(reminder.reminder_id, revoke)
        revoke.assert_called_once_with("task-x")
        self.assertTrue(result.is_deleted)
        self.assertIsNone(result.celery_task_id)

    def test_edit_and_delete_without_old_task_skip_revocation(self):
        """Reminder CRUD also works when no previous Celery task ID exists."""
        reminder = Reminder(
            user_id="u1",
            title="T",
            scheduled_time=utc_now() + timedelta(hours=2),
            status="created",
            celery_task_id=None,
        ).save()
        revoke = MagicMock()
        task = FakeTask("new-task")
        updated = services.edit_reminder(
            reminder.reminder_id,
            title="Updated",
            task=task,
            revoke_task=revoke,
        )
        revoke.assert_not_called()
        updated.status = "created"
        updated.celery_task_id = None
        updated.save()
        deleted = services.delete_reminder(updated.reminder_id, revoke)
        revoke.assert_not_called()
        self.assertTrue(deleted.is_deleted)


class ProcessDueReminderTests(ServicesTestCase):
    """Cover claiming, DND deferral, channels, failures, and repetition."""

    def _due_reminder(self, **overrides):
        """Create a scheduled reminder that is due now."""
        values = {
            "user_id": "u1",
            "title": "Workout",
            "message": "Go train",
            "channel": "push",
            "repeat_type": "none",
            "scheduled_time": utc_now() - timedelta(minutes=1),
            "status": "scheduled",
            "celery_task_id": "task-old",
        }
        values.update(overrides)
        return Reminder(**values).save()

    def test_missing_not_due_or_already_claimed_is_noop(self):
        """Only active scheduled reminders whose time has arrived are claimed."""
        self.assertIsNone(services.process_due_reminder("missing"))
        future = Reminder(
            user_id="u1", title="F", scheduled_time=utc_now() + timedelta(hours=1),
            status="scheduled",
        ).save()
        self.assertIsNone(services.process_due_reminder(future.reminder_id))
        future.reload()
        self.assertEqual(future.status, "scheduled")

    @patch.object(services, "check_dnd_window", return_value=True)
    @patch.object(services, "_next_dnd_end", return_value=datetime(2030, 1, 1, tzinfo=timezone.utc))
    def test_due_reminder_inside_dnd_is_deferred(self, _next_end, _check):
        """A due reminder inside DND is rescheduled to the next allowed time."""
        reminder = self._due_reminder()
        task = FakeTask("deferred")
        result = services.process_due_reminder(reminder.reminder_id, task=task)
        self.assertIsNone(result)
        reminder.reload()
        self.assertEqual(reminder.status, "scheduled")
        self.assertEqual(reminder.celery_task_id, "deferred")
        self.assertEqual(reminder.scheduled_time.replace(tzinfo=timezone.utc), datetime(2030, 1, 1, tzinfo=timezone.utc))

    @patch.object(services, "check_dnd_window", return_value=False)
    def test_disabled_channel_marks_failed_without_notification(self, _check_dnd):
        """A disabled selected channel prevents dispatch and records the reason."""
        settings = NotificationSettings.get_or_create_default("u1")
        settings.push_enabled = False
        settings.save()
        reminder = self._due_reminder()
        self.assertIsNone(services.process_due_reminder(reminder.reminder_id))
        reminder.reload()
        self.assertEqual(reminder.status, "failed")
        self.assertIn("disabled", reminder.last_error)
        self.assertEqual(Notification.objects.count(), 0)

    @patch.object(services, "check_dnd_window", return_value=False)
    def test_unconfigured_non_push_channel_marks_failed_and_reraises(self, _check_dnd):
        """Enabled SMS or email channels fail clearly until providers exist."""
        settings = NotificationSettings.get_or_create_default("u1")
        settings.sms_enabled = True
        settings.save()
        reminder = self._due_reminder(channel="sms")
        with self.assertRaises(NotImplementedError):
            services.process_due_reminder(reminder.reminder_id)
        reminder.reload()
        self.assertEqual(reminder.status, "failed")
        self.assertEqual(Notification.objects.get().delivery_status, "pending")

    @patch.object(services, "check_dnd_window", return_value=False)
    def test_one_off_success_returns_notification_and_stays_sent(self, _check_dnd):
        """A successful one-off reminder is delivered exactly once."""
        reminder = self._due_reminder()
        sender = MagicMock(return_value=services.PushSendResult("m1", 1, 0))
        notification = services.process_due_reminder(
            reminder.reminder_id,
            notification_sender=sender,
        )
        reminder.reload()
        self.assertEqual(reminder.status, "sent")
        self.assertEqual(notification.delivery_status, "sent")
        self.assertEqual(Notification.objects(reminder_id=reminder.reminder_id).count(), 1)
        self.assertIsNone(services.process_due_reminder(reminder.reminder_id, notification_sender=sender))
        self.assertEqual(Notification.objects.count(), 1)

    @patch.object(services, "check_dnd_window", return_value=False)
    def test_sender_failure_marks_both_notification_and_reminder_failed(self, _check_dnd):
        """A provider exception is recorded on both entities and propagated."""
        reminder = self._due_reminder()
        sender = MagicMock(side_effect=RuntimeError("push down"))
        with self.assertRaisesRegex(RuntimeError, "push down"):
            services.process_due_reminder(reminder.reminder_id, notification_sender=sender)
        reminder.reload()
        notification = Notification.objects.get()
        self.assertEqual(reminder.status, "failed")
        self.assertEqual(notification.delivery_status, "failed")

    @patch.object(services, "check_dnd_window", return_value=False)
    def test_repeating_success_schedules_first_future_occurrence(self, _check_dnd):
        """Missed repeated intervals are skipped until the first future run."""
        reminder = self._due_reminder(
            repeat_type="daily",
            scheduled_time=utc_now() - timedelta(days=3, minutes=1),
        )
        task = FakeTask("next-task")
        sender = MagicMock(return_value=services.PushSendResult("m1", 1, 0))
        services.process_due_reminder(reminder.reminder_id, task=task, notification_sender=sender)
        reminder.reload()
        self.assertEqual(reminder.status, "scheduled")
        self.assertGreater(reminder.scheduled_time.replace(tzinfo=timezone.utc), utc_now() - timedelta(seconds=1))
        self.assertEqual(reminder.celery_task_id, "next-task")


class PushNotificationTests(ServicesTestCase):
    """Cover Firebase setup, token handling, partial success, and total failure."""

    def _firebase_modules(self, send_side_effect=None, app_exists=True):
        """Build fake firebase_admin and messaging modules for sys.modules patching."""
        firebase_admin = types.ModuleType("firebase_admin")
        messaging = types.ModuleType("firebase_admin.messaging")
        if app_exists:
            firebase_admin.get_app = MagicMock(return_value=object())
        else:
            firebase_admin.get_app = MagicMock(side_effect=ValueError("no app"))
        firebase_admin.initialize_app = MagicMock(return_value=object())

        class FakeMessage:
            def __init__(self, notification, token):
                self.notification = notification
                self.token = token

        class FakeNotification:
            def __init__(self, title, body):
                self.title = title
                self.body = body

        messaging.Message = FakeMessage
        messaging.Notification = FakeNotification
        messaging.send = MagicMock(side_effect=send_side_effect)
        firebase_admin.messaging = messaging
        return firebase_admin, messaging

    def test_no_tokens_raises(self):
        """Push delivery requires at least one active token."""
        with self.assertRaisesRegex(RuntimeError, "no active device tokens"):
            services.send_push_notification("u1", "T", "M")

    def test_missing_firebase_package_raises_clear_error(self):
        """An unavailable SDK becomes a service-level RuntimeError."""
        DeviceToken(user_id="u1", fcm_token="a").save()
        real_import = __import__

        def guarded_import(name, *args, **kwargs):
            if name == "firebase_admin":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded_import):
            with self.assertRaisesRegex(RuntimeError, "firebase_admin is not installed"):
                services.send_push_notification("u1", "T", "M")

    def test_initializes_app_and_returns_single_message_id(self):
        """Firebase is initialized when needed and a single ID is returned."""
        DeviceToken(user_id="u1", fcm_token="a").save()
        firebase_admin, messaging = self._firebase_modules(["message-1"], app_exists=False)
        with patch.dict(sys.modules, {
            "firebase_admin": firebase_admin,
            "firebase_admin.messaging": messaging,
        }):
            result = services.send_push_notification("u1", "T", "M")
        firebase_admin.initialize_app.assert_called_once()
        self.assertEqual(result.message_id, "message-1")
        self.assertEqual(result.sent_count, 1)
        self.assertEqual(result.failed_count, 0)

    def test_partial_failure_keeps_success_and_soft_deletes_invalid_token(self):
        """One invalid token does not prevent delivery to the remaining tokens."""
        DeviceToken(user_id="u1", fcm_token="bad").save()
        DeviceToken(user_id="u1", fcm_token="good").save()

        class UnregisteredError(Exception):
            pass

        firebase_admin, messaging = self._firebase_modules(
            [UnregisteredError("unregistered token"), "ok-id"]
        )
        with patch.dict(sys.modules, {
            "firebase_admin": firebase_admin,
            "firebase_admin.messaging": messaging,
        }):
            result = services.send_push_notification("u1", "T", "M")
        self.assertEqual(result.sent_count, 1)
        self.assertEqual(result.failed_count, 1)
        self.assertEqual(result.message_id, "ok-id")
        self.assertTrue(DeviceToken.objects.get(fcm_token="bad").is_deleted)
        self.assertFalse(DeviceToken.objects.get(fcm_token="good").is_deleted)

    def test_total_failure_raises_combined_error(self):
        """When every token fails, the provider failure is surfaced."""
        DeviceToken(user_id="u1", fcm_token="a").save()
        firebase_admin, messaging = self._firebase_modules([RuntimeError("boom")])
        with patch.dict(sys.modules, {
            "firebase_admin": firebase_admin,
            "firebase_admin.messaging": messaging,
        }):
            with self.assertRaisesRegex(RuntimeError, "failed for all tokens"):
                services.send_push_notification("u1", "T", "M")


class NotificationAndSuggestionTests(ServicesTestCase):
    """Cover history bounds, settings, and smart-reminder suppression rules."""

    def test_suggestion_requires_push_no_recent_session_and_no_active_reminder(self):
        """A suggestion appears only when all inactivity conditions are met."""
        suggestion = services.get_smart_reminder_suggestion("u1")
        self.assertEqual(suggestion["suggested_repeat_type"], "daily")

        settings = NotificationSettings.objects.get(user_id="u1")
        settings.push_enabled = False
        settings.save()
        self.assertIsNone(services.get_smart_reminder_suggestion("u1"))

        settings.push_enabled = True
        settings.save()
        self.make_session(days_ago=1)
        self.assertIsNone(services.get_smart_reminder_suggestion("u1"))
        WorkoutSession.drop_collection()

        Reminder(
            user_id="u1", title="Existing", scheduled_time=utc_now() + timedelta(hours=1),
            status="created",
        ).save()
        self.assertIsNone(services.get_smart_reminder_suggestion("u1"))

    def test_history_filters_sorts_limits_and_validates_limit(self):
        """History returns newest active notifications within the requested bound."""
        for index in range(3):
            Notification(
                user_id="u1", type="system", content=str(index),
                created_at=utc_now() + timedelta(seconds=index),
            ).save()
        Notification(user_id="u1", type="system", content="deleted", is_deleted=True).save()
        Notification(user_id="u2", type="system", content="other").save()
        history = services.get_notification_history("u1", limit=2)
        self.assertEqual([item.content for item in history], ["2", "1"])
        for invalid in (0, 501):
            with self.assertRaises(ValueError):
                services.get_notification_history("u1", invalid)

    def test_update_settings_rejects_unknown_and_validates_values(self):
        """Only supported settings fields are writable and model validation runs."""
        updated = services.update_notification_settings(
            "u1", push_enabled=False, dnd_start="23:00", timezone_name="Asia/Baku"
        )
        self.assertFalse(updated.push_enabled)
        self.assertEqual(updated.timezone_name, "Asia/Baku")
        with self.assertRaises(ValueError):
            services.update_notification_settings("u1", admin=True)
        with self.assertRaises(mongoengine.ValidationError):
            services.update_notification_settings("u1", dnd_start="99:00")


class EventSubscriptionServiceTests(ServicesTestCase):
    """Cover idempotent subscriptions, reactivation, fan-out, and consumption."""

    def test_subscribe_returns_existing_and_reactivates_deleted(self):
        """Repeated subscription calls do not create duplicate active documents."""
        first = services.subscribe_to_event("u1", "product_available", "p1")
        second = services.subscribe_to_event("u1", "product_available", "p1")
        self.assertEqual(first.subscription_id, second.subscription_id)
        first.is_deleted = True
        first.save()
        reactivated = services.subscribe_to_event("u1", "product_available", "p1")
        self.assertEqual(reactivated.subscription_id, first.subscription_id)
        self.assertFalse(reactivated.is_deleted)

    def test_subscribe_recovers_from_unique_race(self):
        """A unique-index race returns the winner instead of leaking DB errors."""
        existing = EventSubscription(
            user_id="u1", event_type="product_available", reference_id="p1"
        ).save()
        query = MagicMock()
        query.first.return_value = None
        query.get.return_value = existing
        objects_mock = MagicMock(return_value=query)
        objects_mock.get.return_value = existing
        with patch.object(EventSubscription, "objects", objects_mock):
            result = services.subscribe_to_event(
                "u1", "product_available", "p1"
            )
        self.assertEqual(result.subscription_id, existing.subscription_id)
        objects_mock.get.assert_called_once()

    def test_notify_fans_out_counts_failures_and_consumes_successes(self):
        """Successful subscriptions are consumed while failed ones remain active."""
        s1 = services.subscribe_to_event("u1", "product_available", "p1")
        s2 = services.subscribe_to_event("u2", "product_available", "p1")

        def sender(*, user_id, title, message):
            if user_id == "u2":
                raise RuntimeError("down")
            return services.PushSendResult("m1", 1, 0)

        result = services.notify_event_subscribers(
            "product_available", "p1", "Back", sender, consume_subscriptions=True
        )
        self.assertEqual(result, {"sent": 1, "failed": 1})
        self.assertTrue(EventSubscription.objects.get(subscription_id=s1.subscription_id).is_deleted)
        self.assertFalse(EventSubscription.objects.get(subscription_id=s2.subscription_id).is_deleted)
        self.assertEqual(Notification.objects.count(), 2)

    def test_notify_can_keep_successful_subscriptions_active(self):
        """Persistent subscriptions remain active when consumption is disabled."""
        subscription = services.subscribe_to_event("u1", "challenge_start", "c1")
        sender = MagicMock(return_value=services.PushSendResult("m1", 1, 0))
        result = services.notify_event_subscribers(
            "challenge_start", "c1", "Started", sender, consume_subscriptions=False
        )
        self.assertEqual(result, {"sent": 1, "failed": 0})
        self.assertFalse(EventSubscription.objects.get(subscription_id=subscription.subscription_id).is_deleted)


class InternalHelperTests(ServicesTestCase):
    """Cover date recurrence, channel checks, token errors, Celery, and Redis helpers."""

    def test_next_occurrence_none_daily_weekly_monthly_and_invalid(self):
        """Each repeat type returns the first occurrence strictly after now."""
        now = datetime(2026, 3, 31, 12, tzinfo=timezone.utc)
        self.assertIsNone(services._next_occurrence(now, "none", now))
        self.assertEqual(
            services._next_occurrence(now - timedelta(days=2), "daily", now),
            datetime(2026, 4, 1, 12, tzinfo=timezone.utc),
        )
        self.assertGreater(services._next_occurrence(now - timedelta(weeks=3), "weekly", now), now)
        self.assertEqual(
            services._next_occurrence(datetime(2026, 1, 31, 12, tzinfo=timezone.utc), "monthly", now),
            datetime(2026, 4, 28, 12, tzinfo=timezone.utc),
        )
        with self.assertRaises(ValueError):
            services._next_occurrence(now - timedelta(seconds=1), "hourly", now)

    def test_datetime_zone_dnd_end_channel_and_invalid_token_helpers(self):
        """Small helpers normalize time and classify channel/provider behavior."""
        naive = datetime(2026, 1, 1, 12)
        self.assertEqual(services._as_utc(naive).tzinfo, timezone.utc)
        aware = datetime(2026, 1, 1, 15, tzinfo=timezone(timedelta(hours=3)))
        self.assertEqual(services._as_utc(aware).hour, 12)
        self.assertEqual(str(services._get_zone("UTC")), "UTC")
        with self.assertRaises(ValueError):
            services._get_zone("Not/AZone")

        settings = NotificationSettings(
            user_id="u1", timezone_name="UTC", dnd_start="22:00", dnd_end="08:00"
        )
        end = services._next_dnd_end(datetime(2026, 1, 1, 23, tzinfo=timezone.utc), settings)
        self.assertEqual(end, datetime(2026, 1, 2, 8, tzinfo=timezone.utc))
        same_day_end = services._next_dnd_end(
            datetime(2026, 1, 1, 7, tzinfo=timezone.utc), settings
        )
        self.assertEqual(same_day_end, datetime(2026, 1, 1, 8, tzinfo=timezone.utc))
        settings.push_enabled = True
        settings.sms_enabled = False
        self.assertTrue(services._channel_enabled("push", settings))
        self.assertFalse(services._channel_enabled("sms", settings))
        with self.assertRaises(KeyError):
            services._channel_enabled("fax", settings)

        class UnregisteredThing(Exception):
            pass

        self.assertTrue(services._is_invalid_fcm_token_error(UnregisteredThing("x")))
        self.assertTrue(services._is_invalid_fcm_token_error(RuntimeError("invalid registration token")))
        self.assertFalse(services._is_invalid_fcm_token_error(RuntimeError("timeout")))
        self.assertFalse(services._is_trainer_authorized("t", "a"))

    def test_get_process_task_supports_direct_layout(self):
        """Task lookup can import the direct-layout tasks module."""
        fake_tasks = types.ModuleType("tasks")
        fake_task = object()
        fake_tasks.process_due_reminder = fake_task
        with patch.dict(sys.modules, {"tasks": fake_tasks}):
            with patch("builtins.__import__", wraps=__import__):
                result = services._get_process_due_task()
        self.assertIs(result, fake_task)

    def test_revoke_celery_task_and_missing_celery(self):
        """Task revocation delegates to Celery and reports a missing dependency."""
        current_app = MagicMock()
        celery_module = types.ModuleType("celery")
        celery_module.current_app = current_app
        with patch.dict(sys.modules, {"celery": celery_module}):
            services._revoke_celery_task("task-1")
        current_app.control.revoke.assert_called_once_with("task-1", terminate=False)

        real_import = __import__

        def guarded_import(name, *args, **kwargs):
            if name == "celery":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=guarded_import):
            with self.assertRaisesRegex(RuntimeError, "Celery is not installed"):
                services._revoke_celery_task("task-2")

    def test_redis_client_without_url_and_successful_lazy_connection(self):
        """Redis remains optional and is lazily initialized from REDIS_URL."""
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(services._get_redis_client())

        fake = FakeRedis()
        redis_module = types.ModuleType("redis")
        redis_module.from_url = MagicMock(return_value=fake)
        with patch.dict(os.environ, {"REDIS_URL": "redis://example"}, clear=True), patch.dict(
            sys.modules, {"redis": redis_module}
        ):
            client = services._get_redis_client()
            self.assertIs(client, fake)
            self.assertIs(services._get_redis_client(), fake)
        redis_module.from_url.assert_called_once()

    def test_redis_connection_failure_and_operation_failures_reset_client(self):
        """Redis failures soft-fail and reset the cached client for reconnection."""
        redis_module = types.ModuleType("redis")
        redis_module.from_url = MagicMock(side_effect=RuntimeError("offline"))
        with patch.dict(os.environ, {"REDIS_URL": "redis://bad"}, clear=True), patch.dict(
            sys.modules, {"redis": redis_module}
        ):
            self.assertIsNone(services._get_redis_client())

        for operation in ("get", "set", "delete"):
            fake = FakeRedis()
            setattr(fake, f"fail_{operation}", True)
            services._redis_client = fake
            if operation == "get":
                self.assertIsNone(services._redis_get("k"))
            elif operation == "set":
                services._redis_set("k", "v", 1)
            else:
                services._redis_delete("k")
            self.assertIsNone(services._redis_client)

    def test_redis_operations_are_noops_without_a_client(self):
        """Cache operations return safely when Redis is not configured."""
        with patch.object(services, "_get_redis_client", return_value=None):
            self.assertIsNone(services._redis_get("k"))
            self.assertIsNone(services._redis_set("k", "v", 30))
            self.assertIsNone(services._redis_delete("k"))

    def test_redis_success_paths_and_chart_invalidation(self):
        """Redis helpers read, write, delete, and invalidate every chart period."""
        fake = FakeRedis()
        fake.data["k"] = "v"
        services._redis_client = fake
        self.assertEqual(services._redis_get("k"), "v")
        services._redis_set("a", "b", 30)
        self.assertEqual(fake.data["a"], "b")
        services._redis_delete("a")
        self.assertNotIn("a", fake.data)
        services._invalidate_chart_cache("u1")
        self.assertEqual(
            set(fake.deleted[-3:]),
            {"chart:u1:week", "chart:u1:month", "chart:u1:year"},
        )


if __name__ == "__main__":
    unittest.main()
