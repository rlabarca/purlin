#!/usr/bin/env bash
# Tests for session-start.sh — runtime state cleanup hook.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SESSION_SCRIPT="$PROJECT_ROOT/scripts/session-start.sh"
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

echo "=== session-start.sh tests ==="

# Test 1: Removes invariant_write_lock if it exists — RULE-1
test_removes_lock_file() {
  export PROJECT_ROOT="$TMPDIR_ROOT"
  mkdir -p "$TMPDIR_ROOT/.purlin/runtime"
  echo '{"target": "i_colors.md"}' > "$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock"
  bash "$SESSION_SCRIPT"
  [[ ! -f "$TMPDIR_ROOT/.purlin/runtime/invariant_write_lock" ]]
}
run_test "removes lock file" test_removes_lock_file
purlin_proof "session-start" "PROOF-1" "RULE-1" "$([ $? -eq 0 ] && echo pass || echo fail)" "removes invariant_write_lock when present"

# Test 2: Exits 0 when runtime directory does not exist — RULE-2
test_exits_0_no_runtime_dir() {
  local empty_dir
  empty_dir=$(mktemp -d)
  export PROJECT_ROOT="$empty_dir"
  bash "$SESSION_SCRIPT"
  local result=$?
  rm -rf "$empty_dir"
  return $result
}
run_test "exits 0 when runtime dir missing" test_exits_0_no_runtime_dir
purlin_proof "session-start" "PROOF-2" "RULE-2" "$([ $? -eq 0 ] && echo pass || echo fail)" "exits 0 when .purlin/runtime does not exist"

# --- Emit proof files ---
export PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$SCRIPT_DIR/.."
purlin_proof_finish

# --- Summary ---
echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
