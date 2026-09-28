"""Tests for the core package `scripts/mcp/purlin/`.

Five areas, in the order a project meets them: what a spec parses to, what a
test run leaves behind, what the cells of each rule read, what the payload
and the status table say about it, and what the MCP transport answers.

Every fixture is written by the test: a spec, a runtime proof file, a record
under `.purlin/records/`, a brief under `.purlin/briefs/`, a signature beside
the spec. Nothing here reads the repository's own specs except where a test
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
from purlin import drift as purlin_drift
from purlin import frameworks as purlin_frameworks
from purlin import gate as purlin_gate
from purlin import payload as purlin_payload
from purlin import proofs as purlin_proofs
from purlin import records as purlin_records
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


# What a commit Azure DevOps made looks like. `records.record_label` reads the
# committer, so a record written under this identity carries the label `ci`
# without a signature this checkout would have to hold a key for.
CI_COMMITTER = {'GIT_COMMITTER_NAME': 'Project Collection Build Service',
                'GIT_COMMITTER_EMAIL': 'build@azure.local'}


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
    '[bar: strong]\n'
    '- RULE-2: Invalid credentials return 401 and the body "denied"\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200 and a '
    'token\n'
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify 401 and the '
    'body "denied"\n'
)


class Project(object):
    """A throwaway project root with git, a config and one spec."""

    def __init__(self, spec=SPEC, gate='passed', extra_config=None):
        self.root = tempfile.mkdtemp()
        config = {'gate': gate, 'project_name': 'proj'}
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

    def proofs(self, entries, feature='login'):
        _write(os.path.join(self.root, '.purlin', 'runtime', 'proofs',
                            '%s.json' % feature),
               json.dumps({'proofs': entries}))

    def record(self, proofs, feature='login', runner='ci', os_name=None,
               commit=None, scope_tree=None, strength=90, commit_it=True,
               ci=False, source=None, stamp='20260913T120000Z',
               environment_os=None, claimed_source=None):
        """One record in its source folder. The folder is what the reader reads.

        `source` is `ci` or `local` and defaults to `ci` when `ci=True`, so a
        test that wanted the git host's own record gets the git host's own
        folder. `claimed_source` writes a different word into the file, which
        is how a test makes the two disagree.
        """
        source = source or ('ci' if ci else 'local')
        name = '%s-%s-%s%s.json' % (stamp, (commit or self.head())[:7], runner,
                                    '-' + os_name if os_name else '')
        path = os.path.join(self.root, '.purlin', 'records', source, feature,
                            name)
        _write(path, json.dumps({
            'schema_version': 3,
            'feature': feature,
            'source': claimed_source or source,
            'commit': commit or self.head(),
            'timestamp': '2026-09-13T12:00:00Z',
            'runner': runner,
            'os': os_name,
            'environment': {'os': None if environment_os == 'none'
                            else (environment_os or os_name or 'linux')},
            'test_strength': strength,
            'scope_tree': scope_tree,
            'proofs': proofs,
        }))
        if commit_it:
            env = None
            if ci:
                env = dict(os.environ)
                env.update(CI_COMMITTER)
            _git(self.root, 'add', '-A')
            _git(self.root, 'commit', '-q', '-m', 'purlin: record', env=env)
        return os.path.relpath(path, self.root).replace(os.sep, '/')

    def signature(self, rule_id, feature='login', category='auth',
                  signer='jane@acme.com', commit_it=True, **overrides):
        """Write one signature file for a rule's current hashes."""
        return self._attestation(rule_id, feature, category, signer, '',
                                 commit_it, overrides)

    def hold(self, rule_id, reason, feature='login', category='auth',
             signer='jane@acme.com', commit_it=True, **overrides):
        """Write one hold file naming the case the test does not prove."""
        overrides = dict(overrides)
        overrides['reason'] = reason
        return self._attestation(rule_id, feature, category, signer, '.hold',
                                 commit_it, overrides)

    def _attestation(self, rule_id, feature, category, signer, suffix,
                     commit_it, overrides):
        rule = self.rule(rule_id, feature)
        data = {
            'schema': 'purlin-signature/1', 'feature': feature,
            'rule': rule_id, 'bar': rule['bar'], 'signer': signer,
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
        name = '%s.%s.%s%s.json' % (rule_id, hash8, slug, suffix)
        _write(os.path.join(directory, name), json.dumps(data))
        if commit_it:
            _git(self.root, 'add', '-A')
            _git(self.root, 'commit', '-q', '-m', 'sign(%s): %s'
                 % (feature, rule_id))
        return os.path.join(directory, name)

    def brief(self, rule_id, feature='login', settled=True, observations=(),
              tests=(), source='ci'):
        """Write the brief CI would have written for a rule's current hashes."""
        rule = self.rule(rule_id, feature)
        triple = purlin_signatures.triple_hash(
            rule['rule_hash'], rule['proof_hash'], rule['test_hash'])
        path = os.path.join(self.root, '.purlin', 'briefs', source, feature,
                            '%s.%s.brief.json' % (rule_id, triple[:8]))
        _write(path, json.dumps({
            'schema': 'purlin-brief/3', 'feature': feature, 'rule': rule_id,
            'triple_hash': triple, 'settled': settled,
            # A brief that names no model answer is one no model was
            # reached for, and the strong cell reads that as an AI audit
            # that never ran. A fixture that wants a settled or an
            # unsettled review has to carry the answer.
            'ai_review': 'settled: %s' % ('yes' if settled else 'no'),
            'observations': list(observations), 'tests': list(tests)}))
        return os.path.relpath(path, self.root).replace(os.sep, '/')

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


def _entry(proof_id, rule_id, status='pass', feature='login',
           test_file='tests/test_login.py'):
    return {'feature': feature, 'id': proof_id, 'rule': rule_id,
            'status': status, 'test_file': test_file,
            'test_name': 'test_' + proof_id.lower().replace('-', '_')}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class TestSpecParsing:

    @pytest.mark.proof("specs", "PROOF-1", "RULE-1")
    @pytest.mark.proof("specs", "PROOF-3", "RULE-2")
    def test_rule_tags_are_read_off_the_end_and_stripped(self, project):
        info = purlin_specs.scan_specs(project.root)['login']
        assert info['rules']['RULE-1'] == (
            'Valid credentials return 200 with a session token'), info['rules']
        assert info['rule_meta']['RULE-1'] == {'bar': 'strong'}
        # A rule that names no tag carries no metadata at all.
        assert info['rule_meta']['RULE-2'] == {}

    @pytest.mark.proof("specs", "PROOF-2", "RULE-1")
    def test_bracketed_text_that_is_not_a_tag_stays_in_the_claim(self):
        text, meta = purlin_specs.split_rule_tags(
            'Tokens expire [owner: qa] [bar: strong]')
        assert text == 'Tokens expire [owner: qa]'
        assert meta == {'bar': 'strong'}

    @pytest.mark.proof("specs", "PROOF-4", "RULE-3")
    def test_the_hash_ignores_the_tags_and_the_whitespace(self):
        plain = purlin_specs.rule_text_hash('Tokens expire after 24 hours')
        tagged, _meta = purlin_specs.split_rule_tags(
            'Tokens  expire   after 24 hours [bar: strong]')
        assert purlin_specs.rule_text_hash(tagged) == plain, (
            're-tagging or reflowing a rule must not change its rule text hash')

    @pytest.mark.proof("specs", "PROOF-5", "RULE-4")
    @pytest.mark.proof("specs", "PROOF-6", "RULE-5")
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

    @pytest.mark.proof("specs", "PROOF-7", "RULE-6")
    def test_a_second_env_tag_is_refused_not_merged(self):
        _clean, _manual, env, unknown = purlin_specs.split_proof_tags(
            'Lock it @env(macos) @env(windows)')
        assert env == 'windows', 'the trailing tag is the one that is read'
        assert unknown == ['@env(macos)'], unknown

    @pytest.mark.proof("specs", "PROOF-8", "RULE-7")
    @pytest.mark.proof("specs", "PROOF-9", "RULE-8")
    def test_unknown_tags_are_ignored_with_one_warning_naming_the_files(self,
                                                                       project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n- RULE-1: Files lock\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Lock a file; verify 1 open fails '
            '@on(windows-2022)\n')  # retired
        project.spec(
            '# Feature: legacy\n\n> Visual-Reference: ./mock.png\n\n'
            '## Rules\n\n- RULE-1: It renders\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Look at it @manual(a@b.c, '
            '2026-03-31, abc1234)\n', name='legacy')
        features = purlin_specs.scan_specs(project.root)
        assert features['login']['proofs']['PROOF-1']['env'] is None
        assert features['login']['unknown_tags'] == ['@on(windows-2022)']  # retired
        assert features['legacy']['proofs']['PROOF-1']['manual'] is True
        assert set(features['legacy']['unknown_tags']) == {
            '@manual(...)', '> Visual-Reference:'}
        warning = purlin_specs.unknown_tag_warning(features)
        assert warning and 'specs/auth/login.md' in warning, warning
        assert 'specs/auth/legacy.md' in warning, warning
        # One line, naming the files: not one warning per proof line.
        assert warning.count('\n') == 0, warning
        # A scan whose specs carry no such tag warns about nothing at all.
        clean = {name: dict(info, unknown_tags=[])
                 for name, info in features.items()}
        assert purlin_specs.unknown_tag_warning(clean) is None

    @pytest.mark.proof("specs", "PROOF-10", "RULE-9")
    def test_a_source_is_a_git_url_plus_a_path_or_whole(self):
        assert purlin_specs.parse_source(
            'https://github.com/acme/p.git specs/no_eval.md') == (
                'https://github.com/acme/p.git', 'specs/no_eval.md')
        assert purlin_specs.parse_source('./policies') == ('./policies', None)
        # Not a URL followed by a path: the whole line is the source, so a
        # value that has to be refused is refused whole.
        assert purlin_specs.parse_source('--upload-pack=/bin/echo') == (
            '--upload-pack=/bin/echo', None)

    @pytest.mark.proof("specs", "PROOF-11", "RULE-10")
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

    @pytest.mark.proof("specs", "PROOF-12", "RULE-11")
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

    @pytest.mark.proof("specs", "PROOF-14", "RULE-13")
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

    @pytest.mark.proof("specs", "PROOF-13", "RULE-12")
    def test_the_scope_tree_changes_with_the_scoped_files(self, project):
        first = purlin_specs.scope_tree(project.root, ['src/login.py'])
        assert len(first) == 64
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 401\n')
        assert purlin_specs.scope_tree(project.root, ['src/login.py']) != first
        # A scope naming nothing still answers, so a spec with no scope is not
        # an error.
        assert len(purlin_specs.scope_tree(project.root, [])) == 64

    @pytest.mark.proof("specs", "PROOF-16", "RULE-12")
    def test_an_untracked_file_under_a_scoped_directory_is_not_read(
            self, project):
        """A scoped directory expands to what git tracks, not to the disk."""
        first = purlin_specs.scope_tree(project.root, ['src'])
        _write(os.path.join(project.root, 'src', 'scratch.py'), 'x = 1\n')
        assert purlin_specs.scope_tree(project.root, ['src']) == first
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'feat: a second source file')
        assert purlin_specs.scope_tree(project.root, ['src']) != first

    @pytest.mark.proof("specs", "PROOF-15", "RULE-14")
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
# Runtime proof files
# ---------------------------------------------------------------------------

