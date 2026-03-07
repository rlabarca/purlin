#!/bin/bash
# test_context_guard.sh — Automated tests for context_guard.sh
# Covers all automated scenarios from features/context_guard.md.
# Produces tests/context_guard/tests.json.
#
# The hook uses PPID as unique agent identity. Since PPID is read-only in bash,
# tests use CONTEXT_GUARD_AGENT_ID to simulate different agent processes.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
ERRORS=""

log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

# Helper to write 3-line session_meta (session_id, role, process_start_time)
write_session_meta() {
    local file="$1" session_id="$2" role="${3:-unknown}" start_time="${4:-unknown}"
    printf '%s\n%s\n%s\n' "$session_id" "$role" "$start_time" > "$file"
}

# Compute SESSION_HASH matching the hook's algorithm: cksum of session_id
compute_hash() {
    echo -n "$1" | cksum | cut -d' ' -f1
}

SANDBOX=""
cleanup_sandbox() {
    if [[ -n "${SANDBOX:-}" && -d "$SANDBOX" ]]; then
        rm -rf "$SANDBOX"
    fi
}

setup_sandbox() {
    SANDBOX="$(mktemp -d)"
    trap cleanup_sandbox EXIT
    mkdir -p "$SANDBOX/.purlin/runtime"
    mkdir -p "$SANDBOX/tools/hooks"
    mkdir -p "$SANDBOX/tools/config"
    cp "$SCRIPT_DIR/context_guard.sh" "$SANDBOX/tools/hooks/"
    cp "$SCRIPT_DIR/../config/resolve_config.py" "$SANDBOX/tools/config/"
}

# Run context_guard.sh with a given session_id and agent_id.
# Args: session_id [agent_role] [agent_id]
run_guard() {
    local session_id="${1:-test-session}"
    local agent_role="${2:-}"
    local agent_id="${3:-test-agent}"
    if [[ -n "$agent_role" ]]; then
        echo "{\"session_id\":\"$session_id\"}" | \
            PURLIN_PROJECT_ROOT="$SANDBOX" AGENT_ROLE="$agent_role" \
            CONTEXT_GUARD_AGENT_ID="$agent_id" \
            bash "$SANDBOX/tools/hooks/context_guard.sh"
    else
        echo "{\"session_id\":\"$session_id\"}" | \
            PURLIN_PROJECT_ROOT="$SANDBOX" \
            CONTEXT_GUARD_AGENT_ID="$agent_id" \
            bash -c 'unset AGENT_ROLE; bash "$1"' _ "$SANDBOX/tools/hooks/context_guard.sh"
    fi
}

echo "==============================="
echo "Context Guard Tests"
echo "==============================="

###############################################################################
# Scenario 1: Counter increments on each invocation
###############################################################################
echo ""
echo "[Scenario] Counter increments on each invocation"
setup_sandbox

HASH1=$(compute_hash "session-1")
run_guard "session-1" "" "agent-1" >/dev/null 2>&1
run_guard "session-1" "" "agent-1" >/dev/null 2>&1
run_guard "session-1" "" "agent-1" >/dev/null 2>&1

ACTUAL=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-1_${HASH1}")
if [[ "$ACTUAL" == "3" ]]; then
    log_pass "Turn count is 3 after 3 invocations"
else
    log_fail "Expected turn count 3, got '$ACTUAL'"
fi
cleanup_sandbox

###############################################################################
# Scenario 2: Status output on every turn when guard enabled
###############################################################################
echo ""
echo "[Scenario] Status output on every turn when guard enabled"
setup_sandbox

echo '{"context_guard_threshold": 10}' > "$SANDBOX/.purlin/config.json"
# Pre-seed session meta and counter (simulates an existing session)
HASH2=$(compute_hash "session-2")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-2" "session-2"
echo "2" > "$SANDBOX/.purlin/runtime/turn_count_agent-2_${HASH2}"

OUTPUT=$(run_guard "session-2" "" "agent-2" 2>&1)
if echo "$OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 3 / 10 used"'; then
    log_pass "Status output shows CONTEXT GUARD: 3 / 10 used"
