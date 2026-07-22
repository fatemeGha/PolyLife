"""
URL configuration for Team2 microservice.

All routes are prefixed with /api/team2/ by the project root urls.py
or by the Nginx gateway.

Route summary:
    GET  /api/team2/health/                      — Public health check
    GET  /api/team2/auth-test/                   — Auth header test

    GET  /api/team2/progress/records/            — List physical records
    POST /api/team2/progress/records/            — Create physical record
    PUT  /api/team2/progress/records/<id>/       — Update physical record
    DELETE /api/team2/progress/records/<id>/     — Soft-delete physical record

    POST /api/team2/progress/goals/              — Create or update goal
    GET  /api/team2/progress/summary/            — Progress summary

    GET  /api/team2/reminders/                   — List active reminders
    POST /api/team2/reminders/                   — Create reminder (checks quiet hours)
    PUT  /api/team2/reminders/<id>/              — Update reminder
    DELETE /api/team2/reminders/<id>/            — Soft-delete reminder
    PATCH /api/team2/reminders/<id>/complete/    — Mark reminder as completed

    GET  /api/team2/notification-settings/       — Get quiet hours settings
    PUT  /api/team2/notification-settings/       — Update quiet hours settings

    GET  /api/team2/notifications/history/       — View notification history logs

    GET  /api/team2/progress/charts/             — Get chart data (New in Phase 9)
    GET  /api/team2/trainer/users/<id>/progress/ — Get student progress (New in Phase 9)
"""

from django.urls import path
from . import views

from django.views.generic import TemplateView

app_name = "team2"

urlpatterns = [
    # ------------------------------------------------------------------
    # Utility / Test Endpoints
    # ------------------------------------------------------------------
    path("health/", views.health_check, name="health-check"),
    path("auth-test/", views.auth_test, name="auth-test"),

    # ------------------------------------------------------------------
    # Progress Tracking — Physical Records
    # ------------------------------------------------------------------
    path(
        "progress/records/",
        views.physical_records_list_create,
        name="physical-records",
    ),
    path(
        "progress/records/<str:record_id>/",
        views.physical_record_detail,
        name="physical-record-detail",
    ),

    # ------------------------------------------------------------------
    # Progress Tracking — Goals & Summary
    # ------------------------------------------------------------------
    path(
        "progress/goals/",
        views.user_goal,
        name="user-goal",
    ),
    path(
        "progress/summary/",
        views.progress_summary,
        name="progress-summary",
    ),

    # ------------------------------------------------------------------
    # Reminders CRUD
    # ------------------------------------------------------------------
    path(
        "reminders/",
        views.reminder_list_create,
        name="reminder-list-create",
    ),
    path(
        "reminders/<str:reminder_id>/",
        views.reminder_detail,
        name="reminder-detail",
    ),
    path(
        "reminders/<str:reminder_id>/complete/",
        views.reminder_complete,
        name="reminder-complete",
    ),

    # ------------------------------------------------------------------
    # Notification Settings
    # ------------------------------------------------------------------
    path(
        "notification-settings/",
        views.notification_settings,
        name="notification-settings",
    ),

    # ------------------------------------------------------------------
    # Notification History Logs
    # ------------------------------------------------------------------
    path(
        "notifications/history/",
        views.notification_history,
        name="notification-history",
    ),

    # ------------------------------------------------------------------
    # Chart Data (New in Phase 9)
    # ------------------------------------------------------------------
    path(
        "progress/charts/",
        views.chart_data,
        name="chart-data",
    ),

    # ------------------------------------------------------------------
    # Trainer — Student Progress (New in Phase 9)
    # ------------------------------------------------------------------
    path(
        "trainer/users/<int:student_id>/progress/",
        views.trainer_student_progress,
        name="trainer-student-progress",
    ),

    # ------------------------------------------------------------------
    # Front
    # ------------------------------------------------------------------
    path(
        "dashboard/",
        TemplateView.as_view(template_name="./templates/team2/dashboard.html"),
        name="dashboard",
    ),
]
