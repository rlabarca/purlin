"""A stand-in for the `claude` command, so no test ever reaches the real model.

    python3 dev/fake_claude.py install DIR      write a fake into DIR

`install(directory, answers=..., ...)` writes an executable named `claude`
(and `claude.cmd` beside it, for Windows) into `directory`. Put that
directory first on PATH and every call the audit makes lands here instead of
on the model. Each call appends one JSON line to `calls.jsonl` beside the
fake: the arguments it was given, the prompt it read on stdin, the folder it
was started in (`cwd`) and what that folder held (`listing`), the value of
`DISABLE_PROMPT_CACHING` (`env`), and when it started and finished, so a test
can read how many calls were made, what they carried and how many ran at once.

The audit asks once per rule, and the reply holds one part per proof it asks
a bug for and then the reading (`reply`):

    === PROOF-2 ===
    no break: the fake model plants no bug

    === reading ===
    - The test reads the status.

What the fake answers is set in `fake_claude.json` beside it:

    answers   one per call in order; the last one repeats. Each is
              - null: a part reading `no break: the fake model plants no bug`
                for each proof the request asks a bug for, and an empty reading;
              - an object `{"PROOF-2": <part>, "reading": <lines>}`: the part
                of each proof the request asks for and the object names, then
                the reading, so one object answers several rules;
              - a string: the `result`, exactly as given
    exit      the exit code every call ends with, 0 by default
    sleep     seconds each call waits before it answers
    model     the model the JSON names under `modelUsage`, or null for none
    cost      the `total_cost_usd` the JSON reports, or null for none
    writes    `[path, text]`: text the fake appends to that file as it answers
    raw       printed as-is instead of the JSON, when set

`dev/conftest.py` puts one fake first on PATH for every test in the session,
answering null. A test that wants another answer installs its own into its
own directory and puts that first.
"""

import json
import os
import stat
import sys

DEFAULT_ANSWER = 'no break: the fake model plants no bug'
DEFAULT_MODEL = 'claude-fake-1'

_SCRIPT = r'''#!%(python)s
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
started = time.time()
prompt = sys.stdin.read()
with open(os.path.join(here, 'fake_claude.json'), encoding='utf-8') as handle:
    setup = json.load(handle)
count_path = os.path.join(here, 'count')
try:
    fd = os.open(count_path, os.O_RDWR | os.O_CREAT)
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_EX)
    seen = os.read(fd, 32).decode() or '0'
    index = int(seen)
    os.lseek(fd, 0, 0)
    os.ftruncate(fd, 0)
    os.write(fd, str(index + 1).encode())
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
except ImportError:
    index = 0
time.sleep(float(setup.get('sleep') or 0))
answers = setup.get('answers') or [None]
answer = answers[min(index, len(answers) - 1)]
if not isinstance(answer, str):
    import re
    asked = re.findall(r'^Plant one bug for each of: (.*)\.$', prompt, re.M)
    asked = [name.strip() for name in asked[-1].split(',')] if asked else []
    given = answer if isinstance(answer, dict) else dict(
        (name, setup['default']) for name in asked)
    parts = []
    for name in asked:
        if name in given:
            parts.extend(['=== %%s ===' %% name, given[name].rstrip('\n'), ''])
    parts.extend(['=== reading ===', given.get('reading') or ''])
    answer = '\n'.join(parts) + '\n'
if setup.get('writes'):
    with open(setup['writes'][0], 'a', encoding='utf-8') as touched:
        touched.write(setup['writes'][1])
cwd = os.getcwd()
line = json.dumps({'argv': sys.argv[1:], 'prompt': prompt, 'cwd': cwd,
                   'listing': sorted(os.listdir(cwd)),
                   'env': os.environ.get('DISABLE_PROMPT_CACHING'),
                   'start': started, 'end': time.time()})
with open(os.path.join(here, 'calls.jsonl'), 'a', encoding='utf-8') as log:
    log.write(line + '\n')
if setup.get('raw') is not None:
    sys.stdout.write(setup['raw'])
else:
    body = {'type': 'result', 'subtype': 'success', 'is_error': False,
            'result': answer, 'duration_ms': 5}
    if setup.get('model'):
        body['modelUsage'] = {setup['model']: {'outputTokens': 10}}
    if setup.get('cost') is not None:
        body['total_cost_usd'] = setup['cost']
    sys.stdout.write(json.dumps(body))
sys.exit(int(setup.get('exit') or 0))
'''


def reply(parts=None, reading=''):
    """A reply in the audit's shape: `parts` is `{'PROOF-N': its part}`, and
    `reading` the lines under `=== reading ===`."""
    lines = []
    for proof, text in (parts or {}).items():
        lines.extend(['=== %s ===' % proof, str(text).rstrip('\n'), ''])
    lines.extend(['=== reading ===', reading or ''])
    return '\n'.join(lines) + '\n'


def install(directory, answers=(None,), exit_code=0, sleep=0,
            model=DEFAULT_MODEL, raw=None, cost=None, writes=None):
    """Write the fake into `directory`. The directory, to put first on PATH."""
    directory = str(directory)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, 'fake_claude.json'), 'w',
              encoding='utf-8') as handle:
        json.dump({'answers': list(answers), 'exit': exit_code,
                   'sleep': sleep, 'model': model, 'raw': raw, 'cost': cost,
                   'writes': list(writes) if writes else None,
                   'default': DEFAULT_ANSWER}, handle)
    script = os.path.join(directory, 'claude')
    with open(script, 'w', encoding='utf-8') as handle:
        handle.write(_SCRIPT % {'python': sys.executable})
    os.chmod(script, os.stat(script).st_mode | stat.S_IXUSR | stat.S_IXGRP
             | stat.S_IXOTH)
    with open(os.path.join(directory, 'claude.cmd'), 'w',
              encoding='utf-8') as handle:
        handle.write('@"%s" "%%~dp0claude" %%*\r\n' % sys.executable)
    for name in ('calls.jsonl', 'count'):
        try:
            os.remove(os.path.join(directory, name))
        except OSError:
            pass
    return directory


def calls(directory):
    """Every call the fake in `directory` took, oldest first."""
    path = os.path.join(str(directory), 'calls.jsonl')
    if not os.path.isfile(path):
        return []
    with open(path, encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def most_at_once(found):
    """The largest number of calls that were running at the same moment."""
    edges = []
    for call in found:
        edges.append((call['start'], 1))
        edges.append((call['end'], -1))
    running = best = 0
    for _moment, step in sorted(edges, key=lambda edge: (edge[0], edge[1])):
        running += step
        best = max(best, running)
    return best


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'install':
        print(install(sys.argv[2]))
        sys.exit(0)
    print('Usage: fake_claude.py install DIR', file=sys.stderr)
    sys.exit(2)
