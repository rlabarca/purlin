#!/bin/bash
# sync-tracker.sh — FileChanged hook.
# Tracks all file writes in sync_state.json, grouped by feature.
# File type is determined from path alone — no external classifier needed.
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

PURLIN_PROJECT_ROOT="$PROJECT_ROOT" PURLIN_REL_PATH="$REL_PATH" python3 -c "
import json, os, sys, re, glob as _glob
from datetime import datetime, timezone

rel_path = os.environ['PURLIN_REL_PATH']
project_root = os.environ['PURLIN_PROJECT_ROOT']

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

# --- Discover known feature stems from features/ directory ---
known_stems = set()
for f in _glob.glob(os.path.join(project_root, 'features', '*', '*.md')):
    base = os.path.basename(f)
    if base.startswith('_'):
        continue
    for suffix in ('.impl.md', '.discoveries.md'):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
            break
    else:
        if base.endswith('.md'):
            base = base[:-3]
    if base:
        known_stems.add(base)

# --- Map file to feature stem ---
# Type detection is path-based:
#   features/ -> spec, impl, or qa (discoveries)
#   everything else -> code
stem = None
is_spec = False
is_impl = False
is_qa = False

# Skip system directories under features/
if re.match(r'features/(_tombstones|_digests|_design|_invariants)/', rel_path):
    sys.exit(0)

# features/<category>/<stem>.impl.md -> impl
m = re.match(r'features/[^/]+/([^/]+)\.impl\.md$', rel_path)
if m:
    stem = m.group(1)
    is_impl = True

# features/<category>/<stem>.discoveries.md -> qa
if not stem:
    m = re.match(r'features/[^/]+/([^/]+)\.discoveries\.md$', rel_path)
    if m:
        stem = m.group(1)
        is_qa = True

# features/<category>/<stem>.md (not impl, not discoveries) -> spec
if not stem:
    m = re.match(r'features/[^/]+/([^/]+)\.md$', rel_path)
    if m and not rel_path.endswith('.discoveries.md'):
        stem = m.group(1)
        is_spec = True

# tests/<stem>/ directory -> code
if not stem:
    m = re.match(r'tests/([^/]+)/', rel_path)
    if m:
        stem = m.group(1)

# skills/<name>/ -> purlin_<name> (if feature exists)
if not stem:
    m = re.match(r'skills/([^/]+)/', rel_path)
    if m:
        candidate = 'purlin_' + m.group(1).replace('-', '_')
        if candidate in known_stems:
            stem = candidate

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
    elif is_qa:
        feat.setdefault('qa_changed', False)
        feat['qa_changed'] = True
    elif is_spec:
        feat['spec_changed'] = True
        if 'first_spec_change' not in feat:
            feat['first_spec_change'] = now
    else:
        # Everything outside features/ is code
        if rel_path.startswith('tests/'):
            if rel_path not in feat['test_files']:
                feat['test_files'].append(rel_path)
        else:
            if rel_path not in feat['code_files']:
                feat['code_files'].append(rel_path)
        if 'first_code_change' not in feat:
            feat['first_code_change'] = now
else:
    # Can't map to a feature — track as unclassified
    uw = state.setdefault('unclassified_writes', [])
    if rel_path not in uw and len(uw) < 100:
        uw.append(rel_path)

save_state(state)
" 2>/dev/null

exit 0
