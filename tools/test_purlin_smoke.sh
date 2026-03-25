#!/bin/bash
# test_purlin_smoke.sh -- Unit tests for tools/smoke/smoke.py
# Covers the 7 unit test scenarios from features/purlin_smoke_testing.md Section 3.
#
# Produces tests/purlin_smoke_testing/tests.json
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
SCENARIOS=()
ERRORS=""

###############################################################################
# Helpers
###############################################################################
log_pass() { PASS=$((PASS + 1)); SCENARIOS+=("$1"); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); SCENARIOS+=("$1"); ERRORS="$ERRORS\n  FAIL: $1 — $2"; echo "  FAIL: $1 — $2"; }

SMOKE_PY="$PROJECT_ROOT/tools/smoke/smoke.py"

cleanup_fixture() {
    if [ -n "${FIXTURE_DIR:-}" ] && [ -d "$FIXTURE_DIR" ]; then
        rm -rf "$FIXTURE_DIR"
    fi
}

# Run smoke.py against a fixture. Usage: run_smoke <fixture_root> <cmd> [args...]
# Sets SMOKE_OUTPUT.
run_smoke() {
    local fixture_root="$1"
    shift
    SMOKE_OUTPUT=$(PURLIN_PROJECT_ROOT="$fixture_root" python3 "$SMOKE_PY" "$@" 2>&1) || true
}

# Extract JSON value from SMOKE_OUTPUT
json_get() {
    echo "$SMOKE_OUTPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except:
    print('JSON_PARSE_ERROR')
    sys.exit(0)
path = '''$1'''
try:
    val = eval('d' + path)
    if val is None:
        print('null')
    elif isinstance(val, bool):
        print('true' if val else 'false')
    elif isinstance(val, (list, dict)):
        print(json.dumps(val))
    else:
        print(val)
except Exception as e:
    print('EVAL_ERROR: ' + str(e))
" 2>/dev/null
}

###############################################################################
# Fixtures
###############################################################################

# Create a fixture with QA_OVERRIDES.md that has an existing tier table
setup_fixture_with_table() {
    FIXTURE_DIR="$(mktemp -d)"
    mkdir -p "$FIXTURE_DIR/.purlin"
    mkdir -p "$FIXTURE_DIR/.purlin/cache"
    mkdir -p "$FIXTURE_DIR/features"
    mkdir -p "$FIXTURE_DIR/tests/qa/scenarios"

    cat > "$FIXTURE_DIR/.purlin/QA_OVERRIDES.md" << 'EOF'
# QA Overrides

## Test Priority Tiers

| Feature | Tier |
|---------|------|
| project_init | smoke |
| config_layering | smoke |

## Other Section

Other content.
EOF

    # Create a dependency graph with fan-out features
    cat > "$FIXTURE_DIR/.purlin/cache/dependency_graph.json" << 'EOF'
{
    "cycles": [],
    "features": [
        {"file": "features/project_init.md", "category": "Install, Update & Scripts", "label": "Project Init", "prerequisites": []},
        {"file": "features/config_layering.md", "category": "Configuration", "label": "Config Layering", "prerequisites": []},
        {"file": "features/agent_launchers_common.md", "category": "Install, Update & Scripts", "label": "Agent Launchers", "prerequisites": []},
        {"file": "features/feature_a.md", "category": "General", "label": "Feature A", "prerequisites": ["agent_launchers_common.md"]},
        {"file": "features/feature_b.md", "category": "General", "label": "Feature B", "prerequisites": ["agent_launchers_common.md"]},
        {"file": "features/feature_c.md", "category": "General", "label": "Feature C", "prerequisites": ["agent_launchers_common.md"]},
        {"file": "features/feature_d.md", "category": "General", "label": "Feature D", "prerequisites": ["agent_launchers_common.md"]},
        {"file": "features/cdd_status_monitor.md", "category": "Coordination & Lifecycle", "label": "CDD Status", "prerequisites": []},
        {"file": "features/critic_tool.md", "category": "General", "label": "Critic Tool", "prerequisites": []}
    ],
    "orphans": [],
    "generated_at": "2026-03-25T00:00:00Z"
}
EOF

    # Create scan data
    cat > "$FIXTURE_DIR/.purlin/cache/scan.json" << 'EOF'
{
    "features": [
        {"name": "project_init", "test_status": "PASS"},
        {"name": "config_layering", "test_status": "PASS"},
        {"name": "agent_launchers_common", "test_status": "PASS"},
        {"name": "feature_a", "test_status": null},
        {"name": "feature_b", "test_status": null},
        {"name": "feature_c", "test_status": "PASS"},
        {"name": "feature_d", "test_status": null},
        {"name": "cdd_status_monitor", "test_status": "PASS"},
        {"name": "critic_tool", "test_status": "PASS"}
    ]
}
EOF
}

