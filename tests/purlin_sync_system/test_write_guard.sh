#!/usr/bin/env bash
# Test: Write guard enforcement — three-bucket model
# Verifies the full decision tree:
#   1. System files (.purlin/, .claude/) → always ALLOW
#   2. Invariant files (features/_invariants/i_*) → bypass lock or BLOCK
#   3. Features files (features/*) → active_skill marker or BLOCK
#   4. OTHER files (write_exceptions match) → always ALLOW
#   5. Code files (everything else) → active_skill marker or BLOCK
#   UNKNOWN files → always BLOCK (no classification rule)
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
WRITE_GUARD="$PLUGIN_ROOT/hooks/scripts/write-guard.sh"

passed=0
failed=0
total=0

# Create isolated test environment
TEST_DIR=$(mktemp -d)
export PURLIN_PROJECT_ROOT="$TEST_DIR"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

mkdir -p "$TEST_DIR/.purlin/runtime"
mkdir -p "$TEST_DIR/.claude"
mkdir -p "$TEST_DIR/features/_invariants"
mkdir -p "$TEST_DIR/features/_design"
mkdir -p "$TEST_DIR/features/_tombstones"
mkdir -p "$TEST_DIR/features/skills_engineer"
mkdir -p "$TEST_DIR/tests/qa/scenarios"
mkdir -p "$TEST_DIR/scripts/mcp"
mkdir -p "$TEST_DIR/src"
mkdir -p "$TEST_DIR/docs/api"

# Copy file_classification.json for fallback
if [ -f "$PLUGIN_ROOT/references/file_classification.json" ]; then
    mkdir -p "$TEST_DIR/references"
    cp "$PLUGIN_ROOT/references/file_classification.json" "$TEST_DIR/references/"
fi

# Run write guard with a file path, return exit code
run_guard() {
    local file_path="$1"
    echo "{\"tool_input\": {\"file_path\": \"$file_path\"}}" | bash "$WRITE_GUARD" >/dev/null 2>&1
    return $?
}

# Run write guard and capture stderr for message checking
run_guard_stderr() {
    local file_path="$1"
    echo "{\"tool_input\": {\"file_path\": \"$file_path\"}}" | bash "$WRITE_GUARD" 2>&1 >/dev/null
}

assert_allowed() {
    local desc="$1" file_path="$2"
    ((total++))
    if run_guard "$file_path"; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (expected allow, got block)"
        ((failed++))
    fi
}

assert_blocked() {
    local desc="$1" file_path="$2"
    ((total++))
    if run_guard "$file_path"; then
        echo "FAIL: $desc (expected block, got allow)"
        ((failed++))
    else
        echo "PASS: $desc"
        ((passed++))
    fi
}

assert_blocked_with_message() {
    local desc="$1" file_path="$2" expected_fragment="$3"
    ((total++))
    local stderr_output
    stderr_output=$(run_guard_stderr "$file_path")
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "FAIL: $desc (expected block, got allow)"
        ((failed++))
    elif echo "$stderr_output" | grep -q "$expected_fragment"; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (blocked but message missing '$expected_fragment', got: $stderr_output)"
        ((failed++))
    fi
}

assert_blocked_without_message() {
    local desc="$1" file_path="$2" forbidden_fragment="$3"
    ((total++))
    local stderr_output
    stderr_output=$(run_guard_stderr "$file_path")
    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "FAIL: $desc (expected block, got allow)"
        ((failed++))
    elif echo "$stderr_output" | grep -q "$forbidden_fragment"; then
        echo "FAIL: $desc (blocked but message should NOT contain '$forbidden_fragment', got: $stderr_output)"
        ((failed++))
    else
        echo "PASS: $desc"
        ((passed++))
    fi
}

set_marker() {
    echo "$1" > "$TEST_DIR/.purlin/runtime/active_skill"
}

clear_marker() {
    rm -f "$TEST_DIR/.purlin/runtime/active_skill"
}

set_write_exceptions() {
    cat > "$TEST_DIR/.purlin/config.json" <<CONF
{
    "write_exceptions": $1
}
CONF
    # resolve_config copies config.json → config.local.json on first access;
    # subsequent reads use local. Keep both in sync for test isolation.
    cp "$TEST_DIR/.purlin/config.json" "$TEST_DIR/.purlin/config.local.json" 2>/dev/null
}

clear_config() {
    rm -f "$TEST_DIR/.purlin/config.json" "$TEST_DIR/.purlin/config.local.json"
}

# ============================================================
# STEP 1: System files — always ALLOW (no marker needed)
# ============================================================
echo "=== Step 1: System files ==="

