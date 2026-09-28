"""Tests for schema_spec_format — 7 rules.

Validates the spec format contract: required sections, rule numbering,
proof references, metadata fields, and heading conventions.
"""

import glob
import json
import os
import re
import shutil
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
from purlin import payload as purlin_payload
from purlin import specs as purlin_specs
from purlin import status as purlin_status


class TestSpecFormatReference:

    # purlin: schema_spec_format PROOF-1
    def test_format_documents_two_sections(self):
        formats = os.path.join(PROJECT_ROOT, 'references', 'formats')
        with open(os.path.join(formats, 'spec_format.md')) as f:
            content = f.read()
        # Find the Required Sections area specifically
        req_match = re.search(
            r'## Required [Ss]ections\s*\n(.*?)(?=^## |\Z)', content,
            re.MULTILINE | re.DOTALL
        )
        assert req_match, "No '## Required sections' heading in spec_format.md"
        req_section = req_match.group(1)
        assert '## Rules' in req_section, \
            "'## Rules' not listed in Required Sections"
        assert '## Proof' in req_section, \
            "'## Proof' not listed in Required Sections"

        # No third section is part of the format: neither format file names the
        # retired `## What it does` heading.
        for name in ('spec_format.md', 'anchor_format.md'):
            with open(os.path.join(formats, name)) as f:
                text = f.read()
            assert 'What it does' not in text, (
                f"{name} still names the retired `## What it does` heading; "
                "the format defines two sections and no third")

        # A spec written against the older three-section format still parses:
        # the heading is ignored, not rejected, so a consumer's existing specs
        # keep working after the format drops it.
        project_root = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(project_root, '.purlin'))
            spec_dir = os.path.join(project_root, 'specs', 'test')
            os.makedirs(spec_dir)
            with open(os.path.join(spec_dir, 'legacy_feat.md'), 'w') as f:
                f.write(
                    '# Feature: legacy_feat\n\n'
                    '> Description: A spec authored against the 3-section format\n\n'
                    '## What it does\n\nIt does the legacy thing.\n\n'
                    '## Rules\n- RULE-1: The legacy rule still counts\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test the legacy rule\n'
                )
            result = purlin_status.sync_status(project_root)
            assert 'legacy_feat' in result, (
                "a spec carrying `## What it does` was not parsed at all:\n"
                f"{result}")
            data = purlin_payload.build_payload(project_root)
            feature = next(f for f in data['features']
                           if f['name'] == 'legacy_feat')
            assert [r['id'] for r in feature['rules']] == ['RULE-1'], (
                "the rule of a spec carrying `## What it does` is missing:"
                f"\n{feature['rules']}")
            assert 'WARNING' not in result, (
                "an ignored heading must not be reported as a defect: a "
                f"consumer's older specs keep working:\n{result}")
        finally:
            shutil.rmtree(project_root)


