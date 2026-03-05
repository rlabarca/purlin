#!/bin/bash
# test_context_guard.sh — Automated tests for context_guard.sh
# Covers all 5 automated scenarios from features/context_guard.md.
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
run_guard() {
    local session_id="${1:-test-session}"
    echo "{\"session_id\":\"$session_id\"}" | \
        PURLIN_PROJECT_ROOT="$SANDBOX" bash "$SANDBOX/tools/hooks/context_guard.sh"
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
# Scenario 2: Warning fires when threshold exceeded
###############################################################################
echo ""
echo "[Scenario] Warning fires when threshold exceeded"
setup_sandbox

# Set threshold to 5
echo '{"context_guard_threshold": 5}' > "$SANDBOX/.purlin/config.json"

# Pre-set count to 5, same session
echo "5" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-2" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-2" 2>&1)
if echo "$OUTPUT" | grep -q "\[CONTEXT GUARD\] Turn 6/5"; then
    log_pass "Warning fires at turn 6/5"
else
    log_fail "Expected warning 'Turn 6/5', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 3: Counter resets on new session
###############################################################################
echo ""
echo "[Scenario] Counter resets on new session"
setup_sandbox

# Count at 25 with old session
echo "25" > "$SANDBOX/.purlin/runtime/turn_count"
echo "old-session" > "$SANDBOX/.purlin/runtime/session_id"

run_guard "new-session" >/dev/null 2>&1

ACTUAL=$(cat "$SANDBOX/.purlin/runtime/turn_count")
if [[ "$ACTUAL" == "1" ]]; then
    log_pass "Counter reset to 1 on new session"
else
    log_fail "Expected turn count 1 after session reset, got '$ACTUAL'"
fi
cleanup_sandbox

###############################################################################
# Scenario 4: Default threshold when config key absent
###############################################################################
echo ""
echo "[Scenario] Default threshold when config key absent"
setup_sandbox

# Config without threshold key
echo '{"cdd_port": 9086}' > "$SANDBOX/.purlin/config.json"

# Set count to 30 — next run will be 31 which exceeds default threshold of 30
echo "30" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-4" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-4" 2>&1)
if echo "$OUTPUT" | grep -q "\[CONTEXT GUARD\] Turn 31/30"; then
    log_pass "Default threshold is 30 (warning at turn 31/30)"
else
    log_fail "Expected warning 'Turn 31/30' with default threshold, got: '$OUTPUT'"
fi

# Also verify no warning at exactly threshold (turn 30/30)
echo "29" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-4b" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-4b" 2>&1)
if [[ -z "$OUTPUT" ]]; then
    log_pass "No warning at exactly threshold (turn 30/30)"
else
    log_fail "Expected no warning at threshold, got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 5: Warning repeats after threshold
###############################################################################
echo ""
echo "[Scenario] Warning repeats after threshold"
setup_sandbox

echo '{"context_guard_threshold": 2}' > "$SANDBOX/.purlin/config.json"
echo "3" > "$SANDBOX/.purlin/runtime/turn_count"
echo "session-5" > "$SANDBOX/.purlin/runtime/session_id"

OUTPUT=$(run_guard "session-5" 2>&1)
if echo "$OUTPUT" | grep -q "\[CONTEXT GUARD\] Turn 4/2"; then
    log_pass "Warning repeats: Turn 4/2"
else
    log_fail "Expected warning 'Turn 4/2', got: '$OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 6: Parallel invocations count correctly (race condition)
###############################################################################
echo ""
echo "[Scenario] Parallel invocations count correctly"
setup_sandbox

# Run 10 instances in parallel with the same session
for i in $(seq 1 10); do
    run_guard "session-6" >/dev/null 2>&1 &
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
