#!/usr/bin/env python3
"""Bring a project an older Purlin set up onto this release.

    python3 scripts/init/update.py [--check] [--json] [--yes] [--project-root DIR]

`purlin:init --update` is the command you run; this file is the part of it that
has to be deterministic, so the skill asks and this script edits.

`pending(project_root)` returns the migrations a project still needs: an id, one
line saying what it does, and the files it touches. `--check` prints that list
and exits 1 while anything is pending, and `sync_status` reads the same
function, so the advisory you see and the work this script does cannot disagree.
The detectors read the layout v0.9.5 left, and a project lands straight on this
release's layout: the three gate values and no directory of evidence beside a
spec. Every migration asks before it writes, and every file
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
WINDOWS_TAG_RE = re.compile(r'(?m)[ \t]*@windows[ \t]*$')  # retired
KIND_TAG_RE = re.compile(r'(?m)^(- PROOF-.*?)[ \t]+@(?:unit|integration|e2e)'  # retired
                         r'(?=(?:[ \t]+@env\([a-z]+\))?[ \t]*$)')
WORKFLOW_MARKER = '.proofs-'                               # retired
PRE_PUSH_HOOK = '.git/hooks/pre-push'                      # retired
PRE_PUSH_KEY = 'pre_push'                                  # retired

# --- what this release writes instead --------------------------------------
IGNORE_LINES = ('.purlin/report-data.js',)
EVIDENCE_DIR = '.purlin/evidence'
WORKFLOW_DIR = '.github/workflows'
ARROW = '→'
DROPPED_FRAMEWORK = ('dropped %s from test_framework: nothing in the tree '
                     'runs it')
_COMMIT = 'chore(update): migrate to %s (%s)'

# A renamed plugin copy keeps the name the project gave it: its tests name it.
PLUGIN_SOURCES = {OLD_SHELL_PLUGIN: 'shell_purlin.sh'}

GATE_QUESTION = """
What must be true of every rule before a version is proven?
  passed  every rule has a passing tagged test, from any source
  strong  every rule has a record an audit wrote, at the minimum test strength
  signed  strong, plus a signature from a person on the rule"""

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
            'data and the cache; proofs are runtime now and evidence lives in '
            '%s' % (gone, '' if gone == 1 else 's', EVIDENCE_DIR))

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

    A push is a person's act and a gate is the git host's, so a hook in front
    of either was a convenience that had to be explained and could be
    skipped. What is left is the tag: `purlin:sign` writes `signed/<version>`
    when every rule meets the gate, and a person pushes it.
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
    config = _config(root)
    if not config:
        return []
    gate = _gate()
    stale = ('gate' not in config
             or config.get('version') != _version()
             or config.get('trust') not in gate.TRUST_VALUES
             or any(key in config for key in gate.RETIRED_KEYS))
    return ['.purlin/config.json'] if stale else []

def _gate_default(old):
    """The gate to offer: the one the project named, when it named one.

    A project that named none is offered `strong` when the hook setting
    v0.9.5 wrote was the blocking one, because that project asked for
    something to stop a change, and `passed` otherwise.
    """
    gates = _gate().GATES
    named = str(old.get('gate') or '').strip().lower()
    if named in gates:
        return named
    return 'strong' if str(old.get(PRE_PUSH_KEY)).strip() == 'strict' else 'passed'


TRUST_QUESTION = ('Do you trust your own machine for the tests and the '
                  'signing? [y/n]')


def _ask_trust(default, assume_yes):
    """The trust question, asked again on an update.

    A yes is `local`, which is a project whose own runs count and whose own
    signature is the evidence. A no is `remote`, and `purlin:sign` then
    refuses a rule whose tests have no ci record for the commit being signed.
    """
    gate = _gate()
    default = default if default in gate.TRUST_VALUES else gate.DEFAULT_TRUST
    if assume_yes:
        return default
    try:
        answer = input('%s [%s] ' % (
            TRUST_QUESTION, 'y' if default == 'local' else 'n')).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    if answer.startswith('y'):
        return 'local'
    if answer.startswith('n'):
        return 'remote'
    return default


def _ask_gate(default, assume_yes):
    """The one question init asks, asked once more on an update."""
    if assume_yes:
        return default
    print(GATE_QUESTION)
    try:
        answer = input('Gate [%s]: ' % default).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return default
    return answer if answer in _gate().GATES else default

def _prune_frameworks(root, written):
    """`(the value to write, the names dropped)` for one project tree.

    An older release wrote down every plugin it shipped, so a Python-only tree
    can carry `pytest,jest,shell,vitest` and print a jest runner exiting
    non-zero on every run. A name that detection does not find and the tree
    carries no wiring for is dropped; a name the tree does carry stays even
    when detection would not have picked it. `auto` is left alone: it names
    nothing to drop.
    """
    frameworks = _frameworks()
    raw = str(written or '')
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
    chosen = _ask_gate(_gate_default(old), args.yes)
    resolved = gate.resolve_gate(dict(old, gate=chosen))
    framework, unwired = _prune_frameworks(root, resolved.test_framework)
    config = {
        'version': _version(), 'gate': chosen,
        'ci': old.get('ci') or _host(root),
        'min_strength': resolved.min_strength, 'sql_engine': resolved.sql_engine,
        'mutation_engine': resolved.mutation_engine,
        'test_framework': framework, 'digest': old.get('digest', 'auto'),
        'trust': _ask_trust(resolved.trust, args.yes),
    }
    for name in unwired:
        out.say(DROPPED_FRAMEWORK % name)
    dropped = sorted(key for key in gate.RETIRED_KEYS if key in old)
    _write(path, json.dumps(config, indent=2) + '\n')
    out.done('.purlin/config.json')
    out.say('set the gate to %s%s' % (chosen, '' if not dropped else
            ' and dropped %d key%s this release does not read: %s'
            % (len(dropped), _s(dropped), ', '.join(dropped))))

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
            'purlin:test runs every tagged test' % (len(files), _s(files)))

def _detect_workflows(root):
    """The workflow files this release replaces: any that commit proof files.

    A v0.9.5 project ran its Windows proofs in a workflow that committed the
    proof file back beside the spec. Proof files are runtime now, so that
    workflow is removed and one `purlin.yml` is offered in its place.
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

