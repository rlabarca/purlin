"""Tests for the sign-off reader and the walk that writes one.

Every fixture is written by the test in a throwaway project: a spec, a test
file, the evidence, the evidence package, a sign-off. Nothing here reads this
repository's own specs, reaches a network, or signs with a key that exists
anywhere but the temporary directory the test made.

The package each project carries is written here, by `write_package`, to the
shape `references/formats/package_format.md` gives it, so the walk is tested
over a package whatever wrote it.

What each group holds:

*the key*        the fingerprint of the key a signer signs with, and the
                 lines to print when there is none
*what counts*    a sign-off's commit, signed and verified, and its package
*the refusals*   what stops a sign-off, in order
*the walk*       the overview, the stops, the strong list and the answers
*the sign-off*   the file, its commit, the tag, a second signer
*the agent*      `--show` and `--answers`
"""

import hashlib
import json
import os
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
from purlin import specs as purlin_specs  # noqa: E402
from sign_project import (  # noqa: E402
    FIRST_GATE,
    SIGNING_GATE,
    SIGN_PY,
    SPEC,
    TEST_NAMES,
    Project,
    _Out,
    git,
    write)


# ---------------------------------------------------------------------------
# The throwaway project and its package
# ---------------------------------------------------------------------------

MANUAL_SPEC = SPEC.replace('verify 401 and the body "denied"\n',
                           'verify 401 and the body "denied" @manual\n')
WINDOWS_SPEC = SPEC.replace('verify 200 and a token\n',
                            'verify 200 and a token @env(windows)\n')
MACHINE = 'jane-laptop'
EMAIL = 'jane@acme.com'
VERSION = '2.1.0'
PACKAGE = '.purlin/evidence/package/%s.json' % VERSION
SIGNOFFS = '.purlin/evidence/package/%s.signoffs' % VERSION
ANSWERS = '.purlin/runtime/signoff-answers.json'


def record(made, failing=(), systems=None):
    """Write each system's results for both proofs, `failing` ones failing.

    `systems` defaults to this machine's own; each gets a section of its own.
    """
    rel = '.purlin/evidence/local/login.json'
    proofs = [{'id': proof_id, 'rule': 'RULE-%s' % proof_id[-1],
               'result': 'fail' if proof_id in failing else 'pass',
               'env': None, 'manual': False,
               'test': 'tests/test_login.py::%s' % TEST_NAMES[proof_id]}
              for proof_id in ('PROOF-1', 'PROOF-2')]
    data = {'schema': purlin_evidence.SCHEMA, 'feature': 'login',
            'source': 'local', 'spec': 'specs/auth/login.md',
            'platforms': {os_name: {
                'commit': made.head(), 'dirty': False,
                'at': '2026-09-13T12:00:00Z', 'runner': 'jane',
                'machine': MACHINE, 'hostname': MACHINE,
                'fingerprint': purlin_fingerprint.fingerprint(made.root,
                                                              'login'),
                'rules': {}, 'proofs': proofs}
                for os_name in systems or (purlin_evidence.host_os(),)}}
    write(os.path.join(made.root, *rel.split('/')),
          json.dumps(data, indent=2, sort_keys=True))


def commit_all(made, message='purlin: evidence at abc1234'):
    git(made.root, 'add', '-A')
    git(made.root, 'commit', '-q', '-m', message)


def _number(ident):
    return int(str(ident).rsplit('-', 1)[-1])


