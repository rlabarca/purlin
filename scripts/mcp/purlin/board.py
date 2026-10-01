"""The columns every surface reads a spec's row from, rendered once.

The dashboard's board and the `purlin:status` table both answer the same
questions about one spec, and they have to answer them in the same
words: a reader who learns the board reads the table without learning it
again. So the columns and the cell text live here, and
each surface renders what this module returns rather than composing its own
string. `scripts/report/src/board.js` mirrors these
strings on the dashboard's side; changing one here changes the table.

The columns, left to right:

    Spec     the spec's name
    Rules    how many rules the spec has
    Proofs   how many proof lines it writes, and how many have no test;
             only where the project writes a proof line at all
    Tests    how many rules pass, and how many are partial or are failing
    Strong   how many of its rules the audit found strong, wherever the
             audit found any rule of the project strong or weak

Every when, who and platform detail lives in a hover on the dashboard and on
the rule screen; a cell here carries counts and nothing else.
"""

DOT = ' · '

# The five columns, left to right.
COLUMNS = ('Spec', 'Rules', 'Proofs', 'Tests', 'Strong')
STRONG_COLUMNS = ('Strong',)


def shows_proofs(proofs):
    """Whether the Proofs column and the proof count are shown.

    A project that writes no proof line is shown no count of them.
    """
    return bool(proofs)


def shows_strong(audit):
    """Whether the Strong column is shown: the audit found a rule strong or weak.

    `audit` is the payload's `summary.audit`. A project the audit has not
    read is shown no count of what it found.
    """
    audit = audit or {}
    return bool((audit.get('strong') or 0) + (audit.get('weak') or 0))


def columns_for(proofs=1, audited=False):
    """The columns, left to right.

    `proofs` is how many proof lines the project writes; `audited` is
    `shows_strong`'s answer.
    """
    columns = [name for name in COLUMNS[:4]
               if name != 'Proofs' or shows_proofs(proofs)]
    if audited:
        columns.extend(STRONG_COLUMNS)
    return tuple(columns)


def passing(rollup):
    """How many of a spec's rules pass their tests.

    A rule is counted in exactly one bucket, so the rules that pass are the
    ones left after the three that do not: untested, failing, and partial.
    Reading it this way means the four buckets always add up to the rule
    total.
    """
    total = rollup.get('rules') or 0
    short = sum(rollup.get(key) or 0
                for key in ('untested', 'failing', 'partial'))
    return max(total - short, 0)


def strong_met(rollup):
    """How many of a spec's rules the audit found strong."""
    return rollup.get('strong') or 0


def rules_cell(rollup):
    """`<n>`: how many rules the spec has."""
    return '%d' % (rollup.get('rules') or 0)


def proofs_cell(rollup):
    """`<n>`, and `· <k> no test` when a proof has none.

    The count calls the gap out because a spec can write ten proofs and have
    two of them observed by nothing, and the rule counts beside it would not
    show that.
    """
    total = rollup.get('proofs') or 0
    without = rollup.get('proofs_without_test') or 0
    if not without:
        return '%d' % total
    return '%d%s%d no test' % (total, DOT, without)


def tests_cell(rollup):
    """`<passed> of <rules>`, then `· <k> partial` and `· <k> failing`."""
    text = '%d of %d' % (passing(rollup), rollup.get('rules') or 0)
    if rollup.get('partial'):
        text += '%s%d partial' % (DOT, rollup['partial'])
    if rollup.get('failing'):
        text += '%s%d failing' % (DOT, rollup['failing'])
    return text


def strong_cell(rollup):
    """`<n> of <rules>`: how many of the spec's rules the audit found strong.

    Empty for a spec with no rules.
    """
    total = rollup.get('rules') or 0
    if not total:
        return ''
    return '%d of %d' % (strong_met(rollup), total)


def row_cells(name, rollup, proofs=1, audited=False):
    """One spec's row, as the tuple the columns describe.

    `proofs` and `audited` are read as `columns_for` reads them.
    """
    cells = [name, rules_cell(rollup)]
    if shows_proofs(proofs):
        cells.append(proofs_cell(rollup))
    cells.append(tests_cell(rollup))
    if audited:
        cells.append(strong_cell(rollup))
    return tuple(cells)
