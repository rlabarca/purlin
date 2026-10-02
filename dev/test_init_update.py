"""Proofs for `scripts/init/update.py`, the edits `purlin:init --update` makes.

Every case here drives the real script against a real git repository made from
the v0.9.5 upgrade fixture, never against a hand-built expectation of what the
script would do, so the script and these proofs cannot drift apart. The fixture
itself is frozen: each test copies it into a temporary directory and runs
`git init` there, then writes by hand whatever that layout does not carry.

What each group proves:

*pending*     what the update finds in the old layout, and the root it refuses
*applying*    `--yes` applies every migration, a second run finds nothing, and
              a declined migration stays pending
*backups*     every changed file is kept as it was under one ignored folder
*hooks*       the pre-commit and pre-push hooks v0.9.5 installed go
*commit*      one commit, naming the migrations it carries
*status*      `sync_status` says to run the update while anything is pending
*tests*       the `tests` setting written from the frameworks 0.9.5 named
*markers*     each 0.9.5 marker becomes a comment above the same test
*plugins*     the wiring that loaded the plugin copies goes
*config*      the file that is left holds `version` and `tests` alone
*refusals*    what stops the update, and a commit git refuses
*specs*       the lines 0.9.5 wrote into a spec that this release does not read
*files*       the files 0.9.5 kept that this release does not use
*evidence*    `.purlin/evidence/` and its README, and the dashboard page
*lettered*    a proof 0.9.5 numbered with a letter takes a number of its own
*commands*    the command proposed for each test tool, and the owner's own
*output*      one line of totals for each migration, each file's line in the
              log, the lines that need the owner last
*questions*   each on its own line, `--apply` and `--test-command`
*leftovers*   what the update leaves for the owner, and the old record
*titles*      a title tag in the shapes a real project writes it, and the
              read-back with the test run's own reader
"""

import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
UPDATE = os.path.join(ROOT, 'scripts', 'init', 'update.py')
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'init'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import update  # noqa: E402
from purlin import frameworks  # noqa: E402
from purlin import status as status_module  # noqa: E402

V095 = 'upgrade-0.9.5'

# The files 0.9.5 committed beside a spec, which the upgrade removes.
LEFTOVER = ('*.proofs-*.json', '*.receipt.json')

# The pre-commit and pre-push hooks v0.9.5 installed under `.git/hooks/`, as
# its `scripts/hooks/` copies open. A fixture carries no `.git/`, so a hooks
# case writes them.
OLD_PRE_COMMIT = ('#!/usr/bin/env bash\n'
                  '# Purlin pre-commit hook: project digest auto-generation.\n')
OLD_PRE_PUSH = ('#!/usr/bin/env bash\n'
                '# Purlin pre-push hook: proof coverage check.\n')

VERSION = open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip()
NOTHING_PENDING = 'Nothing is pending: this project is at %s.' % VERSION

ON_WINDOWS = pytest.mark.skipif(
    os.name != 'nt', reason='only a Windows machine can show it')

# --- building a project to run against --------------------------------------

def _git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root,
                          capture_output=True, text=True)


def _project(tmp_path, layout, remote=True):
    """One upgrade fixture, copied to a temporary directory and committed.

    A bare repository beside it stands in for the git host. The update checks
    the same prerequisites init does before it writes a workflow: a remote,
    and a host it knows. The directory name carries the host, so the checks
    are answered on disk with no network.
    """
    root = os.path.join(str(tmp_path), layout)
    shutil.copytree(os.path.join(DEV, 'fixtures', layout), root)
    os.rename(os.path.join(root, '_gitignore'),
              os.path.join(root, '.gitignore'))
    _git(root, '-c', 'init.defaultBranch=main', 'init', '-q')
    _git(root, 'config', 'user.name', 'Test Person')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'commit.gpgsign', 'false')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'init')
    if remote:
        url = os.path.join(str(tmp_path), 'github-origin.git')
        _git(str(tmp_path), 'init', '--bare', '-q', '-b', 'main', url)
        _git(root, 'remote', 'add', 'origin', url)
        _git(root, 'push', '-q', '-u', 'origin', 'main')
    return root


def _read(root, rel):
    with open(os.path.join(root, rel), 'r', encoding='utf-8') as handle:
        return handle.read()


def _write(root, rel, text):
    path = os.path.join(root, rel)
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def _read_bytes(root, rel):
    with open(os.path.join(root, rel), 'rb') as handle:
        return handle.read()


def _write_bytes(root, rel, data):
    """`data` exactly, with no line ending turned into another on any system."""
    path = os.path.join(root, rel)
    folder = os.path.dirname(path)
    if not os.path.isdir(folder):
        os.makedirs(folder)
    with open(path, 'wb') as handle:
        handle.write(data)


def _tracked(root):
    return _git(root, 'ls-files').stdout.split()


# Where the update keeps each file it changes, as it was before the run.
BACKUPS = '.purlin/runtime/update-backup'
BACKUPS_LINE = ('Every file the update changed is kept as it was under '
                '.purlin/runtime/update-backup/, with each change listed in '
                'update.log there. Delete the folder once the tests pass.')
LOG = BACKUPS + '/update.log'


def _walk(root, patterns, skip_backups=True):
    """Every project-relative path whose name matches one of `patterns`,
    the folder of backups left out unless asked for."""
    hits = []
    for dirpath, dirs, names in os.walk(root):
        if '.git' in dirs:
            dirs.remove('.git')
        for name in names:
            rel = os.path.relpath(os.path.join(dirpath, name), root)
            rel = rel.replace(os.sep, '/')
            if skip_backups and rel.startswith(BACKUPS + '/'):
                continue
            if any(fnmatch.fnmatch(name, p) for p in patterns):
                hits.append(rel)
    return sorted(hits)


def _backups(root):
    """`{file: the bytes of its backup}` for every backup the update kept."""
    held = {}
    for rel in _walk(root, ('*',), skip_backups=False):
        if rel.startswith(BACKUPS + '/') and rel != LOG:
            held[rel[len(BACKUPS) + 1:]] = _read_bytes(root, rel)
    return held


def _log(root):
    """The lines of the update's log, each without the space around it."""
    return [line.strip() for line in _read(root, LOG).splitlines()]


def _answers(monkeypatch, rules=(), default='y'):
    """Answer each question by what it asks, not by the order it is asked in.

    `rules` is a list of `(substring, reply)` pairs; the first substring the
    prompt carries decides the reply, and anything else gets `default`. The
    returned list collects every prompt, so a test can assert one was asked.
    """
    asked = []

    def fake_input(prompt=''):
        asked.append(prompt)
        for needle, reply in rules:
            if needle in prompt:
                return reply
        return default

    monkeypatch.setattr('builtins.input', fake_input)
    return asked


def _apply(root, argv=('--yes',)):
    return update.main(list(argv) + ['--project-root', root])


def _ids(root):
    return [item['id'] for item in update.pending(root)]


def _config(root):
    return json.loads(_read(root, '.purlin/config.json'))


def _set_config(root, **values):
    config = _config(root)
    config.update(values)
    _write(root, '.purlin/config.json', json.dumps(config, indent=2))




# --- what a project still needs ---------------------------------------------

# The migrations the v0.9.5 fixture needs, in the order they are applied.
NINE = ['design-refs', 'anchor-lines', 'os-tags', 'kind-tags',
        'untracked-files', 'config', 'evidence', 'workflows', 'plugins']


# purlin: update PROOF-2
def test_the_v095_layout_needs_the_nine_migrations_in_order(tmp_path):
    root = _project(tmp_path, V095)
    assert not os.listdir(os.path.join(root, '.git', 'hooks')) or not [
        name for name in os.listdir(os.path.join(root, '.git', 'hooks'))
        if not name.endswith('.sample')]
    assert _ids(root) == NINE


# purlin: update PROOF-68
def test_a_pre_commit_hook_v095_installed_adds_the_hook_migration(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, '.git/hooks/pre-commit', OLD_PRE_COMMIT)
    assert _ids(root) == ['design-refs', 'anchor-lines', 'os-tags',
                          'kind-tags', 'untracked-files', 'hooks', 'config',
                          'evidence', 'workflows', 'plugins']


