# Dagster Orchestration

This directory contains Dagster assets, jobs, and schedules for orchestrating Parliament Explorer's data pipelines.

## Overview

Dagster manages scheduled data fetching and processing:
- **Assets**: Data artifacts (bills, politicians, monitoring stats)
- **Jobs**: Collections of assets that run together
- **Schedules**: Cron-based triggers for automatic execution
- **Sensors**: Event-driven triggers (future)

## Quick Start

### 1. Start Dagster Web UI (Development)

```powershell
# Set Dagster home directory
$env:DAGSTER_HOME = "dagster_home"

# Start Dagster development server (combines webserver + daemon)
python -m dagster dev -f workspace.yaml
```

Then open: http://localhost:3000

### 2. Run Assets Manually

In the Dagster UI:
1. Navigate to **Assets** tab
2. Select `fetch_latest_bills`
3. Click **Materialize**
4. View logs and metadata in real-time

### 3. Enable Schedules

Schedules are **disabled by default**. To enable:

1. Navigate to **Schedules** tab
2. Find `fetch_bills_hourly` or `fetch_bills_daily`
3. Click **Start Schedule**

Dagster will now automatically run the job on schedule.

## Available Assets

### `fetch_latest_bills`
- **Group**: bills
- **Description**: Fetch most recent bills from OpenParliament, enrich with LEGISinfo, persist to database
- **Config**:
  ```yaml
  ops:
    fetch_latest_bills:
      config:
        limit: 50  # Number of bills to fetch
  ```

### `fetch_parliament_session_bills`
- **Group**: bills
- **Description**: Fetch all bills from a specific parliament and session (for backfilling)
- **Config**:
  ```yaml
  ops:
    fetch_parliament_session_bills:
      config:
        parliament: 44
        session: 1
        limit: 1000
  ```

### `monitor_fetch_operations`
- **Group**: monitoring
- **Description**: Monitor recent fetch operations, report success/failure rates and durations
- **Config**:
  ```yaml
  ops:
    monitor_fetch_operations:
      config:
        hours_back: 24  # Monitor last N hours
  ```

## Available Schedules

### `fetch_bills_hourly`
- **Cron**: `0 * * * *` (every hour at minute 0)
- **Job**: `fetch_bills_job` (50 most recent bills)
- **Status**: Stopped by default

### `fetch_bills_daily`
- **Cron**: `0 2 * * *` (daily at 2:00 AM)
- **Job**: `fetch_bills_job` (50 most recent bills)
- **Status**: Stopped by default

### `monitor_daily`
- **Cron**: `0 3 * * *` (daily at 3:00 AM)
- **Job**: `monitor_job` (last 24 hours)
- **Status**: Stopped by default

## Production Deployment

### Railway Setup

1. **Set environment variables**:
   ```bash
   DAGSTER_HOME=/app/dagster_home
   DAGSTER_POSTGRES_URL=postgresql://user:pass@host:port/dagster
   ```

2. **Update `dagster_home/dagster.yaml`**:
   - Uncomment PostgreSQL configuration
   - Use `${DAGSTER_POSTGRES_URL}` for connection

3. **Run Dagster daemon**:
   ```bash
   dagster-daemon run &
   dagster-webserver -h 0.0.0.0 -p 3000 -f workspace.yaml
   ```

### Docker Compose

```yaml
services:
  dagster-webserver:
    image: python:3.13
    command: dagster-webserver -h 0.0.0.0 -p 3000 -f workspace.yaml
    ports:
      - "3000:3000"
    environment:
      DAGSTER_HOME: /app/dagster_home
    volumes:
      - .:/app

  dagster-daemon:
    image: python:3.13
    command: dagster-daemon run
    environment:
      DAGSTER_HOME: /app/dagster_home
    volumes:
      - .:/app
```

## Asset Metadata

Dagster tracks rich metadata for each asset materialization:

**Bills Assets**:
- `bills_fetched`: Number of bills fetched
- `bills_created`: Number of new bills created
- `bills_updated`: Number of existing bills updated
- `error_count`: Number of errors encountered
- `duration_seconds`: Fetch duration
- `fetch_timestamp`: When the fetch occurred

**Monitoring Assets**:
- `hours_monitored`: Time window monitored
- `{status}_count`: Number of operations per status
- `{status}_avg_duration`: Average duration per status
- `{status}_total_succeeded`: Total successful records per status
- `{status}_total_failed`: Total failed records per status

## Troubleshooting

### "ModuleNotFoundError: No module named 'src'"
- Ensure you're running from project root
- Check `workspace.yaml` has `working_directory: .`

### "Database is locked" (SQLite)
- SQLite doesn't support concurrent writes
- For production, use PostgreSQL in `dagster.yaml`

### Schedule not running
- Check schedule is **Started** in UI
- Verify `dagster-daemon` is running (in dev mode, it's automatic)
- Check logs: `dagster_home/storage/schedules/`

### Asset fails with "Cannot find module"
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check imports in asset file match project structure

## Architecture

```
dagster_home/              # Dagster instance directory
├── dagster.yaml          # Instance configuration
└── storage/              # Run/event/schedule storage (SQLite)

src/dagster_assets/        # Asset definitions
├── bill_assets.py        # Bill fetching assets
├── definitions.py        # Jobs, schedules, resources
└── __init__.py

workspace.yaml             # Workspace configuration
```

## Next Steps

1. **Add more assets**:
   - `fetch_politicians` (parallel to bills)
   - `generate_rss_feeds` (after API layer)
   - `update_embeddings` (for semantic search)

2. **Add sensors**:
   - Trigger on new bills detected
   - Alert on fetch failures
   - React to external webhooks

3. **Add partitions**:
   - Daily partitions for time-series data
   - Parliament/session partitions for backfilling

4. **Add tests**:
   - Unit tests for asset logic
   - Integration tests for full job runs
