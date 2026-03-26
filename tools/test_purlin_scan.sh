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
- **Action Required:** Engineer
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
# Scenario 11: Scan detects failing regression test
###############################################################################
echo "--- Scenario 11: Scan detects failing regression test ---"

setup_fixture

cat > "$FIXTURE_DIR/features/auth_flow.md" << 'FEATEOF'
# Feature: Auth Flow

## 1. Overview
Auth flow feature.

## 2. Requirements
Some requirements.
FEATEOF

mkdir -p "$FIXTURE_DIR/tests/auth_flow"
cat > "$FIXTURE_DIR/tests/auth_flow/regression.json" << 'REGEOF'
{
  "status": "FAIL",
  "passed": 3,
  "failed": 2,
  "total": 5
}
REGEOF

run_scan_fixture "$FIXTURE_DIR"

REG_STATUS=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'auth_flow':
        rs = f.get('regression_status')
        print(rs if rs is not None else 'null')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

REG_FAILED=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'auth_flow':
        rf = f.get('regression_failed')
        print(rf if rf is not None else 'null')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$REG_STATUS" = "FAIL" ] && [ "$REG_FAILED" = "2" ]; then
    log_pass "Scan detects failing regression test"
else
    log_fail "Scan detects failing regression test (status=$REG_STATUS, failed=$REG_FAILED)"
fi

cleanup_fixture

###############################################################################
# Scenario 12: Scan reports null regression status when no regression.json
###############################################################################
echo "--- Scenario 12: Scan reports null regression status when no regression.json ---"

setup_fixture

cat > "$FIXTURE_DIR/features/new_feature.md" << 'FEATEOF'
# Feature: New Feature

## 1. Overview
A new feature with no regression tests.
FEATEOF

run_scan_fixture "$FIXTURE_DIR"

REG_NULL=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'new_feature':
        rs = f.get('regression_status')
        print('null' if rs is None else rs)
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$REG_NULL" = "null" ]; then
    log_pass "Scan reports null regression status when no regression.json"
else
    log_fail "Scan reports null regression status (got: $REG_NULL, expected: null)"
fi

cleanup_fixture

###############################################################################
# Scenario 13: Scan detects spec modified after completion
###############################################################################
echo "--- Scenario 13: Scan detects spec modified after completion ---"

setup_fixture

cat > "$FIXTURE_DIR/features/notifications.md" << 'FEATEOF'
# Feature: Notifications

## 1. Overview
Notifications.
FEATEOF

git -C "$FIXTURE_DIR" add features/notifications.md
git -C "$FIXTURE_DIR" commit -q -m "feat: add notifications"

# Add a status commit
git -C "$FIXTURE_DIR" commit --allow-empty -q -m "status(notifications): [Complete features/notifications.md] [Scope: full]"

# Now modify the spec AFTER the status commit
sleep 1
echo "" >> "$FIXTURE_DIR/features/notifications.md"
echo "## 2. Requirements" >> "$FIXTURE_DIR/features/notifications.md"
echo "New requirements added." >> "$FIXTURE_DIR/features/notifications.md"
git -C "$FIXTURE_DIR" add features/notifications.md
git -C "$FIXTURE_DIR" commit -q -m "spec: add requirements to notifications"

run_scan_fixture "$FIXTURE_DIR"

