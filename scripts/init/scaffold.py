#!/usr/bin/env python3
"""purlin:init: four questions at most, then every file a project needs.

    scaffold.py [--gate passed|strong|signed] [--mutation]
                [--add <language>] [--update] [--dry-run]
                [--project-root DIR] [--plugin-root DIR] [--yes]

Init asks these, in this order, and nothing else:

    What must be true of every rule before a version is proven?
    The command that runs the tests and where its report lands, only where
      nothing in the tree says which framework they use
    Measure test strength by breaking the code on purpose? [y/N], only
      where an engine exists for a detected framework
    Do you trust your own machine for the tests and the signing? [y/n]

Everything else is derived from those answers or read from the tree: the
language from detection, the git host from the remote URL, and the minimum
test strength from the gate when mutation testing is on. `--yes` takes every
default, so mutation testing stays off; `--mutation` turns it on without the
question. `audit_parallel` is written as 4 and is not asked.

It then writes, in this order and naming every one in the summary: the config,
whose `tests` setting holds one entry per detected framework with the report
flag already in its command, the engine's config block where mutation testing
is on, the `.gitignore` entries, `.purlin/evidence/` with its README, the
dashboard, and, where one is wanted, the workflow CI runs. It says in one line
what a framework needs added before it can write its report. Nothing is
written into the project's test suite or its test runner's configuration. It
ends with the next step computed from the state.

A workflow is written for two reasons and no others: a proof in `specs/` is
tagged `@env` for an operating system this machine is not, or you answered no
to the trust question. A project with neither gets no workflow and no runner:
`purlin:sign` writes the tag, you push it, and nothing runs remotely. Where
one is wanted the prerequisites are checked first, and a missing one is named
with the command that fixes it; nothing is written then.

Both ways of loading Purlin work, and neither is written into a project: this
checkout under `--plugin-dir`, and the marketplace copy under the plugin cache.

Exit codes: 0 the project is set up, 1 nothing could be done, 2 the invocation
was wrong or the directory is not a git repository.
"""

