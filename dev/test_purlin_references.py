"""Tests for purlin_references — 11 rules.

Grep-based structural verification of the 8 reference documents
that define Purlin's formats, conventions, and quality standards.
"""

import json
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
        assert '## Rules' in section
        assert '## Proof' in section
        # Description is now a metadata field, not a required section
        assert '> Description:' in content
        assert re.search(r'RULE-\d+', content)

    @pytest.mark.proof("purlin_references", "PROOF-2", "RULE-2")
    def test_proofs_format_fields_and_merge(self):
        content = _read(os.path.join(FORMATS, 'proofs_format.md'))
        for field in ('feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'):
            assert field in content, f"Missing field: {field}"
        assert re.search(r'[Ww]rite.[Ss]coped [Oo]verwrite', content), \
            "proofs_format.md must name the merge behaviour"
        assert '(feature, tier, test_file)' in content, \
            "proofs_format.md must state the merge key, not just the pattern's name"

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
            'purlin:test', 'purlin:verify', 'purlin:audit',
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
        assert 'rebuild test' in content.lower(), "Missing rebuild test guidance"
        assert 'contract boundar' in content.lower(), "Missing contract boundaries guidance"
        assert 'Coverage dimensions' in content, "Missing coverage dimensions guidance"
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
        assert re.search(r'Behavioral Gap Drift', content), \
            "Missing 'Behavioral Gap Drift Detection' section"
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

    @pytest.mark.proof("purlin_references", "PROOF-13", "RULE-13")
    def test_quality_guide_e2e_proof_section(self):
        content = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert 'E2E proof descriptions' in content, \
            "Missing 'E2E proof descriptions' section"
        m = re.search(
            r'E2E proof descriptions(.*?)(?=^### |^## |\Z)', content,
            re.MULTILINE | re.DOTALL
        )
        assert m, "Could not extract E2E proof descriptions section"
        section = m.group(1)
        assert 'arrange → act → observe' in section, \
            "E2E section missing arrange → act → observe flow language"
        assert re.search(r'(?i)must not name source files or internal functions', section), \
            "E2E section missing the ban on naming source files/internal functions"
        assert re.search(r'(?i)tool-agnostic', section), \
            "E2E section missing tool-agnostic requirement"
        assert re.search(r'(?i)tier/description match|inverse check', section), \
            "E2E section missing the tier/description match (inverse) check"

    @pytest.mark.proof("purlin_references", "PROOF-14", "RULE-14")
    def test_audit_criteria_e2e_tier_integrity(self):
        content = _read(os.path.join(REFS, 'audit_criteria.md'))
        assert 'E2E Proof Tier Integrity' in content, \
            "Missing 'E2E Proof Tier Integrity' section"
        m = re.search(
            r'## E2E Proof Tier Integrity(.*?)(?=^## )', content,
            re.MULTILINE | re.DOTALL
        )
        assert m, "Could not extract E2E Proof Tier Integrity section"
        section = m.group(1)
        assert re.search(r'(?i)tier mismatch', section), \
            "E2E Proof Tier Integrity missing 'tier mismatch' criterion"
        assert re.search(r'(?i)source-constant', section), \
            "E2E Proof Tier Integrity missing 'source-constant assertion' criterion"
        # Section must apply to ALL @e2e proofs, not only design anchors
        assert re.search(r'(?i)ALL proofs tagged `?@e2e`?', section), \
            "E2E Proof Tier Integrity must state it applies to ALL @e2e proofs"
        assert re.search(r'(?i)not just `?design_', section), \
            "E2E Proof Tier Integrity must state it is not limited to design anchors"

    @pytest.mark.proof("purlin_references", "PROOF-15", "RULE-15")
    def test_supported_frameworks_e2e_section(self):
        content = _read(os.path.join(REFS, 'supported_frameworks.md'))
        assert 'End-to-end (browser) proofs' in content, \
            "Missing 'End-to-end (browser) proofs' section"
        m = re.search(
            r'## End-to-end \(browser\) proofs(.*?)(?=^## )', content,
            re.MULTILINE | re.DOTALL
        )
        assert m, "Could not extract End-to-end (browser) proofs section"
        section = m.group(1)
        assert re.search(r'(?i)no dedicated e2e proof reporter', section), \
            "e2e section must state no dedicated reporter ships"
        assert re.search(r'(?i)tool-agnostic', section), \
            "e2e section must describe @e2e proofs as tool-agnostic"
        # Wiring through existing plugins: Vitest/Jest markers and shell purlin_proof
        assert re.search(r'\[proof:[^:\]]+:PROOF-\d+:RULE-\d+:e2e\]', section), \
            "e2e section must document the Vitest/Jest e2e marker wiring"
        assert 'purlin_proof' in section, \
            "e2e section must document the shell purlin_proof wiring"

    @pytest.mark.proof("purlin_references", "PROOF-16", "RULE-16")
    def test_audit_criteria_defines_both_gauges(self):
        """audit_criteria.md must define Proof Design and Proof Integrity separately,
        score each, and mark the Integrity criteria a vague description disables."""
        crit = _read(os.path.join(REFS, 'audit_criteria.md'))

        assert '## Pass D' in crit, "audit_criteria.md missing the Pass D (Proof Design) section"
        for level in ('PROVABLE', 'LOOSE', 'UNPROVABLE', 'STRUCTURAL'):
            assert level in crit, f"audit_criteria.md missing Design level {level}"
        for level in ('STRONG', 'WEAK', 'HOLLOW', 'EXCLUDED', 'MANUAL'):
            assert level in crit, f"audit_criteria.md missing Integrity level {level}"

        # Both scoring formulas, with the Integrity one kept verbatim for sync_status RULE-33
        assert '(STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL)' in crit, \
            "audit_criteria.md must keep the Integrity formula verbatim"
        assert 'PROVABLE / (PROVABLE + LOOSE + UNPROVABLE)' in crit, \
            "audit_criteria.md must state the Design formula"

        # The criteria that only fire against a specific description
        assert crit.count('[relative]') >= 5, \
            "audit_criteria.md must mark the description-relative Integrity criteria"

        guide = _read(os.path.join(REFS, 'spec_quality_guide.md'))
        assert '## Test Quality Rules (Proof Integrity)' in guide, \
            "spec_quality_guide.md must name the gauge its test-quality rules belong to"
        assert guide.count('*Graded as:') >= 4, \
            "spec_quality_guide.md proof-description sections must carry Design-level labels"
        assert 'UNPROVABLE' in guide, \
            "spec_quality_guide.md must use the Design vocabulary for Level 1 descriptions"


