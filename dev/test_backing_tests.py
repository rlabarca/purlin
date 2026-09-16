"""Tests for which tests a rule's test hash binds.

The test hash is part of what an approval binds, so it must read the same in
every checkout and in CI. The committed records name the tests; this checkout's
runtime proofs speak only for a proof no record has observed. The throwaway
project is `dev/test_approvals.py`'s.
"""

import json
import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from purlin import specs as purlin_specs  # noqa: E402
from test_approvals import TEST_NAMES, Project, git, write  # noqa: E402

EXTRA = 'test_only_this_machine_runs'


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


def _runtime(project, proof_one_names):
    entries = [{'feature': 'login', 'id': 'PROOF-1', 'rule': 'RULE-1',
                'status': 'pass', 'tier': 'unit',
                'test_file': 'tests/test_login.py', 'test_name': name}
               for name in proof_one_names]
    entries.append({'feature': 'login', 'id': 'PROOF-2', 'rule': 'RULE-2',
                    'status': 'pass', 'tier': 'unit',
                    'test_file': 'tests/test_login.py',
                    'test_name': TEST_NAMES['PROOF-2']})
    write(os.path.join(project.root, '.purlin', 'runtime', 'proofs',
                       'login.unit.json'),
          json.dumps({'tier': 'unit', 'proofs': entries}))


def _os_record(project, os_name, stamp, proof_one_names):
    proofs = [{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass',
               'tier': 'unit', 'env': None,
               'test_file': 'tests/test_login.py', 'test_name': name}
              for name in proof_one_names]
    proofs.append({'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass',
                   'tier': 'unit', 'env': None,
                   'test_file': 'tests/test_login.py',
                   'test_name': TEST_NAMES['PROOF-2']})
    rel = '.purlin/records/login/%s-%s-ci-%s.json' % (
        stamp, project.head()[:7], os_name)
    write(os.path.join(project.root, rel), json.dumps({
        'schema_version': 1, 'feature': 'login', 'commit': project.head(),
        'timestamp': '%s-%s-%sT%s:%s:%sZ' % (stamp[0:4], stamp[4:6], stamp[6:8],
                                             stamp[9:11], stamp[11:13],
                                             stamp[13:15]),
        'runner': 'ci-' + os_name, 'os': os_name,
        'gate': 'tested', 'test_strength': 90,
        'scope_tree': purlin_specs.scope_tree(project.root, ['src/login.py']),
        'proofs': proofs}))
    git(project.root, 'add', '-A')
    git(project.root, 'commit', '-q', '-m', 'purlin: record for abc1234')


class TestTheRecordsNameTheTests:

    @pytest.mark.proof("states", "PROOF-34", "RULE-30", tier="integration")
    def test_what_this_checkout_ran_does_not_move_the_hash(self, project):
        project.proofs()
        project.record()
        first = project.rule('RULE-1')['test_hash']
        _runtime(project, [TEST_NAMES['PROOF-1'], EXTRA])
        assert project.rule('RULE-1')['test_hash'] == first, \
            'a test only this checkout ran moved the hash'
        _runtime(project, [])
        assert project.rule('RULE-1')['test_hash'] == first, \
            'a test this checkout could not run moved the hash'

    @pytest.mark.proof("states", "PROOF-35", "RULE-30", tier="integration")
    def test_with_no_record_the_runtime_names_the_tests(self, project):
        project.proofs()
        before = project.rule('RULE-1')['test_hash']
        _runtime(project, [TEST_NAMES['PROOF-1'], EXTRA])
        assert project.rule('RULE-1')['test_hash'] != before

    @pytest.mark.proof("states", "PROOF-36", "RULE-30", tier="integration")
    def test_every_operating_system_s_record_counts(self, project):
        project.proofs()
        _os_record(project, 'linux', '20260913T120000Z',
                   [TEST_NAMES['PROOF-1']])
        _os_record(project, 'windows', '20260913T121000Z',
                   [TEST_NAMES['PROOF-1'], 'test_the_windows_lock'])
        proof = next(p for p in project.rule('RULE-1')['proofs']
                     if p['id'] == 'PROOF-1')
        names = [test['name'] for test in proof['tests']]
        assert sorted(names) == sorted([TEST_NAMES['PROOF-1'],
                                        'test_the_windows_lock']), names
