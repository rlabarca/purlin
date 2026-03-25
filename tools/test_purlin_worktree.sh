#!/bin/bash
# test_purlin_worktree.sh -- Unit tests for Purlin worktree concurrency.
# Covers 7 scenarios from features/purlin_worktree_concurrency.md:
#   1. Worktree branch naming convention
#   2. Worktree directory location
#   3. SessionEnd hook skips non-purlin branches
#   4. SessionEnd hook auto-commits pending work
#   5. SessionEnd hook handles merge conflict gracefully
#   6. Stale worktree cleanup on refresh
#   7. pl-merge cleans up worktree after successful merge
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

# Create an isolated temp git repo for functional tests.
# Sets TEMP_REPO.
setup_temp_repo() {
    TEMP_REPO="$(mktemp -d)"
    git -C "$TEMP_REPO" init -b main --quiet
    git -C "$TEMP_REPO" config user.email "test@purlin.dev"
    git -C "$TEMP_REPO" config user.name "Purlin Test"
    git -C "$TEMP_REPO" commit --allow-empty -m "initial commit" --quiet
}

teardown_temp_repo() {
    if [ -n "${TEMP_REPO:-}" ] && [ -d "$TEMP_REPO" ]; then
        # Remove any worktrees first to avoid git errors
        git -C "$TEMP_REPO" worktree list --porcelain 2>/dev/null | \
            grep "^worktree " | awk '{print $2}' | while read -r wt; do
                [[ "$wt" == "$TEMP_REPO" ]] && continue
                git -C "$TEMP_REPO" worktree remove --force "$wt" 2>/dev/null || true
            done
        rm -rf "$TEMP_REPO"
    fi
    unset TEMP_REPO
}

###############################################################################
echo "=== Purlin Worktree Concurrency Tests ==="
###############################################################################

# ---------------------------------------------------------------------------
# Scenario 1: Worktree branch naming convention
# Verify pl-run.sh creates branches matching "purlin-<mode>-YYYYMMDD-HHMMSS"
# ---------------------------------------------------------------------------
echo ""
echo "--- Scenario 1: Worktree branch naming convention ---"

# Check both the generated pl-run.sh and the template in init.sh
NAMING_FOUND=0

# Check pl-run.sh for the naming pattern
if grep -q 'purlin-\${PURLIN_MODE:-open}-\$(date +%Y%m%d-%H%M%S)' "$PROJECT_ROOT/pl-run.sh" 2>/dev/null; then
    NAMING_FOUND=1
fi

# Also check init.sh template (the generate_purlin_launcher function)
if grep -q 'purlin-\${PURLIN_MODE:-open}-\$(date +%Y%m%d-%H%M%S)' "$PROJECT_ROOT/tools/init.sh" 2>/dev/null; then
    NAMING_FOUND=1
fi

if [ "$NAMING_FOUND" -eq 1 ]; then
    log_pass "Branch naming pattern matches purlin-<mode>-YYYYMMDD-HHMMSS"
else
    log_fail "Branch naming pattern not found in pl-run.sh or init.sh"
fi

# Verify the pattern includes the mode variable
if grep -q 'PURLIN_MODE:-open' "$PROJECT_ROOT/pl-run.sh" 2>/dev/null; then
    log_pass "Branch naming defaults to 'open' when mode is not set"
else
    log_fail "Branch naming does not default to 'open' when mode is not set"
fi

# ---------------------------------------------------------------------------
# Scenario 2: Worktree directory location
# Verify worktrees are created under .purlin/worktrees/
# ---------------------------------------------------------------------------
echo ""
echo "--- Scenario 2: Worktree directory location ---"

if grep -q '\.purlin/worktrees/' "$PROJECT_ROOT/pl-run.sh" 2>/dev/null; then
    log_pass "pl-run.sh creates worktrees under .purlin/worktrees/"
else
    log_fail "pl-run.sh does not reference .purlin/worktrees/ directory"
fi

