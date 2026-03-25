#!/bin/bash
# test_file_classification.sh -- Content verification tests for the file
# classification reference (instructions/references/file_classification.md).
# Covers 5 unit test scenarios from features/file_classification.md.
# Produces tests/file_classification/tests.json at project root.
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

FC_FILE="$PROJECT_ROOT/instructions/references/file_classification.md"
BASE_FILE="$PROJECT_ROOT/instructions/PURLIN_BASE.md"

###############################################################################
echo "=== File Classification Tests ==="
###############################################################################

# ---------------------------------------------------------------------------
# Scenario 1: All standard file types are classified
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] All standard file types are classified"

if [ ! -f "$FC_FILE" ]; then
    log_fail "file_classification.md does not exist at $FC_FILE"
else
    FC_CONTENT=$(cat "$FC_FILE")

    # CODE section exists
    if echo "$FC_CONTENT" | grep -q "## CODE"; then
        log_pass "CODE section exists"
    else
        log_fail "CODE section missing"
    fi

    # SPEC section exists
    if echo "$FC_CONTENT" | grep -q "## SPEC"; then
        log_pass "SPEC section exists"
    else
        log_fail "SPEC section missing"
    fi

    # QA-OWNED section exists
    if echo "$FC_CONTENT" | grep -q "## QA-OWNED"; then
        log_pass "QA-OWNED section exists"
    else
        log_fail "QA-OWNED section missing"
    fi

    # CODE items: source code, scripts, tests, config, skill files, instruction files
    if echo "$FC_CONTENT" | grep -q "Source code"; then
        log_pass "CODE classifies source code"
    else
        log_fail "CODE missing source code classification"
    fi

    if echo "$FC_CONTENT" | grep -q "Scripts"; then
        log_pass "CODE classifies scripts"
    else
        log_fail "CODE missing scripts classification"
    fi

    if echo "$FC_CONTENT" | grep -q "Tests"; then
        log_pass "CODE classifies tests"
    else
        log_fail "CODE missing tests classification"
    fi

    if echo "$FC_CONTENT" | grep -qi "config"; then
        log_pass "CODE classifies config"
    else
        log_fail "CODE missing config classification"
    fi

    if echo "$FC_CONTENT" | grep -q "Skill files"; then
        log_pass "CODE classifies skill files"
    else
        log_fail "CODE missing skill files classification"
    fi

    if echo "$FC_CONTENT" | grep -q "Instruction files"; then
        log_pass "CODE classifies instruction files"
    else
        log_fail "CODE missing instruction files classification"
    fi

    # SPEC items: feature specs, design anchors, policy anchors
    if echo "$FC_CONTENT" | grep -q "Feature specs"; then
        log_pass "SPEC classifies feature specs"
    else
        log_fail "SPEC missing feature specs classification"
    fi

    if echo "$FC_CONTENT" | grep -q "Design anchors"; then
        log_pass "SPEC classifies design anchors"
    else
        log_fail "SPEC missing design anchors classification"
    fi

    if echo "$FC_CONTENT" | grep -q "Policy anchors"; then
        log_pass "SPEC classifies policy anchors"
    else
        log_fail "SPEC missing policy anchors classification"
    fi

    # QA items: discovery sidecars, QA scenario tags, regression JSON
    if echo "$FC_CONTENT" | grep -q "Discovery sidecars"; then
        log_pass "QA-OWNED classifies discovery sidecars"
    else
        log_fail "QA-OWNED missing discovery sidecars classification"
    fi

    if echo "$FC_CONTENT" | grep -q "QA scenario tags"; then
        log_pass "QA-OWNED classifies QA scenario tags"
    else
        log_fail "QA-OWNED missing QA scenario tags classification"
    fi

    if echo "$FC_CONTENT" | grep -qi "Regression.*JSON\|regression.*json"; then
        log_pass "QA-OWNED classifies regression JSON"
    else
        log_fail "QA-OWNED missing regression JSON classification"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 2: PURLIN_BASE.md has no inline file lists
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] PURLIN_BASE.md has no inline file lists"

if [ ! -f "$BASE_FILE" ]; then
    log_fail "PURLIN_BASE.md does not exist at $BASE_FILE"
