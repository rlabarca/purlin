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
    Tests    how many rules pass, and how many are checked by hand, are
             partial or are failing
    Strong   how many of its rules the audit found strong, of those that
             pass their tests and have a tested proof, wherever a rule of
             the project has an audit entry

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


def shows_strong(audit, features=()):
    """Whether the Strong column is shown: an audit has read a rule.

    `audit` is the payload's `summary.audit`, read as `summary.has_audit`
    reads it, and `features` the payload's: a rule that carries an audit
    entry answers too, whatever its strong cell reads now. A project no
    audit has read shows no Strong column.
    """
    from purlin import summary
    return summary.has_audit(audit) or any(
        rule.get('audit') for feature in features or ()
        for rule in feature.get('rules') or ())


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
    ones left after the four that do not: untested, failing, partial and
    checked by hand. Reading it this way means the five buckets always add
    up to the rule total.
    """
    total = rollup.get('rules') or 0
    short = sum(rollup.get(key) or 0
                for key in ('untested', 'failing', 'partial', 'by_hand'))
    return max(total - short, 0)


def strong_met(rollup):
    """How many of a spec's rules the audit found strong."""
    return rollup.get('strong') or 0


# The rollup's five audit flags, one per word `summary.AUDIT_WORDS` counts.
AUDIT_FLAGS = ('strong', 'weak', 'spot_checked', 'audit_out_of_date',
               'not_audited')


def audited_rules(rollup):
    """How many of a spec's rules the audit can speak of: those that pass
    their tests and have a tested proof.

    The sum of the rollup's five audit flags, which is what
    `summary.audit_counts` counts over the same rules: a strong cell reads
    one of the five words only where the passed cell reads `passed` and a
    test answers a proof.
    """
    return sum(rollup.get(key) or 0 for key in AUDIT_FLAGS)


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
    """`<passed> of <rules>`, then `· <k> by hand`, `· <k> partial` and
    `· <k> failing`."""
    text = '%d of %d' % (passing(rollup), rollup.get('rules') or 0)
    if rollup.get('by_hand'):
        text += '%s%d by hand' % (DOT, rollup['by_hand'])
    if rollup.get('partial'):
        text += '%s%d partial' % (DOT, rollup['partial'])
    if rollup.get('failing'):
        text += '%s%d failing' % (DOT, rollup['failing'])
    return text


def strong_cell(rollup):
    """`<strong> of <n>`: how many of the spec's rules the audit found
    strong, `<n>` being `audited_rules`.

    Empty where `<n>` is 0: no rule of the spec passes its tests with a
    tested proof.
    """
    total = audited_rules(rollup)
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
