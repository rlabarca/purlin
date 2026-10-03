#!/usr/bin/env python3
"""Bring a project an older Purlin set up onto this release.

    python3 scripts/init/update.py [--yes | --apply ID[,ID...]]
        [--test-command TOOL=COMMAND ...] [--project-root DIR]

`purlin:init --update` is the command you run, and init hands it here. This
file is the part of the upgrade that has to be deterministic, so the skill
asks and this script edits.

`pending(project_root)` returns the migrations a project still needs: an id, one
line saying what it does, and the files it touches. The run prints that list
before it asks, and `sync_status` reads the same function, so the advisory you
see and the work this script does cannot disagree. The detectors read the
layout v0.9.5 left, and a project lands straight on this release's layout.
Every migration asks before it writes, each question on a line of its own,
and every file it rewrites is copied first to
`.purlin/runtime/update-backup/`, at its own path, which git ignores. `--yes`
answers yes to every migration's question and accepts each test command
proposed. `--apply <id>[,<id>...]` applies exactly the migrations named and
asks nothing, and `--test-command <tool>=<command>` writes that command for a
test tool in place of the one proposed. A run told to apply prints one line
naming the migrations in place of the pending list. The run prints one line
of totals for each migration, then what it left for the owner and the lines
that need the owner; each file's own line goes to
`.purlin/runtime/update-backup/update.log`. A workflow that names a proof
file is removed only on a yes typed for that file, so under `--yes` and
`--apply` each is kept and named. A file this release deletes rather than
rewrites is left in git history instead of copied.

Exit codes: 0 nothing pending or the run applied what was, 1 the settings
file cannot be read, 2 no Purlin project at that root or a flag's value
cannot be used.
"""

import argparse
import ast
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

EXIT_OK, EXIT_UNREADABLE, EXIT_BAD_INVOCATION = 0, 1, 2

PLUGIN_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
_MCP_DIR = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import (console as console_module,                # noqa: E402
                    markers as markers_module,
                    specs as specs_module)
import config_engine                                          # noqa: E402
# --- what 0.9.5 wrote, which the upgrade finds and rewrites --------------

PROOF_FILE_GLOB = '*.proofs-*.json'
RUN_FILE_GLOB = '*.receipt.json'
DASHBOARD_DATA = '.purlin/report-data.js'
CACHE_DIR = '.purlin/cache'
# A proof is its line and the lines that continue it, up to the next proof,
# rule, heading or blank line. Its tags are the `@word`s that end it, on
# whichever of those lines the last one is, with or without a note in
# brackets after them; an `@word` after `and`, `or` or a comma is prose, as
# the spec reader takes it.
PROOF_START_RE = re.compile(r'^- PROOF-')
PROOF_END_RE = re.compile(r'^(?:- PROOF-|- RULE-|#|[ \t]*\r?\n?$)')
TAGS_AT_END_RE = re.compile(
    r'((?:(?<!\band)(?<!\bor)(?<!,)[ \t\r\n]+@\w+(?:\([^)\n]*\))?)+)'
    r'([ \t\r\n]+\([^()]*\))?[ \t]*\Z')
TAG_RE = re.compile(r'([ \t\r\n]+)@(\w+)(\([^)\n]*\))?')
WINDOWS_TAG = 'windows'
# The kinds of test 0.9.5 named. A project's own markers may name more, such
# as `browser`; the upgrade reads those from the markers themselves.
KINDS = ('unit', 'integration', 'e2e')
KEPT_TAGS = ('manual', 'slow', 'env')
WORKFLOW_MARKER = '.proofs-'
WORKFLOWS = 'workflows'
PRE_PUSH_HOOK = '.git/hooks/pre-push'
DESIGN_FIELD_RE = re.compile(r'^>\s*(Visual-Reference|Visual-Hash):')
# A Figma source is an address at figma.com. A git address that only holds
# the word, such as acme/figma-tokens.git, is a remote anchor's and stays.
FIGMA_SOURCE_RE = re.compile(r'^>\s*Source:\s*\S*figma\.com/', re.I)
PINNED_RE = re.compile(r'^>\s*Pinned:')
# The lines by which a 0.9.5 spec named an anchor, and an anchor named what
# it covered, in the order the upgrade names them.
ANCHOR_FIELDS = ('Requires', 'Global', 'Scope')
ANCHOR_FIELD_RE = re.compile(r'^>\s*(Requires|Global|Scope):')
REQUIRES_RE = re.compile(r'^>\s*Requires:(.*)$', re.M)
GLOBAL_TRUE_RE = re.compile(r'^>\s*Global:\s*true\s*$', re.M | re.I)
NAMED_ONE = ('%s: its rules now cover the whole project, where %d spec named '
             'it: %s. A rule that holds only there belongs in that spec: run '
             'purlin:spec %s.')
NAMED_MANY = ('%s: its rules now cover the whole project, where %d specs '
              'named it: %s. A rule that holds only for some of them belongs '
              'in each of their specs: run purlin:spec %s.')
# The markers v0.9.5's proof plugins read, one per framework, and the files
# its init copied and wired. The upgrade rewrites the first and removes the
# second; nothing else in this release reads either. A mark's feature is any
# name a spec may hold.
_NAME = specs_module.NAME
PYTEST_MARK_RE = re.compile(r'^([ \t]*)@pytest\.mark\.proof\(')
PYTEST_ARGS_RE = re.compile(
    r"""\(\s*["'](%s)["']\s*,\s*["'](PROOF-\d+)["']""" % _NAME)
PYTESTMARK_RE = re.compile(r'pytest\.mark\.proof\(')
TITLE_TAG_RE = re.compile(
    r' ?\[proof:(%s):(PROOF-\d+):RULE-\d+(?::\w+)?\]' % _NAME)
TRAIT_RE = re.compile(r'(\[\s*)?,?\s*Trait\s*\(\s*"PurlinProof"\s*,\s*'
                      r'"(%s):(PROOF-\d+):RULE-\d+(?::\w+)?"\s*\)(\s*\])?'
                      % _NAME)
SHELL_CALL_RE = re.compile(r'^([ \t]*)purlin_proof\s+["\']?(%s)["\']?\s+'
                           r'["\']?(PROOF-\d+)["\']?.*$' % _NAME)
SHELL_HARNESS_RE = re.compile(r'^([ \t]*)(?:source|\.)\s+\S*(?:purlin-proof|'
                              r'shell_purlin)\.sh\S*\s*$')
SHELL_FINISH_RE = re.compile(r'^([ \t]*)purlin_proof_finish\b.*$')
SQL_MARK_RE = re.compile(r'^--[ \t]*@purlin[ \t]+(%s)[ \t]+(PROOF-\d+)'
                         r'[ \t]+RULE-\d+(?:[ \t]+\w+)?[ \t]*$' % _NAME)
# A proof 0.9.5 numbered with a letter, on its spec line and in each form
# of marker; the upgrade gives it a number of its own.
_LETTERED = r'PROOF-\d+[a-z]+'
LETTERED_LINE_RE = re.compile(r'^(-\s+)(%s)(?=\s*\()' % _LETTERED)
PROOF_NUMBER_RE = re.compile(r'^-\s+PROOF-(\d+)')
HIGHEST_PROOF_RE = re.compile(r'^(>[ \t]*Highest-Proof:[ \t]*)(\d+)')
LETTERED_PYTEST_RE = re.compile(
    r"""(pytest\.mark\.proof\(\s*["'](%s)["']\s*,\s*["'])(%s)(?=["'])"""
    % (_NAME, _LETTERED))
LETTERED_TAG_RE = re.compile(r'(\[proof:(%s):)(%s)(?=:)' % (_NAME, _LETTERED))
LETTERED_MARK_RES = (
    re.compile(r'("PurlinProof"\s*,\s*"(%s):)(%s)(?=:)' % (_NAME, _LETTERED)),
    re.compile(r"""(purlin_proof\s+["']?(%s)["']?\s+["']?)(%s)\b"""
               % (_NAME, _LETTERED)),
    re.compile(r'(@purlin[ \t]+(%s)[ \t]+)(%s)\b' % (_NAME, _LETTERED)),
    re.compile(r'(purlin:[ \t]+(%s)[ \t]+)(%s)\b' % (_NAME, _LETTERED)),
)
MARKER_KIND_RES = (
    re.compile(r'\[proof:%s:PROOF-\d+[a-z]*:RULE-\d+:(\w+)\]' % _NAME),
    re.compile(r"""pytest\.mark\.proof\(\s*["']%s["']\s*,\s*["']PROOF-\d+"""
               r"""[a-z]*["']\s*,\s*["']RULE-\d+["']\s*,\s*(?:\w+\s*=\s*)?"""
               r"""["'](\w+)["']""" % _NAME),
    re.compile(r'"PurlinProof"\s*,\s*"%s:PROOF-\d+[a-z]*:RULE-\d+:(\w+)"'
               % _NAME),
    re.compile(r'@purlin[ \t]+%s[ \t]+PROOF-\d+[a-z]*[ \t]+RULE-\d+[ \t]+'
               r'(\w+)' % _NAME),
)
RENUMBERED = '%s %s is now %s'
# A line of a Python docstring that holds a 0.9.5 tag and nothing else: the
# plugin of 0.9.5 read the mark, and the tag beside it said the same thing.
DOC_TAGS_RE = re.compile(
    r'(?:\s*\[proof:%s:PROOF-\d+[a-z]*:RULE-\d+(?::\w+)?\])+\s*' % _NAME)
DOC_OPENER_RE = re.compile(r'^([ \t]*[rRuU]?(?:"""|\'\'\'))(.*)$')
DOC_CLOSER_RE = re.compile(r'^([ \t]*)(.*?)("""|\'\'\')[ \t]*$')
TAG_LINES_WENT = 'removed %d docstring line%s that held only a 0.9.5 tag'
LEFT = ('left %s:%d as it was: write the marker as a comment above each test '
        'by hand')
LEFT_NO_SPEC = ('left %s:%d as it was: it names %s %s, which no spec has. '
                'Write the proof with purlin:spec %s, put %s above the test, '
                "and take the old tag out of the test's title or decorator.")
LEFT_LETTERED = ('left %s:%d as it was: it names %s %s, which is numbered '
                 'with a letter. Run purlin:init --update again and apply '
                 'lettered-proofs')
PLUGIN_DIR = '.purlin/plugins'
PYTEST_PLUGIN = 'pytest_purlin'
CONFTEST_UNREAD = ('left %s as it was: it cannot be read as Python. Remove '
                   'the lines that load pytest_purlin by hand')
REPORTER_RE = re.compile(
    r"""\s*,?\s*["'][^"']*(?:jest|vitest)_purlin\.[jt]s["']""")
XUNIT_LOGGER = 'xunit_purlin'
# The files v0.9.5's init copied into the plugin folder, under the names it
# gave them. A file of any other name there is the project's own and stays.
PLUGIN_COPIES = ('pytest_purlin.py', 'jest_purlin.js',
                 'vitest_purlin.ts', 'purlin-proof.sh',
                 'shell_purlin.sh', 'sql_purlin.sh',
                 'xunit_purlin.cs', 'c_purlin.h',
                 'c_purlin_emit.py', 'phpunit_purlin.php', '.keep')

# The old framework names and the suite each becomes.
OLD_FRAMEWORKS = {'pytest': 'pytest', 'jest': 'jest', 'vitest': 'vitest',
                  'xunit': 'dotnet', 'sql': 'sql', 'shell': 'shell'}

# --- what this release writes instead --------------------------------------
IGNORE_LINES = ('.purlin/runtime/', '.purlin/report-data.js')
# Each file the update changes is kept here as it was, at its own path. The
# folder is under `.purlin/runtime/`, which git ignores.
BACKUP_DIR = '.purlin/runtime/update-backup'
BACKUPS_KEPT = ('Every file the update rewrote is kept as it was under %s/, '
                'with each change listed in update.log there.%s Delete the '
                'folder once the tests pass.')
DELETED_IN_GIT = ' A file it deleted is in git, at %s.'
EVIDENCE_DIR = '.purlin/evidence'
EVIDENCE_README = EVIDENCE_DIR + '/README.md'
DASHBOARD_PAGE = 'purlin-report.html'
SHIPPED_PAGE = 'scripts/report/purlin-report.html'
META_RE = re.compile(r'^>\s*[A-Z][A-Za-z-]+:')
SCOPE_RE = re.compile(r'^>\s*Scope:', re.M)
WORKFLOW_DIR = '.github/workflows'
DROPPED_FRAMEWORK = 'dropped %s from the tests: nothing in the tree runs it'
TEST_EXTENSIONS = ('.py', '.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx', '.cs',
                   '.sh', '.bash', '.sql')
