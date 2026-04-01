#!/usr/bin/env bash
# Tests for gate.sh — invariant write protection hook.
#
# Tests:
#   1. Blocks writes to specs/_invariants/i_* files (RULE-1)
#   2. Allows writes to non-invariant files (RULE-2)
#   3. Respects bypass lock for matching file (RULE-3)
#   4. Bypass lock does not unlock other files
#   5. Handles missing TOOL_INPUT_FILE_PATH gracefully (RULE-4)
#   6. Blocked message includes corrective action (RULE-5)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GATE_SCRIPT="$PROJECT_ROOT/scripts/gate.sh"
PASS=0
FAIL=0

# Load proof harness
source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"

run_test() {
  local name="$1"
  shift
  if "$@"; then
    echo "  PASS: $name"
    PASS=$((PASS + 1))
    return 0
  else
    echo "  FAIL: $name"
    FAIL=$((FAIL + 1))
    return 1
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

# Test 1: Block writes to invariant files (relative path) — RULE-1
test_blocks_invariant_write() {
  export TOOL_INPUT_FILE_PATH="specs/_invariants/i_colors.md"
  local output exit_code=0
  output=$(bash "$GATE_SCRIPT" 2>&1) || exit_code=$?
  [[ $exit_code -eq 2 ]] && [[ "$output" == *"BLOCKED"* ]]
}
run_test "blocks invariant writes (relative)" test_blocks_invariant_write
purlin_proof "gate-hook" "PROOF-1a" "RULE-1" "$([ $? -eq 0 ] && echo pass || echo fail)" "blocks invariant writes (relative path, exit 2 + BLOCKED)"

# Test 2: Block writes to invariant files (absolute path) — RULE-1
test_blocks_invariant_write_absolute() {
  export TOOL_INPUT_FILE_PATH="$TMPDIR_ROOT/specs/_invariants/i_design.md"
  local output exit_code=0
  output=$(bash "$GATE_SCRIPT" 2>&1) || exit_code=$?
  [[ $exit_code -eq 2 ]] && [[ "$output" == *"BLOCKED"* ]]
}
run_test "blocks invariant writes (absolute)" test_blocks_invariant_write_absolute
purlin_proof "gate-hook" "PROOF-1b" "RULE-1" "$([ $? -eq 0 ] && echo pass || echo fail)" "blocks invariant writes (absolute path, exit 2 + BLOCKED)"

# Test 3: Allow writes to non-invariant spec files — RULE-2
test_allows_non_invariant_write() {
  export TOOL_INPUT_FILE_PATH="specs/auth/login.md"
  bash "$GATE_SCRIPT" 2>/dev/null
}
run_test "allows non-invariant writes" test_allows_non_invariant_write
purlin_proof "gate-hook" "PROOF-2a" "RULE-2" "$([ $? -eq 0 ] && echo pass || echo fail)" "allows non-invariant spec file writes"

# Test 4: Allow writes to regular files — RULE-2
test_allows_regular_file_write() {
  export TOOL_INPUT_FILE_PATH="src/app.py"
  bash "$GATE_SCRIPT" 2>/dev/null
}
run_test "allows regular file writes" test_allows_regular_file_write
purlin_proof "gate-hook" "PROOF-2b" "RULE-2" "$([ $? -eq 0 ] && echo pass || echo fail)" "allows regular file writes"

# Test 5: Bypass lock allows matching file — RULE-3
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
purlin_proof "gate-hook" "PROOF-3" "RULE-3" "$([ $? -eq 0 ] && echo pass || echo fail)" "bypass lock allows matching file (exit 0)"

# Test 6: Bypass lock does NOT unlock other invariant files
test_bypass_lock_blocks_other_files() {
  export TOOL_INPUT_FILE_PATH="specs/_invariants/i_other.md"
  local lock_file="$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
  echo '{"target": "specs/_invariants/i_colors.md"}' > "$lock_file"
  local output exit_code=0
  output=$(bash "$GATE_SCRIPT" 2>&1) || exit_code=$?
  rm -f "$lock_file"
  [[ $exit_code -eq 2 ]] && [[ "$output" == *"BLOCKED"* ]]
}
run_test "bypass lock blocks other files" test_bypass_lock_blocks_other_files

# Test 7: No TOOL_INPUT_FILE_PATH = allow (exit 0) — RULE-4
test_missing_file_path() {
  unset TOOL_INPUT_FILE_PATH
  unset TOOL_INPUT_file_path
  bash "$GATE_SCRIPT" 2>/dev/null
}
run_test "missing file path exits 0" test_missing_file_path
purlin_proof "gate-hook" "PROOF-4" "RULE-4" "$([ $? -eq 0 ] && echo pass || echo fail)" "missing file path exits 0"

# Test 8: Blocked message includes corrective action — RULE-5
test_blocked_message_includes_action() {
  export TOOL_INPUT_FILE_PATH="specs/_invariants/i_test.md"
  local output
  output=$(bash "$GATE_SCRIPT" 2>&1) || true
  [[ "$output" == *"purlin:invariant sync"* ]]
}
run_test "blocked message includes corrective action" test_blocked_message_includes_action
purlin_proof "gate-hook" "PROOF-5" "RULE-5" "$([ $? -eq 0 ] && echo pass || echo fail)" "blocked message includes purlin:invariant sync"

# --- Emit proof files ---
# Reset PROJECT_ROOT to actual project root for proof file discovery
export PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"
purlin_proof_finish

# --- Summary ---
echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
