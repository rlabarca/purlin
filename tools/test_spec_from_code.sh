#!/bin/bash
# test_spec_from_code.sh — Automated tests for the /pl-spec-from-code command.
# Verifies the command file's structure, role gating, phase coverage,
# template references, and state management instructions.
# Produces tests/spec_from_code/tests.json at project root.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
COMMAND_FILE="$PROJECT_ROOT/.claude/commands/pl-spec-from-code.md"
FEATURE_TEMPLATE="$PROJECT_ROOT/tools/feature_templates/_feature.md"
ANCHOR_TEMPLATE="$PROJECT_ROOT/tools/feature_templates/_anchor.md"
PASS=0
FAIL=0
ERRORS=""

###############################################################################
# Helpers
###############################################################################
log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

echo "=== /pl-spec-from-code Command Tests ==="

###############################################################################
# Scenario: Role gate rejects non-Architect invocation
###############################################################################
echo ""
echo "[Scenario] Role gate rejects non-Architect invocation"

if [ -f "$COMMAND_FILE" ]; then
    log_pass "Command file exists at .claude/commands/pl-spec-from-code.md"
else
    log_fail "Command file missing at .claude/commands/pl-spec-from-code.md"
fi

# Check role gate line
if grep -q "Purlin command owner: Architect" "$COMMAND_FILE"; then
    log_pass "Command has Architect ownership declaration"
else
    log_fail "Missing Architect ownership declaration"
fi

# Check redirect message for non-Architect agents
if grep -q "This is an Architect command" "$COMMAND_FILE"; then
    log_pass "Command has non-Architect redirect message"
else
    log_fail "Missing non-Architect redirect message"
fi

if grep -q "/pl-spec-from-code" "$COMMAND_FILE"; then
    log_pass "Redirect message references /pl-spec-from-code"
else
    log_fail "Redirect message does not reference /pl-spec-from-code"
fi

###############################################################################
# Scenario: Phase 0 creates state file and prompts for directories
###############################################################################
echo ""
echo "[Scenario] Phase 0 creates state file and prompts for directories"

if grep -q "Phase 0" "$COMMAND_FILE"; then
    log_pass "Phase 0 section present"
else
    log_fail "Phase 0 section missing"
fi

if grep -q "sfc_state.json" "$COMMAND_FILE"; then
    log_pass "State file path referenced (sfc_state.json)"
else
    log_fail "State file path not referenced"
fi

if grep -q "AskUserQuestion" "$COMMAND_FILE"; then
    log_pass "AskUserQuestion tool referenced for user prompts"
else
    log_fail "AskUserQuestion tool not referenced"
fi

if grep -q ".purlin/cache/sfc_state.json" "$COMMAND_FILE"; then
    log_pass "State file at correct path (.purlin/cache/)"
else
    log_fail "State file path incorrect (should be .purlin/cache/sfc_state.json)"
fi

###############################################################################
# Scenario: Phase 1 launches parallel sub-agents for codebase survey
###############################################################################
echo ""
echo "[Scenario] Phase 1 launches parallel sub-agents"

if grep -q "Phase 1" "$COMMAND_FILE"; then
    log_pass "Phase 1 section present"
else
    log_fail "Phase 1 section missing"
fi

if grep -q "Explore" "$COMMAND_FILE"; then
    log_pass "Explore sub-agent type referenced"
else
    log_fail "Explore sub-agent type not referenced"
fi

if grep -q "Agent A" "$COMMAND_FILE" && grep -q "Agent B" "$COMMAND_FILE" && grep -q "Agent C" "$COMMAND_FILE"; then
    log_pass "Three sub-agents (A, B, C) described"
else
    log_fail "Not all three sub-agents described"
fi

if grep -q "sfc_inventory.md" "$COMMAND_FILE"; then
    log_pass "Inventory file referenced (sfc_inventory.md)"
else
    log_fail "Inventory file not referenced"
fi

###############################################################################
# Scenario: Phase 2 presents taxonomy for interactive review
###############################################################################
echo ""
echo "[Scenario] Phase 2 taxonomy review"

if grep -q "Phase 2" "$COMMAND_FILE"; then
    log_pass "Phase 2 section present"
else
    log_fail "Phase 2 section missing"
fi

if grep -q "sfc_taxonomy.md" "$COMMAND_FILE"; then
    log_pass "Taxonomy file referenced (sfc_taxonomy.md)"
else
    log_fail "Taxonomy file not referenced"
fi

# Check anchor node type classification
if grep -q "arch_\*" "$COMMAND_FILE" && grep -q "design_\*" "$COMMAND_FILE" && grep -q "policy_\*" "$COMMAND_FILE"; then
    log_pass "All three anchor node types referenced (arch_*, design_*, policy_*)"
else
    log_fail "Not all anchor node types referenced"
fi

###############################################################################
# Scenario: Phase 3 generates anchor nodes before features
###############################################################################
echo ""
echo "[Scenario] Phase 3 generates anchor nodes before features"

if grep -q "Phase 3" "$COMMAND_FILE"; then
    log_pass "Phase 3 section present"
else
    log_fail "Phase 3 section missing"
fi

# Verify anchor nodes before features order
ANCHOR_POS=$(grep -n "Generate Anchor Nodes" "$COMMAND_FILE" | head -1 | cut -d: -f1)
FEATURE_POS=$(grep -n "Generate Features per Category" "$COMMAND_FILE" | head -1 | cut -d: -f1)
if [ -n "$ANCHOR_POS" ] && [ -n "$FEATURE_POS" ] && [ "$ANCHOR_POS" -lt "$FEATURE_POS" ]; then
    log_pass "Anchor nodes generated before features (correct order)"
