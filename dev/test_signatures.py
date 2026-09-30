"""Tests for the signature reader and the command that writes one.

Every fixture is written by the test in a throwaway project: a spec, a test
file, the evidence, a signature. Nothing here reads this repository's own
specs, reaches a network, or signs with a key that exists anywhere but the
temporary directory the test made.

What each group holds:

*the hashes*   what a signature is made over, and what does and does not
               move it
*current*      a signature stops being current when any part of it moves,
               and a new system ends nothing
*the file*     the name, the fields, the signer and the key
*the commit*   one signed commit, what makes a signature count, and the lines
               to print when there is no key
*the walk*     the rules that wait for a person, one at a time
*anchors*      an anchor's rule signed once, over the whole project, and a
               pinned anchor's rule signed as not applying
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
for _path in (os.path.join(ROOT, 'scripts', 'mcp'),
              os.path.join(ROOT, 'scripts', 'review'), DEV):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import sign as sign_module  # noqa: E402
from purlin import evidence as purlin_evidence  # noqa: E402
from purlin import fingerprint as purlin_fingerprint  # noqa: E402
from purlin import signatures as purlin_signatures  # noqa: E402
from purlin import summary as purlin_summary  # noqa: E402
from sign_project import (  # noqa: E402
    FIRST_GATE,
    REVIEW_GATE,
    SIGNING_GATE,
    SIGN_PY,
    SPEC,
    TEST_FILE,
    TEST_NAMES,
    Project,
    _Out,
    git,
    sha256,
    write)


# ---------------------------------------------------------------------------
# The throwaway project
# ---------------------------------------------------------------------------


MANUAL_SPEC = SPEC.replace('verify 401 and the body "denied"\n',
                           'verify 401 and the body "denied" @manual\n')
MACHINE = 'jane-laptop'
EMAIL = 'jane@acme.com'


def record(made, source='local', machine=MACHINE, os_name=None,
           strength=90, at='2026-09-13T12:00:00Z'):
    """Write one machine's passing results for both proofs. Its path.

    The section carries the fingerprint taken now, so it is current until the
    spec, the scoped code or the test changes, and it names the machine it
    ran on. The schema is the one the evidence reader reads.
    """
    os_name = os_name or purlin_evidence.host_os()
    rel = '.purlin/evidence/%s/login.json' % source
    path = os.path.join(made.root, *rel.split('/'))
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError):
        data = {'schema': purlin_evidence.SCHEMA, 'feature': 'login',
                'source': source, 'spec': 'specs/auth/login.md',
                'platforms': {}}
    proofs = [{'id': proof_id, 'rule': 'RULE-%s' % proof_id[-1],
               'result': 'pass', 'env': None, 'manual': False,
               'test': 'tests/test_login.py::%s' % TEST_NAMES[proof_id]}
              for proof_id in ('PROOF-1', 'PROOF-2')]
    data['platforms'][os_name] = {
        'commit': made.head(), 'dirty': False, 'at': at, 'runner': 'jane',
        'machine': machine, 'hostname': machine,
        'fingerprint': purlin_fingerprint.fingerprint(made.root, 'login'),
        'rules': {}, 'proofs': proofs}
    data.setdefault('audit', {'mutation': None, 'rules': {}})['mutation'] = {
        'engine': 'mutmut', 'score': strength, 'at': at,
        'commit': made.head()}
    write(path, json.dumps(data, indent=2, sort_keys=True))
    return rel


def commit_all(made, message='purlin: evidence at abc1234'):
    git(made.root, 'add', '-A')
    git(made.root, 'commit', '-q', '-m', message)


def owner_only(private_key):
    """On Windows, leave the private key readable by its owner alone.

    Windows' own `ssh-keygen` refuses to sign with a key file other accounts
    can read, and a file in the temporary folder inherits that folder's
    permissions. `icacls` ships with Windows. Elsewhere `ssh-keygen` already
    wrote the key readable by its owner alone, so nothing is done.
    """
    if os.name != 'nt':
        return
    subprocess.run(['icacls', private_key, '/inheritance:r', '/grant:r',
                    '%s:F' % os.environ['USERNAME']],
                   check=True, capture_output=True)


def key(root, email=EMAIL, name='Jane', file='signing-key'):
    """A throwaway ssh key, named as this checkout's signing key. Its `.pub`."""
    path = os.path.join(root, '.git', file)
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', email,
                    '-f', path], check=True)
    owner_only(path)
    for setting, value in (('user.email', email), ('user.name', name),
                           ('gpg.format', 'ssh'),
                           ('user.signingkey', path + '.pub')):
        git(root, 'config', setting, value)
    return path + '.pub'


def waiting_pairs(payload, feature=None):
    """`(feature, rule)` for each rule the walk would stop at, in its order."""
    return [(item['feature'], item['id'])
            for item in sign_module.waiting(payload, feature)]


def ready(gate=SIGNING_GATE, spec=SPEC, audited=('RULE-1', 'RULE-2'),
          version='2.1.0', signer=True):
    """A project whose rules pass and are audited, all committed, with a key."""
    made = Project(spec=spec, gate=gate)
    record(made)
    for rule in audited:
        made.audit(rule)
    if version:
        write(os.path.join(made.root, 'VERSION'), version + '\n')
    commit_all(made)
    if signer:
        key(made.root)
    return made


def fingerprint_of(public_key_path):
    """What `ssh-keygen -l` prints as the key's fingerprint."""
    shown = subprocess.run(['ssh-keygen', '-l', '-f', public_key_path],
                           capture_output=True, text=True, check=True).stdout
    return shown.split()[1]


def signed_by_last_commit(root):
    """True when HEAD carries an SSH signature."""
    raw = git(root, 'cat-file', 'commit', 'HEAD').stdout
    return '-----BEGIN SSH SIGNATURE-----' in raw


def read_json(root, rel):
    with open(os.path.join(root, *rel.split('/')), encoding='utf-8') as handle:
        return json.load(handle)


@pytest.fixture
def proved():
    """A project whose rules have evidence, so a signature has something to bind."""
    made = Project(spec=SPEC)
    record(made)
    yield made
    made.close()


@pytest.fixture
def at_signed():
    made = ready()
    yield made
    made.close()


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A home directory holding nothing, so no key and no git settings leak in.

    Git and the command read `HOME` first; on Windows `USERPROFILE` is set
    to the same folder, so nothing else there finds another home.
    """
    monkeypatch.setenv('HOME', str(tmp_path))
    if os.name == 'nt':
        monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / '.config'))
    return tmp_path


def sign_one(made, rule='RULE-1', email=EMAIL, note=None, gate='passed',
             entry=None):
    """Write one signature for a rule's own listing. Its project-relative path."""
    return sign_module.write_signature(
        made.root, entry or made.rule(rule), email, None, gate, note=note)


def stops_of(made, answer='skip'):
    """`{rule id: [lines]}`, each stop of the walk as it was shown."""
    stops = {}

    def seen(entry, rendered):
        stops[entry['id']] = rendered.splitlines()
        return answer

    sign_module.walk(made.root, out=_Out(), answer=seen)
    return stops


def audit_shown(stop):
    """The lines of one stop from `What the audit found` on."""
    return stop[stop.index('What the audit found'):]


def current(made, rule='RULE-1'):
    entry = made.rule(rule)
    return [signature for signature in made.load().get(('login', rule)) or ()
            if purlin_signatures.is_current(signature, entry)]


# ---------------------------------------------------------------------------
# The hashes
# ---------------------------------------------------------------------------