class TestProofFiles:

    @pytest.mark.proof("proofs", "PROOF-1", "RULE-1")
    @pytest.mark.proof("proofs", "PROOF-3", "RULE-3")
    def test_proofs_are_read_from_the_runtime_directory(self, project):
        assert purlin_proofs.load_proofs(project.root) == {}
        project.proofs([_entry('PROOF-1', 'RULE-1')])
        loaded = purlin_proofs.load_proofs(project.root)
        assert [e['id'] for e in loaded['login']] == ['PROOF-1']
        assert purlin_proofs.PROOF_DIR.replace(os.sep, '/') == (
            '.purlin/runtime/proofs')
        # Entries are grouped by the feature each one names, not by the file.
        project.proofs([_entry('PROOF-1', 'RULE-1'),
                        _entry('PROOF-1', 'RULE-1', feature='signup')],
                       feature='login')
        both = purlin_proofs.load_proofs(project.root)
        assert sorted(both) == ['login', 'signup'], sorted(both)
        assert [e['feature'] for e in both['signup']] == ['signup']

    @pytest.mark.proof("proofs", "PROOF-5", "RULE-5")
    def test_a_bad_file_is_skipped(self, project):
        directory = os.path.join(project.root, '.purlin', 'runtime', 'proofs')
        _write(os.path.join(directory, 'login.json'),
               json.dumps({'proofs': [_entry('PROOF-1', 'RULE-1')]}))
        _write(os.path.join(directory, 'broken.json'), 'not json at all')
        _write(os.path.join(directory, 'listed.json'), '[]')
        _write(os.path.join(directory, 'notes.txt'),
               json.dumps({'proofs': [_entry('PROOF-9', 'RULE-9')]}))
        after = purlin_proofs.load_proofs(project.root)
        assert sorted(after) == ['login'], sorted(after)
        assert len(after['login']) == 1, after['login']

    @pytest.mark.proof("proofs", "PROOF-6", "RULE-6")
    def test_a_fail_beats_a_pass_for_the_same_proof(self, project):
        project.proofs([_entry('PROOF-1', 'RULE-1'),
                        _entry('PROOF-1', 'RULE-1', status='fail',
                               test_file='tests/other.py')])
        entries = purlin_proofs.load_proofs(project.root)['login']
        assert purlin_proofs.status_by_proof(entries) == {
            ('login', 'PROOF-1'): 'fail'}

    @pytest.mark.proof("proofs", "PROOF-7", "RULE-7")
    def test_the_tests_backing_a_proof_are_named_once_each(self, project):
        project.proofs([_entry('PROOF-1', 'RULE-1'),
                        _entry('PROOF-1', 'RULE-1')])
        entries = purlin_proofs.load_proofs(project.root)['login']
        assert purlin_proofs.tests_for(entries, 'PROOF-1') == [
            ('tests/test_login.py', 'test_proof_1')]


# ---------------------------------------------------------------------------
# Frameworks
# ---------------------------------------------------------------------------

class TestFrameworks:

    def test_shell_is_the_fallback_and_every_match_is_returned(self, tmp_path):
        root = str(tmp_path)
        assert purlin_frameworks.detect_frameworks(root) == ['shell']
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

    def test_xunit_is_a_csproj_that_references_the_package(self, tmp_path):
        root = str(tmp_path)
        _write(os.path.join(root, 'tests', 'App.Tests.csproj'),
               '<Project><ItemGroup>'
               '<PackageReference Include="xunit" Version="2.6.0" />'
               '</ItemGroup></Project>\n')
        assert 'xunit' in purlin_frameworks.detect_frameworks(root)
        _write(os.path.join(root, 'tests', 'App.Tests.csproj'),
               '<Project><ItemGroup>'
               '<PackageReference Include="Moq" Version="4" />'
               '</ItemGroup></Project>\n')
        assert 'xunit' not in purlin_frameworks.detect_frameworks(root)

    def test_c_and_php_are_gone(self, tmp_path):
        root = str(tmp_path)
        _write(os.path.join(root, 'Makefile'), 'all:\n\techo hi\n')
        _write(os.path.join(root, 'main.c'), 'int main(){return 0;}\n')
        _write(os.path.join(root, 'composer.json'), '{}')
        assert purlin_frameworks.detect_frameworks(root) == ['shell']
        assert 'c' not in purlin_frameworks.KNOWN_FRAMEWORKS
        assert 'php' not in purlin_frameworks.KNOWN_FRAMEWORKS

    def test_auto_expands_in_place_and_a_typo_is_reported(self, tmp_path):
        root = str(tmp_path)
        _write(os.path.join(root, 'conftest.py'), '')
        found, unknown = purlin_frameworks.resolve_frameworks(
            root, 'shell, auto, shell')
        assert found == ['shell', 'pytest'], found
        assert unknown == []
        found, unknown = purlin_frameworks.resolve_frameworks(root, 'pytesst')
        assert unknown == ['pytesst'], unknown
        assert found == ['pytest'], 'an unusable value falls back to detection'


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

