#!/usr/bin/env bash
# End to end: a feature counts its own rules, the rules it requires and the
# rules of every global anchor, and each one reaches its own state.
#
# A real temp git repository, the real package, the real status table. Exits
# non-zero on the first failed check and says what it wanted.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MCP_DIR="$PLUGIN_ROOT/scripts/mcp"

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

echo '{"gate":"tested","test_framework":"shell","project_name":"e2e"}' \
  > "$TMPDIR_E2E/.purlin/config.json"
echo '.purlin/runtime/' > "$TMPDIR_E2E/.gitignore"

cat > "$TMPDIR_E2E/specs/schema/api_conventions.md" << 'SPEC'
# Anchor: api_conventions

> Scope: src/api/

## Rules

- RULE-1: Every API response carries a Content-Type header
- RULE-2: Every error response carries the fields "code" and "message"

## Proof

- PROOF-1 (RULE-1): GET /health; verify the Content-Type header is "application/json" @e2e
- PROOF-2 (RULE-2): GET /missing; verify 404 and the fields "code" and "message" @e2e
SPEC

cat > "$TMPDIR_E2E/specs/_anchors/security_no_eval.md" << 'SPEC'
# Anchor: security_no_eval

> Type: security
> Global: true

## Rules

- RULE-1: No eval() call in any source file [risk: high] [origin: qa]

## Proof

- PROOF-1 (RULE-1): Grep src/ for "eval("; verify zero matches
SPEC

cat > "$TMPDIR_E2E/specs/auth/login.md" << 'SPEC'
# Feature: login

> Requires: api_conventions
> Scope: src/auth/login.js

## Rules

- RULE-1: Valid credentials return 200 with a session token [risk: high] [origin: pm]
- RULE-2: Invalid credentials return 401 and the body "denied"

## Proof

- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200 and a token @e2e
- PROOF-2 (RULE-2): POST /login with a bad password; verify 401 and the body "denied" @e2e
SPEC

echo 'function login() { return 200; }' > "$TMPDIR_E2E/src/auth/login.js"

(
  cd "$TMPDIR_E2E"
  git init -q
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


def count(state):
    return len([r for r in rules if r['state'] == state])


exec(sys.argv[3])
PY
}

write_proofs() {
  # write_proofs <feature> <PROOF-ID:RULE-ID> ...
  local feature="$1"; shift
  local dir="$TMPDIR_E2E/.purlin/runtime/proofs"
  mkdir -p "$dir"
  {
    printf '{"tier": "unit", "proofs": ['
    local first=1
    for pair in "$@"; do
      local pid="${pair%%:*}"
      local rid="${pair##*:}"
      [ $first -eq 1 ] || printf ','
      first=0
      printf '{"feature":"%s","id":"%s","rule":"%s","test_file":"dev/test_e2e_required_rules.sh","test_name":"%s","status":"pass","tier":"unit"}' \
        "$feature" "$pid" "$rid" "$pid"
    done
    printf ']}'
  } > "$dir/$feature.unit.json"
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

# ── phase B: the tags ─────────────────────────────────────────────────
echo "  --- phase B: the rule tags ---"
check "RULE-1 is high risk, owned by the PM" "high pm" \
  "$(query "print(own('RULE-1')['risk'], own('RULE-1')['origin'])")"
check "RULE-2 takes the defaults" "low eng" \
  "$(query "print(own('RULE-2')['risk'], own('RULE-2')['origin'])")"
check "the tags are stripped from the text" "Valid credentials return 200 with a session token" \
  "$(query "print(own('RULE-1')['text'])")"

# ── phase C: nothing proved yet ───────────────────────────────────────
echo "  --- phase C: with no test run ---"
check "every rule is Proof ready" "5" "$(query "print(count('Proof ready'))")"
check "the feature's lowest state is Proof ready" "Proof ready" \
  "$(query "print(feature['rollup']['lowest_state'])")"

# ── phase D: partial, then complete ───────────────────────────────────
echo "  --- phase D: the feature's own tests run ---"
write_proofs login PROOF-1:RULE-1 PROOF-2:RULE-2
check "two rules are Tested" "2" "$(query "print(count('Tested'))")"
check "the lowest state is still Proof ready" "Proof ready" \
  "$(query "print(feature['rollup']['lowest_state'])")"

echo "  --- phase E: the required and global tests run too ---"
write_proofs api_conventions PROOF-1:RULE-1 PROOF-2:RULE-2
write_proofs security_no_eval PROOF-1:RULE-1
check "all five rules are Tested" "5" "$(query "print(count('Tested'))")"
check "the lowest state is Tested" "Tested" \
  "$(query "print(feature['rollup']['lowest_state'])")"

# ── phase F: the status table ─────────────────────────────────────────
echo "  --- phase F: the table ---"
STATUS="$(python3 -c "
import sys
sys.path.insert(0, '$MCP_DIR')
from purlin import status
print(status.sync_status('$TMPDIR_E2E'))
")"

for wanted in 'login' 'api_conventions (anchor)' 'security_no_eval (anchor)' \
              'Lowest state' 'Tested 5'; do
  if printf '%s' "$STATUS" | grep -qF -- "$wanted"; then
    echo "    ok: the table shows '$wanted'"
  else
    echo "    FAIL: the table does not show '$wanted'"
    printf '%s\n' "$STATUS"
    FAILED=1
  fi
done

if printf '%s' "$STATUS" | tail -1 | grep -q '^→'; then
  echo "    ok: the table ends with a next step"
else
  echo "    FAIL: the table does not end with a next step"
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