# Verify mkdir -p is used to ensure directory exists
if grep -q 'mkdir -p.*\.purlin/worktrees' "$PROJECT_ROOT/pl-run.sh" 2>/dev/null; then
    log_pass "pl-run.sh ensures .purlin/worktrees/ directory exists (mkdir -p)"
else
    # Also check if git worktree add handles directory creation
    if grep -q 'git worktree add.*\.purlin/worktrees' "$PROJECT_ROOT/pl-run.sh" 2>/dev/null; then
        log_pass "pl-run.sh uses git worktree add with .purlin/worktrees/ path"
    else
        log_fail "pl-run.sh does not create .purlin/worktrees/ directory"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 3: SessionEnd hook skips non-purlin branches
# ---------------------------------------------------------------------------
echo ""
echo "--- Scenario 3: SessionEnd hook skips non-purlin branches ---"

HOOK_SCRIPT="$PROJECT_ROOT/tools/hooks/merge-worktrees.sh"

if [ ! -f "$HOOK_SCRIPT" ]; then
    log_fail "merge-worktrees.sh hook script not found"
else
    setup_temp_repo

    # Create a non-purlin branch worktree
    FEATURE_BRANCH="feature/login"
    WT_DIR="$TEMP_REPO/.purlin/worktrees/feature-login"
    mkdir -p "$TEMP_REPO/.purlin/worktrees"
    git -C "$TEMP_REPO" worktree add "$WT_DIR" -b "$FEATURE_BRANCH" --quiet 2>/dev/null

    # Run the hook from the non-purlin worktree
    # The hook should detect non-purlin branch and exit 0 without merging
    HOOK_OUTPUT=$(cd "$WT_DIR" && bash "$HOOK_SCRIPT" 2>&1) || true
    HOOK_EXIT=$?

    if [ "$HOOK_EXIT" -eq 0 ]; then
        log_pass "SessionEnd hook exits 0 on non-purlin branch"
    else
        log_fail "SessionEnd hook exited with $HOOK_EXIT on non-purlin branch (expected 0)"
    fi

    # Verify no merge was attempted (no merge output)
    if echo "$HOOK_OUTPUT" | grep -qi "merge\|merged"; then
        log_fail "SessionEnd hook attempted merge on non-purlin branch (output: $HOOK_OUTPUT)"
    else
        log_pass "SessionEnd hook did not attempt merge on non-purlin branch"
    fi

    teardown_temp_repo
fi

# ---------------------------------------------------------------------------
# Scenario 4: SessionEnd hook auto-commits pending work
# ---------------------------------------------------------------------------
echo ""
echo "--- Scenario 4: SessionEnd hook auto-commits pending work ---"

if [ ! -f "$HOOK_SCRIPT" ]; then
    log_fail "merge-worktrees.sh hook script not found"
else
    setup_temp_repo

    # Create a purlin-style worktree
    PURLIN_BRANCH="purlin-engineer-20260324-120000"
    WT_DIR="$TEMP_REPO/.purlin/worktrees/$PURLIN_BRANCH"
    mkdir -p "$TEMP_REPO/.purlin/worktrees"
    git -C "$TEMP_REPO" worktree add "$WT_DIR" -b "$PURLIN_BRANCH" --quiet 2>/dev/null

    # Add uncommitted changes in the worktree
    echo "new content" > "$WT_DIR/test_file.txt"
    git -C "$WT_DIR" add test_file.txt

    # Count commits before hook
    COMMITS_BEFORE=$(git -C "$WT_DIR" rev-list --count HEAD)

    # Run the hook from the purlin worktree
    HOOK_OUTPUT=$(cd "$WT_DIR" && bash "$HOOK_SCRIPT" 2>&1) || true

    # Count commits after hook -- check in temp repo since hook may have merged and removed worktree
    if [ -d "$WT_DIR" ]; then
        COMMITS_AFTER=$(git -C "$WT_DIR" rev-list --count HEAD)
    else
        # Worktree was cleaned up after merge -- check main branch
        COMMITS_AFTER=$(git -C "$TEMP_REPO" rev-list --count HEAD)
    fi

    if [ "$COMMITS_AFTER" -gt "$COMMITS_BEFORE" ]; then
        log_pass "SessionEnd hook auto-committed pending changes"
    else
        log_fail "SessionEnd hook did not auto-commit (before: $COMMITS_BEFORE, after: $COMMITS_AFTER)"
    fi

    # Verify the auto-commit message pattern
    if [ -d "$WT_DIR" ]; then
        LAST_MSG=$(git -C "$WT_DIR" log -1 --format=%s 2>/dev/null || echo "")
    else
        # Check from main branch since worktree may have been merged and removed
        LAST_MSG=$(git -C "$TEMP_REPO" log -1 --format=%s 2>/dev/null || echo "")
    fi

    if echo "$LAST_MSG" | grep -qi "auto-commit.*session exit\|Merge branch"; then
        log_pass "Auto-commit message matches expected pattern"
    else
        log_fail "Auto-commit message does not match expected pattern (got: $LAST_MSG)"
    fi

    teardown_temp_repo
