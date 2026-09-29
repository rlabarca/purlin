"""Tests for the drift report (specs/mcp/drift.md).

Every test builds real git repositories in a temporary directory and produces
each action git logs for real: a pull from a second repository, a merge, a
rebase, a checkout, a reset and a clone.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from purlin import drift as purlin_drift


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

def _git(args, cwd, check=True, env=None):
    """Run a git command in the given directory, capturing output."""
    full_env = None
    if env:
        full_env = dict(os.environ)
        full_env.update(env)
    return subprocess.run(['git'] + args, cwd=cwd, capture_output=True,
                          text=True, check=check, env=full_env)


def _sha(cwd, ref='HEAD'):
    return _git(['rev-parse', ref], cwd).stdout.strip()


def _rmtree(path):
    """Remove a tree that holds a git repository, on every operating system.

    Git marks loose objects and packs read-only. A read-only file inside a
    writable directory still unlinks on POSIX; on Windows it does not, and the
    removal raises PermissionError. Clearing the bit and retrying once is the
    whole difference.
    """
    def _retry(func, failed, _exc_info):
        os.chmod(failed, stat.S_IWRITE)
        func(failed)

    shutil.rmtree(path, onerror=_retry)


def _write(path, text):
    """Write `text` to `path`, creating the parent directory."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(text)


def _identity(root):
    _git(['config', 'user.email', 'test@test.com'], root)
    _git(['config', 'user.name', 'Test'], root)
    _git(['config', 'pull.rebase', 'false'], root)
    _git(['config', 'commit.gpgsign', 'false'], root)


def _commit(root, message, env=None):
    _git(['add', '-A'], root)
    _git(['commit', '-q', '-m', message], root, env=env)
    return _sha(root)


def _repo(root, files=None, gate=None):
    """A git repository made in place, its first commit holding `files`."""
    os.makedirs(root, exist_ok=True)
    _write(os.path.join(root, '.purlin', 'config.json'), _config(gate))
    for path, text in (files or {}).items():
        _write(os.path.join(root, *path.split('/')), text)
    _git(['-c', 'init.defaultBranch=main', 'init', '-q'], root)
    _identity(root)
    _commit(root, 'chore: start')
    return root


def _clone(source, root):
    _git(['clone', '-q', source, root], os.path.dirname(root))
    _identity(root)
    return root


def _change(root, files, message='feat: change'):
    """Write or delete (`None`) each file, and commit."""
    for path, text in files.items():
        full = os.path.join(root, *path.split('/'))
        if text is None:
            os.remove(full)
        else:
            _write(full, text)
    return _commit(root, message)


def _merged_with_conflict(tmp_path):
    """`(root, before)`: a merge of `topic` into `main` that stopped on a
    conflict, resolved and committed by hand.

    `topic` carries 2 commits and `main` 1, both changing the same line of
    `a.txt`. `before` is where `main` stood before the merge.
    """
    root = _repo(str(tmp_path / 'proj'), {'a.txt': '0\n'})
    _git(['checkout', '-q', '-b', 'topic'], root)
    _change(root, {'b.txt': '1\n'})
    _change(root, {'a.txt': 'topic\n'})
    _git(['checkout', '-q', 'main'], root)
    _change(root, {'a.txt': 'main\n'})
    before = _sha(root)
    stopped = _git(['merge', '-q', '--no-edit', 'topic'], root, check=False)
    assert stopped.returncode != 0, stopped
    assert 'CONFLICT' in stopped.stdout + stopped.stderr, stopped
    _write(os.path.join(root, 'a.txt'), 'both\n')
    _git(['add', 'a.txt'], root)
    _git(['commit', '-q', '--no-edit'], root)
    subjects = _git(['reflog', 'show', '--format=%gs', 'HEAD'], root).stdout
    assert subjects.splitlines()[0].startswith('commit (merge):'), subjects
    return root, before


def _pulled(tmp_path, start, changes, gate=None):
    """`(upstream, checkout, before)`: the checkout pulled `changes`.

    The upstream holds `start`; the checkout is cloned from it, then the
    upstream commits each of `changes` in turn and the checkout pulls them.
    `before` is where the checkout stood before the pull.
    """
    upstream = _repo(str(tmp_path / 'upstream'), start, gate=gate)
    checkout = _clone(upstream, str(tmp_path / 'checkout'))
    before = _sha(checkout)
    for index, files in enumerate(changes):
        _change(upstream, files, 'feat: upstream change %d' % index)
    _git(['pull', '-q'], checkout)
    return upstream, checkout, before


def _spec(name, rules, scope=None, proofs=None, kind='Feature'):
    """A spec's text: `rules` is `{RULE-N: text}`, `proofs` `{PROOF-N: (RULE, text)}`."""
    lines = ['# %s: %s' % (kind, name), '']
    if scope:
        lines += ['> Scope: %s' % scope, '']
    lines += ['## Rules', '']
    lines += ['- %s: %s' % (rid, text) for rid, text in rules.items()]
    lines += ['', '## Proof', '']
    if proofs is None:
        proofs = {'PROOF-%s' % rid.split('-')[1]: (rid, 'Call it and see 1')
                  for rid in rules}
    lines += ['- %s (%s): %s' % (pid, rid, text)
              for pid, (rid, text) in proofs.items()]
    return '\n'.join(lines) + '\n'


# The suite a test project names, so its marked files are read.
TESTS = [{'name': 'pytest', 'run': 'pytest {files}', 'report': None,
          'format': 'junit', 'files': ['tests/test_*.py']}]


def _config(gate=None):
    config = {'tests': TESTS}
    if gate is not None:
        config['gate'] = gate
    return json.dumps(config)


