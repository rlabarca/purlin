"""Behavioural proofs for the pre-push hook: the shim and the script.

The hook is two files. `.purlin/hooks/pre-push` is the shim `purlin:init`
writes into the project and git runs; it finds the installed plugin and hands
the push to that plugin's `scripts/hooks/pre-push.sh`, which runs the tagged
tests and decides whether to block.

Every case drives the real files against a temp project that `scripts/init/
scaffold.py` set up, so what these cases prove is what a developer's push
meets.

The contract in two lines: the hook refuses a push from an agent session
outright, and otherwise blocks only when `pre_push` is `on` and a test
failed. Every other outcome exits 0 and prints one line saying why.

Every case here drives the files through `posix_shell()` rather than `sh`,
because `sh` is not one shell. On macOS it is bash answering to another name
and it takes bash's extensions; on most Linux distributions it is dash, which
rejects them and exits 2 before reading a line of the script. A case run
through bash alone proves nothing about the host where the hook is handed
dash.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
SCAFFOLD = os.path.join(ROOT, 'scripts', 'init', 'scaffold.py')
HOOK_SCRIPT = os.path.join(ROOT, 'scripts', 'hooks', 'pre-push.sh')


def posix_shell():
    """The plainest POSIX shell this host has, dash first.

    On Windows `sh` on PATH is not a shell any more than `bash` is (the run
    script explains the WSL launcher), so the answer is the `sh.exe` that Git
    for Windows ships beside the bash the run script already finds.
    """
    if os.name == 'nt':
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'scripts', 'run'))
        from purlin_run import bash_command  # noqa: E402
        bash = bash_command()
        sh = os.path.join(os.path.dirname(bash), 'sh.exe')
        return sh if os.path.isfile(sh) else bash
    return shutil.which('dash') or 'sh'


SH = posix_shell()

# Outside a repository means outside every repository: a temp directory can
# sit under one, and then `git rev-parse` answers instead of failing and the
# case proves something else. This stops the search at the temp root.
OUTSIDE = {'GIT_CEILING_DIRECTORIES': tempfile.gettempdir()}

# The two variables the agent guard reads. Every case sets what it means to
# set and clears both otherwise, because this suite is itself run from a
# session that carries the first one: left in place, every case here would
# prove the guard and nothing else.
SESSION = 'CLAUDE_CODE_SESSION_ID'
REMOTE_RUN = 'PURLIN_REMOTE_RUN'


def person_env(base=None, **named):
    """A copy of the environment with no agent session in it."""
    env = dict(base if base is not None else os.environ)
    env.pop(SESSION, None)
    env.pop(REMOTE_RUN, None)
    env.update(named)
    return env

SPEC = """# Feature: greeting

> Scope: greeting.py
> Description: One rule, so the hook has a tagged test to run.

## Rules

- RULE-1: `greet(name)` returns `Hello, <name>!`

## Proof

- PROOF-1 (RULE-1): Call `greet("Ada")` and verify it returns `Hello, Ada!` @unit
"""

SOURCE = 'def greet(name):\n    return "Hello, %s!" % name\n'

TEST = """import pytest

from greeting import greet


@pytest.mark.proof("greeting", "PROOF-1", "RULE-1")
def test_greet():
    assert greet("Ada") == "%s"
