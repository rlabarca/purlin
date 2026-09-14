#!/usr/bin/env bash
# End-to-end checks for anchors pulled from an anchor repo.
#
# Every source here is a local bare repository on disk, so nothing reaches a
# network. The checks run the real `scripts/anchor/upstream.py` and the real
# `scripts/mcp/purlin` package against temporary projects, each created with
# --project-root, so this repository's own specs/ is never written to.
#
# Run it after `bash dev/setup-external-refs.sh`, which creates the dog-food
# anchor repo the last check reads.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UPSTREAM="$REAL_PROJECT_ROOT/scripts/anchor/upstream.py"
MCP_DIR="$REAL_PROJECT_ROOT/scripts/mcp"

echo "=== external refs: anchors from an anchor repo ==="

ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

PASS=0
FAIL=0

record() {
  local name="$1" ok="$2" detail="${3:-}"
  if [[ "$ok" == "true" ]]; then
    echo "  PASS: $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $name"
    [[ -n "$detail" ]] && echo "        $detail"
    FAIL=$((FAIL + 1))
  fi
}

# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

ANCHOR_V1='# Anchor: no_eval

> Description: No dynamic code execution in production code.
> Type: security

## Rules

- RULE-1: No eval() in source files [risk: high]
- RULE-2: No exec() in source files [risk: high]

## Proof

- PROOF-1 (RULE-1): Grep src/ for "eval("; verify zero matches
- PROOF-2 (RULE-2): Grep src/ for "exec("; verify zero matches
'

ANCHOR_V2='# Anchor: no_eval

> Description: No dynamic code execution in production code.
> Type: security

## Rules

- RULE-1: No eval() in source files [risk: high]
- RULE-2: No exec() anywhere in the tree [risk: high]
- RULE-3: No compile() in source files [risk: medium]

## Proof

- PROOF-1 (RULE-1): Grep src/ for "eval("; verify zero matches
- PROOF-2 (RULE-2): Grep src/ for "exec("; verify zero matches
- PROOF-3 (RULE-3): Grep src/ for "compile("; verify zero matches
'

# Create a bare repository holding one anchor. Prints its head sha.
create_anchor_repo() {
  local bare="$1" file="$2" body="$3"
  local work="${bare}_work"
  git -c init.defaultBranch=main init --bare -q "$bare"
  git clone -q "$bare" "$work" 2>/dev/null
  mkdir -p "$(dirname "$work/$file")"
  printf '%s' "$body" > "$work/$file"
  (
    cd "$work"
    git config user.email "dev@purlin.local"
    git config user.name "Purlin Dev"
    git add -A
    git commit -q -m "publish the anchor"
    git push -q origin HEAD:refs/heads/main
    git rev-parse HEAD
  )
}

# Publish a new version of the anchor. Prints the new head sha.
advance_anchor_repo() {
  local bare="$1" file="$2" body="$3"
  local work="${bare}_work"
  printf '%s' "$body" > "$work/$file"
  (
    cd "$work"
    git add -A
    git commit -q -m "publish the next version"
    git push -q origin HEAD:refs/heads/main
    git rev-parse HEAD
  )
}

# A temporary Purlin project. It carries no scripts/: every command is run
# from this checkout with --project-root.
init_project() {
  local tmpdir="$1"
  mkdir -p "$tmpdir/.purlin" "$tmpdir/specs/_anchors"
  printf '{"gate": "tested"}\n' > "$tmpdir/.purlin/config.json"
  printf '.purlin/runtime/\n' > "$tmpdir/.gitignore"
  (
    cd "$tmpdir"
    git init -q
    git config user.email "dev@purlin.local"
    git config user.name "Purlin Dev"
    git add -A
    git commit -q -m "set the project up"
  )
}

create_feature() {
  local tmpdir="$1" name="$2" requires="$3"
  mkdir -p "$tmpdir/specs/core"
  {
    echo "# Feature: $name"
    echo ""
    [[ -n "$requires" ]] && echo "> Requires: $requires"
    echo ""
    echo "## Rules"
    echo ""
    echo "- RULE-1: The $name page loads"
    echo ""
    echo "## Proof"
    echo ""
    echo "- PROOF-1 (RULE-1): Load the page; verify it renders @e2e"
  } > "$tmpdir/specs/core/$name.md"
}