SKIP_DIRS = ('node_modules', 'bin', 'obj')
_COMMIT = 'chore(update): migrate to %s (%s)'
# The two settings this release reads; the config step removes every other.
SETTINGS = ('version', 'tests')
REMOVED_KEYS = 'removed from .purlin/config.json: %s'
EVIDENCE_TEMPLATE = 'templates/evidence-readme.md'

# The lines 0.9.5 wrote into `.gitignore` for files this release does not
# write, which go, and the comment it wrote above the dashboard page's line.
STALE_IGNORE = ('.purlin/cache/', '.purlin/plugins/__pycache__/',
                '# Purlin cache (audit results, additional criteria)',
                '# Purlin plugin cache')
REWORDED_IGNORE = {
    '# Dashboard HTML (symlinked from framework)':
        '# Dashboard page, rewritten with its data, never committed'}
# What the update prints after its totals.
OWNER_HEADING = 'These need you:'
KIND_TAGS_WENT = ('dropped %d kind-of-test tag%s from %d spec%s: purlin:test '
                  'runs every marked test')
ARROW = '\u2192'
RUN_UPDATE = ARROW + ' Run: purlin:init --update'
HOW_TO_APPLY = ('Nothing was applied. Add --yes to apply every migration and '
                'use each proposed test command, or --apply <id>[,<id>...] '
                'to apply the migrations named.')
STILL_PENDING = ('%d migration%s still pending: %s. A test run stops until '
                 'nothing is pending.')
RUN_TESTS = ARROW + ' Run: purlin:test --all --commit'
RUN_TESTS_FIRST = ('Run it before anything else: every rule reads not run '
                   'until it has.')
FAILS_IN_FULL_RUN = ('A test that fails in that run and passes when its '
                     "feature is run alone is the project's own: purlin:test "
                     '<feature>.')
LEFT_HEADING = 'Purlin left these for you:'
LEFT_NEEDLES = ('[proof:', 'pytest.mark.proof', '.purlin/plugins',
                'purlin:verify', 'proofs-')
LEFT_SHOWN = 20
# The files that instruct an agent, which stand first: an agent that reads
# one goes on writing what this release does not read.
AGENT_FILES = ('CLAUDE.md', 'AGENTS.md')
AGENT_DIR = '.claude/'
CHANGE_FIRST = ('. Change it first: it tells the agent to write what this '
                'release does not read.')
LEFT_MORE = '  and %d more file%s'
LEFT_WHY = ('  Each line counted names something 0.9.5 used: %s. This release '
            'reads none of them.')
NOT_RUN = 'Every rule reads `not run` until the tests run again.'
OLD_RECORD = ("The `verify:` commits 0.9.5 made stay in git as the earlier "
              "record, and its receipts can be read from the commit before "
              "the upgrade, %s.")
UPDATE_LOG = BACKUP_DIR + '/update.log'
APPLYING = 'Applying %d migration%s: %s.'
UNKNOWN_MIGRATION = ('%s is not a migration. The migrations are: %s.')
BAD_TEST_COMMAND = ('--test-command takes <tool>=<command>, as in '
                    '--test-command "pytest=uv run pytest {files} '
                    '--junitxml={report}"; it was given %s.')

# --- helpers ---------------------------------------------------------------
# Both open with `newline=''`: a file the project owns keeps each line's own
# ending, byte for byte, through a rewrite.
def _read(path):
    with open(path, 'r', encoding='utf-8', newline='') as handle:
        return handle.read()

def _write(path, text):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)

def _git(root, *args):
    try:
        done = subprocess.run(['git'] + list(args), cwd=root,
                              capture_output=True, text=True)
    except (OSError, ValueError) as exc:
        return False, str(exc)
    return done.returncode == 0, (done.stdout + done.stderr).strip()

def _untrack(root, rel):
    _git(root, 'rm', '-r', '-q', '--cached', '--ignore-unmatch', '--', rel)

def _back_up_copy(root, rel):
    """Keep `rel` as it is now under the backup folder, at its own path, and
    say where. A file an earlier migration of the run already kept is not
    kept again: its backup holds the bytes from before the run."""
    kept = '%s/%s' % (BACKUP_DIR, rel)
    target = os.path.join(root, *kept.split('/'))
    if os.path.lexists(target):
        return None
    try:
        with open(os.path.join(root, *rel.split('/')), 'rb') as handle:
            previous = handle.read()
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'wb') as handle:
            handle.write(previous)
    except (IOError, OSError):
        return None
    return kept

def _files_under(root, subdir, patterns):
    hits = []
    for dirpath, _dirs, names in os.walk(os.path.join(root, subdir)):
        for name in names:
            if any(fnmatch.fnmatch(name, p) for p in patterns):
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                hits.append(rel.replace(os.sep, '/'))
    return sorted(hits)

def _config(root):
    """The settings as a dict, `{}` with no file; one that cannot be read raises.

    The run stops on `config_problem` before it reads them, and `pending()`
    lists no config step for a file it cannot read.
    """
    path = os.path.join(root, '.purlin', 'config.json')
    if not os.path.lexists(path):
        return {}
    config = json.loads(_read(path))
    if not isinstance(config, dict):
        raise ValueError('.purlin/config.json holds no object')
    return config

def _version():
    try:
        return _read(os.path.join(PLUGIN_ROOT, 'VERSION')).strip()
    except (IOError, OSError):
        return '0'

def _plugin_module(subdir, name):
    """One of the plugin's own modules, imported by path the way CI does."""
    folder = os.path.join(PLUGIN_ROOT, 'scripts', subdir)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return __import__(name)

def _frameworks():
    return _plugin_module('mcp', 'purlin.frameworks').frameworks

def _piped():
    """True where the answers are not typed at a terminal, so nothing shows
    them and no line ends after them."""
    try:
        return not sys.stdin.isatty()
    except (AttributeError, ValueError):
        return True

def _confirm(question, assume_yes):
    """A yes or a no to `question`, on a line of its own. Where the answer
    is not typed at a terminal the answer taken is printed after it."""
    if assume_yes:
        return True
    try:
        answer = input('%s [y/N] ' % question)
    except (EOFError, KeyboardInterrupt):
        answer = ''
    yes = answer.strip().lower() in ('y', 'yes')
    if _piped():
        print('y' if yes else 'n')
    return yes

def _answer(question, default):
    """What is typed after `question`, `default` for an empty answer, `y`,
    `yes` or the end of input; printed after it where no terminal shows it."""
    try:
        typed = input(question).strip()
    except (EOFError, KeyboardInterrupt):
        typed = ''
    taken = default if typed.lower() in ('', 'y', 'yes') else typed
    if _piped():
        print(taken)
    return taken

def _s(items):
    return '' if len(items) == 1 else 's'

# --- the migrations ---------------------------------------------------------
def _design_lines(text):
    """`(the text without its design reference, the fields it removed)`.

    Released 0.9.5 let a spec point at a Figma file and carry a picture's
    fingerprint. A pinned timestamp belongs to a Figma source and goes with
    it, and a `>` line continuing a removed field goes with that field.
    """
    lines = text.splitlines(True)
    figma = any(FIGMA_SOURCE_RE.match(line) for line in lines)
    kept, removed, dropping = [], [], False
    for line in lines:
        field = META_RE.match(line)
        if field:
            dropping = bool(DESIGN_FIELD_RE.match(line)
                            or FIGMA_SOURCE_RE.match(line)
                            or (figma and PINNED_RE.match(line)))
            if dropping:
                removed.append(line.split(':', 1)[0].lstrip('> \t') + ':')
                continue
        elif dropping and line.startswith('>'):
            continue
        else:
            dropping = False
        kept.append(line)
    return ''.join(kept), removed

def _detect_design_refs(root):
    return [rel for rel in _files_under(root, 'specs', ('*.md',))
            if _design_lines(_read(os.path.join(root, rel)))[1]]

def _apply_design_refs(root, files, args, out):
    """No design file is tied to a spec in this release: the lines go."""
    for rel in files:
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(root, rel))
        text, removed = _design_lines(_read(path))
        _write(path, text)
        out.done(rel)
        out.note('removed the design reference from %s: %s'
                 % (rel, ', '.join('> ' + name for name in removed)))
    out.say('removed the design reference from %d spec%s'
            % (len(files), _s(files)))

def _is_anchor(rel, text):
    return (rel.startswith('specs/_anchors/')
            or text.lstrip().startswith('# Anchor:'))

def _anchor_lines(rel, text):
    """`(the text without the lines naming anchors, the fields it removed)`.

    Released 0.9.5 let a spec name the anchors it required and an anchor say
    it was global or name the files it covered. Every anchor covers the whole
    project now, so `> Requires:` and `> Global:` go from every spec and
    `> Scope:` from every anchor, each with the `>` lines continuing it. Only
    the lines above the first section heading are read.
    """
    anchor = _is_anchor(rel, text)
    kept, removed, dropping, body = [], set(), False, False
    for line in text.splitlines(True):
        if line.startswith('## '):
            body = True
        field = None if body else META_RE.match(line)
        if field:
            name = ANCHOR_FIELD_RE.match(line)
            name = name.group(1) if name else None
            dropping = bool(name) and (name != 'Scope' or anchor)
            if dropping:
                removed.add(name)
                continue
        elif dropping and line.startswith('>'):
            continue
        else:
            dropping = False
        kept.append(line)
    return ''.join(kept), [n for n in ANCHOR_FIELDS if n in removed]

def _joined(items):
    """`a`, `a and b`, `a, b and c`."""
    return (items[0] if len(items) == 1
            else ', '.join(items[:-1]) + ' and ' + items[-1])

def _named_anchors(root):
    """`{anchor: [names of the specs whose > Requires: named it]}`, sorted.

    An anchor that carried `> Global: true` is left out: its rules already
    covered every spec.
    """
    specs = {}
    for rel in _files_under(root, 'specs', ('*.md',)):
        specs[rel] = _read(os.path.join(root, rel))
    anchors = {}
    for rel, text in specs.items():
        if _is_anchor(rel, text) and not GLOBAL_TRUE_RE.search(text):
            anchors[os.path.basename(rel)[:-len('.md')]] = []
    for rel, text in sorted(specs.items()):
        name = os.path.basename(rel)[:-len('.md')]
        found = REQUIRES_RE.search(text)
        if not found:
            continue
        for wanted in re.split(r'[,\s]+', found.group(1)):
            if wanted in anchors and wanted != name \
                    and name not in anchors[wanted]:
                anchors[wanted].append(name)
    return dict((a, sorted(n)) for a, n in anchors.items() if n)

def _detect_anchor_lines(root):
    return [rel for rel in _files_under(root, 'specs', ('*.md',))
            if _anchor_lines(rel, _read(os.path.join(root, rel)))[1]]

def _apply_anchor_lines(root, files, args, out):
    """No spec names an anchor, and no anchor names files: the lines go."""
    named = _named_anchors(root)
    for rel in files:
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(root, rel))
        text, removed = _anchor_lines(rel, _read(path))
        _write(path, text)
        out.done(rel)
        out.note('removed from %s: %s'
                 % (rel, _joined(['> %s:' % name for name in removed])))
    out.say('removed the lines naming anchors from %d spec%s'
            % (len(files), _s(files)))
    for anchor in sorted(named):
        specs = named[anchor]
        out.owner((NAMED_ONE if len(specs) == 1 else NAMED_MANY)
                  % (anchor, len(specs), ', '.join(specs), anchor))

def _detect_untracked(root):
    hits = _files_under(root, 'specs', (PROOF_FILE_GLOB, RUN_FILE_GLOB))
    ok, tracked = _git(root, 'ls-files')
    listed = tracked.splitlines() if ok else []
    hits += [rel for rel in listed if rel == DASHBOARD_DATA]
    # The cache 0.9.5 kept is gone outright, tracked or ignored.
    if (os.path.isdir(os.path.join(root, *CACHE_DIR.split('/')))
            or any(rel.startswith(CACHE_DIR + '/') for rel in listed)):
        hits.append(CACHE_DIR + '/')
    path = os.path.join(root, '.gitignore')
    lines = _read(path).splitlines() if os.path.isfile(path) else []
    if (any(line not in lines for line in IGNORE_LINES)
            or any(line in STALE_IGNORE or line in REWORDED_IGNORE
                   for line in lines)):
        hits.append('.gitignore')
    return sorted(set(hits))


