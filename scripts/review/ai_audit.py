#!/usr/bin/env python3
"""The AI audit: what one rule is read with, the model call, and its answer.

    ai_audit.py --feature <f> [--rule RULE-N] [--project-root DIR]

`purlin:audit` reads each rule that needs reading through this module: it
sets the rule, its proofs and the source of each test that backs them beside
`references/review_criteria.md`, sends that prompt to the model, and reads
the answer back into a `verdict` and findings. The run script writes what comes
back into the feature's evidence; this module writes no file.

**The call.** `claude -p --output-format json`, with the prompt on stdin, so
no command line carries it, and stdin closed after the prompt. One call per
rule, `MODEL_TIMEOUT` seconds each, and `audit_parallel` calls at once. The
JSON's `result` is the answer; the model is the one its `modelUsage` names,
or `unknown` where it names none.

**The answer.** The model is asked for what it observed, never for a grade:

    settled: yes
    - <one sentence per finding, naming the proof>
    notes:
    - <one sentence per note, naming the proof>

Settled with no line is the `verdict` `strong`. Settled with lines is `weak`,
and the lines are the findings. Not settled is `undecided`, and its lines are
the reason it gives. The lines under `notes:` are the notes: a proof longer
than the standard, or holding two cases, is noted there and never makes the
rule `weak`.

**When the model cannot be reached** (no `claude` on PATH, a non-zero exit, a
timeout, or an answer with no settled line after one retry) nothing comes
back for that rule but the reason, so nothing is written and the next audit
tries again.

The command line prints what the audit reads for a rule and what the last
audit found, from the payload. It calls no model and writes no file.

Exit codes: 0 a rule was printed, 1 the rule is not in the project, 2 the
command line was wrong.
"""

import concurrent.futures
import hashlib
import json
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
                    payload as payload_module)

USAGE = ('Usage: ai_audit.py --feature <f> [--rule RULE-N] '
         '[--project-root DIR]')

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

CRITERIA = os.path.join('references', 'review_criteria.md')

# The command, and how long one call may take.
COMMAND = ('claude', '-p', '--output-format', 'json')
MODEL_TIMEOUT = 300

# Why a call could not be made, one sentence per cause. The run prints one
# line per cause with a count, and the strong cell names the cause.
NOT_ON_PATH = 'claude is not on PATH'
EXITED = 'claude exited with an error'
TIMED_OUT = 'claude timed out after %d s'
NO_ANSWER = 'claude answered without a settled line'


# ---------------------------------------------------------------------------
# What one rule is read with
# ---------------------------------------------------------------------------

def load_payload(project_root, payload=None):
    """The payload to read, built when the caller did not hand one over."""
    if payload is not None:
        return payload
    return payload_module.build_payload(project_root, generated_by='audit')


def rule_entry(payload, feature, rule):
    """The rule dict for `<feature> <rule>`, or None.

    A required rule belongs to the feature its own `feature` field names, so a
    rule is read where it lives and not once per consumer.
    """
    for entry in (payload or {}).get('features') or ():
        for item in entry.get('rules') or ():
            if item.get('feature') == feature and item.get('id') == rule:
                return item
    return None


def is_read(entry, again=False):
    """True when the audit reads this rule.

    A rule is read when it is its feature's own, at least one of its proofs
    has a test, its passed cell reads `passed`, and it has no audit entry for
    its current rule, proof and test hashes. The same rules are read at every
    gate. `again` drops the condition about an existing entry, which is what
    `--all` asks for.
    """
    entry = entry or {}
    if entry.get('label', 'own') != 'own':
        return False
    passed = ((entry.get('cells') or {}).get('passed') or {}).get('word')
    if passed != 'passed':
        return False
    if not any(proof.get('tests') and not proof.get('manual')
               for proof in entry.get('proofs') or ()):
        return False
    return again or not entry.get('audit')


