"""The readers and the one check the skill test files share.

Each spec under `specs/skills/` holds one list: the commands and the paths
its skill must name. `must_name` reads a skill and answers the ones it does
not name, one line each, so a test body is one assertion and its failure
prints what is missing. `dev/test_skill_<name>.py` and
`dev/test_purlin_agent.py` import what they use from here. This file holds no
test and no marker, and pytest does not collect it.

Prose wraps, so a command a skill writes over a line break is still named:
`flat()` collapses runs of whitespace before a name is searched for. A name
that must sit on one line of the source goes through `same_line()` instead.
"""

import contextlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AGENT = 'agents/purlin.md'


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def skill_path(name):
    return 'skills/%s/SKILL.md' % name


def flat(text):
    return re.sub(r'\s+', ' ', text)


def not_named(text, names):
    """Each of `names` the text does not hold, line wrapping ignored."""
    text = flat(text)
    return [name for name in names if name not in text]


def must_name(skill, commands=(), paths=()):
    """The problems with what a skill names: one `<skill> does not name <x>`
    for each command and each path its text does not hold, commands first."""
    missing = not_named(read(skill_path(skill)), tuple(commands) + tuple(paths))
    return ['%s does not name %s' % (skill, name) for name in missing]


def same_line(rel, names):
    """A problem unless one line of the file holds every one of `names`."""
    for line in read(rel).splitlines():
        if all(name in line for name in names):
            return []
    return ['%s has no single line carrying all of %s'
            % (rel, ', '.join(repr(name) for name in names))]


def sentences_with(rel, names):
    """Each sentence of the file, line wrapping ignored, that holds every one
    of `names`."""
    sentences = re.split(r'(?<=\.)\s+(?=[A-Z`*])', flat(read(rel)))
    return [s for s in sentences if all(name in s for name in names)]


@contextlib.contextmanager
def copy_without(rel, name):
    """While open, `rel` reads as a copy with every `name` taken out. The file
    on disk is never touched."""
    real = read
    original = real(rel)
    # A name the prose wraps over a line break is taken out too.
    wrapped = re.compile(r'\s+'.join(re.escape(word) for word in name.split()))
    text, taken = wrapped.subn('', original)
    assert taken, 'there is no %r in %s to take out' % (name, rel)
    globals()['read'] = lambda path: text if path == rel else real(path)
    try:
        yield text
    finally:
        globals()['read'] = real
