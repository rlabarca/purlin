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
from sign_project import SPEC, Project  # noqa: E402


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


# purlin: states PROOF-11
def test_an_env_proof_is_read_only_from_its_own_system(project):
    here = purlin_evidence.host_os()
    other = 'windows' if here != 'windows' else 'linux'
    project.spec(SPEC.replace('and a token\n',
                              'and a token @env(%s)\n' % other))
    project.proofs()
    project.evidence({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
    one = project.rule('RULE-1')
    assert one['cells']['passed']['word'] == 'not run', one
    assert one['cells']['passed']['reasons'] == [
        '%s: no run yet' % other], one
    assert one['flags']['failing'] is False, one
    assert project.payload()['summary']['failing'] == 0

    project.evidence({'PROOF-1': 'fail', 'PROOF-2': 'pass'}, runner='ci',
                     source='ci', os_name=other)
    one = project.rule('RULE-1')
    assert one['cells']['passed']['word'] == 'failed', one
    assert one['flags']['failing'] is True, one
    assert one['cells']['passed']['reasons'] == [
        'failing: %s, ci' % other], one
