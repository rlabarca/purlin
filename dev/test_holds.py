"""Tests for holds: a person's committed word that a test does not prove its proof.

CI approves a low-risk rule on its own only when the free checks can settle it.
It cannot read whether a test proves the proof text, so a person who finds that
it does not commits a hold, and CI's approval gives way to it. The throwaway
project is `dev/test_approvals.py`'s: `RULE-1` is low risk, `RULE-2` high.
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

import approve as approve_module  # noqa: E402
from test_approvals import (TEST_FILE, Project, git,  # noqa: E402
                            signing_key)

CASE = 'no case for an expired token'
ASSERTION = 'assert login("ada", "secret") == 200'


@pytest.fixture
def proved():
    made = Project()
    made.proofs()
    made.record()
    yield made
    made.close()


def _holds(project):
    return [name for name in project.approvals() if name.endswith('.hold.json')]


def _rule_one_written(written):
    return len(written) == 1 and 'RULE-1' in written[0]


# ---------------------------------------------------------------------------
# What CI may approve alone
# ---------------------------------------------------------------------------

class TestWhatCiApprovesAlone:

    @pytest.mark.proof("approvals", "PROOF-59", "RULE-39", tier="integration")
    def test_a_finding_in_the_test_body_stops_it(self, proved):
        proved.edit_test(TEST_FILE.replace(ASSERTION, 'login("ada", "secret")'))
        proved.record(stamp='20260913T130000Z')
        assert approve_module.auto_approve(proved.root) == []
        proved.edit_test(TEST_FILE)
        proved.record(stamp='20260913T140000Z')
        written = approve_module.auto_approve(proved.root)
        assert _rule_one_written(written), written

    @pytest.mark.proof("approvals", "PROOF-62", "RULE-41", tier="integration")
    def test_a_current_hold_stops_it_and_a_stale_one_does_not(self, proved):
        assert approve_module.write_hold(proved.root, 'login', 'RULE-1',
                                         'jane@acme.com', CASE)
        assert approve_module.auto_approve(proved.root) == []
        proved.edit_test(TEST_FILE.replace(
            '    ' + ASSERTION, "    # the fixture's password\n    " + ASSERTION))
        proved.record(stamp='20260913T130000Z')
        written = approve_module.auto_approve(proved.root)
        assert _rule_one_written(written), written


# ---------------------------------------------------------------------------
# Writing a hold
# ---------------------------------------------------------------------------

class TestWritingAHold:

    @pytest.mark.proof("approvals", "PROOF-60", "RULE-40", tier="integration")
    def test_a_hold_is_one_signed_file_with_the_case(self, proved, capsys):
        signing_key(proved.root)
        code = approve_module.main(['login', 'RULE-1', '--hold', CASE,
                                    '--project-root', proved.root])
        capsys.readouterr()
        assert code == 0
        signature, subject = git(proved.root, 'log', '-1',
                                 '--format=%G?%n%s').stdout.strip().splitlines()
        assert signature == 'G'
        assert subject == 'hold(login): RULE-1'
        triple = approve_module.triple_for(proved.rule('RULE-1'))
        name = 'RULE-1.%s.jane.hold.json' % triple[:8]
        assert _holds(proved) == [name]
        added = git(proved.root, 'show', '--name-only', '--format=',
                    'HEAD').stdout.split()
        assert added == ['specs/auth/login.approvals/' + name], added
        with open(os.path.join(proved.root, 'specs', 'auth', 'login.approvals',
                               name), encoding='utf-8') as handle:
            data = json.load(handle)
        assert data['schema'] == 'purlin-hold/1'
        assert data['holder'] == 'jane@acme.com'
        assert data['reason'] == CASE
        assert data['triple'] == triple[:16]

    @pytest.mark.proof("approvals", "PROOF-61", "RULE-40", tier="integration")
    def test_a_hold_needs_a_case_and_a_rule(self, proved, capsys):
        for argv in (['login', 'RULE-1', '--hold'],
                     ['login', 'RULE-1', '--hold', '--batch'],
                     ['login', '--hold', 'a case']):
            assert approve_module.main(
                argv + ['--project-root', proved.root]) == 2, argv
        capsys.readouterr()
        assert _holds(proved) == []


# ---------------------------------------------------------------------------
# The state a hold leaves
# ---------------------------------------------------------------------------

def _ci_and_hold(project, test_hash=None):
    approve_module.write_approval(project.root, 'login', 'RULE-1', 'ci', None,
                                  None, 'tested', 'low')
    path = approve_module.write_hold(project.root, 'login', 'RULE-1',
                                     'jane@acme.com', CASE)
    if test_hash:
        full = os.path.join(project.root, path)
        with open(full, encoding='utf-8') as handle:
            data = json.load(handle)
        data['test_hash'] = test_hash
        with open(full, 'w', encoding='utf-8') as handle:
            json.dump(data, handle)


class TestTheStateAHoldLeaves:

    @pytest.mark.proof("states", "PROOF-31", "RULE-29", tier="integration")
    def test_a_hold_outranks_ci(self, proved):
        _ci_and_hold(proved)
        rule = proved.rule('RULE-1')
        assert rule['state'] != 'Approved', rule
        assert rule['flags']['held'] is True
        assert rule['flags']['auto_approvable'] is False
        assert 'held by jane@acme.com: %s' % CASE in rule['reasons'], rule

    @pytest.mark.proof("states", "PROOF-32", "RULE-29", tier="integration")
    def test_a_person_still_approves_over_a_hold(self, proved):
        _ci_and_hold(proved)
        approve_module.write_approval(proved.root, 'login', 'RULE-1',
                                      'ada@acme.com', None, None, 'tested',
                                      'low')
        assert proved.rule('RULE-1')['state'] == 'Approved'

    @pytest.mark.proof("states", "PROOF-33", "RULE-29", tier="integration")
    def test_a_hold_on_other_hashes_does_nothing(self, proved):
        _ci_and_hold(proved, test_hash='0' * 64)
        rule = proved.rule('RULE-1')
        assert rule['state'] == 'Approved', rule
        assert rule['flags']['held'] is False
        assert not [reason for reason in rule['reasons'] if 'held' in reason]
