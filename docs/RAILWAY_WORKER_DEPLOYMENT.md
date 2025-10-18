# Railway Worker Deployment - Implementation Guide

**Status**: Ready for deployment  
**Date**: October 18, 2025  
**Objective**: Deploy Prefect Worker to Railway for production ETL execution

---

## What Is Blocker #1?

**Problem**: ETL flows run successfully on local machine but:
- Data doesn't persist to Railway PostgreSQL
- No worker service exists to execute flows on schedule
- `intuitive-flow` service is misconfigured as a web service instead of worker

**Impact**: 
- ❌ Scheduled flows cannot run (no worker to pick up tasks)
- ❌ Data ingestion stalled in production
- ❌ API serves stale data

**Solution**: Deploy Prefect Worker service to Railway with proper configuration

---

## Implementation Checklist

### Phase 1: Codebase Preparation (✅ DONE - This PR)

- [x] `railway-worker.dockerfile` exists with correct CMD
- [x] `requirements.txt` includes all dependencies (prefect, sqlalchemy, redis, minio, aiokafka)
- [x] `prefect.yaml` defines all deployments with schedules
- [x] `railway.json` documents service configuration
- [x] Environment variables documented

**Files Created/Modified**:
- ✅ `railway.json` (new) - Service configuration template
- ✅ `RAILWAY_WORKER_DEPLOYMENT.md` (this file) - Step-by-step guide

### Phase 2: Railway Dashboard Configuration (⏳ MANUAL - Requires Dashboard Access)

**What You Need to Do**:

1. **Log into Railway Dashboard**
   - URL: https://railway.app/dashboard
   - Project: `truecivic`

