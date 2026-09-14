"""Proofs for `scripts/init/update.py`, the edits `purlin:init --update` makes.

Every case here drives the real script against a real git repository made from
one of the two upgrade fixtures, never against a hand-built expectation of what
the script would do, so the script and these proofs cannot drift apart. The
fixtures themselves are frozen: each test copies one into a temporary directory
and runs `git init` there.

One convention runs through this file. The spellings this release retired are
never written out: the scope tag is built as `'@' + 'on('`, the verification
file name carries a character class (`recei[p]t`), and a spec is found by
searching for its text rather than by naming a path that carries a retired word.
`dev/test_vocabulary.py` reads this file with no exception for it, so a fixture
spelled out in full would fail that proof.

What each group proves:

*pending*     what `--check` finds in each old layout, what it prints, what it
              exits with, and that it writes nothing
*applying*    `--yes` applies every migration, a second run finds nothing, and
              a declined migration stays pending
*specs*       no proof or verification file survives beside a spec
*config*      the file that is left is the gate and what the gate derives
*tags*        a scope becomes `@env(<os>)` when the person confirms it, and is
              dropped when they do not or when it names no operating system
*designs*     a design source becomes a path under `designs/`
*hooks*       the pre-commit shim and its delegator go, the pre-push shim is
              repointed
*workflows*   the retired workflows go and one `purlin.yml` replaces them
*plugins*     each copy under `.purlin/plugins/` matches the plugin again
*records*     `.purlin/records/` exists with the README that explains it
*backups*     every rewritten file leaves its previous bytes beside it
*commit*      one commit, naming the migrations it carries
*status*      `sync_status` says to run the update while anything is pending
"""

import fnmatch
import json
import os
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
V010 = 'upgrade-0.10-dev'
LAYOUTS = (V095, V010)

# The retired spellings, never written out. See the module docstring.
SCOPE = '@' + 'on('
LEFTOVER = ('*.proofs-*.json', '*.recei[p]t.json')

VERSION = open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip()


# --- building a project to run against --------------------------------------

def _git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root,
                          capture_output=True, text=True)


def _project(tmp_path, layout):
    """One upgrade fixture, copied to a temporary directory and committed."""
    root = os.path.join(str(tmp_path), layout)
    shutil.copytree(os.path.join(DEV, 'fixtures', layout), root)
    os.rename(os.path.join(root, '_gitignore'),
              os.path.join(root, '.gitignore'))
    _git(root, 'init', '-q')
    _git(root, 'config', 'user.name', 'Test Person')
    _git(root, 'config', 'user.email', 'test@example.com')
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'init')
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

def test_check_on_the_v095_layout_names_every_migration(tmp_path, capsys):
    root = _project(tmp_path, V095)
    assert update.main(['--check', '--project-root', root]) == 1
    printed = capsys.readouterr().out
    for migration_id in _ids(root):
        assert migration_id in printed
    assert 'Run: purlin:init --update' in printed


def test_the_v095_layout_needs_the_migrations_that_layout_left(tmp_path):
    root = _project(tmp_path, V095)
    found = _ids(root)
    for expected in ('os-tags', 'untracked-files', 'config', 'workflows',
                     'plugin-copies', 'records'):
        assert expected in found, found


def test_the_010_layout_needs_its_hooks_migrated_too(tmp_path):
    root = _project(tmp_path, V010)
    found = _ids(root)
    assert 'hooks' in found, found
    for expected in ('os-tags', 'untracked-files', 'config', 'workflows',
                     'plugin-copies', 'records'):
        assert expected in found, found


def test_check_exits_1_while_anything_is_pending(tmp_path):
    root = _project(tmp_path, V095)
    done = subprocess.run([sys.executable, UPDATE, '--check',
                           '--project-root', root],
                          capture_output=True, text=True)
    assert done.returncode == 1
    assert 'untracked-files' in done.stdout


def test_check_writes_nothing(tmp_path):
    root = _project(tmp_path, V010)
    before = _git(root, 'status', '--porcelain').stdout
    update.main(['--check', '--project-root', root])
    assert _git(root, 'status', '--porcelain').stdout == before


def test_json_lists_the_same_migrations(tmp_path, capsys):
    root = _project(tmp_path, V095)
    update.main(['--check', '--json', '--project-root', root])
    payload = json.loads(capsys.readouterr().out)
    assert payload['project_root'] == os.path.abspath(root)
    assert [item['id'] for item in payload['pending']] == _ids(root)
    for item in payload['pending']:
        assert item['description']
        assert item['files']


