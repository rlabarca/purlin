#!/usr/bin/env python3
"""Issue verification receipts for every PASSING feature.

Drives the MCP server's own coverage and vhash functions rather than
reimplementing them, so a receipt can never disagree with what sync_status
reports. This is `purlin:verify` Step 3 as a script; the skill is the
authority on the receipt shape.

Receipts reference COMMITTED state, so commit specs and proofs first.
"""
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import purlin_server as ps  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def main():
    features = ps._scan_specs(ROOT)
    all_proofs = ps._read_proofs(ROOT)
    global_anchors = {
        k: v for k, v in features.items()
        if v.get('is_anchor') and v.get('is_global')
    }
    commit = subprocess.run(['git', 'rev-parse', 'HEAD'],
                            cwd=ROOT, capture_output=True, text=True).stdout.strip()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    issued, skipped = [], []
    for name, info in sorted(features.items()):
        rule_entries, _unresolved = ps._build_coverage_rules(
            name, info, features, global_anchors)
        proofs = ps._collect_relevant_proofs(name, rule_entries, all_proofs)
        proof_by_rule = ps._build_proof_lookup(name, rule_entries, all_proofs)

        # Mirrors _report_feature: deferred rules are excluded from coverage,
        # and the vhash is taken over the active rule keys only.
        active = [(k, l, s) for k, l, s, is_def in rule_entries if not is_def]
        unproved = [k for k, _, _ in active
                    if proof_by_rule.get(k, {}).get('status') != 'pass']
        has_fail = any(proof_by_rule.get(k, {}).get('status') == 'fail'
                       for k, _, _ in active)
        if has_fail or unproved:
            skipped.append((name, 'FAILING' if has_fail else f'{len(unproved)} unproved'))
            continue

        rules = {k: True for k, _, _ in active}
        vhash = ps._compute_vhash(rules, proofs)
        path = os.path.join(os.path.dirname(info['path']), f'{name}.receipt.json')
        with open(path, 'w') as f:
            json.dump({
                'feature': name,
                'vhash': vhash,
                'commit': commit,
                'timestamp': now,
                'rules': sorted(rules.keys()),
                'proofs': sorted(
                    ({'id': p['id'], 'rule': p['rule'], 'status': p['status']}
                     for p in proofs),
                    key=lambda p: (p['id'], p['rule']),
                ),
            }, f, indent=2)
            f.write('\n')
        issued.append((name, vhash))

    for n, v in issued:
        print(f'  receipt {n:38s} vhash={v}')
    for n, why in skipped:
        print(f'  SKIP    {n:38s} {why}')
    print(f'\n{len(issued)} receipts issued, {len(skipped)} skipped')


if __name__ == '__main__':
    main()
