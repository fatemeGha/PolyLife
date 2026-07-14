from django.http import JsonResponse


def whoami(request):
    """
    Example endpoint.

    The gateway already authenticated the user against the core and injected
    these headers — your team never decodes JWTs. Just read them.
    """
    return JsonResponse(
        {
            "team": "team7",
            "user_id": request.headers.get("X-User-Id", ""),
            "username": request.headers.get("X-User-Username", ""),
        }
    )

# Add your team's real views below.
"""
VIEW LAYER
Owns: dynamic page generation and forms management (the 'Boundary'
layer from the phase-2 BCE diagrams). A view function takes data
prepared by a controller and returns an HttpResponse built from a
Django template. No business logic, no direct database queries here.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


# ---------------- Progress Tracking views ----------------

def render_physical_data_form(request: HttpRequest) -> HttpResponse:
    """UC01: render the form for entering weight/height/body-fat/etc."""
    pass


def render_progress_charts(request: HttpRequest, chart_data: dict) -> HttpResponse:
    """UC03: render the progress charts page using chart_data from the controller."""
    pass


def render_goal_form(request: HttpRequest) -> HttpResponse:
    """UC04: render the form for setting target weight/body fat."""
    pass


def render_mentor_dashboard(request: HttpRequest, report_data: dict) -> HttpResponse:
    """UC09: render the trainer's dashboard with an athlete's progress report."""
    pass


# ---------------- Reminder & Notification views ----------------

def render_reminder_form(request: HttpRequest) -> HttpResponse:
    """UC05: render the 'create/edit reminder' form."""
    pass


def render_reminder_list(request: HttpRequest, reminders: list) -> HttpResponse:
    """UC05: render the user's list of reminders."""
    pass


def render_notification_settings_form(request: HttpRequest) -> HttpResponse:
    """UC06: render the notification settings form (channels, DND hours)."""
    pass


def render_notification_history(request: HttpRequest, notifications: list) -> HttpResponse:
    """UC07: render the notification history list."""
    pass


# ---------------- Shared / generic views ----------------

def show_validation_error(request: HttpRequest, errors: dict) -> HttpResponse:
    """Render a generic validation-error response (used across multiple UCs)."""
    pass


def show_success_message(request: HttpRequest, message: str, data: dict = None) -> HttpResponse:
    """Render a generic success confirmation response."""
    pass