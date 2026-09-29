"""Tests for `scripts/mcp/purlin/fingerprint.py`.

Every test builds a real git repository in a temporary directory, writes the
specs, the code and the tests it needs, and takes fingerprints over it. Nothing
in the module under test is replaced.
"""

import hashlib
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))

from purlin import fingerprint, specs  # noqa: E402

EMPTY = hashlib.sha256(b'').hexdigest()


def _spec(name, rules, proofs, scope=None, requires=None, anchor=False,
          is_global=False, description='What it does.'):
    lines = ['# %s: %s' % ('Anchor' if anchor else 'Feature', name), '',
             '> Description: %s' % description]
    if requires:
        lines.append('> Requires: %s' % requires)
    if scope is not None:
        lines.append('> Scope: %s' % scope)
    if is_global:
        lines.append('> Global: true')
    lines += ['', '## Rules', '']
    lines += ['- RULE-%d: %s' % (i + 1, text) for i, text in enumerate(rules)]
    lines += ['', '## Proof', '']
    lines += ['- PROOF-%d (RULE-%d): %s' % (i + 1, i + 1, text)
              for i, text in enumerate(proofs)]
    return '\n'.join(lines) + '\n'


class Project(object):
    def __init__(self, root):
        self.root = str(root)
        self.git('init', '-q')
        self.git('config', 'user.email', 'dev@example.com')
        self.git('config', 'user.name', 'Dev')
        self.git('config', 'commit.gpgsign', 'false')

    def git(self, *args):
        result = subprocess.run(['git'] + list(args), cwd=self.root,
                                capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        return result.stdout

    def write(self, rel, text):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'feat: fixture')

    def fp(self, feature):
        return fingerprint.fingerprint(self.root, feature)

    def login(self, scope='src/login.py', **kwargs):
        """Write the `login` spec, with its one rule and proof, over `scope`."""
        self.write('specs/auth/login.md', _login(scope=scope, **kwargs))


LOGIN_RULE = 'Valid credentials return 200'
LOGIN_PROOF = 'POST /login; verify 200'


def _login(scope='src/login.py', rule=LOGIN_RULE, proof=LOGIN_PROOF,
           **kwargs):
    return _spec('login', [rule], [proof], scope=scope, **kwargs)


LOGIN_TEST = ('import pytest\n\n'
              '# purlin: login PROOF-1\n'
              'def test_login():\n    assert True\n')

JS_TEST = '// purlin: login PROOF-2\nit("works", () => {});\n'


@pytest.fixture
def project(tmp_path):
    p = Project(tmp_path)
    p.login()
    p.write('src/login.py', 'def login():\n    return 200\n')
    p.write('src/other.py', 'x = 1\n')
    p.write('tests/test_login.py', LOGIN_TEST)
    p.write('.purlin/config.json', json.dumps({'tests': [
        {'name': 'pytest', 'run': 'pytest {files}', 'report': None,
         'format': 'junit', 'files': ['tests/test_*.py']},
        {'name': 'jest', 'run': 'jest {files}', 'report': None,
         'format': 'junit', 'files': ['**/*.test.js']}]}))
    p.commit()
    return p


def _changed(before, after):
    return [part for part in fingerprint.PARTS if before[part] != after[part]]


# --- RULE-1 -----------------------------------------------------------------

# purlin: evidence PROOF-1
def test_a_fingerprint_is_three_parts_of_64_hex_characters(project):
    first = project.fp('login')
    assert sorted(first) == ['code', 'spec', 'tests']
    for value in first.values():
        assert len(value) == 64 and all(c in '0123456789abcdef' for c in value)


# purlin: evidence PROOF-32
def test_an_edit_not_committed_changes_the_fingerprint(project):
    first = project.fp('login')
    project.write('src/login.py', 'def login():\n    return 401\n')
    assert _changed(first, project.fp('login')) == ['code']


# --- RULE-2 -----------------------------------------------------------------

# purlin: evidence PROOF-2
def test_a_reworded_rule_changes_spec_alone(project):
    first = project.fp('login')
    project.login(rule='Valid credentials return 201')
    assert _changed(first, project.fp('login')) == ['spec']


