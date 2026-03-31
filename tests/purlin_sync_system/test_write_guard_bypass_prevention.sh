#!/usr/bin/env bash
# Test: Write guard bypass prevention — ensuring agents can't route around blocks
#
# Verifies:
#   1. All BLOCKED messages contain anti-bypass language
#   2. All BLOCKED messages are actionable (name the exact skill)
#   3. Global ~/.claude/ paths are freely writable (plan files, settings)
#   4. No BLOCKED message suggests Bash, shell redirects, or workarounds
#   5. Error messages never suggest reclassification as a bypass
#   6. Messages are specific to the file type (no generic catch-alls that confuse agents)
set -uo pipefail

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$PROJECT_ROOT}"
WRITE_GUARD="$PLUGIN_ROOT/hooks/scripts/write-guard.sh"

passed=0
failed=0
total=0

# Create isolated test environment
TEST_DIR=$(mktemp -d)
export PURLIN_PROJECT_ROOT="$TEST_DIR"
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"

mkdir -p "$TEST_DIR/.purlin/runtime"
mkdir -p "$TEST_DIR/.claude"
mkdir -p "$TEST_DIR/features/_invariants"
mkdir -p "$TEST_DIR/features/skills_engineer"
mkdir -p "$TEST_DIR/tests/qa/scenarios"
mkdir -p "$TEST_DIR/scripts/mcp"
mkdir -p "$TEST_DIR/src"

if [ -f "$PLUGIN_ROOT/references/file_classification.json" ]; then
    mkdir -p "$TEST_DIR/references"
    cp "$PLUGIN_ROOT/references/file_classification.json" "$TEST_DIR/references/"
fi

# ---- Helpers ----

run_guard_stderr() {
    local file_path="$1"
    echo "{\"tool_input\": {\"file_path\": \"$file_path\"}}" | bash "$WRITE_GUARD" 2>&1 >/dev/null
}

run_guard_stdout() {
    local file_path="$1"
    echo "{\"tool_input\": {\"file_path\": \"$file_path\"}}" | bash "$WRITE_GUARD" 2>/dev/null
}

run_guard_exit() {
    local file_path="$1"
    echo "{\"tool_input\": {\"file_path\": \"$file_path\"}}" | bash "$WRITE_GUARD" >/dev/null 2>&1
    return $?
}

assert_message_contains() {
    local desc="$1" file_path="$2" expected="$3"
    ((total++))
    local stderr
    stderr=$(run_guard_stderr "$file_path")
    if echo "$stderr" | grep -qi "$expected"; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc — expected '$expected' in message: $stderr"
        ((failed++))
    fi
}

assert_message_not_contains() {
    local desc="$1" file_path="$2" forbidden="$3"
    ((total++))
    local stderr
    stderr=$(run_guard_stderr "$file_path")
    if echo "$stderr" | grep -qi "$forbidden"; then
        echo "FAIL: $desc — found forbidden '$forbidden' in message: $stderr"
        ((failed++))
    else
        echo "PASS: $desc"
        ((passed++))
    fi
}

assert_allowed() {
    local desc="$1" file_path="$2"
    ((total++))
    if run_guard_exit "$file_path"; then
        echo "PASS: $desc"
        ((passed++))
    else
        echo "FAIL: $desc (expected allow, got block)"
        ((failed++))
    fi
}

assert_blocked() {
    local desc="$1" file_path="$2"
    ((total++))
    if run_guard_exit "$file_path"; then
        echo "FAIL: $desc (expected block, got allow)"
        ((failed++))
    else
        echo "PASS: $desc"
        ((passed++))
    fi
}

clear_marker() { rm -f "$TEST_DIR/.purlin/runtime/active_skill"; }

set_write_exceptions() {
    cat > "$TEST_DIR/.purlin/config.json" <<CONF
{ "write_exceptions": $1 }
CONF
    cp "$TEST_DIR/.purlin/config.json" "$TEST_DIR/.purlin/config.local.json" 2>/dev/null
}

# ============================================================
# SECTION 1: Every BLOCKED message must contain anti-bypass language
# The agent should NEVER think "maybe I can use Bash instead"
# ============================================================
echo "=== Section 1: Anti-bypass language in all BLOCKED messages ==="

clear_marker
ANTI_BYPASS="Do NOT use Bash"

# Invariant block
assert_message_contains "invariant block has anti-bypass warning" \
    "$TEST_DIR/features/_invariants/i_external.md" "$ANTI_BYPASS"

# Spec file block
assert_message_contains "spec block has anti-bypass warning" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "$ANTI_BYPASS"

# Code file block
assert_message_contains "code block has anti-bypass warning" \
    "$TEST_DIR/src/main.py" "$ANTI_BYPASS"

