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
    config = {} if gate is None else {'gate': gate}
    _write(os.path.join(root, '.purlin', 'config.json'), json.dumps(config))
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


# The marker a test file carries, built so this file carries none itself.
_MARK = '@pytest.mark.' + 'proof'


def _marked(*features):
    return ''.join('%s("%s", "PROOF-1", "RULE-1")\ndef test_%s():\n    pass\n\n'
                   % (_MARK, name, index) for index, name in enumerate(features))


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

    @pytest.mark.proof("drift", "PROOF-1", "RULE-1")
    def test_hostile_since_is_refused_before_any_subprocess(self, tmp_path,
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

    @pytest.mark.proof("drift", "PROOF-2", "RULE-1")
    def test_a_count_is_accepted_and_reaches_git(self, tmp_path, monkeypatch):
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

    @pytest.mark.proof("drift", "PROOF-3", "RULE-2")
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

    @pytest.mark.proof("drift", "PROOF-4", "RULE-2")
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

    @pytest.mark.proof("drift", "PROOF-5", "RULE-2")
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

    @pytest.mark.proof("drift", "PROOF-6", "RULE-2")
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

    @pytest.mark.proof("drift", "PROOF-7", "RULE-2")
    def test_the_newest_action_wins_and_a_reset_counts(self, tmp_path):
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

class TestTheLastTwentyCommits:

    @pytest.mark.proof("drift", "PROOF-8", "RULE-3")
    def test_a_clone_or_no_action_measures_the_last_twenty(self, tmp_path):
        made = _repo(str(tmp_path / 'made'), {'a.txt': '0\n'})
        for index in range(24):
            _change(made, {'a.txt': '%d\n' % (index + 1)})
        cloned = _clone(made, str(tmp_path / 'cloned'))

        since = _report(cloned)['since']
        assert since['action'] == 'clone', since
        assert since['from'] == _sha(cloned, 'HEAD~20'), since
        assert since['commits'] == 20, since

        since = _report(made)['since']
        assert since['action'] is None, since
        assert since['from'] == _sha(made, 'HEAD~20'), since
        assert since['commits'] == 20, since

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

    @pytest.mark.proof("drift", "PROOF-9", "RULE-4")
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

    @pytest.mark.proof("drift", "PROOF-10", "RULE-4")
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

    @pytest.mark.proof("drift", "PROOF-11", "RULE-5")
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


# ---------------------------------------------------------------------------
# RULE-6: the PM view
# ---------------------------------------------------------------------------

class TestPmView:

    @pytest.mark.proof("drift", "PROOF-12", "RULE-6")
    def test_rules_added_changed_and_removed(self, tmp_path):
        cart = _spec('cart', {'RULE-1': 'Holds items',
                              'RULE-2': 'Empties on checkout'})
        other = _spec('other', {'RULE-1': 'Stays the same'})
        _up, checkout, _before = _pulled(
            tmp_path,
            {'specs/auth/login.md': LOGIN, 'specs/shop/cart.md': cart,
             'specs/a/other.md': other},
            [{'specs/auth/login.md': _spec(
                'login', {'RULE-1': 'Signs a person in with a passkey',
                          'RULE-2': 'Refuses a wrong password',
                          'RULE-3': 'Locks after five tries'},
                scope='src/auth/'),
              'specs/shop/cart.md': _spec('cart', {'RULE-1': 'Holds items'}),
              'specs/a/other.md': None,
              'specs/b/other.md': other}])
        report = _report(checkout)

        assert _lines(report, 'pm') == [
            '1 rule added: login RULE-3.',
            '1 rule changed: login RULE-1.',
            '1 rule removed: cart RULE-2.'], _lines(report, 'pm')
        pm = report['roles']['pm']
        assert pm['rules_added'] == {'login': ['RULE-3']}, pm
        assert pm['rules_changed'] == {'login': ['RULE-1']}, pm
        assert pm['rules_removed'] == {'cart': ['RULE-2']}, pm

    @pytest.mark.proof("drift", "PROOF-13", "RULE-6")
    def test_no_rule_moved(self, tmp_path):
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
        'schema': 'purlin-evidence/1', 'feature': feature,
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

    @pytest.mark.proof("drift", "PROOF-14", "RULE-7")
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

    @pytest.mark.proof("drift", "PROOF-15", "RULE-8")
    def test_changed_files_under_no_scope(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES,
            [{'src/x.py': 'x = 1\n', 'src/y.py': 'y = 1\n',
              'specs/auth/login.md': LOGIN + '\n',
              '.purlin/config.json': '{"gate": "passed"}',
              'tests/test_login.py': _marked('login')}])
        report = _report(checkout)

        assert ("2 changed files are under no spec's scope: src/x.py, "
                "src/y.py.") in _lines(report, 'eng'), _lines(report, 'eng')
        assert report['roles']['eng']['unscoped'] == ['src/x.py', 'src/y.py']

    @pytest.mark.proof("drift", "PROOF-16", "RULE-9")
    def test_rules_with_no_test(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES, [{'README.md': 'login\n'}])
        report = _report(checkout)
        assert '2 rules have no test: login RULE-1, RULE-2.' in \
            _lines(report, 'eng'), _lines(report, 'eng')
        assert report['roles']['eng']['rules_without_test'] == {
            'login': ['RULE-1', 'RULE-2']}

        _evidence_file(checkout, 'login', ['RULE-1', 'RULE-2'])
        report = _report(checkout)
        assert not [line for line in _lines(report, 'eng')
                    if 'no test' in line], _lines(report, 'eng')
        assert report['roles']['eng']['rules_without_test'] == {}

    @pytest.mark.proof("drift", "PROOF-23", "RULE-14")
    def test_features_out_of_date(self, tmp_path):
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
# RULE-10 to RULE-13: anchors behind their source
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


def _pinned_project(root, bare_path, anchor_name, pinned_sha, rules=None):
    """A project whose one anchor is pinned to `pinned_sha` of `bare_path`."""
    rules = rules or {'RULE-1': 'External constraint one'}
    text = _spec(anchor_name, rules, kind='Anchor').replace(
        '\n\n## Rules', '\n\n> Source: %s\n> Pinned: %s\n\n## Rules'
        % (bare_path, pinned_sha), 1)
    return _repo(root, {'specs/_anchors/%s.md' % anchor_name: text})


def _anchor_rows(root):
    return _report(root)['roles']['eng']['anchors_behind']


class TestAnchorsBehind:

    @pytest.mark.proof("drift", "PROOF-17", "RULE-10")
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

    @pytest.mark.proof("drift", "PROOF-18", "RULE-10")
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

    @pytest.mark.proof("drift", "PROOF-19", "RULE-10")
    def test_a_pin_is_unpinned_an_error_or_not_reported_at_all(self,
                                                               tmp_path):
        root = _repo(str(tmp_path / 'proj'))

        unpinned = purlin_drift.check_pin(
            root, 'https://github.com/acme/p.git', None)
        assert unpinned == {'status': 'unpinned', 'remote_sha': None}, unpinned

        missing = os.path.join(str(tmp_path), 'nope.git')
        unreadable = purlin_drift.check_pin(root, missing, 'abc1234')
        assert unreadable['status'] == 'error', unreadable
        assert unreadable['remote_sha'] is None, unreadable
        assert 'nope.git' in unreadable['error'], unreadable

        bare = os.path.join(str(tmp_path), 'anchor.git')
        sha = _create_bare_repo(bare, 'policy.md', '# policy v1')
        current = purlin_drift.check_pin(root, bare, sha)
        assert current == {'status': 'current', 'remote_sha': sha}, current

        features = {'policy': {'is_anchor': True, 'source': bare,
                               'pinned': sha}}
        assert purlin_drift.pin_report(root, features) == [], (
            'an anchor still at its pin must not be reported')

    @pytest.mark.proof("drift", "PROOF-20", "RULE-11")
    def test_a_source_that_is_not_safe_is_refused_before_any_process(
            self, tmp_path, monkeypatch):
        root = _repo(str(tmp_path / 'proj'))
        calls = []
        real_run = subprocess.run

        def spy(args, *rest, **kwargs):
            calls.append(list(args))
            return real_run(args, *rest, **kwargs)

        monkeypatch.setattr(purlin_drift.subprocess, 'run', spy)
        for value, reason in (
                ('--upload-pack=/bin/echo', 'begins with "-"'),
                ('ext::sh -c id', 'names an ext:: transport'),
                ('fd::7', 'names an fd:: transport'),
                ('/srv/anchors\x00.git', 'contains a NUL byte'),
                ('/srv/anchors.git\n--upload-pack=x', 'contains a newline')):
            assert purlin_drift.source_url_is_safe(value) == (False, reason), \
                value
            row = purlin_drift.check_pin(root, value, 'abc1234')
            assert row == {'status': 'error', 'remote_sha': None,
                           'error': 'rejected source url',
                           'reason': reason}, row
        assert calls == [], calls
        assert purlin_drift.source_url_is_safe(
            'https://github.com/acme/p.git') == (True, '')

    @pytest.mark.proof("drift", "PROOF-21", "RULE-12")
    def test_one_ls_remote_per_source_per_run(self, tmp_path, monkeypatch):
        root = _repo(str(tmp_path / 'proj'))
        calls = []
        real_run = subprocess.run

        def spy(args, *rest, **kwargs):
            calls.append(list(args))
            return real_run(args, *rest, **kwargs)

        monkeypatch.setattr(purlin_drift.subprocess, 'run', spy)
        cache = {}
        for _ in range(3):
            purlin_drift.check_pin(root, 'https://github.invalid/acme/p.git',
                                   'abc1234', cache)
        assert len([c for c in calls if 'ls-remote' in c]) == 1, calls

    @pytest.mark.proof("drift", "PROOF-22", "RULE-13")
    def test_the_row_names_the_spec_not_the_repository(self, tmp_path):
        bare = str(tmp_path / 'anchor.git')
        first = _create_bare_repo(bare, 'constraints.md', '# constraints v1')
        root = _pinned_project(str(tmp_path / 'proj'), bare, 'local_security',
                               first)
        _advance_bare_repo(bare, 'constraints.md', '# constraints v2')

        rows = [row for row in _anchor_rows(root) if row['status'] == 'behind']
        assert [row['anchor'] for row in rows] == ['local_security'], rows
        for row in rows:
            assert row['anchor'] not in (bare, 'constraints.md'), row


# ---------------------------------------------------------------------------
# RULE-15 and RULE-16: the QA view
# ---------------------------------------------------------------------------

class TestQaView:

    @pytest.mark.proof("drift", "PROOF-24", "RULE-15")
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

    @pytest.mark.proof("drift", "PROOF-25", "RULE-16")
    def test_signatures_stale_and_the_queue(self, tmp_path):
        from purlin import payload as purlin_payload

        def spec(first):
            return _spec('login', {'RULE-1': first,
                                   'RULE-2': 'Looks right on a phone'},
                         scope='src/auth/',
                         proofs={'PROOF-1': ('RULE-1', 'Sign in and see 1'),
                                 'PROOF-2': ('RULE-2',
                                             'Look at it on a phone @manual')})

        root = _repo(str(tmp_path / 'proj'),
                     {'specs/auth/login.md': spec('Signs a person in'),
                      'src/auth/login.py': 'x = 1\n'}, gate='strong')
        rule = next(r for r in purlin_payload.build_payload(root)[
            'features'][0]['rules'] if r['id'] == 'RULE-1')
        _write(os.path.join(root, 'specs', 'auth', 'login.signatures',
                            'RULE-1.%s.test.json' % rule['rule_hash'][:8]),
               json.dumps({key: rule[key] for key in (
                   'rule_hash', 'proof_hash', 'test_hash', 'audit_hash')}))
        _commit(root, 'chore: sign RULE-1')
        _change(root, {'specs/auth/login.md': spec('Signs a person in fast')})
        report = _report(root, since='1')

        assert _lines(report, 'qa') == [
            '1 signature is stale: login RULE-1 (rule text changed).',
            'Queue: 1 rule. 1 hand check, 0 signatures.'], _lines(report, 'qa')
        qa = report['roles']['qa']
        assert qa['signatures_stale'] == [
            {'feature': 'login', 'rule': 'RULE-1',
             'reason': 'rule text changed'}], qa
        assert qa['queue'] == {'rules': 1, 'hand_checks': 1,
                               'signatures': 0}, qa

        _write(os.path.join(root, '.purlin', 'config.json'),
               '{"gate": "passed"}')
        _commit(root, 'chore: the gate is passed')
        assert _lines(_report(root, since='1'), 'qa') == []


# ---------------------------------------------------------------------------
# RULE-17: spec files not committed
# ---------------------------------------------------------------------------

class TestSpecsNotCommitted:

    @pytest.mark.proof("drift", "PROOF-26", "RULE-17")
    def test_every_view_ends_with_the_count(self, tmp_path):
        root = _repo(str(tmp_path / 'proj'), LOGIN_FILES)
        _change(root, {'a.txt': '1\n'})
        _write(os.path.join(root, 'specs', 'auth', 'login.md'), LOGIN + '\n')
        report = _report(root, since='1')
        for role in ('pm', 'eng', 'qa'):
            assert report['roles'][role]['lines'][-1] == (
                '1 spec file has changes that are not committed.'), role
            assert report['roles'][role]['specs_uncommitted'] == 1

        _write(os.path.join(root, 'specs', 'shop', 'cart.md'),
               _spec('cart', {'RULE-1': 'Holds items'}))
        report = _report(root, since='1')
        for role in ('pm', 'eng', 'qa'):
            assert report['roles'][role]['lines'][-1] == (
                '2 spec files have changes that are not committed.'), role

        _commit(root, 'feat: both specs')
        report = _report(root, since='1')
        for role in ('pm', 'eng', 'qa'):
            assert not [line for line in report['roles'][role]['lines']
                        if 'not committed' in line], role
            assert report['roles'][role]['specs_uncommitted'] == 0


# ---------------------------------------------------------------------------
# RULE-18 and RULE-19: the shape of the answer
# ---------------------------------------------------------------------------

class TestReportShape:

    @pytest.mark.proof("drift", "PROOF-27", "RULE-18")
    def test_the_report_the_views_and_the_narrowed_answer(self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES,
            [{'src/auth/login.py': 'def login():\n    return 2\n'}])
        report = _report(checkout)

        assert sorted(report) == ['roles', 'since'], sorted(report)
        assert sorted(report['since']) == [
            'action', 'commits', 'from', 'line', 'to', 'when'], report['since']
        assert sorted(report['roles']) == ['eng', 'pm', 'qa']
        assert sorted(report['roles']['pm']) == [
            'lines', 'rules_added', 'rules_changed', 'rules_removed',
            'specs_uncommitted']
        assert sorted(report['roles']['eng']) == [
            'anchors_behind', 'code_changed', 'lines', 'out_of_date',
            'rules_without_test', 'specs_uncommitted', 'unscoped']
        assert sorted(report['roles']['qa']) == [
            'lines', 'not_audited', 'queue', 'signatures_stale',
            'specs_uncommitted', 'tests_changed']

        narrowed = json.loads(purlin_drift.drift(checkout, role='qa'))
        assert sorted(narrowed) == ['role', 'since', 'view'], sorted(narrowed)
        assert narrowed['role'] == 'qa'
        assert narrowed['view'] == report['roles']['qa']
        assert narrowed['since'] == report['since']

    @pytest.mark.proof("drift", "PROOF-28", "RULE-19")
    def test_payload_carries_no_pretty_printing_whitespace(self, tmp_path):
        root = _repo(str(tmp_path / 'proj'), LOGIN_FILES)
        _change(root, {'src/auth/login.py': 'def login():\n    return 2\n'})

        text = purlin_drift.drift(root, since='1')

        assert '\n  ' not in text, "payload still carries indentation"
        assert '": ' not in text, "payload still carries a space after the key separator"
        data = json.loads(text)
        assert sorted(data) == ['roles', 'since'], sorted(data)
        assert len(text) < len(json.dumps(data, indent=2))
