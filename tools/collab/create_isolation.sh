#!/usr/bin/env bash
# create_isolation.sh — Create a named git worktree isolation.
# Usage: create_isolation.sh <name> [--project-root <path>]

set -euo pipefail

# --- Argument parsing ---
NAME=""
PROJECT_ROOT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-root)
            PROJECT_ROOT="$2"
            shift 2
            ;;
        -*)
            echo "Error: Unknown flag '$1'" >&2
            exit 1
            ;;
        *)
            if [[ -z "$NAME" ]]; then
                NAME="$1"
            else
                echo "Error: Unexpected argument '$1'" >&2
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$NAME" ]]; then
    echo "Error: Name is required." >&2
    echo "Usage: create_isolation.sh <name> [--project-root <path>]" >&2
    exit 1
fi

# Default project root to CWD
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

# --- Name validation (Section 2.1) ---
# Must be 1-8 characters, alphanumeric + hyphen + underscore only
if [[ ${#NAME} -gt 8 ]]; then
    echo "Error: Name '$NAME' is too long (${#NAME} chars). Maximum is 8 characters." >&2
    exit 1
fi

if [[ ${#NAME} -lt 1 ]]; then
    echo "Error: Name must be at least 1 character." >&2
    exit 1
fi

if ! [[ "$NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "Error: Name '$NAME' contains invalid characters. Only alphanumeric, hyphen, and underscore are allowed." >&2
    exit 1
fi

# --- Check .worktrees/ is gitignored ---
WORKTREES_DIR="$PROJECT_ROOT/.worktrees"

if ! git -C "$PROJECT_ROOT" check-ignore -q ".worktrees/" 2>/dev/null; then
    echo "Error: .worktrees/ is not gitignored. Add '.worktrees/' to .gitignore before creating isolations." >&2
    exit 1
fi

# --- Idempotency check ---
WORKTREE_PATH="$WORKTREES_DIR/$NAME"

if [[ -d "$WORKTREE_PATH" ]]; then
    BRANCH=$(git -C "$WORKTREE_PATH" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    echo "Isolation '$NAME' already exists at $WORKTREE_PATH (branch: $BRANCH)."
    exit 0
fi

# --- Create worktree ---
BRANCH_NAME="isolated/$NAME"

# Ensure .worktrees/ directory exists
mkdir -p "$WORKTREES_DIR"

# Create the branch and worktree from current HEAD of main
git -C "$PROJECT_ROOT" worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" main

# --- Command file setup (Section 2.2 step 6) ---
WORKTREE_CMD_DIR="$WORKTREE_PATH/.claude/commands"
ROOT_CMD_DIR="$PROJECT_ROOT/.claude/commands"

# Ensure the worktree's .claude/commands/ exists
mkdir -p "$WORKTREE_CMD_DIR"

# Copy pl-local-push.md and pl-local-pull.md from project root
for cmd_file in pl-local-push.md pl-local-pull.md; do
    if [[ -f "$ROOT_CMD_DIR/$cmd_file" ]]; then
        cp "$ROOT_CMD_DIR/$cmd_file" "$WORKTREE_CMD_DIR/$cmd_file"
    fi
done

# Delete all OTHER files from the worktree's .claude/commands/
for f in "$WORKTREE_CMD_DIR"/*; do
    [[ -f "$f" ]] || continue
    basename_f="$(basename "$f")"
    if [[ "$basename_f" != "pl-local-push.md" && "$basename_f" != "pl-local-pull.md" ]]; then
        rm "$f"
        # Mark the deletion as intentional so git doesn't report it as dirty
        git -C "$WORKTREE_PATH" update-index --skip-worktree ".claude/commands/$basename_f" 2>/dev/null || true
    fi
done

# --- Config propagation (Section 2.2 step 7) ---
LIVE_CONFIG="$PROJECT_ROOT/.purlin/config.json"
WORKTREE_CONFIG="$WORKTREE_PATH/.purlin/config.json"

if [[ -f "$LIVE_CONFIG" ]]; then
    mkdir -p "$(dirname "$WORKTREE_CONFIG")"
    cp "$LIVE_CONFIG" "$WORKTREE_CONFIG"
fi

# --- Summary ---
echo ""
echo "Isolation created:"
echo "  Name:      $NAME"
echo "  Path:      $WORKTREE_PATH"
echo "  Branch:    $BRANCH_NAME"
echo ""
echo "Next steps:"
echo "  cd $WORKTREE_PATH"
echo "  # Launch your agent from within the worktree"
echo "  # When done, run /pl-local-push to merge back to main"
