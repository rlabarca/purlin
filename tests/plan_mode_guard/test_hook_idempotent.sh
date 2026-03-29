#!/usr/bin/env bash
# Test: Plan-exit-mode-clear hook is safe when mode file is empty or missing
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
HOOK="$PROJECT_ROOT/hooks/scripts/plan-exit-mode-clear.sh"

passed=0
failed=0

# Test 1: Hook succeeds with already-empty mode file
TMPDIR=$(mktemp -d -t plan-guard-test-XXXXXX)
trap "rm -rf $TMPDIR" EXIT

mkdir -p "$TMPDIR/.purlin/runtime"
touch "$TMPDIR/.purlin/runtime/current_mode"

if PURLIN_PROJECT_ROOT="$TMPDIR" bash "$HOOK" > /dev/null 2>&1; then
    echo "hook succeeds with empty mode file"
    ((passed++))
else
    echo "FAIL: hook failed with empty mode file"
    ((failed++))
fi

# Test 2: Hook succeeds with missing mode file
rm -f "$TMPDIR/.purlin/runtime/current_mode"

if PURLIN_PROJECT_ROOT="$TMPDIR" bash "$HOOK" > /dev/null 2>&1; then
    echo "hook succeeds with missing mode file"
    ((passed++))
else
    echo "FAIL: hook failed with missing mode file"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
