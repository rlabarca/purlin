#!/bin/bash
# test_purlin_scan.sh -- Unit tests for tools/cdd/scan.py (Purlin Scan Engine)
# Covers the 10 unit test scenarios from features/purlin_scan_engine.md Section 3.
#
# Produces tests/purlin_scan_engine/tests.json
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
ERRORS=""

###############################################################################
# Helpers
###############################################################################
log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

cleanup_fixture() {
    if [ -n "${FIXTURE_DIR:-}" ] && [ -d "$FIXTURE_DIR" ]; then
        rm -rf "$FIXTURE_DIR"
    fi
}

# Run scan.py against a given project root and capture stdout JSON.
# Usage: run_scan [extra_args...]
# Sets SCAN_OUTPUT to the JSON string.
run_scan() {
    SCAN_OUTPUT=""
    local scan_py="$PROJECT_ROOT/tools/cdd/scan.py"
    SCAN_OUTPUT=$(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 "$scan_py" "$@" 2>/dev/null) || true
}

# Run scan.py against a fixture project root.
# Usage: run_scan_fixture <fixture_root> [extra_args...]
run_scan_fixture() {
    local fixture_root="$1"
    shift
    SCAN_OUTPUT=""
    local scan_py="$PROJECT_ROOT/tools/cdd/scan.py"
    SCAN_OUTPUT=$(PURLIN_PROJECT_ROOT="$fixture_root" python3 "$scan_py" "$@" 2>/dev/null) || true
}

# Extract a JSON value using python3. Args: <json_path_expression>
# Uses $SCAN_OUTPUT. Prints the result.
json_get() {
    echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except:
    print('JSON_PARSE_ERROR')
    sys.exit(0)
path = '''$1'''
try:
    val = eval('d' + path)
    if val is None:
        print('null')
    elif isinstance(val, bool):
        print('true' if val else 'false')
    elif isinstance(val, (list, dict)):
        print(json.dumps(val))
    else:
        print(val)
except Exception as e:
    print('EVAL_ERROR: ' + str(e))
" 2>/dev/null
}

###############################################################################
# Build a minimal fixture project for isolated tests
###############################################################################
setup_fixture() {
    FIXTURE_DIR="$(mktemp -d)"
    trap cleanup_fixture EXIT

    # Create .purlin directory (so detect_project_root finds it)
    mkdir -p "$FIXTURE_DIR/.purlin/cache"
    echo '{}' > "$FIXTURE_DIR/.purlin/config.json"

    # Initialize git repo
    git -C "$FIXTURE_DIR" init -q
    git -C "$FIXTURE_DIR" commit --allow-empty -q -m "initial commit"

    # Create features directory
    mkdir -p "$FIXTURE_DIR/features"
    mkdir -p "$FIXTURE_DIR/tests"
}

echo "================================================================"
echo "Test Suite: Purlin Scan Engine (tools/cdd/scan.py)"
echo "================================================================"
echo ""

###############################################################################
# Scenario 1: Scan detects feature lifecycle from git log
###############################################################################
echo "--- Scenario 1: Scan detects feature lifecycle from git log ---"

# Use the real project: features with status commits should have a lifecycle.
# agent_behavior_tests has a [Complete] status commit in the real repo.
run_scan
LIFECYCLE=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'agent_behavior_tests':
        print(f['lifecycle'])
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$LIFECYCLE" = "COMPLETE" ]; then
    log_pass "Scan detects feature lifecycle from git log"
else
    log_fail "Scan detects feature lifecycle from git log (got: $LIFECYCLE, expected: COMPLETE)"
fi

###############################################################################
# Scenario 2: Scan detects missing spec sections
###############################################################################
echo "--- Scenario 2: Scan detects missing spec sections ---"

# Create a fixture feature with only an Overview section (no Requirements/Unit Tests).
setup_fixture

cat > "$FIXTURE_DIR/features/incomplete_feature.md" << 'FEATEOF'
# Feature: Incomplete Feature

> Label: "Test: Incomplete"

## 1. Overview

This feature has only an overview.
FEATEOF

run_scan_fixture "$FIXTURE_DIR"

