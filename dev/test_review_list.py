"""Tests for which rules the review list holds once people have approved them.

The review list is what still needs a person. A rule's risk may call for a
model review for good, but a current approval takes it off the list until that
approval goes stale. The throwaway project is `dev/test_approvals.py`'s:
`RULE-1` is low risk, `RULE-2` high.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import approve as approve_module  # noqa: E402
from test_approvals import SPEC, Project  # noqa: E402


@pytest.fixture
def reviewed():
    made = Project(config={'ai_review_at': 'high'})
    made.proofs()
    made.record()
    yield made
    made.close()


def _listed(payload):
    return [(entry['owner'], entry['rule']) for entry in payload['review_list']]


@pytest.mark.proof("states", "PROOF-37", "RULE-31", tier="integration")
def test_an_approval_takes_a_rule_off_the_list_until_it_goes_stale(reviewed):
    before = reviewed.payload()
    assert ('login', 'RULE-2') in _listed(before), before['review_list']
    assert before['project_rollup']['needs_review'] == 1

    approve_module.write_approval(reviewed.root, 'login', 'RULE-2',
                                  'ada@acme.com', None, None, 'tested', 'high')
    after = reviewed.payload()
    assert ('login', 'RULE-2') not in _listed(after), after['review_list']
    assert after['project_rollup']['needs_review'] == 0
    assert reviewed.rule('RULE-2')['flags']['needs_ai_review'] is True

    reviewed.spec(SPEC.replace('return 401 and the body "denied"',
                               'return 401 and the body "denied" at once'))
    assert reviewed.rule('RULE-2')['state'] == 'Stale'
    assert ('login', 'RULE-2') in _listed(reviewed.payload())