class TestGate:

    def test_each_gate_derives_its_own_defaults(self):
        for gate, bar, strength, sign_at, breaks in (
                ('passed', 'passed', None, None, False),
                ('strong', 'strong', 70, None, True),
                ('signed', 'strong', 80, 'strong', True)):
            cfg = purlin_gate.resolve_gate({'gate': gate})
            assert (cfg.gate, purlin_gate.default_bar(gate), cfg.min_strength,
                    cfg.sign_at, cfg.breaks) == (gate, bar, strength, sign_at,
                                                 breaks)

    def test_the_settings_written_out_are_the_ones_a_project_can_name(self):
        written = purlin_gate.resolve_gate({'gate': 'signed'}).as_dict()
        assert sorted(written) == [
            'ci', 'gate', 'min_strength', 'mutation_engine',
            'sign_at', 'sql_engine', 'test_framework', 'trust']

    def test_a_named_key_overrides_the_derived_default(self):
        cfg = purlin_gate.resolve_gate({'gate': 'strong', 'min_strength': 95,
                                        'sign_at': 'all'})
        assert cfg.min_strength == 95 and cfg.sign_at == 'all'

    def test_sign_at_reads_its_two_values_and_warns_on_any_other(self):
        for named in ('strong', 'all'):
            cfg = purlin_gate.resolve_gate({'gate': 'signed',
                                            'sign_at': named})
            assert cfg.sign_at == named, named
            assert cfg.warnings == [], cfg.warnings
        odd = purlin_gate.resolve_gate({'gate': 'signed', 'sign_at': 'often'})
        assert odd.sign_at == 'strong'
        assert any('often' in w for w in odd.warnings), odd.warnings

    def test_a_signature_is_needed_by_the_bar_and_by_sign_at(self):
        needs = purlin_gate.needs_signature
        assert needs('signed', 'strong', 'strong') is True
        assert needs('signed', 'strong', 'passed') is False
        assert needs('signed', 'all', 'passed') is True
        assert needs('strong', 'all', 'strong') is False

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
        cfg = purlin_gate.resolve_gate({'pre_push': 'on'})   # retired
        assert any('purlin:init --update' in w for w in cfg.warnings), \
            cfg.warnings

    def test_the_default_bar_is_the_projects_own_gate(self):
        assert purlin_gate.default_bar('passed') == 'passed'
        assert purlin_gate.default_bar('strong') == 'strong'
        assert purlin_gate.default_bar('signed') == 'strong'


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

class TestRecords:

    def test_the_file_name_carries_the_stamp_the_commit_the_runner_and_the_os(self):
        assert purlin_records.record_name_parts(
            '20260913T120000Z-abc1234-ci.json') == (
                '20260913T120000Z', 'abc1234', 'ci', None)
        assert purlin_records.record_name_parts(
            '20260913T120000Z-abc1234-ci-windows.json') == (
                '20260913T120000Z', 'abc1234', 'ci', 'windows')
        assert purlin_records.record_name_parts('nonsense.json') is None

    def test_the_runner_slug_is_the_email_local_part(self):
        assert purlin_records.runner_slug('Jane.Doe+x@acme.com') == 'jane-doe-x'
        assert purlin_records.runner_slug('') == 'unknown'

    def test_a_record_a_person_committed_is_labelled_local(self, project):
        """Only the git host's own commit is `ci`; everything else is local."""
        path = project.record([_entry('PROOF-1', 'RULE-1')])
        assert purlin_records.record_label(project.root, path) == 'local'

    def test_an_uncommitted_record_is_local(self, project):
        path = project.record([_entry('PROOF-1', 'RULE-1')], commit_it=False)
        loaded = purlin_records.load_records(project.root)
        assert loaded['login'][None]['label'] == 'local', path

    @pytest.mark.proof("states", "PROOF-5", "RULE-4")
    def test_both_sources_count_at_every_gate(self):
        for gate in ('passed', 'strong', 'signed'):
            for source in ('ci', 'local'):
                assert purlin_records.counts_under(gate, source), (gate,
                                                                   source)
        assert not purlin_records.counts_under('signed',
                                               'developer')  # retired

    def test_the_latest_record_per_feature_per_os(self, project):
        project.record([_entry('PROOF-1', 'RULE-1')], os_name='linux')
        project.record([_entry('PROOF-1', 'RULE-1')], os_name='windows')
        loaded = purlin_records.load_records(project.root)
        assert sorted(k for k in loaded['login']) == ['linux', 'windows']

    def test_a_record_is_at_head_only_for_the_commit_it_observed(self, project):
        record = {'commit': project.head()}
        assert purlin_records.at_head(record, project.head())
        assert not purlin_records.at_head({'commit': 'f' * 40}, project.head())


# ---------------------------------------------------------------------------
# The cells
# ---------------------------------------------------------------------------

STRONG_INPUT = {
    'proofs': [{'id': 'PROOF-1', 'env': None, 'text': 'x',
                'findings': [], 'tests': [{'file': 'tests/t.py',
                                           'name': 'test_x'}]}],
    'records': {None: {'commit': 'a' * 40, 'label': 'ci', 'scope_tree': None,
                       'proofs': [{'id': 'PROOF-1', 'rule': 'RULE-1',
                                   'status': 'pass'}]}},
    'head': 'a' * 40,
    'test_strength': 90,
    'bar': 'strong',
}


def _strong(cfg=None, **overrides):
    """One rule's strong cell, built straight from its evidence."""
    inp = dict(STRONG_INPUT)
    inp.update(overrides)
    cfg = cfg or purlin_gate.resolve_gate({'gate': 'strong'})
    return purlin_states.rule_cells(inp, cfg)['cells']['strong']


class TestTheSpecStatus:

    @pytest.mark.proof("states", "PROOF-1", "RULE-1")
    def test_drafted_when_there_is_no_proof(self, project):
        project.spec('# Feature: login\n\n## Rules\n\n- RULE-1: It works\n\n'
                     '## Proof\n')
        rule = project.rule('RULE-1')
        assert rule['spec'] == 'drafted'
        assert rule['proofs'] == []

    @pytest.mark.proof("states", "PROOF-2", "RULE-2")
    def test_a_proof_a_scan_would_flag_is_still_ready(self, project):
        project.spec('# Feature: login\n\n## Rules\n\n- RULE-1: It works\n\n'
                     '## Proof\n\n- PROOF-1 (RULE-1): Call login and verify it '
                     'works correctly\n')
        rule = project.rule('RULE-1')
        assert rule['spec'] == 'ready'
        assert 'findings' not in rule['proofs'][0], rule['proofs'][0]

    @pytest.mark.proof("states", "PROOF-2", "RULE-2")
    def test_ready_when_a_proof_line_names_the_rule(self, project):
        assert project.rule('RULE-2')['spec'] == 'ready'


