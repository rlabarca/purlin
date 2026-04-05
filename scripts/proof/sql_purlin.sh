#!/usr/bin/env bash
# Purlin proof harness for SQL tests.
#
# Runs SQL test files against sqlite3, parses proof markers from comments,
# and emits feature-scoped proof JSON files.
#
# Marker syntax in SQL files:
#   -- @purlin feature_name PROOF-1 RULE-1 unit
#   -- Test: description of what this tests
#   SELECT CASE WHEN (SELECT count(*) FROM users WHERE email='test@x.com') = 1
#          THEN 'PASS' ELSE 'FAIL' END;
#
# Each test block ends at the next @purlin marker or EOF.
# The block must produce a result starting with 'PASS' or 'FAIL'.
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

# Parse proof markers and extract test blocks
python3 -c "
import json, os, re, subprocess, sys, glob

test_file = '$TEST_FILE'
db_file = '$DB_FILE'

with open(test_file) as f:
    content = f.read()

# Find all proof markers
marker_re = re.compile(r'^-- @purlin\s+(\w+)\s+(PROOF-\d+)\s+(RULE-\d+)(?:\s+(\w+))?', re.MULTILINE)
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

    blocks.append({
        'feature': m.group(1),
        'id': m.group(2),
        'rule': m.group(3),
        'tier': m.group(4) or 'unit',
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

    key = f\"{block['feature']}:{block['tier']}\"
    proofs_by_key.setdefault(key, []).append({
        'feature': block['feature'],
        'id': block['id'],
        'rule': block['rule'],
        'test_file': test_file,
        'test_name': block['test_name'],
        'status': 'pass' if passed else 'fail',
        'tier': block['tier'],
    })

# Build spec dir mapping
spec_dirs = {}
for spec in glob.glob('specs/**/*.md', recursive=True):
    stem = os.path.splitext(os.path.basename(spec))[0]
    spec_dirs[stem] = os.path.dirname(spec)

# Write proof files (feature-scoped overwrite)
for key, new_entries in proofs_by_key.items():
    feature, tier = key.split(':')
    spec_dir = spec_dirs.get(feature)
    if spec_dir is None:
        print(f'WARNING: No spec found for feature \"{feature}\"', file=sys.stderr)
        spec_dir = 'specs'
    path = os.path.join(spec_dir, f'{feature}.proofs-{tier}.json')
    existing = []
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f).get('proofs', [])
    kept = [e for e in existing if e.get('feature') != feature]
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump({'tier': tier, 'proofs': kept + new_entries}, f, indent=2)
        f.write('\n')
    os.replace(tmp_path, path)

# Emit to stdout
all_proofs = []
for entries in proofs_by_key.values():
    all_proofs.extend(entries)
print(json.dumps({'proofs': all_proofs}, indent=2))
"
