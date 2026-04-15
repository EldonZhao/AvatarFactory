---
applyTo: "**"
---

# Machine Migration Instructions

When migrating AvatarFactory development environment to a new machine, follow these steps.

## Files to Migrate

### Required

| Path | Description |
|------|-------------|
| `knowledges/` | All persistent data (database, personas, content, etc.) |
| `.env` | Environment variables and API keys |
| `connectors_config.json` | Local connector credentials (if exists) |

### What's in `knowledges/`

| File/Directory | Content |
|----------------|---------|
| `avatarfactory.db` | SQLite database (personas, contents, scheduler tasks, reviews, etc.) |
| `personas/` | Persona YAML configuration files |
| `content_library/` | Generated content files |
| `recommendations/` | Persona recommendation history |
| `scheduler/` | Scheduler tasks and publish queue (JSON persistence) |
| `videos/` | Generated video files |
| `experiments/` | A/B test experiments data |
| `platform_rules/` | Platform-specific content rules |
| `user_feedback/` | User feedback records |

### What's in `.env`

```bash
# LLM Provider
AVATARFACTORY_LLM_PROVIDER=anthropic  # or azure_openai, openai
AVATARFACTORY_MODEL=claude-3-5-sonnet-20241022
AVATARFACTORY_FAST_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Azure OpenAI (if using azure_openai provider)
# AZURE_OPENAI_API_KEY=...
# AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com/
# AZURE_OPENAI_API_VERSION=2024-02-15-preview

# App Settings
AVATARFACTORY_KB_PATH=./knowledges
AVATARFACTORY_LOG_LEVEL=INFO
AVATARFACTORY_SERVICE_URL=http://localhost:8000

# Platform Connectors
BLUESKY_USERNAME=...
BLUESKY_PASSWORD=...
XIAOHONGSHU_COOKIE=...
XIAOHONGSHU_USER_ID=...

# Notifications
AVATARFACTORY_WEBHOOK_URL=...
AVATARFACTORY_WEBHOOK_FORMAT=wecom  # slack | discord | feishu | wecom | generic
```

## Migration Steps

### 1. Package Data on Current Machine

```bash
# Create archive with all required data
tar -czvf avatarfactory-data.tar.gz knowledges/ .env connectors_config.json 2>/dev/null
```

### 2. Transfer to New Machine

Use any method: USB, cloud storage, scp, etc.

```bash
# Example with scp
scp avatarfactory-data.tar.gz user@new-machine:~/
```

### 3. Setup on New Machine

```bash
# Clone repository
git clone https://github.com/EldonZhao/AvatarFactory.git
cd AvatarFactory

# Extract data to project root
tar -xzvf ~/avatarfactory-data.tar.gz

# Create and activate virtual environment
python -m venv .venv
# Windows: .\.venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

# Install Python dependencies
pip install -e ".[service]"

# Install web-admin dependencies
cd web-admin && npm install && cd ..

# Install web-journal dependencies
cd web-journal && npm install && cd ..

# Start backend service
avatarfactory serve --host 0.0.0.0 --port 8000

# Start web-admin (in another terminal)
cd web-admin && npm run dev

# Start web-journal (in another terminal)
cd web-journal && npm run dev
```

## PostgreSQL Migration (Optional)

If using PostgreSQL instead of SQLite:

1. Export data from old database
2. Configure `DATABASE_URL` in `.env` on new machine
3. Run migrations: `avatarfactory db migrate`
4. Import data to new database

## Verification Checklist

After migration, verify:

- [ ] `avatarfactory serve` starts without errors
- [ ] Dashboard shows correct persona and content counts
- [ ] Scheduler tasks are loaded correctly
- [ ] Chat page can list personas
- [ ] Connectors show correct configuration status

## Security Notes

- **Never** commit `knowledges/`, `.env`, or `connectors_config.json` to Git
- These files are already in `.gitignore`
- Delete the archive file after successful migration
- Rotate API keys if archive was transmitted over insecure channels
