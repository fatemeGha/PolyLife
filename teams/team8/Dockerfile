# syntax=docker/dockerfile:1

FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY teams/team8/frontend/package.json teams/team8/frontend/package-lock.json ./
RUN npm ci
COPY teams/team8/frontend/ ./
RUN npm run build

FROM python:3.12-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app
WORKDIR /app/teams/team8

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/*

COPY teams/team8/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/
COPY --from=frontend /frontend/dist ./frontend/dist
RUN chmod +x /app/teams/team8/entrypoint.sh \
 && python manage.py collectstatic --noinput

EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=5 \
  CMD curl --fail http://localhost:8000/health/ || exit 1

CMD ["/app/teams/team8/entrypoint.sh"]
