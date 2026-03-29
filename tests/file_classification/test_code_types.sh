#!/usr/bin/env bash
# Test: DevOps and skill files are classified as CODE
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
FC="$PROJECT_ROOT/references/file_classification.md"

passed=0
failed=0

if [[ ! -f "$FC" ]]; then
    echo "FAIL: file_classification.md not found"
    exit 1
fi

# Extract the CODE section (from "## CODE" to next "##")
code_section=$(sed -n '/^## CODE/,/^## [A-Z]/p' "$FC" | head -n -1)

# Check DevOps files in CODE section
devops_ok=true
for pattern in "Makefile" "Dockerfile" ".github"; do
    if ! echo "$code_section" | grep -q "$pattern"; then
        devops_ok=false
    fi
done
if $devops_ok; then
    echo "devops files classified as CODE"
    ((passed++))
else
    echo "FAIL: DevOps files not all found in CODE section"
    ((failed++))
fi

# Check skill files in CODE section
if echo "$code_section" | grep -qi "skill"; then
    echo "skill files classified as CODE"
    ((passed++))
else
    echo "FAIL: skill files not found in CODE section"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
