"""`purlin:test --remote`: let the git host's runner do the run.

A proof tagged `@env(windows)` cannot be proven on a Mac. Rather than ask
anyone to own a second machine, `--remote` hands the commit to the git host's
runner and brings back what that runner wrote. The evidence is the git host's,
because the commit is the git host's.

What comes back is what the runner committed on the run branch: at `strong`
and above the record it audited, at `passed` the test results under
`.purlin/tests/ci/`. Either way the run pulls that commit onto this branch,
so a proof tagged `@env` for an operating system nobody here has ends up with
its own platform's pass in the tree.

**This is the one push Purlin makes.** Everywhere else a push is a person's
act. Here the push is the point of the command, and it goes to a branch of
its own, `run/<branch>-<sha7>`, which this module creates, waits on, pulls
back from and deletes. The working branch is never pushed, so nothing reaches
the git host that a person did not send there.

A detached head has no branch to name and a dirty tree would run the workflow
against something other than what is on disk, so both are refused before
anything is pushed.

On GitHub the run is found by the branch it was started for, because `gh run
watch` with no id prompts for one and errors where there is no terminal. The
lookup is retried while the run registers, which takes a few seconds, and
then that one run is watched. On Azure DevOps the pipeline URL is printed and
the command returns: watching an Azure DevOps run needs the Azure CLI's
pipelines extension, which is the work-machine follow-up marked below.
"""

import json
import os
import subprocess
import sys
import time

_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(_RUN_DIR))
_MCP_DIR = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

WORKFLOW = 'purlin.yml'
REMOTE = 'origin'
RUN_BRANCH_PREFIX = 'run/'

# How long to keep asking the git host which run this push started. A run
# takes a few seconds to register, and asking once would miss it; a minute is
# far longer than any host takes and short enough to fail while a person is
# still watching.
FIND_SECONDS = 60
FIND_EVERY = 3
NO_RUN_FOUND = ('No run registered for %s within %d seconds. Open it on the '
                'git host, then run: git pull --ff-only %s %s')


def run_branch_name(project_root, branch):
    """The branch one remote run lives on: `run/<branch>-<sha7>`.

    The commit's own short sha is in the name, so two runs of the same branch
    never share a branch and a run left behind is readable for what it was.
    """
    sha = (_capture(project_root, ['git', 'rev-parse', 'HEAD']) or '').strip()
    return '%s%s-%s' % (RUN_BRANCH_PREFIX, branch, sha[:7])


def run_remote(project_root, args=None, cfg=None):
    """Push a run branch, wait for CI, pull it back, delete it. Exit code."""
    host = _host(project_root, args)
    branch = _branch(project_root)
    if not branch or branch == 'HEAD':
        print('This checkout is not on a branch, so there is nothing to push.')
        return 1
    if _dirty(project_root):
        print('This checkout has changes that are not committed, so a run '
              'would prove something other than what is here. Commit them, '
              'then run purlin:test --remote again.')
        return 1

    run_branch = run_branch_name(project_root, branch)
    print('Pushing %s as %s.' % (branch, run_branch))
    if _push(project_root, run_branch) != 0:
        print('The push failed, so no run was started.')
        return 1

    if host == 'azure':
        return _azure(project_root, branch, run_branch)
    return _github(project_root, run_branch)


def _github(project_root, run_branch):
    if not _have('gh'):
        print('GitHub CLI `gh` is not installed, so the run cannot be '
              'watched. Open the run on %s instead, then run: git pull '
              '--ff-only %s %s' % (run_branch, REMOTE, run_branch))
        return 1
    print('Waiting for the %s workflow on %s.' % (WORKFLOW, run_branch))
    run_id = find_run(project_root, run_branch)
    if not run_id:
        print(NO_RUN_FOUND % (run_branch, FIND_SECONDS, REMOTE, run_branch))
        _delete(project_root, run_branch)
        return 1
    watched = _run(project_root,
                   ['gh', 'run', 'watch', run_id, '--exit-status'])
    if watched != 0:
        print('The run finished red. The table below is what came back.')
    # The run branch is this branch plus the one commit the runner made, so a
    # fast-forward is the whole of it: at `strong` and above that commit is
    # the records, and at `passed` the test results under `.purlin/tests/ci/`.
    _run(project_root, ['git', 'pull', '--ff-only', REMOTE, run_branch])
    _delete(project_root, run_branch)
    print(_table(project_root))
    return watched


