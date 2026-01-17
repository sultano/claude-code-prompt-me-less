#!/bin/bash
# Installation script for Claude Code Auto-Approve

set -e

HOOKS_DIR="$HOME/.claude/hooks"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "Installing Claude Code Auto-Approve..."

# Create hooks directory
mkdir -p "$HOOKS_DIR"

# Copy the hook script
cp validate_tool_safety.py "$HOOKS_DIR/"
chmod +x "$HOOKS_DIR/validate_tool_safety.py"

echo "Hook script installed to: $HOOKS_DIR/validate_tool_safety.py"

# Check if settings.json exists and merge, or create new
if [ -f "$SETTINGS_FILE" ]; then
    echo ""
    echo "Existing settings.json found at $SETTINGS_FILE"
    echo "Please manually add the following to your hooks configuration:"
    echo ""
    cat settings.json
    echo ""
    echo "Or backup your existing settings and replace:"
    echo "  cp $SETTINGS_FILE ${SETTINGS_FILE}.backup"
    echo "  # Then merge the hook configuration"
else
    cp settings.json "$SETTINGS_FILE"
    echo "Settings installed to: $SETTINGS_FILE"
fi

# Check if Claude CLI is available
echo ""
echo "Checking Claude CLI..."
if command -v claude &> /dev/null; then
    echo "Claude CLI is available."
else
    echo "Claude CLI not found. Please install it first:"
    echo "  npm install -g @anthropic-ai/claude-code"
fi

echo ""
echo "Installation complete!"
