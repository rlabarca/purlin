"""The `tests` entries this repository's tests give the projects they build.

A throwaway project needs its own test command in `.purlin/config.json`
before a run can run anything. These are the entries `purlin:init` would
write, with the interpreter the test session runs under, so a temporary
project's tests run on the same Python and the same pytest. `ignored()` is
the ignore file `purlin:init` would write.
"""

import os
import shlex
import sys

PYTHON = shlex.quote(sys.executable)

_TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'templates', 'gitignore.purlin')


def ignored():
    """What `purlin:init` has git ignore, as setup writes it: the text of
    `templates/gitignore.purlin`. A project a test builds takes its ignore
    file from here, so a run leaves in it what it leaves in a real one: the
    dashboard's data and page are ignored, never untracked or changed."""
    with open(_TEMPLATE, encoding='utf-8') as handle:
        return handle.read()


def pytest_suite(files=('tests/test_*.py',), name='pytest', extra=''):
    """A `junit` suite that runs pytest on this interpreter."""
    return {'name': name,
            'run': ('%s -m pytest -q -p no:cacheprovider %s{files} '
                    '--junitxml={report}' % (PYTHON, extra + ' ' if extra
                                             else '')),
            'report': '.purlin/runtime/reports/%s.xml' % name,
            'format': 'junit', 'files': list(files)}


def shell_suite(files=('**/*.test.sh',), name='shell'):
    """An `exit` suite: each script is one test and passes when it exits 0."""
    return {'name': name, 'run': 'bash {files}', 'report': None,
            'format': 'exit', 'files': list(files)}


def sql_suite(files=('tests/*.sql',), name='sql'):
    """An `exit` suite of SQL scripts, each run through sqlite3."""
    return {'name': name, 'run': 'sqlite3 -bail :memory: < {files}',
            'report': None, 'format': 'exit', 'files': list(files)}
