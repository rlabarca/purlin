#!/bin/bash
# SessionEnd hook — merge worktrees and clean up session state.
# Adapted from tools/hooks/merge-worktrees.sh for plugin layout.

set +e  # Don't exit on error — this hook must always exit 0

# Detect project root
PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(pwd)}"
MERGE_LOCK="$PROJECT_ROOT/.purlin/cache/merge.lock"

# Acquire merge lock (serializes concurrent worktree merges)
acquire_lock() {
    local lockfile="$1"
    local max_wait=30
    local waited=0
    mkdir -p "$(dirname "$lockfile")"
    while ! (set -o noclobber; echo $$ > "$lockfile") 2>/dev/null; do
        if [ $waited -ge $max_wait ]; then
            echo "Warning: Could not acquire merge lock after ${max_wait}s" >&2
            return 1
        fi
        sleep 1
        waited=$((waited + 1))
    done
    return 0
}

release_lock() {
    rm -f "$1"
}

# Find and merge purlin-* branches
merge_worktrees() {
    local branches
    branches=$(git -C "$PROJECT_ROOT" branch --list 'purlin-*' 2>/dev/null)

    if [ -z "$branches" ]; then
        return 0
    fi

    if ! acquire_lock "$MERGE_LOCK"; then
        return 0
    fi

    while IFS= read -r branch; do
        branch=$(echo "$branch" | sed 's/^[* ]*//')
        [ -z "$branch" ] && continue

        # Attempt merge
        if git -C "$PROJECT_ROOT" merge "$branch" --no-edit 2>/dev/null; then
            # Clean up branch
            git -C "$PROJECT_ROOT" branch -d "$branch" 2>/dev/null

            # Clean up worktree if it exists
            local wt_path
            wt_path=$(git -C "$PROJECT_ROOT" worktree list --porcelain 2>/dev/null | \
                      grep -B1 "branch refs/heads/$branch" | head -1 | sed 's/worktree //')
            if [ -n "$wt_path" ] && [ -d "$wt_path" ]; then
                # Remove session lock
                rm -f "$wt_path/.purlin_session.lock"
                git -C "$PROJECT_ROOT" worktree remove "$wt_path" 2>/dev/null
            fi
        fi
    done <<< "$branches"

    release_lock "$MERGE_LOCK"
}

merge_worktrees
exit 0