else
    log_fail "Expected 'CONTEXT GUARD: 3 / 10 used' in additionalContext, got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 3: Exceeded threshold appends evacuation instructions
###############################################################################
echo ""
echo "[Scenario] Exceeded threshold appends evacuation instructions"
setup_sandbox

echo '{"context_guard_threshold": 5}' > "$SANDBOX/.purlin/config.json"
HASH3=$(compute_hash "session-3")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-3" "session-3"
echo "5" > "$SANDBOX/.purlin/runtime/turn_count_agent-3_${HASH3}"

OUTPUT=$(run_guard "session-3" "" "agent-3" 2>&1)
if echo "$OUTPUT" | grep -q "CONTEXT GUARD: 6 / 5 used -- Run /pl-resume save"; then
    log_pass "Exceeded output shows CONTEXT GUARD: 6 / 5 with evacuation instructions"
else
    log_fail "Expected 'CONTEXT GUARD: 6 / 5 used -- Run /pl-resume save...', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 4: Counter resets on new agent process (different AGENT_ID)
###############################################################################
echo ""
echo "[Scenario] Counter resets on new agent process"
setup_sandbox

# Old agent had 25 turns
OLD_HASH=$(compute_hash "old-session")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_old-agent" "old-session"
echo "25" > "$SANDBOX/.purlin/runtime/turn_count_old-agent_${OLD_HASH}"

# New agent process (different AGENT_ID) starts fresh
NEW_HASH=$(compute_hash "new-session")
run_guard "new-session" "" "new-agent" >/dev/null 2>&1

ACTUAL=$(cat "$SANDBOX/.purlin/runtime/turn_count_new-agent_${NEW_HASH}")
if [[ "$ACTUAL" == "1" ]]; then
    log_pass "New agent starts at count 1 (fresh counter)"
else
    log_fail "Expected turn count 1 for new agent, got '$ACTUAL'"
fi
# Old agent's file should be untouched
OLD=$(cat "$SANDBOX/.purlin/runtime/turn_count_old-agent_${OLD_HASH}")
if [[ "$OLD" == "25" ]]; then
    log_pass "Old agent's counter untouched at 25"
else
    log_fail "Expected old agent count 25, got '$OLD'"
fi
cleanup_sandbox

###############################################################################
# Scenario 5: Default threshold when config key absent
###############################################################################
echo ""
echo "[Scenario] Default threshold when config key absent"
setup_sandbox

echo '{"cdd_port": 9086}' > "$SANDBOX/.purlin/config.json"

OUTPUT=$(run_guard "session-5" "" "agent-5" 2>&1)
if echo "$OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 1 / 45 used"'; then
    log_pass "Default threshold is 45 (shows 1 / 45 used)"
else
    log_fail "Expected 'CONTEXT GUARD: 1 / 45 used' with default threshold, got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 6: Per-agent threshold overrides global
###############################################################################
echo ""
echo "[Scenario] Per-agent threshold overrides global"
setup_sandbox

echo '{"context_guard_threshold": 45, "agents": {"builder": {"context_guard_threshold": 30, "model": "claude-opus-4-6"}}}' > "$SANDBOX/.purlin/config.json"

OUTPUT=$(run_guard "session-6" "builder" "agent-6" 2>&1)
if echo "$OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 1 / 30 used"'; then
    log_pass "Per-agent threshold 30 used instead of global 45"
else
    log_fail "Expected 'CONTEXT GUARD: 1 / 30 used', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 7: Per-agent guard disabled suppresses output
###############################################################################
echo ""
echo "[Scenario] Per-agent guard disabled suppresses output"
setup_sandbox

echo '{"context_guard_threshold": 45, "agents": {"architect": {"context_guard": false, "model": "claude-opus-4-6"}}}' > "$SANDBOX/.purlin/config.json"
HASH7=$(compute_hash "session-7")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-7" "session-7"
echo "10" > "$SANDBOX/.purlin/runtime/turn_count_agent-7_${HASH7}"

OUTPUT=$(run_guard "session-7" "architect" "agent-7" 2>&1)
COUNTER=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-7_${HASH7}")

if [[ -z "$OUTPUT" ]] && [[ "$COUNTER" == "11" ]]; then
    log_pass "No output when guard disabled, counter still incremented to 11"
