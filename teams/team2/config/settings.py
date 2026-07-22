import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-secret-change-me")
DEBUG = os.environ.get("DEBUG", "False").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1"
).split(",")

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "teams.team2.apps.TeamConfig",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# Django ORM is intentionally disabled.
# All application data is stored through MongoEngine in MongoDB.
# This dummy database exists only because Django requires DATABASES.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Celery configuration ---
USE_TZ = True
TIME_ZONE = "UTC"

CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    "redis://redis:6379/1",
)

CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    "redis://redis:6379/2",
)

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = "UTC"

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
