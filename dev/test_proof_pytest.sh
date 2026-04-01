#!/usr/bin/env bash
# Tests for scripts/proof/pytest_purlin.py — pytest proof plugin.
#
# Each test creates a temp project, writes a spec and a pytest test file
# with @pytest.mark.proof markers, runs pytest with the plugin, and
# verifies the proof JSON output.
#
# Tests:
#   PROOF-1 (RULE-1): Passing test with @pytest.mark.proof produces proof with status "pass"
#   PROOF-2 (RULE-2): Proof entry contains all required fields
#   PROOF-3 (RULE-3): Proof file written next to matching spec
#   PROOF-4 (RULE-4): Unknown feature writes to specs/ directory
#   PROOF-5 (RULE-5): Running twice replaces old entries
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN="$PROJECT_ROOT/scripts/proof/pytest_purlin.py"
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

echo "=== proof-pytest tests ==="

# --- PROOF-1: Passing test produces proof with status "pass" ---
test_pass_status() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: my_feat\n\n## Rules\n- RULE-1: Must work" > "$tmpdir/specs/auth/my_feat.md"

  cat > "$tmpdir/test_sample.py" << 'PYEOF'
import pytest

@pytest.mark.proof("my_feat", "PROOF-1", "RULE-1")
def test_it_works():
    assert 1 + 1 == 2
PYEOF

  (cd "$tmpdir" && pytest test_sample.py -p pytest_purlin --override-ini="pythonpath=$PROJECT_ROOT/scripts/proof" -q --no-header 2>/dev/null)

  local proof_file="$tmpdir/specs/auth/my_feat.proofs-default.json"
  [[ -f "$proof_file" ]] || return 1
  local status
  status=$(python3 -c "import json; print(json.load(open('$proof_file'))['proofs'][0]['status'])")
  [[ "$status" == "pass" ]]
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "pass status" test_pass_status
purlin_proof "proof-pytest" "PROOF-1" "RULE-1" "$([ $? -eq 0 ] && echo pass || echo fail)" "pass status"

# --- PROOF-2: All required fields present ---
test_all_fields() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: my_feat\n\n## Rules\n- RULE-1: Must work" > "$tmpdir/specs/auth/my_feat.md"

  cat > "$tmpdir/test_sample.py" << 'PYEOF'
import pytest

@pytest.mark.proof("my_feat", "PROOF-1", "RULE-1")
def test_it_works():
    assert True
PYEOF

  (cd "$tmpdir" && pytest test_sample.py -p pytest_purlin --override-ini="pythonpath=$PROJECT_ROOT/scripts/proof" -q --no-header 2>/dev/null)

  local proof_file="$tmpdir/specs/auth/my_feat.proofs-default.json"
  python3 -c "
import json, sys
entry = json.load(open('$proof_file'))['proofs'][0]
required = ['feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier']
for f in required:
    if f not in entry:
        print(f'missing field: {f}', file=sys.stderr)
        sys.exit(1)
"
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "all required fields" test_all_fields
purlin_proof "proof-pytest" "PROOF-2" "RULE-2" "$([ $? -eq 0 ] && echo pass || echo fail)" "all required fields"

# --- PROOF-3: Proof file next to spec ---
test_proof_location() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/billing"
  echo -e "# Feature: invoice\n\n## Rules\n- RULE-1: Must total" > "$tmpdir/specs/billing/invoice.md"

  cat > "$tmpdir/test_sample.py" << 'PYEOF'
import pytest

@pytest.mark.proof("invoice", "PROOF-1", "RULE-1")
def test_total():
    assert 10 + 20 == 30
PYEOF

  (cd "$tmpdir" && pytest test_sample.py -p pytest_purlin --override-ini="pythonpath=$PROJECT_ROOT/scripts/proof" -q --no-header 2>/dev/null)

  [[ -f "$tmpdir/specs/billing/invoice.proofs-default.json" ]]
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "proof file next to spec" test_proof_location
purlin_proof "proof-pytest" "PROOF-3" "RULE-3" "$([ $? -eq 0 ] && echo pass || echo fail)" "proof file next to spec"

# --- PROOF-4: Unknown feature falls back to specs/ ---
test_unknown_feature() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs"

  cat > "$tmpdir/test_sample.py" << 'PYEOF'
import pytest

@pytest.mark.proof("unknown_feat", "PROOF-1", "RULE-1")
def test_it():
    assert True
PYEOF

  (cd "$tmpdir" && pytest test_sample.py -p pytest_purlin --override-ini="pythonpath=$PROJECT_ROOT/scripts/proof" -q --no-header 2>/dev/null)

  [[ -f "$tmpdir/specs/unknown_feat.proofs-default.json" ]]
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "unknown feature falls back to specs/" test_unknown_feature
purlin_proof "proof-pytest" "PROOF-4" "RULE-4" "$([ $? -eq 0 ] && echo pass || echo fail)" "unknown feature falls back to specs/"

# --- PROOF-5: Running twice replaces old entries ---
test_replace_on_rerun() {
  local tmpdir
  tmpdir=$(mktemp -d)
  mkdir -p "$tmpdir/specs/auth"
  echo -e "# Feature: my_feat\n\n## Rules\n- RULE-1: Must work" > "$tmpdir/specs/auth/my_feat.md"

  # First run: failing test
  cat > "$tmpdir/test_sample.py" << 'PYEOF'
import pytest

@pytest.mark.proof("my_feat", "PROOF-1", "RULE-1")
def test_it():
    assert False
PYEOF

  (cd "$tmpdir" && pytest test_sample.py -p pytest_purlin --override-ini="pythonpath=$PROJECT_ROOT/scripts/proof" -q --no-header 2>/dev/null) || true

  # Second run: passing test
  cat > "$tmpdir/test_sample.py" << 'PYEOF'
import pytest

@pytest.mark.proof("my_feat", "PROOF-1", "RULE-1")
def test_it():
    assert True
PYEOF

  (cd "$tmpdir" && pytest test_sample.py -p pytest_purlin --override-ini="pythonpath=$PROJECT_ROOT/scripts/proof" -q --no-header 2>/dev/null)

  local proof_file="$tmpdir/specs/auth/my_feat.proofs-default.json"
  python3 -c "
import json, sys
data = json.load(open('$proof_file'))
if len(data['proofs']) != 1:
    print(f'expected 1 entry, got {len(data[\"proofs\"])}', file=sys.stderr)
    sys.exit(1)
if data['proofs'][0]['status'] != 'pass':
    print(f'expected pass, got {data[\"proofs\"][0][\"status\"]}', file=sys.stderr)
    sys.exit(1)
"
  local rc=$?
  rm -rf "$tmpdir"
  return $rc
}
run_test "replace on rerun" test_replace_on_rerun
purlin_proof "proof-pytest" "PROOF-5" "RULE-5" "$([ $? -eq 0 ] && echo pass || echo fail)" "replace on rerun"

# --- Emit proofs ---
cd "$PROJECT_ROOT"
purlin_proof_finish

# --- Summary ---
echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
