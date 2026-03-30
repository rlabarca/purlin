#!/bin/bash
# write-guard.sh — PreToolUse hook for Write, Edit, NotebookEdit.
# Blocks: INVARIANT files (use purlin:invariant sync)
# Blocks: UNKNOWN files (add classification to CLAUDE.md)
# Allows: everything else (with permissionDecision:allow for marketplace)
#
# INVARIANT bypass: purlin:invariant creates a lock file at
# .purlin/runtime/invariant_write_lock containing the target path.
# write-guard allows the write if the lock matches, then the skill
# removes the lock. This keeps invariant protection intact for all
# other callers.
#
# Exit codes:
#   0 = allow the write (with permissionDecision JSON)
#   2 = block the write (error on stderr)

set -eo pipefail

_allow() {
    local reason="${1:-Authorized by Purlin write guard}"
    echo "{\"hookSpecificOutput\":{\"hookEventName\":\"PreToolUse\",\"permissionDecision\":\"allow\",\"permissionDecisionReason\":\"$reason\"}}"
    exit 0
}

INPUT=$(cat)

if [ -z "$INPUT" ]; then
    _allow "No hook input — fail open"
fi

FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    inp = data.get('tool_input', {})
    print(inp.get('file_path', inp.get('filePath', '')))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    _allow "File path not determined — fail open"
fi

# Detect project root
_find_project_root() {
    if [ -n "${PURLIN_PROJECT_ROOT:-}" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
        echo "$PURLIN_PROJECT_ROOT"; return
    fi
    local dir; dir="$(pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.purlin" ]; then echo "$dir"; return; fi
        dir=$(dirname "$dir")
    done
    if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/.purlin" ]; then
        echo "$CLAUDE_PLUGIN_ROOT"; return
    fi
    echo "$(pwd)"
}

PROJECT_ROOT="$(_find_project_root)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"

# Classify file
CLASSIFICATION=$(python3 -c "
import sys, os
os.environ.setdefault('PURLIN_PROJECT_ROOT', '$PROJECT_ROOT')
sys.path.insert(0, '$PLUGIN_ROOT/scripts/mcp')
from config_engine import classify_file
print(classify_file('$REL_PATH'))
" 2>/dev/null || echo "UNKNOWN")

case "$CLASSIFICATION" in
    INVARIANT)
        # Check for bypass lock from purlin:invariant skill
        LOCK_FILE="$PROJECT_ROOT/.purlin/runtime/invariant_write_lock"
        if [ -f "$LOCK_FILE" ]; then
            LOCK_PATH=$(cat "$LOCK_FILE" 2>/dev/null)
            if [ "$LOCK_PATH" = "$REL_PATH" ] || [ "$LOCK_PATH" = "$FILE_PATH" ] || [ "$LOCK_PATH" = "*" ]; then
                _allow "Invariant write authorized via purlin:invariant bypass lock"
            fi
        fi
        echo "BLOCKED: $REL_PATH is INVARIANT. Use purlin:invariant sync to update from the external source." >&2
        exit 2
        ;;
    UNKNOWN)
        echo "BLOCKED: $REL_PATH has no classification rule. Add a rule to CLAUDE.md under '## Purlin File Classifications': \`$(dirname "$REL_PATH")/\` → CODE (or SPEC)." >&2
        exit 2
        ;;
    *)
        _allow "Write guard: $CLASSIFICATION write authorized"
        ;;
esac
