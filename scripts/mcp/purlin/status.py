"""The status table: one row per spec, one cell per evidence level.

The table is the dashboard's board, rendered as text. Its columns are the
board's columns and its cells are the board's cells, character for character,
because a reader who learns one should not have to learn the other:
`purlin:purlin.board` renders both. A row says how many rules the spec has,
how many proofs it writes and how many of those have no test, and how many
rules pass their tests. At `strong` the row adds how many rules are strong
and the test strength; at `signed` it adds how many are signable and how many
are signed. The table scales with the gate: a `passed` project is never shown
a strength, a bar or a signature it did not ask for.

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

from purlin import (board as board_module, drift as drift_module,
                    payload as payload_module, specs as specs_module, states)

ARROW = '→'
DOT = board_module.DOT

NO_SPECS = ('No specs found under specs/.\n'
            '%s Run: purlin:init to set this project up, or purlin:spec to '
            'write the first one.' % ARROW)


def columns_for(gate):
    """The table's columns under `gate`, left to right: the board's own."""
    return board_module.columns_for(gate)


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
    import importlib
    init_dir = os.path.join(os.path.dirname(_MCP_DIR), 'init')
    if init_dir not in sys.path:
        sys.path.insert(0, init_dir)
    try:
        return bool(importlib.import_module('update').pending(project_root))
    except Exception:                       # noqa: BLE001 - never block status
        return False


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

def _row(feature, gate):
    """One spec's row, rendered by the module the board renders from."""
    name = feature['name'] + (' (anchor)' if feature['is_anchor'] else '')
    return board_module.row_cells(name, feature['rollup'], gate)


def _table(data):
    gate = data['gate']['gate']
    columns = columns_for(gate)
    # The feature with the most rules short of the gate reads first: the table
    # opens on the work rather than on the alphabet.
    features = sorted(data['features'],
                      key=lambda f: (f['rollup']['met'] - f['rollup']['rules'],
                                     f['name']))
    rows = [_row(feature, gate) for feature in features]
    widths = [max(len(columns[i]), max((len(r[i]) for r in rows), default=0))
              for i in range(len(columns))]
    rule = '─' * (sum(widths) + 2 * (len(widths) - 1))
    lines = [_line(columns, widths, columns), rule]
    lines.extend(_line(row, widths, columns) for row in rows)
    lines.append(rule)
    return lines


def _line(cells, widths, columns):
    """One table line; the counted columns are right aligned, the rest left."""
    right = {index for index, name in enumerate(columns)
             if name in ('Rules',)}
    out = []
    for index, cell in enumerate(cells):
        if index in right:
            out.append(cell.rjust(widths[index]))
        else:
            out.append(cell.ljust(widths[index]))
    return '  '.join(out).rstrip()


# ---------------------------------------------------------------------------
# The summary and the directives
# ---------------------------------------------------------------------------

def _summary(data):
    summary = data['summary']
    cfg = data['gate']
    gate = cfg['gate']
    lines = [board_module.headline(summary, gate),
             board_module.bucket_line(summary, gate) + '.']
    second = ['%d features' % summary['features'],
              board_module.proofs_summary(summary)]
    if gate != 'passed':
        if cfg.get('min_strength') is not None:
            second.append('minimum test strength %d%%' % cfg['min_strength'])
        if summary.get('manual'):
            second.append('%d rules with a manual test' % summary['manual'])
        if summary.get('unsettled'):
            second.append('%d rules unsettled' % summary['unsettled'])
        if summary.get('not_audited'):
            second.append('%d rules not audited' % summary['not_audited'])
        if summary.get('held'):
            second.append('%d rules held' % summary['held'])
    if gate == 'signed':
        second.append('a signature on %s'
                      % ('every rule' if cfg.get('sign_at') == 'all'
                         else 'every rule whose bar is strong'))
        if summary.get('stale'):
            second.append('%d signatures stale' % summary['stale'])
    lines.append(', '.join(second) + '.')
    lines.extend(_list_lines(data, gate))
    return lines


def _list_lines(data, gate):
    """The two counts a person acts on: the Review tab, then the Sign tab."""
    lines = []
    if gate == 'passed':
        return lines
    review = len(data.get('review_list') or ())
    lines.append('%d rule%s to review.' % (review, '' if review == 1 else 's'))
    if gate == 'signed':
        sign = len(data.get('sign_list') or ())
        lines.append('%d rule%s to sign.' % (sign, '' if sign == 1 else 's'))
    return lines


