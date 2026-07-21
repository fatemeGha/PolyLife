"""
CONTROLLER LAYER
Owns: HTTP request handling, input validation, orchestration.
A controller function:
  1) reads/validates request data
  2) calls services.py / models.py (Model layer)
  3) calls a views.py function to build the response (rendered page or JSON)
  4) returns an HttpResponse
Never put business logic or database queries directly here.
"""

from django.http import HttpRequest, HttpResponse


# ---------------- Progress Tracking controllers ----------------

def register_physical_data(request: HttpRequest) -> HttpResponse:
    """UC01: handle the 'submit physical data' form POST."""
    pass


def edit_physical_data(request: HttpRequest, record_id: str) -> HttpResponse:
    """UC02: handle editing an existing PhysicalRecord."""
    pass


def delete_physical_data(request: HttpRequest, record_id: str) -> HttpResponse:
    """UC02: handle soft-deleting a PhysicalRecord (is_deleted = True)."""
    pass


def get_progress_charts(request: HttpRequest) -> HttpResponse:
    """UC03: handle the 'view progress charts' request."""
    pass


def set_goal(request: HttpRequest) -> HttpResponse:
    """UC04: handle creating/updating the user's Goal."""
    pass


def get_mentor_report(request: HttpRequest, athlete_id: str) -> HttpResponse:
    """UC09: handle a trainer viewing an athlete's progress report."""
    pass


# ---------------- Reminder & Notification controllers ----------------

def create_reminder(request: HttpRequest) -> HttpResponse:
    """UC05: handle the 'create reminder' form POST, including DND confirmation."""
    pass


def edit_reminder(request: HttpRequest, reminder_id: str) -> HttpResponse:
    """UC05: handle editing an existing Reminder."""
    pass


def delete_reminder(request: HttpRequest, reminder_id: str) -> HttpResponse:
    """UC05: handle deleting a Reminder."""
    pass


def update_notification_settings(request: HttpRequest) -> HttpResponse:
    """UC06: handle enabling/disabling notification channels and DND hours."""
    pass


def get_notification_history(request: HttpRequest) -> HttpResponse:
    """UC07: handle listing the user's past notifications."""
    pass


def subscribe_to_event(request: HttpRequest) -> HttpResponse:
    """UC08: handle a user requesting to be notified about a future event."""
    pass


def send_mentor_message(request: HttpRequest) -> HttpResponse:
    """UC10: handle a trainer sending an encouragement message to an athlete."""
    pass