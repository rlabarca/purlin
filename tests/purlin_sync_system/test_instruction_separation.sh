#!/usr/bin/env bash
# Test: Instruction separation — CLAUDE.md vs agents/purlin.md
#
# CLAUDE.md is for PROJECT-SPECIFIC overrides (file classifications, tool folder docs).
# agents/purlin.md is for GLOBAL agent behavioral rules (write enforcement, skill routing).
#
# When behavioral instructions leak into CLAUDE.md, they only apply to the Purlin
# repo itself — consumer projects never see them. This test ensures the separation
# stays clean so that agent guardrails work everywhere, not just in this repo.
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
CLAUDE_MD="$PROJECT_ROOT/CLAUDE.md"
PURLIN_MD="$PROJECT_ROOT/agents/purlin.md"

passed=0
failed=0
total=0

assert_true() {
    local desc="$1"
    ((total++))
    if eval "$2"; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc"
        ((failed++))
    fi
}

assert_false() {
    local desc="$1"
    ((total++))
    if eval "$2"; then
        echo "FAIL: $desc"
        ((failed++))
    else
        echo "PASS: $desc"
        ((passed++))
    fi
}

# Helper: check if a file contains a pattern (case-insensitive)
file_contains() {
    grep -qi "$2" "$1" 2>/dev/null
}

# Helper: count occurrences
file_count() {
    grep -ci "$2" "$1" 2>/dev/null || echo "0"
}

# ============================================================
# Both files must exist
# ============================================================
echo "=== Prerequisite: Files exist ==="

assert_true "CLAUDE.md exists" "[ -f '$CLAUDE_MD' ]"
assert_true "agents/purlin.md exists" "[ -f '$PURLIN_MD' ]"

# ============================================================
# SECTION 1: CLAUDE.md must NOT contain agent behavioral directives
#
# These patterns indicate instructions telling agents how to behave,
# which belong in agents/purlin.md (applies to all consumer projects)
# ============================================================
echo ""
echo "=== Section 1: CLAUDE.md must not contain agent behavioral directives ==="

# "Agents must" / "Agents MUST" / "agents must not" — direct behavioral commands
assert_false "CLAUDE.md does not say 'agents must'" \
    "file_contains '$CLAUDE_MD' 'agents must'"

assert_false "CLAUDE.md does not say 'agents MUST NOT'" \
    "file_contains '$CLAUDE_MD' 'agents MUST NOT'"

# "Do NOT" addressed to agents (not to developers writing hooks)
# We need to be careful: "Do NOT" in the context of hook authoring rules is OK
# (telling devs how to write hooks). "Do NOT" telling agents what to do is not.
# Check for agent-directed "Do NOT" by looking for bypass-related language
assert_false "CLAUDE.md does not tell agents to not bypass write guard" \
    "grep -q 'Do NOT.*bypass' '$CLAUDE_MD'"

assert_false "CLAUDE.md does not tell agents to not use Bash to write" \
    "grep -q 'Do NOT.*Bash' '$CLAUDE_MD'"

# "Write-guard blocks are final" — this is an agent behavioral rule
assert_false "CLAUDE.md does not contain 'write-guard blocks are final'" \
    "file_contains '$CLAUDE_MD' 'write-guard blocks are final'"

# "invoke purlin:build" as a directive (not as an example in hook authoring)
# CLAUDE.md can reference purlin:build in examples of what error messages say,
# but should not be the one TELLING agents to invoke it
assert_false "CLAUDE.md does not direct agents to invoke specific skills" \
    "grep -q '^[^>]*[Aa]gents.*invoke.*purlin:' '$CLAUDE_MD'"

# "No escape hatch" — behavioral enforcement language
assert_false "CLAUDE.md does not contain 'no escape hatch'" \
    "file_contains '$CLAUDE_MD' 'no escape hatch'"

# Active skill marker protocol instructions
assert_false "CLAUDE.md does not contain active skill marker instructions" \
    "file_contains '$CLAUDE_MD' 'active.skill.marker'"

# Reclassification bypass rules
assert_false "CLAUDE.md does not contain 'reclassification is not a bypass'" \
    "file_contains '$CLAUDE_MD' 'reclassification is not a bypass'"

# ============================================================
# SECTION 2: agents/purlin.md MUST contain the key behavioral rules
#
# These are the global agent behavioral rules that apply everywhere.
# If they're missing from purlin.md, agents in consumer projects
# won't have them.
# ============================================================
echo ""
echo "=== Section 2: agents/purlin.md must contain key behavioral rules ==="

# Write enforcement section exists
assert_true "purlin.md has Write Enforcement section" \
    "file_contains '$PURLIN_MD' '#### Write Enforcement'"

# Write guard definition
assert_true "purlin.md defines write guard" \
    "file_contains '$PURLIN_MD' 'Write guard'"

# Active skill marker rule
assert_true "purlin.md has active skill marker rule" \
    "file_contains '$PURLIN_MD' 'Active skill marker'"

# Agents MUST NOT set marker directly
assert_true "purlin.md says agents must not set marker directly" \
    "file_contains '$PURLIN_MD' 'Agents MUST NOT set this directly'"

# Write-guard blocks are final (the new rule we added)
assert_true "purlin.md has write-guard blocks are final rule" \
    "file_contains '$PURLIN_MD' 'Write-guard blocks are final'"

# Anti-bypass rule mentions Bash specifically
assert_true "purlin.md anti-bypass rule mentions Bash" \
    "grep -q 'Write-guard blocks are final.*Bash\|Bash.*Write-guard blocks are final' '$PURLIN_MD' || grep -A2 'Write-guard blocks are final' '$PURLIN_MD' | grep -q 'Bash'"

