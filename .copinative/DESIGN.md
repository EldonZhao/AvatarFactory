# AvatarFactory - Design Document

## Project Overview

AvatarFactory is an AI-powered persona management system for social media platforms. It helps users systematically design, simulate, evaluate, and evolve social personas (avatars) using a multi-agent architecture with human-in-the-loop workflows.

**Version:** 0.1.0 (MVP)  
**Language:** Python 3.10+  
**Core Philosophy:** Persona building and learning, not automation. All publishing requires human review.

---

## Architecture

### Multi-Agent System

The system uses a message-based orchestration pattern with one master agent coordinating specialized sub-agents:

```
User (CLI)
    ↓
Orchestrator Agent (Intent understanding & task routing)
    ├→ Persona Lab Agent (Persona creation/versioning)
    ├→ Content Lab Agent (Content generation & adaptation)
    ├→ Review Agent (Multi-dimensional scoring & compliance)
    ├→ Simulation Agent (Engagement prediction)
    └→ Knowledge Base (Shared data persistence)
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| CLI | `avatarfactory/cli.py` | Command-line interface with chat mode |
| Orchestrator | `avatarfactory/agents/orchestrator.py` | Intent routing and coordination |
| Persona Lab | `avatarfactory/agents/persona_lab.py` | Persona CRUD and versioning |
| Content Lab | `avatarfactory/agents/content_lab.py` | Multi-variant content generation |
| Review Agent | `avatarfactory/agents/review.py` | 4-dimension content scoring |
| Simulation | `avatarfactory/agents/simulation.py` | Engagement prediction |
| Knowledge Base | `avatarfactory/core/knowledge_base.py` | File-based YAML/JSON storage |
| LLM Provider | `avatarfactory/core/llm_provider.py` | LLM abstraction layer |
| Platform Adapters | `avatarfactory/adapters/` | Platform-specific formatting |
| Data Models | `avatarfactory/models/schemas.py` | Pydantic models |

---

## Data Flow

### Persona Creation
1. User provides natural language description
2. Orchestrator routes to Persona Lab Agent
3. LLM generates structured JSON config (identity, audience, voice, content pillars)
4. Validates with Pydantic models
5. Saves to Knowledge Base with version history

### Content Generation
1. User specifies topic and platform
2. Orchestrator routes to Content Lab Agent
3. Agent selects template and generates variants
4. Review Agent scores on 4 dimensions
5. Returns reviewed content with feedback

### Review Scoring (4 Dimensions)
- **Persona Consistency** (0-100): Does content match persona's voice?
- **Platform Fit** (0-100): Is content optimized for target platform?
- **Compliance** (0-100): Any risks or sensitive content?
- **Engagement Potential** (0-100): Will target audience engage?

---

## Technology Stack

- **LLM Providers:** Anthropic Claude, Azure OpenAI, OpenAI
- **Data Validation:** Pydantic
- **CLI Framework:** Typer + Rich
- **Storage:** File-based (YAML/JSON)
- **Async:** asyncio + aiofiles

---

## Storage Structure

```
knowledge_base/
├── personas/{id}/
│   ├── config.yaml
│   └── versions/
├── content_library/
│   ├── drafts/
│   └── published/
├── experiments/
└── platform_rules/
```
