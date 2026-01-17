# Claude Code Prompt Me Less

Constant permission prompts breaking your flow? This Claude Code hook auto-approves and whitelists safe commands (`ls`, `git status`, `npm test`...) while leaving others (`rm -rf`, `curl | bash`...) to the normal approval flow.

## Requirements

[Claude Code](https://github.com/anthropics/claude-code) CLI installed and authenticated.

```bash
# Verify installation
claude --version
```

## Install

```bash
./install.sh
```

This will:
- Copy the hook script to `~/.claude/hooks/`
- Auto-merge hook config into your existing `~/.claude/settings.json` (creates timestamped backup if modified)
- Create a new settings file if none exists

### Manual Install

```bash
cp validate_tool_safety.py ~/.claude/hooks/
```

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit|NotebookEdit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/validate_tool_safety.py"
          }
        ]
      }
    ]
  }
}
```

## Uninstall

```bash
rm ~/.claude/hooks/validate_tool_safety.py
# Restore backup if needed: cp ~/.claude/settings.backup.TIMESTAMP.json ~/.claude/settings.json
# Or manually remove the hook entry from ~/.claude/settings.json
```

## How It Works

1. Code-based safety net catches known dangerous patterns (100% reliable)
2. Claude Haiku handles nuanced/novel cases via Claude Code CLI
3. Safe commands are auto-whitelisted to `settings.local.json` for future runs
