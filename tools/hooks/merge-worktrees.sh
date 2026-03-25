#!/bin/bash
# merge-worktrees.sh — SessionEnd hook for Purlin agent
# Merges current worktree back to source branch on agent exit.
#
# Registered in .claude/settings.json as a SessionEnd hook.
# It runs on session end (including Ctrl+C).
#
# Claude Code hooks receive JSON on stdin with session context.
# Exit 0 = success, exit 2 = blocking error.

# Do NOT use set -e here. This hook must always reach exit 0 —
# intermediate failures (e.g., git add) must not prevent the merge attempt.
set -uo pipefail

# Detect project root
if [[ -n "${PURLIN_PROJECT_ROOT:-}" ]]; then
    PROJECT_ROOT="$PURLIN_PROJECT_ROOT"
else
    PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
fi

if [[ -z "$PROJECT_ROOT" ]]; then
    exit 0  # Not in a git repo, nothing to do
fi

# Check if we're in a worktree
GIT_COMMON_DIR="$(git rev-parse --git-common-dir 2>/dev/null || echo "")"
GIT_DIR="$(git rev-parse --git-dir 2>/dev/null || echo "")"

if [[ "$GIT_COMMON_DIR" == "$GIT_DIR" ]] || [[ -z "$GIT_COMMON_DIR" ]]; then
    exit 0  # Not in a worktree, nothing to do
fi

# We're in a worktree — get branch info
WORKTREE_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
if [[ -z "$WORKTREE_BRANCH" ]] || [[ "$WORKTREE_BRANCH" == "HEAD" ]]; then
    exit 0  # Detached HEAD or unknown state
fi

# Only process purlin worktree branches
if [[ ! "$WORKTREE_BRANCH" =~ ^purlin- ]]; then
    exit 0  # Not a purlin worktree branch
fi

WORKTREE_PATH="$(pwd)"

# Commit any uncommitted changes (tracked modifications, staged changes, OR untracked files)
HAS_TRACKED_CHANGES=false
HAS_UNTRACKED=false
if ! git diff --quiet HEAD 2>/dev/null || ! git diff --cached --quiet HEAD 2>/dev/null; then
    HAS_TRACKED_CHANGES=true
fi
if [[ -n "$(git ls-files --others --exclude-standard 2>/dev/null)" ]]; then
    HAS_UNTRACKED=true
fi

if [[ "$HAS_TRACKED_CHANGES" == "true" ]] || [[ "$HAS_UNTRACKED" == "true" ]]; then
    git add -A 2>/dev/null || true
    git commit -m "chore: auto-commit on session exit (worktree merge-back)

Purlin-Mode: auto" 2>/dev/null || true
fi

# Find the main working directory (parent of .git common dir)
MAIN_DIR="$(cd "$GIT_COMMON_DIR/.." && pwd)"

# Resolve source branch name (for display only — merge targets whatever is checked out)
SOURCE_BRANCH="main"
if ! git rev-parse --verify "$SOURCE_BRANCH" &>/dev/null; then
    SOURCE_BRANCH="master"
    if ! git rev-parse --verify "$SOURCE_BRANCH" &>/dev/null; then
        echo "Could not determine source branch. Worktree preserved at: $WORKTREE_PATH" >&2
        exit 0  # Non-fatal — don't block agent exit
    fi
fi

# Switch to main directory and merge
cd "$MAIN_DIR"

# Merge the worktree branch into whatever is checked out in the main repo
if git merge "$WORKTREE_BRANCH" --no-edit 2>/dev/null; then
    # Success — clean up worktree and branch
    git worktree remove "$WORKTREE_PATH" 2>/dev/null || true
    git branch -d "$WORKTREE_BRANCH" 2>/dev/null || true
    echo "Merged $WORKTREE_BRANCH into $(git rev-parse --abbrev-ref HEAD) and cleaned up worktree."
else
    # Merge conflict — abort and preserve worktree for manual resolution
    git merge --abort 2>/dev/null || true
    echo "Merge conflict merging $WORKTREE_BRANCH. Worktree preserved at: $WORKTREE_PATH" >&2
    echo "Resolve manually: cd $MAIN_DIR && git merge $WORKTREE_BRANCH" >&2
fi

exit 0
