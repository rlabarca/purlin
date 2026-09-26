"""`purlin:audit --remote`: let CI do the run and bring its records back.

A proof tagged `@env(windows)` cannot be proven on a Mac. Rather than ask
anyone to own a second machine, `--remote` hands the commit to the git host's
runner and brings back what that runner wrote. The evidence is the git host's,
because the commit is the git host's.

**This is the one push Purlin makes.** Everywhere else a push is a person's
act: a developer's record commit prints `git push` and stops. Here the push is
the point of the command, and it goes to a branch of its own,
`run/<branch>-<sha7>`, which this module creates, waits on, pulls back from
and deletes. The working branch is never pushed, so nothing reaches a pull
request that a person did not send there, and the pre-push hook is told this
is the sanctioned push through `PURLIN_REMOTE_RUN=1`.

A detached head has no branch to name and a dirty tree would run the workflow
against something other than what is on disk, so both are refused before
anything is pushed.

On GitHub the wait is `gh run watch`. On Azure DevOps the pipeline URL is
printed and the command returns: watching an Azure DevOps run needs the Azure
CLI's pipelines extension, which is the work-machine follow-up marked below.
"""

import os
import subprocess
import sys

_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(_RUN_DIR))
_MCP_DIR = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

WORKFLOW = 'purlin.yml'
REMOTE = 'origin'
RUN_BRANCH_PREFIX = 'run/'
# What marks the one push Purlin makes, so the pre-push hook lets it through.
REMOTE_RUN_VARIABLE = 'PURLIN_REMOTE_RUN'


def run_branch_name(project_root, branch):
    """The branch one remote run lives on: `run/<branch>-<sha7>`.

    The commit's own short sha is in the name, so two runs of the same branch
    never share a branch and a run left behind is readable for what it was.
    """
    sha = (_capture(project_root, ['git', 'rev-parse', 'HEAD']) or '').strip()
    return '%s%s-%s' % (RUN_BRANCH_PREFIX, branch, sha[:7])


def run_remote(project_root, args=None):
    """Push a run branch, wait for CI, pull it back, delete it. Exit code."""
    host = _host(project_root, args)
    branch = _branch(project_root)
    if not branch or branch == 'HEAD':
        print('This checkout is not on a branch, so there is nothing to push.')
        return 1
    if _dirty(project_root):
        print('This checkout has changes that are not committed, so a run '
              'would prove something other than what is here. Commit them, '
              'then run purlin:audit --remote again.')
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
    watched = _run(project_root, ['gh', 'run', 'watch', '--exit-status'])
    if watched != 0:
        print('The run finished red. The table below is what came back.')
    # The run branch is this branch plus the record commit, so a fast-forward
    # is the whole of it: the records land here as the one commit CI made.
    _run(project_root, ['git', 'pull', '--ff-only', REMOTE, run_branch])
    _delete(project_root, run_branch)
    print(_table(project_root))
    return watched


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
                ['git', 'push', REMOTE, 'HEAD:refs/heads/%s' % run_branch],
                marked=True)


def _delete(project_root, run_branch):
    """Remove the run branch from the remote once its records are here."""
    if _run(project_root, ['git', 'push', REMOTE, '--delete', run_branch],
            marked=True) != 0:
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


def _run(project_root, argv, marked=False):
    """Run one command. `marked` sets the variable the pre-push hook reads."""
    env = None
    if marked:
        env = dict(os.environ)
        env[REMOTE_RUN_VARIABLE] = '1'
    try:
        return subprocess.run([*argv], cwd=project_root, env=env).returncode
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
