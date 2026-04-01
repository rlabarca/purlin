#!/usr/bin/env bash
# Tests for scripts/proof/shell_purlin.sh — shell proof harness.
#
# Tests:
#   PROOF-1 (RULE-1): purlin_proof + purlin_proof_finish produces correct proof JSON
#   PROOF-2 (RULE-2): PURLIN_PROOF_TIER controls proof file tier naming
#   PROOF-3 (RULE-3): Proof file is placed in the spec's directory
#   PROOF-4 (RULE-4): Running twice replaces old entries for the feature
#   PROOF-5 (RULE-5): purlin_proof_finish with no proofs produces no file writes
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PASS=0
FAIL=0

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

echo "=== proof-shell tests ==="

# --- PROOF-1: purlin_proof accumulates and purlin_proof_finish writes correct JSON ---
test_basic_proof_output() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: login\n\n## Rules\n- RULE-1: Must auth" > "$tmpdir/specs/auth/login.md"

  (
    cd "$tmpdir"
    # Source the harness fresh (resets _PURLIN_PROOFS)
    source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"
    purlin_proof "login" "PROOF-1" "RULE-1" pass "test_auth_works"
    purlin_proof_finish
  )

  # Verify proof file exists and has correct content
  local proof_file="$tmpdir/specs/auth/login.proofs-default.json"
  [[ -f "$proof_file" ]] || return 1

  local feature id rule status
  feature=$(python3 -c "import json; d=json.load(open('$proof_file')); print(d['proofs'][0]['feature'])")
  id=$(python3 -c "import json; d=json.load(open('$proof_file')); print(d['proofs'][0]['id'])")
  rule=$(python3 -c "import json; d=json.load(open('$proof_file')); print(d['proofs'][0]['rule'])")
  status=$(python3 -c "import json; d=json.load(open('$proof_file')); print(d['proofs'][0]['status'])")

  [[ "$feature" == "login" ]] && [[ "$id" == "PROOF-1" ]] && [[ "$rule" == "RULE-1" ]] && [[ "$status" == "pass" ]]
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "basic proof output" test_basic_proof_output

# --- PROOF-2: PURLIN_PROOF_TIER controls tier naming ---
test_tier_naming() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: login\n\n## Rules\n- RULE-1: Must auth" > "$tmpdir/specs/auth/login.md"

  (
    cd "$tmpdir"
    export PURLIN_PROOF_TIER=slow
    source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"
    purlin_proof "login" "PROOF-1" "RULE-1" pass "test_slow"
    purlin_proof_finish
  )

  local proof_file="$tmpdir/specs/auth/login.proofs-slow.json"
  [[ -f "$proof_file" ]]
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "tier naming via PURLIN_PROOF_TIER" test_tier_naming

# --- PROOF-3: Proof file is placed next to the matching spec ---
test_proof_file_location() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/billing"
  echo -e "# Feature: invoice\n\n## Rules\n- RULE-1: Must total" > "$tmpdir/specs/billing/invoice.md"

  (
    cd "$tmpdir"
    source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"
    purlin_proof "invoice" "PROOF-1" "RULE-1" pass "test_total"
    purlin_proof_finish
  )

  # Must be in specs/billing/, not specs/
  [[ -f "$tmpdir/specs/billing/invoice.proofs-default.json" ]]
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "proof file placed next to spec" test_proof_file_location

# --- PROOF-4: Running twice replaces old entries ---
test_replace_on_rerun() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: login\n\n## Rules\n- RULE-1: Must auth" > "$tmpdir/specs/auth/login.md"

  # First run with status=fail
  (
    cd "$tmpdir"
    source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"
    purlin_proof "login" "PROOF-1" "RULE-1" fail "test_auth"
    purlin_proof_finish
  )

  # Second run with status=pass
  (
    cd "$tmpdir"
    source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"
    purlin_proof "login" "PROOF-1" "RULE-1" pass "test_auth"
    purlin_proof_finish
  )

  local proof_file="$tmpdir/specs/auth/login.proofs-default.json"
  local count status
  count=$(python3 -c "import json; d=json.load(open('$proof_file')); print(len(d['proofs']))")
  status=$(python3 -c "import json; d=json.load(open('$proof_file')); print(d['proofs'][0]['status'])")

  # Should have exactly 1 entry (replaced, not appended) with status=pass
  [[ "$count" == "1" ]] && [[ "$status" == "pass" ]]
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "replace on rerun" test_replace_on_rerun

# --- PROOF-5: No proofs accumulated → no file writes ---
test_no_proofs_no_write() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: login\n\n## Rules\n- RULE-1: Must auth" > "$tmpdir/specs/auth/login.md"

  (
    cd "$tmpdir"
    source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"
    # Call finish without any purlin_proof calls
    purlin_proof_finish
  )

  # No proof file should exist
  ! ls "$tmpdir/specs/auth/"*.proofs-*.json 2>/dev/null | grep -q .
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "no proofs = no file writes" test_no_proofs_no_write

# --- Emit proof files for this test suite ---
# Use the REAL project root's proof harness to record results
source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"

# We need to record results based on the test outcomes above.
# Re-check each test and record. We use the PASS/FAIL counters
# and the ordering to determine results.
# Since set -e is on and each test ran, we know the order.
# We'll re-derive from the counter.

# Actually, let's just record based on the run_test results.
# All tests above used run_test which updates PASS/FAIL.
# But we need per-test status. Let's record after each test.

# The proof calls need to happen after the tests but we can't
# easily get per-test status from the counter. Instead, let's
# use a simpler approach: run each test and capture the exit code.

# Reset and re-run with proof recording
_PURLIN_PROOFS=""

record_proof() {
  local proof_id="$1" rule_id="$2" test_name="$3"
  shift 3
  if "$@" >/dev/null 2>&1; then
    purlin_proof "proof-shell" "$proof_id" "$rule_id" pass "$test_name"
  else
    purlin_proof "proof-shell" "$proof_id" "$rule_id" fail "$test_name"
  fi
}

record_proof "PROOF-1" "RULE-1" "basic proof output" test_basic_proof_output
record_proof "PROOF-2" "RULE-2" "tier naming via PURLIN_PROOF_TIER" test_tier_naming
record_proof "PROOF-3" "RULE-3" "proof file placed next to spec" test_proof_file_location
record_proof "PROOF-4" "RULE-4" "replace on rerun" test_replace_on_rerun
record_proof "PROOF-5" "RULE-5" "no proofs = no file writes" test_no_proofs_no_write

cd "$PROJECT_ROOT"
purlin_proof_finish

# --- Summary ---
echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
