#!/bin/bash
# test_purlin_instructions.sh -- Content verification tests for the Purlin
# unified instruction architecture (PURLIN_BASE.md, purlin_commands.md,
# PURLIN_OVERRIDES.md).
# Produces tests/purlin_instruction_architecture/tests.json at project root.
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

BASE_FILE="$PROJECT_ROOT/instructions/PURLIN_BASE.md"
COMMANDS_FILE="$PROJECT_ROOT/instructions/references/purlin_commands.md"
OVERRIDES_FILE="$PROJECT_ROOT/purlin-config-sample/PURLIN_OVERRIDES.md"

###############################################################################
echo "=== Purlin Instruction Architecture Tests ==="
###############################################################################

# --- Scenario: PURLIN_BASE.md defines three modes ---
echo ""
echo "[Scenario] PURLIN_BASE.md defines three modes"

if [ ! -f "$BASE_FILE" ]; then
    log_fail "PURLIN_BASE.md does not exist at $BASE_FILE"
else
    FOUND_ENGINEER=false
    FOUND_PM=false
    FOUND_QA=false

    grep -q "## 3.1 Engineer Mode" "$BASE_FILE" && FOUND_ENGINEER=true
    grep -q "## 3.2 PM Mode" "$BASE_FILE" && FOUND_PM=true
    grep -q "## 3.3 QA Mode" "$BASE_FILE" && FOUND_QA=true

    if $FOUND_ENGINEER; then
        log_pass "PURLIN_BASE.md contains '## 3.1 Engineer Mode' section"
    else
        log_fail "PURLIN_BASE.md missing '## 3.1 Engineer Mode' section"
    fi

    if $FOUND_PM; then
        log_pass "PURLIN_BASE.md contains '## 3.2 PM Mode' section"
    else
        log_fail "PURLIN_BASE.md missing '## 3.2 PM Mode' section"
    fi

    if $FOUND_QA; then
        log_pass "PURLIN_BASE.md contains '## 3.3 QA Mode' section"
    else
        log_fail "PURLIN_BASE.md missing '## 3.3 QA Mode' section"
    fi

    if $FOUND_ENGINEER && $FOUND_PM && $FOUND_QA; then
        log_pass "All three modes defined in PURLIN_BASE.md"
    else
        log_fail "Not all three modes defined in PURLIN_BASE.md"
    fi
fi

# --- Scenario: PURLIN_BASE.md defines open mode ---
echo ""
echo "[Scenario] PURLIN_BASE.md defines open mode"

if [ ! -f "$BASE_FILE" ]; then
    log_fail "PURLIN_BASE.md does not exist"
else
    if grep -qi "open mode" "$BASE_FILE"; then
        log_pass "PURLIN_BASE.md references 'open mode'"
    else
        log_fail "PURLIN_BASE.md does not reference 'open mode'"
    fi

    if grep -q "MUST NOT write" "$BASE_FILE"; then
        log_pass "PURLIN_BASE.md states agent must not write files until mode activated"
    else
        log_fail "PURLIN_BASE.md missing 'MUST NOT write' constraint for open mode"
    fi

    if grep -q "mode.*activated\|mode-activating" "$BASE_FILE"; then
        log_pass "PURLIN_BASE.md references mode activation as prerequisite for writes"
    else
        log_fail "PURLIN_BASE.md missing mode activation prerequisite for writes"
    fi
fi

# --- Scenario: Command reference organized by mode ---
echo ""
echo "[Scenario] Command reference organized by mode"

if [ ! -f "$COMMANDS_FILE" ]; then
    log_fail "purlin_commands.md does not exist at $COMMANDS_FILE"
else
    FOUND_ENG_CMD=false
    FOUND_PM_CMD=false
    FOUND_QA_CMD=false
    FOUND_COMMON_CMD=false

    grep -q "Engineer Mode" "$COMMANDS_FILE" && FOUND_ENG_CMD=true
    grep -q "PM Mode" "$COMMANDS_FILE" && FOUND_PM_CMD=true
    grep -q "QA Mode" "$COMMANDS_FILE" && FOUND_QA_CMD=true
    grep -q "Common" "$COMMANDS_FILE" && FOUND_COMMON_CMD=true

    if $FOUND_ENG_CMD; then
        log_pass "purlin_commands.md has Engineer Mode section"
    else
        log_fail "purlin_commands.md missing Engineer Mode section"
    fi

    if $FOUND_PM_CMD; then
        log_pass "purlin_commands.md has PM Mode section"
    else
        log_fail "purlin_commands.md missing PM Mode section"
    fi

    if $FOUND_QA_CMD; then
        log_pass "purlin_commands.md has QA Mode section"
    else
        log_fail "purlin_commands.md missing QA Mode section"
    fi

    if $FOUND_COMMON_CMD; then
        log_pass "purlin_commands.md has Common section"
    else
        log_fail "purlin_commands.md missing Common section"
    fi
fi

# --- Scenario: Override template has mode sections ---
echo ""
echo "[Scenario] Override template has mode sections"

if [ ! -f "$OVERRIDES_FILE" ]; then
    log_fail "PURLIN_OVERRIDES.md does not exist at $OVERRIDES_FILE"
