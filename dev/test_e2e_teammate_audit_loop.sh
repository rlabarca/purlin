#!/usr/bin/env bash
# E2E test: Teammate Audit Loop
# 7 proofs covering 7 rules — all @e2e.
# Verifies that the skill definitions document the teammate communication protocol.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Load proof harness
source "$PROJECT_ROOT/scripts/proof/shell_purlin.sh"

echo "=== e2e_teammate_audit_loop tests ==="

AUDIT_SKILL="$PROJECT_ROOT/skills/audit/SKILL.md"
BUILD_SKILL="$PROJECT_ROOT/skills/build/SKILL.md"
VERIFY_SKILL="$PROJECT_ROOT/skills/verify/SKILL.md"

# ==========================================================================
# PROOF-1: Audit skill has teammate mode with criteria and assessment levels
# ==========================================================================
echo "  --- PROOF-1: Audit teammate mode documents criteria and assessment ---"

audit_content=$(cat "$AUDIT_SKILL")
proof1_ok=true

if ! echo "$audit_content" | grep -q "## Teammate Mode"; then
  echo "    FAIL: Missing '## Teammate Mode' section in audit skill"
  proof1_ok=false
fi
if ! echo "$audit_content" | grep -q "audit_criteria.md"; then
  echo "    FAIL: Missing audit_criteria.md reference in teammate mode"
  proof1_ok=false
fi
if ! echo "$audit_content" | grep -q "STRONG/WEAK/HOLLOW"; then
  echo "    FAIL: Missing STRONG/WEAK/HOLLOW in teammate mode"
  proof1_ok=false
fi

if $proof1_ok; then
  echo "    PASS: Audit teammate mode documents criteria and assessment levels"
  purlin_proof "e2e_teammate_audit_loop" "PROOF-1" "RULE-1" pass "audit teammate mode documents criteria reading and STRONG/WEAK/HOLLOW assessment"
else
  purlin_proof "e2e_teammate_audit_loop" "PROOF-1" "RULE-1" fail "audit teammate mode missing criteria or assessment documentation"
fi

# ==========================================================================
# PROOF-2: Audit teammate mode instructs messaging the builder
# ==========================================================================
echo "  --- PROOF-2: Audit teammate mode messages builder with findings ---"

# Extract teammate mode section (everything from ## Teammate Mode to the next ## heading)
teammate_section=$(awk '/^## Teammate Mode/{found=1; next} /^## [A-Z]/{if(found) exit} found' "$AUDIT_SKILL")
proof2_ok=true

if ! echo "$teammate_section" | grep -q "purlin-builder"; then
  echo "    FAIL: Missing purlin-builder reference in teammate mode"
  proof2_ok=false
fi
if ! echo "$teammate_section" | grep -qi "message"; then
  echo "    FAIL: Missing message instruction in teammate mode"
  proof2_ok=false
fi

if $proof2_ok; then
  echo "    PASS: Audit teammate mode instructs messaging the builder"
  purlin_proof "e2e_teammate_audit_loop" "PROOF-2" "RULE-2" pass "audit teammate mode instructs messaging purlin-builder with findings"
else
  purlin_proof "e2e_teammate_audit_loop" "PROOF-2" "RULE-2" fail "audit teammate mode missing builder messaging protocol"
fi

# ==========================================================================
# PROOF-3: Build skill has teammate mode with fix-and-message-back protocol
# ==========================================================================
echo "  --- PROOF-3: Build teammate mode fixes proofs and messages auditor ---"

build_content=$(cat "$BUILD_SKILL")
proof3_ok=true

if ! echo "$build_content" | grep -q "## Teammate Mode"; then
  echo "    FAIL: Missing '## Teammate Mode' section in build skill"
  proof3_ok=false
fi
if ! echo "$build_content" | grep -q "purlin-auditor"; then
  echo "    FAIL: Missing purlin-auditor reference in build teammate mode"
  proof3_ok=false
fi
# Check for fix + message back protocol
if ! echo "$build_content" | grep -q "Fix the test"; then
  # Also accept "Fix the test" or "fix" in the teammate section
  if ! echo "$build_content" | grep -qi "fix.*proof\|proof.*fix"; then
    echo "    FAIL: Missing fix instruction in build teammate mode"
    proof3_ok=false
  fi
fi
if ! echo "$build_content" | grep -qi "message.*auditor\|auditor.*message\|Re-audit"; then
  echo "    FAIL: Missing message-back-to-auditor instruction"
  proof3_ok=false
