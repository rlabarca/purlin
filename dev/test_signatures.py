"""Tests for the signature reader and the command that writes one.

Every fixture is written by the test in a throwaway project: a spec, a test
file, a runtime proof file, the evidence, a signature. Nothing here reads this
repository's own specs, reaches a network, or signs with a key that exists
anywhere but the temporary directory the test made.

What each group holds:

*the triple*   the three hashes a signature binds, and what does and does not
               change them: reflowing a rule and adding a tag do not, editing
               the rule, the proof or the test do
*stale*        a signature stops being current when any part of the triple
               or the audit moves under it, and the level it records does
               not stale it
*the file*     the name, the fields, and the evidence file it names
*the commit*   one signed commit for a batch, and the exact setup to print
               when this checkout cannot sign
*any branch*   a signature counts on whatever commit carries it
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
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))

import sign as sign_module  # noqa: E402
from purlin import evidence as purlin_evidence  # noqa: E402
from purlin import gate as purlin_gate  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402
from purlin import signatures as purlin_signatures  # noqa: E402
from purlin import fingerprint as purlin_fingerprint  # noqa: E402
from purlin import specs as purlin_specs  # noqa: E402

SIGN_PY = os.path.join(ROOT, 'scripts', 'review', 'sign.py')

# The three gates by position: the one a project sits at by default, the one
# that turns the breaks and the queue on, and the one that asks for a
# signature.
FIRST_GATE = purlin_gate.GATES[0]
REVIEW_GATE = purlin_gate.GATES[1]
SIGNING_GATE = purlin_gate.GATES[-1]

# ---------------------------------------------------------------------------
# The throwaway project
# ---------------------------------------------------------------------------

SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in with an email and a password.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token '
    '[level: passed]\n'
    '- RULE-2: Invalid credentials return 401 and the body "denied"\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with the password "secret"; verify 200 '
    'and a token\n'
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify 401 and the '
    'body "denied"\n'
)

TEST_FILE = (
    'import pytest\n'
    '\n'
    'from src.login import login\n'
    '\n'
    '\n'
    '@pytest.mark.proof("login", "PROOF-1", "RULE-1")\n'
    'def test_valid_credentials_return_200():\n'
    '    assert login("ada", "secret") == 200\n'
    '\n'
    '\n'
    '@pytest.mark.proof("login", "PROOF-2", "RULE-2")\n'
    'def test_a_bad_password_is_denied():\n'
    '    assert login("ada", "wrong") == 401\n'
)

TEST_NAMES = {'PROOF-1': 'test_valid_credentials_return_200',
              'PROOF-2': 'test_a_bad_password_is_denied'}


def git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root, capture_output=True,
                          text=True)


def write(path, text):
    directory = os.path.dirname(path)
    if directory and not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


class Project(object):
    """A throwaway project: git, a config, one spec, one test file."""

    def __init__(self, spec=SPEC, gate=None, config=None):
        self.root = tempfile.mkdtemp()
        settings = {'gate': gate or FIRST_GATE,
                    'project_name': 'proj'}
        settings.update(config or {})
        write(os.path.join(self.root, '.purlin', 'config.json'),
              json.dumps(settings))
        write(os.path.join(self.root, '.gitignore'), '.purlin/runtime/\n')
        write(os.path.join(self.root, 'specs', 'auth', 'login.md'), spec)
        write(os.path.join(self.root, 'src', 'login.py'),
              'def login(user, password):\n'
              '    return 200 if password == "secret" else 401\n')
        write(os.path.join(self.root, 'tests', 'test_login.py'), TEST_FILE)
        git(self.root, 'init', '-q', '-b', 'main')
        git(self.root, 'config', 'user.email', 'dev@example.com')
        git(self.root, 'config', 'user.name', 'Dev')
        git(self.root, 'config', 'commit.gpgsign', 'false')
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '-m', 'chore: project under test')

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def head(self):
        return git(self.root, 'rev-parse', 'HEAD').stdout.strip()

    def spec(self, text, name='login', category='auth'):
        write(os.path.join(self.root, 'specs', category, name + '.md'), text)

    def edit_test(self, text):
        write(os.path.join(self.root, 'tests', 'test_login.py'), text)
        git(self.root, 'add', '-A')
        git(self.root, 'commit', '-q', '-m', 'test(login): edit')

    def config(self, **fields):
        path = os.path.join(self.root, '.purlin', 'config.json')
        with open(path, encoding='utf-8') as handle:
            settings = json.load(handle)
        settings.update(fields)
        write(path, json.dumps(settings))

    def proofs(self, statuses=None):
        statuses = statuses or {'PROOF-1': 'pass', 'PROOF-2': 'pass'}
        entries = []
        for proof_id, status in sorted(statuses.items()):
            entries.append({
                'feature': 'login', 'id': proof_id,
                'rule': 'RULE-1' if proof_id == 'PROOF-1' else 'RULE-2',
                'status': status,
                'test_file': 'tests/test_login.py',
                'test_name': TEST_NAMES[proof_id]})
        write(os.path.join(self.root, '.purlin', 'runtime', 'proofs',
                           'login.json'),
              json.dumps({'proofs': entries}))

    def evidence(self, statuses=None, runner='ada', strength=90,
                 commit_it=True, at='2026-09-13T12:00:00Z', tests=None,
                 source='local', os_name=None, audited=True):
        """Write a section naming the tests the runtime proofs name. Its path.

        The section carries the fingerprint taken now, so it is current until
        the spec, the scoped code or the test changes. `tests` maps a proof to
        the test names the section observed for it, for a proof backed by
        more than one test. `source` is the folder it goes in, which is what
        a reader reads the source off. With `audited` the file carries an
        `audit` too, whose `mutation` holds `strength`.
        """
        statuses = statuses or {'PROOF-1': 'pass', 'PROOF-2': 'pass'}
        os_name = os_name or purlin_evidence.host_os()
        proofs = []
        for proof_id, status in sorted(statuses.items()):
            for test_name in (tests or {}).get(proof_id,
                                               [TEST_NAMES[proof_id]]):
                proofs.append({
                    'id': proof_id,
                    'rule': 'RULE-1' if proof_id == 'PROOF-1' else 'RULE-2',
                    'result': status, 'env': None, 'manual': False,
                    'test': 'tests/test_login.py::%s' % test_name})
        rel = '.purlin/evidence/%s/login.json' % source
        data = self._read_evidence(rel, source)
        data['platforms'][os_name] = {
            'commit': self.head(), 'dirty': False, 'at': at,
            'runner': runner,
            'fingerprint': purlin_fingerprint.fingerprint(self.root, 'login'),
            'rules': {}, 'proofs': proofs}
        if audited:
            audit = data.setdefault('audit', {'mutation': None, 'rules': {}})
            audit['mutation'] = {'engine': 'mutmut' if strength is not None
                                 else 'none', 'score': strength, 'at': at,
                                 'commit': self.head()}
        write(os.path.join(self.root, *rel.split('/')),
              json.dumps(data, indent=2, sort_keys=True))
        if commit_it:
            git(self.root, 'add', '-A')
            git(self.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
        return rel

    def _read_evidence(self, rel, source, feature='login'):
        path = os.path.join(self.root, *rel.split('/'))
        try:
            with open(path, encoding='utf-8') as handle:
                return json.load(handle)
        except (IOError, OSError, ValueError):
            return {'schema': 'purlin-evidence/1', 'feature': feature,
                    'source': source, 'spec': 'specs/auth/%s.md' % feature,
                    'platforms': {}}

    def audit(self, rule, findings=(), settled=True, source='local',
              feature='login'):
        """Write the audit entry for a rule's current rule, proof and test hashes.

        An entry answers only while the rule, the proof and the test all
        stand as they were when the audit read them. `settled` with no
        finding is `strong`, with a finding `weak`, and not settled is
        `undecided`.
        """
        entry = self.rule(rule, feature)
        rel = '.purlin/evidence/%s/%s.json' % (source, feature)
        data = self._read_evidence(rel, source, feature)
        audit = data.setdefault('audit', {'mutation': None, 'rules': {}})
        word = ('undecided' if not settled
                else 'weak' if findings else 'strong')
        audit['rules'][rule] = {
            'rule_hash': entry['rule_hash'],
            'proof_hash': entry['proof_hash'],
            'test_hash': entry['test_hash'], 'verdict': word,
            'findings': list(findings), 'at': '2026-09-13T12:05:00Z',
            'commit': self.head()}
        write(os.path.join(self.root, *rel.split('/')),
              json.dumps(data, indent=2, sort_keys=True))
        return rel

    def payload(self):
        return purlin_payload.build_payload(self.root)

    def rule(self, rule_id, feature='login'):
        data = self.payload()
        entry = next(f for f in data['features'] if f['name'] == feature)
        return next(r for r in entry['rules'] if r['id'] == rule_id
                    and r['feature'] == feature)

    def signatures(self):
        directory = os.path.join(self.root, 'specs', 'auth',
                                 'login.signatures')
        if not os.path.isdir(directory):
            return []
        return sorted(os.listdir(directory))

    def load(self, kind='signatures'):
        reader = getattr(purlin_signatures, 'load_' + kind)
        return reader(self.root, purlin_specs.scan_specs(self.root))


@pytest.fixture
def proved():
    """A project whose rules have evidence, so a signature has something to bind."""
    made = Project()
    made.proofs()
    made.evidence()
    yield made
    made.close()


def signing_key(root, email='jane@acme.com'):
    """A throwaway ssh signing key, configured in this checkout alone."""
    key = os.path.join(root, '.git', 'signing-key')
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', email,
                    '-f', key], check=True)
    with open(key + '.pub', encoding='utf-8') as handle:
        public = handle.read().strip()
    allowed = os.path.join(root, '.git', 'allowed-signers')
    write(allowed, '%s %s\n' % (email, public))
    for name, value in (('user.email', email), ('user.name', 'Jane'),
                        ('gpg.format', 'ssh'),
                        ('user.signingkey', key + '.pub'),
                        ('commit.gpgsign', 'true'),
                        ('gpg.ssh.allowedSignersFile', allowed)):
        git(root, 'config', name, value)
    return key + '.pub'


# What the git host's build identity looks like on GitHub.
CI_COMMITTER = 'github-actions[bot]'
CI_EMAIL = '41898282+github-actions[bot]@users.noreply.github.com'


def ci_signing_key(root):
    """A throwaway ssh key this project trusts, for the CI commit to sign with.

    The key and the allowed-signers file live inside the project's own `.git`
    and nowhere else. `None` when the machine has no `ssh-keygen`, and then
    the commit is made unsigned.
    """
    key = os.path.join(root, '.git', 'ci-signing-key')
    if not os.path.exists(key + '.pub'):
        made = subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                               '-C', CI_EMAIL, '-f', key],
                              capture_output=True, text=True)
        if made.returncode != 0:
            return None
    with open(key + '.pub', encoding='utf-8') as handle:
        public = handle.read().strip()
    allowed = os.path.join(root, '.git', 'ci-allowed-signers')
    write(allowed, '%s %s\n' % (CI_EMAIL, ' '.join(public.split()[:2])))
    git(root, 'config', 'gpg.ssh.allowedSignersFile', allowed)
    return key + '.pub'


def commit_as_ci(root, message='purlin: evidence at abc1234'):
    """Commit everything staged under the build identity, as CI does.

    CI writes through the git host's API, which signs the commit: the reader
    reads an unsigned commit claiming that identity as a person's, so a
    fixture that leaves the signature out is not what CI writes and a file
    it wrote would be read as a developer's on any machine that can check
    signatures. The signature here is a throwaway ssh key the project itself
    trusts. Call it before `signing_key`, which points the allowed-signers
    file back at the person.
    """
    environment = dict(os.environ,
                       GIT_COMMITTER_NAME=CI_COMMITTER,
                       GIT_COMMITTER_EMAIL=CI_EMAIL)
    key = ci_signing_key(root)
    subprocess.run(['git', 'add', '-A'], cwd=root, capture_output=True,
                   text=True)
    command = ['git']
    if key:
        command += ['-c', 'gpg.format=ssh', '-c', 'user.signingkey=' + key]
    command += ['commit', '-q', '-m', message]
    if key:
        command.append('-S')
    subprocess.run(command, cwd=root, env=environment, capture_output=True,
                   text=True)


def sign_one(project, rule='RULE-1', email='jane@acme.com', evidence=None,
             gate='passed', level=None, note=None):
    """Write one signature for a rule and return its project-relative path."""
    entry = project.rule(rule)
    return sign_module.write_signature(
        project.root, 'login', rule, email, evidence, gate,
        entry['level'] if level is None else level, entry=entry, note=note)


# ---------------------------------------------------------------------------
# The triple
# ---------------------------------------------------------------------------

class TestTheTriple:

    @pytest.mark.proof("signatures", "PROOF-1", "RULE-1")
    def test_the_three_hashes_come_back_with_their_kind(self, proved):
        parts = sign_module.rule_proof_test_hashes(
            proved.root, 'login', 'RULE-1')
        rule_hash, proof_hash, test_hash, kind = parts
        assert len(rule_hash) == 64 and len(proof_hash) == 64
        assert len(test_hash) == 64
        assert kind == 'file'

    @pytest.mark.proof("signatures", "PROOF-2", "RULE-2")
    def test_a_rule_that_is_not_there_has_no_hashes(self, proved):
        assert sign_module.rule_proof_test_hashes(
            proved.root, 'login', 'RULE-99') == (None, None, None, None)

    @pytest.mark.proof("signatures", "PROOF-3", "RULE-3")
    def test_reflowing_a_rule_and_changing_its_level_keep_the_triple(self,
                                                                     proved):
        before = sign_module.triple_for(proved.rule('RULE-1'))
        proved.spec(SPEC.replace(
            '- RULE-1: Valid credentials return 200 with a session token '
            '[level: passed]',
            '- RULE-1: Valid   credentials  return 200  with a session token '
            '[level: signed]'))
        after = sign_module.triple_for(proved.rule('RULE-1'))
        assert after == before, (
            'the triple binds the rule text with its tag stripped')

    @pytest.mark.proof("signatures", "PROOF-4", "RULE-4")
    def test_editing_the_rule_the_proof_or_the_test_moves_the_triple(
            self, proved):
        before = sign_module.triple_for(proved.rule('RULE-1'))

        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 201 with a session token'))
        rule_changed = sign_module.triple_for(proved.rule('RULE-1'))
        assert rule_changed != before

        proved.spec(SPEC.replace('verify 200 and a token',
                                 'verify 200 and a token that expires'))
        proof_changed = sign_module.triple_for(proved.rule('RULE-1'))
        assert proof_changed != before

        proved.spec(SPEC)
        proved.edit_test(TEST_FILE.replace('== 200', '== 200  # checked'))
        test_changed = sign_module.triple_for(proved.rule('RULE-1'))
        assert test_changed != before

    @pytest.mark.proof("signatures", "PROOF-5", "RULE-5")
    def test_a_manual_proof_says_so_instead_of_naming_a_file(self):
        made = Project(spec=SPEC.replace(
            'verify 401 and the body "denied"',
            'verify 401 and the body "denied" @manual'))
        try:
            parts = sign_module.rule_proof_test_hashes(
                made.root, 'login', 'RULE-2')
            assert parts[3] == 'manual'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Stale
# ---------------------------------------------------------------------------

class TestStale:

    def _current(self, project, rule='RULE-1'):
        entry = project.rule(rule)
        found = project.load().get(('login', rule)) or []
        return [s for s in found
                if purlin_signatures.is_current(
                    s, entry['rule_hash'], entry['proof_hash'],
                    entry['test_hash'])]

    @pytest.mark.proof("signatures", "PROOF-6", "RULE-6")
    def test_a_fresh_signature_is_current(self, proved):
        sign_one(proved)
        assert len(self._current(proved)) == 1

    @pytest.mark.proof("signatures", "PROOF-7", "RULE-6")
    def test_the_rule_text_changing_stales_it(self, proved):
        sign_one(proved)
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with a signed session token'))
        assert self._current(proved) == []

    @pytest.mark.proof("signatures", "PROOF-8", "RULE-6")
    def test_the_proof_text_changing_stales_it(self, proved):
        sign_one(proved)
        proved.spec(SPEC.replace('verify 200 and a token',
                                 'verify 200, a token and a cookie'))
        assert self._current(proved) == []

    @pytest.mark.proof("signatures", "PROOF-9", "RULE-6")
    def test_the_test_changing_stales_it(self, proved):
        sign_one(proved)
        proved.edit_test(TEST_FILE.replace('== 200', '== 200 or True'))
        assert self._current(proved) == []

    @pytest.mark.proof("signatures", "PROOF-10", "RULE-6")
    def test_the_level_changing_leaves_it_current(self, proved):
        sign_one(proved)
        assert len(self._current(proved)) == 1
        proved.spec(SPEC.replace(
            '- RULE-1: Valid credentials return 200 with a session token '
            '[level: passed]',
            '- RULE-1: Valid credentials return 200 with a session token '
            '[level: strong]'))
        assert len(self._current(proved)) == 1, (
            'the level is logged in a signature, not locked')

    @pytest.mark.proof("signatures", "PROOF-11", "RULE-7")
    def test_a_stale_signature_still_comes_back_from_the_reader(self, proved):
        sign_one(proved)
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with two session tokens'))
        found = proved.load()[('login', 'RULE-1')]
        assert len(found) == 1, found
        assert found[0]['signer'] == 'jane@acme.com'
        assert self._current(proved) == [], (
            'the signed cell reads stale only while the file is still there')


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

class TestTheFile:

    @pytest.mark.proof("signatures", "PROOF-12", "RULE-8")
    def test_the_name_carries_the_rule_the_triple_and_the_slug(self, proved):
        triple = sign_module.triple_for(proved.rule('RULE-1'))
        sign_one(proved, email='Rich.LaBarca+purlin@example.com')
        assert proved.signatures() == [
            'RULE-1.%s.rich-labarca-purlin.json' % triple[:8]]

    @pytest.mark.proof("signatures", "PROOF-13", "RULE-9")
    def test_the_fields_are_the_ones_the_format_names(self, proved):
        evidence = proved.evidence()
        path = sign_one(proved, evidence=evidence, gate='strong')
        with open(os.path.join(proved.root, path), encoding='utf-8') as handle:
            data = json.load(handle)
        assert data['schema'] == 'purlin-signature/1'
        assert set(data) == {
            'schema', 'feature', 'rule', 'triple', 'rule_hash', 'proof_hash',
            'test_hash', 'test_hash_kind', 'audit_hash', 'level',
            'signer', 'machine', 'os', 'note', 'timestamp', 'gate',
            'evidence'}
        assert data['feature'] == 'login' and data['rule'] == 'RULE-1'
        assert data['triple'] == sign_module.triple_for(
            proved.rule('RULE-1'))[:16]
        assert data['signer'] == 'jane@acme.com'
        assert data['note'] is None
        assert data['level'] == 'passed'
        assert data['evidence'] == '.purlin/evidence/local/login.json'
        assert data['timestamp'].endswith('Z')

    @pytest.mark.proof("signatures", "PROOF-63", "RULE-42")
    def test_the_evidence_it_names_is_the_file_the_run_wrote(self, proved):
        """A signature names the evidence file a reader can open."""
        assert sign_module.evidence_for(proved.payload(), 'login') == \
            '.purlin/evidence/local/login.json'
        proved.evidence(source='ci', commit_it=False)
        assert sign_module.evidence_for(proved.payload(), 'login') == \
            '.purlin/evidence/local/login.json', 'the local file comes first'
        os.remove(os.path.join(proved.root, '.purlin', 'evidence', 'local',
                               'login.json'))
        assert sign_module.evidence_for(proved.payload(), 'login') == \
            '.purlin/evidence/ci/login.json'
        assert sign_module.evidence_for(proved.payload(), 'nosuch') is None

    @pytest.mark.proof("signatures", "PROOF-14", "RULE-10")
    def test_the_reader_finds_it(self, proved):
        sign_one(proved)
        loaded = proved.load()
        assert len(loaded[('login', 'RULE-1')]) == 1
        assert loaded[('login', 'RULE-1')][0]['signer'] == 'jane@acme.com'


# ---------------------------------------------------------------------------
# The signed commit
# ---------------------------------------------------------------------------

@pytest.fixture
def at_strong():
    """The same project at the gate that turns the queue on."""
    made = Project(gate=REVIEW_GATE)
    made.proofs()
    made.evidence()
    yield made
    made.close()


# The spec with both rules at the level `signed`, the gate's own.
EVERY_RULE_SIGNED = SPEC.replace(' [level: passed]', '')


def signing_project(every_rule=True, signer='jane@acme.com', audits=True):
    """A project at the signing gate whose rules are waiting to be signed.

    The evidence is CI's, and the person's signing key is configured last so
    the allowed-signers file names the person rather than the build
    identity. With `every_rule` both rules take the gate's level, `signed`;
    without it `RULE-1` is marked `[level: passed]` and asks for none. Every
    rule whose level is `signed` carries an audit entry, so its tests and its
    audit are met and the only thing outstanding is a person.
    """
    made = Project(gate=SIGNING_GATE,
                   spec=EVERY_RULE_SIGNED if every_rule else SPEC)
    made.proofs()
    made.evidence(runner='ci', commit_it=False, source='ci')
    if audits:
        made.audit('RULE-2')
        if every_rule:
            made.audit('RULE-1')
    commit_as_ci(made.root)
    signing_key(made.root, signer)
    return made


class TestTheSignedCommit:

    @pytest.mark.proof("signatures", "PROOF-21", "RULE-17")
    def test_without_signing_the_setup_is_printed_and_nothing_is_written(
            self, at_strong, capsys):
        code = sign_module.main(['login', '--project-root', at_strong.root])
        output = capsys.readouterr().out
        assert code == 1
        assert 'git config gpg.format ssh' in output
        assert 'git config user.signingkey ~/.ssh/id_ed25519.pub' in output
        assert 'git config commit.gpgsign true' in output
        assert at_strong.signatures() == []

    @pytest.mark.proof("signatures", "PROOF-23", "RULE-18")
    def test_one_signed_commit_carries_the_batch(self, capsys):
        made = signing_project()
        try:
            code = sign_module.main(['login', '--project-root', made.root])
            capsys.readouterr()
            assert code == 0
            assert len(made.signatures()) == 2
            log = git(made.root, 'log', '-1', '--format=%G?%n%s').stdout
            signature, subject = log.strip().splitlines()
            assert signature == 'G', log
            assert subject == 'sign(login): RULE-1 RULE-2', subject
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-25", "RULE-20")
    def test_what_a_counting_signature_is_at_each_gate(self, at_strong):
        signing_key(at_strong.root)
        # The signer is the last person to touch the test, and that is
        # logged, not policed: git names both authors.
        at_strong.edit_test(TEST_FILE + '\n')
        assert git(at_strong.root, 'log', '-1', '--format=%ae', '--',
                   'tests/test_login.py').stdout.strip() == 'jane@acme.com'
        sign_module.main(['login', 'RULE-1', '--project-root', at_strong.root])
        found = at_strong.load()[('login', 'RULE-1')][0]

        counted, reason = purlin_signatures.counts(
            at_strong.root, found, gate='signed')
        assert counted, reason
        counted, reason = purlin_signatures.counts(
            at_strong.root, found, gate='strong')
        assert counted, reason

        unsigned = sign_one(at_strong, 'RULE-2')
        git(at_strong.root, 'add', '-A')
        git(at_strong.root, '-c', 'commit.gpgsign=false', 'commit', '-q',
            '-m', 'sign(login): RULE-2')
        assert git(at_strong.root, 'log', '-1', '--format=%G?').stdout \
            .strip() == 'N'
        found = next(item for item in at_strong.load()[('login', 'RULE-2')]
                     if item['path'] == unsigned)
        counted, reason = purlin_signatures.counts(
            at_strong.root, found, gate='signed')
        assert not counted and reason == 'the signing commit is not signed'
        counted, reason = purlin_signatures.counts(
            at_strong.root, found, gate='strong')
        assert counted, (
            'below signed a committed signature counts: %s' % reason)

    @pytest.mark.proof("signatures", "PROOF-24", "RULE-19")
    def test_a_batch_across_features_names_each_one(self):
        assert sign_module.commit_message(
            [('login', 'RULE-1'), ('login', 'RULE-2')]) == (
            'sign(login): RULE-1 RULE-2')
        assert sign_module.commit_message(
            [('login', 'RULE-1'), ('billing', 'RULE-3')]) == (
            'sign(batch): login RULE-1, billing RULE-3')

    @pytest.mark.proof("signatures", "PROOF-27", "RULE-21")
    def test_the_signing_gate_names_nobody_and_signs(self, capsys):
        made = signing_project(every_rule=False)
        try:
            code = sign_module.main(['--batch', '--project-root', made.root])
            output = capsys.readouterr().out
            assert code == 0, output
            assert any(name.startswith('RULE-2.')
                       for name in made.signatures()), made.signatures()
            assert 'purlin:init --gate signed' not in output, output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-15", "RULE-12")
    def test_a_batch_signs_everything_in_the_queue(self, capsys):
        made = signing_project(every_rule=False)
        try:
            code = sign_module.main(['--batch', '--project-root', made.root])
            output = capsys.readouterr().out
            assert code == 0, output
            assert made.signatures() == [
                name for name in made.signatures() if name.startswith('RULE-2.')
            ], made.signatures()
            assert 'Signed 1 rule in' in output, output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-16", "RULE-13")
    def test_a_note_records_what_the_signer_checked(self, capsys):
        made = signing_project()
        try:
            code = sign_module.main(
                ['login', 'RULE-2', '--note', 'I ran the lockout by hand.',
                 '--project-root', made.root])
            capsys.readouterr()
            assert code == 0
            path = made.load()[('login', 'RULE-2')][0]['path']
            with open(os.path.join(made.root, path), encoding='utf-8') as f:
                assert json.load(f)['note'] == 'I ran the lockout by hand.'
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-17", "RULE-13")
    def test_a_note_needs_a_rule_and_a_line(self):
        for argv in (['login', 'RULE-1', '--note'],
                     ['login', '--note', 'a line'],
                     ['--batch', '--note', 'a line']):
            assert sign_module.main(argv + ['--project-root', '.']) == 2, argv


# ---------------------------------------------------------------------------
# What the gate lets the command do
# ---------------------------------------------------------------------------

class TestTheGateScales:

    @pytest.mark.proof("signatures", "PROOF-18", "RULE-14")
    def test_under_the_first_gate_it_writes_nothing_and_exits_two(
            self, proved, capsys):
        signing_key(proved.root)
        code = sign_module.main(['login', 'RULE-1', '--project-root',
                                 proved.root])
        output = capsys.readouterr().out
        assert code == 2
        assert 'the gate is passed, which asks for no signature.' in output
        assert 'purlin:init --gate strong' in output
        assert proved.signatures() == []

    @pytest.mark.proof("signatures", "PROOF-19", "RULE-15")
    def test_under_the_review_gate_a_bare_signature_says_so_and_is_written(
            self, at_strong, capsys):
        signing_key(at_strong.root)
        code = sign_module.main(['login', 'RULE-1', '--project-root',
                                 at_strong.root])
        output = capsys.readouterr().out
        assert code == 0, output
        assert 'required only under the gate signed' in output
        assert len(at_strong.signatures()) == 1


def unsettled_at_strong():
    """A project at `strong` whose unmarked rule is a hand check in the queue."""
    made = Project(gate=REVIEW_GATE)
    made.proofs()
    made.evidence()
    made.audit('RULE-2', settled=False)
    git(made.root, 'add', '-A')
    git(made.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
    signing_key(made.root)
    return made


class TestTheQueueAtStrong:

    @pytest.mark.proof("signatures", "PROOF-70", "RULE-12")
    def test_a_batch_and_a_bare_feature_sign_the_queue(self, capsys):
        for argv in (['--batch'], ['login']):
            made = unsettled_at_strong()
            try:
                assert [row['rule'] for row in made.payload()['queue']] \
                    == ['RULE-2']
                code = sign_module.main(argv + ['--project-root', made.root])
                output = capsys.readouterr().out
                assert code == 0, (argv, output)
                assert 'Signed 1 rule in' in output, output
                names = made.signatures()
                assert len(names) == 1 and names[0].startswith('RULE-2.'), (
                    argv, names)
                assert 'required only' not in output, output
            finally:
                made.close()

    @pytest.mark.proof("signatures", "PROOF-71", "RULE-15")
    def test_a_named_rule_in_the_queue_is_not_told_it_needs_none(
            self, capsys):
        made = unsettled_at_strong()
        try:
            code = sign_module.main(['login', 'RULE-2', '--project-root',
                                     made.root])
            output = capsys.readouterr().out
            assert code == 0, output
            assert len(made.signatures()) == 1
            assert 'required only under the gate signed' not in output, output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What a person may sign now
# ---------------------------------------------------------------------------

class TestWhatIsQueued:

    @pytest.mark.proof("signatures", "PROOF-20", "RULE-16")
    def test_it_is_the_queue_the_payload_wrote(self):
        made = signing_project(every_rule=False)
        try:
            assert sign_module.queued(made.payload()) == [
                ('login', 'RULE-2')], (
                'only the rule whose level is signed needs a signature')
            sign_module.main(['login', 'RULE-2', '--project-root', made.root])
            assert sign_module.queued(made.payload()) == []
            made.spec(SPEC.replace('return 401 and the body "denied"',
                                   'return 403 and the body "denied"'))
            made.evidence(runner='ci', commit_it=False, source='ci')
            made.audit('RULE-2')
            assert sign_module.queued(made.payload()) == [
                ('login', 'RULE-2')], 'a stale signature is queued again'
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-30", "RULE-16")
    def test_a_rule_that_needs_both_is_one_hand_check(self):
        made = signing_project(every_rule=False, audits=False)
        try:
            payload = made.payload()
            assert payload['queue'] == []
            assert sign_module.queued(payload) == [], (
                'the rule whose level is signed has no audit entry, so its '
                'strong cell is not met')
            made.audit('RULE-2', settled=False)
            payload = made.payload()
            assert [(row['rule'], row['need']) for row in payload['queue']] \
                == [('RULE-2', 'hand check')], payload['queue']
            assert sign_module.queued(payload) == [('login', 'RULE-2')], (
                'the queue is what a batch signs')
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The level
# ---------------------------------------------------------------------------

class TestTheLevel:

    @pytest.mark.proof("signatures", "PROOF-62", "RULE-41")
    def test_the_level_is_logged_and_not_locked(self, capsys):
        made = signing_project(every_rule=False)
        try:
            code = sign_module.main(['login', 'RULE-2', '--project-root',
                                     made.root])
            capsys.readouterr()
            assert code == 0
            path = made.load()[('login', 'RULE-2')][0]['path']
            with open(os.path.join(made.root, path), encoding='utf-8') as f:
                assert json.load(f)['level'] == 'signed'
            assert made.rule('RULE-2')['cells']['signed']['word'] == 'signed'
            made.spec(SPEC.replace('"denied"\n', '"denied" [level: strong]\n',
                                   1))
            made.evidence(runner='ci', commit_it=False, source='ci')
            rule = made.rule('RULE-2')
            assert rule['level'] == 'strong', rule
            assert rule['cells']['signed']['word'] == 'signed', rule
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-72", "RULE-48")
    def test_a_rule_marked_below_signed_is_refused_by_name(self, capsys):
        made = signing_project(every_rule=False)
        try:
            code = sign_module.main(['login', 'RULE-1', '--project-root',
                                     made.root])
            output = capsys.readouterr().out
            assert code == 1, output
            assert ('sign: login RULE-1 is marked [level: passed]; it asks '
                    'for no signature.') in output, output
            assert made.signatures() == []
            made.spec(SPEC.replace('[level: passed]', '[level: strong]'))
            code = sign_module.main(['login', 'RULE-1', '--project-root',
                                     made.root])
            output = capsys.readouterr().out
            assert code == 1, output
            assert 'is marked [level: strong]' in output, output
            code = sign_module.main(['login', 'RULE-1', 'RULE-2',
                                     '--project-root', made.root])
            output = capsys.readouterr().out
            assert code == 0, output
            assert [name.split('.')[0] for name in made.signatures()] == [
                'RULE-2'], made.signatures()
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

class TestTheWalk:

    @pytest.mark.proof("signatures", "PROOF-31", "RULE-11")
    def test_the_walk_opens_on_the_queue_and_signs_with_a_note(self, capsys):
        made = signing_project(every_rule=False)
        try:
            made.spec(SPEC.replace('verify 401 and the body "denied"\n',
                                   'verify 401 and the body "denied" '
                                   '@manual\n'))
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'docs: a proof by hand')
            seen = []

            def answer(entry, rendered):
                seen.append((entry['id'], entry['need'], rendered))
                return ('sign', 'The lockout page read 401 and "denied".')

            given = sign_module.walk(made.root, answer=answer)
            output = capsys.readouterr().out
            assert output.startswith(
                'Queue: 1 rule. 1 hand check, 0 signatures.'), output
            assert [(rule, need) for rule, need, _text in seen] == [
                ('RULE-2', 'hand check')], seen
            rendered = seen[0][2].splitlines()
            assert rendered[0] == 'login RULE-2   level signed   hand check'
            assert rendered[1:3] == [
                'Rule', '  Invalid credentials return 401 and the body '
                '"denied"'], rendered
            assert '  PROOF-2 (@manual): POST /login with a bad password; '\
                'verify 401 and the body "denied"' in rendered, rendered
            assert 'What the audit found' in rendered, rendered
            assert given['signed'] == [('login', 'RULE-2')], given
            assert len(given['commits']) == 1, given
            path = made.load()[('login', 'RULE-2')][0]['path']
            with open(os.path.join(made.root, path), encoding='utf-8') as f:
                assert json.load(f)['note'] == (
                    'The lockout page read 401 and "denied".')
            assert ('Walked 1 rule: 1 signed, 0 cases added, 0 skipped.'
                    in output), output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-31", "RULE-11")
    def test_a_signature_row_names_what_went_stale(self, capsys):
        made = signing_project(every_rule=False)
        try:
            sign_module.main(['login', 'RULE-2', '--project-root', made.root])
            made.spec(SPEC.replace('return 401 and the body "denied"',
                                   'return 403 and the body "denied"'))
            made.evidence(runner='ci', commit_it=False, source='ci')
            made.audit('RULE-2')
            commit_as_ci(made.root)
            capsys.readouterr()
            seen = []
            sign_module.walk(made.root, answer=lambda entry, text: (
                seen.append(text) or 'skip'))
            assert seen[0].splitlines()[0] == (
                'login RULE-2   level signed   signature   stale: hashes '
                'changed after the signature'), seen
            assert '  Strong. It found nothing.' in seen[0].splitlines(), seen
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-32", "RULE-11")
    def test_a_skipped_rule_is_written_nothing_and_stays_in_the_queue(
            self, capsys):
        made = signing_project()
        try:
            given = sign_module.walk(made.root,
                                     answer=lambda _entry, _text: 'skip')
            output = capsys.readouterr().out
            assert given['signed'] == []
            assert len(given['skipped']) == 2
            assert made.signatures() == []
            assert 'Walked 2 rules: 0 signed, 0 cases added, 2 skipped.' in \
                output, output
            assert 'Run: purlin:sign' in output, output
            assert len(made.payload()['queue']) == 2
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-33", "RULE-11")
    def test_a_case_is_carried_to_the_close_and_written_nowhere(self, capsys):
        made = signing_project()
        try:
            given = sign_module.walk(
                made.root,
                answer=lambda _entry, _text: ('case', 'it should also reject '
                                              'an expired token'))
            output = capsys.readouterr().out
            assert len(given['cases']) == 2
            assert made.signatures() == []
            assert 'it should also reject an expired token' in output
            assert 'Run: purlin:build' in output, output
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What a signature rests on, and where it was made
# ---------------------------------------------------------------------------

class TestWhatItRestsOn:

    @pytest.mark.proof("signatures", "PROOF-75", "RULE-50")
    def test_a_signature_names_the_machine_and_its_system_and_hashes_neither(
            self, capsys):
        import platform
        made = signing_project(every_rule=False)
        try:
            code = sign_module.main(['login', 'RULE-2', '--project-root',
                                     made.root])
            capsys.readouterr()
            assert code == 0
            path = os.path.join(
                made.root, made.load()[('login', 'RULE-2')][0]['path'])
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            assert data['machine'] == platform.node(), data
            assert data['os'] == purlin_evidence.host_os(), data
            assert data['os'] in ('windows', 'macos', 'linux'), data
            data.update(machine='another-machine', os='windows')
            write(path, json.dumps(data))
            git(made.root, 'add', '-A')
            git(made.root, 'commit', '-q', '-m', 'sign(login): RULE-2')
            assert made.rule('RULE-2')['cells']['signed']['word'] == 'signed'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# Any branch
# ---------------------------------------------------------------------------

class TestAnyBranch:

    @pytest.mark.proof("signatures", "PROOF-29", "RULE-23")
    def test_a_signature_on_a_side_branch_counts_there(self, capsys):
        made = signing_project(every_rule=False)
        try:
            git(made.root, 'checkout', '-q', '-b', 'side')
            code = sign_module.main(['login', 'RULE-2', '--project-root',
                                     made.root])
            capsys.readouterr()
            assert code == 0
            on_main = git(made.root, 'ls-tree', '-r', '--name-only', 'main',
                          'specs/auth/login.signatures').stdout.strip()
            assert on_main == '', 'main does not carry the signature'
            cell = made.rule('RULE-2')['cells']['signed']
            assert cell['word'] == 'signed', cell
            assert not any('branch' in reason or ' on main' in reason
                           for reason in cell.get('reasons') or ()), cell
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    @pytest.mark.proof("signatures", "PROOF-28", "RULE-22")
    def test_help_exits_zero_and_a_bad_option_exits_two(self):
        assert sign_module.main(['--help']) == 0
        assert sign_module.main(['login', '--nope']) == 2
        assert sign_module.main(['--nope']) == 2

    @pytest.mark.proof("signatures", "PROOF-22", "RULE-17")
    def test_the_script_runs_as_a_command(self, at_strong):
        result = subprocess.run(
            [sys.executable, SIGN_PY, 'login', '--project-root',
             at_strong.root], capture_output=True, text=True, timeout=120)
        assert result.returncode == 1, result.stdout + result.stderr
        assert 'git config gpg.format ssh' in result.stdout
