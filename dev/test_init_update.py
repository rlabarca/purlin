"""Proofs for `scripts/init/update.py`, the edits `purlin:init --update` makes.

Every case here drives the real script against a real git repository made from
the v0.9.5 upgrade fixture, never against a hand-built expectation of what the
script would do, so the script and these proofs cannot drift apart. The fixture
itself is frozen: each test copies it into a temporary directory and runs
`git init` there, then writes by hand whatever that layout does not carry.

A line that writes a spelling `dev/test_vocabulary.py` lists, because the
upgrade has to be fed it, ends with a `# retired` comment, and that check steps
over exactly those lines.

What each group proves:

*pending*     what the update finds in the old layout, and the root it refuses
*applying*    `--yes` applies every migration, a second run finds nothing, and
              a declined migration stays pending
*specs*       no proof file and no run file survives beside a spec, and the
              old cache folder goes
*config*      the file that is left is the gate, what the gate derives, and
              the host
*tests*       the `tests` setting written from the frameworks 0.9.5 named
*tags*        the Windows tag becomes `@env(windows)`, and the kind of test
              goes from every proof line
*hooks*       the pre-commit and pre-push hooks v0.9.5 installed go
*workflows*   the retired workflows go and one `purlin.yml` replaces them
*markers*     each 0.9.5 marker becomes a comment above the same test
*plugins*     the plugin copies and the wiring that loaded them go
*design*      the Figma source and the picture fingerprint go from each spec
*page*        the dashboard page at the root becomes the one the plugin ships
*mutation*    the mutation question init asks, asked of a config without one
*scope*       a spec with no `> Scope:` line is named, and changed by nothing
*evidence*    `.purlin/evidence/` and its README
*backups*     every rewritten file leaves its previous bytes beside it
*commit*      one commit, naming the migrations it carries
*status*      `sync_status` says to run the update while anything is pending
*set up*      a project 0.9.5 set up and nobody upgraded is told apart
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

import scaffold  # noqa: E402
import update  # noqa: E402
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

# The keys of the config this release writes, sorted.
SEVEN_KEYS = ['audit_parallel', 'ci', 'gate', 'min_strength',
              'mutation_engine', 'tests', 'version']


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


def _config(root):
    return json.loads(_read(root, '.purlin/config.json'))


def _set_config(root, **values):
    config = _config(root)
    for key, value in values.items():
        if value is None:
            config.pop(key, None)
        else:
            config[key] = value
    _write(root, '.purlin/config.json', json.dumps(config, indent=2))



# --- what a project still needs ---------------------------------------------

# The migrations the v0.9.5 fixture needs, in the order they are applied.
EIGHT = ['design-refs', 'os-tags', 'kind-tags', 'untracked-files', 'config',
         'evidence', 'workflows', 'plugins']


# purlin: update PROOF-1
def test_a_root_without_purlin_has_nothing_pending(tmp_path):
    empty = str(tmp_path / 'bare')
    os.makedirs(empty)
    assert update.pending(empty) == []


# purlin: update PROOF-67
def test_every_pending_entry_says_what_it_does_and_to_which_files(tmp_path):
    root = _project(tmp_path, V095)
    found = update.pending(root)
    assert found
    for item in found:
        assert sorted(item) == ['description', 'files', 'id'], item
        assert item['description']
        assert '\n' not in item['description'], item
        assert item['files']
    ids = [item['id'] for item in found]
    assert len(ids) == len(set(ids)), ids


# purlin: update PROOF-2
def test_the_v095_layout_needs_the_migrations_that_layout_left(tmp_path):
    root = _project(tmp_path, V095)
    assert _ids(root) == EIGHT


# purlin: update PROOF-68
def test_a_retired_hook_adds_the_hook_migration(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, '.git/hooks/pre-commit', OLD_PRE_COMMIT)
    assert _ids(root) == ['design-refs', 'os-tags', 'kind-tags',
                          'untracked-files', 'hooks', 'config', 'evidence',
                          'workflows', 'plugins']


# purlin: update PROOF-4
def test_a_root_without_purlin_exits_2(tmp_path):
    empty = str(tmp_path / 'empty')
    os.makedirs(empty)
    done = subprocess.run([sys.executable, UPDATE, '--project-root', empty],
                          capture_output=True, text=True)
    assert done.returncode == 2
    assert 'nothing to update' in done.stderr
    assert 'Run purlin:init first.' in done.stderr


# --- applying ----------------------------------------------------------------

# purlin: update PROOF-5
def test_yes_asks_nothing_and_applies_every_migration(tmp_path, capsys,
                                                     monkeypatch):
    root = _project(tmp_path, V095)
    asked = _answers(monkeypatch)
    assert _apply(root) == 0
    capsys.readouterr()
    assert asked == []
    assert update.pending(root) == []


# purlin: update PROOF-33
def test_running_yes_twice_changes_nothing_the_second_time(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root)
    head = _git(root, 'rev-parse', 'HEAD').stdout.strip()
    tree = _git(root, 'status', '--porcelain').stdout
    capsys.readouterr()
    assert _apply(root) == 0
    assert 'Nothing is pending' in capsys.readouterr().out
    assert _git(root, 'rev-parse', 'HEAD').stdout.strip() == head
    assert _git(root, 'status', '--porcelain').stdout == tree


# purlin: update PROOF-69
def test_yes_takes_the_default_of_the_gate_and_mutation_questions(
        tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    _set_config(root, pre_push='strict')
    _write(root, 'conftest.py', '')
    asked = _answers(monkeypatch)
    _apply(root)
    capsys.readouterr()
    assert asked == []
    written = _config(root)
    assert written['gate'] == 'strong'
    assert written['mutation_engine'] == 'none'
    assert written['min_strength'] is None


# purlin: update PROOF-6
def test_a_declined_migration_is_left_pending(tmp_path, capsys, monkeypatch):
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


# --- the files beside the specs ----------------------------------------------

# purlin: update PROOF-8
def test_no_proof_or_run_file_is_left_on_disk_or_tracked(tmp_path):
    root = _project(tmp_path, V095)
    assert _walk(root, LEFTOVER), 'the fixture should start with some'
    _apply(root)
    assert _walk(root, LEFTOVER) == []
    left = [rel for rel in _tracked(root)
            if any(fnmatch.fnmatch(os.path.basename(rel), p)
                   for p in LEFTOVER)]
    assert left == []


# purlin: update PROOF-34
def test_the_dashboard_data_is_untracked_and_ignored(tmp_path):
    root = _project(tmp_path, V095)
    assert '.purlin/report-data.js' in _tracked(root)
    _apply(root)
    assert '.purlin/report-data.js' not in _tracked(root)
    assert os.path.isfile(os.path.join(root, '.purlin', 'report-data.js'))
    ignored = _read(root, '.gitignore').splitlines()
    assert '.purlin/report-data.js' in ignored


# purlin: update PROOF-35
def test_an_ignored_cache_is_deleted(tmp_path):
    root = _project(tmp_path, V095)
    cache = os.path.join(root, '.purlin', 'cache')
    assert os.listdir(cache), 'the fixture carries a cache'
    assert not any(rel.startswith('.purlin/cache/') for rel in _tracked(root))
    _apply(root)
    assert not os.path.exists(cache)


# purlin: update PROOF-36
def test_a_committed_cache_is_deleted_from_git_and_from_disk(tmp_path):
    """The v0.9.5 fixture ignores its cache, so commit one the way a project would."""
    root = _project(tmp_path, V095)
    _git(root, 'add', '-f', '.purlin/cache')
    _git(root, 'commit', '-qm', 'a committed cache')
    assert any(rel.startswith('.purlin/cache/') for rel in _tracked(root))
    assert 'untracked-files' in _ids(root)
    _apply(root)
    assert not any(rel.startswith('.purlin/cache/') for rel in _tracked(root))
    assert not os.path.exists(os.path.join(root, '.purlin', 'cache'))


# purlin: update PROOF-75
def test_a_cache_the_gitignore_does_not_name_is_deleted_too(tmp_path):
    """With nothing ignoring it, the update's own commit must not add it back."""
    root = _project(tmp_path, V095)
    kept = [line for line in _read(root, '.gitignore').splitlines()
            if line != '.purlin/cache/']
    _write(root, '.gitignore', '\n'.join(kept) + '\n')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the cache, committed')
    assert any(rel.startswith('.purlin/cache/') for rel in _tracked(root))
    _apply(root)
    assert not any(rel.startswith('.purlin/cache/') for rel in _tracked(root))
    assert not os.path.exists(os.path.join(root, '.purlin', 'cache'))
    assert 'untracked-files' not in _ids(root)