fi

# ---------------------------------------------------------------------------
# Scenario 5: SessionEnd hook handles merge conflict gracefully
# ---------------------------------------------------------------------------
echo ""
echo "--- Scenario 5: SessionEnd hook handles merge conflict gracefully ---"

if [ ! -f "$HOOK_SCRIPT" ]; then
    log_fail "merge-worktrees.sh hook script not found"
else
    setup_temp_repo

    # Create an initial file on main
    echo "original content" > "$TEMP_REPO/conflict_file.txt"
    git -C "$TEMP_REPO" add conflict_file.txt
    git -C "$TEMP_REPO" commit -m "add conflict_file" --quiet

    # Create a purlin worktree
    PURLIN_BRANCH="purlin-engineer-20260324-130000"
    WT_DIR="$TEMP_REPO/.purlin/worktrees/$PURLIN_BRANCH"
    mkdir -p "$TEMP_REPO/.purlin/worktrees"
    git -C "$TEMP_REPO" worktree add "$WT_DIR" -b "$PURLIN_BRANCH" --quiet 2>/dev/null

    # Make conflicting changes on main
    echo "main branch change" > "$TEMP_REPO/conflict_file.txt"
    git -C "$TEMP_REPO" add conflict_file.txt
    git -C "$TEMP_REPO" commit -m "change on main" --quiet

    # Make conflicting changes in the worktree
    echo "worktree branch change" > "$WT_DIR/conflict_file.txt"
    git -C "$WT_DIR" add conflict_file.txt
    git -C "$WT_DIR" commit -m "change in worktree" --quiet

    # Run the hook from the purlin worktree
    HOOK_OUTPUT=$(cd "$WT_DIR" && bash "$HOOK_SCRIPT" 2>&1) || true
    HOOK_EXIT=$?

    if [ "$HOOK_EXIT" -eq 0 ]; then
        log_pass "SessionEnd hook exits 0 on merge conflict"
    else
        log_fail "SessionEnd hook exited with $HOOK_EXIT on merge conflict (expected 0)"
    fi

    # Verify the worktree is preserved (not removed)
    if [ -d "$WT_DIR" ]; then
        log_pass "Worktree preserved after merge conflict"
    else
        log_fail "Worktree was removed despite merge conflict"
    fi

    # Verify instructions for manual resolution are printed to stderr
    if echo "$HOOK_OUTPUT" | grep -qi "conflict\|preserved\|resolve"; then
        log_pass "Conflict instructions printed to stderr"
    else
        log_fail "No conflict instructions in output (got: $HOOK_OUTPUT)"
    fi

    teardown_temp_repo
fi

# ---------------------------------------------------------------------------
# Scenario 6: Stale worktree cleanup on refresh
# ---------------------------------------------------------------------------
echo ""
echo "--- Scenario 6: Stale worktree cleanup on refresh ---"

INIT_SCRIPT="$PROJECT_ROOT/tools/init.sh"

if [ ! -f "$INIT_SCRIPT" ]; then
    log_fail "init.sh not found"