else
    log_fail "Expected no output and count=11, got output='$OUTPUT' count='$COUNTER'"
fi
cleanup_sandbox

###############################################################################
# Scenario 8: Missing AGENT_ROLE falls back to global
###############################################################################
echo ""
echo "[Scenario] Missing AGENT_ROLE falls back to global"
setup_sandbox

echo '{"context_guard_threshold": 50, "agents": {"builder": {"context_guard_threshold": 30, "model": "claude-opus-4-6"}}}' > "$SANDBOX/.purlin/config.json"

# Run without AGENT_ROLE — should use global threshold 50
OUTPUT=$(run_guard "session-8" "" "agent-8" 2>&1)
if echo "$OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 1 / 50 used"'; then
    log_pass "Global threshold 50 used when AGENT_ROLE unset"
else
    log_fail "Expected 'CONTEXT GUARD: 1 / 50 used', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 9: Exceeded output repeats on subsequent turns
###############################################################################
echo ""
echo "[Scenario] Exceeded output repeats on subsequent turns"
setup_sandbox

echo '{"context_guard_threshold": 2}' > "$SANDBOX/.purlin/config.json"
HASH9=$(compute_hash "session-9")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-9" "session-9"
echo "3" > "$SANDBOX/.purlin/runtime/turn_count_agent-9_${HASH9}"

OUTPUT=$(run_guard "session-9" "" "agent-9" 2>&1)
if echo "$OUTPUT" | grep -q "CONTEXT GUARD: 4 / 2 used -- Run /pl-resume save"; then
    log_pass "Exceeded output repeats: CONTEXT GUARD: 4 / 2 used"
else
    log_fail "Expected 'CONTEXT GUARD: 4 / 2 used -- Run /pl-resume save...', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 10: Per-agent threshold used when AGENT_ROLE is set
###############################################################################
echo ""
echo "[Scenario] Per-agent threshold used when AGENT_ROLE is set"
setup_sandbox

echo '{"context_guard_threshold": 45, "agents": {"builder": {"context_guard_threshold": 60, "model": "claude-opus-4-6"}}}' > "$SANDBOX/.purlin/config.json"

OUTPUT=$(run_guard "session-10" "builder" "agent-10" 2>&1)
if echo "$OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 1 / 60 used"'; then
    log_pass "Per-agent threshold 60 used for builder"
else
    log_fail "Expected 'CONTEXT GUARD: 1 / 60 used', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 11: Context clear produces fresh counter
###############################################################################
echo ""
echo "[Scenario] Context clear produces fresh counter"
setup_sandbox

echo '{"context_guard_threshold": 50}' > "$SANDBOX/.purlin/config.json"
HASH_A=$(compute_hash "session-A")

# Session A runs 3 times — accumulates count
run_guard "session-A" "" "agent-11" >/dev/null 2>&1
run_guard "session-A" "" "agent-11" >/dev/null 2>&1
run_guard "session-A" "" "agent-11" >/dev/null 2>&1

# Verify session A counter
COUNTER_A=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-11_${HASH_A}" 2>/dev/null || echo "MISSING")
if [[ "$COUNTER_A" == "3" ]]; then
    log_pass "Session A counter at 3"
else
    log_fail "Expected session A count=3, got '$COUNTER_A'"
fi

# Context clear → new session_id (session B)
HASH_B=$(compute_hash "session-B")
run_guard "session-B" "" "agent-11" >/dev/null 2>&1

# Session B should start at 1
COUNTER_B=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-11_${HASH_B}" 2>/dev/null || echo "MISSING")
if [[ "$COUNTER_B" == "1" ]]; then
    log_pass "Fresh session B starts at count 1"
else
    log_fail "Expected session B count=1, got '$COUNTER_B'"
fi

# Session A counter should be unaffected
COUNTER_A_AFTER=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-11_${HASH_A}" 2>/dev/null || echo "MISSING")
if [[ "$COUNTER_A_AFTER" == "3" ]]; then
    log_pass "Session A counter still at 3 after session B started"
else
    log_fail "Expected session A count=3 after session B, got '$COUNTER_A_AFTER'"
