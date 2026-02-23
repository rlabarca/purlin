#!/bin/bash
# setup_worktrees.sh — Creates git worktrees for concurrent Architect/Builder/QA sessions.
# See features/agent_launchers_multiuser.md for full specification.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKTREES_DIR="$SCRIPT_DIR/.worktrees"

# Parse arguments
FEATURE_NAME="feature"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --feature)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --feature requires a name argument." >&2
                exit 1
            fi
            FEATURE_NAME="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: setup_worktrees.sh [--feature <name>]"
            echo ""
            echo "Creates three git worktrees under .worktrees/ for concurrent"
            echo "Architect, Builder, and QA sessions."
            echo ""
            echo "Options:"
            echo "  --feature <name>  Name for lifecycle branches (default: feature)"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# Verify we are in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not a git repository. Run this from the project root." >&2
    exit 1
fi

# Check that .worktrees/ is gitignored
if ! git check-ignore -q ".worktrees/" 2>/dev/null; then
    echo "Error: .worktrees/ is not gitignored." >&2
    echo "Add '.worktrees/' to your .gitignore before running this script." >&2
    exit 1
fi

# Role definitions: role-name, branch-prefix, worktree-dirname
ROLES=(
    "architect:spec:architect-session"
    "builder:impl:builder-session"
    "qa:qa:qa-session"
)

MAIN_HEAD=$(git rev-parse HEAD)
CREATED=0
SKIPPED=0

for role_def in "${ROLES[@]}"; do
    IFS=':' read -r role prefix dirname <<< "$role_def"
    branch="${prefix}/${FEATURE_NAME}"
    wt_path="$WORKTREES_DIR/$dirname"

    if [ -d "$wt_path" ]; then
        echo "  EXISTS: $wt_path (branch: $branch)"
        SKIPPED=$((SKIPPED + 1))
        continue
    fi

    # Create branch from main HEAD if it doesn't exist
    if ! git rev-parse --verify "$branch" > /dev/null 2>&1; then
        git branch "$branch" "$MAIN_HEAD"
    fi

    # Create worktree
    mkdir -p "$WORKTREES_DIR"
    git worktree add "$wt_path" "$branch" > /dev/null 2>&1
    echo "  CREATED: $wt_path (branch: $branch)"
    CREATED=$((CREATED + 1))
done

echo ""
if [ "$CREATED" -gt 0 ]; then
    echo "Setup complete: $CREATED worktree(s) created, $SKIPPED already existed."
    echo ""
    echo "Next steps:"
    echo "  1. cd .worktrees/architect-session && bash run_architect.sh"
    echo "  2. After Architect merges to main:"
    echo "     cd .worktrees/builder-session && git merge main && bash run_builder.sh"
    echo "  3. After Builder merges to main:"
    echo "     cd .worktrees/qa-session && git merge main && bash run_qa.sh"
else
    echo "All worktrees already exist. Nothing to do."
fi
