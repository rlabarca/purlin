"""The consumer project's one test file: one agnostic proof, one @on(ubuntu-24).

The `platforms=` kwarg on PROOF-2's marker is what makes the pytest plugin write
`specs/core/greeting.proofs-unit@ubuntu-24.json` instead of the agnostic file,
with `PURLIN_PLATFORM` naming the id. On any other host the proof still runs, but
its result lands under that host's id and satisfies nothing the spec declared.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from greeting import greet, platform_tag  # noqa: E402


@pytest.mark.proof("greeting", "PROOF-1", "RULE-1")
def test_greet_names_and_empty():
    assert greet("Ada") == "Hello, Ada!"
    assert greet("") == "Hello, world!"


@pytest.mark.proof("greeting", "PROOF-2", "RULE-2", platforms=("ubuntu-24",))
def test_platform_tag_is_linux():
    assert platform_tag() == "linux", (
        "platform_tag() returned {!r}; RULE-2 is a claim about an Ubuntu 24.04 "
        "host and only that host can prove it".format(platform_tag()))
