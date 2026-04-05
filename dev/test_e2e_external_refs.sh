#!/usr/bin/env bash
# Tests for e2e_external_refs — 12 proofs covering 12 rules.
# Verifies external references (> Source:, > Pinned:, > Path:) work across
# sync_status, drift, report-data.js, coverage, and pre-push hook.
# Uses local bare git repos as mock external sources.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_SCRIPT="$REAL_PROJECT_ROOT/scripts/hooks/pre-push.sh"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_external_refs tests ==="

# --- Cleanup ---
ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

PASS=0
FAIL=0

# ==========================================================================
# Helper: create a bare git repo with a spec file
# Args: bare_repo_path, spec_content
# Returns: HEAD sha via stdout
# ==========================================================================
create_external_repo() {
  local bare_path="$1"
  local spec_file="$2"
  local spec_content="$3"

  git init --bare -q "$bare_path"

  # Clone, add content, push
  local work_dir="${bare_path}_work"
  git clone -q "$bare_path" "$work_dir"
  mkdir -p "$(dirname "$work_dir/$spec_file")"
  echo "$spec_content" > "$work_dir/$spec_file"
  (cd "$work_dir" && git add -A && git commit -q -m "initial spec")
  (cd "$work_dir" && git push -q origin main 2>/dev/null || git push -q origin master 2>/dev/null)

  local sha
  sha=$(git -C "$bare_path" rev-parse HEAD)
  rm -rf "$work_dir"
  echo "$sha"
}

# ==========================================================================
# Helper: advance a bare repo with a new commit
# Args: bare_repo_path, file_path, new_content
# Returns: new HEAD sha via stdout
# ==========================================================================
advance_repo() {
  local bare_path="$1"
  local spec_file="$2"
  local new_content="$3"

  local work_dir="${bare_path}_work"
  git clone -q "$bare_path" "$work_dir"
  echo "$new_content" > "$work_dir/$spec_file"
  (cd "$work_dir" && git add -A && git commit -q -m "update spec")
  (cd "$work_dir" && git push -q 2>/dev/null)

  local sha
  sha=$(git -C "$bare_path" rev-parse HEAD)
  rm -rf "$work_dir"
  echo "$sha"
}

# ==========================================================================
# Helper: create a Purlin project with external anchor(s)
# Args: project_dir
# ==========================================================================
init_project() {
  local tmpdir="$1"

  mkdir -p "$tmpdir/.purlin"
  mkdir -p "$tmpdir/specs/_anchors"
  echo '{"version":"0.9.0","test_framework":"auto","spec_dir":"specs","pre_push":"warn","report":true}' > "$tmpdir/.purlin/config.json"

  # Copy MCP server for sync_status/drift to work
  mkdir -p "$tmpdir/scripts/mcp"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$tmpdir/scripts/mcp/"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$tmpdir/scripts/mcp/"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$tmpdir/scripts/mcp/" 2>/dev/null || true

  # Git init
  (cd "$tmpdir" && git init -q && git add -A && git commit -q -m "init" --allow-empty)
}

# --- Helper: create an anchor spec ---
create_anchor() {
  local tmpdir="$1" name="$2" source_url="$3" pinned="${4:-}" source_path="${5:-}" global="${6:-false}"
  local file="$tmpdir/specs/_anchors/$name.md"
  {
    echo "# Anchor: $name"
    echo ""
    [[ -n "$source_url" ]] && echo "> Source: $source_url"
    [[ -n "$source_path" ]] && echo "> Path: $source_path"
    [[ -n "$pinned" ]] && echo "> Pinned: $pinned"
    [[ "$global" == "true" ]] && echo "> Global: true"
    echo ""
    echo "## What it does"
    echo ""
    echo "External anchor for testing."
    echo ""
    echo "## Rules"
    echo ""
    echo "- RULE-1: External constraint one"
    echo "- RULE-2: External constraint two"
    echo ""
    echo "## Proof"
    echo ""
    echo "- PROOF-1 (RULE-1): Verify constraint one"
    echo "- PROOF-2 (RULE-2): Verify constraint two"
  } > "$file"
}

