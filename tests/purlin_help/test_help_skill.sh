#!/usr/bin/env bash
# Test: Help skill exists and references purlin_commands.md
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
HELP_SKILL="$PROJECT_ROOT/skills/help/SKILL.md"

passed=0
failed=0

if [[ ! -f "$HELP_SKILL" ]]; then
    echo "FAIL: skills/help/SKILL.md not found"
    exit 1
fi

echo "help skill file exists"
((passed++))

content=$(cat "$HELP_SKILL")
if echo "$content" | grep -q "purlin_commands.md"; then
    echo "help skill references purlin_commands.md"
    ((passed++))
else
    echo "FAIL: help skill does not reference purlin_commands.md"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
