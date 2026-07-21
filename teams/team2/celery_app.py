"""
Celery application instance for Team2 microservice.

This module creates and configures the Celery app used for:
    - Asynchronous task execution (reminder notifications)
    - Scheduled periodic tasks via Celery Beat

Configuration:
    - Broker  : Redis (via CELERY_BROKER_URL env variable)
    - Backend : Redis (via CELERY_RESULT_BACKEND env variable)
    - Timezone: Asia/Tehran (matches user-facing times)

Usage:
    From anywhere in the project:
        from teams.team2.celery_app import celery_app
        celery_app.send_task(...)

    Or via the shared_task decorator in tasks.py (preferred).
"""

import os
from celery import Celery

# ---------------------------------------------------------------------------
# Django settings module — must be set before Celery app is created
# ---------------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# ---------------------------------------------------------------------------
# Create the Celery application
# ---------------------------------------------------------------------------
celery_app = Celery("team2")

# ---------------------------------------------------------------------------
# Load configuration from Django settings (namespace = "CELERY")
# All Celery settings in settings.py must be prefixed with CELERY_
# Example: CELERY_BROKER_URL, CELERY_RESULT_BACKEND, etc.
# ---------------------------------------------------------------------------
celery_app.config_from_object("django.conf:settings", namespace="CELERY")

# ---------------------------------------------------------------------------
# Auto-discover tasks in all installed Django apps
# Celery will look for a tasks.py file in each app
# ---------------------------------------------------------------------------
celery_app.autodiscover_tasks()


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    A simple debug task to verify Celery is working correctly.
    Run with: celery -A teams.team2.celery_app call team2.debug_task
    """
    print(f"[team2] Debug task executed. Request: {self.request!r}")

