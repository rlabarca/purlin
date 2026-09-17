#!/usr/bin/env bash
# Tests for scripts/proof/pytest_purlin.py, the pytest proof plugin.
#
# Each test makes a temp project, writes a spec and a test file carrying
# @pytest.mark.proof markers, runs pytest with the plugin, and reads the
# runtime proof file back.
#
#   the marker produces an entry with status "pass"
#   the entry carries the seven fields
#   the file is .purlin/runtime/proofs/<feature>.<tier>.json
#   the tier keyword names the file
#   a second run replaces this file's entries and keeps the rest
#   a skipped test writes nothing and keeps the entry it had
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROOF_DIR="$PROJECT_ROOT/scripts/proof"
PASS=0
FAIL=0

if ! python3 -c 'import pytest' >/dev/null 2>&1; then
  echo "pytest is not installed, so this suite did not run."
  exit 0
fi

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

make_project() {
  local d
  d="$(mktemp -d)"
  mkdir -p "$d/specs/a" "$d/.purlin" "$d/tests"
  printf '# feat\n\n## Rules\n- RULE-1: a\n- RULE-2: b\n\n## Proof\n- PROOF-1 (RULE-1): t\n' \
    > "$d/specs/a/feat.md"
  echo "$d"
}

run_pytest() {
  local d="$1"
  (cd "$d" && python3 -m pytest tests -p pytest_purlin \
      --override-ini="pythonpath=$PROOF_DIR" -q --no-header -p no:cacheprovider)
}

echo "=== pytest proof plugin tests ==="

test_pass_status() {
  local d; d="$(make_project)"
  cat > "$d/tests/test_s.py" <<'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_it(): assert 1 + 1 == 2
PY
  run_pytest "$d" >/dev/null 2>&1
  python3 -c "
import json
data = json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))
assert data['tier'] == 'unit', data
entry = data['proofs'][0]
assert entry['status'] == 'pass', entry
assert entry['id'] == 'PROOF-1' and entry['rule'] == 'RULE-1', entry
assert entry['test_name'] == 'test_it', entry
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "a passing marked test records status pass" test_pass_status

test_fail_status() {
  local d; d="$(make_project)"
  cat > "$d/tests/test_s.py" <<'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_it(): assert 1 == 2
PY
  run_pytest "$d" >/dev/null 2>&1 || true
  python3 -c "
import json
entry = json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))['proofs'][0]
assert entry['status'] == 'fail', entry
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "a failing marked test records status fail" test_fail_status

test_seven_fields() {
  local d; d="$(make_project)"
  cat > "$d/tests/test_s.py" <<'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_it(): assert True
PY
  run_pytest "$d" >/dev/null 2>&1
  python3 -c "
import json
entry = json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))['proofs'][0]
assert set(entry) == {'feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'}, entry
assert entry['test_file'] == 'tests/test_s.py', entry
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "the entry carries the seven fields and a relative test file" test_seven_fields

test_tier_names_the_file() {
  local d; d="$(make_project)"
  cat > "$d/tests/test_s.py" <<'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1", tier="e2e")
def test_it(): assert True
PY
  run_pytest "$d" >/dev/null 2>&1
  [[ -f "$d/.purlin/runtime/proofs/feat.e2e.json" ]] && \
    [[ ! -f "$d/.purlin/runtime/proofs/feat.unit.json" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "the tier keyword names the file" test_tier_names_the_file

test_rerun_replaces() {
  local d; d="$(make_project)"
  cat > "$d/tests/test_s.py" <<'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_one(): assert True
@pytest.mark.proof("feat", "PROOF-2", "RULE-2")
def test_two(): assert True
PY
  run_pytest "$d" >/dev/null 2>&1
  cat > "$d/tests/test_s.py" <<'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_one(): assert True
PY
  run_pytest "$d" >/dev/null 2>&1
  python3 -c "
import json
ids = [e['id'] for e in json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))['proofs']]
assert ids == ['PROOF-1'], ids
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "a second run replaces this file's entries" test_rerun_replaces

test_skipped_keeps_its_entry() {
  local d; d="$(make_project)"
  cat > "$d/tests/test_s.py" <<'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_one(): assert True
@pytest.mark.proof("feat", "PROOF-2", "RULE-2")
@pytest.mark.skip(reason="no tool")
def test_two(): assert True
PY
  mkdir -p "$d/.purlin/runtime/proofs"
  python3 -c "
import json
entries = [{'feature': 'feat', 'id': 'PROOF-2', 'rule': 'RULE-2',
            'test_file': 'tests/test_s.py', 'test_name': 'test_two',
            'status': 'pass', 'tier': 'unit'}]
json.dump({'tier': 'unit', 'proofs': entries},
          open('$d/.purlin/runtime/proofs/feat.unit.json', 'w', encoding='utf-8'), indent=2)
"
  run_pytest "$d" >/dev/null 2>&1
  python3 -c "
import json
by = {e['id']: e for e in json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))['proofs']}
assert by['PROOF-2']['test_name'] == 'test_two', by
assert by['PROOF-1']['test_name'] == 'test_one', by
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "a skipped test writes nothing and keeps the entry it had" test_skipped_keeps_its_entry

cd "$PROJECT_ROOT"

echo ""
echo "pytest proof plugin: $PASS/$((PASS+FAIL)) passed"
[[ $FAIL -eq 0 ]]
