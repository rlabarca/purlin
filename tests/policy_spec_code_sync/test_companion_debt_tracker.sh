#!/usr/bin/env bash
# Test: Companion debt tracker hook — mechanical enforcement
# Verifies that companion-debt-tracker.sh correctly tracks debt when
# CODE files change and clears debt when .impl.md files change.
#
# Assigned to: policy_spec_code_sync (Gates 1-4)
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
HOOK_SCRIPT="$PLUGIN_ROOT/hooks/scripts/companion-debt-tracker.sh"

passed=0
failed=0
total=0

# Create isolated test environment
TEST_DIR=$(mktemp -d)
export PURLIN_PROJECT_ROOT="$TEST_DIR"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

mkdir -p "$TEST_DIR/.purlin/runtime"
mkdir -p "$TEST_DIR/features/framework_core"
mkdir -p "$TEST_DIR/tests/webhook_delivery"
mkdir -p "$TEST_DIR/tests/rate_limiting"
mkdir -p "$TEST_DIR/src"

# Create fake feature specs so stem resolution works
touch "$TEST_DIR/features/framework_core/webhook_delivery.md"
touch "$TEST_DIR/features/framework_core/rate_limiting.md"

DEBT_FILE="$TEST_DIR/.purlin/runtime/companion_debt.json"

send_file_change() {
    local file_path="$1"
    echo "{\"file_path\": \"$TEST_DIR/$file_path\"}" | bash "$HOOK_SCRIPT" 2>/dev/null
}

get_debt() {
    if [ -f "$DEBT_FILE" ]; then
        cat "$DEBT_FILE"
    else
        echo "{}"
    fi
}

has_debt_for() {
    local stem="$1"
    python3 -c "
import json, sys
try:
    with open('$DEBT_FILE') as f:
        debt = json.load(f)
    sys.exit(0 if '$stem' in debt else 1)
except Exception:
    sys.exit(1)
"
}

assert_pass() {
    local desc="$1"
    ((total++))
    if "$@" >/dev/null 2>&1; then
        # Re-shift past desc
        true
    fi
    # Actually run the test properly:
    true
}

# Better test helpers
assert_debt_exists() {
    local desc="$1" stem="$2"
    ((total++))
    if has_debt_for "$stem"; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (no debt found for $stem)"
        ((failed++))
    fi
}

assert_no_debt() {
    local desc="$1" stem="$2"
    ((total++))
    if has_debt_for "$stem"; then
        echo "FAIL: $desc (debt still exists for $stem)"
        ((failed++))
    else
        echo "PASS: $desc"
        ((passed++))
    fi
}

assert_debt_file_empty() {
    local desc="$1"
    ((total++))
    local content
    content=$(get_debt)
    if [ "$content" = "{}" ] || [ ! -f "$DEBT_FILE" ]; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (debt file not empty: $content)"
        ((failed++))
    fi
}

assert_debt_contains_file() {
    local desc="$1" stem="$2" file_pattern="$3"
    ((total++))
    if python3 -c "
import json, sys
with open('$DEBT_FILE') as f:
    debt = json.load(f)
entry = debt.get('$stem', {})
files = entry.get('files', [])
sys.exit(0 if any('$file_pattern' in f for f in files) else 1)
" 2>/dev/null; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (file pattern '$file_pattern' not in debt for $stem)"
        ((failed++))
    fi
}

# ===== Test: Code file change creates debt =====
send_file_change "tests/webhook_delivery/test_retry.py"
assert_debt_exists "code file change creates debt" "webhook_delivery"

# ===== Test: Debt records the changed file path =====
assert_debt_contains_file "debt records changed file path" "webhook_delivery" "test_retry.py"

# ===== Test: Second code file adds to existing debt =====
send_file_change "tests/webhook_delivery/test_batch.py"
assert_debt_contains_file "second code file adds to debt" "webhook_delivery" "test_batch.py"

# ===== Test: Companion file change clears debt =====
send_file_change "features/framework_core/webhook_delivery.impl.md"
assert_no_debt "companion file change clears debt" "webhook_delivery"

# ===== Test: Multiple features tracked independently =====
send_file_change "tests/webhook_delivery/test_retry.py"
send_file_change "tests/rate_limiting/test_throttle.py"
assert_debt_exists "multiple features: webhook has debt" "webhook_delivery"
assert_debt_exists "multiple features: rate_limiting has debt" "rate_limiting"

# ===== Test: Clearing one feature doesn't affect another =====
send_file_change "features/framework_core/webhook_delivery.impl.md"
assert_no_debt "clearing webhook doesn't affect rate_limiting" "webhook_delivery"
assert_debt_exists "rate_limiting still has debt after webhook cleared" "rate_limiting"

# ===== Test: Feature spec changes do NOT create debt =====
# Clear all debt first
rm -f "$DEBT_FILE"
send_file_change "features/framework_core/webhook_delivery.md"
assert_debt_file_empty "feature spec change does not create debt"

# ===== Test: Discovery sidecar changes do NOT create debt =====
rm -f "$DEBT_FILE"
send_file_change "features/framework_core/webhook_delivery.discoveries.md"
assert_debt_file_empty "discovery sidecar change does not create debt"

# ===== Test: Purlin internal files do NOT create debt =====
rm -f "$DEBT_FILE"
send_file_change ".purlin/config.json"
assert_debt_file_empty "purlin internal file does not create debt"

# ===== Test: .claude internal files do NOT create debt =====
rm -f "$DEBT_FILE"
send_file_change ".claude/settings.json"
assert_debt_file_empty "claude internal file does not create debt"

# ===== Test: Debt file has first_seen timestamp =====
rm -f "$DEBT_FILE"
send_file_change "tests/webhook_delivery/test_retry.py"
((total++))
if python3 -c "
import json, sys
with open('$DEBT_FILE') as f:
    debt = json.load(f)
entry = debt.get('webhook_delivery', {})
ts = entry.get('first_seen', '')
sys.exit(0 if ts and 'T' in ts and 'Z' in ts else 1)
" 2>/dev/null; then
    echo "PASS: debt entry has ISO 8601 first_seen timestamp"
    ((passed++))
else
    echo "FAIL: debt entry missing or malformed first_seen timestamp"
    ((failed++))
fi

# ===== Test: Code file without matching feature spec is ignored =====
rm -f "$DEBT_FILE"
send_file_change "tests/nonexistent_feature/test_foo.py"
assert_debt_file_empty "code file without matching feature spec creates no debt"

# ===== Test: Regression JSON changes do NOT create debt =====
rm -f "$DEBT_FILE"
send_file_change "tests/qa/scenarios/webhook_delivery.json"
assert_debt_file_empty "regression JSON change does not create debt"

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
