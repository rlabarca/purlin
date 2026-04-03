#!/usr/bin/env bash
# E2E test: Cross-model audit with real Gemini CLI
# 3 proofs covering 3 rules — all @e2e (Level 3).
# Requires `gemini` CLI to be installed. Skips gracefully if unavailable.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_PY="$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py"
SERVER_DIR="$(dirname "$SERVER_PY")"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_cross_model_audit tests ==="

# --- Pre-flight: check gemini CLI ---
if ! command -v gemini &>/dev/null; then
  echo "Skipping: gemini CLI not installed"
  # Record skipped proofs so sync_status sees them
  purlin_proof "e2e_cross_model_audit" "PROOF-1" "RULE-1" fail "skipped — gemini CLI not installed"
  purlin_proof "e2e_cross_model_audit" "PROOF-2" "RULE-2" fail "skipped — gemini CLI not installed"
  purlin_proof "e2e_cross_model_audit" "PROOF-3" "RULE-3" fail "skipped — gemini CLI not installed"
  export PROJECT_ROOT="$REAL_PROJECT_ROOT"
  cd "$PROJECT_ROOT"
  purlin_proof_finish
  exit 0
fi

# --- Helper: create a minimal Purlin project in a temp dir ---
create_test_project() {
  local tmpdir="$1"

  mkdir -p "$tmpdir/.purlin"
  mkdir -p "$tmpdir/specs/auth"
  mkdir -p "$tmpdir/scripts/mcp"

  # Config with external audit LLM
  cat > "$tmpdir/.purlin/config.json" <<'CONF'
{
  "version": "0.9.0",
  "test_framework": "shell",
  "spec_dir": "specs",
  "audit_llm": "gemini -m pro -p \"{prompt}\"",
  "audit_llm_name": "Gemini Pro"
}
CONF

  # Copy the real MCP server files so sync_status works
  cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$tmpdir/scripts/mcp/purlin_server.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$tmpdir/scripts/mcp/config_engine.py"
  cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$tmpdir/scripts/mcp/__init__.py" 2>/dev/null || true

  # Create a spec with 2 rules
  cat > "$tmpdir/specs/auth/login.md" <<'SPEC'
# Feature: login

> Scope: src/auth.py

## What it does

User authentication via username and password with bcrypt hashing.

## Rules

- RULE-1: Login with valid credentials returns a 200 status code and a JWT token
- RULE-2: Login with invalid password returns 401 and does not reveal whether the username exists

## Proof

- PROOF-1 (RULE-1): POST valid credentials to /login; verify 200 response and JWT in body
- PROOF-2 (RULE-2): POST invalid password; verify 401 response with generic error message
SPEC

  # Initialize as a git repo
  (cd "$tmpdir" && git init -q && git add -A && git commit -q -m "init")
}

