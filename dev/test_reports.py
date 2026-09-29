"""Tests for how a test's result reaches its proof: the markers, the reports, the tie.

The reports are real. pytest and the shell scripts run here in temporary
projects, and the JUnit XML, the TRX and the exit codes they leave are what
is read. Jest, Vitest and `dotnet test` reports are captured under
`dev/fixtures/reports/`, each beside the test source it was written for; the
tests at the end of this file run those tools again where they are installed
and check that they still write what the capture holds. The Go stream is the
one real `go test -json` printed over the two packages beside it. The run of
that module through the command init writes is in `dev/test_init_scaffold.py`.
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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

LOGIN_SPEC = '''# Feature: login

> Scope: src/

## Rules

- RULE-1: a rule with a proof
- RULE-2: a second rule
- RULE-3: a third rule

## Proof

- PROOF-1 (RULE-1): observe one
- PROOF-2 (RULE-2): observe two
- PROOF-3 (RULE-3): observe three
'''


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
    (root / '.purlin' / 'config.json').write_text(json.dumps(
        {'gate': 'passed', 'mutation_engine': 'none', 'tests': tests}),
        encoding='utf-8')
    (root / 'specs' / 'a' / ('%s.md' % feature)).write_text(
        spec, encoding='utf-8')
    for name, text in more_specs:
        (root / 'specs' / 'a' / ('%s.md' % name)).write_text(
            text, encoding='utf-8')
    return root


def _results(section):
    """`{(id, test): result}` for one evidence section."""
    return {(entry['id'], entry['test']): entry['result']
            for entry in section['proofs']}


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


# ---------------------------------------------------------------------------
# Markers
# ---------------------------------------------------------------------------

class TestTheMarker:

    # purlin: reports PROOF-1
    def test_every_comment_syntax_is_read_and_a_bad_one_is_named(self):
        text = '\n'.join([
            '# purlin: login PROOF-1', '// purlin: login PROOF-2',
            '-- purlin: login PROOF-3', '; purlin: login PROOF-4',
            '% purlin: login PROOF-5', "' purlin: login PROOF-6",
            '/* purlin: login RULE-7 */', '<!-- purlin: login PROOF-8 -->',
            '# purlin: login']) + '\n'
        found, malformed = markers.comment_markers(text, '.txt')
        assert [(m.feature, m.id, m.line) for m in found] == [
            ('login', 'PROOF-1', 1), ('login', 'PROOF-2', 2),
            ('login', 'PROOF-3', 3), ('login', 'PROOF-4', 4),
            ('login', 'PROOF-5', 5), ('login', 'PROOF-6', 6),
            ('login', 'RULE-7', 7), ('login', 'PROOF-8', 8)]
        assert malformed == [(9, '# purlin: login')]
        scan = {'tests/x.txt': markers.read_text('tests/x.txt', text, 'exit')}
        assert reports.malformed_lines(scan) == [(
            'purlin: tests/x.txt:9 is not a marker; write purlin: <feature> '
            'PROOF-<n>')]
        # A marker after code on the same line is not a whole-line comment:
        # it is neither read nor named as a bad marker.
        after_code = 'x = 1  # purlin: login PROOF-1\n'
        for ext in ('.txt', '.py'):
            assert markers.comment_markers(after_code, ext) == ([], []), ext

    # purlin: reports PROOF-2
    def test_a_marker_in_a_string_or_a_here_document_is_not_read(self):
        python = ('BODY = """\n# purlin: login PROOF-1\n"""\n\n'
                  '# purlin: login PROOF-1\ndef test_x():\n    pass\n')
        found, _bad = markers.comment_markers(python, '.py')
        assert [(m.id, m.line) for m in found] == [('PROOF-1', 5)]
        shell = ("cat > other.sh <<'EOF'\n# purlin: login PROOF-1\nEOF\n"
                 '# purlin: login PROOF-2\nexit 0\n')
        found, _bad = markers.comment_markers(shell, '.sh')
        assert [m.id for m in found] == ['PROOF-2']

    # purlin: reports PROOF-3
    def test_the_globs_name_the_files_a_suite_reads(self, tmp_path):
        paths = ['dev/test_a.py', 'dev/sub/test_b.py', 'a/b/c.test.ts']
        assert [p for p in paths if markers.glob_match(p, 'dev/test_*.py')] \
            == ['dev/test_a.py']
        assert [p for p in paths if markers.glob_match(p, '**/*.test.ts')] \
            == ['a/b/c.test.ts']
        assert [p for p in paths if markers.glob_match(p, 'test_*.py')] \
            == ['dev/test_a.py', 'dev/sub/test_b.py']
        # `?` is exactly one character, never a `/`; `**` may be no folder.
        assert [p for p in paths + ['dev/test_ab.py', 'dev/test_/.py']
                if markers.glob_match(p, 'dev/test_?.py')] == ['dev/test_a.py']
        assert markers.glob_match('x.py', '**/*.py')
        assert markers.glob_match('dev/test_a.py', 'dev/**/test_*.py')
        root = tmp_path / 'p'
        _write(root, 'tests/test_a.py', '# purlin: login PROOF-1\n'
                                        'def test_a():\n    pass\n')
        _write(root, 'other/test_b.py', '# purlin: login PROOF-2\n'
                                        'def test_b():\n    pass\n')
        first = markers.Suite('first', 'x', None, 'junit', ['tests/*.py'])
        second = markers.Suite('second', 'x', None, 'junit', ['**/*.py'])
        files = markers.test_files(str(root), [first, second])
        assert {path: suite.name for path, suite in files.items()} == {
            'tests/test_a.py': 'first', 'other/test_b.py': 'second'}
        assert set(markers.scan(str(root), [first])) == {'tests/test_a.py'}

    # purlin: reports PROOF-6
    def test_each_language_declares_its_tests(self):
        python = markers.python_tests(
            'def helper():\n    pass\n\ndef test_a():\n    pass\n\n'
            'class TestB:\n    def test_c(self):\n        pass\n'
            '    def helper(self):\n        pass\n')
        assert [(t.name, t.scopes) for t in python] == [
            ('test_a', []), ('test_c', ['TestB'])]
        with open(os.path.join(FIXTURES, 'vitest', 'tests', 'login.test.ts'),
                  encoding='utf-8') as handle:
            js = markers.js_tests(handle.read())
        assert [(t.name, t.scopes) for t in js] == [
            ('accepts', []), ('same name', ['outer', 'inner']),
            ('same name', ['outer']), ('skipped', ['outer']),
            ('param %i', ['outer'])]
        with open(os.path.join(FIXTURES, 'dotnet', 'App.Tests',
                               'GreetingTests.cs'), encoding='utf-8') as handle:
            cs = markers.cs_tests(handle.read())
        assert [(t.name, t.scopes, t.namespace) for t in cs] == [
            ('GreetsByName', ['GreetingTests'], 'App.Tests'),
            ('Param', ['GreetingTests'], 'App.Tests'),
            ('Skipped', ['GreetingTests'], 'App.Tests'),
            ('Inner', ['GreetingTests', 'Nested'], 'App.Tests')]
        with open(os.path.join(FIXTURES, 'go', 'cart', 'cart_test.go'),
                  encoding='utf-8') as handle:
            go = markers.go_tests(handle.read())
        assert [t.name for t in go] == ['TestTotal', 'TestParse',
                                        'TestDiscount', 'TestTotalIsWrong']
        # The other three C# attributes declare a test, and a method with no
        # attribute does not; a title that is not a literal is no test; nor
        # is a Go function that is not `func TestX(t *testing.T)`.
        cs = markers.cs_tests(
            'namespace N {\n public class C {\n  [Test]\n  public void A() {}\n'
            '  [TestCase(1)]\n  public void B(int x) {}\n  [TestMethod]\n'
            '  public void D() {}\n  public void Helper() {}\n }\n}\n')
        assert [(t.name, t.scopes, t.namespace) for t in cs] == [
            ('A', ['C'], 'N'), ('B', ['C'], 'N'), ('D', ['C'], 'N')]
        js = markers.js_tests('const name = "x";\nit(name, () => {});\n'
                              'test("lit", () => {});\n')
        assert [t.name for t in js] == ['lit']
        go = markers.go_tests(
            'func helper(t *testing.T) {}\nfunc TestA(t *testing.T) {}\n'
            'func BenchmarkB(b *testing.B) {}\nfunc TestLike(n int) {}\n')
        assert [t.name for t in go] == ['TestA']


