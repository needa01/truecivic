# Parliament Explorer - Prefect Orchestration

This directory contains Prefect configuration and documentation for Parliament Explorer's orchestration layer.

## 🚀 Quick Start

### Local Development

```powershell
# 1. Set Prefect API URL (local server)
$env:PREFECT_API_URL = "http://127.0.0.1:4200/api"

# 2. Start Prefect server
prefect server start

# 3. In another terminal, run a flow manually
python -m src.prefect_flows.bill_flows
```

### Production (Railway)

```bash
# 1. Set environment variables
export PREFECT_API_URL="https://api.prefect.cloud/api/accounts/{account_id}/workspaces/{workspace_id}"
export PREFECT_API_KEY="your_prefect_cloud_api_key"

# Or use self-hosted Prefect server
export PREFECT_API_URL="https://prefect.yourdomain.com/api"

# 2. Start Prefect worker
prefect worker start --pool default-agent-pool

# 3. Deploy flows
prefect deploy --all
```

---

## 📦 Flows

### 1. `fetch-latest-bills`

Fetches latest bills from OpenParliament API and enriches with LEGISinfo data.

**Parameters:**
```yaml
limit: 50  # Number of bills to fetch
```

**Schedule Options:**
- **Hourly**: Every hour at minute 0 (cron: `0 * * * *`)
- **Daily**: Daily at 2:00 AM UTC (cron: `0 2 * * *`)

**Tags:** `production`, `bills`, `hourly/daily`

**Example Run:**
```python
from src.prefect_flows.bill_flows import fetch_latest_bills_flow
import asyncio

# Fetch 10 bills for testing
asyncio.run(fetch_latest_bills_flow(limit=10))
```

---

### 2. `fetch-parliament-session-bills`

Backfills all bills from a specific parliament and session.

**Parameters:**
```yaml
parliament: 44  # Parliament number
session: 1      # Session number
limit: 1000     # Maximum bills to fetch
```

**Schedule:** Manual trigger (no automatic schedule)

**Tags:** `backfill`, `bills`, `manual`

**Example Run:**
```python
from src.prefect_flows.bill_flows import fetch_parliament_session_bills_flow
import asyncio

# Backfill Parliament 44, Session 1
asyncio.run(fetch_parliament_session_bills_flow(
    parliament=44,
    session=1,
    limit=500
))
```

---

### 3. `monitor-fetch-operations`

Monitors fetch operations and reports statistics (success rate, avg duration, etc.).

**Parameters:**
```yaml
hours_back: 24  # Hours to look back for monitoring
```

**Schedule:** Daily at 3:00 AM UTC (cron: `0 3 * * *`)

**Tags:** `production`, `monitoring`, `daily`

**Example Run:**
```python
from src.prefect_flows.bill_flows import monitor_fetch_operations_flow
import asyncio

# Monitor last 24 hours
asyncio.run(monitor_fetch_operations_flow(hours_back=24))
```

---

## 🗄️ Database Configuration

Prefect uses PostgreSQL for:
- Flow run history
- Task execution logs
- Scheduling state
- Result persistence

### Local (SQLite - Development Only)

Prefect uses SQLite by default for local development:

```powershell
# Prefect will create ~/.prefect/prefect.db automatically
prefect server start
```

### Production (PostgreSQL on Railway)

Set the following environment variable:

```bash
PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://user:password@host:port/database"
```

**Railway PostgreSQL Example:**
```bash
PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://postgres:${PGPASSWORD}@containers-us-west-123.railway.app:5432/railway"
```

---

## 🔄 Deployment Workflow

### 1. Deploy to Prefect Cloud

```bash
# Login to Prefect Cloud
prefect cloud login

# Deploy all flows
prefect deploy --all

# Or deploy specific flow
prefect deployment build src/prefect_flows/bill_flows.py:fetch_latest_bills_flow \
  --name fetch-bills-hourly \
  --cron "0 * * * *" \
  --pool default-agent-pool \
  --apply
```

### 2. Deploy to Self-Hosted Prefect Server (Railway)

