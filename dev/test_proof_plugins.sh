#!/usr/bin/env bash
# The behaviour every proof plugin shares, driven through pytest, the jest
# reporter and the shell harness.
#
# What is checked here: the runtime proof file's location and name, the seven
# fields, the no-marker no-op, the write-scoped merge, orphan reaping, ordinal
# order after the merge, and the loud failure when markers were seen and
# nothing was written.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROOF_DIR="$PROJECT_ROOT/scripts/proof"
JEST_REPORTER="$PROOF_DIR/jest_purlin.js"
SHELL_HARNESS="$PROOF_DIR/shell_purlin.sh"

# Load the harness so this suite records its own evidence.
source "$SHELL_HARNESS"

PASS=0
FAIL=0
PYTEST_READY=0
if python3 -c 'import pytest' >/dev/null 2>&1; then
  PYTEST_READY=1
else
  echo "  note: pytest is not installed, so the pytest arm did not run."
fi
NODE_READY=0
command -v node >/dev/null 2>&1 && NODE_READY=1 || \
  echo "  note: node is not installed, so the jest arm did not run."

record() {
  local feature="$1" proof_id="$2" rule_id="$3" name="$4" status="$5"
  echo "  $([[ "$status" == "pass" ]] && echo PASS || echo FAIL): $name"
  PURLIN_PROOF_TIER=e2e purlin_proof "$feature" "$proof_id" "$rule_id" \
    "$status" "$name"
  [[ "$status" == "pass" ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1))
}

run() {
  local feature="$1" proof_id="$2" rule_id="$3" name="$4"
  shift 4
  if "$@" >/dev/null 2>&1; then
    record "$feature" "$proof_id" "$rule_id" "$name" pass
  else
    record "$feature" "$proof_id" "$rule_id" "$name" fail
  fi
}

# A project root the plugins recognise: specs/ and .purlin/ both present.
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

echo "=== proof plugin tests (the shared contract) ==="

