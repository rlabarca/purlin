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

# --- Parse launcher flags ---
CONTINUOUS_MODE="false"
while [[ $# -gt 0 ]]; do
    case "$1" in
        -qa) export PURLIN_BUILDER_QA=true; shift ;;
        --continuous)
            echo "The --continuous flag is deprecated. Set \`auto_start: true\` in agent config and relaunch the interactive Builder." >&2
            exit 1
            ;;
        *) shift ;;
    esac
done

# --- Prompt assembly ---
PROMPT_FILE=$(mktemp)
cleanup() {
    # Clear terminal identity (guarded in case helper was not sourced)
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
cat "$CORE_DIR/instructions/BUILDER_BASE.md" >> "$PROMPT_FILE"

if [ -f "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.purlin/BUILDER_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/BUILDER_OVERRIDES.md" >> "$PROMPT_FILE"
fi

# --- Read agent config via resolver ---
export AGENT_ROLE="builder"
mkdir -p "$SCRIPT_DIR/.purlin/runtime"
RESOLVER="$CORE_DIR/tools/config/resolve_config.py"

AGENT_MODEL=""
AGENT_EFFORT=""
AGENT_BYPASS="false"
AGENT_FIND_WORK="true"
AGENT_AUTO_START="false"
AGENT_MODEL_WARNING=""
AGENT_MODEL_WARNING_DISMISSED="false"

if [ -f "$RESOLVER" ]; then
    eval "$(PURLIN_PROJECT_ROOT="$SCRIPT_DIR" python3 "$RESOLVER" "$AGENT_ROLE" 2>/dev/null)"
fi

# --- Model warning display and auto-acknowledge ---
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
    echo "Error: Invalid startup controls for $AGENT_ROLE: find_work=false with auto_start=true is not a valid combination. Set auto_start to false or enable find_work." >&2
    exit 1
fi

# --- Build common CLI args ---
CLI_ARGS=()
[ -n "$AGENT_MODEL" ] && CLI_ARGS+=(--model "$AGENT_MODEL")
[ -n "$AGENT_EFFORT" ] && CLI_ARGS+=(--effort "$AGENT_EFFORT")
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
fi

# --- Launch ---
if [ "$CONTINUOUS_MODE" = "true" ]; then
    # --- Continuous mode (activated by subagent_parallel_builder) ---
    # Bootstrap phase
    type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Bootstrap"
    # (bootstrap work placeholder)
    type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder"

    # Phase loop
    PHASE_NUM=0
    TOTAL_PHASE_COUNT=0
    PHASE_DISPLAY=""
    while true; do
        # Sequential phase execution
        type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Phase ${PHASE_NUM}/${TOTAL_PHASE_COUNT}"

        # Parallel group execution
        type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Phases $PHASE_DISPLAY"

        # Evaluator (sequential path)
        type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Evaluating"
        # (evaluate sequential)

        # Evaluator (parallel path)
        type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder: Evaluating"
        # (evaluate parallel)

        # Between phases reset
        type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder"
        break  # placeholder -- real loop logic in subagent_parallel_builder
    done
else
    # --- Non-continuous mode
    type set_agent_identity >/dev/null 2>&1 && set_agent_identity "Builder"
    claude "${CLI_ARGS[@]}" --append-system-prompt-file "$PROMPT_FILE" "Begin Builder session."
    exit $?
fi
