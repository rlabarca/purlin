#!/usr/bin/env bash
# Purlin proof harness for shell tests.
#
# Source this file and use purlin_proof() to register test results:
#   source .purlin/plugins/purlin-proof.sh  # or scripts/proof/shell_purlin.sh
#   purlin_proof "my_feature" "PROOF-1" "RULE-1" pass "test description"
#   purlin_proof "my_feature" "PROOF-2" "RULE-2" fail "test description"
#   purlin_proof_finish  # writes proof files
#
# Tier comes from PURLIN_PROOF_TIER (default "unit").
#
# The harness writes what it observed to
# .purlin/runtime/proofs/<feature>.<tier>.json. Proof files are runtime: they
# are gitignored, so two runs on two branches never conflict and nothing about
# a run is committed. The record purlin:audit writes is what says where a run
# happened, and it says it once per run.
#
# The operating system a proof must be proved on is a property of the spec,
# not of the test: write @env(windows), @env(macos) or @env(linux) on the
# proof line. The retired PURLIN_PROOF_PLATFORMS variable is refused rather
# than ignored, so a script carrying one fails with a line saying what to
# write instead.
#
# The project root is the nearest ancestor of the working directory holding
# specs/ or .purlin/, and every test_file it writes is relative to it with /
# separators on every operating system, so sourcing this harness from a
# subdirectory writes into the project's own tree.
#
# purlin_proof_finish returns non-zero when it saw calls and wrote no entry at
# all, so evidence that went missing fails the script rather than leaving a
# stale proof file behind.
set -euo pipefail

_PURLIN_PROOFS=""

# The working directory as the python3 below can resolve it. Git bash on
# Windows reports a POSIX path (/c/work) that a native python3 reads as a
# directory named c on the current drive; `pwd -W` prints the same directory
# as C:/work. Every other shell refuses -W, and there the plain path is right.
_purlin_pwd() {
  pwd -W 2>/dev/null || pwd
}

purlin_proof() {
  local feature="$1" proof_id="$2" rule_id="$3" status="$4" test_name="${5:-}"
  local tier="${PURLIN_PROOF_TIER:-unit}"
  local test_file="${BASH_SOURCE[1]:-unknown}"

  if [[ -n "${PURLIN_PROOF_PLATFORMS:-}" ]]; then
    echo "purlin: PURLIN_PROOF_PLATFORMS is not read any more; write @env(windows), @env(macos) or @env(linux) on the proof line in the spec instead (${feature} ${proof_id})." >&2
    return 1
  fi

  # Absolutize here, at call time, while the cwd is still the caller's. The
  # value is relativized in purlin_proof_finish. Doing it in this order is what
  # makes `bash dev/x.sh` and `bash /abs/dev/x.sh` record the SAME test_file:
  # the raw BASH_SOURCE differs between those two, the absolute path does not.
  # Under the (feature, tier, test_file) merge key a difference here would not
  # collapse, it would accumulate as two entries for one proof.
  # A drive letter is as absolute as a leading slash: a script reached as
  # `bash C:/work/x.sh` must not have the working directory put in front of it.
  if [[ "$test_file" != "unknown" && "$test_file" != /* \
        && ! "$test_file" =~ ^[A-Za-z]:[/\\] ]]; then
    test_file="$(_purlin_pwd)/$test_file"
  fi

  _PURLIN_PROOFS="${_PURLIN_PROOFS}${feature}|${proof_id}|${rule_id}|${status}|${test_name}|${test_file}|${tier}
"
}

purlin_proof_finish() {
  [[ -z "$_PURLIN_PROOFS" ]] && return 0

  local payload="$_PURLIN_PROOFS"
  _PURLIN_PROOFS=""

  python3 -c "
import json, os, sys


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


# The project root: everything below is addressed from here rather than from
# the working directory, so a run started in a subdirectory writes into the
# project's own tree instead of making a second one beside itself.
root = _project_root()

entries = {}
seen = set()
for line in sys.stdin.read().strip().split('\n'):
    if not line:
        continue
    parts = line.split('|')
    if len(parts) < 7:
        continue
    feature, proof_id, rule_id, status, test_name, test_file, tier = parts[:7]
    seen.add(feature)
    # Record the test file project-relative with POSIX separators, so nothing
    # carries one machine's home directory or a value that depends on how the
    # script happened to be invoked. Two candidate roots, in order: the project
    # being written to, then the project the test file itself lives in. The
    # second matters when a harness writes proofs into a different tree than
    # the one holding the test script; without it that case falls back to an
    # absolute path, which then differs by invocation form and accumulates
    # duplicate entries under the (feature, tier, test_file) merge key.
    if test_file and test_file != 'unknown':
        abs_tf = os.path.realpath(test_file)
        rel = None
        for base in (root, _find_root(os.path.dirname(abs_tf))):
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
    test_file = test_file.replace(chr(92), '/')
    entries.setdefault((feature, tier), []).append({
        'feature': feature,
        'id': proof_id,
        'rule': rule_id,
        'test_file': test_file,
        'test_name': test_name,
        'status': status,
        'tier': tier,
    })

if not entries:
    if seen:
        print('purlin: calls were seen and no proof entry was written for %s; '
              'the proof files on disk describe an earlier run.'
              % ', '.join(sorted(seen)), file=sys.stderr)
        sys.exit(1)
    sys.exit(0)

directory = os.path.join(root, '.purlin', 'runtime', 'proofs')
os.makedirs(directory, exist_ok=True)

for (feature, tier), new_entries in entries.items():
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
    # whose test file no longer exists are reaped. Each path it wrote is
    # resolved from the project root, the same root it was relativized
    # against. The harness has no skip signal: a script that never called
    # purlin_proof cannot be told apart from one that skipped.
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
    # call order never reaches the file.
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
" <<< "$payload"
}
