#!/usr/bin/env bash
# context_guard.sh — PostToolUse hook that monitors session turn count
# and warns when a configurable threshold is exceeded.
#
# Input: JSON on stdin from Claude Code (contains session_id, cwd, etc.)
# Output: JSON with additionalContext when turn count exceeds threshold.
#         Plain stdout is NOT visible to the agent in PostToolUse hooks.
#         Must use hookSpecificOutput.additionalContext for agent visibility.

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
# Ensure runtime directory exists
mkdir -p "$RUNTIME_DIR"

# Read threshold from resolved config via resolver CLI (config_layering)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOLVER="$SCRIPT_DIR/../config/resolve_config.py"
THRESHOLD=$(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 "$RESOLVER" --key context_guard_threshold 2>/dev/null || echo "45")
if [ -z "$THRESHOLD" ] || ! [[ "$THRESHOLD" =~ ^[0-9]+$ ]]; then
    THRESHOLD=45
fi

# Use hook session_id, fall back to PPID
SESSION_ID="${HOOK_SESSION_ID:-ppid-$PPID}"

# Acquire file lock to prevent race conditions with parallel tool calls.
# mkdir is atomic on POSIX; used as a portable mutex (flock unavailable on macOS).
LOCK_DIR="$RUNTIME_DIR/context_guard.lock"
LOCK_WAIT=0
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    sleep 0.02
    LOCK_WAIT=$((LOCK_WAIT + 1))
    if [[ $LOCK_WAIT -ge 100 ]]; then
        # After ~2 seconds, force break stale lock
        rmdir "$LOCK_DIR" 2>/dev/null || rm -rf "$LOCK_DIR" 2>/dev/null || true
    fi
done
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

# Session detection: new session when session_id changes or file missing.
# Subagent detection: Task-launched subagents have different session_ids but
# run concurrently with the main agent. If session_id mismatches but the
# turn_count file was recently modified, this is a subagent — skip silently.
NEW_SESSION=false
IS_SUBAGENT=false
if [[ ! -f "$SESSION_ID_FILE" ]]; then
    NEW_SESSION=true
elif [[ "$(cat "$SESSION_ID_FILE" 2>/dev/null)" != "$SESSION_ID" ]]; then
    # Session ID mismatch: either a new main session or a subagent.
    # Check turn_count file age to distinguish.
    TURN_MOD_AGE=$(python3 -c "
import os, time
try:
    print(int(time.time() - os.path.getmtime('$TURN_COUNT_FILE')))
except:
    print(9999)" 2>/dev/null || echo "9999")
    if [[ $TURN_MOD_AGE -lt 120 ]]; then
        # Recent activity — main session is still alive, this is a subagent.
        IS_SUBAGENT=true
    else
        # Stale — genuinely new session.
        NEW_SESSION=true
    fi
fi

# Subagents exit without counting or resetting.
if [[ "$IS_SUBAGENT" == "true" ]]; then
    exit 0
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
# PostToolUse hooks MUST output JSON with additionalContext for agent visibility.
# Plain stdout/echo is NOT surfaced to the agent — only to the user's terminal.
if [[ $COUNT -gt $THRESHOLD ]]; then
    cat <<GUARDJSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"[CONTEXT GUARD] Turn ${COUNT}/${THRESHOLD}. Run /pl-resume save, then /clear, then /pl-resume to continue."}}
GUARDJSON
fi
