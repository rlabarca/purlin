#!/usr/bin/env bash
# Test: Write guard enforcement (sync system)
# Verifies that write-guard.sh blocks INVARIANT and UNKNOWN files,
# and allows all other classified files (CODE, SPEC, QA).
# No mode system — the write guard is classification-based only.
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

# Run write guard with a file path, return exit code
run_guard() {
    local file_path="$1"
    echo "{\"tool_input\": {\"file_path\": \"$file_path\"}}" | bash "$WRITE_GUARD" >/dev/null 2>&1
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

# === INVARIANT files — always blocked ===
assert_blocked "INVARIANT file blocked" "$TEST_DIR/features/_invariants/i_external.md"

# === UNKNOWN files — always blocked ===
assert_blocked "UNKNOWN file blocked" "$TEST_DIR/docs/random.md"

# === CODE files — allowed ===
assert_allowed "CODE file allowed (src)" "$TEST_DIR/src/main.py"
assert_allowed "CODE file allowed (scripts)" "$TEST_DIR/scripts/mcp/config_engine.py"

# === SPEC files — allowed ===
assert_allowed "SPEC file allowed" "$TEST_DIR/features/skills_engineer/purlin_build.md"

# === QA files — allowed ===
assert_allowed "QA file allowed (discoveries)" "$TEST_DIR/features/skills_engineer/purlin_build.discoveries.md"

# === Companion files — allowed ===
assert_allowed "companion file allowed (.impl.md)" "$TEST_DIR/features/skills_engineer/purlin_build.impl.md"

# === INVARIANT bypass lock ===
echo "$TEST_DIR/features/_invariants/i_external.md" > "$TEST_DIR/.purlin/runtime/invariant_write_lock"
assert_allowed "invariant bypass lock works" "$TEST_DIR/features/_invariants/i_external.md"
rm -f "$TEST_DIR/.purlin/runtime/invariant_write_lock"

# Cleanup
rm -rf "$TEST_DIR"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
