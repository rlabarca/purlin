#!/usr/bin/env python3
"""purlin:init: one question, then every file a project needs.

    scaffold.py [--gate passed|strong|signed]
                [--add <language>] [--update] [--dry-run]
                [--project-root DIR] [--plugin-root DIR] [--yes]

On a project that has code, init asks two questions and nothing else:

    What must be true of every rule before a version is proven?
    Do you trust your own machine for the tests and the signing? [y/n]

Everything else is derived from those answers or read from the tree: the
language from detection, the git host from the remote URL, and the minimum
test strength from the gate. Two honest exceptions: a tree with nothing to
detect is asked which framework its tests use, and `signed` is asked which
rules need a signature.

It then writes, in this order and naming every one in the summary: the config,
the plugin copies, the runner's wiring, the engine's config block, the
`.gitignore` entries, the dashboard, and, where one is wanted, the workflow
CI runs.
It ends with the next step computed from the state.

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
from mutation import mutmut                                   # noqa: E402
from purlin import (console as console_module,                # noqa: E402
                    frameworks as frameworks_module,
                    evidence as evidence_module,
                    gate as gate_module,
                    specs as specs_module, status as status_module)

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

ARROW = '→'
NOT_A_REPOSITORY = 'This is not a git repository. Run git init, then init.'
DROPPED_FRAMEWORK = ('dropped %s from test_framework: nothing in the tree '
                     'runs it')

GATE_QUESTION = 'What must be true of every rule before a version is proven?'
GATE_CHOICES = (
    'passed  every rule has a passing tagged test, from any source',
    'strong  every rule has a record an audit wrote, at the minimum test strength',
    'signed  strong, plus a signature from a person on the rule',
)
SIGN_AT_QUESTION = 'Which rules need a signature?'
SIGN_AT_CHOICES = (
    'strong  the rules whose bar is strong; the rest meet the gate on their '
    'tests',
    'all     every rule, whatever its bar',
)
LANGUAGE_QUESTION = ('There is nothing here to detect a test framework from. '
                     'Which one do the tests use?')

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

# The registry's **Installed as** column is the one place a plugin's name
# inside a project is written, so this script and the upgrade cannot disagree.
_REGISTRY = os.path.join('references', 'supported_frameworks.md')

MUTANTS_IGNORE = ('# The copy mutmut breaks, rebuilt on every run, never committed\n'
                  'mutants/\n')

_WIRING = {
    'pytest': ('conftest.py',
               '# Purlin proof plugin, wired by purlin:init. `.purlin` is not\n'
               "# an importable package name, so the plugin's directory goes\n"
               '# on sys.path and the plugin is named by module.\n'
               'import os\n'
               'import sys\n'
               '\n'
               'sys.path.insert(0, os.path.join(\n'
               '    os.path.dirname(os.path.abspath(__file__)),\n'
               '    ".purlin", "plugins"))\n'
               '\n'
               'pytest_plugins = ["pytest_purlin"]\n'),
    'jest': ('jest.config.js',
             '// Purlin proof reporter, wired by purlin:init.\n'
             'module.exports = {\n'
             "  reporters: ['default', '.purlin/plugins/jest_purlin.js'],\n"
             '};\n'),
    'vitest': ('vitest.config.ts',
               '// Purlin proof reporter, wired by purlin:init.\n'
               "import { defineConfig } from 'vitest/config';\n"
               '\n'
               'export default defineConfig({\n'
               "  test: { reporters: ['default', "
               "'.purlin/plugins/vitest_purlin.ts'] },\n"
               '});\n'),
}

# xUnit is wired by hand: the logger needs a `*.TestLogger.dll` assembly.
_XUNIT_NOTE = ('xunit: compile .purlin/plugins/xunit_purlin.cs into a '
               '*.TestLogger.dll and run dotnet test --logger purlin.')

_STRYKER_NOTE = ('%s: Stryker measures the breaks. Without it the test '
                 'strength reads n/a.')

_TRUST_WORDS = {'local': TRUST_LOCAL, 'remote': TRUST_REMOTE}

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


def plugin_files(plugin_root):
    """framework -> (the plugin's file name, the name a project installs it as)."""
    rows = {}
    for line in _read(plugin_root, _REGISTRY).splitlines():
        cells = [cell.strip() for cell in line.split('|')]
        if len(cells) < 7 or not cells[1].startswith('**'):
            continue
        source = cells[4].strip('`').split('/')[-1]
        rows[cells[2].split()[0].lower()] = (source, cells[5].strip('`'))
    return rows


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
        the way out, so a plugin copied through it stops being the file it was
        copied from, and a project could no longer be shown to hold the
        plugin this release ships.
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

def write_config(plan, plugin_root, existing, gate, host, framework,
                 sign_at=None, trust=None):
    """`.purlin/config.json`: the template, the gate, and what follows from it."""
    config = json.loads(_read(plugin_root, 'templates', 'config.json'))
    config.update(existing or {})
    derived = gate_module.resolve_gate({'gate': gate})
    config.update({'version': _read(plugin_root, 'VERSION').strip(),
                   'gate': gate, 'min_strength': derived.min_strength,
                   'trust': trust or gate_module.DEFAULT_TRUST})
    if host:
        config['ci'] = host
    if framework:
        config['test_framework'] = framework
    for key in gate_module.RETIRED_KEYS:
        config.pop(key, None)
    if gate == 'signed':
        config['sign_at'] = sign_at or derived.sign_at
    else:
        config.pop('sign_at', None)
    plan.write('.purlin/config.json', json.dumps(config, indent=2) + '\n',
               own=True)
    return config


def install_plugins(plan, plugin_root, selected):
    """A byte-identical copy of each selected framework's plugin."""
    known = plugin_files(plugin_root)
    for framework in selected:
        if framework not in known:
            plan.skip('.purlin/plugins/', 'no plugin for %s' % framework)
            continue
        plan.copy(os.path.join(plugin_root, 'scripts', 'proof',
                               known[framework][0]),
                  '.purlin/plugins/%s' % known[framework][1])


def write_wiring(plan, selected):
    """The test runner's own configuration, never written over."""
    for framework in selected:
        if framework in _WIRING:
            plan.write(*_WIRING[framework])
        elif framework == 'xunit':
            plan.note(_XUNIT_NOTE)


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
    for name in [f for f in ('jest', 'vitest', 'xunit') if f in selected]:
        plan.note(_STRYKER_NOTE % name)


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
    for flag in ('--update', '--dry-run', '--yes'):
        parser.add_argument(flag, action='store_true')
    return parser.parse_args(argv)


def delegate_update(args):
    """`--update` belongs to scripts/init/update.py, which owns the upgrade."""
    if not os.path.isfile(os.path.join(_HERE, 'update.py')):
        print('The upgrade path lives in scripts/init/update.py, which this '
              'plugin does not carry yet.')
        return EXIT_NOTHING
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import update                                              # noqa: PLC0415
    # `--dry-run` is what the upgrade calls `--check`: say what is pending and
    # write nothing. No other flag of this script means anything to it.
    return update.main(['--project-root', args.project_root]
                       + (['--yes'] if args.yes else [])
                       + (['--check'] if args.dry_run else []))


def resolve_frameworks(root, console, existing, add):
    """`(the frameworks to wire, the answer to record, the names dropped)`.

    Detection answers on a project with code, and nothing is asked. A tree
    with nothing to detect is asked once, which is the second exception.

    A name the config carries that the tree cannot run is dropped rather than
    carried: an older release wrote down every plugin it shipped, and wiring a
    runner with nothing to run makes every run print that runner exiting
    non-zero. A name the tree does carry stays even when detection would not
    have picked it.
    """
    written = (existing or {}).get('test_framework')
    written = written if isinstance(written, str) else ''
    if add:
        named = (frameworks_module.detect_frameworks(root)
                 if written in ('', 'auto')
                 else frameworks_module.resolve_frameworks(root, written)[0])
        named, dropped = frameworks_module.prune_unwired(root, named)
        named += [part.strip() for part in add.split(',') if part.strip()]
        named = list(dict.fromkeys(named))
        return named, ','.join(named), dropped
    if written and written != 'auto':
        named = frameworks_module.resolve_frameworks(root, written)[0]
        named, dropped = frameworks_module.prune_unwired(root, named)
        return named, ','.join(named), dropped
    detected = frameworks_module.detect_frameworks(root)
    if detected != ['shell']:
        return detected, 'auto', []
    answer = console.ask(LANGUAGE_QUESTION, 'shell',
                         ['  '.join(frameworks_module.KNOWN_FRAMEWORKS)])
    if answer not in frameworks_module.KNOWN_FRAMEWORKS:
        print('purlin: "%s" is not a framework this release ships a plugin '
              'for; reading it as shell.' % answer)
        answer = 'shell'
    return [answer], answer, []


def ask_sign_at(console):
    """Which rules need a signature: the one question the `signed` gate adds.

    A bar is what a rule must prove before anyone signs it, so the answer is
    either the rules that carry the strong bar or every rule there is.
    """
    answer = str(console.ask(SIGN_AT_QUESTION,
                             gate_module.DEFAULT_SIGN_AT,
                             SIGN_AT_CHOICES) or '').strip().lower()
    if answer in gate_module.SIGN_AT_VALUES:
        return answer
    print('purlin: "%s" is not one of %s; reading it as %s.'
          % (answer, ' or '.join(gate_module.SIGN_AT_VALUES),
             gate_module.DEFAULT_SIGN_AT))
    return gate_module.DEFAULT_SIGN_AT


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

    sign_at = None
    if gate == 'signed':
        sign_at = ask_sign_at(console)

    selected, framework, dropped = resolve_frameworks(
        root, console, existing, args.add)
    trust = ask_trust(console, existing)
    host = git_host(root)

    if not in_git:
        plan.note(NOT_A_REPOSITORY)
    for name in dropped:
        plan.note(DROPPED_FRAMEWORK % name)
    plan.note('Gate %s. Frameworks %s. Git host %s.'
              % (gate, ', '.join(selected), host or 'not read from a remote'))
    plan.note(_TRUST_WORDS[trust])
    for name in ('.purlin', '.purlin/plugins', 'specs', 'specs/_anchors'):
        plan.directory(name)

    config = write_config(plan, plugin_root, existing, gate, host, framework,
                          sign_at, trust)
    install_plugins(plan, plugin_root, selected)
    write_wiring(plan, selected)
    write_engine(plan, root, selected)
    write_gitignore(plan, plugin_root)
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
