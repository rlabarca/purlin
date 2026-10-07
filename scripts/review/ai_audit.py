#!/usr/bin/env python3
"""The AI audit's model: what one rule is read with, the call, and its answer.

    ai_audit.py --feature <f> [--rule RULE-N] [--project-root DIR]

`purlin:audit` runs through `scripts/review/audit_run.py`, which runs the
heuristic spot tests, then asks the model about each rule, then plants each
bug the reply names. This module holds the model's part. It sets a rule, its
proofs, the source of each test that backs them and the findings of the spot
tests beside `references/review_criteria.md`, names the proofs a bug is asked
for, says to aim each past its proof's test (`REQUEST_BUGS`), holds the text
of each file the feature's scope reaches, sends that request
to the model, and reads the reply back: one part per proof, and the reading,
which becomes the explanation under the findings. It decides no verdict and
writes no file.

**An AI proof**, one tagged `@ai`, is asked a wrong output in place of a bug
(`REQUEST_OUTPUTS`): the request holds the output one passing run of its
test kept on this machine (`kept_output`), `reply.md` and each file under
`files/` as text (`output_files`), before it what the AI was given, each
file under `input/` (`input_files`), and no file of the feature's scope for
it. The part the reply holds for it has the shape any part has, its `file:`
a path inside that output.

**The call.** `COMMAND` and `SYSTEM_PROMPT`: `claude -p` with no tools, no MCP
server, no plugin, no skill, no project instructions and none of the person's
settings, started in an empty folder outside the project with
`DISABLE_PROMPT_CACHING=1`, the request on stdin, so no command line carries
it, and stdin closed after it. One call per rule, `MODEL_TIMEOUT` seconds
each, `AUDIT_PARALLEL` calls at once. The JSON's `result` is the reply; the
model is the one its `modelUsage` names, or `unknown` where it names none.

**The reply.** Cut at each line `=== PROOF-N ===` or `=== reading ===`
(`read_reply`). A proof's part names its planted bug, with its aim and the
case it breaks, which `planted_bug.parse_answer` reads. Under the reading, one sentence per line
opening `- ` is the explanation, and the lines under a `notes:` line are the
notes. A reply with no such line at all is read whole as the reading. The
reply sets no verdict.

**When the model cannot be reached** (no `claude` on PATH, a non-zero exit, a
timeout, or an answer that is empty, is not JSON or reports an error) nothing
comes back for that rule but the reason (ai_audit RULE-39).

The command line prints what the audit reads for a rule and what the last
audit found, from the payload, with each note after the findings. It calls no
model and writes no file. A rule no spec has is named on one line, and a
settings file that cannot be read stops it before the payload is built.

Exit codes: 0 a rule was printed, 1 the rule is not in the project or the
settings file cannot be read, 2 the command line was wrong.
"""

