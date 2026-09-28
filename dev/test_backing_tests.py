"""Tests for which tests a rule's test hash binds.

The test hash is part of what a signature binds, so it must read the same in
every checkout and in CI. The evidence sections name the tests; this
checkout's runtime proof files name nothing. The throwaway project is
`dev/test_signatures.py`'s.
"""

import json
import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from test_signatures import TEST_NAMES, Project, write  # noqa: E402

EXTRA = 'test_only_this_machine_runs'


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


def _runtime(project, proof_one_names):
    entries = [{'feature': 'login', 'id': 'PROOF-1', 'rule': 'RULE-1',
                'status': 'pass', 'test_file': 'tests/test_login.py', 'test_name': name}
               for name in proof_one_names]
    entries.append({'feature': 'login', 'id': 'PROOF-2', 'rule': 'RULE-2',
                    'status': 'pass', 'test_file': 'tests/test_login.py',
                    'test_name': TEST_NAMES['PROOF-2']})
    write(os.path.join(project.root, '.purlin', 'runtime', 'proofs',
                       'login.json'),
          json.dumps({'proofs': entries}))


class TestTheEvidenceNamesTheTests:

    @pytest.mark.proof("states", "PROOF-40", "RULE-35")
    def test_what_this_checkout_ran_does_not_move_the_hash(self, project):
        project.proofs()
        project.evidence()
        first = project.rule('RULE-1')['test_hash']
        _runtime(project, [TEST_NAMES['PROOF-1'], EXTRA])
        assert project.rule('RULE-1')['test_hash'] == first, \
            'a test only this checkout ran moved the hash'
        _runtime(project, [])
        assert project.rule('RULE-1')['test_hash'] == first, \
            'a test this checkout could not run moved the hash'

    @pytest.mark.proof("states", "PROOF-41", "RULE-35")
    def test_a_code_change_does_not_move_the_hash_and_a_new_run_can(
            self, project):
        project.evidence()
        first = project.rule('RULE-1')['test_hash']
        write(os.path.join(project.root, 'src', 'login.py'),
              'def login(user, password):\n    return 401\n')
        assert project.rule('RULE-1')['cells']['passed']['word'] == \
            'out of date'
        assert project.rule('RULE-1')['test_hash'] == first, \
            'a section out of date for the code moved the hash'
        project.evidence(tests={'PROOF-1': [TEST_NAMES['PROOF-1'], EXTRA]},
                         at='2026-09-14T12:00:00Z')
        assert project.rule('RULE-1')['test_hash'] != first

    @pytest.mark.proof("states", "PROOF-42", "RULE-35")
    def test_every_operating_system_s_section_counts(self, project):
        project.evidence(os_name='linux', runner='ci', source='ci')
        project.evidence(os_name='windows', runner='ci', source='ci',
                         at='2026-09-13T12:10:00Z',
                         tests={'PROOF-1': [TEST_NAMES['PROOF-1'],
                                            'test_the_windows_lock']})
        proof = next(p for p in project.rule('RULE-1')['proofs']
                     if p['id'] == 'PROOF-1')
        names = [test['name'] for test in proof['tests']]
        assert sorted(names) == sorted([TEST_NAMES['PROOF-1'],
                                        'test_the_windows_lock']), names
