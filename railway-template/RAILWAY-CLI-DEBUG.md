# 🛠️ Railway CLI Debugging Guide

Debug and fix the VOLUME keyword error using Railway CLI.

## 🚨 **Quick Fix Commands**

```bash
# 1. Connect to your Railway project
railway login
railway link --project pg --service browser-use

# 2. Check current build configuration
railway status
railway logs --tail

# 3. Force railpack builder (if not set)
railway variables set RAILWAY_BUILDER=RAILPACK

# 4. Redeploy with railpack
railway up --detach
```

## 🔍 **Debug the Issue**

### Check Build Configuration
```bash
# View current service settings
railway service

# Check environment variables
railway variables

# View build logs
railway logs --filter build

# Check for Dockerfile detection
railway logs --filter "Dockerfile detected"
```

### Verify Railpack Usage
```bash
# Should show "RAILPACK" not "DOCKERFILE"
railway service --json | grep -i builder

# If it shows DOCKERFILE, fix it:
railway service set --builder RAILPACK
```

## 🎯 **Root Cause Analysis**

The error occurs because:

1. **Railway detects Dockerfile first**: Original browser-use Dockerfiles contain `VOLUME` 
2. **Railpack not prioritized**: Railway defaults to Docker if Dockerfile exists
3. **Build context**: Railway builds from wrong directory

## ✅ **Complete Fix Process**

### Step 1: Verify Project Structure
```bash
# Check you're in the right directory
pwd  # Should end with /railway-template

# List files - should see railpack.json
ls -la
# Should show:
# - railpack.json ✅
# - railway.json ✅  
# - .dockerignore ✅
```

### Step 2: Force Railpack Builder
```bash
# Set builder explicitly
railway service set --builder RAILPACK

# Verify it's set
railway service --json | grep builder
# Should show: "builder": "RAILPACK"
```

### Step 3: Deploy from Railway Template Directory
```bash
# Make sure you're in railway-template/
cd railway-template/

# Deploy from here (not root browser-use directory)
railway up --detach

# Watch build logs
railway logs --tail
```

### Step 4: Alternative - Use Railway Dashboard
1. Go to Railway dashboard
2. Select project "pg" → service "browser-use"
3. Settings → Build → Change builder to "RAILPACK"
4. Redeploy

## 🐛 **Common Issues & Solutions**

### Issue: "Still detecting Dockerfile"
**Solution**: Deploy from `railway-template/` directory, not root
```bash
cd railway-template/
railway up
```

### Issue: "Builder not changing"
**Solution**: Force rebuild with new builder
```bash
railway service set --builder RAILPACK
railway redeploy
```

### Issue: "railpack.json not found"
**Solution**: Ensure you're in the right directory
```bash
ls railpack.json  # Should exist
railway up --source .
```

### Issue: "Volume mount failing"
**Solution**: Railway volumes are separate from build process
```bash
# Volume is added via dashboard, not configuration files
# Your railpack.json doesn't need volume configuration
```

## 📊 **Success Indicators**

You'll know it's working when logs show:
```
✅ Using railpack builder
✅ Analyzing project with railpack
✅ Installing uv package manager
✅ Creating virtual environment
✅ Installing playwright dependencies
✅ Install Chromium browser
✅ Deploy successful
```

## 🚀 **Deployment Verification**

```bash
# Check service status
railway status

# Test health endpoint
curl https://browser-use-production.up.railway.app/health

# View environment variables
railway variables list

# Check volume attachment (if added)
railway volumes list
```

## 💡 **Pro Tips**

1. **Always deploy from `railway-template/`** - not the root browser-use directory
2. **Use railpack builder explicitly** - don't rely on auto-detection  
3. **Check build logs** - they show exactly what Railway is doing
4. **Railway volumes are separate** - added via dashboard, not code

Your railpack configuration is correct - the issue is Railway picking up the wrong build context!