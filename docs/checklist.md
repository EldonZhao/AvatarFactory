# 🚀 AvatarFactory - Quick Start Checklist

Follow this checklist to get AvatarFactory up and running in 5 minutes!

---

## ✅ Step 1: Prerequisites

- [ ] Python 3.10 or higher installed
  ```bash
  python --version  # Should be 3.10+
  ```

- [ ] Anthropic API key ready
  - Get one at: https://console.anthropic.com/
  - Keep it handy for Step 3

---

## ✅ Step 2: Installation

- [ ] Install the package:
  ```bash
  # Option 1: Using pip (recommended for quick start)
  pip install -e .

  # Option 2: Using poetry
  poetry install
  ```

- [ ] Verify installation:
  ```bash
  avatarfactory version
  ```
  Should output: `AvatarFactory v0.1.0 (MVP)`

---

## ✅ Step 3: Configuration

- [ ] Create `.env` file:
  ```bash
  # On Windows
  copy .env.example .env

  # On Mac/Linux
  cp .env.example .env
  ```

- [ ] Edit `.env` and add your API key:
  ```
  ANTHROPIC_API_KEY=sk-ant-xxxxx...
  ```

- [ ] Test API connection:
  ```bash
  avatarfactory chat
  # Then type: hello
  # If it responds, you're good to go!
  ```

---

## ✅ Step 4: First Run - Create a Persona

Choose ONE of these methods:

### Method A: Interactive Chat (Recommended)
```bash
avatarfactory chat
```

Then in the chat:
```
You: Create a persona for a productivity tools reviewer targeting freelancers on Xiaohongshu

[Wait for response]

You: Generate content about "Top 5 AI tools for freelancers"

[Review the content]

You: exit
```

### Method B: Quick Commands
```bash
# Create persona
avatarfactory create-persona "Productivity tools expert for freelancers" --platform xiaohongshu

# Note the persona ID from output, then:
avatarfactory generate "Top 5 AI tools for freelancers" --persona <persona_id>
```

---

## ✅ Step 5: Verify Everything Works

- [ ] Check your personas:
  ```bash
  avatarfactory list-personas
  ```

- [ ] Check generated content:
  ```bash
  avatarfactory list-content --status draft
  ```

- [ ] View statistics:
  ```bash
  avatarfactory stats
  ```

---

## ✅ Step 6: Explore Your Data

- [ ] Open the knowledge base folder:
  ```
  knowledge_base/
    └── personas/
        └── persona_xxxxx/
            ├── config.yaml      # Your persona configuration
            ├── versions/        # Version history
            └── reviews/         # Content reviews
  ```

- [ ] Read your persona config:
  - Open `knowledge_base/personas/persona_xxxxx/config.yaml`
  - Review the structured persona definition

- [ ] Check your content:
  - Open `knowledge_base/content_library/drafts/`
  - Find your generated content (JSON files)

---

## 🎉 Success!

If you completed all steps, you now have:

✅ A working AvatarFactory installation
✅ At least one persona created
✅ At least one piece of content generated
✅ Understanding of the file structure

---

## 🚨 Troubleshooting

### "ANTHROPIC_API_KEY not found"
- Make sure `.env` file exists in the project root
- Check that there are no quotes around the key in .env
- Try: `export ANTHROPIC_API_KEY=your_key` (Mac/Linux) or restart terminal

### "Command not found: avatarfactory"
- Make sure you ran `pip install -e .`
- Try: `python -m avatarfactory.cli chat`
- Check your PATH includes pip install location

### "Module not found" errors
- Reinstall: `pip install -e . --force-reinstall`
- Check Python version: `python --version` (must be 3.10+)

### Content generation fails
- Check internet connection (needs API access)
- Verify API key is valid
- Check API credits at https://console.anthropic.com/

### Low review scores (<70)
- This is normal! Iterate and refine
- Read the suggestions in the review report
- Try different topics or adjust persona

---

## 📚 What's Next?

Now that everything works, explore more:

1. **Read the guides:**
   - [quickstart.md](quickstart.md) - Detailed usage guide
   - [architecture.md](architecture.md) - Understand the system

2. **Try advanced features:**
   - Generate multiple variants: `--variants 3`
   - Create personas for different platforms
   - Experiment with different content types

3. **Customize:**
   - Edit content templates in `avatarfactory/agents/content_lab.py`
   - Add your own platform rules to `knowledge_base/platform_rules/`
   - Modify persona prompts in `avatarfactory/agents/persona_lab.py`

4. **Provide feedback:**
   - Report bugs
   - Suggest features
   - Share your success stories!

---

## 🎯 Typical First Session

Here's what a typical first session looks like:

```bash
$ avatarfactory chat

You: Create a persona for a tech book reviewer on Xiaohongshu targeting software engineers

AvatarFactory: ✅ Created persona '技术图书观察者' (ID: persona_a1b2c3)
                Validation score: 85/100
                Sample content generated with review score: 80/100

You: Generate 3 variants about "Clean Code book review"

AvatarFactory: ✅ Generated content: '《代码整洁之道》到底值不值得读？我的 30 天实践心得'
                Review score: 88/100
                Status: ✅ Approved

You: list my personas

AvatarFactory: 📊 Found 1 persona:
                • persona_a1b2c3 - 技术图书观察者

You: exit

AvatarFactory: Goodbye! 👋
```

**Time to get here: ~5 minutes**
**You're now ready to start building your social presence!**

---

**Ready? Let's go!** 🚀

```bash
avatarfactory chat
```
