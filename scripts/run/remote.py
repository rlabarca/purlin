"""`purlin:test --remote`: let the git host's runner do the run.

A proof tagged `@env(windows)` cannot be proven on a Mac. Rather than ask
anyone to own a second machine, `--remote` hands the commit to the git host's
runner and brings back what that runner wrote. The evidence is the git host's,
because the commit is the git host's.

What comes back is what the runner committed on the run branch: its own
operating system's section of `.purlin/evidence/ci/<feature>.json`, at every
gate. The run pulls that commit onto this branch, so a proof tagged `@env`
for an operating system nobody here has ends up with its own platform's pass
in the tree.

**This is the one push Purlin makes.** Everywhere else a push is a person's
act. Here the push is the point of the command, and it goes to a branch of
its own, `run/<branch>-<sha7>`, which this module creates, waits on, pulls
back from and deletes. The working branch is never pushed, so nothing reaches
the git host that a person did not send there.

A detached head has no branch to name and a dirty tree would run the workflow
against something other than what is on disk, so both are refused before
anything is pushed.

On both git hosts the run is found by the branch it was started for, retried
while the run registers, which takes a few seconds, and then that one run is
waited on. On GitHub `gh run watch <id>` waits; the id is named because `gh
run watch` with no id prompts for one and errors where there is no terminal.
On Azure DevOps the Azure CLI's
`azure-devops` extension finds the run and `az pipelines runs show` is asked
for its status until it completes. Either way the run ends the same: pull the
runner's commit, delete the run branch, print the table.

No process started here asks for anything: stdin is closed, git is told not
to prompt for a credential, and the Azure CLI is told not to offer to install
its extension. A missing credential is a failed command, not a question.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.parse

_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(_RUN_DIR))
_MCP_DIR = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

WORKFLOW = 'purlin.yml'
REMOTE = 'origin'
RUN_BRANCH_PREFIX = 'run/'

# The `ci` setting of a project with no supported git host, and the one line
# `--remote` prints there.
NO_CI = 'none'
CI_NONE = ('purlin:test --remote needs a GitHub or Azure DevOps remote, and '
           '.purlin/config.json says ci: none. Add one with git remote add '
           'origin <url>, then run purlin:init.')
NOT_ON_A_BRANCH = ('This checkout is not on a branch, so there is nothing to '
                   'push. Make one with git switch -c <name>, then run '
                   'purlin:test --remote again.')
PUSH_FAILED = ('The push failed, so no run was started. Check that git push '
               'origin works from this checkout, then run purlin:test --remote '
               'again.')

# The program each git host's run is waited on with, and the line printed
# before any push where it is missing: without it the run branch would be
# left on the git host with nobody waiting for it.
PROGRAM = {'github': 'gh', 'azure': 'az'}
NO_PROGRAM = {
    'github': ('purlin:test --remote waits for the run with the GitHub CLI, '
               'gh, which is not installed, so nothing was pushed. Install gh, '
               'then run purlin:test --remote again.'),
    'azure': ('purlin:test --remote waits for the run with the Azure CLI, az, '
              'which is not installed, so nothing was pushed. Install az with '
              'its azure-devops extension, then run purlin:test --remote '
              'again.'),
}

# How long to keep asking the git host which run this push started. A run
# takes a few seconds to register, and asking once would miss it; a minute is
# far longer than any host takes and short enough to fail while a person is
# still watching.
FIND_SECONDS = 60
FIND_EVERY = 3
NO_RUN_FOUND = ('No run registered for %s within %d seconds, so the run '
                'branch was deleted and nothing came back. Check that the git '
                'host runs %s on a push to run/*, then run purlin:test '
                '--remote again.')

# How long to wait for an Azure DevOps run once it is found, and how often to
# ask. A run of the whole suite on a hosted agent takes minutes; ninety of
# them is the limit past which the command stops waiting and says how to
# finish by hand.
POLL_SECONDS = 90 * 60
POLL_EVERY = 15
# The results `az pipelines runs show` reports for a completed run. Only
# `succeeded` is green.
GREEN = 'succeeded'
# How long one git or az command may take before it is abandoned.
COMMAND_SECONDS = 300

NO_AZURE_REMOTE = ('The remote %s is not an Azure DevOps repository URL, so '
                   'nothing was pushed: set %s to the URL Azure DevOps shows '
                   'under Clone and run purlin:test --remote again.')
NO_AZURE_RUN = ('No run registered for %s within %d seconds, so the run '
                'branch was deleted and nothing came back. Check that az has '
                'the azure-devops extension and is signed in, then run '
                'purlin:test --remote again.')
FAILED_ON_HOST = ('The run failed on the git host. The table below is what '
                  'came back.')
AZURE_TIMEOUT = ('Run %s on %s has not completed after %d minutes: open it at '
                 '%s and when it finishes run: git pull --ff-only %s %s, then '
                 'git push %s --delete %s')


def run_branch_name(project_root, branch):
    """The branch one remote run lives on: `run/<branch>-<sha7>`.

    The commit's own short sha is in the name, so two runs of the same branch
    never share a branch and a run left behind is readable for what it was.
    """
    sha = (_capture(project_root, ['git', 'rev-parse', 'HEAD']) or '').strip()
    return '%s%s-%s' % (RUN_BRANCH_PREFIX, branch, sha[:7])


def run_remote(project_root, args=None, cfg=None):
    """Push a run branch, wait for CI, pull it back, delete it. Exit code.

    A project whose settings file cannot be read, or whose settings say
    `ci: none`, pushes nothing: the first prints why the file cannot be read,
    the second that no git host here runs a workflow. Neither does a project
    whose git host's program, `gh` or `az`, is not on the search path: the
    run could not be waited on, so the check comes before the push.
    """
    from config_engine import config_problem, resolve_config
    problem = config_problem(project_root)
    if problem:
        print(problem)
        return 1
    if resolve_config(project_root).get('ci') == NO_CI:
        print(CI_NONE)
        return 1
    host = _host(project_root)
    branch = _branch(project_root)
    if not branch or branch == 'HEAD':
        print(NOT_ON_A_BRANCH)
        return 1
    if _dirty(project_root):
        print('This checkout has changes that are not committed, so a run '
              'would prove something other than what is here. Commit them, '
              'then run purlin:test --remote again.')
        return 1

    run_branch = run_branch_name(project_root, branch)
    where = None
    if host == 'azure':
        # Read before the push, so a remote in no Azure DevOps form leaves
        # nothing behind on it.
        remote = _remote_url(project_root)
        where = parse_azure_remote(remote)
        if where is None:
            print(NO_AZURE_REMOTE % (remote or '(none)', REMOTE))
            return 1
    if not _have(PROGRAM[host]):
        print(NO_PROGRAM[host])
        return 1
    print('Pushing %s as %s.' % (branch, run_branch))
    if _push(project_root, run_branch) != 0:
        print(PUSH_FAILED)
        return 1

    if host == 'azure':
        return _azure(project_root, run_branch, where)
    return _github(project_root, run_branch)


def _github(project_root, run_branch):
    from workflow import workflow_path
    print('Waiting for the %s workflow on %s.' % (WORKFLOW, run_branch))
    run_id = find_run(project_root, run_branch)
    if not run_id:
        print(NO_RUN_FOUND % (run_branch, FIND_SECONDS,
                              workflow_path('github')))
        _delete(project_root, run_branch)
        return 1
    watched = _run(project_root,
                   ['gh', 'run', 'watch', run_id, '--exit-status'],
                   timeout=None)
    return _bring_back(project_root, run_branch, watched)


def _bring_back(project_root, run_branch, code):
    """Pull the runner's commit, delete the run branch, print the table.

    The same for both git hosts and for a green or a red run: a red run's
    results are evidence too. Answers `code`, the run's own exit code.
    """
    if code != 0:
        print(FAILED_ON_HOST)
    # The run branch is this branch plus the one commit the runner made, so a
    # fast-forward is the whole of it: that commit is the evidence under
    # `.purlin/evidence/ci/`.
    _run(project_root, ['git', 'pull', '--ff-only', REMOTE, run_branch])
    _delete(project_root, run_branch)
    print(_table(project_root))
    return code


def find_run(project_root, run_branch, seconds=FIND_SECONDS):
    """The id of the run this push started, or `''` when none registered.

    The run is looked up by the branch it was started for and by the
    workflow file, because `gh run watch` with no id prompts for one and
    errors where there is no terminal, and where it does choose it takes the
    newest run on the repository, which is not necessarily this one; and a
    project's other workflows may run on the same push, so the branch alone
    can name one of those. A run takes a few seconds to appear, so the
    lookup is retried until it does or `seconds` have passed.
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


