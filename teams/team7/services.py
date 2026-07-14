"""
MODEL LAYER (continued)
Business logic that spans multiple collections or talks to external
systems (Celery, Firebase). Controllers call these functions; these
functions call models.py, never the other way around.
"""


# ---------------- Progress Tracking services ----------------

def register_physical_data(user_id: str, weight: float, height: float,
                            body_fat_percent: float = None, muscle_mass: float = None):
    """
    UC01 main flow: validate input, create a PhysicalRecord, compute BMI,
    save it, and return the saved record (or raise a validation error).
    """
    pass


def get_progress_chart_data(user_id: str, period: str) -> dict:
    """
    UC03: build the time series needed to render progress charts for the
    given period ('week' | 'month' | 'year'). Should use cached data
    (Redis) when available, per the NFR on chart response time.
    """
    pass


def get_mentor_report(trainer_id: str, athlete_id: str) -> dict:
    """
    UC09: verify trainer_id has access to athlete_id, then build an
    aggregated progress report for the trainer's dashboard.
    """
    pass


def detect_and_register_new_record(user_id: str, exercise_name: str,
                                    weight_lifted: float, session_id: str):
    """
    UC11 main flow: after a WorkoutSession is saved, check PersonalBest.is_new_record(),
    update the PersonalBest if broken, and trigger a congratulations Notification.
    Returns the updated PersonalBest, or None if no record was broken.
    """
    pass


# ---------------- Reminder & Notification services ----------------

def check_dnd_window(scheduled_time, settings: "NotificationSettings") -> bool:
    """UC05 subflow: True if scheduled_time falls in the user's DND window."""
    pass


def create_reminder(user_id: str, title: str, message: str, channel: str,
                     repeat_type: str, scheduled_time):
    """
    UC05 main flow: validate DND, create+save a Reminder, and call
    reminder.schedule() to enqueue the Celery task.
    """
    pass


def process_due_reminder(reminder_id: str):
    """
    UC12: called by the Celery task when a reminder's scheduled_time
    arrives. Builds the Notification and calls send_push_notification().
    """
    pass


def send_push_notification(user_id: str, title: str, message: str):
    """
    Send a push notification via Firebase Cloud Messaging using the
    user's DeviceToken(s). Retries / queues on failure per UC11 exception flow.
    """
    pass


def get_smart_reminder_suggestion(user_id: str) -> dict | None:
    """
    UC13: analyze the user's recent WorkoutSession history and suggest
    a new reminder (e.g. missing weekly cardio). Returns None if no
    suggestion applies.
    """
    pass