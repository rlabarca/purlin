#!/bin/bash
# test_context_guard.sh — Automated tests for context_guard.sh (PreCompact hook)
# Covers all 6 automated scenarios from features/context_guard.md.
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

# Run context_guard.sh with given type and optional role.
# Returns: sets EXIT_CODE, STDERR_OUTPUT, STDOUT_OUTPUT
run_guard() {
    local compact_type="${1:-auto}"
    local agent_role="${2:-}"
    local stderr_file="$SANDBOX/stderr_output"

    local env_args=(PURLIN_PROJECT_ROOT="$SANDBOX")
    if [[ -n "$agent_role" ]]; then
        env_args+=(AGENT_ROLE="$agent_role")
    fi

    STDOUT_OUTPUT=$(echo "{\"type\":\"$compact_type\"}" | \
        env "${env_args[@]}" \
        bash "$SANDBOX/tools/hooks/context_guard.sh" 2>"$stderr_file") || true
    EXIT_CODE=${PIPESTATUS[1]:-$?}

    # Capture exit code properly
    STDOUT_OUTPUT=""
    STDERR_OUTPUT=""
    echo "{\"type\":\"$compact_type\"}" | \
        env "${env_args[@]}" \
        bash "$SANDBOX/tools/hooks/context_guard.sh" >"$SANDBOX/stdout_output" 2>"$stderr_file"
    EXIT_CODE=$?
    STDOUT_OUTPUT=$(cat "$SANDBOX/stdout_output" 2>/dev/null || echo "")
    STDERR_OUTPUT=$(cat "$stderr_file" 2>/dev/null || echo "")
}

echo "==============================="
echo "Context Guard Tests (PreCompact)"
echo "==============================="

###############################################################################
# Scenario 1: Auto-compaction blocked when guard enabled
###############################################################################
echo ""
echo "[Scenario] Auto-compaction blocked when guard enabled"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"
run_guard "auto" "builder"

if [[ "$EXIT_CODE" -eq 2 ]]; then
    log_pass "Exit code is 2 (blocks auto-compaction)"
else
    log_fail "Expected exit code 2, got $EXIT_CODE"
fi

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD: Auto-compaction blocked"; then
    log_pass "stderr contains evacuation message"
else
    log_fail "Expected 'CONTEXT GUARD: Auto-compaction blocked' in stderr, got: '$STDERR_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 2: Manual compaction allowed regardless of guard state
###############################################################################
echo ""
echo "[Scenario] Manual compaction allowed regardless of guard state"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"
run_guard "manual" "builder"

if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Exit code is 0 (allows manual compaction)"
else
    log_fail "Expected exit code 0, got $EXIT_CODE"
fi

if [[ -z "$STDERR_OUTPUT" ]]; then
    log_pass "No output on stderr"
else
    log_fail "Expected no stderr output, got: '$STDERR_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 3: Auto-compaction allowed when guard disabled
###############################################################################
echo ""
echo "[Scenario] Auto-compaction allowed when guard disabled"
setup_sandbox

echo '{"agents": {"architect": {"context_guard": false}}}' > "$SANDBOX/.purlin/config.json"
run_guard "auto" "architect"

if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Exit code is 0 (guard disabled, allows auto-compaction)"
else
    log_fail "Expected exit code 0, got $EXIT_CODE"
fi

if [[ -z "$STDERR_OUTPUT" ]]; then
    log_pass "No output on stderr when guard disabled"
else
    log_fail "Expected no stderr output, got: '$STDERR_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 4: Guard enabled by default when no config exists
###############################################################################
echo ""
echo "[Scenario] Guard enabled by default when no config exists"
setup_sandbox

# No config file — guard should default to enabled
run_guard "auto" "builder"

if [[ "$EXIT_CODE" -eq 2 ]]; then
    log_pass "Exit code is 2 (default enabled, blocks auto-compaction)"
else
    log_fail "Expected exit code 2, got $EXIT_CODE"
fi

if echo "$STDERR_OUTPUT" | grep -q "CONTEXT GUARD"; then
    log_pass "stderr contains evacuation message with default config"
else
    log_fail "Expected evacuation message in stderr, got: '$STDERR_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 5: Per-agent guard disabled while others remain enabled
###############################################################################
echo ""
echo "[Scenario] Per-agent guard disabled while others remain enabled"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": false}, "architect": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"

# Builder should be allowed (guard disabled)
run_guard "auto" "builder"
if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Builder (guard disabled): exit code 0"
else
    log_fail "Expected exit code 0 for builder, got $EXIT_CODE"
fi

# Architect should be blocked (guard enabled)
run_guard "auto" "architect"
if [[ "$EXIT_CODE" -eq 2 ]]; then
    log_pass "Architect (guard enabled): exit code 2"
else
    log_fail "Expected exit code 2 for architect, got $EXIT_CODE"
fi
cleanup_sandbox

###############################################################################
# Scenario 6: Evacuation message content is correct
###############################################################################
echo ""
echo "[Scenario] Evacuation message content is correct"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"
run_guard "auto" "builder"

EXPECTED_MSG="CONTEXT GUARD: Auto-compaction blocked. Run /pl-resume save, then /clear, then /pl-resume to continue."
if echo "$STDERR_OUTPUT" | grep -qF "$EXPECTED_MSG"; then
    log_pass "Evacuation message matches exactly"
else
    log_fail "Expected exact message '$EXPECTED_MSG', got: '$STDERR_OUTPUT'"
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
echo "{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/hooks/test_context_guard.sh\"}" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
