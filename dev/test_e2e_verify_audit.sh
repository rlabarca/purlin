#!/usr/bin/env bash
# E2E test: Verify → Receipt → Audit Roundtrip
# 4 proofs covering 4 rules — all @e2e (Level 3).
# Creates a real temp git repo, computes vhash, writes receipts, and audits.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_PY="$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py"
SERVER_DIR="$(dirname "$SERVER_PY")"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_verify_audit tests ==="

# --- Helper: create a minimal Purlin project in a temp dir ---
create_test_project() {
  local tmpdir="$1"
  local num_rules="${2:-3}"

  mkdir -p "$tmpdir/.purlin"
  mkdir -p "$tmpdir/specs/auth"
  mkdir -p "$tmpdir/scripts/mcp"

  # Create default config
  echo '{"version":"0.9.0","test_framework":"shell","spec_dir":"specs"}' > "$tmpdir/.purlin/config.json"

  # Copy the real MCP server files so sync_status works
  cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$tmpdir/scripts/mcp/purlin_server.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$tmpdir/scripts/mcp/config_engine.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$tmpdir/scripts/mcp/__init__.py" 2>/dev/null || true

  # Create a spec with the requested number of rules
  {
    echo "# Feature: test_feature"
    echo ""
    echo "## What it does"
    echo ""
    echo "A test feature for verify/audit testing."
    echo ""
    echo "## Rules"
    echo ""
    for i in $(seq 1 "$num_rules"); do
      echo "- RULE-$i: Test rule $i must hold"
    done
    echo ""
    echo "## Proof"
    echo ""
    for i in $(seq 1 "$num_rules"); do
      echo "- PROOF-$i (RULE-$i): Verify rule $i holds @e2e"
    done
  } > "$tmpdir/specs/auth/test_feature.md"

  # Initialize as a git repo
  (cd "$tmpdir" && git init -q && git add -A && git commit -q -m "init")
}

# --- Helper: create a proof file ---
create_proof_file() {
  local tmpdir="$1"
  local feature="$2"
  shift 2

  local proofs="["
  local first=true
  for entry in "$@"; do
    local proof_id rule_id status
    proof_id=$(echo "$entry" | cut -d'|' -f1)
    rule_id=$(echo "$entry" | cut -d'|' -f2)
    status=$(echo "$entry" | cut -d'|' -f3)
    if [ "$first" = true ]; then
      first=false
    else
      proofs="$proofs,"
    fi
    proofs="$proofs
    {
      \"feature\": \"$feature\",
      \"id\": \"$proof_id\",
      \"rule\": \"$rule_id\",
      \"test_file\": \"dev/test_example.sh\",
      \"test_name\": \"test $proof_id\",
      \"status\": \"$status\",
      \"tier\": \"default\"
    }"
  done
  proofs="$proofs
  ]"

  local spec_dir
  spec_dir=$(find "$tmpdir/specs" -name "${feature}.md" -exec dirname {} \; | head -1)
  if [[ -z "$spec_dir" ]]; then
    spec_dir="$tmpdir/specs"
  fi

  echo "{\"tier\": \"default\", \"proofs\": $proofs}" > "$spec_dir/${feature}.proofs-unit.json"
}

# --- Helper: compute vhash using the real purlin_server logic ---
compute_vhash() {
  local tmpdir="$1"
  python3 -c "
import sys; sys.path.insert(0, '$SERVER_DIR')
from purlin_server import _scan_specs, _read_proofs, _build_coverage_rules, _collect_relevant_proofs, _compute_vhash
features = _scan_specs('$tmpdir')
proofs = _read_proofs('$tmpdir')
info = features.get('test_feature', {})
rule_entries, _ = _build_coverage_rules('test_feature', info, features)
all_rules_dict = {key: True for key, _, _, _ in rule_entries}
all_relevant = _collect_relevant_proofs('test_feature', rule_entries, proofs)
print(_compute_vhash(all_rules_dict, all_relevant))
"
}

# --- Helper: write a receipt ---
write_receipt() {
  local tmpdir="$1"
  local vhash="$2"
  python3 -c "
import json, os, sys, subprocess, datetime
sys.path.insert(0, '$SERVER_DIR')
from purlin_server import _scan_specs, _read_proofs, _build_coverage_rules, _collect_relevant_proofs

features = _scan_specs('$tmpdir')
proofs = _read_proofs('$tmpdir')
info = features.get('test_feature', {})
rule_entries, _ = _build_coverage_rules('test_feature', info, features)
all_relevant = _collect_relevant_proofs('test_feature', rule_entries, proofs)

commit = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True, cwd='$tmpdir').stdout.strip()