fi

if $proof3_ok; then
  echo "    PASS: Build teammate mode documents fix-and-message protocol"
  purlin_proof "e2e_teammate_audit_loop" "PROOF-3" "RULE-3" pass "build teammate mode fixes proofs and messages auditor back"
else
  purlin_proof "e2e_teammate_audit_loop" "PROOF-3" "RULE-3" fail "build teammate mode missing fix or message-back protocol"
fi

# ==========================================================================
# PROOF-4: Audit teammate mode re-checks fixed proofs
# ==========================================================================
echo "  --- PROOF-4: Audit teammate mode re-checks after builder fix ---"

proof4_ok=true

if ! echo "$teammate_section" | grep -qi "re-read\|reread\|re-assess\|reassess"; then
  echo "    FAIL: Missing re-read/re-assess in audit teammate mode"
  proof4_ok=false
fi

if $proof4_ok; then
  echo "    PASS: Audit teammate mode documents re-check loop"
  purlin_proof "e2e_teammate_audit_loop" "PROOF-4" "RULE-4" pass "audit teammate mode re-reads and re-assesses fixed proofs"
else
  purlin_proof "e2e_teammate_audit_loop" "PROOF-4" "RULE-4" fail "audit teammate mode missing re-check documentation"
fi

# ==========================================================================
# PROOF-5: Audit teammate mode terminates after 3 rounds
# ==========================================================================
echo "  --- PROOF-5: Audit teammate mode has 3-round termination ---"

proof5_ok=true

if ! echo "$teammate_section" | grep -q "3 rounds"; then
  echo "    FAIL: Missing '3 rounds' termination condition"
  proof5_ok=false
fi

if $proof5_ok; then
  echo "    PASS: Audit teammate mode has 3-round termination"
  purlin_proof "e2e_teammate_audit_loop" "PROOF-5" "RULE-5" pass "audit teammate mode terminates after 3 rounds on any single proof"
else
  purlin_proof "e2e_teammate_audit_loop" "PROOF-5" "RULE-5" fail "audit teammate mode missing termination condition"
fi

# ==========================================================================
# PROOF-6: Verify Step 4e documents teammate mode with integrity score
# ==========================================================================
echo "  --- PROOF-6: Verify Step 4e has teammate mode ---"

verify_content=$(cat "$VERIFY_SKILL")
proof6_ok=true

if ! echo "$verify_content" | grep -q "purlin-auditor"; then
  echo "    FAIL: Missing purlin-auditor reference in verify skill"
  proof6_ok=false
fi
if ! echo "$verify_content" | grep -qi "integrity score"; then
  echo "    FAIL: Missing integrity score reference in verify teammate mode"
  proof6_ok=false
fi

if $proof6_ok; then
  echo "    PASS: Verify Step 4e documents teammate mode"
  purlin_proof "e2e_teammate_audit_loop" "PROOF-6" "RULE-6" pass "verify Step 4e documents teammate mode with integrity score and purlin-auditor"
else
  purlin_proof "e2e_teammate_audit_loop" "PROOF-6" "RULE-6" fail "verify skill missing teammate mode documentation"
fi

# ==========================================================================
# PROOF-7: Audit teammate mode handles invariant rules by messaging lead
# ==========================================================================
echo "  --- PROOF-7: Audit teammate invariant rule handling ---"

proof7_ok=true

# Check for invariant handling within the teammate mode section (scoped, not whole file)
if ! echo "$teammate_section" | grep -qi "invariant"; then
  echo "    FAIL: Missing invariant rule handling in teammate mode section"
  proof7_ok=false
fi
if ! echo "$teammate_section" | grep -qi "message.*lead\|lead.*message"; then
  echo "    FAIL: Missing instruction to message the lead for ambiguous invariant rules in teammate mode section"
  proof7_ok=false
fi

if $proof7_ok; then
  echo "    PASS: Audit teammate mode handles invariant rules correctly"
  purlin_proof "e2e_teammate_audit_loop" "PROOF-7" "RULE-7" pass "audit teammate mode messages lead for ambiguous invariant rules"
else
  purlin_proof "e2e_teammate_audit_loop" "PROOF-7" "RULE-7" fail "audit teammate mode missing invariant rule handling"
fi

# --- Emit proof files ---
export PROJECT_ROOT
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_teammate_audit_loop: 7 proofs recorded"
