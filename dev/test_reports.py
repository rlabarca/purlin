"""Tests for how a test's result reaches its proof: the markers, the reports, the tie.

The reports are real. pytest and the shell scripts run here in temporary
projects, and the JUnit XML, the TRX and the exit codes they leave are what
is read. Jest, Vitest and `dotnet test` reports are captured under
`dev/fixtures/reports/`, each beside the test source it was written for; the
tests at the end of this file run those tools again where they are installed
and check that they still write what the capture holds. The Go stream is the
one real `go test -json` printed over the two packages beside it. The run of
that module through the command init writes is in `dev/test_init_scaffold.py`.

Each marked test shows one case. Where several cases come from one run, the
run is made once, in a fixture of this module, and each case reads its part.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(REPO, 'VERSION'), encoding='utf-8') as _handle:
    VERSION = _handle.read().strip()

for _path in (os.path.join(REPO, 'scripts', 'run'),
              os.path.join(REPO, 'scripts', 'mcp'),
              os.path.join(REPO, 'dev')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import reports                                                # noqa: E402
import suites                                                 # noqa: E402
from purlin import markers                                    # noqa: E402
from reports_project import (FIXTURES, GO_SPECS,              # noqa: E402
                             RUN_SCRIPT, _evidence, _fixture, _run,
                             _write)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def _spec(feature, count):
    """A spec of `count` rules, each with one proof of the same number."""
    rules = ''.join('- RULE-%d: rule %d\n' % (n, n)
                    for n in range(1, count + 1))
    proofs = ''.join('- PROOF-%d (RULE-%d): observe %d\n' % (n, n, n)
                     for n in range(1, count + 1))
    return ('# Feature: %s\n\n> Scope: src/\n\n## Rules\n\n%s\n## Proof\n\n%s'
            % (feature, rules, proofs))


LOGIN_SPEC = _spec('login', 3)


# A passing test for each of LOGIN_SPEC's three proofs, twelve lines long.
_WELL_FORMED = ('# purlin: login PROOF-1\ndef test_a():\n    pass\n\n'
                '# purlin: login PROOF-2\ndef test_b():\n    pass\n\n'
                '# purlin: login PROOF-3\ndef test_c():\n    pass\n\n')


def _project(tmp_path, tests, spec=LOGIN_SPEC, feature='login',
             more_specs=()):
    root = tmp_path / 'project'
    (root / '.purlin').mkdir(parents=True)
    (root / 'specs' / 'a').mkdir(parents=True)
    (root / 'src').mkdir()
    (root / 'tests').mkdir()
    (root / 'src' / 'code.py').write_text('X = 1\n', encoding='utf-8')
    _config(root, tests)
    (root / 'specs' / 'a' / ('%s.md' % feature)).write_text(
        spec, encoding='utf-8')
    for name, text in more_specs:
        (root / 'specs' / 'a' / ('%s.md' % name)).write_text(
            text, encoding='utf-8')
    return root


def _config(root, tests):
    (root / '.purlin' / 'config.json').write_text(json.dumps(
        {'version': VERSION, 'tests': tests}),
        encoding='utf-8')


def _results(section):
    """`{(id, test): result}` for one evidence section."""
    return {(entry['id'], entry['test']): entry['result']
            for entry in section['proofs']}


def _by_id(section):
    """`{id: result}` for one evidence section."""
    return {entry['id']: entry['result'] for entry in section['proofs']}


def _login_run(tmp_path, body, spec=LOGIN_SPEC):
    """Run a `login` project whose one pytest file is `body`.

    Answers the exit code, the printed output and the evidence's results.
    """
    root = _project(tmp_path, [suites.pytest_suite()], spec=spec)
    _write(root, 'tests/test_login.py', body)
    code, out = _run(root, '--all', '--test')
    return code, out, _results(_evidence(root))


def _pytest_run(tmp_path, body):
    """Run real pytest over one test file and read its JUnit report."""
    root = tmp_path / 'py'
    (root / 'tests').mkdir(parents=True)
    (root / 'tests' / 'test_login.py').write_text(body, encoding='utf-8')
    report = root / 'report.xml'
    subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p',
                    'no:cacheprovider', 'tests/test_login.py',
                    '--junitxml=%s' % report], cwd=str(root),
                   capture_output=True)
    cases, problem = reports.read_report('junit', str(root), 'report.xml')
    assert problem is None
    return root, cases


def _tie(root, suite, cases):
    marked = markers.scan(str(root), [suite])
    return reports.tie(str(root), suite, cases, marked), marked


def _marker_results(marked, outcomes):
    """`{(feature, id): result}` for every tied marker."""
    out = {}
    for path, found in marked.items():
        for test in found.tests:
            for marker in test.markers:
                out[marker.key()] = reports.result_of(
                    outcomes.get((path, test.line), []))
    return out


def _captured(tmp_path, tool, report, fmt, globs):
    """A copy of one captured project, its suite and the cases its report
    holds."""
    root = _fixture(tmp_path, tool)
    suite = markers.Suite(tool, 'x', report, fmt, globs)
    cases, problem = reports.read_report(fmt, str(root), report)
    assert problem is None
    return root, suite, cases


def _trx(rows):
    """A TRX document of one result per `(class, method, outcome)` row, in
    the shape `dotnet test --logger trx` writes: a definition per test and a
    result joined to it by its id."""
    tests = ''.join('<UnitTest id="t%d"><TestMethod className="%s" '
                    'name="%s"/></UnitTest>' % (n, cls, name)
                    for n, (cls, name, _o) in enumerate(rows))
    results = ''.join('<UnitTestResult testId="t%d" outcome="%s"/>'
                      % (n, row[2]) for n, row in enumerate(rows))
    return ('<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/'
            'TeamTest/2010"><Results>%s</Results><TestDefinitions>%s'
            '</TestDefinitions></TestRun>' % (results, tests))


PATHS = ['dev/test_a.py', 'dev/sub/test_b.py', 'a/b/c.test.ts']


def _matched(paths, glob):
    return [path for path in paths if markers.glob_match(path, glob)]


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

class TestTheMarker:

    # purlin: reports PROOF-1
    def test_every_comment_syntax_is_read(self):
        text = '\n'.join([
            '# purlin: login PROOF-1', '// purlin: login PROOF-2',
            '-- purlin: login PROOF-3', '; purlin: login PROOF-4',
            '% purlin: login PROOF-5', "' purlin: login PROOF-6",
            '/* purlin: login RULE-7 */',
            '<!-- purlin: login PROOF-8 -->']) + '\n'
        found = markers.comment_markers(text, '.txt')
        assert [(m.feature, m.id, m.line) for m in found] == [
            ('login', 'PROOF-1', 1), ('login', 'PROOF-2', 2),
            ('login', 'PROOF-3', 3), ('login', 'PROOF-4', 4),
            ('login', 'PROOF-5', 5), ('login', 'PROOF-6', 6),
            ('login', 'RULE-7', 7), ('login', 'PROOF-8', 8)]

    # purlin: reports PROOF-27
    def test_a_marker_after_code_in_a_text_file_is_not_read(self):
        assert markers.comment_markers(
            'x = 1  # purlin: login PROOF-1\n', '.txt') == []

    # purlin: reports PROOF-3
    def test_a_star_does_not_cross_a_folder(self):
        assert _matched(PATHS, 'dev/test_*.py') == ['dev/test_a.py']

    # purlin: reports PROOF-43
    def test_a_glob_with_no_slash_matches_the_name_in_any_folder(self):
        assert _matched(PATHS, 'test_*.py') == ['dev/test_a.py',
                                               'dev/sub/test_b.py']

    @staticmethod
    def _two_files(tmp_path):
        root = tmp_path / 'p'
        _write(root, 'tests/test_a.py', '# purlin: login PROOF-1\n'
                                        'def test_a():\n    pass\n')
        _write(root, 'other/test_b.py', '# purlin: login PROOF-2\n'
                                        'def test_b():\n    pass\n')
        return root

    # purlin: reports PROOF-47
    def test_a_file_two_suites_match_belongs_to_the_first(self, tmp_path):
        root = self._two_files(tmp_path)
        first = markers.Suite('first', 'x', None, 'junit', ['tests/*.py'])
        second = markers.Suite('second', 'x', None, 'junit', ['**/*.py'])
        files = markers.test_files(str(root), [first, second])
        assert {path: suite.name for path, suite in files.items()} == {
            'tests/test_a.py': 'first', 'other/test_b.py': 'second'}

    # purlin: reports PROOF-6
    def test_python_declares_test_functions_and_methods_only(self):
        python = markers.python_tests(
            'def helper():\n    pass\n\ndef test_a():\n    pass\n\n'
            'class TestB:\n    def test_c(self):\n        pass\n'
            '    def helper(self):\n        pass\n')
        assert [(t.name, t.scopes) for t in python] == [
            ('test_a', []), ('test_c', ['TestB'])]

    # purlin: reports PROOF-53
    def test_typescript_declares_its_it_and_test_calls(self):
        with open(os.path.join(FIXTURES, 'vitest', 'tests', 'login.test.ts'),
                  encoding='utf-8') as handle:
            js = markers.js_tests(handle.read())
        assert [(t.name, t.scopes) for t in js] == [
            ('accepts', []), ('same name', ['outer', 'inner']),
            ('same name', ['outer']), ('skipped', ['outer']),
            ('param %i', ['outer'])]

    # purlin: reports PROOF-54
    def test_csharp_declares_its_fact_and_theory_methods(self):
        with open(os.path.join(FIXTURES, 'dotnet', 'App.Tests',
                               'GreetingTests.cs'), encoding='utf-8') as handle:
            cs = markers.cs_tests(handle.read())
        assert [(t.name, t.scopes, t.namespace) for t in cs] == [
            ('GreetsByName', ['GreetingTests'], 'App.Tests'),
            ('Param', ['GreetingTests'], 'App.Tests'),
            ('Skipped', ['GreetingTests'], 'App.Tests'),
            ('Inner', ['GreetingTests', 'Nested'], 'App.Tests')]

# ---------------------------------------------------------------------------
# Reading the four formats
# ---------------------------------------------------------------------------

def _go_stream():
    with open(os.path.join(FIXTURES, 'go', 'report.json'),
              encoding='utf-8') as handle:
        return handle.read()


GO_CASES = [
    ('example.com/shop/tax', 'TestRate', 'pass'),
    ('example.com/shop/tax', 'TestLookupPanics', 'fail'),
    ('example.com/shop/cart', 'TestTotal', 'pass'),
    ('example.com/shop/cart', 'TestParse/empty', 'fail'),
    ('example.com/shop/cart', 'TestParse/one', 'pass'),
    ('example.com/shop/cart', 'TestParse', 'fail'),
    ('example.com/shop/cart', 'TestDiscount', 'skip'),
    ('example.com/shop/cart', 'TestTotalIsWrong', 'fail')]


class TestTheReports:

    # purlin: reports PROOF-7
    def test_four_python_tests_read_pass_fail_skip_fail_in_their_order(
            self, tmp_path):
        _root, cases = _pytest_run(tmp_path, (
            'import pytest\n\n'
            'def test_passes():\n    pass\n\n'
            'def test_fails():\n    assert 1 == 2\n\n'
            '@pytest.mark.skip(reason="later")\n'
            'def test_skipped():\n    pass\n\n'
            '@pytest.fixture\ndef broken():\n    raise RuntimeError("x")\n\n'
            'def test_errors(broken):\n    pass\n'))
        assert [(c.classname, c.name, c.outcome) for c in cases] == [
            ('tests.test_login', 'test_passes', 'pass'),
            ('tests.test_login', 'test_fails', 'fail'),
            ('tests.test_login', 'test_skipped', 'skip'),
            ('tests.test_login', 'test_errors', 'fail')]

    # purlin: reports PROOF-8
    def test_the_trx_dotnet_writes(self):
        cases, problem = reports.read_report(
            'trx', os.path.join(FIXTURES, 'dotnet'), 'dotnet.trx')
        assert problem is None
        # In the report's order: the row `x: 2` passed and `x: 1` failed.
        assert [(c.classname, c.name, c.outcome) for c in cases] == [
            ('App.Tests.GreetingTests', 'GreetsByName', 'pass'),
            ('App.Tests.GreetingTests', 'Param', 'pass'),
            ('App.Tests.GreetingTests', 'Param', 'fail'),
            ('App.Tests.GreetingTests', 'Skipped', 'skip'),
            ('App.Tests.GreetingTests+Nested', 'Inner', 'pass'),
            ('Other.Tests.GreetingTests', 'GreetsByName', 'fail')]

    # purlin: reports PROOF-59
    def test_the_trx_outcomes_the_capture_does_not_hold(self):
        cases = reports.read_trx(_trx([
            ('A.T', 'E', 'Error'), ('A.T', 'T', 'Timeout'),
            ('A.T', 'B', 'Aborted'), ('A.T', 'I', 'Inconclusive')]))
        assert [(c.classname, c.name, c.outcome) for c in cases] == [
            ('A.T', 'E', 'fail'), ('A.T', 'T', 'fail'), ('A.T', 'B', 'fail'),
            ('A.T', 'I', 'skip')]

    # purlin: reports PROOF-121
    def test_a_fixture_that_raises_is_marked_an_error_and_a_failure_is_not(
            self, tmp_path):
        _root, cases = _pytest_run(tmp_path, (
            'import pytest\n\n'
            'def test_fails():\n    assert 1 == 2\n\n'
            '@pytest.fixture\ndef broken():\n    raise RuntimeError("x")\n\n'
            'def test_errors(broken):\n    pass\n'))
        assert [(c.name, c.outcome, c.error) for c in cases] == [
            ('test_fails', 'fail', False), ('test_errors', 'fail', True)]

    # purlin: reports PROOF-122
    def test_a_trx_error_timeout_or_abort_is_marked_an_error(self):
        cases = reports.read_trx(_trx([
            ('A.T', 'E', 'Error'), ('A.T', 'T', 'Timeout'),
            ('A.T', 'B', 'Aborted'), ('A.T', 'F', 'Failed')]))
        assert [(c.name, c.outcome, c.error) for c in cases] == [
            ('E', 'fail', True), ('T', 'fail', True), ('B', 'fail', True),
            ('F', 'fail', False)]

    # purlin: reports PROOF-9
    def test_the_stream_go_test_prints(self):
        cases = reports.read_gotest(_go_stream())
        assert [(c.package, c.name, c.outcome) for c in cases] == GO_CASES

    # purlin: reports PROOF-115
    def test_a_junit_skip_carries_its_message_as_the_reason(self):
        (case,) = reports.read_junit(
            '<testsuite><testcase classname="tests.test_screens" '
            'name="test_screens"><skipped message="nothing to check: this '
            'project has no screens"/></testcase></testsuite>')
        assert (case.name, case.outcome, case.reason) == (
            'test_screens', 'skip',
            'nothing to check: this project has no screens')

    # purlin: reports PROOF-117
    def test_a_go_skip_carries_its_last_output_as_the_reason(self):
        events = [
            {'Action': 'run', 'Test': 'TestScreens'},
            {'Action': 'output', 'Test': 'TestScreens',
             'Output': '=== RUN   TestScreens\n'},
            {'Action': 'output', 'Test': 'TestScreens',
             'Output': '    screens_test.go:12: nothing to check: this project '
                       'has no screens\n'},
            {'Action': 'output', 'Test': 'TestScreens',
             'Output': '--- SKIP: TestScreens (0.00s)\n'},
            {'Action': 'skip', 'Test': 'TestScreens'}]
        stream = ''.join(json.dumps(dict(event, Package='example.com/app'))
                         + '\n' for event in events)
        (case,) = reports.read_gotest(stream)
        assert (case.name, case.outcome, case.reason) == (
            'TestScreens', 'skip',
            'nothing to check: this project has no screens')

# ---------------------------------------------------------------------------
# The tie
# ---------------------------------------------------------------------------

PYTEST_SUITE = markers.Suite('pytest', 'x', 'report.xml', 'junit',
                             ['tests/test_*.py'])

_ONE_CLASS = ('class TestGroup:\n'
              '    # purlin: login PROOF-1\n'
              '    def test_same(self):\n        pass\n')


def _dotnet(tmp_path):
    return _captured(tmp_path, 'dotnet', 'dotnet.trx', 'trx', ['**/*.cs'])


def _go(tmp_path):
    return _captured(tmp_path, 'go', 'report.json', 'gotest',
                     ['**/*_test.go'])


class TestTheTie:

    # purlin: reports PROOF-10
    def test_a_python_class_names_its_module_file(self, tmp_path):
        root, cases = _pytest_run(tmp_path, _ONE_CLASS)
        assert [c.classname for c in cases] == ['tests.test_login.TestGroup']
        (outcomes, _problems), _marked = _tie(root, PYTEST_SUITE, cases)
        assert outcomes == {('tests/test_login.py', 3): ['pass']}

    # purlin: reports PROOF-62
    def test_a_jest_case_names_its_file(self, tmp_path):
        # The capture was written on a Mac. Jest on Windows names each file
        # with this system's separator, `tests\login.test.js`, so the
        # report is given the spelling the running system writes.
        native = os.path.join('tests', 'login.test.js')
        report = _fixture(tmp_path, 'jest') / 'jest.xml'
        report.write_bytes(report.read_bytes().replace(
            b'file="tests/login.test.js"',
            b'file="%s"' % native.encode('utf-8')))
        root = report.parent
        suite = markers.Suite('jest', 'x', 'jest.xml', 'junit',
                              ['tests/*.test.*'])
        cases, problem = reports.read_report('junit', str(root), 'jest.xml')
        assert problem is None
        assert {c.file for c in cases} == {native}
        (outcomes, _p), marked = _tie(root, suite, cases)
        assert list(marked) == ['tests/login.test.js']
        assert _marker_results(marked, outcomes)[('login', 'PROOF-1')] \
            == 'pass'

    # purlin: reports PROOF-63
    def test_a_trx_class_is_narrowed_by_its_namespace(self, tmp_path):
        root, suite, cases = _dotnet(tmp_path)
        (outcomes, problems), _marked = _tie(root, suite, cases)
        assert problems == []
        assert outcomes[('App.Tests/GreetingTests.cs', 7)] == ['pass']
        assert outcomes[('App.Tests/OtherGreetingTests.cs', 8)] == ['fail']

    _VALUES = ('import pytest\n\n'
               '# purlin: login PROOF-1\n'
               '@pytest.mark.parametrize("x", [1, %s])\n'
               'def test_values(x):\n    assert x > 0\n')

    # purlin: reports PROOF-68
    def test_a_parametrised_test_fails_when_one_value_fails(self, tmp_path):
        root, cases = _pytest_run(tmp_path, self._VALUES % '-2')
        (outcomes, _p), marked = _tie(root, PYTEST_SUITE, cases)
        assert _marker_results(marked, outcomes) == {
            ('login', 'PROOF-1'): 'fail'}

    # purlin: reports PROOF-70
    def test_a_go_test_with_a_failing_subtest_fails(self, tmp_path):
        root, suite, cases = _go(tmp_path)
        (outcomes, _p), marked = _tie(root, suite, cases)
        assert _marker_results(marked, outcomes)[('cart', 'PROOF-2')] \
            == 'fail'

    def _narrowed(self, tmp_path, tool, report):
        root, suite, cases = _captured(tmp_path, tool, report, 'junit',
                                       ['tests/*.test.*'])
        assert any(c.outcome == 'fail' for c in cases)
        (outcomes, problems), marked = _tie(root, suite, cases)
        assert problems == []
        return _marker_results(marked, outcomes)[('login', 'PROOF-2')]

    # purlin: reports PROOF-12
    def test_a_vitest_title_is_narrowed_by_its_outer_parts(self, tmp_path):
        assert self._narrowed(tmp_path, 'vitest', 'vitest.xml') == 'pass'

    # purlin: reports PROOF-73
    def test_a_python_test_is_narrowed_by_its_class(self, tmp_path):
        root, cases = _pytest_run(tmp_path, _ONE_CLASS + (
            '\nclass TestOther:\n'
            '    def test_same(self):\n        assert False\n'))
        (outcomes, problems), marked = _tie(root, PYTEST_SUITE, cases)
        assert problems == []
        assert _marker_results(marked, outcomes) == {
            ('login', 'PROOF-1'): 'pass'}

# ---------------------------------------------------------------------------
# Through a run
# ---------------------------------------------------------------------------

@pytest.fixture(scope='module')
def untied_run(tmp_path_factory):
    """Two tied markers over passing tests, and a third tied to no test."""
    return _login_run(tmp_path_factory.mktemp('untied'), (
        '# purlin: login PROOF-1\ndef test_one():\n    pass\n\n'
        '# purlin: login PROOF-2\ndef test_two():\n    pass\n\n'
        '# purlin: login PROOF-3\n'))


# Five marked tests, one per way a test can end.
_FIVE_OUTCOMES = (
    'import pytest\n\n'
    '# purlin: login PROOF-1\ndef test_passes():\n    pass\n\n'
    '# purlin: login PROOF-2\ndef test_fails():\n    assert 0\n\n'
    '# purlin: login PROOF-3\n@pytest.mark.skip(reason="later")\n'
    'def test_skipped():\n    pass\n\n'
    '@pytest.fixture\ndef broken():\n    raise RuntimeError("x")\n\n'
    '# purlin: login PROOF-4\ndef test_errors(broken):\n    pass\n\n'
    '# purlin: login PROOF-5\n@pytest.mark.parametrize("x", [\n'
    '    1, pytest.param(2, marks=pytest.mark.skip(reason="later"))])\n'
    'def test_partly_skipped(x):\n    pass\n')


@pytest.fixture(scope='module')
def five_outcomes(tmp_path_factory):
    _code, _out, results = _login_run(tmp_path_factory.mktemp('five'),
                                      _FIVE_OUTCOMES, _spec('login', 5))
    return {key[0]: value for key, value in results.items()}


@pytest.fixture(scope='module')
def exit_run(tmp_path_factory):
    """An `exit` suite over a script that exits 0 and one that exits 3."""
    suite = suites.shell_suite(('tests/*.sh',))
    suite['run'] = 'echo "call: {files}" >> calls.txt; ' + suite['run']
    root = _project(tmp_path_factory.mktemp('exit'), [suite])
    _write_lf(root, 'tests/good.sh', '#!/usr/bin/env bash\n'
              '# purlin: login PROOF-1\n# purlin: login PROOF-2\nexit 0\n')
    _write_lf(root, 'tests/bad.sh', '#!/usr/bin/env bash\n'
              '# purlin: login PROOF-3\nexit 3\n')
    code, out = _run(root, '--all', '--test')
    return root, code, out


def _write_lf(root, rel, text):
    """`_write`, keeping each line's end a bare `\\n` on every system.

    A file written as text on Windows gets `\\r\\n`, and bash reads
    `exit 0\\r` as a word that is not a number: the script would fail
    there for its line ends, not for what it checks.
    """
    path = root.joinpath(*rel.split('/'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode('utf-8'))
    return path


def _arguments_run(tmp_path, *args):
    """Run `login` and `signup` with a command that writes down its
    arguments, one per line, and answer them."""
    suite = suites.pytest_suite()
    suite['run'] = 'printf "%s\\n" x {files} {report} >> args.txt; ' \
        + suite['run']
    root = _project(tmp_path, [suite],
                    more_specs=(('signup', _spec('signup', 3)),))
    _write(root, 'tests/test_login.py',
           '# purlin: login PROOF-1\ndef test_a():\n    pass\n')
    _write(root, 'tests/test_sign up.py',
           '# purlin: signup PROOF-1\ndef test_b():\n    pass\n')
    _run(root, *args)
    return (root / 'args.txt').read_text(encoding='utf-8').splitlines()


_STALE_CASE = ('<testsuite><testcase classname="tests.test_login" '
               'name="test_a"/></testsuite>')


def _silent_project(tmp_path, report):
    """A project whose pytest suite writes no report at `report`."""
    root = _project(tmp_path, [{'name': 'pytest', 'run': 'true',
                                'report': report, 'format': 'junit',
                                'files': ['tests/test_*.py']}])
    _write(root, 'tests/test_login.py',
           '# purlin: login PROOF-1\ndef test_a():\n    pass\n')
    return root


class TestThroughARun:

    # purlin: reports PROOF-124
    def test_a_marker_naming_a_feature_with_a_hyphen_is_tied(self, tmp_path):
        root = _project(tmp_path, [suites.pytest_suite()],
                        spec=_spec('sample-age', 1), feature='sample-age')
        os.rename(str(root / 'specs' / 'a'), str(root / 'specs' / 'intake'))
        _write(root, 'tests/test_age.py', '# purlin: sample-age PROOF-1\n'
                                          'def test_age():\n    pass\n')
        _code, out = _run(root, '--all', '--test')
        assert 'Markers: 1 tied to a test, 0 not tied.' in out.splitlines(), \
            out
        assert _by_id(_evidence(root, 'sample-age')) == {'PROOF-1': 'pass'}, \
            out

    # purlin: reports PROOF-49
    def test_two_markers_over_one_passing_test_both_pass(self, tmp_path):
        _code, out, results = _login_run(tmp_path, (
            '# purlin: login PROOF-1\n'
            '# purlin: login PROOF-2\n'
            'def test_two():\n    pass\n'), _spec('login', 2))
        assert results == {
            ('PROOF-1', 'tests/test_login.py::test_two'): 'pass',
            ('PROOF-2', 'tests/test_login.py::test_two'): 'pass'}, out

    # purlin: reports PROOF-50
    def test_a_blank_line_and_a_comment_after_a_marker_still_tie(
            self, tmp_path):
        _code, out, results = _login_run(tmp_path, (
            'import pytest\n\n'
            '# purlin: login PROOF-1\n\n# an ordinary comment\n'
            '@pytest.mark.parametrize("x", [1])\n'
            'def test_decorated(x):\n    assert x\n'), _spec('login', 1))
        assert results == {
            ('PROOF-1', 'tests/test_login.py::test_decorated'): 'pass'}, out

    # purlin: reports PROOF-5
    def test_a_marker_above_nothing_is_tied_to_no_test(self, untied_run):
        code, out, results = untied_run
        assert ('tests/test_login.py:9 names login PROOF-3 and no test '
                'follows it. Put the comment directly above a test, or run '
                'purlin:build to repair it.') in out.splitlines(), out
        assert results[('PROOF-3', '')] == 'missing'
        assert code == 1

    # purlin: reports PROOF-13
    def test_a_case_that_is_two_tests_is_counted_for_neither(
            self, tmp_path):
        code, out, results = _login_run(tmp_path, (
            '# purlin: login PROOF-1\ndef test_x():\n    pass\n\n'
            '# purlin: login PROOF-2\ndef test_x():\n    pass\n'),
            _spec('login', 2))
        assert ("The report's test_x matches 2 tests in tests/test_login.py, "
                'so its result is not counted. Give the tests different '
                'names, then run purlin:test.') in out.splitlines(), out
        assert {key[0]: value for key, value in results.items()} == {
            'PROOF-1': 'missing', 'PROOF-2': 'missing'}, out
        assert code == 1, out

    # purlin: reports PROOF-120
    def test_a_comment_naming_a_rule_that_has_proofs_exits_1(self, tmp_path):
        code, out, results = _login_run(tmp_path, (
            'import pytest\n\n'
            '# purlin: login RULE-1\n'
            'def test_ok():\n    pass\n'), _spec('login', 1))
        assert ('tests/test_login.py:3 names login RULE-1, which has proofs; '
                'a comment names one of its proofs. Correct the comment, or '
                'run purlin:build to repair it.') in out.splitlines(), out
        assert code == 1, out
        section = _evidence(tmp_path / 'project')
        assert section['rules']['RULE-1'] != 'passed', section
        assert [entry['result'] for entry in section['proofs']
                if entry['rule'] == 'RULE-1'] == ['missing'], section

    # purlin: reports PROOF-119
    def test_a_marker_inside_a_string_is_not_a_marker(self, tmp_path):
        body = ('NOTE = """\n'
                '# purlin: login PROOF-1\n'
                '"""\n\n'
                '# purlin: login PROOF-2\n'
                'def test_ok():\n    pass\n')
        code, out, results = _login_run(tmp_path, body, _spec('login', 2))
        found = markers.scan(str(tmp_path / 'project'))
        read = [(marker.id, marker.line)
                for marker in found['tests/test_login.py'].markers]
        assert read == [('PROOF-2', 5)], read
        assert results == {('PROOF-1', ''): 'missing',
                           ('PROOF-2', 'tests/test_login.py::test_ok'): 'pass'}

    # purlin: reports PROOF-123
    def test_a_marker_inside_a_here_document_is_not_a_marker(self, tmp_path):
        root = _project(tmp_path, [suites.shell_suite(('tests/*.sh',))],
                        spec=_spec('login', 2))
        _write_lf(root, 'tests/check.sh', '#!/usr/bin/env bash\n'
                  "cat <<'EOF' > /dev/null\n"
                  '# purlin: login PROOF-1\n'
                  'EOF\n'
                  '# purlin: login PROOF-2\n'
                  'exit 0\n')
        code, out = _run(root, '--all', '--test')
        found = markers.scan(str(root))
        read = [(marker.id, marker.line)
                for marker in found['tests/check.sh'].markers]
        assert read == [('PROOF-2', 5)], read
        assert _results(_evidence(root)) == {
            ('PROOF-1', ''): 'missing',
            ('PROOF-2', 'tests/check.sh::check.sh'): 'pass'}, out

    # purlin: reports PROOF-77
    def test_a_test_whose_setup_errors_is_fail(self, five_outcomes):
        assert five_outcomes['PROOF-4'] == 'fail'

    # purlin: reports PROOF-78
    def test_a_test_partly_skipped_and_otherwise_passing_is_missing(
            self, five_outcomes):
        assert five_outcomes['PROOF-5'] == 'missing'

    # purlin: reports PROOF-79
    def test_a_test_the_report_holds_no_case_of_is_missing(self, tmp_path):
        root = _project(tmp_path, [{
            'name': 'pytest', 'run': 'cp canned.xml {report}',
            'report': '.purlin/runtime/reports/pytest.xml',
            'format': 'junit', 'files': ['tests/test_*.py']}],
            spec=_spec('login', 2))
        _write(root, 'canned.xml', _STALE_CASE)
        _write(root, 'tests/test_login.py', (
            '# purlin: login PROOF-1\ndef test_a():\n    pass\n\n'
            '# purlin: login PROOF-2\ndef test_b():\n    pass\n'))
        _run(root, '--all', '--test')
        assert _by_id(_evidence(root)) == {'PROOF-1': 'pass',
                                           'PROOF-2': 'missing'}

    # purlin: reports PROOF-15
    def test_an_exit_suite_gives_each_file_its_exit_code(self, exit_run):
        root, code, out = exit_run
        assert code == 1
        assert 'Evidence is missing' not in out, out
        assert _results(_evidence(root)) == {
            ('PROOF-1', 'tests/good.sh::good.sh'): 'pass',
            ('PROOF-2', 'tests/good.sh::good.sh'): 'pass',
            ('PROOF-3', 'tests/bad.sh::bad.sh'): 'fail'}

    # purlin: reports PROOF-80
    def test_an_exit_suite_runs_its_command_once_per_file(self, exit_run):
        root, _code, _out = exit_run
        assert (root / 'calls.txt').read_text(encoding='utf-8').splitlines() \
            == ['call: tests/bad.sh', 'call: tests/good.sh']

    # purlin: reports PROOF-82
    def test_a_path_holding_a_space_is_one_argument_then_the_report_path(
            self, tmp_path):
        assert _arguments_run(tmp_path, '--feature', 'signup', '--test') == [
            'x', 'tests/test_sign up.py',
            '.purlin/runtime/reports/pytest.xml']

    # purlin: reports PROOF-84
    def test_the_command_runs_in_the_project_root(self, tmp_path):
        suite = suites.pytest_suite()
        suite['run'] = 'pwd -P > where.txt; ' + suite['run']
        root = _project(tmp_path, [suite])
        _write(root, 'tests/test_login.py', _WELL_FORMED)
        outside = tmp_path / 'elsewhere'
        outside.mkdir()
        subprocess.run([sys.executable, RUN_SCRIPT, '--project-root',
                        str(root), '--all', '--test'], capture_output=True,
                       cwd=str(outside))
        assert not (outside / 'where.txt').exists()
        assert (root / 'where.txt').read_text(encoding='utf-8') \
            == os.path.realpath(str(root)) + '\n'

    # purlin: reports PROOF-17
    def test_an_old_report_is_deleted_before_the_suite_runs(self, tmp_path):
        report = '.purlin/runtime/reports/pytest.xml'
        root = _silent_project(tmp_path, report)
        _write(root, report, _STALE_CASE)
        code, out = _run(root, '--all', '--test')
        assert code == 1
        assert 'wrote no report' in out, out
        assert not (root / report).exists()

    # purlin: reports PROOF-86
    def test_a_report_folder_is_read_file_by_file(self, tmp_path):
        root = _project(tmp_path, [{
            'name': 'dotnet',
            'run': ('mkdir -p {report} && cp one.trx {report}/one.trx '
                    '&& cp two.trx {report}/two.trx'),
            'report': '.purlin/runtime/reports/out', 'format': 'trx',
            'files': ['tests/*.cs']}], spec=_spec('login', 2))
        _write(root, 'tests/Pair.cs', (
            'namespace N {\n public class C {\n'
            '  // purlin: login PROOF-1\n  [Fact]\n  public void A() {}\n'
            '  // purlin: login PROOF-2\n  [Fact]\n  public void B() {}\n'
            ' }\n}\n'))
        _write(root, 'one.trx', _trx([('N.C', 'A', 'Passed')]))
        _write(root, 'two.trx', _trx([('N.C', 'B', 'Failed')]))
        _code, out = _run(root, '--all', '--test')
        assert _by_id(_evidence(root)) == {'PROOF-1': 'pass',
                                           'PROOF-2': 'fail'}, out

    # purlin: reports PROOF-87
    def test_a_report_of_a_dash_is_read_from_the_output(self, tmp_path):
        root = _fixture(tmp_path, 'go')
        (root / '.purlin').mkdir()
        _config(root, [{'name': 'go', 'run': 'cat report.json',
                        'report': '-', 'format': 'gotest',
                        'files': ['**/*_test.go']}])
        for name, text in GO_SPECS.items():
            _write(root, 'specs/shop/%s.md' % name, text)
        _run(root, '--all', '--test')
        cart = _results(_evidence(root, 'cart'))
        tax = _results(_evidence(root, 'tax'))
        assert cart[('PROOF-1', 'cart/cart_test.go::TestTotal')] == 'pass'
        assert tax[('PROOF-2', 'tax/tax_test.go::TestLookupPanics')] \
            == 'fail'
        assert cart[('PROOF-3', 'cart/cart_test.go::TestDiscount')] \
            == 'missing'

    # purlin: reports PROOF-18
    def test_a_suite_with_no_report_is_missing_evidence(self, tmp_path):
        root = _silent_project(tmp_path, '.purlin/runtime/reports/pytest.xml')
        code, out = _run(root, '--all', '--test')
        assert code == 1
        assert ('Evidence is missing: the pytest suite wrote no report at '
                '.purlin/runtime/reports/pytest.xml.') in out

    @staticmethod
    def _names_nothing(tmp_path, marker):
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', _WELL_FORMED + (
            '# purlin: %s\ndef test_x():\n    pass\n' % marker))
        code, out = _run(root, '--all', '--test')
        return code, out, out.splitlines()

    # purlin: reports PROOF-19
    def test_a_marker_naming_a_feature_no_spec_has_is_printed_and_exits_1(
            self, tmp_path):
        code, out, lines = self._names_nothing(tmp_path, 'nosuch PROOF-1')
        assert ('tests/test_login.py:13 names nosuch PROOF-1, which no spec '
                'has. Correct the comment, or run purlin:build to repair '
                'it.') in lines, out
        assert code == 1

    @staticmethod
    def _beside_a_complete_suite(tmp_path, broken):
        root = _project(tmp_path, [broken, suites.pytest_suite()])
        _write(root, 'tests/test_login.py', _WELL_FORMED)
        code, out = _run(root, '--all', '--test')
        lines = out.splitlines()
        return (code, out, [line for line in lines
                            if line.startswith('purlin: the ')],
                [line for line in lines if line.startswith('Running')])

    # purlin: reports PROOF-20
    def test_a_suite_with_no_run_is_left_out(self, tmp_path):
        code, out, said, started = self._beside_a_complete_suite(
            tmp_path, {'name': 'a', 'format': 'junit', 'files': ['x']})
        assert said == ['purlin: the a suite names no run command. '
                        'Fix the tests setting in .purlin/config.json, then '
                        'run purlin:test.'], out
        assert len(started) == 1 and started[0].startswith(
            'Running pytest: '), out
        assert code == 0, out

    # purlin: reports PROOF-88
    def test_a_suite_of_an_unknown_format_is_left_out(self, tmp_path):
        code, out, said, started = self._beside_a_complete_suite(
            tmp_path, {'name': 'b', 'run': 'x', 'format': 'tap',
                       'files': ['x']})
        assert said == ['purlin: the b suite names the format "tap", which '
                        'is not one of junit, trx, gotest, exit. Fix the tests '
                        'setting in .purlin/config.json, then run '
                        'purlin:test.'], out
        assert len(started) == 1 and started[0].startswith(
            'Running pytest: '), out
        assert code == 0, out

    @staticmethod
    def _suites_read(tmp_path, tests):
        """`(names, problems)` of the suites a settings file's `tests`
        holding `tests` is read as."""
        root = _project(tmp_path, tests)
        read, problems = markers.read_suites(str(root))
        return [suite.name for suite in read], problems

    # purlin: reports PROOF-108
    def test_a_tests_setting_that_is_not_a_list_is_no_suite(self, tmp_path):
        assert self._suites_read(tmp_path, {}) == (
            [], ['"tests" in .purlin/config.json is not a list'])

    @staticmethod
    def _report_written(tmp_path, command):
        """Run a pytest suite whose `command` writes its report."""
        root = _project(tmp_path, [{
            'name': 'pytest', 'run': command,
            'report': '.purlin/runtime/reports/pytest.xml',
            'format': 'junit', 'files': ['tests/test_*.py']}])
        _write(root, 'tests/test_login.py', _WELL_FORMED)
        return _run(root, '--all', '--test')

    # purlin: reports PROOF-114
    def test_a_report_not_in_its_format_is_missing_evidence(self, tmp_path):
        code, out = self._report_written(
            tmp_path, "mkdir -p .purlin/runtime/reports && "
                      "printf 'not xml' > {report}")
        assert ('Evidence is missing: the pytest suite wrote a report at '
                '.purlin/runtime/reports/pytest.xml that is not junit: '
                'syntax error: line 1, column 0') in out, out
        assert code == 1, out


