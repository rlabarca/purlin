#!/bin/bash
# PermissionRequest hook — YOLO auto-approve.
# Reads bypass_permissions from .purlin/config.json and auto-approves
# all permission dialogs when enabled.

INPUT=$(cat)

# Resolve project root reliably:
# 1. PURLIN_PROJECT_ROOT (set by MCP server / launcher)
# 2. CLAUDE_PLUGIN_ROOT (always set by Claude Code for plugin hooks) -> parent is project root
# 3. Climb from cwd looking for .purlin/ marker
_find_project_root() {
    # 1. Explicit env var (set by MCP server or parent process)
    if [ -n "$PURLIN_PROJECT_ROOT" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
        echo "$PURLIN_PROJECT_ROOT"; return
    fi
    # 2. Climb from CWD — most reliable for installed plugins (Claude Code
    #    sets hook CWD to the user's working directory)
    local dir; dir="$(pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.purlin" ]; then echo "$dir"; return; fi
        dir="$(dirname "$dir")"
    done
    # 3. CLAUDE_PLUGIN_ROOT — only works for --plugin-dir where plugin root IS the project
    if [ -n "$CLAUDE_PLUGIN_ROOT" ] && [ -d "$CLAUDE_PLUGIN_ROOT/.purlin" ]; then
        echo "$CLAUDE_PLUGIN_ROOT"; return
    fi
    # 4. Last resort
    echo "$(pwd)"
}

PROJECT_ROOT="$(_find_project_root)"

# Check YOLO flag in config
YOLO=$(PURLIN_PROJECT_ROOT="$PROJECT_ROOT" python3 -c "
import json, os, sys
try:
    project_root = os.environ['PURLIN_PROJECT_ROOT']
    # Check config.local.json first, then config.json
    for name in ['config.local.json', 'config.json']:
        try:
            with open(os.path.join(project_root, '.purlin', name)) as f:
                c = json.load(f)
            val = c.get('agents', {}).get('purlin', {}).get('bypass_permissions', False)
            if val is True or val == 'true':
                print('true')
                sys.exit(0)
        except (IOError, json.JSONDecodeError):
            continue
    print('false')
except Exception:
    print('false')
" 2>/dev/null)

# Extract the tool name from the permission request
TOOL_NAME=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('tool_name', ''))
except Exception:
    print('')
" 2>/dev/null)

if [ "$YOLO" = "true" ]; then
    # Auto-approve tool execution permissions, but NOT user-facing decisions.
    # These tools require the user to review and approve:
    # - AskUserQuestion: agent asking user to make choices (migration confirms, etc.)
    # - ExitPlanMode: agent proposing a plan — user must review before execution
    # - RemoteTrigger: triggers external scheduled agents — external side effects
    case "$TOOL_NAME" in
        AskUserQuestion|ExitPlanMode|RemoteTrigger)
            # Do NOT auto-approve — let the user decide
            ;;
        *)
            echo '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}'
            ;;
    esac
fi

exit 0
