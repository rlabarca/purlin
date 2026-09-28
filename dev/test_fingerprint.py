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

from purlin import fingerprint  # noqa: E402

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


LOGIN_TEST = ('import pytest\n\n'
              '# purlin: login PROOF-1\n'
              'def test_login():\n    assert True\n')


@pytest.fixture
def project(tmp_path):
    p = Project(tmp_path)
    p.write('specs/auth/login.md', _spec(
        'login', ['Valid credentials return 200'],
        ['POST /login; verify 200'], scope='src/login.py'))
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


# purlin: evidence PROOF-1
def test_a_fingerprint_is_three_hashes_read_from_the_working_tree(project):
    first = project.fp('login')
    assert sorted(first) == ['code', 'spec', 'tests']
    for value in first.values():
        assert len(value) == 64 and all(c in '0123456789abcdef' for c in value)
    project.write('src/login.py', 'def login():\n    return 401\n')
    assert _changed(first, project.fp('login')) == ['code']


# purlin: evidence PROOF-2
def test_a_rule_edit_changes_spec_and_a_description_edit_changes_nothing(
        project):
    first = project.fp('login')
    original = _spec('login', ['Valid credentials return 200'],
                     ['POST /login; verify 200'], scope='src/login.py')
    project.write('specs/auth/login.md', original.replace(
        'Valid credentials return 200', 'Valid credentials return 201'))
    assert _changed(first, project.fp('login')) == ['spec']
    project.write('specs/auth/login.md', original.replace(
        'What it does.', 'Something else entirely.'))
    assert project.fp('login') == first


# purlin: evidence PROOF-3
def test_a_required_proof_and_a_proof_tag_are_part_of_spec(project):
    project.write('specs/auth/login.md', _spec(
        'login', ['Valid credentials return 200'],
        ['POST /login; verify 200'], scope='src/login.py', requires='api'))
    project.write('specs/_anchors/api.md', _spec(
        'api', ['Responses carry a request id'], ['GET /x; verify the header'],
        anchor=True))
    first = project.fp('login')
    project.write('specs/_anchors/api.md', _spec(
        'api', ['Responses carry a request id'], ['GET /y; verify the header'],
        anchor=True))
    second = project.fp('login')
    assert _changed(first, second) == ['spec']
    project.write('specs/auth/login.md', _spec(
        'login', ['Valid credentials return 200'],
        ['POST /login; verify 200 @manual'], scope='src/login.py',
        requires='api'))
    assert _changed(second, project.fp('login')) == ['spec']


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


# purlin: evidence PROOF-5
def test_a_global_anchor_rule_edit_reaches_a_feature_that_does_not_name_it(
        project):
    project.write('specs/_anchors/security.md', _spec(
        'security', ['No eval anywhere'], ['Grep for eval(; verify 0'],
        anchor=True, is_global=True))
    first = project.fp('login')
    project.write('specs/_anchors/security.md', _spec(
        'security', ['No exec anywhere'], ['Grep for eval(; verify 0'],
        anchor=True, is_global=True))
    assert _changed(first, project.fp('login')) == ['spec']


# purlin: evidence PROOF-6
def test_a_scoped_file_edit_changes_code_only(project):
    first = project.fp('login')
    project.write('src/login.py', 'def login():\n    return 204\n')
    second = project.fp('login')
    assert _changed(first, second) == ['code']
    project.write('src/other.py', 'x = 2\n')
    assert project.fp('login') == second


# purlin: evidence PROOF-7
def test_a_scoped_directory_reaches_every_tracked_file_under_it(project):
    project.write('specs/auth/login.md', _spec(
        'login', ['Valid credentials return 200'],
        ['POST /login; verify 200'], scope='src'))
    project.write('src/deep/token.py', 'TOKEN = 1\n')
    project.commit()
    first = project.fp('login')
    project.write('src/deep/token.py', 'TOKEN = 2\n')
    assert _changed(first, project.fp('login')) == ['code']


# purlin: evidence PROOF-8
def test_a_glob_scope_changes_when_a_matching_file_changes(tmp_path):
    p = Project(tmp_path)
    p.write('specs/auth/login.md', _spec('login', ['Login works'],
                                         ['POST; verify'],
                                         scope='src/**/*.py'))
    p.write('src/login.py', 'a = 1\n')
    p.write('src/deep/token.py', 'b = 1\n')
    p.write('src/notes.txt', 'notes\n')
    p.commit()
    report = fingerprint.scope_report(p.root, 'login')
    assert report['files'] == ['src/deep/token.py', 'src/login.py']
    first = p.fp('login')
    p.write('src/deep/token.py', 'b = 2\n')
    second = p.fp('login')
    assert _changed(first, second) == ['code']
    p.write('src/notes.txt', 'other notes\n')
    assert p.fp('login') == second


