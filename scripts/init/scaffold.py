#!/usr/bin/env python3
"""purlin:init: two questions at most, then every file a project needs.

    scaffold.py [--gate passed|strong|signed] [--mutation] [--update]
                [--project-root DIR] [--plugin-root DIR] [--yes]

Init asks these, in this order, and nothing else:

    What must be true of every rule before a version is proven?
    Measure test strength by breaking the code on purpose? [y/N], only at
      the gates `strong` and `signed`, and only where an engine that runs on
      this operating system exists for a framework the tree carries

Everything else is derived from those answers or read from the tree: the git
host from the remote URL, and the minimum test strength from the gate when
mutation testing is on. Nothing is asked about how the tests run: a project
with no `tests` setting gets an empty one, and the first test run suggests
the command. `--yes` takes every default, so mutation testing stays off;
`--mutation` turns it on without the question. `audit_parallel` is written as
4 and is not asked.

It then writes, in this order and naming every one in the summary: the config,
the engine's config block where mutation testing is on, the `.gitignore`
entries, `.purlin/evidence/` with its README, the dashboard, and, where one is
wanted, the workflow a remote runner runs. Nothing is written into the
project's test suite or its test runner's configuration. It ends on the
summary and `Left to do` of the project as it now is.

A workflow is written for one reason and no other: a proof in `specs/` is
tagged `@env` for an operating system this machine is not. A project with no
such proof gets no workflow and no runner: at the gate `signed` `purlin:sign`
writes the tag, you push it, and nothing runs remotely. Where one is wanted
the prerequisites are checked first, and a missing one is named with the
command that fixes it; nothing is written then.

Both ways of loading Purlin work, and neither is written into a project: this
checkout under `--plugin-dir`, and the marketplace copy under the plugin cache.

Exit codes: 0 the project is set up, 1 the settings file cannot be read, 2
the invocation was wrong, the directory is not a git repository, or the
project root does not exist.
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

import config_engine                                          # noqa: E402
import mutation as mutation_module                            # noqa: E402
import workflow as workflow_module                            # noqa: E402
from mutation import ENGINE_BY_FRAMEWORK, mutmut              # noqa: E402
from purlin import (console as console_module,                # noqa: E402
                    frameworks as frameworks_module,
                    evidence as evidence_module,
                    gate as gate_module,
                    specs as specs_module, status as status_module)

EXIT_OK = 0
EXIT_UNREADABLE_SETTINGS = 1
EXIT_BAD_INVOCATION = 2

ARROW = '→'
NOT_A_REPOSITORY = 'This is not a git repository. Run git init, then init.'

GATE_QUESTION = 'What must be true of every rule before a version is proven?'
GATE_CHOICES = (
    "passed  every rule's tests pass",
    'strong  tests pass and the audit finds them sound',
    'signed  strong, and a person signs each rule',
)
NOT_A_GATE = 'purlin: "%s" is not a gate; reading it as %s.'

REMOTE_INTRO = 'A remote runner is written because:'
NO_GIT_HOST = 'No git host found.'
REMOTE_NO_REMOTE = ('there is no git remote, so there is no runner to read '
                    'it')

MUTANTS_IGNORE = ('# The copy mutmut breaks, rebuilt on every run, never committed\n'
                  'mutants/\n')

_STRYKER_NOTE = ('%s: Stryker measures the breaks. Without it test strength '
                 'is not measured.')


def runner_label(gate):
    """What a skip line calls the runner file: at `passed`, not `CI`."""
    return 'the runner file' if gate == 'passed' else 'the CI workflow'

# Mutation testing is optional and off by default. The question is asked only
# at the gates `strong` and `signed`, and only where an engine exists for a
# framework the tree carries; a yes writes `mutation_engine: auto` and the
# gate's minimum strength, a no writes `none`.
MUTATION_QUESTION = ('Measure test strength by breaking the code on purpose? '
                     'It needs %s and takes minutes to hours per run. [y/N]')
NO_ENGINE = ('Mutation testing is off: no engine breaks %s code, so the AI '
             'audit alone judges test strength.')
NO_ENGINE_HERE = ('Mutation testing is off: mutmut does not run on Windows, so '
                  'the AI audit alone judges test strength.')
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


def origin_url(root):
    """The URL of the `origin` remote, or '' when there is none."""
    ok, url = _git(root, 'remote', 'get-url', 'origin')
    return url if ok else ''


def git_host(root):
    """`github`, `azure` or None, read from the remote URL."""
    lowered = origin_url(root).lower()
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


class Plan(object):
    """Every write, as one line, in the order the summary prints it."""

    def __init__(self, root):
        self.root = root
        self.lines = []

    def note(self, text):
        self.lines.append(text)

    def skip(self, what, why):
        self.lines.append('skipped %s (%s)' % (what, why))

    def directory(self, rel):
        path = os.path.join(self.root, rel)
        if os.path.isdir(path):
            return self.note('kept %s/' % rel)
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
                 mutation='none'):
    """`.purlin/config.json`: `version`, then the template's keys, and no other.

    `version` is the plugin's `VERSION`. Each other value is the answer, what
    the answers derive, or what the project already wrote. `tests` is the
    `tests` setting, one entry per suite, and `ci` is the host read from the
    remote, or `none` where there is no remote or it names neither host.
    """
    template = json.loads(_read(plugin_root, 'templates', 'config.json'))
    config = {'version': None}
    config.update(template)
    config.update((key, value) for key, value in (existing or {}).items()
                  if key in template)
    config.update({'version': _read(plugin_root, 'VERSION').strip(),
                   'gate': gate, 'mutation_engine': mutation,
                   'min_strength': min_strength_for(gate, mutation),
                   'audit_parallel': audit_parallel(existing),
                   'tests': tests, 'ci': host or 'none'})
    plan.write('.purlin/config.json', json.dumps(config, indent=2) + '\n',
               own=True)
    return config


def write_engine(plan, root, selected):
    """The engine that breaks the code, wired like the other config files."""
    if 'pytest' in selected and mutation_module.runs_here('mutmut'):
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
    """The engine that breaks the code of the first framework that has one
    able to run on this operating system; an engine that cannot run here
    counts as none."""
    for framework in selected:
        engine = ENGINE_BY_FRAMEWORK.get(framework, 'none')
        if engine != 'none' and mutation_module.runs_here(engine):
            return engine
    return None


def _no_engine_line(selected):
    """Why mutation testing is off where no engine can break this code here.

    An engine exists for a framework the tree carries and cannot run on this
    operating system: the line says so, not that no engine exists.
    """
    for framework in selected:
        engine = ENGINE_BY_FRAMEWORK.get(framework, 'none')
        if engine != 'none' and not mutation_module.runs_here(engine):
            return NO_ENGINE_HERE
    return NO_ENGINE % (', '.join(selected) or "this project's")


def resolve_mutation(console, existing, selected, turn_on, gate):
    """`(mutation_engine, the line to print or None)`.

    A value the project already wrote is kept and nothing is asked. With no
    engine for any framework the tree carries that can run on this operating
    system, nothing is asked either: mutation testing stays off, and at
    `strong` and `signed` one line says why. Otherwise `--mutation` turns it
    on, and at those two gates the question decides, defaulting to no; at
    `passed` it stays off unasked.
    """
    engine = engine_for(selected)
    if engine is None:
        if gate == 'passed':
            return 'none', None
        return 'none', _no_engine_line(selected)
    written = str((existing or {}).get('mutation_engine') or '').strip()
    if written and not turn_on:
        return written, None
    if turn_on:
        return 'auto', None
    if gate == 'passed':
        return 'none', None
    answer = str(console.ask(MUTATION_QUESTION % ENGINE_NAMES.get(engine, engine),
                             'n') or '').strip().lower()
    return ('auto' if answer.startswith('y') else 'none'), None


def write_gitignore(plan, plugin_root):
    """templates/gitignore.purlin, appended once and guarded by its first entry."""
    plan.append('.gitignore',
                _read(plugin_root, 'templates', 'gitignore.purlin'),
                '.purlin/runtime/')


def print_remote_reasons(reasons, gate=None):
    """Why this project gets a remote runner, or the line saying it needs none."""
    print('')
    if not reasons:
        print('No remote runner: %s.' % workflow_module.no_reason(gate))
        return
    print(REMOTE_INTRO)
    for reason in reasons:
        print('  %s' % reason)


def write_workflow(plan, root, purlin_ref, gate=None):
    """The workflow the git host runs, with one job per system the `@env`
    tags name that this machine is not.

    The prerequisites are checked first and nothing is written when one is
    missing: a workflow file is no use without the remote that holds it and
    a host that runs it. The triggers name no branch of the project's own.
    """
    ok, host, lines = workflow_module.prerequisites(root)
    # The line naming a host that is neither of the two is already in the
    # summary, under its first line; it is not said twice.
    for line in lines:
        if line not in plan.lines:
            plan.note(line)
    if not ok:
        return plan.skip(runner_label(gate), 'a prerequisite is missing')
    env_tags = workflow_module.foreign_tags(
        workflow_module.env_tags_in_specs(root), evidence_module.host_os())
    rel = workflow_module.workflow_path(host)
    plan.write(rel, workflow_module.render_workflow(
        host, env_tags, purlin_ref), own=True)
    plan.note('  the matrix is %s, the systems the @env tags in specs/ name '
              'that this machine is not.'
              % ', '.join(workflow_module.runners_for(env_tags)))
    plan.note('  it runs on a push to a run/* branch and on a push of a '
              'signed/* tag.')
    return host


def next_step(root):
    """How the project stands now: the lines `purlin:status` ends on.

    That is the summary and `Left to do`, whose first line is the next step.
    A project with no spec yet has neither, and is sent to write one.
    """
    first = '%s Run: purlin:spec to write the first spec.' % ARROW
    try:
        report = status_module.sync_status(root)
    except Exception:                                          # noqa: BLE001
        return [first]
    if report == status_module.NO_SPECS:
        return [first]
    # The report ends on its last block, after the one blank line before it.
    return report.rsplit('\n\n', 1)[-1].splitlines()


# --- Invocation ------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='scaffold.py', description='Set a project up for Purlin')
    parser.add_argument('--gate', choices=gate_module.GATES, default=None)
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--plugin-root', default=None)
    for flag in ('--update', '--yes', '--mutation'):
        parser.add_argument(flag, action='store_true')
    return parser.parse_args(argv)


def delegate_update(args):
    """`--update` belongs to scripts/init/update.py, which owns the upgrade."""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import update                                              # noqa: PLC0415
    return update.main(['--project-root', args.project_root]
                       + (['--yes'] if args.yes else []))


def resolve_tests(existing):
    """`(the suites named, the tests setting to write)`.

    A `tests` setting the project already carries is kept as it is; a project
    with none gets an empty one, and nothing is asked: the first test run
    suggests the command.
    """
    written = (existing or {}).get('tests')
    tests = [dict(entry) for entry in written] if isinstance(
        written, list) else []
    names = [entry.get('name') for entry in tests if isinstance(entry, dict)]
    return [name for name in names if name], tests


def frameworks_carried(root, names):
    """The frameworks the tree carries, then any other the suites name."""
    carried = list(frameworks_module.detect_frameworks(root))
    return carried + [name for name in names if name not in carried]


def _existing_config(root):
    """The project's own `.purlin/config.json`, or None when it has none.

    Called once `config_engine.config_problem` has answered None, so a file
    that is there reads as a JSON object.
    """
    path = os.path.join(root, '.purlin', 'config.json')
    if not os.path.lexists(path):
        return None
    with open(path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


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

    if not is_repository(root):
        print(NOT_A_REPOSITORY, file=sys.stderr)
        return EXIT_BAD_INVOCATION

    # A settings file that cannot be read stops setup before anything is
    # asked or written: rewriting it would lose every setting it holds.
    problem = config_engine.config_problem(root)
    if problem:
        print(problem, file=sys.stderr)
        return EXIT_UNREADABLE_SETTINGS

    existing = _existing_config(root)
    console = Console(args.yes)
    plan = Plan(root)

    gate = args.gate or (existing or {}).get('gate')
    if gate not in gate_module.GATES:
        gate = console.ask(GATE_QUESTION, gate_module.DEFAULT_GATE,
                           GATE_CHOICES)
        if gate not in gate_module.GATES:
            print(NOT_A_GATE % (gate, gate_module.DEFAULT_GATE))
            gate = gate_module.DEFAULT_GATE

    names, tests = resolve_tests(existing)
    carried = frameworks_carried(root, names)
    mutation, no_engine = resolve_mutation(console, existing, carried,
                                           args.mutation, gate)
    host = git_host(root)

    summary = 'Gate %s. Suites %s.' % (gate, ', '.join(names) or 'none')
    if host:
        plan.note('%s Git host %s.' % (summary, host))
    else:
        plan.note(summary)
        plan.note(workflow_module.UNKNOWN_HOST if git_remote(root)
                  else NO_GIT_HOST)
    if no_engine:
        plan.note(no_engine)
    for name in ('.purlin', 'specs'):
        plan.directory(name)

    config = write_config(plan, plugin_root, existing, gate, host, tests,
                          mutation)
    if mutation != 'none':
        write_engine(plan, root, carried)
    write_gitignore(plan, plugin_root)
    write_evidence(plan, plugin_root)
    plan.copy(os.path.join(plugin_root, 'scripts', 'report',
                           'purlin-report.html'), 'purlin-report.html')
    # A workflow is written for one reason and no other: a proof this
    # machine cannot prove. A project with none runs nothing remotely.
    tags = workflow_module.env_tags_in_specs(root)
    wanted, reasons = workflow_module.wanted(
        tags, evidence_module.host_os(), gate)
    print_remote_reasons(reasons, gate)
    if wanted and not git_remote(root):
        wanted = False
        plan.skip(runner_label(gate), REMOTE_NO_REMOTE)
    elif not wanted:
        plan.skip(runner_label(gate), workflow_module.no_reason(gate))
    if wanted:
        write_workflow(plan, root, 'v%s' % config.get('version', ''), gate)

    for line in plan.lines:
        print(line)

    print('')
    for line in next_step(root):
        print(line)
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
