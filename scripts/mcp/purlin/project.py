"""The project's name, read from the project's own files each time.

Nothing writes it: the settings file holds Purlin's version and the test
commands alone, so a renamed project reads its new name on the next status.
"""

import glob
import json
import os
import re
import subprocess

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
