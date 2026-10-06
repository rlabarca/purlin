"""Tests for this repository's own Windows run.

`dev/windows_run.py` pushes a run branch to GitHub, waits for the run the
`windows.yml` workflow starts there, and brings back the commit that run made.
Nothing here reaches GitHub or starts the real `gh`: the `gh` on the search
path is a stand-in program that is found and never started, its answers are
given by a stand-in for `subprocess.run`, and git either answers from the same
stand-in or runs for real against a bare repository on disk.

What these tests cannot show is how GitHub's own runner behaves. The one real
run, started by hand after a build, shows that.
"""

import os
import re
import subprocess
import sys
import types

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)

import windows_run  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
from purlin import status as purlin_status  # noqa: E402

WORKFLOW = os.path.join(ROOT, '.github', 'workflows', 'windows.yml')
SHA = '4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7'
RUN_BRANCH = 'run/feature-x-4f1c2ab'
PUSH = ['git', 'push', 'origin', 'HEAD:refs/heads/%s' % RUN_BRANCH]
WATCH = ['gh', 'run', 'watch', '987', '--exit-status']
PULL = ['git', 'pull', '--ff-only', 'origin', RUN_BRANCH]
DELETE = ['git', 'push', 'origin', '--delete', RUN_BRANCH]
FAILED_ON_GITHUB = ('The run failed on GitHub. The table below is what came '
                    'back.')
NOT_COMMITTED = ('This checkout has changes that are not committed, so a run '
                 'would prove something other than what is here. Commit them, '
                 'then run python3 dev/windows_run.py again.')
RUN_LIST = '[{"databaseId": 987}]'
# One spec, so that the status of a test's project is a table with a row.
LOGIN = ('# Feature: login\n\n## Rules\n\n- RULE-1: Signs a person in\n\n'
         '## Proof\n\n- PROOF-1 (RULE-1): A right password signs in\n')


# ---------------------------------------------------------------------------
# Stand-ins
# ---------------------------------------------------------------------------

def stand_in(folder, name):
    """A program `name` in `folder` that the system's own lookup finds.

    On POSIX a file with no ending and the exec bit set; on Windows
    `<name>.cmd`, which `PATHEXT` names.
    """
    if os.name == 'nt':
        path = os.path.join(str(folder), name + '.cmd')
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('@echo off\r\n')
    else:
        path = os.path.join(str(folder), name)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write('#!/bin/sh\n')
        os.chmod(path, 0o755)
    return path


def git(cwd, *args):
    result = subprocess.run(['git'] + list(args), cwd=str(cwd),
                            capture_output=True, text=True)
    assert result.returncode == 0, ' '.join(args) + ': ' + result.stderr
    return result


def make_repo(path):
    """A git repository with one commit on `main`."""
    os.makedirs(str(path), exist_ok=True)
    git(path, 'init', '--quiet', '-b', 'main')
    git(path, 'config', 'user.name', 'Ada Lovelace')
    git(path, 'config', 'user.email', 'ada@example.com')
    git(path, 'config', 'commit.gpgsign', 'false')
    with open(os.path.join(str(path), 'README.md'), 'w',
              encoding='utf-8') as handle:
        handle.write('the project\n')
    git(path, 'add', '-A')
    git(path, 'commit', '--quiet', '-m', 'the project')
    return str(path)


def _gh_on_the_path(tmp_path, monkeypatch):
    """A stand-in `gh` ahead of the search path, which still finds git."""
    folder = tmp_path / 'with-gh'
    folder.mkdir()
    stand_in(folder, 'gh')
    monkeypatch.setenv('PATH', str(folder) + os.pathsep + os.environ['PATH'])


