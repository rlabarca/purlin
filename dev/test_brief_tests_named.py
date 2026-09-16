"""Tests for `scripts/review/brief.py`: several tests behind one proof.

A proof may be backed by more than one test, and a person approving from the
brief reads the source shown under each test's name. These tests hold that the
source and the findings under a name are that test's own. The throwaway project
is `dev/test_approvals.py`'s, with a second test marked for the same proof.
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

import brief as brief_module  # noqa: E402
import static_checks  # noqa: E402
from test_approvals import TEST_FILE, Project, write  # noqa: E402

SECOND_TEST = (
    '\n\n'
    '@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'
    'def test_a_token_comes_back():\n'
    '    token = session_for("ada", "secret")\n'
    '    assert token.startswith("tok-")\n'
)

NO_ASSERTION = (
    '\n\n'
    '@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'
    'def test_a_token_comes_back():\n'
    '    session_for("ada", "secret")\n'
)

NAMES = ('test_valid_credentials_return_200', 'test_a_token_comes_back')


def _two_tests(project, second=SECOND_TEST, names=NAMES):
    project.edit_test(TEST_FILE + second)
    entries = [{'feature': 'login', 'id': 'PROOF-1', 'rule': 'RULE-1',
                'status': 'pass', 'tier': 'unit',
                'test_file': 'tests/test_login.py', 'test_name': name}
               for name in names]
    entries.append({'feature': 'login', 'id': 'PROOF-2', 'rule': 'RULE-2',
                    'status': 'pass', 'tier': 'unit',
                    'test_file': 'tests/test_login.py',
                    'test_name': 'test_a_bad_password_is_denied'})
    write(os.path.join(project.root, '.purlin', 'runtime', 'proofs',
                       'login.unit.json'),
          json.dumps({'tier': 'unit', 'proofs': entries}))
    project.record(tests={'PROOF-1': list(names)})


def _tests_by_name(project):
    brief = brief_module.build_brief(project.root, None, 'login', 'RULE-1')
    return {test['name']: test for test in brief['tests']}


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


class TestEachTestShowsItsOwnSource:

    @pytest.mark.proof("brief", "PROOF-38", "RULE-26", tier="integration")
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

    @pytest.mark.proof("brief", "PROOF-39", "RULE-26", tier="integration")
    def test_a_finding_stays_with_the_test_it_was_found_in(self, project):
        _two_tests(project, second=NO_ASSERTION)
        tests = _tests_by_name(project)
        assert 'no_assertion' in tests['test_a_token_comes_back']['findings'], \
            tests['test_a_token_comes_back']
        assert 'no_assertion' not in \
            tests['test_valid_credentials_return_200']['findings'], \
            tests['test_valid_credentials_return_200']

    @pytest.mark.proof("brief", "PROOF-40", "RULE-26", tier="integration")
    def test_a_name_the_file_no_longer_holds_shows_no_body(self, project):
        _two_tests(project, names=NAMES + ('test_renamed_away',))
        tests = _tests_by_name(project)
        assert tests['test_renamed_away']['body'] is None, \
            tests['test_renamed_away']
        assert 'def test_valid_credentials_return_200' in \
            tests['test_valid_credentials_return_200']['body']
        assert 'def test_a_token_comes_back' in \
            tests['test_a_token_comes_back']['body']


class TestARecordedNameFindsItsSource:

    @pytest.mark.proof("brief", "PROOF-41", "RULE-26")
    def test_each_runner_name_form_finds_its_own_test(self):
        names = ['Allowed', 'Denied', 'test_found',
                 'works [proof:login:PROOF-1:RULE-1]']
        expected = {
            'Acme.LoginTests.Denied(user: "x")': [1],
            'test_found[jest-[proof:f:PROOF-1:RULE-1]]': [2],
            'TestLogin::test_found': [2],
            'works [proof:login:PROOF-1:RULE-1]': [3],
            'test_gone': [],
        }
        for recorded, indexes in expected.items():
            assert static_checks.test_name_matches(recorded, names) == indexes, \
                recorded
