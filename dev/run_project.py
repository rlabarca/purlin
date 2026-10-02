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