# ---------------------------------------------------------------------------
# Comments that are nearly a marker
# ---------------------------------------------------------------------------

MARKERS_SCRIPT = os.path.join(REPO, 'scripts', 'mcp', 'purlin', 'markers.py')


def _near_misses(root, *args):
    done = subprocess.run(
        [sys.executable, MARKERS_SCRIPT] + list(args or (
            '--near-misses', '--project-root', str(root))),
        capture_output=True, encoding='utf-8', cwd=str(root))
    return done.returncode, done.stdout, done.stderr


def _listed(tmp_path, comment, more_specs=(), spec=LOGIN_SPEC):
    """The near misses listed for a `login` project whose test file carries
    `comment` on its first line, above a test."""
    root = _project(tmp_path, [suites.pytest_suite()], spec=spec,
                    more_specs=more_specs)
    _write(root, 'tests/test_login.py', comment + '\ndef test_a():\n'
                                                  '    pass\n')
    code, out, err = _near_misses(root)
    assert code == 0, err
    return json.loads(out)


def _fix_and_why(tmp_path, comment, spec=LOGIN_SPEC):
    (entry,) = _listed(tmp_path, comment, spec=spec)
    assert (entry['file'], entry['line'], entry['text']) == (
        'tests/test_login.py', 1, comment)
    return entry['fix'], entry['why']