# --- The runtime location and name -----------------------------------------
test_runtime_location() {
  [[ $PYTEST_READY -eq 1 ]] || return 0
  local d; d="$(make_project)"
  cat > "$d/tests/test_s.py" <<'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
def test_it(): assert True
PY
  run_pytest "$d" || true
  [[ -f "$d/.purlin/runtime/proofs/feat.unit.json" ]] || { rm -rf "$d"; return 1; }
  # Nothing is written under specs/.
  [[ -z "$(find "$d/specs" -name '*.json')" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run "run_script" "PROOF-48" "RULE-23" "the proof file is written to the runtime directory" test_runtime_location

test_file_name_carries_feature_and_tier() {
  local d; d="$(make_project)"
  cat > "$d/tests/t.sh" <<EOF
source "$SHELL_HARNESS"
export PURLIN_PROOF_TIER=integration
purlin_proof "feat" "PROOF-1" "RULE-1" pass "a case"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/t.sh)
  [[ -f "$d/.purlin/runtime/proofs/feat.integration.json" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run "run_script" "PROOF-48" "RULE-23" "the file name carries the feature and the tier" test_file_name_carries_feature_and_tier

# --- The seven fields -------------------------------------------------------
test_seven_fields() {
  local d; d="$(make_project)"
  cat > "$d/tests/t.sh" <<EOF
source "$SHELL_HARNESS"
purlin_proof "feat" "PROOF-1" "RULE-1" pass "a case"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/t.sh)
  python3 -c "
import json, sys
entry = json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))['proofs'][0]
want = {'feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'}
assert set(entry) == want, entry
assert entry['test_file'] == 'tests/t.sh', entry
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "run_script" "PROOF-48" "RULE-23" "every entry carries the seven fields and no eighth" test_seven_fields

# --- No marker, no file -----------------------------------------------------
test_no_markers_no_file() {
  [[ $PYTEST_READY -eq 1 ]] || return 0
  local d; d="$(make_project)"
  cat > "$d/tests/test_s.py" <<'PY'
def test_plain(): assert True
PY
  run_pytest "$d" || true
  [[ ! -d "$d/.purlin/runtime/proofs" ]] || \
    [[ -z "$(ls -A "$d/.purlin/runtime/proofs")" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run "run_script" "PROOF-49" "RULE-26" "a run that collected no marker writes nothing" test_no_markers_no_file

# --- The write-scoped merge -------------------------------------------------
test_merge_keeps_other_features_and_files() {
  local d; d="$(make_project)"
  mkdir -p "$d/.purlin/runtime/proofs"
  printf 'kept\n' > "$d/tests/kept.sh"
  python3 -c "
import json
entries = [
  {'feature': 'other', 'id': 'PROOF-1', 'rule': 'RULE-1',
   'test_file': 'tests/kept.sh', 'test_name': 'other', 'status': 'pass', 'tier': 'unit'},
  {'feature': 'feat', 'id': 'PROOF-2', 'rule': 'RULE-2',
   'test_file': 'tests/kept.sh', 'test_name': 'second', 'status': 'pass', 'tier': 'unit'},
  {'feature': 'feat', 'id': 'PROOF-3', 'rule': 'RULE-2',
   'test_file': 'tests/gone.sh', 'test_name': 'gone', 'status': 'pass', 'tier': 'unit'},
]
json.dump({'tier': 'unit', 'proofs': entries},
          open('$d/.purlin/runtime/proofs/feat.unit.json', 'w', encoding='utf-8'), indent=2)
"
  cat > "$d/tests/t.sh" <<EOF
source "$SHELL_HARNESS"
purlin_proof "feat" "PROOF-1" "RULE-1" pass "fresh"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/t.sh)
  python3 -c "
import json
data = json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))
keys = {(e['feature'], e['id'], e['test_file']) for e in data['proofs']}
assert ('other', 'PROOF-1', 'tests/kept.sh') in keys, keys
assert ('feat', 'PROOF-2', 'tests/kept.sh') in keys, keys
assert ('feat', 'PROOF-3', 'tests/gone.sh') not in keys, keys
assert ('feat', 'PROOF-1', 'tests/t.sh') in keys, keys
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "run_script" "PROOF-50" "RULE-27" "the merge keeps other features and other test files" test_merge_keeps_other_features_and_files
run "run_script" "PROOF-50" "RULE-27" "an entry whose test file is gone is reaped" test_merge_keeps_other_features_and_files

# --- Ordinal order after the merge -----------------------------------------
test_ordinal_order() {
  local d; d="$(make_project)"
  mkdir -p "$d/forward" "$d/reversed"
  for dir in forward reversed; do
    mkdir -p "$d/$dir/specs/a" "$d/$dir/.purlin" "$d/$dir/tests"
    printf '# feat\n\n## Rules\n- RULE-1: a\n' > "$d/$dir/specs/a/feat.md"
  done
  cat > "$d/forward/tests/t.sh" <<EOF
source "$SHELL_HARNESS"
purlin_proof "feat" "PROOF-1" "RULE-1" pass "a"
purlin_proof "feat" "PROOF-2" "RULE-1" pass "b"
purlin_proof "feat" "PROOF-10" "RULE-1" pass "c"
purlin_proof "feat" "PROOF-11" "RULE-1" pass "d"
purlin_proof_finish
EOF
  cat > "$d/reversed/tests/t.sh" <<EOF
source "$SHELL_HARNESS"
purlin_proof "feat" "PROOF-11" "RULE-1" pass "d"
purlin_proof "feat" "PROOF-10" "RULE-1" pass "c"
purlin_proof "feat" "PROOF-2" "RULE-1" pass "b"
purlin_proof "feat" "PROOF-1" "RULE-1" pass "a"
purlin_proof_finish
EOF
  (cd "$d/forward" && bash tests/t.sh)
  (cd "$d/reversed" && bash tests/t.sh)
  python3 -c "
import json
a = open('$d/forward/.purlin/runtime/proofs/feat.unit.json', 'rb').read()
b = open('$d/reversed/.purlin/runtime/proofs/feat.unit.json', 'rb').read()
assert a == b, 'the two runs wrote different bytes'
ids = [e['id'] for e in json.loads(a.decode())['proofs']]
want = ['PROOF-1', 'PROOF-10', 'PROOF-11', 'PROOF-2']
assert ids == want, (want, ids)
"
  local rc=$?; rm -rf "$d"; return $rc
}
run "run_script" "PROOF-51" "RULE-28" "entries are written in ordinal order whatever the call order" test_ordinal_order

# --- Markers seen, nothing written -----------------------------------------
test_seen_markers_and_no_entry_fails() {
  [[ $PYTEST_READY -eq 1 ]] || return 0
  local d; d="$(make_project)"
  cat > "$d/tests/test_s.py" <<'PY'
import pytest
@pytest.mark.proof("feat", "PROOF-1", "RULE-1")
@pytest.mark.skip(reason="no tool")
def test_it(): assert True
PY
  local out
  out="$( (cd "$d" && python3 -m pytest tests -p pytest_purlin \
      --override-ini="pythonpath=$PROOF_DIR" -q --no-header -p no:cacheprovider) 2>&1 )" && \
    { rm -rf "$d"; return 1; }
  grep -q "no proof entry was written for feat" <<<"$out"
  local rc=$?; rm -rf "$d"; return $rc
}
run "run_script" "PROOF-52" "RULE-30" "markers seen and nothing written fails the run" test_seen_markers_and_no_entry_fails

# --- The jest reporter ------------------------------------------------------
test_jest_writes_the_runtime_file() {
  [[ $NODE_READY -eq 1 ]] || return 0
  local d; d="$(make_project)"
  printf '// marked\n' > "$d/tests/a.test.js"
  cat > "$d/harness.cjs" <<EOF
const path = require("path");
const Reporter = require("$JEST_REPORTER");
const r = new Reporter({rootDir: "$d"});
r.onTestResult({}, {testFilePath: path.join("$d", "tests/a.test.js"),
  testResults: [{title: "ok [proof:feat:PROOF-1:RULE-1:unit]", status: "passed"}]});
r.onRunComplete();
EOF
  (cd "$d" && node harness.cjs)
  [[ -f "$d/.purlin/runtime/proofs/feat.unit.json" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run "run_script" "PROOF-48" "RULE-23" "the jest reporter writes the runtime proof file" test_jest_writes_the_runtime_file

# --- The retired keyword ----------------------------------------------------
test_retired_keyword_refused() {
  local d; d="$(make_project)"
  cat > "$d/tests/t.sh" <<EOF
source "$SHELL_HARNESS"
export PURLIN_PROOF_PLATFORMS=windows-2022
purlin_proof "feat" "PROOF-1" "RULE-1" pass "a case"
purlin_proof_finish
EOF
  local out
  out="$( (cd "$d" && bash tests/t.sh) 2>&1 )" && { rm -rf "$d"; return 1; }
  grep -q "@env(windows)" <<<"$out"
  local rc=$?; rm -rf "$d"; return $rc
}
run "run_script" "PROOF-53" "RULE-31" "a retired marker keyword is refused and names @env" test_retired_keyword_refused

cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "proof plugins: $PASS/$((PASS+FAIL)) passed"
[[ $FAIL -eq 0 ]]