class TestThePassedCell:

    @pytest.mark.proof("states", "PROOF-3", "RULE-3")
    def test_a_local_run_meets_level_one_under_the_passed_gate(self, project):
        project.proofs([_entry('PROOF-2', 'RULE-2')])
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed'
        assert (cell['source'], cell['current'], cell['counts']) == (
            'local', True, True)

    @pytest.mark.proof("states", "PROOF-4", "RULE-3")
    def test_a_ci_record_at_head_meets_level_one(self, project):
        project.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                       ci=True)
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'passed'
        assert cell['source'] == 'ci'

    @pytest.mark.proof("states", "PROOF-6", "RULE-5")
    def test_a_local_record_counts_under_strong(self):
        made = Project(gate='strong')
        try:
            made.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                        runner='dev', source='local')
            cell = made.cell('RULE-2', 'passed')
            assert cell['word'] == 'passed', cell
            assert cell['source'] == 'local'
            assert cell['counts'] is True
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-6", "RULE-5")
    def test_a_local_record_counts_under_signed_too(self):
        made = Project(gate='signed')
        try:
            made.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                        runner='dev', source='local')
            cell = made.cell('RULE-2', 'passed')
            assert cell['word'] == 'passed', cell
            assert cell['source'] == 'local'
            assert cell['counts'] is True
            assert cell['reasons'] == [], cell
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-7", "RULE-5")
    def test_this_checkouts_own_run_counts_under_signed_too(self):
        made = Project(gate='signed')
        try:
            made.proofs([_entry('PROOF-2', 'RULE-2')])
            cell = made.cell('RULE-2', 'passed')
            assert cell['word'] == 'passed', cell
            assert cell['source'] == 'local'
            assert cell['counts'] is True
            assert cell['reasons'] == [], cell
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-8", "RULE-6")
    def test_an_env_proof_needs_a_record_from_that_operating_system(self,
                                                                   project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n- RULE-1: Files lock\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Lock a file; verify a second open '
            'returns 0 handles @env(windows)\n')
        project.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}],
                       os_name='linux')
        cell = project.cell('RULE-1', 'passed')
        assert cell['word'] == 'not run'
        assert cell['missing_env'] == ['windows'], cell
        assert 'windows: no record yet' in cell['reasons'], cell
        project.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}],
                       os_name='windows')
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'

    @pytest.mark.proof("states", "PROOF-9", "RULE-7")
    def test_code_changed_when_only_the_code_moved(self, project):
        tree = purlin_specs.scope_tree(project.root, ['src/login.py'])
        project.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}],
                       scope_tree=tree)
        assert project.cell('RULE-1', 'passed')['word'] == 'passed'
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 200  # rewritten\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'refactor: login')
        rule = project.rule('RULE-1')
        cell = rule['cells']['passed']
        assert cell['word'] == 'code changed', cell
        assert cell['reasons'][0].startswith('code changed since '), cell
        assert rule['flags']['code_changed'] is True

    @pytest.mark.proof("states", "PROOF-10", "RULE-8")
    def test_a_rule_no_test_backs_reads_no_test(self, project):
        cell = project.cell('RULE-2', 'passed')
        assert cell['word'] == 'no test'
        assert (cell['source'], cell['current'], cell['counts']) == (
            None, False, False)


class TestTheStrongCell:

    @pytest.mark.proof("states", "PROOF-12", "RULE-10")
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

    @pytest.mark.proof("states", "PROOF-13", "RULE-11")
    def test_a_rule_that_did_not_pass_is_weak_for_that_one_reason(self):
        made = Project(gate='strong')
        try:
            made.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}],
                        ci=True, strength=48)
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'weak'
            assert cell['reasons'] == ['not passed'], cell
            assert cell['strength'] == 48, cell
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-14", "RULE-12")
    def test_a_strength_under_the_minimum_is_weak_and_says_so(self):
        made = Project(gate='strong')
        try:
            made.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                         {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                        ci=True, strength=48)
            made.brief('RULE-1')
            cell = made.cell('RULE-1', 'strong')
            assert cell['word'] == 'weak'
            assert cell['reasons'] == ['strength 48% under 70%'], cell
            assert 'findings' not in cell, cell
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-15", "RULE-13")
    def test_with_no_engine_the_cell_says_nothing_measured_a_strength(self):
        made = Project(gate='strong')
        try:
            made.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                        ci=True, strength=None)
            made.brief('RULE-2')
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'strong', cell
            assert cell['reasons'] == [
                'no engine: nothing measured a strength'], cell
            # A proof a scan would flag no longer holds the rule anywhere:
            # the spec status is `ready` and the strong cell is the audit's.
            made.spec(SPEC.replace(
                '401 and the body "denied"\n\n',
                '401 and the body "denied" [bar: passed]\n\n').replace(
                'POST /login with a bad password; verify 401 and the '
                'body "denied"', 'Check that the login handles it properly'))
            loose = made.rule('RULE-2')
            assert loose['spec'] == 'ready', loose
            assert loose['cells']['strong']['word'] == 'strong', loose
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-16", "RULE-14")
    def test_an_old_brief_field_decides_nothing_and_an_observation_does(self):
        # A brief written before `purlin-brief/5` carried sentences a scan
        # wrote about the test body. The cell reads none of them, so a brief
        # that settled with nothing observed leaves the cell strong.
        old_field = 'hints'  # retired
        cell = _strong(bar='passed', brief={
            'settled': True, 'observations': [],
            'tests': [{'proof': 'PROOF-1',
                       old_field: ['The marked test body holds no assertion.']}]})
        assert cell['word'] == 'strong', cell
        assert 'findings' not in cell, cell
        observed = _strong(brief={
            'settled': True,
            'observations': ['The test reads the status code alone.']})
        assert observed['word'] == 'weak', observed
        assert observed['reasons'] == [
            'The test reads the status code alone.'], observed

    @pytest.mark.proof("states", "PROOF-17", "RULE-15")
    def test_the_brief_settles_level_two_where_the_bar_asks_for_one(self):
        assert _strong()['word'] == 'not audited'
        assert _strong()['reasons'] == ['no audit has run on this code']
        open_question = _strong(brief={'settled': False, 'observations': [],
                                       'ai_review': 'settled: no'})
        assert open_question['word'] == 'unsettled', open_question
        assert open_question['reasons'] == [
            'the AI audit could not settle'], open_question
        settled = _strong(brief={'settled': True, 'observations': [],
                                 'ai_review': 'settled: yes'})
        assert settled['word'] == 'strong', settled
        no_model = _strong(brief={'settled': None, 'observations': [],
                                  'ai_review': purlin_states.NO_MODEL})
        assert no_model['word'] == 'strong', (
            'no model was reached, so no question was left open')

    @pytest.mark.proof("states", "PROOF-18", "RULE-15")
    def test_a_passed_bar_reads_neither_of_the_two_audit_words(self):
        lower = _strong(bar='passed')
        assert lower['word'] == 'strong', lower
        assert _strong(bar='strong')['word'] == 'not audited'

    @pytest.mark.proof("states", "PROOF-19", "RULE-16")
    def test_a_manual_proof_asks_for_a_manual_test(self):
        cell = _strong(bar='passed', proofs=[
            {'id': 'PROOF-1', 'manual': True, 'env': None, 'text': 'x',
             'findings': [], 'tests': []}])
        assert cell['word'] == 'manual test'
        assert cell['reasons'] == ['manual proof'], cell

    @pytest.mark.proof("states", "PROOF-23", "RULE-19")
    def test_a_strong_cell_with_an_engine_carries_no_reasons(self):
        made = Project(gate='strong')
        try:
            made.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                        ci=True, strength=90)
            made.brief('RULE-2')
            cell = made.cell('RULE-2', 'strong')
            assert cell['word'] == 'strong'
            assert cell['reasons'] == [], cell
        finally:
            made.close()


