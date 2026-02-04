# Installation Guide

AvatarFactory supports multiple LLM providers (Anthropic Claude, Azure OpenAI, OpenAI).

---

## Quick Install

### Standard Installation

```bash
pip install -r requirements.txt
```

This installs all dependencies including support for all LLM providers.

---

### Development Installation

```bash
pip install -r requirements-dev.txt
```

This includes testing and code quality tools (pytest, black, ruff, mypy).

---

## Virtual Environment Setup (Recommended)

### Windows

```powershell
# PowerShell
.\setup_venv.ps1

# Or CMD
setup_venv.bat
```

### macOS/Linux

```bash
chmod +x setup_venv.sh
./setup_venv.sh
```

### Manual Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

---

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Configure your LLM provider in `.env`:

**Anthropic Claude (Default)**
```bash
AVATARFACTORY_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
```

**Azure OpenAI**
```bash
AVATARFACTORY_LLM_PROVIDER=azure_openai
AVATARFACTORY_MODEL=gpt-4
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

**OpenAI**
```bash
AVATARFACTORY_LLM_PROVIDER=openai
AVATARFACTORY_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your_key
```

---

## Verify Installation

```bash
# Check version
avatarfactory version

# Run tests
pytest tests/ -v
```

---

## Troubleshooting

### Import Errors
```bash
pip install -e .
```

### API Key Issues
Ensure your `.env` file is in the project root and contains valid API keys.

### Windows Unicode Issues
The CLI automatically handles Windows console encoding. If you see garbled characters, try running in Windows Terminal instead of CMD.

---

## Next Steps

- [Quick Start Guide](quickstart.md) - Get started with AvatarFactory
- [LLM Providers](llm-providers.md) - Detailed provider configuration
