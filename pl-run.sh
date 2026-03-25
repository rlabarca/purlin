#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR/purlin"

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

export PURLIN_PROJECT_ROOT="$SCRIPT_DIR"

# Source terminal identity helper (no-op if missing)
if [ -f "$CORE_DIR/tools/terminal/identity.sh" ]; then
    source "$CORE_DIR/tools/terminal/identity.sh"
fi

# --- Parse arguments ---
PURLIN_MODE=""
PURLIN_AUTO_START=""
PURLIN_MODEL_OVERRIDE=""
PURLIN_EFFORT_OVERRIDE=""
PURLIN_WORKTREE=""
PURLIN_FIND_WORK=""
PURLIN_VERIFY_FEATURE=""
PURLIN_YOLO=""
PURLIN_NO_SAVE=""

show_help() {
    cat <<'HELPTEXT'
Usage: ./pl-run.sh [OPTIONS]

Launch a Purlin agent session.

Saved preferences (written to .purlin/config.local.json):
  --model [id]         Set default model (opus, sonnet, haiku, or full ID).
                       Interactive if no value. Saves to config.
  --effort <level>     Set default effort level (high, medium). Saves to config.
  --yolo               Enable YOLO mode (skip all permission prompts). Saves to config.
  --no-yolo            Disable YOLO mode (restore permission prompts). Saves to config.
  --find-work <bool>   Set default work discovery (true/false). Saves to config.

  Use --no-save to apply any of the above for THIS SESSION ONLY
  without changing your saved config.
  Example: ./pl-run.sh --no-save --model haiku

Session options (this run only, never saved):
  --mode <mode>        Set starting mode (pm, engineer, qa).
  --auto-build         Start in Engineer mode with auto-start.
  --auto-verify        Start in QA mode with auto-start.
  --pm                 Start in PM mode.
  --qa                 Start in QA mode.
  --verify [feature]   Start QA mode. Optional: feature name to verify.
  --auto-start         With --mode: begin executing immediately.
                       Example: --mode engineer --auto-start. No effect without --mode.
  --worktree           Run in an isolated git worktree.

Other:
  --no-save            Don't save preferences to config (use with flags above).
  --help               Show this help message and exit.

Examples:
  ./pl-run.sh                           # Interactive session
  ./pl-run.sh --auto-build              # Engineer mode, auto-start
  ./pl-run.sh --model opus              # Use Opus (saved for next time)
  ./pl-run.sh --no-save --model haiku   # Use Haiku just this once
  ./pl-run.sh --yolo                    # YOLO mode on (saved)
  ./pl-run.sh --no-save --yolo          # YOLO just this session
  ./pl-run.sh --verify my_feature       # QA verify a specific feature
HELPTEXT
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help)
            show_help
            exit 0
            ;;
        --model)
            if [[ -n "${2:-}" && ! "$2" =~ ^-- ]]; then
                PURLIN_MODEL_OVERRIDE="$2"
                shift 2
            else
                PURLIN_MODEL_OVERRIDE="__interactive__"
                shift
            fi
            ;;
        --effort)
            PURLIN_EFFORT_OVERRIDE="$2"
            shift 2
            ;;
        --yolo)
            PURLIN_YOLO="true"; shift ;;
        --no-yolo)
            PURLIN_YOLO="false"; shift ;;
        --find-work)
            PURLIN_FIND_WORK="$2"
            shift 2
            ;;
        --no-save)
            PURLIN_NO_SAVE="true"; shift ;;
        --mode)
            PURLIN_MODE="$2"
            shift 2
            ;;
        --auto-build)
            PURLIN_MODE="engineer"
            PURLIN_AUTO_START="true"
            shift
            ;;
        --auto-verify)
            PURLIN_MODE="qa"
            PURLIN_AUTO_START="true"
            shift
            ;;
        --pm)
            PURLIN_MODE="pm"; shift ;;
        --qa)
            PURLIN_MODE="qa"; shift ;;
        --verify)
            PURLIN_MODE="qa"
            if [[ -n "${2:-}" && ! "$2" =~ ^-- ]]; then
                PURLIN_VERIFY_FEATURE="$2"
                shift 2
            else
                shift
            fi
            ;;
        --auto-start)
            PURLIN_AUTO_START="true"; shift ;;
        --worktree)
            PURLIN_WORKTREE="true"; shift ;;
        *) shift ;;
    esac
