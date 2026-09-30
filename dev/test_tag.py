"""The tag `purlin:sign` writes, and the audit hash a signature is made over.

The tag says a version is finished: nothing is left to do at the gate
`signed`, every rule is signed, and every result came from committed work.
Nothing here pushes, and nothing here writes a tag outside the temporary
project the test made.

What each group holds:

*the tag*       the name, the message, the signature and the lines printed
*no tag*        each reason the tag is not written, the line it prints and
                the exit code
*the version*   where the version the tag is named for is read from
*the package*   the evidence package the tagged commit carries
*below signed*  no tag and no package at `strong`
*the audit*     the hash a signature is made over what the audit found
"""

import hashlib
import json
import os
import shutil
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
for _path in (os.path.join(ROOT, 'scripts', 'mcp'),
              os.path.join(ROOT, 'scripts', 'review'),
              os.path.join(ROOT, 'scripts', 'export'), DEV):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import package as package_module                            # noqa: E402
import sign as sign_module                                   # noqa: E402
from purlin import signatures as purlin_signatures           # noqa: E402
from purlin import summary as purlin_summary                 # noqa: E402
from sign_project import REVIEW_GATE, _Out, git, write      # noqa: E402
from test_signatures import (DOUBLED_SPEC, MANUAL_SPEC,     # noqa: E402
                             fingerprint_of, ready, record,
                             waiting_pairs)


def sign_all(made):
    """Sign every rule that waits for a person, in one signed commit."""
    payload = made.payload()
    targets = waiting_pairs(payload)
    assert targets, 'nothing waits to be signed'
    sha, why = sign_module.sign_and_commit(made.root, targets,
                                           'jane@acme.com', payload=payload)
    assert sha, why


def walked(made, release=None):
    """Run the walk, as `purlin:sign` with no argument does. Its lines and tag."""
    out = _Out()
    result = sign_module.walk(made.root, out=out, release=release)
    return out.text().splitlines(), result['tag']


NOTHING_WAITING = 'Nothing is waiting for someone to test by hand or to sign.'


def no_tag_and_no_package(made):
    """True when the project holds no `signed/*` tag and no package folder."""
    tags = git(made.root, 'tag', '-l', 'signed/*').stdout.strip()
    folder = os.path.join(made.root, '.purlin', 'evidence', 'package')
    return tags == '' and not os.path.exists(folder)


@pytest.fixture
def finished():
    """A project at `signed` whose every rule is signed: only the tag is left."""
    made = ready()
    sign_all(made)
    yield made
    made.close()


@pytest.fixture
def tagged():
    """A finished project whose tag `purlin:sign` has written."""
    made = ready()
    sign_all(made)
    made.walked_from = made.head()
    lines, tag = walked(made)
    assert tag == 'signed/2.1.0', lines
    made.tag_output = '\n'.join(lines)
    yield made
    made.close()


# ---------------------------------------------------------------------------
# The tag
# ---------------------------------------------------------------------------

