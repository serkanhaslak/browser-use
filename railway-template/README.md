# 🤖 Browser-Use Railway Template (Railpack Optimized)

Deploy [browser-use](https://github.com/browser-use/browser-use) on Railway with **railpack** - Railway's next-generation build system! This template provides a production-ready deployment with **77% smaller Python images** and optimized caching.

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/your-template-id)

## ⚡ **Railpack Advantages**

- **🏎️ 77% Smaller Images**: Optimized Python builds with BuildKit
- **⚡ Faster Deploys**: Better caching and layer optimization  
- **🔧 Granular Control**: Fine-tuned dependency management
- **🚀 Modern Architecture**: Go-based build system with advanced features

## 🚀 Quick Start

1. Click the "Deploy on Railway" button above
2. Set your LLM API key (OpenAI, Anthropic, or Google)
3. Choose your deployment mode
4. Deploy and start automating!

## 🎯 Deployment Modes

This template supports multiple deployment patterns:

### 🌐 API Mode (Default)
- **FastAPI web service** with REST endpoints
- Perfect for programmatic access and integrations
- Swagger UI available at `/docs`
- Health checks at `/health`

### 🎨 UI Mode  
- **Streamlit web interface** for interactive use
- User-friendly task input and execution
- Real-time status updates and history
- Great for non-technical users

### 🔌 MCP Mode
- **Model Context Protocol server** for Claude Desktop integration
- Exposes browser automation as tools
- Perfect for AI assistant workflows

### 🚀 Hybrid Mode
- **Combined API + UI** deployment
- API on port 8000, UI on port 8001
- Best of both worlds

## ⚙️ Environment Variables

### Required (choose one)
- `OPENAI_API_KEY` - OpenAI API key for GPT models
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude models  
- `GOOGLE_API_KEY` - Google API key for Gemini models

### Optional Configuration
- `DEPLOYMENT_MODE` - `api|ui|mcp|hybrid` (default: `api`)
- `DEFAULT_LLM_PROVIDER` - `openai|anthropic|google` (default: `openai`)
- `DEFAULT_MODEL` - Model name (default: `gpt-4o-mini`)
- `MAX_CONCURRENT_SESSIONS` - Max parallel browser sessions (default: `3`)
- `BROWSER_TIMEOUT` - Session timeout in seconds (default: `300`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `ENABLE_TELEMETRY` - Enable browser-use telemetry (default: `false`)

## 📚 API Usage

### Create Task
```bash
curl -X POST "https://your-app.railway.app/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Go to Google and search for Python tutorials",
    "max_steps": 10
  }'
```

### Check Status
```bash
curl "https://your-app.railway.app/tasks/{session_id}"
```

### Cancel Task
```bash
curl -X DELETE "https://your-app.railway.app/tasks/{session_id}"
```

## 🔧 MCP Integration

To use with Claude Desktop, add this to your MCP configuration:

```json
{
  "mcpServers": {
    "browser-use": {
      "command": "curl",
      "args": [
        "-X", "POST",
        "https://your-app.railway.app/mcp",
        "-H", "Content-Type: application/json"
      ],
      "env": {
        "DEPLOYMENT_MODE": "mcp"
      }
    }
  }
}
```

## 🔧 **Railpack Configuration** 

This template uses `railpack.json` for optimized builds:

```json
{
  "provider": "python",
  "buildAptPackages": ["curl", "wget", "gnupg2", ...],
  "steps": {
    "setup": { "commands": ["Install uv package manager"] },
    "dependencies": { "commands": ["uv sync --all-extras"] },
    "browsers": { "commands": ["playwright install chromium"] },
    "application": { "deployOutputs": [...] }
  },
  "deploy": {
    "aptPackages": ["Browser runtime dependencies"],
    "startCommand": "./railway-template/startup.sh"
  }
}
```

**Key Benefits**:
- **Multi-step builds** with optimized caching
- **System packages** separated by build/runtime needs
- **uv integration** for fast Python dependency management
- **Browser binaries** efficiently cached and deployed

## 🛠️ Local Development

1. Clone the repository:
```bash
git clone https://github.com/browser-use/browser-use.git
cd browser-use/railway-template
```

2. Install dependencies:
```bash
uv venv --python 3.12
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv sync --all-extras --dev
```

3. Install Playwright browsers:
```bash
playwright install chromium --with-deps
```

4. Set environment variables:
```bash
export OPENAI_API_KEY="your-api-key"
export DEPLOYMENT_MODE="api"
```

5. Run locally:
```bash
./startup.sh
```

## 📋 Supported LLM Models

### OpenAI
- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

### Anthropic
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- `claude-3-opus-20240229`

### Google
- `gemini-1.5-pro`
- `gemini-1.5-flash`
- `gemini-pro`

## 🔒 Security Notes

- API keys are stored as Railway environment variables (encrypted)
- Browser runs in sandboxed environment
- Non-root user execution
- Resource limits prevent abuse
- No persistent data storage by default

## 📊 Resource Usage

**Recommended Railway Plan:** Hobby ($5/month) or Pro ($20/month)

- **Memory:** 1-2GB (browser instances are memory-intensive)
- **CPU:** 1-2 vCPUs (AI model calls and browser automation)
- **Storage:** Minimal (unless storing browser profiles)
- **Network:** Outbound for LLM APIs, inbound for web interface

## 🐛 Troubleshooting

### Common Issues

**"No LLM API key configured"**
- Ensure you've set at least one API key environment variable
- Check that the key is valid and has sufficient credits

**"Maximum concurrent sessions reached"**
- Increase `MAX_CONCURRENT_SESSIONS` environment variable
- Consider upgrading Railway plan for more resources

**Browser timeout errors**
- Increase `BROWSER_TIMEOUT` environment variable
- Complex tasks may need longer timeouts

**Memory issues**
- Reduce `MAX_CONCURRENT_SESSIONS`
- Upgrade to Railway Pro plan for more memory

### Logs and Debugging

View logs in Railway dashboard:
1. Go to your Railway project
2. Click on your service
3. Open the "Logs" tab
4. Set log level to `DEBUG` if needed

## 🤝 Contributing

This template is part of the browser-use project. Contributions welcome!

1. Fork the repository
2. Create your feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

MIT License - see the [LICENSE](https://github.com/browser-use/browser-use/blob/main/LICENSE) file for details.

## 🆘 Support

- 📖 [Browser-Use Documentation](https://docs.browser-use.com)
- 💬 [Discord Community](https://link.browser-use.com/discord)
- 🐛 [GitHub Issues](https://github.com/browser-use/browser-use/issues)
- 🚂 [Railway Support](https://help.railway.app)

---

Made with ❤️ by the Browser-Use community | Deployed on [Railway](https://railway.app)