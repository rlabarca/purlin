#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR/agentic-dev"

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

export AGENTIC_PROJECT_ROOT="$SCRIPT_DIR"

PROMPT_FILE=$(mktemp)
trap "rm -f '$PROMPT_FILE'" EXIT

cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$PROMPT_FILE"
printf "\n\n" >> "$PROMPT_FILE"
cat "$CORE_DIR/instructions/ARCHITECT_BASE.md" >> "$PROMPT_FILE"

if [ -f "$SCRIPT_DIR/.agentic_devops/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.agentic_devops/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.agentic_devops/ARCHITECT_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.agentic_devops/ARCHITECT_OVERRIDES.md" >> "$PROMPT_FILE"
fi

claude \
    --allowedTools "Bash(git *)" "Bash(bash *)" "Bash(python3 *)" "Read" "Glob" "Grep" \
    --append-system-prompt-file "$PROMPT_FILE" "Begin Architect session."