# --- applying ----------------------------------------------------------------

# purlin: update PROOF-5
def test_yes_asks_nothing_and_leaves_nothing_pending(tmp_path, capsys,
                                                     monkeypatch):
    root = _project(tmp_path, V095)
    asked = _answers(monkeypatch)
    assert _apply(root) == 0
    capsys.readouterr()
    assert asked == []
    assert update.pending(root) == []


def _twice(tmp_path, capsys):
    """`(the second run's exit code and lines, HEAD and git status before it,
    the same after it)` for the sample updated with `--yes` twice."""
    root = _project(tmp_path, V095)
    _apply(root)
    before = (_git(root, 'rev-parse', 'HEAD').stdout,
              _git(root, 'status', '--porcelain').stdout)
    capsys.readouterr()
    code = _apply(root)
    printed = capsys.readouterr().out.splitlines()
    after = (_git(root, 'rev-parse', 'HEAD').stdout,
             _git(root, 'status', '--porcelain').stdout)
    return code, printed, before, after


# purlin: update PROOF-33
def test_a_second_run_finds_nothing_and_changes_nothing(tmp_path, capsys):
    code, printed, before, after = _twice(tmp_path, capsys)
    assert code == 0
    assert NOTHING_PENDING in printed, printed
    assert after == before


# purlin: update PROOF-117
@ON_WINDOWS
def test_on_windows_a_second_run_finds_nothing_and_changes_nothing(
        tmp_path, capsys):
    code, printed, before, after = _twice(tmp_path, capsys)
    assert code == 0
    assert [line for line in printed
            if line.startswith('Nothing is pending')], printed
    assert after == before


