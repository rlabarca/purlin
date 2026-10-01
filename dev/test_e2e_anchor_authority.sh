#!/usr/bin/env bash
# End-to-end checks for who owns which rule when an anchor comes from an
# anchor repo.
#
# The anchor repo owns the rules in the pinned copy: a sync overwrites them.
# The project owns the rules in a local anchor of its own beside it, and a sync
# never touches those. A rule a consumer does add to the pinned copy does not
# survive the next sync. A pinned copy is written as its source holds it, and a
# field in it Purlin does not read on an anchor is warned of in the status,
# naming the source's owners as the ones to take it out.
#
# Every source is a local bare repository on disk, so nothing reaches a
# network, and every command runs against a temporary project with
# --project-root, so this repository's own specs/ is never written to.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
UPSTREAM="$REAL_PROJECT_ROOT/scripts/anchor/upstream.py"
MCP_DIR="$REAL_PROJECT_ROOT/scripts/mcp"

echo "=== anchor authority: the anchor repo's rules and the project's ==="

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

PUBLISHED_V1='# Anchor: ext_security

> Description: The security rules the shared security team publishes.
> Type: security

## Rules

- RULE-1: Every request carries an authenticated principal
- RULE-2: Secrets are read from the environment, never from a file

## Proof

- PROOF-1 (RULE-1): Call the api with no credentials; verify 401
- PROOF-2 (RULE-2): Grep the tree for secret literals; verify zero matches
'

PUBLISHED_V2='# Anchor: ext_security

> Description: The security rules the shared security team publishes.
> Type: security

## Rules

- RULE-1: Every request carries an authenticated principal
- RULE-2: Secrets are read from the environment alone
- RULE-3: Every failed sign-in is written to the log

## Proof

- PROOF-1 (RULE-1): Call the api with no credentials; verify 401
- PROOF-2 (RULE-2): Grep the tree for secret literals; verify zero matches
- PROOF-3 (RULE-3): Sign in with a wrong password; verify one log line
'

# The published anchor as a 0.9.5 anchor repo may still hold it, with a scope.
PUBLISHED_SCOPED='# Anchor: ext_security

> Description: The security rules the shared security team publishes.
> Type: security
> Scope: src/api.py

## Rules

- RULE-1: Every request carries an authenticated principal
- RULE-2: Secrets are read from the environment, never from a file

## Proof

- PROOF-1 (RULE-1): Call the api with no credentials; verify 401
- PROOF-2 (RULE-2): Grep the tree for secret literals; verify zero matches
'

LOCAL_ANCHOR='# Anchor: local_security

> Description: The security rules this project adds to the published ones.

## Rules

- RULE-1: Every input is sanitised before it reaches the database

## Proof

- PROOF-1 (RULE-1): Post a script tag in every text field; verify it is stored escaped
'

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

init_project() {
  local tmpdir="$1"
  mkdir -p "$tmpdir/.purlin" "$tmpdir/specs/_anchors"
  printf '{"version": "0.10.0", "tests": []}\n' > "$tmpdir/.purlin/config.json"
  printf '.purlin/runtime/\n' > "$tmpdir/.gitignore"
  (
    cd "$tmpdir"
    git -c init.defaultBranch=main init -q
    git config user.email "dev@purlin.local"
    git config user.name "Purlin Dev"
    git add -A
    git commit -q -m "set the project up"
  )
}

commit_project() {
  (cd "$1" && git add -A && git commit -q -m "$2")
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
  PURLIN_MCP_DIR="$MCP_DIR" PURLIN_ROOT="$1" PURLIN_SINCE="${2:-}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["PURLIN_MCP_DIR"])
from purlin import drift
print(drift.drift(os.environ["PURLIN_ROOT"],
                  since=os.environ["PURLIN_SINCE"] or None))
'
}

new_tmpdir() {
  local d
  d=$(mktemp -d)
  ALL_TMPDIRS="$ALL_TMPDIRS $d"
  echo "$d"
}

# A project with the published anchor pinned and a local anchor beside it.
# Sets BARE, PROJECT and FIRST_SHA.
build_workspace() {
  local source_path="${1:-specs/security.md}"
  local tmp
  tmp=$(new_tmpdir)
  BARE="$tmp/published.git"
  FIRST_SHA=$(create_anchor_repo "$BARE" "$source_path" "$PUBLISHED_V1")
  PROJECT="$tmp/project"
  mkdir -p "$PROJECT"
  init_project "$PROJECT"
  run_upstream "$PROJECT" add "$BARE" --path "$source_path" --name ext_security \
    >/dev/null
  printf '%s' "$LOCAL_ANCHOR" > "$PROJECT/specs/_anchors/local_security.md"
  commit_project "$PROJECT" "pin the published anchor and add the local one"
  SOURCE_PATH="$source_path"
}

