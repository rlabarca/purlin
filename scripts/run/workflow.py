"""Render the CI workflow a project's git host runs.

One template per git host lives under `templates/`, and this fills in the
three things a project decides: which operating systems the matrix covers,
which Purlin release the runner clones when the project is not this
repository, and which branch is the protected one a push starts a run on.

The triggers are the same on both hosts: a pull request, a push to the
protected branch, and a push to a `run/*` branch. A push to any other branch
starts nothing. `main` stands in when the project's default branch cannot be
read, which is the name a repository made this decade carries.

The matrix always carries Linux, then the operating systems the `@env` tags in
`specs/` name. A proof tagged `@env(windows)` adds a Windows job to prove it;
an untagged proof is satisfied by any operating system, so the Linux job proves
those and writes the record that counts. A project that tags nothing runs on
Linux alone. Nothing else about the workflow varies, so two projects with the
same tags get the same file.

The scheduled job that reports an anchor pin behind its source is optional:
the template carries it between `# BEGIN upstream-check` and
`# END upstream-check` markers, and `upstream_check=False` drops those lines
along with what they wrap.

`prerequisites()` is what `purlin:init` asks before it writes any of this. A
workflow is three things at once: a file, a remote that holds it, and a branch
the triggers name. Writing the file where the other two are missing leaves a
project believing it has a runner it has not got, so each is checked first and
a missing one is named with the command that fixes it.
"""

import os
import subprocess

_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(_RUN_DIR))
TEMPLATE_DIR = os.path.join(PLUGIN_ROOT, 'templates')

TEMPLATES = {
    'github': 'purlin.yml',
    'azure': 'purlin.azure-pipelines.yml',
}

# The runner image for each operating system `@env` names.
RUNNERS = {
    'linux': 'ubuntu-latest',
    'macos': 'macos-latest',
    'windows': 'windows-latest',
}
DEFAULT_RUNNER = 'ubuntu-latest'
ORDER = ('linux', 'macos', 'windows')

# The branch a push starts a run on when the project's own cannot be read.
DEFAULT_PROTECTED = 'main'

BEGIN = '# BEGIN upstream-check'
END = '# END upstream-check'


def workflow_filename(host):
    """The file name the workflow takes on one git host."""
    return TEMPLATES.get(_host(host), TEMPLATES['github'])


def runners_for(env_tags):
    """The runner images for a set of `@env` tags, in a fixed order.

    Linux always comes first, tagged or not: an untagged proof is satisfied by
    any operating system, and the job that proves every untagged proof and
    writes the record that counts has to exist. The tagged operating systems
    follow in `ORDER`, deduplicated, so `['windows']` gives
    `ubuntu-latest, windows-latest` and `['linux']` gives `ubuntu-latest` once.

    An unknown tag is ignored rather than guessed at: the vocabulary is
    windows, macos and linux and nothing else, and a project that names
    something else still gets a workflow that runs.
    """
    named = {str(tag).strip().lower() for tag in (env_tags or ()) if tag}
    images = [DEFAULT_RUNNER]
    for name in ORDER:
        if name in named and RUNNERS[name] not in images:
            images.append(RUNNERS[name])
    return images


def env_tags_in_specs(project_root):
    """Every operating system the `@env` tags under `specs/` name."""
    import sys
    mcp = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
    if mcp not in sys.path:
        sys.path.insert(0, mcp)
    from purlin import specs as specs_module

    found = set()
    for info in specs_module.scan_specs(project_root).values():
        for env in (info.get('proof_env') or {}).values():
            if env:
                found.add(env)
    return sorted(found)


def render_workflow(host, env_tags, purlin_ref, upstream_check=False,
                    protected=DEFAULT_PROTECTED):
    """The workflow text for one git host, matrix, release and branch."""
    host = _host(host)
    with open(os.path.join(TEMPLATE_DIR, TEMPLATES[host]), 'r',
              encoding='utf-8') as handle:
        text = handle.read()
    text = _upstream(text, upstream_check)
    text = text.replace('<<MATRIX>>', _matrix(host, runners_for(env_tags)))
    text = text.replace('<<PROTECTED>>',
                        str(protected or DEFAULT_PROTECTED).strip()
                        or DEFAULT_PROTECTED)
    return text.replace('<<PURLIN_REF>>', str(purlin_ref or 'main'))


