"""Tests for purlin_references — 11 rules.

Grep-based structural verification of the 8 reference documents
that define Purlin's formats, conventions, and quality standards.
"""

import os
import re

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
REFS = os.path.join(PROJECT_ROOT, 'references')
FORMATS = os.path.join(REFS, 'formats')


def _read(path):
    with open(path) as f:
        return f.read()


class TestPurlinReferences:

    @pytest.mark.proof("purlin_references", "PROOF-1", "RULE-1")
    def test_spec_format_required_sections(self):
        content = _read(os.path.join(FORMATS, 'spec_format.md'))
        # Scope to the Required Sections block
        m = re.search(r'## Required Sections(.*?)(?=^## |\Z)', content,
                       re.MULTILINE | re.DOTALL)
        assert m, "Missing '## Required Sections' heading in spec_format.md"
        section = m.group(1)
        assert '## What it does' in section
        assert '## Rules' in section
        assert '## Proof' in section
        assert re.search(r'RULE-\d+', content)

    @pytest.mark.proof("purlin_references", "PROOF-2", "RULE-2")
    def test_proofs_format_fields_and_merge(self):
        content = _read(os.path.join(FORMATS, 'proofs_format.md'))
        for field in ('feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'):
            assert field in content, f"Missing field: {field}"
        assert re.search(r'[Ff]eature.[Ss]coped [Oo]verwrite', content)

    @pytest.mark.proof("purlin_references", "PROOF-3", "RULE-3")
    def test_proofs_format_three_frameworks(self):
        content = _read(os.path.join(FORMATS, 'proofs_format.md'))
        for fw in ('pytest', 'Jest', 'Shell'):
            assert re.search(rf'###\s+{fw}', content, re.IGNORECASE), \
                f"Missing framework section: {fw}"

    @pytest.mark.proof("purlin_references", "PROOF-4", "RULE-4")
    def test_anchor_format_metadata(self):
        content = _read(os.path.join(FORMATS, 'anchor_format.md'))
        assert '_anchors/' in content
        assert '> Source:' in content
        assert '> Pinned:' in content
        assert re.search(r'[Ss]ync|purlin:anchor', content), \
            "Missing sync protocol documentation"

    @pytest.mark.proof("purlin_references", "PROOF-5", "RULE-5")
    def test_anchor_format_eight_type_values(self):
        content = _read(os.path.join(FORMATS, 'anchor_format.md'))
        type_values = ['design', 'api', 'security', 'brand',
                       'platform', 'schema', 'legal', 'prodbrief']
        for tv in type_values:
            assert tv in content, f"Missing type value: {tv}"

    @pytest.mark.proof("purlin_references", "PROOF-6", "RULE-6")
    def test_hard_gates_exactly_one(self):
        content = _read(os.path.join(REFS, 'hard_gates.md'))
        assert 'Proof Coverage' in content, \
            "Missing 'Proof Coverage' gate name"
        gate_headers = re.findall(r'^## Gate \d+', content, re.MULTILINE)
        assert len(gate_headers) == 1

    @pytest.mark.proof("purlin_references", "PROOF-7", "RULE-7")
    def test_commit_conventions_eight_prefixes(self):
        content = _read(os.path.join(REFS, 'commit_conventions.md'))
        # Extract table/list rows to avoid matching prefixes in prose
        rows = [l for l in content.splitlines()
                if l.strip().startswith('|') or l.strip().startswith('- `')]
        row_text = '\n'.join(rows)
        for prefix in ('spec', 'feat', 'fix', 'test',
                        'verify', 'anchor', 'chore', 'docs'):
            assert prefix in row_text, \
                f"Missing commit prefix '{prefix}' in table/list rows"

    @pytest.mark.proof("purlin_references", "PROOF-8", "RULE-8")
    def test_purlin_commands_categories_and_skills(self):
        content = _read(os.path.join(REFS, 'purlin_commands.md'))
        for category in ('Authoring', 'Building', 'Quality', 'Reporting', 'Project'):
            assert category in content, f"Missing category: {category}"
        expected_skills = {
            'purlin:spec', 'purlin:spec-from-code', 'purlin:build',
            'purlin:unit-test', 'purlin:verify', 'purlin:audit',
            'purlin:status', 'purlin:find', 'purlin:drift',
            'purlin:init', 'purlin:anchor',
            'purlin:rename',
        }
        skills = re.findall(r'`(purlin:[\w-]+)`', content)
        found = set(skills)
        assert found == expected_skills, \
            f"Skill mismatch: missing={expected_skills - found}, extra={found - expected_skills}"

    @pytest.mark.proof("purlin_references", "PROOF-9", "RULE-9")
    def test_spec_quality_guide_coverage(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert re.search(r'5.{1,5}10', content), "Missing 5-10 rules guidance"
        assert 'FORBIDDEN' in content
        # Verify tier assignment is documented as a dedicated section/topic
        assert re.search(r'(?i)##.*tier|tier\s+assign', content), \
            "Missing tier assignment section heading or guidance"
        assert '@integration' in content, "Missing @integration tier tag documentation"
        assert '@e2e' in content, "Missing @e2e tier tag documentation"

    @pytest.mark.proof("purlin_references", "PROOF-10", "RULE-10")
    def test_quality_guide_test_failure_diagnosis(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert 'Code bug' in content, "Missing 'Code bug' diagnosis category"
        assert 'Test bug' in content, "Missing 'Test bug' diagnosis category"
        assert 'Spec drift' in content, "Missing 'Spec drift' diagnosis category"
        assert 'Assertion Integrity' in content, "Missing Assertion Integrity section"

    @pytest.mark.proof("purlin_references", "PROOF-12", "RULE-12")
    def test_drift_criteria_sections(self):
        content = _read(os.path.join(REFS, 'drift_criteria.md'))
        assert 'File Classification' in content, \
            "Missing 'File Classification' section"
        assert 'NO_IMPACT Patterns' in content, \
            "Missing 'NO_IMPACT Patterns' section"
        assert 'Behavioral Directory Exclusions' in content, \
            "Missing 'Behavioral Directory Exclusions' section"
        assert 'Significance Classification' in content, \
            "Missing 'Significance Classification' section"
        assert re.search(r'Structural.Only Drift', content), \
            "Missing 'Structural-Only Drift' section"
        assert 'drift_flags' in content, \
            "Missing 'drift_flags' documentation"

    @pytest.mark.proof("purlin_references", "PROOF-11", "RULE-11")
    def test_quality_guide_audience_language(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert 'Audience-Appropriate Language' in content, \
            "Missing Audience-Appropriate Language section"
        # Verify section contains at least one artifact-to-audience mapping
        m = re.search(
            r'Audience-Appropriate Language(.*?)(?=^## |\Z)', content,
            re.MULTILINE | re.DOTALL
        )
        assert m, "Could not extract Audience-Appropriate Language section"
        section_body = m.group(1)
        # Must contain a table or mapping where an artifact and audience appear on the same line
        lines = section_body.splitlines()
        paired = [l for l in lines
                  if re.search(r'(?i)(rules?|specs?|proofs?|drift)', l)
                  and re.search(r'(?i)(engineer|PM|QA|agent|developer)', l)]
        assert len(paired) >= 3, \
            f"Expected at least 3 artifact-to-audience mapping rows, found {len(paired)}"