class TestTheTag:

    # purlin: signatures PROOF-67
    # purlin: signatures PROOF-156
    def test_the_tag_is_signed_and_names_the_commit_and_the_gate(self,
                                                                 tagged):
        body = git(tagged.root, 'cat-file', 'tag', 'signed/2.1.0').stdout
        assert '-----BEGIN SSH SIGNATURE-----' in body, body
        message = [line.strip() for line in git(
            tagged.root, 'tag', '-n99', '-l', 'signed/2.1.0').stdout
            .replace('signed/2.1.0', '', 1).splitlines()]
        assert message[:1] == ['Nothing left to do at the gate signed.'], \
            message
        assert 'Commit: %s' % tagged.walked_from in message, message
        assert 'Gate: signed' in message, message

    # purlin: signatures PROOF-178
    def test_the_tag_is_signed_with_the_key_the_settings_name(self, tagged):
        public = git(tagged.root, 'config', 'user.signingkey').stdout.strip()
        with open(public, encoding='utf-8') as handle:
            key_line = handle.read().strip()
        allowed = os.path.join(tagged.root, '.git', 'allowed_signers')
        write(allowed, 'jane@acme.com %s\n' % key_line)
        git(tagged.root, 'config', 'gpg.ssh.allowedSignersFile', allowed)
        checked = git(tagged.root, 'tag', '-v', 'signed/2.1.0')
        shown = checked.stdout + checked.stderr
        assert checked.returncode == 0, shown
        assert 'Good "git" signature for jane@acme.com' in shown, shown
        assert fingerprint_of(public) in shown, shown

    # purlin: signatures PROOF-100
    def test_it_prints_the_tag_and_the_push(self, tagged):
        tag_commit = git(tagged.root, 'rev-parse',
                         'signed/2.1.0^{commit}').stdout.strip()
        assert tagged.tag_output.splitlines()[-2:] == [
            'Tagged signed/2.1.0 at %s.' % tag_commit[:7],
            'Nothing left to do. Push the tag to release it: git push origin '
            'signed/2.1.0']

    # purlin: signatures PROOF-101
    def test_a_remote_is_left_as_it_was(self, finished):
        remote = tempfile.mkdtemp()
        try:
            git(remote, 'init', '-q', '--bare')
            git(finished.root, 'remote', 'add', 'origin', remote)
            assert git(finished.root, 'push', '-q', 'origin',
                       'main').returncode == 0
            before = git(finished.root, 'ls-remote', 'origin').stdout
            lines, tag = walked(finished)
            assert tag == 'signed/2.1.0', lines
            assert git(finished.root, 'ls-remote', 'origin').stdout == before
        finally:
            shutil.rmtree(remote, ignore_errors=True)

    # purlin: signatures PROOF-81
    def test_the_walk_signs_the_last_rules_and_writes_the_tag(self, capsys):
        made = ready()
        try:
            out = _Out()
            result = sign_module.walk(made.root, out=out,
                                      answer=lambda _entry, _text: 'sign')
            assert result['signed'] == [('login', 'RULE-1'),
                                        ('login', 'RULE-2')], out.text()
            assert result['tag'] == 'signed/2.1.0', out.text()
            assert git(made.root, 'tag', '-l').stdout.split() == [
                'signed/2.1.0']
        finally:
            made.close()

    # purlin: signatures PROOF-102
    def test_release_names_another_tag(self, finished, capsys):
        assert sign_module.main(['--release', 'beta', '--project-root',
                                 finished.root]) == 0
        capsys.readouterr()
        assert git(finished.root, 'tag', '-l').stdout.split() == [
            'signed/beta']


# ---------------------------------------------------------------------------
# No tag
# ---------------------------------------------------------------------------

