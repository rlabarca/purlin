#!/usr/bin/env bash
# kill_isolation.sh — Safely remove a named isolation worktree.
# Usage: kill_isolation.sh <name> [--dry-run] [--force] [--project-root <path>]

set -euo pipefail

# --- Argument parsing ---
NAME=""
DRY_RUN=false
FORCE=false
PROJECT_ROOT=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
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
    echo "Usage: kill_isolation.sh <name> [--dry-run] [--force] [--project-root <path>]" >&2
    exit 1
fi

# Default project root to CWD
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"

# --- Name validation (Section 2.1) ---
if [[ ${#NAME} -gt 12 ]]; then
    echo "Error: Name '$NAME' is too long (${#NAME} chars). Maximum is 12 characters." >&2
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

# --- Verify worktree exists ---
WORKTREE_PATH="$PROJECT_ROOT/.worktrees/$NAME"

if [[ ! -d "$WORKTREE_PATH" ]]; then
    echo "Error: Isolation '$NAME' not found at $WORKTREE_PATH" >&2
    exit 1
fi

# --- Check dirty state (excluding .purlin/ files) ---
DIRTY_OUTPUT=$(git -C "$WORKTREE_PATH" status --porcelain 2>/dev/null | grep -v '^ *[MADRCU?!].*\.purlin/' | grep -v '^?? \.purlin/' || true)
IS_DIRTY=false
DIRTY_FILES=()

if [[ -n "$DIRTY_OUTPUT" ]]; then
    IS_DIRTY=true
    while IFS= read -r line; do
        # Extract the file path (skip the 3-char status prefix)
        file_path="${line:3}"
        DIRTY_FILES+=("$file_path")
    done <<< "$DIRTY_OUTPUT"
fi

# --- Check unsynced state ---
BRANCH_NAME="isolated/$NAME"
UNSYNCED_OUTPUT=$(git -C "$WORKTREE_PATH" log main..HEAD --oneline 2>/dev/null || true)
IS_UNSYNCED=false
UNSYNCED_COUNT=0

if [[ -n "$UNSYNCED_OUTPUT" ]]; then
    IS_UNSYNCED=true
    UNSYNCED_COUNT=$(echo "$UNSYNCED_OUTPUT" | wc -l | tr -d ' ')
fi

# --- Dry-run mode: output JSON and exit ---
if $DRY_RUN; then
    # Build dirty_files JSON array
    DIRTY_JSON="["
    first=true
    for f in "${DIRTY_FILES[@]+"${DIRTY_FILES[@]}"}"; do
        if $first; then
            first=false
        else
            DIRTY_JSON+=","
        fi
        # Escape quotes in file paths
        escaped=$(echo "$f" | sed 's/"/\\"/g')
        DIRTY_JSON+="\"$escaped\""
    done
    DIRTY_JSON+="]"

    cat <<ENDJSON
{
  "name": "$NAME",
  "dirty": $IS_DIRTY,
  "dirty_files": $DIRTY_JSON,
  "unsynced": $IS_UNSYNCED,
  "unsynced_branch": "$BRANCH_NAME",
  "unsynced_commits": $UNSYNCED_COUNT
}
ENDJSON
    exit 0
fi

# --- Safety checks ---

# HARD BLOCK: dirty state
if $IS_DIRTY && ! $FORCE; then
    echo "Error: Isolation '$NAME' has uncommitted changes:" >&2
    echo "" >&2
    for f in "${DIRTY_FILES[@]}"; do
        echo "  $f" >&2
    done
    echo "" >&2
    echo "Commit or stash your changes before killing this isolation." >&2
    echo "Use --force to bypass this check (changes will be lost)." >&2
    exit 1
fi

# WARN: unsynced commits
if $IS_UNSYNCED; then
    echo "Warning: Branch '$BRANCH_NAME' has $UNSYNCED_COUNT commit(s) not yet merged to main."
    echo "The branch will NOT be deleted — it still exists and can be re-added with:"
    echo "  git worktree add .worktrees/$NAME $BRANCH_NAME"
    echo ""
fi

# --- Remove per-team launcher scripts (Section 2.6) ---
rm -f "$PROJECT_ROOT/run_${NAME}_architect.sh"
rm -f "$PROJECT_ROOT/run_${NAME}_builder.sh"
rm -f "$PROJECT_ROOT/run_${NAME}_qa.sh"

# --- Remove worktree ---
git -C "$PROJECT_ROOT" worktree remove "$WORKTREE_PATH" --force 2>/dev/null || \
    git -C "$PROJECT_ROOT" worktree remove "$WORKTREE_PATH"

# --- Remove branch (only if fully merged) ---
if ! $IS_UNSYNCED; then
    git -C "$PROJECT_ROOT" branch -d "$BRANCH_NAME" 2>/dev/null || true
fi

# --- Remove .worktrees/ if empty ---
if [[ -d "$PROJECT_ROOT/.worktrees" ]]; then
    # Check if directory is empty (no files or subdirs besides . and ..)
    if [[ -z "$(ls -A "$PROJECT_ROOT/.worktrees" 2>/dev/null)" ]]; then
        rmdir "$PROJECT_ROOT/.worktrees"
    fi
fi

echo "Isolation '$NAME' removed."
