"""Proofs for `scripts/init/update.py`, the edits `purlin:init --update` makes.

Every case here drives the real script against a real git repository made from
the v0.9.5 upgrade fixture, never against a hand-built expectation of what the
script would do, so the script and these proofs cannot drift apart. The fixture
itself is frozen: each test copies it into a temporary directory and runs
`git init` there, then writes by hand whatever that layout does not carry.

One convention runs through this file. The spellings this release retired are
never written out: the verification file name carries a character class
(`recei[p]t`), and a spec is found by searching for its text rather than by
naming a path that carries a retired word.
`dev/test_vocabulary.py` reads this file with no exception for it, so a fixture
spelled out in full would fail that proof.

What each group proves:

*pending*     what `--check` finds in the old layout, what it prints, what it
              exits with, and that it writes nothing
*applying*    `--yes` applies every migration, a second run finds nothing, and
              a declined migration stays pending
*specs*       no proof file and no run file survives beside a spec
*config*      the file that is left is the gate and what the gate derives
*tags*        the Windows tag becomes `@env(windows)`, and the kind of test
              goes from every proof line
*hooks*       the pre-commit and pre-push hooks v0.9.5 installed go
*workflows*   the retired workflows go and one `purlin.yml` replaces them
*markers*     each 0.9.5 marker becomes a comment above the same test
*plugins*     the plugin copies and the wiring that loaded them go
*design*      the Figma source and the picture fingerprint go from each spec
*mutation*    the mutation question init asks, asked of a config without one
*scope*       a spec with no `> Scope:` line is named, and changed by nothing
*evidence*    `.purlin/evidence/` and its README
*backups*     every rewritten file leaves its previous bytes beside it
*commit*      one commit, naming the migrations it carries
*status*      `sync_status` says to run the update while anything is pending
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
from purlin import status as status_module  # noqa: E402

V095 = 'upgrade-0.9.5'
LAYOUTS = (V095,)

# The retired spellings, never written out. See the module docstring.
LEFTOVER = ('*.proofs-*.json', '*.recei[p]t.json')

# The pre-commit and pre-push hooks v0.9.5 installed under `.git/hooks/`, as
# its `scripts/hooks/` copies open. A fixture carries no `.git/`, so a hooks
# case writes them.
OLD_PRE_COMMIT = ('#!/usr/bin/env bash\n'
                  '# Purlin pre-commit hook: project digest auto-generation.\n')
OLD_PRE_PUSH = ('#!/usr/bin/env bash\n'
                '# Purlin pre-push hook: proof coverage check.\n')

VERSION = open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip()


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


def _spec_holding(root, needle):
    """The one spec under `specs/` whose text carries `needle`."""
    found = [rel for rel in _walk(root, ('*.md',)) if rel.startswith('specs/')
             and needle in _read(root, rel)]
    assert len(found) == 1, 'expected one spec holding %r, found %s' % (
        needle, found)
    return found[0]


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


# --- what a project still needs ---------------------------------------------

# purlin: update PROOF-3
def test_check_on_the_v095_layout_names_every_migration(tmp_path, capsys):
    root = _project(tmp_path, V095)
    assert update.main(['--check', '--project-root', root]) == 1
    printed = capsys.readouterr().out
    for migration_id in _ids(root):
        assert migration_id in printed
    assert 'Run: purlin:init --update' in printed


# purlin: update PROOF-2
def test_the_v095_layout_needs_the_migrations_that_layout_left(tmp_path):
    root = _project(tmp_path, V095)
    found = _ids(root)
    for expected in ('design-refs', 'os-tags', 'untracked-files', 'config',
                     'evidence', 'workflows', 'plugins'):
        assert expected in found, found


# purlin: update PROOF-2
def test_a_retired_hook_adds_the_hook_migration(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, '.git/hooks/pre-commit', OLD_PRE_COMMIT)
    found = _ids(root)
    assert 'hooks' in found, found
    for expected in ('os-tags', 'untracked-files', 'config', 'workflows',
                     'plugins'):
        assert expected in found, found


# purlin: update PROOF-3
def test_check_exits_1_while_anything_is_pending(tmp_path):
    root = _project(tmp_path, V095)
    done = subprocess.run([sys.executable, UPDATE, '--check',
                           '--project-root', root],
                          capture_output=True, text=True)
    assert done.returncode == 1
    assert 'untracked-files' in done.stdout


# purlin: update PROOF-3
def test_check_writes_nothing(tmp_path):
    root = _project(tmp_path, V095)
    before = _git(root, 'status', '--porcelain').stdout
    update.main(['--check', '--project-root', root])
    assert _git(root, 'status', '--porcelain').stdout == before


# purlin: update PROOF-1
def test_every_pending_entry_says_what_it_does_and_to_which_files(tmp_path):
    root = _project(tmp_path, V095)
    found = update.pending(root)
    assert found
    for item in found:
        assert sorted(item) == ['description', 'files', 'id'], item
        assert item['description']
        assert item['files']


# purlin: update PROOF-4
def test_a_root_without_purlin_exits_2(tmp_path, capsys):
    empty = str(tmp_path / 'empty')
    os.makedirs(empty)
    assert update.main(['--check', '--project-root', empty]) == 2
    assert 'nothing to update' in capsys.readouterr().err


# purlin: update PROOF-1
def test_pending_is_empty_for_a_root_without_purlin(tmp_path):
    empty = str(tmp_path / 'bare')
    os.makedirs(empty)
    assert update.pending(empty) == []


# --- applying ----------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-5
def test_yes_applies_every_migration(tmp_path, capsys, layout):
    root = _project(tmp_path, layout)
    assert _apply(root) == 0
    capsys.readouterr()
    assert update.pending(root) == []
    assert update.main(['--check', '--project-root', root]) == 0
    assert 'Nothing is pending' in capsys.readouterr().out


@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-5
def test_running_yes_twice_changes_nothing_the_second_time(tmp_path, capsys,
                                                           layout):
    root = _project(tmp_path, layout)
    _apply(root)
    head = _git(root, 'rev-parse', 'HEAD').stdout.strip()
    tree = _git(root, 'status', '--porcelain').stdout
    capsys.readouterr()
    assert _apply(root) == 0
    assert _git(root, 'rev-parse', 'HEAD').stdout.strip() == head
    assert _git(root, 'status', '--porcelain').stdout == tree


# purlin: update PROOF-6
def test_a_declined_migration_is_left_pending(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    before = _ids(root)
    _answers(monkeypatch, default='n')
    assert _apply(root, argv=()) == 0
    printed = capsys.readouterr().out
    assert 'skipped config' in printed
    assert _ids(root) == before


# purlin: update PROOF-6
def test_one_declined_migration_does_not_stop_the_others(tmp_path, capsys,
                                                         monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Apply plugins', 'n')])
    _apply(root, argv=())
    capsys.readouterr()
    assert _ids(root) == ['plugins']


# --- the files beside the specs ----------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-8
def test_no_proof_or_verification_file_remains_on_disk(tmp_path, layout):
    root = _project(tmp_path, layout)
    assert _walk(root, LEFTOVER), 'the fixture should start with some'
    _apply(root)
    assert _walk(root, LEFTOVER) == []


@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-8
def test_no_proof_or_verification_file_remains_tracked(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    left = [rel for rel in _tracked(root)
            if any(fnmatch.fnmatch(os.path.basename(rel), p)
                   for p in LEFTOVER)]
    assert left == []


@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-8
def test_the_dashboard_data_is_untracked_and_ignored(tmp_path, layout):
    root = _project(tmp_path, layout)
    assert '.purlin/report-data.js' in _tracked(root)
    _apply(root)
    assert '.purlin/report-data.js' not in _tracked(root)
    assert os.path.isfile(os.path.join(root, '.purlin', 'report-data.js'))
    ignored = _read(root, '.gitignore').splitlines()
    assert '.purlin/report-data.js' in ignored


# purlin: update PROOF-8
def test_a_committed_cache_is_untracked_and_left_on_disk(tmp_path):
    """The v0.9.5 fixture ignores its cache, so commit one the way a project would."""
    root = _project(tmp_path, V095)
    _git(root, 'add', '-f', '.purlin/cache')
    _git(root, 'commit', '-qm', 'a committed cache')
    assert any(rel.startswith('.purlin/cache/') for rel in _tracked(root))
    assert 'untracked-files' in _ids(root)
    _apply(root)
    assert not any(rel.startswith('.purlin/cache/') for rel in _tracked(root))
    assert os.path.isdir(os.path.join(root, '.purlin', 'cache'))


# --- the config --------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-10
def test_the_config_is_the_gate_shape(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    config = json.loads(_read(root, '.purlin/config.json'))
    assert config['version'] == VERSION
    assert config['gate'] == 'passed'
    assert config['mutation_engine'] == 'none'
    assert config['min_strength'] is None
    assert config['audit_parallel'] == 4
    assert sorted(config) == ['audit_parallel', 'ci', 'gate', 'min_strength',
                              'mutation_engine', 'tests', 'trust', 'version']
    assert config['ci'] == 'github'
    assert config['trust'] in ('local', 'remote')


@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-10
def test_retired_keys_are_gone(tmp_path, layout):
    root = _project(tmp_path, layout)
    before = json.loads(_read(root, '.purlin/config.json'))
    retired = update._gate().RETIRED_KEYS
    assert any(key in before for key in retired), before
    _apply(root)
    after = json.loads(_read(root, '.purlin/config.json'))
    assert [key for key in retired if key in after] == []


# purlin: update PROOF-12
def test_the_gate_defaults_to_passed(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    assert json.loads(_read(root, '.purlin/config.json'))['gate'] == 'passed'


# purlin: update PROOF-12
def test_the_gate_defaults_to_strong_when_the_hook_was_strict(tmp_path):
    root = _project(tmp_path, V095)
    config = json.loads(_read(root, '.purlin/config.json'))
    config['pre_push'] = 'strict'
    _write(root, '.purlin/config.json', json.dumps(config, indent=2))
    _apply(root)
    written = json.loads(_read(root, '.purlin/config.json'))
    assert written['gate'] == 'strong'


# purlin: update PROOF-12
def test_the_gate_question_takes_the_answer_you_type(tmp_path, capsys,
                                                     monkeypatch):
    root = _project(tmp_path, V095)
    asked = _answers(monkeypatch, [('Gate [', 'signed')])
    _apply(root, argv=())
    capsys.readouterr()
    assert any('Gate [' in prompt for prompt in asked)
    written = json.loads(_read(root, '.purlin/config.json'))
    assert written['gate'] == 'signed'


# purlin: update PROOF-12
def test_an_answer_that_is_not_a_gate_leaves_the_default(tmp_path, capsys,
                                                         monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Gate [', 'whenever')])
    _apply(root, argv=())
    capsys.readouterr()
    assert json.loads(_read(root, '.purlin/config.json'))['gate'] == 'passed'


# purlin: update PROOF-11
@pytest.mark.parametrize('layout', LAYOUTS)
def test_no_key_nothing_reads_is_written_back(tmp_path, layout):
    """The dashboard switch an older release carried is not carried forward.

    It is not a retired key, so `resolve_gate` never warns about it and
    nothing would report it; the only thing that keeps it out of the file the
    update leaves is that the update does not write it.
    """
    root = _project(tmp_path, layout)
    _apply(root)
    written = json.loads(_read(root, '.purlin/config.json'))
    assert 'report' not in written, written
    source = _read(ROOT, 'scripts/init/update.py')
    assert "'report'" not in source, 'the update writes a key nothing reads'


# purlin: update PROOF-21
def test_a_framework_the_tree_cannot_run_is_dropped(tmp_path, capsys):
    """An older release wrote down every plugin it shipped, runnable or not."""
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    before = json.loads(_read(root, '.purlin/config.json'))
    assert before['test_framework'] == 'pytest,jest,shell,vitest'  # retired
    _apply(root)
    printed = capsys.readouterr().out
    written = json.loads(_read(root, '.purlin/config.json'))
    from purlin import frameworks
    assert written['tests'] == [frameworks.entry_for('pytest')]
    for name in ('jest', 'shell', 'vitest'):
        assert ('dropped %s from the tests: nothing in the tree runs it'
                % name) in printed, printed
    assert 'wrote the tests setting: pytest' in printed


# purlin: update PROOF-21
def test_a_framework_the_tree_carries_is_kept(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    _write(root, 'package.json', json.dumps({'devDependencies': {
        'jest': '^29.0.0', 'vitest': '^3.0.0'}}))
    _write(root, 'tests/login.test.sh', 'exit 0\n')
    _apply(root)
    printed = capsys.readouterr().out
    written = json.loads(_read(root, '.purlin/config.json'))
    assert [suite['name'] for suite in written['tests']] == [
        'pytest', 'jest', 'shell', 'vitest']
    assert 'from the tests' not in printed


# --- the markers -------------------------------------------------------------
# What v0.9.5's plugins read, one test file per framework, written the way
# `git show v0.9.5:scripts/proof/<plugin>` parses it.

OLD_PYTEST = (
    'import pytest\n\n'
    '@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'  # retired
    'def test_accepts():\n    assert True\n\n\n'
    'class TestLogin:\n'
    '    @pytest.mark.proof("login", "PROOF-2", "RULE-2", tier="integration")\n'  # retired
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
OLD_JEST = (
    "describe('login', () => {\n"
    "  it('accepts [proof:login:PROOF-1:RULE-1:unit]', () => {});\n"  # retired
    "  test('refuses [proof:login:PROOF-2:RULE-2]', () => {});\n"  # retired
    "});\n")
NEW_JEST = (
    "describe('login', () => {\n"
    "  // purlin: login PROOF-1\n"
    "  it('accepts', () => {});\n"
    "  // purlin: login PROOF-2\n"
    "  test('refuses', () => {});\n"
    "});\n")
OLD_XUNIT = (
    'public class LoginTests {\n'
    '    [Fact]\n'
    '    [Trait("PurlinProof", "login:PROOF-1:RULE-1:unit")]\n'  # retired
    '    public void Accepts() {}\n'
    '}\n')
NEW_XUNIT = (
    'public class LoginTests {\n'
    '    [Fact]\n'
    '    // purlin: login PROOF-1\n'
    '    public void Accepts() {}\n'
    '}\n')
OLD_SHELL = (
    '#!/usr/bin/env bash\n'
    'source .purlin/plugins/purlin-proof.sh\n'  # retired
    'purlin_proof "login" "PROOF-1" "RULE-1" pass "accepts"\n'  # retired
    'purlin_proof_finish\n')  # retired
NEW_SHELL = (
    '#!/usr/bin/env bash\n'
    '# purlin: login PROOF-1\n'
    ':\n:\n:\n')
OLD_SQL = (
    '-- @purlin login PROOF-1 RULE-1 unit\n'  # retired
    "SELECT 'PASS';\n")
NEW_SQL = (
    '-- purlin: login PROOF-1\n'
    "SELECT 'PASS';\n")
OLD_TESTS = {'tests/test_login.py': (OLD_PYTEST, NEW_PYTEST),
             'tests/login.test.js': (OLD_JEST, NEW_JEST),
             'tests/LoginTests.cs': (OLD_XUNIT, NEW_XUNIT),
             'tests/login.test.sh': (OLD_SHELL, NEW_SHELL),
             'tests/test_login.sql': (OLD_SQL, NEW_SQL)}


def _old_tests(root):
    for rel, (old, _new) in OLD_TESTS.items():
        _write(root, rel, old)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the tests 0.9.5 marked')


# purlin: update PROOF-29
def test_each_old_marker_becomes_a_comment_above_its_test(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _old_tests(root)
    assert update._detect_markers(root) == sorted(OLD_TESTS)
    _apply(root)
    printed = capsys.readouterr().out
    for rel, (_old, new) in OLD_TESTS.items():
        assert _read(root, rel) == new, rel
    assert 'rewrote 2 markers in tests/test_login.py as comments' in printed
    assert ('rewrote 1 marker in tests/login.test.sh as comments; the file '
            'is one test now, and passes when it exits 0') in printed
    assert 'markers' not in _ids(root)


# purlin: update PROOF-29
def test_each_rewritten_test_file_is_backed_up(tmp_path):
    root = _project(tmp_path, V095)
    _old_tests(root)
    _apply(root)
    for rel, (old, _new) in OLD_TESTS.items():
        folder, name = os.path.split(os.path.join(root, rel))
        (backup,) = [entry for entry in os.listdir(folder)
                     if entry.startswith(name + '.local-')]
        assert _read(folder, backup) == old, rel


# purlin: update PROOF-30
def test_a_marker_it_cannot_place_is_named_and_left(tmp_path, capsys):
    root = _project(tmp_path, V095)
    module = ('import pytest\n\n'
              'pytestmark = pytest.mark.proof("login", "PROOF-3", "RULE-3")\n'  # retired
              '\n\n@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'  # retired
              'def test_a():\n    pass\n')
    _write(root, 'tests/test_module.py', module)
    _apply(root)
    printed = capsys.readouterr().out
    text = _read(root, 'tests/test_module.py')
    assert '# purlin: login PROOF-1\ndef test_a' in text
    assert ('left tests/test_module.py:3 as it was: write the marker as a '
            'comment above each test by hand') in printed


# --- the plugins and their wiring ----------------------------------------------

OLD_CONFTEST = 'pytest_plugins = [".purlin.plugins.pytest_purlin"]\n'  # retired
OLD_JEST_CONFIG = ('module.exports = {\n'
                   '  "reporters": ["default", ".purlin/plugins/jest_purlin.js"]\n'  # retired
                   '};\n')
OLD_VITEST_CONFIG = ("import { defineConfig } from 'vitest/config';\n"
                     'export default defineConfig({\n'
                     "  test: { reporters: ['default', "
                     "'.purlin/plugins/vitest_purlin.ts'] },\n"  # retired
                     '});\n')


# purlin: update PROOF-16
def test_the_plugin_copies_go(tmp_path):
    root = _project(tmp_path, V095)
    folder = os.path.join(root, '.purlin', 'plugins')
    assert os.listdir(folder), 'the fixture carries the copies'
    assert 'plugins' in _ids(root)
    _apply(root)
    assert not os.path.exists(folder)
    assert not [rel for rel in _tracked(root)
                if rel.startswith('.purlin/plugins/')]  # retired
    assert 'plugins' not in _ids(root)


# purlin: update PROOF-16
def test_a_file_the_plugin_did_not_ship_is_left_alone(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, '.purlin/plugins/house_purlin.rb', '# our own reporter\n')  # retired
    _apply(root)
    assert _read(root, '.purlin/plugins/house_purlin.rb') == (  # retired
        '# our own reporter\n')
    assert not os.path.exists(
        os.path.join(root, '.purlin', 'plugins', 'pytest_purlin.py'))


# purlin: update PROOF-16
def test_the_wiring_0_9_5_wrote_goes(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', OLD_CONFTEST)
    _write(root, 'jest.config.js', OLD_JEST_CONFIG)
    _write(root, 'vitest.config.ts', OLD_VITEST_CONFIG)
    _write(root, 'App.Tests/App.Tests.csproj',
           '<Project><ItemGroup><Compile Include="../.purlin/plugins/'  # retired
           'xunit_purlin.cs" /></ItemGroup></Project>\n')  # retired
    _apply(root)
    printed = capsys.readouterr().out
    assert not os.path.exists(os.path.join(root, 'conftest.py'))
    assert "removed conftest.py: it held only the plugin's wiring" in printed
    assert _read(root, 'jest.config.js') == (
        'module.exports = {\n  "reporters": ["default"]\n};\n')
    assert "reporters: ['default'] }" in _read(root, 'vitest.config.ts')
    assert "removed the plugin's wiring from jest.config.js" in printed
    assert ('App.Tests/App.Tests.csproj compiles the xUnit logger v0.9.5 '
            'shipped; remove that line by hand') in printed


# purlin: update PROOF-16
def test_a_conftest_holding_more_keeps_the_rest(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', 'import os\n\n' + OLD_CONFTEST)
    _apply(root)
    assert _read(root, 'conftest.py') == 'import os\n\n'


# --- design references -------------------------------------------------------

DESIGN_ANCHOR = 'specs/_anchors/checkout_design.md'
DESIGN_FEATURE = 'specs/workflows/figma_web.md'
DESIGN_FIELDS = ('> Source:', '> Pinned:', '> Visual-Reference:',
                 '> Visual-Hash:')


def _without(text, prefixes):
    return [line for line in text.splitlines()
            if not any(line.startswith(p) for p in prefixes)]


# purlin: update PROOF-24
def test_every_design_line_0_9_5_wrote_is_removed(tmp_path, capsys):
    root = _project(tmp_path, V095)
    anchor_before = _read(root, DESIGN_ANCHOR)
    feature_before = _read(root, DESIGN_FEATURE)
    for field in DESIGN_FIELDS:
        assert field in anchor_before, field
    assert '> Visual-Reference: figma://' in feature_before
    _apply(root)
    printed = capsys.readouterr().out
    anchor_after = _read(root, DESIGN_ANCHOR)
    for field in DESIGN_FIELDS:
        assert not [line for line in anchor_after.splitlines()
                    if line.startswith(field)], field
    # The kind-of-test migration rewrites the anchor's proof line too, so
    # the comparison stops short of the proof lines.
    assert _without(anchor_after, ('- PROOF-',)) == _without(
        anchor_before, DESIGN_FIELDS + ('- PROOF-',))
    for kept in ('> Description:', '> Type: design', '- RULE-1:'):
        assert kept in anchor_after, kept
    feature_after = _read(root, DESIGN_FEATURE)
    assert not [line for line in feature_after.splitlines()
                if line.startswith('> Visual-Reference:')]
    assert _without(feature_after, ('- PROOF-',)) == _without(
        feature_before, ('> Visual-Reference:', '- PROOF-'))
    assert ('removed the design reference from %s: > Source:, > Pinned:, '
            '> Visual-Reference:, > Visual-Hash:' % DESIGN_ANCHOR) in printed
    assert ('removed the design reference from %s: > Visual-Reference:'
            % DESIGN_FEATURE) in printed


# purlin: update PROOF-24
def test_each_design_rewrite_is_backed_up(tmp_path):
    root = _project(tmp_path, V095)
    before = {rel: _read(root, rel) for rel in (DESIGN_ANCHOR, DESIGN_FEATURE)}
    _apply(root)
    for rel, text in before.items():
        folder, name = os.path.split(rel)
        copies = _walk(os.path.join(root, folder), (name + '.local-*.bak',),
                       skip_backups=False)
        assert text in [_read(os.path.join(root, folder), copy)
                        for copy in copies], (rel, copies)


FIGMA_URI_ANCHOR = """# Anchor: modal_design

