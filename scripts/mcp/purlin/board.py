"""The columns every surface reads a spec's row from, rendered once.

The dashboard's board and the `purlin:status` table both answer the same
questions about one spec, and they have to answer them in the same
words: a reader who learns the board reads the table without learning it
again. So the columns, the cell text and the bucket names live here, and
each surface renders what this module returns rather than composing its own
string. `scripts/report/src/board.js` mirrors these
strings on the dashboard's side; changing one here changes the table.

The columns, left to right:

    Spec     the spec's name
    Rules    how many rules it owns, then ` (+<k> shared)` for the rules it
             proves from an anchor it requires or from a global anchor
    Proofs   how many proof lines it writes, and how many have no test; at
             `passed` only where the project writes a proof line at all
    Tests    how many rules pass, and how many are partial or failing
    Strong   how many rules are strong of those whose level asks for the
             audit, and the test strength, at `strong`; empty where no rule's
             level asks for it
    Signed   how many rules are signed of those whose level asks for a
             signature, at `signed`; empty where none does

Every when, who and platform detail lives in a hover on the dashboard and on
the rule screen; a cell here carries counts and nothing else.
"""

DOT = ' · '

# The six columns, and which gate each one appears at.
COLUMNS = ('Spec', 'Rules', 'Proofs', 'Tests', 'Strong', 'Signed')
STRONG_COLUMNS = ('Strong',)
SIGNED_COLUMNS = ('Signed',)

# The one tile a rule is counted in, and the word every surface prints for it.
# The bucket key `passed` reads `Passing` on a tile, because the tile counts
# rules whose tests pass now.
BUCKET_LABELS = (('untested', 'Untested'), ('failing', 'Failing'),
                 ('partial', 'Partial'), ('passed', 'Passing'),
                 ('strong', 'Strong'), ('signed', 'Signed'))



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


def bucket_label(bucket):
    """The word a tile and a summary line print for one bucket key."""
    for key, label in BUCKET_LABELS:
        if key == bucket:
            return label
    return str(bucket)


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


def strength_text(strength):
    """A test strength as a percentage, or `n/a` where nothing measured one."""
    return 'n/a' if strength is None else '%d%%' % int(strength)


def shared_counts(rules):
    """`[(anchor, count)]` for the rules a feature proves and does not own.

    Read from a feature's `rules` in the payload's order: a rule labelled
    `required` or `global` names its owner in `feature`, and is counted under
    that owner.
    """
    counts = {}
    order = []
    for rule in rules or ():
        if rule.get('label') == 'own':
            continue
        owner = rule.get('feature')
        if owner not in counts:
            counts[owner] = 0
            order.append(owner)
        counts[owner] += 1
    return [(owner, counts[owner]) for owner in order]


def rules_cell(rollup, shared=()):
    """`<n>`, or `<own> (+<k> shared)` where the spec proves shared rules.

    The rollup counts every rule the spec must prove, so the rules it owns are
    that total less the shared ones, which are listed once, under the anchor
    that owns them, and still count toward the spec.
    """
    total = rollup.get('rules') or 0
    more = sum(count for _owner, count in shared or ())
    if not more:
        return '%d' % total
    return '%d (+%d shared)' % (total - more, more)


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
    """`<n> of <m> · <strength>`, `<m>` the rules whose level asks for the audit.

    A rule whose level is `passed` is not asked, so it is in neither number,
    and a spec none of whose rules is asked shows an empty cell.
    """
    asked = rollup.get('asks_strong') or 0
    if not asked:
        return ''
    return '%d of %d%s%s' % (strong_met(rollup), asked, DOT,
                             strength_text(rollup.get('test_strength')))


def signed_cell(rollup):
    """`<n> of <m>`, `<m>` the rules whose level is `signed`, or empty where none is."""
    asked = rollup.get('asks_signed') or 0
    if not asked:
        return ''
    return '%d of %d' % (signed_met(rollup), asked)


def row_cells(name, rollup, gate, proofs=1, shared=()):
    """One spec's row under `gate`, as the tuple the columns describe.

    `proofs` is how many proof lines the project writes, as `columns_for`
    reads it; `shared` is `shared_counts` over the spec's rules.
    """
    cells = [name, rules_cell(rollup, shared)]
    if shows_proofs(gate, proofs):
        cells.append(proofs_cell(rollup))
    cells.append(tests_cell(rollup))
    if gate in ('strong', 'signed'):
        cells.append(strong_cell(rollup))
    if gate == 'signed':
        cells.append(signed_cell(rollup))
    return tuple(cells)


def proofs_summary(summary):
    """`<n> proof lines`, and `· <k> no test` when a proof has none.

    The cell's own words, read as a sentence rather than as a column, for the
    summary line under the table.
    """
    total = summary.get('proofs') or 0
    text = '%d proof line%s' % (total, '' if total == 1 else 's')
    without = summary.get('proofs_without_test') or 0
    if without:
        text += '%s%d no test' % (DOT, without)
    return text


def bucket_counts(summary, gate):
    """`[(label, count)]` for every bucket the gate reaches, weakest first."""
    from purlin import states

    keys = states.bucket_keys(gate)
    return [(bucket_label(key), summary.get(key) or 0) for key in keys]


def bucket_line(summary, gate):
    """The six counts on one line, in the order the tiles read."""
    return DOT.join('%s %d' % pair for pair in bucket_counts(summary, gate))


def headline(summary, gate):
    """What the board leads with, and the one line a table's summary opens on."""
    return '%d of %d rules meet the gate %s.' % (
        summary.get('met') or 0, summary.get('rules') or 0, gate)


def count_of(count, word, plural=None):
    """`<n> <word>`, with the plural only where the count asks for one.

    One feature is a feature and one signature is a signature, and a table a
    person reads on their first day should not say `1 features`.
    """
    if count == 1:
        return '1 %s' % word
    return '%d %s' % (count, plural or word + 's')


def queue_line(summary):
    """`Queue: <n> rules. <h> hand checks, <s> signatures.`

    The one line that counts the queue, which `purlin:status` prints and
    `purlin:sign` opens its walk on.
    """
    total = summary.get('queue') or 0
    hand = summary.get('hand_checks') or 0
    return 'Queue: %s. %s, %s.' % (
        count_of(total, 'rule'), count_of(hand, 'hand check'),
        count_of(total - hand, 'signature'))


def needs_a_person(count):
    """`<n> rules need a person`: the one sentence that says a person is owed.

    The queue is the one place a person is named, and this is the sentence
    every surface says it in, so the table and the
    dashboard's heading never disagree about the wording or about how one
    rule reads.
    """
    if not count:
        return 'no rule needs a person'
    if count == 1:
        return '1 rule needs a person'
    return '%d rules need a person' % count
