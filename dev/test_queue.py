"""Tests for the queue: which rules wait on a person, and in what order.

A row is a `hand check`, a rule whose level is `strong` or `signed` and whose
strong cell reads `manual test`, or a `signature`, a rule whose
level is `signed`, whose tests and audit are met and that has no signature
that counts. A rule with no test is build work and stays on the board, and so
is a rule reading `not audited`, whose next step is `purlin:audit`. A rule
whose level is `passed` meets the gate on its tests, so nothing about it
waits.

The throwaway project holds one rule for each kind of row, and one of each
kind that must never be a row. `dev/test_mcp_server.py` owns the fixture.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from purlin import status as purlin_status  # noqa: E402
from test_mcp_server import Project, _git  # noqa: E402

SPEC = (
    '# Feature: review\n\n'
    '> Description: One rule for every kind of row the queue can carry.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: A stale rule was signed before its text was rewritten\n'
    '- RULE-2: A rule marked passed waits on nobody [level: passed]\n'
    '- RULE-3: A rule a person has to read carries no automated proof\n'
    '- RULE-4: A rule with no test is build work, not a person\'s\n'
    '- RULE-5: An unsigned rule is strong and waiting for a signature\n'
    '- RULE-6: An unaudited rule waits for the audit, not for a person\n'
    '- RULE-7: A rule the audit found weak is build work, not a person\'s\n'
    '- RULE-8: A rule whose test fails waits for its tests, not a person\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /session with the password "secret"; verify 200 '
    'and 401 for a wrong one\n'
    '- PROOF-2 (RULE-2): Read the lockout page against the style guide; '
    'verify it names the wait in minutes @manual\n'
    '- PROOF-3 (RULE-3): Read the error messages against the brand voice '
    'guide; verify none names a rejected field twice @manual\n'
    '- PROOF-4 (RULE-4): POST /session with no body at all; verify 400 and an '
    'error body\n'
    '- PROOF-5 (RULE-5): DELETE /session twice; verify 204 and then 404\n'
    '- PROOF-6 (RULE-6): GET /session with an expired cookie; verify 401 and '
    'an empty body\n'
    '- PROOF-7 (RULE-7): PUT /session with a stale token; verify 401\n'
    '- PROOF-8 (RULE-8): PATCH /session; verify 405\n'
)

REWORDED = SPEC.replace(
    'A stale rule was signed before its text was rewritten',
    'A stale rule was signed before its text was rewritten once')

RESULTS = [{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
           {'id': 'PROOF-5', 'rule': 'RULE-5', 'status': 'pass'},
           {'id': 'PROOF-6', 'rule': 'RULE-6', 'status': 'pass'},
           {'id': 'PROOF-7', 'rule': 'RULE-7', 'status': 'pass'},
           {'id': 'PROOF-8', 'rule': 'RULE-8', 'status': 'fail'}]


def _project():
    """A `signed` project holding one rule per kind of row, and the others."""
    made = Project(gate='signed', spec=None)
    made.spec(SPEC, name='review', category='core')
    _git(made.root, 'add', '-A')
    _git(made.root, 'commit', '-q', '-m', 'docs: the spec under test')
    made.evidence(RESULTS, feature='review', ci=True, strength=90)
    # Every rule whose level is above `passed` is owed an AI audit. RULE-6 is
    # the one left without an audit entry, so it reads `not audited` and is
    # not a row.
    for rule in ('RULE-1', 'RULE-5'):
        made.audit(rule, feature='review')
    made.signature('RULE-1', feature='review', category='core')
    # The rule text moves under the signature, and only then is it stale.
    # The audit runs again over the new text, so the rule's tests and audit
    # are met and what is left outstanding is the signature.
    made.spec(REWORDED, name='review', category='core')
    made.evidence(RESULTS, feature='review', ci=True, strength=90)
    made.audit('RULE-1', feature='review')
    # RULE-7's audit found its proof weak, and RULE-8's test fails, so its
    # strong cell reads `waiting`: neither is a row.
    made.audit('RULE-7', feature='review',
               observations=('PROOF-7 reads 401 alone.',))
    return made


@pytest.fixture
def queued():
    made = _project()
    yield made
    made.close()


def _rows(payload, need=None):
    return {row['rule']: row for row in payload['queue']
            if need is None or row['need'] == need}


# purlin: states PROOF-33
def test_a_hand_check_is_a_manual_test_whose_level_asks_for_more(queued):
    payload = queued.payload()
    rows = _rows(payload, 'hand check')
    assert sorted(rows) == ['RULE-3'], rows
    lower = queued.rule('RULE-2', 'review')
    assert sorted(lower['cells']) == ['passed'], (
        'marked passed, so it is asked for no hand check and waits on nobody')
    assert lower['flags']['manual'] is False, lower
    everything = _rows(payload)
    assert 'RULE-2' not in everything, 'a rule whose level is passed'
    assert 'RULE-4' not in everything, 'a rule with no test is build work'
    assert 'RULE-6' not in everything, 'a rule waiting for the audit'
    assert queued.rule('RULE-6', 'review')['cells']['strong']['word'] == (
        'not audited')
    for rule, word in (('RULE-7', 'weak'), ('RULE-8', 'waiting')):
        assert queued.rule(rule, 'review')['cells']['strong']['word'] == word
        assert rule not in everything, 'a rule whose strong cell is ' + word


# purlin: states PROOF-33
def test_the_queue_is_empty_under_the_passed_gate(queued):
    queued.config_value('gate', 'passed')
    payload = queued.payload()
    assert payload['queue'] == [], payload['queue']
    assert payload['summary']['queue'] == 0, payload['summary']
    assert 'strong' not in payload['features'][0]['rules'][0]['cells']


# purlin: states PROOF-63
def test_a_signature_row_is_a_rule_that_met_its_tests_and_audit(queued):
    payload = queued.payload()
    rows = _rows(payload, 'signature')
    assert sorted(rows) == ['RULE-1', 'RULE-5'], rows
    assert rows['RULE-1']['word'] == 'stale'
    assert rows['RULE-5']['word'] == 'unsigned'
    # RULE-3 needs a signature too, and it is one row, a hand check.
    assert [row['rule'] for row in payload['queue']].count('RULE-3') == 1
    assert _rows(payload)['RULE-3']['need'] == 'hand check'
    queued.config_value('gate', 'strong')
    assert _rows(queued.payload(), 'signature') == {}


# purlin: states PROOF-34
def test_each_row_says_what_it_needs_and_the_command_that_answers(queued):
    rows = _rows(queued.payload())
    for row in rows.values():
        assert sorted(row) == ['command', 'feature', 'level', 'need', 'owner',
                               'reasons', 'rule', 'text', 'word'], row
        assert row['feature'] == 'review' and row['owner'] == 'review'
        assert row['level'] == 'signed', row
    hand = rows['RULE-3']
    assert (hand['need'], hand['word'], hand['reasons']) == (
        'hand check', 'manual test', ['manual proof']), hand
    assert hand['command'] == (
        'purlin:sign review RULE-3 --note "<what you saw>"'), hand
    assert hand['text'] == (
        'A rule a person has to read carries no automated proof')
    signature = rows['RULE-5']
    assert (signature['need'], signature['word']) == (
        'signature', 'unsigned'), signature
    assert signature['command'] == 'purlin:sign review RULE-5', signature
    assert rows['RULE-1']['reasons'] == [
        'hashes changed after the signature'], rows['RULE-1']


# purlin: states PROOF-35
def test_the_queue_reads_by_feature_then_rule_number(queued):
    assert [row['rule'] for row in queued.payload()['queue']] == [
        'RULE-1', 'RULE-3', 'RULE-5']


# purlin: states PROOF-35
def test_a_feature_named_first_in_the_alphabet_reads_first():
    made = Project(gate='strong', spec=None)
    try:
        for name in ('zeta', 'alpha'):
            made.spec(
                '# Feature: %s\n\n> Scope: src/login.py\n\n## Rules\n\n'
                '- RULE-1: A person reads it\n- RULE-2: A person reads it '
                'too\n\n## Proof\n\n'
                '- PROOF-1 (RULE-1): Read it; verify it reads well @manual\n'
                '- PROOF-2 (RULE-2): Read it; verify it reads well @manual\n'
                % name, name=name, category='core')
        rows = [(row['owner'], row['rule'])
                for row in made.payload()['queue']]
        assert rows == [('alpha', 'RULE-1'), ('alpha', 'RULE-2'),
                        ('zeta', 'RULE-1'), ('zeta', 'RULE-2')], rows
    finally:
        made.close()


# purlin: states PROOF-36
def test_a_global_anchor_rule_is_named_once():
    made = Project(gate='strong')
    try:
        made.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches @manual\n',
            name='security', category='_anchors')
        made.spec(
            '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
            '- RULE-1: A person reads the page\n\n## Proof\n\n'
            '- PROOF-1 (RULE-1): Read the page; verify it names the wait '
            '@manual\n')
        data = made.payload()
        entries = [(row['owner'], row['rule']) for row in data['queue']]
        assert sorted(entries) == [('login', 'RULE-1'),
                                   ('security', 'RULE-1')], entries
        assert data['summary']['hand_checks'] == 2, data['summary']
    finally:
        made.close()


# purlin: states PROOF-62
def test_the_rollup_and_the_summary_count_the_queue(queued):
    payload = queued.payload()
    rollup = payload['features'][0]['rollup']
    assert (rollup['queue'], rollup['hand_checks']) == (3, 1), rollup
    summary = payload['summary']
    assert (summary['queue'], summary['hand_checks']) == (3, 1), summary
    queued.config_value('gate', 'strong')
    summary = queued.payload()['summary']
    assert (summary['queue'], summary['hand_checks']) == (1, 1), summary


# purlin: states PROOF-64
def test_the_status_report_counts_the_queue_in_one_line(queued):
    lines = purlin_status.sync_status(queued.root).splitlines()
    assert 'Queue: 3 rules. 1 hand check, 2 signatures.' in lines, lines
    assert '→ Queue: 3 rules need a person. Run purlin:sign.' in lines, lines
    queued.config_value('gate', 'passed')
    text = purlin_status.sync_status(queued.root)
    assert 'Queue:' not in text, text
