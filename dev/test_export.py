"""The evidence package `purlin:export` writes, and the one `purlin:sign`
commits with the tag.

Every project here is a throwaway git repository in a temporary directory,
with a spec, a test file, evidence, audit entries and, where a signature is
involved, a signing key that exists nowhere but that directory. The package
command runs as a separate process, as a person runs it.

What each group holds:

*the file*        where it is written, its name, what it prints, and that it
                  commits nothing unless asked
*the state*       `work in progress`, `gate <gate> met` and `signed`, with the
                  failure cases: no evidence, no test, no audit, no signature
*the content*     what one rule carries, and what it never carries
*what git holds*  evidence written and not committed is left out and named
*the bytes*       the same tag gives the same bytes, from a second clone too
*the fingerprint* `--check` on a package as written and on one edited after
*the tag*         `purlin:sign` commits the package and tags that commit
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'export'))

import package as package_module                              # noqa: E402
import sign as sign_module                                    # noqa: E402
from purlin import PURLIN_VERSION                             # noqa: E402
from test_signatures import (SIGNING_GATE, SPEC, TEST_FILE,   # noqa: E402
                             Project, commit_as_ci, git, manual_at_strong,
                             signing_key, write)

PACKAGE_PY = os.path.join(ROOT, 'scripts', 'export', 'package.py')

TOP_LEVEL = ['schema', 'state', 'not_for_approval', 'rules_meeting_gate',
             'rules_short_of_gate', 'purlin_version', 'project', 'version',
             'tag', 'commit', 'gate', 'trust', 'mutation_engine',
             'min_strength', 'features', 'warnings', 'fingerprint']

UTC = re.compile(r'^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$')

# A rule with a requirement's number in its words and no proof at all.
SPEC_WITH_A_THIRD_RULE = SPEC.replace(
    '\n\n## Proof',
    '\n- RULE-3: A locked account returns 423 (URS-042)\n\n## Proof')

MODEL = 'claude-opus-5-20260901'
CRITERIA = 'c' * 64


class _Out(object):
    def __init__(self):
        self.lines = []

    def write(self, text):
        self.lines.append(text)

    def flush(self):
        pass

    def text(self):
        return ''.join(self.lines)


def export(root, *args):
    """Run the package command in `root`. `(exit code, printed lines)`."""
    done = subprocess.run([sys.executable, PACKAGE_PY, '--project-root', root]
                          + list(args), capture_output=True, text=True,
                          cwd=root)
    return done.returncode, (done.stdout + done.stderr).splitlines()


def read_bytes(root, rel):
    with open(os.path.join(root, *rel.split('/')), 'rb') as handle:
        return handle.read()


def read_package(root, version='2.1.0'):
    return json.loads(read_bytes(
        root, '.purlin/evidence/package/%s.json' % version).decode('utf-8'))


def rule_of(package, rule_id, feature='login'):
    entry = next(f for f in package['features'] if f['name'] == feature)
    return next(r for r in entry['rules'] if r['id'] == rule_id)


def status(root):
    return git(root, 'status', '--porcelain', '--untracked-files=all').stdout


def name_the_model(made, rule):
    """Give an audit entry the model and the criteria fingerprint it names."""
    rel = '.purlin/evidence/local/login.json'
    path = os.path.join(made.root, *rel.split('/'))
    with open(path, encoding='utf-8') as handle:
        data = json.load(handle)
    data['audit']['rules'][rule].update(model=MODEL, criteria=CRITERIA)
    write(path, json.dumps(data, indent=2, sort_keys=True))


def signed_project(spec=SPEC, version='2.1.0', gate=SIGNING_GATE):
    """A project at `signed` whose rules pass, one audited strong, both committed.

    `RULE-1` is marked `[level: passed]`, so `RULE-2` is the one rule that
    asks for a signature. The signer's key is set up last. With `gate` the
    same project is made at another gate.
    """
    made = Project(spec=spec, gate=gate, config={'min_strength': 50})
    made.proofs()
    made.evidence(strength=90, runner='ci', commit_it=False, source='ci')
    made.audit('RULE-2')
    name_the_model(made, 'RULE-2')
    write(os.path.join(made.root, 'VERSION'), version + '\n')
    commit_as_ci(made.root)
    signing_key(made.root)
    return made


def sign_the_queue(made):
    payload = made.payload()
    targets = sign_module.queued(payload)
    if targets:
        sign_module.sign_and_commit(made.root, targets, 'jane@acme.com',
                                    payload=payload)
    return targets


@pytest.fixture
def signed():
    made = signed_project()
    yield made
    made.close()


@pytest.fixture
def tagged():
    """A signed project whose tag `purlin:sign` has written."""
    made = signed_project()
    sign_the_queue(made)
    out = _Out()
    assert sign_module.tag_if_met(made.root, out) == 'signed/2.1.0', out.text()
    made.tag_output = out.text()
    yield made
    made.close()


def no_tag_and_no_package(made):
    """True when the project holds no `signed/*` tag and no package folder."""
    tags = git(made.root, 'tag', '-l', 'signed/*').stdout.strip()
    folder = os.path.join(made.root, '.purlin', 'evidence', 'package')
    return tags == '' and not os.path.exists(folder)


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

class TestTheFile:

    # purlin: package PROOF-1
    def test_it_writes_the_version_file_prints_the_state_and_commits_nothing(
            self, signed):
        head = signed.head()
        code, lines = export(signed.root)
        assert code == 0, lines
        assert lines[0] == (
            'Evidence package written to .purlin/evidence/package/2.1.0.json. '
            'State: work in progress, 1 of 2 rules meet the gate signed. '
            'Not for approval.'), lines
        assert signed.head() == head
        assert status(signed.root) == (
            '?? .purlin/evidence/package/2.1.0.json\n')
        assert len(git(signed.root, 'worktree', 'list').stdout
                   .splitlines()) == 1

    # purlin: package PROOF-2
    def test_release_names_the_version_the_file_and_the_tag(self, signed):
        code, lines = export(signed.root, '--release', 'beta')
        assert code == 0, lines
        assert lines[0].startswith('Evidence package written to '
                                   '.purlin/evidence/package/beta.json.'), lines
        package = read_package(signed.root, 'beta')
        assert (package['version'], package['tag']) == ('beta', 'signed/beta')
        assert not os.path.exists(os.path.join(
            signed.root, '.purlin', 'evidence', 'package', '2.1.0.json'))

    # purlin: package PROOF-3
    def test_the_top_level_keys_come_in_the_format_order(self, signed):
        export(signed.root)
        package = read_package(signed.root)
        assert list(package) == TOP_LEVEL
        assert package['schema'] == 'purlin-package/1'
        assert package['purlin_version'] == PURLIN_VERSION
        assert (package['project'], package['gate'], package['trust'],
                package['mutation_engine'], package['min_strength']) == (
                    'proj', 'signed', 'local', 'none', 50)
        assert package['commit'] == signed.head()

    # purlin: package PROOF-10
    def test_commit_commits_the_file_as_evidence_and_once(self, signed):
        head = signed.head()
        code, lines = export(signed.root, '--commit')
        assert code == 0, lines
        assert lines[-1] == 'Package committed.', lines
        assert git(signed.root, 'log', '-1', '--format=%s').stdout.strip() == \
            'purlin: evidence at %s' % head[:7]
        assert status(signed.root) == ''
        code, lines = export(signed.root, '--commit')
        assert lines[-1] == 'Package unchanged.', lines
        assert read_package(signed.root)['commit'] == head


# ---------------------------------------------------------------------------
# The state
# ---------------------------------------------------------------------------

class TestTheState:

    # purlin: package PROOF-4
    def test_a_project_with_no_evidence_is_work_in_progress(self):
        made = Project()
        try:
            write(os.path.join(made.root, 'VERSION'), '1.0.0\n')
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'chore: version')
            code, lines = export(made.root)
            assert code == 0, lines
            assert lines[0].endswith('State: work in progress, 0 of 2 rules '
                                     'meet the gate passed. '
                                     'Not for approval.'), lines
            package = read_package(made.root, '1.0.0')
            assert (package['state'], package['not_for_approval'],
                    package['rules_meeting_gate'],
                    package['rules_short_of_gate']) == (
                        'work in progress', True, 0, 2)
            assert rule_of(package, 'RULE-1')['results'] == []
            assert rule_of(package, 'RULE-1')['statuses']['passed'][
                'word'] == 'no test'
        finally:
            made.close()

    # purlin: package PROOF-5
    def test_a_rule_with_no_test_holds_the_state(self):
        made = signed_project(spec=SPEC_WITH_A_THIRD_RULE)
        try:
            sign_the_queue(made)
            export(made.root)
            package = read_package(made.root)
            third = rule_of(package, 'RULE-3')
            assert third['text'] == 'A locked account returns 423 (URS-042)'
            assert (third['proofs'], third['tests']) == ([], [])
            assert [r['result'] for r in third['results']] == ['no test']
            assert third['meets_gate'] is False
            assert package['state'] == 'work in progress'
            assert package['rules_short_of_gate'] == 1
        finally:
            made.close()

    # purlin: package PROOF-6
    def test_a_rule_with_no_audit_holds_the_state(self):
        made = Project(gate='strong')
        try:
            made.proofs()
            made.evidence()
            export(made.root)
            package = read_package(made.root, 'unversioned')
            second = rule_of(package, 'RULE-2')
            assert second['audit'] is None
            assert second['statuses']['strong']['word'] != 'strong'
            assert second['meets_gate'] is False
            assert package['state'] == 'work in progress'
            assert package['not_for_approval'] is True
        finally:
            made.close()

    # purlin: package PROOF-7
    def test_an_unsigned_rule_holds_the_state(self, signed):
        export(signed.root)
        package = read_package(signed.root)
        second = rule_of(package, 'RULE-2')
        assert second['signatures'] == []
        assert second['statuses']['signed']['word'] == 'unsigned'
        assert (package['state'], package['rules_meeting_gate'],
                package['rules_short_of_gate']) == ('work in progress', 1, 1)

    # purlin: package PROOF-8
    def test_a_met_gate_without_the_tag_is_still_not_for_approval(self):
        made = Project()
        try:
            made.proofs()
            made.evidence()
            code, lines = export(made.root)
            assert lines[0].endswith('State: gate passed met, 2 of 2 rules '
                                     'meet the gate passed. '
                                     'Not for approval.'), lines
            package = read_package(made.root, 'unversioned')
            assert (package['state'], package['not_for_approval']) == (
                'gate passed met', True)
        finally:
            made.close()
        made = signed_project()
        try:
            sign_the_queue(made)
            export(made.root)
            package = read_package(made.root)
            assert (package['state'], package['not_for_approval']) == (
                'gate signed met', True)
        finally:
            made.close()


    # purlin: package PROOF-19
    def test_below_signed_a_tag_on_the_commit_never_reads_signed(self):
        made = signed_project(gate='strong')
        try:
            git(made.root, 'tag', '-a', 'signed/2.1.0', '-m', 'by hand')
            code, lines = export(made.root)
            assert code == 0, lines
            assert lines[0].endswith('State: gate strong met, 2 of 2 rules '
                                     'meet the gate strong. '
                                     'Not for approval.'), lines
            package = read_package(made.root)
            assert (package['state'], package['not_for_approval']) == (
                'gate strong met', True)
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The content
# ---------------------------------------------------------------------------

class TestTheContent:

    # purlin: package PROOF-9
    def test_one_rule_carries_its_words_proofs_tests_results_audit_and_signature(
            self, tagged):
        package = read_package(tagged.root)
        rule = rule_of(package, 'RULE-2')
        print(json.dumps(rule, indent=2, sort_keys=True))
        assert rule['text'] == ('Invalid credentials return 401 and the body '
                                '"denied"')
        assert (rule['level'], rule['level_marked']) == ('signed', False)
        assert (rule_of(package, 'RULE-1')['level'],
                rule_of(package, 'RULE-1')['level_marked']) == ('passed', True)
        assert rule['proofs'] == [{
            'id': 'PROOF-2', 'manual': False, 'env': None,
            'text': 'POST /login with a bad password; verify 401 and the body '
                    '"denied"'}]
        assert rule['tests'] == [{'proof': 'PROOF-2',
                                  'file': 'tests/test_login.py',
                                  'name': 'test_a_bad_password_is_denied'}]
        [result] = rule['results']
        assert (result['source'], result['result'], result['runner'],
                result['at'], result['current']) == (
                    'ci', 'passed', 'ci', '2026-09-13T12:00:00Z', True)
        assert result['os'] in ('windows', 'macos', 'linux')
        assert re.match(r'^[0-9a-f]{40}$', result['commit'])
        audit = rule['audit']
        assert (audit['verdict'], audit['findings'], audit['strength'],
                audit['model'], audit['criteria'], audit['at']) == (
                    'strong', [], 90, MODEL, CRITERIA, '2026-09-13T12:05:00Z')
        [signature] = rule['signatures']
        assert signature['signer'] == 'jane@acme.com'
        assert signature['commit_verifies'] is True
        assert signature['note'] is None
        assert signature['os'] in ('windows', 'macos', 'linux')
        assert signature['machine']
        assert set(signature['locked']) == {
            'triple', 'rule_hash', 'proof_hash', 'test_hash',
            'test_hash_kind', 'audit_hash'}
        assert rule['statuses']['signed'] == {'word': 'signed',
                                              'reasons': ['by jane@acme.com']}
        assert rule['meets_gate'] is True

    # purlin: package PROOF-20
    def test_a_rule_carries_only_the_statuses_its_level_asks_for(self,
                                                                  tagged):
        package = read_package(tagged.root)
        lower = rule_of(package, 'RULE-1')
        assert lower['level'] == 'passed', lower
        assert list(lower['statuses']) == ['passed'], lower['statuses']
        assert lower['statuses']['passed']['word'] == 'passed', lower
        assert sorted(rule_of(package, 'RULE-2')['statuses']) == [
            'passed', 'signed', 'strong']
        made = signed_project(spec=SPEC.replace('[level: passed]',
                                                '[level: strong]'))
        try:
            export(made.root)
            middle = rule_of(read_package(made.root), 'RULE-1')
            assert middle['level'] == 'strong', middle
            assert sorted(middle['statuses']) == ['passed', 'strong'], (
                middle['statuses'])
            assert None not in middle['statuses'].values(), middle
        finally:
            made.close()

    # purlin: package PROOF-18
    def test_a_rule_with_no_proof_carries_the_tests_marked_with_its_id(self):
        made = Project(spec=SPEC_WITH_A_THIRD_RULE, gate='passed')
        try:
            made.edit_test(TEST_FILE + (
                '\n\n# purlin: login RULE-3\n'
                'def test_a_locked_account_returns_423():\n'
                '    assert True\n'))
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'test: the locked account')
            made.proofs()
            rel = made.evidence(commit_it=False)
            path = os.path.join(made.root, *rel.split('/'))
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            for section in data['platforms'].values():
                section['rules']['RULE-3'] = 'passed'
                section['proofs'].append({
                    'id': 'RULE-3', 'rule': 'RULE-3', 'result': 'pass',
                    'env': None, 'manual': False,
                    'test': 'tests/test_login.py::'
                            'test_a_locked_account_returns_423'})
            write(path, json.dumps(data, indent=2, sort_keys=True))
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
            export(made.root)
            third = rule_of(read_package(made.root, 'unversioned'), 'RULE-3')
            assert third['proofs'] == []
            assert third['tests'] == [{
                'proof': 'RULE-3', 'file': 'tests/test_login.py',
                'name': 'test_a_locked_account_returns_423'}]
            assert [r['result'] for r in third['results']] == ['passed']
            second = rule_of(read_package(made.root, 'unversioned'), 'RULE-2')
            assert [t['proof'] for t in second['tests']] == ['PROOF-2']
        finally:
            made.close()

    # purlin: package PROOF-11
    def test_nothing_names_who_last_changed_a_test(self, tagged):
        # The test file was committed by dev@example.com, and nothing in the
        # package names that person or asks who changed the test last.
        text = read_bytes(tagged.root,
                          '.purlin/evidence/package/2.1.0.json').decode()
        assert 'dev@example.com' not in text
        assert 'author' not in text


# ---------------------------------------------------------------------------
# What git holds
# ---------------------------------------------------------------------------

class TestWhatGitHolds:

    # purlin: package PROOF-12
    def test_evidence_not_committed_is_left_out_and_named(self, signed):
        sign_the_queue(signed)
        signed.evidence(strength=90, runner='ci', source='ci',
                        commit_it=False, at='2026-09-14T12:00:00Z')
        code, lines = export(signed.root)
        warning = ('.purlin/evidence/ci/login.json is written and not '
                   'committed; the package leaves it out.')
        assert warning in lines, lines
        package = read_package(signed.root)
        assert package['warnings'] == [warning]
        assert [r['at'] for r in rule_of(package, 'RULE-2')['results']] == [
            '2026-09-13T12:00:00Z']


# ---------------------------------------------------------------------------
# The bytes
# ---------------------------------------------------------------------------

def _clone_at_the_tag(made):
    """A second clone of the project, checked out at the tag, able to verify."""
    parent = tempfile.mkdtemp()
    clone = os.path.join(parent, 'second')
    git(parent, 'clone', '-q', made.root, clone)
    allowed = os.path.join(made.root, '.git', 'allowed-signers')
    git(clone, 'config', 'gpg.format', 'ssh')
    git(clone, 'config', 'gpg.ssh.allowedSignersFile', allowed)
    git(clone, 'checkout', '-q', 'signed/2.1.0')
    return parent, clone


class TestTheBytes:

    # purlin: package PROOF-13
    def test_exporting_twice_gives_the_same_bytes(self, signed):
        export(signed.root)
        first = read_bytes(signed.root, '.purlin/evidence/package/2.1.0.json')
        export(signed.root)
        second = read_bytes(signed.root, '.purlin/evidence/package/2.1.0.json')
        assert first == second
        assert first.endswith(b'}\n') and b'\r' not in first

    # purlin: package PROOF-14
    def test_a_second_clone_at_the_tag_gives_the_committed_bytes(self, tagged):
        committed = git(tagged.root, 'show',
                        'signed/2.1.0:.purlin/evidence/package/2.1.0.json')
        parent, clone = _clone_at_the_tag(tagged)
        try:
            code, lines = export(clone)
            assert code == 0, lines
            assert lines[0].endswith('State: signed, 2 of 2 rules meet the '
                                     'gate signed.'), lines
            assert read_bytes(
                clone, '.purlin/evidence/package/2.1.0.json').decode() == \
                committed.stdout
        finally:
            shutil.rmtree(parent, ignore_errors=True)

    # purlin: package PROOF-15
    def test_every_time_is_utc(self, tagged):
        package = read_package(tagged.root)
        times = []

        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in ('at', 'committed_at') and item is not None:
                        times.append(item)
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)
        walk(package)
        assert len(times) >= 4
        assert [t for t in times if not UTC.match(t)] == []


# ---------------------------------------------------------------------------
# The fingerprint
# ---------------------------------------------------------------------------

class TestTheFingerprint:

    # purlin: package PROOF-16
    def test_check_passes_a_package_as_written(self, signed):
        export(signed.root)
        path = os.path.join(signed.root, '.purlin', 'evidence', 'package',
                            '2.1.0.json')
        code, lines = export(signed.root, '--check', path)
        assert (code, lines) == (0, ['The package matches its fingerprint.'])
        assert re.match(r'^[0-9a-f]{64}$', read_package(signed.root)[
            'fingerprint'])

    # purlin: package PROOF-17
    def test_check_names_an_edit_made_after(self, signed):
        export(signed.root)
        path = os.path.join(signed.root, '.purlin', 'evidence', 'package',
                            '2.1.0.json')
        with open(path, 'rb') as handle:
            data = handle.read()
        with open(path, 'wb') as handle:
            handle.write(data.replace(b'"unsigned"', b'"signed"', 1))
        code, lines = export(signed.root, '--check', path)
        assert code == 1
        assert lines[0].startswith('The package does not match its '
                                   'fingerprint: the package records the '
                                   'fingerprint '), lines
        with open(path, 'wb') as handle:
            handle.write(data.replace(b'\n', b'\r\n'))
        code, lines = export(signed.root, '--check', path)
        assert code == 1
        assert 'not in the canonical form' in lines[0], lines


# ---------------------------------------------------------------------------
# The tag
# ---------------------------------------------------------------------------

class TestTheTag:

    # purlin: signatures PROOF-78
    def test_sign_commits_the_package_and_tags_that_commit(self, tagged):
        root = tagged.root
        tag_commit = git(root, 'rev-parse', 'signed/2.1.0^{commit}').stdout \
            .strip()
        parent = git(root, 'rev-parse', 'signed/2.1.0^{commit}^').stdout \
            .strip()
        assert tag_commit == tagged.head()
        assert git(root, 'show', '--name-only', '--format=%s',
                   tag_commit).stdout.split() == [
            'purlin:', 'evidence', 'at', parent[:7],
            '.purlin/evidence/package/2.1.0.json']
        assert git(root, 'log', '-1', '--format=%G?',
                   tag_commit).stdout.strip() == 'G'
        shown = git(root, 'show',
                    'signed/2.1.0:.purlin/evidence/package/2.1.0.json').stdout
        package = json.loads(shown)
        assert (package['state'], package['not_for_approval'],
                package['commit']) == ('signed', False, parent)
        assert package_module.check_bytes(shown.encode('utf-8')) is None
        assert ('Evidence package committed: '
                '.purlin/evidence/package/2.1.0.json.') in tagged.tag_output
        assert status(root) == ''

    # purlin: signatures PROOF-79
    def test_no_tag_when_the_package_cannot_be_written(self, signed):
        sign_the_queue(signed)
        write(os.path.join(signed.root, '.purlin', 'evidence', 'package'),
              'in the way\n')
        head = signed.head()
        out = _Out()
        assert sign_module.tag_if_met(signed.root, out) is None
        assert out.text().startswith('No tag: the evidence package was not '
                                     'committed: '), out.text()
        assert git(signed.root, 'tag', '-l').stdout.strip() == ''
        assert signed.head() == head

    # purlin: signatures PROOF-80
    def test_at_strong_the_walk_writes_no_tag_and_no_package(self):
        made = signed_project(gate='strong')
        try:
            assert all(rule['meets_gate'] for feature in made.payload()[
                'features'] for rule in feature['rules'])
            head = made.head()
            out = _Out()
            result = sign_module.walk(made.root, out=out,
                                      signer_email='jane@acme.com')
            printed = out.text().splitlines()
            assert printed == ['Queue: 0 rules. 0 hand checks, 0 signatures.',
                               'Nothing is waiting for a person.'], printed
            assert result['tag'] is None
            assert no_tag_and_no_package(made)
            assert made.head() == head
        finally:
            made.close()

        made = manual_at_strong()
        try:
            out = _Out()
            result = sign_module.walk(
                made.root, out=out, signer_email='jane@acme.com',
                answer=lambda entry, rendered: ('sign', 'saw 401 and denied'))
            printed = out.text()
            assert ('Walked 1 rule: 1 signed, 0 cases added, 0 skipped.'
                    in printed), printed
            assert result['commits'] and ('Commits: %s'
                                          % result['commits'][0][:7]
                                          in printed), printed
            assert 'tag' not in printed.lower(), printed
            assert result['tag'] is None
            assert all(rule['meets_gate'] for feature in made.payload()[
                'features'] for rule in feature['rules'])
            assert no_tag_and_no_package(made)
        finally:
            made.close()

    # purlin: signatures PROOF-81
    def test_the_same_project_at_signed_gets_the_tag_and_the_package(self):
        made = signed_project()
        try:
            out = _Out()
            result = sign_module.walk(
                made.root, out=out, signer_email='jane@acme.com',
                answer=lambda entry, rendered: 'sign')
            assert result['signed'] == [('login', 'RULE-2')], out.text()
            assert result['tag'] == 'signed/2.1.0', out.text()
            shown = git(made.root, 'show', 'signed/2.1.0:.purlin/evidence/'
                        'package/2.1.0.json').stdout
            assert json.loads(shown)['state'] == 'signed'
        finally:
            made.close()
