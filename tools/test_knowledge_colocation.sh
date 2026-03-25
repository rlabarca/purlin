#!/bin/bash
# test_knowledge_colocation.sh -- Content verification tests for the knowledge
# colocation reference (instructions/references/knowledge_colocation.md).
# Covers 4 unit test scenarios from features/knowledge_colocation.md.
# Produces tests/knowledge_colocation/tests.json at project root.
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

KC_FILE="$PROJECT_ROOT/instructions/references/knowledge_colocation.md"

###############################################################################
echo "=== Knowledge Colocation Tests ==="
###############################################################################

# ---------------------------------------------------------------------------
# Scenario 1: Three anchor prefixes defined with ownership
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Three anchor prefixes defined with ownership"

if [ ! -f "$KC_FILE" ]; then
    log_fail "knowledge_colocation.md does not exist at $KC_FILE"
else
    KC_CONTENT=$(cat "$KC_FILE")

    # Anchor Node Taxonomy section exists
    if echo "$KC_CONTENT" | grep -q "Anchor Node Taxonomy"; then
        log_pass "Anchor Node Taxonomy section exists"
    else
        log_fail "Anchor Node Taxonomy section missing"
    fi

    # arch_*.md is Engineer-owned
    if echo "$KC_CONTENT" | grep -q 'arch_\*\.md.*Engineer\|`arch_\*\.md`.*Engineer'; then
        log_pass "arch_*.md defined as Engineer-owned"
    else
        log_fail "arch_*.md not defined as Engineer-owned"
    fi

    # design_*.md is PM-owned
    if echo "$KC_CONTENT" | grep -q 'design_\*\.md.*PM\|`design_\*\.md`.*PM'; then
        log_pass "design_*.md defined as PM-owned"
    else
        log_fail "design_*.md not defined as PM-owned"
    fi

    # policy_*.md is PM-owned
    if echo "$KC_CONTENT" | grep -q 'policy_\*\.md.*PM\|`policy_\*\.md`.*PM'; then
        log_pass "policy_*.md defined as PM-owned"
    else
        log_fail "policy_*.md not defined as PM-owned"
    fi

    # Editing anchor resets dependent features
    if echo "$KC_CONTENT" | grep -qi "reset.*TODO\|resets.*\[TODO\]\|resets all dependent"; then
        log_pass "Anchor edit triggers status reset to TODO"
    else
        log_fail "Anchor edit status reset rule not documented"
    fi

    # Prerequisite link requirement
    if echo "$KC_CONTENT" | grep -q 'Prerequisite:'; then
        log_pass "Prerequisite link requirement documented"
    else
        log_fail "Prerequisite link requirement not documented"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 2: Companion file conventions complete
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Companion file conventions complete"

if [ ! -f "$KC_FILE" ]; then
    log_fail "knowledge_colocation.md does not exist"
else
    KC_CONTENT=$(cat "$KC_FILE")

    # Companion Files section exists
    if echo "$KC_CONTENT" | grep -q "## Companion Files"; then
        log_pass "Companion Files section exists"
    else
        log_fail "Companion Files section missing"
    fi

    # Naming convention
    if echo "$KC_CONTENT" | grep -q '<name>.impl.md'; then
        log_pass "Companion file naming convention (*.impl.md) documented"
    else
        log_fail "Companion file naming convention not documented"
    fi

    # Standalone property
    if echo "$KC_CONTENT" | grep -qi "Standalone.*companion files are standalone\|standalone.*feature files do NOT reference"; then
        log_pass "Companion files documented as standalone"
    else
        log_fail "Companion files standalone property not documented"
    fi

    # Status reset exemption
    if echo "$KC_CONTENT" | grep -qi "Status reset exemption\|do NOT reset.*lifecycle"; then
        log_pass "Companion file status reset exemption documented"
    else
        log_fail "Companion file status reset exemption not documented"
    fi

    # References active_deviations.md for table format
    if echo "$KC_CONTENT" | grep -q "active_deviations.md"; then
        log_pass "References active_deviations.md for table format"
    else
        log_fail "Does not reference active_deviations.md"
    fi

    # Engineer-owned
    if echo "$KC_CONTENT" | grep -q "Engineer"; then
        log_pass "Companion files noted as Engineer-owned"
    else
        log_fail "Companion file ownership (Engineer) not documented"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 3: Discovery sidecar conventions complete
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Discovery sidecar conventions complete"

