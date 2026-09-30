"""The release run: the checks, the package it commits and the tag it writes.

`purlin:test --release` runs every test, commits the evidence, then calls
`release.run_release`, which these tests call directly on a project whose
evidence is already committed. Nothing here pushes or fetches from a host
but a bare repository on disk, and nothing writes a tag outside the
temporary project the test made.

What each group holds:

*the refusals*  each check that stops a release, its line and what it leaves
*the host*      the branch's copy on the host, ahead of the checkout or not
*the version*   where the version the tag is named for is read from
*the release*   the package committed, the tag at `passed`, none at `signed`
*what waits*    a weak or unaudited rule, a hand check, a release run again
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
for _path in (os.path.join(ROOT, 'scripts', 'mcp'),
              os.path.join(ROOT, 'scripts', 'export'), DEV):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import release as release_module                              # noqa: E402
from sign_project import (FIRST_GATE, SIGNING_GATE, SPEC,     # noqa: E402
                          TEST_FILE, Project, _Out, commit_all, git, write)

PACKAGE_REL = '.purlin/evidence/package/2.1.0.json'
PUSH = 'Nothing left to do. Push the tag to release it: git push origin %s'

# `PROOF-2` twice: the spec cannot be counted.
DOUBLED_SPEC = SPEC + (
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify the body '
    '"denied"\n')

# `PROOF-2` is a hand check, and no test carries it.
MANUAL_SPEC = SPEC.replace('verify 401 and the body "denied"',
                           'verify 401 and the body "denied" @manual')
MANUAL_TEST_FILE = TEST_FILE.split('\n\n\n# purlin: login PROOF-2')[0] + '\n'


def made_project(gate=FIRST_GATE, spec=SPEC, test_file=None, statuses=None,
                 version='2.1.0'):
    """A project whose tests ran and whose evidence is committed.

    `statuses` maps each proof to its result, both passing by default. The
    `VERSION` file states `version`, and none is written where it is None.
    """
    made = Project(spec=spec, gate=gate)
    if test_file is not None:
        made.edit_test(test_file)
    made.evidence(statuses=statuses, commit_it=False)
    if version:
        write(os.path.join(made.root, 'VERSION'), version + '\n')
    commit_all(made.root)
    return made


def released(made, version=None):
    """Run the release. `(printed lines, tag, refused)`."""
    out = _Out()
    tag, refused = release_module.run_release(made.root, version, out=out)
    return out.text().splitlines(), tag, refused


def tags(made):
    return git(made.root, 'tag', '-l').stdout.split()


def package_at(made, rel=PACKAGE_REL, ref='HEAD'):
    shown = git(made.root, 'show', '%s:%s' % (ref, rel))
    assert shown.returncode == 0, shown.stderr
    return json.loads(shown.stdout)


def short(made):
    return made.head()[:7]


@pytest.fixture
def passing():
    """At the gate `passed`, both rules pass, `VERSION` reads `2.1.0`."""
    made = made_project()
    yield made
    made.close()


@pytest.fixture
def hosted(passing):
    """`passing`, pushed to a bare repository on disk that is its `origin`."""
    bare = tempfile.mkdtemp()
    git(bare, 'init', '-q', '--bare', '-b', 'main')
    git(passing.root, 'remote', 'add', 'origin', bare)
    pushed = git(passing.root, 'push', '-q', '-u', 'origin', 'main')
    assert pushed.returncode == 0, pushed.stderr
    passing.bare = bare
    yield passing
    shutil.rmtree(bare, ignore_errors=True)


def bare_head(bare, ref='refs/heads/main'):
    return git(bare, 'rev-parse', ref).stdout.strip()


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------

class TestTheRefusals:

    # purlin: release PROOF-1
    def test_a_rule_whose_test_fails_refuses_the_release(self):
        made = made_project(statuses={'PROOF-1': 'pass', 'PROOF-2': 'fail'})
        try:
            lines, tag, refused = released(made)
            assert lines == [
                'No release: 1 rule does not pass at %s: login RULE-2. Run '
                'purlin:status to see what is left, then purlin:test '
                '--release.' % short(made)]
            assert (tag, refused) == (None, 'failing')
            assert tags(made) == []
            assert not os.path.exists(os.path.join(made.root, PACKAGE_REL))
        finally:
            made.close()

    # purlin: release PROOF-2
    def test_a_spec_that_cannot_be_counted_refuses_the_release(self):
        made = made_project(spec=DOUBLED_SPEC)
        try:
            lines, tag, refused = released(made)
            assert lines == [
                'No release: login cannot be counted: PROOF-2 is written '
                'twice in the spec. Run purlin:spec login, then purlin:test '
                '--release.']
            assert (tag, refused) == (None, 'spec')
            assert tags(made) == []
        finally:
            made.close()

    # purlin: release PROOF-3
    def test_work_not_committed_refuses_the_release(self, passing):
        write(os.path.join(passing.root, 'NOTES.md'), 'A note.\n')
        lines, tag, refused = released(passing)
        assert lines == [
            'No release: the working tree holds changes that are not '
            'committed, so the results do not describe a commit. Commit '
            'them, then run purlin:test --release.']
        assert (tag, refused) == (None, 'work')
        assert tags(passing) == []

    # purlin: release PROOF-11
    def test_a_tag_already_written_refuses_the_release(self, passing):
        git(passing.root, 'tag', 'passed/2.1.0')
        head = passing.head()
        lines, tag, refused = released(passing)
        assert lines == [
            'No release: passed/2.1.0 is already written. Run purlin:test '
            '--release <version> to name another.']
        assert (tag, refused) == (None, 'exists')
        assert passing.head() == head


# ---------------------------------------------------------------------------
# The host
# ---------------------------------------------------------------------------

class TestTheHost:

    # purlin: release PROOF-4
    def test_a_host_copy_ahead_refuses_the_release(self, hosted):
        other = tempfile.mkdtemp()
        try:
            git(other, 'clone', '-q', hosted.bare, 'copy')
            copy = os.path.join(other, 'copy')
            git(copy, 'config', 'user.email', 'pat@example.com')
            git(copy, 'config', 'user.name', 'Pat')
            git(copy, 'config', 'commit.gpgsign', 'false')
            write(os.path.join(copy, 'NOTES.md'), 'A note.\n')
            commit_all(copy, 'docs: a note')
            assert git(copy, 'push', '-q').returncode == 0
        finally:
            shutil.rmtree(other, ignore_errors=True)
        git(hosted.root, 'fetch', '-q')
        lines, tag, refused = released(hosted)
        assert lines == [
            'No release: origin/main holds 1 commit that %s does not, as '
            'this checkout last fetched it. Pull, then run purlin:test '
            '--release.' % short(hosted)]
        assert (tag, refused) == (None, 'behind')
        assert tags(hosted) == []

    # purlin: release PROOF-5
    def test_a_commit_of_its_own_the_host_lacks_is_released(self, hosted):
        write(os.path.join(hosted.root, 'NOTES.md'), 'A note.\n')
        commit_all(hosted.root, 'docs: a note')
        lines, tag, refused = released(hosted)
        assert (tag, refused) == ('passed/2.1.0', None), lines
        assert package_at(hosted)['version'] == '2.1.0'

    # purlin: release PROOF-16
    def test_nothing_is_fetched_or_pushed(self, hosted):
        before = bare_head(hosted.bare)
        lines, tag, refused = released(hosted)
        assert tag == 'passed/2.1.0', lines
        assert git(hosted.bare, 'tag', '-l').stdout.strip() == ''
        assert bare_head(hosted.bare) == before
        assert not os.path.exists(os.path.join(hosted.root, '.git',
                                               'FETCH_HEAD'))


# ---------------------------------------------------------------------------
# The version
# ---------------------------------------------------------------------------

class TestTheVersion:

    # purlin: release PROOF-6
    def test_the_version_file_names_the_release(self, passing):
        write(os.path.join(passing.root, 'package.json'),
              '{"version": "9.9.9"}\n')
        commit_all(passing.root, 'chore: a package.json')
        lines, tag, refused = released(passing)
        assert (tag, refused) == ('passed/2.1.0', None), lines
        assert package_at(passing)['version'] == '2.1.0'
        assert tags(passing) == ['passed/2.1.0']

    # purlin: release PROOF-7
    def test_a_named_version_names_the_release(self, passing):
        lines, tag, refused = released(passing, '2.0.0')
        assert (tag, refused) == ('passed/2.0.0', None), lines
        assert package_at(
            passing, '.purlin/evidence/package/2.0.0.json')['version'] == '2.0.0'
        assert tags(passing) == ['passed/2.0.0']

    # purlin: release PROOF-8
    def test_no_version_refuses_the_release(self):
        made = made_project(version=None)
        try:
            lines, tag, refused = released(made)
            assert lines == [
                'No version: nothing in this project states one. Run '
                'purlin:test --release <version>, or write it to a VERSION '
                'file.']
            assert (tag, refused) == (None, 'version')
            assert not os.path.exists(os.path.join(
                made.root, '.purlin', 'evidence', 'package'))
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The release
# ---------------------------------------------------------------------------

class TestTheRelease:

    # purlin: release PROOF-9
    def test_at_passed_the_package_is_committed_and_tagged(self, passing):
        evidence_at = passing.head()
        lines, tag, refused = released(passing)
        assert (tag, refused) == ('passed/2.1.0', None), lines
        head = passing.head()
        assert lines == [
            'Evidence package committed: %s.' % PACKAGE_REL,
            'Tagged passed/2.1.0 at %s.' % head[:7],
            PUSH % 'passed/2.1.0']
        assert git(passing.root, 'log', '-1', '--format=%s').stdout.strip() \
            == 'purlin: evidence at %s' % evidence_at[:7]
        assert git(passing.root, 'rev-parse',
                   'passed/2.1.0^{commit}').stdout.strip() == head
        body = git(passing.root, 'cat-file', 'tag', 'passed/2.1.0').stdout
        assert 'SIGNATURE' not in body, body
        assert body.split('\n\n', 1)[1] == (
            'Released at the gate passed.\n\nCommit: %s\nGate: passed\n'
            % evidence_at)
        assert package_at(passing)['commit'] == evidence_at

    # purlin: release PROOF-10
    def test_at_signed_the_package_is_committed_and_no_tag_written(self):
        made = made_project(gate=SIGNING_GATE)
        try:
            lines, tag, refused = released(made)
            assert (tag, refused) == (None, None), lines
            assert lines[-1] == ('Run purlin:sign to sign it; the first '
                                 'signature writes signed/2.1.0.')
            assert package_at(made)['tag'] == 'signed/2.1.0'
            assert tags(made) == []
        finally:
            made.close()

    # purlin: release PROOF-15
    def test_git_refusing_the_tag_is_named(self, passing):
        git(passing.root, 'tag', 'passed')
        lines, tag, refused = released(passing)
        assert (tag, refused) == (None, 'git'), lines
        assert lines[0] == 'Evidence package committed: %s.' % PACKAGE_REL
        assert lines[1].startswith(
            'No tag: git could not write passed/2.1.0: '), lines
        assert lines[1].endswith('.') and len(lines) == 2, lines


# ---------------------------------------------------------------------------
# What waits
# ---------------------------------------------------------------------------

class TestWhatWaits:

    # purlin: release PROOF-12
    def test_a_weak_or_unaudited_rule_does_not_refuse(self):
        made = Project(gate=SIGNING_GATE)
        try:
            made.evidence(commit_it=False)
            made.audit('RULE-1', findings=['The test checks one password.'])
            write(os.path.join(made.root, 'VERSION'), '2.1.0\n')
            commit_all(made.root)
            lines, tag, refused = released(made)
            assert refused is None, lines
            assert lines[-1] == ('Run purlin:sign to sign it; the first '
                                 'signature writes signed/2.1.0.')
            assert package_at(made)['version'] == '2.1.0'
        finally:
            made.close()

    # purlin: release PROOF-13
    def test_a_package_with_no_tag_yet_is_written_again(self):
        made = made_project(gate=SIGNING_GATE)
        try:
            lines, _tag, refused = released(made)
            assert refused is None, lines
            first = package_at(made)['commit']
            write(os.path.join(made.root, 'tests', 'test_login.py'),
                  TEST_FILE + '\n')
            made.evidence(commit_it=False)
            commit_all(made.root, 'test(login): a blank line')
            edited = made.head()
            lines, _tag, refused = released(made)
            assert refused is None, lines
            assert package_at(made)['commit'] == edited != first
        finally:
            made.close()

    # purlin: release PROOF-14
    def test_a_hand_check_at_passed_is_named_and_listed_not_checked(self):
        made = made_project(spec=MANUAL_SPEC, test_file=MANUAL_TEST_FILE,
                            statuses={'PROOF-1': 'pass'})
        try:
            lines, tag, refused = released(made)
            assert (tag, refused) == ('passed/2.1.0', None), lines
            assert lines[:2] == [
                '1 rule is checked by hand, and the gate passed records no '
                'hand check: login RULE-2. The package lists them as not '
                'checked.',
                'Evidence package committed: %s.' % PACKAGE_REL]
            assert package_at(made)['hand_checks'] == [
                {'feature': 'login', 'rule': 'RULE-2', 'proofs': ['PROOF-2'],
                 'checked': False}]
        finally:
            made.close()
