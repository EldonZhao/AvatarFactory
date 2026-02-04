# AvatarFactory Quick Start

## Installation

1. Install dependencies:
```bash
# Using pip
pip install -e .

# Or using poetry (recommended)
poetry install
```

2. Set up your API key:
```bash
# Create .env file
cp .env.example .env

# Edit .env and add your Anthropic API key
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

List personas:
```bash
avatarfactory list-personas
```

List content:
```bash
avatarfactory list-content --status draft
```

Show statistics:
```bash
avatarfactory stats
```

### Python API

See `examples/quickstart.py` for a complete example.

```python
import asyncio
from avatarfactory import OrchestratorAgent, KnowledgeBase
from anthropic import Anthropic

async def main():
    kb = KnowledgeBase("./knowledge_base")
    client = Anthropic()
    orchestrator = OrchestratorAgent(knowledge_base=kb, anthropic_client=client)

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

3. **Generate Content**
   ```bash
   > Generate content about "Top 5 AI tools for freelancers in 2024"
   ```

4. **Review Content** (automatic after generation)
   - Check review score
   - Read suggestions
   - Revise if score < 70

5. **Publish** (manual - copy content to platform)

6. **Track Results** (optional)
   - Record engagement metrics
   - Analyze trends
   - Optimize persona

## Tips

- **Start simple**: Create one persona, generate a few pieces of content
- **Review scores**: Aim for 70+ for publishable content
- **Iterate**: Use optimization suggestions to improve persona over time
- **Stay compliant**: Pay attention to compliance warnings

## Troubleshooting

**"ANTHROPIC_API_KEY not found"**
- Make sure you've created `.env` file
- Check that the API key is correct

**"Persona not found"**
- Use `avatarfactory list-personas` to see available personas
- Specify persona ID with `--persona` flag

**Low review scores**
- Check review report suggestions
- Ensure topic aligns with persona's expertise
- Verify content follows platform guidelines

## What's Next?

- Check out `docs/architecture.md` for system design
- See `examples/` for more code examples
- Report issues at GitHub

Happy persona building! 🎭