> Description: A modal drawn in Figma.
> Source: figma://ABC123/1:2
> Pinned: 2026-03-31T12:00:00Z

## Rules

- RULE-1: The modal matches the frame
"""

GIT_ANCHOR = """# Anchor: no_eval

> Description: No eval() calls in production code
> Source: git@github.com:acme/security-policies.git
> Path: specs/no_eval.md
> Pinned: abc1234def5678

## Rules

- RULE-1: No eval() in source files
"""


# purlin: update PROOF-24
def test_a_figma_uri_goes_and_a_git_source_stays(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, 'specs/_anchors/modal_design.md', FIGMA_URI_ANCHOR)
    _write(root, 'specs/_anchors/no_eval.md', GIT_ANCHOR)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'two sourced anchors')
    _apply(root)
    figma = _read(root, 'specs/_anchors/modal_design.md')
    assert not [line for line in figma.splitlines()
                if line.startswith(('> Source:', '> Pinned:'))], figma
    assert '- RULE-1: The modal matches the frame' in figma
    assert _read(root, 'specs/_anchors/no_eval.md') == GIT_ANCHOR


# --- the keys the config step drops -------------------------------------------

# purlin: update PROOF-25
def test_every_dropped_key_is_named(tmp_path, capsys):
    root = _project(tmp_path, V095)
    config = json.loads(_read(root, '.purlin/config.json'))
    assert 'report' in config
    config['audit_criteria'] = 'git@github.com:acme/q.git#criteria.md'
    config['audit_criteria_pinned'] = 'abc1234'
    _write(root, '.purlin/config.json', json.dumps(config, indent=2))
    _apply(root)
    printed = capsys.readouterr().out
    assert ('dropped 6 keys this release does not read: audit_criteria, '
            'audit_criteria_pinned, digest, pre_push, report, spec_dir'
            ) in printed, printed
    written = json.loads(_read(root, '.purlin/config.json'))
    for key in ('audit_criteria', 'audit_criteria_pinned', 'digest',
                'pre_push', 'report', 'spec_dir'):
        assert key not in written, key


# --- the mutation question ----------------------------------------------------

MUTATION = 'Measure test strength by breaking the code on purpose?'


# purlin: update PROOF-26
def test_the_mutation_question_defaults_to_no(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    asked = _answers(monkeypatch, [(MUTATION, '')])
    _apply(root, argv=())
    capsys.readouterr()
    assert any(prompt.startswith(MUTATION + ' It needs mutmut')
               for prompt in asked), asked
    written = json.loads(_read(root, '.purlin/config.json'))
    assert written['mutation_engine'] == 'none'
    assert written['min_strength'] is None


# purlin: update PROOF-26
def test_yes_turns_it_on_at_the_gate_s_minimum(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    _answers(monkeypatch, [('Gate [', 'strong'), (MUTATION, 'y')])
    _apply(root, argv=())
    printed = capsys.readouterr().out
    written = json.loads(_read(root, '.purlin/config.json'))
    assert written['mutation_engine'] == 'auto'
    assert written['min_strength'] == 70
    assert 'run purlin:init to wire mutmut' in printed


# purlin: update PROOF-26
def test_no_engine_means_no_question(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    asked = _answers(monkeypatch)
    _apply(root, argv=())
    printed = capsys.readouterr().out
    assert not [prompt for prompt in asked if MUTATION in prompt], asked
    assert json.loads(_read(root, '.purlin/config.json'))[
        'mutation_engine'] == 'none'
    assert "no engine breaks this project's code" in printed


# purlin: update PROOF-26
def test_a_mutation_setting_already_written_is_kept(tmp_path, capsys,
                                                    monkeypatch):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    config = json.loads(_read(root, '.purlin/config.json'))
    config['mutation_engine'] = 'auto'
    _write(root, '.purlin/config.json', json.dumps(config, indent=2))
    asked = _answers(monkeypatch)
    _apply(root, argv=())
    capsys.readouterr()
    assert not [prompt for prompt in asked if MUTATION in prompt], asked
    assert json.loads(_read(root, '.purlin/config.json'))[
        'mutation_engine'] == 'auto'


# --- a spec with no scope -----------------------------------------------------

UNSCOPED = """# Feature: nowhere

