#!/usr/bin/env bash
# tests/qa/test_purlin_mode_system_regression.sh
# QA-owned regression harness for features/purlin_mode_system.md
# Tests: Old consolidated skill files are deleted after mode system migration
#
# Usage: bash tests/qa/test_purlin_mode_system_regression.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: purlin_mode_system ==="
echo ""

COMMANDS_DIR="$PURLIN_ROOT/.claude/commands"

# List of old consolidated skills that must not exist
OLD_SKILLS=(
    "pl-release-check.md"
    "pl-release-run.md"
    "pl-release-step.md"
    "pl-regression-run.md"
    "pl-regression-author.md"
    "pl-regression-evaluate.md"
    "pl-remote-push.md"
    "pl-remote-pull.md"
    "pl-remote-add.md"
    "pl-edit-base.md"
)

# PMS1: Each old skill must not exist
ALL_ABSENT=true
for skill in "${OLD_SKILLS[@]}"; do
    if [ -f "$COMMANDS_DIR/$skill" ]; then
        log_fail "PMS1: $skill still exists (should be deleted)"
        ALL_ABSENT=false
    fi
done

if [ "$ALL_ABSENT" = true ]; then
    log_pass "PMS1: all 10 old consolidated skill files are absent"
fi

# PMS2: The commands directory itself still exists (sanity check)
if [ -d "$COMMANDS_DIR" ]; then
    log_pass "PMS2: .claude/commands/ directory exists"
else
    log_fail "PMS2: .claude/commands/ directory is missing"
fi

# PMS3: Replacement consolidated skills exist
REPLACEMENTS=("pl-release.md" "pl-regression.md" "pl-remote.md")
ALL_PRESENT=true
for skill in "${REPLACEMENTS[@]}"; do
    if [ ! -f "$COMMANDS_DIR/$skill" ]; then
        log_fail "PMS3: replacement skill $skill not found"
        ALL_PRESENT=false
    fi
done

if [ "$ALL_PRESENT" = true ]; then
    log_pass "PMS3: all replacement consolidated skills exist"
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
