"""The status report: the two facts, one row per spec, and what is left.

The report opens on three lines, the project and the two facts, which
`scripts/mcp/purlin/summary.py` writes for every surface:

    Purlin status: labconnect, plugin 0.10.0
    Tests: not met
    Sign-off: signed 0.1.0, 4 commits since

The table is the dashboard's board, rendered as text. Its columns are the
board's columns and its cells are the board's cells, character for character,
because a reader who learns one should not have to learn the other:
`scripts/mcp/purlin/board.py` renders both. A row says how many rules the
spec has, how many proofs it writes and how many of those have no test, and
how many rules pass their tests. Where the project has an anchor, the line
`Anchors` heads the anchors' rows and the line `Specs` every other spec's,
as the dashboard lists anchors above the spec table. Where any rule has an
audit entry, the row adds how many rules the audit found strong. A project is
shown a proof count only where it writes a proof line.

Below the table come each anchor rule that passes with nothing to check here,
the specs that name no files, one line per spec whose `> Scope:` names files
not written yet, and the anchors whose pin is not current. The report ends on
the summary sentence, `Left to do` and the last line, with `→ Run:
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
                    fingerprint as fingerprint_module,
                    payload as payload_module, report_data,
                    specs as specs_module, summary as summary_module)

ARROW = '→'
DOT = board_module.DOT

# An anchor rule whose proof found nothing to check: the anchor, the rule,
# the reason after `nothing to check: `.
NOTHING_LINE = '%s %s passes with nothing to check here: %s.'

# A spec ahead of its code: one line for the spec, as information.
NOT_WRITTEN_ONE = ('%s: 1 file its scope names is not written yet: %s. Run purlin:build %s, '
                   'or correct the path with purlin:spec %s.')
NOT_WRITTEN_MANY = ('%s: %d files its scope names are not written yet: %s. Run purlin:build '
                    '%s, or correct the path with purlin:spec %s.')

# What a tree holds that counts as code, for a project with no spec yet: a
# file git lists, tracked or not ignored, outside these folders, with one of
# these extensions.
_NOT_CODE_FOLDERS = ('specs/', '.purlin/', '.github/', 'docs/')
_CODE_EXTENSIONS = frozenset(
    '.py .pyi .js .jsx .mjs .cjs .ts .tsx .cs .fs .vb .go .java .kt .rb .php '
    '.rs .swift .c .h .cc .cpp .hpp .m .scala .sql .sh .ps1'.split())


def _holds_code(project_root):
    """True when the tree holds a file of code outside the folders above."""
    try:
        listed = subprocess.run(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard',
             '-z'], cwd=project_root, capture_output=True, check=False)
    except OSError:
        return False
    if listed.returncode != 0:
        return False
    for raw in listed.stdout.split(b'\0'):
        path = raw.decode('utf-8', 'replace')
        if not path or path.startswith(_NOT_CODE_FOLDERS):
            continue
        if os.path.splitext(path)[1] in _CODE_EXTENSIONS:
            return True
    return False


def no_spec_lines(project_root):
    """The two lines every surface prints for a project with no spec.

    The second names the next step by the state of the project: not set up,
    set up over code, or set up over no code.
    """
    if not os.path.isfile(os.path.join(project_root, '.purlin', 'config.json')):
        second = '%s Run: purlin:init to set this project up.' % ARROW
    elif _holds_code(project_root):
        second = ('%s Run: purlin:spec-from-code to write the specs this code '
                  'already implies.' % ARROW)
    else:
        second = '%s Run: purlin:spec <name> to write the first spec.' % ARROW
    return ['No specs found under specs/.', second]


def columns_for(proofs=1, audited=False):
    """The table's columns, left to right: the board's own."""
    return board_module.columns_for(proofs, audited)


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
        return '\n'.join(no_spec_lines(project_root))

    lines = summary_module.opening(data)
    lines.append('')
    lines.extend(_table(data))
    nothing = nothing_lines(data)
    if nothing:
        lines.append('')
        lines.extend(nothing)
    names = incomplete_names(data)
    information = data.get('information') or []
    if names or information:
        lines.append('')
    if names:
        lines.append(incomplete_line(names))
    lines.extend(information)

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

# The label lines of the table's two groups, where the project has an anchor.
ANCHORS = 'Anchors'
SPECS = 'Specs'


def _row(feature, proofs=1, audited=False):
    """One spec's row, rendered by the module the board renders from."""
    return board_module.row_cells(feature['name'], feature['rollup'],
                                  proofs, audited)


