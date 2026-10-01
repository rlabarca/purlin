"""Tests for the drift report (specs/mcp/drift.md).

Every test builds real git repositories in a temporary directory and produces
each action git logs for real: a pull from a second repository, a merge, a
checkout and a clone. An anchor's source is a bare repository on disk.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
sys.path.insert(0, os.path.dirname(__file__))
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


def _repo(root, files=None):
    """A git repository made in place, its first commit holding `files`."""
    os.makedirs(root, exist_ok=True)
    _write(os.path.join(root, '.purlin', 'config.json'), _config())
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


def _pulled(tmp_path, start, changes):
    """`(upstream, checkout, before)`: the checkout pulled `changes`.

    The upstream holds `start`; the checkout is cloned from it, then the
    upstream commits each of `changes` in turn and the checkout pulls them.
    `before` is where the checkout stood before the pull.
    """
    upstream = _repo(str(tmp_path / 'upstream'), start)
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


def _config():
    return json.dumps({'version': '0.10.0', 'tests': TESTS})




def _report(root, since=None):
    return json.loads(purlin_drift.drift(root, since=since))


def _view(report):
    return report['view']


def _lines(report):
    """The view's lines after the first, which names the range."""
    return report['view']['lines'][1:]


LOGIN = _spec('login', {'RULE-1': 'Signs a person in',
                        'RULE-2': 'Refuses a wrong password'},
              scope='src/auth/')
LOGIN_FILES = {'specs/auth/login.md': LOGIN,
               'src/auth/login.py': 'def login():\n    return 1\n',
               'src/auth/token.py': 'def token():\n    return 1\n'}


def _files_outside_git(root):
    """`{path: bytes}` for every file of the checkout outside `.git`."""
    found = {}
    for folder, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name != '.git']
        for name in files:
            path = os.path.join(folder, name)
            with open(path, 'rb') as handle:
                found[os.path.relpath(path, root)] = handle.read()
    return found


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


# ---------------------------------------------------------------------------
# RULE-1: the `since` argument
# ---------------------------------------------------------------------------

class TestSinceValidation:

    # purlin: drift PROOF-1
    def test_a_since_that_is_no_count_or_date_is_refused(self, tmp_path,
                                                         monkeypatch):
        root = _repo(str(tmp_path / 'proj'))
        calls = _spied(monkeypatch)
        refused = _report(root, since='--output=/tmp/x')

        assert refused['error'] == 'rejected since', refused
        assert refused['reason'] == (
            'since must be a number of commits (digits only) or a YYYY-MM-DD '
            'date; refusing to pass "--output=/tmp/x" to git'), refused['reason']
        assert calls == [], calls


# ---------------------------------------------------------------------------
# RULE-2: the last git action that brought changes in
# ---------------------------------------------------------------------------

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

    # purlin: drift PROOF-29
    def test_a_merge_of_a_two_commit_branch_resolved_by_hand_runs_3_commits_from_main(
            self, tmp_path):
        root, before = _merged_with_conflict(tmp_path)

        since = _report(root)['since']
        assert since['action'] == 'merge', since
        assert since['from'] == before, since
        assert since['to'] == _sha(root), since
        assert since['commits'] == 3, since

    # purlin: drift PROOF-86
    def test_a_branch_made_at_head_after_a_pull_leaves_the_range_at_the_pull(
            self, tmp_path):
        _up, checkout, before = _pulled(
            tmp_path, {'a.txt': '0\n'}, [{'a.txt': '1\n'}, {'a.txt': '2\n'}])
        _git(['checkout', '-q', '-b', 'topic'], checkout)
        subjects = _git(['reflog', 'show', '--format=%gs', 'HEAD'],
                        checkout).stdout
        assert subjects.splitlines()[0].startswith('checkout:'), subjects

        since = _report(checkout)['since']
        assert since['action'] == 'pull', since
        assert since['from'] == before, since
        assert since['to'] == _sha(checkout), since
        assert since['commits'] == 2, since


# ---------------------------------------------------------------------------
# RULE-3: the clone
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


# ---------------------------------------------------------------------------
# RULE-4: `since` overrides the log
# ---------------------------------------------------------------------------

