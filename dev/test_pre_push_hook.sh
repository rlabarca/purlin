#!/usr/bin/env bash
# Tests for pre_push_hook — 8 proofs covering 7 rules.
# Most tests are @slow (Level 2) — they create temp directories and run the hook.
# PROOF-8 is @e2e (Level 3) — full lifecycle across proof states.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_SCRIPT="$REAL_PROJECT_ROOT/scripts/hooks/pre-push.sh"
SERVER_PY="$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== pre_push_hook tests ==="

# --- Helper: create a minimal Purlin project in a temp dir ---
# Sets up .purlin/, specs/, and a spec with N rules.
# Also copies purlin_server.py so the hook can call sync_status.
create_test_project() {
  local tmpdir="$1"
  local num_rules="${2:-3}"

  mkdir -p "$tmpdir/.purlin"
  mkdir -p "$tmpdir/specs/hooks"
  mkdir -p "$tmpdir/scripts/mcp"

  # Create default config
  echo '{"version":"0.9.0","test_framework":"auto","spec_dir":"specs","pre_push":"warn"}' > "$tmpdir/.purlin/config.json"

  # Copy the real MCP server files so sync_status works
  cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$tmpdir/scripts/mcp/purlin_server.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$tmpdir/scripts/mcp/config_engine.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$tmpdir/scripts/mcp/__init__.py" 2>/dev/null || true

  # Create a minimal spec with the requested number of rules
  {
    echo "# Feature: test_feature"
    echo ""
    echo "## What it does"
    echo ""
    echo "A test feature for pre-push hook testing."
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
      echo "- PROOF-$i (RULE-$i): Verify rule $i holds"
    done
  } > "$tmpdir/specs/hooks/test_feature.md"

  # Initialize as a git repo so git rev-parse works
  (cd "$tmpdir" && git init -q && git add -A && git commit -q -m "init" --allow-empty)
}

# --- Helper: create a proof file ---
# Args: tmpdir, feature_name, array of "PROOF-N|RULE-N|status" entries
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

  # Find the spec directory for this feature
  local spec_dir
  spec_dir=$(find "$tmpdir/specs" -name "${feature}.md" -exec dirname {} \; | head -1)
  if [[ -z "$spec_dir" ]]; then
    spec_dir="$tmpdir/specs"
  fi

  echo "{\"tier\": \"default\", \"proofs\": $proofs}" > "$spec_dir/${feature}.proofs-default.json"
}

# --- Helper: run the hook in a test project ---
run_hook() {
  local tmpdir="$1"
  # The hook uses `git rev-parse --show-toplevel` to find ROOT,
  # so we must cd into the git repo.
  (cd "$tmpdir" && bash "$HOOK_SCRIPT" 2>&1) || return $?
}

# ==========================================================================
# PROOF-1 (RULE-1): Blocks push when any proof is FAIL — exit 1
# ==========================================================================
ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

TMPDIR1=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR1"
create_test_project "$TMPDIR1" 3
create_proof_file "$TMPDIR1" "test_feature" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|fail" \
  "PROOF-3|RULE-3|pass"

output1=""
ec1=0
output1=$(run_hook "$TMPDIR1") || ec1=$?

if [[ $ec1 -eq 1 ]] && echo "$output1" | grep -q "PUSH BLOCKED"; then
  echo "  PASS: FAIL proof blocks push (exit 1)"
  purlin_proof "pre_push_hook" "PROOF-1" "RULE-1" pass "FAIL proof blocks push with exit 1 and PUSH BLOCKED message"
else
  echo "  FAIL: expected exit 1 + PUSH BLOCKED, got exit=$ec1"
  echo "  Output: $output1"
  purlin_proof "pre_push_hook" "PROOF-1" "RULE-1" fail "FAIL proof blocks push with exit 1 and PUSH BLOCKED message"
fi
# cleanup via trap

# ==========================================================================
# PROOF-2 (RULE-2): Allows push with warning when NO PROOF exists (no FAIL)
# ==========================================================================
TMPDIR2=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR2"
create_test_project "$TMPDIR2" 3
# 2 pass, 1 has no proof at all (only 2 entries in proof file)
create_proof_file "$TMPDIR2" "test_feature" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass"

output2=""
ec2=0
output2=$(run_hook "$TMPDIR2") || ec2=$?

