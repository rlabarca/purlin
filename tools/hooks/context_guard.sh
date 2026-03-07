#!/usr/bin/env bash
# context_guard.sh — PostToolUse hook that monitors session turn count
# and outputs context budget status on every tool call.
#
# Per-session counter design: each combination of Claude Code process and
# session gets its own counter file. This eliminates the ambiguity between
# subagents and context clears:
# - New process = new PPID = fresh counter
# - Context clear = new session_id = new SESSION_HASH = fresh counter file
# - Subagents = different session_id = independent counter file
# - Multiple agents (even same role) = different PPIDs = no collision
#
# Files: turn_count_<AGENT_ID>_<SESSION_HASH>, session_meta_<AGENT_ID>
# AGENT_ID defaults to $PPID; override via CONTEXT_GUARD_AGENT_ID for testing.
#
# Input: JSON on stdin from Claude Code (contains session_id, cwd, etc.)
# Output: JSON with additionalContext on every turn (when guard enabled).
#         Plain stdout is NOT visible to the agent in PostToolUse hooks.
#         Must use hookSpecificOutput.additionalContext for agent visibility.

set -uo pipefail

# Guaranteed clean exit with JSON output on any failure path.
# Problem: the old ERR trap did `exit 0` which skipped JSON output entirely.
# Claude Code interprets missing JSON as "hook error" even with exit code 0.
# Fix: EXIT trap always produces fallback JSON if the normal path didn't.
_JSON_DONE=0
_LOCK_ACQUIRED=0
LOCK_DIR=""
STATUS_MSG=""

_on_exit() {
    # Always produce JSON — missing JSON causes "hook error" in Claude Code.
    if [[ "$_JSON_DONE" -eq 0 ]]; then
        _JSON_DONE=1
        local msg="${STATUS_MSG:-CONTEXT GUARD: unavailable}"
        printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"%s"}}\n' "$msg"
    fi
    # Release lock if acquired.
    if [[ "$_LOCK_ACQUIRED" -eq 1 && -n "$LOCK_DIR" ]]; then
        rmdir "$LOCK_DIR" 2>/dev/null || true
    fi
}

trap '_on_exit' EXIT
# ERR trap: any error → exit 0 → EXIT trap fires → JSON + lock cleanup.
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

# When guard is disabled, exit immediately — no counter increment, no output.
# Re-enabling mid-session resumes from wherever the counter was (or 0 if never active).
if [[ "$GUARD_ENABLED" != "true" ]]; then
    _JSON_DONE=1  # Suppress fallback JSON from EXIT trap
    exit 0
fi

# Compute SESSION_HASH from session_id for per-session counter files.
# Each session gets its own counter file: turn_count_<AGENT_ID>_<SESSION_HASH>.
# Fallback: when session_id unavailable, hash "agent-<AGENT_ID>" for single file per PPID.
SESSION_ID="${HOOK_SESSION_ID:-agent-$AGENT_ID}"
SESSION_HASH=$(echo -n "$SESSION_ID" | cksum | cut -d' ' -f1)
TURN_COUNT_FILE="$RUNTIME_DIR/turn_count_${AGENT_ID}_${SESSION_HASH}"
SESSION_META_FILE="$RUNTIME_DIR/session_meta_${AGENT_ID}"

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
_LOCK_ACQUIRED=1