# ==========================================================================
# 1. The pin goes behind when the anchor repo publishes
# ==========================================================================
echo "--- 1: the published anchor advances ---"
build_workspace
NEW_SHA=$(advance_anchor_repo "$BARE" "$SOURCE_PATH" "$PUBLISHED_V2")
drift_json=$(run_drift "$PROJECT")
result=$(PURLIN_JSON="$drift_json" PURLIN_REMOTE="$NEW_SHA" python3 -c '
import json, os
data = json.loads(os.environ["PURLIN_JSON"])
pins = data["view"]["anchors_behind"]
rows = {p["anchor"]: p for p in pins}
if "ext_security" not in rows:
    print("no pin row: %s" % json.dumps(pins))
elif "local_security" in rows:
    print("the local anchor was reported as pinned")
else:
    row = rows["ext_security"]
    print("ok" if row["status"] == "behind"
          and row["remote_sha"] == os.environ["PURLIN_REMOTE"][:7]
          else json.dumps(row))
')
ok=true
[[ "$result" == "ok" ]] || ok=false
record "drift names the pinned anchor behind and leaves the local one out" "$ok" "$result"

# ==========================================================================
# 2. Editing a spec in the project is a spec change, not a pin change
# ==========================================================================
echo "--- 2: a local spec change ---"
build_workspace
python3 - "$PROJECT/specs/_anchors/local_security.md" <<'PY'
import sys
path = sys.argv[1]
with open(path, encoding='utf-8') as handle:
    text = handle.read()
text = text.replace(
    '## Proof',
    '- RULE-2: Every response carries a request id\n\n## Proof')
text += '- PROOF-2 (RULE-2): Read the response headers; verify X-Request-Id\n'
with open(path, 'w', encoding='utf-8') as handle:
    handle.write(text)
PY
commit_project "$PROJECT" "add a local rule"
drift_json=$(run_drift "$PROJECT" 1)
result=$(PURLIN_JSON="$drift_json" python3 -c '
import json, os
data = json.loads(os.environ["PURLIN_JSON"])
pm = data["view"]
pins = data["view"]["anchors_behind"]
problems = []
if pm["rules_added"] != {"local_security": ["RULE-2"]}:
    problems.append("rules_added=%s" % json.dumps(pm["rules_added"]))
if pm["rules_changed"] or pm["rules_removed"]:
    problems.append("pm=%s" % json.dumps(pm))
if pins:
    problems.append("pins=%s" % json.dumps(pins))
print("ok" if not problems else ", ".join(problems))
')
ok=true
[[ "$result" == "ok" ]] || ok=false
record "a local rule is a spec change and moves no pin" "$ok" "$result"

# ==========================================================================
# 3. A pin behind and a local spec change surface in the same run
# ==========================================================================
echo "--- 3: both at once ---"
build_workspace
advance_anchor_repo "$BARE" "$SOURCE_PATH" "$PUBLISHED_V2" >/dev/null
python3 - "$PROJECT/specs/_anchors/local_security.md" <<'PY'
import sys
path = sys.argv[1]
with open(path, encoding='utf-8') as handle:
    text = handle.read()
text = text.replace(
    '## Proof',
    '- RULE-2: Spacing uses the four pixel grid\n\n## Proof')
text += '- PROOF-2 (RULE-2): Measure the gutters; verify each is a multiple of four\n'
with open(path, 'w', encoding='utf-8') as handle:
    handle.write(text)
PY
commit_project "$PROJECT" "add a local rule while the source is ahead"
drift_json=$(run_drift "$PROJECT" 1)
result=$(PURLIN_JSON="$drift_json" python3 -c '
import json, os
data = json.loads(os.environ["PURLIN_JSON"])
behind = any(p.get("anchor") == "ext_security" and p.get("status") == "behind"
             for p in data["view"]["anchors_behind"])
added = data["view"]["rules_added"] == {"local_security": ["RULE-2"]}
print("ok" if behind and added else "behind=%s added=%s" % (behind, added))
')
ok=true
[[ "$result" == "ok" ]] || ok=false
record "one drift run carries the pin behind and the local rule" "$ok" "$result"

# ==========================================================================
# 4. A sync overwrites the pinned copy and leaves the local anchor alone
# ==========================================================================
echo "--- 4: what a sync owns ---"
build_workspace
python3 - "$PROJECT/specs/_anchors/ext_security.md" <<'PY'
import sys
path = sys.argv[1]
with open(path, encoding='utf-8') as handle:
    text = handle.read()
text = text.replace(
    '## Proof',
    '- RULE-9: This project alone requires two-person review\n\n## Proof')
with open(path, 'w', encoding='utf-8') as handle:
    handle.write(text)
PY
commit_project "$PROJECT" "edit the pinned copy, which a sync will undo"
BEFORE_LOCAL=$(cat "$PROJECT/specs/_anchors/local_security.md")
advance_anchor_repo "$BARE" "$SOURCE_PATH" "$PUBLISHED_V2" >/dev/null
sync_out=$(run_upstream "$PROJECT" sync ext_security)

ok=true
detail="$sync_out"
grep -q 'RULE-9' "$PROJECT/specs/_anchors/ext_security.md" && {
  ok=false; detail="the local edit survived the sync"; }
grep -q '^- RULE-3: Every failed sign-in is written to the log' \
  "$PROJECT/specs/_anchors/ext_security.md" || {
  ok=false; detail="the published RULE-3 did not arrive"; }
[[ "$BEFORE_LOCAL" == "$(cat "$PROJECT/specs/_anchors/local_security.md")" ]] || {
  ok=false; detail="the local anchor was rewritten"; }
record "a sync replaces the pinned copy and never the local anchor" "$ok" "$detail"

# ==========================================================================
# 5. The anchor name is the spec name, whatever the source path is
# ==========================================================================
echo "--- 5: the name drift reports ---"
build_workspace "policies/deeply/nested/security.md"
advance_anchor_repo "$BARE" "$SOURCE_PATH" "$PUBLISHED_V2" >/dev/null
drift_json=$(run_drift "$PROJECT")
result=$(PURLIN_JSON="$drift_json" python3 -c '
import json, os
data = json.loads(os.environ["PURLIN_JSON"])
names = sorted(p.get("anchor") for p in data["view"]["anchors_behind"])
print("ok" if names == ["ext_security"] else json.dumps(names))
')
ok=true
[[ "$result" == "ok" ]] || ok=false
record "the anchor is named by its spec file, not by its source path" "$ok" "$result"

# ==========================================================================
# 6. A pin behind does not change what the rollup counts
# ==========================================================================
echo "--- 6: the rollup while the pin is behind ---"
build_workspace
advance_anchor_repo "$BARE" "$SOURCE_PATH" "$PUBLISHED_V2" >/dev/null
result=$(PURLIN_MCP_DIR="$MCP_DIR" PURLIN_ROOT="$PROJECT" python3 -c '
import os, sys
sys.path.insert(0, os.environ["PURLIN_MCP_DIR"])
from purlin import payload
data = payload.build_payload(os.environ["PURLIN_ROOT"])
rows = {f["name"]: f for f in data["features"]}
published = rows["ext_security"]["rollup"]["rules"]
local = rows["local_security"]["rollup"]["rules"]
print("ok" if published == 2 and local == 1
      else "published=%s local=%s" % (published, local))
')
ok=true
[[ "$result" == "ok" ]] || ok=false
record "the pinned anchor still counts the rules its copy holds" "$ok" "$result"

# ==========================================================================
# 7. A pinned source carrying > Scope: is copied as it is, and warned of
# ==========================================================================
echo "--- 7: a pinned source that carries > Scope: ---"
TMP7=$(new_tmpdir)
BARE7="$TMP7/published.git"
create_anchor_repo "$BARE7" "specs/security.md" "$PUBLISHED_SCOPED" >/dev/null
PROJECT7="$TMP7/project"
mkdir -p "$PROJECT7"
init_project "$PROJECT7"
run_upstream "$PROJECT7" add "$BARE7" --path specs/security.md --name ext_security \
  >/dev/null
printf '%s' "$LOCAL_ANCHOR" > "$PROJECT7/specs/_anchors/local_security.md"
commit_project "$PROJECT7" "pin a source that carries a scope"
status_out=$(run_status "$PROJECT7")
expected="ext_security: its source, $BARE7, carries > Scope:, which Purlin does not read on an anchor, so the line is read as nothing. Ask the owners of $BARE7 to take it out, then run purlin:anchor sync ext_security."
ok=true
detail="$status_out"
grep -q '^> Scope: src/api.py$' "$PROJECT7/specs/_anchors/ext_security.md" || {
  ok=false; detail="the copy did not keep its source's > Scope: line"; }
[[ "$(grep -cF "$expected" <<<"$status_out")" == "1" ]] || ok=false
grep -q 'is not read on an anchor, because' <<<"$status_out" && ok=false
grep -q 'local_security: .*not read' <<<"$status_out" && ok=false
record "the status names the source's owners once and warns of nothing else" "$ok" "$detail"

echo ""
echo "anchor authority: $PASS passed, $FAIL failed"
[[ $FAIL -eq 0 ]]
