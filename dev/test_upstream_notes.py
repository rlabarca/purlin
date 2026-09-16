"""Tests for the `> Note:` lines a pinned anchor's local copy carries.

A note is the consumer's own free text beside the tracking fields, so a sync
that rewrites those fields keeps it. The anchor repo and project fixtures are
`dev/test_upstream.py`'s.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DEV)

from test_upstream import (_add, _advance, _copy_text, upstream,  # noqa: E402,F401
                           workspace)

NOTES = ('run the setup script first', 'the pin moves on each release')


@pytest.mark.proof("upstream", "PROOF-23", "RULE-23", tier="integration")
def test_a_sync_keeps_the_notes(workspace):  # noqa: F811
    _add(workspace)
    path = upstream.anchor_path(workspace.root, 'no_eval')
    text = _copy_text(workspace)
    pinned = next(line for line in text.splitlines()
                  if line.startswith('> Pinned:'))
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text.replace(
            pinned, pinned + ''.join('\n> Note: %s' % note for note in NOTES)))
    new_sha = _advance(workspace)
    upstream.sync(workspace.root, names=['no_eval'])
    lines = _copy_text(workspace).splitlines()
    assert '> Pinned: %s' % new_sha in lines
    notes = [line for line in lines if line.startswith('> Note:')]
    assert notes == ['> Note: %s' % note for note in NOTES], lines
