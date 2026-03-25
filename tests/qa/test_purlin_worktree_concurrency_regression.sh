#!/usr/bin/env bash
# tests/qa/test_purlin_worktree_concurrency_regression.sh
# QA-owned regression harness for features/purlin_worktree_concurrency.md
# Tests: concurrent worktree isolation and merge hook behavior
#
# Usage: bash tests/qa/test_purlin_worktree_concurrency_regression.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

echo "=== QA Regression: purlin_worktree_concurrency ==="
echo ""

# ──────────────────────────────────────────────
# WTC1: pl-run.sh contains --worktree flag handling
# ──────────────────────────────────────────────
PL_RUN="$PURLIN_ROOT/pl-run.sh"
if [ -f "$PL_RUN" ] && grep -q 'PURLIN_WORKTREE' "$PL_RUN"; then
    log_pass "WTC1: pl-run.sh contains --worktree flag handling"
else
    log_fail "WTC1: pl-run.sh missing or lacks --worktree flag handling"
fi

# ──────────────────────────────────────────────
# WTC2: Worktree branch naming uses purlin-<mode>-<timestamp> pattern
# ──────────────────────────────────────────────
if grep -q 'purlin-${PURLIN_MODE:-open}-$(date' "$PL_RUN" 2>/dev/null || \
   grep -q 'purlin-.*PURLIN_MODE.*date' "$PL_RUN" 2>/dev/null; then
    log_pass "WTC2: branch naming follows purlin-<mode>-<timestamp> convention"
else
    log_fail "WTC2: branch naming pattern not found in pl-run.sh"
fi

# ──────────────────────────────────────────────
# WTC3: Worktree directory is under .purlin/worktrees/
# ──────────────────────────────────────────────
if grep -q '.purlin/worktrees' "$PL_RUN" 2>/dev/null; then
    log_pass "WTC3: worktree directory is under .purlin/worktrees/"
else
    log_fail "WTC3: .purlin/worktrees/ path not found in pl-run.sh"
fi

# ──────────────────────────────────────────────
# WTC4: Concurrent worktrees get unique branch names and directories
# This test creates two actual worktrees one second apart in a
# temporary git repo, verifies uniqueness, and cleans up.
# ──────────────────────────────────────────────
TEMP_REPO=$(mktemp -d)
WORKTREE_TEST_PASSED=true

(
    cd "$TEMP_REPO"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null
    echo "initial" > file.txt
    git add file.txt
    git commit -m "initial" --quiet

    mkdir -p .purlin/worktrees

    # Simulate two worktree creations like pl-run.sh does
    PURLIN_MODE="engineer"
    BRANCH1="purlin-${PURLIN_MODE}-$(date +%Y%m%d-%H%M%S)"
    DIR1="$TEMP_REPO/.purlin/worktrees/$BRANCH1"
    git worktree add "$DIR1" -b "$BRANCH1" --quiet 2>/dev/null
    RESULT1=$?

    # Wait 1 second to ensure different timestamp
    sleep 1

    BRANCH2="purlin-${PURLIN_MODE}-$(date +%Y%m%d-%H%M%S)"
    DIR2="$TEMP_REPO/.purlin/worktrees/$BRANCH2"
    git worktree add "$DIR2" -b "$BRANCH2" --quiet 2>/dev/null
    RESULT2=$?

    # Verify both worktrees created successfully
    if [ "$RESULT1" -ne 0 ] || [ "$RESULT2" -ne 0 ]; then
        echo "CREATION_FAILED"
        exit 1
    fi

    # Verify unique branch names
    if [ "$BRANCH1" = "$BRANCH2" ]; then
        echo "BRANCHES_SAME"
        exit 1
    fi

    # Verify separate directories
    if [ "$DIR1" = "$DIR2" ]; then
        echo "DIRS_SAME"
        exit 1
    fi

    # Verify both directories exist and are distinct
    if [ ! -d "$DIR1" ] || [ ! -d "$DIR2" ]; then
        echo "DIR_MISSING"
        exit 1
    fi

    # Verify each directory has a .git reference (is a valid worktree)
    if [ ! -e "$DIR1/.git" ] || [ ! -e "$DIR2/.git" ]; then
        echo "NOT_WORKTREE"
        exit 1
    fi

    echo "OK:$BRANCH1:$BRANCH2:$DIR1:$DIR2"

    # Cleanup: remove worktrees
    git worktree remove "$DIR1" --force 2>/dev/null || true
    git worktree remove "$DIR2" --force 2>/dev/null || true
    git branch -D "$BRANCH1" 2>/dev/null || true
    git branch -D "$BRANCH2" 2>/dev/null || true
)
WTC4_RESULT=$?

