"""The status table: one row per feature, one state per rule.

The table is the seven states and nothing else. A row says how many rules the
feature has, the lowest state any of them reached, the count in each state
that is not zero, the test strength, the label on the latest record, how many
approvals the feature carries and how many rules are waiting on CI to re-run.

Copy follows `design/readme.md`: sentence case, second person for what you
do, third person for what Purlin does, exact numbers, and the only glyphs are
`->`, `>` and `v` in their unicode forms. No emoji, anywhere.
"""

import os
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import (drift as drift_module, payload as payload_module,
                    specs as specs_module, states)

ARROW = '→'
COLUMNS = ('Feature', 'Rules', 'Lowest state', 'States', 'Strength', 'Record',
           'Approvals', 'Re-verify')

NO_SPECS = ('No specs found under specs/.\n'
            '%s Run: purlin:init to set this project up, or purlin:spec to '
            'write the first one.' % ARROW)


def sync_status(project_root):
    """The whole status report for a project root, as text."""
    data = payload_module.build_payload(project_root, generated_by='sync_status')
    if not data['features']:
        return NO_SPECS

    lines = []
    lines.append('Purlin status: %s, plugin %s, gate %s'
                 % (data['project'], data['version'], data['gate']['gate']))
    lines.append('')
    lines.extend(_table(data))
    lines.append('')
    lines.extend(_summary(data))

    pin_lines = _pin_lines(project_root)
    if pin_lines:
        lines.append('')
        lines.extend(pin_lines)

    uncommitted = _uncommitted_specs(project_root)
    if uncommitted:
        lines.append('')
        lines.append('Uncommitted spec changes:')
        lines.extend('  ' + line for line in uncommitted)

    if data['warnings']:
        lines.append('')
        lines.extend(data['warnings'])

    lines.append('')
    lines.extend(_directives(data, project_root))
    return '\n'.join(lines)


def _update_pending(project_root):
    """True while `purlin:init --update` still has migrations to apply.

    Imported here rather than at the top: a project that is already on this
    release pays nothing for the question, and a checkout without the init
    scripts still prints a table.
    """
    init_dir = os.path.join(os.path.dirname(_MCP_DIR), 'init')
    if init_dir not in sys.path:
        sys.path.insert(0, init_dir)
    try:
        import update
        return bool(update.pending(project_root))
    except Exception:                       # noqa: BLE001 - never block status
        return False


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

def _row(feature):
    rollup = feature['rollup']
    name = feature['name'] + (' (anchor)' if feature['is_anchor'] else '')
    strength = rollup.get('test_strength')
    record = feature.get('latest_record')
    return (
        name,
        str(rollup['rules']),
        rollup['lowest_state'],
        _breakdown(rollup['counts']),
        'n/a' if strength is None else '%d%%' % int(strength),
        (record or {}).get('label') or 'none',
        str(len(feature['approvals'])),
        str(rollup['re_verify_pending']),
    )


def _breakdown(counts):
    """The non-zero state counts, lowest state first."""
    parts = ['%s %d' % (state, counts[state])
             for state in states.STATE_ORDER if counts.get(state)]
    return ', '.join(parts) or '-'


def _table(data):
    rows = [_row(feature) for feature in
            sorted(data['features'],
                   key=lambda f: (states.STATE_ORDER.index(
                       f['rollup']['lowest_state']), f['name']))]
    widths = [max(len(COLUMNS[i]), max((len(r[i]) for r in rows), default=0))
              for i in range(len(COLUMNS))]
    rule = '─' * (sum(widths) + 2 * (len(widths) - 1))
    lines = [_line(COLUMNS, widths), rule]
    lines.extend(_line(row, widths) for row in rows)
    lines.append(rule)
    return lines


def _line(cells, widths):
    out = []
    for index, cell in enumerate(cells):
        if index in (1, 4):
            out.append(cell.rjust(widths[index]))
        else:
            out.append(cell.ljust(widths[index]))
    return '  '.join(out).rstrip()


# ---------------------------------------------------------------------------
# The rollup and the directives
# ---------------------------------------------------------------------------

