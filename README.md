# Claude Code Prompt Me Less

Constant permission prompts breaking your flow? This Claude Code plugin auto-approves safe commands (`ls`, `git status`, `npm test`...) while prompting for others (`rm -rf`, `curl | bash`...).

## Requirements

[Claude Code](https://github.com/anthropics/claude-code) CLI installed and authenticated.

```bash
# Verify installation
claude --version
```

## Install

In a Claude Code session, run:

```
/plugin marketplace add sultano/claude-code-marketplace
/plugin install prompt-me-less@sultano-plugins
```

## Uninstall

In a Claude Code session, run:

```
/plugin uninstall prompt-me-less
/plugin marketplace remove sultano-plugins
```

## How It Works

1. Code-based safety net catches known dangerous patterns (100% reliable)
2. Claude Haiku handles nuanced/novel cases via Claude Code CLI
3. Safe commands are auto-whitelisted to `settings.local.json` for future runs
