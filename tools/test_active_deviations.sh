#!/bin/bash
# test_active_deviations.sh -- Content verification tests for the active
# deviations reference (instructions/references/active_deviations.md).
# Covers 4 unit test scenarios from features/active_deviations.md.
# Produces tests/active_deviations/tests.json at project root.
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

AD_FILE="$PROJECT_ROOT/instructions/references/active_deviations.md"

###############################################################################
echo "=== Active Deviations Tests ==="
###############################################################################

# ---------------------------------------------------------------------------
# Scenario 1: Table format defined with correct columns
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Table format defined with correct columns"

if [ ! -f "$AD_FILE" ]; then
    log_fail "active_deviations.md does not exist at $AD_FILE"
else
    AD_CONTENT=$(cat "$AD_FILE")

    # Table header row with all 4 columns
    if echo "$AD_CONTENT" | grep -q "Spec says.*Implementation does.*Tag.*PM status"; then
        log_pass "Table has all 4 columns: Spec says, Implementation does, Tag, PM status"
    else
        log_fail "Table missing expected columns (Spec says | Implementation does | Tag | PM status)"
    fi

    # Companion file format section exists
    if echo "$AD_CONTENT" | grep -q "Companion File Format"; then
        log_pass "Companion File Format section exists"
    else
        log_fail "Companion File Format section missing"
    fi

    # Table appears inside companion file example
    if echo "$AD_CONTENT" | grep -q 'features/<name>.impl.md'; then
        log_pass "Table format references companion file naming convention"
    else
        log_fail "Table format does not reference companion file naming"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 2: Decision hierarchy covers all PM status values
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Decision hierarchy covers all PM status values"

if [ ! -f "$AD_FILE" ]; then
    log_fail "active_deviations.md does not exist"
else
    AD_CONTENT=$(cat "$AD_FILE")

    # Decision Hierarchy section exists
    if echo "$AD_CONTENT" | grep -q "Decision Hierarchy"; then
        log_pass "Decision Hierarchy section exists"
    else
        log_fail "Decision Hierarchy section missing"
    fi

    # PENDING status with guidance
    if echo "$AD_CONTENT" | grep -q '`PENDING`.*follow the deviation'; then
        log_pass "PENDING status defined with 'follow the deviation' guidance"
    else
        log_fail "PENDING status guidance missing or incorrect"
    fi

    # ACCEPTED status with guidance
    if echo "$AD_CONTENT" | grep -q '`ACCEPTED`.*follow the deviation'; then
        log_pass "ACCEPTED status defined with 'follow the deviation' guidance"
    else
        log_fail "ACCEPTED status guidance missing or incorrect"
    fi

    # REJECTED status with guidance
    if echo "$AD_CONTENT" | grep -q '`REJECTED`.*follow the spec'; then
        log_pass "REJECTED status defined with 'follow the spec' guidance"
    else
        log_fail "REJECTED status guidance missing or incorrect"
    fi

    # No deviation case
    if echo "$AD_CONTENT" | grep -q "No deviation.*follow the spec exactly"; then
        log_pass "No-deviation baseline defined (follow spec exactly)"
    else
        log_fail "No-deviation baseline not defined"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 3: All three flows defined
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] All three flows defined"

if [ ! -f "$AD_FILE" ]; then
    log_fail "active_deviations.md does not exist"
