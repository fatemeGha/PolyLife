"""
Django settings for the PolyLife core project.

Configuration is driven by environment variables (via django-environ) so the
same code runs locally, inside Docker, and in CI without edits. A local `.env`
file is read if present; see `.env.example` for the available keys.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
)
# Read a local .env file if it exists (ignored in production / CI).
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key secret in production!
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="dev-only-insecure-secret-key-change-me-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Team microservices mounted by the core. Empty until teams are implemented;
# the /api/microservices endpoint then falls back to decoy placeholders.
TEAM_APPS = env.list("TEAM_APPS", default=[])
TEAM_APPS.append("teams.team2.apps.TeamConfig")


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Local apps
    "core",

    # Team microservices (empty until teams are implemented)
    *TEAM_APPS,
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.JWTAuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "polylife.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "polylife.wsgi.application"
ASGI_APPLICATION = "polylife.asgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
#
# The core (and Django's built-in apps) live in "default". Each team gets its
# own database, isolated from the others. A team's DB connection comes from
# `<TEAM>_DATABASE_URL` (e.g. TEAM1_DATABASE_URL), carrying that team's unique
# credentials in production; locally it falls back to a per-team SQLite file.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    ),
}

for _team in TEAM_APPS:
    DATABASES[_team] = env.db(
        f"{_team.upper()}_DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / f'{_team}.sqlite3'}",
    )

# Route each team app's models to that team's own database.
DATABASE_ROUTERS = ["core.db_router.TeamPerAppRouter"]


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Built frontend (Vite SPA). When `frontend/dist` exists (e.g. built inside
# Docker), WhiteNoise serves its assets from the site root and the home view
# returns its index.html. Otherwise the home view shows a fallback page.
FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_BUILT = (FRONTEND_DIST / "index.html").exists()
if FRONTEND_BUILT:
    WHITENOISE_ROOT = FRONTEND_DIST
    WHITENOISE_INDEX_FILE = True

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model (email-based), shared by the core and all team apps.
AUTH_USER_MODEL = "core.User"

# JWT authentication
JWT_SECRET = env("JWT_SECRET", default=SECRET_KEY)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TTL_SECONDS = env.int("JWT_ACCESS_TTL_SECONDS", default=15 * 60)  # 15 minutes
JWT_REFRESH_TTL_SECONDS = env.int("JWT_REFRESH_TTL_SECONDS", default=7 * 24 * 60 * 60)  # 7 days

# Auth cookies. In production set JWT_COOKIE_SECURE=True (HTTPS only).
JWT_COOKIE_SECURE = env.bool("JWT_COOKIE_SECURE", default=False)
JWT_COOKIE_SAMESITE = env("JWT_COOKIE_SAMESITE", default="Lax")

# ---------------------------------------------------------------------------
# Celery Configuration
# ---------------------------------------------------------------------------

import os

# Broker: Redis running as a Docker service named "team2_redis"
CELERY_BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    "redis://team2_redis:6379/0"
)

# Result backend: same Redis instance, different DB index
CELERY_RESULT_BACKEND = os.environ.get(
    "CELERY_RESULT_BACKEND",
    "redis://team2_redis:6379/1"
)

# Timezone must match the timezone used when comparing reminder times
CELERY_TIMEZONE = "Asia/Tehran"
CELERY_ENABLE_UTC = False

# Serialization
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# Task execution limits
CELERY_TASK_SOFT_TIME_LIMIT = 30   # seconds — task gets SoftTimeLimitExceeded
CELERY_TASK_TIME_LIMIT = 60        # seconds — task is killed after this

# Retry configuration defaults (can be overridden per task)
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # seconds between retries

# Store task results in DB (requires django-celery-results)
CELERY_RESULT_EXTENDED = True

# Celery Beat scheduler — stores schedule in Django DB
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