def find_run(project_root, run_branch, seconds=FIND_SECONDS):
    """The id of the run this push started, or `''` when none registered.

    The run is looked up by the branch it was started for, because `gh run
    watch` with no id prompts for one and errors where there is no terminal,
    and where it does choose it takes the newest run on the repository, which
    is not necessarily this one. A run takes a few seconds to appear, so the
    lookup is retried until it does or `seconds` have passed.
    """
    deadline = time.time() + max(0, seconds)
    while True:
        listed = _capture(project_root,
                          ['gh', 'run', 'list', '--branch', run_branch,
                           '--limit', '1', '--json', 'databaseId'])
        try:
            rows = json.loads(listed or '[]')
        except ValueError:
            rows = []
        if rows and rows[0].get('databaseId'):
            return str(rows[0]['databaseId'])
        if time.time() >= deadline:
            return ''
        time.sleep(FIND_EVERY)


def _azure(project_root, branch, run_branch):
    # TODO(ado-remote): watch the Azure DevOps run and pull its records the way
    # the GitHub branch does. It needs the Azure CLI's pipelines extension and
    # an organisation to try it against, so it is a work-machine follow-up.
    url = _pipeline_url(project_root)
    print('Azure DevOps runs the pipeline for %s. Open it at:' % run_branch)
    print('  %s' % (url or '<the project\'s Pipelines list>'))
    print('When it finishes, run: git pull --ff-only %s %s'
          % (REMOTE, run_branch))
    print('Then delete the run branch: git push %s --delete %s'
          % (REMOTE, run_branch))
    return 0


def _push(project_root, run_branch):
    """Create the run branch on the remote from this commit.

    `HEAD:refs/heads/<run branch>` rather than a branch name, so nothing local
    is created and the working branch keeps its own upstream.
    """
    return _run(project_root,
                ['git', 'push', REMOTE, 'HEAD:refs/heads/%s' % run_branch])


def _delete(project_root, run_branch):
    """Remove the run branch from the remote once its records are here."""
    if _run(project_root, ['git', 'push', REMOTE, '--delete', run_branch]) != 0:
        print('The run branch %s is still on %s. Delete it with: git push %s '
              '--delete %s' % (run_branch, REMOTE, REMOTE, run_branch))


def _dirty(project_root):
    """True when the working tree carries a change no commit holds."""
    status = _capture(project_root, ['git', 'status', '--porcelain'])
    return bool((status or '').strip())


def _pipeline_url(project_root):
    remote = _capture(project_root, ['git', 'remote', 'get-url', REMOTE])
    remote = (remote or '').strip()
    if not remote:
        return ''
    if remote.startswith('git@ssh.dev.azure.com:'):
        return 'https://dev.azure.com/' + remote.split(':', 1)[-1].lstrip('v/')
    return remote


def _table(project_root):
    from purlin import status as status_module
    return status_module.sync_status(project_root)


def _host(project_root, args):
    named = getattr(args, 'host', None) if args is not None else None
    if named:
        return 'azure' if str(named).lower().startswith(('a', 'ado')) else 'github'
    remote = (_capture(project_root, ['git', 'remote', 'get-url', REMOTE])
              or '').lower()
    if 'dev.azure.com' in remote or 'visualstudio.com' in remote:
        return 'azure'
    return 'github'


def _branch(project_root):
    return (_capture(project_root,
                     ['git', 'rev-parse', '--abbrev-ref', 'HEAD']) or '').strip()


def _have(binary):
    for folder in (os.environ.get('PATH') or '').split(os.pathsep):
        if folder and os.path.isfile(os.path.join(folder, binary)):
            return True
    return False


def _run(project_root, argv):
    """Run one command in the project and answer its exit code."""
    try:
        return subprocess.run([*argv], cwd=project_root).returncode
    except (subprocess.SubprocessError, OSError) as error:
        print('%s failed: %s' % (argv[0], error))
        return 1


def _capture(project_root, argv):
    try:
        result = subprocess.run([*argv], cwd=project_root,
                                capture_output=True, text=True, timeout=30)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout if result.returncode == 0 else ''
