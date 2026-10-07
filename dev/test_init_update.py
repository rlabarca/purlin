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
*tags*        the tags that end a proof running over several lines
*endings*     what a run that applied nothing ends on, and one that applied
*agents*      the files that instruct an agent come first among what is left
*docstrings*  a docstring line that is only a 0.9.5 tag goes
*scripts*     the proposal cites the script of the project's it matches
*applying*    a run told to apply prints one line in place of the pending list
*agent files* the lines naming 0.9.5 go from the files that instruct an agent
*restoring*   a project 0.9.5 did not set up has its missing files restored,
              each named, and the run ends as the status ends
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
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'init'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

import sample_lab  # noqa: E402
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
BACKUPS_LINE = ('Every file the update rewrote is kept as it was under '
                '.purlin/runtime/update-backup/, with each change listed in '
                'update.log there. A file it deleted is in git, at %s. Delete '
                'the folder once the tests pass.')
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
    # The sample has nine pending, and the run says it applies those nine:
    # a migration that was never listed is not one the run left none of.
    assert _ids(root) == list(NINE)
    assert _apply(root) == 0
    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == 'Applying 9 migrations: %s.' % ', '.join(NINE)
    assert asked == []
    assert update.pending(root) == []
    assert _ids(root) == []
    # What the settings migration was pending for is gone from the file.
    assert sorted(_config(root)) == ['tests', 'version']


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
        # A copy: the file's bytes as they were before the update, every one.
        assert backups[rel] == before[rel], rel
    earlier = _git(root, 'rev-parse', '--short', 'HEAD~1').stdout.strip()
    assert BACKUPS_LINE % earlier in printed, printed
    # Every run file 0.9.5 committed beside a spec: the update deletes each.
    deleted = sorted(rel for rel in before if rel.endswith(
        '.receipt.json') or fnmatch.fnmatch(rel, '*.proofs-*.json'))
    assert len(deleted) == 15, deleted
    assert len([rel for rel in deleted
                if rel.endswith('.receipt.json')]) == 5, deleted
    for rel in deleted:
        assert not os.path.exists(os.path.join(root, rel)), rel
        assert rel not in backups, rel
        shown = subprocess.run(
            ['git', 'show', '%s:%s' % (earlier, rel)], cwd=root,
            capture_output=True)
        assert shown.returncode == 0, rel
        assert shown.stdout == before[rel], rel
    assert [rel for rel in backups if rel.endswith('.json')] == [
        '.purlin/config.json'], sorted(backups)
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
    _apply(root)
    log = _git(root, 'log', '--format=%s').stdout.splitlines()
    assert len(log) == 2, log
    release = _read(ROOT, 'VERSION').strip()
    assert log[0] == (
        'chore(update): migrate to %s (design-refs, anchor-lines, os-tags, '
        'kind-tags, untracked-files, config, evidence, workflows, plugins)'
        % release), log[0]
    assert log[1] == 'init', log


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
    # Named by a relative path, the folder is still printed in full.
    here = os.path.realpath(str(tmp_path))
    named = subprocess.run([sys.executable, UPDATE, '--project-root', 'empty'],
                           capture_output=True, text=True, cwd=here)
    assert named.returncode == 2
    assert named.stdout == ''
    assert named.stderr.splitlines() == [
        'There is no .purlin/ under %s, so there is nothing to update. Run '
        'purlin:init first.' % os.path.join(here, 'empty')], named.stderr


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
    # Every change is staged: no path holds a change the index lacks, and
    # no file is untracked.
    changes = _git(root, 'status', '--porcelain',
                   '--untracked-files=all').stdout.splitlines()
    assert len(changes) == 30, changes
    assert [line for line in changes if line[1] != ' '] == [], changes
    assert _git(root, 'diff', '--quiet').returncode == 0
    assert 'M  specs/_anchors/checkout_design.md' in changes, changes


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
    # `ci.yml` is as it was in git too: tracked, with the bytes committed.
    assert '.github/workflows/ci.yml' in _tracked(root)
    assert _git(root, 'status', '--porcelain', '--untracked-files=all',
                '--', '.github/workflows').stdout == ''
    assert subprocess.run(
        ['git', 'show', 'HEAD:.github/workflows/ci.yml'], cwd=root,
        capture_output=True).stdout == OWN_WORKFLOW_TEXT


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
    # No `removed` line for a workflow, whatever its count.
    assert [line for line in printed
            if 'removed' in line and 'workflow' in line] == [], printed
    assert [line for line in printed
            if 'that committed proof files' in line] == [], printed


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
    # Gone from git as from the disk: the commit the update made holds no
    # file of the plugin folder, and nothing is left for a later commit.
    assert [rel for rel in _tracked(root)
            if rel.startswith('.purlin/plugins/')] == []
    assert [rel for rel in _git(root, 'ls-tree', '-r', '--name-only',
                                'HEAD').stdout.splitlines()
            if rel.startswith('.purlin/plugins/')] == []
    assert _git(root, 'status', '--porcelain').stdout.splitlines() == [
        '?? .purlin/plugins/']


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
    # Committed: the latest commit holds the file, and git has nothing of
    # it left to commit.
    assert '.purlin/evidence/README.md' in _git(
        root, 'ls-tree', '-r', '--name-only', 'HEAD').stdout.splitlines()
    assert _git(root, 'status', '--porcelain', '--',
                '.purlin/evidence').stdout == ''
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
            'piano, put # purlin: piano PROOF-<n> above the test, and take '
            "the old tag out of the test's title or decorator."
            ) in printed, printed


ORPHAN_TS = 'packages/web/test/orphan.test.ts'
ORPHAN_TS_OLD = (
    "import { it } from 'vitest';\n\n"
    "it('a held key keeps sounding [proof:piano:PROOF-9c:RULE-2:unit]', "
    "() => {\n});\n")