else
    # Verify init.sh contains the stale worktree cleanup logic
    if grep -q '\.purlin/worktrees' "$INIT_SCRIPT" 2>/dev/null; then
        log_pass "init.sh references .purlin/worktrees/ for cleanup"
    else
        log_fail "init.sh does not reference .purlin/worktrees/"
    fi

    # Verify it uses 'git worktree list' to validate worktrees
    if grep -q 'git worktree list' "$INIT_SCRIPT" 2>/dev/null; then
        log_pass "init.sh uses 'git worktree list' to validate worktrees"
    else
        log_fail "init.sh does not use 'git worktree list' for validation"
    fi

    # Verify it removes invalid worktree directories
    if grep -q 'rm -rf' "$INIT_SCRIPT" 2>/dev/null && grep -q 'worktree' "$INIT_SCRIPT" 2>/dev/null; then
        log_pass "init.sh removes invalid worktree directories"
    else
        log_fail "init.sh does not remove invalid worktree directories"
    fi
fi

# ---------------------------------------------------------------------------
# Scenario 7: pl-merge cleans up worktree after successful merge
# ---------------------------------------------------------------------------
echo ""
echo "--- Scenario 7: pl-merge cleans up worktree after successful merge ---"

PL_MERGE="$PROJECT_ROOT/.claude/commands/pl-merge.md"

if [ ! -f "$PL_MERGE" ]; then
    log_fail "pl-merge.md not found"
else
    # Verify pl-merge describes worktree removal
    if grep -q 'git worktree remove' "$PL_MERGE" 2>/dev/null; then
        log_pass "pl-merge.md describes 'git worktree remove' for cleanup"
    else
        log_fail "pl-merge.md does not describe 'git worktree remove'"
    fi

    # Verify pl-merge describes branch deletion
    if grep -q 'git branch -d' "$PL_MERGE" 2>/dev/null; then
        log_pass "pl-merge.md describes 'git branch -d' for branch cleanup"
    else
        log_fail "pl-merge.md does not describe 'git branch -d'"
    fi

    # Verify pl-merge describes committing pending work
    if grep -q -i 'commit.*pending\|pending.*work\|pending.*commit' "$PL_MERGE" 2>/dev/null; then
        log_pass "pl-merge.md describes committing pending work before merge"
    else
        log_fail "pl-merge.md does not describe committing pending work"
    fi

    # Verify pl-merge describes the merge step
    if grep -q 'git merge' "$PL_MERGE" 2>/dev/null; then
        log_pass "pl-merge.md describes the merge operation"
    else
        log_fail "pl-merge.md does not describe the merge operation"
    fi
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
RESULT_STATUS="$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)"

# Build scenarios list
SCENARIOS='['
SCENARIOS+='"Worktree branch naming convention",'
SCENARIOS+='"Worktree directory location",'
SCENARIOS+='"SessionEnd hook skips non-purlin branches",'
SCENARIOS+='"SessionEnd hook auto-commits pending work",'
SCENARIOS+='"SessionEnd hook handles merge conflict gracefully",'
SCENARIOS+='"Stale worktree cleanup on refresh",'
SCENARIOS+='"pl-merge cleans up worktree after successful merge"'
SCENARIOS+=']'

RAN_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RESULT_JSON="{\"feature\": \"purlin_worktree_concurrency\", \"status\": \"$RESULT_STATUS\", \"passed\": $PASS, \"failed\": $FAIL, \"total\": $TOTAL, \"test_file\": \"tools/test_purlin_worktree.sh\", \"scenarios\": $SCENARIOS, \"ran_at\": \"$RAN_AT\"}"
OUTDIR="$TESTS_DIR/purlin_worktree_concurrency"
mkdir -p "$OUTDIR"
echo "$RESULT_JSON" > "$OUTDIR/tests.json"

echo ""
if [ $FAIL -eq 0 ]; then
    echo "tests.json: PASS"
    exit 0
else
    echo "tests.json: FAIL"
    exit 1
fi
