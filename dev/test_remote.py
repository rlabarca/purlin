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

*remote URL*  the organisation and project the run is looked up in come
              out of the three remote forms, a user part and a
              percent-encoded name, and a URL in none of them is refused
*commands*    the argv of the lookup and of the poll
*the wait*    a run not registered at first and then found, `inProgress`
              then `completed` with each of the four results, the 60-second
              and 90-minute limits, and no `az` on PATH
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

def _looked_up_in(fake):
    """`(organization, project)` the first lookup named."""
    first = fake.az_calls()[0]
    return (first[first.index('--organization') + 1],
            first[first.index('--project') + 1])


# purlin: host PROOF-36
@pytest.mark.parametrize('url', [
    'https://dev.azure.com/acme/widgets/_git/shop',
    'git@ssh.dev.azure.com:v3/acme/widgets/shop',
    'https://acme.visualstudio.com/widgets/_git/shop',
])
def test_each_remote_form_names_the_organisation_and_the_project(azure_run,
                                                                url):
    fake, _clock = azure_run(origin=url)

    assert remote_module.run_remote('/project') == 0
    assert _looked_up_in(fake) == ('https://dev.azure.com/acme', 'widgets')


# purlin: host PROOF-73
def test_a_user_part_before_the_host_is_ignored(azure_run):
    fake, _clock = azure_run(
        origin='https://acme@dev.azure.com/acme/widgets/_git/shop')

    assert remote_module.run_remote('/project') == 0
    assert _looked_up_in(fake) == ('https://dev.azure.com/acme', 'widgets')


# purlin: host PROOF-74
@pytest.mark.parametrize('url', [
    'https://dev.azure.com/acme/My%20Widgets/_git/shop',
    'git@ssh.dev.azure.com:v3/acme/My%20Widgets/shop',
])
def test_a_percent_encoded_project_is_decoded(azure_run, url):
    fake, _clock = azure_run(origin=url)

    assert remote_module.run_remote('/project') == 0
    assert _looked_up_in(fake) == ('https://dev.azure.com/acme', 'My Widgets')


# purlin: host PROOF-75
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
def test_the_lookup_names_the_organisation_the_project_and_the_run_branch(
        azure_run):
    fake, _clock = azure_run()

    remote_module.run_remote('/project')
    assert fake.az_calls()[0] == LIST


# purlin: host PROOF-76
def test_the_poll_names_the_run_the_organisation_and_the_project(azure_run):
    fake, _clock = azure_run()

    assert remote_module.run_remote('/project') == 0
    assert fake.az_calls() == [LIST, SHOW]


# purlin: host PROOF-77
def test_a_run_not_registered_at_first_is_asked_for_again(azure_run):
    fake, clock = azure_run(lookups=('', '', '42'))

    assert remote_module.run_remote('/project') == 0
    assert fake.az_calls() == [LIST, LIST, LIST, SHOW]
    assert clock.slept == [3, 3]


# purlin: host PROOF-78
def test_a_succeeded_run_is_brought_home_green(azure_run, capsys):
    fake, clock = azure_run(polls=('inProgress\t', 'inProgress\t',
                                   'completed\tsucceeded'))

    assert remote_module.run_remote('/project') == 0
    assert fake.az_calls() == [LIST, SHOW, SHOW, SHOW]
    assert clock.slept == [15, 15]
    assert fake.not_az() == [PUSH, PULL, DELETE]
    printed = capsys.readouterr().out
    assert 'Run 42 completed: succeeded.' in printed.splitlines()
    assert 'The run finished red.' not in printed
    assert printed.rstrip().endswith('the status table')


# purlin: host PROOF-79
@pytest.mark.parametrize('result', ['failed', 'canceled', 'partiallySucceeded'])
def test_a_run_that_did_not_succeed_is_brought_home_red(azure_run, capsys,
                                                        result):
    fake, _clock = azure_run(polls=('completed\t%s' % result,))

    assert remote_module.run_remote('/project') == 1
    assert fake.not_az() == [PUSH, PULL, DELETE]
    printed = capsys.readouterr().out
    lines = printed.splitlines()
    assert 'Run 42 completed: %s.' % result in lines
    assert 'The run finished red. The table below is what came back.' in lines
    assert printed.rstrip().endswith('the status table')


# purlin: host PROOF-80
def test_no_run_within_a_minute_deletes_the_branch_and_fails(azure_run,
                                                             capsys):
    fake, clock = azure_run(lookups=('',))

    assert remote_module.run_remote('/project') == 1
    assert fake.az_calls() == [LIST] * 21
    assert clock.slept == [3] * 20
    assert fake.not_az() == [PUSH, DELETE]
    printed = capsys.readouterr().out
    assert 'No run registered for %s within 60 seconds' % RUN_BRANCH in printed
    assert 'git pull --ff-only origin %s' % RUN_BRANCH in printed
    assert 'the status table' not in printed


# purlin: host PROOF-81
def test_a_run_past_ninety_minutes_is_left_for_the_person(azure_run, capsys):
    fake, clock = azure_run(polls=('inProgress\t',))

    assert remote_module.run_remote('/project') == 1
    assert clock.slept == [15] * 360
    assert fake.az_calls() == [LIST] + [SHOW] * 361
    assert fake.not_az() == [PUSH]
    printed = capsys.readouterr().out
    assert 'Run 42 on %s has not completed after 90 minutes' % RUN_BRANCH \
        in printed
    assert 'git pull --ff-only origin %s' % RUN_BRANCH in printed
    assert 'git push origin --delete %s' % RUN_BRANCH in printed
    assert 'the status table' not in printed


# purlin: host PROOF-82
def test_without_az_the_run_is_neither_found_nor_pulled(azure_run, capsys):
    fake, _clock = azure_run(az=False)

    assert remote_module.run_remote('/project') == 1
    assert fake.started == [PUSH]
    printed = capsys.readouterr().out
    assert 'The Azure CLI `az` is not on PATH' in printed
    assert 'https://dev.azure.com/acme/My%20Widgets/_build' in printed
    assert 'git pull --ff-only origin %s' % RUN_BRANCH in printed
    assert 'the status table' not in printed


# purlin: host PROOF-83
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