# purlin: evidence PROOF-33
def test_a_rewritten_description_changes_no_part(project):
    first = project.fp('login')
    project.login(description='Something else entirely.')
    assert project.fp('login') == first


def _requiring_api(project, api_proof):
    project.login(requires='api')
    project.write('specs/_anchors/api.md', _spec(
        'api', ['Responses carry a request id'], [api_proof], anchor=True))


# purlin: evidence PROOF-3
def test_a_changed_proof_of_a_required_anchor_changes_spec_alone(project):
    _requiring_api(project, 'GET /x; verify the header')
    first = project.fp('login')
    _requiring_api(project, 'GET /y; verify the header')
    assert _changed(first, project.fp('login')) == ['spec']


# purlin: evidence PROOF-34
def test_manual_added_to_a_proof_changes_spec_alone(project):
    first = project.fp('login')
    project.login(proof=LOGIN_PROOF + ' @manual')
    assert _changed(first, project.fp('login')) == ['spec']


# --- RULE-3 -----------------------------------------------------------------

# purlin: evidence PROOF-4
def test_an_anchor_rule_edit_reaches_every_feature_that_requires_it(tmp_path):
    p = Project(tmp_path)
    p.write('specs/_anchors/api.md', _spec('api', ['Carry a request id'],
                                           ['GET /x; verify it'], anchor=True))
    p.write('specs/shop/orders.md', _spec('orders', ['Orders list'],
                                          ['GET; verify'], requires='api'))
    p.write('specs/auth/login.md', _spec('login', ['Login works'],
                                         ['POST; verify'], requires='orders'))
    p.write('specs/pay/billing.md', _spec('billing', ['Bills add up'],
                                          ['Sum; verify']))
    p.commit()
    names = ('api', 'orders', 'login', 'billing')
    before = {name: p.fp(name) for name in names}
    p.write('specs/_anchors/api.md', _spec('api', ['Carry a trace id'],
                                           ['GET /x; verify it'], anchor=True))
    after = {name: p.fp(name) for name in names}
    for name in ('api', 'orders', 'login'):
        assert _changed(before[name], after[name]) == ['spec'], name
    assert after['billing'] == before['billing']


def _security(project, rule, is_global):
    project.write('specs/_anchors/security.md', _spec(
        'security', [rule], ['Grep for eval(; verify 0'], anchor=True,
        is_global=is_global))


# purlin: evidence PROOF-5
def test_a_global_anchor_rule_edit_reaches_a_feature_that_does_not_name_it(
        project):
    _security(project, 'No eval anywhere', is_global=True)
    first = project.fp('login')
    _security(project, 'No exec anywhere', is_global=True)
    assert _changed(first, project.fp('login')) == ['spec']


# purlin: evidence PROOF-35
def test_an_anchor_that_is_not_global_leaves_a_feature_that_does_not_name_it(
        project):
    _security(project, 'No eval anywhere', is_global=False)
    first = project.fp('login')
    _security(project, 'No exec anywhere', is_global=False)
    assert project.fp('login') == first


# --- RULE-4 -----------------------------------------------------------------

# purlin: evidence PROOF-6
def test_an_edit_to_a_scoped_file_changes_code_alone(project):
    first = project.fp('login')
    project.write('src/login.py', 'def login():\n    return 204\n')
    assert _changed(first, project.fp('login')) == ['code']


# purlin: evidence PROOF-36
def test_an_edit_to_a_file_outside_the_scope_changes_nothing(project):
    first = project.fp('login')
    project.write('src/other.py', 'x = 2\n')
    assert project.fp('login') == first


# purlin: evidence PROOF-7
def test_a_scoped_folder_reaches_a_tracked_file_one_folder_down(project):
    project.login(scope='src')
    project.write('src/deep/token.py', 'TOKEN = 1\n')
    project.commit()
    first = project.fp('login')
    project.write('src/deep/token.py', 'TOKEN = 2\n')
    assert _changed(first, project.fp('login')) == ['code']


def _globbed(tmp_path, scope):
    """A project whose `login` covers `scope`, over three tracked files."""
    p = Project(tmp_path)
    p.login(scope=scope)
    p.write('src/login.py', 'a = 1\n')
    p.write('src/deep/token.py', 'b = 1\n')
    p.write('src/notes.txt', 'notes\n')
    p.commit()
    return p


