#!/bin/bash
# Virtual Environment Setup and Verification Script for AvatarFactory
# Works on Windows (Git Bash), macOS, and Linux

set -e  # Exit on error

echo "============================================================"
echo "  AvatarFactory - Virtual Environment Setup & Verification"
echo "============================================================"
echo ""

# Detect OS
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    OS="windows"
    VENV_ACTIVATE="venv/Scripts/activate"
    PYTHON_CMD="python"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    VENV_ACTIVATE="venv/bin/activate"
    PYTHON_CMD="python3"
else
    OS="linux"
    VENV_ACTIVATE="venv/bin/activate"
    PYTHON_CMD="python3"
fi

echo "Detected OS: $OS"
echo ""

# Check Python version
echo "1️⃣  Checking Python version..."
$PYTHON_CMD --version

PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "   Python version: $PYTHON_VERSION"

if [[ $(echo "$PYTHON_VERSION < 3.10" | bc -l) -eq 1 ]]; then
    echo "   ❌ Python 3.10+ required (found $PYTHON_VERSION)"
    exit 1
else
    echo "   ✅ Python version OK"
fi
echo ""

# Create virtual environment
echo "2️⃣  Creating virtual environment..."
if [ -d "venv" ]; then
    echo "   ⚠️  venv directory already exists"
    read -p "   Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "   Deleting old venv..."
        rm -rf venv
        $PYTHON_CMD -m venv venv
        echo "   ✅ New virtual environment created"
    else
        echo "   Using existing venv"
    fi
else
    $PYTHON_CMD -m venv venv
    echo "   ✅ Virtual environment created"
fi
echo ""

# Activate virtual environment
echo "3️⃣  Activating virtual environment..."
source $VENV_ACTIVATE
echo "   ✅ Virtual environment activated"
echo "   Python location: $(which python)"
echo ""

# Upgrade pip
echo "4️⃣  Upgrading pip..."
python -m pip install --upgrade pip --quiet
echo "   ✅ pip upgraded"
echo ""

# Install requirements
echo "5️⃣  Installing dependencies..."
echo ""
echo "   Choose installation type:"
echo "   1) Standard (all LLM providers)"
echo "   2) Development (with testing tools)"
echo ""
read -p "   Enter choice [1-2]: " choice

case $choice in
    1)
        REQ_FILE="requirements.txt"
        echo "   Installing: Standard"
        ;;
    2)
        REQ_FILE="requirements-dev.txt"
        echo "   Installing: Development"
        ;;
    *)
        echo "   Invalid choice, using Standard installation"
        REQ_FILE="requirements.txt"
        ;;
esac

echo ""
pip install -r $REQ_FILE
echo "   ✅ Dependencies installed"
echo ""

# Install package in editable mode
echo "6️⃣  Installing AvatarFactory package..."
pip install -e .
echo "   ✅ AvatarFactory package installed"
echo ""

# Check .env file
echo "7️⃣  Checking configuration..."
if [ -f ".env" ]; then
    echo "   ✅ .env file found"
else
    echo "   ⚠️  .env file not found"
    if [ -f ".env.example" ]; then
        read -p "   Create .env from .env.example? (Y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            cp .env.example .env
            echo "   ✅ .env created from .env.example"
            echo "   ⚠️  IMPORTANT: Edit .env and add your API keys!"
        fi
    fi
fi
echo ""

# Run verification
echo "8️⃣  Running installation verification..."
echo ""
python scripts/verify_install.py

# Show activation instructions
echo ""
echo "============================================================"
echo "  ✅ Setup Complete!"
echo "============================================================"
echo ""
echo "Virtual environment is activated in this session."
echo ""
echo "To use AvatarFactory:"
echo "  • In this terminal: avatarfactory chat"
echo ""
echo "To activate venv in a new terminal:"
if [ "$OS" = "windows" ]; then
    echo "  • Windows (CMD):     venv\\Scripts\\activate.bat"
    echo "  • Windows (PowerShell): venv\\Scripts\\Activate.ps1"
    echo "  • Git Bash:          source venv/Scripts/activate"
else
    echo "  • Run: source venv/bin/activate"
fi
echo ""
echo "To deactivate:"
echo "  • Run: deactivate"
echo ""
echo "Next steps:"
echo "  1. Edit .env and add your API keys"
echo "  2. Run: avatarfactory chat"
echo "  3. Start creating personas!"
echo ""
