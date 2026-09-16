"""Tests for the signature reader and the command that writes one.

Every fixture is written by the test in a throwaway project: a spec, a test
file, a runtime proof file, a record, a signature. Nothing here reads this
repository's own specs, reaches a network, or signs with a key that exists
anywhere but the temporary directory the test made.

What each group holds:

*the triple*   the three hashes a signature binds, and what does and does not
               change them: reflowing a rule and adding a tag do not, editing
               the rule, the proof or the test do
*stale*        a signature stops being current when any part of the triple or
               the risk moves under it
*the file*     the name, the fields, and the brief the reader steps over
*the commit*   one signed commit for a batch, and the exact setup to print
               when this checkout cannot sign
*ancestor*     a signature on a side branch is not on the protected branch
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
from purlin import gate as purlin_gate  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402
from purlin import signatures as purlin_signatures  # noqa: E402
from purlin import specs as purlin_specs  # noqa: E402

SIGN_PY = os.path.join(ROOT, 'scripts', 'review', 'sign.py')

# The three gates by position: the one a project sits at by default, the one
# that turns the breaks and the review list on, and the one that asks for a
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
    '[risk: low]\n'
    '- RULE-2: Invalid credentials return 401 and the body "denied" '
    '[risk: high]\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with the password "secret"; verify 200 '
    'and a token @integration\n'
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

    def proofs(self, statuses=None, tier='unit'):
        statuses = statuses or {'PROOF-1': 'pass', 'PROOF-2': 'pass'}
        entries = []
        for proof_id, status in sorted(statuses.items()):
            entries.append({
                'feature': 'login', 'id': proof_id,
                'rule': 'RULE-1' if proof_id == 'PROOF-1' else 'RULE-2',
                'status': status, 'tier': tier,
                'test_file': 'tests/test_login.py',
                'test_name': TEST_NAMES[proof_id]})
        write(os.path.join(self.root, '.purlin', 'runtime', 'proofs',
                           'login.%s.json' % tier),
              json.dumps({'tier': tier, 'proofs': entries}))

    def record(self, statuses=None, runner='ada', strength=90,
               commit_it=True, stamp='20260913T120000Z', tests=None):
        """Write a record naming the tests the runtime proofs name.

        `tests` maps a proof to the test names the record observed for it, for
        a proof backed by more than one test.
        """
        statuses = statuses or {'PROOF-1': 'pass', 'PROOF-2': 'pass'}
        proofs = []
        for proof_id, status in sorted(statuses.items()):
            for test_name in (tests or {}).get(proof_id,
                                               [TEST_NAMES[proof_id]]):
                proofs.append({
                    'id': proof_id,
                    'rule': 'RULE-1' if proof_id == 'PROOF-1' else 'RULE-2',
                    'status': status, 'tier': 'unit', 'env': None,
                    'test_file': 'tests/test_login.py',
                    'test_name': test_name})
        name = '%s-%s-%s.json' % (stamp, self.head()[:7], runner)
        rel = '.purlin/records/login/' + name
        iso = '%s-%s-%sT%s:%s:%sZ' % (stamp[0:4], stamp[4:6], stamp[6:8],
                                      stamp[9:11], stamp[11:13], stamp[13:15])
        write(os.path.join(self.root, rel), json.dumps({
            'schema_version': 1, 'feature': 'login', 'commit': self.head(),
            'timestamp': iso, 'runner': runner,
            'os': None, 'gate': FIRST_GATE, 'test_strength': strength,
            'scope_tree': purlin_specs.scope_tree(self.root, ['src/login.py']),
            'proofs': proofs}))
        if commit_it:
            git(self.root, 'add', '-A')
            git(self.root, 'commit', '-q', '-m', 'purlin: record for abc1234')
        return rel

    def brief(self, rule, observations=(), settled=True):
        """Write the brief CI would commit for a rule's current triple.

        A brief is named for the triple it was built from, so it is found
        again only while the rule, the proof and the test all stand as they
        were when the model read them.
        """
        entry = self.rule(rule)
        triple = purlin_signatures.triple_hash(
            entry['rule_hash'], entry['proof_hash'], entry['test_hash'])
        rel = '.purlin/briefs/login/%s.%s.brief.json' % (rule, triple[:8])
        write(os.path.join(self.root, *rel.split('/')), json.dumps({
            'schema': 'purlin-brief/2', 'feature': 'login', 'rule': rule,
            'risk': entry['risk'], 'observations': list(observations),
            'settled': settled, 'tests': []}))
        return rel

    def payload(self):
        return purlin_payload.build_payload(self.root)

    def rule(self, rule_id):
        data = self.payload()
        entry = next(f for f in data['features'] if f['name'] == 'login')
        return next(r for r in entry['rules'] if r['id'] == rule_id)

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
    """A project whose rules have a record, so a signature has something to bind."""
    made = Project()
    made.proofs()
    made.record()
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


def commit_as_ci(root, message='purlin: record for abc1234'):
    """Commit everything staged under the build identity, as CI does.

    CI writes through the git host's API, which signs the commit: the reader
    reads an unsigned commit claiming that identity as a person's, so a
    fixture that leaves the signature out is not what CI writes and a record
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


