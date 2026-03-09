#!/bin/bash
# test_context_guard.sh — Automated tests for context_guard.sh (PreCompact hook)
# Covers all 12 automated scenarios from features/context_guard.md (v2 mechanical-save model).
# Produces tests/context_guard/tests.json.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
ERRORS=""

log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

SANDBOX=""
cleanup_sandbox() {
    if [[ -n "${SANDBOX:-}" && -d "$SANDBOX" ]]; then
        rm -rf "$SANDBOX"
    fi
}

setup_sandbox() {
    SANDBOX="$(mktemp -d)"
    trap cleanup_sandbox EXIT
    mkdir -p "$SANDBOX/.purlin/runtime"
    mkdir -p "$SANDBOX/.purlin/cache"
    mkdir -p "$SANDBOX/tools/hooks"
    mkdir -p "$SANDBOX/tools/config"
    cp "$SCRIPT_DIR/context_guard.sh" "$SANDBOX/tools/hooks/"
    cp "$SCRIPT_DIR/../config/resolve_config.py" "$SANDBOX/tools/config/"

    # Initialize a git repo in the sandbox for checkpoint tests
    git -C "$SANDBOX" init -q 2>/dev/null
    git -C "$SANDBOX" config user.email "test@test.com" 2>/dev/null
    git -C "$SANDBOX" config user.name "Test" 2>/dev/null
    # Gitignore framework dirs so they don't show as untracked
    printf '.purlin/\ntools/\n' > "$SANDBOX/.gitignore"
    # Initial commit so HEAD exists
    echo "init" > "$SANDBOX/init.txt"
    git -C "$SANDBOX" add init.txt .gitignore 2>/dev/null
    git -C "$SANDBOX" commit -q -m "initial commit" 2>/dev/null
}

# Run context_guard.sh with given type and optional role.
# Sets: EXIT_CODE, STDERR_OUTPUT
run_guard() {
    local compact_type="${1:-auto}"
    local agent_role="${2:-}"
    # Write temp files inside gitignored dir to avoid polluting git status
    local stderr_file="$SANDBOX/.purlin/runtime/stderr_output"
    local stdout_file="$SANDBOX/.purlin/runtime/stdout_output"

    local env_args=(PURLIN_PROJECT_ROOT="$SANDBOX")
    if [[ -n "$agent_role" ]]; then
        env_args+=(AGENT_ROLE="$agent_role")
    else
        # Unset AGENT_ROLE to test fallback behavior
        env_args+=(AGENT_ROLE="")
    fi

    echo "{\"type\":\"$compact_type\"}" | \
        env -u AGENT_ROLE "${env_args[@]}" \
        bash "$SANDBOX/tools/hooks/context_guard.sh" >"$stdout_file" 2>"$stderr_file"
    EXIT_CODE=$?
    STDERR_OUTPUT=$(cat "$stderr_file" 2>/dev/null || echo "")
}

# Find checkpoint file by role glob pattern (handles unique PID suffix).
# Sets CHECKPOINT to the first matching file, or empty string if none.
find_checkpoint() {
    local role="$1"
    CHECKPOINT=$(ls "$SANDBOX/.purlin/cache/session_checkpoint_${role}_"*.md 2>/dev/null | head -1 || echo "")
}

echo "==============================="
echo "Context Guard Tests (PreCompact)"
echo "==============================="

###############################################################################
# Scenario 1: Checkpoint saved on auto-compaction with guard enabled
###############################################################################
echo ""
echo "[Scenario] Checkpoint saved on auto-compaction with guard enabled"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"
run_guard "auto" "builder"

if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Exit code is 0"
else
    log_fail "Expected exit code 0, got $EXIT_CODE"
fi

find_checkpoint "builder"
if [[ -n "$CHECKPOINT" && -f "$CHECKPOINT" ]]; then
    log_pass "Checkpoint file exists for builder"
else
    log_fail "Checkpoint file does not exist for builder"
fi

if grep -q '^\*\*Role:\*\* builder' "$CHECKPOINT" 2>/dev/null; then
    log_pass "Checkpoint contains **Role:** builder"
else
    log_fail "Checkpoint missing **Role:** builder"
fi

if grep -q '^\*\*Source:\*\* PreCompact hook' "$CHECKPOINT" 2>/dev/null; then
    log_pass "Checkpoint contains **Source:** PreCompact hook"
else
    log_fail "Checkpoint missing **Source:** PreCompact hook"
fi
cleanup_sandbox

###############################################################################
# Scenario 2: No checkpoint saved on manual compaction
###############################################################################
echo ""
echo "[Scenario] No checkpoint saved on manual compaction"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"
run_guard "manual" "builder"