class TestNoTag:

    # purlin: signatures PROOF-68
    def test_while_work_is_left_it_prints_the_summary_ending(self):
        made = ready(audited=())
        try:
            lines, tag = walked(made)
            ending = purlin_summary.ending(made.payload())
            assert lines == [NOTHING_WAITING] + ending.splitlines(), lines
            assert lines[-1] == '  2 rules to audit: purlin:audit', lines
            assert tag is None
            assert git(made.root, 'tag', '-l').stdout.strip() == ''
        finally:
            made.close()

    # purlin: signatures PROOF-103
    def test_no_tag_over_one_already_written(self, finished):
        assert walked(finished, release='beta')[1] == 'signed/beta'
        lines, tag = walked(finished, release='beta')
        assert tag is None
        assert lines == [
            NOTHING_WAITING,
            'No tag: signed/beta is already written. Run purlin:sign '
            '--release <name> to name another.'], lines
        assert git(finished.root, 'tag', '-l').stdout.split() == [
            'signed/beta']

    # purlin: signatures PROOF-74
    def test_no_tag_over_results_that_are_not_committed(self, finished):
        record(finished, at='2026-09-14T12:00:00Z')
        lines, tag = walked(finished)
        assert tag is None
        assert lines == [
            NOTHING_WAITING,
            'No tag: login has results that are not committed. Run '
            'purlin:test --commit.'], lines
        assert git(finished.root, 'tag', '-l').stdout.strip() == ''

    # purlin: signatures PROOF-105
    def test_no_tag_over_work_that_is_not_committed(self, finished):
        write(os.path.join(finished.root, 'notes.txt'), 'a draft\n')
        lines, tag = walked(finished)
        assert tag is None
        assert lines == [
            NOTHING_WAITING,
            'No tag: the working tree holds changes that are not committed, '
            'so the results do not describe a commit. Commit them, then run '
            'purlin:sign.'], lines
        assert git(finished.root, 'tag', '-l').stdout.strip() == ''

    # purlin: signatures PROOF-111
    def test_no_tag_with_no_version(self):
        made = ready(version=None)
        try:
            sign_all(made)
            lines, tag = walked(made)
            assert tag is None
            assert lines == [
                NOTHING_WAITING,
                'No version: nothing in this project states one. Run '
                'purlin:sign --release <version>, or write it to a VERSION '
                'file.'], lines
            assert git(made.root, 'tag', '-l').stdout.strip() == ''
        finally:
            made.close()

    # purlin: signatures PROOF-146
    def test_work_not_committed_exits_one(self, finished, capsys):
        write(os.path.join(finished.root, 'notes.txt'), 'a draft\n')
        code, lines = run_command(finished, capsys)
        assert lines[-1].startswith('No tag: the working tree holds'), lines
        assert (code, tags(finished)) == (1, [])

    # purlin: signatures PROOF-147
    def test_results_not_committed_exit_one(self, finished, capsys):
        record(finished, at='2026-09-14T12:00:00Z')
        code, lines = run_command(finished, capsys)
        assert lines[-1].startswith('No tag: login has results'), lines
        assert (code, tags(finished)) == (1, [])

    # purlin: signatures PROOF-148
    def test_no_version_exits_one(self, capsys):
        made = ready(version=None)
        try:
            sign_all(made)
            code, lines = run_command(made, capsys, '--all')
            assert lines[0] == NOTHING_WAITING, lines
            assert lines[-1].startswith('No version: '), lines
            assert (code, tags(made)) == (1, [])
        finally:
            made.close()

    # purlin: signatures PROOF-149
    def test_a_package_not_committed_exits_one(self, finished, capsys):
        write(os.path.join(finished.root, '.purlin', 'evidence', 'package'),
              'in the way\n')
        code, lines = run_command(finished, capsys)
        assert lines[-1].startswith('No tag: the evidence package was not '
                                    'committed: '), lines
        assert (code, tags(finished)) == (1, [])

    # purlin: signatures PROOF-150
    def test_a_tag_already_written_exits_zero(self, finished, capsys):
        assert walked(finished, release='beta')[1] == 'signed/beta'
        code, lines = run_command(finished, capsys, '--release', 'beta')
        assert lines[-1] == ('No tag: signed/beta is already written. Run '
                             'purlin:sign --release <name> to name '
                             'another.'), lines
        assert (code, tags(finished)) == (0, ['signed/beta'])

    # purlin: signatures PROOF-151
    def test_git_failing_to_write_the_tag_exits_one(self, finished, capsys):
        # A tag named `signed` leaves git no room for `signed/2.1.0`.
        git(finished.root, 'tag', 'signed')
        code, lines = run_command(finished, capsys)
        assert lines[-1].startswith(
            'No tag: git could not write signed/2.1.0: '), lines
        assert 'refs/tags/signed' in lines[-1], lines
        assert lines[-1].endswith('.') and not lines[-1].endswith('..'), lines
        assert (code, tags(finished)) == (1, ['signed'])


