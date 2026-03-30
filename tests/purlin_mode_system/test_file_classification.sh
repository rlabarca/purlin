#!/usr/bin/env bash
# Test: File classification logic
# Verifies that classify_file() in config_engine.py correctly
# categorizes files as CODE, SPEC, QA, or INVARIANT.
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
CONFIG_ENGINE="$PLUGIN_ROOT/scripts/mcp/config_engine.py"

passed=0
failed=0
total=0

classify() {
    python3 -c "
import sys, os
os.environ['PURLIN_PROJECT_ROOT'] = '$PROJECT_ROOT'
sys.path.insert(0, '$PLUGIN_ROOT/scripts/mcp')
from config_engine import classify_file
print(classify_file('$1'))
" 2>/dev/null
}

assert_class() {
    local desc="$1" expected="$2" filepath="$3"
    ((total++))
    local actual
    actual=$(classify "$filepath")
    if [ "$expected" = "$actual" ]; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (expected '$expected', got '$actual')"
        ((failed++))
    fi
}

# === INVARIANT files ===
assert_class "invariant file detected" "INVARIANT" "features/_invariants/i_external_api.md"
assert_class "invariant with nested path" "INVARIANT" "/abs/path/features/_invariants/i_schema.md"

# === QA files ===
assert_class "discovery sidecar is QA" "QA" "features/skills_qa/purlin_verify.discoveries.md"
assert_class "regression JSON is QA" "QA" "/project/tests/purlin_resume/regression.json"
assert_class "scenario file is QA" "QA" "/project/tests/qa/scenarios/purlin_resume.json"

# === SPEC files ===
assert_class "feature spec is SPEC" "SPEC" "features/skills_engineer/purlin_build.md"
assert_class "policy spec is SPEC" "SPEC" "features/policy/policy_branch_collab.md"
assert_class "framework spec is SPEC" "SPEC" "features/framework_core/purlin_mode_system.md"

# === CODE files (companion override) ===
assert_class "companion (.impl.md) is CODE" "CODE" "features/skills_engineer/purlin_build.impl.md"

# === CODE files (general) ===
assert_class "python source is CODE" "CODE" "scripts/mcp/config_engine.py"
assert_class "shell script is CODE" "CODE" "hooks/scripts/mode-guard.sh"
assert_class "agent definition is CODE" "CODE" "agents/purlin.md"
assert_class "skill file is CODE" "CODE" "skills/build/SKILL.md"
assert_class "test script is CODE" "CODE" "tests/purlin_mode_system/test_write_guard.sh"
assert_class "reference file is CODE" "CODE" "references/file_classification.json"
assert_class "template is CODE" "CODE" "templates/config.json"
assert_class "hook config is CODE" "CODE" "hooks/hooks.json"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