def package_body(made, verdicts=None, findings=None, failing=(),
                 untied=()):
    """The package for `2.1.0` over the project's specs, as the format shapes it.

    `verdicts` maps a rule id to what the audit found; a rule it leaves out
    was not audited. `failing` names the rules whose results failed, and
    `untied` the proofs the package lists no test for.
    """
    verdicts = verdicts or {}
    findings = findings or {}
    features, hand_checks, count = [], [], 0
    for name, info in sorted(purlin_specs.scan_specs(made.root).items()):
        rules = []
        for rule_id in sorted(info['rules'], key=_number):
            count += 1
            proofs = [{'id': proof_id, 'text': proof['text'],
                       'manual': bool(proof['manual']), 'env': proof['env']}
                      for proof_id, proof in sorted(info['proofs'].items(),
                                                    key=lambda i: _number(i[0]))
                      if rule_id in proof['rules']]
            tests = [{'proof': proof['id'], 'file': 'tests/test_login.py',
                      'name': TEST_NAMES[proof['id']]}
                     for proof in proofs
                     if not proof['manual'] and proof['id'] in TEST_NAMES
                     and proof['id'] not in untied]
            word = 'failed' if rule_id in failing else 'passed'
            verdict = verdicts.get(rule_id)
            if any(proof['manual'] for proof in proofs):
                hand_checks.append({'feature': name, 'rule': rule_id,
                                    'proofs': [proof['id'] for proof in proofs
                                               if proof['manual']],
                                    'checked': 'in the sign-offs'})
            rules.append({
                'id': rule_id, 'text': info['rules'][rule_id],
                'left': 'to_fix' if rule_id in failing else None,
                'proofs': proofs, 'tests': tests,
                'results': [{'os': purlin_evidence.host_os(),
                             'source': 'local', 'result': word,
                             'at': '2026-09-13T12:00:00Z',
                             'commit': made.head(), 'runner': 'jane',
                             'machine': MACHINE, 'current': True,
                             'out_of_date': []}],
                'audit': None if not verdict else {
                    'verdict': verdict,
                    'findings': list(findings.get(rule_id, ())),
                    'strength': None},
                'statuses': {'passed': {'word': word, 'reasons': []},
                             'strong': {'word': verdict or 'not audited',
                                        'reasons': []}}})
        features.append({'name': name, 'spec': info['spec_path'],
                         'scope': list(info.get('scope') or ()),
                         'anchor': bool(info['is_anchor']), 'rules': rules})
    package = {
        'schema': 'purlin-package/3',
        'state': 'not finished' if failing else 'finished',
        'rules': count, 'steps': {'passed': count - len(failing)},
        'audit': {'strong': 0, 'weak': 0, 'not_audited': 0}, 'left': [],
        'purlin_version': '0.10.0', 'project': 'proj', 'version': VERSION,
        'tag': 'signed/%s' % VERSION, 'commit': made.head(),
        'gate': SIGNING_GATE, 'mutation_engine': None, 'features': features,
        'hand_checks': hand_checks, 'warnings': [], 'fingerprint': ''}
    package['fingerprint'] = hashlib.sha256(
        json.dumps(package, sort_keys=True).encode('utf-8')).hexdigest()
    return package


def write_package(made, **kwargs):
    """Write the package and commit it alone, as the release run does."""
    package = package_body(made, **kwargs)
    write(os.path.join(made.root, *PACKAGE.split('/')),
          json.dumps(package, indent=2, sort_keys=True) + '\n')
    git(made.root, 'add', '--', PACKAGE)
    git(made.root, 'commit', '-q', '-m',
        'purlin: evidence at %s' % made.head()[:7])
    return package


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
                           ('gpg.ssh.program', 'ssh-keygen'),
                           ('user.signingkey', path + '.pub')):
        git(root, 'config', setting, value)
    return path + '.pub'


def ready(gate=SIGNING_GATE, spec=SPEC, verdicts=None, findings=None,
          failing=(), signer=True, package=True, systems=None, untied=()):
    """A project whose rules pass, with `VERSION` and its package committed."""
    made = Project(spec=spec, gate=gate)
    record(made, failing=['PROOF-%s' % rule[-1] for rule in failing],
           systems=systems)
    write(os.path.join(made.root, 'VERSION'), VERSION + '\n')
    commit_all(made)
    if package:
        made.package = write_package(made, verdicts=verdicts,
                                     findings=findings, failing=failing,
                                     untied=untied)
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


def status(root):
    return git(root, 'status', '--porcelain', '--untracked-files=all').stdout


def walked(made, answers, name=None):
    """Run the walk with `answers`, in order. `(exit, lines, questions)`.

    Once the answers run out, input ends, which stops the walk.
    """
    left, asked, out = list(answers), [], _Out()

    def ask(_kind, _key, prompt):
        asked.append(prompt)
        return left.pop(0) if left else None

    code = sign_module.walk(made.root, name, ask=ask, out=out)
    return code, out.text().splitlines(), asked


def stop_lines(lines, head):
    """The lines of the stop that opens on `head`, up to the next blank line."""
    start = lines.index(head)
    end = start
    while end < len(lines) and lines[end] and \
            not lines[end].startswith('Stopped at '):
        end += 1
    return lines[start:end]


def audit_shown(stop):
    """The lines of one stop from `What the audit found` on."""
    return stop[stop.index('What the audit found'):]


@pytest.fixture
def proved():
    """A project whose rules have evidence, with no package and no key yet."""
    made = Project(spec=SPEC)
    record(made)
    yield made
    made.close()


