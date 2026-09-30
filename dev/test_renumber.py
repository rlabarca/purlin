"""Tests for the renumbering helper (specs/spec/renumber.md).

Every test builds real git repositories in a temporary directory: a host is a
repository on disk that a checkout clones, and a merge that writes a number
twice is made for real, stopped on its conflict and resolved by hand.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, 'scripts', 'spec', 'renumber.py')

DRY_RUN = 'Nothing is changed: this is a dry run.'
TESTS = [{'name': 'pytest', 'run': 'pytest {files}', 'report': None,
          'format': 'junit', 'files': ['tests/test_*.py']}]


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

def _git(args, cwd, check=True):
    return subprocess.run(['git'] + args, cwd=cwd, capture_output=True,
                          text=True, check=check)


def _sha(cwd, ref='HEAD'):
    return _git(['rev-parse', ref], cwd).stdout.strip()


def _write(root, path, text):
    full = os.path.join(root, *path.split('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8', newline='') as handle:
        handle.write(text)


def _read(root, path):
    with open(os.path.join(root, *path.split('/')), 'rb') as handle:
        return handle.read()


def _identity(root):
    for key, value in (('user.email', 'test@test.com'), ('user.name', 'Test'),
                       ('pull.rebase', 'false'), ('commit.gpgsign', 'false')):
        _git(['config', key, value], root)


def _commit(root, files, message='feat: change'):
    for path, text in files.items():
        _write(root, path, text)
    _git(['add', '-A'], root)
    _git(['commit', '-q', '-m', message], root)
    return _sha(root)


def _repo(root, files):
    os.makedirs(root, exist_ok=True)
    _write(root, '.purlin/config.json', json.dumps({'tests': TESTS}))
    _git(['-c', 'init.defaultBranch=main', 'init', '-q'], root)
    _identity(root)
    _commit(root, files, 'chore: start')
    return root


def _clone(source, root):
    _git(['clone', '-q', source, root], os.path.dirname(root))
    _identity(root)
    return root


def _spec(rules, proofs, highest_rule, highest_proof):
    """`login`'s text: `rules` and `proofs` are lists of whole lines."""
    lines = ['# Feature: login', '',
             '> Highest-Rule: %d' % highest_rule,
             '> Highest-Proof: %d' % highest_proof, '', '## Rules', '']
    lines += ['- %s' % line for line in rules]
    lines += ['', '## Proof', '']
    lines += ['- %s' % line for line in proofs]
    return '\n'.join(lines) + '\n'


SPEC = 'specs/auth/login.md'
RULE = 'RULE-1: Signs a person in'
ONE = 'PROOF-1 (RULE-1): One'


def _marker(proof):
    return '# purlin: login %s\ndef test_it():\n    pass\n' % proof


def _merge(checkout, resolved):
    """Pull `origin/main` into `checkout`, stop on the conflict, write
    `resolved` over the spec and commit the merge."""
    stopped = _git(['pull', '-q', '--no-edit'], checkout, check=False)
    assert stopped.returncode != 0, stopped
    _write(checkout, SPEC, resolved)
    _git(['add', '-A'], checkout)
    _git(['commit', '-q', '--no-edit'], checkout)


def _merged_twice(tmp_path):
    """A checkout whose merge left `login` writing `PROOF-4` twice: its own
    `B` on line 13 above `origin/main`'s `A` on line 14. `tests/test_b.py`
    names `PROOF-4` from the branch, `tests/test_a.py` from `origin/main`,
    and the host's `qa/age-proofs` adds `tests/test_qa.py` naming it too."""
    host = _repo(str(tmp_path / 'host'),
                 {SPEC: _spec([RULE], [ONE], 1, 1)})
    checkout = _clone(host, str(tmp_path / 'checkout'))
    _commit(host, {SPEC: _spec([RULE], [ONE, 'PROOF-4 (RULE-1): A'], 1, 4),
                   'tests/test_a.py': _marker('PROOF-4')})
    _git(['checkout', '-q', '-b', 'qa/age-proofs'], host)
    _commit(host, {'tests/test_qa.py': _marker('PROOF-4')})
    _git(['checkout', '-q', 'main'], host)
    _commit(checkout, {SPEC: _spec([RULE], [ONE, 'PROOF-4 (RULE-1): B'], 1, 4),
                       'tests/test_b.py': _marker('PROOF-4')})
    _merge(checkout, _spec([RULE], [ONE, 'PROOF-4 (RULE-1): B',
                                     'PROOF-4 (RULE-1): A'], 1, 4))
    return checkout


