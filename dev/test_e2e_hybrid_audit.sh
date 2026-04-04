#!/usr/bin/env bash
# E2E test: Hybrid Audit — deterministic static checks + semantic pass
# 5 phases testing the two-pass audit architecture.
# Creates temp projects with deliberately flawed and valid tests.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
STATIC_CHECKS="$REAL_PROJECT_ROOT/scripts/audit/static_checks.py"

# Load proof harness
source "$REAL_PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_hybrid_audit tests ==="

# --- Cleanup ---
ALL_TMPDIRS=""
cleanup_all() { for d in $ALL_TMPDIRS; do rm -rf "$d" 2>/dev/null; done; }
trap cleanup_all EXIT

# --- Helper: create temp dir with a spec ---
create_test_env() {
  local tmpdir
  tmpdir=$(mktemp -d)
  ALL_TMPDIRS="$ALL_TMPDIRS $tmpdir"
  mkdir -p "$tmpdir/specs/auth"

  cat > "$tmpdir/specs/auth/login.md" << 'SPECEOF'
# Feature: login

## What it does

Login feature for testing.

## Rules

- RULE-1: Returns 200 with JWT on valid credentials
- RULE-2: Returns 401 on invalid password
- RULE-3: Passwords hashed with bcrypt

## Proof

- PROOF-1 (RULE-1): POST valid credentials; verify 200 and JWT
- PROOF-2 (RULE-2): POST invalid password; verify 401
- PROOF-3 (RULE-3): Verify bcrypt hashing used
SPECEOF
  echo "$tmpdir"
}

# ==========================================================================
# Phase A — assert True detected deterministically
# ==========================================================================
echo "  --- Phase A: assert True → HOLLOW (deterministic) ---"
TMPDIR_A=$(create_test_env)

cat > "$TMPDIR_A/test_login.py" << 'PYEOF'
import pytest

@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_valid_login():
    assert True

@pytest.mark.proof("login", "PROOF-2", "RULE-2")
def test_invalid_login():
    resp = mock_post("/login", {"pass": "wrong"})
    assert resp == 401
PYEOF

