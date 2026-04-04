#!/usr/bin/env bash
# E2E test: Feature-Scoped Overwrite
# 3 proofs covering 3 rules — all @e2e (Level 3).
# Creates a real temp git repo with 2 specs and tests that proof file writes
# for one feature don't affect another, and that re-runs correctly purge old entries.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_PY="$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py"
SERVER_DIR="$(dirname "$SERVER_PY")"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_feature_scoped_overwrite tests ==="

# --- Helper: run sync_status ---
run_sync_status() {
  local tmpdir="$1"
  python3 -c "
import sys; sys.path.insert(0, '$SERVER_DIR')
from purlin_server import sync_status
print(sync_status('$tmpdir'))
"
}

# --- Helper: write a proof file directly ---
write_proof_file() {
  local path="$1"
  local feature="$2"
  shift 2
  # Remaining args are "PROOF-N|RULE-N|status" entries

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

  echo "{\"tier\": \"default\", \"proofs\": $proofs}" > "$path"
}

# --- Cleanup ---
ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

# ==========================================================================
# Setup: create temp repo with 2 specs (login + signup)
# ==========================================================================
TMPDIR=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR"

mkdir -p "$TMPDIR/.purlin"
mkdir -p "$TMPDIR/specs/auth"
mkdir -p "$TMPDIR/scripts/mcp"

# Create default config
echo '{"version":"0.9.0","test_framework":"shell","spec_dir":"specs"}' > "$TMPDIR/.purlin/config.json"

# Copy the real MCP server files
cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$TMPDIR/scripts/mcp/purlin_server.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$TMPDIR/scripts/mcp/config_engine.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$TMPDIR/scripts/mcp/__init__.py" 2>/dev/null || true

# login spec: 2 rules
cat > "$TMPDIR/specs/auth/login.md" << 'SPEC'
# Feature: login

## What it does

User login feature.

## Rules

- RULE-1: Valid credentials return 200
- RULE-2: Invalid credentials return 401

## Proof

- PROOF-1 (RULE-1): POST /login with valid creds; verify 200 @e2e
- PROOF-2 (RULE-2): POST /login with bad creds; verify 401 @e2e
SPEC

# signup spec: 2 rules
cat > "$TMPDIR/specs/auth/signup.md" << 'SPEC'
# Feature: signup

## What it does

User signup feature.

## Rules

- RULE-1: Valid registration creates account
- RULE-2: Duplicate email returns 409

## Proof

- PROOF-1 (RULE-1): POST /signup with new email; verify 201 @e2e
- PROOF-2 (RULE-2): POST /signup with existing email; verify 409 @e2e
SPEC

# Initialize git repo
(cd "$TMPDIR" && git init -q && git add -A && git commit -q -m "init")

# ==========================================================================
# Phase A — Write login proofs, then signup proofs → both PASSING
# ==========================================================================
echo "  --- Phase A: Write proofs for both features ---"

# Write login proofs first
write_proof_file "$TMPDIR/specs/auth/login.proofs-unit.json" "login" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass"

# Verify signup proof file does not exist yet (non-interference)
signup_file="$TMPDIR/specs/auth/signup.proofs-unit.json"
signup_untouched=true
if [[ -f "$signup_file" ]]; then
  echo "    WARNING: signup proof file exists before writing signup proofs"
  signup_untouched=false
fi

# Now write signup proofs (separate file)
write_proof_file "$signup_file" "signup" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass"

(cd "$TMPDIR" && git add -A && git commit -q -m "add proofs for both features")

STATUS_A=$(run_sync_status "$TMPDIR")

login_ready=false
signup_ready=false
echo "$STATUS_A" | grep -q "login: PASSING" && login_ready=true
echo "$STATUS_A" | grep -q "signup: PASSING" && signup_ready=true

phase_a_ok=false
if $login_ready && $signup_ready && $signup_untouched; then
  echo "    Phase A PASS: both PASSING, signup untouched before its own write"
  phase_a_ok=true