class TestTheHashes:

    # purlin: signatures PROOF-1
    def test_the_three_hashes_come_back_with_their_kind(self, proved):
        entry = sign_module.rule_entry(
            sign_module.load_payload(proved.root), 'login', 'RULE-1')
        blob = git(proved.root, 'rev-parse',
                   'HEAD:tests/test_login.py').stdout.strip()
        assert entry['rule_hash'] == sha256(
            'Valid credentials return 200 with a session token')
        assert entry['proof_hash'] == sha256(
            'PROOF-1 POST /login with the password "secret"; verify 200 '
            'and a token')
        assert entry['test_hash'] == sha256(
            'tests/test_login.py test_valid_credentials_return_200 ' + blob)
        assert entry['test_hash_kind'] == 'file'
        assert len({entry['rule_hash'], entry['proof_hash'],
                    entry['test_hash']}) == 3

    # purlin: signatures PROOF-3
    def test_reflowing_a_rule_keeps_the_signed_hash(self, proved):
        before = purlin_signatures.signed_hash(proved.rule('RULE-1'))
        proved.spec(SPEC.replace(
            '- RULE-1: Valid credentials return 200 with a session token',
            '- RULE-1: Valid   credentials  return 200  with a session token'))
        assert purlin_signatures.signed_hash(proved.rule('RULE-1')) == before

    # purlin: signatures PROOF-4
    def test_editing_the_rule_moves_the_signed_hash(self, proved):
        before = purlin_signatures.signed_hash(proved.rule('RULE-1'))
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 201 with a session token'))
        assert purlin_signatures.signed_hash(proved.rule('RULE-1')) != before

    # purlin: signatures PROOF-82
    def test_editing_the_proof_moves_the_signed_hash(self, proved):
        before = purlin_signatures.signed_hash(proved.rule('RULE-1'))
        proved.spec(SPEC.replace('verify 200 and a token',
                                 'verify 200 and a token that expires'))
        assert purlin_signatures.signed_hash(proved.rule('RULE-1')) != before

    # purlin: signatures PROOF-83
    def test_editing_the_test_moves_the_signed_hash(self, proved):
        before = purlin_signatures.signed_hash(proved.rule('RULE-1'))
        proved.edit_test(TEST_FILE.replace('== 200', '== 200  # checked'))
        assert purlin_signatures.signed_hash(proved.rule('RULE-1')) != before

    # purlin: signatures PROOF-5
    def test_a_manual_proof_says_so_instead_of_naming_a_file(self):
        made = Project(spec=MANUAL_SPEC)
        try:
            entry = sign_module.rule_entry(
                sign_module.load_payload(made.root), 'login', 'RULE-2')
            assert entry['test_hash_kind'] == 'manual'
        finally:
            made.close()

    # purlin: signatures PROOF-126
    def test_a_manual_proof_beside_a_tested_one_reads_file(self, proved):
        proved.spec(SPEC + '- PROOF-3 (RULE-1): A person signs in by hand '
                    'and sees the home page @manual\n')
        entry = proved.rule('RULE-1')
        assert [(p['id'], p['manual']) for p in entry['proofs']] == [
            ('PROOF-1', False), ('PROOF-3', True)], entry['proofs']
        assert entry['test_hash_kind'] == 'file'


# ---------------------------------------------------------------------------
# Current
# ---------------------------------------------------------------------------

class TestCurrent:

    # purlin: signatures PROOF-6
    def test_a_fresh_signature_is_current(self, proved):
        sign_one(proved)
        assert len(current(proved)) == 1

    # purlin: signatures PROOF-127
    def test_a_new_audit_finding_ends_it(self, proved):
        sign_one(proved)
        assert len(current(proved)) == 1
        proved.audit('RULE-1', findings=['PROOF-1 reads the status alone.'])
        assert current(proved) == []

    # purlin: signatures PROOF-7
    def test_the_rule_text_changing_ends_it(self, proved):
        sign_one(proved)
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with a signed session token'))
        assert current(proved) == []

    # purlin: signatures PROOF-8
    def test_the_proof_text_changing_ends_it(self, proved):
        sign_one(proved)
        proved.spec(SPEC.replace('verify 200 and a token',
                                 'verify 200, a token and a cookie'))
        assert current(proved) == []

    # purlin: signatures PROOF-9
    def test_the_test_changing_ends_it(self, proved):
        sign_one(proved)
        proved.edit_test(TEST_FILE.replace('== 200', '== 200 or True'))
        assert current(proved) == []

    # purlin: signatures PROOF-84
    def test_the_code_the_feature_lists_changing_ends_it(self, proved):
        sign_one(proved)
        assert len(current(proved)) == 1
        write(os.path.join(proved.root, 'src', 'login.py'),
              'def login(user, password):\n    return 401\n')
        assert current(proved) == []

    # purlin: signatures PROOF-11
    def test_a_signature_that_ended_still_comes_back_from_the_reader(
            self, proved):
        sign_one(proved)
        proved.spec(SPEC.replace('return 200 with a session token',
                                 'return 200 with two session tokens'))
        found = proved.load()[('login', 'RULE-1')]
        assert len(found) == 1, found
        assert found[0]['signer'] == EMAIL
        assert current(proved) == []

    # purlin: signatures PROOF-85
    def test_a_rule_whose_signature_ended_is_to_sign_again(self, at_signed,
                                                           capsys):
        assert sign_module.main(['login', 'RULE-2', '--project-root',
                                 at_signed.root]) == 0
        capsys.readouterr()
        at_signed.spec(SPEC.replace('return 401 and the body "denied"',
                                    'return 403 and the body "denied"'))
        record(at_signed)
        at_signed.audit('RULE-2')
        commit_all(at_signed)
        assert at_signed.rule('RULE-2')['left'] == 'to_sign'


class TestTheMachines:
    """A signature is made over the machine each system's tests ran on."""

    def _signed_over_jane(self, made, windows=False):
        """`login RULE-1` signed over macOS results from jane-laptop."""
        record(made, os_name='macos', machine=MACHINE)
        if windows:
            record(made, source='ci', os_name='windows',
                   machine='remote runner, Windows')
        sign_one(made)
        assert len(current(made)) == 1

    # purlin: signatures PROOF-119
    def test_the_same_machine_again_ends_nothing(self, proved):
        self._signed_over_jane(proved)
        record(proved, os_name='macos', machine=MACHINE,
               at='2026-09-14T12:00:00Z')
        assert len(current(proved)) == 1

    # purlin: signatures PROOF-120
    def test_another_machine_for_a_system_it_names_ends_it(self, proved):
        self._signed_over_jane(proved)
        record(proved, os_name='macos', machine='omar-desktop',
               at='2026-09-14T12:00:00Z')
        assert current(proved) == []

    # purlin: signatures PROOF-121
    def test_a_new_system_ends_nothing(self, proved):
        self._signed_over_jane(proved)
        record(proved, source='ci', os_name='windows',
               machine='remote runner, Windows')
        assert proved.rule('RULE-1')['machines'] == {
            'macos': MACHINE, 'windows': 'remote runner, Windows'}
        assert len(current(proved)) == 1

    # purlin: signatures PROOF-122
    def test_a_system_it_names_that_is_gone_ends_it(self, proved):
        self._signed_over_jane(proved, windows=True)
        os.remove(os.path.join(proved.root, '.purlin', 'evidence', 'ci',
                               'login.json'))
        assert proved.rule('RULE-1')['machines'] == {'macos': MACHINE}
        assert current(proved) == []


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

# The fields signature format 13 names, required and optional.
FIELDS = {'schema', 'feature', 'rule', 'applies_to', 'signed_hash',
          'rule_hash', 'proof_hash', 'test_hash', 'code_hash', 'audit_hash',
          'machines', 'signer', 'key_fingerprint', 'timestamp',
          'signer_name', 'test_hash_kind', 'note', 'does_not_apply', 'gate',
          'evidence'}


class TestTheFile:

    # purlin: signatures PROOF-12
    def test_the_name_carries_the_rule_the_hash_and_the_slug(self, proved):
        signed = purlin_signatures.signed_hash(proved.rule('RULE-1'))
        sign_one(proved, email='Rich.LaBarca+purlin@example.com')
        assert proved.signatures() == [
            'RULE-1.%s.rich-labarca-purlin.json' % signed[:8]]

    # purlin: signatures PROOF-13
    def test_the_fields_are_the_ones_the_format_names(self, proved):
        rel = sign_one(proved, gate='strong')
        data = read_json(proved.root, rel)
        assert data['schema'] == 'purlin-signature/2'
        assert set(data) == FIELDS, sorted(set(data) ^ FIELDS)
        rule = proved.rule('RULE-1')
        lines = '\n'.join([rule['applies_to'], rule['rule_hash'],
                           rule['proof_hash'], rule['test_hash'],
                           rule['code_hash'], rule['audit_hash'],
                           ','.join('%s=%s' % pair for pair in sorted(
                               rule['machines'].items()))])
        assert data['signed_hash'] == sha256(lines)
        assert data['note'] is None
        assert data['timestamp'].endswith('Z')

    def _evidence_named(self, sources, capsys):
        """`login RULE-1` signed with evidence from `sources`. Its `evidence`."""
        made = Project(spec=SPEC)
        try:
            for source in sources:
                record(made, source=source)
            key(made.root)
            assert sign_module.main(['login', 'RULE-1', '--project-root',
                                     made.root]) == 0
            capsys.readouterr()
            path, = git(made.root, 'show', '--name-only', '--format=',
                        'HEAD').stdout.split()
            return read_json(made.root, path)['evidence']
        finally:
            made.close()

    # purlin: signatures PROOF-63
    def test_the_local_file_is_named(self, capsys):
        assert self._evidence_named(['local'], capsys) == \
            '.purlin/evidence/local/login.json'

    # purlin: signatures PROOF-135
    def test_the_local_file_comes_before_the_ci_one(self, capsys):
        assert self._evidence_named(['local', 'ci'], capsys) == \
            '.purlin/evidence/local/login.json'

    # purlin: signatures PROOF-136
    def test_the_ci_file_is_named_when_it_is_the_only_one(self, capsys):
        assert self._evidence_named(['ci'], capsys) == \
            '.purlin/evidence/ci/login.json'

    # purlin: signatures PROOF-137
    def test_no_evidence_file_names_none(self, capsys):
        assert self._evidence_named([], capsys) is None

    # purlin: signatures PROOF-14
    def test_the_reader_finds_it(self, proved):
        sign_one(proved)
        loaded = proved.load()
        assert len(loaded[('login', 'RULE-1')]) == 1
        assert loaded[('login', 'RULE-1')][0]['signer'] == EMAIL
        path = loaded[('login', 'RULE-1')][0]['path']
        assert path.startswith('specs/auth/login.signatures/RULE-1.'), path

    def _copied_elsewhere(self, made):
        """Sign `login RULE-1` and copy its file to three other folders."""
        path = made.root + '/' + sign_one(made)
        for elsewhere in ('specs/login.signatures', 'signatures',
                          'specs/auth/signatures'):
            os.makedirs(os.path.join(made.root, elsewhere))
            shutil.copy(path, os.path.join(made.root, elsewhere,
                                           os.path.basename(path)))
        return path

    # purlin: signatures PROOF-128
    def test_a_copy_anywhere_else_is_not_read(self, proved):
        path = self._copied_elsewhere(proved)
        assert [s['path'] for s in proved.load()[('login', 'RULE-1')]] == [
            os.path.relpath(path, proved.root)]
        assert os.path.relpath(path, proved.root).startswith(
            'specs/auth/login.signatures/')

    # purlin: signatures PROOF-129
    def test_the_copies_alone_are_no_signature(self, proved):
        os.remove(self._copied_elsewhere(proved))
        assert ('login', 'RULE-1') not in proved.load()

    # purlin: signatures PROOF-75
    # purlin: signatures PROOF-157
    def test_it_records_the_signer_as_git_holds_them_and_the_key(
            self, capsys):
        made = ready(signer=False)
        try:
            public = key(made.root, email='Jane.Doe@Acme.com', name='Jane Doe')
            assert sign_module.main(['login', 'RULE-2', '--project-root',
                                     made.root]) == 0
            capsys.readouterr()
            data = read_json(made.root,
                             made.load()[('login', 'RULE-2')][0]['path'])
            assert (data['signer'], data['signer_name'],
                    data['key_fingerprint']) == (
                'Jane.Doe@Acme.com', 'Jane Doe', fingerprint_of(public))
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The key a signer signs with
# ---------------------------------------------------------------------------