"""


def write(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


class Project(object):
    """A temp project init has set up, with one tagged test that can be broken."""

    def __init__(self, passing=True, specs=True):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix='purlin-hook-'))
        self.home = os.path.realpath(tempfile.mkdtemp(prefix='purlin-home-'))
        subprocess.run(['git', '-c', 'init.defaultBranch=main', 'init', '-q', '.'], cwd=self.root, timeout=120)
        write(self.path('pyproject.toml'), '[tool.pytest.ini_options]\n')
        write(self.path('greeting.py'), SOURCE)
        done = subprocess.run(
            [sys.executable, SCAFFOLD, '--project-root', self.root,
             '--gate', 'passed', '--yes'], capture_output=True, text=True,
            timeout=300, stdin=subprocess.DEVNULL)
        assert done.returncode == 0, done.stdout + done.stderr
        if specs:
            write(self.path('specs/core/greeting.md'), SPEC)
            write(self.path('tests/test_greeting.py'),
                  TEST % ('Hello, Ada!' if passing else 'Goodbye'))

    def path(self, rel):
        return os.path.join(self.root, rel)

    def setting(self, value):
        config = json.loads(read(self.path('.purlin/config.json')))
        config['pre_push'] = value
        write(self.path('.purlin/config.json'),
              json.dumps(config, indent=2) + '\n')

    def push(self, **kwargs):
        """Run the shim the way git runs it, and answer with what it said."""
        env = person_env()
        env['HOME'] = self.home
        env.pop('CLAUDE_PLUGIN_ROOT', None)
        env['PURLIN_PLUGIN_ROOT'] = kwargs.get('plugin_root', ROOT)
        if env['PURLIN_PLUGIN_ROOT'] is None:
            env.pop('PURLIN_PLUGIN_ROOT')
        for name, value in (kwargs.get('env') or {}).items():
            env[name] = value
        return subprocess.run(
            [SH, self.path('.purlin/hooks/pre-push')], cwd=self.root,
            capture_output=True, text=True, timeout=600, env=env,
            stdin=subprocess.DEVNULL)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.home, ignore_errors=True)


@pytest.fixture
def passing():
    made = Project(passing=True)
    yield made
    made.close()


@pytest.fixture
def failing():
    made = Project(passing=False)
    yield made
    made.close()


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------

class TestTheContract:

    @pytest.mark.proof("scaffold", "PROOF-27", "RULE-27")
    def test_a_passing_suite_says_so_and_lets_the_push_through(self, passing):
        done = passing.push()
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'the tagged tests passed' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-27", "RULE-27")
    def test_a_failure_with_the_setting_off_is_reported_and_not_blocked(
            self, failing):
        done = failing.push()
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'a tagged test failed' in done.stdout
        assert 'not blocked' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-27", "RULE-27")
    def test_a_failure_with_the_setting_on_blocks(self, failing):
        failing.setting('on')
        done = failing.push()
        assert done.returncode == 1
        assert 'this push is blocked' in done.stdout
        assert 'purlin:test' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-27", "RULE-27")
    def test_a_pass_with_the_setting_on_still_goes_through(self, passing):
        passing.setting('on')
        done = passing.push()
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'the tagged tests passed' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-27", "RULE-27")
    def test_an_unreadable_setting_never_blocks(self, failing):
        write(failing.path('.purlin/config.json'), 'not json at all')
        done = failing.push()
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'not blocked' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-27", "RULE-27")
    def test_the_setting_true_counts_as_on(self, failing):
        failing.setting(True)
        assert failing.push().returncode == 1

    @pytest.mark.proof("scaffold", "PROOF-27", "RULE-27")
    def test_a_run_that_reached_no_test_never_blocks(self, passing):
        """Exit 2 is the run script saying it could not read its command line.

        No test ran, so none failed, and the setting has nothing to act on.
        The hook is pointed at a plugin whose run script is that one answer.
        """
        passing.setting('on')
        stub = os.path.realpath(tempfile.mkdtemp(prefix='purlin-stub-'))
        try:
            for rel in ('scripts/hooks/pre-push.sh', 'scripts/purlin_python.sh'):
                write(os.path.join(stub, rel), read(os.path.join(ROOT, rel)))
            write(os.path.join(stub, 'scripts/run/purlin_run.py'),
                  'import sys\n\nsys.exit(2)\n')
            done = subprocess.run(
                [SH, os.path.join(stub, 'scripts', 'hooks', 'pre-push.sh')],
                cwd=passing.root, capture_output=True, text=True, timeout=300,
                env=person_env(), stdin=subprocess.DEVNULL)
            assert done.returncode == 0, done.stdout + done.stderr
            assert 'not blocked' in done.stdout
            assert 'exited 2' in done.stdout
        finally:
            shutil.rmtree(stub, ignore_errors=True)

    @pytest.mark.proof("scaffold", "PROOF-27", "RULE-27")
    def test_one_line_either_way(self, passing):
        lines = [line for line in passing.push().stdout.splitlines()
                 if line.startswith('purlin:')]
        assert len(lines) == 1


class TestTheAgentGuard:
    """A push is a person's act, and this is where git enforces it."""

    @pytest.mark.proof("scaffold", "PROOF-43", "RULE-43")
    def test_an_agent_session_is_refused(self, passing):
        done = passing.push(env={SESSION: 'session-01'})
        assert done.returncode == 1
        assert ('purlin: an agent does not push. A person runs git push.'
                in done.stdout)

    @pytest.mark.proof("scaffold", "PROOF-43", "RULE-43")
    def test_the_remote_run_goes_through(self, passing):
        """`purlin:test --remote` is the one push Purlin makes."""
        done = passing.push(env={SESSION: 'session-01', REMOTE_RUN: '1'})
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'the tagged tests passed' in done.stdout
        assert 'an agent does not push' not in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-43", "RULE-43")
    def test_a_person_is_never_stopped_by_the_guard(self, passing):
        done = passing.push()
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'an agent does not push' not in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-43", "RULE-43")
    def test_the_guard_runs_before_the_tests(self, failing):
        """No spec is run and no setting is read: the refusal is the first word."""
        done = failing.push(env={SESSION: 'session-01'})
        assert done.returncode == 1
        lines = [line for line in done.stdout.splitlines()
                 if line.startswith('purlin:')]
        assert lines == ['purlin: an agent does not push. A person runs '
                         'git push.']

    @pytest.mark.proof("scaffold", "PROOF-43", "RULE-43")
    def test_a_project_with_no_spec_is_refused_too(self):
        made = Project(specs=False)
        try:
            done = made.push(env={SESSION: 'session-01'})
            assert done.returncode == 1
            assert 'an agent does not push' in done.stdout
        finally:
            made.close()