def sign_one(project, rule='RULE-1', email='jane@acme.com', brief=None,
             record=None, gate='passed', risk=None, note=None):
    """Write one signature for a rule and return its project-relative path."""
    entry = project.rule(rule)
    return sign_module.write_signature(
        project.root, 'login', rule, email, brief, record, gate,
        entry['risk'] if risk is None else risk, entry=entry, note=note)


# ---------------------------------------------------------------------------
# The triple
# ---------------------------------------------------------------------------

class TestTheTriple:

    @pytest.mark.proof("signatures", "PROOF-1", "RULE-1", tier="integration")
    def test_the_three_hashes_come_back_with_their_kind(self, proved):
        parts = sign_module.rule_proof_test_hashes(
            proved.root, 'login', 'RULE-1')
        rule_hash, proof_hash, test_hash, kind, design = parts
        assert len(rule_hash) == 64 and len(proof_hash) == 64
        assert len(test_hash) == 64
        assert kind == 'file'
        assert design is None

    @pytest.mark.proof("signatures", "PROOF-2", "RULE-2", tier="integration")
    def test_a_rule_that_is_not_there_has_no_hashes(self, proved):
        assert sign_module.rule_proof_test_hashes(
            proved.root, 'login', 'RULE-99') == (None, None, None, None, None)

    @pytest.mark.proof("signatures", "PROOF-3", "RULE-3", tier="integration")
    def test_reflowing_a_rule_and_adding_a_tag_keep_the_triple(self, proved):
        before = sign_module.triple_for(proved.rule('RULE-1'))
        proved.spec(SPEC.replace(
            '- RULE-1: Valid credentials return 200 with a session token '
            '[risk: low]',
            '- RULE-1: Valid   credentials  return 200  with a session token '
            '[origin: pm] [risk: low]'))
        after = sign_module.triple_for(proved.rule('RULE-1'))
        assert after == before, (
            'the triple binds the rule text with its tags stripped')

    @pytest.mark.proof("signatures", "PROOF-4", "RULE-4", tier="integration")
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

    @pytest.mark.proof("signatures", "PROOF-5", "RULE-5", tier="integration")
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
                    entry['test_hash'], entry['risk'], entry['design_hash'])]

    @pytest.mark.proof("signatures", "PROOF-6", "RULE-6", tier="integration")
    def test_a_fresh_signature_is_current(self, proved):
        sign_one(proved)
        assert len(self._current(proved)) == 1

    @pytest.mark.proof("signatures", "PROOF-7", "RULE-6", tier="integration")
    def test_the_rule_text_changing_stales_it(self, proved):
        sign_one(proved)
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with a signed session token'))
        assert self._current(proved) == []

    @pytest.mark.proof("signatures", "PROOF-8", "RULE-6", tier="integration")
    def test_the_proof_text_changing_stales_it(self, proved):
        sign_one(proved)
        proved.spec(SPEC.replace('verify 200 and a token',
                                 'verify 200, a token and a cookie'))
        assert self._current(proved) == []

    @pytest.mark.proof("signatures", "PROOF-9", "RULE-6", tier="integration")
    def test_the_test_changing_stales_it(self, proved):
        sign_one(proved)
        proved.edit_test(TEST_FILE.replace('== 200', '== 200 or True'))
        assert self._current(proved) == []

    @pytest.mark.proof("signatures", "PROOF-10", "RULE-6", tier="integration")
    def test_the_risk_changing_stales_it(self, proved):
        sign_one(proved)
        proved.spec(SPEC.replace(
            '- RULE-1: Valid credentials return 200 with a session token '
            '[risk: low]',
            '- RULE-1: Valid credentials return 200 with a session token '
            '[risk: high]'))
        assert self._current(proved) == [], (
            'raising a rule from low to high changes what signing it meant')

    @pytest.mark.proof("signatures", "PROOF-11", "RULE-7", tier="integration")
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

    @pytest.mark.proof("signatures", "PROOF-12", "RULE-8", tier="integration")
    def test_the_name_carries_the_rule_the_triple_and_the_slug(self, proved):
        triple = sign_module.triple_for(proved.rule('RULE-1'))
        sign_one(proved, email='Rich.LaBarca+purlin@example.com')
        assert proved.signatures() == [
            'RULE-1.%s.rich-labarca-purlin.json' % triple[:8]]

    @pytest.mark.proof("signatures", "PROOF-13", "RULE-9", tier="integration")
    def test_the_fields_are_the_ones_the_format_names(self, proved):
        record = proved.record()
        path = sign_one(
            proved, brief='.purlin/briefs/login/RULE-1.brief.json',
            record=record, gate='strong')
        with open(os.path.join(proved.root, path), encoding='utf-8') as handle:
            data = json.load(handle)
        assert data['schema'] == 'purlin-signature/1'
        assert set(data) == {
            'schema', 'feature', 'rule', 'triple', 'rule_hash', 'proof_hash',
            'test_hash', 'test_hash_kind', 'design_hash', 'risk', 'signer',
            'note', 'timestamp', 'gate', 'brief', 'record'}
        assert data['feature'] == 'login' and data['rule'] == 'RULE-1'
        assert data['triple'] == sign_module.triple_for(
            proved.rule('RULE-1'))[:16]
        assert data['signer'] == 'jane@acme.com'
        assert data['note'] is None
        assert data['risk'] == 'low'
        assert data['record'] == record
        assert data['timestamp'].endswith('Z')

    @pytest.mark.proof("signatures", "PROOF-14", "RULE-10", tier="integration")
    def test_the_reader_finds_it_and_never_reads_a_brief_as_one(self, proved):
        triple = sign_module.triple_for(proved.rule('RULE-1'))
        sign_one(proved)
        write(os.path.join(proved.root, 'specs', 'auth', 'login.signatures',
                           'RULE-1.%s.brief.json' % triple[:8]),
              json.dumps({'schema': 'purlin-brief/1', 'rule': 'RULE-1'}))
        loaded = proved.load()
        assert len(loaded[('login', 'RULE-1')]) == 1
        assert loaded[('login', 'RULE-1')][0]['signer'] == 'jane@acme.com'




