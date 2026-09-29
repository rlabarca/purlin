"""Tests for `scripts/review/ai_audit.py`: several tests behind one proof.

A proof may be backed by more than one test, and the AI audit, and a person
reading what it read, see the source shown under each test's name. These tests hold that the
source under a name is that test's own. The throwaway project
is `dev/test_signatures.py`'s, with a second test marked for the same proof.
"""

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
    def test_each_name_shows_its_own_body(self, project):
        _two_tests(project)
        tests = _tests_by_name(project)
        assert sorted(tests) == sorted(NAMES), tests
        first = tests['test_valid_credentials_return_200']['body']
        second = tests['test_a_token_comes_back']['body']
        assert 'def test_valid_credentials_return_200' in first, first
        assert '== 200' in first, first
        assert 'def test_a_token_comes_back' not in first, first
        assert 'def test_a_token_comes_back' in second, second
        assert 'token' in second, second
        assert 'def test_valid_credentials_return_200' not in second, second

    # purlin: ai_audit PROOF-35
    def test_a_name_the_file_no_longer_holds_shows_no_body(self, project):
        _two_tests(project, names=NAMES + ('test_renamed_away',))
        tests = _tests_by_name(project)
        assert tests['test_renamed_away']['body'] is None, \
            tests['test_renamed_away']
        assert 'def test_valid_credentials_return_200' in \
            tests['test_valid_credentials_return_200']['body']
        assert 'def test_a_token_comes_back' in \
            tests['test_a_token_comes_back']['body']


class TestANameFromARecordFindsItsSource:

    # purlin: ai_audit PROOF-36
    def test_each_runner_name_form_finds_its_own_test(self):
        names = ['Allowed', 'Denied', 'test_found', 'works']
        expected = {
            'Acme.LoginTests.Denied(user: "x")': [1],
            'test_found[jest-case-1]': [2],
            'TestLogin::test_found': [2],
            'login > works': [3],
            'test_gone': [],
        }
        for written, indexes in expected.items():
            assert marked_tests.name_matches(written, names) == indexes, \
                written