if [ ! -f "$KC_FILE" ]; then
    log_fail "knowledge_colocation.md does not exist"
else
    KC_CONTENT=$(cat "$KC_FILE")

    # Discovery Sidecars section exists
    if echo "$KC_CONTENT" | grep -q "## Discovery Sidecars"; then
        log_pass "Discovery Sidecars section exists"
    else
        log_fail "Discovery Sidecars section missing"
    fi

    # QA owns lifecycle
    if echo "$KC_CONTENT" | grep -q "QA owns lifecycle"; then
        log_pass "QA owns sidecar lifecycle documented"
    else
        log_fail "QA lifecycle ownership not documented"
    fi

    # Any mode can record OPEN entries
    if echo "$KC_CONTENT" | grep -qi "Any mode can record\|any mode.*OPEN"; then
        log_pass "Any mode can record new OPEN entries documented"
    else
        log_fail "Any mode recording rule not documented"
    fi

    # All 4 discovery types defined
    if echo "$KC_CONTENT" | grep -q '\[BUG\]'; then
        log_pass "[BUG] discovery type defined"
    else
        log_fail "[BUG] discovery type not defined"
    fi

    if echo "$KC_CONTENT" | grep -q '\[DISCOVERY\]'; then
        log_pass "[DISCOVERY] discovery type defined"
    else
        log_fail "[DISCOVERY] discovery type not defined"
    fi

    if echo "$KC_CONTENT" | grep -q '\[INTENT_DRIFT\]'; then
        log_pass "[INTENT_DRIFT] discovery type defined"
    else
        log_fail "[INTENT_DRIFT] discovery type not defined"
    fi

    if echo "$KC_CONTENT" | grep -q '\[SPEC_DISPUTE\]'; then
        log_pass "[SPEC_DISPUTE] discovery type defined"
    else
        log_fail "[SPEC_DISPUTE] discovery type not defined"
    fi

    # Discovery lifecycle
    if echo "$KC_CONTENT" | grep -q "OPEN.*SPEC_UPDATED.*RESOLVED.*PRUNED"; then
        log_pass "Discovery lifecycle (OPEN -> SPEC_UPDATED -> RESOLVED -> PRUNED) defined"
    else
        log_fail "Discovery lifecycle not fully defined"
    fi

    # References /pl-discovery
    if echo "$KC_CONTENT" | grep -q "/pl-discovery"; then
        log_pass "References /pl-discovery for full protocol"
    else
        log_fail "Does not reference /pl-discovery"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 4: Cross-cutting standards pattern has 3 tiers
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Cross-cutting standards pattern has 3 tiers"

if [ ! -f "$KC_FILE" ]; then
    log_fail "knowledge_colocation.md does not exist"
else
    KC_CONTENT=$(cat "$KC_FILE")

    # Cross-Cutting Standards section exists
    if echo "$KC_CONTENT" | grep -q "Cross-Cutting Standards"; then
        log_pass "Cross-Cutting Standards section exists"
    else
        log_fail "Cross-Cutting Standards section missing"
    fi

    # Tier 1: Anchor Node
    if echo "$KC_CONTENT" | grep -qF "**Anchor Node**"; then
        log_pass "Tier 1 (Anchor Node) defined"
    else
        log_fail "Tier 1 (Anchor Node) not defined"
    fi

    # Tier 2: Foundation Feature
    if echo "$KC_CONTENT" | grep -qF "**Foundation Feature**"; then
        log_pass "Tier 2 (Foundation Feature) defined"
    else
        log_fail "Tier 2 (Foundation Feature) not defined"
    fi

    # Tier 3: Consumer Features
    if echo "$KC_CONTENT" | grep -qF "**Consumer Features**"; then
        log_pass "Tier 3 (Consumer Features) defined"
    else
        log_fail "Tier 3 (Consumer Features) not defined"
    fi

    # Prerequisite link requirements for tiers
    if echo "$KC_CONTENT" | grep -q 'Prerequisite.*link.*anchor\|`> Prerequisite:`.*link'; then
        log_pass "Prerequisite link requirements stated for tiers"
    else
        log_fail "Prerequisite link requirements not stated for tiers"
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
FEAT="knowledge_colocation"
OUTDIR="$TESTS_DIR/$FEAT"
mkdir -p "$OUTDIR"
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_knowledge_colocation.sh\"}"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
