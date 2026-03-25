#!/usr/bin/env bash
# tests/qa/test_worktree_merge_on_exit.sh
# QA-owned regression: verifies that merge-worktrees.sh correctly merges
# a purlin worktree branch back to main when invoked (simulating SessionEnd).
#
# We can't trigger an actual Claude Code session exit in automation, but we
# CAN create a real worktree, make real changes, and invoke the hook script
# from within the worktree — which is exactly what SessionEnd does.
#
# Usage: bash tests/qa/test_worktree_merge_on_exit.sh
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PURLIN_ROOT="${PURLIN_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
PASS=0; FAIL=0; ERRORS=""

log_pass() { PASS=$((PASS+1)); echo "PASS: $1"; }
log_fail() { FAIL=$((FAIL+1)); ERRORS="$ERRORS\nFAIL: $1"; echo "FAIL: $1"; }

MERGE_HOOK="$PURLIN_ROOT/tools/hooks/merge-worktrees.sh"

echo "=== QA Regression: worktree merge-on-exit ==="
echo ""

# ──────────────────────────────────────────────
# MOE1: SessionEnd hook is registered in .claude/settings.json
# ──────────────────────────────────────────────
SETTINGS="$PURLIN_ROOT/.claude/settings.json"
if [ -f "$SETTINGS" ]; then
    if grep -q 'SessionEnd' "$SETTINGS" 2>/dev/null && \
       grep -q 'merge-worktrees' "$SETTINGS" 2>/dev/null; then
        log_pass "MOE1: merge-worktrees.sh is registered as a SessionEnd hook in settings.json"
    else
        log_fail "MOE1: merge-worktrees.sh is NOT registered as a SessionEnd hook in settings.json"
    fi
else
    log_fail "MOE1: .claude/settings.json not found"
fi

# ──────────────────────────────────────────────
# MOE2: Merge hook successfully merges a worktree branch back to main
# Creates a temp repo, creates a worktree, makes changes, runs the hook
# from within the worktree, and verifies the changes appear on main.
# ──────────────────────────────────────────────
TEMP_REPO=$(mktemp -d)
MOE2_RESULT=1

(
    set -e
    cd "$TEMP_REPO"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null
    echo "initial content" > app.txt
    git add app.txt
    git commit -m "initial commit" --quiet

    # Create a purlin worktree
    BRANCH="purlin-engineer-20260101-120000"
    WORKTREE_DIR="$TEMP_REPO/.purlin/worktrees/$BRANCH"
    mkdir -p "$TEMP_REPO/.purlin/worktrees"
    git worktree add "$WORKTREE_DIR" -b "$BRANCH" --quiet 2>/dev/null

    # Make and commit changes in the worktree
    cd "$WORKTREE_DIR"
    echo "worktree feature" > feature.txt
    git add feature.txt
    git commit -m "feat: add feature from worktree" --quiet

    # Run the merge hook FROM the worktree (simulating SessionEnd)
    # The hook detects it's in a worktree, finds the purlin-* branch,
    # and merges back to main.
    bash "$MERGE_HOOK" </dev/null 2>&1

    # Verify: switch to main and check if feature.txt exists
    cd "$TEMP_REPO"
    if [ -f "feature.txt" ] && grep -q "worktree feature" feature.txt; then
        echo "MERGE_VERIFIED"
    else
        echo "MERGE_FAILED: feature.txt not found on main after hook execution"
        exit 1
    fi

    # Verify: worktree branch was deleted
    if git rev-parse --verify "$BRANCH" &>/dev/null; then
        echo "BRANCH_NOT_CLEANED"
        exit 1
    fi

    echo "ALL_OK"
)
MOE2_RESULT=$?

if [ $MOE2_RESULT -eq 0 ]; then
    log_pass "MOE2: merge hook successfully merges worktree branch back to main and cleans up"
else
    log_fail "MOE2: merge hook failed to merge worktree branch back to main"
fi

rm -rf "$TEMP_REPO"

# ──────────────────────────────────────────────
# MOE3: Merge hook auto-commits uncommitted changes before merging
# ──────────────────────────────────────────────
TEMP_REPO2=$(mktemp -d)
MOE3_RESULT=1

