#!/bin/bash
# PreToolUse hook — mechanical mode guard enforcement.
# Intercepts Write/Edit/NotebookEdit calls, classifies the target file,
# and blocks writes that violate mode boundaries.
#
# Exit codes:
#   0 = allow the write (with permissionDecision JSON for marketplace auto-approve)
#   2 = block the write (error on stderr, required for Claude Code to enforce block)
#
# Permission model: Instead of relying on bypassPermissions (stripped for
# marketplace plugins), this hook returns permissionDecision:"allow" for
# authorized writes. This gives surgical per-call approval.

# Output permissionDecision:allow JSON and exit 0
_allow() {
    local reason="${1:-Authorized by Purlin mode guard}"
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"permissionDecisionReason\":\"$reason\"}}"
    exit 0
}

# Output permissionDecision:ask JSON and exit 0 — let user decide
_ask() {
    local reason="${1:-Purlin mode guard: unrecognized file — user approval required}"
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"ask\",\"permissionDecisionReason\":\"$reason\"}}"
    exit 0
}

set -e

# Read the hook input from stdin
INPUT=$(cat)

# Extract the file path from the tool input
# The hook receives JSON with tool_name and tool_input
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    tool_input = data.get('tool_input', {})
    # Write tool uses file_path, Edit uses file_path
    path = tool_input.get('file_path', '')
    print(path)
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    # Cannot determine file — allow (fail open)
    _allow "File path not determined — fail open"
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

# Detect project root — works for both installed plugins (cache dir) and --plugin-dir.
# Order: env var → climb from CWD → CWD fallback → CLAUDE_PLUGIN_ROOT (--plugin-dir only).
_find_project_root() {
    # 1. Explicit env var (set by MCP server or parent process)
    if [ -n "$PURLIN_PROJECT_ROOT" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
        echo "$PURLIN_PROJECT_ROOT"; return
    fi
    # 2. Climb from CWD — most reliable for installed plugins (Claude Code sets
    #    hook CWD to the user's working directory)
    local dir; dir="$(pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.purlin" ]; then echo "$dir"; return; fi
        dir="$(dirname "$dir")"
    done
    # 3. CLAUDE_PLUGIN_ROOT — only works for --plugin-dir where plugin root IS the project
    if [ -n "$CLAUDE_PLUGIN_ROOT" ] && [ -d "$CLAUDE_PLUGIN_ROOT/.purlin" ]; then
        echo "$CLAUDE_PLUGIN_ROOT"; return
    fi
    # 4. Last resort
    echo "$(pwd)"
}

PROJECT_ROOT="$(_find_project_root)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Make path relative to project root for classification
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"

# Use agent_id for mode file scoping (subagents), fall back to PURLIN_SESSION_ID
if [ -n "$AGENT_ID" ]; then
    export PURLIN_SESSION_ID="$AGENT_ID"
else
    export PURLIN_SESSION_ID="${PURLIN_SESSION_ID:-}"
fi

# Try MCP server classification first (via Python inline)
CLASSIFICATION=$(python3 -c "
import sys, os
os.environ.setdefault('PURLIN_PROJECT_ROOT', '$PROJECT_ROOT')
sys.path.insert(0, '$PLUGIN_ROOT/scripts/mcp')
from config_engine import classify_file, get_mode
classification = classify_file('$REL_PATH')
mode = get_mode()
print(f'{classification}|{mode or \"none\"}')
" 2>/dev/null)

if [ -z "$CLASSIFICATION" ]; then
    # Fallback to file_classification.json
    CLASSIFICATION=$(python3 -c "
import json, sys, os, re
try:
    with open('$PLUGIN_ROOT/references/file_classification.json') as f:
        rules = json.load(f)
    path = '$REL_PATH'
    for rule in rules.get('rules', []):
        if re.search(rule['pattern'], path):
            print(rule['classification'] + '|none')
            sys.exit(0)
    print('UNKNOWN|none')
except Exception:
    print('')
" 2>/dev/null)
fi

if [ -z "$CLASSIFICATION" ]; then
    # Cannot classify — ask user
    _ask "File classification unavailable for $REL_PATH — approve manually?"
fi

FILE_CLASS=$(echo "$CLASSIFICATION" | cut -d'|' -f1)
CURRENT_MODE=$(echo "$CLASSIFICATION" | cut -d'|' -f2)

# UNKNOWN files — guard doesn't have a rule for this file.
# Ask the user instead of silently blocking or allowing.
if [ "$FILE_CLASS" = "UNKNOWN" ]; then
    _ask "Unrecognized file type: $REL_PATH — not in any mode's access list. Approve?"
fi

# Invariant files blocked regardless of mode (including default)
if [ "$FILE_CLASS" = "INVARIANT" ]; then
    echo "{\"error\":\"Mode guard: $REL_PATH is an invariant file. Invariants are immutable — use purlin:invariant sync to update from the external source.\"}" >&2
    exit 2
fi

# Default mode (no mode active) — allow basic file operations.
# Only INVARIANT files are blocked above. All other writes are allowed
# so the agent can do housekeeping (move files, edit configs, etc.)
# without needing to activate a mode first.
if [ "$CURRENT_MODE" = "none" ] || [ "$CURRENT_MODE" = "None" ]; then
    _allow "Default mode: $FILE_CLASS write allowed"
fi

# Mode-active: check mode-file compatibility
case "$CURRENT_MODE" in
    engineer)
        if [ "$FILE_CLASS" = "SPEC" ]; then
            echo "{\"error\":\"Mode guard: $REL_PATH is SPEC-owned, not writable in Engineer mode. Switch by calling the MCP tool: purlin_mode(mode: \\\"pm\\\").\"}" >&2
            exit 2
        fi
        if [ "$FILE_CLASS" = "QA" ]; then
            echo "{\"error\":\"Mode guard: $REL_PATH is QA-owned, not writable in Engineer mode. Switch by calling the MCP tool: purlin_mode(mode: \\\"qa\\\").\"}" >&2
            exit 2
        fi
        ;;
    pm)
        if [ "$FILE_CLASS" = "CODE" ]; then
            echo "{\"error\":\"Mode guard: $REL_PATH is CODE-owned, not writable in PM mode. Switch by calling the MCP tool: purlin_mode(mode: \\\"engineer\\\").\"}" >&2
            exit 2
        fi
        if [ "$FILE_CLASS" = "QA" ]; then
            echo "{\"error\":\"Mode guard: $REL_PATH is QA-owned, not writable in PM mode. Switch by calling the MCP tool: purlin_mode(mode: \\\"qa\\\").\"}" >&2
            exit 2
        fi
        ;;
    qa)
        if [ "$FILE_CLASS" = "CODE" ]; then
            echo "{\"error\":\"Mode guard: $REL_PATH is CODE-owned, not writable in QA mode. Switch by calling the MCP tool: purlin_mode(mode: \\\"engineer\\\").\"}" >&2
            exit 2
        fi
        if [ "$FILE_CLASS" = "SPEC" ]; then
            echo "{\"error\":\"Mode guard: $REL_PATH is SPEC-owned, not writable in QA mode. Switch by calling the MCP tool: purlin_mode(mode: \\\"pm\\\").\"}" >&2
            exit 2
        fi
        ;;
esac

_allow "$CURRENT_MODE mode: $FILE_CLASS write authorized"
