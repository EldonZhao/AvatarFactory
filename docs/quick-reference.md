# AvatarFactory - Quick Reference

## 🚀 Installation

```bash
# Install all dependencies
pip install -r requirements.txt

# For development (includes testing tools)
pip install -r requirements-dev.txt
```

---

## ⚙️ Configuration

**Edit `.env` file:**

### Anthropic Claude (Default)
```bash
AVATARFACTORY_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx...
```

### Azure OpenAI
```bash
AVATARFACTORY_LLM_PROVIDER=azure_openai
AVATARFACTORY_MODEL=gpt-4
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
```

### OpenAI
```bash
AVATARFACTORY_LLM_PROVIDER=openai
AVATARFACTORY_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=sk-xxxxx...
```

---

## 💬 Usage

### Interactive Mode
```bash
avatarfactory chat
```

### Quick Commands
```bash
# Create persona
avatarfactory create-persona "AI tools expert"

# Generate content
avatarfactory generate "Topic here"

# List personas
avatarfactory list-personas

# List content
avatarfactory list-content

# Show stats
avatarfactory stats
```

---

## 🧪 Testing

```bash
# Test LLM configuration
python tests/test_llm_provider.py

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/unit/test_knowledge_base.py -v
```

---

## 📂 File Locations

```
.env                    # Your configuration
knowledge_base/         # All your data
  personas/            # Persona configs
  content_library/     # Generated content
  experiments/         # Experiment data
```

---

## 📚 Documentation

- **[installation.md](installation.md)** - Detailed installation guide
- **[llm-providers.md](llm-providers.md)** - LLM configuration
- **[quickstart.md](quickstart.md)** - Getting started tutorial
- **[architecture.md](architecture.md)** - System architecture

---

## 🆘 Common Issues

**"avatarfactory: command not found"**
```bash
pip install -e .
```

**"openai module not found"**
```bash
pip install openai
```

**"API key not found"**
```bash
# Check .env file exists and has your API key
cat .env
```

---

## 📞 Support

- GitHub Issues: Report bugs
- Documentation: Check docs/ folder
- Test script: `python tests/test_llm_provider.py`

---

**Quick Start:**
1. `pip install -r requirements.txt`
2. Edit `.env` with your API key
3. `avatarfactory chat`
4. Start creating! 🎭
