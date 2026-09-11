#!/usr/bin/env bash
# E2E test: Verify-Audit-Build Loop
# 7 proofs covering 7 rules — all @e2e.
# Verifies that the skill definitions document the audit -> purlin:build remediation protocol.
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
# PROOF-1: Audit skill has independent auditor mode with criteria and assessment levels
# ==========================================================================
echo "  --- PROOF-1: Audit independent auditor mode documents criteria and assessment ---"

audit_content=$(cat "$AUDIT_SKILL")
proof1_ok=true

if ! echo "$audit_content" | grep -q "## When Running as Independent Auditor"; then
  echo "    FAIL: Missing '## When Running as Independent Auditor' section in audit skill"
  proof1_ok=false
fi
# Scope criteria and assessment checks to the Independent Auditor section
auditor_section=$(awk '/^## When Running as Independent Auditor/{found=1; next} /^## [A-Z]/{if(found) exit} found' "$AUDIT_SKILL")
# RULE-4 requires the section to document reading the criteria. The skill points at the
# single loader (Step 1 / --load-criteria) rather than restating audit_criteria.md here,
# per the no-duplication rule in CLAUDE.md.
if ! echo "$auditor_section" | grep -q -- "--load-criteria"; then
  echo "    FAIL: Missing criteria-loading instruction (--load-criteria) in independent auditor section"
  proof1_ok=false
fi
if ! (echo "$auditor_section" | grep -q "STRONG" && echo "$auditor_section" | grep -q "WEAK" && echo "$auditor_section" | grep -q "HOLLOW"); then
  echo "    FAIL: Missing STRONG/WEAK/HOLLOW assessment levels in independent auditor section"
  proof1_ok=false
fi

if $proof1_ok; then
  echo "    PASS: Audit independent auditor mode documents criteria and assessment levels"
  purlin_proof "skill_audit" "PROOF-4" "RULE-4" pass "audit independent auditor mode documents criteria reading and STRONG/WEAK/HOLLOW assessment"
else
  purlin_proof "skill_audit" "PROOF-4" "RULE-4" fail "audit independent auditor mode missing criteria or assessment documentation"
fi

# ==========================================================================
# PROOF-2: Audit independent auditor mode routes findings to purlin:build
# ==========================================================================
echo "  --- PROOF-2: Audit independent auditor mode routes findings to purlin:build ---"

# Extract independent auditor section (everything from ## When Running as Independent Auditor to the next ## heading)
auditor_section=$(awk '/^## When Running as Independent Auditor/{found=1; next} /^## [A-Z]/{if(found) exit} found' "$AUDIT_SKILL")
proof2_ok=true

if ! echo "$auditor_section" | grep -q "purlin:build"; then
  echo "    FAIL: Missing purlin:build remediation route in independent auditor mode"
  proof2_ok=false
fi
if ! echo "$auditor_section" | grep -qi "read-only"; then
  echo "    FAIL: Missing read-only statement in independent auditor mode"
  proof2_ok=false
fi
if echo "$auditor_section" | grep -q "purlin-builder"; then
  echo "    FAIL: purlin-builder is retired but still referenced in independent auditor mode"
  proof2_ok=false
fi

if $proof2_ok; then
  echo "    PASS: Audit independent auditor mode routes findings to purlin:build"
  purlin_proof "skill_audit" "PROOF-5" "RULE-5" pass "audit independent auditor mode routes HOLLOW/WEAK findings to purlin:build and states the audit is read-only"
else
  purlin_proof "skill_audit" "PROOF-5" "RULE-5" fail "audit independent auditor mode missing purlin:build remediation route"
fi

# ==========================================================================
# PROOF-3: Build skill has proof fixer mode with fix-and-report protocol
# ==========================================================================
echo "  --- PROOF-3: Build proof fixer mode fixes proofs and reports back ---"

build_content=$(cat "$BUILD_SKILL")
proof3_ok=true

if ! echo "$build_content" | grep -q "## When Running as Proof Fixer"; then
  echo "    FAIL: Missing '## When Running as Proof Fixer' section in build skill"
  proof3_ok=false
fi
# Extract the build skill's Proof Fixer section
build_fixer=$(awk '/^## When Running as Proof Fixer/{found=1; next} /^## [A-Z]/{if(found) exit} found' "$BUILD_SKILL")
if ! echo "$build_fixer" | grep -qi "audit\|auditor"; then
  echo "    FAIL: Missing auditor reference in build proof fixer section"
  proof3_ok=false
fi
# Check for fix + report back protocol
if ! echo "$build_fixer" | grep -qi "fix.*proof\|proof.*fix\|Fix the test"; then
  echo "    FAIL: Missing fix instruction in build proof fixer section"
  proof3_ok=false
fi
if ! echo "$build_fixer" | grep -qi "report\|Re-audit"; then
  echo "    FAIL: Missing report-back in build proof fixer section"
  proof3_ok=false
