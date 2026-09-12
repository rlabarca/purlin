#!/usr/bin/env python3
"""The mechanical half of `purlin:init`: every file a new project needs.

    python3 scripts/init/scaffold.py --project-root DIR
        [--test-framework auto|<id>[,<id>...]] [--pre-push warn|strict|off]
        [--mutation-checks on|off] [--remote-verification required|optional|off]
        [--report on|off] [--digest auto|warn|off]
        [--force] [--plugin-root DIR] [--dry-run]

`purlin:init` is the user-facing command; this script is the part of it that
must be deterministic and provable, so the skill asks the questions and this
script writes the files. It is to init what `scripts/update/migrate.py` is to
`purlin:init --update`: nothing here decides anything a user was asked about,
and nothing the skill decides is re-decided here.

WHAT IT WRITES
    .purlin/config.json     the template with the answered values and the
                            `version` stamped from VERSION
    .purlin/plugins/<file>  a byte-identical copy of each selected framework's
                            plugin from scripts/proof/
    conftest.py             the pytest wiring, jest.config.js the jest
    jest.config.js          reporter and vitest.config.ts the vitest one, each
    vitest.config.ts        written only when the project has no such file
    .gitignore              templates/gitignore.purlin, entry by entry, with
                            entries the file already carries left alone
    purlin-report.html      a symlink to the plugin's dashboard (report on)
    .git/hooks/pre-push     a symlink to scripts/hooks/, copied when the
    .git/hooks/pre-commit   symlink target does not resolve

    It never writes a proof entry, never writes a receipt and never commits.
    Those are claims about a run that happened, and scaffolding a project is
    not one.

THE PLAN
    One line per path, on stdout, in a fixed order:
    `wrote`, `kept`, `linked`, `copied`, `skipped`. `--dry-run` prints exactly
    the same plan and touches nothing, so what a run would do can be read
    before it does it.

EXIT CODES  (aligned with scripts/update/migrate.py)
    0  the project is scaffolded
    1  refused: `.purlin/config.json` already exists and `--force` was absent
    2  bad invocation: not a git repository, an unknown framework id, or a
       plugin root with no templates/config.json

    The git refusal is exit 2 and not 1 because it is the caller's mistake
    rather than the project's state: proofs, receipts, manual stamps, drift
    detection and both hooks all read git, so a project without it cannot be
    initialized at all, while an already-initialized project can be with
    `--force`.

WHAT `--force` KEEPS
    The existing `.purlin/config.json` is the base: every key it carries keeps
    its value unless a flag on this command line answers that key, the missing
    template keys are filled, and `version` is restamped from VERSION. So a
    re-init preserves `platforms`, `audit_criteria`, `audit_llm` and any answer
    this run did not ask about, and changes exactly what was re-answered.
    Nothing else on disk is replaced: an existing plugin copy, wiring file,
    hook or dashboard is kept and reported as `kept`.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_BAD_INVOCATION = 2

GIT_REQUIRED = "Purlin requires git. Run 'git init' first."

# The registry is the single source of truth for which frameworks exist and
# which file each one installs (`skill_init` RULE-48). The destination name is
# the plugin's own basename, except for the shell harness: a project installs
# it as `purlin-proof.sh`, which is the name every shell test sources.
_DEST_OVERRIDES = {'shell_purlin.sh': 'purlin-proof.sh'}

# The registry's Detection column is prose for a reader; these are the same
# checks as code. An id here that the registry does not list is a bug, and
# `_frameworks()` raises on one rather than installing a file nobody shipped.
_DETECTORS = (
    ('pytest', lambda root: (_exists(root, 'conftest.py')
                             or '[tool.pytest' in _slurp(root, 'pyproject.toml'))),
    ('vitest', lambda root: 'vitest' in _slurp(root, 'package.json')),
    ('jest', lambda root: 'jest' in _slurp(root, 'package.json')),
    ('c', lambda root: (_exists(root, 'Makefile')
                        or _exists(root, 'CMakeLists.txt'))),
    ('php', lambda root: (_exists(root, 'composer.json')
                          or _exists(root, 'phpunit.xml'))),
    ('sql', lambda root: any(n.endswith('.sql')
                             for n in _listdir(root, 'tests'))),
)

# Step 4 of the skill. Each is written only when the project has no file of
# that name: a project's own test configuration is never rewritten by init.
_WIRING = {
    'pytest': ('conftest.py',
               '# Purlin proof plugin, wired by purlin:init.\n'
               '#\n'
               "# `.purlin` is not an importable package name, so the plugin's\n"
               '# directory goes on sys.path and the plugin is named by module.\n'
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

_HOOKS = (('pre-push', 'pre-push.sh'), ('pre-commit', 'pre-commit.sh'))


# ── small filesystem helpers ──────────────────────────────────────────

def _exists(root, rel):
    return os.path.exists(os.path.join(root, rel))


def _slurp(root, rel):
    try:
        with open(os.path.join(root, rel), 'r', encoding='utf-8') as f:
            return f.read()
    except (IOError, OSError, UnicodeDecodeError):
        return ''


def _listdir(root, rel):
    try:
        return sorted(os.listdir(os.path.join(root, rel)))
    except (IOError, OSError):
        return []


def _write(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def _plugin_root():
    """The installed plugin: this file is <plugin root>/scripts/init/."""
    return os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))


# ── the registry ──────────────────────────────────────────────────────

_REGISTRY_ROW = re.compile(
    r'^\|\s*\*\*[^|]+\*\*\s*\|\s*([A-Za-z0-9_.+-]+)[^|]*\|[^|]*\|([^|]*)\|')


def _frameworks(plugin_root):
    """id -> [plugin file, ...], read from references/supported_frameworks.md.

    Both tables are read, so a framework that ships a plugin and is registered
    is one this script can install without being edited (RULE-48).
    """
    registry = _slurp(plugin_root, os.path.join('references',
                                                'supported_frameworks.md'))
    out = {}
    for line in registry.splitlines():
        match = _REGISTRY_ROW.match(line)
        if not match:
            continue
        framework_id = match.group(1).strip()
        files = re.findall(r'scripts/proof/([A-Za-z0-9_.+-]+)', match.group(2))
        if framework_id and files:
            out[framework_id] = files
    return out


def _detect(root, known):
    ids = []
    for framework_id, test in _DETECTORS:
        if framework_id not in known:
            raise KeyError(f'{framework_id} is not in the framework registry')
        if test(root):
            ids.append(framework_id)
    return ids


# ── the steps ─────────────────────────────────────────────────────────

def _config(plan, root, plugin_root, answers, force, dry_run):
    """Step 2: the template, the answers, and `version` from VERSION."""
    template = json.loads(_slurp(plugin_root, os.path.join('templates',
                                                           'config.json')))
    path = os.path.join(root, '.purlin', 'config.json')
    base = {}
    if os.path.exists(path) and force:
        try:
            base = json.loads(_slurp(root, os.path.join('.purlin',
                                                        'config.json')))
        except json.JSONDecodeError:
            base = {}
            plan.append('wrote .purlin/config.json (the existing file was not '
                        'readable JSON; rewritten from the template)')
    config = dict(template)
    config.update(base)
    for key, value in answers.items():
        if value is not None:
            config[key] = value
    config['version'] = _slurp(plugin_root, 'VERSION').strip()
    text = json.dumps(config, indent=2) + '\n'
    if not dry_run:
        _write(path, text)
    plan.append('wrote .purlin/config.json')
    return config


def _plugins(plan, root, plugin_root, registry, selected, dry_run):
    """Step 4: a byte-identical copy of each selected framework's plugin."""
    if not selected:
        plan.append('skipped .purlin/plugins/ (no framework selected; '
                    'run purlin:init --add-plugin or re-run with '
                    '--test-framework)')
        return
    for framework_id in selected:
        if framework_id == 'other':
            plan.append('skipped .purlin/plugins/ for "other" (install a '
                        'custom plugin with purlin:init --add-plugin)')
            continue
        for name in registry[framework_id]:
            dest_name = _DEST_OVERRIDES.get(name, name)
            dest = os.path.join(root, '.purlin', 'plugins', dest_name)
            rel = f'.purlin/plugins/{dest_name}'
            if os.path.exists(dest):
                plan.append(f'kept {rel}')
                continue
            if not dry_run:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copyfile(
                    os.path.join(plugin_root, 'scripts', 'proof', name), dest)
            plan.append(f'copied scripts/proof/{name} -> {rel}')


