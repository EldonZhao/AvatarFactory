# AvatarFactory - Development Principles

## Code Standards

### Python Version & Style
- Python 3.10+ required
- Type hints on all function signatures (`disallow_untyped_defs = true`)
- Line length: 100 characters (Black, Ruff)
- Async/await for all I/O operations

### Data Validation
- Use Pydantic models for all data structures
- Validate at system boundaries
- Use `mode='json'` for serialization to avoid Enum issues

### Error Handling
- Graceful degradation for LLM API failures
- Retry logic for transient errors
- Clear error messages for user-facing CLI

---

## Architecture Principles

### Agent Design
- Each agent inherits from `BaseAgent`
- Single responsibility per agent
- Message-based communication via `AgentMessage`
- Agents access shared `KnowledgeBase` for persistence

### LLM Provider Abstraction
- Use `LLMProviderFactory.from_env()` for provider instantiation
- Support multiple providers (Anthropic, Azure OpenAI, OpenAI)
- Handle provider-specific quirks (temperature, max_tokens params)

### Platform Adapters
- Use adapter pattern for multi-platform support
- Each adapter implements `BasePlatformAdapter`
- Adapters handle platform-specific validation and formatting

---

## CLI Guidelines

- Load `.env` at startup with `python-dotenv`
- Handle Windows console encoding (UTF-8)
- Use Rich for terminal UI (tables, panels, progress)
- Graceful exit on Ctrl+C

---

## Testing

- Use pytest with pytest-asyncio
- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/`
- Run: `pytest tests/ -v`

---

## Git Workflow

- Conventional commit messages (feat/fix/chore/docs)
- Keep commits focused and atomic
- Update documentation when changing functionality