class TestSinceOverrides:

    # purlin: drift PROOF-9
    def test_since_3_after_a_pull_of_1_runs_the_last_3_commits(self, tmp_path):
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
        assert since['to'] == _sha(checkout), since
        assert since['line'].startswith('The last 3 commits ('), since

    # purlin: drift PROOF-10
    def test_since_a_date_runs_the_last_2_of_3_dated_commits(self, tmp_path):
        root = str(tmp_path / 'proj')
        os.makedirs(root)
        _write(os.path.join(root, '.purlin', 'config.json'), _config())
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
        assert since['to'] == shas[2], since
        assert since['line'].startswith('Since 2026-02-15 ('), since


# ---------------------------------------------------------------------------
# RULE-6: the rules added, changed and removed
# ---------------------------------------------------------------------------

class TestRules:

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
                scope='src/auth/',
                proofs={'PROOF-1': ('RULE-1', 'Call it and see 1'),
                        'PROOF-2': ('RULE-2', 'Call it and see 1')}),
              'specs/shop/cart.md': _spec('cart', {'RULE-1': 'Holds items'})}])
        report = _report(checkout)

        assert _lines(report) == [
            '1 rule added: login RULE-3.',
            '1 rule changed: login RULE-1.',
            '1 rule removed: cart RULE-2.'], _lines(report)
        view = _view(report)
        assert view['rules_added'] == {'login': ['RULE-3']}, view
        assert view['rules_changed'] == {'login': ['RULE-1']}, view
        assert view['rules_removed'] == {'cart': ['RULE-2']}, view

    # purlin: drift PROOF-38
    def test_a_spec_moved_with_its_rules_unchanged_is_named_nowhere(
            self, tmp_path):
        other = _spec('other', {'RULE-1': 'Stays the same'})
        _up, checkout, _before = _pulled(
            tmp_path, {'specs/a/other.md': other},
            [{'specs/a/other.md': None, 'specs/b/other.md': other}])
        report = _report(checkout)

        assert _lines(report) == [
            'No rule was added, changed or removed since your last pull.'], \
            _lines(report)


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


def _one_anchor(tmp_path, monkeypatch, source, pinned='abc1234'):
    """`(report, calls)`: drift's report on a project whose one anchor,
    `policy`, names `source`, and every command the report started."""
    root = _repo(str(tmp_path / 'proj'), {
        'specs/_anchors/policy.md': _anchor_text('policy', source, pinned)})
    calls = _spied(monkeypatch)
    return _report(root), calls


def _refused(tmp_path, monkeypatch, source, reason):
    """`(report, calls)` for the anchor pinned to `source`, asserting its row
    reads `error` with `reason` and no command was handed that source."""
    report, calls = _one_anchor(tmp_path, monkeypatch, source)
    assert _view(report)['anchors_behind'] == [
        {'anchor': 'policy', 'source': source, 'pinned': 'abc1234',
         'status': 'error', 'error': 'rejected source url',
         'reason': reason}], _view(report)['anchors_behind']
    assert 'remote_sha' not in _view(report)['anchors_behind'][0]
    assert _handed(calls, source) == [], _handed(calls, source)
    return report