(
    set -e
    cd "$TEMP_REPO2"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null
    echo "initial" > app.txt
    git add app.txt
    git commit -m "initial" --quiet

    BRANCH="purlin-qa-20260201-120000"
    WORKTREE_DIR="$TEMP_REPO2/.purlin/worktrees/$BRANCH"
    mkdir -p "$TEMP_REPO2/.purlin/worktrees"
    git worktree add "$WORKTREE_DIR" -b "$BRANCH" --quiet 2>/dev/null

    # Make changes but do NOT commit (leave them dirty)
    cd "$WORKTREE_DIR"
    echo "uncommitted work" > dirty.txt
    git add dirty.txt
    # Intentionally no git commit

    # Run the merge hook — it should auto-commit then merge
    bash "$MERGE_HOOK" </dev/null 2>&1

    # Verify on main
    cd "$TEMP_REPO2"
    if [ -f "dirty.txt" ] && grep -q "uncommitted work" dirty.txt; then
        echo "AUTO_COMMIT_VERIFIED"
    else
        echo "AUTO_COMMIT_FAILED"
        exit 1
    fi
)
MOE3_RESULT=$?

if [ $MOE3_RESULT -eq 0 ]; then
    log_pass "MOE3: merge hook auto-commits uncommitted changes before merging"
else
    log_fail "MOE3: merge hook failed to auto-commit uncommitted changes"
fi

rm -rf "$TEMP_REPO2"

# ──────────────────────────────────────────────
# MOE4: Merge hook is a no-op when not in a worktree
# ──────────────────────────────────────────────
TEMP_REPO3=$(mktemp -d)
MOE4_RESULT=1

(
    set -e
    cd "$TEMP_REPO3"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null
    echo "initial" > app.txt
    git add app.txt
    git commit -m "initial" --quiet

    BEFORE_SHA=$(git rev-parse HEAD)

    # Run the hook from a non-worktree directory
    bash "$MERGE_HOOK" </dev/null 2>&1

    AFTER_SHA=$(git rev-parse HEAD)

    if [ "$BEFORE_SHA" = "$AFTER_SHA" ]; then
        echo "NOOP_VERIFIED"
    else
        echo "NOOP_FAILED: hook modified state in non-worktree"
        exit 1
    fi
)
MOE4_RESULT=$?

if [ $MOE4_RESULT -eq 0 ]; then
    log_pass "MOE4: merge hook is a no-op when not in a worktree"
else
    log_fail "MOE4: merge hook unexpectedly modified state in non-worktree"
fi

rm -rf "$TEMP_REPO3"

# ──────────────────────────────────────────────
# MOE5: Merge hook skips non-purlin branches in worktrees
# ──────────────────────────────────────────────
TEMP_REPO4=$(mktemp -d)
MOE5_RESULT=1

(
    set -e
    cd "$TEMP_REPO4"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null
    echo "initial" > app.txt
    git add app.txt
    git commit -m "initial" --quiet

    # Create a worktree with a non-purlin branch name
    BRANCH="feature/login"
    WORKTREE_DIR="$TEMP_REPO4/.worktrees/$BRANCH"
    mkdir -p "$TEMP_REPO4/.worktrees"
    git worktree add "$WORKTREE_DIR" -b "$BRANCH" --quiet 2>/dev/null

    cd "$WORKTREE_DIR"
    echo "feature work" > login.txt
    git add login.txt
    git commit -m "add login" --quiet

    MAIN_SHA_BEFORE=$(cd "$TEMP_REPO4" && git rev-parse HEAD)

    # Run the hook — it should skip this non-purlin branch
    bash "$MERGE_HOOK" </dev/null 2>&1

    MAIN_SHA_AFTER=$(cd "$TEMP_REPO4" && git rev-parse HEAD)

    if [ "$MAIN_SHA_BEFORE" = "$MAIN_SHA_AFTER" ]; then
        echo "SKIP_VERIFIED"
    else
        echo "SKIP_FAILED: hook merged a non-purlin branch"
        exit 1
    fi

    # Cleanup
    cd "$TEMP_REPO4"
    git worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true
    git branch -D "$BRANCH" 2>/dev/null || true
)
MOE5_RESULT=$?