run_upstream() {
  local tmpdir="$1"
  shift
  python3 "$UPSTREAM" --project-root "$tmpdir" "$@"
}

run_status() {
  PURLIN_MCP_DIR="$MCP_DIR" PURLIN_ROOT="$1" python3 -c '
import os, sys
sys.path.insert(0, os.environ["PURLIN_MCP_DIR"])
from purlin import status
print(status.sync_status(os.environ["PURLIN_ROOT"]))
'
}

run_drift() {
  PURLIN_MCP_DIR="$MCP_DIR" PURLIN_ROOT="$1" python3 -c '
import os, sys
sys.path.insert(0, os.environ["PURLIN_MCP_DIR"])
from purlin import drift
print(drift.drift(os.environ["PURLIN_ROOT"]))
'
}

new_tmpdir() {
  local d
  d=$(mktemp -d)
  ALL_TMPDIRS="$ALL_TMPDIRS $d"
  echo "$d"
}

# ==========================================================================
# 1. add writes the local copy with > Source: and > Pinned:
# ==========================================================================
echo "--- 1: add writes the copy with its tracking fields ---"
TMP1=$(new_tmpdir)
BARE1="$TMP1/policies.git"
SHA1=$(create_anchor_repo "$BARE1" "specs/no_eval.md" "$ANCHOR_V1")
PROJECT1="$TMP1/project"
mkdir -p "$PROJECT1"
init_project "$PROJECT1"
run_upstream "$PROJECT1" add "$BARE1" --path specs/no_eval.md --name no_eval >/dev/null

COPY1="$PROJECT1/specs/_anchors/no_eval.md"
ok=true
grep -q "^> Source: $BARE1 specs/no_eval.md\$" "$COPY1" || ok=false
grep -q "^> Pinned: $SHA1\$" "$COPY1" || ok=false
grep -q '^- RULE-2: No exec() in source files \[risk: high\]$' "$COPY1" || ok=false
record "add writes Source, Pinned and the author's rules" "$ok" "$(cat "$COPY1")"

# ==========================================================================
# 2. sync --check is 0 while the pin is current and 1 once it is behind
# ==========================================================================
echo "--- 2: sync --check exit codes ---"
ok=true
detail=""
if ! run_upstream "$PROJECT1" sync --check >/dev/null; then
  ok=false
  detail="a current pin exited non-zero"
fi
SHA2=$(advance_anchor_repo "$BARE1" "specs/no_eval.md" "$ANCHOR_V2")
set +e
run_upstream "$PROJECT1" sync --check >/dev/null
code=$?
set -e
[[ $code -eq 1 ]] || { ok=false; detail="a pin behind exited $code, expected 1"; }
record "sync --check exits 0 when current and 1 when behind" "$ok" "$detail"