class TestAnchorsBehind:

    # purlin: drift PROOF-17
    def test_a_pin_behind_its_source_reads_behind_with_the_new_sha7(self,
                                                                   tmp_path):
        bare = str(tmp_path / 'anchor.git')
        first = _create_bare_repo(bare, 'spec.md', '# spec v1')
        root = _pinned_project(str(tmp_path / 'proj'), bare,
                               'external_anchor', first)
        new_sha = _advance_bare_repo(bare, 'spec.md', '# spec v2')
        report = _report(root)

        rows = _view(report)['anchors_behind']
        assert len(rows) == 1, rows
        assert rows[0]['anchor'] == 'external_anchor', rows
        assert rows[0]['status'] == 'behind', rows
        assert rows[0]['remote_sha'] == new_sha[:7], (rows, new_sha)
        assert ('anchor external_anchor: the pin %s is behind its source, now '
                '%s. Run purlin:anchor sync external_anchor.'
                % (first[:7], new_sha[:7])) in _lines(report), _lines(report)

    # purlin: drift PROOF-88
    def test_a_pin_named_behind_leaves_the_anchor_file_and_this_checkouts_objects(
            self, tmp_path):
        bare = str(tmp_path / 'anchor.git')
        first = _create_bare_repo(bare, 'spec.md', '# spec v1')
        root = _pinned_project(str(tmp_path / 'proj'), bare,
                               'external_anchor', first)
        anchor = os.path.join(root, 'specs', '_anchors', 'external_anchor.md')
        with open(anchor, 'rb') as handle:
            before = handle.read()
        new_sha = _advance_bare_repo(bare, 'spec.md', '# spec v2')

        rows = _view(_report(root))['anchors_behind']
        assert [(row['anchor'], row['status']) for row in rows] == [
            ('external_anchor', 'behind')], rows
        with open(anchor, 'rb') as handle:
            assert handle.read() == before
        held = _git(['cat-file', '-e', new_sha], root, check=False)
        assert held.returncode != 0, 'the checkout holds %s' % new_sha

    # purlin: drift PROOF-19
    def test_a_source_with_no_pin_reads_unpinned(self, tmp_path,
                                                 monkeypatch):
        source = 'https://github.com/acme/p.git'
        report, calls = _one_anchor(tmp_path, monkeypatch, source,
                                    pinned=None)

        assert _view(report)['anchors_behind'] == [
            {'anchor': 'policy', 'source': source, 'pinned': None,
             'status': 'unpinned'}], _view(report)['anchors_behind']
        assert ('anchor policy: names a source and no pin. Run purlin:anchor '
                'sync policy.') in _lines(report), _lines(report)
        assert _handed(calls, source) == [], _handed(calls, source)

    # purlin: drift PROOF-40
    def test_a_source_path_with_no_repository_reads_error_naming_it(
            self, tmp_path, monkeypatch):
        missing = os.path.join(str(tmp_path), 'nope.git')
        report, _calls = _one_anchor(tmp_path, monkeypatch, missing)

        rows = _view(report)['anchors_behind']
        assert len(rows) == 1, rows
        assert rows[0]['anchor'] == 'policy', rows
        assert rows[0]['status'] == 'error', rows
        assert 'remote_sha' not in rows[0], rows
        assert missing in rows[0]['error'], rows
        assert ('anchor policy: the source could not be read (%s). Check its '
                '> Source: line, then run purlin:anchor sync policy.'
                % rows[0]['error']) in _lines(report), _lines(report)


# ---------------------------------------------------------------------------
# RULE-20: a source that names no repository
# ---------------------------------------------------------------------------

class TestSourceNamesNoRepository:

    # purlin: drift PROOF-56
    def test_a_text_file_in_the_project_reads_error(self, tmp_path,
                                                    monkeypatch):
        root = _repo(str(tmp_path / 'proj'), {
            'specs/_anchors/refunds.md': _anchor_text('refunds', 'policy.txt',
                                                      'abc1234'),
            'policy.txt': 'Refunds within 30 days.\n'})
        calls = _spied(monkeypatch)
        report = _report(root)

        rows = _view(report)['anchors_behind']
        assert [(row['anchor'], row['status']) for row in rows] == [
            ('refunds', 'error')], rows
        lines = [line for line in _lines(report)
                 if line.startswith("anchor refunds: its source, policy.txt, is "
                                    "not a spec in Purlin's format kept in a "
                                    "git repository")]
        assert len(lines) == 1, _lines(report)
        assert 'purlin:spec refunds' in lines[0], lines
        assert _handed(calls, 'policy.txt') == [], calls


# ---------------------------------------------------------------------------
# RULE-11: a source that is not safe is refused before any process starts
# ---------------------------------------------------------------------------

