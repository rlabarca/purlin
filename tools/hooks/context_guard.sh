#!/usr/bin/env bash
# context_guard.sh — PostToolUse hook that monitors session turn count
# and outputs context budget status on every tool call.
#
# Each Claude Code process gets its own counter file, keyed by PPID.
# This eliminates the fragile file-age heuristic for session detection:
# - New process = new PPID = fresh counter (no reset logic needed)
# - Multiple agents (even same role) = different PPIDs = no collision
# - Subagents (same PPID, different session_id) = detected deterministically
#
# Files per agent: turn_count_<AGENT_ID>, session_meta_<AGENT_ID>
# AGENT_ID defaults to $PPID; override via CONTEXT_GUARD_AGENT_ID for testing.
#
# Input: JSON on stdin from Claude Code (contains session_id, cwd, etc.)
# Output: JSON with additionalContext on every turn (when guard enabled).
#         Plain stdout is NOT visible to the agent in PostToolUse hooks.
#         Must use hookSpecificOutput.additionalContext for agent visibility.

set -uo pipefail
# Advisory hook — must NEVER block the agent. Trap ensures exit 0 on any failure.
trap 'exit 0' ERR

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
mkdir -p "$RUNTIME_DIR"

# Role detection for config resolution (threshold, enabled).
# Role is NOT used for file naming — PPID provides unique identity.
# Launcher scripts write AGENT_ROLE to .purlin/runtime/agent_role for this fallback.
if [[ -z "${AGENT_ROLE:-}" ]] && [[ -f "$RUNTIME_DIR/agent_role" ]]; then
    AGENT_ROLE=$(cat "$RUNTIME_DIR/agent_role" 2>/dev/null || echo "")
fi

# Agent identity: PPID uniquely identifies the Claude Code process.
# CONTEXT_GUARD_AGENT_ID overrides for testing (PPID is read-only in bash).
AGENT_ID="${CONTEXT_GUARD_AGENT_ID:-$PPID}"
TURN_COUNT_FILE="$RUNTIME_DIR/turn_count_${AGENT_ID}"
SESSION_META_FILE="$RUNTIME_DIR/session_meta_${AGENT_ID}"

# Read per-agent config via resolver --dump + inline Python.
# AGENT_ROLE is set by launcher scripts (agent_launchers_common.md Section 2.1).
# Fallback chain: agents.<role>.context_guard_threshold > global context_guard_threshold > 45
# Enabled chain: agents.<role>.context_guard > default true
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESOLVER="$SCRIPT_DIR/../config/resolve_config.py"

