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

  _PURLIN_PROOFS="${_PURLIN_PROOFS}${feature}|${proof_id}|${rule_id}|${status}|${test_name}|${test_file}|${tier}
"
}

purlin_proof_finish() {
  [[ -z "$_PURLIN_PROOFS" ]] && return 0

  python3 -c "
import json, os, glob, sys

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

# Write proof files (feature-scoped overwrite)
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
    kept = [e for e in existing if e.get('feature') != feature]
    with open(path, 'w') as f:
        json.dump({'tier': tier, 'proofs': kept + new_entries}, f, indent=2)
        f.write('\n')
" <<< "$_PURLIN_PROOFS"

  _PURLIN_PROOFS=""
}
