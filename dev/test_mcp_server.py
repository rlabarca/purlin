"""Tests for the core package `scripts/mcp/purlin/`.

Five areas, in the order a project meets them: what a spec parses to, what a
test run leaves behind, what the cells of each rule read, what the payload
and the status table say about it, and what the MCP transport answers.

Every fixture is written by the test: a spec, a runtime proof file, the
evidence under `.purlin/evidence/`, a signature beside the spec. Nothing here reads the repository's own specs except where a test
says so.
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

from purlin import board as purlin_board
from purlin import signatures as purlin_signatures
from purlin import evidence as purlin_evidence
from purlin import fingerprint as purlin_fingerprint
from purlin import frameworks as purlin_frameworks
from purlin import gate as purlin_gate
from purlin import payload as purlin_payload
from purlin import server as purlin_srv
from purlin import specs as purlin_specs
from purlin import states as purlin_states
from purlin import status as purlin_status

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


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class TestSpecParsing:

    # purlin: specs PROOF-1
    # purlin: specs PROOF-3
    def test_rule_tags_are_read_off_the_end_and_stripped(self, project):
        info = purlin_specs.scan_specs(project.root)['login']
        assert info['rules']['RULE-1'] == (
            'Valid credentials return 200 with a session token'), info['rules']
        assert info['rule_meta']['RULE-1'] == {'level': 'signed'}
        # A rule that names no tag carries no metadata at all.
        assert info['rule_meta']['RULE-2'] == {}

    # purlin: specs PROOF-2
    def test_bracketed_text_that_is_not_a_tag_stays_in_the_claim(self):
        text, meta = purlin_specs.split_rule_tags(
            'Tokens expire [owner: qa] [level: strong]')
        assert text == 'Tokens expire [owner: qa]'
        assert meta == {'level': 'strong'}

    # purlin: specs PROOF-4
    def test_the_hash_ignores_the_tags_and_the_whitespace(self):
        plain = purlin_specs.rule_text_hash('Tokens expire after 24 hours')
        tagged, _meta = purlin_specs.split_rule_tags(
            'Tokens  expire   after 24 hours [level: strong]')
        assert purlin_specs.rule_text_hash(tagged) == plain, (
            're-tagging or reflowing a rule must not change its rule text hash')

    # purlin: specs PROOF-17
    def test_the_level_tag_takes_the_gates_three_words(self):
        claim = 'Tokens expire after 24 hours'
        hashes = set()
        for level in ('passed', 'strong', 'signed'):
            text, meta = purlin_specs.split_rule_tags(
                '%s [level: %s]' % (claim, level))
            assert meta == {'level': level}, meta
            assert text == claim and '[' not in text, text
            hashes.add(purlin_specs.rule_text_hash(text))
        assert len(hashes) == 1, hashes

    # purlin: specs PROOF-5
    # purlin: specs PROOF-6
    def test_env_is_parsed_and_bounded_to_three_values(self, project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n- RULE-1: Files lock\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Lock a file; verify a second open fails '
            '@manual @env(windows)\n')
        info = purlin_specs.scan_specs(project.root)['login']
        assert info['proofs']['PROOF-1']['env'] == 'windows'
        assert info['proofs']['PROOF-1']['manual'] is True
        assert info['proof_env'] == {'PROOF-1': 'windows'}
        for value in ('windows', 'macos', 'linux'):
            assert purlin_specs.split_proof_tags('x @env(%s)' % value)[2] == value
        assert purlin_specs.split_proof_tags('x @env(bsd)')[2] is None
        assert purlin_specs.split_proof_tags('x @env(bsd)')[3] == ['@env(bsd)']
        # A proof line with no tag at all is not manual, and a trailing
        # word that is not a tag stays in the text.
        assert purlin_specs.split_proof_tags(
            'Call login and verify 200')[:2] == ('Call login and verify 200',
                                                 False)
        assert purlin_specs.split_proof_tags(
            'Call login and verify 200 @smoke')[:2] == (
                'Call login and verify 200 @smoke', False)

    # purlin: specs PROOF-7
    def test_a_second_env_tag_is_refused_not_merged(self):
        _clean, _manual, env, unknown = purlin_specs.split_proof_tags(
            'Lock it @env(macos) @env(windows)')
        assert env == 'windows', 'the trailing tag is the one that is read'
        assert unknown == ['@env(macos)'], unknown

    # purlin: specs PROOF-8
    # purlin: specs PROOF-9
    def test_unknown_tags_are_ignored_with_one_warning_naming_the_files(self,
                                                                       project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n- RULE-1: Files lock\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Lock a file; verify 1 open fails '
            '@windows\n')
        project.spec(
            '# Feature: mockup\n\n> Visual-Reference: ./mock.png\n\n'
            '## Rules\n\n- RULE-1: It renders\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Look at it @manual(a@b.c, '
            '2026-03-31, abc1234)\n', name='mockup')
        features = purlin_specs.scan_specs(project.root)
        assert features['login']['proofs']['PROOF-1']['env'] is None
        assert features['login']['unknown_tags'] == ['@windows']
        assert features['mockup']['proofs']['PROOF-1']['manual'] is True
        assert set(features['mockup']['unknown_tags']) == {
            '@manual(...)', '> Visual-Reference:'}
        warning = purlin_specs.unknown_tag_warning(features)
        assert warning and 'specs/auth/login.md' in warning, warning
        assert 'specs/auth/mockup.md' in warning, warning
        # One line, naming the files: not one warning per proof line.
        assert warning.count('\n') == 0, warning
        # A scan whose specs carry no such tag warns about nothing at all.
        clean = {name: dict(info, unknown_tags=[])
                 for name, info in features.items()}
        assert purlin_specs.unknown_tag_warning(clean) is None

    # purlin: specs PROOF-10
    def test_a_source_is_a_git_url_plus_a_path_or_whole(self):
        assert purlin_specs.parse_source(
            'https://github.com/acme/p.git specs/no_eval.md') == (
                'https://github.com/acme/p.git', 'specs/no_eval.md')
        assert purlin_specs.parse_source('./policies') == ('./policies', None)
        # Not a URL followed by a path: the whole line is the source, so a
        # value that has to be refused is refused whole.
        assert purlin_specs.parse_source('--upload-pack=/bin/echo') == (
            '--upload-pack=/bin/echo', None)

    # purlin: specs PROOF-11
    def test_a_path_field_supplies_the_path_for_a_bare_source_url(self, project):
        project.spec(
            '# Anchor: policy\n\n'
            '> Source: https://github.com/acme/p.git\n'
            '> Path: specs/no_eval.md\n'
            '> Pinned: abc1234\n\n'
            '## Rules\n\n- RULE-1: No eval in source files\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Grep src/ for eval(; verify zero '
            'matches\n', name='policy', category='_anchors')
        info = purlin_specs.scan_specs(project.root)['policy']
        assert info['source'] == 'https://github.com/acme/p.git'
        assert info['source_path'] == 'specs/no_eval.md', info

    # purlin: specs PROOF-12
    def test_an_anchor_carries_its_source_and_its_pin(self, project):
        project.spec(
            '# Anchor: policy\n\n'
            '> Source: https://github.com/acme/p.git specs/no_eval.md\n'
            '> Pinned: abc1234def\n\n'
            '## Rules\n\n- RULE-1: No eval in source files\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Grep src/ for eval(; verify zero '
            'matches\n', name='policy', category='_anchors')
        info = purlin_specs.scan_specs(project.root)['policy']
        assert info['is_anchor'] is True
        assert info['source'] == 'https://github.com/acme/p.git'
        assert info['source_path'] == 'specs/no_eval.md'
        assert info['pinned'] == 'abc1234def'

    # purlin: specs PROOF-14
    def test_requires_and_global_pull_rules_into_a_feature(self, project):
        project.spec(
            '# Anchor: api\n\n## Rules\n\n- RULE-1: Responses carry a type\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): GET /x; verify the header\n',
            name='api', category='schema')
        project.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
            name='security', category='_anchors')
        project.spec(SPEC.replace('# Feature: login\n',
                                  '# Feature: login\n\n> Requires: api\n'))
        features = purlin_specs.scan_specs(project.root)
        refs = purlin_specs.rule_refs('login', features)
        assert refs == [
            ('login', 'RULE-1', 'own'), ('login', 'RULE-2', 'own'),
            ('api', 'RULE-1', 'required'),
            ('security', 'RULE-1', 'global')], refs
        # An anchor proves its own rules and nothing else.
        assert purlin_specs.rule_refs('security', features) == [
            ('security', 'RULE-1', 'own')]

    # purlin: specs PROOF-15
    def test_every_spec_is_keyed_by_its_filename_stem(self, project):
        project.spec(SPEC, name='sign_up')
        undecodable = os.path.join(project.root, 'specs', 'auth', 'broken.md')
        with open(undecodable, 'wb') as handle:
            handle.write(b'# Feature: broken\n\xff\xfe not utf-8\n')
        features = purlin_specs.scan_specs(project.root)
        assert 'login' in features and 'sign_up' in features, sorted(features)
        assert 'broken' not in features, (
            'a file that cannot be decoded must be skipped, not parsed')
        assert features['sign_up']['spec_path'] == 'specs/auth/sign_up.md'
        # A project with no specs/ directory is an empty scan, not an error.
        empty = tempfile.mkdtemp()
        try:
            assert purlin_specs.scan_specs(empty) == {}
        finally:
            shutil.rmtree(empty, ignore_errors=True)


# ---------------------------------------------------------------------------
# Frameworks
# ---------------------------------------------------------------------------

class TestFrameworks:

    def test_nothing_detected_is_an_empty_answer_and_every_match_is_returned(
            self, tmp_path):
        root = str(tmp_path)
        assert purlin_frameworks.detect_frameworks(root) == []
        _write(os.path.join(root, 'conftest.py'), '')
        _write(os.path.join(root, 'package.json'),
               json.dumps({'devDependencies': {'vitest': '^1.0.0'}}))
        assert purlin_frameworks.detect_frameworks(root) == ['pytest', 'vitest']

    def test_a_package_that_only_mentions_a_framework_is_not_that_project(self,
                                                                         tmp_path):
        root = str(tmp_path)
        _write(os.path.join(root, 'package.json'),
               json.dumps({'description': 'migrated off jest',
                           'devDependencies': {'vitest': '^1.0.0'}}))
        assert purlin_frameworks.detect_frameworks(root) == ['vitest']

    def test_dotnet_is_a_csproj_that_references_a_test_framework(self,
                                                              tmp_path):
        root = str(tmp_path)
        _write(os.path.join(root, 'tests', 'App.Tests.csproj'),
               '<Project><ItemGroup>'
               '<PackageReference Include="xunit" Version="2.6.0" />'
               '</ItemGroup></Project>\n')
        assert 'dotnet' in purlin_frameworks.detect_frameworks(root)
        _write(os.path.join(root, 'tests', 'App.Tests.csproj'),
               '<Project><ItemGroup>'
               '<PackageReference Include="Moq" Version="4" />'
               '</ItemGroup></Project>\n')
        assert 'dotnet' not in purlin_frameworks.detect_frameworks(root)

    def test_go_shell_and_sql_are_detected_by_their_test_files(self, tmp_path):
        root = str(tmp_path)
        _write(os.path.join(root, 'go.mod'), 'module example.com/x\n')
        _write(os.path.join(root, 'cart', 'cart_test.go'), 'package cart\n')
        _write(os.path.join(root, 'tests', 'login.test.sh'), 'exit 0\n')
        _write(os.path.join(root, 'tests', 'test_users.sql'), 'SELECT 1;\n')
        assert purlin_frameworks.detect_frameworks(root) == ['go', 'sql',
                                                             'shell']

    def test_a_project_of_no_known_framework_detects_none(self, tmp_path):
        root = str(tmp_path)
        _write(os.path.join(root, 'Makefile'), 'all:\n\techo hi\n')
        _write(os.path.join(root, 'main.c'), 'int main(){return 0;}\n')
        _write(os.path.join(root, 'composer.json'), '{}')
        assert purlin_frameworks.detect_frameworks(root) == []


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

class TestGate:

    def test_each_gate_derives_its_own_defaults(self):
        for gate, strength, breaks in (
                ('passed', None, False),
                ('strong', 70, True),
                ('signed', 80, True)):
            cfg = purlin_gate.resolve_gate({'gate': gate,
                                            'mutation_engine': 'auto'})
            assert (cfg.gate, cfg.min_strength, cfg.breaks) == (
                gate, strength, breaks)

    def test_a_config_that_names_no_engine_runs_no_breaks(self):
        for gate in ('passed', 'strong', 'signed'):
            cfg = purlin_gate.resolve_gate({'gate': gate})
            assert cfg.mutation_engine == 'none', gate
            assert cfg.breaks is False, gate

    def test_the_settings_written_out_are_the_ones_a_project_can_name(self):
        written = purlin_gate.resolve_gate({'gate': 'signed'}).as_dict()
        assert sorted(written) == [
            'audit_parallel', 'ci', 'gate', 'min_strength', 'mutation_engine',
            'trust']

    def test_a_named_key_overrides_the_derived_default(self):
        cfg = purlin_gate.resolve_gate({'gate': 'strong', 'min_strength': 95})
        assert cfg.min_strength == 95

    def test_an_empty_minimum_is_read_as_none_and_warns_of_nothing(self):
        cfg = purlin_gate.resolve_gate({'gate': 'strong', 'min_strength': None})
        assert cfg.min_strength is None
        assert cfg.warnings == []
        named = purlin_gate.resolve_gate({'gate': 'strong',
                                          'min_strength': 'high'})
        assert named.min_strength == 70
        assert any('"min_strength" is not a number' in line
                   for line in named.warnings)

    def test_an_unreadable_gate_falls_back_loudly(self):
        cfg = purlin_gate.resolve_gate({'gate': 'stronng'})
        assert cfg.gate == 'passed'
        assert any('stronng' in w for w in cfg.warnings), cfg.warnings

    def test_retired_keys_are_ignored_with_one_directive(self):
        cfg = purlin_gate.resolve_gate({
            'gate': 'passed', 'spec_dir': 'elsewhere',
            'audit_criteria': 'team://custom-standards'})
        retired = [w for w in cfg.warnings if 'purlin:init --update' in w]
        assert len(retired) == 1, cfg.warnings
        for key in ('spec_dir', 'audit_criteria'):
            assert key in retired[0], retired[0]

    def test_trust_is_local_or_remote_and_defaults_to_local(self):
        assert purlin_gate.resolve_gate({}).trust == 'local'
        assert purlin_gate.resolve_gate({'trust': 'remote'}).trust == 'remote'
        cfg = purlin_gate.resolve_gate({'trust': 'whenever'})
        assert cfg.trust == 'local'
        assert any('trust' in w for w in cfg.warnings), cfg.warnings

    def test_the_hook_setting_is_a_key_this_release_does_not_read(self):
        cfg = purlin_gate.resolve_gate({'pre_push': 'on'})
        assert any('purlin:init --update' in w for w in cfg.warnings), \
            cfg.warnings

    def test_a_level_is_the_lower_of_its_tag_and_the_gate(self):
        level_of = purlin_gate.level_of
        for marked, gate, level in ((None, 'passed', 'passed'),
                                    (None, 'strong', 'strong'),
                                    (None, 'signed', 'signed'),
                                    ('passed', 'signed', 'passed'),
                                    ('strong', 'signed', 'strong'),
                                    ('signed', 'strong', 'strong'),
                                    ('signed', 'passed', 'passed'),
                                    ('often', 'signed', 'signed')):
            assert level_of(marked, gate) == level, (marked, gate)


# ---------------------------------------------------------------------------
# The sources
# ---------------------------------------------------------------------------

class TestTheSources:

    # purlin: states PROOF-5
    def test_a_current_section_from_either_source_counts_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            for source in ('ci', 'local'):
                made = Project(gate=gate)
                try:
                    made.evidence([_entry('PROOF-2', 'RULE-2')],
                                  source=source, ci=source == 'ci')
                    cell = made.cell('RULE-2', 'passed')
                    assert cell['word'] == 'passed', (gate, source, cell)
                    assert cell['source'] == source, (gate, source, cell)
                    assert cell['counts'] is True, (gate, source, cell)
                finally:
                    made.close()


# ---------------------------------------------------------------------------
# The cells
# ---------------------------------------------------------------------------

def _section(source='ci', os_name='linux', statuses=None, current=True,
             at='2026-09-13T12:00:00Z', commit='a' * 40, out_of_date=()):
    """One checked section, as `evidence.checked_sections` hands it over."""
    statuses = statuses or {'PROOF-1': 'pass'}
    return {'source': source, 'os': os_name,
            'path': '.purlin/evidence/%s/login.json' % source,
            'current': current, 'out_of_date': list(out_of_date),
            'section': {'commit': commit, 'at': at,
                        'proofs': [{'id': proof_id, 'rule': 'RULE-1',
                                    'result': status}
                                   for proof_id, status in statuses.items()]}}


STRONG_INPUT = {
    'proofs': [{'id': 'PROOF-1', 'env': None, 'text': 'x',
                'findings': [], 'tests': [{'file': 'tests/t.py',
                                           'name': 'test_x'}]}],
    'sections': [_section()],
    'test_strength': 90,
}


def _audit(word='strong', findings=(), **extra):
    """An audit entry for the rule's current hashes, as the payload hands it."""
    entry = {'verdict': word, 'findings': list(findings),
             'path': '.purlin/evidence/local/login.json'}
    entry.update(extra)
    return entry