def _fresh_ignore(text):
    """A `.gitignore` without the lines 0.9.5 wrote for files this release
    does not write, a blank line they leave doubled written once."""
    kept = []
    for line in text.splitlines(True):
        bare = line.rstrip('\r\n')
        if bare in STALE_IGNORE:
            continue
        if bare in REWORDED_IGNORE:
            line = REWORDED_IGNORE[bare] + line[len(bare):]
        if not bare.strip() and kept and not kept[-1].strip():
            continue
        kept.append(line)
    return ''.join(kept)

def _apply_untracked(root, files, args, out):
    gone, cache = 0, False
    for rel in files:
        if rel == '.gitignore':
            continue
        _untrack(root, rel)
        out.done(rel)
        if rel.startswith('specs/'):
            os.remove(os.path.join(root, rel))
            gone += 1
        elif rel == CACHE_DIR + '/':
            shutil.rmtree(os.path.join(root, *CACHE_DIR.split('/')),
                          ignore_errors=True)
            cache = True
    if '.gitignore' in files:
        path = os.path.join(root, '.gitignore')
        text = _read(path) if os.path.isfile(path) else ''
        out.kept(_back_up_copy(root, '.gitignore'))
        text = _fresh_ignore(text)
        missing = [l for l in IGNORE_LINES if l not in text.splitlines()]
        if missing:
            if text and not text.endswith('\n'):
                text += '\n'
            text += ('\n# Regenerated locally, never committed\n'
                     + ''.join(line + '\n' for line in missing))
        _write(path, text)
        out.done('.gitignore')
    out.say('deleted %d file%s beside the specs%s, and untracked the '
            'dashboard data; a run writes no file beside a spec, and evidence '
            'lives in %s' % (gone, '' if gone == 1 else 's',
                             ' and the folder %s/' % CACHE_DIR if cache
                             else '', EVIDENCE_DIR))

def _detect_hooks(root):
    """Every git hook v0.9.5 installed. This release installs none."""
    hits = []
    for rel in ('.git/hooks/pre-commit', PRE_PUSH_HOOK):
        path = os.path.join(root, *rel.split('/'))
        if os.path.isfile(path) and 'purlin' in _read(path).lower():
            hits.append(rel)
    return hits

def _apply_hooks(root, files, args, out):
    """Remove them. Nothing runs at commit time and nothing runs at push time.

    A push is a person's act, so a hook in front of it was a convenience that
    had to be explained and could be skipped.
    """
    for rel in files:
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(root, rel))
        _untrack(root, rel)
        try:
            os.remove(path)
        except OSError:
            continue
        out.done(rel)
    out.say('removed %d git hook%s; this release runs nothing at commit or '
            'push time' % (len(files), _s(files)))

def _detect_config(root):
    """The settings file, while it holds anything but this release's two."""
    config = _config(root)
    if not config:
        return []
    stale = (sorted(config) != sorted(SETTINGS)
             or not isinstance(config.get('tests'), list)
             or config.get('version') != _version())
    return ['.purlin/config.json'] if stale else []

# How a project starts each test tool where it differs from the command
# setup suggests: the words in front of the tool's name. A launcher listed
# here is the suggested one in another spelling, and the suggestion stays.
_TOOL_RES = {
    'pytest': re.compile(r'(?<![\w./-])(?:pytest|py\.test)(?![\w.-])'),
    'vitest': re.compile(r'(?<![\w./-])vitest(?![\w.-])'),
    'jest': re.compile(r'(?<![\w./-])jest(?![\w.-])'),
}
_SUGGESTED_RES = {
    'pytest': re.compile(r'(?:python3 -m |py -3 -m )pytest'),
    'vitest': re.compile(r'npx vitest'),
    'jest': re.compile(r'npx jest'),
}
_PLAIN_LAUNCHERS = {
    'pytest': ('pytest', 'py.test', 'python -m pytest', 'python3 -m pytest',
               'py -3 -m pytest'),
    'vitest': ('vitest', 'npx vitest'),
    'jest': ('jest', 'npx jest'),
}
_INSTALLS_RE = re.compile(r'\b(?:install|add|uninstall|remove)\b')
# The options by which a command of the project's own runs only some of a
# tool's tests: True for one that takes a value. The command proposed
# carries none of them, since a run hands the tool the files to run.
_NARROWING = {
    'pytest': {'-k': True, '-m': True, '--deselect': True, '--ignore': True,
               '--ignore-glob': True, '--lf': False, '--last-failed': False},
    'vitest': {'--project': True, '-t': True, '--testNamePattern': True,
               '--dir': True, '--exclude': True, '--shard': True,
               '--changed': False},
    'jest': {'-t': True, '--testNamePattern': True,
             '--testPathPattern': True, '--testPathPatterns': True,
             '--testPathIgnorePatterns': True, '--selectProjects': True,
             '--shard': True, '-o': False, '--onlyChanged': False,
             '--changedSince': True},
}
PROPOSED = '%s: %s'
RUNS_IT_AS = '  %s runs it as: %s'
LEAVES_OUT = '  The proposal leaves out %s, so every %s test runs.'
COMMAND_QUESTION = ('Use this command for %s? Press Enter to use it, or type '
                    'the command to use instead: ')


def _own_commands(root):
    """`[(where, command)]`: each command the project keeps for its own use,
    in its `package.json` scripts, its `Makefile` and its workflows."""
    found = []
    try:
        scripts = json.loads(_read(os.path.join(root, 'package.json'))).get(
            'scripts')
    except (IOError, OSError, ValueError, AttributeError):
        scripts = None
    if isinstance(scripts, dict):
        found += [('package.json, "%s",' % name, command)
                  for name, command in scripts.items()
                  if isinstance(command, str)]
    try:
        found += [('Makefile', line.strip())
                  for line in _read(os.path.join(root, 'Makefile')).splitlines()
                  if line.startswith('\t')]
    except (IOError, OSError, UnicodeDecodeError):
        pass
    for rel in _files_under(root, WORKFLOW_DIR, ('*.yml', '*.yaml')):
        try:
            lines = _read(os.path.join(root, rel)).splitlines()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        found += [(rel, command) for command in _workflow_commands(lines)]
    return found


_RUN_KEY_RE = re.compile(r'^(\s*)(?:-\s*)?run:\s*(.*)$')


def _workflow_commands(lines):
    """The commands a workflow's `run:` keys hold, a block's lines each one."""
    commands, block = [], None
    for line in lines:
        key = _RUN_KEY_RE.match(line)
        if key:
            block = None
            if key.group(2).strip() in ('|', '>', '|-', '>-', '|+', '>+'):
                block = len(key.group(1))
            elif key.group(2).strip():
                commands.append(key.group(2).strip())
        elif block is not None:
            indent = len(line) - len(line.lstrip())
            if line.strip() and indent <= block:
                block = None
            elif line.strip():
                commands.append(line.strip())
    return commands


def _runs_tool(tool, command):
    """`(the launcher, what follows the tool's name)` for the part of
    `command` that runs `tool`, or None where no part does."""
    pattern = _TOOL_RES.get(tool)
    if pattern is None:
        return None
    for part in re.split(r'&&|\|\||[;|]', command):
        found = pattern.search(part)
        # A command that installs the tool does not run it.
        if found and not _INSTALLS_RE.search(part[:found.start()]):
            return part[:found.end()].strip(), part[found.end():]
    return None


def narrowing(tool, command):
    """Each option of `command` that runs only some of `tool`'s tests, with
    its value: `['--project unit']`."""
    runs = _runs_tool(tool, command)
    known = _NARROWING.get(tool, {})
    if runs is None:
        return []
    try:
        words = shlex.split(runs[1])
    except ValueError:
        words = runs[1].split()
    found, index = [], 0
    while index < len(words):
        word = words[index]
        name = word.split('=', 1)[0]
        index += 1
        if name not in known:
            continue
        if known[name] and '=' not in word and index < len(words):
            word += ' ' + shlex.quote(words[index])
            index += 1
        found.append(word)
    return found


def project_runs(root, tool):
    """`(where, the command, its launcher)` for the command of the project's
    own that runs `tool` and is closest to the one proposed: the one with the
    fewest options that run only some of the tool's tests, the first of
    those. None where no command runs it. The launcher is what stands in
    front of the tool's name, the name included: `uv run --project pipeline
    pytest` in `uv run --project pipeline pytest pipeline/tests`."""
    best = None
    for where, command in _own_commands(root):
        runs = _runs_tool(tool, command)
        if runs is None:
            continue
        narrowed = len(narrowing(tool, command))
        if best is None or narrowed < best[0]:
            best = (narrowed, where, command.strip(), runs[0])
    return best[1:] if best else None


def proposed_tests(root, old):
    """`(entries, sources, dropped)`: the `tests` setting the update proposes.

    Each framework `test_framework` named becomes the suite setup suggests
    for it, xunit read as dotnet. v0.9.5 wrote down every plugin it shipped,
    so a Python-only tree can carry `pytest,jest,shell,vitest`: a name that
    neither detection nor a command of the project's own finds is dropped
    rather than written, because its suite would fail on every run. `auto`,
    or no value, writes what detection finds. Where the project starts a
    tool its own way, the entry's command starts that way too, and
    `sources` holds `{name: (where, the project's command)}` for it. A
    config that already carries `tests` keeps it.
    """
    frameworks = _frameworks()
    if isinstance(old.get('tests'), list):
        return old['tests'], {}, []
    detected = frameworks.detect_frameworks(root)
    raw = str(old.get('test_framework') or '')
    names = [part.strip() for part in raw.split(',') if part.strip()]
    wanted, dropped = [], []
    if not names or 'auto' in names:
        wanted = list(detected)
    for name in ([] if wanted else names):
        suite = OLD_FRAMEWORKS.get(name)
        if suite is None or (suite not in detected
                             and project_runs(root, suite) is None):
            dropped.append(name)
        elif suite not in wanted:
            wanted.append(suite)
    entries, sources = frameworks.entries_for(wanted), {}
    for entry in entries:
        runs = project_runs(root, entry['name'])
        if runs is None:
            continue
        where, command, launcher = runs
        sources[entry['name']] = (where, command)
        if launcher not in _PLAIN_LAUNCHERS[entry['name']]:
            entry['run'] = _SUGGESTED_RES[entry['name']].sub(
                lambda _found: launcher, entry['run'], count=1)
    return entries, sources, dropped


def _proposal_lines(entries, sources):
    lines = []
    for entry in entries:
        lines.append(PROPOSED % (entry['name'], entry['run']))
        if entry['name'] in sources:
            lines.append(RUNS_IT_AS % sources[entry['name']])
            left_out = [option for option in narrowing(
                entry['name'], sources[entry['name']][1])
                if option not in entry['run']]
            if left_out:
                lines.append(LEAVES_OUT % (_joined(left_out), entry['name']))
    return lines


def _apply_config(root, files, args, out):
    """`version` and `tests`, and every other key removed and named.

    The command proposed for each test tool is shown, and the owner accepts
    it or types the one to use; `--yes` accepts each.
    """
    old = _config(root)
    path = os.path.join(root, '.purlin', 'config.json')
    out.kept(_back_up_copy(root, '.purlin/config.json'))
    tests, sources, unwired = proposed_tests(root, old)
    given = dict(getattr(args, 'commands', None) or {})
    for entry in ([] if isinstance(old.get('tests'), list) else tests):
        if entry['name'] in given:
            entry['run'] = given[entry['name']]
        elif args.ask:
            for line in _proposal_lines([entry], sources):
                print(line)
            entry['run'] = _answer(COMMAND_QUESTION % entry['name'],
                                   entry['run'])
    config = {'version': _version(), 'tests': tests}
    _write(path, json.dumps(config, indent=2) + '\n')
    out.done('.purlin/config.json')
    names = [entry.get('name') for entry in tests if isinstance(entry, dict)]
    out.say('wrote the tests setting: %s' % (', '.join(names) or 'no suite; '
            'add one under "tests" in .purlin/config.json'))
    for entry in tests:
        if isinstance(entry, dict) and entry.get('name'):
            out.say(PROPOSED % (entry['name'], entry.get('run')))
    for name in unwired:
        out.say(DROPPED_FRAMEWORK % name)
    removed = [key for key in old if key not in SETTINGS]
    if removed:
        out.say(REMOVED_KEYS % ', '.join(removed))