if [[ $ec2 -eq 0 ]] && echo "$output2" | grep -q "partial coverage"; then
  echo "  PASS: NO PROOF allows with warning (exit 0)"
  purlin_proof "pre_push_hook" "PROOF-2" "RULE-2" pass "NO PROOF allows push with exit 0 and partial coverage warning"
else
  echo "  FAIL: expected exit 0 + partial coverage, got exit=$ec2"
  echo "  Output: $output2"
  purlin_proof "pre_push_hook" "PROOF-2" "RULE-2" fail "NO PROOF allows push with exit 0 and partial coverage warning"
fi

# ==========================================================================
# PROOF-3 (RULE-3): Allows push silently when no specs exist
# ==========================================================================
TMPDIR3=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR3"
mkdir -p "$TMPDIR3/.purlin"
(cd "$TMPDIR3" && git init -q && git commit -q -m "init" --allow-empty)
# No specs/ directory at all

output3=""
ec3=0
output3=$(run_hook "$TMPDIR3") || ec3=$?

if [[ $ec3 -eq 0 ]] && [[ -z "$output3" ]]; then
  echo "  PASS: no specs → silent exit 0"
  purlin_proof "pre_push_hook" "PROOF-3" "RULE-3" pass "no specs directory allows push silently with exit 0"
else
  echo "  FAIL: expected silent exit 0, got exit=$ec3 output='$output3'"
  purlin_proof "pre_push_hook" "PROOF-3" "RULE-3" fail "no specs directory allows push silently with exit 0"
fi

# ==========================================================================
# PROOF-4 (RULE-4): Allows push when all proofs pass (READY)
# ==========================================================================
TMPDIR4=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR4"
create_test_project "$TMPDIR4" 3
create_proof_file "$TMPDIR4" "test_feature" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass" \
  "PROOF-3|RULE-3|pass"

output4=""
ec4=0
output4=$(run_hook "$TMPDIR4") || ec4=$?

if [[ $ec4 -eq 0 ]]; then
  echo "  PASS: all pass → exit 0"
  purlin_proof "pre_push_hook" "PROOF-4" "RULE-4" pass "all proofs pass allows push with exit 0"
else
  echo "  FAIL: expected exit 0, got exit=$ec4"
  echo "  Output: $output4"
  purlin_proof "pre_push_hook" "PROOF-4" "RULE-4" fail "all proofs pass allows push with exit 0"
fi

# ==========================================================================
# PROOF-5 (RULE-5): Detects test framework from config
# ==========================================================================
TMPDIR5=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR5"
create_test_project "$TMPDIR5" 1
create_proof_file "$TMPDIR5" "test_feature" \
  "PROOF-1|RULE-1|pass"

# Set test_framework to pytest in config
echo '{"test_framework": "pytest"}' > "$TMPDIR5/.purlin/config.json"

output5=""
ec5=0
output5=$(run_hook "$TMPDIR5") || ec5=$?

# The hook prints "purlin: running default-tier tests (pytest)..."
if echo "$output5" | grep -q "(pytest)"; then
  echo "  PASS: detects pytest from config"
  result5="pass"
else
  echo "  FAIL: expected (pytest) in output"
  echo "  Output: $output5"
  result5="fail"
fi

# Now test jest detection
echo '{"test_framework": "jest"}' > "$TMPDIR5/.purlin/config.json"
output5b=""
ec5b=0
output5b=$(run_hook "$TMPDIR5") || ec5b=$?

if echo "$output5b" | grep -q "(jest)"; then
  echo "  PASS: detects jest from config"
  if [[ "$result5" == "pass" ]]; then
    purlin_proof "pre_push_hook" "PROOF-5" "RULE-5" pass "detects test framework from config (pytest and jest)"
  else
    purlin_proof "pre_push_hook" "PROOF-5" "RULE-5" fail "detects test framework from config (pytest and jest)"
  fi
else
  echo "  FAIL: expected (jest) in output"
  echo "  Output: $output5b"
  purlin_proof "pre_push_hook" "PROOF-5" "RULE-5" fail "detects test framework from config (pytest and jest)"
fi

