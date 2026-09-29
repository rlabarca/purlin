"""Which test frameworks a project uses, and the `tests` entry each one gets.

Detection answers all the matches, not the first: a project can carry pytest
for the server and vitest for the client. The first test run in a project
whose `tests` setting is empty suggests the entry of the first framework it
detects, in the order of `ENTRIES`, with the report flag already in the
command, and says in one line what that framework needs added before it can
write a report. Where it detects none, `purlin:test` reads the project and
proposes an entry.

Nothing of Purlin is installed in a project's test suite: every entry below
runs the project's own test command and reads the report that command writes.
`references/supported_frameworks.md` shows the same entries to a reader.
"""

import json
import os
import re
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

REPORTS = '.purlin/runtime/reports'

_JS_TEST_GLOBS = ['**/*.%s.%s' % (kind, ext) for kind in ('test', 'spec')
                  for ext in ('js', 'jsx', 'mjs', 'cjs', 'ts', 'tsx')]

# The entry of the `tests` setting suggested for each framework, in the order
# detection tries them. Each command is the framework's own, with the flag
# that writes the report Purlin reads.
ENTRIES = {
    'pytest': {
        'run': 'python3 -m pytest --ignore=mutants {files} --junitxml={report}',
        'report': REPORTS + '/pytest.xml', 'format': 'junit',
        'files': ['**/test_*.py', '**/*_test.py'],
    },
    'vitest': {
        'run': ('npx vitest run --reporter=default --reporter=junit '
                '--outputFile.junit={report} {files}'),
        'report': REPORTS + '/vitest.xml', 'format': 'junit',
        'files': list(_JS_TEST_GLOBS),
    },
    'jest': {
        'run': ("JEST_JUNIT_OUTPUT_FILE={report} "
                "JEST_JUNIT_ADD_FILE_ATTRIBUTE=true "
                "JEST_JUNIT_CLASSNAME='{classname}' "
                "JEST_JUNIT_TITLE='{title}' "
                "JEST_JUNIT_ANCESTOR_SEPARATOR=' > ' "
                "npx jest --ci --reporters=default --reporters=jest-junit "
                "{files}"),
        'report': REPORTS + '/jest.xml', 'format': 'junit',
        'files': list(_JS_TEST_GLOBS),
    },
    'dotnet': {
        'run': 'dotnet test --logger trx --results-directory {report}',
        'report': REPORTS + '/dotnet', 'format': 'trx',
        'files': ['**/*.cs'],
    },
    'go': {
        'run': 'go test -json ./...',
        'report': '-', 'format': 'gotest',
        'files': ['**/*_test.go'],
    },
    'sql': {
        'run': 'sqlite3 -bail :memory: < {files}',
        'report': None, 'format': 'exit',
        'files': ['**/test_*.sql', '**/*_test.sql', '**/*.test.sql'],
    },
    'shell': {
        'run': 'bash {files}',
        'report': None, 'format': 'exit',
        'files': ['**/*.test.sh'],
    },
}

# What each framework needs added before it can write the report, in one
# line; None where it needs nothing.
NEEDS = {
    'pytest': None,
    'vitest': None,
    'jest': 'jest needs the package jest-junit to write its report: run '
            'npm install --save-dev jest-junit',
    'dotnet': None,
    'go': None,
    'sql': 'sql runs each test file through the sqlite3 command, and a test '
           'fails by raising an error; change the run command for another '
           'engine',
    'shell': None,
}

# Directory names detection never descends into: dot directories are tool
# state, and `node_modules` is other people's code, where a vendored package's
# own fixtures are not this project's frameworks.
_SKIP_DIRS = ('node_modules', 'bin', 'obj', 'mutants')

# A SQL file counts as a test only when its name says so. `tests/fixtures.sql`
# is seed data, not a test.
_SQL_TEST_NAME = re.compile(r'^(?:test_.+\.sql|.+_test\.sql|.+\.test\.sql)$')

# A .NET test project is any `*.csproj` that references a test framework or
# the test SDK.
_DOTNET_TEST_REF = re.compile(
    r'Include="(?:xunit|nunit|MSTest|Microsoft\.NET\.Test\.Sdk)(?:\.|")',
    re.IGNORECASE)


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


def _has_dotnet_tests(root):
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
            if _DOTNET_TEST_REF.search(text):
                return True
    return False


def _any_file(root, test):
    for _dirpath, filenames in _walk(root):
        if any(test(name) for name in filenames):
            return True
    return False


_DETECTORS = (
    ('pytest', lambda root: (os.path.isfile(os.path.join(root, 'conftest.py'))
                             or os.path.isfile(os.path.join(root, 'pytest.ini'))
                             or '[tool.pytest' in _read(root, 'pyproject.toml'))),
    ('vitest', lambda root: _npm_package(root, 'vitest')),
    ('jest', lambda root: _npm_package(root, 'jest')),
    ('dotnet', _has_dotnet_tests),
    ('go', lambda root: (os.path.isfile(os.path.join(root, 'go.mod'))
                         and _any_file(root, lambda n: n.endswith('_test.go')))),
    ('sql', lambda root: _any_file(root, _SQL_TEST_NAME.match)),
    ('shell', lambda root: _any_file(root, lambda n: n.endswith('.test.sh'))),
)


def detect_frameworks(project_root):
    """Every framework detected under `project_root`, in registry order.

    Empty when nothing matches.
    """
    found = []
    for framework_id, test in _DETECTORS:
        try:
            if test(project_root):
                found.append(framework_id)
        except OSError:
            continue
    return found


def entry_for(framework):
    """The `tests` entry for one framework, as a new dict."""
    base = ENTRIES[framework]
    return {'name': framework, 'run': base['run'], 'report': base['report'],
            'format': base['format'], 'files': list(base['files'])}


def entries_for(frameworks):
    """The `tests` setting for a list of frameworks, unknown names left out."""
    return [entry_for(name) for name in frameworks if name in ENTRIES]


def suggest(project_root):
    """The `tests` entry the first test run suggests, or None.

    The entry of the first framework detected, in registry order; None where
    none is detected.
    """
    found = detect_frameworks(project_root)
    return entry_for(found[0]) if found else None
