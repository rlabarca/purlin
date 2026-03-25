#!/usr/bin/env bash
# tests/qa/test_purlin_instruction_architecture_regression.sh
# QA-owned regression harness for features/purlin_instruction_architecture.md
# Tests: PURLIN_BASE.md line count is within target range (200-700)
#
# Usage: bash tests/qa/test_purlin_instruction_architecture_regression.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: purlin_instruction_architecture ==="
echo ""

TARGET_FILE="$PURLIN_ROOT/instructions/PURLIN_BASE.md"

# PIA1: PURLIN_BASE.md exists
if [ -f "$TARGET_FILE" ]; then
    log_pass "PIA1: instructions/PURLIN_BASE.md exists"
else
    log_fail "PIA1: instructions/PURLIN_BASE.md not found"
    echo ""
    echo "────────────────────────────────"
    TOTAL=$((PASS + FAIL))
    echo "Results: $PASS/$TOTAL tests passed"
    exit 1
fi

# PIA2: Line count is between 200 and 700
LINE_COUNT=$(wc -l < "$TARGET_FILE")
if [ "$LINE_COUNT" -ge 200 ] && [ "$LINE_COUNT" -le 700 ]; then
    log_pass "PIA2: line count ($LINE_COUNT) is within target range [200, 700]"
else
    log_fail "PIA2: line count ($LINE_COUNT) is outside target range [200, 700]"
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
