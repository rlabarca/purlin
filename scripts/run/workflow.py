"""Render the CI workflow a project's git host runs.

One template per git host lives under `templates/`, and this fills in the two
things a project decides: which operating systems the matrix covers, and which
Purlin release the runner clones when the project is not this repository.

The matrix comes from the `@env` tags in `specs/`. A proof tagged
`@env(windows)` needs a Windows job to prove it; a project that tags nothing
runs on Linux alone. Nothing else about the workflow varies, so two projects
with the same tags get the same file.

The scheduled job that reports an anchor pin behind its source is optional:
the template carries it between `# BEGIN upstream-check` and
`# END upstream-check` markers, and `upstream_check=False` drops those lines
along with what they wrap.
"""

import os

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

BEGIN = '# BEGIN upstream-check'
END = '# END upstream-check'


def workflow_filename(host):
    """The file name the workflow takes on one git host."""
    return TEMPLATES.get(_host(host), TEMPLATES['github'])


def runners_for(env_tags):
    """The runner images for a set of `@env` tags, in a fixed order.

    An unknown tag is ignored rather than guessed at: the vocabulary is
    windows, macos and linux and nothing else, and a project that names
    something else still gets a workflow that runs.
    """
    named = {str(tag).strip().lower() for tag in (env_tags or ()) if tag}
    images = [RUNNERS[name] for name in ORDER if name in named]
    return images or [DEFAULT_RUNNER]


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


def render_workflow(host, env_tags, purlin_ref, upstream_check=False):
    """The workflow text for one git host, matrix and Purlin release."""
    host = _host(host)
    with open(os.path.join(TEMPLATE_DIR, TEMPLATES[host]), 'r',
              encoding='utf-8') as handle:
        text = handle.read()
    text = _upstream(text, upstream_check)
    text = text.replace('<<MATRIX>>', _matrix(host, runners_for(env_tags)))
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
