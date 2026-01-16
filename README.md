# Claude Code Safety Hook

Claude Code hook that auto-approves safe commands and whitelists them. Everything else prompts as usual.

## Requirements

[Ollama](https://ollama.ai) with `qwen2.5-coder:7b`:

```bash
ollama pull qwen2.5-coder:7b
ollama serve
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
2. LLM handles nuanced/novel cases
3. Safe commands are auto-whitelisted to `settings.local.json` for future runs