class TestUnsafeSources:

    # purlin: drift PROOF-20
    def test_a_source_that_begins_with_a_dash_is_refused(self, tmp_path,
                                                         monkeypatch):
        report = _refused(tmp_path, monkeypatch, '--upload-pack=/bin/echo',
                          'begins with "-"')
        assert ('anchor policy: the source could not be read (begins with '
                '"-"). Check its > Source: line, then run purlin:anchor sync '
                'policy.') in _lines(report), _lines(report)

    # purlin: drift PROOF-42
    def test_a_source_naming_the_ext_transport_is_refused(self, tmp_path,
                                                          monkeypatch):
        _refused(tmp_path, monkeypatch, 'ext::sh -c id',
                 'names an ext:: transport')

    # purlin: drift PROOF-44
    def test_a_source_carrying_a_nul_byte_is_refused(self, tmp_path,
                                                     monkeypatch):
        _refused(tmp_path, monkeypatch, '/srv/anchors\x00.git',
                 'contains a NUL byte')


# ---------------------------------------------------------------------------
# RULE-31 and RULE-32: a number written twice, and the default branch's age
# ---------------------------------------------------------------------------

def _login_with(proofs):
    """`login` of 2 rules whose proofs are `{PROOF-N: text}`, each of RULE-1."""
    return _spec('login', {'RULE-1': 'Signs a person in',
                           'RULE-2': 'Refuses a wrong password'},
                 scope='src/auth/',
                 proofs={pid: ('RULE-1', text) for pid, text in proofs.items()})


LOGIN_TWICE = _spec('login', {'RULE-1': 'Signs a person in'},
                    proofs={'PROOF-1': ('RULE-1', 'One'),
                            'PROOF-2': ('RULE-1', 'Two'),
                            'PROOF-3': ('RULE-1', 'Three')})


def _with_proof(spec, *lines):
    return spec + ''.join('- %s\n' % line for line in lines)


def _merged_twice(tmp_path):
    """A checkout whose merge of `origin/main` left `login` writing
    `PROOF-4` twice: `A` from `origin/main`, `B` from its own commit."""
    upstream = _repo(str(tmp_path / 'upstream'),
                     {'specs/auth/login.md': LOGIN_TWICE})
    checkout = _clone(upstream, str(tmp_path / 'checkout'))
    _change(upstream, {'specs/auth/login.md': _with_proof(
        LOGIN_TWICE, 'PROOF-4 (RULE-1): A')})
    _change(checkout, {'specs/auth/login.md': _with_proof(
        LOGIN_TWICE, 'PROOF-4 (RULE-1): B')})
    stopped = _git(['pull', '-q', '--no-edit'], checkout, check=False)
    assert stopped.returncode != 0, stopped
    _write(os.path.join(checkout, 'specs', 'auth', 'login.md'), _with_proof(
        LOGIN_TWICE, 'PROOF-4 (RULE-1): A', 'PROOF-4 (RULE-1): B'))
    _git(['add', '-A'], checkout)
    _git(['commit', '-q', '--no-edit'], checkout)
    return checkout