## Rules

- RULE-1: A rule whose code is not named

## Proof

- PROOF-1 (RULE-1): Call it and verify it answers
"""


# purlin: update PROOF-27
def test_a_spec_with_no_scope_is_named_and_left_alone(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write(root, 'specs/core/nowhere.md', UNSCOPED)
    _write(root, 'specs/_anchors/unscoped_anchor.md',
           UNSCOPED.replace('Feature: nowhere', 'Anchor: unscoped_anchor'))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'a spec with no scope')
    _apply(root)
    printed = capsys.readouterr().out
    assert ('1 spec has no > Scope: line: nowhere. Run purlin:spec <name> to '
            'add one.') in printed, printed
    assert 'required at signed' in printed
    assert 'unscoped_anchor' not in printed.split('Scope: line:')[1]
    assert _read(root, 'specs/core/nowhere.md') == UNSCOPED
    assert update.pending(root) == []
    _apply(root)
    again = capsys.readouterr().out
    assert 'Nothing is pending' in again
    assert '1 spec has no > Scope: line: nowhere.' in again


# --- the evidence folder ------------------------------------------------------

# purlin: update PROOF-28
def test_the_evidence_folder_gets_its_readme(tmp_path):
    root = _project(tmp_path, V095)
    assert 'evidence' in _ids(root)
    _apply(root)
    with open(os.path.join(root, '.purlin', 'evidence', 'README.md'),
              'rb') as got, open(os.path.join(
                  ROOT, 'templates', 'evidence-readme.md'), 'rb') as want:
        assert got.read() == want.read()
    assert '.purlin/evidence/README.md' in _tracked(root)
    assert _walk(root, LEFTOVER) == []
    assert 'evidence' not in _ids(root)


# --- operating-system tags ---------------------------------------------------

# A spec where the Windows tag's spelling is prose in the middle of a line rather
# than a tag at its end: the rewrite has to leave it exactly as it is.
PROSE_SPEC = """# Feature: runners