class TestHoldsAndSignatures:
    """What a person's committed attestation does to the top two cells."""

    @staticmethod
    def _signed_project():
        made = Project(gate='signed')
        made.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                     {'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                    ci=True, strength=90)
        # Both rules carry the `strong` bar the `signed` gate derives, so the
        # AI audit is owed on each and the strong cell reads `not audited`
        # until a brief exists.
        made.brief('RULE-1')
        made.brief('RULE-2')
        return made

    @pytest.mark.proof("states", "PROOF-20", "RULE-17")
    def test_a_current_hold_puts_the_rule_in_front_of_a_person(self):
        made = self._signed_project()
        try:
            made.hold('RULE-2', 'no case for an expired token')
            rule = made.rule('RULE-2')
            assert rule['cells']['strong']['word'] == 'held'
            assert rule['cells']['strong']['reasons'] == [
                'held by jane@acme.com: no case for an expired token'], rule
            assert rule['cells']['signed']['word'] == 'held'
            assert rule['flags']['held'] is True
            assert rule['flags']['manual'] is False
            assert rule['flags']['unsettled'] is False
            assert rule['flags']['not_audited'] is False
            assert rule['meets_gate'] is False
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-21", "RULE-17")
    def test_a_hold_bound_to_other_hashes_does_nothing(self):
        made = self._signed_project()
        try:
            made.hold('RULE-2', 'no case for an expired token',
                      test_hash='0' * 64)
            rule = made.rule('RULE-2')
            assert rule['cells']['strong']['word'] == 'strong', rule
            assert rule['flags']['held'] is False
            assert not any('held by' in reason for reason
                           in rule['cells']['strong']['reasons'])
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-22", "RULE-18")
    def test_a_signature_for_the_same_hashes_outranks_the_hold(self):
        made = self._signed_project()
        try:
            made.hold('RULE-2', 'no case for an expired token')
            made.sign_commits()
            made.signature('RULE-2')
            rule = made.rule('RULE-2')
            assert rule['cells']['strong']['word'] == 'strong', rule
            assert rule['cells']['signed']['word'] == 'signed', rule
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-24", "RULE-20")
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

    @pytest.mark.proof("states", "PROOF-25", "RULE-21")
    def test_a_signature_is_needed_by_the_rules_bar(self):
        made = self._signed_project()
        try:
            made.spec(SPEC.replace(
                '- RULE-2: Invalid credentials return 401 and the body '
                '"denied"',
                '- RULE-2: Invalid credentials return 401 and the body '
                '"denied" [bar: passed]'))
            lower = made.cell('RULE-2', 'signed')
            assert (lower['word'], lower['required']) == ('unsigned', False)
            assert purlin_states.cell_is_met('signed', lower)
            higher = made.cell('RULE-1', 'signed')
            assert (higher['word'], higher['required']) == ('unsigned', True)
            assert not purlin_states.cell_is_met('signed', higher)
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-65", "RULE-56")
    def test_sign_at_all_asks_for_a_signature_on_every_rule(self):
        made = self._signed_project()
        try:
            made.spec(SPEC.replace(
                '- RULE-2: Invalid credentials return 401 and the body '
                '"denied"',
                '- RULE-2: Invalid credentials return 401 and the body '
                '"denied" [bar: passed]'))
            assert made.cell('RULE-2', 'signed')['required'] is False
            made.config_value('sign_at', 'all')
            assert made.cell('RULE-2', 'signed')['required'] is True
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-26", "RULE-22")
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
    '- RULE-1: A drafted rule names no proof [bar: passed]\n'
    '- RULE-2: A failing rule has a test that fails [bar: passed]\n'
    '- RULE-3: A passed rule is held by a person [bar: passed]\n'
    '- RULE-4: A strong rule has no signature yet [bar: strong]\n'
    '- RULE-5: A signed rule carries one [bar: strong]\n\n'
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
    made.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'fail'},
                 {'id': 'PROOF-3', 'rule': 'RULE-3', 'status': 'pass'},
                 {'id': 'PROOF-4', 'rule': 'RULE-4', 'status': 'pass'},
                 {'id': 'PROOF-5', 'rule': 'RULE-5', 'status': 'pass'}],
                feature='ledger', ci=True, strength=90)
    made.hold('RULE-3', 'the lock expiry is never read', feature='ledger',
              category='core')
    # The two rules whose bar is `strong` are the ones the AI audit is owed
    # on, so each carries a brief that settled.
    made.brief('RULE-4', feature='ledger')
    made.brief('RULE-5', feature='ledger')
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

    @pytest.mark.proof("states", "PROOF-51", "RULE-43")
    def test_one_entry_per_operating_system_a_counting_run_named(self):
        made = Project(gate='strong')
        try:
            made.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                         {'id': 'PROOF-2', 'rule': 'RULE-2',
                          'status': 'pass'}],
                        os_name='linux', source='ci')
            made.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                         {'id': 'PROOF-2', 'rule': 'RULE-2',
                          'status': 'pass'}],
                        os_name='windows', source='ci',
                        stamp='20260913T130000Z')
            cell = made.cell('RULE-1', 'passed')
            assert sorted(cell['platforms']) == ['linux', 'windows'], cell
            for name, entry in cell['platforms'].items():
                assert entry['word'] == 'passed', (name, entry)
                assert entry['source'] == 'ci', (name, entry)
                assert entry['at'] == '2026-09-13T12:00:00Z', (name, entry)
            assert cell['word'] == 'passed', cell
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-52", "RULE-43")
    def test_a_platform_a_proof_asks_for_and_nothing_ran_on_is_listed(self):
        made = Project(spec=ENV_SPEC, gate='strong')
        try:
            made.record([{'id': 'PROOF-1', 'rule': 'RULE-1',
                          'status': 'pass'}],
                        os_name='linux', source='ci')
            cell = made.cell('RULE-1', 'passed')
            assert cell['platforms']['windows'] == {
                'word': 'not run', 'source': None, 'at': None}, cell
            assert cell['platforms']['linux']['word'] == 'passed', cell
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-53", "RULE-44")
    def test_platforms_that_disagree_read_partial(self):
        made = Project(spec=ENV_SPEC, gate='strong')
        try:
            made.record([{'id': 'PROOF-1', 'rule': 'RULE-1',
                          'status': 'pass'}],
                        os_name='linux', source='ci')
            made.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'},
                         {'id': 'PROOF-2', 'rule': 'RULE-1',
                          'status': 'fail'}],
                        os_name='windows', source='ci',
                        stamp='20260913T130000Z')
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

    @pytest.mark.proof("states", "PROOF-54", "RULE-45")
    def test_a_run_that_named_no_operating_system_answers_as_one(self):
        made = Project(gate='strong')
        try:
            made.record([{'id': 'PROOF-1', 'rule': 'RULE-1',
                          'status': 'pass'}],
                        source='ci', environment_os='none')
            cell = made.cell('RULE-1', 'passed')
            assert cell['platforms'] == {}, cell
            assert cell['word'] == 'passed', cell
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-50", "RULE-42")
    def test_a_record_whose_source_field_disagrees_is_left_out(self):
        made = Project(gate='strong')
        try:
            path = made.record([{'id': 'PROOF-1', 'rule': 'RULE-1',
                                 'status': 'pass'}],
                               source='ci', claimed_source='local')
            data = made.payload()
            assert made.cell('RULE-1', 'passed')['word'] != 'passed'
            named = [w for w in data['warnings'] if path in w]
            assert len(named) == 1, data['warnings']
            assert 'folder and its source field must agree' in named[0]
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-66", "RULE-57")
    def test_this_checkouts_own_run_answers_for_its_platform_at_every_gate(self):
        """A local run is a platform's answer at `signed` as at `strong`.

        Both sources count at every gate, so a red macOS run beside a green
        Linux record reads `partial` wherever the gate is set, and a local
        run with no record at all reads `passed`.
        """
        def cells(gate, local_status, records):
            return purlin_states.rule_cells({
                'proofs': [{'id': 'PROOF-1', 'env': None,
                            'text': 'x',
                            'tests': [{'file': 'tests/t.py',
                                       'name': 'test_x'}]}],
                'local_status': local_status, 'local_os': 'macos',
                'local_at': '2026-09-26T12:00:00Z',
                'records': records, 'head': 'abc1234', 'bar': 'passed',
            }, purlin_gate.resolve_gate({'gate': gate}))['cells']['passed']

        linux = {'linux': {'source': 'ci', 'os': 'linux',
                           'timestamp': '2026-09-25T12:00:00Z',
                           'commit': 'abc1234',
                           'proofs': [{'id': 'PROOF-1', 'status': 'pass'}]}}
        for gate in ('strong', 'signed'):
            cell = cells(gate, {'PROOF-1': 'fail'}, linux)
            assert cell['word'] == 'partial', (gate, cell)
            assert sorted(cell['platforms']) == ['linux', 'macos'], cell

        alone = cells('signed', {'PROOF-1': 'pass'}, {})
        assert alone['word'] == 'passed', alone
        assert alone['counts'] is True, alone
        assert alone['reasons'] == [], alone

    @pytest.mark.proof("states", "PROOF-55", "RULE-46")
    def test_with_no_record_at_all_the_strong_cell_says_no_audit_has_run(self):
        cfg = purlin_gate.resolve_gate({'gate': 'strong'})
        cell = purlin_states.rule_cells({
            'proofs': [{'id': 'PROOF-1', 'env': None,
                        'text': 'x', 'findings': [],
                        'tests': [{'file': 'tests/t.py', 'name': 'test_x'}]}],
            'local_status': {'PROOF-1': 'pass'},
            'records': {}, 'audited': False, 'bar': 'passed',
        }, cfg)['cells']['strong']
        assert cell['word'] == 'weak', cell
        assert cell['reasons'] == ['no audit has run'], cell


