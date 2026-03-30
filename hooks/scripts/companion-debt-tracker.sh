#!/bin/bash
# FileChanged hook — track companion file debt.
#
# Two tracking levels:
#   1. Feature-level: maps tests/<stem>/ changes to feature stems in
#      companion_debt.json (for scan-based detection in purlin:status).
#   2. Session-level: records all code file writes and companion file writes
#      in session_writes.json (for mode-switch gate — blocks engineer exit
#      when code was written but no companion files were updated).
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
SESSION_WRITES_FILE="$PROJECT_ROOT/.purlin/runtime/session_writes.json"

# Use inline python for all JSON manipulation and feature mapping
python3 -c "
import json, os, sys, re
from datetime import datetime, timezone

rel_path = '$REL_PATH'
project_root = '$PROJECT_ROOT'
debt_file = '$DEBT_FILE'
session_writes_file = '$SESSION_WRITES_FILE'
features_dir = os.path.join(project_root, 'features')
runtime_dir = os.path.join(project_root, '.purlin', 'runtime')

# --- JSON helpers ---

def load_json(path, default):
    if os.path.isfile(path):
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return default

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)

# --- State ---

debt = load_json(debt_file, {})
session_writes = load_json(session_writes_file, {
    'code_files': [], 'companion_files_written': []
})

def save_debt():
    save_json(debt_file, debt)

def save_session_writes():
    save_json(session_writes_file, session_writes)

def get_mode():
    \"\"\"Read current mode from the runtime mode file.\"\"\"
    mode_file = os.path.join(runtime_dir, 'current_mode')
    try:
        with open(mode_file) as f:
            return f.read().strip() or None
    except (IOError, OSError):
        return None

def feature_spec_exists(stem):
    \"\"\"Check if a feature spec exists in any category subdirectory.\"\"\"
    if not os.path.isdir(features_dir):
        return False
    for category in os.listdir(features_dir):
        spec_path = os.path.join(features_dir, category, stem + '.md')
        if os.path.isfile(spec_path):
            return True
    return False

# --- Non-code file patterns (skip for session-level tracking) ---

_SKIP_SESSION_TRACKING = re.compile(
    r'^('
    r'docs/|'                    # documentation directories
    r'references/|'              # Purlin reference docs
    r'instructions/|'            # Purlin instruction files
    r'README|'                   # README files
    r'LICENSE|'                  # license files
    r'CHANGELOG|'               # changelogs
    r'CLAUDE\.md$|'             # Claude config
    r'\.gitignore$|'            # git config
    r'\.gitattributes$|'        # git config
    r'package-lock\.json$|'     # lock files (auto-generated)
    r'yarn\.lock$|'
    r'Cargo\.lock$|'
    r'go\.sum$|'
    r'poetry\.lock$'
    r')',
    re.IGNORECASE
)

# --- Case 1: Companion file changed ---

m = re.match(r'features/[^/]+/([^/]+)\.impl\.md$', rel_path)
if m:
    stem = m.group(1)
    # Clear feature-level debt
    if stem in debt:
        del debt[stem]
        save_debt()
    # Record in session writes
    if stem not in session_writes['companion_files_written']:
        session_writes['companion_files_written'].append(stem)
        save_session_writes()
    sys.exit(0)

# Skip feature specs and discovery sidecars (not code changes)
if re.match(r'features/', rel_path):
    sys.exit(0)

# --- Case 2: Test file changed — map to feature stem ---

m = re.match(r'tests/([^/]+)/', rel_path)
if m:
    stem = m.group(1)
    if not feature_spec_exists(stem):
        sys.exit(0)
    # Feature-level debt tracking
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
    # Session-level tracking (test files are code)
    if get_mode() == 'engineer':
        code_files = session_writes['code_files']
        if len(code_files) < _MAX_CODE_FILES and rel_path not in code_files:
            code_files.append(rel_path)
            save_session_writes()
    sys.exit(0)

# --- Case 3: Any other file — session-level tracking only ---
# Cap code_files list to prevent unbounded growth.  The mode switch gate
# only needs to know 'were any code files written?' — the count is for
# the user message, and exact paths beyond 50 are not useful.

_MAX_CODE_FILES = 50

if get_mode() == 'engineer' and not _SKIP_SESSION_TRACKING.search(rel_path):
    code_files = session_writes['code_files']
    if len(code_files) < _MAX_CODE_FILES and rel_path not in code_files:
        code_files.append(rel_path)
        save_session_writes()
    elif len(code_files) >= _MAX_CODE_FILES:
        # Already at cap — just bump the count marker if present
        if not any(f.startswith('... and ') for f in code_files):
            code_files.append('... and more')
            save_session_writes()
" 2>/dev/null

exit 0