def _renumber(root, *args):
    """`(exit code, the lines printed)` for one run of the helper."""
    result = subprocess.run(
        [sys.executable, SCRIPT, 'login', '--project-root', root] + list(args),
        capture_output=True, text=True)
    return result.returncode, result.stdout.splitlines()


def _files(root):
    """`{path: bytes}` for every file outside `.git`."""
    found = {}
    for folder, dirs, names in os.walk(root):
        dirs[:] = [name for name in dirs if name != '.git']
        for name in names:
            path = os.path.relpath(os.path.join(folder, name), root)
            found[path] = _read(root, path.replace(os.sep, '/'))
    return found


# ---------------------------------------------------------------------------
# The tests
# ---------------------------------------------------------------------------

class TestPlan:

    # purlin: renumber PROOF-1
    def test_a_dry_run_changes_nothing(self, tmp_path):
        root = _merged_twice(tmp_path)
        before = _files(root)
        code, lines = _renumber(root, '--dry-run')
        assert code == 0
        assert len(lines) > 1 and lines[-1] == DRY_RUN, lines
        assert _files(root) == before

    # purlin: renumber PROOF-2
    def test_the_line_not_on_the_default_branch_moves(self, tmp_path):
        _code, lines = _renumber(_merged_twice(tmp_path), '--dry-run')
        assert lines[0] == 'login: PROOF-4 at line 13 becomes PROOF-5: "B".', \
            lines

    # purlin: renumber PROOF-3
    def test_neither_line_on_the_default_branch(self, tmp_path):
        host = _repo(str(tmp_path / 'host'), {SPEC: _spec([RULE], [ONE], 1, 1)})
        checkout = _clone(host, str(tmp_path / 'checkout'))
        _commit(checkout, {SPEC: _spec([RULE], [
            ONE, 'PROOF-7 (RULE-1): X', 'PROOF-7 (RULE-1): Y'], 1, 7)})
        _code, lines = _renumber(checkout, '--dry-run')
        assert lines[0] == (
            'login: PROOF-7 at line 14 becomes PROOF-8: "Y". Neither line is '
            'on origin/main, so the later one moves.'), lines

    # purlin: renumber PROOF-4
    def test_no_default_branch(self, tmp_path):
        root = _repo(str(tmp_path / 'proj'), {SPEC: _spec([RULE], [
            ONE, 'PROOF-4 (RULE-1): A', 'PROOF-4 (RULE-1): B'], 1, 4)})
        _code, lines = _renumber(root, '--dry-run')
        assert lines[0] == (
            'login: PROOF-4 at line 14 becomes PROOF-5: "B". This checkout has '
            'no copy of a default branch, so the later one moves.'), lines


class TestComments:

    # purlin: renumber PROOF-5
    def test_a_comment_written_for_the_moving_line_moves(self, tmp_path):
        root = _merged_twice(tmp_path)
        _code, lines = _renumber(root, '--dry-run')
        assert 'tests/test_b.py:1 names login PROOF-4 and moves to PROOF-5.' \
            in lines, lines
        _renumber(root)
        assert _read(root, 'tests/test_b.py').startswith(
            b'# purlin: login PROOF-5\n')

    # purlin: renumber PROOF-6
    def test_a_comment_written_for_the_kept_line_stays(self, tmp_path):
        root = _merged_twice(tmp_path)
        _code, lines = _renumber(root, '--dry-run')
        assert not [line for line in lines if 'test_a.py' in line], lines
        _renumber(root)
        assert _read(root, 'tests/test_a.py').startswith(
            b'# purlin: login PROOF-4\n')

    # purlin: renumber PROOF-7
    def test_an_uncommitted_comment_is_named_not_changed(self, tmp_path):
        root = _merged_twice(tmp_path)
        _write(root, 'tests/test_new.py', _marker('PROOF-4'))
        _code, lines = _renumber(root, '--dry-run')
        assert ('tests/test_new.py:1 names login PROOF-4 and is not committed, '
                'so it is not changed: check which proof it means.') in lines, \
            lines
        _renumber(root)
        assert _read(root, 'tests/test_new.py').startswith(
            b'# purlin: login PROOF-4\n')

    # purlin: renumber PROOF-8
    def test_a_comment_follows_its_old_wording(self, tmp_path):
        root = _repo(str(tmp_path / 'proj'), {
            SPEC: _spec([RULE], [ONE, 'PROOF-4 (RULE-1): A'], 1, 4),
            'tests/test_login.py': _marker('PROOF-4')})
        _commit(root, {SPEC: _spec([RULE], [
            ONE, 'PROOF-4 (RULE-1): B', 'PROOF-6 (RULE-1): A'], 1, 6)})
        _code, lines = _renumber(root, '--dry-run')
        assert lines[0] == ('tests/test_login.py:1 names login PROOF-4 and '
                            'moves to PROOF-6, where its old wording is now.'), \
            lines
        _renumber(root)
        assert _read(root, 'tests/test_login.py').startswith(
            b'# purlin: login PROOF-6\n')