else
    FOUND_GENERAL=false
    FOUND_ENG_OVR=false
    FOUND_PM_OVR=false
    FOUND_QA_OVR=false

    grep -q "## General" "$OVERRIDES_FILE" && FOUND_GENERAL=true
    grep -q "## Engineer Mode" "$OVERRIDES_FILE" && FOUND_ENG_OVR=true
    grep -q "## PM Mode" "$OVERRIDES_FILE" && FOUND_PM_OVR=true
    grep -q "## QA Mode" "$OVERRIDES_FILE" && FOUND_QA_OVR=true

    if $FOUND_GENERAL; then
        log_pass "PURLIN_OVERRIDES.md has '## General' section"
    else
        log_fail "PURLIN_OVERRIDES.md missing '## General' section"
    fi

    if $FOUND_ENG_OVR; then
        log_pass "PURLIN_OVERRIDES.md has '## Engineer Mode' section"
    else
        log_fail "PURLIN_OVERRIDES.md missing '## Engineer Mode' section"
    fi

    if $FOUND_PM_OVR; then
        log_pass "PURLIN_OVERRIDES.md has '## PM Mode' section"
    else
        log_fail "PURLIN_OVERRIDES.md missing '## PM Mode' section"
    fi

    if $FOUND_QA_OVR; then
        log_pass "PURLIN_OVERRIDES.md has '## QA Mode' section"
    else
        log_fail "PURLIN_OVERRIDES.md missing '## QA Mode' section"
    fi
fi

# --- Scenario: Active Deviations protocol documented ---
echo ""
echo "[Scenario] Active Deviations protocol documented"

if [ ! -f "$BASE_FILE" ]; then
    log_fail "PURLIN_BASE.md does not exist"
else
    if grep -q "Active Deviations" "$BASE_FILE"; then
        log_pass "PURLIN_BASE.md documents Active Deviations protocol"
    else
        log_fail "PURLIN_BASE.md missing Active Deviations protocol"
    fi

    # Check for the table format (headers: Spec says | Implementation does | Tag | PM status)
    if grep -q "Spec says.*Implementation does.*Tag.*PM status" "$BASE_FILE"; then
        log_pass "Active Deviations table format is present (column headers)"
    else
        log_fail "Active Deviations table format missing (expected Spec says | Implementation does | Tag | PM status)"
    fi

    # Check for the 3 flows: INFEASIBLE, inline deviation, SPEC_PROPOSAL
    if grep -q "INFEASIBLE" "$BASE_FILE"; then
        log_pass "Flow 1 (INFEASIBLE) documented"
    else
        log_fail "Flow 1 (INFEASIBLE) not documented"
    fi

    if grep -qi "Inline Deviation\|inline deviation" "$BASE_FILE"; then
        log_pass "Flow 2 (inline deviation) documented"
    else
        log_fail "Flow 2 (inline deviation) not documented"
    fi

    if grep -q "SPEC_PROPOSAL" "$BASE_FILE"; then
        log_pass "Flow 3 (SPEC_PROPOSAL) documented"
    else
        log_fail "Flow 3 (SPEC_PROPOSAL) not documented"
    fi
fi

# --- Scenario: Startup protocol references scan.sh ---
echo ""
echo "[Scenario] Startup protocol references scan.sh"

if [ ! -f "$BASE_FILE" ]; then
    log_fail "PURLIN_BASE.md does not exist"
else
    if grep -q "scan.sh" "$BASE_FILE"; then
        log_pass "PURLIN_BASE.md references scan.sh in startup protocol"
    else
        log_fail "PURLIN_BASE.md does not reference scan.sh"
    fi

    # Check that startup presents work organized by mode
    if grep -q "Engineer work\|Engineer work:" "$BASE_FILE"; then
        log_pass "Startup protocol identifies Engineer work"
    else
        log_fail "Startup protocol does not identify Engineer work"
    fi

    if grep -q "QA work\|QA work:" "$BASE_FILE"; then
        log_pass "Startup protocol identifies QA work"
    else
        log_fail "Startup protocol does not identify QA work"
    fi

    if grep -q "PM work\|PM work:" "$BASE_FILE"; then
        log_pass "Startup protocol identifies PM work"
    else
        log_fail "Startup protocol does not identify PM work"
    fi
fi

# --- Bonus: PURLIN_BASE.md line count sanity check ---
echo ""
echo "[Scenario] PURLIN_BASE.md line count within bounds"

if [ ! -f "$BASE_FILE" ]; then
    log_fail "PURLIN_BASE.md does not exist"
else
    LINE_COUNT=$(wc -l < "$BASE_FILE" | tr -d ' ')
    if [ "$LINE_COUNT" -ge 200 ] && [ "$LINE_COUNT" -le 700 ]; then
        log_pass "PURLIN_BASE.md has $LINE_COUNT lines (within 200-700 range)"
    else
        log_fail "PURLIN_BASE.md has $LINE_COUNT lines (expected 200-700)"
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
FEAT="purlin_instruction_architecture"
OUTDIR="$TESTS_DIR/$FEAT"
mkdir -p "$OUTDIR"
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_purlin_instructions.sh\"}"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
