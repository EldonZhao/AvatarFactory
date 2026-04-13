# Troubleshooting

Common issues and solutions for AvatarFactory.

---

## Installation

### "ANTHROPIC_API_KEY not found"

- Ensure `.env` file exists in the project root
- No quotes around the key value:
  ```bash
  # ✅ Correct
  ANTHROPIC_API_KEY=sk-ant-xxxxx...
  # ❌ Wrong
  ANTHROPIC_API_KEY="sk-ant-xxxxx..."
  ```
- Try exporting directly: `export ANTHROPIC_API_KEY=your_key`

### "Command not found: avatarfactory"

```bash
pip install -e .
# Or run directly:
python -m avatarfactory.cli chat
```

### "Module not found" errors

```bash
pip install -e . --force-reinstall
python --version  # Must be 3.10+
```

### Unicode/encoding errors on Windows

- Use Windows Terminal instead of CMD
- The CLI handles UTF-8 encoding automatically

---

## LLM / Content Generation

### "Provider not configured correctly"

- Check `AVATARFACTORY_LLM_PROVIDER` matches your API key type
- For Azure: verify endpoint URL includes `https://`
- For Azure: use your **deployment name** as `AVATARFACTORY_MODEL`, not the OpenAI model name

### "Model not found"

- Azure: use deployment name, not model name
- Check model availability in your region/subscription

### "Rate limit exceeded"

- Reduce request frequency
- Use a cheaper model for testing (Haiku, GPT-3.5)
- Check your API quota/limits

### Content generation fails

- Check internet connection
- Verify API key is valid and has credits
- Check LLM provider setting in `.env`

### Low review scores (<70)

- This is expected — scores are intentionally strict
- Read the review report for specific suggestions
- Adjust persona parameters and regenerate

---

## Platform Connectors

### Bluesky connection fails

- Use an **app password**, not your main password
- Create at: https://bsky.app/settings/app-passwords
- Format: `BLUESKY_USERNAME=your.handle.bsky.social`

### Xiaohongshu "Cookie expired"

- Cookies expire periodically — refresh from browser
- DevTools → Application → Cookies → xiaohongshu.com
- Copy entire cookie string to `.env`

### Twitter API errors

- Verify API v2 (not v1.1) credentials
- Check token permissions and scopes
- Confirm API access tier supports your usage

### LinkedIn token expired

- OAuth 2.0 tokens are valid for 60 days
- Regenerate at https://www.linkedin.com/developers/tools/oauth
- Update `LINKEDIN_ACCESS_TOKEN` in `.env`

### WeChat Work notification fails

- Verify webhook URL format
- Check `AVATARFACTORY_WEBHOOK_FORMAT` setting
- Ensure network access to WeChat API

---

## Service / Deployment

### Backend 404 on API endpoints

- Verify the backend is running: `curl http://127.0.0.1:8000/health`
- If using web-admin frontend, ensure it proxies to the correct backend port
- Default backend port is 8000

### Docker container not starting

```bash
docker-compose logs -f  # Check logs
```

### Azure: new image not deployed after restart

```bash
# Use stop/start instead of restart:
az webapp stop -g avatarfactory-rg -n avatarfactory-app
az webapp start -g avatarfactory-rg -n avatarfactory-app
```

### Azure CLI encoding error on Windows

```powershell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

---

## Performance

### Content generation is slow

- LLM API calls are sequential — this is expected
- First call to an agent has warmup overhead
- Use faster models (Haiku, GPT-3.5) for development

### Service startup is slow

- APScheduler cold-start: ~5-10s
- FastAPI startup: ~10-15s
- Docker container: ~15-30s

---

## Diagnostics

Run the verification script to check your entire setup:

```bash
python scripts/verify_install.py
```

This verifies: Python version, dependencies, LLM connection, knowledge base, and agent loading.

---

## Still Stuck?

1. Search [GitHub Issues](https://github.com/EldonZhao/AvatarFactory/issues)
2. Check the [interactive API docs](http://localhost:8000/docs) for endpoint details
3. Open a new Issue with environment info, steps to reproduce, and error output
