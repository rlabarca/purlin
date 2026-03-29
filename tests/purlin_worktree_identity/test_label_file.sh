#!/usr/bin/env bash
# Test: Worktree label file is gitignored and identity.sh reads it.
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

passed=0
failed=0

# Check 1: .purlin_worktree_label is in .gitignore
gitignore="$PROJECT_ROOT/.gitignore"
if [[ -f "$gitignore" ]] && grep -q 'purlin_worktree_label' "$gitignore"; then
    echo "gitignore contains purlin_worktree_label"
    ((passed++))
else
    echo "FAIL: .purlin_worktree_label not found in .gitignore"
    ((failed++))
fi

# Check 2: identity.sh _purlin_detect_context reads .purlin_worktree_label
identity_sh="$PROJECT_ROOT/scripts/terminal/identity.sh"
if [[ -f "$identity_sh" ]] && grep -q 'purlin_worktree_label' "$identity_sh"; then
    echo "identity script reads label file"
    ((passed++))
else
    echo "FAIL: identity.sh does not reference .purlin_worktree_label"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
