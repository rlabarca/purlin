#!/usr/bin/env bash
# Purlin proof harness for shell tests.
#
# Source this file and use purlin_proof() to register test results:
#   source .purlin/plugins/purlin-proof.sh  # or scripts/proof/shell_purlin.sh
#   purlin_proof "my_feature" "PROOF-1" "RULE-1" pass "test_description"
#   purlin_proof "my_feature" "PROOF-2" "RULE-2" fail "test_description"
#   purlin_proof_finish  # writes proof files
#
# Tier comes from PURLIN_PROOF_TIER (default "unit"). Platforms a proof must be
# proved on come from PURLIN_PROOF_PLATFORMS, a comma-separated list of ids, read
# at each purlin_proof call:
#   PURLIN_PROOF_PLATFORMS="windows-2022" purlin_proof "my_feature" "PROOF-3" "RULE-3" pass "name"
# An entry recorded with platforms declared is written to
# <feature>.proofs-<tier>@<host>.json, where <host> is PURLIN_PLATFORM when set
# and otherwise the detected OS family (windows, macos, linux); every entry in
# that file carries an eighth field, "platform", equal to <host>. An entry with
# no platforms declared goes to the agnostic <feature>.proofs-<tier>.json with
# the seven standard fields, whatever PURLIN_PLATFORM says. The harness never
# evaluates version constraints.
#
# purlin_proof_finish also writes or merges the project's run marker
# .purlin/runtime/test_run.json (proof_common RULE-19), so a receipt issued in
# a consumer project can record which run its evidence came from.
set -euo pipefail

_PURLIN_PROOFS=""

