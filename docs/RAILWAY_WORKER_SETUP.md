# Railway Worker Setup Guide

**Status**: CRITICAL - Worker service failed, blocking all ETL operations  
**Last Updated**: October 17, 2025

---

## 🚨 Problem Summary

**Current State:**
- ❌ `intuitive-flow` service **FAILED** (trying to run non-existent frontend)
- ❌ No Prefect Worker running on Railway to execute flows
- ❌ ETL says "5 bills updated" but database has 0 bills
- ❌ Data not persisting to Railway PostgreSQL database

**Root Cause:**
- `intuitive-flow` is configured as a **web service** but should be a **worker service**
- Service is trying to start a web app that doesn't exist yet (frontend not built)
- Prefect flows run locally but need a Railway-based worker to persist data correctly

---

## ✅ Solution: Deploy Prefect Worker Service

### Step 1: Railway Dashboard Configuration

1. **Navigate to Railway Dashboard**: https://railway.app/dashboard

2. **Option A: Reconfigure Existing Service** (Recommended)
   - Go to `intuitive-flow` service
   - Click **Settings** → **Service Settings**
   - Change **Service Type** from "Web Service" to "Worker Service"
   - Update **Start Command** to: `prefect worker start --pool default-agent-pool --name railway-worker`
   - Update **Root Directory** to: `/app`
   - Update **Dockerfile Path** to: `railway-worker.dockerfile`

3. **Option B: Create New Service** (If above fails)
   - Delete `intuitive-flow` service (or rename it)
   - Click **+ New** → **Empty Service**
   - Name it: `prefect-worker`
   - Connect to GitHub repository: `monuit/truecivic`
   - Set **Dockerfile Path**: `railway-worker.dockerfile`
   - Set **Service Type**: Worker

### Step 2: Environment Variables

Configure the following environment variables in Railway dashboard:

```bash
# Prefect Configuration
PREFECT_API_URL=https://prefect-production-a5a7.up.railway.app/api

# Database Connection (Railway PostgreSQL with pgvector)
DATABASE_PUBLIC_URL=${{PostgreSQL.DATABASE_PUBLIC_URL}}
# Example: postgresql://postgres:PASSWORD@shortline.proxy.rlwy.net:21723/railway

# Redis Cache
REDIS_URL=${{Redis.REDIS_URL}}
# Example: redis://default:PASSWORD@nozomi.proxy.rlwy.net:10324

# Kafka Stream (Optional - for future event streaming)
KAFKA_PUBLIC_URL=${{Kafka.KAFKA_PUBLIC_URL}}
# Example: yamabiko.proxy.rlwy.net:11594

# MinIO Object Storage
MINIO_ENDPOINT=${{MinIO.MINIO_ENDPOINT}}
MINIO_ACCESS_KEY=${{MinIO.MINIO_ACCESS_KEY}}
MINIO_SECRET_KEY=${{MinIO.MINIO_SECRET_KEY}}
# Endpoint example: bucket-production-62fe.up.railway.app

# Python Configuration
PYTHONUNBUFFERED=1
```

**Important Notes:**
- Use Railway's **variable references** syntax `${{ServiceName.VARIABLE}}`
- This ensures variables auto-update if services are recreated
- Don't hardcode sensitive values

### Step 3: Deploy Worker Service

1. **Trigger Deployment:**
   - Railway will auto-deploy after configuration changes
   - Or manually click **Deploy** button

2. **Monitor Deployment Logs:**
   ```
   ✅ Building Docker image from railway-worker.dockerfile
   ✅ Installing dependencies from requirements.txt
   ✅ Starting Prefect worker
   ✅ Worker connected to Prefect Server
   ✅ Polling for flow runs...
   ```

3. **Expected Success Output:**
   ```
   prefect worker start --pool default-agent-pool --name railway-worker
   Connected to Prefect Server: https://prefect-production-a5a7.up.railway.app/api
   Worker 'railway-worker' started
   Polling for flow runs on work pool 'default-agent-pool'
   ```

### Step 4: Deploy Prefect Flows to Railway

Once worker is running, deploy flows from your local machine:

```bash
# Set Prefect API to Railway
export PREFECT_API_URL=https://prefect-production-a5a7.up.railway.app/api

# Deploy all flows from prefect.yaml
prefect deploy --all

# Verify deployments
prefect deployment ls
```