read -r THRESHOLD GUARD_ENABLED < <(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" AGENT_ROLE="${AGENT_ROLE:-}" python3 -c "
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

# Use hook session_id, fall back to agent-ID
SESSION_ID="${HOOK_SESSION_ID:-agent-$AGENT_ID}"

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

# Clean up stale files from dead processes (runs every invocation, very cheap).
for f in "$RUNTIME_DIR"/turn_count_* "$RUNTIME_DIR"/session_meta_*; do
    [[ -f "$f" ]] || continue
    basename="${f##*/}"
    stale_id="${basename##*_}"
    # Only auto-clean numeric IDs (PIDs); non-numeric are test artifacts
    [[ "$stale_id" =~ ^[0-9]+$ ]] || continue
    [[ "$stale_id" == "$AGENT_ID" ]] && continue
    if ! kill -0 "$stale_id" 2>/dev/null; then
        rm -f "$f"
    else
        # PID is alive — check for PID recycling via process start time
        stale_meta="$RUNTIME_DIR/session_meta_${stale_id}"
        if [[ -f "$stale_meta" ]]; then
            stored_start=$(sed -n '3p' "$stale_meta" 2>/dev/null || echo "")
            actual_start=$(ps -p "$stale_id" -o lstart= 2>/dev/null || echo "")
            if [[ -n "$stored_start" && "$stored_start" != "unknown" && -n "$actual_start" && "$stored_start" != "$actual_start" ]]; then
                rm -f "$f"
            fi
        fi
    fi
done

# Remove legacy role-suffixed and unsuffixed files (one-time migration).
for f in "$RUNTIME_DIR"/turn_count "$RUNTIME_DIR"/turn_count_architect \
         "$RUNTIME_DIR"/turn_count_builder "$RUNTIME_DIR"/turn_count_qa \
         "$RUNTIME_DIR"/session_id "$RUNTIME_DIR"/session_id_architect \
         "$RUNTIME_DIR"/session_id_builder "$RUNTIME_DIR"/session_id_qa; do
    [[ -f "$f" ]] && rm -f "$f"
done

# Session detection using PPID + session_id.
#
# session_meta_<AGENT_ID> stores the session_id of the current conversation.
# - Meta file missing    → new agent process, initialize tracking files.
# - session_id matches   → same conversation, increment counter.
# - session_id differs   → subagent (Task tool) running under the same Claude Code
#                          process. Read counter without incrementing. Counter reset
#                          for /clear is handled by /pl-resume deleting session_meta,
#                          which triggers the "no meta" path → fresh start at 1.
IS_SUBAGENT=false
if [[ -f "$SESSION_META_FILE" ]]; then
    STORED_SESSION_ID=$(head -1 "$SESSION_META_FILE" 2>/dev/null || echo "")
    if [[ "$STORED_SESSION_ID" != "$SESSION_ID" ]]; then
        # Session ID mismatch — subagent running under same Claude Code process.
        # Read counter without incrementing. Still output guard status.
        IS_SUBAGENT=true
    fi
else
    # New agent process — initialize tracking files
    # session_meta format: line 1=session_id, line 2=role, line 3=process_start_time
    META_ROLE="${AGENT_ROLE:-unknown}"
    if [[ "$AGENT_ID" =~ ^[0-9]+$ ]]; then
        META_START_TIME=$(ps -p "$AGENT_ID" -o lstart= 2>/dev/null || echo "unknown")
    else
        META_START_TIME="unknown"
    fi
    printf '%s\n%s\n%s\n' "$SESSION_ID" "$META_ROLE" "$META_START_TIME" > "$SESSION_META_FILE"
    echo "0" > "$TURN_COUNT_FILE"
fi

# Read current count and increment (unless subagent — subagents read without incrementing).
# Counter always increments when not a subagent, even when guard disabled.
COUNT=$(cat "$TURN_COUNT_FILE" 2>/dev/null || echo "0")
if [[ "$IS_SUBAGENT" != "true" ]]; then
    COUNT=$((COUNT + 1))
    echo "$COUNT" > "$TURN_COUNT_FILE"
fi

# When guard is disabled, no output — counter still increments in background.
if [[ "$GUARD_ENABLED" != "true" ]]; then
    exit 0
fi

# Output context status on every turn via additionalContext.
# PostToolUse hooks MUST output JSON with additionalContext for agent visibility.
# Format: "COUNT / THRESHOLD used" where COUNT = turns consumed (higher = closer to limit).
# Also emit color-coded status line to stderr for user visibility in terminal.
if [[ $COUNT -lt $THRESHOLD ]]; then
    STATUS_MSG="CONTEXT GUARD: ${COUNT} / ${THRESHOLD} used"
else
    STATUS_MSG="CONTEXT GUARD: ${COUNT} / ${THRESHOLD} used -- Run /pl-resume save, then /clear, then /pl-resume to continue."
fi

# Color-coded stderr output (Section 2.4.1).
# Zones: Normal (no color), Warning (>=80%), Critical (>=92%).
# ANSI true-color (24-bit) from design tokens. No color when stderr is not a terminal.
WARN_AT=$((THRESHOLD * 80 / 100))
CRIT_AT=$((THRESHOLD * 92 / 100))

if [[ -t 2 ]]; then
    if [[ $COUNT -ge $CRIT_AT ]] || [[ $COUNT -ge $THRESHOLD ]]; then
        # Critical zone (or exceeded): --purlin-status-error #F87171
        printf '\033[38;2;248;113;113m%s\033[0m\n' "$STATUS_MSG" >&2
    elif [[ $COUNT -ge $WARN_AT ]]; then
        # Warning zone: --purlin-status-warning #FB923C
        printf '\033[38;2;251;146;60m%s\033[0m\n' "$STATUS_MSG" >&2
    else
        # Normal zone: no color
        echo "$STATUS_MSG" >&2
    fi
else
    # Not a terminal — plain text, no ANSI codes
    echo "$STATUS_MSG" >&2
fi

# JSON additionalContext — always uncolored (plain text)
cat <<GUARDJSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"${STATUS_MSG}"}}
GUARDJSON