# purlin: evidence PROOF-9
def test_a_scope_entry_that_reaches_nothing_is_listed_as_unmatched(project):
    project.write('specs/auth/login.md', _spec(
        'login', ['Valid credentials return 200'],
        ['POST /login; verify 200'],
        scope='src/login.py, src/gone.py, lib/*.rs'))
    report = fingerprint.scope_report(project.root, 'login')
    assert report['unmatched'] == ['src/gone.py', 'lib/*.rs']
    assert report['files'] == ['src/login.py']
    assert report['names_no_files'] is False
    assert len(project.fp('login')['code']) == 64


# purlin: evidence PROOF-10
def test_a_spec_with_no_scope_names_no_files(project):
    project.write('specs/auth/login.md', _spec(
        'login', ['Valid credentials return 200'],
        ['POST /login; verify 200']))
    report = fingerprint.scope_report(project.root, 'login')
    assert report['names_no_files'] is True
    assert report['scope'] == [] and report['files'] == []
    fp = project.fp('login')
    assert fp['code'] == EMPTY
    assert len(fp['spec']) == 64 and len(fp['tests']) == 64


# purlin: evidence PROOF-11
def test_a_marked_test_edit_changes_tests_only(project):
    project.write('tests/test_other.py',
                  '# purlin: billing PROOF-1\n'
                  'def test_bill():\n    pass\n')
    project.commit()
    assert fingerprint.marker_files(project.root, 'login') == [
        'tests/test_login.py']
    first = project.fp('login')
    project.write('tests/test_login.py', LOGIN_TEST + '\n# edited\n')
    second = project.fp('login')
    assert _changed(first, second) == ['tests']
    project.write('tests/test_other.py', '# rewritten\n')
    assert project.fp('login') == second


# purlin: evidence PROOF-12
def test_markers_of_every_framework_are_read_outside_skipped_folders(project):
    marked = '// purlin: login PROOF-2\nit("works", () => {});\n'
    project.write('web/login.test.js', marked)
    project.write('node_modules/pkg/login.test.js', marked)
    project.git('add', '-f', 'web', 'node_modules')
    project.git('commit', '-q', '-m', 'test: fixture')
    files = fingerprint.marker_files(project.root, 'login')
    assert 'web/login.test.js' in files
    assert not [path for path in files if path.startswith('node_modules/')]


# purlin: evidence PROOF-13
def test_an_untracked_file_is_reported_and_left_out(project):
    project.write('specs/auth/login.md', _spec(
        'login', ['Valid credentials return 200'],
        ['POST /login; verify 200'], scope='src'))
    project.write('.gitignore', 'src/*.log\n')
    project.commit()
    first = project.fp('login')
    project.write('src/new_token.py', 'NEW = 1\n')
    project.write('tests/helper.py', 'HELP = 1\n')
    project.write('src/debug.log', 'noise\n')
    assert project.fp('login') == first
    assert fingerprint.untracked(project.root, 'login') == [
        'src/new_token.py', 'tests/helper.py']


# purlin: evidence PROOF-14
def test_an_added_file_joins_the_fingerprint(project):
    project.write('specs/auth/login.md', _spec(
        'login', ['Valid credentials return 200'],
        ['POST /login; verify 200'], scope='src'))
    project.commit()
    first = project.fp('login')
    project.write('src/new_token.py', 'NEW = 1\n')
    assert 'src/new_token.py' in fingerprint.untracked(project.root, 'login')
    project.git('add', 'src/new_token.py')
    assert _changed(first, project.fp('login')) == ['code']
    assert fingerprint.untracked(project.root, 'login') == []


# purlin: evidence PROOF-15
def test_a_name_no_spec_defines_raises(project):
    with pytest.raises(KeyError) as caught:
        project.fp('nosuch')
    assert 'nosuch' in str(caught.value)


# purlin: evidence PROOF-16
def test_the_compare_names_the_parts_that_differ_in_order():
    now = {'spec': 'a', 'code': 'x', 'tests': 'y'}
    assert fingerprint.differing_parts(
        {'spec': 'a', 'code': 'b', 'tests': 'c'}, now) == ['code', 'tests']
    assert fingerprint.differing_parts(None, now) == ['spec', 'code', 'tests']
    assert fingerprint.differing_parts('abc', now) == ['spec', 'code', 'tests']
    assert fingerprint.differing_parts(dict(now), now) == []
