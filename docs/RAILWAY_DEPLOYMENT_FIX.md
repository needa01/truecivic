# Railway Deployment Fix Guide

**URGENT**: Railway deployment failing due to misconfigured service

**Last Updated**: October 17, 2025  
**Status**: CRITICAL - Main service trying to deploy frontend instead of API

---

## 🚨 Problem

Railway is trying to deploy the **frontend** as the main service, but:
- Frontend deployment is failing (likely missing env vars or build issues)
- The **API backend** is not being deployed
- The **Prefect Worker** is not running (referenced as `intuitive-flow` service)

**Result**: No services are operational on Railway

---

## ✅ Solution: 3-Service Architecture

Railway should have **3 separate services**:

1. **truecivic-api** (FastAPI backend) - Main application
2. **truecivic-worker** (Prefect worker) - ETL pipeline
3. **truecivic-frontend** (Next.js) - User interface (optional for now)

---

## 🚀 URGENT FIX: Deploy API Service

### Step 1: Update Main Service to Deploy API

The main repository service should deploy the **API**, not the frontend.

**✅ DONE**: Updated `railway.toml` to deploy API using `api.dockerfile`

### Step 2: Configure Main Service in Railway Dashboard

1. **Go to Railway Dashboard**: https://railway.app/dashboard
2. **Find your main service** (probably called `truecivic` or `intuitive-flow`)
3. **Click on the service** → **Settings**
4. **Update Configuration**:
   - **Service Name**: `truecivic-api`
   - **Root Directory**: `/` (leave empty or set to root)
   - **Railway Config File Path**: `railway.toml` (default)
   - **Start Command**: (leave empty - railway.toml handles this)

5. **Set Environment Variables**:
   ```bash
   # Database (link to your PostgreSQL service)
   DATABASE_URL=${{PostgreSQL.DATABASE_URL}}
   DATABASE_PUBLIC_URL=${{PostgreSQL.DATABASE_PUBLIC_URL}}
   
   # Redis (link to your Redis service)
   REDIS_URL=${{Redis.REDIS_URL}}
   
   # Prefect (link to your Prefect Server service)
   PREFECT_API_URL=${{Prefect-Server.URL}}/api
   
   # MinIO (link to your MinIO service)
   MINIO_ENDPOINT=${{MinIO.MINIO_ENDPOINT}}
   MINIO_ACCESS_KEY=${{MinIO.MINIO_ACCESS_KEY}}
   MINIO_SECRET_KEY=${{MinIO.MINIO_SECRET_KEY}}
   MINIO_SECURE=false
   
   # Application Settings
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   CORS_ORIGINS=*
   
   # Railway provides this automatically
   PORT=8000
   ```

6. **Deploy**:
   - Click **Deploy** or push to GitHub to trigger deployment
   - Monitor logs for successful startup

7. **Verify Deployment**:
   - Check service URL: `https://your-service.up.railway.app/health`
   - Should return: `{"status":"healthy"}`
   - Check API docs: `https://your-service.up.railway.app/docs`

---

## 🔧 Step 3: Fix/Deploy Worker Service

### Option A: Update Existing Service

If you have a service called `intuitive-flow`:

1. **Go to the service** → **Settings**
2. **Update Configuration**:
   - **Service Name**: `truecivic-worker`
   - **Root Directory**: `/`
   - **Dockerfile Path**: `railway-worker.dockerfile`
   - **Service Type**: Worker (not Web)
   - **Start Command**: (leave empty - dockerfile handles this)

3. **Set Environment Variables**:
   ```bash
   # Same as API service, plus:
   PREFECT_API_URL=${{Prefect-Server.URL}}/api
   DATABASE_URL=${{PostgreSQL.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   ```

4. **Deploy** and verify logs show:
   ```
   Worker 'railway-worker' started
   Polling for flow runs on work pool 'default-agent-pool'
   ```

### Option B: Create New Worker Service

1. **Click** **+ New** in Railway dashboard
2. **Select** **Empty Service**
3. **Name**: `truecivic-worker`
4. **Connect** to your GitHub repository
5. **Configure** as described in Option A above

---

## 🎨 Step 4: Deploy Frontend (Optional)

The frontend can be deployed separately or later. For now, focus on API + Worker.

### When Ready to Deploy Frontend:

1. **Create new Railway service**
2. **Name**: `truecivic-frontend`
3. **Settings**:
   - **Root Directory**: `frontend`
   - **Railway Config File Path**: `railway-frontend.toml`
   - **Build Command**: `npm ci && npm run build`
   - **Start Command**: `npm run start`