@pytest.fixture
def at_signed():
    """Both rules pass; `RULE-1` is strong and `RULE-2` weak."""
    made = ready(verdicts={'RULE-1': 'strong', 'RULE-2': 'weak'})
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


def signed_off(made, email=EMAIL):
    """The sign-off file `email` wrote for `2.1.0`, read back."""
    slug = purlin_signatures.signer_slug(email)
    return read_json(made.root, '%s/%s.json' % (SIGNOFFS, slug))


# ---------------------------------------------------------------------------
# The key a signer signs with
# ---------------------------------------------------------------------------

NO_KEY_LINES = ['No key to sign with. These commands set one up:',
                '  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""',
                '  git config gpg.format ssh',
                '  git config user.signingkey ~/.ssh/id_ed25519.pub']


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
    def test_a_key_that_is_not_ssh_is_no_key(self, home, capsys):
        made = ready(signer=False)
        try:
            git(made.root, 'config', 'gpg.format', 'ssh')
            git(made.root, 'config', 'user.signingkey', '3AA5C34371567BD2')
            code = sign_module.main(['--project-root', made.root])
            assert code == 1
            assert capsys.readouterr().out.splitlines()[0] == NO_KEY_LINES[0]
        finally:
            made.close()

    # purlin: signatures PROOF-21
    def test_without_a_key_the_commands_are_printed(self, home, capsys):
        made = ready(signer=False)
        try:
            before = made.head()
            code = sign_module.main(['--project-root', made.root])
            assert capsys.readouterr().out.splitlines() == NO_KEY_LINES
            assert (code, made.head()) == (1, before)
        finally:
            made.close()

    # purlin: signatures PROOF-95
    # purlin: signatures PROOF-153
    def test_an_existing_key_file_is_not_made_again(self, home, capsys):
        made = ready(signer=False)
        try:
            write(str(home / '.ssh' / 'id_ed25519'), 'a private key\n')
            code = sign_module.main(['--project-root', made.root])
            assert code == 1
            assert capsys.readouterr().out.splitlines() == [
                NO_KEY_LINES[0]] + NO_KEY_LINES[2:]
        finally:
            made.close()

    # purlin: signatures PROOF-22
    def test_the_script_runs_as_a_command(self, home):
        made = ready(signer=False)
        try:
            result = subprocess.run(
                [sys.executable, SIGN_PY, '--project-root', made.root],
                capture_output=True, text=True, timeout=120)
            assert result.returncode == 1, result.stdout + result.stderr
            assert result.stdout.splitlines() == NO_KEY_LINES, result.stdout
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What counts
# ---------------------------------------------------------------------------

