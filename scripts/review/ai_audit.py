#!/usr/bin/env python3
"""The AI audit's model: what one rule is read with, the call, and its answer.

    ai_audit.py --feature <f> [--rule RULE-N] [--project-root DIR]

`purlin:audit` runs through `scripts/review/audit_run.py`, which runs the
heuristic spot tests, then one planted bug per proof, then the model's reading
of each rule. This module holds the model's two parts. It sets a rule, its
proofs, the source of each test that backs them and the findings of the spot
tests and the planted bugs beside `references/review_criteria.md`, sends that
prompt to the model, and reads the answer back as the explanation under the
findings. It also asks the model for a planted bug (`ask_for_bug`). It
decides no verdict and writes no file.

**The call.** `claude -p --output-format json`, with the prompt on stdin, so
no command line carries it, and stdin closed after the prompt. One call per
rule, `MODEL_TIMEOUT` seconds each, `AUDIT_PARALLEL` calls at once. The JSON's
`result` is the answer; the model is the one its `modelUsage` names, or
`unknown` where it names none; `total_cost_usd` is what the call cost.

**The answer.** One sentence per line opening `- `, the explanation; the lines
under a `notes:` line are the notes. The answer sets no verdict.

**When the model cannot be reached** (no `claude` on PATH, a non-zero exit or
a timeout) nothing comes back for that rule but the reason, and the audit's
run writes the rule no `strong` (ai_audit RULE-43).

The command line prints what the audit reads for a rule and what the last
audit found, from the payload, with each note after the findings. It calls no
model and writes no file. A rule no spec has is named on one line, and a
settings file that cannot be read stops it before the payload is built.

Exit codes: 0 a rule was printed, 1 the rule is not in the project or the
settings file cannot be read, 2 the command line was wrong.
"""