class TestHardGatesAccuracy:
    """RULE-17 — hard_gates.md contradicted the verify skill and, read literally,
    described a state no feature could ever reach."""

    @pytest.mark.proof("purlin_references", "PROOF-17", "RULE-17")
    def test_receipt_condition_is_passing_not_verified(self):
        gates = _read(os.path.join(REFS, 'hard_gates.md'))
        assert 'PASSING' in gates, \
            "hard_gates.md must name PASSING as the receipt condition"
        assert re.search(r'(?i)VERIFIED\s+is\s+the\s+state\s+\*?after\*?\s+a\s+receipt', gates, re.S) or \
               re.search(r'(?i)requiring\s+VERIFIED', gates, re.S), \
            "hard_gates.md must explain that VERIFIED is the post-receipt state"
        assert re.search(r'(?i)(deadlock|no\s+feature\s+could\s+ever)', gates, re.S), \
            "hard_gates.md must record why requiring VERIFIED would deadlock"

        # Still exactly one gate, and both gauges are explicitly not gates.
        assert re.search(r'(?i)exactly 1 hard gate', gates), \
            "the single-gate promise must survive"
        not_gate = gates.split('What Is NOT a Gate', 1)
        assert len(not_gate) == 2, "hard_gates.md missing the 'What Is NOT a Gate' list"
        assert 'Proof Design' in not_gate[1] and 'Proof Integrity' in not_gate[1], \
            "both gauges must be listed as non-gates"


