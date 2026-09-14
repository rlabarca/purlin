#!/usr/bin/env python3
"""Bring a project an older Purlin set up onto this release.

    python3 scripts/init/update.py [--check] [--json] [--yes] [--project-root DIR]

`purlin:init --update` is the command you run; this file is the part of it that
has to be deterministic, so the skill asks and this script edits.

`pending(project_root)` returns the migrations a project still needs: an id, one
line saying what it does, and the files it touches. `--check` prints that list
and exits 1 while anything is pending, and `sync_status` reads the same
function, so the advisory you see and the work this script does cannot disagree.
The detectors read both old layouts: the one v0.9.5 left and the one the 0.10
development branch left. Every migration asks before it writes, and every file
it rewrites is copied beside itself first as `<name>.local-<sha8>.bak`. `--yes`
answers yes to every question. A file this release deletes rather than rewrites
is left in git history instead of copied.

Exit codes: 0 nothing pending or the run applied what was, 1 `--check` with
something pending, 2 no Purlin project at that root.
"""

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

EXIT_OK, EXIT_PENDING, EXIT_BAD_INVOCATION = 0, 1, 2

PLUGIN_ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
_MCP_DIR = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import console as console_module                  # noqa: E402
# --- the migration table: the one place a retired spelling is written -------
# Each line ends with a `# retired` comment, which is what the vocabulary
# proof reads to step over exactly these lines and no others.

PROOF_FILE_GLOB = '*.proofs-*.json'                        # retired
RUN_FILE_GLOB = '*.recei[p]t.json'                         # retired
DASHBOARD_DATA = '.purlin/report-data.js'                  # retired
CACHE_DIR = '.purlin/cache'                                # retired
OLD_SHELL_PLUGIN = 'purlin-proof.sh'                       # retired
REGISTRY_KEY = 'platforms'                                 # retired
SCOPE_TAG_RE = re.compile(r'[ \t]*@on\(([a-z0-9][a-z0-9-]*)\)')  # retired
TIER_TAG_RE = re.compile(r'(?m)[ \t]*@windows[ \t]*$')     # retired
DESIGN_SCHEME = 'figma://'                                 # retired
DESIGN_FIELDS = ('> Visual-Reference:', '> Visual-Hash:')  # retired
WORKFLOW_MARKERS = ('PURLIN_PLATFORM', 'scripts/ci/verify_gate.py',
                    'scripts/update/migrate.py', '.proofs-')  # retired

# --- what this release writes instead --------------------------------------
IGNORE_LINES = ('.purlin/report-data.js', '.purlin/report-stamp.js')
PRE_PUSH_SCRIPT = 'scripts/hooks/pre-push.sh'
_SHIM_LINE = 'PURLIN_SCRIPT="%s"' % PRE_PUSH_SCRIPT
RECORDS_DIR = '.purlin/records'
WORKFLOW_DIR = '.github/workflows'
OS_NAMES = ('linux', 'macos', 'windows')
GATES = ('tested', 'recorded', 'approved')  # the gate question's three answers
ARROW = '→'
DROPPED_FRAMEWORK = ('dropped %s from test_framework: nothing in the tree '
                     'runs it')
_COMMIT = 'chore(update): migrate to %s (%s)'

# A renamed plugin copy keeps the name the project gave it: its tests name it.
PLUGIN_SOURCES = {OLD_SHELL_PLUGIN: 'shell_purlin.sh'}

GATE_QUESTION = """
What must be true before CI lets a change merge?
  tested    every rule has a passing tagged test
  recorded  CI writes a record at this commit, at or above the minimum strength
  approved  recorded, plus a current approval on every high and medium risk rule"""

RECORDS_README = """# Records

One file per verify run, committed, at
`.purlin/records/<feature>/<timestamp>-<commit7>-<runner>.json`. A record says
what ran, on which commit, what passed and the test strength. The git history of
this folder is the log, so adding a file never conflicts. Verify prunes a
feature's records past the newest three unless a `validated/<name>` tag names
them. You do not edit anything here by hand.
"""

# --- helpers ---------------------------------------------------------------
def _read(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()

def _write(path, text):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)

def _git(root, *args):
    try:
        done = subprocess.run(['git'] + list(args), cwd=root,
                              capture_output=True, text=True)
    except (OSError, ValueError) as exc:
        return False, str(exc)
    return done.returncode == 0, (done.stdout + done.stderr).strip()

def _untrack(root, rel):
    _git(root, 'rm', '-q', '--cached', '--ignore-unmatch', '--', rel)

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
    try:
        return json.loads(_read(os.path.join(root, '.purlin', 'config.json')))
    except (IOError, OSError, ValueError):
        return {}

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

def _gate():
    return _plugin_module('mcp', 'purlin.gate').gate

def _frameworks():
    return _plugin_module('mcp', 'purlin.frameworks').frameworks