done

# --- Compute mode display name (identity set after worktree creation) ---
case "${PURLIN_MODE:-}" in
    engineer) MODE_NAME="Engineer" ;;
    qa)       MODE_NAME="QA" ;;
    pm)       MODE_NAME="PM" ;;
    *)        MODE_NAME="Purlin" ;;
esac

# --- Prompt assembly ---
PROMPT_FILE=$(mktemp)
cleanup() {
    type clear_agent_identity >/dev/null 2>&1 && clear_agent_identity
    rm -f "$PROMPT_FILE"
}
trap cleanup EXIT

graceful_stop() {
    type clear_agent_identity >/dev/null 2>&1 && clear_agent_identity
    trap - INT
    kill -INT $$
}
trap graceful_stop INT

# PURLIN_BASE.md is the single instruction file (HOW_WE_WORK content merged in)
if [ -f "$CORE_DIR/instructions/PURLIN_BASE.md" ]; then
    cat "$CORE_DIR/instructions/PURLIN_BASE.md" > "$PROMPT_FILE"
else
    echo "ERROR: instructions/PURLIN_BASE.md not found at $CORE_DIR/instructions/" >&2
    exit 1
fi

if [ -f "$SCRIPT_DIR/.purlin/PURLIN_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/PURLIN_OVERRIDES.md" >> "$PROMPT_FILE"
fi

# --- Read agent config via resolver ---
export AGENT_ROLE="purlin"
mkdir -p "$SCRIPT_DIR/.purlin/runtime"
RESOLVER="$CORE_DIR/tools/config/resolve_config.py"

AGENT_MODEL=""
AGENT_EFFORT=""
AGENT_BYPASS="false"
AGENT_FIND_WORK="true"
AGENT_AUTO_START="false"
AGENT_MODEL_WARNING=""
AGENT_MODEL_WARNING_DISMISSED="false"
PROJECT_NAME=""

if [ -f "$RESOLVER" ]; then
    eval "$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" "$AGENT_ROLE" 2>/dev/null)"
fi

# --- First-run / interactive model selection ---
# Always persists (not affected by --no-save — this establishes defaults)
if [[ "$PURLIN_MODEL_OVERRIDE" == "__interactive__" ]] || [[ -z "$AGENT_MODEL" ]]; then
    echo ""
    echo "Select model:"
    echo "  1. Opus 4.6         (200K context)"
    echo "  2. Sonnet 4.6       (200K context, cost-efficient)"
    echo "  3. Opus 4.6 [1M]    (1M context, extended)"
    echo ""
    read -p "Choice [1]: " MODEL_CHOICE
    MODEL_CHOICE="${MODEL_CHOICE:-1}"

    case "$MODEL_CHOICE" in
        1) AGENT_MODEL="claude-opus-4-6" ;;
        2) AGENT_MODEL="claude-sonnet-4-6" ;;
        3) AGENT_MODEL="claude-opus-4-6[1m]" ;;
        *) AGENT_MODEL="claude-opus-4-6" ;;
    esac

    echo ""
    echo "Select effort:"
    echo "  1. high   (thorough)"
    echo "  2. medium (balanced)"
    echo ""
    read -p "Choice [1]: " EFFORT_CHOICE
    EFFORT_CHOICE="${EFFORT_CHOICE:-1}"

    case "$EFFORT_CHOICE" in
        1) AGENT_EFFORT="high" ;;
        2) AGENT_EFFORT="medium" ;;
        *) AGENT_EFFORT="high" ;;
    esac

    # First-run always persists regardless of --no-save
    if [ -f "$RESOLVER" ]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin model "$AGENT_MODEL" 2>/dev/null
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin effort "$AGENT_EFFORT" 2>/dev/null
    fi

    echo ""
    echo "Saved to config: model=$AGENT_MODEL effort=$AGENT_EFFORT"
    echo "(To change later: ./pl-run.sh --model)"
    echo ""
