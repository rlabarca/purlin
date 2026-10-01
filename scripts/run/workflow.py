"""Render the runner file a project's git host runs.

One template per git host lives under `templates/`, and this fills in the
two things a project decides: which operating systems the matrix covers, and
which Purlin release the runner clones when the project is not this
repository.

The trigger is the same on both hosts: a push to a `run/*` branch, and
nothing else. A push to any other branch starts nothing, a tag starts
nothing, and a pull request starts nothing.

The file is written on first need: the first `purlin:test --remote` in a
project with no runner file for its remote's git host writes it
(`remote.ensure_runner`). The matrix names the systems some proof in
`specs/` is tagged `@env` for that the machine writing the file is not, one
job each and no other (`foreign_tags`). A proof tagged `@env(windows)`,
written from a Mac, adds a Windows job to prove it. Nothing else about the
file varies, so two projects with the same tags, written from the same
system, get the same file.

The git host is read from `origin` each time it is asked (`host_of`); no
setting holds it.
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

# The git host as a person reads its name.
HOST_WORDS = {
    'github': 'GitHub',
    'azure': 'Azure DevOps',
}

# The runner image for each operating system `@env` names.
RUNNERS = {
    'linux': 'ubuntu-latest',
    'macos': 'macos-latest',
    'windows': 'windows-latest',
}
ORDER = ('linux', 'macos', 'windows')

REMOTE = 'origin'


def workflow_filename(host):
    """The file name the runner file takes on one git host."""
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


def host_word(host):
    """`GitHub` or `Azure DevOps`."""
    return HOST_WORDS[_host(host)]


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
    """The runner file's text for one git host, matrix and release."""
    host = _host(host)
    with open(os.path.join(TEMPLATE_DIR, TEMPLATES[host]), 'r', encoding='utf-8') as handle:
        text = handle.read()
    text = text.replace('<<MATRIX>>', _matrix(host, runners_for(env_tags)))
    return text.replace('<<PURLIN_REF>>', str(purlin_ref or 'main'))


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
    `host_os`, the machine writing the runner file."""
    return sorted({str(tag).strip().lower() for tag in (env_tags or ())
                   if str(tag).strip().lower()
                   and str(tag).strip().lower() != str(host_os or '')})


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
# The git host, read from the remote
# ---------------------------------------------------------------------------

def host_of(project_root):
    """`github`, `azure` or None, read from `origin`'s URL each time."""
    url = _capture(project_root, ['remote', 'get-url', REMOTE]).lower()
    if 'github' in url:
        return 'github'
    if 'dev.azure.com' in url or 'visualstudio.com' in url:
        return 'azure'
    return None


def _capture(project_root, args):
    """One git command's stdout, or an empty string when it could not run.

    The command can ask nothing: its input is closed, `GIT_TERMINAL_PROMPT=0`
    makes git fail rather than ask for a password, and
    `AZURE_EXTENSION_USE_DYNAMIC_INSTALL=no` is the same environment every
    other process `purlin:test --remote` starts runs with.
    """
    environment = dict(os.environ)
    environment['GIT_TERMINAL_PROMPT'] = '0'
    environment['AZURE_EXTENSION_USE_DYNAMIC_INSTALL'] = 'no'
    try:
        done = subprocess.run(['git'] + list(args), cwd=project_root,
                              stdin=subprocess.DEVNULL, capture_output=True,
                              text=True, timeout=20, env=environment)
    except (OSError, subprocess.SubprocessError):
        return ''
    return done.stdout if done.returncode == 0 else ''
