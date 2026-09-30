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
    Proofs   how many proof lines it writes, and how many have no test; at
             `passed` only where the project writes a proof line at all
    Tests    how many rules pass, and how many do not apply, are partial or
             are failing
    Strong   how many of its rules are strong, and the test strength where
             one was measured, at `strong` and above
    Signed   how many of its rules are signed, at `signed`

Every when, who and platform detail lives in a hover on the dashboard and on
the rule screen; a cell here carries counts and nothing else.
"""

DOT = ' · '

# The six columns, and which gate each one appears at.
COLUMNS = ('Spec', 'Rules', 'Proofs', 'Tests', 'Strong', 'Signed')
STRONG_COLUMNS = ('Strong',)
SIGNED_COLUMNS = ('Signed',)

def shows_proofs(gate, proofs):
    """Whether the Proofs column and the proof count are shown.

    Proofs are optional at `passed`, so a project there that writes none is
    shown no count of them; from `strong` up every rule needs one.
    """
    return gate != 'passed' or bool(proofs)


def columns_for(gate, proofs=1):
    """The columns under `gate`, left to right.

    `proofs` is how many proof lines the project writes.
    """
    columns = [name for name in COLUMNS[:4]
               if name != 'Proofs' or shows_proofs(gate, proofs)]
    if gate in ('strong', 'signed'):
        columns.extend(STRONG_COLUMNS)
    if gate == 'signed':
        columns.extend(SIGNED_COLUMNS)
    return tuple(columns)


def passing(rollup):
    """How many of a spec's rules pass their tests.

    A rule is counted in exactly one bucket, so the rules that pass are the
    ones left after the three that do not: untested, failing, and partial. Reading it this way means the six counts always add up to the
    rule total, whatever the gate.
    """
    total = rollup.get('rules') or 0
    short = sum(rollup.get(key) or 0
                for key in ('untested', 'failing', 'partial'))
    return max(total - short, 0)


def strong_met(rollup):
    """How many of a spec's rules meet the strong cell."""
    return (rollup.get('strong') or 0) + (rollup.get('signed') or 0)


def signed_met(rollup):
    """How many of a spec's rules meet the signed cell."""
    return rollup.get('signed') or 0


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
    """`<passed> of <rules>`, then `· <k> does not apply`, `· <k> partial`
    and `· <k> failing`.

    A rule that does not apply is counted among the rules that pass;
    `does_not_apply` in `rollup` is how many of the spec's rules carry it.
    """
    text = '%d of %d' % (passing(rollup), rollup.get('rules') or 0)
    if rollup.get('does_not_apply'):
        text += '%s%d does not apply' % (DOT, rollup['does_not_apply'])
    if rollup.get('partial'):
        text += '%s%d partial' % (DOT, rollup['partial'])
    if rollup.get('failing'):
        text += '%s%d failing' % (DOT, rollup['failing'])
    return text


def strong_cell(rollup):
    """`<n> of <rules>`, then `· <strength>%` where a strength was measured.

    Where nothing measured one the cell says nothing of strength, rather than
    printing a stand-in. Empty for a spec with no rules.
    """
    total = rollup.get('rules') or 0
    if not total:
        return ''
    text = '%d of %d' % (strong_met(rollup), total)
    strength = rollup.get('test_strength')
    if strength is not None:
        text += '%s%d%%' % (DOT, int(strength))
    return text


def signed_cell(rollup):
    """`<n> of <rules>`, or empty for a spec with no rules."""
    total = rollup.get('rules') or 0
    if not total:
        return ''
    return '%d of %d' % (signed_met(rollup), total)


def row_cells(name, rollup, gate, proofs=1):
    """One spec's row under `gate`, as the tuple the columns describe.

    `proofs` is how many proof lines the project writes, as `columns_for`
    reads it.
    """
    cells = [name, rules_cell(rollup)]
    if shows_proofs(gate, proofs):
        cells.append(proofs_cell(rollup))
    cells.append(tests_cell(rollup))
    if gate in ('strong', 'signed'):
        cells.append(strong_cell(rollup))
    if gate == 'signed':
        cells.append(signed_cell(rollup))
    return tuple(cells)
