"""Which test frameworks a project uses, and the `tests` entry each one gets.

Detection answers all the matches, not the first: a project can carry pytest
for the server and vitest for the client. The first test run in a project
whose `tests` setting is empty suggests the entry of every framework it
detects, in the order of `ENTRIES`, with the report flag already in each
command, and says in one line what each framework needs added before it can
write a report. On Windows the pytest entry starts `py -3 -m pytest` in
place of `python3 -m pytest`. Where it detects none, the agent reads the
project and proposes an entry.

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
        'run': 'python3 -m pytest {files} --junitxml={report}',
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
                "npx jest --ci {files} --reporters=default "
                "--reporters=jest-junit"),
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
# line; None where it needs nothing. jest's line names the package manager
# the project uses (`needs`).
JEST_NEEDS = 'jest needs the package jest-junit to write its report: run %s'
JEST_JUNIT_INSTALL = {
    'npm': 'npm install --save-dev jest-junit',
    'yarn': 'yarn add --dev jest-junit',
    'pnpm': 'pnpm add --save-dev jest-junit',
}
NEEDS = {
    'pytest': None,
    'vitest': None,
    'jest': JEST_NEEDS % JEST_JUNIT_INSTALL['npm'],
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
_SKIP_DIRS = ('node_modules', 'bin', 'obj')

# Folders of test fixtures, samples and test data, at any depth: a project
# kept there to test against is not a tool this project uses.
FIXTURE_DIRS = ('fixtures', 'fixture', 'samples', 'sample', 'testdata',
                'test_data', 'test-data')

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
                             if not d.startswith('.') and d not in _SKIP_DIRS
                             and d not in FIXTURE_DIRS)
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


def _pytest_tests_folder(root):
    """True when `tests/` at the root holds a `test_*.py` at any depth."""
    tests = os.path.join(root, 'tests')
    if not os.path.isdir(tests):
        return False
    return _any_file(tests, lambda n: n.startswith('test_') and n.endswith('.py'))


_DETECTORS = (
    ('pytest', lambda root: (os.path.isfile(os.path.join(root, 'conftest.py'))
                             or os.path.isfile(os.path.join(root, 'pytest.ini'))
                             or '[tool.pytest' in _read(root, 'pyproject.toml')
                             or _pytest_tests_folder(root))),
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


def package_manager(project_root):
    """`yarn` where the root holds `yarn.lock`, `pnpm` where it holds
    `pnpm-lock.yaml`, and `npm` where it holds neither, or both."""
    yarn = os.path.isfile(os.path.join(project_root, 'yarn.lock'))
    pnpm = os.path.isfile(os.path.join(project_root, 'pnpm-lock.yaml'))
    if yarn and not pnpm:
        return 'yarn'
    if pnpm and not yarn:
        return 'pnpm'
    return 'npm'


def needs(project_root, framework):
    """The line saying what `framework` needs added in this project, or None.

    jest's names the install command of the package manager the project's
    lock file shows, so running it leaves no second lock file beside the
    first.
    """
    if framework == 'jest':
        return JEST_NEEDS % JEST_JUNIT_INSTALL[package_manager(project_root)]
    return NEEDS.get(framework)


def entry_for(framework):
    """The `tests` entry for one framework, as a new dict."""
    base = ENTRIES[framework]
    return {'name': framework, 'run': base['run'], 'report': base['report'],
            'format': base['format'], 'files': list(base['files'])}


def entries_for(frameworks):
    """The `tests` setting for a list of frameworks, unknown names left out."""
    return [entry_for(name) for name in frameworks if name in ENTRIES]


# The start of the pytest entry's command, and what it reads on Windows,
# where the Python launcher is `py` and `python3` is often not on PATH.
PYTHON_COMMAND = 'python3 -m pytest'
WINDOWS_PYTHON_COMMAND = 'py -3 -m pytest'

def suggest(project_root, os_name=None):
    """The `tests` entries the first test run suggests, as a list.

    The entry of every framework detected, in registry order; empty where
    none is detected. `os_name` is `windows` for a Windows machine, and with
    none given it is read from this one: there the pytest entry's command
    starts `py -3 -m pytest`.
    """
    windows = (os_name == 'windows' if os_name is not None
               else os.name == 'nt')
    entries = entries_for(detect_frameworks(project_root))
    for entry in entries:
        if windows and entry['run'].startswith(PYTHON_COMMAND):
            entry['run'] = (WINDOWS_PYTHON_COMMAND
                            + entry['run'][len(PYTHON_COMMAND):])
    return entries


# ---------------------------------------------------------------------------
# Leaving a slow test out of a run
# ---------------------------------------------------------------------------

# A proof tagged `@slow` has a test `purlin:test` never starts. Nothing is
# added to the test or to the project's suite: the test is left out through
# its own tool's option, added to the command the settings hold. Each tool
# is known by its command and the report format it writes.
_TOOLS = (
    ('pytest', 'junit', re.compile(r'\bpytest\b|\bpy\.test\b')),
    ('vitest', 'junit', re.compile(r'\bvitest\b')),
    ('jest', 'junit', re.compile(r'\bjest\b')),
    ('dotnet', 'trx', re.compile(r'\bdotnet\s+test\b')),
    ('go', 'gotest', re.compile(r'\bgo\s+test\b')),
)

# The option a command may already carry. A second one would replace or
# fight the project's own, so its slow tests are started instead.
_CARRIED = {
    'vitest': re.compile(r'(?:^|\s)(?:-t|--testNamePattern)(?:[\s=]|$)'),
    'jest': re.compile(r'(?:^|\s)(?:-t|--testNamePattern)(?:[\s=]|$)'),
    'dotnet': re.compile(r'(?:^|\s)--filter(?:[\s=]|$)'),
    'go': re.compile(r'(?:^|\s)-skip(?:[\s=]|$)'),
}

# A command with no `{files}` gets the option at its end, which a command
# that pipes, chains or redirects does not allow.
_SHELL_OPERATOR = re.compile(r'[|;&<>]')

# What pytest exits with when every test it was given was deselected.
PYTEST_NOTHING_COLLECTED = 5


def tool_of(suite):
    """`pytest`, `vitest`, `jest`, `dotnet` or `go` for a suite whose command
    is that tool's and whose report is the one it writes, else None."""
    for name, fmt, pattern in _TOOLS:
        if suite.format == fmt and pattern.search(suite.run or ''):
            return name
    return None


