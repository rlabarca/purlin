"""Tests for which tests a rule's test hash binds.

The test hash is part of what a signature binds, so it must read the same in
every checkout and in CI: it is read from the tests the evidence sections
name. The throwaway project is `dev/sign_project.py`'s.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from sign_project import TEST_FILE, TEST_NAMES, Project, git, write  # noqa: E402

WINDOWS_LOCK = 'test_the_windows_lock'
LINUX_LOCK = 'test_the_linux_lock'


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


def _hash_of_one_section_naming(proof_one_tests):
    """`RULE-1`'s test hash in a project whose one section names those tests."""
    single = Project()
    try:
        single.evidence(os_name='linux', tests={'PROOF-1': proof_one_tests})
        return single.rule('RULE-1')['test_hash']
    finally:
        single.close()


def _rewrite_the_code(project):
    write(os.path.join(project.root, 'src', 'login.py'),
          'def login(user, password):\n    return 401\n')


class TestTheEvidenceNamesTheTests:

    # purlin: states PROOF-41
    def test_a_code_change_does_not_move_the_hash(self, project):
        project.evidence()
        first = project.rule('RULE-1')['test_hash']
        _rewrite_the_code(project)
        assert project.rule('RULE-1')['cells']['passed']['word'] == \
            'out of date'
        assert project.rule('RULE-1')['test_hash'] == first, \
            'a section out of date for the code moved the hash'

    # purlin: states PROOF-218
    def test_a_checkout_with_windows_line_endings_keeps_the_hash(
            self, project):
        test_file = os.path.join(project.root, 'tests', 'test_login.py')
        git(project.root, 'config', 'core.autocrlf', 'false')
        # The file as git stores it, line feeds alone, whatever this system
        # writes for a line ending.
        with open(test_file, 'wb') as handle:
            handle.write(TEST_FILE.encode('utf-8'))
        git(project.root, 'add', '-A')
        git(project.root, 'commit', '-q', '-m', 'test(login): line feeds')
        project.evidence()
        plain = project.rule('RULE-1')['test_hash']

        git(project.root, 'config', 'core.autocrlf', 'true')
        os.remove(test_file)
        assert git(project.root, 'checkout', '--',
                   'tests/test_login.py').returncode == 0
        with open(test_file, 'rb') as handle:
            assert b'\r\n' in handle.read(), \
                'the checkout did not write Windows line endings'
        assert project.rule('RULE-1')['test_hash'] == plain, \
            'the line endings of the checkout moved the hash'

    # purlin: states PROOF-164
    def test_both_sources_make_up_the_hash(self, project):
        local = [TEST_NAMES['PROOF-1'], LINUX_LOCK]
        ci = [TEST_NAMES['PROOF-1'], WINDOWS_LOCK]
        project.evidence(os_name='linux', tests={'PROOF-1': local})
        project.evidence(os_name='windows', runner='ci', source='ci',
                         at='2026-09-13T12:10:00Z', tests={'PROOF-1': ci})
        assert project.rule('RULE-1')['test_hash'] == \
            _hash_of_one_section_naming(local + [WINDOWS_LOCK]), \
            'a local and a ci section did not make up one list'
