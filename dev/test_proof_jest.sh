#!/usr/bin/env bash
# Tests for scripts/proof/jest_purlin.js, the Jest proof reporter.
#
# Node drives the reporter class directly: jest is not needed, and the two
# hooks the reporter exposes are its whole contract.
#
#   a title marker produces a proof entry
#   the entry carries the seven fields
#   the file is .purlin/runtime/proofs/<feature>.<tier>.json
#   a title with no marker is ignored
#   a second run replaces this file's entries
#   a skipped test writes nothing and keeps the entry it had
#   the retired :on(...) keyword is refused and names @env
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPORTER="$PROJECT_ROOT/scripts/proof/jest_purlin.js"
PASS=0
FAIL=0

if ! command -v node >/dev/null 2>&1; then
  echo "node is not installed, so this suite did not run."
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
  printf '# feat\n\n## Rules\n- RULE-1: a\n- RULE-2: b\n' > "$d/specs/a/feat.md"
  printf '// marked\n' > "$d/tests/a.test.js"
  echo "$d"
}

# drive <dir> <results-json>
drive() {
  local d="$1" results="$2"
  cat > "$d/harness.cjs" <<EOF
const path = require("path");
const Reporter = require("$REPORTER");
const r = new Reporter({rootDir: "$d"});
r.onTestResult({}, {testFilePath: path.join("$d", "tests/a.test.js"),
  testResults: $results});
r.onRunComplete();
EOF
  (cd "$d" && node harness.cjs)
}

echo "=== jest proof reporter tests ==="

test_marker_produces_an_entry() {
  local d; d="$(make_project)"
  drive "$d" '[{"title": "does it [proof:feat:PROOF-1:RULE-1:unit]", "status": "passed"},
               {"title": "breaks [proof:feat:PROOF-2:RULE-2:unit]", "status": "failed"}]' \
    >/dev/null 2>&1
  python3 -c "
import json
data = json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))
by = {e['id']: e for e in data['proofs']}
assert by['PROOF-1']['status'] == 'pass', by
assert by['PROOF-2']['status'] == 'fail', by
assert set(by['PROOF-1']) == {'feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'}, by
assert by['PROOF-1']['test_file'] == 'tests/a.test.js', by
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "a title marker produces an entry with the seven fields" test_marker_produces_an_entry

test_tier_names_the_file() {
  local d; d="$(make_project)"
  drive "$d" '[{"title": "does it [proof:feat:PROOF-1:RULE-1:e2e]", "status": "passed"}]' \
    >/dev/null 2>&1
  [[ -f "$d/.purlin/runtime/proofs/feat.e2e.json" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "the marker's tier names the file" test_tier_names_the_file

test_unmarked_title_ignored() {
  local d; d="$(make_project)"
  drive "$d" '[{"title": "no marker here", "status": "passed"}]' >/dev/null 2>&1
  [[ ! -d "$d/.purlin/runtime/proofs" ]] || [[ -z "$(ls -A "$d/.purlin/runtime/proofs")" ]]
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "a title with no marker is ignored" test_unmarked_title_ignored

test_rerun_replaces() {
  local d; d="$(make_project)"
  drive "$d" '[{"title": "a [proof:feat:PROOF-1:RULE-1]", "status": "passed"},
               {"title": "b [proof:feat:PROOF-2:RULE-2]", "status": "passed"}]' \
    >/dev/null 2>&1
  drive "$d" '[{"title": "a [proof:feat:PROOF-1:RULE-1]", "status": "passed"}]' \
    >/dev/null 2>&1
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
  mkdir -p "$d/.purlin/runtime/proofs"
  python3 -c "
import json
entries = [{'feature': 'feat', 'id': 'PROOF-2', 'rule': 'RULE-2',
            'test_file': 'tests/a.test.js', 'test_name': 'kept name',
            'status': 'pass', 'tier': 'unit'}]
json.dump({'tier': 'unit', 'proofs': entries},
          open('$d/.purlin/runtime/proofs/feat.unit.json', 'w', encoding='utf-8'), indent=2)
"
  drive "$d" '[{"title": "a [proof:feat:PROOF-1:RULE-1]", "status": "passed"},
               {"title": "b [proof:feat:PROOF-2:RULE-2]", "status": "skipped"}]' \
    >/dev/null 2>&1
  python3 -c "
import json
by = {e['id']: e for e in json.load(open('$d/.purlin/runtime/proofs/feat.unit.json', encoding='utf-8'))['proofs']}
assert by['PROOF-2']['test_name'] == 'kept name', by
assert by['PROOF-1']['status'] == 'pass', by
" >/dev/null 2>&1
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "a skipped test writes nothing and keeps the entry it had" test_skipped_keeps_its_entry

test_retired_keyword_refused() {
  local d; d="$(make_project)"
  local out
  out="$(drive "$d" '[{"title": "a [proof:feat:PROOF-1:RULE-1:unit:on(windows)]", "status": "passed"}]' 2>&1)" \
    && { rm -rf "$d"; return 1; }
  grep -q "@env(windows)" <<<"$out" && \
    { [[ ! -d "$d/.purlin/runtime/proofs" ]] || [[ -z "$(ls -A "$d/.purlin/runtime/proofs")" ]]; }
  local rc=$?; rm -rf "$d"; return $rc
}
run_test "the retired :on(...) keyword is refused and names @env" test_retired_keyword_refused

cd "$PROJECT_ROOT"

echo ""
echo "jest proof reporter: $PASS/$((PASS+FAIL)) passed"
[[ $FAIL -eq 0 ]]