def _wiring(plan, root, selected, dry_run):
    """Step 4: the runner configuration, written only when it is absent."""
    for framework_id in selected:
        if framework_id not in _WIRING:
            continue
        name, body = _WIRING[framework_id]
        path = os.path.join(root, name)
        if os.path.exists(path):
            plan.append(f'kept {name}')
            continue
        if not dry_run:
            _write(path, body)
        plan.append(f'wrote {name}')


def _gitignore(plan, root, plugin_root, dry_run):
    """Step 5: templates/gitignore.purlin, entry by entry, never twice.

    The template is the one source for the block (the skill points at it), and
    an entry the project already carries is left where the project put it.
    """
    template = _slurp(plugin_root, os.path.join('templates',
                                                'gitignore.purlin'))
    path = os.path.join(root, '.gitignore')
    existing = _slurp(root, '.gitignore')
    have = set(line.strip() for line in existing.splitlines() if line.strip())
    additions = []
    pending = []
    for line in template.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            pending.append(line)
            continue
        if stripped in have:
            pending = []
            continue
        additions.extend(p for p in pending if p.strip() not in have)
        pending = []
        additions.append(line)
        have.add(stripped)
    if not additions:
        plan.append('kept .gitignore')
        return
    text = existing
    if text and not text.endswith('\n'):
        text += '\n'
    if text:
        text += '\n'
    text += '\n'.join(additions) + '\n'
    if not dry_run:
        _write(path, text)
    plan.append('wrote .gitignore')


