"""Tests for what a spec parses to, the framework detection and the gate.

The throwaway project and its helpers are in `dev/mcp_project.py`.
"""

import contextlib
import json
import os
import shutil
import subprocess
import sys
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

def _one_proof(project, line, name='login'):
    """Read a spec whose one rule has the one proof `line`.

    Returns the proof as the scan reads it and the spec's unknown tags.
    """
    project.spec('# Feature: %s\n\n## Rules\n\n- RULE-1: Files lock\n\n'
                 '## Proof\n\n- PROOF-1 (RULE-1): %s\n' % (name, line),
                 name=name)
    info = purlin_specs.scan_specs(project.root)[name]
    return info['proofs']['PROOF-1'], info['unknown_tags']


def _anchor(project, *fields, **where):
    """Read the anchor `policy` carrying the metadata lines `fields`."""
    project.spec('# Anchor: policy\n\n%s\n\n'
                 '## Rules\n\n- RULE-1: No eval in source files\n\n'
                 '## Proof\n\n- PROOF-1 (RULE-1): Grep src/ for eval(; verify '
                 'zero matches\n' % '\n'.join(fields),
                 name='policy', category=where.get('category', '_anchors'))
    return purlin_specs.scan_specs(project.root)['policy']


# The other program that holds a file locked on Windows: it locks every byte
# of the file named by its one argument, says `locked`, and holds the lock
# until its input closes.
_HOLD_LOCKED = '''
import msvcrt, os, sys
size = os.path.getsize(sys.argv[1])
with open(sys.argv[1], 'r+b') as handle:
    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, size)
    print('locked', flush=True)
    sys.stdin.read()
    handle.seek(0)
    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, size)
'''


