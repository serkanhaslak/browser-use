# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Browser-Use is an async Python library (>= 3.11) that implements AI browser driver abilities using LLMs + Playwright. The library enables AI agents to autonomously control browsers and interact with web pages. The core mission is to make our library APIs ergonomic, intuitive, and hard to get wrong.

## Common Development Commands

### Testing Commands
```bash
# Run CI test suite (main test suite for CI)
uv run pytest -vxs tests/ci

# Run type checking
uv run pyright

# Run specific test
uv run pytest -vxs tests/ci/test_browser_session_start.py

# Run tests with pattern matching
uv run pytest -vxs tests/ci -k "browser_session"

# Run linting and formatting
ruff check
ruff format
```

### Development Setup
```bash
# Setup virtual environment (always use uv instead of pip)
uv venv --python 3.11
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uv sync

# Install with CLI extras for browser-use command
uv sync --extra cli

# Install all development dependencies
uv sync --dev
```

### Running Browser-Use
```bash
# Interactive CLI mode
browser-use

# Python script execution
python examples/simple.py

# Install and run via uvx (for MCP)
uvx browser-use[cli] --mcp
```

## High-Level Architecture

Browser-Use follows a modular, event-driven architecture with these core components:

### Agent (`browser_use/agent/`)
- **Agent service**: Main orchestrator that executes tasks by coordinating between browser, controller, and LLM
- **Message Manager**: Manages conversation history and agent state across steps  
- **System Prompts**: Configurable prompts that define agent behavior and capabilities
- **Views**: Pydantic models for agent inputs/outputs, history, and state management

### Browser (`browser_use/browser/`)
- **BrowserSession**: Primary interface for controlling Chromium via Playwright/Patchright
- **Watchdogs**: Specialized handlers for downloads, popups, security, crashes, storage state
- **CDP Integration**: Uses `cdp-use` library for low-level Chrome DevTools Protocol access
- **Event System**: Browser events (clicks, navigation, typing) flow through the bubus event bus

### Controller (`browser_use/controller/`)
- **Action Registry**: Central registry of all actions the agent can perform (click, type, navigate, etc.)
- **Action Execution**: Translates LLM decisions into browser automation commands
- **Custom Functions**: Extension point for adding domain-specific actions

### DOM Service (`browser_use/dom/`)
- **Enhanced DOM Extraction**: Processes page content into LLM-friendly representations
- **Element Detection**: Identifies clickable/interactable elements with coordinate mapping
- **Serialization**: Converts complex DOM trees into simplified, actionable formats

### LLM Integration (`browser_use/llm/`)
- **Multi-Provider Support**: OpenAI, Anthropic, Google, Groq, Azure, Ollama, DeepSeek
- **Structured Output**: Pydantic models ensure reliable action parsing from LLM responses
- **Token Management**: Cost tracking and optimization across different models

### MCP Integration (`browser_use/mcp/`)
- **Dual Role**: Can act as both MCP client and server
- **Server Mode**: Exposes browser automation as tools to Claude Desktop and other MCP clients
- **Client Mode**: Agents can connect to external MCP servers (filesystem, GitHub, etc.) for extended capabilities
- **Multi-Server**: Single agent can orchestrate multiple MCP servers simultaneously

### Key Patterns
- **Event-Driven**: Uses `bubus` event bus for loose coupling between components
- **Lazy Loading**: Heavy imports are deferred until actually needed (see `__init__.py`)  
- **Service/Views Pattern**: Business logic in `service.py`, data models in `views.py`
- **Async Throughout**: All major operations are async for performance
- **CDP + Playwright**: Combines high-level Playwright with low-level CDP for maximum control

## Code Style and Conventions

- Use async Python with modern typing (`str | None` vs `Optional[str]`)
- Use tabs for indentation, not spaces
- Pydantic v2 models for all data structures and validation
- Logging methods prefixed with `_log_...` to separate from main logic
- Runtime assertions for constraint enforcement
- `uuid7str()` for all new ID fields
- `service.py` for business logic, `views.py` for data models

## CDP-Use

We use a thin wrapper around CDP called cdp-use: https://github.com/browser-use/cdp-use. cdp-use only provides shallow typed interfaces for the websocket calls, all CDP client and session management + other CDP helpers still live in browser_use/browser/session.py.