def _flow():
    return _plugin_module('run', 'workflow')

def _confirm(question, assume_yes):
    if assume_yes:
        return True
    try:
        answer = input('%s [y/N] ' % question)
    except (EOFError, KeyboardInterrupt):
        return False
    return answer.strip().lower() in ('y', 'yes')

def _host(root):
    ok, out = _git(root, 'remote', 'get-url', 'origin')
    if ok and ('dev.azure.com' in out or 'visualstudio.com' in out):
        return 'azure'
    return 'github'

def _s(items):
    return '' if len(items) == 1 else 's'

# --- the migrations ---------------------------------------------------------
def _detect_untracked(root):
    hits = _files_under(root, 'specs', (PROOF_FILE_GLOB, RUN_FILE_GLOB))
    ok, tracked = _git(root, 'ls-files')
    hits += [rel for rel in (tracked.splitlines() if ok else [])
             if rel == DASHBOARD_DATA or rel.startswith(CACHE_DIR + '/')]
    path = os.path.join(root, '.gitignore')
    lines = _read(path).splitlines() if os.path.isfile(path) else []
    if any(line not in lines for line in IGNORE_LINES):
        hits.append('.gitignore')
    return sorted(set(hits))

def _apply_untracked(root, files, args, out):
    gone = 0
    for rel in files:
        if rel == '.gitignore':
            continue
        _untrack(root, rel)
        out.done(rel)
        if rel.startswith('specs/'):
            os.remove(os.path.join(root, rel))
            gone += 1
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
    out.say('deleted %d file%s beside the specs and untracked the dashboard '
            'data and the cache; proofs are runtime now and records live in %s'
            % (gone, '' if gone == 1 else 's', RECORDS_DIR))

def _detect_hooks(root):
    hits = []
    if os.path.isfile(os.path.join(root, '.purlin', 'hooks', 'pre-commit')):
        hits.append('.purlin/hooks/pre-commit')
    delegator = os.path.join(root, '.git', 'hooks', 'pre-commit')
    if os.path.isfile(delegator) and 'purlin' in _read(delegator).lower():
        hits.append('.git/hooks/pre-commit')
    shim = os.path.join(root, '.purlin', 'hooks', 'pre-push')
    if os.path.isfile(shim) and _SHIM_LINE not in _read(shim).splitlines():
        hits.append('.purlin/hooks/pre-push')
    return hits

def _apply_hooks(root, files, args, out):
    for rel in files:
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(path, rel))
        if rel.endswith('pre-commit'):
            _untrack(root, rel)
            os.remove(path)
            out.say('removed %s; this release runs no pre-commit hook' % rel)
        else:
            _write(path, ''.join(_SHIM_LINE + '\n'
                                 if l.startswith('PURLIN_SCRIPT=') else l
                                 for l in _read(path).splitlines(True)))
            out.say('pointed %s at %s' % (rel, PRE_PUSH_SCRIPT))
        out.done(rel)

def _detect_config(root):
    config = _config(root)
    if not config:
        return []
    stale = ('gate' not in config
             or config.get('version') != _version()
             or str(config.get('pre_push', 'off')) not in ('on', 'off')
             or any(key in config for key in _gate().RETIRED_KEYS))
    return ['.purlin/config.json'] if stale else []

def _ask_gate(previous, assume_yes):
    """The one question init asks, asked once more on an update."""
    default = 'recorded' if str(previous).strip() == 'strict' else 'tested'
    if assume_yes:
        return default
    print(GATE_QUESTION)
    try:
        answer = input('Gate [%s]: ' % default).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    return answer if answer in GATES else default

def _prune_frameworks(root, recorded):
    """`(the value to record, the names dropped)` for one project tree.

    An older release recorded every plugin it shipped, so a Python-only tree
    can carry `pytest,jest,shell,vitest` and print a jest runner exiting
    non-zero on every run. A recorded name that detection does not find and
    the tree carries no wiring for is dropped; a name the tree does carry
    stays even when detection would not have picked it. `auto` is left alone:
    it names nothing to drop.
    """
    frameworks = _frameworks()
    raw = str(recorded or '')
    if not raw.strip() or 'auto' in [part.strip() for part in raw.split(',')]:
        return raw or 'auto', []
    named, unknown = frameworks.resolve_frameworks(root, raw)
    kept, dropped = frameworks.prune_unwired(root, named)
    value = ','.join(kept + unknown)
    return value or 'auto', dropped

