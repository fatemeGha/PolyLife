"""
URL configuration for Team2 microservice.

All routes are prefixed with /api/team2/ via the project's root urls.py
or via Nginx gateway routing.
"""

from django.urls import path
from . import views

app_name = "team2"

urlpatterns = [
    # ------------------------------------------------------------------
    # Utility endpoints
    # ------------------------------------------------------------------

    # Health check — no auth needed
    # GET /api/team2/health/
    path("health/", views.health_check, name="health-check"),

    # Auth test — verifies Gateway header injection
    # GET /api/team2/auth-test/
    path("auth-test/", views.auth_test, name="auth-test"),
]
