# Security Policy

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Please report security issues via email to the maintainer. Include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a timeline for resolution.

---

## Compliance-First Design

AvatarFactory has compliance built into its review system. The ReviewAgent scores all content on four dimensions, including a dedicated **Compliance** score (0-100) that checks for:

- Sensitive words detection
- Misleading claims detection
- Spam pattern detection
- Platform policy adherence
- Sensitive topic detection (varies by platform)

---

## Authentication & Credentials

### API Keys

- Keep all API keys in `.env` file — **never commit `.env`**
- `.env` is already in `.gitignore`
- Use `.env.example` as a template with placeholder values
- Rotate keys regularly

### Platform Credentials

| Platform | Auth Method | Notes |
|----------|-------------|-------|
| Bluesky | App password | Use [app-specific passwords](https://bsky.app/settings/app-passwords), not your main password |
| Twitter/X | OAuth 2.0 API keys | Scoped to specific apps |
| Xiaohongshu | Browser cookie | Cookies expire — refresh from browser when needed |
| LinkedIn | OAuth 2.0 token | Token valid for 60 days |
| WeChat Work | Webhook URL | System-level, used for notifications only |

### Best Practices

```bash
# ✅ DO: Use .env.example as template
cp .env.example .env

# ✅ DO: Check .gitignore includes .env
grep ".env" .gitignore

# ❌ DON'T: Commit real credentials
# ❌ DON'T: Log sensitive values in output
# ❌ DON'T: Share API keys across environments
```

---

## Deployment Security

### Azure Deployment
- Uses GitHub Actions secrets for Azure credentials
- Health checks verify deployment before marking complete
- Automatic rollback on health check failure

### Docker
- Container builds run in isolated GitHub Actions environment
- Images pushed to GitHub Container Registry
- Attestation included for supply chain security

---

## Data Privacy

- All personas and content stored locally in `knowledges/` folder
- No telemetry or usage tracking
- LLM provider privacy depends on your choice:
  - **Anthropic**: [Usage policy](https://www.anthropic.com/policies)
  - **Azure OpenAI**: Enterprise data protection
  - **OpenAI**: [API data usage policy](https://openai.com/policies)

---

## Dependency Security

Before deploying, check for known vulnerabilities:

```bash
pip-audit
```

Keep dependencies up to date and monitor for security advisories.
