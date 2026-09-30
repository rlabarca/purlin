"""Render the runner file a project's git host runs.

One template per git host lives under `templates/`, and this fills in the
two things a project decides: which operating systems the matrix covers, and
which Purlin release the runner clones when the project is not this
repository.

The triggers are the same on both hosts: a push to a `run/*` branch and a
push of a `signed/*` tag. A push to any other branch starts nothing, and a
pull request starts nothing.

`wanted()` is what decides whether a project has a workflow at all. There
is one reason for one: a proof in `specs/` is tagged `@env` for an operating
system this machine is not, so only a runner can run its test. A project with
no such tag gets no file: at the gate `signed` `purlin:sign` writes the tag, a
person pushes it, and nothing runs remotely.

The matrix names the systems some proof in `specs/` is tagged `@env` for
that the machine writing the file is not, one job each and no other: setup
and the upgrade hand `render_workflow` those tags through `foreign_tags`. A
proof tagged `@env(windows)`, written from a Mac, adds a Windows job to prove
it. Nothing else about the workflow varies, so two projects with the same
tags, written from the same system, get the same file.

`prerequisites()` is what `purlin:init` asks before it writes any of this. A
workflow is a file, a remote that holds it and a host that runs it. Writing
the file where the remote or the host is missing leaves a project believing it
has a runner it has not got, so both are checked first and a missing one is
named with the command that fixes it. No branch is checked: the triggers name
the run branches and the signing tags, and a signature counts on whatever
commit carries it.
"""

import os
import shutil
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
ORDER = ('linux', 'macos', 'windows')


def workflow_filename(host):
    """The file name the workflow takes on one git host."""
    return TEMPLATES.get(_host(host), TEMPLATES['github'])


def workflow_path(host):
    """Where the runner file goes, relative to the project root.

    GitHub reads workflows under `.github/workflows/`; an Azure DevOps
    pipeline is created from a file at the root.
    """
    name = workflow_filename(host)
    if _host(host) == 'azure':
        return name
    return '.github/workflows/%s' % name


def runners_for(env_tags):
    """The runner images for a set of `@env` tags, in a fixed order.

    One image per operating system the tags name, in `ORDER`, and no other:
    `['windows']` gives `windows-latest` alone, and `['windows', 'linux']`
    gives `ubuntu-latest, windows-latest`.

    An unknown tag is ignored rather than guessed at: the vocabulary is
    windows, macos and linux and nothing else.
    """
    named = {str(tag).strip().lower() for tag in (env_tags or ()) if tag}
    return [RUNNERS[name] for name in ORDER if name in named]


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


def render_workflow(host, env_tags, purlin_ref):
    """The workflow text for one git host, matrix and release."""
    host = _host(host)
    with open(os.path.join(TEMPLATE_DIR, TEMPLATES[host]), 'r',
              encoding='utf-8') as handle:
        text = handle.read()
    text = text.replace('<<MATRIX>>', _matrix(host, runners_for(env_tags)))
    return text.replace('<<PURLIN_REF>>', str(purlin_ref or 'main'))


# The one reason a project has a workflow, in the words init prints it: one
# system, then two or more. `<System>` is `Windows`, `macOS` or `Linux/Unix`.
FOREIGN_OS_REASON = ('A proof in specs/ is tagged @env for %s, which this '
                     'machine is not, so only a runner can prove it.')
FOREIGN_OS_REASONS = ('Proofs in specs/ are tagged @env for %s, which this '
                      'machine is not, so only a runner can prove them.')
# The same at the gate `passed`, whose words are rules and tests.
FOREIGN_OS_REASON_AT_PASSED = ('A test is tagged @env for %s, which this '
                               'machine is not, so only a runner can run it.')
FOREIGN_OS_REASONS_AT_PASSED = ('Tests are tagged @env for %s, which this '
                                'machine is not, so only a runner can run '
                                'them.')
NO_REASON = ('every proof runs on this operating system, so nothing has to '
             'run remotely')
# The same at the gate `passed`, whose words are rules and tests.
NO_REASON_AT_PASSED = ('every test runs on this operating system, so nothing '
                       'has to run remotely')


def no_reason(gate):
    """Why a project needs no runner, in the words its gate uses."""
    return NO_REASON_AT_PASSED if gate == 'passed' else NO_REASON


def foreign_reason(gate, count=1):
    """The operating-system reason in the words the gate uses, for `count`
    systems: the singular for one, the plural for two or more."""
    if gate == 'passed':
        return (FOREIGN_OS_REASON_AT_PASSED if count == 1
                else FOREIGN_OS_REASONS_AT_PASSED)
    return FOREIGN_OS_REASON if count == 1 else FOREIGN_OS_REASONS


def systems_words(tags):
    """The systems `tags` name, as a person reads them.

    `Linux/Unix`, `macOS`, `Windows`, in that order, the last joined with
    ` and ` and the others with `, `: `macOS and Windows`. A tag that names
    none of the three is kept as it is written.
    """
    named = {str(tag).strip().lower() for tag in (tags or ()) if tag}
    words = [_os_word(name) for name in ORDER if name in named]
    words += sorted(name for name in named if name not in ORDER)
    if len(words) < 2:
        return ''.join(words)
    return '%s and %s' % (', '.join(words[:-1]), words[-1])


def _os_word(name):
    import sys
    mcp = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
    if mcp not in sys.path:
        sys.path.insert(0, mcp)
    from purlin import evidence as evidence_reader
    return evidence_reader.os_word(name)


def foreign_tags(env_tags, host_os):
    """The `@env` tags, lower-cased and sorted, that name a system other than
    `host_os`, the machine running setup or the upgrade."""
    return sorted({str(tag).strip().lower() for tag in (env_tags or ())
                   if str(tag).strip().lower()
                   and str(tag).strip().lower() != str(host_os or '')})


def wanted(env_tags, host_os, gate=None):
    """`(write one, the reasons)` for a project's workflow, in the gate's words.

    One reason and no other: a proof tagged `@env` for another operating
    system cannot be proven here. A project with none gets no workflow at
    all.
    """
    reasons = []
    foreign = foreign_tags(env_tags, host_os)
    if foreign:
        reasons.append(foreign_reason(gate, len(foreign))
                       % systems_words(foreign))
    return bool(reasons), reasons


def _host(host):
    name = str(host or 'github').strip().lower()
    if name == 'azure':
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


# ---------------------------------------------------------------------------
# What has to be true before a workflow is worth writing
# ---------------------------------------------------------------------------

REMOTE = 'origin'

NO_REMOTE = ('No git remote, so there is no runner to read this workflow. '
             'Add one with: git remote add %s <url>' % REMOTE)
UNKNOWN_HOST = 'This git host cannot run tests remotely. Everything on this machine works.'
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


def prerequisites(project_root):
    """`(ok, host, lines)`: what a workflow needs, checked before it is written.

    Two checks can fail, the remote and the host, and the first failure is
    the one reported. Nothing else is checked. The host CLI is reported
    either way, because a missing one costs a remote run its watch and
    nothing else.
    """
    if not _capture(project_root, ['remote']).strip():
        return False, None, [NO_REMOTE]
    host = host_of(project_root)
    if host is None:
        return False, None, [UNKNOWN_HOST]
    cli = _HOST_CLI[host]
    line = (CLI_PRESENT if _which(cli) else CLI_ABSENT) % cli
    return True, host, [line]


def _which(binary):
    """True when `binary` is a program on the search path.

    `shutil.which` honours `PATHEXT` on Windows, so `gh.exe` and `gh.cmd` are
    found, and asks for the exec bit elsewhere.
    """
    return shutil.which(binary) is not None


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