fi
cleanup_sandbox

###############################################################################
# Scenario 12: Subagent gets independent counter
###############################################################################
echo ""
echo "[Scenario] Subagent gets independent counter"
setup_sandbox

echo '{"context_guard_threshold": 50}' > "$SANDBOX/.purlin/config.json"
HASH_PARENT=$(compute_hash "parent-session")
HASH_SUB=$(compute_hash "subagent-session")

# Parent session runs 5 times
for i in $(seq 1 5); do
    run_guard "parent-session" "" "agent-12" >/dev/null 2>&1
done

# Subagent runs with different session_id under same PPID
run_guard "subagent-session" "" "agent-12" >/dev/null 2>&1

# Parent counter should still be at 5 (subagent didn't inflate it)
PARENT_COUNT=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-12_${HASH_PARENT}" 2>/dev/null || echo "MISSING")
if [[ "$PARENT_COUNT" == "5" ]]; then
    log_pass "Parent counter at 5 (subagent did not inflate)"
else
    log_fail "Expected parent count=5, got '$PARENT_COUNT'"
fi

# Subagent counter should be at 1 (independent file)
SUB_COUNT=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-12_${HASH_SUB}" 2>/dev/null || echo "MISSING")
if [[ "$SUB_COUNT" == "1" ]]; then
    log_pass "Subagent counter at 1 (independent file)"
else
    log_fail "Expected subagent count=1, got '$SUB_COUNT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 13: Parallel invocations count correctly (race condition)
###############################################################################
echo ""
echo "[Scenario] Parallel invocations count correctly"
setup_sandbox

# Run 10 instances in parallel with the same session and agent
HASH13=$(compute_hash "session-13")
for i in $(seq 1 10); do
    run_guard "session-13" "" "agent-13" >/dev/null 2>&1 &
done
wait

ACTUAL=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-13_${HASH13}")
if [[ "$ACTUAL" == "10" ]]; then
    log_pass "Parallel invocations all counted: 10/10"
else
    log_fail "Expected turn count 10 from 10 parallel invocations, got '$ACTUAL'"
fi
cleanup_sandbox

###############################################################################
# Scenario 14: Different agent IDs isolate counters
###############################################################################
echo ""
echo "[Scenario] Different agent IDs isolate counters"
setup_sandbox

echo '{"context_guard_threshold": 10}' > "$SANDBOX/.purlin/config.json"

# Agent A runs 3 times
run_guard "session-a" "" "agent-a" >/dev/null 2>&1
run_guard "session-a" "" "agent-a" >/dev/null 2>&1
run_guard "session-a" "" "agent-a" >/dev/null 2>&1

# Agent B runs 5 times (different agent, simulating different Claude Code process)
run_guard "session-b" "" "agent-b" >/dev/null 2>&1
run_guard "session-b" "" "agent-b" >/dev/null 2>&1
run_guard "session-b" "" "agent-b" >/dev/null 2>&1
run_guard "session-b" "" "agent-b" >/dev/null 2>&1
run_guard "session-b" "" "agent-b" >/dev/null 2>&1

HASH_A=$(compute_hash "session-a")
HASH_B=$(compute_hash "session-b")
A_COUNT=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-a_${HASH_A}" 2>/dev/null || echo "MISSING")
B_COUNT=$(cat "$SANDBOX/.purlin/runtime/turn_count_agent-b_${HASH_B}" 2>/dev/null || echo "MISSING")

if [[ "$A_COUNT" == "3" ]] && [[ "$B_COUNT" == "5" ]]; then
    log_pass "Agent-A=3, Agent-B=5 in separate files"
else
    log_fail "Expected A=3, B=5, got A='$A_COUNT', B='$B_COUNT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 15: Guard output on every tool call with no silent exits
###############################################################################
echo ""
echo "[Scenario] Guard output on every tool call with no silent exits"
setup_sandbox

echo '{"context_guard_threshold": 10}' > "$SANDBOX/.purlin/config.json"

# New session call
OUTPUT_NEW=$(run_guard "session-15" "" "agent-15" 2>&1)

