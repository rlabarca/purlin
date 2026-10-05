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


def _spec(name, rules, proofs, scope=None, anchor=False,
          description='What it does.'):
    lines = ['# %s: %s' % ('Anchor' if anchor else 'Feature', name), '',
             '> Description: %s' % description]
    if scope is not None:
        lines.append('> Scope: %s' % scope)
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
        """Write `text` with line feeds alone, on every system."""
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'feat: fixture')

    def check_out_again(self, autocrlf):
        """Check every tracked file out afresh under `core.autocrlf`.

        With `true`, git writes each text file with a carriage return before
        every line feed, as a Windows checkout does.
        """
        self.git('config', 'core.autocrlf', autocrlf)
        for rel in self.git('ls-files', '-z').split('\0'):
            if rel:
                os.remove(os.path.join(self.root, rel))
        self.git('checkout', '--', '.')

    def read_bytes(self, rel):
        with open(os.path.join(self.root, rel), 'rb') as handle:
            return handle.read()

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

def _three_parts(found):
    assert sorted(found) == ['code', 'spec', 'tests']
    for value in found.values():
        assert len(value) == 64 and all(c in '0123456789abcdef' for c in value)


# purlin: evidence PROOF-1
def test_a_fingerprint_is_three_parts_of_64_hex_characters(project):
    _three_parts(project.fp('login'))


# purlin: evidence PROOF-71
def test_a_crlf_checkout_takes_the_code_part_of_the_commit(project):
    project.check_out_again('false')
    assert b'\r' not in project.read_bytes('src/login.py')
    plain = project.fp('login')
    project.check_out_again('true')
    assert b'\r\n' in project.read_bytes('src/login.py')
    converted = project.fp('login')
    _three_parts(converted)
    assert converted['code'] == plain['code']


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


# --- RULE-34 ----------------------------------------------------------------

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
    [selected] = [entry for entry in fingerprint.selection(project.root)
                  if entry['feature'] == 'login']
    assert not [reason for reason in selected['reasons']
                if 'names no files' in reason], selected


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


# --- RULE-30 to RULE-32: an anchor's code part is the project ---------------

SECURITY = _spec('security', ['No eval anywhere'],
                 ['Grep every file for eval(; verify 0'], anchor=True)


@pytest.fixture
def anchored(project):
    """`project` with the anchor `security` and a tracked `docs/guide.md`."""
    project.write('specs/_anchors/security.md', SECURITY)
    project.write('docs/guide.md', 'How to use it.\n')
    project.commit()
    return project


# purlin: evidence PROOF-78
def test_an_edit_to_a_file_no_scope_names_changes_an_anchors_code(anchored):
    first = anchored.fp('security')
    anchored.write('docs/guide.md', 'How to use it, again.\n')
    assert _changed(first, anchored.fp('security')) == ['code']


# purlin: evidence PROOF-79
def test_an_untracked_file_leaves_an_anchor_as_it_was(anchored):
    first = anchored.fp('security')
    anchored.write('docs/draft.md', 'Not added.\n')
    assert anchored.fp('security') == first


def _settings(project, **changed):
    """Rewrite `.purlin/config.json` with `changed` over what it holds."""
    path = os.path.join(project.root, '.purlin', 'config.json')
    with open(path, encoding='utf-8') as handle:
        held = json.load(handle)
    held.update(changed)
    project.write('.purlin/config.json', json.dumps(held))
    return held


# purlin: evidence PROOF-90
def test_a_changed_version_leaves_an_anchor_as_it_was(anchored):
    _settings(anchored, version='0.10.0')
    anchored.commit()
    first = anchored.fp('security')
    _settings(anchored, version='0.10.1')
    assert anchored.fp('security') == first


# purlin: evidence PROOF-91
def test_a_changed_test_command_changes_an_anchors_tests_alone(anchored):
    held = _settings(anchored, version='0.10.0')
    anchored.commit()
    first = anchored.fp('security')
    tests = [dict(held['tests'][0], run='pytest -x {files}')] + held['tests'][1:]
    _settings(anchored, tests=tests)
    assert _changed(first, anchored.fp('security')) == ['tests']


def _record_leaves_the_anchor(project, rel, text):
    first = project.fp('security')
    project.write(rel, text)
    project.git('add', '-f', rel)
    project.git('commit', '-q', '-m', 'chore: a record')
    assert rel in project.git('ls-files', '--', rel)
    assert project.fp('security') == first, rel


# purlin: evidence PROOF-80
def test_a_new_evidence_file_leaves_an_anchor_as_it_was(anchored):
    _record_leaves_the_anchor(anchored, '.purlin/evidence/local/login.json',
                              '{"schema": "purlin-evidence/2"}\n')


# purlin: evidence PROOF-82
def test_a_signoff_file_leaves_an_anchor_as_it_was(anchored):
    _record_leaves_the_anchor(
        anchored, '.purlin/evidence/package/1.0.0.signoffs/jane.json',
        '{"schema": "purlin-signoff/1"}\n')


# purlin: evidence PROOF-83
def test_an_evidence_package_leaves_an_anchor_as_it_was(anchored):
    _record_leaves_the_anchor(anchored, '.purlin/evidence/package/1.0.0.json',
                              '{"version": "1.0.0"}\n')


# purlin: evidence PROOF-84
def test_an_anchors_code_part_is_the_blob_ids_the_commit_holds(anchored):
    anchored.write('.purlin/evidence/local/login.json', '{}\n')
    anchored.commit()
    anchored.check_out_again('true')
    assert b'\r\n' in anchored.read_bytes('docs/guide.md')
    records = ('.purlin/evidence/', '.purlin/config.json')
    held = []
    for line in anchored.git('ls-tree', '-r', 'HEAD').splitlines():
        head, path = line.split('\t', 1)
        if not path.startswith(records):
            held.append('%s %s' % (path, head.split()[2]))
    expected = hashlib.sha256(
        '\n'.join(sorted(held)).encode('utf-8')).hexdigest()
    assert anchored.fp('security')['code'] == expected


