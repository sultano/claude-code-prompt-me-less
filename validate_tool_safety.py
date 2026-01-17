#!/usr/bin/env python3
"""
Claude Code Auto-Approve: LLM-based Tool Safety Validator

Uses Claude Haiku (via Claude Code CLI) to assess whether a tool call is safe
(read-only) or requires user confirmation (write/destructive operations).

BEHAVIOR: This hook intercepts tool calls and uses Claude Haiku to classify them
as safe (auto-approve) or potentially dangerous (ask user). The LLM assessment
provides context-aware safety decisions beyond simple pattern matching.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Configuration
CLAUDE_MODEL = "haiku"
TIMEOUT_SECONDS = 60  # Allow time for Claude CLI

# Tools that are always safe (read-only by design)
ALWAYS_SAFE_TOOLS = {"Read", "Glob", "Grep", "WebSearch", "WebFetch"}

# Tools that always need user confirmation
ALWAYS_ASK_TOOLS = {"Task", "Skill"}

# Settings file paths
GLOBAL_SETTINGS = Path.home() / ".claude" / "settings.local.json"
PROJECT_SETTINGS_NAME = ".claude/settings.local.json"

# BEHAVIOR: Code-based safety net - catches dangerous patterns before LLM
# These are checked with simple string matching for 100% reliability

# Commands that are NEVER safe to run (always ask user)
UNSAFE_COMMANDS = {
    # Destructive
    "rm ", "rm\t", "rmdir", "unlink",
    "git clean", "git reset --hard", "git reset --mixed",
    # Force flags
    "--force", " -f ", " -rf", "-rf ",
    # Secrets in file paths
    ".env", ".ssh", ".aws", ".gnupg", "credentials", "secrets",
    "/etc/passwd", "/etc/shadow",
    # Inline secrets (API keys, tokens) - should never be whitelisted
    "sk-", "api_key=", "apikey=", "API_KEY=",
    "token=", "TOKEN=", "secret=", "SECRET=",
    "password=", "PASSWORD=", "passwd=",
    "Bearer ", "Basic ",
    # System modification
    "sudo ", "sudo\t", "doas ",
    "chmod ", "chown ", "chgrp ",
    "systemctl", "service ",
    # Process killing
    "pkill ", "kill ", "killall ",
    # Arbitrary execution
    "eval ", "exec ",
    "docker run", "docker exec",
    "kubectl run", "kubectl exec",
    # Network (data exfiltration risk)
    "curl ", "wget ", "nc ", "netcat",
    # Package managers (run arbitrary install scripts)
    "brew install", "brew upgrade",
    "pip install", "npm install", "yarn add", "pnpm install", "bun install",
}

# Commands safe to run but NEVER auto-whitelist (pattern could be abused)
NEVER_WHITELIST_COMMANDS = {
    # Git push - could add --force later
    "git push",
    # Docker/k8s - arbitrary execution
    "docker run", "docker exec",
    "kubectl exec", "kubectl run", "kubectl delete", "kubectl apply",
}

# Base commands that are always safe to run AND whitelist
SAFE_COMMAND_BASES = {
    # Version checks
    "--version", "-v", "-V", "version",
    # Read-only git
    "git status", "git log", "git diff", "git branch", "git show", "git remote",
    # Build/test (local operations)
    "go build", "go test", "go run", "go mod", "go version",
    "cargo build", "cargo test", "cargo run", "cargo check",
    "npm test", "npm run", "npm start",
    "make", "cmake",
    "pytest", "python -m pytest",
    # Read-only file operations
    "ls", "cat ", "head ", "tail ", "less ", "more ",
    "find ", "grep ", "wc ", "du ", "df ",
}

SYSTEM_PROMPT = """Evaluate if this bash command is safe to run without user confirmation.

Evaluate the EXACT command received. Is THIS specific command safe?

SAFE if the command:
- Only reads, displays, or queries information
- Builds, compiles, or tests code
- Checks versions or system info
- Performs standard, non-destructive operations

UNSAFE if the command:
- Deletes or modifies files
- Uses --force or -f flags
- Accesses secrets or credentials
- Could exfiltrate data to arbitrary destinations
- Runs arbitrary/untrusted code
- Changes system permissions
- Has irreversible effects