# Same session call
OUTPUT_SAME=$(run_guard "session-15" "" "agent-15" 2>&1)

# New session via context clear (different session_id, same agent)
OUTPUT_NEWCONV=$(run_guard "session-15-cleared" "" "agent-15" 2>&1)

ALL_HAVE_OUTPUT=true
for label_output in "new:$OUTPUT_NEW" "same:$OUTPUT_SAME" "context-clear:$OUTPUT_NEWCONV"; do
    label="${label_output%%:*}"
    output="${label_output#*:}"
    if ! echo "$output" | grep -q "CONTEXT GUARD:"; then
        log_fail "No CONTEXT GUARD output for $label session call: '$output'"
        ALL_HAVE_OUTPUT=false
    fi
done
if [[ "$ALL_HAVE_OUTPUT" == "true" ]]; then
    log_pass "All code paths (new, same, context-clear) produce CONTEXT GUARD output"
fi
cleanup_sandbox

###############################################################################
# Scenario 16: Session meta contains 3 lines (session_id, role, start_time)
###############################################################################
echo ""
echo "[Scenario] Session meta contains 3 lines"
setup_sandbox

echo '{"context_guard_threshold": 10}' > "$SANDBOX/.purlin/config.json"

run_guard "session-16" "builder" "agent-16" >/dev/null 2>&1

META_LINES=$(wc -l < "$SANDBOX/.purlin/runtime/session_meta_agent-16" | tr -d ' ')
META_LINE1=$(sed -n '1p' "$SANDBOX/.purlin/runtime/session_meta_agent-16")
META_LINE2=$(sed -n '2p' "$SANDBOX/.purlin/runtime/session_meta_agent-16")
META_LINE3=$(sed -n '3p' "$SANDBOX/.purlin/runtime/session_meta_agent-16")

if [[ "$META_LINES" == "3" ]] && [[ "$META_LINE1" == "session-16" ]] && [[ "$META_LINE2" == "builder" ]] && [[ "$META_LINE3" == "unknown" ]]; then
    log_pass "session_meta has 3 lines: session_id=session-16, role=builder, start_time=unknown"
else
    log_fail "Expected 3-line meta (session-16/builder/unknown), got lines=$META_LINES l1='$META_LINE1' l2='$META_LINE2' l3='$META_LINE3'"
fi
cleanup_sandbox

###############################################################################
# Scenario 17: PID recycling detected and stale files cleaned up
###############################################################################
echo ""
echo "[Scenario] PID recycling detected and stale files cleaned up"
setup_sandbox

# Use current shell PID as a "stale" process (it IS alive, but with wrong start time)
STALE_PID=$$
STALE_HASH=$(compute_hash "stale-session")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_${STALE_PID}" "stale-session" "builder" "Mon Jan  1 00:00:00 2000"
echo "15" > "$SANDBOX/.purlin/runtime/turn_count_${STALE_PID}_${STALE_HASH}"

# Run guard with a different agent ID — cleanup should detect recycled PID
run_guard "test-session" "" "agent-recycled" >/dev/null 2>&1

if [[ ! -f "$SANDBOX/.purlin/runtime/turn_count_${STALE_PID}_${STALE_HASH}" ]] && \
   [[ ! -f "$SANDBOX/.purlin/runtime/session_meta_${STALE_PID}" ]]; then
    log_pass "PID recycling detected: stale files cleaned up"
else
    log_fail "Expected stale files to be cleaned up due to PID recycling"
fi
cleanup_sandbox

###############################################################################
# Scenario 18: Alive process with matching start time is preserved
###############################################################################
echo ""
echo "[Scenario] Alive process with matching start time is preserved"
setup_sandbox

LIVE_PID=$$
LIVE_HASH=$(compute_hash "active-session")
ACTUAL_START=$(ps -p $LIVE_PID -o lstart= 2>/dev/null)
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_${LIVE_PID}" "active-session" "builder" "$ACTUAL_START"
echo "10" > "$SANDBOX/.purlin/runtime/turn_count_${LIVE_PID}_${LIVE_HASH}"

run_guard "another-session" "" "agent-no-recycle" >/dev/null 2>&1

