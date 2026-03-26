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

# Breadcrumb and merge lock directories
MERGE_PENDING_DIR="$MAIN_DIR/.purlin/cache/merge_pending"
MERGE_LOCK="$MAIN_DIR/.purlin/cache/merge.lock"

# Acquire merge lock (serialize with other worktrees)
_acquire_merge_lock() {
    local retries=3
    while [ "$retries" -gt 0 ]; do
        # Check for stale lock (PID dead)
        if [ -f "$MERGE_LOCK" ]; then
            local lock_pid
            lock_pid=$(python3 -c "import json; print(json.load(open('$MERGE_LOCK'))['pid'])" 2>/dev/null || echo "")
            if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
                rm -f "$MERGE_LOCK" 2>/dev/null || true
            fi
        fi
        # Try to acquire
        if [ ! -f "$MERGE_LOCK" ]; then
            mkdir -p "$(dirname "$MERGE_LOCK")" 2>/dev/null || true
            echo "{\"pid\": $$, \"started\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}" > "$MERGE_LOCK" 2>/dev/null
            return 0
        fi
        echo "Merge blocked: another worktree is merging to main. Retrying in 2s..." >&2
        sleep 2
        retries=$((retries - 1))
    done
    return 1
}

_release_merge_lock() {
    rm -f "$MERGE_LOCK" 2>/dev/null || true
}

if ! _acquire_merge_lock; then
    echo "Merge lock timeout. Worktree preserved at: $WORKTREE_PATH" >&2
    # Write breadcrumb for recovery
    mkdir -p "$MERGE_PENDING_DIR" 2>/dev/null || true
    cat > "$MERGE_PENDING_DIR/$WORKTREE_BRANCH.json" 2>/dev/null <<BREADCRUMB || true
{
  "branch": "$WORKTREE_BRANCH",
  "worktree_path": "$WORKTREE_PATH",
  "source_branch": "$SOURCE_BRANCH",
  "failed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "reason": "merge_lock_timeout"
}
BREADCRUMB
    exit 0
fi

# Merge the worktree branch into whatever is checked out in the main repo
if git merge "$WORKTREE_BRANCH" --no-edit 2>/dev/null; then
    # Success — delete session lock, clean up worktree and branch
    rm -f "$WORKTREE_PATH/.purlin_session.lock" 2>/dev/null || true
    git worktree remove "$WORKTREE_PATH" 2>/dev/null || true
    git branch -d "$WORKTREE_BRANCH" 2>/dev/null || true
    # Remove breadcrumb from any prior failed attempt of this branch
    rm -f "$MERGE_PENDING_DIR/$WORKTREE_BRANCH.json" 2>/dev/null || true
    _release_merge_lock
    echo "Merged $WORKTREE_BRANCH into $(git rev-parse --abbrev-ref HEAD) and cleaned up worktree."
else
    # Merge conflict — check if all conflicts are in safe files
    CONFLICT_FILES=$(git diff --name-only --diff-filter=U 2>/dev/null)
    SAFE_ONLY=true
    if [ -n "$CONFLICT_FILES" ]; then
        while IFS= read -r _cf; do
            case "$_cf" in
                .purlin/delivery_plan.md|.purlin/cache/*) ;;
                *) SAFE_ONLY=false; break ;;
            esac
        done <<< "$CONFLICT_FILES"
    fi

    if [ "$SAFE_ONLY" = true ] && [ -n "$CONFLICT_FILES" ]; then
        # Auto-resolve safe files by keeping main's version
        while IFS= read -r _cf; do
            git checkout --ours "$_cf" 2>/dev/null || true
            git add "$_cf" 2>/dev/null || true
        done <<< "$CONFLICT_FILES"
        if git commit --no-edit 2>/dev/null; then
            rm -f "$WORKTREE_PATH/.purlin_session.lock" 2>/dev/null || true
            git worktree remove "$WORKTREE_PATH" 2>/dev/null || true
            git branch -d "$WORKTREE_BRANCH" 2>/dev/null || true
            rm -f "$MERGE_PENDING_DIR/$WORKTREE_BRANCH.json" 2>/dev/null || true
            _release_merge_lock
            echo "Merged $WORKTREE_BRANCH (auto-resolved safe-file conflicts in .purlin/)."
            exit 0
        fi
    fi

    # Real conflicts or safe-file resolution failed — abort, preserve worktree, write breadcrumb
    git merge --abort 2>/dev/null || true
    _release_merge_lock

    # Write breadcrumb so next Purlin session can recover
    mkdir -p "$MERGE_PENDING_DIR" 2>/dev/null || true
    cat > "$MERGE_PENDING_DIR/$WORKTREE_BRANCH.json" 2>/dev/null <<BREADCRUMB || true
{
  "branch": "$WORKTREE_BRANCH",
  "worktree_path": "$WORKTREE_PATH",
  "source_branch": "$SOURCE_BRANCH",
  "failed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "reason": "conflict"
}
BREADCRUMB

    # Set iTerm badge to MERGE FAILED (persists on dead terminal tab)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    TOOLS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    if [ -f "$TOOLS_DIR/terminal/identity.sh" ]; then
        source "$TOOLS_DIR/terminal/identity.sh"
        set_iterm_badge "MERGE FAILED" 2>/dev/null || true
    fi

    # Prominent warning to stderr
    cat >&2 <<WARNING

╔══════════════════════════════════════════════════════╗
║  MERGE FAILED — worktree preserved                   ║
║  Branch: $(printf '%-40s' "$WORKTREE_BRANCH")║
║  Next Purlin session will recover automatically.     ║
╚══════════════════════════════════════════════════════╝

WARNING
fi

exit 0
