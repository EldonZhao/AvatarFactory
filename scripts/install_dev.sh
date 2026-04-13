# Development installation script

echo "Installing AvatarFactory in development mode..."

# Install in editable mode
pip install -e .

echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your ANTHROPIC_API_KEY"
echo "2. Run: avatarfactory chat"
