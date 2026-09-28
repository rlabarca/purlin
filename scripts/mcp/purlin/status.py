"""The status table: one row per spec, one cell per evidence level.

The table is the dashboard's board, rendered as text. Its columns are the
board's columns and its cells are the board's cells, character for character,
because a reader who learns one should not have to learn the other:
`purlin:purlin.board` renders both. A row says how many rules the spec has,
how many proofs it writes and how many of those have no test, and how many
rules pass their tests. At `strong` the row adds how many rules are strong
and the test strength; at `signed` it adds how many are signed. The table scales with the gate: a `passed` project is never shown
a strength, a level or a signature it did not ask for.

Copy follows `references/writing_style.md`: sentence case, second person for what you
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
                    gate as gate_module, payload as payload_module,
                    report_data, specs as specs_module, states)

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
    # The dashboard reads what the table reads: every command that ends on
    # this table refreshes the page's data file with the same payload.
    report_data.refresh(project_root, data)
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

    Imported here rather than at the top, so a project that is already on
    this release pays nothing for the question. Whatever goes wrong while
    asking it, the table is still printed.
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
    second = [board_module.count_of(summary['features'], 'feature'),
              board_module.proofs_summary(summary)]
    if gate != 'passed':
        if cfg.get('min_strength') is not None:
            second.append('minimum test strength %d%%' % cfg['min_strength'])
        if summary.get('manual'):
            second.append('%d rules with a manual test' % summary['manual'])
        if summary.get('not_audited'):
            second.append('%d rules not audited' % summary['not_audited'])
    if gate == 'signed':
        second.append('a signature on every rule whose level is signed')
        if summary.get('stale'):
            second.append('%s stale'
                          % board_module.count_of(summary['stale'],
                                                  'signature'))
    lines.append(', '.join(second) + '.')
    if gate != 'passed':
        lines.append(board_module.queue_line(summary))
    above = marked_above_the_gate(data)
    if above:
        lines.append(above_the_gate_line(above, gate))
    names = incomplete_names(data)
    if names:
        lines.append(incomplete_line(names))
    return lines


def incomplete_names(data):
    """The feature specs that name no files, sorted. Anchors are never one."""
    return sorted(feature['name'] for feature in data['features']
                  if feature.get('incomplete'))


def incomplete_line(names):
    """`1 spec names no files, so its tests run every time: export.`"""
    if len(names) == 1:
        return ('1 spec names no files, so its tests run every time: %s.'
                % names[0])
    return ('%d specs name no files, so their tests run every time: %s.'
            % (len(names), ', '.join(names)))


def marked_above_the_gate(data):
    """How many rules carry a `[level: ...]` tag above the project's gate.

    The gate is the ceiling, so such a rule is read as the gate. Each rule is
    counted once, under the feature that owns it.
    """
    gate = data['gate']['gate']
    ceiling = gate_module.GATES.index(gate)
    count = 0
    for feature in data['features']:
        for rule in feature.get('rules') or ():
            if rule.get('label') != 'own':
                continue
            marked = rule.get('level_marked')
            if marked in gate_module.GATES and (
                    gate_module.GATES.index(marked) > ceiling):
                count += 1
    return count


def above_the_gate_line(count, gate):
    """`<n> rules are marked above the gate and are read as <gate>.`"""
    if count == 1:
        return '1 rule is marked above the gate and is read as %s.' % gate
    return ('%d rules are marked above the gate and are read as %s.'
            % (count, gate))


def _blocking(data):
    """`{cell_name: {word: count}}` over the rules that do not meet the gate.

    Only a rule's own entry is counted, so a global anchor's rule is counted
    once however many features have to prove it.
    """
    found = {'no_proof': 0}
    for name in states.CELLS:
        found[name] = {}
    for feature in data['features']:
        for rule in feature.get('rules') or ():
            if rule.get('label') != 'own' or rule.get('meets_gate'):
                continue
            blocked = rule.get('blocked_by')
            cells = rule.get('cells') or {}
            waits_for_a_proof = (
                ((cells.get('passed') or {}).get('reasons') or ())
                == [states.NO_PROOF_WRITTEN]
                or (cells.get('strong') or {}).get('word') == states.NO_PROOF)
            if (rule.get('flags') or {}).get('no_proof') and waits_for_a_proof:
                # A rule with neither a proof nor a test marked with its id
                # reads `no test`, and one whose test passes above the gate
                # `passed` reads `no proof`: what either waits for is a
                # proof, not a build. A rule whose own marked test fails is
                # build work like any other.
                found['no_proof'] += 1
            elif blocked in found:
                word = ((rule.get('cells') or {}).get(blocked) or {}).get('word')
                found[blocked][word] = found[blocked].get(word, 0) + 1
    return found


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
    trust = data['gate'].get('trust')
    blocked = _blocking(data)
    passed = blocked['passed']
    strong = blocked['strong']

    no_test = passed.get('no test', 0)
    failing = passed.get('failed', 0)
    partial = passed.get('partial', 0)
    waiting = passed.get('not run', 0) + passed.get('out of date', 0)
    weak = strong.get('weak', 0)
    unaudited = _unaudited(data)
    person = len(data.get('queue') or ())

    if blocked['no_proof']:
        lines.append('%s Next: run purlin:spec. %d rules have no proof line '
                     'naming them.' % (ARROW, blocked['no_proof']))
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
    elif waiting and trust == 'remote':
        # This project said it does not trust this machine for the tests a
        # signature rests on, so the run that clears these rules is the
        # runner's. It is the only case in which a person is sent there.
        lines.append('%s Next: run purlin:test --remote. %d rules are waiting '
                     'for a ci run, which is what this project signs on.'
                     % (ARROW, waiting))
    elif waiting and gate != 'passed':
        # Evidence either source wrote counts at every gate, so the shortest
        # way to it is the audit on this machine, which runs the tests too.
        lines.append('%s Next: run purlin:audit. %d rules have no current run '
                     'to read, and an audit you run counts at gate %s.'
                     % (ARROW, waiting, gate))
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
    elif gate == 'signed' and incomplete_names(data):
        # A signature needs a spec tied to its files, so what the rest of
        # the gate waits on is the `> Scope:` line.
        name = incomplete_names(data)[0]
        lines.append('%s Next: run purlin:spec %s. It names no files in '
                     '> Scope:, so its rules cannot be signed.'
                     % (ARROW, name))
    else:
        lines.append('%s Next: nothing is outstanding at gate %s.' % (ARROW, gate))

    if person:
        lines.append('%s Queue: %s. Run purlin:sign.'
                     % (ARROW, board_module.needs_a_person(person)))
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
