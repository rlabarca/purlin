#!/bin/bash
# write-guard.sh — PreToolUse hook for Write, Edit, NotebookEdit.
#
# Three-bucket decision tree:
#   1. .purlin/* or .claude/*                   → ALLOW (system files)
#   2. features/_invariants/i_*                 → INVARIANT bypass lock (unchanged)
#   3. features/*                               → check active_skill marker
#                                                  present → ALLOW
#                                                  absent  → BLOCK (use spec skill)
#   4. path classified as OTHER (write_exceptions) → ALLOW (freely editable)
#   5. everything else (code)                   → check active_skill marker
#                                                  present → ALLOW
#                                                  absent  → BLOCK (use purlin:build)
#
# Active skill marker: .purlin/runtime/active_skill
#   - Set by skills at start, cleared at end
#   - Cleared by session-init-identity.sh on session start
#   - Non-empty file = authorized; empty/missing = not authorized
#
# INVARIANT bypass: purlin:invariant creates a lock file at
# .purlin/runtime/invariant_write_lock containing the target path.
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

# Check if active_skill marker is present and non-empty
_has_active_skill() {
    local marker="$PROJECT_ROOT/.purlin/runtime/active_skill"
    [ -f "$marker" ] && [ -s "$marker" ]
}

# --- Step 1: System files — always writable ---
case "$REL_PATH" in
    .purlin/*|.claude/*)
        _allow "Write guard: system file"
        ;;
esac

# --- Step 2: Invariant files — existing bypass lock protocol ---
case "$REL_PATH" in
    features/_invariants/i_*)
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
esac

# --- Step 3: Features files — need active_skill marker ---
case "$REL_PATH" in
    features/*)
        if _has_active_skill; then
            _allow "Write guard: features file authorized via active_skill marker"
        fi
        echo "BLOCKED: $REL_PATH is a spec file. Use purlin:spec, purlin:anchor, purlin:discovery, or another spec skill. Or for a one-off edit: echo spec > .purlin/runtime/active_skill" >&2
        exit 2
        ;;
esac

# --- Step 4: Classify for OTHER (write_exceptions) ---
CLASSIFICATION=$(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" PURLIN_PLUGIN_ROOT="$PLUGIN_ROOT" PURLIN_REL_PATH="$REL_PATH" python3 -c "
import sys, os
project_root = os.environ['PURLIN_PROJECT_ROOT']
plugin_root = os.environ['PURLIN_PLUGIN_ROOT']
rel_path = os.environ['PURLIN_REL_PATH']
os.environ.setdefault('PURLIN_PROJECT_ROOT', project_root)
sys.path.insert(0, os.path.join(plugin_root, 'scripts', 'mcp'))
from config_engine import classify_file
print(classify_file(rel_path))
" 2>/dev/null || echo "UNKNOWN")

if [ "$CLASSIFICATION" = "OTHER" ]; then
    _allow "Write guard: OTHER file (write exception) — freely editable"
fi

# --- Step 5: Everything else (code) — need active_skill marker ---
if _has_active_skill; then
    _allow "Write guard: code file authorized via active_skill marker"
fi

case "$CLASSIFICATION" in
    UNKNOWN)
        echo "BLOCKED: $REL_PATH has no classification rule. Add a rule to CLAUDE.md under '## Purlin File Classifications': \`$(dirname "$REL_PATH")/\` → CODE (or SPEC)." >&2
        exit 2
        ;;
    *)
        echo "BLOCKED: $REL_PATH requires purlin:build. If this path isn't code, run: purlin:classify add $REL_PATH. Or for a one-off edit: echo build > .purlin/runtime/active_skill" >&2
        exit 2
        ;;
esac
