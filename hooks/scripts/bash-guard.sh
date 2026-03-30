#!/bin/bash
# PreToolUse hook — default-mode Bash guard.
# When no mode is active (default read-only), blocks Bash commands
# that match known write/destructive patterns.
# When a mode IS active, allows all Bash through with permissionDecision:allow.
#
# Exit codes:
#   0 = allow (with permissionDecision JSON for marketplace auto-approve)
#   2 = block (error on stderr)

set -e

# Output permissionDecision:allow JSON and exit 0
_allow() {
    local reason="${1:-Authorized by Purlin bash guard}"
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"permissionDecisionReason\":\"$reason\"}}"
    exit 0
}

INPUT=$(cat)

# Extract the command string from the tool input
COMMAND=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    tool_input = data.get('tool_input', {})
    print(tool_input.get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$COMMAND" ]; then
    _allow "No command to evaluate"
fi

# Extract agent_id from hook input (present when running inside a subagent)
AGENT_ID=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('agent_id', ''))
except Exception:
    print('')
" 2>/dev/null)

# Detect project root — works for both installed plugins and --plugin-dir.
_find_project_root() {
    if [ -n "$PURLIN_PROJECT_ROOT" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
        echo "$PURLIN_PROJECT_ROOT"; return
    fi
    local dir; dir="$(pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.purlin" ]; then echo "$dir"; return; fi
        dir="$(dirname "$dir")"
    done
    if [ -n "$CLAUDE_PLUGIN_ROOT" ] && [ -d "$CLAUDE_PLUGIN_ROOT/.purlin" ]; then
        echo "$CLAUDE_PLUGIN_ROOT"; return
    fi
    echo "$(pwd)"
}

PROJECT_ROOT="$(_find_project_root)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Use agent_id for mode file scoping (subagents), fall back to PURLIN_SESSION_ID
if [ -n "$AGENT_ID" ]; then
    export PURLIN_SESSION_ID="$AGENT_ID"
else
    export PURLIN_SESSION_ID="${PURLIN_SESSION_ID:-}"
fi

# Read current mode
CURRENT_MODE=$(python3 -c "
import sys, os
os.environ.setdefault('PURLIN_PROJECT_ROOT', '$PROJECT_ROOT')
sys.path.insert(0, '$PLUGIN_ROOT/scripts/mcp')
from config_engine import get_mode
mode = get_mode()
print(mode or 'none')
" 2>/dev/null)

# If a mode is active, allow all Bash commands through.
# Full per-mode classification of shell commands is too fragile.
if [ -n "$CURRENT_MODE" ] && [ "$CURRENT_MODE" != "none" ] && [ "$CURRENT_MODE" != "None" ]; then
    _allow "$CURRENT_MODE mode active: Bash authorized"
fi

# Default mode (no mode active) — allow basic file operations and safe git.
# Block dangerous operations and shell writes to files (bypasses mode guard).

# Shell write patterns — these bypass the Write/Edit mode guard.
# Redirect patterns use [^0-9] lookbehind to avoid matching stderr
# redirects like 2>/dev/null which are harmless.
SHELL_WRITE='(echo\s+.*[>]|printf\s+.*[>]|cat\s+.*[>]|tee\s|sed\s+-i|[^0-9]>\s*[/a-zA-Z.]|[^0-9]>>\s*[/a-zA-Z.]|^>\s*[/a-zA-Z.]|^>>\s*[/a-zA-Z.])'

# Dangerous operations
DANGEROUS='(git\s+push|git\s+reset\s+--hard|rm\s+-rf\s|rm\s+-r\s)'

if echo "$COMMAND" | grep -qE "$SHELL_WRITE"; then
    echo '{"error":"Shell file writes blocked in default mode — use Write/Edit tools instead, or call purlin_mode(mode: \"engineer\") to activate a mode."}' >&2
    exit 2
fi

if echo "$COMMAND" | grep -qE "$DANGEROUS"; then
    echo '{"error":"Dangerous command blocked in default mode. Call purlin_mode(mode: \"engineer\") to activate a mode first."}' >&2
    exit 2
fi

# Everything else is allowed in default mode — mv, cp, mkdir, git add,
# git commit, git checkout, basic rm, python, node, etc.
_allow "Default mode: command allowed"