def _after_edit(p, rel, text):
    first = p.fp('login')
    p.write(rel, text)
    return _changed(first, p.fp('login'))


# purlin: evidence PROOF-8
def test_a_glob_reaches_a_matching_file_one_folder_down(tmp_path):
    p = _globbed(tmp_path, 'src/**/*.py')
    assert _after_edit(p, 'src/deep/token.py', 'b = 2\n') == ['code']


# purlin: evidence PROOF-37
def test_a_glob_reaches_a_matching_file_directly_in_its_folder(tmp_path):
    p = _globbed(tmp_path, 'src/**/*.py')
    assert _after_edit(p, 'src/login.py', 'a = 2\n') == ['code']


# purlin: evidence PROOF-38
def test_a_glob_does_not_reach_a_file_it_does_not_match(tmp_path):
    p = _globbed(tmp_path, 'src/**/*.py')
    assert _after_edit(p, 'src/notes.txt', 'other notes\n') == []


# purlin: evidence PROOF-39
def test_an_entry_holding_a_question_mark_is_a_glob(tmp_path):
    p = _globbed(tmp_path, 'src/logi?.py')
    assert _after_edit(p, 'src/login.py', 'a = 2\n') == ['code']


# purlin: evidence PROOF-40
def test_an_entry_holding_a_bracket_is_a_glob(tmp_path):
    p = _globbed(tmp_path, 'src/[l]ogin.py')
    assert _after_edit(p, 'src/login.py', 'a = 2\n') == ['code']


# --- RULE-5 -----------------------------------------------------------------

UNMATCHED_SCOPE = 'src/login.py, src/gone.py, lib/*.rs'


# purlin: evidence PROOF-9
def test_entries_that_reach_nothing_are_listed_as_unmatched(project):
    assert fingerprint.expand_scope(
        project.root, ['src/login.py', 'src/gone.py', 'lib/*.rs']) == (
        ['src/login.py'], ['src/gone.py', 'lib/*.rs'])


# purlin: evidence PROOF-41
def test_the_fingerprint_is_taken_over_what_the_other_entries_reach(project):
    alone = project.fp('login')
    project.login(scope=UNMATCHED_SCOPE)
    with_unmatched = project.fp('login')
    assert with_unmatched['code'] == alone['code']
    assert fingerprint.incomplete_reason(project.root, 'login') is None


# purlin: evidence PROOF-42
def test_a_file_git_does_not_track_is_listed_as_unmatched(project):
    project.write('src/draft.py', 'DRAFT = 1\n')
    project.login(scope='src/login.py, src/draft.py')
    own_scope = specs.scan_specs(project.root)['login']['scope']
    assert fingerprint.expand_scope(project.root, own_scope) == (
        ['src/login.py'], ['src/draft.py'])


# --- RULE-6 -----------------------------------------------------------------