class TestWhenThereIsNothingToRun:

    @pytest.mark.proof("scaffold", "PROOF-28", "RULE-28")
    def test_a_project_with_no_specs_exits_zero(self):
        made = Project(specs=False)
        try:
            done = made.push()
            assert done.returncode == 0, done.stdout + done.stderr
            assert 'purlin:' not in done.stdout
        finally:
            made.close()

    @pytest.mark.proof("scaffold", "PROOF-28", "RULE-28")
    def test_a_project_that_is_not_a_purlin_project_exits_zero(self, passing):
        shutil.rmtree(passing.path('.purlin'), ignore_errors=True)
        done = subprocess.run([SH, HOOK_SCRIPT], cwd=passing.root,
                              capture_output=True, text=True, timeout=300,
                              env=person_env(), stdin=subprocess.DEVNULL)
        assert done.returncode == 0, done.stdout + done.stderr
        assert done.stdout == ''

    @pytest.mark.proof("scaffold", "PROOF-28", "RULE-28")
    def test_outside_a_repository_it_exits_zero(self):
        directory = tempfile.mkdtemp(prefix='purlin-norepo-')
        env = person_env()
        env.update(OUTSIDE)
        try:
            done = subprocess.run([SH, HOOK_SCRIPT], cwd=directory, env=env,
                                  capture_output=True, text=True, timeout=300,
                                  stdin=subprocess.DEVNULL)
            assert done.returncode == 0, done.stdout + done.stderr
            assert done.stdout == ''
        finally:
            shutil.rmtree(directory, ignore_errors=True)


# ---------------------------------------------------------------------------
# The shim
# ---------------------------------------------------------------------------

