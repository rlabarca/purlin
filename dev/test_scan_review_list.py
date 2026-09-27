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


def _payload(review=(), sign=()):
    """A payload carrying only the two lists, as the scan reads them.

    Each item is `(feature, rule, bar, cell, kind)`, which is the shape both
    lists write minus the owner, filled in here as the feature itself.
    """
    def rows(items):
        return [{'feature': feature, 'owner': feature, 'rule': rule,
                 'bar': bar, 'cell': cell, 'kind': kind, 'why': [kind]}
                for feature, rule, bar, cell, kind in items]
    return {'review_list': rows(review), 'sign_list': rows(sign)}


@pytest.mark.proof("records", "PROOF-28", "RULE-25")
def test_the_lists_are_one_line_per_rule_in_their_own_order():
    payload = _payload(
        review=[('billing', 'RULE-2', 'passed', 'strong', 'held'),
                ('login', 'RULE-10', 'strong', 'strong', 'unsettled')],
        sign=[('auth', 'RULE-1', 'strong', 'signed', 'unsigned')])
    lines = scan_module.review_list_text(payload).splitlines()

    assert lines[0] == '3 rules need a person.'
    assert lines[1] == 'Review list: 2'
    assert lines[2].split()[:4] == ['strong', 'login', 'RULE-10', 'strong']
    assert lines[2].endswith('unsettled'), lines[2]
    assert lines[3].split()[:4] == ['passed', 'billing', 'RULE-2', 'strong']
    assert lines[3].endswith('held'), lines[3]
    assert lines[4] == 'Sign list: 1'
    assert lines[5].split()[:4] == ['strong', 'auth', 'RULE-1', 'signed']
    assert lines[5].endswith('unsigned'), lines[5]
    assert scan_module.review_list_text(_payload()) == \
        'No rule needs a person.'


@pytest.mark.proof("records", "PROOF-28", "RULE-25")
def test_one_rule_reads_in_the_singular():
    text = scan_module.review_list_text(
        _payload(review=[('login', 'RULE-3', 'strong', 'strong', 'held')]))
    assert text.splitlines()[0] == '1 rule needs a person.'


@pytest.mark.proof("records", "PROOF-29", "RULE-25", tier="integration")
def test_the_scan_prints_the_list_after_the_rollup(tmp_path):
    """A `@manual` proof is the one thing no machine can run.

    The gate is `strong`, so the strong cell exists, and the rule lands on
    Review reading `manual test`.
    """
    source = str(tmp_path / 'source')
    make_project(source)
    spec = os.path.join(source, 'specs', 'core', 'greeting.md')
    with open(spec, 'w', encoding='utf-8') as handle:
        handle.write(SPEC.replace('returns `Hello, <name>!`',
                                  'returns `Hello, <name>!` [bar: strong]')
                         .replace('verify `Hello, Ada!` @unit',
                                  'verify `Hello, Ada!` @manual'))
    git(source, 'commit', '--quiet', '-am', 'a rule proved by hand')
    bare = str(tmp_path / 'origin.git')
    git(tmp_path, 'init', '--bare', '--quiet', '-b', 'main', bare)
    git(source, 'push', '--quiet', bare, 'main')

    text = scan_module.scan(bare, 'main')

    assert 'Review list:' in text
    assert text.index('Review list:') > text.index('proof line')
    rows = [line.split() for line in text.splitlines()
            if 'greeting RULE-1' in line]
    assert rows and rows[0][:3] == ['strong', 'greeting', 'RULE-1'], text
    assert rows[0][3] == 'strong', text
    assert rows[0][4:6] == ['manual', 'test'], text
