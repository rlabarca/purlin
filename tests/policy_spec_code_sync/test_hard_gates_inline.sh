#!/usr/bin/env bash
# Test: Hard gates must be inline in agent definition
# Verifies that the critical Engineer gates (companion file minimum,
# status tag rules, FORBIDDEN pre-scan, build protocol) are present
# INLINE in agents/purlin.md — not just referenced via a pointer to
# hard_gates.md.
#
# WHY THIS TEST EXISTS: Commit cd069af0 (2026-03-28) extracted hard gates
# from the agent definition into references/hard_gates.md. Because the
# agent definition is the system prompt (always in context) but reference
# files are only read on demand, Engineer stopped following the build
# protocol, stopped writing impl files, and just wrote code directly.
# This regression test ensures the gates are NEVER extracted again.
#
# Assigned to: policy_spec_code_sync (Gates 1-4 enforcement)
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
AGENT_DEF="$PLUGIN_ROOT/agents/purlin.md"
BUILD_SKILL="$PLUGIN_ROOT/skills/build/SKILL.md"

passed=0
failed=0
total=0

assert_contains() {
    local desc="$1" file="$2" pattern="$3"
    ((total++))
    if grep -qE "$pattern" "$file"; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (pattern not found: $pattern)"
        ((failed++))
    fi
}

assert_not_contains() {
    local desc="$1" file="$2" pattern="$3"
    ((total++))
    if grep -qE "$pattern" "$file"; then
        echo "FAIL: $desc (pattern found but should not be: $pattern)"
        ((failed++))
    else
        echo "PASS: $desc"
        ((passed++))
    fi
}

# ===================================================================
# AGENT DEFINITION: §14 Hard Gates must be inline, not a pointer
# ===================================================================

# The section header must exist
assert_contains \
    "agent def has Hard Gates section header" \
    "$AGENT_DEF" \
    "## 14.*Hard Gates"

# §14 must NOT be just a pointer to a reference file
assert_not_contains \
    "agent def §14 is NOT just a reference pointer" \
    "$AGENT_DEF" \
    "^> Per-mode mechanical checks.*See.*hard_gates\.md"

# ===================================================================
# ENGINEER GATES: Companion file minimum (the gate that broke)
# ===================================================================

assert_contains \
    "agent def has companion file minimum gate" \
    "$AGENT_DEF" \
    "Companion file minimum.*Every code commit.*MUST include.*companion file update"

assert_contains \
    "agent def says no matches-spec exemption" \
    "$AGENT_DEF" \
    "No.*matches spec.*no entry needed.*exemption"

assert_contains \
    "agent def has minimum one IMPL line" \
    "$AGENT_DEF" \
    "at minimum one.*\\[IMPL\\].*line"

# ===================================================================
# ENGINEER GATES: Status tag is a separate commit
# ===================================================================

assert_contains \
    "agent def says status tag is separate commit" \
    "$AGENT_DEF" \
    "Status tag is a separate commit.*Never combine"

# ===================================================================
# ENGINEER GATES: Pre-checks before status tag
# ===================================================================

assert_contains \
    "agent def has companion file pre-check" \
    "$AGENT_DEF" \
    "Companion file has new entries this session"

assert_contains \
    "agent def has spec alignment pre-check" \
    "$AGENT_DEF" \
    "Spec alignment.*re-read spec.*walk each requirement"

assert_contains \
    "agent def has web test pre-check" \
    "$AGENT_DEF" \
    "Web test passed with zero BUG"

assert_contains \
    "agent def has plan alignment pre-check" \
    "$AGENT_DEF" \
    "Plan alignment.*delivery plan.*verify deliverables"

# ===================================================================
# ENGINEER GATES: FORBIDDEN pre-scan
# ===================================================================

assert_contains \
    "agent def has FORBIDDEN pre-scan gate" \
    "$AGENT_DEF" \
    "FORBIDDEN pre-scan.*blocks the build"

# ===================================================================
# ENGINEER GATES: Spec existence
# ===================================================================

assert_contains \
    "agent def has spec existence gate" \
    "$AGENT_DEF" \
    "Spec existence.*Feature spec MUST exist"

# ===================================================================
# ENGINEER GATES: Re-verification fast path
# ===================================================================

assert_contains \
    "agent def has re-verification fast path" \
    "$AGENT_DEF" \
    "Re-verification fast path.*has_passing_tests.*Do NOT re-implement"

# ===================================================================
# ENGINEER GATES: Execution group dispatch
# ===================================================================

assert_contains \
    "agent def has execution group dispatch rule" \
    "$AGENT_DEF" \
    "Execution group dispatch.*2\\+ independent.*protocol violation"

# ===================================================================
# ENGINEER GATES: Verified is QA-only
# ===================================================================

assert_contains \
    "agent def says Verified is QA-only" \
    "$AGENT_DEF" \
    "Verified.*is QA-only.*Engineer MUST NOT"

# ===================================================================
# ENGINEER GATES: tests.json from runner
# ===================================================================

assert_contains \
    "agent def says tests.json must come from runner" \
    "$AGENT_DEF" \
    "tests\\.json.*must come from a test runner"

# ===================================================================
# PM GATES: Must be inline
# ===================================================================

assert_contains \
    "agent def has PM scenario heading format gate" \
    "$AGENT_DEF" \
    "Scenario heading format.*MUST use.*four hashes"

assert_contains \
    "agent def has PM required sections gate" \
    "$AGENT_DEF" \
    "Required sections.*overview.*requirements.*scenarios"

