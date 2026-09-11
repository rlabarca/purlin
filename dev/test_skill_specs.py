"""Tests for individual skill specs — one spec per skill.

Structural verification of each skill definition file under skills/.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
from static_checks import (
    check_python,
    load_criteria,
    read_audit_cache,
    write_audit_cache,
)
import purlin_server

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
SKILLS_DIR = os.path.join(PROJECT_ROOT, 'skills')
REFS_DIR = os.path.join(PROJECT_ROOT, 'references')


def _read(skill_name):
    path = os.path.join(SKILLS_DIR, skill_name, 'SKILL.md')
    with open(path) as f:
        return f.read()


def _read_ref(ref_name):
    path = os.path.join(REFS_DIR, ref_name)
    with open(path) as f:
        return f.read()


def _assert_frontmatter(content, skill_name):
    m = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    assert m, f"No frontmatter in {skill_name}"
    fm = m.group(1)
    assert 'name:' in fm, f"Missing name: in {skill_name}"
    assert 'description:' in fm, f"Missing description: in {skill_name}"


def _assert_usage(content, skill_name):
    assert '## Usage' in content, f"No ## Usage section in {skill_name}"


def _assert_name_matches(content, skill_name):
    m = re.search(r'^name:\s*(.+)', content, re.MULTILINE)
    assert m, f"No name: field in {skill_name}"
    assert m.group(1).strip() == skill_name, \
        f"name '{m.group(1).strip()}' != dir '{skill_name}'"


def _assert_commit_instructions(content, skill_name):
    assert re.search(r'(?i)(git commit|commit the|create.*commit|commit.*change)', content), \
        f"{skill_name} skill missing positive commit instruction"


# ── skill_anchor ──────────────────────────────────────────────────────

class TestSkillAnchor:

    @pytest.mark.proof("skill_anchor", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('anchor')
        assert '---' in content, "anchor SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'anchor')

    @pytest.mark.proof("skill_anchor", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('anchor')
        assert '## Usage' in content, "anchor SKILL.md must have a ## Usage section"
        _assert_usage(content, 'anchor')

    @pytest.mark.proof("skill_anchor", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('anchor')
        assert 'name:' in content, "anchor SKILL.md must have a name: field"
        _assert_name_matches(content, 'anchor')

    @pytest.mark.proof("skill_anchor", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        content = _read('anchor')
        assert re.search(r'(?i)(git commit|commit the|create.*commit|commit.*change)', content), \
            "anchor skill missing positive commit instruction"
        _assert_commit_instructions(content, 'anchor')


# ── skill_audit ───────────────────────────────────────────────────────

class TestSkillAudit:

    @pytest.mark.proof("skill_audit", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('audit')
        assert '---' in content, "audit SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'audit')

    @pytest.mark.proof("skill_audit", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('audit')
        assert '## Usage' in content, "audit SKILL.md must have a ## Usage section"
        _assert_usage(content, 'audit')

    @pytest.mark.proof("skill_audit", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('audit')
        assert 'name:' in content, "audit SKILL.md must have a name: field"
        _assert_name_matches(content, 'audit')

    @pytest.mark.proof("skill_audit", "PROOF-4", "RULE-4", tier="e2e")
    def test_independent_auditor_reads_criteria_and_assesses(self):
        content = _read('audit')
        assert re.search(r'(?i)independent auditor', content), \
            "audit SKILL.md missing 'independent auditor' section"
        assert 'audit_criteria' in content, \
            "audit SKILL.md missing audit_criteria reference in independent auditor mode"
        assert 'STRONG' in content, "audit SKILL.md missing STRONG assessment level"
        assert 'WEAK' in content, "audit SKILL.md missing WEAK assessment level"
        assert 'HOLLOW' in content, "audit SKILL.md missing HOLLOW assessment level"

    @pytest.mark.proof("skill_audit", "PROOF-5", "RULE-5", tier="e2e")
    def test_independent_auditor_routes_findings_to_build(self):
        content = _read('audit')
        assert 'purlin:build' in content, \
            "audit SKILL.md must route remediation to purlin:build"
        assert re.search(r'(?i)read-only', content), \
            "audit SKILL.md must state the audit is read-only"
        assert 'purlin-builder' not in content, \
            "purlin-builder is retired — it is not a spawnable type in consumer projects"
        assert re.search(r'(?i)(PROOF-ID|finding|fix)', content), \
            "audit SKILL.md missing three-part finding structure"

    @pytest.mark.proof("skill_audit", "PROOF-6", "RULE-6", tier="e2e")
    def test_independent_auditor_re_audits_after_fixes_land(self):
        content = _read('audit')
        assert re.search(r'(?i)(re-audit|re.audit)', content), \
            "audit SKILL.md missing re-audit step after fixes land"
        assert re.search(r'(?i)after the fixes land', content), \
            "audit SKILL.md must say re-audit happens after the fixes land"

    @pytest.mark.proof("skill_audit", "PROOF-7", "RULE-7", tier="e2e")
    def test_independent_auditor_terminates_after_3_rounds(self):
        content = _read('audit')
        assert re.search(r'3 rounds', content), \
            "audit SKILL.md missing '3 rounds' termination condition"
        assert re.search(r'(?i)(rounds exhausted|move on|all findings addressed)', content), \
            "audit SKILL.md missing termination language (findings addressed or rounds exhausted)"

    @pytest.mark.proof("skill_audit", "PROOF-8", "RULE-8", tier="e2e")
    def test_anchor_rule_handling_reports_to_lead(self):
        content = _read('audit')
        assert re.search(r'(?i)anchor rule', content), \
            "audit SKILL.md missing Anchor Rule Handling section"
        assert re.search(r'(?i)message the lead', content), \
            "audit SKILL.md missing 'message the lead' for ambiguous anchor rules"
        assert re.search(r'(?i)(ambiguous|could be clearer)', content), \
            "audit SKILL.md missing ambiguous rule guidance in anchor handling"

    @pytest.mark.proof("skill_audit", "PROOF-9", "RULE-9", tier="e2e")
    def test_static_checks_detects_hollow_test_as_non_strong(self):
        """Pass 1 (static_checks) catches deliberately hollow tests — assert True is flagged as fail."""
        hollow_code = (
            'import pytest\n'
            '\n'
            '@pytest.mark.proof("myfeature", "PROOF-1", "RULE-1")\n'
            'def test_hollow_assert_true():\n'
            '    assert True\n'
        )
        path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(hollow_code)
                path = f.name
            results = check_python(path, 'myfeature')
            assert len(results) == 1, "Expected one proof result for hollow test"
            assert results[0]['status'] == 'fail', \
                "Hollow test (assert True) must not pass static checks"
            assert results[0]['check'] == 'assert_true', \
                f"Expected 'assert_true' check, got '{results[0]['check']}'"
        finally:
            if path:
                os.unlink(path)

    @pytest.mark.proof("skill_audit", "PROOF-10", "RULE-10", tier="e2e")
    def test_static_checks_passes_well_structured_test(self):
        """Pass 1 passes a well-structured test with real assertions — eligible for STRONG or WEAK via LLM."""
        strong_code = (
            'import pytest\n'
            '\n'
            '@pytest.mark.proof("myfeature", "PROOF-1", "RULE-1")\n'
            'def test_well_structured():\n'
            '    result = sorted([3, 1, 2])\n'
            '    assert result == [1, 2, 3]\n'
        )
        path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(strong_code)
                path = f.name
            results = check_python(path, 'myfeature')
            assert len(results) == 1, "Expected one proof result for well-structured test"
            assert results[0]['status'] == 'pass', \
                "Well-structured test with real assertions must pass static checks"
        finally:
            if path:
                os.unlink(path)

    @pytest.mark.proof("skill_audit", "PROOF-11", "RULE-11", tier="e2e")
    def test_skill_documents_external_llm_response_fields(self):
        """The skill documents that parsing must extract all required fields from LLM output."""
        content = _read('audit')
        for field in ('PROOF-ID', 'ASSESSMENT', 'CRITERION', 'WHY', 'FIX'):
            assert field in content, \
                f"audit SKILL.md external LLM section missing required field: {field}"
        assert re.search(r'(?i)(flexible|different LLMs|format slightly differently)', content), \
            "audit SKILL.md missing flexible parsing note for external LLM responses"

    @pytest.mark.proof("skill_audit", "PROOF-12", "RULE-12", tier="e2e")
    def test_two_pass_flow_hollow_caught_in_pass1_valid_passes_through(self):
        """Pass 1 flags assert True as HOLLOW; well-structured test survives and proceeds to Pass 2."""
        mixed_code = (
            'import pytest\n'
            '\n'
            '@pytest.mark.proof("myfeature", "PROOF-1", "RULE-1")\n'
            'def test_hollow():\n'
            '    assert True\n'
            '\n'
            '@pytest.mark.proof("myfeature", "PROOF-2", "RULE-2")\n'
            'def test_valid():\n'
            '    result = sorted([3, 1, 2])\n'
            '    assert result == [1, 2, 3]\n'
        )
        path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(mixed_code)
                path = f.name
            results = check_python(path, 'myfeature')
            assert len(results) == 2, f"Expected 2 proof results, got {len(results)}"
            by_proof = {r['proof_id']: r for r in results}
            assert by_proof['PROOF-1']['status'] == 'fail', \
                "PROOF-1 (assert True) must fail Pass 1 as HOLLOW"
            assert by_proof['PROOF-1']['check'] == 'assert_true', \
                "PROOF-1 must be flagged as assert_true"
            assert by_proof['PROOF-2']['status'] == 'pass', \
                "PROOF-2 (valid test) must pass Pass 1 and be eligible for Pass 2 (LLM)"
        finally:
            if path:
                os.unlink(path)

    @pytest.mark.proof("skill_audit", "PROOF-13", "RULE-13", tier="e2e")
    def test_config_stores_audit_llm_fields_and_skill_documents_external_llm_mode(self):
        """Config stores audit_llm and audit_llm_name; skill documents the external LLM two-pass flow."""
        content = _read('audit')
        assert 'audit_llm' in content, \
            "audit SKILL.md missing audit_llm config field documentation"
        assert re.search(r'(?i)(pass 1.*external|external.*pass 1|still runs pass 1)', content), \
            "audit SKILL.md must document that Pass 1 runs before external LLM"
        assert re.search(
            r'(?i)(external llm.*independent audit|independent.*external llm)', content
        ), "audit SKILL.md missing 'External LLM with Independent Audit' subsection"
        # Verify config fields round-trip through JSON
        tmp_dir = tempfile.mkdtemp()
        try:
            purlin_dir = os.path.join(tmp_dir, '.purlin')
            os.makedirs(purlin_dir)
            config = {
                "version": "0.9.0",
                "audit_llm": "echo 'fake response'",
                "audit_llm_name": "FakeLLM",
            }
            config_path = os.path.join(purlin_dir, 'config.json')
            with open(config_path, 'w') as f:
                json.dump(config, f)
            with open(config_path) as f:
                loaded = json.load(f)
            assert loaded['audit_llm'] == "echo 'fake response'", \
                "audit_llm field must round-trip through config JSON"
            assert loaded['audit_llm_name'] == "FakeLLM", \
                "audit_llm_name field must round-trip through config JSON"
        finally:
            shutil.rmtree(tmp_dir)

    @pytest.mark.proof("skill_audit", "PROOF-14", "RULE-14", tier="e2e")
    def test_load_criteria_assembles_builtin_plus_additional_and_pass1_still_works(self):
        """load_criteria() appends additional criteria after built-in; Pass 1 still catches assert True."""
        tmp_dir = tempfile.mkdtemp()
        try:
            purlin_dir = os.path.join(tmp_dir, '.purlin')
            cache_dir = os.path.join(purlin_dir, 'cache')
            os.makedirs(cache_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"version": "0.9.0", "audit_criteria": "team://custom-standards"}, f)
            additional_criteria = "## Custom Rule\n\nAll tests must use fixtures.\n"
            with open(os.path.join(cache_dir, 'additional_criteria.md'), 'w') as f:
                f.write(additional_criteria)

            combined = load_criteria(tmp_dir)

            assert 'Criteria-Version' in combined, \
                "load_criteria must include built-in criteria (Criteria-Version header)"
            assert 'assert True' in combined or 'Tautological' in combined, \
                "load_criteria must include built-in tautological assertion criterion"
            assert 'Custom Rule' in combined, \
                "load_criteria must append additional team criteria"
            assert combined.index('Criteria-Version') < combined.index('Custom Rule'), \
                "built-in criteria must appear before additional criteria (appended, not replaced)"

            # Pass 1 catches assert True independently of criteria configuration
            hollow_code = (
                'import pytest\n'
                '\n'
                '@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")\n'
                'def test_hollow():\n'
                '    assert True\n'
            )
            path = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                    f.write(hollow_code)
                    path = f.name
                results = check_python(path, 'testfeat')
                assert len(results) == 1
                assert results[0]['status'] == 'fail', \
                    "Pass 1 must still catch assert True with additional criteria configured"
                assert results[0]['check'] == 'assert_true'
            finally:
                if path:
                    os.unlink(path)
        finally:
            shutil.rmtree(tmp_dir)

    @pytest.mark.proof("skill_audit", "PROOF-15", "RULE-15")
    def test_documents_portable_interpreter_fallback(self):
        """SKILL.md documents python -> py -3 fallbacks for python3 (Windows PATH)."""
        content = _read('audit')
        assert 'py -3' in content, \
            "audit SKILL.md must document the 'py -3' interpreter fallback"
        assert '`python`' in content or 'then `python`' in content or 'python`,' in content, \
            "audit SKILL.md must document the 'python' interpreter fallback"

    @pytest.mark.proof("skill_audit", "PROOF-16", "RULE-16")
    def test_documents_empty_test_file_fallback(self):
        """SKILL.md documents resolving an empty test_file from test_name via
        --resolve-source, and names CollectSourceInformation as the native fix."""
        content = _read('audit')
        assert '--resolve-source' in content, \
            "audit SKILL.md must document the --resolve-source fallback"
        assert 'test_file' in content and 'test_name' in content, \
            "audit SKILL.md must explain resolving an empty test_file from test_name"
        assert 'CollectSourceInformation' in content, \
            "audit SKILL.md must name CollectSourceInformation as the native way to populate test_file"

    @pytest.mark.proof("skill_audit", "PROOF-17", "RULE-17")
    def test_documents_which_lever_moves_which_assessment(self):
        """The skill must say which lever moves which assessment, so an agent does not
        try to raise Integrity by editing spec prose, and must carry the arithmetic."""
        content = _read('audit')
        section = content.split('## Which Lever Moves Which Assessment', 1)
        assert len(section) == 2, \
            "audit SKILL.md missing 'Which Lever Moves Which Assessment' section"
        body = section[1].split('## Key Principles', 1)[0]

        # Each level, and what actually moves it
        for level in ('HOLLOW', 'EXCLUDED', 'WEAK', 'UNPROVABLE'):
            assert level in body, f"lever section must name {level}"
        assert 'purlin:build' in body, \
            "lever section must say HOLLOW is moved by editing the test via purlin:build"
        assert re.search(r'(?i)narrow', body), \
            "lever section must warn against narrowing a proof description"
        assert re.search(r'(?i)anchor', body), \
            "lever section must forbid narrowing descriptions for anchor rules"
        assert re.search(r'(?i)(shrink|denominator)', body), \
            "lever section must warn that reclassifying shrinks the denominator"

        # The arithmetic, so feasibility is a one-step answer
        assert '(N \u2212 H) / N' in body or '(N - H) / N' in body, \
            "lever section must state the ceiling formula"
        assert re.search(r'H\s*\u2264\s*\(1\s*\u2212\s*T\)', body) or \
               re.search(r'H\s*<=\s*\(1\s*-\s*T\)', body), \
            "lever section must state the reachability condition"

    @pytest.mark.proof("skill_audit", "PROOF-18", "RULE-18")
    def test_cache_write_is_its_own_mandatory_step(self):
        """The cache write must be a numbered step naming the command, ordered before the
        prune. Prose alone left every later step depending on something that never ran."""
        content = _read('audit')

        m = re.search(r'^## (Step [\d.]+) [^\n]*Write Audit Cache[^\n]*$', content, re.M)
        assert m, "audit SKILL.md has no numbered 'Write Audit Cache' step"
        heading = m.group(0)
        assert re.search(r'(?i)mandatory', heading), \
            "the cache-write step must be marked mandatory in its heading"

        # Must be ordered before the prune step, which assumes it already ran
        prune = content.find('## Step 3.5')
        assert prune > m.start(), \
            "the cache-write step must come before the prune step"

        body = content[m.end():prune]
        assert '--write-cache' in body, \
            "the cache-write step must name the literal --write-cache command"
        assert '--project-root' in body, \
            "the cache-write step must pass --project-root explicitly (cache modes default to cwd)"
        assert re.search(r'(?i)no measurement', body), \
            "the step must state that an audit without a cache write produced no measurement"
        for field in ('feature', 'proof_id'):
            assert field in body, f"the documented entry shape must include {field}"

        # The prune must warn against the empty-live-keys full sweep
        prune_body = content[prune:content.find('## Step 4')]
        assert re.search(r'(?i)empty live-keys', prune_body), \
            "the prune step must warn against pruning with an empty live-keys file"

    @pytest.mark.proof("skill_audit", "PROOF-19", "RULE-19")
    def test_mode_is_derived_from_observable_state(self):
        """The agent must derive the mode, not guess. Without this, an audit on a
        spec-only project runs Pass 0.5 and Pass 1 against files that do not
        exist, and static_checks exits 2."""
        content = _read('audit')
        section = content.split('## Step 0', 1)
        assert len(section) == 2, "audit SKILL.md has no Step 0 mode-selection step"
        body = section[1].split('## Step D', 1)[0]

        assert '--audit-scope' in body, "Step 0 must invoke --audit-scope"
        assert 'design' in body and 'both' in body, \
            "Step 0 must name both mode outcomes"
        assert '--design' in body and '--integrity' in body, \
            "Step 0 must document the explicit overrides"
        assert 'scope_files_exist' in body, \
            "Step 0 must use scope_files_exist to tell 'nothing built' from 'no tests'"
        assert re.search(r'(?i)announce', body), \
            "Step 0 must require announcing the chosen mode"
        assert re.search(r'exit 2', body), \
            "Step 0 must warn that Pass 0.5 / Pass 1 exit 2 without proof files"

    @pytest.mark.proof("skill_audit", "PROOF-20", "RULE-20")
    def test_documents_the_proof_design_pass(self):
        content = _read('audit')
        section = content.split('## Step D', 1)
        assert len(section) == 2, "audit SKILL.md has no Proof Design pass"
        body = section[1].split('## Step 1 ', 1)[0]

        assert '--check-proof-design' in body
        for level in ('PROVABLE', 'LOOSE', 'UNPROVABLE', 'STRUCTURAL'):
            assert level in body, f"Design pass must name {level}"
        assert 'PROVABLE + LOOSE + UNPROVABLE' in body, \
            "Design pass must state the scoring formula"
        assert 'purlin:spec' in body, \
            "a Design finding is fixed in the spec, not the build loop"
        assert re.search(r'STRONG/WEAK/HOLLOW', body), \
            "Design pass must forbid using test vocabulary for descriptions"


# ── skill_build ───────────────────────────────────────────────────────

class TestSkillBuild:

    @pytest.mark.proof("skill_build", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('build')
        assert '---' in content, "build SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'build')

    @pytest.mark.proof("skill_build", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('build')
        assert '## Usage' in content, "build SKILL.md must have a ## Usage section"
        _assert_usage(content, 'build')

    @pytest.mark.proof("skill_build", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('build')
        assert 'name:' in content, "build SKILL.md must have a name: field"
        _assert_name_matches(content, 'build')

    @pytest.mark.proof("skill_build", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        content = _read('build')
        assert re.search(r'(?i)(git commit|commit the|create.*commit|commit.*change)', content), \
            "build skill missing positive commit instruction"
        _assert_commit_instructions(content, 'build')

    @pytest.mark.proof("skill_build", "PROOF-5", "RULE-5")
    def test_requires_sync_status_not_optional(self):
        content = _read('build')
        assert 'sync_status' in content, \
            "build skill doesn't reference sync_status"
        assert 'not optional' in content, \
            "build skill doesn't state sync_status is not optional"

    @pytest.mark.proof("skill_build", "PROOF-6", "RULE-6")
    def test_has_failure_diagnosis_guidance(self):
        content = _read('build')
        assert 'diagnose' in content, \
            "build skill missing test failure diagnosis guidance"
        assert 'Never weaken' in content, \
            "build skill missing 'Never weaken' assertion guardrail"

    @pytest.mark.proof("skill_build", "PROOF-7", "RULE-7")
    def test_has_tier_review(self):
        content = _read('build')
        assert re.search(r'(?i)(tier\s+(assign|review|tag)|review.*tier|assign.*tier)', content), \
            "build skill missing tier review step/instruction"
        assert re.search(r'@integration|@e2e|unit.*tier|tier.*unit', content), \
            "build skill missing tier tag references (@integration/@e2e/unit)"

    @pytest.mark.proof("skill_build", "PROOF-8", "RULE-8")
    def test_documents_proof_fixer_mode(self):
        content = _read('build')
        # Build skill must document the "proof fixer" mode invoked by the auditor
        assert re.search(r'(?i)(proof fixer|running as proof fixer)', content), \
            "build skill missing 'proof fixer' mode documentation"
        # Must instruct to fix proofs based on audit feedback
        assert re.search(r'(?i)(audit.*finding|finding.*audit|fix.*proof|HOLLOW|WEAK)', content), \
            "build skill missing fix-proofs-based-on-audit instruction"
        # Must document reporting back after fixing
        assert re.search(r'(?i)(report back|re-audit|Fixed.*PROOF)', content), \
            "build skill missing 'report back' / 're-audit' instruction after fixing"

    @pytest.mark.proof("skill_build", "PROOF-9", "RULE-9")
    def test_documents_changeset_summary(self):
        content = _read('build')
        # Must have Changeset Summary section
        assert re.search(r'(?i)changeset summary', content), \
            "build skill missing 'Changeset Summary' section"
        # Must document all three sections
        assert re.search(r'── Changeset ', content), \
            "build skill missing Changeset section header"
        assert re.search(r'── Decisions ', content), \
            "build skill missing Decisions section header"
        assert re.search(r'── Review ', content), \
            "build skill missing Review section header"
        # Must show rule→file:line mapping format
        assert re.search(r'RULE-\d+ →.*:', content), \
            "build skill missing RULE-N → file:line mapping format"

    @pytest.mark.proof("skill_build", "PROOF-10", "RULE-10")
    def test_changeset_summary_in_commit_body(self):
        content = _read('build')
        # Commit step must reference changeset summary as commit message body
        assert re.search(r'(?i)changeset summary.*commit message body|commit message body.*changeset summary',
                         content), \
            "build skill missing instruction to use changeset summary as commit message body"
        # Must reference commit_conventions.md
        assert 'commit_conventions.md' in content, \
            "build skill Step 6 missing reference to commit_conventions.md"

    @pytest.mark.proof("skill_build", "PROOF-11", "RULE-11")
    def test_proof_fixer_changeset_maps_proofs(self):
        content = _read('build')
        # Proof fixer section must document changeset with PROOF-N mapping
        assert re.search(r'(?i)proof fixer.*changeset|changeset.*proof fix', content), \
            "build skill missing proof fixer changeset documentation"
        # Must document skipping Decisions section in proof fixer mode
        assert re.search(r'(?i)(skip|omit|no).*decisions', content), \
            "build skill missing instruction to skip Decisions in proof fixer mode"

    @pytest.mark.proof("skill_build", "PROOF-12", "RULE-12")
    def test_has_exit_criteria(self):
        content = _read('build')
        assert '## Exit Criteria' in content, \
            "build skill missing '## Exit Criteria' section"
        # Must require tests pass
        assert re.search(r'(?i)tests pass', content), \
            "build exit criteria missing tests pass requirement"
        # Must require changeset summary
        assert re.search(r'(?i)changeset summary.*printed|printed.*changeset summary', content), \
            "build exit criteria missing changeset summary requirement"
        # Must require committed changes
        assert re.search(r'(?i)all changes committed|changes committed', content), \
            "build exit criteria missing commit requirement"
        # Must require no uncommitted proof files
        assert re.search(r'(?i)uncommitted proof files', content), \
            "build exit criteria missing uncommitted proof files check"



    @pytest.mark.proof("skill_build", "PROOF-20", "RULE-13")
    def test_forbids_narrowing_the_proof_description(self):
        """The cheap way to silence the assertion-change warning is to edit the
        description down to match the test. That lowers Proof Design and leaves
        Integrity looking fine, because Integrity is measured against the
        description."""
        content = _read('build')
        assert re.search(r'(?i)never\s+resolve', content) or \
               re.search(r'(?i)never\s+.{0,30}narrow', content), \
            "build SKILL.md must forbid narrowing the proof description"
        assert 'Proof Design' in content and 'Proof Integrity' in content, \
            "the guard must name which gauge each choice moves"
        assert re.search(r'(?i)anchor', content), \
            "narrowing an anchor-rule description must be forbidden outright"

# ── skill_drift ───────────────────────────────────────────────────────

class TestSkillDrift:

    @pytest.mark.proof("skill_drift", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('drift')
        assert '---' in content, "drift SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'drift')

    @pytest.mark.proof("skill_drift", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('drift')
        assert '## Usage' in content, "drift SKILL.md must have a ## Usage section"
        _assert_usage(content, 'drift')

    @pytest.mark.proof("skill_drift", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('drift')
        assert 'name:' in content, "drift SKILL.md must have a name: field"
        _assert_name_matches(content, 'drift')

    @pytest.mark.proof("skill_drift", "PROOF-4", "RULE-4")
    def test_references_drift_mcp_tool(self):
        content = _read('drift')
        assert 'drift' in content, \
            "drift skill doesn't reference MCP tool 'drift'"

    @pytest.mark.proof("skill_drift", "PROOF-5", "RULE-5")
    def test_requires_reading_diffs(self):
        content = _read('drift')
        assert 'git diff' in content, \
            "drift skill missing git diff requirement"



    @pytest.mark.proof("skill_drift", "PROOF-6", "RULE-6")
    def test_changed_specs_is_not_automatically_drift(self):
        """Every specs/ edit classifies as CHANGED_SPECS, so a spec-first project
        triggers it on every run. Calling that drift is wrong when no code exists."""
        content = _read('drift')
        assert 'CHANGED_SPECS' in content
        assert re.search(r'(?i)does not imply', content), \
            "drift SKILL.md must state CHANGED_SPECS does not imply code is out of sync"
        assert 'Scope:' in content, \
            "the check must be whether the spec's scope files exist"
        assert 'purlin:build' in content, \
            "with no implementation there is nothing to have drifted from — route to build"

# ── skill_find ────────────────────────────────────────────────────────

class TestSkillFind:

    @pytest.mark.proof("skill_find", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('find')
        assert '---' in content, "find SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'find')

    @pytest.mark.proof("skill_find", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('find')
        assert '## Usage' in content, "find SKILL.md must have a ## Usage section"
        _assert_usage(content, 'find')

    @pytest.mark.proof("skill_find", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('find')
        assert 'name:' in content, "find SKILL.md must have a name: field"
        _assert_name_matches(content, 'find')

    @pytest.mark.proof("skill_find", "PROOF-4", "RULE-4")
    def test_references_sync_status_mcp_tool(self):
        content = _read('find')
        assert 'sync_status' in content, \
            "find skill doesn't reference MCP tool 'sync_status'"


# ── skill_init ────────────────────────────────────────────────────────

class TestSkillInit:

    @pytest.mark.proof("skill_init", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('init')
        assert '---' in content, "init SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'init')

    @pytest.mark.proof("skill_init", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('init')
        assert '## Usage' in content, "init SKILL.md must have a ## Usage section"
        _assert_usage(content, 'init')

    @pytest.mark.proof("skill_init", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('init')
        assert 'name:' in content, "init SKILL.md must have a name: field"
        _assert_name_matches(content, 'init')

    @pytest.mark.proof("skill_init", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        content = _read('init')
        assert re.search(r'(?i)(git commit|commit the|create.*commit|commit.*change)', content), \
            "init skill missing positive commit instruction"
        _assert_commit_instructions(content, 'init')

    @pytest.mark.proof("skill_init", "PROOF-5", "RULE-5")
    def test_add_plugin_validates_by_language(self):
        content = _read('init')
        for lang in ('Python', 'JavaScript', 'Shell', 'Java'):
            assert lang in content, \
                f"init skill missing validation entry for {lang}"
        assert "doesn't look like a standard proof plugin" in content, \
            "init skill missing validation warning text"

    @pytest.mark.proof("skill_init", "PROOF-6", "RULE-6")
    def test_add_plugin_supports_file_and_git(self):
        content = _read('init')
        assert 'local file path' in content, \
            "init skill missing local file path source docs"
        assert 'git URL' in content, \
            "init skill missing git URL source docs"
        assert re.search(r'(?i)if source is a local file path', content), \
            "init skill missing conditional step for local file path handling"
        assert re.search(r'(?i)if source is a git URL', content), \
            "init skill missing conditional step for git URL handling"

    @pytest.mark.proof("skill_init", "PROOF-7", "RULE-7")
    def test_list_plugins_labels_builtin_and_custom(self):
        content = _read('init')
        ref = _read_ref('supported_frameworks.md')
        # Framework→plugin associations live in supported_frameworks.md
        assert re.search(r'pytest_purlin\.py.*Python|Python.*pytest_purlin\.py',
                         ref), \
            "supported_frameworks.md missing pytest_purlin.py → Python association"
        assert re.search(r'jest_purlin\.js.*JavaScript|JavaScript.*jest_purlin\.js',
                         ref), \
            "supported_frameworks.md missing jest_purlin.js → JavaScript association"
        # SKILL.md must reference the file and document the custom label
        assert 'supported_frameworks.md' in content, \
            "init skill missing reference to supported_frameworks.md for plugin labels"
        assert 'custom' in content, \
            "init skill missing 'custom' label for non-built-in plugins"

    # ── RULE-8 through RULE-32 ────────────────────────────────────────



























    @pytest.mark.proof("skill_init", "PROOF-35", "RULE-33")
    def test_skill_prints_detecting_codebase_before_scan(self):
        """SKILL.md must instruct printing DETECTING CODEBASE before framework scan."""
        content = _read('init')
        # Must contain the exact status message
        assert 'DETECTING CODEBASE' in content, \
            "init SKILL.md missing 'DETECTING CODEBASE' status message"
        # The message must appear BEFORE the detection checklist
        detecting_pos = content.index('DETECTING CODEBASE')
        # Detection logic references conftest.py — that must come after
        conftest_pos = content.index('conftest.py')
        assert detecting_pos < conftest_pos, \
            "DETECTING CODEBASE must appear before framework detection logic"

    @pytest.mark.proof("skill_init", "PROOF-36", "RULE-34")
    def test_skill_always_presents_framework_selection_list(self):
        """SKILL.md must instruct always showing the selection list, even on auto-detect."""
        content = _read('init')
        # Must document presenting the list always (not just when no detection)
        assert re.search(r'(?i)always present the framework selection list', content), \
            "init SKILL.md missing 'always present the framework selection list' instruction"
        # Must use checkbox-style markers [x] and [ ]
        assert '[x]' in content, \
            "init SKILL.md missing [x] pre-selected checkbox marker"
        assert '[ ]' in content, \
            "init SKILL.md missing [ ] unselected checkbox marker"
        # Must document pre-selection of detected frameworks
        assert re.search(r'(?i)pre-select.*detected|detected.*pre-selected', content), \
            "init SKILL.md missing pre-selection of detected frameworks"
        # Must include a confirm prompt
        assert re.search(r'(?i)confirm.*selection|confirm.*change', content), \
            "init SKILL.md missing confirmation prompt for framework selection"

    @pytest.mark.proof("skill_init", "PROOF-37", "RULE-35")
    def test_skill_shows_single_detection_preselected(self):
        """SKILL.md must show a template for single detection with [x] and [ ] markers."""
        content = _read('init')
        ref = _read_ref('supported_frameworks.md')
        # SKILL.md must show [x] for detected and [ ] for unselected in same block
        assert '[x]' in content and '[ ]' in content, \
            "init SKILL.md missing [x]/[ ] checkbox markers for detection example"
        # The template shows detected framework with detection reason
        assert re.search(r'\[x\].*detection reason', content), \
            "init SKILL.md missing [x] with detection reason template"
        # supported_frameworks.md must have at least one detection heuristic
        assert re.search(r'conftest\.py|package\.json|Makefile', ref), \
            "supported_frameworks.md missing detection heuristics"

    @pytest.mark.proof("skill_init", "PROOF-38", "RULE-36")
    def test_skill_shows_multi_detection_preselected(self):
        """SKILL.md documents that multiple detected frameworks are all pre-selected."""
        content = _read('init')
        ref = _read_ref('supported_frameworks.md')
        # SKILL.md must document that detected frameworks are pre-selected
        assert re.search(r'(?i)pre-select.*detected|detected.*pre-selected',
                         content), \
            "init SKILL.md missing detected framework pre-selection instruction"
        # supported_frameworks.md must list multiple frameworks
        frameworks = re.findall(r'^\| \*\*(\w+)\*\*', ref, re.MULTILINE)
        assert len(frameworks) >= 3, \
            f"supported_frameworks.md should list multiple frameworks, found {len(frameworks)}"

    @pytest.mark.proof("skill_init", "PROOF-39", "RULE-37")
    def test_skill_shows_no_detection_all_unselected(self):
        """SKILL.md must show a no-detection example with all [ ] unselected."""
        content = _read('init')
        # Must have a "no detection" section
        assert re.search(r'(?i)no test framework.*detected|no framework.*detected', content), \
            "init SKILL.md missing no-detection scenario"
        # In the no-detection block, must show [ ] for framework and no [x]
        lines = content.split('\n')
        found_no_detect = False
        in_no_detect_section = False
        for i, line in enumerate(lines):
            if re.search(r'(?i)no test framework.*detected|no framework.*detected', line):
                in_no_detect_section = True
            if in_no_detect_section and '[ ] <framework>' in line:
                # Verify no [x] in nearby context
                context = '\n'.join(lines[max(0, i-2):i+8])
                if '[x]' not in context:
                    found_no_detect = True
                    break
        assert found_no_detect, \
            "init SKILL.md missing no-detection example with all [ ] unselected"

    # ── RULE-38 through RULE-40: MCP server configuration ────────────

    @pytest.mark.proof("skill_init", "PROOF-40", "RULE-38")
    def test_mcp_server_bundled_in_plugin_manifest(self):
        """Plugin manifest declares the purlin MCP server; init does not write a project entry."""
        manifest_path = os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json')
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert 'purlin' in manifest.get('mcpServers', {}), \
            ".claude-plugin/plugin.json missing 'purlin' entry under mcpServers"

        content = _read('init')
        assert re.search(r'(?i)do not create a `?purlin`? entry', content), \
            "init SKILL.md must forbid creating a purlin entry in the project's .mcp.json"
        assert 'Resolve `${CLAUDE_PLUGIN_ROOT}` to its absolute path at init time' not in content, \
            "init SKILL.md still instructs init-time path resolution (version-pins the MCP server)"

    @pytest.mark.proof("skill_init", "PROOF-41", "RULE-39")
    def test_bundled_mcp_server_uses_plugin_root_variable(self):
        """Bundled MCP entry uses python3 with ${CLAUDE_PLUGIN_ROOT} so the path tracks updates."""
        manifest_path = os.path.join(PROJECT_ROOT, '.claude-plugin', 'plugin.json')
        with open(manifest_path) as f:
            manifest = json.load(f)
        entry = manifest['mcpServers']['purlin']
        assert entry['command'] == 'python3', \
            f"Expected python3 command in bundled MCP entry, got {entry.get('command')}"
        assert '${CLAUDE_PLUGIN_ROOT}/scripts/mcp/purlin_server.py' in entry.get('args', []), \
            f"Expected ${{CLAUDE_PLUGIN_ROOT}}/scripts/mcp/purlin_server.py in args, got {entry.get('args')}"

    @pytest.mark.proof("skill_init", "PROOF-42", "RULE-40")
    def test_documents_legacy_mcp_json_migration(self):
        """SKILL.md must document removing the legacy purlin entry, preserving other servers."""
        content = _read('init')
        assert re.search(r'(?i)remove the `?purlin`? (key|entry)', content), \
            "init SKILL.md missing removal of the legacy purlin entry from .mcp.json"
        assert re.search(r'(?i)preserve all other server entries', content), \
            "init SKILL.md missing 'preserve all other server entries' guard"
        assert '/reload-plugins' in content, \
            "init SKILL.md must tell the user to run /reload-plugins after migration"

    # ── RULE-41 through RULE-46: digest / pre-commit hook ────────────







    @pytest.mark.proof("skill_init", "PROOF-50", "RULE-48")
    def test_selection_list_built_from_registry_not_hardcoded(self):
        """SKILL.md must build the framework list from the registry, not hardcode it."""
        content = _read('init')
        # Sources the list dynamically from the registry...
        assert re.search(r'(?i)build the (?:list|framework selection list) dynamically from `?references/supported_frameworks\.md', content), \
            "init SKILL.md must build the selection list dynamically from supported_frameworks.md"
        # ...and explicitly forbids hardcoding framework names.
        assert re.search(r'(?i)do NOT hardcode framework names', content), \
            "init SKILL.md must state framework names are not hardcoded"

    @pytest.mark.proof("skill_init", "PROOF-51", "RULE-48", tier="integration")
    def test_registry_covers_every_shipped_plugin(self):
        """Every plugin shipped in scripts/proof/ is registered, and every
        scripts/proof/ path the registry names exists — so the registry-built
        selection list covers exactly the shipped frameworks."""
        proof_dir = os.path.join(PROJECT_ROOT, 'scripts', 'proof')
        registry = _read_ref('supported_frameworks.md')

        shipped = sorted(
            f for f in os.listdir(proof_dir)
            if os.path.isfile(os.path.join(proof_dir, f))
        )
        assert shipped, "no proof plugins found in scripts/proof/"

        # The registry names plugins as `scripts/proof/<file>` paths. Both
        # directions check against THIS set (not a loose substring) so the
        # invariant is genuinely bidirectional.
        referenced = set(re.findall(r'scripts/proof/([A-Za-z0-9_]+\.[A-Za-z0-9]+)', registry))
        assert referenced, "registry names no scripts/proof/ plugin paths"

        # Backward: every shipped plugin is referenced as a scripts/proof/ path,
        # so the registry-built selection list cannot omit a shipped framework.
        unregistered = [f for f in shipped if f not in referenced]
        assert not unregistered, (
            f"shipped plugins missing a scripts/proof/<file> reference in "
            f"references/supported_frameworks.md (init would not present them): {unregistered}"
        )

        # Forward: every referenced path exists on disk (registry names no ghosts).
        missing = sorted(p for p in referenced if not os.path.isfile(os.path.join(proof_dir, p)))
        assert not missing, f"registry references nonexistent plugin files: {missing}"

        # The newly shipped xUnit plugin specifically must be covered.
        assert 'xunit_purlin.cs' in shipped and 'xunit_purlin.cs' in referenced, \
            "xUnit plugin must be shipped and registered (scripts/proof/xunit_purlin.cs) so init presents it"


# ── skill_rename ──────────────────────────────────────────────────────

class TestSkillRename:

    @pytest.mark.proof("skill_rename", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('rename')
        assert '---' in content, "rename SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'rename')

    @pytest.mark.proof("skill_rename", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('rename')
        assert '## Usage' in content, "rename SKILL.md must have a ## Usage section"
        _assert_usage(content, 'rename')

    @pytest.mark.proof("skill_rename", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('rename')
        assert 'name:' in content, "rename SKILL.md must have a name: field"
        _assert_name_matches(content, 'rename')

    @pytest.mark.proof("skill_rename", "PROOF-4", "RULE-4")
    def test_rename_covers_the_quality_caches(self):
        """RULE-4: a rename that skips the caches orphans every assessment.

        Both caches key on feature name. Renaming skill_unit_test to skill_test
        left six graded descriptions stranded under the old key, and the feature
        dropped to `unmeasured` on both gauges despite having been fully graded
        moments earlier. The skill's documented surface did not mention them.
        """
        content = _read('rename')

        for cache in ('audit_cache.json', 'design_cache.json'):
            assert cache in content, \
                f"rename SKILL.md never mentions {cache}, so a rename orphans its entries"

        # Named in both the what-it-renames list and the execute steps, so an
        # agent reading either half sees it.
        listing, _, steps = content.partition('## Steps')
        assert 'audit_cache.json' in listing and 'design_cache.json' in listing, \
            "the caches must appear in the numbered what-it-renames list"
        assert 'audit_cache.json' in steps and 'design_cache.json' in steps, \
            "the caches must appear in the execute steps, not only the summary list"

        # The `feature` field is what moves, and cached_at must not be re-stamped:
        # re-stamping would reset the 24h staleness check on untouched results.
        assert re.search(r'`?"?feature"?`?', steps), \
            "the steps must name the `feature` field as what gets rewritten"
        assert 'cached_at' in content, \
            "the skill must address cached_at when repointing cache entries"
        assert re.search(r'(?i)(do not|never|forbid).{0,40}re-?stamp', content), \
            "the skill must forbid re-stamping cached_at during a rename"


# ── skill_spec ────────────────────────────────────────────────────────

class TestSkillSpec:

    @pytest.mark.proof("skill_spec", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('spec')
        assert '---' in content, "spec SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'spec')

    @pytest.mark.proof("skill_spec", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('spec')
        assert '## Usage' in content, "spec SKILL.md must have a ## Usage section"
        _assert_usage(content, 'spec')

    @pytest.mark.proof("skill_spec", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('spec')
        assert 'name:' in content, "spec SKILL.md must have a name: field"
        _assert_name_matches(content, 'spec')

    @pytest.mark.proof("skill_spec", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        content = _read('spec')
        assert re.search(r'(?i)(git commit|commit the|create.*commit|commit.*change)', content), \
            "spec skill missing positive commit instruction"
        _assert_commit_instructions(content, 'spec')

    @pytest.mark.proof("skill_spec", "PROOF-5", "RULE-5")
    def test_has_delta_report_structure(self):
        content = _read('spec')
        for keyword in ('KEEPING', 'ADDING', 'UPDATING', 'REMOVING'):
            assert keyword in content, \
                f"spec skill missing '{keyword}' in delta report structure"

    @pytest.mark.proof("skill_spec", "PROOF-6", "RULE-6")
    def test_has_tier_review(self):
        content = _read('spec')
        assert re.search(r'(?i)(tier\s+(assign|review|tag)|review.*tier|assign.*tier)', content), \
            "spec skill missing tier review step/instruction"
        assert re.search(r'@integration|@e2e|unit.*tier|tier.*unit', content), \
            "spec skill missing tier tag references (@integration/@e2e/unit)"

    @pytest.mark.proof("skill_spec", "PROOF-9", "RULE-8")
    def test_validate_e2e_observable_flow(self):
        content = _read('spec')
        # Validate Before Commit must check @e2e proofs are observable flows
        validate = content.split('### Validate Before Commit', 1)
        assert len(validate) == 2, "spec skill missing 'Validate Before Commit' section"
        section = validate[1].split('### Commit', 1)[0]
        assert re.search(r'@e2e.*observable flow', section), \
            "spec skill Validate Before Commit missing @e2e observable-flow check"
        assert re.search(r'(?i)does not name a source file or internal function', section), \
            "spec skill Validate Before Commit missing source-file/internal-function ban for @e2e proofs"
        assert 'E2E proof descriptions' in section, \
            "spec skill Validate Before Commit missing pointer to quality guide 'E2E proof descriptions'"

    @pytest.mark.proof("skill_spec", "PROOF-7", "RULE-7")
    def test_has_exit_criteria(self):
        content = _read('spec')
        assert '## Exit Criteria' in content, \
            "spec skill missing '## Exit Criteria' section"
        # Must require spec committed
        assert re.search(r'(?i)spec.*committed|committed.*spec', content), \
            "spec exit criteria missing spec committed requirement"
        # Must require no uncommitted spec files
        assert re.search(r'(?i)uncommitted spec files', content), \
            "spec exit criteria missing uncommitted spec files check"

    @pytest.mark.proof("skill_spec", "PROOF-10", "RULE-9")
    def test_points_at_proof_design_criteria(self):
        """purlin:spec is the skill a user reaches for when they want the quality number
        to go up, so it must point at the Design criteria and say what prose cannot move."""
        content = _read('spec')
        assert 'audit_criteria.md' in content, \
            "spec SKILL.md must point at references/audit_criteria.md"
        assert re.search(r'(Pass D|PROVABLE)', content), \
            "spec SKILL.md must name Pass D or the Design levels"
        assert 'HOLLOW' in content and 'EXCLUDED' in content, \
            "spec SKILL.md must state that HOLLOW and EXCLUDED are not moved by spec edits"

    @pytest.mark.proof("skill_spec", "PROOF-11", "RULE-10")
    def test_exit_criteria_report_design_and_next_step(self):
        content = _read('spec')
        exit_section = content.split('## Exit Criteria', 1)
        assert len(exit_section) == 2, "spec SKILL.md has no Exit Criteria section"
        body = exit_section[1]

        assert '--check-proof-design' in body, \
            "exit criteria must grade the proof descriptions just written"
        assert re.search(r'(?i)advisory', body), \
            "the Design report must be advisory, never blocking"
        assert 'purlin:build' in body and 'purlin:test' in body, \
            "exit criteria must print the next-step directive for the current state"


# ── skill_spec_from_code ──────────────────────────────────────────────

class TestSkillSpecFromCode:

    @pytest.mark.proof("skill_spec_from_code", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('spec-from-code')
        assert '---' in content, "spec-from-code SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'spec-from-code')

    @pytest.mark.proof("skill_spec_from_code", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('spec-from-code')
        assert '## Usage' in content, "spec-from-code SKILL.md must have a ## Usage section"
        _assert_usage(content, 'spec-from-code')

    @pytest.mark.proof("skill_spec_from_code", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('spec-from-code')
        assert 'name:' in content, "spec-from-code SKILL.md must have a name: field"
        _assert_name_matches(content, 'spec-from-code')

    @pytest.mark.proof("skill_spec_from_code", "PROOF-4", "RULE-4")
    def test_has_tier_review(self):
        content = _read('spec-from-code')
        assert re.search(r'(?i)(tier\s+(assign|review|tag)|review.*tier|assign.*tier)', content), \
            "spec-from-code skill missing tier review step/instruction"
        assert re.search(r'@integration|@e2e|unit.*tier|tier.*unit', content), \
            "spec-from-code skill missing tier tag references (@integration/@e2e/unit)"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-5", "RULE-9")
    def test_phase4_cleanup_offer_and_overwrite_in_place(self):
        content = _read('spec-from-code')
        # Phase 4 must offer to remove features/ after migration
        assert re.search(r'(?i)(remove|delete).*features/', content), \
            "spec-from-code skill missing offer to remove features/ in Phase 4"
        # Non-compliant specs in specs/ are overwritten in place — NOT removed
        assert re.search(r'(?i)overwritten in place', content), \
            "spec-from-code skill missing 'overwritten in place' language for specs/"
        # The spec must NOT say to remove non-compliant specs from specs/
        # (they are overwritten, not deleted separately)
        assert 'features/' in content and 'overwritten in place' in content, \
            "spec-from-code skill must document features/ removal AND specs/ overwrite-in-place paths"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-34", "RULE-24")
    def test_draft_and_evaluate_with_rebuild_test(self):
        content = _read('spec-from-code')
        assert re.search(r'(?i)draft and evaluate', content), \
            "spec-from-code skill missing 'Draft and evaluate' step"
        assert re.search(r'(?i)rebuild test', content), \
            "spec-from-code skill missing 'rebuild test' filter"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-39", "RULE-27")
    def test_discoveries_figma_preserved_as_visual_reference(self):
        content = _read('spec-from-code')
        assert 'Visual-Reference' in content, \
            "spec-from-code skill missing Visual-Reference metadata"
        assert 'Figma' in content, \
            "spec-from-code skill missing Figma reference"
        assert '.discoveries.md' in content, \
            "spec-from-code skill missing .discoveries.md reference"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-40", "RULE-28")
    def test_quality_guide_coverage_dimensions_not_fixed_count(self):
        content = _read_ref('spec_quality_guide.md')
        assert re.search(r'(?i)coverage dimensions', content), \
            "spec_quality_guide.md missing 'Coverage dimensions' section"
        assert not re.search(r'5.10 rules per feature', content), \
            "spec_quality_guide.md still contains fixed '5-10 rules per feature' target"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-41", "RULE-29")
    def test_no_single_spec_category_folders(self):
        content = _read('spec-from-code')
        assert re.search(r'(?i)single-feature category check', content), \
            "spec-from-code skill missing Phase 2 single-feature category check"
        assert re.search(r'(?i)merge the feature into the closest related category', content), \
            "spec-from-code skill missing merge-into-related-category instruction"
        assert re.search(r'(?i)`specs/<name>\.md`.*do NOT create a folder', content), \
            "spec-from-code skill missing root-placement (no folder) instruction"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-42", "RULE-30")
    def test_tier_review_inverse_check(self):
        content = _read('spec-from-code')
        # Step 7 tier review must include the inverse check on @e2e descriptions
        assert re.search(r'(?i)inverse check', content), \
            "spec-from-code skill missing the tier-review inverse check"
        assert re.search(r'observable flow', content), \
            "spec-from-code skill inverse check missing 'observable flow' language"
        assert re.search(r'arrange → act → observe', content), \
            "spec-from-code skill inverse check missing arrange → act → observe flow shape"
        assert re.search(r'(?i)must not name a source file or internal function', content), \
            "spec-from-code skill inverse check missing source-file/internal-function ban"
        assert re.search(r'spec_quality_guide\.md.*E2E proof descriptions', content), \
            "spec-from-code skill inverse check missing pointer to quality guide 'E2E proof descriptions'"
        # Mis-tagged proofs are rewritten or retagged
        assert re.search(r'(?i)retag', content), \
            "spec-from-code skill inverse check missing rewrite-or-retag instruction"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-43", "RULE-31")
    def test_step11_proof_coupling_check(self):
        content = _read('spec-from-code')
        # The check must live inside the step 11 "Validate generated specs" block
        m = re.search(r'11\.\s+\*\*Validate generated specs(.*?)(?=\n12\.)', content, re.DOTALL)
        assert m, "spec-from-code skill missing step 11 'Validate generated specs'"
        step11 = m.group(1)
        assert re.search(r'(?i)proof implementation-coupling', step11), \
            "spec-from-code skill step 11 missing proof implementation-coupling check"
        assert re.search(r'(?i)names a source file or an internal function', step11), \
            "spec-from-code step 11 coupling check must reject proofs naming source files or internal symbols"
        assert re.search(r'audit_criteria\.md.*E2E Proof Tier Integrity', step11), \
            "spec-from-code step 11 coupling check missing pointer to audit criteria 'E2E Proof Tier Integrity'"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-44", "RULE-32")
    def test_e2e_runner_reality_check(self):
        content = _read('spec-from-code')
        # Phase 1 must record the e2e_capable flag
        assert 'e2e_capable' in content, \
            "spec-from-code skill missing Phase 1 e2e_capable detection"
        # The warning must appear in BOTH the step 12 review block and the Phase 4 summary
        warning_re = r'(?i)proofs tagged @e2e but no e2e runner detected'
        parts = re.split(r'^## Phase 4', content, flags=re.MULTILINE)
        assert len(parts) == 2, "spec-from-code skill missing '## Phase 4' section"
        assert re.search(warning_re, parts[0]), \
            "spec-from-code skill missing the @e2e/no-runner warning in the Phase 3 review block"
        assert re.search(warning_re, parts[1]), \
            "spec-from-code skill missing the @e2e/no-runner warning in the Phase 4 summary"
        # Warning must be tool-agnostic and point at the frameworks registry
        assert re.search(r'(?i)supported_frameworks\.md', content), \
            "spec-from-code @e2e warning missing pointer to supported_frameworks.md"

    @pytest.mark.proof("skill_spec_from_code", "PROOF-45", "RULE-30")
    def test_quality_guide_has_e2e_flow_section(self):
        content = _read_ref('spec_quality_guide.md')
        assert 'E2E proof descriptions' in content, \
            "spec_quality_guide.md missing 'E2E proof descriptions' section (the canonical " \
            "guidance the spec-from-code inverse check points to)"
        assert re.search(r'arrange → act → observe', content), \
            "spec_quality_guide.md E2E section missing arrange → act → observe flow shape"
        assert re.search(r'(?i)must not name source files or internal functions', content), \
            "spec_quality_guide.md E2E section missing the source-file/internal-function ban"


# ── skill_status ──────────────────────────────────────────────────────

class TestSkillStatus:

    @pytest.mark.proof("skill_status", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('status')
        assert '---' in content, "status SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'status')

    @pytest.mark.proof("skill_status", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('status')
        assert '## Usage' in content, "status SKILL.md must have a ## Usage section"
        _assert_usage(content, 'status')

    @pytest.mark.proof("skill_status", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('status')
        assert 'name:' in content, "status SKILL.md must have a name: field"
        _assert_name_matches(content, 'status')

    @pytest.mark.proof("skill_status", "PROOF-4", "RULE-4")
    def test_references_sync_status_mcp_tool(self):
        content = _read('status')
        assert 'sync_status' in content, \
            "status skill doesn't reference MCP tool 'sync_status'"



    @pytest.mark.proof("skill_status", "PROOF-5", "RULE-5")
    def test_documented_sort_order_matches_implementation(self):
        """The skill claimed 'PARTIAL first, then PASSING, then VERIFIED' — omitting
        FAILING and UNTESTED, and in a spec-only project every row is the status the
        skill never mentioned."""
        content = _read('status')
        for status in ('FAILING', 'PARTIAL', 'PASSING', 'VERIFIED', 'UNTESTED'):
            assert status in content, f"status skill must document {status} in the sort order"

        # The documented order must match _build_summary_table's priority map.
        import purlin_server, inspect
        src = inspect.getsource(purlin_server._build_summary_table)
        impl = re.search(r'priority = \{([^}]*)\}', src)
        assert impl, "could not read the priority map from _build_summary_table"
        impl_order = [m2.group(1) for m2 in
                      re.finditer(r'"(\w+)":\s*\d', impl.group(1))]
        doc_order = sorted(impl_order, key=lambda st: content.index(st))
        assert doc_order == impl_order, (
            f"documented order {doc_order} != implementation order {impl_order}")

# ── skill_test ───────────────────────────────────────────────────

    @pytest.mark.proof("skill_status", "PROOF-6", "RULE-6")
    def test_feature_table_has_both_gauge_columns(self):
        """RULE-6: the documented table shows both gauges per feature.

        It was ruled for three columns and showed neither gauge, so an agent
        reading purlin:status could not see that a VERIFIED feature rested on
        unfalsifiable descriptions.
        """
        content = _read('status')
        assert 'three columns' not in content, \
            "the skill still claims a three-column table"
        block = content.split('## Step 2', 1)[1].split('```', 2)[1]
        header = block.strip().splitlines()[0]
        for col in ('Feature', 'Coverage', 'Status', 'Design', 'Integrity'):
            assert col in header, f"table header is missing {col}: {header!r}"
        rows = [l for l in block.strip().splitlines()[2:] if l.strip()]
        assert any('%' in l.split('Status')[-1] for l in rows), \
            "no sample row carries a gauge percentage"
        # Each gauge's unscorable word, in its own vocabulary.
        assert 'structural' in block and 'excluded' in block, \
            "the sample rows must show both unscorable tokens"
        assert 'not audited' in block, "the sample rows must show the unmeasured token"

    @pytest.mark.proof("skill_status", "PROOF-7", "RULE-7")
    def test_prints_the_servers_summary_line_not_a_substitute(self):
        """RULE-7: a reconstructed status-count line cannot carry a gauge."""
        content = _read('status')
        assert not re.search(r'Summary:\s*\d+\s*features\s*\|', content), (
            "the skill still templates its own 'Summary: N features |' line, which "
            "structurally cannot carry either gauge")
        assert re.search(r'(?i)exactly as .{0,20}sync_status.{0,20}returned', content), \
            "the skill must instruct printing sync_status's summary line verbatim"
        # And the sample must be the real thing, with both gauges and denominators.
        assert 'Proof Design:' in content and 'Proof Integrity:' in content, \
            "the documented summary line must show both gauges"
        assert 'measured' in content, \
            "the documented summary line must show each gauge's denominator"

    @pytest.mark.proof("skill_status", "PROOF-8", "RULE-8")
    def test_documents_gauge_remediation_and_ordering(self):
        """RULE-8: each finding routes to the artifact that can actually fix it."""
        content = _read('status')
        section = content.split('Gauge Recommendations', 1)
        assert len(section) == 2, "no gauge recommendation section"
        body = section[1]

        assert re.search(r'LOOSE.*purlin:spec|purlin:spec.*LOOSE', body, re.S), \
            "a Design finding must route to purlin:spec"
        assert re.search(r'(WEAK|HOLLOW).*purlin:build|purlin:build.*(WEAK|HOLLOW)', body, re.S), \
            "an Integrity finding must route to purlin:build"
        assert 'purlin:audit' in body, "an unmeasured gauge must route to purlin:audit"

        # Design before Integrity, with the reason stated rather than asserted.
        assert body.index('purlin:spec') < body.index('purlin:build'), \
            "Design remediation must be documented before Integrity"
        assert re.search(r'(?i)design before integrity', body), \
            "the ordering must be stated explicitly"
        assert re.search(r'(?i)compare a test against its proof description', body), \
            "the reason for the ordering must be given, not just the order"




class TestSkillTest:

    @pytest.mark.proof("skill_test", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('test')
        assert '---' in content, "test SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'test')

    @pytest.mark.proof("skill_test", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('test')
        assert '## Usage' in content, "test SKILL.md must have a ## Usage section"
        _assert_usage(content, 'test')

    @pytest.mark.proof("skill_test", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('test')
        assert 'name:' in content, "test SKILL.md must have a name: field"
        _assert_name_matches(content, 'test')

    @pytest.mark.proof("skill_test", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        content = _read('test')
        assert re.search(r'(?i)(git commit|commit the|create.*commit|commit.*change)', content), \
            "test skill missing positive commit instruction"
        _assert_commit_instructions(content, 'test')

    @pytest.mark.proof("skill_test", "PROOF-5", "RULE-5")
    def test_requires_sync_status_not_optional(self):
        content = _read('test')
        assert 'sync_status' in content, \
            "test skill doesn't reference sync_status"
        assert 'not optional' in content, \
            "test skill doesn't state sync_status is not optional"

    @pytest.mark.proof("skill_test", "PROOF-6", "RULE-6")
    def test_zero_tests_is_not_a_plugin_failure(self):
        """"No tests collected" and "the plugin failed to emit" are different, and
        conflating them sent users to re-scaffold working infrastructure."""
        content = _read('test')
        fresh = content.split('Proof File Freshness Check', 1)
        assert len(fresh) == 2, "test SKILL.md missing the freshness check"
        section = fresh[1].split('## Step 3', 1)[0]

        assert re.search(r'(?i)no tests (found|were collected|collected)', section), \
            "the freshness check must handle the zero-tests case first"
        assert re.search(r'(?i)plugin is (fine|working)', section), \
            "zero tests means the plugin is fine — say so"
        assert 'purlin:build' in section, \
            "zero tests should route to purlin:build, not to re-scaffolding"

        # The re-scaffold advice must be confined to the real-failure branch.
        idx_ok = section.lower().find('plugin is fine')
        idx_force = section.find('purlin:init --force')
        assert idx_force > idx_ok, \
            "purlin:init --force must only appear in the branch where tests actually ran"

# ── skill_verify ──────────────────────────────────────────────────────



class TestSkillVerify:

    @pytest.mark.proof("skill_verify", "PROOF-9", "RULE-9", tier="integration")
    def test_platform_partial_receipt_records_what_it_could_not_verify(self):
        """RULE-9: an absent runner must not make a receipt unobtainable, and a
        receipt issued without one must not claim to be verified everywhere."""
        root = os.path.join(os.path.dirname(__file__), '..')
        issuer = os.path.join(root, 'dev', 'issue_receipts.py')
        assert os.path.isfile(issuer), "receipt issuer missing"

        tmp = tempfile.mkdtemp()
        try:
            spec_dir = os.path.join(tmp, 'specs', 'audit')
            os.makedirs(spec_dir)
            os.makedirs(os.path.join(tmp, '.purlin'))
            with open(os.path.join(spec_dir, 'locking.md'), 'w') as f:
                f.write('# Feature: locking\n\n## What it does\nLocks.\n\n'
                        '## Rules\n- RULE-1: POSIX\n- RULE-2: Windows\n\n'
                        '## Proof\n'
                        '- PROOF-1 (RULE-1): fcntl locks @unit\n'
                        '- PROOF-2 (RULE-2): msvcrt locks on a real windows runner @windows\n')
            with open(os.path.join(spec_dir, 'plain.md'), 'w') as f:
                f.write('# Feature: plain\n\n## What it does\nP.\n\n'
                        '## Rules\n- RULE-1: A\n\n'
                        '## Proof\n- PROOF-1 (RULE-1): a @unit\n')
            for feat in ('locking', 'plain'):
                with open(os.path.join(spec_dir, f'{feat}.proofs-unit.json'), 'w') as f:
                    json.dump({"tier": "unit", "proofs": [
                        {"feature": feat, "id": "PROOF-1", "rule": "RULE-1",
                         "test_file": "dev/t.py", "test_name": "t",
                         "status": "pass", "tier": "unit"}]}, f)

            sys.path.insert(0, os.path.join(root, 'scripts', 'mcp'))
            import purlin_server as ps
            features = ps._scan_specs(tmp)
            all_proofs = ps._read_proofs(tmp)

            awaiting = ps._awaiting_runner('locking', features['locking'], all_proofs)
            assert awaiting == [('PROOF-2', 'windows')], awaiting
            assert ps._awaiting_runner('plain', features['plain'], all_proofs) == []

            # The issuer writes exactly what RULE-9 requires.
            src = open(issuer).read()
            assert "receipt['awaiting_runner']" in src, \
                "the issuer must record the gap on the receipt"
            assert 'if awaiting:' in src, \
                "the key must be omitted when nothing is awaiting"

            # And the feature still qualifies: its coverage excludes the rule
            # whose only proof is runner-gated, so it is PASSING, not PARTIAL.
            rule_entries, _ = ps._build_coverage_rules(
                'locking', features['locking'], features, {})
            active, aw, gated = ps._active_rule_entries(
                'locking', features['locking'], rule_entries, all_proofs)
            assert len(active) == 1 and gated == 1, (active, gated)
            proof_by_rule = ps._build_proof_lookup('locking', rule_entries, all_proofs)
            proved = sum(1 for k, _, _ in active
                         if proof_by_rule.get(k, {}).get('status') == 'pass')
            assert proved == len(active), \
                "an absent runner must leave the feature receipt-eligible"
        finally:
            shutil.rmtree(tmp)

    @pytest.mark.proof("skill_verify", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('verify')
        assert '---' in content, "verify SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'verify')

    @pytest.mark.proof("skill_verify", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('verify')
        assert '## Usage' in content, "verify SKILL.md must have a ## Usage section"
        _assert_usage(content, 'verify')

    @pytest.mark.proof("skill_verify", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('verify')
        assert 'name:' in content, "verify SKILL.md must have a name: field"
        _assert_name_matches(content, 'verify')

    @pytest.mark.proof("skill_verify", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        content = _read('verify')
        assert re.search(r'(?i)(git commit|commit the|create.*commit|commit.*change)', content), \
            "verify skill missing positive commit instruction"
        _assert_commit_instructions(content, 'verify')

    @pytest.mark.proof("skill_verify", "PROOF-5", "RULE-5")
    def test_verify_prohibits_modifying_files(self):
        content = _read('verify')
        assert 'NEVER modify' in content, \
            "verify skill missing 'NEVER modify' read-only constraint"

    @pytest.mark.proof("skill_verify", "PROOF-6", "RULE-6")
    def test_step_4e_documents_independent_audit(self):
        content = _read('verify')
        # Step 4e must document the independent audit that reports final integrity score
        assert re.search(r'Step 4e', content), \
            "verify skill missing Step 4e heading"
        assert re.search(r'(?i)independent', content), \
            "verify skill missing 'independent' audit language in Step 4e"
        assert re.search(r'(?i)integrity', content), \
            "verify skill missing integrity score reference in Step 4e"
        # Must reference the auditor agent (purlin-auditor)
        assert 'purlin-auditor' in content, \
            "verify skill Step 4e missing purlin-auditor reference"

    @pytest.mark.proof("skill_verify", "PROOF-7", "RULE-7")
    def test_untested_case_is_handled(self):
        """Step 2 enumerated PASSING / PARTIAL / FAILING only. A spec-first project
        is entirely UNTESTED, so every feature fell outside all defined cases."""
        content = _read('verify')
        assert 'UNTESTED' in content, "verify SKILL.md must handle the UNTESTED case"
        step2 = content.split('UNTESTED', 1)[1][:900]
        assert re.search(r'(?i)no\s+receipt', step2), \
            "UNTESTED must issue no receipt"
        assert re.search(r'(?i)not\s+a\s+failure', step2), \
            "UNTESTED is not a failure and must not be reported as one"
        assert 'purlin:build' in step2 and 'purlin:test' in step2, \
            "the next step must branch on whether the scope files exist"
        assert '--design' in step2, \
            "UNTESTED features should be pointed at the gauge that is measurable"

    @pytest.mark.proof("skill_verify", "PROOF-8", "RULE-8")
    def test_the_two_audits_are_distinguished(self):
        """build and verify both spawn an auditor. Undifferentiated, that is a
        duplicated project-wide audit for one number."""
        verify = _read('verify')
        build = _read('build')
        assert re.search(r'(?i)authoritative', verify), \
            "verify's audit must be identified as the authoritative one"
        assert re.search(r'(?i)project-wide', verify), \
            "verify's audit must be described as project-wide"
        assert re.search(r'(?i)feature-scoped', build), \
            "build's audit must be described as feature-scoped"
        assert re.search(r'(?i)advisory', build), \
            "build's audit must be described as advisory"


class TestSkillTestRemotePath:
    """skill_test RULE-7 through RULE-11: tier classification and the remote path.

    A @windows proof that had never run reported nothing: the rule read PASS
    off a local proof while nothing had proved the platform. Phase 4 made the
    gap visible; these rules are the skill that closes it.
    """

    @pytest.mark.proof("skill_test", "PROOF-7", "RULE-7")
    def test_tiers_are_classified_before_anything_runs(self):
        content = _read('test')
        assert 'Step 1.5' in content, "no tier-classification step"
        i_classify = content.index('Step 1.5')
        i_run = content.index('## Step 2')
        assert i_classify < i_run, (
            "classification must come before the step that runs tests; naming "
            "what cannot run here after running is not a warning")

        section = content[i_classify:i_run]
        assert 'locally-runnable' in section and 'runner-gated' in section, (
            "the step must name both groups")
        assert 'windows' in section, "the runner-gated tier must be named"
        assert 'schema_proof_format' in section, (
            "the step must cite the closed tier set that defines runner-gated, "
            "so adding a tier has one place to change")
        assert re.search(r'(?i)never.*substitut|not a windows proof', section), (
            "the step must forbid substituting a local approximation")
        assert re.search(r'(?i)never block|does not block|warn, never block',
                         section), (
            "an absent runner warns; the step must say it does not block")

    @pytest.mark.proof("skill_test", "PROOF-8", "RULE-8")
    def test_the_remote_path_is_four_ordered_operations_and_says_why_it_is_here(self):
        content = _read('test')
        assert 'Step 2b' in content, "no remote-path step"
        section = content[content.index('Step 2b'):content.index('### Proof File Freshness')]

        order = []
        for label, pattern in (
                ('push', r'(?i)push the current branch'),
                ('dispatch', r'(?i)dispatch the workflow'),
                ('await', r'(?i)await it'),
                ('pull', r'(?i)pull the proof commits')):
            m = re.search(pattern, section)
            assert m, f"the remote path is missing the {label} operation"
            order.append((m.start(), label))
        assert order == sorted(order), (
            f"the four operations must appear in order, got "
            f"{[l for _, l in order]}")

        # Why here and not in verify. The reason, not just the placement.
        assert re.search(r'(?i)read-only', content), (
            "the skill must name verify's read-only contract as the reason")
        assert 'purlin:verify' in content

        # And verify must not have grown a write path of its own.
        verify = _read('verify')
        for forbidden in ('git push', 'gh workflow run', 'git pull'):
            assert forbidden not in verify, (
                f"skills/verify/SKILL.md gained {forbidden!r}; verify is a "
                "read-only gate and must inherit the remote path by delegation")

    @pytest.mark.proof("skill_test", "PROOF-9", "RULE-9")
    def test_remotely_proved_is_reported_distinctly_and_sourced_from_the_commit(self):
        content = _read('test')
        step3 = content[content.index('## Step 3'):content.index('## Step 4')]
        assert re.search(r'(?i)locally-proved', step3) and \
               re.search(r'(?i)remotely-proved', step3), (
            "Step 3 must distinguish the two kinds of pass by name")
        assert 'proved remotely' in step3, (
            "the sample output must mark a remotely-proved tier")
        assert 'Purlin-Runner' in step3, (
            "the runner identity must be sourced from the commit trailer")
        assert re.search(r'(?i)not\s+from\s+the\s+proof\s+entry'
                         r'|only\s+the\s+commit\s+says\s+where', step3, re.S), (
            "Step 3 must say the proof entry does not record where it ran")

        fresh = content[content.index('Proof File Freshness'):content.index('## Step 3')]
        assert re.search(r'(?i)locally-runnable tiers only|does not apply', fresh), (
            "the freshness check must exclude pulled runner-gated proof files, "
            "whose mtime says when they were fetched")

    @pytest.mark.proof("skill_test", "PROOF-10", "RULE-10")
    def test_the_remote_loop_bound_is_three_and_matches_the_other_skills(self):
        content = _read('test')
        assert re.search(r'Bound the loop at 3 rounds', content), (
            "the remote loop must be bounded at a literal 3 rounds")
        # The three skills must not drift to different bounds.
        for skill in ('audit', 'verify'):
            other = _read(skill)
            assert re.search(r'3 rounds', other), (
                f"skills/{skill}/SKILL.md no longer says 3 rounds; the bound "
                "has drifted between skills")

    @pytest.mark.proof("skill_test", "PROOF-11", "RULE-11")
    def test_setup_is_offered_on_discovery_and_never_at_init(self):
        content = _read('test')
        section = content[content.index('Step 2b'):content.index('### Proof File Freshness')]
        assert re.search(r'(?i)no workflow is configured', section), (
            "the offer must be conditioned on discovering no workflow")
        assert 'references/remote_verification.md' in section, (
            "the offer must point at the template")
        assert re.search(r'(?i)only on a yes|never write a workflow file unasked',
                         section), (
            "writing a workflow changes what runs on every push; it needs consent")
        assert re.search(r'(?i)init is not the place', section), (
            "the skill must state that init is not where this happens")
        assert re.search(r'(?i)asks nothing about runners|has no answer yet',
                         section), (
            "and must give the reason, not just the rule")

        init = _read('init')
        assert 'remote_verification' in init, (
            "init must still write the config field, so a project has a default")
        assert not re.search(r'(?i)(scaffold|set up|configure).{0,40}'
                             r'(runner|remote verification workflow)', init), (
            "purlin:init must not have gained a remote-verification setup step")


class TestBuildDelegatesTestExecution:

    @pytest.mark.proof("skill_build", "PROOF-21", "RULE-14")
    def test_build_names_purlin_test_and_no_retired_name_survives(self):
        """The skill was renamed from purlin:unit-test and build's iteration
        loop kept pointing at the old name, directing the agent at a skill
        that does not exist."""
        content = _read('build')
        assert 'purlin:unit-test' not in content, (
            "skills/build/SKILL.md still names the retired purlin:unit-test")
        assert 'purlin:test' in content
        assert re.search(r'(?i)single owner of test execution', content), (
            "build must name purlin:test as the single owner of test execution")
        assert re.search(r'(?i)never invoke a test runner directly', content), (
            "build must forbid invoking a runner itself")

        # No bare runner invocation as an instruction. The prohibition itself
        # names them, so exclude the line that carries it.
        for line in content.splitlines():
            if 'never invoke a test runner directly' in line.lower():
                continue
            assert not re.search(r'^\s*(npx (jest|vitest)|pytest)\b', line), (
                f"build instructs a runner directly: {line!r}")


class TestRetiredVerifyFlagIsGone:

    @pytest.mark.proof("skill_verify", "PROOF-10", "RULE-10")
    def test_no_doc_names_the_retired_audit_flag(self):
        """`purlin:verify --audit` collided with the purlin:audit skill and was
        renamed to --recheck. Three references in docs/ survived the rename."""
        roots = [os.path.join(PROJECT_ROOT, d)
                 for d in ('skills', 'references', 'docs')]
        md_files = [os.path.join(PROJECT_ROOT, 'README.md')]
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                md_files.extend(os.path.join(dirpath, fn)
                                for fn in filenames if fn.endswith('.md'))

        offenders = []
        for path in md_files:
            if os.path.basename(path) == 'RELEASE_NOTES.md':
                continue
            text = open(path).read()
            for m in re.finditer(r'[^\w-]--audit\b(?!-)', text):
                # Attribute the flag: verify's flag is the retired one.
                window = text[max(0, m.start() - 120):m.end() + 60]
                if re.search(r'(?i)(verify|deploy gate|re-execution|clean-room)',
                             window):
                    offenders.append(
                        f"{os.path.relpath(path, PROJECT_ROOT)}: "
                        f"{window.strip()[:140]}")
        assert not offenders, (
            "the retired `purlin:verify --audit` flag survives in:\n  "
            + "\n  ".join(offenders))

        # The replacement must exist, so the scan cannot pass by the flag
        # having been deleted rather than renamed.
        verify = _read('verify')
        usage = verify[verify.index('## Usage'):verify.index('## Default Mode')]
        assert '--recheck' in usage, (
            "verify's Usage block must document --recheck")
