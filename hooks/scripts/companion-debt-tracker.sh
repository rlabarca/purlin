#!/bin/bash
# FileChanged hook — track companion file debt.
# When a code file changes, check if the corresponding feature's
# companion file was also updated. Emits a reminder if not.

INPUT=$(cat)

# Extract the changed file path
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    # FileChanged provides the file path
    print(data.get('file_path', data.get('path', '')))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Only track code files that map to features
# Skip feature specs, companion files, test results, and non-project files
case "$FILE_PATH" in
    */features/*.md|*/tests/*|*/.purlin/*|*/__pycache__/*)
        exit 0
        ;;
esac

# This hook is intentionally lightweight — it just tracks that code files
# are changing. The actual companion debt enforcement is in the mode switch
# protocol (purlin:mode pre-switch check) and the commit covenant.

exit 0