receipt = {
    'feature': 'test_feature',
    'vhash': '$vhash',
    'commit': commit,
    'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'rules': sorted(set(key for key, _, _, _ in rule_entries)),
    'proofs': [{'id': p['id'], 'rule': p['rule'], 'status': p['status']} for p in all_relevant]
}

spec_dir = os.path.dirname(info.get('path', 'specs/auth/test_feature.md'))
receipt_path = os.path.join('$tmpdir', spec_dir, 'test_feature.receipt.json')
with open(receipt_path, 'w') as f:
    json.dump(receipt, f, indent=2)
    f.write('\n')
print(receipt_path)
"
}

# --- Cleanup ---
ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

# ==========================================================================
# Full lifecycle test — 4 phases in one temp repo
# ==========================================================================
TMPDIR=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR"
create_test_project "$TMPDIR" 3
create_proof_file "$TMPDIR" "test_feature" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass" \
  "PROOF-3|RULE-3|pass"
(cd "$TMPDIR" && git add -A && git commit -q -m "add proofs")

# ==========================================================================
# Phase A — Verify: compute vhash, write receipt
# ==========================================================================
echo "  --- Phase A: Verify (write receipt) ---"

VHASH_A=$(compute_vhash "$TMPDIR")
RECEIPT_PATH=$(write_receipt "$TMPDIR" "$VHASH_A")
COMMIT_A=$(cd "$TMPDIR" && git rev-parse HEAD)

# Check receipt exists and has correct content
phase_a_ok=false
if [[ -f "$RECEIPT_PATH" ]]; then
  receipt_vhash=$(python3 -c "import json; print(json.load(open('$RECEIPT_PATH'))['vhash'])")
  receipt_commit=$(python3 -c "import json; print(json.load(open('$RECEIPT_PATH'))['commit'])")
  receipt_rules_count=$(python3 -c "import json; print(len(json.load(open('$RECEIPT_PATH'))['rules']))")
  receipt_proofs_count=$(python3 -c "import json; print(len(json.load(open('$RECEIPT_PATH'))['proofs']))")

  if [[ "$receipt_vhash" == "$VHASH_A" ]] && \
     [[ "$receipt_commit" == "$COMMIT_A" ]] && \
     [[ "$receipt_rules_count" == "3" ]] && \
     [[ "$receipt_proofs_count" == "3" ]]; then
    echo "    Phase A PASS: receipt written with vhash=$VHASH_A, commit=$COMMIT_A, 3 rules, 3 proofs"
    phase_a_ok=true
  else
    echo "    Phase A FAIL: receipt content mismatch"
    echo "      vhash: expected=$VHASH_A got=$receipt_vhash"
    echo "      commit: expected=$COMMIT_A got=$receipt_commit"
    echo "      rules: expected=3 got=$receipt_rules_count"
    echo "      proofs: expected=3 got=$receipt_proofs_count"
  fi
else
  echo "    Phase A FAIL: receipt file not found at $RECEIPT_PATH"
fi

if $phase_a_ok; then
  purlin_proof "e2e_verify_audit" "PROOF-1" "RULE-1" pass "receipt written with correct vhash, commit, rules, proofs"
else
  purlin_proof "e2e_verify_audit" "PROOF-1" "RULE-1" fail "receipt written with correct vhash, commit, rules, proofs"
fi

# ==========================================================================
# Phase B — Audit (match): recompute vhash, compare to receipt
# ==========================================================================
echo "  --- Phase B: Audit (match) ---"

VHASH_B=$(compute_vhash "$TMPDIR")
# Read receipt from disk and compare (not just in-memory vhash)
receipt_stored_vhash=$(python3 -c "import json; print(json.load(open('$RECEIPT_PATH'))['vhash'])")
phase_b_ok=false
if [[ "$VHASH_B" == "$receipt_stored_vhash" ]]; then
  echo "    Phase B PASS: vhash matches receipt on disk ($VHASH_B == $receipt_stored_vhash)"
  phase_b_ok=true
else
  echo "    Phase B FAIL: vhash mismatch with receipt ($VHASH_B != $receipt_stored_vhash)"
fi

if $phase_b_ok; then
  purlin_proof "e2e_verify_audit" "PROOF-2" "RULE-2" pass "audit matches when rules+proofs unchanged"
else
  purlin_proof "e2e_verify_audit" "PROOF-2" "RULE-2" fail "audit matches when rules+proofs unchanged"
fi

# ==========================================================================
# Phase C — Audit (mismatch): add RULE-4 to spec, receipt is stale
# ==========================================================================
echo "  --- Phase C: Audit (mismatch) ---"