# purlin: update PROOF-204
def test_the_comment_to_put_is_in_the_file_s_own_comment_style(tmp_path,
                                                               capsys):
    root = _lettered(tmp_path, files=((ORPHAN_TS, ORPHAN_TS_OLD),
                                      (KEYS_PY, KEYS_PY_OLD)))
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert _read(root, ORPHAN_TS) == ORPHAN_TS_OLD
    assert ('  left packages/web/test/orphan.test.ts:3 as it was: it names '
            'piano PROOF-9c, which no spec has. Write the proof with '
            'purlin:spec piano, put // purlin: piano PROOF-<n> above the '
            "test, and take the old tag out of the test's title or "
            'decorator.') in printed, printed


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
    assert _proof_ids(root, PIANO) == ['PROOF-1', 'PROOF-2', 'PROOF-2b',
                                       'PROOF-7b']
    assert '> Highest-Proof: 9' in _read(root, PIANO).splitlines()
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

def _three_marked(tmp_path, more=()):
    """The sample 0.9.5 project with three pytest files holding 2, 1 and 1
    marks of 0.9.5, and `more`, committed and not yet updated."""
    root = _project(tmp_path, V095)
    for rel, text in (('tests/test_login.py', OLD_PYTEST),
                      ('tests/test_keys.py', KEYS_PY_OLD.replace(
                          '"piano"', '"login"')),
                      ('tests/test_more.py', KEYS_PY_OLD.replace(
                          '"piano"', '"login"'))) + tuple(more):
        _write_bytes(root, rel, text.encode('utf-8'))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the tests 0.9.5 marked')
    return root


def _three_marked_files(tmp_path, capsys, more=()):
    root = _three_marked(tmp_path, more)
    _apply(root)
    return root, capsys.readouterr().out.splitlines()


# purlin: update PROOF-184
def test_each_migration_prints_one_line_of_totals(tmp_path, capsys):
    root = _three_marked(tmp_path)
    assert _apply(root) == 0
    output = capsys.readouterr()
    printed = output.out.splitlines()
    assert printed.count('  markers: rewrote 4 markers in 3 files') == 1, \
        printed
    # Neither stream of the output holds a file's own line.
    for line in printed + output.err.splitlines():
        assert not line.endswith('as comments'), line
        assert 'as comments' not in line, line
        assert 'kept the previous bytes' not in line, line
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
    assert asked[0].startswith('Apply design-refs, ') and asked[0].endswith(
        '? [y/N] y'), asked[0]
    assert asked[0].count('?') == 1, asked[0]
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
    assert done.stdout == ''
    assert done.stderr.splitlines() == [
        'everything is not a migration. The migrations are: design-refs, '
        'anchor-lines, os-tags, kind-tags, untracked-files, hooks, config, '
        'evidence, dashboard, workflows, lettered-proofs, markers, '
        'plugins.'], done.stderr
    assert _git(root, 'rev-parse', 'HEAD').stdout == head
    assert _git(root, 'status', '--porcelain').stdout == ''


# --- what the update leaves for the owner ------------------------------------------

LEFT_HEADING = 'Purlin left these for you:'
OLD_CLAUDE_MD = ('# Notes for the agent\n\n'
                 'Mark each test `[proof:feature:PROOF-1:RULE-1:unit]`.\n'
                 'In Python use `@pytest.mark.proof("feature", "PROOF-1")`.\n'
                 'The plugin lives in `.purlin/plugins/`.\n'
                 'Run `purlin:verify` before a push.\n')
CHANGE_FIRST = ('. Change it first: it tells the agent to write what this '
                'release does not read.')
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
    first = printed.index('  CLAUDE.md: 4 lines' + CHANGE_FIRST)
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
    # `<n>` is the files not listed: every tracked file a line of which
    # still holds one of the five, counted here from the files themselves,
    # less the 20 listed. The sample leaves 6 of its own beside the 22.
    holding = []
    for rel in _tracked(root):
        with open(os.path.join(root, rel), encoding='utf-8',
                  errors='replace') as handle:
            text = handle.read()
        if any(name in text for name in (
                '[proof:', 'pytest.mark.proof', '.purlin/plugins',
                'purlin:verify', 'proofs-')):
            holding.append(rel)
    assert len(holding) == 28, holding
    assert printed[heading + 21] == '  and 8 more files'
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


# --- the tags that end a proof running over several lines -----------------------

TABS = 'specs/web/tabs.md'
TABS_HEAD = ('# Feature: tabs\n\n> Description: The tab strip.\n'
             '> Scope: tabs.py\n\n## Rules\n\n'
             '- RULE-1: A tab opens\n- RULE-2: A tab closes\n'
             '- RULE-3: A tab moves\n\n## Proof\n\n')
TABS_SPEC = TABS_HEAD + (
    '- PROOF-1 (RULE-1): Choose a tab; its page shows and the others\n'
    '  are hidden. @unit\n'
    '- PROOF-2 (RULE-2): Close the tab; the strip holds one fewer and the\n'
    '  page beside it shows.\n'
    '  @browser\n'
    '- PROOF-3 (RULE-3): Drag the tab past its neighbour; the two change\n'
    '  places @integration @slow\n')
TABS_AFTER = TABS_HEAD + (
    '- PROOF-1 (RULE-1): Choose a tab; its page shows and the others\n'
    '  are hidden.\n'
    '- PROOF-2 (RULE-2): Close the tab; the strip holds one fewer and the\n'
    '  page beside it shows.\n'
    '- PROOF-3 (RULE-3): Drag the tab past its neighbour; the two change\n'
    '  places @slow\n')
TABS_TS = 'packages/web/test/tabs.browser.test.ts'
TABS_TS_OLD = (
    "import { it } from 'vitest';\n\n"
    "it('closing a tab shows the page beside it "
    "[proof:tabs:PROOF-2:RULE-2:browser]', () => {\n});\n")
WENT_RE = re.compile(r'^  kind-tags: dropped (\d+) kind-of-test tags from '
                     r'(\d+) specs: purlin:test runs every marked test$')


def _tabs(tmp_path, spec=TABS_SPEC, files=((TABS_TS, TABS_TS_OLD),)):
    root = _project(tmp_path, V095)
    _write_bytes(root, TABS, spec.encode('utf-8'))
    for rel, text in files:
        _write_bytes(root, rel, text.encode('utf-8'))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the tab strip, as 0.9.5 tagged it')
    return root