**Expected Output:**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Name                         ┃ Schedule          ┃ Tags          ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ fetch-bills-hourly           │ Cron: 0 * * * *   │ production    │
│ fetch-bills-daily            │ Cron: 0 2 * * *   │ bills, daily  │
│ monitor-daily                │ Cron: 0 3 * * *   │ monitoring    │
│ backfill-parliament-session  │ None (manual)     │ backfill      │
└──────────────────────────────┴───────────────────┴───────────────┘
```

### Step 5: Test End-to-End Pipeline

**Trigger a test flow run:**

```bash
# Manually trigger hourly bill fetch
prefect deployment run fetch-bills-hourly

# Monitor execution in Railway logs or Prefect UI
```

**Check Prefect UI:**
- Go to: https://prefect-production-a5a7.up.railway.app
- Navigate to **Flow Runs** tab
- Look for `fetch-latest-bills-flow` execution
- Status should be: ✅ **Completed**

**Verify Data Persistence:**

```bash
# Run validation script
python scripts/run_etl_test_no_cache.py
```

**Expected Result:**
```
✅ ETL completed: 5 bills fetched
✅ Database validated: 5 bills in railway database
✅ Fetch logs written: 1 entry
✅ Bills created: 5
```

---

## 🔧 Troubleshooting

### Issue: Worker not connecting to Prefect Server

**Symptom:**
```
Failed to connect to Prefect API at https://prefect-production-a5a7.up.railway.app/api
```

**Fix:**
1. Verify `PREFECT_API_URL` environment variable is set correctly
2. Check Prefect Server service is running in Railway
3. Verify Prefect Server is accessible (visit URL in browser)

### Issue: Worker connects but doesn't execute flows

**Symptom:**
```
Worker 'railway-worker' started
Polling for flow runs on work pool 'default-agent-pool'
(no activity)
```

**Fix:**
1. Verify flows are deployed: `prefect deployment ls`
2. Check work pool name matches: `prefect work-pool ls`
3. Manually trigger a flow: `prefect deployment run fetch-bills-hourly`

### Issue: Flow runs but data not persisting

**Symptom:**
```
Flow run completed successfully
(but database still has 0 bills)
```

**Fix:**
1. Check `DATABASE_PUBLIC_URL` is set correctly
2. Verify database connection in flow logs
3. Check for transaction commit issues in BillIntegrationService
4. Verify Railway PostgreSQL service has public networking enabled

### Issue: Permission denied errors

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/app/logs'
```

**Fix:**
1. Remove hardcoded log paths from flows
2. Use stdout/stderr for logging (captured by Railway)
3. Or create logs directory in Dockerfile:
   ```dockerfile
   RUN mkdir -p /app/logs && chmod 777 /app/logs
   ```

---

## 📊 Success Criteria

✅ Worker service shows **RUNNING** status in Railway dashboard  
✅ Worker logs show: `Polling for flow runs on work pool 'default-agent-pool'`  
✅ `prefect deployment ls` shows 4 deployments  
✅ Manual flow run completes successfully  
✅ Database query returns bills: `SELECT COUNT(*) FROM bills;` > 0  
✅ Hourly cron schedule triggers automatically  
✅ Prefect UI shows successful flow runs  

---

## 📁 Related Files

- **Dockerfile**: `railway-worker.dockerfile` (25 lines)
- **Flow Definitions**: `src/prefect_flows/bill_flows.py`
- **Deployment Config**: `prefect.yaml`
- **Validation Script**: `scripts/run_etl_test_no_cache.py`
- **Service Code**: `src/services/bill_integration_service.py`

---

## 🚀 After Worker is Fixed

Once the worker is operational, proceed with:

1. **Phase D**: Complete remaining data adapters (vote records, committees, speeches)
2. **Phase F**: Build Next.js frontend with graph visualization
3. **Phase G**: Complete RAG pipeline and ranking system
4. **Phase H**: Production hardening (testing, monitoring, deployment)

---

## 📞 Support

If issues persist after following this guide:
1. Check Railway service logs for detailed error messages
2. Review Prefect Server logs in Railway dashboard
3. Verify all environment variables are set correctly
4. Test database connection manually: `psql $DATABASE_PUBLIC_URL`

---

**Status**: Ready for Railway deployment  
**Next**: Follow Step 1 to reconfigure `intuitive-flow` service
