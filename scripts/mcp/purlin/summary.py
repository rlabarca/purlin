"""The status's opening lines, its sentence, `Left to do` and its last line, written once.

Every surface that says where a project stands says it in these words: the
status opens and ends on them, a test run and an audit end on the status,
the evidence package copies the counts, and the dashboard reads the payload
keys this module fills. No surface composes the text itself.

The status opens on the project and the two facts:

    Purlin status: labconnect, plugin 0.10.0
    Tests: not met
    Sign-off: signed 0.1.0, 4 commits since

It ends on one sentence, counting each rule once under the spec that owns
it, anchors' included, and how many pass their tests, with how many of those
a model graded where any is; then how many are
checked at sign-off, the rules checked by hand alone that no sign-off has
noted on their wording as it is; where a rule that passes has an audit
entry, it gives the share the audit found strong and then each count. No
bug is planted for an anchor's rule, which is never found strong, so the
share counts no rule of an anchor and the counts after it count every rule:

    40 rules. 40 pass their tests. The audit found 34 of 40 rules strong (85%): 34 strong, 4 weak, 2 spot-checked.
    48 rules. 48 pass their tests. The audit found 40 of 40 rules strong (100%): 40 strong, 8 spot-checked.
    10 rules. 9 pass their tests. 1 is checked at sign-off.
    40 rules. 40 pass their tests, 6 of them graded by an AI.

`Left to do` follows it: one line per kind of work, in the order the work is
done, each with its count and the command that clears it. A kind at zero is
left out, and each rule is counted under one kind, the first that applies;
`specs to repair` counts specs, `test comments to correct` comments above
tests, `slow proofs to run` the slow proofs that no run has
answered for, and `features whose results are not committed` features, not
rules. `rules to test on <model>` has one line per model: the rules an AI
proof of which a run has tried and that hold no counting result on it.
`rules to write a proof for` and `rules to strengthen` are not blocking: the
tests read `met` beside them.

    Left to do:
      1 rule to fix: purlin:build
      2 rules to strengthen: purlin:build

Where the tests are met and this code is not signed, the last line names the
sign-off as a choice: `Every rule passes its tests on the committed evidence.
Optional: sign this version with purlin:sign`. Where `purlin:sign` would
refuse those results as they stand, the line names the run to make first and
why (`closing_line`):

    Every rule passes its tests on the committed evidence. Before a sign-off, run purlin:test --all --commit: a sign-off counts only results recorded on this version of the code.

`payload.build_payload` is the one caller of `rule_kind`, `steps`,
`sentence`, `left` and `last_line`; `status.sync_status` is the one caller of
`closing_line`. `audit_share` is the one home of the
share: the sentence, the audit's last line and the status table read it. Everything else reads the
payload they fill, through `opening`, `left_lines` and `ending`.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import facts, states                               # noqa: E402

# The kinds of work left, in the order the work is done and the lines read.
# Each is `(kind, one, many, command)`: the words after the count for one
# and for any other count, and the command that clears it. `%s` in the
# words and the command of `to_test_remote` is the systems it waits for, and
# in the words of `to_test_model` the one model its line is about. `to_repair` counts
# the specs that write a number twice or hold a line left from a merge
# conflict, `to_correct` the comments above tests, `to_run_slow` the proofs
# that are slow and read `not run`, an AI proof among them until a run has
# tried it, `to_commit` the features whose results are written and not
# committed; every other kind counts rules.
KINDS = (
    ('to_repair', 'spec to repair', 'specs to repair', 'purlin:spec'),
    ('no_proof', 'rule to write a proof for', 'rules to write a proof for',
     'purlin:spec'),
    ('to_correct', 'test comment to correct', 'test comments to correct',
     'purlin:build'),
    ('to_fix', 'rule to fix', 'rules to fix', 'purlin:build'),
    ('no_test', 'rule to write a test for', 'rules to write a test for',
     'purlin:build'),
    ('to_test', 'rule to test', 'rules to test', 'purlin:test'),
    ('to_run_slow', 'slow proof to run', 'slow proofs to run',
     'purlin:test --all'),
    ('to_test_model', 'rule to test on %s', 'rules to test on %s',
     'purlin:test --all'),
    ('to_test_remote', 'rule to test on %s', 'rules to test on %s',
     'run purlin:test on %s'),
    ('to_commit', 'feature whose results are not committed',
     'features whose results are not committed', 'purlin:test --commit'),
    ('to_strengthen', 'rule to strengthen', 'rules to strengthen',
     'purlin:build'),
)

# The kinds that stop the tests being met. A rule with no proof line, or one
# the audit found weak, still lets them read `met`.
BLOCKING = ('to_repair', 'to_correct', 'to_fix', 'no_test', 'to_test',
            'to_run_slow', 'to_test_model', 'to_test_remote', 'to_commit')

OPENING = 'Purlin status: %s, plugin %s'
TESTS_LINE = 'Tests: %s'
SIGNOFF_LINE = 'Sign-off: %s'
LEFT_TO_DO = 'Left to do:'
# The audit's five counts, in the order they are said: the key each is
# counted under, and its word. `AUDIT_LINE` is the share followed by them.
AUDIT_WORDS = (('strong', 'strong'), ('weak', 'weak'),
               ('spot_checked', 'spot-checked'),
               ('out_of_date', 'out of date'), ('not_audited', 'not audited'))
AUDIT_LINE = 'The audit found %d of %d rules strong (%d%%): %s.'
# The same line where no rule the audit read can be found strong, each being
# an anchor's: there is nothing to take a share of, so it lists what was found.
AUDIT_FOUND = 'The audit found %s.'
# What the sentence's second part ends on where a passed cell reads
# `graded`: for one rule that passes, for one of several, for any other count.
GRADED_ALONE = ', graded by an AI'
GRADED_ONE = ', 1 of them graded by an AI'
GRADED_MANY = ', %d of them graded by an AI'
# The sentence's third part, where a passed cell reads `checked at sign-off`.
BY_HAND_ONE = '1 is checked at sign-off.'
BY_HAND_MANY = '%d are checked at sign-off.'
LAST_LINE = 'Every rule passes its tests on the committed evidence. Optional: sign this version with purlin:sign'
# The last line where the sign-off would refuse the results as they stand:
# the run to make first, then why. `%s` is `run_again`'s commands.
LAST_LINE_RUN_FIRST = ('Every rule passes its tests on the committed evidence. Before a '
                       'sign-off, run %s: a sign-off counts only results recorded on '
                       'this version of the code.')
LAST_LINE_RUN_CLEAN = ('Every rule passes its tests on the committed evidence. Before a '
                       'sign-off, run %s: a sign-off counts only results taken with '
                       'nothing uncommitted.')
# The last line while a test still carries a marker Purlin 0.9.5 wrote, which
# `purlin:sign` refuses: the one for a single test, then the one for more.
LAST_LINE_OLD_ONE = ('Every rule passes its tests on the committed evidence. Before a '
                     'sign-off, rewrite the 1 test that still carries a marker from '
                     'Purlin 0.9.5: purlin:status names it.')
LAST_LINE_OLD_MANY = ('Every rule passes its tests on the committed evidence. Before a '
                      'sign-off, rewrite the %d tests that still carry a marker from '
                      'Purlin 0.9.5: purlin:status names each.')
# The run that takes a source's results again; `%s` is the systems.
RUN_AGAIN = {'local': 'purlin:test --all --commit', 'ci': 'purlin:test on %s'}

# The order systems are named in, whatever order the rules name them.
SYSTEM_ORDER = states.SYSTEM_ORDER


def _words(one, many, count):
    return one if count == 1 else many


def rule_kind(rule, here_os, broken=None):
    """The one kind of work a rule waits for, or None.

    `rule` is a payload rule entry, read for its `cells` and its `proofs`.
    `here_os` is this machine's system, `windows`, `macos` or `linux`.
    `broken`, the reasons the rule's own spec is broken, gives `to_repair`
    first. Otherwise the first that applies: a passed cell reading `failed`
    or `partial`, `no test`, `out of date` or `not run` where this machine
    can run part of it, `not run` for other systems only, no proof line with
    its tests passing, a weak audit. A rule that reads `not run` for slow
    proofs alone, one of them an AI proof a run has tried, answers
    `to_test_model`: `left` counts it once per model of
    `missing_models`. A hand check adds no kind, a passed
    cell reading `checked at sign-off` included, and neither does a rule no
    audit has read. A rule that waits for slow proofs alone answers
    `to_run_slow`, which `left` counts by proof and not by rule.
    """
    if broken:
        return 'to_repair'
    cells = rule.get('cells') or {}
    passed = cells.get('passed') or {}
    word = passed.get('word')

    if word == states.CHECKED_AT_SIGNOFF:
        # No test runs for the rule, so no work of any kind clears it: a
        # person checks it at the sign-off.
        return None
    if word in ('failed', 'partial'):
        return 'to_fix'
    if word == 'no test':
        return 'no_test'
    if word == 'not run':
        missing = passed.get('missing_env') or []
        if missing and here_os not in missing:
            return 'to_test_remote'
        if not _waits_for_slow_alone(rule, here_os):
            return 'to_test'
        return 'to_test_model' if passed.get('missing_models') \
            else 'to_run_slow'
    if not states.passes(word):
        # `out of date`: the next run here clears it, unless slow proofs
        # are all the rule has.
        return 'to_run_slow' if _waits_for_slow_alone(rule, here_os) \
            else 'to_test'
    if not (rule.get('proofs') or []):
        return 'no_proof'
    if (cells.get('strong') or {}).get('word') == 'weak':
        return 'to_strengthen'
    return None


def _slow_here(proof, here_os):
    """True for a `@slow` proof this machine's `purlin:test --all` answers for."""
    return bool(proof.get('slow')) and proof.get('env') in (None, here_os)


