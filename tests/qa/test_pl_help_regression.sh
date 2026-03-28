#!/usr/bin/env bash
# tests/qa/test_pl_help_regression.sh
# QA-owned regression harness for features/pl_help.md
# Tests: command table file, skill file structure, CLI script discovery
#
# Usage: bash tests/qa/test_pl_help_regression.sh [--write-results]
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: pl_help ==="
echo ""

# PH1: Command table file exists
CMD_TABLE="$PURLIN_ROOT/references/purlin_commands.md"
if [ -f "$CMD_TABLE" ]; then
    log_pass "PH1: purlin_commands.md exists"
else
    log_fail "PH1: purlin_commands.md not found at references/"
fi

# PH2: Command table contains all mode sections
if [ -f "$CMD_TABLE" ]; then
    MISSING=""
    for section in "Engineer Mode" "PM Mode" "QA Mode"; do
        if ! grep -q "$section" "$CMD_TABLE" 2>/dev/null; then
            MISSING="$MISSING $section"
        fi
    done
    if [ -z "$MISSING" ]; then
        log_pass "PH2: command table contains all mode sections"
    else
        log_fail "PH2: command table missing sections:$MISSING"
    fi
fi

# PH3: Skill file exists
SKILL_FILE="$PURLIN_ROOT/.claude/commands/pl-help.md"
if [ -f "$SKILL_FILE" ]; then
    log_pass "PH3: .claude/commands/pl-help.md exists"
else
    log_fail "PH3: pl-help.md skill file not found"
fi

# PH4: Skill file references the command table source
if [ -f "$SKILL_FILE" ]; then
    if grep -q "purlin_commands" "$SKILL_FILE" 2>/dev/null; then
        log_pass "PH4: skill file references purlin_commands"
    else
        log_fail "PH4: skill file does not reference purlin_commands"
    fi
fi

# PH5: Skill file references CLI script discovery via globbing
if [ -f "$SKILL_FILE" ]; then
    if grep -qi "pl-\*\.sh\|glob.*pl-" "$SKILL_FILE" 2>/dev/null; then
        log_pass "PH5: skill file references pl-*.sh globbing"
    else
        log_fail "PH5: skill file does not reference pl-*.sh discovery"
    fi
fi

# PH6: At least one pl-*.sh script exists and is executable
SCRIPTS=( "$PURLIN_ROOT"/pl-*.sh )
if [ -e "${SCRIPTS[0]}" ]; then
    ALL_EXEC=true
    for s in "${SCRIPTS[@]}"; do
        if [ ! -x "$s" ]; then
            ALL_EXEC=false
            break
        fi
    done
    if $ALL_EXEC; then
        log_pass "PH6: ${#SCRIPTS[@]} pl-*.sh scripts found, all executable"
    else
        log_fail "PH6: some pl-*.sh scripts are not executable"
    fi
else
    log_fail "PH6: no pl-*.sh scripts found in project root"
fi

# PH7: Skill file handles no-scripts fallback
if [ -f "$SKILL_FILE" ]; then
    if grep -q "no CLI scripts found\|no.*scripts.*found" "$SKILL_FILE" 2>/dev/null; then
        log_pass "PH7: skill file contains no-scripts fallback text"
    else
        log_fail "PH7: skill file missing no-scripts fallback handling"
    fi
fi

# Summary
echo ""
echo "Results: $((PASS+FAIL))/$((PASS+FAIL)) tests ran, ${PASS} passed, ${FAIL} failed"
if [ $FAIL -gt 0 ]; then
    echo -e "\nFailures:$ERRORS"
    exit 1
fi
exit 0