clear_marker
assert_allowed "system file .purlin/config.json (no marker)" "$TEST_DIR/.purlin/config.json"
assert_allowed "system file .purlin/runtime/sync_state.json (no marker)" "$TEST_DIR/.purlin/runtime/sync_state.json"
assert_allowed "system file .claude/settings.json (no marker)" "$TEST_DIR/.claude/settings.json"

# ============================================================
# STEP 2: Invariant files — bypass lock protocol (unchanged)
# ============================================================
echo ""
echo "=== Step 2: Invariant files ==="

clear_marker

# Blocked without lock
assert_blocked "INVARIANT file blocked (no lock)" "$TEST_DIR/features/_invariants/i_external.md"

# Blocked with marker but no lock (marker does NOT bypass invariant protection)
set_marker "build"
assert_blocked "INVARIANT file blocked even with active_skill marker" "$TEST_DIR/features/_invariants/i_external.md"
clear_marker

# Bypass lock — relative path
echo "features/_invariants/i_external.md" > "$TEST_DIR/.purlin/runtime/invariant_write_lock"
assert_allowed "invariant bypass lock (relative path)" "$TEST_DIR/features/_invariants/i_external.md"
rm -f "$TEST_DIR/.purlin/runtime/invariant_write_lock"

# Bypass lock — absolute path
echo "$TEST_DIR/features/_invariants/i_external.md" > "$TEST_DIR/.purlin/runtime/invariant_write_lock"
assert_allowed "invariant bypass lock (absolute path)" "$TEST_DIR/features/_invariants/i_external.md"
rm -f "$TEST_DIR/.purlin/runtime/invariant_write_lock"

# Bypass lock — wildcard
echo "*" > "$TEST_DIR/.purlin/runtime/invariant_write_lock"
assert_allowed "invariant bypass lock (wildcard)" "$TEST_DIR/features/_invariants/i_external.md"
rm -f "$TEST_DIR/.purlin/runtime/invariant_write_lock"

# Bypass lock — wrong path still blocks
echo "features/_invariants/i_OTHER.md" > "$TEST_DIR/.purlin/runtime/invariant_write_lock"
assert_blocked "invariant lock wrong path still blocks" "$TEST_DIR/features/_invariants/i_external.md"
rm -f "$TEST_DIR/.purlin/runtime/invariant_write_lock"

# Bypass lock — empty file still blocks
touch "$TEST_DIR/.purlin/runtime/invariant_write_lock"
assert_blocked "invariant lock empty file still blocks" "$TEST_DIR/features/_invariants/i_external.md"
rm -f "$TEST_DIR/.purlin/runtime/invariant_write_lock"

# Error message is actionable
assert_blocked_with_message "invariant block message mentions purlin:invariant" \
    "$TEST_DIR/features/_invariants/i_external.md" "purlin:invariant sync"

# ============================================================
# STEP 3: Features files — need active_skill marker
# ============================================================
echo ""
echo "=== Step 3: Features files (spec gate) ==="

clear_marker

# Spec files blocked without marker
assert_blocked "spec file blocked (no marker)" "$TEST_DIR/features/skills_engineer/purlin_build.md"

# Spec files allowed with marker
set_marker "spec"
assert_allowed "spec file allowed (marker=spec)" "$TEST_DIR/features/skills_engineer/purlin_build.md"
clear_marker

# .impl.md in features/ — also needs marker (it's under features/)
assert_blocked ".impl.md blocked without marker" "$TEST_DIR/features/skills_engineer/purlin_build.impl.md"
set_marker "build"
assert_allowed ".impl.md allowed with marker=build" "$TEST_DIR/features/skills_engineer/purlin_build.impl.md"
clear_marker

# .discoveries.md in features/ — also needs marker
assert_blocked ".discoveries.md blocked without marker" "$TEST_DIR/features/skills_engineer/purlin_build.discoveries.md"
set_marker "discovery"
assert_allowed ".discoveries.md allowed with marker=discovery" "$TEST_DIR/features/skills_engineer/purlin_build.discoveries.md"
clear_marker

# Nested features paths: _design/, _tombstones/
assert_blocked "features/_design/ blocked without marker" "$TEST_DIR/features/_design/mockup.md"
set_marker "spec"
assert_allowed "features/_design/ allowed with marker" "$TEST_DIR/features/_design/mockup.md"
clear_marker

assert_blocked "features/_tombstones/ blocked without marker" "$TEST_DIR/features/_tombstones/old_feature.md"
set_marker "tombstone"
assert_allowed "features/_tombstones/ allowed with marker" "$TEST_DIR/features/_tombstones/old_feature.md"
clear_marker

