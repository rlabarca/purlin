"""Tests for what a spec parses to, the framework detection and the gate.

The throwaway project and its helpers are in `dev/mcp_project.py`.
"""

import json
import os
import shutil
import tempfile

import pytest

from mcp_project import SPEC, _write, project
# `mcp_project` puts `scripts/mcp` on the path.
from purlin import frameworks as purlin_frameworks
from purlin import gate as purlin_gate
from purlin import specs as purlin_specs


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class TestSpecParsing:

    # purlin: specs PROOF-1
    def test_a_bracket_at_the_end_of_a_rule_is_part_of_its_text(self, project):
        project.spec('# Feature: login\n\n## Rules\n\n'
                     '- RULE-1: Tokens expire [owner: qa]\n')
        info = purlin_specs.scan_specs(project.root)['login']
        assert info['rules']['RULE-1'] == 'Tokens expire [owner: qa]', (
            info['rules'])

    # purlin: specs PROOF-2
    def test_a_bracket_at_the_end_of_a_rule_enters_its_hash(self):
        assert purlin_specs.rule_text_hash('Tokens expire [owner: qa]') != (
            purlin_specs.rule_text_hash('Tokens expire'))

    # purlin: specs PROOF-3
    def test_reflowing_a_proof_keeps_its_hash(self):
        proof = purlin_specs.proof_text_hash('Wait 24 hours; verify 401')
        assert purlin_specs.proof_text_hash(
            'Wait  24\n hours;   verify 401') == proof

    # purlin: specs PROOF-4
    def test_reflowing_a_rule_keeps_its_hash(self):
        plain = purlin_specs.rule_text_hash('Tokens expire after 24 hours')
        assert purlin_specs.rule_text_hash(
            'Tokens  expire   after 24 hours') == plain
        assert purlin_specs.rule_text_hash(
            'Tokens expire\n  after 24 hours') == plain

    # purlin: specs PROOF-17
    def test_a_changed_word_changes_a_rules_hash(self):
        assert purlin_specs.rule_text_hash('Tokens expire after 12 hours') != (
            purlin_specs.rule_text_hash('Tokens expire after 24 hours'))

    # purlin: specs PROOF-18
    def test_a_changed_word_changes_a_proofs_hash(self):
        assert purlin_specs.proof_text_hash('Wait 12 hours; verify 401') != (
            purlin_specs.proof_text_hash('Wait 24 hours; verify 401'))

    # purlin: specs PROOF-5
    # purlin: specs PROOF-6
    def test_env_is_parsed_and_bounded_to_three_values(self, project):
        # Reading stops at a word that is not a tag, so a tag before it is
        # not read either.
        assert purlin_specs.split_proof_tags('x @manual @smoke') == (
            'x @manual @smoke', False, None, [])
        project.spec(
            '# Feature: bsd_lock\n\n## Rules\n\n- RULE-1: Files lock\n\n'
            '## Proof\n\n'
            '- PROOF-1 (RULE-1): Lock a file; verify a second open fails '
            '@env(bsd)\n', name='bsd_lock')
        bsd = purlin_specs.scan_specs(project.root)['bsd_lock']
        assert bsd['proofs']['PROOF-1']['env'] is None, bsd['proofs']
        assert bsd['unknown_tags'] == ['@env(bsd)'], bsd['unknown_tags']
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
        # The other retired field, `> Visual-Hash:`, is ignored the same way.
        project.spec(
            '# Feature: swatch\n\n> Visual-Hash: 9f86d081\n\n'
            '## Rules\n\n- RULE-1: It renders\n\n'
            '## Proof\n\n- PROOF-1 (RULE-1): Open it; verify 1 swatch\n',
            name='swatch')
        swatch = purlin_specs.scan_specs(project.root)['swatch']
        assert swatch['rules'] == {'RULE-1': 'It renders'}, swatch['rules']
        assert swatch['unknown_tags'] == ['> Visual-Hash:'], swatch

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
        # A value with a space whose first word is not a git URL is not split.
        assert purlin_specs.parse_source('./policies specs/no_eval.md') == (
            './policies specs/no_eval.md', None)
        assert purlin_specs.parse_source('--upload-pack=touch x specs/a.md') == (
            '--upload-pack=touch x specs/a.md', None)

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
        # Either condition alone makes an anchor; neither makes a feature.
        project.spec('# Feature: ruleset\n\n## Rules\n\n- RULE-1: A\n',
                     name='ruleset', category='_anchors')
        project.spec('# Anchor: shared\n\n## Rules\n\n- RULE-1: A\n',
                     name='shared', category='schema')
        features = purlin_specs.scan_specs(project.root)
        assert features['ruleset']['is_anchor'] is True
        assert features['shared']['is_anchor'] is True
        assert features['login']['is_anchor'] is False

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
        # Two levels down: `api` now requires `base`, so `login` owes `base`
        # too, while `api`, an anchor, still owes only its own rule.
        project.spec(
            '# Feature: base\n\n## Rules\n\n- RULE-1: Requests carry an id\n',
            name='base', category='core')
        project.spec(
            '# Anchor: api\n\n> Requires: base\n\n'
            '## Rules\n\n- RULE-1: Responses carry a type\n',
            name='api', category='schema')
        features = purlin_specs.scan_specs(project.root)
        assert purlin_specs.rule_refs('login', features) == [
            ('login', 'RULE-1', 'own'), ('login', 'RULE-2', 'own'),
            ('api', 'RULE-1', 'required'), ('base', 'RULE-1', 'required'),
            ('security', 'RULE-1', 'global')]
        assert purlin_specs.rule_refs('api', features) == [
            ('api', 'RULE-1', 'own')]

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

    # purlin: specs PROOF-15
    @pytest.mark.skipif(not hasattr(os, 'geteuid') or os.geteuid() == 0,
                        reason='file modes do not refuse a read here')
    def test_a_spec_that_cannot_be_read_is_skipped(self, project):
        locked = os.path.join(project.root, 'specs', 'auth', 'locked.md')
        _write(locked, SPEC.replace('login', 'locked'))
        os.chmod(locked, 0)
        try:
            features = purlin_specs.scan_specs(project.root)
        finally:
            os.chmod(locked, 0o644)
        assert sorted(features) == ['login'], sorted(features)


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
            'audit_parallel', 'ci', 'gate', 'min_strength', 'mutation_engine']

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

    def test_the_hook_setting_is_a_key_this_release_does_not_read(self):
        cfg = purlin_gate.resolve_gate({'pre_push': 'on'})
        assert any('purlin:init --update' in w for w in cfg.warnings), \
            cfg.warnings
