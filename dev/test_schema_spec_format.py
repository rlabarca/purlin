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
import purlin_server


class TestSpecFormatReference:

    @pytest.mark.proof("schema_spec_format", "PROOF-1", "RULE-1")
    def test_format_documents_two_sections(self):
        with open(os.path.join(PROJECT_ROOT, 'references', 'formats', 'spec_format.md')) as f:
            content = f.read()
        # Find the Required Sections area specifically
        req_match = re.search(
            r'## Required Sections\s*\n(.*?)(?=^## |\Z)', content,
            re.MULTILINE | re.DOTALL
        )
        assert req_match, "No '## Required Sections' heading in spec_format.md"
        req_section = req_match.group(1)
        assert '## Rules' in req_section, \
            "'## Rules' not listed in Required Sections"
        assert '## Proof' in req_section, \
            "'## Proof' not listed in Required Sections"


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

    @pytest.mark.proof("schema_spec_format", "PROOF-2", "RULE-2")
    def test_unnumbered_rule_triggers_warning(self):
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n'
            '- some constraint without RULE-N prefix\n'
            '- RULE-1: A proper rule\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'WARNING' in result
        assert 'not numbered' in result, \
            f"WARNING doesn't mention unnumbered rules: {result}"

    @pytest.mark.proof("schema_spec_format", "PROOF-4", "RULE-4")
    def test_rule_without_proof_shows_uncovered(self):
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n- RULE-1: Must work\n\n'
            '## Proof\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'RULE-1: NO PROOF' in result

    @pytest.mark.proof("schema_spec_format", "PROOF-5", "RULE-5")
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
        result = purlin_server.sync_status(self.project_root)
        assert 'base/RULE-1' in result, \
            f"Required spec's rules not included in coverage: {result}"

    @pytest.mark.proof("schema_spec_format", "PROOF-6", "RULE-6")
    def test_scope_metadata_parsed(self):
        # Create a feature with Scope and an anchor with overlapping scope
        # so sync_status exercises the scope in its overlap suggestion
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '> Scope: scripts/mcp/purlin_server.py, src/app.py\n\n'
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
        features = purlin_server._scan_specs(self.project_root)
        assert 'test_feat' in features
        scope = features['test_feat']['scope']
        assert scope == ['scripts/mcp/purlin_server.py', 'src/app.py'], \
            f"Scope should be parsed as comma-separated list, got: {scope}"
        # Verify sync_status uses the parsed scope in its output (overlap suggestion)
        result = purlin_server.sync_status(self.project_root)
        assert 'test_feat' in result, "Feature should appear in sync_status output"
        assert 'api_conv' in result and 'scope' in result.lower(), \
            f"sync_status should use scope for overlap suggestion. Got: {result}"


class TestSpecFormatConventions:

    @pytest.mark.proof("schema_spec_format", "PROOF-3", "RULE-3")
    def test_all_proof_lines_match_pattern(self):
        spec_files = glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**', '*.md'),
                               recursive=True)
        pattern = re.compile(r'^-\s+PROOF-\d+\s+\(RULE-\d+\)')
        for path in spec_files:
            with open(path) as f:
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

    @pytest.mark.proof("schema_spec_format", "PROOF-7", "RULE-7")
    def test_spec_headings_use_correct_prefix(self):
        spec_files = glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**', '*.md'),
                               recursive=True)
        valid = re.compile(r'^# (Feature|Anchor): ')
        for path in spec_files:
            with open(path) as f:
                content = f.read()
            headings = re.findall(r'^# .+', content, re.MULTILINE)
            for h in headings:
                assert valid.match(h), \
                    f"Invalid heading in {path}: {h}"