# purlin: update PROOF-196
def test_a_kind_tag_ending_a_proof_s_last_line_goes(tmp_path, capsys):
    root = _tabs(tmp_path)
    _apply(root)
    capsys.readouterr()
    assert _read(root, TABS) == TABS_AFTER


def _went(printed):
    found = [WENT_RE.match(line) for line in printed.splitlines()]
    found = [match for match in found if match]
    assert len(found) == 1, printed
    return int(found[0].group(1)), int(found[0].group(2))


# purlin: update PROOF-197
def test_the_totals_line_counts_the_tags_and_the_specs(tmp_path, capsys):
    plain = _project(tmp_path / 'plain', V095)
    _apply(plain)
    tags, specs = _went(capsys.readouterr().out)
    root = _tabs(tmp_path / 'tabs')
    _apply(root)
    assert _went(capsys.readouterr().out) == (tags + 3, specs + 1)


TAGS_KEPT = TABS_HEAD + (
    '- PROOF-1 (RULE-1): Choose a tab and look at the page it\n'
    '  shows @manual\n'
    '- PROOF-2 (RULE-2): Close each of 500 tabs; the strip\n'
    '  is empty @slow\n'
    '- PROOF-3 (RULE-3): Drag the tab past its neighbour; the two change\n'
    '  places @env(linux)\n'
    '- PROOF-4 (RULE-3): Drag the tab off the strip; it comes back\n'
    '  @browser\n')


# purlin: update PROOF-198
def test_a_tag_no_marker_names_and_the_three_kept_tags_stay(tmp_path, capsys):
    root = _tabs(tmp_path, spec=TAGS_KEPT, files=())
    _apply(root)
    capsys.readouterr()
    assert _read(root, TABS) == TAGS_KEPT
    assert update.pending(root) == []


AI_TAGS_KEPT = TABS_HEAD + (
    '- PROOF-1 (RULE-1): Ask for a tab; the reply names the tab it\n'
    '  opened @ai\n'
    '- PROOF-2 (RULE-2): Ask to close a tab; the reply says which one\n'
    '  closed @ai(claude-opus-5-5) @graded\n')
AI_TS_OLD = (
    "import { it } from 'vitest';\n\n"
    "it('asking for a tab opens it [proof:tabs:PROOF-1:RULE-1:ai]', "
    "() => {\n});\n"
    "it('asking to close a tab closes it "
    "[proof:tabs:PROOF-2:RULE-2:graded]', () => {\n});\n")


# purlin: update PROOF-229
def test_the_ai_and_graded_tags_stay_where_a_marker_names_them_as_kinds(
        tmp_path, capsys):
    root = _tabs(tmp_path, spec=AI_TAGS_KEPT, files=((TABS_TS, AI_TS_OLD),))
    _apply(root)
    capsys.readouterr()
    assert _read(root, TABS) == AI_TAGS_KEPT


WINDOWS_THEN_KIND = TABS_HEAD + (
    '- PROOF-1 (RULE-1): Choose a tab; its page shows and the others\n'
    '  are hidden @windows @unit\n')


# purlin: update PROOF-199
def test_the_windows_tag_on_a_continuation_line_is_rewritten(tmp_path,
                                                             capsys):
    root = _tabs(tmp_path, spec=WINDOWS_THEN_KIND, files=())
    _apply(root)
    capsys.readouterr()
    assert _read(root, TABS).splitlines()[-2:] == [
        '- PROOF-1 (RULE-1): Choose a tab; its page shows and the others',
        '  are hidden @env(windows)']
    assert update.pending(root) == []


# purlin: update PROOF-200
def test_a_kind_is_still_known_once_the_markers_are_rewritten(tmp_path,
                                                             capsys):
    root = _tabs(tmp_path)
    assert _apply(root, argv=('--apply', 'markers')) == 0
    assert '[proof:' not in _read(root, TABS_TS)
    assert '@browser' in _read(root, TABS)
    _apply(root)
    capsys.readouterr()
    assert _read(root, TABS) == TABS_AFTER


NOTED = TABS_HEAD + (
    '- PROOF-1 (RULE-1): Choose a tab; its page shows and the others\n'
    '  are hidden. @unit (python: the collector owns\n'
    '  this file)\n'
    '- PROOF-2 (RULE-2): Close the tab (the last one) and the strip is empty\n')


# purlin: update PROOF-205
def test_a_kind_tag_goes_from_before_a_note_in_brackets(tmp_path, capsys):
    root = _tabs(tmp_path, spec=NOTED, files=())
    _apply(root)
    capsys.readouterr()
    assert _read(root, TABS) == NOTED.replace(' @unit', '')


# --- what a run ends on -----------------------------------------------------------

HOW_TO_APPLY = ('Nothing was applied. Add --yes to apply every migration and '
                'use each proposed test command, or --apply <id>[,<id>...] '
                'to apply the migrations named.')


# purlin: update PROOF-201
def test_a_run_that_applied_nothing_ends_on_the_update_and_how_to_say_yes(
        tmp_path):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'a pytest project')
    done = _piped(root, '')
    assert done.returncode == 0, done.stderr
    printed = done.stdout.splitlines()
    assert printed[0].startswith('9 migrations pending in '), printed[0]
    assert ('      pytest: python3 -m pytest {files} --junitxml={report}'
            in printed), printed
    assert printed[-2:] == [
        '→ Run: purlin:init --update',
        'Nothing was applied. Add --yes to apply every migration and use '
        'each proposed test command, or --apply <id>[,<id>...] to apply the '
        'migrations named.'], printed[-2:]
    assert 'Left to do:' not in printed
    for line in printed + done.stderr.splitlines():
        assert 'Left to do:' not in line, line
        assert 'pass their tests' not in line, line
        assert 'purlin:build' not in line, line
        assert 'purlin:test' not in line, line


RUN_TESTS = ['→ Run: purlin:test --all --commit',
             'Run it before anything else: every rule reads not run until '
             'it has.',
             'A test that fails in that run and passes when its feature is '
             "run alone is the project's own: purlin:test <feature>."]


