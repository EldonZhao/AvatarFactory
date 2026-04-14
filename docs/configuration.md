# Configuration

AvatarFactory supports multiple LLM providers and platform connectors. This guide covers all configuration options.

---

## LLM Providers

Set your provider in `.env`:

```bash
# Options: anthropic | azure_openai | openai
AVATARFACTORY_LLM_PROVIDER=anthropic
```

### Anthropic Claude (Default)

Best reasoning capabilities, long context windows, excellent at structured output.

```bash
AVATARFACTORY_LLM_PROVIDER=anthropic
AVATARFACTORY_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-xxxxx...
```

Get API key: https://console.anthropic.com/

**Recommended models:**
- `claude-3-5-sonnet-20241022` — Best for complex reasoning
- `claude-3-5-haiku-20241022` — Faster, cheaper

### Azure OpenAI

Enterprise-grade security, regional deployment, Azure ecosystem integration.

```bash
AVATARFACTORY_LLM_PROVIDER=azure_openai
AVATARFACTORY_MODEL=gpt-4
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

Setup: Create an Azure OpenAI resource → Deploy a model → Copy endpoint and key → Set deployment name as `AVATARFACTORY_MODEL`.

**Recommended models:** `gpt-4`, `gpt-4-turbo`, `gpt-35-turbo`

### OpenAI

Easy to get started, pay-as-you-go pricing.

```bash
AVATARFACTORY_LLM_PROVIDER=openai
AVATARFACTORY_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=sk-xxxxx...
```

Get API key: https://platform.openai.com/api-keys

**Recommended models:** `gpt-4-turbo-preview`, `gpt-4`, `gpt-3.5-turbo`

---

## Switching Providers

```bash
# Edit .env to switch providers — no code changes needed
AVATARFACTORY_LLM_PROVIDER=azure_openai
AVATARFACTORY_MODEL=gpt-4

# Or override temporarily for one session:
export AVATARFACTORY_LLM_PROVIDER=openai
avatarfactory chat
```

---

## Cost Comparison (Approximate)

| Provider | Model | Input (per 1M tokens) | Output (per 1M tokens) |
|----------|-------|----------------------|------------------------|
| Anthropic | Claude 3.5 Sonnet | $3 | $15 |
| Anthropic | Claude 3.5 Haiku | $0.80 | $4 |
| Azure/OpenAI | GPT-4 Turbo | $10 | $30 |
| Azure/OpenAI | GPT-3.5 Turbo | $0.50 | $1.50 |

**Recommendations:**
- **Development:** Claude Haiku or GPT-3.5 (cheap)
- **Production:** Claude Sonnet or GPT-4 (quality)
- **Enterprise:** Azure OpenAI (compliance)

---

## Test Configuration

```bash
python -c "
from avatarfactory.core.llm_provider import LLMProviderFactory
provider = LLMProviderFactory.from_env()
print(f'Provider: {provider.__class__.__name__}')
print(f'Model: {provider.model}')
print(f'Config valid: {provider.validate_config()}')
"
```

Or simply:
```bash
avatarfactory chat
> Hello
```

---

## Programmatic Usage

```python
from avatarfactory.core.llm_provider import LLMProviderFactory

# Auto-detect from environment
provider = LLMProviderFactory.from_env()