def _apply_config(root, files, args, out):
    gate = _gate()
    old = _config(root)
    path = os.path.join(root, '.purlin', 'config.json')
    out.kept(_back_up_copy(path, '.purlin/config.json'))
    chosen = _ask_gate(old.get('pre_push'), args.yes)
    resolved = gate.resolve_gate(dict(old, gate=chosen))
    framework, unwired = _prune_frameworks(root, resolved.test_framework)
    config = {
        'version': _version(), 'gate': chosen,
        'ai_review_at': resolved.ai_review_at, 'ci': old.get('ci') or _host(root),
        'min_strength': resolved.min_strength, 'sql_engine': resolved.sql_engine,
        'mutation_engine': resolved.mutation_engine,
        'test_framework': framework, 'digest': old.get('digest', 'auto'),
        'pre_push': resolved.pre_push,
    }
    for name in unwired:
        out.say(DROPPED_FRAMEWORK % name)
    if chosen == 'approved':
        config['approvers'] = resolved.approvers
    dropped = sorted(key for key in gate.RETIRED_KEYS if key in old)
    _write(path, json.dumps(config, indent=2) + '\n')
    out.done('.purlin/config.json')
    out.say('set the gate to %s%s' % (chosen, '' if not dropped else
            ' and dropped %d key%s this release does not read: %s'
            % (len(dropped), _s(dropped), ', '.join(dropped))))

def _detect_os_tags(root):
    hits = []
    for rel in _files_under(root, 'specs', ('*.md',)):
        text = _read(os.path.join(root, rel))
        if SCOPE_TAG_RE.search(text) or TIER_TAG_RE.search(text):
            hits.append(rel)
    return hits

def _apply_os_tags(root, files, args, out):
    """A proof names an operating system now, or names none and runs anywhere."""
    registry = _config(root).get(REGISTRY_KEY) or {}
    decided = {}

    def tag(name, prefix):  # asked about once per scope, then remembered
        if name not in decided:
            entry = registry.get(name)
            found = (str(entry.get('os', '')).strip().lower()
                     if isinstance(entry, dict) else name)
            decided[name] = found if found in OS_NAMES else None
            if decided[name] is None:
                out.say('dropped the scope on %s: it names no operating '
                        'system, so any runner proves it now' % name)
            elif not _confirm('Rewrite the %s scope to @env(%s)?'
                              % (name, decided[name]), args.yes):
                out.say('dropped the scope on %s rather than guess an '
                        'operating system' % name)
                decided[name] = None
        return '' if decided[name] is None else '%s @env(%s)' % (prefix,
                                                                 decided[name])

    for rel in files:
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(path, rel))
        text = SCOPE_TAG_RE.sub(lambda m: tag(m.group(1).strip(), ''),
                                _read(path))
        _write(path, TIER_TAG_RE.sub(lambda m: tag('windows', ' @unit'), text))
        out.done(rel)
    out.say('rewrote the operating-system tags in %d spec%s'
            % (len(files), _s(files)))

def _detect_design_sources(root):
    hits = []
    for rel in _files_under(root, 'specs', ('*.md',)):
        for line in _read(os.path.join(root, rel)).splitlines():
            if line.startswith(DESIGN_FIELDS) or (
                    line.startswith('> Source:') and DESIGN_SCHEME in line):
                hits.append(rel)
                break
    return hits

def _apply_design_sources(root, files, args, out):
    """A design is a versioned file under designs/, never a tool connection."""
    for rel in files:
        path = os.path.join(root, rel)
        out.kept(_back_up_copy(path, rel))
        kept, dropping = [], False
        for line in _read(path).splitlines(True):
            if line.startswith(DESIGN_FIELDS):
                dropping = True
                continue
            if dropping and line.startswith('>   '):
                continue
            dropping = False
            if line.startswith('> Source:') and DESIGN_SCHEME in line:
                line = '> Source: designs/%s/\n' % os.path.basename(rel)[:-3]
            kept.append(line)
        _write(path, ''.join(kept))
        out.done(rel)
    out.say('pointed %d spec%s at designs/<feature>/ instead of a design tool'
            % (len(files), _s(files)))

def _detect_workflows(root):
    hits = []
    for rel in _files_under(root, WORKFLOW_DIR, ('*.yml', '*.yaml')):
        try:
            text = _read(os.path.join(root, rel))
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if any(marker in text for marker in WORKFLOW_MARKERS):
            hits.append(rel)
    return hits

def _apply_workflows(root, files, args, out):
    """One workflow runs the same verify a developer runs, one job per OS."""
    for rel in files:
        out.kept(_back_up_copy(os.path.join(root, rel), rel))
        _untrack(root, rel)
        os.remove(os.path.join(root, rel))
        out.done(rel)
    out.say('removed %d workflow%s this release replaced'
            % (len(files), _s(files)))
    flow, host = _flow(), _config(root).get('ci') or _host(root)
    rel = '%s/%s' % (WORKFLOW_DIR, flow.workflow_filename(host))
    if not _confirm('Write %s, one job per operating system your specs name?'
                    % rel, args.yes):
        out.say('left %s unwritten; run purlin:init --ci to add it later' % rel)
        return
    tags = flow.env_tags_in_specs(root)
    _write(os.path.join(root, rel),
           flow.render_workflow(host, tags, 'v' + _version()))
    out.done(rel)
    out.say('wrote %s for %s, covering %s'
            % (rel, host, ', '.join(tags) if tags else 'linux'))

