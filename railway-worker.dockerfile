# Railway Dockerfile for Prefect Worker
# This service executes the ETL flows

FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables will be set by Railway
ENV PYTHONUNBUFFERED=1

# Start Prefect worker
# The worker will:
# 1. Connect to Prefect Server (via PREFECT_API_URL)
# 2. Poll for flow runs
# 3. Execute flows that write to pgvector, Redis, Kafka, MinIO
CMD ["prefect", "worker", "start", "--pool", "default-agent-pool", "--name", "railway-worker"]
