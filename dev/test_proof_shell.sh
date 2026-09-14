#!/usr/bin/env bash
# Tests for scripts/proof/shell_purlin.sh, the shell proof harness.
#
#   purlin_proof + purlin_proof_finish writes the runtime proof file
#   PURLIN_PROOF_TIER names the tier and the file
#   test_file is the calling script, project-relative
#   a second run replaces this script's entries and keeps the rest
#   purlin_proof_finish with nothing buffered writes nothing
#   the retired PURLIN_PROOF_PLATFORMS variable is refused and names @env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HARNESS="$PROJECT_ROOT/scripts/proof/shell_purlin.sh"
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

make_project() {
  local d
  d="$(mktemp -d)"
  mkdir -p "$d/specs/a" "$d/.purlin" "$d/tests"
  printf '# feat\n\n## Rules\n- RULE-1: a\n- RULE-2: b\n' > "$d/specs/a/feat.md"
  echo "$d"
}

echo "=== shell proof harness tests ==="

test_writes_the_runtime_file() {
  local d; d="$(make_project)"
  cat > "$d/tests/t.sh" <<EOF
source "$HARNESS"
purlin_proof "feat" "PROOF-1" "RULE-1" pass "a case"
purlin_proof "feat" "PROOF-2" "RULE-2" fail "another case"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/t.sh) >/dev/null 2>&1
  python3 -c "
import json
data = json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))
assert data['tier'] == 'unit', data
by = {e['id']: e for e in data['proofs']}
assert by['PROOF-1']['status'] == 'pass', by
assert by['PROOF-2']['status'] == 'fail', by
assert set(by['PROOF-1']) == {'feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'}, by
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "purlin_proof_finish writes the runtime proof file" test_writes_the_runtime_file

test_tier_env() {
  local d; d="$(make_project)"
  cat > "$d/tests/t.sh" <<EOF
source "$HARNESS"
export PURLIN_PROOF_TIER=integration
purlin_proof "feat" "PROOF-1" "RULE-1" pass "a case"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/t.sh) >/dev/null 2>&1
  [[ -f "$d/.purlin/runtime/proofs/feat.integration.json" ]] && \
    [[ ! -f "$d/.purlin/runtime/proofs/feat.unit.json" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "PURLIN_PROOF_TIER names the tier and the file" test_tier_env

test_test_file_is_the_caller() {
  local d; d="$(make_project)"
  mkdir -p "$d/tests/deep"
  cat > "$d/tests/deep/suite.sh" <<EOF
source "$HARNESS"
purlin_proof "feat" "PROOF-1" "RULE-1" pass "a case"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/deep/suite.sh) >/dev/null 2>&1
  python3 -c "
import json
entry = json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))['proofs'][0]
assert entry['test_file'] == 'tests/deep/suite.sh', entry
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "test_file is the calling script, project-relative" test_test_file_is_the_caller

test_rerun_replaces_this_script() {
  local d; d="$(make_project)"
  cat > "$d/tests/other.sh" <<EOF
source "$HARNESS"
purlin_proof "feat" "PROOF-9" "RULE-2" pass "kept"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/other.sh) >/dev/null 2>&1
  cat > "$d/tests/t.sh" <<EOF
source "$HARNESS"
purlin_proof "feat" "PROOF-1" "RULE-1" pass "first"
purlin_proof "feat" "PROOF-2" "RULE-2" pass "second"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/t.sh) >/dev/null 2>&1
  cat > "$d/tests/t.sh" <<EOF
source "$HARNESS"
purlin_proof "feat" "PROOF-1" "RULE-1" pass "first"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/t.sh) >/dev/null 2>&1
  python3 -c "
import json
ids = sorted(e['id'] for e in json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))['proofs'])
assert ids == ['PROOF-1', 'PROOF-9'], ids
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "a second run replaces this script's entries and keeps the rest" test_rerun_replaces_this_script

test_finish_with_nothing_buffered() {
  local d; d="$(make_project)"
  cat > "$d/tests/t.sh" <<EOF
source "$HARNESS"
purlin_proof_finish
EOF
  (cd "$d" && bash tests/t.sh) >/dev/null 2>&1
  [[ ! -d "$d/.purlin/runtime/proofs" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "purlin_proof_finish with nothing buffered writes nothing" test_finish_with_nothing_buffered

test_retired_variable_refused() {
  local d; d="$(make_project)"
  cat > "$d/tests/t.sh" <<EOF
source "$HARNESS"
export PURLIN_PROOF_PLATFORMS=windows-2022
purlin_proof "feat" "PROOF-1" "RULE-1" pass "a case"
purlin_proof_finish
EOF
  local out
  out="$( (cd "$d" && bash tests/t.sh) 2>&1 )" && { rm -rf "$d"; return 1; }
  grep -q "@env(windows)" <<<"$out" && [[ ! -d "$d/.purlin/runtime/proofs" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "the retired PURLIN_PROOF_PLATFORMS variable is refused" test_retired_variable_refused

source "$HARNESS"
cd "$PROJECT_ROOT"
PURLIN_PROOF_TIER=e2e purlin_proof "run_script" "PROOF-56" "RULE-38" \
  "$([[ $FAIL -eq 0 ]] && echo pass || echo fail)" "shell harness suite"
purlin_proof_finish

echo ""
echo "shell proof harness: $PASS/$((PASS+FAIL)) passed"
[[ $FAIL -eq 0 ]]
