"""Tests for which rules the review list holds, and in what order.

The review list is what still needs a person: a rule blocked at the strong
cell by a question the machine could not settle, and a rule blocked at the
signed cell. A rule with no test is build work and stays on the board.

The throwaway project holds one rule for each row the list can carry, and one
that must never be on it. `dev/test_mcp_server.py` owns the project fixture.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from test_mcp_server import Project, _git  # noqa: E402

SPEC = (
    '# Feature: review\n\n'
    '> Description: One rule for every row the review list can carry.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: A stale rule was signed before its text was rewritten '
    '[risk: medium]\n'
    '- RULE-2: A held rule has a case a person wrote down [risk: low]\n'
    '- RULE-3: A rule a person has to read carries no automated proof '
    '[risk: medium]\n'
    '- RULE-4: A rule with no test is build work, not review work '
    '[risk: high]\n'
    '- RULE-5: An unsigned rule is strong and waiting for a signature '
    '[risk: high]\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /session with the password "secret"; verify 200 '
    'and 401 for a wrong one\n'
    '- PROOF-2 (RULE-2): POST /session 5 times with a wrong password; verify '
    '423 and an error body\n'
    '- PROOF-3 (RULE-3): Read the error messages against the brand voice '
    'guide; verify none names a rejected field twice @manual\n'
    '- PROOF-4 (RULE-4): POST /session with no body at all; verify 400 and an '
    'error body\n'
    '- PROOF-5 (RULE-5): DELETE /session twice; verify 204 and then 404\n'
)

REWORDED = SPEC.replace(
    'A stale rule was signed before its text was rewritten',
    'A stale rule was signed before its text was rewritten once')


def _project():
    """A `signed` project holding one rule per review row, and one without."""
    made = Project(gate='signed', spec=None,
                   extra_config={'signers': ['jane@acme.com'],
                                 'ai_review_at': 'never'})
    made.spec(SPEC, name='review', category='core')
    _git(made.root, 'add', '-A')
    _git(made.root, 'commit', '-q', '-m', 'docs: the spec under test')
    made.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                 {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'},
                 {'id': 'PROOF-5', 'rule': 'RULE-5', 'status': 'pass'}],
                feature='review', ci=True, strength=90)
    made.signature('RULE-1', feature='review', category='core')
    made.hold('RULE-2', 'the lock expiry is never read', feature='review',
              category='core')
    # The rule text moves under the signature, and only then is it stale.
    made.spec(REWORDED, name='review', category='core')
    return made


@pytest.fixture
def listed():
    made = _project()
    yield made
    made.close()


def _rows(payload):
    return [(row['rule'], row['cell'], tuple(row['why']))
            for row in payload['review_list']]


@pytest.mark.proof("states", "PROOF-33", "RULE-29", tier="integration")
def test_the_list_holds_the_rules_whose_next_step_is_a_person(listed):
    payload = listed.payload()
    rows = {row['rule']: row for row in payload['review_list']}
    assert sorted(rows) == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-5'], rows
    assert 'RULE-4' not in rows, 'a rule with no test is build work'
    for row in rows.values():
        assert sorted(row) == ['cell', 'feature', 'owner', 'risk', 'rule',
                               'why'], row
        assert row['feature'] == 'review' and row['owner'] == 'review'
    assert rows['RULE-1']['cell'] == 'signed'
    assert rows['RULE-2']['cell'] == 'strong'
    assert rows['RULE-5']['risk'] == 'high'


@pytest.mark.proof("states", "PROOF-33", "RULE-29", tier="integration")
def test_the_list_is_empty_under_the_passed_gate(listed):
    listed.config_value('gate', 'passed')
    payload = listed.payload()
    assert payload['review_list'] == [], payload['review_list']
    assert 'strong' not in payload['features'][0]['rules'][0]['cells']


@pytest.mark.proof("states", "PROOF-34", "RULE-30", tier="integration")
def test_every_why_is_one_of_the_five_words(listed):
    allowed = {'unsigned', 'stale', 'held', 'needs a person', 'manual'}
    rows = {rule: why for rule, _cell, why in _rows(listed.payload())}
    for why in rows.values():
        assert set(why) <= allowed, why
    assert rows['RULE-1'] == ('stale',)
    assert rows['RULE-2'] == ('held',)
    assert rows['RULE-3'] == ('manual',), 'a @manual proof names itself'
    assert rows['RULE-5'] == ('unsigned',)


@pytest.mark.proof("states", "PROOF-35", "RULE-31", tier="integration")
def test_the_list_reads_high_risk_first_then_stale_and_held(listed):
    assert [rule for rule, _cell, _why in _rows(listed.payload())] == [
        'RULE-5', 'RULE-1', 'RULE-3', 'RULE-2']


@pytest.mark.proof("states", "PROOF-36", "RULE-31", tier="integration")
def test_a_global_anchor_rule_is_named_once():
    made = Project(gate='strong')
    try:
        made.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere [risk: high]\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
            name='security', category='_anchors')
        made.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                     {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                    ci=True, strength=90)
        made.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}],
                    feature='security', ci=True, strength=90)
        data = made.payload()
        entries = [(e['feature'], e['rule']) for e in data['review_list']]
        assert sorted(entries) == [('login', 'RULE-1'),
                                   ('security', 'RULE-1')], entries
        assert data['summary']['needs_person'] == 2, data['summary']
    finally:
        made.close()