# ---------------------------------------------------------------------------
# The signed commit
# ---------------------------------------------------------------------------

@pytest.fixture
def at_strong():
    """The same project at the gate that turns the review list on."""
    made = Project(gate=REVIEW_GATE)
    made.proofs()
    made.record()
    yield made
    made.close()


def signing_project(sign_at='low', signer='jane@acme.com'):
    """A project at the signing gate whose rules are waiting to be signed.

    The record is CI's, because only a CI record counts at this gate, and the
    person's signing key is configured last so the allowed-signers file names
    the person rather than the build identity.
    """
    made = Project(gate=SIGNING_GATE,
                   config={'signers': [signer], 'sign_at': sign_at})
    made.proofs()
    made.record(runner='ci', commit_it=False)
    commit_as_ci(made.root)
    signing_key(made.root, signer)
    return made


class TestTheSignedCommit:

    @pytest.mark.proof("signatures", "PROOF-21", "RULE-17", tier="integration")
    def test_without_signing_the_setup_is_printed_and_nothing_is_written(
            self, at_strong, capsys):
        code = sign_module.main(['login', '--project-root', at_strong.root])
        output = capsys.readouterr().out
        assert code == 1
        assert 'git config gpg.format ssh' in output
        assert 'git config user.signingkey ~/.ssh/id_ed25519.pub' in output
        assert 'git config commit.gpgsign true' in output
        assert at_strong.signatures() == []

    @pytest.mark.proof("signatures", "PROOF-23", "RULE-18", tier="integration")
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
            assert subject == 'sign(login): RULE-2 RULE-1', subject
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-25", "RULE-20", tier="integration")
    def test_what_a_counting_signature_is_at_each_gate(self, at_strong):
        signing_key(at_strong.root)
        sign_module.main(['login', 'RULE-1', '--project-root', at_strong.root])
        found = at_strong.load()[('login', 'RULE-1')][0]

        counted, reason = purlin_signatures.counts(
            at_strong.root, found, ['jane@acme.com'], gate='signed')
        assert counted, reason

        counted, reason = purlin_signatures.counts(
            at_strong.root, found, ['someone@else.com'], gate='signed')
        assert not counted and 'signer is not on the list' in reason

        counted, reason = purlin_signatures.counts(
            at_strong.root, found, ['someone@else.com'], gate='strong')
        assert counted, (
            'under strong a signature from anyone settles what the machine '
            'could not: %s' % reason)

    @pytest.mark.proof("signatures", "PROOF-24", "RULE-19")
    def test_a_batch_across_features_names_each_one(self):
        assert sign_module.commit_message(
            [('login', 'RULE-1'), ('login', 'RULE-2')]) == (
            'sign(login): RULE-1 RULE-2')
        assert sign_module.commit_message(
            [('login', 'RULE-1'), ('billing', 'RULE-3')]) == (
            'sign(batch): login RULE-1, billing RULE-3')

    @pytest.mark.proof("signatures", "PROOF-26", "RULE-21", tier="integration")
    def test_the_signer_list_bounds_who_may_run_it(self, at_strong, capsys):
        at_strong.config(signers=['someone@else.com'])
        code = sign_module.main(['login', '--project-root', at_strong.root])
        output = capsys.readouterr().out
        assert code == 1
        assert 'not on the signer list' in output

    @pytest.mark.proof("signatures", "PROOF-27", "RULE-21", tier="integration")
    def test_the_signing_gate_with_no_list_names_the_command(self, capsys):
        made = Project(gate=SIGNING_GATE)
        try:
            made.proofs()
            made.record()
            code = sign_module.main(['login', '--project-root', made.root])
            output = capsys.readouterr().out
            assert code == 1
            assert 'signer list missing: run purlin:init --gate signed' \
                in output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-15", "RULE-12", tier="integration")
    def test_a_batch_signs_everything_signable(self, capsys):
        made = signing_project(sign_at='medium')
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

    @pytest.mark.proof("signatures", "PROOF-16", "RULE-13", tier="integration")
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

    @pytest.mark.proof("signatures", "PROOF-18", "RULE-14", tier="integration")
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

    @pytest.mark.proof("signatures", "PROOF-19", "RULE-15", tier="integration")
    def test_under_the_review_gate_a_bare_signature_says_so_and_is_written(
            self, at_strong, capsys):
        signing_key(at_strong.root)
        code = sign_module.main(['login', 'RULE-1', '--project-root',
                                 at_strong.root])
        output = capsys.readouterr().out
        assert code == 0, output
        assert 'required only under the gate signed' in output
        assert len(at_strong.signatures()) == 1


