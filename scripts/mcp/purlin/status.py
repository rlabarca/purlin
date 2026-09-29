"""The status table: one row per spec, one cell per step.

The table is the dashboard's board, rendered as text. Its columns are the
board's columns and its cells are the board's cells, character for character,
because a reader who learns one should not have to learn the other:
`scripts/mcp/purlin/board.py` renders both. A row says how many rules the
spec owns and how many it proves from an anchor, as `15 (+6 shared)`, how
many proofs it writes and how many of those have no test, and how many rules
pass their tests. At `strong` the row adds how many rules are
strong and the test strength; at `signed` it adds how many are signed. The
table scales with the gate: a `passed` project is never shown a strength or a
signature it did not ask for, and is shown a proof count only where it writes
a proof line.

The report ends on the summary sentence and `Left to do`, which
`scripts/mcp/purlin/summary.py` writes for every surface, with `→ Run:
purlin:init --update` above them while an upgrade is pending.

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

from config_engine import config_problem
from purlin import (board as board_module, drift as drift_module,
                    payload as payload_module, report_data,
                    specs as specs_module, summary as summary_module)

ARROW = '→'
DOT = board_module.DOT

NO_SPECS = ('No specs found under specs/.\n'
            '%s Run: purlin:init to set this project up, or purlin:spec to '
            'write the first one.' % ARROW)


def columns_for(gate, proofs=1):
    """The table's columns under `gate`, left to right: the board's own."""
    return board_module.columns_for(gate, proofs)


def sync_status(project_root):
    """The whole status report for a project root, as text.

    A settings file that cannot be read stops it before anything is read or
    written: the report is that one sentence.
    """
    problem = config_problem(project_root)
    if problem:
        return problem
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
    names = incomplete_names(data)
    if names:
        lines.append('')
        lines.append(incomplete_line(names))

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
    lines.extend(ending_lines(data, project_root))
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

def _row(feature, gate, proofs=1):
    """One spec's row, rendered by the module the board renders from."""
    name = feature['name'] + (' (anchor)' if feature['is_anchor'] else '')
    return board_module.row_cells(
        name, feature['rollup'], gate, proofs,
        board_module.shared_counts(feature.get('rules')))


def _proof_lines(data):
    """How many proof lines the project writes."""
    return (data.get('summary') or {}).get('proofs') or 0


def _table(data):
    gate = data['gate']['gate']
    proofs = _proof_lines(data)
    columns = columns_for(gate, proofs)
    # The feature with the most rules left to do reads first: the table
    # opens on the work rather than on the alphabet.
    features = sorted(data['features'],
                      key=lambda f: (-_left_count(f), f['name']))
    rows = [_row(feature, gate, proofs) for feature in features]
    widths = [max(len(columns[i]), max((len(r[i]) for r in rows), default=0))
              for i in range(len(columns))]
    rule = '─' * (sum(widths) + 2 * (len(widths) - 1))
    lines = [_line(columns, widths, columns), rule]
    lines.extend(_line(row, widths, columns) for row in rows)
    lines.append(rule)
    return lines


def _left_count(feature):
    """How many of the rules a feature lists wait for some kind of work."""
    return sum(1 for rule in feature.get('rules') or () if rule.get('left'))


def _line(cells, widths, columns):
    """One table line, every cell set from its column's left edge.

    A `Rules` cell reads `15 (+6 shared)` beside one that reads `6`, and
    a count and its words line up only from the left, as they do on the
    board.
    """
    return '  '.join(cell.ljust(widths[index])
                     for index, cell in enumerate(cells)).rstrip()


# ---------------------------------------------------------------------------
# The specs that name no files, and the ending
# ---------------------------------------------------------------------------

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


def ending_lines(data, project_root):
    """`→ Run: purlin:init --update` where an upgrade is pending, then the summary.

    The lines every command that ends as the status ends prints last.
    """
    lines = []
    if (any('purlin:init --update' in warning for warning in data['warnings'])
            or _update_pending(project_root)):
        lines.append('%s Run: purlin:init --update' % ARROW)
    lines.append(summary_module.ending(data))
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