fi

# --- CLI overrides (apply sticky + ephemeral flags) ---
if [[ -n "$PURLIN_MODEL_OVERRIDE" && "$PURLIN_MODEL_OVERRIDE" != "__interactive__" ]]; then
    case "$PURLIN_MODEL_OVERRIDE" in
        opus|Opus*) AGENT_MODEL="claude-opus-4-6" ;;
        sonnet|Sonnet*) AGENT_MODEL="claude-sonnet-4-6" ;;
        haiku|Haiku*) AGENT_MODEL="claude-haiku-4-5-20251001" ;;
        *) AGENT_MODEL="$PURLIN_MODEL_OVERRIDE" ;;
    esac
fi

if [[ -n "$PURLIN_EFFORT_OVERRIDE" ]]; then
    AGENT_EFFORT="$PURLIN_EFFORT_OVERRIDE"
fi

if [[ -n "$PURLIN_YOLO" ]]; then
    AGENT_BYPASS="$PURLIN_YOLO"
fi

if [[ -n "$PURLIN_FIND_WORK" ]]; then
    AGENT_FIND_WORK="$PURLIN_FIND_WORK"
fi

if [[ -n "$PURLIN_AUTO_START" ]]; then
    AGENT_AUTO_START="true"
fi

# --- Model warning display ---
if [ -n "$AGENT_MODEL_WARNING" ] && [ "$AGENT_MODEL_WARNING_DISMISSED" != "true" ]; then
    echo "============================================================" >&2
    echo "WARNING: $AGENT_MODEL_WARNING" >&2
    echo "By continuing, you are acknowledging this warning." >&2
    echo "============================================================" >&2
    if [ -f "$RESOLVER" ]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" acknowledge_warning "$AGENT_MODEL" 2>/dev/null
    fi
fi

# --- Validate startup controls ---
if [ "$AGENT_FIND_WORK" = "false" ] && [ "$AGENT_AUTO_START" = "true" ]; then
    echo "Error: find_work=false with auto_start=true is not valid. Set auto_start to false or enable find_work." >&2
    exit 1
fi

# --- Persist sticky flags (after validation, before launch) ---
if [[ "$PURLIN_NO_SAVE" != "true" ]] && [ -f "$RESOLVER" ]; then
    if [[ -n "$PURLIN_MODEL_OVERRIDE" && "$PURLIN_MODEL_OVERRIDE" != "__interactive__" ]]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin model "$AGENT_MODEL" 2>/dev/null
    fi
    if [[ -n "$PURLIN_EFFORT_OVERRIDE" ]]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin effort "$AGENT_EFFORT" 2>/dev/null
    fi
    if [[ -n "$PURLIN_YOLO" ]]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin bypass_permissions "$PURLIN_YOLO" 2>/dev/null
    fi
    if [[ -n "$PURLIN_FIND_WORK" ]]; then
        PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" set_agent_config purlin find_work "$PURLIN_FIND_WORK" 2>/dev/null
    fi
fi

# --- CLI auto-update ---
if command -v claude >/dev/null 2>&1; then
    echo "Checking for Claude Code updates..." >&2
    if ! claude update --check >/dev/null 2>&1; then
        if claude update >/dev/null 2>&1; then
            echo "Claude Code updated successfully." >&2
        else
            echo "WARNING: Claude Code update failed. Continuing with current version." >&2
        fi
    fi
fi

