"""Tests for which rules the two lists hold, and in what order.

Review is what a person still has to answer about the tests: a strong cell
reading `manual test`, `unsettled` or `held`. Sign is what a signer can act
on: a rule whose level is `signed`, whose tests and audit are met and that
has no signature that counts.
A rule with no test is build work and stays on the board, and so is a rule
reading `not audited`, whose next step is `purlin:audit`.

The throwaway project holds one rule for each row the lists can carry, and
one that must never be on either. `dev/test_mcp_server.py` owns the fixture.
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
    '- RULE-1: A stale rule was signed before its text was rewritten\n'
    '- RULE-2: A held rule has a case a person wrote down [level: passed]\n'
    '- RULE-3: A rule a person has to read carries no automated proof\n'
    '- RULE-4: A rule with no test is build work, not review work\n'
    '- RULE-5: An unsigned rule is strong and waiting for a signature\n'
    '- RULE-6: An unaudited rule waits for the audit, not for a person\n\n'
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
    '- PROOF-6 (RULE-6): GET /session with an expired cookie; verify 401 and '
    'an empty body\n'
)

REWORDED = SPEC.replace(
    'A stale rule was signed before its text was rewritten',
    'A stale rule was signed before its text was rewritten once')


def _project():
    """A `signed` project holding one rule per review row, and one without."""
    made = Project(gate='signed', spec=None)
    made.spec(SPEC, name='review', category='core')
    _git(made.root, 'add', '-A')
    _git(made.root, 'commit', '-q', '-m', 'docs: the spec under test')
    made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                   {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'},
                   {'id': 'PROOF-5', 'rule': 'RULE-5', 'status': 'pass'},
                   {'id': 'PROOF-6', 'rule': 'RULE-6', 'status': 'pass'}],
                  feature='review', ci=True, strength=90)
    # Every rule whose level is above `passed` is owed an AI audit. RULE-6 is the one
    # left without an audit entry, so it reads `not audited` and is on no
    # list.
    for rule in ('RULE-1', 'RULE-5'):
        made.audit(rule, feature='review')
    made.signature('RULE-1', feature='review', category='core')
    made.hold('RULE-2', 'the lock expiry is never read', feature='review',
              category='core')
    # The rule text moves under the signature, and only then is it stale.
    # The audit runs again over the new text, so the rule's tests and audit
    # are met and what is left outstanding is the signature.
    made.spec(REWORDED, name='review', category='core')
    made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                   {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'},
                   {'id': 'PROOF-5', 'rule': 'RULE-5', 'status': 'pass'},
                   {'id': 'PROOF-6', 'rule': 'RULE-6', 'status': 'pass'}],
                  feature='review', ci=True, strength=90)
    made.audit('RULE-1', feature='review')
    return made


@pytest.fixture
def listed():
    made = _project()
    yield made
    made.close()


def _rows(payload):
    both = list(payload['review_list']) + list(payload['sign_list'])
    return [(row['rule'], row['cell'], tuple(row['why'])) for row in both]


@pytest.mark.proof("states", "PROOF-33", "RULE-29")
def test_review_holds_the_rules_whose_next_step_is_a_person(listed):
    payload = listed.payload()
    rows = {row['rule']: row for row in payload['review_list']}
    assert sorted(rows) == ['RULE-2', 'RULE-3'], rows
    assert 'RULE-4' not in rows, 'a rule with no test is build work'
    assert 'RULE-6' not in rows, 'a rule waiting for the audit is not a row'
    for row in rows.values():
        assert sorted(row) == ['cell', 'feature', 'kind', 'level', 'owner',
                               'rule', 'why'], row
        assert row['feature'] == 'review' and row['owner'] == 'review'
        assert row['cell'] == 'strong'
    assert rows['RULE-2']['kind'] == 'held'
    assert rows['RULE-3']['kind'] == 'manual test'
    assert listed.rule('RULE-6', 'review')['cells']['strong']['word'] == (
        'not audited')


@pytest.mark.proof("states", "PROOF-63", "RULE-54")
def test_sign_holds_the_signable_rules(listed):
    payload = listed.payload()
    rows = {row['rule']: row for row in payload['sign_list']}
    assert sorted(rows) == ['RULE-1', 'RULE-5'], rows
    for row in rows.values():
        assert sorted(row) == ['cell', 'feature', 'kind', 'level', 'owner',
                               'rule', 'why'], row
        assert row['cell'] == 'signed'
    assert rows['RULE-1']['kind'] == 'stale'
    assert rows['RULE-5']['kind'] == 'unsigned'
    listed.config_value('gate', 'strong')
    assert listed.payload()['sign_list'] == []


@pytest.mark.proof("states", "PROOF-33", "RULE-29")
def test_the_lists_are_empty_under_the_passed_gate(listed):
    listed.config_value('gate', 'passed')
    payload = listed.payload()
    assert payload['review_list'] == [], payload['review_list']
    assert payload['sign_list'] == [], payload['sign_list']
    assert 'strong' not in payload['features'][0]['rules'][0]['cells']


@pytest.mark.proof("states", "PROOF-34", "RULE-30")
def test_every_kind_is_one_of_its_list_own_words(listed):
    payload = listed.payload()
    at_strong = {'manual test', 'unsettled', 'held'}
    at_signed = {'unsigned', 'stale', 'held'}
    for key, allowed in (('review_list', at_strong), ('sign_list', at_signed)):
        for row in payload[key]:
            assert row['kind'] in allowed, row
            assert row['why'] == [row['kind']], row
    rows = {rule: why for rule, _cell, why in _rows(payload)}
    assert rows['RULE-1'] == ('stale',)
    assert rows['RULE-2'] == ('held',)
    assert rows['RULE-3'] == ('manual test',), 'a @manual proof names itself'
    assert rows['RULE-5'] == ('unsigned',)


@pytest.mark.proof("states", "PROOF-35", "RULE-31")
def test_both_lists_read_the_highest_level_first_then_feature_and_number(
        listed):
    payload = listed.payload()
    assert [row['rule'] for row in payload['review_list']] == [
        'RULE-3', 'RULE-2']
    assert [row['rule'] for row in payload['sign_list']] == [
        'RULE-1', 'RULE-5']


@pytest.mark.proof("states", "PROOF-36", "RULE-31")
def test_a_global_anchor_rule_is_named_once():
    made = Project(gate='strong')
    try:
        made.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
            name='security', category='_anchors')
        made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                     {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                    ci=True, strength=90)
        made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}],
                    feature='security', ci=True, strength=90)
        made.audit('RULE-1', settled=False)
        made.audit('RULE-1', feature='security', settled=False)
        data = made.payload()
        entries = [(e['feature'], e['rule']) for e in data['review_list']]
        assert sorted(entries) == [('login', 'RULE-1'),
                                   ('security', 'RULE-1')], entries
        assert data['summary']['unsettled'] == 2, data['summary']
    finally:
        made.close()
