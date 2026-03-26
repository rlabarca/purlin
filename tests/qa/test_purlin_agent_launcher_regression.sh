#!/usr/bin/env bash
# tests/qa/test_purlin_agent_launcher_regression.sh
# QA-owned regression harness for features/purlin_agent_launcher.md
# Tests: Deprecation warning on old launcher, instruction stack assembly
#
# Usage: bash tests/qa/test_purlin_agent_launcher_regression.sh [--write-results]
# --write-results accepted but is a no-op (harness_runner.py writes tests.json).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: purlin_agent_launcher ==="
echo ""

# --- Setup: create mock claude binary ---
MOCK_DIR=$(mktemp -d)
MOCK_ARGS_FILE="$MOCK_DIR/captured_args.txt"
MOCK_PROMPT_FILE_PATH="$MOCK_DIR/prompt_file_path.txt"

cat > "$MOCK_DIR/claude" <<'MOCKEOF'
#!/usr/bin/env bash
# Mock claude: handle update --check (exit 0 = up to date) and capture launch args
if [[ "${1:-}" == "update" ]]; then
    exit 0
fi
# Capture all args for inspection
printf '%s\n' "$@" > "${MOCK_ARGS_DIR}/captured_args.txt"
# Find and record the --append-system-prompt-file argument
NEXT_IS_PROMPT=false
for arg in "$@"; do
    if [ "$NEXT_IS_PROMPT" = "true" ]; then
        echo "$arg" > "${MOCK_ARGS_DIR}/prompt_file_path.txt"
        # Copy the prompt file content before it gets cleaned up by trap
        if [ -f "$arg" ]; then
            cp "$arg" "${MOCK_ARGS_DIR}/prompt_file_content.txt"
        fi
        break
    fi
    if [ "$arg" = "--append-system-prompt-file" ]; then
        NEXT_IS_PROMPT=true
    fi
done
exit 0
MOCKEOF
chmod +x "$MOCK_DIR/claude"

# Cleanup on exit
cleanup_mock() {
    rm -rf "$MOCK_DIR"
}
trap cleanup_mock EXIT

# Export the mock args dir so the mock script can find it
export MOCK_ARGS_DIR="$MOCK_DIR"

# Prepend mock dir to PATH so launchers find our mock claude
export PATH="$MOCK_DIR:$PATH"

# --- Pre-check: required files exist ---
echo "--- Pre-checks ---"

LEGACY_LAUNCHER="$PURLIN_ROOT/pl-run-builder.sh"
if [ -f "$LEGACY_LAUNCHER" ]; then
    log_pass "T0a: pl-run-builder.sh exists (legacy launcher present)"
    LEGACY_EXISTS=true
else
    # Legacy launchers were removed in the unified-launcher transition.
    # Absence is expected — skip Scenario A deprecation tests.
    log_pass "T0a: pl-run-builder.sh absent (legacy launchers removed — Scenario A N/A)"
    LEGACY_EXISTS=false
fi

if [ -f "$PURLIN_ROOT/pl-run.sh" ]; then
    log_pass "T0b: pl-run.sh exists"
else
    log_fail "T0b: pl-run.sh not found at $PURLIN_ROOT/pl-run.sh"
fi

# HOW_WE_WORK_BASE.md was removed in v0.8.5 (merged into PURLIN_BASE.md)
if [ -f "$PURLIN_ROOT/instructions/HOW_WE_WORK_BASE.md" ]; then
    log_fail "T0c: instructions/HOW_WE_WORK_BASE.md still exists (should be removed)"
else
    log_pass "T0c: instructions/HOW_WE_WORK_BASE.md correctly absent"
fi

if [ -f "$PURLIN_ROOT/instructions/PURLIN_BASE.md" ]; then
    log_pass "T0d: instructions/PURLIN_BASE.md exists"
else
    log_fail "T0d: instructions/PURLIN_BASE.md not found"
fi

echo ""

# ============================================================
# Scenario A: Deprecation warning on old launcher
# Spec 2.5: Old launchers MUST print a visible deprecation
# warning before launching the agent, mentioning pl-run.sh.
# ============================================================
echo "--- Scenario A: Deprecation warning on old launcher ---"