def retag(text, change):
    """`(text, changed)`: `text` with `change` applied to each tag that ends
    a proof, its continuation lines read with it.

    `change(name, argument)` returns the tag to write in its place, None to
    drop it, or False to leave it. A line a dropped tag leaves empty goes.
    """
    lines = text.splitlines(True)
    out, changed, index = [], 0, 0
    while index < len(lines):
        if not PROOF_START_RE.match(lines[index]):
            out.append(lines[index])
            index += 1
            continue
        end = index + 1
        while end < len(lines) and not PROOF_END_RE.match(lines[end]):
            end += 1
        block = ''.join(lines[index:end])
        body = block.rstrip('\r\n')
        eol = block[len(body):]
        index = end
        tail = TAGS_AT_END_RE.search(body)
        if not tail:
            out.append(block)
            continue
        kept, carry, here = [], None, 0
        for space, name, argument in TAG_RE.findall(tail.group(1)):
            new = change(name, argument)
            if new is False:
                new = '@' + name + argument
            else:
                here += 1
            if new is None:
                # A tag that opened its line hands its indent to the next
                # tag on that line, and takes the line with it if alone.
                if '\n' in space and carry is None:
                    carry = space
                continue
            if '\n' in space or carry is None:
                kept.append(space + new)
            else:
                kept.append(carry + new)
            carry = None
        if not here:
            out.append(block)
            continue
        changed += here
        out.append(body[:tail.start()] + ''.join(kept)
                   + (tail.group(2) or '') + eol)
    return ''.join(out), changed

def _end_tags(text):
    """The name of every tag that ends a proof of the spec `text`."""
    names = []
    retag(text, lambda name, argument: names.append(name) or False)
    return names

def _to_env(name, argument):
    return '@env(windows)' if name == WINDOWS_TAG and not argument else False

def _detect_os_tags(root):
    return [rel for rel in _files_under(root, 'specs', ('*.md',))
            if WINDOWS_TAG in _end_tags(_read(os.path.join(root, rel)))]

def _apply_os_tags(root, files, args, out):
    """A proof names an operating system now, or names none and runs anywhere."""
    for rel in files:
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(root, rel))
        _write(path, retag(_read(path), _to_env)[0])
        out.done(rel)
    out.say('rewrote the operating-system tags in %d spec%s'
            % (len(files), _s(files)))

def marker_kinds(root):
    """Each kind of test the project's own 0.9.5 markers name in their last
    field, read from its test files and from the copies of them an earlier
    run of the update kept."""
    kinds = set()
    paths = [os.path.join(root, rel) for rel in _test_files(root)]
    for dirpath, _dirnames, names in os.walk(
            os.path.join(root, *BACKUP_DIR.split('/'))):
        paths += [os.path.join(dirpath, name) for name in sorted(names)
                  if name.endswith(TEST_EXTENSIONS)]
    for path in paths:
        try:
            text = _read(path)
        except (IOError, OSError, UnicodeDecodeError):
            continue
        for pattern in MARKER_KIND_RES:
            for match in pattern.finditer(text):
                kinds.add(match.group(pattern.groups))
    return kinds

def _kinds(root, texts):
    """The tags the upgrade drops: the three kinds 0.9.5 named, and each
    kind the project's own markers name. The test files are read only where
    a proof ends with a tag that is neither one of the three nor kept."""
    kinds = set(KINDS)
    if any(name not in kinds and name not in KEPT_TAGS + (WINDOWS_TAG,)
           for text in texts for name in _end_tags(text)):
        kinds |= marker_kinds(root)
    return kinds - set(KEPT_TAGS) - set((WINDOWS_TAG,))

def _detect_kind_tags(root):
    """Every spec with a proof that still names what kind of test it is."""
    texts = dict((rel, _read(os.path.join(root, rel)))
                 for rel in _files_under(root, 'specs', ('*.md',)))
    kinds = _kinds(root, texts.values())
    return [rel for rel in sorted(texts)
            if any(name in kinds for name in _end_tags(texts[rel]))]

def _apply_kind_tags(root, files, args, out):
    """A proof ends with an operating system, `@slow` or `@manual`, and
    names no kind of test."""
    texts = dict((rel, _read(os.path.join(root, rel))) for rel in files)
    kinds = _kinds(root, texts.values())
    total = 0
    for rel in files:
        new, count = retag(
            texts[rel], lambda name, argument: None if name in kinds
            and not argument else False)
        out.kept(_back_up_copy(root, rel))
        _write(os.path.join(root, rel), new)
        out.done(rel)
        out.note('dropped %d tag%s from %s' % (count, '' if count == 1
                                               else 's', rel))
        total += count
    out.say(KIND_TAGS_WENT % (total, '' if total == 1 else 's', len(files),
                              _s(files)))

def _detect_workflows(root):
    """The workflow files whose text names a proof file.

    A v0.9.5 project ran its Windows proofs in a workflow that committed the
    proof file back beside the spec. This release writes no proof file. A
    project's own pipeline may name one too, so no workflow is removed
    without a yes for that file. Every other workflow or pipeline file is
    left as it is.
    """
    hits = []
    for rel in _files_under(root, WORKFLOW_DIR, ('*.yml', '*.yaml')):
        try:
            text = _read(os.path.join(root, rel))
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if WORKFLOW_MARKER in text:
            hits.append(rel)
    return hits

# What the run prints for each such workflow, the question it asks, and the
# line for one it did not remove.
WORKFLOW_NAMES = '%s:%d names a proof file: %s'
WORKFLOW_QUESTION = 'Remove %s?'
WORKFLOW_KEPT = ('%s: kept. It names a proof file and may be the old Purlin '
                 'workflow; remove it by hand if it is.')

def _apply_workflows(root, files, args, out):
    """Each workflow is shown with the line that names a proof file and
    asked about on its own; one answered yes is backed up, untracked and
    removed. `--yes` is a yes to no one file, so under it each is kept and
    named."""
    removed = []
    for rel in files:
        lines = _read(os.path.join(root, rel)).splitlines()
        number = next(index for index, line in enumerate(lines, 1)
                      if WORKFLOW_MARKER in line)
        print(WORKFLOW_NAMES % (rel, number, lines[number - 1].strip()))
        if not args.ask or not _confirm(WORKFLOW_QUESTION % rel, False):
            out.owner(WORKFLOW_KEPT % rel)
            continue
        out.kept(_back_up_copy(root, rel))
        _untrack(root, rel)
        os.remove(os.path.join(root, rel))
        out.done(rel)
        removed.append(rel)
    if removed:
        out.say('removed %d workflow%s that committed proof files'
                % (len(removed), _s(removed)))


def _detect_evidence(root):
    """A project with no README in its evidence folder: 0.9.5 had no folder."""
    return ([] if os.path.isfile(os.path.join(root, EVIDENCE_README))
            else [EVIDENCE_README])

def _apply_evidence(root, files, args, out):
    """The folder every run writes into, and one README saying what it holds."""
    _write(os.path.join(root, EVIDENCE_README),
           _read(os.path.join(PLUGIN_ROOT, *EVIDENCE_TEMPLATE.split('/'))))
    out.done(EVIDENCE_README)
    out.say('wrote %s: each feature\'s evidence lands beside it, under '
            'local/ and ci/' % EVIDENCE_README)


def _shipped_page():
    with open(os.path.join(PLUGIN_ROOT, *SHIPPED_PAGE.split('/')),
              'rb') as handle:
        return handle.read()

def _detect_dashboard(root):
    """The page at the root when it is a link or not the page this release ships.

    v0.9.5 linked the page into the plugin's own folder, so an upgraded plugin
    leaves the link pointing at the old one. A project with no page is left
    without one.
    """
    path = os.path.join(root, DASHBOARD_PAGE)
    if not os.path.lexists(path):
        return []
    if os.path.islink(path):
        return [DASHBOARD_PAGE]
    try:
        with open(path, 'rb') as handle:
            current = handle.read()
    except (IOError, OSError):
        return [DASHBOARD_PAGE]
    return [] if current == _shipped_page() else [DASHBOARD_PAGE]

def _apply_dashboard(root, files, args, out):
    """The page init copies, in place of the link or the older copy."""
    path = os.path.join(root, DASHBOARD_PAGE)
    tracked = _git(root, 'ls-files', '--error-unmatch', '--',
                   DASHBOARD_PAGE)[0]
    if os.path.lexists(path):
        os.remove(path)
    with open(path, 'wb') as handle:
        handle.write(_shipped_page())
    if tracked:
        out.done(DASHBOARD_PAGE)
    out.say('replaced %s with the page this release ships' % DASHBOARD_PAGE)


# --- the proofs numbered with a letter ---------------------------------------

def _spec_name(rel):
    return os.path.basename(rel)[:-len('.md')]


def _renumbered(text):
    """`(the spec's text with each lettered proof numbered, [(old, new)])`.

    Each takes the next free number of the spec, in the order the lines
    stand: one above every proof number the spec holds and above
    `> Highest-Proof:`, which moves with it where the spec has the line.
    Only the lines under `## Proof` are read.
    """
    lines = text.splitlines(True)
    inside, lettered, top, highest = False, [], 0, None
    for index, line in enumerate(lines):
        if line.startswith('## '):
            inside = line.strip() == '## Proof'
            continue
        found = HIGHEST_PROOF_RE.match(line)
        if found and highest is None:
            highest = index
            top = max(top, int(found.group(2)))
        if not inside:
            continue
        number = PROOF_NUMBER_RE.match(line)
        if number:
            top = max(top, int(number.group(1)))
        if LETTERED_LINE_RE.match(line):
            lettered.append(index)
    moved = []
    for index in lettered:
        top += 1
        found = LETTERED_LINE_RE.match(lines[index])
        moved.append((found.group(2), 'PROOF-%d' % top))
        lines[index] = (found.group(1) + 'PROOF-%d' % top
                        + lines[index][found.end():])
    if moved and highest is not None:
        lines[highest] = HIGHEST_PROOF_RE.sub(
            lambda m: m.group(1) + str(top), lines[highest], count=1)
    return ''.join(lines), moved


def _lettered_specs(root):
    """`{spec path: [(old id, new id)]}` for each spec with a lettered proof."""
    found = {}
    for rel in _files_under(root, 'specs', ('*.md',)):
        moved = _renumbered(_read(os.path.join(root, rel)))[1]
        if moved:
            found[rel] = moved
    return found


def _detect_lettered(root):
    return sorted(_lettered_specs(root))


def _renumber_marks(text, ext, moved):
    """`(text, how many)`: each marker naming a `(feature, lettered id)` of
    `moved` names its new number. A `[proof:...]` tag in a Python file is a
    docstring's, not a marker, and is left."""
    count = [0]

    def swap(found):
        new = moved.get((found.group(2), found.group(3)))
        if new is None:
            return found.group(0)
        count[0] += 1
        return found.group(1) + new

    patterns = LETTERED_MARK_RES + (
        (LETTERED_PYTEST_RE,) if ext == '.py' else (LETTERED_TAG_RE,))
    for pattern in patterns:
        text = pattern.sub(swap, text)
    return text, count[0]


def _apply_lettered(root, files, args, out):
    """Each lettered proof takes a number of its own, in its spec and in the
    marker of each test that named it, before the markers are rewritten."""
    moved, changes = {}, []
    for rel in files:
        path = os.path.join(root, rel)
        new, pairs = _renumbered(_read(path))
        if not pairs:
            continue
        out.kept(_back_up_copy(root, rel))
        _write(path, new)
        out.done(rel)
        for old, number in pairs:
            moved[(_spec_name(rel), old)] = number
            changes.append(RENUMBERED % (_spec_name(rel), old, number))
    marks, marked = 0, 0
    for rel in _test_files(root):
        path = os.path.join(root, rel)
        try:
            text = _read(path)
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if 'PROOF-' not in text:
            continue
        new, count = _renumber_marks(text, os.path.splitext(rel)[1].lower(),
                                     moved)
        if not count:
            continue
        out.kept(_back_up_copy(root, rel))
        _write(path, new)
        out.done(rel)
        marks += count
        marked += 1
    out.say('renumbered %d proof%s in %d spec%s and %d marker%s in %d file%s'
            % (len(changes), _s(changes), len(files), _s(files), marks,
               '' if marks == 1 else 's', marked, '' if marked == 1 else 's'))
    for line in changes:
        out.say(line)


# --- the markers and the plugins -------------------------------------------

def _test_files(root):
    """Every file under the project a 0.9.5 marker could sit in, sorted."""
    hits = []
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith('.') and d not in SKIP_DIRS)
        for name in sorted(names):
            if name.endswith(TEST_EXTENSIONS):
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                hits.append(rel.replace(os.sep, '/'))
    return hits


