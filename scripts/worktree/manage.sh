#!/usr/bin/env bash
# manage.sh -- Worktree management helper for purlin:worktree skill
# Usage: manage.sh list | cleanup-stale [--dry-run]
#
# Outputs JSON to stdout for agent consumption.
# Diagnostic messages go to stderr.

set -euo pipefail

###############################################################################
# Help
###############################################################################
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    cat <<'HELP'
Usage: manage.sh <subcommand> [options]

Subcommands:
  list              Show all worktrees with status (JSON to stdout)
  cleanup-stale     Remove stale/orphaned worktrees (JSON to stdout)
  check-lock <path> Check if a worktree is safe to enter (JSON to stdout)
  claim <path>      Update session lock to claim a stale worktree (JSON to stdout)

Options:
  --dry-run         (cleanup-stale only) Report without removing
  --help, -h        Show this help

Environment:
  PURLIN_PROJECT_ROOT   Override project root detection
HELP
    exit 0
fi

###############################################################################
# Path Resolution (submodule-safe)
###############################################################################
SOURCE="${BASH_SOURCE[0]}"
while [ -L "$SOURCE" ]; do
    LINK_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"
    SOURCE="$(readlink "$SOURCE")"
    [[ "$SOURCE" != /* ]] && SOURCE="$LINK_DIR/$SOURCE"
done
SCRIPT_DIR="$(cd "$(dirname "$SOURCE")" && pwd)"

if [[ -n "${PURLIN_PROJECT_ROOT:-}" ]] && [[ -d "$PURLIN_PROJECT_ROOT/.purlin" ]]; then
    PROJECT_ROOT="$(cd "$PURLIN_PROJECT_ROOT" && pwd -P)"
else
    # Climb from script dir: scripts/worktree/ -> scripts/ -> project root
    PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"
    if [[ ! -d "$PROJECT_ROOT/.purlin" ]]; then
        # Try submodule layout
        PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
    fi
fi

if [[ ! -d "$PROJECT_ROOT/.purlin" ]]; then
    echo '{"error": "Cannot find project root (.purlin/ not found)"}' >&2
    exit 1
fi

# Source bootstrap.sh if it exists for shared functions
if [[ -f "$SCRIPT_DIR/../bootstrap.sh" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/../bootstrap.sh"
fi

###############################################################################
# Helpers
###############################################################################

# Parse JSON value from a simple single-line JSON object.
# Usage: _json_value '{"key": "val"}' key
# Handles string and numeric values.
_json_value() {
    local json="$1" key="$2"
    # Try string value first, then numeric
    local val
    val=$(echo "$json" | sed -n "s/.*\"$key\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p")
    if [[ -z "$val" ]]; then
        val=$(echo "$json" | sed -n "s/.*\"$key\"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p")
    fi
    echo "$val"
}

# Check if a PID is alive
_pid_alive() {
    local pid="$1"
    if [[ -z "$pid" ]]; then
        return 1
    fi
    kill -0 "$pid" 2>/dev/null
}

# Compute age in seconds from an ISO 8601 timestamp (UTC)
_age_seconds() {
    local ts="$1"
    if [[ -z "$ts" ]]; then
        echo "0"
        return
    fi
    local now_epoch ts_epoch
    now_epoch=$(date +%s)
    # Handle both GNU and BSD date
    if date -d "2000-01-01" +%s &>/dev/null; then
        # GNU date
        ts_epoch=$(date -d "$ts" +%s 2>/dev/null || echo "$now_epoch")
    else
        # BSD date (macOS) -- convert ISO 8601 to a format -j -f understands
        # Input: 2026-03-25T14:30:00Z
        ts_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$ts" +%s 2>/dev/null || echo "$now_epoch")
    fi
    echo $(( now_epoch - ts_epoch ))
}

# Get age from lock file mtime as fallback
_file_age_seconds() {
    local filepath="$1"
    if [[ ! -e "$filepath" ]]; then
        echo "0"
        return
    fi
    local now_epoch file_epoch
    now_epoch=$(date +%s)
    if stat --version &>/dev/null 2>&1; then
        # GNU stat
        file_epoch=$(stat -c %Y "$filepath" 2>/dev/null || echo "$now_epoch")
    else
        # BSD stat (macOS)
        file_epoch=$(stat -f %m "$filepath" 2>/dev/null || echo "$now_epoch")
    fi
    echo $(( now_epoch - file_epoch ))
}

# Escape a string for safe JSON embedding
_json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\t'/\\t}"
    echo "$s"
}

###############################################################################
# Worktree Discovery
###############################################################################

# Collect worktree info into parallel arrays.
# Sets: WT_PATHS, WT_BRANCHES, WT_LABELS, WT_STATUSES, WT_PIDS, WT_MODES, WT_AGES
_discover_worktrees() {
    WT_PATHS=()
    WT_BRANCHES=()
    WT_LABELS=()
    WT_STATUSES=()
    WT_PIDS=()
    WT_MODES=()
    WT_AGES=()

    local wt_path="" wt_branch=""
    local purlin_wt_dir="$PROJECT_ROOT/.purlin/worktrees"

    # Parse porcelain output from git worktree list
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^worktree\ (.+) ]]; then
            wt_path="${BASH_REMATCH[1]}"
        elif [[ "$line" =~ ^branch\ refs/heads/(.+) ]]; then
            wt_branch="${BASH_REMATCH[1]}"
        elif [[ -z "$line" ]]; then
            # End of a worktree entry -- process if it is under .purlin/worktrees/
            if [[ -n "$wt_path" ]] && [[ "$wt_path" == "$purlin_wt_dir"* ]]; then
                _classify_worktree "$wt_path" "$wt_branch"
            fi
            wt_path=""
            wt_branch=""
        fi
    done < <(git -C "$PROJECT_ROOT" worktree list --porcelain 2>/dev/null; echo "")
    # The trailing echo ensures the last entry is processed
}

_classify_worktree() {
    local path="$1" branch="$2"
    local lock_file="$path/.purlin_session.lock"
    local label_file="$path/.purlin_worktree_label"

    local label="" pid="" mode="" started="" status="" age="0"

    # Read label
    if [[ -f "$label_file" ]]; then
        label="$(cat "$label_file" 2>/dev/null | tr -d '[:space:]')"
    fi
    if [[ -z "$label" ]]; then
        label="$(basename "$path")"
    fi

    # Read session lock
    if [[ -f "$lock_file" ]]; then
        local lock_json
        lock_json="$(cat "$lock_file" 2>/dev/null || echo "")"
        pid="$(_json_value "$lock_json" "pid")"
        mode="$(_json_value "$lock_json" "mode")"
        started="$(_json_value "$lock_json" "started")"

        # Classify based on PID liveness
        if _pid_alive "$pid"; then
            status="active"
        else
            status="stale"
        fi

        # Compute age from started timestamp
        if [[ -n "$started" ]]; then
            age="$(_age_seconds "$started")"
        else
            age="$(_file_age_seconds "$lock_file")"
        fi
    else
        # No lock file
        status="orphaned"
        pid=""
        mode=""
        # Use directory mtime for age
        age="$(_file_age_seconds "$path")"
    fi

    WT_PATHS+=("$path")
    WT_BRANCHES+=("$branch")
    WT_LABELS+=("$label")
    WT_STATUSES+=("$status")
    WT_PIDS+=("$pid")
    WT_MODES+=("$mode")
    WT_AGES+=("$age")
}

###############################################################################
# Subcommand: list
###############################################################################
_cmd_list() {
    _discover_worktrees

    local count=${#WT_PATHS[@]}

    if [[ "$count" -eq 0 ]]; then
        echo '{"worktrees": []}'
        return 0
    fi

    # Build JSON array
    local json='{"worktrees": ['
    local i
    for (( i=0; i<count; i++ )); do
        if [[ "$i" -gt 0 ]]; then
            json+=","
        fi
        local path_esc branch_esc label_esc mode_esc
        path_esc="$(_json_escape "${WT_PATHS[$i]}")"
        branch_esc="$(_json_escape "${WT_BRANCHES[$i]}")"
        label_esc="$(_json_escape "${WT_LABELS[$i]}")"
        mode_esc="$(_json_escape "${WT_MODES[$i]}")"

        local pid_json
        if [[ -n "${WT_PIDS[$i]}" ]]; then
            pid_json="${WT_PIDS[$i]}"
        else
            pid_json="null"
        fi

        json+="{"
        json+="\"path\": \"$path_esc\","
        json+="\"label\": \"$label_esc\","
        json+="\"branch\": \"$branch_esc\","
        json+="\"status\": \"${WT_STATUSES[$i]}\","
        json+="\"pid\": $pid_json,"
        json+="\"mode\": \"$mode_esc\","
        json+="\"age_seconds\": ${WT_AGES[$i]}"
        json+="}"
    done
    json+=']}'

    echo "$json"
}

###############################################################################
# Subcommand: cleanup-stale
###############################################################################
_cmd_cleanup_stale() {
    local dry_run=false
    if [[ "${1:-}" == "--dry-run" ]]; then
        dry_run=true
    fi

    _discover_worktrees

    local count=${#WT_PATHS[@]}
    local cleaned=()
    local has_uncommitted=()
    local skipped_active=()

    local i
    for (( i=0; i<count; i++ )); do
        local label="${WT_LABELS[$i]}"
        local path="${WT_PATHS[$i]}"
        local branch="${WT_BRANCHES[$i]}"
        local status="${WT_STATUSES[$i]}"

        if [[ "$status" == "active" ]]; then
            skipped_active+=("$label")
            continue
        fi

        # Stale or orphaned -- check for uncommitted work
        local porcelain_output
        porcelain_output="$(git -C "$path" status --porcelain 2>/dev/null || echo "")"

        if [[ -n "$porcelain_output" ]]; then
            has_uncommitted+=("$label")
            echo "Worktree $label has uncommitted changes -- skipping (agent handles prompt)" >&2
        else
            if [[ "$dry_run" == "true" ]]; then
                echo "dry-run: would remove $label ($path, branch $branch)" >&2
                cleaned+=("$label")
            else
                # Remove worktree and branch
                git -C "$PROJECT_ROOT" worktree remove "$path" 2>/dev/null || true
                git -C "$PROJECT_ROOT" branch -d "$branch" 2>/dev/null || true
                echo "Removed worktree $label ($path)" >&2
                cleaned+=("$label")
            fi
        fi
    done

    # Build JSON output
    local json='{"cleaned": ['
    local first=true
    for item in "${cleaned[@]+"${cleaned[@]}"}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            json+=","
        fi
        json+="\"$(_json_escape "$item")\""
    done
    json+='], "has_uncommitted": ['

    first=true
    for item in "${has_uncommitted[@]+"${has_uncommitted[@]}"}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            json+=","
        fi
        json+="\"$(_json_escape "$item")\""
    done
    json+='], "skipped_active": ['

    first=true
    for item in "${skipped_active[@]+"${skipped_active[@]}"}"; do
        if [[ "$first" == "true" ]]; then
            first=false
        else
            json+=","
        fi
        json+="\"$(_json_escape "$item")\""
    done
    json+=']}'

    echo "$json"
}

###############################################################################
# Subcommand: check-lock
# Check if a worktree is safe to enter (no live PID owns it).
# Returns JSON: {"safe": true/false, "status": "...", "pid": N|null, ...}
###############################################################################
_cmd_check_lock() {
    local wt_path="${1:-}"
    if [[ -z "$wt_path" ]]; then
        echo '{"error": "worktree path required"}' >&2
        exit 1
    fi

    local lock_file="$wt_path/.purlin_session.lock"
    local label_file="$wt_path/.purlin_worktree_label"

    local label=""
    if [[ -f "$label_file" ]]; then
        label="$(cat "$label_file" 2>/dev/null | tr -d '[:space:]')"
    fi

    if [[ ! -f "$lock_file" ]]; then
        echo "{\"safe\": true, \"status\": \"orphaned\", \"pid\": null, \"label\": \"$label\"}"
        return 0
    fi

    local lock_json pid
    lock_json="$(cat "$lock_file" 2>/dev/null || echo "")"
    pid="$(_json_value "$lock_json" "pid")"
    local mode
    mode="$(_json_value "$lock_json" "mode")"

    if _pid_alive "$pid"; then
        echo "{\"safe\": false, \"status\": \"active\", \"pid\": $pid, \"label\": \"$label\", \"mode\": \"$mode\"}"
        return 0
    fi

    echo "{\"safe\": true, \"status\": \"stale\", \"pid\": $pid, \"label\": \"$label\", \"mode\": \"$mode\"}"
}

###############################################################################
# Subcommand: claim
# Update the session lock to claim a stale/orphaned worktree for the current process.
# Usage: claim <path> [--mode <mode>]
###############################################################################
_cmd_claim() {
    local wt_path="${1:-}"
    if [[ -z "$wt_path" ]]; then
        echo '{"error": "worktree path required"}' >&2
        exit 1
    fi
    shift

    local mode="unknown"
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --mode) mode="${2:-unknown}"; shift 2 ;;
            *) shift ;;
        esac
    done

    local lock_file="$wt_path/.purlin_session.lock"
    local label_file="$wt_path/.purlin_worktree_label"

    # Safety: reject if PID is alive
    if [[ -f "$lock_file" ]]; then
        local lock_json pid
        lock_json="$(cat "$lock_file" 2>/dev/null || echo "")"
        pid="$(_json_value "$lock_json" "pid")"
        if _pid_alive "$pid"; then
            echo "{\"error\": \"worktree is owned by active session (PID $pid)\", \"claimed\": false}"
            return 1
        fi
    fi

    # Read existing label
    local label=""
    if [[ -f "$label_file" ]]; then
        label="$(cat "$label_file" 2>/dev/null | tr -d '[:space:]')"
    fi

    # Write new session lock with current PID
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")
    local new_pid=$$

    cat > "$lock_file" <<EOF
{
  "pid": $new_pid,
  "started": "$timestamp",
  "mode": "$mode",
  "label": "$label"
}
EOF

    echo "{\"claimed\": true, \"pid\": $new_pid, \"label\": \"$label\", \"mode\": \"$mode\"}"
}

###############################################################################
# Main dispatch
###############################################################################
SUBCOMMAND="${1:-}"

case "$SUBCOMMAND" in
    list)
        _cmd_list
        ;;
    cleanup-stale)
        shift
        _cmd_cleanup_stale "$@"
        ;;
    check-lock)
        shift
        _cmd_check_lock "$@"
        ;;
    claim)
        shift
        _cmd_claim "$@"
        ;;
    "")
        echo "Error: no subcommand provided. Use --help for usage." >&2
        exit 1
        ;;
    *)
        echo "Error: unknown subcommand '$SUBCOMMAND'. Use --help for usage." >&2
        exit 1
        ;;
esac