class TestBucketsAndTheGate:

    @pytest.mark.proof("states", "PROOF-27", "RULE-23")
    def test_one_rule_in_each_of_the_five_buckets(self):
        made = _five_bucket_project()
        try:
            buckets = [made.rule('RULE-%d' % n, 'ledger')['bucket']
                       for n in range(1, 6)]
            assert buckets == ['untested', 'failing', 'passed', 'strong',
                               'signed'], buckets
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-27", "RULE-23")
    def test_partial_sits_between_failing_and_passed(self):
        assert purlin_states.BUCKETS == ('untested', 'failing', 'partial',
                                         'passed', 'strong', 'signed')
        assert purlin_states.bucket_keys('passed') == [
            'untested', 'failing', 'partial', 'passed']

    @pytest.mark.proof("states", "PROOF-28", "RULE-24")
    def test_the_gate_is_met_by_one_of_them_and_blocked_by_name(self):
        made = _five_bucket_project()
        try:
            rules = [made.rule('RULE-%d' % n, 'ledger') for n in range(1, 6)]
            assert [r['meets_gate'] for r in rules] == [
                False, False, False, False, True]
            assert [r['blocked_by'] for r in rules] == [
                'spec', 'passed', 'strong', 'signed', None]
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The payload
# ---------------------------------------------------------------------------

class TestPayload:

    @pytest.mark.proof("states", "PROOF-31", "RULE-27")
    def test_schema_six_carries_the_documented_top_level(self, project):
        data = project.payload()
        assert data["schema_version"] == 8
        for key in ('generated_at', 'generated_by', 'project', 'version',
                    'commit', 'dirty', 'gate', 'summary', 'features',
                    'review_list', 'sign_list', 'records', 'remote_url',
                    'warnings'):
            assert key in data, key
        assert data['gate']['gate'] == 'passed'
        assert data['generated_at'].endswith('Z')
        # A project with no remote gets null rather than a broken link.
        assert data['remote_url'] is None
        _git(project.root, 'remote', 'add', 'origin',
             'https://github.com/acme/ledger.git')
        assert project.payload()['remote_url'] == (
            'https://github.com/acme/ledger.git')

    @pytest.mark.proof("states", "PROOF-32", "RULE-28")
    def test_a_feature_carries_its_rules_with_their_tags_and_proofs(self,
                                                                   project):
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
        assert feature['spec_path'] == 'specs/auth/login.md'
        assert feature['category'] == 'auth'
        assert feature['signatures'] == []
        rule = next(r for r in feature['rules'] if r['id'] == 'RULE-1')
        assert (rule['bar'], rule['bar_from']) == ('strong', 'tag')
        assert 'origin' not in rule and 'criterion' not in rule
        assert rule['proofs'][0]['manual'] is False
        assert rule['proofs'][0]['env'] is None

    @pytest.mark.proof("states", "PROOF-29", "RULE-25")
    def test_the_rollup_counts_the_buckets_the_gate_reaches(self, project):
        project.proofs([_entry('PROOF-2', 'RULE-2')])
        data = project.payload()
        feature = next(f for f in data['features'] if f['name'] == 'login')
        rollup = feature['rollup']
        assert sorted(rollup) == sorted([
            'rules', 'met', 'untested', 'failing', 'partial', 'passed',
            'stale', 'held', 'manual', 'unsettled', 'not_audited',
            'signable', 'test_strength', 'latest_record', 'proofs',
            'proofs_without_test', 'proofs_without_test_ids']), rollup
        assert (rollup['rules'], rollup['met']) == (2, 1)
        assert (rollup['passed'], rollup['untested']) == (1, 1), rollup
        assert (rollup['partial'], rollup['failing']) == (0, 0), rollup
        assert rollup['proofs'] == 2, rollup
        assert rollup['proofs_without_test'] == 1, (
            'PROOF-1 has no test; PROOF-2 was observed by the local run')
        assert rollup['proofs_without_test_ids'] == ['PROOF-1'], rollup
        assert data['summary']['features'] == 1

    @pytest.mark.proof("states", "PROOF-57", "RULE-48")
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
        project.proofs([_entry('PROOF-1', 'RULE-1')])
        rollup = next(f for f in project.payload()['features']
                      if f['name'] == 'login')['rollup']
        assert rollup['proofs'] == 3, rollup
        assert rollup['proofs_without_test'] == 1, rollup
        assert rollup['proofs_without_test_ids'] == ['PROOF-2'], rollup

    @pytest.mark.proof("states", "PROOF-56", "RULE-47")
    def test_the_signed_cell_carries_when_it_was_signed(self):
        made = Project(gate='signed')
        try:
            made.sign_commits()
            made.signature('RULE-2')
            cell = made.cell('RULE-2', 'signed')
            assert cell['signer'] == 'jane@acme.com'
            assert cell['at'] and cell['at'].endswith('Z'), cell
            assert len(cell['at']) == 20, cell
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-30", "RULE-26")
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

    @pytest.mark.proof("states", "PROOF-39", "RULE-34")
    def test_a_record_carries_the_result_of_the_run_it_names(self, project):
        """Two operating systems, one run each: one failed, one passed."""
        project.record([{'id': 'PROOF-1', 'status': 'pass'},
                        {'id': 'PROOF-2', 'status': 'fail'}], os_name='linux')
        project.record([{'id': 'PROOF-1', 'status': 'pass'},
                        {'id': 'PROOF-2', 'status': 'pass'}],
                       os_name='windows')
        records = project.payload()['records']['login']
        assert records['linux']['result'] == 'fail'
        assert records['windows']['result'] == 'pass'
        assert records['linux']['label'] == 'local'
        assert records['windows']['label'] == 'local'
        assert records['linux']['source'] == 'local'

    @pytest.mark.proof("states", "PROOF-37", "RULE-32")
    def test_the_data_file_is_a_const_assignment_and_round_trips(self, project):
        data = project.payload()
        path = purlin_payload.write_report_data(project.root, data)
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        assert text.startswith('const PURLIN_DATA = ') and text.endswith(';\n')
        assert purlin_payload.read_report_payload(project.root)['commit'] == (
            data['commit'])

    @pytest.mark.proof("states", "PROOF-38", "RULE-33")
    def test_an_unchanged_payload_is_touched_rather_than_rewritten(self,
                                                                  project):
        purlin_payload.write_report_data(project.root, project.payload())
        path = purlin_payload.report_data_path(project.root)
        before = open(path, 'rb').read()
        os.utime(path, (0, 0))
        purlin_payload.write_report_data(project.root, project.payload(),
                                         only_if_changed=True)
        assert open(path, 'rb').read() == before
        assert os.stat(path).st_mtime > 0


