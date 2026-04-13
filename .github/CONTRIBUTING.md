# Contributing to AvatarFactory

Thank you for your interest in contributing to AvatarFactory! This guide will help you get started.

---

## Development Setup

### Prerequisites

- Python 3.10+
- Git

### Install

```bash
git clone https://github.com/EldonZhao/AvatarFactory.git
cd AvatarFactory

# Using virtual environment (recommended)
# Windows PowerShell:
.\setup_venv.ps1
# macOS/Linux:
chmod +x setup_venv.sh && ./setup_venv.sh

# Or manual install:
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1 on Windows
pip install -r requirements-dev.txt
pip install -e .
```

### Configure

```bash
cp .env.example .env
# Edit .env with your LLM provider API key
```

See [docs/configuration.md](../docs/configuration.md) for all provider options.

---

## Code Standards

| Rule | Tool | Command |
|------|------|---------|
| Python 3.10+ | — | `python --version` |
| Type hints on **all** function signatures | mypy (`disallow_untyped_defs = true`) | `mypy avatarfactory` |
| Line length ≤ 100 characters | Black + Ruff | `black avatarfactory tests --check` |
| Linting | Ruff | `ruff check avatarfactory tests` |
| Async/await for all I/O | — | — |
| Pydantic models for data structures | — | — |

Run all checks before submitting:

```bash
black avatarfactory tests --check
ruff check avatarfactory tests
mypy avatarfactory
pytest tests/ -v
```

---

## Extension Patterns

AvatarFactory has three main extension points. Follow the patterns below when adding new components.

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

- Each agent inherits from `BaseAgent`
- Single responsibility per agent
- Communication via `AgentMessage`
- Access shared `KnowledgeBase` for persistence

### Adding a Platform Connector

```python
from avatarfactory.connectors.base import BasePlatformConnector
from avatarfactory.connectors.registry import ConnectorRegistry

@ConnectorRegistry.register_decorator("new_platform")
class NewPlatformConnector(BasePlatformConnector):
    async def connect(self) -> bool:
        pass  # Connection logic

    async def publish(self, content: Content) -> Dict[str, Any]:
        pass  # Publish logic

    async def fetch_posts(self, limit: int = 20) -> List[Dict]:
        pass  # Fetch logic
```

- Register via `@ConnectorRegistry.register_decorator`
- Import in `avatarfactory/connectors/__init__.py` to trigger registration
- Add connector documentation in `docs/connectors/<platform>.md`

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

- Adapters handle platform-specific content formatting and validation (offline)
- Connectors handle API integration and network operations (online)

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=avatarfactory

# Run specific test file
pytest tests/unit/test_adapters.py -v
```

- Unit tests go in `tests/unit/`
- Integration tests go in `tests/integration/`
- Use `pytest-asyncio` for async tests
- Mock LLM calls to avoid API costs in tests

---

## Commit Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add LinkedIn connector
fix: resolve encoding issue on Windows
docs: update quickstart guide
chore: bump dependencies
test: add adapter unit tests
refactor: simplify orchestrator routing
```

Keep commits focused and atomic. Update documentation when changing functionality.

---

## Development Principles

### Human-in-the-Loop

AvatarFactory is a **learning and building** tool, not an automation tool:

- All publishing requires explicit human approval
- Default mode is human-in-the-loop
- No automatic engagement or spamming

### Error Handling

- Graceful degradation for LLM API failures
- Retry logic for transient errors
- Clear error messages for user-facing CLI
- Use `python-dotenv` to load `.env` at startup
- Handle Windows console encoding (UTF-8)
- Use Rich for terminal UI (tables, panels, progress)

---

## Review Scoring Dimensions

Content is scored on four independent dimensions (0-100 each):

1. **Persona Consistency** — matches voice/expertise
2. **Platform Fit** — optimized for target platform
3. **Compliance** — no sensitive/misleading content
4. **Engagement Potential** — audience appeal

These scores are referenced in code reviews for content-related changes.

---

## Questions?

- Open a [GitHub Issue](https://github.com/EldonZhao/AvatarFactory/issues) for bugs or features
- Check [SUPPORT.md](SUPPORT.md) for troubleshooting
- Read [docs/architecture.md](../docs/architecture.md) for system design
