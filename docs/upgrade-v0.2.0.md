# AvatarFactory v0.2.0 - Multi-LLM Support Update

## 🎉 What's New

AvatarFactory now supports multiple LLM providers:
- ✅ **Anthropic Claude** (existing, default)
- ✅ **Azure OpenAI** (new)
- ✅ **OpenAI** (new)

---

## 📦 Changes

### New Files
- `avatarfactory/core/llm_provider.py` - LLM provider abstraction layer
- `docs/llm-providers.md` - Complete LLM configuration guide
- `tests/test_llm_provider.py` - Provider testing script

### Modified Files
- `avatarfactory/agents/base.py` - Now uses `llm_provider` instead of `anthropic_client`
- `avatarfactory/agents/orchestrator.py` - Updated to use new provider system
- `.env.example` - Added configuration for all providers
- `pyproject.toml` - Added optional `openai` dependency
- `README.md` - Updated setup instructions

---

## ✅ Migration Guide (Existing Users)

### If you're using Anthropic Claude (no changes needed!)

Your existing setup will continue to work. The system is **backward compatible**.

**Your current .env:**
```bash
ANTHROPIC_API_KEY=sk-ant-xxxxx...
```

**This still works!** The system auto-detects Anthropic as the provider.

### To switch to Azure OpenAI:

1. **Install OpenAI package:**
   ```bash
   pip install openai
   ```

2. **Update .env:**
   ```bash
   AVATARFACTORY_LLM_PROVIDER=azure_openai
   AVATARFACTORY_MODEL=gpt-4
   AZURE_OPENAI_API_KEY=your_azure_key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   ```

3. **That's it!** No code changes needed.

### To switch to OpenAI:

1. **Install OpenAI package:**
   ```bash
   pip install openai
   ```

2. **Update .env:**
   ```bash
   AVATARFACTORY_LLM_PROVIDER=openai
   AVATARFACTORY_MODEL=gpt-4-turbo-preview
   OPENAI_API_KEY=sk-xxxxx...
   ```

3. **Done!**

---

## 🧪 Testing Your Setup

Run the test script to verify your configuration:

```bash
python tests/test_llm_provider.py
```

Expected output:
```
============================================================
AvatarFactory LLM Provider Test
============================================================

1️⃣  Detecting provider from environment...
   ✅ Provider: AzureOpenAIProvider
   ✅ Model: gpt-4

2️⃣  Validating configuration...
   ✅ Configuration is valid

3️⃣  Testing text generation...
   Sending test prompt...
   ✅ Response received: Hello from AvatarFactory!

4️⃣  Testing with system prompt...
   ✅ Response: The answer is 4.

============================================================
✅ All tests passed! Your LLM provider is working correctly.
============================================================
```

---

## 💡 Usage Examples

### CLI (no changes)
```bash
avatarfactory chat
avatarfactory create-persona "..."
avatarfactory generate "..."
```

### Python API (backward compatible)
```python
# Old way (still works)
from anthropic import Anthropic
from avatarfactory.agents.orchestrator import OrchestratorAgent
from avatarfactory.core.knowledge_base import KnowledgeBase

kb = KnowledgeBase()
client = Anthropic()
orchestrator = OrchestratorAgent(
    knowledge_base=kb,
    anthropic_client=client,  # Still supported
    model="claude-3-5-sonnet-20241022"
)

# New way (recommended)
from avatarfactory.core.llm_provider import LLMProviderFactory
from avatarfactory.agents.orchestrator import OrchestratorAgent
from avatarfactory.core.knowledge_base import KnowledgeBase

kb = KnowledgeBase()
provider = LLMProviderFactory.from_env()  # Auto-detects from .env
orchestrator = OrchestratorAgent(
    knowledge_base=kb,
    llm_provider=provider
)
```

---

## 🔧 For Developers

### Adding a new LLM provider

1. Create a class inheriting from `BaseLLMProvider`
2. Implement `generate()` and `validate_config()` methods
3. Register in `LLMProviderFactory._providers`

Example:
```python
class MyCustomProvider(BaseLLMProvider):
    def __init__(self, model: str = "my-model", **kwargs):
        super().__init__(model)
        # Initialize your client

    async def generate(self, prompt: str, system: Optional[str] = None,
                      temperature: float = 1.0, max_tokens: int = 4096) -> str:
        # Your generation logic
        pass

    def validate_config(self) -> bool:
        # Check if required config is present
        return True

# Register
LLMProviderFactory._providers["my_custom"] = MyCustomProvider
```

---

## 📊 Provider Comparison

| Provider | Pros | Cons |
|----------|------|------|
| **Anthropic Claude** | Best reasoning, long context, great JSON output | Higher cost |
| **Azure OpenAI** | Enterprise features, regional deployment | Setup complexity |
| **OpenAI** | Easy to start, wide model selection | Rate limits |

---

## ❓ FAQ

**Q: Do I need to change my code?**
A: No! Existing code continues to work. The update is backward compatible.

**Q: Can I use multiple providers in one project?**
A: Yes! Create different provider instances:
```python
claude = LLMProviderFactory.create("anthropic")
gpt4 = LLMProviderFactory.create("azure_openai", model="gpt-4")
```

**Q: Which provider should I use?**
A: For AvatarFactory, we recommend:
- **Development**: Claude Haiku or GPT-3.5 (cheap)
- **Production**: Claude Sonnet or GPT-4 (quality)
- **Enterprise**: Azure OpenAI (compliance)

**Q: Will this affect my costs?**
A: Only if you switch providers. Check [llm-providers.md](llm-providers.md) for pricing.

**Q: What if I don't have an Azure/OpenAI account?**
A: Keep using Anthropic Claude! No changes needed.

---

## 🚀 Next Steps

1. ✅ Read [llm-providers.md](llm-providers.md) for full documentation
2. ✅ Run `python tests/test_llm_provider.py` to test your setup
3. ✅ Update `.env` if you want to use a different provider
4. ✅ Continue using AvatarFactory as before!

---

## 🐛 Troubleshooting

**"openai module not found"**
```bash
pip install openai
```

**"Provider not configured"**
- Check `.env` file exists
- Verify API key is set
- For Azure: check endpoint URL is correct

**Still having issues?**
- Run: `python tests/test_llm_provider.py`
- Check logs for detailed error messages
- Open an issue on GitHub

---

## 📝 Version Info

- **Version**: 0.2.0
- **Release Date**: 2026-02-02
- **Breaking Changes**: None (backward compatible)
- **New Dependencies**: `openai` (optional)

---

**Enjoy multi-LLM support!** 🎉
