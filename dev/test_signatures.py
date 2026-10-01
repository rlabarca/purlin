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
*the refusals*   what stops a sign-off
*the walk*       the run lines, the overview, the audit's findings, the stops
*the sign-off*   the file, its commit, the tag, a second signer
*the agent*      `--show`, `--answers` and `--check`
"""

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
from sign_project import SPEC, TEST_FILE, TEST_NAMES, Project, _Out, git, write  # noqa: E402


# ---------------------------------------------------------------------------
# The throwaway project
# ---------------------------------------------------------------------------

EMAIL = 'jane@acme.com'
DANA = 'dana.dev@labconnect.example'
MACHINE = 'dana-laptop'
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
            feature='login'):
    """One evidence section, as the run writes it, over the project as it stands.

    `proofs` is `[(id, rule, result, test name or None, reason or None)]`;
    `rules` is `{RULE-N: word}`. A remote runner's section names no email.
    """
    entries = []
    for proof_id, rule, result, name, reason in proofs:
        entry = {'id': proof_id, 'rule': rule, 'result': result, 'env': None,
                 'manual': False,
                 'test': 'tests/test_%s.py::%s' % (feature, name) if name
                 else ''}
        if reason is not None:
            entry['reason'] = reason
        entries.append(entry)
    found = {'commit': commit or made.head(), 'dirty': False, 'at': at,
             'runner': 'ci' if source == 'ci' else email.split('@')[0],
             'machine': machine,
             'fingerprint': purlin_fingerprint.fingerprint(made.root, feature),
             'rules': dict(rules), 'proofs': entries}
    if source == 'ci':
        found['hostname'] = 'runner-17'
    else:
        found['email'] = email
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


class TestTheRefusals:

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
                    machine='remote runner, Windows', feature='audit')
            commit_all(made, 'purlin: results pulled home')
            write(os.path.join(made.root, 'src', 'audit.py'), 'LINES = 2\n')
            commit_all(made, 'fix(audit): two lines')
            passing(made)
            section(made, [('PROOF-1', 'RULE-1', 'not run',
                            'test_one_line_per_sign_in', None)],
                    {'RULE-1': 'not run'}, feature='audit')
            commit_all(made)
            assert run_main(made, capsys) == (1, [
                'No sign-off: these results were not taken on this version of '
                'the code, %s: audit on Windows. Run purlin:test --remote, '
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
        git(signed.root, 'tag', 'signed/2.1.0')
        tagged = signed.head()
        git(signed.root, 'switch', '-q', 'main')
        assert run_main(signed, capsys) == (1, [
            'No sign-off: signed/2.1.0 is at %s, which this checkout does not '
            'hold. Pull, then run purlin:sign.' % tagged[:7]])

    # purlin: signatures PROOF-225
    def test_a_code_change_since_the_tag_is_refused(self, signed, capsys):
        git(signed.root, 'tag', 'signed/2.1.0')
        tagged = signed.head()
        write(os.path.join(signed.root, 'src', 'login.py'),
              'def login(user, password):\n    return 401\n')
        commit_all(signed, 'fix(login): refuse')
        assert run_main(signed, capsys) == (1, [
            'No sign-off: signed/2.1.0 is at %s, and the code has changed '
            'since. To sign this code, name a new version: purlin:sign '
            '--version <version>.' % tagged[:7]])

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
    on 2026-10-01; 17 rules are audited strong, 1 weak, and the hand check
    is not audited."""
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
            '  19 rules on Linux/Unix: 19 pass their tests, 1 has a hand check.',
            '  The audit: 17 strong, 1 weak, 1 not audited.']

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
            code, lines, asked = walked(made, ['list'])
            assert '  login RULE-1   PROOF-1 reads the status alone.' in lines
            assert asked[:2] == ["The audit's findings: 1 weak. list / go on: ",
                                 'go on: ']
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
        text = json.dumps(body)
        assert not any('"%s"' % word in text
                       for word in ('go on', 'list', 'y', 'yes', 'stop'))

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
            code, lines, _asked = sign_as(made, 'quinn.qa@labconnect.example',
                                          'Quinn')
            head = made.head()
            assert code == 0
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
    def test_it_fetches_nothing_and_pushes_nothing(self, signed, tmp_path):
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
        assert git(signed.root, 'rev-parse', '--verify', '--quiet',
                   'signed/2.1.0').returncode == 0
        assert git(host, 'tag', '--list').stdout == ''
        assert git(host, 'rev-parse', 'main').stdout.strip() == hosted
        assert not os.path.exists(os.path.join(signed.root, '.git',
                                               'FETCH_HEAD'))


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
        assert lines[-1] == ('Answer each stop, then run purlin:sign '
                             '--answers <file>.')
        at = lines.index('Signing 2.1.0 at %s.' % hand_checked.head()[:7])
        assert lines[at + 1:at + 3] == [
            '  2 rules on Linux/Unix: 2 pass their tests, 1 has a hand check.',
            '  The audit: 0 strong, 1 weak, 1 not audited.']
        assert (code, status(hand_checked.root)) == (0, '')

    # purlin: signatures PROOF-228
    def test_show_needs_no_key(self, home, capsys):
        made = ready(signer=False)
        try:
            code, lines = run_main(made, capsys, ['--show'])
            assert code == 0
            assert 'Signing 2.1.0 at %s.' % made.head()[:7] in lines
            assert NO_KEY_LINES[0] not in lines
        finally:
            made.close()

    # purlin: signatures PROOF-221
    def test_answers_walk_with_the_files_note(self, hand_checked, capsys):
        path = os.path.join(hand_checked.root, *ANSWERS.split('/'))
        write(path, json.dumps({
            'audit': 'go on',
            'stops': {'login RULE-2': {'answer': 'note',
                                       'note': 'the lockout page read 401'}},
            'sign': True}))
        code = sign_module.main(['--answers', path, '--project-root',
                                 hand_checked.root])
        lines = capsys.readouterr().out.splitlines()
        assert ('login RULE-2   what did you see, in one line, or Enter for no '
                'note, or stop: the lockout page read 401') in lines
        assert code == 0
        assert signed_off(hand_checked)['notes'] == [
            {'feature': 'login', 'rule': 'RULE-2',
             'note': 'the lockout page read 401'}]

    # purlin: signatures PROOF-222
    def test_a_stop_with_no_answer_is_refused(self, hand_checked, capsys,
                                              monkeypatch):
        write(os.path.join(hand_checked.root, *ANSWERS.split('/')),
              json.dumps({'audit': 'go on', 'stops': {}, 'sign': True}))
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
