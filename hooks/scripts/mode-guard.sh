#!/bin/bash
# PreToolUse hook — mechanical mode guard enforcement.
# Intercepts Write/Edit/NotebookEdit calls, classifies the target file,
# and blocks writes that violate mode boundaries.
#
# Exit codes:
#   0 = allow the write
#   2 = block the write (tool error shown to agent)

set -e

# Read the hook input from stdin
INPUT=$(cat)

# Extract the file path from the tool input
# The hook receives JSON with tool_name and tool_input
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    tool_input = data.get('tool_input', {})
    # Write tool uses file_path, Edit uses file_path
    path = tool_input.get('file_path', '')
    print(path)
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    # Cannot determine file — allow (fail open)
    exit 0
fi

# Detect project root
PROJECT_ROOT="${PURLIN_PROJECT_ROOT:-$(pwd)}"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"

# Make path relative to project root for classification
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"

# Try MCP server classification first (via Python inline)
CLASSIFICATION=$(python3 -c "
import sys
sys.path.insert(0, '$PLUGIN_ROOT/scripts/mcp')
from config_engine import classify_file, get_mode
classification = classify_file('$REL_PATH')
mode = get_mode()
print(f'{classification}|{mode or \"none\"}')
" 2>/dev/null)

if [ -z "$CLASSIFICATION" ]; then
    # Fallback to file_classification.json
    CLASSIFICATION=$(python3 -c "
import json, sys, os, re
try:
    with open('$PLUGIN_ROOT/references/file_classification.json') as f:
        rules = json.load(f)
    path = '$REL_PATH'
    for rule in rules.get('rules', []):
        if re.search(rule['pattern'], path):
            print(rule['classification'] + '|none')
            sys.exit(0)
    print('CODE|none')
except Exception:
    print('')
" 2>/dev/null)
fi

if [ -z "$CLASSIFICATION" ]; then
    # Cannot classify — allow (fail open)
    exit 0
fi

FILE_CLASS=$(echo "$CLASSIFICATION" | cut -d'|' -f1)
CURRENT_MODE=$(echo "$CLASSIFICATION" | cut -d'|' -f2)

# If no mode is active, block all writes
if [ "$CURRENT_MODE" = "none" ] || [ "$CURRENT_MODE" = "None" ]; then
    echo '{"error":"No mode active. Activate a mode before writing files."}'
    exit 2
fi

# Check mode-file compatibility
case "$CURRENT_MODE" in
    engineer)
        if [ "$FILE_CLASS" = "SPEC" ] || [ "$FILE_CLASS" = "QA" ] || [ "$FILE_CLASS" = "INVARIANT" ]; then
            echo "{\"error\":\"Mode guard: $REL_PATH is $FILE_CLASS-owned, not writable in Engineer mode.\"}"
            exit 2
        fi
        ;;
    pm)
        if [ "$FILE_CLASS" = "CODE" ] || [ "$FILE_CLASS" = "QA" ] || [ "$FILE_CLASS" = "INVARIANT" ]; then
            echo "{\"error\":\"Mode guard: $REL_PATH is $FILE_CLASS-owned, not writable in PM mode.\"}"
            exit 2
        fi
        ;;
    qa)
        if [ "$FILE_CLASS" = "CODE" ] || [ "$FILE_CLASS" = "SPEC" ] || [ "$FILE_CLASS" = "INVARIANT" ]; then
            echo "{\"error\":\"Mode guard: $REL_PATH is $FILE_CLASS-owned, not writable in QA mode.\"}"
            exit 2
        fi
        ;;
esac

# Invariant files blocked regardless of mode
if [ "$FILE_CLASS" = "INVARIANT" ]; then
    echo "{\"error\":\"Mode guard: $REL_PATH is an invariant file. No mode can write to invariant files.\"}"
    exit 2
fi

exit 0