def _comment(ext, indent, feature, proof):
    opener = {'.py': '#', '.sh': '#', '.bash': '#', '.sql': '--'}.get(ext,
                                                                       '//')
    return '%s%s purlin: %s %s' % (indent, opener, feature, proof)


def _closing_line(lines, index, start):
    """The line the call opened at `lines[index][start]` closes on."""
    depth = 0
    for number in range(index, len(lines)):
        text = lines[number][start:] if number == index else lines[number]
        for char in text:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1
                if depth == 0:
                    return number
    return None


def _rewrite_python(lines, ext, written=None):
    """`written`, where given, takes the line number of each comment
    written, as the lines returned number them."""
    out, left, count = [], [], 0
    index = 0
    while index < len(lines):
        line = lines[index]
        found = PYTEST_MARK_RE.match(line)
        if found:
            end = _closing_line(lines, index, found.end() - 1)
            call = '\n'.join(lines[index:(end if end is not None
                                          else index) + 1])
            args = PYTEST_ARGS_RE.search(call)
            if end is not None and args:
                out.append(_comment(ext, found.group(1), args.group(1),
                                    args.group(2)))
                if written is not None:
                    written.append(len(out))
                count += 1
                index = end + 1
                continue
            lettered = LETTERED_PYTEST_RE.search(call)
            left.append((index + 1, lettered.group(2, 3) if lettered
                         else None))
        elif PYTESTMARK_RE.search(line):
            left.append((index + 1, None))
        out.append(line)
        index += 1
    return out, count, left


_CALL_START_RE = re.compile(
    r'(?<![\w$.])(?:it|test)((?:\s*\.\s*\w+)*)\s*\(')
# What may stand between a test's opening bracket and a piece of its title:
# other pieces, blanked here, the `+` joining them, and a name joined in.
_STRING = '\x00'
_TITLE_SO_FAR_RE = re.compile(r'^[\s+\w$.\x00]*$')


def _js_strings(text):
    """`(mask, spans)`: `text` with every comment and regex literal blanked
    and every character of a string literal written `_STRING`, newlines
    kept, and `(start, end)` of each string literal, read as the test run's
    reader reads them."""
    mask, spans = list(text), []
    index, size = 0, len(text)
    while index < size:
        after = markers_module.skip_noncode(text, index)
        if after is None:
            index += 1
            continue
        after = max(min(after, size), index + 1)
        string = text[index] in '"\'`'
        if string:
            spans.append((index, after))
        for position in range(index, after):
            if mask[position] != '\n':
                mask[position] = _STRING if string else ' '
        index = after
    return ''.join(mask), spans


def _closing(mask, index):
    """The offset after the `)` matching the `(` at `index`, else None."""
    depth = 0
    for position in range(index, len(mask)):
        if mask[position] == '(':
            depth += 1
        elif mask[position] == ')':
            depth -= 1
            if depth == 0:
                return position + 1
    return None


def _owning_call(mask, calls, position):
    """The offset at which the test whose title holds `position` opens, or
    None where the string there is not part of a test's title."""
    owner = None
    for call in calls:
        if call.end() > position:
            break
        owner = call
    if owner is None:
        return None
    opened = owner.end() - 1
    if '.each' in re.sub(r'\s', '', owner.group(1)):
        # `it.each(table)(title, fn)`: the title is in the second brackets.
        after = _closing(mask, opened)
        if after is None or after > position:
            return None
        rest = mask[after:position]
        if not rest.lstrip().startswith('('):
            return None
        opened = after + len(rest) - len(rest.lstrip())
    if not _TITLE_SO_FAR_RE.match(mask[opened + 1:position]):
        return None
    return owner.start()


def _line_at(text, offset):
    return text.count('\n', 0, offset) + 1


def _rewrite_js(text, eol):
    """Each title tag becomes one comment above the line that opens its test.

    A tag that was a string piece of its own goes with its `+`, and the space
    beside a tag goes with it, so `'a title ' + '[proof:...]'` is left as
    `'a title'`. A tag in a string that is no test's title is left and named.
    """
    mask, spans = _js_strings(text)
    calls = list(_CALL_START_RE.finditer(mask))
    starts = dict((start, end) for start, end in spans)
    ends = dict((end, start) for start, end in spans)
    edits, comments, left, count = [], {}, [], 0
    for start, end in spans:
        if '[proof:' not in text[start:end] or text[end - 1] != text[start]:
            continue
        inner = text[start + 1:end - 1]
        line = _line_at(text, start)
        lettered = [found.group(2, 3)
                    for found in LETTERED_TAG_RE.finditer(inner)]
        left.extend((line, pair) for pair in lettered)
        tags = list(TITLE_TAG_RE.finditer(inner))
        if not tags:
            continue
        owner = _owning_call(mask, calls, start)
        if owner is None:
            left.append((line, None))
            continue
        at = text.rfind('\n', 0, owner) + 1
        indent = re.match(r'[ \t]*', text[at:]).group(0)
        for tag in tags:
            comments.setdefault(at, []).append(
                _comment('.js', indent, tag.group(1), tag.group(2)))
            count += 1
        kept = TITLE_TAG_RE.sub('', inner)
        if TITLE_TAG_RE.match(inner):
            kept = kept.lstrip(' ')
        if kept.strip() or lettered:
            edits.append((start + 1, end - 1, kept))
            continue
        # The tag was the whole piece: it goes with the `+` that joined it.
        before = start - 1
        while before >= 0 and mask[before] in ' \t\r\n':
            before -= 1
        after = end
        while after < len(mask) and mask[after] in ' \t\r\n':
            after += 1
        if before >= 0 and mask[before] == '+':
            last = before - 1
            while last >= 0 and mask[last] in ' \t\r\n':
                last -= 1
            edits.append((last + 1, end, ''))
            if last + 1 in ends:
                piece = text[ends[last + 1] + 1:last]
                edits.append((last - (len(piece) - len(piece.rstrip(' '))),
                              last, ''))
        elif after < len(mask) and mask[after] == '+':
            first = after + 1
            while first < len(mask) and mask[first] in ' \t\r\n':
                first += 1
            edits.append((start, first, ''))
            if first in starts:
                piece = text[first + 1:starts[first] - 1]
                edits.append((first + 1, first + 1 + len(piece)
                              - len(piece.lstrip(' ')), ''))
        else:
            edits.append((start + 1, end - 1, kept))
    edits += [(at, at, ''.join(line + eol for line in lines))
              for at, lines in comments.items()]
    # From the end of the file back, so each offset still points at its place.
    out, floor = text, len(text) + 1
    for begin, stop, new in sorted(edits, reverse=True):
        if stop > floor:
            continue
        out = out[:begin] + new + out[stop:]
        floor = begin
    return out, count, left


def _rewrite_cs(lines, ext):
    out, count = [], 0
    for line in lines:
        found = list(TRAIT_RE.finditer(line))
        if not found:
            out.append(line)
            continue
        indent = re.match(r'[ \t]*', line).group(0)
        rest = line
        comments = []
        for match in found:
            comments.append(_comment(ext, indent, match.group(2),
                                     match.group(3)))
            count += 1
            opened, closed = match.group(1), match.group(4)
            # A trait alone in its brackets goes with them; one in a list of
            # attributes leaves the others where they are.
            keep = '[' if opened and not closed else ''
            keep += ']' if closed and not opened else ''
            rest = rest.replace(match.group(0), keep, 1)
        out.extend(comments)
        rest = re.sub(r'\[\s*,\s*', '[', rest)
        if rest.strip():
            out.append(rest)
    return out, count, []


def _rewrite_shell(lines, ext):
    body, found = [], []
    for line in lines:
        call = SHELL_CALL_RE.match(line)
        if call:
            if (call.group(2), call.group(3)) not in found:
                found.append((call.group(2), call.group(3)))
            body.append(call.group(1) + ':')
            continue
        harness = SHELL_HARNESS_RE.match(line) or SHELL_FINISH_RE.match(line)
        if harness:
            body.append(harness.group(1) + ':')
            continue
        body.append(line)
    if not found:
        return lines, 0, []
    head = 1 if body and body[0].startswith('#!') else 0
    comments = [_comment(ext, '', feature, proof) for feature, proof in found]
    return body[:head] + comments + body[head:], len(found), []


def _rewrite_sql(lines, ext):
    out, count = [], 0
    for line in lines:
        found = SQL_MARK_RE.match(line)
        if found:
            out.append(_comment(ext, '', found.group(1), found.group(2)))
            count += 1
        else:
            out.append(line)
    return out, count, []


_REWRITERS = {'.py': _rewrite_python, '.sh': _rewrite_shell,
              '.bash': _rewrite_shell, '.sql': _rewrite_sql, '.cs': _rewrite_cs}


def rewrite_markers(text, ext):
    """`(the text with every 0.9.5 marker a comment, how many, lines left)`.

    `lines left` holds `(line number, lettered)` for each marker the upgrade
    could not place above one test, which it names and leaves as it was:
    `lettered` is None for one such as a module-wide `pytestmark`, and
    `(feature, id)` for one naming a proof numbered with a letter.
    """
    return _rewritten(text, ext)[:3]


def _rewritten(text, ext):
    """What `rewrite_markers` returns, and the line number of each comment
    written into a Python file."""
    # A file whose every line ends `\r\n` keeps that ending, the comments
    # written into it included.
    eol = ('\r\n' if '\r\n' in text
           and text.count('\r\n') == text.count('\n') else '\n')
    rewrite = _REWRITERS.get(ext)
    if rewrite is None:
        return _rewrite_js(text, eol) + ([],)
    ending = eol if text.endswith(eol) else ''
    lines = text.split(eol)
    if ending:
        lines = lines[:-1]
    written = []
    if rewrite is _rewrite_python:
        out, count, left = rewrite(lines, ext, written)
    else:
        out, count, left = rewrite(lines, ext)
    return eol.join(out) + ending, count, left, written


def _docstring(node):
    """The statement that is the docstring of the function `node`, or None."""
    first = node.body[0]
    if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)):
        return first
    return None


