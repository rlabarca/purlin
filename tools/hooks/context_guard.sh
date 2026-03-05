#!/usr/bin/env bash
# context_guard.sh — PostToolUse hook that monitors session turn count
# and warns when a configurable threshold is exceeded.
#
# Input: JSON on stdin from Claude Code (contains session_id, cwd, etc.)
# Output: Warning message to stdout when turn count exceeds threshold.

set -uo pipefail

# Read hook input from stdin (Claude Code sends JSON with session_id, etc.)
INPUT=$(cat 2>/dev/null || echo '{}')

# Extract session_id from hook input
HOOK_SESSION_ID=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('session_id', ''))
except:
    print('')" 2>/dev/null || echo "")

# Project root: PURLIN_PROJECT_ROOT > CWD
PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(pwd)}"
RUNTIME_DIR="$PROJECT_ROOT/.purlin/runtime"
TURN_COUNT_FILE="$RUNTIME_DIR/turn_count"
SESSION_ID_FILE="$RUNTIME_DIR/session_id"
CONFIG_FILE="$PROJECT_ROOT/.purlin/config.json"

# Ensure runtime directory exists
mkdir -p "$RUNTIME_DIR"

# Read threshold from config (default: 30)
THRESHOLD=$(python3 -c "
import json, sys
try:
    with open(sys.argv[1]) as f:
        print(json.load(f).get('context_guard_threshold', 30))
except (json.JSONDecodeError, IOError, OSError):
    print(30)" "$CONFIG_FILE" 2>/dev/null || echo "30")

# Use hook session_id, fall back to PPID
SESSION_ID="${HOOK_SESSION_ID:-ppid-$PPID}"

# Session detection: new session when session_id changes or file missing
NEW_SESSION=false
if [[ ! -f "$SESSION_ID_FILE" ]]; then
    NEW_SESSION=true
elif [[ "$(cat "$SESSION_ID_FILE" 2>/dev/null)" != "$SESSION_ID" ]]; then
    NEW_SESSION=true
fi

if [[ "$NEW_SESSION" == "true" ]]; then
    echo "$SESSION_ID" > "$SESSION_ID_FILE"
    echo "0" > "$TURN_COUNT_FILE"
fi

# Read current count and increment
COUNT=$(cat "$TURN_COUNT_FILE" 2>/dev/null || echo "0")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$TURN_COUNT_FILE"

# Warning when count exceeds threshold
if [[ $COUNT -gt $THRESHOLD ]]; then
    echo "[CONTEXT GUARD] Turn ${COUNT}/${THRESHOLD}. Run /pl-resume save, then /clear, then /pl-resume to continue."
fi