else
    BASE_CONTENT=$(cat "$BASE_FILE")

    # Engineer write-access references file_classification.md
    if echo "$BASE_CONTENT" | grep -q "Write access.*CODE.*references/file_classification.md\|Write access.*CODE in.*file_classification"; then
        log_pass "Engineer write-access references file_classification.md"
    else
        log_fail "Engineer write-access does not reference file_classification.md"
    fi

    # PM write-access references file_classification.md
    if echo "$BASE_CONTENT" | grep -q "Write access.*SPEC.*references/file_classification.md\|Write access.*SPEC in.*file_classification"; then
        log_pass "PM write-access references file_classification.md"
    else
        log_fail "PM write-access does not reference file_classification.md"
    fi

    # QA write-access references file_classification.md
    if echo "$BASE_CONTENT" | grep -q "Write access.*QA-OWNED.*references/file_classification.md\|Write access.*QA.OWNED in.*file_classification"; then
        log_pass "QA write-access references file_classification.md"
    else
        log_fail "QA write-access does not reference file_classification.md"
    fi

    # Check that mode definitions do NOT contain inline file pattern enumerations
    # in their Write access lines. The pattern "Write access:" lines should
    # delegate to file_classification.md, not list patterns like "*.py", "*.sh" etc.
    WRITE_ACCESS_LINES=$(echo "$BASE_CONTENT" | grep "^\*\*Write access:\*\*")
    HAS_INLINE=false
    while IFS= read -r line; do
        # Check for inline glob patterns like *.py, *.sh, *.md in write-access lines
        if echo "$line" | grep -qE '\*\.(py|sh|js|ts|go|json|md)'; then
            HAS_INLINE=true
        fi
    done <<< "$WRITE_ACCESS_LINES"

    if [ "$HAS_INLINE" = false ]; then
        log_pass "No inline file pattern enumerations in Write access definitions"
    else
        log_fail "Write access definitions contain inline file patterns (should delegate to file_classification.md)"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 3: Cross-mode recording rights documented
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Cross-mode recording rights documented"

if [ ! -f "$FC_FILE" ]; then
    log_fail "file_classification.md does not exist"
else
    FC_CONTENT=$(cat "$FC_FILE")

    # Cross-mode section exists
    if echo "$FC_CONTENT" | grep -q "Cross-Mode Recording Rights"; then
        log_pass "Cross-Mode Recording Rights section exists"
    else
        log_fail "Cross-Mode Recording Rights section missing"
    fi

    # Discovery sidecars: any mode can add new OPEN entries
    if echo "$FC_CONTENT" | grep -qi "Any mode can add new OPEN entries\|any mode.*OPEN"; then
        log_pass "Discovery sidecars: any mode can add new OPEN entries"
    else
        log_fail "Missing: any mode can add new OPEN entries to discovery sidecars"
    fi

    # QA Scenarios: QA adds @auto/@manual tags
    if echo "$FC_CONTENT" | grep -q "@auto.*@manual\|@manual.*@auto"; then
        log_pass "QA Scenarios: QA adds @auto/@manual tags"
    else
        log_fail "Missing: QA adds @auto/@manual tags to scenarios"
    fi

    # Cross-mode table has Owner and "Who can record" columns
    if echo "$FC_CONTENT" | grep -q "Owner.*Who can record\|Owner.*record"; then
        log_pass "Cross-mode table has Owner and 'Who can record' columns"
    else
        log_fail "Cross-mode table missing Owner/Who can record columns"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 4: Skill files classified as CODE
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Skill files classified as CODE"

if [ ! -f "$FC_FILE" ]; then
    log_fail "file_classification.md does not exist"
else
    FC_CONTENT=$(cat "$FC_FILE")

    # .claude/commands/*.md listed under CODE
    if echo "$FC_CONTENT" | grep -q '\.claude/commands/\*\.md'; then
        log_pass "Skill files (.claude/commands/*.md) listed under CODE"
    else
        log_fail "Skill files (.claude/commands/*.md) not found under CODE"
    fi

    # Verify they appear in the CODE section (not SPEC or QA)
    # Extract CODE section content (between ## CODE and ## SPEC)
    CODE_SECTION=$(echo "$FC_CONTENT" | sed -n '/^## CODE/,/^## SPEC/p')
    if echo "$CODE_SECTION" | grep -q '\.claude/commands'; then
        log_pass "Skill files appear in CODE section specifically"
    else
        log_fail "Skill files not in CODE section (may be misclassified)"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 5: DevOps files classified as CODE
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] DevOps files classified as CODE"

if [ ! -f "$FC_FILE" ]; then
    log_fail "file_classification.md does not exist"
else
    FC_CONTENT=$(cat "$FC_FILE")
    CODE_SECTION=$(echo "$FC_CONTENT" | sed -n '/^## CODE/,/^## SPEC/p')

    # Dockerfile
    if echo "$CODE_SECTION" | grep -qi "Dockerfile"; then
        log_pass "Dockerfile classified under CODE"
    else
        log_fail "Dockerfile not classified under CODE"
    fi

    # Makefile
    if echo "$CODE_SECTION" | grep -qi "Makefile"; then
        log_pass "Makefile classified under CODE"
    else
        log_fail "Makefile not classified under CODE"
    fi

    # .github/workflows or CI config
    if echo "$CODE_SECTION" | grep -qi "\.github\|CI"; then
        log_pass "CI configuration (.github/) classified under CODE"
    else
        log_fail "CI configuration not classified under CODE"
    fi

    # Build/CI as a category
    if echo "$CODE_SECTION" | grep -qi "Build.*CI\|CI.*Build\|Build/CI"; then
        log_pass "Build/CI configuration category present in CODE"
    else
        log_fail "Build/CI configuration category missing from CODE"
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
FEAT="file_classification"
OUTDIR="$TESTS_DIR/$FEAT"
mkdir -p "$OUTDIR"
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_file_classification.sh\"}"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
