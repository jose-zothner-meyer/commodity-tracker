# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies
# - build-essential: for compiling some Python packages if needed from source
# - libpq-dev: for psycopg2 (PostgreSQL adapter)
# - gettext: for Django's internationalization features if used
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gettext \
    # Add any other system dependencies your project needs
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt /app/
# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . /app/

# Expose the port the app runs on (same as Gunicorn/Uvicorn will run on)
EXPOSE 8000

# Command to run the application using Gunicorn (for production)
# Ensure 'gunicorn' is in your requirements.txt
# Adjust --workers based on your server's CPU cores (typically 2-4 per core)
# The DJANGO_SETTINGS_MODULE might need to be set if you have separate production settings
# ENV DJANGO_SETTINGS_MODULE=commodity_tracker.settings.production
# CMD ["gunicorn", "commodity_tracker.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]

# For development, you might run manage.py runserver, but this is not for production.
# A separate docker-compose.override.yml is better for development command.
# If this Dockerfile is ONLY for production, the Gunicorn CMD is appropriate.
# If it's also for dev, you might have a more generic entrypoint script. 