# 📁 Railway Volume Setup for Browser-Use

Since Railway bans the `VOLUME` keyword in Dockerfiles, we use Railway's managed volumes for persistent storage.

## 🚀 **Quick Setup**

### 1. Deploy the Service First
Deploy browser-use using the railpack template - it will work without volumes initially.

### 2. Add Railway Volume (Optional)
If you need persistent browser profiles or file storage:

1. **Go to Railway Dashboard**
2. **Click "Add Service" → "Volume"**
3. **Configure Volume:**
   - **Name**: `browser-data`
   - **Size**: `5GB` (adjust as needed)
   - **Mount Path**: `/data`

### 3. Attach Volume to Service
1. **Select your browser-use service**
2. **Go to "Volumes" tab** 
3. **Click "Attach Volume"**
4. **Select the volume you created**

## 📂 **Directory Structure**

With Railway volume mounted at `/data`:

```
/data/
├── profiles/           # Browser profiles (persistent)
│   ├── default/       # Default profile
│   └── user-123/      # User-specific profiles
├── downloads/         # Downloaded files
├── screenshots/       # Generated screenshots  
├── logs/             # Application logs
└── cache/            # Browser cache
```

## 🔧 **Configuration**

The railpack template automatically creates cache directories:
- `/tmp/browser-profiles` - Temporary profiles (no volume needed)
- `/app/.cache` - Application cache
- Browser data stored in `/data` if volume is attached

## 🎯 **When to Use Volumes**

### ✅ **Use Railway Volume When:**
- Storing user browser profiles permanently
- Saving downloaded files between deployments
- Keeping browser cache for performance
- Running production workloads

### ❌ **Skip Volume When:**
- Just testing or development
- Stateless automation tasks
- Using fresh browser sessions each time
- Cost optimization (volumes add monthly cost)

## 💰 **Cost Considerations**

Railway Volume pricing:
- **$0.25/GB/month** for persistent storage
- **5GB volume** = ~$1.25/month
- **10GB volume** = ~$2.50/month

For most use cases, you can start without a volume and add it later if needed.

## 🛠️ **Environment Variables**

The template includes these defaults:
```bash
# Google API (your key)
GOOGLE_API_KEY="AIzaSyDAnXe4lJmUiMrS6usmUnfWxpanmkNKYcY"

# Telemetry and logging (your settings)
ANONYMIZED_TELEMETRY="true"
BROWSER_USE_LOGGING_LEVEL="info" 
BROWSER_USE_CALCULATE_COST="true"

# Defaults from railpack.json
DEFAULT_LLM_PROVIDER="google"
DEFAULT_MODEL="gemini-1.5-flash"
```

## 🚀 **Deployment Steps**

1. **Deploy without volume first**:
   ```bash
   git clone browser-use
   cd railway-template  
   # Deploy to Railway - will work immediately
   ```

2. **Add volume later if needed**:
   ```bash
   # In Railway dashboard:
   # Services → Add → Volume → Configure → Attach
   ```

3. **Access your service**:
   ```bash
   # Your service will be available at:
   # https://your-service-name.railway.app
   ```

Railway's volume system is much more reliable and manageable than Docker volumes, with automatic backups and scaling capabilities!