def _azure(project_root, run_branch, where):
    """Find the Azure DevOps run on `run_branch`, wait for it, bring it back.

    `where` is `(organization, project, repository)` from the remote.
    """
    organization, project, _repository = where
    runs_url = _runs_url(organization, project)
    # Found before the push; the path is what is started, so `az.cmd` runs
    # on Windows.
    az = shutil.which('az') or 'az'
    print('Waiting for the Azure DevOps pipeline on %s.' % run_branch)
    run_id = find_azure_run(project_root, az, organization, project,
                            run_branch)
    if not run_id:
        print(NO_AZURE_RUN % (run_branch, FIND_SECONDS))
        _delete(project_root, run_branch)
        return 1
    result = wait_azure_run(project_root, az, organization, project, run_id)
    if result is None:
        # The run is still going and will commit onto the run branch, so the
        # branch stays for the person to pull and delete when it is done.
        print(AZURE_TIMEOUT % (run_id, run_branch, POLL_SECONDS // 60,
                               runs_url, REMOTE, run_branch, REMOTE,
                               run_branch))
        return 1
    print('Run %s completed: %s.' % (run_id, result))
    return _bring_back(project_root, run_branch, 0 if result == GREEN else 1)


def parse_azure_remote(url):
    """`(organization, project, repository)` from an Azure DevOps remote.

    Three forms: `https://dev.azure.com/<org>/<project>/_git/<repo>`,
    `git@ssh.dev.azure.com:v3/<org>/<project>/<repo>` and
    `https://<org>.visualstudio.com/<project>/_git/<repo>`. A user part
    before the host is ignored and percent-encoded characters are decoded,
    so `My%20Project` is the project `My Project`. Anything else is `None`.
    """
    url = (url or '').strip()
    if url.startswith('git@ssh.dev.azure.com:'):
        parts = url.split(':', 1)[1].strip('/').split('/')
        if len(parts) == 4 and parts[0] == 'v3':
            return _decoded(parts[1], parts[2], parts[3])
        return None
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ('https', 'http'):
        return None
    host = (parsed.hostname or '').lower()
    parts = [part for part in parsed.path.split('/') if part]
    if host == 'dev.azure.com':
        if len(parts) == 4 and parts[2] == '_git':
            return _decoded(parts[0], parts[1], parts[3])
        return None
    if host.endswith('.visualstudio.com'):
        organization = host[:-len('.visualstudio.com')]
        if organization and len(parts) == 3 and parts[1] == '_git':
            return _decoded(organization, parts[0], parts[2])
    return None


