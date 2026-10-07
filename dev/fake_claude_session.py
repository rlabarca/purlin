"""A stand-in for the `claude` program as `scripts/ai/purlin_ai.py` starts
it, so no test of an AI proof ever reaches a real model.

    python3 dev/fake_claude_session.py install DIR      write a fake into DIR

It answers both calls the helper makes: a session (`--output-format
stream-json`, one JSON object per line, the last a `result`) and the bare
call (`--output-format json`, the one `result` object), which is also the
call `purlin_ai.py grade` and the audit make.

**Installing it.** `install(directory, answers=...)` writes an executable
named `claude` (and `claude.cmd` beside it, for Windows) into `directory`.
Put that directory first on PATH for the process that starts the helper:

    import fake_claude_session as fake
    bin_dir = fake.install(tmp_path / 'bin', answers=[
        fake.answer('Three findings: F-1, F-2, F-3.',
                    writes={'out/summary.md': '# Summary\n'}),
        fake.answer('accept: it names all three'),
    ])
    done = subprocess.run([sys.executable, PURLIN_AI, 'run', ...],
                          env=fake.environment(bin_dir, PURLIN_AI_MODEL='m'))
    sent = fake.calls(bin_dir)

`environment(directory, **more)` is `os.environ` with `directory` first on
PATH and `more` set; a value of None takes that variable out.

**Scripting an answer.** `answers` holds one answer per call, in the order
the calls arrive; the last one repeats. `answer(...)` builds one:

    reply       the `result` text, `DEFAULT_REPLY` where none is given
    writes      `{path: text}`: each file is written, its folders made,
                under the folder the fake was started in, before it answers
    removes     paths under that folder to delete
    exit_code   what the call exits with, 0 by default
    sleep       seconds the call waits before it answers
    error       True makes the `result` object report an error
                (`is_error` true), its `result` still the reply
    no_result   True leaves the `result` object out of what is printed
    stderr      text written to standard error
    raw         printed as it is in place of every JSON line
    model       the model `modelUsage` names; where None, the one `--model`
                named, or `DEFAULT_MODEL`

A plain string stands for `answer(<that string>)`, and None for `answer()`.

**What each call logs.** One JSON line in `calls.jsonl` beside the fake,
read back with `calls(directory)`:

    argv        the arguments, without the program's own name
    prompt      everything read from standard input
    cwd         the folder it was started in, as the system names it
    listing     every file under that folder before the answer's `writes`,
                `/` separated and sorted
    plugins     `{<--plugin-dir value>: {path: text}}`, every file of each
                plugin folder, read before the helper removes it
    env         the values of `LOGGED`, None for one that is not set

A session's lines are a `system` line naming the folder and the model, one
`assistant` line holding the reply, then the `result`.
"""

import json
import os
import stat
import sys

DEFAULT_REPLY = 'The fake model says nothing.'
DEFAULT_MODEL = 'claude-fake-1'
SETUP = 'fake_claude_session.json'

# The environment values a call logs.
LOGGED = ('DISABLE_PROMPT_CACHING', 'ENABLE_CLAUDEAI_MCP_SERVERS', 'PURLIN_AI', 'PURLIN_AI_MODEL',
          'PURLIN_AI_OUT', 'PURLIN_AI_REPLAY', 'PURLIN_PROJECT_ROOT')