# --- Helper: construct audit prompt (same as audit skill would) ---
# Writes the prompt to a temp file and prints the path.
# Using a temp file avoids shell quoting issues with special chars in
# criteria/test code ($, backticks, etc.).
build_audit_prompt() {
  local tmpdir="$1"
  local spec_path="$2"
  local test_code="$3"

  local criteria
  criteria=$(cat "$REAL_PROJECT_ROOT/references/audit_criteria.md")

  # Extract ## Proof section only (stop at next ## or EOF)
  local proof_section
  proof_section=$(awk '/^## Proof/{found=1; print; next} found && /^## /{exit} found{print}' "$spec_path")

  local prompt_file
  prompt_file=$(mktemp)

  {
    printf '%s\n' 'You are a code test auditor. Evaluate whether each test actually proves what the proof description claims.'
    printf '\n%s\n' 'CRITERIA:'
    printf '%s\n' "$criteria"
    printf '\n%s\n' 'SPEC PROOF DESCRIPTIONS:'
    printf '%s\n' "$proof_section"
    printf '\n%s\n' 'TEST CODE:'
    printf '%s\n' "$test_code"
    printf '\n%s\n' 'For each proof, respond in EXACTLY this format (one block per proof, no other text). Each field must be on a single line — do not wrap lines.'
    printf '\n'
    printf '%s\n' 'PROOF-ID: PROOF-1'
    printf '%s\n' 'RULE-ID: RULE-1'
    printf '%s\n' 'ASSESSMENT: STRONG|WEAK|HOLLOW'
    printf '%s\n' 'CRITERION: <which criterion was violated, or "matches proof description" if STRONG>'
    printf '%s\n' 'WHY: <what real problem this creates, or "test meaningfully proves the rule" if STRONG>'
    printf '%s\n' 'FIX: <specific change to make, or "none" if STRONG>'
    printf '%s\n' '---'
    printf '\n'
    printf '%s\n' 'PROOF-ID: PROOF-2'
    printf '%s\n' 'RULE-ID: RULE-2'
    printf '%s\n' 'ASSESSMENT: STRONG|WEAK|HOLLOW'
    printf '%s\n' 'CRITERION: <which criterion was violated, or "matches proof description" if STRONG>'
    printf '%s\n' 'WHY: <what real problem this creates, or "test meaningfully proves the rule" if STRONG>'
    printf '%s\n' 'FIX: <specific change to make, or "none" if STRONG>'
    printf '%s\n' '---'
  } > "$prompt_file"

  echo "$prompt_file"
}

# --- Helper: construct Pass 2 (semantic-only) prompt ---
# This is the two-pass architecture prompt: structural checks already ran,
# the LLM only evaluates semantic alignment — returns STRONG or WEAK only.
build_pass2_prompt() {
  local spec_path="$1"
  local test_code="$2"
  shift 2
  # Remaining args are PROOF-ID/RULE-ID pairs that passed Pass 1
  local proof_ids=("$@")

  local proof_section
  proof_section=$(awk '/^## Proof/{found=1; print; next} found && /^## /{exit} found{print}' "$spec_path")

  local prompt_file
  prompt_file=$(mktemp)

  {
    printf '%s\n' 'You are evaluating semantic alignment between spec rules and test code.'
    printf '%s\n' 'Structural issues (assert True, no assertions, logic mirroring) have already been checked and passed.'
    printf '\n%s\n' 'For each proof, answer ONLY these questions:'
    printf '%s\n' '1. Does the test set up a scenario that exercises the rules constraint?'
    printf '%s\n' '2. Does the test check the specific outcome the proof description claims?'
    printf '%s\n' '3. Is anything described in the proof missing from the test?'
    printf '\n%s\n' 'Rate each: STRONG (test matches rule intent) or WEAK (test partially matches — something is missing or too loose).'
    printf '%s\n' 'Do NOT check for structural issues — those were already handled.'
    printf '\n%s\n' 'SPEC PROOF DESCRIPTIONS:'
    printf '%s\n' "$proof_section"
    printf '\n%s\n' 'TEST CODE:'
    printf '%s\n' "$test_code"
    printf '\n%s\n' 'For each proof, respond in EXACTLY this format (one block per proof, no other text). Each field must be on a single line.'

    for pair in "${proof_ids[@]}"; do
      local pid rid
      pid=$(echo "$pair" | cut -d'|' -f1)
      rid=$(echo "$pair" | cut -d'|' -f2)
      printf '\n'
      printf '%s\n' "PROOF-ID: $pid"
      printf '%s\n' "RULE-ID: $rid"
      printf '%s\n' 'ASSESSMENT: STRONG|WEAK'
      printf '%s\n' 'CRITERION: <what semantic aspect is missing, or "matches rule intent" if STRONG>'
      printf '%s\n' 'WHY: <what behavior would slip through, or "test exercises the rule correctly" if STRONG>'
      printf '%s\n' 'FIX: <specific change to align test with rule, or "none" if STRONG>'
      printf '%s\n' '---'
    done
  } > "$prompt_file"

  echo "$prompt_file"
}

