#!/bin/bash
# test_commit_conventions.sh -- Content verification tests for the commit
# conventions reference (instructions/references/commit_conventions.md).
# Covers 3 unit test scenarios from features/commit_conventions.md.
# Produces tests/commit_conventions/tests.json at project root.
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

CC_FILE="$PROJECT_ROOT/instructions/references/commit_conventions.md"

###############################################################################
echo "=== Commit Conventions Tests ==="
###############################################################################

# ---------------------------------------------------------------------------
# Scenario 1: All mode prefixes defined
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] All mode prefixes defined"

if [ ! -f "$CC_FILE" ]; then
    log_fail "commit_conventions.md does not exist at $CC_FILE"
else
    CC_CONTENT=$(cat "$CC_FILE")

    # Engineer prefixes: feat, fix, test
    if echo "$CC_CONTENT" | grep -q '`feat('; then
        log_pass "Engineer prefix 'feat' defined"
    else
        log_fail "Engineer prefix 'feat' not defined"
    fi

    if echo "$CC_CONTENT" | grep -q '`fix('; then
        log_pass "Engineer prefix 'fix' defined"
    else
        log_fail "Engineer prefix 'fix' not defined"
    fi

    if echo "$CC_CONTENT" | grep -q '`test('; then
        log_pass "Engineer prefix 'test' defined"
    else
        log_fail "Engineer prefix 'test' not defined"
    fi

    # PM prefixes: spec, design
    if echo "$CC_CONTENT" | grep -q '`spec('; then
        log_pass "PM prefix 'spec' defined"
    else
        log_fail "PM prefix 'spec' not defined"
    fi

    if echo "$CC_CONTENT" | grep -q '`design('; then
        log_pass "PM prefix 'design' defined"
    else
        log_fail "PM prefix 'design' not defined"
    fi

    # QA prefixes: qa, status
    if echo "$CC_CONTENT" | grep -q '`qa('; then
        log_pass "QA prefix 'qa' defined"
    else
        log_fail "QA prefix 'qa' not defined"
    fi

    if echo "$CC_CONTENT" | grep -q '`status('; then
        log_pass "QA prefix 'status' defined"
    else
        log_fail "QA prefix 'status' not defined"
    fi

    # Mode attribution table exists with Engineer, PM, QA, Shared rows
    if echo "$CC_CONTENT" | grep -q "| Engineer"; then
        log_pass "Mode attribution table has Engineer row"
    else
        log_fail "Mode attribution table missing Engineer row"
    fi

    if echo "$CC_CONTENT" | grep -q "| PM"; then
        log_pass "Mode attribution table has PM row"
    else
        log_fail "Mode attribution table missing PM row"
    fi

    if echo "$CC_CONTENT" | grep -q "| QA"; then
        log_pass "Mode attribution table has QA row"
    else
        log_fail "Mode attribution table missing QA row"
    fi

    if echo "$CC_CONTENT" | grep -q "| Shared"; then
        log_pass "Mode attribution table has Shared row"
    else
        log_fail "Mode attribution table missing Shared row"
    fi

    # Purlin-Mode trailer requirement
    if echo "$CC_CONTENT" | grep -q "Purlin-Mode:"; then
        log_pass "Purlin-Mode trailer requirement documented"
    else
        log_fail "Purlin-Mode trailer requirement not documented"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 2: Exemption tags defined with usage
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Exemption tags defined with usage"

if [ ! -f "$CC_FILE" ]; then
    log_fail "commit_conventions.md does not exist"
else
    CC_CONTENT=$(cat "$CC_FILE")

    # [QA-Tags] defined
    if echo "$CC_CONTENT" | grep -q '\[QA-Tags\]'; then
        log_pass "[QA-Tags] exemption tag defined"
    else
        log_fail "[QA-Tags] exemption tag not defined"
    fi

    # [Spec-FMT] defined
    if echo "$CC_CONTENT" | grep -q '\[Spec-FMT\]'; then
        log_pass "[Spec-FMT] exemption tag defined"
    else
        log_fail "[Spec-FMT] exemption tag not defined"
    fi

    # [Migration] defined
    if echo "$CC_CONTENT" | grep -q '\[Migration\]'; then
        log_pass "[Migration] exemption tag defined"
    else
        log_fail "[Migration] exemption tag not defined"
    fi

    # Each has a "When to Use" column
    if echo "$CC_CONTENT" | grep -q "When to Use"; then
        log_pass "Exemption tags table has 'When to Use' column"
    else
        log_fail "Exemption tags table missing 'When to Use' column"
    fi

    # Lifecycle preservation rule documented
    if echo "$CC_CONTENT" | grep -qi "lifecycle.*preserved\|lifecycle is preserved"; then
        log_pass "Lifecycle preservation rule for exempt tags documented"
    else
        log_fail "Lifecycle preservation rule not documented"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 3: Status tag format includes scope
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Status tag format includes scope"

if [ ! -f "$CC_FILE" ]; then
    log_fail "commit_conventions.md does not exist"
else
    CC_CONTENT=$(cat "$CC_FILE")

    # Scope types defined
    if echo "$CC_CONTENT" | grep -q '`full`'; then
        log_pass "Scope type 'full' defined"
    else
        log_fail "Scope type 'full' not defined"
    fi

    if echo "$CC_CONTENT" | grep -q '`targeted'; then
        log_pass "Scope type 'targeted' defined"
    else
        log_fail "Scope type 'targeted' not defined"
    fi

    if echo "$CC_CONTENT" | grep -q '`cosmetic`'; then
        log_pass "Scope type 'cosmetic' defined"
    else
        log_fail "Scope type 'cosmetic' not defined"
    fi

    if echo "$CC_CONTENT" | grep -q '`dependency-only`'; then
        log_pass "Scope type 'dependency-only' defined"
    else
        log_fail "Scope type 'dependency-only' not defined"
    fi

    # Status tag format examples
    if echo "$CC_CONTENT" | grep -q '\[Complete features/'; then
        log_pass "Status tag [Complete] format defined"
    else
        log_fail "Status tag [Complete] format not defined"
    fi

    if echo "$CC_CONTENT" | grep -q '\[Ready for Verification'; then
        log_pass "Status tag [Ready for Verification] format defined"
    else
        log_fail "Status tag [Ready for Verification] format not defined"
    fi

    if echo "$CC_CONTENT" | grep -q '\[Verified\]'; then
        log_pass "QA [Verified] tag defined"
    else
        log_fail "QA [Verified] tag not defined"
    fi

    # Standalone commit requirement
    if echo "$CC_CONTENT" | grep -qi "standalone\|separate.*standalone"; then
        log_pass "Status tag commits required to be standalone"
    else
        log_fail "Standalone requirement for status tag commits not documented"
    fi
fi

###############################################################################
# Results
###############################################################################
echo ""
echo "==============================="
TOTAL=$((PASS + FAIL))
echo "  Results: $PASS/$TOTAL passed"
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "  Failures:"
    echo -e "$ERRORS"
fi
echo "==============================="

# Write test results
FEAT="commit_conventions"
OUTDIR="$TESTS_DIR/$FEAT"
mkdir -p "$OUTDIR"
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_commit_conventions.sh\"}"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