if [[ -f "$SANDBOX/.purlin/runtime/turn_count_${LIVE_PID}_${LIVE_HASH}" ]]; then
    log_pass "Alive process with matching start time preserved"
else
    log_fail "Alive process with matching start time was incorrectly cleaned up"
fi
cleanup_sandbox

###############################################################################
# Scenario 19: User-visible status line emitted to stderr
###############################################################################
echo ""
echo "[Scenario] User-visible status line emitted to stderr"
setup_sandbox

echo '{"context_guard_threshold": 45}' > "$SANDBOX/.purlin/config.json"
HASH19=$(compute_hash "session-19")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-19" "session-19"
echo "4" > "$SANDBOX/.purlin/runtime/turn_count_agent-19_${HASH19}"

STDERR_FILE="$SANDBOX/stderr_output"
STDOUT_OUTPUT=$(run_guard "session-19" "" "agent-19" 2>"$STDERR_FILE")
STDERR_OUTPUT=$(cat "$STDERR_FILE")

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD: 5 / 45 used"; then
    log_pass "stderr contains 'CONTEXT GUARD: 5 / 45 used'"
else
    log_fail "Expected stderr 'CONTEXT GUARD: 5 / 45 used', got: '$STDERR_OUTPUT'"
fi
if echo "$STDOUT_OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 5 / 45 used"'; then
    log_pass "stdout JSON additionalContext also contains 'CONTEXT GUARD: 5 / 45 used'"
else
    log_fail "Expected stdout additionalContext 'CONTEXT GUARD: 5 / 45 used', got: '$STDOUT_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 20: Exceeded status line emitted to stderr
###############################################################################
echo ""
echo "[Scenario] Exceeded status line emitted to stderr"
setup_sandbox

echo '{"context_guard_threshold": 5}' > "$SANDBOX/.purlin/config.json"
HASH20=$(compute_hash "session-20")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-20" "session-20"
echo "5" > "$SANDBOX/.purlin/runtime/turn_count_agent-20_${HASH20}"

STDERR_FILE="$SANDBOX/stderr_exceeded"
STDOUT_OUTPUT=$(run_guard "session-20" "" "agent-20" 2>"$STDERR_FILE")
STDERR_OUTPUT=$(cat "$STDERR_FILE")

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD: 6 / 5 used -- Run /pl-resume save"; then
    log_pass "stderr contains exceeded message with evacuation instructions"
else
    log_fail "Expected stderr exceeded message, got: '$STDERR_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 21: New session via context clear also emits stderr
###############################################################################
echo ""
echo "[Scenario] New session via context clear also emits stderr"
setup_sandbox

echo '{"context_guard_threshold": 10}' > "$SANDBOX/.purlin/config.json"
HASH21_MAIN=$(compute_hash "main-session-21")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-21" "main-session-21"
echo "7" > "$SANDBOX/.purlin/runtime/turn_count_agent-21_${HASH21_MAIN}"

# Context clear → new session_id → fresh counter file starting at 1
STDERR_FILE="$SANDBOX/stderr_context_clear"
STDOUT_OUTPUT=$(run_guard "cleared-session-21" "" "agent-21" 2>"$STDERR_FILE")
STDERR_OUTPUT=$(cat "$STDERR_FILE")

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD: 1 / 10 used"; then
    log_pass "Context-cleared session emits stderr status line with count 1"
else
    log_fail "Expected stderr 'CONTEXT GUARD: 1 / 10 used', got: '$STDERR_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 22: Stderr output is uncolored in normal zone
###############################################################################
echo ""
echo "[Scenario] Stderr output is uncolored in normal zone"
setup_sandbox

echo '{"context_guard_threshold": 50}' > "$SANDBOX/.purlin/config.json"
HASH22=$(compute_hash "session-22")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-22" "session-22"
echo "9" > "$SANDBOX/.purlin/runtime/turn_count_agent-22_${HASH22}"

# Use script(1) to simulate a terminal for stderr
STDERR_FILE="$SANDBOX/stderr_normal"
if [[ "$(uname)" == "Darwin" ]]; then
    script -q "$STDERR_FILE" bash -c '
        echo "{\"session_id\":\"session-22\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-22" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" >/dev/null
    ' >/dev/null 2>&1