class FakeProcesses(object):
    """`subprocess.run` for `windows_run.py`: git and gh answer, nothing runs.

    The branch is `feature-x`, HEAD is `SHA`, the tree is clean and GitHub
    lists run 987. Every process other than those reads is kept in `started`,
    in order, with the directory it was started in.
    """

    def __init__(self):
        self.started = []
        self.cwds = []

    def __call__(self, argv, cwd=None, **_kwargs):
        argv = list(argv)
        if argv[:3] == ['git', 'rev-parse', '--abbrev-ref']:
            return subprocess.CompletedProcess(argv, 0, 'feature-x\n', '')
        if argv[:2] == ['git', 'rev-parse']:
            return subprocess.CompletedProcess(argv, 0, SHA + '\n', '')
        if argv[:3] == ['git', 'status', '--porcelain']:
            return subprocess.CompletedProcess(argv, 0, '', '')
        if argv[:3] == ['gh', 'run', 'list']:
            return subprocess.CompletedProcess(argv, 0, RUN_LIST, '')
        self.started.append(argv)
        self.cwds.append(cwd)
        return subprocess.CompletedProcess(argv, 0, '', '')


# ---------------------------------------------------------------------------
# The round trip
# ---------------------------------------------------------------------------

# purlin: windows_run PROOF-1
def test_a_green_run_pushes_watches_pulls_and_deletes(tmp_path, monkeypatch,
                                                      capsys):
    project = str(tmp_path / 'project')
    os.makedirs(os.path.join(project, 'specs', 'app'))
    with open(os.path.join(project, 'specs', 'app', 'login.md'), 'w',
              encoding='utf-8') as handle:
        handle.write(LOGIN)
    _gh_on_the_path(tmp_path, monkeypatch)
    fake = FakeProcesses()
    # The script's own processes are answered by the stand-in. The status it
    # prints is the real one, read with the real `subprocess`.
    monkeypatch.setattr(windows_run, 'subprocess', types.SimpleNamespace(
        run=fake, DEVNULL=subprocess.DEVNULL,
        SubprocessError=subprocess.SubprocessError))

    assert windows_run.windows_run(project) == 0
    assert fake.started == [PUSH, WATCH, PULL, DELETE]
    assert fake.cwds == [project] * 4
    printed = capsys.readouterr().out
    assert FAILED_ON_GITHUB not in printed
    # The output ends with the status table of this project: its first line,
    # the row of its one spec, and every line of it down to the last.
    table = purlin_status.sync_status(project).splitlines()
    assert table[0].startswith('Purlin status: '), table
    assert [line.split()[:2] for line in table
            if line.startswith('login ')] == [['login', '1']], table
    lines = printed.splitlines()
    assert lines[-len(table):] == table, printed
    assert lines[:-len(table)] == [
        'Pushing feature-x as %s.' % RUN_BRANCH,
        'Waiting for the windows.yml workflow on %s.' % RUN_BRANCH], printed


