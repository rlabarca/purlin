#!/usr/bin/env bash
# E2E test: Strict Mode with Required Rules
# 2 proofs covering 2 rules — all @e2e (Level 3).
# Creates a real temp git repo with anchor + feature spec, strict mode config,
# and tests that the pre-push hook blocks when required rules lack proofs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_SCRIPT="$REAL_PROJECT_ROOT/scripts/hooks/pre-push.sh"
SERVER_PY="$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_strict_required tests ==="

# --- Helper: create a proof file in a specific spec dir ---
create_proof_file() {
  local tmpdir="$1"
  local spec_dir="$2"
  local feature="$3"
  shift 3

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

  echo "{\"tier\": \"default\", \"proofs\": $proofs}" > "$tmpdir/$spec_dir/${feature}.proofs-unit.json"
}

# --- Helper: run the hook ---
run_hook() {
  local tmpdir="$1"
  (cd "$tmpdir" && bash "$HOOK_SCRIPT" 2>&1) || return $?
}

# --- Cleanup ---
ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

# ==========================================================================
# Setup: create temp repo with anchor + feature, strict mode
# ==========================================================================
TMPDIR=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR"

mkdir -p "$TMPDIR/.purlin"
mkdir -p "$TMPDIR/specs/schema"
mkdir -p "$TMPDIR/specs/auth"
mkdir -p "$TMPDIR/scripts/mcp"

# Strict mode config
echo '{"version":"0.9.0","test_framework":"shell","spec_dir":"specs","pre_push":"strict"}' > "$TMPDIR/.purlin/config.json"

# Copy the real MCP server files
cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$TMPDIR/scripts/mcp/purlin_server.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$TMPDIR/scripts/mcp/config_engine.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$TMPDIR/scripts/mcp/__init__.py" 2>/dev/null || true

# Anchor spec: api_conventions with 2 rules
cat > "$TMPDIR/specs/schema/api_conventions.md" << 'SPEC'
# Anchor: api_conventions

> Scope: src/api/

## What it does

API conventions anchor defining cross-cutting API rules.

## Rules

- RULE-1: All API responses include Content-Type header
- RULE-2: All error responses use standard error format

## Proof

- PROOF-1 (RULE-1): Verify API responses include Content-Type @e2e
- PROOF-2 (RULE-2): Verify error responses use standard format @e2e
SPEC

# Feature spec: login with 2 own rules + Requires api_conventions
cat > "$TMPDIR/specs/auth/login.md" << 'SPEC'
# Feature: login

> Requires: api_conventions

## What it does

User login feature with authentication.

## Rules

- RULE-1: Valid credentials return 200 with session token
- RULE-2: Invalid credentials return 401 with error message

## Proof

- PROOF-1 (RULE-1): POST /login with valid creds; verify 200 and token @e2e
- PROOF-2 (RULE-2): POST /login with bad creds; verify 401 @e2e
SPEC

# Initialize git repo
(cd "$TMPDIR" && git init -q && git add -A && git commit -q -m "init")

# ==========================================================================
# Phase A — Own rules proved, required not → strict blocks
# ==========================================================================
echo "  --- Phase A: Own rules proved, required not → strict blocks ---"

# Create proofs for login's 2 own rules only
create_proof_file "$TMPDIR" "specs/auth" "login" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass"

(cd "$TMPDIR" && git add -A && git commit -q -m "add login own proofs")

output_a=""
ec_a=0
output_a=$(run_hook "$TMPDIR") || ec_a=$?

phase_a_ok=false
if [[ $ec_a -eq 1 ]] && echo "$output_a" | grep -q "strict mode"; then
  echo "    Phase A PASS: strict mode blocks (exit 1) — required rules not proved"
  phase_a_ok=true
else
  echo "    Phase A FAIL: expected exit 1 + strict mode, got exit=$ec_a"
  echo "    Output: $output_a"
fi

if $phase_a_ok; then
  purlin_proof "pre_push_hook" "PROOF-15" "RULE-8" pass "strict blocks when required rules lack proofs"
else
  purlin_proof "pre_push_hook" "PROOF-15" "RULE-8" fail "strict blocks when required rules lack proofs"
fi

# ==========================================================================
# Phase B0: all rules proved but unreceipted, strict still blocks
# ==========================================================================
echo "  --- Phase B0: All rules proved, no receipt, strict blocks ---"

# Add proofs for api_conventions (required rules)
create_proof_file "$TMPDIR" "specs/schema" "api_conventions" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass"

(cd "$TMPDIR" && git add -A && git commit -q -m "add api_conventions proofs")

output_b0=""
ec_b0=0
output_b0=$(run_hook "$TMPDIR") || ec_b0=$?

phase_b0_ok=false
if [[ $ec_b0 -eq 1 ]] && echo "$output_b0" | grep -q "strict mode"; then
  echo "    Phase B0 PASS: strict mode blocks (exit 1) with every rule proved but no receipt"
  phase_b0_ok=true
else
  echo "    Phase B0 FAIL: expected exit 1 + strict mode, got exit=$ec_b0"
  echo "    Output: $output_b0"
fi

# ==========================================================================
# Phase B: receipted through the real issuer, strict allows
# ==========================================================================
echo "  --- Phase B: Receipts issued → strict allows ---"

# Through dev/issue_receipts.py, never by hand: a hand-written receipt is free
# to drift from the shape purlin:verify writes.
python3 -c "
import sys
sys.path.insert(0, sys.argv[2])
import issue_receipts
issue_receipts.write_run_marker(sys.argv[1])
issue_receipts.main(sys.argv[1], quiet=True)
" "$TMPDIR" "$REAL_PROJECT_ROOT/dev"

output_b=""
ec_b=0
output_b=$(run_hook "$TMPDIR") || ec_b=$?

phase_b_ok=false
if [[ $ec_b -eq 0 ]]; then
  echo "    Phase B PASS: strict mode allows (exit 0) with all 4 rules proved and receipted"
  phase_b_ok=true
else
  echo "    Phase B FAIL: expected exit 0, got exit=$ec_b"
  echo "    Output: $output_b"
fi

if $phase_b0_ok && $phase_b_ok; then
  purlin_proof "pre_push_hook" "PROOF-16" "RULE-8" pass "strict blocks all-proved-unreceipted, allows once receipted"
else
  purlin_proof "pre_push_hook" "PROOF-16" "RULE-8" fail "strict blocks all-proved-unreceipted, allows once receipted (b0=$phase_b0_ok b=$phase_b_ok)"
fi

# --- Emit proof files ---
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_strict_required: 2 proofs recorded"
