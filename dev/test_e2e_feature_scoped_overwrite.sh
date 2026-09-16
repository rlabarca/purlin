#!/usr/bin/env bash
# End to end: the write-scoped overwrite, keyed by (feature, tier, test_file).
#
# A real temp project with two specs and two shell suites: a write for one
# feature never touches another, two test files covering one feature coexist in
# any order, and a re-run replaces only what it ran. The status table Purlin
# renders is read back at the end, so the merge is proved through the reader the
# rest of the framework uses.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HARNESS="$PROJECT_ROOT/scripts/proof/shell_purlin.sh"
MCP_DIR="$PROJECT_ROOT/scripts/mcp"

PASS=0
FAIL=0

echo "=== e2e_feature_scoped_overwrite tests ==="

ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

record() {
  local name="$1" status="$2"
  echo "  $([[ "$status" == "pass" ]] && echo PASS || echo FAIL): $name"
  [[ "$status" == "pass" ]] && PASS=$((PASS + 1)) || FAIL=$((FAIL + 1))
}

# A project with two specs and the shell framework selected.
make_repo() {
  local dir
  dir="$(mktemp -d)"
  ALL_TMPDIRS="$ALL_TMPDIRS $dir"
  mkdir -p "$dir/.purlin" "$dir/specs/auth" "$dir/tests"
  printf '{"gate":"passed","test_framework":"shell"}\n' > "$dir/.purlin/config.json"

  cat > "$dir/specs/auth/login.md" <<'SPEC'
# login

> Scope: src/

## Rules

- RULE-1: Valid credentials return 200
- RULE-2: Invalid credentials return 401

## Proof

- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200 @e2e
- PROOF-2 (RULE-2): POST /login with bad credentials; verify 401 @e2e
SPEC

  cat > "$dir/specs/auth/signup.md" <<'SPEC'
# signup

> Scope: src/

## Rules

- RULE-1: Valid registration creates an account
- RULE-2: A duplicate email returns 409

## Proof

- PROOF-1 (RULE-1): POST /signup with a fresh email; verify the account exists @e2e
- PROOF-2 (RULE-2): POST /signup twice with one email; verify 409 @e2e
SPEC

  echo "$dir"
}

# suite <dir> <script-rel> <feature> <entry...>   entry is PROOF-N|RULE-N|status
suite() {
  local dir="$1" rel="$2" feature="$3"
  shift 3
  {
    echo "source \"$HARNESS\""
    echo 'export PURLIN_PROOF_TIER=e2e'
    for entry in "$@"; do
      local proof_id rule_id status
      proof_id="$(cut -d'|' -f1 <<<"$entry")"
      rule_id="$(cut -d'|' -f2 <<<"$entry")"
      status="$(cut -d'|' -f3 <<<"$entry")"
      echo "purlin_proof \"$feature\" \"$proof_id\" \"$rule_id\" $status \"case $proof_id\""
    done
    echo 'purlin_proof_finish'
  } > "$dir/$rel"
  (cd "$dir" && bash "$rel")
}

read_ids() {
  local dir="$1" feature="$2"
  python3 -c "
import json, sys
path = '$dir/.purlin/runtime/proofs/$feature.e2e.json'
try:
    data = json.load(open(path, encoding='utf-8'))
except OSError:
    print('')
    sys.exit(0)
print(','.join(sorted('%s@%s' % (e['id'], e['test_file']) for e in data['proofs'])))
"
}

# --- PROOF-1: a write for one feature never touches another ----------------
phase_one() {
  local dir; dir="$(make_repo)"
  suite "$dir" "tests/login.test.sh" login "PROOF-1|RULE-1|pass" "PROOF-2|RULE-2|pass"
  suite "$dir" "tests/signup.test.sh" signup "PROOF-1|RULE-1|pass" "PROOF-2|RULE-2|fail"
  [[ "$(read_ids "$dir" login)" == "PROOF-1@tests/login.test.sh,PROOF-2@tests/login.test.sh" ]] || return 1
  [[ "$(read_ids "$dir" signup)" == "PROOF-1@tests/signup.test.sh,PROOF-2@tests/signup.test.sh" ]] || return 1
}
if phase_one; then
  record "a write for one feature leaves the other alone" pass
else
  record "a write for one feature leaves the other alone" fail
fi

# --- PROOF-2: two files covering one feature coexist, in any order ---------
phase_two() {
  local dir; dir="$(make_repo)"
  suite "$dir" "tests/login_a.test.sh" login "PROOF-1|RULE-1|pass"
  suite "$dir" "tests/login_b.test.sh" login "PROOF-2|RULE-2|pass"
  local forward; forward="$(read_ids "$dir" login)"

  local other; other="$(make_repo)"
  suite "$other" "tests/login_b.test.sh" login "PROOF-2|RULE-2|pass"
  suite "$other" "tests/login_a.test.sh" login "PROOF-1|RULE-1|pass"
  [[ "$forward" == "$(read_ids "$other" login)" ]] || return 1
  [[ "$forward" == "PROOF-1@tests/login_a.test.sh,PROOF-2@tests/login_b.test.sh" ]] || return 1
}
if phase_two; then
  record "two test files for one feature coexist in any order" pass
else
  record "two test files for one feature coexist in any order" fail
fi

# --- PROOF-3: a re-run replaces only what it ran, and the table reads it ---
phase_three() {
  local dir; dir="$(make_repo)"
  suite "$dir" "tests/login_a.test.sh" login "PROOF-1|RULE-1|pass"
  suite "$dir" "tests/login_b.test.sh" login "PROOF-2|RULE-2|fail"
  suite "$dir" "tests/login_b.test.sh" login "PROOF-2|RULE-2|pass"
  [[ "$(read_ids "$dir" login)" == "PROOF-1@tests/login_a.test.sh,PROOF-2@tests/login_b.test.sh" ]] || return 1
  python3 -c "
import json
data = json.load(open('$dir/.purlin/runtime/proofs/login.e2e.json', encoding='utf-8'))
by = {e['id']: e['status'] for e in data['proofs']}
assert by == {'PROOF-1': 'pass', 'PROOF-2': 'pass'}, by
" || return 1
  # The reader the rest of Purlin uses sees both entries as one feature.
  python3 -c "
import sys
sys.path.insert(0, '$MCP_DIR')
from purlin import proofs
loaded = proofs.load_proofs('$dir')
assert sorted(loaded) == ['login'], loaded
assert len(loaded['login']) == 2, loaded
statuses = proofs.status_by_proof(loaded['login'])
assert statuses[('login', 'PROOF-2')] == 'pass', statuses
" || return 1
}
if phase_three; then
  record "a re-run replaces only the file it ran" pass
else
  record "a re-run replaces only the file it ran" fail
fi

cd "$PROJECT_ROOT"

echo ""
echo "e2e feature-scoped overwrite: $PASS/$((PASS+FAIL)) passed"
[[ $FAIL -eq 0 ]]
