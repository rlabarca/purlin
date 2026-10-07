"""The one shape of every warning and every line of information Purlin prints.

    <what it is about>: <kind>. <what is wrong, in few words>. Run <command>.

    package PROOF-3 (RULE-3): test comment to correct. "sixteen" became "seventeen" after tests/test_export.py:336 last changed (82c91f6). Run purlin:build package.

What it is about comes first, as a person looks it up: `<spec> PROOF-N
(RULE-N)` for a proof, `<spec> RULE-N` for a rule, `<spec>` for a whole spec
or an anchor, and the thing itself, a tag or a file, where the line is about
no one spec. The kind is the same few words every time, and `KINDS` is the
one list of them; where the status names that work under `Left to do`, the
kind is that name. What is wrong is short, and left out where the kind says
it; the line ends on the command to run, or, where nothing is to be run, on
what to do. A line is one line, and none runs long because of its
explanation: what is wrong is a few words, a list is its first entry and a
count, and another tool's message is its first sentence (`first_sentence`).
A path, a name and a command are never cut.

`line` builds a line, as a `Notice`: the text, which every surface prints as
it is, with what it is about, its kind and the spec, rule and proof it names
beside it. `entries` gives those parts for the dashboard's data, which draws
the name and the kind apart from the rest. `grouped` folds three or more
entries of one kind into one, the kind first (`GROUP_MANY`), so the board
stays short, and `folded` is the same fold over the lines the terminal
prints: the status and a test run print a kind's lines whole up to two, and
`purlin:status <name>`, where the folded line sends a reader, prints every
line of that spec whole. `changed_words` says what
changed between two wordings of a proof without printing either whole, and
`change_sentence` is that as the sentence every surface prints.
"""

# Every kind of warning and of information, `(key, words)`. The words are
# what a line prints after its name; the key is what the data carries.
KINDS = (
    # A comment above a test: it names a proof reworded since the test last
    # changed, or names nothing a spec has. `Left to do` counts both.
    ('to_correct', 'test comment to correct'),
    # A number written twice, or a line left from a merge conflict.
    ('to_repair', 'spec to repair'),
    ('unnumbered', 'rule line with no number'),
    ('same_name', 'two specs with one name'),
    ('name_refused', 'spec name not allowed'),
    ('proof_unread', 'proof line not read'),
    ('heading', 'first line names another spec'),
    ('tags_conflict', 'tags that conflict'),
    ('line_unread', 'line not read'),
    ('tag_unread', 'tag not read'),
    ('setting_unread', 'setting not read'),
    ('evidence_ignored', 'evidence file ignored'),
    ('tag_no_signoff', 'tag with no sign-off'),
    ('tag_not_here', 'tag not in this checkout'),
    ('old_marker', 'marker from Purlin 0.9.5'),
    ('setting_changed', 'tests setting changed'),
    ('pin_behind', 'anchor pin behind'),
    ('pin_missing', 'anchor with no pin'),
    ('source_unread', 'anchor source not read'),
    ('source_refused', 'anchor source refused'),
    ('source_not_spec', 'anchor source not a spec'),
    ('spec_uncommitted', 'spec change not committed'),
    ('tree_dirty', 'changes not committed'),
    # What a test run adds: each rule of the features it ran that is left to
    # do, under the name `Left to do` counts it by; each piece of evidence
    # it could not take; and the proofs tagged for another system.
    ('to_fix', 'rule to fix'),
    ('no_test', 'rule to write a test for'),
    ('evidence_missing', 'evidence missing'),
    ('other_system', 'proofs not run here'),
    # A model an AI proof names that gave no answer.
    ('model_not_reached', 'model not reached'),
    ('untied', 'test comment with no test'),
    ('title_unread', 'test title not read'),
    ('ambiguous', 'test name not unique'),
    # What `purlin:drift` adds.
    ('number_twice', 'number written twice'),
    ('merge', 'merge in progress'),
    ('fetch_age', 'last fetch'),
    # Information: nothing here stops the tests being met.
    ('not_written', 'spec ahead of its code'),
    ('nothing_to_check', 'nothing to check here'),
    ('no_scope', 'spec with no scope'),
)
WORDS = dict(KINDS)