# purlin: update PROOF-202
def test_a_run_that_applied_everything_ends_on_the_test_run(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root)
    output = capsys.readouterr()
    printed = output.out.splitlines()
    assert printed[-3:] == [
        '→ Run: purlin:test --all --commit',
        'Run it before anything else: every rule reads not run until it has.',
        'A test that fails in that run and passes when its feature is run '
        "alone is the project's own: purlin:test <feature>."], printed[-3:]
    assert 'Left to do:' not in output.out, printed
    assert 'Left to do:' not in output.err, output.err
    assert not [line for line in printed + output.err.splitlines()
                if 'pass their tests' in line]


# purlin: update PROOF-203
def test_a_run_that_left_a_migration_pending_ends_on_the_update(tmp_path,
                                                                capsys):
    root = _project(tmp_path, V095)
    _apply(root, argv=('--apply', 'evidence'))
    output = capsys.readouterr()
    printed = output.out.splitlines()
    assert printed[-2:] == [
        '→ Run: purlin:init --update',
        '8 migrations are still pending: design-refs, anchor-lines, os-tags, '
        'kind-tags, untracked-files, config, workflows, plugins. A test run '
        'stops until nothing is pending.'], printed[-2:]
    assert RUN_TESTS[0] not in printed
    assert '→ Run: purlin:test --all --commit' not in output.out, printed
    assert '→ Run: purlin:test --all --commit' not in output.err, output.err


# --- the files that instruct an agent come first ---------------------------------

NOTES = 'Run purlin:verify.\n'


def _left(tmp_path, capsys, files):
    """What the update prints under `Purlin left these for you:` for the
    sample 0.9.5 project holding `files`, up to the line that explains it."""
    root = _project(tmp_path, V095)
    for rel, text in files:
        _write(root, rel, text)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'what 0.9.5 left in the project')
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    heading = printed.index(LEFT_HEADING)
    end = [index for index, line in enumerate(printed)
           if line.startswith('  Each line counted names')][0]
    return printed[heading + 1:end]


# purlin: update PROOF-206
def test_claude_md_stands_first_among_what_is_left(tmp_path, capsys):
    listed = _left(tmp_path, capsys, (
        ('notes/a.md', NOTES * 9), ('notes/b.md', NOTES * 7),
        ('CLAUDE.md', 'Run `purlin:verify` before a push.\n')))
    assert listed[:3] == [
        '  CLAUDE.md: 1 line' + CHANGE_FIRST,
        '  notes/a.md: 9 lines', '  notes/b.md: 7 lines'], listed


# purlin: update PROOF-207
def test_agents_md_and_the_claude_folder_follow_claude_md(tmp_path, capsys):
    listed = _left(tmp_path, capsys, (
        ('notes/a.md', NOTES * 9),
        ('.claude/commands/ship.md', NOTES * 3),
        ('.claude/RESUME.md', NOTES * 2),
        ('AGENTS.md', NOTES * 2),
        ('CLAUDE.md', NOTES)))
    assert listed[:5] == [
        '  CLAUDE.md: 1 line' + CHANGE_FIRST,
        '  AGENTS.md: 2 lines' + CHANGE_FIRST,
        '  .claude/commands/ship.md: 3 lines' + CHANGE_FIRST,
        '  .claude/RESUME.md: 2 lines' + CHANGE_FIRST,
        '  notes/a.md: 9 lines'], listed


# --- a docstring line that is only a 0.9.5 tag -------------------------------------

DOCS_PY = 'tests/test_docs.py'
DOCS_PY_OLD = (
    'import pytest\n\n\n'
    '@pytest.mark.proof("piano", "PROOF-1", "RULE-1")\n'
    'def test_a_key_sounds() -> None:\n'
    '    """[proof:piano:PROOF-1:RULE-1:unit]"""\n'
    '    assert 1 + 1 == 2\n\n\n'
    '@pytest.mark.proof("piano", "PROOF-2", "RULE-2")\n'
    'def test_a_key_stops() -> None:\n'
    '    """[proof:piano:PROOF-2:RULE-2:unit]\n\n'
    '    Measured on the long clip: the note ends within one line.\n'
    '    """\n'
    '    assert 2 + 2 == 4\n\n\n'
    'class TestRelease:\n'
    '    @pytest.mark.proof("piano", "PROOF-2b", "RULE-2")\n'
    '    def test_stops_on_the_line(self) -> None:\n'
    '        """\n'
    '        Part way through a bar.\n\n'
    '        [proof:piano:PROOF-2b:RULE-2:integration]\n'
    '        """\n'
    '        assert True\n')
DOCS_PY_NEW = (
    'import pytest\n\n\n'
    '# purlin: piano PROOF-1\n'
    'def test_a_key_sounds() -> None:\n'
    '    assert 1 + 1 == 2\n\n\n'
    '# purlin: piano PROOF-2\n'
    'def test_a_key_stops() -> None:\n'
    '    """Measured on the long clip: the note ends within one line.\n'
    '    """\n'
    '    assert 2 + 2 == 4\n\n\n'
    'class TestRelease:\n'
    '    # purlin: piano PROOF-10\n'
    '    def test_stops_on_the_line(self) -> None:\n'
    '        """\n'
    '        Part way through a bar.\n'
    '        """\n'
    '        assert True\n')
TAG_LINES_WENT = '    removed %d docstring line%s that held only a 0.9.5 tag'


# purlin: update PROOF-208
def test_a_docstring_line_that_is_only_a_tag_goes(tmp_path, capsys):
    root = _lettered(tmp_path, files=((DOCS_PY, DOCS_PY_OLD),))
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert _read(root, DOCS_PY) == DOCS_PY_NEW
    compile(_read(root, DOCS_PY), DOCS_PY, 'exec')
    at = printed.index('  markers: rewrote 3 markers in 1 file')
    assert printed[at + 1] == TAG_LINES_WENT % (3, 's'), printed[at:at + 2]
    assert not [line for line in printed if line.startswith('  ' + DOCS_PY)]


