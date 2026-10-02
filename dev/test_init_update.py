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
*backups*     every rewritten file leaves its previous bytes beside it
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
"""

import fnmatch
import hashlib
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


def _walk(root, patterns, skip_backups=True):
    """Every project-relative path whose name matches one of `patterns`."""
    hits = []
    for dirpath, dirs, names in os.walk(root):
        if '.git' in dirs:
            dirs.remove('.git')
        for name in names:
            if skip_backups and name.endswith('.bak'):
                continue
            if any(fnmatch.fnmatch(name, p) for p in patterns):
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                hits.append(rel.replace(os.sep, '/'))
    return sorted(hits)


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

def _backed_up(tmp_path):
    """`(root, every file's bytes before the run, every backup after it)`."""
    root = _project(tmp_path, V095)
    before = {}
    for rel in _walk(root, ('*',)):
        with open(os.path.join(root, rel), 'rb') as handle:
            before[rel] = handle.read()
    _apply(root)
    return root, before, _walk(root, ('*.bak',), skip_backups=False)


BACKUP_NAME = re.compile(r'^(.+)\.local-([0-9a-f]{8})\.bak$')


# purlin: update PROOF-7
def test_every_backup_is_named_for_the_bytes_it_holds(tmp_path):
    root, before, backups = _backed_up(tmp_path)
    beside = [BACKUP_NAME.match(rel).group(1) for rel in backups
              if BACKUP_NAME.match(rel)]
    assert '.purlin/config.json' in beside, backups
    assert '.gitignore' in beside, backups
    assert any(rel.startswith('specs/') and rel.endswith('.md')
               for rel in beside), backups
    for rel in backups:
        named = BACKUP_NAME.match(rel)
        assert named, rel
        assert named.group(1) in before, rel
        with open(os.path.join(root, rel), 'rb') as handle:
            data = handle.read()
        assert hashlib.sha256(data).hexdigest()[:8] == named.group(2), rel


def _held(root, backups):
    """`{file: [the bytes of each backup beside it]}`."""
    held = {}
    for rel in backups:
        with open(os.path.join(root, rel), 'rb') as handle:
            held.setdefault(BACKUP_NAME.match(rel).group(1), []).append(
                handle.read())
    return held


# purlin: update PROOF-71
def test_every_backed_up_file_keeps_its_bytes_from_before_the_run(tmp_path):
    root, before, backups = _backed_up(tmp_path)
    held = _held(root, backups)
    assert held
    for rel, copies in held.items():
        assert before[rel] in copies, rel


# purlin: update PROOF-118
@ON_WINDOWS
def test_on_windows_every_backup_keeps_the_bytes_from_before(tmp_path):
    root, before, backups = _backed_up(tmp_path)
    held = _held(root, backups)
    assert held
    for rel, copies in held.items():
        assert before[rel] in copies, rel


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
def test_nothing_is_left_uncommitted_but_the_backups(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    left = _git(root, 'status', '--porcelain',
                '--untracked-files=all').stdout.splitlines()
    assert left, 'the backups should still be sitting there'
    for line in left:
        assert line.startswith('?? '), line
        assert line.endswith('.bak'), line


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
    printed = capsys.readouterr().out.splitlines()
    assert _config(root)['tests'] == [frameworks.entry_for('pytest')]
    for name in ('jest', 'shell', 'vitest'):
        assert ('  dropped %s from the tests: nothing in the tree runs it'
                % name) in printed, printed
    assert '  wrote the tests setting: pytest' in printed, printed


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
    assert '  wrote the tests setting: dotnet\n' in printed
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
    assert ('  rewrote 2 markers in tests/test_login.py as comments'
            in printed), printed


# purlin: update PROOF-109
def test_the_shell_harness_calls_become_one_comment(tmp_path, capsys):
    root, printed = _rewritten(tmp_path, capsys, 'tests/login.test.sh',
                               OLD_SHELL)
    assert _read(root, 'tests/login.test.sh') == NEW_SHELL
    assert ('  rewrote 1 marker in tests/login.test.sh as comments; the file '
            'is one test now, and passes when it exits 0' in printed), printed


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


def _conftest_with_import_os(tmp_path, eol):
    """The sample given a conftest of `import os` above the plugin's line,
    each line ended by `eol`, updated with `--yes`: `(the bytes it now
    holds, the bytes of the lines kept)`."""
    root = _project(tmp_path, V095)
    kept = ('import os' + eol).encode('utf-8')
    _write_bytes(root, 'conftest.py',
                 kept + OLD_CONFTEST.replace('\n', eol).encode('utf-8'))
    _apply(root)
    return _read_bytes(root, 'conftest.py'), kept


# purlin: update PROOF-83
def test_a_conftest_holding_import_os_keeps_it_alone(tmp_path):
    now, kept = _conftest_with_import_os(tmp_path, '\n')
    assert now == b'import os\n'
    assert now == kept


# purlin: update PROOF-120
@ON_WINDOWS
def test_on_windows_the_conftest_keeps_import_os_and_its_ending(tmp_path):
    now, kept = _conftest_with_import_os(tmp_path, '\r\n')
    assert now == b'import os\r\n'
    assert now == kept


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
    (line,) = [row for row in printed
               if row.startswith('  removed from .purlin/config.json:')]
    named = line[len('  removed from .purlin/config.json:'):].split(',')
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
    assert ('  removed the design reference from %s: > Source:, > Pinned:, '
            '> Visual-Reference:, > Visual-Hash:' % DESIGN_ANCHOR) in printed


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
    return [rel for rel in _walk(root, ('*',), skip_backups=False)
            if rel.startswith('.github/workflows/')]


WORKFLOW_LINE = (".github/workflows/purlin-proofs.yml:9 names a proof file: "
                 "- run: git add '*.proofs-*.json'")
WORKFLOW_QUESTION = 'Remove .github/workflows/purlin-proofs.yml? [y/N] '
WORKFLOW_KEPT = ('  .github/workflows/purlin-proofs.yml: kept. It names a '
                 'proof file and may be the old Purlin workflow; remove it '
                 'by hand if it is.')
WORKFLOW_REMOVED = '  removed 1 workflow that committed proof files'


# purlin: update PROOF-164
def test_a_workflow_is_removed_only_on_a_yes_for_that_file(tmp_path, capsys,
                                                          monkeypatch):
    root = _two_workflows(tmp_path)
    asked = _answers(monkeypatch)
    assert _apply(root, argv=()) == 0
    printed = capsys.readouterr().out.splitlines()
    assert WORKFLOW_LINE in printed, printed
    assert WORKFLOW_QUESTION in asked, asked
    backup = '%s.local-%s.bak' % (
        PROOF_WORKFLOW, hashlib.sha256(PROOF_WORKFLOW_TEXT).hexdigest()[:8])
    assert _workflows(root) == [OWN_WORKFLOW, backup]
    assert _read_bytes(root, backup) == PROOF_WORKFLOW_TEXT
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