def _strong(cfg=None, **overrides):
    """One rule's strong cell, built straight from its evidence."""
    inp = dict(STRONG_INPUT)
    inp.update(overrides)
    cfg = cfg or purlin_gate.resolve_gate({'gate': 'strong'})
    return purlin_states.rule_cells(inp, cfg)['cells']['strong']


class TestARuleWithNoProof:

    # purlin: states PROOF-1
    def test_no_proof_written_reads_no_test(self, project):
        project.spec('# Feature: login\n\n## Rules\n\n- RULE-1: It works\n'
                     '- RULE-2: It fails\n\n## Proof\n\n'
                     '- PROOF-1 (RULE-2): Call it; verify 401\n')
        rule = project.rule('RULE-1')
        cell = rule['cells']['passed']
        assert cell['word'] == 'no test', cell
        assert cell['reasons'] == ['no proof written'], cell
        assert rule['proofs'] == []
        assert rule['flags']['no_proof'] is True
        assert project.rule('RULE-2')['flags']['no_proof'] is False

    # purlin: states PROOF-77
    def test_a_test_marked_with_the_rule_answers_the_passed_cell(self,
                                                                 project):
        project.spec('# Feature: login\n\n> Scope: src/login.py\n\n'
                     '## Rules\n\n- RULE-1: It works\n- RULE-2: It fails\n\n'
                     '## Proof\n\n')
        project.evidence([{'id': 'RULE-1', 'rule': 'RULE-1', 'status': 'pass'},
                          {'id': 'RULE-2', 'rule': 'RULE-2', 'status': 'fail'}],
                         commit_it=False)
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'
        assert project.cell('RULE-2', 'passed')['word'] == 'failed'
        project.evidence([], commit_it=False)
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'no test', cell
        assert cell['reasons'] == ['no proof written'], cell

    # purlin: states PROOF-78
    def test_above_passed_a_rule_with_a_test_and_no_proof_reads_no_proof(
            self):
        rule_spec = ('# Feature: login\n\n> Scope: src/login.py\n\n'
                     '## Rules\n\n- RULE-1: It works\n'
                     '- RULE-2: It is quick [level: passed]\n\n## Proof\n\n')
        project = Project(spec=rule_spec, gate='strong')
        try:
            project.evidence([{'id': 'RULE-1', 'rule': 'RULE-1',
                               'status': 'pass'},
                              {'id': 'RULE-2', 'rule': 'RULE-2',
                               'status': 'pass'}], commit_it=False)
            first = project.rule('RULE-1')
            assert first['cells']['passed']['word'] == 'passed'
            assert first['cells']['strong']['word'] == 'no proof'
            assert first['cells']['strong']['reasons'] == [
                'the rule has a test and no proof']
            assert first['meets_gate'] is False
            second = project.rule('RULE-2')
            assert sorted(second['cells']) == ['passed'], second
            assert second['meets_gate'] is True
        finally:
            project.close()


class TestThePassedCell:

    # purlin: states PROOF-3
    def test_a_local_section_meets_level_one_under_the_passed_gate(self,
                                                                  project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed'
        assert (cell['source'], cell['current'], cell['counts']) == (
            'local', True, True)

    # purlin: states PROOF-4
    def test_a_ci_section_meets_level_one(self, project):
        project.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                           'status': 'pass'}], ci=True)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed'
        assert cell['source'] == 'ci'

    # purlin: states PROOF-6
    def test_a_local_section_counts_under_strong_and_signed(self):
        for gate in ('strong', 'signed'):
            made = Project(gate=gate)
            try:
                made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}], runner='dev',
                              source='local')
                cell = made.cell('RULE-2', 'passed')
                assert cell['word'] == 'passed', cell
                assert cell['source'] == 'local'
                assert cell['counts'] is True
                assert cell['reasons'] == [], cell
            finally:
                made.close()

    # purlin: states PROOF-7
    def test_an_uncommitted_run_counts_and_a_report_alone_does_not(
            self):
        made = Project(gate='signed')
        try:
            _write(os.path.join(made.root, '.purlin', 'runtime', 'reports',
                                'pytest.xml'),
                   '<testsuite><testcase classname="tests.test_login" '
                   'name="test_proof_2"/></testsuite>')
            assert made.cell('RULE-2', 'passed')['word'] == 'no test', (
                'a report is not evidence')
            made.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False)
            cell = made.cell('RULE-2', 'passed')
            assert cell['word'] == 'passed', cell
            assert cell['source'] == 'local'
            assert cell['counts'] is True
            assert cell['reasons'] == [], cell
        finally:
            made.close()

    # purlin: states PROOF-8
    def test_an_env_proof_needs_a_section_from_that_operating_system(
            self, project):
        project.spec(
            '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
            '- RULE-1: Files lock\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Lock a file; verify a second open '
            'returns 0 handles @env(windows)\n')
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], os_name='linux')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'not run'
        assert cell['missing_env'] == ['windows'], cell
        assert 'windows: no run yet' in cell['reasons'], cell
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], os_name='windows',
                         at='2026-09-13T13:00:00Z')
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'

    # purlin: states PROOF-9
    def test_out_of_date_when_the_code_moved(self, project):
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}])
        seen = _git(project.root, 'rev-parse', 'HEAD~1').stdout.strip()
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 200  # rewritten\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'refactor: login')
        rule = project.rule('RULE-1')
        cell = rule['cells']['passed']
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['code changed since %s' % seen[:7]], cell
        assert cell['current'] is False, cell
        assert rule['flags']['out_of_date'] is True
        assert rule['meets_gate'] is False

    # purlin: states PROOF-9
    def test_a_spec_edit_and_a_test_edit_leave_it_out_of_date_too(self,
                                                                  project):
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               'import pytest\n\n# purlin: login PROOF-1\n'
               'def test_proof_1():\n    assert True\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'test(login): proof 1')
        project.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                           'status': 'pass'}], commit_it=False)
        seen = project.head()
        project.spec(SPEC.replace('return 200 with a session token',
                                  'return 200 and a session token'))
        cell = project.cell('RULE-1', 'passed')
        assert cell['reasons'] == ['spec changed since %s' % seen[:7]], cell
        project.spec(SPEC)
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               'import pytest\n\n# purlin: login PROOF-1\n'
               'def test_proof_1():\n    assert 1\n')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'out of date', cell
        assert cell['reasons'] == ['tests changed since %s' % seen[:7]], cell

    # purlin: states PROOF-10
    def test_a_rule_no_test_backs_reads_no_test(self, project):
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'no test'
        assert (cell['source'], cell['current'], cell['counts']) == (
            None, False, False)