fi

if $proof3_ok; then
  echo "    PASS: Build proof fixer mode documents fix-and-report protocol"
  purlin_proof "skill_build" "PROOF-8" "RULE-8" pass "build proof fixer mode fixes proofs and reports back"
else
  purlin_proof "skill_build" "PROOF-8" "RULE-8" fail "build proof fixer mode missing fix or report protocol"
fi

# ==========================================================================
# PROOF-4: Audit independent auditor mode re-audits fixed proofs
# ==========================================================================
echo "  --- PROOF-4: Audit independent auditor mode re-audits after fixes land ---"

proof4_ok=true

if ! echo "$auditor_section" | grep -qi "re-audit\|reaudit\|re-assess\|reassess"; then
  echo "    FAIL: Missing re-audit/re-assess in independent auditor mode"
  proof4_ok=false
fi

if $proof4_ok; then
  echo "    PASS: Audit independent auditor mode documents re-audit loop"
  purlin_proof "skill_audit" "PROOF-6" "RULE-6" pass "audit independent auditor mode re-audits fixed proofs"
else
  purlin_proof "skill_audit" "PROOF-6" "RULE-6" fail "audit independent auditor mode missing re-audit documentation"
fi

# ==========================================================================
# PROOF-5: Audit independent auditor mode terminates after 3 rounds
# ==========================================================================
echo "  --- PROOF-5: Audit independent auditor mode has 3-round termination ---"

proof5_ok=true

if ! echo "$auditor_section" | grep -q "3 rounds"; then
  echo "    FAIL: Missing '3 rounds' termination condition"
  proof5_ok=false
fi

if $proof5_ok; then
  echo "    PASS: Audit independent auditor mode has 3-round termination"
  purlin_proof "skill_audit" "PROOF-7" "RULE-7" pass "audit independent auditor mode terminates after 3 rounds on any single proof"
else
  purlin_proof "skill_audit" "PROOF-7" "RULE-7" fail "audit independent auditor mode missing termination condition"
fi

# ==========================================================================
# PROOF-6: Verify Step 4e documents independent audit with integrity score
# ==========================================================================
echo "  --- PROOF-6: Verify Step 4e has independent audit ---"

verify_content=$(cat "$VERIFY_SKILL")
proof6_ok=true

# Extract the verify skill's Step 4e block (from Step 4e heading to next ## or ### Step heading)
verify_audit=$(awk '/^### Step 4e/{found=1} found{print} /^### Step 5|^## /{if(found && !/^### Step 4e/) exit}' "$VERIFY_SKILL")
if ! echo "$verify_audit" | grep -q "purlin-auditor"; then
  echo "    FAIL: Missing purlin-auditor reference in verify Step 4e section"
  proof6_ok=false
fi
if ! echo "$verify_audit" | grep -qi "integrity score"; then
  echo "    FAIL: Missing integrity score reference in verify Step 4e section"
  proof6_ok=false
fi

if $proof6_ok; then
  echo "    PASS: Verify Step 4e documents independent audit"
  purlin_proof "skill_verify" "PROOF-6" "RULE-6" pass "verify Step 4e documents independent audit with integrity score and purlin-auditor"
else
  purlin_proof "skill_verify" "PROOF-6" "RULE-6" fail "verify skill missing independent audit documentation"
fi

# ==========================================================================
# PROOF-7: Audit anchor rule handling
# ==========================================================================
echo "  --- PROOF-7: Audit anchor rule handling ---"

proof7_ok=true

# Check for anchor handling section (may be in the independent auditor section or a separate subsection)
anchor_section=$(awk '/^### Anchor Rule Handling/{found=1; next} /^(## |### [A-Z])/{if(found) exit} found' "$AUDIT_SKILL")
if [[ -z "$anchor_section" ]]; then
  # Fall back to checking the full auditor section
  anchor_section="$auditor_section"
fi
if ! echo "$anchor_section" | grep -qi "anchor"; then
  echo "    FAIL: Missing anchor rule handling section"
  proof7_ok=false
fi
if ! echo "$anchor_section" | grep -qi "report\|lead"; then
  echo "    FAIL: Missing instruction to report to the lead for ambiguous anchor rules"
  proof7_ok=false
fi

if $proof7_ok; then
  echo "    PASS: Audit anchor rule handling documented correctly"
  purlin_proof "skill_audit" "PROOF-8" "RULE-8" pass "audit anchor rule handling reports to lead for ambiguous anchor rules"
else
  purlin_proof "skill_audit" "PROOF-8" "RULE-8" fail "audit missing anchor rule handling"
fi

# --- Emit proof files ---
export PROJECT_ROOT
cd "$PROJECT_ROOT"
purlin_proof_finish

echo ""
echo "e2e_teammate_audit_loop: 7 proofs recorded"