# Add RULE-4 to the spec
python3 -c "
content = open('$TMPDIR/specs/auth/test_feature.md').read()
content = content.replace(
    '- RULE-3: Test rule 3 must hold',
    '- RULE-3: Test rule 3 must hold\n- RULE-4: Test rule 4 must hold'
)
content = content.replace(
    '- PROOF-3 (RULE-3): Verify rule 3 holds @e2e',
    '- PROOF-3 (RULE-3): Verify rule 3 holds @e2e\n- PROOF-4 (RULE-4): Verify rule 4 holds @e2e'
)
open('$TMPDIR/specs/auth/test_feature.md', 'w').write(content)
"
(cd "$TMPDIR" && git add -A && git commit -q -m "add RULE-4")

VHASH_C=$(compute_vhash "$TMPDIR")
# Read receipt from disk — stale receipt should have different vhash
receipt_stale_vhash=$(python3 -c "import json; print(json.load(open('$RECEIPT_PATH'))['vhash'])")
phase_c_ok=false
if [[ "$VHASH_C" != "$receipt_stale_vhash" ]]; then
  echo "    Phase C PASS: vhash mismatch detected with stale receipt ($VHASH_C != $receipt_stale_vhash)"
  phase_c_ok=true
else
  echo "    Phase C FAIL: vhash should differ from stale receipt ($VHASH_C == $receipt_stale_vhash)"
fi

if $phase_c_ok; then
  purlin_proof "e2e_verify_audit" "PROOF-3" "RULE-3" pass "audit detects mismatch when rule added but receipt stale"
else
  purlin_proof "e2e_verify_audit" "PROOF-3" "RULE-3" fail "audit detects mismatch when rule added but receipt stale"
fi

# ==========================================================================
# Phase D — Re-verify: add proof for RULE-4, write new receipt, audit matches
# ==========================================================================
echo "  --- Phase D: Re-verify ---"

# Add passing proof for RULE-4
create_proof_file "$TMPDIR" "test_feature" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass" \
  "PROOF-3|RULE-3|pass" \
  "PROOF-4|RULE-4|pass"
(cd "$TMPDIR" && git add -A && git commit -q -m "add RULE-4 proof")

VHASH_D=$(compute_vhash "$TMPDIR")
RECEIPT_PATH_D=$(write_receipt "$TMPDIR" "$VHASH_D")

# Verify new vhash differs from Phase A
phase_d_vhash_differs=false
if [[ "$VHASH_D" != "$VHASH_A" ]]; then
  phase_d_vhash_differs=true
fi

# Audit: read the new receipt from disk and compare
receipt_d_vhash=$(python3 -c "import json; print(json.load(open('$RECEIPT_PATH_D'))['vhash'])")
phase_d_audit_matches=false
if [[ "$receipt_d_vhash" == "$VHASH_D" ]]; then
  phase_d_audit_matches=true
fi

phase_d_ok=false
if $phase_d_vhash_differs && $phase_d_audit_matches; then
  echo "    Phase D PASS: new vhash=$VHASH_D differs from Phase A ($VHASH_A), audit matches"
  phase_d_ok=true
else
  echo "    Phase D FAIL: vhash_differs=$phase_d_vhash_differs audit_matches=$phase_d_audit_matches"
  echo "      VHASH_A=$VHASH_A VHASH_D=$VHASH_D receipt_d_vhash=$receipt_d_vhash"
fi

if $phase_d_ok; then
  purlin_proof "e2e_verify_audit" "PROOF-4" "RULE-4" pass "re-verify produces different vhash, audit matches after update"
else
  purlin_proof "e2e_verify_audit" "PROOF-4" "RULE-4" fail "re-verify produces different vhash, audit matches after update"
fi

# ==========================================================================
# Phase E — Structural-only spec flagged separately from behavioral
# ==========================================================================
echo "  --- Phase E: Structural-only vs behavioral spec separation ---"

TMPDIR_E=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR_E"

# Create project with both a behavioral and structural-only spec
mkdir -p "$TMPDIR_E/.purlin"
mkdir -p "$TMPDIR_E/specs/auth"
mkdir -p "$TMPDIR_E/specs/instructions"
mkdir -p "$TMPDIR_E/scripts/mcp"

echo '{"version":"0.9.0","test_framework":"shell","spec_dir":"specs"}' > "$TMPDIR_E/.purlin/config.json"
cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$TMPDIR_E/scripts/mcp/purlin_server.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$TMPDIR_E/scripts/mcp/config_engine.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$TMPDIR_E/scripts/mcp/__init__.py" 2>/dev/null || true

