# Team team4 — backend image.  *** REPLACE WITH YOUR OWN STACK ***
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
#FROM python:3.12-slim
#CMD ["sh", "-c", "echo 'Team team4: replace this Dockerfile with your service'; sleep infinity"]
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .


EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py collectstatic --noinput && gunicorn config.wsgi:application -b 0.0.0.0:8000"]