if [ $MOE5_RESULT -eq 0 ]; then
    log_pass "MOE5: merge hook correctly skips non-purlin branches"
else
    log_fail "MOE5: merge hook incorrectly processed a non-purlin branch"
fi

rm -rf "$TEMP_REPO4"

# ──────────────────────────────────────────────
# MOE6: Merge hook preserves worktree on conflict
# ──────────────────────────────────────────────
TEMP_REPO5=$(mktemp -d)
MOE6_RESULT=1

(
    set -e
    cd "$TEMP_REPO5"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null
    echo "original" > conflict.txt
    git add conflict.txt
    git commit -m "initial" --quiet

    BRANCH="purlin-pm-20260301-120000"
    WORKTREE_DIR="$TEMP_REPO5/.purlin/worktrees/$BRANCH"
    mkdir -p "$TEMP_REPO5/.purlin/worktrees"
    git worktree add "$WORKTREE_DIR" -b "$BRANCH" --quiet 2>/dev/null

    # Create conflicting changes
    cd "$WORKTREE_DIR"
    echo "worktree version" > conflict.txt
    git add conflict.txt
    git commit -m "worktree change" --quiet

    cd "$TEMP_REPO5"
    echo "main version" > conflict.txt
    git add conflict.txt
    git commit -m "main change" --quiet

    # Run the hook from the worktree — should detect conflict, abort, preserve
    cd "$WORKTREE_DIR"
    bash "$MERGE_HOOK" </dev/null 2>&1 || true

    # Verify worktree still exists
    if [ -d "$WORKTREE_DIR" ]; then
        echo "PRESERVED_OK"
    else
        echo "WORKTREE_LOST"
        exit 1
    fi

    # Verify main is clean (merge was aborted)
    cd "$TEMP_REPO5"
    if git diff --quiet HEAD 2>/dev/null; then
        echo "MAIN_CLEAN"
    else
        echo "MAIN_DIRTY"
        exit 1
    fi

    # Cleanup
    cd "$TEMP_REPO5"
    git worktree remove "$WORKTREE_DIR" --force 2>/dev/null || true
    git branch -D "$BRANCH" 2>/dev/null || true
)
MOE6_RESULT=$?

if [ $MOE6_RESULT -eq 0 ]; then
    log_pass "MOE6: merge hook preserves worktree and aborts cleanly on conflict"
else
    log_fail "MOE6: merge hook did not handle conflict correctly"
fi

rm -rf "$TEMP_REPO5"

# ──────────────────────────────────────────────
# MOE7: Merge hook auto-commits UNTRACKED files (not just staged/modified)
# ──────────────────────────────────────────────
TEMP_REPO6=$(mktemp -d)
MOE7_RESULT=1

(
    set -e
    cd "$TEMP_REPO6"
    git init --quiet
    git checkout -b main --quiet 2>/dev/null
    echo "initial" > app.txt
    git add app.txt
    git commit -m "initial" --quiet

    BRANCH="purlin-engineer-20260401-120000"
    WORKTREE_DIR="$TEMP_REPO6/.purlin/worktrees/$BRANCH"
    mkdir -p "$TEMP_REPO6/.purlin/worktrees"
    git worktree add "$WORKTREE_DIR" -b "$BRANCH" --quiet 2>/dev/null

    # Create a new file but do NOT stage or commit it (purely untracked)
    cd "$WORKTREE_DIR"
    echo "brand new file" > untracked.txt
    # Intentionally no git add or commit

    # Run the merge hook — it should detect the untracked file, add and commit it
    bash "$MERGE_HOOK" </dev/null 2>&1

    # Verify on main
    cd "$TEMP_REPO6"
    if [ -f "untracked.txt" ] && grep -q "brand new file" untracked.txt; then
        echo "UNTRACKED_COMMIT_VERIFIED"
    else
        echo "UNTRACKED_COMMIT_FAILED"
        exit 1
    fi
)
MOE7_RESULT=$?

if [ $MOE7_RESULT -eq 0 ]; then
    log_pass "MOE7: merge hook auto-commits untracked files before merging"
else
    log_fail "MOE7: merge hook failed to auto-commit untracked files"
fi

rm -rf "$TEMP_REPO6"

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
