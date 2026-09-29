#!/usr/bin/env bash
# End to end: a feature counts its own rules, the rules it requires and the
# rules of every global anchor, and every one of them reaches its own cell.
#
# A real temp git repository, real shell tests run by `purlin_run.py --test`,
# the evidence that run writes, the real package and the real status table.
# Exits non-zero when a check failed and says what it wanted.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MCP_DIR="$PLUGIN_ROOT/scripts/mcp"
RUN="$PLUGIN_ROOT/scripts/run/purlin_run.py"

echo "=== e2e_required_rules ==="

FAILED=0
TMPDIR_E2E="$(mktemp -d)"
cleanup() { rm -rf "$TMPDIR_E2E"; }
trap cleanup EXIT

check() {
  # check <label> <expected> <actual>
  if [ "$2" = "$3" ]; then
    echo "    ok: $1"
  else
    echo "    FAIL: $1"
    echo "      wanted: $2"
    echo "      got:    $3"
    FAILED=1
  fi
}

# ── the project ───────────────────────────────────────────────────────
mkdir -p "$TMPDIR_E2E/.purlin" "$TMPDIR_E2E/specs/schema" \
         "$TMPDIR_E2E/specs/_anchors" "$TMPDIR_E2E/specs/auth" \
         "$TMPDIR_E2E/src/auth"

echo '{"gate":"passed","project_name":"e2e","tests":[{"name":"shell","run":"bash {files}","report":null,"format":"exit","files":["tests/*.test.sh"]}]}' \
  > "$TMPDIR_E2E/.purlin/config.json"
echo '.purlin/runtime/' > "$TMPDIR_E2E/.gitignore"

cat > "$TMPDIR_E2E/specs/schema/api_conventions.md" << 'SPEC'
# Anchor: api_conventions

> Scope: src/api/

## Rules

- RULE-1: Every API response carries a Content-Type header
- RULE-2: Every error response carries the fields "code" and "message"

## Proof

- PROOF-1 (RULE-1): GET /health; verify the Content-Type header is "application/json"
- PROOF-2 (RULE-2): GET /missing; verify 404 and the fields "code" and "message"
SPEC

cat > "$TMPDIR_E2E/specs/_anchors/security_no_eval.md" << 'SPEC'
# Anchor: security_no_eval

> Type: security
> Global: true

## Rules

- RULE-1: No eval() call in any source file

## Proof

- PROOF-1 (RULE-1): Grep src/ for "eval("; verify zero matches
SPEC

cat > "$TMPDIR_E2E/specs/auth/login.md" << 'SPEC'
# Feature: login

> Requires: api_conventions
> Scope: src/auth/login.js

## Rules

- RULE-1: Valid credentials return 200 with a session token
- RULE-2: Invalid credentials return 401 and the body "denied"

## Proof

- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200 and a token
- PROOF-2 (RULE-2): POST /login with a bad password; verify 401 and the body "denied"
SPEC

echo 'function login() { return 200; }' > "$TMPDIR_E2E/src/auth/login.js"

(
  cd "$TMPDIR_E2E"
  git -c init.defaultBranch=main init -q
  git config user.email 'dev@example.com'
  git config user.name 'Dev'
  git add -A
  git commit -q -m 'chore: the project under test'
)

# ── helpers ───────────────────────────────────────────────────────────
query() {
  # query <python statements; `data`, `feature` and `rules` are in scope>
  python3 - "$MCP_DIR" "$TMPDIR_E2E" "$1" << 'PY'
import sys
sys.path.insert(0, sys.argv[1])
from purlin import payload
data = payload.build_payload(sys.argv[2])
feature = next(f for f in data['features'] if f['name'] == 'login')
rules = feature['rules']


def own(rule_id):
    return [r for r in rules if r['id'] == rule_id and r['label'] == 'own'][0]


def proved():
    return len([r for r in rules if r['proofs']])


def count(word):
    return len([r for r in rules if r['cells']['passed']['word'] == word])


exec(sys.argv[3])
PY
}

