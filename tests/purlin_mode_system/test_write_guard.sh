#!/usr/bin/env bash
# Test: Mode guard write enforcement
# Verifies that mode-guard.sh correctly allows/blocks file writes
# based on the active mode and file classification.
#
# Tests the full mode-file compatibility matrix:
#   Engineer -> CODE=allow, SPEC=block, QA=block, INVARIANT=block
#   PM       -> SPEC=allow, CODE=block, QA=block, INVARIANT=block
#   QA       -> QA=allow,   CODE=block, SPEC=block, INVARIANT=block
#   (none)   -> ALL=block
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
MODE_GUARD="$PLUGIN_ROOT/hooks/scripts/mode-guard.sh"

passed=0
failed=0
total=0

# Create isolated test environment
TEST_DIR=$(mktemp -d)
TEST_SESSION="test-guard-$$"
export PURLIN_PROJECT_ROOT="$TEST_DIR"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
export PURLIN_SESSION_ID="$TEST_SESSION"

mkdir -p "$TEST_DIR/.purlin/runtime"
mkdir -p "$TEST_DIR/features/_invariants"
mkdir -p "$TEST_DIR/features/skills_engineer"
mkdir -p "$TEST_DIR/tests/qa/scenarios"
mkdir -p "$TEST_DIR/scripts/mcp"
mkdir -p "$TEST_DIR/src"

# Copy file_classification.json for fallback
if [ -f "$PLUGIN_ROOT/references/file_classification.json" ]; then
    mkdir -p "$TEST_DIR/references"
    cp "$PLUGIN_ROOT/references/file_classification.json" "$TEST_DIR/references/"
fi

set_mode() {
    echo "$1" > "$TEST_DIR/.purlin/runtime/current_mode_$TEST_SESSION"
}

clear_mode() {
    echo "" > "$TEST_DIR/.purlin/runtime/current_mode_$TEST_SESSION"
}

# Run mode guard with a file path, return exit code
# Args: $1=file_path
run_guard() {
    local file_path="$1"
    echo "{\"tool_input\": {\"file_path\": \"$file_path\"}}" | bash "$MODE_GUARD" >/dev/null 2>&1
    return $?
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

# === DEFAULT MODE (no mode active) — blocks everything ===
clear_mode

assert_blocked "default mode blocks CODE file" "$TEST_DIR/src/main.py"
assert_blocked "default mode blocks SPEC file" "$TEST_DIR/features/skills_engineer/purlin_build.md"
assert_blocked "default mode blocks QA file" "$TEST_DIR/features/skills_engineer/purlin_build.discoveries.md"
assert_blocked "default mode blocks INVARIANT file" "$TEST_DIR/features/_invariants/i_external.md"
assert_blocked "default mode blocks companion file" "$TEST_DIR/features/skills_engineer/purlin_build.impl.md"

# === ENGINEER MODE ===
set_mode "engineer"

assert_allowed "engineer allows CODE file (src)" "$TEST_DIR/src/main.py"
assert_allowed "engineer allows CODE file (scripts)" "$TEST_DIR/scripts/mcp/config_engine.py"
assert_allowed "engineer allows companion file (.impl.md)" "$TEST_DIR/features/skills_engineer/purlin_build.impl.md"
assert_blocked "engineer blocks SPEC file" "$TEST_DIR/features/skills_engineer/purlin_build.md"
assert_blocked "engineer blocks INVARIANT file" "$TEST_DIR/features/_invariants/i_external.md"

# === PM MODE ===
set_mode "pm"

assert_allowed "pm allows SPEC file" "$TEST_DIR/features/skills_engineer/purlin_build.md"
assert_blocked "pm blocks CODE file (src)" "$TEST_DIR/src/main.py"
assert_blocked "pm blocks CODE file (scripts)" "$TEST_DIR/scripts/mcp/config_engine.py"
assert_blocked "pm blocks companion file (.impl.md)" "$TEST_DIR/features/skills_engineer/purlin_build.impl.md"
assert_blocked "pm blocks INVARIANT file" "$TEST_DIR/features/_invariants/i_external.md"

# === QA MODE ===
set_mode "qa"

assert_allowed "qa allows discovery sidecar" "$TEST_DIR/features/skills_engineer/purlin_build.discoveries.md"
assert_blocked "qa blocks CODE file" "$TEST_DIR/src/main.py"
assert_blocked "qa blocks SPEC file" "$TEST_DIR/features/skills_engineer/purlin_build.md"
assert_blocked "qa blocks INVARIANT file" "$TEST_DIR/features/_invariants/i_external.md"
assert_blocked "qa blocks companion file (.impl.md)" "$TEST_DIR/features/skills_engineer/purlin_build.impl.md"

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