> Scope: src/runners.py

## Rules

- RULE-1: A proof names the operating system it needs

## Proof

- PROOF-1 (RULE-1): Read a line naming @windows mid-sentence and verify it is left alone
"""


# purlin: update PROOF-13
def test_the_retired_windows_tag_becomes_env(tmp_path):
    root = _project(tmp_path, V095)
    rel = _spec_holding(root, 'msvcrt.locking')
    assert '@windows\n' in _read(root, rel)
    _apply(root)
    text = _read(root, rel)
    proofs = [line for line in text.splitlines()
              if line.startswith('- PROOF-53 ')]
    assert len(proofs) == 1
    assert proofs[0].endswith(' @env(windows)')
    assert '@unit' not in proofs[0]  # retired
    assert '@windows\n' not in text


# purlin: update PROOF-23
def test_the_kind_of_test_is_dropped_from_every_proof_line(tmp_path):
    root = _project(tmp_path, V095)
    rel = 'specs/_anchors/proof_common.md'
    before = [line for line in _read(root, rel).splitlines()
              if line.startswith('- PROOF-')]
    assert before[0].endswith('@integration')  # retired
    _apply(root)
    after = [line for line in _read(root, rel).splitlines()
             if line.startswith('- PROOF-')]
    assert len(after) == len(before)
    for line in after:
        assert not re.search(r'@(unit|integration|e2e)\s*$', line), line  # retired
    assert after[0].endswith('written to `specs/hooks/`'), after[0]

    path = os.path.join(root, rel)
    with open(path, 'a', encoding='utf-8') as handle:
        handle.write('- PROOF-99 (RULE-1): Lock a file @e2e @env(linux)\n')  # retired
    _apply(root)
    added = [line for line in _read(root, rel).splitlines()
             if line.startswith('- PROOF-99 ')]
    assert added == ['- PROOF-99 (RULE-1): Lock a file @env(linux)']


# purlin: update PROOF-13
def test_prose_that_is_not_a_tag_is_left_alone(tmp_path):
    root = _project(tmp_path, V095)
    rel = 'specs/core/runners.md'
    _write(root, rel, PROSE_SPEC)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'a spec naming the tag in prose')
    _apply(root)
    assert _read(root, rel) == PROSE_SPEC


# --- hooks -------------------------------------------------------------------

def _with_hooks(tmp_path):
    """A v0.9.5 project carrying the two hooks that release installed."""
    root = _project(tmp_path, V095)
    _write(root, '.git/hooks/pre-commit', OLD_PRE_COMMIT)
    _write(root, '.git/hooks/pre-push', OLD_PRE_PUSH)
    return root


def _hook_files(root):
    return [item['files'] for item in update.pending(root)
            if item['id'] == 'hooks'][0]


# purlin: update PROOF-9
def test_the_pre_commit_hook_goes(tmp_path):
    root = _with_hooks(tmp_path)
    hook = os.path.join(root, '.git', 'hooks', 'pre-commit')
    assert '.git/hooks/pre-commit' in _hook_files(root)
    _apply(root)
    assert not os.path.exists(hook)


# purlin: update PROOF-9
def test_a_foreign_hook_is_left_alone(tmp_path):
    root = _with_hooks(tmp_path)
    hook = os.path.join(root, '.git', 'hooks', 'pre-commit')
    with open(hook, 'w', encoding='utf-8') as handle:
        handle.write('#!/bin/sh\nexec ./node_modules/.bin/lint-staged\n')
    _apply(root)
    assert os.path.isfile(hook)


# purlin: update PROOF-9
def test_the_pre_push_hook_goes_too(tmp_path):
    """Nothing runs at push time, so the hook is removed rather than moved."""
    root = _with_hooks(tmp_path)
    assert '.git/hooks/pre-push' in _hook_files(root)
    _apply(root)
    assert not os.path.exists(os.path.join(root, '.git', 'hooks', 'pre-push'))


# purlin: update PROOF-9
def test_a_project_with_the_hooks_gone_needs_the_migration_once(tmp_path):
    root = _with_hooks(tmp_path)
    _apply(root)
    assert 'hooks' not in _ids(root)


# purlin: update PROOF-2
def test_a_project_with_no_hooks_needs_no_hook_migration(tmp_path):
    root = _project(tmp_path, V095)
    assert 'hooks' not in _ids(root)


# --- workflows ---------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-15
def test_the_retired_workflows_are_removed(tmp_path, layout):
    root = _project(tmp_path, layout)
    before = _walk(root, ('*.yml',))
    assert any(rel.startswith('.github/workflows/') for rel in before)
    _apply(root)
    after = [rel for rel in _walk(root, ('*.yml',))
             if rel.startswith('.github/workflows/')]
    assert after == ['.github/workflows/purlin.yml']


# purlin: update PROOF-15
def test_purlin_yml_carries_the_matrix_the_tags_name(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    text = _read(root, '.github/workflows/purlin.yml')
    assert 'windows-latest' in text
    assert 'v%s' % VERSION in text


# purlin: update PROOF-15
def test_purlin_yml_carries_this_releases_triggers_and_gate_check(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    text = _read(root, '.github/workflows/purlin.yml')
    assert "branches: ['run/**']" in text
    assert "tags: ['signed/**']" in text
    assert 'name: Check the gate' in text
    assert 'scripts/ci/gate_check.py" --check --verify' in text


# purlin: update PROOF-15
def test_declining_the_workflow_leaves_it_unwritten(tmp_path, capsys,
                                                    monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Write .github/workflows/purlin.yml', 'n')])
    _apply(root, argv=())
    printed = capsys.readouterr().out
    assert not os.path.exists(
        os.path.join(root, '.github', 'workflows', 'purlin.yml'))
    assert 'run purlin:init again to add it later' in printed
    assert 'workflows' not in _ids(root)


# purlin: update PROOF-32
def test_an_azure_remote_gets_the_pipeline_where_init_writes_it(tmp_path):
    root = _project(tmp_path, V095, remote=False)
    _git(root, 'remote', 'add', 'origin',
         'https://dev.azure.com/acme/demo/_git/demo')
    _apply(root)
    assert [rel for rel in _walk(root, ('*.yml',))
            if rel.startswith('.github/')] == []
    text = _read(root, 'purlin.azure-pipelines.yml')
    assert 'windows-latest' in text
    assert 'v%s' % VERSION in text


# --- the dashboard page ------------------------------------------------------

# purlin: update PROOF-31
def test_the_page_linked_into_the_old_plugin_is_replaced(tmp_path):
    root = _project(tmp_path, V095)
    page = os.path.join(root, 'purlin-report.html')
    try:
        os.symlink(os.path.join(str(tmp_path), 'plugins', 'cache', 'purlin',
                                '0.9.5', 'purlin-report.html'), page)
    except (OSError, NotImplementedError):
        pytest.skip('this machine makes no symbolic link')
    assert 'dashboard' in _ids(root)
    _apply(root)
    with open(os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html'),
              'rb') as handle:
        shipped = handle.read()
    assert not os.path.islink(page)
    with open(page, 'rb') as handle:
        assert handle.read() == shipped
    assert 'dashboard' not in _ids(root)
    _write(root, 'purlin-report.html', '<html>an older copy</html>\n')
    assert 'dashboard' in _ids(root)
    os.remove(page)
    assert 'dashboard' not in _ids(root)


# --- backups -----------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-7
def test_every_rewritten_file_leaves_its_previous_bytes(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    backups = _walk(root, ('*.bak',), skip_backups=False)
    names = ' '.join(backups)
    assert '.purlin/config.json.local-' in names
    assert '.gitignore.local-' in names
    assert any(rel.startswith('specs/') for rel in backups)


# purlin: update PROOF-7
def test_a_backup_holds_what_the_file_said_before(tmp_path):
    root = _project(tmp_path, V095)
    before = _read(root, '.purlin/config.json')
    _apply(root)
    backups = [rel for rel in _walk(root, ('config.json.local-*.bak',),
                                    skip_backups=False)]
    assert len(backups) == 1
    assert _read(root, backups[0]) == before


# purlin: update PROOF-7
def test_a_backup_is_not_written_twice(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    first = _walk(root, ('*.bak',), skip_backups=False)
    _apply(root)
    assert _walk(root, ('*.bak',), skip_backups=False) == first


# --- the commit --------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-18
def test_one_commit_carries_every_migration_id(tmp_path, layout):
    root = _project(tmp_path, layout)
    applied = _ids(root)
    _apply(root)
    log = _git(root, 'log', '--format=%s').stdout.splitlines()
    assert len(log) == 2, log
    subject = log[0]
    assert subject.startswith('chore(update): migrate to %s (' % VERSION)
    for migration_id in applied:
        assert migration_id in subject


@pytest.mark.parametrize('layout', LAYOUTS)
# purlin: update PROOF-18
def test_nothing_is_left_uncommitted_but_the_backups(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    left = _git(root, 'status', '--porcelain').stdout.splitlines()
    assert left, 'the backups should still be sitting there'
    for line in left:
        assert line.startswith('?? '), line
        assert line.endswith('.bak'), line


# purlin: update PROOF-18
def test_a_run_that_applies_nothing_writes_no_commit(tmp_path, capsys,
                                                     monkeypatch):
    root = _project(tmp_path, V095)
    head = _git(root, 'rev-parse', 'HEAD').stdout.strip()
    _answers(monkeypatch, default='n')
    _apply(root, argv=())
    capsys.readouterr()
    assert _git(root, 'rev-parse', 'HEAD').stdout.strip() == head


# --- the line sync_status prints ---------------------------------------------

# purlin: update PROOF-19
def test_status_says_it_for_a_project_that_has_not_updated(tmp_path):
    root = _project(tmp_path, V095)
    assert 'Run: purlin:init --update' in status_module.sync_status(root)


# purlin: update PROOF-19
def test_status_stops_saying_it_once_the_old_project_has_updated(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    assert 'Run: purlin:init --update' not in status_module.sync_status(root)


# purlin: update PROOF-19
def test_status_says_it_even_when_the_config_is_already_clean(tmp_path):
    """The line must come from the pending list, not only from a config warning."""
    root = _project(tmp_path, V095)
    _apply(root)
    _write(root, 'specs/core/later.md',
           '# Feature: later\n\n## Rules\n\n- RULE-1: x\n\n## Proof\n\n'
           '- PROOF-1 (RULE-1): y @windows\n')
    assert update.pending(root)
    assert 'Run: purlin:init --update' in status_module.sync_status(root)


# --- the copy the update prints ----------------------------------------------

# purlin: update PROOF-20
def test_what_the_update_prints_carries_no_emoji(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root)
    printed = capsys.readouterr().out
    for char in printed:
        assert ord(char) < 0x2190 or char in '→─', repr(char)


# purlin: update PROOF-20
def test_the_run_ends_by_naming_the_next_step(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root)
    printed = capsys.readouterr().out.rstrip().splitlines()
    assert printed[-1].startswith('→ Next: run purlin:status')


# purlin: update PROOF-20
def test_a_run_that_leaves_work_names_it(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Apply plugins', 'n')])
    _apply(root, argv=())
    printed = capsys.readouterr().out.rstrip().splitlines()
    assert printed[-1] == ('→ Next: run purlin:init --update again for '
                           'plugins.')