class TestNoTagWhileBrokenOrBehind:

    # purlin: signatures PROOF-196
    def test_a_broken_spec_refuses_the_tag(self, finished, capsys):
        write(os.path.join(finished.root, 'specs', 'auth', 'login.md'),
              DOUBLED_SPEC)
        git(finished.root, 'commit', '-q', '-am', 'spec(login): doubled')
        code, lines = run_command(finished, capsys)
        assert ('No tag: login cannot be counted: PROOF-2 is written twice '
                'in the spec. Run purlin:spec login, then purlin:sign.'
                ) in lines, lines
        assert (code, tags(finished)) == (1, [])

    # purlin: signatures PROOF-197
    def test_a_host_copy_ahead_refuses_the_tag(self, finished, hosted):
        other = clone_and_push(hosted)
        try:
            git(finished.root, 'fetch', '-q', 'origin')
            lines, tag = walked(finished)
            assert lines[-1] == (
                'No tag: origin/main holds 1 commit that %s does not, as '
                'this checkout last fetched it. Pull, run purlin:test '
                '--commit, then purlin:sign.' % finished.head()[:7]), lines
            assert (tag, tags(finished)) == (None, [])
        finally:
            shutil.rmtree(other, ignore_errors=True)

    # purlin: signatures PROOF-198
    def test_an_unpushed_commit_is_tagged(self, finished, hosted):
        git(finished.root, 'commit', '-q', '--allow-empty', '-m',
            'chore: not pushed')
        lines, tag = walked(finished)
        assert tag == 'signed/2.1.0', lines

    # purlin: signatures PROOF-199
    def test_a_push_not_fetched_does_not_stop_the_tag(self, finished,
                                                      hosted):
        other = clone_and_push(hosted)
        try:
            lines, tag = walked(finished)
            assert tag == 'signed/2.1.0', lines
        finally:
            shutil.rmtree(other, ignore_errors=True)


@pytest.fixture
def hosted(finished):
    """A bare repository on disk as `origin`, `main` pushed and tracked. Its path."""
    remote = tempfile.mkdtemp()
    git(remote, 'init', '-q', '--bare')
    git(finished.root, 'remote', 'add', 'origin', remote)
    assert git(finished.root, 'push', '-q', '-u', 'origin',
               'main').returncode == 0
    yield remote
    shutil.rmtree(remote, ignore_errors=True)


def clone_and_push(remote):
    """Another clone of `remote` that pushes one commit to `main`. Its path."""
    other = tempfile.mkdtemp()
    git(other, 'clone', '-q', '-b', 'main', remote, '.')
    git(other, 'config', 'user.email', 'ada@example.com')
    git(other, 'config', 'user.name', 'Ada')
    git(other, 'commit', '-q', '--allow-empty', '--no-gpg-sign', '-m',
        'chore: from another clone')
    assert git(other, 'push', '-q', 'origin', 'main').returncode == 0
    return other


def run_command(made, capsys, *argv):
    """`purlin:sign` as a person runs it. Its exit code and printed lines."""
    code = sign_module.main(list(argv) + ['--project-root', made.root])
    return code, capsys.readouterr().out.splitlines()


def tags(made):
    """Every tag the project holds, sorted."""
    return sorted(git(made.root, 'tag', '-l').stdout.split())


# ---------------------------------------------------------------------------
# The version
# ---------------------------------------------------------------------------

@pytest.fixture
def bare():
    """An empty directory to state a version in."""
    folder = tempfile.mkdtemp()
    yield folder
    shutil.rmtree(folder, ignore_errors=True)


class TestTheVersion:

    # purlin: signatures PROOF-106
    def test_the_version_file_comes_first(self, bare):
        write(os.path.join(bare, 'VERSION'), '2.1.0\n')
        write(os.path.join(bare, 'package.json'), '{"version": "3.0.0"}\n')
        assert sign_module.tag_name(bare) == 'signed/2.1.0'

    # purlin: signatures PROOF-107
    def test_package_json_states_it(self, bare):
        write(os.path.join(bare, 'package.json'),
              '{"name": "shop", "version": "3.0.0"}\n')
        assert sign_module.tag_name(bare) == 'signed/3.0.0'

    # purlin: signatures PROOF-108
    def test_the_project_table_of_pyproject_states_it(self, bare):
        write(os.path.join(bare, 'pyproject.toml'),
              '[tool.poetry]\nversion = "0.1.0"\n\n'
              '[project]\nname = "shop"\nversion = "4.2.0"\n')
        assert sign_module.tag_name(bare) == 'signed/4.2.0'

    # purlin: signatures PROOF-109
    def test_the_poetry_table_of_pyproject_states_it(self, bare):
        write(os.path.join(bare, 'pyproject.toml'),
              '[project]\nname = "shop"\n\n'
              '[tool.poetry]\nversion = "0.5.1"\n')
        assert sign_module.tag_name(bare) == 'signed/0.5.1'

    # purlin: signatures PROOF-110
    def test_a_csproj_states_it(self, bare):
        write(os.path.join(bare, 'Shop.csproj'),
              '<Project Sdk="Microsoft.NET.Sdk">\n  <PropertyGroup>\n'
              '    <Version>1.4.0</Version>\n  </PropertyGroup>\n'
              '</Project>\n')
        assert sign_module.tag_name(bare) == 'signed/1.4.0'


