#!/usr/bin/env python3
"""The mechanical half of `purlin:init`: every file a new project needs.

    python3 scripts/init/scaffold.py --project-root DIR
        [--test-framework auto|<id>[,<id>...]] [--pre-push warn|strict|off]
        [--mutation-checks on|off] [--remote-verification required|optional|off]
        [--report on|off] [--digest auto|warn|off]
        [--quality-gate off|deterministic]
        [--force] [--plugin-root DIR] [--dry-run]

`purlin:init` is the user-facing command; this script is the part of it that
must be deterministic and provable, so the skill asks the questions and this
script writes the files. It is to init what `scripts/update/migrate.py` is to
`purlin:init --update`: nothing here decides anything a user was asked about,
and nothing the skill decides is re-decided here.

WHAT IT WRITES
    .purlin/config.json     the template with the answered values and the
                            `version` stamped from VERSION. `quality_gate` is
                            the one answer the template does not carry: it is
                            written only when `--quality-gate` answers it, so
                            a project that never asked for the quality gate
                            holds exactly the template's keys
    .purlin/plugins/<file>  a byte-identical copy of each selected framework's
                            plugin from scripts/proof/
    conftest.py             the pytest wiring, jest.config.js the jest
    jest.config.js          reporter and vitest.config.ts the vitest one, each
    vitest.config.ts        written only when the project has no such file
    .gitignore              templates/gitignore.purlin, entry by entry, with
                            entries the file already carries left alone
    purlin-report.html      a symlink to the plugin's dashboard (report on)
    .purlin/hooks/pre-push  the generated shims, tracked, which find the
    .purlin/hooks/pre-commit  installed plugin and run its hook script
    .purlin/plugin-root     where this machine keeps the plugin (gitignored)
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

    `--quality-gate` keeps the same way, from the other side: it is not a
    template key, so absent it is neither answered nor backfilled. A project
    that recorded one keeps the recorded mode, and a project that never
    recorded one still has no `quality_gate` key after a re-init. That is why
    `scripts/update/migrate.py` has nothing to do for this field: it backfills
    the template's keys, and this is not one of them.

    `--test-framework` keeps with the rest. Absent, it is the project's own
    recorded value (`auto` in a project that has no config yet), so the
    framework selection a re-init resolves is the one the project already
    answered and the field is not rewritten. That is what makes a single-step
    re-answer single: `--force --pre-push strict` alone changes `pre_push` and
    nothing else, which is what `purlin:init --pre-push` needs from this script
    (`skill_init` RULE-74). A flag that defaulted to `auto` would re-detect the
    frameworks and write `auto` over the recorded answer on every such run.
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

# Directory names detection never descends into: dot directories are tool
# state, and `node_modules` is other people's code, where a vendored package's
# own Makefile or test fixtures are not this project's frameworks.
_SKIP_DIRS = ('node_modules',)

# A SQL file counts as a test only when its name says so. `tests/fixtures.sql`
# is seed data, not a test, and a project that keeps one got the sql plugin.
_SQL_TEST_NAME = re.compile(r'^(?:test_.+\.sql|.+_test\.sql|.+\.test\.sql)$')

# The registry's Detection column is prose for a reader; these are the same
# checks as code. An id here that the registry does not list is a bug, and
# `_frameworks()` raises on one rather than installing a file nobody shipped.
_DETECTORS = (
    ('pytest', lambda root: (_exists(root, 'conftest.py')
                             or '[tool.pytest' in _slurp(root, 'pyproject.toml'))),
    ('vitest', lambda root: _npm_package(root, 'vitest')),
    ('jest', lambda root: _npm_package(root, 'jest')),
    ('c', lambda root: ((_exists(root, 'Makefile')
                         or _exists(root, 'CMakeLists.txt'))
                        and _has_source(root, '.c'))),
    ('php', lambda root: (_exists(root, 'composer.json')
                          or _exists(root, 'phpunit.xml'))),
    ('sql', lambda root: any(_SQL_TEST_NAME.match(n)
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


# ── the generated hook shims (Step 7) ─────────────────────────────────
#
# A shim is what `.git/hooks/<name>` reaches, and it is tracked in git: it
# names no machine, no plugin version and no checkout, so the copy in the
# repository is correct for every clone of it. Everything machine-specific is
# resolved at run time, which is what makes the install survive a plugin
# update: the version-pinned cache path a symlink would have frozen
# (`~/.claude/plugins/cache/purlin/purlin/<version>/`) is gone the moment the
# version changes, while the registry entry below moves with it.

# The install registry step, run by the shim as an argument to python. It
# holds no single quote, because the shim passes it inside a single-quoted sh
# word. `plugins["purlin@purlin"]` is a list of entries, each carrying
# `installPath`, `version`, `lastUpdated` and usually `projectPath`.
_SHIM_REGISTRY_PY = '''import json, os, sys
path = os.path.expanduser("~/.claude/plugins/installed_plugins.json")
try:
    with open(path) as handle:
        entries = json.load(handle).get("plugins", {}).get("purlin@purlin", [])
except Exception:
    sys.exit(0)
if isinstance(entries, dict):
    entries = [entries]
entries = [e for e in entries if isinstance(e, dict)]
chosen = None
for entry in entries:
    if entry.get("projectPath") == sys.argv[1]:
        chosen = entry
        break
if chosen is None and entries:
    chosen = max(entries, key=lambda e: str(e.get("lastUpdated") or ""))
if chosen:
    print(chosen.get("installPath") or "")
'''

# What each shim does when no candidate carries its script. Neither may leave
# the hook's own contract: pre-commit never blocks a commit, and pre-push
# never passes a push it could not check in a mode that would have blocked it.
_SHIM_FALLBACK = {
    'pre-commit': '''  # This hook never blocks a commit, on any path.
  exit 0''',
    'pre-push': '''  # warn and off would have let this push through anyway; anything else
  # would have checked it, and a check that could not run is not a pass.
  PURLIN_MODE="warn"
  PURLIN_PY="$(purlin_interpreter)"
  if [ -n "$PURLIN_PY" ]; then
    PURLIN_MODE="$("$PURLIN_PY" -c '@MODE_PY@' "$PURLIN_PROJECT")"
  fi
  if [ "$PURLIN_MODE" = "warn" ] || [ "$PURLIN_MODE" = "off" ]; then
    exit 0
  fi
  echo "purlin: mode is \\"$PURLIN_MODE\\", which cannot be enforced without"
  echo "        the plugin. Blocking the push rather than passing it unchecked."
  exit 1''',
}

_SHIM_MODE_PY = '''import json, os, sys
path = os.path.join(sys.argv[1], ".purlin", "config.json")
try:
    with open(path) as handle:
        print(json.load(handle).get("pre_push", "warn"))
except Exception:
    print("unreadable")
'''

_SHIM_TEMPLATE = '''#!/bin/sh
# Purlin @NAME@ shim, generated by purlin:init (scripts/init/scaffold.py).
#
# Tracked in git on purpose: nothing below names this machine, this plugin
# version or this checkout, so the file is correct for every clone. It finds
# the installed plugin and hands the hook to that plugin's own copy of
# @SCRIPT@, which is where the behaviour lives, so a plugin update
# changes the hook without anything in the project being rewritten.
#
# The plugin root is the first of these that carries
# @SCRIPT@; a candidate that does not carry it is stepped
# over rather than ending the search:
#   1. $PURLIN_PLUGIN_ROOT
#   2. the path on the first line of .purlin/plugin-root, written by
#      purlin:init and refreshed by purlin:init --update. It names one
#      machine, so templates/gitignore.purlin excludes it
#   3. $CLAUDE_PLUGIN_ROOT
#   4. the installPath Claude Code recorded for this project in
#      ~/.claude/plugins/installed_plugins.json, which is what survives a
#      plugin update: the entry moves to the new version's directory
#   5. the project root, for a dev checkout of the framework itself
set -u

PURLIN_HOOK="@NAME@"
PURLIN_SCRIPT="@SCRIPT@"
PURLIN_PROJECT="$(git rev-parse --show-toplevel)"
PURLIN_ROOT=""
PURLIN_SEARCHED=""

purlin_interpreter() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
  elif command -v python >/dev/null 2>&1; then
    echo python
  fi
}

purlin_try() {
  [ -n "${1:-}" ] || return 0
  PURLIN_SEARCHED="$PURLIN_SEARCHED          $1
"
  if [ -z "$PURLIN_ROOT" ] && [ -f "$1/$PURLIN_SCRIPT" ]; then
    PURLIN_ROOT="$1"
  fi
}

purlin_registry_root() {
  PURLIN_PY="$(purlin_interpreter)"
  [ -n "$PURLIN_PY" ] || return 0
  "$PURLIN_PY" -c '@REGISTRY_PY@' "$PURLIN_PROJECT"
}

PURLIN_PINNED=""
if [ -f "$PURLIN_PROJECT/.purlin/plugin-root" ]; then
  PURLIN_PINNED="$(sed -n 1p "$PURLIN_PROJECT/.purlin/plugin-root")"
fi

purlin_try "${PURLIN_PLUGIN_ROOT:-}"
purlin_try "$PURLIN_PINNED"
purlin_try "${CLAUDE_PLUGIN_ROOT:-}"
if [ -z "$PURLIN_ROOT" ]; then
  purlin_try "$(purlin_registry_root)"
fi
purlin_try "$PURLIN_PROJECT"

if [ -z "$PURLIN_ROOT" ]; then
  echo "purlin: WARNING: the Purlin plugin was not found, so the $PURLIN_HOOK"
  echo "        hook did not run. Searched for $PURLIN_SCRIPT under:"
  printf "%s" "$PURLIN_SEARCHED"
  echo "        Set PURLIN_PLUGIN_ROOT, or write the plugin directory into"
  echo "        .purlin/plugin-root, to fix this."
@FALLBACK@
fi

# The interpreter resolver, once the plugin that ships it has been found.
if [ -f "$PURLIN_ROOT/scripts/purlin_python.sh" ]; then
  . "$PURLIN_ROOT/scripts/purlin_python.sh"
fi

exec "$PURLIN_ROOT/$PURLIN_SCRIPT" "$@"
'''

# Three lines, in the repository's hooks directory, which is the one place
# git looks and the one place a project may already have a hook of its own.
_DELEGATOR_MARKER = 'purlin-delegator'
_DELEGATOR = ('#!/bin/sh\n'
              '# purlin-delegator (purlin:init): the hook body is '
              '.purlin/hooks/@NAME@, tracked in git.\n'
              'exec "$(git rev-parse --show-toplevel)/.purlin/hooks/@NAME@"'
              ' "$@"\n')


def _shim(name, script):
    """The generated shim for one hook, as text."""
    fallback = _SHIM_FALLBACK[name].replace('@MODE_PY@', _SHIM_MODE_PY)
    return (_SHIM_TEMPLATE
            .replace('@REGISTRY_PY@', _SHIM_REGISTRY_PY)
            .replace('@FALLBACK@', fallback)
            .replace('@SCRIPT@', script)
            .replace('@NAME@', name))


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


def _npm_package(root, name):
    """True when `package.json` declares `name` as a dependency.

    A substring search over the file's text called every project whose
    package.json merely mentioned the word a project of that framework: a
    vitest project whose `description` says "migrated off jest" got the jest
    plugin too. The dependency maps are parsed and the key looked up, and a
    `<name>.config.*` file beside the manifest counts as the same answer.
    """
    text = _slurp(root, 'package.json')
    if text:
        try:
            data = json.loads(text)
        except ValueError:
            data = None
        if isinstance(data, dict):
            for section in ('dependencies', 'devDependencies'):
                deps = data.get(section)
                if isinstance(deps, dict) and name in deps:
                    return True
    return any(n.startswith(name + '.config.') for n in _listdir(root, '.'))


def _has_source(root, suffix):
    """True when some file under `root` ends in `suffix`.

    A build file alone is not a language: `Makefile` is how a Python or a Go
    project spells its task runner just as often as it is how a C project
    builds. Dot directories and `node_modules` are skipped (`_SKIP_DIRS`).
    """
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith('.') and d not in _SKIP_DIRS)
        if any(n.endswith(suffix) for n in filenames):
            return True
    return False


def _write(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def _existing_config(root):
    """The project's current `.purlin/config.json`, or None.

    None means absent or not a readable JSON object, which are the two cases
    with no answers to keep.
    """
    rel = os.path.join('.purlin', 'config.json')
    if not os.path.exists(os.path.join(root, rel)):
        return None
    try:
        value = json.loads(_slurp(root, rel))
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


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


def _search_roots(root):
    """The project root and the package directories under it.

    A monorepo keeps its `conftest.py` and its `package.json` in
    `packages/api/` and `packages/web/`, not at the root, so a root-only
    search reported "no framework detected" for every project that has more
    than one. The two levels below the root are the shape every monorepo tool
    lays down (`packages/*`, `apps/*`, `services/*`); deeper is a source tree,
    not a package boundary. Dot directories and `node_modules` are skipped
    (`_SKIP_DIRS`) and the order is sorted, so the framework list a project
    gets does not depend on the order the filesystem hands back.
    """
    out = [root]
    for name in _listdir(root, '.'):
        if name.startswith('.') or name in _SKIP_DIRS:
            continue
        child = os.path.join(root, name)
        if not os.path.isdir(child):
            continue
        out.append(child)
        for sub in _listdir(child, '.'):
            if sub.startswith('.') or sub in _SKIP_DIRS:
                continue
            if os.path.isdir(os.path.join(child, sub)):
                out.append(os.path.join(child, sub))
    return out


def _detect(root, known):
    ids = []
    bases = _search_roots(root)
    for framework_id, test in _DETECTORS:
        if framework_id not in known:
            raise KeyError(f'{framework_id} is not in the framework registry')
        if any(test(base) for base in bases):
            ids.append(framework_id)
    return ids


# ── the steps ─────────────────────────────────────────────────────────

def _config(plan, root, plugin_root, answers, existing, force, dry_run):
    """Step 2: the template, the answers, and `version` from VERSION.

    `existing` is `_existing_config(root)`, read once in `main` because the
    framework selection needs the same answers this writes.
    """
    template = json.loads(_slurp(plugin_root, os.path.join('templates',
                                                           'config.json')))
    path = os.path.join(root, '.purlin', 'config.json')
    base = {}
    if os.path.exists(path) and force:
        if existing is None:
            plan.append('wrote .purlin/config.json (the existing file was not '
                        'readable JSON; rewritten from the template)')
        else:
            base = existing
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


def _generated(plan, path, rel, body, dry_run, mode=None):
    """A file whose bytes this script owns, written only when they differ.

    Not `kept` the way a project's own file is kept: these are generated, so a
    stale one is refreshed rather than preserved. Writing identical bytes would
    make every single-step re-answer report a write it did not make (RULE-74).
    """
    if os.path.isfile(path) and not os.path.islink(path):
        try:
            with open(path, encoding='utf-8') as f:
                current = f.read()
        except (IOError, OSError, UnicodeDecodeError):
            current = None
        if current == body:
            plan.append(f'kept {rel}')
            return
    if not dry_run:
        _write(path, body)
        if mode is not None:
            os.chmod(path, mode)
    plan.append(f'wrote {rel}')


def _plugin_root_file(plan, root, plugin_root, dry_run):
    """`.purlin/plugin-root`: where this machine keeps the installed plugin.

    The shims read it as their second candidate. It is gitignored because it
    is the one thing about the install that is true of one machine only.
    """
    _generated(plan, os.path.join(root, '.purlin', 'plugin-root'),
               '.purlin/plugin-root', plugin_root + '\n', dry_run)


def _hooks(plan, root, plugin_root, git_dir, digest, dry_run):
    """Steps 7 and 7a: the tracked shims, then the hook git itself runs."""
    hooks_dir = os.path.join(git_dir, 'hooks')
    for name, script in _HOOKS:
        rel = f'.git/hooks/{name}'
        shim_rel = f'.purlin/hooks/{name}'
        dest = os.path.join(hooks_dir, name)
        if name == 'pre-commit' and digest == 'off':
            plan.append(f'skipped {shim_rel} (digest mode "off")')
            plan.append(f'skipped {rel} (digest mode "off")')
            continue
        _generated(plan, os.path.join(root, '.purlin', 'hooks', name),
                   shim_rel, _shim(name, f'scripts/hooks/{script}'), dry_run,
                   mode=0o755)
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
    parser.add_argument('--test-framework', default=None,
                        help='auto, one registry id, or a comma-separated list '
                             "(default: the project's own recorded value, or "
                             'auto when it has no config yet)')
    parser.add_argument('--pre-push', choices=('warn', 'strict', 'off'),
                        default=None)
    parser.add_argument('--mutation-checks', choices=('on', 'off'), default=None)
    parser.add_argument('--remote-verification',
                        choices=('required', 'optional', 'off'), default=None)
    parser.add_argument('--report', choices=('on', 'off'), default=None)
    parser.add_argument('--digest', choices=('auto', 'warn', 'off'), default=None)
    parser.add_argument('--quality-gate', choices=('off', 'deterministic'),
                        default=None,
                        help='the project-policy quality gate scripts/ci/'
                             'verify_gate.py reads (default: unanswered, and '
                             'an unanswered field is not written)')
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

    # Absent, `--test-framework` is the project's own recorded answer, so a
    # single-step re-answer (`--force --pre-push strict` alone) resolves the
    # frameworks the project already chose and leaves the field alone. A
    # non-string recorded value is no answer at all and falls back to `auto`.
    existing = _existing_config(root) if args.force else None
    recorded = (existing or {}).get('test_framework')
    framework_spec = args.test_framework
    if framework_spec is None:
        framework_spec = recorded if isinstance(recorded, str) else 'auto'

    requested = [part.strip() for part in framework_spec.split(',')
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
        # Not a template key. `None` here means unanswered, and `_config`
        # writes no key for an unanswered answer, so a project that never
        # asked for the quality gate holds exactly the template's keys and
        # `scripts/update/migrate.py` has nothing to backfill (RULE-75).
        'quality_gate': args.quality_gate,
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

    config = _config(plan, root, plugin_root, answers, existing, args.force,
                     args.dry_run)
    _plugins(plan, root, plugin_root, registry, selected, args.dry_run)
    _wiring(plan, root, selected, args.dry_run)
    _gitignore(plan, root, plugin_root, args.dry_run)
    _report(plan, root, plugin_root, bool(config.get('report')), args.dry_run)
    _plugin_root_file(plan, root, plugin_root, args.dry_run)
    _hooks(plan, root, plugin_root, git_dir, config.get('digest'), args.dry_run)

    for line in plan:
        print(line)
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
