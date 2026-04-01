#!/usr/bin/env bash
# Tests for session-start.sh — runtime state cleanup hook.
# Covers all 5 rules: hook config, lock removal, missing runtime dir, missing lock, exit 0.
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

# PROOF-1 (RULE-1): hooks.json has SessionStart matcher "startup|clear|compact" pointing to session-start.sh
test_hooks_json_config() {
  local hooks_file="$PROJECT_ROOT/hooks/hooks.json"
  [[ -f "$hooks_file" ]] || return 1
  # Verify SessionStart matcher
  python3 -c "
import json, sys
with open('$hooks_file') as f:
    data = json.load(f)
ss = data['hooks']['SessionStart']
assert len(ss) == 1, f'Expected 1 SessionStart entry, got {len(ss)}'
assert ss[0]['matcher'] == 'startup|clear|compact', f'Wrong matcher: {ss[0][\"matcher\"]}'
assert 'session-start.sh' in ss[0]['hooks'][0]['command'], f'Wrong command: {ss[0][\"hooks\"][0][\"command\"]}'
"
}
run_test "hooks.json SessionStart config" test_hooks_json_config
purlin_proof "session_start" "PROOF-1" "RULE-1" "$([ $FAIL -eq 0 ] && echo pass || echo fail)" "hooks.json SessionStart config matches spec"

# PROOF-2 (RULE-2): Creates lock file, runs script, verifies deletion
test_removes_lock_file() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/.purlin/runtime"
  echo '{"target": "i_test.md"}' > "$tmpdir/.purlin/runtime/invariant_write_lock"
  PROJECT_ROOT="$tmpdir" bash "$SESSION_SCRIPT"
  local result=0
  [[ ! -f "$tmpdir/.purlin/runtime/invariant_write_lock" ]] || result=1
  rm -rf "$tmpdir"
  return $result
}
PREV_FAIL=$FAIL
run_test "removes lock file" test_removes_lock_file
purlin_proof "session_start" "PROOF-2" "RULE-2" "$([ $FAIL -eq $PREV_FAIL ] && echo pass || echo fail)" "removes invariant_write_lock when present"

# PROOF-3 (RULE-3): Runs with no .purlin/runtime/ directory, exits 0
test_no_runtime_dir() {
  local tmpdir
  tmpdir=$(mktemp -d)
  # No .purlin/runtime at all
  PROJECT_ROOT="$tmpdir" bash "$SESSION_SCRIPT"
  local result=$?
  rm -rf "$tmpdir"
  return $result
}
PREV_FAIL=$FAIL
run_test "exits 0 when runtime dir missing" test_no_runtime_dir
purlin_proof "session_start" "PROOF-3" "RULE-3" "$([ $FAIL -eq $PREV_FAIL ] && echo pass || echo fail)" "no-op when .purlin/runtime does not exist"

# PROOF-4 (RULE-4): Runs with runtime dir but no lock file, exits 0
test_no_lock_file() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/.purlin/runtime"
  # Runtime dir exists but no lock file
  PROJECT_ROOT="$tmpdir" bash "$SESSION_SCRIPT"
  local result=$?
  rm -rf "$tmpdir"
  return $result
}
PREV_FAIL=$FAIL
run_test "exits 0 when lock file missing" test_no_lock_file
purlin_proof "session_start" "PROOF-4" "RULE-4" "$([ $FAIL -eq $PREV_FAIL ] && echo pass || echo fail)" "no-op when lock file does not exist"

# PROOF-5 (RULE-5): Verify exit code 0 under normal conditions
test_always_exits_0() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/.purlin/runtime"
  echo '{"target": "i_test.md"}' > "$tmpdir/.purlin/runtime/invariant_write_lock"
  PROJECT_ROOT="$tmpdir" bash "$SESSION_SCRIPT"
  local rc=$?
  rm -rf "$tmpdir"
  [[ $rc -eq 0 ]]
}
PREV_FAIL=$FAIL
run_test "always exits 0" test_always_exits_0
purlin_proof "session_start" "PROOF-5" "RULE-5" "$([ $FAIL -eq $PREV_FAIL ] && echo pass || echo fail)" "exit code is always 0"

# --- Emit proof files ---
export PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$SCRIPT_DIR/.."
purlin_proof_finish

# --- Summary ---
echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