SPEC_MOD=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'notifications':
        v = f.get('spec_modified_after_completion')
        if v is None:
            print('null')
        else:
            print('true' if v else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$SPEC_MOD" = "true" ]; then
    log_pass "Scan detects spec modified after completion"
else
    log_fail "Scan detects spec modified after completion (got: $SPEC_MOD, expected: true)"
fi

cleanup_fixture

###############################################################################
# Scenario 14: Exempt commits do not trigger spec_modified_after_completion
###############################################################################
echo "--- Scenario 14: Exempt commits do not trigger spec_modified_after_completion ---"

setup_fixture

cat > "$FIXTURE_DIR/features/auth_flow.md" << 'FEATEOF'
# Feature: Auth Flow

## 1. Overview
Auth flow.
FEATEOF

git -C "$FIXTURE_DIR" add features/auth_flow.md
git -C "$FIXTURE_DIR" commit -q -m "feat: add auth flow"
sleep 1
git -C "$FIXTURE_DIR" commit --allow-empty -q -m "status(auth_flow): [Complete features/auth_flow.md] [Scope: full]"

# Modify with an exempt tag
sleep 1
echo "" >> "$FIXTURE_DIR/features/auth_flow.md"
echo "<!-- formatting fix -->" >> "$FIXTURE_DIR/features/auth_flow.md"
git -C "$FIXTURE_DIR" add features/auth_flow.md
git -C "$FIXTURE_DIR" commit -q -m "spec(auth_flow): fix formatting [Migration]"

run_scan_fixture "$FIXTURE_DIR"

SPEC_MOD_EXEMPT=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'auth_flow':
        v = f.get('spec_modified_after_completion')
        if v is None:
            print('null')
        else:
            print('true' if v else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$SPEC_MOD_EXEMPT" = "false" ]; then
    log_pass "Exempt commits do not trigger spec_modified_after_completion"
else
    log_fail "Exempt commits do not trigger spec_modified_after_completion (got: $SPEC_MOD_EXEMPT, expected: false)"
fi

cleanup_fixture

###############################################################################
# Scenario 15: Mixed exempt and non-exempt commits trigger modification
###############################################################################
echo "--- Scenario 15: Mixed exempt and non-exempt commits trigger modification ---"

setup_fixture

cat > "$FIXTURE_DIR/features/auth_flow.md" << 'FEATEOF'
# Feature: Auth Flow

## 1. Overview
Auth flow.
FEATEOF

git -C "$FIXTURE_DIR" add features/auth_flow.md
git -C "$FIXTURE_DIR" commit -q -m "feat: add auth flow"
git -C "$FIXTURE_DIR" commit --allow-empty -q -m "status(auth_flow): [Complete features/auth_flow.md] [Scope: full]"

# First modification: exempt
sleep 1
echo "<!-- fmt -->" >> "$FIXTURE_DIR/features/auth_flow.md"
git -C "$FIXTURE_DIR" add features/auth_flow.md
git -C "$FIXTURE_DIR" commit -q -m "spec: formatting [Spec-FMT]"

# Second modification: NOT exempt
echo "## 2. Requirements" >> "$FIXTURE_DIR/features/auth_flow.md"
git -C "$FIXTURE_DIR" add features/auth_flow.md
git -C "$FIXTURE_DIR" commit -q -m "spec: add requirements to auth flow"

run_scan_fixture "$FIXTURE_DIR"

SPEC_MOD_MIXED=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'auth_flow':
        v = f.get('spec_modified_after_completion')
        if v is None:
            print('null')
        else:
            print('true' if v else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$SPEC_MOD_MIXED" = "true" ]; then
    log_pass "Mixed exempt and non-exempt commits trigger modification"
else
    log_fail "Mixed exempt and non-exempt commits trigger modification (got: $SPEC_MOD_MIXED, expected: true)"
fi

cleanup_fixture

###############################################################################
# Scenario 16: Scan reports null modification when never completed
###############################################################################
echo "--- Scenario 16: Scan reports null modification when never completed ---"

setup_fixture

cat > "$FIXTURE_DIR/features/new_feature.md" << 'FEATEOF'
# Feature: New Feature

## 1. Overview
Never completed feature.
FEATEOF

git -C "$FIXTURE_DIR" add features/new_feature.md
git -C "$FIXTURE_DIR" commit -q -m "feat: add new feature"

# No status commit exists

run_scan_fixture "$FIXTURE_DIR"

SPEC_MOD_NULL=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'new_feature':
        v = f.get('spec_modified_after_completion')
        if v is None:
            print('null')
        else:
            print('true' if v else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$SPEC_MOD_NULL" = "null" ]; then
    log_pass "Scan reports null modification when never completed"
else
    log_fail "Scan reports null modification when never completed (got: $SPEC_MOD_NULL, expected: null)"
fi

cleanup_fixture

###############################################################################
# Scenario 17: Scan uses current branch only for status commits
###############################################################################
echo "--- Scenario 17: Scan uses current branch only for status commits ---"

# Verify scan.py does NOT use --all flag in git log calls
SCAN_PY="$PROJECT_ROOT/tools/cdd/scan.py"
ALL_FLAG_COUNT=$(grep -c -- '--all' "$SCAN_PY" 2>/dev/null || true)
ALL_FLAG_COUNT=$(echo "$ALL_FLAG_COUNT" | tr -d '[:space:]')

if [ "$ALL_FLAG_COUNT" = "0" ]; then
    log_pass "Scan uses current branch only (no --all flag in scan.py)"
else
    log_fail "Scan uses current branch only (found $ALL_FLAG_COUNT --all flags in scan.py)"
fi

###############################################################################
# Scenario 18: Scan detects newly created spec as modified
###############################################################################
echo "--- Scenario 18: Scan detects newly created spec as modified ---"

setup_fixture

cat > "$FIXTURE_DIR/features/recreated.md" << 'FEATEOF'
# Feature: Recreated

## 1. Overview
Original spec.
FEATEOF

git -C "$FIXTURE_DIR" add features/recreated.md
git -C "$FIXTURE_DIR" commit -q -m "feat: add recreated"
git -C "$FIXTURE_DIR" commit --allow-empty -q -m "status(recreated): [Complete features/recreated.md] [Scope: full]"

# Delete and recreate the spec
sleep 1
rm "$FIXTURE_DIR/features/recreated.md"
git -C "$FIXTURE_DIR" add features/recreated.md
git -C "$FIXTURE_DIR" commit -q -m "chore: remove recreated spec"

cat > "$FIXTURE_DIR/features/recreated.md" << 'FEATEOF'
# Feature: Recreated

## 1. Overview
New version of spec.

## 2. Requirements
All new requirements.
FEATEOF

git -C "$FIXTURE_DIR" add features/recreated.md
git -C "$FIXTURE_DIR" commit -q -m "spec: recreate spec"

run_scan_fixture "$FIXTURE_DIR"

SPEC_RECREATED=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for f in d['features']:
    if f['name'] == 'recreated':
        v = f.get('spec_modified_after_completion')
        if v is None:
            print('null')
        else:
            print('true' if v else 'false')
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

if [ "$SPEC_RECREATED" = "true" ]; then
    log_pass "Scan detects newly created spec as modified"
else
    log_fail "Scan detects newly created spec as modified (got: $SPEC_RECREATED, expected: true)"
fi

cleanup_fixture

###############################################################################
# Scenario 19: Exemption check uses batched git call
###############################################################################
echo "--- Scenario 19: Exemption check uses batched git call ---"

# Verify scan.py does NOT have per-feature git calls for exemption checks.
# The scan.py should use a single batched git log call.
SCAN_PY="$PROJECT_ROOT/tools/cdd/scan.py"

# Count git subprocess calls in the exemption-related code.
# A well-batched implementation should not have git calls inside loops.
GIT_CALL_IN_LOOP=$(python3 -c "
import ast, sys
with open('$SCAN_PY') as f:
    source = f.read()
tree = ast.parse(source)
# Count subprocess calls that contain 'git' inside for loops
found_git_in_loop = False
for node in ast.walk(tree):
    if isinstance(node, ast.For):
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_str = ast.dump(child)
                if 'subprocess' in call_str and 'git' in ast.dump(child):
                    found_git_in_loop = True
                    break
print('true' if found_git_in_loop else 'false')
" 2>/dev/null)

# Check that scan.py uses a single _run_git helper (batched approach).
# Count how many unique git subprocess call sites exist.
GIT_CALL_SITES=$(grep -c '_run_git\|subprocess.run.*git' "$SCAN_PY" 2>/dev/null || true)
GIT_CALL_SITES=$(echo "$GIT_CALL_SITES" | tr -d '[:space:]')

if [ "$GIT_CALL_SITES" -le 10 ]; then
    log_pass "Exemption check uses batched git calls ($GIT_CALL_SITES call sites)"
else
    log_fail "Exemption check uses batched git calls (found $GIT_CALL_SITES call sites, expected <= 10)"
fi

###############################################################################
# Scenario 20: Scan surfaces smoke candidates for high-fan-out completed features
###############################################################################
echo "--- Scenario 20: Scan surfaces smoke candidates ---"

setup_fixture

# Create 4 features: hub_feature is a prerequisite for the other 3
cat > "$FIXTURE_DIR/features/hub_feature.md" << 'FEATEOF'
# Feature: Hub Feature

> Label: "Core: Hub"
> Category: "Install, Update & Scripts"

## 1. Overview
Central feature.

## 2. Requirements
Some requirements.
FEATEOF

for dep in dep_a dep_b dep_c; do
cat > "$FIXTURE_DIR/features/${dep}.md" << FEATEOF
# Feature: ${dep}

> Prerequisite: features/hub_feature.md

## 1. Overview
Depends on hub.
FEATEOF
done

# Create dependency graph (hub_feature has 3 dependents)
mkdir -p "$FIXTURE_DIR/.purlin/cache"
cat > "$FIXTURE_DIR/.purlin/cache/dependency_graph.json" << 'DEPEOF'
{
  "features": [
    {"file": "features/hub_feature.md", "category": "Install, Update & Scripts", "label": "Core: Hub", "prerequisites": []},
    {"file": "features/dep_a.md", "category": "", "label": "", "prerequisites": ["hub_feature.md"]},
    {"file": "features/dep_b.md", "category": "", "label": "", "prerequisites": ["hub_feature.md"]},
    {"file": "features/dep_c.md", "category": "", "label": "", "prerequisites": ["hub_feature.md"]}
  ]
}
DEPEOF

# Mark hub_feature as COMPLETE via git status commit
git -C "$FIXTURE_DIR" add -A
git -C "$FIXTURE_DIR" commit -q -m "status(hub_feature): [Complete features/hub_feature.md]"

# No tier table — hub_feature should appear as candidate
# No PURLIN_OVERRIDES.md with tier table

run_scan_fixture "$FIXTURE_DIR"

CANDIDATE_FEATURE=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
candidates = d.get('smoke_candidates', [])
for c in candidates:
    if c['feature'] == 'hub_feature':
        print(c['feature'])
        sys.exit(0)
print('NOT_FOUND')
" 2>/dev/null)

CANDIDATE_DEPS=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for c in d.get('smoke_candidates', []):
    if c['feature'] == 'hub_feature':
        print(c['dependents'])
        sys.exit(0)
print(-1)
" 2>/dev/null)

if [ "$CANDIDATE_FEATURE" = "hub_feature" ] && [ "$CANDIDATE_DEPS" = "3" ]; then
    log_pass "Scan surfaces smoke candidates"
else
    log_fail "Scan surfaces smoke candidates (feature=$CANDIDATE_FEATURE, deps=$CANDIDATE_DEPS)"
fi

cleanup_fixture

###############################################################################
# Scenario 21: Scan excludes already-classified smoke features from candidates
###############################################################################
echo "--- Scenario 21: Scan excludes already-classified smoke features ---"

setup_fixture

# Same hub_feature setup
cat > "$FIXTURE_DIR/features/hub_feature.md" << 'FEATEOF'
# Feature: Hub Feature

> Label: "Core: Hub"
> Category: "Install, Update & Scripts"

## 1. Overview
Central feature.

## 2. Requirements
Some requirements.
FEATEOF

for dep in dep_a dep_b dep_c; do
cat > "$FIXTURE_DIR/features/${dep}.md" << FEATEOF
# Feature: ${dep}

> Prerequisite: features/hub_feature.md

## 1. Overview
Depends on hub.
FEATEOF
done

mkdir -p "$FIXTURE_DIR/.purlin/cache"
cat > "$FIXTURE_DIR/.purlin/cache/dependency_graph.json" << 'DEPEOF'
{
  "features": [
    {"file": "features/hub_feature.md", "category": "Install, Update & Scripts", "label": "Core: Hub", "prerequisites": []},
    {"file": "features/dep_a.md", "category": "", "label": "", "prerequisites": ["hub_feature.md"]},
    {"file": "features/dep_b.md", "category": "", "label": "", "prerequisites": ["hub_feature.md"]},
    {"file": "features/dep_c.md", "category": "", "label": "", "prerequisites": ["hub_feature.md"]}
  ]
}
DEPEOF

# Mark as COMPLETE
git -C "$FIXTURE_DIR" add -A
git -C "$FIXTURE_DIR" commit -q -m "status(hub_feature): [Complete features/hub_feature.md]"

# NOW add hub_feature to tier table as smoke — should be excluded
cat > "$FIXTURE_DIR/.purlin/PURLIN_OVERRIDES.md" << 'TIEREOF'
# Overrides

## Test Priority Tiers

| Feature | Tier |
|---------|------|
| hub_feature | smoke |
TIEREOF

git -C "$FIXTURE_DIR" add -A
git -C "$FIXTURE_DIR" commit -q -m "add tier table"

run_scan_fixture "$FIXTURE_DIR"

EXCLUDED=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
candidates = d.get('smoke_candidates', [])
for c in candidates:
    if c['feature'] == 'hub_feature':
        print('FOUND')
        sys.exit(0)
print('EXCLUDED')
" 2>/dev/null)

if [ "$EXCLUDED" = "EXCLUDED" ]; then
    log_pass "Scan excludes already-classified smoke features"
else
    log_fail "Scan excludes already-classified smoke features (hub_feature still in candidates)"
fi

cleanup_fixture

###############################################################################
# Scenario 22: Scan excludes non-complete features from smoke candidates
###############################################################################
echo "--- Scenario 22: Scan excludes non-complete features from smoke candidates ---"

setup_fixture

# hub_feature with 3 dependents but NOT marked Complete
cat > "$FIXTURE_DIR/features/hub_feature.md" << 'FEATEOF'
# Feature: Hub Feature

> Label: "Core: Hub"
> Category: "Install, Update & Scripts"

## 1. Overview
Central feature.
FEATEOF

for dep in dep_a dep_b dep_c; do
cat > "$FIXTURE_DIR/features/${dep}.md" << FEATEOF
# Feature: ${dep}

> Prerequisite: features/hub_feature.md

## 1. Overview
Depends on hub.
FEATEOF
done

mkdir -p "$FIXTURE_DIR/.purlin/cache"
cat > "$FIXTURE_DIR/.purlin/cache/dependency_graph.json" << 'DEPEOF'
{
  "features": [
    {"file": "features/hub_feature.md", "category": "Install, Update & Scripts", "label": "Core: Hub", "prerequisites": []},
    {"file": "features/dep_a.md", "category": "", "label": "", "prerequisites": ["hub_feature.md"]},
    {"file": "features/dep_b.md", "category": "", "label": "", "prerequisites": ["hub_feature.md"]},
    {"file": "features/dep_c.md", "category": "", "label": "", "prerequisites": ["hub_feature.md"]}
  ]
}
DEPEOF

# Commit but NO status commit — lifecycle is TODO
git -C "$FIXTURE_DIR" add -A
git -C "$FIXTURE_DIR" commit -q -m "add features"

run_scan_fixture "$FIXTURE_DIR"

NON_COMPLETE=$(echo "$SCAN_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
candidates = d.get('smoke_candidates', [])
for c in candidates:
    if c['feature'] == 'hub_feature':
        print('FOUND')
        sys.exit(0)
print('EXCLUDED')
" 2>/dev/null)

if [ "$NON_COMPLETE" = "EXCLUDED" ]; then
    log_pass "Scan excludes non-complete features from smoke candidates"
else
    log_fail "Scan excludes non-complete features from smoke candidates (hub_feature in candidates despite TODO lifecycle)"
fi

cleanup_fixture

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
    "Scan lists git worktrees",
    "Scan detects failing regression test",
    "Scan reports null regression status when no regression.json",
    "Scan detects spec modified after completion",
    "Exempt commits do not trigger spec_modified_after_completion",
    "Mixed exempt and non-exempt commits trigger modification",
    "Scan reports null modification when never completed",
    "Scan uses current branch only for status commits",
    "Scan detects newly created spec as modified",
    "Exemption check uses batched git calls",
    "Scan surfaces smoke candidates",
    "Scan excludes already-classified smoke features",
    "Scan excludes non-complete features from smoke candidates"
  ],
  "ran_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSONEOF

echo "Wrote $TESTS_OUTPUT_DIR/tests.json"
exit $FAIL
