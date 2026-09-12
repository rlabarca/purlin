#!/usr/bin/env python3
"""Issue verification receipts for every PASSING feature.

    python3 dev/issue_receipts.py [project_root] [--no-run-check]

Drives the MCP server's own verdict function rather than reimplementing it, so
a receipt can never disagree with what sync_status reports: coverage, the
active rule set and the vhash all come from `_feature_verdict`, and this script
computes none of them.

Receipts reference COMMITTED state, so commit specs and proofs first.

A receipt also records the run its evidence came from. Without a recorded run
a receipt says only that some proof file on disk holds a `pass`, which is a
claim about a file rather than about a test that was executed. So the issuer
refuses unless `.purlin/runtime/test_run.json` exists, records a passing sweep
and names the commit that is HEAD now. `--no-run-check` overrides, and says so
in the receipt by writing `evidence.test_run: null`.

`project_root` defaults to this repository. It is a parameter so a test can
receipt a temp project through the real issuer instead of hand-writing a
receipt shape that would then be free to drift from this one.
"""
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import purlin_server as ps  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RUN_MARKER = os.path.join('.purlin', 'runtime', 'test_run.json')


def _head(root):
    return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root,
                          capture_output=True, text=True).stdout.strip()


def marker_path(root):
    return os.path.join(root, '.purlin', 'runtime', 'test_run.json')


def read_run_marker(root):
    """(marker, error): the recorded run, and why it cannot back a receipt.

    `error` is None only when a marker exists, records a sweep that reached its
    end with no failed suite, and names the commit that is HEAD now. Those are
    the three ways a receipt's evidence can be about a different tree than the
    one it stamps.
    """
    path = marker_path(root)
    if not os.path.isfile(path):
        return None, (f'no run marker at {RUN_MARKER}; nothing records that '
                      f'the tests were run')
    try:
        with open(path) as f:
            marker = json.load(f)
    except (json.JSONDecodeError, IOError, OSError):
        return None, f'{RUN_MARKER} is not readable JSON'
    if not marker.get('ok'):
        return marker, (f'the run recorded in {RUN_MARKER} did not pass '
                        f'(ok: false)')
    head = _head(root)
    if head and marker.get('commit') != head:
        return marker, (f'the recorded run is at commit '
                        f'{(marker.get("commit") or "none")[:8]}, HEAD is '
                        f'{head[:8]}')
    return marker, None


