"""Tests for the `failed` word: where a test backing a rule failed.

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

from purlin import evidence as purlin_evidence  # noqa: E402
from test_signatures import Project  # noqa: E402


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


# purlin: states PROOF-11
def test_a_failing_test_is_named_where_it_failed(project):
    here = purlin_evidence.host_os()
    project.proofs()
    project.evidence({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
    one, two = project.rule('RULE-1'), project.rule('RULE-2')
    assert one['cells']['passed']['word'] == 'failed', one
    assert one['flags']['failing'] is True
    assert 'failing: %s, local' % here in one['cells']['passed']['reasons'], one
    assert two['flags']['failing'] is False
    assert one['bucket'] == 'failing', one
    assert project.payload()['summary']['failing'] == 1

    other = 'windows' if here != 'windows' else 'linux'
    project.evidence({'PROOF-1': 'fail', 'PROOF-2': 'fail'})
    project.evidence({'PROOF-1': 'fail', 'PROOF-2': 'fail'}, runner='ci',
                     source='ci', os_name=other)
    two = project.rule('RULE-2')
    assert two['flags']['failing'] is True
    assert two['cells']['passed']['reasons'] == [
        'failing: %s, local' % here, 'failing: %s, ci' % other], two
    assert project.payload()['summary']['failing'] == 2