def _without_docstrings(tree):
    """`tree` as text, every function's docstring left out."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and _docstring(node) is not None:
            node.body = node.body[1:] or [ast.Pass()]
    return ast.dump(tree)


def without_tag_lines(text, written):
    """`(text, how many lines went)`: the Python test file `text` without
    each docstring line that holds nothing but a 0.9.5 tag, in the tests
    whose marker comment is on one of the lines `written`.

    A docstring that was the tag alone goes whole, and stays where it is all
    the test holds. A tag that opened a docstring goes with the blank lines
    under it, and one that ended it with the blank lines above it. A tag
    inside a sentence stays. The file reads as the same code afterwards, or
    it is returned as it was.
    """
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return text, 0
    lines = text.splitlines(True)
    drop, edits, count = set(), {}, 0

    def bare(number):
        return lines[number - 1].rstrip('\r\n')

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        top = min([mark.lineno for mark in node.decorator_list]
                  + [node.lineno])
        while top > 1 and bare(top - 1).lstrip().startswith('#'):
            top -= 1
        doc = _docstring(node)
        if doc is None or not any(top <= number < node.lineno
                                  for number in written):
            continue
        first, last = doc.lineno, doc.end_lineno
        raw = lines[last - 1].encode('utf-8')
        if (lines[first - 1].encode('utf-8')[:doc.col_offset].strip()
                or raw[doc.end_col_offset:].strip()):
            continue
        if DOC_TAGS_RE.fullmatch(doc.value.value):
            if len(node.body) > 1 and node.body[1].lineno > last:
                tagged = [number for number in range(first, last + 1)
                          if '[proof:' in bare(number)]
                drop.update(range(first, last + 1))
                count += len(tagged)
            continue
        opener = DOC_OPENER_RE.match(bare(first))
        closer = DOC_CLOSER_RE.match(bare(last))
        if last == first or not opener or not closer:
            continue
        tags, body = set(), first + 1
        if opener.group(2).strip() and DOC_TAGS_RE.fullmatch(opener.group(2)):
            # The opening quotes move to the first line of text under it.
            while body < last and not bare(body).strip():
                body += 1
            drop.update(range(first, body))
            edits[body] = opener.group(1) + lines[body - 1].lstrip(' \t')
            count += 1
            if body == last:
                continue
            body += 1
        for number in range(body, last):
            if bare(number).strip() and DOC_TAGS_RE.fullmatch(bare(number)):
                tags.add(number)
        if closer.group(2).strip() and DOC_TAGS_RE.fullmatch(closer.group(2)):
            ending = lines[last - 1][len(bare(last)):]
            edits[last] = closer.group(1) + closer.group(3) + ending
            tags.add(last)
            count += 1
            closer = DOC_CLOSER_RE.match(edits[last].rstrip('\r\n'))
        count += len(tags - set((last,)))
        drop.update(tags - set((last,)))
        if not closer.group(2).strip():
            # A tag that ended the docstring takes the blank lines above it.
            run, number = [], last - 1
            while number > first and (number in tags
                                      or not bare(number).strip()):
                run.append(number)
                number -= 1
            if tags.intersection(run + [last]):
                drop.update(run)
    if not count:
        return text, 0
    new = ''.join(edits.get(number, line)
                  for number, line in enumerate(lines, 1)
                  if number not in drop)
    try:
        same = _without_docstrings(ast.parse(new)) == _without_docstrings(tree)
    except (SyntaxError, ValueError):
        same = False
    return (new, count) if same else (text, 0)


ONE_TEST_NOW = '; the file is one test now, and passes when it exits 0'
TITLE_UNREAD = ('%s:%d: the title of the test under this marker cannot be '
                'read, so its result cannot be matched. Write it as one plain '
                'string.')
_JS_EXTENSIONS = ('.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx', '.mts', '.cts')


def unread_titles(rel, text):
    """The lines of the markers in `text` whose test the test run's reader
    cannot read: a marker it ties to no test, and in a JavaScript or
    TypeScript file one it ties to another test than the one under it."""
    ext = os.path.splitext(rel)[1].lower()
    if ext in ('.sh', '.bash', '.sql'):
        return []
    read = markers_module.read_text(rel, text, 'junit')
    tied = dict((marker.line, test.line) for test in read.tests
                for marker in test.markers)
    lines = text.splitlines()
    problems = []
    for marker in read.markers:
        under = marker.line
        while (under < len(lines)
               and markers_module.parse_comment(lines[under]) is not None):
            under += 1
        if marker.line not in tied or (ext in _JS_EXTENSIONS
                                       and tied[marker.line] != under + 1):
            problems.append(marker.line)
    return problems


def _marked_old(root):
    """`{path: (new text, count, lines left)}` for each file with an old marker."""
    found = {}
    for rel in _test_files(root):
        try:
            text = _read(os.path.join(root, rel))
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if not any(token in text for token in ('pytest.mark.proof',
                                               '[proof:',
                                               'PurlinProof',
                                               'purlin_proof',
                                               '@purlin')):
            continue
        ext = os.path.splitext(rel)[1].lower()
        new, count, left = rewrite_markers(text, ext)
        if count or left:
            found[rel] = (new, count, left)
    return found


def _detect_markers(root):
    """The test files with a marker to rewrite and, where there is one, the
    files that instruct an agent with a line naming what 0.9.5 used: those
    lines go in the same migration, so they alone hold nothing pending."""
    tests = [rel for rel, (_new, count, _left) in _marked_old(root).items()
             if count]
    return (_agent_files(root) + tests) if tests else []


# --- the lines 0.9.5 wrote into the files that instruct an agent ------------
AGENT_LINES_WENT = 'removed %d line%s that named 0.9.5 from %s'
AGENT_TEXT = ('.md', '.markdown', '.mdc', '.txt')
AGENT_JSON = ('.json',)
_FENCE_RE = re.compile(r'^[ \t]{0,3}(`{3,}|~{3,})')
_ITEM_RE = re.compile(r'^([ \t]*)(?:[-*+]|\d{1,9}[.)])(?:[ \t]+|$)')
_HEADING_RE = re.compile(r'^[ \t]{0,3}(#{1,6})(?:[ \t]|$)')
_BREAK_RE = re.compile(r'^[ \t]{0,3}(?:(?:-[ \t]*){3,}|(?:\*[ \t]*){3,}|'
                       r'(?:_[ \t]*){3,})$')
_ROW_RE = re.compile(r'^[ \t]*\|')
_QUOTE_RE = re.compile(r'^[ \t]*>')
_SEPARATOR_RE = re.compile(r'^[ \t]*\|?[ \t]*:?-{1,}')
# A sentence ends at `.`, `!` or `?`, with any closing mark after it, where
# white space and then anything but a lowercase letter follow.
_SENTENCE_END_RE = re.compile(r'[.!?][)\]"\'*_`]*(\s+)(?=[^\sa-z])')


def _names_old(text):
    return any(needle in text for needle in LEFT_NEEDLES)


def _agent_files(root):
    """Each tracked file that instructs an agent and holds a line naming
    what 0.9.5 used, in the order the list of what is left gives them."""
    return [rel for rel, _count in left_for_owner(root)
            if _agent_rank(rel) is not None
            and os.path.splitext(rel)[1].lower() in AGENT_TEXT + AGENT_JSON]


def _line_kinds(lines):
    """One kind per line: `front` for the lines that open and close the
    settings at the top of the file and `meta` between them, `code` inside a
    fenced block, `fence`, `blank`, `heading`, `break`, `row`, `quote`,
    `item` for a list item's first line, and `text` for any other."""
    kinds, fence = [], None
    if lines and lines[0].strip() == '---':
        close = next((index for index in range(1, len(lines))
                      if lines[index].strip() == '---'), None)
        if close is not None:
            kinds = ['front'] + ['meta'] * (close - 1) + ['front']
    for line in lines[len(kinds):]:
        opened = _FENCE_RE.match(line)
        if fence is not None:
            if opened and opened.group(1)[0] == fence[0] \
                    and len(opened.group(1)) >= len(fence) \
                    and not line[opened.end():].strip():
                kinds.append('fence')
                fence = None
            else:
                kinds.append('code')
            continue
        if opened:
            kinds.append('fence')
            fence = opened.group(1)
        elif not line.strip():
            kinds.append('blank')
        elif _HEADING_RE.match(line):
            kinds.append('heading')
        elif _BREAK_RE.match(line):
            kinds.append('break')
        elif _ROW_RE.match(line):
            kinds.append('row')
        elif _QUOTE_RE.match(line):
            kinds.append('quote')
        elif _ITEM_RE.match(line):
            kinds.append('item')
        else:
            kinds.append('text')
    return kinds


def _kind_runs(kinds, kind):
    """`[(first, last)]`: each run of consecutive lines of `kind`."""
    runs, start = [], None
    for index, found in enumerate(kinds + [None]):
        if found == kind and start is None:
            start = index
        elif found != kind and start is not None:
            runs.append((start, index - 1))
            start = None
    return runs


def _sentence_cuts(joined):
    """`[(start, end)]`: the stretches of `joined`, a paragraph, that go: each
    sentence naming what 0.9.5 used, with the white space on the side of it
    that keeps the paragraph's line breaks where it can."""
    sentences, start = [], 0
    for found in _SENTENCE_END_RE.finditer(joined):
        sentences.append((start, found.start(1), found.end(1)))
        start = found.end(1)
    sentences.append((start, len(joined), len(joined)))
    cuts = []
    for index, (begin, end, gap_end) in enumerate(sentences):
        if not _names_old(joined[begin:end]):
            continue
        before = sentences[index - 1][1] if index else begin
        last = index == len(sentences) - 1
        if index and (last or '\n' not in joined[before:begin]):
            cuts.append((before, end))
        else:
            cuts.append((begin, gap_end))
    return cuts


def _paragraph(lines, first, last, gone, now):
    """The sentences naming what 0.9.5 used go from the paragraph on lines
    `first` to `last`; a line left empty goes, and a line left in part is
    given its new text in `now`."""
    texts = [line.rstrip('\r\n') for line in lines[first:last + 1]]
    joined = '\n'.join(texts)
    if not _names_old(joined):
        return
    keep = [True] * len(joined)
    for begin, end in _sentence_cuts(joined):
        for position in range(begin, end):
            keep[position] = False
    starts, at = [], 0
    for text in texts:
        starts.append(at)
        at += len(text) + 1
    # The paragraph as it now reads: a row for each line break kept, each
    # row placed on the line its first character comes from.
    rows, row = [], []
    for position, char in enumerate(joined):
        if keep[position] and char == '\n':
            rows.append(row)
            row = []
        elif keep[position]:
            row.append(position)
    rows.append(row)
    placed = {}
    for row in rows:
        text = ''.join(joined[position] for position in row)
        if not text.strip():
            continue
        offset = max(number for number, start in enumerate(starts)
                     if start <= row[0])
        if row[0] != starts[offset]:
            text = text.lstrip()
        placed[offset] = text.rstrip()
    for offset, text in enumerate(texts):
        index = first + offset
        if offset not in placed:
            gone[index] = True
        elif placed[offset] != text:
            now[index] = placed[offset] + (lines[index][len(text):] or '\n')


def _section_holds(lines, kinds, gone, index):
    """True where the heading on line `index` has a line under it, before the
    next heading of its level or above, that is not blank, not a break and
    not gone."""
    level = len(_HEADING_RE.match(lines[index]).group(1))
    for later in range(index + 1, len(lines)):
        if gone[later]:
            continue
        if kinds[later] == 'heading' and len(
                _HEADING_RE.match(lines[later]).group(1)) <= level:
            return False
        if kinds[later] not in ('blank', 'break'):
            return True
    return False


def without_old_markdown(text):
    """`(new text, lines that named 0.9.5, log lines)` for a Markdown file
    that instructs an agent.

    Each line naming what 0.9.5 used goes with the part of the file it
    belongs to: a list item whole, with the lines that continue it and the
    items under it; a table row alone, and the table where no row is left;
    a line of a fenced code block alone, and the block where nothing is left
    in it; the sentence holding it in a paragraph. A heading left with
    nothing under it goes too, and the blank lines a removal leaves side by
    side become one. Every other line is as it was.
    """
    lines = text.splitlines(True)
    kinds = _line_kinds(lines)
    named = [_names_old(line) for line in lines]
    gone, now = [False] * len(lines), {}
    for index, kind in enumerate(kinds):
        if kind in ('heading', 'quote', 'meta') and named[index]:
            gone[index] = True
    # A list item: its own lines run to the next item, a blank line or
    # another kind; its whole runs on over the items set deeper under it.
    for index, kind in enumerate(kinds):
        if kind != 'item':
            continue
        indent = len(_ITEM_RE.match(lines[index]).group(1).expandtabs(4))
        own, end = True, index
        for later in range(index + 1, len(lines)):
            if kinds[later] == 'item':
                deeper = len(_ITEM_RE.match(lines[later]).group(1)
                             .expandtabs(4)) > indent
                if not deeper:
                    break
                own = False
            elif kinds[later] not in ('text', 'quote'):
                break
            end = later
            if own and named[later]:
                named[index] = True
        if named[index]:
            for later in range(index, end + 1):
                gone[later] = True
    for first, last in _kind_runs(kinds, 'row'):
        head = range(first, min(first + 2, last + 1))
        if any(named[index] for index in head):
            for index in range(first, last + 1):
                gone[index] = True
            continue
        body = range(first + 2, last + 1) if (
            last > first and _SEPARATOR_RE.match(lines[first + 1])) \
            else range(first + 1, last + 1)
        for index in body:
            if named[index]:
                gone[index] = True
        if body and all(gone[index] for index in body) \
                and any(named[index] for index in body):
            for index in range(first, last + 1):
                gone[index] = True
    opened = None
    for index, kind in enumerate(kinds):
        if kind == 'fence' and opened is None:
            opened = index
        elif kind == 'fence':
            inside = range(opened + 1, index)
            for at in inside:
                if named[at]:
                    gone[at] = True
            if inside and all(gone[at] for at in inside) \
                    and any(named[at] for at in inside):
                gone[opened] = gone[index] = True
            opened = None
    for first, last in _kind_runs(kinds, 'text'):
        if not all(gone[index] for index in range(first, last + 1)):
            _paragraph(lines, first, last, gone, now)
    # A heading left with nothing under it goes, the deepest first, so a
    # heading whose only content was such a heading goes with it.
    for index in reversed(range(len(lines))):
        if kinds[index] == 'heading' and not gone[index] \
                and _section_holds(lines, kinds, [False] * len(lines), index) \
                and not _section_holds(lines, kinds, gone, index):
            gone[index] = True
    if not any(gone) and not now:
        return text, 0, []
    # The blank lines a removal leaves side by side become one, and so do
    # two breaks; none is left at the start or the end of the file.
    kept, removed = [], False
    for index, kind in enumerate(kinds):
        if gone[index]:
            removed = True
            continue
        if removed and kind == 'blank' and (
                not kept or kinds[kept[-1]] == 'blank'):
            continue
        if removed and kind == 'break':
            above = [at for at in kept if kinds[at] != 'blank']
            if not above or kinds[above[-1]] == 'break':
                continue
        kept.append(index)
        if kind != 'blank':
            removed = False
    if removed:
        while kept and kinds[kept[-1]] == 'blank':
            kept.pop()
    new = ''.join(now.get(index, lines[index]) for index in kept)
    log = []
    for index, line in enumerate(lines):
        if gone[index] and line.strip():
            log.append('removed %%s:%d: %s' % (index + 1, line.strip()))
        elif index in now:
            log.append('%%s:%d now reads: %s' % (index + 1, now[index].strip()))
    return new, sum(1 for line in lines if _names_old(line)), log


