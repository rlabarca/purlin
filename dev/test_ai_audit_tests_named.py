"""Tests for `scripts/review/ai_audit.py`: several tests behind one proof.

A proof may be backed by more than one test, and the AI audit, and a person
reading what it read, see the source shown under each test's name. These tests
hold that the source under a name is that test's own, whatever form of the
name a runner records, and that the audit names a test whose source it cannot
find. The throwaway project is `dev/sign_project.py`'s, with a
second test marked for the same proof.
"""

import io
import json
import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import ai_audit as audit_module  # noqa: E402
import audit_run  # noqa: E402
import marked_tests  # noqa: E402
from sign_project import TEST_FILE, Project, write  # noqa: E402

SECOND_TEST = (
    '\n\n'
    '# purlin: login PROOF-1\n'
    'def test_a_token_comes_back():\n'
    '    token = session_for("ada", "secret")\n'
    '    assert token.startswith("tok-")\n'
)

NAMES = ('test_valid_credentials_return_200', 'test_a_token_comes_back')


def _two_tests(project, second=SECOND_TEST, names=NAMES):
    project.edit_test(TEST_FILE + second)
    entries = [{'feature': 'login', 'id': 'PROOF-1', 'rule': 'RULE-1',
                'status': 'pass', 'test_file': 'tests/test_login.py', 'test_name': name}
               for name in names]
    entries.append({'feature': 'login', 'id': 'PROOF-2', 'rule': 'RULE-2',
                    'status': 'pass', 'test_file': 'tests/test_login.py',
                    'test_name': 'test_a_bad_password_is_denied'})
    write(os.path.join(project.root, '.purlin', 'runtime', 'proofs',
                       'login.json'),
          json.dumps({'proofs': entries}))
    project.evidence(tests={'PROOF-1': list(names)})


def _tests_by_name(project):
    reading = audit_module.reading_for(project.root, None, 'login', 'RULE-1')
    return {test['name']: test for test in reading['tests']}


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


class TestEachTestShowsItsOwnSource:

    # purlin: ai_audit PROOF-34
    def test_two_passing_tests_of_one_proof_each_show_their_own_source(
            self, project):
        _two_tests(project)
        rule = project.rule('RULE-1')
        assert [test['result'] for proof in rule['proofs']
                for test in proof['tests']] == ['pass', 'pass'], rule
        reading = audit_module.reading_for(project.root, None, 'login',
                                           'RULE-1')
        # Exactly those two: each listed once and no third entry.
        assert sorted(test['name'] for test in reading['tests']) == sorted(
            NAMES), reading['tests']
        tests = _tests_by_name(project)
        first = tests['test_valid_credentials_return_200']['body']
        second = tests['test_a_token_comes_back']['body']
        assert 'def test_valid_credentials_return_200' in first, first
        assert '== 200' in first, first
        assert 'def test_a_token_comes_back' not in first, first
        assert 'def test_a_token_comes_back' in second, second
        assert 'token.startswith("tok-")' in second, second
        assert 'def test_valid_credentials_return_200' not in second, second
        assert '== 200' not in second, second
        assert 'tok-' not in first, first

    # purlin: ai_audit PROOF-35
    def test_a_name_the_evidence_holds_and_the_file_does_not_shows_no_source(
            self, project):
        _two_tests(project, names=NAMES + ('test_renamed_away',))
        tests = _tests_by_name(project)
        assert tests['test_renamed_away']['body'] is None, \
            tests['test_renamed_away']
        assert 'def test_valid_credentials_return_200' in \
            tests['test_valid_credentials_return_200']['body']
        assert 'def test_a_token_comes_back' in \
            tests['test_a_token_comes_back']['body']

    # purlin: plain_checks PROOF-31
    def test_a_test_whose_source_is_not_found_is_named_once(self, project):
        _two_tests(project, names=NAMES + ('test_renamed_away',))
        out = io.StringIO()
        assert audit_run.run(project.root, None, ['login'], out=out) == 0
        lines = out.getvalue().splitlines()
        assert 'login RULE-1   spot-checked' in lines, lines
        assert lines.count(
            'tests/test_login.py::test_renamed_away: its source was not '
            'found, so the spot tests did not read it.') == 1, lines


class TestANameFromARecordFindsItsSource:
    """Two tests marked for one proof, and the name a runner records for one.

    The source read for that name is that test's own, never its neighbour's.
    """

    @staticmethod
    def _source(tmp_path, path, text, recorded):
        (tmp_path / 'tests').mkdir(exist_ok=True)
        (tmp_path / path).write_text(text, encoding='utf-8')
        return marked_tests.source(str(tmp_path), 'demo', 'PROOF-1', path,
                                   recorded)

    # purlin: ai_audit PROOF-65
    def test_a_csharp_name_with_arguments_finds_its_own_test(self, tmp_path):
        text = (
            'using Xunit;\n'
            '\n'
            'namespace Acme\n'
            '{\n'
            '    public class LoginTests\n'
            '    {\n'
            '        // purlin: demo PROOF-1\n'
            '        [Fact]\n'
            '        public void Allowed()\n'
            '        {\n'
            '            Assert.Equal(200, 200);\n'
            '        }\n'
            '\n'
            '        // purlin: demo PROOF-1\n'
            '        [Theory]\n'
            '        [InlineData("x")]\n'
            '        public void Denied(string user)\n'
            '        {\n'
            '            Assert.Equal(401, 401);\n'
            '        }\n'
            '    }\n'
            '}\n')
        body = self._source(tmp_path, 'tests/LoginTests.cs', text,
                            'Acme.LoginTests.Denied(user: "x")')
        assert body is not None and 'public void Denied' in body, body
        assert 'Allowed' not in body, body
