"""Tests for the core package `scripts/mcp/purlin/`.

Six areas, in the order a project meets them: what a spec parses to, what a
test run leaves behind, how ids are allocated, what state each rule is in,
what the payload and the status table say about it, and what the MCP
transport answers.

Every fixture is written by the test: a spec, a runtime proof file, a record
under `.purlin/records/`, an approval beside the spec. Nothing here reads the
repository's own specs except where a test says so.
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

from purlin import approvals as purlin_approvals
from purlin import checks as purlin_checks
from purlin import drift as purlin_drift
from purlin import frameworks as purlin_frameworks
from purlin import gate as purlin_gate
from purlin import ids as purlin_ids
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

def _git(root, *args):
    return subprocess.run(['git'] + list(args), cwd=root, capture_output=True,
                          text=True)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


SPEC = (
    '# Feature: login\n\n'
    '> Description: Signing in with an email and a password.\n'
    '> Scope: src/login.py\n\n'
    '## Rules\n\n'
    '- RULE-1: Valid credentials return 200 with a session token [risk: high] '
    '[origin: pm] [criterion: US-12]\n'
    '- RULE-2: Invalid credentials return 401 and the body "denied"\n\n'
    '## Proof\n\n'
    '- PROOF-1 (RULE-1): POST /login with valid credentials; verify 200 and a '
    'token @integration\n'
    '- PROOF-2 (RULE-2): POST /login with a bad password; verify 401 and the '
    'body "denied"\n'
)


class Project(object):
    """A throwaway project root with git, a config and one spec."""

    def __init__(self, spec=SPEC, gate='tested', extra_config=None):
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

    def proofs(self, entries, feature='login', tier='unit'):
        _write(os.path.join(self.root, '.purlin', 'runtime', 'proofs',
                            '%s.%s.json' % (feature, tier)),
               json.dumps({'tier': tier, 'proofs': entries}))

    def record(self, proofs, feature='login', runner='ci', os_name=None,
               commit=None, scope_tree=None, strength=90, commit_it=True):
        stamp = '20260913T120000Z'
        name = '%s-%s-%s%s.json' % (stamp, (commit or self.head())[:7], runner,
                                    '-' + os_name if os_name else '')
        path = os.path.join(self.root, '.purlin', 'records', feature, name)
        _write(path, json.dumps({
            'schema_version': 1,
            'feature': feature,
            'commit': commit or self.head(),
            'timestamp': '2026-09-13T12:00:00Z',
            'runner': runner,
            'os': os_name,
            'test_strength': strength,
            'scope_tree': scope_tree,
            'proofs': proofs,
        }))
        if commit_it:
            _git(self.root, 'add', '-A')
            _git(self.root, 'commit', '-q', '-m', 'purlin: record')
        return os.path.relpath(path, self.root).replace(os.sep, '/')

    def approval(self, rule_id, data, feature='login', category='auth',
                 slug='jane'):
        directory = os.path.join(self.root, 'specs', category,
                                 feature + '.approvals')
        name = '%s.%s.%s.json' % (rule_id, data['rule_hash'][:8], slug)
        _write(os.path.join(directory, name), json.dumps(data))
        return os.path.join(directory, name)

    def payload(self):
        return purlin_payload.build_payload(self.root)

    def rule(self, rule_id, feature='login'):
        data = self.payload()
        entry = next(f for f in data['features'] if f['name'] == feature)
        return next(r for r in entry['rules'] if r['id'] == rule_id)


@pytest.fixture
def project():
    made = Project()
    yield made
    made.close()


def _entry(proof_id, rule_id, status='pass', feature='login',
           test_file='tests/test_login.py'):
    return {'feature': feature, 'id': proof_id, 'rule': rule_id,
            'status': status, 'tier': 'unit', 'test_file': test_file,
            'test_name': 'test_' + proof_id.lower().replace('-', '_')}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class TestSpecParsing:

    @pytest.mark.proof("specs", "PROOF-1", "RULE-1", tier="integration")
    @pytest.mark.proof("specs", "PROOF-3", "RULE-2", tier="integration")
    def test_rule_tags_are_read_off_the_end_and_stripped(self, project):
        info = purlin_specs.scan_specs(project.root)['login']
        assert info['rules']['RULE-1'] == (
            'Valid credentials return 200 with a session token'), info['rules']
        assert info['rule_meta']['RULE-1'] == {
            'risk': 'high', 'origin': 'pm', 'criterion': 'US-12'}
        # The defaults, for a rule that names none of them.
        assert info['rule_meta']['RULE-2'] == {'risk': 'low', 'origin': 'eng'}

    @pytest.mark.proof("specs", "PROOF-2", "RULE-1")
    def test_tag_order_does_not_matter(self):
        first, meta = purlin_specs.split_rule_tags(
            'Tokens expire [origin: qa] [risk: medium]')
        second, other = purlin_specs.split_rule_tags(
            'Tokens expire [risk: medium] [origin: qa]')
        assert first == second == 'Tokens expire'
        assert meta == other == {'risk': 'medium', 'origin': 'qa'}

    @pytest.mark.proof("specs", "PROOF-4", "RULE-3")
    def test_the_hash_ignores_the_tags_and_the_whitespace(self):
        plain = purlin_specs.rule_text_hash('Tokens expire after 24 hours')
        tagged, _meta = purlin_specs.split_rule_tags(
            'Tokens  expire   after 24 hours [risk: high]')
        assert purlin_specs.rule_text_hash(tagged) == plain, (
            're-tagging or reflowing a rule must not stale its approval')

    @pytest.mark.proof("specs", "PROOF-5", "RULE-4", tier="integration")
    @pytest.mark.proof("specs", "PROOF-6", "RULE-5", tier="integration")
    def test_env_is_parsed_and_bounded_to_three_values(self, project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n- RULE-1: Files lock\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Lock a file; verify a second open fails '
            '@unit @env(windows)\n')
        info = purlin_specs.scan_specs(project.root)['login']
        assert info['proofs']['PROOF-1']['env'] == 'windows'
        assert info['proofs']['PROOF-1']['tier'] == 'unit'
        assert info['proof_env'] == {'PROOF-1': 'windows'}
        for value in ('windows', 'macos', 'linux'):
            assert purlin_specs.split_proof_tags('x @env(%s)' % value)[2] == value
        assert purlin_specs.split_proof_tags('x @env(bsd)')[2] is None
        assert purlin_specs.split_proof_tags('x @env(bsd)')[3] == ['@env(bsd)']
        # A proof line naming no tier at all is unit tier.
        assert purlin_specs.split_proof_tags(
            'Call login and verify 200')[1] == 'unit'

    @pytest.mark.proof("specs", "PROOF-7", "RULE-6")
    def test_a_second_env_tag_is_refused_not_merged(self):
        _clean, _tier, env, unknown = purlin_specs.split_proof_tags(
            'Lock it @env(macos) @env(windows)')
        assert env == 'windows', 'the trailing tag is the one that is read'
        assert unknown == ['@env(macos)'], unknown

    @pytest.mark.proof("specs", "PROOF-8", "RULE-7", tier="integration")
    @pytest.mark.proof("specs", "PROOF-9", "RULE-8", tier="integration")
    def test_unknown_tags_are_ignored_with_one_warning_naming_the_files(self,
                                                                       project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n- RULE-1: Files lock\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Lock a file; verify 1 open fails '
            '@unit @on(windows-2022)\n')
        project.spec(
            '# Feature: legacy\n\n> Visual-Reference: ./designs/a.png\n\n'
            '## Rules\n\n- RULE-1: It renders\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Look at it @manual(a@b.c, '
            '2026-03-31, abc1234)\n', name='legacy')
        features = purlin_specs.scan_specs(project.root)
        assert features['login']['proofs']['PROOF-1']['env'] is None
        assert features['login']['unknown_tags'] == ['@on(windows-2022)']
        assert features['legacy']['proofs']['PROOF-1']['tier'] == 'manual'
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
    def test_a_source_is_a_git_url_plus_a_path_or_local_globs(self):
        assert purlin_specs.parse_source(
            'https://github.com/acme/p.git specs/no_eval.md') == (
                'https://github.com/acme/p.git', 'specs/no_eval.md', [])
        assert purlin_specs.parse_source(
            'designs/checkout/*.png, designs/checkout/*.pdf') == (
                None, None, ['designs/checkout/*.png', 'designs/checkout/*.pdf'])
        # Neither shape: the whole line is the source, so a value that has to
        # be refused is refused whole.
        assert purlin_specs.parse_source('--upload-pack=/bin/echo')[0] == (
            '--upload-pack=/bin/echo')

    @pytest.mark.proof("specs", "PROOF-11", "RULE-10", tier="integration")
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

    @pytest.mark.proof("specs", "PROOF-12", "RULE-11", tier="integration")
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

    @pytest.mark.proof("specs", "PROOF-14", "RULE-13", tier="integration")
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

    @pytest.mark.proof("specs", "PROOF-13", "RULE-12", tier="integration")
    def test_the_scope_tree_changes_with_the_scoped_files(self, project):
        first = purlin_specs.scope_tree(project.root, ['src/login.py'])
        assert len(first) == 64
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 401\n')
        assert purlin_specs.scope_tree(project.root, ['src/login.py']) != first
        # A scope naming nothing still answers, so a spec with no scope is not
        # an error.
        assert len(purlin_specs.scope_tree(project.root, [])) == 64

    @pytest.mark.proof("specs", "PROOF-15", "RULE-14", tier="integration")
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
# Free checks
# ---------------------------------------------------------------------------

class TestChecks:

    def test_each_finding_has_a_case_that_raises_it(self):
        assert 'no_expected_value' in purlin_checks.proof_findings(
            'Call the parser and read the result')
        assert 'vague_verb' in purlin_checks.proof_findings(
            'Call login and verify it works correctly')
        assert 'missing_trigger' in purlin_checks.proof_findings(
            'The response body is "ok"')
        assert 'tier_mismatch' in purlin_checks.proof_findings(
            'Call login(user, pass) and verify 200', tier='e2e')
        assert 'implementation_coupling' in purlin_checks.proof_findings(
            'Call _resolve_token and verify 200')
        assert purlin_checks.rule_findings(
            ['POST /login with valid credentials; verify 200']) == [
                'happy_path_only']
        assert purlin_checks.rule_findings(
            ['POST /login with valid credentials; verify 200',
             'POST with a bad password; verify 401']) == []

    def test_a_clean_proof_raises_nothing(self):
        assert purlin_checks.proof_findings(
            'POST /login with a bad password; verify 401 and the body '
            '"denied"') == []

    def test_only_the_blocking_findings_hold_a_rule_out_of_proof_ready(self):
        assert purlin_checks.blocks_proof_ready(['no_expected_value'])
        assert not purlin_checks.blocks_proof_ready(['happy_path_only'])
        assert not purlin_checks.blocks_proof_ready(['implementation_coupling'])


# ---------------------------------------------------------------------------
# Runtime proof files
# ---------------------------------------------------------------------------

class TestProofFiles:

    @pytest.mark.proof("proofs", "PROOF-1", "RULE-1", tier="integration")
    @pytest.mark.proof("proofs", "PROOF-3", "RULE-3", tier="integration")
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

    @pytest.mark.proof("proofs", "PROOF-2", "RULE-2", tier="integration")
    @pytest.mark.proof("proofs", "PROOF-4", "RULE-4", tier="integration")
    @pytest.mark.proof("proofs", "PROOF-5", "RULE-5", tier="integration")
    def test_the_file_name_decides_the_tier_and_a_bad_file_is_skipped(
            self, project):
        parts = purlin_proofs.proof_file_parts
        assert parts('login.unit.json') == ('login', 'unit')
        assert parts('purlin.report.data.integration.json') == (
            'purlin.report.data', 'integration')
        assert parts('notes.txt') is None

        directory = os.path.join(project.root, '.purlin', 'runtime', 'proofs')
        entry = _entry('PROOF-1', 'RULE-1')
        entry.pop('tier')
        _write(os.path.join(directory, 'login.integration.json'),
               json.dumps({'proofs': [entry]}))
        loaded = purlin_proofs.load_proofs(project.root)
        assert [e['tier'] for e in loaded['login']] == ['integration'], loaded

        _write(os.path.join(directory, 'broken.unit.json'), 'not json at all')
        _write(os.path.join(directory, 'listed.unit.json'), '[]')
        _write(os.path.join(directory, 'stray.json'),
               json.dumps({'proofs': [_entry('PROOF-9', 'RULE-9')]}))
        after = purlin_proofs.load_proofs(project.root)
        assert sorted(after) == ['login'], sorted(after)
        assert len(after['login']) == 1, after['login']

    @pytest.mark.proof("proofs", "PROOF-6", "RULE-6", tier="integration")
    def test_a_fail_beats_a_pass_for_the_same_proof(self, project):
        project.proofs([_entry('PROOF-1', 'RULE-1'),
                        _entry('PROOF-1', 'RULE-1', status='fail',
                               test_file='tests/other.py')])
        entries = purlin_proofs.load_proofs(project.root)['login']
        assert purlin_proofs.status_by_proof(entries) == {
            ('login', 'PROOF-1'): 'fail'}

    @pytest.mark.proof("proofs", "PROOF-7", "RULE-7", tier="integration")
    def test_the_tests_backing_a_proof_are_named_once_each(self, project):
        project.proofs([_entry('PROOF-1', 'RULE-1'),
                        _entry('PROOF-1', 'RULE-1')])
        entries = purlin_proofs.load_proofs(project.root)['login']
        assert purlin_proofs.tests_for(entries, 'PROOF-1') == [
            ('tests/test_login.py', 'test_proof_1')]


# ---------------------------------------------------------------------------
# Ids
# ---------------------------------------------------------------------------

class TestIds:

    def test_the_next_id_is_one_past_the_highest_anywhere(self, project):
        assert purlin_ids.next_ids(project.root, 'specs/auth/login.md') == (3, 3)
        project.spec(SPEC + '- PROOF-7 (RULE-2): Another look; verify 401\n')
        assert purlin_ids.next_ids(project.root, 'specs/auth/login.md') == (3, 8)

    def test_a_gap_is_legal_and_never_reused(self, project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n'
            '- RULE-1: First\n- RULE-9: Ninth\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Verify 1\n')
        assert purlin_ids.next_ids(project.root, 'specs/auth/login.md')[0] == 10

    def test_allocation_reads_the_shared_ref_when_there_is_one(self, project):
        # With no origin, the ref is HEAD and the answer still comes.
        assert purlin_ids.allocation_ref(project.root) == 'HEAD'

    def test_a_duplicate_id_after_a_merge_is_reported(self, project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n'
            '- RULE-1: First\n- RULE-1: Both sides of the merge\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Verify 1\n'
            '- PROOF-1 (RULE-1): Verify 1 again\n')
        found = purlin_ids.duplicate_ids(project.root, 'specs/auth/login.md')
        assert found == {'rules': {'RULE-1': 2}, 'proofs': {'PROOF-1': 2}}

    def test_renumber_rewrites_the_spec_the_markers_and_the_approvals(self,
                                                                     project):
        _write(os.path.join(project.root, 'tests', 'test_login.py'),
               '@pytest.mark.proof("login", "PROOF-2", "RULE-2")\n'
               'def test_denied():\n    assert True\n')
        project.approval('RULE-2', {'rule': 'RULE-2', 'rule_hash': 'a' * 64,
                                    'proof_hash': 'b' * 64,
                                    'test_hash': 'c' * 64, 'risk': 'low'})
        changed = purlin_ids.renumber(
            project.root, 'specs/auth/login.md',
            {'RULE-2': 'RULE-14', 'PROOF-2': 'PROOF-14'},
            extra_paths=['tests/test_login.py'])
        with open(os.path.join(project.root, 'specs', 'auth', 'login.md'),
                  encoding='utf-8') as handle:
            spec_text = handle.read()
        assert 'RULE-14' in spec_text and 'RULE-2:' not in spec_text
        with open(os.path.join(project.root, 'tests', 'test_login.py'),
                  encoding='utf-8') as handle:
            assert '"PROOF-14", "RULE-14"' in handle.read()
        approvals_dir = os.path.join(project.root, 'specs', 'auth',
                                     'login.approvals')
        assert [n.split('.')[0] for n in os.listdir(approvals_dir)] == ['RULE-14']
        assert any(p.endswith('tests/test_login.py') for p in changed), changed

    def test_renumber_never_lets_one_id_eat_a_longer_one(self, project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n'
            '- RULE-1: First\n- RULE-12: Twelfth\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Verify 1\n')
        purlin_ids.renumber(project.root, 'specs/auth/login.md',
                            {'RULE-1': 'RULE-20'})
        with open(os.path.join(project.root, 'specs', 'auth', 'login.md'),
                  encoding='utf-8') as handle:
            text = handle.read()
        assert 'RULE-20: First' in text and 'RULE-12: Twelfth' in text, text


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
        for gate, review, strength, tags in (
                ('tested', 'never', 50, False),
                ('recorded', 'high', 70, False),
                ('approved', 'medium', 80, True)):
            cfg = purlin_gate.resolve_gate({'gate': gate})
            assert (cfg.gate, cfg.ai_review_at, cfg.min_strength,
                    cfg.tags_required) == (gate, review, strength, tags)

    def test_a_named_key_overrides_the_derived_default(self):
        cfg = purlin_gate.resolve_gate({'gate': 'recorded', 'min_strength': 95,
                                        'ai_review_at': 'low'})
        assert cfg.min_strength == 95 and cfg.ai_review_at == 'low'

    def test_an_unreadable_gate_falls_back_loudly(self):
        cfg = purlin_gate.resolve_gate({'gate': 'reccorded'})
        assert cfg.gate == 'tested'
        assert any('reccorded' in w for w in cfg.warnings), cfg.warnings

    def test_retired_keys_are_ignored_with_one_directive(self):
        cfg = purlin_gate.resolve_gate({
            'gate': 'tested', 'remote_verification': 'optional',
            'mutation_checks': True, 'quality_gate': 'deterministic',
            'platforms': {}, 'spec_dir': 'elsewhere'})
        retired = [w for w in cfg.warnings if 'purlin:init --update' in w]
        assert len(retired) == 1, cfg.warnings
        for key in ('remote_verification', 'mutation_checks', 'quality_gate',
                    'platforms', 'spec_dir'):
            assert key in retired[0], retired[0]

    def test_pre_push_survives_only_as_on_or_off(self):
        assert purlin_gate.resolve_gate({'pre_push': 'off'}).pre_push == 'off'
        cfg = purlin_gate.resolve_gate({'pre_push': 'strict'})
        assert cfg.pre_push == 'on'
        assert any('on or off' in w for w in cfg.warnings), cfg.warnings

    def test_risk_thresholds(self):
        assert purlin_gate.risk_at_or_above('high', 'medium')
        assert not purlin_gate.risk_at_or_above('low', 'medium')
        assert not purlin_gate.risk_at_or_above('high', 'never')
        assert purlin_gate.one_level_lower('high') == 'medium'
        assert purlin_gate.one_level_lower('low') == 'low'


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

    def test_a_record_a_person_committed_is_labelled_developer(self, project):
        path = project.record([_entry('PROOF-1', 'RULE-1')])
        assert purlin_records.record_label(project.root, path) == 'developer'

    def test_an_uncommitted_record_is_local(self, project):
        path = project.record([_entry('PROOF-1', 'RULE-1')], commit_it=False)
        loaded = purlin_records.load_records(project.root)
        assert loaded['login'][None]['label'] == 'local', path

    def test_what_counts_under_each_gate(self):
        assert purlin_records.counts_under('tested', 'developer')
        assert purlin_records.counts_under('tested', 'ci')
        assert not purlin_records.counts_under('tested', 'local')
        assert not purlin_records.counts_under('recorded', 'developer')
        assert purlin_records.counts_under('recorded', 'ci')
        assert not purlin_records.counts_under('approved', 'developer')
        assert purlin_records.counts_under('approved', 'ci')

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
# Approvals
# ---------------------------------------------------------------------------

def _approval_payload(project, rule_id='RULE-1', risk='high', **overrides):
    rule = project.rule(rule_id)
    data = {
        'feature': 'login', 'rule': rule_id, 'risk': risk,
        'approver': 'jane@acme.com', 'approved_at': '2026-09-13T12:00:00Z',
        'rule_hash': rule['rule_hash'], 'proof_hash': rule['proof_hash'],
        'test_hash': rule['test_hash'], 'design_hash': None,
        'brief_hash': 'd' * 64, 'record': None,
    }
    data['triple_hash'] = purlin_approvals.triple_hash(
        data['rule_hash'], data['proof_hash'], data['test_hash'])
    data.update(overrides)
    return data


class TestApprovals:

    def test_an_approval_is_one_file_named_for_its_rule_and_hash(self, project):
        data = _approval_payload(project)
        project.approval('RULE-1', data)
        loaded = purlin_approvals.load_approvals(
            project.root, purlin_specs.scan_specs(project.root))
        assert list(loaded) == [('login', 'RULE-1')]
        approval = loaded[('login', 'RULE-1')][0]
        assert approval['is_ci'] is False
        assert approval['path'].endswith('.jane.json')

    def test_a_ci_auto_approval_is_named_ci(self, project):
        data = _approval_payload(project, risk='low')
        project.approval('RULE-1', data, slug='ci')
        loaded = purlin_approvals.load_approvals(
            project.root, purlin_specs.scan_specs(project.root))
        assert loaded[('login', 'RULE-1')][0]['is_ci'] is True

    def test_current_means_the_triple_and_the_risk_still_match(self, project):
        data = _approval_payload(project)
        assert purlin_approvals.is_current(
            data, data['rule_hash'], data['proof_hash'], data['test_hash'],
            'high')
        # Any one of the three, or the risk, and it is not current.
        assert not purlin_approvals.is_current(
            data, 'x' * 64, data['proof_hash'], data['test_hash'], 'high')
        assert not purlin_approvals.is_current(
            data, data['rule_hash'], 'x' * 64, data['test_hash'], 'high')
        assert not purlin_approvals.is_current(
            data, data['rule_hash'], data['proof_hash'], 'x' * 64, 'high')
        assert not purlin_approvals.is_current(
            data, data['rule_hash'], data['proof_hash'], data['test_hash'],
            'medium')

    def test_an_unsigned_approval_does_not_count(self, project):
        data = _approval_payload(project)
        path = project.approval('RULE-1', data)
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'chore: approve')
        rel = os.path.relpath(path, project.root).replace(os.sep, '/')
        loaded = purlin_approvals.load_approvals(
            project.root, purlin_specs.scan_specs(project.root))
        approval = loaded[('login', 'RULE-1')][0]
        counted, reason = purlin_approvals.counts(
            project.root, approval, ['jane@acme.com'])
        assert counted is False and 'not signed' in reason, (reason, rel)

    def test_a_ci_approval_needs_no_signature_of_its_own(self, project):
        data = _approval_payload(project, risk='low')
        project.approval('RULE-1', data, slug='ci')
        loaded = purlin_approvals.load_approvals(
            project.root, purlin_specs.scan_specs(project.root))
        counted, reason = purlin_approvals.counts(
            project.root, loaded[('login', 'RULE-1')][0], ['jane@acme.com'])
        assert counted is True, reason


# ---------------------------------------------------------------------------
# The seven states
# ---------------------------------------------------------------------------

class TestStates:
    """Every one of the seven, and the three flags."""

    @pytest.mark.proof("states", "PROOF-1", "RULE-1", tier="integration")
    def test_drafted_when_there_is_no_proof(self, project):
        project.spec('# Feature: login\n\n## Rules\n\n- RULE-1: It works\n\n'
                     '## Proof\n')
        assert project.rule('RULE-1')['state'] == 'Drafted'

    @pytest.mark.proof("states", "PROOF-2", "RULE-2", tier="integration")
    def test_drafted_when_the_free_checks_fail(self, project):
        project.spec('# Feature: login\n\n## Rules\n\n- RULE-1: It works\n\n'
                     '## Proof\n\n- PROOF-1 (RULE-1): Call login and verify it '
                     'works correctly\n')
        rule = project.rule('RULE-1')
        assert rule['state'] == 'Drafted'
        assert 'vague_verb' in rule['proofs'][0]['findings']

    @pytest.mark.proof("states", "PROOF-2", "RULE-2", tier="integration")
    def test_proof_ready_when_the_free_checks_pass(self, project):
        assert project.rule('RULE-2')['state'] == 'Proof ready'

    @pytest.mark.proof("states", "PROOF-3", "RULE-3", tier="integration")
    def test_tested_when_the_tagged_test_passes_locally(self, project):
        project.proofs([_entry('PROOF-2', 'RULE-2')])
        assert project.rule('RULE-2')['state'] == 'Tested'
        # A failing entry is not Tested.
        project.proofs([_entry('PROOF-2', 'RULE-2', status='fail')])
        assert project.rule('RULE-2')['state'] == 'Proof ready'

    @pytest.mark.proof("states", "PROOF-4", "RULE-4", tier="integration")
    def test_recorded_when_a_counting_record_at_head_passes(self, project):
        project.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}])
        assert project.rule('RULE-2')['state'] == 'Recorded'

    @pytest.mark.proof("states", "PROOF-5", "RULE-5", tier="integration")
    def test_a_developer_record_does_not_count_under_recorded(self):
        made = Project(gate='recorded')
        try:
            made.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}])
            assert made.rule('RULE-2')['state'] != 'Recorded', (
                'under the recorded gate only a record CI wrote counts')
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-6", "RULE-6", tier="integration")
    def test_an_env_proof_needs_a_record_from_that_operating_system(self,
                                                                   project):
        project.spec(
            '# Feature: login\n\n## Rules\n\n- RULE-1: Files lock\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Lock a file; verify a second open '
            'returns 0 handles @env(windows)\n')
        project.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}],
                       os_name='linux')
        rule = project.rule('RULE-1')
        assert rule['state'] != 'Recorded'
        assert rule['missing_env'] == ['windows'], rule
        assert 'windows: no record yet' in rule['reasons'], rule
        project.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}],
                       os_name='windows')
        assert project.rule('RULE-1')['state'] == 'Recorded'

    @pytest.mark.proof("states", "PROOF-7", "RULE-7", tier="integration")
    def test_reviewed_when_a_brief_matches_the_triple(self, project):
        rule = project.rule('RULE-2')
        expected = purlin_approvals.triple_hash(
            rule['rule_hash'], rule['proof_hash'], rule['test_hash'])
        result = purlin_states.rule_state({
            'proofs': [{'id': 'PROOF-2', 'tier': 'unit', 'env': None,
                        'text': 'x', 'findings': []}],
            'brief': {'triple_hash': expected},
            'rule_hash': rule['rule_hash'], 'proof_hash': rule['proof_hash'],
            'test_hash': rule['test_hash'], 'risk': 'low',
        }, purlin_gate.resolve_gate({}))
        assert result['state'] == 'Reviewed'
        # A brief for other text is no brief at all.
        stale = purlin_states.rule_state({
            'proofs': [{'id': 'PROOF-2', 'tier': 'unit', 'env': None,
                        'text': 'x', 'findings': []}],
            'brief': {'triple_hash': 'f' * 64},
            'rule_hash': rule['rule_hash'], 'proof_hash': rule['proof_hash'],
            'test_hash': rule['test_hash'], 'risk': 'low',
        }, purlin_gate.resolve_gate({}))
        assert stale['state'] == 'Proof ready'

    @pytest.mark.proof("states", "PROOF-8", "RULE-8", tier="integration")
    def test_approved_when_a_current_approval_meets_a_passing_record(self,
                                                                    project):
        project.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}])
        project.approval('RULE-1', _approval_payload(project))
        assert project.rule('RULE-1')['state'] == 'Approved'

    @pytest.mark.proof("states", "PROOF-9", "RULE-9", tier="integration")
    def test_stale_when_the_rule_text_changed_after_the_approval(self, project):
        project.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}])
        project.approval('RULE-1', _approval_payload(project))
        assert project.rule('RULE-1')['state'] == 'Approved'
        project.spec(SPEC.replace('return 200 with a session token',
                                  'return 201 with a session token'))
        assert project.rule('RULE-1')['state'] == 'Stale'

    @pytest.mark.proof("states", "PROOF-10", "RULE-10", tier="integration")
    def test_re_verify_pending_when_only_the_code_changed(self, project):
        tree = purlin_specs.scope_tree(project.root, ['src/login.py'])
        project.record([{'id': 'PROOF-1', 'rule': 'RULE-1', 'status': 'pass'}],
                       scope_tree=tree)
        project.approval('RULE-1', _approval_payload(project))
        assert project.rule('RULE-1')['flags']['re_verify_pending'] is False
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 200  # rewritten\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'refactor: login')
        rule = project.rule('RULE-1')
        assert rule['state'] == 'Approved', (
            'the approval stands: only the code moved')
        assert rule['flags']['re_verify_pending'] is True, rule

    @pytest.mark.proof("states", "PROOF-11", "RULE-11", tier="integration")
    def test_auto_approvable_is_low_risk_with_a_strong_enough_record(self,
                                                                    project):
        project.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                       strength=90)
        assert project.rule('RULE-2')['flags']['auto_approvable'] is True
        # High risk is never auto-approvable.
        assert project.rule('RULE-1')['flags']['auto_approvable'] is False

    @pytest.mark.proof("states", "PROOF-27", "RULE-11", tier="integration")
    def test_with_no_engine_the_free_checks_stand_in_for_a_strength(self):
        # A record with no measured strength: the free checks decide instead.
        made = Project()
        try:
            made.record([{'id': 'PROOF-2', 'rule': 'RULE-2', 'status': 'pass'}],
                        strength=None)
            assert made.rule('RULE-2')['flags']['auto_approvable'] is True
            made.spec(SPEC.replace(
                'POST /login with a bad password; verify 401 and the '
                'body "denied"', 'Check that the login handles it properly'))
            blocked = made.rule('RULE-2')
            assert 'vague_verb' in blocked['proofs'][0]['findings'], blocked
            assert blocked['flags']['auto_approvable'] is False
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-12", "RULE-12")
    def test_needs_ai_review_at_or_above_the_threshold(self):
        cfg = purlin_gate.resolve_gate({'gate': 'recorded'})
        base = {'proofs': [{'id': 'PROOF-1', 'tier': 'unit', 'env': None,
                            'text': 'x', 'findings': []}]}
        high = dict(base, risk='high')
        low = dict(base, risk='low')
        assert purlin_states.rule_state(high, cfg)['flags']['needs_ai_review']
        assert not purlin_states.rule_state(low, cfg)['flags']['needs_ai_review']
        # With no engine the net widens by one level.
        medium = dict(base, risk='medium', mutation_engine_available=False)
        assert purlin_states.rule_state(medium, cfg)['flags']['needs_ai_review']
        # A strength under the minimum puts a rule on the list whatever its risk.
        weak = dict(base, risk='low', test_strength=10)
        assert purlin_states.rule_state(weak, cfg)['flags']['needs_ai_review']
        # So does an approval that no longer binds the current text.
        stale = dict(base, risk='low',
                     approvals=[{'risk': 'low', 'rule_hash': 'gone'}])
        assert purlin_states.rule_state(stale, cfg)['flags']['needs_ai_review']

    @pytest.mark.proof("states", "PROOF-14", "RULE-14", tier="integration")
    def test_the_rollups_count_states_and_name_the_lowest(self, project):
        project.proofs([_entry('PROOF-2', 'RULE-2')])
        data = project.payload()
        feature = next(f for f in data['features'] if f['name'] == 'login')
        rollup = feature['rollup']
        assert rollup['rules'] == 2
        assert rollup['counts'] == {'Proof ready': 1, 'Tested': 1}, rollup
        assert rollup['lowest_state'] == 'Proof ready'
        assert (rollup['stale'], rollup['re_verify_pending'],
                rollup['needs_review']) == (0, 0, 0), rollup
        assert data['project_rollup']['features'] == 1
        assert data['states'] == {'Proof ready': 1, 'Tested': 1}

    @pytest.mark.proof("states", "PROOF-13", "RULE-13")
    def test_the_state_order_puts_stale_first_and_approved_last(self):
        assert purlin_states.STATE_ORDER[0] == 'Stale'
        assert purlin_states.STATE_ORDER[-1] == 'Approved'
        assert len(purlin_states.STATE_ORDER) == 7
        assert purlin_states.lowest(['Approved', 'Tested']) == 'Tested'


# ---------------------------------------------------------------------------
# The payload
# ---------------------------------------------------------------------------

class TestPayload:

    @pytest.mark.proof("states", "PROOF-16", "RULE-16", tier="integration")
    def test_schema_four_carries_the_documented_top_level(self, project):
        data = project.payload()
        assert data['schema_version'] == 4
        for key in ('generated_at', 'generated_by', 'project', 'version',
                    'commit', 'dirty', 'gate', 'states', 'features',
                    'review_list', 'records', 'warnings'):
            assert key in data, key
        assert data['gate']['gate'] == 'tested'
        assert data['generated_at'].endswith('Z')

    @pytest.mark.proof("states", "PROOF-17", "RULE-17", tier="integration")
    def test_a_feature_carries_its_rules_with_their_tags_and_proofs(self,
                                                                   project):
        feature = next(f for f in project.payload()['features']
                       if f['name'] == 'login')
        assert feature['spec_path'] == 'specs/auth/login.md'
        assert feature['category'] == 'auth'
        rule = next(r for r in feature['rules'] if r['id'] == 'RULE-1')
        assert (rule['risk'], rule['origin'], rule['criterion']) == (
            'high', 'pm', 'US-12')
        assert rule['proofs'][0]['tier'] == 'integration'
        assert rule['proofs'][0]['env'] is None

    @pytest.mark.proof("states", "PROOF-18", "RULE-18", tier="integration")
    def test_the_review_list_names_the_rule_and_why(self):
        made = Project(gate='recorded')
        try:
            entries = made.payload()['review_list']
            assert [(e['rule'], e['risk']) for e in entries] == [
                ('RULE-1', 'high')], entries
            assert 'risk high' in entries[0]['reason']
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-28", "RULE-26", tier="integration")
    def test_a_review_entry_lists_its_reasons_and_joins_them(self):
        """Two rules on one list, each saying why it is there and no more."""
        made = Project(gate='recorded')
        try:
            made.record([{'id': 'PROOF-1', 'status': 'pass'},
                         {'id': 'PROOF-2', 'status': 'pass'}], strength=40)
            entries = {e['rule']: e for e in made.payload()['review_list']}
            assert entries['RULE-1']['reasons'] == [
                'risk high', 'strength 40% under 70%', 'happy_path_only']
            assert entries['RULE-1']['reason'] == (
                'risk high; strength 40% under 70%; happy_path_only')
            assert entries['RULE-2']['reasons'] == [
                'strength 40% under 70%']
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-29", "RULE-27", tier="integration")
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
        assert records['linux']['label'] == 'developer'
        assert records['windows']['label'] == 'developer'

    @pytest.mark.proof("states", "PROOF-19", "RULE-19", tier="integration")
    def test_the_data_file_is_a_const_assignment_and_round_trips(self, project):
        data = project.payload()
        path = purlin_payload.write_report_data(project.root, data)
        with open(path, encoding='utf-8') as handle:
            text = handle.read()
        assert text.startswith('const PURLIN_DATA = ') and text.endswith(';\n')
        assert purlin_payload.read_report_payload(project.root)['commit'] == (
            data['commit'])

    @pytest.mark.proof("states", "PROOF-20", "RULE-20", tier="integration")
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

    @pytest.mark.proof("states", "PROOF-15", "RULE-15", tier="integration")
    def test_global_anchor_rules_are_counted_once_in_the_project_rollup(self,
                                                                       project):
        project.spec(
            '# Anchor: security\n\n> Global: true\n\n'
            '## Rules\n\n- RULE-1: No eval anywhere\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
            name='security', category='_anchors')
        data = project.payload()
        assert data['project_rollup']['rules'] == 3, (
            'two own rules plus the anchor\'s one, counted once')
        login = next(f for f in data['features'] if f['name'] == 'login')
        assert login['rollup']['rules'] == 3, (
            'the feature must prove the global anchor\'s rule too')

    @pytest.mark.proof("states", "PROOF-30", "RULE-28", tier="integration")
    def test_the_review_list_names_a_global_anchor_rule_once(self):
        made = Project(gate='recorded')
        try:
            made.spec(
                '# Anchor: security\n\n> Global: true\n\n'
                '## Rules\n\n- RULE-1: No eval anywhere [risk: high]\n\n'
                '## Proof\n\n'
                '- PROOF-1 (RULE-1): Grep for eval(; verify 0 matches\n',
                name='security', category='_anchors')
            data = made.payload()
            entries = [(e['feature'], e['rule']) for e in data['review_list']]
            assert sorted(entries) == [('login', 'RULE-1'),
                                       ('security', 'RULE-1')], entries
            assert data['project_rollup']['needs_review'] == 2, (
                data['project_rollup'])
        finally:
            made.close()


# ---------------------------------------------------------------------------
# The status table
# ---------------------------------------------------------------------------

class TestStatusTable:

    @pytest.mark.proof("states", "PROOF-21", "RULE-21", tier="integration")
    def test_one_row_per_feature_with_the_seven_state_columns(self, project):
        project.proofs([_entry('PROOF-2', 'RULE-2')])
        text = purlin_status.sync_status(project.root)
        header = next(line for line in text.splitlines()
                      if line.startswith('Feature'))
        for column in ('Rules', 'Lowest state', 'States', 'Strength', 'Record',
                       'Approvals', 'Re-verify'):
            assert column in header, (column, header)
        row = next(line for line in text.splitlines()
                   if line.startswith('login '))
        assert 'Proof ready' in row and 'Tested 1' in row, row
        assert 'n/a' in row, 'no record, so no test strength'

    @pytest.mark.proof("states", "PROOF-23", "RULE-22", tier="integration")
    def test_the_table_ends_with_one_next_step(self, project):
        text = purlin_status.sync_status(project.root)
        directives = [line for line in text.splitlines()
                      if line.startswith('→ Next:')]
        assert len(directives) == 1, text
        assert 'purlin:build' in directives[0], directives[0]

    @pytest.mark.proof("states", "PROOF-26", "RULE-25", tier="integration")
    def test_retired_config_keys_print_the_update_directive(self):
        made = Project(extra_config={'remote_verification': 'optional'})
        try:
            text = purlin_status.sync_status(made.root)
            assert '→ Run: purlin:init --update' in text, text
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-24", "RULE-23", tier="integration")
    def test_an_empty_project_says_what_to_run(self):
        made = Project(spec=None)
        try:
            text = purlin_status.sync_status(made.root)
            assert 'No specs found' in text and 'purlin:init' in text
        finally:
            made.close()

    @pytest.mark.proof("states", "PROOF-25", "RULE-24", tier="integration")
    def test_no_emoji_and_only_the_three_glyphs(self, project):
        text = purlin_status.sync_status(project.root)
        allowed = set('→▶▼─')
        for char in text:
            assert ord(char) < 0x2000 or char in allowed, repr(char)

    @pytest.mark.proof("states", "PROOF-22", "RULE-21", tier="integration")
    def test_the_repository_own_specs_print_the_seven_state_table(self):
        text = purlin_status.sync_status(PROJECT_ROOT)
        assert 'Lowest state' in text
        assert any(state in text for state in purlin_states.STATE_ORDER), text
        assert text.rstrip().splitlines()[-1].startswith('→'), text


# ---------------------------------------------------------------------------
# Drift
# ---------------------------------------------------------------------------

class TestDriftRoles:

    @pytest.mark.proof("drift", "PROOF-16", "RULE-14", tier="integration")
    def test_the_four_role_views_are_present(self, project):
        _write(os.path.join(project.root, 'src', 'login.py'),
               'def login():\n    return 401\n')
        _git(project.root, 'add', '-A')
        _git(project.root, 'commit', '-q', '-m', 'fix: login')
        report = json.loads(purlin_drift.drift(project.root, since='1'))
        assert sorted(report['roles']) == ['design', 'eng', 'pm', 'qa']
        assert 'src/login.py' in report['roles']['eng']['files_touched']
        assert report['roles']['eng']['tests_missing'] == [
            'login/RULE-1', 'login/RULE-2']

    @pytest.mark.proof("drift", "PROOF-17", "RULE-15", tier="integration")
    def test_a_role_narrows_the_report(self, project):
        report = json.loads(purlin_drift.drift(project.root, since='1',
                                               role='qa'))
        assert report['role'] == 'qa'
        assert sorted(report['view']) == [
            'approvals_stale', 'review_list_size',
            'rules_without_a_negative_case']

    @pytest.mark.proof("drift", "PROOF-2", "RULE-1", tier="integration")
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

    @pytest.mark.proof("drift", "PROOF-14", "RULE-12", tier="integration")
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

    @pytest.mark.proof("server", "PROOF-1", "RULE-1", tier="integration")
    @pytest.mark.proof("server", "PROOF-5", "RULE-5", tier="integration")
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

    @pytest.mark.proof("server", "PROOF-2", "RULE-2", tier="integration")
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
        assert 'Lowest state' in text and 'login' in text

    @pytest.mark.proof("server", "PROOF-9", "RULE-9", tier="integration")
    def test_purlin_config_reads_and_writes(self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'read', 'key': 'gate'}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'write', 'key': 'gate',
                                      'value': 'recorded'}}},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
             'params': {'name': 'purlin_config',
                        'arguments': {'action': 'read', 'key': 'gate'}}})
        assert json.loads(responses[0]['result']['content'][0]['text']) == {
            'gate': 'tested'}
        assert json.loads(responses[2]['result']['content'][0]['text']) == {
            'gate': 'recorded'}
        # The write goes to the local overlay, never to the committed file.
        with open(os.path.join(project.root, '.purlin', 'config.json'),
                  encoding='utf-8') as handle:
            assert json.load(handle)['gate'] == 'tested'

    def test_drift_answers_json(self, project):
        responses, _stderr = _rpc(project.root, {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'drift', 'arguments': {'since': '1'}}})
        report = json.loads(responses[0]['result']['content'][0]['text'])
        assert 'commits' in report and 'files' in report

    @pytest.mark.proof("server", "PROOF-7", "RULE-7", tier="integration")
    def test_a_root_with_no_workspace_says_so_rather_than_reporting_nothing(
            self, tmp_path):
        responses, _stderr = _rpc(str(tmp_path), {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'sync_status', 'arguments': {}}})
        text = responses[0]['result']['content'][0]['text']
        assert 'No Purlin workspace' in text and 'purlin:init' in text

    @pytest.mark.proof("server", "PROOF-3", "RULE-3", tier="integration")
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

    @pytest.mark.proof("server", "PROOF-4", "RULE-4", tier="integration")
    def test_an_unknown_tool_and_an_unknown_method_are_errors(self, project):
        responses, _stderr = _rpc(
            project.root,
            {'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
             'params': {'name': 'nope', 'arguments': {}}},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'nope/at/all'})
        assert responses[0]['error']['code'] == -32601
        assert responses[1]['error']['code'] == -32601

    @pytest.mark.proof("server", "PROOF-6", "RULE-6", tier="integration")
    def test_project_root_can_be_named_per_call(self, project, tmp_path):
        responses, _stderr = _rpc(str(tmp_path), {
            'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
            'params': {'name': 'sync_status',
                       'arguments': {'project_root': project.root}}})
        assert 'login' in responses[0]['result']['content'][0]['text']

    @pytest.mark.proof("server", "PROOF-8", "RULE-8", tier="integration")
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
        assert 'Lowest state' in again, again

    @pytest.mark.proof("server", "PROOF-10", "RULE-10", tier="integration")
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

    @pytest.mark.proof("server", "PROOF-11", "RULE-11", tier="integration")
    def test_generate_digest_writes_the_data_file(self, project):
        path = purlin_srv.generate_digest(project.root,
                                             generated_by='hook',
                                             network=False)
        assert path and os.path.isfile(path)
        data = purlin_payload.read_report_payload(project.root)
        assert data['generated_by'] == 'hook'
        assert data['schema_version'] == 4

    @pytest.mark.proof("server", "PROOF-12", "RULE-12", tier="integration")
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
