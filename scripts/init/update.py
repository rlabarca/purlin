#!/usr/bin/env python3
"""Bring a project an older Purlin set up onto this release.

    python3 scripts/init/update.py [--yes] [--project-root DIR]

`purlin:init --update` is the command you run, and init hands it here. This
file is the part of the upgrade that has to be deterministic, so the skill
asks and this script edits.

`pending(project_root)` returns the migrations a project still needs: an id, one
line saying what it does, and the files it touches. The run prints that list
before it asks, and `sync_status` reads the same function, so the advisory you
see and the work this script does cannot disagree. The detectors read the
layout v0.9.5 left, and a project lands straight on this release's layout.
Every migration asks before it writes, and every file it rewrites is copied
beside itself first as `<name>.local-<sha8>.bak`. `--yes` answers yes to every
migration's question. A workflow that names a proof file is removed only on a
yes typed for that file, so under `--yes` each is kept and named. A file this release deletes rather than rewrites is left in git
history instead of copied.

Exit codes: 0 nothing pending or the run applied what was, 1 the settings
file cannot be read, 2 no Purlin project at that root.
"""

import argparse
import ast
import fnmatch
import hashlib
import json
import os
import re
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
WINDOWS_TAG_RE = re.compile(r'(?m)[ \t]*@windows[ \t]*(?=\r?$)')
KIND_TAG_RE = re.compile(r'(?m)^(- PROOF-.*?)[ \t]+@(?:unit|integration|e2e)'
                         r'(?=(?:[ \t]+@env\([a-z]+\))?[ \t]*\r?$)')
WORKFLOW_MARKER = '.proofs-'
WORKFLOWS = 'workflows'
PRE_PUSH_HOOK = '.git/hooks/pre-push'
PRE_PUSH_KEY = 'pre_push'
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
RENUMBERED = '%s %s is now %s'
LEFT = ('left %s:%d as it was: write the marker as a comment above each test '
        'by hand')
LEFT_NO_SPEC = ('left %s:%d as it was: it names %s %s, which no spec has. '
                'Write the proof with purlin:spec %s, then write the marker '
                'as a comment above the test by hand')
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
IGNORE_LINES = ('.purlin/report-data.js',)
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

def _back_up_copy(path, rel):
    """Copy the bytes about to change, named for their sha256, and say where."""
    try:
        with open(path, 'rb') as handle:
            previous = handle.read()
    except (IOError, OSError):
        return None
    suffix = '.local-%s.bak' % hashlib.sha256(previous).hexdigest()[:8]
    try:
        with open(path + suffix, 'wb') as handle:
            handle.write(previous)
    except (IOError, OSError):
        return None
    return rel + suffix

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