# --- Helper: parse audit response ---
# Extracts ASSESSMENT for a given PROOF-ID from the LLM response.
# Handles minor formatting variations across different LLMs.
parse_assessment() {
  local response="$1"
  local proof_id="$2"

  local assessment
  assessment=$(echo "$response" | awk -v pid="$proof_id" '
    /PROOF-ID:/ && $0 ~ pid { found=1; next }
    found && /^ASSESSMENT:/ { gsub(/^ASSESSMENT:[ \t]*/, ""); gsub(/[ \t]*$/, ""); print; exit }
    found && /^PROOF-ID:/ { exit }
    found && /^---/ { exit }
  ')

  # Fallback: looser matching (case-insensitive, within 5 lines of proof ID)
  if [[ -z "$assessment" ]]; then
    assessment=$(echo "$response" | grep -A8 "PROOF-ID:.*$proof_id" | grep -i "^ASSESSMENT" | head -1 | sed 's/^[Aa][Ss][Ss][Ee][Ss][Ss][Mm][Ee][Nn][Tt]:[ \t]*//' | awk '{print $1}')
  fi

  echo "$assessment"
}

# --- Helper: parse a specific field for a PROOF-ID ---
# Collects multi-line values: reads from the field line until the next
# known field marker (PROOF-ID:, RULE-ID:, ASSESSMENT:, CRITERION:, WHY:, FIX:, ---)
parse_field() {
  local response="$1"
  local proof_id="$2"
  local field="$3"

  local value
  value=$(echo "$response" | awk -v pid="$proof_id" -v fld="^$field:" '
    /PROOF-ID:/ && $0 ~ pid { in_block=1; next }
    in_block && $0 ~ fld {
      gsub(fld "[ \t]*", "")
      val = $0
      collecting = 1
      next
    }
    collecting && /^(PROOF-ID:|RULE-ID:|ASSESSMENT:|CRITERION:|WHY:|FIX:|---)/ { exit }
    collecting { val = val " " $0 }
    in_block && /^(PROOF-ID:|---)/ && !collecting { exit }
    END { gsub(/^[ \t]+|[ \t]+$/, "", val); print val }
  ')

  echo "$value"
}

# --- Cleanup ---
ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

# ==========================================================================
# Setup
# ==========================================================================
TMPDIR=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR"
create_test_project "$TMPDIR"

# ==========================================================================
# Phase A — Deliberately hollow test: Gemini should detect it
# ==========================================================================
echo "  --- Phase A: Hollow test detection ---"

HOLLOW_TEST='
def test_login_valid():
    """PROOF-1 for RULE-1"""
    assert True

def test_login_invalid():
    """PROOF-2 for RULE-2"""
    result = None
    assert result is None
'

PROMPT_FILE_A=$(build_audit_prompt "$TMPDIR" "$TMPDIR/specs/auth/login.md" "$HOLLOW_TEST")

echo "    Calling Gemini for hollow test audit..."
GEMINI_STDERR_A=$(mktemp)
RESPONSE_A=$(cat "$PROMPT_FILE_A" | gemini -m pro -p "" 2>"$GEMINI_STDERR_A") || {
  rm -f "$PROMPT_FILE_A"
  echo "    Gemini CLI failed (stderr): $(cat "$GEMINI_STDERR_A" | grep -i 'error\|quota' | head -3)"
  rm -f "$GEMINI_STDERR_A"
  purlin_proof "e2e_cross_model_audit" "PROOF-1" "RULE-1" fail "gemini CLI returned error"
  purlin_proof "e2e_cross_model_audit" "PROOF-2" "RULE-2" fail "gemini CLI returned error"
  purlin_proof "e2e_cross_model_audit" "PROOF-3" "RULE-3" fail "gemini CLI returned error"
  export PROJECT_ROOT="$REAL_PROJECT_ROOT"
  cd "$PROJECT_ROOT"
  purlin_proof_finish
  exit 1
}
rm -f "$PROMPT_FILE_A" "$GEMINI_STDERR_A"

ASSESS_1A=$(parse_assessment "$RESPONSE_A" "PROOF-1")
ASSESS_2A=$(parse_assessment "$RESPONSE_A" "PROOF-2")

phase_a_ok=false
# Gemini should identify these as HOLLOW (or at minimum not STRONG)
if [[ "$ASSESS_1A" == "HOLLOW" ]] || [[ "$ASSESS_1A" == "WEAK" ]]; then
  if [[ "$ASSESS_2A" == "HOLLOW" ]] || [[ "$ASSESS_2A" == "WEAK" ]]; then
    echo "    Phase A PASS: Gemini detected hollow tests (PROOF-1=$ASSESS_1A, PROOF-2=$ASSESS_2A)"
    phase_a_ok=true
  else
    echo "    Phase A FAIL: PROOF-2 expected HOLLOW or WEAK, got '$ASSESS_2A'"
  fi
else
  echo "    Phase A FAIL: PROOF-1 expected HOLLOW or WEAK, got '$ASSESS_1A'"
fi

if $phase_a_ok; then
  purlin_proof "e2e_cross_model_audit" "PROOF-1" "RULE-1" pass "external LLM detects hollow tests as non-STRONG"
else
  echo "    Raw Gemini response (Phase A):"
  echo "$RESPONSE_A" | head -30
  purlin_proof "e2e_cross_model_audit" "PROOF-1" "RULE-1" fail "external LLM detects hollow tests as non-STRONG"
fi

# ==========================================================================
# Phase B — Strong test: Gemini should approve it
# ==========================================================================
echo "  --- Phase B: Strong test approval ---"

STRONG_TEST='
import requests
import jwt

def test_login_valid():
    """PROOF-1 for RULE-1"""
    resp = requests.post("http://localhost:8000/login", json={"username": "alice", "password": "correct_password"})
    assert resp.status_code == 200
    body = resp.json()
    assert "token" in body
    decoded = jwt.decode(body["token"], options={"verify_signature": False})
    assert decoded["sub"] == "alice"

def test_login_invalid_password():
    """PROOF-2 for RULE-2"""
    resp = requests.post("http://localhost:8000/login", json={"username": "alice", "password": "wrong_password"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] == "invalid_credentials"
    # Verify the error message does not reveal whether the username exists
    assert "alice" not in body.get("message", "")
    assert "username" not in body.get("message", "").lower()
'

PROMPT_FILE_B=$(build_audit_prompt "$TMPDIR" "$TMPDIR/specs/auth/login.md" "$STRONG_TEST")

echo "    Calling Gemini for strong test audit..."
GEMINI_STDERR_B=$(mktemp)
RESPONSE_B=$(cat "$PROMPT_FILE_B" | gemini -m pro -p "" 2>"$GEMINI_STDERR_B") || {
  rm -f "$PROMPT_FILE_B"
  echo "    Gemini CLI failed (stderr): $(cat "$GEMINI_STDERR_B" | grep -i 'error\|quota' | head -3)"
  rm -f "$GEMINI_STDERR_B"
  purlin_proof "e2e_cross_model_audit" "PROOF-2" "RULE-2" fail "gemini CLI returned error"
  purlin_proof "e2e_cross_model_audit" "PROOF-3" "RULE-3" fail "gemini CLI returned error"
  export PROJECT_ROOT="$REAL_PROJECT_ROOT"
  cd "$PROJECT_ROOT"
  purlin_proof_finish
  exit 1
}
rm -f "$PROMPT_FILE_B" "$GEMINI_STDERR_B"

ASSESS_1B=$(parse_assessment "$RESPONSE_B" "PROOF-1")
ASSESS_2B=$(parse_assessment "$RESPONSE_B" "PROOF-2")

phase_b_ok=false
if [[ "$ASSESS_1B" == "STRONG" ]] && [[ "$ASSESS_2B" == "STRONG" ]]; then
  echo "    Phase B PASS: Gemini approved strong tests (PROOF-1=$ASSESS_1B, PROOF-2=$ASSESS_2B)"
  phase_b_ok=true
else
  echo "    Phase B FAIL: expected STRONG for both, got PROOF-1=$ASSESS_1B, PROOF-2=$ASSESS_2B"
fi

if $phase_b_ok; then
  purlin_proof "e2e_cross_model_audit" "PROOF-2" "RULE-2" pass "external LLM approves strong tests as STRONG"
else
  echo "    Raw Gemini response (Phase B):"
  echo "$RESPONSE_B" | head -30
  purlin_proof "e2e_cross_model_audit" "PROOF-2" "RULE-2" fail "external LLM approves strong tests as STRONG"
fi

# ==========================================================================
# Phase C — Response parsing: verify all fields extracted
# ==========================================================================
echo "  --- Phase C: Response parsing ---"

# Use the Phase B response (should have full structured output)
phase_c_ok=true
parse_failures=""

for proof_id in "PROOF-1" "PROOF-2"; do
  assess=$(parse_assessment "$RESPONSE_B" "$proof_id")
  criterion=$(parse_field "$RESPONSE_B" "$proof_id" "CRITERION")
  why=$(parse_field "$RESPONSE_B" "$proof_id" "WHY")
  fix=$(parse_field "$RESPONSE_B" "$proof_id" "FIX")

  if [[ -z "$assess" ]]; then
    parse_failures="${parse_failures}  $proof_id: ASSESSMENT not parsed\n"
    phase_c_ok=false
  fi
  if [[ -z "$criterion" ]]; then
    parse_failures="${parse_failures}  $proof_id: CRITERION not parsed\n"
    phase_c_ok=false
  fi
  if [[ -z "$why" ]]; then
    parse_failures="${parse_failures}  $proof_id: WHY not parsed\n"
    phase_c_ok=false
  fi
  if [[ -z "$fix" ]]; then
    parse_failures="${parse_failures}  $proof_id: FIX not parsed\n"
    phase_c_ok=false
  fi

  echo "    $proof_id: ASSESSMENT=$assess CRITERION=${criterion:0:40}... WHY=${why:0:40}... FIX=${fix:0:40}..."
done

if $phase_c_ok; then
  echo "    Phase C PASS: all fields parsed from Gemini response"
  purlin_proof "e2e_cross_model_audit" "PROOF-3" "RULE-3" pass "response parsing extracts PROOF-ID, ASSESSMENT, CRITERION, WHY, FIX"
else
  echo "    Phase C FAIL: parsing failures:"
  echo -e "$parse_failures"
  echo "    Raw Gemini response (Phase B, used for parsing):"
  echo "$RESPONSE_B" | head -40
  purlin_proof "e2e_cross_model_audit" "PROOF-3" "RULE-3" fail "response parsing extracts PROOF-ID, ASSESSMENT, CRITERION, WHY, FIX"
fi

# ==========================================================================
# Phase D — Two-pass flow: static_checks (Pass 1) then Gemini (Pass 2)
# ==========================================================================
echo "  --- Phase D: Two-pass hybrid audit with Gemini ---"

TMPDIR_D=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR_D"
create_test_project "$TMPDIR_D"

# Write a Python test file with mixed quality:
# - PROOF-1: assert True (should be caught by static_checks → HOLLOW)
# - PROOF-2: real assertions (should pass static_checks, go to Gemini → STRONG)
cat > "$TMPDIR_D/test_login.py" << 'PYEOF'
import pytest
import requests

@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_valid_login_hollow():
    assert True

@pytest.mark.proof("login", "PROOF-2", "RULE-2")
def test_invalid_login_strong():
    resp = requests.post("http://localhost:8000/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] == "invalid_credentials"
    assert "alice" not in body.get("message", "")
PYEOF

# Pass 1: Run static_checks.py
echo "    Pass 1: Running static_checks.py..."
STATIC_OUTPUT=$(python3 "$REAL_PROJECT_ROOT/scripts/audit/static_checks.py" \
  "$TMPDIR_D/test_login.py" "login" \
  --spec-path "$TMPDIR_D/specs/auth/login.md" 2>&1 || true)

# Check that PROOF-1 was caught deterministically
PROOF1_STATIC=$(echo "$STATIC_OUTPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for p in d['proofs']:
    if p['proof_id'] == 'PROOF-1':
        print(f\"{p['status']}/{p.get('check','none')}\")
        break
else:
    print('missing')
")
PROOF2_STATIC=$(echo "$STATIC_OUTPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for p in d['proofs']:
    if p['proof_id'] == 'PROOF-2':
        print(p['status'])
        break
else:
    print('missing')
")

echo "    Pass 1 results: PROOF-1=$PROOF1_STATIC, PROOF-2=$PROOF2_STATIC"

if [[ "$PROOF1_STATIC" != "fail/assert_true" ]]; then
  echo "    Phase D FAIL: Pass 1 should catch PROOF-1 as fail/assert_true, got $PROOF1_STATIC"
  purlin_proof "e2e_cross_model_audit" "PROOF-4" "RULE-4" fail "two-pass: static_checks did not catch PROOF-1"
else
  if [[ "$PROOF2_STATIC" != "pass" ]]; then
    echo "    Phase D FAIL: Pass 1 should pass PROOF-2, got $PROOF2_STATIC"
    purlin_proof "e2e_cross_model_audit" "PROOF-4" "RULE-4" fail "two-pass: PROOF-2 should pass static checks"
  else
    # Pass 2: Send only PROOF-2 (the one that passed Pass 1) to Gemini
    echo "    Pass 2: Sending only PROOF-2 to Gemini (PROOF-1 already HOLLOW)..."

    PASS2_TEST='
import requests

def test_invalid_login_strong():
    """PROOF-2 for RULE-2"""
    resp = requests.post("http://localhost:8000/login", json={"username": "alice", "password": "wrong"})
    assert resp.status_code == 401
    body = resp.json()
    assert body["error"] == "invalid_credentials"
    assert "alice" not in body.get("message", "")
'

    PROMPT_FILE_D=$(build_pass2_prompt "$TMPDIR_D/specs/auth/login.md" "$PASS2_TEST" "PROOF-2|RULE-2")

    GEMINI_STDERR_D=$(mktemp)
    RESPONSE_D=$(cat "$PROMPT_FILE_D" | gemini -m pro -p "" 2>"$GEMINI_STDERR_D") || {
      rm -f "$PROMPT_FILE_D" "$GEMINI_STDERR_D"
      echo "    Gemini CLI failed in Phase D"
      purlin_proof "e2e_cross_model_audit" "PROOF-4" "RULE-4" fail "gemini CLI returned error in two-pass flow"
      export PROJECT_ROOT="$REAL_PROJECT_ROOT"
      cd "$PROJECT_ROOT"
      purlin_proof_finish
      exit 1
    }
    rm -f "$PROMPT_FILE_D" "$GEMINI_STDERR_D"

    ASSESS_D=$(parse_assessment "$RESPONSE_D" "PROOF-2")
    echo "    Pass 2 result: PROOF-2=$ASSESS_D"

    # Gemini should return STRONG or WEAK (never HOLLOW — that's Pass 1 only)
    if [[ "$ASSESS_D" == "STRONG" ]]; then
      echo "    Phase D PASS: Pass 1 caught PROOF-1 (HOLLOW), Pass 2 approved PROOF-2 (STRONG)"
      purlin_proof "e2e_cross_model_audit" "PROOF-4" "RULE-4" pass "two-pass: static catches HOLLOW, Gemini rates STRONG"
    elif [[ "$ASSESS_D" == "WEAK" ]]; then
      echo "    Phase D PASS (WEAK): Pass 1 caught PROOF-1, Gemini rated PROOF-2 as WEAK (acceptable — semantic judgment)"
      purlin_proof "e2e_cross_model_audit" "PROOF-4" "RULE-4" pass "two-pass: static catches HOLLOW, Gemini rates WEAK"
    elif [[ "$ASSESS_D" == "HOLLOW" ]]; then
      echo "    Phase D FAIL: Gemini returned HOLLOW in Pass 2 — should only return STRONG or WEAK"
      echo "    Raw response: $(echo "$RESPONSE_D" | head -15)"
      purlin_proof "e2e_cross_model_audit" "PROOF-4" "RULE-4" fail "Gemini returned HOLLOW in Pass 2 (should be overridden to WEAK)"
    else
      echo "    Phase D FAIL: Gemini returned unexpected assessment '$ASSESS_D'"
      echo "    Raw response: $(echo "$RESPONSE_D" | head -15)"
      purlin_proof "e2e_cross_model_audit" "PROOF-4" "RULE-4" fail "unexpected assessment from Gemini in Pass 2"
    fi
  fi
fi

# ==========================================================================
# Phase E — Custom audit LLM configured via init flow (fake LLM wrapper)
# ==========================================================================
echo "  --- Phase E: Custom audit LLM from init config ---"

TMPDIR_E=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR_E"

FAKE_LLM="$REAL_PROJECT_ROOT/dev/fake_audit_llm.sh"

# Step 1: Create project with fake LLM in config (simulates purlin:init --audit-llm)
mkdir -p "$TMPDIR_E/.purlin" "$TMPDIR_E/specs/auth" "$TMPDIR_E/scripts/mcp"
cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$TMPDIR_E/scripts/mcp/purlin_server.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$TMPDIR_E/scripts/mcp/config_engine.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$TMPDIR_E/scripts/mcp/__init__.py" 2>/dev/null || true

# Config points to our fake LLM — same pattern as a real user would configure
cat > "$TMPDIR_E/.purlin/config.json" <<CONF
{
  "version": "0.9.0",
  "test_framework": "pytest",
  "spec_dir": "specs",
  "audit_llm": "$FAKE_LLM -p \"{prompt}\"",
  "audit_llm_name": "Fake Test LLM"
}
CONF

cat > "$TMPDIR_E/specs/auth/login.md" <<'SPEC'
# Feature: login

## What it does
User login with password.

## Rules
- RULE-1: Returns 200 with JWT on valid credentials
- RULE-2: Returns 401 on invalid password

## Proof
- PROOF-1 (RULE-1): POST valid credentials; verify 200 and JWT
- PROOF-2 (RULE-2): POST invalid password; verify 401
SPEC

(cd "$TMPDIR_E" && git init -q && git add -A && git commit -q -m "init")

# Step 2: Test the init ping (same test purlin:init --audit-llm does)
echo "    Testing init ping..."
PING_CMD="$FAKE_LLM -p \"Respond with exactly: PURLIN_AUDIT_OK\""
PING_RESPONSE=$(eval "$PING_CMD" 2>&1)

ping_ok=false
if echo "$PING_RESPONSE" | grep -q "PURLIN_AUDIT_OK"; then
  echo "    Init ping PASS: fake LLM responded with PURLIN_AUDIT_OK"
  ping_ok=true
else
  echo "    Init ping FAIL: expected PURLIN_AUDIT_OK, got: $PING_RESPONSE"
fi

# Step 3: Read config to verify audit_llm was stored
CONFIG_LLM=$(python3 -c "import json; c=json.load(open('$TMPDIR_E/.purlin/config.json')); print(c.get('audit_llm',''))")
CONFIG_NAME=$(python3 -c "import json; c=json.load(open('$TMPDIR_E/.purlin/config.json')); print(c.get('audit_llm_name',''))")

config_ok=false
if [[ -n "$CONFIG_LLM" ]] && [[ "$CONFIG_NAME" == "Fake Test LLM" ]]; then
  echo "    Config stored: audit_llm_name=$CONFIG_NAME"
  config_ok=true
else
  echo "    Config FAIL: audit_llm=$CONFIG_LLM, audit_llm_name=$CONFIG_NAME"
fi

# Step 4: Run Pass 1 (static checks) on a strong test
cat > "$TMPDIR_E/test_login.py" << 'PYEOF'
import pytest

@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_valid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "secret"})
    assert resp.status_code == 200
    assert "jwt" in resp.json()

@pytest.mark.proof("login", "PROOF-2", "RULE-2")
def test_invalid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "wrong"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_credentials"
PYEOF

STATIC_OUT_E=$(python3 "$REAL_PROJECT_ROOT/scripts/audit/static_checks.py" \
  "$TMPDIR_E/test_login.py" "login" \
  --spec-path "$TMPDIR_E/specs/auth/login.md" 2>&1)
STATIC_EXIT_E=$?

static_ok=false
if [[ "$STATIC_EXIT_E" == "0" ]]; then
  echo "    Pass 1: both proofs passed static checks"
  static_ok=true
else
  echo "    Pass 1 FAIL: exit $STATIC_EXIT_E"
fi

# Step 5: Send surviving proofs to the configured fake LLM (Pass 2)
# Build the Pass 2 prompt exactly as the audit skill would
PASS2_PROMPT_E=$(build_pass2_prompt "$TMPDIR_E/specs/auth/login.md" "$(cat "$TMPDIR_E/test_login.py")" \
  "PROOF-1|RULE-1" "PROOF-2|RULE-2")

echo "    Pass 2: Calling configured fake LLM..."
# Substitute {prompt} in the configured command — read prompt from file to avoid shell escaping
FAKE_RESPONSE_E=$(cat "$PASS2_PROMPT_E" | "$FAKE_LLM" -p "" 2>&1) || {
  echo "    Fake LLM call failed"
  FAKE_RESPONSE_E=""
}
rm -f "$PASS2_PROMPT_E"

ASSESS_E1=$(parse_assessment "$FAKE_RESPONSE_E" "PROOF-1")
ASSESS_E2=$(parse_assessment "$FAKE_RESPONSE_E" "PROOF-2")

llm_ok=false
if [[ "$ASSESS_E1" == "STRONG" ]] && [[ "$ASSESS_E2" == "STRONG" ]]; then
  echo "    Pass 2: PROOF-1=$ASSESS_E1, PROOF-2=$ASSESS_E2"
  llm_ok=true
else
  echo "    Pass 2 FAIL: PROOF-1=$ASSESS_E1, PROOF-2=$ASSESS_E2"
  echo "    Raw response:"
  echo "$FAKE_RESPONSE_E" | head -20
fi

# Step 6: Parse all fields from fake LLM response
fields_ok=true
for pid in "PROOF-1" "PROOF-2"; do
  for fld in "CRITERION" "WHY" "FIX"; do
    val=$(parse_field "$FAKE_RESPONSE_E" "$pid" "$fld")
    if [[ -z "$val" ]]; then
      echo "    Parse FAIL: $pid $fld empty"
      fields_ok=false
    fi
  done
done

if $ping_ok && $config_ok && $static_ok && $llm_ok && $fields_ok; then
  echo "    Phase E PASS: custom LLM configured, init ping works, two-pass audit completes"
  purlin_proof "e2e_cross_model_audit" "PROOF-5" "RULE-5" pass "custom audit LLM configured and used in two-pass flow"
else
  echo "    Phase E FAIL: ping=$ping_ok config=$config_ok static=$static_ok llm=$llm_ok fields=$fields_ok"
  purlin_proof "e2e_cross_model_audit" "PROOF-5" "RULE-5" fail "custom audit LLM flow incomplete"
fi

# --- Emit proof files ---
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_cross_model_audit: 5 proofs recorded"