def test_a_root_without_purlin_exits_2(tmp_path, capsys):
    empty = str(tmp_path / 'empty')
    os.makedirs(empty)
    assert update.main(['--check', '--project-root', empty]) == 2
    assert 'nothing to update' in capsys.readouterr().err


def test_pending_is_empty_for_a_root_without_purlin(tmp_path):
    empty = str(tmp_path / 'bare')
    os.makedirs(empty)
    assert update.pending(empty) == []


# --- applying ----------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
def test_yes_applies_every_migration(tmp_path, capsys, layout):
    root = _project(tmp_path, layout)
    assert _apply(root) == 0
    capsys.readouterr()
    assert update.pending(root) == []
    assert update.main(['--check', '--project-root', root]) == 0
    assert 'Nothing is pending' in capsys.readouterr().out


@pytest.mark.parametrize('layout', LAYOUTS)
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


def test_a_declined_migration_is_left_pending(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    before = _ids(root)
    _answers(monkeypatch, default='n')
    assert _apply(root, argv=()) == 0
    printed = capsys.readouterr().out
    assert 'skipped config' in printed
    assert _ids(root) == before


def test_one_declined_migration_does_not_stop_the_others(tmp_path, capsys,
                                                         monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Apply records', 'n')])
    _apply(root, argv=())
    capsys.readouterr()
    assert _ids(root) == ['records']


# --- the files beside the specs ----------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
def test_no_proof_or_verification_file_remains_on_disk(tmp_path, layout):
    root = _project(tmp_path, layout)
    assert _walk(root, LEFTOVER), 'the fixture should start with some'
    _apply(root)
    assert _walk(root, LEFTOVER) == []


@pytest.mark.parametrize('layout', LAYOUTS)
def test_no_proof_or_verification_file_remains_tracked(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    left = [rel for rel in _tracked(root)
            if any(fnmatch.fnmatch(os.path.basename(rel), p)
                   for p in LEFTOVER)]
    assert left == []


@pytest.mark.parametrize('layout', LAYOUTS)
def test_the_dashboard_data_is_untracked_and_ignored(tmp_path, layout):
    root = _project(tmp_path, layout)
    assert '.purlin/report-data.js' in _tracked(root)
    _apply(root)
    assert '.purlin/report-data.js' not in _tracked(root)
    assert os.path.isfile(os.path.join(root, '.purlin', 'report-data.js'))
    ignored = _read(root, '.gitignore').splitlines()
    assert '.purlin/report-data.js' in ignored
    assert '.purlin/report-stamp.js' in ignored


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
def test_the_config_is_the_gate_shape(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    config = json.loads(_read(root, '.purlin/config.json'))
    assert config['version'] == VERSION
    assert config['gate'] == 'tested'
    assert config['ai_review_at'] == 'never'
    assert config['min_strength'] == 50
    assert config['mutation_engine'] == 'auto'
    assert config['sql_engine'] is None
    assert config['ci'] == 'github'
    assert config['pre_push'] in ('on', 'off')


@pytest.mark.parametrize('layout', LAYOUTS)
def test_retired_keys_are_gone(tmp_path, layout):
    root = _project(tmp_path, layout)
    before = json.loads(_read(root, '.purlin/config.json'))
    retired = update._gate().RETIRED_KEYS
    assert any(key in before for key in retired), before
    _apply(root)
    after = json.loads(_read(root, '.purlin/config.json'))
    assert [key for key in retired if key in after] == []


def test_the_gate_defaults_to_tested(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    assert json.loads(_read(root, '.purlin/config.json'))['gate'] == 'tested'


def test_the_gate_defaults_to_recorded_when_the_hook_was_strict(tmp_path):
    root = _project(tmp_path, V095)
    config = json.loads(_read(root, '.purlin/config.json'))
    config['pre_push'] = 'strict'
    _write(root, '.purlin/config.json', json.dumps(config, indent=2))
    _apply(root)
    written = json.loads(_read(root, '.purlin/config.json'))
    assert written['gate'] == 'recorded'
    assert written['min_strength'] == 70
    assert written['ai_review_at'] == 'high'


def test_the_gate_question_takes_the_answer_you_type(tmp_path, capsys,
                                                     monkeypatch):
    root = _project(tmp_path, V095)
    asked = _answers(monkeypatch, [('Gate [', 'approved')])
    _apply(root, argv=())
    capsys.readouterr()
    assert any('Gate [' in prompt for prompt in asked)
    written = json.loads(_read(root, '.purlin/config.json'))
    assert written['gate'] == 'approved'
    assert written['approvers'] == []


def test_an_answer_that_is_not_a_gate_leaves_the_default(tmp_path, capsys,
                                                         monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Gate [', 'whenever')])
    _apply(root, argv=())
    capsys.readouterr()
    assert json.loads(_read(root, '.purlin/config.json'))['gate'] == 'tested'


# --- operating-system tags ---------------------------------------------------

def test_a_confirmed_scope_becomes_env(tmp_path):
    root = _project(tmp_path, V010)
    rel = _spec_holding(root, 'msvcrt.locking')
    assert SCOPE in _read(root, rel)
    _apply(root)
    text = _read(root, rel)
    assert '@env(windows)' in text
    assert SCOPE not in text


@pytest.mark.parametrize('layout', LAYOUTS)
def test_no_spec_carries_the_retired_scope_afterwards(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    for rel in _walk(root, ('*.md',)):
        if rel.startswith('specs/'):
            assert '%swindows-2022)' % SCOPE not in _read(root, rel)
            assert '%sfigma-mcp)' % SCOPE not in _read(root, rel)


def test_a_declined_scope_drops_the_tag(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V010)
    rel = _spec_holding(root, 'msvcrt.locking')
    _answers(monkeypatch, [('Rewrite the windows-2022 scope', 'n')])
    _apply(root, argv=())
    printed = capsys.readouterr().out
    text = _read(root, rel)
    assert SCOPE not in text
    assert '@env(' not in text
    assert 'rather than guess an operating system' in printed


def test_the_retired_tier_tag_becomes_unit_and_env(tmp_path):
    root = _project(tmp_path, V095)
    rel = _spec_holding(root, 'msvcrt.locking')
    assert '@windows\n' in _read(root, rel)
    _apply(root)
    text = _read(root, rel)
    proofs = [line for line in text.splitlines()
              if line.startswith('- PROOF-53 ')]
    assert len(proofs) == 1
    assert proofs[0].endswith('@unit @env(windows)')
    assert '@windows\n' not in text


def test_a_scope_naming_no_operating_system_is_dropped(tmp_path, capsys):
    root = _project(tmp_path, V010)
    rel = _spec_holding(root, 'TEZI0T6lObCJrC9mkmZT8v')
    assert SCOPE in _read(root, rel)
    _apply(root)
    printed = capsys.readouterr().out
    assert SCOPE not in _read(root, rel)
    assert 'it names no operating system' in printed


def test_prose_that_is_not_a_tag_is_left_alone(tmp_path):
    root = _project(tmp_path, V010)
    rel = _spec_holding(root, 'awaiting_runner')
    before = _read(root, rel)
    assert '%s<' % SCOPE in before       # a placeholder, not a real scope
    _apply(root)
    assert '%s<' % SCOPE in _read(root, rel)


# --- design sources ----------------------------------------------------------

DESIGN_ANCHOR = """# Anchor: checkout_design

> Type: design
> Source: figma://file/ABC123/checkout
> Visual-Reference: figma://file/ABC123/checkout?node-id=7-81
>   the second line of the reference, which goes with it
> Visual-Hash: 0f1e2d3c
> Pinned: 0f1e2d3c

## Rules

- RULE-1: The checkout page shows the order total above the pay button

## Proof

- PROOF-1 (RULE-1): Open /checkout and read the two elements in order @e2e
"""


def _with_design(tmp_path, layout):
    root = _project(tmp_path, layout)
    _write(root, 'specs/_anchors/checkout_design.md', DESIGN_ANCHOR)
    _git(root, 'add', '-A')
    _git(root, 'commit', '-qm', 'the design anchor')
    return root


def test_a_design_source_becomes_a_designs_path(tmp_path):
    root = _with_design(tmp_path, V095)
    assert 'design-sources' in _ids(root)
    _apply(root)
    text = _read(root, 'specs/_anchors/checkout_design.md')
    assert '> Source: designs/checkout_design/' in text
    assert 'figma://' not in text


def test_the_visual_fields_are_dropped(tmp_path):
    root = _with_design(tmp_path, V010)
    _apply(root)
    text = _read(root, 'specs/_anchors/checkout_design.md')
    assert 'Visual-Reference' not in text
    assert 'Visual-Hash' not in text
    assert 'the second line of the reference' not in text
    assert '> Pinned: 0f1e2d3c' in text
    assert 'RULE-1: The checkout page' in text


def test_the_design_migration_is_not_pending_afterwards(tmp_path):
    root = _with_design(tmp_path, V010)
    _apply(root)
    assert 'design-sources' not in _ids(root)


# --- hooks -------------------------------------------------------------------

def test_the_pre_commit_shim_goes(tmp_path):
    root = _project(tmp_path, V010)
    assert os.path.isfile(os.path.join(root, '.purlin', 'hooks', 'pre-commit'))
    _apply(root)
    assert not os.path.exists(
        os.path.join(root, '.purlin', 'hooks', 'pre-commit'))
    assert '.purlin/hooks/pre-commit' not in _tracked(root)


def test_the_delegator_git_runs_goes_too(tmp_path):
    root = _project(tmp_path, V010)
    delegator = os.path.join(root, '.git', 'hooks', 'pre-commit')
    with open(delegator, 'w', encoding='utf-8') as handle:
        handle.write('#!/bin/sh\nexec "$(git rev-parse --show-toplevel)"'
                     '/.purlin/hooks/pre-commit "$@"\n')
    assert '.git/hooks/pre-commit' in [
        item['files'] for item in update.pending(root)
        if item['id'] == 'hooks'][0]
    _apply(root)
    assert not os.path.exists(delegator)


def test_a_foreign_delegator_is_left_alone(tmp_path):
    root = _project(tmp_path, V010)
    delegator = os.path.join(root, '.git', 'hooks', 'pre-commit')
    with open(delegator, 'w', encoding='utf-8') as handle:
        handle.write('#!/bin/sh\nexec ./node_modules/.bin/lint-staged\n')
    _apply(root)
    assert os.path.isfile(delegator)


def test_the_pre_push_shim_is_repointed(tmp_path):
    root = _project(tmp_path, V010)
    shim = '.purlin/hooks/pre-push'
    text = _read(root, shim).replace(
        'PURLIN_SCRIPT="scripts/hooks/pre-push.sh"',
        'PURLIN_SCRIPT="scripts/hooks/pre_push_hook.py"')
    _write(root, shim, text)
    _git(root, 'commit', '-aqm', 'an older shim')
    assert shim in [item['files'] for item in update.pending(root)
                    if item['id'] == 'hooks'][0]
    _apply(root)
    after = _read(root, shim)
    assert 'PURLIN_SCRIPT="scripts/hooks/pre-push.sh"' in after
    assert 'pre_push_hook.py' not in after
    assert 'purlin_interpreter()' in after   # the rest of the shim is untouched


def test_a_shim_already_pointing_here_is_left_alone(tmp_path):
    root = _project(tmp_path, V010)
    before = _read(root, '.purlin/hooks/pre-push')
    _apply(root)
    assert _read(root, '.purlin/hooks/pre-push') == before


def test_a_project_with_no_hooks_needs_no_hook_migration(tmp_path):
    root = _project(tmp_path, V095)
    assert 'hooks' not in _ids(root)


# --- workflows ---------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
def test_the_retired_workflows_are_removed(tmp_path, layout):
    root = _project(tmp_path, layout)
    before = _walk(root, ('*.yml',))
    assert any(rel.startswith('.github/workflows/') for rel in before)
    _apply(root)
    after = [rel for rel in _walk(root, ('*.yml',))
             if rel.startswith('.github/workflows/')]
    assert after == ['.github/workflows/purlin.yml']


def test_purlin_yml_carries_the_matrix_the_tags_name(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    text = _read(root, '.github/workflows/purlin.yml')
    assert 'windows-latest' in text
    assert 'v%s' % VERSION in text


def test_declining_the_workflow_leaves_it_unwritten(tmp_path, capsys,
                                                    monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Write .github/workflows/purlin.yml', 'n')])
    _apply(root, argv=())
    printed = capsys.readouterr().out
    assert not os.path.exists(
        os.path.join(root, '.github', 'workflows', 'purlin.yml'))
    assert 'run purlin:init --ci to add it later' in printed
    assert 'workflows' not in _ids(root)


# --- plugin copies -----------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
def test_every_copy_matches_the_plugin_afterwards(tmp_path, layout):
    root = _project(tmp_path, layout)
    assert 'plugin-copies' in _ids(root)
    _apply(root)
    assert 'plugin-copies' not in _ids(root)


def test_the_renamed_shell_plugin_keeps_its_name(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    copied = os.path.join(root, '.purlin', 'plugins', 'purlin-proof.sh')
    assert os.path.isfile(copied)
    source = os.path.join(ROOT, 'scripts', 'proof', 'shell_purlin.sh')
    with open(copied, 'rb') as one, open(source, 'rb') as two:
        assert one.read() == two.read()


def test_a_copy_the_plugin_does_not_ship_is_left_alone(tmp_path):
    root = _project(tmp_path, V095)
    _write(root, '.purlin/plugins/house_purlin.rb', '# our own reporter\n')
    _apply(root)
    assert _read(root, '.purlin/plugins/house_purlin.rb') == (
        '# our own reporter\n')


# --- records -----------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
def test_the_records_folder_and_its_readme_are_created(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    readme = _read(root, '.purlin/records/README.md')
    assert 'One file per verify run' in readme
    assert '.purlin/records/README.md' in _tracked(root)


# --- backups -----------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
def test_every_rewritten_file_leaves_its_previous_bytes(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    backups = _walk(root, ('*.bak',), skip_backups=False)
    names = ' '.join(backups)
    assert '.purlin/config.json.local-' in names
    assert '.gitignore.local-' in names
    assert any(rel.startswith('.purlin/plugins/') for rel in backups)
    assert any(rel.startswith('specs/') for rel in backups)


def test_a_backup_holds_what_the_file_said_before(tmp_path):
    root = _project(tmp_path, V095)
    before = _read(root, '.purlin/config.json')
    _apply(root)
    backups = [rel for rel in _walk(root, ('config.json.local-*.bak',),
                                    skip_backups=False)]
    assert len(backups) == 1
    assert _read(root, backups[0]) == before


def test_a_backup_is_not_written_twice(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    first = _walk(root, ('*.bak',), skip_backups=False)
    _apply(root)
    assert _walk(root, ('*.bak',), skip_backups=False) == first


# --- the commit --------------------------------------------------------------

@pytest.mark.parametrize('layout', LAYOUTS)
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
def test_nothing_is_left_uncommitted_but_the_backups(tmp_path, layout):
    root = _project(tmp_path, layout)
    _apply(root)
    left = _git(root, 'status', '--porcelain').stdout.splitlines()
    assert left, 'the backups should still be sitting there'
    for line in left:
        assert line.startswith('?? '), line
        assert line.endswith('.bak'), line


def test_a_run_that_applies_nothing_writes_no_commit(tmp_path, capsys,
                                                     monkeypatch):
    root = _project(tmp_path, V095)
    head = _git(root, 'rev-parse', 'HEAD').stdout.strip()
    _answers(monkeypatch, default='n')
    _apply(root, argv=())
    capsys.readouterr()
    assert _git(root, 'rev-parse', 'HEAD').stdout.strip() == head


# --- the line sync_status prints ---------------------------------------------

def test_pending_is_true_for_a_project_that_has_not_updated(tmp_path):
    root = _project(tmp_path, V095)
    assert status_module._update_pending(root) is True


def test_pending_is_false_once_the_update_has_run(tmp_path):
    root = _project(tmp_path, V095)
    _apply(root)
    assert status_module._update_pending(root) is False


def test_status_says_run_the_update_while_something_is_pending(tmp_path):
    root = _project(tmp_path, V010)
    assert 'Run: purlin:init --update' in status_module.sync_status(root)


def test_status_says_it_even_when_the_config_is_already_clean(tmp_path):
    """The line must come from the pending list, not only from a config warning."""
    root = _project(tmp_path, V010)
    _apply(root)
    os.remove(os.path.join(root, '.purlin', 'records', 'README.md'))
    assert update.pending(root)
    assert 'Run: purlin:init --update' in status_module.sync_status(root)


def test_status_stops_saying_it_once_nothing_is_pending(tmp_path):
    root = _project(tmp_path, V010)
    _apply(root)
    assert 'Run: purlin:init --update' not in status_module.sync_status(root)


# --- the copy the update prints ----------------------------------------------

def test_what_the_update_prints_carries_no_emoji(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root)
    printed = capsys.readouterr().out
    for char in printed:
        assert ord(char) < 0x2190 or char in '→─', repr(char)


def test_the_run_ends_by_naming_the_next_step(tmp_path, capsys):
    root = _project(tmp_path, V095)
    _apply(root)
    printed = capsys.readouterr().out.rstrip().splitlines()
    assert printed[-1].startswith('→ Next: run purlin:status')


def test_a_run_that_leaves_work_names_it(tmp_path, capsys, monkeypatch):
    root = _project(tmp_path, V095)
    _answers(monkeypatch, [('Apply records', 'n')])
    _apply(root, argv=())
    printed = capsys.readouterr().out.rstrip().splitlines()
    assert printed[-1] == ('→ Next: run purlin:init --update again for '
                           'records.')
