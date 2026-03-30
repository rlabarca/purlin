#!/bin/bash
# session-init-identity.sh — Set terminal identity on Claude startup.
# Fires on the SessionStart "init" event (first launch, not clear/compact).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

source "$PLUGIN_ROOT/scripts/terminal/identity.sh"

# Persist the resolved TTY so SessionEnd can reach the terminal during teardown
purlin_save_tty

# Clear stale session writes from previous sessions so the companion debt
# gate doesn't block based on a crashed session's state.
rm -f ".purlin/runtime/session_writes.json" 2>/dev/null

# Check if a mode is already persisted (e.g. from a previous session)
mode="none"
if [ -n "$PURLIN_SESSION_ID" ] && [ -f ".purlin/runtime/current_mode_${PURLIN_SESSION_ID}" ]; then
    mode=$(cat ".purlin/runtime/current_mode_${PURLIN_SESSION_ID}" 2>/dev/null)
elif [ -f ".purlin/runtime/current_mode" ]; then
    mode=$(cat .purlin/runtime/current_mode 2>/dev/null)
fi
[ -z "$mode" ] && mode="none"

update_session_identity "$mode"
exit 0
