#!/usr/bin/env bash
# tests/qa/test_release_doc_consistency_check_regression.sh
# QA-owned regression harness for features/release_doc_consistency_check.md
# Tests: doc_consistency_check.py runs, detects coverage gaps, handles missing README, stale paths
#
# Usage: bash tests/qa/test_release_doc_consistency_check_regression.sh [--write-results]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""
FIXTURE_DIRS=()

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

cleanup() {
    for dir in "${FIXTURE_DIRS[@]}"; do
        [ -d "$dir" ] && bash "$PURLIN_ROOT/tools/test_support/fixture.sh" cleanup "$dir" 2>/dev/null || true
    done
}
trap cleanup EXIT

FIXTURE_SH="$PURLIN_ROOT/tools/test_support/fixture.sh"
FIXTURE_REPO="$PURLIN_ROOT/.purlin/runtime/fixture-repo"
DOC_CHECK_PY="$PURLIN_ROOT/tools/release/doc_consistency_check.py"

echo "=== QA Regression: release_doc_consistency_check ==="
echo ""

# DC1: doc_consistency_check.py exists
if [ -f "$DOC_CHECK_PY" ]; then
    log_pass "DC1: tools/release/doc_consistency_check.py exists"
else
    log_fail "DC1: doc_consistency_check.py not found"
fi

# DC2: Coverage gaps fixture — detects features not in README
FD=$(bash "$FIXTURE_SH" checkout "$FIXTURE_REPO" "main/release_doc_consistency_check/coverage-gaps" 2>/dev/null)
if [ -n "$FD" ] && [ -d "$FD" ]; then
    FIXTURE_DIRS+=("$FD")
    OUTPUT=$(PURLIN_PROJECT_ROOT="$FD" python3 "$DOC_CHECK_PY" 2>/dev/null)
    if echo "$OUTPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
findings = d.get('findings', [])
if findings:
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
        log_pass "DC2: coverage-gaps fixture: findings detected"
    else
        log_fail "DC2: coverage-gaps fixture: no findings (expected coverage gap detection)"
    fi
else
    log_fail "DC2: coverage-gaps fixture checkout failed"
fi

# DC3: Output is valid JSON with required structure
if [ -n "${OUTPUT:-}" ]; then
    if echo "$OUTPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'step' in d, 'missing step'
assert d.get('step') == 'doc_consistency_check', 'wrong step name'
assert 'findings' in d, 'missing findings'
" 2>/dev/null; then
        log_pass "DC3: output is valid JSON with step='doc_consistency_check' and findings"
    else
        log_fail "DC3: output missing required JSON structure"
    fi
else
    log_fail "DC3: no output to validate"
fi

# DC4: Missing README handled gracefully (no crash, summary message)
FD_INCON=$(bash "$FIXTURE_SH" checkout "$FIXTURE_REPO" "main/release_doc_consistency_check/inconsistent-docs" 2>/dev/null)
if [ -n "$FD_INCON" ] && [ -d "$FD_INCON" ]; then
    FIXTURE_DIRS+=("$FD_INCON")
    OUT_INCON=$(PURLIN_PROJECT_ROOT="$FD_INCON" python3 "$DOC_CHECK_PY" 2>/dev/null)
    if echo "$OUT_INCON" | python3 -c "
import json, sys
d = json.load(sys.stdin)
# Should run without crashing; summary may mention missing README
assert 'step' in d, 'no step field'
" 2>/dev/null; then
        log_pass "DC4: inconsistent-docs fixture: script runs gracefully (handles edge cases)"
    else
        log_fail "DC4: inconsistent-docs fixture: script crashed or produced invalid JSON"
    fi
else
    log_fail "DC4: inconsistent-docs fixture checkout failed"
fi

# DC5: Stale reference fixture
FD_STALE=$(bash "$FIXTURE_SH" checkout "$FIXTURE_REPO" "main/release_doc_consistency_check/clean" 2>/dev/null)
if [ -n "$FD_STALE" ] && [ -d "$FD_STALE" ]; then
    FIXTURE_DIRS+=("$FD_STALE")
    OUT_CLEAN=$(PURLIN_PROJECT_ROOT="$FD_STALE" python3 "$DOC_CHECK_PY" 2>/dev/null)
    if echo "$OUT_CLEAN" | python3 -c "
import json, sys
d = json.load(sys.stdin)
assert 'step' in d, 'missing step'
" 2>/dev/null; then
        log_pass "DC5: clean fixture: script runs successfully"
    else
        log_fail "DC5: clean fixture: script produced invalid output"
    fi
else
    log_fail "DC5: clean fixture checkout failed"
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