def _confirm(question, assume_yes):
    if assume_yes:
        return True
    try:
        answer = input('%s [y/N] ' % question)
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().lower() in ('y', 'yes')

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
        out.kept(_back_up_copy(path, rel))
        text, removed = _design_lines(_read(path))
        _write(path, text)
        out.done(rel)
        out.say('removed the design reference from %s: %s'
                % (rel, ', '.join('> ' + name for name in removed)))

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
        out.kept(_back_up_copy(path, rel))
        text, removed = _anchor_lines(rel, _read(path))
        _write(path, text)
        out.done(rel)
        out.say('removed from %s: %s'
                % (rel, _joined(['> %s:' % name for name in removed])))
    for anchor in sorted(named):
        specs = named[anchor]
        out.say((NAMED_ONE if len(specs) == 1 else NAMED_MANY)
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
    if any(line not in lines for line in IGNORE_LINES):
        hits.append('.gitignore')
    return sorted(set(hits))

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
        out.kept(_back_up_copy(path, '.gitignore'))
        missing = [l for l in IGNORE_LINES if l not in text.splitlines()]
        if text and not text.endswith('\n'):
            text += '\n'
        _write(path, text + '\n# Regenerated locally, never committed\n'
               + ''.join(line + '\n' for line in missing))
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
        out.kept(_back_up_copy(path, rel))
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

def _tests_setting(root, old):
    """`(the tests setting, the names dropped)` from the config v0.9.5 wrote.

    Each framework `test_framework` named becomes the suite init writes for
    it, xunit read as dotnet. v0.9.5 wrote down every plugin it shipped, so a
    Python-only tree can carry `pytest,jest,shell,vitest`: a name detection
    does not find in the tree is dropped rather than written, because its
    suite would fail on every run. `auto`, or no value, writes what detection
    finds. A config that already carries `tests` keeps it.
    """
    frameworks = _frameworks()
    if isinstance(old.get('tests'), list):
        return old['tests'], []
    detected = frameworks.detect_frameworks(root)
    raw = str(old.get('test_framework') or '')
    names = [part.strip() for part in raw.split(',') if part.strip()]
    if not names or 'auto' in names:
        return frameworks.entries_for(detected), []
    wanted, dropped = [], []
    for name in names:
        suite = OLD_FRAMEWORKS.get(name)
        if suite is None or suite not in detected:
            dropped.append(name)
        elif suite not in wanted:
            wanted.append(suite)
    return frameworks.entries_for(wanted), dropped


def _apply_config(root, files, args, out):
    """`version` and `tests`, and every other key removed and named."""
    old = _config(root)
    path = os.path.join(root, '.purlin', 'config.json')
    out.kept(_back_up_copy(path, '.purlin/config.json'))
    tests, unwired = _tests_setting(root, old)
    for name in unwired:
        out.say(DROPPED_FRAMEWORK % name)
    config = {'version': _version(), 'tests': tests}
    _write(path, json.dumps(config, indent=2) + '\n')
    out.done('.purlin/config.json')
    removed = [key for key in old if key not in SETTINGS]
    if removed:
        out.say(REMOVED_KEYS % ', '.join(removed))
    names = [entry.get('name') for entry in tests if isinstance(entry, dict)]
    out.say('wrote the tests setting: %s' % (', '.join(names) or 'no suite; '
            'add one under "tests" in .purlin/config.json'))

def _detect_os_tags(root):
    return [rel for rel in _files_under(root, 'specs', ('*.md',))
            if WINDOWS_TAG_RE.search(_read(os.path.join(root, rel)))]

def _apply_os_tags(root, files, args, out):
    """A proof names an operating system now, or names none and runs anywhere."""
    for rel in files:
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(path, rel))
        _write(path, WINDOWS_TAG_RE.sub(' @env(windows)', _read(path)))
        out.done(rel)
    out.say('rewrote the operating-system tags in %d spec%s'
            % (len(files), _s(files)))

def _detect_kind_tags(root):
    """Every spec with a proof line that still names what kind of test it is."""
    return [rel for rel in _files_under(root, 'specs', ('*.md',))
            if KIND_TAG_RE.search(_read(os.path.join(root, rel)))]

def _apply_kind_tags(root, files, args, out):
    """A proof line names an operating system or `@manual`, and nothing else."""
    for rel in files:
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(path, rel))
        _write(path, KIND_TAG_RE.sub(lambda m: m.group(1), _read(path)))
        out.done(rel)
    out.say('dropped the kind of test from the proof lines of %d spec%s: '
            'purlin:test runs every marked test' % (len(files), _s(files)))

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
        if args.yes or not _confirm(WORKFLOW_QUESTION % rel, False):
            out.say(WORKFLOW_KEPT % rel)
            continue
        out.kept(_back_up_copy(os.path.join(root, rel), rel))
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
        out.kept(_back_up_copy(path, rel))
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
        out.kept(_back_up_copy(path, rel))
        _write(path, new)
        out.done(rel)
        marks += count
        marked += 1
    out.say('renumbered %d proof%s in %d spec%s and %d marker%s in %d file%s'
            % (len(changes), _s(changes), len(files), _s(files), marks,
               '' if marks == 1 else 's', marked, '' if marked == 1 else 's'))
    for line in changes:
        out.say('  ' + line)


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


def _rewrite_python(lines, ext):
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
    # A file whose every line ends `\r\n` keeps that ending, the comments
    # written into it included.
    eol = ('\r\n' if '\r\n' in text
           and text.count('\r\n') == text.count('\n') else '\n')
    rewrite = _REWRITERS.get(ext)
    if rewrite is None:
        return _rewrite_js(text, eol)
    ending = eol if text.endswith(eol) else ''
    lines = text.split(eol)
    if ending:
        lines = lines[:-1]
    out, count, left = rewrite(lines, ext)
    return eol.join(out) + ending, count, left


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
    return [rel for rel, (_new, count, _left) in _marked_old(root).items()
            if count]


