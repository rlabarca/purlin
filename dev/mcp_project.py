"""The throwaway project the tests of `scripts/mcp/purlin/` share.

`dev/test_specs_reader.py`, `dev/test_states.py` and `dev/test_mcp_server.py`
import the `project` fixture and the helpers from here by name. Every
fixture is written by the test: a spec, the evidence under
`.purlin/evidence/`, a signature beside the spec. This file holds no test and
no marker, and pytest does not collect it.
"""

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))

from purlin import PURLIN_VERSION
from purlin import evidence as purlin_evidence
from purlin import fingerprint as purlin_fingerprint
from purlin import payload as purlin_payload
from purlin import server as purlin_srv

SERVER_PY = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin', 'server.py')


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _git(root, *args, **kwargs):
    return subprocess.run(['git'] + list(args), cwd=root, capture_output=True,
                          text=True, env=kwargs.get('env'))


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in with an email and a password.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n'
    '- RULE-2: Invalid credentials return 401 and the body "denied"\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200 and a '
    'token\n'
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify 401 and the '
    'body "denied"\n'
)

# The same feature with its one rule and no proof line.
NO_PROOF_SPEC = (
    '# Feature: login\n\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n\n'
    '## Proof\n'
)

# The same feature with one rule and its one proof.
ONE_RULE_SPEC = (
    '# Feature: login\n\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200 and '
    'a token\n'
)


class Project(object):
    """A throwaway project root with git, a config and one spec."""

    def __init__(self, spec=SPEC, extra_config=None):
        self.root = tempfile.mkdtemp()
        config = {'version': PURLIN_VERSION,
                  'tests': [{'name': 'pytest', 'run': 'pytest {files}',
                             'report': None, 'format': 'junit',
                             'files': ['tests/test_*.py']}]}
        config.update(extra_config or {})
        _write(os.path.join(self.root, '.purlin', 'config.json'),
               json.dumps(config))
        _write(os.path.join(self.root, '.gitignore'), '.purlin/runtime/\n')
        if spec:
            _write(os.path.join(self.root, 'specs', 'auth', 'login.md'), spec)
        _write(os.path.join(self.root, 'src', 'login.py'), 'def login():\n    return 200\n')
        _git(self.root, 'init', '-q')
        _git(self.root, 'config', 'user.email', 'dev@example.com')
        _git(self.root, 'config', 'user.name', 'Dev')
        _git(self.root, 'add', '-A')
        _git(self.root, 'commit', '-q', '-m', 'chore: project under test')

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def head(self):
        return _git(self.root, 'rev-parse', 'HEAD').stdout.strip()

    def spec(self, text, name='login', category='auth'):
        _write(os.path.join(self.root, 'specs', category, name + '.md'), text)

    def evidence(self, proofs, feature='login', runner='ci', os_name=None,
                 commit_it=True, ci=False, source=None,
                 at='2026-09-13T12:00:00Z', claimed_source=None,
                 audited=True, fingerprint=None):
        """One section of a feature's evidence file, in its source folder.

        `proofs` is `[{'id', 'rule', 'status'}]`, what the run saw. The
        section carries the fingerprint taken now, so it is current until the
        spec, the scoped code or the tests change. `source` is `ci` or
        `local` and defaults to `ci` when `ci=True`. A `ci` section is the
        one a project's own run on another system writes: machine `build-7`,
        email `runner@example.com`, runner `runner`.
        `claimed_source` writes a different word into the file,
        which is how a test makes the two disagree. With `audited` the file
        carries an `audit`.
        """
        source = source or ('ci' if ci else 'local')
        os_name = os_name or purlin_evidence.host_os()
        rel = '.purlin/evidence/%s/%s.json' % (source, feature)
        path = os.path.join(self.root, *rel.split('/'))
        try:
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
        except (IOError, OSError, ValueError):
            data = {'schema': purlin_evidence.SCHEMA, 'feature': feature,
                    'spec': 'specs/auth/%s.md' % feature, 'platforms': {}}
        data['source'] = claimed_source or source
        data['platforms'][os_name] = {
            'commit': self.head(), 'dirty': False, 'at': at,
            'runner': CI_RUNNER if source == 'ci' else runner,
            'machine': _machine(source),
            'fingerprint': fingerprint or purlin_fingerprint.fingerprint(
                self.root, feature),
            'rules': {},
            'proofs': [{'id': entry.get('id'), 'rule': entry.get('rule'),
                        'result': entry.get('status'), 'env': None,
                        'manual': False,
                        'test': _test_of(entry, feature)}
                       for entry in proofs]}
        if source == 'ci':
            data['platforms'][os_name]['email'] = CI_EMAIL
        if audited:
            data.setdefault('audit', {'rules': {}})
        _write(path, json.dumps(data, indent=2, sort_keys=True))
        if commit_it:
            _git(self.root, 'add', '-A')
            _git(self.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234')
        return rel

    def audit(self, rule_id, feature='login', observations=(),
              source='local', word=None, no_bug=(), breaks=None, **extra):
        """Write the audit entry for a rule's current rule, proof and test
        hashes, and the feature's `code` part taken now.

        With an observation the verdict is `weak`, with none `strong`;
        `word` names another outright, `spot-checked` among them. `breaks`
        is the planted bugs on record, one per proof, and `no_bug` the
        sentence for each proof no bug was caught for. `extra` adds any
        other field of the entry, such as `model` or `explanation`.
        """
        rule = self.rule(rule_id, feature)
        rel = '.purlin/evidence/%s/%s.json' % (source, feature)
        path = os.path.join(self.root, *rel.split('/'))
        try:
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
        except (IOError, OSError, ValueError):
            data = {'schema': purlin_evidence.SCHEMA, 'feature': feature,
                    'source': source, 'spec': 'specs/auth/%s.md' % feature,
                    'platforms': {}}
        audit = data.setdefault('audit', {'rules': {}})
        entry = {'rule_hash': rule['rule_hash'],
                 'proof_hash': rule['proof_hash'],
                 'test_hash': rule['test_hash'],
                 'code_hash': purlin_fingerprint.fingerprint(
                     self.root, feature)['code'],
                 'verdict': word or ('weak' if observations else 'strong'),
                 'findings': list(observations), 'no_bug': list(no_bug),
                 'breaks': dict(breaks or {}),
                 'at': '2026-09-13T12:05:00Z', 'commit': self.head()}
        entry.update(extra)
        audit['rules'][rule_id] = entry
        _write(path, json.dumps(data, indent=2, sort_keys=True))
        return rel

    def sign_commits(self, email='jane@acme.com'):
        """Configure a throwaway ssh signing key, so every commit here is signed.

        `dev/test_signatures.py` proves the reader that judges a signature;
        this only has to make signed commits exist so the payload can read
        a signature that counts.
        """
        key = os.path.join(self.root, '.git', 'signing-key')
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C',
                        email, '-f', key], check=True)
        for name, value in (('user.email', email), ('user.name', 'Jane'),
                            ('gpg.format', 'ssh'),
                            ('user.signingkey', key + '.pub'),
                            ('commit.gpgsign', 'true')):
            _git(self.root, 'config', name, value)

    def payload(self):
        return purlin_payload.build_payload(self.root)

    def rule(self, rule_id, feature='login'):
        data = self.payload()
        entry = next(f for f in data['features'] if f['name'] == feature)
        return next(r for r in entry['rules'] if r['id'] == rule_id)

    def cell(self, rule_id, name, feature='login'):
        return self.rule(rule_id, feature)['cells'][name]

    def config_value(self, key, value):
        path = os.path.join(self.root, '.purlin', 'config.json')
        with open(path, encoding='utf-8') as handle:
            settings = json.load(handle)
        settings[key] = value
        _write(path, json.dumps(settings))


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


