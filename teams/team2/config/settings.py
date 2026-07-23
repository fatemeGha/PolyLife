"""
Standalone Django settings for the Team2 microservice.

This module intentionally does not import the PolyLife core settings, core
middleware, core user model, or another team's settings.
"""

from pathlib import Path

import environ


TEAM2_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = TEAM2_DIR.parents[1]

env = environ.Env(DEBUG=(bool, True))

# Prefer Team2's local environment file. In the integrated repository, values
# already exported by Docker/CI still take precedence.
environ.Env.read_env(TEAM2_DIR / ".env")

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="dev-only-team2-secret-change-me",
)
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1"],
)

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "teams.team2.apps.TeamConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "teams.team2.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEAM2_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "teams.team2.config.wsgi.application"

# MongoEngine owns Team2's domain data. Django still requires a default
# DATABASES entry for its framework internals and test client.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env(
            "TEAM2_SQLITE_PATH",
            default=str(TEAM2_DIR / "team2.sqlite3"),
        ),
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = TEAM2_DIR / "staticfiles"
STATICFILES_DIRS = [TEAM2_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Team2 database
MONGO_DATABASE_URL = env(
    "MONGO_DATABASE_URL",
    default="mongodb://localhost:27017/team2_db",
)

# Team2 Celery/Redis
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default="redis://localhost:6379/1",
)
CELERY_RESULT_BACKEND = env(
    "CELERY_RESULT_BACKEND",
    default="redis://localhost:6379/2",
)
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SOFT_TIME_LIMIT = 30
CELERY_TASK_TIME_LIMIT = 60
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60
CELERY_RESULT_EXTENDED = True

# Celery includes its own persistent Beat scheduler, so Team2 does not need
# django-celery-beat or the PolyLife core database.
CELERY_BEAT_SCHEDULER = "celery.beat:PersistentScheduler"
CELERY_BEAT_SCHEDULE_FILENAME = env(
    "CELERY_BEAT_SCHEDULE_FILENAME",
    default=str(TEAM2_DIR / "celerybeat-schedule"),
)
