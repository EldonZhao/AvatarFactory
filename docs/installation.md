# Installation Guide

AvatarFactory provides multiple installation options depending on your needs and LLM provider choice.

---

## Quick Install (Recommended)

### Option 1: Full Installation (All Features)

```bash
pip install -r requirements.txt
```

This installs everything including support for all LLM providers (Anthropic, Azure OpenAI, OpenAI).

---

### Option 2: Minimal Installation (Anthropic Claude only)

```bash
pip install -r requirements-minimal.txt
```

This installs only the essential packages for using Anthropic Claude (default provider).

**Best for:** Production deployments with Anthropic Claude

---

### Option 3: Azure OpenAI

```bash
pip install -r requirements-azure.txt
```

This installs minimal requirements + OpenAI package for Azure OpenAI support.

**Best for:** Enterprise users with Azure OpenAI

---

### Option 4: OpenAI

```bash
pip install -r requirements-openai.txt
```

This installs minimal requirements + OpenAI package for OpenAI API support.

**Best for:** Users with OpenAI API keys

---

### Option 5: Development

```bash
pip install -r requirements-dev.txt
```

This installs everything including testing and development tools.

**Best for:** Contributors and developers

---

## Alternative: Using Poetry

If you prefer Poetry for dependency management:

```bash
# Install base dependencies
poetry install

# Install with OpenAI support
poetry install -E openai

# Install with all extras
poetry install -E all-llm

# Install for development
poetry install --with dev
```

---

## Editable Installation

For development or if you want to modify the code:

```bash
pip install -e .
```

Or with a specific requirements file:

```bash
pip install -e . -r requirements-azure.txt
```

---

## Verifying Installation

After installation, verify it works:

```bash
# Check version
avatarfactory version

# Test your LLM configuration
python tests/test_llm_provider.py

# Start interactive mode
avatarfactory chat
```

---

## Requirements Files Summary

| File | Contents | Use Case |
|------|----------|----------|
| `requirements.txt` | All packages (Anthropic + OpenAI + LangChain) | Full features, all providers |
| `requirements-minimal.txt` | Essential packages only (Anthropic) | Production, Claude only |
| `requirements-azure.txt` | Minimal + OpenAI for Azure | Azure OpenAI users |
| `requirements-openai.txt` | Minimal + OpenAI for OpenAI API | OpenAI users |
| `requirements-dev.txt` | All + dev tools (pytest, black, etc.) | Development & testing |

---

## Platform-Specific Notes

### Windows

```bash
# Use regular pip commands
pip install -r requirements.txt
```

### macOS / Linux

```bash
# You might need pip3
pip3 install -r requirements.txt

# Or use python -m pip
python -m pip install -r requirements.txt
```

### Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install
pip install -r requirements.txt
```

---

## Troubleshooting

### "Command not found: avatarfactory"

Solution:
```bash
# Reinstall in editable mode
pip install -e .
```

### "Module not found: openai"

For Azure OpenAI or OpenAI users:
```bash
pip install openai
```

### "Dependency conflict"

Try upgrading pip first:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Fresh install

```bash
# Uninstall everything
pip uninstall -y avatarfactory anthropic openai pydantic typer rich

# Reinstall
pip install -r requirements.txt
```

---

## Upgrading

### Upgrade all packages

```bash
pip install --upgrade -r requirements.txt
```

### Upgrade specific package

```bash
pip install --upgrade anthropic
pip install --upgrade openai
```

---

## Docker Installation (Future)

Coming soon! We'll provide a Dockerfile for containerized deployment.

---

## Next Steps

After installation:

1. **Configure**: Create `.env` file from `.env.example`
2. **Setup**: Add your API keys to `.env`
3. **Test**: Run `python tests/test_llm_provider.py`
4. **Use**: Run `avatarfactory chat`

See [quickstart.md](quickstart.md) for detailed usage guide.

---

## Support

- Installation issues? Check [Troubleshooting](#troubleshooting)
- LLM configuration? See [llm-providers.md](llm-providers.md)
- General questions? See [README.md](../README.md)