class TestTheKey:

    # purlin: signatures PROOF-115
    def test_a_public_key_path_gives_its_fingerprint(self, proved):
        public = key(proved.root)
        assert purlin_signatures.key_fingerprint(proved.root) == \
            fingerprint_of(public)

    # purlin: signatures PROOF-116
    # purlin: signatures PROOF-158
    def test_a_private_key_path_reads_the_public_key_beside_it(self, proved):
        public = key(proved.root)
        private = public[:-len('.pub')]
        if os.name == 'nt':
            # The path as a person on Windows writes it: every `/` a `\`.
            private = private.replace('/', '\\')
            assert '\\' in private, private
        git(proved.root, 'config', 'user.signingkey', private)
        assert purlin_signatures.key_fingerprint(proved.root) == \
            fingerprint_of(public)

    # purlin: signatures PROOF-117
    def test_a_key_literal_gives_its_fingerprint(self, proved):
        public = key(proved.root)
        with open(public, encoding='utf-8') as handle:
            literal = handle.read().strip()
        git(proved.root, 'config', 'user.signingkey', 'key::' + literal)
        assert purlin_signatures.key_fingerprint(proved.root) == \
            fingerprint_of(public)

    # purlin: signatures PROOF-118
    def test_a_key_that_is_not_ssh_is_no_key(self, proved, home, capsys):
        git(proved.root, 'config', 'gpg.format', 'ssh')
        git(proved.root, 'config', 'user.signingkey', '3AA5C34371567BD2')
        code = sign_module.main(['login', 'RULE-1', '--project-root',
                                 proved.root])
        assert code == 1
        assert capsys.readouterr().out.splitlines()[0] == (
            'No key to sign with. These commands set one up:')


# ---------------------------------------------------------------------------
# The signed commit
# ---------------------------------------------------------------------------

NO_KEY_LINES = ['No key to sign with. These commands set one up:',
                '  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""',
                '  git config gpg.format ssh',
                '  git config user.signingkey ~/.ssh/id_ed25519.pub']


def all_across_two_features(made, capsys):
    """`--all` over both `login` rules and `billing`'s hand check.

    Returns the commit the run began on; the output is left on `made.output`.
    """
    add_billing(made)
    before = made.head()
    assert sign_module.main(['--all', '--project-root', made.root]) == 0
    made.output = capsys.readouterr().out
    return before


def add_billing(made):
    """A second feature, `billing`, whose one rule is a hand check, committed."""
    made.spec('# Feature: billing\n\n'
              '> Description: Invoices.\n'
              '> Scope: src/login.py\n\n'
              '## Rules\n\n'
              '- RULE-1: An invoice shows its total with tax\n\n'
              '## Proof\n\n'
              '- PROOF-1 (RULE-1): An invoice of two lines of 50.00 at 10 '
              'percent tax shows 110.00 @manual\n', name='billing',
              category='pay')
    commit_all(made, 'spec(billing): invoices')


class TestTheSignedCommit:

    # purlin: signatures PROOF-21
    def test_without_a_key_the_commands_are_printed_and_nothing_is_written(
            self, proved, home, capsys):
        code = sign_module.main(['login', '--project-root', proved.root])
        assert code == 1
        assert capsys.readouterr().out.splitlines() == NO_KEY_LINES
        assert proved.signatures() == []

    # purlin: signatures PROOF-95
    # purlin: signatures PROOF-153
    def test_an_existing_key_file_is_not_made_again(self, proved, home,
                                                     capsys):
        write(str(home / '.ssh' / 'id_ed25519'), 'a private key\n')
        code = sign_module.main(['login', '--project-root', proved.root])
        assert code == 1
        assert capsys.readouterr().out.splitlines() == [
            NO_KEY_LINES[0]] + NO_KEY_LINES[2:]

    # purlin: signatures PROOF-22
    def test_the_script_runs_as_a_command(self, proved, home):
        result = subprocess.run(
            [sys.executable, SIGN_PY, 'login', '--project-root', proved.root],
            capture_output=True, text=True, timeout=120)
        assert result.returncode == 1, result.stdout + result.stderr
        assert result.stdout.splitlines() == NO_KEY_LINES, result.stdout
        assert proved.signatures() == []

    # purlin: signatures PROOF-23
    # purlin: signatures PROOF-154
    def test_one_signed_commit_carries_the_feature(self, at_signed, capsys):
        before = at_signed.head()
        code = sign_module.main(['login', '--project-root', at_signed.root])
        capsys.readouterr()
        assert code == 0
        assert len(at_signed.signatures()) == 2
        assert git(at_signed.root, 'rev-list', '--count',
                   before + '..HEAD').stdout.strip() == '1'
        assert git(at_signed.root, 'log', '-1', '--format=%s').stdout \
            .strip() == 'sign(login): RULE-1 RULE-2'
        assert signed_by_last_commit(at_signed.root)
        carried = git(at_signed.root, 'show', '--name-only', '--format=',
                      'HEAD').stdout.split()
        assert sorted(carried) == ['specs/auth/login.signatures/' + name
                                   for name in at_signed.signatures()]

    # purlin: signatures PROOF-24
    def test_a_batch_across_features_names_each_one(self, at_signed, capsys):
        all_across_two_features(at_signed, capsys)
        assert git(at_signed.root, 'log', '-1', '--format=%s').stdout \
            .strip() == 'sign(batch): billing RULE-1, login RULE-1 RULE-2'

    # purlin: signatures PROOF-112
    def test_it_closes_by_naming_the_signer_and_the_key(self, at_signed,
                                                        capsys):
        code = sign_module.main(['login', 'RULE-2', '--project-root',
                                 at_signed.root])
        assert code == 0
        last4 = purlin_signatures.key_fingerprint(at_signed.root)[-4:]
        assert ('Signed 1 rule as jane@acme.com with the key ending ...%s.'
                % last4) in capsys.readouterr().out.splitlines()

    # purlin: signatures PROOF-27
    def test_anyone_with_a_key_signs(self, capsys):
        made = ready(signer=False)
        try:
            key(made.root, email='omar@example.org', name='Omar')
            code = sign_module.main(['--all', '--project-root', made.root])
            assert code == 0, capsys.readouterr().out
            assert sorted(name.split('.')[0] + '.' + name.split('.')[2]
                          for name in made.signatures()) == [
                'RULE-1.omar', 'RULE-2.omar']
        finally:
            made.close()


