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
it, anchors' included, and how many pass their tests; where the audit read a
rule that passes, it gives the share it found strong:

    50 rules. 50 pass their tests. The audit found 42 of 50 rules strong (84%).

`Left to do` follows it: one line per kind of work, in the order the work is
done, each with its count and the command that clears it. A kind at zero is
left out, and each rule is counted under one kind, the first that applies;
`specs to repair` counts specs, `test comments to correct` comments above
tests, `slow proofs to run` the proofs tagged `@slow` that no run has
answered for, and `features whose results are not committed` features, not
rules.
`rules to write a proof for` and `rules to strengthen` are not blocking: the
tests read `met` beside them.

    Left to do:
      1 rule to fix: purlin:build
      2 rules to strengthen: purlin:build

Where the tests are met and this code is not signed, the last line names the
sign-off: `Every rule passes its tests on the committed evidence. To sign it:
purlin:sign`.

`payload.build_payload` is the one caller of `rule_kind`, `steps`,
`audit_counts`, `sentence`, `left` and `last_line`. Everything else reads the
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
# words and the command of `to_test_remote` is the systems it waits for. `to_repair` counts
# the specs that write a number twice or hold a line left from a merge
# conflict, `to_correct` the comments above tests, `to_run_slow` the proofs
# tagged `@slow` that read `not run`, `to_commit` the features whose results
# are written and not committed; every other kind counts rules.
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
    ('to_test_remote', 'rule to test on %s', 'rules to test on %s',
     'run purlin:test on %s'),
    ('to_commit', 'feature whose results are not committed',
     'features whose results are not committed', 'purlin:test --commit'),
    ('to_strengthen', 'rule to strengthen', 'rules to strengthen',
     'purlin:build'),
)

KIND_NAMES = tuple(kind[0] for kind in KINDS)

# The kinds that stop the tests being met. A rule with no proof line, or one
# the audit found weak, still lets them read `met`.
BLOCKING = ('to_repair', 'to_correct', 'to_fix', 'no_test', 'to_test',
            'to_run_slow', 'to_test_remote', 'to_commit')

OPENING = 'Purlin status: %s, plugin %s'
TESTS_LINE = 'Tests: %s'
SIGNOFF_LINE = 'Sign-off: %s'
LEFT_TO_DO = 'Left to do:'
AUDIT_SHARE = 'The audit found %d of %d rules strong (%d%%).'
# The audit's five counts, in the order they are said: the key each is
# counted under, and its word. `AUDIT_LINE` is the share followed by them.
AUDIT_WORDS = (('strong', 'strong'), ('weak', 'weak'),
               ('spot_checked', 'spot-checked'),
               ('out_of_date', 'out of date'), ('not_audited', 'not audited'))
AUDIT_LINE = 'The audit found %d of %d rules strong (%d%%): %s.'
LAST_LINE = 'Every rule passes its tests on the committed evidence. To sign it: purlin:sign'

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
    its tests passing, a weak audit. A hand check adds no kind, and neither
    does a rule no audit has read. A rule that waits for slow proofs alone
    answers `to_run_slow`, which `left` counts by proof and not by rule.
    """
    if broken:
        return 'to_repair'
    cells = rule.get('cells') or {}
    passed = cells.get('passed') or {}
    word = passed.get('word')

    if word in ('failed', 'partial'):
        return 'to_fix'
    if word == 'no test':
        return 'no_test'
    if word == 'not run':
        missing = passed.get('missing_env') or []
        if missing and here_os not in missing:
            return 'to_test_remote'
        return 'to_run_slow' if _waits_for_slow_alone(rule, here_os) \
            else 'to_test'
    if word != 'passed':
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
               if not proof.get('manual') and proof.get('result') != 'passed']
    return bool(waiting) and all(_slow_here(proof, here_os)
                                 for proof in waiting)


def slow_to_run(features, here_os):
    """`{(feature, proof id)}` for each `@slow` proof that reads `not run`
    and is not tagged for another system than this machine's."""
    return {(feature.get('name'), proof.get('id'))
            for feature in features or ()
            for rule in feature.get('rules') or ()
            for proof in rule.get('proofs') or ()
            if _slow_here(proof, here_os) and proof.get('result') == 'not run'}


def _passes(rule):
    return ((rule.get('cells') or {}).get('passed') or {}).get(
        'word') == 'passed'


def steps(own_rules):
    """`{"passed": p}` over the rules given.

    `p` counts the rules whose passed cell reads `passed`, a rule whose
    every proof is `@manual` included.
    """
    return {'passed': sum(1 for rule in own_rules or () if _passes(rule))}


def audit_counts(own_rules):
    """`{"strong": s, "weak": w, "not_audited": u}` over the rules that pass.

    Each counts the rules whose passed cell reads `passed` and whose strong
    cell reads that word, so a rule checked by hand alone is in none.
    """
    counts = {'strong': 0, 'weak': 0, 'not_audited': 0}
    names = {'strong': 'strong', 'weak': 'weak',
             states.NOT_AUDITED: 'not_audited'}
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


def audit_line(counts):
    """AUDIT_LINE over the five counts: strong, their sum, the whole per cent
    rounded down, `audit_words(counts)`."""
    counts = counts or {}
    strong = counts.get('strong') or 0
    over = sum(counts.get(key) or 0 for key, _word in AUDIT_WORDS)
    return AUDIT_LINE % (strong, over, strong * 100 // over if over else 0,
                         audit_words(counts))


def sentence(summary):
    """`<N> rules. <p> pass their tests.`, then the audit's share where it read a rule."""
    total = summary.get('rules') or 0
    count = (summary.get('steps') or {}).get('passed') or 0
    parts = ['%d %s.' % (total, _words('rule', 'rules', total)),
             '%d %s.' % (count, _words('passes its tests',
                                        'pass their tests', count))]
    audit = summary.get('audit') or {}
    strong = audit.get('strong') or 0
    read = strong + (audit.get('weak') or 0)
    if read > 0:
        over = read + (audit.get('not_audited') or 0)
        parts.append(AUDIT_SHARE % (strong, over, strong * 100 // over))
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
    slow proofs `slow_to_run` names. A kind at zero is left out.
    """
    counts = {}
    if corrections:
        counts['to_correct'] = corrections
    slow = slow_to_run(features, here_os)
    if slow:
        counts['to_run_slow'] = len(slow)
    systems = set()
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