_SCRIPT = r'''#!%(python)s
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__))
prompt = sys.stdin.read()
with open(os.path.join(here, %(setup)r), encoding='utf-8') as handle:
    setup = json.load(handle)
try:
    import fcntl
    fd = os.open(os.path.join(here, 'count'), os.O_RDWR | os.O_CREAT)
    fcntl.flock(fd, fcntl.LOCK_EX)
    index = int(os.read(fd, 32).decode() or '0')
    os.lseek(fd, 0, 0)
    os.ftruncate(fd, 0)
    os.write(fd, str(index + 1).encode())
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
except ImportError:
    try:
        with open(os.path.join(here, 'count'), encoding='utf-8') as handle:
            index = int(handle.read() or '0')
    except (OSError, ValueError):
        index = 0
    with open(os.path.join(here, 'count'), 'w', encoding='utf-8') as handle:
        handle.write(str(index + 1))
answers = setup.get('answers') or [{}]
answer = answers[min(index, len(answers) - 1)] or {}
argv = sys.argv[1:]


def value(option):
    return argv[argv.index(option) + 1] if option in argv[:-1] else None


def files(folder):
    found = {}
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames.sort()
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, folder).replace(os.sep, '/')
            try:
                with open(path, encoding='utf-8') as handle:
                    found[rel] = handle.read()
            except (OSError, UnicodeDecodeError):
                found[rel] = None
    return found


cwd = os.getcwd()
plugins = {}
for position, item in enumerate(argv[:-1]):
    if item == '--plugin-dir':
        plugins[argv[position + 1]] = files(argv[position + 1])
line = json.dumps({
    'argv': argv, 'prompt': prompt, 'cwd': cwd,
    'listing': sorted(files(cwd)), 'plugins': plugins,
    'env': dict((name, os.environ.get(name)) for name in setup['logged'])})
with open(os.path.join(here, 'calls.jsonl'), 'a', encoding='utf-8') as log:
    log.write(line + '\n')
time.sleep(float(answer.get('sleep') or 0))
for rel, text in sorted((answer.get('writes') or {}).items()):
    path = os.path.join(cwd, *rel.split('/'))
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)
for rel in answer.get('removes') or ():
    os.remove(os.path.join(cwd, *rel.split('/')))
if answer.get('stderr'):
    sys.stderr.write(answer['stderr'])
reply = answer.get('reply')
reply = setup['default'] if reply is None else reply
model = answer.get('model') or value('--model') or setup['model']
result = {'type': 'result',
          'subtype': 'error_during_execution' if answer.get('error')
          else 'success',
          'is_error': bool(answer.get('error')), 'result': reply,
          'duration_ms': 5, 'modelUsage': {model: {'outputTokens': 10}}}
if answer.get('raw') is not None:
    sys.stdout.write(answer['raw'])
elif value('--output-format') == 'stream-json':
    lines = [{'type': 'system', 'subtype': 'init', 'cwd': cwd,
              'model': model},
             {'type': 'assistant', 'message': {
                 'role': 'assistant', 'model': model,
                 'content': [{'type': 'text', 'text': reply}]}}]
    if not answer.get('no_result'):
        lines.append(result)
    for item in lines:
        sys.stdout.write(json.dumps(item) + '\n')
elif not answer.get('no_result'):
    sys.stdout.write(json.dumps(result))
sys.exit(int(answer.get('exit') or 0))
'''


def answer(reply=None, writes=None, removes=None, exit_code=0, sleep=0,
           error=False, no_result=False, stderr='', raw=None, model=None):
    """One scripted answer; the module's docstring says what each part
    does."""
    return {'reply': reply, 'writes': dict(writes or {}),
            'removes': list(removes or ()), 'exit': exit_code,
            'sleep': sleep, 'error': bool(error),
            'no_result': bool(no_result), 'stderr': stderr, 'raw': raw,
            'model': model}


def install(directory, answers=(None,), model=DEFAULT_MODEL):
    """Write the fake into `directory`. The directory, to put first on PATH.

    A fake already there is replaced, and its log of calls is emptied.
    """
    directory = str(directory)
    os.makedirs(directory, exist_ok=True)
    scripted = [answer(item) if item is None or isinstance(item, str)
                else item for item in answers]
    with open(os.path.join(directory, SETUP), 'w',
              encoding='utf-8') as handle:
        json.dump({'answers': scripted, 'model': model,
                   'default': DEFAULT_REPLY, 'logged': list(LOGGED)}, handle)
    script = os.path.join(directory, 'claude')
    with open(script, 'w', encoding='utf-8') as handle:
        handle.write(_SCRIPT % {'python': sys.executable, 'setup': SETUP})
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


def environment(directory, **more):
    """`os.environ` with the fake in `directory` first on PATH and `more`
    set; a value of None takes that variable out."""
    env = dict(os.environ)
    env['PATH'] = str(directory) + os.pathsep + env.get('PATH', '')
    for name, value in more.items():
        if value is None:
            env.pop(name, None)
        else:
            env[name] = str(value)
    return env


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'install':
        print(install(sys.argv[2]))
        sys.exit(0)
    print('Usage: fake_claude_session.py install DIR', file=sys.stderr)
    sys.exit(2)