SECT_REQ=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'incomplete_feature':
        print('true' if f['sections']['requirements'] else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

SECT_UT=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'incomplete_feature':
        print('true' if f['sections']['unit_tests'] else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$SECT_REQ" = "false" ] && [ "$SECT_UT" = "false" ]; then
    log_pass "Scan detects missing spec sections"
else
    log_fail "Scan detects missing spec sections (requirements=$SECT_REQ, unit_tests=$SECT_UT)"
fi

# Also verify that numbered headings ARE detected
cat > "$FIXTURE_DIR/features/complete_feature.md" << 'FEATEOF'
# Feature: Complete Feature

> Label: "Test: Complete"

## 1. Overview

Some overview text.

## 2. Requirements

Some requirements.

## 3. Scenarios

### Unit Tests

#### Scenario: Something
    Given something

### QA Scenarios

#### Scenario: QA check
    Given a QA check
FEATEOF

run_scan_fixture "$FIXTURE_DIR"

SECT_REQ2=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'complete_feature':
        print('true' if f['sections']['requirements'] else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

SECT_UT2=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'complete_feature':
        print('true' if f['sections']['unit_tests'] else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

SECT_QA2=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'complete_feature':
        print('true' if f['sections']['qa_scenarios'] else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$SECT_REQ2" = "true" ] && [ "$SECT_UT2" = "true" ] && [ "$SECT_QA2" = "true" ]; then
    log_pass "Scan detects numbered section headings (bug fix)"
else
    log_fail "Scan detects numbered section headings (requirements=$SECT_REQ2, unit_tests=$SECT_UT2, qa_scenarios=$SECT_QA2)"
fi

cleanup_fixture

###############################################################################
# Scenario 3: Scan reads test status from tests.json
###############################################################################
echo "--- Scenario 3: Scan reads test status from tests.json ---"

setup_fixture

cat > "$FIXTURE_DIR/features/notifications.md" << 'FEATEOF'
# Feature: Notifications

## 1. Overview
Notifications feature.

## 2. Requirements
Some requirements.
FEATEOF

mkdir -p "$FIXTURE_DIR/tests/notifications"
cat > "$FIXTURE_DIR/tests/notifications/tests.json" << 'TESTEOF'
{
  "status": "PASS",
  "passed": 5,
  "failed": 0,
  "total": 5
}
TESTEOF

run_scan_fixture "$FIXTURE_DIR"

TEST_STATUS=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'notifications':
        ts = f['test_status']
        print(ts if ts is not None else 'null')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$TEST_STATUS" = "PASS" ]; then
    log_pass "Scan reads test status from tests.json"
else
    log_fail "Scan reads test status from tests.json (got: $TEST_STATUS, expected: PASS)"
fi

cleanup_fixture

###############################################################################
# Scenario 4: Scan reports null test status when no tests.json
###############################################################################
echo "--- Scenario 4: Scan reports null test status when no tests.json ---"

setup_fixture

cat > "$FIXTURE_DIR/features/new_feature.md" << 'FEATEOF'
# Feature: New Feature

## 1. Overview
A brand new feature with no tests yet.
FEATEOF

# Deliberately do NOT create tests/new_feature/tests.json

run_scan_fixture "$FIXTURE_DIR"

TEST_STATUS_NULL=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'new_feature':
        ts = f['test_status']
        print('null' if ts is None else ts)
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$TEST_STATUS_NULL" = "null" ]; then
    log_pass "Scan reports null test status when no tests.json"
else
    log_fail "Scan reports null test status when no tests.json (got: $TEST_STATUS_NULL, expected: null)"
fi

cleanup_fixture

###############################################################################
# Scenario 5: Scan detects open BUG discovery
###############################################################################
echo "--- Scenario 5: Scan detects open BUG discovery ---"

setup_fixture

cat > "$FIXTURE_DIR/features/auth.md" << 'FEATEOF'
# Feature: Auth

## 1. Overview
Auth feature.
FEATEOF

cat > "$FIXTURE_DIR/features/auth.discoveries.md" << 'DISCEOF'
# Discoveries: Auth

### [BUG] Login fails on empty password (Discovered: 2026-03-24)
- **Observed Behavior:** Login crashes with empty password.
- **Expected Behavior:** Should show validation error.
- **Action Required:** Builder
- **Status:** OPEN
DISCEOF

run_scan_fixture "$FIXTURE_DIR"

BUG_FOUND=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
found = False
for disc in d['open_discoveries']:
    if disc['type'] == 'BUG' and disc['status'] == 'OPEN' and disc['feature'] == 'auth':
        found = True
        break
print('true' if found else 'false')
" 2>/dev/null)

if [ "$BUG_FOUND" = "true" ]; then
    log_pass "Scan detects open BUG discovery"
else
    log_fail "Scan detects open BUG discovery (found=$BUG_FOUND)"
fi

cleanup_fixture

###############################################################################
# Scenario 6: Scan detects unacknowledged deviation
###############################################################################
echo "--- Scenario 6: Scan detects unacknowledged deviation ---"

setup_fixture

cat > "$FIXTURE_DIR/features/auth.md" << 'FEATEOF'
# Feature: Auth

## 1. Overview
Auth feature.
FEATEOF

cat > "$FIXTURE_DIR/features/auth.impl.md" << 'IMPLEOF'
# Implementation Notes: Auth

**[DEVIATION]** Used JWT instead of session tokens for auth persistence. (Severity: HIGH)
IMPLEOF

run_scan_fixture "$FIXTURE_DIR"

DEV_FOUND=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
found = False
for dev in d['unacknowledged_deviations']:
    if dev['feature'] == 'auth' and dev['tag'] == 'DEVIATION':
        found = True
        break
print('true' if found else 'false')
" 2>/dev/null)

if [ "$DEV_FOUND" = "true" ]; then
    log_pass "Scan detects unacknowledged deviation"
else
    log_fail "Scan detects unacknowledged deviation (found=$DEV_FOUND)"
fi

cleanup_fixture

###############################################################################
# Scenario 7: Scan parses delivery plan phases
###############################################################################
echo "--- Scenario 7: Scan parses delivery plan phases ---"

setup_fixture

cat > "$FIXTURE_DIR/.purlin/delivery_plan.md" << 'PLANEOF'
# Delivery Plan

## Phase 1 -- Core (COMPLETE)

- `features/core_init.md`
- `features/core_config.md`

## Phase 2 -- Extensions (IN_PROGRESS)

- `features/ext_auth.md`
- `features/ext_notifications.md`

## Phase 3 -- Polish (PENDING)

- `features/polish_ui.md`
PLANEOF

run_scan_fixture "$FIXTURE_DIR"

PLAN_RESULT=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
dp = d.get('delivery_plan')
if dp is None:
    print('null')
    sys.exit(0)
phases = dp.get('phases', [])
total = len(phases)
# Find the current phase (first non-COMPLETE phase)
current = None
for p in phases:
    if p['status'] != 'COMPLETE':
        current = p['number']
        break
print(f'{current},{total}')
" 2>/dev/null)

if [ "$PLAN_RESULT" = "2,3" ]; then
    log_pass "Scan parses delivery plan phases"
else
    log_fail "Scan parses delivery plan phases (got: $PLAN_RESULT, expected: 2,3)"
fi

cleanup_fixture

###############################################################################
# Scenario 8: Cached scan returns quickly
###############################################################################
echo "--- Scenario 8: Cached scan returns quickly ---"

# Run a fresh scan to populate the cache, then immediately run --cached
# and verify it returns quickly and matches.

# Use real project for this test.
run_scan
FRESH_SCANNED_AT=$(json_get "['scanned_at']")

# Now run with --cached -- should return the same cached data quickly.
START_TIME=$(python3 -c "import time; print(time.time())")
run_scan --cached
END_TIME=$(python3 -c "import time; print(time.time())")
CACHED_SCANNED_AT=$(json_get "['scanned_at']")

ELAPSED=$(python3 -c "print(float($END_TIME) - float($START_TIME))")
FAST_ENOUGH=$(python3 -c "print('true' if float('$ELAPSED') < 0.5 else 'false')")
MATCHES=$(python3 -c "print('true' if '$FRESH_SCANNED_AT' == '$CACHED_SCANNED_AT' else 'false')")

if [ "$FAST_ENOUGH" = "true" ] && [ "$MATCHES" = "true" ]; then
    log_pass "Cached scan returns quickly"
else
    log_fail "Cached scan returns quickly (elapsed=${ELAPSED}s, fast_enough=$FAST_ENOUGH, timestamps_match=$MATCHES)"
fi

###############################################################################
# Scenario 9: Scan handles missing dependency graph gracefully
###############################################################################
echo "--- Scenario 9: Scan handles missing dependency graph gracefully ---"

setup_fixture

# Ensure NO dependency_graph.json exists
rm -f "$FIXTURE_DIR/.purlin/cache/dependency_graph.json"

cat > "$FIXTURE_DIR/features/simple.md" << 'FEATEOF'
# Feature: Simple

## 1. Overview
A simple feature.
FEATEOF

run_scan_fixture "$FIXTURE_DIR"

DEP_TOTAL=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
dg = d.get('dependency_graph', {})
print(dg.get('total', -1))
" 2>/dev/null)

DEP_CYCLES=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
dg = d.get('dependency_graph', {})
print(json.dumps(dg.get('cycles', 'MISSING')))
" 2>/dev/null)

if [ "$DEP_TOTAL" = "0" ] && [ "$DEP_CYCLES" = "[]" ]; then
    log_pass "Scan handles missing dependency graph gracefully"
else
    log_fail "Scan handles missing dependency graph gracefully (total=$DEP_TOTAL, cycles=$DEP_CYCLES)"
fi

cleanup_fixture

###############################################################################
# Scenario 10: Scan lists git worktrees
###############################################################################
echo "--- Scenario 10: Scan lists git worktrees ---"

# Use the real project -- worktrees exist (we are running in one).
run_scan

WT_COUNT=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
wts = d['git_state']['worktrees']
print(len(wts))
" 2>/dev/null)

WT_HAS_BRANCH=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
wts = d['git_state']['worktrees']
has_branch = any('branch' in wt for wt in wts)
print('true' if has_branch else 'false')
" 2>/dev/null)

if [ "$WT_COUNT" -ge 1 ] && [ "$WT_HAS_BRANCH" = "true" ]; then
    log_pass "Scan lists git worktrees"
else
    log_fail "Scan lists git worktrees (count=$WT_COUNT, has_branch=$WT_HAS_BRANCH)"
fi

###############################################################################
# Summary and tests.json output
###############################################################################
echo ""
echo "================================================================"
TOTAL=$((PASS + FAIL))
echo "Results: $PASS passed, $FAIL failed out of $TOTAL tests"
if [ $FAIL -gt 0 ]; then
    echo -e "Failures:$ERRORS"
fi
echo "================================================================"

# Determine overall status
if [ $FAIL -eq 0 ] && [ $TOTAL -gt 0 ]; then
    STATUS="PASS"
else
    STATUS="FAIL"
fi

# Write tests.json
TESTS_OUTPUT_DIR="$TESTS_DIR/purlin_scan_engine"
mkdir -p "$TESTS_OUTPUT_DIR"
cat > "$TESTS_OUTPUT_DIR/tests.json" << JSONEOF
{
  "feature": "purlin_scan_engine",
  "status": "$STATUS",
  "passed": $PASS,
  "failed": $FAIL,
  "total": $TOTAL,
  "test_file": "tools/test_purlin_scan.sh",
  "scenarios": [
    "Scan detects feature lifecycle from git log",
    "Scan detects missing spec sections",
    "Scan detects numbered section headings (bug fix)",
    "Scan reads test status from tests.json",
    "Scan reports null test status when no tests.json",
    "Scan detects open BUG discovery",
    "Scan detects unacknowledged deviation",
    "Scan parses delivery plan phases",
    "Cached scan returns quickly",
    "Scan handles missing dependency graph gracefully",
    "Scan lists git worktrees"
  ],
  "ran_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSONEOF

echo "Wrote $TESTS_OUTPUT_DIR/tests.json"
exit $FAIL