def _blocking(data):
    """`{cell_name: {word: count}}` over the rules that do not meet the gate.

    Only a rule's own entry is counted, so a global anchor's rule is counted
    once however many features have to prove it.
    """
    found = {'spec': 0}
    for name in states.CELLS:
        found[name] = {}
    for feature in data['features']:
        for rule in feature.get('rules') or ():
            if rule.get('label') != 'own' or rule.get('meets_gate'):
                continue
            blocked = rule.get('blocked_by')
            if blocked == 'spec':
                found['spec'] += 1
            elif blocked in found:
                word = ((rule.get('cells') or {}).get(blocked) or {}).get('word')
                found[blocked][word] = found[blocked].get(word, 0) + 1
    return found


NO_AUDIT = 'no audit has run'


def _unaudited(data):
    """How many rules no audit has measured yet.

    A weak rule is build work, and that is what the next step says, unless
    nothing has run the breaks over it at all: then the work is the audit,
    not the build, and telling a reader to build would send them at the
    wrong thing.
    """
    return (data.get('summary') or {}).get('not_audited') or 0


def _directives(data, project_root):
    """The next step, computed from the blocking cell, plus anything to fix first."""
    lines = []
    if (any('purlin:init --update' in warning for warning in data['warnings'])
            or _update_pending(project_root)):
        lines.append('%s Run: purlin:init --update' % ARROW)

    gate = data['gate']['gate']
    blocked = _blocking(data)
    passed = blocked['passed']
    strong = blocked['strong']

    no_test = passed.get('no test', 0)
    failing = passed.get('failed', 0)
    partial = passed.get('partial', 0)
    waiting = passed.get('not run', 0) + passed.get('code changed', 0)
    weak = strong.get('weak', 0)
    unaudited = _unaudited(data)
    person = len(data.get('review_list') or ()) + len(
        data.get('sign_list') or ())

    if blocked['spec']:
        lines.append('%s Next: run purlin:spec. %d rules have no proof that '
                     'clears the free checks.' % (ARROW, blocked['spec']))
    elif failing:
        lines.append('%s Next: run purlin:build. %d rules have a failing test.'
                     % (ARROW, failing))
    elif partial:
        lines.append('%s Next: run purlin:build. %d rules are partial; their '
                     'tests pass on one operating system and not on another.'
                     % (ARROW, partial))
    elif no_test:
        lines.append('%s Next: run purlin:build. %d rules have a proof and no '
                     'passing test.' % (ARROW, no_test))
    elif waiting and gate == 'signed':
        # A push of this branch starts nothing: CI runs on a pull request, on
        # the protected branch and on a run branch. `--remote` is what gets a
        # record that counts onto this branch before the merge, and under
        # `signed` CI's is the only record that counts.
        lines.append('%s Next: run purlin:test --remote. %d rules are waiting '
                     'for the record CI writes, which is the only one that '
                     'counts under signed.' % (ARROW, waiting))
    elif waiting and gate == 'strong':
        # Either source counts here, so the shortest way to a record is the
        # audit on this machine.
        lines.append('%s Next: run purlin:audit. %d rules have no record to '
                     'read, and an audit you run counts under strong.'
                     % (ARROW, waiting))
    elif waiting:
        lines.append('%s Next: run purlin:test. %d rules have no run to read.'
                     % (ARROW, waiting))
    elif unaudited:
        lines.append('%s Next: run purlin:audit. %d rules have no audit, so '
                     'nothing has measured how good their tests are.'
                     % (ARROW, unaudited))
    elif weak:
        lines.append('%s Next: run purlin:build. %d rules are weak; the strong '
                     'cell names what each one is short of.' % (ARROW, weak))
    elif person:
        lines.append('%s Next: run purlin:sign. %d rules are waiting for a '
                     'person.' % (ARROW, person))
    else:
        lines.append('%s Next: nothing is outstanding at gate %s.' % (ARROW, gate))

    if data.get('review_list') or data.get('sign_list'):
        lines.append('%s Review list: %s. Run purlin:sign.'
                     % (ARROW, board_module.needs_a_person(
                         len(data.get('review_list') or ())
                         + len(data.get('sign_list') or ()))))
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
