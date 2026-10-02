#!/usr/bin/env bash
# End to end: a feature counts its own rules, an anchor counts its own, each
# rule is counted once, and the status table lists the anchor under `Anchors`
# above every other spec under `Specs`.
#
# A real temp git repository, real shell tests run by `purlin_run.py --test`,
# the evidence that run writes and the real status table.
# Exits non-zero when a check failed and says what it wanted.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MCP_DIR="$PLUGIN_ROOT/scripts/mcp"
RUN="$PLUGIN_ROOT/scripts/run/purlin_run.py"

echo "=== e2e_anchor_rules ==="

FAILED=0
TMPDIR_E2E="$(mktemp -d)"
# The runs' output is kept outside the project, so the project holds only
# what a person would commit.
RUN_LOG="$(mktemp)"
cleanup() { rm -rf "$TMPDIR_E2E" "$RUN_LOG"; }
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
mkdir -p "$TMPDIR_E2E/.purlin" "$TMPDIR_E2E/specs/_anchors" \
         "$TMPDIR_E2E/specs/auth" "$TMPDIR_E2E/src/auth"

echo '{"version":"0.10.0","tests":[{"name":"shell","run":"bash {files}","report":null,"format":"exit","files":["tests/*.test.sh"]}]}' \
  > "$TMPDIR_E2E/.purlin/config.json"
echo '.purlin/runtime/' > "$TMPDIR_E2E/.gitignore"

cat > "$TMPDIR_E2E/specs/_anchors/security_no_eval.md" << 'SPEC'
# Anchor: security_no_eval

> Type: security

## Rules

- RULE-1: No eval() call in any source file

## Proof

- PROOF-1 (RULE-1): Grep every tracked file for "eval("; verify zero matches
SPEC

cat > "$TMPDIR_E2E/specs/auth/login.md" << 'SPEC'
# Feature: login

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
  # query <python statements; `data` and `spec(name)` are in scope>
  python3 - "$MCP_DIR" "$TMPDIR_E2E" "$1" << 'PY'
import sys
sys.path.insert(0, sys.argv[1])
from purlin import board, payload
data = payload.build_payload(sys.argv[2])


def spec(name):
    return next(f for f in data['features'] if f['name'] == name)


def tests(name):
    return board.tests_cell(spec(name)['rollup'])


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
    > "$RUN_LOG" 2>&1 || true
}

# ── phase A: the count ────────────────────────────────────────────────
echo "  --- phase A: each spec lists its own rules ---"
check "login lists its two rules" "login login" \
  "$(query "print(' '.join(r['feature'] for r in spec('login')['rules']))")"
check "the anchor lists its one rule" "security_no_eval" \
  "$(query "print(' '.join(r['feature'] for r in spec('security_no_eval')['rules']))")"
check "the summary counts three rules and none passing" \
  "3 rules. 0 pass their tests." "$(query "print(data['summary']['sentence'])")"

# ── phase B: the feature's tests, then the anchor's ───────────────────
echo "  --- phase B: the feature's own tests run ---"
write_test login login PROOF-1 PROOF-2
run_tests
check "login reads 2 of 2" "2 of 2" "$(query "print(tests('login'))")"
check "the anchor reads 0 of 1" "0 of 1" \
  "$(query "print(tests('security_no_eval'))")"

echo "  --- phase C: the anchor's tests run too ---"
write_test security security_no_eval PROOF-1
run_tests
check "the run wrote the anchor's own evidence" "yes" \
  "$([ -f "$TMPDIR_E2E/.purlin/evidence/local/security_no_eval.json" ] && echo yes || echo no)"
check "login still reads 2 of 2" "2 of 2" "$(query "print(tests('login'))")"
check "the anchor reads 1 of 1" "1 of 1" \
  "$(query "print(tests('security_no_eval'))")"
check "the summary counts three rules, each once" \
  "3 rules. 3 pass their tests." "$(query "print(data['summary']['sentence'])")"

# ── phase D: the status table ─────────────────────────────────────────
echo "  --- phase D: the table ---"
# The results committed, so the tests are met on the committed evidence.
python3 "$RUN" --all --test --commit --project-root "$TMPDIR_E2E" \
  > "$RUN_LOG" 2>&1 || true
STATUS="$(python3 -c "
import sys
sys.path.insert(0, '$MCP_DIR')
from purlin import status
print(status.sync_status('$TMPDIR_E2E'))
")"

# The rows under the heading rule, each cut to the spec's name: the label
# line, the anchor, the label line, the feature.
ROWS="$(printf '%s\n' "$STATUS" \
  | awk '/^─/ { inside = !inside; next } inside { print $1 }' | paste -sd ' ' -)"
check "the anchors stand above the specs" \
  "Anchors security_no_eval Specs login" "$ROWS"

check "the status says the tests are met" "Tests: met" \
  "$(printf '%s\n' "$STATUS" | grep -x 'Tests: met' || true)"
check "the table ends on the line that names the sign-off" \
  'Every rule passes its tests on the committed evidence. To sign it: purlin:sign' \
  "$(printf '%s' "$STATUS" | tail -1)"

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "e2e_anchor_rules: every check passed"
else
  echo "e2e_anchor_rules: FAILED"
fi
exit "$FAILED"
