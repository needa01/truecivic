# 🚂 Railway Frontend Deployment Guide

## 📋 Overview

This guide walks you through deploying the TrueCivic Next.js frontend to Railway.

## 🗂️ Configuration Files Created

1. **`railway.toml`** - Railway-specific build and deployment configuration
2. **`nixpacks.toml`** - Nixpacks build configuration (Node.js 20)
3. **`.env.production.template`** - Template for production environment variables

## 🚀 Deployment Steps

### Step 1: Create New Railway Service

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Select your project (or create a new one)
3. Click **"New Service"**
4. Select **"GitHub Repo"**
5. Choose your `truecivic` repository

### Step 2: Configure Service Settings

In the Railway service settings:

#### Build Configuration
- **Root Directory**: `/frontend`
- **Build Command**: Auto-detected from `railway.toml`
- **Start Command**: Auto-detected from `railway.toml`
- **Builder**: Nixpacks (auto-detected)

#### Environment Variables
Add these variables in Railway Dashboard → Settings → Variables:

```bash
# Required: Production API URL (update with your actual Railway API service URL)
NEXT_PUBLIC_API_URL=https://your-api-service.up.railway.app/api/v1/ca

# Optional but recommended
NODE_ENV=production
```

**To get your API service URL:**
1. Go to your Railway dashboard
2. Find your API service (FastAPI service)
3. Go to Settings → Networking → Public Domain
4. Copy the URL and append `/api/v1/ca`

### Step 3: Configure Networking

1. In Railway service → Settings → Networking
2. Click **"Generate Domain"** or add a custom domain
3. Note the frontend URL for testing

### Step 4: Deploy

1. Click **"Deploy"** or push to your GitHub repository
2. Railway will automatically:
   - Clone your repo
   - Navigate to `/frontend` directory
   - Run `npm install`
   - Run `npm run build`
   - Start the production server with `npm run start`

### Step 5: Verify Deployment

1. Open the generated Railway URL in your browser
2. Check that:
   - ✅ Homepage loads
   - ✅ Stats display correctly (Bills: 99, etc.)
   - ✅ Recent bills section shows data
   - ✅ No console errors
   - ✅ API requests succeed

## 🔧 Configuration Details

### railway.toml

```toml
[build]
builder = "NIXPACKS"
buildCommand = "npm install && npm run build"

[deploy]
startCommand = "npm run start"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

[healthcheck]
path = "/"
timeout = 100
interval = 30
```

- **Builder**: Uses Nixpacks for reliable Node.js builds
- **Build**: Installs dependencies and builds Next.js
- **Deploy**: Starts production server on port 3000
- **Restart Policy**: Automatically restarts on failure (max 10 retries)
- **Health Check**: Pings `/` every 30 seconds

### nixpacks.toml

```toml
[phases.setup]
nixPkgs = ["nodejs_20"]

[phases.install]
cmds = ["npm install"]

[phases.build]
cmds = ["npm run build"]

[start]
cmd = "npm run start"

[variables]
NODE_ENV = "production"
```

- **Node Version**: Uses Node.js 20 (latest LTS)
- **Phases**: Explicit setup → install → build → start sequence
- **Environment**: Sets NODE_ENV to production

## 🌍 Environment Variables

### Development (Local)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1/ca
```

### Production (Railway)
```bash
NEXT_PUBLIC_API_URL=https://your-api-service.up.railway.app/api/v1/ca
NODE_ENV=production
```

**Important:** The `NEXT_PUBLIC_` prefix makes the variable available in the browser. Without it, the API client won't be able to connect.

## 🔍 Troubleshooting

### Build Fails
- Check Railway build logs for errors
- Verify `/frontend` root directory is set correctly
- Ensure `package.json` has all required scripts

### Runtime Errors
- Check Railway service logs
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Ensure API service is running and accessible

### API Connection Issues
- Verify API service has a public domain
- Check CORS settings in FastAPI
- Ensure `NEXT_PUBLIC_API_URL` includes `/api/v1/ca` path

### Health Check Failures
- Verify app is listening on port 3000
- Check that homepage (`/`) loads successfully
- Increase health check timeout if needed

## 📊 Expected Performance

Based on local production build:

- **Bundle Size**: 50.3 kB (page), 142 kB (First Load JS)
- **Build Time**: ~10-30 seconds on Railway
- **Start Time**: <1 second
- **Cold Start**: ~2-3 seconds
- **Response Time**: <100ms (homepage)

## 🎯 Next Steps After Deployment

1. ✅ Verify frontend is accessible at Railway URL
2. ✅ Test API connectivity (stats should show real data)
3. ✅ Configure custom domain (optional)
4. 🔄 Fix Railway worker service (to populate production database)
5. 🔄 Build remaining pages (bills list, bill detail, etc.)
6. 🔄 Implement node-based visualization

## 🔗 Related Documentation

- [Railway Documentation](https://docs.railway.app/)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [Nixpacks Documentation](https://nixpacks.com/docs)

## 📝 Notes

- Railway automatically detects `railway.toml` and `nixpacks.toml`
- Root directory setting is crucial - must be `/frontend`
- Environment variables must be set in Railway dashboard (not in `.env.production`)
- Production build is already validated locally (✅ successful)
- Static prerendering works (homepage is pre-rendered at build time)

---

**Status**: ✅ Configuration files ready for deployment
**Next Action**: Create Railway service and deploy