# Create a fixture with overrides but NO tier table
setup_fixture_no_table() {
    FIXTURE_DIR="$(mktemp -d)"
    mkdir -p "$FIXTURE_DIR/.purlin"
    mkdir -p "$FIXTURE_DIR/features"

    cat > "$FIXTURE_DIR/.purlin/PURLIN_OVERRIDES.md" << 'EOF'
# Purlin Overrides

## General (all modes)

Some general content.
EOF
}

echo "=== Purlin Smoke Testing Tests ==="
echo ""

###############################################################################
# Scenario 1: Promote feature to smoke tier
###############################################################################
echo "--- Scenario 1: Promote feature to smoke tier ---"
setup_fixture_with_table

run_smoke "$FIXTURE_DIR" add cdd_status_monitor

action=$(json_get "['action']")
# Verify the feature was added to the table
tiers_after=$(PURLIN_PROJECT_ROOT="$FIXTURE_DIR" python3 "$SMOKE_PY" read-tiers 2>/dev/null)
has_feature=$(echo "$tiers_after" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('true' if d.get('cdd_status_monitor') == 'smoke' else 'false')
" 2>/dev/null)

if [ "$action" = "added" ] && [ "$has_feature" = "true" ]; then
    log_pass "Promote feature to smoke tier"
else
    log_fail "Promote feature to smoke tier" "action=$action has_feature=$has_feature"
fi
cleanup_fixture

###############################################################################
# Scenario 2: Create tier table when missing
###############################################################################
echo "--- Scenario 2: Create tier table when missing ---"
setup_fixture_no_table

run_smoke "$FIXTURE_DIR" add project_init

action=$(json_get "['action']")
# Verify file has the table now
has_table=$(grep -c "## Test Priority Tiers" "$FIXTURE_DIR/.purlin/PURLIN_OVERRIDES.md" 2>/dev/null || true)
has_row=$(grep -c "project_init" "$FIXTURE_DIR/.purlin/PURLIN_OVERRIDES.md" 2>/dev/null || true)

if [ "$action" = "created_table" ] && [ "$has_table" -ge 1 ] && [ "$has_row" -ge 1 ]; then
    log_pass "Create tier table when missing"
else
    log_fail "Create tier table when missing" "action=$action table=$has_table row=$has_row"
fi
cleanup_fixture

###############################################################################
# Scenario 3: Offer simplified smoke regression
###############################################################################
echo "--- Scenario 3: Offer simplified smoke regression ---"
setup_fixture_with_table

# Use Python directly to call create_smoke_regression
SMOKE_FILE=$(PURLIN_PROJECT_ROOT="$FIXTURE_DIR" python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT/tools/smoke')
from smoke import create_smoke_regression
result = create_smoke_regression(
    '$FIXTURE_DIR',
    'cdd_status_monitor',
    [
        {'name': 'critical_path_check', 'description': 'Verify monitor starts and reports status'},
        {'name': 'event_detection', 'description': 'Verify monitor detects file changes'}
    ]
)
import json
print(json.dumps(result))
" 2>/dev/null)

# Verify the file was created
smoke_json_path="$FIXTURE_DIR/tests/qa/scenarios/cdd_status_monitor_smoke.json"
if [ -f "$smoke_json_path" ]; then
    has_tier=$(python3 -c "
import json
with open('$smoke_json_path') as f:
    d = json.load(f)
print('true' if d.get('tier') == 'smoke' else 'false')
" 2>/dev/null)
    scenario_count=$(python3 -c "
import json
with open('$smoke_json_path') as f:
    d = json.load(f)
print(len(d.get('scenarios', [])))
" 2>/dev/null)
    has_smoke_of=$(python3 -c "
import json
with open('$smoke_json_path') as f:
    d = json.load(f)
print('true' if 'smoke_of' in d else 'false')
" 2>/dev/null)

    if [ "$has_tier" = "true" ] && [ "$scenario_count" -le 3 ] && [ "$has_smoke_of" = "true" ]; then
        log_pass "Offer simplified smoke regression"
    else
        log_fail "Offer simplified smoke regression" "tier=$has_tier count=$scenario_count smoke_of=$has_smoke_of"
    fi
else
    log_fail "Offer simplified smoke regression" "smoke JSON file not created"
fi
cleanup_fixture

###############################################################################
# Scenario 4: Smoke suggestion identifies high-fan-out features
###############################################################################
echo "--- Scenario 4: Smoke suggestion identifies high-fan-out features ---"
setup_fixture_with_table

run_smoke "$FIXTURE_DIR" suggest

# agent_launchers_common has 4 dependents (feature_a through feature_d)
# and is not in the smoke tier table → should appear in suggestions
has_launchers=$(echo "$SMOKE_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
found = any(s['feature'] == 'agent_launchers_common' for s in d)
print('true' if found else 'false')
" 2>/dev/null)

# Verify the reason mentions prerequisites
launcher_reasons=$(echo "$SMOKE_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for s in d:
    if s['feature'] == 'agent_launchers_common':
        print('; '.join(s['reasons']))
        break
" 2>/dev/null)

if [ "$has_launchers" = "true" ] && echo "$launcher_reasons" | grep -qi "prerequisite"; then
    log_pass "Smoke suggestion identifies high-fan-out features"
else
    log_fail "Smoke suggestion identifies high-fan-out features" "found=$has_launchers reasons=$launcher_reasons"
fi
cleanup_fixture

###############################################################################
# Scenario 5: Smoke suggestion skips already-classified features
###############################################################################
echo "--- Scenario 5: Smoke suggestion skips already-classified features ---"
setup_fixture_with_table

run_smoke "$FIXTURE_DIR" suggest

# project_init is already in the tier table as smoke → should NOT appear
no_project_init=$(echo "$SMOKE_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
found = any(s['feature'] == 'project_init' for s in d)
print('true' if not found else 'false')
" 2>/dev/null)

if [ "$no_project_init" = "true" ]; then
    log_pass "Smoke suggestion skips already-classified features"
else
    log_fail "Smoke suggestion skips already-classified features" "project_init was suggested despite being in tier table"
fi
cleanup_fixture

###############################################################################
# Scenario 6: Verify smoke gate runs smoke regressions first
###############################################################################
echo "--- Scenario 6: Verify smoke gate runs smoke regressions first ---"
setup_fixture_with_table

# Create a _smoke.json regression for critic_tool
mkdir -p "$FIXTURE_DIR/tests/qa/scenarios"
cat > "$FIXTURE_DIR/tests/qa/scenarios/critic_tool_smoke.json" << 'EOF'
{
    "feature": "critic_tool",
    "frequency": "per-feature",
    "tier": "smoke",
    "smoke_of": "critic_tool.json",
    "scenarios": [{"name": "basic_check", "description": "Verify critic runs"}]
}
EOF

# Call order_verification with critic_tool and feature_a
ORDER_OUTPUT=$(PURLIN_PROJECT_ROOT="$FIXTURE_DIR" python3 -c "
import sys, json
sys.path.insert(0, '$PROJECT_ROOT/tools/smoke')
from smoke import order_verification
result = order_verification('$FIXTURE_DIR', ['critic_tool', 'feature_a', 'project_init'])
print(json.dumps(result))
" 2>/dev/null)

# smoke_regressions should include critic_tool_smoke.json
has_smoke_reg=$(echo "$ORDER_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
regs = d.get('smoke_regressions', [])
found = any(r['feature'] == 'critic_tool' for r in regs)
print('true' if found else 'false')
" 2>/dev/null)

# project_init should be in smoke_features (it's in the tier table)
has_smoke_feature=$(echo "$ORDER_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('true' if 'project_init' in d.get('smoke_features', []) else 'false')
" 2>/dev/null)

# feature_a should be in standard_features (not smoke)
has_standard=$(echo "$ORDER_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('true' if 'feature_a' in d.get('standard_features', []) else 'false')
" 2>/dev/null)

if [ "$has_smoke_reg" = "true" ] && [ "$has_smoke_feature" = "true" ] && [ "$has_standard" = "true" ]; then
    log_pass "Verify smoke gate runs smoke regressions first"
else
    log_fail "Verify smoke gate runs smoke regressions first" \
        "reg=$has_smoke_reg smoke=$has_smoke_feature standard=$has_standard"
fi
cleanup_fixture

###############################################################################
# Scenario 7: Verify smoke failure blocks further verification
###############################################################################
echo "--- Scenario 7: Verify smoke failure blocks further verification ---"

# Call check_smoke_gate with a failing result
GATE_OUTPUT=$(python3 -c "
import sys, json
sys.path.insert(0, '$PROJECT_ROOT/tools/smoke')
from smoke import check_smoke_gate
result = check_smoke_gate([
    {'feature': 'project_init', 'status': 'PASS'},
    {'feature': 'config_layering', 'status': 'FAIL'},
])
print(json.dumps(result))
" 2>/dev/null)

gate_passed=$(echo "$GATE_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('true' if d['passed'] else 'false')
" 2>/dev/null)

has_failure_msg=$(echo "$GATE_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('true' if 'SMOKE FAILURE' in d.get('message', '') else 'false')
" 2>/dev/null)

has_blocked_feature=$(echo "$GATE_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('true' if 'config_layering' in d.get('failures', []) else 'false')
" 2>/dev/null)

if [ "$gate_passed" = "false" ] && [ "$has_failure_msg" = "true" ] && [ "$has_blocked_feature" = "true" ]; then
    log_pass "Verify smoke failure blocks further verification"
else
    log_fail "Verify smoke failure blocks further verification" \
        "passed=$gate_passed msg=$has_failure_msg blocked=$has_blocked_feature"
fi

###############################################################################
# Results
###############################################################################
echo ""
echo "=== Results ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo "  Total: $((PASS + FAIL))"

if [ -n "$ERRORS" ]; then
    echo ""
    echo "Failures:"
    echo -e "$ERRORS"
fi

# Write tests.json
FEATURE_NAME="purlin_smoke_testing"
RESULT_DIR="$TESTS_DIR/$FEATURE_NAME"
mkdir -p "$RESULT_DIR"

STATUS="PASS"
[ "$FAIL" -gt 0 ] && STATUS="FAIL"

SCENARIO_JSON="["
for i in "${!SCENARIOS[@]}"; do
    [ "$i" -gt 0 ] && SCENARIO_JSON+=","
    SCENARIO_JSON+="\"${SCENARIOS[$i]}\""
done
SCENARIO_JSON+="]"

cat > "$RESULT_DIR/tests.json" << JSONEOF
{
  "feature": "$FEATURE_NAME",
  "status": "$STATUS",
  "passed": $PASS,
  "failed": $FAIL,
  "total": $((PASS + FAIL)),
  "test_file": "tools/test_purlin_smoke.sh",
  "scenarios": $SCENARIO_JSON,
  "ran_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
JSONEOF

echo ""
echo "Results written to tests/$FEATURE_NAME/tests.json"

exit $FAIL