# The grouped notice, which stands for three or more lines of one kind: the
# kind, how many specs the lines name, and the first two. One spec is named
# with how many places its lines name.
GROUP_ONE = '%s: %s, in %d places. Run purlin:status %s.'
GROUP_TWO = '%s: 2 specs, %s and %s. Run purlin:status for each.'
GROUP_MANY = '%s: %d specs, %s, %s and %d more. Run purlin:status for each.'

# How many words of a wording `changed_words` shows on each side.
WORDS_SHOWN = 8
CUT = '...'
# How many characters of another tool's own message a line quotes.
CHARS_SHOWN = 80
BECAME = '"%s" became "%s"'
REWORDED = 'was reworded'
# The sentence a change is said in: what changed, then what follows it in the
# same sentence. `CHANGE_REWORDED` where the change is too large to show.
CHANGE = '%s%s.'
CHANGE_REWORDED = 'It %s%s.'


class Notice(str):
    """One line, with the parts the dashboard draws apart: `about`, `kind`
    (a key of `KINDS`), and the `feature`, `rule` and `proof` it names, each
    None where it names none."""

    about = None
    kind = None
    feature = None
    rule = None
    proof = None


def line(kind, about, wrong, do=None, feature=None, rule=None, proof=None):
    """`<about>: <kind>. <wrong> <do>` as a `Notice`.

    `wrong` and `do` are whole sentences. `wrong` is left out where the
    kind already says it, and `do` where the line says what to do nowhere
    else."""
    text = '%s: %s.' % (about, WORDS[kind])
    for sentence in (wrong, do):
        if sentence:
            text += ' ' + sentence
    made = Notice(text)
    made.about = about
    made.kind = kind
    made.feature = feature
    made.rule = rule
    made.proof = proof
    return made


def run(command):
    """`Run <command>.`, the sentence a line ends on."""
    return 'Run %s.' % command


def about_proof(info, name, proof_id):
    """`(about, rule)` for a proof: `<spec> PROOF-N (RULE-N)`, or
    `<spec> PROOF-N` where the spec, `scan_specs`' entry, names no rule for it."""
    rule = next((rule_id for rule_id, proofs
                 in ((info or {}).get('proofs_by_rule') or {}).items()
                 if proof_id in proofs), None)
    if rule:
        return '%s %s (%s)' % (name, proof_id, rule), rule
    return '%s %s' % (name, proof_id), None


def shown(text, limit=WORDS_SHOWN):
    """The first `limit` words of a text, with ` ...` where it is cut."""
    words = (text or '').split()
    if len(words) <= limit:
        return ' '.join(words)
    return ' '.join(words[:limit]) + ' ' + CUT


def first_sentence(text, limit=CHARS_SHOWN):
    """Another tool's own message as a line quotes it: its first sentence,
    without its full stop, cut at `limit` characters with `...` where it is
    longer. Git's message for a source it cannot read is one."""
    text = ' '.join((text or '').split())
    end = text.find('. ')
    if end >= 0:
        text = text[:end]
    text = text.rstrip('.')
    if len(text) > limit:
        return text[:limit].rstrip() + CUT
    return text


