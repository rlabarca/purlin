"""`purlin:verify --remote`: let CI do the run and bring its records back.

A proof tagged `@env(windows)` cannot be proven on a Mac. Rather than ask
anyone to own a second machine, `--remote` pushes the branch, waits for the
workflow the git host already runs, pulls the records that run committed, and
prints the same table `purlin:status` prints. The evidence is the git host's,
because the commit is the git host's.

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


def run_remote(project_root, args=None):
    """Push, wait for CI, pull what it committed, print the table. Exit code."""
    host = _host(project_root, args)
    branch = _branch(project_root)
    if not branch or branch == 'HEAD':
        print('This checkout is not on a branch, so there is nothing to push.')
        return 1

    print('Pushing %s.' % branch)
    if _run(project_root, ['git', 'push', '-u', 'origin', branch]) != 0:
        print('The push failed, so no run was started.')
        return 1

    if host == 'azure':
        return _azure(project_root, branch)
    return _github(project_root, branch)


def _github(project_root, branch):
    if not _have('gh'):
        print('GitHub CLI `gh` is not installed, so the run cannot be '
              'watched. Open the run on the pull request instead.')
        return 1
    print('Waiting for the %s workflow on %s.' % (WORKFLOW, branch))
    watched = _run(project_root, ['gh', 'run', 'watch', '--exit-status'])
    if watched != 0:
        print('The run finished red. The table below is what came back.')
    _run(project_root, ['git', 'pull', '--ff-only'])
    print(_table(project_root))
    return watched


def _azure(project_root, branch):
    # TODO(ado-remote): watch the Azure DevOps run and pull its records the way
    # the GitHub branch does. It needs the Azure CLI's pipelines extension and
    # an organisation to try it against, so it is a work-machine follow-up.
    url = _pipeline_url(project_root)
    print('Azure DevOps runs the pipeline for %s. Open it at:' % branch)
    print('  %s' % (url or '<the project\'s Pipelines list>'))
    print('When it finishes, run: git pull --ff-only')
    return 0


def _pipeline_url(project_root):
    remote = _capture(project_root, ['git', 'remote', 'get-url', 'origin'])
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
    remote = (_capture(project_root, ['git', 'remote', 'get-url', 'origin'])
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
    try:
        return subprocess.run(argv, cwd=project_root).returncode
    except (subprocess.SubprocessError, OSError) as error:
        print('%s failed: %s' % (argv[0], error))
        return 1


def _capture(project_root, argv):
    try:
        result = subprocess.run(argv, cwd=project_root, capture_output=True,
                                text=True, timeout=30)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout if result.returncode == 0 else ''