class TestTheFixturesAreTheContract:
    """The dashboard's fixtures and the builder's output are one shape.

    `dev/fixtures/report/{solo,team,regulated}.json` are written by hand from
    the plan, and the dashboard is built against them. A key the builder adds
    and the fixtures do not carry would render nowhere, so the two are
    compared key by key here rather than by eye.
    """

    FIXTURES = os.path.join(PROJECT_ROOT, 'dev', 'fixtures', 'report')

    @staticmethod
    def _fixture(name):
        with open(os.path.join(TestTheFixturesAreTheContract.FIXTURES,
                               name + '.json'), encoding='utf-8') as handle:
            return json.load(handle)

    @pytest.mark.proof("states", "PROOF-31", "RULE-27")
    @pytest.mark.proof("states", "PROOF-29", "RULE-25")
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
            assert sorted(rule['flags']) == sorted(purlin_states.FLAGS), name

    @pytest.mark.proof("states", "PROOF-68", "RULE-59")
    def test_the_tag_key_is_present_in_every_fixture(self):
        """The board's chip reads this key, so a fixture without it is a lie."""
        for name in ('solo', 'team'):
            assert self._fixture(name)['tag'] is None, name
        tag = self._fixture('regulated')['tag']
        assert sorted(tag) == ['commit', 'name']
        assert tag['name'].startswith('signed/')
        assert tag['commit'] == self._fixture('regulated')['commit']

    @pytest.mark.proof("states", "PROOF-34", "RULE-30")
    def test_every_fixture_review_row_uses_the_closed_set(self):
        at_strong = {'manual test', 'unsettled', 'held'}
        at_signed = {'unsigned', 'stale', 'held'}
        keys = ['bar', 'cell', 'feature', 'kind', 'owner', 'rule', 'why']
        for name in ('solo', 'team', 'regulated'):
            fixture = self._fixture(name)
            for key, allowed in (('review_list', at_strong),
                                 ('sign_list', at_signed)):
                for row in fixture[key]:
                    assert sorted(row) == keys, row
                    assert row['kind'] in allowed, row
                    assert row['why'] == [row['kind']], row


# ---------------------------------------------------------------------------
# The status table
# ---------------------------------------------------------------------------

class TestStatusTable:

    @pytest.mark.proof("states", "PROOF-58", "RULE-49")
    def test_the_table_and_the_board_render_the_same_cells(self):
        """One module renders both, so a cell cannot read two ways."""
        for name, gate in (('solo', 'passed'), ('team', 'strong'),
                           ('regulated', 'signed')):
            fixture = TestTheFixturesAreTheContract._fixture(name)
            columns = purlin_status.columns_for(gate)
            assert columns == purlin_board.columns_for(gate), name
            for feature in fixture['features']:
                row = purlin_status._row(feature, gate)
                board = purlin_board.row_cells(feature['name'],
                                               feature['rollup'], gate)
                assert row[1:] == board[1:], (name, feature['name'], row)
                assert len(row) == len(columns), (name, row)

    @pytest.mark.proof("states", "PROOF-58", "RULE-49")
    def test_the_board_cells_read_the_way_the_fixtures_say(self):
        fixture = TestTheFixturesAreTheContract._fixture('regulated')
        cells = {f['name']: purlin_board.row_cells(
            f['name'], f['rollup'], 'signed') for f in fixture['features']}
        assert cells['login'] == ('login', '4', '5', '3 of 4 · 1 partial',
                                  '2 of 4 · 86%', '1 of 4',
                                  '1 of 4'), cells['login']
        assert cells['invoice'] == ('invoice', '3', '3', '3 of 3',
                                    '0 of 3 · 64%', '0 of 3',
                                    '0 of 3'), cells['invoice']
        team = TestTheFixturesAreTheContract._fixture('team')
        rows = {f['name']: purlin_board.row_cells(
            f['name'], f['rollup'], 'strong') for f in team['features']}
        assert rows['invoice'] == ('invoice', '2', '2 · 1 without a test',
                                   '1 of 2', '0 of 2 · 48%'), rows['invoice']

    @pytest.mark.proof("states", "PROOF-43", "RULE-36")
    def test_the_columns_scale_with_the_gate(self, project):
        project.proofs([_entry('PROOF-2', 'RULE-2')])
        text = purlin_status.sync_status(project.root)
        header = next(line for line in text.splitlines()
                      if line.startswith('Spec'))
        for column in ('Spec', 'Rules', 'Proofs', 'Tests'):
            assert column in header, (column, header)
        assert 'Strong' not in header and 'Signed' not in header, header
        row = next(line for line in text.splitlines()
                   if line.startswith('login '))
        assert '1 of 2' in row, row
        assert '2 · 1 without a test' in row, row

        for gate, expected in (('strong', ('Strong',)),
                               ('signed', ('Strong', 'Signable', 'Signed'))):
            made = Project(gate=gate)
            try:
                text = purlin_status.sync_status(made.root)
                header = next(line for line in text.splitlines()
                              if line.startswith('Spec'))
                for column in expected:
                    assert column in header, (gate, header)
                row = next(line for line in text.splitlines()
                           if line.startswith('login '))
                assert 'n/a' in row, 'no record, so no test strength'
            finally:
                made.close()

    @pytest.mark.proof("states", "PROOF-44", "RULE-37")
    def test_the_summary_counts_the_rules_that_meet_the_gate(self, project):
        project.proofs([_entry('PROOF-2', 'RULE-2')])
        text = purlin_status.sync_status(project.root)
        line = next(line for line in text.splitlines()
                    if 'meet the gate' in line)
        assert line == '1 of 2 rules meet the gate passed.', line
        second = text.splitlines()[text.splitlines().index(line) + 1]
        assert 'test strength' not in second, second
        assert 'signature' not in second, second

    @pytest.mark.proof("states", "PROOF-45", "RULE-38")
    def test_the_table_ends_with_one_next_step(self, project):
        text = purlin_status.sync_status(project.root)
        directives = [line for line in text.splitlines()
                      if line.startswith('→ Next:')]
        assert len(directives) == 1, text
        assert 'purlin:build' in directives[0], directives[0]

    @pytest.mark.proof("states", "PROOF-67", "RULE-58")
    def test_the_next_step_names_the_command_this_gate_would_write_with(self):
        """An audit you run counts at every gate, so it is the shortest way.

        Only `trust: remote` sends a reader to the runner, because that is
        the one setting that asks for a `ci` run before a signature.
        """
        for gate, trust, named, unnamed in (
                ('strong', 'local', 'purlin:audit', 'purlin:test --remote'),
                ('signed', 'local', 'purlin:audit', 'purlin:test --remote'),
                ('signed', 'remote', 'purlin:test --remote', 'purlin:audit')):
            made = Project(gate=gate, extra_config={'trust': trust})
            try:
                made.record([{'id': 'PROOF-1', 'rule': 'RULE-1',
                              'status': 'pass'},
                             {'id': 'PROOF-2', 'rule': 'RULE-2',
                              'status': 'pass'}],
                            source='ci', commit='0' * 40,
                            scope_tree='the code has moved on')
                step = [line for line in
                        purlin_status.sync_status(made.root).splitlines()
                        if line.startswith('→ Next:')]
                assert len(step) == 1, step
                assert named in step[0], (gate, trust, step[0])
                assert unnamed not in step[0], (gate, trust, step[0])
            finally:
                made.close()
        assert purlin_board.needs_a_person(1) == '1 rule needs a person'
        assert purlin_board.needs_a_person(3) == '3 rules need a person'
        assert purlin_board.needs_a_person(0) == 'no rule needs a person'

    @pytest.mark.proof("states", "PROOF-48", "RULE-41")
    def test_retired_config_keys_print_the_update_directive(self):
        made = Project(extra_config={'spec_dir': 'elsewhere'})
        try:
            text = purlin_status.sync_status(made.root)
            assert '→ Run: purlin:init --update' in text, text
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-46", "RULE-39")
    def test_an_empty_project_says_what_to_run(self):
        made = Project(spec=None)
        try:
            text = purlin_status.sync_status(made.root)
            assert 'No specs found' in text and 'purlin:init' in text
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-47", "RULE-40")
    def test_no_emoji_and_only_the_four_glyphs(self, project):
        text = purlin_status.sync_status(project.root)
        allowed = set('→▶▼─')
        for char in text:
            assert ord(char) < 0x2000 or char in allowed, repr(char)

    @pytest.mark.proof("states", "PROOF-49", "RULE-36")
    def test_the_repository_own_specs_print_the_table(self):
        text = purlin_status.sync_status(PROJECT_ROOT)
        header = next(line for line in text.splitlines()
                      if line.startswith('Spec'))
        assert 'Proofs' in header and 'Tests' in header, header
        assert any('of' in line for line in text.splitlines()), text
        assert text.rstrip().splitlines()[-1].startswith('→'), text


