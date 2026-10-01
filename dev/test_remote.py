"""Tests for the Azure DevOps half of `scripts/run/remote.py`.

`purlin:test --remote` on an Azure DevOps remote finds the pipeline run its
push started, waits for it to complete, and brings the runner's commit home
the way the GitHub half does. Every process `remote.py` starts is answered
here by a stand-in for `subprocess.run`, the `az` it finds on PATH is a
stand-in program, `az` with the exec bit on POSIX and `az.cmd` on Windows,
and the clock only moves when the code sleeps, so
nothing reaches a network and no test waits.

What these tests cannot show is how the real Azure DevOps service and the
real Azure CLI answer. A hand-run check on a machine with Azure DevOps
access confirms that part.

What each group proves:

*remote URL*  the organisation and project the run is looked up in come
              out of the three remote forms, a percent-encoded name decoded
*the wait*    `inProgress` then `completed`, a green and a red result, the
              90-minute limit, and no process that can wait forever or ask
"""

import os
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'run'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import remote as remote_module  # noqa: E402

SHA = '4f1c2ab9e1d4e8c9b5f2a7d3c6e0b8a1d9f4c2e7'
RUN_BRANCH = 'run/feature-x-4f1c2ab'
ORIGIN = 'https://dev.azure.com/acme/My%20Widgets/_git/shop'
PUSH = ['git', 'push', 'origin', 'HEAD:refs/heads/%s' % RUN_BRANCH]
PULL = ['git', 'pull', '--ff-only', 'origin', RUN_BRANCH]
DELETE = ['git', 'push', 'origin', '--delete', RUN_BRANCH]
LIST = ['pipelines', 'runs', 'list',
        '--organization', 'https://dev.azure.com/acme',
        '--project', 'My Widgets',
        '--branch', 'refs/heads/%s' % RUN_BRANCH,
        '--top', '1', '--query', '[0].id', '--output', 'tsv']
FAILED_ON_HOST = ('The run failed on the git host. The table below is what '
                  'came back.')
SHOW = ['pipelines', 'runs', 'show', '--id', '42',
        '--organization', 'https://dev.azure.com/acme',
        '--project', 'My Widgets',
        '--query', '[status,result]', '--output', 'tsv']


# ---------------------------------------------------------------------------
# Stand-ins
# ---------------------------------------------------------------------------

class Clock(object):
    """`time.time` and `time.sleep` for `remote.py`: time moves on a sleep."""

    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


class FakeAzure(object):
    """`subprocess.run` for `remote.py`: git and az answer, and nothing runs.

    The branch is `feature-x`, HEAD is `SHA` and `origin` is `origin`.
    `lookups` is the list of answers `az pipelines runs list` gives, one per
    call, the last repeated; `polls` the same for `az pipelines runs show`.
    Every call is kept in `calls` with its keyword arguments, and every call
    that is not a read of git's own state is kept in `started`, in order.
    """

    def __init__(self, origin=ORIGIN, lookups=('42',),
                 polls=('completed\tsucceeded',)):
        self.origin = origin
        self.lookups = list(lookups)
        self.polls = list(polls)
        self.calls = []
        self.started = []

    def __call__(self, argv, **kwargs):
        argv = list(argv)
        self.calls.append((argv, kwargs))
        if argv[:3] == ['git', 'rev-parse', '--abbrev-ref']:
            return self._answer(argv, 'feature-x\n')
        if argv[:2] == ['git', 'rev-parse']:
            return self._answer(argv, SHA + '\n')
        if argv[:3] == ['git', 'remote', 'get-url']:
            return self._answer(argv, self.origin + '\n')
        if argv[:3] == ['git', 'status', '--porcelain']:
            return self._answer(argv, '')
        self.started.append(argv)
        if _is_az(argv[0]):
            if argv[1:4] == ['pipelines', 'runs', 'list']:
                return self._answer(argv, self._next(self.lookups) + '\n')
            if argv[1:4] == ['pipelines', 'runs', 'show']:
                return self._answer(argv, self._next(self.polls) + '\n')
        return self._answer(argv, '')

    @staticmethod
    def _next(answers):
        return answers.pop(0) if len(answers) > 1 else answers[0]

    @staticmethod
    def _answer(argv, out):
        return subprocess.CompletedProcess(argv, 0, out, '')

    def az_calls(self):
        return [argv[1:] for argv in self.started if _is_az(argv[0])]

    def not_az(self):
        return [argv for argv in self.started if not _is_az(argv[0])]


def _is_az(program):
    """True for the `az` the lookup found: `az`, or `az.cmd` on Windows."""
    name = os.path.basename(program)
    return os.path.splitext(name)[0].lower() == 'az'


def _stand_in_az(folder):
    """The `az` the system's own lookup finds, which nothing ever starts."""
    if os.name == 'nt':
        path = folder / 'az.cmd'
        path.write_text('@echo off\r\n', encoding='utf-8')
    else:
        path = folder / 'az'
        path.write_text('#!/bin/sh\n', encoding='utf-8')
        path.chmod(0o755)


@pytest.fixture
def project(tmp_path):
    """A project folder that already carries its Azure DevOps runner file."""
    folder = tmp_path / 'project'
    folder.mkdir()
    (folder / 'purlin.azure-pipelines.yml').write_text('trigger: none\n',
                                                      encoding='utf-8')
    return str(folder)


