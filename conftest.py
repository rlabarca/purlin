"""Keep pytest's collection to this repository's own tests.

`dev/fixtures/` holds whole sample projects that the tests copy and run. One
of them declares `pytest_plugins` in its own `conftest.py`, which pytest
refuses to load from below the root directory, so collecting that tree stops
the session before a single test runs. Nothing under `dev/fixtures/` is a test
of this repository, so collection never descends into it.

This file is also what framework detection reads pytest off, so the framework
this repository proves itself with is named by the same file that keeps the
session collectable.
"""

collect_ignore = ['dev/fixtures']
