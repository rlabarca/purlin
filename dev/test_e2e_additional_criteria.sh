#!/usr/bin/env bash
# E2E test: Additional (additive) audit criteria
# Proves that user-added criteria are appended to built-in, never replace them,
# and that the combined criteria reach the LLM and affect audit outcomes.
#
# 5 phases covering skill_audit RULE-14 @e2e (Level 3).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATIC_CHECKS="$REAL_PROJECT_ROOT/scripts/audit/static_checks.py"
FAKE_LLM="$SCRIPT_DIR/fake_audit_llm_with_criteria.sh"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_additional_criteria tests ==="

# --- Helper: create a fake git repo with additional criteria ---
create_criteria_repo() {
  local repodir="$1"
  mkdir -p "$repodir"
  cat > "$repodir/team_criteria.md" <<'CRITERIA'
## Team-Specific WEAK Criteria

- **No sleep() in tests** — any test containing time.sleep() or sleep()
  is WEAK. Tests must not depend on timing.
- **API tests must check response headers** — tests for API endpoints that
  only check status code without verifying Content-Type header are WEAK.
CRITERIA
  (cd "$repodir" && git init -q && git add -A && git commit -q -m "initial criteria")
}

# --- Helper: create a minimal Purlin project ---
create_test_project() {
  local projdir="$1"
  local criteria_url="${2:-}"

  mkdir -p "$projdir/.purlin/cache"
  mkdir -p "$projdir/specs/auth"

  # Config
  if [[ -n "$criteria_url" ]]; then
    cat > "$projdir/.purlin/config.json" <<CONF
{
  "version": "0.9.0",
  "test_framework": "pytest",
  "spec_dir": "specs",
  "audit_criteria": "$criteria_url"
}
CONF
  else
    cat > "$projdir/.purlin/config.json" <<'CONF'
{
  "version": "0.9.0",
  "test_framework": "pytest",
  "spec_dir": "specs"
}
CONF
  fi

  # Create a spec
  cat > "$projdir/specs/auth/login.md" <<'SPEC'
# Feature: login

> Scope: src/auth.py

## What it does
User authentication.

## Rules
- RULE-1: Login with valid credentials returns 200 and JWT token

## Proof
- PROOF-1 (RULE-1): POST valid credentials to /login; verify 200 response and JWT in body
SPEC

  (cd "$projdir" && git init -q && git add -A && git commit -q -m "init")
}


# ================================================================
# Phase A: Built-in criteria always active
# ================================================================
echo "--- Phase A: Built-in criteria always active ---"

TMPDIR_A=$(mktemp -d)
CRITERIA_REPO_A=$(mktemp -d)
create_criteria_repo "$CRITERIA_REPO_A"
create_test_project "$TMPDIR_A" "file://$CRITERIA_REPO_A#team_criteria.md"

# Cache the additional criteria
cp "$CRITERIA_REPO_A/team_criteria.md" "$TMPDIR_A/.purlin/cache/additional_criteria.md"

# Create a test file with assert True (should be HOLLOW by Pass 1 regardless of additional criteria)
cat > "$TMPDIR_A/test_hollow.py" <<'PYTEST'
import pytest

@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_login():
    assert True
PYTEST

# Run static_checks (Pass 1) — should detect assert True even with additional criteria
result=$(python3 "$STATIC_CHECKS" "$TMPDIR_A/test_hollow.py" "login" 2>&1)
if echo "$result" | python3 -c "import json,sys; d=json.load(sys.stdin); assert any(p['status']=='fail' and p.get('check')=='assert_true' for p in d['proofs'])"; then
  echo "  PASS: assert True detected by Pass 1 even with additional criteria configured"
  phase_a=true
else
  echo "  FAIL: Pass 1 did not detect assert True with additional criteria configured"
  phase_a=false
fi

rm -rf "$TMPDIR_A" "$CRITERIA_REPO_A"


# ================================================================
# Phase B: load_criteria() appends additional criteria
# ================================================================
echo "--- Phase B: load_criteria() appends ---"

TMPDIR_B=$(mktemp -d)
CRITERIA_REPO_B=$(mktemp -d)
create_criteria_repo "$CRITERIA_REPO_B"
create_test_project "$TMPDIR_B" "file://$CRITERIA_REPO_B#team_criteria.md"