SENTENCE_PY = 'tests/test_sentence.py'
SENTENCE_PY_OLD = (
    'import pytest\n\n\n'
    '@pytest.mark.proof("piano", "PROOF-1", "RULE-1")\n'
    'def test_a_key_sounds():\n'
    '    """Covers [proof:piano:PROOF-1:RULE-1:unit] on the long clip."""\n'
    '    assert True\n')


# purlin: update PROOF-209
def test_a_tag_in_a_sentence_stays_and_is_counted(tmp_path, capsys):
    root = _lettered(tmp_path, files=((SENTENCE_PY, SENTENCE_PY_OLD),))
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert _read(root, SENTENCE_PY) == SENTENCE_PY_OLD.replace(
        '@pytest.mark.proof("piano", "PROOF-1", "RULE-1")',
        '# purlin: piano PROOF-1')
    assert printed.index('  %s: 1 line' % SENTENCE_PY) > printed.index(
        LEFT_HEADING)
    assert not [line for line in printed if 'held only a 0.9.5 tag' in line]


KEPT_PY = 'tests/test_kept.py'
KEPT_PY_OLD = (
    'import pytest\n\n\n'
    '@pytest.mark.proof("piano", "PROOF-2", "RULE-2")\n'
    'def test_a_key_stops():\n'
    '    """[proof:piano:PROOF-2:RULE-2:unit]"""\n\n\n'
    '@pytest.mark.proof("piano", "PROOF-9c", "RULE-2")\n'
    'def test_names_a_proof_no_spec_has():\n'
    '    """[proof:piano:PROOF-9c:RULE-2:unit]"""\n'
    '    assert True\n\n\n'
    'def test_no_marker():\n'
    '    """[proof:piano:PROOF-1:RULE-1:unit]"""\n'
    '    assert True\n')


# purlin: update PROOF-215
def test_a_docstring_the_update_cannot_take_stays(tmp_path, capsys):
    root = _lettered(tmp_path, files=((KEPT_PY, KEPT_PY_OLD),))
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert _read(root, KEPT_PY) == KEPT_PY_OLD.replace(
        '@pytest.mark.proof("piano", "PROOF-2", "RULE-2")',
        '# purlin: piano PROOF-2')
    assert '  %s: 4 lines' % KEPT_PY in printed, printed
    assert not [line for line in printed if 'held only a 0.9.5 tag' in line]
    # Listed under the heading: the heading stands once, above the file's
    # line, with nothing but other files' lines between the two.
    assert printed.count('Purlin left these for you:') == 1, printed
    heading = printed.index('Purlin left these for you:')
    at = printed.index('  tests/test_kept.py: 4 lines')
    assert printed[heading - 1] == '', printed
    assert heading < at, printed
    for line in printed[heading + 1:at]:
        assert re.match(r'^  \S+: \d+ lines?$', line), line


# --- the script the proposal cites ---------------------------------------------------

def _scripts_project(tmp_path, scripts):
    root = _project(tmp_path, V095)
    _set_config(root, test_framework='vitest')
    _write(root, 'package.json', json.dumps({
        'name': 'studio', 'scripts': scripts,
        'devDependencies': {'vitest': '^3.0.0'}}, indent=2) + '\n')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'vitest in tiers')
    return root


def _proposal(root, tool):
    """The lines the listing run prints for `tool` under `config`."""
    done = _piped(root, '')
    assert done.returncode == 0, done.stderr
    printed = done.stdout.splitlines()
    at = [index for index, line in enumerate(printed)
          if line.startswith('      %s: ' % tool)][0]
    lines = [printed[at]]
    for line in printed[at + 1:]:
        if not line.startswith('        '):
            break
        lines.append(line)
    return lines


VITEST_PROPOSED = '      vitest: ' + frameworks.entry_for('vitest')['run']


# purlin: update PROOF-210
def test_the_proposal_cites_the_script_it_is_closest_to(tmp_path):
    root = _scripts_project(tmp_path, {
        'test': 'vitest run --project unit',
        'test:integration': 'vitest run --project integration',
        'test:all': 'vitest run'})
    assert _proposal(root, 'vitest') == [
        VITEST_PROPOSED,
        '        package.json, "test:all", runs it as: vitest run']


# purlin: update PROOF-211
def test_the_proposal_says_which_option_of_the_script_it_leaves_out(tmp_path):
    root = _scripts_project(tmp_path, {'test': 'vitest run --project unit'})
    assert _proposal(root, 'vitest') == [
        VITEST_PROPOSED,
        '        package.json, "test", runs it as: vitest run --project unit',
        '        The proposal leaves out --project unit, so every vitest '
        'test runs.']


# purlin: update PROOF-212
def test_an_option_that_narrows_nothing_is_not_named(tmp_path):
    root = _scripts_project(tmp_path, {
        'test': 'vitest run --coverage --reporter=dot'})
    assert _proposal(root, 'vitest') == [
        VITEST_PROPOSED,
        '        package.json, "test", runs it as: vitest run --coverage '
        '--reporter=dot']


# --- a run told to apply prints one line in place of the pending list ----------------