else
    log_fail "Anchor nodes not generated before features"
fi

###############################################################################
# Scenario: Phase 3 generates features with template compliance
###############################################################################
echo ""
echo "[Scenario] Phase 3 template compliance"

if grep -q "_feature.md" "$COMMAND_FILE"; then
    log_pass "Feature template referenced (_feature.md)"
else
    log_fail "Feature template not referenced"
fi

if grep -q "_anchor.md" "$COMMAND_FILE"; then
    log_pass "Anchor template referenced (_anchor.md)"
else
    log_fail "Anchor template not referenced"
fi

if grep -q "tools/feature_templates/" "$COMMAND_FILE"; then
    log_pass "Template path references tools/feature_templates/"
else
    log_fail "Template path does not reference tools/feature_templates/"
fi

# Check templates actually exist
if [ -f "$FEATURE_TEMPLATE" ]; then
    log_pass "Feature template file exists at tools/feature_templates/_feature.md"
else
    log_fail "Feature template file missing"
fi

if [ -f "$ANCHOR_TEMPLATE" ]; then
    log_pass "Anchor template file exists at tools/feature_templates/_anchor.md"
else
    log_fail "Anchor template file missing"
fi

# Check draft notice requirement
if grep -q "\[Draft\]" "$COMMAND_FILE"; then
    log_pass "Draft notice requirement present for generated scenarios"
else
    log_fail "Draft notice requirement missing"
fi

if grep -q "TODO" "$COMMAND_FILE"; then
    log_pass "TODO status marker referenced for generated features"
else
    log_fail "TODO status marker not referenced"
fi

###############################################################################
# Scenario: Phase 3 creates companion files for features with rich comments
###############################################################################
echo ""
echo "[Scenario] Phase 3 companion files"

if grep -q "impl.md" "$COMMAND_FILE"; then
    log_pass "Companion file (.impl.md) creation referenced"
else
    log_fail "Companion file creation not referenced"
fi

if grep -q "Source Mapping" "$COMMAND_FILE"; then
    log_pass "Source Mapping section required in companion files"
else
    log_fail "Source Mapping section not referenced"
fi

###############################################################################
# Scenario: Phase 3 asks user to confirm each category
###############################################################################
echo ""
echo "[Scenario] Phase 3 category confirmation"

# Count AskUserQuestion references in Phase 3 context
ASK_COUNT=$(grep -c "AskUserQuestion" "$COMMAND_FILE")
if [ "$ASK_COUNT" -ge 2 ]; then
    log_pass "Multiple AskUserQuestion prompts (Phase 0 + Phase 3 confirmation)"
else
    log_fail "Insufficient AskUserQuestion prompts (found $ASK_COUNT, expected >= 2)"
fi

if grep -q "completed_categories" "$COMMAND_FILE"; then
    log_pass "State file tracks completed_categories"
else
    log_fail "State file does not track completed_categories"
fi

###############################################################################
# Scenario: Phase 4 runs CDD status and summarizes results
###############################################################################
echo ""
echo "[Scenario] Phase 4 finalization"

if grep -q "Phase 4" "$COMMAND_FILE"; then
    log_pass "Phase 4 section present"
else
    log_fail "Phase 4 section missing"
fi

if grep -q "tools/cdd/status.sh" "$COMMAND_FILE"; then
    log_pass "CDD status tool referenced for finalization"
else
    log_fail "CDD status tool not referenced"
fi

###############################################################################
# Scenario: Phase 4 cleans up temporary files
###############################################################################
echo ""
echo "[Scenario] Phase 4 cleanup"

# All three temp files should be mentioned for deletion
if grep -q "sfc_state.json" "$COMMAND_FILE" && grep -q "sfc_inventory.md" "$COMMAND_FILE" && grep -q "sfc_taxonomy.md" "$COMMAND_FILE"; then
    log_pass "All three temporary files referenced for cleanup"
else
    log_fail "Not all temporary files referenced for cleanup"
fi

###############################################################################
# Scenario: Phase 4 prints recommended next steps
###############################################################################
echo ""
echo "[Scenario] Phase 4 recommended next steps"

if grep -q "/pl-spec-code-audit" "$COMMAND_FILE"; then
    log_pass "Recommended next step: /pl-spec-code-audit"
else
    log_fail "/pl-spec-code-audit not in recommended next steps"
fi

if grep -q "/pl-build" "$COMMAND_FILE"; then
    log_pass "Recommended next step: /pl-build"
else
    log_fail "/pl-build not in recommended next steps"
fi

###############################################################################
# Scenario: Cross-session resume from interrupted Phase 3
###############################################################################
echo ""
echo "[Scenario] Cross-session resume"

if grep -q "Resume" "$COMMAND_FILE" || grep -q "resume" "$COMMAND_FILE"; then
    log_pass "Resume logic described in command"
else
    log_fail "Resume logic not described"
fi

if grep -q "completed_categories" "$COMMAND_FILE"; then
    log_pass "Resume uses completed_categories from state file"
else
    log_fail "Resume does not reference completed_categories"
fi

###############################################################################
# Results
###############################################################################
echo ""
echo "==============================="
TOTAL=$((PASS + FAIL))
echo "  Results: $PASS/$TOTAL passed"
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "  Failures:"
    echo -e "$ERRORS"
fi
echo "==============================="

# Write test results
OUTDIR="$TESTS_DIR/spec_from_code"
mkdir -p "$OUTDIR"
RESULT_JSON="{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL}"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