# ---------------------------------------------------------------------------
# Reading the four formats
# ---------------------------------------------------------------------------

class TestTheReports:

    # purlin: reports PROOF-7
    def test_the_junit_pytest_writes(self, tmp_path):
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
        assert sorted((c.classname, c.name, c.outcome) for c in cases) == [
            ('App.Tests.GreetingTests', 'GreetsByName', 'pass'),
            ('App.Tests.GreetingTests', 'Param', 'fail'),
            ('App.Tests.GreetingTests', 'Param', 'pass'),
            ('App.Tests.GreetingTests', 'Skipped', 'skip'),
            ('App.Tests.GreetingTests+Nested', 'Inner', 'pass'),
            ('Other.Tests.GreetingTests', 'GreetsByName', 'fail')]
        # The outcomes the capture holds none of: three more that fail, and
        # one that is none of the known words and so is skipped.
        cases = reports.read_trx(_trx([
            ('A.T', 'E', 'Error'), ('A.T', 'T', 'Timeout'),
            ('A.T', 'B', 'Aborted'), ('A.T', 'I', 'Inconclusive')]))
        assert [(c.classname, c.name, c.outcome) for c in cases] == [
            ('A.T', 'E', 'fail'), ('A.T', 'T', 'fail'), ('A.T', 'B', 'fail'),
            ('A.T', 'I', 'skip')]

    # purlin: reports PROOF-9
    def test_the_stream_go_test_prints(self):
        with open(os.path.join(FIXTURES, 'go', 'report.json'),
                  encoding='utf-8') as handle:
            text = handle.read()
        cases = reports.read_gotest(text + 'ok  \texample.com/shop 0.1s\n')
        assert [(c.name, c.outcome) for c in cases] == [
            ('TestRate', 'pass'), ('TestLookupPanics', 'fail'),
            ('TestTotal', 'pass'), ('TestParse/empty', 'fail'),
            ('TestParse/one', 'pass'), ('TestParse', 'fail'),
            ('TestDiscount', 'skip'), ('TestTotalIsWrong', 'fail')]
        assert 'TestAfterThePanic' not in {c.name for c in cases}
        assert [c.package for c in cases] == (
            ['example.com/shop/tax'] * 2 + ['example.com/shop/cart'] * 6)