class TestTheStrongCell:

    # purlin: states PROOF-12
    def test_a_cell_above_the_gate_is_absent(self):
        expected = {'passed': ['passed'],
                    'strong': ['passed', 'strong'],
                    'signed': ['passed', 'strong', 'signed']}
        for gate, names in expected.items():
            made = Project(gate=gate)
            try:
                rule = made.rule('RULE-1')
                assert sorted(rule['cells']) == sorted(names), (gate, rule)
            finally:
                made.close()

    # purlin: states PROOF-13
    def test_a_rule_that_did_not_pass_is_weak_for_that_one_reason(self):
        made = Project(gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], ci=True, strength=48)
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'weak'
            assert cell['reasons'] == ['not passed'], cell
            assert cell['strength'] == 48, cell
        finally:
            made.close()

    # purlin: states PROOF-14
    def test_a_strength_under_the_minimum_is_weak_and_says_so(self):
        made = Project(gate='strong', extra_config={'mutation_engine': 'auto'})
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=48)
            made.audit('RULE-1')
            cell = made.cell('RULE-1', 'strong')
            assert cell['word'] == 'weak'
            assert cell['reasons'] == ['strength 48% under 70%'], cell
            assert cell['findings'] == [], cell
        finally:
            made.close()

    # purlin: states PROOF-15
    def test_with_no_score_the_cell_says_no_mutation_score_was_measured(self):
        made = Project(gate='strong')
        try:
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=None)
            made.audit('RULE-2')
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'strong', cell
            assert cell['reasons'] == ['no mutation score measured'], cell
            # A loosely worded proof decides nothing by its wording: the
            # strong cell is the audit's.
            made.spec(SPEC.replace(
                'POST /login with a bad password; verify 401 and the '
                'body "denied"', 'Check that the login handles it properly'))
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=None)
            made.audit('RULE-2')
            loose = made.rule('RULE-2')
            assert loose['cells']['strong']['word'] == 'strong', loose
        finally:
            made.close()

    # purlin: states PROOF-16
    def test_a_field_the_format_does_not_name_decides_nothing(self):
        # An entry carrying a field the evidence format does not name, here
        # a sentence about the test body, is read for its `verdict` and its
        # `findings` alone, so an entry that found nothing leaves the cell
        # strong.
        cell = _strong(audit=_audit(
            tests=[{'proof': 'PROOF-1',
                    'notes': ['The marked test body holds no assertion.']}]))
        assert cell['word'] == 'strong', cell
        assert cell['findings'] == [], cell
        assert cell['evidence'] == '.purlin/evidence/local/login.json', cell
        found = _strong(audit=_audit('weak', [
            'The test reads the status code alone.']))
        assert found['word'] == 'weak', found
        assert found['reasons'] == [
            'The test reads the status code alone.'], found

    # purlin: states PROOF-17
    def test_the_audit_entry_settles_level_two_where_the_level_asks(self):
        assert _strong()['word'] == 'not audited'
        assert _strong()['reasons'] == ['no audit has run on this code']
        open_question = _strong(audit=_audit('undecided', [
            'The test body is not shown, so PROOF-1 cannot be read.']))
        assert open_question['word'] == 'weak', open_question
        assert open_question['reasons'] == [
            'the AI audit could not decide: The test body is not shown, so '
            'PROOF-1 cannot be read.'], open_question
        silent = _strong(audit=_audit('undecided'))
        assert silent['reasons'] == ['the AI audit could not decide'], silent
        settled = _strong(audit=_audit('strong'))
        assert settled['word'] == 'strong', settled

    # purlin: states PROOF-18
    def test_a_passed_level_is_never_owed_an_audit(self):
        cfg = purlin_gate.resolve_gate({'gate': 'strong'})
        lower = purlin_states.rule_cells(
            dict(STRONG_INPUT, level_marked='passed'), cfg)
        assert sorted(lower['cells']) == ['passed'], lower
        assert lower['flags']['not_audited'] is False, lower
        assert lower['meets_gate'] is True, lower
        assert _strong()['word'] == 'not audited'
        assert _strong(level_marked='signed')['word'] == 'not audited'

    # purlin: states PROOF-19
    def test_a_manual_proof_asks_for_a_manual_test(self):
        cell = _strong(proofs=[
            {'id': 'PROOF-1', 'manual': True, 'env': None, 'text': 'x',
             'findings': [], 'tests': []}])
        assert cell['word'] == 'manual test'
        assert cell['reasons'] == ['manual proof'], cell

    # purlin: states PROOF-23
    def test_a_strong_cell_with_an_engine_carries_no_reasons(self):
        made = Project(gate='strong', extra_config={'mutation_engine': 'auto'})
        try:
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=90)
            made.audit('RULE-2')
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'strong'
            assert cell['reasons'] == [], cell
        finally:
            made.close()


class TestTheAuditOnTheRule:
    """What the AI audit left decides the strong cell, and every rule shows it."""

    # purlin: states PROOF-70
    def test_with_mutation_off_a_strength_left_behind_is_not_compared(self):
        made = Project(gate='strong', extra_config={'mutation_engine': 'none'})
        try:
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=40)
            made.audit('RULE-2')
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'strong', cell
            assert cell['reasons'] == ['no mutation score measured'], cell
        finally:
            made.close()

    # purlin: states PROOF-71
    def test_a_rule_the_model_could_not_be_reached_for_says_why(self):
        made = Project(gate='strong')
        try:
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True)
            rule = made.rule('RULE-2')
            _write(os.path.join(made.root, '.purlin', 'runtime',
                                'audit_could_not_run.json'),
                   json.dumps({'login': {'RULE-2': {
                       'rule_hash': rule['rule_hash'],
                       'proof_hash': rule['proof_hash'],
                       'test_hash': rule['test_hash'],
                       'why': 'claude is not on PATH'}}}))
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'not audited', cell
            assert cell['reasons'] == [
                'the AI audit could not run: claude is not on PATH'], cell
            made.spec(SPEC.replace('return 401 and the body "denied"',
                                   'return 403 and the body "denied"'))
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True)
            cell = made.cell('RULE-2', 'strong')
            assert cell['reasons'] == ['no audit has run on this code'], cell
        finally:
            made.close()

    # purlin: states PROOF-72
    def test_a_fresh_finding_stales_the_signature_and_says_so(self):
        made = Project(gate='signed')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], ci=True)
            made.audit('RULE-1')
            made.signature('RULE-1')
            assert made.cell('RULE-1', 'signed')['word'] != 'stale'
            made.audit('RULE-1',
                       observations=['PROOF-2 reads the status alone.'])
            cell = made.cell('RULE-1', 'signed')
            assert cell['word'] == 'stale', cell
            assert cell['reasons'] == [
                'audit findings changed after the signature'], cell
        finally:
            made.close()

    # purlin: states PROOF-73
    def test_every_rule_carries_its_audit_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            made = Project(gate=gate)
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'pass'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}])
                made.audit('RULE-2', observations=['PROOF-2 reads 401 alone.'])
                audit = made.rule('RULE-2')['audit']
                assert sorted(audit) == ['at', 'commit', 'findings', 'model',
                                         'path', 'strength', 'verdict'], audit
                assert audit['verdict'] == 'weak', (gate, audit)
                assert audit['findings'] == ['PROOF-2 reads 401 alone.']
                assert audit['model'] == 'unknown', audit
                assert audit['strength'] == 90, audit
                assert audit['path'] == '.purlin/evidence/local/login.json'
                assert made.rule('RULE-1')['audit'] is None, gate
            finally:
                made.close()


class TestHoldsAndSignatures:
    """What a person's committed attestation does to the top two cells."""

    @staticmethod
    def _signed_project():
        made = Project(gate='signed')
        made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                       {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                      ci=True, strength=90)
        # RULE-1 is marked `signed` and RULE-2 takes the gate, so both are at
        # the level `signed`: the AI audit is owed on each, and the strong
        # cell reads `not audited` until an audit entry exists.
        made.audit('RULE-1')
        made.audit('RULE-2')
        return made

    # purlin: states PROOF-22
    def test_a_signature_for_the_current_hashes_clears_the_hand_check(self):
        cfg = purlin_gate.resolve_gate({'gate': 'signed'})
        manual = [{'id': 'PROOF-1', 'manual': True, 'env': None, 'text': 'x',
                   'tests': []}]
        inp = dict(STRONG_INPUT, proofs=manual, audit_hash='a' * 64)
        before = purlin_states.rule_cells(inp, cfg)
        assert before['cells']['strong']['word'] == 'manual test', before
        assert before['need'] == 'hand check', before
        signature = {'rule_hash': None, 'proof_hash': None, 'test_hash': None,
                     'audit_hash': 'a' * 64, 'counts': True,
                     'signer': 'jane@acme.com', 'path': 'x.json'}
        after = purlin_states.rule_cells(dict(inp, signatures=[signature]),
                                         cfg)
        assert after['cells']['strong']['word'] == 'strong', after
        assert after['cells']['signed']['word'] == 'signed', after
        assert after['need'] is None, after

    # purlin: states PROOF-24
    def test_a_signature_is_read_until_the_hashes_move_under_it(self):
        made = self._signed_project()
        try:
            made.sign_commits()
            made.signature('RULE-1')
            cell = made.cell('RULE-1', 'signed')
            assert cell['word'] == 'signed', cell
            assert cell['reasons'] == ['by jane@acme.com'], cell
            made.spec(SPEC.replace('return 200 with a session token',
                                   'return 201 with a session token'))
            rule = made.rule('RULE-1')
            assert rule['cells']['signed']['word'] == 'stale'
            assert rule['cells']['signed']['reasons'] == [
                'hashes changed after the signature'], rule
            assert rule['flags']['stale'] is True
        finally:
            made.close()

    # purlin: states PROOF-25
    def test_a_signature_is_needed_where_the_level_is_signed(self):
        made = self._signed_project()
        try:
            made.spec(SPEC.replace(
                '- RULE-2: Invalid credentials return 401 and the body '
                '"denied"',
                '- RULE-2: Invalid credentials return 401 and the body '
                '"denied" [level: strong]'))
            # The tag is part of the spec the evidence is checked against, so
            # the tests run again; the rule text did not change, so the audit
            # entries still bind.
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], ci=True, strength=90)
            lower = made.rule('RULE-2')
            assert lower['level'] == 'strong', lower
            assert lower['cells']['strong']['word'] == 'strong', lower
            assert 'signed' not in lower['cells'], lower
            assert (lower['meets_gate'], lower['blocked_by']) == (True, None)
            higher = made.rule('RULE-1')
            assert higher['level'] == 'signed', higher
            assert higher['cells']['signed']['word'] == 'unsigned', higher
            assert (higher['meets_gate'], higher['blocked_by']) == (
                False, 'signed')
        finally:
            made.close()

    # purlin: states PROOF-26
    def test_an_unsigned_signing_commit_leaves_the_rule_unsigned(self):
        made = self._signed_project()
        try:
            made.signature('RULE-1')
            cell = made.cell('RULE-1', 'signed')
            assert cell['word'] == 'unsigned', cell
            assert cell['reasons'] == [
                'the signing commit is not signed'], cell
        finally:
            made.close()


