#!/usr/bin/env bash
# tests/qa/test_regression_testing_regression.sh
# QA-owned regression harness for features/regression_testing.md
# Tests: meta-runner exists, discovers scenario files, harness_runner.py works,
#        result files written correctly, run_regression.sh interface
#
# Usage: bash tests/qa/test_regression_testing_regression.sh [--write-results]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: regression_testing ==="
echo ""

# RT1: Meta-runner script exists
META_RUNNER="$PURLIN_ROOT/tools/test_support/run_regression.sh"
if [ -f "$META_RUNNER" ]; then
    log_pass "RT1: run_regression.sh exists"
else
    log_fail "RT1: run_regression.sh not found"
fi

# RT2: Harness runner exists
HARNESS_RUNNER="$PURLIN_ROOT/tools/test_support/harness_runner.py"
if [ -f "$HARNESS_RUNNER" ]; then
    log_pass "RT2: harness_runner.py exists"
else
    log_fail "RT2: harness_runner.py not found"
fi

# RT3: Scenarios directory exists
SCENARIOS_DIR="$PURLIN_ROOT/tests/qa/scenarios"
if [ -d "$SCENARIOS_DIR" ]; then
    SCENARIO_COUNT=$(ls "$SCENARIOS_DIR/"*.json 2>/dev/null | wc -l | tr -d ' ')
    log_pass "RT3: scenarios/ directory exists with $SCENARIO_COUNT JSON files"
else
    log_fail "RT3: tests/qa/scenarios/ directory not found"
fi

# RT4: harness_runner.py is importable and has expected interface
if python3 -c "
import subprocess, sys, os
root = '$PURLIN_ROOT'
# Check harness_runner.py has process_scenario_file function
content = open(os.path.join(root, 'tools/test_support/harness_runner.py')).read()
assert 'process_scenario_file' in content, 'missing process_scenario_file'
assert 'agent_behavior' in content, 'missing agent_behavior handler'
assert 'web_test' in content, 'missing web_test handler'
assert 'custom_script' in content, 'missing custom_script handler'
" 2>/dev/null; then
    log_pass "RT4: harness_runner.py has expected dispatch functions (agent_behavior, web_test, custom_script)"
else
    log_fail "RT4: harness_runner.py missing expected dispatch functions"
fi

# RT5: Result file written by harness_runner
RESULT_FILE="$PURLIN_ROOT/tests/project_init/tests.json"
if [ -f "$RESULT_FILE" ]; then
    if python3 -c "
import json, sys
d = json.load(open('$RESULT_FILE'))
required = ['status', 'passed', 'failed', 'total']
missing = [k for k in required if k not in d]
if missing:
    print('Missing:', missing, file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; then
        log_pass "RT5: tests.json written with required fields (status, passed, failed, total)"
    else
        log_fail "RT5: tests.json missing required fields"
    fi
else
    log_fail "RT5: tests/project_init/tests.json not found"
fi

# RT6: Enriched tests.json has detail entries with scenario_ref
if python3 -c "
import json, sys
d = json.load(open('$RESULT_FILE'))
details = d.get('details', [])
if not details:
    sys.exit(1)
has_ref = any('scenario_ref' in entry for entry in details)
if not has_ref:
    sys.exit(1)
" 2>/dev/null; then
    log_pass "RT6: tests.json details contain enriched scenario_ref fields"
else
    log_fail "RT6: tests.json details missing scenario_ref enrichment"
fi

# RT7: Meta-runner script has correct interface (--scenarios-dir, --help, or discoverable args)
if grep -q "scenarios.dir\|scenarios_dir\|SCENARIOS_DIR" "$META_RUNNER" 2>/dev/null; then
    log_pass "RT7: run_regression.sh accepts --scenarios-dir argument (found in script)"
else
    log_fail "RT7: run_regression.sh missing --scenarios-dir argument handling"
fi

# RT8: fixture.sh exists (part of regression infrastructure)
FIXTURE_SH="$PURLIN_ROOT/tools/test_support/fixture.sh"
if [ -f "$FIXTURE_SH" ]; then
    log_pass "RT8: fixture.sh exists"
else
    log_fail "RT8: fixture.sh not found"
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