# ---------------------------------------------------------------------------
# The package the tagged commit carries
# ---------------------------------------------------------------------------

class TestThePackage:

    # purlin: signatures PROOF-78
    def test_the_package_is_committed_signed_and_tagged(self, tagged):
        root = tagged.root
        tag_commit = git(root, 'rev-parse', 'signed/2.1.0^{commit}').stdout \
            .strip()
        parent = git(root, 'rev-parse', 'signed/2.1.0^{commit}^').stdout \
            .strip()
        assert tag_commit == tagged.head() and parent == tagged.walked_from
        assert git(root, 'show', '--name-only', '--format=%s',
                   tag_commit).stdout.split() == [
            'purlin:', 'evidence', 'at', parent[:7],
            '.purlin/evidence/package/2.1.0.json']
        raw = git(root, 'cat-file', 'commit', tag_commit).stdout
        assert '-----BEGIN SSH SIGNATURE-----' in raw
        shown = git(root, 'show',
                    'signed/2.1.0:.purlin/evidence/package/2.1.0.json').stdout
        assert json.loads(shown)['commit'] == parent
        assert package_module.check_bytes(shown.encode('utf-8')) is None
        assert ('Evidence package committed: '
                '.purlin/evidence/package/2.1.0.json.') in \
            tagged.tag_output.splitlines()
        assert git(root, 'status', '--porcelain').stdout == ''

    # purlin: signatures PROOF-79
    def test_no_tag_when_the_package_cannot_be_written(self, finished):
        write(os.path.join(finished.root, '.purlin', 'evidence', 'package'),
              'in the way\n')
        head = finished.head()
        lines, tag = walked(finished)
        assert tag is None
        assert lines[0] == NOTHING_WAITING, lines
        assert lines[1].startswith('No tag: the evidence package was not '
                                   'committed: '), lines
        assert git(finished.root, 'tag', '-l').stdout.strip() == ''
        assert finished.head() == head

    # purlin: signatures PROOF-163
    def test_no_tag_while_the_package_finds_work_left(self, finished,
                                                      monkeypatch):
        monkeypatch.setattr(package_module, 'build', lambda *_a, **_k: {
            'state': package_module.NOT_FINISHED})
        head = finished.head()
        lines, tag = walked(finished)
        assert tag is None
        assert lines[-1] == (
            'No tag: the committed evidence still has work left to do, so no '
            'evidence package was committed. Run purlin:test --commit, then '
            'purlin:sign.'), lines
        assert git(finished.root, 'tag', '-l').stdout.strip() == ''
        assert finished.head() == head


# ---------------------------------------------------------------------------
# Below signed
# ---------------------------------------------------------------------------

class TestBelowSigned:

    # purlin: signatures PROOF-80
    def test_a_walk_at_strong_with_nothing_waiting(self):
        made = ready(gate=REVIEW_GATE)
        try:
            head = made.head()
            out = _Out()
            result = sign_module.walk(made.root, out=out)
            printed = out.text().splitlines()
            assert printed[0] == ('Nothing is waiting for someone to test by '
                                  'hand or to sign.'), printed
            assert printed[-1] == 'Nothing left to do.', printed
            assert result['tag'] is None and no_tag_and_no_package(made)
            assert made.head() == head
        finally:
            made.close()

    # purlin: signatures PROOF-104
    def test_a_walk_at_strong_signs_a_hand_check_and_ends_on_the_summary(
            self):
        made = ready(gate=REVIEW_GATE, spec=MANUAL_SPEC)
        try:
            out = _Out()
            result = sign_module.walk(
                made.root, out=out,
                answer=lambda _entry, _text: ('sign', 'saw 401 and denied'))
            assert len(result['commits']) == 1, out.text()
            assert out.text().endswith(
                purlin_summary.ending(made.payload()) + '\n'), out.text()
            assert out.text().splitlines()[-2:] == [
                '2 rules. 2 pass their tests. 2 are strong.',
                'Nothing left to do.'], out.text()
            assert result['tag'] is None and no_tag_and_no_package(made)
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What the audit hash is taken over
# ---------------------------------------------------------------------------