```bash
# Set API URL to your Railway Prefect server
export PREFECT_API_URL="https://prefect-production-8527.up.railway.app/api"

# Deploy flows
prefect deploy --all

# Start worker on Railway (see Railway deployment section)
```

---

## 🐳 Docker Deployment (Railway)

### Prefect Server Service

```dockerfile
FROM prefecthq/prefect:3.4.24-python3.11

WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose Prefect UI port
EXPOSE 4200

# Start Prefect server
CMD ["prefect", "server", "start", "--host", "0.0.0.0", "--port", "4200"]
```

**Railway Environment Variables:**
```bash
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://...
PREFECT_SERVER_API_HOST=0.0.0.0
PREFECT_SERVER_API_PORT=4200
```

---

### Prefect Worker Service

```dockerfile
FROM prefecthq/prefect:3.4.24-python3.11

WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Start Prefect worker
CMD ["prefect", "worker", "start", "--pool", "default-agent-pool"]
```

**Railway Environment Variables:**
```bash
PREFECT_API_URL=https://prefect-production-8527.up.railway.app/api
DB_DRIVER=postgresql+asyncpg
DB_HOST=containers-us-west-123.railway.app
DB_PORT=5432
DB_DATABASE=railway
DB_USERNAME=postgres
DB_PASSWORD=${PGPASSWORD}
```

---

## 📊 Monitoring & Observability

### Prefect UI

Access Prefect UI at:
- **Local**: http://localhost:4200
- **Production**: https://prefect-production-8527.up.railway.app

Features:
- Flow run history and logs
- Task execution details
- Schedule management
- Performance metrics

### Flow Run Logs

View logs in Prefect UI or via CLI:

```bash
# List recent flow runs
prefect flow-run ls

# View specific flow run logs
prefect flow-run logs <flow-run-id>
```

---

## 🔧 Troubleshooting

### Issue: Flow not found

**Error:** `Flow 'fetch-latest-bills' not found`

**Solution:**
```bash
# Ensure flows are deployed
prefect deploy --all

# Verify deployment
prefect deployment ls
```

---

### Issue: Worker not picking up runs

**Error:** Flow runs stuck in "Scheduled" state

**Solution:**
```bash
# Start worker
prefect worker start --pool default-agent-pool

# Check worker status
prefect worker ls
```

---

### Issue: Database connection failed

**Error:** `Could not connect to database`

**Solution:**
```bash
# Verify PREFECT_API_DATABASE_CONNECTION_URL is set correctly
echo $PREFECT_API_DATABASE_CONNECTION_URL

# Test database connection
psql $PREFECT_API_DATABASE_CONNECTION_URL
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Prefect Cloud/Server                    │
│  - Flow scheduling                                           │
│  - Run history                                               │
│  - Task logs                                                 │
│  - UI/API                                                    │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ API
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                      Prefect Worker                          │
│  - Executes flows                                            │
│  - Polls for scheduled runs                                  │
│  - Reports status back                                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ Runs flows
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                   Parliament Explorer Flows                  │
│  fetch_latest_bills_flow                                     │
│  fetch_parliament_session_bills_flow                         │
│  monitor_fetch_operations_flow                               │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ Uses
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              BillIntegrationService                          │
│  - BillPipeline (OpenParliament + LEGISinfo)                 │
│  - BillRepository (Database persistence)                     │
└─────────────────┬───────────────────────────────────────────┘
                  │
                  │ Persists to
                  │
┌─────────────────▼───────────────────────────────────────────┐
│                PostgreSQL Database (Railway)                 │
│  - Bills table                                               │
│  - Politicians table                                         │
│  - Fetch logs table                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 📚 Additional Resources

- [Prefect Documentation](https://docs.prefect.io/)
- [Prefect Cloud](https://www.prefect.io/cloud)
- [Prefect Deployments Guide](https://docs.prefect.io/concepts/deployments/)
- [Railway Deployment Guide](https://docs.railway.app/)

---

**Last Updated:** October 17, 2025
