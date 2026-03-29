#!/bin/bash
# session-init-identity.sh — Set terminal identity on Claude startup.
# Fires on the SessionStart "init" event (first launch, not clear/compact).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

source "$PLUGIN_ROOT/scripts/terminal/identity.sh"

# Persist the resolved TTY so SessionEnd can reach the terminal during teardown
purlin_save_tty

# Check if a mode is already persisted (e.g. from a previous session)
mode="none"
if [ -f ".purlin/state/mode" ]; then
    mode=$(cat .purlin/state/mode 2>/dev/null)
fi

update_session_identity "$mode"
exit 0
