#!/usr/bin/env python3
"""Read a repository's state without cloning it whole.

    python3 scripts/report/scan.py --repo <url> [--ref <branch|tag>]

QA and a PM want the rollup without a checkout and without a build. This
fetches `specs/` and `.purlin/records/` alone, reads them with the same
package every other surface reads, and prints how many rules meet the gate,
one line per bucket, and how far the working branch has moved past the newest
record. CI prints the same text as a pull request comment, so one rollup is
read everywhere. The review list follows, one line per rule, so a reader
without a checkout can work it: the risk, the rule, the cell that blocks it
and why a person is needed.

Nothing is written outside the temporary directory, and the directory is
removed before the command returns.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile

_REPORT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(_REPORT_DIR))
_MCP_DIR = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import console as console_module                  # noqa: E402

# Only these two trees are fetched. A repository's code is not read here.
SPARSE = ('specs', '.purlin')
RECORDS_DIR = '.purlin/records'
# The order a person reads the review list in.
RISK_ORDER = ('high', 'medium', 'low')
# The separator the status line and the board both use between two counts.
DOT = ' · '

# How much history is fetched. Enough to count the commits since the newest
# record on any branch anyone reviews; a deeper count says so instead.
DEPTH = 200


def fetch(url, ref, into):
    """Fetch `specs/` and `.purlin/` at `ref` into `into`. The commit sha."""
    _git(into, ['init', '--quiet'])
    _git(into, ['remote', 'add', 'origin', url])
    _git(into, ['config', 'core.sparseCheckout', 'true'])
    info = os.path.join(into, '.git', 'info')
    if not os.path.isdir(info):
        os.makedirs(info)
    with open(os.path.join(info, 'sparse-checkout'), 'w',
              encoding='utf-8') as handle:
        for folder in SPARSE:
            handle.write('/%s/\n' % folder)

    target = ref or 'HEAD'
    fetched = _git(into, ['fetch', '--depth', str(DEPTH), 'origin', target],
                   check=False)
    if fetched is None:
        raise SystemExit('Could not fetch %s from %s.' % (target, url))
    _git(into, ['checkout', '--quiet', 'FETCH_HEAD'])
    return (_git(into, ['rev-parse', 'HEAD']) or '').strip()


def commits_behind(project_root, record_commit):
    """How many commits the ref is past the commit the newest record observed.

    The commit that carries the record is not counted: it lands after the run
    it describes, so counting it would say every project is one commit behind
    the moment CI writes. Commits that touch only `.purlin/records/` are left
    out for the same reason.
    """
    if not record_commit:
        return None
    counted = _git(project_root,
                   ['rev-list', '--count', '%s..HEAD' % record_commit,
                    '--', '.', ':!%s' % RECORDS_DIR],
                   check=False)
    if counted is None:
        return None
    try:
        return int(counted.strip())
    except ValueError:
        return None


def newest_record(payload):
    """The newest record any feature carries, or None."""
    newest = None
    for by_os in (payload.get('records') or {}).values():
        for record in by_os.values():
            if newest is None or str(record.get('timestamp') or '') > str(
                    newest.get('timestamp') or ''):
                newest = record
    return newest


def rollup_text(project_root, payload):
    """The rollup: the gate, one line per bucket, and the newest record.

    A bucket is the one tile a rule is counted in, so the counts add up to
    the rule total and a reader can check them. The flags `stale`, `held`,
    `manual` and `audit` are counted beside the buckets, never instead of
    them, and each is printed only when it stands.
    """
    summary = payload['summary']
    gate = payload['gate']['gate']
    lines = ['Purlin: %s, gate %s' % (payload['project'], gate), '']
    lines.append('%d of %d rules meet the gate %s%s%d failing'
                 % (summary['met'], summary['rules'], gate, DOT,
                    summary.get('failing') or 0))
    lines.append('%d features, %d rules.'
                 % (summary['features'], summary['rules']))

    from purlin import states
    for bucket in states.bucket_keys(gate):
        lines.append('  %-12s %d' % (bucket, summary.get(bucket) or 0))

    if summary.get('stale'):
        lines.append('%d signatures stale: the hashes changed after signing.'
                     % summary['stale'])
    if summary.get('held'):
        lines.append('%d rules held: a person said a test does not prove '
                     'its proof.' % summary['held'])
    if summary.get('manual'):
        lines.append('%d rules have a manual test: a person runs it and a '
                     'signature records what they saw.' % summary['manual'])
    if summary.get('audit'):
        lines.append('%d rules need a manual audit: the model review could '
                     'not settle them.' % summary['audit'])

    record = newest_record(payload)
    lines.append('')
    if record is None:
        lines.append('No record has been committed yet.')
    else:
        behind = commits_behind(project_root, record.get('commit'))
        lines.append('Newest record: %s (%s, %s).'
                     % (record.get('path'), record.get('label') or 'local',
                        record.get('timestamp') or 'no timestamp'))
        if behind is None:
            lines.append('How far this ref is past that record is unknown: '
                         'the fetched history stops short of the commit it '
                         'observed.')
        elif behind == 0:
            lines.append('0 commits behind the latest record.')
        else:
            lines.append('%d commits behind the latest record.' % behind)
    return '\n'.join(lines)


def review_list_text(payload):
    """The review list, one line per rule: risk, rule, cell, and why.

    High risk first, then medium, then low; inside a level a stale or held
    rule first, then by feature and rule number, which is the order the
    payload already sorts them in and the order a person works them in. The
    `why` tokens are the closed set `unsigned`, `stale`, `held`,
    `manual test` and `manual audit`.
    """
    entries = []
    for item in payload.get('review_list') or ():
        owner = item.get('owner') or item.get('feature')
        risk = item.get('risk') or 'low'
        why = list(item.get('why') or ())
        number = str(item.get('rule') or '').rpartition('-')[2]
        entries.append((RISK_ORDER.index(risk) if risk in RISK_ORDER else 3,
                        0 if set(why) & {'stale', 'held'} else 1, owner or '',
                        int(number) if number.isdigit() else 0,
                        '  %-6s  %s %s  %s  %s' % (
                            risk, owner, item.get('rule'),
                            item.get('cell') or '', ', '.join(why))))
    if not entries:
        return 'Review list: no rule needs a person.'
    lines = ['Review list: %d %s a person.'
             % (len(entries),
                'rule needs' if len(entries) == 1 else 'rules need')]
    lines.extend(line.rstrip() for *_key, line in sorted(entries))
    return '\n'.join(lines)


def scan(url, ref=None):
    """Fetch, read and render one repository's rollup as text."""
    into = tempfile.mkdtemp(prefix='purlin-scan-')
    try:
        fetch(url, ref, into)
        from purlin import payload as payload_module
        payload = payload_module.build_payload(into, generated_by='scan')
        return rollup_text(into, payload) + '\n\n' + review_list_text(payload)
    finally:
        shutil.rmtree(into, ignore_errors=True)


def _git(cwd, args, check=True):
    try:
        result = subprocess.run(['git'] + list(args), cwd=cwd,
                                capture_output=True, text=True, timeout=180)
    except (subprocess.SubprocessError, OSError) as error:
        if check:
            raise SystemExit('git %s failed: %s' % (' '.join(args), error))
        return None
    if result.returncode != 0:
        if check:
            raise SystemExit('git %s failed: %s'
                             % (' '.join(args), result.stderr.strip()))
        return None
    return result.stdout


def main(argv=None):
    console_module.force_utf8_stdio()
    parser = argparse.ArgumentParser(
        description='Print a repository\'s rollup without cloning it '
                    'whole.')
    parser.add_argument('--repo', required=True,
                        help='the repository URL, or a local path')
    parser.add_argument('--ref', default=None,
                        help='the branch or tag to read; the default branch '
                             'when omitted')
    args = parser.parse_args(argv)
    print(scan(args.repo, args.ref))
    return 0


if __name__ == '__main__':
    sys.exit(main())
