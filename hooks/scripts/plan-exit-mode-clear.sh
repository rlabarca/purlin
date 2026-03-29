#!/bin/bash
# PostToolUse hook — clear mode state after ExitPlanMode.
# Forces the agent to explicitly reactivate a Purlin mode before
# writing any files, preventing stale mode state from bypassing
# the mode guard.
#
# Exit codes:
#   0 = always (informational hook, never blocks)

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(pwd)}"

# Only act if this is a Purlin project
if [ ! -d "$PROJECT_ROOT/.purlin" ]; then
    exit 0
fi

# Clear PID-scoped mode file if PURLIN_SESSION_ID is set, else unscoped
if [ -n "$PURLIN_SESSION_ID" ]; then
    MODE_FILE="$PROJECT_ROOT/.purlin/runtime/current_mode_${PURLIN_SESSION_ID}"
else
    MODE_FILE="$PROJECT_ROOT/.purlin/runtime/current_mode"
fi

if [ -f "$MODE_FILE" ]; then
    > "$MODE_FILE"
fi

echo "Plan mode exited. Now in default mode (read-only). Activate a mode (purlin:mode engineer|pm|qa) before making changes."
exit 0