else
    script -qc '
        echo "{\"session_id\":\"session-22\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-22" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" >/dev/null
    ' "$STDERR_FILE" >/dev/null 2>&1
fi
STDERR_OUTPUT=$(cat "$STDERR_FILE")

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD: 10 / 50 used" && \
   ! echo "$STDERR_OUTPUT" | grep -q $'\033\[38;2;'; then
    log_pass "Normal zone: no ANSI color codes in stderr"
else
    log_fail "Expected uncolored 'CONTEXT GUARD: 10 / 50 used', got: '$STDERR_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 23: Stderr output is warning-colored when within 20% of limit
###############################################################################
echo ""
echo "[Scenario] Stderr output is warning-colored when within 20% of limit"
setup_sandbox

echo '{"context_guard_threshold": 50}' > "$SANDBOX/.purlin/config.json"
HASH23=$(compute_hash "session-23")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-23" "session-23"
echo "39" > "$SANDBOX/.purlin/runtime/turn_count_agent-23_${HASH23}"

STDERR_FILE="$SANDBOX/stderr_warning"
if [[ "$(uname)" == "Darwin" ]]; then
    script -q "$STDERR_FILE" bash -c '
        echo "{\"session_id\":\"session-23\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-23" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" >/dev/null
    ' >/dev/null 2>&1
else
    script -qc '
        echo "{\"session_id\":\"session-23\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-23" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" >/dev/null
    ' "$STDERR_FILE" >/dev/null 2>&1
fi
STDERR_OUTPUT=$(cat "$STDERR_FILE")

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD: 40 / 50 used" && \
   echo "$STDERR_OUTPUT" | grep -qP '\x1b\[38;2;251;146;60m' 2>/dev/null || \
   echo "$STDERR_OUTPUT" | LC_ALL=C grep -q $'\033\[38;2;251;146;60m'; then
    log_pass "Warning zone: stderr contains warning color code"
else
    log_fail "Expected warning color \\033[38;2;251;146;60m in stderr, got: $(cat -v "$STDERR_FILE")"
fi
cleanup_sandbox

###############################################################################
# Scenario 24: Stderr output is critical-colored when within 8% of limit
###############################################################################
echo ""
echo "[Scenario] Stderr output is critical-colored when within 8% of limit"
setup_sandbox

echo '{"context_guard_threshold": 50}' > "$SANDBOX/.purlin/config.json"
HASH24=$(compute_hash "session-24")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-24" "session-24"
echo "45" > "$SANDBOX/.purlin/runtime/turn_count_agent-24_${HASH24}"

STDERR_FILE="$SANDBOX/stderr_critical"
if [[ "$(uname)" == "Darwin" ]]; then
    script -q "$STDERR_FILE" bash -c '
        echo "{\"session_id\":\"session-24\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-24" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" >/dev/null
    ' >/dev/null 2>&1
else
    script -qc '
        echo "{\"session_id\":\"session-24\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-24" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" >/dev/null
    ' "$STDERR_FILE" >/dev/null 2>&1
fi
STDERR_OUTPUT=$(cat "$STDERR_FILE")

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD: 46 / 50 used" && \
   echo "$STDERR_OUTPUT" | LC_ALL=C grep -q $'\033\[38;2;248;113;113m'; then
    log_pass "Critical zone: stderr contains critical color code"
else
    log_fail "Expected critical color \\033[38;2;248;113;113m in stderr, got: $(cat -v "$STDERR_FILE")"
fi
cleanup_sandbox

###############################################################################
# Scenario 25: Exceeded threshold uses critical color
###############################################################################
echo ""
echo "[Scenario] Exceeded threshold uses critical color"
setup_sandbox

echo '{"context_guard_threshold": 10}' > "$SANDBOX/.purlin/config.json"
HASH25=$(compute_hash "session-25")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-25" "session-25"
echo "10" > "$SANDBOX/.purlin/runtime/turn_count_agent-25_${HASH25}"

STDERR_FILE="$SANDBOX/stderr_exceeded_color"
if [[ "$(uname)" == "Darwin" ]]; then
    script -q "$STDERR_FILE" bash -c '
        echo "{\"session_id\":\"session-25\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-25" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" >/dev/null
    ' >/dev/null 2>&1