def _listed(data, rule_id, feature='login', listed_under=None):
    """A rule's entry in a payload, as the feature it is listed under lists it."""
    under = next(f for f in data['features']
                 if f['name'] == (listed_under or feature))
    return next(r for r in under['rules']
                if r['id'] == rule_id and r['feature'] == feature)


# What a `ci` section records: the machine of a project's own run on another
# system, and the git identity set there.
CI_MACHINE = 'build-7'
CI_EMAIL = 'runner@example.com'
CI_RUNNER = 'runner'


def _machine(source):
    """The `machine` a section names, the host's name under either source."""
    return CI_MACHINE if source == 'ci' else 'dev-machine'


def _test_of(entry, feature):
    """`<file>::<name>` for one observed proof, as a section lists it."""
    if entry.get('test_file'):
        return '%s::%s' % (entry['test_file'], entry.get('test_name', ''))
    return 'tests/test_%s.py::test_%s' % (
        feature, str(entry.get('id', '')).lower().replace('-', '_'))


def _marked_tests(*proof_ids, feature='login'):
    """A test file holding one marked test per proof id."""
    return ''.join('# purlin: %s %s\ndef test_%s():\n    pass\n\n'
                   % (feature, proof_id, proof_id.lower().replace('-', '_'))
                   for proof_id in proof_ids)


def _commit_tests(project, *proof_ids):
    """Write and commit a test file marking each proof id."""
    _write(os.path.join(project.root, 'tests', 'test_login.py'),
           _marked_tests(*proof_ids))
    _git(project.root, 'add', '-A')
    _git(project.root, 'commit', '-q', '-m', 'test(login): marked tests')


def _entry(proof_id, rule_id, status='pass', feature='login',
           test_file='tests/test_login.py'):
    return {'feature': feature, 'id': proof_id, 'rule': rule_id,
            'status': status, 'test_file': test_file,
            'test_name': 'test_' + proof_id.lower().replace('-', '_')}


def _rpc(root, *requests, **kwargs):
    """The server's answers to `requests` on stdin, and what it wrote to stderr.

    The server's `main()` runs in this process with `root` as the working
    directory.
    `child=True` starts `server.py` as the client does instead.
    """
    lines = '\n'.join(json.dumps(request) for request in requests) + '\n'
    if kwargs.get('child'):
        result = subprocess.run([sys.executable, SERVER_PY], input=lines,
                                capture_output=True, text=True, cwd=root,
                                timeout=180)
        stdout, stderr = result.stdout, result.stderr
    else:
        out, err = io.StringIO(), io.StringIO()
        cwd, stdin = os.getcwd(), sys.stdin
        os.chdir(root)
        sys.stdin = io.StringIO(lines)
        try:
            with contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                purlin_srv.main()
        finally:
            os.chdir(cwd)
            sys.stdin = stdin
        stdout, stderr = out.getvalue(), err.getvalue()
    return [json.loads(line) for line in stdout.splitlines()
            if line.strip()], stderr