if $LEGACY_EXISTS; then
    # Run pl-run-builder.sh and capture stderr
    # The launcher will find our mock claude via PATH
    BUILDER_STDERR=$(cd "$PURLIN_ROOT" && bash "$PURLIN_ROOT/pl-run-builder.sh" 2>&1 1>/dev/null || true)
    BUILDER_ALL=$(cd "$PURLIN_ROOT" && bash "$PURLIN_ROOT/pl-run-builder.sh" 2>&1 || true)

    # T1: Check that output contains a deprecation warning
    if echo "$BUILDER_ALL" | grep -qi "deprecat"; then
        log_pass "T1: pl-run-builder.sh prints deprecation warning"
    else
        log_fail "T1: pl-run-builder.sh does not print deprecation warning (spec 2.5 requires it)"
    fi

    # T2: Check that the deprecation warning mentions pl-run.sh
    if echo "$BUILDER_ALL" | grep -q "pl-run.sh"; then
        log_pass "T2: deprecation warning mentions pl-run.sh"
    else
        log_fail "T2: deprecation warning does not mention pl-run.sh"
    fi

    # T3: Check that the agent session still starts (mock claude was invoked)
    if [ -f "$MOCK_DIR/captured_args.txt" ]; then
        log_pass "T3: agent session started after deprecation warning (claude was invoked)"
    else
        log_fail "T3: agent session did not start (claude mock was not invoked)"
    fi
else
    log_pass "T1: Scenario A skipped — legacy launchers removed (unified launcher transition)"
    log_pass "T2: Scenario A skipped — legacy launchers removed"
    log_pass "T3: Scenario A skipped — legacy launchers removed"
fi

echo ""

# ============================================================
# Scenario B: Instruction stack assembly
# Spec 2.1: Launcher assembles HOW_WE_WORK_BASE.md +
# PURLIN_BASE.md + HOW_WE_WORK_OVERRIDES.md (if exists) +
# PURLIN_OVERRIDES.md (if exists)
# ============================================================
echo "--- Scenario B: Instruction stack assembly ---"

# Reset captured args
rm -f "$MOCK_DIR/captured_args.txt" "$MOCK_DIR/prompt_file_path.txt" "$MOCK_DIR/prompt_file_content.txt"

# Run pl-run.sh with --model opus to skip interactive model selection
# The resolver may still output a model from config, but --model opus overrides
PL_RUN_OUTPUT=$(cd "$PURLIN_ROOT" && bash "$PURLIN_ROOT/pl-run.sh" --model opus 2>&1 || true)

# T4: Check that the mock claude was invoked (args captured)
if [ -f "$MOCK_DIR/captured_args.txt" ]; then
    log_pass "T4: pl-run.sh invoked claude successfully"
else
    log_fail "T4: pl-run.sh did not invoke claude (mock args not captured)"
    # Cannot continue scenario B without captured args
    echo ""
    echo "---"
    TOTAL=$((PASS + FAIL))
    echo "Results: $PASS/$TOTAL tests passed"
    if [ $FAIL -gt 0 ]; then
        printf "\nFailed tests:%s\n" "$ERRORS"
        exit 1
    fi
    exit 0
fi

# T5: Check that --append-system-prompt-file was passed
if [ -f "$MOCK_DIR/prompt_file_path.txt" ]; then
    log_pass "T5: --append-system-prompt-file argument was passed to claude"
else
    log_fail "T5: --append-system-prompt-file argument was not found in claude args"
fi

# T6: Check that prompt content file was captured
PROMPT_CONTENT_FILE="$MOCK_DIR/prompt_file_content.txt"
if [ -f "$PROMPT_CONTENT_FILE" ] && [ -s "$PROMPT_CONTENT_FILE" ]; then
    log_pass "T6: prompt file content was captured (non-empty)"