# --- Helper: create a feature spec ---
create_feature() {
  local tmpdir="$1" name="$2" subdir="$3" num_rules="${4:-2}" requires="${5:-}"
  mkdir -p "$tmpdir/specs/$subdir"
  {
    echo "# Feature: $name"
    echo ""
    [[ -n "$requires" ]] && echo "> Requires: $requires"
    echo ""
    echo "## What it does"
    echo ""
    echo "Test feature."
    echo ""
    echo "## Rules"
    echo ""
    for i in $(seq 1 "$num_rules"); do
      echo "- RULE-$i: Feature rule $i"
    done
    echo ""
    echo "## Proof"
    echo ""
    for i in $(seq 1 "$num_rules"); do
      echo "- PROOF-$i (RULE-$i): Verify feature rule $i"
    done
  } > "$tmpdir/specs/$subdir/$name.md"
}

# --- Helper: create proof file ---
create_proof_file() {
  local tmpdir="$1" feature="$2" subdir="$3"
  shift 3

  local proofs="["
  local first=true
  for entry in "$@"; do
    local proof_id rule_id status
    proof_id=$(echo "$entry" | cut -d'|' -f1)
    rule_id=$(echo "$entry" | cut -d'|' -f2)
    status=$(echo "$entry" | cut -d'|' -f3)
    $first || proofs="$proofs,"
    first=false
    proofs="$proofs{\"feature\":\"$feature\",\"id\":\"$proof_id\",\"rule\":\"$rule_id\",\"test_file\":\"test.sh\",\"test_name\":\"test\",\"status\":\"$status\",\"tier\":\"unit\"}"
  done
  proofs="$proofs]"
  echo "{\"tier\":\"unit\",\"proofs\":$proofs}" > "$tmpdir/specs/$subdir/$feature.proofs-unit.json"
}

# --- Helper: run sync_status ---
run_sync_status() {
  local tmpdir="$1"
  python3 -c "
import sys, os
sys.path.insert(0, os.path.join('$tmpdir', 'scripts', 'mcp'))
from purlin_server import sync_status
print(sync_status('$tmpdir'))
" 2>/dev/null
}

# --- Helper: run drift ---
run_drift() {
  local tmpdir="$1"
  python3 -c "
import sys, os
sys.path.insert(0, os.path.join('$tmpdir', 'scripts', 'mcp'))
from purlin_server import drift
print(drift('$tmpdir'))
" 2>/dev/null
}

# --- Helper: run pre-push hook ---
run_hook() {
  local tmpdir="$1"
  (cd "$tmpdir" && bash "$HOOK_SCRIPT" 2>&1) || return $?
}


# ==========================================================================
# PROOF-1 (RULE-1): _scan_specs extracts Pinned and Path
# ==========================================================================
echo "--- PROOF-1: Pinned/Path extraction ---"
TMP1=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP1"
init_project "$TMP1"
create_anchor "$TMP1" "api_contract" "/tmp/fake.git" "abc1234def5678" "docs/spec.md"
(cd "$TMP1" && git add -A && git commit -q -m "add anchor")

