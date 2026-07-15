import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.staticfiles",
    "teams.team7",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "teams.team7.middleware.GatewayUserMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# نکته مهم: چون از mongoengine برای اتصال به MongoDB استفاده می‌کنیم
# (نه Django ORM)، این تنظیم فقط برای اینکه جنگو خطا ندهد لازم است
# و هیچ‌وقت واقعاً استفاده نمی‌شود.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Celery configuration ---
# Uses the same Redis instance as the caching layer in services.py,
# just a different logical DB index (1) to keep task queues and
# cached chart data separate.
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/1")
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
