# Virtual Environment Setup

Detailed guide for setting up and managing Python virtual environments with AvatarFactory.

---

## Why Use a Virtual Environment

- **Isolation** — Keep project dependencies separate from system Python
- **Reproducibility** — Ensure consistent environments across machines
- **Easy cleanup** — Delete the venv directory to remove everything

---

## Quick Start

### Windows

**PowerShell (recommended):**
```powershell
.\scripts\setup_venv.ps1
```

If you see a "scripts disabled" error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**CMD:**
```cmd
scripts\setup_venv.bat
```

### macOS / Linux

```bash
chmod +x scripts/setup_venv.sh
./scripts/setup_venv.sh
```

---

## What the Setup Script Does

1. Checks Python version (requires 3.10+)
2. Creates virtual environment (`.venv/`)
3. Activates the environment
4. Upgrades pip
5. Prompts for install type (Full / Minimal / Azure / OpenAI / Dev)
6. Installs dependencies
7. Installs AvatarFactory in editable mode
8. Checks `.env` configuration
9. Runs verification tests

---

## Manual Setup

If you prefer not to use the automated script:

### Step 1: Create virtual environment

```bash
# Windows
python -m venv .venv

# macOS/Linux
python3 -m venv .venv
```

### Step 2: Activate

```bash
# Windows CMD
.venv\Scripts\activate.bat

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Windows Git Bash
source .venv/Scripts/activate

# macOS/Linux
source .venv/bin/activate
```

A `(.venv)` prefix in your terminal prompt confirms activation.

### Step 3: Upgrade pip

```bash
python -m pip install --upgrade pip
```

### Step 4: Install dependencies

```bash
# Standard
pip install -r requirements.txt

# Development (includes test tools)
pip install -r requirements-dev.txt
```

### Step 5: Install AvatarFactory

```bash
pip install -e .
```

### Step 6: Configure environment

```bash
cp .env.example .env   # macOS/Linux
copy .env.example .env  # Windows
# Edit .env and add your API keys
```

### Step 7: Verify

```bash
python scripts/verify_install.py
```

---

## Daily Usage

### Activate the environment

Each time you open a new terminal:

```bash
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

### Run AvatarFactory

```bash
(.venv) $ avatarfactory chat
(.venv) $ avatarfactory create-persona "..."
```

### Deactivate

```bash
deactivate
```

---

## Updating Dependencies

```bash
# Activate venv first, then:
pip install --upgrade -r requirements.txt

# Or update a specific package:
pip install --upgrade anthropic
```

---

## Removing the Environment

```bash
deactivate
# Windows
rmdir /s .venv
# macOS/Linux
rm -rf .venv

# Then re-run setup script to start fresh
```

---

## Troubleshooting

### "python: command not found"

```bash
# Windows: use py launcher
py -m venv .venv

# macOS/Linux: use python3
python3 -m venv .venv
```

### Cannot activate virtual environment

Check if the activation script exists:
```bash
# Windows
dir .venv\Scripts\activate.bat

# macOS/Linux
ls .venv/bin/activate
```

If not found, recreate the venv.

### PowerShell script execution disabled

```powershell
# Temporary bypass
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process

# Or permanent (current user)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### "pip install" fails

```bash
python -m pip install --upgrade pip
pip cache purge
pip install -r requirements.txt
```

### "avatarfactory: command not found"

```bash
pip install -e .
# Or run directly:
python -m avatarfactory.cli chat
```

---

## Best Practices

1. Always activate venv before working on the project
2. Never commit `.venv/` to Git (already in `.gitignore`)
3. Use `requirements.txt` to manage dependencies
4. Update dependencies monthly

---

## Alternatives

### Using conda

```bash
conda create -n avatarfactory python=3.10
conda activate avatarfactory
pip install -r requirements.txt
```

---

## Verification Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment created (`.venv/` exists)
- [ ] Environment activated (prompt shows `(.venv)`)
- [ ] Dependencies installed (`pip list` shows packages)
- [ ] AvatarFactory installed (`avatarfactory version` works)
- [ ] `.env` file configured
- [ ] `python scripts/verify_install.py` passes

---

## Related

- [Getting Started](../getting-started.md) — Full installation guide
- [Configuration](../configuration.md) — LLM provider setup
- [Python venv documentation](https://docs.python.org/3/library/venv.html)