def _summary(data):
    rollup = data['project_rollup']
    cfg = data['gate']
    lines = ['%d features, %d rules. %s.'
             % (rollup['features'], rollup['rules'],
                _breakdown(rollup['counts']))]
    second = ['gate %s' % cfg['gate'],
              'minimum test strength %d%%' % cfg['min_strength']]
    if cfg['ai_review_at'] != 'never':
        second.append('review at risk %s and above' % cfg['ai_review_at'])
    if rollup['stale']:
        second.append('%d approvals stale' % rollup['stale'])
    if rollup['re_verify_pending']:
        second.append('%d rules waiting on CI' % rollup['re_verify_pending'])
    lines.append(', '.join(second) + '.')
    return lines


def _directives(data, project_root):
    """The next step, computed from the state, plus anything to fix first."""
    lines = []
    if (any('purlin:init --update' in warning for warning in data['warnings'])
            or _update_pending(project_root)):
        lines.append('%s Run: purlin:init --update' % ARROW)

    counts = data['states']
    gate = data['gate']['gate']
    rollup = data['project_rollup']

    if rollup['stale']:
        lines.append('%s Next: run purlin:review. %d rules changed after they '
                     'were approved, so a person has to look at them.'
                     % (ARROW, rollup['stale']))
    elif counts.get(states.DRAFTED):
        lines.append('%s Next: run purlin:spec. %d rules have no proof that '
                     'passes the free checks.' % (ARROW, counts[states.DRAFTED]))
    elif counts.get(states.PROOF_READY):
        lines.append('%s Next: run purlin:build. %d rules have a proof and no '
                     'passing test.' % (ARROW, counts[states.PROOF_READY]))
    elif counts.get(states.TESTED) and gate != 'tested':
        lines.append('%s Next: run purlin:verify. %d rules pass locally and have '
                     'no record at this commit.' % (ARROW, counts[states.TESTED]))
    elif counts.get(states.TESTED):
        lines.append('%s Next: run purlin:verify to write the record for %d '
                     'tested rules.' % (ARROW, counts[states.TESTED]))
    elif gate == 'approved' and (counts.get(states.RECORDED)
                                 or counts.get(states.REVIEWED)):
        outstanding = (counts.get(states.RECORDED, 0)
                       + counts.get(states.REVIEWED, 0))
        lines.append('%s Next: run purlin:approve. %d rules are recorded and not '
                     'approved.' % (ARROW, outstanding))
    else:
        lines.append('%s Next: nothing is outstanding at gate %s.' % (ARROW, gate))

    if data['review_list']:
        lines.append('%s Review list: %d rules are waiting for a look. Run '
                     'purlin:review.' % (ARROW, len(data['review_list'])))
    return lines


# ---------------------------------------------------------------------------
# Pins and the working tree
# ---------------------------------------------------------------------------

def _pin_lines(project_root):
    """One line per anchor whose pin is not current, or whose Source is refused."""
    features = specs_module.scan_specs(project_root)
    rows = drift_module.pin_report(project_root, features)
    lines = []
    for row in rows:
        if row.get('reason'):
            lines.append('%s: (source rejected: %s)'
                         % (row['anchor'], row['reason']))
        elif row['status'] == 'behind':
            lines.append('%s: the pin %s is behind its source, now %s. Run '
                         'purlin:anchor sync %s.'
                         % (row['anchor'], (row.get('pinned') or '')[:7],
                            row.get('remote_sha', ''), row['anchor']))
        elif row['status'] == 'unpinned':
            lines.append('%s: names a source and no pin. Run purlin:anchor sync '
                         '%s.' % (row['anchor'], row['anchor']))
        else:
            lines.append('%s: the source could not be read (%s).'
                         % (row['anchor'], row.get('error', 'unknown')))
    if lines:
        lines.insert(0, 'Anchors:')
    return lines


def _uncommitted_specs(project_root):
    """`git status` lines for spec files that are not committed."""
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain', '--', 'specs/'],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines()
            if len(line) > 3 and line[3:].endswith('.md')]