class TestWhatCounts:

    def _committed(self, made, *commit_args, email=EMAIL):
        rel = '%s/%s.json' % (SIGNOFFS, purlin_signatures.signer_slug(email))
        write(os.path.join(made.root, *rel.split('/')),
              json.dumps({'signer': email}) + '\n')
        git(made.root, 'add', '-A')
        git(made.root, *(list(commit_args[:-1]) + [
            'commit', '-q', '-m', commit_args[-1]]))
        return purlin_signatures.counts(made.root, {'path': rel})

    # purlin: signatures PROOF-25
    # purlin: signatures PROOF-155
    def test_a_commit_signed_with_the_signers_key_counts(self, proved):
        key(proved.root)
        assert self._committed(proved, '-c', 'commit.gpgsign=true',
                               'sign(2.1.0): jane@acme.com') == (True, '')

    # purlin: signatures PROOF-96
    def test_an_unsigned_commit_does_not_count(self, proved):
        key(proved.root)
        assert self._committed(proved, '-c', 'commit.gpgsign=false',
                               'sign(2.1.0): jane@acme.com') == (
            False, 'the commit that added it is not signed')

    # purlin: signatures PROOF-97
    def test_a_key_nobody_registered_counts(self, proved):
        key(proved.root)
        stranger = os.path.join(proved.root, '.git', 'stranger-key')
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C',
                        'mallory@else.org', '-f', stranger], check=True)
        owner_only(stranger)
        assert self._committed(
            proved, '-c', 'user.signingkey=' + stranger + '.pub',
            '-c', 'commit.gpgsign=true', 'sign(2.1.0): mallory@else.org',
            email='mallory@else.org') == (True, '')

    # purlin: signatures PROOF-98
    def test_a_signed_commit_by_another_author_counts(self, proved):
        key(proved.root)
        rel = '%s/jane.json' % SIGNOFFS
        write(os.path.join(proved.root, *rel.split('/')), '{}\n')
        git(proved.root, 'add', '-A')
        git(proved.root, 'commit', '-q', '-S', '--author',
            'Bob <bob@else.org>', '-m', 'sign(2.1.0): jane@acme.com')
        assert git(proved.root, 'log', '-1', '--format=%ae').stdout.strip() \
            == 'bob@else.org'
        assert purlin_signatures.counts(proved.root, {'path': rel}) == (
            True, '')

    # purlin: signatures PROOF-217
    def test_it_counts_only_over_the_committed_package(self, at_signed):
        assert walked(at_signed, ['go on', 'continue', 'y'])[0] == 0
        assert [item['counts'] for item in purlin_signatures.load_signoffs(
            at_signed.root, VERSION)] == [True]
        package = read_json(at_signed.root, PACKAGE)
        package['fingerprint'] = 'f' * 64
        write(os.path.join(at_signed.root, *PACKAGE.split('/')),
              json.dumps(package, indent=2, sort_keys=True) + '\n')
        commit_all(at_signed, 'purlin: evidence at abc1234')
        found = purlin_signatures.load_signoffs(at_signed.root, VERSION)
        assert [(item['counts'], item['count_reason']) for item in found] == [
            (False, 'it signs another evidence package than the one '
                    'committed')]


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
    def test_a_signature_block_changed_does_not_verify(self, at_signed):
        assert walked(at_signed, ['go on', 'continue', 'y'])[0] == 0
        tamper_last_commit(at_signed.root)
        found = purlin_signatures.load_signoffs(at_signed.root, VERSION)
        assert [(item['counts'], item['count_reason']) for item in found] == [
            (False, 'the signature on the commit that added it does not '
                    'verify')]

    # purlin: signatures PROOF-193
    def test_a_key_deleted_since_still_counts(self, at_signed):
        assert walked(at_signed, ['go on', 'continue', 'y'])[0] == 0
        for name in ('signing-key', 'signing-key.pub'):
            os.remove(os.path.join(at_signed.root, '.git', name))
        git(at_signed.root, 'config', '--unset', 'user.signingkey')
        found = purlin_signatures.load_signoffs(at_signed.root, VERSION)
        assert [item['counts'] for item in found] == [True]


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------

class TestTheRefusals:

    def _only(self, made, capsys, argv=()):
        before = made.head()
        code = sign_module.main(list(argv) + ['--project-root', made.root])
        lines = capsys.readouterr().out.splitlines()
        assert made.head() == before
        return code, lines

    # purlin: signatures PROOF-202
    def test_at_passed_nothing_is_signed(self, capsys):
        made = ready(gate=FIRST_GATE)
        try:
            assert self._only(made, capsys) == (0, [
                'Nothing is signed at the gate passed: purlin:test --release '
                'tags the release unsigned. To sign releases, run '
                'purlin:init --gate signed.'])
        finally:
            made.close()

    # purlin: signatures PROOF-203
    def test_uncommitted_work_is_refused(self, at_signed, capsys):
        write(os.path.join(at_signed.root, 'notes.txt'), 'a note\n')
        assert self._only(at_signed, capsys) == (1, [
            'No sign-off: the working tree holds changes that are not '
            'committed. Commit them, then run purlin:test --release.'])

    # purlin: signatures PROOF-204
    def test_no_package_is_refused(self, capsys):
        made = ready(package=False)
        try:
            assert self._only(made, capsys) == (1, [
                'No sign-off: no evidence package for 2.1.0 is committed at '
                '%s. Run purlin:test --release.' % made.head()[:7]])
        finally:
            made.close()

    # purlin: signatures PROOF-205
    def test_a_commit_after_the_package_is_refused(self, at_signed, capsys):
        package_commit = at_signed.head()
        write(os.path.join(at_signed.root, 'src', 'login.py'),
              'def login(user, password):\n    return 401\n')
        commit_all(at_signed, 'fix(login): refuse')
        assert self._only(at_signed, capsys) == (1, [
            'No sign-off: the evidence package for 2.1.0 describes %s, and '
            '%s has changed since. Run purlin:test --release.'
            % (package_commit[:7], at_signed.head()[:7])])

    # purlin: signatures PROOF-206
    def test_a_rule_that_does_not_pass_is_refused(self, capsys):
        made = ready(failing=('RULE-2',))
        try:
            assert self._only(made, capsys) == (1, [
                'No sign-off: 1 rule does not pass at %s: login RULE-2. Run '
                'purlin:status to see what is left, then purlin:test '
                '--release.' % made.head()[:7]])
        finally:
            made.close()

    # purlin: signatures PROOF-207
    def test_a_host_copy_ahead_is_refused(self, at_signed, tmp_path, capsys):
        host = str(tmp_path / 'host.git')
        git(at_signed.root, 'init', '-q', '--bare', host)
        git(at_signed.root, 'remote', 'add', 'origin', host)
        # A push that negotiates first fails against a bare repository on
        # some hosts' git settings; this one sends everything.
        git(at_signed.root, '-c', 'push.negotiate=false', 'push', '-q',
            'origin', 'main')
        other = str(tmp_path / 'other')
        git(at_signed.root, 'clone', '-q', '-b', 'main', host, other)
        git(other, 'config', 'user.email', 'omar@example.org')
        git(other, 'config', 'user.name', 'Omar')
        git(other, 'config', 'commit.gpgsign', 'false')
        git(other, 'commit', '-q', '--allow-empty', '-m', 'chore: ahead')
        git(other, '-c', 'push.negotiate=false', 'push', '-q', 'origin',
            'main')
        git(at_signed.root, 'fetch', '-q', 'origin')
        assert self._only(at_signed, capsys) == (1, [
            'No sign-off: origin/main holds 1 commit that %s does not, as '
            'this checkout last fetched it. Pull, then run purlin:sign.'
            % at_signed.head()[:7]])

    # purlin: signatures PROOF-208
    def test_a_second_sign_off_by_the_same_signer_is_refused(
            self, at_signed, capsys):
        assert walked(at_signed, ['go on', 'continue', 'y'])[0] == 0
        assert self._only(at_signed, capsys) == (1, [
            'jane@acme.com has already signed 2.1.0 over this package; '
            'nothing was written.'])


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