def _marked(*features):
    return ''.join('# purlin: %s PROOF-1\ndef test_%s():\n    pass\n\n'
                   % (name, index) for index, name in enumerate(features))


def _report(root, since=None):
    return json.loads(purlin_drift.drift(root, since=since))


def _lines(report, role):
    """A view's lines after the first, which names the range."""
    return report['roles'][role]['lines'][1:]


LOGIN = _spec('login', {'RULE-1': 'Signs a person in',
                        'RULE-2': 'Refuses a wrong password'},
              scope='src/auth/')
LOGIN_FILES = {'specs/auth/login.md': LOGIN,
               'src/auth/login.py': 'def login():\n    return 1\n',
               'src/auth/token.py': 'def token():\n    return 1\n'}


# ---------------------------------------------------------------------------
# RULE-1: the `since` argument
# ---------------------------------------------------------------------------

class TestSinceValidation:

    # purlin: drift PROOF-1
    def test_a_since_that_is_no_count_or_date_is_refused(self, tmp_path,
                                                         monkeypatch):
        root = _repo(str(tmp_path / 'proj'))
        calls = []
        real_run = subprocess.run

        def spy(args, *rest, **kwargs):
            calls.append(list(args))
            return real_run(args, *rest, **kwargs)

        monkeypatch.setattr(purlin_drift.subprocess, 'run', spy)
        refused = _report(root, since='--output=/tmp/x')

        assert refused['error'] == 'rejected since', refused
        assert 'digits only' in refused['reason'], refused['reason']
        assert 'YYYY-MM-DD' in refused['reason'], refused['reason']
        assert calls == [], calls

    # purlin: drift PROOF-2
    def test_a_count_is_accepted_and_git_is_run(self, tmp_path, monkeypatch):
        root = _repo(str(tmp_path / 'proj'))
        for index in range(2):
            _change(root, {'f%d.txt' % index: str(index)})
        calls = []
        real_run = subprocess.run

        def spy(args, *rest, **kwargs):
            calls.append(list(args))
            return real_run(args, *rest, **kwargs)

        monkeypatch.setattr(purlin_drift.subprocess, 'run', spy)
        report = _report(root, since='2')

        assert report['since']['commits'] == 2, report['since']
        assert any(call[:1] == ['git'] for call in calls), calls


# ---------------------------------------------------------------------------
# RULE-2: the last git action that brought changes in
# ---------------------------------------------------------------------------

class TestWhereDriftStarts:

    # purlin: drift PROOF-3
    def test_a_pull_is_measured_from_where_head_stood_before_it(self,
                                                                tmp_path):
        _up, checkout, before = _pulled(
            tmp_path, {'a.txt': '0\n'}, [{'a.txt': '1\n'}, {'a.txt': '2\n'}])
        _change(checkout, {'b.txt': 'mine\n'}, 'feat: my own commit')

        since = _report(checkout)['since']
        assert since['action'] == 'pull', since
        assert since['from'] == before, since
        assert since['to'] == _sha(checkout), since
        assert since['commits'] == 3, since

    # purlin: drift PROOF-4
    def test_a_merge_is_measured_from_main_before_it(self, tmp_path):
        root = _repo(str(tmp_path / 'proj'), {'a.txt': '0\n'})
        _git(['checkout', '-q', '-b', 'topic'], root)
        _change(root, {'b.txt': '1\n'})
        _change(root, {'b.txt': '2\n'})
        _git(['checkout', '-q', 'main'], root)
        _change(root, {'a.txt': 'main moved\n'})
        before = _sha(root)
        _git(['merge', '-q', '--no-edit', 'topic'], root)

        since = _report(root)['since']
        assert since['action'] == 'merge', since
        assert since['from'] == before, since
        assert since['commits'] == 3, since

    # purlin: drift PROOF-29
    def test_a_merge_committed_after_its_conflicts_counts_as_a_merge(
            self, tmp_path):
        root, before = _merged_with_conflict(tmp_path)

        since = _report(root)['since']
        assert since['action'] == 'merge', since
        assert since['from'] == before, since
        assert since['to'] == _sha(root), since
        assert since['commits'] == 3, since

    # purlin: drift PROOF-35
    def test_a_plain_commit_after_the_merge_is_not_an_action(self, tmp_path):
        root, before = _merged_with_conflict(tmp_path)
        _change(root, {'c.txt': 'after\n'}, 'feat: after the merge')

        since = _report(root)['since']
        assert since['action'] == 'merge', since
        assert since['from'] == before, since
        assert since['to'] == _sha(root), since
        assert since['commits'] == 4, since

    # purlin: drift PROOF-5
    def test_a_rebase_is_measured_from_before_its_first_step(self, tmp_path):
        root = _repo(str(tmp_path / 'proj'), {'a.txt': '0\n'})
        _git(['checkout', '-q', '-b', 'topic'], root)
        _change(root, {'b.txt': 'mine\n'})
        _git(['checkout', '-q', 'main'], root)
        _change(root, {'a.txt': '1\n'})
        _change(root, {'a.txt': '2\n'})
        _git(['checkout', '-q', 'topic'], root)
        before = _sha(root)
        _git(['rebase', '-q', 'main'], root)
        subjects = _git(['reflog', 'show', '--format=%gs', 'HEAD'],
                        root).stdout
        assert '(finish)' in subjects, subjects

        since = _report(root)['since']
        assert since['action'] == 'rebase', since
        assert since['from'] == before, since
        assert since['commits'] == 3, since

    # purlin: drift PROOF-6
    def test_a_checkout_is_measured_from_the_branch_it_left(self, tmp_path):
        root = _repo(str(tmp_path / 'proj'), {'a.txt': '0\n'})
        main = _sha(root)
        _git(['checkout', '-q', '-b', 'ahead'], root)
        _change(root, {'a.txt': '1\n'})
        _change(root, {'a.txt': '2\n'})
        _git(['checkout', '-q', 'main'], root)
        _git(['checkout', '-q', 'ahead'], root)

        since = _report(root)['since']
        assert since['action'] == 'checkout', since
        assert since['from'] == main, since
        assert since['commits'] == 2, since

    # purlin: drift PROOF-7
    def test_a_reset_after_a_pull_is_the_newest_action(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, {'a.txt': '0\n'}, [{'a.txt': '1\n'}, {'a.txt': '2\n'}])
        pulled = _sha(checkout)
        _git(['reset', '-q', '--hard', 'HEAD~2'], checkout)

        since = _report(checkout)['since']
        assert since['action'] == 'reset', since
        assert since['from'] == pulled, since
        assert since['to'] == _sha(checkout), since