# ==========================================================================
# 3. sync --check --json names both shas and changes nothing
# ==========================================================================
echo "--- 3: sync --check --json ---"
set +e
json=$(run_upstream "$PROJECT1" sync --check --json)
set -e
before=$(cat "$COPY1")
result=$(PURLIN_JSON="$json" PURLIN_PINNED="$SHA1" PURLIN_REMOTE="$SHA2" python3 -c '
import json, os, sys
data = json.loads(os.environ["PURLIN_JSON"])
row = data["anchors"][0]
problems = []
if data["behind"] != 1:
    problems.append("behind=%s" % data["behind"])
if data["checked"] is not True:
    problems.append("checked=%s" % data["checked"])
if row["status"] != "behind":
    problems.append("status=%s" % row["status"])
if row["pinned"] != os.environ["PURLIN_PINNED"]:
    problems.append("pinned=%s" % row["pinned"])
if row["remote_sha"] != os.environ["PURLIN_REMOTE"]:
    problems.append("remote_sha=%s" % row["remote_sha"])
print("ok" if not problems else ", ".join(problems))
')
ok=true
[[ "$result" == "ok" ]] || ok=false
[[ "$before" == "$(cat "$COPY1")" ]] || { ok=false; result="$result; the copy was rewritten"; }
record "sync --check --json reports both shas and writes nothing" "$ok" "$result"

# ==========================================================================
# 4. sync advances the pin and names the rule delta
# ==========================================================================
echo "--- 4: sync advances the pin ---"
sync_out=$(run_upstream "$PROJECT1" sync no_eval)
ok=true
echo "$sync_out" | grep -q "RULE-2 changed, RULE-3 added" || ok=false
grep -q "^> Pinned: $SHA2\$" "$COPY1" || ok=false
grep -q '^- RULE-3: No compile() in source files \[risk: medium\]$' "$COPY1" || ok=false
record "sync names the delta and advances the pin" "$ok" "$sync_out"

# ==========================================================================
# 5. the status table names the anchor whose pin is behind
# ==========================================================================
echo "--- 5: sync_status reports a pin behind ---"
TMP5=$(new_tmpdir)
BARE5="$TMP5/policies.git"
SHA5=$(create_anchor_repo "$BARE5" "specs/no_eval.md" "$ANCHOR_V1")
PROJECT5="$TMP5/project"
mkdir -p "$PROJECT5"
init_project "$PROJECT5"
run_upstream "$PROJECT5" add "$BARE5" --path specs/no_eval.md --name no_eval >/dev/null
create_feature "$PROJECT5" "checkout" "no_eval"
(cd "$PROJECT5" && git add -A && git commit -q -m "add the anchor and a feature")
NEW5=$(advance_anchor_repo "$BARE5" "specs/no_eval.md" "$ANCHOR_V2")

status_out=$(run_status "$PROJECT5")
ok=true
echo "$status_out" | grep -q "no_eval: the pin ${SHA5:0:7} is behind its source" || ok=false
echo "$status_out" | grep -q "purlin:anchor sync no_eval" || ok=false
record "the status table names the anchor and the command to run" "$ok" "$status_out"

# ==========================================================================
# 6. a feature that requires the anchor counts its rules
# ==========================================================================
echo "--- 6: required anchor rules are counted ---"
result=$(PURLIN_MCP_DIR="$MCP_DIR" PURLIN_ROOT="$PROJECT5" python3 -c '
import os, sys
sys.path.insert(0, os.environ["PURLIN_MCP_DIR"])
from purlin import payload
data = payload.build_payload(os.environ["PURLIN_ROOT"])
rows = {f["name"]: f for f in data["features"]}
checkout = rows["checkout"]["rollup"]["rules"]
labels = sorted({r["label"] for r in rows["checkout"]["rules"]})
print("ok" if checkout == 3 and labels == ["own", "required"]
      else "rules=%s labels=%s" % (checkout, labels))
')
ok=true
[[ "$result" == "ok" ]] || ok=false
record "one own rule plus two anchor rules is three" "$ok" "$result"

# ==========================================================================
# 7. drift carries the pin, its status and the remote sha
# ==========================================================================
echo "--- 7: drift reports the pin ---"
drift_json=$(run_drift "$PROJECT5")
result=$(PURLIN_JSON="$drift_json" PURLIN_REMOTE="$NEW5" python3 -c '
import json, os
data = json.loads(os.environ["PURLIN_JSON"])
pins = data.get("pins", [])
match = [p for p in pins if p.get("anchor") == "no_eval"]
if not match:
    print("no pin row: %s" % json.dumps(pins))
else:
    row = match[0]
    remote = os.environ["PURLIN_REMOTE"][:7]
    print("ok" if row.get("status") == "behind" and row.get("remote_sha") == remote
          else json.dumps(row))
')
ok=true
[[ "$result" == "ok" ]] || ok=false
record "drift names the anchor, the status behind and the remote sha" "$ok" "$result"

# ==========================================================================
# 8. an anchor with a source and no pin is reported as unpinned
# ==========================================================================
echo "--- 8: an unpinned source ---"
TMP8=$(new_tmpdir)
BARE8="$TMP8/policies.git"
create_anchor_repo "$BARE8" "specs/no_eval.md" "$ANCHOR_V1" >/dev/null
PROJECT8="$TMP8/project"
mkdir -p "$PROJECT8"
init_project "$PROJECT8"
{
  echo "# Anchor: loose"
  echo ""
  echo "> Source: $BARE8 specs/no_eval.md"
  echo ""
  echo "## Rules"
  echo ""
  echo "- RULE-1: Something is constrained"
  echo ""
  echo "## Proof"
  echo ""
  echo "- PROOF-1 (RULE-1): Check it"
} > "$PROJECT8/specs/_anchors/loose.md"
(cd "$PROJECT8" && git add -A && git commit -q -m "add an unpinned anchor")

status_out=$(run_status "$PROJECT8")
ok=true
echo "$status_out" | grep -q "loose: names a source and no pin" || ok=false
record "an anchor with a source and no pin is named" "$ok" "$status_out"

# ==========================================================================
# 9. the dashboard data carries pinned and source_path
# ==========================================================================
echo "--- 9: the dashboard data carries the pin ---"
result=$(PURLIN_MCP_DIR="$MCP_DIR" PURLIN_ROOT="$PROJECT5" python3 -c '
import json, os, re, sys
sys.path.insert(0, os.environ["PURLIN_MCP_DIR"])
from purlin import server
root = os.environ["PURLIN_ROOT"]
server.generate_digest(root, network=False)
with open(os.path.join(root, ".purlin", "report-data.js"), encoding="utf-8") as h:
    text = h.read()
data = json.loads(re.sub(r";\s*$", "", text.split("= ", 1)[1]))
rows = {f["name"]: f for f in data["features"]}
anchor = rows["no_eval"]
feature = rows["checkout"]
problems = []
if not anchor.get("pinned"):
    problems.append("anchor pinned=%r" % anchor.get("pinned"))
if anchor.get("source_path") != "specs/no_eval.md":
    problems.append("source_path=%r" % anchor.get("source_path"))
if feature.get("pinned") is not None:
    problems.append("feature pinned=%r" % feature.get("pinned"))
print("ok" if not problems else ", ".join(problems))
')
ok=true
[[ "$result" == "ok" ]] || ok=false
record "report-data.js carries pinned and source_path, null on a feature" "$ok" "$result"

# ==========================================================================
# 10. a hostile > Source: is refused before any process starts
# ==========================================================================
echo "--- 10: a hostile source is refused ---"
TMP10=$(new_tmpdir)
PROJECT10="$TMP10/project"
mkdir -p "$PROJECT10"
init_project "$PROJECT10"
set +e
add_out=$(run_upstream "$PROJECT10" add --path a.md --name hostile -- '--upload-pack=/bin/echo' 2>&1)
code=$?
set -e
ok=true
[[ $code -eq 2 ]] || { ok=false; }
echo "$add_out" | grep -q 'begins with "-"' || ok=false
[[ -f "$PROJECT10/specs/_anchors/hostile.md" ]] && ok=false
record "a source beginning with a dash is refused and nothing is written" "$ok" "$add_out"

# ==========================================================================
# 11. the dog-food anchor repo this checkout creates is readable
# ==========================================================================
echo "--- 11: the dog-food anchor repo ---"
DOGFOOD="$REAL_PROJECT_ROOT/dev/external-refs/security-policy.git"
if [[ ! -d "$DOGFOOD" ]]; then
  echo "  SKIP: run bash dev/setup-external-refs.sh first"
else
  TMP11=$(new_tmpdir)
  PROJECT11="$TMP11/project"
  mkdir -p "$PROJECT11"
  init_project "$PROJECT11"
  run_upstream "$PROJECT11" add "$DOGFOOD" --path security_policy.md \
    --name security_no_dangerous_patterns >/dev/null
  COPY11="$PROJECT11/specs/_anchors/security_no_dangerous_patterns.md"
  ok=true
  detail=""
  grep -q '^> Pinned: [0-9a-f]\{40\}$' "$COPY11" || { ok=false; detail="no 40-character pin"; }
  grep -q '^- RULE-1: FORBIDDEN' "$COPY11" || { ok=false; detail="$detail no RULE-1"; }
  grep -qi '^> Visual-' "$COPY11" && { ok=false; detail="$detail a retired field survived"; }
  run_upstream "$PROJECT11" sync --check >/dev/null || { ok=false; detail="$detail the fresh pin read as behind"; }
  record "the dog-food repo serves a 0.10.0 anchor that pins clean" "$ok" "$detail"
fi

echo ""
echo "external refs: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