assert_contains \
    "agent def has PM no implementation notes gate" \
    "$AGENT_DEF" \
    "No Implementation Notes.*MUST NOT contain"

assert_contains \
    "agent def has PM scenarios untagged gate" \
    "$AGENT_DEF" \
    "Scenarios are untagged.*without.*@auto.*@manual.*Tags are QA-owned"

# ===================================================================
# QA GATES: Must be inline
# ===================================================================

assert_contains \
    "agent def has QA verified mandatory gate" \
    "$AGENT_DEF" \
    "Verified.*is mandatory.*QA status commits MUST include"

assert_contains \
    "agent def has QA delivery plan gating" \
    "$AGENT_DEF" \
    "Delivery plan gating.*Do NOT mark.*Complete.*PENDING phase"

assert_contains \
    "agent def has QA companion edits no reset" \
    "$AGENT_DEF" \
    "Companion file edits do NOT reset status"

assert_contains \
    "agent def has QA regression readiness gate" \
    "$AGENT_DEF" \
    "Regression readiness.*@auto.*scenarios MUST have regression JSON"

# ===================================================================
# MODE GUARD: Must use strong language (not softened)
# ===================================================================

assert_contains \
    "mode guard uses CRITICAL prefix" \
    "$AGENT_DEF" \
    "CRITICAL.*Before ANY file write"

assert_contains \
    "mode guard has response template for open mode" \
    "$AGENT_DEF" \
    "If open mode.*Do NOT write.*Respond.*activate a mode"

assert_contains \
    "mode guard narration-is-not-activation warning" \
    "$AGENT_DEF" \
    "Narration is not activation"

assert_contains \
    "mode guard says MUST execute mode switch BEFORE writing" \
    "$AGENT_DEF" \
    "MUST execute the mode switch.*BEFORE writing"

# ===================================================================
# OPEN MODE BLOCK: Must be in executive summary
# ===================================================================

assert_contains \
    "executive summary has open mode write block" \
    "$AGENT_DEF" \
    "Until a mode is activated.*open mode.*MUST NOT write"

assert_contains \
    "executive summary forbids Edit Write NotebookEdit" \
    "$AGENT_DEF" \
    "Do NOT call Edit, Write, or NotebookEdit"

# ===================================================================
# MODE DEFINITIONS: Activated-by lists must be present
# ===================================================================

assert_contains \
    "engineer mode has activated-by list" \
    "$AGENT_DEF" \
    "Activated by.*purlin:build.*purlin:unit-test"

assert_contains \
    "PM mode has activated-by list" \
    "$AGENT_DEF" \
    "Activated by.*purlin:spec.*purlin:anchor"

assert_contains \
    "QA mode has activated-by list" \
    "$AGENT_DEF" \
    "Activated by.*purlin:verify.*purlin:complete"

# ===================================================================
# REGRESSION REGISTRATION GATE: Must be in agent definition
# ===================================================================

assert_contains \
    "agent def has regression registration gate" \
    "$AGENT_DEF" \
    "Regression Registration Gate.*Cross-Mode.*MANDATORY"

assert_contains \
    "agent def says all regression work through purlin:regression" \
    "$AGENT_DEF" \
    "All regression.*work.*MUST go through.*purlin:regression"

assert_contains \
    "agent def says unregistered tests invisible" \
    "$AGENT_DEF" \
    "Unregistered tests are invisible"

# ===================================================================
# REGRESSION REGISTRATION: In regression skill
# ===================================================================

REGRESSION_SKILL="$PLUGIN_ROOT/skills/regression/SKILL.md"

assert_contains \
    "regression skill has spec registration protocol" \
    "$REGRESSION_SKILL" \
    "Spec Registration Protocol.*MANDATORY"

assert_contains \
    "regression skill says switch to PM mode" \
    "$REGRESSION_SKILL" \
    "switch to PM mode"

assert_contains \
    "regression skill says Regression Guidance section" \
    "$REGRESSION_SKILL" \
    "Regression Guidance.*section in the feature spec"

assert_contains \
    "regression skill author step has registration" \
    "$REGRESSION_SKILL" \
    "Register with spec.*MANDATORY"

assert_contains \
    "regression skill says do not commit without registration" \
    "$REGRESSION_SKILL" \
    "Do not commit regression JSON without spec registration"

# ===================================================================
# BUILD SKILL: Companion gate in Step 4
# ===================================================================

assert_contains \
    "build skill Step 4 has companion file gate" \
    "$BUILD_SKILL" \
    "Companion File Gate.*Mechanical"

assert_contains \
    "build skill Step 4 blocks without new entries" \
    "$BUILD_SKILL" \
    "BLOCK the status tag commit.*Write at least.*IMPL"

assert_contains \
    "build skill Step 4 says mechanical check" \
    "$BUILD_SKILL" \
    "mechanical check.*did the companion file get updated"

assert_contains \
    "build skill Step 4 says not a judgment call" \
    "$BUILD_SKILL" \
    "not a judgment call"

# ===================================================================
# BUILD SKILL: Step 2 has companion requirement
# ===================================================================

assert_contains \
    "build skill Step 2 says record in impl.md" \
    "$BUILD_SKILL" \
    "Knowledge Colocation.*Record.*impl\\.md"

assert_contains \
    "build skill Step 2 has IMPL tag documentation" \
    "$BUILD_SKILL" \
    "\\[IMPL\\].*INFO.*Interpreted|\\[IMPL\\].*implemented"

# Cleanup
echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