# purlin: windows_run PROOF-2
def test_a_red_run_says_so_still_pulls_and_deletes_and_exits_1(
        tmp_path, monkeypatch, capsys):
    """git runs for real against a bare repository standing in for GitHub.

    `gh` is answered here: it lists run 987, and its watch puts the runner's
    one commit on the run branch and then exits 1, as a run with a failed
    test does.
    """
    bare = str(tmp_path / 'github.git')
    git(tmp_path, 'init', '--bare', '--quiet', '-b', 'main', bare)
    project = make_repo(tmp_path / 'project')
    git(project, 'remote', 'add', 'origin', bare)
    git(project, 'checkout', '--quiet', '-b', 'feature-x')
    # One spec, committed, so the status the script prints holds a row.
    os.makedirs(os.path.join(project, 'specs', 'app'))
    with open(os.path.join(project, 'specs', 'app', 'login.md'), 'w',
              encoding='utf-8') as handle:
        handle.write(LOGIN)
    git(project, 'add', '-A')
    git(project, 'commit', '--quiet', '-m', 'spec(login): one rule')
    head = git(project, 'rev-parse', 'HEAD').stdout.strip()
    run_branch = 'run/feature-x-%s' % head[:7]
    _gh_on_the_path(tmp_path, monkeypatch)
    monkeypatch.setattr(windows_run.time, 'sleep', lambda seconds: None)
    started = []
    real = subprocess.run

    def the_runner_commits():
        runner = make_runner_clone(tmp_path, bare, run_branch)
        evidence = os.path.join(runner, '.purlin', 'evidence', 'ci')
        os.makedirs(evidence)
        with open(os.path.join(evidence, 'feat.json'), 'w',
                  encoding='utf-8') as handle:
            handle.write('{}\n')
        git(runner, 'add', '-A')
        git(runner, 'commit', '--quiet', '-m',
            'purlin: evidence at %s' % head[:7])
        git(runner, 'push', '--quiet', 'origin', 'HEAD:%s' % run_branch)

    def run(argv, **kwargs):
        argv = list(argv)
        if argv[:3] == ['gh', 'run', 'list']:
            return subprocess.CompletedProcess(argv, 0, RUN_LIST, '')
        if argv[0] == 'gh':
            started.append(argv)
            the_runner_commits()
            return subprocess.CompletedProcess(argv, 1, '', '')
        # The runner's own git, in its own checkout, is not this script's.
        if (argv[:2] in (['git', 'push'], ['git', 'pull'])
                and kwargs.get('cwd') == project):
            started.append(argv)
            kwargs = dict(kwargs, capture_output=True)
        return real(argv, **kwargs)
    monkeypatch.setattr(windows_run.subprocess, 'run', run)

    assert windows_run.windows_run(project) == 1
    assert started == [
        ['git', 'push', 'origin', 'HEAD:refs/heads/%s' % run_branch],
        WATCH,
        ['git', 'pull', '--ff-only', 'origin', run_branch],
        ['git', 'push', 'origin', '--delete', run_branch]], started
    printed = capsys.readouterr().out
    assert FAILED_ON_GITHUB in printed.splitlines()
    # The output ends with the real status table of this project, every line
    # of it, and the failure line is the one line above it.
    monkeypatch.setattr(windows_run.subprocess, 'run', real)
    table = purlin_status.sync_status(project).splitlines()
    assert table[0].startswith('Purlin status: '), table
    assert [line.split()[:2] for line in table
            if line.startswith('login ')] == [['login', '1']], table
    lines = printed.splitlines()
    assert lines[-len(table):] == table, printed
    assert lines[:-len(table)] == [
        'Pushing feature-x as %s.' % run_branch,
        'Waiting for the windows.yml workflow on %s.' % run_branch,
        FAILED_ON_GITHUB], printed
    # The pull and the delete did what they were started for.
    assert git(project, 'log', '-1', '--format=%s').stdout.strip() == (
        'purlin: evidence at %s' % head[:7])
    assert git(project, 'rev-parse', 'HEAD~1').stdout.strip() == head
    assert git(bare, 'branch', '--list', 'run/*').stdout.strip() == ''


def make_runner_clone(tmp_path, bare, run_branch):
    """A second checkout of the run branch, as GitHub's runner has."""
    runner = str(tmp_path / 'runner')
    git(tmp_path, 'clone', '--quiet', '--branch', run_branch, bare, runner)
    git(runner, 'config', 'user.name', 'github-actions[bot]')
    git(runner, 'config', 'user.email', 'runner@example.com')
    git(runner, 'config', 'commit.gpgsign', 'false')
    return runner


# ---------------------------------------------------------------------------
# The refusal
# ---------------------------------------------------------------------------

# purlin: windows_run PROOF-3
def test_one_uncommitted_file_exits_1_with_the_one_line_and_no_push(
        tmp_path, monkeypatch, capsys):
    """A run against a commit the tree no longer matches proves the wrong thing."""
    project = make_repo(tmp_path / 'project')
    git(project, 'remote', 'add', 'origin', str(tmp_path / 'github.git'))
    _gh_on_the_path(tmp_path, monkeypatch)
    with open(os.path.join(project, 'uncommitted.txt'), 'w',
              encoding='utf-8') as handle:
        handle.write('x\n')
    started = []

    def record(root, argv, **_kwargs):
        # A push that got this far fails, so the run ends here and not after
        # a minute of asking GitHub for a run.
        started.append(list(argv))
        return 1
    monkeypatch.setattr(windows_run, '_run', record)

    assert windows_run.windows_run(project) == 1
    assert capsys.readouterr().out.splitlines() == [NOT_COMMITTED]
    assert started == [], 'a tree with uncommitted changes started %r' % started

    # The one file is refused whichever way it is not committed: new and
    # staged with `git add`, and a committed file changed on disk.
    staged = make_repo(tmp_path / 'staged')
    git(staged, 'remote', 'add', 'origin', str(tmp_path / 'github.git'))
    with open(os.path.join(staged, 'staged.txt'), 'w',
              encoding='utf-8') as handle:
        handle.write('x\n')
    git(staged, 'add', 'staged.txt')
    assert git(staged, 'status', '--porcelain').stdout == 'A  staged.txt\n'
    assert windows_run.windows_run(staged) == 1
    assert capsys.readouterr().out.splitlines() == [NOT_COMMITTED]
    assert started == [], 'a tree with a staged file started %r' % started

    changed = make_repo(tmp_path / 'changed')
    git(changed, 'remote', 'add', 'origin', str(tmp_path / 'github.git'))
    with open(os.path.join(changed, 'README.md'), 'w',
              encoding='utf-8') as handle:
        handle.write('the project, changed\n')
    assert git(changed, 'status', '--porcelain').stdout == ' M README.md\n'
    assert windows_run.windows_run(changed) == 1
    assert capsys.readouterr().out.splitlines() == [NOT_COMMITTED]
    assert started == [], 'a tree with a changed file started %r' % started