def _decoded(*parts):
    return tuple(urllib.parse.unquote(part) for part in parts)


def _organization_url(organization):
    return 'https://dev.azure.com/%s' % organization


def _runs_url(organization, project):
    return '%s/%s/_build' % (_organization_url(organization),
                             urllib.parse.quote(project))


def azure_list_command(az, organization, project, run_branch):
    """The `az` command that names the newest run on `run_branch`."""
    return [az, 'pipelines', 'runs', 'list',
            '--organization', _organization_url(organization),
            '--project', project,
            '--branch', 'refs/heads/%s' % run_branch,
            '--top', '1', '--query', '[0].id', '--output', 'tsv']


def azure_show_command(az, organization, project, run_id):
    """The `az` command that reports one run's status and result."""
    return [az, 'pipelines', 'runs', 'show', '--id', str(run_id),
            '--organization', _organization_url(organization),
            '--project', project,
            '--query', '[status,result]', '--output', 'tsv']


def find_azure_run(project_root, az, organization, project, run_branch,
                   seconds=None):
    """The id of the run this push started, or `''` when none registered.

    Asked every `FIND_EVERY` seconds for up to `FIND_SECONDS`, because a run
    takes a few seconds to appear after the push.
    """
    seconds = FIND_SECONDS if seconds is None else seconds
    deadline = time.time() + max(0, seconds)
    command = azure_list_command(az, organization, project, run_branch)
    while True:
        listed = (_capture(project_root, command) or '').strip()
        if listed and listed != 'None':
            return listed.split()[0]
        if time.time() >= deadline:
            return ''
        time.sleep(FIND_EVERY)


def wait_azure_run(project_root, az, organization, project, run_id):
    """The run's result once its status is `completed`, or `None` at the limit.

    Asked every `POLL_EVERY` seconds for up to `POLL_SECONDS`. An answer that
    cannot be read counts as not completed yet.
    """
    deadline = time.time() + max(0, POLL_SECONDS)
    command = azure_show_command(az, organization, project, run_id)
    while True:
        words = (_capture(project_root, command) or '').split()
        if words and words[0] == 'completed':
            return words[1] if len(words) > 1 else ''
        if time.time() >= deadline:
            return None
        time.sleep(POLL_EVERY)


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
        print('The run branch %s is still on %s. Delete it with: git push %s '
              '--delete %s' % (run_branch, REMOTE, REMOTE, run_branch))


def _dirty(project_root):
    """True when the working tree carries a change no commit holds."""
    status = _capture(project_root, ['git', 'status', '--porcelain'])
    return bool((status or '').strip())


def _remote_url(project_root):
    return (_capture(project_root, ['git', 'remote', 'get-url', REMOTE])
            or '').strip()


def _table(project_root):
    from purlin import status as status_module
    return status_module.sync_status(project_root)


def _host(project_root):
    remote = _remote_url(project_root).lower()
    if 'dev.azure.com' in remote or 'visualstudio.com' in remote:
        return 'azure'
    return 'github'


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
    fail rather than ask for one; `AZURE_EXTENSION_USE_DYNAMIC_INSTALL=no`
    makes `az` report a missing extension rather than offer to install it.
    """
    env = dict(os.environ)
    env['GIT_TERMINAL_PROMPT'] = '0'
    env['AZURE_EXTENSION_USE_DYNAMIC_INSTALL'] = 'no'
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