class TestWhatCounts:

    def _committed(self, made, rule, *commit_args, email=EMAIL):
        rel = sign_one(made, rule, email=email)
        git(made.root, 'add', '-A')
        git(made.root, *(list(commit_args[:-1]) + [
            'commit', '-q', '-m', commit_args[-1]]))
        found = next(item for item in made.load()[('login', rule)]
                     if item['path'] == rel)
        return purlin_signatures.counts(made.root, found)

    # purlin: signatures PROOF-25
    # purlin: signatures PROOF-155
    def test_a_commit_signed_with_the_signers_key_counts(self, proved):
        key(proved.root)
        assert self._committed(proved, 'RULE-1', '-c', 'commit.gpgsign=true',
                               'sign(login): RULE-1') == (True, '')

    # purlin: signatures PROOF-96
    def test_an_unsigned_commit_does_not_count(self, proved):
        key(proved.root)
        assert self._committed(proved, 'RULE-1', '-c', 'commit.gpgsign=false',
                               'sign(login): RULE-1') == (
            False, 'the commit that added it is not signed')

    # purlin: signatures PROOF-97
    def test_a_key_nobody_registered_counts(self, proved):
        key(proved.root)
        stranger = os.path.join(proved.root, '.git', 'stranger-key')
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C',
                        'mallory@else.org', '-f', stranger], check=True)
        owner_only(stranger)
        assert self._committed(
            proved, 'RULE-1', '-c', 'user.signingkey=' + stranger + '.pub',
            '-c', 'commit.gpgsign=true', 'sign(login): RULE-1',
            email='mallory@else.org') == (True, '')

    # purlin: signatures PROOF-98
    def test_a_signed_commit_by_another_author_counts(self, proved):
        key(proved.root)
        rel = sign_one(proved, 'RULE-1')
        git(proved.root, 'add', '-A')
        git(proved.root, 'commit', '-q', '-S', '--author',
            'Bob <bob@else.org>', '-m', 'sign(login): RULE-1')
        assert git(proved.root, 'log', '-1', '--format=%ae').stdout.strip() \
            == 'bob@else.org'
        found = proved.load()[('login', 'RULE-1')][0]
        assert found['path'] == rel
        assert purlin_signatures.counts(proved.root, found) == (True, '')


class TestTheNote:

    # purlin: signatures PROOF-16
    def test_a_note_records_what_the_signer_checked(self, capsys):
        made = ready(spec=MANUAL_SPEC)
        try:
            assert made.rule('RULE-2')['left'] == 'to_test_by_hand'
            code = sign_module.main(
                ['login', 'RULE-2', '--note', 'I ran the lockout by hand.',
                 '--project-root', made.root])
            capsys.readouterr()
            assert code == 0
            path = made.load()[('login', 'RULE-2')][0]['path']
            assert read_json(made.root, path)['note'] == \
                'I ran the lockout by hand.'
        finally:
            made.close()

    # purlin: signatures PROOF-145
    def test_one_note_goes_on_each_rule_named(self, at_signed, capsys):
        code = sign_module.main(
            ['login', 'RULE-1', 'RULE-2', '--note', 'I read both by hand.',
             '--project-root', at_signed.root])
        capsys.readouterr()
        assert code == 0
        loaded = at_signed.load()
        notes = [read_json(at_signed.root, loaded[('login', rule)][0]['path'])
                 ['note'] for rule in ('RULE-1', 'RULE-2')]
        assert notes == ['I read both by hand.'] * 2, notes

    def _refused(self, made, capsys, argv):
        before = made.head()
        code = sign_module.main(['--project-root', made.root] + argv)
        error = capsys.readouterr().err
        assert made.signatures() == [] and made.head() == before
        return code, error.splitlines()

    # purlin: signatures PROOF-17
    def test_a_note_with_no_line_is_refused(self, at_signed, capsys):
        assert self._refused(at_signed, capsys, ['login', 'RULE-1', '--note']) \
            == (2, [sign_module.USAGE,
                    'sign.py: --note needs the line you want on the '
                    'signature.'])

    # purlin: signatures PROOF-93
    def test_a_note_on_a_feature_with_no_rule_is_refused(self, at_signed,
                                                         capsys):
        assert self._refused(at_signed, capsys,
                             ['login', '--note', 'a line']) == (
            2, [sign_module.USAGE,
                'sign.py: --note names a feature and the rules it carries.'])

    # purlin: signatures PROOF-94
    def test_a_note_on_all_is_refused(self, at_signed, capsys):
        assert self._refused(at_signed, capsys, ['--all', '--note', 'a line']) \
            == (2, [sign_module.USAGE,
                    'sign.py: --note names a feature and the rules it '
                    'carries.'])


# ---------------------------------------------------------------------------
# What is signed without a stop
# ---------------------------------------------------------------------------

class TestWhatIsSigned:

    # purlin: signatures PROOF-15
    def test_all_signs_every_waiting_rule_in_one_commit(self, at_signed,
                                                        capsys):
        before = at_signed.head()
        code = sign_module.main(['--all', '--project-root', at_signed.root])
        output = capsys.readouterr().out
        assert code == 0, output
        assert output.startswith('Signed 2 rules as jane@acme.com with the '
                                 'key ending ...'), output
        assert [name.split('.')[0] for name in at_signed.signatures()] == [
            'RULE-1', 'RULE-2']
        assert git(at_signed.root, 'rev-list', '--count',
                   before + '..HEAD').stdout.strip() == '1'
        assert signed_by_last_commit(at_signed.root)

    # purlin: signatures PROOF-90
    def test_all_across_two_features_is_one_commit(self, at_signed, capsys):
        before = all_across_two_features(at_signed, capsys)
        assert git(at_signed.root, 'rev-list', '--count',
                   before + '..HEAD').stdout.strip() == '1'
        carried = sorted(git(at_signed.root, 'show', '--name-only',
                             '--format=', 'HEAD').stdout.split())
        assert [path.rsplit('/', 1)[0] for path in carried] == [
            'specs/auth/login.signatures'] * 2 + [
            'specs/pay/billing.signatures'], carried

    # purlin: signatures PROOF-70
    def test_at_strong_all_signs_the_hand_check(self, capsys):
        made = ready(gate=REVIEW_GATE, spec=MANUAL_SPEC)
        try:
            assert waiting_pairs(made.payload()) == [('login', 'RULE-2')]
            assert sign_module.main(['--all', '--project-root',
                                     made.root]) == 0
            capsys.readouterr()
            assert [name.split('.')[0] for name in made.signatures()] == [
                'RULE-2']
        finally:
            made.close()

    # purlin: signatures PROOF-91
    def test_a_bare_feature_signs_its_waiting_rules(self, capsys):
        made = ready(gate=REVIEW_GATE, spec=MANUAL_SPEC)
        try:
            assert sign_module.main(['login', '--project-root', made.root]) \
                == 0
            capsys.readouterr()
            assert [name.split('.')[0] for name in made.signatures()] == [
                'RULE-2']
        finally:
            made.close()

    # purlin: signatures PROOF-92
    def test_at_passed_all_signs_the_hand_check(self, capsys):
        made = ready(gate=FIRST_GATE, spec=MANUAL_SPEC, audited=())
        try:
            assert sign_module.main(['--all', '--project-root',
                                     made.root]) == 0
            capsys.readouterr()
            assert [name.split('.')[0] for name in made.signatures()] == [
                'RULE-2']
        finally:
            made.close()

    # purlin: signatures PROOF-123
    def test_a_named_rule_is_signed_at_any_gate(self, capsys):
        made = ready(gate=FIRST_GATE, audited=())
        try:
            assert sign_module.main(['login', 'RULE-1', '--project-root',
                                     made.root]) == 0
            capsys.readouterr()
            assert [name.split('.')[0] for name in made.signatures()] == [
                'RULE-1']
        finally:
            made.close()

    # purlin: signatures PROOF-124
    def test_all_with_nothing_waiting_says_so_and_ends(self, capsys):
        made = ready(gate=REVIEW_GATE)
        try:
            code = sign_module.main(['--all', '--project-root', made.root])
            assert capsys.readouterr().out.splitlines() == [
                'Nothing is waiting for someone to test by hand or to sign.',
                '2 rules. 2 pass their tests. 2 are strong.',
                'Nothing left to do.']
            assert (code, made.signatures()) == (0, [])
        finally:
            made.close()

    # purlin: signatures PROOF-143
    def test_a_bare_feature_with_nothing_waiting_says_so_and_ends(
            self, capsys):
        made = ready(gate=REVIEW_GATE)
        try:
            code = sign_module.main(['login', '--project-root', made.root])
            assert capsys.readouterr().out.splitlines() == [
                'Nothing is waiting for someone to test by hand or to sign.',
                '2 rules. 2 pass their tests. 2 are strong.',
                'Nothing left to do.']
            assert (code, made.signatures()) == (0, [])
        finally:
            made.close()

    # purlin: signatures PROOF-125
    def test_a_rule_no_spec_has_is_named_and_nothing_is_signed(self, capsys):
        made = ready(gate=REVIEW_GATE)
        try:
            code = sign_module.main(['login', 'RULE-9', '--project-root',
                                     made.root])
            assert capsys.readouterr().out.splitlines() == [
                'login RULE-9 is not a rule any spec has. Run purlin:status login '
                'to see its rules.',
                '2 rules. 2 pass their tests. 2 are strong.',
                'Nothing left to do.']
            assert (code, made.signatures()) == (1, [])
        finally:
            made.close()

    # purlin: signatures PROOF-144
    def test_the_rules_beside_one_no_spec_has_are_signed(self, capsys):
        made = ready(gate=REVIEW_GATE)
        try:
            before = made.head()
            code = sign_module.main(['login', 'RULE-1', 'RULE-9',
                                     '--project-root', made.root])
            lines = capsys.readouterr().out.splitlines()
            ending = purlin_summary.ending(made.payload())
            assert lines[-3:] == [
                'login RULE-9 is not a rule any spec has. Run purlin:status '
                'login to see its rules.'] + ending.splitlines(), lines
            assert [name.split('.')[0] for name in made.signatures()] == [
                'RULE-1']
            assert git(made.root, 'rev-list', '--count',
                       before + '..HEAD').stdout.strip() == '1'
            assert git(made.root, 'log', '-1', '--format=%s').stdout.strip() \
                == 'sign(login): RULE-1'
            assert code == 1
        finally:
            made.close()

    # purlin: signatures PROOF-20
    def test_all_signs_in_the_order_the_walk_shows(self, at_signed, capsys):
        add_billing(at_signed)
        shown = []
        sign_module.walk(at_signed.root, answer=lambda entry, _text: (
            shown.append((entry['feature'], entry['id'])) or 'skip'))
        capsys.readouterr()
        assert shown == [('billing', 'RULE-1'), ('login', 'RULE-1'),
                         ('login', 'RULE-2')], shown

    # purlin: signatures PROOF-130
    def test_all_signs_in_the_same_order(self, at_signed, capsys):
        all_across_two_features(at_signed, capsys)
        lines = at_signed.output.splitlines()
        assert lines[0].startswith('Signed 3 rules as '), lines
        assert lines[1:4] == ['  billing RULE-1', '  login RULE-1',
                              '  login RULE-2'], lines

    # purlin: signatures PROOF-30
    def test_a_bare_feature_signs_a_hand_check_and_a_rule_to_sign(
            self, capsys):
        made = ready(spec=MANUAL_SPEC, audited=('RULE-1',))
        try:
            assert [made.rule(rule)['left'] for rule in ('RULE-1', 'RULE-2')] \
                == ['to_sign', 'to_test_by_hand']
            before = made.head()
            assert sign_module.main(['login', '--project-root', made.root]) \
                == 0
            capsys.readouterr()
            assert [name.split('.')[0] for name in made.signatures()] == [
                'RULE-1', 'RULE-2']
            assert git(made.root, 'rev-list', '--count',
                       before + '..HEAD').stdout.strip() == '1'
            assert git(made.root, 'log', '-1', '--format=%s').stdout.strip() \
                == 'sign(login): RULE-1 RULE-2'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

