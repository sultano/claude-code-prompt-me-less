# Claude Code Prompt Me Less

Claude Code hook that auto-approves safe commands and whitelists them. Everything else prompts as usual.

## Requirements

[Claude Code](https://github.com/anthropics/claude-code) CLI installed and authenticated.

```bash
# Verify installation
claude --version
```

## Install

```bash
cp validate_tool_safety.py ~/.claude/hooks/
```

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
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

## How It Works

1. Code-based safety net catches known dangerous patterns (100% reliable)
2. Claude Haiku handles nuanced/novel cases via Claude Code CLI
3. Safe commands are auto-whitelisted to `settings.local.json` for future runs