# ---------------------------------------------------------------------------
# RULE-3: the clone, or nothing at all
# ---------------------------------------------------------------------------

def _twenty_five_commits(tmp_path):
    """A repository of 25 commits made in place, with no pull, merge,
    rebase, checkout, clone or reset in its log of HEAD."""
    made = _repo(str(tmp_path / 'made'), {'a.txt': '0\n'})
    for index in range(24):
        _change(made, {'a.txt': '%d\n' % (index + 1)})
    assert _git(['rev-list', '--count', 'HEAD'], made).stdout.strip() == '25'
    return made


class TestTheLastTwentyCommits:

    # purlin: drift PROOF-8
    def test_a_clone_measures_its_last_twenty_commits(self, tmp_path):
        made = _twenty_five_commits(tmp_path)
        cloned = _clone(made, str(tmp_path / 'cloned'))

        since = _report(cloned)['since']
        assert since['action'] == 'clone', since
        assert since['from'] == _sha(cloned, 'HEAD~20'), since
        assert since['to'] == _sha(cloned), since
        assert since['commits'] == 20, since

    # purlin: drift PROOF-36
    def test_a_repository_with_no_action_measures_its_last_twenty(
            self, tmp_path):
        made = _twenty_five_commits(tmp_path)

        since = _report(made)['since']
        assert since['action'] is None, since
        assert since['from'] == _sha(made, 'HEAD~20'), since
        assert since['commits'] == 20, since

    # purlin: drift PROOF-37
    def test_a_repository_of_three_commits_measures_all_three(self,
                                                             tmp_path):
        small = _repo(str(tmp_path / 'small'), {'a.txt': '0\n'})
        _change(small, {'a.txt': '1\n'})
        _change(small, {'a.txt': '2\n'})
        since = _report(small)['since']
        assert since['from'] is None, since
        assert since['commits'] == 3, since
        assert since['line'] == (
            "The last 3 commits (up to %s, 3 commits). Git's log of HEAD "
            "names no pull, merge, rebase, checkout, clone or reset."
            % _sha(small)[:7]), since['line']


# ---------------------------------------------------------------------------
# RULE-4: `since` overrides the log
# ---------------------------------------------------------------------------

class TestSinceOverrides:

    # purlin: drift PROOF-9
    def test_a_count_wins_over_the_pull(self, tmp_path):
        upstream = _repo(str(tmp_path / 'upstream'), {'a.txt': '0\n'})
        for index in range(3):
            _change(upstream, {'a.txt': '%d\n' % (index + 1)})
        checkout = _clone(upstream, str(tmp_path / 'checkout'))
        _change(upstream, {'a.txt': 'pulled\n'})
        _git(['pull', '-q'], checkout)
        assert _report(checkout)['since']['commits'] == 1

        since = _report(checkout, since='3')['since']
        assert since['commits'] == 3, since
        assert since['from'] == _sha(checkout, 'HEAD~3'), since
        assert since['line'].startswith('The last 3 commits ('), since

    # purlin: drift PROOF-10
    def test_a_date_measures_the_commits_made_since(self, tmp_path):
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        _write(os.path.join(root, '.purlin', 'config.json'), '{}')
        _git(['-c', 'init.defaultBranch=main', 'init', '-q'], root)
        _identity(root)
        shas = []
        for index, day in enumerate(('2026-01-01', '2026-03-01',
                                     '2026-04-01')):
            _write(os.path.join(root, 'a.txt'), '%d\n' % index)
            stamp = '%sT12:00:00' % day
            shas.append(_commit(root, 'chore: %s' % day,
                                env={'GIT_AUTHOR_DATE': stamp,
                                     'GIT_COMMITTER_DATE': stamp}))

        since = _report(root, since='2026-02-15')['since']
        assert since['commits'] == 2, since
        assert since['from'] == shas[0], since
        assert since['line'].startswith('Since 2026-02-15 ('), since


# ---------------------------------------------------------------------------
# RULE-5: the first line
# ---------------------------------------------------------------------------

class TestTheFirstLine:

    # purlin: drift PROOF-11
    def test_every_view_opens_by_naming_the_pull(self, tmp_path):
        _up, checkout, before = _pulled(
            tmp_path, {'a.txt': '0\n'}, [{'a.txt': '1\n'}, {'a.txt': '2\n'}])
        report = _report(checkout)

        firsts = [report['roles'][role]['lines'][0]
                  for role in ('pm', 'eng', 'qa')]
        assert len(set(firsts)) == 1, firsts
        pattern = (r'^Since your last pull, \d+ \w+ ago '
                   r'\(%s\.\.%s, 2 commits\)\.$'
                   % (before[:7], _sha(checkout)[:7]))
        assert re.match(pattern, firsts[0]), firsts[0]
        assert report['since']['line'] == firsts[0]


    # purlin: drift PROOF-30
    def test_every_view_opens_by_naming_a_merge_with_conflicts(self,
                                                               tmp_path):
        root, before = _merged_with_conflict(tmp_path)
        report = _report(root)

        firsts = [report['roles'][role]['lines'][0]
                  for role in ('pm', 'eng', 'qa')]
        assert len(set(firsts)) == 1, firsts
        pattern = (r'^Since your last merge, \d+ \w+ ago '
                   r'\(%s\.\.%s, 3 commits\)\.$'
                   % (before[:7], _sha(root)[:7]))
        assert re.match(pattern, firsts[0]), firsts[0]

