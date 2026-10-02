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
not written yet, and the anchors whose pin is not current, then the warnings,
the last of them the one for the markers Purlin 0.9.5 wrote that are still in
a test: its opening line, one line per test with the feature and the rule the
marker names, and what to do. The dashboard's data carries that warning as
one line. The report ends on the summary sentence, `Left to do` and the last
line, with `→ Run: purlin:init --update` above them while an upgrade is
pending. Where every rule passes and `purlin:sign` would refuse the results
as they stand, the last line names the run to make first
(`facts.results_to_retake`).

The status of a project Purlin 0.9.5 set up, while its upgrade is pending, is
three lines, and it writes no file: the dashboard page and its data file stay
as they are until the project is brought to this version.

Copy follows `references/writing_style.md`: sentence case, second person for what you
do, third person for what Purlin does, exact numbers, and the only glyphs are
`->`, `>` and `v` in their unicode forms. No emoji, anywhere.
"""

import io
import os
import re
import subprocess
import sys
import tokenize

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from config_engine import config_problem
from purlin import (board as board_module, drift as drift_module,
                    fingerprint as fingerprint_module,
                    markers as markers_module,
                    payload as payload_module,
                    project as project_module, report_data,
                    specs as specs_module, summary as summary_module)

ARROW = '→'
DOT = board_module.DOT

# An anchor rule whose proof found nothing to check: the anchor, the rule,
# the reason after `nothing to check: `.
NOTHING_LINE = '%s %s passes with nothing to check here: %s.'

# What the status says, after its first line, of a project Purlin 0.9.5 set
# up while its upgrade is pending.
PENDING = ('This project was set up by Purlin 0.9.5. Nothing here counts '
           'until it is brought to %s.')

# What the status says once where the `tests` setting changed since the
# evidence was taken (`fingerprint.setting_changed`).
SETTING_CHANGED = 'The tests setting changed, so every result is out of date.'

# What the status says while a tracked test file still holds a marker Purlin
# 0.9.5 wrote, where that release read it. In the terminal: the count, one
# line per test, `OLD_MARKERS_SHOWN` of them and then the rest counted, and
# what to do. In the dashboard's data: one line.
OLD_MARKER_ONE = '1 test still carries'
OLD_MARKER_MANY = '%d tests still carry'
OLD_MARKERS_OPEN = '%s a marker from Purlin 0.9.5, which is not read:'
OLD_MARKERS_SHOWN = 20
OLD_MARKERS_MORE = '  and %d more'
OLD_MARKERS_DO = ('For each, write the proof with purlin:spec, put the '
                  'comment above the test, and take the old tag out.')
OLD_MARKERS_DATA = ('%s a marker from Purlin 0.9.5, which is not read. Run '
                    'purlin:status to see each.')

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
    if (project_module.set_up_by_095(project_root)
            and _update_pending(project_root)):
        # Nothing is read and nothing is written: the page and the data file
        # the project holds are the ones its own release wrote.
        return '\n'.join(pending_lines(project_root))
    data = payload_module.build_payload(project_root, generated_by='sync_status')
    warnings = list(data['warnings'])
    old = _old_markers_found(project_root)
    if old:
        # The last of the warnings, so it reads nearest `Left to do`; the
        # dashboard shows it as a notice, one line, from the same list.
        data['warnings'].append(old_marker_line(old))
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
    if fingerprint_module.setting_changed(project_root):
        lines.append('')
        lines.append(SETTING_CHANGED)

    pin_lines = _pin_lines(project_root)
    if pin_lines:
        lines.append('')
        lines.extend(pin_lines)

    uncommitted = _uncommitted_specs(project_root)
    if uncommitted:
        lines.append('')
        lines.append('Uncommitted spec changes:')
        lines.extend('  ' + line for line in uncommitted)

    if warnings or old:
        lines.append('')
        lines.extend(warnings)
        lines.extend(old_marker_lines(old))

    lines.append('')
    lines.extend(ending_lines(data, project_root))
    return '\n'.join(lines)


def pending_lines(project_root):
    """The whole status of a project Purlin 0.9.5 set up, while its
    upgrade is pending: the first line, then what set the project up, that
    nothing counts yet, and the command.

    No table, no warning and no `Left to do`: none of them means anything
    until the project is brought to this version.
    """
    version = payload_module.PURLIN_VERSION
    return [summary_module.OPENING % (
                project_module.project_name(project_root), version),
            PENDING % version,
            '%s Run: purlin:init --update' % ARROW]


def _update_module():
    """`scripts/init/update.py`, the one home of what Purlin 0.9.5 wrote.

    Imported when asked for rather than at the top: the update imports this
    package.
    """
    import importlib
    init_dir = os.path.join(os.path.dirname(_MCP_DIR), 'init')
    if init_dir not in sys.path:
        sys.path.insert(0, init_dir)
    return importlib.import_module('update')


def _update_pending(project_root):
    """True while `purlin:init --update` still has migrations to apply.

    Whatever goes wrong while asking it, the table is still printed.
    """
    try:
        return bool(_update_module().pending(project_root))
    except Exception:                       # noqa: BLE001 - never block status
        return False


# ---------------------------------------------------------------------------
# The markers Purlin 0.9.5 wrote that are still in a test
# ---------------------------------------------------------------------------

_OLD_TOKENS = ('[proof:', 'pytest.mark.proof')


def _tracked(project_root):
    """Every path git tracks under the root, or [] where git cannot say."""
    try:
        listed = subprocess.run(['git', 'ls-files', '-z'], cwd=project_root,
                                capture_output=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    if listed.returncode != 0:
        return []
    return [raw.decode('utf-8', 'replace')
            for raw in listed.stdout.split(b'\0') if raw]


def _proof_mark_lines(text):
    """The lines of a Python file on which `pytest.mark.proof` is code, not
    words in a comment or a docstring; None where the file cannot be read
    as Python."""
    names, lines = [], set()
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type in (tokenize.NAME, tokenize.OP):
                names.append(token.string)
                if names[-5:] == ['pytest', '.', 'mark', '.', 'proof']:
                    lines.add(token.start[0])
            elif token.type not in (tokenize.NL, tokenize.COMMENT):
                names.append('')
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return None
    return lines


# The feature and the rule an old marker names, read from the marker itself:
# a title tag's first and third fields, a mark's first and third arguments.
_OLD_TAG_RULE_RE = re.compile(r':(RULE-\d+)[:\]]')
_OLD_MARK_RE = re.compile(
    r"pytest\.mark\.proof\(\s*[\"']([^\"']+)[\"']"
    r"(?:\s*,\s*[\"'][^\"']*[\"'](?:\s*,\s*[\"'](RULE-\d+)[\"'])?)?")


def _line_start(text, line):
    """The offset at which line `line` of `text`, counted from 1, starts."""
    offset = 0
    for _ in range(line - 1):
        offset = text.find('\n', offset) + 1
        if not offset:
            return len(text)
    return offset


def _named(text, ext, line, pair):
    """`(feature, rule)` as the old marker at `line` names them, each None
    where the marker does not name it."""
    start = _line_start(text, line)
    if ext == '.py':
        mark = _OLD_MARK_RE.search(text, start)
        if mark is None or text.count('\n', start, mark.start()):
            return (pair[0] if pair else None), None
        return mark.group(1), mark.group(2)
    if not pair:
        return None, None
    tag = '[proof:%s:%s' % pair
    at = text.find(tag, start)
    if at < 0:
        return pair[0], None
    rule = _OLD_TAG_RULE_RE.match(text, at + len(tag))
    return pair[0], rule.group(1) if rule else None


def old_markers(project_root):
    """`(file, line, feature, rule)` for each 0.9.5 marker a tracked test
    file still holds where that release read it, sorted by file then line: a
    tag in a test's title, or a `pytest.mark.proof` mark.

    `line` is the line the tag or the mark is on in the file as it stands.
    `feature` and `rule` are read from the marker itself, each None where it
    does not name one. `purlin:init --update`'s own reader finds the places
    (`update.rewrite_markers`), so the status names the markers the upgrade
    leaves. A tag in a comment, in a docstring or in a string that is no
    test's title is not one.
    """
    update = _update_module()
    found = {}
    for rel in _tracked(project_root):
        ext = os.path.splitext(rel)[1].lower()
        if ext == '.py':
            wanted = _OLD_TOKENS[1:]
        elif ext in update.TEST_EXTENSIONS and ext not in (
                '.sh', '.bash', '.sql', '.cs'):
            wanted = _OLD_TOKENS[:1]
        else:
            continue
        try:
            path = os.path.join(project_root, rel)
            with open(path, encoding='utf-8', newline='') as handle:
                text = handle.read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if not any(token in text for token in wanted):
            continue
        left = update.rewrite_markers(text, ext)[2]
        if ext != '.py':
            # A tag counts where the test run's own reader finds it in a
            # test's title. The update also names a tag it leaves in any
            # other string, which no release read.
            titles = [test.name for test in markers_module.js_tests(text)]
            left = [entry for entry in left if entry[1] is not None
                    and any('[proof:%s:%s:' % entry[1] in title
                            for title in titles)]
        elif left:
            code = _proof_mark_lines(text)
            if code is not None:
                left = [entry for entry in left if entry[0] in code]
        for line, pair in left:
            if (rel, line) not in found:
                found[(rel, line)] = _named(text, ext, line, pair)
    return [place + found[place] for place in sorted(found)]


def _old_markers_found(project_root):
    """`old_markers`, or [] whatever goes wrong while looking: the status is
    still printed."""
    try:
        return old_markers(project_root)
    except Exception:                       # noqa: BLE001 - never block status
        return []


def _old_marker_opening(found):
    return (OLD_MARKER_ONE if len(found) == 1
            else OLD_MARKER_MANY % len(found))


def old_marker_line(found):
    """The warning for the 0.9.5 markers `old_markers` found, as the one
    line the dashboard's data carries."""
    return OLD_MARKERS_DATA % _old_marker_opening(found)


def old_marker_lines(found):
    """The same warning as the terminal prints it, or [] with none found:
    the count, one line per test, `<file>:<line>` then the feature and the
    rule its marker names, the first `OLD_MARKERS_SHOWN` and then the rest
    counted, and what to do."""
    if not found:
        return []
    lines = [OLD_MARKERS_OPEN % _old_marker_opening(found)]
    for rel, line, feature, rule in found[:OLD_MARKERS_SHOWN]:
        named = ' '.join(word for word in (feature, rule) if word)
        lines.append(('  %s:%d  %s' % (rel, line, named)).rstrip())
    if len(found) > OLD_MARKERS_SHOWN:
        lines.append(OLD_MARKERS_MORE % (len(found) - OLD_MARKERS_SHOWN))
    lines.append(OLD_MARKERS_DO)
    return lines


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

# The label lines of the table's two groups, where the project has an anchor.
ANCHORS = 'Anchors'
SPECS = 'Specs'


def _row(feature, proofs=1, audited=False):
    """One spec's row, rendered by the module the board renders from."""
    return board_module.row_cells(feature['name'], feature['rollup'],
                                  proofs, audited,
                                  bool(feature.get('is_anchor')))


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
