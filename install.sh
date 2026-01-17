#!/bin/bash
# Installation script for Claude Code Prompt Me Less

set -e

HOOKS_DIR="$HOME/.claude/hooks"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "Installing Claude Code Prompt Me Less..."

# Create hooks directory
mkdir -p "$HOOKS_DIR"

# Copy the hook script
cp validate_tool_safety.py "$HOOKS_DIR/"
chmod +x "$HOOKS_DIR/validate_tool_safety.py"

echo "Hook script installed to: $HOOKS_DIR/validate_tool_safety.py"

# Check if settings.json exists and merge, or create new
if [ -f "$SETTINGS_FILE" ]; then
    echo ""
    echo "Existing settings.json found. Merging hook configuration..."

    # Backup existing settings
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.backup"
    echo "Backup created: ${SETTINGS_FILE}.backup"

    # Merge using Python
    python3 - "$SETTINGS_FILE" "settings.json" <<'MERGE_SCRIPT'
import json
import sys

existing_path = sys.argv[1]
new_hooks_path = sys.argv[2]

with open(existing_path, 'r') as f:
    existing = json.load(f)

with open(new_hooks_path, 'r') as f:
    new_hooks = json.load(f)

# Ensure hooks structure exists
if 'hooks' not in existing:
    existing['hooks'] = {}

if 'PreToolUse' not in existing['hooks']:
    existing['hooks']['PreToolUse'] = []

# Check if our hook is already installed
our_hook_command = "python3 ~/.claude/hooks/validate_tool_safety.py"
already_installed = False

for hook_group in existing['hooks']['PreToolUse']:
    if 'hooks' in hook_group:
        for hook in hook_group['hooks']:
            if hook.get('command') == our_hook_command:
                already_installed = True
                break

if already_installed:
    print("Hook already configured in settings.json")
else:
    # Add our hook configuration
    existing['hooks']['PreToolUse'].extend(new_hooks['hooks']['PreToolUse'])

    with open(existing_path, 'w') as f:
        json.dump(existing, f, indent=2)

    print("Hook configuration merged into settings.json")
MERGE_SCRIPT

else
    mkdir -p "$(dirname "$SETTINGS_FILE")"
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
