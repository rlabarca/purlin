#!/bin/bash
# teardown_worktrees.sh — Safely remove git worktrees under .worktrees/.
# See features/agent_launchers_multiuser.md Section 2.6 for full specification.
set -uo pipefail

# Parse arguments
PROJECT_ROOT=""
FORCE=false
DRY_RUN=false
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
        --force)
            FORCE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: teardown_worktrees.sh [--force] [--dry-run] [--project-root <path>]"
            echo ""
            echo "Safely remove all git worktrees under .worktrees/."
            echo ""
            echo "Options:"
            echo "  --force              Bypass dirty-state safety check"
            echo "  --dry-run            Report safety status without removing anything"
            echo "  --project-root <path>  Project root directory (default: current directory)"
            echo "  -h, --help           Show this help message"
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

# Check if worktrees directory exists
if [ ! -d "$WORKTREES_DIR" ]; then
    echo "No .worktrees/ directory found. Nothing to tear down."
    exit 0
fi

# Discover worktree session directories
SESSIONS=()
for entry in "$WORKTREES_DIR"/*/; do
    [ -d "$entry" ] && SESSIONS+=("$entry")
done

if [ ${#SESSIONS[@]} -eq 0 ]; then
    echo "No worktree sessions found under .worktrees/. Nothing to tear down."
    rmdir "$WORKTREES_DIR" 2>/dev/null || true
    exit 0
fi

# Phase 1: Check for dirty worktrees (HARD BLOCK unless --force)
DIRTY_WORKTREES=()
DIRTY_FILES_OUTPUT=""
for session in "${SESSIONS[@]}"; do
    session_name="$(basename "$session")"
    porcelain_output=$(git -C "$session" status --porcelain 2>/dev/null || echo "")
    if [ -n "$porcelain_output" ]; then
        DIRTY_WORKTREES+=("$session_name")
        file_count=$(echo "$porcelain_output" | wc -l | tr -d ' ')
        DIRTY_FILES_OUTPUT="${DIRTY_FILES_OUTPUT}  ${session_name}: ${file_count} uncommitted file(s)\n"
        while IFS= read -r line; do
            DIRTY_FILES_OUTPUT="${DIRTY_FILES_OUTPUT}    ${line}\n"
        done <<< "$porcelain_output"
    fi
done

# Phase 2: Check for unmerged commits (WARN + ALLOW)
UNSYNCED_WORKTREES=()
UNSYNCED_OUTPUT=""
for session in "${SESSIONS[@]}"; do
    session_name="$(basename "$session")"
    unmerged=$(git -C "$session" log main..HEAD --oneline 2>/dev/null || echo "")
    if [ -n "$unmerged" ]; then
        commit_count=$(echo "$unmerged" | wc -l | tr -d ' ')
        branch_name=$(git -C "$session" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
        UNSYNCED_WORKTREES+=("$session_name")
        UNSYNCED_OUTPUT="${UNSYNCED_OUTPUT}  ${session_name} (${branch_name}): ${commit_count} commit(s) not merged to main\n"
    fi
done

# Dry-run: report status and exit
if [ "$DRY_RUN" = true ]; then
    echo "{"
    echo "  \"dirty_count\": ${#DIRTY_WORKTREES[@]},"
    if [ ${#DIRTY_WORKTREES[@]} -gt 0 ]; then
        echo "  \"dirty_worktrees\": ["
        first=true
        for session in "${SESSIONS[@]}"; do
            session_name="$(basename "$session")"
            porcelain_output=$(git -C "$session" status --porcelain 2>/dev/null || echo "")
            if [ -n "$porcelain_output" ]; then
                file_count=$(echo "$porcelain_output" | wc -l | tr -d ' ')
                files_json="["
                file_first=true
                while IFS= read -r line; do
                    if [ "$file_first" = true ]; then
                        file_first=false
                    else
                        files_json="${files_json},"
                    fi
                    # Escape double quotes in filenames
                    escaped_line=$(echo "$line" | sed 's/"/\\"/g')
                    files_json="${files_json}\"${escaped_line}\""
                done <<< "$porcelain_output"
                files_json="${files_json}]"
                if [ "$first" = true ]; then
                    first=false
                else
                    echo ","
                fi
                printf '    {"name": "%s", "file_count": %d, "files": %s}' "$session_name" "$file_count" "$files_json"
            fi
        done
        echo ""
        echo "  ],"
    else
        echo "  \"dirty_worktrees\": [],"
    fi
    echo "  \"unsynced_count\": ${#UNSYNCED_WORKTREES[@]},"
    if [ ${#UNSYNCED_WORKTREES[@]} -gt 0 ]; then
        echo "  \"unsynced_worktrees\": ["
        first=true
        for session in "${SESSIONS[@]}"; do
            session_name="$(basename "$session")"
            unmerged=$(git -C "$session" log main..HEAD --oneline 2>/dev/null || echo "")
            if [ -n "$unmerged" ]; then
                commit_count=$(echo "$unmerged" | wc -l | tr -d ' ')
                branch_name=$(git -C "$session" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
                if [ "$first" = true ]; then
                    first=false
                else
                    echo ","
                fi
                printf '    {"name": "%s", "branch": "%s", "commit_count": %d}' "$session_name" "$branch_name" "$commit_count"
            fi
        done
        echo ""
        echo "  ]"
    else
        echo "  \"unsynced_worktrees\": []"
    fi
    echo "}"
    exit 0
fi

# Enforce dirty hard block
if [ ${#DIRTY_WORKTREES[@]} -gt 0 ] && [ "$FORCE" = false ]; then
    echo "Error: Worktrees have uncommitted changes. Commit or stash before teardown." >&2
    echo "" >&2
    echo -e "$DIRTY_FILES_OUTPUT" >&2
    echo "Use --force to bypass this check (data will be lost)." >&2
    exit 1
fi

# Warn about unsynced commits (proceed anyway)
if [ ${#UNSYNCED_WORKTREES[@]} -gt 0 ]; then
    echo "Warning: Some worktrees have commits not yet merged to main."
    echo "The branches will survive worktree removal — no commits are lost."
    echo ""
    echo -e "$UNSYNCED_OUTPUT"
fi

# Remove worktrees
REMOVED=0
for session in "${SESSIONS[@]}"; do
    session_name="$(basename "$session")"
    if git -C "$PROJECT_ROOT" worktree remove "$session" --force 2>/dev/null; then
        echo "  REMOVED: $session_name"
        REMOVED=$((REMOVED + 1))
    else
        echo "  WARNING: Failed to remove $session_name" >&2
    fi
done

# Remove .worktrees/ if empty
if [ -d "$WORKTREES_DIR" ]; then
    rmdir "$WORKTREES_DIR" 2>/dev/null && echo "  REMOVED: .worktrees/" || true
fi

echo ""
echo "Teardown complete: $REMOVED worktree(s) removed."
