"""The consumer project's one test file: one plain proof, one scoped to Linux.

PROOF-2 is tagged `@env(linux)` in the spec, so it reaches `strong` only when a
Linux job's record says it passed. The marker above each test names the feature
and the proof and nothing else: which rule a proof serves and which operating
system it needs are the spec's to say, and CI reads them from there.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from greeting import greet, os_tag  # noqa: E402


# purlin: greeting PROOF-1
def test_greet_names_and_empty():
    assert greet("Ada") == "Hello, Ada!"
    assert greet("") == "Hello, world!"


# purlin: greeting PROOF-2
def test_os_tag_is_linux():
    assert os_tag() == "linux", (
        "os_tag() returned {!r}; RULE-2 is a claim about a Linux host and only "
        "a Linux host can prove it".format(os_tag()))
