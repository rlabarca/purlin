"""The status table: one row per feature, one cell per evidence level.

A row says how many rules the feature has, what its specs say about them, how
many rules pass their tests, and what the latest record was. At `strong` the
row adds the test strength and how many rules are strong; at `signed` it adds
how many are signed. The table scales with the gate: a `passed` project is
never shown a strength, a risk or a signature it did not ask for.

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
DOT = ' · '

BASE_COLUMNS = ('Feature', 'Rules', 'Spec', 'Tests', 'Run')
STRONG_COLUMNS = ('Strength', 'Strong')
SIGNED_COLUMNS = ('Signed',)

NO_SPECS = ('No specs found under specs/.\n'
            '%s Run: purlin:init to set this project up, or purlin:spec to '
            'write the first one.' % ARROW)


def columns_for(gate):
    """The table's columns under `gate`, left to right."""
    columns = list(BASE_COLUMNS)
    if gate in ('strong', 'signed'):
        columns.extend(STRONG_COLUMNS)
    if gate == 'signed':
        columns.extend(SIGNED_COLUMNS)
    return tuple(columns)


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

def _cell_words(feature, name):
    """`{word: count}` over one cell of every rule the feature must prove."""
    counts = {}
    for rule in feature.get('rules') or ():
        cell = (rule.get('cells') or {}).get(name)
        if not cell:
            continue
        word = cell.get('word')
        counts[word] = counts.get(word, 0) + 1
    return counts


def _met_count(feature, name):
    """How many of a feature's rules meet one cell."""
    return sum(1 for rule in feature.get('rules') or ()
               if states.cell_is_met(name, (rule.get('cells') or {}).get(name)))


def _row(feature, gate):
    rollup = feature['rollup']
    name = feature['name'] + (' (anchor)' if feature['is_anchor'] else '')
    total = rollup['rules']

    drafted = sum(1 for rule in feature.get('rules') or ()
                  if rule.get('spec') == states.DRAFTED)
    spec_cell = '%d ready%s%d drafted' % (total - drafted, DOT, drafted)

    words = _cell_words(feature, 'passed')
    tests_cell = '%d passed%s%d failing%s%d no test' % (
        words.get('passed', 0), DOT, words.get('failed', 0), DOT,
        total - words.get('passed', 0) - words.get('failed', 0))

    record = feature.get('latest_record') or {}
    run_cell = record.get('label') or 'none'
    if record.get('os'):
        run_cell = '%s %s' % (run_cell, record['os'])

    cells = [name, str(total), spec_cell, tests_cell, run_cell]
    if gate in ('strong', 'signed'):
        strength = rollup.get('test_strength')
        cells.append('n/a' if strength is None else '%d%%' % int(strength))
        cells.append('%d of %d' % (_met_count(feature, 'strong'), total))
    if gate == 'signed':
        cells.append('%d of %d' % (_met_count(feature, 'signed'), total))
    return tuple(cells)


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
             if name in ('Rules', 'Strength')}
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
    lines = ['%d of %d rules meet the gate %s.'
             % (summary['met'], summary['rules'], gate)]
    second = ['%d features' % summary['features']]
    if summary.get('failing'):
        second.append('%d failing' % summary['failing'])
    if gate != 'passed':
        if cfg.get('min_strength') is not None:
            second.append('minimum test strength %d%%' % cfg['min_strength'])
        if cfg['ai_review_at'] != 'never':
            second.append('review at risk %s and above' % cfg['ai_review_at'])
        if summary.get('manual'):
            second.append('%d rules with a manual test' % summary['manual'])
        if summary.get('audit'):
            second.append('%d rules with a manual audit' % summary['audit'])
        if summary.get('held'):
            second.append('%d rules held' % summary['held'])
    if gate == 'signed':
        if cfg.get('sign_at'):
            second.append('a signature at risk %s and above' % cfg['sign_at'])
        if summary.get('stale'):
            second.append('%d signatures stale' % summary['stale'])
    lines.append(', '.join(second) + '.')
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
    signed = blocked['signed']

    no_test = passed.get('no test', 0)
    failing = passed.get('failed', 0)
    waiting = passed.get('not run', 0) + passed.get('code changed', 0)
    weak = strong.get('weak', 0)
    person = (strong.get('manual test', 0) + strong.get('manual audit', 0)
              + strong.get('held', 0) + signed.get('unsigned', 0)
              + signed.get('stale', 0) + signed.get('held', 0))

    if blocked['spec']:
        lines.append('%s Next: run purlin:spec. %d rules have no proof that '
                     'clears the free checks.' % (ARROW, blocked['spec']))
    elif failing:
        lines.append('%s Next: run purlin:build. %d rules have a failing test.'
                     % (ARROW, failing))
    elif no_test:
        lines.append('%s Next: run purlin:build. %d rules have a proof and no '
                     'passing test.' % (ARROW, no_test))
    elif waiting and gate != 'passed':
        lines.append('%s Next: push the branch. %d rules are waiting for CI to '
                     'write the record that counts under %s.'
                     % (ARROW, waiting, gate))
    elif waiting:
        lines.append('%s Next: run purlin:test. %d rules have no run to read.'
                     % (ARROW, waiting))
    elif weak:
        lines.append('%s Next: run purlin:build. %d rules are weak; the strong '
                     'cell names what each one is short of.' % (ARROW, weak))
    elif person:
        lines.append('%s Next: run purlin:sign. %d rules are waiting for a '
                     'person.' % (ARROW, person))
    else:
        lines.append('%s Next: nothing is outstanding at gate %s.' % (ARROW, gate))

    if data['review_list']:
        lines.append('%s Review list: %d rules need a person. Run purlin:sign.'
                     % (ARROW, len(data['review_list'])))
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