def _apply_workflows(root, files, args, out):
    """One workflow runs the same audit a developer runs, one job per OS."""
    for rel in files:
        out.kept(_back_up_copy(os.path.join(root, rel), rel))
        _untrack(root, rel)
        os.remove(os.path.join(root, rel))
        out.done(rel)
    out.say('removed %d workflow%s this release replaced'
            % (len(files), _s(files)))
    flow = _flow()
    from purlin import evidence as evidence_module
    tags = flow.env_tags_in_specs(root)
    write_one, reasons = flow.wanted(tags, _config(root).get('trust'),
                                     evidence_module.host_os())
    if not write_one:
        out.say('wrote no workflow: %s' % flow.NO_REASON)
        return
    for reason in reasons:
        out.say(reason)
    # The same prerequisites init checks. A workflow file is no use without
    # the remote that holds it and a host that runs it, so a missing one is
    # named and nothing is written.
    ok, host, lines = flow.prerequisites(root)
    for line in lines:
        out.say(line)
    if not ok:
        out.say('left the workflow unwritten; a prerequisite is missing')
        return
    rel = '%s/%s' % (WORKFLOW_DIR, flow.workflow_filename(host))
    if not _confirm('Write %s, one job per operating system your specs name?'
                    % rel, args.yes):
        out.say('left %s unwritten; run purlin:init again to add it later'
                % rel)
        return
    _write(os.path.join(root, rel),
           flow.render_workflow(host, tags, 'v' + _version()))
    out.done(rel)
    out.say('wrote %s for %s, covering %s'
            % (rel, host, ', '.join(tags) if tags else 'linux'))
    out.say('it runs on a push to a run/* branch and on a push of a signed/* '
            'tag, and ends with the gate check')


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

# Order matters: the tags are rewritten before the workflow matrix is rendered
# from them.
MIGRATIONS = (
    ('os-tags', 'rewrite the retired operating-system tag to @env(windows)',
     _detect_os_tags, _apply_os_tags),
    ('kind-tags', 'drop the kind of test from every proof line',
     _detect_kind_tags, _apply_kind_tags),
    ('untracked-files', 'drop the proof files and untrack the dashboard data',
     _detect_untracked, _apply_untracked),
    ('hooks', 'remove the git hooks an older release installed',
     _detect_hooks, _apply_hooks),
    ('config', 'write .purlin/config.json at this shape and set the gate',
     _detect_config, _apply_config),
    ('workflows', 'remove the retired workflows and write purlin.yml only '
     'where this project has a reason for a runner',
     _detect_workflows, _apply_workflows),
    ('plugin-copies', 'refresh the proof plugin copies under .purlin/plugins/',
     _detect_plugin_copies, _apply_plugin_copies),
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