def _link_or_copy(plan, source, dest, rel, dry_run):
    """Symlink first, copy when the target does not resolve (Step 7)."""
    if not os.path.exists(source):
        plan.append(f'skipped {rel} (no {os.path.basename(source)} in the '
                    f'plugin root)')
        return
    if not dry_run:
        try:
            os.symlink(source, dest)
        except OSError:
            shutil.copyfile(source, dest)
            os.chmod(dest, 0o755)
            plan.append(f'copied {source} -> {rel}')
            return
    plan.append(f'linked {rel} -> {source}')


def _report(plan, root, plugin_root, report, dry_run):
    """Step 5b: the dashboard, symlinked so it tracks plugin updates."""
    rel = 'purlin-report.html'
    dest = os.path.join(root, rel)
    if not report:
        if os.path.lexists(dest):
            plan.append(f'kept {rel} (report is off; an existing dashboard is '
                        f'never deleted)')
        else:
            plan.append(f'skipped {rel} (report is off)')
        return
    if os.path.lexists(dest):
        plan.append(f'kept {rel}')
        return
    source = os.path.join(plugin_root, 'scripts', 'report', 'purlin-report.html')
    _link_or_copy(plan, source, dest, rel, dry_run)


def _hooks(plan, root, plugin_root, git_dir, digest, dry_run):
    """Steps 7 and 7a: both hooks, never over one the project already has."""
    hooks_dir = os.path.join(git_dir, 'hooks')
    for name, script in _HOOKS:
        rel = f'.git/hooks/{name}'
        dest = os.path.join(hooks_dir, name)
        if name == 'pre-commit' and digest == 'off':
            plan.append(f'skipped {rel} (digest mode "off")')
            continue
        if os.path.lexists(dest):
            body = _slurp(hooks_dir, name)
            if 'purlin' in body:
                plan.append(f'kept {rel} (purlin hook already installed)')
            else:
                plan.append(f'kept {rel} (existing non-purlin hook preserved)')
            continue
        if not dry_run:
            os.makedirs(hooks_dir, exist_ok=True)
        _link_or_copy(plan, os.path.join(plugin_root, 'scripts', 'hooks',
                                         script), dest, rel, dry_run)


# ── invocation ────────────────────────────────────────────────────────