class TestSpecFormatEnforcement:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'test')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, name, content):
        with open(os.path.join(self.spec_dir, f'{name}.md'), 'w') as f:
            f.write(content)

    # purlin: schema_spec_format PROOF-2
    def test_unnumbered_rule_triggers_warning(self):
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n'
            '- some constraint without RULE-N prefix\n'
            '- RULE-1: A proper rule\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        result = purlin_status.sync_status(self.project_root)
        assert 'WARNING' in result
        assert 'not numbered' in result, \
            f"WARNING doesn't mention unnumbered rules: {result}"

        # A retired rule leaves its number vacant, so a gapped spec is legal:
        # RULE-2 and RULE-4..19 are absent and nothing is reported.
        self._write_spec('gapped_feat', (
            '# Feature: gapped_feat\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n'
            '- RULE-1: The first rule\n'
            '- RULE-3: The rule that outlived RULE-2\n'
            '- RULE-20: The rule numbered after sixteen retirements\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): Test one\n'
            '- PROOF-3 (RULE-3): Test three\n'
            '- PROOF-20 (RULE-20): Test twenty\n'
        ))
        os.remove(os.path.join(self.spec_dir, 'test_feat.md'))
        gapped = purlin_status.sync_status(self.project_root)
        assert 'WARNING' not in gapped, (
            "a gap in the rule numbers is legal: a retired rule leaves its "
            f"number vacant and the rest are never renumbered:\n{gapped}")
        data = purlin_payload.build_payload(self.project_root)
        feature = next(f for f in data['features'] if f['name'] == 'gapped_feat')
        assert [r['id'] for r in feature['rules']] == ['RULE-1', 'RULE-3',
                                                       'RULE-20'], (
            "the gapped spec was not parsed as written: "
            f"{[r['id'] for r in feature['rules']]}")

    # purlin: schema_spec_format PROOF-4
    def test_a_rule_with_no_proof_line_reads_no_proof_written(self):
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n- RULE-1: Must work\n\n'
            '## Proof\n'
        ))
        data = purlin_payload.build_payload(self.project_root)
        feature = next(f for f in data['features'] if f['name'] == 'test_feat')
        rule = next(r for r in feature['rules'] if r['id'] == 'RULE-1')
        assert rule['proofs'] == [], f"RULE-1 has no proof line: {rule}"
        cell = rule['cells']['passed']
        assert (cell['word'], cell['reasons']) == (
            'no test', ['no proof written']), cell

    # purlin: schema_spec_format PROOF-5
    def test_requires_includes_referenced_rules(self):
        # Create an anchor spec
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir)
        with open(os.path.join(anchor_dir, 'base.md'), 'w') as f:
            f.write(
                '# Anchor: base\n\n'
                '## What it does\nBase rules.\n\n'
                '## Rules\n- RULE-1: Base rule\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Test\n'
            )
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '> Requires: base\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n- RULE-1: Own rule\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        data = purlin_payload.build_payload(self.project_root)
        feature = next(f for f in data['features'] if f['name'] == 'test_feat')
        required = [r for r in feature['rules'] if r['label'] == 'required']
        assert [(r['feature'], r['id']) for r in required] == [('base', 'RULE-1')], (
            f"the required spec's rules are not counted with the feature's own: "
            f"{[(r['feature'], r['id'], r['label']) for r in feature['rules']]}")

    # purlin: schema_spec_format PROOF-6
    def test_scope_metadata_parsed(self):
        # Create a feature with Scope and an anchor with overlapping scope
        # so sync_status exercises the scope in its overlap suggestion
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '> Scope: scripts/mcp/purlin/specs.py, src/app.py\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n- RULE-1: Must work\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        self._write_spec('api_conv', (
            '# Anchor: api_conv\n\n'
            '> Scope: scripts/\n\n'
            '## What it does\nConventions.\n\n'
            '## Rules\n- RULE-1: Conv\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Check\n'
        ), )
        # Verify the scope was correctly parsed as a comma-separated list
        features = purlin_specs.scan_specs(self.project_root)
        assert 'test_feat' in features
        scope = features['test_feat']['scope']
        assert scope == ['scripts/mcp/purlin/specs.py', 'src/app.py'], \
            f"Scope should be parsed as comma-separated list, got: {scope}"
        result = purlin_status.sync_status(self.project_root)
        assert 'test_feat' in result, "Feature should appear in sync_status output"
        assert 'api_conv' in result, "The anchor should appear too"


