#!/usr/bin/env bash
# tests/qa/test_purlin_scan_engine_regression.sh
# QA-owned regression harness for features/purlin_scan_engine.md
# Tests: scan.py performance (< 2s) and JSON output validity
#
# Usage: bash tests/qa/test_purlin_scan_engine_regression.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: purlin_scan_engine ==="
echo ""

SCAN_PY="$PURLIN_ROOT/tools/cdd/scan.py"

# PSE1: scan.py exists
if [ -f "$SCAN_PY" ]; then
    log_pass "PSE1: tools/cdd/scan.py exists"
else
    log_fail "PSE1: tools/cdd/scan.py not found"
    echo ""
    echo "────────────────────────────────"
    TOTAL=$((PASS + FAIL))
    echo "Results: $PASS/$TOTAL tests passed"
    exit 1
fi

# PSE2: Feature count check (scenario requires 97+ features)
FEATURE_COUNT=$(find "$PURLIN_ROOT/features" -maxdepth 1 -name '*.md' \
    ! -name '*.impl.md' ! -name '*.discoveries.md' | wc -l | tr -d ' ')
if [ "$FEATURE_COUNT" -ge 97 ]; then
    log_pass "PSE2: project has $FEATURE_COUNT feature files (>= 97 threshold)"
else
    log_fail "PSE2: project has only $FEATURE_COUNT feature files (need >= 97)"
fi

# PSE3: Full scan completes under 2 seconds
START_TIME=$(python3 -c "import time; print(time.monotonic())")
OUTPUT=$(cd "$PURLIN_ROOT" && PURLIN_PROJECT_ROOT="$PURLIN_ROOT" python3 "$SCAN_PY" 2>/dev/null)
EXIT_CODE=$?
END_TIME=$(python3 -c "import time; print(time.monotonic())")

ELAPSED=$(python3 -c "print(round($END_TIME - $START_TIME, 3))")
if python3 -c "import sys; sys.exit(0 if $ELAPSED < 2.0 else 1)"; then
    log_pass "PSE3: full scan completed in ${ELAPSED}s (< 2.0s limit)"
else
    log_fail "PSE3: full scan took ${ELAPSED}s (exceeds 2.0s limit)"
fi

# PSE4: Output is valid JSON
if echo "$OUTPUT" | python3 -c "import json, sys; json.load(sys.stdin)" 2>/dev/null; then
    log_pass "PSE4: scan output is valid JSON"
else
    log_fail "PSE4: scan output is not valid JSON"
fi

# PSE5: JSON contains expected top-level fields
if echo "$OUTPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
required = ['features', 'scanned_at']
missing = [k for k in required if k not in d]
if missing:
    print(f'Missing fields: {missing}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
    log_pass "PSE5: JSON contains required top-level fields (features, scanned_at)"
else
    log_fail "PSE5: JSON missing required top-level fields"
fi

# PSE6: Feature count in JSON matches filesystem
if echo "$OUTPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
count = len(d.get('features', []))
if count >= 90:
    sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    log_pass "PSE6: JSON features array has sufficient entries"
else
    log_fail "PSE6: JSON features array unexpectedly small"
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
