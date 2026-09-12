#!/usr/bin/env bash
# Purlin proof harness for SQL tests.
#
# Runs SQL test files against sqlite3, parses proof markers from comments,
# and emits write-scoped proof JSON files.
#
# Marker syntax in SQL files:
#   -- @purlin feature_name PROOF-1 RULE-1 unit
#   -- Test: description of what this tests
#   SELECT CASE WHEN (SELECT count(*) FROM users WHERE email='test@x.com') = 1
#          THEN 'PASS' ELSE 'FAIL' END;
#
#   -- @purlin feature_name PROOF-2 RULE-2 unit on(windows-2022)
#   -- @purlin feature_name PROOF-3 RULE-3 on(windows, macos)      (tier omitted: unit)
#
# Each test block ends at the next @purlin marker or EOF.
# The block must produce a result starting with 'PASS' or 'FAIL'.
#
# A marker that declares on(...) writes its entry to
# <feature>.proofs-<tier>@<host>.json, where <host> is PURLIN_PLATFORM when set
# and otherwise the detected OS family (windows, macos, linux); every entry in
# that file carries an eighth field, "platform", equal to <host>. A marker with
# no on(...) writes the agnostic <feature>.proofs-<tier>.json with the seven
# standard fields, whatever PURLIN_PLATFORM says. The harness never evaluates
# version constraints.
#
# Usage:
#   bash scripts/proof/sql_purlin.sh <test_file.sql> [database_file]
#
# If database_file is omitted, uses :memory:
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <test_file.sql> [database_file]" >&2
    exit 2
fi

TEST_FILE="$1"
DB_FILE="${2:-:memory:}"

if [[ ! -f "$TEST_FILE" ]]; then
    echo "File not found: $TEST_FILE" >&2
    exit 2
fi

# Parse proof markers and extract test blocks. The paths travel through the
# environment rather than being spliced into the Python source, so a path
# holding a quote or a backslash is neither a syntax error nor an escape.
PURLIN_SQL_TEST_FILE="$TEST_FILE" PURLIN_SQL_DB_FILE="$DB_FILE" python3 -c "
import json, os, platform, re, subprocess, sys, glob

test_file = os.environ['PURLIN_SQL_TEST_FILE']
db_file = os.environ['PURLIN_SQL_DB_FILE']
# Recorded with '/' separators on every OS (proof_common RULE-15); the path as
# given is still used to read the file.
recorded_file = test_file.replace(os.sep, '/').replace(chr(92), '/')

_FAMILIES = {'Windows': 'windows', 'Darwin': 'macos', 'Linux': 'linux'}


def _host_platform():
    # PURLIN_PLATFORM when set, else the OS family. The only host lookup here.
    env = os.environ.get('PURLIN_PLATFORM', '').strip()
    if env:
        return env
    system = platform.system()
    return _FAMILIES.get(system, system.lower())


with open(test_file) as f:
    content = f.read()

# Find all proof markers
marker_re = re.compile(r'^-- @purlin\s+(\w+)\s+(PROOF-\d+)\s+(RULE-\d+)(?:[ \t]+(?!on\()(\w+))?(?:[ \t]+on\(([^)]*)\))?', re.MULTILINE)
markers = list(marker_re.finditer(content))

if not markers:
    print(json.dumps({'proofs': []}, indent=2))
    sys.exit(0)

# Extract test blocks between markers
blocks = []
for i, m in enumerate(markers):
    start = m.end()
    end = markers[i+1].start() if i+1 < len(markers) else len(content)
    sql_block = content[start:end].strip()

    # Extract test name from -- Test: comment
    test_name_match = re.search(r'^-- Test:\s*(.+)', sql_block, re.MULTILINE)
    test_name = test_name_match.group(1).strip() if test_name_match else m.group(2)

    # Remove comment lines for execution
    sql_lines = [l for l in sql_block.split('\n') if not l.strip().startswith('--')]
    sql_exec = '\n'.join(sql_lines).strip()

    declared = [p.strip() for p in (m.group(5) or '').split(',') if p.strip()]
    blocks.append({
        'feature': m.group(1),
        'id': m.group(2),
        'rule': m.group(3),
        'tier': m.group(4) or 'unit',
        'platform': _host_platform() if declared else None,
        'test_name': test_name,
        'sql': sql_exec,
    })

# Run each block and collect results
proofs_by_key = {}
for block in blocks:
    try:
        result = subprocess.run(
            ['sqlite3', db_file],
            input=block['sql'],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip()
        passed = output.upper().startswith('PASS')
    except Exception as e:
        passed = False

    key = (block['feature'], block['tier'], block['platform'])
    entry = {
        'feature': block['feature'],
        'id': block['id'],
        'rule': block['rule'],
        'test_file': recorded_file,
        'test_name': block['test_name'],
        'status': 'pass' if passed else 'fail',
        'tier': block['tier'],
    }
    if block['platform'] is not None:
        entry['platform'] = block['platform']
    proofs_by_key.setdefault(key, []).append(entry)

# Build spec dir mapping
spec_dirs = {}
for spec in glob.glob('specs/**/*.md', recursive=True):
    stem = os.path.splitext(os.path.basename(spec))[0]
    spec_dirs[stem] = os.path.dirname(spec)

# Write proof files (write-scoped overwrite)
for (feature, tier, plat), new_entries in proofs_by_key.items():
    suffix = f'{tier}@{plat}' if plat is not None else tier
    spec_dir = spec_dirs.get(feature)
    if spec_dir is None:
        print(f'WARNING: No spec found for feature \"{feature}\"', file=sys.stderr)
        spec_dir = 'specs'
    path = os.path.join(spec_dir, f'{feature}.proofs-{suffix}.json')
    existing = []
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f).get('proofs', [])
    # Write-scoped overwrite keyed by (feature, tier, platform, test_file), per
    # proof_common RULE-4 (the file carries tier and platform, so within it the
    # key is (feature, test_file)), plus orphan reaping of vanished test files (RULE-11).
    run_files = {e['test_file'] for e in new_entries}
    kept = [
        e for e in existing
        if e.get('feature') != feature
        or (e.get('test_file') not in run_files and os.path.exists(e.get('test_file') or ''))
    ]
    payload = {'tier': tier}
    if plat is not None:
        payload['platform'] = plat
    payload['proofs'] = kept + new_entries
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    os.replace(tmp_path, path)

# Emit to stdout
all_proofs = []
for entries in proofs_by_key.values():
    all_proofs.extend(entries)
print(json.dumps({'proofs': all_proofs}, indent=2))
"
