"""The throwaway signing project the signature, export and audit tests share.

A helper module, not a test file: it carries no marker and pytest collects
nothing from it. Each test file imports the names it uses from here, so no
test file imports another. Everything a project here holds lives in a
temporary directory, and every key it signs with is a throwaway one inside
that project's own `.git`.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
for _path in (os.path.join(ROOT, 'scripts', 'mcp'),
              os.path.join(ROOT, 'scripts', 'review'),
              os.path.join(ROOT, 'scripts', 'export')):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from purlin import PURLIN_VERSION  # noqa: E402
from purlin import evidence as purlin_evidence  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402
from purlin import fingerprint as purlin_fingerprint  # noqa: E402


SIGN_PY = os.path.join(ROOT, 'scripts', 'review', 'sign.py')


SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in with an email and a password.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n'
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
    '# purlin: login PROOF-1\n'
    'def test_valid_credentials_return_200():\n'
    '    assert login("ada", "secret") == 200\n'
    '\n'
    '\n'
    '# purlin: login PROOF-2\n'
    'def test_a_bad_password_is_denied():\n'
    '    assert login("ada", "wrong") == 401\n'
)


TEST_NAMES = {'PROOF-1': 'test_valid_credentials_return_200',
              'PROOF-2': 'test_a_bad_password_is_denied'}


# What a `ci` section records: the machine of a project's own run on another
# system, and the git identity set there.
CI_MACHINE = 'build-7'
CI_EMAIL = 'runner@example.com'
CI_RUNNER = 'runner'


def machine_of(source):
    """The machine a section records, the host's name under either source."""
    return CI_MACHINE if source == 'ci' else 'jane-laptop'


def sha256(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


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

    def __init__(self, spec=SPEC, config=None):
        self.root = tempfile.mkdtemp()
        settings = {'version': PURLIN_VERSION,
                    'tests': [{'name': 'pytest', 'run': 'pytest {files}',
                               'report': None, 'format': 'junit',
                               'files': ['tests/test_*.py']}]}
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

    def evidence(self, statuses=None, runner='ada',
                 commit_it=True, at='2026-09-13T12:00:00Z', tests=None,
                 source='local', os_name=None, audited=True):
        """Write a section naming the tests `statuses` names. Its path.

        The section carries the fingerprint taken now, so it is current until
        the spec, the scoped code or the test changes. `tests` maps a proof to
        the test names the section observed for it, for a proof backed by
        more than one test. `source` is the folder it goes in, which is what
        a reader reads the source off. With `audited` the file carries an
        `audit` too.
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
            'runner': CI_RUNNER if source == 'ci' else runner,
            'machine': machine_of(source),
            'fingerprint': purlin_fingerprint.fingerprint(self.root, 'login'),
            'rules': {}, 'proofs': proofs}
        if source == 'ci':
            data['platforms'][os_name]['email'] = CI_EMAIL
        if audited:
            data.setdefault('audit', {'rules': {}})
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
            return {'schema': purlin_evidence.SCHEMA, 'feature': feature,
                    'source': source, 'spec': 'specs/auth/%s.md' % feature,
                    'platforms': {}}

    def audit(self, rule, findings=(), source='local', feature='login',
              no_bug=(), word=None, breaks=None):
        """Write the audit entry for a rule's current rule, proof and test
        hashes, and the feature's `code` part taken now.

        An entry is current only while the rule, the proof, the test and the
        code all stand as they were when the audit read them. With a finding
        the verdict is `weak`, with none `strong`; `word` names
        `spot-checked` outright. `breaks` is the planted bugs on record, one
        per proof, and `no_bug` the sentence for each proof no bug was caught
        for.
        """
        entry = self.rule(rule, feature)
        rel = '.purlin/evidence/%s/%s.json' % (source, feature)
        data = self._read_evidence(rel, source, feature)
        audit = data.setdefault('audit', {'rules': {}})
        audit['rules'][rule] = {
            'rule_hash': entry['rule_hash'],
            'proof_hash': entry['proof_hash'],
            'test_hash': entry['test_hash'],
            'code_hash': purlin_fingerprint.fingerprint(
                self.root, feature)['code'],
            'verdict': word or ('weak' if findings else 'strong'),
            'findings': list(findings), 'no_bug': list(no_bug),
            'breaks': dict(breaks or {}),
            'at': '2026-09-13T12:05:00Z',
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


def signing_key(root, email='jane@acme.com'):
    """A throwaway ssh signing key, configured in this checkout alone.

    `gpg.ssh.program` is set here too, so a program the machine names for
    every checkout does not sign with a key of its own."""
    key = os.path.join(root, '.git', 'signing-key')
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', email,
                    '-f', key], check=True)
    for name, value in (('user.email', email), ('user.name', 'Jane'),
                        ('gpg.format', 'ssh'),
                        ('gpg.ssh.program', 'ssh-keygen'),
                        ('user.signingkey', key + '.pub')):
        git(root, 'config', name, value)
    return key + '.pub'


def commit_all(root, message='purlin: evidence at abc1234'):
    """Stage and commit everything, as the run that wrote the evidence does."""
    git(root, 'add', '-A')
    git(root, 'commit', '-q', '-m', message)


def signing_project(signer='jane@acme.com'):
    """A project whose two rules pass under the source `ci` and carry an audit reading
    strong, ready for a sign-off.

    The signer's key is set up last.
    """
    made = Project()
    made.evidence(commit_it=False, source='ci')
    made.audit('RULE-1')
    made.audit('RULE-2')
    commit_all(made.root)
    signing_key(made.root, signer)
    return made


MODEL = 'claude-opus-5-20260901'
CRITERIA = 'c' * 64


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


class _Out(object):
    """Somewhere for the walk and the tag to print, read back as one string."""

    def __init__(self):
        self.lines = []

    def write(self, text):
        self.lines.append(text)

    def flush(self):
        pass

    def text(self):
        return ''.join(self.lines)