else
    log_fail "T6: prompt file content is empty or not captured"
    # Cannot continue content checks
    echo ""
    echo "---"
    TOTAL=$((PASS + FAIL))
    echo "Results: $PASS/$TOTAL tests passed"
    if [ $FAIL -gt 0 ]; then
        printf "\nFailed tests:%s\n" "$ERRORS"
        exit 1
    fi
    exit 0
fi

# T7: Prompt does NOT contain HOW_WE_WORK_BASE.md content
# Per purlin_instruction_architecture spec: launcher loads only PURLIN_BASE.md
# Distinctive string: "Continuously Design-Driven" from HOW_WE_WORK_BASE.md
if grep -q "Continuously Design-Driven" "$PROMPT_CONTENT_FILE"; then
    log_fail "T7: prompt contains HOW_WE_WORK_BASE.md content (should not be loaded)"
else
    log_pass "T7: prompt correctly excludes HOW_WE_WORK_BASE.md content"
fi

# T8: Prompt contains PURLIN_BASE.md content
# Distinctive string: "Role Definition: The Purlin Agent" from line 1
if grep -q "Role Definition: The Purlin Agent" "$PROMPT_CONTENT_FILE"; then
    log_pass "T8: prompt contains PURLIN_BASE.md content (found 'Role Definition: The Purlin Agent')"
else
    log_fail "T8: prompt missing PURLIN_BASE.md content (expected 'Role Definition: The Purlin Agent')"
fi

# T9: If PURLIN_OVERRIDES.md exists, prompt should contain its content
OVERRIDES_FILE="$PURLIN_ROOT/.purlin/PURLIN_OVERRIDES.md"
if [ -f "$OVERRIDES_FILE" ]; then
    # Get a distinctive string from the overrides file (first non-empty, non-comment line)
    OVERRIDE_MARKER=$(head -5 "$OVERRIDES_FILE" | grep -v '^$' | head -1)
    if [ -n "$OVERRIDE_MARKER" ] && grep -qF "$OVERRIDE_MARKER" "$PROMPT_CONTENT_FILE"; then
        log_pass "T9: prompt contains PURLIN_OVERRIDES.md content"
    else
        log_fail "T9: PURLIN_OVERRIDES.md exists but its content not found in prompt"
    fi
else
    # PURLIN_OVERRIDES.md does not exist -- verify it is not required
    log_pass "T9: PURLIN_OVERRIDES.md does not exist (optional, correctly skipped)"
fi

# T10: Verify PURLIN_BASE.md is the sole base instruction file
# HOW_WE_WORK_BASE.md must not appear; PURLIN_BASE.md must be present
PB_LINE=$(grep -n "Role Definition: The Purlin Agent" "$PROMPT_CONTENT_FILE" | head -1 | cut -d: -f1)
HWW_LINE=$(grep -n "Continuously Design-Driven" "$PROMPT_CONTENT_FILE" | head -1 | cut -d: -f1)
if [ -n "$PB_LINE" ] && [ -z "$HWW_LINE" ]; then
    log_pass "T10: PURLIN_BASE.md is sole base instruction (no HOW_WE_WORK_BASE.md)"
elif [ -n "$PB_LINE" ] && [ -n "$HWW_LINE" ]; then
    log_fail "T10: both PURLIN_BASE.md and HOW_WE_WORK_BASE.md found (only PURLIN_BASE expected)"
else
    log_fail "T10: PURLIN_BASE.md marker not found in prompt"
fi

# T11: Verify AGENT_ROLE is set to "purlin" (check args for model override confirmation)
# The pl-run.sh launcher sets AGENT_ROLE="purlin" -- we verify the session message
if grep -q "Begin Purlin session" "$MOCK_DIR/captured_args.txt"; then
    log_pass "T11: session message is 'Begin Purlin session' (confirms purlin role)"
else
    log_fail "T11: session message does not contain 'Begin Purlin session'"
fi

echo ""
echo "---"
TOTAL=$((PASS + FAIL))
echo "Results: $PASS/$TOTAL tests passed"
if [ $FAIL -gt 0 ]; then
    printf "\nFailed tests:%s\n" "$ERRORS"
    exit 1
fi
exit 0