class TestNumbersWrittenTwice:

    # purlin: drift PROOF-70
    def test_the_line_on_the_default_branch_keeps_the_number(self, tmp_path):
        report = _report(_merged_twice(tmp_path))
        assert ('login: PROOF-4 is written twice. The line on origin/main keeps '
                'PROOF-4; renumber the other to PROOF-5 and move its test '
                'comments with it: "B".') in _lines(report), _lines(report)

    # purlin: drift PROOF-71
    def test_proof_7_twice_with_neither_line_on_origin_main_renumbers_to_8(
            self, tmp_path):
        upstream = _repo(str(tmp_path / 'upstream'),
                         {'specs/auth/login.md': LOGIN_TWICE})
        checkout = _clone(upstream, str(tmp_path / 'checkout'))
        _change(checkout, {'specs/auth/login.md': _with_proof(
            LOGIN_TWICE, 'PROOF-4 (RULE-1): Four', 'PROOF-5 (RULE-1): Five',
            'PROOF-6 (RULE-1): Six', 'PROOF-7 (RULE-1): X',
            'PROOF-7 (RULE-1): Y')})
        report = _report(checkout)
        assert ('login: PROOF-7 is written twice, and neither line is on '
                'origin/main. The one that reaches origin/main first keeps '
                'PROOF-7; renumber the other to PROOF-8 and move its test '
                'comments with it.') in _lines(report), _lines(report)

    # purlin: drift PROOF-85
    def test_a_number_written_twice_by_a_merge_is_never_a_proof_changed(
            self, tmp_path):
        report = _report(_merged_twice(tmp_path))
        twice = [(entry['feature'], entry['id'])
                 for entry in _view(report)['numbers_twice']]
        assert twice == [('login', 'PROOF-4')], twice
        assert [line for line in _lines(report)
                if line.startswith('login: PROOF-4 is written twice')], \
            _lines(report)
        assert not [line for line in _lines(report)
                    if line.startswith('login PROOF-4 changed')], _lines(report)
        assert _view(report)['proofs_changed'] == []

    # purlin: drift PROOF-73
    def test_origin_main_fetched_three_days_ago_says_so(self, tmp_path):
        checkout = _merged_twice(tmp_path)
        when = int(time.time()) - 3 * 86400 - 120
        fetched = _sha(checkout, 'refs/remotes/origin/main')
        # Git logs a ref's update only when its value moves, so the ref steps
        # back one commit and forward again, both at that time.
        for sha in (_sha(checkout, fetched + '^'), fetched):
            _git(['update-ref', '-m', 'fetch: long ago',
                  'refs/remotes/origin/main', sha],
                 checkout, env={'GIT_COMMITTER_DATE': '@%d +0000' % when})
        report = _report(checkout)
        assert ('origin/main was last fetched 3 days ago, and drift does not '
                'fetch. Run git fetch, then purlin:drift again.') in \
            _lines(report), _lines(report)
        assert _view(report)['default_branch']['ref'] == 'origin/main'


# ---------------------------------------------------------------------------
# RULE-33 and RULE-35: a test comment whose proof's wording changed
# ---------------------------------------------------------------------------

TEST_FOUR = '# purlin: login PROOF-4\ndef test_four():\n    assert 4\n'


def _comment_pulled(tmp_path, proofs_after):
    """`(checkout, sha7 of the commit that wrote the test)`: a checkout
    that pulled `login`'s proofs from `PROOF-4` reading `A` to
    `proofs_after`; its test file marks `login PROOF-4` on line 1."""
    _up, checkout, start = _pulled(
        tmp_path, {'specs/auth/login.md': _login_with(
            {'PROOF-1': 'One', 'PROOF-4': 'A'}),
            'tests/test_login.py': TEST_FOUR},
        [{'specs/auth/login.md': _login_with(proofs_after)}])
    return checkout, start[:7]


def _names_line_1(report):
    return [line for line in _lines(report)
            if line.startswith('tests/test_login.py:1 ')]


class TestCommentsChanged:

    # purlin: drift PROOF-75
    def test_a_test_marked_while_proof_4_read_a_is_named_after_a_pull_rewords_it(
            self, tmp_path):
        checkout, sha = _comment_pulled(tmp_path, {'PROOF-1': 'One',
                                                   'PROOF-4': 'B'})
        assert ('tests/test_login.py:1 names login PROOF-4, whose wording '
                'changed after the test was last changed in %s: it read "A" '
                'and now reads "B". Run purlin:build login to make the test '
                'show it; the line clears once the test changes.' % sha) in \
            _lines(_report(checkout)), _lines(_report(checkout))

    # purlin: drift PROOF-76
    def test_a_pull_that_puts_a_under_proof_6_says_move_the_comment_there(
            self, tmp_path):
        checkout, _sha7 = _comment_pulled(tmp_path, {
            'PROOF-1': 'One', 'PROOF-4': 'B', 'PROOF-6': 'A'})
        lines = _names_line_1(_report(checkout))
        assert len(lines) == 1, lines
        assert lines[0].endswith(
            'it read "A" and now reads "B". Its old wording is now PROOF-6: '
            'move the comment there.'), lines

    # purlin: drift PROOF-82
    def test_a_test_changed_in_a_commit_after_the_pull_is_not_named(
            self, tmp_path):
        checkout, _sha7 = _comment_pulled(tmp_path, {'PROOF-1': 'One',
                                                     'PROOF-4': 'B'})
        _change(checkout, {'tests/test_login.py': TEST_FOUR.replace(
            'assert 4', 'assert 4 == 4')}, 'test(login): PROOF-4 shows B')
        assert _names_line_1(_report(checkout)) == []

    # purlin: drift PROOF-83
    def test_a_test_changed_and_not_committed_is_not_named(self, tmp_path):
        checkout, _sha7 = _comment_pulled(tmp_path, {'PROOF-1': 'One',
                                                     'PROOF-4': 'B'})
        _write(os.path.join(checkout, 'tests', 'test_login.py'),
               TEST_FOUR.replace('assert 4', 'assert 4 == 4'))
        assert _git(['status', '--porcelain'], checkout).stdout.strip() == \
            'M tests/test_login.py'
        assert _names_line_1(_report(checkout)) == []

    # purlin: drift PROOF-84
    def test_a_commit_that_rewrites_only_the_comment_line_leaves_it_named(
            self, tmp_path):
        checkout, _sha7 = _comment_pulled(tmp_path, {'PROOF-1': 'One',
                                                     'PROOF-4': 'B'})
        _change(checkout, {'tests/test_login.py': TEST_FOUR.replace(
            '# purlin: login PROOF-4', '#  purlin:  login PROOF-4')},
            'test(login): the comment respaced')
        lines = _names_line_1(_report(checkout))
        assert len(lines) == 1, lines
        assert lines[0].startswith('tests/test_login.py:1 names login PROOF-4,'), \
            lines


