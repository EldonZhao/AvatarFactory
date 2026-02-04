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
avatarfactory list-personas
avatarfactory list-content
avatarfactory stats

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
# or with specific provider extras
pip install -e ".[openai]"
```

## Architecture

### Multi-Agent System

The system uses message-based orchestration with one master agent coordinating specialized sub-agents:

```
CLI (chat/commands)
    ↓
Orchestrator Agent (intent routing)
    ├→ Persona Lab Agent (persona CRUD, versioning)
    ├→ Content Lab Agent (multi-variant generation)
    ├→ Review Agent (4-dimension scoring)
    ├→ Simulation Agent (engagement prediction)
    └→ Knowledge Base (file-based persistence)
```

### Key Modules

- **`avatarfactory/agents/`** - Agent implementations inheriting from `BaseAgent`
- **`avatarfactory/core/knowledge_base.py`** - File-based YAML/JSON storage at `./knowledge_base/`
- **`avatarfactory/core/llm_provider.py`** - LLM abstraction (Anthropic, Azure OpenAI, OpenAI)
- **`avatarfactory/models/schemas.py`** - Pydantic models for all data structures
- **`avatarfactory/adapters/`** - Platform-specific adapters (Xiaohongshu, Zhihu, Twitter)
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
- `AVATARFACTORY_LLM_PROVIDER` - anthropic | azure_openai | openai
- `AVATARFACTORY_MODEL` - model name (e.g., claude-3-5-sonnet-20241022)
- `AVATARFACTORY_KB_PATH` - knowledge base directory (default: ./knowledge_base)
- Provider-specific API keys (ANTHROPIC_API_KEY, OPENAI_API_KEY, AZURE_OPENAI_*)

## Code Standards

- Python 3.10+
- Type hints required on all function signatures (`disallow_untyped_defs = true`)
- Line length: 100 characters (Black, Ruff)
- Async/await for all I/O operations
- Pydantic models for data validation
