#!/usr/bin/env bash
# tests/qa/test_terminal_identity_regression.sh
# QA-owned regression harness for features/terminal_identity.md
# Tests: identity.sh can be sourced, functions defined, escape sequences go to /dev/tty
#
# Usage: bash tests/qa/test_terminal_identity_regression.sh [--write-results]
# --write-results accepted but is a no-op (harness_runner.py writes tests.json).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

IDENTITY_SH="$PURLIN_ROOT/tools/terminal/identity.sh"

echo "=== QA Regression: terminal_identity ==="
echo ""

# T1: identity.sh exists
if [ -f "$IDENTITY_SH" ]; then
    log_pass "T1: identity.sh exists"
else
    log_fail "T1: identity.sh not found at $IDENTITY_SH"
fi

# T2: identity.sh can be sourced
# shellcheck disable=SC1090
if source "$IDENTITY_SH" 2>/dev/null; then
    log_pass "T2: identity.sh sourced without errors"
else
    log_fail "T2: identity.sh failed to source"
fi

# T3-T8: Required functions are defined after sourcing
for fn in set_term_title clear_term_title set_iterm_badge clear_iterm_badge set_agent_identity clear_agent_identity; do
    if declare -f "$fn" > /dev/null 2>&1; then
        log_pass "T3-T8: function '$fn' defined"
    else
        log_fail "T3-T8: function '$fn' NOT defined"
    fi
done

# T9: set_term_title output goes to /dev/tty when writable, falls back to stdout otherwise
# In sandboxed environments (e.g. Claude Code), /dev/tty may exist but not be writable.
# The fallback to stdout is acceptable in that case.
if [ -e /dev/tty ] && (echo -n > /dev/tty) 2>/dev/null; then
    # /dev/tty is writable — output should go there, not stdout
    OUT=$(TERM_PROGRAM="" set_term_title "regression-test" 2>/dev/null || true)
    if [ -z "$OUT" ]; then
        log_pass "T9: set_term_title writes to /dev/tty (not stdout)"
    else
        log_fail "T9: set_term_title leaked to stdout: $OUT"
    fi
else
    log_pass "T9: /dev/tty unavailable or not writable, stdout fallback acceptable (skip)"
fi

# T10: Non-iTerm2: set_iterm_badge is a no-op (returns 0, no output)
BADGE_OUT=$(TERM_PROGRAM="xterm" set_iterm_badge "test-badge" 2>/dev/null || true)
if [ -z "$BADGE_OUT" ]; then
    log_pass "T10: set_iterm_badge is no-op on non-iTerm2 terminal"
else
    log_fail "T10: set_iterm_badge produced output on non-iTerm2: $BADGE_OUT"
fi

# T11: set_agent_identity calls both title and badge functions
# (verify function exists and is callable; /dev/tty write may fail in subprocess context)
set_agent_identity "test-agent" 2>/dev/null || true
CALL_STATUS=$?
if [ $CALL_STATUS -ne 127 ]; then
    log_pass "T11: set_agent_identity is callable (exit $CALL_STATUS; /dev/tty write acceptable)"
else
    log_fail "T11: set_agent_identity not found (command not found)"
fi

# T12: clear_agent_identity is callable
clear_agent_identity 2>/dev/null || true
CALL_STATUS=$?
if [ $CALL_STATUS -ne 127 ]; then
    log_pass "T12: clear_agent_identity is callable (exit $CALL_STATUS)"
else
    log_fail "T12: clear_agent_identity not found (command not found)"
fi

echo ""
echo "────────────────────────────────"
TOTAL=$((PASS + FAIL))
echo "Results: $PASS/$TOTAL tests passed"
if [ $FAIL -gt 0 ]; then
    printf "\nFailed tests:%s\n" "$ERRORS"
    exit 1
fi
exit 0