def test_any_argument_is_refused_with_one_line_and_nothing_starts(
        tmp_path, monkeypatch, capsys):
    """No proof names this. `--help` would otherwise push a run branch."""
    started = []

    def record(*args, **_kwargs):
        started.append(args)
        raise AssertionError('a command line with an argument started %r'
                             % (args,))
    monkeypatch.setattr(subprocess, 'run', record)
    monkeypatch.setattr(windows_run, 'windows_run', record)

    assert windows_run.main(['--help'], str(tmp_path)) == 2
    assert capsys.readouterr().out.splitlines() == [
        '--help is not an argument of python3 dev/windows_run.py, which '
        'takes none, so nothing was pushed. Run python3 dev/windows_run.py.']
    assert started == []


# ---------------------------------------------------------------------------
# The workflow file
# ---------------------------------------------------------------------------

def _workflow():
    """The workflow's lines, comments and blank lines taken out."""
    with open(WORKFLOW, encoding='utf-8') as handle:
        return [line.rstrip() for line in handle
                if line.strip() and not line.lstrip().startswith('#')]


def _block(lines, key):
    """The lines under the top-level `key:`, up to the next top-level key."""
    start = lines.index(key + ':')
    rest = lines[start + 1:]
    for index, line in enumerate(rest):
        if not line.startswith(' '):
            return rest[:index]
    return rest


def _steps(lines):
    """Each step of the one job, as its own list of stripped lines."""
    steps = []
    for line in lines[lines.index('    steps:') + 1:]:
        if line.startswith('      - '):
            steps.append([line[8:].strip()])
        else:
            steps[-1].append(line.strip())
    return steps


# purlin: windows_run PROOF-4
def test_the_workflow_starts_on_a_run_branch_runs_on_windows_and_pushes_back():
    lines = _workflow()
    assert _block(lines, 'on') == ['  push:', "    branches: ['run/**']"]

    text = '\n'.join(lines)
    assert re.findall(r'runs-on:\s*(.+)', text) == ['windows-latest']
    assert re.findall(r'\b(\w+)-latest\b', text) == ['windows']
    assert not re.search(r'ubuntu|macos|linux|matrix', text, re.I), text

    steps = _steps(lines)
    runs = [index for index, step in enumerate(steps)
            if any(re.search(r'scripts/run/purlin_run\.py"? --ci --commit$',
                             line) for line in step)]
    assert len(runs) == 1, steps
    # The step runs the script: the line is a command of the step's `run:`,
    # python started on the script and nothing before it, and no other line
    # of the workflow names the script.
    step = steps[runs[0]]
    commands = step[step.index('run: |') + 1:]
    command = re.compile(r'(?:python3?|py) "?(?:[^\s"]+/)?scripts/run/'
                         r'purlin_run\.py"? --ci --commit')
    ran = [line for line in commands if command.fullmatch(line)]
    assert len(ran) == 1, commands
    assert [line.strip() for line in lines if 'purlin_run.py' in line] == ran, \
        lines
    after = steps[runs[0] + 1:]
    pushes = [step for step in after if 'if: always()' in step]
    assert len(pushes) == 1, after
    assert 'run: git push origin "HEAD:${GITHUB_REF_NAME}"' in pushes[0], \
        pushes[0]
