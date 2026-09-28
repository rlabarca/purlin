"""The `tests` entries this repository's tests give the projects they build.

A throwaway project needs its own test command in `.purlin/config.json`
before a run can run anything. These are the entries `purlin:init` would
write, with the interpreter the test session runs under, so a temporary
project's tests run on the same Python and the same pytest.
"""

import shlex
import sys

PYTHON = shlex.quote(sys.executable)


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
