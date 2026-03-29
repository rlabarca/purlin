#!/usr/bin/env bash
# Test: Config engine persists boolean fields as JSON booleans, handles missing agent config
set -euo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
CONFIG_ENGINE="$PROJECT_ROOT/scripts/mcp/config_engine.py"

passed=0
failed=0

if [[ ! -f "$CONFIG_ENGINE" ]]; then
    echo "FAIL: config_engine.py not found"
    exit 1
fi

# Test 1: Boolean coercion — set find_work to string "true", verify JSON has boolean true
TMPDIR=$(mktemp -d -t config-test-XXXXXX)
trap "rm -rf $TMPDIR" EXIT

mkdir -p "$TMPDIR/.purlin"
echo '{"agents": {"purlin": {"model": "claude-opus-4-6"}}}' > "$TMPDIR/.purlin/config.local.json"

PURLIN_PROJECT_ROOT="$TMPDIR" python3 "$CONFIG_ENGINE" set_agent_config purlin find_work true 2>/dev/null

# Check the JSON file directly for boolean (not string)
bool_check=$(python3 -c "
import json
with open('$TMPDIR/.purlin/config.local.json') as f:
    config = json.load(f)
val = config['agents']['purlin']['find_work']
print('boolean' if isinstance(val, bool) and val is True else f'wrong:{type(val).__name__}={val}')
")

if [[ "$bool_check" == "boolean" ]]; then
    echo "boolean fields persist as JSON booleans"
    ((passed++))
else
    echo "FAIL: find_work is $bool_check instead of boolean true"
    ((failed++))
fi

# Test 2: Missing agents.purlin — role resolution should fall back to builder or return safe defaults
TMPDIR2=$(mktemp -d -t config-test-XXXXXX)
mkdir -p "$TMPDIR2/.purlin"
echo '{"agents": {"builder": {"model": "claude-sonnet-4-6", "effort": "high", "bypass_permissions": true, "find_work": true, "auto_start": false}}}' > "$TMPDIR2/.purlin/config.local.json"

role_output=$(PURLIN_PROJECT_ROOT="$TMPDIR2" python3 "$CONFIG_ENGINE" role purlin 2>/dev/null || true)

if echo "$role_output" | grep -q 'AGENT_MODEL='; then
    echo "missing agents.purlin returns safe defaults"
    ((passed++))
else
    echo "FAIL: role resolution with missing agents.purlin produced no output"
    ((failed++))
fi

# Test 3: Startup control values resolve correctly
TMPDIR3=$(mktemp -d -t config-test-XXXXXX)
mkdir -p "$TMPDIR3/.purlin"
echo '{"agents": {"purlin": {"model": "claude-opus-4-6", "effort": "high", "bypass_permissions": false, "find_work": false, "auto_start": false}}}' > "$TMPDIR3/.purlin/config.local.json"

role_output=$(PURLIN_PROJECT_ROOT="$TMPDIR3" python3 "$CONFIG_ENGINE" role purlin 2>/dev/null || true)

if echo "$role_output" | grep -q 'AGENT_FIND_WORK="false"' && echo "$role_output" | grep -q 'AGENT_AUTO_START="false"'; then
    echo "startup control values resolve correctly"
    ((passed++))
else
    echo "FAIL: startup control values not resolved correctly: $role_output"
    ((failed++))
fi

echo ""
echo "$passed passed, $failed failed"
exit "$failed"