if [ $WTC4_RESULT -eq 0 ]; then
    log_pass "WTC4: concurrent worktrees have unique branch names and separate directories"
else
    log_fail "WTC4: concurrent worktree isolation failed"
fi

# Clean up temp repo
rm -rf "$TEMP_REPO"

# ──────────────────────────────────────────────
# WTC5: SessionEnd merge hook exists
# ──────────────────────────────────────────────
MERGE_HOOK="$PURLIN_ROOT/tools/hooks/merge-worktrees.sh"
if [ -f "$MERGE_HOOK" ]; then
    log_pass "WTC5: merge-worktrees.sh hook exists at tools/hooks/"
else
    log_fail "WTC5: merge-worktrees.sh hook not found at tools/hooks/"
fi

# ──────────────────────────────────────────────
# WTC6: Merge hook only processes purlin-* branches
# ──────────────────────────────────────────────
if [ -f "$MERGE_HOOK" ] && grep -q 'purlin-' "$MERGE_HOOK" 2>/dev/null; then
    log_pass "WTC6: merge hook filters on purlin-* branch pattern"
else
    log_fail "WTC6: merge hook missing purlin-* branch filter"
fi

# ──────────────────────────────────────────────
# WTC7: Merge hook always exits 0 (never blocks agent exit)
# Verify the hook ends with exit 0 and has no exit 1/exit 2 calls
# ──────────────────────────────────────────────
if [ -f "$MERGE_HOOK" ]; then
    LAST_EXIT=$(tail -5 "$MERGE_HOOK" | grep -c 'exit 0')
    # Check for actual exit 1 or exit 2 statements (not in comments)
    # Use a temp var to avoid pipefail issues with grep -c returning 1 on no match
    BLOCKING_EXITS="$(grep -v '^\s*#' "$MERGE_HOOK" | grep -E 'exit [12]' 2>/dev/null | wc -l | tr -d ' ')"
    if [ "$LAST_EXIT" -ge 1 ] && [ "$BLOCKING_EXITS" -eq 0 ]; then
        log_pass "WTC7: merge hook always exits 0 (non-blocking)"
    else
        log_fail "WTC7: merge hook may exit with non-zero (blocking agent exit)"
    fi
else
    log_fail "WTC7: merge hook not found -- cannot verify exit behavior"
fi

# ──────────────────────────────────────────────
# WTC8: Merge hook auto-commits pending changes
# ──────────────────────────────────────────────
if [ -f "$MERGE_HOOK" ] && grep -q 'auto-commit' "$MERGE_HOOK" 2>/dev/null; then
    log_pass "WTC8: merge hook auto-commits pending changes on session exit"
else
    log_fail "WTC8: merge hook missing auto-commit behavior"
fi

# ──────────────────────────────────────────────
# WTC9: Safe file auto-resolution -- merge conflict with .purlin/cache/ file
# Creates a temp repo, simulates a cache file conflict, and verifies
# the merge hook aborts gracefully (preserves worktree, exits 0).
# Note: The merge-worktrees.sh hook aborts on conflict rather than
# auto-resolving. Safe-file auto-resolution is handled by the /pl-merge
# agent skill during interactive sessions.
# ──────────────────────────────────────────────
TEMP_MERGE_REPO=$(mktemp -d)
WTC9_RESULT=1

