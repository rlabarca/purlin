#!/usr/bin/env python3
"""Read a repository's state without cloning it whole.

    python3 scripts/report/scan.py --repo <url> [--ref <branch|tag>]

QA and a PM want the rollup without a checkout and without a build. This
fetches `specs/` and `.purlin/records/` alone, reads them with the same
package every other surface reads, and prints the seven-state rollup and how
far the working branch has moved past the newest record. CI prints the same
text as a pull request comment, so one rollup is read everywhere.

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

# Only these two trees are fetched. A repository's code is not read here.
SPARSE = ('specs', '.purlin')
RECORDS_DIR = '.purlin/records'
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
    """The seven-state rollup, plus how far HEAD has moved past the record."""
    rollup = payload['project_rollup']
    lines = ['Purlin: %s, gate %s'
             % (payload['project'], payload['gate']['gate']),
             '']
    lines.append('%d features, %d rules.'
                 % (rollup['features'], rollup['rules']))

    from purlin import states
    for state in states.STATE_ORDER:
        count = (rollup.get('counts') or {}).get(state)
        if count:
            lines.append('  %-12s %d' % (state, count))

    if rollup.get('stale'):
        lines.append('%d rules are Stale: a human must look.'
                     % rollup['stale'])
    if rollup.get('re_verify_pending'):
        lines.append('%d rules are re-verify pending: only the code changed.'
                     % rollup['re_verify_pending'])

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


def scan(url, ref=None):
    """Fetch, read and render one repository's rollup as text."""
    into = tempfile.mkdtemp(prefix='purlin-scan-')
    try:
        fetch(url, ref, into)
        from purlin import payload as payload_module
        payload = payload_module.build_payload(into, generated_by='scan')
        return rollup_text(into, payload)
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
    parser = argparse.ArgumentParser(
        description='Print a repository\'s seven-state rollup without '
                    'cloning it whole.')
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