# Unknown file block (no config = UNKNOWN)
assert_message_contains "unknown block has anti-bypass warning" \
    "$TEST_DIR/unknown/file.xyz" "$ANTI_BYPASS"

# ============================================================
# SECTION 2: Every BLOCKED message names the exact corrective action
# The agent should know EXACTLY what to do — no inference needed
# ============================================================
echo ""
echo "=== Section 2: Actionable error messages (exact skill named) ==="

clear_marker

# Invariant → purlin:invariant sync
assert_message_contains "invariant block names purlin:invariant sync" \
    "$TEST_DIR/features/_invariants/i_external.md" "purlin:invariant sync"

# Spec → purlin:spec (among other spec skills)
assert_message_contains "spec block names purlin:spec" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "purlin:spec"
assert_message_contains "spec block names purlin:anchor" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "purlin:anchor"
assert_message_contains "spec block names purlin:tombstone" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "purlin:tombstone"

# Code → purlin:build
assert_message_contains "code block names purlin:build" \
    "$TEST_DIR/src/main.py" "purlin:build"

# Unknown → CLAUDE.md classification
assert_message_contains "unknown block names CLAUDE.md" \
    "$TEST_DIR/unknown/file.xyz" "CLAUDE.md"

# ============================================================
# SECTION 3: BLOCKED messages warn against reclassification
# Agents that get blocked sometimes try to reclassify the file
# via purlin:classify to bypass the write guard. Messages must
# explicitly warn against this and state it won't work.
# ============================================================
echo ""
echo "=== Section 3: Anti-reclassification warnings in BLOCKED messages ==="

clear_marker

# Code block explicitly warns against reclassification
assert_message_contains "code block warns against purlin:classify" \
    "$TEST_DIR/src/main.py" "Do NOT reclassify"
assert_message_contains "code block says classify won't work" \
    "$TEST_DIR/src/main.py" "cannot be added to write_exceptions"

# Spec block explicitly warns against reclassification
assert_message_contains "spec block warns against purlin:classify" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "Do NOT reclassify"
assert_message_contains "spec block says classify won't work" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "cannot be added to write_exceptions"

# Invariant block explicitly warns against reclassification
assert_message_contains "invariant block warns against purlin:classify" \
    "$TEST_DIR/features/_invariants/i_external.md" "Do NOT reclassify"
assert_message_contains "invariant block says classify won't work" \
    "$TEST_DIR/features/_invariants/i_external.md" "cannot be added to write_exceptions"

# No block message should suggest using a different tool
assert_message_not_contains "code block does not suggest 'try'" \
    "$TEST_DIR/src/main.py" "try using"
assert_message_not_contains "spec block does not suggest 'try'" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "try using"

# ============================================================
# SECTION 4: Global ~/.claude/ paths bypass (plan file fix)
# The bug: plan files at ~/.claude/plans/ were blocked because
# absolute paths outside PROJECT_ROOT don't match .claude/* relative
# ============================================================
echo ""
echo "=== Section 4: Global ~/.claude/ path bypass ==="

clear_marker

# Plan files at ~/.claude/plans/ — the exact bug we fixed
assert_allowed "plan file at ~/.claude/plans/ allowed" \
    "$HOME/.claude/plans/test-plan.md"

# Other global Claude system files
assert_allowed "global ~/.claude/settings.json allowed" \
    "$HOME/.claude/settings.json"

assert_allowed "global ~/.claude/projects/foo/MEMORY.md allowed" \
    "$HOME/.claude/projects/foo/MEMORY.md"

# Claude Code alternative config dir
assert_allowed "global ~/.claude-code/ path allowed" \
    "$HOME/.claude-code/config.json"

# Deeply nested plan files
assert_allowed "deeply nested plan file allowed" \
    "$HOME/.claude/plans/subdir/deep-plan.md"

# ============================================================
# SECTION 5: Global bypass does NOT extend to arbitrary HOME paths
# Agent shouldn't be able to write ~/anything by framing it as .claude/
# ============================================================
echo ""
echo "=== Section 5: Global bypass is scoped to .claude/ only ==="

clear_marker

# ~/src/ is NOT ~/.claude/ — should be blocked or at least not bypassed
# (These may fail-open due to PROJECT_ROOT mismatch, but should NOT match the .claude bypass)
((total++))
local_stdout=$(run_guard_stdout "$HOME/src/evil.py")
if echo "$local_stdout" | grep -q "global Claude system file"; then
    echo "FAIL: ~/src/evil.py incorrectly matched global .claude bypass"
    ((failed++))
else
    echo "PASS: ~/src/evil.py does not match global .claude bypass"
    ((passed++))
fi

