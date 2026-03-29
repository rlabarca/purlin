#!/usr/bin/env bash
# Test: .purlin_worktree_label does not exist in non-worktree project root.
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

passed=0
failed=0

# Check: .purlin_worktree_label must NOT exist in the project root
# (it should only exist inside worktree directories)
if [[ ! -f "$PROJECT_ROOT/.purlin_worktree_label" ]]; then
    echo "no label file in project root"
    ((passed++))
else
    echo "FAIL: .purlin_worktree_label exists in non-worktree project root"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
