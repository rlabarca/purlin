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

while [[ $# -gt 0 ]]; do
    case "$1" in
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
        --pm) PURLIN_MODE="pm"; shift ;;
        --qa) PURLIN_MODE="qa"; shift ;;
        --verify)
            PURLIN_MODE="qa"
            if [[ -n "${2:-}" && ! "$2" =~ ^-- ]]; then
                PURLIN_VERIFY_FEATURE="$2"
                shift 2
            else
                shift
            fi
            ;;
        --auto-start) PURLIN_AUTO_START="true"; shift ;;
        --find-work)
            PURLIN_FIND_WORK="$2"
            shift 2
            ;;
        --worktree) PURLIN_WORKTREE="true"; shift ;;
        *) shift ;;
    esac
done

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

cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$PROMPT_FILE"
printf "\n\n" >> "$PROMPT_FILE"

if [ -f "$CORE_DIR/instructions/PURLIN_BASE.md" ]; then
    cat "$CORE_DIR/instructions/PURLIN_BASE.md" >> "$PROMPT_FILE"
else
    echo "ERROR: instructions/PURLIN_BASE.md not found at $CORE_DIR/instructions/" >&2
    exit 1
fi

if [ -f "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
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

    echo ""
    echo "Stored selection: model=$AGENT_MODEL effort=$AGENT_EFFORT"
    echo "(To change later: ./pl-run.sh --model)"
    echo ""
fi

# --- CLI overrides ---
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

if [[ -n "$PURLIN_AUTO_START" ]]; then
    AGENT_AUTO_START="true"
fi

if [[ "$PURLIN_FIND_WORK" == "false" ]]; then
    AGENT_FIND_WORK="false"
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
        echo "Working in worktree: $WORKTREE_DIR"
        echo "Branch: $WORKTREE_BRANCH"
        echo "Run /pl-merge when done to merge back."
        echo ""
        cd "$WORKTREE_DIR"
        export PURLIN_PROJECT_ROOT="$WORKTREE_DIR"
    else
        echo "ERROR: Failed to create worktree. Continuing without isolation." >&2
    fi
fi

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
ROLE_DISPLAY="Purlin"
CLI_ARGS=()
[ -n "$AGENT_MODEL" ] && CLI_ARGS+=(--model "$AGENT_MODEL")
[ -n "$AGENT_EFFORT" ] && CLI_ARGS+=(--effort "$AGENT_EFFORT")

# Purlin always gets full permissions
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
fi

[ -n "$PROJECT_NAME" ] && CLI_ARGS+=(--remote-control "$PROJECT_NAME | $ROLE_DISPLAY")

type set_agent_identity >/dev/null 2>&1 && set_agent_identity "$ROLE_DISPLAY"
claude "${CLI_ARGS[@]}" --append-system-prompt-file "$PROMPT_FILE" "$SESSION_MSG"
exit $?