# purlin: update PROOF-213
def test_a_run_with_yes_prints_one_line_in_place_of_the_pending_list(
        tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == 'Applying 9 migrations: %s.' % ', '.join(NINE)
    assert printed[1].startswith('.github/workflows/') and \
        ' names a proof file: ' in printed[1], printed[1]
    assert printed[1] == (".github/workflows/windows-proofs.yml:11 names a "
                          "proof file: - '**/*.proofs-windows.json'"), \
        printed[1]
    assert printed[2].startswith('  design-refs: '), printed[2]
    # The line of totals: the sample holds two specs with a design reference.
    assert printed[2] == ('  design-refs: removed the design reference from '
                          '2 specs'), printed[2]
    assert printed[3].startswith('  anchor-lines: '), printed[3]
    assert not [line for line in printed if 'pending in' in line]
    assert not [line for line in printed
                if line.startswith('      specs/')]
    # The lines of the migrations end at the commit; none names a spec.
    committed = [index for index, line in enumerate(printed)
                 if line.startswith('  committed ')]
    assert len(committed) == 1, printed
    assert [line for line in printed[1:committed[0]]
            if 'specs/' in line] == [], printed[:committed[0]]
    # Under a migration stands nothing but what the settings migration
    # says of the test tools and the keys: each other line is one line of
    # totals, one for each migration that has one, in order.
    block = printed[2:committed[0]]
    totals = [line for line in block if re.match(r'  [a-z-]+: ', line)]
    assert [line.split(':')[0].strip() for line in totals] == [
        'design-refs', 'anchor-lines', 'os-tags', 'kind-tags',
        'untracked-files', 'config', 'evidence', 'plugins'], totals
    under = [line for line in block if line not in totals]
    assert under[0].startswith('    pytest: '), under
    assert under[1:] == [
        '    dropped jest from the tests: nothing in the tree runs it',
        '    dropped shell from the tests: nothing in the tree runs it',
        '    dropped vitest from the tests: nothing in the tree runs it',
        '    removed from .purlin/config.json: test_framework, spec_dir, '
        'pre_push, report, digest'], under


# purlin: update PROOF-214
def test_a_run_with_apply_names_the_migrations_it_applies(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root, argv=('--apply', 'evidence'))
    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == 'Applying 1 migration: evidence.'
    assert [line for line in printed if line.startswith('  evidence: ')]
    assert not [line for line in printed if 'pending in' in line]


MIXED_TS = 'packages/web/test/mixed.test.ts'
MIXED_TS_OLD = (
    "import { it } from 'vitest';\n\n"
    "it('two keys sound two notes [proof:piano:PROOF-7b:RULE-6:unit]', "
    "() => {\n});\n\n"
    "it('a held key keeps sounding [proof:piano:PROOF-9c:RULE-2:unit]', "
    "() => {\n});\n")


# purlin: update PROOF-216
def test_a_left_marker_is_named_at_its_line_after_the_rewrite(tmp_path,
                                                             capsys):
    root = _lettered(tmp_path, files=((MIXED_TS, MIXED_TS_OLD),
                                      (KEYS_PY, KEYS_PY_OLD)))
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    lines = _read(root, MIXED_TS).splitlines()
    at = next(number for number, text in enumerate(lines, 1)
              if 'PROOF-9c' in text)
    assert at == 7, lines
    assert any(line.startswith('  left %s:%d as it was: it names piano '
                               'PROOF-9c' % (MIXED_TS, at))
               for line in printed), printed


# --- the lines 0.9.5 wrote into the files that instruct an agent ----------------

AGENT_MD_OLD = (
    '# Notes for the agent\n'
    '\n'
    'Keep each change small. Run the whole suite before a push.\n'
    '\n'
    '## Testing\n'
    '\n'
    '- Write the spec first.\n'
    '- Name each test with its marker,\n'
    '  `[proof:<feature>:PROOF-n:RULE-n:unit]`, so the plugin records it.\n'
    '  - The tier is the last field.\n'
    '- Run `npm test` for the rest.\n'
    '\n'
    '| Command | What it does |\n'
    '|---|---|\n'
    '| `npm test` | runs every test |\n'
    '| `purlin:verify` | writes the receipts |\n'
    '\n'
    '## The proof plugin\n'
    '\n'
    'The plugin under `.purlin/plugins/` records each result.\n'
    '\n'
    '## Commands\n'
    '\n'
    '```\n'
    'npm test\n'
    'npm run verify   # purlin:verify\n'
    '```\n'
    '\n'
    'The collector writes `specs/<group>/*.proofs-unit.json` from the\n'
    'working directory; set it up once. Mixed features keep their\n'
    'proofs together. The suite takes a minute.\n'
    '\n'
    'Rules are numbered. The old collector read `PROOF-4b` from\n'
    '`.purlin/plugins/vitest_purlin.ts`.\n')
AGENT_MD_NEW = (
    '# Notes for the agent\n'
    '\n'
    'Keep each change small. Run the whole suite before a push.\n'
    '\n'
    '## Testing\n'
    '\n'
    '- Write the spec first.\n'
    '- Run `npm test` for the rest.\n'
    '\n'
    '| Command | What it does |\n'
    '|---|---|\n'
    '| `npm test` | runs every test |\n'
    '\n'
    '## Commands\n'
    '\n'
    '```\n'
    'npm test\n'
    '```\n'
    '\n'
    'Mixed features keep their\n'
    'proofs together. The suite takes a minute.\n'
    '\n'
    'Rules are numbered.\n')


def _agent_files(tmp_path, files, argv=('--yes',)):
    """The sample 0.9.5 project with one test file 0.9.5 marked, so that
    `markers` is pending, and `files`, updated with `argv`."""
    root = _project(tmp_path, V095)
    _write(root, 'tests/test_login.py', OLD_PYTEST)
    for rel, text in files:
        _write_bytes(root, rel, text.encode('utf-8'))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'what 0.9.5 told the agent')
    _apply(root, argv)
    return root


# purlin: update PROOF-217
def test_each_line_naming_0_9_5_goes_from_claude_md(tmp_path, capsys):
    root = _agent_files(tmp_path, (('CLAUDE.md', AGENT_MD_OLD),))
    assert _read(root, 'CLAUDE.md') == AGENT_MD_NEW
    assert 'markers' not in _ids(root)


SETTINGS_OLD = ('{\n'
                '  "permissions": {\n'
                '    "allow": [\n'
                '      "Bash(npm test)",\n'
                '      "Skill(purlin:verify)"\n'
                '    ]\n'
                '  }\n'
                '}\n')
CHECK_SH = ('#!/bin/sh\n'
            'echo "run purlin:verify before a push"\n')


