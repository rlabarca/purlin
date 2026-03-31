#!/usr/bin/env bash
# Test: Sync tracker state management
# Verifies that sync-tracker.sh correctly tracks file writes in sync_state.json,
# mapping files to features using path-based type detection.
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

# === CODE file tracking (unclassified - no feature stem match) ===
fire_tracker "$TEST_DIR/scripts/mcp/config_engine.py"

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

# === Skill file maps to purlin_<name> if feature exists, no spurious keys ===
rm -f "$STATE_FILE"
mkdir -p "$TEST_DIR/skills/build"
fire_tracker "$TEST_DIR/skills/build/SKILL.md"

if [ -f "$STATE_FILE" ] && python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
# skills/build/ maps to purlin_build (if that feature exists) -- not 'build' or 'SKILL'
feats = data.get('features', {})
has_spurious = any('build' == k or 'SKILL' in k for k in feats)
sys.exit(0 if not has_spurious else 1)
" 2>/dev/null; then
    assert_pass "skill file does not create spurious feature entry"
else
    assert_fail "skill file does not create spurious feature entry"
fi

# === System folder _tombstones/ excluded from feature mapping ===
rm -f "$STATE_FILE"
mkdir -p "$TEST_DIR/features/_tombstones"
fire_tracker "$TEST_DIR/features/_tombstones/old_feature.md"

if python3 -c "
import json, sys
try:
    with open('$STATE_FILE') as f:
        data = json.load(f)
except FileNotFoundError:
    data = {'features': {}, 'unclassified_writes': []}
feats = data.get('features', {})
sys.exit(0 if 'old_feature' not in feats else 1)
" 2>/dev/null; then
    assert_pass "_tombstones/ file excluded from feature mapping"
else
    assert_fail "_tombstones/ file excluded from feature mapping"
fi

# === System folder _invariants/ excluded from feature mapping ===
rm -f "$STATE_FILE"
mkdir -p "$TEST_DIR/features/_invariants"
fire_tracker "$TEST_DIR/features/_invariants/i_arch_api.md"

if python3 -c "
import json, sys
try:
    with open('$STATE_FILE') as f:
        data = json.load(f)
except FileNotFoundError:
    data = {'features': {}, 'unclassified_writes': []}
feats = data.get('features', {})
sys.exit(0 if 'i_arch_api' not in feats else 1)
" 2>/dev/null; then
    assert_pass "_invariants/ file excluded from feature mapping"
else
    assert_fail "_invariants/ file excluded from feature mapping"
fi

# === Discoveries file maps to feature with qa_changed ===
rm -f "$STATE_FILE"
fire_tracker "$TEST_DIR/features/skills_engineer/purlin_build.discoveries.md"

if [ -f "$STATE_FILE" ] && python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
feat = data.get('features', {}).get('purlin_build', {})
sys.exit(0 if feat.get('qa_changed') else 1)
" 2>/dev/null; then
    assert_pass "discoveries file maps to feature with qa_changed"
else
    assert_fail "discoveries file maps to feature with qa_changed"
fi

# === .claude/ directory skipped by tracker ===
rm -f "$STATE_FILE"
mkdir -p "$TEST_DIR/.claude"
fire_tracker "$TEST_DIR/.claude/settings.json"

if [ ! -f "$STATE_FILE" ] || python3 -c "
import json, sys
with open('$STATE_FILE') as f:
    data = json.load(f)
feats = data.get('features', {})
uw = data.get('unclassified_writes', [])
sys.exit(0 if not feats and not uw else 1)
" 2>/dev/null; then
    assert_pass ".claude/ directory skipped by tracker"
else
    assert_fail ".claude/ directory skipped by tracker"
fi

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