p1_result=$(python3 -c "
import sys, os
sys.path.insert(0, os.path.join('$TMP1', 'scripts', 'mcp'))
from purlin_server import _scan_specs
features = _scan_specs('$TMP1')
info = features.get('api_contract', {})
pinned = info.get('pinned', '')
source_path = info.get('source_path', '')
if pinned == 'abc1234def5678' and source_path == 'docs/spec.md':
    print('pass')
else:
    print(f'fail: pinned={pinned} source_path={source_path}')
" 2>/dev/null)

if [[ "$p1_result" == "pass" ]]; then
  echo "  PASS: pinned and source_path extracted"
  purlin_proof "e2e_external_refs" "PROOF-1" "RULE-1" pass "Pinned/Path extraction correct"
  PASS=$((PASS + 1))
else
  echo "  FAIL: $p1_result"
  purlin_proof "e2e_external_refs" "PROOF-1" "RULE-1" fail "Pinned/Path extraction: $p1_result"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-2 (RULE-2): sync_status shows Source/Path/Pinned
# ==========================================================================
echo "--- PROOF-2: sync_status pinned display ---"
TMP2=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP2"
init_project "$TMP2"
create_anchor "$TMP2" "api_contract" "git@github.com:acme/api.git" "abc1234def5678" "docs/spec.md"
create_feature "$TMP2" "login" "auth" 1 "api_contract"
(cd "$TMP2" && git add -A && git commit -q -m "add specs")

output2=$(run_sync_status "$TMP2")
p2_source=false; p2_path=false; p2_pinned=false
echo "$output2" | grep -q "Source: git@github.com:acme/api.git" && p2_source=true
echo "$output2" | grep -q "Path: docs/spec.md" && p2_path=true
echo "$output2" | grep -q "Pinned: abc1234" && p2_pinned=true

if $p2_source && $p2_path && $p2_pinned; then
  echo "  PASS: Source/Path/Pinned in sync_status"
  purlin_proof "e2e_external_refs" "PROOF-2" "RULE-2" pass "sync_status shows pinned info"
  PASS=$((PASS + 1))
else
  echo "  FAIL: source=$p2_source path=$p2_path pinned=$p2_pinned"
  purlin_proof "e2e_external_refs" "PROOF-2" "RULE-2" fail "sync_status pinned display"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-3 (RULE-3): sync_status warns on unpinned
# ==========================================================================
echo "--- PROOF-3: Unpinned warning ---"
TMP3=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP3"
init_project "$TMP3"
create_anchor "$TMP3" "loose_ref" "git@github.com:acme/loose.git" "" ""
(cd "$TMP3" && git add -A && git commit -q -m "add anchor")

output3=$(run_sync_status "$TMP3")
if echo "$output3" | grep -qi "unpinned"; then
  echo "  PASS: unpinned warning shown"
  purlin_proof "e2e_external_refs" "PROOF-3" "RULE-3" pass "unpinned warning present"
  PASS=$((PASS + 1))
else
  echo "  FAIL: no unpinned warning"
  echo "  Output: $output3"
  purlin_proof "e2e_external_refs" "PROOF-3" "RULE-3" fail "no unpinned warning"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-4 (RULE-4): report-data.js includes pinned and source_path
# ==========================================================================
echo "--- PROOF-4: report-data.js fields ---"
TMP4=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP4"
init_project "$TMP4"
create_anchor "$TMP4" "api_contract" "git@github.com:acme/api.git" "abc1234def5678" "docs/spec.md"
# Need purlin-report.html for report generation
touch "$TMP4/purlin-report.html"
(cd "$TMP4" && git add -A && git commit -q -m "add specs")

run_sync_status "$TMP4" >/dev/null

p4_result=$(python3 -c "
import json, re
with open('$TMP4/.purlin/report-data.js') as f:
    text = f.read()
match = re.search(r'const PURLIN_DATA = (.+);', text, re.DOTALL)
data = json.loads(match.group(1))
anchor = [f for f in data['features'] if f['name'] == 'api_contract'][0]
if anchor.get('pinned') == 'abc1234def5678' and anchor.get('source_path') == 'docs/spec.md':
    print('pass')
else:
    print(f'fail: pinned={anchor.get(\"pinned\")} source_path={anchor.get(\"source_path\")}')
" 2>/dev/null)

if [[ "$p4_result" == "pass" ]]; then
  echo "  PASS: report-data.js has pinned/source_path"
  purlin_proof "e2e_external_refs" "PROOF-4" "RULE-4" pass "report-data.js includes pinned fields"
  PASS=$((PASS + 1))
else
  echo "  FAIL: $p4_result"
  purlin_proof "e2e_external_refs" "PROOF-4" "RULE-4" fail "report-data.js: $p4_result"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-5 (RULE-5): Coverage includes external anchor rules
# ==========================================================================
echo "--- PROOF-5: Coverage with 1 external anchor ---"
TMP5=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP5"
BARE5=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE5"
rm -rf "$BARE5"

SHA5=$(create_external_repo "$BARE5" "spec.md" "# external spec")

init_project "$TMP5"
create_anchor "$TMP5" "ext_anchor" "$BARE5" "$SHA5" "spec.md"
create_feature "$TMP5" "my_feature" "core" 1 "ext_anchor"
(cd "$TMP5" && git add -A && git commit -q -m "add specs")

output5=$(run_sync_status "$TMP5")
# Feature should have 3 rules: 1 own + 2 from anchor
if echo "$output5" | grep -q "0/3"; then
  echo "  PASS: coverage 0/3 (1 own + 2 anchor)"
  purlin_proof "e2e_external_refs" "PROOF-5" "RULE-5" pass "coverage includes anchor rules"
  PASS=$((PASS + 1))
else
  echo "  FAIL: expected 0/3 in output"
  echo "  Output: $output5"
  purlin_proof "e2e_external_refs" "PROOF-5" "RULE-5" fail "coverage count wrong"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-6 (RULE-6): Coverage with 2 external anchors
# ==========================================================================
echo "--- PROOF-6: Coverage with 2 external anchors ---"
TMP6=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP6"
BARE6A=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE6A"; rm -rf "$BARE6A"
BARE6B=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE6B"; rm -rf "$BARE6B"

SHA6A=$(create_external_repo "$BARE6A" "api.md" "# api spec")
SHA6B=$(create_external_repo "$BARE6B" "sec.md" "# sec spec")

init_project "$TMP6"
create_anchor "$TMP6" "anchor_a" "$BARE6A" "$SHA6A" "api.md"
# anchor_b with only 1 rule
cat > "$TMP6/specs/_anchors/anchor_b.md" << 'EOF'
# Anchor: anchor_b

> Source: PLACEHOLDER
> Pinned: PLACEHOLDER
> Path: sec.md

## What it does

Security anchor.

## Rules

- RULE-1: Security constraint

## Proof

- PROOF-1 (RULE-1): Verify security
EOF
sed -i.bak "s|> Source: PLACEHOLDER|> Source: $BARE6B|" "$TMP6/specs/_anchors/anchor_b.md"
sed -i.bak "s|> Pinned: PLACEHOLDER|> Pinned: $SHA6B|" "$TMP6/specs/_anchors/anchor_b.md"
rm -f "$TMP6/specs/_anchors/anchor_b.md.bak"

create_feature "$TMP6" "big_feature" "core" 2 "anchor_a, anchor_b"
(cd "$TMP6" && git add -A && git commit -q -m "add specs")

output6=$(run_sync_status "$TMP6")
# 2 own + 2 anchor_a + 1 anchor_b = 5
if echo "$output6" | grep -q "0/5"; then
  echo "  PASS: coverage 0/5 (2 own + 2 + 1)"
  purlin_proof "e2e_external_refs" "PROOF-6" "RULE-6" pass "2 external anchors counted"
  PASS=$((PASS + 1))
else
  echo "  FAIL: expected 0/5"
  echo "  Output: $output6"
  purlin_proof "e2e_external_refs" "PROOF-6" "RULE-6" fail "2 anchor coverage wrong"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-7 (RULE-7): External + local anchor together
# ==========================================================================
echo "--- PROOF-7: External + local anchor ---"
TMP7=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP7"
BARE7=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE7"; rm -rf "$BARE7"
SHA7=$(create_external_repo "$BARE7" "ext.md" "# ext")

init_project "$TMP7"
create_anchor "$TMP7" "ext_anchor" "$BARE7" "$SHA7" "ext.md"
# Local anchor (no Source)
cat > "$TMP7/specs/_anchors/local_anchor.md" << 'EOF'
# Anchor: local_anchor

## What it does

Local anchor.

## Rules

- RULE-1: Local constraint

## Proof

- PROOF-1 (RULE-1): Verify local
EOF

create_feature "$TMP7" "hybrid" "core" 1 "ext_anchor, local_anchor"
(cd "$TMP7" && git add -A && git commit -q -m "add specs")

output7=$(run_sync_status "$TMP7")
# 1 own + 2 ext_anchor + 1 local_anchor = 4
if echo "$output7" | grep -q "0/4"; then
  echo "  PASS: coverage 0/4 (1 own + 2 ext + 1 local)"
  purlin_proof "e2e_external_refs" "PROOF-7" "RULE-7" pass "external + local anchor counted"
  PASS=$((PASS + 1))
else
  echo "  FAIL: expected 0/4"
  echo "  Output: $output7"
  purlin_proof "e2e_external_refs" "PROOF-7" "RULE-7" fail "hybrid anchor coverage wrong"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-8 (RULE-8): Global external anchor auto-applies
# ==========================================================================
echo "--- PROOF-8: Global external anchor ---"
TMP8=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP8"
BARE8=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE8"; rm -rf "$BARE8"
SHA8=$(create_external_repo "$BARE8" "sec.md" "# sec")

init_project "$TMP8"
create_anchor "$TMP8" "global_ext" "$BARE8" "$SHA8" "sec.md" "true"
create_feature "$TMP8" "feature_a" "core" 1
create_feature "$TMP8" "feature_b" "core" 1
(cd "$TMP8" && git add -A && git commit -q -m "add specs")

output8=$(run_sync_status "$TMP8")
# Each feature: 1 own + 2 global = 3 rules
p8_a=false; p8_b=false
echo "$output8" | grep -A5 "feature_a" | grep -q "0/3" && p8_a=true
echo "$output8" | grep -A5 "feature_b" | grep -q "0/3" && p8_b=true

if $p8_a && $p8_b; then
  echo "  PASS: global anchor auto-applied to both features"
  purlin_proof "e2e_external_refs" "PROOF-8" "RULE-8" pass "global external anchor auto-applies"
  PASS=$((PASS + 1))
else
  echo "  FAIL: a=$p8_a b=$p8_b"
  echo "  Output: $output8"
  purlin_proof "e2e_external_refs" "PROOF-8" "RULE-8" fail "global anchor not auto-applied"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-9 (RULE-9): drift detects stale external anchor
# ==========================================================================
echo "--- PROOF-9: Drift staleness detection ---"
TMP9=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP9"
BARE9=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE9"; rm -rf "$BARE9"
SHA9=$(create_external_repo "$BARE9" "spec.md" "# original")

init_project "$TMP9"
create_anchor "$TMP9" "stale_anchor" "$BARE9" "$SHA9" "spec.md"
create_feature "$TMP9" "stale_feat" "core" 1 "stale_anchor"
(cd "$TMP9" && git add -A && git commit -q -m "add specs")

# Advance the bare repo
NEW_SHA9=$(advance_repo "$BARE9" "spec.md" "# updated spec with new rules")

drift9=$(run_drift "$TMP9")
p9_result=$(echo "$drift9" | python3 -c "
import sys, json
data = json.load(sys.stdin)
drift = data.get('external_anchor_drift', [])
for d in drift:
    if d.get('anchor') == 'stale_anchor' and d.get('status') == 'stale' and d.get('remote_sha'):
        print('pass')
        sys.exit(0)
print('fail')
" 2>/dev/null)

if [[ "$p9_result" == "pass" ]]; then
  echo "  PASS: drift detects staleness with remote SHA"
  purlin_proof "e2e_external_refs" "PROOF-9" "RULE-9" pass "drift detects stale anchor"
  PASS=$((PASS + 1))
else
  echo "  FAIL: no stale entry in drift output"
  purlin_proof "e2e_external_refs" "PROOF-9" "RULE-9" fail "drift staleness detection failed"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-10 (RULE-10): drift detects unpinned
# ==========================================================================
echo "--- PROOF-10: Drift unpinned detection ---"
TMP10=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP10"
BARE10=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE10"; rm -rf "$BARE10"
create_external_repo "$BARE10" "spec.md" "# unpinned" >/dev/null

init_project "$TMP10"
create_anchor "$TMP10" "unpinned_anchor" "$BARE10" "" "spec.md"
(cd "$TMP10" && git add -A && git commit -q -m "add anchor")

drift10=$(run_drift "$TMP10")
if echo "$drift10" | grep -q '"status": "unpinned"'; then
  echo "  PASS: drift detects unpinned"
  purlin_proof "e2e_external_refs" "PROOF-10" "RULE-10" pass "drift detects unpinned anchor"
  PASS=$((PASS + 1))
else
  echo "  FAIL: no unpinned status in drift"
  echo "  Drift: $drift10"
  purlin_proof "e2e_external_refs" "PROOF-10" "RULE-10" fail "drift unpinned detection failed"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-11 (RULE-11): Coverage progression with external anchor
# ==========================================================================
echo "--- PROOF-11: Coverage progression ---"
TMP11=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP11"
BARE11=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE11"; rm -rf "$BARE11"
SHA11=$(create_external_repo "$BARE11" "spec.md" "# ext")

init_project "$TMP11"
create_anchor "$TMP11" "ext_anchor" "$BARE11" "$SHA11" "spec.md"
create_feature "$TMP11" "progress" "core" 1 "ext_anchor"
(cd "$TMP11" && git add -A && git commit -q -m "add specs")

# Phase A: no proofs → UNTESTED
out11a=$(run_sync_status "$TMP11")
phase_a=false
echo "$out11a" | grep -q "UNTESTED" && phase_a=true

# Phase B: prove own rule only → PARTIAL
create_proof_file "$TMP11" "progress" "core" "PROOF-1|RULE-1|pass"
(cd "$TMP11" && git add -A && git commit -q -m "own proof")
out11b=$(run_sync_status "$TMP11")
phase_b=false
echo "$out11b" | grep -q "PARTIAL" && phase_b=true

# Phase C: prove anchor rules too → PASSING
create_proof_file "$TMP11" "progress" "core" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|ext_anchor/RULE-1|pass" \
  "PROOF-3|ext_anchor/RULE-2|pass"
(cd "$TMP11" && git add -A && git commit -q -m "all proofs")
out11c=$(run_sync_status "$TMP11")
phase_c=false
echo "$out11c" | grep -q "PASSING" && phase_c=true

if $phase_a && $phase_b && $phase_c; then
  echo "  PASS: UNTESTED → PARTIAL → PASSING"
  purlin_proof "e2e_external_refs" "PROOF-11" "RULE-11" pass "coverage progression correct"
  PASS=$((PASS + 1))
else
  echo "  FAIL: a=$phase_a b=$phase_b c=$phase_c"
  purlin_proof "e2e_external_refs" "PROOF-11" "RULE-11" fail "coverage progression (a=$phase_a b=$phase_b c=$phase_c)"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-12 (RULE-12): Pre-push blocks on failing anchor proof
# ==========================================================================
echo "--- PROOF-12: Pre-push enforces anchor rules ---"
TMP12=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP12"
BARE12=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE12"; rm -rf "$BARE12"
SHA12=$(create_external_repo "$BARE12" "spec.md" "# ext")

init_project "$TMP12"
create_anchor "$TMP12" "ext_anchor" "$BARE12" "$SHA12" "spec.md"
create_feature "$TMP12" "blocked" "core" 1 "ext_anchor"
# Anchor rule proof fails
create_proof_file "$TMP12" "blocked" "core" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|ext_anchor/RULE-1|fail" \
  "PROOF-3|ext_anchor/RULE-2|pass"
(cd "$TMP12" && git add -A && git commit -q -m "add failing proof")

# Install hook
cp "$HOOK_SCRIPT" "$TMP12/.git/hooks/pre-push"
chmod +x "$TMP12/.git/hooks/pre-push"

ec12=0
output12=$(run_hook "$TMP12" 2>&1) || ec12=$?

if [[ $ec12 -eq 1 ]] && echo "$output12" | grep -q "PUSH BLOCKED"; then
  echo "  PASS: pre-push blocks on failing anchor proof"
  purlin_proof "e2e_external_refs" "PROOF-12" "RULE-12" pass "pre-push blocks on anchor fail"
  PASS=$((PASS + 1))
else
  echo "  FAIL: exit=$ec12"
  echo "  Output: $output12"
  purlin_proof "e2e_external_refs" "PROOF-12" "RULE-12" fail "pre-push did not block"
  FAIL=$((FAIL + 1))
fi


# ==========================================================================
# Emit proof files
# ==========================================================================
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_external_refs: $PASS passed, $FAIL failed (12 proofs recorded)"
[[ $FAIL -eq 0 ]]
