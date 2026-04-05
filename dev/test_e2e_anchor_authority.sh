#!/usr/bin/env bash
# Tests for e2e_anchor_authority — 5 proofs covering 5 rules.
# Verifies drift correctly detects when an externally-referenced anchor
# with local rules has its external source advance, and that both
# external staleness and local spec changes are surfaced together.
# Uses local bare git repos as mock external sources.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load proof harness
export PURLIN_PROOF_TIER="e2e"
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_anchor_authority tests ==="

# --- Cleanup ---
ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

PASS=0
FAIL=0

# ==========================================================================
# Helper: create a bare git repo with a spec file
# Args: bare_repo_path, spec_file, spec_content
# Returns: HEAD sha via stdout
# ==========================================================================
create_external_repo() {
  local bare_path="$1"
  local spec_file="$2"
  local spec_content="$3"

  git init --bare -q "$bare_path"

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
# Helper: create a Purlin project
# Args: project_dir
# ==========================================================================
init_project() {
  local tmpdir="$1"

  mkdir -p "$tmpdir/.purlin"
  mkdir -p "$tmpdir/specs/_anchors"
  echo '{"version":"0.9.0","test_framework":"auto","spec_dir":"specs","pre_push":"warn","report":true}' > "$tmpdir/.purlin/config.json"

  # Copy MCP server for drift to work
  mkdir -p "$tmpdir/scripts/mcp"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$tmpdir/scripts/mcp/"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$tmpdir/scripts/mcp/"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$tmpdir/scripts/mcp/" 2>/dev/null || true

  # Git init
  (cd "$tmpdir" && git init -q && git add -A && git commit -q -m "init" --allow-empty)
}

# ==========================================================================
# Helper: create an externally-referenced anchor with local rules
# Args: tmpdir, name, source_url, pinned, source_path, num_external_rules, local_rules...
# Writes the anchor with num_external_rules "external" rules + extra local rules
# ==========================================================================
create_mixed_anchor() {
  local tmpdir="$1" name="$2" source_url="$3" pinned="$4" source_path="$5" num_ext="$6"
  shift 6
  local local_rules=("$@")

  local file="$tmpdir/specs/_anchors/$name.md"
  local rule_num=1
  local proof_num=1
  {
    echo "# Anchor: $name"
    echo ""
    echo "> Source: $source_url"
    [[ -n "$source_path" ]] && echo "> Path: $source_path"
    [[ -n "$pinned" ]] && echo "> Pinned: $pinned"
    echo ""
    echo "## What it does"
    echo ""
    echo "Mixed anchor: external rules from source + local rules."
    echo ""
    echo "## Rules"
    echo ""
    for i in $(seq 1 "$num_ext"); do
      echo "- RULE-$rule_num: External constraint $i from source"
      rule_num=$((rule_num + 1))
    done
    for lr in "${local_rules[@]}"; do
      echo "- RULE-$rule_num: $lr"
      rule_num=$((rule_num + 1))
    done
    echo ""
    echo "## Proof"
    echo ""
    local total=$((rule_num - 1))
    for i in $(seq 1 "$total"); do
      echo "- PROOF-$i (RULE-$i): Verify rule $i"
    done
  } > "$file"
}

# --- Helper: create a feature spec ---
create_feature() {
  local tmpdir="$1" name="$2" subdir="$3" num_rules="${4:-1}" requires="${5:-}"
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


# ==========================================================================
# PROOF-1 (RULE-1): Mixed anchor staleness detection
# External anchor with local rules — external source advances → stale
# ==========================================================================
echo "--- PROOF-1: Mixed anchor staleness detection ---"
TMP1=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP1"
BARE1=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE1"; rm -rf "$BARE1"

SHA1=$(create_external_repo "$BARE1" "security.md" "# external security policy v1")

init_project "$TMP1"
create_mixed_anchor "$TMP1" "ext_security" "$BARE1" "$SHA1" "security.md" 2 \
  "Local rule: all inputs must be sanitized"
(cd "$TMP1" && git add -A && git commit -q -m "add mixed anchor")

# Advance external source (simulates external team publishing new rules)
NEW_SHA1=$(advance_repo "$BARE1" "security.md" "# external security policy v2 — new rules added")

drift1=$(run_drift "$TMP1")
p1_result=$(echo "$drift1" | python3 -c "
import sys, json
data = json.load(sys.stdin)
drift_entries = data.get('external_anchor_drift', [])
for d in drift_entries:
    if (d.get('anchor') == 'ext_security'
        and d.get('status') == 'stale'
        and d.get('remote_sha')):
        print('pass')
        sys.exit(0)
print('fail: ' + json.dumps(drift_entries))
" 2>/dev/null)

if [[ "$p1_result" == "pass" ]]; then
  echo "  PASS: mixed anchor detected as stale"
  purlin_proof "e2e_anchor_authority" "PROOF-1" "RULE-1" pass "mixed anchor staleness detected"
  PASS=$((PASS + 1))
else
  echo "  FAIL: $p1_result"
  purlin_proof "e2e_anchor_authority" "PROOF-1" "RULE-1" fail "mixed anchor staleness: $p1_result"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-2 (RULE-2): Local anchor modification → CHANGED_SPECS
# ==========================================================================
echo "--- PROOF-2: Local anchor modification classified as CHANGED_SPECS ---"
TMP2=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP2"
BARE2=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE2"; rm -rf "$BARE2"

SHA2=$(create_external_repo "$BARE2" "api.md" "# api contract v1")

init_project "$TMP2"
create_mixed_anchor "$TMP2" "api_contract" "$BARE2" "$SHA2" "api.md" 2 \
  "Local rule: rate limiting on all endpoints"
(cd "$TMP2" && git add -A && git commit -q -m "add anchor")

# Modify the local anchor file: add a new local rule
cat >> "$TMP2/specs/_anchors/api_contract.md" << 'EOF'

- RULE-4: Local rule: all responses include X-Request-Id header
EOF
# Also add the proof entry
sed -i.bak 's/## Proof/## Proof\n/' "$TMP2/specs/_anchors/api_contract.md"
rm -f "$TMP2/specs/_anchors/api_contract.md.bak"
echo "- PROOF-4 (RULE-4): Verify X-Request-Id header" >> "$TMP2/specs/_anchors/api_contract.md"
(cd "$TMP2" && git add -A && git commit -q -m "add local rule to anchor")

drift2=$(run_drift "$TMP2")
p2_result=$(echo "$drift2" | python3 -c "
import sys, json
data = json.load(sys.stdin)
files = data.get('files', [])
for f in files:
    if 'api_contract' in f.get('path', '') and f.get('category') == 'CHANGED_SPECS':
        print('pass')
        sys.exit(0)
print('fail: ' + json.dumps([f for f in files if 'api_contract' in f.get('path', '')]))
" 2>/dev/null)

if [[ "$p2_result" == "pass" ]]; then
  echo "  PASS: anchor file classified as CHANGED_SPECS"
  purlin_proof "e2e_anchor_authority" "PROOF-2" "RULE-2" pass "local anchor mod → CHANGED_SPECS"
  PASS=$((PASS + 1))
else
  echo "  FAIL: $p2_result"
  purlin_proof "e2e_anchor_authority" "PROOF-2" "RULE-2" fail "anchor classification: $p2_result"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-3 (RULE-3): Simultaneous external staleness + local spec change
# ==========================================================================
echo "--- PROOF-3: External staleness AND local spec change surfaced together ---"
TMP3=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP3"
BARE3=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE3"; rm -rf "$BARE3"

SHA3=$(create_external_repo "$BARE3" "design.md" "# design system v1")

init_project "$TMP3"
create_mixed_anchor "$TMP3" "design_tokens" "$BARE3" "$SHA3" "design.md" 2 \
  "Local rule: font sizes use rem units"
(cd "$TMP3" && git add -A && git commit -q -m "add anchor")

# Advance external source (external team publishes new rules)
advance_repo "$BARE3" "design.md" "# design system v2 — colors updated" >/dev/null

# Also modify local anchor (add new local rule)
cat >> "$TMP3/specs/_anchors/design_tokens.md" << 'EOF'

- RULE-4: Local rule: spacing uses 4px grid
EOF
echo "- PROOF-4 (RULE-4): Verify 4px grid spacing" >> "$TMP3/specs/_anchors/design_tokens.md"
(cd "$TMP3" && git add -A && git commit -q -m "add local design rule")

drift3=$(run_drift "$TMP3")
p3_result=$(echo "$drift3" | python3 -c "
import sys, json
data = json.load(sys.stdin)

# Check external_anchor_drift for stale
stale_found = False
for d in data.get('external_anchor_drift', []):
    if d.get('anchor') == 'design_tokens' and d.get('status') == 'stale':
        stale_found = True
        break

# Check spec_changes for new rule on the anchor
spec_change_found = False
for sc in data.get('spec_changes', []):
    if sc.get('spec') == 'design_tokens' and sc.get('new_rules'):
        spec_change_found = True
        break

if stale_found and spec_change_found:
    print('pass')
else:
    print(f'fail: stale={stale_found} spec_change={spec_change_found}')
" 2>/dev/null)

if [[ "$p3_result" == "pass" ]]; then
  echo "  PASS: both external staleness and local spec change surfaced"
  purlin_proof "e2e_anchor_authority" "PROOF-3" "RULE-3" pass "dual detection: stale + spec change"
  PASS=$((PASS + 1))
else
  echo "  FAIL: $p3_result"
  purlin_proof "e2e_anchor_authority" "PROOF-3" "RULE-3" fail "dual detection: $p3_result"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-4 (RULE-4): proof_status totals correct despite staleness
# ==========================================================================
echo "--- PROOF-4: proof_status totals correct despite staleness ---"
TMP4=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP4"
BARE4=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE4"; rm -rf "$BARE4"

SHA4=$(create_external_repo "$BARE4" "contract.md" "# contract v1")

init_project "$TMP4"
# Anchor: 2 external rules + 1 local rule = 3 anchor rules
create_mixed_anchor "$TMP4" "ext_contract" "$BARE4" "$SHA4" "contract.md" 2 \
  "Local rule: all errors use RFC 7807"
# Feature: 1 own rule + requires ext_contract (3 anchor rules) = 4 total
create_feature "$TMP4" "checkout" "core" 1 "ext_contract"
# Proofs: all 4 rules pass
create_proof_file "$TMP4" "checkout" "core" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|ext_contract/RULE-1|pass" \
  "PROOF-3|ext_contract/RULE-2|pass" \
  "PROOF-4|ext_contract/RULE-3|pass"
(cd "$TMP4" && git add -A && git commit -q -m "add specs and proofs")

# Advance external source — makes anchor stale
advance_repo "$BARE4" "contract.md" "# contract v2 — breaking change" >/dev/null

drift4=$(run_drift "$TMP4")
p4_result=$(echo "$drift4" | python3 -c "
import sys, json
data = json.load(sys.stdin)

# Verify anchor is stale
stale = any(
    d.get('anchor') == 'ext_contract' and d.get('status') == 'stale'
    for d in data.get('external_anchor_drift', [])
)

# Verify proof_status for checkout: total=4, proved=4
ps = data.get('proof_status', {}).get('checkout', {})
total = ps.get('total', 0)
proved = ps.get('proved', 0)

if stale and total == 4 and proved == 4:
    print('pass')
else:
    print(f'fail: stale={stale} total={total} proved={proved}')
" 2>/dev/null)

if [[ "$p4_result" == "pass" ]]; then
  echo "  PASS: proof_status 4/4 despite stale anchor"
  purlin_proof "e2e_anchor_authority" "PROOF-4" "RULE-4" pass "proof_status correct during staleness"
  PASS=$((PASS + 1))
else
  echo "  FAIL: $p4_result"
  purlin_proof "e2e_anchor_authority" "PROOF-4" "RULE-4" fail "proof_status: $p4_result"
  FAIL=$((FAIL + 1))
fi

# ==========================================================================
# PROOF-5 (RULE-5): anchor name in external_anchor_drift matches spec name
# ==========================================================================
echo "--- PROOF-5: Anchor name matches spec name in drift output ---"
TMP5=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $TMP5"
BARE5=$(mktemp -d); ALL_TMPDIRS="$ALL_TMPDIRS $BARE5"; rm -rf "$BARE5"

SHA5=$(create_external_repo "$BARE5" "deeply/nested/policy.md" "# policy v1")

init_project "$TMP5"
create_mixed_anchor "$TMP5" "local_security" "$BARE5" "$SHA5" "deeply/nested/policy.md" 1 \
  "Local rule: audit logging required"
(cd "$TMP5" && git add -A && git commit -q -m "add anchor")

# Advance external source
advance_repo "$BARE5" "deeply/nested/policy.md" "# policy v2 — updated" >/dev/null

drift5=$(run_drift "$TMP5")
p5_result=$(echo "$drift5" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for d in data.get('external_anchor_drift', []):
    if d.get('anchor') == 'local_security' and d.get('status') == 'stale':
        print('pass')
        sys.exit(0)
print('fail: ' + json.dumps(data.get('external_anchor_drift', [])))
" 2>/dev/null)

if [[ "$p5_result" == "pass" ]]; then
  echo "  PASS: anchor field is 'local_security' (spec name)"
  purlin_proof "e2e_anchor_authority" "PROOF-5" "RULE-5" pass "anchor name matches spec name"
  PASS=$((PASS + 1))
else
  echo "  FAIL: $p5_result"
  purlin_proof "e2e_anchor_authority" "PROOF-5" "RULE-5" fail "anchor name: $p5_result"
  FAIL=$((FAIL + 1))
fi


# ==========================================================================
# Emit proof files
# ==========================================================================
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_anchor_authority: $PASS passed, $FAIL failed (5 proofs recorded)"
[[ $FAIL -eq 0 ]]