# purlin: evidence PROOF-10
def test_a_spec_with_no_scope_is_incomplete_and_its_code_part_is_empty(
        project):
    project.login(scope=None)
    assert fingerprint.incomplete_reason(project.root, 'login') == (
        'no > Scope: line')
    fp = project.fp('login')
    assert fp['code'] == EMPTY == (
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')
    assert len(fp['spec']) == 64 and len(fp['tests']) == 64


# --- RULE-7 -----------------------------------------------------------------

# purlin: evidence PROOF-11
def test_an_edit_to_a_marked_test_file_changes_tests_alone(project):
    first = project.fp('login')
    project.write('tests/test_login.py', LOGIN_TEST + '\n# edited\n')
    assert _changed(first, project.fp('login')) == ['tests']


# purlin: evidence PROOF-43
def test_a_test_file_marked_for_another_feature_is_not_counted(project):
    project.write('tests/test_other.py',
                  '# purlin: billing PROOF-1\n'
                  'def test_bill():\n    pass\n')
    project.commit()
    first = project.fp('login')
    project.write('tests/test_other.py', '# rewritten\n')
    assert project.fp('login') == first


# purlin: evidence PROOF-44
def test_a_marked_file_no_suite_names_is_not_counted(project):
    project.write('scripts/check_login.py', LOGIN_TEST)
    project.commit()
    first = project.fp('login')
    project.write('scripts/check_login.py', LOGIN_TEST + '\n# edited\n')
    assert project.fp('login') == first


# purlin: evidence PROOF-12
def test_a_javascript_marker_is_counted(project):
    project.write('web/login.test.js', JS_TEST)
    project.commit()
    first = project.fp('login')
    project.write('web/login.test.js', JS_TEST + '// edited\n')
    assert _changed(first, project.fp('login')) == ['tests']


SKIPPED = ('node_modules/pkg', 'bin', 'obj', 'mutants', '.cache')


# purlin: evidence PROOF-45
def test_a_marked_file_in_a_skipped_folder_is_not_counted(project):
    copies = ['%s/login.test.js' % folder for folder in SKIPPED]
    for path in copies:
        project.write(path, JS_TEST)
    project.git('add', '-f', *copies)
    project.git('commit', '-q', '-m', 'test: fixture')
    first = project.fp('login')
    for path in copies:
        project.write(path, JS_TEST + '// edited\n')
        assert project.fp('login') == first, path
        project.write(path, JS_TEST)


# --- RULE-8 -----------------------------------------------------------------

@pytest.fixture
def folder_scoped(project):
    """`login` covering the folder `src`, committed."""
    project.login(scope='src')
    project.commit()
    return project


# purlin: evidence PROOF-13
def test_an_untracked_file_changes_no_part(folder_scoped):
    first = folder_scoped.fp('login')
    folder_scoped.write('src/new_token.py', 'NEW = 1\n')
    folder_scoped.write('tests/helper.py', 'HELP = 1\n')
    assert folder_scoped.fp('login') == first


# purlin: evidence PROOF-46
def test_untracked_files_in_the_scope_or_beside_a_marker_file_are_listed(
        folder_scoped):
    folder_scoped.write('src/new_token.py', 'NEW = 1\n')
    folder_scoped.write('tests/helper.py', 'HELP = 1\n')
    folder_scoped.write('docs/notes.md', 'Notes.\n')
    assert fingerprint.untracked(folder_scoped.root, 'login') == [
        'src/new_token.py', 'tests/helper.py']


# purlin: evidence PROOF-47
def test_a_file_git_ignores_is_not_listed(folder_scoped):
    folder_scoped.write('.gitignore', 'src/*.log\n')
    folder_scoped.commit()
    folder_scoped.write('src/debug.log', 'noise\n')
    folder_scoped.write('src/new_token.py', 'NEW = 1\n')
    assert fingerprint.untracked(folder_scoped.root, 'login') == [
        'src/new_token.py']


# purlin: evidence PROOF-14
def test_an_added_file_joins_the_fingerprint(folder_scoped):
    first = folder_scoped.fp('login')
    folder_scoped.write('src/new_token.py', 'NEW = 1\n')
    assert fingerprint.untracked(folder_scoped.root, 'login') == [
        'src/new_token.py']
    folder_scoped.git('add', 'src/new_token.py')
    assert _changed(first, folder_scoped.fp('login')) == ['code']
    assert fingerprint.untracked(folder_scoped.root, 'login') == []


# --- RULE-9 -----------------------------------------------------------------

# purlin: evidence PROOF-15
def test_a_name_no_spec_defines_raises(project):
    with pytest.raises(KeyError) as caught:
        project.fp('nosuch')
    assert 'nosuch' in str(caught.value)


# --- RULE-10 ----------------------------------------------------------------

NOW = {'spec': 'a', 'code': 'x', 'tests': 'y'}


# purlin: evidence PROOF-16
def test_the_parts_that_differ_are_named_in_order():
    assert fingerprint.differing_parts(
        {'spec': 'a', 'code': 'b', 'tests': 'c'}, NOW) == ['code', 'tests']


# purlin: evidence PROOF-48
def test_a_missing_stored_fingerprint_differs_on_all_three():
    assert fingerprint.differing_parts(None, NOW) == ['spec', 'code', 'tests']


# purlin: evidence PROOF-49
def test_a_stored_fingerprint_that_is_text_differs_on_all_three():
    assert fingerprint.differing_parts('abc', NOW) == [
        'spec', 'code', 'tests']


# purlin: evidence PROOF-50
def test_two_equal_fingerprints_differ_on_no_part():
    assert fingerprint.differing_parts(dict(NOW), NOW) == []