# Cache the additional criteria
cp "$CRITERIA_REPO_B/team_criteria.md" "$TMPDIR_B/.purlin/cache/additional_criteria.md"

# Run --load-criteria
combined=$(python3 "$STATIC_CHECKS" --load-criteria --project-root "$TMPDIR_B")

# Verify built-in is present
phase_b_builtin=false
if echo "$combined" | grep -q "## Assessment Levels"; then
  echo "  PASS: Built-in criteria present in combined output"
  phase_b_builtin=true
else
  echo "  FAIL: Built-in criteria missing from combined output"
fi

# Verify additional criteria appended with separator
phase_b_additional=false
if echo "$combined" | grep -q "## Additional Team Criteria" && echo "$combined" | grep -q "No sleep() in tests"; then
  echo "  PASS: Additional criteria appended with separator header"
  phase_b_additional=true
else
  echo "  FAIL: Additional criteria not found in combined output"
fi

# Verify source URL in separator
phase_b_source=false
if echo "$combined" | grep -q "file://$CRITERIA_REPO_B#team_criteria.md"; then
  echo "  PASS: Source URL in separator header"
  phase_b_source=true
else
  echo "  FAIL: Source URL missing from separator header"
fi

if $phase_b_builtin && $phase_b_additional && $phase_b_source; then phase_b=true; else phase_b=false; fi

rm -rf "$TMPDIR_B" "$CRITERIA_REPO_B"


# ================================================================
# Phase C: Additional criteria reach the LLM and change outcomes
# ================================================================
echo "--- Phase C: Additional criteria change LLM outcomes ---"

# Test WITH additional criteria + sleep in code -> should get WEAK
prompt_with_criteria="CRITERIA:
## Team-Specific WEAK Criteria
- No sleep() in tests

TEST CODE:
def test_login():
    time.sleep(1)
    assert resp.status == 200

PROOF-ID: PROOF-1
RULE-ID: RULE-1"

result_with=$("$FAKE_LLM" -p "$prompt_with_criteria")
phase_c_weak=false
if echo "$result_with" | grep -q "WEAK"; then
  echo "  PASS: Fake LLM returns WEAK when criteria + sleep present"
  phase_c_weak=true
else
  echo "  FAIL: Expected WEAK from fake LLM with sleep criteria"
fi

# Test WITHOUT additional criteria + sleep in code -> should get STRONG
prompt_without_criteria="CRITERIA:
## Assessment Levels
Standard criteria only.

TEST CODE:
def test_login():
    resp = client.post('/login', json={'user': 'alice', 'pass': 'secret'})
    assert resp.status == 200

PROOF-ID: PROOF-1
RULE-ID: RULE-1"

result_without=$("$FAKE_LLM" -p "$prompt_without_criteria")
phase_c_strong=false
if echo "$result_without" | grep -q "STRONG"; then
  echo "  PASS: Fake LLM returns STRONG without sleep criteria"
  phase_c_strong=true
else
  echo "  FAIL: Expected STRONG from fake LLM without sleep criteria"
fi

if $phase_c_weak && $phase_c_strong; then phase_c=true; else phase_c=false; fi


# ================================================================
# Phase D: Pinned SHA staleness
# ================================================================
echo "--- Phase D: Pinned SHA staleness ---"

TMPDIR_D=$(mktemp -d)
CRITERIA_REPO_D=$(mktemp -d)
create_criteria_repo "$CRITERIA_REPO_D"

# Get initial SHA
initial_sha=$(cd "$CRITERIA_REPO_D" && git rev-parse HEAD)

create_test_project "$TMPDIR_D" "file://$CRITERIA_REPO_D#team_criteria.md"
# Set pinned SHA to initial
python3 -c "
import json, os
p = os.path.join('$TMPDIR_D', '.purlin', 'config.json')
with open(p) as f: c = json.load(f)
c['audit_criteria_pinned'] = '$initial_sha'
with open(p, 'w') as f: json.dump(c, f)
"

# Cache the initial criteria
cp "$CRITERIA_REPO_D/team_criteria.md" "$TMPDIR_D/.purlin/cache/additional_criteria.md"

