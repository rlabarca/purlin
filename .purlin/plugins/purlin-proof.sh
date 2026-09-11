#!/usr/bin/env bash
# Purlin proof harness for shell tests.
#
# Source this file and use purlin_proof() to register test results:
#   source .purlin/plugins/purlin-proof.sh  # or scripts/proof/shell_purlin.sh
#   purlin_proof "my_feature" "PROOF-1" "RULE-1" pass "test_description"
#   purlin_proof "my_feature" "PROOF-2" "RULE-2" fail "test_description"
#   purlin_proof_finish  # writes proof files
set -euo pipefail

_PURLIN_PROOFS=""

purlin_proof() {
  local feature="$1" proof_id="$2" rule_id="$3" status="$4" test_name="${5:-}"
  local tier="${PURLIN_PROOF_TIER:-unit}"
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

  _PURLIN_PROOFS="${_PURLIN_PROOFS}${feature}|${proof_id}|${rule_id}|${status}|${test_name}|${test_file}|${tier}
"
}

purlin_proof_finish() {
  [[ -z "$_PURLIN_PROOFS" ]] && return 0

  python3 -c "
import json, os, glob, sys


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
    feature, proof_id, rule_id, status, test_name, test_file, tier = parts
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
    key = (feature, tier)
    entries.setdefault(key, []).append({
        'feature': feature,
        'id': proof_id,
        'rule': rule_id,
        'test_file': test_file,
        'test_name': test_name,
        'status': status,
        'tier': tier,
    })

# Write proof files (write-scoped overwrite)
for (feature, tier), new_entries in entries.items():
    spec_dir = spec_dirs.get(feature)
    if spec_dir is None:
        print(f'WARNING: No spec found for feature \"{feature}\" — writing proofs to specs/{feature}.proofs-{tier}.json. Create a spec with: purlin:spec {feature}', file=sys.stderr)
        spec_dir = 'specs'
    path = os.path.join(spec_dir, f'{feature}.proofs-{tier}.json')
    existing = []
    if os.path.exists(path):
        with open(path) as f:
            existing = json.load(f).get('proofs', [])
    # Write-scoped overwrite keyed by (feature, tier, test_file), per proof_common RULE-4,
    # plus orphan reaping of vanished test files (RULE-11).
    run_files = {e['test_file'] for e in new_entries}
    kept = [
        e for e in existing
        if e.get('feature') != feature
        or (e.get('test_file') not in run_files and os.path.exists(e.get('test_file') or ''))
    ]
    tmp_path = path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump({'tier': tier, 'proofs': kept + new_entries}, f, indent=2)
        f.write('\n')
    os.replace(tmp_path, path)
" <<< "$_PURLIN_PROOFS"

  _PURLIN_PROOFS=""
}