def _waits_for_slow_alone(rule, here_os):
    """True when every proof of the rule that has not passed is a slow
    proof this machine can run."""
    waiting = [proof for proof in rule.get('proofs') or ()
               if not proof.get('manual')
               and not states.passes(proof.get('result'))]
    return bool(waiting) and all(_slow_here(proof, here_os)
                                 for proof in waiting)


def slow_to_run(features, here_os):
    """`{(feature, proof id)}` for each slow proof that reads `not run`
    and is not tagged for another system than this machine's. An AI proof a
    run has tried is not one: its rule waits for a model, which
    `to_test_model` counts."""
    return {(feature.get('name'), proof.get('id'))
            for feature in features or ()
            for rule in feature.get('rules') or ()
            for proof in rule.get('proofs') or ()
            if _slow_here(proof, here_os) and proof.get('result') == 'not run'
            and not states.tried(proof.get('models'))}


def _word(rule):
    return ((rule.get('cells') or {}).get('passed') or {}).get('word')


def _passes(rule):
    return states.passes(_word(rule))


def steps(own_rules):
    """`{"passed": p, "graded": g, "by_hand": h}` over the rules given.

    `p` counts the rules that pass their tests, whose passed cell reads
    `passed` or `graded`; `g` those of them whose cell reads `graded`; and
    `h` the rules whose passed cell reads `checked at sign-off`: a rule is
    in `p` or in `h` or in neither.
    """
    words = [_word(rule) for rule in own_rules or ()]
    return {'passed': sum(1 for word in words if states.passes(word)),
            'graded': words.count(states.GRADED),
            'by_hand': words.count(states.CHECKED_AT_SIGNOFF)}