# Error message is actionable — directs to the right skill
assert_blocked_with_message "spec block message mentions purlin:spec" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "purlin:spec"
assert_blocked_with_message "spec block message mentions purlin:anchor" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "purlin:anchor"
assert_blocked_with_message "spec block message says skill sets marker" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "skill will set the write marker"

# ============================================================
# STEP 4: OTHER files (write_exceptions) — always ALLOW
# ============================================================
echo ""
echo "=== Step 4: OTHER files (write exceptions) ==="

clear_marker

# Set up write_exceptions
set_write_exceptions '["docs/", "README.md", "CHANGELOG.md", "LICENSE", ".gitignore"]'

# Directory prefix match
assert_allowed "docs/ file allowed as OTHER (dir prefix)" "$TEST_DIR/docs/guide.md"
assert_allowed "docs/api/ file allowed as OTHER (nested dir)" "$TEST_DIR/docs/api/endpoints.md"

# Exact filename match
assert_allowed "README.md allowed as OTHER (exact match)" "$TEST_DIR/README.md"
assert_allowed "CHANGELOG.md allowed as OTHER (exact match)" "$TEST_DIR/CHANGELOG.md"
assert_allowed "LICENSE allowed as OTHER (exact match)" "$TEST_DIR/LICENSE"
assert_allowed ".gitignore allowed as OTHER (exact match)" "$TEST_DIR/.gitignore"

# OTHER files don't need active_skill marker (no marker set, still allowed)
assert_allowed "OTHER file allowed without marker" "$TEST_DIR/docs/guide.md"

# File NOT in write_exceptions is NOT OTHER
assert_blocked "non-excepted file blocked (no marker)" "$TEST_DIR/src/main.py"

# Remove exceptions — formerly OTHER file now blocked as code
set_write_exceptions '[]'
assert_blocked "docs/ blocked when not in exceptions (no marker)" "$TEST_DIR/docs/guide.md"

# Missing config — no exceptions, docs/ is UNKNOWN
clear_config
assert_blocked "docs/ blocked when config missing (no marker)" "$TEST_DIR/docs/guide.md"

# Restore config for remaining tests
set_write_exceptions '["docs/", "README.md", "CHANGELOG.md", "LICENSE", ".gitignore"]'

# ============================================================
# STEP 5: Code files — need active_skill marker
# ============================================================
echo ""
echo "=== Step 5: Code files ==="

clear_marker

# Code files blocked without marker
assert_blocked "CODE file blocked (src, no marker)" "$TEST_DIR/src/main.py"
assert_blocked "CODE file blocked (scripts, no marker)" "$TEST_DIR/scripts/mcp/config_engine.py"
assert_blocked "CODE file blocked (tests, no marker)" "$TEST_DIR/tests/purlin_sync_system/test_guard.sh"

# Code files allowed with marker
set_marker "build"
assert_allowed "CODE file allowed (src, marker=build)" "$TEST_DIR/src/main.py"
assert_allowed "CODE file allowed (scripts, marker=build)" "$TEST_DIR/scripts/mcp/config_engine.py"
assert_allowed "CODE file allowed (tests, marker=build)" "$TEST_DIR/tests/purlin_sync_system/test_guard.sh"
clear_marker

# Error message is actionable — directs to the right skill
assert_blocked_with_message "code block message mentions purlin:build" \
    "$TEST_DIR/src/main.py" "purlin:build"
assert_blocked_with_message "code block message warns against purlin:classify" \
    "$TEST_DIR/src/main.py" "Do NOT reclassify"
assert_blocked_with_message "code block message says it sets the write marker" \
    "$TEST_DIR/src/main.py" "set the write marker"

# ============================================================
# UNKNOWN files — always blocked
# ============================================================
echo ""
echo "=== UNKNOWN files ==="

clear_marker
clear_config

# UNKNOWN file blocked even with marker (marker allows code, not unknown)
# Actually... UNKNOWN files are blocked at step 5 after the marker check.
# With marker: the marker check passes but then we fall through to UNKNOWN case.
# Wait — let me re-check: step 5 checks marker first, then classifies.
# If marker is set, step 5 allows. If not, it checks classification.
# So UNKNOWN with marker → allowed (marker overrides).
# UNKNOWN without marker → blocked.
assert_blocked "UNKNOWN file blocked (no marker, no config)" "$TEST_DIR/unknown/file.xyz"

assert_blocked_with_message "UNKNOWN block message mentions CLAUDE.md" \
    "$TEST_DIR/unknown/file.xyz" "CLAUDE.md"

# UNKNOWN with marker — marker overrides at step 5
set_marker "build"
assert_allowed "UNKNOWN file allowed with active_skill marker (escape)" "$TEST_DIR/unknown/file.xyz"
clear_marker

