#!/usr/bin/env python3
"""purlin:init: one question, then every file a project needs.

    scaffold.py [--gate tested|recorded|approved] [--ci github|ado]
                [--upstream-check] [--add <language>] [--update]
                [--dry-run] [--project-root DIR] [--plugin-root DIR] [--yes]

On a project that has code, init asks one question and nothing else:

    What must be true before CI lets a change merge?

Everything else is derived from that answer or read from the tree: the
language from detection, the git host from the remote URL, the minimum test
strength and the review threshold from the gate. Two honest exceptions: a tree
with nothing to detect is asked which framework its tests use, and `approved`
is asked who may approve.

It then writes, in this order and naming every one in the summary: the config,
the plugin copies and `.purlin/plugin-root`, the test runner's wiring, the
engine's config block, the `.gitignore` entries, `designs/` and
`.purlin/records/` with their READMEs, the dashboard, the pre-push hook, and
under `recorded` and `approved` the workflow CI runs. It ends with the branch
rules the git host has to enforce and the next step computed from the state.

Both ways of loading Purlin work, and neither is written into a project: this
checkout under `claude --plugin-dir`, and the marketplace copy under
`~/.claude/plugins/cache/purlin/purlin/<version>/`.

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
from purlin import (frameworks as frameworks_module,          # noqa: E402
                    gate as gate_module, specs as specs_module,
                    status as status_module)

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

ARROW = '→'
NOT_A_REPOSITORY = 'This is not a git repository. Run git init, then init.'

GATE_QUESTION = 'What must be true before CI lets a change merge?'
GATE_CHOICES = (
    'tested    every rule has a passing tagged test',
    'recorded  every rule has a record CI wrote at this commit, at or above '
    'the minimum test strength',
    'approved  recorded, plus a current approval on every high and medium rule',
)
LANGUAGE_QUESTION = ('There is nothing here to detect a test framework from. '
                     'Which one do the tests use?')
APPROVER_QUESTION = 'Who may approve a rule? Emails, separated by commas.'

# The registry's **Installed as** column is the one place a plugin's name
# inside a project is written, so this script and the upgrade cannot disagree.
_REGISTRY = os.path.join('references', 'supported_frameworks.md')

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

_READMES = {
    'designs': """The mocks a design rule is written against: PNG, PDF, SVG or an HTML prototype.
A design anchor pins the hash of these files, and a feature spec requires that anchor.
A new export stales the approvals of that anchor's rules, so a person looks again.
""",
    '.purlin/records': """Every verify run writes one record per feature here, and commits it.
