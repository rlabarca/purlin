#!/usr/bin/env bash
# Test: Command table in purlin_commands.md has all mode sections and core commands
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
CMD_REF="$PROJECT_ROOT/references/purlin_commands.md"

passed=0
failed=0

if [[ ! -f "$CMD_REF" ]]; then
    echo "FAIL: purlin_commands.md not found"
    exit 1
fi

content=$(cat "$CMD_REF")

# Check all mode sections exist
sections_ok=true
for section in "Common" "Engineer Mode" "PM Mode" "QA Mode"; do
    if ! echo "$content" | grep -q "$section"; then
        sections_ok=false
    fi
done
if $sections_ok; then
    echo "command table contains all mode sections"
    ((passed++))
else
    echo "FAIL: command table missing mode sections"
    ((failed++))
fi

# Check core commands listed
cmds_ok=true
for cmd in "purlin:status" "purlin:mode" "purlin:help"; do
    if ! echo "$content" | grep -q "$cmd"; then
        cmds_ok=false
    fi
done
if $cmds_ok; then
    echo "command table lists core commands"
    ((passed++))
else
    echo "FAIL: command table missing core commands"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