import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _path in (_MCP_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import config_engine                                          # noqa: E402
import marked_tests                                           # noqa: E402
from purlin import (console as console_module,                 # noqa: E402
                    payload as payload_module)

NOT_A_RULE = ('%s %s is not a rule any spec has. Run purlin:status %s to see '
              'its rules.')


def not_a_rule(feature, rule):
    """The line naming a rule no spec has, filled in for `feature` and `rule`."""
    return NOT_A_RULE % (feature, rule, feature)


USAGE = ('Usage: ai_audit.py --feature <f> [--rule RULE-N] '
         '[--project-root DIR]')

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

CRITERIA = os.path.join('references', 'review_criteria.md')

# The command, how long one call may take, and how many run at once.
COMMAND = ('claude', '-p', '--output-format', 'json')
MODEL_TIMEOUT = 300
AUDIT_PARALLEL = 4

# Why a call could not be made, one sentence per cause.
NOT_ON_PATH = 'claude is not on PATH'
EXITED = 'claude exited with an error'
TIMED_OUT = 'claude timed out after %d s'

# What a person reads of the last audit, the same on every surface.
NO_AUDIT = "No audit has read this rule's text, proof and test yet."
STRONG_NOTHING = 'Strong. It found nothing.'
VERDICT_WORDS = {'strong': 'Strong.', 'weak': 'Weak.'}
NO_TEST_YET = '  No test yet. Run purlin:build %s.'


class ModelUnreachable(Exception):
    """The model could not be reached; `str(error)` is the reason."""


# ---------------------------------------------------------------------------
# What one rule is read with
# ---------------------------------------------------------------------------

def load_payload(project_root, payload=None):
    """The payload to read, built when the caller did not hand one over."""
    if payload is not None:
        return payload
    return payload_module.build_payload(project_root, generated_by='audit')


def rule_entry(payload, feature, rule):
    """The rule dict for `<feature> <rule>`, or None."""
    for entry in (payload or {}).get('features') or ():
        for item in entry.get('rules') or ():
            if item.get('feature') == feature and item.get('id') == rule:
                return item
    return None


def passes(entry):
    """True when the rule passes its tests: its passed cell reads `passed`."""
    cells = (entry or {}).get('cells') or {}
    return ((cells.get('passed') or {}).get('word')) == 'passed'


def tested(entry):
    """True when at least one proof of the rule has a test, not by hand."""
    return any(proof.get('tests') and not proof.get('manual')
               for proof in (entry or {}).get('proofs') or ())


def is_read(entry, again=False, code_changed=False):
    """True when the audit reads this rule (ai_audit RULE-1).

    A rule is read when at least one of its proofs has a test, its passed
    cell reads `passed`, and it has no audit entry for its current rule,
    proof and test, or its feature's code changed since that entry
    (`code_changed`, which the caller works out). `again` drops the
    condition about an existing entry, which is what `--all` asks for.
    """
    if not passes(entry) or not tested(entry):
        return False
    return again or not (entry or {}).get('audit') or bool(code_changed)


def reading_for(project_root, payload, feature, rule, findings=()):
    """What the audit reads for one rule, as a dict. None when it is not there.

    `findings` are the spot tests' and the planted bugs' sentences for the
    rule, which the prompt sets after the tests.
    """
    payload = load_payload(project_root, payload)
    entry = rule_entry(payload, feature, rule)
    if entry is None:
        return None
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
        'anchor': bool(_feature_entry(payload, feature).get('is_anchor')),
        'findings': [str(line) for line in findings or ()],
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

def criteria_text(project_root=None):
    """The plugin's `references/review_criteria.md`, verbatim."""
    path = os.path.join(_ROOT, CRITERIA)
    if os.path.isfile(path):
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()
    return ''


def criteria_hash(text):
    """The sha256 of the criteria as they were sent, which each entry records."""
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()


def model_prompt(project_root, reading, criteria=None):
    """The criteria verbatim, then the rule, its proofs, each test's source,
    and the findings of the spot tests and the planted bugs."""
    text = criteria_text(project_root) if criteria is None else criteria
    parts = [text, '', '---', '',
             '%s %s' % (reading.get('feature'), reading.get('rule')),
             'Rule: %s' % (reading.get('rule_text') or '')]
    for proof in reading.get('proofs') or ():
        parts.append('%s%s: %s' % (proof.get('id'), _proof_tags(proof),
                                   proof.get('text')))
    for test in reading.get('tests') or ():
        parts.append('')
        if test.get('manual'):
            parts.append('Test for %s: checked by hand' % test.get('proof'))
            continue
        parts.append('Test for %s: %s::%s'
                     % (test.get('proof'), test.get('file'), test.get('name')))
        if test.get('body'):
            parts.append(test['body'].rstrip('\n'))
    parts.extend(['', 'Findings:'])
    findings = reading.get('findings') or ()
    parts.extend('- %s' % line for line in findings)
    if not findings:
        parts.append('none')
    return '\n'.join(parts) + '\n'


# ---------------------------------------------------------------------------
# The answer
# ---------------------------------------------------------------------------

_NOTES_RE = re.compile(r'^\s*notes\s*:\s*$', re.I)
_LINE_RE = re.compile(r'^\s*[-*]\s+(.*\S)\s*$')


def read_answer(answer):
    """`(explanation, notes)`: each `- ` line is a sentence of the
    explanation until a `notes:` line, and a note after it."""
    explanation, notes = [], []
    lines = explanation
    for line in str(answer or '').splitlines():
        if _NOTES_RE.match(line):
            lines = notes
            continue
        found = _LINE_RE.match(line)
        if found:
            lines.append(found.group(1))
    return explanation, notes


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


def _cost(body):
    cost = body.get('total_cost_usd') if isinstance(body, dict) else None
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        return None
    return float(cost)


# ---------------------------------------------------------------------------
# The call
# ---------------------------------------------------------------------------

def claude_path():
    """Where `claude` is on PATH, or None."""
    return shutil.which(COMMAND[0])


def ask_model(project_root, prompt, command=None, runner=None):
    """One call: `{'answer', 'model', 'why', 'cost_usd', 'seconds'}`.

    The prompt goes on stdin and stdin is closed after it, so the command
    line never carries it. `why` is None when the model answered, and names
    the cause otherwise. `cost_usd` is the answer's `total_cost_usd`, or None.
    `runner` stands in for `subprocess.run` in a test.
    """
    found = {'answer': None, 'model': None, 'why': None, 'cost_usd': None,
             'seconds': 0.0}
    command = command or claude_path()
    if not command:
        found['why'] = NOT_ON_PATH
        return found
    runner = runner or subprocess.run
    started = time.time()
    try:
        result = runner([command] + list(COMMAND[1:]), input=prompt,
                        capture_output=True, text=True, encoding='utf-8',
                        errors='replace', cwd=project_root,
                        timeout=MODEL_TIMEOUT)
    except subprocess.TimeoutExpired:
        result = None
        found['why'] = TIMED_OUT % MODEL_TIMEOUT
    except (OSError, subprocess.SubprocessError):
        result = None
        found['why'] = EXITED
    found['seconds'] = time.time() - started
    if result is None:
        return found
    if result.returncode != 0:
        found['why'] = EXITED
        return found
    stdout = result.stdout or ''
    try:
        body = json.loads(stdout)
    except ValueError:
        body = None
    if not isinstance(body, dict):
        found.update(answer=stdout, model='unknown')
        return found
    answer = body.get('result')
    found.update(answer=answer if isinstance(answer, str) else '',
                 model=model_name(body), cost_usd=_cost(body))
    return found


def audit_one(project_root, reading, criteria, command=None, runner=None):
    """The model's reading of one rule, or why it could not be asked.

    `{'explanation', 'notes', 'model', 'criteria', 'cost_usd', 'seconds'}`
    when the model answered, where `criteria` is the sha256 of the criteria it
    was sent; only `{'why'}` when it could not be reached. The answer sets no
    verdict.
    """
    prompt = model_prompt(project_root, reading, criteria)
    called = ask_model(project_root, prompt, command, runner)
    if called['why']:
        return {'why': called['why']}
    explanation, notes = read_answer(called['answer'])
    return {'explanation': explanation, 'notes': notes,
            'model': called['model'], 'criteria': criteria_hash(criteria),
            'cost_usd': called['cost_usd'], 'seconds': called['seconds']}


def audit_all(project_root, readings, parallel=AUDIT_PARALLEL, runner=None):
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
# The planted bug's request
# ---------------------------------------------------------------------------

BUG_INSTRUCTION = (
    'Make the smallest change to one of the files below that would break '
    'what the proof says, so that a test checking the proof fails. Answer in '
    'this shape and nothing else, the lines under before: copied exactly '
    'from the file:',
    '',
    'file: <the path, as given below>',
    'before:',
    '<the exact lines>',
    'after:',
    '<the lines>',
    '',
    'or, when no change to these files can break what the proof says:',
    '',
    'no break: <why, in one sentence>',
)


def bug_prompt(project_root, request):
    """The request for one planted bug: the instruction, the rule, the proof,
    its tests' source and the text of each file the feature covers."""
    parts = list(BUG_INSTRUCTION)
    parts.extend(['', '---', '',
                  '%s %s' % (request.get('feature'), request.get('rule')),
                  'Rule: %s' % (request.get('rule_text') or ''),
                  '%s: %s' % (request.get('proof'),
                              request.get('proof_text') or '')])
    for test in request.get('tests') or ():
        parts.append('')
        parts.append('Test: %s::%s' % (test.get('file'), test.get('name')))
        if test.get('source'):
            parts.append(str(test['source']).rstrip('\n'))
    for item in request.get('files') or ():
        path, text = _file_of(project_root, item)
        parts.extend(['', 'File: %s' % path, text.rstrip('\n')])
    return '\n'.join(parts) + '\n'


def _file_of(project_root, item):
    """`(path, text)` for one file of the request, a path or a dict."""
    if isinstance(item, dict):
        path = item.get('path') or item.get('file') or ''
        text = item.get('text')
        if text is None:
            text = item.get('source')
    else:
        path, text = str(item), None
    if text is None:
        try:
            with open(os.path.join(project_root, *path.split('/')),
                      encoding='utf-8') as handle:
                text = handle.read()
        except (OSError, UnicodeDecodeError):
            text = ''
    return path, text


def ask_for_bug(project_root, request, spent=None, runner=None):
    """The model's text for one planted bug's request (the `ask` audit_run
    hands `targeted_break.break_proof`).

    Raises `ModelUnreachable(reason)` when the model cannot be reached.
    `spent`, a list, gains one `{'cost_usd', 'seconds'}` per call made.
    """
    called = ask_model(project_root, bug_prompt(project_root, request),
                       runner=runner)
    if spent is not None and called['why'] != NOT_ON_PATH:
        spent.append({'cost_usd': called['cost_usd'],
                      'seconds': called['seconds']})
    if called['why']:
        raise ModelUnreachable(called['why'])
    return called['answer'] or ''


def break_key(test_source_hash, code_part):
    """The sha256 of a proof's tests' source hash and its code part, joined
    by a line feed: a planted bug's result holds while this is unchanged."""
    return hashlib.sha256(('%s\n%s' % (test_source_hash or '',
                                       code_part or '')).encode('utf-8')
                          ).hexdigest()


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
        lines.append(NO_TEST_YET % reading.get('feature'))
    for test in reading.get('tests') or ():
        if test.get('file'):
            lines.append('  %s  %s::%s' % (test.get('proof'), test['file'],
                                           test.get('name')))
        else:
            lines.append('  %s  manual' % test.get('proof'))
        for line in (test.get('body') or '').splitlines():
            lines.append('    %s' % line)
    lines.extend(['', 'What the audit found'])
    audit = reading.get('audit') or {}
    if not audit:
        lines.append('  ' + NO_AUDIT)
    else:
        lines.extend('  %s' % line for line in verdict_lines(audit))
        lines.extend('    %s' % line
                     for line in audit.get('explanation') or ())
        lines.append('  Read by %s at %s.'
                     % (audit.get('model') or 'unknown',
                        audit.get('at') or 'an unknown time'))
        for note in audit.get('notes') or ():
            lines.append('  Note: %s' % note)
    lines.append('')
    return '\n'.join(lines)


def verdict_lines(audit):
    """What one audit entry found, one line each, as every surface words it."""
    verdict = str(audit.get('verdict') or '')
    findings = list(audit.get('findings') or ())
    if verdict == 'strong' and not findings:
        return [STRONG_NOTHING]
    if verdict in VERDICT_WORDS:
        return [VERDICT_WORDS[verdict]] + findings
    return ['%s.' % verdict.capitalize()] + findings


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
        print('ai_audit.py: %s is not a directory.' % args.project_root,
              file=sys.stderr)
        return EXIT_BAD_INVOCATION
    problem = config_engine.config_problem(args.project_root)
    if problem:
        print(problem)
        return EXIT_NOTHING

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
            if args.rule:
                print(not_a_rule(args.feature, rule))
            continue
        print(render(reading))
        shown += 1
    return EXIT_OK if shown else EXIT_NOTHING


def _rules_of(payload, feature):
    entry = _feature_entry(payload, feature)
    return [rule['id'] for rule in entry.get('rules') or ()]


if __name__ == '__main__':
    sys.exit(main())
