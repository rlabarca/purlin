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
WINDOWS_TAG_RE = re.compile(r'(?m)[ \t]*@windows[ \t]*$')  # retired
KIND_TAG_RE = re.compile(r'(?m)^(- PROOF-.*?)[ \t]+@(?:unit|integration|e2e)'  # retired
                         r'(?=(?:[ \t]+@env\([a-z]+\))?[ \t]*$)')
WORKFLOW_MARKER = '.proofs-'                               # retired
PRE_PUSH_HOOK = '.git/hooks/pre-push'                      # retired
PRE_PUSH_KEY = 'pre_push'                                  # retired
DESIGN_FIELD_RE = re.compile(r'^>\s*(Visual-Reference|Visual-Hash):')  # retired
FIGMA_SOURCE_RE = re.compile(r'^>\s*Source:.*figma', re.I)  # retired
PINNED_RE = re.compile(r'^>\s*Pinned:')                    # retired
# The markers v0.9.5's proof plugins read, one per framework, and the files
# its init copied and wired. The upgrade rewrites the first and removes the
# second; nothing else in this release reads either.
PYTEST_MARK_RE = re.compile(r'^([ \t]*)@pytest\.mark\.proof\(')  # retired
PYTEST_ARGS_RE = re.compile(r"""\(\s*["'](\w+)["']\s*,\s*["'](PROOF-\d+)["']""")
PYTESTMARK_RE = re.compile(r'pytest\.mark\.proof\(')            # retired
TITLE_TAG_RE = re.compile(r' ?\[proof:(\w+):(PROOF-\d+):RULE-\d+(?::\w+)?\]')  # retired
TRAIT_RE = re.compile(r'(\[\s*)?,?\s*Trait\s*\(\s*"PurlinProof"\s*,\s*'  # retired
                      r'"(\w+):(PROOF-\d+):RULE-\d+(?::\w+)?"\s*\)(\s*\])?')
SHELL_CALL_RE = re.compile(r'^([ \t]*)purlin_proof\s+["\']?(\w+)["\']?\s+'  # retired
                           r'["\']?(PROOF-\d+)["\']?.*$')
SHELL_HARNESS_RE = re.compile(r'^([ \t]*)(?:source|\.)\s+\S*(?:purlin-proof|'  # retired
                              r'shell_purlin)\.sh\S*\s*$')
SHELL_FINISH_RE = re.compile(r'^([ \t]*)purlin_proof_finish\b.*$')  # retired
SQL_MARK_RE = re.compile(r'^--[ \t]*@purlin[ \t]+(\w+)[ \t]+(PROOF-\d+)'  # retired
                         r'[ \t]+RULE-\d+(?:[ \t]+\w+)?[ \t]*$')
PLUGIN_DIR = '.purlin/plugins'                             # retired
CONFTEST_PLUGIN_RE = re.compile(                           # retired
    r"""["']\.purlin\.plugins\.pytest_purlin["']\s*,?\s*""")
REPORTER_RE = re.compile(                                  # retired
    r"""\s*,?\s*["'][^"']*(?:jest|vitest)_purlin\.[jt]s["']""")
XUNIT_LOGGER = 'xunit_purlin'                              # retired
# The files v0.9.5's init copied into the plugin folder, under the names it
# gave them. A file of any other name there is the project's own and stays.
PLUGIN_COPIES = ('pytest_purlin.py', 'jest_purlin.js',          # retired
                 'vitest_purlin.ts', 'purlin-proof.sh',          # retired
                 'shell_purlin.sh', 'sql_purlin.sh',             # retired
                 'xunit_purlin.cs', 'c_purlin.h',                # retired
                 'c_purlin_emit.py', 'phpunit_purlin.php', '.keep')  # retired

# The old framework names and the suite each becomes.
OLD_FRAMEWORKS = {'pytest': 'pytest', 'jest': 'jest', 'vitest': 'vitest',
                  'xunit': 'dotnet', 'sql': 'sql', 'shell': 'shell'}

# --- what this release writes instead --------------------------------------
IGNORE_LINES = ('.purlin/report-data.js',)
EVIDENCE_DIR = '.purlin/evidence'
EVIDENCE_README = EVIDENCE_DIR + '/README.md'
META_RE = re.compile(r'^>\s*[A-Z][A-Za-z-]+:')
SCOPE_RE = re.compile(r'^>\s*Scope:', re.M)
SCOPE_ADVICE = ('%d spec%s no > Scope: line: %s. Run purlin:spec <name> to '
                'add one. The line is optional below the gate signed and '
                'required at signed.')
WORKFLOW_DIR = '.github/workflows'
ARROW = '→'
DROPPED_FRAMEWORK = 'dropped %s from the tests: nothing in the tree runs it'
TEST_EXTENSIONS = ('.py', '.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx', '.cs',
                   '.sh', '.bash', '.sql')