def _host(host):
    name = str(host or 'github').strip().lower()
    if name in ('azure', 'ado', 'azure devops', 'azure-devops'):
        return 'azure'
    return 'github'


def _matrix(host, images):
    """The matrix body: a flow list on GitHub, one named entry on Azure DevOps."""
    if host == 'github':
        return ', '.join(images)
    lines = []
    for image in images:
        lines.append('        %s:' % image.split('-')[0])
        lines.append('          imageName: %s' % image)
    return '\n'.join(lines)


def _upstream(text, keep):
    """Unwrap the upstream-check blocks, or drop them with what they wrap."""
    out = []
    inside = False
    for line in text.splitlines(True):
        stripped = line.strip()
        if stripped == BEGIN:
            inside = True
            continue
        if stripped == END:
            inside = False
            continue
        if inside and not keep:
            continue
        out.append(line)
    return ''.join(out)


# ---------------------------------------------------------------------------
# What has to be true before a workflow is worth writing
# ---------------------------------------------------------------------------

REMOTE = 'origin'

NO_REMOTE = ('No git remote, so there is no runner to read this workflow. '
             'Add one with: git remote add %s <url>' % REMOTE)
UNKNOWN_HOST = ('The %s remote is neither GitHub nor Azure DevOps, and those '
                'are the two hosts this release writes a workflow for.'
                % REMOTE)
NO_BRANCH = ('The branch %s is not on %s yet, so the workflow would trigger '
             'on a branch that is not there. Push it with: git push -u %s %s')
UNREACHABLE = ('%s could not be reached, so whether %s is on it was not '
               'checked. The workflow names that branch either way.')
CLI_PRESENT = '%s is installed, so a remote run can be watched from here.'
CLI_ABSENT = ('%s is not installed, so purlin:test --remote cannot watch a '
              'run. Install it, or open the run on the git host instead.')

_HOST_CLI = {'github': 'gh', 'azure': 'az'}


def host_of(project_root):
    """`github`, `azure` or None, read from the remote URL."""
    url = _capture(project_root, ['remote', 'get-url', REMOTE]).lower()
    if 'github' in url:
        return 'github'
    if 'dev.azure.com' in url or 'visualstudio.com' in url:
        return 'azure'
    return None


def prerequisites(project_root, protected=None):
    """`(ok, host, lines)`: what a workflow needs, checked before it is written.

    The three checks that can fail are the remote, the host and the protected
    branch, and the first failure is the one reported: naming a branch on a
    remote that is not there would say nothing useful. The host CLI is
    reported either way, because a missing one costs a remote run its watch
    and nothing else.
    """
    if not _capture(project_root, ['remote']).strip():
        return False, None, [NO_REMOTE]
    host = host_of(project_root)
    if host is None:
        return False, None, [UNKNOWN_HOST]
    lines = []
    branch = protected or DEFAULT_PROTECTED
    # A remote that answers settles the question. One that cannot be reached
    # at all, which is every offline machine, is not an answer either way, so
    # it is reported and the workflow is written: refusing there would make a
    # network the price of setting a project up.
    reached, heads = _ask(project_root, ['ls-remote', '--heads', REMOTE,
                                         branch])
    if not reached:
        lines.append(UNREACHABLE % (REMOTE, branch))
    elif not heads.strip():
        return False, host, [NO_BRANCH % (branch, REMOTE, REMOTE, branch)]
    cli = _HOST_CLI[host]
    lines.append((CLI_PRESENT if _which(cli) else CLI_ABSENT) % cli)
    return True, host, lines


def _which(binary):
    for folder in (os.environ.get('PATH') or '').split(os.pathsep):
        if folder and os.path.isfile(os.path.join(folder, binary)):
            return True
    return False


def _capture(project_root, args):
    """One git command's stdout, or an empty string when it could not run."""
    return _ask(project_root, args)[1]


def _ask(project_root, args):
    """`(the command worked, its stdout)` for one git command.

    `GIT_TERMINAL_PROMPT=0` makes git fail rather than ask for a password: a
    remote nobody here can read is a question with no answer, and the whole
    point of the check is that it finishes.
    """
    environment = dict(os.environ)
    environment['GIT_TERMINAL_PROMPT'] = '0'
    try:
        done = subprocess.run(['git'] + list(args), cwd=project_root,
                              capture_output=True, text=True, timeout=20,
                              env=environment)
    except (OSError, subprocess.SubprocessError):
        return False, ''
    return done.returncode == 0, done.stdout
