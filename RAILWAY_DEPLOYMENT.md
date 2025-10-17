# 🚂 Railway Deployment Guide - Parliament Explorer

This guide walks you through deploying Parliament Explorer to Railway with Prefect orchestration.

## 📋 Prerequisites

- Railway account ([railway.app](https://railway.app))
- GitHub repository with Parliament Explorer code
- (Optional) Prefect Cloud account ([prefect.io/cloud](https://prefect.io/cloud))

---

## 🏗️ Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│                    Railway Project                      │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL │  │  Prefect     │  │  Prefect     │  │
│  │  Database   │  │  Server      │  │  Worker      │  │
│  │  (XQge)     │  │  (intuitive- │  │  (pgvector)  │  │
│  │             │  │   flow)      │  │              │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Redis     │  │   Bucket     │  │   Console    │  │
│  │             │  │   (S3/Minio) │  │   (logs)     │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
└────────────────────────────────────────────────────────┘
```

Based on your Railway deployment diagram, you'll have:
1. **PostgreSQL Database** - For bill/politician data and Prefect metadata
2. **Redis** - For Prefect result caching and rate limiting
3. **Prefect Server** (intuitive-flow) - Orchestration server with UI
4. **Prefect Worker** (pgvector) - Executes flows
5. **Bucket** - Object storage for backups
6. **Console** - Log aggregation (optional)

---

## 🚀 Step-by-Step Deployment

### Step 1: Create Railway Project

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init
```

Or use the Railway web UI: https://railway.app/new

---

### Step 2: Add PostgreSQL Database

1. In Railway dashboard, click **"New Service"**
2. Select **"Database" → "PostgreSQL"**
3. Railway will automatically provision a PostgreSQL instance
4. Note the connection details (available as environment variables)

**Connection String Format:**
```
postgresql://postgres:password@containers-us-west-123.railway.app:5432/railway
```

---

### Step 3: Add Redis Cache

1. Click **"New Service"**
2. Select **"Database" → "Redis"**
3. Railway provisions Redis instance
4. Connection details available as `REDIS_URL`

---

### Step 4: Deploy Prefect Server

#### Option A: Prefect Cloud (Recommended)

Use Prefect's managed cloud service:

1. Sign up at [prefect.io/cloud](https://prefect.io/cloud)
2. Create a workspace
3. Get API key from Account Settings
4. Set environment variables in Railway:

```bash
PREFECT_API_URL=https://api.prefect.cloud/api/accounts/{account_id}/workspaces/{workspace_id}
PREFECT_API_KEY=your_api_key_here
```

**Advantages:**
- No infrastructure management
- Built-in monitoring and alerting
- Automatic scaling
- Free tier available

#### Option B: Self-Hosted Prefect Server (Railway)

Deploy Prefect server on Railway:

1. Create new service **"intuitive-flow"**
2. Connect to GitHub repository
3. Set environment variables:

```bash
# Database
PREFECT_API_DATABASE_CONNECTION_URL=postgresql+asyncpg://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/${PGDATABASE}

# Server settings
PREFECT_SERVER_API_HOST=0.0.0.0
PREFECT_SERVER_API_PORT=4200

# Application database
DB_DRIVER=postgresql+asyncpg
DB_HOST=${PGHOST}
DB_PORT=${PGPORT}
DB_DATABASE=${PGDATABASE}
DB_USERNAME=${PGUSER}
DB_PASSWORD=${PGPASSWORD}
```

4. Create `Dockerfile.prefect-server`:

```dockerfile
FROM prefecthq/prefect:3.4.24-python3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Expose Prefect UI
EXPOSE 4200

# Start Prefect server
CMD ["prefect", "server", "start", "--host", "0.0.0.0", "--port", "4200"]
```

5. Set **Start Command** in Railway:
```bash
prefect server start --host 0.0.0.0 --port 4200
```

---

### Step 5: Deploy Prefect Worker

1. Create new service **"pgvector"** (worker service)
2. Connect to GitHub repository
3. Set environment variables:

```bash
# Prefect API (Cloud or self-hosted)
PREFECT_API_URL=https://api.prefect.cloud/api/accounts/{account_id}/workspaces/{workspace_id}
PREFECT_API_KEY=your_api_key  # If using Prefect Cloud

# Or for self-hosted:
# PREFECT_API_URL=https://intuitive-flow-production.up.railway.app/api

# Application database
DB_DRIVER=postgresql+asyncpg
DB_HOST=${PGHOST}
DB_PORT=${PGPORT}
DB_DATABASE=${PGDATABASE}
DB_USERNAME=${PGUSER}
DB_PASSWORD=${PGPASSWORD}

# Redis
REDIS_ENABLED=true
REDIS_HOST=${REDIS_HOST}
REDIS_PORT=${REDIS_PORT}
REDIS_PASSWORD=${REDIS_PASSWORD}
```

4. Create `Dockerfile.prefect-worker`:

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

5. Set **Start Command**:
```bash
prefect worker start --pool default-agent-pool
```

---

### Step 6: Run Database Migrations

```bash
# Connect to worker service via Railway CLI
railway run python -m alembic upgrade head
```

Or add migration to worker startup:

```bash
# In Dockerfile.prefect-worker or start command
alembic upgrade head && prefect worker start --pool default-agent-pool
```

---

### Step 7: Deploy Flows

```bash
# From local machine (Prefect Cloud)
export PREFECT_API_URL="https://api.prefect.cloud/api/accounts/{account_id}/workspaces/{workspace_id}"
export PREFECT_API_KEY="your_api_key"

# Deploy all flows
prefect deploy --all

# Or deploy specific flow
prefect deployment build src/prefect_flows/bill_flows.py:fetch_latest_bills_flow \
  --name fetch-bills-hourly \
  --cron "0 * * * *" \
  --pool default-agent-pool \
  --apply
```

---

## 🔧 Configuration

### Environment Variables (Complete List)

**Required:**
```bash
# Database (PostgreSQL)
DB_DRIVER=postgresql+asyncpg
DB_HOST=${PGHOST}
DB_PORT=${PGPORT}
DB_DATABASE=${PGDATABASE}
DB_USERNAME=${PGUSER}
DB_PASSWORD=${PGPASSWORD}

# Prefect (Cloud)
PREFECT_API_URL=https://api.prefect.cloud/api/accounts/{account_id}/workspaces/{workspace_id}
PREFECT_API_KEY=your_api_key
```

**Optional:**
```bash
# Redis
REDIS_ENABLED=true
REDIS_HOST=${REDIS_HOST}
REDIS_PORT=${REDIS_PORT}
REDIS_PASSWORD=${REDIS_PASSWORD}

# Prefect Worker
PREFECT_WORKER_POOL_NAME=default-agent-pool
PREFECT_WORKER_QUERY_INTERVAL=5

# Logging
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

---

## 📊 Monitoring

### Access Prefect UI

**Prefect Cloud:**
- https://app.prefect.cloud

**Self-Hosted:**
- https://intuitive-flow-production.up.railway.app

### Check Flow Runs

```bash
# List recent flow runs
prefect flow-run ls

# View flow run logs
prefect flow-run logs <flow-run-id>

# Check worker status
prefect worker ls
```

### Database Health

```bash
# Connect to PostgreSQL
railway connect postgres

# Check tables
\dt

# Count bills
SELECT COUNT(*) FROM bills;

# Check fetch logs
SELECT * FROM fetch_logs ORDER BY created_at DESC LIMIT 10;
```

---

## 🐛 Troubleshooting

### Issue: Worker not picking up flows

**Symptoms:** Flow runs stuck in "Scheduled" state

**Solutions:**
1. Check worker is running: `railway logs --service pgvector`
2. Verify `PREFECT_API_URL` matches server
3. Ensure work pool exists: `prefect work-pool ls`
4. Create pool if missing: `prefect work-pool create default-agent-pool`

---

### Issue: Database connection failed

**Symptoms:** `could not connect to server`

**Solutions:**
1. Verify environment variables are set: `railway variables --service pgvector`
2. Check PostgreSQL is running: `railway status`
3. Test connection: `psql $DATABASE_URL`
4. Ensure `asyncpg` is installed: `pip list | grep asyncpg`

---

### Issue: Flow execution errors

**Symptoms:** Flow fails with import errors

**Solutions:**
1. Verify all dependencies installed: `pip install -r requirements.txt`
2. Check Python version: `python --version` (should be 3.11+)
3. View detailed logs: `prefect flow-run logs <flow-run-id>`
4. Test flow locally: `python -m src.prefect_flows.bill_flows`

---

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [Prefect Documentation](https://docs.prefect.io/)
- [Prefect Deployments Guide](https://docs.prefect.io/concepts/deployments/)
- [PostgreSQL Best Practices](https://www.postgresql.org/docs/current/admin.html)

---

## 🎯 Quick Commands Reference

```bash
# Deploy to Railway
railway up

# View logs
railway logs --service pgvector
railway logs --service intuitive-flow

# Run shell in service
railway run --service pgvector bash

# Connect to database
railway connect postgres

# Deploy Prefect flows
prefect deploy --all

# Start flow run manually
prefect deployment run fetch-latest-bills/fetch-bills-hourly

# Check deployment status
prefect deployment ls

# View worker logs
prefect worker start --pool default-agent-pool --log-level DEBUG
```

---

**Last Updated:** October 17, 2025
