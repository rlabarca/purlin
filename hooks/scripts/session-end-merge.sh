#!/bin/bash
# SessionEnd hook — auto-commit, merge worktrees, breadcrumb on failure, clean up.
# Spec: features/purlin_worktree_concurrency.md §2.3, §2.6, §2.8

set +e  # Don't exit on error — this hook must always exit 0

# --- Clear terminal identity (badge, title, tab name) ---
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
if [ -f "$PLUGIN_ROOT/scripts/terminal/identity.sh" ]; then
    source "$PLUGIN_ROOT/scripts/terminal/identity.sh"
    clear_agent_identity
    purlin_cleanup_tty
fi

# Detect project root — works for both installed plugins and --plugin-dir.
_find_project_root() {
    if [ -n "$PURLIN_PROJECT_ROOT" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
        echo "$PURLIN_PROJECT_ROOT"; return
    fi
    local dir; dir="$(pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.purlin" ]; then echo "$dir"; return; fi
        dir="$(dirname "$dir")"
    done
    if [ -n "$CLAUDE_PLUGIN_ROOT" ] && [ -d "$CLAUDE_PLUGIN_ROOT/.purlin" ]; then
        echo "$CLAUDE_PLUGIN_ROOT"; return
    fi
    echo "$(pwd)"
}
PROJECT_ROOT="$(cd "$(_find_project_root)" && pwd -P)"
MERGE_LOCK="$PROJECT_ROOT/.purlin/cache/merge.lock"

# --- Merge lock with stale PID detection (§2.6) ---
acquire_lock() {
    local lockfile="$1"
    local max_retries=3
    local attempt=0
    mkdir -p "$(dirname "$lockfile")"

    while true; do
        # Check for stale lock before attempting acquisition
        if [ -f "$lockfile" ]; then
            local lock_pid
            lock_pid=$(cat "$lockfile" 2>/dev/null)
            if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
                # Stale lock — PID is dead, silently remove
                rm -f "$lockfile"
            fi
        fi

        if (set -o noclobber; echo $$ > "$lockfile") 2>/dev/null; then
            return 0
        fi

        attempt=$((attempt + 1))
        if [ $attempt -ge $max_retries ]; then
            echo "Warning: Could not acquire merge lock after $max_retries retries" >&2
            return 1
        fi
        sleep 2
    done
}

release_lock() {
    rm -f "$1"
}

# --- Auto-commit pending work in a worktree (§2.3) ---
auto_commit_worktree() {
    local wt_path="$1"

    # Check for any changes (tracked modifications + untracked files)
    local has_changes=false
    if [ -n "$(git -C "$wt_path" status --porcelain 2>/dev/null)" ]; then
        has_changes=true
    fi

    if [ "$has_changes" = "false" ]; then
        return 0
    fi

    # Add tracked modifications
    git -C "$wt_path" add -u 2>/dev/null || true

    # Add untracked files (respects .gitignore — won't add .purlin_worktree_label or .purlin_session.lock)
    local untracked
    untracked=$(git -C "$wt_path" ls-files --others --exclude-standard 2>/dev/null)
    if [ -n "$untracked" ]; then
        echo "$untracked" | while IFS= read -r f; do
            git -C "$wt_path" add "$f" 2>/dev/null || true
        done
    fi

    # Commit if anything was staged
    if git -C "$wt_path" diff --cached --quiet 2>/dev/null; then
        return 0  # Nothing staged
    fi

    git -C "$wt_path" commit -m "chore: auto-commit on session exit" 2>/dev/null || true
}

# --- Write merge-pending breadcrumb (§2.8) ---
write_breadcrumb() {
    local branch="$1"
    local wt_path="$2"
    local source_branch="$3"

    local breadcrumb_dir="$PROJECT_ROOT/.purlin/cache/merge_pending"
    mkdir -p "$breadcrumb_dir"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")

    cat > "$breadcrumb_dir/$branch.json" <<EOF
{
  "branch": "$branch",
  "worktree_path": "$wt_path",
  "source_branch": "$source_branch",
  "failed_at": "$timestamp",
  "reason": "conflict"
}
EOF
}

# --- Signal merge failure visually (§2.8) ---
signal_merge_failure() {
    local branch="$1"

    # Set iTerm badge to MERGE FAILED
    if type set_iterm_badge &>/dev/null; then
        set_iterm_badge "MERGE FAILED"
    fi

    # Print prominent warning to stderr
    cat >&2 <<EOF
╔══════════════════════════════════════════════════╗
║  MERGE FAILED — worktree preserved              ║
║  Branch: $branch
║  Next Purlin session will recover automatically. ║
╚══════════════════════════════════════════════════╝
EOF
}

# --- Find and merge purlin-* branches ---
merge_worktrees() {
    local branches
    branches=$(git -C "$PROJECT_ROOT" branch --list 'purlin-*' 2>/dev/null)

    if [ -z "$branches" ]; then
        return 0
    fi

    if ! acquire_lock "$MERGE_LOCK"; then
        return 0
    fi

    # Determine current branch (source for merges)
    local source_branch
    source_branch=$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "main")

    while IFS= read -r branch; do
        branch=$(echo "$branch" | sed 's/^[*+ ]*//')
        [ -z "$branch" ] && continue

        # Find the worktree path for this branch
        local wt_path
        wt_path=$(git -C "$PROJECT_ROOT" worktree list --porcelain 2>/dev/null | \
                  grep -B2 "branch refs/heads/$branch" | grep '^worktree ' | sed 's/^worktree //')

        # Auto-commit pending work before merge
        if [ -n "$wt_path" ] && [ -d "$wt_path" ]; then
            auto_commit_worktree "$wt_path"
        fi

        # Attempt merge
        if git -C "$PROJECT_ROOT" merge "$branch" --no-edit 2>/dev/null; then
            # Success — clean up worktree first (branch -d fails while worktree references it)
            if [ -n "$wt_path" ] && [ -d "$wt_path" ]; then
                rm -f "$wt_path/.purlin_session.lock"
                git -C "$PROJECT_ROOT" worktree remove "$wt_path" --force 2>/dev/null
            fi
            git -C "$PROJECT_ROOT" worktree prune 2>/dev/null
            git -C "$PROJECT_ROOT" branch -d "$branch" 2>/dev/null

            # Delete stale breadcrumb from prior failed attempt of same branch
            rm -f "$PROJECT_ROOT/.purlin/cache/merge_pending/$branch.json"
        else
            # Merge conflict — abort, preserve worktree, write breadcrumb
            git -C "$PROJECT_ROOT" merge --abort 2>/dev/null || true

            write_breadcrumb "$branch" "$wt_path" "$source_branch"
            signal_merge_failure "$branch"
        fi
    done <<< "$branches"

    release_lock "$MERGE_LOCK"
}

merge_worktrees
exit 0