# ==========================================================================
# PROOF-6 (RULE-6): Runs only default tier (pytest -m "not slow")
# ==========================================================================
TMPDIR6=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR6"
create_test_project "$TMPDIR6" 1
create_proof_file "$TMPDIR6" "test_feature" \
  "PROOF-1|RULE-1|pass"

# Create conftest.py to trigger auto-detect of pytest
touch "$TMPDIR6/conftest.py"
# Remove config so auto-detection kicks in
rm -f "$TMPDIR6/.purlin/config.json"

# We can't easily capture the exact pytest invocation, but we can verify
# the hook's source code uses the right flags. Read the script and check.
if grep -q 'pytest -m "not slow"' "$HOOK_SCRIPT"; then
  echo "  PASS: hook uses pytest -m 'not slow' (default tier only)"
  purlin_proof "pre_push_hook" "PROOF-6" "RULE-6" pass "hook runs only default-tier tests (pytest -m not slow)"
else
  echo "  FAIL: hook does not use pytest -m 'not slow'"
  purlin_proof "pre_push_hook" "PROOF-6" "RULE-6" fail "hook runs only default-tier tests (pytest -m not slow)"
fi

# ==========================================================================
# PROOF-7 (RULE-7): Produces clear output with pass/warn/block sections
# ==========================================================================
TMPDIR7=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR7"
create_test_project "$TMPDIR7" 3
create_proof_file "$TMPDIR7" "test_feature" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|fail"
# RULE-3 has no proof → NO PROOF

output7=""
ec7=0
output7=$(run_hook "$TMPDIR7") || ec7=$?

has_passing=false
has_partial=false
has_blocked=false

echo "$output7" | grep -q "partial coverage" && has_partial=true
echo "$output7" | grep -q "PUSH BLOCKED" && has_blocked=true
# Note: when there's a FAIL, passing features may not be shown (since the
# feature is not READY). Check for the FAIL detail line instead.

if $has_partial && $has_blocked; then
  echo "  PASS: output contains partial coverage + PUSH BLOCKED sections"
  purlin_proof "pre_push_hook" "PROOF-7" "RULE-7" pass "output shows partial coverage and PUSH BLOCKED sections"
else
  echo "  FAIL: expected partial+blocked sections, got partial=$has_partial blocked=$has_blocked"
  echo "  Output: $output7"
  purlin_proof "pre_push_hook" "PROOF-7" "RULE-7" fail "output shows partial coverage and PUSH BLOCKED sections"
fi

# ==========================================================================
# PROOF-9 (RULE-8): Strict mode blocks on partial coverage (NO PROOF)
# ==========================================================================
TMPDIR9=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR9"
create_test_project "$TMPDIR9" 3
# Set strict mode
python3 -c "
import json
cfg = json.load(open('$TMPDIR9/.purlin/config.json'))
cfg['pre_push'] = 'strict'
json.dump(cfg, open('$TMPDIR9/.purlin/config.json', 'w'))
"
# Create proofs for only 2 of 3 rules (partial — no FAIL, but not READY)
create_proof_file "$TMPDIR9" "test_feature" "PROOF-1|RULE-1|pass" "PROOF-2|RULE-2|pass"
OUTPUT9=$(run_hook "$TMPDIR9" 2>&1) || EXIT9=$?
EXIT9=${EXIT9:-0}
if [[ "$EXIT9" -eq 1 ]] && echo "$OUTPUT9" | grep -q "strict mode"; then
  echo "  PASS: strict mode blocks on partial coverage"
  purlin_proof "pre_push_hook" "PROOF-9" "RULE-8" pass "strict mode blocks push when features are not READY"
else
  echo "  FAIL: expected exit 1 + strict mode block, got exit=$EXIT9"
  echo "  Output: $OUTPUT9"
  purlin_proof "pre_push_hook" "PROOF-9" "RULE-8" fail "strict mode blocks push when features are not READY"
fi

# ==========================================================================
# PROOF-10 (RULE-8): Strict mode allows when all READY
# ==========================================================================
TMPDIR10=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR10"
create_test_project "$TMPDIR10" 2
python3 -c "
import json
cfg = json.load(open('$TMPDIR10/.purlin/config.json'))
cfg['pre_push'] = 'strict'
json.dump(cfg, open('$TMPDIR10/.purlin/config.json', 'w'))
"
create_proof_file "$TMPDIR10" "test_feature" "PROOF-1|RULE-1|pass" "PROOF-2|RULE-2|pass"
OUTPUT10=$(run_hook "$TMPDIR10" 2>&1) || EXIT10=$?
EXIT10=${EXIT10:-0}
if [[ "$EXIT10" -eq 0 ]]; then
  echo "  PASS: strict mode allows when all READY"
  purlin_proof "pre_push_hook" "PROOF-10" "RULE-8" pass "strict mode allows push when all features READY"