class TestTheWalk:

    # purlin: signatures PROOF-31
    def test_the_walk_opens_on_what_waits_and_shows_each_rule(self, capsys):
        made = ready(spec=MANUAL_SPEC, audited=('RULE-1',))
        try:
            seen = []
            sign_module.walk(made.root, answer=lambda entry, rendered: (
                seen.append(rendered) or 'skip'))
            output = capsys.readouterr().out
            assert output.splitlines()[:2] == [
                '1 rule to test by hand: purlin:sign',
                '1 rule to sign: purlin:sign'], output
            stop = seen[-1].splitlines()
            assert stop[:3] == ['login RULE-2   to test by hand', 'Rule',
                                '  Invalid credentials return 401 and the '
                                'body "denied"'], stop
            assert '  PROOF-2 (@manual): POST /login with a bad password; ' \
                'verify 401 and the body "denied"' in stop
            assert 'What the audit found' in stop
        finally:
            made.close()

    # purlin: signatures PROOF-86
    def test_a_hand_check_signed_carries_what_was_seen(self, capsys):
        made = ready(spec=MANUAL_SPEC, audited=('RULE-1',))
        try:
            given = sign_module.walk(made.root, answer=lambda entry, _text: (
                ('sign', 'The lockout page read 401.')
                if entry['id'] == 'RULE-2' else 'skip'))
            output = capsys.readouterr().out
            path = made.load()[('login', 'RULE-2')][0]['path']
            assert read_json(made.root, path)['note'] == \
                'The lockout page read 401.'
            assert given['signed'] == [('login', 'RULE-2')]
            assert ('Walked 2 rules: 1 signed, 0 cases added, 1 skipped.'
                    in output.splitlines()), output
        finally:
            made.close()

    # purlin: signatures PROOF-88
    def test_a_hand_check_signed_with_no_line_is_signed(self, capsys):
        made = ready(spec=MANUAL_SPEC, audited=('RULE-1',))
        try:
            given = sign_module.walk(made.root, answer=lambda entry, _text: (
                ('sign', '') if entry['id'] == 'RULE-2' else 'skip'))
            capsys.readouterr()
            assert len(given['commits']) == 1, given
            path = made.load()[('login', 'RULE-2')][0]['path']
            assert read_json(made.root, path)['note'] is None
        finally:
            made.close()

    # purlin: signatures PROOF-87
    def test_the_walk_writes_nothing_until_it_closes(self, at_signed, capsys):
        before = at_signed.head()
        at_each_stop = []

        def answer(_entry, _rendered):
            at_each_stop.append((at_signed.signatures(), at_signed.head()))
            return 'sign'

        given = sign_module.walk(at_signed.root, answer=answer)
        capsys.readouterr()
        assert at_each_stop == [([], before), ([], before)], at_each_stop
        assert len(at_signed.signatures()) == 2
        assert len(given['commits']) == 1
        assert git(at_signed.root, 'rev-parse',
                   given['commits'][0] + '^').stdout.strip() == before

    # purlin: signatures PROOF-32
    def test_a_skipped_rule_waits_again(self, at_signed, capsys):
        given = sign_module.walk(at_signed.root,
                                 answer=lambda _entry, _text: 'skip')
        output = capsys.readouterr().out.splitlines()
        assert given['signed'] == [] and at_signed.signatures() == []
        assert 'Walked 2 rules: 0 signed, 0 cases added, 2 skipped.' in output
        assert output[-1] == '  2 rules to sign: purlin:sign', output

    # purlin: signatures PROOF-33
    def test_a_case_is_carried_to_the_close_and_written_nowhere(
            self, at_signed, capsys):
        given = sign_module.walk(
            at_signed.root, answer=lambda entry, _text: (
                ('case', 'it should also reject an expired token')
                if entry['id'] == 'RULE-2' else 'skip'))
        output = capsys.readouterr().out.splitlines()
        assert len(given['cases']) == 1 and at_signed.signatures() == []
        assert 'Walked 2 rules: 0 signed, 1 case added, 1 skipped.' in output
        assert ('  login RULE-2   add this proof line: it should also reject '
                'an expired token') in output, output

    # purlin: signatures PROOF-175
    def test_a_case_with_no_line_says_the_reviewer_named_none(
            self, at_signed, capsys):
        given = sign_module.walk(
            at_signed.root, answer=lambda entry, _text: (
                ('case', '') if entry['id'] == 'RULE-2' else 'skip'))
        output = capsys.readouterr().out.splitlines()
        assert len(given['cases']) == 1 and at_signed.signatures() == []
        assert ('  login RULE-2   add this proof line: the reviewer named no '
                'case') in output, output

    # purlin: signatures PROOF-176
    def test_a_walk_that_signed_names_its_commit(self, at_signed, capsys):
        given = sign_module.walk(at_signed.root,
                                 answer=lambda _entry, _text: 'sign')
        output = capsys.readouterr().out.splitlines()
        sha, = given['commits']
        signed_at = next(index for index, line in enumerate(output)
                         if line.startswith('Signed 2 rules as '))
        assert output[signed_at + 1] == 'Commits: %s' % sha[:7], output
        assert git(at_signed.root, 'log', '-1', '--format=%s', sha).stdout \
            .strip() == 'sign(login): RULE-1 RULE-2'

    # purlin: signatures PROOF-177
    def test_a_skipped_rule_is_still_to_sign_and_nothing_records_it(
            self, at_signed, capsys):
        sign_module.walk(at_signed.root, answer=lambda _entry, _text: 'skip')
        capsys.readouterr()
        assert [at_signed.rule(rule)['left'] for rule in ('RULE-1', 'RULE-2')] \
            == ['to_sign', 'to_sign']
        assert git(at_signed.root, 'status', '--porcelain',
                   '--untracked-files=all', '--ignored').stdout == ''

    # purlin: signatures PROOF-165
    def test_rule_2_comes_before_rule_10(self, capsys):
        made = ready(spec=SPEC.replace('- RULE-1:', '- RULE-10:')
                     .replace('(RULE-1)', '(RULE-10)'),
                     audited=('RULE-2', 'RULE-10'))
        try:
            shown = []
            sign_module.walk(made.root, answer=lambda entry, _text: (
                shown.append(entry['id']) or 'skip'))
            capsys.readouterr()
            assert shown == ['RULE-2', 'RULE-10'], shown
        finally:
            made.close()

    # purlin: signatures PROOF-166
    def test_a_proof_for_one_system_shows_its_tag(self, capsys):
        made = ready(spec=SPEC.replace('verify 200 and a token\n',
                                       'verify 200 and a token @env(windows)\n'),
                     signer=False)
        try:
            record(made, source='ci', os_name='windows',
                   machine='remote runner, Windows')
            made.audit('RULE-1')
            commit_all(made)
            key(made.root)
            stops = stops_of(made, 'skip')
            assert ('  PROOF-1 (@env(windows)): POST /login with the password '
                    '"secret"; verify 200 and a token') in stops['RULE-1'], \
                stops
        finally:
            made.close()

    # purlin: signatures PROOF-89
    def test_a_walk_with_nothing_waiting_says_so(self, capsys):
        made = ready(gate=REVIEW_GATE)
        try:
            out = _Out()
            sign_module.walk(made.root, out=out)
            assert out.text().splitlines()[0] == (
                'Nothing is waiting for someone to test by hand or to sign.')
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What a stop shows, and what the walk asks
# ---------------------------------------------------------------------------