def without_old_json(text):
    """`(new text, lines that named 0.9.5, log lines)` for a JSON file that
    instructs an agent, each such line gone; the text as it was where what
    is left does not read as JSON."""
    lines = text.splitlines(True)
    named = [index for index, line in enumerate(lines) if _names_old(line)]
    if not named:
        return text, 0, []
    kept = [index for index in range(len(lines)) if index not in named]
    rows = dict((index, lines[index]) for index in kept)
    # An entry that was the last of its list leaves a comma behind it.
    for position, index in enumerate(kept[:-1]):
        after = kept[position + 1]
        if index + 1 != after and rows[index].rstrip().endswith(',') \
                and lines[after].lstrip()[:1] in (']', '}'):
            body = rows[index].rstrip('\r\n')
            rows[index] = body.rstrip()[:-1] + rows[index][len(body):]
    new = ''.join(rows[index] for index in kept)
    try:
        json.loads(new)
    except ValueError:
        return text, 0, []
    return new, len(named), ['removed %%s:%d: %s' % (index + 1,
                                                     lines[index].strip())
                             for index in named]


def _clean_agent_files(root, files, out):
    """The lines naming what 0.9.5 used go from each file that instructs an
    agent, each file kept as it was first, and each line counted."""
    for rel in files:
        ext = os.path.splitext(rel)[1].lower()
        path = os.path.join(root, *rel.split('/'))
        try:
            with open(path, 'r', encoding='utf-8', newline='') as handle:
                text = handle.read()
        except (IOError, OSError, UnicodeDecodeError):
            continue
        clean = without_old_json if ext in AGENT_JSON \
            else without_old_markdown
        new, count, log = clean(text)
        if new == text or not count:
            continue
        out.kept(_back_up_copy(root, rel))
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(new)
        out.done(rel)
        for line in log:
            out.note(line % rel)
        out.say(AGENT_LINES_WENT % (count, '' if count == 1 else 's', rel))


def _apply_markers(root, files, args, out):
    """Each 0.9.5 marker becomes one comment above the same test."""
    found = _marked_old(root)
    unread, total, written, whole, tag_lines = [], 0, 0, False, 0
    for rel in files:
        new, count, left = found.get(rel, (None, 0, []))
        if not count:
            continue
        gone = 0
        if os.path.splitext(rel)[1].lower() == '.py':
            new, gone = without_tag_lines(*_rewritten(
                _read(os.path.join(root, rel)), '.py')[::3])
        out.kept(_back_up_copy(root, rel))
        _write(os.path.join(root, rel), new)
        out.done(rel)
        line = 'rewrote %d marker%s in %s as comments' % (count, _s(range(
            count)), rel)
        if os.path.splitext(rel)[1].lower() in ('.sh', '.bash', '.sql'):
            line += ONE_TEST_NOW
            whole = True
        out.note(line)
        if gone:
            out.note(TAG_LINES_WENT % (gone, '' if gone == 1 else 's')
                     + ' in ' + rel)
        tag_lines += gone
        total += count
        written += 1
        for number in unread_titles(rel, new):
            unread.append(TITLE_UNREAD % (rel, number))
    out.say('rewrote %d marker%s in %d file%s%s'
            % (total, '' if total == 1 else 's', written,
               '' if written == 1 else 's',
               '; a shell or SQL file is one test now, and passes when it '
               'exits 0' if whole else ''))
    if tag_lines:
        out.say(TAG_LINES_WENT % (tag_lines, '' if tag_lines == 1 else 's'))
    _clean_agent_files(root, [rel for rel in files if rel not in found],
                       out)
    held =set((_spec_name(spec), old)
               for spec, pairs in _lettered_specs(root).items()
               for old, _new in pairs)
    for rel, (_new, count, left) in sorted(found.items()):
        if count and rel in files:
            # The rewrite adds and drops lines above a marker it leaves, so
            # the line is read again from the file as it now stands.
            left = rewrite_markers(_read(os.path.join(root, rel)),
                                   os.path.splitext(rel)[1].lower())[2]
        for number, lettered in left:
            if lettered is None:
                out.owner(LEFT % (rel, number))
            elif lettered in held:
                out.owner(LEFT_LETTERED % ((rel, number) + lettered))
            else:
                out.owner(LEFT_NO_SPEC % (
                    (rel, number) + lettered + lettered[:1]
                    + (_comment(os.path.splitext(rel)[1].lower(), '',
                                lettered[0], 'PROOF-<n>'),)))
    for line in unread:
        out.owner(line)


def _strings(node):
    return [part.value for part in ast.walk(node)
            if isinstance(part, ast.Constant) and isinstance(part.value, str)]


def _plugin_path(call):
    """True for `sys.path.insert(...)` or `.append(...)` naming the folder
    0.9.5 copied its plugins into."""
    target = call.func
    if not (isinstance(target, ast.Attribute)
            and target.attr in ('insert', 'append')
            and isinstance(target.value, ast.Attribute)
            and target.value.attr == 'path'
            and isinstance(target.value.value, ast.Name)
            and target.value.value.id == 'sys'):
        return False
    strings = _strings(call)
    return (any(PLUGIN_DIR in text.replace('\\', '/') for text in strings)
            or ('.purlin' in strings and 'plugins' in strings))


def _cut(line, start, end):
    """`line` without its bytes `start` to `end`, a list entry, and without
    the comma that set the entry apart."""
    raw = line.encode('utf-8')
    head, tail = raw[:start].decode('utf-8'), raw[end:].decode('utf-8')
    after = re.match(r'\s*,[ \t]*', tail)
    if after:
        return head + tail[after.end():]
    return re.sub(r'[ \t]*,[ \t]*$', '', head) + tail


def clean_conftest(text):
    """`text` without what loaded 0.9.5's pytest plugin, or None where
    nothing else is left; raises SyntaxError for text Python cannot read.

    The entry naming the plugin goes from `pytest_plugins`, the whole line
    where it was the only entry, and so does a `sys.path` line pointing at
    `.purlin/plugins`. The file is read as Python reads it, so text inside a
    comment or a docstring is never edited. A file left with nothing but
    comments, a docstring and imports nothing uses is no longer needed.
    """
    tree = ast.parse(text)
    lines = text.splitlines(True)
    drop, cuts = set(), []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) \
                and _plugin_path(node.value):
            drop.update(range(node.lineno, node.end_lineno + 1))
        elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == 'pytest_plugins'
                for target in node.targets):
            value = node.value
            entries = (value.elts if isinstance(value, (ast.List, ast.Tuple))
                       else [value])
            named = [entry for entry in entries
                     if isinstance(entry, ast.Constant)
                     and isinstance(entry.value, str)
                     and PYTEST_PLUGIN in entry.value]
            if named and len(named) == len(entries):
                drop.update(range(node.lineno, node.end_lineno + 1))
            else:
                cuts.extend(entry for entry in named
                            if entry.lineno == entry.end_lineno)
    if not drop and not cuts:
        return text
    for entry in sorted(cuts, key=lambda e: (e.lineno, e.col_offset),
                        reverse=True):
        lines[entry.lineno - 1] = _cut(lines[entry.lineno - 1],
                                       entry.col_offset, entry.end_col_offset)
    kept = [line for number, line in enumerate(lines, 1) if number not in drop]
    if drop and max(drop) == len(lines):
        while kept and not kept[-1].strip():
            kept.pop()
    new = ''.join(kept)
    body = ast.parse(new).body
    if all(isinstance(node, (ast.Import, ast.ImportFrom, ast.Pass))
           or (isinstance(node, ast.Expr)
               and isinstance(node.value, ast.Constant))
           for node in body):
        return None
    return new


def _conftests(root):
    """Every `conftest.py` under the project that names the pytest plugin."""
    hits = []
    for dirpath, dirnames, names in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith('.') and d not in SKIP_DIRS)
        if 'conftest.py' in names:
            rel = os.path.relpath(os.path.join(dirpath, 'conftest.py'), root)
            hits.append(rel.replace(os.sep, '/'))
    return hits


def _wiring(root):
    """`[(path, new text)]`: what loaded 0.9.5's plugins, undone.

    A text of None means the file held nothing else and goes; False means
    a `conftest.py` Python cannot read, which is named and left. A `.csproj`
    compiling the xUnit logger is not rewritten: it is reported, with what
    to remove.
    """
    edits = []
    for rel in _conftests(root):
        try:
            text = _read(os.path.join(root, rel))
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if PYTEST_PLUGIN not in text:
            continue
        try:
            new = clean_conftest(text)
        except (SyntaxError, ValueError):
            edits.append((rel, False))
            continue
        if new != text:
            edits.append((rel, new))
    names = [name for name in sorted(os.listdir(root))
             if re.match(r'^(?:jest|vitest)\.config\.[cm]?[jt]s$|^jest\.'
                         r'config\.json$|^package\.json$', name)]
    for rel in names:
        text = _read(os.path.join(root, rel))
        if REPORTER_RE.search(text):
            new = REPORTER_RE.sub('', text)
            new = re.sub(r'\[\s*,\s*', '[', new)
            edits.append((rel, new))
    return edits


def _plugin_copies(root):
    folder = os.path.join(root, *PLUGIN_DIR.split('/'))
    if not os.path.isdir(folder):
        return []
    return ['%s/%s' % (PLUGIN_DIR, name) for name in sorted(os.listdir(folder))
            if name in PLUGIN_COPIES]


def _logger_projects(root):
    hits = []
    for rel in _files_under(root, '.', ('*.csproj',)):
        rel = rel[2:] if rel.startswith('./') else rel
        try:
            if XUNIT_LOGGER in _read(os.path.join(root, rel)):
                hits.append(rel)
        except (IOError, OSError, UnicodeDecodeError):
            continue
    return hits


def _detect_plugins(root):
    return _plugin_copies(root) + [rel for rel, new in _wiring(root)
                                   if new is not False]


def _apply_plugins(root, files, args, out):
    """The plugin copies go, and so does the wiring that loaded them."""
    copies = _plugin_copies(root)
    for rel in copies:
        _untrack(root, rel)
        try:
            os.remove(os.path.join(root, rel))
        except OSError:
            continue
        out.done(rel)
    if copies:
        out.say('removed the %d plugin cop%s under %s/: Purlin reads the '
                'report your own test command writes'
                % (len(copies), 'y' if len(copies) == 1 else 'ies',
                   PLUGIN_DIR))
    folder = os.path.join(root, *PLUGIN_DIR.split('/'))
    cache = os.path.join(folder, '__pycache__')
    if os.path.isdir(cache):
        shutil.rmtree(cache, ignore_errors=True)
    if os.path.isdir(folder) and not os.listdir(folder):
        os.rmdir(folder)
    for rel, new in _wiring(root):
        path = os.path.join(root, rel)
        if new is False:
            out.owner(CONFTEST_UNREAD % rel)
            continue
        out.kept(_back_up_copy(root, rel))
        if new is None:
            _untrack(root, rel)
            os.remove(path)
            out.say('removed %s: it held only the plugin\'s wiring' % rel)
        else:
            _write(path, new)
            out.say('removed the plugin\'s wiring from %s' % rel)
        out.done(rel)
    for rel in _logger_projects(root):
        out.owner('%s compiles the xUnit logger v0.9.5 shipped; remove that '
                  'line by hand, since dotnet test --logger trx needs nothing '
                  'added' % rel)


