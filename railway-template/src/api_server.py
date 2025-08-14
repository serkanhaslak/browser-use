"""
FastAPI web service wrapper for browser-use deployment on Railway.

Provides REST API endpoints for browser automation tasks.
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

# Add browser-use to path (railpack optimized)
sys.path.insert(0, os.getcwd())

from browser_use import Agent, Controller
from browser_use.browser import BrowserSession, BrowserProfile
from browser_use.agent.views import AgentSettings


# Configuration from environment
DEFAULT_LLM_PROVIDER = os.getenv('DEFAULT_LLM_PROVIDER', 'openai')
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'gpt-4o-mini')
MAX_CONCURRENT_SESSIONS = int(os.getenv('MAX_CONCURRENT_SESSIONS', '3'))
BROWSER_TIMEOUT = int(os.getenv('BROWSER_TIMEOUT', '300'))

# Global session manager
active_sessions: Dict[str, Dict[str, Any]] = {}

# Request/Response models
class TaskRequest(BaseModel):
    task: str = Field(..., description="The task for the browser agent to perform")
    llm_provider: Optional[str] = Field(DEFAULT_LLM_PROVIDER, description="LLM provider: openai, anthropic, google")
    model: Optional[str] = Field(DEFAULT_MODEL, description="Model name")
    max_steps: Optional[int] = Field(10, description="Maximum steps for task execution")
    headless: Optional[bool] = Field(True, description="Run browser in headless mode")
    use_vision: Optional[bool] = Field(True, description="Enable vision capabilities")

class TaskResponse(BaseModel):
    session_id: str
    status: str
    message: str

class SessionStatus(BaseModel):
    session_id: str
    status: str
    current_step: int
    max_steps: int
    final_result: Optional[str] = None
    error: Optional[str] = None

def get_llm(provider: str, model: str):
    """Get LLM instance based on provider."""
    if provider == 'openai':
        from browser_use.llm import ChatOpenAI
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise HTTPException(status_code=400, detail="OPENAI_API_KEY not configured")
        return ChatOpenAI(model=model, temperature=0.0)
    
    elif provider == 'anthropic':
        from browser_use.llm import ChatAnthropic
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise HTTPException(status_code=400, detail="ANTHROPIC_API_KEY not configured")
        return ChatAnthropic(model=model, temperature=0.0)
    
    elif provider == 'google':
        from browser_use.llm import ChatGoogle
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise HTTPException(status_code=400, detail="GOOGLE_API_KEY not configured")
        return ChatGoogle(model=model, temperature=0.0)
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported LLM provider: {provider}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    yield
    # Cleanup: Close all active sessions
    for session_data in active_sessions.values():
        if 'browser' in session_data:
            try:
                await session_data['browser'].kill()
            except Exception as e:
                logging.error(f"Error closing browser session: {e}")

# Create FastAPI app
app = FastAPI(
    title="Browser-Use API",
    description="AI-powered browser automation service deployed on Railway",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with basic UI."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Browser-Use API</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            code { background: #e0e0e0; padding: 2px 4px; border-radius: 3px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Browser-Use API</h1>
            <p>AI-powered browser automation service deployed on Railway</p>
            
            <h2>Available Endpoints:</h2>
            <div class="endpoint">
                <h3>POST /tasks</h3>
                <p>Create a new browser automation task</p>
                <p><strong>Body:</strong> <code>{"task": "your task description"}</code></p>
            </div>
            
            <div class="endpoint">
                <h3>GET /tasks/{session_id}</h3>
                <p>Get status of a running task</p>
            </div>
            
            <div class="endpoint">
                <h3>GET /health</h3>
                <p>Service health check</p>
            </div>
            
            <div class="endpoint">
                <h3>GET /docs</h3>
                <p>Interactive API documentation (Swagger UI)</p>
            </div>
            
            <p><a href="/docs">📚 View API Documentation</a></p>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway."""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "max_sessions": MAX_CONCURRENT_SESSIONS,
        "version": "1.0.0"
    }

@app.post("/tasks", response_model=TaskResponse)
async def create_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """Create and execute a browser automation task."""
    
    # Check session limit
    if len(active_sessions) >= MAX_CONCURRENT_SESSIONS:
        raise HTTPException(
            status_code=429, 
            detail=f"Maximum concurrent sessions ({MAX_CONCURRENT_SESSIONS}) reached"
        )
    
    session_id = str(uuid.uuid4())
    
    try:
        # Initialize LLM
        llm = get_llm(request.llm_provider, request.model)
        
        # Initialize browser session
        browser_session = BrowserSession(headless=request.headless)
        
        # Initialize controller
        controller = Controller()
        
        # Create agent
        agent = Agent(
            task=request.task,
            llm=llm,
            controller=controller,
            browser_session=browser_session,
            settings=AgentSettings(
                use_vision=request.use_vision,
                max_actions_per_step=1
            )
        )
        
        # Store session
        active_sessions[session_id] = {
            'agent': agent,
            'browser': browser_session,
            'status': 'running',
            'current_step': 0,
            'max_steps': request.max_steps,
            'final_result': None,
            'error': None
        }
        
        # Start task in background
        background_tasks.add_task(run_agent_task, session_id, request.max_steps)
        
        return TaskResponse(
            session_id=session_id,
            status="started",
            message=f"Task started with session ID: {session_id}"
        )
        
    except Exception as e:
        logging.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{session_id}", response_model=SessionStatus)
async def get_task_status(session_id: str):
    """Get the status of a running task."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = active_sessions[session_id]
    
    return SessionStatus(
        session_id=session_id,
        status=session_data['status'],
        current_step=session_data['current_step'],
        max_steps=session_data['max_steps'],
        final_result=session_data.get('final_result'),
        error=session_data.get('error')
    )

@app.delete("/tasks/{session_id}")
async def cancel_task(session_id: str):
    """Cancel a running task and clean up resources."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = active_sessions[session_id]
    
    try:
        # Close browser
        if 'browser' in session_data:
            await session_data['browser'].kill()
        
        # Remove from active sessions
        del active_sessions[session_id]
        
        return {"message": f"Task {session_id} cancelled successfully"}
        
    except Exception as e:
        logging.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_agent_task(session_id: str, max_steps: int):
    """Background task to run the agent."""
    session_data = active_sessions.get(session_id)
    if not session_data:
        return
    
    try:
        agent = session_data['agent']
        
        # Run the agent
        history = await agent.run(max_steps=max_steps)
        
        # Update session with results
        session_data['status'] = 'completed'
        session_data['final_result'] = history.final_result() if history else None
        session_data['current_step'] = max_steps
        
    except Exception as e:
        logging.error(f"Error running agent task {session_id}: {e}")
        session_data['status'] = 'error'
        session_data['error'] = str(e)
    
    finally:
        # Clean up after some time
        await asyncio.sleep(300)  # Keep results for 5 minutes
        if session_id in active_sessions:
            try:
                if 'browser' in session_data:
                    await session_data['browser'].kill()
                del active_sessions[session_id]
            except Exception as e:
                logging.error(f"Error cleaning up session {session_id}: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    
    uvicorn.run(app, host=args.host, port=args.port)