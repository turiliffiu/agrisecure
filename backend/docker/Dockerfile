# AgriSecure IoT System - Dockerfile
# Django Backend con Python 3.12

FROM python:3.12-slim

# Metadata
LABEL maintainer="Turiliffiu"
LABEL description="AgriSecure IoT Backend"
LABEL version="1.0.0"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV APP_HOME=/app

# Working directory
WORKDIR $APP_HOME

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN addgroup --system django && \
    adduser --system --ingroup django django && \
    chown -R django:django $APP_HOME

# Switch to non-root user
USER django

# Expose port
EXPOSE 8000

# Default command
CMD ["gunicorn", "agrisecure.wsgi:application", "--bind", "0.0.0.0:8000"]
