"""The readers and the checks the skill test files share.

Each spec under `specs/skills/` holds one list: the commands and the paths
its skill must name. `must_name` reads a skill and answers the ones it does
not name, one line each, so a test body is one assertion and its failure
prints what is missing. `dev/test_skill_<name>.py` and
`dev/test_purlin_agent.py` import what they use from here. This file holds no
test and no marker, and pytest does not collect it.

Prose wraps, so a command a skill writes over a line break is still named:
`not_named()` reads a line break, with the white space around it, as one
space before a name is searched for, and holds every other space as written.
A name is held whole: `purlin:specs` does not name `purlin:spec`. A name that
must sit on one line of the source goes through `same_line()` instead.
"""

import contextlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AGENT = 'agents/purlin.md'


def skill_files():
    """Every `skills/<name>/SKILL.md`, as it stands, in name order."""
    return sorted(path.relative_to(ROOT).as_posix()
                  for path in (ROOT / 'skills').glob('*/SKILL.md'))


def reference_files():
    """Every `references/**/*.md`, in name order."""
    return sorted(path.relative_to(ROOT).as_posix()
                  for path in (ROOT / 'references').rglob('*.md'))


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8')


def skill_path(name):
    return 'skills/%s/SKILL.md' % name


def flat(text):
    return re.sub(r'\s+', ' ', text)


# What may not follow a name that ends in a letter, a digit or `_`: a
# character that carries the word on, or a `.`, `/` or `:` that joins it to
# one more. `purlin:spec` is not named by `purlin:specs`, `purlin:spec-from-code`
# or `purlin:spec:x`, and is named by `purlin:spec.` ending a sentence.
_GOES_ON = r'(?![\w-]|[./:]\w)'


def holds(text, name):
    """True where `text` holds `name` whole, each space of it as written: the
    name is not followed by a character that could carry it on."""
    ends = _GOES_ON if re.search(r'\w$', name) else ''
    return re.search(re.escape(name) + ends, text) is not None


def not_named(text, names):
    """Each of `names` the text does not hold whole, line wrapping ignored:
    a line break and the white space around it read as one space."""
    text = re.sub(r'\s*\n\s*', ' ', text)
    return [name for name in names if not holds(text, name)]


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


def under_heading(text, heading):
    """The part of a Markdown text under the heading `heading`, up to the
    next heading of the same or a higher level; empty where there is none."""
    found = re.search(r'^(#+) %s\n' % re.escape(heading), text, re.M)
    if not found:
        return ''
    rest = text[found.end():]
    end = re.search(r'^#{1,%d} ' % len(found.group(1)), rest, re.M)
    return rest[:end.start()] if end else rest


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


# --- what a skill tells an agent to run --------------------------------------

# A path into one of the five folders an install carries and a skill may
# name. It starts a word, or follows the plugin root's `}/`; a path that
# follows any other folder, as in `my/scripts/x.py`, is not the repository's.
_PATH_RE = re.compile(
    r'(?:(?<=\}/)|(?<![\w./<>*-]))'
    r'(?:scripts|references|templates|skills|docs)/[\w./<>*{}\[\]-]*')
# What makes a path a pattern and not one path: `<name>`, `*`, `{a,b}`, `[`.
_PATTERN_RE = re.compile(r'[<>*{}\[\]]')


def named_paths(text):
    """Each path under `scripts/`, `references/`, `templates/`, `skills/` or
    `docs/` the text names, once, in the order named. A `#section` after a
    path and the full stop or slash ending it are not part of it; a path
    holding a placeholder or a wildcard names no one file and is left out."""
    found = []
    for path in _PATH_RE.findall(text):
        path = path.rstrip('./')
        if '/' in path and not _PATTERN_RE.search(path) and path not in found:
            found.append(path)
    return found


def _is_here(path):
    """True where the repository holds `path` under that very name, letter
    for letter. A file system that ignores case finds `references/Glossary.md`
    where the repository holds `glossary.md`, so each part is looked for in
    its folder's own listing."""
    folder = ROOT
    for part in path.split('/'):
        if not folder.is_dir() or part not in os.listdir(folder):
            return False
        folder = folder / part
    return True


def absent_paths(text):
    """Each path `named_paths` reads that is no file or folder here, under
    the very name the text gives it."""
    return [path for path in named_paths(text) if not _is_here(path)]


_SCRIPT_RE = re.compile(r'scripts/[\w/]+\.py')
_FLAG_RE = re.compile(r'(?<![\w-])--[a-z][a-z-]*')
_HELP = {}


def _help(script, *before):
    """What `<script> [<subcommand>] --help` prints, on either stream."""
    key = (script,) + before
    if key not in _HELP:
        ran = subprocess.run(
            [sys.executable, str(ROOT / script)] + list(before) + ['--help'],
            capture_output=True, text=True, encoding='utf-8', cwd=str(ROOT))
        _HELP[key] = ran.stdout + ran.stderr
    return _HELP[key]


def script_flags(script):
    """Every `--flag` the script takes, read from its `--help`, and for a
    script with subcommands from each subcommand's `--help` too."""
    text = _help(script)
    flags = set(_FLAG_RE.findall(text))
    choices = re.search(r'\{([a-z][a-z,-]*)\}', text)
    for sub in choices.group(1).split(',') if choices else ():
        flags.update(_FLAG_RE.findall(_help(script, sub)))
    return flags


def passed_flags(text):
    """`(script, flag)` for each `--flag` written after a `scripts/**/*.py`
    on one line of the text, a line ending in a backslash read with the next."""
    found = []
    for line in re.sub(r'\\\n', ' ', text).splitlines():
        scripts = list(_SCRIPT_RE.finditer(line))
        for at, script in enumerate(scripts):
            end = scripts[at + 1].start() if at + 1 < len(scripts) else None
            for flag in _FLAG_RE.findall(line[script.end():end]):
                if (script.group(), flag) not in found:
                    found.append((script.group(), flag))
    return found


def unknown_flags(text):
    """Each `(script, flag)` the text passes that the script does not take. A
    script that is not in the repository is `absent_paths`' to name."""
    return [(script, flag) for script, flag in passed_flags(text)
            if (ROOT / script).is_file() and flag not in script_flags(script)]


STATUS_TOOL = 'mcp__plugin_purlin_purlin__sync_status'
STATUS_SCRIPT = 'scripts/run/purlin_status.py'


def status_unnamed(skill, text):
    """The problems with how a skill's text names the status: for a text
    holding `sync_status`, one `<skill> does not name <x>` for the tool as a
    session lists it and for the script that prints the same status, where
    the text does not hold it. A text that never names `sync_status` has
    none."""
    if 'sync_status' not in text:
        return []
    return ['%s does not name %s' % (skill, name)
            for name in not_named(text, (STATUS_TOOL, STATUS_SCRIPT))]


def dev_paths(text):
    """Each line of the text that holds `dev/`, every `/dev/null` set aside."""
    return [line for line in text.splitlines()
            if 'dev/' in line.replace('/dev/null', '')]


def json_block_under(text, heading):
    """The first fenced `json` block under the heading that starts with
    `heading`, parsed."""
    import json
    section = re.search(r'^#+ %s.*?(?=^#+ |\Z)' % re.escape(heading), text,
                        re.M | re.S)
    assert section, 'there is no heading %r' % heading
    block = re.search(r'```json\n(.*?)```', section.group(), re.S)
    assert block, 'there is no json block under %r' % heading
    return json.loads(block.group(1))