# Explicit creation
provider = LLMProviderFactory.create(
    "azure_openai",
    model="gpt-4",
    endpoint="https://your-resource.openai.azure.com/",
    api_key="your_key"
)
```

---

## Platform Connectors

See [connectors/README.md](connectors/README.md) for complete setup guides per platform.

### Quick Reference

| Platform | Required Environment Variables |
|----------|-------------------------------|
| Bluesky | `BLUESKY_USERNAME`, `BLUESKY_PASSWORD` |
| Twitter/X | `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` |
| Xiaohongshu | `XIAOHONGSHU_COOKIE`, `XIAOHONGSHU_USER_ID` |
| LinkedIn | `LINKEDIN_ACCESS_TOKEN` |
| Instagram | `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID` |
| Threads | `THREADS_ACCESS_TOKEN` |
| Mastodon | `MASTODON_ACCESS_TOKEN`, `MASTODON_INSTANCE_URL` |
| Weibo | `WEIBO_ACCESS_TOKEN` |
| WeChat Work | `AVATARFACTORY_WEBHOOK_URL`, `AVATARFACTORY_WEBHOOK_FORMAT` |

---

## Database Configuration

AvatarFactory supports two storage backends:

1. **File-based (default)**: YAML/JSON files in the `knowledges/` directory
2. **Database**: SQLite or PostgreSQL for better performance and scalability

### Storage Architecture

When database storage is enabled, AvatarFactory uses a hybrid approach:

| Data Type | Storage Backend | Notes |
|-----------|-----------------|-------|
| Personas | Database | Full CRUD with versioning |
| Content & Reviews | Database | Efficient queries and filtering |
| Discoveries | Database | Historical trend data |
| Recommendations | Database | Persona recommendations |
| Trend Snapshots | Database | Platform trend data |
| **Scheduler Tasks** | **File System** | `scheduler/tasks.json` |
| **Publish Queue** | **File System** | `scheduler/publish_queue.json` |

**Why Scheduler uses File Storage:**
- APScheduler manages tasks in-memory with file persistence as its native approach
- Runtime state (`last_run`, `run_count`) updates frequently during task execution
- File storage avoids database transaction overhead for frequent updates
- Simpler and more reliable for the scheduler's operational needs

**Important for Azure:** Both database and scheduler files require persistent storage. Set `WEBSITES_ENABLE_APP_SERVICE_STORAGE=true`.

### Enabling Database Storage

```bash
# Enable database storage (default: false)
AVATARFACTORY_USE_DB=true

# Database URL (optional, defaults to SQLite in knowledges directory)
# SQLite (default when USE_DB=true):
AVATARFACTORY_DB_URL=sqlite+aiosqlite:///./knowledges/avatarfactory.db

# PostgreSQL:
AVATARFACTORY_DB_URL=postgresql+asyncpg://user:password@localhost:5432/avatarfactory
```

### PostgreSQL Connection Pool Settings

For production PostgreSQL deployments, you can tune the connection pool:

```bash
AVATARFACTORY_DB_POOL_SIZE=5          # Base pool size (default: 5)
AVATARFACTORY_DB_MAX_OVERFLOW=10      # Max additional connections (default: 10)
AVATARFACTORY_DB_POOL_TIMEOUT=30      # Checkout timeout in seconds (default: 30)
AVATARFACTORY_DB_POOL_RECYCLE=1800    # Recycle connections after N seconds (default: 1800)
```

### Debug Options

```bash
AVATARFACTORY_DB_ECHO=true            # Enable SQL query logging
```

### Migration from File-based to Database

If you have existing data in file-based storage, use the migration script:

```bash
# Dry run to see what would be migrated
python -m avatarfactory.core.database.migrations.initial_migration --dry-run

# Perform migration
python -m avatarfactory.core.database.migrations.initial_migration
```

### When to Use Database Storage

| Use Case | Recommended Backend |
|----------|---------------------|
| Local development | File-based (simpler) |
| Single user | File-based or SQLite |
| Multiple users/instances | PostgreSQL |
| Production deployment | PostgreSQL |
| Large datasets (>1000 personas) | PostgreSQL |

---

## Other Settings

### Knowledge Base
```bash
AVATARFACTORY_KB_PATH=./knowledges    # Data storage directory
```

### Video Generation
```bash
AZURE_SPEECH_KEY=your_key             # Azure Speech Service
AZURE_SPEECH_REGION=eastasia          # Azure region
AVATARFACTORY_VIDEO_PROVIDER=auto     # auto | azure | edge
AVATARFACTORY_DEFAULT_VOICE=zh-CN-XiaoxiaoNeural  # Default TTS voice
```

### Notifications
```bash
AVATARFACTORY_WEBHOOK_URL=https://...  # Webhook URL
AVATARFACTORY_WEBHOOK_FORMAT=wecom     # slack | discord | feishu | wecom | generic
```

---

## All Environment Variables

See `.env.example` for a complete list of all supported environment variables with descriptions.