# purlin: update PROOF-6
def test_each_declined_migration_is_skipped_and_left_pending(
        tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    before = _ids(root)
    tree = _git(root, 'status', '--porcelain').stdout
    asked = _answers(monkeypatch, default='n')
    assert _apply(root, argv=()) == 0
    printed = capsys.readouterr().out
    assert [prompt.split(',')[0] for prompt in asked] == [
        'Apply %s' % migration_id for migration_id in before]
    for migration_id in before:
        assert '  skipped %s\n' % migration_id in printed, migration_id
    assert _git(root, 'status', '--porcelain').stdout == tree
    assert _ids(root) == before


# purlin: update PROOF-70
def test_one_declined_migration_does_not_stop_the_others(tmp_path, capsys,
                                                         monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Apply plugins', 'n')])
    _apply(root, argv=())
    capsys.readouterr()
    assert _ids(root) == ['plugins']


# --- backups -----------------------------------------------------------------

def _backed_up(tmp_path, capsys):
    """`(root, every file's bytes before the run, every backup after it,
    the lines printed)`."""
    root = _project(tmp_path, V095)
    before = {}
    for rel in _walk(root, ('*',)):
        before[rel] = _read_bytes(root, rel)
    _apply(root)
    return root, before, _backups(root), capsys.readouterr().out.splitlines()


# purlin: update PROOF-7
# purlin: update PROOF-195
def test_every_backup_keeps_its_file_s_path_under_one_folder(tmp_path,
                                                             capsys):
    root, before, backups, printed = _backed_up(tmp_path, capsys)
    assert '.purlin/config.json' in backups, sorted(backups)
    assert '.gitignore' in backups, sorted(backups)
    assert any(rel.startswith('specs/') and rel.endswith('.md')
               for rel in backups), sorted(backups)
    for rel in backups:
        assert rel in before, rel
    assert BACKUPS_LINE in printed, printed
    assert not _walk(root, ('*.bak',), skip_backups=False)


# purlin: update PROOF-71
def test_every_backed_up_file_keeps_its_bytes_from_before_the_run(tmp_path,
                                                                  capsys):
    _root, before, backups, _printed = _backed_up(tmp_path, capsys)
    assert backups
    for rel, data in backups.items():
        assert data == before[rel], rel


# purlin: update PROOF-118
@ON_WINDOWS
def test_on_windows_every_backup_keeps_the_bytes_from_before(tmp_path,
                                                             capsys):
    _root, before, backups, _printed = _backed_up(tmp_path, capsys)
    assert backups
    for rel, data in backups.items():
        assert data == before[rel], rel


# --- hooks -------------------------------------------------------------------

LINT_STAGED = '#!/bin/sh\nexec ./node_modules/.bin/lint-staged\n'


def _hooks(tmp_path, pre_commit, pre_push):
    """The sample project with these two hooks under `.git/hooks/`."""
    root = _project(tmp_path, V095)
    _write(root, '.git/hooks/pre-commit', pre_commit)
    _write(root, '.git/hooks/pre-push', pre_push)
    return root


# purlin: update PROOF-9
def test_the_hooks_v0_9_5_installed_go(tmp_path):
    root = _hooks(tmp_path, OLD_PRE_COMMIT, OLD_PRE_PUSH)
    assert [item['files'] for item in update.pending(root)
            if item['id'] == 'hooks'] == [['.git/hooks/pre-commit',
                                           '.git/hooks/pre-push']]
    _apply(root)
    for name in ('pre-commit', 'pre-push'):
        assert not os.path.exists(os.path.join(root, '.git', 'hooks', name))
    assert 'hooks' not in _ids(root)


# purlin: update PROOF-76
def test_a_lint_staged_hook_beside_the_old_pre_push_is_left_alone(tmp_path):
    root = _hooks(tmp_path, LINT_STAGED, OLD_PRE_PUSH)
    _apply(root)
    folder = os.path.join(root, '.git', 'hooks')
    assert not os.path.exists(os.path.join(folder, 'pre-push'))
    assert _read(folder, 'pre-commit') == LINT_STAGED


# --- the commit --------------------------------------------------------------

# purlin: update PROOF-18
def test_one_commit_carries_every_migration_id(tmp_path):
    root = _project(tmp_path, V095)
    assert len(_git(root, 'log', '--format=%s').stdout.splitlines()) == 1
    applied = _ids(root)
    _apply(root)
    log = _git(root, 'log', '--format=%s').stdout.splitlines()
    assert len(log) == 2, log
    assert log[0] == 'chore(update): migrate to %s (%s)' % (
        VERSION, ', '.join(applied))


# purlin: update PROOF-89
def test_nothing_is_left_uncommitted(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    assert _backups(root), 'the backups should be on disk'
    assert _git(root, 'status', '--porcelain',
                '--untracked-files=all').stdout == ''


# purlin: update PROOF-90
def test_a_run_that_applies_nothing_writes_no_commit(tmp_path, capsys,
                                                     monkeypatch):
    root = _project(tmp_path, V095)
    head = _git(root, 'rev-parse', 'HEAD').stdout.strip()
    _answers(monkeypatch, default='n')
    _apply(root, argv=())
    capsys.readouterr()
    assert _git(root, 'rev-parse', 'HEAD').stdout.strip() == head


# --- the line sync_status prints ---------------------------------------------

UPDATE_LINE = '→ Run: purlin:init --update'


# purlin: update PROOF-19
def test_status_says_it_for_a_project_that_has_not_updated(tmp_path):
    root = _project(tmp_path, V095)
    assert UPDATE_LINE in status_module.sync_status(root).splitlines()


# purlin: update PROOF-91
def test_status_stops_saying_it_once_the_old_project_has_updated(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    assert 'Run: purlin:init --update' not in status_module.sync_status(root)


# --- the tests setting ---------------------------------------------------------

# purlin: update PROOF-21
def test_a_framework_the_tree_cannot_run_is_dropped(tmp_path, capsys):
    """An older release wrote down every plugin it shipped, runnable or not."""
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    assert _config(root)['test_framework'] == 'pytest,jest,shell,vitest'
    _apply(root)
    printed = [line.strip() for line in capsys.readouterr().out.splitlines()]
    assert _config(root)['tests'] == [frameworks.entry_for('pytest')]
    for name in ('jest', 'shell', 'vitest'):
        assert ('dropped %s from the tests: nothing in the tree runs it'
                % name) in printed, printed
    assert 'config: wrote the tests setting: pytest' in printed, printed


# purlin: update PROOF-94
def test_xunit_is_read_as_dotnet(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write(root, 'App.Tests/App.Tests.csproj',
           '<Project><ItemGroup><PackageReference Include="xunit" '
           'Version="2.9.0" /></ItemGroup></Project>\n')
    _set_config(root, test_framework='xunit')
    _apply(root)
    printed = capsys.readouterr().out
    assert _config(root)['tests'] == [frameworks.entry_for('dotnet')]
    assert '  config: wrote the tests setting: dotnet\n' in printed
    assert 'from the tests' not in printed


OWN_TESTS = [{'name': 'pytest', 'run': 'pytest -q tests',
              'report': 'report.xml', 'format': 'junit',
              'files': ['tests/**/*.py']}]


# purlin: update PROOF-97
def test_a_tests_setting_already_written_is_kept(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _set_config(root, tests=OWN_TESTS)
    assert 'config' in _ids(root)
    _apply(root)
    printed = capsys.readouterr().out
    assert _config(root)['tests'] == OWN_TESTS
    assert 'from the tests' not in printed


# --- the markers -------------------------------------------------------------
# What v0.9.5's plugins read, written the way
# `git show v0.9.5:scripts/proof/<plugin>` parses it.

OLD_PYTEST = (
    'import pytest\n\n'
    '@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'
    'def test_accepts():\n    assert True\n\n\n'
    'class TestLogin:\n'
    '    @pytest.mark.proof("login", "PROOF-2", "RULE-2", tier="integration")\n'
    '    @pytest.mark.parametrize("x", [1])\n'
    '    def test_refuses(self, x):\n        assert x\n')
NEW_PYTEST = (
    'import pytest\n\n'
    '# purlin: login PROOF-1\n'
    'def test_accepts():\n    assert True\n\n\n'
    'class TestLogin:\n'
    '    # purlin: login PROOF-2\n'
    '    @pytest.mark.parametrize("x", [1])\n'
    '    def test_refuses(self, x):\n        assert x\n')
OLD_SHELL = (
    '#!/usr/bin/env bash\n'
    'source .purlin/plugins/purlin-proof.sh\n'
    'purlin_proof "login" "PROOF-1" "RULE-1" pass "accepts"\n'
    'purlin_proof_finish\n')
NEW_SHELL = (
    '#!/usr/bin/env bash\n'
    '# purlin: login PROOF-1\n'
    ':\n:\n:\n')


def _rewritten(tmp_path, capsys, rel, old):
    """The sample project with one file 0.9.5 marked, updated with `--yes`."""
    root = _project(tmp_path, V095)
    # Exactly the line feeds it is given, on every system.
    _write_bytes(root, rel, old.encode('utf-8'))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the tests 0.9.5 marked')
    _apply(root)
    return root, capsys.readouterr().out.splitlines()


# purlin: update PROOF-29
def test_the_two_pytest_marks_become_comments(tmp_path, capsys):
    root, printed = _rewritten(tmp_path, capsys, 'tests/test_login.py',
                               OLD_PYTEST)
    assert _read(root, 'tests/test_login.py') == NEW_PYTEST
    assert '  markers: rewrote 2 markers in 1 file' in printed, printed
    assert ('rewrote 2 markers in tests/test_login.py as comments'
            in _log(root)), _log(root)


# purlin: update PROOF-168
def test_a_mark_naming_a_feature_with_a_hyphen_becomes_a_comment(tmp_path,
                                                                 capsys):
    old = ('import pytest\n\n\n'
           '@pytest.mark.proof("sample-age", "PROOF-1", "RULE-1")\n'
           'def test_age():\n    pass\n')
    root, printed = _rewritten(tmp_path, capsys, 'tests/test_age.py', old)
    assert _read(root, 'tests/test_age.py') == (
        'import pytest\n\n\n'
        '# purlin: sample-age PROOF-1\n'
        'def test_age():\n    pass\n')
    assert '  markers: rewrote 1 marker in 1 file' in printed, printed


# purlin: update PROOF-109
def test_the_shell_harness_calls_become_one_comment(tmp_path, capsys):
    root, printed = _rewritten(tmp_path, capsys, 'tests/login.test.sh',
                               OLD_SHELL)
    assert _read(root, 'tests/login.test.sh') == NEW_SHELL
    assert ('  markers: rewrote 1 marker in 1 file; a shell or SQL file is '
            'one test now, and passes when it exits 0' in printed), printed
    assert ('rewrote 1 marker in tests/login.test.sh as comments; the file '
            'is one test now, and passes when it exits 0'
            in _log(root)), _log(root)


# purlin: update PROOF-30
def test_a_module_wide_marker_is_named_and_left_on_its_line(tmp_path,
                                                             capsys):
    root = _project(tmp_path, V095)
    module = ('import pytest\n\n'
              'pytestmark = pytest.mark.proof("login", "PROOF-3", "RULE-3")\n'
              '\n\n@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'
              'def test_a():\n    pass\n')
    _write(root, 'tests/test_module.py', module)
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    lines = _read(root, 'tests/test_module.py').splitlines()
    at = lines.index('def test_a():')
    assert lines[at - 1] == '# purlin: login PROOF-1', lines
    assert lines[2] == module.splitlines()[2]
    assert ('  left tests/test_module.py:3 as it was: write the marker as a '
            'comment above each test by hand') in printed, printed


# --- the wiring --------------------------------------------------------------

OLD_CONFTEST = 'pytest_plugins = [".purlin.plugins.pytest_purlin"]\n'
CSPROJ = ('<Project><ItemGroup><Compile Include="../.purlin/plugins/'
          'xunit_purlin.cs" /></ItemGroup></Project>\n')


# A line of the project's own that uses the import above it, so the file is
# kept once the plugin's line is gone.
OWN_LINE = 'ROOT = os.getcwd()'


def _conftest_with_a_line_of_its_own(tmp_path, eol):
    """The sample given a conftest of `import os` and `ROOT = os.getcwd()`
    above the plugin's line, each line ended by `eol`, updated with `--yes`:
    `(the bytes it now holds, the bytes of the lines kept)`."""
    root = _project(tmp_path, V095)
    kept = ('import os' + eol + OWN_LINE + eol).encode('utf-8')
    _write_bytes(root, 'conftest.py',
                 kept + OLD_CONFTEST.replace('\n', eol).encode('utf-8'))
    _apply(root)
    return _read_bytes(root, 'conftest.py'), kept


# purlin: update PROOF-83
def test_a_conftest_with_a_line_of_its_own_keeps_it(tmp_path):
    now, kept = _conftest_with_a_line_of_its_own(tmp_path, '\n')
    assert now == b'import os\nROOT = os.getcwd()\n'
    assert now == kept


# purlin: update PROOF-120
@ON_WINDOWS
def test_on_windows_the_conftest_keeps_its_own_line_and_its_ending(tmp_path):
    now, kept = _conftest_with_a_line_of_its_own(tmp_path, '\r\n')
    assert now == b'import os\r\nROOT = os.getcwd()\r\n'
    assert now == kept


# The two files a real 0.9.5 project loaded the plugin from: each a docstring
# that quotes the scaffolded line, two imports, the path line and the entry.
LOADER = (
    '"""Load the Purlin pytest plugin by path.\n\n'
    'The scaffolded form of this file was\n'
    '`pytest_plugins = [".purlin.plugins.pytest_purlin"]`, which cannot '
    'import.\n"""\n\n'
    'import sys\n'
    'from pathlib import Path\n\n'
    'sys.path.insert(0, str(Path(__file__).resolve().parent%s / ".purlin" '
    '/ "plugins"))\n\n'
    'pytest_plugins = ["pytest_purlin"]\n')
# A conftest the project keeps: a docstring that names the plugin, a comment
# that does, a fixture, and the plugin beside one of the project's own.
KEPT_CONFTEST = (
    '"""Fixtures. `pytest_plugins = ["pytest_purlin"]` loads the proofs."""\n'
    'import sys\n\n'
    'import pytest\n\n'
    '# sys.path.insert(0, ".purlin/plugins") is what finds pytest_purlin\n'
    'sys.path.insert(0, ".purlin/plugins")\n'
    'pytest_plugins = ["pytest_purlin", "house_plugin"]\n\n\n'
    '@pytest.fixture\n'
    'def engine():\n    return 1\n')


KEPT_CONFTEST_AFTER = (
    '"""Fixtures. `pytest_plugins = ["pytest_purlin"]` loads the proofs."""\n'
    'import sys\n\n'
    'import pytest\n\n'
    '# sys.path.insert(0, ".purlin/plugins") is what finds pytest_purlin\n'
    'pytest_plugins = ["house_plugin"]\n\n\n'
    '@pytest.fixture\n'
    'def engine():\n    return 1\n')


def _two_loaders(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write_bytes(root, 'conftest.py', (LOADER % '').encode('utf-8'))
    _write_bytes(root, 'pipeline/conftest.py',
                 (LOADER % '.parent').encode('utf-8'))
    _write_bytes(root, 'pipeline/tests/conftest.py',
                 KEPT_CONFTEST.encode('utf-8'))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the files that load the plugin')
    listed = [item['files'] for item in update.pending(root)
              if item['id'] == 'plugins'][0]
    _apply(root)
    return root, listed, capsys.readouterr().out.splitlines()


# purlin: update PROOF-180
def test_every_conftest_that_only_loads_the_plugin_is_deleted(tmp_path,
                                                              capsys):
    root, listed, printed = _two_loaders(tmp_path, capsys)
    for rel in ('conftest.py', 'pipeline/conftest.py'):
        assert rel in listed, listed
        assert not os.path.exists(os.path.join(root, rel)), rel
        assert rel not in _tracked(root)
        assert [line for line in printed if line.strip() == (
            "removed %s: it held only the plugin's wiring" % rel)], printed


# purlin: update PROOF-181
def test_a_conftest_with_more_loses_the_two_lines_alone(tmp_path, capsys):
    root, listed, printed = _two_loaders(tmp_path, capsys)
    rel = 'pipeline/tests/conftest.py'
    assert rel in listed, listed
    assert _read(root, rel) == KEPT_CONFTEST_AFTER
    assert [line for line in printed if line.strip() == (
        "removed the plugin's wiring from %s" % rel)], printed


# purlin: update PROOF-88
def test_a_csproj_compiling_the_logger_is_named_and_left(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write_bytes(root, 'App.Tests/App.Tests.csproj', CSPROJ.encode('utf-8'))
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert _read_bytes(root, 'App.Tests/App.Tests.csproj') == CSPROJ.encode(
        'utf-8')
    assert ('  App.Tests/App.Tests.csproj compiles the xUnit logger v0.9.5 '
            'shipped; remove that line by hand, since dotnet test --logger trx '
            'needs nothing added') in printed, printed


# --- the config --------------------------------------------------------------

# purlin: update PROOF-162
def test_the_config_holds_version_and_tests_alone(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    config = _config(root)
    assert sorted(config) == ['tests', 'version'], config
    assert config['version'] == VERSION


# purlin: update PROOF-163
def test_every_key_the_config_carried_is_removed_and_named(tmp_path, capsys):
    root = _project(tmp_path, V095)
    old = _config(root)
    for key in ('digest', 'pre_push', 'report', 'spec_dir'):
        assert key in old, key
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    (line,) = [row.strip() for row in printed
               if row.strip().startswith('removed from .purlin/config.json:')]
    named = line[len('removed from .purlin/config.json:'):].split(',')
    for key in ('digest', 'pre_push', 'report', 'spec_dir'):
        assert key in [name.strip() for name in named], line
    written = _config(root)
    for key in ('digest', 'pre_push', 'report', 'spec_dir'):
        assert key not in written, written


# --- the refusals --------------------------------------------------------------

# purlin: update PROOF-4
def test_a_root_without_purlin_exits_2(tmp_path):
    empty = str(tmp_path / 'empty')
    os.makedirs(empty)
    done = subprocess.run([sys.executable, UPDATE, '--project-root', empty],
                          capture_output=True, text=True)
    assert done.returncode == 2
    assert done.stderr.splitlines() == [
        'There is no .purlin/ under %s, so there is nothing to update. Run '
        'purlin:init first.' % os.path.abspath(empty)], done.stderr


# purlin: update PROOF-116
def test_a_settings_file_that_cannot_be_read_stops_the_update(tmp_path,
                                                              capsys):
    root = _project(tmp_path, V095)
    text = _read(root, '.purlin/config.json').rstrip()
    assert text.endswith('}')
    broken = text[:-1].rstrip() + ',\n}\n'
    _write(root, '.purlin/config.json', broken)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'a comma after the last value')
    head = _git(root, 'rev-parse', 'HEAD').stdout
    status = _git(root, 'status', '--porcelain').stdout
    # The reader's own message and line, as this Python words them.
    with pytest.raises(ValueError) as reader:
        json.loads(broken)
    assert _apply(root) == 1
    captured = capsys.readouterr()
    printed = captured.out + captured.err
    line = [row for row in printed.splitlines()
            if row.startswith('.purlin/config.json cannot be read: ')]
    assert line == ['.purlin/config.json cannot be read: %s at line %d. Fix '
                    'the file by hand; nothing ran and nothing was saved.'
                    % (reader.value.msg, reader.value.lineno)], printed
    assert _git(root, 'status', '--porcelain').stdout == status
    assert _git(root, 'rev-parse', 'HEAD').stdout == head


# A pre-commit hook of the project's own, which refuses every commit.
REFUSING_HOOK = '#!/bin/sh\necho blocked by policy\nexit 1\n'


# purlin: update PROOF-151
def test_a_commit_git_refuses_leaves_the_changes_staged(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write_bytes(root, '.git/hooks/pre-commit', REFUSING_HOOK.encode('utf-8'))
    os.chmod(os.path.join(root, '.git', 'hooks', 'pre-commit'), 0o755)
    head = _git(root, 'rev-parse', 'HEAD').stdout
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert ('The changes are staged and not committed: blocked by policy'
            in printed), printed
    assert _git(root, 'rev-parse', 'HEAD').stdout == head
    assert _git(root, 'diff', '--cached', '--quiet').returncode == 1


# --- the lines 0.9.5 wrote into a spec -----------------------------------------

# One proof line whose Windows tag hides a kind-of-test tag before it.
HIDDEN_KIND = ('# Feature: lock\n\n> Scope: lock.py\n\n## Rules\n\n'
               '- RULE-1: A lock holds\n\n## Proof\n\n'
               '- PROOF-1 (RULE-1): Lock a file @unit @windows\n')


# purlin: update PROOF-129
def test_one_run_rewrites_a_tag_the_windows_tag_hid(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write(root, 'specs/core/lock.md', HIDDEN_KIND)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'a proof line with two tags')
    assert _apply(root) == 0
    assert _read(root, 'specs/core/lock.md').splitlines()[-1] == (
        '- PROOF-1 (RULE-1): Lock a file @env(windows)')
    capsys.readouterr()
    assert update.pending(root) == []
    _apply(root)
    assert NOTHING_PENDING in capsys.readouterr().out.splitlines()


DESIGN_ANCHOR = 'specs/_anchors/checkout_design.md'
DESIGN_FIELDS = ('> Source:', '> Pinned:', '> Visual-Reference:',
                 '> Visual-Hash:')


def _without(text, prefixes):
    return [line for line in text.splitlines()
            if not any(line.startswith(p) for p in prefixes)]


# purlin: update PROOF-24
def test_every_design_line_of_the_anchor_is_removed(tmp_path, capsys):
    root = _project(tmp_path, V095)
    before = _read(root, DESIGN_ANCHOR)
    for field in DESIGN_FIELDS:
        assert field in before, field
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    after = _read(root, DESIGN_ANCHOR)
    for field in DESIGN_FIELDS:
        assert not [line for line in after.splitlines()
                    if line.startswith(field)], field
    # The kind-of-test migration rewrites the anchor's proof lines too, so
    # the comparison stops short of the proof lines.
    assert _without(after, ('- PROOF-',)) == _without(
        before, DESIGN_FIELDS + ('- PROOF-',))
    assert ('removed the design reference from %s: > Source:, > Pinned:, '
            '> Visual-Reference:, > Visual-Hash:' % DESIGN_ANCHOR) in _log(
                root)
    assert ('  design-refs: removed the design reference from 2 specs'
            in printed), printed


# A remote anchor: its source is a git address that only holds the word.
GIT_ANCHOR = 'specs/_anchors/tokens.md'
GIT_ANCHOR_TEXT = (
    b'# Anchor: tokens\n\n'
    b'> Description: The design tokens every screen uses.\n'
    b'> Source: https://github.com/acme/figma-tokens.git specs/tokens.md\n'
    b'> Pinned: 0123456789abcdef0123456789abcdef01234567\n\n'
    b'## Rules\n\n'
    b'- RULE-1: Every colour on a screen is one of the tokens\n\n'
    b'## Proof\n\n'
    b'- PROOF-1 (RULE-1): Read the checkout screen; every colour is a token '
    b'@manual\n')


# purlin: update PROOF-165
def test_an_anchor_from_a_git_address_holding_figma_is_left_as_it_was(
        tmp_path):
    root = _project(tmp_path, V095)
    _write_bytes(root, GIT_ANCHOR, GIT_ANCHOR_TEXT)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'anchor(tokens): add')
    assert _apply(root) == 0
    assert _read_bytes(root, GIT_ANCHOR) == GIT_ANCHOR_TEXT
    assert _walk(root, ('tokens.md*',), skip_backups=False) == [GIT_ANCHOR]


# purlin: update PROOF-153
def test_no_spec_names_an_anchor_after_the_update(tmp_path):
    root = _project(tmp_path, V095)
    rel = 'specs/audit/static_checks.md'
    text = _read(root, rel)
    assert '\n> Scope:' in text
    _write(root, rel, text.replace('\n> Scope:', '\n> Global: true\n> Scope:',
                                   1))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'a Global line')
    specs = [path for path in _walk(root, ('*.md',))
             if path.startswith('specs/')]
    assert [path for path in specs
            if re.search(r'(?m)^> Requires:', _read(root, path))]
    _apply(root)
    for path in specs:
        lines = _read(root, path).splitlines()
        assert not [l for l in lines
                    if l.startswith(('> Requires:', '> Global:'))], path
        if path.startswith('specs/_anchors/'):
            assert not [l for l in lines if l.startswith('> Scope:')], path


# --- the files 0.9.5 kept ------------------------------------------------------

# purlin: update PROOF-8
def test_no_proof_or_run_file_is_left_on_disk_or_tracked(tmp_path):
    root = _project(tmp_path, V095)
    assert _walk(root, ('*.proofs-*.json',)), 'the fixture has proof files'
    assert _walk(root, ('*.receipt.json',)), 'the fixture has run files'
    _apply(root)
    assert _walk(root, LEFTOVER) == []
    left = [rel for rel in _tracked(root)
            if any(fnmatch.fnmatch(os.path.basename(rel), p)
                   for p in LEFTOVER)]
    assert left == []


SHIPPED_COPIES = ('pytest_purlin.py', 'jest_purlin.js', 'vitest_purlin.ts',
                  'purlin-proof.sh')


# The workflow 0.9.5 wrote, and one of the project's own.
PROOF_WORKFLOW = '.github/workflows/purlin-proofs.yml'
PROOF_WORKFLOW_TEXT = (
    b'name: purlin-proofs\n'
    b'on: push\n'
    b'jobs:\n'
    b'  proofs:\n'
    b'    runs-on: ubuntu-latest\n'
    b'    steps:\n'
    b'      - uses: actions/checkout@v4\n'
    b'      - run: python -m pytest\n'
    b"      - run: git add '*.proofs-*.json'\n"
    b'      - run: git commit -m "proofs [skip ci]" && git push\n')
OWN_WORKFLOW = '.github/workflows/ci.yml'
OWN_WORKFLOW_TEXT = (
    b'name: ci\n'
    b'on: push\n'
    b'jobs:\n'
    b'  test:\n'
    b'    runs-on: ubuntu-latest\n'
    b'    steps:\n'
    b'      - uses: actions/checkout@v4\n'
    b'      - run: pytest\n')


def _two_workflows(tmp_path):
    """The sample with `purlin-proofs.yml` in place of its own workflow, and
    the project's `ci.yml`, both committed."""
    root = _project(tmp_path, V095)
    os.rename(os.path.join(root, '.github/workflows/windows-proofs.yml'),
              os.path.join(root, PROOF_WORKFLOW))
    _write_bytes(root, PROOF_WORKFLOW, PROOF_WORKFLOW_TEXT)
    _write_bytes(root, OWN_WORKFLOW, OWN_WORKFLOW_TEXT)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'ci: the two workflows')
    return root


def _workflows(root):
    return [rel for rel in _walk(root, ('*',))
            if rel.startswith('.github/workflows/')]


WORKFLOW_LINE = (".github/workflows/purlin-proofs.yml:9 names a proof file: "
                 "- run: git add '*.proofs-*.json'")
WORKFLOW_QUESTION = 'Remove .github/workflows/purlin-proofs.yml? [y/N] '
WORKFLOW_KEPT = ('  .github/workflows/purlin-proofs.yml: kept. It names a '
                 'proof file and may be the old Purlin workflow; remove it '
                 'by hand if it is.')
WORKFLOW_REMOVED = ('  workflows: removed 1 workflow that committed proof '
                    'files')


# purlin: update PROOF-164
def test_a_workflow_is_removed_only_on_a_yes_for_that_file(tmp_path, capsys,
                                                          monkeypatch):
    root = _two_workflows(tmp_path)
    asked = _answers(monkeypatch)
    assert _apply(root, argv=()) == 0
    printed = capsys.readouterr().out.splitlines()
    assert WORKFLOW_LINE in printed, printed
    assert WORKFLOW_QUESTION in asked, asked
    assert _workflows(root) == [OWN_WORKFLOW]
    assert _backups(root)[PROOF_WORKFLOW] == PROOF_WORKFLOW_TEXT
    assert _read_bytes(root, OWN_WORKFLOW) == OWN_WORKFLOW_TEXT
    assert WORKFLOW_REMOVED in printed
    assert PROOF_WORKFLOW not in _tracked(root)


# purlin: update PROOF-166
def test_yes_removes_no_workflow_and_names_the_one_it_kept(tmp_path, capsys,
                                                           monkeypatch):
    root = _two_workflows(tmp_path)
    asked = _answers(monkeypatch)
    assert _apply(root) == 0
    printed = capsys.readouterr().out.splitlines()
    assert asked == []
    assert _workflows(root) == [OWN_WORKFLOW, PROOF_WORKFLOW]
    assert _read_bytes(root, PROOF_WORKFLOW) == PROOF_WORKFLOW_TEXT
    assert PROOF_WORKFLOW in _tracked(root)
    assert WORKFLOW_KEPT in printed, printed
    assert update.pending(root) == []


# purlin: update PROOF-167
def test_a_workflow_answered_no_is_kept_and_named(tmp_path, capsys,
                                                  monkeypatch):
    root = _two_workflows(tmp_path)
    _answers(monkeypatch, [('Remove %s?' % PROOF_WORKFLOW, 'n')])
    assert _apply(root, argv=()) == 0
    printed = capsys.readouterr().out.splitlines()
    assert _read_bytes(root, PROOF_WORKFLOW) == PROOF_WORKFLOW_TEXT
    assert WORKFLOW_KEPT in printed, printed
    assert not [line for line in printed if 'removed 1 workflow' in line]


# purlin: update PROOF-81
def test_a_reporter_the_plugin_never_shipped_is_left_alone(tmp_path):
    root = _project(tmp_path, V095)
    folder = os.path.join(root, '.purlin', 'plugins')
    for name in SHIPPED_COPIES:
        assert os.path.isfile(os.path.join(folder, name)), name
    _write(root, '.purlin/plugins/house_purlin.rb', '# our own reporter\n')
    _apply(root)
    assert _read(root, '.purlin/plugins/house_purlin.rb') == (
        '# our own reporter\n')
    assert sorted(os.listdir(folder)) == ['house_purlin.rb']


# purlin: update PROOF-34
def test_the_dashboard_data_is_untracked_and_ignored(tmp_path):
    root = _project(tmp_path, V095)
    assert '.purlin/report-data.js' in _tracked(root)
    _apply(root)
    assert '.purlin/report-data.js' not in _tracked(root)
    assert os.path.isfile(os.path.join(root, '.purlin', 'report-data.js'))
    assert '.purlin/report-data.js' in _read(root, '.gitignore').splitlines()


# --- the evidence folder and the page -------------------------------------------

# purlin: update PROOF-28
def test_the_evidence_folder_gets_its_readme(tmp_path):
    root = _project(tmp_path, V095)
    assert not os.path.exists(os.path.join(root, '.purlin', 'evidence'))
    assert 'evidence' in _ids(root)
    _apply(root)
    with open(os.path.join(root, '.purlin', 'evidence', 'README.md'),
              'rb') as got, open(os.path.join(
                  ROOT, 'templates', 'evidence-readme.md'), 'rb') as want:
        assert got.read() == want.read()
    assert '.purlin/evidence/README.md' in _tracked(root)
    assert 'evidence' not in _ids(root)


# purlin: update PROOF-106
def test_a_readme_already_there_is_left_alone(tmp_path):
    root = _project(tmp_path, V095)
    ours = '# Our evidence\n\nWritten by hand.\n'
    _write(root, '.purlin/evidence/README.md', ours)
    assert 'evidence' not in _ids(root)
    _apply(root)
    assert _read(root, '.purlin/evidence/README.md') == ours
    assert _walk(root, LEFTOVER) == []


def _shipped_page():
    with open(os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html'),
              'rb') as handle:
        return handle.read()


# purlin: update PROOF-31
def test_the_page_linked_into_the_old_plugin_is_replaced(tmp_path):
    root = _project(tmp_path, V095)
    page = os.path.join(root, 'purlin-report.html')
    target = os.path.join(str(tmp_path), 'plugins', 'cache', 'purlin',
                          '0.9.5', 'purlin-report.html')
    try:
        os.symlink(target, page)
    except (OSError, NotImplementedError):
        pytest.skip('this machine makes no symbolic link')
    assert not os.path.exists(target)
    assert 'dashboard' in _ids(root)
    _apply(root)
    assert not os.path.islink(page)
    assert os.path.isfile(page)
    with open(page, 'rb') as handle:
        assert handle.read() == _shipped_page()
    assert 'dashboard' not in _ids(root)


# --- the proofs 0.9.5 numbered with a letter ----------------------------------
# The shapes of a real 0.9.5 project: a spec whose proofs carry a letter,
# and the tests whose markers name them.

PIANO = 'specs/web/piano.md'
PIANO_SPEC = (
    '# Feature: piano\n\n'
    '> Description: The piano roll.\n'
    '> Scope: piano.py\n'
    '> Highest-Proof: 9\n\n'
    '## Rules\n\n'
    '- RULE-1: A note sounds\n'
    '- RULE-2: A note stops\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): Press a key; one note sounds\n'
    '- PROOF-2 (RULE-2): Release the key; the note stops\n'
    '- PROOF-2b (RULE-2): Release the key part way through a bar; the note\n'
    '  stops on that line @integration\n'
    '- PROOF-7b (RULE-1): Press two keys; two notes sound\n')
PIANO_TS = 'packages/web/test/piano.test.ts'
PIANO_TS_OLD = (
    "import { it } from 'vitest';\n\n"
    "it('two keys sound two notes [proof:piano:PROOF-7b:RULE-1:unit]', "
    "() => {\n});\n")
PIANO_PY = 'tests/test_piano.py'
PIANO_PY_OLD = (
    'import pytest\n\n\n'
    '@pytest.mark.proof("piano", "PROOF-2b", "RULE-2")\n'
    'def test_stops_on_the_line():\n    pass\n')
KEYS_PY = 'tests/test_keys.py'
KEYS_PY_OLD = (
    'import pytest\n\n\n'
    '@pytest.mark.proof("piano", "PROOF-1", "RULE-1")\n'
    'def test_a_key_sounds():\n    pass\n')
ORPHAN_PY = 'tests/test_orphan.py'
ORPHAN_PY_OLD = (
    'import pytest\n\n\n'
    '@pytest.mark.proof("piano", "PROOF-9c", "RULE-2")\n'
    'def test_names_a_proof_no_spec_has():\n    pass\n')


def _lettered(tmp_path, spec=PIANO_SPEC, files=()):
    """The sample 0.9.5 project with the spec `piano` and these test files,
    committed."""
    root = _project(tmp_path, V095)
    _write_bytes(root, PIANO, spec.encode('utf-8'))
    for rel, text in files:
        _write_bytes(root, rel, text.encode('utf-8'))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the piano roll, as 0.9.5 numbered it')
    return root


def _proof_ids(root, rel):
    return re.findall(r'(?m)^- (PROOF-\w+) ', _read(root, rel))


# purlin: update PROOF-169
def test_each_lettered_proof_takes_the_next_free_number(tmp_path, capsys):
    root = _lettered(tmp_path)
    assert 'lettered-proofs' in _ids(root)
    assert _apply(root) == 0
    printed = [line.strip() for line in capsys.readouterr().out.splitlines()]
    assert _proof_ids(root, PIANO) == ['PROOF-1', 'PROOF-2', 'PROOF-10',
                                       'PROOF-11']
    assert '> Highest-Proof: 11' in _read(root, PIANO).splitlines()
    assert 'piano PROOF-2b is now PROOF-10' in printed, printed
    assert 'piano PROOF-7b is now PROOF-11' in printed, printed
    assert 'lettered-proofs' not in _ids(root)


# purlin: update PROOF-170
def test_a_spec_with_no_highest_line_is_given_none(tmp_path, capsys):
    spec = PIANO_SPEC.replace('> Highest-Proof: 9\n', '')
    root = _lettered(tmp_path, spec=spec)
    _apply(root)
    printed = [line.strip() for line in capsys.readouterr().out.splitlines()]
    assert _proof_ids(root, PIANO) == ['PROOF-1', 'PROOF-2', 'PROOF-8',
                                       'PROOF-9']
    assert 'Highest-Proof' not in _read(root, PIANO)
    assert 'piano PROOF-2b is now PROOF-8' in printed, printed
    assert 'piano PROOF-7b is now PROOF-9' in printed, printed


# purlin: update PROOF-171
def test_the_markers_of_a_lettered_proof_carry_its_new_number(tmp_path,
                                                              capsys):
    root = _lettered(tmp_path, files=((PIANO_TS, PIANO_TS_OLD),
                                      (PIANO_PY, PIANO_PY_OLD)))
    _apply(root)
    capsys.readouterr()
    assert _read(root, PIANO_TS) == (
        "import { it } from 'vitest';\n\n"
        "// purlin: piano PROOF-11\n"
        "it('two keys sound two notes', () => {\n});\n")
    assert _read(root, PIANO_PY) == (
        'import pytest\n\n\n'
        '# purlin: piano PROOF-10\n'
        'def test_stops_on_the_line():\n    pass\n')
    for rel in (PIANO_TS, PIANO_PY):
        assert 'PROOF-7b' not in _read(root, rel)
        assert 'PROOF-2b' not in _read(root, rel)


# purlin: update PROOF-172
def test_a_marker_naming_a_lettered_proof_no_spec_has_is_left(tmp_path,
                                                              capsys):
    root = _lettered(tmp_path, files=((ORPHAN_PY, ORPHAN_PY_OLD),
                                      (KEYS_PY, KEYS_PY_OLD)))
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert _read(root, ORPHAN_PY) == ORPHAN_PY_OLD
    assert ('  left tests/test_orphan.py:4 as it was: it names piano '
            'PROOF-9c, which no spec has. Write the proof with purlin:spec '
            'piano, then write the marker as a comment above the test by '
            'hand') in printed, printed


# purlin: update PROOF-173
def test_declined_lettered_proofs_stay_and_their_markers_say_so(
        tmp_path, capsys, monkeypatch):
    root = _lettered(tmp_path, files=((PIANO_PY, PIANO_PY_OLD),
                                      (KEYS_PY, KEYS_PY_OLD)))
    order = _ids(root)
    assert order.index('lettered-proofs') < order.index('markers')
    _answers(monkeypatch, [('Apply lettered-proofs', 'n')])
    _apply(root, argv=())
    printed = capsys.readouterr().out.splitlines()
    assert _read(root, PIANO) == PIANO_SPEC
    assert _read(root, PIANO_PY) == PIANO_PY_OLD
    assert ('  left tests/test_piano.py:4 as it was: it names piano '
            'PROOF-2b, which is numbered with a letter. Run purlin:init '
            '--update again and apply lettered-proofs') in printed, printed
    assert _ids(root) == ['lettered-proofs']


# --- a title tag, in the shapes a real project writes it ------------------------

PROXY_TS = 'packages/web/test/dev_proxy.test.ts'
UNREAD = ('the title of the test under this marker cannot be read, so its '
          'result cannot be matched. Write it as one plain string.')


def _title(tmp_path, capsys, old):
    """The sample given one TypeScript test file, updated with `--yes`:
    `(the file's lines now, the lines printed)`."""
    root, printed = _rewritten(tmp_path, capsys, PROXY_TS, old)
    return _read(root, PROXY_TS).splitlines(), printed


# purlin: update PROOF-174
def test_a_tag_joined_on_one_line_leaves_one_plain_title(tmp_path, capsys):
    now, printed = _title(tmp_path, capsys, (
        "it('every route is forwarded to it ' + "
        "'[proof:dev_proxy:PROOF-1:RULE-1:unit]', () => {\n});\n"))
    assert now == ['// purlin: dev_proxy PROOF-1',
                   "it('every route is forwarded to it', () => {", '});']
    assert not [line for line in printed if line.endswith(UNREAD)], printed


# purlin: update PROOF-175
def test_a_tag_on_a_line_of_its_own_goes_with_its_plus(tmp_path, capsys):
    now, _printed = _title(tmp_path, capsys, (
        "test(\n"
        "  'a role still plays '\n"
        "  + '[proof:dev_proxy:PROOF-1:RULE-1:unit]',\n"
        "  () => {\n});\n"))
    assert now == ['// purlin: dev_proxy PROOF-1', 'test(',
                   "  'a role still plays',", '  () => {', '});']


# purlin: update PROOF-176
def test_a_plus_ending_the_line_above_the_tag_goes_too(tmp_path, capsys):
    now, _printed = _title(tmp_path, capsys, (
        "test(\n"
        "  'a role still plays ' +\n"
        "  '[proof:dev_proxy:PROOF-1:RULE-1:unit]',\n"
        "  () => {\n});\n"))
    assert now == ['// purlin: dev_proxy PROOF-1', 'test(',
                   "  'a role still plays',", '  () => {', '});']


# purlin: update PROOF-177
def test_a_tag_opening_a_title_leaves_no_leading_space(tmp_path, capsys):
    now, _printed = _title(tmp_path, capsys, (
        'it("[proof:dev_proxy:PROOF-1:RULE-1:unit] every setting is '
        'accepted", () => {\n});\n'))
    assert now == ['// purlin: dev_proxy PROOF-1',
                   'it("every setting is accepted", () => {', '});']


# purlin: update PROOF-178
def test_the_comment_goes_above_the_line_that_opens_the_test(tmp_path,
                                                             capsys):
    now, _printed = _title(tmp_path, capsys, (
        "describe('import', () => {\n"
        "  test(\n"
        "    'an imported track is a stem of the built score '\n"
        "    + 'through the standard setters, '\n"
        "    + 'and its audition [proof:dev_proxy:PROOF-2:RULE-2:unit]',\n"
        "    async () => {\n    },\n  );\n});\n"))
    assert now == ["describe('import', () => {",
                   '  // purlin: dev_proxy PROOF-2',
                   '  test(',
                   "    'an imported track is a stem of the built score '",
                   "    + 'through the standard setters, '",
                   "    + 'and its audition',",
                   '    async () => {', '    },', '  );', '});']


# purlin: update PROOF-179
def test_a_title_the_reader_cannot_read_is_named(tmp_path, capsys):
    now, printed = _title(tmp_path, capsys, (
        "const NAME = 'forwarded';\n"
        "it(NAME + ' [proof:dev_proxy:PROOF-1:RULE-1:unit]', () => {\n});\n"))
    assert now == ["const NAME = 'forwarded';",
                   '// purlin: dev_proxy PROOF-1', 'it(NAME, () => {', '});']
    assert ('  %s:2: %s' % (PROXY_TS, UNREAD)) in printed, printed


# --- the command proposed for each test tool -------------------------------------

UV_PYTEST = 'uv run --project pipeline pytest pipeline/tests'
PACKAGE_JSON = json.dumps({
    'name': 'studio',
    'scripts': {'test': 'vitest run --project unit',
                'test:python': UV_PYTEST},
    'devDependencies': {'vitest': '^3.0.0'}}, indent=2) + '\n'
TYPED = ('uv run --project pipeline python -m pytest -c '
         'pipeline/pyproject.toml {files} --junitxml={report}')
COMMAND_QUESTION = ('Use this command for %s? Press Enter to use it, or type '
                    'the command to use instead: ')


def _subfolder_project(tmp_path):
    """The sample as a project whose pytest lives in `pipeline/` and is run
    through `uv` from a `package.json` script, with vitest beside it."""
    root = _project(tmp_path, V095)
    _set_config(root, test_framework='pytest,vitest,shell')
    _write(root, 'package.json', PACKAGE_JSON)
    _write(root, 'pipeline/pyproject.toml',
           '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n')
    _write(root, 'pipeline/tests/test_x.py', 'def test_x():\n    pass\n')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'pytest in a subfolder, run through uv')
    return root


def _runs(root):
    return dict((entry['name'], entry['run'])
                for entry in _config(root)['tests'])


# purlin: update PROOF-182
def test_the_command_proposed_starts_the_way_the_project_starts_it(
        tmp_path, capsys):
    root = _subfolder_project(tmp_path)
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert _runs(root) == {
        'pytest': 'uv run --project pipeline pytest {files} '
                  '--junitxml={report}',
        'vitest': frameworks.entry_for('vitest')['run']}
    assert ('    pytest: uv run --project pipeline pytest {files} '
            '--junitxml={report}') in printed, printed
    assert '    dropped shell from the tests: nothing in the tree runs it' \
        in printed, printed


# purlin: update PROOF-183
def test_the_owner_is_shown_where_each_command_runs_and_may_type_another(
        tmp_path, capsys, monkeypatch):
    root = _subfolder_project(tmp_path)
    asked = _answers(monkeypatch, [(COMMAND_QUESTION % 'pytest', TYPED),
                                   (COMMAND_QUESTION % 'vitest', '')])
    _apply(root, argv=())
    printed = capsys.readouterr().out.splitlines()
    assert COMMAND_QUESTION % 'pytest' in asked, asked
    assert COMMAND_QUESTION % 'vitest' in asked, asked
    at = printed.index('pytest: uv run --project pipeline pytest {files} '
                       '--junitxml={report}')
    assert printed[at + 1] == ('  package.json, "test:python", runs it as: '
                               + UV_PYTEST), printed[at:at + 2]
    assert _runs(root) == {'pytest': TYPED,
                           'vitest': frameworks.entry_for('vitest')['run']}


# --- what the update prints -----------------------------------------------------

def _three_marked_files(tmp_path, capsys, more=()):
    root = _project(tmp_path, V095)
    for rel, text in (('tests/test_login.py', OLD_PYTEST),
                      ('tests/test_keys.py', KEYS_PY_OLD.replace(
                          '"piano"', '"login"')),
                      ('tests/test_more.py', KEYS_PY_OLD.replace(
                          '"piano"', '"login"'))) + tuple(more):
        _write_bytes(root, rel, text.encode('utf-8'))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the tests 0.9.5 marked')
    _apply(root)
    return root, capsys.readouterr().out.splitlines()


# purlin: update PROOF-184
def test_each_migration_prints_one_line_of_totals(tmp_path, capsys):
    root, printed = _three_marked_files(tmp_path, capsys)
    assert '  markers: rewrote 4 markers in 3 files' in printed, printed
    assert not [line for line in printed if 'as comments' in line]
    assert not [line for line in printed if 'kept the previous bytes' in line]
    log = _log(root)
    assert 'rewrote 2 markers in tests/test_login.py as comments' in log
    assert 'rewrote 1 marker in tests/test_keys.py as comments' in log
    assert ('kept the previous bytes at %s/tests/test_login.py' % BACKUPS
            in log), log


MODULE_WIDE = ('import pytest\n\n'
               'pytestmark = pytest.mark.proof("login", "PROOF-3", "RULE-3")\n')
LEFT_LINE = ('  left tests/test_module.py:3 as it was: write the marker as a '
             'comment above each test by hand')


# purlin: update PROOF-185
def test_the_lines_that_need_the_owner_come_last_under_a_heading(tmp_path,
                                                                 capsys):
    _root, printed = _three_marked_files(
        tmp_path, capsys, more=(('tests/test_module.py', MODULE_WIDE),))
    heading = printed.index('These need you:')
    committed = [index for index, line in enumerate(printed)
                 if line.startswith('  committed ')]
    assert committed and committed[0] < heading
    assert printed.index(LEFT_LINE) > heading
    assert printed.index('  markers: rewrote 4 markers in 3 files') < heading
    assert LEFT_LINE.strip() in _log(_root)


# --- the questions --------------------------------------------------------------

def _piped(root, answers, *flags):
    """The update run as a command with `answers` on its input."""
    env = dict(os.environ, PYTHONIOENCODING='utf-8')
    return subprocess.run(
        [sys.executable, UPDATE, '--project-root', root] + list(flags),
        input=answers, capture_output=True, encoding='utf-8', env=env,
        timeout=300)


# purlin: update PROOF-186
def test_each_question_is_on_its_own_line_with_the_answer_taken(tmp_path):
    root = _project(tmp_path, V095)
    done = _piped(root, 'y\nn\n')
    assert done.returncode == 0, done.stderr
    asked = [line for line in done.stdout.splitlines() if '[y/N]' in line]
    assert len(asked) == len(NINE), asked
    for line in asked:
        assert line.count('[y/N]') == 1, line
        assert line.startswith('Apply '), line
    assert asked[0].startswith('Apply design-refs,') and asked[0].endswith(
        '[y/N] y'), asked[0]
    for line in asked[1:]:
        assert line.endswith('[y/N] n'), line
    assert _ids(root) == NINE[1:]


# purlin: update PROOF-187
def test_apply_names_the_migrations_to_apply_and_asks_nothing(tmp_path):
    root = _project(tmp_path, V095)
    done = _piped(root, '', '--apply', 'evidence,config')
    assert done.returncode == 0, done.stderr
    assert '[y/N]' not in done.stdout
    assert _ids(root) == [name for name in NINE
                          if name not in ('config', 'evidence')]
    assert _git(root, 'log', '-1', '--format=%s').stdout.strip() == (
        'chore(update): migrate to %s (config, evidence)' % VERSION)


GIVEN = 'uv run pytest {files} --junitxml={report}'


# purlin: update PROOF-188
def test_a_test_command_given_is_the_one_written(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    done = _piped(root, '', '--apply', 'config', '--test-command',
                  'pytest=' + GIVEN)
    assert done.returncode == 0, done.stderr
    assert _runs(root) == {'pytest': GIVEN}
    assert '    pytest: ' + GIVEN in done.stdout.splitlines()


# purlin: update PROOF-189
def test_an_id_that_is_no_migration_is_refused(tmp_path):
    root = _project(tmp_path, V095)
    head = _git(root, 'rev-parse', 'HEAD').stdout
    done = _piped(root, '', '--apply', 'config,everything')
    assert done.returncode == 2
    assert done.stderr.splitlines() == [
        'everything is not a migration. The migrations are: %s.'
        % ', '.join(m[0] for m in update.MIGRATIONS)], done.stderr
    assert _git(root, 'rev-parse', 'HEAD').stdout == head
    assert _git(root, 'status', '--porcelain').stdout == ''


# --- what the update leaves for the owner ------------------------------------------

LEFT_HEADING = 'Purlin left these for you:'
OLD_CLAUDE_MD = ('# Notes for the agent\n\n'
                 'Mark each test `[proof:feature:PROOF-1:RULE-1:unit]`.\n'
                 'In Python use `@pytest.mark.proof("feature", "PROOF-1")`.\n'
                 'The plugin lives in `.purlin/plugins/`.\n'
                 'Run `purlin:verify` before a push.\n')
DOCSTRING_PY = ('def test_documented():\n'
                '    """[proof:login:PROOF-1:RULE-1:unit]"""\n')


# purlin: update PROOF-190
def test_each_file_still_naming_what_0_9_5_used_is_listed_most_first(
        tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write(root, 'CLAUDE.md', OLD_CLAUDE_MD)
    _write(root, 'tests/test_documented.py', DOCSTRING_PY)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'what 0.9.5 told the agent')
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    heading = printed.index(LEFT_HEADING)
    first = printed.index('  CLAUDE.md: 4 lines')
    second = printed.index('  tests/test_documented.py: 1 line')
    assert heading < first < second
    assert _read(root, 'CLAUDE.md') == OLD_CLAUDE_MD
    assert _read(root, 'tests/test_documented.py') == DOCSTRING_PY


# purlin: update PROOF-191
def test_at_most_20_files_are_listed_and_the_rest_counted(tmp_path, capsys):
    root = _project(tmp_path, V095)
    for number in range(1, 23):
        _write(root, 'notes/n%02d.md' % number,
               'Run purlin:verify.\n' * (60 - number))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', '22 files of notes')
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    heading = printed.index(LEFT_HEADING)
    assert printed[heading + 1:heading + 21] == [
        '  notes/n%02d.md: %d lines' % (number, 60 - number)
        for number in range(1, 21)]
    more = re.match(r'^  and (\d+) more files$', printed[heading + 21])
    assert more and int(more.group(1)) >= 2, printed[heading + 21]
    assert not [line for line in printed if 'notes/n21.md' in line]


# purlin: update PROOF-192
def test_the_gitignore_lines_for_the_cache_and_the_plugins_go(tmp_path):
    root = _project(tmp_path, V095)
    before = _read(root, '.gitignore').splitlines()
    for line in ('.purlin/cache/', '.purlin/plugins/__pycache__/', '.venv/',
                 '/purlin-report.html'):
        assert line in before, line
    _apply(root)
    after = _read(root, '.gitignore').splitlines()
    assert '.purlin/cache/' not in after
    assert '.purlin/plugins/__pycache__/' not in after
    assert [line for line in before if line not in after] == [
        '.purlin/plugins/__pycache__/', '.purlin/cache/',
        '# Dashboard HTML (symlinked from framework)']
    assert '.venv/' in after and '/purlin-report.html' in after


# --- what became of the old record --------------------------------------------------

NOT_RUN = 'Every rule reads `not run` until the tests run again.'
OLD_RECORD = ('The `verify:` commits 0.9.5 made stay in git as the earlier '
              'record, and its receipts can be read from the commit before '
              'the upgrade, %s.')


# purlin: update PROOF-193
def test_the_update_says_what_became_of_the_old_record(tmp_path, capsys):
    root = _project(tmp_path, V095)
    before = _git(root, 'rev-parse', '--short', 'HEAD').stdout.strip()
    receipt = _walk(root, ('*.receipt.json',))[0]
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert NOT_RUN in printed, printed
    assert OLD_RECORD % before in printed, printed
    assert not os.path.exists(os.path.join(root, receipt))
    assert _git(root, 'show', '%s:%s' % (before, receipt)).returncode == 0


# purlin: update PROOF-194
def test_a_run_that_applies_nothing_says_nothing_of_the_record(
        tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, default='n')
    _apply(root, argv=())
    printed = capsys.readouterr().out
    assert NOT_RUN not in printed
    assert 'the commit before the upgrade' not in printed
    assert LEFT_HEADING not in printed
    assert not os.path.exists(os.path.join(root, BACKUPS))
