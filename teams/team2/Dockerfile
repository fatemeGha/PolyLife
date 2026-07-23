# Base image for Team2 microservice
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=teams.team2.config.settings

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY teams/team2/requirements.txt /app/team2_requirements.txt
RUN pip install --no-cache-dir -r /app/team2_requirements.txt

# Copy project source
COPY . /app/

# Default command (overridden in docker-compose per service)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