class TestSpecFormatMultilineDescription:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'test')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, name, content):
        path = os.path.join(self.spec_dir, f'{name}.md')
        with open(path, 'w') as f:
            f.write(content)
        return path

    # purlin: schema_spec_format PROOF-8
    def test_multiline_description_continuation(self):
        """PROOF-8: Description continuation lines joined; Scope not included."""
        spec_path = self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '> Description: First line\n'
            '>   second line\n'
            '> Scope: src/\n\n'
            '## Rules\n'
            '- RULE-1: Must work\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): Test\n'
        ))
        features = purlin_specs.scan_specs(self.project_root)
        assert 'test_feat' in features, \
            "test_feat not found in scanned specs"
        desc = features['test_feat'].get('description', '')
        # Description must contain both continuation lines
        assert 'First line' in desc, \
            f"Description missing 'First line': {desc!r}"
        assert 'second line' in desc, \
            f"Description missing 'second line': {desc!r}"
        # Description must NOT contain the Scope field value
        assert 'src/' not in desc, \
            f"Description must not include Scope field value 'src/': {desc!r}"
        # Scope must be parsed independently as its own field
        scope = features['test_feat'].get('scope', [])
        assert scope == ['src/'], \
            f"Scope should be parsed as ['src/'], got: {scope!r}"


class TestSpecFormatConventions:

    # purlin: schema_spec_format PROOF-3
    def test_all_proof_lines_match_pattern(self):
        spec_files = glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**', '*.md'),
                               recursive=True)
        pattern = re.compile(r'^-\s+PROOF-\d+\s+\(RULE-\d+\)')
        for path in spec_files:
            with open(path, encoding='utf-8') as f:
                content = f.read()
            proof_section = re.search(
                r'^## Proof\s*\n(.*?)(?=^## |\Z)', content,
                re.MULTILINE | re.DOTALL
            )
            if not proof_section:
                continue
            for line in proof_section.group(1).strip().splitlines():
                line = line.strip()
                if line.startswith('- '):
                    assert pattern.match(line), \
                        f"Bad proof line in {path}: {line}"

    # purlin: schema_spec_format PROOF-7
    def test_spec_headings_use_correct_prefix(self):
        spec_files = glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**', '*.md'),
                               recursive=True)
        valid = re.compile(r'^# (Feature|Anchor): ')
        for path in spec_files:
            with open(path, encoding='utf-8') as f:
                content = f.read()
            headings = re.findall(r'^# .+', content, re.MULTILINE)
            for h in headings:
                assert valid.match(h), \
                    f"Invalid heading in {path}: {h}"


