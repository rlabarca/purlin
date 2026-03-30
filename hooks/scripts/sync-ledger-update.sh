#!/bin/bash
# sync-ledger-update.sh — Updates .purlin/sync_ledger.json on git commit.
# Intended to be called from skill commit steps or as a pre-commit hook.
# Classifies staged files, maps to features, updates per-feature sync status.
#
# Usage:
#   sync-ledger-update.sh              # Normal: reads staged files, uses 'pending' SHA
#   sync-ledger-update.sh --sha <hash> # Backfill: updates 'pending' SHAs with real commit hash
#
# Exit codes:
#   0 = always (informational, never blocks commits)

set -eo pipefail

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
LEDGER_FILE="$PROJECT_ROOT/.purlin/sync_ledger.json"

# --- SHA Backfill Mode ---
if [ "${1:-}" = "--sha" ] && [ -n "${2:-}" ]; then
    BACKFILL_SHA="$2"
    if [ ! -f "$LEDGER_FILE" ]; then
        exit 0
    fi
    # Replace all 'pending' SHAs with the real commit hash
    export PURLIN_LEDGER_FILE="$LEDGER_FILE"
    export PURLIN_BACKFILL_SHA="$BACKFILL_SHA"
    python3 -c "
import json, os, sys

ledger_file = os.environ.get('PURLIN_LEDGER_FILE', '')
if not ledger_file:
    sys.exit(0)
sha = os.environ.get('PURLIN_BACKFILL_SHA', '')
if not sha:
    sys.exit(0)

try:
    with open(ledger_file) as f:
        ledger = json.load(f)
except (IOError, json.JSONDecodeError):
    sys.exit(0)

changed = False
for stem, entry in ledger.items():
    for key in ('last_code_commit', 'last_spec_commit', 'last_impl_commit'):
        if entry.get(key) == 'pending':
            entry[key] = sha
            changed = True

if changed:
    with open(ledger_file, 'w') as f:
        json.dump(ledger, f, indent=2)
        f.write('\n')
    print(f'sync: backfilled pending SHAs with {sha[:8]}', file=sys.stderr)
" 2>/dev/null
    exit 0
fi

# --- Normal Mode: classify staged files and update ledger ---

# Get staged files — pipe to Python via stdin for robustness
# (avoids shell quoting issues with unusual filenames)
export PURLIN_PROJECT_ROOT="$PROJECT_ROOT"
export PURLIN_PLUGIN_ROOT="$PLUGIN_ROOT"
export PURLIN_LEDGER_FILE="$LEDGER_FILE"

git -C "$PROJECT_ROOT" diff --cached --name-only 2>/dev/null | python3 -c "
import json, os, sys, re
from datetime import datetime, timezone

project_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
plugin_root = os.environ.get('PURLIN_PLUGIN_ROOT', '')
ledger_file = os.environ.get('PURLIN_LEDGER_FILE', '')

sys.path.insert(0, os.path.join(plugin_root, 'scripts', 'mcp'))
os.environ.setdefault('PURLIN_PROJECT_ROOT', project_root)

try:
    from config_engine import classify_file
except Exception:
    sys.exit(0)

staged = [line.strip() for line in sys.stdin if line.strip()]
if not staged:
    sys.exit(0)

# --- Map staged files to features ---
feature_changes = {}  # stem -> {'code': bool, 'spec': bool, 'impl': bool}

for path in staged:
    classification = classify_file(path)
    stem = None
    is_impl = False

    # features/<category>/<stem>.impl.md
    m = re.match(r'features/[^/]+/([^/]+)\.impl\.md$', path)
    if m:
        stem = m.group(1)
        is_impl = True

    # features/<category>/<stem>.md (not impl, not discoveries)
    if not stem:
        m = re.match(r'features/[^/]+/([^/]+)\.md$', path)
        if m and not path.endswith('.discoveries.md'):
            stem = m.group(1)

    # tests/<stem>/
    if not stem:
        m = re.match(r'tests/([^/]+)/', path)
        if m:
            stem = m.group(1)

    if not stem:
        continue

    changes = feature_changes.setdefault(stem, {'code': False, 'spec': False, 'impl': False})
    if is_impl:
        changes['impl'] = True
    elif classification == 'SPEC':
        changes['spec'] = True
    elif classification in ('CODE', 'QA'):
        changes['code'] = True

if not feature_changes:
    sys.exit(0)

# --- Load existing ledger ---
ledger = {}
if os.path.isfile(ledger_file):
    try:
        with open(ledger_file) as f:
            ledger = json.load(f)
    except (json.JSONDecodeError, IOError):
        pass

now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
# Use placeholder for commit SHA — backfilled by caller via --sha
commit_sha = 'pending'

# --- Update ledger per feature ---
for stem, changes in feature_changes.items():
    entry = ledger.setdefault(stem, {
        'last_code_commit': None, 'last_code_date': None,
        'last_spec_commit': None, 'last_spec_date': None,
        'last_impl_commit': None, 'last_impl_date': None,
        'sync_status': 'unknown',
    })

    if changes['code']:
        entry['last_code_commit'] = commit_sha
        entry['last_code_date'] = now
    if changes['spec']:
        entry['last_spec_commit'] = commit_sha
        entry['last_spec_date'] = now
    if changes['impl']:
        entry['last_impl_commit'] = commit_sha
        entry['last_impl_date'] = now

    # Recompute sync status
    if changes['code'] and changes['spec']:
        entry['sync_status'] = 'synced'
    elif changes['code'] and changes['impl']:
        entry['sync_status'] = 'synced'
    elif changes['code'] and not changes['spec'] and not changes['impl']:
        entry['sync_status'] = 'code_ahead'
    elif changes['spec'] and not changes['code']:
        entry['sync_status'] = 'spec_ahead'
    elif changes['impl'] and not changes['code'] and not changes['spec']:
        # Impl-only update resolves existing debt
        if entry.get('sync_status') == 'code_ahead':
            entry['sync_status'] = 'synced'
    # else: keep existing status

    # Print summary to stderr (visible in commit output)
    print(f'sync: {stem}: {entry[\"sync_status\"]}', file=sys.stderr)

# --- Write updated ledger ---
os.makedirs(os.path.dirname(ledger_file), exist_ok=True)
with open(ledger_file, 'w') as f:
    json.dump(ledger, f, indent=2)
    f.write('\n')

# Stage the updated ledger so it's included in the commit
import subprocess
subprocess.run(['git', '-C', project_root, 'add', ledger_file],
               capture_output=True, timeout=10)
" 2>/dev/null

exit 0
