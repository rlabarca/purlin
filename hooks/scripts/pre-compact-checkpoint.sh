#!/bin/bash
# PreCompact hook — auto-save checkpoint before context compaction.
# Writes a minimal checkpoint so the agent can recover after compaction.

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(pwd)}"
CACHE_DIR="$PROJECT_ROOT/.purlin/cache"
CHECKPOINT="$CACHE_DIR/session_checkpoint_purlin.md"

mkdir -p "$CACHE_DIR"

BRANCH=$(git -C "$PROJECT_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

cat > "$CHECKPOINT" << EOF
# Session Checkpoint (auto-saved before compaction)

**Mode:** unknown
**Timestamp:** $TIMESTAMP
**Branch:** $BRANCH

## Current Work

**Feature:** unknown
**In Progress:** Session was compacted. Run purlin:start to restore context.

### Done
- (auto-checkpoint — details lost to compaction)

### Next
1. Run purlin:start to restore session context

## Uncommitted Changes
$(git -C "$PROJECT_ROOT" status --short 2>/dev/null || echo "Unknown")

## Notes
This checkpoint was auto-saved by the PreCompact hook.
The agent should run purlin:start to fully restore context.
EOF

exit 0
