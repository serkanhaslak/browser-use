#!/bin/bash

# Railway startup script for browser-use (railpack optimized)
# Handles different deployment modes: api, mcp, ui, hybrid

set -e

# Virtual environment is already activated via railpack PATH configuration
# No need to explicitly activate

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