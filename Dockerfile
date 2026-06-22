# syntax=docker/dockerfile:1

# ---- Stage 1: build the React/Vite frontend ----
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build          # outputs /frontend/dist

# ---- Stage 2: Django runtime ----
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
# Pull the built SPA from the frontend stage so WhiteNoise can serve it.
COPY --from=frontend /frontend/dist ./frontend/dist

RUN python manage.py collectstatic --noinput

EXPOSE 8000

# Apply migrations, then serve with gunicorn.
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn polylife.wsgi:application -b 0.0.0.0:8000"]
