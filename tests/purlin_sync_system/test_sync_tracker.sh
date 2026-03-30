#!/usr/bin/env bash
# Test: Sync tracker state management
# Verifies that sync-tracker.sh correctly tracks file writes in sync_state.json,
# mapping files to features and classifying changes.
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
SYNC_TRACKER="$PLUGIN_ROOT/hooks/scripts/sync-tracker.sh"

passed=0
failed=0
total=0

# Create isolated test environment
TEST_DIR=$(mktemp -d)
export PURLIN_PROJECT_ROOT="$TEST_DIR"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

mkdir -p "$TEST_DIR/.purlin/runtime"
mkdir -p "$TEST_DIR/features/skills_engineer"
mkdir -p "$TEST_DIR/scripts/mcp"
mkdir -p "$TEST_DIR/src"

# Copy file_classification.json for fallback
if [ -f "$PLUGIN_ROOT/references/file_classification.json" ]; then
    mkdir -p "$TEST_DIR/references"
    cp "$PLUGIN_ROOT/references/file_classification.json" "$TEST_DIR/references/"
fi

STATE_FILE="$TEST_DIR/.purlin/runtime/sync_state.json"

# Simulate a FileChanged hook call
fire_tracker() {
    local file_path="$1"
    echo "{\"file_path\": \"$file_path\"}" | bash "$SYNC_TRACKER" 2>/dev/null
}

assert_pass() {
    local desc="$1"
    ((total++))
    echo "PASS: $desc"
    ((passed++))
}

assert_fail() {
    local desc="$1"
    ((total++))
    echo "FAIL: $desc"
    ((failed++))
}

# === CODE file tracking ===
fire_tracker "$TEST_DIR/scripts/mcp/config_engine.py"

# scripts/mcp/config_engine.py can't map to a feature stem, so it goes to unclassified
if [ -f "$STATE_FILE" ] && python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
uw = data.get('unclassified_writes', [])
sys.exit(0 if 'scripts/mcp/config_engine.py' in uw else 1)
" 2>/dev/null; then
    assert_pass "unclassified file tracked"
else
    assert_fail "unclassified file tracked"
fi

# Reset state
rm -f "$STATE_FILE"

# === Feature-mapped CODE file ===
mkdir -p "$TEST_DIR/tests/purlin_build"
fire_tracker "$TEST_DIR/tests/purlin_build/test_preflight.sh"

if [ -f "$STATE_FILE" ] && python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
feat = data.get('features', {}).get('purlin_build', {})
sys.exit(0 if 'tests/purlin_build/test_preflight.sh' in feat.get('test_files', []) else 1)
" 2>/dev/null; then
    assert_pass "code file tracked in sync_state"
else
    assert_fail "code file tracked in sync_state"
fi

# === SPEC file tracking ===
fire_tracker "$TEST_DIR/features/skills_engineer/purlin_build.md"

if python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
feat = data.get('features', {}).get('purlin_build', {})
sys.exit(0 if feat.get('spec_changed') else 1)
" 2>/dev/null; then
    assert_pass "spec change tracked in sync_state"
else
    assert_fail "spec change tracked in sync_state"
fi

# === IMPL file tracking ===
fire_tracker "$TEST_DIR/features/skills_engineer/purlin_build.impl.md"

if python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
feat = data.get('features', {}).get('purlin_build', {})
sys.exit(0 if feat.get('impl_changed') else 1)
" 2>/dev/null; then
    assert_pass "impl change tracked in sync_state"
else
    assert_fail "impl change tracked in sync_state"
fi

# === .purlin/ files are skipped ===
rm -f "$STATE_FILE"
fire_tracker "$TEST_DIR/.purlin/config.json"

if [ ! -f "$STATE_FILE" ]; then
    assert_pass "purlin runtime files skipped"
else
    # File may exist but should be empty/default
    if python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
feats = data.get('features', {})
uw = data.get('unclassified_writes', [])
sys.exit(0 if not feats and not uw else 1)
" 2>/dev/null; then
        assert_pass "purlin runtime files skipped"
    else
        assert_fail "purlin runtime files skipped"
    fi
fi

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