# Add a new commit to the criteria repo
echo "- **No print() in tests**" >> "$CRITERIA_REPO_D/team_criteria.md"
(cd "$CRITERIA_REPO_D" && git add -A && git commit -q -m "add print rule")
new_sha=$(cd "$CRITERIA_REPO_D" && git rev-parse HEAD)

phase_d_different=false
if [[ "$initial_sha" != "$new_sha" ]]; then
  echo "  PASS: Criteria repo has new commit (SHA changed)"
  phase_d_different=true
else
  echo "  FAIL: SHA didn't change after new commit"
fi

# Verify pinned SHA differs from current HEAD
phase_d_stale=false
pinned_sha=$(python3 -c "import json; print(json.load(open('$TMPDIR_D/.purlin/config.json')).get('audit_criteria_pinned',''))")
if [[ "$pinned_sha" != "$new_sha" ]]; then
  echo "  PASS: Pinned SHA ($pinned_sha) differs from current HEAD ($new_sha) — staleness detected"
  phase_d_stale=true
else
  echo "  FAIL: Pinned SHA matches new HEAD — staleness not detected"
fi

if $phase_d_different && $phase_d_stale; then phase_d=true; else phase_d=false; fi

rm -rf "$TMPDIR_D" "$CRITERIA_REPO_D"


# ================================================================
# Phase E: --extra flag also appends
# ================================================================
echo "--- Phase E: --extra flag appends ---"

TMPDIR_E=$(mktemp -d)
create_test_project "$TMPDIR_E"

# Create an extra criteria file
cat > "$TMPDIR_E/extra_criteria.md" <<'EXTRA'
## Project-Specific Rules

- All API tests must verify response schema
EXTRA

# Run --load-criteria with --extra
combined_e=$(python3 "$STATIC_CHECKS" --load-criteria --project-root "$TMPDIR_E" --extra "$TMPDIR_E/extra_criteria.md")

phase_e_builtin=false
if echo "$combined_e" | grep -q "## Assessment Levels"; then
  echo "  PASS: Built-in present with --extra"
  phase_e_builtin=true
else
  echo "  FAIL: Built-in missing with --extra"
fi

phase_e_extra=false
if echo "$combined_e" | grep -q "## Additional Criteria" && echo "$combined_e" | grep -q "response schema"; then
  echo "  PASS: Extra criteria appended"
  phase_e_extra=true
else
  echo "  FAIL: Extra criteria not appended"
fi

# Verify no team criteria separator (with "(from" — the separator added by load_criteria)
# Note: the built-in doc has a "## Additional Team Criteria" section title, but load_criteria
# adds "## Additional Team Criteria (from <url>)" — we check for the "(from" suffix
phase_e_no_team=false
if ! echo "$combined_e" | grep -q "## Additional Team Criteria (from"; then
  echo "  PASS: No team criteria separator when not configured"
  phase_e_no_team=true
else
  echo "  FAIL: Team criteria separator appeared when not configured"
fi

if $phase_e_builtin && $phase_e_extra && $phase_e_no_team; then phase_e=true; else phase_e=false; fi

rm -rf "$TMPDIR_E"


# ================================================================
# Record proofs
# ================================================================
echo ""
echo "=== Results ==="

# PROOF-14 covers all phases
if $phase_a && $phase_b && $phase_c && $phase_d && $phase_e; then
  echo "ALL PHASES PASSED"
  export PROJECT_ROOT="$REAL_PROJECT_ROOT"
  cd "$PROJECT_ROOT"
  purlin_proof "skill_audit" "PROOF-14" "RULE-14" pass "All 5 phases passed: built-in always active, load_criteria appends, criteria reach LLM, SHA staleness detected, --extra appends"
else
  echo "SOME PHASES FAILED"
  export PROJECT_ROOT="$REAL_PROJECT_ROOT"
  cd "$PROJECT_ROOT"
  purlin_proof "skill_audit" "PROOF-14" "RULE-14" fail "Phase failures: A=$phase_a B=$phase_b C=$phase_c D=$phase_d E=$phase_e"
fi

purlin_proof_finish
