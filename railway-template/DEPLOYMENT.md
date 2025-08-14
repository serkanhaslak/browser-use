# 🚂 Railway Deployment Guide for Browser-Use (Railpack Optimized)

Complete guide for deploying browser-use on Railway using **railpack** - Railway's next-generation build system with **77% smaller Python images** and advanced BuildKit optimization.

## 📋 Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **LLM API Key**: At least one of:
   - OpenAI API key from [platform.openai.com](https://platform.openai.com)
   - Anthropic API key from [console.anthropic.com](https://console.anthropic.com)
   - Google API key from [aistudio.google.com](https://aistudio.google.com)

## ⚡ **Why Railpack?**

This template uses **railpack**, Railway's modern build system (launched March 2025) that replaces traditional Docker builds with significant optimizations:

### 🏆 **Performance Benefits**
- **77% smaller Python images** compared to traditional builds
- **Faster deployments** with BuildKit layer optimization  
- **Better caching** with sharable layers across environments
- **Granular versioning** support for exact package versions

### 🔧 **Technical Advantages**
- **Multi-step builds** with optimized dependency installation
- **System package separation** between build-time and runtime
- **uv integration** for ultra-fast Python package management
- **Browser binary caching** for efficient Playwright deployments

### 📁 **Configuration Files**
- `railway.json` - Railway service configuration with railpack builder
- `railpack.json` - Build optimization with steps, packages, and deployment settings

## 🚀 One-Click Deployment

1. **Click Deploy Button**
   ```
   [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)
   ```

2. **Configure Environment Variables**
   - Set your LLM API key (required)
   - Choose deployment mode (optional)
   - Adjust other settings as needed

3. **Deploy & Access**
   - Railway will build and deploy automatically
   - Access your service at the provided Railway URL

## ⚙️ Configuration Reference

### Core Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | * | - | OpenAI API key for GPT models |
| `ANTHROPIC_API_KEY` | * | - | Anthropic API key for Claude models |
| `GOOGLE_API_KEY` | * | - | Google API key for Gemini models |
| `DEPLOYMENT_MODE` | No | `api` | Service mode: `api`, `ui`, `mcp`, `hybrid` |

*\* At least one API key is required*

### Advanced Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DEFAULT_LLM_PROVIDER` | `openai` | Default provider: `openai`, `anthropic`, `google` |
| `DEFAULT_MODEL` | `gpt-4o-mini` | Default model name |
| `MAX_CONCURRENT_SESSIONS` | `3` | Maximum parallel browser sessions |
| `BROWSER_TIMEOUT` | `300` | Browser session timeout (seconds) |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ENABLE_TELEMETRY` | `false` | Enable browser-use usage telemetry |

## 🎯 Deployment Modes

### 1. API Mode (`DEPLOYMENT_MODE=api`)

**Best for**: Programmatic access, integrations, automation

**Features**:
- FastAPI web service with REST endpoints
- Swagger UI at `/docs`
- Health checks at `/health`
- Session management and monitoring

**Endpoints**:
- `POST /tasks` - Create new automation task
- `GET /tasks/{session_id}` - Check task status
- `DELETE /tasks/{session_id}` - Cancel running task
- `GET /health` - Service health check
- `GET /docs` - Interactive API documentation

**Example Usage**:
```bash
# Create task
curl -X POST "https://your-app.railway.app/tasks" \
  -H "Content-Type: application/json" \
  -d '{"task": "Search Google for Python tutorials", "max_steps": 5}'

# Check status
curl "https://your-app.railway.app/tasks/session-id-here"
```

### 2. UI Mode (`DEPLOYMENT_MODE=ui`)

**Best for**: Interactive use, non-technical users, demonstrations

**Features**:
- Streamlit web interface
- Real-time task execution
- Visual status updates
- Execution history
- Pre-defined example tasks

**Access**: Navigate to your Railway URL in a web browser

### 3. MCP Mode (`DEPLOYMENT_MODE=mcp`)

**Best for**: Integration with Claude Desktop, AI assistant workflows

**Features**:
- Model Context Protocol server
- Exposes browser automation as tools
- Compatible with Claude Desktop and other MCP clients

**Claude Desktop Configuration**:
```json
{
  "mcpServers": {
    "browser-use": {
      "command": "curl",
      "args": [
        "-X", "POST", 
        "https://your-app.railway.app/mcp",
        "-H", "Content-Type: application/json"
      ]
    }
  }
}
```

### 4. Hybrid Mode (`DEPLOYMENT_MODE=hybrid`)

**Best for**: Maximum flexibility, development, testing

**Features**:
- API server on port 8000
- Web UI on port 8001
- Both interfaces available simultaneously

## 🔧 Manual Deployment

For advanced users who want more control:

### 1. Fork Repository
```bash
git clone https://github.com/browser-use/browser-use.git
cd browser-use
```

### 2. Create Railway Project
1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your forked repository
5. Set root directory to `railway-template`

### 3. Configure Build
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "railway-template/Dockerfile"
  }
}
```

### 4. Set Environment Variables
Add your API keys and configuration in Railway dashboard

### 5. Deploy
Railway will automatically build and deploy

## 📊 Resource Planning

### Railway Plan Recommendations

| Plan | Memory | CPU | Concurrent Sessions | Best For |
|------|--------|-----|-------------------|----------|
| **Hobby** ($5/month) | 512MB | 1 vCPU | 1-2 | Light usage, testing |
| **Pro** ($20/month) | 8GB | 8 vCPU | 3-5 | Production, multiple users |
| **Team** ($100/month) | 32GB | 32 vCPU | 10+ | Heavy automation, enterprise |

### Resource Usage Tips

- **Memory**: Browser instances use ~200-500MB each
- **CPU**: AI model calls and browser automation are CPU-intensive
- **Timeout**: Increase for complex, long-running tasks
- **Sessions**: Limit concurrent sessions based on available resources

## 🔒 Security Best Practices

### API Key Management
- Store API keys as Railway environment variables (encrypted)
- Never commit API keys to version control
- Rotate API keys regularly
- Monitor API usage and costs

### Access Control
- Use Railway's built-in authentication if needed
- Consider adding API authentication for production use
- Monitor logs for suspicious activity
- Set resource limits to prevent abuse

### Network Security
- Railway provides HTTPS by default
- Browser runs in sandboxed container
- No persistent data storage by default
- Outbound connections only to LLM APIs

## 🐛 Troubleshooting

### Common Issues

#### "No LLM API key configured"
**Solution**: Set the appropriate environment variable:
- `OPENAI_API_KEY` for OpenAI models
- `ANTHROPIC_API_KEY` for Anthropic models  
- `GOOGLE_API_KEY` for Google models

#### "Maximum concurrent sessions reached"
**Solutions**:
1. Increase `MAX_CONCURRENT_SESSIONS` environment variable
2. Upgrade Railway plan for more resources
3. Optimize task complexity to reduce execution time

#### "Browser timeout errors"
**Solutions**:
1. Increase `BROWSER_TIMEOUT` environment variable
2. Break complex tasks into smaller steps
3. Optimize task prompts for efficiency

#### "Out of memory errors"
**Solutions**:
1. Reduce `MAX_CONCURRENT_SESSIONS`
2. Upgrade Railway plan
3. Monitor memory usage in Railway dashboard

#### "Build failures"
**Solutions**:
1. Check build logs in Railway dashboard
2. Ensure all dependencies are properly specified
3. Verify Dockerfile syntax
4. Check for system dependency issues

### Debugging Steps

1. **Check Railway Logs**:
   - Go to Railway dashboard
   - Open your service
   - Click "Logs" tab
   - Look for error messages

2. **Verify Environment Variables**:
   - Check all required variables are set
   - Verify API keys are valid
   - Test API keys independently

3. **Test Health Endpoint**:
   ```bash
   curl https://your-app.railway.app/health
   ```

4. **Monitor Resource Usage**:
   - Check memory and CPU usage in Railway dashboard
   - Adjust limits if necessary

5. **Enable Debug Logging**:
   ```
   LOG_LEVEL=DEBUG
   ```

## 🚀 Performance Optimization

### For Better Performance

1. **Choose Appropriate Models**:
   - Use smaller, faster models for simple tasks
   - Reserve larger models for complex reasoning

2. **Optimize Task Prompts**:
   - Be specific and clear
   - Break complex tasks into steps
   - Use examples in prompts

3. **Resource Management**:
   - Monitor concurrent sessions
   - Set appropriate timeouts
   - Use headless mode for better performance

4. **Railway Optimization**:
   - Use appropriate plan for your needs
   - Monitor resource usage
   - Consider auto-scaling settings

### Monitoring and Alerts

1. **Set up Railway Alerts**:
   - Memory usage alerts
   - CPU usage alerts
   - Deployment failure alerts

2. **Monitor API Costs**:
   - Track LLM API usage
   - Set spending limits
   - Monitor token consumption

3. **Health Checks**:
   - Use built-in health endpoints
   - Set up external monitoring
   - Configure automated restarts

## 📈 Scaling Considerations

### Vertical Scaling
- Upgrade Railway plan for more resources
- Increase memory for more concurrent sessions
- Add CPU for faster processing

### Horizontal Scaling
- Deploy multiple instances
- Use load balancer
- Implement session affinity

### Cost Optimization
- Monitor resource usage
- Use sleep mode for development
- Optimize model selection
- Implement caching where possible

## 🤝 Support and Community

- 📖 [Browser-Use Documentation](https://docs.browser-use.com)
- 💬 [Discord Community](https://link.browser-use.com/discord)
- 🐛 [GitHub Issues](https://github.com/browser-use/browser-use/issues)
- 🚂 [Railway Support](https://help.railway.app)
- 📧 [Railway Community](https://discord.gg/railway)

---

Happy automating! 🤖✨