def reading_for(project_root, payload, feature, rule):
    """What the audit reads for one rule, as a dict. None when it is not there."""
    payload = load_payload(project_root, payload)
    entry = rule_entry(payload, feature, rule)
    if entry is None:
        return None
    gate = payload.get('gate') or {}
    proofs = [{'id': proof.get('id'), 'manual': bool(proof.get('manual')),
               'env': proof.get('env'), 'text': proof.get('text')}
              for proof in entry.get('proofs') or ()]
    return {
        'feature': feature,
        'rule': rule,
        'rule_text': entry.get('text'),
        'proofs': proofs,
        'rule_hash': entry.get('rule_hash'),
        'proof_hash': entry.get('proof_hash'),
        'test_hash': entry.get('test_hash'),
        'tests': _test_layer(project_root, feature, entry),
        'test_strength': _feature_entry(payload, feature).get('test_strength'),
        'min_strength': gate.get('min_strength'),
        'audit': entry.get('audit'),
    }


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
# The prompt
# ---------------------------------------------------------------------------

def criteria_text(project_root):
    """The plugin's `references/review_criteria.md`, verbatim."""
    path = os.path.join(_ROOT, CRITERIA)
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()
    return ''


def criteria_hash(text):
    """The sha256 of the criteria as they were sent, which each entry records."""
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


# What the model is asked for: what the test observes set against what the
# proof names, one sentence at a time, and a plain statement when it cannot
# tell. Never a recommendation and never a grade.
INSTRUCTION = (
    'Read one rule against the criteria above and report what you see: '
    'set each proof against the test body below it and say what you '
    'observed. Answer in this shape and nothing else:',
    '',
    '    settled: yes',
    '    - <one sentence, naming the proof it concerns>',
    '    notes:',
    '    - <one sentence, naming the proof it concerns>',
    '',
    'Write `settled: yes` when you could tell what each test observes against '
    'what its proof names, and `settled: no` when you could not.',
    'Write one line per observation, each opening with `- `, each one sentence '
    'long, and each naming the proof it concerns. Write no line at all when '
    'you observed nothing.',
    'Write a note, under notes:, for a proof longer than 60 words or one '
    'holding more than one case, one sentence naming the proof, and never an '
    'observation for it: a note does not make the rule weak. Leave out '
    '`notes:` when you have no note.',
    'Do not recommend a change, do not grade the rule and do not score it. A '
    'person reads what you write and decides.',
)


def model_prompt(project_root, reading, criteria=None):
    """The criteria verbatim, then this rule's rule, proof, test and numbers."""
    text = criteria_text(project_root) if criteria is None else criteria
    parts = [text, '', '---', '']
    parts.extend(INSTRUCTION)
    parts.extend([
        '',
        '%s %s' % (reading.get('feature'), reading.get('rule')),
        'Rule: %s' % (reading.get('rule_text') or '')])
    for proof in reading.get('proofs') or ():
        parts.append('%s%s: %s' % (proof.get('id'), _proof_tags(proof),
                                   proof.get('text')))
    for test in reading.get('tests') or ():
        parts.append('')
        parts.append('Test for %s: %s::%s'
                     % (test.get('proof'), test.get('file'), test.get('name')))
        if test.get('body'):
            parts.append(test['body'])
    parts.append('')
    parts.append('Test strength: %s'
                 % _strength_words(reading, '(minimum %s)'))
    return '\n'.join(parts)


def _strength_words(reading, minimum):
    """The strength in words: `not measured`, or the percent and `minimum`."""
    strength = reading.get('test_strength')
    if strength is None:
        return 'not measured'
    words = '%d percent' % strength
    if reading.get('min_strength') is not None:
        words += ' ' + minimum % reading['min_strength']
    return words


# ---------------------------------------------------------------------------
# The answer
# ---------------------------------------------------------------------------

