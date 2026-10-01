"""Tests for what a spec parses to, and the framework detection.

The throwaway project and its helpers are in `dev/mcp_project.py`.
"""

import json
import os

from mcp_project import _write, project
# `mcp_project` puts `scripts/mcp` on the path.
from purlin import frameworks as purlin_frameworks
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


class TestRuleText:

    # purlin: specs PROOF-19
    def test_a_line_break_in_a_rule_keeps_its_hash(self):
        plain = purlin_specs.rule_text_hash('Tokens expire after 24 hours')
        assert purlin_specs.rule_text_hash(
            'Tokens expire\n  after 24 hours') == plain

    # purlin: specs PROOF-17
    def test_a_changed_word_changes_a_rules_hash(self):
        assert purlin_specs.rule_text_hash('Tokens expire after 12 hours') != (
            purlin_specs.rule_text_hash('Tokens expire after 24 hours'))


class TestOldTagsAndFields:

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

class TestSource:

    # purlin: specs PROOF-10
    def test_a_git_url_and_a_path_are_read_apart(self, project):
        info = _anchor(project,
                       '> Source: https://github.com/acme/p.git '
                       'specs/no_eval.md')
        assert (info['source'], info['source_path']) == (
            'https://github.com/acme/p.git', 'specs/no_eval.md')

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

class TestTheScan:

    # purlin: specs PROOF-39
    def test_a_spec_that_cannot_be_decoded_is_skipped(self, project):
        undecodable = os.path.join(project.root, 'specs', 'auth', 'broken.md')
        with open(undecodable, 'wb') as handle:
            handle.write(b'# Feature: broken\n\xff\xfe not utf-8\n')
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
