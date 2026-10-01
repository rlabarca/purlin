#!/usr/bin/env python3
"""The test comments to correct: a comment naming a proof whose wording changed.

    python3 scripts/mcp/purlin/wording.py [--project-root DIR] [--file PATH ...]

Prints each entry's `text`, one per line, then `<n> test comments to correct.`,
`1 test comment to correct.` or `No test comment to correct.`, and exits 0.

A stub from the base commit of `dev/plans/d115-plan.md`: it finds no comment
until the lane `states` fills it.
"""

import sys

STALE = ('%s:%d names %s %s, whose wording changed after the test was last changed in %s: '
         'it read "%s" and now reads "%s". ')
STALE_BUILD = ('Run purlin:build %s to make the test show it; the line clears once the test '
               'changes.')
STALE_MOVE = 'Its old wording is now %s: move the comment there.'

NONE_TO_CORRECT = 'No test comment to correct.'


def stale_comments(project_root, features, scanned=None):
    """One entry per test comment naming a proof whose wording, at the commit that last
    changed the test, differs from its wording now. A test is last changed at the newest
    commit git blame names for the lines below its comment down to the test's last line,
    or for any line of its file when the file is run whole. A test with an uncommitted
    line is never named. By file, then line.
    Each: {'file','line','feature','id','commit' (sha7),'old','new','now_under','text'}."""
    return []


def test_last_change(project_root, path, marker_line, end_line):
    """`(sha, author email)` of that commit, or None."""
    return None


def main(argv=None):
    print(NONE_TO_CORRECT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