class TestTheRest:

    # purlin: renumber PROOF-9
    def test_the_highest_line_is_raised(self, tmp_path):
        root = _merged_twice(tmp_path)
        _code, lines = _renumber(root, '--dry-run')
        assert 'login: > Highest-Proof: 4 becomes 5.' in lines, lines
        _renumber(root)
        assert b'\n> Highest-Proof: 5\n' in _read(root, SPEC)

    # purlin: renumber PROOF-10
    def test_a_comment_on_another_branch_is_named(self, tmp_path):
        root = _merged_twice(tmp_path)
        before = _sha(root, 'refs/remotes/origin/qa/age-proofs')
        _code, lines = _renumber(root, '--dry-run')
        assert (
            'origin/qa/age-proofs names login PROOF-4 at tests/test_qa.py:1, '
            'which this checkout does not change. If it means the line that '
            'moves, move it to PROOF-5 on that branch.') in lines, lines
        assert [line for line in lines if 'names login' in line
                and 'which this checkout' in line] == [
            line for line in lines if line.startswith('origin/qa/age-proofs')]
        _renumber(root)
        assert _sha(root, 'refs/remotes/origin/qa/age-proofs') == before

    # purlin: renumber PROOF-11
    def test_a_moved_rule_takes_its_new_proofs(self, tmp_path):
        host = _repo(str(tmp_path / 'host'), {SPEC: _spec([RULE], [ONE], 1, 1)})
        checkout = _clone(host, str(tmp_path / 'checkout'))
        _commit(host, {SPEC: _spec([RULE, 'RULE-2: Main'], [
            ONE, 'PROOF-2 (RULE-2): Main proof'], 2, 2)})
        _commit(checkout, {SPEC: _spec([RULE, 'RULE-2: Branch'], [
            ONE, 'PROOF-3 (RULE-2): Branch proof'], 2, 3)})
        _merge(checkout, _spec(
            [RULE, 'RULE-2: Branch', 'RULE-2: Main'],
            [ONE, 'PROOF-2 (RULE-2): Main proof',
             'PROOF-3 (RULE-2): Branch proof'], 2, 3))
        _code, lines = _renumber(checkout, '--dry-run')
        assert 'login: PROOF-3 at line 16 now names RULE-3.' in lines, lines
        assert not [line for line in lines if 'PROOF-2' in line], lines
        _renumber(checkout)
        text = _read(checkout, SPEC).decode('utf-8')
        assert '- PROOF-2 (RULE-2): Main proof\n' in text
        assert '- PROOF-3 (RULE-3): Branch proof\n' in text

    # purlin: renumber PROOF-12
    def test_a_run_makes_the_edits_and_commits_nothing(self, tmp_path):
        root = _merged_twice(tmp_path)
        head = _sha(root)
        code, lines = _renumber(root)
        assert code == 0
        assert lines[-1] == ('Renumbered in login: 1 spec line and 1 test '
                             'comment. Nothing is committed.'), lines
        assert _sha(root) == head
        status = _git(['status', '--porcelain'], root).stdout.splitlines()
        assert sorted(status) == [' M specs/auth/login.md',
                                  ' M tests/test_b.py'], status