# purlin: update PROOF-218
def test_agents_md_and_the_claude_folder_lose_the_lines_too(tmp_path, capsys):
    root = _agent_files(tmp_path, (
        ('pipeline/AGENTS.md', '# Pipeline\n\n- Run `purlin:verify`.\n'
                               '- Run `uv run pytest`.\n'),
        ('.claude/commands/ship.md', 'Ship it.\n\n- Run `purlin:verify`.\n'),
        ('.claude/commands/check.md', '---\ndescription: Run purlin:verify.\n'
                                      '---\n\nCheck the build.\n'),
        ('.claude/settings.json', SETTINGS_OLD),
        ('.claude/hooks/check.sh', CHECK_SH)))
    assert _read(root, 'pipeline/AGENTS.md') == (
        '# Pipeline\n\n- Run `uv run pytest`.\n')
    assert _read(root, '.claude/commands/ship.md') == 'Ship it.\n'
    assert _read(root, '.claude/commands/check.md') == (
        '---\n---\n\nCheck the build.\n')
    assert json.loads(_read(root, '.claude/settings.json')) == {
        'permissions': {'allow': ['Bash(npm test)']}}
    assert _read(root, '.claude/hooks/check.sh') == CHECK_SH
    printed = capsys.readouterr().out.splitlines()
    assert '  .claude/hooks/check.sh: 1 line' + CHANGE_FIRST in printed
    # Listed under the heading, which stands once, right above its line:
    # a file under `.claude/` stands first among what is left.
    assert printed.count('Purlin left these for you:') == 1, printed
    heading = printed.index('Purlin left these for you:')
    assert printed[heading - 1] == '', printed
    assert printed[heading + 1].startswith(
        '  .claude/hooks/check.sh: 1 line. '), printed[heading + 1]


# purlin: update PROOF-219
def test_the_totals_the_log_and_the_backup_name_each_line_removed(tmp_path,
                                                                  capsys):
    root = _agent_files(tmp_path, (('CLAUDE.md', AGENT_MD_OLD),))
    printed = capsys.readouterr().out.splitlines()
    totals = printed.index('  markers: rewrote 2 markers in 1 file')
    assert printed[totals + 1] == (
        '    removed 6 lines that named 0.9.5 from CLAUDE.md'), printed
    log = _log(root)
    assert ('removed CLAUDE.md:9: `[proof:<feature>:PROOF-n:RULE-n:unit]`, '
            'so the plugin records it.') in log, log
    assert 'removed CLAUDE.md:16: | `purlin:verify` | writes the receipts |' \
        in log, log
    assert 'removed CLAUDE.md:18: ## The proof plugin' in log, log
    assert 'removed CLAUDE.md:26: npm run verify   # purlin:verify' in log, log
    assert ('CLAUDE.md:30 now reads: Mixed features keep their') in log, log
    assert _read_bytes(root, BACKUPS + '/CLAUDE.md') == \
        AGENT_MD_OLD.encode('utf-8')
    assert not [line for line in printed if line.startswith('  CLAUDE.md:')]
    assert _git(root, 'status', '--porcelain').stdout == ''


# purlin: update PROOF-220
def test_claude_md_is_left_where_markers_is_declined(tmp_path, capsys,
                                                     monkeypatch):
    _answers(monkeypatch, rules=(('Apply markers', 'n'),))
    root = _agent_files(tmp_path, (('CLAUDE.md', AGENT_MD_OLD),), argv=())
    assert _read(root, 'CLAUDE.md') == AGENT_MD_OLD
    printed = capsys.readouterr().out.splitlines()
    assert not [line for line in printed if 'that named 0.9.5' in line]
    assert '  CLAUDE.md: 6 lines' + CHANGE_FIRST in printed, printed


# --- a project 0.9.5 did not set up -------------------------------------------

IGNORE = '.gitignore'
EVIDENCE_README = '.purlin/evidence/README.md'
SETTINGS = '.purlin/config.json'
PAGE = 'purlin-report.html'
FOR = {
    IGNORE: 'keeps .purlin/runtime/ and .purlin/report-data.js out of git: '
            'each run writes them again',
    EVIDENCE_README: 'says what the evidence folder holds',
    SETTINGS: 'holds the settings, with version reading %s' % VERSION,
    PAGE: 'the dashboard page, as this version ships it',
}
NOTHING_RESTORED = 'Nothing was restored. Add --yes to restore each file.'
# What only a project 0.9.5 set up is told.
OF_095 = ('0.9.5', 'migrat', 'not run', 'verify:', 'update-backup',
          'Run it before anything else', 'beside the specs', 'untracked',
          'Applying', 'Purlin left these for you:', 'These need you:')


def _fresh(tmp_path):
    """A project this release set up, built by `sample_lab`: its `.gitignore`
    lacks `.purlin/report-data.js` and it has no evidence README. Its tests
    have run once, so the status counts its rules."""
    root = sample_lab.build(tmp_path)
    _git(root, 'config', 'user.name', 'Test Person')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'config', 'commit.gpgsign', 'false')
    return root


def _status_ending(root):
    """The lines the status ends on, as it prints them now."""
    return status_module.sync_status(root).rsplit('\n\n', 1)[-1].splitlines()


def _head(root):
    return _git(root, 'rev-parse', 'HEAD').stdout.strip()


# purlin: update PROOF-221
def test_a_project_of_this_release_has_its_missing_files_restored_and_named(
        tmp_path, capsys):
    root = _fresh(tmp_path)
    assert _ids(root) == ['untracked-files', 'evidence']
    was = _read(root, IGNORE)
    assert _apply(root) == 0
    printed = capsys.readouterr().out.splitlines()
    sha = _git(root, 'rev-parse', '--short', 'HEAD').stdout.strip()
    subject = 'chore(update): restore %s, %s' % (IGNORE, EVIDENCE_README)
    assert printed[:5] == [
        'Restoring 2 files: %s, %s.' % (IGNORE, EVIDENCE_README),
        '  restored %s: %s' % (IGNORE, FOR[IGNORE]),
        '  restored %s: %s' % (EVIDENCE_README, FOR[EVIDENCE_README]),
        '  committed %s as %s' % (sha, subject),
        ''], printed
    assert _git(root, 'log', '-1', '--format=%s').stdout.strip() == subject
    assert _git(root, 'show', '--name-only', '--format=',
                'HEAD').stdout.split() == [IGNORE, EVIDENCE_README]
    assert _read_bytes(root, EVIDENCE_README) == _read_bytes(
        ROOT, 'templates/evidence-readme.md')
    assert _read(root, IGNORE) == was + (
        '\n# Regenerated locally, never committed\n.purlin/report-data.js\n')
    assert _ids(root) == []


