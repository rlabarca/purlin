#!/usr/bin/env python3
"""purlin:init: one question, then every file a project needs.

    scaffold.py [--update] [--project-root DIR] [--plugin-root DIR] [--yes]

Init asks one question, and nothing about how the tests run:

    Commit the files setup wrote? [y/N], only once it wrote or changed a
      file git does not ignore

It writes, in this order and naming every one in the summary: `.purlin/` and
`specs/`, the settings file, the `.gitignore` block, `.purlin/evidence/` with
its README, and the dashboard. The settings file holds `version`, the
plugin's `VERSION` file, and `tests`, an empty list where the project carried
none: the first test run suggests the command. Nothing is written into the
project's test suite or its test runner's configuration, and no git hook is
installed. On `y`, `yes` or `--yes` it commits exactly the files it wrote, in
one commit. It ends on the lines `purlin:status` ends on for the project as
it now is.

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
_MCP = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP not in sys.path:
    sys.path.insert(0, _MCP)

import config_engine                                          # noqa: E402
from purlin import (console as console_module,                # noqa: E402
                    status as status_module)

EXIT_OK = 0
EXIT_UNREADABLE_SETTINGS = 1
EXIT_BAD_INVOCATION = 2

NOT_A_REPOSITORY = ('This is not a git repository. Run git init, then '
                    'purlin:init.')

# Setup asks whether it may commit what it wrote, and commits only that.
COMMIT_QUESTION = 'Commit the files setup wrote?'
COMMIT_SUBJECT = 'chore(init): set up Purlin'
COMMITTED = 'Committed %s, the files setup wrote:'
NOT_COMMITTED = ('The files setup wrote are staged and not committed: %s.')

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


def is_repository(root):
    """True when `root` is inside a git checkout.

    Everything init writes lands in the tree, so this is the one thing git
    has to answer before it writes any of it.
    """
    ok, top = _git(root, 'rev-parse', '--show-toplevel')
    return bool(ok and top)


# --- Asking, and writing ---------------------------------------------------

def yes_or_no(question):
    """The answer to a question whose default is no, lower-cased.

    The question and `[y/N] ` are one line, and the answer is read on it.
    Reading stdin rather than testing for a terminal lets a script pipe its
    answer in, and end of input is the default, so a run with nothing on
    stdin answers no rather than hanging.
    """
    try:
        return input('%s [y/N] ' % question).strip().lower()
    except EOFError:
        return ''


class Plan(object):
    """Every write, as one line, in the order the summary prints it.

    Each path is named once, and `files` holds every file written or
    changed, in the order it was first named.
    """

    def __init__(self, root):
        self.root = root
        self.lines = []
        self.named = {}
        self.files = []

    def skip(self, what, why):
        self.lines.append('skipped %s (%s)' % (what, why))

    def name(self, word, rel, line=None):
        """The line naming `rel`, once, however often it is written."""
        line = line or '%s %s' % (word, rel)
        if rel in self.named:
            at = self.named[rel]
            if word != 'kept':
                self.lines[at] = line
        else:
            self.named[rel] = len(self.lines)
            self.lines.append(line)
        if word != 'kept' and not rel.endswith('/') and rel not in self.files:
            self.files.append(rel)

    def directory(self, rel):
        path = os.path.join(self.root, rel)
        if os.path.isdir(path):
            return self.name('kept', rel + '/')
        os.makedirs(path, exist_ok=True)
        self.name('wrote', rel + '/')

    def write(self, rel, text, own=False, source=None, exact=False):
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
                return self.name('kept', rel)
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        if exact:
            with open(path, 'wb') as handle:
                handle.write(text)
        else:
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write(text)
        if source:
            self.name('copied', rel, 'copied %s to %s' % (source, rel))
        else:
            self.name('wrote', rel)

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
            return self.name('kept', rel)
        if current:
            current = current.rstrip('\n') + '\n\n'
        self.write(rel, current + block, own=True)


# --- The steps -------------------------------------------------------------

def write_config(plan, plugin_root, existing):
    """`.purlin/config.json`, holding exactly `version` and `tests`.

    `version` is the plugin's `VERSION` file. `tests` is the setting the
    project already carries, kept as it is, or the template's empty list.
    """
    template = json.loads(_read(plugin_root, 'templates', 'config.json'))
    written = (existing or {}).get('tests')
    config = {'version': _read(plugin_root, 'VERSION').strip(),
              'tests': written if isinstance(written, list)
              else template['tests']}
    plan.write('.purlin/config.json', json.dumps(config, indent=2) + '\n',
               own=True)
    return config


def write_gitignore(plan, plugin_root):
    """templates/gitignore.purlin, appended once and guarded by its first entry."""
    plan.append('.gitignore',
                _read(plugin_root, 'templates', 'gitignore.purlin'),
                '.purlin/runtime/')


def write_evidence(plan, plugin_root):
    """`.purlin/evidence/` and the README that says what the folder holds.

    The README is handed over as bytes, so it is the file the plugin ships
    on every system: text mode on Windows would end each line in two bytes.
    """
    plan.directory(EVIDENCE_DIR)
    plan.write(EVIDENCE_DIR + '/README.md',
               _read_bytes(plugin_root, EVIDENCE_README), exact=True)


def git_message(done):
    """Git's own words for a command that failed.

    The first line starting `fatal:` or `error:`, with that word cut;
    otherwise the first line printed; the closing stop cut, since the line
    that carries it adds its own.
    """
    lines = [line.strip() for text in (done.stderr, done.stdout)
             for line in str(text or '').splitlines() if line.strip()]
    for line in lines:
        if line.startswith(('fatal: ', 'error: ')):
            return line.split(': ', 1)[1].rstrip('.')
    if lines:
        return lines[0].rstrip('.')
    return 'git exited with %d' % done.returncode


def _git_run(root, *args):
    try:
        return subprocess.run(['git'] + list(args), cwd=root,
                              capture_output=True, text=True)
    except (OSError, subprocess.SubprocessError) as error:
        return subprocess.CompletedProcess(args, 1, '', str(error))


def to_commit(root, written):
    """The files setup wrote or changed that git does not ignore, in the
    order setup named them: the ones git sees as new or changed."""
    if not written:
        return []
    ignored = _git_run(root, 'check-ignore', '--no-index', '--', *written)
    skip = set(ignored.stdout.splitlines())
    status = subprocess.run(
        ['git', 'status', '--porcelain', '-z', '--untracked-files=all',
         '--'] + [rel for rel in written if rel not in skip],
        cwd=root, capture_output=True)
    seen = {entry[3:].decode('utf-8', 'replace')
            for entry in status.stdout.split(b'\0') if len(entry) > 3}
    return [rel for rel in written if rel not in skip and rel in seen]


def commit(root, paths):
    """One commit of exactly `paths`; another file staged stays staged."""
    done = _git_run(root, 'add', '--', *paths)
    if done.returncode == 0:
        done = _git_run(root, 'commit', '-q', '-m', COMMIT_SUBJECT,
                        '--', *paths)
    if done.returncode != 0:
        print(NOT_COMMITTED % git_message(done))
        return
    ok, sha = _git(root, 'rev-parse', 'HEAD')
    print(COMMITTED % sha[:7])
    for rel in paths:
        print('  %s' % rel)


def next_step(root):
    """How the project stands now: the lines `purlin:status` ends on.

    That is the summary and `Left to do`, whose first line is the next step.
    A project with no spec yet has neither, and ends on the two lines every
    surface prints for it.
    """
    try:
        report = status_module.sync_status(root)
    except Exception:                                          # noqa: BLE001
        return status_module.no_spec_lines(root)
    no_spec = status_module.no_spec_lines(root)
    if report == '\n'.join(no_spec):
        return no_spec
    # The report ends on its last block, after the one blank line before it.
    return report.rsplit('\n\n', 1)[-1].splitlines()


# --- Invocation ------------------------------------------------------------

def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog='scaffold.py', description='Set a project up for Purlin')
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--plugin-root', default=None)
    for flag in ('--update', '--yes'):
        parser.add_argument(flag, action='store_true')
    return parser.parse_args(argv)


def delegate_update(args):
    """`--update` belongs to scripts/init/update.py, which owns the upgrade."""
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
    import update                                              # noqa: PLC0415
    return update.main(['--project-root', args.project_root]
                       + (['--yes'] if args.yes else []))


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

    plan = Plan(root)
    for name in ('.purlin', 'specs'):
        plan.directory(name)
    write_config(plan, plugin_root, _existing_config(root))
    write_gitignore(plan, plugin_root)
    write_evidence(plan, plugin_root)
    plan.copy(os.path.join(plugin_root, 'scripts', 'report',
                           'purlin-report.html'), 'purlin-report.html')
    for line in plan.lines:
        print(line)

    # The one question: whether setup may commit what it wrote. `--yes`
    # answers yes without asking.
    paths = to_commit(root, plan.files)
    if paths and (args.yes or yes_or_no(COMMIT_QUESTION) in ('y', 'yes')):
        commit(root, paths)

    print('')
    for line in next_step(root):
        print(line)
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