# One project holding one rule at each of the five buckets, so the bucket, the
# gate and the review list are all read off the same evidence.
FIVE = (
    '# Feature: ledger\n\n'
    '> Description: Five rules, one per bucket.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: A rule with no proof names none [level: passed]\n'
    '- RULE-2: A failing rule has a test that fails [level: passed]\n'
    '- RULE-3: A passed rule has no audit yet\n'
    '- RULE-4: A strong rule has no signature yet\n'
    '- RULE-5: A signed rule carries one\n\n'
    '## Proof\n\n'
    '- PROOF-2 (RULE-2): POST /session with the password "wrong"; verify 401\n'
    '- PROOF-3 (RULE-3): POST /session with the password "secret"; verify 200 '
    'and a rejected second attempt\n'
    '- PROOF-4 (RULE-4): POST /session 5 times with a wrong password; verify '
    '423 and an error body\n'
    '- PROOF-5 (RULE-5): POST /session with no body at all; verify 400 and an '
    'error body\n'
)


def _five_bucket_project():
    """A `signed` project with one rule in each of the five buckets."""
    made = Project(gate='signed', spec=None)
    made.spec(FIVE, name='ledger', category='core')
    _git(made.root, 'add', '-A')
    _git(made.root, 'commit', '-q', '-m', 'docs: the spec under test')
    made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'fail'},
                   {'id': 'PROOF-3', 'rule': 'RULE-3', 'status': 'pass'},
                   {'id': 'PROOF-4', 'rule': 'RULE-4', 'status': 'pass'},
                   {'id': 'PROOF-5', 'rule': 'RULE-5', 'status': 'pass'}],
                  feature='ledger', ci=True, strength=90)
    # RULE-3 is left without an audit entry, so it has only passed. The two
    # rules after it carry an audit entry that settled.
    made.audit('RULE-4', feature='ledger')
    made.audit('RULE-5', feature='ledger')
    made.sign_commits()
    made.signature('RULE-5', feature='ledger', category='core')
    return made


# ---------------------------------------------------------------------------
# The platforms in the passed cell
# ---------------------------------------------------------------------------

ENV_SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in with an email and a password.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200 and a '
    'token\n'
    '- PROOF-2 (RULE-1): On Windows, POST /login with valid credentials and '
    'read the token file; verify it holds exactly the 200 response\'s token '
    'value @env(windows)\n'
)


class TestThePlatformsInThePassedCell:

    # purlin: states PROOF-51
    def test_one_entry_per_operating_system_a_current_section_covers(self):
        made = Project(gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}],
                          os_name='linux', source='ci')
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}],
                          os_name='windows', source='ci',
                          at='2026-09-13T13:00:00Z')
            cell = made.cell('RULE-1', 'passed')
            assert sorted(cell['platforms']) == ['linux', 'windows'], cell
            assert cell['platforms']['linux'] == {
                'word': 'passed', 'source': 'ci',
                'at': '2026-09-13T12:00:00Z'}, cell
            assert cell['platforms']['windows'] == {
                'word': 'passed', 'source': 'ci',
                'at': '2026-09-13T13:00:00Z'}, cell
            assert cell['word'] == 'passed', cell
        finally:
            made.close()

    # purlin: states PROOF-52
    def test_a_platform_a_proof_asks_for_and_nothing_ran_on_is_listed(self):
        made = Project(spec=ENV_SPEC, gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}],
                          os_name='linux', source='ci')
            cell = made.cell('RULE-1', 'passed')
            assert cell['platforms']['windows'] == {
                'word': 'not run', 'source': None, 'at': None}, cell
            assert cell['platforms']['linux']['word'] == 'passed', cell
        finally:
            made.close()

    # purlin: states PROOF-53
    def test_platforms_that_disagree_read_partial(self):
        made = Project(spec=ENV_SPEC, gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}],
                          os_name='linux', source='ci')
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-1',
                            'status': 'fail'}],
                          os_name='windows', source='ci',
                          at='2026-09-13T13:00:00Z')
            rule = made.rule('RULE-1')
            cell = rule['cells']['passed']
            assert cell['word'] == 'partial', cell
            assert cell['reasons'] == ['passed on linux',
                                       'windows: failed'], cell
            assert rule['bucket'] == 'partial', rule['bucket']
            assert rule['flags']['partial'] is True, rule['flags']
            assert rule['flags']['failing'] is False, rule['flags']
            assert rule['meets_gate'] is False
            assert rule['blocked_by'] == 'passed'
        finally:
            made.close()

    # purlin: states PROOF-54
    def test_an_older_section_that_is_out_of_date_is_not_read(self):
        """A failing section two edits old says nothing about this code."""
        cell = purlin_states.rule_cells({
            'proofs': STRONG_INPUT['proofs'],
            'sections': [
                _section('ci', 'linux', {'PROOF-1': 'fail'}, current=False,
                         at='2026-09-01T00:00:00Z', out_of_date=['code']),
                _section('local', 'macos', {'PROOF-1': 'pass'},
                         at='2026-09-02T00:00:00Z')],
            'level_marked': 'passed',
        }, purlin_gate.resolve_gate({'gate': 'strong'}))['cells']['passed']
        assert cell['word'] == 'passed', cell
        assert sorted(cell['platforms']) == ['macos'], cell

    # purlin: states PROOF-50
    def test_a_file_whose_source_field_disagrees_is_left_out(self):
        made = Project(gate='strong')
        try:
            path = made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                   'status': 'pass'}],
                                 source='ci', claimed_source='local')
            data = made.payload()
            assert made.cell('RULE-1', 'passed')['word'] != 'passed'
            named = [w for w in data['warnings'] if path in w]
            assert len(named) == 1, data['warnings']
            assert 'it is ignored' in named[0], named
        finally:
            made.close()

    # purlin: states PROOF-66
    def test_a_persons_own_section_answers_for_its_platform_at_every_gate(
            self):
        """A local section is a platform's answer at `signed` as at `strong`.

        Both sources count at every gate, so a red macOS section beside a
        green Linux one reads `partial` wherever the gate is set, and a local
        section alone reads `passed`.
        """
        def cells(gate, sections):
            return purlin_states.rule_cells({
                'proofs': STRONG_INPUT['proofs'], 'sections': sections,
                'level_marked': 'passed',
            }, purlin_gate.resolve_gate({'gate': gate}))['cells']['passed']

        linux = _section('ci', 'linux', {'PROOF-1': 'pass'},
                         at='2026-09-25T12:00:00Z')
        macos = _section('local', 'macos', {'PROOF-1': 'fail'},
                         at='2026-09-26T12:00:00Z')
        for gate in ('strong', 'signed'):
            cell = cells(gate, [linux, macos])
            assert cell['word'] == 'partial', (gate, cell)
            assert sorted(cell['platforms']) == ['linux', 'macos'], cell

        alone = cells('signed', [_section('local', 'macos')])
        assert alone['word'] == 'passed', alone
        assert alone['counts'] is True, alone
        assert alone['reasons'] == [], alone

    # purlin: states PROOF-55
    def test_a_passed_level_has_no_strong_cell_whatever_the_audit_found(self):
        cfg = purlin_gate.resolve_gate({'gate': 'signed'})
        found = {'verdict': 'weak', 'findings': ['PROOF-1 reads 200 alone.'],
                 'path': '.purlin/evidence/local/login.json'}
        for audit in (None, found, dict(found, verdict='strong',
                                        findings=[])):
            result = purlin_states.rule_cells({
                'proofs': STRONG_INPUT['proofs'],
                'sections': [_section('local', 'macos')],
                'level_marked': 'passed', 'audit': audit,
            }, cfg)
            assert sorted(result['cells']) == ['passed'], (audit, result)
            assert result['bucket'] == 'passed', (audit, result)
            assert result['flags']['not_audited'] is False, result
            assert result['meets_gate'] is True, result
        unmarked = purlin_states.rule_cells({
            'proofs': STRONG_INPUT['proofs'],
            'sections': [_section('local', 'macos')], 'audit': found,
        }, cfg)
        assert unmarked['cells']['strong']['word'] == 'weak', unmarked


class TestBucketsAndTheGate:

    # purlin: states PROOF-27
    def test_one_rule_in_each_of_the_five_buckets(self):
        made = _five_bucket_project()
        try:
            buckets = [made.rule('RULE-%d' % n, 'ledger')['bucket']
                       for n in range(1, 6)]
            assert buckets == ['untested', 'failing', 'passed', 'strong',
                               'signed'], buckets
        finally:
            made.close()

    # purlin: states PROOF-27
    def test_partial_sits_between_failing_and_passed(self):
        assert purlin_states.bucket_keys('signed') == [
            'untested', 'failing', 'partial', 'passed', 'strong', 'signed']
        assert purlin_states.bucket_keys('passed') == [
            'untested', 'failing', 'partial', 'passed']

    # purlin: states PROOF-28
    def test_the_gate_is_met_by_one_of_them_and_blocked_by_name(self):
        made = _five_bucket_project()
        try:
            rules = [made.rule('RULE-%d' % n, 'ledger') for n in range(1, 6)]
            assert [r['meets_gate'] for r in rules] == [
                False, False, False, False, True]
            assert [r['blocked_by'] for r in rules] == [
                'passed', 'passed', 'strong', 'signed', None]
        finally:
            made.close()