else
    AD_CONTENT=$(cat "$AD_FILE")

    # Flow 1: INFEASIBLE
    if echo "$AD_CONTENT" | grep -q "Flow 1.*INFEASIBLE\|### Flow 1:.*INFEASIBLE"; then
        log_pass "Flow 1 (INFEASIBLE) defined"
    else
        log_fail "Flow 1 (INFEASIBLE) not defined"
    fi

    # INFEASIBLE references /pl-infeasible
    if echo "$AD_CONTENT" | grep -q "/pl-infeasible"; then
        log_pass "INFEASIBLE flow references /pl-infeasible skill"
    else
        log_fail "INFEASIBLE flow does not reference /pl-infeasible"
    fi

    # Flow 2: Inline Deviation
    if echo "$AD_CONTENT" | grep -q "Flow 2.*Inline Deviation\|### Flow 2:.*Inline"; then
        log_pass "Flow 2 (Inline Deviation) defined"
    else
        log_fail "Flow 2 (Inline Deviation) not defined"
    fi

    # Flow 3: SPEC_PROPOSAL
    if echo "$AD_CONTENT" | grep -q "Flow 3.*SPEC_PROPOSAL\|### Flow 3:.*SPEC_PROPOSAL"; then
        log_pass "Flow 3 (SPEC_PROPOSAL) defined"
    else
        log_fail "Flow 3 (SPEC_PROPOSAL) not defined"
    fi

    # SPEC_PROPOSAL references /pl-propose
    if echo "$AD_CONTENT" | grep -q "/pl-propose"; then
        log_pass "SPEC_PROPOSAL flow references /pl-propose skill"
    else
        log_fail "SPEC_PROPOSAL flow does not reference /pl-propose"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 4: All builder decision tags defined with severity
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] All builder decision tags defined with severity"

if [ ! -f "$AD_FILE" ]; then
    log_fail "active_deviations.md does not exist"
else
    AD_CONTENT=$(cat "$AD_FILE")

    # Builder Decision Tags section exists
    if echo "$AD_CONTENT" | grep -q "Builder Decision Tags"; then
        log_pass "Builder Decision Tags section exists"
    else
        log_fail "Builder Decision Tags section missing"
    fi

    # All 5 tags defined with severity
    if echo "$AD_CONTENT" | grep -q '\[CLARIFICATION\].*INFO\|CLARIFICATION.*INFO'; then
        log_pass "[CLARIFICATION] defined with INFO severity"
    else
        log_fail "[CLARIFICATION] not defined or missing INFO severity"
    fi

    if echo "$AD_CONTENT" | grep -q '\[AUTONOMOUS\].*WARN\|AUTONOMOUS.*WARN'; then
        log_pass "[AUTONOMOUS] defined with WARN severity"
    else
        log_fail "[AUTONOMOUS] not defined or missing WARN severity"
    fi

    if echo "$AD_CONTENT" | grep -q '\[DEVIATION\].*HIGH\|DEVIATION.*HIGH'; then
        log_pass "[DEVIATION] defined with HIGH severity"
    else
        log_fail "[DEVIATION] not defined or missing HIGH severity"
    fi

    if echo "$AD_CONTENT" | grep -q '\[DISCOVERY\].*HIGH\|DISCOVERY.*HIGH'; then
        log_pass "[DISCOVERY] defined with HIGH severity"
    else
        log_fail "[DISCOVERY] not defined or missing HIGH severity"
    fi

    if echo "$AD_CONTENT" | grep -q '\[INFEASIBLE\].*CRITICAL\|INFEASIBLE.*CRITICAL'; then
        log_pass "[INFEASIBLE] defined with CRITICAL severity"
    else
        log_fail "[INFEASIBLE] not defined or missing CRITICAL severity"
    fi

    # Format specification
    if echo "$AD_CONTENT" | grep -q 'Format:.*\*\*\[TAG\]\*\*'; then
        log_pass "Tag format specification present"
    else
        log_fail "Tag format specification missing"
    fi

    # Cross-feature discovery rule
    if echo "$AD_CONTENT" | grep -qi "target feature.*companion file\|Cross-feature.*target"; then
        log_pass "Cross-feature discovery filing rule documented"
    else
        log_fail "Cross-feature discovery filing rule not documented"
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
FEAT="active_deviations"
OUTDIR="$TESTS_DIR/$FEAT"
mkdir -p "$OUTDIR"
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_active_deviations.sh\"}"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