# ---------------------------------------------------------------------------
# Drift
# ---------------------------------------------------------------------------

class TestDriftRoles:

    @pytest.mark.proof("drift", "PROOF-16", "RULE-14")
    def test_the_three_role_views_are_present(self, project):
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 401\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'fix: login')
        report = json.loads(purlin_drift.drift(project.root, since='1'))
        assert sorted(report['roles']) == ['eng', 'pm', 'qa']
        assert 'src/login.py' in report['roles']['eng']['files_touched']
        assert report['roles']['eng']['tests_missing'] == [
            'login/RULE-1', 'login/RULE-2']

    @pytest.mark.proof("drift", "PROOF-17", "RULE-15")
    def test_a_role_narrows_the_report(self, project):
        report = json.loads(purlin_drift.drift(project.root, since='1',
                                               role='qa'))
        assert report['role'] == 'qa'
        assert sorted(report['view']) == [
            'manual', 'not_audited', 'review_list_size', 'sign_list_size',
            'signatures_stale', 'unsettled']

    @pytest.mark.proof("drift", "PROOF-2", "RULE-1")
    def test_a_hostile_since_never_reaches_git(self, project):
        report = json.loads(purlin_drift.drift(project.root,
                                               since='--output=/tmp/x'))
        assert report['error'] == 'rejected since'

    @pytest.mark.proof("drift", "PROOF-13", "RULE-11")
    def test_a_source_that_is_not_safe_is_refused_before_any_process(self):
        for value, reason in (('--upload-pack=/bin/echo', 'begins with "-"'),
                              ('ext::sh -c id', 'names an ext:: transport'),
                              ('fd::7', 'names an fd:: transport')):
            safe, got = purlin_drift.source_url_is_safe(value)
            assert safe is False and got == reason, (value, got)
        assert purlin_drift.source_url_is_safe(
            'https://github.com/acme/p.git') == (True, '')

    @pytest.mark.proof("drift", "PROOF-14", "RULE-12")
    def test_one_ls_remote_per_source_per_run(self, project, monkeypatch):
        calls = []
        real_run = purlin_drift.subprocess.run

        def spy(args, *rest, **kwargs):
            calls.append(list(args))
            return real_run(args, *rest, **kwargs)

        monkeypatch.setattr(purlin_drift.subprocess, 'run', spy)
        cache = {}
        for _ in range(3):
            purlin_drift.check_pin(project.root,
                                   'https://github.invalid/acme/p.git',
                                   'abc1234', cache)
        assert len([c for c in calls if 'ls-remote' in c]) == 1, calls


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

    @pytest.mark.proof("server", "PROOF-1", "RULE-1")
    @pytest.mark.proof("server", "PROOF-5", "RULE-5")
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

    @pytest.mark.proof("server", "PROOF-2", "RULE-2")
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

    @pytest.mark.proof("server", "PROOF-9", "RULE-9")
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
        assert 'commits' in report and 'files' in report

    @pytest.mark.proof("server", "PROOF-7", "RULE-7")
    def test_a_root_with_no_workspace_says_so_rather_than_reporting_nothing(
            self, tmp_path):
        responses, _stderr = _rpc(str(tmp_path), {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'sync_status', 'arguments': {}}})
        text = responses[0]['result']['content'][0]['text']
        assert 'No Purlin workspace' in text and 'purlin:init' in text

    @pytest.mark.proof("server", "PROOF-3", "RULE-3")
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

    @pytest.mark.proof("server", "PROOF-4", "RULE-4")
    def test_an_unknown_tool_and_an_unknown_method_are_errors(self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
             'params': {'name': 'nope', 'arguments': {}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'nope/at/all'})
        assert responses[0]['error']['code'] == -32601
        assert responses[1]['error']['code'] == -32601

    @pytest.mark.proof("server", "PROOF-6", "RULE-6")
    def test_project_root_can_be_named_per_call(self, project, tmp_path):
        responses, _stderr = _rpc(str(tmp_path), {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'sync_status',
                       'arguments': {'project_root': project.root}}})
        assert 'login' in responses[0]['result']['content'][0]['text']

    @pytest.mark.proof("server", "PROOF-8", "RULE-8")
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

    @pytest.mark.proof("server", "PROOF-10", "RULE-10")
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


class TestDigest:

    @pytest.mark.proof("server", "PROOF-11", "RULE-11")
    def test_generate_digest_writes_the_data_file(self, project):
        path = purlin_srv.generate_digest(project.root,
                                             generated_by='hook',
                                             network=False)
        assert path and os.path.isfile(path)
        data = purlin_payload.read_report_payload(project.root)
        assert data['generated_by'] == 'hook'
        assert data["schema_version"] == 8

    @pytest.mark.proof("server", "PROOF-12", "RULE-12")
    def test_a_project_with_no_config_writes_nothing(self, tmp_path):
        assert purlin_srv.generate_digest(str(tmp_path)) is None


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

    def test_the_old_server_module_is_gone(self):
        assert not os.path.exists(
            os.path.join(PROJECT_ROOT, 'scripts', 'mcp', 'purlin_srv.py'))

    @pytest.mark.proof("server", "PROOF-22", "RULE-22")
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

    @pytest.mark.proof("states", "PROOF-68", "RULE-59")
    def test_no_tag_reads_none_and_a_tag_on_head_reads_its_name(self):
        made = Project()
        try:
            assert made.payload()['tag'] is None
            _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
            tag = made.payload()['tag']
            assert tag['name'] == 'signed/1.2.0', tag
            assert tag['commit'] == made.head(), tag
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-68", "RULE-59")
    def test_a_tag_that_is_not_on_head_says_nothing_about_this_code(self):
        made = Project()
        try:
            _git(made.root, 'tag', '-a', 'signed/1.2.0', '-m', 'a release')
            _write(os.path.join(made.root, 'src', 'later.py'), 'X = 1\n')
            _git(made.root, 'add', '-A')
            _git(made.root, 'commit', '-q', '-m', 'feat: more')
            assert made.payload()['tag'] is None
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-68", "RULE-59")
    def test_the_newest_version_wins_where_several_point_at_head(self):
        made = Project()
        try:
            for name in ('signed/1.9.0', 'signed/1.10.0', 'signed/beta'):
                _git(made.root, 'tag', '-a', name, '-m', name)
            assert made.payload()['tag']['name'] == 'signed/1.10.0'
        finally:
            made.close()