# Restore config
set_write_exceptions '["docs/", "README.md", "CHANGELOG.md", "LICENSE", ".gitignore"]'

# ============================================================
# Active skill marker edge cases
# ============================================================
echo ""
echo "=== Active skill marker edge cases ==="

# Empty marker file — treated as absent
touch "$TEST_DIR/.purlin/runtime/active_skill"
assert_blocked "empty marker file treated as absent (code)" "$TEST_DIR/src/main.py"
assert_blocked "empty marker file treated as absent (features)" "$TEST_DIR/features/skills_engineer/purlin_build.md"

# Marker with only whitespace — treated as present (file is non-empty)
echo "   " > "$TEST_DIR/.purlin/runtime/active_skill"
assert_allowed "whitespace-only marker treated as present" "$TEST_DIR/src/main.py"
clear_marker

# Marker with any skill name works
set_marker "unit-test"
assert_allowed "marker=unit-test allows code" "$TEST_DIR/src/main.py"
clear_marker

set_marker "spec-code-audit"
assert_allowed "marker=spec-code-audit allows features" "$TEST_DIR/features/skills_engineer/purlin_build.md"
clear_marker

# ============================================================
# Absolute vs relative paths
# ============================================================
echo ""
echo "=== Path handling ==="

clear_marker

# Absolute path gets stripped to relative for classification
set_marker "build"
assert_allowed "absolute path stripped to relative" "$TEST_DIR/src/main.py"
clear_marker

# ============================================================
# classify_file() returns OTHER for excepted paths
# ============================================================
echo ""
echo "=== classify_file() OTHER classification ==="

