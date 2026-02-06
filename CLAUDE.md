# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AvatarFactory is an AI-powered persona management system for social media platforms. It helps users design, simulate, evaluate, and evolve social personas (avatars) using a multi-agent architecture with human-in-the-loop workflows.

**Core Philosophy:** Persona building and learning, not automation. All publishing requires human review.

## Common Commands

```bash
# Run the interactive chat interface (primary UX)
avatarfactory chat [--persona PERSONA_ID]

# Quick CLI commands
avatarfactory create-persona "description"
avatarfactory generate "topic"
avatarfactory discover --platform bluesky --limit 20
avatarfactory list-personas
avatarfactory list-content
avatarfactory show-content <content_id>
avatarfactory publish-draft <content_id> --platform bluesky
avatarfactory stats

# Service deployment
avatarfactory serve --host 0.0.0.0 --port 8000
avatarfactory serve --mode scheduler

# Scheduler commands
avatarfactory schedule list
avatarfactory schedule run <task_id>

# Testing
pytest tests/ -v
pytest tests/ --cov=avatarfactory
pytest tests/unit/test_adapters.py -v  # single test file

# Linting and formatting
black avatarfactory tests --check
ruff check avatarfactory tests
mypy avatarfactory

# Install (development)
pip install -e .
# or with service extras
pip install -e ".[service]"
```

## Architecture

### Multi-Agent System

The system uses message-based orchestration with one master agent coordinating specialized sub-agents:

```
CLI (chat/commands) / FastAPI Service
    ↓
ProactiveOrchestrator (intent routing + scheduled tasks)
    ├→ PersonaAgent (persona CRUD, versioning)
    ├→ ContentAgent (multi-variant generation + hot-topic integration)
    ├→ DiscoveryAgent (platform trend analysis)
    ├→ ReviewAgent (4-dimension scoring)
    ├→ SimulationAgent (engagement prediction)
    └→ Knowledges (file-based persistence)

Platform Connectors (via ConnectorRegistry)
    ├→ BlueskyConnector (AT Protocol)
    ├→ TwitterConnector (API v2)
    ├→ XiaohongshuConnector (cookie + xhs signing)
    └→ WeComConnector (webhook notifications)
```

### Key Modules

- **`avatarfactory/agents/`** - Agent implementations inheriting from `BaseAgent`
  - `persona.py` - PersonaAgent (persona CRUD, versioning)
  - `content.py` - ContentAgent (content generation with hot-topic support)
  - `discovery.py` - DiscoveryAgent (platform trend analysis)
  - `orchestrator.py` - OrchestratorAgent (intent routing)
  - `proactive_orchestrator.py` - ProactiveOrchestrator (scheduled tasks)
- **`avatarfactory/connectors/`** - Platform connectors
  - `registry.py` - ConnectorRegistry with decorator-based registration
  - `bluesky.py`, `twitter.py`, `xiaohongshu.py`, `wecom.py`
- **`avatarfactory/core/knowledges.py`** - File-based YAML/JSON storage at `./knowledges/`
- **`avatarfactory/core/llm_provider.py`** - LLM abstraction (Anthropic, Azure OpenAI, OpenAI)
- **`avatarfactory/models/schemas.py`** - Pydantic models for all data structures
- **`avatarfactory/adapters/`** - Platform-specific content adapters (Xiaohongshu, Twitter)
- **`avatarfactory/service/app.py`** - FastAPI REST API
- **`avatarfactory/scheduler/`** - APScheduler-based task automation
- **`avatarfactory/video/`** - Video generation (Azure TTS, Edge TTS, Azure Avatar)
- **`avatarfactory/cli.py`** - Typer CLI with Rich terminal UI

### Review Scoring Dimensions

Content is scored on four independent dimensions (0-100 each):
1. **Persona Consistency** - matches voice/expertise
2. **Platform Fit** - optimized for target platform
3. **Compliance** - no sensitive/misleading content
4. **Engagement Potential** - audience appeal

## Extending the System

### Adding a New Agent

```python
from avatarfactory.agents.base import BaseAgent
from avatarfactory.models.schemas import AgentMessage

class CustomAgent(BaseAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(agent_id="custom_agent", *args, **kwargs)

    async def process(self, message: AgentMessage) -> Any:
        self.validate_message(message)
        # Agent logic here
```

### Adding a Platform Connector

```python
from avatarfactory.connectors.base import BasePlatformConnector
from avatarfactory.connectors.registry import ConnectorRegistry

@ConnectorRegistry.register_decorator("new_platform")
class NewPlatformConnector(BasePlatformConnector):
    async def connect(self) -> bool:
        # Connection logic
        pass

    async def publish(self, content: Content) -> Dict[str, Any]:
        # Publish logic
        pass

    async def fetch_posts(self, limit: int = 20) -> List[Dict]:
        # Fetch posts logic
        pass
```

### Adding a Platform Adapter

```python
from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import PlatformType, Content

class NewPlatformAdapter(BasePlatformAdapter):
    platform = PlatformType.NEW_PLATFORM

    def get_content_guidelines(self) -> dict:
        return {...}

    def validate_content(self, content: Content) -> dict:
        return {...}
```

## Configuration

Environment variables (see `.env.example`):

### LLM Provider
- `AVATARFACTORY_LLM_PROVIDER` - anthropic | azure_openai | openai
- `AVATARFACTORY_MODEL` - model name (e.g., claude-3-5-sonnet-20241022)
- `AVATARFACTORY_KB_PATH` - knowledges directory (default: ./knowledges)
- Provider-specific API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, AZURE_OPENAI_*)

### Platform Connectors
- `BLUESKY_USERNAME`, `BLUESKY_PASSWORD` - Bluesky credentials
- `TWITTER_API_KEY`, `TWITTER_API_SECRET`, etc. - Twitter API v2
- `XIAOHONGSHU_COOKIE`, `XIAOHONGSHU_USER_ID` - Xiaohongshu auth

### Notifications
- `AVATARFACTORY_WEBHOOK_URL` - Webhook URL
- `AVATARFACTORY_WEBHOOK_FORMAT` - slack | discord | feishu | wecom | generic

### Video Generation
- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` - Azure Speech Service
- `AVATARFACTORY_VIDEO_PROVIDER` - auto | azure | edge
- `AVATARFACTORY_DEFAULT_VOICE` - Default TTS voice

## Code Standards

- Python 3.10+
- Type hints required on all function signatures (`disallow_untyped_defs = true`)
- Line length: 100 characters (Black, Ruff)
- Async/await for all I/O operations
- Pydantic models for data validation
