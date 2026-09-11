FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies required for psycopg2 build and runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ .

# Create volume mount point for employee profile photo uploads
RUN mkdir -p /uploads && chmod 777 /uploads

EXPOSE 5000

# Run with Gunicorn WSGI server for production reliability
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
