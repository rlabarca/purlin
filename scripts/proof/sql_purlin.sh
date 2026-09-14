#!/usr/bin/env bash
# Purlin proof harness for SQL tests.
#
# Runs SQL test files against the project's SQL engine, parses proof markers
# from comments, and writes what it observed to
# .purlin/runtime/proofs/<feature>.<tier>.json. Proof files are runtime: they
# are gitignored, so two runs on two branches never conflict and nothing about
# a run is committed.
#
# Marker syntax in SQL files:
#   -- @purlin feature_name PROOF-1 RULE-1 unit
#   -- Test: description of what this tests
#   SELECT CASE WHEN (SELECT count(*) FROM users WHERE email='test@x.com') = 1
#          THEN 'PASS' ELSE 'FAIL' END;
#
#   -- @purlin feature_name PROOF-2 RULE-2        (tier omitted: unit)
#
# Each test block ends at the next @purlin marker or EOF. The block must
# produce a result starting with 'PASS' or 'FAIL'.
#
# The engine is the project's sql_engine setting, read from
# .purlin/config.json and defaulting to sqlite3. PURLIN_SQL_ENGINE overrides
# it for one run.
#
# The operating system a proof must be proved on is a property of the spec,
# not of the test: write @env(windows), @env(macos) or @env(linux) on the
# proof line. The retired on(...) marker keyword is refused rather than
# ignored, so a file carrying one fails with a line saying what to write
# instead.
#
# The project root is the nearest ancestor of the working directory holding
# specs/ or .purlin/, and the recorded test_file is relative to it with /
# separators on every operating system.
#
# The run exits non-zero when it saw markers and wrote no entry at all, so
# evidence that went missing fails the run rather than leaving a stale proof
# file behind.
#
# Usage:
#   bash scripts/proof/sql_purlin.sh <test_file.sql> [database_file]
#
# If database_file is omitted, uses :memory:
set -euo pipefail

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
import json, os, re, subprocess, sys

test_file = os.environ['PURLIN_SQL_TEST_FILE']
db_file = os.environ['PURLIN_SQL_DB_FILE']


# The project root. Everything the harness addresses project-relative is
# rooted here and not at the working directory, so a run started from a
# subdirectory writes into the project's own tree instead of making a second
# one beside itself.


