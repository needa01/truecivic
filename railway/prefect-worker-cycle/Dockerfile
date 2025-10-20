FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies required by Prefect pull steps (git clone)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy the helper script used to manage the Prefect worker lifecycle
COPY prefect_worker_cycle.py ./prefect_worker_cycle.py

# Install Prefect (matches production worker version)
RUN pip install --no-cache-dir prefect==3.4.24

# Run the cycle once then exit
CMD ["python", "prefect_worker_cycle.py"]
