# Team team7 — backend image.  *** REPLACE WITH YOUR OWN STACK ***
# Build your service so it listens on port 8000 and serves both your UI (/)
# and your API (/api/...). It reads the trusted X-User-* headers the gateway
# injects, and connects to its own database via DATABASE_URL (from .env).
#
# Minimal Django starting point (uncomment and flesh out):
# FROM python:3.12-slim
# WORKDIR /app
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY . .
# EXPOSE 8000
# CMD ["gunicorn", "yourproject.wsgi:application", "-b", "0.0.0.0:8000"]
FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# این پوشه (team7) را در مسیری کپی می‌کنیم که apps.py انتظارش را دارد:
# teams/team7/ ...
COPY . /app/teams/team7
RUN mkdir -p /app/teams && touch /app/teams/__init__.py

# فایل‌های سطح پروژه به ریشه /app منتقل می‌شوند
COPY manage.py /app/manage.py
COPY config /app/config

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "-b", "0.0.0.0:8000"]