def audit_counts(own_rules):
    """The five counts of `AUDIT_WORDS` over the rules that pass.

    Each counts the rules that pass their tests (`states.passes`) and whose strong
    cell reads that word, so a rule checked by hand alone is in none.
    """
    counts = {key: 0 for key, _word in AUDIT_WORDS}
    names = {word: key for key, word in AUDIT_WORDS}
    for rule in own_rules or ():
        if not _passes(rule):
            continue
        word = ((rule.get('cells') or {}).get('strong') or {}).get('word')
        if word in names:
            counts[names[word]] += 1
    return counts


def audit_words(counts):
    """`34 strong, 4 weak, 2 spot-checked`: `strong` always, each other count
    only where it is not zero, in AUDIT_WORDS' order."""
    counts = counts or {}
    return ', '.join('%d %s' % (counts.get(key) or 0, word)
                     for key, word in AUDIT_WORDS
                     if key == 'strong' or counts.get(key))


def anchors_audit(features):
    """`audit_counts` over the rules of the anchors among `features`, the
    payload's feature entries: what `audit_share` leaves out of the share."""
    return audit_counts([rule for feature in features or ()
                         if feature.get('is_anchor')
                         for rule in feature.get('rules') or ()])


def audit_share(counts, anchors=None):
    """`(strong, over)`: the share of strong rules, counting no rule of an
    anchor.

    `counts` is `audit_counts` over every rule and `anchors` is
    `anchors_audit`'s answer for the same project, or None where it has no
    anchor. `over` is the rules the audit can find strong: those that pass
    their tests, have a tested proof and are not an anchor's.
    """
    counts = counts or {}
    anchors = anchors or {}
    strong = (counts.get('strong') or 0) - (anchors.get('strong') or 0)
    over = sum((counts.get(key) or 0) - (anchors.get(key) or 0)
               for key, _word in AUDIT_WORDS)
    return max(strong, 0), max(over, 0)


