"""Tests for the `failed` word: where a test backing a rule last failed.

A word like `no test` would hide a failing test, so the passed cell names the
failure and where it happened. The throwaway project is
`dev/test_signatures.py`'s.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from test_signatures import Project  # noqa: E402


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


@pytest.mark.proof("states", "PROOF-11", "RULE-9", tier="integration")
def test_a_failing_test_is_named_where_it_failed(project):
    project.proofs()
    project.record({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
    one, two = project.rule('RULE-1'), project.rule('RULE-2')
    assert one['cells']['passed']['word'] == 'failed', one
    assert one['flags']['failing'] is True
    assert 'failing: the record' in one['cells']['passed']['reasons'], one
    assert two['flags']['failing'] is False
    assert one['bucket'] == 'failing', one
    assert project.payload()['summary']['failing'] == 1

    project.proofs({'PROOF-1': 'pass', 'PROOF-2': 'fail'})
    two = project.rule('RULE-2')
    assert two['flags']['failing'] is True
    assert 'failing: this checkout' in two['cells']['passed']['reasons'], two
    assert project.payload()['summary']['failing'] == 2