# ---------------------------------------------------------------------------
# RULE-6: the PM view
# ---------------------------------------------------------------------------

class TestPmView:

    # purlin: drift PROOF-12
    def test_rules_added_changed_and_removed(self, tmp_path):
        cart = _spec('cart', {'RULE-1': 'Holds items',
                              'RULE-2': 'Empties on checkout'})
        _up, checkout, _before = _pulled(
            tmp_path,
            {'specs/auth/login.md': LOGIN, 'specs/shop/cart.md': cart},
            [{'specs/auth/login.md': _spec(
                'login', {'RULE-1': 'Signs a person in with a passkey',
                          'RULE-2': 'Refuses a wrong password',
                          'RULE-3': 'Locks after five tries'},
                scope='src/auth/'),
              'specs/shop/cart.md': _spec('cart', {'RULE-1': 'Holds items'})}])
        report = _report(checkout)

        assert _lines(report, 'pm') == [
            '1 rule added: login RULE-3.',
            '1 rule changed: login RULE-1.',
            '1 rule removed: cart RULE-2.'], _lines(report, 'pm')
        pm = report['roles']['pm']
        assert pm['rules_added'] == {'login': ['RULE-3']}, pm
        assert pm['rules_changed'] == {'login': ['RULE-1']}, pm
        assert pm['rules_removed'] == {'cart': ['RULE-2']}, pm

    # purlin: drift PROOF-38
    def test_a_spec_moved_with_its_rules_unchanged_is_named_nowhere(
            self, tmp_path):
        other = _spec('other', {'RULE-1': 'Stays the same'})
        _up, checkout, _before = _pulled(
            tmp_path, {'specs/a/other.md': other},
            [{'specs/a/other.md': None, 'specs/b/other.md': other}])
        report = _report(checkout)

        assert _lines(report, 'pm') == [
            'No rule was added, changed or removed since your last pull.'], \
            _lines(report, 'pm')

    # purlin: drift PROOF-13
    def test_a_change_to_no_spec_names_no_rule(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES,
            [{'src/auth/login.py': 'def login():\n    return 2\n'}])
        assert _lines(_report(checkout), 'pm') == [
            'No rule was added, changed or removed since your last pull.']


# ---------------------------------------------------------------------------
# RULE-7 to RULE-9 and RULE-14: the engineer view
# ---------------------------------------------------------------------------

def _evidence_file(root, feature, rule_ids):
    """Write a local section marking each of `rule_ids` as passing.

    The fingerprint is taken when this is called, so the section is current
    for the tree as it stands then.
    """
    from purlin import evidence as purlin_evidence
    from purlin import fingerprint as purlin_fingerprint

    path = os.path.join(root, '.purlin', 'evidence', 'local',
                        '%s.json' % feature)
    _write(path, json.dumps({
        'schema': 'purlin-evidence/2', 'feature': feature,
        'source': 'local', 'spec': '',
        'platforms': {purlin_evidence.host_os(): {
            'commit': '', 'dirty': False, 'at': '2026-09-13T12:00:00Z',
            'runner': 'test',
            'fingerprint': purlin_fingerprint.fingerprint(root, feature),
            'rules': {},
            'proofs': [{'id': 'PROOF-%s' % rid.split('-')[1], 'rule': rid,
                        'result': 'pass', 'env': None, 'manual': False,
                        'test': 'tests/test_%s.py::test_%s' % (
                            feature, rid.lower().replace('-', '_'))}
                       for rid in rule_ids]}}}))


class TestEngView:

    # purlin: drift PROOF-14
    def test_code_changed_under_a_directory_scope(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES,
            [{'src/auth/login.py': 'def login():\n    return 2\n',
              'src/auth/token.py': 'def token():\n    return 2\n'}])
        report = _report(checkout)

        assert ("2 files changed under login's scope: RULE-1, RULE-2 are "
                "behind them.") in _lines(report, 'eng'), _lines(report, 'eng')
        assert report['roles']['eng']['code_changed'] == [
            {'feature': 'login',
             'files': ['src/auth/login.py', 'src/auth/token.py'],
             'rules': ['RULE-1', 'RULE-2']}]

    # purlin: drift PROOF-15
    def test_changed_files_under_no_scope(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES,
            [{'src/x.py': 'x = 1\n', 'src/y.py': 'y = 1\n',
              'specs/auth/login.md': LOGIN + '\n',
              '.purlin/config.json': _config('passed'),
              'tests/test_login.py': _marked('login')}])
        report = _report(checkout)

        assert ("2 changed files are under no spec's scope: src/x.py, "
                "src/y.py.") in _lines(report, 'eng'), _lines(report, 'eng')
        assert report['roles']['eng']['unscoped'] == ['src/x.py', 'src/y.py']

    # purlin: drift PROOF-16
    def test_rules_no_test_has_run_for_are_named(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES, [{'README.md': 'login\n'}])
        report = _report(checkout)
        assert '2 rules have no test: login RULE-1, RULE-2.' in \
            _lines(report, 'eng'), _lines(report, 'eng')
        assert report['roles']['eng']['rules_without_test'] == {
            'login': ['RULE-1', 'RULE-2']}

    # purlin: drift PROOF-39
    def test_rules_with_a_passing_run_are_not_named(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES, [{'README.md': 'login\n'}])
        _evidence_file(checkout, 'login', ['RULE-1', 'RULE-2'])
        report = _report(checkout)
        assert not [line for line in _lines(report, 'eng')
                    if 'no test' in line], _lines(report, 'eng')
        assert report['roles']['eng']['rules_without_test'] == {}

    # purlin: drift PROOF-23
    def test_a_feature_with_a_run_is_out_of_date_and_one_without_is_not(
            self, tmp_path):
        cart = _spec('cart', {'RULE-1': 'Holds items'}, scope='src/cart.py')
        start = dict(LOGIN_FILES)
        start.update({'specs/shop/cart.md': cart, 'src/cart.py': 'c = 1\n'})
        upstream = _repo(str(tmp_path / 'upstream'), start)
        checkout = _clone(upstream, str(tmp_path / 'checkout'))
        _evidence_file(checkout, 'login', ['RULE-1', 'RULE-2'])
        assert not [line for line in _lines(_report(checkout, since='1'),
                                            'eng') if 'out of date' in line]
        _change(upstream, {'src/auth/login.py': 'def login():\n    return 2\n',
                           'src/cart.py': 'c = 2\n'})
        _git(['pull', '-q'], checkout)
        report = _report(checkout)

        assert '1 feature is out of date: login.' in _lines(report, 'eng'), \
            _lines(report, 'eng')
        assert report['roles']['eng']['out_of_date'] == ['login']


