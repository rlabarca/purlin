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
    # 1. Explicit env var
    if [ -n "$PURLIN_PROJECT_ROOT" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
        echo "$PURLIN_PROJECT_ROOT"
        return
    fi
    # 2. CLAUDE_PLUGIN_ROOT — for inline plugins this IS the repo root;
    #    for installed plugins it may be a subdirectory. Check both.
    if [ -n "$CLAUDE_PLUGIN_ROOT" ]; then
        if [ -d "$CLAUDE_PLUGIN_ROOT/.purlin" ]; then
            echo "$CLAUDE_PLUGIN_ROOT"
            return
        fi
        if [ -d "$CLAUDE_PLUGIN_ROOT/../.purlin" ]; then
            echo "$(cd "$CLAUDE_PLUGIN_ROOT/.." && pwd)"
            return
        fi
    fi
    # 3. Climb from the script's own location (most reliable fallback —
    #    the script is always inside the repo at hooks/scripts/)
    local dir
    dir="$(cd "$(dirname "$0")" && pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.purlin" ]; then
            echo "$dir"
            return
        fi
        dir="$(dirname "$dir")"
    done
    # 4. Last resort: cwd
    echo "$(pwd)"
}

PROJECT_ROOT="$(_find_project_root)"

# Check YOLO flag in config
YOLO=$(python3 -c "
import json, sys
try:
    # Check config.local.json first, then config.json
    for path in ['$PROJECT_ROOT/.purlin/config.local.json', '$PROJECT_ROOT/.purlin/config.json']:
        try:
            with open(path) as f:
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

if [ "$YOLO" = "true" ]; then
    echo '{"hookSpecificOutput":{"hookEventName":"PermissionRequest","decision":{"behavior":"allow"}}}'
fi

exit 0