def changed_words(old, new):
    """What changed between two wordings, without printing either whole.

    `"sixteen" became "seventeen"`: the shortest run of words that differs,
    each side cut to `WORDS_SHOWN` words with ` ...` where it is cut. A word
    added or taken out is shown with the word on each side of it. Where the
    two share no word at either end, or the run that differs is longer than
    `WORDS_SHOWN` words on both sides, the answer is `was reworded`.
    """
    before, after = (old or '').split(), (new or '').split()
    head = 0
    while (head < len(before) and head < len(after)
           and before[head] == after[head]):
        head += 1
    tail = 0
    while (tail < len(before) - head and tail < len(after) - head
           and before[-1 - tail] == after[-1 - tail]):
        tail += 1
    if head + tail == 0:
        return REWORDED
    if len(before) - head - tail == 0 or len(after) - head - tail == 0:
        # A word added or taken out: one side of the run is empty, so each
        # side takes the word before and the word after.
        head = max(0, head - 1)
        tail = max(0, tail - 1)
    was = before[head:len(before) - tail]
    now = after[head:len(after) - tail]
    if len(was) > WORDS_SHOWN and len(now) > WORDS_SHOWN:
        return REWORDED
    return BECAME % (shown(' '.join(was)), shown(' '.join(now)))


def change_sentence(old, new, tail=''):
    """`changed_words` as a whole sentence: `"sixteen" became "seventeen".`,
    or `It was reworded.` where the change is too large to show. `tail` is
    what follows in the same sentence, before its full stop."""
    changed = changed_words(old, new)
    return (CHANGE_REWORDED if changed == REWORDED else CHANGE) % (changed,
                                                                   tail)


def entries(lines, tone):
    """One entry per line for the dashboard's data: `{tone, kind, label,
    about, feature, rule, rest, text}`. `rest` is the line after its name and
    its kind. A line that is no `Notice` carries `text` alone, the other
    parts None."""
    out = []
    for item in lines or ():
        kind = getattr(item, 'kind', None)
        about = getattr(item, 'about', None)
        text = str(item)
        rest = text
        if kind:
            rest = text[len('%s: %s. ' % (about, WORDS[kind])):]
        out.append({'tone': tone, 'kind': kind,
                    'label': WORDS.get(kind), 'about': about,
                    'feature': getattr(item, 'feature', None),
                    'rule': getattr(item, 'rule', None),
                    'rest': rest, 'text': text})
    return out


def folded(lines):
    """The lines as the terminal prints them: three or more of one kind,
    each naming a spec, folded into the one line `grouped` gives, where the
    first of them stood. Every other line is handed back as it was."""
    lines = list(lines or ())
    found = entries(lines, None)
    for entry, item in zip(found, lines):
        entry['line'] = item
    return [entry['line'] if 'line' in entry else entry['text']
            for entry in grouped(found)]


def grouped(found):
    """`entries`' answer with three or more entries of one kind, each naming
    a spec, folded into one where the first of them stood.

    The one entry opens on the kind: `spec to repair: 4 specs, login, signup
    and 2 more. Run purlin:status for each.` Two specs are both named, and
    one spec is named with how many places its lines name. It carries
    `names`, every spec it counts, and no `about`, `feature` or `rule`. An
    entry that names no spec always stands alone.
    """
    groups = {}
    for item in found:
        if item.get('kind') and item.get('feature'):
            group = groups.setdefault((item['tone'], item['kind']),
                                      {'lines': 0, 'names': []})
            group['lines'] += 1
            if item['feature'] not in group['names']:
                group['names'].append(item['feature'])
    out = []
    drawn = set()
    for item in found:
        key = (item.get('tone'), item.get('kind'))
        group = groups.get(key) if item.get('feature') else None
        if group is None or group['lines'] < 3:
            out.append(item)
            continue
        if key in drawn:
            continue
        drawn.add(key)
        names = group['names']
        label = item['label']
        if len(names) == 1:
            text = GROUP_ONE % (label, names[0], group['lines'], names[0])
        elif len(names) == 2:
            text = GROUP_TWO % (label, names[0], names[1])
        else:
            text = GROUP_MANY % (label, len(names), names[0], names[1],
                                 len(names) - 2)
        out.append({'tone': item['tone'], 'kind': item['kind'],
                    'label': label, 'about': None, 'feature': None,
                    'rule': None, 'rest': text[len(label) + 2:],
                    'text': text, 'names': names})
    return out