def audit_line(counts, anchors=None):
    """AUDIT_LINE: `audit_share(counts, anchors)`, the whole per cent rounded
    down, then `audit_words(counts)`, which counts the anchors' rules too.
    Where the share is over no rule, AUDIT_FOUND: each count that is not
    zero, in AUDIT_WORDS' order."""
    strong, over = audit_share(counts, anchors)
    if not over:
        return AUDIT_FOUND % ', '.join(
            '%d %s' % (counts[key], word) for key, word in AUDIT_WORDS
            if (counts or {}).get(key))
    return AUDIT_LINE % (strong, over, strong * 100 // over,
                         audit_words(counts))


def features_audit_line(features):
    """`audit_line` over the payload's feature entries given: the counts over
    every rule each lists, the share over those that are not an anchor's."""
    own = [rule for feature in features or ()
           for rule in feature.get('rules') or ()]
    return audit_line(audit_counts(own), anchors_audit(features))


def has_audit(counts):
    """True where a rule that passes has an audit entry: the counts hold a
    rule read `strong`, `weak`, `spot-checked` or `out of date`."""
    counts = counts or {}
    return any(counts.get(key) for key, _word in AUDIT_WORDS
               if key != 'not_audited')


def sentence(summary, anchors=None):
    """`<N> rules. <p> pass their tests.`, its second part ending
    `, <g> of them graded by an AI.` where a passed cell reads `graded`
    (`GRADED_ONE` for one, `GRADED_ALONE` where one rule passes and it is
    the graded one), then `BY_HAND_ONE` or
    `BY_HAND_MANY` where a passed cell reads `checked at sign-off`, then
    `audit_line` where a rule that passes has an audit entry: one read
    `strong`, `weak`, `spot-checked` or `out of date`. `anchors` is
    `anchors_audit`'s answer, which the share leaves out."""
    total = summary.get('rules') or 0
    count = (summary.get('steps') or {}).get('passed') or 0
    by_hand = (summary.get('steps') or {}).get('by_hand') or 0
    graded = (summary.get('steps') or {}).get('graded') or 0
    parts = ['%d %s.' % (total, _words('rule', 'rules', total)),
             '%d %s%s.' % (count, _words('passes its tests',
                                          'pass their tests', count),
                           '' if not graded
                           else GRADED_ALONE if count == 1
                           else GRADED_ONE if graded == 1
                           else GRADED_MANY % graded)]
    if by_hand:
        parts.append(BY_HAND_ONE if by_hand == 1 else BY_HAND_MANY % by_hand)
    audit = summary.get('audit') or {}
    if has_audit(audit):
        parts.append(audit_line(audit, anchors))
    return ' '.join(parts)


def systems_text(systems):
    """The systems in display words, Linux/Unix, macOS, Windows, joined ` and `.

    This machine's own system is never among them, so there are one or two.
    The join is the cell reasons' own, `states.systems_text`.
    """
    return states.systems_text(systems)