def _find_root(start):
    '''Nearest ancestor of the directory start, start itself included, holding
    a specs/ or a .purlin/ directory; None when none does.'''
    d = os.path.realpath(start)
    while True:
        if os.path.isdir(os.path.join(d, 'specs')) or os.path.isdir(os.path.join(d, '.purlin')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def _project_root(start=None):
    '''The project root of start (the working directory by default).'''
    start = os.path.realpath(start or os.getcwd())
    return _find_root(start) or start


def _relativize(base_root, raw_path):
    '''raw_path recorded relative to base_root with / separators.

    The argv path is resolved against the working directory first, so an
    absolute invocation and a relative one naming the same file record the
    same value: under the merge key a difference does not collapse, it
    accumulates as a second entry for one proof. A file outside base_root is
    made relative to the nearest project root above the file itself, and left
    absolute when there is none, rather than rewritten with ../ segments.
    '''
    if not raw_path:
        return raw_path
    abs_path = os.path.realpath(raw_path)
    for base in (base_root, _find_root(os.path.dirname(abs_path))):
        if not base:
            continue
        try:
            rel = os.path.relpath(abs_path, base)
        except ValueError:
            continue
        if rel != os.pardir and not rel.startswith(os.pardir + os.sep):
            return rel.replace(os.sep, '/').replace(chr(92), '/')
    return abs_path.replace(os.sep, '/').replace(chr(92), '/')


def _sql_engine(root):
    '''The command that runs a SQL script: PURLIN_SQL_ENGINE, else the
    project's sql_engine setting, else sqlite3.'''
    env = os.environ.get('PURLIN_SQL_ENGINE', '').strip()
    if env:
        return env
    try:
        with open(os.path.join(root, '.purlin', 'config.json'),
                  encoding='utf-8') as f:
            value = json.load(f).get('sql_engine')
    except (ValueError, OSError):
        value = None
    return (str(value).strip() if value else '') or 'sqlite3'


root = _project_root()
# Recorded relative to the project root, with '/' separators on every OS; the
# path as given is still used to read the file.
recorded_file = _relativize(root, test_file)
engine = _sql_engine(root)

with open(test_file, encoding='utf-8') as f:
    content = f.read()

# Find all proof markers. A trailing on(...) is the retired keyword naming
# an operating system; it is captured so the run can refuse it by name.
marker_re = re.compile(r'^-- @purlin\s+(\w+)\s+(PROOF-\d+)\s+(RULE-\d+)(?:[ \t]+(?!on\()(\w+))?(?:[ \t]+on\(([^)]*)\))?', re.MULTILINE)
markers = list(marker_re.finditer(content))

if not markers:
    print(json.dumps({'proofs': []}, indent=2))
    sys.exit(0)

retired = ['%s %s' % (m.group(1), m.group(2)) for m in markers if m.group(5)]
if retired:
    print('purlin: the on(...) marker keyword is not read any more; write '
          '@env(windows), @env(macos) or @env(linux) on the proof line in the '
          'spec instead: %s' % ', '.join(retired), file=sys.stderr)
    sys.exit(1)

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
            [engine, db_file],
            input=block['sql'],
            capture_output=True, text=True, timeout=10
        )
        output = result.stdout.strip()
        passed = output.upper().startswith('PASS')
    except Exception:
        passed = False

    proofs_by_key.setdefault((block['feature'], block['tier']), []).append({
        'feature': block['feature'],
        'id': block['id'],
        'rule': block['rule'],
        'test_file': recorded_file,
        'test_name': block['test_name'],
        'status': 'pass' if passed else 'fail',
        'tier': block['tier'],
    })

if not proofs_by_key:
    print('purlin: markers were seen and no proof entry was written for %s; '
          'the proof files on disk describe an earlier run.'
          % ', '.join(sorted({b['feature'] for b in blocks})), file=sys.stderr)
    sys.exit(1)

directory = os.path.join(root, '.purlin', 'runtime', 'proofs')
os.makedirs(directory, exist_ok=True)

for (feature, tier), new_entries in proofs_by_key.items():
    path = os.path.join(directory, '%s.%s.json' % (feature, tier))
    existing = []
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                existing = json.load(f).get('proofs', [])
        except (ValueError, OSError):
            existing = []
    # Write-scoped overwrite keyed by (feature, tier, test_file); the file
    # carries the tier, so within it the key is (feature, test_file). Entries
    # whose test file no longer exists are reaped. Each recorded path is
    # resolved from the project root, the same root it was relativized
    # against. A SQL block that is never reached emits no marker, so the
    # harness has no skip signal.
    run_files = {e['test_file'] for e in new_entries}
    kept = [
        e for e in existing
        if e.get('feature') != feature
        or (e.get('test_file') not in run_files
            and bool(e.get('test_file'))
            and os.path.exists(os.path.join(root, e.get('test_file') or '')))
    ]
    payload = {'tier': tier}
    # Sorted by (id, test_file, test_name), ordinal, after the merge, so the
    # collection order never reaches the file.
    payload['proofs'] = sorted(
        kept + new_entries,
        key=lambda e: (e.get('id') or '', e.get('test_file') or '',
                       e.get('test_name') or ''))
    # Atomic write: the temp name carries this process id, so two plugins
    # writing the same file concurrently never share a temp path.
    tmp_path = '%s.%d.tmp' % (path, os.getpid())
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    os.replace(tmp_path, path)

# Emit to stdout
all_proofs = []
for entries in proofs_by_key.values():
    all_proofs.extend(entries)
print(json.dumps({'proofs': all_proofs}, indent=2))
"
