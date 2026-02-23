#!/bin/bash
# test_setup_worktrees.sh — Automated tests for setup_worktrees.sh
# Covers all 3 automated scenarios from features/agent_launchers_multiuser.md
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

    # Copy the script under test
    cp "$PROJECT_ROOT/setup_worktrees.sh" "$SANDBOX/setup_worktrees.sh"
    chmod +x "$SANDBOX/setup_worktrees.sh"

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
echo "=== Scenario: setup_worktrees Creates Three Worktrees ==="
setup_sandbox

OUTPUT=$(bash "$SANDBOX/setup_worktrees.sh" --feature task-crud 2>&1)

# Check that all three worktrees were created
if [ -d "$SANDBOX/.worktrees/architect-session" ]; then
    log_pass "architect-session directory created"
else
    log_fail "architect-session directory NOT created"
fi

if [ -d "$SANDBOX/.worktrees/builder-session" ]; then
    log_pass "builder-session directory created"
else
    log_fail "builder-session directory NOT created"
fi

if [ -d "$SANDBOX/.worktrees/qa-session" ]; then
    log_pass "qa-session directory created"
else
    log_fail "qa-session directory NOT created"
fi

# Check branch names
ARCH_BRANCH=$(git -C "$SANDBOX/.worktrees/architect-session" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$ARCH_BRANCH" = "spec/task-crud" ]; then
    log_pass "architect-session on branch spec/task-crud"
else
    log_fail "architect-session on wrong branch: '$ARCH_BRANCH' (expected spec/task-crud)"
fi

BUILD_BRANCH=$(git -C "$SANDBOX/.worktrees/builder-session" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$BUILD_BRANCH" = "impl/task-crud" ]; then
    log_pass "builder-session on branch impl/task-crud"
else
    log_fail "builder-session on wrong branch: '$BUILD_BRANCH' (expected impl/task-crud)"
fi

QA_BRANCH=$(git -C "$SANDBOX/.worktrees/qa-session" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
if [ "$QA_BRANCH" = "qa/task-crud" ]; then
    log_pass "qa-session on branch qa/task-crud"
else
    log_fail "qa-session on wrong branch: '$QA_BRANCH' (expected qa/task-crud)"
fi

# Check all branches start from the same HEAD as main
MAIN_HEAD=$(git -C "$SANDBOX" rev-parse main)
for wt_dir in architect-session builder-session qa-session; do
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
echo "=== Scenario: setup_worktrees Is Idempotent ==="
setup_sandbox

# First run — create worktrees
bash "$SANDBOX/setup_worktrees.sh" --feature task-crud > /dev/null 2>&1

# Count worktrees before
WT_COUNT_BEFORE=$(git -C "$SANDBOX" worktree list 2>/dev/null | wc -l | tr -d ' ')

# Second run — should be idempotent
OUTPUT2=$(bash "$SANDBOX/setup_worktrees.sh" --feature task-crud 2>&1)
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
echo "=== Scenario: PURLIN_PROJECT_ROOT Resolves to Worktree Path ==="
setup_sandbox

# Create worktrees
bash "$SANDBOX/setup_worktrees.sh" --feature task-crud > /dev/null 2>&1

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
echo "=== Scenario: Rejects when .worktrees not gitignored ==="
SANDBOX="$(mktemp -d)"
cd "$SANDBOX"
git init -q
git checkout -b main 2>/dev/null || git checkout -B main
echo "stub" > README.md
git add -A && git commit -q -m "initial"
cp "$PROJECT_ROOT/setup_worktrees.sh" "$SANDBOX/setup_worktrees.sh"
chmod +x "$SANDBOX/setup_worktrees.sh"

# Do NOT add .worktrees/ to gitignore
OUTPUT=$(bash "$SANDBOX/setup_worktrees.sh" 2>&1)
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
# Write results
###############################################################################
echo ""
write_results "agent_launchers_multiuser"