SKIP_DIRS = ('node_modules', 'bin', 'obj', 'mutants')
_COMMIT = 'chore(update): migrate to %s (%s)'

GATE_QUESTION = """
What must be true of every rule before a version is proven?
  passed  every rule's tests pass
  strong  tests pass and the audit finds them sound
  signed  strong, and a person signs each rule"""

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

def _init():
    """scaffold.py, the one home of the questions init asks and what they write."""
    return _plugin_module('init', 'scaffold')

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
             or 'tests' not in config
             or 'mutation_engine' not in config
             or 'audit_parallel' not in config
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
    refuses a rule whose tests have no run from the remote runner for the
    commit being signed.
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


def _ask_mutation(root, framework, assume_yes, out):
    # `framework` is the list of suite names the update writes.
    """`none` or `auto`: the mutation question init asks, asked on an update.

    Released 0.9.5 had no such setting, so the question is new to a project
    it set up. It is asked only where an engine exists for a framework the
    project carries, and the default is no.
    """
    init = _init()
    named = list(framework)
    engine = init.engine_for(named)
    if engine is None:
        out.say(init.NO_ENGINE % (', '.join(named) or "this project's"))
        return 'none'
    if assume_yes:
        return 'none'
    try:
        answer = input('%s ' % (init.MUTATION_QUESTION
                                % init.ENGINE_NAMES.get(engine, engine)))
    except (EOFError, KeyboardInterrupt):
        return 'none'
    if not answer.strip().lower().startswith('y'):
        return 'none'
    out.say('turned mutation testing on; run purlin:init to wire %s into '
            'the project' % init.ENGINE_NAMES.get(engine, engine))
    return 'auto'

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
    raw = str(old.get('test_framework') or '')                    # retired
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
    gate = _gate()
    old = _config(root)
    path = os.path.join(root, '.purlin', 'config.json')
    out.kept(_back_up_copy(path, '.purlin/config.json'))
    chosen = _ask_gate(_gate_default(old), args.yes)
    resolved = gate.resolve_gate(dict(old, gate=chosen))
    tests, unwired = _tests_setting(root, old)
    for name in unwired:
        out.say(DROPPED_FRAMEWORK % name)
    init = _init()
    names = [entry.get('name') for entry in tests if isinstance(entry, dict)]
    mutation = (old['mutation_engine'] if 'mutation_engine' in old
                else _ask_mutation(root, names, args.yes, out))
    config = {
        'version': _version(), 'gate': chosen, 'mutation_engine': mutation,
        'min_strength': init.min_strength_for(chosen, mutation),
        'audit_parallel': init.audit_parallel(old),
        'tests': tests,
        'ci': old.get('ci') or _host(root),
        'trust': _ask_trust(resolved.trust, args.yes),
    }
    # Every key the old file carried that this one does not: the retired
    # ones, and the ones 0.9.5 wrote that nothing here reads. The framework
    # list is not dropped: it became the tests setting, which says so.
    dropped = sorted(key for key in old if key not in config
                     and key != 'test_framework')
    _write(path, json.dumps(config, indent=2) + '\n')
    out.done('.purlin/config.json')
    out.say('set the gate to %s%s' % (chosen, '' if not dropped else
            ' and dropped %d key%s this release does not read: %s'
            % (len(dropped), _s(dropped), ', '.join(dropped))))
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


def _detect_evidence(root):
    """A project with no README in its evidence folder: 0.9.5 had no folder."""
    return ([] if os.path.isfile(os.path.join(root, EVIDENCE_README))
            else [EVIDENCE_README])

def _apply_evidence(root, files, args, out):
    """The folder every run writes into, and one README saying what it holds."""
    _write(os.path.join(root, EVIDENCE_README),
           _read(os.path.join(PLUGIN_ROOT, _init().EVIDENCE_README)))
    out.done(EVIDENCE_README)
    out.say('wrote %s: each feature\'s evidence lands beside it, under '
            'local/ and ci/' % EVIDENCE_README)


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
            args = PYTEST_ARGS_RE.search('\n'.join(
                lines[index:(end if end is not None else index) + 1]))
            if end is not None and args:
                out.append(_comment(ext, found.group(1), args.group(1),
                                    args.group(2)))
                count += 1
                index = end + 1
                continue
        if PYTESTMARK_RE.search(line) and not found:
            left.append(index + 1)
        elif found:
            left.append(index + 1)
        out.append(line)
        index += 1
    return out, count, left


_CALL_START_RE = re.compile(r'(?<![\w$.])(?:it|test)(?:\s*\.\s*\w+)*\s*\(')


