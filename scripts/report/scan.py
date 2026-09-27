#!/usr/bin/env python3
"""Read a repository's state without cloning it whole.

    python3 scripts/report/scan.py --repo <url> [--ref <branch|tag>]

QA and a PM want the rollup without a checkout and without a build. This
fetches `specs/` and `.purlin/` alone, which is where the test results and
the records are, reads them with the same package every other surface reads,
and prints how many rules meet the gate, one line per bucket, and how far the
working branch has moved past the newest record. It is the one rollup a
reader without a checkout gets, and it is the same one the board draws and
`purlin:status` prints. The two lists follow,
one line per rule, so a reader without a checkout can work them: the bar, the
rule, the cell and the word that put it there.

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
# The order a person reads both lists in: the rules whose bar is `strong`
# first, as the payload already sorts them.
BAR_ORDER = ('strong', 'passed')
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
    the rule total and a reader can check them, and each is named with the
    word its tile carries on the board. The counts beside the buckets, never
    instead of them, are `stale`, `held`, `manual`, `unsettled`,
    `not_audited` and `signable`, and each is printed only when it stands.
    """
    from purlin import board as board_module

    summary = payload['summary']
    gate = payload['gate']['gate']
    lines = ['Purlin: %s, gate %s' % (payload['project'], gate), '']
    lines.append(board_module.headline(summary, gate))
    lines.append('%s, %s, %s.'
                 % (board_module.count_of(summary['features'], 'feature'),
                    board_module.count_of(summary['rules'], 'rule'),
                    board_module.proofs_summary(summary)))
    lines.append('')

    # The tiles' own words, in the tiles' own order, so a reader of the board
    # and a reader of this text count the same six things.
    for label, count in board_module.bucket_counts(summary, gate):
        lines.append('  %-9s %d' % (label, count))

    if summary.get('stale'):
        lines.append('%s stale: the hashes changed after signing.'
                     % board_module.count_of(summary['stale'], 'signature'))
    if summary.get('partial'):
        lines.append('%d rules are partial: their tests pass on one operating '
                     'system and not on another.' % summary['partial'])
    if summary.get('held'):
        lines.append('%d rules held: a person said a test does not prove '
                     'its proof.' % summary['held'])
    if summary.get('manual'):
        lines.append('%d rules have a manual test: a person runs it and a '
                     'signature records what they saw.' % summary['manual'])
    if summary.get('unsettled'):
        lines.append('%d rules are unsettled: the AI audit could not settle '
                     'them.' % summary['unsettled'])
    if summary.get('not_audited'):
        lines.append('%d rules are not audited: no audit has run over this '
                     'code.' % summary['not_audited'])
    if summary.get('signable'):
        lines.append('%d rules are signable: they cleared their bar and need '
                     'a signature.' % summary['signable'])

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
    """Review, then Sign: one line per rule, the bar, the cell and the word.

    The rules whose bar is `strong` read first, then by feature and rule
    number, which is the order the payload already sorts them in and the
    order a person works them in. Review's words are `manual test`,
    `unsettled` and `held`; Sign's are `unsigned`, `stale` and `held`.
    """
    review = list(payload.get('review_list') or ())
    sign = list(payload.get('sign_list') or ())
    total = len(review) + len(sign)
    from purlin import board as board_module

    if not total:
        return '%s.' % board_module.needs_a_person(0).capitalize()
    lines = ['%s.' % board_module.needs_a_person(total).capitalize()]
    for title, rows in (('Review list', review), ('Sign list', sign)):
        if not rows:
            continue
        lines.append('%s: %d' % (title, len(rows)))
        lines.extend(_list_line(item) for item in _sorted(rows))
    return '\n'.join(lines)


def _sorted(rows):
    """One list in the order the payload writes it, sorted again to be sure."""
    def key(item):
        bar = item.get('bar') or 'passed'
        number = str(item.get('rule') or '').rpartition('-')[2]
        return (BAR_ORDER.index(bar) if bar in BAR_ORDER else 2,
                item.get('owner') or '',
                int(number) if number.isdigit() else 0)
    return sorted(rows, key=key)


def _list_line(item):
    """One row: the bar, the feature and rule, the cell and the word."""
    owner = item.get('owner') or item.get('feature')
    return ('  %-6s  %s %s  %s  %s'
            % (item.get('bar') or 'passed', owner, item.get('rule'),
               item.get('cell') or '',
               ', '.join(item.get('why') or ()))).rstrip()


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