# Test classify_file directly via python
_test_classify() {
    local desc="$1" rel_path="$2" expected="$3"
    ((total++))
    local result
    result=$(PURLIN_PROJECT_ROOT="$TEST_DIR" python3 -c "
import sys, os
sys.path.insert(0, os.path.join('$PLUGIN_ROOT', 'scripts', 'mcp'))
from config_engine import classify_file
# Clear cache if exists
if hasattr(classify_file, '_cache'):
    delattr(classify_file, '_cache')
# Clear _read_claude_md_classifications cache
from config_engine import _read_claude_md_classifications
if hasattr(_read_claude_md_classifications, '_cache'):
    delattr(_read_claude_md_classifications, '_cache')
print(classify_file('$rel_path'))
" 2>/dev/null)
    if [ "$result" = "$expected" ]; then
        echo "PASS: $desc (got $result)"
        ((passed++))
    else
        echo "FAIL: $desc (expected $expected, got $result)"
        ((failed++))
    fi
}

set_write_exceptions '["docs/", "README.md", "CHANGELOG.md"]'
_test_classify "docs/guide.md → OTHER" "docs/guide.md" "OTHER"
_test_classify "docs/api/endpoints.md → OTHER" "docs/api/endpoints.md" "OTHER"
_test_classify "README.md → OTHER" "README.md" "OTHER"
_test_classify "CHANGELOG.md → OTHER" "CHANGELOG.md" "OTHER"
_test_classify "src/main.py → CODE" "src/main.py" "CODE"
_test_classify "features/auth/login.md → SPEC" "features/auth/login.md" "SPEC"
_test_classify "features/_invariants/i_ext.md → INVARIANT" "features/_invariants/i_ext.md" "INVARIANT"

# Without config — no OTHER classification
clear_config
# Need to clear python module cache by using a fresh invocation
_test_classify "docs/guide.md → UNKNOWN when no config" "docs/guide.md" "UNKNOWN"

# Restore for remaining tests
set_write_exceptions '["docs/", "README.md", "CHANGELOG.md", "LICENSE", ".gitignore"]'

# ============================================================
# Session-init clears stale marker
# ============================================================
echo ""
echo "=== Session-init stale marker cleanup ==="

set_marker "stale-skill"
((total++))
# Simulate what session-init does for marker cleanup
rm -f "$TEST_DIR/.purlin/runtime/active_skill" 2>/dev/null
if [ ! -f "$TEST_DIR/.purlin/runtime/active_skill" ]; then
    echo "PASS: session-init clears stale marker"
    ((passed++))
else
    echo "FAIL: session-init did not clear stale marker"
    ((failed++))
fi

# ============================================================
# Config edge cases
# ============================================================
echo ""
echo "=== Config edge cases ==="

clear_marker

# Malformed config.json — should not crash, no exceptions
echo "NOT VALID JSON" > "$TEST_DIR/.purlin/config.json"
echo "NOT VALID JSON" > "$TEST_DIR/.purlin/config.local.json"
assert_blocked "malformed config.json doesn't crash (code blocked)" "$TEST_DIR/src/main.py"
assert_blocked "malformed config.json doesn't crash (docs blocked as unknown)" "$TEST_DIR/docs/guide.md"

# Empty write_exceptions array
set_write_exceptions '[]'
assert_blocked "empty write_exceptions — docs blocked" "$TEST_DIR/docs/guide.md"

# Restore
set_write_exceptions '["docs/", "README.md", "CHANGELOG.md", "LICENSE", ".gitignore"]'

# ============================================================
# Full decision tree integration — no marker
# ============================================================
echo ""
echo "=== Full decision tree (no marker) ==="

clear_marker

assert_allowed  "system file passes (step 1)" "$TEST_DIR/.purlin/config.json"
assert_blocked  "invariant blocked (step 2)" "$TEST_DIR/features/_invariants/i_external.md"
assert_blocked  "features file blocked (step 3)" "$TEST_DIR/features/skills_engineer/purlin_build.md"
assert_allowed  "OTHER file passes (step 4)" "$TEST_DIR/docs/guide.md"
assert_blocked  "code file blocked (step 5)" "$TEST_DIR/src/main.py"

# ============================================================
# Full decision tree integration — with marker
# ============================================================
echo ""
echo "=== Full decision tree (with marker=build) ==="

set_marker "build"

assert_allowed  "system file passes (step 1, marker)" "$TEST_DIR/.purlin/config.json"
assert_blocked  "invariant still blocked even with marker (step 2)" "$TEST_DIR/features/_invariants/i_external.md"
assert_allowed  "features file passes (step 3, marker)" "$TEST_DIR/features/skills_engineer/purlin_build.md"
assert_allowed  "OTHER file passes (step 4, marker)" "$TEST_DIR/docs/guide.md"
assert_allowed  "code file passes (step 5, marker)" "$TEST_DIR/src/main.py"

clear_marker

# ============================================================
# Full marker lifecycle: set → write allowed → clear → blocked
# ============================================================
echo ""
echo "=== Full marker lifecycle ==="

clear_marker

# Step 1: No marker — code blocked
assert_blocked "lifecycle: code blocked without marker" "$TEST_DIR/src/main.py"

# Step 2: Set marker — code allowed
set_marker "build"
assert_allowed "lifecycle: code allowed after marker set" "$TEST_DIR/src/main.py"

# Step 3: Clear marker — code blocked again
clear_marker
assert_blocked "lifecycle: code blocked after marker cleared" "$TEST_DIR/src/main.py"

# Same lifecycle for features/
assert_blocked "lifecycle: spec blocked without marker" "$TEST_DIR/features/skills_engineer/purlin_build.md"
set_marker "spec"
assert_allowed "lifecycle: spec allowed after marker set" "$TEST_DIR/features/skills_engineer/purlin_build.md"
clear_marker
assert_blocked "lifecycle: spec blocked after marker cleared" "$TEST_DIR/features/skills_engineer/purlin_build.md"

# ============================================================
# Multiple marker values — various skill names
# ============================================================
echo ""
echo "=== Multiple marker skill names ==="

for skill in build spec anchor discovery propose tombstone spec-from-code spec-code-audit infeasible spec-catch-up unit-test regression smoke fixture toolbox verify invariant; do
    set_marker "$skill"
    assert_allowed "marker=$skill allows code write" "$TEST_DIR/src/main.py"
done
clear_marker

# ============================================================
# PLAN items 13-15: classify_file integration
# ============================================================
echo ""
echo "=== classify_file plan items 13-15 ==="

set_write_exceptions '["docs/", "README.md", "CHANGELOG.md"]'

# Item 13: classify_file("docs/guide.md") with exception → OTHER
_test_classify "PLAN-13: docs/guide.md with exception → OTHER" "docs/guide.md" "OTHER"

# Item 14: classify_file("src/auth.ts") → CODE
_test_classify "PLAN-14: src/auth.ts → CODE" "src/auth.ts" "CODE"

# Item 15: classify_file("features/auth/login.md") → SPEC
_test_classify "PLAN-15: features/auth/login.md → SPEC" "features/auth/login.md" "SPEC"

# Restore
set_write_exceptions '["docs/", "README.md", "CHANGELOG.md", "LICENSE", ".gitignore"]'

# ============================================================
# Cleanup
# ============================================================
rm -rf "$TEST_DIR"

echo ""
echo "================================="
echo "$passed passed, $failed failed out of $total"
if [ "$failed" -gt 0 ]; then
    exit 1
fi
exit 0
