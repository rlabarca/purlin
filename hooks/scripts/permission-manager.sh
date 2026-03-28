#!/bin/bash
# PermissionRequest hook — YOLO auto-approve.
# Reads bypass_permissions from .purlin/config.json and auto-approves
# all permission dialogs when enabled.

INPUT=$(cat)

PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(pwd)}"

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
