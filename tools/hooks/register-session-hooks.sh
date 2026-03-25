#!/bin/bash
# register-session-hooks.sh — Register Claude Code session hooks for Purlin
#
# Called by pl-run.sh to set up SessionEnd hook for worktree merge-back.
# This creates/updates a temporary hooks config that Claude Code reads.
#
# Usage: register-session-hooks.sh [--worktree]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MERGE_SCRIPT="$SCRIPT_DIR/merge-worktrees.sh"

if [[ "${1:-}" == "--worktree" ]]; then
    # Set environment variable that Claude Code reads for hook configuration
    # The launcher should export this before invoking claude
    echo "CLAUDE_CODE_HOOKS_SessionEnd=$MERGE_SCRIPT"
fi
