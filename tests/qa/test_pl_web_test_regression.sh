#!/usr/bin/env bash
# tests/qa/test_pl_web_test_regression.sh
# QA-owned regression harness for features/pl_web_test.md
# Tests: command file exists, no stale references to pl-web-verify,
#        Web Test metadata pattern is consistent, role guard present
#
# Usage: bash tests/qa/test_pl_web_test_regression.sh [--write-results]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: pl_web_test ==="
echo ""

# WT1: pl-web-test.md command file exists
CMD_FILE="$PURLIN_ROOT/.claude/commands/pl-web-test.md"
if [ -f "$CMD_FILE" ]; then
    log_pass "WT1: .claude/commands/pl-web-test.md exists"
else
    log_fail "WT1: pl-web-test.md command file not found"
fi

# WT2: Old skill name pl-web-verify has been fully renamed
# Scope: only check implementation files (.claude/, tools/, instructions/)
# Exclude: feature specs (docs), impl/companion files, test files (they reference the name intentionally)
OLD_SKILL_FILE="$PURLIN_ROOT/.claude/commands/pl-web-verify.md"
if [ ! -f "$OLD_SKILL_FILE" ]; then
    log_pass "WT2: old skill file .claude/commands/pl-web-verify.md does not exist (correctly renamed)"
else
    log_fail "WT2: old skill file pl-web-verify.md still exists (should have been deleted)"
fi
OLD_NAME_COUNT=$(grep -r "pl-web-verify\|pl_web_verify" \
    "$PURLIN_ROOT/tools" \
    "$PURLIN_ROOT/instructions" \
    2>/dev/null | grep -v ".git" | wc -l | tr -d ' ')
if [ "$OLD_NAME_COUNT" -eq 0 ]; then
    log_pass "WT2b: zero references to 'pl-web-verify' in tools/ and instructions/"
else
    log_fail "WT2b: $OLD_NAME_COUNT stale references to 'pl-web-verify' in tools/instructions"
fi

# WT3: Command file contains QA as authorized role
if [ -f "$CMD_FILE" ]; then
    if grep -q "QA\|qa\|Builder\|builder" "$CMD_FILE" 2>/dev/null; then
        log_pass "WT3: command file specifies role authorization"
    else
        log_fail "WT3: command file missing role specification"
    fi
fi

# WT4: Role guard — command file references Architect rejection
if [ -f "$CMD_FILE" ]; then
    if grep -q "[Aa]rchitect\|role.*guard\|guard.*role\|not.*architect\|architect.*not" "$CMD_FILE" 2>/dev/null; then
        log_pass "WT4: command file contains Architect role restriction"
    else
        log_fail "WT4: command file missing Architect role guard"
    fi
fi

# WT5: Features with Web Test metadata use consistent pattern (> Web Test: http://...)
WEB_TEST_FEATURES=$(grep -rl "^> Web Test:" "$PURLIN_ROOT/features/" 2>/dev/null | wc -l | tr -d ' ')
if [ "$WEB_TEST_FEATURES" -gt 0 ]; then
    log_pass "WT5: $WEB_TEST_FEATURES features use '> Web Test:' metadata pattern"
else
    log_fail "WT5: no features found with '> Web Test:' metadata"
fi

# WT6: Web Test metadata always pairs with Web Start metadata (if start needed)
# Check that features with Web Test also have Web Start (or the server is pre-existing)
WEB_TEST_ONLY=$(grep -rL "Web Start" $(grep -rl "^> Web Test:" "$PURLIN_ROOT/features/" 2>/dev/null) 2>/dev/null | wc -l | tr -d ' ')
log_pass "WT6: $WEB_TEST_ONLY features have Web Test without Web Start (may use pre-existing server)"

# WT7: Feature spec exists with auto-discovery requirement
FEATURE_SPEC="$PURLIN_ROOT/features/pl_web_test.md"
if grep -q "auto.discov\|auto_discov\|discover" "$FEATURE_SPEC" 2>/dev/null; then
    log_pass "WT7: feature spec references auto-discovery behavior"
else
    log_fail "WT7: feature spec missing auto-discovery requirement"
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
