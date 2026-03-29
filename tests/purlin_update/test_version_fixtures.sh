#!/usr/bin/env bash
# tests/purlin_update/test_version_fixtures.sh
#
# Regression test: checks out each purlin_update fixture from the fixture repo
# and validates version detection + migration path computation.
#
# Usage:
#   bash tests/purlin_update/test_version_fixtures.sh [--write-results]
#
# Requires: fixture repo initialized with main/purlin_update/* tags
# (run dev/setup_version_fixtures.sh first)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURE_REPO="$PROJECT_ROOT/.purlin/runtime/fixture-repo"
DETECTOR="$PROJECT_ROOT/scripts/migration/version_detector.py"
REGISTRY="$PROJECT_ROOT/scripts/migration/migration_registry.py"
CHECKOUT_DIR=""
PASSED=0
FAILED=0
TOTAL=0

cleanup() {
    [[ -n "$CHECKOUT_DIR" && -d "$CHECKOUT_DIR" ]] && rm -rf "$CHECKOUT_DIR"
}
trap cleanup EXIT

# Check prerequisites
if [[ ! -d "$FIXTURE_REPO" ]]; then
    echo "FAIL: Fixture repo not found at $FIXTURE_REPO"
    echo "Run: dev/setup_version_fixtures.sh first"
    exit 1
fi

if ! git -C "$FIXTURE_REPO" tag -l 'main/purlin_update/*' | grep -q .; then
    echo "FAIL: No purlin_update fixture tags found"
    echo "Run: dev/setup_version_fixtures.sh first"
    exit 1
fi

CHECKOUT_DIR="$(mktemp -d -t purlin-update-test-XXXXXX)"

# --- Test helpers ---

checkout_fixture() {
    local tag="$1"
    local slug="${tag//\//_}"
    local dir="$CHECKOUT_DIR/$slug"
    rm -rf "$dir"
    git clone -q "$FIXTURE_REPO" "$dir" 2>/dev/null
    git -C "$dir" checkout -q "$tag" 2>/dev/null
    echo "$dir"
}

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    TOTAL=$((TOTAL + 1))
    if [[ "$expected" == "$actual" ]]; then
        echo "  ✓ $label"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ $label (expected: $expected, got: $actual)"
        FAILED=$((FAILED + 1))
    fi
}

assert_contains() {
    local label="$1" expected="$2" actual="$3"
    TOTAL=$((TOTAL + 1))
    if echo "$actual" | grep -q "$expected"; then
        echo "  ✓ $label"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ $label (expected to contain: $expected)"
        FAILED=$((FAILED + 1))
    fi
}

detect() {
    local dir="$1"
    python3 "$DETECTOR" --project-root "$dir" 2>/dev/null
}

field() {
    local json="$1" key="$2"
    echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); v=d.get('$key'); print(v if v is not None else 'null')"
}

registry_dry_run() {
    local dir="$1"
    python3 "$REGISTRY" --project-root "$dir" --dry-run 2>/dev/null || true
}

count_steps() {
    local output="$1"
    echo "$output" | grep -c "^Step " || echo "0"
}

# ==================================================================
# Detection tests
# ==================================================================
echo "━━━ Version Detection ━━━━━━━━━━━━━━━━━"

echo ""
echo "submodule-v0-7-x:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-7-x")
fp=$(detect "$dir")
assert_eq "model=submodule" "submodule" "$(field "$fp" model)"
assert_eq "era=pre-unified-legacy" "pre-unified-legacy" "$(field "$fp" era)"
assert_eq "version_hint=v0.7.x" "v0.7.x" "$(field "$fp" version_hint)"
assert_eq "migration_version=null" "null" "$(field "$fp" migration_version)"

echo ""
echo "submodule-v0-8-0-v0-8-3:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-8-0-v0-8-3")
fp=$(detect "$dir")
assert_eq "model=submodule" "submodule" "$(field "$fp" model)"
assert_eq "era=pre-unified-modern" "pre-unified-modern" "$(field "$fp" era)"
assert_eq "version_hint=v0.8.0-v0.8.3" "v0.8.0-v0.8.3" "$(field "$fp" version_hint)"

echo ""
echo "submodule-v0-8-4:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-8-4")
fp=$(detect "$dir")
assert_eq "model=submodule" "submodule" "$(field "$fp" model)"
assert_eq "era=pre-unified-with-pm" "pre-unified-with-pm" "$(field "$fp" era)"
assert_eq "version_hint=v0.8.4" "v0.8.4" "$(field "$fp" version_hint)"

echo ""
echo "submodule-v0-8-4-partial:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-8-4-partial")
fp=$(detect "$dir")
assert_eq "model=submodule" "submodule" "$(field "$fp" model)"
assert_eq "era=unified-partial" "unified-partial" "$(field "$fp" era)"
assert_eq "migration_version=null" "null" "$(field "$fp" migration_version)"

echo ""
echo "submodule-v0-8-5:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-8-5")
fp=$(detect "$dir")
assert_eq "model=submodule" "submodule" "$(field "$fp" model)"
assert_eq "era=unified" "unified" "$(field "$fp" era)"
assert_eq "migration_version=1" "1" "$(field "$fp" migration_version)"

echo ""
echo "plugin-v0-9-0:"
dir=$(checkout_fixture "main/purlin_update/plugin-v0-9-0")
fp=$(detect "$dir")
assert_eq "model=plugin" "plugin" "$(field "$fp" model)"
assert_eq "era=plugin" "plugin" "$(field "$fp" era)"
assert_eq "migration_version=2" "2" "$(field "$fp" migration_version)"

