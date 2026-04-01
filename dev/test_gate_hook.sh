#!/usr/bin/env bash
# Tests for gate.sh — invariant write protection hook.
#
# Tests:
#   1. Blocks writes to specs/_invariants/i_* files
#   2. Allows writes to non-invariant files
#   3. Respects bypass lock for matching file
#   4. Bypass lock does not unlock other files
#   5. Handles missing TOOL_INPUT_FILE_PATH gracefully
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GATE_SCRIPT="$SCRIPT_DIR/../scripts/gate.sh"
PASS=0
FAIL=0

run_test() {
  local name="$1"
  shift
  if "$@"; then
    echo "  PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $name"
    FAIL=$((FAIL + 1))
  fi
}

# --- Setup temp project ---
TMPDIR_ROOT=$(mktemp -d)
trap 'rm -rf "$TMPDIR_ROOT"' EXIT
export PROJECT_ROOT="$TMPDIR_ROOT"
mkdir -p "$TMPDIR_ROOT/.purlin/runtime"
mkdir -p "$TMPDIR_ROOT/specs/_invariants"
mkdir -p "$TMPDIR_ROOT/specs/auth"

echo "=== gate.sh tests ==="

# Test 1: Block writes to invariant files
test_blocks_invariant_write() {
  export TOOL_INPUT_FILE_PATH="specs/_invariants/i_colors.md"
  local output
  output=$(bash "$GATE_SCRIPT" 2>&1) && return 1 || true
  [[ "$output" == *"BLOCKED"* ]]
}
run_test "blocks invariant writes" test_blocks_invariant_write

# Test 2: Block writes to invariant files (absolute path)
test_blocks_invariant_write_absolute() {
  export TOOL_INPUT_FILE_PATH="$TMPDIR_ROOT/specs/_invariants/i_design.md"
  local output
  output=$(bash "$GATE_SCRIPT" 2>&1) && return 1 || true
  [[ "$output" == *"BLOCKED"* ]]
}
run_test "blocks invariant writes (absolute path)" test_blocks_invariant_write_absolute

# Test 3: Allow writes to non-invariant files
test_allows_non_invariant_write() {
  export TOOL_INPUT_FILE_PATH="specs/auth/login.md"
  bash "$GATE_SCRIPT" 2>/dev/null
}
run_test "allows non-invariant writes" test_allows_non_invariant_write

# Test 4: Allow writes to regular files
test_allows_regular_file_write() {
  export TOOL_INPUT_FILE_PATH="src/app.py"
  bash "$GATE_SCRIPT" 2>/dev/null
}
run_test "allows regular file writes" test_allows_regular_file_write

# Test 5: Bypass lock allows matching file
test_bypass_lock_allows_matching() {
  export TOOL_INPUT_FILE_PATH="specs/_invariants/i_colors.md"
  local lock_file="$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
  echo '{"target": "specs/_invariants/i_colors.md"}' > "$lock_file"
  bash "$GATE_SCRIPT" 2>/dev/null
  local result=$?
  rm -f "$lock_file"
  return $result
}
run_test "bypass lock allows matching file" test_bypass_lock_allows_matching

# Test 6: Bypass lock does NOT unlock other invariant files
test_bypass_lock_blocks_other_files() {
  export TOOL_INPUT_FILE_PATH="specs/_invariants/i_other.md"
  local lock_file="$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
  echo '{"target": "specs/_invariants/i_colors.md"}' > "$lock_file"
  local output
  output=$(bash "$GATE_SCRIPT" 2>&1) && { rm -f "$lock_file"; return 1; } || true
  rm -f "$lock_file"
  [[ "$output" == *"BLOCKED"* ]]
}
run_test "bypass lock blocks other files" test_bypass_lock_blocks_other_files

# Test 7: No TOOL_INPUT_FILE_PATH = allow (exit 0)
test_missing_file_path() {
  unset TOOL_INPUT_FILE_PATH
  unset TOOL_INPUT_file_path
  bash "$GATE_SCRIPT" 2>/dev/null
}
run_test "missing file path exits 0" test_missing_file_path

# --- Summary ---
echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