@contextlib.contextmanager
def _refused_to_readers(path):
    """Hold `path` so that any other read of it fails.

    On Windows another program locks the whole file for the duration;
    elsewhere its mode is set to 0. Either way the next reader gets an
    `OSError`.
    """
    if os.name == 'nt':
        holder = subprocess.Popen([sys.executable, '-c', _HOLD_LOCKED, path],
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        try:
            said = holder.stdout.readline().decode('ascii', 'replace')
            assert said.strip() == 'locked', (
                said + holder.stderr.read().decode('utf-8', 'replace'))
            with pytest.raises(OSError):
                with open(path, 'rb') as reader:
                    reader.read()
            yield
        finally:
            holder.stdin.close()
            holder.wait(timeout=30)
        return
    os.chmod(path, 0)
    try:
        yield
    finally:
        os.chmod(path, 0o644)


class TestRuleText:

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
    def test_extra_spaces_in_a_rule_keep_its_hash(self):
        plain = purlin_specs.rule_text_hash('Tokens expire after 24 hours')
        assert purlin_specs.rule_text_hash(
            'Tokens  expire   after 24 hours') == plain

    # purlin: specs PROOF-19
    def test_a_line_break_in_a_rule_keeps_its_hash(self):
        plain = purlin_specs.rule_text_hash('Tokens expire after 24 hours')
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


class TestOldTagsAndFields:

    # purlin: specs PROOF-8
    def test_a_bare_windows_tag_is_ignored_and_listed(self, project):
        proof, unknown = _one_proof(project,
                                    'Lock a file; verify 1 open fails @windows')
        assert proof['text'] == 'Lock a file; verify 1 open fails', proof
        assert proof['env'] is None, proof
        assert unknown == ['@windows'], unknown

    # purlin: specs PROOF-24
    def test_a_stamped_manual_still_reads_manual_and_is_listed(self, project):
        proof, unknown = _one_proof(
            project, 'Look at it @manual(a@b.c, 2026-03-31, abc1234)')
        assert proof['text'] == 'Look at it', proof
        assert proof['manual'] is True, proof
        assert unknown == ['@manual(...)'], unknown

    # purlin: specs PROOF-25
    def test_a_visual_reference_field_is_ignored_and_listed(self, project):
        project.spec(
            '# Feature: mockup\n\n> Visual-Reference: ./mock.png\n\n'
            '## Rules\n\n- RULE-1: It renders\n', name='mockup')
        mockup = purlin_specs.scan_specs(project.root)['mockup']
        assert mockup['rules'] == {'RULE-1': 'It renders'}, mockup['rules']
        assert mockup['unknown_tags'] == ['> Visual-Reference:'], mockup

    # purlin: specs PROOF-26
    def test_a_visual_hash_field_is_ignored_and_listed(self, project):
        project.spec(
            '# Feature: swatch\n\n> Visual-Hash: 9f86d081\n\n'
            '## Rules\n\n- RULE-1: It renders\n', name='swatch')
        swatch = purlin_specs.scan_specs(project.root)['swatch']
        assert swatch['rules'] == {'RULE-1': 'It renders'}, swatch['rules']
        assert swatch['unknown_tags'] == ['> Visual-Hash:'], swatch


def _tag_spec(project, name):
    project.spec('# Feature: %s\n\n## Rules\n\n- RULE-1: Files lock\n\n'
                 '## Proof\n\n- PROOF-1 (RULE-1): Lock a file @windows\n'
                 % name, name=name)


class TestTheWarning:

    # purlin: specs PROOF-9
    def test_one_warning_names_both_files(self, project):
        _one_proof(project, 'Lock a file @windows')
        _one_proof(project, 'Look at it @manual(a@b.c, 2026-03-31, abc1234)',
                   name='mockup')
        assert project.payload()['warnings'] == [
            '2 spec files carry tags this release does not read '
            '(@manual(...), @windows); they are ignored: '
            'specs/auth/login.md, specs/auth/mockup.md. '
            'Run purlin:init --update to remove them.']

    # purlin: specs PROOF-27
    def test_the_warning_names_five_files_and_counts_the_rest(self, project):
        for name in 'abcdefg':
            _tag_spec(project, name)
        assert project.payload()['warnings'] == [
            '7 spec files carry tags this release does not read (@windows); '
            'they are ignored: specs/auth/a.md, specs/auth/b.md, '
            'specs/auth/c.md, specs/auth/d.md, specs/auth/e.md, and 2 more. '
            'Run purlin:init --update to remove them.']

    # purlin: specs PROOF-28
    def test_no_carrier_means_no_warning(self, project):
        assert project.payload()['warnings'] == []


class TestSource:

    # purlin: specs PROOF-10
    def test_a_git_url_and_a_path_are_read_apart(self, project):
        info = _anchor(project,
                       '> Source: https://github.com/acme/p.git '
                       'specs/no_eval.md')
        assert (info['source'], info['source_path']) == (
            'https://github.com/acme/p.git', 'specs/no_eval.md')

    # purlin: specs PROOF-29
    def test_a_local_path_is_the_whole_source(self, project):
        info = _anchor(project, '> Source: ./policies')
        assert (info['source'], info['source_path']) == ('./policies', None)

    # purlin: specs PROOF-30
    def test_a_local_path_and_a_path_are_not_split(self, project):
        info = _anchor(project, '> Source: ./policies specs/no_eval.md')
        assert (info['source'], info['source_path']) == (
            './policies specs/no_eval.md', None)

    # purlin: specs PROOF-31
    def test_an_option_shaped_source_is_not_split(self, project):
        info = _anchor(project, '> Source: --upload-pack=touch x specs/a.md')
        assert (info['source'], info['source_path']) == (
            '--upload-pack=touch x specs/a.md', None)

    # purlin: specs PROOF-11
    def test_a_path_field_supplies_the_path_for_a_bare_url(self, project):
        info = _anchor(project, '> Source: https://github.com/acme/p.git',
                       '> Path: specs/no_eval.md')
        assert info['source'] == 'https://github.com/acme/p.git', info
        assert info['source_path'] == 'specs/no_eval.md', info

    # purlin: specs PROOF-32
    def test_the_source_lines_path_wins_over_a_path_field(self, project):
        info = _anchor(project,
                       '> Source: https://github.com/acme/p.git specs/a.md',
                       '> Path: specs/b.md')
        assert info['source_path'] == 'specs/a.md', info


class TestAnchors:

    # purlin: specs PROOF-12
    def test_an_anchor_carries_its_source_and_its_pin(self, project):
        info = _anchor(project,
                       '> Source: https://github.com/acme/p.git '
                       'specs/no_eval.md',
                       '> Pinned: abc1234def')
        assert info['spec_path'] == 'specs/_anchors/policy.md', info
        assert info['is_anchor'] is True
        assert info['source'] == 'https://github.com/acme/p.git'
        assert info['source_path'] == 'specs/no_eval.md'
        assert info['pinned'] == 'abc1234def'

    # purlin: specs PROOF-33
    # purlin: specs PROOF-42
    def test_the_anchors_folder_alone_makes_an_anchor(self, project):
        project.spec('# Feature: ruleset\n\n## Rules\n\n- RULE-1: A\n',
                     name='ruleset', category='_anchors')
        ruleset = purlin_specs.scan_specs(project.root)['ruleset']
        assert ruleset['is_anchor'] is True, ruleset

    # purlin: specs PROOF-34
    def test_the_anchor_heading_alone_makes_an_anchor(self, project):
        project.spec('# Anchor: shared\n\n## Rules\n\n- RULE-1: A\n',
                     name='shared', category='schema')
        shared = purlin_specs.scan_specs(project.root)['shared']
        assert shared['is_anchor'] is True, shared

    # purlin: specs PROOF-35
    def test_a_feature_outside_the_anchors_folder_is_no_anchor(self, project):
        login = purlin_specs.scan_specs(project.root)['login']
        assert login['spec_path'] == 'specs/auth/login.md'
        assert login['is_anchor'] is False, login


class TestTheScan:

    # purlin: specs PROOF-15
    def test_every_spec_is_keyed_by_its_filename_stem(self, project):
        project.spec(SPEC, name='sign_up')
        features = purlin_specs.scan_specs(project.root)
        assert sorted(features) == ['login', 'sign_up'], sorted(features)
        assert features['sign_up']['spec_path'] == 'specs/auth/sign_up.md'

    # purlin: specs PROOF-39
    def test_a_spec_that_cannot_be_decoded_is_skipped(self, project):
        undecodable = os.path.join(project.root, 'specs', 'auth', 'broken.md')
        with open(undecodable, 'wb') as handle:
            handle.write(b'# Feature: broken\n\xff\xfe not utf-8\n')
        features = purlin_specs.scan_specs(project.root)
        assert sorted(features) == ['login'], sorted(features)

    # purlin: specs PROOF-40
    def test_a_project_with_no_specs_folder_has_no_specs(self):
        empty = tempfile.mkdtemp()
        try:
            assert purlin_specs.scan_specs(empty) == {}
        finally:
            shutil.rmtree(empty, ignore_errors=True)

    # purlin: specs PROOF-41
    # purlin: specs PROOF-43
    @pytest.mark.skipif(os.name != 'nt' and (
        not hasattr(os, 'geteuid') or os.geteuid() == 0),
        reason='file modes do not refuse a read to this user')
    def test_a_spec_that_cannot_be_read_is_skipped(self, project):
        locked = os.path.join(project.root, 'specs', 'auth', 'locked.md')
        _write(locked, SPEC.replace('login', 'locked'))
        with _refused_to_readers(locked):
            features = purlin_specs.scan_specs(project.root)
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