class TestNearMisses:

    # purlin: reports PROOF-28
    def test_a_near_miss_is_listed_as_json(self, tmp_path):
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', '# purln: login PROOF-1\n'
                                            'def test_a():\n    pass\n')
        code, out, err = _near_misses(root)
        (entry,) = json.loads(out)
        assert {key: entry[key] for key in ('file', 'line', 'text', 'fix')} \
            == {'file': 'tests/test_login.py', 'line': 1,
                'text': '# purln: login PROOF-1',
                'fix': '# purlin: login PROOF-1'}, out
        assert '`purln`' in entry['why'], entry
        assert code == 0, err

    # purlin: reports PROOF-35
    def test_a_feature_one_character_off(self, tmp_path):
        assert _fix_and_why(tmp_path, '# purlin: logn PROOF-1') == (
            '# purlin: login PROOF-1',
            '`logn` is one character from the feature `login`.')

    # purlin: reports PROOF-37
    def test_an_id_one_character_from_several_is_not_a_near_miss(
            self, tmp_path):
        assert _listed(tmp_path, '# purlin: login PROOF-4') == []

    # purlin: reports PROOF-125
    def test_a_feature_holding_a_character_no_name_may_has_no_fix(
            self, tmp_path):
        assert _fix_and_why(tmp_path, '# purlin: sample.age PROOF-1') == (
            None,
            "`sample.age` holds a character a spec's name cannot: a name "
            "holds letters, digits, `_` and `-`.")