def _rewrite_js(lines, ext):
    out = list(lines)
    inserts = []
    count = 0
    for index, line in enumerate(lines):
        tags = list(TITLE_TAG_RE.finditer(line))
        if not tags:
            continue
        out[index] = TITLE_TAG_RE.sub('', line)
        # The call the title belongs to starts on this line or just above it.
        owner = index
        for back in range(index, max(-1, index - 3), -1):
            if _CALL_START_RE.search(lines[back]):
                owner = back
                break
        indent = re.match(r'[ \t]*', lines[owner]).group(0)
        for tag in tags:
            inserts.append((owner, _comment(ext, indent, tag.group(1),
                                            tag.group(2))))
            count += 1
    # From the bottom up, so each index still points at its line, and the
    # tags of one call in the order the title held them.
    by_owner = {}
    for owner, comment in inserts:
        by_owner.setdefault(owner, []).append(comment)
    for owner in sorted(by_owner, reverse=True):
        out[owner:owner] = by_owner[owner]
    return out, count, []


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

    `lines left` are the line numbers of a marker the upgrade could not
    place above one test, such as a module-wide `pytestmark`, which it names
    and leaves as it was.
    """
    rewrite = _REWRITERS.get(ext, _rewrite_js)
    ending = '\n' if text.endswith('\n') else ''
    lines = text.split('\n')
    if ending:
        lines = lines[:-1]
    out, count, left = rewrite(lines, ext)
    return '\n'.join(out) + ending, count, left


def _marked_old(root):
    """`{path: (new text, count, lines left)}` for each file with an old marker."""
    found = {}
    for rel in _test_files(root):
        try:
            text = _read(os.path.join(root, rel))
        except (IOError, OSError, UnicodeDecodeError):
            continue
        if not any(token in text for token in ('pytest.mark.proof',  # retired
                                               '[proof:',            # retired
                                               'PurlinProof',        # retired
                                               'purlin_proof',       # retired
                                               '@purlin')):          # retired
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
    for rel, (_new, _count, left) in sorted(found.items()):
        for number in left:
            out.say('left %s:%d as it was: write the marker as a comment '
                    'above each test by hand' % (rel, number))


def _wiring(root):
    """`[(path, new text or None)]`: the wiring v0.9.5's init wrote, undone.

    None means the file held nothing else and goes. A `.csproj` compiling the
    xUnit logger is not rewritten: it is reported, with what to remove.
    """
    edits = []
    for rel in ('conftest.py',):
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        text = _read(path)
        if not CONFTEST_PLUGIN_RE.search(text):
            continue
        new = CONFTEST_PLUGIN_RE.sub('', text)
        new = re.sub(r'(?m)^[ \t]*pytest_plugins\s*=\s*\[\s*\][ \t]*\n?', '',
                     new)
        edits.append((rel, new if new.strip() else None))
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
    return _plugin_copies(root) + [rel for rel, _new in _wiring(root)]


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


# Order matters: the tags are rewritten before the workflow matrix is rendered
# from them.
MIGRATIONS = (
    ('design-refs', 'remove the Figma source and the picture fingerprint '
     'from each spec that carries them',
     _detect_design_refs, _apply_design_refs),
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
    ('evidence', 'create .purlin/evidence/ with the README that says what '
     'it holds', _detect_evidence, _apply_evidence),
    ('workflows', 'remove the retired workflows and write purlin.yml only '
     'where this project has a reason for a runner',
     _detect_workflows, _apply_workflows),
    ('markers', 'rewrite each 0.9.5 marker as a comment above its test',
     _detect_markers, _apply_markers),
    ('plugins', 'remove the proof plugin copies and the wiring that loaded '
     'them', _detect_plugins, _apply_plugins),
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

def scope_advice(project_root):
    """The line naming every feature spec with no `> Scope:` line, or None.

    Advice, not a migration: nothing is changed, and nothing stays pending.
    Anchors are exempt, because their code is the requiring feature's.
    """
    root = os.path.abspath(project_root)
    names = [os.path.basename(rel)[:-len('.md')]
             for rel in _files_under(root, 'specs', ('*.md',))
             if not rel.startswith('specs/_anchors/')
             and not SCOPE_RE.search(_read(os.path.join(root, rel)))]
    if not names:
        return None
    return SCOPE_ADVICE % (len(names), ' has' if len(names) == 1 else 's have',
                           ', '.join(names))

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
    advice = scope_advice(root)
    if not items:
        print('Nothing is pending: this project is at %s.' % _version())
        if advice:
            print(advice)
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
    if advice:
        print('  %s' % advice)
    left = [item['id'] for item in pending(root)]
    print('%s Next: run %s' % (ARROW, 'purlin:init --update again for %s.'
          % ', '.join(left) if left else
          'purlin:status to see where every rule stands.'))
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
