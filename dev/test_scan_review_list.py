"""Tests for the review list `scripts/report/scan.py` prints after the rollup.

A reader without a checkout, the QA tool in Claude Desktop among them, works
the review list rule by rule, so the scan prints it one line per rule. The
repository fixture is `dev/test_scan.py`'s, scanned by path.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'report'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import scan as scan_module  # noqa: E402
from test_scan import SPEC, git, make_project  # noqa: E402


def _payload(items, states):
    features = {}
    for (feature, rule), state in states.items():
        features.setdefault(feature, []).append(
            {'feature': feature, 'id': rule, 'state': state})
    return {'features': [{'name': name, 'rules': rules}
                         for name, rules in features.items()],
            'review_list': [{'feature': feature, 'owner': feature,
                             'rule': rule, 'risk': risk, 'reason': reason}
                            for feature, rule, risk, reason in items]}


@pytest.mark.proof("records", "PROOF-28", "RULE-25")
def test_the_list_is_one_line_per_rule_in_review_order():
    payload = _payload(
        [('billing', 'RULE-2', 'low', 'no_expected_value'),
         ('login', 'RULE-10', 'high', 'risk high'),
         ('login', 'RULE-3', 'high', 'stale; risk high'),
         ('auth', 'RULE-1', 'medium', 'risk medium')],
        {('billing', 'RULE-2'): 'Recorded', ('login', 'RULE-10'): 'Reviewed',
         ('login', 'RULE-3'): 'Stale', ('auth', 'RULE-1'): 'Tested'})
    lines = scan_module.review_list_text(payload).splitlines()
    assert lines[0] == 'Review list: 4 rules.'
    order = [line.split()[1] + ' ' + line.split()[2] for line in lines[1:]]
    assert order == ['login RULE-3', 'login RULE-10', 'auth RULE-1',
                     'billing RULE-2'], lines
    assert lines[1].split()[:4] == ['high', 'login', 'RULE-3', 'Stale']
    assert lines[1].endswith('stale; risk high'), lines[1]
    assert lines[3].split()[:4] == ['medium', 'auth', 'RULE-1', 'Tested']
    assert lines[4].endswith('no_expected_value'), lines[4]
    assert scan_module.review_list_text(_payload([], {})) == \
        'Review list: no rule needs a person.'


@pytest.mark.proof("records", "PROOF-29", "RULE-25", tier="integration")
def test_the_scan_prints_the_list_after_the_rollup(tmp_path):
    source = str(tmp_path / 'source')
    make_project(source)
    spec = os.path.join(source, 'specs', 'core', 'greeting.md')
    with open(spec, 'w', encoding='utf-8') as handle:
        handle.write(SPEC.replace('returns `Hello, <name>!`',
                                  'returns `Hello, <name>!` [risk: high]'))
    git(source, 'commit', '--quiet', '-am', 'a high-risk rule')
    bare = str(tmp_path / 'origin.git')
    git(tmp_path, 'init', '--bare', '--quiet', '-b', 'main', bare)
    git(source, 'push', '--quiet', bare, 'main')
    text = scan_module.scan(bare, 'main')
    assert 'Review list:' in text
    assert text.index('Review list:') > text.index('rules.')
    rows = [line.split() for line in text.splitlines()
            if 'greeting RULE-1' in line]
    assert rows and rows[0][:3] == ['high', 'greeting', 'RULE-1'], text
    assert len(rows[0]) >= 4, rows