# ---------------------------------------------------------------------------
# The captures are what the tools write today
# ---------------------------------------------------------------------------

def _shape(cases, root):
    return sorted((reports._normalise_file(root, c.file or '') or '',
                   c.classname, c.name, c.outcome) for c in cases)


@pytest.fixture(scope='module')
def node_project(tmp_path_factory):
    """A project with jest, jest-junit and vitest installed, or a skip."""
    if not shutil.which('npm'):
        pytest.skip('npm is not on this machine')
    root = tmp_path_factory.mktemp('node')
    (root / 'package.json').write_text(json.dumps({
        'name': 'capture', 'private': True, 'devDependencies': {
            'jest': '^29.7.0', 'jest-junit': '^16.0.0',
            'vitest': '^3.2.0'}}), encoding='utf-8')
    done = subprocess.run(['npm', 'install', '--prefer-offline', '--no-fund',
                           '--loglevel=error'], cwd=str(root),
                          capture_output=True)
    if done.returncode != 0:
        pytest.skip('jest and vitest could not be installed here')
    return root


def test_jest_still_writes_what_the_capture_holds(node_project):
    from purlin import frameworks
    root = node_project / 'jest'
    shutil.copytree(os.path.join(FIXTURES, 'jest', 'tests'),
                    str(root / 'tests'))
    os.symlink(str(node_project / 'node_modules'), str(root / 'node_modules'))
    (root / 'package.json').write_text('{"name": "j", "private": true}',
                                       encoding='utf-8')
    entry = frameworks.entry_for('jest')
    suite = markers.Suite('jest', entry['run'], 'out.xml', 'junit',
                          entry['files'])
    subprocess.run(['bash', '-c', reports.command_for(suite, [], 'out.xml')],
                   cwd=str(root), capture_output=True)
    now, problem = reports.read_report('junit', str(root), 'out.xml')
    assert problem is None
    captured, _p = reports.read_report('junit', os.path.join(FIXTURES, 'jest'),
                                       'jest.xml')
    assert _shape(now, str(root)) == _shape(captured, '/home/dev/project')


