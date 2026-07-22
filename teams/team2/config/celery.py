"""
Celery application instance for this project.

This is the single Celery "app" that both the web process (when it
calls .apply_async / .delay) and the separate `celery worker` process
(when it actually executes tasks) share. It's wired to Django settings
so CELERY_* values in config/settings.py configure it automatically.
"""

import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

# Read every setting whose name starts with CELERY_ from Django's
# settings.py (e.g. CELERY_BROKER_URL -> broker_url).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover a tasks.py inside every app listed in INSTALLED_APPS -
# this is what picks up teams/team2/tasks.py without needing to import
# it manually anywhere.
app.autodiscover_tasks()