# AvatarFactory

**AvatarFactory** is a *Persona Factory* for social platforms: it helps you **design, simulate, evaluate, and evolve** social personas (avatars) across different platforms, so you can build long-term attention and trust—preparing for sustainable lead generation and future monetization.

> Focus: **persona building & learning**, not risky “full automation”.  
> Default mode: **human-in-the-loop** publishing and engagement for compliance.

---

## Why AvatarFactory

Building a strong persona is not just “writing posts”. It’s an iterative loop:

1. Define a persona with clear positioning and boundaries  
2. Create consistent, platform-native content at scale  
3. Learn from feedback signals (saves, comments, follows, DMs)  
4. Evolve the persona and content pillars over time  
5. Gradually build trust and conversion readiness

AvatarFactory turns this into an **experiment-driven workflow**.

---

## Core Goals

- **Persona Assetization**: represent a persona as a structured, versioned configuration (not a one-line bio).
- **Cross-Platform Adaptation**: translate one persona into platform-native styles (e.g., Xiaohongshu vs. Twitter/X vs. Reddit).
- **Offline Simulation**: simulate “what could happen after posting” (expected engagement, comment topics, risk flags) before going live.
- **Experiment & Learning Loop**: run experiments, collect feedback, and update persona/content strategies with traceability.
- **Monetization Readiness (Later)**: mine recurring demands from interactions to inform future offers/products—without locking into a product too early.

---

## What It Does (MVP)

### 1) Persona Lab
- Persona schema (identity, audience, voice, content pillars, boundaries, credibility strategy)
- Persona versioning (why changed, what changed, expected impact)

### 2) Content Lab
- Column / template-based content generation (checklists, how-tos, pitfalls, stories, Q&A)
- Multi-variant generation (same topic → multiple structures/titles)
- Style constraints to keep persona consistency

### 3) Review & Compliance Layer
- Persona consistency scoring
- Platform fit scoring
- Compliance & risk checks (sensitive claims, spammy CTAs, risky phrasing)

### 4) Simulation Lab
- Predict engagement ranges (rough estimates for ranking and comparison)
- Generate “comment scripts” (what users might ask/argue)
- Suggest engagement replies (human review recommended)

### 5) Experiment Dashboard
- Compare runs by persona/pillar/platform
- Weekly retrospectives: what worked, what didn’t, what to try next

---

## Non-Goals (By Design)

- No built-in “mass automation” (auto-login, auto-follow, auto-like, auto-comment spamming).
- No promise of guaranteed virality or sales.
- No support for deceptive identity claims or fake credentials.

AvatarFactory aims to be **compliance-aware** and **strategy-first**.

---

## Roadmap

- **Phase 1 (MVP)**: persona schema + content generation + multi-critic scoring + offline simulation + basic experiment tracking
- **Phase 2**: platform adapters (XHS first), metrics import/export, better evaluation models
- **Phase 3**: cross-platform transfer learning, demand mining, offer suggestion engine
- **Phase 4**: pluggable tool ecosystem (MCP tools / skills), multi-agent workflows

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
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Setup AvatarFactory
- ✅ Verify installation

📖 See [Virtual Environment Guide](docs/venv-guide.md) for manual setup.

---

**Alternative: Direct install**

```bash
# Clone the repository
git clone https://github.com/yourusername/AvatarFactory.git
cd AvatarFactory

# Install all dependencies
pip install -r requirements.txt

# Or install based on your LLM provider:
pip install -r requirements-minimal.txt  # Anthropic Claude only
pip install -r requirements-azure.txt    # Azure OpenAI
pip install -r requirements-openai.txt   # OpenAI

# Or using poetry
poetry install
```

📖 See [Installation Guide](docs/installation.md) for detailed options.

### Setup

1. Create a `.env` file from the example:
```bash
cp .env.example .env
```

2. Configure your LLM provider:

**Option A: Anthropic Claude (Default)**
```bash
# .env
AVATARFACTORY_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_api_key_here
```

**Option B: Azure OpenAI**
```bash
# .env
AVATARFACTORY_LLM_PROVIDER=azure_openai
AVATARFACTORY_MODEL=gpt-4
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/

# Install OpenAI package
pip install openai
```

**Option C: OpenAI**
```bash
# .env
AVATARFACTORY_LLM_PROVIDER=openai
AVATARFACTORY_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your_key

# Install OpenAI package
pip install openai
```

📖 See [LLM Providers Guide](docs/llm-providers.md) for detailed configuration.

### Quick Start

**Interactive Chat (Recommended):**
```bash
avatarfactory chat
```

Then talk naturally:
```
You: Create a persona for an AI tools reviewer targeting product managers
You: Generate content about Notion vs Obsidian comparison
```

**Quick Commands:**
```bash
# Create a persona
avatarfactory create-persona "AI tools expert for product managers"

# Generate content
avatarfactory generate "Notion vs Obsidian comparison"

# List personas
avatarfactory list-personas

# Show stats
avatarfactory stats
```

### Documentation

- 📖 [Quick Start Guide](docs/quickstart.md) - Detailed getting started guide
- 🏗️ [Architecture Design](docs/architecture.md) - System architecture and agent design
- 💡 [Examples](examples/) - Code examples and tutorials

---

## Project Structure

```
avatarfactory/
├── agents/          # AI agents (Persona Lab, Content Lab, Review, etc.)
├── core/            # Core functionality (Knowledge Base)
├── models/          # Data models (Pydantic schemas)
├── utils/           # Utility functions
├── templates/       # Content templates
├── adapters/        # Platform adapters
└── cli.py           # Command-line interface

knowledge_base/      # User data storage
├── personas/        # Persona configurations
├── content_library/ # Generated content
├── experiments/     # Experiment data
└── platform_rules/  # Platform-specific rules
```

---

## Current Status (v0.1.0 - MVP)

✅ **Implemented:**
- Persona creation and versioning
- Content generation with multiple variants
- Multi-dimensional review system
- Compliance checking
- CLI interface with natural language
- Knowledge base storage

🚧 **Coming Soon:**
- Simulation Lab (engagement prediction)
- Experiment tracking and analytics
- Platform adapters (XHS, Zhihu, Twitter)
- Web UI
- Advanced optimization algorithms

---

## Contributing

Contributions are welcome! This is an early-stage project. Feel free to:
- Report bugs and issues
- Suggest new features
- Submit pull requests
- Improve documentation

---

## License

MIT License - see [LICENSE](LICENSE) for details.