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


def _project(tmp_path, tests=None, gate='passed'):
    """A project root with `.purlin/config.json` and an empty `specs/`.

    `tests` is the `tests` setting, one pytest suite by default. `passed` is
    the default gate because it is the gate a new project is set up at. A
    test that needs the breaks to run sets mutation_engine, which is off
    until named, at either gate.
    """
    root = tmp_path / 'project'
    (root / 'specs' / 'a').mkdir(parents=True)
    (root / '.purlin').mkdir(parents=True)
    (root / '.purlin' / 'config.json').write_text(
        json.dumps({'gate': gate, 'tests': (
            [suites.pytest_suite(extra='--ignore=mutants')] if tests is None
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


def _pytest_project(tmp_path, body=None, gate='passed'):
    root = _project(tmp_path, gate=gate)
    (root / 'tests').mkdir()
    (root / 'tests' / 'test_feat.py').write_text(
        body if body is not None else
        'import pytest\n\n'
        '# purlin: feat PROOF-1\n'
        'def test_ok():\n'
        '    assert 1 + 1 == 2\n', encoding='utf-8')
    return root


def _run(root, *args):
    """The run script as a subprocess. `(returncode, stdout + stderr)`."""
    cwd = str(root) if os.path.isdir(str(root)) else REPO
    result = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', str(root)] + list(args),
        capture_output=True, encoding='utf-8', cwd=cwd)
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