import concurrent.futures
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _path in (_MCP_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import config_engine                                          # noqa: E402
import marked_tests                                           # noqa: E402
import planted_bug                                            # noqa: E402
from purlin import (console as console_module,                 # noqa: E402
                    evidence as evidence_module,
                    outputs as outputs_module,
                    payload as payload_module,
                    states as states_module)

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

# The command, its last argument the system prompt; how long one call may
# take; and how many run at once. Each flag was checked against `claude`
# 2.1.287: no tools, no MCP server, nothing of the project or the person.
COMMAND = ('claude', '-p', '--output-format', 'json', '--max-turns', '1',
           '--tools', '', '--strict-mcp-config', '--safe-mode',
           '--setting-sources', '', '--disable-slash-commands',
           '--no-session-persistence', '--system-prompt')
SYSTEM_PROMPT = ("You review software tests for Purlin's audit. You have no "
                 "tools. Answer in exactly the shape the request gives, and "
                 "with nothing else.")
ENVIRONMENT = {'DISABLE_PROMPT_CACHING': '1'}
FOLDER_PREFIX = 'purlin-audit-'
MODEL_TIMEOUT = 300
AUDIT_PARALLEL = 4

# Why a call could not be made, one sentence per cause.
NOT_ON_PATH = 'claude is not on PATH'
EXITED = 'claude exited with an error'
TIMED_OUT = 'claude timed out after %d s'
NO_ANSWER = 'claude gave no answer'

# What a person reads of the last audit, the same on every surface.
NO_AUDIT = 'No audit has read this rule yet.'
STRONG_NOTHING = 'Strong. It found nothing.'
VERDICT_WORDS = {'strong': 'Strong.', 'weak': 'Weak.',
                 'spot-checked': 'Spot-checked.'}
SPOT_CHECKED = 'The spot tests found nothing. %s'   # the `no_bug` sentences
NO_TEST_YET = '  No test yet. Run purlin:build %s.'
# Under `Output`, for an AI proof: PROOF-N, then the folder of the kept output
# a wrong output is planted in, or `NO_OUTPUT_KEPT`.
OUTPUT_LINE = '  %s  %s'
NO_OUTPUT_KEPT = 'no passing output kept on this machine'


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
    """True when the rule passes its tests: its passed cell reads `passed`,
    or `graded` (`states.passes`)."""
    cells = (entry or {}).get('cells') or {}
    return states_module.passes((cells.get('passed') or {}).get('word'))


def tested(entry):
    """True when at least one proof of the rule has a test, not by hand."""
    return any(proof.get('tests') and not proof.get('manual')
               for proof in (entry or {}).get('proofs') or ())


def plants_for(entry, anchor=False, here=None, project_root=None):
    """The ids of the proofs the audit plants a bug for: each proof of the
    rule that has a test, is not checked by hand and is not tagged for a
    system this machine is not; none for an anchor's rule. With
    `project_root`, an AI proof this machine keeps no passing output of
    (`kept_output`) is left out as well: there is nothing to plant a wrong
    output in."""
    if anchor:
        return []
    here = here or evidence_module.host_os()
    return [proof.get('id') for proof in (entry or {}).get('proofs') or ()
            if proof.get('tests') and not proof.get('manual')
            and proof.get('env') in (None, '', here)
            and (project_root is None or not proof.get('ai')
                 or kept_output(project_root, proof))]


def kept_output(project_root, proof):
    """`(sha256, folder)` of the output a wrong one is planted in for an AI
    proof, or None for any other proof and where this machine keeps none.

    `proof` is the payload's. The output is that of the first passing run,
    on the first model the proof's tag names, whose folder this machine
    still keeps (`outputs.ai_held`); `folder` is `/` separated from the
    project root."""
    models = (proof or {}).get('ai') or ()
    for model in (proof or {}).get('models') or ():
        if not models or model.get('model') != models[0]:
            continue
        for run in model.get('runs') or ():
            if run.get('result') != 'pass' or not run.get('output'):
                continue
            folder = outputs_module.ai_held(project_root, run['output'])
            if folder:
                return run['output'], folder
    return None


def output_files(project_root, folder):
    """`[{'path', 'text'}]` for each file of a kept output the model is
    shown as what the AI produced: `reply.md`, then each file under `files/`
    in path order, each where it is UTF-8 text (`planted_bug.in_output`).
    `transcript.jsonl` and the helper's record are not shown."""
    return _shown_files(project_root, folder, planted_bug.in_output)


def input_files(project_root, folder):
    """`[{'path', 'text'}]` for each file under `input/` of a kept output,
    what the AI was given, in path order, each where it is UTF-8 text. The
    model is shown them and no wrong output changes one."""
    return _shown_files(
        project_root, folder,
        lambda rel: rel.startswith(planted_bug.OUTPUT_INPUT + '/'))


def _shown_files(project_root, folder, wanted):
    full = os.path.join(project_root, *str(folder).split('/'))
    found = []
    for rel in sorted(outputs_module.folder_files(full),
                      key=lambda rel: (rel != outputs_module.REPLY, rel)):
        if not wanted(rel):
            continue
        try:
            with open(os.path.join(full, *rel.split('/')), encoding='utf-8',
                      newline='') as handle:
                found.append({'path': rel, 'text': handle.read()})
        except (OSError, UnicodeDecodeError):
            continue
    return found


def is_read(entry, again=False, audit=None, plant=()):
    """True when the audit reads this rule (ai_audit RULE-1).

    A rule is read when at least one of its proofs has a test, its passed
    cell reads `passed` or `graded`, and it has no audit entry, an entry out of date, or
    a proof it plants a bug for with no result recorded. `audit` is the
    rule's entry as `evidence.audit_entry` gives it, with `out_of_date`, and
    `plant` the proofs of `plants_for`. `again` drops the condition about an
    existing entry, which is what `--all` asks for.
    """
    if not passes(entry) or not tested(entry):
        return False
    if again or not audit or audit.get('out_of_date'):
        return True
    bugs = audit.get('bugs') if isinstance(audit.get('bugs'),
                                           dict) else {}
    return any(proof not in bugs for proof in plant or ())


def reading_for(project_root, payload, feature, rule, findings=()):
    """What the audit reads for one rule, as a dict. None when it is not there.

    `findings` are the spot tests' sentences for the rule, which the request
    sets after the tests. `plant`, the proofs a bug is asked for, and
    `files`, the paths the feature's scope reaches, are the caller's to fill.
    A proof holds `ai`, the models its tag names, and `graded`, its grader;
    an AI proof holds `output` and `folder` as well, what `kept_output`
    gives for it, each None where this machine keeps no passing output.
    """
    payload = load_payload(project_root, payload)
    entry = rule_entry(payload, feature, rule)
    if entry is None:
        return None
    proofs = []
    for proof in entry.get('proofs') or ():
        proofs.append({'id': proof.get('id'),
                       'manual': bool(proof.get('manual')),
                       'env': proof.get('env'), 'text': proof.get('text'),
                       'ai': list(proof.get('ai') or ()),
                       'graded': proof.get('graded')})
        if proofs[-1]['ai']:
            kept = kept_output(project_root, proof) or (None, None)
            proofs[-1].update(output=kept[0], folder=kept[1])
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
        'plant': [],
        'files': [],
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
    if proof.get('ai'):
        tags += ' @ai(%s)' % ', '.join(proof['ai'])
    if proof.get('graded'):
        tags += ' @graded(%s)' % proof['graded']
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
# The request
# ---------------------------------------------------------------------------

# What asks for the planted bugs, each aimed past its proof's test: the
# proofs, the instruction, then each file of the scope.
REQUEST_BUGS = (
    '---',
    '',
    'Plant one bug for each of: %s.',
    "Each proof's test is shown above. For each proof, make the smallest "
    'change to one of the files',
    'below after which what the proof says no longer holds: the case the '
    'proof names gives a',
    "different result from the one it names. Choose the change the proof's "
    'test, as it is written,',
    'is most likely to miss: a value it never compares, a case other than '
    "the proof's, an expected",
    "value taken from the code. Where the test checks the proof's case and "
    'its result, make the',
    "plainest such change. Never a change that leaves the proof's case as it "
    'was, and no comment',
    'about the bug.',
)

# What asks for the wrong outputs, one for each AI proof, each aimed past its
# proof's test: the proofs, the instruction, then for each proof what the AI
# was given, under `INPUT_OF`, and its kept output, under `OUTPUT_OF`.
REQUEST_OUTPUTS = (
    '---',
    '',
    'Plant one wrong output for each of: %s.',
    'Each of these proofs is about what an AI produced, and its test is '
    'shown above. Below, for',
    'each proof, is what the AI was given, where it was kept, and then the '
    'output one passing run',
    'of that test kept. The input is shown and never changed. For each '
    'proof, make the smallest',
    'change to one file of its output after which what the proof says no '
    "longer holds. Choose the",
    "change the proof's test, as it is written, is most likely to miss: "
    'words it never reads, a value',
    'it never compares, a file it never opens. Where a model grades the '
    'output, choose the change a',
    'grader is most likely to accept. Where the test checks what the proof '
    'says, make the plainest',
    'such change. Never a change that leaves what the proof says true, and '
    'no note about the change.',
    'In the part, file: is a path of that output as given below, never one '
    'under input/, and case:',
    'says what the proof says and what the changed output says in its place.',
)
INPUT_OF = 'Input of %s:'
OUTPUT_OF = 'Output of %s:'

# The shape of the reply, the request's last part: with a part per proof
# (filled with the first proof asked for), or the reading alone.
REPLY_PARTS = (
    '---',
    '',
    'Answer in this shape and with nothing else. One part for each proof '
    'named above, the lines',
    'under before: copied exactly from the file, and aim: reading plain '
    "where the proof's test",
    'leaves no way past it:',
    '',
    '=== %(proof)s ===',
    'aim: <past the test, or plain>',
    "case: <the proof's case; the result the proof names; the result the "
    'changed code gives>',
    'file: <the path, as given above>',
    'before:',
    '<the exact lines>',
    'after:',
    '<the lines>',
    '',
    'or, for a proof no change to these files can break:',
    '',
    '=== %(proof)s ===',
    'no bug: <why, in one sentence>',
    '',
    'Then the reading:',
    '',
)
REPLY_ALONE = (
    '---',
    '',
    'Answer in this shape and with nothing else:',
    '',
)
REPLY_SHAPE = (
    '=== reading ===',
    '- <one sentence>',
    'notes:',
    '- <one sentence naming a proof>',
)


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
    """The one request for a rule: the criteria verbatim, then the rule, its
    proofs, each test's source and the spot tests' findings; where
    `reading['plant']` names a proof, those proofs and the text of each of
    `reading['files']`; where it names an AI proof, those proofs and each
    one's kept output (`REQUEST_OUTPUTS`); and last the shape of the
    reply."""
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
    plant = [str(proof) for proof in reading.get('plant') or ()]
    kept = {proof.get('id'): proof.get('folder')
            for proof in reading.get('proofs') or () if proof.get('ai')}
    code = [proof for proof in plant if proof not in kept]
    wrong = [proof for proof in plant if proof in kept]
    parts.append('')
    if code:
        parts.extend(line % ', '.join(code) if '%s' in line else line
                     for line in REQUEST_BUGS)
        for item in reading.get('files') or ():
            path, held = _file_of(project_root, item)
            parts.extend(['', 'File: %s' % path, held.rstrip('\n')])
        parts.append('')
    if wrong:
        parts.extend(line % ', '.join(wrong) if '%s' in line else line
                     for line in REQUEST_OUTPUTS)
        for proof in wrong:
            for title, shown in (
                    (INPUT_OF, input_files(project_root, kept[proof] or '')),
                    (OUTPUT_OF, output_files(project_root,
                                             kept[proof] or ''))):
                if title == INPUT_OF and not shown:
                    continue
                parts.extend(['', title % proof])
                for item in shown:
                    parts.extend(['', 'File: %s' % item['path'],
                                  item['text'].rstrip('\n')])
        parts.append('')
    if plant:
        parts.extend(line % {'proof': plant[0]} if '%(' in line else line
                     for line in REPLY_PARTS)
    else:
        parts.extend(REPLY_ALONE)
    parts.extend(REPLY_SHAPE)
    return '\n'.join(parts) + '\n'


def _file_of(project_root, item):
    """`(path, text)` for one file of the request, a path or a dict."""
    if isinstance(item, dict):
        path = item.get('path') or item.get('file') or ''
        text = item.get('text')
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


# ---------------------------------------------------------------------------
# The reply
# ---------------------------------------------------------------------------

_HEAD_RE = re.compile(r'^=== (PROOF-\d+|reading) ===\s*$')
_NOTES_RE = re.compile(r'^\s*notes\s*:\s*$', re.I)
_LINE_RE = re.compile(r'^\s*[-*]\s+(.*\S)\s*$')


def read_reply(text, proofs=()):
    """`({proof: its part}, explanation, notes)` from one reply.

    The reply is cut at each line `=== PROOF-N ===` or `=== reading ===`. A
    proof of `proofs` with no part is left out of the dict, and the first
    part of a proof named twice stands. A reply with no such line at all is
    read whole as the reading; one with no `=== reading ===` leaves the
    explanation empty.
    """
    wanted = [str(proof) for proof in proofs or ()]
    cuts, name, lines = [], None, []
    heads = 0
    for line in str(text or '').splitlines():
        found = _HEAD_RE.match(line)
        if found:
            cuts.append((name, lines))
            name, lines = found.group(1), []
            heads += 1
        else:
            lines.append(line)
    cuts.append((name, lines))
    if not heads:
        explanation, notes = read_answer(text)
        return {}, explanation, notes
    parts, reading = {}, None
    for name, lines in cuts:
        if name == 'reading':
            reading = lines if reading is None else reading
        elif name in wanted and name not in parts:
            parts[name] = '\n'.join(lines)
    explanation, notes = read_answer('\n'.join(reading or ()))
    return parts, explanation, notes


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


# ---------------------------------------------------------------------------
# The call
# ---------------------------------------------------------------------------

def claude_path():
    """Where `claude` is on PATH, or None."""
    return shutil.which(COMMAND[0])


@contextlib.contextmanager
def empty_folder():
    """A new empty folder under the system's temporary folder, where `claude`
    is started so it finds nothing of the project; removed after."""
    folder = tempfile.mkdtemp(prefix=FOLDER_PREFIX)
    try:
        yield folder
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def ask_model(prompt, command=None, runner=None, cwd=None, model=None,
              system=None):
    """One call: `{'answer', 'model', 'why', 'printed', 'said'}`.

    The request goes on stdin and stdin is closed after it, so the command
    line never carries it. `claude` is started in `cwd`, the audit's empty
    folder, or in one of its own, with `DISABLE_PROMPT_CACHING=1`. `why` is
    None when the model answered, and names the cause otherwise: an answer
    that is empty, is not JSON or reports an error is `NO_ANSWER`. `runner`
    stands in for `subprocess.run` in a test.

    `model` names the model to ask, as `--model <name>` before
    `--system-prompt`, and `system` is the system prompt sent in place of
    `SYSTEM_PROMPT`; the audit gives neither. `printed` is the program's
    standard output, and `said` what the program itself said of a call
    that failed: the `result` of a JSON that reports an error, else its
    standard error where it exited with an error, else ''.
    """
    command = command or claude_path()
    if not command:
        return {'answer': None, 'model': None, 'why': NOT_ON_PATH,
                'printed': '', 'said': ''}
    if cwd is None:
        with empty_folder() as folder:
            return _call(prompt, command, runner or subprocess.run, folder,
                         model, system)
    return _call(prompt, command, runner or subprocess.run, cwd, model,
                 system)


def _call(prompt, command, runner, cwd, model=None, system=None):
    found = {'answer': None, 'model': None, 'why': None, 'printed': '',
             'said': ''}
    argv = [command] + list(COMMAND[1:-1])
    if model:
        argv.extend(['--model', model])
    argv.extend([COMMAND[-1], system or SYSTEM_PROMPT])
    try:
        result = runner(argv,
                        input=prompt, capture_output=True, text=True,
                        encoding='utf-8', errors='replace', cwd=cwd,
                        env=dict(os.environ, **ENVIRONMENT),
                        timeout=MODEL_TIMEOUT)
    except subprocess.TimeoutExpired:
        result = None
        found['why'] = TIMED_OUT % MODEL_TIMEOUT
    except (OSError, subprocess.SubprocessError):
        result = None
        found['why'] = EXITED
    if result is None:
        return found
    found['printed'] = result.stdout or ''
    try:
        body = json.loads(result.stdout or '')
    except ValueError:
        body = None
    if isinstance(body, dict) and body.get('is_error') \
            and isinstance(body.get('result'), str):
        found['said'] = body['result']
    elif result.returncode != 0:
        found['said'] = result.stderr or ''
    if result.returncode != 0:
        found['why'] = EXITED
        return found
    if not isinstance(body, dict):
        found['why'] = NO_ANSWER
        return found
    answer = body.get('result')
    if body.get('is_error') or not isinstance(answer, str) \
            or not answer.strip():
        found['why'] = NO_ANSWER
        return found
    found.update(answer=answer, model=model_name(body))
    return found


def audit_one(project_root, reading, criteria, command=None, runner=None,
              cwd=None):
    """The model's one reply for a rule, or why it could not be asked.

    `{'parts', 'explanation', 'notes', 'model', 'criteria'}` when the model
    answered, where `parts` is `{proof: its part}` for the proofs of
    `reading['plant']` the reply holds, and `criteria` the sha256 of the
    criteria it was sent; only `{'why'}` when it could not be reached. The
    reply sets no verdict.
    """
    prompt = model_prompt(project_root, reading, criteria)
    called = ask_model(prompt, command, runner, cwd)
    if called['why']:
        return {'why': called['why']}
    parts, explanation, notes = read_reply(called['answer'],
                                           reading.get('plant') or ())
    return {'parts': parts, 'explanation': explanation, 'notes': notes,
            'model': called['model'], 'criteria': criteria_hash(criteria)}


def audit_all(project_root, readings, parallel=AUDIT_PARALLEL, runner=None,
              cwd=None):
    """One result per reading, in order, `parallel` calls at once.

    With no `claude` on PATH nothing is called and every reading carries
    that reason. Every call is started in `cwd`, or in one empty folder made
    here and removed after.
    """
    readings = list(readings or ())
    command = claude_path()
    if not command:
        return [{'why': NOT_ON_PATH} for _ in readings]
    if cwd is None:
        with empty_folder() as folder:
            return audit_all(project_root, readings, parallel, runner,
                             folder)
    criteria = criteria_text(project_root)
    workers = max(1, min(int(parallel or 1), len(readings) or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(audit_one, project_root, reading, criteria,
                               command, runner, cwd)
                   for reading in readings]
        return [future.result() for future in futures]


def bug_key(test_source_hash, code_part):
    """The sha256 of a proof's tests' source hash and its code part, joined
    by a line feed: a planted bug's result holds while this is unchanged."""
    return hashlib.sha256(('%s\n%s' % (test_source_hash or '',
                                       code_part or '')).encode('utf-8')
                          ).hexdigest()


# ---------------------------------------------------------------------------
# The text a person reads
# ---------------------------------------------------------------------------

def render(reading):
    """One rule as the audit reads it, and what the last audit found. A rule
    with an AI proof names, under `Output`, the kept output a wrong one is
    planted in."""
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
    kept = [proof for proof in reading.get('proofs') or ()
            if proof.get('ai')]
    if kept:
        lines.extend(['', 'Output'])
        lines.extend(OUTPUT_LINE % (proof.get('id'), proof.get('folder')
                                    or NO_OUTPUT_KEPT) for proof in kept)
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
    """What one audit entry found, one line each, as every surface words it:
    the verdict, each finding, then each `no_bug` sentence, which a
    `spot-checked` entry sets on one line after `The spot tests found
    nothing.`"""
    verdict = str(audit.get('verdict') or '')
    findings = list(audit.get('findings') or ())
    no_bug = [str(line) for line in audit.get('no_bug') or ()]
    if verdict == 'spot-checked':
        return [VERDICT_WORDS[verdict],
                (SPOT_CHECKED % ' '.join(no_bug)).strip()] + findings
    if verdict == 'strong' and not findings:
        return [STRONG_NOTHING] + no_bug
    if verdict in VERDICT_WORDS:
        return [VERDICT_WORDS[verdict]] + findings + no_bug
    return ['%s.' % verdict.capitalize()] + findings + no_bug


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