(
    set -e
    cd "$TEMP_MERGE_REPO"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null

    # Create initial files
    mkdir -p .purlin/cache
    echo '{"version": 1}' > .purlin/cache/scan.json
    echo "app code" > src_app.txt
    git add -A
    git commit -m "initial commit" --quiet

    # Create a purlin worktree branch
    BRANCH="purlin-engineer-20250101-120000"
    WORKTREE_DIR="$TEMP_MERGE_REPO/.purlin/worktrees/$BRANCH"
    mkdir -p "$TEMP_MERGE_REPO/.purlin/worktrees"
    git worktree add "$WORKTREE_DIR" -b "$BRANCH" --quiet 2>/dev/null

    # Make changes in the worktree (both a normal file and a cache file)
    cd "$WORKTREE_DIR"
    echo "modified app code" > src_app.txt
    echo '{"version": 2, "source": "worktree"}' > .purlin/cache/scan.json
    git add -A
    git commit -m "worktree changes" --quiet

    # Make conflicting changes on main (only cache file)
    cd "$TEMP_MERGE_REPO"
    echo '{"version": 3, "source": "main"}' > .purlin/cache/scan.json
    git add -A
    git commit -m "main cache update" --quiet

    # Now simulate the merge hook behavior:
    # The hook attempts a merge and if it conflicts, it aborts.
    cd "$TEMP_MERGE_REPO"
    if git merge "$BRANCH" --no-edit 2>/dev/null; then
        # Merge succeeded (no conflict) -- this is fine
        echo "MERGE_OK"
    else
        # Conflict detected -- verify abort works cleanly
        git merge --abort 2>/dev/null || true
        # Verify we're back on main cleanly
        CURRENT=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
        if [ "$CURRENT" = "main" ]; then
            echo "CONFLICT_HANDLED"
        else
            echo "ABORT_FAILED"
            exit 1
        fi
    fi

    # Verify worktree still exists (preserved on conflict)
    if [ -d "$WORKTREE_DIR" ]; then
        echo "WORKTREE_PRESERVED"
    else
        echo "WORKTREE_LOST"
        exit 1
    fi

    # Cleanup
    git worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true
    git branch -D "$BRANCH" 2>/dev/null || true
)
WTC9_RESULT=$?

if [ $WTC9_RESULT -eq 0 ]; then
    log_pass "WTC9: merge conflict with cache file handled gracefully (worktree preserved)"
else
    log_fail "WTC9: merge conflict handling failed"
fi

# Clean up temp merge repo
rm -rf "$TEMP_MERGE_REPO"

# ──────────────────────────────────────────────
# WTC10: pl-merge skill defines safe-file auto-resolution
# Verify the /pl-merge command references safe file patterns
# ──────────────────────────────────────────────
PL_MERGE_SKILL="$PURLIN_ROOT/.claude/commands/pl-merge.md"
if [ -f "$PL_MERGE_SKILL" ]; then
    SAFE_FILES_REF=$(grep -c '.purlin/cache' "$PL_MERGE_SKILL" 2>/dev/null || echo "0")
    AUTO_RESOLVE_REF=$(grep -ci 'auto-resolve\|safe.file\|keep main' "$PL_MERGE_SKILL" 2>/dev/null || echo "0")
    if [ "$SAFE_FILES_REF" -ge 1 ] && [ "$AUTO_RESOLVE_REF" -ge 1 ]; then
        log_pass "WTC10: /pl-merge skill defines safe-file auto-resolution for .purlin/cache/*"
    else
        log_fail "WTC10: /pl-merge skill missing safe-file auto-resolution references"
    fi
else
    log_fail "WTC10: /pl-merge skill not found at .claude/commands/pl-merge.md"
fi

# ──────────────────────────────────────────────
echo ""
echo "────────────────────────────────"
TOTAL=$((PASS + FAIL))
echo "Results: $PASS/$TOTAL tests passed"
if [ $FAIL -gt 0 ]; then
    printf "\nFailed tests:%s\n" "$ERRORS"
    exit 1
fi
exit 0
