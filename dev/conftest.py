"""Load the Purlin proof plugin for pytest."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'proof'))
from pytest_purlin import pytest_configure  # noqa: F401

# `dev/fixtures/` holds whole consumer projects, each with its own conftest and
# its own `.purlin/plugins/` copy of the proof plugin. They are data this
# repository's tests build and drive, never tests of this repository, and a
# consumer's root conftest is a nested one here, which pytest refuses to load.
collect_ignore_glob = ['fixtures/*']