# ---------------------------------------------------------------------------
# RULE-10: anchors that are not current
# ---------------------------------------------------------------------------

def _create_bare_repo(bare_path, initial_file='spec.md', initial_content='# initial'):
    """Create a bare git repo with one commit. Returns the initial commit SHA."""
    subprocess.run(['git', '-c', 'init.defaultBranch=main', 'init', '--bare',
                    '-q', bare_path], check=True, capture_output=True)
    work_dir = bare_path + '_work'
    subprocess.run(['git', 'clone', '-q', bare_path, work_dir],
                   check=True, capture_output=True)
    _identity(work_dir)
    _write(os.path.join(work_dir, initial_file), initial_content)
    _commit(work_dir, 'initial spec')
    subprocess.run(['git', 'push', '-q', 'origin', 'HEAD:main'],
                   cwd=work_dir, capture_output=True, check=True)
    sha = _sha(work_dir)
    _rmtree(work_dir)
    return sha


def _advance_bare_repo(bare_path, file_path='spec.md', new_content='# updated'):
    """Add a new commit to a bare repo. Returns the new HEAD SHA."""
    work_dir = bare_path + '_work2'
    subprocess.run(['git', 'clone', '-q', bare_path, work_dir],
                   check=True, capture_output=True)
    _identity(work_dir)
    _write(os.path.join(work_dir, file_path), new_content)
    _commit(work_dir, 'update spec')
    subprocess.run(['git', 'push', '-q', 'origin', 'HEAD:main'],
                   cwd=work_dir, capture_output=True, check=True)
    sha = _sha(work_dir)
    _rmtree(work_dir)
    return sha


def _anchor_text(anchor_name, source, pinned_sha=None, rules=None):
    """An anchor spec naming `source`, pinned to `pinned_sha` when given."""
    rules = rules or {'RULE-1': 'External constraint one'}
    meta = '> Source: %s\n' % source
    if pinned_sha:
        meta += '> Pinned: %s\n' % pinned_sha
    return _spec(anchor_name, rules, kind='Anchor').replace(
        '\n\n## Rules', '\n\n%s\n## Rules' % meta, 1)


def _pinned_project(root, bare_path, anchor_name, pinned_sha, rules=None):
    """A project whose one anchor is pinned to `pinned_sha` of `bare_path`."""
    return _repo(root, {'specs/_anchors/%s.md' % anchor_name: _anchor_text(
        anchor_name, bare_path, pinned_sha, rules)})


def _anchor_rows(root):
    return _report(root)['roles']['eng']['anchors_behind']


def _spied(monkeypatch):
    """Every command line started from here on, as a list of lists."""
    calls = []
    real_run = subprocess.run

    def spy(args, *rest, **kwargs):
        calls.append(list(args))
        return real_run(args, *rest, **kwargs)

    monkeypatch.setattr(purlin_drift.subprocess, 'run', spy)
    return calls


def _handed(calls, value):
    """The command lines that carry `value` in any argument."""
    return [call for call in calls if any(value in str(arg) for arg in call)]


def _one_anchor(tmp_path, monkeypatch, source, pinned='abc1234'):
    """`(report, calls)`: drift's report on a project whose one anchor,
    `policy`, names `source`, and every command the report started."""
    root = _repo(str(tmp_path / 'proj'), {
        'specs/_anchors/policy.md': _anchor_text('policy', source, pinned)})
    calls = _spied(monkeypatch)
    return _report(root), calls


def _refused(tmp_path, monkeypatch, source, reason):
    """Assert the anchor pinned to `source` is refused for `reason`, its
    line says so, and no command was handed that source."""
    report, calls = _one_anchor(tmp_path, monkeypatch, source)
    assert report['roles']['eng']['anchors_behind'] == [
        {'anchor': 'policy', 'source': source, 'pinned': 'abc1234',
         'status': 'error', 'error': 'rejected source url',
         'reason': reason}], report['roles']['eng']['anchors_behind']
    assert ('anchor policy: its source could not be read (%s).' % reason) \
        in _lines(report, 'eng'), _lines(report, 'eng')
    assert _handed(calls, source) == [], _handed(calls, source)