# ~/.claude-but-not-really/ should not match
((total++))
local_stdout=$(run_guard_stdout "$HOME/.claude-but-not-really/file.md")
if echo "$local_stdout" | grep -q "global Claude system file"; then
    echo "FAIL: ~/.claude-but-not-really matched global .claude bypass"
    ((failed++))
else
    echo "PASS: ~/.claude-but-not-really does not match global .claude bypass"
    ((passed++))
fi

# ============================================================
# SECTION 6: Message specificity — no type confusion
# When an agent gets a message for the wrong file type, it improvises
# ============================================================
echo ""
echo "=== Section 6: Messages are specific to file type ==="

clear_marker

# Invariant message should say "INVARIANT" not "code file"
assert_message_contains "invariant block says INVARIANT" \
    "$TEST_DIR/features/_invariants/i_external.md" "INVARIANT"
assert_message_not_contains "invariant block does NOT say 'code file'" \
    "$TEST_DIR/features/_invariants/i_external.md" "is a code file"

# Spec message should say "spec file" not "code file"
assert_message_contains "spec block says 'spec file'" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "spec file"
assert_message_not_contains "spec block does NOT say 'code file'" \
    "$TEST_DIR/features/skills_engineer/purlin_build.md" "is a code file"

# Code message should say "code file" not "spec file"
assert_message_contains "code block says 'code file'" \
    "$TEST_DIR/src/main.py" "code file"
assert_message_not_contains "code block does NOT say 'spec file'" \
    "$TEST_DIR/src/main.py" "spec file"

# Unknown message should say "no classification rule"
assert_message_contains "unknown block says 'no classification rule'" \
    "$TEST_DIR/unknown/file.xyz" "no classification rule"
assert_message_not_contains "unknown block does NOT say 'code file'" \
    "$TEST_DIR/unknown/file.xyz" "is a code file"

# ============================================================
# SECTION 7: Error messages go to stderr (not stdout)
# Claude Code ignores stdout for exit-code-2 hooks — if stderr is
# empty, the tool call proceeds despite the non-zero exit code
# ============================================================
echo ""
echo "=== Section 7: Error messages on stderr (critical for hook enforcement) ==="

clear_marker

# For each blocked file type, verify stderr is non-empty and stdout is empty
for desc_path in \
    "invariant:$TEST_DIR/features/_invariants/i_external.md" \
    "spec:$TEST_DIR/features/skills_engineer/purlin_build.md" \
    "code:$TEST_DIR/src/main.py" \
    "unknown:$TEST_DIR/unknown/file.xyz"; do

    desc="${desc_path%%:*}"
    fpath="${desc_path#*:}"

    ((total++))
    stderr_out=$(echo "{\"tool_input\": {\"file_path\": \"$fpath\"}}" | bash "$WRITE_GUARD" 2>&1 1>/dev/null)
    if [ -n "$stderr_out" ]; then
        echo "PASS: $desc block writes to stderr"
        ((passed++))
    else
        echo "FAIL: $desc block has EMPTY stderr (hook will be silently ignored!)"
        ((failed++))
    fi

    ((total++))
    stdout_out=$(echo "{\"tool_input\": {\"file_path\": \"$fpath\"}}" | bash "$WRITE_GUARD" 2>/dev/null)
    if [ -z "$stdout_out" ]; then
        echo "PASS: $desc block has no stdout (correct)"
        ((passed++))
    else
        echo "FAIL: $desc block writes to stdout (should be stderr only): $stdout_out"
        ((failed++))
    fi
done

# ============================================================
# SECTION 8: The "shell redirects" anti-bypass covers the full phrase
# Make sure we didn't just say "Do NOT use Bash" but also mention
# the other common bypass vectors agents try
# ============================================================
echo ""
echo "=== Section 8: Anti-bypass language covers common bypass vectors ==="

clear_marker

# Each blocked type should mention "shell redirects" and "any other tool"
for desc_path in \
    "invariant:$TEST_DIR/features/_invariants/i_external.md" \
    "spec:$TEST_DIR/features/skills_engineer/purlin_build.md" \
    "code:$TEST_DIR/src/main.py" \
    "unknown:$TEST_DIR/unknown/file.xyz"; do

    desc="${desc_path%%:*}"
    fpath="${desc_path#*:}"

    assert_message_contains "$desc block mentions 'shell redirects'" \
        "$fpath" "shell redirects"
    assert_message_contains "$desc block mentions 'any other tool'" \
        "$fpath" "any other tool"
done

# ============================================================
# Cleanup
# ============================================================
rm -rf "$TEST_DIR"

echo ""
echo "================================="
echo "$passed/$total passed, $failed failed"
if [ "$failed" -gt 0 ]; then
    exit 1
fi
exit 0
