#!/bin/bash
# test_pl_help.sh -- Unit tests for pl-help feature (Purlin unified command table)
# Covers 3 scenarios from features/pl_help.md:
#   1. Command table file exists and is readable
#   2. CLI scripts are discoverable in project root
#   3. CLI scripts respond to --help
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
ERRORS=""

log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

echo "=== pl-help Unit Tests ==="

# ---------------------------------------------------------------------------
# Scenario 1: Command table file exists and is readable
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] Command table file exists and is readable"

CMD_TABLE="$PROJECT_ROOT/instructions/references/purlin_commands.md"

if [ -f "$CMD_TABLE" ]; then
    log_pass "purlin_commands.md exists"
else
    log_fail "purlin_commands.md does not exist at $CMD_TABLE"
fi

if [ -r "$CMD_TABLE" ]; then
    log_pass "purlin_commands.md is readable"
else
    log_fail "purlin_commands.md is not readable"
fi

TABLE_CONTENT=$(cat "$CMD_TABLE" 2>/dev/null || echo "")

if echo "$TABLE_CONTENT" | grep -q "Purlin Agent"; then
    log_pass "Command table contains 'Purlin Agent'"
else
    log_fail "Command table missing 'Purlin Agent'"
fi

if echo "$TABLE_CONTENT" | grep -q "Engineer Mode"; then
    log_pass "Command table contains 'Engineer Mode'"
else
    log_fail "Command table missing 'Engineer Mode'"
fi

if echo "$TABLE_CONTENT" | grep -q "PM Mode"; then
    log_pass "Command table contains 'PM Mode'"
else
    log_fail "Command table missing 'PM Mode'"
fi

if echo "$TABLE_CONTENT" | grep -q "QA Mode"; then
    log_pass "Command table contains 'QA Mode'"
else
    log_fail "Command table missing 'QA Mode'"
fi

# Verify it contains key commands from each mode section
if echo "$TABLE_CONTENT" | grep -q "/pl-build"; then
    log_pass "Command table contains /pl-build (Engineer command)"
else
    log_fail "Command table missing /pl-build"
fi

if echo "$TABLE_CONTENT" | grep -q "/pl-spec"; then
    log_pass "Command table contains /pl-spec (PM command)"
else
    log_fail "Command table missing /pl-spec"
fi

if echo "$TABLE_CONTENT" | grep -q "/pl-verify"; then
    log_pass "Command table contains /pl-verify (QA command)"
else
    log_fail "Command table missing /pl-verify"
fi

# ---------------------------------------------------------------------------
# Scenario 2: CLI scripts are discoverable in project root
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] CLI scripts are discoverable in project root"

SCRIPTS=($(ls "$PROJECT_ROOT"/pl-*.sh 2>/dev/null))

if [ ${#SCRIPTS[@]} -gt 0 ]; then
    log_pass "At least one pl-*.sh file found (count: ${#SCRIPTS[@]})"
else
    log_fail "No pl-*.sh files found in project root"
fi

ALL_EXEC=true
for SCRIPT in "${SCRIPTS[@]}"; do
    if [ ! -x "$SCRIPT" ]; then
        ALL_EXEC=false
        log_fail "$(basename "$SCRIPT") is not executable"
    fi
done
if [ "$ALL_EXEC" = true ] && [ ${#SCRIPTS[@]} -gt 0 ]; then
    log_pass "All discovered pl-*.sh files are executable"
fi

# Verify pl-run.sh specifically is among them
FOUND_PL_RUN=false
for SCRIPT in "${SCRIPTS[@]}"; do
    if [ "$(basename "$SCRIPT")" = "pl-run.sh" ]; then
        FOUND_PL_RUN=true
        break
    fi
done
if [ "$FOUND_PL_RUN" = true ]; then
    log_pass "pl-run.sh is among discovered scripts"
else
    log_fail "pl-run.sh not found among discovered scripts"
fi

# ---------------------------------------------------------------------------
# Scenario 3: CLI scripts respond to --help
# ---------------------------------------------------------------------------
echo ""
echo "[Scenario] CLI scripts respond to --help"

HELP_OUTPUT=$(bash "$PROJECT_ROOT/pl-run.sh" --help 2>/dev/null)
HELP_EXIT=$?

if [ "$HELP_EXIT" -eq 0 ]; then
    log_pass "pl-run.sh --help exits with code 0"
else
    log_fail "pl-run.sh --help exited with code $HELP_EXIT (expected 0)"
fi

if echo "$HELP_OUTPUT" | grep -qi "usage"; then
    log_pass "pl-run.sh --help output contains 'Usage'"
else
    log_fail "pl-run.sh --help output missing 'Usage' (output: $(echo "$HELP_OUTPUT" | head -3))"
fi

# Verify --help output includes option descriptions
if echo "$HELP_OUTPUT" | grep -q -- "--model"; then
    log_pass "pl-run.sh --help lists --model option"
else
    log_fail "pl-run.sh --help missing --model option"
fi

if echo "$HELP_OUTPUT" | grep -q -- "--auto-build"; then
    log_pass "pl-run.sh --help lists --auto-build option"
else
    log_fail "pl-run.sh --help missing --auto-build option"
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
RESULT_STATUS="$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)"
RESULT_JSON="{\"status\": \"$RESULT_STATUS\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_pl_help.sh\"}"
OUTDIR="$TESTS_DIR/pl_help"
mkdir -p "$OUTDIR"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