if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Exit code is 0 (manual compaction)"
else
    log_fail "Expected exit code 0, got $EXIT_CODE"
fi

# No checkpoint file should exist
if ! ls "$SANDBOX/.purlin/cache/session_checkpoint_"* 2>/dev/null | grep -q .; then
    log_pass "No checkpoint file written"
else
    log_fail "Checkpoint file was written for manual compaction"
fi
cleanup_sandbox

###############################################################################
# Scenario 3: No checkpoint saved when guard disabled
###############################################################################
echo ""
echo "[Scenario] No checkpoint saved when guard disabled"
setup_sandbox

echo '{"agents": {"architect": {"context_guard": false}}}' > "$SANDBOX/.purlin/config.json"
run_guard "auto" "architect"

if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Exit code is 0 (guard disabled)"
else
    log_fail "Expected exit code 0, got $EXIT_CODE"
fi

if ! ls "$SANDBOX/.purlin/cache/session_checkpoint_"* 2>/dev/null | grep -q .; then
    log_pass "No checkpoint file written when guard disabled"
else
    log_fail "Checkpoint file was written when guard disabled"
fi
cleanup_sandbox

###############################################################################
# Scenario 4: Guard enabled by default when no config exists
###############################################################################
echo ""
echo "[Scenario] Guard enabled by default when no config exists"
setup_sandbox

# No config file — guard should default to enabled, role to "unknown"
run_guard "auto" ""

if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Exit code is 0"
else
    log_fail "Expected exit code 0, got $EXIT_CODE"
fi

find_checkpoint "unknown"
if [[ -n "$CHECKPOINT" && -f "$CHECKPOINT" ]]; then
    log_pass "Checkpoint file written with role unknown"
else
    log_fail "Expected checkpoint file with role unknown"
fi
cleanup_sandbox

###############################################################################
# Scenario 5: Per-agent guard disabled while others remain enabled
###############################################################################
echo ""
echo "[Scenario] Per-agent guard disabled while others remain enabled"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": false}, "architect": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"

# Builder should NOT get a checkpoint (guard disabled)
run_guard "auto" "builder"
if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Builder (guard disabled): exit code 0"
else
    log_fail "Expected exit code 0 for builder, got $EXIT_CODE"
fi

if ! ls "$SANDBOX/.purlin/cache/session_checkpoint_"* 2>/dev/null | grep -q .; then
    log_pass "No checkpoint for builder (guard disabled)"
else
    log_fail "Checkpoint was written for builder (guard disabled)"
fi
cleanup_sandbox

###############################################################################
# Scenario 6: Checkpoint contains git branch
###############################################################################
echo ""
echo "[Scenario] Checkpoint contains git branch"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"

# Get the current branch name (should be main or master after git init)
EXPECTED_BRANCH=$(git -C "$SANDBOX" rev-parse --abbrev-ref HEAD 2>/dev/null)
run_guard "auto" "builder"

find_checkpoint "builder"
if grep -q "^\*\*Branch:\*\* $EXPECTED_BRANCH" "$CHECKPOINT" 2>/dev/null; then
    log_pass "Checkpoint contains **Branch:** $EXPECTED_BRANCH"
else
    log_fail "Checkpoint missing **Branch:** $EXPECTED_BRANCH, got: $(grep 'Branch' "$CHECKPOINT" 2>/dev/null)"
fi
cleanup_sandbox

###############################################################################
# Scenario 7: Checkpoint contains uncommitted changes summary
###############################################################################
echo ""
echo "[Scenario] Checkpoint contains uncommitted changes summary"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"

# Create an uncommitted change
echo "modified" > "$SANDBOX/init.txt"
run_guard "auto" "builder"

find_checkpoint "builder"
if grep -q '^\*\*Uncommitted Changes:\*\*$' "$CHECKPOINT" 2>/dev/null; then
    log_pass "Checkpoint contains **Uncommitted Changes:** header"
else
    log_fail "Checkpoint missing **Uncommitted Changes:** header"
fi

if grep -q 'init.txt' "$CHECKPOINT" 2>/dev/null; then
    log_pass "Checkpoint contains git status showing modified file"
else
    log_fail "Checkpoint missing git status output for modified file"
fi
cleanup_sandbox

###############################################################################
# Scenario 8: Checkpoint shows no uncommitted changes when tree is clean
###############################################################################
echo ""
echo "[Scenario] Checkpoint shows no uncommitted changes when tree is clean"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"

# Tree is already clean after setup
run_guard "auto" "builder"

find_checkpoint "builder"
if grep -q '^\*\*Uncommitted Changes:\*\* None$' "$CHECKPOINT" 2>/dev/null; then
    log_pass "Checkpoint contains **Uncommitted Changes:** None"
