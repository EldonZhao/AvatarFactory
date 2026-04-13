# Virtual Environment Setup and Verification Script for AvatarFactory (PowerShell)

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  AvatarFactory - Virtual Environment Setup & Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "1️⃣  Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version
    Write-Host "   $pythonVersion" -ForegroundColor Green

    # Extract version number
    $version = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ([double]$version -lt 3.10) {
        Write-Host "   ❌ Python 3.10+ required (found $version)" -ForegroundColor Red
        exit 1
    }
    Write-Host "   ✅ Python version OK" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Create virtual environment
Write-Host "2️⃣  Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "   ⚠️  venv directory already exists" -ForegroundColor Yellow
    $reply = Read-Host "   Delete and recreate? (y/N)"
    if ($reply -eq "y" -or $reply -eq "Y") {
        Write-Host "   Deleting old venv..." -ForegroundColor Yellow
        Remove-Item -Recurse -Force venv
        python -m venv venv
        Write-Host "   ✅ New virtual environment created" -ForegroundColor Green
    } else {
        Write-Host "   Using existing venv" -ForegroundColor Yellow
    }
} else {
    python -m venv venv
    Write-Host "   ✅ Virtual environment created" -ForegroundColor Green
}
Write-Host ""

# Activate virtual environment
Write-Host "3️⃣  Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"
Write-Host "   ✅ Virtual environment activated" -ForegroundColor Green
Write-Host "   Python location: $(Get-Command python | Select-Object -ExpandProperty Source)" -ForegroundColor Gray
Write-Host ""

# Upgrade pip
Write-Host "4️⃣  Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
Write-Host "   ✅ pip upgraded" -ForegroundColor Green
Write-Host ""

# Install requirements
Write-Host "5️⃣  Installing dependencies..." -ForegroundColor Yellow
Write-Host ""
Write-Host "   Choose installation type:" -ForegroundColor Cyan
Write-Host "   1) Standard (all LLM providers)"
Write-Host "   2) Development (with testing tools)"
Write-Host ""
$choice = Read-Host "   Enter choice [1-2]"

switch ($choice) {
    "1" {
        $reqFile = "requirements.txt"
        Write-Host "   Installing: Standard" -ForegroundColor Cyan
    }
    "2" {
        $reqFile = "requirements-dev.txt"
        Write-Host "   Installing: Development" -ForegroundColor Cyan
    }
    default {
        Write-Host "   Invalid choice, using Standard installation" -ForegroundColor Yellow
        $reqFile = "requirements.txt"
    }
}

Write-Host ""
pip install -r $reqFile
Write-Host "   ✅ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Install package in editable mode
Write-Host "6️⃣  Installing AvatarFactory package..." -ForegroundColor Yellow
pip install -e .
Write-Host "   ✅ AvatarFactory package installed" -ForegroundColor Green
Write-Host ""

# Check .env file
Write-Host "7️⃣  Checking configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "   ✅ .env file found" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  .env file not found" -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        $reply = Read-Host "   Create .env from .env.example? (Y/n)"
        if ($reply -ne "n" -and $reply -ne "N") {
            Copy-Item .env.example .env
            Write-Host "   ✅ .env created from .env.example" -ForegroundColor Green
            Write-Host "   ⚠️  IMPORTANT: Edit .env and add your API keys!" -ForegroundColor Yellow
        }
    }
}
Write-Host ""

# Run verification
Write-Host "8️⃣  Running installation verification..." -ForegroundColor Yellow
Write-Host ""
python scripts/verify_install.py

# Show activation instructions
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  ✅ Setup Complete!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Virtual environment is activated in this session." -ForegroundColor White
Write-Host ""
Write-Host "To use AvatarFactory:" -ForegroundColor Cyan
Write-Host "  • In this terminal: avatarfactory chat" -ForegroundColor White
Write-Host ""
Write-Host "To activate venv in a new terminal:" -ForegroundColor Cyan
Write-Host "  • PowerShell: .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "  • CMD:        venv\Scripts\activate.bat" -ForegroundColor White
Write-Host "  • Git Bash:   source venv/Scripts/activate" -ForegroundColor White
Write-Host ""
Write-Host "To deactivate:" -ForegroundColor Cyan
Write-Host "  • Run: deactivate" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit .env and add your API keys" -ForegroundColor White
Write-Host "  2. Run: avatarfactory chat" -ForegroundColor White
Write-Host "  3. Start creating personas!" -ForegroundColor White
Write-Host ""
