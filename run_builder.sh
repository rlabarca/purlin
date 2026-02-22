#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="$SCRIPT_DIR/purlin"

# Fall back to local instructions/ if not a submodule consumer
if [ ! -d "$CORE_DIR/instructions" ]; then
    CORE_DIR="$SCRIPT_DIR"
fi

export AGENTIC_PROJECT_ROOT="$SCRIPT_DIR"

PROMPT_FILE=$(mktemp)
trap "rm -f '$PROMPT_FILE'" EXIT

cat "$CORE_DIR/instructions/HOW_WE_WORK_BASE.md" > "$PROMPT_FILE"
printf "\n\n" >> "$PROMPT_FILE"
cat "$CORE_DIR/instructions/BUILDER_BASE.md" >> "$PROMPT_FILE"

if [ -f "$SCRIPT_DIR/.agentic_devops/HOW_WE_WORK_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.agentic_devops/HOW_WE_WORK_OVERRIDES.md" >> "$PROMPT_FILE"
fi

if [ -f "$SCRIPT_DIR/.agentic_devops/BUILDER_OVERRIDES.md" ]; then
    printf "\n\n" >> "$PROMPT_FILE"
    cat "$SCRIPT_DIR/.agentic_devops/BUILDER_OVERRIDES.md" >> "$PROMPT_FILE"
fi

# --- Read agent config from config.json ---
CONFIG_FILE="$SCRIPT_DIR/.agentic_devops/config.json"
AGENT_ROLE="builder"

AGENT_PROVIDER="claude"
AGENT_MODEL=""
AGENT_EFFORT=""
AGENT_BYPASS="false"

if [ -f "$CONFIG_FILE" ]; then
    eval "$(python3 -c "
import json
try:
    c = json.load(open('$CONFIG_FILE'))
    a = c.get('agents', {}).get('$AGENT_ROLE', {})
    print(f'AGENT_PROVIDER=\"{a.get(\"provider\", \"claude\")}\"')
    print(f'AGENT_MODEL=\"{a.get(\"model\", \"\")}\"')
    print(f'AGENT_EFFORT=\"{a.get(\"effort\", \"\")}\"')
    bp = 'true' if a.get('bypass_permissions', False) else 'false'
    print(f'AGENT_BYPASS=\"{bp}\"')
except: pass
" 2>/dev/null)"
fi

# --- Provider dispatch ---
case "$AGENT_PROVIDER" in
  claude)
    CLI_ARGS=()
    [ -n "$AGENT_MODEL" ] && CLI_ARGS+=(--model "$AGENT_MODEL")
    [ -n "$AGENT_EFFORT" ] && CLI_ARGS+=(--effort "$AGENT_EFFORT")
    if [ "$AGENT_BYPASS" = "true" ]; then
        CLI_ARGS+=(--dangerously-skip-permissions)
    else
        # Builder: no --allowedTools (default permissions, user confirms each tool use)
        :
    fi
    claude "${CLI_ARGS[@]}" --append-system-prompt-file "$PROMPT_FILE" "Begin Builder session."
    ;;
  gemini)
    # Pre-launch: ensure .gemini/settings.json disables gitignore filtering
    mkdir -p "$SCRIPT_DIR/.gemini"
    python3 -c "
import json, os, sys
p = os.path.join('$SCRIPT_DIR', '.gemini', 'settings.json')
try:
    data = json.load(open(p))
except (json.JSONDecodeError, IOError, OSError):
    data = {}
data.setdefault('context', {}).setdefault('fileFiltering', {})['respectGitIgnore'] = False
with open(p, 'w') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
"
    git -C "$SCRIPT_DIR" add .gemini/settings.json 2>/dev/null
    CLI_ARGS=("chat" "Begin Builder session." "-m" "$AGENT_MODEL")
    [ "$AGENT_BYPASS" = "true" ] && CLI_ARGS+=("--yolo")
    GEMINI_SYSTEM_MD="$PROMPT_FILE" gemini "${CLI_ARGS[@]}"
    ;;
  *)
    echo "ERROR: Provider '$AGENT_PROVIDER' is not yet supported for agent invocation."
    echo "Supported providers: claude, gemini"
    echo "Provider '$AGENT_PROVIDER' models may be available for detection and configuration."
    echo "Launcher support requires a provider-specific invocation module."
    exit 1
    ;;
esac