def _git_dir(root):
    """The repository's git directory, or None when `root` is not one."""
    try:
        result = subprocess.run(['git', 'rev-parse', '--absolute-git-dir'],
                                cwd=root, capture_output=True, text=True)
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='scaffold.py', add_help=True,
        description='Write the files purlin:init scaffolds')
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--plugin-root', default=None,
                        help='the installed Purlin plugin (default: the '
                             'directory this script ships in)')
    parser.add_argument('--test-framework', default='auto',
                        help='auto, one registry id, or a comma-separated list')
    parser.add_argument('--pre-push', choices=('warn', 'strict', 'off'),
                        default=None)
    parser.add_argument('--mutation-checks', choices=('on', 'off'), default=None)
    parser.add_argument('--remote-verification',
                        choices=('required', 'optional', 'off'), default=None)
    parser.add_argument('--report', choices=('on', 'off'), default=None)
    parser.add_argument('--digest', choices=('auto', 'warn', 'off'), default=None)
    parser.add_argument('--force', action='store_true',
                        help='re-initialize a project that already has '
                             '.purlin/config.json')
    parser.add_argument('--dry-run', action='store_true',
                        help='print the plan and write nothing')
    args = parser.parse_args(argv)

    root = os.path.abspath(args.project_root)
    plugin_root = os.path.abspath(args.plugin_root or _plugin_root())
    if not os.path.isdir(root):
        print(f'no such project root: {root}', file=sys.stderr)
        return EXIT_BAD_INVOCATION
    if not _exists(plugin_root, os.path.join('templates', 'config.json')):
        print(f'not a Purlin plugin root (no templates/config.json): '
              f'{plugin_root}', file=sys.stderr)
        return EXIT_BAD_INVOCATION

    # Step 1, before anything is read or written: without git there is no
    # provenance for a proof, a receipt or a stamp, and neither hook can run.
    git_dir = _git_dir(root)
    if git_dir is None:
        print(GIT_REQUIRED, file=sys.stderr)
        return EXIT_BAD_INVOCATION

    config_path = os.path.join(root, '.purlin', 'config.json')
    if os.path.exists(config_path) and not args.force:
        print('Project already initialized. Use --force to re-initialize.',
              file=sys.stderr)
        return EXIT_REFUSED

    registry = _frameworks(plugin_root)
    if not registry:
        print(f'the framework registry lists no plugins: '
              f'{plugin_root}/references/supported_frameworks.md',
              file=sys.stderr)
        return EXIT_BAD_INVOCATION

    requested = [part.strip() for part in args.test_framework.split(',')
                 if part.strip()]
    if requested == ['auto']:
        selected = _detect(root, registry)
    else:
        unknown = [i for i in requested
                   if i != 'other' and i not in registry]
        if unknown:
            print(f'unknown test framework: {", ".join(unknown)}',
                  file=sys.stderr)
            print(f'known ids: {", ".join(sorted(registry))}, other',
                  file=sys.stderr)
            return EXIT_BAD_INVOCATION
        selected = requested

    answers = {
        'test_framework': args.test_framework,
        'pre_push': args.pre_push,
        'remote_verification': args.remote_verification,
        'report': None if args.report is None else args.report == 'on',
        'digest': args.digest,
        'mutation_checks': (None if args.mutation_checks is None
                            else args.mutation_checks == 'on'),
    }

    plan = []
    for directory in ('.purlin', '.purlin/plugins', 'specs', 'specs/_anchors'):
        path = os.path.join(root, directory)
        if os.path.isdir(path):
            plan.append(f'kept {directory}/')
            continue
        if not args.dry_run:
            os.makedirs(path, exist_ok=True)
        plan.append(f'wrote {directory}/')

    config = _config(plan, root, plugin_root, answers, args.force, args.dry_run)
    _plugins(plan, root, plugin_root, registry, selected, args.dry_run)
    _wiring(plan, root, selected, args.dry_run)
    _gitignore(plan, root, plugin_root, args.dry_run)
    _report(plan, root, plugin_root, bool(config.get('report')), args.dry_run)
    _hooks(plan, root, plugin_root, git_dir, config.get('digest'), args.dry_run)

    for line in plan:
        print(line)
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