else
  echo "    Phase A FAIL: login_ready=$login_ready signup_ready=$signup_ready signup_untouched=$signup_untouched"
  echo "    Status output:"
  echo "$STATUS_A"
fi

if $phase_a_ok; then
  purlin_proof "e2e_feature_scoped_overwrite" "PROOF-1" "RULE-1" pass "separate proof files don't interfere"
else
  purlin_proof "e2e_feature_scoped_overwrite" "PROOF-1" "RULE-1" fail "separate proof files don't interfere"
fi

# ==========================================================================
# Phase B — Overwrite login proofs (feature-scoped) → both still PASSING
# ==========================================================================
echo "  --- Phase B: Overwrite login proofs ---"

# Use the shell proof harness to simulate a real re-run for login only.
# The harness does feature-scoped overwrite: removes old entries for the feature,
# then appends new ones.
(
  cd "$TMPDIR"
  source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"
  purlin_proof "login" "PROOF-1" "RULE-1" pass "login test 1 (re-run)"
  purlin_proof "login" "PROOF-2" "RULE-2" pass "login test 2 (re-run)"
  export PROJECT_ROOT="$TMPDIR"
  purlin_proof_finish
)
(cd "$TMPDIR" && git add -A && git commit -q -m "overwrite login proofs via harness")

STATUS_B=$(run_sync_status "$TMPDIR")

login_ready_b=false
signup_ready_b=false
echo "$STATUS_B" | grep -q "login: PASSING" && login_ready_b=true
echo "$STATUS_B" | grep -q "signup: PASSING" && signup_ready_b=true

phase_b_ok=false
if $login_ready_b && $signup_ready_b; then
  echo "    Phase B PASS: login PASSING (new entries), signup PASSING (untouched)"
  phase_b_ok=true
else
  echo "    Phase B FAIL: login_ready=$login_ready_b signup_ready=$signup_ready_b"
  echo "    Status output:"
  echo "$STATUS_B"
fi

if $phase_b_ok; then
  purlin_proof "e2e_feature_scoped_overwrite" "PROOF-2" "RULE-2" pass "overwrite replaces only target feature, others intact"
else
  purlin_proof "e2e_feature_scoped_overwrite" "PROOF-2" "RULE-2" fail "overwrite replaces only target feature, others intact"
fi

# ==========================================================================
# Phase C — Simulate deleted test: login proof file with only 1 of 2 proofs
# ==========================================================================
echo "  --- Phase C: Simulate deleted test ---"

# Write login proof file with only PROOF-1 (PROOF-2 removed — simulates a test deletion)
write_proof_file "$TMPDIR/specs/auth/login.proofs-unit.json" "login" \
  "PROOF-1|RULE-1|pass"

(cd "$TMPDIR" && git add -A && git commit -q -m "remove PROOF-2 from login")

STATUS_C=$(run_sync_status "$TMPDIR")

phase_c_ok=false
# login should show 1/2 rules proved (not PASSING, not carrying over old PROOF-2)
if echo "$STATUS_C" | grep -q "login: 1/2 rules proved"; then
  # Also verify signup is still PASSING
  if echo "$STATUS_C" | grep -q "signup: PASSING"; then
    echo "    Phase C PASS: login shows 1/2 (purged old proof), signup still PASSING"
    phase_c_ok=true
  else
    echo "    Phase C FAIL: signup not PASSING"
  fi
else
  echo "    Phase C FAIL: expected 'login: 1/2 rules proved'"
  echo "    Status output:"
  echo "$STATUS_C"
fi

if $phase_c_ok; then
  purlin_proof "e2e_feature_scoped_overwrite" "PROOF-3" "RULE-3" pass "removed test proof is purged, not carried over"
else
  purlin_proof "e2e_feature_scoped_overwrite" "PROOF-3" "RULE-3" fail "removed test proof is purged, not carried over"
fi

# --- Emit proof files ---
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_feature_scoped_overwrite: 3 proofs recorded"