class TestTheWalk:

    # purlin: signatures PROOF-209
    def test_it_opens_on_the_overview(self):
        made = ready(verdicts={'RULE-1': 'strong'})
        try:
            lines = walked(made, [])[1]
            assert lines[:4] == [
                'Signing 2.1.0: .purlin/evidence/package/2.1.0.json, at %s.'
                % made.head()[:7],
                '  2 rules on %s: 2 pass their tests, 0 are checked by hand.'
                % purlin_evidence.os_word(purlin_evidence.host_os()),
                '  The audit: 1 strong, 0 weak, 1 not audited.',
                '  1 stop: 0 hand checks, 0 weak, 1 not audited.']
        finally:
            made.close()

    # purlin: signatures PROOF-210
    def test_a_weak_stop_shows_the_test_and_the_results(self, at_signed):
        lines = walked(at_signed, ['go on'])[1]
        stop = stop_lines(lines, 'login RULE-2   weak')
        tied = stop.index('    tied to tests/test_login.py::'
                          'test_a_bad_password_is_denied')
        assert stop[tied + 1:tied + 3] == [
            '      def test_a_bad_password_is_denied():',
            '          assert login("ada", "wrong") == 401']
        assert stop[stop.index('Results') + 1] == '  %s: passed on %s' % (
            purlin_evidence.os_word(purlin_evidence.host_os()), MACHINE)

    # purlin: signatures PROOF-211
    def test_a_hand_check_stops_first_and_asks_what_was_seen(self):
        made = ready(spec=MANUAL_SPEC, verdicts={'RULE-1': 'weak'})
        try:
            code, lines, asked = walked(made, [])
            heads = [line for line in lines if line.startswith('login RULE-')]
            assert heads == ['login RULE-2   hand check']
            assert 'Results' not in stop_lines(lines, heads[0])
            assert asked == [
                'login RULE-2   what did you see, in one line, or stop: ']
        finally:
            made.close()

    # purlin: signatures PROOF-212
    def test_the_strong_list_opens_on_list(self):
        made = ready(verdicts={'RULE-1': 'strong', 'RULE-2': 'strong'})
        try:
            code, lines, asked = walked(made, ['list'])
            assert asked[:2] == [
                '2 rules the audit found strong. list / walk / go on: ',
                'walk / go on: ']
            assert '  login RULE-1, RULE-2' in lines
        finally:
            made.close()

    # purlin: signatures PROOF-213
    def test_walk_makes_each_strong_rule_a_stop_after_the_others(
            self, at_signed):
        lines = walked(at_signed, ['walk', 'continue'])[1]
        heads = [line for line in lines if line.startswith('login RULE-')]
        assert heads == ['login RULE-2   weak', 'login RULE-1   strong']

    # purlin: signatures PROOF-166
    def test_a_proof_for_one_system_shows_its_tag(self):
        made = ready(spec=WINDOWS_SPEC,
                     systems=(purlin_evidence.host_os(), 'windows'))
        try:
            stop = stop_lines(walked(made, [])[1], 'login RULE-1   not audited')
            assert ('  PROOF-1 (@env(windows)): POST /login with the password '
                    '"secret"; verify 200 and a token') in stop
        finally:
            made.close()

    # purlin: signatures PROOF-200
    def test_a_stop_names_the_test_under_its_proof(self):
        made = ready()
        try:
            stop = stop_lines(walked(made, [])[1], 'login RULE-1   not audited')
            proof = next(i for i, line in enumerate(stop)
                         if line.startswith('  PROOF-1:'))
            assert stop[proof + 1] == ('    tied to tests/test_login.py::'
                                       'test_valid_credentials_return_200')
        finally:
            made.close()

    # purlin: signatures PROOF-201
    def test_a_proof_no_test_carries_out_says_so(self):
        made = ready(untied=('PROOF-2',))
        try:
            lines = walked(made, ['continue'])[1]
            stop = stop_lines(lines, 'login RULE-2   not audited')
            proof = next(i for i, line in enumerate(stop)
                         if line.startswith('  PROOF-2:'))
            assert stop[proof + 1] == '    tied to no test'
        finally:
            made.close()