If SAFE, suggest a whitelist pattern using Claude Code's syntax:
- "Bash(cmd:*)" - prefix match: "Bash(go build:*)" matches "go build", "go build ./...", "go build -v"
- "Bash(cmd *)" - prefix wildcard: "Bash(git diff *)" matches "git diff HEAD", "git diff main"
- "Bash(* cmd)" - suffix wildcard: "Bash(* --version)" matches "node --version", "python --version"
- "Bash(cmd * arg)" - middle wildcard: "Bash(git * main)" matches "git checkout main", "git merge main"
- "Bash(cmd)" - exact match only (avoid this, prefer :* for flexibility)

Pattern guidelines - think: "What's the WORST command that could match this pattern?"
- If ALL variations are safe → use broad pattern "Bash(cmd:*)"
  Example: "go test:*" is safe because go test -v, go test ./... are all safe
- If SOME variations are dangerous → use exact match "Bash(exact command)"
  Example: "git push origin main" exact, because "git push:*" could match "git push --force"
- If even exact match is risky → use "none"

Respond with ONLY valid JSON:
{"safe": true, "reason": "...", "pattern": "Bash(...)"}
or
{"safe": false, "reason": "...", "pattern": "none"}
"""


def check_unsafe_command(command: str) -> bool:
    """Code-based check: Is this command unsafe to run? (100% reliable)"""
    cmd_lower = command.lower()
    return any(pattern in cmd_lower for pattern in UNSAFE_COMMANDS)


def check_never_whitelist(command: str) -> bool:
    """Code-based check: Should this command never be whitelisted? (100% reliable)"""
    cmd_lower = command.lower()
    return any(pattern in cmd_lower for pattern in NEVER_WHITELIST_COMMANDS)


def check_safe_command(command: str) -> bool:
    """Code-based check: Is this command known-safe to run AND whitelist?"""
    cmd_lower = command.lower()
    return any(pattern in cmd_lower for pattern in SAFE_COMMAND_BASES)


def get_settings_path() -> Path:
    """Get the closest settings file (project-level if exists, else global)."""
    project_settings = Path.cwd() / PROJECT_SETTINGS_NAME
    if project_settings.exists():
        return project_settings
    return GLOBAL_SETTINGS


def is_command_whitelisted(command: str) -> bool:
    """Check if command matches any pattern in the whitelist."""
    import fnmatch

    settings_path = get_settings_path()
    if not settings_path.exists():
        return False

    try:
        settings = json.loads(settings_path.read_text())
        allow_list = settings.get("permissions", {}).get("allow", [])
    except (json.JSONDecodeError, KeyError):
        return False

    for pattern in allow_list:
        # Extract pattern from Bash(...) format
        if pattern.startswith("Bash(") and pattern.endswith(")"):
            bash_pattern = pattern[5:-1]  # Remove "Bash(" and ")"

            # Handle :* prefix matching
            if bash_pattern.endswith(":*"):
                prefix = bash_pattern[:-2]
                if command.startswith(prefix):
                    return True
            # Handle * wildcards using fnmatch
            elif "*" in bash_pattern:
                if fnmatch.fnmatch(command, bash_pattern):
                    return True
            # Exact match
            elif command == bash_pattern:
                return True

    return False


def add_to_whitelist(command: str, pattern: str) -> None:
    """Add permission pattern to the closest settings.local.json."""
    # BEHAVIOR: Code-based safety net (100% reliable)
    if check_never_whitelist(command):
        return
    if check_unsafe_command(command):
        return
    if not pattern or pattern == "none":
        return

    settings_path = get_settings_path()

    try:
        if settings_path.exists():
            settings = json.loads(settings_path.read_text())
        else:
            settings = {}
    except json.JSONDecodeError:
        settings = {}

    # Ensure structure exists
    permissions = settings.setdefault("permissions", {})
    allow_list = permissions.setdefault("allow", [])

    # Add pattern if not already present
    if pattern not in allow_list:
        allow_list.append(pattern)
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def query_claude(prompt: str, system_prompt: str) -> dict[str, Any] | None:
    """Query Claude Haiku via Claude Code CLI for safety assessment."""
    full_prompt = f"{system_prompt}\n\n{prompt}"
    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt, "--model", CLAUDE_MODEL, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            return None

        # Parse JSON output - claude outputs JSON with "result" field containing the response
        output = json.loads(result.stdout)
        response_text = output.get("result", "")

        # Extract JSON from response text
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(response_text[start:end])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Claude query failed: {e}", file=sys.stderr)
    return None


def format_tool_for_analysis(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Format tool call for LLM analysis."""
    if tool_name == "Bash":
        command = tool_input.get("command", "")
        description = tool_input.get("description", "")
        return f"Tool: Bash\nCommand: {command}\nDescription: {description}"

    if tool_name in ("Write", "Edit"):
        file_path = tool_input.get("file_path", "")
        if tool_name == "Write":
            content_preview = tool_input.get("content", "")[:200]
            return f"Tool: Write\nFile: {file_path}\nContent preview: {content_preview}..."
        old_string = tool_input.get("old_string", "")[:100]
        new_string = tool_input.get("new_string", "")[:100]
        return f"Tool: Edit\nFile: {file_path}\nReplacing: {old_string}\nWith: {new_string}"

    if tool_name == "NotebookEdit":
        notebook_path = tool_input.get("notebook_path", "")
        edit_mode = tool_input.get("edit_mode", "replace")
        return f"Tool: NotebookEdit\nNotebook: {notebook_path}\nMode: {edit_mode}"

    # Generic format for other tools
    return f"Tool: {tool_name}\nInput: {json.dumps(tool_input, indent=2)[:500]}"