class TestAnchorsBehind:

    # purlin: drift PROOF-17
    def test_a_pin_behind_names_the_new_sha(self, tmp_path):
        bare = str(tmp_path / 'anchor.git')
        first = _create_bare_repo(bare, 'spec.md', '# spec v1')
        root = _pinned_project(str(tmp_path / 'proj'), bare,
                               'external_anchor', first)
        new_sha = _advance_bare_repo(bare, 'spec.md', '# spec v2')
        report = _report(root)

        rows = [row for row in report['roles']['eng']['anchors_behind']
                if row['anchor'] == 'external_anchor']
        assert len(rows) == 1, rows
        assert rows[0]['status'] == 'behind', rows
        assert len(rows[0]['remote_sha']) == 7, rows
        assert new_sha.startswith(rows[0]['remote_sha']), (rows, new_sha)
        assert ('anchor external_anchor is behind its source (now %s). Run: '
                'purlin:anchor sync external_anchor.' % new_sha[:7]) in \
            _lines(report, 'eng'), _lines(report, 'eng')

    # purlin: drift PROOF-18
    def test_an_anchor_with_rules_of_its_own_goes_behind(self, tmp_path):
        bare = str(tmp_path / 'anchor.git')
        first = _create_bare_repo(bare, 'policy.md', '# policy v1')
        root = _pinned_project(str(tmp_path / 'proj'), bare, 'mixed_policy',
                               first, {'RULE-1': 'Local constraint one',
                                       'RULE-2': 'Local constraint two'})
        _advance_bare_repo(bare, 'policy.md', '# policy v2')

        rows = [row for row in _anchor_rows(root)
                if row['anchor'] == 'mixed_policy'
                and row['status'] == 'behind']
        assert len(rows) == 1, rows

    # purlin: drift PROOF-19
    def test_a_source_with_no_pin_reads_unpinned(self, tmp_path,
                                                 monkeypatch):
        source = 'https://github.com/acme/p.git'
        report, calls = _one_anchor(tmp_path, monkeypatch, source,
                                    pinned=None)

        assert report['roles']['eng']['anchors_behind'] == [
            {'anchor': 'policy', 'source': source, 'pinned': None,
             'status': 'unpinned'}], report['roles']['eng']['anchors_behind']
        assert ('anchor policy names a source and no pin. Run: '
                'purlin:anchor sync policy.') in _lines(report, 'eng'), \
            _lines(report, 'eng')
        assert _handed(calls, source) == [], _handed(calls, source)

    # purlin: drift PROOF-40
    def test_a_source_that_cannot_be_read_reads_error(self, tmp_path,
                                                      monkeypatch):
        missing = os.path.join(str(tmp_path), 'nope.git')
        report, _calls = _one_anchor(tmp_path, monkeypatch, missing)

        rows = report['roles']['eng']['anchors_behind']
        assert len(rows) == 1, rows
        assert rows[0]['anchor'] == 'policy', rows
        assert rows[0]['status'] == 'error', rows
        assert 'remote_sha' not in rows[0], rows
        assert 'nope.git' in rows[0]['error'], rows
        assert ('anchor policy: its source could not be read (%s).'
                % rows[0]['error']) in _lines(report, 'eng'), \
            _lines(report, 'eng')

    # purlin: drift PROOF-41
    def test_an_anchor_still_at_its_pin_is_not_named(self, tmp_path,
                                                     monkeypatch):
        bare = os.path.join(str(tmp_path), 'anchor.git')
        sha = _create_bare_repo(bare, 'policy.md', '# policy v1')
        report, calls = _one_anchor(tmp_path, monkeypatch, bare, pinned=sha)

        # The source was read, and found at its pin.
        assert len([c for c in _handed(calls, bare) if 'ls-remote' in c]) \
            == 1, calls
        assert report['roles']['eng']['anchors_behind'] == []
        assert not [line for line in _lines(report, 'eng')
                    if 'anchor' in line], _lines(report, 'eng')


# ---------------------------------------------------------------------------
# RULE-11: a source that is not safe is refused before any process starts
# ---------------------------------------------------------------------------

class TestUnsafeSources:

    # purlin: drift PROOF-20
    def test_a_source_that_begins_with_a_dash_is_refused(self, tmp_path,
                                                         monkeypatch):
        _refused(tmp_path, monkeypatch, '--upload-pack=/bin/echo',
                 'begins with "-"')

    # purlin: drift PROOF-42
    def test_a_source_naming_the_ext_transport_is_refused(self, tmp_path,
                                                          monkeypatch):
        _refused(tmp_path, monkeypatch, 'ext::sh -c id',
                 'names an ext:: transport')

    # purlin: drift PROOF-43
    def test_a_source_naming_the_fd_transport_is_refused(self, tmp_path,
                                                         monkeypatch):
        _refused(tmp_path, monkeypatch, 'fd::7', 'names an fd:: transport')

    # purlin: drift PROOF-44
    def test_a_source_carrying_a_nul_byte_is_refused(self, tmp_path,
                                                     monkeypatch):
        _refused(tmp_path, monkeypatch, '/srv/anchors\x00.git',
                 'contains a NUL byte')

    # purlin: drift PROOF-45
    def test_a_source_carrying_a_newline_is_refused(self, tmp_path,
                                                    monkeypatch):
        # A spec's `> Source:` line ends at a line break, so this value is
        # handed to the check of one anchor's source directly.
        root = _repo(str(tmp_path / 'proj'))
        calls = _spied(monkeypatch)
        row = purlin_drift.check_pin(
            root, '/srv/anchors.git\n--upload-pack=x', 'abc1234')

        assert row == {'status': 'error', 'remote_sha': None,
                       'error': 'rejected source url',
                       'reason': 'contains a newline'}, row
        assert calls == [], calls

    # purlin: drift PROOF-46
    def test_a_source_holding_ext_and_a_dash_inside_is_not_refused(
            self, tmp_path, monkeypatch):
        source = 'https://github.com/acme/ext-rules.git'
        report, _calls = _one_anchor(tmp_path, monkeypatch, source,
                                     pinned=None)

        assert report['roles']['eng']['anchors_behind'] == [
            {'anchor': 'policy', 'source': source, 'pinned': None,
             'status': 'unpinned'}], report['roles']['eng']['anchors_behind']


