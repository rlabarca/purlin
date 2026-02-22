#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR/purlin"

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

export PURLIN_PROJECT_ROOT="$SCRIPT_DIR"

PROMPT_FILE=$(mktemp)
trap "rm -f '$PROMPT_FILE'" EXIT

cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$PROMPT_FILE"
printf "\n\n" >> "$PROMPT_FILE"
cat "$CORE_DIR/instructions/QA_BASE.md" >> "$PROMPT_FILE"

if [ -f "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.purlin/QA_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.purlin/QA_OVERRIDES.md" >> "$PROMPT_FILE"
fi

# --- Read agent config from config.json ---
CONFIG_FILE="$SCRIPT_DIR/.purlin/config.json"
AGENT_ROLE="qa"

AGENT_MODEL=""
AGENT_EFFORT=""
AGENT_BYPASS="false"
AGENT_STARTUP="true"
AGENT_RECOMMEND="true"

if [ -f "$CONFIG_FILE" ]; then
    eval "$(python3 -c "
import json
try:
    c = json.load(open('$CONFIG_FILE'))
    a = c.get('agents', {}).get('$AGENT_ROLE', {})
    print(f'AGENT_MODEL=\"{a.get(\"model\", \"\")}\"')
    print(f'AGENT_EFFORT=\"{a.get(\"effort\", \"\")}\"')
    bp = 'true' if a.get('bypass_permissions', False) else 'false'
    print(f'AGENT_BYPASS=\"{bp}\"')
    ss = 'true' if a.get('startup_sequence', True) else 'false'
    print(f'AGENT_STARTUP=\"{ss}\"')
    rn = 'true' if a.get('recommend_next_actions', True) else 'false'
    print(f'AGENT_RECOMMEND=\"{rn}\"')
except: pass
" 2>/dev/null)"
fi

# --- Validate startup controls ---
if [ "$AGENT_STARTUP" = "false" ] && [ "$AGENT_RECOMMEND" = "true" ]; then
    echo "Error: Invalid startup controls for $AGENT_ROLE: startup_sequence=false with recommend_next_actions=true is not a valid combination. Set recommend_next_actions to false or enable startup_sequence." >&2
    exit 1
fi

# --- Claude dispatch ---
CLI_ARGS=()
[ -n "$AGENT_MODEL" ] && CLI_ARGS+=(--model "$AGENT_MODEL")
[ -n "$AGENT_EFFORT" ] && CLI_ARGS+=(--effort "$AGENT_EFFORT")
if [ "$AGENT_BYPASS" = "true" ]; then
    CLI_ARGS+=(--dangerously-skip-permissions)
else
    CLI_ARGS+=(--allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep" "Write" "Edit")
fi
claude "${CLI_ARGS[@]}" --append-system-prompt-file "$PROMPT_FILE" "Begin QA verification session."
