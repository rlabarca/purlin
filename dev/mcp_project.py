"""The throwaway project the tests of `scripts/mcp/purlin/` share.

`dev/test_specs_reader.py`, `dev/test_states.py` and `dev/test_mcp_server.py`
import the `project` fixture and the helpers from here by name. Every
fixture is written by the test: a spec, a runtime proof file, the evidence
under `.purlin/evidence/`, a signature beside the spec. This file holds no
test and no marker, and pytest does not collect it.
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

from purlin import signatures as purlin_signatures
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


# The committer a CI evidence commit carries in these fixtures. An evidence
# file's source is the folder it sits in, and nothing the server reads asks
# who committed it; that is the tag run's question, proved in
# `dev/test_provenance.py`.
CI_COMMITTER = {'GIT_COMMITTER_NAME': 'github-actions[bot]',
                'GIT_COMMITTER_EMAIL': 'noreply@github.com'}


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in with an email and a password.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token '
    '[level: signed]\n'
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

    def __init__(self, spec=SPEC, gate='passed', extra_config=None):
        self.root = tempfile.mkdtemp()
        config = {'gate': gate, 'project_name': 'proj',
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
                 strength=90, commit_it=True, ci=False, source=None,
                 at='2026-09-13T12:00:00Z', claimed_source=None,
                 audited=True, fingerprint=None):
        """One section of a feature's evidence file, in its source folder.

        `proofs` is `[{'id', 'rule', 'status'}]`, what the run saw. The
        section carries the fingerprint taken now, so it is current until the
        spec, the scoped code or the tests change. `source` is `ci` or
        `local` and defaults to `ci` when `ci=True`, so a test that wanted
        the git host's own evidence gets the git host's own folder and
        committer. `claimed_source` writes a different word into the file,
        which is how a test makes the two disagree. With `audited` the file
        carries an `audit` whose `mutation` holds `strength`.
        """
        source = source or ('ci' if ci else 'local')
        os_name = os_name or purlin_evidence.host_os()
        rel = '.purlin/evidence/%s/%s.json' % (source, feature)
        path = os.path.join(self.root, *rel.split('/'))
        try:
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
        except (IOError, OSError, ValueError):
            data = {'schema': 'purlin-evidence/1', 'feature': feature,
                    'spec': 'specs/auth/%s.md' % feature, 'platforms': {}}
        data['source'] = claimed_source or source
        data['platforms'][os_name] = {
            'commit': self.head(), 'dirty': False, 'at': at,
            'runner': runner,
            'fingerprint': fingerprint or purlin_fingerprint.fingerprint(
                self.root, feature),
            'rules': {},
            'proofs': [{'id': entry.get('id'), 'rule': entry.get('rule'),
                        'result': entry.get('status'), 'env': None,
                        'manual': False,
                        'test': _test_of(entry, feature)}
                       for entry in proofs]}
        if audited:
            audit = data.setdefault('audit', {'mutation': None, 'rules': {}})
            audit['mutation'] = {'engine': 'mutmut' if strength is not None
                                 else 'none', 'score': strength, 'at': at,
                                 'commit': self.head()}
        _write(path, json.dumps(data, indent=2, sort_keys=True))
        if commit_it:
            env = None
            if ci:
                env = dict(os.environ)
                env.update(CI_COMMITTER)
            _git(self.root, 'add', '-A')
            _git(self.root, 'commit', '-q', '-m', 'purlin: evidence at abc1234',
                 env=env)
        return rel

    def signature(self, rule_id, feature='login', category='auth',
                  signer='jane@acme.com', commit_it=True, **overrides):
        """Write one signature file for a rule's current hashes."""
        rule = self.rule(rule_id, feature)
        data = {
            'schema': 'purlin-signature/1', 'feature': feature,
            'rule': rule_id, 'level': rule['level'], 'signer': signer,
            'note': None, 'timestamp': '2026-09-13T12:00:00Z',
            'rule_hash': rule['rule_hash'], 'proof_hash': rule['proof_hash'],
            'test_hash': rule['test_hash'],
            'test_hash_kind': rule['test_hash_kind'],
            'audit_hash': rule['audit_hash'],
        }
        data.update(overrides)
        data['triple'] = purlin_signatures.triple_hash(
            data['rule_hash'], data['proof_hash'], data['test_hash'])[:16]
        slug = purlin_signatures.signer_slug(signer)
        hash8 = purlin_signatures.triple_hash(
            rule['rule_hash'], rule['proof_hash'], rule['test_hash'])[:8]
        directory = os.path.join(self.root, 'specs', category,
                                 feature + '.signatures')
        name = '%s.%s.%s.json' % (rule_id, hash8, slug)
        _write(os.path.join(directory, name), json.dumps(data))
        if commit_it:
            _git(self.root, 'add', '-A')
            _git(self.root, 'commit', '-q', '-m', 'sign(%s): %s'
                 % (feature, rule_id))
        return os.path.join(directory, name)

    def audit(self, rule_id, feature='login', settled=True, observations=(),
              source='local', word=None, **extra):
        """Write the audit entry for a rule's current rule, proof and test hashes.

        `settled` with no observation is `strong`, with one `weak`, and not
        settled is `undecided`; `word` names another outright. `extra`
        adds fields the format does not name.
        """
        rule = self.rule(rule_id, feature)
        rel = '.purlin/evidence/%s/%s.json' % (source, feature)
        path = os.path.join(self.root, *rel.split('/'))
        try:
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
        except (IOError, OSError, ValueError):
            data = {'schema': 'purlin-evidence/1', 'feature': feature,
                    'source': source, 'spec': 'specs/auth/%s.md' % feature,
                    'platforms': {}}
        audit = data.setdefault('audit', {'mutation': None, 'rules': {}})
        entry = {'rule_hash': rule['rule_hash'],
                 'proof_hash': rule['proof_hash'],
                 'test_hash': rule['test_hash'],
                 'verdict': word or ('undecided' if not settled else
                                     'weak' if observations else 'strong'),
                 'findings': list(observations),
                 'at': '2026-09-13T12:05:00Z', 'commit': self.head()}
        entry.update(extra)
        audit['rules'][rule_id] = entry
        _write(path, json.dumps(data, indent=2, sort_keys=True))
        return rel

    def sign_commits(self, email='jane@acme.com'):
        """Configure a throwaway ssh signing key, so a commit verifies here.

        `dev/test_signatures.py` proves the reader that judges a signature;
        this only has to make one signed commit exist so the payload can read
        a signature that counts.
        """
        key = os.path.join(self.root, '.git', 'signing-key')
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C',
                        email, '-f', key], check=True)
        with open(key + '.pub', encoding='utf-8') as handle:
            public = handle.read().strip()
        allowed = os.path.join(self.root, '.git', 'allowed-signers')
        _write(allowed, '%s %s\n' % (email, public))
        for name, value in (('user.email', email), ('user.name', 'Jane'),
                            ('gpg.format', 'ssh'),
                            ('user.signingkey', key + '.pub'),
                            ('commit.gpgsign', 'true'),
                            ('gpg.ssh.allowedSignersFile', allowed)):
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


