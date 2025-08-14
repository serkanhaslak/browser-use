#!/bin/bash

# Railway startup script for browser-use (railpack optimized)
# Handles different deployment modes: api, mcp, ui, hybrid

set -e

# Ensure virtual environment is activated (defensive)
if [ -f "/app/.venv/bin/activate" ]; then
    source /app/.venv/bin/activate
    echo "✅ Activated virtual environment"
else
    echo "⚠️  No virtual environment found, using system Python"
fi

# Verify critical dependencies
python -c "
import uvicorn, fastapi, streamlit, dotenv, psutil, redis, aioredis, bubus, markdownify, patchright
from pydantic_settings import BaseSettings
import PIL
" 2>/dev/null || {
    echo "❌ Missing dependencies detected, trying to install..."
    pip install fastapi uvicorn streamlit python-dotenv psutil redis aioredis pydantic-settings pillow bubus markdownify patchright playwright
}

# Default values
DEPLOYMENT_MODE=${DEPLOYMENT_MODE:-"api"}
PORT=${PORT:-8000}

echo "🚀 Starting browser-use in $DEPLOYMENT_MODE mode on port $PORT"

# Validate LLM configuration
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$GOOGLE_API_KEY" ]; then
    echo "⚠️  Warning: No LLM API keys provided. Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY"
fi

case $DEPLOYMENT_MODE in
    "api")
        echo "🌐 Starting FastAPI web service..."
        python ./src/api_server.py --port $PORT
        ;;
    "mcp")
        echo "🔌 Starting MCP server..."
        browser-use --mcp --port $PORT
        ;;
    "ui")
        echo "🎨 Starting Streamlit web UI..."
        streamlit run ./src/streamlit_app.py --server.port $PORT --server.address 0.0.0.0
        ;;
    "hybrid")
        echo "🚀 Starting hybrid mode (API + UI)..."
        # Run API server in background
        python ./src/api_server.py --port $PORT &
        # Run Streamlit on different port
        streamlit run ./src/streamlit_app.py --server.port $((PORT + 1)) --server.address 0.0.0.0 &
        # Wait for both processes
        wait
        ;;
    *)
        echo "❌ Invalid DEPLOYMENT_MODE: $DEPLOYMENT_MODE"
        echo "Valid modes: api, mcp, ui, hybrid"
        exit 1
        ;;
esac