class TestRemoteVerificationReference:
    """purlin_references RULE-18/19/20."""

    RV = os.path.join(REFS, 'remote_verification.md')

    @pytest.mark.proof("purlin_references", "PROOF-18", "RULE-18")
    def test_documents_the_loop_and_a_complete_workflow_template(self):
        rv = _read(self.RV)

        assert 'purlin:test' in rv, "the reference must name the owning skill"
        assert re.search(r'(?i)read-only', rv), (
            "it must give verify's read-only contract as the reason the loop "
            "lives in purlin:test")

        for label, pattern in (('push', r'(?i)push(es)? the (current )?branch'),
                               ('dispatch', r'(?i)dispatch'),
                               ('await', r'(?i)await'),
                               ('pull', r'(?i)pull')):
            assert re.search(pattern, rv), f"the loop is missing {label}"

        assert re.search(r'bounded at \*\*3 rounds\*\*|at \*\*3 rounds\*\*|3 rounds',
                         rv), "the 3-round bound must be stated as a literal"

        # The template is what gets copied, so its load-bearing parts must be
        # in the template block itself, not only in the prose around it.
        m = re.search(r'```yaml(.*?)```', rv, re.S)
        assert m, "no YAML workflow template block"
        template = m.group(1)
        assert 'paths-ignore' in template, (
            "a template copied without paths-ignore loops forever")
        assert '[skip ci]' in template, (
            "a template copied without [skip ci] loops on other triggers")
        assert 'Purlin-Runner:' in template, (
            "a template copied without the trailer produces proofs whose "
            "runner is unrecorded")

    @pytest.mark.proof("purlin_references", "PROOF-19", "RULE-19")
    def test_states_the_declaration_enforcement_split_and_the_gauge_gap(self):
        rv = _read(self.RV)

        assert 'branch protection' in rv, (
            "the enforcement must be named")
        assert re.search(r'(?i)declares? the mode', rv), (
            "the field must be described as declaring, not enforcing")
        assert re.search(r'(?i)agent can edit', rv), (
            "the reason must be given: the field is editable in the tree")

        assert re.search(r'(?i)gitignored', rv), (
            "both gauge caches must be recorded as gitignored")
        assert 'audit_cache.json' in rv and 'design_cache.json' in rv, (
            "both caches must be named")
        assert re.search(r'(?i)per-machine|do not\b.*travel|not travelling', rv), (
            "the reference must say the gauges do not travel with a branch")
        assert 'audit_llm' in rv, (
            "the Integrity recommendation must name the config that makes it "
            "possible")
        assert re.search(r'(?i)deterministic', rv), (
            "the Design recommendation rests on it being deterministic")

    @pytest.mark.proof("purlin_references", "PROOF-20", "RULE-20")
    def test_every_config_template_field_has_an_ownership_row(self):
        """A field stamped into new projects with no row here has no recorded
        owner and no recorded default, which is how `digest` went unlisted."""
        with open(os.path.join(PROJECT_ROOT, 'templates', 'config.json')) as f:
            template_keys = set(json.load(f).keys())
        assert template_keys, "templates/config.json is empty"

        drift = _read(os.path.join(REFS, 'drift_criteria.md'))
        section = drift.split('Config Field Ownership', 1)
        assert len(section) == 2, "drift_criteria.md has no ownership section"
        body = section[1].split('\n## ', 1)[0]

        listed = set(re.findall(r'^\|\s*`([^`]+)`\s*\|', body, re.M))
        assert listed, "the ownership table has no rows"

        missing = sorted(template_keys - listed)
        assert not missing, (
            f"templates/config.json stamps {missing} into every new project "
            f"with no row in drift_criteria.md's Config Field Ownership table")

        # Optional fields init never writes still need an owner and a default:
        # a skill reads them, so somebody has to say who sets them.
        optional = {'audit_llm', 'audit_llm_name', 'audit_criteria',
                    'audit_criteria_pinned', 'platforms'}
        missing_optional = sorted(optional - listed)
        assert not missing_optional, (
            f"optional config fields {missing_optional} are read by a skill but "
            f"have no row in drift_criteria.md's Config Field Ownership table")

    @pytest.mark.proof("purlin_references", "PROOF-21", "RULE-21")
    def test_receipt_format_is_the_receipt_contract(self):
        """RULE-21: the receipt contract lives in one file and states the
        version, every v2 field, what the vhash does and does not bind, and
        that a receipt issued without a run marker records no run."""
        path = os.path.join(FORMATS, 'receipt_format.md')
        assert os.path.isfile(path), \
            "references/formats/receipt_format.md is the receipt contract"
        content = _read(path)

        m = re.match(r'>\s*Format-Version:\s*(\d+)', content)
        assert m, "receipt_format.md must open with a > Format-Version: line"
        assert int(m.group(1)) >= 2, \
            f"receipt v2 needs Format-Version 2 or later, got {m.group(1)}"

        fields = ['feature', 'vhash', 'vhash_version', 'commit', 'timestamp',
                  'rules', 'rule_hashes', 'proofs', 'manual', 'evidence',
                  'test_run', 'proof_files', 'awaiting_runner']
        missing = [f for f in fields if f'`{f}`' not in content]
        assert not missing, \
            f"receipt_format.md documents no {missing} field"

        row_keys = ['file', 'tier', 'platform', 'committed_at', 'runner',
                    'executed_in_test_run']
        missing_rows = [k for k in row_keys if f'`{k}`' not in content]
        assert not missing_rows, (
            f"the proof_files row keys {missing_rows} are undocumented, so a "
            f"consumer cannot read the evidence block")

        assert 'What the vhash binds' in content, \
            "receipt_format.md must say what the vhash binds"
        assert 'It does not bind' in content, (
            "receipt_format.md must say what the vhash does NOT bind: a hash "
            "read as binding the source code is read as a signature")

        assert re.search(r'^## Version 1', content, re.M), \
            "receipt_format.md must document the version 1 shape as historical"

        null_marker = re.search(
            r'`evidence\.test_run` is null for a receipt issued without a '
            r'run marker', content)
        assert null_marker, (
            "receipt_format.md must state that evidence.test_run is null for a "
            "receipt issued without a run marker")