@pytest.fixture
def azure_run(monkeypatch, tmp_path):
    """Stand in for every process and the clock, with or without `az`."""
    def arrange(az=True, **answers):
        folder = tmp_path / ('with-az' if az else 'without-az')
        folder.mkdir()
        if az:
            _stand_in_az(folder)
        monkeypatch.setenv('PATH', str(folder))
        fake = FakeAzure(**answers)
        clock = Clock()
        monkeypatch.setattr(remote_module.subprocess, 'run', fake)
        monkeypatch.setattr(remote_module.time, 'time', clock.time)
        monkeypatch.setattr(remote_module.time, 'sleep', clock.sleep)
        monkeypatch.setattr(remote_module, '_table',
                            lambda project_root: 'the status table')
        return fake, clock
    return arrange


# ---------------------------------------------------------------------------
# The remote URL
# ---------------------------------------------------------------------------

def _looked_up_in(fake):
    """`(organization, project)` the first lookup named."""
    first = fake.az_calls()[0]
    return (first[first.index('--organization') + 1],
            first[first.index('--project') + 1])


def _organisation_and_project(azure_run, project, url):
    fake, _clock = azure_run(origin=url)

    assert remote_module.run_remote(project) == 0
    return _looked_up_in(fake)


# purlin: host PROOF-36
def test_the_https_form_names_the_organisation_and_the_project(azure_run,
                                                               project):
    assert _organisation_and_project(
        azure_run, project, 'https://dev.azure.com/acme/widgets/_git/shop') == (
        'https://dev.azure.com/acme', 'widgets')


# purlin: host PROOF-112
def test_the_visualstudio_form_names_the_organisation_and_the_project(
        azure_run, project):
    assert _organisation_and_project(
        azure_run, project,
        'https://acme.visualstudio.com/widgets/_git/shop') == (
        'https://dev.azure.com/acme', 'widgets')


# purlin: host PROOF-113
def test_a_percent_encoded_project_in_the_ssh_form_is_decoded(azure_run,
                                                              project):
    assert _organisation_and_project(
        azure_run, project,
        'git@ssh.dev.azure.com:v3/acme/My%20Widgets/shop') == (
        'https://dev.azure.com/acme', 'My Widgets')


# ---------------------------------------------------------------------------
# The wait
# ---------------------------------------------------------------------------

# purlin: host PROOF-78
def test_a_succeeded_run_is_brought_home_green(azure_run, project, capsys):
    fake, clock = azure_run(polls=('inProgress\t', 'inProgress\t',
                                   'completed\tsucceeded'))

    assert remote_module.run_remote(project) == 0
    assert fake.az_calls() == [LIST, SHOW, SHOW, SHOW]
    started_as = {os.path.basename(argv[0]).lower()
                  for argv in fake.started if _is_az(argv[0])}
    assert started_as == {'az.cmd' if os.name == 'nt' else 'az'}, started_as
    assert clock.slept == [15, 15]
    assert fake.not_az() == [PUSH, PULL, DELETE]
    printed = capsys.readouterr().out
    assert 'Run 42 completed: succeeded.' in printed.splitlines()
    assert FAILED_ON_HOST not in printed
    assert printed.rstrip().endswith('the status table')


# purlin: host PROOF-79
def test_a_failed_run_says_so_pulls_deletes_and_exits_1(azure_run, project,
                                                        capsys):
    """`Run 42 completed: failed.`, then the line that the run failed."""
    fake, _clock = azure_run(polls=('completed\tfailed',))

    assert remote_module.run_remote(project) == 1
    assert fake.not_az() == [PUSH, PULL, DELETE]
    printed = capsys.readouterr().out
    lines = printed.splitlines()
    assert lines.index('Run 42 completed: failed.') < lines.index(
        FAILED_ON_HOST), lines
    assert printed.rstrip().endswith('the status table')


# purlin: host PROOF-81
def test_a_run_past_ninety_minutes_is_polled_361_times_and_left(
        azure_run, project, capsys):
    """Neither pulled nor deleted, no table, and the two commands named."""
    fake, clock = azure_run(polls=('inProgress\t',))

    assert remote_module.run_remote(project) == 1
    assert clock.slept == [15] * 360
    assert fake.az_calls() == [LIST] + [SHOW] * 361
    assert fake.not_az() == [PUSH]
    printed = capsys.readouterr().out
    assert 'Run 42 on %s has not completed after 90 minutes' % RUN_BRANCH \
        in printed
    assert 'git pull --ff-only origin %s' % RUN_BRANCH in printed
    assert 'git push origin --delete %s' % RUN_BRANCH in printed
    assert 'the status table' not in printed


# purlin: host PROOF-83
def test_no_process_can_wait_forever_or_prompt(azure_run, project):
    """The lookup answers at the second ask and the run finishes failed."""
    fake, _clock = azure_run(lookups=('', '42'),
                             polls=('inProgress\t', 'completed\tfailed'))

    assert remote_module.run_remote(project) == 1
    assert fake.calls
    for argv, kwargs in fake.calls:
        assert kwargs.get('timeout'), argv
        assert kwargs.get('stdin') is subprocess.DEVNULL, argv
        assert kwargs['env']['GIT_TERMINAL_PROMPT'] == '0', argv
        assert kwargs['env']['AZURE_EXTENSION_USE_DYNAMIC_INSTALL'] == 'no', \
            argv
