FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy the helper script used to manage the Prefect worker lifecycle
COPY ../../scripts/prefect_worker_cycle.py ./scripts/prefect_worker_cycle.py

# Install Prefect (matches production worker version)
RUN pip install --no-cache-dir prefect==3.4.24

# Run the cycle once then exit
CMD ["python", "scripts/prefect_worker_cycle.py"]
