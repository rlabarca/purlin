#!/usr/bin/env bash
# E2E test: a custom audit LLM command in .purlin/config.json drives the
# two-pass audit (skill_audit PROOF-27 for RULE-13).
#
# This used to be Phase E of dev/test_e2e_cross_model_audit.sh, which is scoped
# to the gemini-cli environment and skips whole when that CLI is absent. Nothing
# here calls gemini: the configured command is dev/fake_audit_llm.sh, a
# deterministic wrapper, so every host can run this and RULE-13 has local
# evidence instead of evidence only a gemini machine could produce.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

export PURLIN_PROOF_TIER="e2e"
# No PURLIN_PROOF_PLATFORMS: the fake LLM wrapper is a file in this repo, so the
# entry belongs in the agnostic proof file (proof_common RULE-17).

echo "=== e2e_fake_audit_llm tests ==="

FAKE_LLM="$REAL_PROJECT_ROOT/dev/fake_audit_llm.sh"

# --- Helper: construct the Pass 2 (semantic-only) prompt ---
# The same prompt the audit skill builds after Pass 1: structural checks have
# already run, so the model is asked for STRONG or WEAK only. Written to a temp
# file whose path is printed, which avoids quoting the test code through a shell.
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
    printf '\n%s\n' 'Rate each: STRONG (test matches rule intent) or WEAK (test partially matches, something is missing or too loose).'
    printf '%s\n' 'Do NOT check for structural issues, those were already handled.'
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

# --- Helper: parse the ASSESSMENT for a given PROOF-ID out of a reply ---
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

  # Fallback: looser matching (case-insensitive, within 8 lines of the proof ID)
  if [[ -z "$assessment" ]]; then
    assessment=$(echo "$response" | grep -A8 "PROOF-ID:.*$proof_id" | grep -i "^ASSESSMENT" | head -1 | sed 's/^[Aa][Ss][Ss][Ee][Ss][Ss][Mm][Ee][Nn][Tt]:[ \t]*//' | awk '{print $1}')
  fi

  echo "$assessment"
}

# --- Helper: parse one named field for a PROOF-ID ---
# Collects multi-line values: reads from the field line until the next known
# field marker (PROOF-ID:, RULE-ID:, ASSESSMENT:, CRITERION:, WHY:, FIX:, ---)
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
# Custom audit LLM command in config (fake LLM wrapper)
# ==========================================================================
echo "  --- Custom audit LLM command in config ---"

TMPDIR_E=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR_E"

# Step 1: Create project with fake LLM in config (simulates purlin:init --audit-llm)
mkdir -p "$TMPDIR_E/.purlin" "$TMPDIR_E/specs/auth" "$TMPDIR_E/scripts/mcp"
cp "$REAL_PROJECT_ROOT/scripts/mcp/purlin_server.py" "$TMPDIR_E/scripts/mcp/purlin_server.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/config_engine.py" "$TMPDIR_E/scripts/mcp/config_engine.py"
cp "$REAL_PROJECT_ROOT/scripts/mcp/__init__.py" "$TMPDIR_E/scripts/mcp/__init__.py" 2>/dev/null || true

# Config points to our fake LLM, the same pattern a real user would configure
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

# Step 2: Test the init ping (the same test purlin:init --audit-llm runs)
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

# Step 3: Read config back to verify both fields were stored
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

STATIC_EXIT_E=0
STATIC_OUT_E=$(python3 "$REAL_PROJECT_ROOT/scripts/audit/static_checks.py" \
  "$TMPDIR_E/test_login.py" "login" \
  --spec-path "$TMPDIR_E/specs/auth/login.md" 2>&1) || STATIC_EXIT_E=$?

static_ok=false
if [[ "$STATIC_EXIT_E" == "0" ]]; then
  echo "    Pass 1: both proofs passed static checks"
  static_ok=true
else
  echo "    Pass 1 FAIL: exit $STATIC_EXIT_E"
  echo "$STATIC_OUT_E" | head -20
fi

# Step 5: Send the surviving proofs to the configured fake LLM (Pass 2)
PASS2_PROMPT_E=$(build_pass2_prompt "$TMPDIR_E/specs/auth/login.md" "$(cat "$TMPDIR_E/test_login.py")" \
  "PROOF-1|RULE-1" "PROOF-2|RULE-2")

echo "    Pass 2: Calling configured fake LLM..."
# The prompt is read from a file rather than substituted into {prompt}, which
# keeps the test code's quotes and $ out of a shell word.
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

# Step 6: Parse the remaining fields out of the fake LLM reply
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

SUITE_RC=0
if $ping_ok && $config_ok && $static_ok && $llm_ok && $fields_ok; then
  echo "    PASS: custom LLM configured, init ping works, two-pass audit completes"
  purlin_proof "skill_audit" "PROOF-27" "RULE-13" pass "custom audit LLM configured and used in the two-pass flow"
else
  echo "    FAIL: ping=$ping_ok config=$config_ok static=$static_ok llm=$llm_ok fields=$fields_ok"
  purlin_proof "skill_audit" "PROOF-27" "RULE-13" fail "custom audit LLM flow incomplete"
  SUITE_RC=1
fi

# --- Emit proof files ---
export PROJECT_ROOT="$REAL_PROJECT_ROOT"
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_fake_audit_llm: 1 proof recorded"
exit $SUITE_RC
