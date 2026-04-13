# Support & Troubleshooting

## Documentation

- [Getting Started](../docs/getting-started.md) — Installation and first run
- [Configuration](../docs/configuration.md) — LLM providers and environment variables
- [Architecture](../docs/architecture.md) — System design
- [Connector Guides](../docs/connectors/README.md) — Platform-specific setup

---

## Common Issues

### Installation

**"ANTHROPIC_API_KEY not found"**
- Make sure `.env` file exists in the project root
- Check that there are **no quotes** around the key:
  ```bash
  # ✅ Correct
  ANTHROPIC_API_KEY=sk-ant-xxxxx...
  # ❌ Wrong
  ANTHROPIC_API_KEY="sk-ant-xxxxx..."
  ```
- Try exporting directly: `export ANTHROPIC_API_KEY=your_key` (Mac/Linux)

**"Command not found: avatarfactory"**
```bash
# Ensure you installed in dev mode:
pip install -e .

# Or run directly:
python -m avatarfactory.cli chat

# Check PATH includes pip install location:
where avatarfactory  # Windows
which avatarfactory  # Mac/Linux
```

**"Module not found" errors**
```bash
# Reinstall:
pip install -e . --force-reinstall

# Verify Python version (must be 3.10+):
python --version

# Make sure virtual environment is active
```

**Unicode/encoding errors on Windows**
- Use Windows Terminal instead of CMD
- The CLI automatically handles UTF-8 encoding

---

### API / Content Generation

**"Content generation fails"**
- Check internet connection (needs LLM API access)
- Verify API key is valid
- Check API credits/quota
- Verify `AVATARFACTORY_LLM_PROVIDER` in `.env`

**"Low review scores (<70)"**
- This is normal — scores are intentionally strict
- Read the review report suggestions
- Adjust persona parameters and try again

**"Provider not configured correctly"**
- Check API key is set in `.env`
- Verify environment variable names match your provider
- For Azure: ensure endpoint URL is correct and includes `https://`

---

### Platform Connectors

**Bluesky connection fails**
- Use an **app password**, not your main password
- Create one at: https://bsky.app/settings/app-passwords
- Format: `BLUESKY_USERNAME=your.handle.bsky.social`

**Xiaohongshu "Cookie expired"**
- Cookies expire — refresh from browser
- Open DevTools → Application → Cookies → xiaohongshu.com
- Copy entire cookie string to `.env`

**Twitter API authentication errors**
- Verify you have API v2 (not v1.1) credentials
- Check token permissions match required scopes
- Confirm API access tier supports your usage

**WeChat Work notification fails**
- Verify webhook URL is correct
- Check `AVATARFACTORY_WEBHOOK_FORMAT` matches your platform
- Ensure internet access to WeChat API

---

## Verify Your Installation

Run the verification script:

```bash
python verify_install.py
```

This checks: Python version, dependencies, LLM API connection, knowledge base access, and agent loading.

---

## Reporting Issues

When opening a GitHub Issue, please include:

1. **Environment**
   ```
   Python version: (python --version)
   OS: Windows / macOS / Linux
   LLM Provider: Anthropic / Azure OpenAI / OpenAI
   ```

2. **Steps to reproduce** — exact commands and input

3. **Error message** — full traceback or screenshot

4. **Configuration** — relevant `.env` values (redact API keys!)

---

## Still Stuck?

1. Search [existing Issues](https://github.com/EldonZhao/AvatarFactory/issues)
2. Run `python verify_install.py` for diagnostics
3. Open a new Issue with the details above