class TestWhatTheAuditFound:

    def _audit(self, verdicts, findings, head, answers):
        made = ready(verdicts=verdicts, findings=findings)
        try:
            return audit_shown(stop_lines(walked(made, answers)[1], head))
        finally:
            made.close()

    # purlin: signatures PROOF-167
    def test_no_audit_yet(self):
        assert self._audit({}, {}, 'login RULE-1   not audited', []) == [
            'What the audit found',
            "  No audit has read this rule's text, proof and test yet."]

    # purlin: signatures PROOF-168
    def test_strong_with_no_finding(self):
        assert self._audit({'RULE-1': 'strong', 'RULE-2': 'strong'}, {},
                           'login RULE-1   strong', ['walk']) == [
            'What the audit found', '  Strong. It found nothing.']

    # purlin: signatures PROOF-169
    def test_strong_with_a_finding(self):
        assert self._audit(
            {'RULE-1': 'strong', 'RULE-2': 'strong'},
            {'RULE-1': ['PROOF-1 reads the status alone.']},
            'login RULE-1   strong', ['walk']) == [
            'What the audit found', '  Strong.',
            '  PROOF-1 reads the status alone.']

    # purlin: signatures PROOF-170
    def test_weak_with_a_finding(self):
        assert self._audit(
            {'RULE-1': 'strong', 'RULE-2': 'weak'},
            {'RULE-2': ['PROOF-2 reads the status alone.']},
            'login RULE-2   weak', ['go on']) == [
            'What the audit found', '  Weak.',
            '  PROOF-2 reads the status alone.']

    # purlin: signatures PROOF-171
    def test_undecided_with_a_finding(self):
        assert self._audit(
            {'RULE-1': 'strong', 'RULE-2': 'undecided'},
            {'RULE-2': ['PROOF-2 names no status.']},
            'login RULE-2   weak', ['go on']) == [
            'What the audit found',
            '  Undecided. The AI audit could not decide, so the rule reads '
            'weak until its proof or test changes.',
            '  PROOF-2 names no status.']


class TestStoppingAndNo:

    # purlin: signatures PROOF-218
    def test_stop_writes_nothing(self, at_signed):
        before = at_signed.head()
        code, lines, _asked = walked(at_signed, ['go on', 'stop'])
        assert lines[-1] == (
            'Stopped at login RULE-2: nothing was signed. After the fix, run '
            'purlin:test --release, then purlin:sign.')
        assert (code, at_signed.head(), status(at_signed.root)) == (
            0, before, '')

    # purlin: signatures PROOF-219
    def test_no_to_the_last_question_writes_nothing(self, at_signed):
        before = at_signed.head()
        code, lines, asked = walked(at_signed, ['go on', 'continue', ''])
        assert asked[-1] == ('Sign the evidence package for 2.1.0 as '
                             'jane@acme.com? [y/N] ')
        assert lines[-1] == 'Nothing was signed.'
        assert (code, at_signed.head(), status(at_signed.root)) == (
            0, before, '')