echo ""
echo "fresh-project:"
dir=$(checkout_fixture "main/purlin_update/fresh-project")
fp=$(detect "$dir")
assert_eq "model=fresh" "fresh" "$(field "$fp" model)"
assert_eq "migration_version=null" "null" "$(field "$fp" migration_version)"

# ==================================================================
# Migration path tests
# ==================================================================
echo ""
echo "━━━ Migration Paths ━━━━━━━━━━━━━━━━━━━"

echo ""
echo "v0.7.x path:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-7-x")
output=$(registry_dry_run "$dir")
assert_eq "3 steps" "3" "$(count_steps "$output")"
assert_contains "includes Unified Agent Model" "Unified Agent Model" "$output"
assert_contains "includes Submodule to Plugin" "Submodule to Plugin" "$output"
assert_contains "includes Plugin Refresh" "Plugin Refresh" "$output"

echo ""
echo "v0.8.0-v0.8.3 path:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-8-0-v0-8-3")
output=$(registry_dry_run "$dir")
assert_eq "3 steps" "3" "$(count_steps "$output")"

echo ""
echo "v0.8.4 path:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-8-4")
output=$(registry_dry_run "$dir")
assert_eq "3 steps" "3" "$(count_steps "$output")"

echo ""
echo "v0.8.4-partial path:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-8-4-partial")
output=$(registry_dry_run "$dir")
assert_eq "3 steps" "3" "$(count_steps "$output")"
assert_contains "repair in plan" "Repair\|repair" "$output"

echo ""
echo "v0.8.5 path:"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-8-5")
output=$(registry_dry_run "$dir")
assert_eq "2 steps" "2" "$(count_steps "$output")"
assert_contains "starts at Submodule to Plugin" "Submodule to Plugin" "$output"

echo ""
echo "plugin-v0.9.0 path:"
dir=$(checkout_fixture "main/purlin_update/plugin-v0-9-0")
output=$(registry_dry_run "$dir")
assert_eq "1 step" "1" "$(count_steps "$output")"
assert_contains "only Plugin Refresh" "Plugin Refresh" "$output"

echo ""
echo "fresh-project path:"
dir=$(checkout_fixture "main/purlin_update/fresh-project")
output=$(registry_dry_run "$dir")
assert_contains "needs init" "Fresh project\|purlin:init" "$output"

# ==================================================================
# Step 1 execution test (safe — only modifies config in temp dir)
# ==================================================================
echo ""
echo "━━━ Step 1 Execution ━━━━━━━━━━━━━━━━━━"

echo ""
echo "v0.7.x step 1 (consolidation):"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-7-x")
python3 -c "
import sys, json, os
sys.path.insert(0, '$PROJECT_ROOT/scripts/migration')
from version_detector import detect_version
from migration_registry import Step1UnifiedAgentModel

fp = detect_version('$dir')
step = Step1UnifiedAgentModel()
ok, reason = step.preconditions(fp, '$dir')
assert ok, f'preconditions failed: {reason}'
result = step.execute(fp, '$dir')
assert result, 'execution failed'

config = json.load(open(os.path.join('$dir', '.purlin', 'config.json')))
assert 'purlin' in config['agents'], 'agents.purlin missing'
assert 'architect' not in config['agents'], 'architect not removed'
assert config['_migration_version'] == 1, f'wrong version: {config[\"_migration_version\"]}'
print('OK')
" 2>&1
rc=$?
TOTAL=$((TOTAL + 1))
if [[ $rc -eq 0 ]]; then
    echo "  ✓ consolidates 4 roles into agents.purlin, stamps mv=1"
    PASSED=$((PASSED + 1))
else
    echo "  ✗ step 1 execution failed"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "v0.8.4-partial step 1 (repair):"
dir=$(checkout_fixture "main/purlin_update/submodule-v0-8-4-partial")
python3 -c "
import sys, json, os
sys.path.insert(0, '$PROJECT_ROOT/scripts/migration')
from version_detector import detect_version
from migration_registry import Step1UnifiedAgentModel

fp = detect_version('$dir')
step = Step1UnifiedAgentModel()
result = step.execute(fp, '$dir')
assert result

config = json.load(open(os.path.join('$dir', '.purlin', 'config.json')))
purlin = config['agents']['purlin']
assert 'find_work' in purlin, 'find_work not added'
assert 'auto_start' in purlin, 'auto_start not added'
assert 'builder' not in config['agents'], 'builder not removed'
print('OK')
" 2>&1
rc=$?
TOTAL=$((TOTAL + 1))
if [[ $rc -eq 0 ]]; then
    echo "  ✓ repairs partial migration, adds missing keys"
    PASSED=$((PASSED + 1))
else
    echo "  ✗ step 1 repair failed"
    FAILED=$((FAILED + 1))
fi

# ==================================================================
# Idempotency test
# ==================================================================
echo ""
echo "━━━ Idempotency ━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "Already-current project:"
dir=$(checkout_fixture "main/purlin_update/plugin-v0-9-0")
# Manually stamp mv=3 to simulate already-current
python3 -c "
import json, os
config_path = os.path.join('$dir', '.purlin', 'config.json')
config = json.load(open(config_path))
config['_migration_version'] = 3
with open(config_path, 'w') as f:
    json.dump(config, f, indent=4)
"
output=$(registry_dry_run "$dir")
assert_contains "already up to date" "Already up to date" "$output"

# ==================================================================
# Summary
# ==================================================================
echo ""
echo "━━━ $PASSED passed · $FAILED failed · $TOTAL total"

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
