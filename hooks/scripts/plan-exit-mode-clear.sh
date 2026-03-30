#!/bin/bash
# PostToolUse hook — clear mode state after ExitPlanMode.
# Forces the agent to explicitly reactivate a Purlin mode before
# writing any files, preventing stale mode state from bypassing
# the mode guard.
#
# Exit codes:
#   0 = always (informational hook, never blocks)

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

# Only act if this is a Purlin project
if [ ! -d "$PROJECT_ROOT/.purlin" ]; then
    exit 0
fi

# Extract agent_id from hook input for subagent scoping
INPUT=$(cat)
AGENT_ID=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('agent_id', ''))
except Exception:
    print('')
" 2>/dev/null)

# Clear agent-scoped mode file first, then PID-scoped, then unscoped
if [ -n "$AGENT_ID" ]; then
    MODE_FILE="$PROJECT_ROOT/.purlin/runtime/current_mode_${AGENT_ID}"
elif [ -n "$PURLIN_SESSION_ID" ]; then
    MODE_FILE="$PROJECT_ROOT/.purlin/runtime/current_mode_${PURLIN_SESSION_ID}"
else
    MODE_FILE="$PROJECT_ROOT/.purlin/runtime/current_mode"
fi

if [ -f "$MODE_FILE" ]; then
    > "$MODE_FILE"
fi

echo "Plan mode exited. Now in default mode (read-only). Activate a mode (purlin:mode engineer|pm|qa) before making changes."
exit 0