_SETTLED_RE = re.compile(r'^\s*settled\s*:\s*(yes|no|true|false)\s*$', re.I)
_NOTES_RE = re.compile(r'^\s*notes\s*:\s*$', re.I)
_FINDING_RE = re.compile(r'^\s*[-*]\s+(.*\S)\s*$')


def _read_answer(answer):
    """`(findings, settled, notes)`: each `- ` line is a finding until a
    `notes:` line, and a note after it."""
    settled = None
    findings, notes = [], []
    lines = findings
    for line in str(answer or '').splitlines():
        found = _SETTLED_RE.match(line)
        if found:
            settled = found.group(1).lower() in ('yes', 'true')
            continue
        if _NOTES_RE.match(line):
            lines = notes
            continue
        found = _FINDING_RE.match(line)
        if found:
            lines.append(found.group(1))
    return findings, settled, notes


def parse_answer(answer):
    """`(findings, settled)` read out of one model answer.

    `settled` is True, False, or None for an answer that never says whether
    it settled, which is not an answer the audit can record. A line under
    `notes:` is not a finding.
    """
    findings, settled, _notes = _read_answer(answer)
    return findings, settled


def answer_notes(answer):
    """The lines under `notes:` in one model answer, `[]` when there are none."""
    return _read_answer(answer)[2]


def verdict_of(findings, settled):
    """`strong`, `weak` or `undecided`, or None when the answer did not say."""
    if settled is None:
        return None
    if not settled:
        return 'undecided'
    return 'weak' if findings else 'strong'


def model_name(body):
    """The model the CLI's JSON names, or `unknown`.

    A top-level `model` is read first. Otherwise `modelUsage` names each model
    the call used; the one that wrote the most output answered.
    """
    if not isinstance(body, dict):
        return 'unknown'
    if isinstance(body.get('model'), str) and body['model'].strip():
        return body['model'].strip()
    usage = body.get('modelUsage')
    if isinstance(usage, dict) and usage:
        def weight(name):
            entry = usage.get(name)
            tokens = entry.get('outputTokens') if isinstance(entry, dict) else 0
            return (-(tokens if isinstance(tokens, (int, float)) else 0), name)
        return sorted(usage, key=weight)[0]
    return 'unknown'


# ---------------------------------------------------------------------------
# The call
# ---------------------------------------------------------------------------

def claude_path():
    """Where `claude` is on PATH, or None."""
    return shutil.which(COMMAND[0])


def ask_model(project_root, prompt, command=None, runner=None):
    """`(answer, model, why)` for one call.

    The prompt goes on stdin and stdin is closed after it, so the command
    line never carries it. `why` is None when the model answered, and names
    the cause otherwise. `runner` stands in for `subprocess.run` in a test.
    """
    command = command or claude_path()
    if not command:
        return None, None, NOT_ON_PATH
    runner = runner or subprocess.run
    try:
        result = runner([command] + list(COMMAND[1:]), input=prompt,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', cwd=project_root,
                        timeout=MODEL_TIMEOUT)
    except subprocess.TimeoutExpired:
        return None, None, TIMED_OUT % MODEL_TIMEOUT
    except (OSError, subprocess.SubprocessError):
        return None, None, EXITED
    if result.returncode != 0:
        return None, None, EXITED
    stdout = result.stdout or ''
    try:
        body = json.loads(stdout)
    except ValueError:
        return stdout, 'unknown', None
    if not isinstance(body, dict):
        return stdout, 'unknown', None
    answer = body.get('result')
    return (answer if isinstance(answer, str) else ''), model_name(body), None


def audit_one(project_root, reading, criteria, command=None, runner=None):
    """What the audit found for one rule, or why it could not ask.

    `{'verdict', 'findings', 'notes', 'model', 'criteria'}` when the model
    answered, where `criteria` is the sha256 of the criteria it was sent and
    `notes` never changes the verdict; `{why}` when it could not be reached.
    An answer with no settled line is asked once more before it counts as no
    answer.
    """
    prompt = model_prompt(project_root, reading, criteria)
    for _attempt in range(2):
        answer, model, why = ask_model(project_root, prompt, command, runner)
        if why:
            return {'why': why}
        findings, settled = parse_answer(answer)
        answered = verdict_of(findings, settled)
        if answered:
            return {'verdict': answered, 'findings': findings,
                    'notes': answer_notes(answer), 'model': model,
                    'criteria': criteria_hash(criteria)}
    return {'why': NO_ANSWER}