def make_decision(safe: bool, reason: str) -> dict[str, Any] | None:
    """Create the hook response. Returns None for unsafe operations to let Claude Code decide."""
    if safe:
        # BEHAVIOR: Auto-approve safe commands without prompting
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": reason,
            }
        }
    # BEHAVIOR: Return nothing for unsafe operations - lets Claude Code's
    # built-in permission system handle it (respects existing whitelist)
    return None


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # Let it pass if we can't parse input

    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # BEHAVIOR: Always-safe tools bypass LLM check - let Claude Code decide
    if tool_name in ALWAYS_SAFE_TOOLS:
        sys.exit(0)

    # BEHAVIOR: Always-ask tools - let Claude Code decide (respects whitelist)
    if tool_name in ALWAYS_ASK_TOOLS:
        sys.exit(0)

    # For Bash commands, use code-based safety net first
    if tool_name == "Bash":
        command = tool_input.get("command", "")

        # BEHAVIOR: Code-based unsafe check (100% reliable, no LLM needed)
        if check_unsafe_command(command):
            # Return nothing - let Claude Code ask user
            sys.exit(0)

        # BEHAVIOR: Code-based safe check (100% reliable, no LLM needed)
        if check_safe_command(command):
            decision = make_decision(True, "Code safety check: known safe command")
            if decision:
                print(json.dumps(decision))
            sys.exit(0)

        # BEHAVIOR: Already whitelisted - let Claude Code handle (no LLM needed)
        if is_command_whitelisted(command):
            sys.exit(0)

    # For commands not caught by code checks, use LLM
    analysis_prompt = format_tool_for_analysis(tool_name, tool_input)
    llm_result = query_claude(analysis_prompt, SYSTEM_PROMPT)

    if llm_result is None:
        # BEHAVIOR: If LLM unavailable, let Claude Code decide (respects whitelist)
        sys.exit(0)

    safe = llm_result.get("safe", False)
    reason = llm_result.get("reason", "LLM assessment")
    pattern = llm_result.get("pattern", "none")

    # BEHAVIOR: Auto-whitelist safe Bash commands for future runs
    if safe and tool_name == "Bash":
        command = tool_input.get("command", "")
        if command and pattern:
            add_to_whitelist(command, pattern)

    decision = make_decision(safe, f"LLM assessment: {reason}")
    if decision:
        print(json.dumps(decision))
    sys.exit(0)


if __name__ == "__main__":
    main()
