"""Which test frameworks a project uses.

Detection answers all the matches, not the first: a project can carry pytest
for the server and jest for the client, and running only one of them calls a
suite that never ran green. Shell has no detection heuristic, so it is the
fallback that keeps a runner always present.

The six frameworks this release ships plugins for are pytest, vitest, jest,
xunit, sql and shell. C and PHP were dropped.
"""

import json
import os
import re
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

KNOWN_FRAMEWORKS = ('pytest', 'vitest', 'jest', 'xunit', 'sql', 'shell')

# Directory names detection never descends into: dot directories are tool
# state, and `node_modules` is other people's code, where a vendored package's
# own fixtures are not this project's frameworks.
_SKIP_DIRS = ('node_modules',)

# A SQL file counts as a test only when its name says so. `tests/fixtures.sql`
# is seed data, not a test.
_SQL_TEST_NAME = re.compile(r'^(?:test_.+\.sql|.+_test\.sql|.+\.test\.sql)$')

# An xUnit project is any `*.csproj` that references the xunit package.
_XUNIT_REF = re.compile(r'Include="xunit(?:\.|")', re.IGNORECASE)


def _read(root, rel):
    try:
        with open(os.path.join(root, rel), 'r', encoding='utf-8') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return ''


def _listdir(root, rel):
    try:
        return sorted(os.listdir(os.path.join(root, rel)))
    except OSError:
        return []


def _npm_package(root, name):
    """True when `package.json` declares `name` as a dependency.

    The dependency maps are parsed and the key looked up rather than the file
    searched: a vitest project whose description says "migrated off jest" is
    not a jest project. A `<name>.config.*` file beside the manifest counts as
    the same answer.
    """
    text = _read(root, 'package.json')
    if text:
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if isinstance(data, dict):
            for section in ('dependencies', 'devDependencies'):
                deps = data.get(section)
                if isinstance(deps, dict) and name in deps:
                    return True
    return any(n.startswith(name + '.config.') for n in _listdir(root, '.'))


def _walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith('.') and d not in _SKIP_DIRS)
        yield dirpath, filenames


def _has_xunit_csproj(root):
    for dirpath, filenames in _walk(root):
        for name in filenames:
            if not name.endswith('.csproj'):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding='utf-8') as handle:
                    text = handle.read()
            except (IOError, OSError, UnicodeDecodeError):
                continue
            if _XUNIT_REF.search(text):
                return True
    return False


_DETECTORS = (
    ('pytest', lambda root: (os.path.isfile(os.path.join(root, 'conftest.py'))
                             or '[tool.pytest' in _read(root, 'pyproject.toml'))),
    ('vitest', lambda root: _npm_package(root, 'vitest')),
    ('jest', lambda root: _npm_package(root, 'jest')),
    ('xunit', _has_xunit_csproj),
    ('sql', lambda root: any(_SQL_TEST_NAME.match(n)
                             for n in _listdir(root, 'tests'))),
)


def detect_frameworks(project_root):
    """Every framework detected under `project_root`, in registry order.

    Shell is the fallback when nothing else matches, so the answer is never
    empty and a caller always has a runner to name.
    """
    found = []
    for framework_id, test in _DETECTORS:
        try:
            if test(project_root):
                found.append(framework_id)
        except OSError:
            continue
    if not found:
        found.append('shell')
    return found


# What a tree must carry for a framework to be runnable at all, checked when a
# named `test_framework` names something detection did not find. Detection
# is the stricter question (jest is detected only when `package.json` declares
# it); this is the looser one, so a project that wires a runner in a way
# detection does not recognise keeps it.
_WIRING = {
    'pytest': lambda root: (os.path.isfile(os.path.join(root, 'conftest.py'))
                            or os.path.isfile(os.path.join(root, 'pytest.ini'))
                            or os.path.isfile(os.path.join(root,
                                                           'pyproject.toml'))),
    'jest': lambda root: os.path.isfile(os.path.join(root, 'package.json')),
    'vitest': lambda root: os.path.isfile(os.path.join(root, 'package.json')),
    'xunit': lambda root: _any_file(root, '.csproj'),
    'sql': lambda root: _any_file(root, '.sql'),
}


def _any_file(root, suffix):
    for _dirpath, filenames in _walk(root):
        for name in filenames:
            if name.endswith(suffix):
                return True
    return False


def carries_wiring(project_root, name):
    """True when `project_root` carries anything a `name` runner could run.

    Shell and any name this release does not ship a plugin for answer True:
    shell needs no wiring, and an unknown name is somebody else's decision.
    """
    test = _WIRING.get(name)
    if test is None:
        return True
    try:
        return bool(test(project_root))
    except OSError:
        return True


def prune_unwired(project_root, names):
    """`(kept, dropped)` from a configured `test_framework` list.

    A name detection does not find and the tree carries no wiring for is
    dropped: running it prints a runner that exited non-zero on every run and
    proves nothing. A name the tree does carry stays even when detection would
    not have picked it, so a project that wires a runner its own way keeps it.
    """
    detected = detect_frameworks(project_root)
    kept, dropped = [], []
    for name in names:
        if name in detected or carries_wiring(project_root, name):
            kept.append(name)
        else:
            dropped.append(name)
    return kept, dropped


def resolve_frameworks(project_root, raw):
    """`(frameworks, unknown)` from a `test_framework` config value.

    The value is a comma separated list because `purlin:init` writes one when
    it detects more than one framework. Order is the order it was written,
    duplicates collapse, and `auto` expands in place to everything detected.
    A name outside `KNOWN_FRAMEWORKS` is returned in `unknown` rather than
    run: a typo must not silently run nothing.
    """
    frameworks, unknown = [], []
    for part in str(raw or '').split(','):
        name = part.strip()
        if not name:
            continue
        if name == 'auto':
            for detected in detect_frameworks(project_root):
                if detected not in frameworks:
                    frameworks.append(detected)
        elif name in KNOWN_FRAMEWORKS:
            if name not in frameworks:
                frameworks.append(name)
        else:
            unknown.append(name)
    if not frameworks:
        for detected in detect_frameworks(project_root):
            if detected not in frameworks:
                frameworks.append(detected)
    return frameworks, unknown