# ---------------------------------------------------------------------------
# The tie
# ---------------------------------------------------------------------------

PYTEST_SUITE = markers.Suite('pytest', 'x', 'report.xml', 'junit',
                             ['tests/test_*.py'])


class TestTheTie:

    # purlin: reports PROOF-10
    def test_each_report_finds_the_file_of_its_case(self, tmp_path):
        root, cases = _pytest_run(tmp_path, (
            'class TestGroup:\n'
            '    # purlin: login PROOF-1\n'
            '    def test_same(self):\n        pass\n'))
        (outcomes, _problems), _marked = _tie(root, PYTEST_SUITE, cases)
        assert outcomes == {('tests/test_login.py', 3): ['pass']}
        # A case whose class names no marked file is tied to nothing.
        stray = reports.Case('test_same', 'fail', 'tests.test_elsewhere')
        assert _tie(root, PYTEST_SUITE, cases + [stray])[0] == (outcomes, [])

        for tool, report in (('vitest', 'vitest.xml'), ('jest', 'jest.xml')):
            root = _fixture(tmp_path, tool)
            suite = markers.Suite(tool, 'x', report, 'junit',
                                  ['tests/*.test.*'])
            cases, _problem = reports.read_report('junit', str(root), report)
            (outcomes, _p), marked = _tie(root, suite, cases)
            (path,) = marked
            assert path.startswith('tests/login.test.')
            assert _marker_results(marked, outcomes)[('login', 'PROOF-1')] \
                == 'pass'

        root = _fixture(tmp_path, 'dotnet')
        suite = markers.Suite('dotnet', 'x', 'dotnet.trx', 'trx', ['**/*.cs'])
        cases, _problem = reports.read_report('trx', str(root), 'dotnet.trx')
        (outcomes, problems), _marked = _tie(root, suite, cases)
        assert problems == []
        assert outcomes[('App.Tests/GreetingTests.cs', 7)] == ['pass']
        assert outcomes[('App.Tests/OtherGreetingTests.cs', 8)] == ['fail']
        stray = reports.Case('GreetsByName', 'fail',
                             'Nowhere.Tests.MissingTests')
        assert _tie(root, suite, cases + [stray])[0] == (outcomes, [])

        root = _fixture(tmp_path, 'go')
        suite = markers.Suite('go', 'x', 'report.json', 'gotest',
                              ['**/*_test.go'])
        cases, _problem = reports.read_report('gotest', str(root),
                                              'report.json')
        (outcomes, _p), _marked = _tie(root, suite, cases)
        assert outcomes[('cart/cart_test.go', 6)] == ['pass']
        assert outcomes[('tax/tax_test.go', 6)] == ['pass']
        stray = reports.Case('TestTotal', 'fail',
                             package='example.com/shop/nowhere')
        assert _tie(root, suite, cases + [stray])[0][0] == outcomes

    # purlin: reports PROOF-11
    def test_every_case_of_a_parametrised_test_must_pass(self, tmp_path):
        body = ('import pytest\n\n'
                '# purlin: login PROOF-1\n'
                '@pytest.mark.parametrize("x", [1, %s])\n'
                'def test_values(x):\n    assert x > 0\n')
        root, cases = _pytest_run(tmp_path, body % '2')
        (outcomes, _p), marked = _tie(root, PYTEST_SUITE, cases)
        assert _marker_results(marked, outcomes) == {('login', 'PROOF-1'):
                                                     'pass'}
        shutil.rmtree(str(root))
        root, cases = _pytest_run(tmp_path, body % '-2')
        (outcomes, _p), marked = _tie(root, PYTEST_SUITE, cases)
        assert _marker_results(marked, outcomes) == {('login', 'PROOF-1'):
                                                     'fail'}

        root = _fixture(tmp_path, 'dotnet')
        suite = markers.Suite('dotnet', 'x', 'dotnet.trx', 'trx', ['**/*.cs'])
        cases, _problem = reports.read_report('trx', str(root), 'dotnet.trx')
        (outcomes, _p), marked = _tie(root, suite, cases)
        results = _marker_results(marked, outcomes)
        assert results[('greeting', 'PROOF-2')] == 'fail'

        root = _fixture(tmp_path, 'go')
        suite = markers.Suite('go', 'x', 'report.json', 'gotest',
                              ['**/*_test.go'])
        cases, _problem = reports.read_report('gotest', str(root),
                                              'report.json')
        (outcomes, _p), marked = _tie(root, suite, cases)
        assert _marker_results(marked, outcomes)[('cart', 'PROOF-2')] == 'fail'

        root = _fixture(tmp_path, 'vitest')
        suite = markers.Suite('vitest', 'x', 'vitest.xml', 'junit',
                              ['tests/*.test.ts'])
        cases, _problem = reports.read_report('junit', str(root), 'vitest.xml')
        (outcomes, _p), marked = _tie(root, suite, cases)
        assert _marker_results(marked, outcomes)[('login', 'PROOF-4')] == 'pass'

    # purlin: reports PROOF-12
    def test_a_nested_title_is_narrowed_by_its_outer_parts(self, tmp_path):
        for tool, report in (('vitest', 'vitest.xml'), ('jest', 'jest.xml')):
            root = _fixture(tmp_path, tool)
            suite = markers.Suite(tool, 'x', report, 'junit',
                                  ['tests/*.test.*'])
            cases, _problem = reports.read_report('junit', str(root), report)
            assert any(c.outcome == 'fail' for c in cases)
            (outcomes, problems), marked = _tie(root, suite, cases)
            assert problems == []
            assert _marker_results(marked, outcomes)[('login', 'PROOF-2')] \
                == 'pass', tool
        root, cases = _pytest_run(tmp_path, (
            'class TestGroup:\n'
            '    # purlin: login PROOF-1\n'
            '    def test_same(self):\n        pass\n\n'
            'class TestOther:\n'
            '    def test_same(self):\n        assert False\n'))
        (outcomes, problems), marked = _tie(root, PYTEST_SUITE, cases)
        assert problems == []
        assert _marker_results(marked, outcomes) == {('login', 'PROOF-1'):
                                                     'pass'}
        # Two C# classes in one file, each with a test `Same`: the TRX
        # result of each is narrowed to its own class.
        root = tmp_path / 'cs'
        _write(root, 'tests/Twice.cs', (
            'namespace N {\n public class First {\n'
            '  // purlin: login PROOF-3\n  [Fact]\n  public void Same() {}\n'
            ' }\n public class Second {\n  [Fact]\n  public void Same() {}\n'
            ' }\n}\n'))
        suite = markers.Suite('dotnet', 'x', 'r.trx', 'trx', ['**/*.cs'])
        cases = reports.read_trx(_trx([('N.First', 'Same', 'Passed'),
                                       ('N.Second', 'Same', 'Failed')]))
        (outcomes, problems), marked = _tie(root, suite, cases)
        assert problems == []
        assert _marker_results(marked, outcomes) == {('login', 'PROOF-3'):
                                                     'pass'}

    # purlin: reports PROOF-13
    def test_a_case_that_is_two_tests_is_counted_for_neither(self, tmp_path):
        root, cases = _pytest_run(tmp_path, (
            '# purlin: login PROOF-1\n'
            'def test_x():\n    pass\n\n'
            'def test_x():\n    pass\n'))
        (outcomes, problems), marked = _tie(root, PYTEST_SUITE, cases)
        assert problems == [
            "purlin: the report's test_x matches 2 tests in "
            'tests/test_login.py, so its result is not counted']
        assert _marker_results(marked, outcomes) == {('login', 'PROOF-1'):
                                                     'not run'}
        # The same file through a run: the run prints that line.
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', (
            '# purlin: login PROOF-1\ndef test_x():\n    pass\n\n'
            'def test_x():\n    pass\n'))
        code, out = _run(root, '--all', '--test')
        assert problems[0] in out.splitlines(), out
        assert code == 1, out

    # purlin: reports PROOF-14
    def test_what_each_outcome_reads(self, tmp_path):
        root, cases = _pytest_run(tmp_path, (
            'import pytest\n\n'
            '# purlin: login PROOF-1\ndef test_passes():\n    pass\n\n'
            '# purlin: login PROOF-2\ndef test_fails():\n    assert 0\n\n'
            '# purlin: login PROOF-3\n@pytest.mark.skip(reason="later")\n'
            'def test_skipped():\n    pass\n\n'
            '@pytest.fixture\ndef broken():\n    raise RuntimeError("x")\n\n'
            '# purlin: login PROOF-4\ndef test_errors(broken):\n    pass\n'))
        (outcomes, _p), marked = _tie(root, PYTEST_SUITE, cases)
        assert _marker_results(marked, outcomes) == {
            ('login', 'PROOF-1'): 'pass', ('login', 'PROOF-2'): 'fail',
            ('login', 'PROOF-3'): 'not run', ('login', 'PROOF-4'): 'fail'}
        (outcomes, _p), marked = _tie(root, PYTEST_SUITE, cases[1:])
        assert _marker_results(marked, outcomes)[('login', 'PROOF-1')] \
            == 'not run'