# No escape hatch is in purlin.md
assert_true "purlin.md has 'no escape hatch' language" \
    "file_contains '$PURLIN_MD' 'No escape hatch'"

# ============================================================
# SECTION 3: CLAUDE.md should ONLY contain project-specific content
#
# Positive checks: CLAUDE.md should have these project-specific things
# ============================================================
echo ""
echo "=== Section 3: CLAUDE.md contains project-specific content ==="

# File Classifications section (project-specific path overrides)
assert_true "CLAUDE.md has File Classifications section" \
    "file_contains '$CLAUDE_MD' '## Purlin File Classifications'"

# Tool Folder Separation (project-specific directory docs)
assert_true "CLAUDE.md has Tool Folder Separation" \
    "file_contains '$CLAUDE_MD' '## Tool Folder Separation'"

# Hook Authoring Rules (dev guidelines for THIS repo's hooks)
assert_true "CLAUDE.md has Hook Authoring Rules" \
    "file_contains '$CLAUDE_MD' '## Hook Authoring Rules'"

# References agents/purlin.md as the protocol source
assert_true "CLAUDE.md references agents/purlin.md as protocol source" \
    "file_contains '$CLAUDE_MD' 'agents/purlin.md'"

# ============================================================
# SECTION 4: Separation boundary — specific known violations
#
# These are patterns that have leaked in the past or could easily
# leak again. Each test documents a specific incident or risk.
# ============================================================
echo ""
echo "=== Section 4: Known violation patterns ==="

# Pattern: "When a write is blocked" — this is agent behavioral guidance
assert_false "CLAUDE.md does not contain 'when a write is blocked' (agent guidance)" \
    "file_contains '$CLAUDE_MD' 'when a write is blocked'"

# Pattern: "follow the error message" — telling agents what to do
assert_false "CLAUDE.md does not contain 'follow the error message' (agent guidance)" \
    "file_contains '$CLAUDE_MD' 'follow the error message'"

# Pattern: "ask the user" as a directive to agents (not as hook error message content)
# The hook authoring rules can SAY what messages should contain, but CLAUDE.md
# should not itself be directing agent behavior
assert_false "CLAUDE.md does not direct agents to 'ask the user' for blocked writes" \
    "grep -q 'ask the user.*classif\|classif.*ask the user' '$CLAUDE_MD'"

# Pattern: Defining what agents can/cannot write — that's purlin.md territory
assert_false "CLAUDE.md does not define file bucket model" \
    "file_contains '$CLAUDE_MD' 'Three-Bucket Model'"

assert_false "CLAUDE.md does not define file buckets" \
    "file_contains '$CLAUDE_MD' 'Spec file.*Code file'"

# Pattern: Skill routing rules — which skill to invoke for which file type
assert_false "CLAUDE.md does not contain skill routing rules" \
    "grep -q 'Modified via.*purlin:' '$CLAUDE_MD'"

# ============================================================
# SECTION 5: Content proportionality — CLAUDE.md should be concise
#
# If CLAUDE.md is growing large, it's probably absorbing behavioral
# rules that belong in purlin.md. Flag if it exceeds reasonable size.
# ============================================================
echo ""
echo "=== Section 5: Content proportionality ==="

claude_lines=$(wc -l < "$CLAUDE_MD" | tr -d ' ')
purlin_lines=$(wc -l < "$PURLIN_MD" | tr -d ' ')

# CLAUDE.md should be much smaller than purlin.md (project overrides vs full protocol)
((total++))
if [ "$claude_lines" -lt 100 ]; then
    echo "PASS: CLAUDE.md is concise ($claude_lines lines < 100 threshold)"
    ((passed++))
else
    echo "FAIL: CLAUDE.md is too large ($claude_lines lines >= 100) — likely absorbing behavioral rules"
    ((failed++))
fi

# purlin.md should contain the bulk of behavioral rules
((total++))
if [ "$purlin_lines" -gt 100 ]; then
    echo "PASS: purlin.md has substantial behavioral content ($purlin_lines lines)"
    ((passed++))
else
    echo "FAIL: purlin.md seems thin ($purlin_lines lines) — behavioral rules may be elsewhere"
    ((failed++))
fi

# Ratio check: purlin.md should be at least 3x larger than CLAUDE.md
((total++))
threshold=$((claude_lines * 3))
if [ "$purlin_lines" -ge "$threshold" ]; then
    echo "PASS: purlin.md is ${purlin_lines}L vs CLAUDE.md ${claude_lines}L (ratio OK)"
    ((passed++))
else
    echo "FAIL: purlin.md ($purlin_lines) is not 3x CLAUDE.md ($claude_lines) — check separation"
    ((failed++))
fi

# ============================================================
# SECTION 6: Cross-reference integrity
#
# CLAUDE.md says "This CLAUDE.md provides project-specific overrides"
# and references agents/purlin.md. Verify these contracts hold.
# ============================================================
echo ""
echo "=== Section 6: Cross-reference integrity ==="

# CLAUDE.md declares itself as project-specific
assert_true "CLAUDE.md declares itself project-specific" \
    "file_contains '$CLAUDE_MD' 'project-specific'"

# CLAUDE.md says it does NOT replace purlin protocol
assert_true "CLAUDE.md says it does not replace purlin protocol" \
    "file_contains '$CLAUDE_MD' 'does NOT replace'"

# purlin.md has a vocabulary section (structural anchor for behavioral rules)
assert_true "purlin.md has Vocabulary section" \
    "file_contains '$PURLIN_MD' '### 2.0 Vocabulary'"

# ============================================================
# Cleanup
# ============================================================

echo ""
echo "================================="
echo "$passed/$total passed, $failed failed"
if [ "$failed" -gt 0 ]; then
    exit 1
fi
exit 0
