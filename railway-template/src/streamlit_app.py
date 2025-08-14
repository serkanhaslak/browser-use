"""
Streamlit web UI for browser-use on Railway.

Provides an interactive web interface for browser automation tasks.
"""

import asyncio
import os
import sys
import time
from typing import Optional

import streamlit as st

# Add browser-use to path (railpack optimized)  
sys.path.insert(0, os.getcwd())

from browser_use import Agent
from browser_use.browser import BrowserSession
from browser_use.controller.service import Controller
from browser_use.agent.views import AgentSettings

# Configure Streamlit
st.set_page_config(
    page_title="Browser-Use on Railway",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Handle Windows event loop
if os.name == 'nt':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def get_llm(provider: str, model: str, temperature: float = 0.0):
    """Get LLM instance based on provider."""
    try:
        if provider == 'openai':
            from browser_use.llm import ChatOpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                st.error('❌ OPENAI_API_KEY environment variable is not set')
                st.stop()
            return ChatOpenAI(model=model, temperature=temperature)
        
        elif provider == 'anthropic':
            from browser_use.llm import ChatAnthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                st.error('❌ ANTHROPIC_API_KEY environment variable is not set')
                st.stop()
            return ChatAnthropic(model=model, temperature=temperature)
        
        elif provider == 'google':
            from browser_use.llm import ChatGoogle
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                st.error('❌ GOOGLE_API_KEY environment variable is not set')
                st.stop()
            return ChatGoogle(model=model, temperature=temperature)
        
        else:
            st.error(f'❌ Unsupported provider: {provider}')
            st.stop()
            
    except ImportError as e:
        st.error(f'❌ Error importing LLM provider: {e}')
        st.stop()

def initialize_session_state():
    """Initialize Streamlit session state."""
    if 'agent_running' not in st.session_state:
        st.session_state.agent_running = False
    if 'browser_session' not in st.session_state:
        st.session_state.browser_session = None
    if 'execution_history' not in st.session_state:
        st.session_state.execution_history = []

def main():
    initialize_session_state()
    
    # Main title
    st.title("🤖 Browser-Use on Railway")
    st.markdown("AI-powered browser automation deployed on Railway")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # LLM Configuration
        st.subheader("🧠 LLM Settings")
        provider = st.selectbox(
            "Provider",
            options=['google', 'openai', 'anthropic'],
            index=0,
            help="Select your LLM provider"
        )
        
        # Model selection based on provider
        if provider == 'google':
            model_options = ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro', 'gemini-1.5-flash-8b']
            default_model = 'gemini-1.5-flash'
        elif provider == 'openai':
            model_options = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo']
            default_model = 'gpt-4o-mini'
        else:  # anthropic
            model_options = ['claude-3-5-sonnet-20241022', 'claude-3-5-haiku-20241022', 'claude-3-opus-20240229']
            default_model = 'claude-3-5-sonnet-20241022'
        
        model = st.selectbox("Model", options=model_options, index=0)
        temperature = st.slider("Temperature", 0.0, 1.0, 0.0, 0.1)
        
        # Browser Settings
        st.subheader("🌐 Browser Settings")
        headless = st.checkbox("Headless Mode", value=True, help="Run browser in headless mode (no GUI)")
        use_vision = st.checkbox("Enable Vision", value=True, help="Allow agent to see and analyze page content")
        max_steps = st.number_input("Max Steps", min_value=1, max_value=50, value=10, help="Maximum number of steps for task execution")
        
        # Environment info
        st.subheader("📊 Environment")
        st.info(f"Platform: Railway")
        
        # Check API keys
        api_keys = {
            'openai': bool(os.getenv('OPENAI_API_KEY')),
            'anthropic': bool(os.getenv('ANTHROPIC_API_KEY')),
            'google': bool(os.getenv('GOOGLE_API_KEY'))
        }
        
        st.write("API Keys Status:")
        for key, available in api_keys.items():
            status = "✅" if available else "❌"
            st.write(f"{status} {key.upper()}")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🎯 Task Input")
        
        # Pre-defined example tasks
        example_tasks = [
            "Go to Google and search for 'Python web scraping'",
            "Visit Reddit and find the top post in r/python",
            "Navigate to GitHub and search for browser automation repositories",
            "Go to Wikipedia and find information about artificial intelligence",
            "Visit a news website and summarize the top headlines"
        ]
        
        selected_example = st.selectbox(
            "Example Tasks (optional)",
            options=[""] + example_tasks,
            help="Select an example task or write your own"
        )
        
        # Task input
        if selected_example:
            task = st.text_area(
                "Task Description",
                value=selected_example,
                height=100,
                help="Describe what you want the browser agent to do"
            )
        else:
            task = st.text_area(
                "Task Description",
                placeholder="Enter your task here...",
                height=100,
                help="Describe what you want the browser agent to do"
            )
        
        # Execution button
        if st.button("🚀 Execute Task", disabled=st.session_state.agent_running or not task.strip()):
            if not api_keys[provider]:
                st.error(f"❌ {provider.upper()}_API_KEY environment variable is not set")
            else:
                execute_task(task, provider, model, temperature, headless, use_vision, max_steps)
    
    with col2:
        st.subheader("📈 Status")
        
        if st.session_state.agent_running:
            st.warning("🔄 Agent is running...")
            if st.button("🛑 Stop Agent"):
                stop_agent()
        else:
            st.success("✅ Ready")
        
        # System stats
        st.subheader("💾 System Info")
        st.metric("Active Sessions", len(st.session_state.execution_history))
        
    # Execution history
    if st.session_state.execution_history:
        st.subheader("📋 Execution History")
        
        for i, execution in enumerate(reversed(st.session_state.execution_history)):
            with st.expander(f"Task {len(st.session_state.execution_history) - i}: {execution['task'][:50]}..."):
                st.write(f"**Status:** {execution['status']}")
                st.write(f"**Started:** {execution['start_time']}")
                if execution.get('end_time'):
                    st.write(f"**Completed:** {execution['end_time']}")
                if execution.get('result'):
                    st.write(f"**Result:** {execution['result']}")
                if execution.get('error'):
                    st.error(f"**Error:** {execution['error']}")

def execute_task(task: str, provider: str, model: str, temperature: float, headless: bool, use_vision: bool, max_steps: int):
    """Execute the browser automation task."""
    st.session_state.agent_running = True
    
    # Add to execution history
    execution = {
        'task': task,
        'status': 'running',
        'start_time': time.strftime('%Y-%m-%d %H:%M:%S'),
        'end_time': None,
        'result': None,
        'error': None
    }
    st.session_state.execution_history.append(execution)
    
    try:
        with st.spinner('🔄 Initializing agent...'):
            # Get LLM
            llm = get_llm(provider, model, temperature)
            
            # Initialize browser session
            browser_session = BrowserSession(headless=headless)
            st.session_state.browser_session = browser_session
            
            # Initialize controller
            controller = Controller()
            
            # Create agent
            agent = Agent(
                task=task,
                llm=llm,
                controller=controller,
                browser_session=browser_session,
                settings=AgentSettings(
                    use_vision=use_vision,
                    max_actions_per_step=1
                )
            )
        
        with st.spinner(f'🤖 Executing task (max {max_steps} steps)...'):
            # Run the agent
            history = asyncio.run(agent.run(max_steps=max_steps))
            
            # Get final result
            final_result = history.final_result() if history else "Task completed"
            
            # Update execution record
            execution['status'] = 'completed'
            execution['end_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
            execution['result'] = final_result
            
            st.success(f"✅ Task completed successfully!")
            st.write("**Result:**")
            st.write(final_result)
            
    except Exception as e:
        # Update execution record
        execution['status'] = 'error'
        execution['end_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        execution['error'] = str(e)
        
        st.error(f"❌ Error: {e}")
    
    finally:
        st.session_state.agent_running = False
        # Clean up browser session
        if st.session_state.browser_session:
            try:
                asyncio.run(st.session_state.browser_session.kill())
            except:
                pass
            st.session_state.browser_session = None

def stop_agent():
    """Stop the running agent."""
    st.session_state.agent_running = False
    if st.session_state.browser_session:
        try:
            asyncio.run(st.session_state.browser_session.kill())
        except:
            pass
        st.session_state.browser_session = None
    st.success("Agent stopped")

if __name__ == "__main__":
    main()