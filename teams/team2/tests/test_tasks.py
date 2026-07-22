"""
Unit tests for tasks.py.

The Celery worker and broker are not started during these tests. The task is
executed synchronously through its ``run`` method, while the service function
and Celery retry mechanism are mocked. This keeps the tests fast and verifies
that tasks.py remains a thin adapter around services.py.
"""

import unittest
from unittest.mock import patch

from celery.exceptions import Retry

# Support both common execution styles:
#   1) From the repository root:
#      python -m unittest teams.team2.tests.test_tasks -v
#   2) From inside teams/team2:
#      python -m unittest tests.test_tasks -v
if __package__ in (None, "", "tests"):
    import tasks
else:
    from .. import tasks


class ProcessDueReminderTaskTests(unittest.TestCase):
    """Tests for the Celery process_due_reminder task wrapper."""

    def test_task_metadata_is_configured_correctly(self):
        """
        Verify the public Celery task name and retry configuration.

        These values are part of the integration contract used by
        Reminder.schedule(), Celery workers, and monitoring tools.
        """
        task = tasks.process_due_reminder

        self.assertEqual(task.name, "team2.process_due_reminder")
        self.assertEqual(task.max_retries, 3)

    @patch.object(tasks.services, "process_due_reminder")
    def test_success_delegates_to_service_once(self, mock_service):
        """
        Delegate a successful task execution to services.py exactly once.

        tasks.py must not duplicate reminder-processing business logic.
        """
        result = tasks.process_due_reminder.run("reminder-123")

        mock_service.assert_called_once_with("reminder-123")
        self.assertIsNone(result)

    @patch.object(tasks.services, "process_due_reminder")
    def test_service_result_is_not_exposed_as_task_result(self, mock_service):
        """
        Keep the task interface independent from the service return value.

        The task performs work for side effects and intentionally returns None.
        """
        mock_service.return_value = {"status": "processed"}

        result = tasks.process_due_reminder.run("reminder-123")

        self.assertIsNone(result)

    @patch.object(tasks.services, "process_due_reminder")
    def test_failure_requests_retry_with_original_exception(self, mock_service):
        """
        Retry transient failures with the original exception and a five-second delay.
        """
        original_error = RuntimeError("temporary database failure")
        mock_service.side_effect = original_error

        with patch.object(
            tasks.process_due_reminder,
            "retry",
            side_effect=Retry(),
        ) as mock_retry:
            with self.assertRaises(Retry):
                tasks.process_due_reminder.run("reminder-123")

        mock_service.assert_called_once_with("reminder-123")
        mock_retry.assert_called_once_with(
            exc=original_error,
            countdown=5,
        )

    @patch.object(tasks.services, "process_due_reminder")
    def test_retry_is_requested_for_any_exception_type(self, mock_service):
        """
        Confirm that any service-layer exception follows the retry path.
        """
        original_error = ValueError("unexpected transient input failure")
        mock_service.side_effect = original_error

        with patch.object(
            tasks.process_due_reminder,
            "retry",
            side_effect=Retry(),
        ) as mock_retry:
            with self.assertRaises(Retry):
                tasks.process_due_reminder.run("reminder-456")

        mock_retry.assert_called_once_with(
            exc=original_error,
            countdown=5,
        )


if __name__ == "__main__":
    unittest.main()