# ---------------------------------------------------------------------------
# RULE-12 and RULE-13: one listing per source, and the row's name
# ---------------------------------------------------------------------------

class TestAnchorRows:

    # purlin: drift PROOF-21
    def test_three_anchors_of_one_source_list_it_once(self, tmp_path,
                                                      monkeypatch):
        bare = str(tmp_path / 'anchor.git')
        first = _create_bare_repo(bare, 'policy.md', '# policy v1')
        root = _repo(str(tmp_path / 'proj'), {
            'specs/_anchors/%s.md' % name: _anchor_text(name, bare, first)
            for name in ('policy_a', 'policy_b', 'policy_c')})
        _advance_bare_repo(bare, 'policy.md', '# policy v2')
        calls = _spied(monkeypatch)
        report = _report(root)

        rows = report['roles']['eng']['anchors_behind']
        assert [(row['anchor'], row['status']) for row in rows] == [
            ('policy_a', 'behind'), ('policy_b', 'behind'),
            ('policy_c', 'behind')], rows
        assert len([c for c in calls if 'ls-remote' in c]) == 1, calls

    # purlin: drift PROOF-22
    def test_the_row_names_the_spec_not_the_repository(self, tmp_path):
        bare = str(tmp_path / 'anchor.git')
        first = _create_bare_repo(bare, 'constraints.md', '# constraints v1')
        root = _repo(str(tmp_path / 'proj'), {
            'specs/_anchors/local_security.md': _anchor_text(
                'local_security', '%s constraints.md' % bare, first)})
        new_sha = _advance_bare_repo(bare, 'constraints.md',
                                     '# constraints v2')
        report = _report(root)

        rows = [row for row in report['roles']['eng']['anchors_behind']
                if row['status'] == 'behind']
        assert [row['anchor'] for row in rows] == ['local_security'], rows
        anchor_lines = [line for line in _lines(report, 'eng')
                        if line.startswith('anchor ')]
        assert anchor_lines == [
            'anchor local_security is behind its source (now %s). Run: '
            'purlin:anchor sync local_security.' % new_sha[:7]], anchor_lines


# ---------------------------------------------------------------------------
# RULE-15: the QA view
# ---------------------------------------------------------------------------

class TestQaView:

    # purlin: drift PROOF-24
    def test_test_files_changed_and_what_they_cover(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES,
            [{'tests/test_both.py': _marked('login', 'export'),
              'tests/test_login.py': _marked('login'),
              'tests/test_plain.py': 'def test_plain():\n    pass\n'}])
        report = _report(checkout)

        assert _lines(report, 'qa') == [
            '2 test files changed, covering export, login.'], \
            _lines(report, 'qa')
        assert report['roles']['qa']['tests_changed'] == {
            'files': ['tests/test_both.py', 'tests/test_login.py'],
            'features': ['export', 'login']}

    # purlin: drift PROOF-31
    def test_a_rule_to_test_by_hand(self, tmp_path):
        root = _repo(str(tmp_path / 'proj'), {
            'specs/auth/login.md': _spec(
                'login', {'RULE-1': 'Signs a person in',
                          'RULE-2': 'Looks right on a phone'},
                scope='src/auth/',
                proofs={'PROOF-1': ('RULE-1', 'Sign in and see 1'),
                        'PROOF-2': ('RULE-2',
                                    'Look at it on a phone @manual')}),
            'src/auth/login.py': 'x = 1\n'}, gate='passed')
        _change(root, {'src/auth/login.py': 'x = 2\n'})

        assert _lines(_report(root, since='1'), 'qa') == [
            '1 rule to test by hand: purlin:sign']

    # purlin: drift PROOF-32
    def test_the_rules_to_sign_and_not_the_rest(self, tmp_path):
        assert _qa_lines_left(tmp_path, [
            _left('to_audit', 3, '3 rules to audit', 'purlin:audit'),
            _left('to_sign', 2, '2 rules to sign', 'purlin:sign')]) == [
            '2 rules to sign: purlin:sign']

    # purlin: drift PROOF-33
    def test_nothing_waiting_for_a_person_prints_nothing(self, tmp_path):
        assert _qa_lines_left(tmp_path, [
            _left('to_audit', 3, '3 rules to audit', 'purlin:audit')]) == []

    # purlin: drift PROOF-34
    def test_the_qa_view_carries_the_items_it_printed(self, tmp_path):
        view = _qa_view_left(tmp_path, [
            _left('to_audit', 3, '3 rules to audit', 'purlin:audit'),
            _left('to_sign', 2, '2 rules to sign', 'purlin:sign')])
        assert view['left'] == [
            _left('to_sign', 2, '2 rules to sign', 'purlin:sign')]


def _left(kind, count, text, command):
    """One line of `Left to do` as the status's payload carries it."""
    return {'kind': kind, 'count': count, 'text': text, 'command': command}