# Behavioral spec
cat > "$TMPDIR_E/specs/auth/login.md" << 'SPECEOF'
# Feature: login

## What it does

Login feature.

## Rules

- RULE-1: Returns 200 with JWT on valid credentials
- RULE-2: Rejects invalid password with 401

## Proof

- PROOF-1 (RULE-1): POST valid creds; verify 200 and JWT
- PROOF-2 (RULE-2): POST invalid; verify 401
SPECEOF

# Structural-only spec
cat > "$TMPDIR_E/specs/instructions/agent_def.md" << 'SPECEOF'
# Feature: agent_def

## What it does

Agent definition structural checks.

## Rules

- RULE-1: Verify agent.md contains ## Core Loop section
- RULE-2: Grep skill files for ## Usage heading

## Proof

- PROOF-1 (RULE-1): Grep agent.md for heading; verify section exists
- PROOF-2 (RULE-2): Grep skill files for heading; verify present
SPECEOF

# Add proof files for both
echo '{"tier":"unit","proofs":[
  {"feature":"login","id":"PROOF-1","rule":"RULE-1","test_file":"test.sh","test_name":"test1","status":"pass","tier":"unit"},
  {"feature":"login","id":"PROOF-2","rule":"RULE-2","test_file":"test.sh","test_name":"test2","status":"pass","tier":"unit"}
]}' > "$TMPDIR_E/specs/auth/login.proofs-unit.json"

echo '{"tier":"unit","proofs":[
  {"feature":"agent_def","id":"PROOF-1","rule":"RULE-1","test_file":"test.sh","test_name":"test1","status":"pass","tier":"unit"},
  {"feature":"agent_def","id":"PROOF-2","rule":"RULE-2","test_file":"test.sh","test_name":"test2","status":"pass","tier":"unit"}
]}' > "$TMPDIR_E/specs/instructions/agent_def.proofs-unit.json"

(cd "$TMPDIR_E" && git init -q && git add -A && git commit -q -m "init")

# Run sync_status and check that structural-only is flagged
SYNC_OUTPUT_E=$(python3 -c "
import sys; sys.path.insert(0, '$SERVER_DIR')
from purlin_server import sync_status
print(sync_status('$TMPDIR_E'))
")

# Check: login should be READY (not structural only), agent_def should be READY (structural only)
login_structural=$(echo "$SYNC_OUTPUT_E" | grep -c "login: READY (structural only)" || true)
login_ready=$(echo "$SYNC_OUTPUT_E" | grep -c "login: READY" || true)
agent_structural=$(echo "$SYNC_OUTPUT_E" | grep -c "agent_def: READY (structural only)" || true)

# Also verify check_spec_coverage via CLI
COVERAGE_BEHAVIORAL=$(python3 "$REAL_PROJECT_ROOT/scripts/audit/static_checks.py" --check-spec-coverage --spec-path "$TMPDIR_E/specs/auth/login.md")
COVERAGE_STRUCTURAL=$(python3 "$REAL_PROJECT_ROOT/scripts/audit/static_checks.py" --check-spec-coverage --spec-path "$TMPDIR_E/specs/instructions/agent_def.md")

BEHAV_FLAG=$(echo "$COVERAGE_BEHAVIORAL" | python3 -c "import json,sys; print(json.load(sys.stdin)['structural_only_spec'])")
STRUCT_FLAG=$(echo "$COVERAGE_STRUCTURAL" | python3 -c "import json,sys; print(json.load(sys.stdin)['structural_only_spec'])")

phase_e_ok=false
if [[ "$login_structural" == "0" ]] && \
   [[ "$login_ready" -ge "1" ]] && \
   [[ "$agent_structural" == "1" ]] && \
   [[ "$BEHAV_FLAG" == "False" ]] && \
   [[ "$STRUCT_FLAG" == "True" ]]; then
  echo "    Phase E PASS: behavioral spec=READY, structural spec=READY (structural only), coverage check agrees"
  phase_e_ok=true
else
  echo "    Phase E FAIL: login_structural=$login_structural login_ready=$login_ready agent_structural=$agent_structural"
  echo "      check_spec_coverage: behavioral=$BEHAV_FLAG structural=$STRUCT_FLAG"
fi

if $phase_e_ok; then
  purlin_proof "e2e_verify_audit" "PROOF-5" "RULE-5" pass "structural-only spec flagged separately from behavioral spec"
else
  purlin_proof "e2e_verify_audit" "PROOF-5" "RULE-5" fail "structural-only spec not flagged correctly"
fi

# --- Emit proof files ---
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_verify_audit: 5 proofs recorded"
