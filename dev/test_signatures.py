"""Tests for the sign-off: the walk, its refusals, the sign-off file and its commit.

Every fixture is written by the test in a throwaway project: a spec, a test
file, the evidence, a key. Nothing here reads this repository's own specs,
reaches a network, or signs with a key that exists anywhere but the
temporary directory the test made. A git host is a bare repository on disk.

The walk runs in the test's own process through `sign.walk`, answered by a
list of lines; `sign.main` stands for the command line.

What each group holds:

*the key*        the fingerprint of the key a signer signs with, and the
                 lines to print when there is none
*what counts*    a sign-off's commit, signed and verified, and its package
*signed*         where the status reads `signed`, and a tag passed over
*the refusals*   what stops a sign-off
*the 0.9.5 markers*  no sign-off while a test still carries one
*the walk*       the run lines, the overview, the audit's findings, the stops
*settled by judgment*  a proof settled with its test unchanged, in the list
*the sign-off*   the file, its commit, the tag, a second signer, a tag git
                 could not write
*the key that signed*  a commit signed with another key than the one named
*the last note*  what a hand check's stop shows of the sign-off before
*the agent*      `--show`, `--answers` and `--check`
"""

import json
import os
import re
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
from sign_project import SPEC, TEST_FILE, TEST_NAMES, Project, _Out, git, write  # noqa: E402


# ---------------------------------------------------------------------------
# The throwaway project
# ---------------------------------------------------------------------------

EMAIL = 'jane@acme.com'
DANA = 'dana.dev@labconnect.example'
MACHINE = 'dana-laptop'
# The git email a project's own run on another system set.
RUNNER = 'runner@example.com'
AT = '2026-10-01T12:17:13Z'
VERSION = '2.1.0'
PACKAGE = '.purlin/evidence/package/%s.json' % VERSION
SIGNOFFS = '.purlin/evidence/package/%s.signoffs' % VERSION
ANSWERS = '.purlin/runtime/signoff-answers.json'
FINDING = 'PROOF-1 reads the status alone.'

# `login RULE-2` checked by hand: its one proof is `@manual`.
MANUAL_SPEC = SPEC.replace('verify 401 and the body "denied"\n',
                           'verify 401 and the body "denied" @manual\n')
MANUAL_TEST_FILE = TEST_FILE.split('\n\n\n# purlin: login PROOF-2')[0] + '\n'


def section(made, proofs, rules, source='local', os_name='linux',
            email=DANA, machine=MACHINE, at=AT, commit=None,
            feature='login', carried=None):
    """One evidence section, as the run writes it, over the project as it stands.

    `proofs` is `[(id, rule, result, test name or None, reason or None)]`;
    `rules` is `{RULE-N: word}`. A section has the same fields under either
    source. `carried`, where the run carried every result forward, is what
    each entry holds of the run that took it.
    """
    entries = []
    for proof_id, rule, result, name, reason in proofs:
        entry = {'id': proof_id, 'rule': rule, 'result': result, 'env': None,
                 'manual': False,
                 'test': 'tests/test_%s.py::%s' % (feature, name) if name
                 else ''}
        if reason is not None:
            entry['reason'] = reason
        if carried is not None:
            entry['carried'] = dict(carried)
        entries.append(entry)
    found = {'commit': commit or made.head(), 'dirty': False, 'at': at,
             'runner': email.split('@')[0], 'email': email,
             'machine': machine,
             'fingerprint': purlin_fingerprint.fingerprint(made.root, feature),
             'rules': dict(rules), 'proofs': entries}
    rel = '.purlin/evidence/%s/%s.json' % (source, feature)
    path = os.path.join(made.root, *rel.split('/'))
    try:
        with open(path, encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError):
        data = {'schema': purlin_evidence.SCHEMA, 'feature': feature,
                'source': source,
                'spec': 'specs/auth/%s.md' % feature if feature == 'login'
                else 'specs/%s.md' % feature,
                'platforms': {}}
    data['platforms'][os_name] = found
    write(path, json.dumps(data, indent=2, sort_keys=True))
    return rel


def passing(made, failing=(), **kwargs):
    """Both of `login`'s proofs, passing but for the rules `failing` names."""
    proofs, rules = [], {}
    for proof_id in ('PROOF-1', 'PROOF-2'):
        rule = 'RULE-%s' % proof_id[-1]
        word = 'fail' if rule in failing else 'pass'
        proofs.append((proof_id, rule, word, TEST_NAMES[proof_id], None))
        rules[rule] = 'failed' if rule in failing else 'passed'
    return section(made, proofs, rules, **kwargs)


def commit_all(made, message='purlin: evidence at abc1234'):
    git(made.root, 'add', '-A')
    git(made.root, 'commit', '-q', '-m', message)


def owner_only(private_key):
    """On Windows, leave the private key readable by its owner alone.

    Windows' own `ssh-keygen` refuses to sign with a key file other accounts
    can read, and a file in the temporary folder inherits that folder's
    permissions. Elsewhere `ssh-keygen` already wrote it so.
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


def ready(spec=SPEC, test_file=None, version=VERSION, failing=(), weak=(),
          strong=(), signer=True):
    """A project whose rules pass, its `VERSION` and its results committed.

    `weak` and `strong` name the rules the audit read; a rule in neither was
    not audited. A `@manual` proof has no test and no result.
    """
    made = Project(spec=spec)
    if test_file is not None:
        made.edit_test(test_file)
    if version:
        write(os.path.join(made.root, 'VERSION'), version + '\n')
        commit_all(made, 'chore: version')
    if test_file is MANUAL_TEST_FILE:
        section(made, [('PROOF-1', 'RULE-1', 'pass', TEST_NAMES['PROOF-1'],
                        None)], {'RULE-1': 'passed', 'RULE-2': 'passed'})
    else:
        passing(made, failing=failing)
    for rule in strong:
        made.audit(rule)
    for rule in weak:
        made.audit(rule, findings=[FINDING.replace('PROOF-1', 'PROOF-%s'
                                                   % rule[-1])])
    commit_all(made)
    if signer:
        key(made.root)
    return made


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


def run_main(made, capsys, argv=()):
    """`sign.py` over the project; `(exit, lines)`, the project's HEAD unmoved."""
    before = made.head()
    code = sign_module.main(list(argv) + ['--project-root', made.root])
    lines = capsys.readouterr().out.splitlines()
    assert made.head() == before
    return code, lines


def fingerprint_of(public_key_path):
    """What `ssh-keygen -l` prints as the key's fingerprint."""
    shown = subprocess.run(['ssh-keygen', '-l', '-f', public_key_path],
                           capture_output=True, text=True, check=True).stdout
    return shown.split()[1]


def read_json(root, rel):
    with open(os.path.join(root, *rel.split('/')), encoding='utf-8') as handle:
        return json.load(handle)


def status(root):
    return git(root, 'status', '--porcelain', '--untracked-files=all').stdout


def changed_in_head(root):
    return git(root, 'show', '--name-only', '--format=', 'HEAD').stdout.split()


def signed_off(made, email=EMAIL, version=VERSION):
    """The sign-off file `email` wrote for `version`, read back."""
    slug = purlin_signatures.signer_slug(email)
    return read_json(made.root, '.purlin/evidence/package/%s.signoffs/%s.json'
                     % (version, slug))


