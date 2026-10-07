"""The throwaway project the run script's tests and the refresh tests share.

A helper module, not a test file: it carries no marker and pytest collects
nothing from it. Each test file imports the names it uses from here, so no
test file imports another.
"""

import json
import os
import subprocess
import sys

import pytest

_DEV = os.path.dirname(os.path.abspath(__file__))
if _DEV not in sys.path:
    sys.path.insert(0, _DEV)

import fake_claude  # noqa: E402
import suites  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_SCRIPT = os.path.join(REPO, 'scripts', 'run', 'purlin_run.py')

with open(os.path.join(REPO, 'VERSION'), encoding='utf-8') as _handle:
    VERSION = _handle.read().strip()


def _project(tmp_path, tests=None):
    """A project root with `.purlin/config.json` and an empty `specs/`.

    The settings hold `version` and `tests`. `tests` is the `tests` setting,
    one pytest suite by default.
    """
    root = tmp_path / 'project'
    (root / 'specs' / 'a').mkdir(parents=True)
    (root / '.purlin').mkdir(parents=True)
    (root / '.purlin' / 'config.json').write_text(
        json.dumps({'version': VERSION, 'tests': (
            [suites.pytest_suite()] if tests is None
            else tests)}), encoding='utf-8')
    return root


def _spec(root, feature, proofs=(('PROOF-1', 'RULE-1', ''),), rules=1,
          scope='src/'):
    """A two-section spec. Each proof is `(id, rule, tag_suffix)`.

    `scope` is the `> Scope:` line's value, None for no line at all.
    """
    lines = ['# %s' % feature, '']
    if scope is not None:
        lines.append('> Scope: %s' % scope)
    lines.extend(['', '## Rules', ''])
    for index in range(1, rules + 1):
        lines.append('- RULE-%d: the software does thing %d' % (index, index))
    lines.extend(['', '## Proof', ''])
    for proof_id, rule_id, suffix in proofs:
        lines.append('- %s (%s): observe thing%s'
                     % (proof_id, rule_id, suffix))
    (root / 'specs' / 'a' / ('%s.md' % feature)).write_text(
        '\n'.join(lines) + '\n', encoding='utf-8')


def _pytest_project(tmp_path, body=None):
    root = _project(tmp_path)
    (root / 'tests').mkdir()
    (root / 'tests' / 'test_feat.py').write_text(
        body if body is not None else
        'import pytest\n\n'
        '# purlin: feat PROOF-1\n'
        'def test_ok():\n'
        '    assert 1 + 1 == 2\n', encoding='utf-8')
    return root


def _run(root, *args, answer=None):
    """The run script as a subprocess. `(returncode, stdout + stderr)`.

    `answer` is what its input holds; with none the input is at its end, as
    it is for a run nobody can answer.
    """
    cwd = str(root) if os.path.isdir(str(root)) else REPO
    result = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', str(root)] + list(args),
        capture_output=True, encoding='utf-8', cwd=cwd,
        **({'stdin': subprocess.DEVNULL} if answer is None
           else {'input': answer}))
    return result.returncode, result.stdout + result.stderr


@pytest.fixture
def claude(tmp_path, monkeypatch):
    """A fake `claude` first on PATH: `(install, directory)`.

    `install(**settings)` rewrites what it answers; see `dev/fake_claude.py`.
    """
    directory = tmp_path / 'claude'

    def install(**settings):
        fake_claude.install(directory, **settings)
        return directory

    install()
    monkeypatch.setenv('PATH', str(directory) + os.pathsep
                       + os.environ.get('PATH', ''))
    return install, directory


# ---------------------------------------------------------------------------
# A project with an AI proof
# ---------------------------------------------------------------------------

# `feat` of two rules. The test of PROOF-1 passes. The test of PROOF-2, an AI
# proof, stands in for one that starts the helper: it writes `reply.md` and
# the helper's record, `purlin.json`, into the folder the run names, and adds
# one line to `starts.log`, `<model> <run folder's name>`. `ai.json` in the
# project root says what it does: `fail`, the starts that fail, each as
# `<model> <run>`; `unreached`, `{model: why}` for the models that give no
# answer; `grade`, what a grader said, written into the record. Started with
# no folder named, it writes the line `bare` and passes.
AI_BODY = '''import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _reply():
    if 'PURLIN_AI_OUT' not in os.environ:
        with open(ROOT / 'starts.log', 'a') as log:
            log.write('bare\\n')
        return
    out = pathlib.Path(os.environ['PURLIN_AI_OUT'])
    model = os.environ['PURLIN_AI_MODEL']
    plan = json.loads((ROOT / 'ai.json').read_text(encoding='utf-8'))
    with open(ROOT / 'starts.log', 'a') as log:
        log.write('%s %s\\n' % (model, out.name))
    (ROOT / 'seen.json').write_text(json.dumps(
        {'out': str(out), 'helper': os.environ['PURLIN_AI'],
         'held': sorted(os.listdir(str(out)))}), encoding='utf-8')
    record = {'made': 'helper', 'model': model, 'reached': True, 'why': None}
    if model in plan.get('unreached', {}):
        record.update(reached=False, why=plan['unreached'][model])
    else:
        (out / 'reply.md').write_bytes(('reply of %s\\n' % model).encode())
        if 'grade' in plan:
            record['grade'] = plan['grade']
    (out / 'purlin.json').write_text(json.dumps(record), encoding='utf-8')
    assert record['reached'], record['why']
    assert '%s %s' % (model, out.name) not in plan.get('fail', [])


# purlin: feat PROOF-1
def test_ok():
    assert True


# purlin: feat PROOF-2
def test_reply():
    _reply()
'''


def _ai_project(tmp_path, tag='@ai(model-a, model-b)', tests=None, **plan):
    """A project whose `feat` PROOF-2 carries `tag`, with `AI_BODY` as its
    test file and `plan` as `ai.json`."""
    root = _project(tmp_path, tests)
    (root / 'tests').mkdir()
    (root / 'tests' / 'test_feat.py').write_text(AI_BODY, encoding='utf-8')
    (root / 'src').mkdir()
    (root / 'src' / 'feat.py').write_text('VALUE = 1\n', encoding='utf-8')
    (root / '.gitignore').write_text(
        '.purlin/runtime/\n__pycache__/\n.pytest_cache/\nstarts.log\n'
        'seen.json\nai.json\n', encoding='utf-8')
    _spec(root, 'feat', rules=2, proofs=(('PROOF-1', 'RULE-1', ''),
                                         ('PROOF-2', 'RULE-2', ' ' + tag)))
    _ai_plan(root, **plan)
    return root


def _ai_plan(root, **plan):
    """Write `ai.json`: what the AI proof's test does from now on."""
    (root / 'ai.json').write_text(json.dumps(plan), encoding='utf-8')


def _ai_starts(root):
    """The lines of `starts.log`, one per start of the AI proof's test."""
    path = root / 'starts.log'
    if not path.exists():
        return []
    return path.read_text(encoding='utf-8').split('\n')[:-1]
