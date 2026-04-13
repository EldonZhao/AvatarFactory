# Getting Started

This guide covers installation, configuration, and your first run with AvatarFactory.

---

## Prerequisites

- Python 3.10 or higher (`python --version`)
- An LLM API key (Anthropic, Azure OpenAI, or OpenAI)

---

## Installation

### Option 1: Virtual Environment (Recommended)

**Windows PowerShell:**
```powershell
.\scripts\setup_venv.ps1
```

**macOS/Linux:**
```bash
chmod +x scripts/setup_venv.sh
./scripts/setup_venv.sh
```

The script will create a virtual environment, install dependencies, set up AvatarFactory, and verify installation.

### Option 2: Direct Install

```bash
git clone https://github.com/EldonZhao/AvatarFactory.git
cd AvatarFactory

pip install -r requirements.txt
pip install -e .

# For service deployment extras:
pip install -e ".[service]"
```

### Development Install

```bash
pip install -r requirements-dev.txt
pip install -e .
```

This includes testing and code quality tools (pytest, black, ruff, mypy).

### Verify Installation

```bash
avatarfactory version
# Or run the verification script:
python scripts/verify_install.py
```

---

## Configuration

### 1. Create `.env` file

```bash
cp .env.example .env
```

### 2. Choose your LLM provider

**Anthropic Claude (Default, recommended):**
```bash
AVATARFACTORY_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx...
```

**Azure OpenAI:**
```bash
AVATARFACTORY_LLM_PROVIDER=azure_openai
AVATARFACTORY_MODEL=gpt-4
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

**OpenAI:**
```bash
AVATARFACTORY_LLM_PROVIDER=openai
AVATARFACTORY_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=sk-xxxxx...
```

See [configuration.md](configuration.md) for detailed provider options and cost comparison.

### 3. (Optional) Configure platform connectors

```bash
# Bluesky
BLUESKY_USERNAME=your.handle.bsky.social
BLUESKY_PASSWORD=your-app-password

# Xiaohongshu
XIAOHONGSHU_COOKIE=your_cookie_string
XIAOHONGSHU_USER_ID=your_user_id

# WeChat Work notifications
AVATARFACTORY_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
AVATARFACTORY_WEBHOOK_FORMAT=wecom
```

See [connectors/README.md](connectors/README.md) for all platform setup guides.

### 4. Test your configuration

```bash
avatarfactory chat
# Type: hello
# If it responds, you're good to go!
```

---

## Quick Start

### Interactive Chat (Recommended)

```bash
avatarfactory chat
```

Then talk naturally:

```
You: Create a persona for an AI tools reviewer targeting product managers
You: Generate content about Notion vs Obsidian comparison
You: Discover trending topics on Bluesky
You: Show me my personas
```

### CLI Commands

```bash
# Create a persona
avatarfactory create-persona "AI tools expert for product managers"

# Generate content
avatarfactory generate "Notion vs Obsidian comparison"

# Discover trending content
avatarfactory discover --platform bluesky --limit 20

# List personas and content
avatarfactory list-personas
avatarfactory list-content

# Show content details
avatarfactory show-content <content_id>

# Publish a draft
avatarfactory publish-draft <content_id> --platform bluesky

# View statistics
avatarfactory stats
```

### Service Mode

```bash
# Start HTTP service
avatarfactory serve --host 0.0.0.0 --port 8000

# Run scheduler only
avatarfactory serve --mode scheduler
```

API docs available at `http://localhost:8000/docs`

### Docker

```bash
docker-compose up -d
docker-compose logs -f
```

### Python API

```python
import asyncio
from avatarfactory import OrchestratorAgent, KnowledgeBase
from avatarfactory.core.llm_provider import LLMProviderFactory

async def main():
    kb = KnowledgeBase("./knowledges")
    llm = LLMProviderFactory.from_env()
    orchestrator = OrchestratorAgent(knowledge_base=kb, llm_provider=llm)
    result = await orchestrator._handle_user_input(
        "Create a persona for AI tools reviewer"
    )
    print(result)

asyncio.run(main())
```

---

## Typical Workflow

1. **Create a Persona** — Define positioning, voice, and target audience
2. **Discover Trends** — Scan platforms for hot topics relevant to your persona
3. **Generate Content** — Create multi-variant content with hot-topic integration
4. **Review** — Auto-scored on 4 dimensions (persona consistency, platform fit, compliance, engagement)
5. **Publish** — Human-reviewed publishing to target platforms
6. **Iterate** — Evolve persona based on feedback signals

---

## Verify Everything Works

```bash
# Check personas
avatarfactory list-personas

# Check generated content
avatarfactory list-content --status draft

# View statistics
avatarfactory stats
```

---

## File Locations

```
.env                     # Your configuration
knowledges/              # All user data
  personas/              # Persona configurations
  content_library/       # Generated content
  experiments/           # Experiment data
  platform_rules/        # Platform-specific rules
  scheduler/             # Scheduled task configs
```

---

## What's Next?

- [Configuration Guide](configuration.md) — All LLM providers and advanced settings
- [Connector Guides](connectors/README.md) — Set up platform integrations
- [Architecture](architecture.md) — Understand the multi-agent system
- [Deployment](deployment/azure.md) — Deploy to production
