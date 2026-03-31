#!/bin/bash
# sync-ledger-update.sh — Updates .purlin/sync_ledger.json on git commit.
# Intended to be called from skill commit steps or as a pre-commit hook.
# Maps staged files to features via path, updates per-feature sync status.
#
# Usage:
#   sync-ledger-update.sh              # Normal: reads staged files, uses 'pending' SHA
#   sync-ledger-update.sh --sha <hash> # Backfill: updates 'pending' SHAs with real commit hash
#
# Environment:
#   PURLIN_COMMIT_MSG  — optional commit message for scope-based stem fallback
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

# --- Normal Mode: map staged files to features and update ledger ---
# File type is determined from path alone — no external classifier needed.
# features/ = spec or impl; everything else = code.

export PURLIN_PROJECT_ROOT="$PROJECT_ROOT"
export PURLIN_LEDGER_FILE="$LEDGER_FILE"
export PURLIN_COMMIT_MSG="${PURLIN_COMMIT_MSG:-}"

git -C "$PROJECT_ROOT" diff --cached --name-only 2>/dev/null | python3 -c "
import json, os, sys, re, glob as _glob
from datetime import datetime, timezone

project_root = os.environ.get('PURLIN_PROJECT_ROOT', '')
ledger_file = os.environ.get('PURLIN_LEDGER_FILE', '')
commit_msg = os.environ.get('PURLIN_COMMIT_MSG', '')

staged = [line.strip() for line in sys.stdin if line.strip()]
if not staged:
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

# --- Extract scope from commit message (fallback for unmapped files) ---
commit_scope_stem = None
if commit_msg:
    scope_m = re.match(r'\w+\(([^)]+)\):', commit_msg)
    if scope_m:
        candidate = scope_m.group(1).replace('-', '_')
        if candidate in known_stems:
            commit_scope_stem = candidate

# --- Map staged files to features ---
# Type detection is path-based:
#   features/ -> spec or impl
#   everything else -> code
feature_changes = {}  # stem -> {'code': bool, 'spec': bool, 'impl': bool}

for path in staged:
    stem = None
    is_spec = False
    is_impl = False

    # Skip system directories under features/
    if re.match(r'features/(_tombstones|_digests|_design|_invariants)/', path):
        continue

    # features/<category>/<stem>.impl.md -> impl
    m = re.match(r'features/[^/]+/([^/]+)\.impl\.md$', path)
    if m:
        stem = m.group(1)
        is_impl = True

    # features/<category>/<stem>.md (not impl, not discoveries) -> spec
    if not stem:
        m = re.match(r'features/[^/]+/([^/]+)\.md$', path)
        if m and not path.endswith('.discoveries.md'):
            stem = m.group(1)
            is_spec = True

    # tests/<stem>/
    if not stem:
        m = re.match(r'tests/([^/]+)/', path)
        if m:
            stem = m.group(1)

    # skills/<name>/ -> purlin_<name> (if feature exists)
    if not stem:
        m = re.match(r'skills/([^/]+)/', path)
        if m:
            candidate = 'purlin_' + m.group(1).replace('-', '_')
            if candidate in known_stems:
                stem = candidate

    # Fallback: commit scope for anything not under features/
    if not stem and not path.startswith('features/') and commit_scope_stem:
        stem = commit_scope_stem

    if not stem:
        continue

    changes = feature_changes.setdefault(stem, {'code': False, 'spec': False, 'impl': False})
    if is_impl:
        changes['impl'] = True
    elif is_spec:
        changes['spec'] = True
    else:
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