import argparse
import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _path in (os.path.join(PLUGIN_ROOT, 'scripts', 'mcp'),
              os.path.join(PLUGIN_ROOT, 'scripts', 'run'),
              os.path.join(PLUGIN_ROOT, 'scripts', 'review')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import workflow as workflow_module                            # noqa: E402
from mutation import ENGINE_BY_FRAMEWORK, mutmut              # noqa: E402
from purlin import (console as console_module,                # noqa: E402
                    frameworks as frameworks_module,
                    evidence as evidence_module,
                    gate as gate_module,
                    specs as specs_module, status as status_module)

EXIT_OK = 0
EXIT_BAD_INVOCATION = 2

ARROW = '→'
NOT_A_REPOSITORY = 'This is not a git repository. Run git init, then init.'

GATE_QUESTION = 'What must be true of every rule before a version is proven?'
GATE_CHOICES = (
    "passed  every rule's tagged tests pass",
    'strong  tests pass and the audit finds them sound',
    'signed  strong, and a person signs each rule',
)
# What init asks where it detects no framework: the two things a run needs.
COMMAND_QUESTION = ('There is nothing here to detect a test framework from. '
                    'What command runs the tests?')
REPORT_QUESTION = ('Where does that command write its report? A JUnit XML '
                   'file, a .trx file or folder, - for a go test -json '
                   'stream on standard output, or nothing when each test '
                   'file passes by exiting 0.')
NO_COMMAND = ('No test command was given, so no suite is written. Add one '
              'under "tests" in .purlin/config.json.')
# The globs a suite init could not detect reads its test files from.
ASKED_FILES = ['**/test_*', '**/*_test.*', '**/*.test.*', '**/*.spec.*']

# The one question that is not derived from the gate. A project that trusts
# this machine runs its tests and writes its signatures here; one that does
# not has purlin:sign refuse a rule whose tests have no ci record for the
# commit being signed.
TRUST_QUESTION = ('Do you trust your own machine for the tests and the '
                  'signing? [y/n]')
TRUST_LOCAL = ('Trust local: your own runs count, and purlin:sign signs what '
               'you ran.')
TRUST_REMOTE = ('Trust remote: purlin:sign refuses a rule whose tests have no '
                'ci record for this commit, so purlin:test --remote runs '
                'first.')

REMOTE_INTRO = 'A remote runner is written for two reasons:'
REMOTE_NO_REMOTE = ('there is no git remote, so there is no runner to read '
                    'it')

MUTANTS_IGNORE = ('# The copy mutmut breaks, rebuilt on every run, never committed\n'
                  'mutants/\n')

_STRYKER_NOTE = ('%s: Stryker measures the breaks. Without it the test '
                 'strength reads n/a.')

_TRUST_WORDS = {'local': TRUST_LOCAL, 'remote': TRUST_REMOTE}

# Mutation testing is optional and off by default. The question is asked only
# where an engine exists for a framework the tree carries; a yes writes
# `mutation_engine: auto` and the gate's minimum strength, a no writes `none`.
MUTATION_QUESTION = ('Measure test strength by breaking the code on purpose? '
                     'It needs %s and takes minutes to hours per run. [y/N]')
NO_ENGINE = ('Mutation testing is off: no engine breaks %s code, so the AI '
             'audit alone judges test strength.')
ENGINE_NAMES = {'mutmut': 'mutmut', 'stryker': 'Stryker',
                'stryker_net': 'Stryker.NET'}

# How many AI audit calls run at once. Written into every new project and
# never asked; a project changes it in the settings file.
AUDIT_PARALLEL = 4
AUDIT_PARALLEL_RANGE = (1, 16)

EVIDENCE_DIR = '.purlin/evidence'
EVIDENCE_README = os.path.join('templates', 'evidence-readme.md')

# --- Reading the tree ------------------------------------------------------

def _read(*parts):
    try:
        with open(os.path.join(*parts), 'r', encoding='utf-8') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return ''


def _read_bytes(*parts):
    """The file as it is on disk, with nothing translated on the way in."""
    try:
        with open(os.path.join(*parts), 'rb') as handle:
            return handle.read()
    except (IOError, OSError):
        return b''


def _git(root, *args):
    """`(ok, stripped stdout)` for one git command run in `root`."""
    try:
        done = subprocess.run(['git'] + list(args), cwd=root,
                              capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return False, ''
    return done.returncode == 0, done.stdout.strip()


def git_remote(root):
    """True when the project has a git remote for a runner to read."""
    ok, listed = _git(root, 'remote')
    return bool(ok and listed.strip())


def git_host(root):
    """`github`, `azure` or None, read from the remote URL."""
    ok, url = _git(root, 'remote', 'get-url', 'origin')
    lowered = url.lower() if ok else ''
    if 'github' in lowered:
        return 'github'
    if 'dev.azure.com' in lowered or 'visualstudio.com' in lowered:
        return 'azure'
    return None


def is_repository(root):
    """True when `root` is inside a git checkout.

    Everything init writes lands in the tree, so this is the one thing git
    has to answer before it writes any of it.
    """
    ok, top = _git(root, 'rev-parse', '--show-toplevel')
    return bool(ok and top)


def _is_test_file(name):
    return name.endswith('.py') and (name.startswith('test_')
                                     or name.endswith('_test.py'))


def _holds_python(path):
    """True when a `.py` file sits anywhere under `path`."""
    for current, subdirs, files in os.walk(path):
        subdirs[:] = [d for d in subdirs if not d.startswith('.')
                      and d not in ('__pycache__', 'node_modules')]
        if any(f.endswith('.py') for f in files):
            return True
    return False


def mutmut_paths(root):
    """`(source paths, test selection)` for the engine's config block.

    A directory holding a test file at its top level, one with `test_*.py`
    files directly in it, is where the tests are. Any other directory holding
    a `.py` file at any depth, one whose code sits a level down, is source. `src`, `lib` and `app` win as source, and `tests` and
    `test` win as the selection, whenever they are there.

    A project whose code is modules at the root is named module by module,
    never as `.`: mutmut copies every source path into `mutants/`, and `.`
    would copy `.git` and `mutants/` itself along with the code.
    """
    names = sorted(os.listdir(root))
    dirs = [n for n in names if not n.startswith('.')
            and os.path.isdir(os.path.join(root, n))]
    test_dirs = [n for n in dirs if any(
        _is_test_file(f) for f in os.listdir(os.path.join(root, n)))]
    sources = [n for n in ('src', 'lib', 'app') if n in dirs] or [
        n for n in dirs if n not in ('tests', 'test', 'specs', 'mutants')
        and n not in test_dirs and _holds_python(os.path.join(root, n))]
    if not sources:
        sources = [n for n in names if n.endswith('.py')
                   and os.path.isfile(os.path.join(root, n))
                   and not _is_test_file(n) and n not in ('conftest.py',
                                                          'setup.py')]
    tests = [n for n in ('tests', 'test') if n in dirs] or test_dirs
    return sources or ['.'], tests or ['.']


# --- Asking, and writing ---------------------------------------------------

class Console(object):
    """The questions init asks, and how it behaves when nobody is there."""

    def __init__(self, yes):
        # `--yes` is the only thing that silences a question. Reading stdin
        # rather than testing for a terminal lets a script pipe its answers
        # in, and end of input is the default, so a run with nothing on stdin
        # takes every default rather than hanging.
        self.interactive = not yes

    def ask(self, question, default, choices=()):
        print(question)
        for line in choices:
            print('  ' + line)
        if not self.interactive:
            print('[%s]: %s' % (default, default))
            return default
        try:
            answer = input('[%s]: ' % default).strip()
        except EOFError:
            answer = ''
        return answer or default

    def confirm(self, question, gated):
        if not gated or not self.interactive:
            return True
        try:
            return input('%s [Y/n]: ' % question).strip().lower() in (
                '', 'y', 'yes')
        except EOFError:
            return True


class Plan(object):
    """Every write, as one line, in the order the summary prints it."""

    def __init__(self, root, dry_run, console, gated):
        self.root = root
        self.dry_run = dry_run
        self.console = console
        self.gated = gated
        self.lines = []

    def note(self, text):
        self.lines.append(text)

    def skip(self, what, why):
        self.lines.append('skipped %s (%s)' % (what, why))

    def directory(self, rel):
        path = os.path.join(self.root, rel)
        if os.path.isdir(path):
            return self.note('kept %s/' % rel)
        if self.allowed(rel, 'create %s/' % rel):
            if not self.dry_run:
                os.makedirs(path, exist_ok=True)
            self.note('wrote %s/' % rel)

    def write(self, rel, text, own=False, perm=None, source=None,
              exact=False):
        """One file. `own` means Purlin owns the bytes and refreshes a stale one.

        `exact` hands over bytes rather than text and writes them as they
        came. Text mode on Windows turns every line ending into two bytes on
        the way out, so a file copied through it would stop being the file it
        was copied from.
        """
        path = os.path.join(self.root, rel)
        if os.path.lexists(path):
            current = _read_bytes(path) if exact else _read(path)
            if not own or current == text:
                return self.note('kept %s' % rel)
        if not self.allowed(rel, 'write %s' % rel):
            return
        if not self.dry_run:
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            if exact:
                with open(path, 'wb') as handle:
                    handle.write(text)
            else:
                with open(path, 'w', encoding='utf-8') as handle:
                    handle.write(text)
            if perm is not None:
                os.chmod(path, perm)
        self.note('copied %s -> %s' % (source, rel) if source
                  else 'wrote %s' % rel)

    def copy(self, source, rel):
        """A file the plugin ships, copied into the project unchanged."""
        if not os.path.isfile(source):
            return self.skip(rel, 'the plugin carries no %s'
                             % os.path.basename(source))
        self.write(rel, _read_bytes(source), exact=True,
                   source=os.path.relpath(
                       source, PLUGIN_ROOT).replace(os.sep, '/'))

    def append(self, rel, block, marker):
        """A block into a file the project also owns, once and never twice."""
        current = _read(self.root, rel)
        if marker in current:
            return self.note('kept %s' % rel)
        if current:
            current = current.rstrip('\n') + '\n\n'
        self.write(rel, current + block, own=True)

    def allowed(self, rel, question):
        if self.console.confirm(question, self.gated):
            return True
        self.skip(rel, 'declined')
        return False


# --- The steps -------------------------------------------------------------

def audit_parallel(existing):
    """The number of audit calls at once: the project's own, or 4."""
    value = (existing or {}).get('audit_parallel')
    low, high = AUDIT_PARALLEL_RANGE
    if isinstance(value, int) and not isinstance(value, bool) \
            and low <= value <= high:
        return value
    return AUDIT_PARALLEL


def min_strength_for(gate, mutation):
    """The minimum score: the gate's where mutation testing is on, else null."""
    if mutation == 'none':
        return None
    return gate_module.resolve_gate({'gate': gate}).min_strength


def write_config(plan, plugin_root, existing, gate, host, tests,
                 trust=None, mutation='none'):
    """`.purlin/config.json`: the template, the answers, and what they derive.

    `tests` is the `tests` setting, one entry per suite.
    """
    config = json.loads(_read(plugin_root, 'templates', 'config.json'))
    config.update(existing or {})
    config.update({'version': _read(plugin_root, 'VERSION').strip(),
                   'gate': gate, 'mutation_engine': mutation,
                   'min_strength': min_strength_for(gate, mutation),
                   'audit_parallel': audit_parallel(existing),
                   'trust': trust or gate_module.DEFAULT_TRUST})
    if host:
        config['ci'] = host
    config['tests'] = tests
    for key in gate_module.RETIRED_KEYS:
        config.pop(key, None)
    plan.write('.purlin/config.json', json.dumps(config, indent=2) + '\n',
               own=True)
    return config


def print_needs(plan, selected):
    """One line per framework that needs something added to write its report."""
    for framework in selected:
        needs = frameworks_module.NEEDS.get(framework)
        if needs:
            plan.note(needs)


def write_engine(plan, root, selected):
    """The engine that breaks the code, wired like the other config files."""
    if 'pytest' in selected:
        rel, style, section = mutmut.config_target(root)
        sources, tests = mutmut_paths(root)
        plan.append(rel, mutmut.mutmut_config_block(sources, tests, style),
                    section)
        # mutmut leaves its working copy in `mutants/`. Committed, it carries
        # a copy of every test and every record into the next commit.
        plan.append('.gitignore', MUTANTS_IGNORE, 'mutants/')
    for name in [f for f in ('jest', 'vitest', 'dotnet') if f in selected]:
        plan.note(_STRYKER_NOTE % name)


def write_evidence(plan, plugin_root):
    """`.purlin/evidence/` and the README that says what the folder holds."""
    plan.directory(EVIDENCE_DIR)
    plan.write(EVIDENCE_DIR + '/README.md', _read(plugin_root, EVIDENCE_README))


def engine_for(selected):
    """The engine that breaks the code of the first framework that has one."""
    for framework in selected:
        engine = ENGINE_BY_FRAMEWORK.get(framework, 'none')
        if engine != 'none':
            return engine
    return None


def resolve_mutation(console, existing, selected, turn_on):
    """`(mutation_engine, the line to print or None)`.

    A value the project already wrote is kept and nothing is asked. With no
    engine for any framework the tree carries, nothing is asked either:
    mutation testing stays off and one line says why. Otherwise `--mutation`
    turns it on and the question decides, defaulting to no.
    """
    engine = engine_for(selected)
    if engine is None:
        return 'none', NO_ENGINE % ', '.join(selected)
    written = str((existing or {}).get('mutation_engine') or '').strip()
    if written and not turn_on:
        return written, None
    if turn_on:
        return 'auto', None
    answer = str(console.ask(MUTATION_QUESTION % ENGINE_NAMES.get(engine, engine),
                             'n') or '').strip().lower()
    return ('auto' if answer.startswith('y') else 'none'), None


def write_gitignore(plan, plugin_root):
    """templates/gitignore.purlin, appended once and guarded by its first entry."""
    plan.append('.gitignore',
                _read(plugin_root, 'templates', 'gitignore.purlin'),
                '.purlin/runtime/')


def ask_trust(console, existing):
    """`local` or `remote`: whether this machine's own runs count for signing.

    The default is `local`, which is a yes: your own tests and your own
    signature are the evidence. A no writes `remote`, and `purlin:sign` then
    refuses a rule whose tests have no ci record for the commit being signed.
    """
    named = str((existing or {}).get('trust') or '').strip().lower()
    if named in gate_module.TRUST_VALUES:
        return named
    answer = str(console.ask(TRUST_QUESTION, 'y') or '').strip().lower()
    return 'local' if answer.startswith('y') else 'remote'


def print_remote_reasons(reasons):
    """Why this project gets a remote runner, or the line saying it needs none."""
    print('')
    if not reasons:
        print('No remote runner: %s.' % workflow_module.NO_REASON)
        return
    print(REMOTE_INTRO)
    for reason in reasons:
        print('  %s' % reason)


def write_workflow(plan, root, purlin_ref):
    """The workflow the git host runs, with the matrix the `@env` tags name.

    The prerequisites are checked first and nothing is written when one is
    missing: a workflow file is no use without the remote that holds it and
    a host that runs it. The triggers name no branch of the project's own.
    """
    ok, host, lines = workflow_module.prerequisites(root)
    for line in lines:
        plan.note(line)
    if not ok:
        return plan.skip('the CI workflow', 'a prerequisite is missing')
    env_tags = workflow_module.env_tags_in_specs(root)
    name = workflow_module.workflow_filename(host)
    rel = name if host == 'azure' else '.github/workflows/%s' % name
    plan.write(rel, workflow_module.render_workflow(
        host, env_tags, purlin_ref), own=True)
    plan.note('  the matrix is %s: ubuntu-latest always, then the @env tags '
              'in specs/.'
              % ', '.join(workflow_module.runners_for(env_tags)))
    plan.note('  it runs on a push to a run/* branch and on a push of a '
              'signed/* tag, and ends with the gate check.')
    return host


def next_step(root):
    """The next step, computed from the state the project is now in."""
    first = '%s Next: run purlin:spec to write the first spec.' % ARROW
    try:
        report = status_module.sync_status(root)
    except Exception:                                          # noqa: BLE001
        return [first]
    lines = [] if report == status_module.NO_SPECS else [
        line for line in report.splitlines() if line.startswith(ARROW)]
    return lines or [first]


# --- Invocation ------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='scaffold.py', description='Set a project up for Purlin')
    parser.add_argument('--gate', choices=gate_module.GATES, default=None)
    parser.add_argument('--add', default=None, help='one more framework')
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--plugin-root', default=None)
    for flag in ('--update', '--dry-run', '--yes', '--mutation'):
        parser.add_argument(flag, action='store_true')
    return parser.parse_args(argv)


def delegate_update(args):
    """`--update` belongs to scripts/init/update.py, which owns the upgrade."""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import update                                              # noqa: PLC0415
    # `--dry-run` is what the upgrade calls `--check`: say what is pending and
    # write nothing. No other flag of this script means anything to it.
    return update.main(['--project-root', args.project_root]
                       + (['--yes'] if args.yes else [])
                       + (['--check'] if args.dry_run else []))


def format_for(report):
    """The report format a report path names: `.trx` or a folder is TRX, `-`
    a Go JSON stream, nothing at all an exit code, and anything else JUnit."""
    report = (report or '').strip()
    if not report:
        return 'exit'
    if report == '-':
        return 'gotest'
    if report.lower().endswith('.trx') or report.endswith('/'):
        return 'trx'
    return 'junit'


def asked_suite(console):
    """The one suite a tree init could not detect is asked for, or None."""
    command = str(console.ask(COMMAND_QUESTION, '') or '').strip()
    if not command:
        print(NO_COMMAND)
        return None
    report = str(console.ask(REPORT_QUESTION, '') or '').strip()
    fmt = format_for(report)
    run = command
    if fmt == 'exit' and '{files}' not in run:
        run += ' {files}'
    return {'name': 'tests', 'run': run,
            'report': report.rstrip('/') or None, 'format': fmt,
            'files': list(ASKED_FILES)}


def resolve_tests(root, console, existing, add):
    """`(the frameworks named, the tests setting to write)`.

    A `tests` setting the project already carries is kept as it is. Otherwise
    detection answers on a project with code, and nothing is asked; a tree
    with nothing to detect is asked for its command and its report, which is
    the second exception. `--add` appends the entry of one more framework,
    once however many times it is added.
    """
    written = (existing or {}).get('tests')
    tests = [dict(entry) for entry in written] if isinstance(
        written, list) else None
    if tests is None:
        detected = frameworks_module.detect_frameworks(root)
        if detected:
            tests = frameworks_module.entries_for(detected)
        else:
            asked = asked_suite(console)
            tests = [asked] if asked else []
    names = [entry.get('name') for entry in tests if isinstance(entry, dict)]
    for part in str(add or '').split(','):
        name = part.strip()
        if not name:
            continue
        if name not in frameworks_module.ENTRIES:
            print('purlin: "%s" is not a framework init writes a command for; '
                  'add it under "tests" in .purlin/config.json.' % name)
            continue
        if name not in names:
            tests.append(frameworks_module.entry_for(name))
            names.append(name)
    return [name for name in names if name], tests


def _existing_config(root):
    """The project's own `.purlin/config.json`, or None when it has none."""
    try:
        value = json.loads(_read(root, '.purlin', 'config.json'))
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def signing_setup():
    """The one-time commit-signing setup, from the module that owns signing."""
    import sign as sign_module                                 # noqa: PLC0415
    return sign_module.SIGNING_SETUP


def print_signed(root):
    """What `signed` needs beyond the config: signed commits."""
    print('')
    print('Each signer runs this once, then uploads the public key to the git '
          'host:')
    for command in signing_setup():
        print('  %s' % command)


def main(argv=None):
    console_module.force_utf8_stdio()
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.update:
        return delegate_update(args)

    root = os.path.abspath(args.project_root)
    plugin_root = os.path.abspath(args.plugin_root or PLUGIN_ROOT)
    if not os.path.isdir(root):
        print('no such project root: %s' % root, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    if not os.path.isfile(os.path.join(plugin_root, 'templates',
                                       'config.json')):
        print('not a Purlin plugin root: %s' % plugin_root, file=sys.stderr)
        return EXIT_BAD_INVOCATION

    in_git = is_repository(root)
    if not in_git and not args.dry_run:
        print(NOT_A_REPOSITORY, file=sys.stderr)
        return EXIT_BAD_INVOCATION

    existing = _existing_config(root)
    console = Console(args.yes)
    # A first run's one question is its consent. A later run asks before each
    # write, because it changes something a person already answered.
    plan = Plan(root, args.dry_run, console, gated=existing is not None)

    gate = args.gate or (existing or {}).get('gate')
    if gate not in gate_module.GATES:
        gate = console.ask(GATE_QUESTION, gate_module.DEFAULT_GATE,
                           GATE_CHOICES)
        if gate not in gate_module.GATES:
            print('purlin: "%s" is not a gate; reading it as %s.'
                  % (gate, gate_module.DEFAULT_GATE))
            gate = gate_module.DEFAULT_GATE

    selected, tests = resolve_tests(root, console, existing, args.add)
    mutation, no_engine = resolve_mutation(console, existing, selected,
                                           args.mutation)
    trust = ask_trust(console, existing)
    host = git_host(root)

    if not in_git:
        plan.note(NOT_A_REPOSITORY)
    plan.note('Gate %s. Suites %s. Git host %s.'
              % (gate, ', '.join(selected) or 'none',
                 host or 'not read from a remote'))
    if no_engine:
        plan.note(no_engine)
    plan.note(_TRUST_WORDS[trust])
    for name in ('.purlin', 'specs', 'specs/_anchors'):
        plan.directory(name)

    config = write_config(plan, plugin_root, existing, gate, host, tests,
                          trust, mutation)
    print_needs(plan, selected)
    if mutation != 'none':
        write_engine(plan, root, selected)
    write_gitignore(plan, plugin_root)
    write_evidence(plan, plugin_root)
    plan.copy(os.path.join(plugin_root, 'scripts', 'report',
                           'purlin-report.html'), 'purlin-report.html')
    # A workflow is written for two reasons and no others: a proof this
    # machine cannot prove, and a project that does not trust this machine
    # for signing. A project with neither runs nothing remotely.
    tags = workflow_module.env_tags_in_specs(root)
    wanted, reasons = workflow_module.wanted(
        tags, trust, evidence_module.host_os())
    print_remote_reasons(reasons)
    if wanted and not git_remote(root):
        wanted = False
        plan.skip('the CI workflow', REMOTE_NO_REMOTE)
    elif not wanted:
        plan.skip('the CI workflow', workflow_module.NO_REASON)
    if wanted:
        write_workflow(plan, root, 'v%s' % config.get('version', ''))

    for line in plan.lines:
        print(line)
    if gate == 'signed':
        print_signed(root)

    print('')
    for line in next_step(root):
        print(line)
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
