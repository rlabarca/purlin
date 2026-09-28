"""Tests for the Azure DevOps half of `scripts/run/remote.py`.

`purlin:test --remote` on an Azure DevOps remote finds the pipeline run its
push started, waits for it to complete, and brings the runner's commit home
the way the GitHub half does. Every process `remote.py` starts is answered
here by a stand-in for `subprocess.run`, the `az` it finds on PATH is an
empty executable file, and the clock only moves when the code sleeps, so
nothing reaches a network and no test waits.

What these tests cannot show is how the real Azure DevOps service and the
real Azure CLI answer. A hand-run check on a machine with Azure DevOps
access confirms that part.

What each group proves:

*remote URL*  the organisation, project and repository come out of the
              three remote forms, a user part and a percent-encoded name
*commands*    the argv of the lookup and of the poll
*the wait*    a run not registered at first and then found, `inProgress`
              then `completed` with each of the four results, the 60-second
              and 90-minute limits shortened, and no `az` on PATH
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
        if os.path.basename(argv[0]) == 'az':
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
        return [argv[1:] for argv in self.started
                if os.path.basename(argv[0]) == 'az']

    def not_az(self):
        return [argv for argv in self.started
                if os.path.basename(argv[0]) != 'az']


@pytest.fixture
def azure_run(monkeypatch, tmp_path):
    """Stand in for every process and the clock, with or without `az`."""
    def arrange(az=True, **answers):
        folder = tmp_path / ('with-az' if az else 'without-az')
        folder.mkdir()
        if az:
            fake_az = folder / 'az'
            fake_az.write_text('', encoding='utf-8')
            fake_az.chmod(0o755)
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

# purlin: host PROOF-36
@pytest.mark.parametrize('url', [
    'https://dev.azure.com/acme/widgets/_git/shop',
    'git@ssh.dev.azure.com:v3/acme/widgets/shop',
    'https://acme.visualstudio.com/widgets/_git/shop',
    'https://acme@dev.azure.com/acme/widgets/_git/shop',
])
def test_each_remote_form_names_the_organisation_project_and_repository(url):
    assert remote_module.parse_azure_remote(url) == ('acme', 'widgets', 'shop')


# purlin: host PROOF-36
@pytest.mark.parametrize('url', [
    'https://dev.azure.com/acme/My%20Widgets/_git/shop',
    'git@ssh.dev.azure.com:v3/acme/My%20Widgets/shop',
])
def test_a_percent_encoded_project_is_decoded(url):
    assert remote_module.parse_azure_remote(url) == (
        'acme', 'My Widgets', 'shop')


# purlin: host PROOF-36
@pytest.mark.parametrize('url', [
    'https://github.com/acme/widgets.git',
    'https://dev.azure.com/acme/widgets',
    '',
])
def test_a_url_in_no_azure_form_reads_none(url):
    assert remote_module.parse_azure_remote(url) is None


# purlin: host PROOF-36
def test_a_remote_in_no_azure_form_is_refused_before_the_push(azure_run,
                                                              capsys):
    fake, _clock = azure_run(origin='https://dev.azure.com/acme/widgets')

    assert remote_module.run_remote('/project') == 1
    assert fake.started == []
    printed = capsys.readouterr().out.strip()
    assert printed == (
        'The remote https://dev.azure.com/acme/widgets is not an Azure '
        'DevOps repository URL, so nothing was pushed: set origin to the URL '
        'Azure DevOps shows under Clone and run purlin:test --remote again.')


# ---------------------------------------------------------------------------
# The wait
# ---------------------------------------------------------------------------

# purlin: host PROOF-37
def test_the_lookup_and_the_poll_name_the_organisation_and_the_project(
        azure_run):
    fake, _clock = azure_run()

    assert remote_module.run_remote('/project') == 0
    assert fake.az_calls() == [LIST, SHOW]


# purlin: host PROOF-37
def test_a_run_not_registered_at_first_is_asked_for_again(azure_run):
    fake, clock = azure_run(lookups=('', '', '42'))

    assert remote_module.run_remote('/project') == 0
    assert fake.az_calls() == [LIST, LIST, LIST, SHOW]
    assert clock.slept == [3, 3]


# purlin: host PROOF-37
@pytest.mark.parametrize('result, code', [
    ('succeeded', 0),
    ('failed', 1),
    ('canceled', 1),
    ('partiallySucceeded', 1),
])
def test_a_completed_run_is_brought_home_whatever_its_result(azure_run, capsys,
                                                            result, code):
    fake, clock = azure_run(polls=('inProgress\t', 'inProgress\t',
                                   'completed\t%s' % result))

    assert remote_module.run_remote('/project') == code
    assert fake.az_calls() == [LIST, SHOW, SHOW, SHOW]
    assert clock.slept == [15, 15]
    assert fake.not_az() == [PUSH, PULL, DELETE]
    printed = capsys.readouterr().out
    assert 'Run 42 completed: %s.' % result in printed
    assert ('The run finished red.' in printed) is (code == 1)
    assert printed.rstrip().endswith('the status table')


# purlin: host PROOF-37
def test_no_run_within_the_find_limit_deletes_the_branch_and_fails(
        azure_run, monkeypatch, capsys):
    monkeypatch.setattr(remote_module, 'FIND_SECONDS', 9)
    fake, clock = azure_run(lookups=('',))

    assert remote_module.run_remote('/project') == 1
    assert clock.slept == [3, 3, 3]
    assert fake.az_calls() == [LIST] * 4
    assert fake.not_az() == [PUSH, DELETE]
    printed = capsys.readouterr().out
    assert 'No run registered for %s within 9 seconds' % RUN_BRANCH in printed
    assert 'git pull --ff-only origin %s' % RUN_BRANCH in printed
    assert 'the status table' not in printed


# purlin: host PROOF-37
def test_a_run_past_the_poll_limit_is_left_for_the_person(azure_run,
                                                           monkeypatch,
                                                           capsys):
    monkeypatch.setattr(remote_module, 'POLL_SECONDS', 120)
    fake, clock = azure_run(polls=('inProgress\t',))

    assert remote_module.run_remote('/project') == 1
    assert clock.slept == [15] * 8
    assert fake.az_calls() == [LIST] + [SHOW] * 9
    assert fake.not_az() == [PUSH]
    printed = capsys.readouterr().out
    assert 'Run 42 on %s has not completed after 2 minutes' % RUN_BRANCH \
        in printed
    assert 'git pull --ff-only origin %s' % RUN_BRANCH in printed
    assert 'git push origin --delete %s' % RUN_BRANCH in printed
    assert 'the status table' not in printed


# purlin: host PROOF-37
def test_without_az_the_run_is_neither_found_nor_pulled(azure_run, capsys):
    fake, _clock = azure_run(az=False)

    assert remote_module.run_remote('/project') == 1
    assert fake.started == [PUSH]
    printed = capsys.readouterr().out
    assert 'The Azure CLI `az` is not on PATH' in printed
    assert 'https://dev.azure.com/acme/My%20Widgets/_build' in printed
    assert 'git pull --ff-only origin %s' % RUN_BRANCH in printed
    assert 'the status table' not in printed


# purlin: host PROOF-37
def test_no_process_can_wait_forever_or_prompt(azure_run):
    fake, _clock = azure_run(lookups=('', '42'),
                             polls=('inProgress\t', 'completed\tfailed'))

    assert remote_module.run_remote('/project') == 1
    assert fake.calls
    for argv, kwargs in fake.calls:
        assert kwargs.get('timeout'), argv
        assert kwargs.get('stdin') is subprocess.DEVNULL, argv
        assert kwargs['env']['GIT_TERMINAL_PROMPT'] == '0', argv
        assert kwargs['env']['AZURE_EXTENSION_USE_DYNAMIC_INSTALL'] == 'no', \
            argv


# purlin: host PROOF-37
def test_the_intervals_and_limits_are_the_modules_own():
    assert remote_module.FIND_EVERY == 3
    assert remote_module.FIND_SECONDS == 60
    assert remote_module.POLL_EVERY == 15
    assert remote_module.POLL_SECONDS == 5400
