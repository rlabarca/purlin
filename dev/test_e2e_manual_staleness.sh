#!/usr/bin/env bash
# E2E test: Manual Proof Staleness Lifecycle
# 3 proofs covering 3 rules — all @e2e (Level 3).
# Creates a real temp git repo, stamps manual proofs, modifies scope files,
# and verifies staleness detection + re-stamping.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_PY="$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py"
SERVER_DIR="$(dirname "$SERVER_PY")"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_manual_staleness tests ==="

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
# Setup: create temp repo with spec + scope file
# ==========================================================================
TMPDIR=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR"

mkdir -p "$TMPDIR/.purlin"
mkdir -p "$TMPDIR/specs/auth"
mkdir -p "$TMPDIR/scripts/mcp"
mkdir -p "$TMPDIR/src"

# Create default config
echo '{"version":"0.9.0","test_framework":"shell","spec_dir":"specs"}' > "$TMPDIR/.purlin/config.json"

# Copy the real MCP server files
cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$TMPDIR/scripts/mcp/purlin_server.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$TMPDIR/scripts/mcp/config_engine.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$TMPDIR/scripts/mcp/__init__.py" 2>/dev/null || true

# Create the scope file
cat > "$TMPDIR/src/login.js" << 'JS'
function login(user, pass) {
  return authenticate(user, pass);
}
JS

# Initialize git repo and get initial commit SHA
(cd "$TMPDIR" && git init -q && git add -A && git commit -q -m "init")
INIT_SHA=$(cd "$TMPDIR" && git rev-parse HEAD)
SHORT_SHA=$(cd "$TMPDIR" && git rev-parse --short=7 HEAD)

# Create spec with 2 rules — RULE-2 has a @manual stamp at current HEAD
cat > "$TMPDIR/specs/auth/login.md" << SPEC
# Feature: login

> Scope: src/login.js

## What it does

User login feature.

## Rules

- RULE-1: Valid credentials return session token
- RULE-2: Login UI matches design spec

## Proof

- PROOF-1 (RULE-1): POST /login with valid creds; verify token returned @e2e
- PROOF-2 (RULE-2): Visual layout matches design @manual(dev@test.com, 2026-04-01, ${SHORT_SHA})
SPEC

# Create a passing proof file for RULE-1 (automated proof)
cat > "$TMPDIR/specs/auth/login.proofs-default.json" << JSON
{"tier": "default", "proofs": [
  {
    "feature": "login",
    "id": "PROOF-1",
    "rule": "RULE-1",
    "test_file": "dev/test_login.sh",
    "test_name": "test login",
    "status": "pass",
    "tier": "default"
  }
]}
JSON

# Commit the stamped spec
(cd "$TMPDIR" && git add -A && git commit -q -m "add stamped spec")

# ==========================================================================
# Phase A — Stamp is fresh: manual proof shows PASS
# ==========================================================================
echo "  --- Phase A: Fresh manual stamp → PASS ---"

STATUS_A=$(run_sync_status "$TMPDIR")

phase_a_ok=false
# The manual proof line should show PASS with the verified date
if echo "$STATUS_A" | grep -q "PASS.*manual.*verified.*2026-04-01"; then
  echo "    Phase A PASS: manual proof shows PASS with verified date"
  phase_a_ok=true
else
  echo "    Phase A FAIL: expected manual proof PASS with verified date"
  echo "    Status output:"
  echo "$STATUS_A"
fi

if $phase_a_ok; then
  purlin_proof "e2e_manual_staleness" "PROOF-1" "RULE-1" pass "stamped manual proof shows PASS with verified date"
else
  purlin_proof "e2e_manual_staleness" "PROOF-1" "RULE-1" fail "stamped manual proof shows PASS with verified date"
fi

# ==========================================================================
# Phase B — Modify scope file → manual proof becomes STALE
# ==========================================================================
echo "  --- Phase B: Modify scope file → STALE ---"

# Edit the scope file
echo "// added authentication logging" >> "$TMPDIR/src/login.js"
(cd "$TMPDIR" && git add -A && git commit -q -m "modify login.js")

STATUS_B=$(run_sync_status "$TMPDIR")

phase_b_stale=false
phase_b_directive=false

echo "$STATUS_B" | grep -q "MANUAL PROOF STALE" && phase_b_stale=true
echo "$STATUS_B" | grep -q "Re-verify and run: purlin:verify --manual" && phase_b_directive=true

phase_b_ok=false
if $phase_b_stale && $phase_b_directive; then
  echo "    Phase B PASS: manual proof shows STALE with re-verify directive"
  phase_b_ok=true
else
  echo "    Phase B FAIL: stale=$phase_b_stale directive=$phase_b_directive"
  echo "    Status output:"
  echo "$STATUS_B"
fi

if $phase_b_ok; then
  purlin_proof "e2e_manual_staleness" "PROOF-2" "RULE-2" pass "scope file change makes manual proof STALE with directive"
else
  purlin_proof "e2e_manual_staleness" "PROOF-2" "RULE-2" fail "scope file change makes manual proof STALE with directive"
fi

# ==========================================================================
# Phase C — Re-stamp with new HEAD → PASS again
# ==========================================================================
echo "  --- Phase C: Re-stamp → PASS ---"

NEW_SHA=$(cd "$TMPDIR" && git rev-parse --short=7 HEAD)

# Update the manual stamp with the new commit SHA
cat > "$TMPDIR/specs/auth/login.md" << SPEC
# Feature: login

> Scope: src/login.js

## What it does

User login feature.

## Rules

- RULE-1: Valid credentials return session token
- RULE-2: Login UI matches design spec

## Proof

- PROOF-1 (RULE-1): POST /login with valid creds; verify token returned @e2e
- PROOF-2 (RULE-2): Visual layout matches design @manual(dev@test.com, 2026-04-02, ${NEW_SHA})
SPEC

(cd "$TMPDIR" && git add -A && git commit -q -m "re-stamp manual proof")

STATUS_C=$(run_sync_status "$TMPDIR")

phase_c_ok=false
if echo "$STATUS_C" | grep -q "PASS.*manual.*verified.*2026-04-02"; then
  # Also verify NOT stale
  if ! echo "$STATUS_C" | grep -q "MANUAL PROOF STALE"; then
    echo "    Phase C PASS: re-stamped manual proof shows PASS again"
    phase_c_ok=true
  else
    echo "    Phase C FAIL: still shows STALE after re-stamp"
  fi
else
  echo "    Phase C FAIL: expected manual proof PASS with new date"
  echo "    Status output:"
  echo "$STATUS_C"
fi

if $phase_c_ok; then
  purlin_proof "e2e_manual_staleness" "PROOF-3" "RULE-3" pass "re-stamp clears stale state, shows PASS"
else
  purlin_proof "e2e_manual_staleness" "PROOF-3" "RULE-3" fail "re-stamp clears stale state, shows PASS"
fi

# --- Emit proof files ---
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_manual_staleness: 3 proofs recorded"