def _qa_view_left(tmp_path, left):
    """The QA view, with the status's `Left to do` holding `left`, in a
    project where one source file changed."""
    from purlin import payload as purlin_payload
    root = _repo(str(tmp_path / 'proj'), LOGIN_FILES, gate='signed')
    _change(root, {'src/auth/login.py': 'def login():\n    return 2\n'})
    data = purlin_payload.build_payload(root)
    data['left'] = left
    report = purlin_drift.compute_drift(root, since='1', network=False,
                                        data=data)
    return report['roles']['qa']


def _qa_lines_left(tmp_path, left):
    """The QA view's lines after the first."""
    return _qa_view_left(tmp_path, left)['lines'][1:]


# ---------------------------------------------------------------------------
# RULE-17: spec files not committed
# ---------------------------------------------------------------------------

class TestSpecsNotCommitted:

    # purlin: drift PROOF-26
    def test_one_spec_edited_ends_every_view_with_one(self, tmp_path):
        root = _edited_spec(tmp_path)
        report = _report(root, since='1')
        for role in ('pm', 'eng', 'qa'):
            assert report['roles'][role]['lines'][-1] == (
                '1 spec file has changes that are not committed.'), role
            assert report['roles'][role]['specs_uncommitted'] == 1

    # purlin: drift PROOF-47
    def test_a_spec_edited_and_one_not_tracked_end_every_view_with_two(
            self, tmp_path):
        root = _edited_spec(tmp_path)
        _write(os.path.join(root, 'specs', 'shop', 'cart.md'),
               _spec('cart', {'RULE-1': 'Holds items'}))
        report = _report(root, since='1')
        for role in ('pm', 'eng', 'qa'):
            assert report['roles'][role]['lines'][-1] == (
                '2 spec files have changes that are not committed.'), role
            assert report['roles'][role]['specs_uncommitted'] == 2

    # purlin: drift PROOF-48
    def test_specs_all_committed_print_no_such_line(self, tmp_path):
        root = _edited_spec(tmp_path)
        _write(os.path.join(root, 'specs', 'shop', 'cart.md'),
               _spec('cart', {'RULE-1': 'Holds items'}))
        _commit(root, 'feat: both specs')
        report = _report(root, since='1')
        for role in ('pm', 'eng', 'qa'):
            assert not [line for line in report['roles'][role]['lines']
                        if 'not committed' in line], role
            assert report['roles'][role]['specs_uncommitted'] == 0


def _edited_spec(tmp_path):
    """A project of 2 commits whose spec `login` is edited and not
    committed."""
    root = _repo(str(tmp_path / 'proj'), LOGIN_FILES)
    _change(root, {'a.txt': '1\n'})
    _write(os.path.join(root, 'specs', 'auth', 'login.md'), LOGIN + '\n')
    return root


# ---------------------------------------------------------------------------
# RULE-18 and RULE-19: the shape of the answer
# ---------------------------------------------------------------------------

def _pulled_source_change(tmp_path):
    """A checkout that pulled one change to a source file of `login`."""
    _up, checkout, _before = _pulled(
        tmp_path, LOGIN_FILES,
        [{'src/auth/login.py': 'def login():\n    return 2\n'}])
    return checkout


class TestReportShape:

    # purlin: drift PROOF-27
    def test_the_report_carries_the_range_and_three_roles(self, tmp_path):
        report = _report(_pulled_source_change(tmp_path))

        assert sorted(report) == ['roles', 'since'], sorted(report)
        assert sorted(report['since']) == [
            'action', 'commits', 'from', 'line', 'to', 'when'], report['since']
        assert sorted(report['roles']) == ['eng', 'pm', 'qa']

    # purlin: drift PROOF-49
    def test_each_view_carries_its_fixed_keys(self, tmp_path):
        report = _report(_pulled_source_change(tmp_path))

        assert sorted(report['roles']['pm']) == [
            'lines', 'rules_added', 'rules_changed', 'rules_removed',
            'specs_uncommitted']
        assert sorted(report['roles']['eng']) == [
            'anchors_behind', 'code_changed', 'lines', 'out_of_date',
            'rules_without_test', 'specs_uncommitted', 'unscoped']
        assert sorted(report['roles']['qa']) == [
            'left', 'lines', 'not_audited', 'specs_uncommitted',
            'tests_changed']

    # purlin: drift PROOF-50
    def test_the_qa_role_narrows_the_answer_to_its_view(self, tmp_path,
                                                        monkeypatch):
        checkout = _pulled_source_change(tmp_path)
        # The reflog names its times relative to now, so two reads a moment
        # apart can straddle a second and read `1 second ago` and `0 seconds
        # ago`. Both reports here see the one read, so they are compared
        # whole, relative time included.
        read = purlin_drift._reflog
        seen = {}

        def read_once(root):
            if root not in seen:
                seen[root] = read(root)
            return seen[root]

        monkeypatch.setattr(purlin_drift, '_reflog', read_once)
        report = _report(checkout)
        narrowed = json.loads(purlin_drift.drift(checkout, role='qa'))
        assert sorted(narrowed) == ['role', 'since', 'view'], sorted(narrowed)
        assert narrowed['role'] == 'qa'
        assert narrowed['view'] == report['roles']['qa']
        assert narrowed['since'] == report['since']

    # purlin: drift PROOF-28
    def test_the_report_text_has_no_indent_and_no_space_after_a_separator(
            self, tmp_path):
        root = _repo(str(tmp_path / 'proj'), LOGIN_FILES)
        _change(root, {'src/auth/login.py': 'def login():\n    return 2\n'})

        text = purlin_drift.drift(root, since='1')

        assert '\n  ' not in text, "payload still carries indentation"
        assert '": ' not in text, "payload still carries a space after the key separator"
        assert ', "' not in text, "payload still carries a space after the item separator"
        data = json.loads(text)
        assert sorted(data) == ['roles', 'since'], sorted(data)
        assert len(text) < len(json.dumps(data, indent=2))