def stop_lines(lines, head):
    """The lines of the stop that opens on `head`, up to the next blank line."""
    start = lines.index(head)
    end = start
    while end < len(lines) and lines[end]:
        end += 1
    return lines[start:end]


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A home directory holding nothing, so no key and no git settings leak in."""
    monkeypatch.setenv('HOME', str(tmp_path))
    if os.name == 'nt':
        monkeypatch.setenv('USERPROFILE', str(tmp_path))
    monkeypatch.setenv('XDG_CONFIG_HOME', str(tmp_path / '.config'))
    return tmp_path


@pytest.fixture
def signed():
    """Both rules pass and are strong; Jane is ready to sign."""
    made = ready(strong=('RULE-1', 'RULE-2'))
    yield made
    made.close()


@pytest.fixture
def hand_checked():
    """`login RULE-2` is a hand check and `RULE-1` the audit found weak."""
    made = ready(spec=MANUAL_SPEC, test_file=MANUAL_TEST_FILE, weak=('RULE-1',))
    yield made
    made.close()


# ---------------------------------------------------------------------------
# The key a signer signs with
# ---------------------------------------------------------------------------

NO_KEY_LINES = ['No key to sign with. These commands set one up:',
                '  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N ""',
                '  git config gpg.format ssh',
                '  git config user.signingkey ~/.ssh/id_ed25519.pub']


class TestTheKey:

    # purlin: signatures PROOF-115
    def test_a_public_key_path_reads_as_ssh_keygen_prints_it(self):
        made = Project()
        try:
            public = key(made.root)
            assert purlin_signatures.key_fingerprint(made.root) == \
                fingerprint_of(public)
        finally:
            made.close()

    # purlin: signatures PROOF-116
    def test_a_private_key_path_reads_the_public_key_beside_it(self):
        made = Project()
        try:
            public = key(made.root)
            private = public[:-len('.pub')]
            if os.name == 'nt':
                private = private.replace('/', '\\')
            git(made.root, 'config', 'user.signingkey', private)
            assert purlin_signatures.key_fingerprint(made.root) == \
                fingerprint_of(public)
        finally:
            made.close()

    # purlin: signatures PROOF-118
    def test_a_gpg_key_id_is_no_key(self, home, capsys):
        made = ready(signer=False)
        try:
            git(made.root, 'config', 'gpg.format', 'ssh')
            git(made.root, 'config', 'user.signingkey', '3AA5C34371567BD2')
            code, lines = run_main(made, capsys)
            assert (code, lines[0]) == (1, NO_KEY_LINES[0])
        finally:
            made.close()

    # purlin: signatures PROOF-21
    def test_with_no_key_the_four_lines_are_printed(self, home, capsys):
        made = ready(signer=False)
        try:
            assert run_main(made, capsys) == (1, NO_KEY_LINES)
        finally:
            made.close()

    # purlin: signatures PROOF-95
    def test_an_existing_key_file_leaves_the_ssh_keygen_line_out(
            self, home, capsys):
        made = ready(signer=False)
        try:
            write(str(home / '.ssh' / 'id_ed25519'), 'a private key\n')
            assert run_main(made, capsys) == (
                1, [NO_KEY_LINES[0]] + NO_KEY_LINES[2:])
        finally:
            made.close()


# ---------------------------------------------------------------------------
# What counts
# ---------------------------------------------------------------------------

def committed_signoff(made, *commit_args, email=EMAIL):
    """Commit a sign-off file for `2.1.0`; what `counts` answers for it."""
    rel = '%s/%s.json' % (SIGNOFFS, purlin_signatures.signer_slug(email))
    write(os.path.join(made.root, *rel.split('/')),
          json.dumps({'signer': email}) + '\n')
    git(made.root, 'add', '-A')
    git(made.root, *(list(commit_args[:-1]) + ['commit', '-q', '-m',
                                                commit_args[-1]]))
    return purlin_signatures.counts(made.root, {'path': rel})


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


def counted(made):
    return [(item['counts'], item['count_reason']) for item in
            purlin_signatures.load_signoffs(made.root, VERSION)]


class TestWhatCounts:

    # purlin: signatures PROOF-96
    def test_a_file_committed_with_signing_off_does_not_count(self):
        made = Project()
        try:
            key(made.root)
            assert committed_signoff(made, '-c', 'commit.gpgsign=false',
                                     'sign(2.1.0): jane@acme.com') == (
                False, 'the commit that added it is not signed')
        finally:
            made.close()

    # purlin: signatures PROOF-97
    def test_a_key_made_on_the_spot_for_mallory_counts(self):
        made = Project()
        try:
            stranger = os.path.join(made.root, '.git', 'stranger-key')
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C',
                            'mallory@else.org', '-f', stranger], check=True)
            owner_only(stranger)
            git(made.root, 'config', 'gpg.format', 'ssh')
            assert committed_signoff(
                made, '-c', 'user.signingkey=' + stranger + '.pub',
                '-c', 'user.email=mallory@else.org', '-c', 'commit.gpgsign=true',
                'sign(2.1.0): mallory@else.org',
                email='mallory@else.org') == (True, '')
        finally:
            made.close()

    # purlin: signatures PROOF-217
    def test_it_counts_only_over_the_committed_package(self, signed):
        assert walked(signed, ['y'])[0] == 0
        assert counted(signed) == [(True, '')]
        package = read_json(signed.root, PACKAGE)
        package['fingerprint'] = 'f' * 64
        write(os.path.join(signed.root, *PACKAGE.split('/')),
              json.dumps(package, indent=2) + '\n')
        commit_all(signed, 'chore: the package edited')
        assert counted(signed) == [
            (False, 'it signs another evidence package than the one committed')]

    # purlin: signatures PROOF-254
    def test_a_package_edited_after_signing_ends_the_sign_off(self, signed):
        assert walked(signed, ['y'])[0] == 0
        assert counted(signed) == [(True, '')]
        path = os.path.join(signed.root, *PACKAGE.split('/'))
        with open(path, 'rb') as handle:
            data = handle.read()
        edited = data.replace(b'"passed"', b'"failed"', 1)
        assert edited != data
        with open(path, 'wb') as handle:
            handle.write(edited)
        commit_all(signed, 'chore: the package edited')
        assert json.loads(edited)['fingerprint'] == \
            json.loads(data)['fingerprint']
        assert [item[0] for item in counted(signed)] == [False]
        before = signed.head()
        code, lines, _asked = sign_as(signed, 'pat@acme.com', 'Pat')
        assert len(lines) == 1, lines
        assert lines[0].startswith(
            'No sign-off: .purlin/evidence/package/2.1.0.json does not match '
            'its fingerprint:'), lines
        assert (code, signed.head(), status(signed.root)) == (1, before, '')

    # purlin: signatures PROOF-192
    def test_a_signature_block_changed_does_not_verify(self, signed):
        assert walked(signed, ['y'])[0] == 0
        tamper_last_commit(signed.root)
        assert counted(signed) == [
            (False, 'the signature on the commit that added it does not '
                    'verify')]

    # purlin: signatures PROOF-193
    def test_a_key_deleted_since_still_counts(self, signed):
        assert walked(signed, ['y'])[0] == 0
        for name in ('signing-key', 'signing-key.pub'):
            os.remove(os.path.join(signed.root, '.git', name))
        git(signed.root, 'config', '--unset', 'user.signingkey')
        assert counted(signed) == [(True, '')]


# ---------------------------------------------------------------------------
# Where the status reads `signed`
# ---------------------------------------------------------------------------

def signoff_and_warnings(made):
    """The payload's `signoff.word`, and its warnings that name a tag."""
    payload = made.payload()
    return (payload['signoff']['word'],
            [line for line in payload['warnings']
             if line.startswith('signed/')])


class TestWhereItReadsSigned:

    # purlin: signatures PROOF-252
    def test_a_tag_typed_by_hand_is_no_sign_off(self, signed):
        git(signed.root, 'tag', 'signed/9.9.9')
        assert not os.path.exists(os.path.join(
            signed.root, '.purlin', 'evidence', 'package'))
        word, warned = signoff_and_warnings(signed)
        assert word == 'not signed'
        assert warned == [
            'signed/9.9.9: it names a commit that holds no evidence package '
            'for 9.9.9, so it is not a sign-off. Delete it: git tag -d '
            'signed/9.9.9.']

    # purlin: signatures PROOF-253
    def test_a_sign_off_changed_in_an_unsigned_commit_is_no_sign_off(
            self, hand_checked):
        assert walked(hand_checked, ['go on', 'the tube is red', 'y'])[0] == 0
        assert signoff_and_warnings(hand_checked) == (
            'signed 2.1.0 at %s' % hand_checked.head()[:7], [])
        rel = '%s/jane.json' % SIGNOFFS
        body = read_json(hand_checked.root, rel)
        body['notes'][0]['note'] = 'the tube is blue'
        write(os.path.join(hand_checked.root, *rel.split('/')),
              json.dumps(body, indent=2) + '\n')
        commit_all(hand_checked, 'chore: the note edited')
        assert 'gpgsig' not in git(hand_checked.root, 'cat-file', 'commit',
                                   'HEAD').stdout
        word, warned = signoff_and_warnings(hand_checked)
        assert word == 'not signed'
        assert len(warned) == 1, warned
        assert warned[0].startswith(
            'signed/2.1.0: no sign-off of 2.1.0 counts: the commit that added '
            'it is not signed'), warned


    # purlin: signatures PROOF-274
    def test_a_tag_this_checkout_lacks_is_read_from_the_sign_off_files(self):
        made = noted_by_quinn()
        try:
            signed_at = made.head()
            assert git(made.root, 'tag', '-d', 'signed/0.1.0').returncode == 0
            assert git(made.root, 'tag', '--list').stdout == ''
            word, warned = signoff_and_warnings(made)
            assert word == 'signed 0.1.0 at %s' % signed_at[:7]
            assert warned == [
                'signed/0.1.0 is not in this checkout: the sign-off of 0.1.0 '
                'at %s is read from its files. Run git fetch --tags, or '
                'purlin:sign if no one wrote the tag.' % signed_at[:7]]
        finally:
            made.close()

    # purlin: signatures PROOF-275
    def test_with_no_tag_a_sign_off_that_does_not_count_is_not_signed(self):
        made = noted_by_quinn()
        try:
            git(made.root, 'tag', '-d', 'signed/0.1.0')
            assert signoff_and_warnings(made)[0].startswith('signed 0.1.0 at ')
            rel = '.purlin/evidence/package/0.1.0.signoffs/quinn-qa.json'
            body = read_json(made.root, rel)
            body['notes'][0]['note'] = 'the tube is blue'
            write(os.path.join(made.root, *rel.split('/')),
                  json.dumps(body, indent=2) + '\n')
            commit_all(made, 'chore: the note edited')
            assert 'gpgsig' not in git(made.root, 'cat-file', 'commit',
                                       'HEAD').stdout
            assert signoff_and_warnings(made)[0] == 'not signed'
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The refusals
# ---------------------------------------------------------------------------

AUDIT_SPEC = (
    '# Feature: audit\n\n'
    '> Description: The audit log.\n'
    '> Scope: src/audit.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Every sign-in writes one audit line\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): Sign in once; verify one line in the audit log '
    '@env(windows)\n')

AUDIT_TEST = (
    '# purlin: audit PROOF-1\n'
    'def test_one_line_per_sign_in():\n'
    '    assert True\n')


# `login RULE-2`'s one proof, tagged for Windows and tagged slow.
WINDOWS_SPEC = SPEC.replace('verify 401 and the body "denied"\n',
                            'verify 401 and the body "denied" @env(windows)\n')
SLOW_SPEC = SPEC.replace('verify 401 and the body "denied"\n',
                         'verify 401 and the body "denied" @slow\n')
# Two lines numbered `RULE-2`.
TWICE_SPEC = SPEC.replace(
    '\n\n## Proof', '\n- RULE-2: A locked account returns 423\n\n## Proof')


def second_proof_not_run(spec):
    """`login` under `spec`, its results committed at HEAD: `PROOF-1` passes
    and the test of `PROOF-2` was left out of the run."""
    made = Project(spec=spec)
    write(os.path.join(made.root, 'VERSION'), VERSION + '\n')
    commit_all(made, 'chore: version')
    section(made, [('PROOF-1', 'RULE-1', 'pass', TEST_NAMES['PROOF-1'], None),
                   ('PROOF-2', 'RULE-2', 'not run', TEST_NAMES['PROOF-2'],
                    None)],
            {'RULE-1': 'passed', 'RULE-2': 'not run'})
    commit_all(made)
    key(made.root)
    return made