else
    script -qc '
        echo "{\"session_id\":\"session-25\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-25" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" >/dev/null
    ' "$STDERR_FILE" >/dev/null 2>&1
fi
STDERR_OUTPUT=$(cat "$STDERR_FILE")

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD: 11 / 10 used -- Run /pl-resume save" && \
   echo "$STDERR_OUTPUT" | LC_ALL=C grep -q $'\033\[38;2;248;113;113m'; then
    log_pass "Exceeded: stderr uses critical color with evacuation instructions"
else
    log_fail "Expected critical color + exceeded message, got: $(cat -v "$STDERR_FILE")"
fi
cleanup_sandbox

###############################################################################
# Scenario 26: No ANSI codes when stderr is not a terminal
###############################################################################
echo ""
echo "[Scenario] No ANSI codes when stderr is not a terminal"
setup_sandbox

echo '{"context_guard_threshold": 50}' > "$SANDBOX/.purlin/config.json"
HASH26=$(compute_hash "session-26")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-26" "session-26"
echo "45" > "$SANDBOX/.purlin/runtime/turn_count_agent-26_${HASH26}"

# Redirect stderr to file (NOT a terminal) — should produce no ANSI codes
STDERR_FILE="$SANDBOX/stderr_piped"
STDOUT_OUTPUT=$(run_guard "session-26" "" "agent-26" 2>"$STDERR_FILE")
STDERR_OUTPUT=$(cat "$STDERR_FILE")

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD: 46 / 50 used" && \
   ! cat -v "$STDERR_FILE" | grep -q '\^\\['; then
    log_pass "No ANSI codes in stderr when not a terminal"
else
    log_fail "Expected plain text (no ANSI) when piped, got: $(cat -v "$STDERR_FILE")"
fi
cleanup_sandbox

###############################################################################
# Scenario 27: JSON additionalContext remains uncolored regardless of zone
###############################################################################
echo ""
echo "[Scenario] JSON additionalContext remains uncolored regardless of zone"
setup_sandbox

echo '{"context_guard_threshold": 50}' > "$SANDBOX/.purlin/config.json"
HASH27=$(compute_hash "session-27")
write_session_meta "$SANDBOX/.purlin/runtime/session_meta_agent-27" "session-27"
echo "45" > "$SANDBOX/.purlin/runtime/turn_count_agent-27_${HASH27}"

STDERR_FILE="$SANDBOX/stderr_json_check"
if [[ "$(uname)" == "Darwin" ]]; then
    STDOUT_OUTPUT=$(script -q "$STDERR_FILE" bash -c '
        echo "{\"session_id\":\"session-27\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-27" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" 2>/dev/null
    ' 2>/dev/null)
else
    STDOUT_OUTPUT=$(script -qc '
        echo "{\"session_id\":\"session-27\"}" | \
            PURLIN_PROJECT_ROOT="'"$SANDBOX"'" \
            CONTEXT_GUARD_AGENT_ID="agent-27" \
            bash "'"$SANDBOX"'/tools/hooks/context_guard.sh" 2>/dev/null
    ' /dev/null 2>/dev/null)
fi

if echo "$STDOUT_OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 46 / 50 used"' && \
   ! echo "$STDOUT_OUTPUT" | cat -v | grep -q '\^\\['; then
    log_pass "JSON additionalContext is plain text (no ANSI codes)"
else
    log_fail "Expected uncolored JSON output, got: $(echo "$STDOUT_OUTPUT" | cat -v)"
fi
cleanup_sandbox

###############################################################################
# Summary
###############################################################################
TOTAL=$((PASS + FAIL))
echo ""
echo "==============================="
echo "Results: $PASS passed, $FAIL failed (of $TOTAL)"
if [[ $FAIL -gt 0 ]]; then
    echo "  Failures:"
    echo -e "$ERRORS"
fi
echo "==============================="

# Write tests/context_guard/tests.json
OUTDIR="$TESTS_DIR/context_guard"
mkdir -p "$OUTDIR"
echo "{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL}" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