# ---------------------------------------------------------------------------
# What a person may sign now
# ---------------------------------------------------------------------------

class TestWhatIsSignable:

    @pytest.mark.proof("signatures", "PROOF-20", "RULE-16", tier="integration")
    def test_it_is_the_unsigned_the_stale_and_the_ones_needing_a_person(self):
        made = signing_project(sign_at='medium')
        try:
            assert sign_module.signable(made.payload()) == [
                ('login', 'RULE-2')], (
                'only the high-risk rule is at or above sign_at')
            sign_module.main(['login', 'RULE-2', '--project-root', made.root])
            assert sign_module.signable(made.payload()) == []
            made.spec(SPEC.replace('return 401 and the body "denied"',
                                   'return 403 and the body "denied"'))
            assert sign_module.signable(made.payload()) == [
                ('login', 'RULE-2')], 'a stale signature is signable again'
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-30", "RULE-16", tier="integration")
    def test_a_rule_needing_a_person_is_signable_under_the_review_gate(self):
        made = Project(gate=REVIEW_GATE, config={'min_strength': 50})
        try:
            made.proofs()
            made.record(runner='ci', commit_it=False)
            commit_as_ci(made.root)
            assert sign_module.signable(made.payload()) == [
                ('login', 'RULE-2')], (
                'the high-risk rule has no brief, so it needs a person')
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

