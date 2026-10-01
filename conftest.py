"""Keep pytest's collection to this repository's own tests.

`dev/fixtures/` holds whole sample projects that the tests copy and run, and
their own test files are tests of those projects, not of this repository. A
session collecting them would import each sample's code against this
repository's root, so collection never descends into that tree.

This file is also what framework detection reads pytest off, so the framework
this repository proves itself with is named by the same file that keeps the
session collectable.
"""

collect_ignore = ['dev/fixtures']