2. **Reconfigure `intuitive-flow` Service** (or create new)
   
   **Option A: Reconfigure Existing Service** (Recommended)
   ```
   Settings → Service Settings
   - Service Type: Change from "Web Service" to "Worker Service"
   - Dockerfile Path: railway-worker.dockerfile
   - Start Command: prefect worker start --pool default-agent-pool --name railway-worker
   - Root Directory: /app
   ```

   **Option B: Create New Service** (If reconfigure doesn't work)
   ```
   + New → Empty Service
   - Name: prefect-worker
   - Repository: monuit/truecivic
   - Dockerfile Path: railway-worker.dockerfile
   - Service Type: Worker
   ```

3. **Set Environment Variables**
   
   In Railway dashboard, go to `prefect-worker` service → Variables:

   ```bash
   # Prefect Configuration
   PREFECT_API_URL=https://prefect-production-a5a7.up.railway.app/api

   # Database (use Railway variable reference)
   DATABASE_PUBLIC_URL=${{PostgreSQL.DATABASE_PUBLIC_URL}}

   # Redis (use Railway variable reference)
   REDIS_URL=${{Redis.REDIS_URL}}

   # MinIO (if configured)
   MINIO_ENDPOINT=${{MinIO.MINIO_ENDPOINT}}
   MINIO_ACCESS_KEY=${{MinIO.MINIO_ACCESS_KEY}}
   MINIO_SECRET_KEY=${{MinIO.MINIO_SECRET_KEY}}

   # Python Configuration
   PYTHONUNBUFFERED=1
   ```

   **Important**: Use Railway's variable reference syntax `${{ServiceName.VARIABLE}}` so variables auto-update if services are recreated.

4. **Deploy Service**
   - Click **Deploy** button or wait for auto-deploy
   - Monitor logs for success:
     ```
     ✅ Building docker image from railway-worker.dockerfile
     ✅ Installing dependencies from requirements.txt
     ✅ Starting Prefect worker
     ✅ Connected to Prefect Server
     ✅ Polling for flow runs...
     ```

### Phase 3: Deploy Flows to Railway (⏳ LOCAL - Run from Your Machine)

Once worker is running on Railway, deploy flows from your local machine:

```bash
# Navigate to project
cd c:\Users\boredbedouin\Desktop\truecivic

# Set Prefect API to Railway
$env:PREFECT_API_URL = "https://prefect-production-a5a7.up.railway.app/api"

# Deploy all flows
prefect deploy --all

# Verify deployments
prefect deployment ls
```

**Expected Output**:
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Name                              ┃ Schedule          ┃ Tags        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ fetch-bills-hourly                │ Cron: 0 * * * *   │ production  │
│ fetch-bills-daily                 │ Cron: 0 2 * * *   │ production  │
│ fetch-votes-hourly                │ Cron: 30 * * * *  │ production  │
│ fetch-votes-daily                 │ Cron: 0 3 * * *   │ production  │
│ fetch-committee-meetings-daily    │ Cron: 0 4 * * *   │ production  │
│ fetch-top-committees-meetings     │ Cron: 0 5 * * *   │ production  │
│ fetch-debates-with-speeches       │ Cron: 0 6 * * *   │ production  │
│ fetch-top-debates                 │ Cron: 0 7 * * *   │ production  │
│ backfill-parliament-session       │ None (manual)     │ backfill    │
└━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┴───────────────────┴─────────────┘
```

### Phase 4: Verify End-to-End Pipeline (⏳ LOCAL - Trigger Tests)

```bash
# Manually trigger a test flow run
prefect deployment run fetch-bills-hourly

# Monitor execution
# - Prefect UI: https://prefect-production-a5a7.up.railway.app
# - Railway Logs: https://railway.app/dashboard → prefect-worker → Logs
```

**Verify Data Persistence**:
```bash
# Run validation script
python scripts/run_etl_test_no_cache.py

# Expected output:
# ✅ ETL completed: 5 bills fetched
# ✅ Database validated: 5 bills persisted to Railway PostgreSQL
# ✅ Worker successfully executed flow
```

---

## Deployment Schedule

All flows are configured with UTC cron schedules:

```
├─ 0 * * * *  (Every hour at minute 0)
│  └─ fetch-bills-hourly (50 bills)
│
├─ 30 * * * * (Every hour at minute 30)
│  └─ fetch-votes-hourly (10 votes)
│
├─ 0 2 * * *  (Daily at 2 AM UTC)
│  └─ fetch-bills-daily (100 bills)
│
├─ 0 3 * * *  (Daily at 3 AM UTC)
│  └─ fetch-votes-daily (50 votes)
│
├─ 0 4 * * *  (Daily at 4 AM UTC)
│  └─ fetch-committee-meetings-daily
│
├─ 0 5 * * *  (Daily at 5 AM UTC)
│  └─ fetch-top-committees-meetings
│
├─ 0 6 * * *  (Daily at 6 AM UTC)
│  └─ fetch-debates-with-speeches
│
└─ 0 7 * * *  (Daily at 7 AM UTC)
   └─ fetch-top-debates
```

**Total Daily Data Volume**:
- ~250 bills (50/hr × 4 + 100 daily)
- ~150 votes (10/hr × 4 + 50 daily)
- ~1000 committee meetings (5 committees × 2 daily runs)
- ~500 debate speeches (extracted daily)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Railway Platform                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │  Prefect Server  │    │ PostgreSQL       │              │
│  │  (Cloud)         │◄──►│ + pgvector       │              │
│  └──────────────────┘    └──────────────────┘              │
│           ▲                                                  │
│           │ Polls for                                        │
│           │ flow runs                                        │
│           │                                                  │
│  ┌────────┴─────────────────┐                              │
│  │  Prefect Worker Service  │                              │
│  │  (railway-worker.docker) │                              │
│  │                          │                              │
│  │  Executes flows:         │                              │
│  │  - fetch-bills-hourly    │                              │
│  │  - fetch-votes-hourly    │                              │
│  │  - fetch-meetings-daily  │                              │
│  │  - fetch-speeches-daily  │                              │
│  └────────────┬─────────────┘                              │
│               │                                              │
│               ├──► OpenParliament API                       │
│               ├──► LEGISinfo API                            │
│               └──► Database (PostgreSQL)                    │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐              │
│  │ Redis            │    │ MinIO (S3)       │              │
│  │ (Cache/Results)  │    │ (Object Storage) │              │
│  └──────────────────┘    └──────────────────┘              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Issue: Worker doesn't connect to Prefect Server

**Symptom**:
```
ERROR: Failed to connect to Prefect API at https://prefect-production-a5a7.up.railway.app/api
```

**Fixes**:
1. Verify `PREFECT_API_URL` environment variable is set correctly
2. Check Railway Prefect Server service is running
3. Test connectivity: `curl https://prefect-production-a5a7.up.railway.app/api`

### Issue: Worker connects but doesn't execute flows

**Symptom**:
```
Connected to Prefect Server
Polling for flow runs on work pool 'default-agent-pool'
(no activity after 5+ minutes)
```

**Fixes**:
1. Verify flows are deployed: `prefect deployment ls`
2. Check work pool name matches: `prefect work-pool ls`
3. Manually trigger a test run: `prefect deployment run fetch-bills-hourly`

### Issue: Flow executes but data not persisting

**Symptom**:
```
Flow run completed successfully
(but database still shows 0 bills)
```

**Fixes**:
1. Check DATABASE_PUBLIC_URL is correct: `psql <url>`
2. Verify PostgreSQL tables exist: `\dt` in psql
3. Check logs for database errors: Railway logs → prefect-worker
4. Run migration if needed: `alembic upgrade head`

### Issue: Out of memory or timeout

**Symptom**:
```
OOMKilled or Connection timeout after 30 minutes
```

**Fixes**:
1. Increase Railway worker resources (CPU/Memory)
2. Reduce batch sizes in flow parameters
3. Add task-level timeouts to detect hanging tasks
4. Split large flows into smaller sub-flows

---

## Files Included in This Implementation

| File | Purpose | Status |
|------|---------|--------|
| `railway-worker.dockerfile` | Docker image for worker service | ✅ Existing |
| `requirements.txt` | Python dependencies | ✅ Updated |
| `prefect.yaml` | Flow deployment config | ✅ Existing |
| `railway.json` | Railway service config template | ✅ New |
| `RAILWAY_WORKER_DEPLOYMENT.md` | This deployment guide | ✅ New |

---

## Next Steps After Deployment

1. **Monitor worker health** (first 24 hours)
   - Watch for any connection errors
   - Verify all scheduled flows run at scheduled times
   - Check data volume in database grows as expected

2. **Optimize performance** (if needed)
   - Adjust batch sizes based on actual volume
   - Monitor worker resource utilization
   - Tune database indexes if queries are slow

3. **Setup monitoring** (Phase E)
   - Create Prefect monitoring dashboard
   - Setup alerts for failed flow runs
   - Create database metrics dashboard

4. **Test coverage** (Phase E)
   - Write pytest tests for flows
   - Create integration tests
   - Setup CI/CD for automated testing

---

## Success Criteria

✅ **Blocker #1 Resolved When**:
- [ ] Worker service runs successfully on Railway
- [ ] Worker connects to Prefect Server
- [ ] At least one scheduled flow runs and completes
- [ ] Data persists to Railway PostgreSQL database
- [ ] Bills, votes, committees, and speeches are in database
- [ ] API can query the data from database

**Estimated Time**: 30-60 minutes (mostly manual Railway dashboard configuration)