CI writes the records that count under recorded and approved; a person writes the ones that
count under tested. Verify keeps the newest three per feature per runner.
""",
}

# A gate is three things: a job running verify on every push, a rule blocking
# merge unless it passes, and the setting saying what pass means. The setting
# is in .purlin/config.json; these two are what the git host has to be told.
_BRANCH_RULES = {
    'github': """Branch rules to apply on GitHub:
  1. Require a pull request, and require the purlin status check. Bypass: the GitHub Actions app alone.
  2. Restrict file paths .purlin/records/** and specs/**/*.approvals/*.ci.json. Bypass: the GitHub
     Actions app alone, so a person cannot push a record or a CI approval.
  3. Block force pushes and restrict deletions, with no bypass.""",
    'azure': """Branch security to apply on Azure DevOps:
  1. Require a pull request, with the purlin pipeline as a build validation policy.
  2. Grant Contribute on .purlin/records/** and specs/**/*.approvals/*.ci.json to the build service
     alone, so a person cannot push a record or a CI approval.
  3. Deny Force Push and Delete branch for everyone.""",
    'tested': """Branch rules to apply on the git host: block force pushes and restrict deletions, with no bypass.
The gate is tested, so nothing else is required until you raise it.""",
}


# --- Reading the tree ------------------------------------------------------

def _read(*parts):
    try:
        with open(os.path.join(*parts), 'r', encoding='utf-8') as handle:
            return handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return ''


def _git(root, *args):
    """`(ok, stripped stdout)` for one git command run in `root`."""
    try:
        done = subprocess.run(['git'] + list(args), cwd=root,
                              capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError):
        return False, ''
    return done.returncode == 0, done.stdout.strip()


def git_host(root):
    """`github`, `azure` or None, read from the remote URL."""
    ok, url = _git(root, 'remote', 'get-url', 'origin')
    lowered = url.lower() if ok else ''
    if 'github' in lowered:
        return 'github'
    if 'dev.azure.com' in lowered or 'visualstudio.com' in lowered:
        return 'azure'
    return None


def hooks_dir(root):
    """The directory git reads hooks from, or None outside a repository.

    `core.hooksPath` first: a repository that sets it is one where git reads
    nothing else, and a hook in `.git/hooks` there is a file git never runs.
    """
    ok, top = _git(root, 'rev-parse', '--show-toplevel')
    if not ok or not top:
        return None
    _, setting = _git(root, 'config', '--get', 'core.hooksPath')
    if setting:
        return os.path.abspath(setting if os.path.isabs(setting)
                               else os.path.join(top, setting))
    ok, common = _git(root, 'rev-parse', '--git-common-dir')
    if not ok or not common:
        return None
    return os.path.join(os.path.abspath(os.path.join(root, common)), 'hooks')


def installed_plugin_root():
    """The plugin directory `.purlin/plugin-root` names, which the shim reads.

    `CLAUDE_PLUGIN_ROOT` when set and carrying this script, which is the
    marketplace install; else this checkout, which `--plugin-dir` loads.
    """
    named = os.environ.get('CLAUDE_PLUGIN_ROOT') or ''
    if named and os.path.isfile(os.path.join(named, 'scripts', 'init',
                                             'scaffold.py')):
        return os.path.abspath(named)
    return PLUGIN_ROOT


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


def untagged_rules(root):
    """`[(feature, RULE-N)]` for every rule that names no risk.

    Read off the rule line: in the parsed metadata an untagged rule and one
    tagged `low` are the same thing.
    """
    found = []
    for path in specs_module.spec_files(root):
        name = os.path.splitext(os.path.basename(path))[0]
        section = specs_module.extract_section(_read(path), '## Rules') or ''
        for line in section.splitlines():
            line = line.strip()
            if line.startswith('- RULE-') and '[risk:' not in line:
                found.append((name, line[2:].split(':', 1)[0]))
    return found


def mutmut_paths(root):
    """`(source paths, test selection)` for the engine's config block."""
    dirs = [n for n in sorted(os.listdir(root)) if not n.startswith('.')
            and os.path.isdir(os.path.join(root, n))]
    sources = [n for n in ('src', 'lib', 'app') if n in dirs] or [
        n for n in dirs if n not in ('tests', 'test', 'specs', 'designs')
        and any(f.endswith('.py') for f in os.listdir(os.path.join(root, n)))]
    return sources or ['.'], [n for n in ('tests', 'test') if n in dirs] or ['.']


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

    def write(self, rel, text, own=False, perm=None, source=None):
        """One file. `own` means Purlin owns the bytes and refreshes a stale one."""
        path = os.path.join(self.root, rel)
        if os.path.lexists(path) and (not own or _read(path) == text):
            return self.note('kept %s' % rel)
        if not self.allowed(rel, 'write %s' % rel):
            return
        if not self.dry_run:
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
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
        self.write(rel, _read(source), source=os.path.relpath(
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


# --- The pre-push hook -----------------------------------------------------

# The shim is tracked in git on purpose: it names no machine, no release and
# no checkout, so the file is right for every clone, and everything
# machine-specific is resolved when it runs. That is what lets a plugin update
# change the hook with nothing in the project rewritten.
_SHIM = '''#!/bin/sh
# Purlin pre-push shim, written by purlin:init. It hands the hook to the
# installed plugin's own scripts/hooks/pre-push.sh, where the behaviour lives.
# The first of these carrying that file wins: $PURLIN_PLUGIN_ROOT, line 1 of
# .purlin/plugin-root, $CLAUDE_PLUGIN_ROOT, a marketplace install under
# ~/.claude/plugins/cache/purlin/purlin/, then the project root. A push is
# never blocked because the plugin was not found: no test ran, none failed.
set -u

PURLIN_SCRIPT="scripts/hooks/pre-push.sh"
PURLIN_PROJECT="$(git rev-parse --show-toplevel)"
PURLIN_ROOT=""

purlin_try() {
  if [ -z "$PURLIN_ROOT" ] && [ -n "${1:-}" ] && [ -f "$1/$PURLIN_SCRIPT" ]; then
    PURLIN_ROOT="$1"
  fi
}

PURLIN_PINNED=""
if [ -f "$PURLIN_PROJECT/.purlin/plugin-root" ]; then
  PURLIN_PINNED="$(sed -n 1p "$PURLIN_PROJECT/.purlin/plugin-root")"
fi

purlin_try "${PURLIN_PLUGIN_ROOT:-}"
purlin_try "$PURLIN_PINNED"
purlin_try "${CLAUDE_PLUGIN_ROOT:-}"
for purlin_cached in "$HOME"/.claude/plugins/cache/purlin/purlin/*; do
  purlin_try "$purlin_cached"
done
purlin_try "$PURLIN_PROJECT"

if [ -z "$PURLIN_ROOT" ]; then
  echo "purlin: the plugin was not found, so the tagged tests did not run"
  echo "        before this push. Set PURLIN_PLUGIN_ROOT, or write the plugin"
  echo "        directory into .purlin/plugin-root, to fix this."
  exit 0
fi

exec "$PURLIN_ROOT/$PURLIN_SCRIPT" "$@"
'''

_DELEGATOR_MARKER = 'purlin-delegator'
_DELEGATOR = ('#!/bin/sh\n'
              '# purlin-delegator (purlin:init): the hook body is '
              '.purlin/hooks/pre-push, tracked in git.\n'
              'PURLIN_SHIM="$(git rev-parse --show-toplevel)'
              '/.purlin/hooks/pre-push"\n'
              'if [ ! -x "$PURLIN_SHIM" ]; then\n'
              '  echo "purlin: no hook shim at $PURLIN_SHIM; run purlin:init"\n'
              '  exit 0\n'
              'fi\n'
              'exec "$PURLIN_SHIM" "$@"\n')


def hook_manager(root):
    """The tool that already owns this repository's hooks, or None.

    Such a tool runs only its own file, so writing into the slot it points at
    either loses the project's hooks or has Purlin's overwritten.
    """
    _, setting = _git(root, 'config', '--get', 'core.hooksPath')
    lowered = (setting or '').replace('\\', '/').lower()
    if '.husky' in lowered:
        return 'husky', '.husky/pre-push'
    if 'lefthook' in lowered:
        return 'lefthook', 'lefthook.yml'
    if os.path.exists(os.path.join(root, '.pre-commit-config.yaml')):
        return 'the pre-commit framework', '.pre-commit-config.yaml'
    return None


def install_hook(plan, root, hooks):
    """The tracked shim, then the hook git itself runs."""
    plan.write('.purlin/hooks/pre-push', _SHIM, own=True, perm=0o755)
    line = 'exec "$(git rev-parse --show-toplevel)/.purlin/hooks/pre-push" "$@"'
    managed = hook_manager(root)
    if managed is not None:
        return plan.skip('the pre-push hook', '%s manages this repository\'s '
                         'hooks; add this line to %s: %s'
                         % (managed[0], managed[1], line))
    if hooks is None:
        return plan.skip('the pre-push hook', 'no git repository yet')
    dest = os.path.join(hooks, 'pre-push')
    rel = os.path.relpath(dest, root).replace(os.sep, '/')
    if os.path.lexists(dest) and _DELEGATOR_MARKER not in _read(dest):
        return plan.skip(rel, 'a hook is already there and is kept; add this '
                              'line to it: %s' % line)
    plan.write(rel, _DELEGATOR, own=True, perm=0o755)


# --- The steps -------------------------------------------------------------

def write_config(plan, plugin_root, existing, gate, host, framework, approvers):
    """`.purlin/config.json`: the template, the gate, and what follows from it."""
    config = json.loads(_read(plugin_root, 'templates', 'config.json'))
    config.update(existing or {})
    derived = gate_module.resolve_gate({'gate': gate})
    config.update({'version': _read(plugin_root, 'VERSION').strip(),
                   'gate': gate, 'ai_review_at': derived.ai_review_at,
                   'min_strength': derived.min_strength})
    if host:
        config['ci'] = host
    if framework:
        config['test_framework'] = framework
    for key in gate_module.RETIRED_KEYS:
        config.pop(key, None)
    if gate == 'approved':
        config['approvers'] = approvers
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
    for name in [f for f in ('jest', 'vitest', 'xunit') if f in selected]:
        plan.note(_STRYKER_NOTE % name)


def write_gitignore(plan, plugin_root):
    """templates/gitignore.purlin, appended once and guarded by its first entry."""
    plan.append('.gitignore',
                _read(plugin_root, 'templates', 'gitignore.purlin'),
                '.purlin/runtime/')


def write_workflow(plan, root, host, purlin_ref, upstream_check):
    """The workflow the git host runs, with the matrix the `@env` tags name."""
    env_tags = workflow_module.env_tags_in_specs(root)
    name = workflow_module.workflow_filename(host)
    rel = name if host == 'azure' else '.github/workflows/%s' % name
    plan.write(rel, workflow_module.render_workflow(
        host, env_tags, purlin_ref, upstream_check=upstream_check), own=True)
    plan.note('  the matrix is %s, from the @env tags in specs/.'
              % ', '.join(workflow_module.runners_for(env_tags)))


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
    parser.add_argument('--ci', choices=('github', 'ado', 'azure'), default=None)
    parser.add_argument('--add', default=None, help='one more framework')
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--plugin-root', default=None)
    for flag in ('--upstream-check', '--update', '--dry-run', '--yes'):
        parser.add_argument(flag, action='store_true')
    return parser.parse_args(argv)


def delegate_update(argv):
    """`--update` belongs to scripts/init/update.py, which owns the upgrade."""
    if not os.path.isfile(os.path.join(_HERE, 'update.py')):
        print('The upgrade path lives in scripts/init/update.py, which this '
              'plugin does not carry yet.')
        return EXIT_NOTHING
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import update                                              # noqa: PLC0415
    return update.main([arg for arg in argv if arg != '--update'])


def resolve_frameworks(root, console, existing, add):
    """`(the frameworks to wire, the answer to record)` for this project.

    Detection answers on a project with code, and nothing is asked. A tree
    with nothing to detect is asked once, which is the second exception.
    """
    recorded = (existing or {}).get('test_framework')
    recorded = recorded if isinstance(recorded, str) else ''
    if add:
        named = (frameworks_module.detect_frameworks(root)
                 if recorded in ('', 'auto')
                 else frameworks_module.resolve_frameworks(root, recorded)[0])
        named += [part.strip() for part in add.split(',') if part.strip()]
        named = list(dict.fromkeys(named))
        return named, ','.join(named)
    if recorded and recorded != 'auto':
        return frameworks_module.resolve_frameworks(root, recorded)[0], recorded
    detected = frameworks_module.detect_frameworks(root)
    if detected != ['shell']:
        return detected, 'auto'
    answer = console.ask(LANGUAGE_QUESTION, 'shell',
                         ['  '.join(frameworks_module.KNOWN_FRAMEWORKS)])
    if answer not in frameworks_module.KNOWN_FRAMEWORKS:
        print('purlin: "%s" is not a framework this release ships a plugin '
              'for; reading it as shell.' % answer)
        answer = 'shell'
    return [answer], answer


def _existing_config(root):
    """The project's own `.purlin/config.json`, or None when it has none."""
    try:
        value = json.loads(_read(root, '.purlin', 'config.json'))
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def print_approved(root, approvers):
    """What `approved` needs beyond the config: signers, and tagged risk."""
    import approve as approve_module                           # noqa: PLC0415
    print('')
    if approvers:
        print('Approvers: %s.' % ', '.join(approvers))
    else:
        print('%s No approver list yet. Run purlin:init --gate approved and '
              'name the emails; the gate exits 1 without them.' % ARROW)
    print('Each approver runs this once, then uploads the public key to the '
          'git host:')
    for command in approve_module.SIGNING_SETUP:
        print('  %s' % command)
    untagged = untagged_rules(root)
    if untagged:
        print('%s %d rules carry no risk tag, and approved requires one. Run '
              'purlin:spec to tag them:' % (ARROW, len(untagged)))
        for feature, rule in untagged[:20]:
            print('  %s %s' % (feature, rule))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    args = parse_args(argv)
    if args.update:
        return delegate_update(argv)

    root = os.path.abspath(args.project_root)
    plugin_root = os.path.abspath(args.plugin_root or PLUGIN_ROOT)
    if not os.path.isdir(root):
        print('no such project root: %s' % root, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    if not os.path.isfile(os.path.join(plugin_root, 'templates',
                                       'config.json')):
        print('not a Purlin plugin root: %s' % plugin_root, file=sys.stderr)
        return EXIT_BAD_INVOCATION

    hooks = hooks_dir(root)
    if hooks is None and not args.dry_run:
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

    approvers = [str(e).strip().lower() for e
                 in ((existing or {}).get('approvers') or []) if str(e).strip()]
    if gate == 'approved' and not approvers:
        approvers = [part.strip().lower()
                     for part in console.ask(APPROVER_QUESTION, '').split(',')
                     if part.strip()]

    selected, framework = resolve_frameworks(root, console, existing, args.add)
    host = {'ado': 'azure'}.get(args.ci, args.ci) or git_host(root)

    if hooks is None:
        plan.note(NOT_A_REPOSITORY)
    plan.note('Gate %s. Frameworks %s. Git host %s.'
              % (gate, ', '.join(selected), host or 'not read from a remote'))
    for name in ('.purlin', '.purlin/plugins', 'specs', 'specs/_anchors'):
        plan.directory(name)

    config = write_config(plan, plugin_root, existing, gate, host, framework,
                          approvers)
    install_plugins(plan, plugin_root, selected)
    plan.write('.purlin/plugin-root', installed_plugin_root() + '\n', own=True)
    write_wiring(plan, selected)
    write_engine(plan, root, selected)
    write_gitignore(plan, plugin_root)
    for directory in sorted(_READMES):
        plan.directory(directory)
        plan.write(directory + '/README.md', _READMES[directory])
    plan.copy(os.path.join(plugin_root, 'scripts', 'report',
                           'purlin-report.html'), 'purlin-report.html')
    install_hook(plan, root, hooks)
    if gate != 'tested' or args.ci:
        write_workflow(plan, root, host or 'github',
                       'v%s' % config.get('version', ''), args.upstream_check)
    else:
        plan.skip('the CI workflow',
                  'the gate is tested; pass --ci to write it anyway')

    for line in plan.lines:
        print(line)
    print('')
    print(_BRANCH_RULES['tested' if gate == 'tested' and not args.ci
                        else ('azure' if host == 'azure' else 'github')])
    if gate == 'approved':
        print_approved(root, approvers)

    print('')
    for line in next_step(root):
        print(line)
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