class TestTheRefusals:

    # purlin: signatures PROOF-256
    def test_a_rule_with_no_result_on_its_system_is_named(self, capsys):
        made = second_proof_not_run(WINDOWS_SPEC)
        try:
            assert run_main(made, capsys) == (1, [
                'No sign-off: 1 rule does not pass at %s: login RULE-2. Run '
                'purlin:status to see what is left, then purlin:sign.'
                % made.head()[:7]])
        finally:
            made.close()

    # purlin: signatures PROOF-257
    def test_a_slow_proof_not_run_is_named(self, capsys):
        made = second_proof_not_run(SLOW_SPEC)
        try:
            assert run_main(made, capsys) == (1, [
                'No sign-off: 1 rule does not pass at %s: login RULE-2. Run '
                'purlin:status to see what is left, then purlin:sign.'
                % made.head()[:7]])
        finally:
            made.close()

    # purlin: signatures PROOF-258
    def test_a_spec_that_holds_a_number_twice_is_refused_in_one_whole_line(
            self, capsys):
        made = ready(spec=TWICE_SPEC)
        try:
            code, lines = run_main(made, capsys)
            # The whole line: every rule of the spec, the feature's name once
            # and its rule numbers after it, each number written once.
            assert lines == [
                'No sign-off: 2 rules do not pass at %s: login RULE-1, '
                'RULE-2. Run purlin:status to see what is left, then '
                'purlin:sign.' % made.head()[:7]], lines
            assert (code, status(made.root)) == (1, '')
        finally:
            made.close()

    # purlin: signatures PROOF-261
    def test_the_settings_file_changed_and_not_committed_is_refused(
            self, signed, capsys):
        signed.config(version='0.0.1')
        assert status(signed.root) == ' M .purlin/config.json\n'
        assert run_main(signed, capsys) == (1, [
            'No sign-off: 1 file is changed and not committed. Commit it or '
            'set it aside, then run purlin:sign again.'])

    # purlin: signatures PROOF-265
    def test_a_settings_file_that_cannot_be_read_stops_the_command(
            self, signed, capsys):
        write(os.path.join(signed.root, '.purlin', 'config.json'),
              '{"version": "0.10.0",')
        assert run_main(signed, capsys) == (1, [
            '.purlin/config.json cannot be read: Expecting property name '
            'enclosed in double quotes at line 1. Fix the file by hand; '
            'nothing ran and nothing was saved.'])

    # purlin: signatures PROOF-206
    def test_a_rule_that_fails_is_named(self, capsys):
        made = ready(failing=('RULE-2',))
        try:
            assert run_main(made, capsys) == (1, [
                'No sign-off: 1 rule does not pass at %s: login RULE-2. Run '
                'purlin:status to see what is left, then purlin:sign.'
                % made.head()[:7]])
        finally:
            made.close()

    # purlin: signatures PROOF-223
    def test_results_written_and_not_committed_are_refused(self, signed,
                                                          capsys):
        passing(signed, at='2026-10-01T13:00:00Z')
        assert run_main(signed, capsys) == (1, [
            'No sign-off: the evidence is written and not committed. Run '
            'purlin:test --commit, then purlin:sign.'])

    # purlin: signatures PROOF-244
    def test_one_tracked_file_changed_and_not_committed_is_refused(
            self, signed, capsys):
        write(os.path.join(signed.root, 'src', 'login.py'),
              'def login(user, password):\n    return 401\n')
        assert run_main(signed, capsys) == (1, [
            'No sign-off: 1 file is changed and not committed. Commit it or '
            'set it aside, then run purlin:sign again.'])

    # purlin: signatures PROOF-245
    def test_two_tracked_files_changed_and_not_committed_are_counted(
            self, signed, capsys):
        write(os.path.join(signed.root, 'src', 'login.py'),
              'def login(user, password):\n    return 401\n')
        write(os.path.join(signed.root, 'tests', 'test_login.py'),
              TEST_FILE + '\n# a line not committed\n')
        assert run_main(signed, capsys) == (1, [
            'No sign-off: 2 files are changed and not committed. Commit them '
            'or set them aside, then run purlin:sign again.'])

    # purlin: signatures PROOF-246
    def test_results_taken_over_files_not_committed_are_refused(self, capsys):
        made = ready()
        try:
            rel = '.purlin/evidence/local/login.json'
            data = read_json(made.root, rel)
            assert data['platforms']['linux']['commit'] == git(
                made.root, 'rev-parse', 'HEAD~1').stdout.strip()
            data['platforms']['linux']['dirty'] = True
            write(os.path.join(made.root, *rel.split('/')),
                  json.dumps(data, indent=2, sort_keys=True))
            commit_all(made)
            assert run_main(made, capsys) == (1, [
                'No sign-off: these results were taken while files were '
                'changed and not committed: login on Linux/Unix. Run '
                'purlin:test --all --commit, then purlin:sign.'])
        finally:
            made.close()

    # purlin: signatures PROOF-248
    def test_a_file_git_does_not_track_stops_nothing(self, signed, capsys):
        write(os.path.join(signed.root, 'notes.txt'), 'not tracked\n')
        assert status(signed.root) == '?? notes.txt\n'
        code, lines = run_main(signed, capsys, ['--show'])
        assert code == 0, lines
        assert not [line for line in lines
                    if line.startswith('No sign-off')], lines

    # purlin: signatures PROOF-247
    def test_a_rule_with_no_proof_and_no_test_is_named_with_purlin_build(
            self, capsys):
        made = ready(spec=SPEC.replace(
            '\n\n## Proof',
            '\n- RULE-3: A locked account returns 423\n\n## Proof'))
        try:
            third = made.rule('RULE-3')
            assert (third['proofs'], third['tests']) == ([], [])
            assert run_main(made, capsys) == (1, [
                'No sign-off: 1 rule has no test at %s: login RULE-3. Run '
                'purlin:build login, then purlin:sign.' % made.head()[:7]])
        finally:
            made.close()

    # purlin: signatures PROOF-226
    def test_results_taken_before_a_code_change_are_named(self, capsys):
        made = ready()
        try:
            made.spec(AUDIT_SPEC, name='audit', category='review')
            write(os.path.join(made.root, 'src', 'audit.py'), 'LINES = 1\n')
            write(os.path.join(made.root, 'tests', 'test_audit.py'), AUDIT_TEST)
            commit_all(made, 'feat(audit): the log')
            section(made, [('PROOF-1', 'RULE-1', 'pass',
                            'test_one_line_per_sign_in', None)],
                    {'RULE-1': 'passed'}, source='ci', os_name='windows',
                    email=RUNNER, machine='build-7', feature='audit')
            commit_all(made, 'purlin: results pulled home')
            write(os.path.join(made.root, 'src', 'audit.py'), 'LINES = 2\n')
            commit_all(made, 'fix(audit): two lines')
            passing(made)
            section(made, [('PROOF-1', 'RULE-1', 'not run',
                            'test_one_line_per_sign_in', None)],
                    {'RULE-1': 'not run'}, feature='audit')
            commit_all(made)
            assert run_main(made, capsys) == (1, [
                'No sign-off: these results are not recorded on this version '
                'of the code, %s: audit on Windows. Run purlin:test on Windows, '
                'then purlin:sign.' % made.head()[:7]])
        finally:
            made.close()

    # purlin: signatures PROOF-207
    def test_a_host_copy_ahead_is_refused(self, signed, tmp_path, capsys):
        host = str(tmp_path / 'host.git')
        git(signed.root, 'init', '-q', '--bare', host)
        git(signed.root, 'remote', 'add', 'origin', host)
        git(signed.root, '-c', 'push.negotiate=false', 'push', '-q',
            'origin', 'main')
        other = str(tmp_path / 'other')
        git(signed.root, 'clone', '-q', '-b', 'main', host, other)
        git(other, 'config', 'user.email', 'omar@example.org')
        git(other, 'config', 'user.name', 'Omar')
        git(other, 'config', 'commit.gpgsign', 'false')
        git(other, 'commit', '-q', '--allow-empty', '-m', 'chore: ahead')
        git(other, '-c', 'push.negotiate=false', 'push', '-q', 'origin', 'main')
        git(signed.root, 'fetch', '-q', 'origin')
        assert run_main(signed, capsys) == (1, [
            'No sign-off: origin/main holds 1 commit that %s does not, as this '
            'checkout last fetched it. Pull, then run purlin:sign.'
            % signed.head()[:7]])

    # purlin: signatures PROOF-224
    def test_a_tag_on_another_branch_is_refused(self, signed, capsys):
        git(signed.root, 'switch', '-q', '-c', 'other')
        git(signed.root, 'commit', '-q', '--allow-empty', '-m', 'chore: other')
        assert walked(signed, ['y'])[0] == 0
        tagged = git(signed.root, 'rev-parse', 'signed/2.1.0^{commit}'
                     ).stdout.strip()
        assert tagged == signed.head()
        git(signed.root, 'switch', '-q', 'main')
        assert run_main(signed, capsys) == (1, [
            'No sign-off: signed/2.1.0 is at %s, which this checkout does not '
            'hold. Pull, then run purlin:sign.' % tagged[:7]])

    # purlin: signatures PROOF-225
    def test_a_code_change_since_the_tag_is_refused(self, signed, capsys):
        assert walked(signed, ['y'])[0] == 0
        tagged = signed.head()
        write(os.path.join(signed.root, 'src', 'login.py'),
              'def login(user, password):\n    return 401\n')
        commit_all(signed, 'fix(login): refuse')
        assert run_main(signed, capsys) == (1, [
            'No sign-off: signed/2.1.0 is at %s, and the code has changed '
            'since. To sign this code, name a new version: purlin:sign '
            '--version <version>.' % tagged[:7]])

    HAND_TAG = ('No sign-off: signed/2.1.0 names a commit that holds no '
                'evidence package for 2.1.0, so purlin:sign did not write it. '
                'Delete it: git tag -d signed/2.1.0%s. Then run purlin:sign '
                'again.')

    # purlin: signatures PROOF-266
    def test_a_tag_typed_by_hand_for_this_version_is_refused(self, signed,
                                                             capsys):
        git(signed.root, 'tag', 'signed/2.1.0')
        assert git(signed.root, 'remote').stdout == '', 'a remote is set'
        assert run_main(signed, capsys) == (1, [self.HAND_TAG % ''])
        assert status(signed.root) == ''
        assert not os.path.exists(os.path.join(
            signed.root, '.purlin', 'evidence', 'package'))

    # purlin: signatures PROOF-267
    def test_the_refusal_names_the_remote_where_there_is_one(
            self, signed, tmp_path, capsys):
        host = str(tmp_path / 'host.git')
        git(signed.root, 'init', '-q', '--bare', host)
        git(signed.root, 'remote', 'add', 'origin', host)
        git(signed.root, 'tag', 'signed/2.1.0')
        assert run_main(signed, capsys) == (1, [self.HAND_TAG % (
            ', and git push origin --delete signed/2.1.0 if it was pushed')])

    # purlin: signatures PROOF-268
    def test_a_tag_that_is_the_sign_off_lets_a_second_signer_sign(self,
                                                                  signed):
        assert walked(signed, ['y'])[0] == 0
        tagged = signed.head()
        code, lines, _asked = sign_as(signed, 'omar@example.org', 'Omar')
        assert code == 0, lines
        assert not [line for line in lines if line.startswith('No sign-off:')]
        folder = os.path.join(signed.root, *SIGNOFFS.split('/'))
        assert sorted(os.listdir(folder)) == ['jane.json', 'omar.json']
        assert git(signed.root, 'rev-parse', 'signed/2.1.0^{commit}'
                   ).stdout.strip() == tagged

    # purlin: signatures PROOF-162
    def test_a_commit_git_refuses_names_gits_own_message(self, signed):
        hook = os.path.join(signed.root, '.git', 'hooks', 'pre-commit')
        with open(hook, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write('#!/bin/sh\n'
                         'echo "error: the hook refused the commit." >&2\n'
                         'exit 1\n')
        os.chmod(hook, 0o755)
        before = signed.head()
        code, lines, _asked = walked(signed, ['y'])
        assert lines[-1] == (
            'The sign-off commit was not made: the hook refused the commit. '
            'Nothing was signed; run purlin:sign again.')
        assert (code, signed.head(), status(signed.root)) == (1, before, '')

    # purlin: signatures PROOF-208
    def test_the_same_signer_again_is_refused(self, signed, capsys):
        assert walked(signed, ['y'])[0] == 0
        assert run_main(signed, capsys) == (1, [
            'jane@acme.com has already signed 2.1.0 over this package; nothing '
            'was written.'])

    # purlin: signatures PROOF-243
    def test_no_version_stated_or_named_is_refused(self, capsys):
        made = ready(version=None)
        try:
            assert run_main(made, capsys) == (1, [
                'No version: nothing in this project states one. Run '
                'purlin:sign --version <version>, or write it to a VERSION '
                'file.'])
            assert status(made.root) == ''
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The markers Purlin 0.9.5 wrote that are still in a test
# ---------------------------------------------------------------------------

OLD_TS = 'tests/login.test.ts'
OLD_TAGS = ('[proof:login:PROOF-1b:RULE-1:unit]',
            '[proof:login:PROOF-2b:RULE-2:unit]',
            '[proof:login:PROOF-2c:RULE-2:unit]')
OLD_REST = (' a marker from Purlin 0.9.5, which is not read. Run purlin:status '
            'to see each, rewrite them, then purlin:sign.')
OLD_ONE = ('No sign-off: 1 test still carries a marker from Purlin 0.9.5, which '
           'is not read. Run purlin:status to see it, rewrite it, then '
           'purlin:sign.')


def old_ts(tags):
    """A vitest file with one test per tag, the tag in the test's title."""
    return "import { it } from 'vitest';\n" + ''.join(
        "it('signs in %d %s', () => {});\n" % (number, tag)
        for number, tag in enumerate(tags, 1))


def carrying(tags, version=VERSION, signer=True):
    """A project whose two rules pass on committed evidence, with a tracked
    vitest file whose tests' titles carry `tags`, committed before the
    results were taken."""
    made = Project()
    write(os.path.join(made.root, *OLD_TS.split('/')), old_ts(tags))
    if version:
        write(os.path.join(made.root, 'VERSION'), version + '\n')
    commit_all(made, 'test: the vitest tests')
    passing(made)
    commit_all(made)
    if signer:
        key(made.root)
    return made


class TestMarkersFrom095:

    # purlin: signatures PROOF-276
    def test_one_test_that_carries_one_is_refused(self, capsys):
        made = carrying(OLD_TAGS[:1])
        try:
            assert run_main(made, capsys) == (1, [OLD_ONE])
            assert status(made.root) == ''
        finally:
            made.close()

    # purlin: signatures PROOF-277
    def test_the_same_project_with_the_tag_taken_out_is_shown(self, capsys):
        made = carrying(('',))
        try:
            code, lines = run_main(made, capsys, ['--show'])
            assert code == 0, lines
            assert not [line for line in lines
                        if line.startswith('No sign-off')], lines
            assert lines[-1] == ('Answer each stop, then run purlin:sign '
                                 '--answers <file>.')
        finally:
            made.close()

    # purlin: signatures PROOF-278
    def test_three_are_counted_before_a_version_or_a_key_is_asked_for(
            self, home):
        made = carrying(OLD_TAGS, version=None, signer=False)
        try:
            before = made.head()
            code, lines, asked = walked(made, ['y'])
            assert lines == ['No sign-off: 3 tests still carry' + OLD_REST]
            assert (code, asked) == (1, [])
            assert (made.head(), status(made.root)) == (before, '')
        finally:
            made.close()

    # purlin: signatures PROOF-279
    def test_show_prints_the_same_line_and_exits_1(self, capsys):
        made = carrying(OLD_TAGS[:2])
        try:
            assert run_main(made, capsys, ['--show']) == (1, [
                'No sign-off: 2 tests still carry' + OLD_REST])
            assert status(made.root) == ''
        finally:
            made.close()

    # purlin: signatures PROOF-280
    def test_check_still_checks_a_package(self, signed, capsys):
        assert walked(signed, ['y'])[0] == 0
        write(os.path.join(signed.root, *OLD_TS.split('/')),
              old_ts(OLD_TAGS[:1]))
        commit_all(signed, 'test: a vitest test')
        capsys.readouterr()
        assert run_main(signed, capsys, ['--show']) == (1, [OLD_ONE])
        code = sign_module.main(['--check', os.path.join(
            signed.root, *PACKAGE.split('/'))])
        assert (code, capsys.readouterr().out.splitlines()) == (
            0, ['The package matches its fingerprint.'])


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

def nineteen_rules():
    """A spec of 19 rules: 18 with one test each, the 19th checked by hand."""
    rules = ['- RULE-%d: Sample %d is accepted' % (n, n) for n in range(1, 20)]
    proofs = ['- PROOF-%d (RULE-%d): Send sample %d; verify it is accepted%s'
              % (n, n, n, ' @manual' if n == 19 else '') for n in range(1, 20)]
    spec = ('# Feature: login\n\n> Description: Samples.\n'
            '> Scope: src/login.py\n\n## Rules\n\n%s\n\n## Proof\n\n%s\n'
            % ('\n'.join(rules), '\n'.join(proofs)))
    tests = ''.join('\n\n# purlin: login PROOF-%d\ndef test_sample_%d():\n'
                    '    assert True\n' % (n, n) for n in range(1, 19))
    return spec, tests.lstrip('\n')


@pytest.fixture(scope='module')
def nineteen():
    """Dana ran 19 rules' tests on dana-laptop, a Linux machine, at 12:17 UTC
    on 2026-10-01; 17 rules are audited strong and 1 weak, and the 19th is
    checked by hand alone."""
    spec, tests = nineteen_rules()
    made = Project(spec=spec)
    made.edit_test(tests)
    write(os.path.join(made.root, 'VERSION'), '0.1.0\n')
    commit_all(made, 'chore: version')
    made.tests_ran_at = made.head()
    section(made, [('PROOF-%d' % n, 'RULE-%d' % n, 'pass', 'test_sample_%d' % n,
                    None) for n in range(1, 19)],
            {'RULE-%d' % n: 'passed' for n in range(1, 20)})
    for n in range(1, 18):
        made.audit('RULE-%d' % n)
    made.audit('RULE-18', findings=['PROOF-18 reads the status alone.'])
    commit_all(made)
    key(made.root, email=DANA, name='Dana')
    yield made
    made.close()


def hand_check_with_a_test(tag=''):
    """`login RULE-2` has `PROOF-2` marked `@manual` and `PROOF-3`, tied to
    `test_lockout_page` and carrying `tag`; `VERSION` is committed."""
    spec = SPEC.replace(
        'verify 401 and the body "denied"\n',
        'verify 401 and the body "denied" @manual\n'
        '- PROOF-3 (RULE-2): After three bad passwords; verify the lockout '
        'page%s\n' % tag)
    made = Project(spec=spec)
    made.edit_test(MANUAL_TEST_FILE + ('\n\n# purlin: login PROOF-3\n'
                                       'def test_lockout_page():\n'
                                       '    assert True\n'))
    write(os.path.join(made.root, 'VERSION'), VERSION + '\n')
    commit_all(made, 'chore: version')
    return made


class TestTheWalk:

    # purlin: signatures PROOF-227
    def test_it_opens_on_who_ran_the_tests_where_and_when(self, nineteen):
        lines = walked(nineteen, [])[1]
        assert lines[0] == (
            'Tests run by dana.dev@labconnect.example on dana-laptop at '
            '2026-10-01 12:17 UTC on %s: 19 rules on Linux/Unix.'
            % nineteen.tests_ran_at[:7])

    # purlin: signatures PROOF-209
    def test_signing_follows_the_last_run_line(self, nineteen):
        lines = walked(nineteen, [])[1]
        last_run = max(i for i, line in enumerate(lines)
                       if line.startswith('Tests run by '))
        assert lines[last_run + 1] == 'Signing 0.1.0 at %s.' % \
            nineteen.head()[:7]

    # purlin: signatures PROOF-232
    def test_the_overview_counts_per_system_and_the_audit(self, nineteen):
        lines = walked(nineteen, [])[1]
        assert lines[2:4] == [
            '  19 rules on Linux/Unix: 18 pass their tests, 1 has a hand check.',
            '  The audit: 17 strong, 1 weak.']

    # purlin: signatures PROOF-229
    def test_a_weak_rule_and_one_never_audited_add_no_stop(self):
        made = ready(weak=('RULE-1',))
        try:
            code, lines, asked = walked(made, ['go on', ''])
            assert asked == [
                "The audit's findings: 1 weak. list / go on: ",
                'Sign the evidence package for 2.1.0 as jane@acme.com? [y/N] ']
            assert (code, lines[-1]) == (0, 'Nothing was signed.')
        finally:
            made.close()

    # purlin: signatures PROOF-230
    def test_list_prints_each_weak_rule_with_its_finding(self):
        made = ready(weak=('RULE-1',))
        try:
            finding = '  login RULE-1   PROOF-1 reads the status alone.'
            left, asked, out = ['list'], [], _Out()

            printed = []

            def ask(_kind, _key, prompt):
                # Each question with whether the finding was printed by then.
                asked.append((prompt, finding in out.text().splitlines()))
                printed.append(len(out.text().splitlines()))
                return left.pop(0) if left else None

            sign_module.walk(made.root, None, ask=ask, out=out)
            assert asked[:2] == [
                ("The audit's findings: 1 weak. list / go on: ", False),
                ('go on: ', True)], asked
            # Between the two questions `list` prints that line, once, and
            # nothing else.
            assert out.text().splitlines()[printed[0]:printed[1]] == [
                finding], out.text()
        finally:
            made.close()

    # purlin: signatures PROOF-211
    def test_a_hand_check_stops_under_its_head_and_asks(self, hand_checked):
        code, lines, asked = walked(hand_checked, ['go on'])
        assert [line for line in lines if line.startswith('login RULE-')] == [
            'login RULE-2   hand check']
        assert asked[1] == ('login RULE-2   what did you see, in one line, or '
                            'Enter for no note, or stop: ')

    # purlin: signatures PROOF-200
    def test_a_stop_names_the_test_under_its_proof(self):
        spec = SPEC.replace(
            'verify 401 and the body "denied"\n',
            'verify 401 and the body "denied" @manual\n'
            '- PROOF-3 (RULE-2): After three bad passwords; verify the lockout '
            'page\n')
        tests = MANUAL_TEST_FILE + ('\n\n# purlin: login PROOF-3\n'
                                    'def test_lockout_page():\n'
                                    '    assert True\n')
        made = Project(spec=spec)
        try:
            made.edit_test(tests)
            write(os.path.join(made.root, 'VERSION'), VERSION + '\n')
            commit_all(made, 'chore: version')
            section(made, [('PROOF-1', 'RULE-1', 'pass',
                            TEST_NAMES['PROOF-1'], None),
                           ('PROOF-3', 'RULE-2', 'pass', 'test_lockout_page',
                            None)],
                    {'RULE-1': 'passed', 'RULE-2': 'passed'})
            commit_all(made)
            key(made.root)
            stop = stop_lines(walked(made, [])[1], 'login RULE-2   hand check')
            proof = next(i for i, line in enumerate(stop)
                         if line.startswith('  PROOF-3'))
            assert stop[proof + 1] == ('    tied to tests/test_login.py::'
                                       'test_lockout_page')
        finally:
            made.close()

    # purlin: signatures PROOF-262
    def test_a_weak_hand_check_shows_the_audits_finding_at_its_stop(self):
        made = hand_check_with_a_test()
        try:
            section(made, [('PROOF-1', 'RULE-1', 'pass',
                            TEST_NAMES['PROOF-1'], None),
                           ('PROOF-3', 'RULE-2', 'pass', 'test_lockout_page',
                            None)],
                    {'RULE-1': 'passed', 'RULE-2': 'passed'})
            made.audit('RULE-2', findings=['PROOF-3 reads the status alone.'])
            commit_all(made)
            key(made.root)
            code, lines, asked = walked(made, ['go on'])
            stop = stop_lines(lines, 'login RULE-2   hand check')
            found = stop.index('What the audit found')
            assert stop[found + 1] == '  PROOF-3 reads the status alone.'
            assert asked[-1].startswith('login RULE-2   what did you see')
        finally:
            made.close()

    # purlin: signatures PROOF-263
    def test_a_stop_names_each_system_and_the_machine_it_ran_on(self):
        made = hand_check_with_a_test(tag=' @env(windows)')
        try:
            section(made, [('PROOF-1', 'RULE-1', 'pass',
                            TEST_NAMES['PROOF-1'], None)],
                    {'RULE-1': 'passed', 'RULE-2': 'passed'})
            section(made, [('PROOF-3', 'RULE-2', 'pass', 'test_lockout_page',
                            None)], {'RULE-2': 'passed'}, source='ci',
                    os_name='windows', email=RUNNER, machine='build-7')
            commit_all(made)
            key(made.root)
            stop = stop_lines(walked(made, [])[1], 'login RULE-2   hand check')
            results = stop.index('Results')
            assert stop[results + 1:results + 3] == [
                '  Linux/Unix: passed on dana-laptop',
                '  Windows: passed on build-7']
        finally:
            made.close()

    @staticmethod
    def _carried(made):
        """`made`, a hand check with a test, its results taken by Pat on
        `pat-laptop` at one commit and carried into sections Dana's run
        recorded on the next. The commit they were taken at."""
        ran_at = made.head()
        write(os.path.join(made.root, 'README.md'), '# Login\n')
        commit_all(made, 'docs: a readme')
        taken = {'commit': ran_at, 'at': '2026-09-30T08:05:00Z',
                 'machine': 'pat-laptop',
                 'email': 'pat.product@labconnect.example'}
        section(made, [('PROOF-1', 'RULE-1', 'pass', TEST_NAMES['PROOF-1'],
                        None),
                       ('PROOF-3', 'RULE-2', 'pass', 'test_lockout_page',
                        None)],
                {'RULE-1': 'passed', 'RULE-2': 'passed'}, carried=taken)
        commit_all(made)
        key(made.root)
        return ran_at

    # purlin: signatures PROOF-290
    def test_carried_results_open_on_the_runs_that_took_them(self):
        made = hand_check_with_a_test()
        try:
            ran_at = self._carried(made)
            code, lines, _asked = walked(made, [])
            assert lines[0] == (
                'Carried forward from earlier runs by '
                'pat.product@labconnect.example on pat-laptop, the newest at '
                '2026-09-30 08:05 UTC on %s: 2 rules on Linux/Unix.'
                % ran_at[:7]), lines
            assert lines[1] == 'Signing %s at %s.' % (
                VERSION, git(made.root, 'rev-parse',
                             'HEAD').stdout.strip()[:7]), lines
        finally:
            made.close()

    # purlin: signatures PROOF-291
    def test_a_stop_names_the_commit_a_result_was_carried_from(self):
        made = hand_check_with_a_test()
        try:
            ran_at = self._carried(made)
            stop = stop_lines(walked(made, [])[1], 'login RULE-2   hand check')
            assert stop[stop.index('Results') + 1] == (
                '  Linux/Unix: passed on dana-laptop; PROOF-3 carried forward '
                'from %s' % ran_at[:7]), stop
        finally:
            made.close()

    # purlin: signatures PROOF-242
    def test_a_proof_with_nothing_to_check_shows_its_reason(self):
        made = Project(spec=SPEC)
        try:
            write(os.path.join(made.root, 'specs', '_anchors', 'screens.md'),
                  '# Anchor: screens\n\n'
                  '> Description: Every screen.\n\n'
                  '## Rules\n\n'
                  '- RULE-1: For every screen in the project, its colours '
                  'pass contrast\n\n'
                  '## Proof\n\n'
                  '- PROOF-2 (RULE-1): Look at each screen; verify the '
                  'contrast @manual\n'
                  '- PROOF-3 (RULE-1): For every screen, verify a contrast of '
                  '7 to 1\n')
            write(os.path.join(made.root, 'tests', 'test_screens.py'),
                  '# purlin: screens PROOF-3\n'
                  'def test_contrast():\n'
                  '    assert True\n')
            write(os.path.join(made.root, 'VERSION'), VERSION + '\n')
            commit_all(made, 'spec(screens): the anchor')
            passing(made)
            section(made, [('PROOF-3', 'RULE-1', 'nothing to check',
                            'test_contrast', 'this project has no screens')],
                    {'RULE-1': 'passed'}, feature='screens')
            commit_all(made)
            key(made.root)
            stop = stop_lines(walked(made, [])[1], 'screens RULE-1   hand check')
            assert ('  Linux/Unix: passed on dana-laptop; nothing to check for '
                    'PROOF-3: this project has no screens') in stop
        finally:
            made.close()

    # purlin: signatures PROOF-218
    def test_stop_at_a_hand_check_writes_nothing(self, hand_checked):
        before = hand_checked.head()
        code, lines, _asked = walked(hand_checked, ['go on', 'stop'])
        assert lines[-1] == (
            'Stopped at login RULE-2: nothing was signed. After the fix, run '
            'purlin:test --all --commit, then purlin:sign.')
        assert (code, hand_checked.head(), status(hand_checked.root)) == (
            0, before, '')

    # purlin: signatures PROOF-219
    def test_an_empty_line_at_every_question_signs_nothing(self, hand_checked):
        before = hand_checked.head()
        code, lines, asked = walked(hand_checked, ['', '', ''])
        assert asked[-1] == ('Sign the evidence package for 2.1.0 as '
                             'jane@acme.com? [y/N] ')
        assert lines[-1] == 'Nothing was signed.'
        assert (code, hand_checked.head(), status(hand_checked.root)) == (
            0, before, '')


# ---------------------------------------------------------------------------
# A proof settled with its test unchanged
# ---------------------------------------------------------------------------

# The sentence the audit stores under `no_bug` for a proof settled under
# `--sound`, its test left as it was.
JUDGED = ('%s was settled with its test unchanged: it was judged to assert '
          'what the proof names.')
JUDGED_ASK = "The audit's findings: %s. list / go on: "
SIGN_QUESTION = 'Sign the evidence package for 2.1.0 as jane@acme.com? [y/N] '


def judged(settled=('RULE-1',), weak=(), strong=()):
    """`login` passing, each rule `settled` names reading `strong` with its
    one proof settled with its test unchanged; `weak` and `strong` as `ready`
    has them. Jane is ready to sign."""
    made = Project(spec=SPEC)
    write(os.path.join(made.root, 'VERSION'), VERSION + '\n')
    commit_all(made, 'chore: version')
    passing(made)
    for rule in strong:
        made.audit(rule)
    for rule in weak:
        made.audit(rule, findings=[FINDING.replace('PROOF-1', 'PROOF-%s'
                                                   % rule[-1])])
    for rule in settled:
        made.audit(rule, no_bug=[JUDGED % ('PROOF-%s' % rule[-1])])
    commit_all(made)
    key(made.root)
    return made


def between_questions(made, answers):
    """Walk with `answers`; `(exit, questions, lines printed between the
    first two questions, every line)`."""
    left, asked, marks, out = list(answers), [], [], _Out()

    def ask(_kind, _key, prompt):
        asked.append(prompt)
        marks.append(len(out.text().splitlines()))
        return left.pop(0) if left else None

    code = sign_module.walk(made.root, None, ask=ask, out=out)
    lines = out.text().splitlines()
    shown = lines[marks[0]:marks[1]] if len(marks) > 1 else []
    return code, asked, shown, lines


class TestSettledByJudgment:

    # purlin: signatures PROOF-281
    def test_one_settled_proof_and_no_weak_rule_asks_the_question(self):
        made = judged()
        try:
            asked = walked(made, ['go on', ''])[2]
            assert asked == [
                JUDGED_ASK % '1 proof settled with its test unchanged',
                SIGN_QUESTION]
        finally:
            made.close()

    # purlin: signatures PROOF-282
    def test_two_settled_proofs_are_counted_together(self):
        made = judged(settled=('RULE-1', 'RULE-2'))
        try:
            asked = walked(made, ['go on', ''])[2]
            assert asked[0] == JUDGED_ASK % (
                '2 proofs settled with their tests unchanged')
        finally:
            made.close()

    # purlin: signatures PROOF-283
    def test_a_weak_rule_and_a_settled_proof_are_counted_in_that_order(self):
        made = judged(settled=('RULE-2',), weak=('RULE-1',))
        try:
            asked = walked(made, ['go on', ''])[2]
            assert asked[0] == JUDGED_ASK % (
                '1 weak, 1 proof settled with its test unchanged')
        finally:
            made.close()

    # purlin: signatures PROOF-284
    def test_list_prints_the_settled_proof_on_its_own_line(self):
        made = judged()
        try:
            code, asked, shown, _lines = between_questions(made, ['list'])
            assert asked[1] == 'go on: '
            assert shown == ['  login RULE-1: %s' % (JUDGED % 'PROOF-1')]
        finally:
            made.close()

    # purlin: signatures PROOF-285
    def test_the_settled_line_follows_every_weak_finding(self):
        made = judged(settled=('RULE-2',), weak=('RULE-1',))
        try:
            shown = between_questions(made, ['list'])[2]
            assert shown == ['  login RULE-1   PROOF-1 reads the status alone.',
                             '  login RULE-2: %s' % (JUDGED % 'PROOF-2')]
        finally:
            made.close()

    # purlin: signatures PROOF-286
    def test_a_settled_proof_adds_no_stop_and_refuses_nothing(self):
        made = judged()
        try:
            before = made.head()
            code, asked, _shown, lines = between_questions(
                made, ['list', 'go on', 'y'])
            assert asked == [JUDGED_ASK % '1 proof settled with its test unchanged',
                             'go on: ', SIGN_QUESTION]
            assert code == 0
            assert lines[-2] == 'Tagged signed/2.1.0 at %s.' % made.head()[:7]
            assert git(made.root, 'log', '-1', '--format=%s').stdout.strip() \
                == 'sign(2.1.0): jane@acme.com'
            assert made.head() != before
            assert git(made.root, 'rev-parse',
                       'signed/2.1.0^{commit}').stdout.strip() == made.head()
        finally:
            made.close()

    # purlin: signatures PROOF-287
    def test_another_no_bug_sentence_is_not_listed(self):
        made = judged(settled=())
        try:
            made.audit('RULE-1', word='spot-checked', no_bug=[
                'No bug was planted: the model could not be reached: claude '
                'exited with an error.'])
            commit_all(made)
            code, lines, asked = walked(made, [''])
            assert asked == [SIGN_QUESTION]
            assert not [line for line in lines if 'was settled' in line]
        finally:
            made.close()

    # purlin: signatures PROOF-288
    def test_show_prints_the_settled_line_under_the_findings(self, capsys):
        made = judged()
        try:
            code, lines = run_main(made, capsys, ['--show'])
            at = lines.index("The audit's findings: 1 proof settled with its "
                             "test unchanged.")
            assert lines[at + 1] == '  login RULE-1: %s' % (JUDGED % 'PROOF-1')
            assert code == 0
        finally:
            made.close()

    # purlin: signatures PROOF-289
    def test_the_sign_off_records_the_list_opened_and_the_package_the_line(
            self):
        made = judged()
        try:
            assert walked(made, ['list', 'go on', 'y'])[0] == 0
            assert signed_off(made)['shown']['audit_list_opened'] is True
            package = read_json(made.root, PACKAGE)
            login = next(f for f in package['features'] if f['name'] == 'login')
            rule = next(r for r in login['rules'] if r['id'] == 'RULE-1')
            assert rule['statuses']['strong']['word'] == 'strong'
            assert rule['audit']['no_bug'] == [JUDGED % 'PROOF-1']
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The sign-off, its commit and the tag
# ---------------------------------------------------------------------------

def sign_as(made, email, name, answers=('y',), file=None):
    key(made.root, email=email, name=name, file=file or email.split('@')[0])
    return walked(made, list(answers))


class TestTheSignOff:

    # purlin: signatures PROOF-214
    def test_it_records_what_was_shown_and_the_note(self, hand_checked):
        assert walked(hand_checked, ['go on', 'the lockout page read 401',
                                     'y'])[0] == 0
        body = signed_off(hand_checked)
        package = read_json(hand_checked.root, PACKAGE)
        assert body['package_hash'] == package['fingerprint']
        assert {'feature': 'login', 'rule': 'RULE-2'} in \
            body['shown']['hand_checks']
        assert body['shown']['audit_list_opened'] is False
        assert body['notes'] == [{'feature': 'login', 'rule': 'RULE-2',
                                  'note': 'the lockout page read 401'}]
        # What was shown is these four and nothing beside them.
        assert sorted(body['shown']) == ['audit_list_opened', 'hand_checks',
                                         'overview', 'runs'], body['shown']
        def values(item):
            if isinstance(item, dict):
                return [found for value in item.values()
                        for found in values(value)]
            if isinstance(item, list):
                return [found for value in item for found in values(value)]
            return [item]

        def keys(item):
            if isinstance(item, dict):
                return list(item) + [found for value in item.values()
                                     for found in keys(value)]
            if isinstance(item, list):
                return [found for value in item for found in keys(value)]
            return []

        # No value anywhere in the file is an answer word, in either case,
        # and no key is one either.
        assert not [word for word in values(body) + keys(body)
                    if str(word).strip().lower()
                    in ('go on', 'list', 'y', 'yes', 'stop')], body

    # purlin: signatures PROOF-235
    def test_an_empty_answer_is_recorded_as_no_note(self, hand_checked):
        assert walked(hand_checked, ['go on', '', 'y'])[0] == 0
        assert signed_off(hand_checked)['notes'] == [
            {'feature': 'login', 'rule': 'RULE-2', 'note': 'no note'}]

    # purlin: signatures PROOF-75
    def test_it_records_the_signer_as_git_holds_them_and_the_key(self):
        made = ready(signer=False)
        try:
            public = key(made.root, email='Jane.Doe@Acme.com', name='Jane Doe')
            assert walked(made, ['y'])[0] == 0
            body = signed_off(made, 'Jane.Doe@Acme.com')
            assert (body['signer'], body['signer_name'],
                    body['key_fingerprint']) == (
                'Jane.Doe@Acme.com', 'Jane Doe', fingerprint_of(public))
        finally:
            made.close()

    # purlin: signatures PROOF-178
    def test_the_tag_carries_the_signers_ssh_signature(self, signed, tmp_path):
        assert walked(signed, ['y'])[0] == 0
        public = git(signed.root, 'config', 'user.signingkey').stdout.strip()
        with open(public, encoding='utf-8') as handle:
            allowed = '%s %s' % (EMAIL, handle.read().strip())
        allowed_file = tmp_path / 'allowed'
        allowed_file.write_text(allowed + '\n', encoding='utf-8')
        checked = git(signed.root, '-c',
                      'gpg.ssh.allowedSignersFile=%s' % allowed_file,
                      'tag', '-v', 'signed/2.1.0')
        said = checked.stdout + checked.stderr
        assert checked.returncode == 0, said
        assert 'Good "git" signature' in said, said
        assert fingerprint_of(public) in said, said

    # purlin: signatures PROOF-236
    def test_the_first_sign_off_is_one_commit_with_the_package_and_the_tag(
            self):
        made = ready(version='0.1.0', signer=False)
        try:
            before = made.head()
            code, lines, _asked = sign_as(made, 'quinn.qa@labconnect.example',
                                          'Quinn')
            head = made.head()
            assert code == 0
            # One commit, and no other, since the walk began.
            assert git(made.root, 'rev-list', '--count',
                       '%s..HEAD' % before).stdout.strip() == '1'
            assert git(made.root, 'log', '-1', '--format=%s').stdout.strip() \
                == 'sign(0.1.0): quinn.qa@labconnect.example'
            assert '-----BEGIN SSH SIGNATURE-----' in git(
                made.root, 'cat-file', 'commit', 'HEAD').stdout
            assert sorted(changed_in_head(made.root)) == [
                '.purlin/evidence/package/0.1.0.json',
                '.purlin/evidence/package/0.1.0.signoffs/quinn-qa.json']
            assert git(made.root, 'rev-parse',
                       'signed/0.1.0^{commit}').stdout.strip() == head
            assert 'Tagged signed/0.1.0 at %s.' % head[:7] in lines
        finally:
            made.close()

    # purlin: signatures PROOF-237
    def test_a_later_sign_off_adds_its_own_file_alone(self):
        made = ready(version='0.1.0', signer=False)
        try:
            assert sign_as(made, 'quinn.qa@labconnect.example', 'Quinn')[0] == 0
            quinns = made.head()
            assert sign_as(made, 'pat.product@labconnect.example',
                           'Pat')[0] == 0
            assert changed_in_head(made.root) == [
                '.purlin/evidence/package/0.1.0.signoffs/pat-product.json']
            assert git(made.root, 'rev-parse',
                       'signed/0.1.0^{commit}').stdout.strip() == quinns
        finally:
            made.close()

    # purlin: signatures PROOF-233
    def test_the_first_sign_off_ends_on_pushing_the_branch_and_the_tag(self):
        made = ready(version='0.1.0')
        try:
            code, lines, _asked = walked(made, ['y'])
            assert (code, lines[-1]) == (
                0, 'Push the branch and the tag: git push origin main '
                   'signed/0.1.0')
        finally:
            made.close()

    # purlin: signatures PROOF-234
    def test_a_second_signer_ends_on_the_tag_staying(self):
        made = ready(version='0.1.0')
        try:
            assert walked(made, ['y'])[0] == 0
            tagged = made.head()
            code, lines, _asked = sign_as(made, 'pat@acme.com', 'Pat')
            assert (code, lines[-1]) == (
                0, 'signed/0.1.0 stays at %s; this sign-off is added after it. '
                   'Push it: git push origin main' % tagged[:7])
        finally:
            made.close()

    # purlin: signatures PROOF-238
    def test_it_tags_the_sign_off_commit_and_fetches_and_pushes_nothing(
            self, signed, tmp_path):
        host = str(tmp_path / 'host.git')
        git(signed.root, 'init', '-q', '--bare', host)
        git(signed.root, 'remote', 'add', 'origin', host)
        git(signed.root, '-c', 'push.negotiate=false', 'push', '-q',
            'origin', 'main')
        hosted = git(host, 'rev-parse', 'main').stdout.strip()
        git(signed.root, 'fetch', '-q', 'origin')
        os.remove(os.path.join(signed.root, '.git', 'FETCH_HEAD'))
        write(os.path.join(signed.root, 'NOTES'), 'a note\n')
        commit_all(signed, 'docs: a note the host lacks')
        passing(signed)
        commit_all(signed)
        assert walked(signed, ['y'])[0] == 0
        # The tag itself: a branch of that name would answer to the short
        # name too.
        assert git(signed.root, 'tag', '--list').stdout.splitlines() == [
            'signed/2.1.0']
        assert git(signed.root, 'rev-parse', '--verify', '--quiet',
                   'refs/tags/signed/2.1.0^{commit}').stdout.strip() == \
            signed.head()
        assert git(host, 'tag', '--list').stdout == ''
        assert git(host, 'rev-parse', 'main').stdout.strip() == hosted
        assert not os.path.exists(os.path.join(signed.root, '.git',
                                               'FETCH_HEAD'))


    # purlin: signatures PROOF-255
    def test_a_tag_git_could_not_write_is_written_by_the_next_run(
            self, signed):
        in_the_way = os.path.join(signed.root, '.git', 'refs', 'tags',
                                  'signed')
        write(in_the_way, '')
        before = signed.head()
        code, lines, _asked = walked(signed, ['y'])
        signed_at = signed.head()
        assert signed_at != before
        assert git(signed.root, 'log', '-1', '--format=%s').stdout.strip() \
            == 'sign(2.1.0): jane@acme.com'
        assert [line for line in lines if line.startswith(
            'No tag: git could not write signed/2.1.0:')], lines
        assert code == 1
        os.remove(in_the_way)
        shown = _Out()
        assert sign_module.show(signed.root, out=shown) == 0
        assert shown.text().splitlines() == [
            'signed/2.1.0 is not written yet: jane@acme.com signed 2.1.0 at '
            '%s. Run purlin:sign to write the tag.' % signed_at[:7]]
        code, lines, asked = walked(signed, [])
        assert (code, asked) == (0, []), lines
        assert git(signed.root, 'rev-parse',
                   'signed/2.1.0^{commit}').stdout.strip() == signed_at
        assert signed.head() == signed_at
        assert lines == ['Tagged signed/2.1.0 at %s.' % signed_at[:7],
                         'Push the branch and the tag: git push origin main '
                         'signed/2.1.0']

    # purlin: signatures PROOF-260
    def test_two_signers_who_share_a_name_each_keep_a_sign_off(self, signed):
        assert walked(signed, ['y'])[0] == 0
        folder = os.path.join(signed.root, *SIGNOFFS.split('/'))
        with open(os.path.join(folder, 'jane.json'), 'rb') as handle:
            first = handle.read()
        code, lines, _asked = sign_as(signed, 'jane@labs.org', 'Jane',
                                      file='jane-labs')
        assert code == 0, lines
        assert sorted(os.listdir(folder)) == ['jane-2.json', 'jane.json']
        with open(os.path.join(folder, 'jane.json'), 'rb') as handle:
            assert handle.read() == first
        assert json.loads(first)['signer'] == 'jane@acme.com'
        assert read_json(signed.root, SIGNOFFS + '/jane-2.json')['signer'] \
            == 'jane@labs.org'
        assert status(signed.root).replace('?? .purlin/report-data.js\n',
                                           '') == ''


def signed_with_another_key(made):
    """Quinn's key is the one `user.signingkey` names, and `gpg.ssh.program`
    names a program that signs with another key, as a global setting of a
    password manager does. The walk is answered yes: `(exit, lines, the
    ending of the key that signed, the ending of Quinn's key)`."""
    quinns = key(made.root, email=QUINN, name='Quinn', file='quinn')
    other = os.path.join(made.root, '.git', 'another-key')
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C',
                    'another', '-f', other], check=True)
    owner_only(other)
    program = os.path.join(made.root, '.git', 'sign-with-another-key')
    with open(program, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('#!/bin/sh\n'
                     '# Signs what git hands over with another key than the '
                     'one git names.\n'
                     'for last; do :; done\n'
                     'exec ssh-keygen -Y sign -n git -f "%s" "$last"\n'
                     % other.replace(os.sep, '/'))
    os.chmod(program, 0o755)
    git(made.root, 'config', 'gpg.ssh.program', program.replace(os.sep, '/'))
    code, lines, _asked = walked(made, ['y'])
    return (code, lines, fingerprint_of(other + '.pub')[-4:],
            fingerprint_of(quinns)[-4:])


class TestTheKeyThatSigned:

    # purlin: signatures PROOF-269
    def test_a_commit_signed_with_another_key_is_taken_back(self):
        made = ready(signer=False)
        try:
            before = made.head()
            code, lines, signed_by, named = signed_with_another_key(made)
            assert signed_by != named
            assert lines[-1] == (
                'No sign-off: the commit was signed with the key ending ...%s, '
                'not the key this checkout names, ending ...%s, so it was '
                'taken back and no tag was written. A global gpg.ssh.program '
                'or signing key is the usual cause. Run git config '
                'gpg.ssh.program ssh-keygen, then purlin:sign again.'
                % (signed_by, named))
            assert not [line for line in lines if line.startswith('Signed ')]
            assert (code, made.head()) == (1, before)
            assert git(made.root, 'tag', '--list', 'signed/2.1.0').stdout == ''
        finally:
            made.close()

    # purlin: signatures PROOF-270
    def test_the_refusal_leaves_no_file_and_nothing_staged(self):
        made = ready(signer=False)
        try:
            assert signed_with_another_key(made)[0] == 1
            assert not os.path.exists(os.path.join(made.root,
                                                   *PACKAGE.split('/')))
            folder = os.path.join(made.root, *SIGNOFFS.split('/'))
            assert not os.path.isdir(folder) or os.listdir(folder) == []
            assert git(made.root, 'status', '--porcelain').stdout == ''
        finally:
            made.close()


QUINN = 'quinn.qa@labconnect.example'
STOP_HEAD = 'login RULE-2   hand check'


def manual_results(made):
    """Commit `login`'s results over the code as it stands, `RULE-2` by hand."""
    section(made, [('PROOF-1', 'RULE-1', 'pass', TEST_NAMES['PROOF-1'], None)],
            {'RULE-1': 'passed', 'RULE-2': 'passed'})
    commit_all(made)


def noted_by_quinn():
    """`login RULE-2` is a hand check, and Quinn signed `0.1.0` with a note."""
    made = ready(spec=MANUAL_SPEC, test_file=MANUAL_TEST_FILE, version='0.1.0',
                 signer=False)
    assert sign_as(made, QUINN, 'Quinn', answers=('the tube is red', 'y'))[0] == 0
    return made


def shown_stop(made, name=None):
    """The lines of `login RULE-2`'s stop, as `--show` prints them."""
    out = _Out()
    assert sign_module.show(made.root, name, out=out) == 0, out.text()
    return stop_lines(out.text().splitlines(), STOP_HEAD)


class TestTheLastNote:

    # purlin: signatures PROOF-249
    def test_a_second_signer_sees_the_note_at_this_commit(self):
        made = noted_by_quinn()
        try:
            key(made.root, email='pat.product@labconnect.example', name='Pat',
                file='pat')
            assert shown_stop(made)[-2:] == [
                'Last note',
                '  noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
                'at this commit: the tube is red']
        finally:
            made.close()

    # purlin: signatures PROOF-250
    def test_four_commits_later_the_note_says_so(self):
        made = noted_by_quinn()
        try:
            for number in range(3):
                write(os.path.join(made.root, 'NOTES'), 'note %d\n' % number)
                commit_all(made, 'docs: note %d' % number)
            manual_results(made)
            assert shown_stop(made, '0.2.0')[-1] == (
                '  noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
                '4 commits since: the tube is red')
        finally:
            made.close()

    # purlin: signatures PROOF-251
    def test_before_any_sign_off_the_stop_ends_on_its_results(self):
        made = ready(spec=MANUAL_SPEC, test_file=MANUAL_TEST_FILE)
        try:
            stop = shown_stop(made)
            assert stop[-2:] == [
                'Results', '  No test runs for this rule: you check it here.']
            assert 'Last note' not in stop
        finally:
            made.close()

    # purlin: signatures PROOF-272
    def test_a_rule_reworded_since_the_note_says_so_above_it(self):
        made = noted_by_quinn()
        try:
            reworded = MANUAL_SPEC.replace(
                'RULE-2: Invalid credentials return 401',
                'RULE-2: A wrong password returns 401')
            assert reworded != MANUAL_SPEC
            made.spec(reworded)
            commit_all(made, 'spec(login): reword RULE-2')
            manual_results(made)
            stop = shown_stop(made, '0.2.0')
            assert stop[stop.index('Last note') + 1:] == [
                "  The rule's wording changed since this note.",
                '  noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
                '2 commits since: the tube is red']
        finally:
            made.close()

    # purlin: signatures PROOF-273
    def test_a_proof_reworded_since_the_note_says_so_above_it(self):
        made = noted_by_quinn()
        try:
            reworded = MANUAL_SPEC.replace(
                'POST /login with a bad password',
                'POST /login with a wrong password')
            assert reworded != MANUAL_SPEC
            made.spec(reworded)
            commit_all(made, 'spec(login): reword PROOF-2')
            manual_results(made)
            stop = shown_stop(made, '0.2.0')
            assert stop[stop.index('Last note') + 1:] == [
                "  The proof's wording changed since this note.",
                '  noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
                '2 commits since: the tube is red']
        finally:
            made.close()

    # purlin: signatures PROOF-259
    def test_a_note_edited_and_not_committed_is_not_shown(self):
        made = noted_by_quinn()
        try:
            rel = '.purlin/evidence/package/0.1.0.signoffs/quinn-qa.json'
            path = os.path.join(made.root, *rel.split('/'))
            with open(path, encoding='utf-8') as handle:
                text = handle.read()
            assert text.count('the tube is red') == 1
            write(path, text.replace('the tube is red', 'the tube is blue'))
            assert status(made.root).splitlines()[0] == ' M ' + rel
            reasons = made.rule('RULE-2')['cells']['strong']['reasons']
            assert [reason for reason in reasons
                    if 'the tube is red' in reason], reasons
            assert not [reason for reason in reasons
                        if 'the tube is blue' in reason], reasons
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The agent's walk and the check
# ---------------------------------------------------------------------------

class TestTheAgent:

    # purlin: signatures PROOF-220
    def test_show_prints_every_stop_and_asks_nothing(self, hand_checked,
                                                     capsys):
        code, lines = run_main(hand_checked, capsys, ['--show'])
        assert '  login RULE-1   PROOF-1 reads the status alone.' in lines
        head = lines.index('login RULE-2   hand check')
        assert not any('what did you see' in line for line in lines[head:])
        # A question of any kind ends where its answer is typed, on `: ` or
        # `] `: no line from the stop on does.
        assert not [line for line in lines[head:]
                    if line.endswith((': ', '] '))], lines
        # After the stop comes the last line and nothing else: no question
        # of any kind.
        stop = stop_lines(lines, 'login RULE-2   hand check')
        assert lines[head + len(stop):] == [
            '', 'Answer each stop, then run purlin:sign --answers <file>.']
        at = lines.index('Signing 2.1.0 at %s.' % hand_checked.head()[:7])
        assert lines[at + 1:at + 3] == [
            '  2 rules on Linux/Unix: 1 passes its tests, 1 has a hand check.',
            '  The audit: 0 strong, 1 weak.']
        assert (code, status(hand_checked.root)) == (0, '')

    # purlin: signatures PROOF-228
    def test_show_with_no_key_prints_the_overview_after_the_signing_line(
            self, home, capsys):
        made = ready(signer=False)
        try:
            code, lines = run_main(made, capsys, ['--show'])
            assert code == 0
            at = lines.index('Signing 2.1.0 at %s.' % made.head()[:7])
            assert lines[at + 1] == ('  2 rules on Linux/Unix: 2 pass their '
                                     'tests, no hand check.'), lines
            assert NO_KEY_LINES[0] not in lines
        finally:
            made.close()

    # purlin: signatures PROOF-221
    def test_answers_holding_the_signers_address_walk_with_the_files_note(
            self, hand_checked, capsys):
        path = os.path.join(hand_checked.root, *ANSWERS.split('/'))
        write(path, json.dumps({
            'audit': 'go on',
            'stops': {'login RULE-2': {'answer': 'note',
                                       'note': 'the lockout page read 401'}},
            'sign': EMAIL}))
        code = sign_module.main(['--answers', path, '--project-root',
                                 hand_checked.root])
        lines = capsys.readouterr().out.splitlines()
        assert ('login RULE-2   what did you see, in one line, or Enter for no '
                'note, or stop: the lockout page read 401') in lines
        assert code == 0
        assert signed_off(hand_checked)['notes'] == [
            {'feature': 'login', 'rule': 'RULE-2',
             'note': 'the lockout page read 401'}]

    # purlin: signatures PROOF-264
    def test_answers_whose_sign_is_true_sign_nothing(self, hand_checked,
                                                     capsys, monkeypatch):
        write(os.path.join(hand_checked.root, *ANSWERS.split('/')),
              json.dumps({
                  'audit': 'go on',
                  'stops': {'login RULE-2': {
                      'answer': 'note', 'note': 'the lockout page read 401'}},
                  'sign': True}))
        monkeypatch.chdir(hand_checked.root)
        before = hand_checked.head()
        code = sign_module.main(['--answers', ANSWERS])
        lines = capsys.readouterr().out.splitlines()
        assert lines[-1] == (
            'Nothing was signed: "sign" in .purlin/runtime/signoff-answers.json '
            'must hold jane@acme.com, typed by the person signing.')
        assert (code, hand_checked.head(), status(hand_checked.root)) == (
            0, before, '')

    # purlin: signatures PROOF-271
    def test_answers_holding_another_address_sign_nothing(self, hand_checked,
                                                          capsys, monkeypatch):
        write(os.path.join(hand_checked.root, *ANSWERS.split('/')),
              json.dumps({
                  'audit': 'go on',
                  'stops': {'login RULE-2': {
                      'answer': 'note', 'note': 'the lockout page read 401'}},
                  'sign': 'quinn@acme.com'}))
        monkeypatch.chdir(hand_checked.root)
        before = hand_checked.head()
        code = sign_module.main(['--answers', ANSWERS])
        lines = capsys.readouterr().out.splitlines()
        assert lines[-1] == (
            'Nothing was signed: "sign" in .purlin/runtime/signoff-answers.json '
            'must hold jane@acme.com, typed by the person signing.')
        assert (code, hand_checked.head(), status(hand_checked.root)) == (
            0, before, '')

    # purlin: signatures PROOF-222
    def test_a_stop_with_no_answer_is_refused(self, hand_checked, capsys,
                                              monkeypatch):
        write(os.path.join(hand_checked.root, *ANSWERS.split('/')),
              json.dumps({'audit': 'go on', 'stops': {}, 'sign': EMAIL}))
        monkeypatch.chdir(hand_checked.root)
        before = hand_checked.head()
        code = sign_module.main(['--answers', ANSWERS])
        assert capsys.readouterr().out.splitlines() == [
            'No sign-off: login RULE-2 has no answer in %s. Answer every stop, '
            'then run purlin:sign --answers %s again.' % (ANSWERS, ANSWERS)]
        assert (code, hand_checked.head()) == (1, before)
        assert status(hand_checked.root) == ''

    # purlin: signatures PROOF-240
    def test_check_passes_the_committed_package(self, signed, capsys):
        assert walked(signed, ['y'])[0] == 0
        code = sign_module.main(['--check', os.path.join(
            signed.root, *PACKAGE.split('/'))])
        assert (code, capsys.readouterr().out.splitlines()) == (
            0, ['The package matches its fingerprint.'])

    # purlin: signatures PROOF-241
    def test_check_names_a_package_changed_after(self, signed, capsys):
        assert walked(signed, ['y'])[0] == 0
        path = os.path.join(signed.root, *PACKAGE.split('/'))
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        write(path, text.replace('"version": "2.1.0"', '"version": "2.1.1"'))
        code = sign_module.main(['--check', path])
        lines = capsys.readouterr().out.splitlines()
        assert code == 1
        assert len(lines) == 1
        assert lines[0].startswith('The package does not match its fingerprint: ')