def test_vitest_still_writes_what_the_capture_holds(node_project):
    from purlin import frameworks
    root = node_project / 'vitest'
    shutil.copytree(os.path.join(FIXTURES, 'vitest', 'tests'),
                    str(root / 'tests'))
    os.symlink(str(node_project / 'node_modules'), str(root / 'node_modules'))
    (root / 'package.json').write_text('{"name": "v", "private": true}',
                                       encoding='utf-8')
    entry = frameworks.entry_for('vitest')
    suite = markers.Suite('vitest', entry['run'], 'out.xml', 'junit',
                          entry['files'])
    subprocess.run(['bash', '-c', reports.command_for(suite, [], 'out.xml')],
                   cwd=str(root), capture_output=True)
    now, problem = reports.read_report('junit', str(root), 'out.xml')
    assert problem is None
    captured, _p = reports.read_report(
        'junit', os.path.join(FIXTURES, 'vitest'), 'vitest.xml')
    assert _shape(now, str(root)) == _shape(captured, '/home/dev/project')


def test_dotnet_still_writes_what_the_capture_holds(tmp_path):
    if not shutil.which('dotnet'):
        pytest.skip('dotnet is not on this machine')
    from purlin import frameworks
    root = _fixture(tmp_path, 'dotnet')
    entry = frameworks.entry_for('dotnet')
    suite = markers.Suite('dotnet', entry['run'], 'out', 'trx',
                          entry['files'])
    done = subprocess.run(
        ['bash', '-c', reports.command_for(suite, [], 'out')],
        cwd=str(root), capture_output=True,
        env=dict(os.environ, DOTNET_CLI_TELEMETRY_OPTOUT='1',
                 DOTNET_NOLOGO='1'))
    now, problem = reports.read_report('trx', str(root), 'out')
    if problem and b'NU1' in (done.stdout + done.stderr):
        pytest.skip('the xunit packages could not be restored here')
    assert problem is None
    captured, _p = reports.read_report(
        'trx', os.path.join(FIXTURES, 'dotnet'), 'dotnet.trx')
    assert _shape(now, str(root)) == _shape(captured, '/home/dev/project')


