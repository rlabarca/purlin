"""Load the Purlin proof plugin for pytest."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'proof'))
from pytest_purlin import pytest_configure  # noqa: F401