# One spec with a rule at each level under the gate `signed`, and a rule at
# `passed` and one at `strong` whose tests fail: a rule is asked only what its
# level asks.
LEVELS_SPEC = (
    '# Feature: login\n\n'
    '> Description: One rule at each level.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 [level: passed]\n'
    '- RULE-2: Invalid credentials return 401 [level: strong]\n'
    '- RULE-3: Five failures lock the account\n'
    '- RULE-4: The page loads in a second [level: passed]\n'
    '- RULE-5: A locked account returns 423 [level: strong]\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200\n'
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify 401\n'
    '- PROOF-3 (RULE-3): POST /login 5 times with a bad password; verify the '
    'sixth returns 423\n'
    '- PROOF-4 (RULE-4): GET /; verify the reply arrives within 1000 ms\n'
    '- PROOF-5 (RULE-5): POST /login to a locked account; verify 423\n'
)


ONE_PASSED_SPEC = (
    '# Feature: notes\n\n'
    '> Description: A spec whose one rule asks for its tests alone.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: A note keeps its text [level: passed]\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): Save the note "hi"; verify it reads "hi"\n'
)


def _levels_project(gate='signed'):
    """A `signed` project with a rule at each level, three audited strong."""
    made = Project(spec=LEVELS_SPEC, gate=gate)
    made.evidence([_entry('PROOF-1', 'RULE-1'), _entry('PROOF-2', 'RULE-2'),
                   _entry('PROOF-3', 'RULE-3'),
                   _entry('PROOF-4', 'RULE-4', status='fail'),
                   _entry('PROOF-5', 'RULE-5', status='fail')])
    for rule_id in ('RULE-1', 'RULE-2', 'RULE-3'):
        made.audit(rule_id)
    return made


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


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
    directory, so a mutation run can see which case caught a break.
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