def write_run_marker(root, test_files=None, ok=True, commit=None,
                     passed=1, failed=0, skipped=0):
    """Write a run marker for `root`, for tests that build a temp project.

    Shared from here rather than copied into each test file, so a change to the
    marker's shape moves one definition. `test_files` defaults to every
    `test_file` a committed proof entry names, which is the case a test almost
    always wants: a run that executed everything the proofs claim.
    """
    if test_files is None:
        test_files = sorted({
            entry.get('test_file', '')
            for entries in ps._read_proofs(root).values()
            for entry in entries
            if entry.get('test_file')
        })
    marker = {
        'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'commit': commit if commit is not None else _head(root),
        'sweep': 'dev/run_tests.sh',
        'suites': ['All Pytest Tests'],
        'test_files': list(test_files),
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'ok': ok,
    }
    path = marker_path(root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(marker, f, indent=2)
        f.write('\n')
    return marker


def legacy_migrations_pending(root):
    """The `legacy-*` migrations pending in `root`, as ids.

    A receipt is a claim about coverage, and while a legacy alias is in play
    coverage is a guess: the `@windows` tag is read as `@unit @on(windows)`,
    the legacy proof file is read as `unit@windows`, and a marker still writing
    the old tier can land results under a name no spec declares. Declining to
    claim is not a gate (`references/hard_gates.md` is unchanged); it is the
    issuer refusing to sign for something it cannot read straight.
    """
    return [entry['id'] for entry in ps._pending_migrations(root)
            if entry['id'].startswith('legacy-')]


def _legacy_refusal_lines(ids):
    return [
        f'REFUSED: {len(ids)} legacy migration'
        f'{"s" if len(ids) != 1 else ""} pending: {", ".join(ids)}',
        'The legacy alias makes coverage a guess, so no receipt is issued.',
        '\u2192 Run: purlin:init --update, then re-run the issuer',
    ]


def _refusal_lines(err):
    return [
        f'REFUSED: {err}',
        '→ Run: bash dev/run_tests.sh, then re-run the issuer '
        '(or pass --no-run-check to issue without a recorded run)',
    ]


def _proof_file_rows(root, features, proofs, executed, have_marker):
    """One `evidence.proof_files` row per file the feature's proofs came from.

    Returns (rows, unverified) where `unverified` lists (file, count) for files
    that no recorded run executed and no runner committed: evidence whose only
    witness is that somebody once wrote the file.
    """
    by_file = {}
    for entry in proofs:
        feature = entry.get('feature', '')
        info = features.get(feature)
        if not info:
            continue
        tier = entry.get('tier') or 'unit'
        platform = entry.get('platform')
        rel = ps._proof_file_rel(root, info['path'], feature, tier, platform)
        rel = rel.replace(os.sep, '/')
        by_file.setdefault((rel, tier, platform), []).append(entry)

    rows, unverified = [], []
    for (rel, tier, platform), entries in sorted(by_file.items()):
        prov = ps._file_provenance(root, rel) or {}
        missing = [e for e in entries
                   if e.get('test_file', '') not in executed]
        row_executed = have_marker and not missing
        rows.append({
            'file': rel,
            'tier': tier,
            'platform': platform,
            'commit': prov.get('commit'),
            'committed_at': prov.get('when'),
            'runner': prov.get('runner'),
            'executed_in_test_run': row_executed,
        })
        if have_marker and missing and not prov.get('runner'):
            unverified.append((rel, len(missing)))
    return rows, unverified


def main(root=None, quiet=False, run_check=True):
    root = root or ROOT
    # skill_verify RULE-13: no receipt while a legacy-* migration is pending.
    legacy_ids = legacy_migrations_pending(root)
    if legacy_ids:
        if not quiet:
            for line in _legacy_refusal_lines(legacy_ids):
                print(line)
        return [], []
    marker = None
    if run_check:
        marker, err = read_run_marker(root)
        if err:
            if not quiet:
                for line in _refusal_lines(err):
                    print(line)
            return [], []
    elif not quiet:
        print('WARNING: --no-run-check: issuing without a recorded test run; '
              'every receipt records evidence.test_run: null')

    ps._PROVENANCE_CACHE.clear()
    features = ps._scan_specs(root)
    all_proofs = ps._read_proofs(root)
    # The platform registry decides which scoped result satisfies which
    # declared platform (sync_status RULE-47), and which results count toward
    # nothing (RULE-53); resolved once, the same way sync_status does.
    registry, _errors = ps._platform_registry(ps.resolve_config(root))
    ps._mark_undeclared_results(features, all_proofs, registry)
    global_anchors = {
        k: v for k, v in features.items()
        if v.get('is_anchor') and v.get('is_global')
    }
    commit = _head(root)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    executed = set(marker.get('test_files') or []) if marker else set()
    test_run = None
    if marker:
        test_run = {
            'at': marker.get('at'),
            'commit': marker.get('commit'),
            'sweep': marker.get('sweep'),
            'passed': marker.get('passed'),
            'failed': marker.get('failed'),
            'skipped': marker.get('skipped'),
        }

    issued, skipped = [], []
    for name, info in sorted(features.items()):
        verdict = ps._feature_verdict(name, info, features, all_proofs,
                                      global_anchors, root, registry)
        active = verdict['active_entries']
        proof_by_rule = verdict['proof_by_rule']
        # A rule carrying a current manual stamp is proved (sync_status
        # RULE-5), exactly as `_feature_verdict` counted it. Reading only
        # `proof_by_rule` here is what made the issuer skip a feature the
        # report called PASSING.
        manual_ok_rules = verdict['manual_ok_rules']
        unproved = [k for k, label, _ in active
                    if proof_by_rule.get(k, {}).get('status') != 'pass'
                    and not (label == 'own' and k in manual_ok_rules)]
        if not active:
            skipped.append((name, 'no active rules'))
            continue
        if verdict['has_fail'] or unproved:
            skipped.append((name, 'FAILING' if verdict['has_fail']
                            else f'{len(unproved)} unproved'))
            continue

        rows, unverified = _proof_file_rows(
            root, features, verdict['relevant_proofs'], executed,
            marker is not None)
        if unverified:
            for rel, count in unverified:
                if not quiet:
                    print(f'  SKIP    {name:38s} {count} proof'
                          f'{"s" if count != 1 else ""} from {rel} not '
                          f'executed in the recorded run')
            skipped.append((name, 'evidence not in the recorded run'))
            continue

        rules_text = verdict['rules_text']
        receipt = {
            'feature': name,
            'vhash': verdict['vhash'],
            'vhash_version': 2,
            'commit': commit,
            'timestamp': now,
            'rules': sorted(rules_text),
            'rule_hashes': {k: ps._rule_text_hash(rules_text[k])
                            for k in sorted(rules_text)},
            'proofs': sorted(
                ({'feature': p.get('feature', ''), 'id': p.get('id', ''),
                  'rule': p.get('rule', ''), 'status': p.get('status', ''),
                  'tier': p.get('tier', ''),
                  'test_file': p.get('test_file', ''),
                  'test_name': p.get('test_name', ''),
                  'platform': p.get('platform')}
                 for p in verdict['relevant_proofs']),
                key=lambda p: (p['feature'], p['id'], p['rule'], p['tier'],
                               p['platform'] or '', p['test_file'],
                               p['test_name']),
            ),
        }
        # The stamps that counted, so a reader can see which rules were proved
        # by a human rather than by a test. Omitted when there are none.
        if verdict['manual_ok']:
            receipt['manual'] = verdict['manual_ok']
        receipt['evidence'] = {'test_run': test_run, 'proof_files': rows}
        # skill_verify RULE-9: a platform-partial receipt says so. The key is
        # omitted entirely when nothing is awaiting.
        awaiting = verdict['awaiting']
        if awaiting:
            receipt['awaiting_runner'] = [
                {'id': pid, 'tier': tier, 'platform': platform}
                for pid, tier, platform in awaiting
            ]
        # info['path'] is project-relative, so it must be resolved against
        # `root`. Without the join this only worked when cwd happened to be the
        # project root, which is true for a bare `python3 dev/issue_receipts.py`
        # and false for every other caller.
        path = os.path.join(root, os.path.dirname(info['path']),
                            f'{name}.receipt.json')
        with open(path, 'w') as f:
            json.dump(receipt, f, indent=2)
            f.write('\n')
        issued.append((name, verdict['vhash'], len(awaiting)))

    if quiet:
        return issued, skipped

    for n, v, aw in issued:
        note = f'  ({aw} awaiting runner)' if aw else ''
        print(f'  receipt {n:38s} vhash={v}{note}')
    for n, why in skipped:
        print(f'  SKIP    {n:38s} {why}')
    # The two counts the `verify:` commit carries, printed the way
    # `references/commit_conventions.md` spells them so the message is copied
    # rather than recounted. Features and anchors are never summed: an anchor
    # is a cross-cutting constraint, and one merged fraction hides which of the
    # two a run actually receipted.
    anchors_total = sum(1 for v in features.values() if v.get('is_anchor'))
    features_total = len(features) - anchors_total
    anchors_issued = sum(1 for n, _v, _aw in issued
                         if features[n].get('is_anchor'))
    features_issued = len(issued) - anchors_issued
    print(f'\nfeatures={features_issued}/{features_total} '
          f'anchors={anchors_issued}/{anchors_total}, '
          f'{len(skipped)} skipped')
    return issued, skipped


if __name__ == '__main__':
    argv = sys.argv[1:]
    run_check = '--no-run-check' not in argv
    positional = [a for a in argv if not a.startswith('--')]
    target = positional[0] if positional else ROOT
    if legacy_migrations_pending(target):
        for line in _legacy_refusal_lines(legacy_migrations_pending(target)):
            print(line)
        sys.exit(1)
    if run_check and read_run_marker(target)[1]:
        for line in _refusal_lines(read_run_marker(target)[1]):
            print(line)
        sys.exit(1)
    main(target, run_check=run_check)