class TestLevels:

    # purlin: states PROOF-59
    def test_a_level_is_the_tag_under_the_gate_or_the_gate(self):
        spec = SPEC.replace(
            '[level: signed]', '[level: passed]').replace(
            '"denied"\n\n', '"denied" [level: signed]\n\n', 1).replace(
            '## Proof', '- RULE-3: A locked account returns 423\n\n## Proof', 1)
        made = Project(spec=spec, gate='strong')
        try:
            rules = [made.rule('RULE-%d' % n) for n in (1, 2, 3)]
            assert [r['level'] for r in rules] == [
                'passed', 'strong', 'strong'], rules
            assert [r['level_marked'] for r in rules] == [
                'passed', 'signed', None], rules
            made.config_value('gate', 'signed')
            assert [made.rule('RULE-%d' % n)['level'] for n in (1, 2, 3)] == [
                'passed', 'signed', 'signed']
        finally:
            made.close()

    # purlin: states PROOF-61
    def test_the_level_decides_which_cells_block(self):
        def retag(made, tag):
            made.spec(SPEC.replace('"denied"\n\n', '"denied"%s\n\n' % tag, 1))
            made.evidence([{'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}], strength=None)
            return made.rule('RULE-2')

        made = Project(gate='signed')
        try:
            rule = retag(made, ' [level: passed]')
            assert sorted(rule['cells']) == ['passed'], rule
            assert rule['cells']['passed']['word'] == 'passed', rule
            assert (rule['meets_gate'], rule['blocked_by']) == (True, None)
            rule = retag(made, ' [level: strong]')
            assert sorted(rule['cells']) == ['passed', 'strong'], rule
            assert rule['cells']['strong']['word'] == 'not audited', rule
            assert (rule['meets_gate'], rule['blocked_by']) == (
                False, 'strong')
            made.audit('RULE-2')
            rule = made.rule('RULE-2')
            assert rule['cells']['strong']['word'] == 'strong', rule
            assert (rule['meets_gate'], rule['blocked_by']) == (True, None)
            rule = retag(made, '')
            assert rule['level'] == 'signed', rule
            assert (rule['meets_gate'], rule['blocked_by']) == (
                False, 'signed')
        finally:
            made.close()


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


class TestALevelAsksItsOwnQuestions:

    # purlin: states PROOF-89
    def test_a_rule_has_only_the_cells_its_level_asks_for(self):
        made = _levels_project()
        try:
            rules = {n: made.rule('RULE-%d' % n) for n in (1, 2, 3)}
            assert [rules[n]['level'] for n in (1, 2, 3)] == [
                'passed', 'strong', 'signed']
            assert list(rules[1]['cells']) == ['passed'], rules[1]
            assert sorted(rules[2]['cells']) == ['passed', 'strong'], rules[2]
            assert sorted(rules[3]['cells']) == [
                'passed', 'signed', 'strong'], rules[3]
            for rule in rules.values():
                assert None not in rule['cells'].values(), rule
                assert rule['cells']['passed']['word'] == 'passed', rule
            assert rules[2]['cells']['strong']['word'] == 'strong', rules[2]
            assert rules[3]['cells']['signed']['word'] == 'unsigned', rules[3]
            assert [rules[n]['bucket'] for n in (1, 2, 3)] == [
                'passed', 'strong', 'strong']
            assert [rules[n]['meets_gate'] for n in (1, 2, 3)] == [
                True, True, False]
        finally:
            made.close()

    # purlin: states PROOF-90
    def test_the_rollup_counts_the_rules_each_question_is_asked_of(self):
        made = _levels_project()
        try:
            data = made.payload()
            rollup = data['features'][0]['rollup']
            for counted in (rollup, data['summary']):
                assert (counted['asks_strong'], counted['asks_signed']) == (
                    3, 1), counted
                assert (counted['strong'], counted['signed']) == (2, 0), counted
                assert counted['not_audited'] == 0, counted
            made.config_value('gate', 'strong')
            rollup = made.payload()['features'][0]['rollup']
            assert rollup['asks_strong'] == 3, rollup
            assert 'asks_signed' not in rollup, rollup
        finally:
            made.close()

    # purlin: states PROOF-91
    def test_the_table_counts_strong_and_signed_over_the_rules_asked(self):
        made = _levels_project()
        try:
            data = made.payload()
            row = purlin_status._row(data['features'][0], 'signed')
            assert row[-2:] == ('2 of 3 · 90%', '0 of 1'), row
            made.spec(ONE_PASSED_SPEC, name='notes', category='notes')
            notes = next(f for f in made.payload()['features']
                         if f['name'] == 'notes')
            row = purlin_status._row(notes, 'signed')
            assert row[-2:] == ('', ''), row
        finally:
            made.close()

    # purlin: states PROOF-92
    def test_a_rule_whose_test_fails_reads_its_passed_cell(self):
        made = _levels_project()
        try:
            lower = made.rule('RULE-4')
            assert list(lower['cells']) == ['passed'], lower
            assert lower['cells']['passed']['word'] == 'failed', lower
            assert (lower['bucket'], lower['blocked_by']) == (
                'failing', 'passed'), lower
            middle = made.rule('RULE-5')
            assert middle['cells']['strong']['word'] == 'weak', middle
            assert middle['cells']['strong']['reasons'] == ['not passed'], (
                middle)
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The payload
# ---------------------------------------------------------------------------

class TestPayload:

    # purlin: states PROOF-31
    def test_schema_nine_carries_the_documented_top_level(self, project):
        data = project.payload()
        assert data["schema_version"] == 9
        for key in ('generated_at', 'generated_by', 'project', 'version',
                    'commit', 'dirty', 'gate', 'summary', 'features',
                    'queue', 'evidence', 'tag',
                    'remote_url', 'warnings'):
            assert key in data, key
        assert data['gate']['gate'] == 'passed'
        assert data['generated_at'].endswith('Z')
        # A project with no remote gets null rather than a broken link.
        assert data['remote_url'] is None
        _git(project.root, 'remote', 'add', 'origin',
             'https://github.com/acme/ledger.git')
        assert project.payload()['remote_url'] == (
            'https://github.com/acme/ledger.git')

    # purlin: states PROOF-32
    def test_a_feature_carries_its_rules_with_their_tags_and_proofs(self,
                                                                   project):
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
        assert feature['spec_path'] == 'specs/auth/login.md'
        assert feature['category'] == 'auth'
        assert feature['signatures'] == []
        rule = next(r for r in feature['rules'] if r['id'] == 'RULE-1')
        # The gate is `passed`, so a rule marked `signed` is read as `passed`.
        assert (rule['level'], rule['level_marked']) == ('passed', 'signed')
        assert project.rule('RULE-2')['level_marked'] is None
        assert 'origin' not in rule and 'criterion' not in rule
        assert rule['proofs'][0]['manual'] is False
        assert rule['proofs'][0]['env'] is None
        assert feature['current'] is False
        assert feature['evidence'] == {'local': None, 'ci': None}

    # purlin: states PROOF-32
    def test_a_feature_says_whether_its_evidence_is_current_and_committed(
            self, project):
        project.evidence([_entry('PROOF-2', 'RULE-2')], commit_it=False,
                         os_name='linux')
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
        assert feature['current'] is True
        local = feature['evidence']['local']
        assert local['path'] == '.purlin/evidence/local/login.json'
        assert local['committed'] is False
        assert local['platforms'] == {'linux': {
            'commit': project.head(), 'at': '2026-09-13T12:00:00Z',
            'current': True}}
        assert feature['evidence']['ci'] is None
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'purlin: evidence')
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
        assert feature['evidence']['local']['committed'] is True
        _write(os.path.join(project.root, 'src', 'login.py'), 'x = 1\n')
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
        assert feature['current'] is False
        assert feature['evidence']['local']['platforms']['linux'][
            'current'] is False

    # purlin: states PROOF-29
    def test_the_rollup_counts_the_buckets_the_gate_reaches(self, project):
        _commit_tests(project, 'PROOF-2')
        project.evidence([_entry('PROOF-2', 'RULE-2')])
        data = project.payload()
        feature = next(f for f in data['features'] if f['name'] == 'login')
        rollup = feature['rollup']
        assert sorted(rollup) == sorted([
            'rules', 'met', 'untested', 'failing', 'partial', 'passed',
            'stale', 'manual', 'not_audited',
            'queue', 'hand_checks', 'test_strength', 'proofs',
            'proofs_without_test', 'proofs_without_test_ids',
            'incomplete']), rollup
        assert (rollup['rules'], rollup['met']) == (2, 1)
        assert (rollup['passed'], rollup['untested']) == (1, 1), rollup
        assert (rollup['partial'], rollup['failing']) == (0, 0), rollup
        assert rollup['proofs'] == 2, rollup
        assert rollup['proofs_without_test'] == 1, (
            'PROOF-1 has no test; PROOF-2 was observed by the run')
        assert rollup['proofs_without_test_ids'] == ['PROOF-1'], rollup
        assert data['summary']['features'] == 1

    # purlin: states PROOF-57
    def test_the_proof_counts_call_out_a_proof_with_no_test(self, project):
        project.spec(
            '# Feature: login\n\n> Scope: src/login.py\n\n## Rules\n\n'
            '- RULE-1: Valid credentials return 200 with a session token\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): POST /login with valid credentials; verify '
            '200 and a token\n'
            '- PROOF-2 (RULE-1): POST /login twice; verify the second reply '
            'carries the same token\n'
            '- PROOF-3 (RULE-1): Sign in on the handset and read that the '
            'home screen names the account; verify it reads the email '
            '@manual\n')
        _commit_tests(project, 'PROOF-1')
        project.evidence([_entry('PROOF-1', 'RULE-1')])
        rollup = next(f for f in project.payload()['features']
                      if f['name'] == 'login')['rollup']
        assert rollup['proofs'] == 3, rollup
        assert rollup['proofs_without_test'] == 1, rollup
        assert rollup['proofs_without_test_ids'] == ['PROOF-2'], rollup

    # purlin: states PROOF-84
    def test_a_marked_test_that_has_not_run_is_a_test(self, project):
        path = os.path.join(project.root, 'tests', 'test_login.py')
        _write(path, _marked_tests('PROOF-1'))
        data = project.payload()
        rollup = next(f for f in data['features']
                      if f['name'] == 'login')['rollup']
        for counted in (rollup, data['summary']):
            assert counted['proofs_without_test'] == 1, counted
            assert counted['proofs_without_test_ids'] == ['PROOF-2'], counted
        words = {rule['id']: rule['cells']['passed']['word']
                 for f in data['features'] for rule in f['rules']}
        assert words == {'RULE-1': 'not run', 'RULE-2': 'no test'}, words

        # A marker below the last test is tied to none, so it backs nothing.
        _write(path, 'def test_x():\n    pass\n\n# purlin: login PROOF-1\n')
        rollup = next(f for f in project.payload()['features']
                      if f['name'] == 'login')['rollup']
        assert rollup['proofs_without_test'] == 2, rollup

    # purlin: states PROOF-56
    def test_the_signed_cell_carries_when_it_was_signed(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            made.signature('RULE-2', machine='jane-laptop', os='macos')
            cell = made.cell('RULE-2', 'signed')
            assert cell['signer'] == 'jane@acme.com'
            assert cell['at'] and cell['at'].endswith('Z'), cell
            assert len(cell['at']) == 20, cell
            assert (cell['machine'], cell['os']) == ('jane-laptop', 'macos')
            made.signature('RULE-1')
            other = made.cell('RULE-1', 'signed')
            assert (other['machine'], other['os']) == (None, None), other
        finally:
            made.close()

    # purlin: states PROOF-30
    def test_global_anchor_rules_are_counted_once_in_the_summary(self, project):
        project.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
            name='security', category='_anchors')
        data = project.payload()
        assert data['summary']['rules'] == 3, (
            'two own rules plus the anchor\'s one, counted once')
        assert data['summary']['features'] == 2
        login = next(f for f in data['features'] if f['name'] == 'login')
        assert login['rollup']['rules'] == 3, (
            'the feature must prove the global anchor\'s rule too')

    # purlin: states PROOF-39
    def test_a_section_carries_the_result_of_the_run_it_names(self, project):
        """Two operating systems, one run each: one failed, one passed."""
        project.evidence([{'id': 'PROOF-1', 'status': 'pass'},
                          {'id': 'PROOF-2', 'status': 'fail'}],
                         os_name='linux')
        project.evidence([{'id': 'PROOF-1', 'status': 'pass'},
                          {'id': 'PROOF-2', 'status': 'pass'}],
                         os_name='windows')
        evidence = project.payload()['evidence']['login']
        assert sorted(evidence) == ['local']
        assert evidence['local']['linux']['result'] == 'fail'
        assert evidence['local']['windows']['result'] == 'pass'
        for entry in evidence['local'].values():
            assert len(entry['commit']) == 40
            assert entry['current'] is True
            assert entry['path'] == '.purlin/evidence/local/login.json'

    # purlin: states PROOF-37
    def test_the_data_file_is_a_const_assignment_and_round_trips(self, project):
        data = project.payload()
        path = purlin_payload.write_report_data(project.root, data)
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        assert text.startswith('const PURLIN_DATA = ') and text.endswith(';\n')
        read_back = json.loads(text[len('const PURLIN_DATA = '):-len(';\n')])
        assert read_back['commit'] == data['commit']


class TestTheFixturesAreTheContract:
    """The dashboard's fixtures and the builder's output are one shape.

    `dev/fixtures/report/{solo,team,regulated}.json` are written by hand, and
    the dashboard is built against them. A key the builder adds
    and the fixtures do not carry would render nowhere, so the two are
    compared key by key here rather than by eye.
    """

    FIXTURES = os.path.join(PROJECT_ROOT, 'dev', 'fixtures', 'report')

    @staticmethod
    def _fixture(name):
        with open(os.path.join(TestTheFixturesAreTheContract.FIXTURES,
                               name + '.json'), encoding='utf-8') as handle:
            return json.load(handle)

    # Where a payload keys a map by a name rather than by a field, such as
    # an operating system or a source, every name reads as one path.
    MAPS = ('.evidence', '.evidence.*', '.evidence.*.*',
            '.features[].evidence.ci.platforms',
            '.features[].evidence.local.platforms',
            '.features[].rules[].cells', '.features[].rules[].cells.*.platforms')

    @classmethod
    def _key_paths(cls, value, prefix='', found=None):
        """Every key path in `value`, lists read as `[]`."""
        found = set() if found is None else found
        if isinstance(value, dict):
            for key, inner in value.items():
                path = prefix + '.' + ('*' if prefix in cls.MAPS else key)
                found.add(path)
                cls._key_paths(inner, path, found)
        elif isinstance(value, list):
            for inner in value:
                cls._key_paths(inner, prefix + '[]', found)
        return found

    @staticmethod
    def _full_payload(gate):
        """A payload that fills every part a fixture fills: evidence from both
        sources, audit entries, a hand check in the queue, a signature and
        the signed tag on HEAD."""
        made = Project(gate=gate, spec=SPEC.replace(
            'body "denied"\n', 'body "denied" @manual\n'),
            extra_config={'mutation_engine': 'auto'})
        try:
            made.sign_commits()
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], source='local')
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'}], ci=True)
            made.audit('RULE-1')
            made.audit('RULE-2', observations=['PROOF-2 reads the status.'])
            made.signature('RULE-1')
            _git(made.root, 'tag', 'signed/1.0')
            return made.payload()
        finally:
            made.close()

    # purlin: states PROOF-82
    def test_the_fixtures_carry_exactly_the_keys_the_builder_writes(self):
        fixtures, built = set(), set()
        for name, gate in (('solo', 'passed'), ('team', 'strong'),
                           ('regulated', 'signed')):
            fixtures |= self._key_paths(self._fixture(name))
            built |= self._key_paths(self._full_payload(gate))
        assert sorted(fixtures - built) == [], 'no builder writes these'
        assert sorted(built - fixtures) == [], 'no fixture carries these'

    # purlin: states PROOF-31
    # purlin: states PROOF-29
    def test_every_fixture_has_the_key_set_the_builder_writes(self):
        for name, gate in (('solo', 'passed'), ('team', 'strong'),
                           ('regulated', 'signed')):
            fixture = self._fixture(name)
            assert fixture['schema_version'] == purlin_payload.SCHEMA_VERSION
            assert fixture['gate']['gate'] == gate
            made = Project(gate=gate)
            try:
                built = made.payload()
            finally:
                made.close()
            assert sorted(fixture) == sorted(built), name
            assert sorted(fixture['gate']) == sorted(built['gate']), name
            assert sorted(fixture['summary']) == sorted(built['summary']), name
            feature = fixture['features'][0]
            assert sorted(feature) == sorted(built['features'][0]), name
            assert sorted(feature['rollup']) == sorted(
                built['features'][0]['rollup']), name
            rule = feature['rules'][0]
            assert sorted(rule) == sorted(built['features'][0]['rules'][0]), name
            assert sorted(rule['cells']) == sorted(purlin_states.cells_for(gate))
            for cell_name, cell in rule['cells'].items():
                built_cell = built['features'][0]['rules'][0]['cells'][cell_name]
                assert sorted(cell) == sorted(built_cell), (name, cell_name)
            assert sorted(rule['flags']) == sorted(
                built['features'][0]['rules'][0]['flags']), name

    # purlin: states PROOF-68
    def test_the_tag_key_is_present_in_every_fixture(self):
        """The board's chip reads this key, so a fixture without it is a lie."""
        for name in ('solo', 'team'):
            assert self._fixture(name)['tag'] is None, name
        tag = self._fixture('regulated')['tag']
        assert sorted(tag) == ['commit', 'name']
        assert tag['name'].startswith('signed/')
        assert tag['commit'] == self._fixture('regulated')['commit']

    # purlin: states PROOF-34
    def test_every_fixture_queue_row_uses_the_closed_set(self):
        words = {'hand check': {'manual test'},
                 'signature': {'unsigned', 'stale'}}
        keys = ['command', 'feature', 'level', 'need', 'owner', 'reasons',
                'rule', 'text', 'word']
        for name in ('solo', 'team', 'regulated'):
            fixture = self._fixture(name)
            for row in fixture['queue']:
                assert sorted(row) == keys, row
                assert row['word'] in words[row['need']], row
                assert row['command'].startswith(
                    'purlin:sign %s %s' % (row['owner'], row['rule'])), row
            assert fixture['summary']['queue'] == len(fixture['queue']), name


