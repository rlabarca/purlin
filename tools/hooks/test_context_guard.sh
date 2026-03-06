#!/bin/bash
# test_context_guard.sh — Automated tests for context_guard.sh
# Covers all 9 automated scenarios from features/context_guard.md.
# Produces tests/context_guard/tests.json.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
ERRORS=""

log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

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

# Run context_guard.sh with a given session_id, using the sandbox as project root.
# Optional second arg: AGENT_ROLE value (empty string = unset).
run_guard() {
    local session_id="${1:-test-session}"
    local agent_role="${2:-}"
    if [[ -n "$agent_role" ]]; then
        echo "{\"session_id\":\"$session_id\"}" | \
            PURLIN_PROJECT_ROOT="$SANDBOX" AGENT_ROLE="$agent_role" bash "$SANDBOX/tools/hooks/context_guard.sh"
    else
        echo "{\"session_id\":\"$session_id\"}" | \
            PURLIN_PROJECT_ROOT="$SANDBOX" bash -c 'unset AGENT_ROLE; bash "$1"' _ "$SANDBOX/tools/hooks/context_guard.sh"
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

run_guard "session-1" >/dev/null 2>&1
run_guard "session-1" >/dev/null 2>&1
run_guard "session-1" >/dev/null 2>&1

ACTUAL=$(cat "$SANDBOX/.purlin/runtime/turn_count")
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
echo "2" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-2" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-2" 2>&1)
if echo "$OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 7/10"'; then
    log_pass "Status output shows CONTEXT GUARD: 7/10"
else
    log_fail "Expected 'CONTEXT GUARD: 7/10' in additionalContext, got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 3: Exceeded threshold appends evacuation instructions
###############################################################################
echo ""
echo "[Scenario] Exceeded threshold appends evacuation instructions"
setup_sandbox

echo '{"context_guard_threshold": 5}' > "$SANDBOX/.purlin/config.json"
echo "5" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-3" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-3" 2>&1)
if echo "$OUTPUT" | grep -q "CONTEXT GUARD: -1/5 -- Run /pl-resume save"; then
    log_pass "Exceeded output shows CONTEXT GUARD: -1/5 with evacuation instructions"
else
    log_fail "Expected 'CONTEXT GUARD: -1/5 -- Run /pl-resume save...', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 4: Counter resets on new session
###############################################################################
echo ""
echo "[Scenario] Counter resets on new session"
setup_sandbox

echo "25" > "$SANDBOX/.purlin/runtime/turn_count"
echo "old-session" > "$SANDBOX/.purlin/runtime/session_id"
# Backdate turn_count to simulate stale file (>120s) so subagent detection triggers reset
touch -t 202501010000 "$SANDBOX/.purlin/runtime/turn_count"

run_guard "new-session" >/dev/null 2>&1

ACTUAL=$(cat "$SANDBOX/.purlin/runtime/turn_count")
if [[ "$ACTUAL" == "1" ]]; then
    log_pass "Counter reset to 1 on new session"
else
    log_fail "Expected turn count 1 after session reset, got '$ACTUAL'"
fi
cleanup_sandbox

###############################################################################
# Scenario 5: Default threshold when config key absent
###############################################################################
echo ""
echo "[Scenario] Default threshold when config key absent"
setup_sandbox

# Config without threshold key, AGENT_ROLE unset
echo '{"cdd_port": 9086}' > "$SANDBOX/.purlin/config.json"
echo "45" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-5" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-5" 2>&1)
if echo "$OUTPUT" | grep -q "CONTEXT GUARD: -1/45 -- Run /pl-resume save"; then
    log_pass "Default threshold is 45 (exceeded at turn 46/45)"
else
    log_fail "Expected 'CONTEXT GUARD: -1/45' with default threshold, got: '$OUTPUT'"
fi

# Also verify normal output at pre-threshold (turn 45/45)
echo "44" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-5b" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-5b" 2>&1)
if echo "$OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 0/45 -- Run /pl-resume save'; then
    log_pass "At exactly threshold (turn 45/45), remaining=0 triggers evacuation"
else
    log_fail "Expected 'CONTEXT GUARD: 0/45' at threshold, got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 6: Per-agent threshold overrides global
###############################################################################
echo ""
echo "[Scenario] Per-agent threshold overrides global"
setup_sandbox

echo '{"context_guard_threshold": 45, "agents": {"builder": {"context_guard_threshold": 30, "model": "claude-opus-4-6"}}}' > "$SANDBOX/.purlin/config.json"
echo "29" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-6" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-6" "builder" 2>&1)
if echo "$OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 0/30 -- Run /pl-resume save'; then
    log_pass "Per-agent threshold 30 used instead of global 45 (turn 30/30)"
else
    log_fail "Expected 'CONTEXT GUARD: 0/30', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 7: Per-agent guard disabled suppresses output
###############################################################################
echo ""
echo "[Scenario] Per-agent guard disabled suppresses output"
setup_sandbox

echo '{"context_guard_threshold": 45, "agents": {"architect": {"context_guard": false, "model": "claude-opus-4-6"}}}' > "$SANDBOX/.purlin/config.json"
echo "10" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-7" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-7" "architect" 2>&1)
COUNTER=$(cat "$SANDBOX/.purlin/runtime/turn_count")

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
echo "49" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-8" > "$SANDBOX/.purlin/runtime/session_id"

# Run without AGENT_ROLE — should use global threshold 50
OUTPUT=$(run_guard "session-8" 2>&1)
if echo "$OUTPUT" | grep -q '"additionalContext":"CONTEXT GUARD: 0/50 -- Run /pl-resume save'; then
    log_pass "Global threshold 50 used when AGENT_ROLE unset (turn 50/50)"
else
    log_fail "Expected 'CONTEXT GUARD: 0/50', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 9: Exceeded output repeats on subsequent turns
###############################################################################
echo ""
echo "[Scenario] Exceeded output repeats on subsequent turns"
setup_sandbox

echo '{"context_guard_threshold": 2}' > "$SANDBOX/.purlin/config.json"
echo "3" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-9" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-9" 2>&1)
if echo "$OUTPUT" | grep -q "CONTEXT GUARD: -2/2 -- Run /pl-resume save"; then
    log_pass "Exceeded output repeats: CONTEXT GUARD: -2/2"
else
    log_fail "Expected 'CONTEXT GUARD: -2/2 -- Run /pl-resume save...', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 10: Parallel invocations count correctly (race condition)
###############################################################################
echo ""
echo "[Scenario] Parallel invocations count correctly"
setup_sandbox

# Run 10 instances in parallel with the same session
for i in $(seq 1 10); do
    run_guard "session-10" >/dev/null 2>&1 &
done
wait

ACTUAL=$(cat "$SANDBOX/.purlin/runtime/turn_count")
if [[ "$ACTUAL" == "10" ]]; then
    log_pass "Parallel invocations all counted: 10/10"
else
    log_fail "Expected turn count 10 from 10 parallel invocations, got '$ACTUAL'"
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
