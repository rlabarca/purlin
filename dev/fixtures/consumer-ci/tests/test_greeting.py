"""The consumer project's one test file: one plain proof, one scoped to Linux.

PROOF-2 is tagged `@env(linux)` in the spec, so it reaches `strong` only when a
Linux job's record says it passed. The marker here names the feature, the proof
and the rule and nothing else: which operating system a proof needs is the
spec's to say, and CI reads it from there to build the matrix.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from greeting import greet, os_tag  # noqa: E402


@pytest.mark.proof("greeting", "PROOF-1", "RULE-1")
def test_greet_names_and_empty():
    assert greet("Ada") == "Hello, Ada!"
    assert greet("") == "Hello, world!"


@pytest.mark.proof("greeting", "PROOF-2", "RULE-2")
def test_os_tag_is_linux():
    assert os_tag() == "linux", (
        "os_tag() returned {!r}; RULE-2 is a claim about a Linux host and only "
        "a Linux host can prove it".format(os_tag()))
