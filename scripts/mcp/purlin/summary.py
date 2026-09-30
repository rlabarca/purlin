"""The summary sentence and `Left to do`, written once.

Every surface that says where a project stands says it in these words: the
status table ends on them, a test run and an audit end on the status table,
the evidence package copies the counts, and the dashboard reads the payload
keys this module fills. No surface composes the text itself.

The sentence counts each rule once, under the spec that owns it, anchors'
included, and how many pass their tests; where the audit read any rule that
passes, it says what the audit found:

    40 rules. 35 pass their tests. The audit found 30 strong and 2 weak.

`Left to do` follows it: one line per kind of work, in the order the work is
done, each with its count and the command that clears it. A kind at zero is
left out, and each rule is counted under one kind, the first that applies;
`specs to repair` counts specs and `test comments to correct` comments above
tests, not rules. Every kind is work: nothing here waits on a person or on
the audit.

    Left to do:
      1 rule to fix: purlin:build
      2 rules to strengthen: purlin:build

When nothing is left, the line after the sentence names the release step:
`Nothing left to do. To release a version: purlin:test --release`, with
`, then purlin:sign` at the gate `signed`, or, where HEAD carries a
`passed/*` or `signed/*` tag, `Nothing left to do. Push the tag to release
it: git push origin <tag>`.

`payload.build_payload` is the one caller of `rule_kind`, `steps`,
`audit_counts`, `left` and `last_line`. Everything else reads the payload
they fill, through `left_lines` and `ending`.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import states                                      # noqa: E402

# The kinds of work left, in the order the work is done and the lines read.
# Each is `(kind, one, many, command)`: the words after the count for one
# and for any other count, and the command that clears it. `%s` in the
# words of `to_test_remote` is the systems it waits for. `to_repair` counts
# the specs that write a number twice or hold a line left from a merge
# conflict, `to_correct` the comments above tests that name something no
# spec has or a rule that has proofs; every other kind counts rules.
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
    ('to_test_remote', 'rule to test on %s', 'rules to test on %s',
     'purlin:test --remote'),
    ('to_strengthen', 'rule to strengthen', 'rules to strengthen',
     'purlin:build'),
)

KIND_NAMES = tuple(kind[0] for kind in KINDS)

# The kinds that stop a release: a rule whose tests do not pass here, or a
# spec or a test comment the run cannot read.
BLOCKING = ('to_repair', 'to_correct', 'to_fix', 'no_test', 'to_test',
            'to_test_remote')

LEFT_TO_DO = 'Left to do:'
NOTHING_LEFT = 'Nothing left to do.'
TO_RELEASE = NOTHING_LEFT + ' To release a version: purlin:test --release'
TO_RELEASE_SIGNED = (NOTHING_LEFT + ' To release a version: '
                     'purlin:test --release, then purlin:sign')
RELEASE = NOTHING_LEFT + ' Push the tag to release it: git push origin %s'
AUDIT_FOUND = 'The audit found %d strong and %d weak.'

# The order systems are named in, whatever order the rules name them.
SYSTEM_ORDER = states.SYSTEM_ORDER


def _words(one, many, count):
    return one if count == 1 else many


def rule_kind(rule, gate, here_os, broken=None):
    """The one kind of work a rule waits for under `gate`, or None.

    `rule` is a payload rule entry, read for its `cells` and its `proofs`.
    `here_os` is this machine's system, `windows`, `macos` or `linux`.
    `broken`, the reasons the rule's own spec is broken, gives `to_repair`
    first. Otherwise the first kind that applies wins, in the order of
    `KINDS`: a proof is asked for at the gate `signed` alone, and a rule the
    audit found weak is `to_strengthen`. A `@manual` proof adds no kind, and
    neither does a rule no audit has read.
    """
    if broken:
        return 'to_repair'
    cells = rule.get('cells') or {}
    passed = cells.get('passed') or {}
    word = passed.get('word')

    if gate == 'signed' and not (rule.get('proofs') or []):
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
    if (cells.get('strong') or {}).get('word') == 'weak':
        return 'to_strengthen'
    return None


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
    cell reads that word.
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


def sentence(summary):
    """`<N> rules. <p> pass their tests.`, then what the audit found where it read a rule."""
    total = summary.get('rules') or 0
    count = (summary.get('steps') or {}).get('passed') or 0
    parts = ['%d %s.' % (total, _words('rule', 'rules', total)),
             '%d %s.' % (count, _words('passes its tests',
                                        'pass their tests', count))]
    audit = summary.get('audit') or {}
    strong = audit.get('strong') or 0
    weak = audit.get('weak') or 0
    if strong + weak > 0:
        parts.append(AUDIT_FOUND % (strong, weak))
    return ' '.join(parts)


def systems_text(systems):
    """The systems in display words, Linux/Unix, macOS, Windows, joined ` and `.

    This machine's own system is never among them, so there are one or two.
    The join is the cell reasons' own, `states.systems_text`.
    """
    return states.systems_text(systems)


def left(features, gate, here_os, corrections=0):
    """`[{kind, count, text, command}]`: the work left, in the order it is done.

    `features` is the payload's feature entries; each rule is counted once,
    under the spec that owns it and lists it. `corrections` is how many
    comments above tests name something no spec has or a rule that has
    proofs, at every gate. A kind at zero is left out.
    """
    counts = {}
    if corrections:
        counts['to_correct'] = corrections
    systems = set()
    to_repair = set()
    for feature in features or ():
        for rule in feature.get('rules') or ():
            kind = rule_kind(rule, gate, here_os, feature.get('broken'))
            if kind is None:
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
    out = []
    for kind, one, many, command in KINDS:
        count = counts.get(kind)
        if not count:
            continue
        words = _words(one, many, count)
        if kind == 'to_test_remote':
            words = words % systems_text(systems)
        out.append({'kind': kind, 'count': count,
                    'text': '%d %s' % (count, words), 'command': command})
    return out


def last_line(left_items, gate, tag=None):
    """The line after the sentence when nothing is left, or None while work is.

    `RELEASE` naming the tag where HEAD carries a `passed/*` or `signed/*`
    tag; otherwise the release step, with `purlin:sign` after it at the gate
    `signed`.
    """
    if left_items:
        return None
    if tag and tag.get('name'):
        return RELEASE % tag['name']
    return TO_RELEASE_SIGNED if gate == 'signed' else TO_RELEASE


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
