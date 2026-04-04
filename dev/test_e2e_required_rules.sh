#!/usr/bin/env bash
# E2E test: Required Rules + Global Anchors in sync_status
# 4 proofs covering 4 rules — all @e2e (Level 3).
# Creates a real temp git repo with anchor, global anchor, and feature specs.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_PY="$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py"
SERVER_DIR="$(dirname "$SERVER_PY")"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_required_rules tests ==="

# --- Helper: create project with anchor, global anchor, and feature spec ---
create_test_project() {
  local tmpdir="$1"

  mkdir -p "$tmpdir/.purlin"
  mkdir -p "$tmpdir/specs/schema"
  mkdir -p "$tmpdir/specs/_anchors"
  mkdir -p "$tmpdir/specs/auth"
  mkdir -p "$tmpdir/scripts/mcp"

  # Create default config
  echo '{"version":"0.9.0","test_framework":"shell","spec_dir":"specs"}' > "$tmpdir/.purlin/config.json"

  # Copy the real MCP server files
  cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$tmpdir/scripts/mcp/purlin_server.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$tmpdir/scripts/mcp/config_engine.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$tmpdir/scripts/mcp/__init__.py" 2>/dev/null || true

  # Anchor spec: api_conventions with 2 rules
  cat > "$tmpdir/specs/schema/api_conventions.md" << 'SPEC'
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

  # Global anchor: security_no_eval with 1 rule
  cat > "$tmpdir/specs/_anchors/security_no_eval.md" << 'SPEC'
# Anchor: security_no_eval

> Type: security
> Global: true

## What it does

Global security anchor prohibiting eval() usage.

## Rules

- RULE-1: No eval() calls in source code

## Proof

- PROOF-1 (RULE-1): Grep source for eval(); verify zero matches
SPEC

  # Feature spec: login with 2 own rules + Requires api_conventions
  cat > "$tmpdir/specs/auth/login.md" << 'SPEC'
# Feature: login

> Requires: api_conventions
> Scope: src/auth/login.js

## What it does

User login feature with authentication.

## Rules

- RULE-1: Valid credentials return 200 with session token
- RULE-2: Invalid credentials return 401 with error message

## Proof

- PROOF-1 (RULE-1): POST /login with valid creds; verify 200 and token @e2e
- PROOF-2 (RULE-2): POST /login with bad creds; verify 401 @e2e
SPEC

  # Initialize as a git repo
  (cd "$tmpdir" && git init -q && git add -A && git commit -q -m "init")
}

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

# --- Helper: run sync_status ---
run_sync_status() {
  local tmpdir="$1"
  python3 -c "
import sys; sys.path.insert(0, '$SERVER_DIR')
from purlin_server import sync_status
print(sync_status('$tmpdir'))
"
}

# --- Cleanup ---
ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

# ==========================================================================
# Phase A — Coverage includes required + global (0/5)
# ==========================================================================
TMPDIR=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR"
create_test_project "$TMPDIR"

echo "  --- Phase A: Coverage includes required + global ---"

STATUS_A=$(run_sync_status "$TMPDIR")

# login should show 0/5 rules (2 own + 2 required + 1 global)
phase_a_ok=false
if echo "$STATUS_A" | grep -q "login: 0/5 rules proved"; then
  echo "    Phase A PASS: login shows 0/5 rules"
  phase_a_ok=true
else
  echo "    Phase A FAIL: expected 'login: 0/5 rules proved'"
  echo "    Status output:"
  echo "$STATUS_A"
fi

if $phase_a_ok; then
  purlin_proof "e2e_required_rules" "PROOF-1" "RULE-1" pass "sync_status counts required+global rules in total"
else
  purlin_proof "e2e_required_rules" "PROOF-1" "RULE-1" fail "sync_status counts required+global rules in total"
fi

# ==========================================================================
# Phase A2 — Labels (own), (required), (global)
# ==========================================================================
echo "  --- Phase A2: Labels ---"

has_own=false
has_required=false
has_global=false