class TestTagParsing:
    """RULE-9 / RULE-10: the tag grammar.

    A trailing @word is only a tag when it is `@manual` or `@env(...)`, and
    only when it is metadata. A description that ends "...documents @manual,
    @env, and @windows" is prose, and reading its last word as a tag would
    truncate it at the final clause. A tag may not follow a list connector,
    which is what separates the two.
    """

    # purlin: schema_spec_format PROOF-9
    def test_prose_ending_in_an_at_word_is_not_a_tag(self):
        split = purlin_specs.split_proof_tags
        tagged = [
            ('Check it by hand @manual', 'Check it by hand', True, None),
            ('Lock the file @manual @env(windows)', 'Lock the file', True,
             'windows'),
            ('Lock the file @env(macos) @manual', 'Lock the file', True,
             'macos'),
            ('Lock the file @env(linux)', 'Lock the file', False, 'linux'),
        ]
        for desc, text, manual, env in tagged:
            clean, got_manual, got_env, unknown = split(desc)
            assert (clean, got_manual, got_env) == (text, manual, env), desc
            assert not unknown, f"{desc!r}: unexpected unknown tags {unknown!r}"
        # A word that is not a tag, and prose that merely ends in an @word,
        # come back whole.
        untagged = [
            'Grep the file; verify present @smoke',
            'verify `spec_format.md` documents @manual, @env, and @windows',
            'Check the documented tags @manual, @env',
            'Accepts either @env or @manual',
        ]
        for desc in untagged:
            assert split(desc) == (desc, False, None, []), desc

        # Either order is one grammar: the tuple must not depend on tag order.
        assert (split('Lock the file @manual @env(windows)')
                == split('Lock the file @env(windows) @manual'))

    # purlin: schema_spec_format PROOF-10
    def test_env_takes_three_values_and_nothing_else(self):
        split = purlin_specs.split_proof_tags
        for good in ('windows', 'macos', 'linux'):
            clean, manual, env, unknown = split('Lock the file @env(%s)' % good)
            assert (clean, manual, env, unknown) == ('Lock the file', False,
                                                     good, [])
        # windows-2022 is a runner name, not one of the three values, so it is
        # ignored and named rather than read as a fourth operating system.
        for bad in ('windows-2022', 'ubuntu-24.04', 'Windows'):
            clean, manual, env, unknown = split('Lock the file @env(%s)' % bad)
            assert env is None, f"{bad!r} must not be read as an environment"
            assert unknown == ['@env(%s)' % bad], unknown
            assert (clean, manual) == ('Lock the file', False)
        # A retired tag is ignored and named, never read.
        clean, manual, env, unknown = split('Lock the file @on(windows-2022)')  # retired
        assert (clean, manual, env) == ('Lock the file', False, None)
        assert unknown == ['@on(windows-2022)'], unknown  # retired

    # purlin: schema_spec_format PROOF-9
    def test_real_spec_is_parsed_correctly(self):
        """The two shapes, read off this repository's own specs.

        PROOF-9 of this anchor quotes several tags in backticks and carries
        no tag of its own; scaffold's PROOF-36 carries one real trailing
        `@env` tag. A parser that read a quoted tag would give the first an
        environment or a manual mark it never declared and truncate its
        description at the last quote."""
        features = purlin_specs.scan_specs(PROJECT_ROOT)

        quoted = features['schema_spec_format']['proofs']['PROOF-9']
        assert '`Lock the file @env(macos) @manual`' in quoted['text'], \
            "PROOF-9 no longer quotes a tag, so this pins nothing"
        assert quoted['manual'] is False, \
            "a quoted tag mid-description does not make the proof manual"
        assert quoted['env'] is None, \
            "a quoted environment tag mid-description is not an environment"
        assert quoted['text'].rstrip().endswith('identical tuples'), \
            "the description's final clause must not be truncated"

        tagged = features['scaffold']['proofs']['PROOF-36']
        assert tagged['env'] == 'linux', \
            "scaffold PROOF-36's one trailing tag is its environment"
        assert tagged['manual'] is False, tagged['manual']
        assert tagged['text'].rstrip().endswith(
            'the typescript one, each with a note'), \
            "the tag is stripped off the description, nothing else is"


class TestAnchorNoteMetadata:
    """RULE-11: `> Note:` is free text the parser ignores.

    The anchor-metadata tests for `> Source:`/`> Pinned:` live in
    dev/test_mcp_server.py; this proof lives here because `> Note:` is a spec
    metadata field, which is what schema_spec_format owns.
    """

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    # purlin: schema_spec_format PROOF-11
    def test_note_field_is_ignored_by_the_parser(self):
        path = os.path.join(self.spec_dir, 'policy.md')
        with open(path, 'w') as f:
            f.write(
                '# Anchor: policy\n\n'
                '> Description: Local policy\n'
                '> Note: run bash dev/setup-external-refs.sh before the first sync\n'
                '> Note: the second Note line is ignored too\n'
                '> Source: ./dev/external-refs/policy.git\n'
                '> Pinned: d1e2816\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep src/ for eval(; verify zero matches\n'
            )
        features = purlin_specs.scan_specs(self.project_root)
        assert 'policy' in features, f"the anchor did not parse at all: {list(features)}"
        info = features['policy']
        assert info.get('description') == 'Local policy', (
            f"the Note text leaked into the description: {info.get('description')!r}")
        assert info.get('source') == './dev/external-refs/policy.git', (
            f"the Note text displaced the Source: {info.get('source')!r}")
        leaked = [k for k, v in info.items()
                  if isinstance(v, str) and 'setup-external-refs' in v]
        assert not leaked, f"the Note text reached parsed fields {leaked}: {info}"
        assert info.get('rules', {}).get('RULE-1'), (
            f"the rules still parse alongside a Note: {info.get('rules')}")
