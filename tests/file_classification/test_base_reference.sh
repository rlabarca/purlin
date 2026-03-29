#!/usr/bin/env bash
# Test: Agent definition references file_classification.md, no inline file lists
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
AGENT_DEF="$PROJECT_ROOT/agents/purlin.md"

passed=0
failed=0

if [[ ! -f "$AGENT_DEF" ]]; then
    echo "FAIL: agents/purlin.md not found"
    exit 1
fi

content=$(cat "$AGENT_DEF")

# Check that mode sections reference file_classification.md
ref_count=$(echo "$content" | grep -c "file_classification" || true)
if [[ $ref_count -ge 1 ]]; then
    echo "all modes reference file_classification.md"
    ((passed++))
else
    echo "FAIL: agents/purlin.md does not reference file_classification.md ($ref_count refs)"
    ((failed++))
fi

# Check no inline file pattern lists in mode definitions
# Mode definitions should NOT contain patterns like "*.py", "*.sh" in write-access lines
# They should delegate to file_classification.md instead
inline_patterns=$(echo "$content" | grep -cE '\*\.(py|sh|js|ts|go)\b.*write|write.*\*\.(py|sh|js|ts|go)\b' || true)
if [[ $inline_patterns -eq 0 ]]; then
    echo "no inline file pattern lists in mode definitions"
    ((passed++))
else
    echo "FAIL: found $inline_patterns inline file pattern lists in agent definition"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
