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
        assert '## What it does' in content
        assert '## Rules' in content
        assert '## Proof' in content
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
    def test_invariant_format_metadata(self):
        content = _read(os.path.join(FORMATS, 'invariant_format.md'))
        assert '_invariants/' in content
        assert '> Source:' in content
        assert '> Pinned:' in content

    @pytest.mark.proof("purlin_references", "PROOF-5", "RULE-5")
    def test_anchor_format_eight_prefixes(self):
        content = _read(os.path.join(FORMATS, 'anchor_format.md'))
        prefixes = ['design_', 'api_', 'security_', 'brand_',
                     'platform_', 'schema_', 'legal_', 'prodbrief_']
        for prefix in prefixes:
            assert prefix in content, f"Missing prefix: {prefix}"

    @pytest.mark.proof("purlin_references", "PROOF-6", "RULE-6")
    def test_hard_gates_exactly_two(self):
        content = _read(os.path.join(REFS, 'hard_gates.md'))
        assert 'Invariant Protection' in content or \
               ('Invariant' in content and 'Protection' in content)
        assert 'Proof Coverage' in content or \
               ('Proof' in content and 'Coverage' in content)
        gate_headers = re.findall(r'^## Gate \d+', content, re.MULTILINE)
        assert len(gate_headers) == 2

    @pytest.mark.proof("purlin_references", "PROOF-7", "RULE-7")
    def test_commit_conventions_eight_prefixes(self):
        content = _read(os.path.join(REFS, 'commit_conventions.md'))
        for prefix in ('spec', 'feat', 'fix', 'test',
                        'verify', 'invariant', 'chore', 'docs'):
            assert prefix in content, f"Missing commit prefix: {prefix}"

    @pytest.mark.proof("purlin_references", "PROOF-8", "RULE-8")
    def test_purlin_commands_categories_and_skills(self):
        content = _read(os.path.join(REFS, 'purlin_commands.md'))
        for category in ('Authoring', 'Building', 'Reporting', 'Project'):
            assert category in content, f"Missing category: {category}"
        skills = set(re.findall(r'`(purlin:[\w-]+)`', content))
        assert len(skills) >= 12, f"Expected >= 12 skills, found {len(skills)}: {skills}"

    @pytest.mark.proof("purlin_references", "PROOF-9", "RULE-9")
    def test_spec_quality_guide_coverage(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert re.search(r'5.{1,5}10', content), "Missing 5-10 rules guidance"
        assert 'FORBIDDEN' in content
        assert re.search(r'[Tt]ier', content)

    @pytest.mark.proof("purlin_references", "PROOF-10", "RULE-10")
    def test_quality_guide_test_failure_diagnosis(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert 'Code bug' in content, "Missing 'Code bug' diagnosis category"
        assert 'Test bug' in content, "Missing 'Test bug' diagnosis category"
        assert 'Spec drift' in content, "Missing 'Spec drift' diagnosis category"
        assert 'Assertion Integrity' in content, "Missing Assertion Integrity section"

    @pytest.mark.proof("purlin_references", "PROOF-11", "RULE-11")
    def test_quality_guide_audience_language(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert 'Audience-Appropriate Language' in content, \
            "Missing Audience-Appropriate Language section"