# --- Worktree setup ---
if [[ "$PURLIN_WORKTREE" == "true" ]]; then
    WORKTREE_BRANCH="purlin-${PURLIN_MODE:-open}-$(date +%Y%m%d-%H%M%S)"
    WORKTREE_DIR="$SCRIPT_DIR/.purlin/worktrees/$WORKTREE_BRANCH"
    mkdir -p "$SCRIPT_DIR/.purlin/worktrees"
    if git worktree add "$WORKTREE_DIR" -b "$WORKTREE_BRANCH" 2>/dev/null; then
        # Assign worktree label (W1, W2, ...) — gap-filling
        _used_nums=()
        for _lf in "$SCRIPT_DIR/.purlin/worktrees"/*/.purlin_worktree_label; do
            [ -f "$_lf" ] || continue
            _n=$(tr -cd '0-9' < "$_lf")
            [ -n "$_n" ] && _used_nums+=("$_n")
        done
        _next=1
        while printf '%s\n' "${_used_nums[@]}" 2>/dev/null | grep -qx "$_next"; do
            _next=$((_next + 1))
        done
        WORKTREE_LABEL="W${_next}"
        echo "$WORKTREE_LABEL" > "$WORKTREE_DIR/.purlin_worktree_label"

        echo "Working in worktree: $WORKTREE_DIR ($WORKTREE_LABEL)"
        echo "Branch: $WORKTREE_BRANCH"
        echo "Run /pl-merge when done to merge back."
        echo ""
        cd "$WORKTREE_DIR"
        export PURLIN_PROJECT_ROOT="$WORKTREE_DIR"
    else
        echo "ERROR: Failed to create worktree. Continuing without isolation." >&2
    fi
fi

# --- Set terminal identity (after worktree so label is available) ---
ROLE_DISPLAY="$MODE_NAME"
if [[ -f "$PURLIN_PROJECT_ROOT/.purlin_worktree_label" ]]; then
    WORKTREE_LABEL=$(cat "$PURLIN_PROJECT_ROOT/.purlin_worktree_label")
    ROLE_DISPLAY="$MODE_NAME ($WORKTREE_LABEL)"
fi
_PROJECT_DISPLAY="${PROJECT_NAME:-$(basename "$PURLIN_PROJECT_ROOT")}"
type set_agent_identity >/dev/null 2>&1 && set_agent_identity "$ROLE_DISPLAY" "$_PROJECT_DISPLAY"

# --- Session message ---
SESSION_MSG="Begin Purlin session."
if [[ -n "$PURLIN_MODE" ]]; then
    case "$PURLIN_MODE" in
        engineer) SESSION_MSG="Begin Purlin session. Enter Engineer mode. Run /pl-build." ;;
        qa)
            if [[ -n "$PURLIN_VERIFY_FEATURE" ]]; then
                SESSION_MSG="Begin Purlin session. Enter QA mode. Run /pl-verify $PURLIN_VERIFY_FEATURE."
            else
                SESSION_MSG="Begin Purlin session. Enter QA mode. Run /pl-verify."
            fi
            ;;
        pm) SESSION_MSG="Begin Purlin session. Enter PM mode." ;;
    esac
fi

# --- Build CLI args and launch ---
CLI_ARGS=()
[ -n "$AGENT_MODEL" ] && CLI_ARGS+=(--model "$AGENT_MODEL")
[ -n "$AGENT_EFFORT" ] && CLI_ARGS+=(--effort "$AGENT_EFFORT")

# Purlin always gets full permissions
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
fi

# Session name: shown in remote control list and /resume picker
SESSION_NAME="$_PROJECT_DISPLAY | $ROLE_DISPLAY"
CLI_ARGS+=(--remote-control "$SESSION_NAME")
CLI_ARGS+=(--name "$SESSION_NAME")

claude "${CLI_ARGS[@]}" --append-system-prompt-file "$PROMPT_FILE" "$SESSION_MSG"
exit $?