# ---------------------------------------------------------------------------
# Through a run
# ---------------------------------------------------------------------------

class TestThroughARun:

    # purlin: reports PROOF-4
    def test_markers_above_a_decorator_and_two_on_one_test(self, tmp_path):
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', (
            'import pytest\n\n'
            '# purlin: login PROOF-3\n'
            '@pytest.mark.parametrize("x", [1])\n'
            'def test_decorated(x):\n    assert x\n\n'
            '# purlin: login PROOF-1\n'
            '# purlin: login PROOF-2\n'
            'def test_two():\n    pass\n'))
        code, out = _run(root, '--all', '--test')
        assert code == 0, out
        assert _results(_evidence(root)) == {
            ('PROOF-1', 'tests/test_login.py::test_two'): 'pass',
            ('PROOF-2', 'tests/test_login.py::test_two'): 'pass',
            ('PROOF-3', 'tests/test_login.py::test_decorated'): 'pass'}
        # A blank line and an ordinary comment between marker and test still
        # tie, and a failing test's result counts for each of its markers,
        # each pair written once.
        _write(root, 'tests/test_login.py', (
            'import pytest\n\n'
            '# purlin: login PROOF-3\n\n# an ordinary comment\n'
            '@pytest.mark.parametrize("x", [1])\n'
            'def test_decorated(x):\n    assert x\n\n'
            '# purlin: login PROOF-1\n'
            '# purlin: login PROOF-2\n'
            'def test_two():\n    assert False\n'))
        code, out = _run(root, '--all', '--test')
        assert code == 1, out
        assert len(_evidence(root)['proofs']) == 3
        assert _results(_evidence(root)) == {
            ('PROOF-1', 'tests/test_login.py::test_two'): 'fail',
            ('PROOF-2', 'tests/test_login.py::test_two'): 'fail',
            ('PROOF-3', 'tests/test_login.py::test_decorated'): 'pass'}

    # purlin: reports PROOF-5
    def test_a_marker_above_nothing_is_tied_to_no_test(self, tmp_path):
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', (
            '# purlin: login PROOF-1\ndef test_one():\n    pass\n\n'
            '# purlin: login PROOF-2\ndef test_two():\n    pass\n\n'
            '# purlin: login PROOF-3\n'))
        code, out = _run(root, '--all', '--test')
        assert code == 1
        assert ('purlin: login PROOF-3 at tests/test_login.py:9 is tied to '
                'no test') in out
        assert ('Evidence is missing: 1 marker has no passing or failing '
                'result: login PROOF-3 at tests/test_login.py:9.') in out
        assert _results(_evidence(root)) == {
            ('PROOF-1', 'tests/test_login.py::test_one'): 'pass',
            ('PROOF-2', 'tests/test_login.py::test_two'): 'pass',
            ('PROOF-3', ''): 'missing'}

    # purlin: reports PROOF-15
    def test_an_exit_suite_runs_each_file_as_one_test(self, tmp_path):
        suite = suites.shell_suite(('tests/*.sh',))
        suite['run'] = 'echo "call: {files}" >> calls.txt; ' + suite['run']
        root = _project(tmp_path, [suite])
        _write(root, 'tests/good.sh', '#!/usr/bin/env bash\n'
               '# purlin: login PROOF-1\n# purlin: login PROOF-2\nexit 0\n')
        _write(root, 'tests/bad.sh', '#!/usr/bin/env bash\n'
               '# purlin: login PROOF-3\nexit 3\n')
        code, out = _run(root, '--all', '--test')
        assert code == 1
        assert 'Evidence is missing' not in out, out
        assert _results(_evidence(root)) == {
            ('PROOF-1', 'tests/good.sh::good.sh'): 'pass',
            ('PROOF-2', 'tests/good.sh::good.sh'): 'pass',
            ('PROOF-3', 'tests/bad.sh::bad.sh'): 'fail'}
        # The command ran once per script, given that one script alone.
        assert (root / 'calls.txt').read_text(encoding='utf-8').splitlines() \
            == ['call: tests/bad.sh', 'call: tests/good.sh']

    # purlin: reports PROOF-16
    def test_files_and_report_are_filled_in(self, tmp_path):
        suite = suites.pytest_suite()
        suite['run'] = ('printf "%s\\n" x {files} {report} >> args.txt; '
                        'echo "${BASH_VERSION:+bash}" > shell.txt; '
                        + suite['run'])
        other = LOGIN_SPEC.replace('# Feature: login', '# Feature: signup')
        root = _project(tmp_path, [suite], more_specs=(('signup', other),))
        _write(root, 'tests/test_login.py',
               '# purlin: login PROOF-1\ndef test_a():\n    pass\n')
        _write(root, 'tests/test_sign up.py',
               '# purlin: signup PROOF-1\ndef test_b():\n    pass\n')
        _run(root, '--feature', 'login', '--test')
        assert (root / 'args.txt').read_text(encoding='utf-8').split() == [
            'x', 'tests/test_login.py', '.purlin/runtime/reports/pytest.xml']
        (root / 'args.txt').unlink()
        _run(root, '--all', '--test')
        assert (root / 'args.txt').read_text(encoding='utf-8').split() == [
            'x', '.purlin/runtime/reports/pytest.xml']
        # A path holding a space arrives as one argument, and the command
        # runs through bash.
        (root / 'args.txt').unlink()
        _run(root, '--feature', 'signup', '--test')
        assert (root / 'args.txt').read_text(
            encoding='utf-8').splitlines() == [
            'x', 'tests/test_sign up.py', '.purlin/runtime/reports/pytest.xml']
        assert (root / 'shell.txt').read_text(encoding='utf-8') == 'bash\n'

    # purlin: reports PROOF-17
    def test_a_stale_report_is_never_read(self, tmp_path):
        suite = {'name': 'pytest', 'run': 'true',
                 'report': '.purlin/runtime/reports/pytest.xml',
                 'format': 'junit', 'files': ['tests/test_*.py']}
        root = _project(tmp_path, [suite])
        _write(root, 'tests/test_login.py',
               '# purlin: login PROOF-1\ndef test_a():\n    pass\n')
        _write(root, '.purlin/runtime/reports/pytest.xml',
               '<testsuite><testcase classname="tests.test_login" '
               'name="test_a"/></testsuite>')
        code, out = _run(root, '--all', '--test')
        assert code == 1
        assert 'wrote no report' in out
        assert not (root / '.purlin' / 'runtime' / 'reports'
                    / 'pytest.xml').exists()
        # An old report that is a folder is deleted too.
        suite['report'] = '.purlin/runtime/reports/out'
        (root / '.purlin' / 'config.json').write_text(json.dumps(
            {'gate': 'passed', 'mutation_engine': 'none', 'tests': [suite]}),
            encoding='utf-8')
        _write(root, '.purlin/runtime/reports/out/old.xml',
               '<testsuite><testcase classname="tests.test_login" '
               'name="test_a"/></testsuite>')
        code, out = _run(root, '--all', '--test')
        assert code == 1
        assert 'wrote no report at .purlin/runtime/reports/out' in out, out
        assert not (root / '.purlin' / 'runtime' / 'reports' / 'out').exists()

        folder = tmp_path / 'trx'
        (folder / 'out').mkdir(parents=True)
        for name in ('one.trx', 'two.trx'):
            shutil.copy(os.path.join(FIXTURES, 'dotnet', 'dotnet.trx'),
                        str(folder / 'out' / name))
        cases, problem = reports.read_report('trx', str(folder), 'out')
        assert problem is None and len(cases) == 12

        root = _fixture(tmp_path, 'go')
        cases, problem = reports.read_report(
            'gotest', str(root), '-',
            (root / 'report.json').read_text(encoding='utf-8'))
        assert problem is None and len(cases) == 8
        # Through a run: a suite whose command prints that stream, and whose
        # report is `-`, gives each Go test its result.
        (root / '.purlin').mkdir()
        (root / '.purlin' / 'config.json').write_text(json.dumps(
            {'gate': 'passed', 'mutation_engine': 'none', 'tests': [{
                'name': 'go', 'run': 'cat report.json', 'report': '-',
                'format': 'gotest', 'files': ['**/*_test.go']}]}),
            encoding='utf-8')
        for name, text in GO_SPECS.items():
            _write(root, 'specs/shop/%s.md' % name, text)
        _run(root, '--all', '--test')
        assert _results(_evidence(root, 'cart'))[
            ('PROOF-1', 'cart/cart_test.go::TestTotal')] == 'pass'
        assert _results(_evidence(root, 'tax'))[
            ('PROOF-2', 'tax/tax_test.go::TestLookupPanics')] == 'fail'

    # purlin: reports PROOF-18
    def test_a_suite_with_no_report_is_missing_evidence(self, tmp_path):
        suite = {'name': 'pytest', 'run': 'true',
                 'report': '.purlin/runtime/reports/pytest.xml',
                 'format': 'junit', 'files': ['tests/test_*.py']}
        root = _project(tmp_path, [suite])
        _write(root, 'tests/test_login.py',
               '# purlin: login PROOF-1\ndef test_a():\n    pass\n')
        code, out = _run(root, '--all', '--test')
        assert code == 1
        assert ('Evidence is missing: the pytest suite wrote no report at '
                '.purlin/runtime/reports/pytest.xml.') in out

    # purlin: reports PROOF-19
    def test_a_marker_naming_a_feature_no_spec_has_fails_the_run(
            self, tmp_path):
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', _WELL_FORMED + (
            '# purlin: nosuch PROOF-1\ndef test_x():\n    pass\n'))
        code, out = _run(root, '--all', '--test')
        lines = out.splitlines()
        wrong = ('purlin: nosuch PROOF-1 at tests/test_login.py:13 names a '
                 'feature no spec has')
        assert wrong in lines, out
        assert lines[lines.index(wrong) + 1] == (
            'Remove the comment, or write the proof it names.'), out
        assert 'Evidence is missing' not in out
        assert 'gate passed met: 3 of 3 rules' in out, out
        assert code == 1

        _write(root, 'tests/test_login.py', _WELL_FORMED + (
            '# purlin: nosuch PROOF-1\ndef test_x():\n    pass\n\n'
            '# purlin: other PROOF-2\ndef test_y():\n    pass\n'))
        code, out = _run(root, '--all', '--test')
        lines = out.splitlines()
        second = ('purlin: other PROOF-2 at tests/test_login.py:17 names a '
                  'feature no spec has')
        assert wrong in lines and second in lines, out
        assert lines[lines.index(second) + 1] == (
            'Remove each comment, or write the proof it names.'), out
        assert 'Remove the comment' not in out
        assert code == 1

    # purlin: reports PROOF-21
    def test_a_marker_naming_a_proof_no_spec_has_fails_the_run(
            self, tmp_path):
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', _WELL_FORMED + (
            '# purlin: login PROOF-9\ndef test_x():\n    pass\n'))
        code, out = _run(root, '--all', '--test')
        lines = out.splitlines()
        wrong = ('purlin: login PROOF-9 at tests/test_login.py:13 names a '
                 'proof no spec has')
        assert wrong in lines, out
        assert lines[lines.index(wrong) + 1] == (
            'Remove the comment, or write the proof it names.'), out
        assert code == 1

    # purlin: reports PROOF-22
    def test_a_marker_naming_a_rule_no_spec_has_fails_the_run(
            self, tmp_path):
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', _WELL_FORMED + (
            '# purlin: login RULE-9\ndef test_x():\n    pass\n'))
        code, out = _run(root, '--all', '--test')
        lines = out.splitlines()
        wrong = ('purlin: login RULE-9 at tests/test_login.py:13 names a '
                 'rule no spec has')
        assert wrong in lines, out
        assert lines[lines.index(wrong) + 1] == (
            'Remove the comment, or write the proof it names.'), out
        assert code == 1

    # purlin: reports PROOF-23
    def test_a_marker_naming_a_rule_that_has_proofs_fails_the_run(
            self, tmp_path):
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', _WELL_FORMED + (
            '# purlin: login RULE-1\ndef test_x():\n    pass\n'))
        code, out = _run(root, '--all', '--test')
        lines = out.splitlines()
        wrong = ('purlin: login RULE-1 at tests/test_login.py:13 names a '
                 'rule that has proofs; name one of them')
        assert wrong in lines, out
        assert lines[lines.index(wrong) + 1] == (
            'Remove the comment, or write the proof it names.'), out
        assert code == 1

    # purlin: reports PROOF-24
    def test_a_run_with_only_well_formed_markers_exits_0(self, tmp_path):
        root = _project(tmp_path, [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', _WELL_FORMED)
        code, out = _run(root, '--all', '--test')
        assert 'names a' not in out, out
        assert 'Remove the comment' not in out, out
        assert 'Remove each comment' not in out, out
        assert code == 0, out

    # purlin: reports PROOF-20
    def test_a_suite_missing_a_part_is_left_out(self, tmp_path):
        broken = [{'name': 'a', 'format': 'junit', 'files': ['x']},
                  {'name': 'b', 'run': 'x', 'format': 'tap', 'files': ['x']},
                  {'name': 'c', 'run': 'x', 'format': 'junit'}]
        found, problems = markers.read_suites('', {'tests': broken + [
            {'name': 'd', 'run': 'x', 'format': 'exit', 'files': ['x']}]})
        assert [suite.name for suite in found] == ['d']
        assert problems == [
            'the a suite names no run command',
            'the b suite names the format "tap", which is not one of junit, '
            'trx, gotest, exit',
            'the c suite names no files']
        # A run prints the three lines and runs only the complete suite.
        root = _project(tmp_path, broken + [suites.pytest_suite()])
        _write(root, 'tests/test_login.py', _WELL_FORMED)
        code, out = _run(root, '--all', '--test')
        lines = out.splitlines()
        assert ['purlin: %s.' % problem for problem in problems] == [
            line for line in lines if line.startswith('purlin: the ')], out
        assert [line for line in lines if line.startswith('Running')] == [
            'Running the pytest suite.'], out
        assert code == 0, out


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


