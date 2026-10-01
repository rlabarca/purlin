#!/usr/bin/env python3
"""This repository's own Windows run, started from the owner's Mac.

    python3 dev/windows_run.py

A proof tagged `@env(windows)` cannot be proven on a Mac. Purlin starts no run
on another machine, so this repository holds its own setup for one, as any
project would: `.github/workflows/windows.yml`, which GitHub runs on
`windows-latest`, and this script, which starts that workflow and brings back
what it wrote.

The script pushes this commit to a branch of its own, `run/<branch>-<sha7>`,
which starts the workflow. It waits for that run, pulls the one commit the run
made, `purlin: evidence at <sha7>`, deletes the run branch and prints the
status. A failed run's results come back the same way. The working branch
itself is never pushed.

A checkout on no branch has nothing to name the run branch after, and
uncommitted changes would mean the run proves something other than what is on
disk, so both are refused before anything is pushed. So is a machine without
`gh`: the run branch would be left on GitHub with nobody waiting for it.

The run is found by the branch it was started for and by the workflow file,
asked again while the run registers, which takes a few seconds. Then
`gh run watch <id>` waits; the id is named because `gh run watch` with no id
prompts for one and fails where there is no terminal.

No process started here asks for anything: stdin is closed and git is told not
to prompt for a credential. A missing credential is a failed command, not a
question.
"""

import json
import os
import shutil
import subprocess
import sys
import time

