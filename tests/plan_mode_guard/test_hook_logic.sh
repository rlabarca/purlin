#!/usr/bin/env bash
# Test: Plan-exit-mode-clear hook clears mode state file
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
HOOK="$PROJECT_ROOT/hooks/scripts/plan-exit-mode-clear.sh"

passed=0
failed=0

if [[ ! -f "$HOOK" ]]; then
    echo "FAIL: plan-exit-mode-clear.sh not found"
    exit 1
fi

# Check hook script guards on .purlin directory
if grep -q '\.purlin' "$HOOK"; then
    echo "hook script checks for .purlin directory"
    ((passed++))
else
    echo "FAIL: hook does not check for .purlin directory"
    ((failed++))
fi

# Check hook handles PID-scoped mode files
if grep -q 'PURLIN_SESSION_ID' "$HOOK"; then
    echo "hook handles pid-scoped mode files"
    ((passed++))
else
    echo "FAIL: hook does not handle PID-scoped mode files"
    ((failed++))
fi

# Functional test: create temp dir, write mode, run hook, verify cleared
TMPDIR=$(mktemp -d -t plan-guard-test-XXXXXX)
trap "rm -rf $TMPDIR" EXIT

mkdir -p "$TMPDIR/.purlin/runtime"
echo "engineer" > "$TMPDIR/.purlin/runtime/current_mode"

PURLIN_PROJECT_ROOT="$TMPDIR" bash "$HOOK" > /dev/null 2>&1
mode_content=$(cat "$TMPDIR/.purlin/runtime/current_mode")

if [[ -z "$mode_content" ]]; then
    echo "hook clears mode state file"
    ((passed++))
else
    echo "FAIL: mode file still contains '$mode_content' after hook"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