class TestTheShim:

    @pytest.mark.proof("scaffold", "PROOF-29", "RULE-29")
    def test_the_pinned_plugin_root_is_enough(self, passing):
        done = passing.push(plugin_root=None)
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'the tagged tests passed' in done.stdout
        assert read(passing.path('.purlin/plugin-root')).strip() == ROOT

    @pytest.mark.proof("scaffold", "PROOF-29", "RULE-29")
    def test_claude_plugin_root_is_enough(self, passing):
        os.remove(passing.path('.purlin/plugin-root'))
        done = passing.push(plugin_root=None,
                            env={'CLAUDE_PLUGIN_ROOT': ROOT})
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'the tagged tests passed' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-29", "RULE-29")
    def test_a_marketplace_copy_under_home_is_found(self, passing):
        installed = os.path.join(passing.home, '.claude', 'plugins', 'cache',
                                 'purlin', 'purlin', '0.10.0')
        os.makedirs(os.path.dirname(installed), exist_ok=True)
        shutil.copytree(ROOT, installed,
                        ignore=shutil.ignore_patterns('.git', 'design',
                                                      'docs', '__pycache__'))
        os.remove(passing.path('.purlin/plugin-root'))
        done = passing.push(plugin_root=None)
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'the tagged tests passed' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-29", "RULE-29")
    def test_no_plugin_anywhere_warns_and_never_blocks(self, passing):
        os.remove(passing.path('.purlin/plugin-root'))
        done = passing.push(plugin_root=None)
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'the plugin was not found' in done.stdout
        assert 'PURLIN_PLUGIN_ROOT' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-29", "RULE-29")
    def test_an_environment_root_wins_over_the_pinned_one(self, passing):
        write(passing.path('.purlin/plugin-root'), '/no/such/plugin\n')
        done = passing.push()
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'the tagged tests passed' in done.stdout

    @pytest.mark.proof("scaffold", "PROOF-25", "RULE-25")
    def test_the_shim_names_no_machine_and_no_release(self, passing):
        shim = read(passing.path('.purlin/hooks/pre-push'))
        assert ROOT not in shim
        assert passing.root not in shim
        assert read(os.path.join(ROOT, 'VERSION')).strip() not in shim

    @pytest.mark.proof("scaffold", "PROOF-24", "RULE-24")
    def test_the_delegator_git_runs_reaches_the_shim(self, passing):
        delegator = read(passing.path('.git/hooks/pre-push'))
        assert '.purlin/hooks/pre-push' in delegator
        assert os.access(passing.path('.git/hooks/pre-push'), os.X_OK)

    @pytest.mark.proof("scaffold", "PROOF-24", "RULE-24")
    def test_the_delegator_survives_a_checkout_without_the_shim(self, passing):
        os.remove(passing.path('.purlin/hooks/pre-push'))
        done = subprocess.run([SH, passing.path('.git/hooks/pre-push')],
                              cwd=passing.root, capture_output=True,
                              text=True, timeout=300, env=person_env(),
                              stdin=subprocess.DEVNULL)
        assert done.returncode == 0
        assert 'no hook shim' in done.stdout


# ---------------------------------------------------------------------------
# What the two files say
# ---------------------------------------------------------------------------

class TestTheFilesThemselves:

    @pytest.mark.proof("scaffold", "PROOF-27", "RULE-27")
    def test_the_script_runs_the_quick_pass_and_nothing_else(self):
        text = read(HOOK_SCRIPT)
        assert '--all --quick' in text
        assert 'purlin_run.py' in text
        assert 'pytest' not in text
        assert 'npx' not in text

    @pytest.mark.proof("scaffold", "PROOF-28", "RULE-28")
    def test_the_script_asks_for_sh_and_sets_no_option_outside_posix(self):
        """The one line that decides which shell reads the rest of the file.

        A host whose `sh` is dash has no `pipefail`, and `set -o pipefail`
        there exits 2 before line 2 of the script, which is a block.
        """
        lines = read(HOOK_SCRIPT).splitlines()
        assert lines[0] == '#!/bin/sh'
        options = [line for line in lines if line.startswith('set ')]
        assert options == ['set -u'], options

    @pytest.mark.proof("scaffold", "PROOF-35", "RULE-35")
    def test_the_script_carries_no_retired_word(self):
        text = read(HOOK_SCRIPT).lower()
        # Spelled in halves so this file does not carry the words either.
        # `audit` is not among them: it is the name of the level 2 run and
        # the hook names the one command that pushes, purlin:test --remote.
        for word in ('rece' + 'ipt', 'ga' + 'uge', 'str' + 'ict',
                     'fo' + 'rge', 'appro' + 'val', 'verif' + 'ied'):
            assert word not in text

    @pytest.mark.proof("scaffold", "PROOF-24", "RULE-24")
    def test_no_pre_commit_script_ships(self):
        assert not os.path.exists(
            os.path.join(ROOT, 'scripts', 'hooks', 'pre-commit.sh'))
        assert not os.path.exists(
            os.path.join(ROOT, 'scripts', 'hooks', 'pre_push_gate.py'))

    def test_every_open_in_the_script_reads_utf_8(self):
        assert "encoding='utf-8'" in read(HOOK_SCRIPT)