class TestTheWalk:

    @pytest.mark.proof("signatures", "PROOF-31", "RULE-11", tier="integration")
    def test_the_four_answers_each_do_their_own_thing(self, capsys):
        made = signing_project(sign_at='low')
        try:
            answers = {'RULE-2': ('hold', 'no case for an expired token'),
                       'RULE-1': 'sign'}
            given = sign_module.walk(
                made.root, answer=lambda entry, _text: answers[entry['id']])
            capsys.readouterr()
            assert given['signed'] == [('login', 'RULE-1')]
            assert given['held'] == [('login', 'RULE-2')]
            assert len(given['commits']) == 2, given
            names = made.signatures()
            assert any(name.startswith('RULE-1.') and not
                       name.endswith('.hold.json') for name in names), names
            assert any(name.endswith('.hold.json') for name in names), names
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-32", "RULE-11", tier="integration")
    def test_a_skipped_rule_is_written_nothing_and_stays_on_the_list(
            self, capsys):
        made = signing_project(sign_at='low')
        try:
            given = sign_module.walk(made.root,
                                     answer=lambda _entry, _text: 'skip')
            output = capsys.readouterr().out
            assert given['signed'] == [] and given['held'] == []
            assert len(given['skipped']) == 2
            assert made.signatures() == []
            assert 'Run: purlin:sign' in output, output
        finally:
            made.close()

    @pytest.mark.proof("signatures", "PROOF-33", "RULE-11", tier="integration")
    def test_a_case_is_carried_to_the_close_and_written_nowhere(self, capsys):
        made = signing_project(sign_at='low')
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
# The ancestor check
# ---------------------------------------------------------------------------

class TestTheAncestorCheck:

    @pytest.mark.proof("signatures", "PROOF-29", "RULE-23", tier="integration")
    def test_a_signature_on_a_side_branch_is_not_on_the_protected_branch(
            self, at_strong):
        signing_key(at_strong.root)
        git(at_strong.root, 'checkout', '-q', '-b', 'side')
        sign_module.main(['login', 'RULE-1', '--project-root', at_strong.root])
        path = at_strong.load()[('login', 'RULE-1')][0]['path']
        assert not purlin_signatures.is_ancestor(at_strong.root, path, 'main')
        git(at_strong.root, 'checkout', '-q', 'main')
        git(at_strong.root, 'merge', '-q', '--ff-only', 'side')
        assert purlin_signatures.is_ancestor(at_strong.root, path, 'main')


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    @pytest.mark.proof("signatures", "PROOF-28", "RULE-22")
    def test_help_exits_zero_and_a_bad_option_exits_two(self):
        assert sign_module.main(['--help']) == 0
        assert sign_module.main(['login', '--nope']) == 2
        assert sign_module.main(['--nope']) == 2

    @pytest.mark.proof("signatures", "PROOF-22", "RULE-17", tier="integration")
    def test_the_script_runs_as_a_command(self, at_strong):
        result = subprocess.run(
            [sys.executable, SIGN_PY, 'login', '--project-root',
             at_strong.root], capture_output=True, text=True, timeout=120)
        assert result.returncode == 1, result.stdout + result.stderr
        assert 'git config gpg.format ssh' in result.stdout
