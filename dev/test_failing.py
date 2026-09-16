"""Tests for the `failing` flag: where a test backing a rule last failed.

A failing test only holds a rule in a lower state, so the state alone cannot
say a test is failing. The throwaway project is `dev/test_approvals.py`'s.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from test_approvals import Project  # noqa: E402


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


@pytest.mark.proof("states", "PROOF-38", "RULE-32", tier="integration")
def test_a_failing_test_is_named_where_it_failed(project):
    project.proofs()
    project.record({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
    one, two = project.rule('RULE-1'), project.rule('RULE-2')
    assert one['flags']['failing'] is True
    assert 'failing: the record' in one['reasons'], one['reasons']
    assert two['flags']['failing'] is False
    assert project.payload()['project_rollup']['failing'] == 1

    project.proofs({'PROOF-1': 'pass', 'PROOF-2': 'fail'})
    two = project.rule('RULE-2')
    assert two['flags']['failing'] is True
    assert 'failing: this checkout' in two['reasons'], two['reasons']
    assert project.payload()['project_rollup']['failing'] == 2
