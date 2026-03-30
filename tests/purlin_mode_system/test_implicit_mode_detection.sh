#!/usr/bin/env bash
# Test: Implicit mode detection rules in agent definition
# Verifies that agents/purlin.md Section 4.4 contains the correct
# proactive mode-switching instructions (not the degraded version).
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
AGENT_DEF="$PLUGIN_ROOT/agents/purlin.md"

passed=0
failed=0
total=0

assert_contains() {
    local desc="$1" pattern="$2"
    ((total++))
    if grep -qE "$pattern" "$AGENT_DEF"; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (pattern not found: $pattern)"
        ((failed++))
    fi
}

assert_not_contains() {
    local desc="$1" pattern="$2"
    ((total++))
    if grep -qE "$pattern" "$AGENT_DEF"; then
        echo "FAIL: $desc (pattern found but should not be: $pattern)"
        ((failed++))
    else
        echo "PASS: $desc"
        ((passed++))
    fi
}

# === Opening statement must be forceful ===
assert_contains "opening uses MANDATORY language" "OPEN MODE WRITE BLOCK.*MANDATORY"
assert_contains "opening says FORBIDDEN" "FORBIDDEN from calling Edit, Write"
assert_contains "opening references Section 4.4" "see Section 4\\.4"
assert_contains "opening says activate via purlin_mode" "activate it via.*purlin_mode"
assert_not_contains "opening does NOT say research only" "Default mode is for research only"
assert_not_contains "opening does NOT say DEFAULT MODE READ-ONLY" "DEFAULT MODE.*READ-ONLY"

# === Section 4.4 must say activate directly ===
assert_contains "section 4.4 says activate directly" "activate it directly.*don.t ask"
assert_contains "section 4.4 says Call purlin_mode MCP tool" "Call.*purlin_mode.*MCP tool"
assert_contains "section 4.4 maps spec requests to PM mode" "activate PM mode, begin work"
assert_contains "section 4.4 maps build requests to Engineer mode" "activate Engineer mode, begin work"
assert_contains "section 4.4 maps verify requests to QA mode" "activate QA mode, begin work"
assert_not_contains "section 4.4 does NOT say invoke skill" "invoke.*purlin:spec"
assert_not_contains "section 4.4 does NOT say invoke purlin:build" "invoke.*purlin:build"

# === Mode guard must be terse ===
assert_contains "mode guard uses Open mode label" "Open mode.*Do NOT write"
assert_not_contains "mode guard does NOT say can read and research" "You can read and research"

# === Mode activation priority includes default_mode config ===
assert_contains "activation priority includes config default_mode" "config.*default_mode.*user input"

# === Ambiguous requests still require suggestion ===
assert_contains "ambiguous requests trigger suggestion" "Ambiguous requests.*require a suggestion"

echo ""
echo "$passed passed, $failed failed out of $total"
exit 0