def _proof_lines(data):
    """How many proof lines the project writes."""
    return (data.get('summary') or {}).get('proofs') or 0


def _table(data):
    proofs = _proof_lines(data)
    audited = board_module.shows_strong(
        (data.get('summary') or {}).get('audit'), data.get('features'))
    columns = columns_for(proofs, audited)
    # The feature with the most rules left to do reads first: the table
    # opens on the work rather than on the alphabet.
    features = sorted(data['features'],
                      key=lambda f: (-_left_count(f), f['name']))
    anchors = [_row(f, proofs, audited)
               for f in features if f.get('is_anchor')]
    specs = [_row(f, proofs, audited)
             for f in features if not f.get('is_anchor')]
    rows = anchors + specs
    widths = [max(len(columns[i]), max((len(r[i]) for r in rows), default=0))
              for i in range(len(columns))]
    rule = '─' * (sum(widths) + 2 * (len(widths) - 1))
    lines = [_line(columns, widths, columns), rule]
    if anchors:
        # The anchors first, under their label line, then every other spec
        # under its own; with no anchor there is no label line.
        lines.append(ANCHORS)
        lines.extend(_line(row, widths, columns) for row in anchors)
        lines.append(SPECS)
    lines.extend(_line(row, widths, columns) for row in specs)
    lines.append(rule)
    return lines


def _left_count(feature):
    """How many of the rules a feature lists wait for some kind of work."""
    return sum(1 for rule in feature.get('rules') or () if rule.get('left'))


def _line(cells, widths, columns):
    """One table line, every cell set from its column's left edge.

    A `Tests` cell reads `12 of 14 · 1 failing` beside one that reads
    `11 of 11`, and a count and its words line up only from the left, as they
    do on the board.
    """
    return '  '.join(cell.ljust(widths[index])
                     for index, cell in enumerate(cells)).rstrip()


# ---------------------------------------------------------------------------
# The specs that name no files, and the ending
# ---------------------------------------------------------------------------

def incomplete_names(data):
    """The feature specs with no `> Scope:` line, sorted. Anchors are never one."""
    return sorted(feature['name'] for feature in data['features']
                  if feature.get('incomplete')
                  and feature.get('incomplete_reason')
                  == fingerprint_module.NO_SCOPE_LINE)


def incomplete_line(names):
    """The one line for the feature specs that name no files, with its step.

    The status prints it, and so does the upgrade.
    """
    if len(names) == 1:
        return ('1 spec names no files, so its tests run every time: %s. Run '
                'purlin:spec %s to add its > Scope: line.'
                % (names[0], names[0]))
    return ('%d specs name no files, so their tests run every time: %s. Run '
            'purlin:spec with each name to add its > Scope: line.'
            % (len(names), ', '.join(names)))


def nothing_lines(data):
    """`NOTHING_LINE` for each anchor rule that passes with nothing to check here."""
    lines = []
    for feature in data.get('features') or ():
        if not feature.get('is_anchor'):
            continue
        for rule in feature.get('rules') or ():
            passed = (rule.get('cells') or {}).get('passed') or {}
            if passed.get('word') != 'passed':
                continue
            for item in passed.get('nothing_to_check') or ():
                lines.append(NOTHING_LINE % (feature['name'], rule['id'],
                                             item['reason']))
    return lines


def not_written_lines(project_root, features):
    """One line per feature spec whose `> Scope:` names files git does not have.

    Writing a spec before its code is the normal order, so the line is
    information: it names the files, `purlin:build` to write them, then
    `purlin:spec` to correct a path. By spec name.
    """
    lines = []
    for name in sorted(features or {}):
        info = features[name]
        if info.get('is_anchor'):
            continue
        scope = [entry.strip() for entry in info.get('scope') or ()
                 if entry.strip()]
        if not scope:
            continue
        _files, unmatched = fingerprint_module.expand_scope(project_root, scope)
        if len(unmatched) == 1:
            lines.append(NOT_WRITTEN_ONE % (name, unmatched[0], name, name))
        elif unmatched:
            lines.append(NOT_WRITTEN_MANY % (name, len(unmatched),
                                             ', '.join(unmatched), name, name))
    return lines


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
        # An anchor whose source names no repository is read as any spec;
        # purlin:drift and the anchor check name it, and the status does not.
        if row.get('not_a_spec'):
            continue
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
            lines.append('%s: the source could not be read (%s). Check its '
                         '> Source: line, then run purlin:anchor sync %s.'
                         % (row['anchor'], row.get('error', 'unknown'),
                            row['anchor']))
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