4. **Environment Variables**:
   ```bash
   NEXT_PUBLIC_API_URL=${{truecivic-api.URL}}
   NODE_ENV=production
   ```

5. **Deploy** and verify at service URL

---

## 📋 Verification Checklist

After deploying, verify each service:

### API Service (truecivic-api)
- [ ] Service shows **RUNNING** status
- [ ] Health endpoint responds: `curl https://your-api.up.railway.app/health`
- [ ] API docs accessible: `https://your-api.up.railway.app/docs`
- [ ] Logs show: `Uvicorn running on http://0.0.0.0:8000`
- [ ] No database connection errors

### Worker Service (truecivic-worker)
- [ ] Service shows **RUNNING** status
- [ ] Logs show: `Worker 'railway-worker' started`
- [ ] Logs show: `Polling for flow runs on work pool 'default-agent-pool'`
- [ ] Can trigger flow from local: `prefect deployment run fetch-bills-hourly`
- [ ] Flow executes and completes successfully

### Database
- [ ] Can query from API: `SELECT COUNT(*) FROM bills;`
- [ ] Returns count > 0 after running ETL flow

---

## 🚨 Common Issues & Fixes

### Issue: "Build failed - cannot find api.dockerfile"

**Fix**: 
- Ensure `api.dockerfile` is in root directory
- Check Railway service **Root Directory** is `/` or empty
- Verify **Dockerfile Path** is `api.dockerfile`

### Issue: "Health check failed"

**Fix**:
- Check API logs for startup errors
- Verify `DATABASE_URL` is set correctly
- Try accessing `/health` endpoint manually
- Increase health check timeout in railway.toml

### Issue: "Worker not connecting to Prefect"

**Fix**:
- Verify `PREFECT_API_URL` is set correctly
- Format should be: `https://your-prefect-server.up.railway.app/api`
- Check Prefect Server service is running
- Test connection: `curl $PREFECT_API_URL/health`

### Issue: "Database connection refused"

**Fix**:
- Verify Railway PostgreSQL service is running
- Use `${{PostgreSQL.DATABASE_URL}}` reference syntax
- Check if PostgreSQL has public networking enabled
- Try connecting with `psql $DATABASE_URL` from local

### Issue: "ModuleNotFoundError"

**Fix**:
- Verify all dependencies are in `requirements.txt`
- Check Railway build logs for pip install errors
- Ensure virtual environment isn't committed to git
- Clear Railway cache and redeploy

---

## 📁 Files Changed

### Modified:
1. **`railway.toml`** - Now deploys API using api.dockerfile

### Created:
2. **`railway-frontend.toml`** - Configuration for frontend service (when ready)
3. **`docs/RAILWAY_DEPLOYMENT_FIX.md`** - This guide

### Existing (No Changes):
4. **`api.dockerfile`** - API service Dockerfile (already exists)
5. **`railway-worker.dockerfile`** - Worker service Dockerfile (already exists)

---

## 🎯 Next Steps After Fix

Once services are running:

1. **Deploy Prefect Flows**:
   ```bash
   export PREFECT_API_URL=https://your-prefect-server.up.railway.app/api
   prefect deploy --all
   ```

2. **Trigger Test Flow**:
   ```bash
   prefect deployment run fetch-bills-hourly
   ```

3. **Verify Data**:
   ```bash
   psql $DATABASE_PUBLIC_URL -c "SELECT COUNT(*) FROM bills;"
   ```

4. **Monitor Logs**:
   - API service logs
   - Worker service logs
   - Prefect Server UI

5. **Configure Monitoring** (optional):
   - Set up alerts for service failures
   - Configure log aggregation
   - Set up uptime monitoring

---

## 📞 Support

If issues persist:

1. **Check Railway Logs**:
   - Click service → **Deployments** → Latest deployment → **View Logs**
   - Look for error messages in build or runtime logs

2. **Test Locally**:
   - Run API: `uvicorn api.main:app --reload`
   - Run Worker: `prefect worker start --pool default-agent-pool`
   - Verify services work before debugging Railway

3. **Railway Documentation**:
   - https://docs.railway.app/
   - Check for recent platform changes or outages

---

## ✅ Success Criteria

Your Railway deployment is fixed when:

- ✅ **API service** is RUNNING and responds to `/health`
- ✅ **Worker service** is RUNNING and polls for flows
- ✅ Can trigger ETL flow and see data in database
- ✅ No build or deployment errors in Railway logs
- ✅ All environment variables properly linked with `${{}}` syntax

---

**Status**: Ready to deploy  
**Estimated Time**: 30 minutes (Railway configuration)  
**Priority**: CRITICAL - Blocks all production operations