# ---------------------------------------------------------------------------
# The sign-off, its commit and the tag
# ---------------------------------------------------------------------------

class TestTheSignOff:

    # purlin: signatures PROOF-214
    def test_it_records_what_was_shown_and_every_note(self):
        made = ready(spec=MANUAL_SPEC, verdicts={'RULE-1': 'strong'})
        try:
            assert walked(made, ['go on', 'the lockout page read 401',
                                 'y'])[0] == 0
            body = signed_off(made)
            assert body['package_hash'] == made.package['fingerprint']
            assert body['shown']['one_by_one'] == [
                {'feature': 'login', 'rule': 'RULE-2', 'why': 'hand check'}]
            assert body['shown']['in_list'] == [
                {'feature': 'login', 'rule': 'RULE-1'}]
            assert body['shown']['list_opened'] is False
            assert body['notes'] == [
                {'feature': 'login', 'rule': 'RULE-2', 'kind': 'hand check',
                 'note': 'the lockout page read 401'}]
            text = json.dumps(body)
            assert not any('"%s"' % word in text
                           for word in ('go on', 'continue', 'y', 'yes'))
        finally:
            made.close()

    # purlin: signatures PROOF-215
    def test_the_first_sign_off_writes_the_tag_on_its_commit(self, at_signed):
        before = at_signed.head()
        code, lines, _asked = walked(at_signed, ['go on', 'continue', 'y'])
        head = at_signed.head()
        assert code == 0
        assert git(at_signed.root, 'rev-list', '--count',
                   before + '..HEAD').stdout.strip() == '1'
        assert git(at_signed.root, 'log', '-1', '--format=%s').stdout \
            .strip() == 'sign(2.1.0): jane@acme.com'
        assert signed_by_last_commit(at_signed.root)
        assert git(at_signed.root, 'show', '--name-only', '--format=',
                   'HEAD').stdout.split() == ['%s/jane.json' % SIGNOFFS]
        assert git(at_signed.root, 'rev-parse',
                   'signed/2.1.0^{commit}').stdout.strip() == head
        assert 'Tagged signed/2.1.0 at %s.' % head[:7] in lines

    # purlin: signatures PROOF-216
    def test_a_later_sign_off_leaves_the_tag(self, at_signed):
        assert walked(at_signed, ['go on', 'continue', 'y'])[0] == 0
        first = at_signed.head()
        key(at_signed.root, email='pat@acme.com', name='Pat', file='pat-key')
        code, lines, _asked = walked(at_signed, ['go on', 'continue', 'y'])
        assert code == 0
        assert git(at_signed.root, 'rev-parse',
                   'signed/2.1.0^{commit}').stdout.strip() == first
        assert lines[-2:] == [
            'signed/2.1.0 stays at %s; this sign-off is added after it. Push '
            'it: git push' % first[:7],
            'Sign-offs of 2.1.0: jane@acme.com, pat@acme.com.']

    # purlin: signatures PROOF-178
    def test_the_tag_carries_the_signers_ssh_signature(self, at_signed,
                                                       tmp_path):
        assert walked(at_signed, ['go on', 'continue', 'y'])[0] == 0
        public = git(at_signed.root, 'config', 'user.signingkey').stdout \
            .strip()
        with open(public, encoding='utf-8') as handle:
            allowed = '%s %s' % (EMAIL, handle.read().strip())
        allowed_file = tmp_path / 'allowed'
        allowed_file.write_text(allowed + '\n', encoding='utf-8')
        checked = git(at_signed.root, '-c',
                      'gpg.ssh.allowedSignersFile=%s' % allowed_file,
                      'tag', '-v', 'signed/2.1.0')
        said = checked.stdout + checked.stderr
        assert checked.returncode == 0, said
        assert 'Good "git" signature' in said, said
        assert fingerprint_of(public) in said, said

    # purlin: signatures PROOF-75
    # purlin: signatures PROOF-157
    def test_it_records_the_signer_as_git_holds_them_and_the_key(self):
        made = ready(verdicts={'RULE-1': 'strong', 'RULE-2': 'strong'},
                     signer=False)
        try:
            public = key(made.root, email='Jane.Doe@Acme.com',
                         name='Jane Doe')
            assert walked(made, ['go on', 'y'])[0] == 0
            body = signed_off(made, 'Jane.Doe@Acme.com')
            assert (body['signer'], body['signer_name'],
                    body['key_fingerprint']) == (
                'Jane.Doe@Acme.com', 'Jane Doe', fingerprint_of(public))
        finally:
            made.close()

    # purlin: signatures PROOF-27
    def test_anyone_with_a_key_signs(self, capsys):
        made = ready(verdicts={'RULE-1': 'strong', 'RULE-2': 'strong'},
                     signer=False)
        try:
            key(made.root, email='omar@example.org', name='Omar')
            assert walked(made, ['go on', 'y'])[0] == 0
            assert os.path.isfile(os.path.join(
                made.root, *('%s/omar.json' % SIGNOFFS).split('/')))
        finally:
            made.close()

    # purlin: signatures PROOF-162
    def test_gits_own_message_is_named(self, at_signed):
        hook = os.path.join(at_signed.root, '.git', 'hooks', 'pre-commit')
        with open(hook, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write('#!/bin/sh\n'
                         'echo "error: the hook refused the commit." >&2\n'
                         'exit 1\n')
        os.chmod(hook, 0o755)
        before = at_signed.head()
        code, lines, _asked = walked(at_signed, ['go on', 'continue', 'y'])
        assert lines[-1] == (
            'The sign-off commit was not made: the hook refused the commit. '
            'Nothing was signed; run purlin:sign again.')
        assert (code, at_signed.head(), status(at_signed.root)) == (
            1, before, '')


# ---------------------------------------------------------------------------
# The agent's walk
# ---------------------------------------------------------------------------

class TestTheAgent:

    # purlin: signatures PROOF-220
    def test_show_asks_nothing_and_writes_nothing(self, at_signed, capsys):
        before = at_signed.head()
        code = sign_module.main(['--show', '--project-root', at_signed.root])
        lines = capsys.readouterr().out.splitlines()
        assert lines[0].startswith('Signing 2.1.0: ')
        stop = stop_lines(lines, 'login RULE-2   weak')
        assert not any('continue / note / stop' in line for line in lines)
        assert stop[-2:] == ['What the audit found', '  Weak.']
        assert '  login RULE-1' in lines
        assert lines[-1] == ('Answer each stop, then run purlin:sign '
                             '--answers <file>.')
        assert (code, at_signed.head(), status(at_signed.root)) == (
            0, before, '')

    # purlin: signatures PROOF-221
    def test_answers_walk_with_the_files_answers(self, at_signed, capsys):
        path = os.path.join(at_signed.root, *ANSWERS.split('/'))
        write(path, json.dumps({
            'strong': 'go on',
            'stops': {'login RULE-2': {'answer': 'note',
                                       'note': 'check the lockout copy'}},
            'sign': True}))
        code = sign_module.main(['--answers', path, '--project-root',
                                 at_signed.root])
        lines = capsys.readouterr().out.splitlines()
        assert 'login RULE-2   continue / note / stop: note' in lines
        assert code == 0
        assert signed_off(at_signed)['notes'] == [
            {'feature': 'login', 'rule': 'RULE-2', 'kind': 'note',
             'note': 'check the lockout copy'}]

    # purlin: signatures PROOF-222
    def test_a_stop_with_no_answer_is_refused(self, at_signed, capsys,
                                              monkeypatch):
        write(os.path.join(at_signed.root, *ANSWERS.split('/')),
              json.dumps({'strong': 'go on', 'stops': {}, 'sign': True}))
        monkeypatch.chdir(at_signed.root)
        before = at_signed.head()
        code = sign_module.main(['--answers', ANSWERS])
        assert capsys.readouterr().out.splitlines() == [
            'No sign-off: login RULE-2 has no answer in %s. Answer every '
            'stop, then run purlin:sign --answers %s again.'
            % (ANSWERS, ANSWERS)]
        assert (code, at_signed.head()) == (1, before)


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class TestTheCommandLine:

    # purlin: signatures PROOF-28
    def test_help_exits_zero(self, capsys):
        assert sign_module.main(['--help']) == 0
        assert capsys.readouterr().out.splitlines()[0] == (
            "Sign a release's evidence package, as a signed commit.")

    # purlin: signatures PROOF-132
    def test_an_unknown_option_after_another_exits_two(self, capsys):
        assert sign_module.main(['--release', '2.1.0', '--nope']) == 2
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
        code = sign_module.main(['--project-root', at_signed.root])
        lines = capsys.readouterr().out.splitlines()
        assert len(lines) == 1, lines
        assert lines[0].startswith('.purlin/config.json cannot be read: '), lines
        assert lines[0].endswith('Fix the file by hand; nothing ran and '
                                 'nothing was saved.'), lines
        assert (code, at_signed.head()) == (1, before)
