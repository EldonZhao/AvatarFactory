# Multi-LLM Support Configuration Guide

AvatarFactory now supports multiple LLM providers! You can use:
- **Anthropic Claude** (default)
- **Azure OpenAI**
- **OpenAI**

---

## Quick Start

### 1. Choose Your Provider

Edit your `.env` file and set `AVATARFACTORY_LLM_PROVIDER`:

```bash
# Options: anthropic | azure_openai | openai
AVATARFACTORY_LLM_PROVIDER=anthropic
```

### 2. Configure API Keys

Based on your provider choice:

---

## Option 1: Anthropic Claude (Default)

**Advantages:**
- Best reasoning capabilities
- Long context windows
- Excellent at structured output (JSON)

**Configuration:**

```bash
# .env
AVATARFACTORY_LLM_PROVIDER=anthropic
AVATARFACTORY_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-xxxxx...
```

**Get API Key:**
https://console.anthropic.com/

**Recommended Models:**
- `claude-3-5-sonnet-20241022` - Best for complex reasoning
- `claude-3-5-haiku-20241022` - Faster, cheaper
- `claude-opus-4-5-20251101` - Most powerful (if available)

---

## Option 2: Azure OpenAI

**Advantages:**
- Enterprise-grade security
- Regional deployment options
- Integrated with Azure ecosystem

**Configuration:**

```bash
# .env
AVATARFACTORY_LLM_PROVIDER=azure_openai
AVATARFACTORY_MODEL=gpt-4
AZURE_OPENAI_API_KEY=your_azure_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

**Setup Steps:**

1. Create an Azure OpenAI resource in Azure Portal
2. Deploy a model (e.g., gpt-4, gpt-35-turbo)
3. Copy your endpoint and key
4. Set the deployment name as `AVATARFACTORY_MODEL`

**Recommended Models:**
- `gpt-4` - Best quality
- `gpt-4-turbo` - Faster inference
- `gpt-35-turbo` - Cost-effective

**Installation:**
```bash
pip install openai
# Or with poetry:
poetry install -E azure
```

---

## Option 3: OpenAI

**Advantages:**
- Easy to get started
- Pay-as-you-go pricing
- Wide model selection

**Configuration:**

```bash
# .env
AVATARFACTORY_LLM_PROVIDER=openai
AVATARFACTORY_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=sk-xxxxx...
```

**Get API Key:**
https://platform.openai.com/api-keys

**Recommended Models:**
- `gpt-4-turbo-preview` - Latest GPT-4
- `gpt-4` - Stable GPT-4
- `gpt-3.5-turbo` - Fast and cheap

**Installation:**
```bash
pip install openai
# Or with poetry:
poetry install -E openai
```

---

## Switching Between Providers

You can easily switch providers by changing environment variables:

### Method 1: Edit .env file
```bash
# From Anthropic to Azure
AVATARFACTORY_LLM_PROVIDER=azure_openai
AVATARFACTORY_MODEL=gpt-4
```

### Method 2: Environment variable override
```bash
# Temporary override for one session
export AVATARFACTORY_LLM_PROVIDER=openai
export AVATARFACTORY_MODEL=gpt-4-turbo-preview
avatarfactory chat
```

---

## Testing Your Configuration

### Check if configuration is valid:

```bash
python -c "
from avatarfactory.core.llm_provider import LLMProviderFactory
provider = LLMProviderFactory.from_env()
print(f'✅ Using: {provider.__class__.__name__}')
print(f'✅ Model: {provider.model}')
print(f'✅ Config valid: {provider.validate_config()}')
"
```

### Test generation:

```bash
avatarfactory chat
> Hello
```

If you get a response, your LLM is configured correctly!

---

## Programmatic Usage

```python
from avatarfactory.core.llm_provider import LLMProviderFactory

# Option 1: Auto-detect from environment
provider = LLMProviderFactory.from_env()

# Option 2: Explicit creation
provider = LLMProviderFactory.create(
    "azure_openai",
    model="gpt-4",
    endpoint="https://your-resource.openai.azure.com/",
    api_key="your_key"
)

# Option 3: Direct instantiation
from avatarfactory.core.llm_provider import AzureOpenAIProvider
provider = AzureOpenAIProvider(
    model="gpt-4",
    api_key="your_key",
    endpoint="https://your-resource.openai.azure.com/"
)

# Use with agents
from avatarfactory.core.knowledge_base import KnowledgeBase
from avatarfactory.agents.orchestrator import OrchestratorAgent

kb = KnowledgeBase("./knowledge_base")
orchestrator = OrchestratorAgent(
    knowledge_base=kb,
    llm_provider=provider
)
```

---

## Cost Comparison (Approximate)

| Provider | Model | Input (per 1M tokens) | Output (per 1M tokens) |
|----------|-------|----------------------|------------------------|
| Anthropic | Claude 3.5 Sonnet | $3 | $15 |
| Anthropic | Claude 3.5 Haiku | $0.80 | $4 |
| Azure/OpenAI | GPT-4 Turbo | $10 | $30 |
| Azure/OpenAI | GPT-3.5 Turbo | $0.50 | $1.50 |

*Prices as of Jan 2025, subject to change*

---

## Performance Considerations

**For AvatarFactory:**

- **Best Quality**: Claude 3.5 Sonnet or GPT-4 Turbo
- **Best Speed**: Claude 3.5 Haiku or GPT-3.5 Turbo
- **Best Value**: Claude 3.5 Haiku (good quality + low cost)

**Recommended Setup:**
```bash
# Use Sonnet for main tasks, Haiku for quick operations
AVATARFACTORY_MODEL=claude-3-5-sonnet-20241022
AVATARFACTORY_FAST_MODEL=claude-3-5-haiku-20241022
```

---

## Troubleshooting

### "Provider not configured correctly"
- Check API key is set in `.env`
- Verify environment variable names are correct
- For Azure: ensure endpoint URL is correct

### "Model not found"
- For Azure: use your deployment name, not OpenAI's model name
- Check model is available in your region/subscription

### "Import error: openai not installed"
- Install: `pip install openai`
- Or: `poetry install -E openai`

### "Rate limit exceeded"
- Reduce request frequency
- Use cheaper/faster model for testing
- Check your API quota/limits

---

## Migration Guide

### From Anthropic-only to Multi-LLM

No code changes needed! Just:

1. Update `.env` with new provider
2. Install additional dependencies if needed
3. Restart your application

The system will automatically detect and use the new provider.

---

## Best Practices

1. **Development**: Use cheaper models (Haiku, GPT-3.5)
2. **Production**: Use best models (Sonnet, GPT-4)
3. **Testing**: Mock LLM calls to avoid costs
4. **Fallback**: Configure multiple providers for redundancy
5. **Monitoring**: Track token usage and costs

---

## Future Providers

We plan to add support for:
- Google Gemini
- Cohere
- Local models (Ollama, LM Studio)
- Custom endpoints

Want to contribute? See `avatarfactory/core/llm_provider.py` for the provider interface!

---

## Questions?

- Check `.env.example` for all configuration options
- Read `docs/architecture.md` for system design
- Report issues at GitHub
