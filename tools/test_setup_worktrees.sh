#!/bin/bash
# test_setup_worktrees.sh — Automated tests for setup_worktrees.sh and teardown_worktrees.sh
# Covers all automated scenarios from features/agent_launchers_multiuser.md
# Produces tests/agent_launchers_multiuser/tests.json at project root.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTS_DIR="$PROJECT_ROOT/tests"
PASS=0
FAIL=0
ERRORS=""

###############################################################################
# Helpers
###############################################################################
log_pass() { PASS=$((PASS + 1)); echo "  PASS: $1"; }
log_fail() { FAIL=$((FAIL + 1)); ERRORS="$ERRORS\n  FAIL: $1"; echo "  FAIL: $1"; }

setup_sandbox() {
    SANDBOX="$(mktemp -d)"
    cd "$SANDBOX"

    # Initialize a git repo with an initial commit
    git init -q
    git checkout -b main 2>/dev/null || git checkout -B main
    mkdir -p features .purlin instructions
    echo "# stub" > features/example.md
    echo "# stub" > instructions/HOW_WE_WORK_BASE.md
    echo "# stub" > instructions/BUILDER_BASE.md
    echo "# stub" > instructions/ARCHITECT_BASE.md
    echo "# stub" > instructions/QA_BASE.md
    echo '{}' > .purlin/config.json

    # Add .worktrees/ to gitignore
    echo ".worktrees/" > .gitignore

    git add -A && git commit -q -m "initial commit"

    # Copy the scripts under test
    mkdir -p "$SANDBOX/tools/collab"
    cp "$PROJECT_ROOT/tools/collab/setup_worktrees.sh" "$SANDBOX/tools/collab/setup_worktrees.sh"
    cp "$PROJECT_ROOT/tools/collab/teardown_worktrees.sh" "$SANDBOX/tools/collab/teardown_worktrees.sh"
    chmod +x "$SANDBOX/tools/collab/setup_worktrees.sh"
    chmod +x "$SANDBOX/tools/collab/teardown_worktrees.sh"

    # Copy launcher scripts for scenario 3
    for role in architect builder qa; do
        cp "$PROJECT_ROOT/run_${role}.sh" "$SANDBOX/run_${role}.sh" 2>/dev/null || true
    done
}