else
    log_fail "Expected **Uncommitted Changes:** None, got: $(grep 'Uncommitted' "$CHECKPOINT" 2>/dev/null)"
fi
cleanup_sandbox

###############################################################################
# Scenario 9: Staged changes are committed before checkpoint
###############################################################################
echo ""
echo "[Scenario] Staged changes are committed before checkpoint"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"

# Stage a change
echo "staged content" > "$SANDBOX/staged_file.txt"
git -C "$SANDBOX" add staged_file.txt 2>/dev/null

# Count commits before
COMMITS_BEFORE=$(git -C "$SANDBOX" rev-list --count HEAD 2>/dev/null)

run_guard "auto" "builder"

# Count commits after
COMMITS_AFTER=$(git -C "$SANDBOX" rev-list --count HEAD 2>/dev/null)

if [[ "$COMMITS_AFTER" -gt "$COMMITS_BEFORE" ]]; then
    log_pass "Git commit was created for staged changes"
else
    log_fail "Expected a new commit, before=$COMMITS_BEFORE after=$COMMITS_AFTER"
fi

# Verify commit message
LAST_MSG=$(git -C "$SANDBOX" log -1 --format=%s 2>/dev/null)
if echo "$LAST_MSG" | grep -q "context guard checkpoint"; then
    log_pass "Commit message contains 'context guard checkpoint'"
else
    log_fail "Expected commit message with 'context guard checkpoint', got: '$LAST_MSG'"
fi
cleanup_sandbox

###############################################################################
# Scenario 10: Hook succeeds even when git commit fails
###############################################################################
echo ""
echo "[Scenario] Hook succeeds even when git commit fails"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"

# Create a pre-commit hook that always fails
mkdir -p "$SANDBOX/.git/hooks"
cat > "$SANDBOX/.git/hooks/pre-commit" <<'HOOK'
#!/bin/bash
echo "pre-commit hook failure" >&2
exit 1
HOOK
chmod +x "$SANDBOX/.git/hooks/pre-commit"

# Stage a change so commit is attempted
echo "will fail" > "$SANDBOX/fail_file.txt"
git -C "$SANDBOX" add fail_file.txt 2>/dev/null

run_guard "auto" "builder"

if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Exit code is 0 despite commit failure"
else
    log_fail "Expected exit code 0, got $EXIT_CODE"
fi

find_checkpoint "builder"
if [[ -n "$CHECKPOINT" && -f "$CHECKPOINT" ]]; then
    log_pass "Checkpoint file still written after commit failure"
else
    log_fail "Checkpoint file not written after commit failure"
fi

if echo "$STDERR_OUTPUT" | grep -q "git commit failed"; then
    log_pass "stderr contains commit failure message"
else
    log_fail "Expected commit failure message in stderr, got: '$STDERR_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 11: Status line emitted to stderr
###############################################################################
echo ""
echo "[Scenario] Status line emitted to stderr"
setup_sandbox

echo '{"agents": {"qa": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"
run_guard "auto" "qa"

if echo "$STDERR_OUTPUT" | grep -q "Context Guard: checkpoint saved for qa"; then
    log_pass "stderr contains 'Context Guard: checkpoint saved for qa'"
else
    log_fail "Expected 'Context Guard: checkpoint saved for qa' in stderr, got: '$STDERR_OUTPUT'"
fi
cleanup_sandbox

###############################################################################
# Scenario 12: Hook always exits with code 0
###############################################################################
echo ""
echo "[Scenario] Hook always exits with code 0"
setup_sandbox

echo '{"agents": {"builder": {"context_guard": true}}}' > "$SANDBOX/.purlin/config.json"

# Test auto compaction
run_guard "auto" "builder"
if [[ "$EXIT_CODE" -eq 0 ]]; then
    log_pass "Auto-compaction: exit code is 0"
else
    log_fail "Auto-compaction: expected exit code 0, got $EXIT_CODE"
fi

# Verify it does NOT exit with code 2
if [[ "$EXIT_CODE" -ne 2 ]]; then
    log_pass "Hook does NOT exit with code 2"
else
    log_fail "Hook exited with code 2 (blocking behavior is removed)"
fi
cleanup_sandbox

###############################################################################
# Summary
###############################################################################
TOTAL=$((PASS + FAIL))
echo ""
echo "==============================="
echo "Results: $PASS passed, $FAIL failed (of $TOTAL)"
if [[ $FAIL -gt 0 ]]; then
    echo "  Failures:"
    echo -e "$ERRORS"
fi
echo "==============================="

# Write tests/context_guard/tests.json
OUTDIR="$TESTS_DIR/context_guard"
mkdir -p "$OUTDIR"
echo "{\"status\": \"$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/hooks/test_context_guard.sh\"}" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
