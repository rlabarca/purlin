#!/bin/bash
# session-init-identity.sh — Set terminal identity on Claude startup.
# Fires on the SessionStart "init" event (first launch, not clear/compact).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

source "$PLUGIN_ROOT/scripts/terminal/identity.sh"

# Persist the resolved TTY so SessionEnd can reach the terminal during teardown
purlin_save_tty

# Clear stale session sync state from previous sessions
rm -f ".purlin/runtime/sync_state.json" 2>/dev/null

# Detect project name from config or directory basename
PROJECT_NAME=$(python3 "$PLUGIN_ROOT/scripts/mcp/config_engine.py" --key project_name 2>/dev/null)
if [ -z "$PROJECT_NAME" ]; then
    PROJECT_NAME=$(basename "$(pwd)")
fi

update_session_identity "$PROJECT_NAME"
exit 0
