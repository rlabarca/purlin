#!/usr/bin/env bash
# E2E test: Write-Scoped Overwrite, keyed by (feature, tier, test_file)
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
# --- Helper: build a fresh temp repo with the login + signup specs ---
# Each phase that measures a merge outcome needs its own repo. Entries written
# by an earlier phase from a different test file now legitimately survive a
# later run (that is the point of the (feature, tier, test_file) key), so a
# phase reading the whole proof file must start from a clean one or it is
# measuring the previous phase's leftovers.
make_repo() {
  local dir
  dir=$(mktemp -d)
  ALL_TMPDIRS="$ALL_TMPDIRS $dir"

  mkdir -p "$dir/.purlin" "$dir/specs/auth" "$dir/scripts/mcp"
  echo '{"version":"0.9.0","test_framework":"shell","spec_dir":"specs"}' > "$dir/.purlin/config.json"

  cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$dir/scripts/mcp/purlin_server.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$dir/scripts/mcp/config_engine.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$dir/scripts/mcp/__init__.py" 2>/dev/null || true

  cat > "$dir/specs/auth/login.md" << 'SPEC'
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

  cat > "$dir/specs/auth/signup.md" << 'SPEC'
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

  (cd "$dir" && git init -q && git add -A && git commit -q -m "init")
  echo "$dir"
}

TMPDIR=$(make_repo)

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
  purlin_proof "proof_common" "PROOF-10" "RULE-4" pass "separate proof files don't interfere"
else
  purlin_proof "proof_common" "PROOF-10" "RULE-4" fail "separate proof files don't interfere"
fi

# ==========================================================================
# Phase B — Overwrite login proofs (feature-scoped) → both still PASSING
# ==========================================================================
echo "  --- Phase B: Overwrite login proofs ---"

# Use the shell proof harness to simulate a real re-run for login only.
# The harness does write-scoped overwrite: it replaces this feature's entries for
# the test files the run executed, then appends the new ones.
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
  purlin_proof "proof_common" "PROOF-11" "RULE-4" pass "overwrite replaces only target feature, others intact"
else
  purlin_proof "proof_common" "PROOF-11" "RULE-4" fail "overwrite replaces only target feature, others intact"
fi

# ==========================================================================
# Phase C — Re-run one test file with a proof removed: the entry is purged
# ==========================================================================
# Previously this phase hand-wrote a 1-of-2 proof file, which proved that
# sync_status reads what is on disk, not that anything was ever purged. Under
# the (feature, tier, test_file) merge key (proof_common RULE-4) the purge is
# only observable by re-running the SAME test file with one proof dropped, so
# that is what this phase now does.
echo "  --- Phase C: Re-run the same test file with PROOF-2 removed ---"

# One generated test file, written twice at the SAME path. Run 1 emits both
# proofs, run 2 emits only PROOF-1. Anything that survives into run 2's output
# was carried over rather than purged.
# Its own repo: see make_repo's comment. Phase B left login entries recorded
# against a different test file, and those now survive by design, so reading
# this phase's outcome out of Phase B's proof file would measure the wrong thing.
TMPDIR_C=$(make_repo)
LOGIN_TEST="$TMPDIR_C/test_login_proofs.sh"

write_login_test() {
  # $@ = "PROOF-N|RULE-N" pairs to emit
  {
    echo '#!/usr/bin/env bash'
    echo 'set -euo pipefail'
    echo "source \"$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh\""
    for entry in "$@"; do
      pid=$(echo "$entry" | cut -d'|' -f1)
      rid=$(echo "$entry" | cut -d'|' -f2)
      echo "purlin_proof \"login\" \"$pid\" \"$rid\" pass \"login $pid\""
    done
    echo 'purlin_proof_finish'
  } > "$LOGIN_TEST"
}

write_login_test "PROOF-1|RULE-1" "PROOF-2|RULE-2"
(cd "$TMPDIR_C" && bash "$LOGIN_TEST")

STATUS_C_BEFORE=$(run_sync_status "$TMPDIR_C")
login_two_of_two=false
echo "$STATUS_C_BEFORE" | grep -q "login: PASSING" && login_two_of_two=true

# Same path, PROOF-2's call deleted.
write_login_test "PROOF-1|RULE-1"
(cd "$TMPDIR_C" && bash "$LOGIN_TEST")

(cd "$TMPDIR_C" && git add -A && git commit -q -m "re-run login test with PROOF-2 removed")

STATUS_C=$(run_sync_status "$TMPDIR_C")

# PROOF-2 must be gone from the file itself, not merely uncounted.
proof2_gone=true
if grep -q '"PROOF-2"' "$TMPDIR_C/specs/auth/login.proofs-unit.json"; then
  proof2_gone=false
fi

phase_c_ok=false
if ! $login_two_of_two; then
  echo "    Phase C FAIL: run 1 did not leave login PASSING (2/2)"
  echo "$STATUS_C_BEFORE"
elif ! $proof2_gone; then
  echo "    Phase C FAIL: PROOF-2 entry survived a re-run of its own test file"
  cat "$TMPDIR_C/specs/auth/login.proofs-unit.json"
elif ! echo "$STATUS_C" | grep -q "login: 1/2 rules proved"; then
  echo "    Phase C FAIL: expected 'login: 1/2 rules proved'"
  echo "    Status output:"
  echo "$STATUS_C"
else
  echo "    Phase C PASS: 2/2, then a re-run of the same file purged PROOF-2 to 1/2"
  phase_c_ok=true
fi

if $phase_c_ok; then
  purlin_proof "proof_common" "PROOF-12" "RULE-10" pass "re-run of the same test file purges the removed proof"
else
  purlin_proof "proof_common" "PROOF-12" "RULE-10" fail "re-run of the same test file purges the removed proof"
fi

# --- Emit proof files ---
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_feature_scoped_overwrite: 3 proofs recorded"