write_test() {
  # write_test <name> <feature> <PROOF-ID> ...
  # One shell test under tests/ that carries one marker per proof at its top
  # and exits 0, so every proof it names passes.
  local name="$1" feature="$2"; shift 2
  mkdir -p "$TMPDIR_E2E/tests"
  {
    printf '#!/usr/bin/env bash\n'
    for proof in "$@"; do
      printf '# purlin: %s %s\n' "$feature" "$proof"
    done
    printf 'exit 0\n'
  } > "$TMPDIR_E2E/tests/$name.test.sh"
}

run_tests() {
  # The tests, run the way `purlin:test` runs them: every feature, evidence
  # written under .purlin/evidence/local/ and nothing committed. Each phase
  # checks what the run left for itself.
  python3 "$RUN" --all --test --project-root "$TMPDIR_E2E" \
    > "$TMPDIR_E2E/.run.log" 2>&1 || true
}

# ── phase A: the count ────────────────────────────────────────────────
echo "  --- phase A: own plus required plus global ---"
check "login counts five rules" "5" "$(query 'print(len(rules))')"
check "the labels split two, two and one" "own 2, required 2, global 1" \
  "$(query "print(', '.join('%s %d' % (label, len([r for r in rules if r['label'] == label])) for label in ('own', 'required', 'global')))")"
check "the required rules name their owner" "api_conventions" \
  "$(query "print(sorted({r['feature'] for r in rules if r['label'] == 'required'})[0])")"
check "the global rule names its owner" "security_no_eval" \
  "$(query "print(sorted({r['feature'] for r in rules if r['label'] == 'global'})[0])")"

# ── phase B: nothing proved yet ───────────────────────────────────────
echo "  --- phase B: with no test run ---"
check "every rule has a proof line" "5" "$(query "print(proved())")"
check "every rule's passed cell reads no test" "5" \
  "$(query "print(count('no test'))")"
check "the summary counts five rules and none passing" \
  "5 rules. 0 pass their tests." "$(query "print(data['summary']['sentence'])")"

# ── phase C: partial, then complete ───────────────────────────────────
echo "  --- phase C: the feature's own tests run ---"
write_test login login PROOF-1 PROOF-2
run_tests
check "the run wrote login's evidence" "yes" \
  "$([ -f "$TMPDIR_E2E/.purlin/evidence/local/login.json" ] && echo yes || echo no)"
check "two rules passed" "2" "$(query "print(count('passed'))")"
check "three rules still have no test" "3" "$(query "print(count('no test'))")"

echo "  --- phase D: the required and global tests run too ---"
write_test api api_conventions PROOF-1 PROOF-2
write_test security security_no_eval PROOF-1
run_tests
check "the run wrote each anchor's own evidence" "yes yes" \
  "$(for name in api_conventions security_no_eval; do [ -f "$TMPDIR_E2E/.purlin/evidence/local/$name.json" ] && printf yes || printf no; printf ' '; done | sed 's/ $//')"
check "all five rules passed" "5" "$(query "print(count('passed'))")"
check "the summary counts all five passing" "5 rules. 5 pass their tests." \
  "$(query "print(data['summary']['sentence'])")"

# ── phase E: the status table ─────────────────────────────────────────
echo "  --- phase E: the table ---"
STATUS="$(python3 -c "
import sys
sys.path.insert(0, '$MCP_DIR')
from purlin import status
print(status.sync_status('$TMPDIR_E2E'))
")"

for wanted in 'login' 'api_conventions (anchor)' 'security_no_eval (anchor)' \
              '5 rules. 5 pass their tests.'; do
  if printf '%s' "$STATUS" | grep -qF -- "$wanted"; then
    echo "    ok: the table shows '$wanted'"
  else
    echo "    FAIL: the table does not show '$wanted'"
    printf '%s\n' "$STATUS"
    FAILED=1
  fi
done

if [ "$(printf '%s' "$STATUS" | tail -1)" = 'Nothing left to do.' ]; then
  echo "    ok: the table ends with nothing left to do"
else
  echo "    FAIL: the table does not end with nothing left to do"
  printf '%s\n' "$STATUS" | tail -3
  FAILED=1
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "e2e_required_rules: every check passed"
else
  echo "e2e_required_rules: FAILED"
fi
exit "$FAILED"