# Order matters: a migration can leave work for a later one, as the Windows
# tag rewritten to `@env(windows)` leaves a kind-of-test tag before it.
MIGRATIONS = (
    ('design-refs', 'remove the Figma source and the picture fingerprint '
     'from each spec that carries them',
     _detect_design_refs, _apply_design_refs),
    ('anchor-lines', 'take out > Requires: and > Global: from every spec, and '
     '> Scope: from every anchor', _detect_anchor_lines, _apply_anchor_lines),
    ('os-tags', 'rewrite the retired operating-system tag to @env(windows)',
     _detect_os_tags, _apply_os_tags),
    ('kind-tags', 'drop the kind of test from every proof line',
     _detect_kind_tags, _apply_kind_tags),
    ('untracked-files', 'drop the proof files and the old cache, and untrack '
     'the dashboard data',
     _detect_untracked, _apply_untracked),
    ('hooks', 'remove the git hooks an older release installed',
     _detect_hooks, _apply_hooks),
    ('config', 'write .purlin/config.json with version and tests alone',
     _detect_config, _apply_config),
    ('evidence', 'create .purlin/evidence/ with the README that says what '
     'it holds', _detect_evidence, _apply_evidence),
    ('dashboard', 'replace purlin-report.html with the page this release '
     'ships', _detect_dashboard, _apply_dashboard),
    (WORKFLOWS, 'remove each workflow that names a proof file, asking for '
     'each', _detect_workflows, _apply_workflows),
    ('lettered-proofs', 'give each proof numbered with a letter, such as '
     'PROOF-3b, the next free number in its spec', _detect_lettered,
     _apply_lettered),
    ('markers', 'rewrite each 0.9.5 marker as a comment above its test, and '
     'remove each line naming what 0.9.5 used from CLAUDE.md, AGENTS.md and '
     'the files under .claude/', _detect_markers, _apply_markers),
    ('plugins', 'remove the proof plugin copies and the wiring that loaded '
     'them', _detect_plugins, _apply_plugins),
)

def pending(project_root):
    """The migrations a project still needs, in the order they are applied.

    A workflow that names a proof file holds no update pending alone: one a
    person kept is theirs, and is asked about again only while another
    migration is pending.
    """
    found = _found(project_root)
    return [] if [item['id'] for item in found] == [WORKFLOWS] else found

def _found(project_root):
    """Every migration whose detector finds something, `workflows` included."""
    root = os.path.abspath(project_root)
    if not os.path.isdir(os.path.join(root, '.purlin')):
        return []
    found = []
    for name, description, detect, _apply in MIGRATIONS:
        try:
            files = detect(root)
        except (IOError, OSError, ValueError, UnicodeDecodeError):
            files = []
        if files:
            found.append({'id': name, 'description': description,
                          'files': files})
    return found

def scope_advice(project_root):
    """The line naming every feature spec with no `> Scope:` line, or None.

    Advice, not a migration: nothing is changed, and nothing stays pending.
    Anchors are exempt, because an anchor names no files. The
    words are the status's own, so the two never say it differently.
    """
    root = os.path.abspath(project_root)
    names = sorted(os.path.basename(rel)[:-len('.md')]
                   for rel in _files_under(root, 'specs', ('*.md',))
                   if not rel.startswith('specs/_anchors/')
                   and not SCOPE_RE.search(_read(os.path.join(root, rel))))
    if not names:
        return None
    return _plugin_module('mcp', 'purlin.status').status.incomplete_line(names)

# --- running ---------------------------------------------------------------
class _Report(object):
    """What one run changed: what it prints, what it logs and what it commits.

    `say` is a line of the migration being applied: its first is the line of
    totals, printed after the migration's id, and any later one a detail
    under it. `note` is one file's own line, which goes to the log alone.
    `owner` is a line the owner has to act on, printed last under its own
    heading. The log holds all three, in the order they were made.
    """
    def __init__(self):
        self.lines, self.owners, self.log, self.paths = [], [], [], []
        self.current, self.started = None, False
    def start(self, migration):
        self.current, self.started = migration, False
    def say(self, line):
        if self.current is None:
            shown = '  ' + line
        elif not self.started:
            shown = '  %s: %s' % (self.current, line)
        else:
            shown = '    ' + line
        self.started = True
        self.lines.append(shown)
        self.log.append(shown)
    def note(self, line):
        self.log.append('    ' + line)
    def owner(self, line):
        self.owners.append('  ' + line)
        self.log.append('  ' + line)
    def done(self, rel):
        if not rel.startswith('.git/') and rel not in self.paths:
            self.paths.append(rel)
    def kept(self, rel):
        if rel:
            self.note('kept the previous bytes at %s' % rel)

def _print_pending(items, root):
    print('%d migration%s pending in %s:' % (len(items), _s(items), root))
    for item in items:
        names = item['files'][:6] + (['and %d more' % (len(item['files']) - 6)]
                                     if len(item['files']) > 6 else [])
        print('  %s: %s\n      %s'
              % (item['id'], item['description'], '\n      '.join(names)))
        if item['id'] == 'config':
            try:
                old = _config(root)
            except (IOError, OSError, ValueError):
                continue
            if isinstance(old.get('tests'), list):
                continue
            entries, sources, _dropped = proposed_tests(root, old)
            for line in _proposal_lines(entries, sources):
                print('      ' + line)

def _commit(root, applied, paths):
    """One commit for the whole update, naming the migrations it carries."""
    for rel in paths:  # one at a time: a path git now ignores must not stop it
        _git(root, 'add', '-A', '--', rel)
    if _git(root, 'diff', '--cached', '--quiet')[0]:
        return None
    ok, out = _git(root, 'commit', '-q', '-m',
                   _COMMIT % (_version(), ', '.join(applied)))
    if ok:
        return _git(root, 'rev-parse', '--short', 'HEAD')[1].strip()
    print('The changes are staged and not committed: %s' % out)
    return None

def _agent_rank(rel):
    """Where a file that instructs an agent stands among what is left, or
    None for any other file: `CLAUDE.md`, then `AGENTS.md`, each at the root
    before one in a folder, then the files under `.claude/`."""
    name = os.path.basename(rel)
    if name in AGENT_FILES:
        return (AGENT_FILES.index(name), rel.count('/'))
    if rel.startswith(AGENT_DIR):
        return (len(AGENT_FILES), 0)
    return None


def left_for_owner(root):
    """`[(file, lines)]`: each tracked file still holding text 0.9.5 used,
    with how many of its lines do: the files that instruct an agent first,
    then most first and then by name."""
    command = ['grep', '-c', '-I', '-F']
    for needle in LEFT_NEEDLES:
        command += ['-e', needle]
    ok, out = _git(root, *command)
    found = []
    for line in (out.splitlines() if ok else []):
        rel, _colon, count = line.rpartition(':')
        if rel and count.isdigit():
            found.append((rel, int(count)))
    last = (len(AGENT_FILES) + 1, 0)
    return sorted(found, key=lambda item: (_agent_rank(item[0]) or last,
                                           -item[1], item[0]))

def _left_lines(root):
    found = left_for_owner(root)
    if not found:
        return []
    lines = [LEFT_HEADING]
    lines += ['  %s: %d line%s%s' % (rel, count, '' if count == 1 else 's',
                                     CHANGE_FIRST if _agent_rank(rel) else '')
              for rel, count in found[:LEFT_SHOWN]]
    more = len(found) - LEFT_SHOWN
    if more > 0:
        lines.append(LEFT_MORE % (more, '' if more == 1 else 's'))
    lines.append(LEFT_WHY % ', '.join(LEFT_NEEDLES))
    return lines

def _write_log(root, report, sha):
    """Every line of the run, each file's own included, added to the log."""
    path = os.path.join(root, *UPDATE_LOG.split('/'))
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write('purlin:init --update to %s%s\n'
                         % (_version(), ', committed as %s' % sha if sha
                            else ''))
            handle.write(''.join(line + '\n' for line in report.log))
    except (IOError, OSError):
        return False
    return True

def _parse(argv):
    parser = argparse.ArgumentParser(
        prog='update.py', description=__doc__.splitlines()[0])
    parser.add_argument('--yes', action='store_true',
                        help='answer yes to every question')
    parser.add_argument('--apply', metavar='ID[,ID...]',
                        help='apply these migrations and no other, asking '
                             'nothing')
    parser.add_argument('--test-command', action='append', default=[],
                        metavar='TOOL=COMMAND',
                        help='the command to write for one test tool, in '
                             'place of the one proposed')
    parser.add_argument('--project-root', default='.')
    return parser.parse_args(argv)

def main(argv=None):
    console_module.force_utf8_stdio()
    args = _parse(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(os.path.join(root, '.purlin')):
        print('There is no .purlin/ under %s, so there is nothing to update. '
              'Run purlin:init first.' % root, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    known = [m[0] for m in MIGRATIONS]
    chosen = None
    if args.apply is not None:
        chosen = [part.strip() for part in args.apply.split(',')
                  if part.strip()]
        for name in chosen:
            if name not in known:
                print(UNKNOWN_MIGRATION % (name, ', '.join(known)),
                      file=sys.stderr)
                return EXIT_BAD_INVOCATION
    args.commands = {}
    for given in args.test_command:
        tool, equals, command = given.partition('=')
        if not equals or not tool.strip() or not command.strip():
            print(BAD_TEST_COMMAND % given, file=sys.stderr)
            return EXIT_BAD_INVOCATION
        args.commands[tool.strip()] = command.strip()
    # The questions inside a migration are asked only where each migration
    # is asked about too.
    args.ask = not args.yes and chosen is None
    problem = config_engine.config_problem(root)
    if problem:
        print(problem, file=sys.stderr)
        return EXIT_UNREADABLE
    items = pending(root)
    advice = scope_advice(root)
    if not items:
        print('Nothing is pending: this project is at %s.' % _version())
        if advice:
            print(advice)
        _print_ending(root)
        return EXIT_OK
    # A run told what to apply names it in one line; a run that asks, or
    # one that will apply nothing, prints the list the answers are about.
    listed = [item['id'] for item in items
              if chosen is None or item['id'] in chosen]
    told = not args.ask and bool(listed)
    if told:
        print(APPLYING % (len(listed), _s(listed), ', '.join(listed)))
    else:
        _print_pending(items, root)
        print('')
    before = _git(root, 'rev-parse', '--short', 'HEAD')
    appliers = dict((m[0], m[3]) for m in MIGRATIONS)
    report, applied, asked = _Report(), [], set()
    queue = items
    while queue:
        item = queue[0]
        asked.add(item['id'])
        report.start(None)
        if chosen is not None:
            wanted = item['id'] in chosen
        else:
            wanted = _confirm('Apply %s, which will %s?'
                              % (item['id'], item['description']), args.yes)
        if not wanted:
            report.say('skipped %s' % item['id'])
            queue = queue[1:]
            continue
        report.start(item['id'])
        appliers[item['id']](root, item['files'], args, report)
        applied.append(item['id'])
        # Read again: a migration can leave work for a later one, as the
        # Windows tag rewritten to `@env(windows)` leaves a kind-of-test tag
        # at the end of its line.
        queue = [found for found in _found(root) if found['id'] not in asked]
    report.start(None)
    if not told:
        print('')
    for line in report.lines:
        print(line)
    sha = _commit(root, applied, report.paths)
    if sha:
        print('  committed %s as %s'
              % (sha, _COMMIT % (_version(), ', '.join(applied))))
    if not applied:
        # Nothing changed, so the run says how to change it and no more.
        print('')
        print(RUN_UPDATE)
        print(HOW_TO_APPLY)
        return EXIT_OK
    if advice:
        report.owner(advice)
    if applied:
        print('')
        print(NOT_RUN)
        earlier = before[1].strip() if before[0] else ''
        if earlier:
            print(OLD_RECORD % earlier)
        if _write_log(root, report, sha):
            print(BACKUPS_KEPT % (BACKUP_DIR, DELETED_IN_GIT % earlier
                                  if earlier else ''))
    left = _left_lines(root) if applied else []
    if left:
        print('')
        for line in left:
            print(line)
    if report.owners:
        print('')
        print(OWNER_HEADING)
        for line in report.owners:
            print(line)
    print('')
    left_pending = [item['id'] for item in pending(root)]
    if left_pending:
        print(RUN_UPDATE)
        print(STILL_PENDING % (len(left_pending), ' is' if len(left_pending)
                               == 1 else 's are', ', '.join(left_pending)))
    else:
        print(RUN_TESTS)
        print(RUN_TESTS_FIRST)
        print(FAILS_IN_FULL_RUN)
    return EXIT_OK


def _print_ending(root):
    """End as `purlin:status` ends: the update line while one is pending, the summary.

    Read from the payload alone, so the run writes nothing a person declined.
    """
    status = _plugin_module('mcp', 'purlin.status').status
    payload = _plugin_module('mcp', 'purlin.payload').payload
    data = payload.build_payload(root)
    print('')
    if not data['features']:
        for line in status.no_spec_lines(root):
            print(line)
        return
    for line in status.ending_lines(data, root):
        print(line)


if __name__ == '__main__':
    sys.exit(main())
