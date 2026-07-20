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
"""

from django.urls import path
from . import views

app_name = "team2"

urlpatterns = [
    # ------------------------------------------------------------------
    # Utility
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
        "progress/records/<int:record_id>/",
        views.physical_record_detail,
        name="physical-record-detail",
    ),

    # ------------------------------------------------------------------
    # Progress Tracking — Goals
    # ------------------------------------------------------------------
    path(
        "progress/goals/",
        views.user_goal,
        name="user-goal",
    ),

    # ------------------------------------------------------------------
    # Progress Tracking — Summary
    # ------------------------------------------------------------------
    path(
        "progress/summary/",
        views.progress_summary,
        name="progress-summary",
    ),
]
