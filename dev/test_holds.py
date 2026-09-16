"""Tests for holds: a person's committed word that a test does not prove its proof.

The machine reads whether the tests pass and how strong they are. It cannot
read whether a test proves the proof text, so a person who finds that it does
not commits a hold, and the rule needs a person until the text moves or a
signature outranks it. The throwaway project is `dev/test_signatures.py`'s:
`RULE-1` is low risk, `RULE-2` high.
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

import approve as sign_module  # noqa: E402
from test_signatures import Project, git, signing_key  # noqa: E402

CASE = 'no case for an expired token'


@pytest.fixture
def proved():
    made = Project()
    made.proofs()
    made.record()
    yield made
    made.close()


def _holds(project):
    return [name for name in project.signatures()
            if name.endswith('.hold.json')]


# ---------------------------------------------------------------------------
# Writing a hold
# ---------------------------------------------------------------------------

class TestWritingAHold:

    @pytest.mark.proof("signatures", "PROOF-60", "RULE-40", tier="integration")
    def test_a_hold_is_one_signed_file_with_the_case(self, proved, capsys):
        signing_key(proved.root)
        code = sign_module.main(['login', 'RULE-1', '--hold', CASE,
                                 '--project-root', proved.root])
        capsys.readouterr()
        assert code == 0
        signature, subject = git(proved.root, 'log', '-1',
                                 '--format=%G?%n%s').stdout.strip().splitlines()
        assert signature == 'G'
        assert subject == 'hold(login): RULE-1'
        triple = sign_module.triple_for(proved.rule('RULE-1'))
        name = 'RULE-1.%s.jane.hold.json' % triple[:8]
        assert _holds(proved) == [name]
        added = git(proved.root, 'show', '--name-only', '--format=',
                    'HEAD').stdout.split()
        assert added == ['specs/auth/login.signatures/' + name], added
        with open(os.path.join(proved.root, 'specs', 'auth',
                               'login.signatures', name),
                  encoding='utf-8') as handle:
            data = json.load(handle)
        assert data['schema'] == 'purlin-hold/1'
        assert data['holder'] == 'jane@acme.com'
        assert data['reason'] == CASE
        assert data['triple'] == triple[:16]

    @pytest.mark.proof("signatures", "PROOF-61", "RULE-40", tier="integration")
    def test_a_hold_needs_a_case_and_a_rule(self, proved, capsys):
        for argv in (['login', 'RULE-1', '--hold'],
                     ['login', 'RULE-1', '--hold', '--batch'],
                     ['login', '--hold', 'a case']):
            assert sign_module.main(
                argv + ['--project-root', proved.root]) == 2, argv
        capsys.readouterr()
        assert _holds(proved) == []
