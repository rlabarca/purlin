#!/usr/bin/env python3
"""Build the brief the machine writes about one rule.

    brief.py --feature <f> [--rule RULE-N] [--ai] [--project-root DIR]

The brief reports; it recommends nothing. It sets the rule, its proofs and
the source of each test that backs them beside the evidence, in two layers,
and stops when it has enough for the rule's level:

    passed  the test strength the evidence holds
    strong  plus the AI audit, which reads the rule, the proofs and the
            test source against `references/review_criteria.md`

The AI audit writes what it observed in plain sentences. A settled audit
that observed a gap leaves the strong cell reading `weak` with that sentence
as the reason.

What the brief ends with is three things and no judgment: the test strength
beside the project minimum, the audit's observations one sentence at a time,
and whether the audit settled the question. A rule whose brief settled with
nothing observed is one the machine could read; an audit that could not
settle leaves the strong cell reading `unsettled`.

No file is written. `purlin:audit` reads each brief it builds into the
feature's evidence, as the rule's entry under `audit.rules` keyed by the
rule, proof and test hashes the brief was built over; this command prints
the brief and nothing else.

Exit codes: 0 a brief was built, 1 the rule is not in the project, 2 the
command line was wrong.
"""

import os
import re
import shutil
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _path in (_MCP_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import marked_tests                                           # noqa: E402
from purlin import (console as console_module,                 # noqa: E402
                    payload as payload_module,
                    signatures as signatures_module, states)

USAGE = ('Usage: brief.py --feature <f> [--rule RULE-N] [--ai] '
         '[--project-root DIR]')

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

CRITERIA = os.path.join('references', 'review_criteria.md')

# The layers, cheapest first, and the level each set is built for. The AI
# audit runs on the rules whose level is `strong` or `signed`.
LAYERS = ('test strength', 'AI audit')
_LAYERS_BY_LEVEL = {
    'passed': LAYERS[:1],
    'strong': LAYERS,
    'signed': LAYERS,
}

# What the brief writes where no model could be reached. The strong cell
# reads this word and treats the AI audit as one that never ran, so the name
# lives in the module that reads it.
NOT_AVAILABLE = states.NO_MODEL


# ---------------------------------------------------------------------------
# One brief
# ---------------------------------------------------------------------------

def load_payload(project_root, payload=None):
    """The payload to read, built when the caller did not hand one over."""
    if payload is not None:
        return payload
    return payload_module.build_payload(project_root, generated_by='brief')


def rule_entry(payload, feature, rule):
    """The rule dict for `<feature> <rule>`, or None.

    A required rule belongs to the feature its own `feature` field names, so a
    brief is built where the rule lives and not once per consumer.
    """
    for entry in (payload or {}).get('features') or ():
        for item in entry.get('rules') or ():
            if item.get('feature') == feature and item.get('id') == rule:
                return item
    return None


def triple_for(entry):
    """The triple hash of one rule entry."""
    return signatures_module.triple_hash(
        entry.get('rule_hash'), entry.get('proof_hash'), entry.get('test_hash'))


def build_brief(project_root, payload, feature, rule, ai=False):
    """The brief for one rule, as a dict. None when the rule is not there."""
    payload = load_payload(project_root, payload)
    entry = rule_entry(payload, feature, rule)
    if entry is None:
        return None

    level = entry.get('level') or 'passed'
    layers = _LAYERS_BY_LEVEL.get(level, _LAYERS_BY_LEVEL['passed'])
    gate = payload.get('gate') or {}
    min_strength = gate.get('min_strength') or 0
    feature_entry = _feature_entry(payload, feature)

    proofs = [{'id': proof.get('id'), 'manual': bool(proof.get('manual')),
               'env': proof.get('env'), 'text': proof.get('text')}
              for proof in entry.get('proofs') or ()]

    brief = {
        'feature': feature,
        'rule': rule,
        'level': level,
        'rule_text': entry.get('text'),
        'proofs': proofs,
        'rule_hash': entry.get('rule_hash'),
        'proof_hash': entry.get('proof_hash'),
        'test_hash': entry.get('test_hash'),
        'test_hash_kind': entry.get('test_hash_kind'),
        'triple_hash': triple_for(entry),
        'layers': list(layers),
        'tests': _test_layer(project_root, feature, entry),
        'test_strength': None,
        'min_strength': min_strength,
        'ai_review': None,
        'observations': [],
        'settled': None,
        'generated_at': payload_module.now_iso(),
    }

    if 'test strength' in layers:
        brief['test_strength'] = feature_entry.get('test_strength')

    if 'AI audit' in layers:
        brief['ai_review'] = (_ai_audit(project_root, brief) if ai
                              else NOT_AVAILABLE)
        brief['observations'], brief['settled'] = model_observations(
            brief['ai_review'])

    return brief


def asks_for_a_review(entry):
    """True when the AI audit runs on a rule: its level is `strong` or `signed`.

    The strong cell asks the same question when it decides whether a brief
    was owed, so the answer is computed from the one place that knows it.
    """
    return (entry or {}).get('level') in ('strong', 'signed')


def _feature_entry(payload, feature):
    for entry in (payload or {}).get('features') or ():
        if entry.get('name') == feature:
            return entry
    return {}


def _proof_tags(proof):
    """The tags a proof line carries, as the spec writes them, or ''."""
    tags = ' @manual' if proof.get('manual') else ''
    if proof.get('env'):
        tags += ' @env(%s)' % proof['env']
    return tags


def _test_layer(project_root, feature, entry):
    """One entry per test backing the rule, with its source."""
    seen = set()
    tests = []
    for proof in entry.get('proofs') or ():
        if proof.get('manual'):
            tests.append({'proof': proof.get('id'), 'file': None, 'name': None,
                          'body': None, 'manual': True})
            continue
        for test in proof.get('tests') or ():
            key = (proof.get('id'), test.get('file'), test.get('name'))
            if key in seen:
                continue
            seen.add(key)
            tests.append(_one_test(project_root, feature, proof.get('id'),
                                   test))
    return tests


def _one_test(project_root, feature, proof_id, test):
    path = test.get('file') or ''
    body = None
    if path:
        try:
            body = marked_tests.source(
                project_root, feature, proof_id, path, test.get('name'))
        except (OSError, UnicodeDecodeError, ValueError):
            body = None
    return {'proof': proof_id, 'file': path or None,
            'name': test.get('name'), 'body': body, 'manual': False}


# ---------------------------------------------------------------------------
# The AI audit
# ---------------------------------------------------------------------------

def criteria_text(project_root):
    """`references/review_criteria.md`, verbatim, from the plugin or project."""
    for base in (_ROOT, project_root):
        path = os.path.join(base, CRITERIA)
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as handle:
                return handle.read()
    return ''


# What the model is asked for: what the test observes set against what the
# proof names, one sentence at a time, and a plain statement when it cannot
# tell. Never a recommendation and never a grade: the brief reports, and the
# person reading it decides.
INSTRUCTION = (
    'Read one rule against the criteria above and report what you see: '
    'set each proof against the test body below it and say what you '
    'observed. Answer in this shape and nothing else:',
    '',
    '    settled: yes',
    '    - <one sentence, naming the proof it concerns>',
    '',
    'Write `settled: yes` when you could tell what each test observes against '
    'what its proof names, and `settled: no` when you could not.',
    'Write one line per observation, each opening with `- `, each one sentence '
    'long, and each naming the proof it concerns. Write no line at all when '
    'you observed nothing.',
    'Do not recommend a change, do not grade the rule and do not score it. A '
    'person reads what you write and decides.',
)


def model_prompt(project_root, brief):
    """The criteria verbatim, then this rule's rule, proof, test and numbers."""
    parts = [criteria_text(project_root), '', '---', '']
    parts.extend(INSTRUCTION)
    parts.extend([
        '',
        '%s %s (level %s)'
        % (brief.get('feature'), brief.get('rule'), brief.get('level')),
        'Rule: %s' % (brief.get('rule_text') or '')])
    for proof in brief.get('proofs') or ():
        parts.append('%s%s: %s' % (proof.get('id'), _proof_tags(proof),
                                   proof.get('text')))
    for test in brief.get('tests') or ():
        parts.append('')
        parts.append('Test for %s: %s::%s'
                     % (test.get('proof'), test.get('file'), test.get('name')))
        if test.get('body'):
            parts.append(test['body'])
    strength = brief.get('test_strength')
    parts.append('')
    parts.append('Test strength: %s (minimum %s)'
                 % ('n/a' if strength is None else '%d percent' % strength,
                    brief.get('min_strength')))
    return '\n'.join(parts)


def _ai_audit(project_root, brief):
    """The model's answer, or `not available` when no model can be reached."""
    if not shutil.which('claude'):
        return NOT_AVAILABLE
    try:
        result = subprocess.run(
            ['claude', '-p', model_prompt(project_root, brief)],
            capture_output=True, text=True, cwd=project_root, timeout=300)
    except (subprocess.SubprocessError, OSError):
        return NOT_AVAILABLE
    if result.returncode != 0 or not result.stdout.strip():
        return NOT_AVAILABLE
    return result.stdout.strip()


_SETTLED_RE = re.compile(r'^\s*settled\s*:\s*(yes|no|true|false)\s*$', re.I)
_OBSERVATION_RE = re.compile(r'^\s*[-*]\s+(.*\S)\s*$')


def model_observations(answer):
    """`(observations, settled)` read out of one model answer.

    An answer nobody could get, or one that never says whether it settled,
    leaves `settled` None: the strong cell reads that as a question still
    open, which is the honest reading of an answer that is not there.
    """
    if not answer or answer == NOT_AVAILABLE:
        return [], None
    settled = None
    observations = []
    for line in str(answer).splitlines():
        found = _SETTLED_RE.match(line)
        if found:
            settled = found.group(1).lower() in ('yes', 'true')
            continue
        found = _OBSERVATION_RE.match(line)
        if found:
            observations.append(found.group(1))
    return observations, settled


# ---------------------------------------------------------------------------
# The text a person reads
# ---------------------------------------------------------------------------

def render_brief(brief):
    """The brief as text: the rule, the proof, the test, and what it found."""
    lines = []
    lines.append('%s %s   level %s'
                 % (brief.get('feature'), brief.get('rule'), brief.get('level')))
    lines.append('')
    lines.append('Rule')
    lines.append('  %s' % (brief.get('rule_text') or ''))
    lines.append('')
    lines.append('Proof')
    for proof in brief.get('proofs') or ():
        lines.append('  %s%s: %s' % (proof.get('id'), _proof_tags(proof),
                                     proof.get('text')))
    lines.append('')
    lines.append('Test')
    if not brief.get('tests'):
        lines.append('  Nothing backs this rule yet.')
    for test in brief.get('tests') or ():
        if test.get('file'):
            lines.append('  %s  %s::%s' % (test.get('proof'), test['file'],
                                           test.get('name')))
        else:
            lines.append('  %s  manual' % test.get('proof'))
        for line in (test.get('body') or '').splitlines():
            lines.append('    %s' % line)
    lines.append('')
    strength = brief.get('test_strength')
    if 'test strength' in (brief.get('layers') or ()):
        lines.append('Test strength: %s   minimum %s'
                     % ('n/a' if strength is None else '%d percent' % strength,
                        brief.get('min_strength')))
    # The AI audit is printed only where one was asked for, so a brief for
    # a rule whose level is `passed` says nothing about an audit that was
    # never owed.
    if brief.get('ai_review') is not None:
        if brief['ai_review'] != NOT_AVAILABLE:
            lines.append('')
            lines.append('AI audit')
            for line in str(brief['ai_review']).splitlines():
                lines.append('  %s' % line)
        lines.append('')
        lines.append('Observations')
        for observation in brief.get('observations') or ():
            lines.append('  %s' % observation)
        if not brief.get('observations'):
            lines.append('  None.')
        lines.append('Settled: %s' % _settled_word(brief.get('settled')))
    lines.append('')
    return '\n'.join(lines)


def _settled_word(settled):
    """`yes`, `no` or `not answered`, the three answers an AI audit gives."""
    if settled is True:
        return 'yes'
    if settled is False:
        return 'no'
    return 'not answered'


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class _Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    __slots__ = ('feature', 'rule', 'ai', 'project_root', 'error', 'help')

    def __init__(self):
        self.feature = None
        self.rule = None
        self.ai = False
        self.project_root = '.'
        self.error = None
        self.help = False


def _parse(argv):
    args = _Args()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ('-h', '--help'):
            args.help = True
            return args
        if item == '--ai':
            args.ai = True
        elif item in ('--feature', '--rule', '--project-root'):
            if not rest:
                args.error = '%s needs a value.' % item
                return args
            value = rest.pop(0)
            setattr(args, item[2:].replace('-', '_'), value)
        else:
            args.error = 'unexpected argument %s' % item
            return args
    if not args.feature:
        args.error = '--feature is required.'
    return args


def main(argv=None):
    console_module.force_utf8_stdio()
    args = _parse(sys.argv[1:] if argv is None else argv)
    if args.help:
        print(__doc__.strip())
        return EXIT_OK
    if args.error:
        print(USAGE, file=sys.stderr)
        print('brief.py: %s' % args.error, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    if not os.path.isdir(args.project_root or '.'):
        print('brief.py: not a directory: %r' % args.project_root,
              file=sys.stderr)
        return EXIT_BAD_INVOCATION

    payload = load_payload(args.project_root)
    rules = ([args.rule] if args.rule
             else _rules_of(payload, args.feature))
    if not rules:
        print('brief: no rule of %s is in this project.' % args.feature)
        return EXIT_NOTHING

    built = 0
    for rule in rules:
        brief = build_brief(args.project_root, payload, args.feature, rule,
                            ai=args.ai)
        if brief is None:
            continue
        print(render_brief(brief))
        built += 1
    return EXIT_OK if built else EXIT_NOTHING


def _rules_of(payload, feature):
    entry = _feature_entry(payload, feature)
    return [rule['id'] for rule in entry.get('rules') or ()
            if rule.get('feature') == feature]


if __name__ == '__main__':
    sys.exit(main())
