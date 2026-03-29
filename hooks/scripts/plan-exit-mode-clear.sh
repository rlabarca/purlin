#!/bin/bash
# PostToolUse hook — clear mode state after ExitPlanMode.
# Forces the agent to explicitly reactivate a Purlin mode before
# writing any files, preventing stale mode state from bypassing
# the mode guard.
#
# Exit codes:
#   0 = always (informational hook, never blocks)

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(pwd)}"
MODE_FILE="$PROJECT_ROOT/.purlin/runtime/current_mode"

# Only act if this is a Purlin project
if [ ! -d "$PROJECT_ROOT/.purlin" ]; then
    exit 0
fi

# Clear the persisted mode state
if [ -f "$MODE_FILE" ]; then
    > "$MODE_FILE"
fi

echo "Plan mode exited. Mode cleared — activate a mode before writing files."
exit 0
