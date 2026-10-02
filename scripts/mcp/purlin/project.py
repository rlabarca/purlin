"""The project's name, and whether a folder is a project a tool may answer for.

The name is read from the project's own files each time. Nothing writes it:
the settings file holds Purlin's version and the test commands alone, so a
renamed project reads its new name on the next status.

`refusal` is the one check the server and the status and drift scripts make
before they answer: a folder with no `.purlin/config.json` is no project, and
Purlin's own folder is not the project of a session working anywhere else.
"""

import glob
import json
import os
import re
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from config_engine import config_problem

NO_PROJECT_HERE = ('No Purlin project root at %s: .purlin/config.json is not there. '
                   'Run purlin:init.')
PLUGIN_FOLDER = ("%s is Purlin's own folder, not your project. Pass the top folder of "
                 "the git checkout you are working in.")


def plugin_root():
    """Purlin's own folder: the one holding `scripts/`, by real path."""
    return os.path.realpath(os.path.dirname(os.path.dirname(_MCP_DIR)))


def _within(path, folder):
    """True where the real path `path` is `folder` or under it."""
    try:
        return os.path.commonpath([path, folder]) == folder
    except ValueError:      # two drives on Windows
        return False


def _git_common_dir(folder):
    """The real path of the git folder `folder`'s checkout shares, or None."""
    try:
        result = subprocess.run(['git', 'rev-parse', '--git-common-dir'],
                                capture_output=True, text=True, cwd=folder,
                                timeout=15)
    except (subprocess.SubprocessError, OSError):
        return None
    found = result.stdout.strip() if result.returncode == 0 else ''
    return os.path.realpath(os.path.join(folder, found)) if found else None


def same_repository(a, b):
    """True where the folders `a` and `b` are in checkouts of one repository:
    both answer the same `git rev-parse --git-common-dir`."""
    one = _git_common_dir(a)
    return one is not None and one == _git_common_dir(b)


def refusal(project_root, started_in):
    """The one line to answer in place of the work, or None. PLUGIN_FOLDER where
    `project_root` is `plugin_root()` or under it, unless `started_in` is that
    folder, under it, or `same_repository(started_in, plugin_root())`; then
    NO_PROJECT_HERE where it holds no `.purlin/config.json`; then
    `config_engine.config_problem`'s sentence. Paths are compared by real path."""
    own = plugin_root()
    if _within(os.path.realpath(project_root), own):
        started = os.path.realpath(started_in)
        if not (_within(started, own) or same_repository(started, own)):
            return PLUGIN_FOLDER % project_root
    if not os.path.isfile(os.path.join(project_root, '.purlin', 'config.json')):
        return NO_PROJECT_HERE % project_root
    return config_problem(project_root)


_SECTION_RE = re.compile(r'^\s*\[([^\[\]]+)\]\s*(?:#.*)?$')
_NAME_RE = re.compile(r'''^\s*name\s*=\s*(?:"([^"]*)"|'([^']*)')\s*(?:#.*)?$''')


def project_name(project_root):
    """The project's name, read each time and never written. The first found of: `name`
    under `[project]`, then under `[tool.poetry]`, in pyproject.toml; `name` in
    package.json; the first root `*.csproj` file's name without `.csproj`; the last
    segment of `git remote get-url origin` without `.git`; the folder's name."""
    names = _pyproject_names(project_root)
    for section in ('project', 'tool.poetry'):
        if names.get(section):
            return names[section]
    for found in (_package_json_name(project_root), _csproj_name(project_root),
                  _origin_name(project_root)):
        if found:
            return found
    return os.path.basename(os.path.abspath(project_root))


def _read(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None


def _pyproject_names(project_root):
    """`{section: name}` for the `name` keys of pyproject.toml's sections."""
    text = _read(os.path.join(project_root, 'pyproject.toml'))
    names = {}
    section = None
    for line in (text or '').splitlines():
        header = _SECTION_RE.match(line)
        if header:
            section = header.group(1).strip()
            continue
        found = _NAME_RE.match(line)
        if found and section and section not in names:
            value = found.group(1) if found.group(1) is not None else found.group(2)
            if value.strip():
                names[section] = value.strip()
    return names


def _package_json_name(project_root):
    text = _read(os.path.join(project_root, 'package.json'))
    if not text:
        return None
    try:
        data = json.loads(text)
    except ValueError:
        return None
    name = data.get('name') if isinstance(data, dict) else None
    return name.strip() if isinstance(name, str) and name.strip() else None


def _csproj_name(project_root):
    found = sorted(glob.glob(os.path.join(glob.escape(project_root), '*.csproj')))
    return os.path.basename(found[0])[:-len('.csproj')] if found else None


def _origin_name(project_root):
    try:
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'],
                                capture_output=True, text=True, cwd=project_root,
                                timeout=15)
    except (subprocess.SubprocessError, OSError):
        return None
    url = result.stdout.strip() if result.returncode == 0 else ''
    segment = re.split(r'[/:\\]', url.rstrip('/'))[-1] if url else ''
    if segment.endswith('.git'):
        segment = segment[:-len('.git')]
    return segment or None