def _apply_markers(root, files, args, out):
    """Each 0.9.5 marker becomes one comment above the same test."""
    found = _marked_old(root)
    unread = []
    for rel in files:
        new, count, left = found.get(rel, (None, 0, []))
        if not count:
            continue
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(path, rel))
        _write(path, new)
        out.done(rel)
        line = 'rewrote %d marker%s in %s as comments' % (count, _s(range(
            count)), rel)
        ext = os.path.splitext(rel)[1].lower()
        if ext in ('.sh', '.bash', '.sql'):
            line += ('; the file is one test now, and passes when it exits 0')
        out.say(line)
        for number in unread_titles(rel, new):
            unread.append(TITLE_UNREAD % (rel, number))
    held = set((_spec_name(spec), old)
               for spec, pairs in _lettered_specs(root).items()
               for old, _new in pairs)
    for rel, (_new, _count, left) in sorted(found.items()):
        for number, lettered in left:
            if lettered is None:
                out.say(LEFT % (rel, number))
            elif lettered in held:
                out.say(LEFT_LETTERED % ((rel, number) + lettered))
            else:
                out.say(LEFT_NO_SPEC % ((rel, number) + lettered
                                        + lettered[:1]))
    for line in unread:
        out.say(line)


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
            out.say(CONFTEST_UNREAD % rel)
            continue
        out.kept(_back_up_copy(path, rel))
        if new is None:
            _untrack(root, rel)
            os.remove(path)
            out.say('removed %s: it held only the plugin\'s wiring' % rel)
        else:
            _write(path, new)
            out.say('removed the plugin\'s wiring from %s' % rel)
        out.done(rel)
    for rel in _logger_projects(root):
        out.say('%s compiles the xUnit logger v0.9.5 shipped; remove that '
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
    ('markers', 'rewrite each 0.9.5 marker as a comment above its test',
     _detect_markers, _apply_markers),
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
    """What one run changed: the lines it prints and the paths it commits."""
    def __init__(self):
        self.lines, self.paths = [], []
    def say(self, line):
        self.lines.append(line)
    def done(self, rel):
        if not rel.startswith('.git/') and rel not in self.paths:
            self.paths.append(rel)
    def kept(self, rel):
        if rel:
            self.say('kept the previous bytes at %s' % rel)

def _print_pending(items, root):
    print('%d migration%s pending in %s:' % (len(items), _s(items), root))
    for item in items:
        names = item['files'][:6] + (['and %d more' % (len(item['files']) - 6)]
                                     if len(item['files']) > 6 else [])
        print('  %s: %s\n      %s'
              % (item['id'], item['description'], '\n      '.join(names)))

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

def main(argv=None):
    console_module.force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog='update.py', description=__doc__.splitlines()[0])
    parser.add_argument('--yes', action='store_true',
                        help='answer yes to every question')
    parser.add_argument('--project-root', default='.')
    args = parser.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(os.path.join(root, '.purlin')):
        print('There is no .purlin/ under %s, so there is nothing to update. '
              'Run purlin:init first.' % root, file=sys.stderr)
        return EXIT_BAD_INVOCATION
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
    _print_pending(items, root)
    print('')
    appliers = dict((m[0], m[3]) for m in MIGRATIONS)
    report, applied, asked = _Report(), [], set()
    queue = items
    while queue:
        item = queue[0]
        asked.add(item['id'])
        if not _confirm('Apply %s, which will %s?'
                        % (item['id'], item['description']), args.yes):
            report.say('skipped %s' % item['id'])
            queue = queue[1:]
            continue
        appliers[item['id']](root, item['files'], args, report)
        applied.append(item['id'])
        # Read again: a migration can leave work for a later one, as the
        # Windows tag rewritten to `@env(windows)` leaves a kind-of-test tag
        # at the end of its line.
        queue = [found for found in _found(root) if found['id'] not in asked]
    print('')
    for line in report.lines:
        print('  %s' % line)
    sha = _commit(root, applied, report.paths)
    if sha:
        print('  committed %s as %s'
              % (sha, _COMMIT % (_version(), ', '.join(applied))))
    if advice:
        print('  %s' % advice)
    _print_ending(root)
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
