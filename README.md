# AvatarFactory

**AvatarFactory** is a *Persona Factory* for social platforms: it helps you **design, simulate, evaluate, and evolve** social personas (avatars) across different platforms, so you can build long-term attention and trust—preparing for sustainable lead generation and future monetization.

> Focus: **persona building & learning**, not risky "full automation".
> Default mode: **human-in-the-loop** publishing and engagement for compliance.

---

## Why AvatarFactory

Building a strong persona is not just "writing posts". It's an iterative loop:

1. Define a persona with clear positioning and boundaries
2. Create consistent, platform-native content at scale
3. Learn from feedback signals (saves, comments, follows, DMs)
4. Evolve the persona and content pillars over time
5. Gradually build trust and conversion readiness

AvatarFactory turns this into an **experiment-driven workflow**.

---

## Core Goals

- **Persona Assetization**: represent a persona as a structured, versioned configuration (not a one-line bio).
- **Cross-Platform Adaptation**: translate one persona into platform-native styles (e.g., Xiaohongshu vs. Twitter/X vs. Bluesky).
- **Offline Simulation**: simulate "what could happen after posting" (expected engagement, comment topics, risk flags) before going live.
- **Experiment & Learning Loop**: run experiments, collect feedback, and update persona/content strategies with traceability.
- **Monetization Readiness (Later)**: mine recurring demands from interactions to inform future offers/products—without locking into a product too early.

---

## Features

### Agent System
- **PersonaAgent** - Persona CRUD, versioning, optimization
- **ContentAgent** - Multi-variant generation with hot-topic integration
- **DiscoveryAgent** - Learn from social platforms, analyze trends
- **ReviewAgent** - 4-dimension scoring (persona consistency, platform fit, compliance, engagement)
- **SimulationAgent** - Engagement prediction and comment scripts
- **ProactiveOrchestrator** - Scheduled tasks, automatic trend scanning

### Platform Connectors
- **Bluesky** - Full AT Protocol support (post, reply threads, fetch posts)
- **Twitter/X** - API v2 with thread support
- **Xiaohongshu (小红书)** - Cookie-based auth with xhs library signing
- **WeChat Work (企业微信)** - Webhook notifications

### Service Deployment
- **FastAPI REST API** - Production-ready HTTP service
- **Background Scheduler** - APScheduler-based task automation
- **Docker Support** - Containerized deployment
- **Webhook Notifications** - Slack, Discord, Feishu, WeChat Work

### Video Generation
- **Azure TTS** - High-quality text-to-speech
- **Edge TTS** - Free Microsoft Edge TTS (no API key required)
- **Azure Avatar** - AI digital human video generation
- **Video Composer** - Combine audio and images into videos

---

## Getting Started

### Installation

**Recommended: Using Virtual Environment (venv)**

Windows:
```powershell
# PowerShell (recommended)
.\setup_venv.ps1

# Or CMD
setup_venv.bat
```

macOS/Linux:
```bash
# Make executable and run
chmod +x setup_venv.sh
./setup_venv.sh
```

The script will:
- Create virtual environment
- Install dependencies
- Setup AvatarFactory
- Verify installation

---

**Alternative: Direct install**

```bash
# Clone the repository
git clone https://github.com/EldonZhao/AvatarFactory.git
cd AvatarFactory

# Install dependencies
pip install -r requirements.txt

# Install package
pip install -e .

# For service deployment
pip install -e ".[service]"
```

### Configuration

1. Create a `.env` file from the example:
```bash
cp .env.example .env
```

2. Configure your LLM provider:

**Option A: Anthropic Claude (Default)**
```bash
AVATARFACTORY_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key_here
```

**Option B: Azure OpenAI**
```bash
AVATARFACTORY_LLM_PROVIDER=azure_openai
AVATARFACTORY_MODEL=gpt-4
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

**Option C: OpenAI**
```bash
AVATARFACTORY_LLM_PROVIDER=openai
AVATARFACTORY_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your_key
```

3. (Optional) Configure platform connectors:

```bash
# Bluesky
BLUESKY_USERNAME=your.handle.bsky.social
BLUESKY_PASSWORD=your-app-password