# Verify labels appear on the correct rule lines (not just anywhere in output)
echo "$STATUS_A" | grep -q "RULE-1.*\(own\)\|RULE-2.*\(own\)" && has_own=true
echo "$STATUS_A" | grep -q "api_conventions/RULE.*\(required\)" && has_required=true
echo "$STATUS_A" | grep -q "security_no_eval/RULE.*\(global\)" && has_global=true

phase_a2_ok=false
if $has_own && $has_required && $has_global; then
  echo "    Phase A2 PASS: labels on correct rule lines (own=$has_own, required=$has_required, global=$has_global)"
  phase_a2_ok=true
else
  echo "    Phase A2 FAIL: missing labels on correct lines (own=$has_own, required=$has_required, global=$has_global)"
  echo "    Status output:"
  echo "$STATUS_A"
fi

if $phase_a2_ok; then
  purlin_proof "e2e_required_rules" "PROOF-2" "RULE-2" pass "sync_status labels rules as own/required/global"
else
  purlin_proof "e2e_required_rules" "PROOF-2" "RULE-2" fail "sync_status labels rules as own/required/global"
fi

# ==========================================================================
# Phase B — Partial proofs (own rules only → 2/5, NOT VERIFIED)
# ==========================================================================
echo "  --- Phase B: Partial proofs ---"

# Create proofs for login's 2 own rules
create_proof_file "$TMPDIR" "specs/auth" "login" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass"

(cd "$TMPDIR" && git add -A && git commit -q -m "add login own proofs")

STATUS_B=$(run_sync_status "$TMPDIR")

phase_b_ok=false
if echo "$STATUS_B" | grep -q "login: 2/5 rules proved"; then
  # Also verify NOT VERIFIED (no VERIFIED line for login)
  if ! echo "$STATUS_B" | grep -q "login: VERIFIED"; then
    echo "    Phase B PASS: login shows 2/5, not VERIFIED"
    phase_b_ok=true
  else
    echo "    Phase B FAIL: login shows VERIFIED but should be partial"
  fi
else
  echo "    Phase B FAIL: expected 'login: 2/5 rules proved'"
  echo "    Status output:"
  echo "$STATUS_B"
fi

if $phase_b_ok; then
  purlin_proof "e2e_required_rules" "PROOF-3" "RULE-3" pass "partial proofs show 2/5 and not VERIFIED"
else
  purlin_proof "e2e_required_rules" "PROOF-3" "RULE-3" fail "partial proofs show 2/5 and not VERIFIED"
fi

# ==========================================================================
# Phase C — Full proofs (all 5 proved → PASSING)
# ==========================================================================
echo "  --- Phase C: Full proofs ---"

# Add proofs for api_conventions (2 rules)
create_proof_file "$TMPDIR" "specs/schema" "api_conventions" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass"

# Add proofs for security_no_eval (1 rule)
create_proof_file "$TMPDIR" "specs/_anchors" "security_no_eval" \
  "PROOF-1|RULE-1|pass"

(cd "$TMPDIR" && git add -A && git commit -q -m "add required+global proofs")

STATUS_C=$(run_sync_status "$TMPDIR")

phase_c_ok=false
if echo "$STATUS_C" | grep -q "login: PASSING"; then
  # Verify 5/5 in the detail line
  if echo "$STATUS_C" | grep -q "5/5 rules proved"; then
    echo "    Phase C PASS: login shows PASSING with 5/5"
    phase_c_ok=true
  else
    echo "    Phase C FAIL: PASSING but missing 5/5 count"
    echo "    Status output:"
    echo "$STATUS_C"
  fi
else
  echo "    Phase C FAIL: expected 'login: PASSING'"
  echo "    Status output:"
  echo "$STATUS_C"
fi

if $phase_c_ok; then
  purlin_proof "e2e_required_rules" "PROOF-4" "RULE-4" pass "full proofs show 5/5 and PASSING"
else
  purlin_proof "e2e_required_rules" "PROOF-4" "RULE-4" fail "full proofs show 5/5 and PASSING"
fi

# --- Emit proof files ---
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_required_rules: 4 proofs recorded"
