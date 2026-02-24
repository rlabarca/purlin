#!/bin/bash
# setup_worktrees.sh — Creates git worktrees for concurrent Architect/Builder/QA sessions.
# See features/agent_launchers_multiuser.md for full specification.
set -euo pipefail

# Parse arguments
FEATURE_NAME="collab"
PROJECT_ROOT=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-root)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --project-root requires a path argument." >&2
                exit 1
            fi
            PROJECT_ROOT="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: setup_worktrees.sh [--project-root <path>]"
            echo ""
            echo "Creates three git worktrees under .worktrees/ for concurrent"
            echo "Architect, Builder, and QA sessions."
            echo ""
            echo "Branches created: spec/collab, build/collab, qa/collab"
            echo ""
            echo "Options:"
            echo "  --project-root <path>  Project root directory (default: current directory)"
            echo "  -h, --help             Show this help message"
            exit 0
            ;;
        *)
            echo "Error: Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# Resolve project root
if [[ -z "$PROJECT_ROOT" ]]; then
    PROJECT_ROOT="$(pwd)"
fi
PROJECT_ROOT="$(cd "$PROJECT_ROOT" && pwd)"
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"

# Verify we are in a git repository
if ! git -C "$PROJECT_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not a git repository. Run this from the project root." >&2
    exit 1
fi

# Check that .worktrees/ is gitignored
if ! git -C "$PROJECT_ROOT" check-ignore -q ".worktrees/" 2>/dev/null; then
    echo "Error: .worktrees/ is not gitignored." >&2
    echo "Add '.worktrees/' to your .gitignore before running this script." >&2
    exit 1
fi

# Role definitions: role-name, branch-prefix, worktree-dirname
ROLES=(
    "architect:spec:architect-session"
    "builder:build:build-session"
    "qa:qa:qa-session"
)

MAIN_HEAD=$(git -C "$PROJECT_ROOT" rev-parse HEAD)
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

    # Create or reset branch to main HEAD
    if ! git -C "$PROJECT_ROOT" rev-parse --verify "$branch" > /dev/null 2>&1; then
        git -C "$PROJECT_ROOT" branch "$branch" "$MAIN_HEAD"
    else
        git -C "$PROJECT_ROOT" branch -f "$branch" "$MAIN_HEAD"
    fi

    # Create worktree
    mkdir -p "$WORKTREES_DIR"
    git -C "$PROJECT_ROOT" worktree add "$wt_path" "$branch" > /dev/null 2>&1

    # Copy live project root config into the new worktree (overwrite git-committed copy)
    LIVE_CONFIG="$PROJECT_ROOT/.purlin/config.json"
    WT_CONFIG="$wt_path/.purlin/config.json"
    if [ -f "$LIVE_CONFIG" ]; then
        mkdir -p "$wt_path/.purlin"
        cp "$LIVE_CONFIG" "$WT_CONFIG"
    fi

    # Remove .claude/commands/ from worktree to prevent duplicate /pl-* completions.
    # Claude Code climbs the directory tree and discovers the main repo's commands
    # automatically; the per-worktree copy is redundant.
    if [ -d "$wt_path/.claude/commands" ]; then
        rm -rf "$wt_path/.claude/commands"
    fi

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
    echo "     cd .worktrees/build-session && git merge main && bash run_builder.sh"
    echo "  3. After Builder merges to main:"
    echo "     cd .worktrees/qa-session && git merge main && bash run_qa.sh"
else
    echo "All worktrees already exist. Nothing to do."
fi