def set_findings(made, rule, findings):
    """Give the audit entry `made` wrote for a rule these findings."""
    rel = made.audit(rule)
    path = os.path.join(made.root, *rel.split('/'))
    data = read_json(made.root, rel)
    data['audit']['rules'][rule]['findings'] = list(findings)
    write(path, json.dumps(data, indent=2, sort_keys=True))


class TestWhatTheAuditFound:

    # purlin: signatures PROOF-167
    def test_no_audit_yet(self):
        made = ready(spec=MANUAL_SPEC, audited=('RULE-1',))
        try:
            assert made.rule('RULE-2')['audit'] is None
            assert audit_shown(stops_of(made)['RULE-2']) == [
                'What the audit found',
                "  No audit has read this rule's text, proof and test yet."]
        finally:
            made.close()

    # purlin: signatures PROOF-168
    def test_strong_with_no_finding(self, at_signed):
        assert audit_shown(stops_of(at_signed)['RULE-1']) == [
            'What the audit found', '  Strong. It found nothing.']

    # purlin: signatures PROOF-169
    def test_strong_with_a_finding(self, at_signed):
        set_findings(at_signed, 'RULE-1', ['PROOF-1 reads the status alone.'])
        assert audit_shown(stops_of(at_signed)['RULE-1']) == [
            'What the audit found', '  Strong.',
            '  PROOF-1 reads the status alone.']

    # purlin: signatures PROOF-170
    def test_weak_with_a_finding(self):
        made = ready(spec=MANUAL_SPEC, audited=('RULE-1',))
        try:
            made.audit('RULE-2', findings=['PROOF-2 reads the status alone.'])
            assert audit_shown(stops_of(made)['RULE-2']) == [
                'What the audit found', '  Weak.',
                '  PROOF-2 reads the status alone.']
        finally:
            made.close()

    # purlin: signatures PROOF-171
    def test_undecided_with_a_finding(self):
        made = ready(spec=MANUAL_SPEC, audited=('RULE-1',))
        try:
            made.audit('RULE-2', findings=['PROOF-2 names no status.'],
                       settled=False)
            assert audit_shown(stops_of(made)['RULE-2']) == [
                'What the audit found',
                '  Undecided. The AI audit could not decide, so the rule '
                'reads weak until its proof or test changes.',
                '  PROOF-2 names no status.']
        finally:
            made.close()


def typed(monkeypatch, answers):
    """Answer the walk's questions with `answers`, in order. The questions asked."""
    asked = []
    left = list(answers)

    def answer(question=''):
        asked.append(question)
        if not left:
            raise EOFError
        return left.pop(0)

    monkeypatch.setattr('builtins.input', answer)
    return asked


class TestWhatTheWalkAsks:

    # purlin: signatures PROOF-172
    def test_each_stop_asks_for_one_of_three(self, at_signed, monkeypatch):
        asked = typed(monkeypatch, ['skip', 'skip'])
        sign_module.walk(at_signed.root, out=_Out())
        assert asked[0] == 'login RULE-1   sign / case / skip: ', asked

    # purlin: signatures PROOF-173
    def test_signing_a_hand_check_asks_what_was_seen(self, monkeypatch):
        made = ready(spec=MANUAL_SPEC, audited=('RULE-1',))
        try:
            asked = typed(monkeypatch, ['skip', 'sign', 'It read 401.'])
            sign_module.walk(made.root, out=_Out())
            assert asked[1:] == ['login RULE-2   sign / case / skip: ',
                                 'What did you see, in one line: '], asked
        finally:
            made.close()

    # purlin: signatures PROOF-174
    def test_a_case_asks_for_the_line(self, at_signed, monkeypatch):
        asked = typed(monkeypatch, ['case', 'reject an empty password', 'skip'])
        sign_module.walk(at_signed.root, out=_Out())
        assert asked[:2] == ['login RULE-1   sign / case / skip: ',
                             '  in one line: '], asked


# ---------------------------------------------------------------------------
# A spec that names no files
# ---------------------------------------------------------------------------

NO_SCOPE = SPEC.replace('> Scope: src/login.py\n', '')


class TestNoFiles:

    # purlin: signatures PROOF-159
    def test_a_named_rule_says_its_signature_does_not_count(self, capsys):
        made = ready(spec=NO_SCOPE)
        try:
            assert sign_module.main(['login', 'RULE-1', '--project-root',
                                     made.root]) == 0
            lines = capsys.readouterr().out.splitlines()
            assert lines[0].startswith('Signed 1 rule as '), lines
            assert lines[1] == ('  login RULE-1   does not count until the '
                                'spec names its files: purlin:spec login'), lines
            assert [name.split('.')[0] for name in made.signatures()] == [
                'RULE-1']
        finally:
            made.close()

    # purlin: signatures PROOF-160
    def test_the_walk_says_so_for_each_such_rule_it_signed(self, capsys):
        made = ready(spec=MANUAL_SPEC.replace('> Scope: src/login.py\n', ''),
                     audited=('RULE-1',))
        try:
            assert made.rule('RULE-2')['left'] == 'to_test_by_hand'
            out = _Out()
            sign_module.walk(made.root, out=out, answer=lambda entry, _text: (
                ('sign', 'It read 401.') if entry['id'] == 'RULE-2'
                else 'skip'))
            lines = out.text().splitlines()
            signed_at = next(index for index, line in enumerate(lines)
                             if line.startswith('Signed 1 rule as '))
            assert lines[signed_at - 1] == (
                '  login RULE-2   does not count until the spec names its '
                'files: purlin:spec login'), lines
        finally:
            made.close()

    # purlin: signatures PROOF-161
    def test_below_signed_the_line_is_the_plain_one(self, capsys):
        made = ready(gate=REVIEW_GATE, spec=NO_SCOPE)
        try:
            assert sign_module.main(['login', 'RULE-1', '--project-root',
                                     made.root]) == 0
            lines = capsys.readouterr().out.splitlines()
            assert lines[0].startswith('Signed 1 rule as '), lines
            assert lines[1] == '  login RULE-1', lines
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The commit not made
# ---------------------------------------------------------------------------