# Xiaohongshu
XIAOHONGSHU_COOKIE=your_cookie_string
XIAOHONGSHU_USER_ID=your_user_id

# WeChat Work (for notifications)
AVATARFACTORY_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
AVATARFACTORY_WEBHOOK_FORMAT=wecom
```

### Quick Start

**Interactive Chat (Recommended):**
```bash
avatarfactory chat
```

Then talk naturally:
```
You: Create a persona for an AI tools reviewer targeting product managers
You: Generate content about Notion vs Obsidian comparison
You: Discover trending topics on Bluesky
```

**Quick Commands:**
```bash
# Create a persona
avatarfactory create-persona "AI tools expert for product managers"

# Generate content
avatarfactory generate "Notion vs Obsidian comparison"

# Discover trending content
avatarfactory discover --platform bluesky --limit 20

# List personas
avatarfactory list-personas

# Show content
avatarfactory show-content <content_id>

# Publish draft
avatarfactory publish-draft <content_id> --platform bluesky

# Show stats
avatarfactory stats
```

---

## Service Deployment

### Run as HTTP Service

```bash
# Start the service
avatarfactory serve --host 0.0.0.0 --port 8000

# Or run scheduler only
avatarfactory serve --mode scheduler
```

### API Endpoints

- `GET /health` - Health check
- `POST /chat` - Process chat message
- `GET /personas` - List all personas
- `GET /personas/{id}` - Get persona details
- `POST /personas` - Create persona
- `GET /content` - List content
- `GET /content/{id}` - Get content details
- `POST /content/generate` - Generate content
- `GET /scheduler/status` - Scheduler status
- `GET /scheduler/tasks` - List scheduled tasks
- `POST /scheduler/tasks/{persona_id}/setup` - Setup proactive tasks

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## Project Structure

```
avatarfactory/
├── agents/              # AI agents
│   ├── persona.py       # PersonaAgent (persona CRUD)
│   ├── content.py       # ContentAgent (content generation)
│   ├── discovery.py     # DiscoveryAgent (trend analysis)
│   ├── orchestrator.py  # OrchestratorAgent (intent routing)
│   └── proactive_orchestrator.py  # ProactiveOrchestrator
├── connectors/          # Platform connectors
│   ├── bluesky.py       # Bluesky (AT Protocol)
│   ├── twitter.py       # Twitter/X API v2
│   ├── xiaohongshu.py   # Xiaohongshu (小红书)
│   ├── wecom.py         # WeChat Work (企业微信)
│   └── registry.py      # Connector registry
├── core/                # Core functionality
│   ├── knowledges.py    # Knowledge base
│   └── llm_provider.py  # LLM abstraction
├── models/              # Data models (Pydantic)
├── adapters/            # Platform content adapters
├── scheduler/           # Task scheduling
│   ├── engine.py        # APScheduler engine
│   └── tasks.py         # Task definitions
├── service/             # FastAPI service
│   └── app.py           # REST API
├── video/               # Video generation
│   ├── azure_tts.py     # Azure TTS
│   ├── edge_tts.py      # Edge TTS (free)
│   ├── azure_avatar.py  # Azure Avatar
│   └── composer.py      # Video composer
├── notifications/       # Notification system
└── cli.py               # Command-line interface

knowledges/              # User data storage (default)
├── personas/            # Persona configurations
├── content_library/     # Generated content
├── experiments/         # Experiment data
└── platform_rules/      # Platform-specific rules
```

---

## Current Status (v0.2.0)

**Implemented:**
- Persona creation and versioning
- Content generation with multi-variant support
- Hot-topic driven content generation
- Multi-dimensional review system
- Platform connectors (Bluesky, Twitter, Xiaohongshu, WeChat Work)
- Discovery Agent for trend analysis
- Scheduled task automation
- FastAPI REST API service
- Docker deployment support
- Video generation with TTS
- Webhook notifications

**Coming Soon:**
- Web UI dashboard
- Advanced analytics and reporting
- More platform connectors
- MCP tool ecosystem integration

---

## Contributing

Contributions are welcome! Feel free to:
- Report bugs and issues
- Suggest new features
- Submit pull requests
- Improve documentation

---

## License

MIT License - see [LICENSE](LICENSE) for details.
