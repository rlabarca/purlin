#!/usr/bin/env bash
# context_guard.sh — PostToolUse hook that monitors session turn count
# and outputs context budget status on every tool call.
#
# Input: JSON on stdin from Claude Code (contains session_id, cwd, etc.)
# Output: JSON with additionalContext on every turn (when guard enabled).
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
# Ensure runtime directory exists
mkdir -p "$RUNTIME_DIR"

# Role-specific files prevent cross-contamination between concurrent agents.
# When AGENT_ROLE is set (via launcher scripts), each agent gets its own counter
# and session tracking. Without AGENT_ROLE, falls back to unsuffixed files.
ROLE_SUFFIX=""
if [[ -n "${AGENT_ROLE:-}" ]]; then
    ROLE_SUFFIX="_${AGENT_ROLE}"
fi
TURN_COUNT_FILE="$RUNTIME_DIR/turn_count${ROLE_SUFFIX}"
SESSION_ID_FILE="$RUNTIME_DIR/session_id${ROLE_SUFFIX}"

# Read per-agent config via resolver --dump + inline Python.
# AGENT_ROLE is set by launcher scripts (agent_launchers_common.md Section 2.1).
# Fallback chain: agents.<role>.context_guard_threshold > global context_guard_threshold > 45
# Enabled chain: agents.<role>.context_guard > default true
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOLVER="$SCRIPT_DIR/../config/resolve_config.py"

read -r THRESHOLD GUARD_ENABLED < <(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import json, subprocess, sys, os
role = os.environ.get('AGENT_ROLE', '')
try:
    raw = subprocess.check_output(
        [sys.executable, '$RESOLVER', '--dump'],
        env={**os.environ, 'PURLIN_PROJECT_ROOT': '$PROJECT_ROOT'},
        stderr=subprocess.DEVNULL
    )
    cfg = json.loads(raw)
except:
    cfg = {}
global_thresh = cfg.get('context_guard_threshold', 45)
agent = cfg.get('agents', {}).get(role, {}) if role else {}
thresh = agent.get('context_guard_threshold', global_thresh)
enabled = agent.get('context_guard', True)
print(f'{thresh} {\"true\" if enabled else \"false\"}')
" 2>/dev/null || echo "45 true")

# Validate threshold is a positive integer
if [ -z "$THRESHOLD" ] || ! [[ "$THRESHOLD" =~ ^[0-9]+$ ]]; then
    THRESHOLD=45
fi
if [ -z "$GUARD_ENABLED" ]; then
    GUARD_ENABLED="true"
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

# Read current count and increment (counter always increments, even when guard disabled)
COUNT=$(cat "$TURN_COUNT_FILE" 2>/dev/null || echo "0")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$TURN_COUNT_FILE"

# When guard is disabled, no output — counter still increments in background.
if [[ "$GUARD_ENABLED" != "true" ]]; then
    exit 0
fi

# Output context status on every turn via additionalContext.
# PostToolUse hooks MUST output JSON with additionalContext for agent visibility.
REMAINING=$((THRESHOLD - COUNT))
if [[ $REMAINING -gt 0 ]]; then
    cat <<GUARDJSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"CONTEXT GUARD: ${REMAINING}/${THRESHOLD}"}}
GUARDJSON
else
    cat <<GUARDJSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"CONTEXT GUARD: ${REMAINING}/${THRESHOLD} -- Run /pl-resume save, then /clear, then /pl-resume to continue."}}
GUARDJSON
fi