OUTPUT_A=$(python3 "$STATIC_CHECKS" "$TMPDIR_A/test_login.py" "login" --spec-path "$TMPDIR_A/specs/auth/login.md" 2>&1 || true)
PROOF1_STATUS=$(echo "$OUTPUT_A" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-1',{}).get('status','missing'))")
PROOF1_CHECK=$(echo "$OUTPUT_A" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-1',{}).get('check','none'))")
PROOF2_STATUS=$(echo "$OUTPUT_A" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-2',{}).get('status','missing'))")

if [[ "$PROOF1_STATUS" == "fail" && "$PROOF1_CHECK" == "assert_true" && "$PROOF2_STATUS" == "pass" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-1" "RULE-1" pass "assert True detected as HOLLOW, valid test passes"
  echo "    PASS: assert True → fail/assert_true, valid test → pass"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-1" "RULE-1" fail "Expected PROOF-1=fail/assert_true, PROOF-2=pass; got $PROOF1_STATUS/$PROOF1_CHECK, $PROOF2_STATUS"
  echo "    FAIL: got PROOF-1=$PROOF1_STATUS/$PROOF1_CHECK, PROOF-2=$PROOF2_STATUS"
fi

# ==========================================================================
# Phase B — no assertions detected deterministically
# ==========================================================================
echo "  --- Phase B: no assertions → HOLLOW (deterministic) ---"
TMPDIR_B=$(create_test_env)

cat > "$TMPDIR_B/test_login.py" << 'PYEOF'
import pytest

@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_valid_login():
    resp = mock_post("/login", {"user": "alice", "pass": "secret"})
    # no assertion — just runs the code
PYEOF

OUTPUT_B=$(python3 "$STATIC_CHECKS" "$TMPDIR_B/test_login.py" "login" 2>&1 || true)
PROOF1_STATUS_B=$(echo "$OUTPUT_B" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-1',{}).get('status','missing'))")
PROOF1_CHECK_B=$(echo "$OUTPUT_B" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-1',{}).get('check','none'))")

if [[ "$PROOF1_STATUS_B" == "fail" && "$PROOF1_CHECK_B" == "no_assertions" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-2" "RULE-2" pass "no_assertions detected"
  echo "    PASS: no assertions detected"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-2" "RULE-2" fail "Expected fail/no_assertions; got $PROOF1_STATUS_B/$PROOF1_CHECK_B"
  echo "    FAIL: got $PROOF1_STATUS_B/$PROOF1_CHECK_B"
fi

# ==========================================================================
# Phase C — logic mirroring detected deterministically
# ==========================================================================
echo "  --- Phase C: logic mirroring → HOLLOW (deterministic) ---"
TMPDIR_C=$(create_test_env)

cat > "$TMPDIR_C/test_login.py" << 'PYEOF'
import pytest

@pytest.mark.proof("login", "PROOF-3", "RULE-3")
def test_bcrypt_hash():
    from auth import hash_password
    expected = hash_password("secret")
    result = hash_password("secret")
    assert result == expected
PYEOF

OUTPUT_C=$(python3 "$STATIC_CHECKS" "$TMPDIR_C/test_login.py" "login" --spec-path "$TMPDIR_C/specs/auth/login.md" 2>&1 || true)
PROOF3_STATUS_C=$(echo "$OUTPUT_C" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-3',{}).get('status','missing'))")
PROOF3_CHECK_C=$(echo "$OUTPUT_C" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-3',{}).get('check','none'))")

if [[ "$PROOF3_STATUS_C" == "fail" && "$PROOF3_CHECK_C" == "logic_mirroring" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-3" "RULE-3" pass "logic mirroring detected"
  echo "    PASS: logic mirroring detected"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-3" "RULE-3" fail "Expected fail/logic_mirroring; got $PROOF3_STATUS_C/$PROOF3_CHECK_C"
  echo "    FAIL: got $PROOF3_STATUS_C/$PROOF3_CHECK_C"
fi

# ==========================================================================
# Phase D — structurally valid but semantically weak
# ==========================================================================
echo "  --- Phase D: structurally valid test passes Pass 1 ---"
TMPDIR_D=$(create_test_env)

# This test checks status code but NOT the error body — structurally fine but semantically weak
cat > "$TMPDIR_D/test_login.py" << 'PYEOF'
import pytest

@pytest.mark.proof("login", "PROOF-2", "RULE-2")
def test_invalid_login():
    resp = client.post("/login", json={"user": "alice", "pass": "wrong"})
    assert resp.status_code == 401
    # Doesn't check error body — WEAK semantically but passes structural check
PYEOF

OUTPUT_D=$(python3 "$STATIC_CHECKS" "$TMPDIR_D/test_login.py" "login" --spec-path "$TMPDIR_D/specs/auth/login.md" 2>&1 || true)
EXIT_D=$?
PROOF2_STATUS_D=$(echo "$OUTPUT_D" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-2',{}).get('status','missing'))")

if [[ "$PROOF2_STATUS_D" == "pass" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-4" "RULE-4" pass "structurally valid test passes Pass 1"
  echo "    PASS: structurally valid test passes static checks (exit $EXIT_D)"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-4" "RULE-4" fail "Expected pass; got $PROOF2_STATUS_D"
  echo "    FAIL: expected pass, got $PROOF2_STATUS_D"
fi

# ==========================================================================
# Phase E — strong test passes both passes
# ==========================================================================
echo "  --- Phase E: strong test passes structural checks ---"
TMPDIR_E=$(create_test_env)

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

@pytest.mark.proof("login", "PROOF-3", "RULE-3")
def test_bcrypt_hashing():
    import bcrypt
    stored_hash = get_stored_hash("alice")
    assert bcrypt.checkpw(b"secret", stored_hash)
PYEOF

OUTPUT_E=$(python3 "$STATIC_CHECKS" "$TMPDIR_E/test_login.py" "login" --spec-path "$TMPDIR_E/specs/auth/login.md" 2>&1)
EXIT_E=$?
ALL_PASS_E=$(echo "$OUTPUT_E" | python3 -c "import json,sys; d=json.load(sys.stdin); print('true' if all(p['status']=='pass' for p in d['proofs']) else 'false')")
PROOF_COUNT_E=$(echo "$OUTPUT_E" | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['proofs']))")

if [[ "$ALL_PASS_E" == "true" && "$EXIT_E" == "0" && "$PROOF_COUNT_E" == "3" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-5" "RULE-5" pass "all 3 strong tests pass structural checks with exit 0"
  echo "    PASS: 3/3 proofs pass structural checks, exit 0"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-5" "RULE-5" fail "Expected all pass exit 0 count 3; got $ALL_PASS_E exit $EXIT_E count $PROOF_COUNT_E"
  echo "    FAIL: all_pass=$ALL_PASS_E exit=$EXIT_E count=$PROOF_COUNT_E"
fi

# ==========================================================================
# Phase F — JSON output format validation
# ==========================================================================
echo "  --- Phase F: JSON output has required fields ---"

# Reuse output from Phase A which has both pass and fail proofs
HAS_FIELDS=$(echo "$OUTPUT_A" | python3 -c "
import json, sys
d = json.load(sys.stdin)
ok = 'proofs' in d and isinstance(d['proofs'], list)
for p in d['proofs']:
    for f in ['proof_id', 'rule_id', 'test_name', 'status', 'reason']:
        if f not in p:
            ok = False
print('true' if ok else 'false')
")

if [[ "$HAS_FIELDS" == "true" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-6" "RULE-6" pass "JSON output has all required fields"
  echo "    PASS: JSON has proofs array with required fields"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-6" "RULE-6" fail "Missing required fields in JSON output"
  echo "    FAIL: missing required fields"
fi

# ==========================================================================
# Phase G — Exit codes
# ==========================================================================
echo "  --- Phase G: Exit 0 always, defects reported in JSON ---"

# Exit 0 from Phase E (all pass) and exit 0 from Phase A (has failures — defects in JSON)
EXIT_CLEAN=$EXIT_E
EXIT_DEFECTS=0
DEFECTS_OUTPUT=$(python3 "$STATIC_CHECKS" "$TMPDIR_A/test_login.py" "login" --spec-path "$TMPDIR_A/specs/auth/login.md" 2>&1) || EXIT_DEFECTS=$?
HAS_FAIL=$(echo "$DEFECTS_OUTPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print('true' if any(p['status']=='fail' for p in d['proofs']) else 'false')")

if [[ "$EXIT_CLEAN" == "0" && "$EXIT_DEFECTS" == "0" && "$HAS_FAIL" == "true" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-7" "RULE-7" pass "exit 0 on clean and on failures; defects reported via JSON status=fail"
  echo "    PASS: exit 0 (clean), exit 0 (failures with status=fail in JSON)"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-7" "RULE-7" fail "Expected exit 0/0 with JSON fail; got exit_clean=$EXIT_CLEAN exit_defects=$EXIT_DEFECTS has_fail=$HAS_FAIL"
  echo "    FAIL: got exit_clean=$EXIT_CLEAN exit_defects=$EXIT_DEFECTS has_fail=$HAS_FAIL"
fi

# ==========================================================================
# Phase H — mock_target_match detection
# ==========================================================================
echo "  --- Phase H: mock target match detected ---"
TMPDIR_H=$(create_test_env)

cat > "$TMPDIR_H/test_login.py" << 'PYEOF'
import pytest
from unittest.mock import patch

@pytest.mark.proof("login", "PROOF-3", "RULE-3")
@patch("auth.bcrypt.checkpw")
def test_bcrypt_mocked(mock_checkpw):
    mock_checkpw.return_value = True
    result = login("alice", "secret")
    assert result.status_code == 200
PYEOF

OUTPUT_H=$(python3 "$STATIC_CHECKS" "$TMPDIR_H/test_login.py" "login" --spec-path "$TMPDIR_H/specs/auth/login.md" 2>&1 || true)
PROOF3_STATUS_H=$(echo "$OUTPUT_H" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-3',{}).get('status','missing'))")
PROOF3_CHECK_H=$(echo "$OUTPUT_H" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-3',{}).get('check','none'))")

if [[ "$PROOF3_STATUS_H" == "fail" && "$PROOF3_CHECK_H" == "mock_target_match" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-8" "RULE-8" pass "mock_target_match detected"
  echo "    PASS: mock target match detected"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-8" "RULE-8" fail "Expected fail/mock_target_match; got $PROOF3_STATUS_H/$PROOF3_CHECK_H"
  echo "    FAIL: got $PROOF3_STATUS_H/$PROOF3_CHECK_H"
fi

# ==========================================================================
# Phase I — bare except detection
# ==========================================================================
echo "  --- Phase I: bare except:pass detected ---"
TMPDIR_I=$(create_test_env)

cat > "$TMPDIR_I/test_login.py" << 'PYEOF'
import pytest

@pytest.mark.proof("login", "PROOF-1", "RULE-1")
def test_with_bare_except():
    try:
        result = client.post("/login", json={"user": "alice", "pass": "secret"})
    except Exception:
        pass
    assert result.status_code == 200
PYEOF

OUTPUT_I=$(python3 "$STATIC_CHECKS" "$TMPDIR_I/test_login.py" "login" 2>&1 || true)
PROOF1_STATUS_I=$(echo "$OUTPUT_I" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-1',{}).get('status','missing'))")
PROOF1_CHECK_I=$(echo "$OUTPUT_I" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-1',{}).get('check','none'))")

if [[ "$PROOF1_STATUS_I" == "fail" && "$PROOF1_CHECK_I" == "bare_except" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-9" "RULE-9" pass "bare except detected"
  echo "    PASS: bare except detected"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-9" "RULE-9" fail "Expected fail/bare_except; got $PROOF1_STATUS_I/$PROOF1_CHECK_I"
  echo "    FAIL: got $PROOF1_STATUS_I/$PROOF1_CHECK_I"
fi

# ==========================================================================
# Phase J — Pass 0: spec coverage check (structural vs behavioral)
# ==========================================================================
echo "  --- Phase J: Pass 0 spec coverage check ---"
TMPDIR_J=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR_J"
mkdir -p "$TMPDIR_J/specs/instructions"

# Create a structural-only spec
cat > "$TMPDIR_J/specs/instructions/agent_def.md" << 'SPECEOF'
# Feature: agent_def

## What it does

Agent definition structural checks.

## Rules

- RULE-1: Verify agent.md contains ## Core Loop section
- RULE-2: Grep skill files for ## Usage heading
- RULE-3: Verify config field appears in output

## Proof

- PROOF-1 (RULE-1): Grep agent.md for heading
- PROOF-2 (RULE-2): Grep skill files
- PROOF-3 (RULE-3): Grep config output
SPECEOF

# Create a behavioral spec
cat > "$TMPDIR_J/specs/instructions/login.md" << 'SPECEOF'
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

# Check structural-only spec
OUTPUT_J_STRUCT=$(python3 "$STATIC_CHECKS" --check-spec-coverage --spec-path "$TMPDIR_J/specs/instructions/agent_def.md" 2>&1)
STRUCT_ONLY=$(echo "$OUTPUT_J_STRUCT" | python3 -c "import json,sys; print(json.load(sys.stdin)['structural_only_spec'])")

# Check behavioral spec
OUTPUT_J_BEHAV=$(python3 "$STATIC_CHECKS" --check-spec-coverage --spec-path "$TMPDIR_J/specs/instructions/login.md" 2>&1)
BEHAV_ONLY=$(echo "$OUTPUT_J_BEHAV" | python3 -c "import json,sys; print(json.load(sys.stdin)['structural_only_spec'])")

if [[ "$STRUCT_ONLY" == "True" && "$BEHAV_ONLY" == "False" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-10" "RULE-10" pass "Pass 0 correctly identifies structural-only and behavioral specs"
  echo "    PASS: structural_only=True for grep spec, False for behavioral spec"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-10" "RULE-10" fail "Expected structural=True/behavioral=False; got $STRUCT_ONLY/$BEHAV_ONLY"
  echo "    FAIL: structural=$STRUCT_ONLY behavioral=$BEHAV_ONLY"
fi

# ==========================================================================
# Phase K — Shell if/else pair NOT flagged as hardcoded pass
# ==========================================================================
echo "  --- Phase K: shell if/else pair recognized as conditional proof ---"
TMPDIR_K=$(mktemp -d)
ALL_TMPDIRS="$ALL_TMPDIRS $TMPDIR_K"

cat > "$TMPDIR_K/test_shell_ifelse.sh" << 'SHEOF'
#!/usr/bin/env bash
source shell_purlin.sh
output=$(some_command)
if echo "$output" | grep -q "PASSING"; then
  purlin_proof "shell_feat" "PROOF-1" "RULE-1" pass "checks PASSING"
else
  purlin_proof "shell_feat" "PROOF-1" "RULE-1" fail "checks PASSING"
fi
SHEOF

OUTPUT_K=$(python3 "$STATIC_CHECKS" "$TMPDIR_K/test_shell_ifelse.sh" "shell_feat" 2>&1 || true)
EXIT_K=$?
PROOF1_STATUS_K=$(echo "$OUTPUT_K" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-1',{}).get('status','missing'))")

# Also test that a bare hardcoded pass is still caught
cat > "$TMPDIR_K/test_shell_bare.sh" << 'SHEOF'
#!/usr/bin/env bash
source shell_purlin.sh
purlin_proof "shell_feat" "PROOF-1" "RULE-1" pass "no test here"
SHEOF

OUTPUT_K2=$(python3 "$STATIC_CHECKS" "$TMPDIR_K/test_shell_bare.sh" "shell_feat" 2>&1 || true)
BARE_STATUS=$(echo "$OUTPUT_K2" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-1',{}).get('status','missing'))")
BARE_CHECK=$(echo "$OUTPUT_K2" | python3 -c "import json,sys; d=json.load(sys.stdin); proofs={p['proof_id']:p for p in d['proofs']}; print(proofs.get('PROOF-1',{}).get('check','none'))")

if [[ "$PROOF1_STATUS_K" == "pass" && "$BARE_STATUS" == "fail" && "$BARE_CHECK" == "assert_true" ]]; then
  purlin_proof "e2e_hybrid_audit" "PROOF-11" "RULE-11" pass "if/else pair passes, bare hardcoded pass still caught"
  echo "    PASS: if/else pair → pass, bare pass → fail/assert_true"
else
  purlin_proof "e2e_hybrid_audit" "PROOF-11" "RULE-11" fail "Expected pair=pass, bare=fail/assert_true; got pair=$PROOF1_STATUS_K, bare=$BARE_STATUS/$BARE_CHECK"
  echo "    FAIL: pair=$PROOF1_STATUS_K, bare=$BARE_STATUS/$BARE_CHECK"
fi

# --- Finish ---
purlin_proof_finish
echo "=== e2e_hybrid_audit complete ==="
