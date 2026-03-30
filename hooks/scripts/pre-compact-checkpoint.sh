#!/bin/bash
# PreCompact hook — auto-save enriched checkpoint before context compaction.
# Reads disk state to capture pipeline context so purlin:resume can reconstruct.

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

PROJECT_ROOT="$(_find_project_root)"
CACHE_DIR="$PROJECT_ROOT/.purlin/cache"
CHECKPOINT="$CACHE_DIR/session_checkpoint_purlin.md"

mkdir -p "$CACHE_DIR"

BRANCH=$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# No mode system — checkpoints track branch context only
MODE="sync"

# Read work plan summary (first 20 lines of pipeline status table)
WORK_PLAN="No work plan"
if [ -f "$PROJECT_ROOT/.purlin/work_plan.md" ]; then
    WORK_PLAN=$(head -20 "$PROJECT_ROOT/.purlin/work_plan.md" 2>/dev/null || echo "Work plan exists but unreadable")
fi

# Recent commits for context
RECENT_COMMITS=$(git -C "$PROJECT_ROOT" log --oneline -5 2>/dev/null || echo "Unknown")

# Active worktrees count
WORKTREE_COUNT=$(git -C "$PROJECT_ROOT" worktree list --porcelain 2>/dev/null | grep -c "^worktree" || echo "1")

cat > "$CHECKPOINT" << EOF
# Session Checkpoint (auto-saved before compaction)

**Mode:** $MODE
**Timestamp:** $TIMESTAMP
**Branch:** $BRANCH
**Active Worktrees:** $WORKTREE_COUNT

## Work Plan Summary

$WORK_PLAN

## Recent Commits

$RECENT_COMMITS

## Uncommitted Changes
$(git -C "$PROJECT_ROOT" status --short 2>/dev/null || echo "Unknown")

## Notes
This checkpoint was auto-saved by the PreCompact hook with enriched pipeline state.
The agent should run purlin:resume to fully restore context.
EOF

exit 0
