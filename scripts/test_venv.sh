#!/bin/bash
# Quick test script - verifies venv installation

echo "🧪 Quick Test - AvatarFactory"
echo ""

# Check if venv is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "❌ Virtual environment not activated!"
    echo ""
    echo "Please activate venv first:"
    echo "  Windows: venv\\Scripts\\activate"
    echo "  macOS/Linux: source venv/bin/activate"
    exit 1
fi

echo "✅ Virtual environment active: $VIRTUAL_ENV"
echo ""

# Run verification
python scripts/verify_install.py

echo ""
echo "Test complete! If all checks passed, you're ready to use AvatarFactory."
echo ""
echo "Try: avatarfactory chat"