_DEV_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_DEV_DIR)
_MCP_DIR = os.path.join(ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

WORKFLOW = 'windows.yml'
WORKFLOW_PATH = '.github/workflows/' + WORKFLOW
REMOTE = 'origin'
RUN_BRANCH_PREFIX = 'run/'

NOT_ON_A_BRANCH = ('This checkout is not on a branch, so there is nothing to '
                   'push. Make one with git switch -c <name>, then run '
                   'python3 dev/windows_run.py again.')
NOT_COMMITTED = ('This checkout has changes that are not committed, so a run '
                 'would prove something other than what is here. Commit them, '
                 'then run python3 dev/windows_run.py again.')
PUSH_FAILED = ('The push failed, so no run was started. Check that git push '
               'origin works from this checkout, then run python3 '
               'dev/windows_run.py again.')
# Printed before any push: without gh the run branch would be left on GitHub
# with nobody waiting for it.
NO_GH = ('python3 dev/windows_run.py waits for the run with the GitHub CLI, '
         'gh, which is not installed, so nothing was pushed. Install gh, then '
         'run python3 dev/windows_run.py again.')

# How long to keep asking GitHub which run this push started. A run takes a
# few seconds to register, and asking once would miss it; a minute is far
# longer than GitHub takes and short enough to fail while a person is still
# watching.
FIND_SECONDS = 60
FIND_EVERY = 3
NO_RUN_FOUND = ('No run registered for %s within %d seconds, so the run '
                'branch was deleted and nothing came back. Check that GitHub '
                'runs %s on a push to run/*, then run python3 '
                'dev/windows_run.py again.')
FAILED_ON_GITHUB = ('The run failed on GitHub. The table below is what came '
                    'back.')
STILL_THERE = ('The run branch %s is still on %s. Delete it with: git push %s '
               '--delete %s')
# How long one git command may take before it is abandoned.
COMMAND_SECONDS = 300


def run_branch_name(project_root, branch):
    """The branch one run lives on: `run/<branch>-<sha7>`.

    The commit's own short sha is in the name, so two runs of the same branch
    never share a branch and a run left behind is readable for what it was.
    """
    sha = (_capture(project_root, ['git', 'rev-parse', 'HEAD']) or '').strip()
    return '%s%s-%s' % (RUN_BRANCH_PREFIX, branch, sha[:7])


def windows_run(project_root):
    """Push a run branch, wait for the run, pull it back, delete the branch.

    Answers the exit code. Refused before anything is pushed, each with the
    one line saying why: a checkout on no branch or with changes not
    committed, and a machine with no `gh` on the search path.
    """
    branch = _branch(project_root)
    if not branch or branch == 'HEAD':
        print(NOT_ON_A_BRANCH)
        return 1
    if _dirty(project_root):
        print(NOT_COMMITTED)
        return 1
    if not _have('gh'):
        print(NO_GH)
        return 1

    run_branch = run_branch_name(project_root, branch)
    print('Pushing %s as %s.' % (branch, run_branch))
    if _push(project_root, run_branch) != 0:
        print(PUSH_FAILED)
        return 1
    return _github(project_root, run_branch)


def _github(project_root, run_branch):
    print('Waiting for the %s workflow on %s.' % (WORKFLOW, run_branch))
    run_id = find_run(project_root, run_branch)
    if not run_id:
        print(NO_RUN_FOUND % (run_branch, FIND_SECONDS, WORKFLOW_PATH))
        _delete(project_root, run_branch)
        return 1
    watched = _run(project_root,
                   ['gh', 'run', 'watch', run_id, '--exit-status'],
                   timeout=None)
    return _bring_back(project_root, run_branch, watched)


def _bring_back(project_root, run_branch, code):
    """Pull the run's commit, delete the run branch, print the table.

    The same for a green and a red run: a red run's results are evidence too.
    Answers 0 for a green run and 1 for a red one.
    """
    if code != 0:
        print(FAILED_ON_GITHUB)
    # The run branch is this branch plus the one commit the run made, so a
    # fast-forward is the whole of it: that commit is the evidence under
    # `.purlin/evidence/ci/`.
    _run(project_root, ['git', 'pull', '--ff-only', REMOTE, run_branch])
    _delete(project_root, run_branch)
    print(_table(project_root))
    return 0 if code == 0 else 1


def find_run(project_root, run_branch, seconds=FIND_SECONDS):
    """The id of the run this push started, or `''` when none registered.

    The run is looked up by the branch it was started for and by the
    workflow file, because `gh run watch` with no id prompts for one and
    errors where there is no terminal, and where it does choose it takes the
    newest run on the repository, which is not necessarily this one. A run
    takes a few seconds to appear, so the lookup is retried until it does or
    `seconds` have passed.
    """
    deadline = time.time() + max(0, seconds)
    while True:
        listed = _capture(project_root,
                          ['gh', 'run', 'list', '--branch', run_branch,
                           '--workflow', WORKFLOW, '--limit', '1',
                           '--json', 'databaseId'])
        try:
            rows = json.loads(listed or '[]')
        except ValueError:
            rows = []
        if rows and rows[0].get('databaseId'):
            return str(rows[0]['databaseId'])
        if time.time() >= deadline:
            return ''
        time.sleep(FIND_EVERY)


def _push(project_root, run_branch):
    """Create the run branch on the remote from this commit.

    `HEAD:refs/heads/<run branch>` rather than a branch name, so nothing local
    is created and the working branch keeps its own upstream.
    """
    return _run(project_root,
                ['git', 'push', REMOTE, 'HEAD:refs/heads/%s' % run_branch])


def _delete(project_root, run_branch):
    """Remove the run branch from the remote once its evidence is here."""
    if _run(project_root, ['git', 'push', REMOTE, '--delete', run_branch]) != 0:
        print(STILL_THERE % (run_branch, REMOTE, REMOTE, run_branch))


def _dirty(project_root):
    """True when the working tree carries a change no commit holds."""
    status = _capture(project_root, ['git', 'status', '--porcelain',
                                     '--untracked-files=all'])
    return any(line.strip() for line in (status or '').splitlines())


def _table(project_root):
    from purlin import status as status_module
    return status_module.sync_status(project_root)


def _branch(project_root):
    return (_capture(project_root,
                     ['git', 'rev-parse', '--abbrev-ref', 'HEAD']) or '').strip()


def _have(binary):
    """True when `binary` is a program on the search path.

    `shutil.which` is the lookup the system itself makes: on Windows it tries
    each ending `PATHEXT` names, so `gh.exe` and `gh.cmd` are both found, and
    elsewhere it asks for the exec bit. The program is still started by its
    bare name.
    """
    return shutil.which(binary) is not None


def _environment():
    """This process's environment, with every prompt turned off.

    `GIT_TERMINAL_PROMPT=0` makes a push or a pull that lacks a credential
    fail rather than ask for one.
    """
    env = dict(os.environ)
    env['GIT_TERMINAL_PROMPT'] = '0'
    return env


def _run(project_root, argv, timeout=COMMAND_SECONDS):
    """Run one command in the project and answer its exit code.

    `timeout=None` is for `gh run watch` alone, which ends when the run does.
    """
    try:
        return subprocess.run([*argv], cwd=project_root,
                              stdin=subprocess.DEVNULL, env=_environment(),
                              timeout=timeout).returncode
    except (subprocess.SubprocessError, OSError) as error:
        print('%s failed: %s' % (argv[0], error))
        return 1


def _capture(project_root, argv):
    try:
        result = subprocess.run([*argv], cwd=project_root,
                                stdin=subprocess.DEVNULL, env=_environment(),
                                capture_output=True, text=True, timeout=30)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout if result.returncode == 0 else ''


if __name__ == '__main__':
    sys.exit(windows_run(ROOT))