# purlin: update PROOF-222
def test_a_restoring_run_ends_as_the_status_ends(tmp_path, capsys):
    root = _fresh(tmp_path)
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    ending = _status_ending(root)
    assert [line for line in ending if 'pass' in line], ending
    assert 'Left to do:' in ending, ending
    assert printed[-len(ending) - 1:] == [''] + ending, printed
    assert len(printed) == 4 + 1 + len(ending), printed


# purlin: update PROOF-223
def test_a_restoring_run_says_nothing_of_0_9_5_and_keeps_no_copy(tmp_path,
                                                               capsys):
    root = _fresh(tmp_path)
    _apply(root)
    output = capsys.readouterr()
    # Both streams: a sentence on the error stream is output of the run too.
    printed = output.out + output.err
    assert output.out.strip(), 'the run printed nothing'
    for word in ('0.9.5', 'migrat', 'not run', 'verify:', 'update-backup',
                 'Run it before anything else', 'beside the specs',
                 'untracked', 'Applying', 'Purlin left these for you:',
                 'These need you:'):
        assert word not in output.out, (word, output.out)
        assert word not in output.err, (word, output.err)
    assert [word for word in OF_095 if word in printed] == [], printed
    assert not os.path.exists(os.path.join(root, BACKUPS))
    assert not os.path.exists(
        os.path.join(root, '.purlin', 'runtime', 'update-backup'))


# purlin: update PROOF-224
def test_a_restoring_run_lists_each_file_and_asks_about_it(tmp_path, capsys):
    root = _fresh(tmp_path)
    head, status = _head(root), _git(root, 'status', '--porcelain').stdout
    done = subprocess.run(
        [sys.executable, UPDATE, '--project-root', root],
        capture_output=True, encoding='utf-8', stdin=subprocess.DEVNULL)
    assert done.returncode == 0, done.stderr
    assert done.stdout.splitlines() == [
        '2 files to restore in %s:' % os.path.abspath(root),
        '  %s: %s' % (IGNORE, FOR[IGNORE]),
        '  %s: %s' % (EVIDENCE_README, FOR[EVIDENCE_README]),
        '',
        'Restore %s? [y/N] n' % IGNORE,
        'Restore %s? [y/N] n' % EVIDENCE_README,
        '',
        '  skipped %s' % IGNORE,
        '  skipped %s' % EVIDENCE_README,
        '',
        UPDATE_LINE,
        NOTHING_RESTORED], done.stdout
    assert _head(root) == head
    assert _git(root, 'status', '--porcelain').stdout == status


# purlin: update PROOF-225
def test_one_file_restored_leaves_the_other_and_the_status_names_the_update(
        tmp_path, capsys, monkeypatch):
    root = _fresh(tmp_path)
    _answers(monkeypatch, rules=(('Restore %s?' % IGNORE, 'n'),))
    _apply(root, argv=())
    printed = capsys.readouterr().out.splitlines()
    assert '  skipped %s' % IGNORE in printed, printed
    assert '  restored %s: %s' % (EVIDENCE_README,
                                  FOR[EVIDENCE_README]) in printed
    assert _git(root, 'log', '-1', '--format=%s').stdout.strip() == (
        'chore(update): restore %s' % EVIDENCE_README)
    assert _ids(root) == ['untracked-files']
    ending = _status_ending(root)
    assert ending[0] == UPDATE_LINE, ending
    assert printed[-len(ending):] == ending, printed


# purlin: update PROOF-226
def test_a_stale_version_and_a_page_not_shipped_are_restored_too(tmp_path,
                                                                 capsys):
    root = _fresh(tmp_path)
    tests = _config(root)['tests']
    _set_config(root, version='0.0.1')
    _write(root, PAGE, 'an older page\n')
    _git(root, 'add', SETTINGS, PAGE)
    _git(root, 'commit', '-qm', 'an older stamp and page')
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    files = [IGNORE, SETTINGS, EVIDENCE_README, PAGE]
    assert printed[:5] == (
        ['Restoring 4 files: %s.' % ', '.join(files)]
        + ['  restored %s: %s' % (rel, FOR[rel]) for rel in files]), printed
    assert _config(root) == {'version': VERSION, 'tests': tests}
    assert _read_bytes(root, PAGE) == _read_bytes(
        ROOT, 'scripts/report/purlin-report.html')
    assert [word for word in OF_095 if word in '\n'.join(printed)] == []
    assert _ids(root) == []


# purlin: update PROOF-227
def test_settings_with_no_tests_setting_make_it_a_project_0_9_5_set_up(
        tmp_path, capsys):
    root = _fresh(tmp_path)
    _write(root, SETTINGS, json.dumps({'version': '0.9.5',
                                       'test_framework': 'pytest'}))
    _git(root, 'commit', '-qam', 'the settings 0.9.5 wrote')
    before = _git(root, 'rev-parse', '--short', 'HEAD').stdout.strip()
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == ('Applying 3 migrations: untracked-files, config, '
                          'evidence.'), printed
    assert NOT_RUN in printed
    assert OLD_RECORD % before in printed
    assert BACKUPS_LINE % before in printed
    assert printed[-3:] == RUN_TESTS, printed
    assert _git(root, 'log', '-1', '--format=%s').stdout.strip() == (
        'chore(update): migrate to %s (untracked-files, config, evidence)'
        % VERSION)
    assert not [line for line in printed if 'restored' in line.split(':')[0]]


# purlin: update PROOF-228
def test_a_line_0_9_5_wrote_in_gitignore_makes_it_a_project_0_9_5_set_up(
        tmp_path, capsys):
    root = _fresh(tmp_path)
    _write(root, IGNORE, _read(root, IGNORE) + '.purlin/cache/\n')
    _git(root, 'commit', '-qam', 'the line 0.9.5 wrote for its cache')
    _apply(root)
    printed = capsys.readouterr().out.splitlines()
    assert printed[0] == 'Applying 2 migrations: untracked-files, evidence.'
    assert NOT_RUN in printed
    assert printed[-3:] == RUN_TESTS, printed