class TestProofResult:

    @staticmethod
    def _proofs(project):
        rules = next(f for f in project.payload()['features']
                     if f['name'] == 'login')['rules']
        return {proof['id']: proof for rule in rules for proof in rule['proofs']}

    # purlin: states PROOF-85
    def test_each_proof_carries_its_own_result_and_its_tests(self, project):
        _commit_tests(project, 'PROOF-1')
        proofs = self._proofs(project)
        assert proofs['PROOF-1']['result'] == 'not run', proofs['PROOF-1']
        assert proofs['PROOF-1']['tests'] == []
        assert proofs['PROOF-2']['result'] == 'no test', proofs['PROOF-2']

        project.evidence([_entry('PROOF-1', 'RULE-1'),
                          _entry('PROOF-2', 'RULE-2', status='fail')])
        proofs = self._proofs(project)
        assert proofs['PROOF-1']['result'] == 'passed', proofs['PROOF-1']
        assert proofs['PROOF-1']['tests'] == [
            {'file': 'tests/test_login.py', 'name': 'test_proof_1',
             'result': 'pass'}], proofs['PROOF-1']['tests']
        assert proofs['PROOF-2']['result'] == 'failed', proofs['PROOF-2']
        assert [test['result'] for test in proofs['PROOF-2']['tests']] == [
            'fail'], proofs['PROOF-2']['tests']

        project.spec(SPEC.replace('body "denied"\n', 'body "denied" @manual\n'))
        assert self._proofs(project)['PROOF-2']['result'] == 'hand check'


# ---------------------------------------------------------------------------
# The status table
# ---------------------------------------------------------------------------

