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

import approve as sign_module  # noqa: E402
from purlin import gate as purlin_gate  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402
from purlin import signatures as purlin_signatures  # noqa: E402
from purlin import specs as purlin_specs  # noqa: E402

SIGN_PY = os.path.join(ROOT, 'scripts', 'review', 'approve.py')

# The gate the project sits at by default, and the one that asks for a
# signature: the bottom and the top of the three the resolver reads.
FIRST_GATE = purlin_gate.GATES[0]
SIGNING_GATE = purlin_gate.GATES[-1]

# The config key the resolver reads for the signer list.
SIGNER_KEY = ('signers' if 'signers' in purlin_gate.GateConfig.__slots__
              else 'approvers')


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


def sign_one(project, rule='RULE-1', email='jane@acme.com', brief=None,
             record=None, gate='passed', risk=None):
    """Write one signature for a rule and return its project-relative path."""
    entry = project.rule(rule)
    return sign_module.write_approval(
        project.root, 'login', rule, email, brief, record, gate,
        entry['risk'] if risk is None else risk, entry=entry)


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

class TestTheSignedCommit:

    @pytest.mark.proof("signatures", "PROOF-21", "RULE-17", tier="integration")
    def test_without_signing_the_setup_is_printed_and_nothing_is_written(
            self, proved, capsys):
        code = sign_module.main(['login', '--project-root', proved.root])
        output = capsys.readouterr().out
        assert code == 1
        assert 'git config gpg.format ssh' in output
        assert 'git config user.signingkey ~/.ssh/id_ed25519.pub' in output
        assert 'git config commit.gpgsign true' in output
        assert proved.signatures() == []

    @pytest.mark.proof("signatures", "PROOF-23", "RULE-18", tier="integration")
    def test_one_signed_commit_carries_the_batch(self, proved, capsys):
        signing_key(proved.root)
        code = sign_module.main(['login', '--project-root', proved.root])
        capsys.readouterr()
        assert code == 0
        assert len(proved.signatures()) == 2
        log = git(proved.root, 'log', '-1', '--format=%G?%n%s').stdout
        signature, subject = log.strip().splitlines()
        assert signature == 'G', log
        assert subject == 'sign(login): RULE-2 RULE-1', subject

    @pytest.mark.proof("signatures", "PROOF-25", "RULE-20", tier="integration")
    def test_what_a_counting_signature_is_at_each_gate(self, proved):
        signing_key(proved.root)
        sign_module.main(['login', 'RULE-1', '--project-root', proved.root])
        found = proved.load()[('login', 'RULE-1')][0]

        counted, reason = purlin_signatures.counts(
            proved.root, found, ['jane@acme.com'], gate='signed')
        assert counted, reason

        counted, reason = purlin_signatures.counts(
            proved.root, found, ['someone@else.com'], gate='signed')
        assert not counted and 'signer is not on the list' in reason

        counted, reason = purlin_signatures.counts(
            proved.root, found, ['someone@else.com'], gate='strong')
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
    def test_the_signer_list_bounds_who_may_run_it(self, proved, capsys):
        proved.config(**{SIGNER_KEY: ['someone@else.com']})
        code = sign_module.main(['login', '--project-root', proved.root])
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

# ---------------------------------------------------------------------------
# The ancestor check
# ---------------------------------------------------------------------------

class TestTheAncestorCheck:

    @pytest.mark.proof("signatures", "PROOF-29", "RULE-23", tier="integration")
    def test_a_signature_on_a_side_branch_is_not_on_the_protected_branch(
            self, proved):
        signing_key(proved.root)
        git(proved.root, 'checkout', '-q', '-b', 'side')
        sign_module.main(['login', 'RULE-1', '--project-root', proved.root])
        path = proved.load()[('login', 'RULE-1')][0]['path']
        assert not purlin_signatures.is_ancestor(proved.root, path, 'main')
        git(proved.root, 'checkout', '-q', 'main')
        git(proved.root, 'merge', '-q', '--ff-only', 'side')
        assert purlin_signatures.is_ancestor(proved.root, path, 'main')


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    @pytest.mark.proof("signatures", "PROOF-28", "RULE-22")
    def test_help_exits_zero_and_a_bad_option_exits_two(self):
        assert sign_module.main(['--help']) == 0
        assert sign_module.main(['login', '--nope']) == 2
        assert sign_module.main([]) == 2

    @pytest.mark.proof("signatures", "PROOF-22", "RULE-17", tier="integration")
    def test_the_script_runs_as_a_command(self, proved):
        result = subprocess.run(
            [sys.executable, SIGN_PY, 'login', '--project-root',
             proved.root], capture_output=True, text=True, timeout=120)
        assert result.returncode == 1, result.stdout + result.stderr
        assert 'git config gpg.format ssh' in result.stdout