def test_go_still_writes_what_the_capture_holds(tmp_path):
    if not shutil.which('go'):
        pytest.skip('go is not on this machine')
    from purlin import frameworks
    root = _fixture(tmp_path, 'go')
    entry = frameworks.entry_for('go')
    done = subprocess.run(['bash', '-c', entry['run']], cwd=str(root),
                          capture_output=True, encoding='utf-8')
    now, problem = reports.read_report('gotest', str(root), '-', done.stdout)
    assert problem is None
    captured, _p = reports.read_report(
        'gotest', os.path.join(FIXTURES, 'go'), 'report.json')
    assert sorted((c.package, c.name, c.outcome) for c in now) == sorted(
        (c.package, c.name, c.outcome) for c in captured)


# ---------------------------------------------------------------------------
# A JavaScript title as the string it makes
# ---------------------------------------------------------------------------

_BUS_SPEC = _spec('bus', 2)


def _canned(tmp_path, source, cases, spec=LOGIN_SPEC, feature='login',
            path='tests/login.test.ts'):
    """A project whose one suite copies a canned JUnit report naming
    `cases`, each `(name, passed)`, for the test file `source`. `(root, exit
    code, output)` of `--all --test`."""
    root = _project(tmp_path, [{
        'name': 'vitest', 'run': 'cp canned.xml {report}',
        'report': '.purlin/runtime/reports/vitest.xml',
        'format': 'junit', 'files': ['tests/*.test.ts']}],
        spec=spec, feature=feature)
    _write(root, path, source)
    body = ''.join(
        '<testcase classname="%s" name="%s">%s</testcase>' % (
            path, name.replace('&', '&amp;').replace('>', '&gt;')
            .replace("'", '&apos;'), '' if passed else '<failure/>')
        for name, passed in cases)
    _write(root, 'canned.xml', '<testsuites><testsuite name="x">%s'
           '</testsuite></testsuites>' % body)
    code, out = _run(root, '--all', '--test')
    return root, code, out