class TestTheAuditHash:

    # An entry reading `strong` with no finding, as one audit wrote it.
    ONE = {'verdict': 'strong', 'findings': [], 'rule_hash': 'r',
           'at': '2026-09-13T12:00:00Z', 'commit': 'a' * 40,
           'path': '.purlin/evidence/local/login.json'}

    # purlin: signatures PROOF-64
    def test_what_moves_on_its_own_does_not_move_it(self):
        same = dict(self.ONE, at='2026-09-27T09:00:00Z', commit='b' * 40,
                    path='.purlin/evidence/ci/login.json',
                    model='claude-opus-4-1-20250805', criteria='c' * 64)
        assert purlin_signatures.audit_hash(self.ONE, 90) == \
            purlin_signatures.audit_hash(same, 90)

    # purlin: signatures PROOF-138
    def test_a_weak_verdict_with_a_finding_moves_it(self):
        found = dict(self.ONE, verdict='weak',
                     findings=['PROOF-2 reads the status alone.'])
        assert purlin_signatures.audit_hash(found, 90) != \
            purlin_signatures.audit_hash(self.ONE, 90)

    # purlin: signatures PROOF-139
    def test_an_undecided_verdict_moves_it(self):
        undecided = dict(self.ONE, verdict='undecided')
        assert purlin_signatures.audit_hash(undecided, 90) != \
            purlin_signatures.audit_hash(self.ONE, 90)

    # purlin: signatures PROOF-140
    def test_another_test_strength_moves_it(self):
        assert purlin_signatures.audit_hash(self.ONE, 70) != \
            purlin_signatures.audit_hash(self.ONE, 90)

    # purlin: signatures PROOF-141
    def test_the_order_of_the_findings_does_not_move_it(self):
        one = {'verdict': 'weak', 'findings': ['b.', 'a.']}
        other = {'verdict': 'weak', 'findings': ['a.', 'b.']}
        assert purlin_signatures.audit_hash(one) == \
            purlin_signatures.audit_hash(other)

    # purlin: signatures PROOF-142
    def test_no_entry_hashes_the_empty_string(self):
        empty = purlin_signatures.audit_hash(None)
        assert empty == hashlib.sha256(b'').hexdigest()
        assert empty.startswith('e3b0c442')

    def _signed_rule_2(self, made, capsys):
        assert sign_module.main(['login', 'RULE-2', '--project-root',
                                 made.root]) == 0
        capsys.readouterr()
        return made.load()[('login', 'RULE-2')][0]

    # purlin: signatures PROOF-65
    def test_the_same_audit_again_leaves_the_signature_current(self, capsys):
        made = ready()
        try:
            signature = self._signed_rule_2(made, capsys)
            rel = made.audit('RULE-2')
            path = os.path.join(made.root, *rel.split('/'))
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            data['audit']['rules']['RULE-2']['at'] = '2026-09-27T09:00:00Z'
            write(path, json.dumps(data, indent=2, sort_keys=True))
            assert purlin_signatures.is_current(signature,
                                                made.rule('RULE-2'))
        finally:
            made.close()

    # purlin: signatures PROOF-99
    def test_a_new_finding_ends_the_signature(self, capsys):
        made = ready()
        try:
            signature = self._signed_rule_2(made, capsys)
            made.audit('RULE-2', findings=['PROOF-2 reads the status alone.'])
            assert not purlin_signatures.is_current(signature,
                                                    made.rule('RULE-2'))
        finally:
            made.close()
