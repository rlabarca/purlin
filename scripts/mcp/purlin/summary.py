"""The summary sentence and `Left to do`, written once.

Every surface that says where a project stands says it in these words: the
status table ends on them, a test run and an audit end on the status table,
`purlin:sign` opens its walk on two of the lines, drift's view for QA prints
the same two, the evidence package copies the counts, and the dashboard reads
the payload keys this module fills. No surface composes the text itself.

The sentence counts each rule once, under the feature that owns it, and names
the steps up to the gate, each containing the next:

    40 rules. 35 pass their tests. 30 are strong. 20 are signed.

`Left to do` follows it: one line per kind of work, in the order the work is
done, each with its count and the command that clears it. A kind at zero is
left out, and each rule is counted under one kind, the first that applies:

    Left to do:
      5 rules to audit: purlin:audit
      10 rules to sign: purlin:sign

When nothing is left, the line after the sentence is `Nothing left to do.`,
and at the gate `signed` it names the release step instead:
`Nothing left to do. Push the tag to release it: git push origin
signed/<version>`.

`payload.build_payload` is the one caller of `rule_kind`, `steps`, `left` and
`last_line`. Everything else reads the payload they fill, through
`left_lines` and `ending`.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import evidence as evidence_module                 # noqa: E402

# The kinds of work left, in the order the work is done and the lines read.
# Each is `(kind, one, many, command)`: the words after the count for one
# rule and for any other count, and the command that clears it. `%s` in the
# words of `to_test_remote` is the systems it waits for.
KINDS = (
    ('no_proof', 'rule to write a proof for', 'rules to write a proof for',
     'purlin:spec'),
    ('to_fix', 'rule to fix', 'rules to fix', 'purlin:build'),
    ('no_test', 'rule to write a test for', 'rules to write a test for',
     'purlin:build'),
    ('to_test', 'rule to test', 'rules to test', 'purlin:test'),
    ('to_test_remote', 'rule to test on %s', 'rules to test on %s',
     'purlin:test --remote'),
    ('to_test_by_hand', 'rule to test by hand', 'rules to test by hand',
     'purlin:sign'),
    ('to_audit', 'rule to audit', 'rules to audit', 'purlin:audit'),
    ('to_strengthen', 'rule to strengthen', 'rules to strengthen',
     'purlin:build'),
    ('no_scope', 'rule to tie to its files', 'rules to tie to their files',
     'purlin:spec'),
    ('to_sign', 'rule to sign', 'rules to sign', 'purlin:sign'),
    ('to_tag', 'the version to tag', 'the version to tag', 'purlin:sign'),
)

KIND_NAMES = tuple(kind[0] for kind in KINDS)

# The two kinds that wait for a person, which the sign walk and drift's view
# for QA print.
FOR_A_PERSON = ('to_test_by_hand', 'to_sign')

LEFT_TO_DO = 'Left to do:'
NOTHING_LEFT = 'Nothing left to do.'
RELEASE = NOTHING_LEFT + ' Push the tag to release it: git push origin %s'

# The order systems are named in, whatever order the rules name them.
SYSTEM_ORDER = ('linux', 'macos', 'windows')

_UPPER = ('strong', 'signed')


def _words(one, many, count):
    return one if count == 1 else many


def rule_kind(rule, gate, here_os, incomplete=None):
    """The one kind of work a rule waits for under `gate`, or None.

    `rule` is a payload rule entry, read for its `cells`, its `proofs` and
    its `hand_checked`. `here_os` is this machine's system, `windows`,
    `macos` or `linux`. `incomplete` is true, or the reason, when the spec
    that owns the rule names no files. The first kind that applies wins, in
    the order of `KINDS`.

    A cell the rule does not carry is one it is not asked for, and reads as
    reached: a rule marked `[level: passed]` has no strong cell and waits
    for nothing once its tests pass. Once every rule takes the gate, every
    rule carries every cell up to it and this never applies.
    """
    cells = rule.get('cells') or {}
    passed = cells.get('passed') or {}
    word = passed.get('word')
    proofs = rule.get('proofs') or []
    upper = gate in _UPPER

    if upper and not proofs:
        return 'no_proof'
    if word in ('failed', 'partial'):
        return 'to_fix'
    if word == 'no test':
        return 'no_test'
    if word == 'not run':
        missing = passed.get('missing_env') or []
        if missing and here_os not in missing:
            return 'to_test_remote'
        return 'to_test'
    if word != 'passed':
        # `out of date`: the next run here clears it.
        return 'to_test'
    if (any(proof.get('manual') for proof in proofs)
            and not rule.get('hand_checked')):
        return 'to_test_by_hand'
    if not upper:
        return None

    strong = cells.get('strong')
    if strong is None:
        return None
    if strong.get('word') == 'weak':
        return 'to_strengthen'
    if strong.get('word') != 'strong':
        return 'to_audit'
    if gate != 'signed':
        return None

    signed = cells.get('signed')
    if signed is None or signed.get('word') == 'signed':
        return None
    if incomplete:
        return 'no_scope'
    return 'to_sign'


def steps(own_rules, gate):
    """`{"passed": p[, "strong": s[, "signed": g]]}` over the rules given.

    `p` counts the rules whose passed cell reads `passed` and, where a proof
    is `@manual`, whose `hand_checked` is true; `s` the rules in `p` whose
    strong cell reads `strong`; `g` the rules in `s` whose signed cell reads
    `signed`. Only the steps up to the gate are named. A cell the rule does
    not carry is one it is not asked for, and counts as reached.
    """
    reached = {'passed': 0, 'strong': 0, 'signed': 0}
    for rule in own_rules or ():
        cells = rule.get('cells') or {}
        if (cells.get('passed') or {}).get('word') != 'passed':
            continue
        if (any(proof.get('manual') for proof in rule.get('proofs') or ())
                and not rule.get('hand_checked')):
            continue
        reached['passed'] += 1
        strong = cells.get('strong')
        if strong is not None and strong.get('word') != 'strong':
            continue
        reached['strong'] += 1
        signed = cells.get('signed')
        if signed is None or signed.get('word') == 'signed':
            reached['signed'] += 1
    names = ('passed',) + tuple(name for name in _UPPER
                                if _UPPER.index(name) < _gate_depth(gate))
    return {name: reached[name] for name in names}


def _gate_depth(gate):
    """How many steps above `passed` the gate names: 0, 1 or 2."""
    return {'strong': 1, 'signed': 2}.get(gate, 0)


def sentence(summary, gate):
    """`<N> rules. <p> pass their tests.`, then the steps above it the gate names."""
    total = summary.get('rules') or 0
    reached = summary.get('steps') or {}
    parts = ['%d %s.' % (total, _words('rule', 'rules', total))]
    count = reached.get('passed') or 0
    parts.append('%d %s.' % (count, _words('passes its tests',
                                            'pass their tests', count)))
    if gate in _UPPER:
        count = reached.get('strong') or 0
        parts.append('%d %s.' % (count, _words('is strong', 'are strong',
                                                count)))
    if gate == 'signed':
        count = reached.get('signed') or 0
        parts.append('%d %s.' % (count, _words('is signed', 'are signed',
                                                count)))
    return ' '.join(parts)


def systems_text(systems):
    """The systems in display words, Linux/Unix, macOS, Windows, joined `, ` and ` and `."""
    known = [name for name in SYSTEM_ORDER if name in systems]
    words = [evidence_module.os_word(name) for name in known]
    if len(words) <= 1:
        return ''.join(words)
    return '%s and %s' % (', '.join(words[:-1]), words[-1])


def left(features, gate, here_os, tag=None):
    """`[{kind, count, text, command}]`: the work left, in the order it is done.

    `features` is the payload's feature entries; each rule is counted once,
    under the feature that owns it, so only a rule labelled `own` is read.
    `tag` is the payload's `tag`, the `signed/*` tag on HEAD or None. A kind
    at zero is left out. At the gate `signed`, with no other kind left and
    no tag on HEAD, the one line is `the version to tag`.
    """
    counts = {}
    systems = set()
    for feature in features or ():
        for rule in feature.get('rules') or ():
            if rule.get('label', 'own') != 'own':
                continue
            kind = rule_kind(rule, gate, here_os, feature.get('incomplete'))
            if kind is None:
                continue
            counts[kind] = counts.get(kind, 0) + 1
            if kind == 'to_test_remote':
                systems.update(((rule.get('cells') or {}).get('passed')
                                or {}).get('missing_env') or ())
    if gate == 'signed' and not counts and not tag:
        counts['to_tag'] = 1
    out = []
    for kind, one, many, command in KINDS:
        count = counts.get(kind)
        if not count:
            continue
        if kind == 'to_tag':
            text = one
        else:
            words = _words(one, many, count)
            if kind == 'to_test_remote':
                words = words % systems_text(systems)
            text = '%d %s' % (count, words)
        out.append({'kind': kind, 'count': count, 'text': text,
                    'command': command})
    return out


def last_line(left_items, gate, tag=None):
    """The line after the sentence when nothing is left, or None while work is.

    `Nothing left to do.` at the gates `passed` and `strong`; at `signed` the
    same with the release step for the tag on HEAD.
    """
    if left_items:
        return None
    if gate == 'signed' and tag and tag.get('name'):
        return RELEASE % tag['name']
    return NOTHING_LEFT


def left_lines(payload, kinds=None):
    """`<text>: <command>` for each line of the payload's `left`, in order.

    `kinds` keeps only the lines of those kinds. No indent and no heading:
    `ending` adds both.
    """
    return ['%s: %s' % (item['text'], item['command'])
            for item in payload.get('left') or ()
            if kinds is None or item.get('kind') in kinds]


def ending(payload):
    """The sentence, then `Left to do:` and its lines, or the nothing-left line."""
    lines = [(payload.get('summary') or {}).get('sentence') or '']
    if payload.get('left'):
        lines.append(LEFT_TO_DO)
        lines.extend('  ' + line for line in left_lines(payload))
    elif payload.get('last_line'):
        lines.append(payload['last_line'])
    return '\n'.join(lines)
