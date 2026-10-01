"""The heuristic spot tests: each check fires on a wrong test and stays silent on a right one."""

import io
import json
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_ROOT, 'scripts', 'review'))
sys.path.insert(0, _HERE)

import fake_claude  # noqa: E402
import plain_checks  # noqa: E402

AGE_PROOF = {'id': 'PROOF-1', 'text': 'has an age of `90` minutes'}
NO_VALUE = {'id': 'PROOF-1', 'text': 'the age is read'}


@pytest.fixture(autouse=True)
def own_claude(tmp_path, monkeypatch):
    """A fake `claude` under this test's own folder stands first on PATH."""
    directory = fake_claude.install(str(tmp_path / 'claude-bin'))
    monkeypatch.setenv('PATH', directory + os.pathsep + os.environ.get('PATH', ''))
    assert os.path.realpath(shutil.which('claude')).startswith(os.path.realpath(str(tmp_path)))
    return directory


def write(root, path, text):
    full = os.path.join(str(root), *path.split('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as handle:
        handle.write(textwrap.dedent(text).lstrip('\n'))
    return path


def findings(root, path, name, proof=NO_VALUE):
    test = {'file': path, 'name': name, 'source': ''}
    return [finding for _check, finding in
            plain_checks.check(str(root), 'age', proof, test) if finding]


APP = '''
def age(stamp, zone="UTC"):
    if zone == "Mars":
        raise ValueError("zone")
    return 90
'''


# purlin: plain_checks PROOF-1
def test_a_test_that_asserts_nothing_checks_nothing(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from src.age import age

        def test_age():
            age("2026-01-01")
    ''')
    assert findings(tmp_path, path, 'test_age') == [
        'tests/test_age.py::test_age: the test checks nothing.']


# purlin: plain_checks PROOF-3
def test_a_helper_from_another_file_may_assert(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    write(tmp_path, 'tests/helpers.py', '''
        from src.age import age

        def check_age():
            assert age("2026-01-01") == 90
    ''')
    path = write(tmp_path, 'tests/test_age.py', '''
        from tests.helpers import check_age

        def test_age():
            check_age()
    ''')
    assert findings(tmp_path, path, 'test_age') == []


# purlin: plain_checks PROOF-4
def test_a_test_that_only_expects_an_error_asserts(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        import pytest
        from src.age import age

        def test_bad_zone():
            with pytest.raises(ValueError): age("2026-01-01", zone="Mars")
    ''')
    assert findings(tmp_path, path, 'test_bad_zone') == []


# purlin: plain_checks PROOF-9
def test_a_value_compared_with_itself_cannot_fail(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from src.age import age

        def test_age():
            days = age("2026-01-01")
            assert days == days
    ''')
    assert findings(tmp_path, path, 'test_age') == [
        'tests/test_age.py::test_age: the check cannot fail: assert days == days.']


# purlin: plain_checks PROOF-10
def test_a_weak_but_failable_check_is_not_flagged(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from src.age import age

        def test_age():
            result = age("2026-01-01")
            assert result is not None
    ''')
    assert findings(tmp_path, path, 'test_age') == []


# purlin: plain_checks PROOF-11
def test_expect_true_to_be_true_cannot_fail(tmp_path):
    path = write(tmp_path, 'tests/age.test.ts', '''
        import { age } from "../src/age";

        test("age", () => {
          age("2026-01-01");
          expect(true).toBe(true);
        });
    ''')
    assert findings(tmp_path, path, 'age') == [
        'tests/age.test.ts::age: the check cannot fail: expect(true).toBe(true).']


# purlin: plain_checks PROOF-13
def test_an_except_that_only_passes_swallows_the_error(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from src.age import age

        def test_bad_zone():
            try:
                age("2026-01-01", zone="Mars")
            except ValueError:
                pass
    ''')
    found = findings(tmp_path, path, 'test_bad_zone')
    assert 'tests/test_age.py::test_bad_zone: the test swallows the error the code raises.' \
        in found


# purlin: plain_checks PROOF-14
def test_an_except_that_asserts_on_the_error_is_not_flagged(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from src.age import age

        def test_bad_zone():
            try:
                age("2026-01-01", zone="Mars")
            except ValueError as e:
                assert "zone" in str(e)
    ''')
    assert findings(tmp_path, path, 'test_bad_zone') == []


# purlin: plain_checks PROOF-17
def test_an_empty_catch_in_csharp_swallows_the_error(tmp_path):
    path = write(tmp_path, 'Tests/AgeTests.cs', '''
        using Xunit;

        public class AgeTests
        {
            [Fact]
            public void BadZone()
            {
                try
                {
                    Ages.Age("2026-01-01", "Mars");
                }
                catch { }
                Assert.NotNull(Ages.Zone);
            }
        }
    ''')
    assert findings(tmp_path, path, 'BadZone') == [
        'Tests/AgeTests.cs::BadZone: the test swallows the error the code raises.']


# purlin: plain_checks PROOF-18
def test_an_expected_value_from_the_code_under_test(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from src.age import age

        def test_age():
            s = "2026-01-01"
            expected = age(s)
            assert age(s) == expected
    ''')
    assert findings(tmp_path, path, 'test_age') == [
        'tests/test_age.py::test_age: the expected value comes from age(), the code under test.']


# purlin: plain_checks PROOF-19
def test_an_expected_value_from_another_function_is_not_flagged(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from src.age import age
        from src.calendar import days_between, today

        def test_age():
            s = "2026-01-01"
            assert age(s) == days_between(s, today)
    ''')
    assert findings(tmp_path, path, 'test_age') == []


# purlin: plain_checks PROOF-20
def test_an_expected_value_from_the_code_under_test_in_typescript(tmp_path):
    path = write(tmp_path, 'tests/age.test.ts', '''
        import { age } from "../src/age";

        test("age", () => {
          const s = "2026-01-01";
          const expected = age(s);
          expect(age(s)).toBe(expected);
        });
    ''')
    assert findings(tmp_path, path, 'age') == [
        'tests/age.test.ts::age: the expected value comes from age(), the code under test.']


# purlin: plain_checks PROOF-22
def test_a_patch_of_the_function_it_checks(tmp_path):
    write(tmp_path, 'app.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from unittest.mock import patch
        import app

        def test_age():
            s = "2026-01-01"
            with patch("app.age", return_value=90):
                assert app.age(s) == 90
    ''')
    assert findings(tmp_path, path, 'test_age') == [
        'tests/test_age.py::test_age: the test mocks age(), the function it checks.']


# purlin: plain_checks PROOF-23
def test_a_patch_of_a_dependency_is_not_flagged(tmp_path):
    write(tmp_path, 'app.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        import datetime
        from unittest.mock import patch
        import app

        def test_age():
            s = "2026-01-01"
            with patch("app.clock.now", return_value=datetime.datetime(2026, 1, 1)):
                assert app.age(s) == 90
    ''')
    assert findings(tmp_path, path, 'test_age') == []


# purlin: plain_checks PROOF-24
def test_a_spy_on_the_function_it_checks_in_typescript(tmp_path):
    path = write(tmp_path, 'tests/age.test.ts', '''
        import * as lib from "../src/age";

        test("age", () => {
          const s = "2026-01-01";
          jest.spyOn(lib, "age").mockReturnValue(90);
          expect(lib.age(s)).toBe(90);
        });
    ''')
    assert findings(tmp_path, path, 'age') == [
        'tests/age.test.ts::age: the test mocks age(), the function it checks.']


# purlin: plain_checks PROOF-25
def test_a_value_the_proof_names_and_the_file_never_holds(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from src.age import age

        def test_age():
            assert age("2026-01-01") > 60
    ''')
    assert findings(tmp_path, path, 'test_age', AGE_PROOF) == [
        'tests/test_age.py::test_age: the proof expects 90 and the test never checks it.']


# purlin: plain_checks PROOF-26
def test_the_same_number_written_another_way_is_held(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    path = write(tmp_path, 'tests/test_age.py', '''
        from src.age import age

        def test_age():
            minutes = age("2026-01-01")
            assert minutes == 90.0
    ''')
    assert findings(tmp_path, path, 'test_age', AGE_PROOF) == []


# purlin: plain_checks PROOF-27
def test_a_value_held_in_a_data_file_the_test_names(tmp_path):
    write(tmp_path, 'src/age.py', APP)
    write(tmp_path, 'tests/data/ages.json', '{"2026-01-01": 90}\n')
    path = write(tmp_path, 'tests/test_age.py', '''
        import json
        from src.age import age

        def test_age():
            with open("tests/data/ages.json") as handle:
                ages = json.load(handle)
            for stamp, minutes in ages.items():
                assert age(stamp) == minutes
    ''')
    with open(os.path.join(str(tmp_path), 'tests', 'test_age.py')) as handle:
        assert '90' not in handle.read()
    assert findings(tmp_path, path, 'test_age', AGE_PROOF) == []


# purlin: plain_checks PROOF-32
def test_an_empty_pair_of_backticks_names_no_value(tmp_path):
    write(tmp_path, 'src/intake.py', APP)
    path = write(tmp_path, 'tests/test_intake.py', '''
        import pytest
        from src.intake import intake

        def test_an_empty_barcode_is_refused():
            with pytest.raises(ValueError, match="barcode is required"):
                intake("")
    ''')
    proof = {'id': 'PROOF-1', 'text': 'an empty barcode `` is handed in; it is refused '
                                      'with `barcode is required`'}
    assert findings(tmp_path, path, 'test_an_empty_barcode_is_refused', proof) == []


def project(root, features, files):
    """A git project whose specs are `features` ({name: [proof text]}) and whose test files
    are `files` ({path: text}), with the tests setting given."""
    for name, proofs in features.items():
        lines = ['# Feature: %s' % name, '', '> Scope: src/%s.py' % name, '', '## Rules', '']
        lines += ['- RULE-%d: rule %d' % (n, n) for n in range(1, len(proofs) + 1)]
        lines += ['', '## Proof', '']
        lines += ['- PROOF-%d (RULE-%d): %s' % (n, n, text)
                  for n, text in enumerate(proofs, 1)]
        write(root, 'specs/%s.md' % name, '\n'.join(lines) + '\n')
        write(root, 'src/%s.py' % name, 'def %s():\n    return 90\n' % name)
    for path, text in files.items():
        write(root, path, text)
    write(root, '.purlin/config.json', json.dumps({'version': '0.10.0', 'tests': [
        {'name': 'pytest', 'run': 'python3 -m pytest {files} --junitxml={report}',
         'format': 'junit', 'files': ['tests/**/*.py']},
        {'name': 'shell', 'run': 'bash {files}', 'format': 'exit',
         'files': ['tests/**/*.sh']}]}))
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)


# purlin: plain_checks PROOF-28
def test_a_check_shell_is_not_read_for_is_named_once(tmp_path):
    project(tmp_path, {'login': ['logs in', 'logs out']}, {
        'tests/login_in.sh': '# purlin: login PROOF-1\n[ "$(./login)" = "in" ]\n',
        'tests/login_out.sh': '# purlin: login PROOF-2\n[ "$(./logout)" = "out" ]\n'})
    out = io.StringIO()
    plain_checks.check_project(str(tmp_path), out=out)
    lines = out.getvalue().splitlines()
    assert lines.count('The test replaces what it is testing is not read in shell tests.') == 1


# purlin: plain_checks PROOF-30
def test_the_spot_tests_start_no_claude(tmp_path, own_claude):
    project(tmp_path, {'age': ['has an age of `90` minutes'],
                       'login': ['logs in'], 'zone': ['reads `UTC`']}, {
        'tests/test_age.py': '# purlin: age PROOF-1\ndef test_age():\n    assert 90 == 90\n',
        'tests/test_login.py': '# purlin: login PROOF-1\ndef test_login():\n    pass\n',
        'tests/test_zone.py': ('# purlin: zone PROOF-1\ndef test_zone():\n'
                               '    try:\n        open("x")\n    except OSError:\n'
                               '        pass\n')})
    found = plain_checks.check_project(str(tmp_path), out=io.StringIO())
    assert {(f['feature'], f['proof']) for f in found} == {
        ('age', 'PROOF-1'), ('login', 'PROOF-1'), ('zone', 'PROOF-1')}
    assert len(fake_claude.calls(own_claude)) == 0