# ---------------------------------------------------------------------------
# RULE-40: drift cannot read the project
# ---------------------------------------------------------------------------

class TestCannotRead:

    # purlin: drift PROOF-58
    def test_a_trailing_comma_answers_the_sentence_alone(self, tmp_path,
                                                         monkeypatch):
        root = _repo(str(tmp_path / 'proj'), LOGIN_FILES)
        _write(os.path.join(root, '.purlin', 'config.json'),
               '{\n  "version": "0.10.0",\n}\n')
        calls = _spied(monkeypatch)

        answer = purlin_drift.drift(root)

        # The JSON reader's own message and line differ between versions of
        # Python, so they are read as any message and any line.
        assert re.match(re.escape('.purlin/config.json cannot be read: ')
                        + r'\S.* at line \d+'
                        + re.escape('. Fix the file by hand; nothing ran and '
                                    'nothing was saved.') + '$', answer), answer
        assert 'comma' in answer.lower() or 'property name' in answer, answer
        assert calls == [], calls

    # purlin: drift PROOF-61
    def test_a_repository_with_no_commit_is_refused(self, tmp_path):
        root = str(tmp_path / 'proj')
        _write(os.path.join(root, '.purlin', 'config.json'), _config())
        _git(['-c', 'init.defaultBranch=main', 'init', '-q'], root)

        answer = _report(root)

        assert answer == {'error': 'no commits',
                          'reason': 'drift reads git, and HEAD names no commit '
                                    'here'}, answer


# ---------------------------------------------------------------------------
# RULE-41: drift changes nothing
# ---------------------------------------------------------------------------

class TestChangesNothing:

    # purlin: drift PROOF-66
    def test_two_reports_after_a_pull_of_a_spec_and_a_source_file_change_nothing(
            self, tmp_path):
        _up, checkout, _before = _pulled(
            tmp_path, LOGIN_FILES,
            [{'specs/auth/login.md': LOGIN.replace('Signs a person in',
                                                   'Signs a person in by name'),
              'src/auth/login.py': 'def login():\n    return 2\n'}])
        head = _sha(checkout)
        status = _git(['status', '--porcelain'], checkout).stdout
        files = _files_outside_git(checkout)

        for _ in range(2):
            assert _report(checkout)['view']['rules_changed'] == {
                'login': ['RULE-1']}

        assert _sha(checkout) == head
        assert _git(['status', '--porcelain'], checkout).stdout == status
        assert _files_outside_git(checkout) == files

    # purlin: drift PROOF-74
    def test_drift_does_not_fetch(self, tmp_path):
        host = str(tmp_path / 'host.git')
        seed = _repo(str(tmp_path / 'seed'), LOGIN_FILES)
        _git(['clone', '-q', '--bare', seed, host], str(tmp_path))
        mine = _clone(host, str(tmp_path / 'mine'))
        theirs = _clone(host, str(tmp_path / 'theirs'))
        _change(theirs, {'src/auth/login.py': 'x = 2\n'})
        _git(['push', '-q', 'origin', 'HEAD:main'], theirs)
        before = _sha(mine, 'refs/remotes/origin/main')

        _report(mine)

        assert _sha(mine, 'refs/remotes/origin/main') == before
        assert _sha(host, 'main') != before