class TestStatusTable:

    # purlin: states PROOF-58
    def test_the_table_and_the_board_render_the_same_cells(self):
        """One module renders both, so a cell cannot read two ways."""
        for name, gate in (('solo', 'passed'), ('team', 'strong'),
                           ('regulated', 'signed')):
            fixture = TestTheFixturesAreTheContract._fixture(name)
            columns = purlin_status.columns_for(gate)
            assert columns == purlin_board.columns_for(gate), name
            for feature in fixture['features']:
                row = purlin_status._row(feature, gate)
                board = purlin_board.row_cells(
                    feature['name'], feature['rollup'], gate,
                    shared=purlin_board.shared_counts(feature['rules']))
                assert row[1:] == board[1:], (name, feature['name'], row)
                assert len(row) == len(columns), (name, row)

    # purlin: states PROOF-58
    def test_the_board_cells_read_the_way_the_fixtures_say(self):
        fixture = TestTheFixturesAreTheContract._fixture('regulated')
        cells = {f['name']: purlin_board.row_cells(
            f['name'], f['rollup'], 'signed') for f in fixture['features']}
        # login's RULE-3 and invoice's RULE-1 are marked `[level: passed]`,
        # so neither is asked the audit's question or a signature's.
        assert cells['login'] == ('login', '4', '5', '3 of 4 · 1 partial',
                                  '2 of 3 · 86%', '1 of 3'), cells['login']
        assert cells['invoice'] == ('invoice', '3', '3', '3 of 3',
                                    '0 of 2 · 64%', '0 of 2'), cells['invoice']
        team = TestTheFixturesAreTheContract._fixture('team')
        rows = {f['name']: purlin_board.row_cells(
            f['name'], f['rollup'], 'strong') for f in team['features']}
        assert rows['invoice'] == ('invoice', '2', '2 · 1 no test',
                                   '1 of 2', '0 of 2 · 48%'), rows['invoice']

    # purlin: states PROOF-86
    def test_the_rules_cell_names_the_shared_rules(self, project):
        project.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
            name='security', category='_anchors')
        lines = purlin_status.sync_status(project.root).splitlines()
        header = next(line for line in lines if line.startswith('Spec'))
        login = next(line for line in lines if line.startswith('login '))
        anchor = next(line for line in lines if line.startswith('security '))
        column = header.index('Rules')
        assert login[column:].startswith('2 \u00b7 plus 1 shared'), (header,
                                                                     login)
        assert anchor[column:].split('  ')[0] == '1', (header, anchor)

        os.remove(os.path.join(project.root, 'specs', '_anchors',
                               'security.md'))
        lines = purlin_status.sync_status(project.root).splitlines()
        header = next(line for line in lines if line.startswith('Spec'))
        login = next(line for line in lines if line.startswith('login '))
        assert login[header.index('Rules'):].split('  ')[0] == '2', login
        assert not [line for line in lines if 'shared' in line], lines

    # purlin: states PROOF-43
    def test_the_columns_scale_with_the_gate(self, project):
        _commit_tests(project, 'PROOF-2')
        project.evidence([_entry('PROOF-2', 'RULE-2')])
        text = purlin_status.sync_status(project.root)
        header = next(line for line in text.splitlines()
                      if line.startswith('Spec'))
        for column in ('Spec', 'Rules', 'Proofs', 'Tests'):
            assert column in header, (column, header)
        assert 'Strong' not in header and 'Signed' not in header, header
        row = next(line for line in text.splitlines()
                   if line.startswith('login '))
        assert '1 of 2' in row, row
        assert '2 · 1 no test' in row, row

        for gate, expected in (('strong', ('Strong',)),
                               ('signed', ('Strong', 'Signed'))):
            made = Project(gate=gate)
            try:
                text = purlin_status.sync_status(made.root)
                header = next(line for line in text.splitlines()
                              if line.startswith('Spec'))
                for column in expected:
                    assert column in header, (gate, header)
                row = next(line for line in text.splitlines()
                           if line.startswith('login '))
                assert 'n/a' in row, 'no audit, so no test strength'
            finally:
                made.close()

    # purlin: states PROOF-44
    def test_the_summary_counts_the_rules_that_meet_the_gate(self, project):
        project.evidence([_entry('PROOF-2', 'RULE-2')])
        text = purlin_status.sync_status(project.root)
        line = next(line for line in text.splitlines()
                    if 'meet the gate' in line)
        assert line == '1 of 2 rules meet the gate passed.', line
        second = text.splitlines()[text.splitlines().index(line) + 1]
        assert 'test strength' not in second, second
        assert 'signature' not in second, second
        made = Project(gate='signed')
        try:
            made.evidence([_entry('PROOF-1', 'RULE-1'),
                           _entry('PROOF-2', 'RULE-2')])
            lines = purlin_status.sync_status(made.root).splitlines()
            counts = next(line for line in lines
                          if line.startswith('1 feature'))
            # Counts only: a requirement is not a count.
            assert counts == ('1 feature, 2 proof lines · 2 no test, minimum '
                              'test strength 80%, 2 rules not audited.'), \
                counts
            assert 'every rule' not in counts, counts
        finally:
            made.close()

    # purlin: states PROOF-43
    # purlin: states PROOF-81
    def test_a_passed_project_with_no_proof_line_is_shown_no_proof_count(
            self):
        made = Project(spec=NO_PROOF_SPEC)
        try:
            lines = purlin_status.sync_status(made.root).splitlines()
            header = next(line for line in lines if line.startswith('Spec'))
            assert header.split() == ['Spec', 'Rules', 'Tests'], header
            summary = lines[lines.index('0 of 1 rules meet the gate passed.')
                            + 2]
            assert summary == '1 feature.', summary
            assert not [line for line in lines if 'proof' in line], lines
            assert lines[-1] == '→ Next: run purlin:build. 1 rule has no test.'
        finally:
            made.close()

    # purlin: states PROOF-79
    def test_rules_out_of_date_are_counted_and_sent_to_the_tests(self):
        moved = {'spec': 's', 'code': 'moved on', 'tests': 't'}
        for spec, count, said in (
                (SPEC, '2 rules out of date', '2 rules are out of date.'),
                (ONE_RULE_SPEC, '1 rule out of date', '1 rule is out of date.')):
            made = Project(spec=spec)
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'pass'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}], fingerprint=moved)
                lines = purlin_status.sync_status(made.root).splitlines()
                summary = next(line for line in lines
                               if line.startswith(('1 feature', '2 feature')))
                assert summary.rstrip('.').split(', ')[-1] == count, summary
                step = [line for line in lines if line.startswith('→ Next:')]
                assert step == ['→ Next: run purlin:test. ' + said], step
            finally:
                made.close()
        made = Project()
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}])
            text = purlin_status.sync_status(made.root)
            assert 'out of date' not in text, text
        finally:
            made.close()

    # purlin: states PROOF-80
    def test_a_count_of_one_rule_reads_singular(self):
        for spec, said in (
                (ONE_RULE_SPEC, '→ Next: run purlin:build. 1 rule has a '
                                'failing test.'),
                (SPEC, '→ Next: run purlin:build. 2 rules have a failing '
                       'test.')):
            made = Project(spec=spec)
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'fail'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'fail'}])
                step = [line for line in
                        purlin_status.sync_status(made.root).splitlines()
                        if line.startswith('→ Next:')]
                assert step == [said], step
            finally:
                made.close()

    # purlin: states PROOF-45
    def test_the_table_ends_with_one_next_step(self, project):
        text = purlin_status.sync_status(project.root)
        directives = [line for line in text.splitlines()
                      if line.startswith('→ Next:')]
        assert len(directives) == 1, text
        assert 'purlin:build' in directives[0], directives[0]

    # purlin: states PROOF-69
    def test_a_rule_marked_above_the_gate_is_named_once(self):
        made = Project(gate='strong')
        try:
            lines = purlin_status.sync_status(made.root).splitlines()
            assert ('1 rule is marked above the gate and is read as strong.'
                    in lines), lines
            made.spec(SPEC.replace('"denied"\n\n', '"denied" [level: signed]'
                                   '\n\n', 1))
            lines = purlin_status.sync_status(made.root).splitlines()
            assert ('2 rules are marked above the gate and are read as '
                    'strong.' in lines), lines
            made.config_value('gate', 'signed')
            text = purlin_status.sync_status(made.root)
            assert 'marked above the gate' not in text, text
        finally:
            made.close()

    # purlin: states PROOF-67
    def test_a_rule_waiting_on_a_run_is_sent_to_the_tests(self):
        """A rule whose run is out of date waits on a test run, at every gate.

        The audit is never the step while a test run is: only `trust: remote`
        sends the run to the runner.
        """
        for gate, trust, said in (
                ('passed', 'local',
                 '→ Next: run purlin:test. 2 rules are out of date.'),
                ('strong', 'local',
                 '→ Next: run purlin:test. 2 rules are out of date.'),
                ('signed', 'local',
                 '→ Next: run purlin:test. 2 rules are out of date.'),
                ('signed', 'remote',
                 '→ Next: run purlin:test --remote. 2 rules have no current '
                 'run.')):
            made = Project(gate=gate, extra_config={'trust': trust})
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'pass'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}],
                              source='ci',
                              fingerprint={'spec': 's', 'code': 'moved on',
                                           'tests': 't'})
                step = [line for line in
                        purlin_status.sync_status(made.root).splitlines()
                        if line.startswith('→ Next:')]
                assert step == [said], (gate, trust, step)
            finally:
                made.close()
        assert purlin_board.needs_a_person(1) == '1 rule needs a person'
        assert purlin_board.needs_a_person(3) == '3 rules need a person'
        assert purlin_board.needs_a_person(0) == 'no rule needs a person'

    # purlin: states PROOF-87
    def test_a_rule_tagged_for_another_system_is_sent_to_the_runner(self):
        here = purlin_evidence.host_os()
        other = 'windows' if here == 'linux' else 'linux'
        for tag, said in (
                (other, '→ Next: run purlin:test --remote. 2 rules need %s, '
                        'which this machine is not.' % other),
                (here, '→ Next: run purlin:test. 2 rules have no run to '
                       'read.')):
            made = Project(spec=SPEC.replace('token\n', 'token @env(%s)\n'
                                             % tag).replace(
                'denied"\n', 'denied" @env(%s)\n' % tag))
            try:
                made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                'status': 'pass'},
                               {'id': 'PROOF-2', 'rule': 'RULE-2',
                                'status': 'pass'}],
                              os_name='macos' if here != 'macos'
                              else 'windows')
                step = [line for line in
                        purlin_status.sync_status(made.root).splitlines()
                        if line.startswith('→ Next:')]
                assert step == [said], (tag, step)
            finally:
                made.close()

    # purlin: states PROOF-88
    def test_the_audit_is_the_step_only_when_no_rule_waits_on_a_run(self):
        made = Project(gate='strong')
        try:
            made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                            'status': 'pass'},
                           {'id': 'PROOF-2', 'rule': 'RULE-2',
                            'status': 'pass'}])
            step = [line for line in
                    purlin_status.sync_status(made.root).splitlines()
                    if line.startswith('→ Next:')]
            assert step == ['→ Next: run purlin:audit. 2 rules are not '
                            'audited.'], step
            made.audit('RULE-2', observations=['PROOF-2 reads the code '
                                               'alone.'])
            made.audit('RULE-1')
            step = [line for line in
                    purlin_status.sync_status(made.root).splitlines()
                    if line.startswith('→ Next:')]
            assert step == ['→ Next: run purlin:build. 1 rule is weak.'], step
        finally:
            made.close()

    # purlin: states PROOF-48
    def test_retired_config_keys_print_the_update_directive(self):
        made = Project(extra_config={'spec_dir': 'elsewhere'})
        try:
            text = purlin_status.sync_status(made.root)
            assert '→ Run: purlin:init --update' in text, text
        finally:
            made.close()

    # purlin: states PROOF-46
    def test_an_empty_project_says_what_to_run(self):
        made = Project(spec=None)
        try:
            text = purlin_status.sync_status(made.root)
            assert 'No specs found' in text and 'purlin:init' in text
        finally:
            made.close()

    # purlin: states PROOF-47
    def test_no_emoji_and_only_the_four_glyphs(self, project):
        text = purlin_status.sync_status(project.root)
        allowed = set('→▶▼─')
        for char in text:
            assert ord(char) < 0x2000 or char in allowed, repr(char)

    # purlin: states PROOF-49
    def test_the_repository_own_specs_print_the_table(self):
        text = purlin_status.sync_status(PROJECT_ROOT)
        header = next(line for line in text.splitlines()
                      if line.startswith('Spec'))
        assert 'Proofs' in header and 'Tests' in header, header
        assert any('of' in line for line in text.splitlines()), text
        assert text.rstrip().splitlines()[-1].startswith('→'), text


# ---------------------------------------------------------------------------
# The MCP transport
# ---------------------------------------------------------------------------

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


class TestTransport:

    # purlin: server PROOF-1
    # purlin: server PROOF-5
    def test_initialize_names_the_protocol_and_the_version(self, project):
        responses, stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
            'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                       'clientInfo': {'name': 't', 'version': '0'}}},
            child=True)
        result = responses[0]['result']
        assert result['protocolVersion'] == '2024-11-05'
        assert result['serverInfo']['name'] == 'purlin'
        with open(os.path.join(PROJECT_ROOT, 'VERSION'),
                  encoding='utf-8') as handle:
            assert result['serverInfo']['version'] == handle.read().strip()
        assert 'Purlin MCP server' in stderr

    # purlin: server PROOF-2
    def test_tools_list_names_the_three_tools(self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'})
        names = [t['name'] for t in responses[0]['result']['tools']]
        assert sorted(names) == ['drift', 'purlin_config', 'sync_status']
        for tool in responses[0]['result']['tools']:
            assert 'project_root' in tool['inputSchema']['properties']

    def test_sync_status_answers_the_table(self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
            'params': {'name': 'sync_status', 'arguments': {}}})
        text = responses[0]['result']['content'][0]['text']
        assert 'Spec' in text and 'Tests' in text and 'login' in text

    # purlin: server PROOF-9
    def test_purlin_config_reads_and_writes(self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'read', 'key': 'gate'}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'write', 'key': 'gate',
                                      'value': 'strong'}}},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'read', 'key': 'gate'}}})
        assert json.loads(responses[0]['result']['content'][0]['text']) == {
            'gate': 'passed'}
        assert json.loads(responses[2]['result']['content'][0]['text']) == {
            'gate': 'strong'}
        # The write lands in the one settings file.
        with open(os.path.join(project.root, '.purlin', 'config.json'),
                  encoding='utf-8') as handle:
            assert json.load(handle)['gate'] == 'strong'

    def test_drift_answers_json(self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'drift', 'arguments': {'since': '1'}}})
        report = json.loads(responses[0]['result']['content'][0]['text'])
        assert sorted(report) == ['roles', 'since'], sorted(report)
        assert sorted(report['roles']) == ['eng', 'pm', 'qa']

    # purlin: server PROOF-7
    def test_a_root_with_no_workspace_says_so_rather_than_reporting_nothing(
            self, tmp_path):
        responses, _stderr = _rpc(str(tmp_path), {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'sync_status', 'arguments': {}}})
        text = responses[0]['result']['content'][0]['text']
        assert 'No Purlin workspace' in text and 'purlin:init' in text

    # purlin: server PROOF-3
    def test_a_notification_gets_no_response_and_bad_json_gets_a_parse_error(
            self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 9, 'method': 'tools/list'})
        assert [r['id'] for r in responses] == [9]

        result = subprocess.run([sys.executable, SERVER_PY],
                                input='not json\n', capture_output=True,
                                text=True, cwd=project.root, timeout=60)
        parsed = json.loads(result.stdout.strip())
        assert parsed['error']['code'] == -32700

    # purlin: server PROOF-4
    def test_an_unknown_tool_and_an_unknown_method_are_errors(self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
             'params': {'name': 'nope', 'arguments': {}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'nope/at/all'})
        assert responses[0]['error']['code'] == -32601
        assert responses[1]['error']['code'] == -32601

    # purlin: server PROOF-6
    def test_project_root_can_be_named_per_call(self, project, tmp_path):
        responses, _stderr = _rpc(str(tmp_path), {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'sync_status',
                       'arguments': {'project_root': project.root}}})
        assert 'login' in responses[0]['result']['content'][0]['text']

    # purlin: server PROOF-8
    def test_a_tool_that_raises_answers_rather_than_crashing(self, project,
                                                             monkeypatch):
        def boom(_root):
            raise RuntimeError('boom')

        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                   'params': {'name': 'sync_status', 'arguments': {}}}
        monkeypatch.setattr(purlin_srv.status_module, 'sync_status', boom)
        text = purlin_srv.handle_request(
            request, project.root)['result']['content'][0]['text']
        assert text.startswith('Error running sync_status'), text
        assert 'boom' in text, text
        monkeypatch.undo()
        # The session is still usable: the next call answers normally.
        again = purlin_srv.handle_request(
            request, project.root)['result']['content'][0]['text']
        assert 'Tests' in again, again

    # purlin: server PROOF-10
    def test_a_write_with_no_key_and_an_unknown_action_are_refused(self,
                                                                   project):
        before = purlin_srv.resolve_config(project.root)
        no_key = purlin_srv.handle_purlin_config(
            project.root, {'action': 'write', 'value': 'x'})
        assert "'key' is required" in no_key, no_key
        unknown = purlin_srv.handle_purlin_config(
            project.root, {'action': 'delete', 'key': 'gate'})
        assert unknown.startswith('Unknown action'), unknown
        assert purlin_srv.resolve_config(project.root) == before