# Clean up stale files from dead processes (runs every invocation, very cheap).
# For per-session counter files (turn_count_<PID>_<HASH>), extract PID as the
# middle segment between first underscore after "turn_count_" and the next underscore.
# Uses space-padded strings for PID tracking (portable — no bash 4+ associative arrays).
_DEAD_PIDS=" "
_ALIVE_PIDS=" "
for f in "$RUNTIME_DIR"/turn_count_* "$RUNTIME_DIR"/session_meta_*; do
    [[ -f "$f" ]] || continue
    fname="${f##*/}"
    # Extract PID: for turn_count_<PID>_<HASH>, strip prefix then take first segment
    # For session_meta_<PID>, strip prefix and use the whole suffix
    if [[ "$fname" == turn_count_* ]]; then
        suffix="${fname#turn_count_}"
        stale_id="${suffix%%_*}"
    elif [[ "$fname" == session_meta_* ]]; then
        stale_id="${fname#session_meta_}"
    else
        continue
    fi
    # Only auto-clean numeric IDs (PIDs); non-numeric are test artifacts
    [[ "$stale_id" =~ ^[0-9]+$ ]] || continue
    [[ "$stale_id" == "$AGENT_ID" ]] && continue
    # Skip if we already checked this PID
    if [[ "$_DEAD_PIDS" == *" $stale_id "* ]]; then
        rm -f "$f"
        continue
    elif [[ "$_ALIVE_PIDS" == *" $stale_id "* ]]; then
        continue
    fi
    if ! kill -0 "$stale_id" 2>/dev/null; then
        _DEAD_PIDS="${_DEAD_PIDS}${stale_id} "
        # Dead process — delete all its files
        rm -f "$RUNTIME_DIR"/turn_count_${stale_id}_* "$RUNTIME_DIR/session_meta_${stale_id}"
    else
        # PID is alive — check for PID recycling via process start time
        stale_meta="$RUNTIME_DIR/session_meta_${stale_id}"
        if [[ -f "$stale_meta" ]]; then
            stored_start=$(sed -n '3p' "$stale_meta" 2>/dev/null || echo "")
            actual_start=$(ps -p "$stale_id" -o lstart= 2>/dev/null || echo "")
            if [[ -n "$stored_start" && "$stored_start" != "unknown" && -n "$actual_start" && "$stored_start" != "$actual_start" ]]; then
                _DEAD_PIDS="${_DEAD_PIDS}${stale_id} "
                rm -f "$RUNTIME_DIR"/turn_count_${stale_id}_* "$RUNTIME_DIR/session_meta_${stale_id}"
            else
                _ALIVE_PIDS="${_ALIVE_PIDS}${stale_id} "
            fi
        else
            _ALIVE_PIDS="${_ALIVE_PIDS}${stale_id} "
        fi
    fi
done

# Remove legacy single-file-per-PPID counter files (one-time migration).
# Old format: turn_count_<PID> (no session hash). Also legacy role-suffixed files.
for f in "$RUNTIME_DIR"/turn_count "$RUNTIME_DIR"/turn_count_architect \
         "$RUNTIME_DIR"/turn_count_builder "$RUNTIME_DIR"/turn_count_qa \
         "$RUNTIME_DIR"/session_id "$RUNTIME_DIR"/session_id_architect \
         "$RUNTIME_DIR"/session_id_builder "$RUNTIME_DIR"/session_id_qa; do
    [[ -f "$f" ]] && rm -f "$f"
done
# Migrate old turn_count_<PID> files (no underscore after PID = old format)
for f in "$RUNTIME_DIR"/turn_count_*; do
    [[ -f "$f" ]] || continue
    basename="${f##*/}"
    suffix="${basename#turn_count_}"
    # Old format has no second underscore (just a PID). New format has PID_HASH.
    if [[ "$suffix" =~ ^[0-9]+$ ]]; then
        rm -f "$f"
    fi
done

# Session meta: write/update on first invocation per AGENT_ID or when session_id changes.
# session_meta format: line 1=session_id, line 2=role, line 3=process_start_time
if [[ -f "$SESSION_META_FILE" ]]; then
    STORED_SESSION_ID=$(head -1 "$SESSION_META_FILE" 2>/dev/null || echo "")
    if [[ "$STORED_SESSION_ID" != "$SESSION_ID" ]]; then
        # Session ID changed — update meta (new session or subagent)
        META_ROLE="${AGENT_ROLE:-unknown}"
        if [[ "$AGENT_ID" =~ ^[0-9]+$ ]]; then
            META_START_TIME=$(ps -p "$AGENT_ID" -o lstart= 2>/dev/null || echo "unknown")
        else
            META_START_TIME="unknown"
        fi
        printf '%s\n%s\n%s\n' "$SESSION_ID" "$META_ROLE" "$META_START_TIME" > "$SESSION_META_FILE"
    fi
else
    # New agent process — initialize session meta
    META_ROLE="${AGENT_ROLE:-unknown}"
    if [[ "$AGENT_ID" =~ ^[0-9]+$ ]]; then
        META_START_TIME=$(ps -p "$AGENT_ID" -o lstart= 2>/dev/null || echo "unknown")
    else
        META_START_TIME="unknown"
    fi
    printf '%s\n%s\n%s\n' "$SESSION_ID" "$META_ROLE" "$META_START_TIME" > "$SESSION_META_FILE"
fi

# Read current count and increment. Each session has its own counter file,
# so subagents and context clears automatically get independent counters.
COUNT=$(cat "$TURN_COUNT_FILE" 2>/dev/null || echo "0")
COUNT=$((COUNT + 1))
echo "$COUNT" > "$TURN_COUNT_FILE"

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
_JSON_DONE=1
cat <<GUARDJSON
{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"${STATUS_MSG}"}}
GUARDJSON
