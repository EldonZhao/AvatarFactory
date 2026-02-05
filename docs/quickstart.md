# AvatarFactory Quick Start

## Installation

1. Install dependencies:
```bash
# Using pip
pip install -e .

# Or for service deployment
pip install -e ".[service]"
```

2. Set up your API key:
```bash
# Create .env file
cp .env.example .env

# Edit .env and add your API key
AVATARFACTORY_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
```

## Usage

### CLI Mode (Recommended for beginners)

#### Interactive Chat
```bash
avatarfactory chat
```

Then talk naturally:
```
You: Create a persona for an AI tools reviewer targeting product managers
You: Generate content about Notion vs Obsidian comparison
You: Discover trending topics on Bluesky
You: Show me my personas
```

#### Quick Commands

Create a persona:
```bash
avatarfactory create-persona "AI tools expert for product managers" --platform xiaohongshu
```

Generate content:
```bash
avatarfactory generate "Notion vs Obsidian comparison" --persona persona_abc123
```

Discover trending content:
```bash
avatarfactory discover --platform bluesky --limit 20
```

List personas:
```bash
avatarfactory list-personas
```

List content:
```bash
avatarfactory list-content --status draft
```

Show content details:
```bash
avatarfactory show-content content_abc123
```

Publish to platform:
```bash
avatarfactory publish-draft content_abc123 --platform bluesky
```

Show statistics:
```bash
avatarfactory stats
```

### Service Mode (Production)

Start the HTTP service:
```bash
avatarfactory serve --host 0.0.0.0 --port 8000
```

Or run as background daemon:
```bash
avatarfactory daemon start --background
```

API endpoints available at `http://localhost:8000/docs`

### Docker Deployment

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f
```

### Python API

See `examples/quickstart.py` for a complete example.

```python
import asyncio
from avatarfactory import OrchestratorAgent, KnowledgeBase
from avatarfactory.core.llm_provider import LLMProviderFactory

async def main():
    kb = KnowledgeBase("./knowledges")
    llm = LLMProviderFactory.from_env()
    orchestrator = OrchestratorAgent(knowledge_base=kb, llm_provider=llm)

    # Talk to orchestrator naturally
    result = await orchestrator._handle_user_input(
        "Create a persona for AI tools reviewer"
    )
    print(result)

asyncio.run(main())
```

## Typical Workflow

1. **Create a Persona**
   ```bash
   avatarfactory chat
   > Create a persona for an AI productivity tools expert targeting freelancers on Xiaohongshu
   ```

2. **Review Persona** (automatic during creation)
   - Check validation score
   - Review sample content
   - Adjust if needed

3. **Discover Trends** (optional but recommended)
   ```bash
   > Discover trending topics on Bluesky for AI tools
   ```

4. **Generate Content**
   ```bash
   > Generate content about "Top 5 AI tools for freelancers in 2024"
   ```

5. **Review Content** (automatic after generation)
   - Check review score
   - Read suggestions
   - Revise if score < 70

6. **Publish**
   ```bash
   > Publish content_abc123 to Bluesky
   ```
   Or manually copy content to platform.

7. **Track Results** (optional)
   - Record engagement metrics
   - Analyze trends
   - Optimize persona

## Platform Connectors

### Bluesky (Recommended for getting started)
```bash
# .env
BLUESKY_USERNAME=your.handle.bsky.social
BLUESKY_PASSWORD=your-app-password
```

### Xiaohongshu (小红书)
```bash
# .env - Get cookie from browser DevTools
XIAOHONGSHU_COOKIE=your_full_cookie_string
XIAOHONGSHU_USER_ID=your_user_id
```

### Twitter/X
```bash
# .env
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET=your_api_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
```

### WeChat Work (for notifications)
```bash
# .env
AVATARFACTORY_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY
AVATARFACTORY_WEBHOOK_FORMAT=wecom
```

## Tips

- **Start simple**: Create one persona, generate a few pieces of content
- **Review scores**: Aim for 70+ for publishable content
- **Use discovery**: Let the system find trending topics for inspiration
- **Iterate**: Use optimization suggestions to improve persona over time
- **Stay compliant**: Pay attention to compliance warnings

## Troubleshooting

**"API key not found"**
- Make sure you've created `.env` file
- Check that the API key is correct for your provider

**"Persona not found"**
- Use `avatarfactory list-personas` to see available personas
- Specify persona ID with `--persona` flag

**Low review scores**
- Check review report suggestions
- Ensure topic aligns with persona's expertise
- Verify content follows platform guidelines

**Connection errors with connectors**
- Check your credentials in `.env`
- For Xiaohongshu, cookies may expire - refresh from browser
- For Bluesky, use an app password (not main password)

## What's Next?

- Check out `docs/architecture.md` for system design
- See `examples/` for more code examples
- Try the REST API at `/docs` when running in service mode
- Report issues at GitHub

Happy persona building!