# ---------------------------------------------------------------------------
# RULE-42: the shape of the answer
# ---------------------------------------------------------------------------

def _pulled_source_change(tmp_path):
    """A checkout that pulled one change to a source file of `login`."""
    _up, checkout, _before = _pulled(
        tmp_path, LOGIN_FILES,
        [{'src/auth/login.py': 'def login():\n    return 2\n'}])
    return checkout


class TestReportShape:

    # purlin: drift PROOF-27
    def test_the_report_carries_since_and_view_and_since_its_six_keys(
            self, tmp_path):
        report = _report(_pulled_source_change(tmp_path))

        assert sorted(report) == ['since', 'view'], sorted(report)
        assert sorted(report['since']) == [
            'action', 'commits', 'from', 'line', 'to', 'when'], report['since']

    # purlin: drift PROOF-49
    def test_the_view_carries_its_eleven_keys(self, tmp_path):
        report = _report(_pulled_source_change(tmp_path))

        assert sorted(report['view']) == [
            'anchors_behind', 'comments_changed', 'default_branch', 'lines',
            'numbers_twice', 'proofs_added', 'proofs_changed', 'proofs_moved',
            'rules_added', 'rules_changed', 'rules_removed']


# ---------------------------------------------------------------------------
# RULE-43: proofs added, changed and moved
# ---------------------------------------------------------------------------

FOUR = {'PROOF-1': 'An age of 150 minutes', 'PROOF-2': 'Two',
        'PROOF-3': 'Three', 'PROOF-4': 'Four'}


def _pulled_proofs(tmp_path, proofs):
    """The report of a checkout that pulled `login`'s proofs from FOUR to `proofs`."""
    _up, checkout, _before = _pulled(
        tmp_path, {'specs/auth/login.md': _login_with(FOUR)},
        [{'specs/auth/login.md': _login_with(proofs)}])
    return _report(checkout)


class TestProofsChanged:

    # purlin: drift PROOF-67
    def test_a_pull_adding_proof_5_and_6_names_both_in_one_line(self, tmp_path):
        report = _pulled_proofs(tmp_path, dict(FOUR, **{'PROOF-5': 'Five',
                                                        'PROOF-6': 'Six'}))
        assert '2 proofs added: login PROOF-5, PROOF-6.' in _lines(report), \
            _lines(report)
        assert _view(report)['proofs_added'] == {
            'login': ['PROOF-5', 'PROOF-6']}

    # purlin: drift PROOF-68
    def test_a_pull_rewording_proof_1_quotes_both_wordings(self, tmp_path):
        report = _pulled_proofs(
            tmp_path, dict(FOUR, **{'PROOF-1': 'An age of 90 minutes'}))
        assert ('login PROOF-1 changed: it read "An age of 150 minutes" and '
                'now reads "An age of 90 minutes".') in _lines(report), \
            _lines(report)
        assert _view(report)['proofs_changed'] == [{
            'feature': 'login', 'id': 'PROOF-1',
            'old': 'An age of 150 minutes', 'new': 'An age of 90 minutes'}]

    # purlin: drift PROOF-69
    def test_a_pull_moving_proof_4s_text_to_proof_6_names_the_move(
            self, tmp_path):
        report = _pulled_proofs(
            tmp_path, dict(FOUR, **{'PROOF-4': 'Another four',
                                    'PROOF-5': 'Five', 'PROOF-6': 'Four'}))
        assert 'login PROOF-4 moved to PROOF-6.' in _lines(report), \
            _lines(report)
        assert _view(report)['proofs_moved'] == [
            {'feature': 'login', 'from': 'PROOF-4', 'to': 'PROOF-6'}]