class TestAJavaScriptTitle:

    # purlin: reports PROOF-126
    def test_an_escaped_apostrophe_is_read_as_the_apostrophe(self, tmp_path):
        root, _code, out = _canned(tmp_path, (
            "describe('bus', () => {\n"
            "  // purlin: bus PROOF-1\n"
            "  it('a tap after the node\\'s own gain', () => {});\n"
            "});\n"), [("bus > a tap after the node's own gain", True)],
            spec=_BUS_SPEC, feature='bus', path='tests/bus.test.ts')
        assert _by_id(_evidence(root, 'bus'))['PROOF-1'] == 'pass', out

    # purlin: reports PROOF-127
    def test_pieces_joined_with_a_plus_are_one_title(self, tmp_path):
        root, _code, out = _canned(tmp_path, (
            "describe('bus', () => {\n"
            "  // purlin: bus PROOF-1\n"
            "  test(\n"
            "    'every route is ' + 'forwarded to it '\n"
            "    + '',\n"
            "    () => {});\n"
            "});\n"), [('bus > every route is forwarded to it', True)],
            spec=_BUS_SPEC, feature='bus', path='tests/bus.test.ts')
        assert _by_id(_evidence(root, 'bus'))['PROOF-1'] == 'pass', out

    # purlin: reports PROOF-128
    def test_a_filled_template_title_is_named_and_not_tied(self, tmp_path):
        _root, code, out = _canned(tmp_path, (
            "const name = 'x';\n"
            "\n"
            "// purlin: login PROOF-1\n"
            "it(`greets ${name}`, () => {});\n"), [('greets x', True)],
            spec=_spec('login', 1))
        lines = out.splitlines()
        assert ("tests/login.test.ts:4: the test's title is not one plain "
                'string, so its result cannot be matched. Write it as one '
                'string.') in lines, out
        assert 'Markers: 0 tied to a test, 1 not tied.' in lines, out
        assert code == 1, out

    # purlin: reports PROOF-129
    def test_a_variable_title_takes_no_marker_of_a_later_test(self, tmp_path):
        root, _code, out = _canned(tmp_path, (
            "const title = 'first';\n"
            "// purlin: login PROOF-1\n"
            "it(title, () => {});\n"
            "// purlin: login PROOF-2\n"
            "it('second', () => {});\n"),
            [('first', True), ('second', True)], spec=_spec('login', 2))
        assert _results(_evidence(root)) == {
            ('PROOF-1', ''): 'missing',
            ('PROOF-2', 'tests/login.test.ts::second'): 'pass'}, out