def audit_all(project_root, readings, parallel, runner=None):
    """One result per reading, in order, `parallel` calls at once.

    With no `claude` on PATH nothing is called and every reading carries
    that reason.
    """
    readings = list(readings or ())
    command = claude_path()
    if not command:
        return [{'why': NOT_ON_PATH} for _ in readings]
    criteria = criteria_text(project_root)
    workers = max(1, min(int(parallel or 1), len(readings) or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(audit_one, project_root, reading, criteria,
                               command, runner) for reading in readings]
        return [future.result() for future in futures]


# ---------------------------------------------------------------------------
# The text a person reads
# ---------------------------------------------------------------------------

def render(reading):
    """One rule as the audit reads it, and what the last audit found."""
    lines = ['%s %s' % (reading.get('feature'), reading.get('rule')),
             '', 'Rule', '  %s' % (reading.get('rule_text') or ''), '',
             'Proof']
    for proof in reading.get('proofs') or ():
        lines.append('  %s%s: %s' % (proof.get('id'), _proof_tags(proof),
                                     proof.get('text')))
    lines.extend(['', 'Test'])
    if not reading.get('tests'):
        lines.append('  Nothing backs this rule yet.')
    for test in reading.get('tests') or ():
        if test.get('file'):
            lines.append('  %s  %s::%s' % (test.get('proof'), test['file'],
                                           test.get('name')))
        else:
            lines.append('  %s  manual' % test.get('proof'))
        for line in (test.get('body') or '').splitlines():
            lines.append('    %s' % line)
    # A person is told nothing of strength where none was measured.
    if reading.get('test_strength') is not None:
        lines.extend(['', 'Test strength: %s'
                      % _strength_words(reading, '  minimum %s')])
    lines.extend(['', 'What the audit found'])
    audit = reading.get('audit') or {}
    if not audit:
        lines.append("  Nothing yet: no audit has read this rule's text, "
                     "proof and test.")
    else:
        lines.append('  %s, by %s at %s.'
                     % (str(audit.get('verdict') or '').capitalize(),
                        audit.get('model') or 'unknown',
                        audit.get('at') or 'an unknown time'))
        for finding in audit.get('findings') or ():
            lines.append('  %s' % finding)
        if not audit.get('findings'):
            lines.append('  It found nothing.')
    lines.append('')
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class _Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    __slots__ = ('feature', 'rule', 'project_root', 'error', 'help')

    def __init__(self):
        self.feature = None
        self.rule = None
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
        if item in ('--feature', '--rule', '--project-root'):
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
        print('ai_audit.py: %s' % args.error, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    if not os.path.isdir(args.project_root or '.'):
        print('ai_audit.py: not a directory: %r' % args.project_root,
              file=sys.stderr)
        return EXIT_BAD_INVOCATION

    payload = load_payload(args.project_root)
    rules = ([args.rule] if args.rule
             else _rules_of(payload, args.feature))
    if not rules:
        print('audit: no rule of %s is in this project.' % args.feature)
        return EXIT_NOTHING

    shown = 0
    for rule in rules:
        reading = reading_for(args.project_root, payload, args.feature, rule)
        if reading is None:
            continue
        print(render(reading))
        shown += 1
    return EXIT_OK if shown else EXIT_NOTHING


def _rules_of(payload, feature):
    entry = _feature_entry(payload, feature)
    return [rule['id'] for rule in entry.get('rules') or ()
            if rule.get('feature') == feature]


if __name__ == '__main__':
    sys.exit(main())