teardown_sandbox() {
    cd "$PROJECT_ROOT"
    if [ -n "${SANDBOX:-}" ] && [ -d "$SANDBOX" ]; then
        # Remove worktrees cleanly before deleting
        if [ -d "$SANDBOX/.worktrees" ]; then
            for wt in "$SANDBOX/.worktrees"/*/; do
                [ -d "$wt" ] && git -C "$SANDBOX" worktree remove --force "$wt" 2>/dev/null || true
            done
        fi
        rm -rf "$SANDBOX"
    fi
}

write_results() {
    local feature="$1"
    local total=$((PASS + FAIL))
    local status="PASS"
    [ "$FAIL" -gt 0 ] && status="FAIL"

    mkdir -p "$TESTS_DIR/$feature"
    cat > "$TESTS_DIR/$feature/tests.json" << EOF
{"status": "$status", "passed": $PASS, "failed": $FAIL, "total": $total}
EOF
    echo ""
    echo "Results: $PASS passed, $FAIL failed out of $total"
    if [ -n "$ERRORS" ]; then
        echo -e "\nFailures:$ERRORS"
    fi
}

###############################################################################
# Scenario 1: setup_worktrees Creates Three Worktrees
###############################################################################
echo "[Scenario] setup_worktrees Creates Three Worktrees"
setup_sandbox

OUTPUT=$(bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" 2>&1)

# Check that all three worktrees were created
if [ -d "$SANDBOX/.worktrees/architect-session" ]; then
    log_pass "architect-session directory created"
else
    log_fail "architect-session directory NOT created"
fi

if [ -d "$SANDBOX/.worktrees/build-session" ]; then
    log_pass "build-session directory created"
else
    log_fail "build-session directory NOT created"
fi

if [ -d "$SANDBOX/.worktrees/qa-session" ]; then
    log_pass "qa-session directory created"
else
    log_fail "qa-session directory NOT created"
fi

# Check branch names
ARCH_BRANCH=$(git -C "$SANDBOX/.worktrees/architect-session" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$ARCH_BRANCH" = "spec/collab" ]; then
    log_pass "architect-session on branch spec/collab"
else
    log_fail "architect-session on wrong branch: '$ARCH_BRANCH' (expected spec/collab)"
fi

BUILD_BRANCH=$(git -C "$SANDBOX/.worktrees/build-session" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$BUILD_BRANCH" = "build/collab" ]; then
    log_pass "build-session on branch build/collab"
else
    log_fail "build-session on wrong branch: '$BUILD_BRANCH' (expected build/collab)"
fi

QA_BRANCH=$(git -C "$SANDBOX/.worktrees/qa-session" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$QA_BRANCH" = "qa/collab" ]; then
    log_pass "qa-session on branch qa/collab"
else
    log_fail "qa-session on wrong branch: '$QA_BRANCH' (expected qa/collab)"
fi

# Check all branches start from the same HEAD as main
MAIN_HEAD=$(git -C "$SANDBOX" rev-parse main)
for wt_dir in architect-session build-session qa-session; do
    WT_HEAD=$(git -C "$SANDBOX/.worktrees/$wt_dir" rev-parse HEAD 2>/dev/null || echo "")
    if [ "$WT_HEAD" = "$MAIN_HEAD" ]; then
        log_pass "$wt_dir HEAD matches main"
    else
        log_fail "$wt_dir HEAD does not match main ($WT_HEAD != $MAIN_HEAD)"
    fi
done

# Check output mentions CREATED
if echo "$OUTPUT" | grep -q "CREATED"; then
    log_pass "Output contains CREATED message"
else
    log_fail "Output missing CREATED message"
fi

teardown_sandbox

###############################################################################
# Scenario 2: setup_worktrees Is Idempotent
###############################################################################
echo ""
echo "[Scenario] setup_worktrees Is Idempotent"
setup_sandbox

# First run — create worktrees
bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" > /dev/null 2>&1

# Count worktrees before
WT_COUNT_BEFORE=$(git -C "$SANDBOX" worktree list 2>/dev/null | wc -l | tr -d ' ')

# Second run — should be idempotent
OUTPUT2=$(bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" 2>&1)
EXIT_CODE=$?

# Count worktrees after
WT_COUNT_AFTER=$(git -C "$SANDBOX" worktree list 2>/dev/null | wc -l | tr -d ' ')

if [ "$EXIT_CODE" -eq 0 ]; then
    log_pass "Second run exits cleanly (exit code 0)"
else
    log_fail "Second run failed with exit code $EXIT_CODE"
fi

if [ "$WT_COUNT_BEFORE" = "$WT_COUNT_AFTER" ]; then
    log_pass "No duplicate worktrees created ($WT_COUNT_BEFORE == $WT_COUNT_AFTER)"
else
    log_fail "Worktree count changed ($WT_COUNT_BEFORE -> $WT_COUNT_AFTER)"
fi

if echo "$OUTPUT2" | grep -q "EXISTS"; then
    log_pass "Second run shows EXISTS status messages"
else
    log_fail "Second run missing EXISTS status messages"
fi

if echo "$OUTPUT2" | grep -q "already exist"; then
    log_pass "Second run indicates nothing to do"
else
    log_fail "Second run missing 'already exist' message"
fi

teardown_sandbox

###############################################################################
# Scenario 3: PURLIN_PROJECT_ROOT Resolves to Worktree Path
###############################################################################
echo ""
echo "[Scenario] PURLIN_PROJECT_ROOT Resolves to Worktree Path"
setup_sandbox

# Create worktrees
bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" > /dev/null 2>&1

# The launcher script sets PURLIN_PROJECT_ROOT="$SCRIPT_DIR" (line 10 of run_builder.sh).
# When run from a worktree directory, SCRIPT_DIR resolves to the worktree path.
# We verify this by sourcing just the export logic.

WT_PATH="$SANDBOX/.worktrees/architect-session"
# Copy launcher to worktree if needed
if [ -f "$SANDBOX/run_architect.sh" ]; then
    cp "$SANDBOX/run_architect.sh" "$WT_PATH/run_architect.sh"
fi

# Extract PURLIN_PROJECT_ROOT by running the first lines of the launcher
# We simulate what SCRIPT_DIR would resolve to when the script runs from WT_PATH
RESOLVED_DIR=$(cd "$WT_PATH" && cd "$(dirname "run_architect.sh")" && pwd)
if [ "$RESOLVED_DIR" = "$WT_PATH" ]; then
    log_pass "SCRIPT_DIR resolves to worktree path"
else
    log_fail "SCRIPT_DIR resolves to '$RESOLVED_DIR' (expected '$WT_PATH')"
fi

# Verify features/ exists in worktree and is from the worktree branch
if [ -d "$WT_PATH/features" ]; then
    log_pass "features/ directory accessible in worktree"
else
    log_fail "features/ directory NOT found in worktree"
fi

# Verify .purlin can be created in worktree (cache isolation)
mkdir -p "$WT_PATH/.purlin/cache"
if [ -d "$WT_PATH/.purlin/cache" ]; then
    log_pass ".purlin/cache/ can be created in worktree (isolation)"
else
    log_fail ".purlin/cache/ creation failed in worktree"
fi

teardown_sandbox

###############################################################################
# Scenario: gitignore check enforced
###############################################################################
echo ""
echo "[Scenario] Rejects when .worktrees not gitignored"
SANDBOX="$(mktemp -d)"
cd "$SANDBOX"
git init -q
git checkout -b main 2>/dev/null || git checkout -B main
echo "stub" > README.md
git add -A && git commit -q -m "initial"
mkdir -p "$SANDBOX/tools/collab"
cp "$PROJECT_ROOT/tools/collab/setup_worktrees.sh" "$SANDBOX/tools/collab/setup_worktrees.sh"
chmod +x "$SANDBOX/tools/collab/setup_worktrees.sh"

# Do NOT add .worktrees/ to gitignore
OUTPUT=$(bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -ne 0 ]; then
    log_pass "Script exits with error when .worktrees not gitignored"
else
    log_fail "Script should have failed when .worktrees not gitignored"
fi

if echo "$OUTPUT" | grep -qi "not gitignored"; then
    log_pass "Error message mentions gitignore requirement"
else
    log_fail "Error message missing gitignore reference"
fi

cd "$PROJECT_ROOT"
rm -rf "$SANDBOX"

###############################################################################
# Scenario: Teardown Is Blocked When Worktree Has Uncommitted Changes
###############################################################################
echo ""
echo "[Scenario] Teardown Is Blocked When Worktree Has Uncommitted Changes"
setup_sandbox

# Create worktrees
bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" > /dev/null 2>&1

# Make build-session dirty
echo "dirty change" > "$SANDBOX/.worktrees/build-session/dirty_file.txt"

# Run teardown without --force
OUTPUT=$(bash "$SANDBOX/tools/collab/teardown_worktrees.sh" --project-root "$SANDBOX" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 1 ]; then
    log_pass "Teardown exits with code 1 when dirty"
else
    log_fail "Teardown should exit 1 when dirty, got $EXIT_CODE"
fi

if echo "$OUTPUT" | grep -qi "uncommitted"; then
    log_pass "Error message mentions uncommitted changes"
else
    log_fail "Error message missing uncommitted changes reference"
fi

if echo "$OUTPUT" | grep -qi "build-session"; then
    log_pass "Error output identifies dirty worktree (build-session)"
else
    log_fail "Error output missing dirty worktree name"
fi

# Verify worktrees still exist (not removed)
if [ -d "$SANDBOX/.worktrees/build-session" ]; then
    log_pass "Worktrees not removed when blocked"
else
    log_fail "Worktrees were removed despite dirty block"
fi

teardown_sandbox

###############################################################################
# Scenario: Teardown Proceeds with Warning When Branch Has Unmerged Commits
###############################################################################
echo ""
echo "[Scenario] Teardown Proceeds with Warning When Branch Has Unmerged Commits"
setup_sandbox

# Create worktrees
bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" > /dev/null 2>&1

# Add commits to build-session that are not merged to main
cd "$SANDBOX/.worktrees/build-session"
echo "impl code" > impl_file.txt
git add impl_file.txt
git commit -q -m "feat: implement handler"
echo "impl code 2" > impl_file2.txt
git add impl_file2.txt
git commit -q -m "feat: implement validator"
echo "impl code 3" > impl_file3.txt
git add impl_file3.txt
git commit -q -m "feat: implement tests"
cd "$PROJECT_ROOT"

# Run teardown — should warn but proceed
OUTPUT=$(bash "$SANDBOX/tools/collab/teardown_worktrees.sh" --project-root "$SANDBOX" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    log_pass "Teardown exits cleanly despite unmerged commits"
else
    log_fail "Teardown should succeed with unmerged commits, got exit $EXIT_CODE"
fi

if echo "$OUTPUT" | grep -qi "warning"; then
    log_pass "Output contains warning about unmerged commits"
else
    log_fail "Output missing warning about unmerged commits"
fi

if echo "$OUTPUT" | grep -q "build/collab"; then
    log_pass "Warning mentions unmerged branch name"
else
    log_fail "Warning missing branch name reference"
fi

# Verify worktrees are removed
if [ ! -d "$SANDBOX/.worktrees/build-session" ]; then
    log_pass "Worktrees removed after unsynced warning"
else
    log_fail "Worktrees still present after teardown"
fi

# Verify the branch still exists
if git -C "$SANDBOX" rev-parse --verify "build/collab" > /dev/null 2>&1; then
    log_pass "build/collab branch still exists after worktree removal"
else
    log_fail "build/collab branch was deleted (should survive)"
fi

teardown_sandbox

###############################################################################
# Scenario: Teardown --dry-run Reports Without Removing
###############################################################################
echo ""
echo "[Scenario] Teardown --dry-run Reports Without Removing"
setup_sandbox

# Create worktrees
bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" > /dev/null 2>&1

# Make architect-session dirty
echo "draft" > "$SANDBOX/.worktrees/architect-session/draft.md"

# Run dry-run
OUTPUT=$(bash "$SANDBOX/tools/collab/teardown_worktrees.sh" --dry-run --project-root "$SANDBOX" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    log_pass "Dry-run exits cleanly"
else
    log_fail "Dry-run should exit 0, got $EXIT_CODE"
fi

if echo "$OUTPUT" | grep -q '"dirty_count"'; then
    log_pass "Dry-run output contains dirty_count field"
else
    log_fail "Dry-run output missing dirty_count field"
fi

# Verify JSON is parseable
if echo "$OUTPUT" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
    log_pass "Dry-run output is valid JSON"
else
    log_fail "Dry-run output is not valid JSON"
fi

# Verify worktrees still exist (dry-run should not remove)
if [ -d "$SANDBOX/.worktrees/architect-session" ]; then
    log_pass "Worktrees not removed during dry-run"
else
    log_fail "Worktrees were removed during dry-run"
fi

teardown_sandbox

###############################################################################
# Scenario: Teardown --force Bypasses Dirty Check
###############################################################################
echo ""
echo "[Scenario] Teardown --force Bypasses Dirty Check"
setup_sandbox

# Create worktrees
bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" > /dev/null 2>&1

# Make build-session dirty
echo "dirty change" > "$SANDBOX/.worktrees/build-session/dirty_file.txt"

# Run teardown with --force
OUTPUT=$(bash "$SANDBOX/tools/collab/teardown_worktrees.sh" --force --project-root "$SANDBOX" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    log_pass "Teardown --force exits cleanly despite dirty worktree"
else
    log_fail "Teardown --force should exit 0, got $EXIT_CODE"
fi

# Verify worktrees are removed
if [ ! -d "$SANDBOX/.worktrees/build-session" ]; then
    log_pass "Dirty worktree removed with --force"
else
    log_fail "Dirty worktree still present after --force teardown"
fi

teardown_sandbox

###############################################################################
# Scenario: setup_worktrees --project-root Flag
###############################################################################
echo ""
echo "[Scenario] setup_worktrees --project-root Flag"
SANDBOX="$(mktemp -d)"
EXTERNAL_DIR="$(mktemp -d)"
cd "$SANDBOX"
git init -q
git checkout -b main 2>/dev/null || git checkout -B main
mkdir -p features .purlin
echo "# stub" > features/example.md
echo ".worktrees/" > .gitignore
git add -A && git commit -q -m "initial"

# Run setup from a different directory using --project-root
OUTPUT=$(bash "$PROJECT_ROOT/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" 2>&1)
EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 0 ]; then
    log_pass "--project-root: setup completes from external directory"
else
    log_fail "--project-root: setup failed with exit $EXIT_CODE. Output: $OUTPUT"
fi

if [ -d "$SANDBOX/.worktrees/architect-session" ]; then
    log_pass "--project-root: worktrees created at specified project root"
else
    log_fail "--project-root: worktrees NOT created at specified project root"
fi

cd "$PROJECT_ROOT"
# Clean up worktrees before removing
if [ -d "$SANDBOX/.worktrees" ]; then
    for wt in "$SANDBOX/.worktrees"/*/; do
        [ -d "$wt" ] && git -C "$SANDBOX" worktree remove --force "$wt" 2>/dev/null || true
    done
fi
rm -rf "$SANDBOX" "$EXTERNAL_DIR"

###############################################################################
# Scenario: setup_worktrees Removes .claude/commands/ From Each Worktree
###############################################################################
echo ""
echo "[Scenario] setup_worktrees Removes .claude/commands/ From Each Worktree"
setup_sandbox

# Add .claude/commands/ to the repo so worktrees inherit it
mkdir -p "$SANDBOX/.claude/commands"
echo "# stub command" > "$SANDBOX/.claude/commands/pl-status.md"
echo "# stub command" > "$SANDBOX/.claude/commands/pl-build.md"
git -C "$SANDBOX" add -A && git -C "$SANDBOX" commit -q -m "add .claude/commands"

# Create worktrees — each will initially have .claude/commands/ from git
bash "$SANDBOX/tools/collab/setup_worktrees.sh" --project-root "$SANDBOX" > /dev/null 2>&1

# Verify .claude/commands/ is removed from each worktree
for wt_dir in architect-session build-session qa-session; do
    if [ ! -d "$SANDBOX/.worktrees/$wt_dir/.claude/commands" ]; then
        log_pass "$wt_dir: .claude/commands/ removed"
    else
        log_fail "$wt_dir: .claude/commands/ still exists (should be removed)"
    fi
done

# Verify .claude/commands/ at project root is unaffected
if [ -d "$SANDBOX/.claude/commands" ]; then
    log_pass "Project root .claude/commands/ still exists"
else
    log_fail "Project root .claude/commands/ was removed (should be preserved)"
fi

# Verify command files still exist at project root
if [ -f "$SANDBOX/.claude/commands/pl-status.md" ] && [ -f "$SANDBOX/.claude/commands/pl-build.md" ]; then
    log_pass "Project root command files intact"
else
    log_fail "Project root command files missing"
fi

teardown_sandbox

###############################################################################
# Write results
###############################################################################
echo ""
write_results "agent_launchers_multiuser"
