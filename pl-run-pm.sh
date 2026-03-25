#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR/purlin"

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

export PURLIN_PROJECT_ROOT="$SCRIPT_DIR"

# --- Deprecation warning ---
echo "============================================================" >&2
echo "DEPRECATED: pl-run-pm.sh is deprecated." >&2
echo "Use ./pl-run.sh instead. Examples:" >&2
echo "  ./pl-run.sh                  # Interactive Purlin agent" >&2
echo "  ./pl-run.sh --pm             # Start in PM mode" >&2
echo "============================================================" >&2

# Source terminal identity helper (no-op if missing)
if [ -f "$CORE_DIR/tools/terminal/identity.sh" ]; then
    source "$CORE_DIR/tools/terminal/identity.sh"
fi

PROMPT_FILE=$(mktemp)
cleanup() {
    type clear_agent_identity >/dev/null 2>&1 && clear_agent_identity
    rm -f "$PROMPT_FILE"
}
trap cleanup EXIT

cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$PROMPT_FILE"
printf "\n\n" >> "$PROMPT_FILE"
cat "$CORE_DIR/instructions/PM_BASE.md" >> "$PROMPT_FILE"

if [ -f "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.purlin/PM_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/PM_OVERRIDES.md" >> "$PROMPT_FILE"
fi

# --- Read agent config via resolver ---
AGENT_ROLE="pm"
export AGENT_ROLE
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

# PM-specific defaults when agents.pm is absent from config
# (resolver returns empty model/effort when role section is missing)
if [ -z "$AGENT_MODEL" ] && [ -z "$AGENT_EFFORT" ]; then
    AGENT_MODEL="claude-sonnet-4-6"
    AGENT_EFFORT="medium"
    AGENT_BYPASS="true"
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

# --- Claude dispatch ---
ROLE_DISPLAY="PM"
CLI_ARGS=()
[ -n "$AGENT_MODEL" ] && CLI_ARGS+=(--model "$AGENT_MODEL")
[ -n "$AGENT_EFFORT" ] && CLI_ARGS+=(--effort "$AGENT_EFFORT")
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
else
    CLI_ARGS+=(--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Write" "Edit" "Glob" "Grep")
fi
CLI_ARGS+=(--remote-control "$PROJECT_NAME | $ROLE_DISPLAY")
type set_agent_identity >/dev/null 2>&1 && set_agent_identity "PM"
claude "${CLI_ARGS[@]}" --append-system-prompt-file "$PROMPT_FILE" "Begin PM session."
