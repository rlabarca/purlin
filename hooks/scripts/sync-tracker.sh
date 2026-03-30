#!/bin/bash
# sync-tracker.sh — FileChanged hook.
# Tracks all file writes in sync_state.json, grouped by feature.
# Tracks all file writes grouped by feature for sync state.
#
# Exit codes:
#   0 = always (informational hook, never blocks)

INPUT=$(cat)

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

# Detect project root
_find_project_root() {
    if [ -n "${PURLIN_PROJECT_ROOT:-}" ] && [ -d "$PURLIN_PROJECT_ROOT/.purlin" ]; then
        echo "$PURLIN_PROJECT_ROOT"; return
    fi
    local dir; dir="$(pwd)"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.purlin" ]; then echo "$dir"; return; fi
        dir=$(dirname "$dir")
    done
    if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "$CLAUDE_PLUGIN_ROOT/.purlin" ]; then
        echo "$CLAUDE_PLUGIN_ROOT"; return
    fi
    echo "$(pwd)"
}

PROJECT_ROOT="$(_find_project_root)"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
REL_PATH="${FILE_PATH#$PROJECT_ROOT/}"

# Skip non-trackable paths
case "$REL_PATH" in
    .purlin/*|.claude/*|*/__pycache__/*) exit 0 ;;
esac

PURLIN_PROJECT_ROOT="$PROJECT_ROOT" PURLIN_PLUGIN_ROOT="$PLUGIN_ROOT" PURLIN_REL_PATH="$REL_PATH" python3 -c "
import json, os, sys, re
from datetime import datetime, timezone

rel_path = os.environ['PURLIN_REL_PATH']
project_root = os.environ['PURLIN_PROJECT_ROOT']
plugin_root = os.environ['PURLIN_PLUGIN_ROOT']

# --- Classify file ---
sys.path.insert(0, os.path.join(plugin_root, 'scripts', 'mcp'))
os.environ.setdefault('PURLIN_PROJECT_ROOT', project_root)
try:
    from config_engine import classify_file
    classification = classify_file(rel_path)
except Exception:
    sys.exit(0)

# Skip INVARIANT (can't be written) and UNKNOWN (blocked by write-guard)
if classification in ('INVARIANT', 'UNKNOWN'):
    sys.exit(0)

# --- Skip non-project-content files ---
_SKIP = re.compile(
    r'^('
    r'README|LICENSE|CHANGELOG|CLAUDE\.md$|'
    r'\.gitignore$|\.gitattributes$|'
    r'package-lock\.json$|yarn\.lock$|Cargo\.lock$|go\.sum$|poetry\.lock$'
    r')',
    re.IGNORECASE
)
if _SKIP.search(rel_path):
    sys.exit(0)

# --- Map file to feature stem ---
stem = None
is_impl = False
is_qa = False

# features/<category>/<stem>.impl.md
m = re.match(r'features/[^/]+/([^/]+)\.impl\.md$', rel_path)
if m:
    stem = m.group(1)
    is_impl = True

# features/<category>/<stem>.discoveries.md
if not stem:
    m = re.match(r'features/[^/]+/([^/]+)\.discoveries\.md$', rel_path)
    if m:
        stem = m.group(1)
        is_qa = True

# features/<category>/<stem>.md (not impl, not discoveries)
if not stem:
    m = re.match(r'features/[^/]+/([^/]+)\.md$', rel_path)
    if m and not rel_path.endswith('.discoveries.md'):
        stem = m.group(1)

# tests/<stem>/ directory
if not stem:
    m = re.match(r'tests/([^/]+)/', rel_path)
    if m:
        stem = m.group(1)

# --- Load sync state ---
state_file = os.path.join(project_root, '.purlin', 'runtime', 'sync_state.json')

def load_state():
    if os.path.isfile(state_file):
        try:
            with open(state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {'features': {}, 'unclassified_writes': []}

def save_state(state):
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    tmp = state_file + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, state_file)

state = load_state()
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

if stem:
    feat = state['features'].setdefault(stem, {
        'code_files': [],
        'test_files': [],
        'spec_changed': False,
        'impl_changed': False,
    })

    if is_impl:
        feat['impl_changed'] = True
    elif is_qa or classification == 'QA':
        feat.setdefault('qa_changed', False)
        feat['qa_changed'] = True
    elif classification == 'SPEC':
        feat['spec_changed'] = True
        if 'first_spec_change' not in feat:
            feat['first_spec_change'] = now
    elif classification == 'CODE':
        # Test files vs code files
        if rel_path.startswith('tests/'):
            if rel_path not in feat['test_files']:
                feat['test_files'].append(rel_path)
        else:
            if rel_path not in feat['code_files']:
                feat['code_files'].append(rel_path)
        if 'first_code_change' not in feat:
            feat['first_code_change'] = now
elif classification in ('CODE', 'SPEC'):
    # Unclassified — can't map to a feature
    uw = state.setdefault('unclassified_writes', [])
    if rel_path not in uw and len(uw) < 100:
        uw.append(rel_path)

save_state(state)
" 2>/dev/null

exit 0