class TestTheCommitNotMade:

    # purlin: signatures PROOF-162
    def test_gits_own_message_is_named(self, at_signed, capsys):
        hook = os.path.join(at_signed.root, '.git', 'hooks', 'pre-commit')
        with open(hook, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write('#!/bin/sh\n'
                         'echo "error: the hook refused the commit." >&2\n'
                         'exit 1\n')
        os.chmod(hook, 0o755)
        before = at_signed.head()
        code = sign_module.main(['--all', '--project-root', at_signed.root])
        assert capsys.readouterr().out.splitlines() == [
            'The signature commit was not made: the hook refused the commit. '
            'Nothing was signed; run purlin:sign again once git can make a '
            'signed commit.']
        assert (code, at_signed.head()) == (1, before)


# ---------------------------------------------------------------------------
# Anchors
# ---------------------------------------------------------------------------

ANCHOR = ('# Anchor: %s\n\n'
          '> Description: What every feature does with a password.\n%s\n'
          '## Rules\n\n'
          '- RULE-1: A password is never written to a log\n\n'
          '## Proof\n\n'
          '- PROOF-1 (RULE-1): A sign-in with the password "secret" leaves '
          'no line holding "secret" in the log @manual\n')

SOURCE = 'https://github.com/acme/policies.git'
PINNED = '> Source: %s\n> Pinned: %s\n' % (SOURCE, 'a' * 40)
NO_CARD_DATA = 'the project stores no card data'


def an_anchor(made, name='secure', pinned=False, manual=True):
    """An anchor of one hand-checked rule, and a tracked `NOTES.txt`, committed.

    With `pinned` the anchor carries `> Source:`, as a copy pulled from
    another repository does. Without `manual` its one proof carries no
    `@manual` and no test backs it, so its signature is not a hand check's.
    """
    text = ANCHOR % (name, PINNED if pinned else '')
    if not manual:
        text = text.replace(' @manual\n', '\n')
    write(os.path.join(made.root, 'specs', '_anchors', name + '.md'), text)
    write(os.path.join(made.root, 'NOTES.txt'), 'Notes.\n')
    # The dashboard's data is ignored, as setup writes `.gitignore`: it is
    # rebuilt on every status and is not part of the project.
    write(os.path.join(made.root, '.gitignore'),
          '.purlin/runtime/\n.purlin/report-data.js\n')
    commit_all(made, 'spec(%s): the anchor' % name)


def with_anchor(made):
    """The anchor `secure` beside `login` and a second feature, `billing`."""
    made.spec('# Feature: billing\n\n'
              '> Description: Invoices.\n'
              '> Scope: src/billing.py\n\n'
              '## Rules\n\n'
              '- RULE-1: An invoice shows its total with tax\n\n'
              '## Proof\n\n'
              '- PROOF-1 (RULE-1): An invoice of two lines of 50.00 at 10 '
              'percent tax shows 110.00 @manual\n', name='billing',
              category='pay')
    write(os.path.join(made.root, 'src', 'billing.py'),
          'def total(lines):\n    return sum(lines) * 1.1\n')
    an_anchor(made)


def anchor_signatures(made, name='secure'):
    """Every signature of the anchor's `RULE-1`, as the reader returns them."""
    return made.load().get((name, 'RULE-1')) or []


def anchor_current(made, name='secure'):
    """The anchor's signatures still made over its rule as it now stands."""
    entry = made.rule('RULE-1', feature=name)
    return [signature for signature in anchor_signatures(made, name)
            if purlin_signatures.is_current(signature, entry)]


def edit_notes(made):
    """An edit to `NOTES.txt`, a tracked file no spec names, committed."""
    write(os.path.join(made.root, 'NOTES.txt'), 'Notes, edited.\n')
    commit_all(made, 'docs: notes')


@pytest.fixture
def beside_features():
    """`login`, whose rules pass and wait for an audit, `billing` and `secure`."""
    made = ready(audited=())
    with_anchor(made)
    yield made
    made.close()


class TestAnchors:

    # purlin: signatures PROOF-131
    def test_all_signs_an_anchor_rule_once(self, beside_features, capsys):
        assert sign_module.main(['--all', '--project-root',
                                 beside_features.root]) == 0
        lines = capsys.readouterr().out.splitlines()
        assert lines[0].startswith('Signed 2 rules as '), lines
        assert lines[1:3] == ['  billing RULE-1', '  secure RULE-1'], lines
        assert not lines[3].startswith('  '), lines

    # purlin: signatures PROOF-113
    def test_an_anchor_rule_is_signed_once(self, beside_features, capsys):
        before = beside_features.head()
        assert sign_module.main(['secure', 'RULE-1', '--project-root',
                                 beside_features.root]) == 0
        capsys.readouterr()
        folder = os.path.join(beside_features.root, 'specs', '_anchors',
                              'secure.signatures')
        applies = [read_json(folder, name)['applies_to']
                   for name in os.listdir(folder)]
        assert applies == ['secure'], applies
        assert git(beside_features.root, 'rev-list', '--count',
                   before + '..HEAD').stdout.strip() == '1'

    # purlin: signatures PROOF-179
    def test_an_edit_anywhere_in_the_project_ends_it(self, beside_features,
                                                     capsys):
        an_anchor(beside_features, manual=False)
        sign_module.main(['secure', 'RULE-1', '--project-root',
                          beside_features.root])
        capsys.readouterr()
        assert len(anchor_current(beside_features)) == 1
        edit_notes(beside_features)
        assert len(anchor_signatures(beside_features)) == 1
        assert anchor_current(beside_features) == []

    # purlin: signatures PROOF-180
    def test_signatures_and_results_leave_it_standing(self, beside_features,
                                                      capsys):
        root = beside_features.root
        sign_module.main(['secure', 'RULE-1', '--project-root', root])
        sign_module.main(['login', 'RULE-1', '--project-root', root])
        capsys.readouterr()
        record(beside_features, at='2026-09-14T12:00:00Z')
        commit_all(beside_features)
        assert len(anchor_current(beside_features)) == 1

    # purlin: signatures PROOF-181
    def test_the_walk_visits_features_before_anchors(self, at_signed):
        an_anchor(at_signed, name='aaa')
        order = []

        def seen(entry, _rendered):
            order.append((entry['feature'], entry['id']))
            return 'skip'

        sign_module.walk(at_signed.root, out=_Out(), answer=seen)
        assert order == [('login', 'RULE-1'), ('login', 'RULE-2'),
                         ('aaa', 'RULE-1')], order


def not_applying(made, rule='RULE-1', reason=NO_CARD_DATA, name='baseline'):
    """`sign.py <name> <rule> --does-not-apply <reason>`. Its exit code."""
    return sign_module.main([name, rule, '--does-not-apply', reason,
                             '--project-root', made.root])


@pytest.fixture
def pinned():
    """At the gate `signed`, `login` beside the pinned anchor `baseline`."""
    made = ready()
    an_anchor(made, name='baseline', pinned=True, manual=False)
    yield made
    made.close()


class TestDoesNotApply:

    # purlin: signatures PROOF-182
    def test_the_signature_carries_the_reason(self, pinned, capsys):
        assert not_applying(pinned) == 0
        capsys.readouterr()
        [signature] = anchor_signatures(pinned, 'baseline')
        assert signature['does_not_apply'] == NO_CARD_DATA

    # purlin: signatures PROOF-183
    def test_it_is_one_signed_commit(self, pinned, capsys):
        before = pinned.head()
        assert not_applying(pinned) == 0
        capsys.readouterr()
        assert git(pinned.root, 'rev-list', '--count',
                   before + '..HEAD').stdout.strip() == '1'
        assert git(pinned.root, 'log', '-1', '--format=%s').stdout.strip() \
            == 'sign(baseline): RULE-1'
        assert signed_by_last_commit(pinned.root)
        carried = git(pinned.root, 'show', '--name-only', '--format=',
                      'HEAD').stdout.split()
        assert [path.rsplit('/', 1)[0] for path in carried] == [
            'specs/_anchors/baseline.signatures'], carried

    # purlin: signatures PROOF-184
    def test_a_local_anchors_rule_is_refused(self, beside_features, capsys):
        before = beside_features.head()
        assert not_applying(beside_features, reason='no card data',
                            name='secure') == 1
        assert capsys.readouterr().out.splitlines() == [
            'secure RULE-1 is not a rule of a pinned anchor, so it cannot be '
            'signed as not applying. A rule of this project that does not '
            'apply is deleted: run purlin:spec secure.']
        assert beside_features.head() == before
        assert anchor_signatures(beside_features) == []

    # purlin: signatures PROOF-185
    def test_a_features_rule_is_refused(self, pinned, capsys):
        before = pinned.head()
        assert not_applying(pinned, reason='no card data', name='login') == 1
        assert capsys.readouterr().out.splitlines() == [
            'login RULE-1 is not a rule of a pinned anchor, so it cannot be '
            'signed as not applying. A rule of this project that does not '
            'apply is deleted: run purlin:spec login.']
        assert (pinned.head(), pinned.signatures()) == (before, [])

    # purlin: signatures PROOF-186
    def test_no_reason_exits_two(self, pinned, capsys):
        before = pinned.head()
        assert sign_module.main(['baseline', 'RULE-1', '--does-not-apply',
                                 '--project-root', pinned.root]) == 2
        assert capsys.readouterr().err.splitlines() == [
            sign_module.USAGE,
            'sign.py: --does-not-apply needs the reason the rule does not '
            'apply to this project.']
        assert pinned.head() == before
        assert anchor_signatures(pinned, 'baseline') == []

    # purlin: signatures PROOF-187
    def test_with_all_it_exits_two(self, pinned, capsys):
        before = pinned.head()
        assert sign_module.main(['--all', '--does-not-apply', 'no card data',
                                 '--project-root', pinned.root]) == 2
        assert capsys.readouterr().err.splitlines() == [
            sign_module.USAGE,
            'sign.py: --does-not-apply names a pinned anchor and the rules it '
            'carries.']
        assert (pinned.head(), pinned.signatures()) == (before, [])

    # purlin: signatures PROOF-188
    def test_the_walk_asks_to_confirm_and_signs_the_reason_again(
            self, pinned, capsys):
        assert not_applying(pinned) == 0
        capsys.readouterr()
        edit_notes(pinned)
        stops = {}

        def seen(entry, rendered):
            stops[entry['feature']] = rendered.splitlines()
            return 'confirm' if entry['feature'] == 'baseline' else 'skip'

        sign_module.walk(pinned.root, out=_Out(), answer=seen)
        assert stops['baseline'][-1] == (
            'baseline RULE-1 was signed as not applying by jane@acme.com: '
            'the project stores no card data. Confirm it still does not '
            'apply?'), stops
        [now] = anchor_current(pinned, 'baseline')
        assert now['does_not_apply'] == NO_CARD_DATA
        assert len(anchor_signatures(pinned, 'baseline')) == 2

    # purlin: signatures PROOF-189
    def test_all_leaves_a_rule_to_confirm(self, pinned, capsys):
        assert not_applying(pinned) == 0
        edit_notes(pinned)
        assert sign_module.main(['--all', '--project-root', pinned.root]) == 0
        capsys.readouterr()
        assert len(anchor_signatures(pinned, 'baseline')) == 1
        assert pinned.rule('RULE-1', feature='baseline')['left'] == \
            'to_confirm'


# ---------------------------------------------------------------------------
# Any branch
# ---------------------------------------------------------------------------

class TestAnyBranch:

    # purlin: signatures PROOF-29
    def test_a_signature_on_a_side_branch_counts_there(self, at_signed,
                                                       capsys):
        git(at_signed.root, 'checkout', '-q', '-b', 'side')
        assert sign_module.main(['login', 'RULE-2', '--project-root',
                                 at_signed.root]) == 0
        capsys.readouterr()
        on_main = git(at_signed.root, 'ls-tree', '-r', '--name-only', 'main',
                      'specs/auth/login.signatures').stdout.strip()
        assert on_main == '', 'main does not carry the signature'
        cell = at_signed.rule('RULE-2')['cells']['signed']
        assert cell['word'] == 'signed', cell
        assert not any('branch' in reason or 'main' in reason
                       for reason in cell.get('reasons') or ()), cell

    # purlin: signatures PROOF-134
    def test_the_branch_that_does_not_carry_it_is_unsigned(self, at_signed,
                                                           capsys):
        git(at_signed.root, 'checkout', '-q', '-b', 'side')
        assert sign_module.main(['login', 'RULE-2', '--project-root',
                                 at_signed.root]) == 0
        capsys.readouterr()
        git(at_signed.root, 'checkout', '-q', 'main')
        assert at_signed.rule('RULE-2')['cells']['signed']['word'] == \
            'unsigned'


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    # purlin: signatures PROOF-28
    def test_help_exits_zero(self, capsys):
        assert sign_module.main(['--help']) == 0
        assert capsys.readouterr().out.splitlines()[0] == (
            'Write the signatures a person attests, and commit them signed.')

    # purlin: signatures PROOF-132
    def test_an_unknown_option_after_a_feature_exits_two(self, capsys):
        assert sign_module.main(['login', '--nope']) == 2
        assert capsys.readouterr().err.splitlines() == [
            sign_module.USAGE, 'sign.py: unknown option --nope']

    # purlin: signatures PROOF-133
    def test_an_unknown_option_alone_exits_two(self, capsys):
        assert sign_module.main(['--nope']) == 2
        assert capsys.readouterr().err.splitlines() == [
            sign_module.USAGE, 'sign.py: unknown option --nope']

    # purlin: signatures PROOF-164
    def test_a_root_that_is_not_a_directory_exits_two(self, capsys):
        assert sign_module.main(['--project-root', 'no/such/folder']) == 2
        assert capsys.readouterr().err.splitlines() == [
            'sign.py: no/such/folder is not a directory.']

    # purlin: signatures PROOF-152
    def test_a_settings_file_that_cannot_be_read_stops_it(self, at_signed,
                                                          capsys):
        path = os.path.join(at_signed.root, '.purlin', 'config.json')
        with open(path, encoding='utf-8') as handle:
            text = handle.read().rstrip()
        assert text.endswith('}'), text
        write(path, text[:-1].rstrip() + ',\n}\n')
        before = at_signed.head()
        code = sign_module.main(['--all', '--project-root', at_signed.root])
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 1, lines
        assert lines[0].startswith('.purlin/config.json cannot be read: '), lines
        assert lines[0].endswith('Fix the file by hand; nothing ran and '
                                 'nothing was saved.'), lines
        assert (code, at_signed.signatures(), at_signed.head()) == (
            1, [], before)


# ---------------------------------------------------------------------------
# A hand check, a verified commit, a broken spec, the tied test
# ---------------------------------------------------------------------------

# `login` with `PROOF-2` written a second time, in the same words.
DOUBLED_SPEC = SPEC + (
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify 401 and the '
    'body "denied"\n')


def signed_word(made, rule):
    """The word and the reasons of a rule's signed cell."""
    cell = made.rule(rule)['cells']['signed']
    return cell['word'], cell.get('reasons')


class TestAHandCheck:

    # purlin: signatures PROOF-190
    def test_an_edit_to_the_code_leaves_it_signed(self, capsys):
        made = ready(spec=MANUAL_SPEC)
        try:
            assert sign_module.main(['login', 'RULE-2', '--project-root',
                                     made.root]) == 0
            capsys.readouterr()
            write(os.path.join(made.root, 'src', 'login.py'),
                  'def login(user, password):\n    return 401\n')
            commit_all(made, 'fix(login): always refuse')
            assert signed_word(made, 'RULE-2')[0] == 'signed'
        finally:
            made.close()

    # purlin: signatures PROOF-191
    def test_an_edit_to_its_proof_ends_it(self, capsys):
        made = ready(spec=MANUAL_SPEC)
        try:
            assert sign_module.main(['login', 'RULE-2', '--project-root',
                                     made.root]) == 0
            capsys.readouterr()
            made.spec(MANUAL_SPEC.replace('a bad password', 'a wrong password'))
            commit_all(made, 'spec(login): reword')
            assert signed_word(made, 'RULE-2')[0] == 'unsigned'
        finally:
            made.close()


def tamper_last_commit(root):
    """Rewrite HEAD with one byte of its signature block changed."""
    raw = subprocess.run(['git', 'cat-file', 'commit', 'HEAD'], cwd=root,
                         capture_output=True, check=True).stdout
    lines = raw.split(b'\n')
    start = next(i for i, line in enumerate(lines)
                 if line.startswith(b'gpgsig '))
    target = start + 2
    line = bytearray(lines[target])
    line[10] = ord('B') if line[10] != ord('B') else ord('C')
    lines[target] = bytes(line)
    made = subprocess.run(['git', 'hash-object', '-t', 'commit', '-w',
                           '--stdin'], cwd=root, input=b'\n'.join(lines),
                          capture_output=True, check=True).stdout
    git(root, 'update-ref', 'refs/heads/main', made.decode().strip())


class TestAVerifiedCommit:

    # purlin: signatures PROOF-192
    def test_a_signature_block_changed_does_not_verify(self, at_signed,
                                                       capsys):
        assert sign_module.main(['login', 'RULE-1', '--project-root',
                                 at_signed.root]) == 0
        capsys.readouterr()
        tamper_last_commit(at_signed.root)
        assert signed_word(at_signed, 'RULE-1') == (
            'unsigned',
            ['the signature on the commit that added it does not verify'])

    # purlin: signatures PROOF-193
    def test_a_key_deleted_since_still_counts(self, at_signed, capsys):
        assert sign_module.main(['login', 'RULE-1', '--project-root',
                                 at_signed.root]) == 0
        capsys.readouterr()
        for name in ('signing-key', 'signing-key.pub'):
            os.remove(os.path.join(at_signed.root, '.git', name))
        git(at_signed.root, 'config', '--unset', 'user.signingkey')
        assert signed_word(at_signed, 'RULE-1')[0] == 'signed'


class TestABrokenSpec:

    REFUSED = ('login is not signed: PROOF-2 is written twice in the spec. '
               'Run purlin:spec login, then purlin:sign again.')

    # purlin: signatures PROOF-194
    def test_naming_a_rule_signs_nothing(self, capsys):
        made = ready(spec=DOUBLED_SPEC)
        try:
            before = made.head()
            code = sign_module.main(['login', 'RULE-1', '--project-root',
                                     made.root])
            lines = capsys.readouterr().out.splitlines()
            assert (code, lines) == (1, [self.REFUSED])
            assert (made.signatures(), made.head()) == ([], before)
        finally:
            made.close()

    # purlin: signatures PROOF-195
    def test_naming_the_feature_signs_nothing(self, capsys):
        made = ready(spec=DOUBLED_SPEC)
        try:
            before = made.head()
            code = sign_module.main(['login', '--project-root', made.root])
            lines = capsys.readouterr().out.splitlines()
            assert (code, lines) == (1, [self.REFUSED])
            assert (made.signatures(), made.head()) == ([], before)
        finally:
            made.close()


class TestTheTiedTest:

    # purlin: signatures PROOF-200
    def test_a_stop_names_the_test_under_its_proof(self, at_signed):
        stop = stops_of(at_signed)['RULE-1']
        at = stop.index('  PROOF-1: POST /login with the password "secret"; '
                        'verify 200 and a token')
        assert stop[at + 1] == ('    tied to tests/test_login.py::'
                                'test_valid_credentials_return_200'), stop

    # purlin: signatures PROOF-201
    def test_a_proof_no_test_carries_out_says_so(self, at_signed):
        at_signed.spec(SPEC + '- PROOF-3 (RULE-2): POST /login with no '
                       'password; verify 401\n')
        stop = sign_module.render_row(at_signed.rule('RULE-2')).splitlines()
        at = stop.index('  PROOF-3: POST /login with no password; verify 401')
        assert stop[at + 1] == '    tied to no test', stop