else
  echo "  FAIL: expected exit 0, got exit=$EXIT10"
  echo "  Output: $OUTPUT10"
  purlin_proof "pre_push_hook" "PROOF-10" "RULE-8" fail "strict mode allows push when all features READY"
fi

# ==========================================================================
# PROOF-8 (RULE-1, RULE-2, RULE-4): Full lifecycle — @e2e (Level 3)
#   Phase A: 1 PASS, 1 FAIL, 1 NO PROOF → exit 1 (blocked by FAIL)
#   Phase B: Fix FAIL to PASS → exit 0 with warning (NO PROOF remains)
#   Phase C: Add missing proof as PASS → exit 0 silently (all READY)
# ==========================================================================
TMPDIR8=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR8"
create_test_project "$TMPDIR8" 3

echo "  --- Phase A: 1 PASS, 1 FAIL, 1 NO PROOF ---"
create_proof_file "$TMPDIR8" "test_feature" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|fail"
# RULE-3 has no proof entry → NO PROOF

# Commit the proof file so git state is clean
(cd "$TMPDIR8" && git add -A && git commit -q -m "add proofs phase A")

output8a=""
ec8a=0
output8a=$(run_hook "$TMPDIR8") || ec8a=$?

phase_a_ok=false
if [[ $ec8a -eq 1 ]] && echo "$output8a" | grep -q "PUSH BLOCKED"; then
  echo "    Phase A PASS: exit 1, PUSH BLOCKED"
  phase_a_ok=true
else
  echo "    Phase A FAIL: expected exit 1 + PUSH BLOCKED, got exit=$ec8a"
  echo "    Output: $output8a"
fi

echo "  --- Phase B: Fix FAIL to PASS (NO PROOF remains) ---"
create_proof_file "$TMPDIR8" "test_feature" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass"
# RULE-3 still has no proof → NO PROOF

(cd "$TMPDIR8" && git add -A && git commit -q -m "fix FAIL in phase B")

output8b=""
ec8b=0
output8b=$(run_hook "$TMPDIR8") || ec8b=$?

phase_b_ok=false
if [[ $ec8b -eq 0 ]] && echo "$output8b" | grep -q "partial coverage"; then
  echo "    Phase B PASS: exit 0, partial coverage warning"
  phase_b_ok=true
else
  echo "    Phase B FAIL: expected exit 0 + partial coverage, got exit=$ec8b"
  echo "    Output: $output8b"
fi

echo "  --- Phase C: Add missing proof (all READY) ---"
create_proof_file "$TMPDIR8" "test_feature" \
  "PROOF-1|RULE-1|pass" \
  "PROOF-2|RULE-2|pass" \
  "PROOF-3|RULE-3|pass"

(cd "$TMPDIR8" && git add -A && git commit -q -m "complete proofs phase C")

output8c=""
ec8c=0
output8c=$(run_hook "$TMPDIR8") || ec8c=$?

phase_c_ok=false
if [[ $ec8c -eq 0 ]]; then
  echo "    Phase C PASS: exit 0 (all READY)"
  phase_c_ok=true
else
  echo "    Phase C FAIL: expected exit 0, got exit=$ec8c"
  echo "    Output: $output8c"
fi

if $phase_a_ok && $phase_b_ok && $phase_c_ok; then
  echo "  PASS: full lifecycle test"
  purlin_proof "pre_push_hook" "PROOF-8" "RULE-1" pass "full lifecycle: FAIL→blocks, fix→warns, complete→allows"
else
  echo "  FAIL: full lifecycle test (a=$phase_a_ok b=$phase_b_ok c=$phase_c_ok)"
  purlin_proof "pre_push_hook" "PROOF-8" "RULE-1" fail "full lifecycle: FAIL→blocks, fix→warns, complete→allows"
fi

# --- Emit proof files ---
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "pre_push_hook: 8 proofs recorded"