class TestPackageHygiene:
    """What the package may not do, whatever else it does."""

    def test_every_open_passes_an_encoding(self):
        import re
        package = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin')
        offenders = []
        for name in sorted(os.listdir(package)):
            if not name.endswith('.py'):
                continue
            with open(os.path.join(package, name), encoding='utf-8') as handle:
                for number, line in enumerate(handle, 1):
                    if re.search(r'(?<!\w)open\(', line) and 'encoding=' not in line:
                        offenders.append('%s:%d %s' % (name, number, line.strip()))
        assert offenders == [], offenders

    def test_the_package_imports_nothing_outside_the_standard_library(self):
        import re
        package = os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin')
        allowed = set(sys.stdlib_module_names) if hasattr(
            sys, 'stdlib_module_names') else set()
        local = {'purlin', 'config_engine'}
        offenders = []
        for name in sorted(os.listdir(package)):
            if not name.endswith('.py'):
                continue
            with open(os.path.join(package, name), encoding='utf-8') as handle:
                for line in handle:
                    m = re.match(r'\s*(?:import|from)\s+([A-Za-z_][\w.]*)', line)
                    if not m:
                        continue
                    top = m.group(1).split('.')[0]
                    if top in local or not allowed or top in allowed:
                        continue
                    offenders.append('%s: %s' % (name, line.strip()))
        assert offenders == [], offenders

    # purlin: server PROOF-22
    def test_the_plugin_entry_point_names_the_package(self):
        with open(os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json'),
                  encoding='utf-8') as handle:
            manifest = json.load(handle)
        entry = manifest['mcpServers']['purlin']
        assert entry['command'] == 'sh', entry
        args = entry['args']
        assert args[0].endswith('scripts/purlin_python.sh'), args
        assert args[-1].endswith('scripts/mcp/purlin/server.py'), args


# ---------------------------------------------------------------------------
# The signed tag on HEAD
# ---------------------------------------------------------------------------

class TestTheSignedTag:
    """The payload names the `signed/*` tag pointing at HEAD, or nothing."""

    # purlin: states PROOF-68
    def test_no_tag_reads_none_and_a_tag_on_head_reads_its_name(self):
        made = Project(gate='signed')
        try:
            assert made.payload()['tag'] is None
            _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
            tag = made.payload()['tag']
            assert tag['name'] == 'signed/1.2.0', tag
            assert tag['commit'] == made.head(), tag
        finally:
            made.close()

    # purlin: states PROOF-68
    def test_a_tag_that_is_not_on_head_says_nothing_about_this_code(self):
        made = Project(gate='signed')
        try:
            _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
            _write(os.path.join(made.root, 'src', 'later.py'), 'X = 1\n')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'feat: more')
            assert made.payload()['tag'] is None
        finally:
            made.close()

    # purlin: states PROOF-68
    def test_the_newest_version_wins_where_several_point_at_head(self):
        made = Project(gate='signed')
        try:
            for name in ('signed/1.9.0', 'signed/1.10.0', 'signed/beta'):
                _git(made.root, 'tag', '-a', name, '-m', name)
            assert made.payload()['tag']['name'] == 'signed/1.10.0'
        finally:
            made.close()

    # purlin: states PROOF-83
    def test_below_signed_the_payload_names_no_tag(self):
        for gate in ('strong', 'passed'):
            made = Project(gate=gate)
            try:
                _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
                assert made.payload()['tag'] is None, gate
                config = os.path.join(made.root, '.purlin', 'config.json')
                with open(config, encoding='utf-8') as handle:
                    settings = json.load(handle)
                settings['gate'] = 'signed'
                _write(config, json.dumps(settings))
                assert made.payload()['tag']['name'] == 'signed/1.2.0', gate
            finally:
                made.close()


# ---------------------------------------------------------------------------
# A spec that names no files
# ---------------------------------------------------------------------------

NO_SCOPE_SPEC = SPEC.replace('> Scope: src/login.py\n', '')
PASSING = [{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
           {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}]


def _feature(payload, name='login'):
    return next(f for f in payload['features'] if f['name'] == name)


class TestASpecThatNamesNoFiles:
    """Its tests still run and pass; only a signature needs its files named."""

    # purlin: states PROOF-74
    def test_the_payload_names_why_it_is_incomplete(self):
        for spec, reason in (
                (NO_SCOPE_SPEC, 'no > Scope: line'),
                (SPEC.replace('src/login.py', 'src/nowhere.py'),
                 '> Scope: names nothing that exists'),
                (SPEC, None)):
            made = Project(spec=spec)
            try:
                made.evidence(PASSING)
                data = made.payload()
                feature = _feature(data)
                assert feature['incomplete'] is (reason is not None), spec
                assert feature['incomplete_reason'] == reason, feature
                assert feature['rollup']['incomplete'] is (
                    reason is not None), feature['rollup']
                assert data['summary']['incomplete'] == (
                    1 if reason else 0), data['summary']
                # Its tests pass and it meets the gate `passed` all the same.
                assert [rule['cells']['passed']['word']
                        for rule in feature['rules']] == ['passed', 'passed']
                assert all(rule['meets_gate'] for rule in feature['rules'])
            finally:
                made.close()

    # purlin: states PROOF-74
    def test_an_anchor_is_never_incomplete(self):
        made = Project()
        try:
            made.spec('# Anchor: shared\n\n## Rules\n\n- RULE-1: every '
                      'answer is JSON\n\n## Proof\n\n- PROOF-1 (RULE-1): an '
                      'answer parses as JSON\n', name='shared',
                      category='_anchors')
            data = made.payload()
            anchor = _feature(data, 'shared')
            assert anchor['is_anchor'] is True
            assert (anchor['incomplete'], anchor['incomplete_reason']) == (
                False, None)
            assert data['summary']['incomplete'] == 0
        finally:
            made.close()

    # purlin: states PROOF-75
    def test_at_signed_its_rules_read_unsigned_and_wait_on_nobody(self):
        for spec, word, queued in ((SPEC, 'unsigned', True),
                                   (NO_SCOPE_SPEC, 'unsigned', False)):
            made = Project(spec=spec, gate='signed')
            try:
                made.evidence(PASSING)
                made.audit('RULE-1')
                made.audit('RULE-2')
                data = made.payload()
                rule = next(r for r in _feature(data)['rules']
                            if r['id'] == 'RULE-2')
                cell = rule['cells']['signed']
                assert cell['word'] == word, cell
                assert rule['cells']['strong']['word'] == 'strong', rule
                assert rule['meets_gate'] is False
                assert rule['blocked_by'] == 'signed'
                assert bool(data['queue']) is queued, data['queue']
                if not queued:
                    assert cell['reasons'] == [
                        'the spec names no files in > Scope:, so a signature '
                        'cannot be tied to the code it governs'], cell
            finally:
                made.close()

    # purlin: states PROOF-75
    def test_at_signed_a_signature_on_it_does_not_count(self):
        made = Project(spec=NO_SCOPE_SPEC, gate='signed')
        try:
            made.sign_commits()
            made.evidence(PASSING)
            made.audit('RULE-2')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'purlin: evidence at x')
            made.signature('RULE-2')
            rule = made.rule('RULE-2')
            assert rule['cells']['signed']['word'] == 'unsigned', rule
            assert rule['meets_gate'] is False
        finally:
            made.close()

    # purlin: states PROOF-75
    def test_below_signed_it_blocks_nothing(self):
        made = Project(spec=NO_SCOPE_SPEC, gate='strong')
        try:
            made.evidence(PASSING)
            made.audit('RULE-1')
            made.audit('RULE-2')
            data = made.payload()
            assert _feature(data)['incomplete'] is True
            assert all(rule['meets_gate'] for rule in _feature(data)['rules'])
        finally:
            made.close()

    # purlin: states PROOF-76
    def test_status_names_it_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            made = Project(spec=NO_SCOPE_SPEC, gate=gate)
            try:
                lines = purlin_status.sync_status(made.root).splitlines()
                assert ('1 spec names no files, so its tests run every time: '
                        'login.') in lines, (gate, lines)
            finally:
                made.close()
        made = Project()
        try:
            made.spec(NO_SCOPE_SPEC.replace('login', 'export'), name='export')
            made.spec(NO_SCOPE_SPEC)
            lines = purlin_status.sync_status(made.root).splitlines()
            assert ('2 specs name no files, so their tests run every time: '
                    'export, login.') in lines, lines
        finally:
            made.close()
        made = Project()
        try:
            text = purlin_status.sync_status(made.root)
            assert 'names no files' not in text and 'name no files' not in text
        finally:
            made.close()

    # purlin: states PROOF-76
    def test_at_signed_with_nothing_else_left_the_next_step_is_the_spec(self):
        made = Project(spec=NO_SCOPE_SPEC.replace(' [level: signed]', ''),
                       gate='signed')
        try:
            made.evidence(PASSING)
            made.audit('RULE-1')
            made.audit('RULE-2')
            lines = purlin_status.sync_status(made.root).splitlines()
            assert ('→ Next: run purlin:spec login. It names no files in '
                    '> Scope:, so its rules cannot be signed.') in lines, lines
        finally:
            made.close()
