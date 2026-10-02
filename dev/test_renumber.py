"""Tests for the renumbering helper (specs/spec/renumber.md).

Every test builds real git repositories in a temporary directory: a host is a
repository on disk that a checkout clones, and a merge that writes a number
twice is made for real, stopped on its conflict and resolved by hand, or left
as git stopped it for the helper to resolve.
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


def _renumber(root, *args, answer=''):
    """`(exit code, the lines printed)` for one run of the helper, `answer`
    being all there is on its input."""
    result = subprocess.run(
        [sys.executable, SCRIPT, 'login', '--project-root', root] + list(args),
        capture_output=True, text=True, input=answer)
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
# A merge left as git stopped it
# ---------------------------------------------------------------------------

ABOUT = '> Description: Signing a person in.'
EIGHT = [1, 2, 3, 4, 5, 8]
EIGHT_RULES = ['RULE-%d: Rule %d' % (n, n) for n in EIGHT]
EIGHT_PROOFS = ['PROOF-%d (RULE-%d): Proof %d' % (n, n, n) for n in EIGHT]


def _login(rules, proofs, highest=(8, 8), about=ABOUT, wrap=0):
    """`login`'s text under a description: with `wrap` 0 and both
    `> Highest-` lines, `> Highest-Proof:` is line 6 and the first rule line
    10. `highest` None leaves both lines out."""
    lines = ['# Feature: login', '', about]
    lines += ['>   and what follows a wrong password.'] * wrap
    lines += ['> Scope: src/login.py']
    if highest:
        lines += ['> Highest-Rule: %d' % highest[0],
                  '> Highest-Proof: %d' % highest[1]]
    lines += ['', '## Rules', '']
    lines += ['- %s' % line for line in rules]
    lines += ['', '## Proof', '']
    lines += ['- %s' % line for line in proofs]
    return '\n'.join(lines) + '\n'


def _stopped(tmp_path, base, on_main, on_branch):
    """A checkout on `main` whose merge of `qa/login` stopped on a conflict
    in `login` and is left there. `main` holds `on_main`, pulled from the host
    it was cloned from, and `qa/login` holds `on_branch`, both made from
    `base`."""
    host = _repo(str(tmp_path / 'host'), {SPEC: base})
    checkout = _clone(host, str(tmp_path / 'checkout'))
    _git(['checkout', '-q', '-b', 'qa/login'], checkout)
    _commit(checkout, {SPEC: on_branch})
    _commit(host, {SPEC: on_main})
    _git(['checkout', '-q', 'main'], checkout)
    _git(['pull', '-q', '--no-edit'], checkout)
    stopped = _git(['merge', '--no-edit', 'qa/login'], checkout, check=False)
    assert stopped.returncode != 0 and 'CONFLICT' in stopped.stdout, stopped
    return checkout


def _collided(tmp_path):
    """The merge of the real-skills check: `main` adds `RULE-9`, `A`, with
    `PROOF-9`; `qa/login` adds `RULE-9`, `B`, with `PROOF-10`, and `PROOF-9`
    for `RULE-3`. Git stops on three conflicts: `> Highest-Proof:` at line
    6, the rule lines at line 20 and the proof lines at line 34."""
    return _stopped(
        tmp_path, _login(EIGHT_RULES, EIGHT_PROOFS),
        _login(EIGHT_RULES + ['RULE-9: A'],
               EIGHT_PROOFS + ['PROOF-9 (RULE-9): A proof'], (9, 9)),
        _login(EIGHT_RULES + ['RULE-9: B'],
               EIGHT_PROOFS + ['PROOF-9 (RULE-3): A boundary',
                               'PROOF-10 (RULE-9): B proof'], (9, 10)))


def _conflict_lines(root):
    return [line for line in _read(root, SPEC).decode('utf-8').splitlines()
            if line.startswith(('<<<<<<<', '=======', '>>>>>>>', '|||||||'))]


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
        _renumber(root, '--yes')
        assert _read(root, 'tests/test_b.py').startswith(
            b'# purlin: login PROOF-5\n')

    # purlin: renumber PROOF-6
    def test_a_comment_written_for_the_kept_line_stays(self, tmp_path):
        root = _merged_twice(tmp_path)
        _code, lines = _renumber(root, '--dry-run')
        assert not [line for line in lines if 'test_a.py' in line], lines
        _renumber(root, '--yes')
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
        _renumber(root, '--yes')
        assert _read(root, 'tests/test_new.py').startswith(
            b'# purlin: login PROOF-4\n')

    # purlin: renumber PROOF-8
    def test_a_test_marked_while_proof_4_read_a_moves_to_proof_6_where_a_is_now(
            self, tmp_path):
        # The test is committed while PROOF-4 reads `A`, and is not changed
        # again; a later commit rewords PROOF-4 to `B` and writes `A` under
        # PROOF-6.
        root = _repo(str(tmp_path / 'proj'), {
            SPEC: _spec([RULE], [ONE, 'PROOF-4 (RULE-1): A'], 1, 4),
            'tests/test_login.py': _marker('PROOF-4')})
        _commit(root, {SPEC: _spec([RULE], [
            ONE, 'PROOF-4 (RULE-1): B', 'PROOF-6 (RULE-1): A'], 1, 6)},
            'spec(login): PROOF-4 reworded, its old wording now PROOF-6')
        _code, lines = _renumber(root, '--dry-run')
        assert lines[0] == ('tests/test_login.py:1 names login PROOF-4 and '
                            'moves to PROOF-6, where its old wording is now.'), \
            lines
        _renumber(root, '--yes')
        assert _read(root, 'tests/test_login.py').startswith(
            b'# purlin: login PROOF-6\n')


class TestTheRest:

    # purlin: renumber PROOF-9
    def test_the_highest_line_is_raised(self, tmp_path):
        root = _merged_twice(tmp_path)
        _code, lines = _renumber(root, '--dry-run')
        assert 'login: > Highest-Proof: 4 becomes 5.' in lines, lines
        _renumber(root, '--yes')
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
        _renumber(root, '--yes')
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
        _renumber(checkout, '--yes')
        text = _read(checkout, SPEC).decode('utf-8')
        assert '- PROOF-2 (RULE-2): Main proof\n' in text
        assert '- PROOF-3 (RULE-3): Branch proof\n' in text

    # purlin: renumber PROOF-12
    def test_a_run_with_yes_makes_the_edits_and_commits_nothing(self, tmp_path):
        root = _merged_twice(tmp_path)
        head = _sha(root)
        code, lines = _renumber(root, '--yes')
        assert code == 0
        assert lines[-1] == ('Renumbered in login: 1 spec line and 1 test '
                             'comment. Nothing is committed.'), lines
        assert _sha(root) == head
        status = _git(['status', '--porcelain'], root).stdout.splitlines()
        assert sorted(status) == [' M specs/auth/login.md',
                                  ' M tests/test_b.py'], status


class TestAsking:

    # purlin: renumber PROOF-15
    def test_a_run_with_nothing_to_answer_from_changes_nothing(self, tmp_path):
        root = _merged_twice(tmp_path)
        before = _files(root)
        code, lines = _renumber(root)
        assert code == 0
        assert lines[0] == 'login: PROOF-4 at line 13 becomes PROOF-5: "B".', \
            lines
        assert lines[-2:] == ['Do it? [y/N] ', 'Nothing is changed.'], lines
        assert _files(root) == before

    # purlin: renumber PROOF-16
    def test_a_run_answered_y_renumbers(self, tmp_path):
        root = _merged_twice(tmp_path)
        code, lines = _renumber(root, answer='y\n')
        assert code == 0
        assert lines[-1] == ('Renumbered in login: 1 spec line and 1 test '
                             'comment. Nothing is committed.'), lines
        assert b'- PROOF-5 (RULE-1): B\n' in _read(root, SPEC)


class TestConflicts:

    # purlin: renumber PROOF-17
    def test_a_conflict_of_two_added_rules_keeps_both(self, tmp_path):
        root = _collided(tmp_path)
        assert _read(root, SPEC).decode('utf-8').splitlines()[19] == \
            '<<<<<<< HEAD'
        _code, lines = _renumber(root, '--dry-run')
        assert ('login: the conflict at line 20 keeps both sides: 1 line from '
                'HEAD and 1 from qa/login.') in lines, lines
        code, lines = _renumber(root, '--yes')
        assert code == 0, lines
        text = _read(root, SPEC).decode('utf-8')
        assert _conflict_lines(root) == []
        assert '- RULE-9: A\n' in text and '- RULE-10: B\n' in text, text

    # purlin: renumber PROOF-18
    def test_a_conflict_of_two_highest_lines_takes_the_higher(self, tmp_path):
        root = _collided(tmp_path)
        before = _read(root, SPEC).decode('utf-8').splitlines()
        assert before[5:10] == ['<<<<<<< HEAD', '> Highest-Proof: 9', '=======',
                                '> Highest-Proof: 10', '>>>>>>> qa/login']
        _code, lines = _renumber(root, '--dry-run')
        assert ('login: the conflict at line 6 takes > Highest-Proof: 10, the '
                'higher of 9 and 10.') in lines, lines
        _renumber(root, '--yes')
        after = _read(root, SPEC).decode('utf-8').splitlines()
        assert len([line for line in after
                    if line.startswith('> Highest-Proof:')]) == 1, after

    # purlin: renumber PROOF-19
    def test_one_conflict_resolved_and_nothing_renumbered(self, tmp_path):
        root = _stopped(
            tmp_path, _login(EIGHT_RULES, EIGHT_PROOFS, None),
            _login(EIGHT_RULES, EIGHT_PROOFS + ['PROOF-9 (RULE-1): Main'],
                   None),
            _login(EIGHT_RULES, EIGHT_PROOFS + ['PROOF-10 (RULE-2): Branch'],
                   None))
        code, lines = _renumber(root, '--yes')
        assert code == 0
        assert lines[-1] == ('Resolved 1 conflict in login. Nothing is '
                             'committed.'), lines
        text = _read(root, SPEC).decode('utf-8')
        assert '- PROOF-9 (RULE-1): Main\n' in text
        assert '- PROOF-10 (RULE-2): Branch\n' in text
        assert _conflict_lines(root) == []
        assert _git(['status', '--porcelain'], root).stdout.splitlines() == [
            'UU specs/auth/login.md']

    # purlin: renumber PROOF-20
    def test_a_line_both_sides_changed_is_left(self, tmp_path):
        rules = ['RULE-1: Rule 1', 'RULE-2: Rule 2']
        proofs = ['PROOF-1 (RULE-1): Proof 1', 'PROOF-2 (RULE-2): Proof 2']
        root = _stopped(
            tmp_path, _login(rules, proofs, (2, 2), wrap=7),
            _login([rules[0], 'RULE-2: A2'], proofs, (2, 2), wrap=7),
            _login([rules[0], 'RULE-2: B2'], proofs, (2, 2), wrap=7))
        before = _read(root, SPEC)
        assert before.decode('utf-8').splitlines()[17:22] == [
            '<<<<<<< HEAD', '- RULE-2: A2', '=======', '- RULE-2: B2',
            '>>>>>>> qa/login']
        _code, lines = _renumber(root, '--dry-run')
        assert ('login: the conflict at line 18 is left: both sides changed '
                'RULE-2. Resolve it by hand, then run purlin:spec login '
                'again.') in lines, lines
        code, _lines = _renumber(root, '--yes')
        assert code == 0
        assert _read(root, SPEC).decode('utf-8').splitlines()[17:22] == \
            before.decode('utf-8').splitlines()[17:22]

    # purlin: renumber PROOF-21
    def test_a_conflict_holding_another_kind_of_line_is_left(self, tmp_path):
        root = _stopped(
            tmp_path, _login(EIGHT_RULES, EIGHT_PROOFS),
            _login(EIGHT_RULES, EIGHT_PROOFS,
                   about='> Description: Signing in, for product.'),
            _login(EIGHT_RULES, EIGHT_PROOFS,
                   about='> Description: Signing in, for QA.'))
        assert _read(root, SPEC).decode('utf-8').splitlines()[2] == \
            '<<<<<<< HEAD'
        _code, lines = _renumber(root, '--dry-run')
        assert ('login: the conflict at line 3 is left: it holds a line that '
                'is not a rule, a proof or a > Highest- line. Resolve it by '
                'hand, then run purlin:spec login again.') in lines, lines