def _plugin_source(name):
    source = PLUGIN_SOURCES.get(name, name)
    path = os.path.join(PLUGIN_ROOT, 'scripts', 'proof', source)
    return (source, path) if os.path.isfile(path) else (None, None)

def _detect_plugin_copies(root):
    folder = os.path.join(root, '.purlin', 'plugins')
    hits = []
    for name in sorted(os.listdir(folder) if os.path.isdir(folder) else ()):
        _source, path = _plugin_source(name)
        if path is None:
            continue
        with open(path, 'rb') as new, open(os.path.join(folder, name),
                                           'rb') as old:
            if new.read() != old.read():
                hits.append('.purlin/plugins/%s' % name)
    return hits

def _apply_plugin_copies(root, files, args, out):
    """A copy that predates this release writes proof files nothing reads."""
    for rel in files:
        source, path = _plugin_source(os.path.basename(rel))
        target = os.path.join(root, rel)
        out.kept(_back_up_copy(target, rel))
        shutil.copyfile(path, target)
        out.done(rel)
        out.say('copied scripts/proof/%s over %s' % (source, rel))

def _detect_records(root):
    rel = '%s/README.md' % RECORDS_DIR
    return [] if os.path.isfile(os.path.join(root, rel)) else [rel]

def _apply_records(root, files, args, out):
    _write(os.path.join(root, files[0]), RECORDS_README)
    out.done(files[0])
    out.say('created %s, where verify commits one file per run' % RECORDS_DIR)

# Order matters: the tags are rewritten before the config drops the registry that
# maps them, and before the workflow matrix is rendered from them.
MIGRATIONS = (
    ('os-tags', 'rewrite the retired operating-system tags to @env(<os>)',
     _detect_os_tags, _apply_os_tags),
    ('design-sources', 'point design sources at designs/<feature>/',
     _detect_design_sources, _apply_design_sources),
    ('untracked-files', 'drop the proof files and untrack the dashboard data',
     _detect_untracked, _apply_untracked),
    ('hooks', 'drop the pre-commit hook and repoint the pre-push shim',
     _detect_hooks, _apply_hooks),
    ('config', 'write .purlin/config.json at this shape and set the gate',
     _detect_config, _apply_config),
    ('workflows', 'replace the retired workflows with purlin.yml',
     _detect_workflows, _apply_workflows),
    ('plugin-copies', 'refresh the proof plugin copies under .purlin/plugins/',
     _detect_plugin_copies, _apply_plugin_copies),
    ('records', 'create .purlin/records/ for the records verify commits',
     _detect_records, _apply_records),
)

def pending(project_root):
    """The migrations a project still needs, in the order they are applied."""
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
    print('%s Run: purlin:init --update' % ARROW)

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
    for flag, note in (('--check', 'print what is pending and write nothing'),
                       ('--json', 'print the pending list as JSON'),
                       ('--yes', 'answer yes to every question')):
        parser.add_argument(flag, action='store_true', help=note)
    parser.add_argument('--project-root', default='.')
    args = parser.parse_args(argv)

    root = os.path.abspath(args.project_root)
    if not os.path.isdir(os.path.join(root, '.purlin')):
        print('There is no .purlin/ under %s, so there is nothing to update. '
              'Run purlin:init first.' % root, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    items = pending(root)
    if args.json:
        print(json.dumps({'project_root': root, 'pending': items}, indent=2))
        return EXIT_PENDING if (items and args.check) else EXIT_OK
    if not items:
        print('Nothing is pending: this project is at %s.' % _version())
        return EXIT_OK
    _print_pending(items, root)
    if args.check:
        return EXIT_PENDING
    print('')
    appliers = dict((m[0], m[3]) for m in MIGRATIONS)
    report, applied = _Report(), []
    for item in items:
        if not _confirm('Apply %s, which will %s?'
                        % (item['id'], item['description']), args.yes):
            report.say('skipped %s' % item['id'])
            continue
        appliers[item['id']](root, item['files'], args, report)
        applied.append(item['id'])
    print('')
    for line in report.lines:
        print('  %s' % line)
    sha = _commit(root, applied, report.paths)
    if sha:
        print('  committed %s as %s'
              % (sha, _COMMIT % (_version(), ', '.join(applied))))
    left = [item['id'] for item in pending(root)]
    print('%s Next: run %s' % (ARROW, 'purlin:init --update again for %s.'
          % ', '.join(left) if left else
          'purlin:status to see where every rule stands.'))
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