def left(features, here_os, corrections=0, uncommitted=()):
    """`[{kind, count, text, command}]`: the work left, in the order it is done.

    `features` is the payload's feature entries; each rule is counted once,
    under the spec that owns it and lists it. `corrections` is how many
    comments above tests name something no spec has, a rule that has
    proofs, or a proof reworded since the test last changed. `uncommitted`
    names the features whose results are written and not committed, counted
    once no other work stops the tests being met. `to_run_slow` counts the
    slow proofs `slow_to_run` names. `to_test_model` has one entry per
    model, by name, each counting the rules that wait for it and carrying
    `model`. A kind at zero is left out.
    """
    counts = {}
    if corrections:
        counts['to_correct'] = corrections
    slow = slow_to_run(features, here_os)
    if slow:
        counts['to_run_slow'] = len(slow)
    systems = set()
    models = {}
    to_repair = set()
    for feature in features or ():
        for rule in feature.get('rules') or ():
            kind = rule_kind(rule, here_os, feature.get('broken'))
            if kind is None or kind == 'to_run_slow':
                continue
            if kind == 'to_repair':
                # A broken spec is repaired once, whatever its rules count.
                to_repair.add(feature.get('name'))
                counts[kind] = len(to_repair)
                continue
            if kind == 'to_test_model':
                for name in ((rule.get('cells') or {}).get('passed')
                             or {}).get('missing_models') or ():
                    models[name] = models.get(name, 0) + 1
            counts[kind] = counts.get(kind, 0) + 1
            if kind == 'to_test_remote':
                systems.update(((rule.get('cells') or {}).get('passed')
                                or {}).get('missing_env') or ())
    if uncommitted and not any(kind in BLOCKING for kind in counts):
        counts['to_commit'] = len(set(uncommitted))
    out = []
    for kind, one, many, command in KINDS:
        count = counts.get(kind)
        if not count:
            continue
        if kind == 'to_test_model':
            out.extend({'kind': kind, 'count': models[name],
                        'text': '%d %s' % (models[name], _words(
                            one, many, models[name]) % name),
                        'command': command, 'model': name}
                       for name in sorted(models))
            continue
        words = _words(one, many, count)
        if kind == 'to_test_remote':
            words = words % systems_text(systems)
            command = command % systems_text(systems)
        out.append({'kind': kind, 'count': count,
                    'text': '%d %s' % (count, words), 'command': command})
    return out


def last_line(left_items, signoff):
    """`LAST_LINE` where the tests are met and this code is not signed, else None.

    `signoff` is `facts.signoff_fact`'s answer: the line is left out where it
    reads `signed <version> at <sha7>`.
    """
    if any(item.get('kind') in BLOCKING for item in left_items or ()):
        return None
    if facts.is_signed_here(signoff):
        return None
    return LAST_LINE


def run_again(found):
    """The runs that take results again, joined ` and `: this machine's
    first, then the one on each other system, as `purlin:test on Windows`.

    `found` is `[(source, system)]`, `facts.results_to_retake`'s second
    answer.
    """
    systems = [name for name in SYSTEM_ORDER
               if ('ci', name) in found]
    systems += sorted(name for source, name in found
                      if source == 'ci' and name not in systems)
    commands = []
    if any(source != 'ci' for source, _name in found):
        commands.append(RUN_AGAIN['local'])
    if systems:
        commands.append(RUN_AGAIN['ci'] % systems_text(systems))
    return ' and '.join(commands)


def closing_line(last, retake):
    """The status's last line, given what the sign-off would refuse.

    `last` is `last_line`'s answer and `retake` is
    `facts.results_to_retake`'s. Any other line than `LAST_LINE` stays as it
    is, and so does `LAST_LINE` where nothing would be refused. Otherwise
    the line names the run to make before a sign-off: `LAST_LINE_RUN_FIRST`
    for results recorded on another version of the code, `LAST_LINE_RUN_CLEAN`
    for results taken while files were changed and not committed.
    """
    if last != LAST_LINE or not retake:
        return last
    why, found = retake
    words = LAST_LINE_RUN_FIRST if why == 'code' else LAST_LINE_RUN_CLEAN
    return words % run_again(found)


def opening(payload):
    """The status's three opening lines: the project, the tests, the sign-off."""
    word = facts.TESTS_MET if payload.get('met') else facts.TESTS_NOT_MET
    signoff = (payload.get('signoff') or {}).get('word') or facts.NOT_SIGNED
    return [OPENING % (payload.get('project'), payload.get('version')),
            TESTS_LINE % word, SIGNOFF_LINE % signoff]


def left_lines(payload, kinds=None):
    """`<text>: <command>` for each line of the payload's `left`, in order.

    `kinds` keeps only the lines of those kinds. No indent and no heading:
    `ending` adds both.
    """
    return ['%s: %s' % (item['text'], item['command'])
            for item in payload.get('left') or ()
            if kinds is None or item.get('kind') in kinds]


def ending(payload):
    """The sentence, then `Left to do:` and its lines, then the last line where there is one."""
    lines = [(payload.get('summary') or {}).get('sentence') or '']
    if payload.get('left'):
        lines.append(LEFT_TO_DO)
        lines.extend('  ' + line for line in left_lines(payload))
    if payload.get('last_line'):
        lines.append(payload['last_line'])
    return '\n'.join(lines)