purlin_proof() {
  local feature="$1" proof_id="$2" rule_id="$3" status="$4" test_name="${5:-}"
  local tier="${PURLIN_PROOF_TIER:-unit}"
  local platforms="${PURLIN_PROOF_PLATFORMS:-}"
  local test_file="${BASH_SOURCE[1]:-unknown}"

  # Absolutize here, at call time, while the cwd is still the caller's. The
  # value is relativized in purlin_proof_finish. Doing it in this order is what
  # makes `bash dev/x.sh` and `bash /abs/dev/x.sh` record the SAME test_file:
  # the raw BASH_SOURCE differs between those two, the absolute path does not.
  # Under the (feature, tier, test_file) merge key a difference here would not
  # collapse, it would accumulate as two entries for one proof (RULE-5).
  if [[ "$test_file" != "unknown" && "$test_file" != /* ]]; then
    test_file="$PWD/$test_file"
  fi

  _PURLIN_PROOFS="${_PURLIN_PROOFS}${feature}|${proof_id}|${rule_id}|${status}|${test_name}|${test_file}|${tier}|${platforms}
"
}

purlin_proof_finish() {
  [[ -z "$_PURLIN_PROOFS" ]] && return 0

  python3 -c "
import datetime, glob, json, os, platform, subprocess, sys, time


_FAMILIES = {'Windows': 'windows', 'Darwin': 'macos', 'Linux': 'linux'}


def _host_platform():
    # PURLIN_PLATFORM when set, else the OS family. The only host lookup here.
    env = os.environ.get('PURLIN_PLATFORM', '').strip()
    if env:
        return env
    system = platform.system()
    return _FAMILIES.get(system, system.lower())


def _project_root_of(path):
    '''Nearest ancestor of path that looks like a project root.'''
    d = os.path.dirname(path)
    while True:
        if os.path.isdir(os.path.join(d, '.git')) or os.path.isdir(os.path.join(d, 'specs')):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


# ── The run marker (proof_common RULE-19) ───────────────────────────────────
# Written or merged at the same moment the proof files are written, so a
# consumer receipt can record which run its evidence came from.

_RUN_MARKER_REL = os.path.join('.purlin', 'runtime', 'test_run.json')


def _run_marker_commit(root):
    '''HEAD in root, or None when root is not inside a git work tree.'''
    try:
        out = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root,
                             capture_output=True, text=True)
    except OSError:
        return None
    return out.stdout.strip() or None


def _write_run_marker(root, sweep, test_files, passed, failed, skipped):
    '''Write or merge <root>/.purlin/runtime/test_run.json (RULE-19).

    Nothing is written when <root>/.purlin is absent: that is not a Purlin
    project. An existing marker whose commit equals this run's commit is
    merged into: test_files unioned, the three counts summed, this run
    appended to runs, ok and-ed, and every other top-level field carried
    through untouched. A marker naming another commit is replaced. The file is
    written to a temp file in the same directory and renamed over the target,
    so a concurrent reader sees one whole marker or the other; a read that
    lands on unparsable JSON is retried before this run starts a fresh marker.
    '''
    if not os.path.isdir(os.path.join(root, '.purlin')):
        return None
    path = os.path.join(root, _RUN_MARKER_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    commit = _run_marker_commit(root)
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    files = sorted({str(f).replace(os.sep, '/').replace(chr(92), '/')
                    for f in test_files if f})
    marker = {}
    for _attempt in range(3):
        try:
            with open(path) as f:
                existing = json.load(f)
            if isinstance(existing, dict) and existing.get('commit') == commit:
                marker = existing
            break
        except FileNotFoundError:
            break
        except (ValueError, OSError):
            # A concurrent writer is mid-replace: read again before giving up.
            time.sleep(0.05)
    runs = list(marker.get('runs') or [])
    runs.append({'plugin': sweep, 'at': at, 'test_files': files,
                 'passed': passed, 'failed': failed, 'skipped': skipped})
    marker.update({
        'at': at,
        'commit': commit,
        'sweep': sweep,
        'test_files': sorted(set(marker.get('test_files') or []) | set(files)),
        'passed': int(marker.get('passed') or 0) + passed,
        'failed': int(marker.get('failed') or 0) + failed,
        'skipped': int(marker.get('skipped') or 0) + skipped,
        'ok': bool(marker.get('ok', True)) and failed == 0,
        'runs': runs,
    })
    tmp = '%s.%d.tmp' % (path, os.getpid())
    with open(tmp, 'w') as f:
        json.dump(marker, f, indent=2)
        f.write('\n')
    os.replace(tmp, path)
    return marker


# Build spec dir mapping
spec_dirs = {}
for spec in glob.glob('specs/**/*.md', recursive=True):
    stem = os.path.splitext(os.path.basename(spec))[0]
    spec_dirs[stem] = os.path.dirname(spec)

# Parse entries
entries = {}
for line in sys.stdin.read().strip().split('\n'):
    if not line:
        continue
    parts = line.split('|')
    if len(parts) < 7:
        continue
    feature, proof_id, rule_id, status, test_name, test_file, tier = parts[:7]
    declared = [p.strip() for p in (parts[7] if len(parts) > 7 else '').split(',') if p.strip()]
    plat = _host_platform() if declared else None
    # Record the test file project-relative with POSIX separators, so a
    # committed proof file carries neither one machine's home directory nor a
    # value that depends on how the script happened to be invoked. Mirrors the
    # pytest plugin's item.fspath.relto(config.rootdir).
    #
    # Two candidate roots, in order: the project being written to (cwd), then
    # the project the test file itself lives in. The second matters when a
    # harness writes proofs into a different tree than the one holding the test
    # script; without it that case falls back to an absolute path, which then
    # differs by invocation form and accumulates duplicate entries under the
    # (feature, tier, test_file) merge key.
    if test_file and test_file != 'unknown':
        abs_tf = os.path.realpath(test_file)
        rel = None
        for base in (os.getcwd(), _project_root_of(abs_tf)):
            if not base:
                continue
            try:
                cand = os.path.relpath(abs_tf, os.path.realpath(base))
            except ValueError:
                continue
            if not cand.startswith(os.pardir + os.sep) and cand != os.pardir:
                rel = cand
                break
        test_file = (rel or abs_tf).replace(os.sep, '/')
    # Forward slashes on every OS (proof_common RULE-15).
    test_file = test_file.replace(chr(92), '/')
    key = (feature, tier, plat)
    entry = {
        'feature': feature,
        'id': proof_id,
        'rule': rule_id,
        'test_file': test_file,
        'test_name': test_name,
        'status': status,
        'tier': tier,
    }
    if plat is not None:
        entry['platform'] = plat
    entries.setdefault(key, []).append(entry)

# Write proof files (write-scoped overwrite)
for (feature, tier, plat), new_entries in entries.items():
    suffix = f'{tier}@{plat}' if plat is not None else tier
    spec_dir = spec_dirs.get(feature)
    if spec_dir is None:
        print(f'WARNING: No spec found for feature \"{feature}\" — writing proofs to specs/{feature}.proofs-{suffix}.json. Create a spec with: purlin:spec {feature}', file=sys.stderr)
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

# RULE-19: the run marker, written at the same moment as the proof files.
# The harness has no skip signal (a script that never calls purlin_proof
# cannot be told apart from one that skipped), so skipped is 0.
all_entries = [e for group in entries.values() for e in group]
_write_run_marker(
    os.getcwd(),
    'shell_purlin',
    [e['test_file'] for e in all_entries],
    sum(1 for e in all_entries if e['status'] == 'pass'),
    sum(1 for e in all_entries if e['status'] != 'pass'),
    0,
)
" <<< "$_PURLIN_PROOFS"

  _PURLIN_PROOFS=""
}