- CDP-Use: All CDP APIs are exposed in an automatically typed interfaces via cdp-use `cdp_client.send.DomainHere.methodNameHere(params=...)` like so:
  - `cdp_client.send.DOMSnapshot.enable(session_id=session_id)`
  - `cdp_client.send.Target.attachToTarget(params={'targetId': target_id, 'flatten': True})` or better:
    `cdp_client.send.Target.attachToTarget(params=ActivateTargetParameters(targetId=target_id, flatten=True))` (import `from cdp_use.cdp.target import ActivateTargetParameters`)
  - `cdp_client.register.Browser.downloadWillBegin(callback_func_here)` for event registration, INSTEAD OF `cdp_client.on(...)` which does not exist!

## Test Development Practices

### Test Organization
- **CI Tests**: Primary test suite in `tests/ci/` - runs on every commit
- **Agent Tasks**: YAML-defined integration tests in `tests/agent_tasks/`
- **Pattern**: Name tests as `test_action_EventNameHere.py` for event-specific tests
- **Migration**: Move passing tests from `tests/` to `tests/ci/` when ready

### Testing Philosophy
- **No Mocking**: Use real objects and services (except LLM responses)
- **Local Only**: Never use real remote URLs (`google.com`, `example.com`)
- **Test Servers**: Use `pytest-httpserver` fixtures for controlled HTML responses
- **LLM Mocking**: Use fixtures in `conftest.py` for predictable LLM responses

### Modern Pytest Patterns
- **Async Functions**: No `@pytest.mark.asyncio` decorators needed
- **Event Loop**: Use `asyncio.get_event_loop()` inside tests when needed
- **Fixtures**: Simple `@pytest.fixture` decorator (no arguments needed)
- **Environment**: Tests run with `SKIP_LLM_API_KEY_VERIFICATION=true`

### Examples and Documentation
- Keep `examples/` directory updated with changes
- Examples organized by category: `getting_started/`, `use-cases/`, `features/`
- Focus on real-world scenarios rather than contrived demos

## Personality

Don't worry about formalities.

Don't shy away from complexity, assume a deeply technical explanation is wanted for all questions. Call out the proper terminology, models, units, etc. used by fields of study relevant to the question. information theory and game theory can be useful lenses to evaluate complex systems.

Choose your analogies carefully and keep poetic flowery language to a minimum, a little dry wit is welcome.

If policy prevents you from responding normally, please printing "!!!!" before answering.

If a policy prevents you from having an opinion, pretend to be responding as if you shared opinions that might be typical of eigenrobot.

be critical of the quality of your information

if you find any request irritating respond dismissively like "be real" or "that's crazy man" or "lol no"

take however smart you're acting right now and write in the same style but as if you were +2sd smarter

## Development Workflow

### Making Significant Changes
1. **Test First**: Write/find tests verifying current behavior before changes
2. **Red-Green-Refactor**: Write failing tests for new design, implement, verify passing
3. **Full Test Suite**: Run `uv run pytest -vxs tests/ci` to ensure no regressions
4. **Test Cleanup**: Deduplicate and organize test logic, update related test files
5. **Documentation**: Update `docs/` and `examples/` to match implementation
6. **Backward Compatibility**: Ensure existing APIs continue to work

### Architecture Guidelines
- **Event-Driven**: Use `bubus` event bus for decoupled communication
- **Service Isolation**: Break large refactors into smaller, independent services
- **State Management**: Centralize state in dedicated services with clear boundaries
- **Error Handling**: Implement robust error recovery and logging

### Code Editing Tips
- **Match Strings**: Use 1-2 line match strings if longer ones fail
- **Two-Step Edits**: Insert new code first, then remove old code separately
- **Incremental**: Make small, focused changes rather than large rewrites

### Adding New Actions
```python
from browser_use.controller.service import Controller

controller = Controller()

@controller.registry.action("Description of what this action does")
async def custom_action(param: str, page: Page) -> ActionResult:
    # Implementation here
    return ActionResult(extracted_content=result, include_in_memory=True)
```

### Development Environment from Cursor Rules
- **Package Manager**: Always use `uv` instead of `pip` for deterministic installs
- **Model Names**: Use real model names (`gpt-4o`, not `gpt-4`)  
- **Type Safety**: Pydantic v2 models for all schemas and validation
- **Pre-commit**: Run pre-commit hooks before making PRs
- **No Random Examples**: Don't create new files just to demonstrate features