# --- the config --------------------------------------------------------------

# purlin: update PROOF-10
def test_the_config_is_the_gate_shape(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    config = _config(root)
    assert sorted(config) == SEVEN_KEYS
    assert config['version'] == VERSION
    assert config['gate'] == 'passed'
    assert config['mutation_engine'] == 'none'
    assert config['min_strength'] is None
    assert config['audit_parallel'] == 4
    assert config['ci'] == 'github'


def _config_at(tmp_path, monkeypatch, gate):
    """The config the update leaves with the gate question answered `gate`."""
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Gate [', gate)])
    _apply(root, argv=())
    return _config(root)


# purlin: update PROOF-37
def test_the_config_is_the_gate_shape_at_strong(tmp_path, capsys, monkeypatch):
    config = _config_at(tmp_path, monkeypatch, 'strong')
    capsys.readouterr()
    assert config['gate'] == 'strong'
    assert config['audit_parallel'] == 4
    assert sorted(config) == SEVEN_KEYS


# purlin: update PROOF-38
def test_the_config_is_the_gate_shape_at_signed(tmp_path, capsys, monkeypatch):
    config = _config_at(tmp_path, monkeypatch, 'signed')
    capsys.readouterr()
    assert config['gate'] == 'signed'
    assert config['audit_parallel'] == 4
    assert sorted(config) == SEVEN_KEYS


# purlin: update PROOF-39
def test_retired_keys_are_gone(tmp_path):
    root = _project(tmp_path, V095)
    before = _config(root)
    assert 'spec_dir' in before and 'pre_push' in before, before
    _apply(root)
    after = _config(root)
    assert 'spec_dir' not in after and 'pre_push' not in after, after


# purlin: update PROOF-40
def test_no_remote_writes_ci_none(tmp_path):
    root = _project(tmp_path, V095, remote=False)
    _apply(root)
    assert _config(root)['ci'] == 'none'


# purlin: update PROOF-41
def test_another_host_writes_ci_none(tmp_path):
    root = _project(tmp_path, V095, remote=False)
    _git(root, 'remote', 'add', 'origin', 'https://gitlab.com/acme/demo.git')
    _apply(root)
    assert _config(root)['ci'] == 'none'


# purlin: update PROOF-42
def test_an_azure_remote_writes_ci_azure(tmp_path):
    root = _project(tmp_path, V095, remote=False)
    _git(root, 'remote', 'add', 'origin',
         'https://dev.azure.com/acme/demo/_git/demo')
    _apply(root)
    assert _config(root)['ci'] == 'azure'


# purlin: update PROOF-43
def test_a_ci_the_project_named_is_kept(tmp_path):
    root = _project(tmp_path, V095)
    _set_config(root, ci='none')
    _apply(root)
    assert _config(root)['ci'] == 'none'


# purlin: update PROOF-78
def test_an_audit_parallel_the_project_named_is_kept(tmp_path):
    root = _project(tmp_path, V095)
    _set_config(root, audit_parallel=8)
    _apply(root)
    assert _config(root)['audit_parallel'] == 8


# purlin: update PROOF-11
def test_a_dashboard_switch_set_on_is_not_written_back(tmp_path):
    root = _project(tmp_path, V095)
    assert _config(root)['report'] is True
    _apply(root)
    written = _config(root)
    assert 'report' not in written, written


# purlin: update PROOF-44
def test_a_dashboard_switch_set_off_is_not_written_back_either(tmp_path):
    root = _project(tmp_path, V095)
    _set_config(root, report=False)
    _apply(root)
    written = _config(root)
    assert 'report' not in written, written


# purlin: update PROOF-12
def test_the_gate_defaults_to_passed(tmp_path):
    root = _project(tmp_path, V095)
    before = _config(root)
    assert 'gate' not in before and before['pre_push'] == 'off', before
    _apply(root)
    assert _config(root)['gate'] == 'passed'


# purlin: update PROOF-45
def test_the_gate_defaults_to_strong_when_the_hook_was_strict(tmp_path):
    root = _project(tmp_path, V095)
    _set_config(root, pre_push='strict')
    _apply(root)
    assert _config(root)['gate'] == 'strong'


# purlin: update PROOF-46
def test_the_gate_question_takes_the_answer_you_type(tmp_path, capsys,
                                                     monkeypatch):
    root = _project(tmp_path, V095)
    asked = _answers(monkeypatch, [('Gate [', 'signed')])
    _apply(root, argv=())
    printed = capsys.readouterr().out
    assert ('What must be true of every rule before a version is proven?'
            in printed), printed
    assert scaffold.GATE_QUESTION in printed, printed
    assert len([prompt for prompt in asked if prompt.startswith('Gate [')]) == 1
    assert _config(root)['gate'] == 'signed'


# purlin: update PROOF-47
def test_an_answer_that_is_not_a_gate_leaves_the_default(tmp_path, capsys,
                                                         monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Gate [', 'whenever')])
    _apply(root, argv=())
    capsys.readouterr()
    assert _config(root)['gate'] == 'passed'


# purlin: update PROOF-48
def test_the_gate_the_project_named_is_the_default(tmp_path, capsys,
                                                   monkeypatch):
    root = _project(tmp_path, V095)
    assert _config(root)['pre_push'] == 'off'
    _set_config(root, gate='signed')
    asked = _answers(monkeypatch, [('Gate [', '')])
    _apply(root, argv=())
    capsys.readouterr()
    assert [prompt for prompt in asked if 'Gate [' in prompt] == [
        'Gate [signed]: ']
    assert _config(root)['gate'] == 'signed'


# --- the tests setting ---------------------------------------------------------

# purlin: update PROOF-21
def test_a_framework_the_tree_cannot_run_is_dropped(tmp_path, capsys):
    """An older release wrote down every plugin it shipped, runnable or not."""
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    assert _config(root)['test_framework'] == 'pytest,jest,shell,vitest'
    _apply(root)
    printed = capsys.readouterr().out
    from purlin import frameworks
    assert _config(root)['tests'] == [frameworks.entry_for('pytest')]
    for name in ('jest', 'shell', 'vitest'):
        assert ('dropped %s from the tests: nothing in the tree runs it'
                % name) in printed, printed
    assert 'wrote the tests setting: pytest\n' in printed


# purlin: update PROOF-93
def test_a_framework_the_tree_carries_is_kept(tmp_path, capsys):
    root = _project(tmp_path, V095)
    assert _config(root)['test_framework'] == 'pytest,jest,shell,vitest'
    _write(root, 'conftest.py', '')
    _write(root, 'package.json', json.dumps({'devDependencies': {
        'jest': '^29.0.0', 'vitest': '^3.0.0'}}))
    _write(root, 'tests/login.test.sh', 'exit 0\n')
    _apply(root)
    printed = capsys.readouterr().out
    assert [suite['name'] for suite in _config(root)['tests']] == [
        'pytest', 'jest', 'shell', 'vitest']
    assert 'from the tests' not in printed


# purlin: update PROOF-94
def test_xunit_is_read_as_dotnet(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write(root, 'App.Tests/App.Tests.csproj',
           '<Project><ItemGroup><PackageReference Include="xunit" '
           'Version="2.9.0" /></ItemGroup></Project>\n')
    _set_config(root, test_framework='xunit')
    _apply(root)
    printed = capsys.readouterr().out
    from purlin import frameworks
    assert _config(root)['tests'] == [frameworks.entry_for('dotnet')]
    assert 'wrote the tests setting: dotnet\n' in printed
    assert 'from the tests' not in printed


def _detected_suites(tmp_path, capsys, named):
    """The suites and the output with the frameworks named `named`, or none."""
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    _write(root, 'tests/login.test.sh', 'exit 0\n')
    config = _config(root)
    if named is None:
        del config['test_framework']
    else:
        config['test_framework'] = named
    _write(root, '.purlin/config.json', json.dumps(config, indent=2))
    _apply(root)
    printed = capsys.readouterr().out
    return [suite['name'] for suite in _config(root)['tests']], printed


# purlin: update PROOF-95
def test_auto_writes_what_detection_finds(tmp_path, capsys):
    suites, printed = _detected_suites(tmp_path, capsys, 'auto')
    assert suites == ['pytest', 'shell']
    assert 'from the tests' not in printed


# purlin: update PROOF-96
def test_no_framework_named_writes_what_detection_finds(tmp_path, capsys):
    suites, printed = _detected_suites(tmp_path, capsys, None)
    assert suites == ['pytest', 'shell']
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
ONE_TEST_NOW = '; the file is one test now, and passes when it exits 0'


def _old_tests(root):
    for rel, (old, _new) in OLD_TESTS.items():
        _write(root, rel, old)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the tests 0.9.5 marked')


def _rewritten(tmp_path, capsys):
    """The sample project with one old-marked file per framework, updated."""
    root = _project(tmp_path, V095)
    _old_tests(root)
    _apply(root)
    return root, capsys.readouterr().out


# purlin: update PROOF-29
def test_the_pytest_marks_become_comments(tmp_path, capsys):
    root, printed = _rewritten(tmp_path, capsys)
    assert _read(root, 'tests/test_login.py') == NEW_PYTEST
    assert '  rewrote 2 markers in tests/test_login.py as comments\n' in printed


# purlin: update PROOF-107
def test_the_jest_title_tags_become_comments(tmp_path, capsys):
    root, printed = _rewritten(tmp_path, capsys)
    assert _read(root, 'tests/login.test.js') == NEW_JEST
    assert '  rewrote 2 markers in tests/login.test.js as comments\n' in printed


# purlin: update PROOF-108
def test_the_xunit_trait_becomes_a_comment(tmp_path, capsys):
    root, printed = _rewritten(tmp_path, capsys)
    assert _read(root, 'tests/LoginTests.cs') == NEW_XUNIT
    assert '  rewrote 1 marker in tests/LoginTests.cs as comments\n' in printed


# purlin: update PROOF-109
def test_the_shell_harness_calls_become_one_comment(tmp_path, capsys):
    root, printed = _rewritten(tmp_path, capsys)
    assert _read(root, 'tests/login.test.sh') == NEW_SHELL
    assert ('rewrote 1 marker in tests/login.test.sh as comments'
            + ONE_TEST_NOW) in printed


# purlin: update PROOF-110
def test_the_sql_comment_becomes_the_marker(tmp_path, capsys):
    root, printed = _rewritten(tmp_path, capsys)
    assert _read(root, 'tests/test_login.sql') == NEW_SQL
    assert ('rewrote 1 marker in tests/test_login.sql as comments'
            + ONE_TEST_NOW) in printed


# purlin: update PROOF-111
def test_each_rewritten_test_file_is_backed_up(tmp_path):
    root = _project(tmp_path, V095)
    _old_tests(root)
    assert [item['files'] for item in update.pending(root)
            if item['id'] == 'markers'] == [sorted(OLD_TESTS)]
    _apply(root)
    assert 'markers' not in _ids(root)
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
    assert text.splitlines()[2] == module.splitlines()[2]


# --- the plugins and their wiring ----------------------------------------------

OLD_CONFTEST = 'pytest_plugins = [".purlin.plugins.pytest_purlin"]\n'
OLD_JEST_CONFIG = ('module.exports = {\n'
                   '  "reporters": ["default", ".purlin/plugins/jest_purlin.js"]\n'  # retired
                   '};\n')
OLD_VITEST_CONFIG = ("import { defineConfig } from 'vitest/config';\n"
                     'export default defineConfig({\n'
                     "  test: { reporters: ['default', "
                     "'.purlin/plugins/vitest_purlin.ts'] },\n"  # retired
                     '});\n')
OLD_PACKAGE_JSON = json.dumps({'jest': {'reporters': [
    'default', '.purlin/plugins/jest_purlin.js']}}) + '\n'  # retired
WIRING = {'conftest.py': OLD_CONFTEST, 'jest.config.js': OLD_JEST_CONFIG,
          'vitest.config.ts': OLD_VITEST_CONFIG,
          'package.json': OLD_PACKAGE_JSON}
CSPROJ = ('<Project><ItemGroup><Compile Include="../.purlin/plugins/'  # retired
          'xunit_purlin.cs" /></ItemGroup></Project>\n')


def _unwired(tmp_path, capsys):
    """The sample project given the wiring v0.9.5's init wrote, updated."""
    root = _project(tmp_path, V095)
    for rel, text in WIRING.items():
        _write(root, rel, text)
    _write(root, 'App.Tests/App.Tests.csproj', CSPROJ)
    _apply(root)
    return root, capsys.readouterr().out


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


# purlin: update PROOF-81
def test_a_file_the_plugin_did_not_ship_is_left_alone(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, '.purlin/plugins/house_purlin.rb', '# our own reporter\n')  # retired
    _apply(root)
    assert _read(root, '.purlin/plugins/house_purlin.rb') == (  # retired
        '# our own reporter\n')
    assert sorted(os.listdir(os.path.join(root, '.purlin', 'plugins'))) == [
        'house_purlin.rb']


# purlin: update PROOF-82
def test_a_conftest_holding_only_the_wiring_is_deleted(tmp_path, capsys):
    root, printed = _unwired(tmp_path, capsys)
    assert not os.path.exists(os.path.join(root, 'conftest.py'))
    assert "removed conftest.py: it held only the plugin's wiring" in printed


# purlin: update PROOF-83
def test_a_conftest_holding_more_keeps_the_rest(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', 'import os\n\n' + OLD_CONFTEST)
    _apply(root)
    assert _read(root, 'conftest.py') == 'import os\n\n'


# purlin: update PROOF-84
def test_the_jest_config_keeps_its_other_reporter(tmp_path, capsys):
    root, printed = _unwired(tmp_path, capsys)
    assert _read(root, 'jest.config.js') == (
        'module.exports = {\n  "reporters": ["default"]\n};\n')
    assert "removed the plugin's wiring from jest.config.js" in printed


# purlin: update PROOF-85
def test_the_vitest_config_keeps_its_other_reporter(tmp_path, capsys):
    root, printed = _unwired(tmp_path, capsys)
    assert _read(root, 'vitest.config.ts') == (
        "import { defineConfig } from 'vitest/config';\n"
        'export default defineConfig({\n'
        "  test: { reporters: ['default'] },\n"
        '});\n')
    assert "removed the plugin's wiring from vitest.config.ts" in printed


# purlin: update PROOF-86
def test_the_package_json_keeps_its_other_reporter(tmp_path, capsys):
    root, printed = _unwired(tmp_path, capsys)
    assert json.loads(_read(root, 'package.json')) == {
        'jest': {'reporters': ['default']}}
    assert "removed the plugin's wiring from package.json" in printed


# purlin: update PROOF-87
def test_each_file_the_wiring_leaves_is_backed_up(tmp_path, capsys):
    root, _printed = _unwired(tmp_path, capsys)
    for rel, text in WIRING.items():
        (backup,) = [name for name in os.listdir(root)
                     if name.startswith(rel + '.local-')]
        assert _read(root, backup) == text, rel


# purlin: update PROOF-88
def test_a_csproj_compiling_the_logger_is_named_and_left(tmp_path, capsys):
    root, printed = _unwired(tmp_path, capsys)
    assert _read(root, 'App.Tests/App.Tests.csproj') == CSPROJ
    assert ('App.Tests/App.Tests.csproj compiles the xUnit logger v0.9.5 '
            'shipped; remove that line by hand') in printed


# --- design references -------------------------------------------------------

DESIGN_ANCHOR = 'specs/_anchors/checkout_design.md'
DESIGN_FEATURE = 'specs/workflows/figma_web.md'
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
    printed = capsys.readouterr().out
    after = _read(root, DESIGN_ANCHOR)
    for field in DESIGN_FIELDS:
        assert not [line for line in after.splitlines()
                    if line.startswith(field)], field
    # The kind-of-test migration rewrites the anchor's proof line too, so
    # the comparison stops short of the proof lines.
    assert _without(after, ('- PROOF-',)) == _without(
        before, DESIGN_FIELDS + ('- PROOF-',))
    for kept in ('> Description:', '> Type: design', '- RULE-1:'):
        assert kept in after, kept
    assert ('removed the design reference from %s: > Source:, > Pinned:, '
            '> Visual-Reference:, > Visual-Hash:\n' % DESIGN_ANCHOR) in printed


# purlin: update PROOF-99
def test_the_picture_reference_of_the_feature_is_removed(tmp_path, capsys):
    root = _project(tmp_path, V095)
    before = _read(root, DESIGN_FEATURE)
    assert '> Visual-Reference: figma://' in before
    _apply(root)
    printed = capsys.readouterr().out
    after = _read(root, DESIGN_FEATURE)
    assert not [line for line in after.splitlines()
                if line.startswith('> Visual-Reference:')]
    assert _without(after, ('- PROOF-',)) == _without(
        before, ('> Visual-Reference:', '- PROOF-'))
    assert ('removed the design reference from %s: > Visual-Reference:\n'
            % DESIGN_FEATURE) in printed


# purlin: update PROOF-100
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


def _with_anchor(tmp_path, rel, text):
    root = _project(tmp_path, V095)
    _write(root, rel, text)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'a sourced anchor')
    _apply(root)
    return _read(root, rel)


# purlin: update PROOF-101
def test_a_figma_uri_source_goes_with_its_pin(tmp_path):
    figma = _with_anchor(tmp_path, 'specs/_anchors/modal_design.md',
                         FIGMA_URI_ANCHOR)
    assert not [line for line in figma.splitlines()
                if line.startswith(('> Source:', '> Pinned:'))], figma
    assert '- RULE-1: The modal matches the frame' in figma


# purlin: update PROOF-102
def test_a_git_source_and_its_pin_stay(tmp_path):
    assert _with_anchor(tmp_path, 'specs/_anchors/no_eval.md',
                        GIT_ANCHOR) == GIT_ANCHOR


# --- the keys the config step drops -------------------------------------------

# purlin: update PROOF-25
def test_every_dropped_key_is_named(tmp_path, capsys):
    root = _project(tmp_path, V095)
    config = _config(root)
    for key in ('digest', 'report', 'spec_dir', 'pre_push'):
        assert key in config, key
    _set_config(root, audit_criteria='git@github.com:acme/q.git#criteria.md',
                audit_criteria_pinned='abc1234')
    _apply(root)
    printed = capsys.readouterr().out
    assert ('dropped 6 keys this release does not read: audit_criteria, '
            'audit_criteria_pinned, digest, pre_push, report, spec_dir'
            ) in printed, printed
    written = _config(root)
    for key in ('audit_criteria', 'audit_criteria_pinned', 'digest',
                'pre_push', 'report', 'spec_dir'):
        assert key not in written, key


# purlin: update PROOF-103
def test_a_config_with_no_key_to_drop_prints_no_dropped_line(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _write(root, '.purlin/config.json', json.dumps(
        {'version': '0.9.2', 'test_framework': 'pytest'}, indent=2))
    _apply(root)
    printed = capsys.readouterr().out
    assert '  set the gate to passed\n' in printed, printed
    assert 'this release does not read' not in printed, printed


# --- the mutation question ----------------------------------------------------

MUTATION = 'Measure test strength by breaking the code on purpose?'


def _asked_at(asked, needle):
    """The position of the one prompt carrying `needle` among those asked."""
    found = [index for index, prompt in enumerate(asked) if needle in prompt]
    assert len(found) == 1, asked
    return found[0]


# purlin: update PROOF-26
def test_the_mutation_question_defaults_to_no(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    asked = _answers(monkeypatch, [('Gate [', 'strong'), (MUTATION, '')])
    _apply(root, argv=())
    capsys.readouterr()
    assert asked[_asked_at(asked, MUTATION)].startswith(
        MUTATION + ' It needs mutmut'), asked
    assert _asked_at(asked, 'Gate [') < _asked_at(asked, MUTATION)
    written = _config(root)
    assert written['mutation_engine'] == 'none'
    assert written['min_strength'] is None


# purlin: update PROOF-54
def test_yes_turns_it_on_at_the_gate_s_minimum(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    _answers(monkeypatch, [('Gate [', 'strong'), (MUTATION, 'y')])
    _apply(root, argv=())
    printed = capsys.readouterr().out
    written = _config(root)
    assert written['mutation_engine'] == 'auto'
    assert written['min_strength'] == 70
    assert 'run purlin:init to wire mutmut' in printed


# purlin: update PROOF-55
def test_no_engine_means_no_question(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    asked = _answers(monkeypatch, [('Gate [', 'strong')])
    _apply(root, argv=())
    printed = capsys.readouterr().out
    assert not [prompt for prompt in asked if MUTATION in prompt], asked
    assert _config(root)['mutation_engine'] == 'none'
    assert "no engine breaks this project's code" in printed


# purlin: update PROOF-56
def test_at_passed_no_mutation_question_is_asked(tmp_path, capsys,
                                                  monkeypatch):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    asked = _answers(monkeypatch, [('Gate [', 'passed')])
    _apply(root, argv=())
    capsys.readouterr()
    assert not [prompt for prompt in asked if MUTATION in prompt], asked
    written = _config(root)
    assert written['mutation_engine'] == 'none'
    assert written['min_strength'] is None


# purlin: update PROOF-57
def test_at_passed_no_engine_is_named(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    asked = _answers(monkeypatch, [('Gate [', 'passed')])
    _apply(root, argv=())
    printed = capsys.readouterr().out
    assert not [prompt for prompt in asked if MUTATION in prompt], asked
    assert 'no engine breaks' not in printed, printed


# purlin: update PROOF-58
def test_a_mutation_setting_already_written_is_kept(tmp_path, capsys,
                                                    monkeypatch):
    root = _project(tmp_path, V095)
    _write(root, 'conftest.py', '')
    _set_config(root, mutation_engine='auto')
    asked = _answers(monkeypatch, [('Gate [', 'strong')])
    _apply(root, argv=())
    capsys.readouterr()
    assert not [prompt for prompt in asked if MUTATION in prompt], asked
    assert _config(root)['mutation_engine'] == 'auto'


# --- a spec with no scope -----------------------------------------------------

UNSCOPED = """# Feature: nowhere

## Rules

- RULE-1: A rule whose code is not named

## Proof

- PROOF-1 (RULE-1): Call it and verify it answers
"""
UNSCOPED_ANCHOR = UNSCOPED.replace('Feature: nowhere', 'Anchor: unscoped_anchor')
SCOPE_ADVICE = ('1 spec has no > Scope: line: nowhere. Run purlin:spec <name> '
                'to add one. The line is optional below the gate signed and '
                'required at signed.\n')


def _with_specs(tmp_path, specs):
    root = _project(tmp_path, V095)
    for rel, text in specs.items():
        _write(root, rel, text)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'specs with no scope')
    return root


# purlin: update PROOF-27
def test_a_spec_with_no_scope_is_named_and_left_alone(tmp_path, capsys):
    root = _with_specs(tmp_path, {
        'specs/core/nowhere.md': UNSCOPED,
        'specs/_anchors/unscoped_anchor.md': UNSCOPED_ANCHOR})
    _apply(root)
    printed = capsys.readouterr().out
    assert SCOPE_ADVICE in printed, printed
    assert 'unscoped_anchor' not in printed.split('Scope: line:')[1]
    assert _read(root, 'specs/core/nowhere.md') == UNSCOPED
    assert update.pending(root) == []


# purlin: update PROOF-104
def test_the_scope_advice_is_given_again_when_nothing_is_pending(tmp_path,
                                                                 capsys):
    root = _with_specs(tmp_path, {'specs/core/nowhere.md': UNSCOPED})
    _apply(root)
    capsys.readouterr()
    _apply(root)
    again = capsys.readouterr().out
    assert 'Nothing is pending' in again
    assert SCOPE_ADVICE in again, again


# purlin: update PROOF-105
def test_an_anchor_with_no_scope_gets_no_advice(tmp_path, capsys):
    root = _with_specs(tmp_path, {
        'specs/_anchors/unscoped_anchor.md': UNSCOPED_ANCHOR})
    _apply(root)
    printed = capsys.readouterr().out
    assert '> Scope: line' not in printed, printed


# --- the evidence folder ------------------------------------------------------

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


# --- operating-system tags ---------------------------------------------------

WINDOWS_SPEC = 'specs/audit/static_checks.md'

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
    assert _spec_holding(root, 'msvcrt.locking') == WINDOWS_SPEC
    assert [line for line in _read(root, WINDOWS_SPEC).splitlines()
            if line.startswith('- PROOF-53 ')][0].endswith(' @windows')
    _apply(root)
    text = _read(root, WINDOWS_SPEC)
    proofs = [line for line in text.splitlines()
              if line.startswith('- PROOF-53 ')]
    assert len(proofs) == 1
    assert proofs[0].endswith(' @env(windows)')
    assert '@unit' not in proofs[0]  # retired
    assert not [line for line in text.splitlines()
                if line.endswith('@windows')]


# purlin: update PROOF-79
def test_prose_that_is_not_a_tag_is_left_alone(tmp_path):
    root = _with_specs(tmp_path, {'specs/core/runners.md': PROSE_SPEC})
    _apply(root)
    assert _read(root, 'specs/core/runners.md') == PROSE_SPEC


# purlin: update PROOF-23
def test_the_kind_of_test_is_dropped_from_every_proof_line(tmp_path):
    root = _project(tmp_path, V095)
    rel = 'specs/_anchors/proof_common.md'
    before = [line for line in _read(root, rel).splitlines()
              if line.startswith('- PROOF-')]
    assert before[0].endswith(' @integration')  # retired
    _apply(root)
    after = [line for line in _read(root, rel).splitlines()
             if line.startswith('- PROOF-')]
    assert len(after) == len(before)
    for line in after:
        assert not re.search(r'@(unit|integration|e2e)\s*$', line), line
    assert after[0] == before[0][:-len(' @integration')]  # retired
    assert after[0].endswith('written to `specs/hooks/`'), after[0]


# purlin: update PROOF-98
def test_an_env_tag_after_the_kind_of_test_is_kept(tmp_path):
    root = _project(tmp_path, V095)
    rel = 'specs/_anchors/proof_common.md'
    with open(os.path.join(root, rel), 'a', encoding='utf-8') as handle:
        handle.write('- PROOF-14 (RULE-1): Lock a file @e2e @env(linux)\n')  # retired
    _apply(root)
    added = [line for line in _read(root, rel).splitlines()
             if line.startswith('- PROOF-14 ')]
    assert added == ['- PROOF-14 (RULE-1): Lock a file @env(linux)']


# --- hooks -------------------------------------------------------------------

LINT_STAGED = '#!/bin/sh\nexec ./node_modules/.bin/lint-staged\n'
HUSKY = '#!/bin/sh\nexec ./node_modules/.bin/husky-run\n'


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
def test_a_foreign_hook_beside_an_old_one_is_left_alone(tmp_path):
    root = _hooks(tmp_path, LINT_STAGED, OLD_PRE_PUSH)
    _apply(root)
    folder = os.path.join(root, '.git', 'hooks')
    assert not os.path.exists(os.path.join(folder, 'pre-push'))
    assert _read(folder, 'pre-commit') == LINT_STAGED


# purlin: update PROOF-77
def test_hooks_another_tool_wrote_are_left_byte_for_byte(tmp_path):
    root = _hooks(tmp_path, LINT_STAGED, HUSKY)
    folder = os.path.join(root, '.git', 'hooks')
    before = sorted(os.listdir(folder))
    assert 'hooks' not in _ids(root)
    _apply(root)
    assert sorted(os.listdir(folder)) == before
    assert _read(folder, 'pre-commit') == LINT_STAGED
    assert _read(folder, 'pre-push') == HUSKY


# --- workflows ---------------------------------------------------------------

def _workflows(root):
    """Every workflow file under `.github/` and the pipeline at the root."""
    return [rel for rel in _walk(root, ('*.yml', '*.yaml'))
            if rel.startswith('.github/')
            or rel == 'purlin.azure-pipelines.yml']


# purlin: update PROOF-15
def test_one_purlin_yml_replaces_the_retired_workflow(tmp_path):
    root = _project(tmp_path, V095)
    assert _workflows(root) == ['.github/workflows/windows-proofs.yml']
    _apply(root)
    assert _workflows(root) == ['.github/workflows/purlin.yml']
    text = _read(root, '.github/workflows/purlin.yml')
    assert 'windows-latest' in text
    assert 'v%s' % VERSION in text
    assert "branches: ['run/**']" in text
    assert "tags: ['signed/**']" in text


# purlin: update PROOF-32
def test_an_azure_remote_gets_the_pipeline_where_init_writes_it(tmp_path):
    root = _project(tmp_path, V095, remote=False)
    _git(root, 'remote', 'add', 'origin',
         'https://dev.azure.com/acme/demo/_git/demo')
    _apply(root)
    assert _workflows(root) == ['purlin.azure-pipelines.yml']
    text = _read(root, 'purlin.azure-pipelines.yml')
    assert 'windows-latest' in text
    assert 'v%s' % VERSION in text


# purlin: update PROOF-49
def test_declining_the_workflow_leaves_it_unwritten(tmp_path, capsys,
                                                    monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Write .github/workflows/purlin.yml', 'n')])
    _apply(root, argv=())
    printed = capsys.readouterr().out
    assert _workflows(root) == []
    assert 'run purlin:init again to add it later' in printed
    assert 'workflows' not in _ids(root)


# purlin: update PROOF-50
def test_a_project_with_no_remote_gets_no_workflow(tmp_path, capsys):
    root = _project(tmp_path, V095, remote=False)
    _apply(root)
    printed = capsys.readouterr().out
    assert _workflows(root) == []
    assert 'No git remote, so there is no runner to read this workflow' in printed
    assert 'left the workflow unwritten; a prerequisite is missing' in printed


# purlin: update PROOF-51
def test_a_host_init_writes_no_workflow_for_gets_none(tmp_path, capsys):
    root = _project(tmp_path, V095, remote=False)
    _git(root, 'remote', 'add', 'origin', 'https://gitlab.com/acme/demo.git')
    _apply(root)
    printed = capsys.readouterr().out
    assert _workflows(root) == []
    assert ('This git host cannot run tests remotely. Everything on this '
            'machine works.') in printed
    assert 'left the workflow unwritten; a prerequisite is missing' in printed


# purlin: update PROOF-80
def test_no_proof_for_another_system_means_no_workflow(tmp_path, capsys):
    root = _project(tmp_path, V095)
    text = _read(root, WINDOWS_SPEC)
    tag = re.compile(r'(?m)[ \t]+@windows[ \t]*$')
    assert len(tag.findall(text)) == 2
    _write(root, WINDOWS_SPEC, tag.sub('', text))
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'no proof names Windows')
    assert 'workflows' in _ids(root)
    _apply(root)
    printed = capsys.readouterr().out
    assert _workflows(root) == []
    assert ('wrote no workflow: every test runs on this operating system'
            in printed), printed


# --- the dashboard page ------------------------------------------------------

def _shipped_page():
    with open(os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html'),
              'rb') as handle:
        return handle.read()


def _page(root):
    with open(os.path.join(root, 'purlin-report.html'), 'rb') as handle:
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
    assert _page(root) == _shipped_page()
    assert 'dashboard' not in _ids(root)


# purlin: update PROOF-112
def test_an_older_copy_of_the_page_is_replaced(tmp_path, capsys):
    root = _updated(tmp_path)
    capsys.readouterr()
    _write(root, 'purlin-report.html', '<html>an older copy</html>\n')
    assert 'dashboard' in _ids(root)
    _apply(root)
    capsys.readouterr()
    assert _page(root) == _shipped_page()


# purlin: update PROOF-113
def test_a_project_with_no_page_is_left_without_one(tmp_path):
    root = _project(tmp_path, V095)
    page = os.path.join(root, 'purlin-report.html')
    assert not os.path.lexists(page)
    assert 'dashboard' not in _ids(root)
    _apply(root)
    assert not os.path.lexists(page)


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
    names = ' '.join(backups)
    assert '.purlin/config.json.local-' in names
    assert '.gitignore.local-' in names
    assert any(rel.startswith('specs/') for rel in backups)
    for rel in backups:
        named = BACKUP_NAME.match(rel)
        assert named, rel
        assert named.group(1) in before, rel
        with open(os.path.join(root, rel), 'rb') as handle:
            data = handle.read()
        assert hashlib.sha256(data).hexdigest()[:8] == named.group(2), rel


# purlin: update PROOF-71
def test_every_backed_up_file_keeps_its_bytes_from_before_the_run(tmp_path):
    root, before, backups = _backed_up(tmp_path)
    held = {}
    for rel in backups:
        with open(os.path.join(root, rel), 'rb') as handle:
            held.setdefault(BACKUP_NAME.match(rel).group(1), []).append(
                handle.read())
    assert held
    for rel, copies in held.items():
        assert before[rel] in copies, rel


# purlin: update PROOF-72
def test_a_spec_two_migrations_rewrite_has_a_backup_from_each(tmp_path):
    root = _project(tmp_path, V095)
    before = _read(root, DESIGN_ANCHOR)
    _apply(root)
    folder, name = os.path.split(os.path.join(root, DESIGN_ANCHOR))
    copies = sorted(_read(folder, entry) for entry in os.listdir(folder)
                    if entry.startswith(name + '.local-'))
    without = ''.join(line for line in before.splitlines(True)
                      if not line.startswith(DESIGN_FIELDS))
    assert len(before.splitlines()) - len(without.splitlines()) == 4
    assert copies == sorted([before, without])


# purlin: update PROOF-73
def test_the_config_backup_holds_what_it_said_before(tmp_path):
    root = _project(tmp_path, V095)
    before = _read(root, '.purlin/config.json')
    _apply(root)
    backups = _walk(root, ('config.json.local-*.bak',), skip_backups=False)
    assert len(backups) == 1
    assert _read(root, backups[0]) == before


# purlin: update PROOF-74
def test_a_backup_is_not_written_twice(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    first = _walk(root, ('*.bak',), skip_backups=False)
    _apply(root)
    assert _walk(root, ('*.bak',), skip_backups=False) == first


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
    left = _git(root, 'status', '--porcelain').stdout.splitlines()
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


# purlin: update PROOF-92
def test_status_says_it_even_when_the_config_is_already_clean(tmp_path):
    """The line must come from the pending list, not only from a config warning."""
    root = _project(tmp_path, V095)
    _apply(root)
    _write(root, 'specs/core/later.md',
           '# Feature: later\n\n## Rules\n\n- RULE-1: x\n\n## Proof\n\n'
           '- PROOF-1 (RULE-1): y @windows\n')
    assert _ids(root) == ['os-tags']
    assert UPDATE_LINE in status_module.sync_status(root).splitlines()


# --- the copy the update prints ----------------------------------------------

# purlin: update PROOF-20
def test_what_the_update_prints_carries_no_emoji(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root)
    printed = capsys.readouterr().out
    for char in printed:
        assert ord(char) < 0x2190 or char in '→─', repr(char)


def _status_ending(root):
    """The summary sentence and `Left to do` lines the status ends on."""
    from purlin import payload as purlin_payload, summary as purlin_summary
    return purlin_summary.ending(
        purlin_payload.build_payload(str(root))).splitlines()


# purlin: update PROOF-52
def test_the_run_ends_as_the_status_ends(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root)
    printed = capsys.readouterr().out.rstrip().splitlines()
    ending = _status_ending(root)
    assert printed[-len(ending):] == ending, printed
    assert not printed[-len(ending) - 1].startswith('→'), printed


# purlin: update PROOF-53
def test_a_run_that_leaves_work_names_the_update_above_the_summary(
        tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Apply plugins', 'n')])
    _apply(root, argv=())
    printed = capsys.readouterr().out.rstrip().splitlines()
    ending = _status_ending(root)
    assert printed[-len(ending):] == ending, printed
    assert printed[-len(ending) - 1] == UPDATE_LINE, printed


# --- a project 0.9.5 set up and nobody upgraded -------------------------------

def _updated(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    return root


# purlin: update PROOF-59
def test_an_updated_project_is_not_one_0_9_5_set_up(tmp_path, capsys):
    root = _project(tmp_path, V095)
    assert update.set_up_by_095(root)
    _apply(root)
    capsys.readouterr()
    assert not update.set_up_by_095(root)


# purlin: update PROOF-60
def test_a_settings_file_with_no_tests_reads_as_0_9_5(tmp_path, capsys):
    root = _updated(tmp_path)
    capsys.readouterr()
    _set_config(root, tests=None)
    assert update.set_up_by_095(root)


@pytest.mark.parametrize('key', ('test_framework', 'spec_dir', 'pre_push',
                                 'report', 'digest'))
# purlin: update PROOF-61
def test_a_key_only_0_9_5_wrote_reads_as_0_9_5(tmp_path, capsys, key):
    root = _updated(tmp_path)
    capsys.readouterr()
    assert not update.set_up_by_095(root)
    _set_config(root, **{key: 'pytest'})
    assert update.set_up_by_095(root)


# purlin: update PROOF-62
def test_a_proof_file_under_specs_reads_as_0_9_5(tmp_path, capsys):
    root = _updated(tmp_path)
    capsys.readouterr()
    _write(root, 'specs/core/login.proofs-unit.json', '{}\n')
    assert update.set_up_by_095(root)


# purlin: update PROOF-63
def test_a_run_file_under_specs_reads_as_0_9_5(tmp_path, capsys):
    root = _updated(tmp_path)
    capsys.readouterr()
    _write(root, 'specs/core/login.receipt.json', '{}\n')
    assert update.set_up_by_095(root)


# purlin: update PROOF-64
def test_no_settings_file_is_not_a_0_9_5_project(tmp_path):
    root = str(tmp_path / 'unset')
    os.makedirs(os.path.join(root, '.purlin'))
    assert not update.set_up_by_095(root)


# purlin: update PROOF-65
def test_the_version_stamp_is_not_read(tmp_path, capsys):
    root = _updated(tmp_path)
    capsys.readouterr()
    _set_config(root, version='0.9.2')
    assert 'config' in _ids(root)
    assert not update.set_up_by_095(root)


# purlin: update PROOF-66
def test_the_dashboard_page_is_not_read(tmp_path, capsys):
    root = _updated(tmp_path)
    capsys.readouterr()
    _write(root, 'purlin-report.html', '<html>an older copy</html>\n')
    assert 'dashboard' in _ids(root)
    assert not update.set_up_by_095(root)
