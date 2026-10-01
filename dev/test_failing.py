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


def _other(here):
    """An operating system that is not this machine's."""
    return 'windows' if here != 'windows' else 'linux'


def _word(os_name):
    """The system as a person reads it: `Windows`, `macOS` or `Linux/Unix`."""
    return {'windows': 'Windows', 'macos': 'macOS',
            'linux': 'Linux/Unix'}[os_name]


def _tagged_for(project, os_name):
    """`PROOF-1` tagged `@env` for `os_name`."""
    project.spec(SPEC.replace('and a token\n',
                              'and a token @env(%s)\n' % os_name))


# purlin: states PROOF-11
def test_a_failing_test_is_named_where_it_failed(project):
    here = purlin_evidence.host_os()
    project.evidence({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
    one, two = project.rule('RULE-1'), project.rule('RULE-2')
    assert one['cells']['passed']['word'] == 'failed', one
    assert one['flags']['failing'] is True
    assert ('failing: %s, local' % _word(here)
            in one['cells']['passed']['reasons']), one
    assert two['flags']['failing'] is False
    assert one['bucket'] == 'failing', one
    assert project.payload()['summary']['failing'] == 1


# purlin: states PROOF-156
def test_an_env_proof_failing_on_its_own_system_is_failed(project):
    other = _other(purlin_evidence.host_os())
    _tagged_for(project, other)
    project.evidence({'PROOF-1': 'fail', 'PROOF-2': 'pass'})
    project.evidence({'PROOF-1': 'fail', 'PROOF-2': 'pass'}, runner='ci',
                     source='ci', os_name=other)
    one = project.rule('RULE-1')
    assert one['cells']['passed']['word'] == 'failed', one
    assert one['flags']['failing'] is True, one
    assert one['cells']['passed']['reasons'] == [
        'failing: %s, ci' % _word(other)], one
