#!/bin/bash
# FileChanged hook — track companion file debt.
# When a code file changes, check if the corresponding feature's
# companion file was also updated. Records debt in
# .purlin/runtime/companion_debt.json so the mode-switch gate (Gate 3)
# can mechanically block switching out of Engineer mode with unpaid debt.
#
# Exit codes:
#   0 = always (this hook is informational, never blocks)

INPUT=$(cat)

# Extract the changed file path
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    print(data.get('file_path', data.get('path', '')))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$FILE_PATH" ]; then
    exit 0
fi

# Detect project root (same logic as mode-guard.sh)
_find_project_root() {
    if [ -n "$PURLIN_PROJECT_ROOT" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
        echo "$PURLIN_PROJECT_ROOT"; return
    fi
    local dir; dir="$(pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.purlin" ]; then echo "$dir"; return; fi
        dir="$(dirname "$dir")"
    done
    if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/.purlin" ]; then
        echo "$CLAUDE_PLUGIN_ROOT"; return
    fi
    echo "$(pwd)"
}

PROJECT_ROOT="$(_find_project_root)"
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"

# Early exit for non-trackable paths
case "$REL_PATH" in
    .purlin/*|.claude/*|*/__pycache__/*)
        exit 0
        ;;
    tests/qa/scenarios/*)
        exit 0
        ;;
esac

DEBT_FILE="$PROJECT_ROOT/.purlin/runtime/companion_debt.json"

# Use inline python for all JSON manipulation and feature mapping
python3 -c "
import json, os, sys, re, glob
from datetime import datetime, timezone

rel_path = '$REL_PATH'
project_root = '$PROJECT_ROOT'
debt_file = '$DEBT_FILE'
features_dir = os.path.join(project_root, 'features')

# Load existing debt
debt = {}
if os.path.isfile(debt_file):
    try:
        with open(debt_file) as f:
            debt = json.load(f)
    except (json.JSONDecodeError, IOError):
        debt = {}

def save_debt():
    os.makedirs(os.path.dirname(debt_file), exist_ok=True)
    with open(debt_file, 'w') as f:
        json.dump(debt, f, indent=2)

def feature_spec_exists(stem):
    \"\"\"Check if a feature spec exists in any category subdirectory.\"\"\"
    for category in os.listdir(features_dir):
        spec_path = os.path.join(features_dir, category, stem + '.md')
        if os.path.isfile(spec_path):
            return True
    return False

# Case 1: Companion file changed — clear debt for that feature
m = re.match(r'features/[^/]+/([^/]+)\.impl\.md$', rel_path)
if m:
    stem = m.group(1)
    if stem in debt:
        del debt[stem]
        save_debt()
    sys.exit(0)

# Skip feature specs and discovery sidecars (not code changes)
if re.match(r'features/', rel_path):
    sys.exit(0)

# Case 2: Test file changed — map to feature stem
m = re.match(r'tests/([^/]+)/', rel_path)
if m:
    stem = m.group(1)
    # Validate that a feature spec exists for this stem
    if not os.path.isdir(features_dir) or not feature_spec_exists(stem):
        sys.exit(0)
    # Add or update debt entry
    if stem in debt:
        files = debt[stem].get('files', [])
        if rel_path not in files:
            files.append(rel_path)
        debt[stem]['files'] = files
    else:
        debt[stem] = {
            'files': [rel_path],
            'first_seen': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        }
    save_debt()
    sys.exit(0)

# Everything else — no tracking
" 2>/dev/null

exit 0
