# Claude Code Prompt Me Less

Constant permission prompts breaking your flow? This Claude Code plugin auto-approves and whitelists safe commands (`ls`, `git status`, `npm test`...) while leaving others (`rm -rf`, `curl | bash`...) to the normal approval flow.

## Requirements

[Claude Code](https://github.com/anthropics/claude-code) CLI installed and authenticated.

```bash
# Verify installation
claude --version
```

## Install

In a Claude Code session, run:

```
/plugin install sultano/claude-code-prompt-me-less
```

## Uninstall

In a Claude Code session, run:

```
/plugin uninstall prompt-me-less
```

## How It Works

1. Code-based safety net catches known dangerous patterns (100% reliable)
2. Claude Haiku handles nuanced/novel cases via Claude Code CLI
3. Safe commands are auto-whitelisted to `settings.local.json` for future runs