def _js_title(test):
    """A JavaScript test's full title as jest and vitest match it: the
    `describe` titles and its own, joined by one space."""
    return ' '.join(list(test.scopes) + [test.name])


def _js_regex(text):
    """`text` with every character a JavaScript regular expression reads
    specially escaped."""
    return re.sub(r'([\\^$.*+?()\[\]{}|/])', r'\\\1', text)


def _dotnet_name(test):
    """A C# test's fully qualified name: namespace, classes joined by `+`,
    method."""
    owner = '+'.join(test.scopes)
    parts = [part for part in (test.namespace, owner, test.name) if part]
    return '.'.join(parts)


def _dotnet_value(text):
    """`text` with the characters a `dotnet test --filter` value reads
    specially escaped."""
    return re.sub(r'([\\()&|=!~])', r'\\\1', text)


def leave_out(suite, slow, others=()):
    """`(option, held, started)` for the slow tests of one suite.

    `slow` is `[(path, test)]`, each test one whose every marker names a
    proof tagged `@slow`, `test` None for a file of an `exit` suite; `others`
    is the suite's marked tests that are not slow. `option` is the text to
    add to the suite's command, '' where none is needed, `held` the tests it
    leaves out and `started` those the command cannot leave out: the tool is
    not one of `_TOOLS`, the command already carries the option or cannot
    take one at its end, the option would leave out a test of `others` as
    well, or the test is one NUnit names row by row.
    """
    slow = list(slow)
    if not slow:
        return '', [], []
    if suite.format == 'exit':
        # The file is the test, and a file not handed to the command is a
        # test not started.
        return '', slow, []
    tool = tool_of(suite)
    carried = _CARRIED.get(tool)
    if tool is None or (carried is not None and carried.search(suite.run)) \
            or ('{files}' not in suite.run
                and _SHELL_OPERATOR.search(suite.run)):
        return '', [], slow
    import shlex
    if tool == 'pytest':
        held = slow
        option = ' '.join('--deselect %s' % shlex.quote(
            '%s::%s' % (path, test.qualified('::'))) for path, test in held)
        return option, held, []
    if tool in ('vitest', 'jest'):
        # Both match a pattern against the full title, whatever the file,
        # so a test of the same title elsewhere would be left out with it.
        taken = [_js_title(test).lower() for _path, test in others]
        held, started = [], []
        for path, test in slow:
            title = _js_title(test).lower()
            shared = any(other == title or other.endswith(' ' + title)
                         for other in taken)
            (started if shared or test.pattern is not None
             else held).append((path, test))
        if not held:
            return '', [], started
        titles = sorted({_js_regex(_js_title(test)) for _path, test in held})
        return ('--testNamePattern %s' % shlex.quote(
            '^(?!(?:.* )?(?:%s)$)' % '|'.join(titles))), held, started
    if tool == 'dotnet':
        # NUnit names a `[TestCase]` test once per row, with the row's
        # arguments after the method's name, so no one name leaves it out.
        held = [(path, test) for path, test in slow if not test.rows]
        started = [(path, test) for path, test in slow if test.rows]
        if not held:
            return '', [], started
        names = sorted({_dotnet_value(_dotnet_name(test))
                        for _path, test in held})
        return ('--filter %s' % shlex.quote('&'.join(
            'FullyQualifiedName!=%s' % name for name in names))), held, started
    # go: `-skip` matches a test's name in every package.
    taken = {test.name for _path, test in others}
    held = [(path, test) for path, test in slow if test.name not in taken]
    started = [(path, test) for path, test in slow if test.name in taken]
    if not held:
        return '', [], started
    names = sorted({re.escape(test.name) for _path, test in held})
    return '-skip %s' % shlex.quote('^(?:%s)$' % '|'.join(names)), held, started
