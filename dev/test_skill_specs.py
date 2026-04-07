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
    def test_independent_auditor_spawns_builder(self):
        content = _read('audit')
        assert re.search(r'(?i)(spawn|purlin-builder)', content), \
            "audit SKILL.md missing purlin-builder spawn protocol"
        assert re.search(r'(?i)(PROOF-ID|finding|fix)', content), \
            "audit SKILL.md missing three-part finding structure for builder"

    @pytest.mark.proof("skill_audit", "PROOF-6", "RULE-6", tier="e2e")
    def test_independent_auditor_re_audits_after_builder(self):
        content = _read('audit')
        assert re.search(r'(?i)(re-audit|re.audit|after the builder responds)', content), \
            "audit SKILL.md missing re-audit step after builder responds"

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
        assert re.search(r'(?i)(message the lead|lead.*not the builder)', content), \
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

    @pytest.mark.proof("skill_init", "PROOF-8", "RULE-8")
    def test_documents_required_directory_structure(self):
        content = _read('init')
        for directory in ('.purlin/', '.purlin/plugins/', 'specs/', 'specs/_anchors/'):
            assert directory in content, \
                f"init SKILL.md missing required directory '{directory}'"

    @pytest.mark.proof("skill_init", "PROOF-9", "RULE-9")
    def test_config_template_has_five_required_fields(self):
        config_path = os.path.join(PROJECT_ROOT, 'templates', 'config.json')
        with open(config_path) as f:
            config = json.load(f)
        for field in ('version', 'test_framework', 'spec_dir', 'pre_push', 'report'):
            assert field in config, \
                f"templates/config.json missing required field '{field}'"
        assert len(config) == 5, \
            f"templates/config.json should have exactly 5 fields, got {len(config)}: {list(config)}"

    @pytest.mark.proof("skill_init", "PROOF-10", "RULE-10")
    def test_config_version_matches_version_file(self):
        config_path = os.path.join(PROJECT_ROOT, 'templates', 'config.json')
        version_path = os.path.join(PROJECT_ROOT, 'VERSION')
        with open(config_path) as f:
            config = json.load(f)
        with open(version_path) as f:
            version = f.read().strip()
        assert config['version'] == version, \
            f"templates/config.json version '{config['version']}' != VERSION file '{version}'"

    @pytest.mark.proof("skill_init", "PROOF-11", "RULE-11")
    def test_config_template_default_values(self):
        config_path = os.path.join(PROJECT_ROOT, 'templates', 'config.json')
        with open(config_path) as f:
            config = json.load(f)
        assert config['test_framework'] == 'auto', \
            f"Default test_framework should be 'auto', got '{config['test_framework']}'"
        assert config['spec_dir'] == 'specs', \
            f"Default spec_dir should be 'specs', got '{config['spec_dir']}'"
        assert config['pre_push'] == 'warn', \
            f"Default pre_push should be 'warn', got '{config['pre_push']}'"
        assert config['report'] is True, \
            f"Default report should be true, got '{config['report']}'"

    @pytest.mark.proof("skill_init", "PROOF-12", "RULE-12")
    def test_documents_conftest_py_detects_pytest(self):
        content = _read('init')
        assert 'conftest.py' in content, \
            "init SKILL.md missing conftest.py detection indicator"
        assert re.search(r'conftest\.py.*pytest|pytest.*conftest\.py', content), \
            "init SKILL.md missing conftest.py -> pytest auto-detection mapping"

    @pytest.mark.proof("skill_init", "PROOF-13", "RULE-13")
    def test_documents_pyproject_toml_detects_pytest(self):
        ref = _read_ref('supported_frameworks.md')
        assert 'pyproject.toml' in ref, \
            "supported_frameworks.md missing pyproject.toml detection indicator"
        assert re.search(r'\[tool\.pytest\]', ref), \
            "supported_frameworks.md missing [tool.pytest] detection entry"

    @pytest.mark.proof("skill_init", "PROOF-14", "RULE-14")
    def test_documents_package_json_jest_detects_jest(self):
        content = _read('init')
        assert 'package.json' in content, \
            "init SKILL.md missing package.json detection indicator"
        assert re.search(r'package\.json.*jest|jest.*package\.json', content), \
            "init SKILL.md missing package.json jest -> jest detection mapping"

    @pytest.mark.proof("skill_init", "PROOF-15", "RULE-15")
    def test_documents_vitest_maps_to_jest_plugin(self):
        ref = _read_ref('supported_frameworks.md')
        assert 'vitest' in ref.lower(), \
            "supported_frameworks.md missing vitest framework reference"
        # Vitest row must reference jest_purlin.js as its plugin file
        assert re.search(r'[Vv]itest.*jest_purlin\.js', ref), \
            "supported_frameworks.md missing vitest -> jest_purlin.js mapping"

    @pytest.mark.proof("skill_init", "PROOF-16", "RULE-16")
    def test_documents_multi_framework_scaffolding(self):
        content = _read('init')
        # Must show the multi-detection display format
        assert re.search(r'pytest,jest|pytest.*jest', content), \
            "init SKILL.md missing pytest,jest combined config example"
        # Must document scaffolding ALL detected plugins
        assert re.search(r'(?i)scaffold.*both|both.*plugin|all.*plugin|all.*detected',
                         content), \
            "init SKILL.md missing documentation for scaffolding all detected plugins"

    @pytest.mark.proof("skill_init", "PROOF-17", "RULE-17")
    def test_documents_no_framework_asks_user_not_silent_shell(self):
        content = _read('init')
        # When no framework is detected, the skill must ask the user
        assert re.search(r'(?i)no test framework detected', content), \
            "init SKILL.md missing 'No test framework detected' user prompt"
        # Must present a menu of options to the user
        assert re.search(r'(?i)(which framework|which framework\(s\))', content), \
            "init SKILL.md missing user prompt asking which framework"
        # The skill must state it does NOT silently default to shell
        assert re.search(r'(?i)do not silently default', content), \
            "init SKILL.md missing 'do not silently default' guard"

    @pytest.mark.proof("skill_init", "PROOF-18", "RULE-18")
    def test_pytest_plugin_source_exists_and_is_copy_source(self):
        src = os.path.join(PROJECT_ROOT, 'scripts', 'proof', 'pytest_purlin.py')
        assert os.path.isfile(src), \
            "scripts/proof/pytest_purlin.py does not exist — cannot be scaffolded"
        ref = _read_ref('supported_frameworks.md')
        assert re.search(r'scripts/proof/pytest_purlin\.py', ref), \
            "supported_frameworks.md missing source path scripts/proof/pytest_purlin.py"

    @pytest.mark.proof("skill_init", "PROOF-19", "RULE-19")
    def test_jest_plugin_source_exists_and_is_copy_source(self):
        src = os.path.join(PROJECT_ROOT, 'scripts', 'proof', 'jest_purlin.js')
        assert os.path.isfile(src), \
            "scripts/proof/jest_purlin.js does not exist — cannot be scaffolded"
        ref = _read_ref('supported_frameworks.md')
        assert re.search(r'scripts/proof/jest_purlin\.js', ref), \
            "supported_frameworks.md missing source path scripts/proof/jest_purlin.js"

    @pytest.mark.proof("skill_init", "PROOF-20", "RULE-20")
    def test_shell_plugin_source_exists_and_is_copy_source(self):
        src = os.path.join(PROJECT_ROOT, 'scripts', 'proof', 'shell_purlin.sh')
        assert os.path.isfile(src), \
            "scripts/proof/shell_purlin.sh does not exist — cannot be scaffolded"
        ref = _read_ref('supported_frameworks.md')
        assert re.search(r'shell_purlin\.sh', ref), \
            "supported_frameworks.md missing source path shell_purlin.sh"

    @pytest.mark.proof("skill_init", "PROOF-21", "RULE-21", tier="e2e")
    def test_pytest_plugin_emits_valid_proofs_json(self, tmp_path):
        """Scaffold pytest plugin into a temp project and run it with a marker."""
        src = os.path.join(PROJECT_ROOT, 'scripts', 'proof', 'pytest_purlin.py')
        plugins_dir = tmp_path / '.purlin' / 'plugins'
        plugins_dir.mkdir(parents=True)
        shutil.copy(src, str(plugins_dir / 'pytest_purlin.py'))

        spec_dir = tmp_path / 'specs' / 'auth'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'login.md').write_text(
            "# Feature: login\n\n## Rules\n- RULE-1: Returns 200\n\n"
            "## Proof\n- PROOF-1 (RULE-1): Assert 200\n"
        )

        # conftest.py registers the plugin so pytest loads it at session start
        conftest = tmp_path / 'conftest.py'
        conftest.write_text(
            "import sys\n"
            f"sys.path.insert(0, r'{str(plugins_dir)}')\n"
            "from pytest_purlin import pytest_configure\n"
        )

        test_file = tmp_path / 'test_sample.py'
        test_file.write_text(
            "import pytest\n"
            "@pytest.mark.proof('login', 'PROOF-1', 'RULE-1')\n"
            "def test_valid_creds():\n"
            "    assert 200 == 200\n"
        )

        result = subprocess.run(
            [sys.executable, '-m', 'pytest', str(test_file), '-v', '--tb=short'],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"pytest plugin test failed:\n{result.stdout}\n{result.stderr}"

        proof_files = list((tmp_path / 'specs').rglob('*.proofs-unit.json'))
        assert proof_files, \
            "pytest plugin did not emit any .proofs-unit.json files"

        with open(str(proof_files[0])) as f:
            data = json.load(f)
        assert 'proofs' in data, "emitted proof file missing 'proofs' key"
        assert data['proofs'], "emitted proof file has empty proofs list"
        proof = data['proofs'][0]
        assert proof['id'] == 'PROOF-1', \
            f"expected PROOF-1, got {proof['id']}"
        assert proof['status'] == 'pass', \
            f"expected status pass, got {proof['status']}"

    @pytest.mark.proof("skill_init", "PROOF-22", "RULE-22")
    def test_jest_plugin_has_proof_emission_logic(self):
        """Verify jest_purlin.js contains the JSON emission and [proof:...] parsing logic."""
        src = os.path.join(PROJECT_ROOT, 'scripts', 'proof', 'jest_purlin.js')
        with open(src) as f:
            content = f.read()
        assert 'proofs' in content, \
            "jest_purlin.js missing 'proofs' key in output schema"
        assert 'JSON' in content, \
            "jest_purlin.js missing JSON serialization call"
        assert re.search(r'proof:', content), \
            "jest_purlin.js missing [proof:...] marker parsing"
        assert re.search(r'\.proofs-', content), \
            "jest_purlin.js missing .proofs-*.json file write logic"

    @pytest.mark.proof("skill_init", "PROOF-23", "RULE-23", tier="e2e")
    def test_shell_plugin_emits_valid_proofs_json(self, tmp_path):
        """Scaffold purlin-proof.sh and call purlin_proof + purlin_proof_finish."""
        src = os.path.join(PROJECT_ROOT, 'scripts', 'proof', 'shell_purlin.sh')
        plugin_dst = tmp_path / 'purlin-proof.sh'
        shutil.copy(src, str(plugin_dst))

        spec_dir = tmp_path / 'specs' / 'auth'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'login.md').write_text(
            "# Feature: login\n\n## Rules\n- RULE-1: Returns 200\n\n"
            "## Proof\n- PROOF-1 (RULE-1): Assert 200\n"
        )

        test_script = tmp_path / 'run_proof.sh'
        test_script.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"source '{str(plugin_dst)}'\n"
            "purlin_proof 'login' 'PROOF-1' 'RULE-1' pass 'returns 200'\n"
            "purlin_proof_finish\n"
        )
        test_script.chmod(0o755)

        result = subprocess.run(
            ['bash', str(test_script)],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"shell plugin test failed:\n{result.stdout}\n{result.stderr}"

        proof_files = list((tmp_path / 'specs').rglob('*.proofs-unit.json'))
        assert proof_files, \
            "shell plugin did not emit any .proofs-unit.json files"

        with open(str(proof_files[0])) as f:
            data = json.load(f)
        assert 'proofs' in data, "shell emitted proof file missing 'proofs' key"
        assert data['proofs'], "shell emitted proof file has empty proofs list"
        proof = data['proofs'][0]
        assert proof['id'] == 'PROOF-1', \
            f"expected PROOF-1, got {proof['id']}"
        assert proof['status'] == 'pass', \
            f"expected status pass, got {proof['status']}"

    @pytest.mark.proof("skill_init", "PROOF-24", "RULE-24", tier="e2e")
    def test_sync_status_returns_no_specs_found_for_empty_project(self, tmp_path):
        """sync_status on empty specs/ returns 'No specs found' without errors."""
        purlin_dir = tmp_path / '.purlin'
        purlin_dir.mkdir()
        config = {
            'version': '0.9.0',
            'test_framework': 'auto',
            'spec_dir': 'specs',
            'pre_push': 'warn',
            'report': False,
        }
        (purlin_dir / 'config.json').write_text(json.dumps(config))
        (tmp_path / 'specs').mkdir()

        result = purlin_server.sync_status(str(tmp_path))
        assert 'No specs found' in result, \
            f"sync_status should return 'No specs found' for empty specs/, got:\n{result}"

    @pytest.mark.proof("skill_init", "PROOF-25", "RULE-25", tier="e2e")
    def test_status_progression_untested_passing_failing(self, tmp_path):
        """Status: no proofs -> UNTESTED, all passing -> PASSING, one failing -> FAILING."""
        purlin_dir = tmp_path / '.purlin'
        purlin_dir.mkdir()
        config = {
            'version': '0.9.0',
            'test_framework': 'auto',
            'spec_dir': 'specs',
            'pre_push': 'warn',
            'report': False,
        }
        (purlin_dir / 'config.json').write_text(json.dumps(config))

        spec_dir = tmp_path / 'specs' / 'auth'
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / 'login.md'
        spec_file.write_text(
            "# Feature: login\n\n> Scope: src/auth.py\n\n"
            "## Rules\n- RULE-1: Returns 200\n\n"
            "## Proof\n- PROOF-1 (RULE-1): POST valid creds returns 200\n"
        )

        # Step 1: no proof file -> UNTESTED
        result = purlin_server.sync_status(str(tmp_path))
        assert 'UNTESTED' in result, \
            f"Expected UNTESTED with no proof file, got:\n{result}"

        # Step 2: passing proof -> PASSING
        proof_data = {'tier': 'unit', 'proofs': [
            {'feature': 'login', 'id': 'PROOF-1', 'rule': 'RULE-1',
             'test_file': 'tests/test_login.py', 'test_name': 'test_valid',
             'status': 'pass', 'tier': 'unit'},
        ]}
        (spec_dir / 'login.proofs-unit.json').write_text(json.dumps(proof_data))
        result = purlin_server.sync_status(str(tmp_path))
        assert 'PASSING' in result, \
            f"Expected PASSING with all passing proofs, got:\n{result}"

        # Step 3: failing proof -> FAILING
        proof_data['proofs'][0]['status'] = 'fail'
        (spec_dir / 'login.proofs-unit.json').write_text(json.dumps(proof_data))
        result = purlin_server.sync_status(str(tmp_path))
        assert 'FAILING' in result, \
            f"Expected FAILING with a failing proof, got:\n{result}"

    @pytest.mark.proof("skill_init", "PROOF-26", "RULE-26", tier="e2e")
    def test_sync_status_generates_report_data_js_when_report_true(self, tmp_path):
        """When report:true, sync_status generates .purlin/report-data.js with PURLIN_DATA."""
        purlin_dir = tmp_path / '.purlin'
        purlin_dir.mkdir()
        config = {
            'version': '0.9.0',
            'test_framework': 'auto',
            'spec_dir': 'specs',
            'pre_push': 'warn',
            'report': True,
        }
        (purlin_dir / 'config.json').write_text(json.dumps(config))

        spec_dir = tmp_path / 'specs' / 'auth'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'login.md').write_text(
            "# Feature: login\n\n> Scope: src/auth.py\n\n"
            "## Rules\n- RULE-1: Returns 200\n\n"
            "## Proof\n- PROOF-1 (RULE-1): POST valid creds returns 200\n"
        )
        proof_data = {'tier': 'unit', 'proofs': [
            {'feature': 'login', 'id': 'PROOF-1', 'rule': 'RULE-1',
             'test_file': 'tests/test_login.py', 'test_name': 'test_valid',
             'status': 'pass', 'tier': 'unit'},
        ]}
        (spec_dir / 'login.proofs-unit.json').write_text(json.dumps(proof_data))

        purlin_server.sync_status(str(tmp_path))

        report_data_path = purlin_dir / 'report-data.js'
        assert report_data_path.exists(), \
            ".purlin/report-data.js was not generated when report:true"
        content = report_data_path.read_text()
        assert 'PURLIN_DATA' in content, \
            ".purlin/report-data.js does not contain PURLIN_DATA"

    @pytest.mark.proof("skill_init", "PROOF-27", "RULE-27")
    def test_documents_required_gitignore_entries(self):
        content = _read('init')
        required_entries = [
            '.purlin/runtime/',
            '.purlin/plugins/__pycache__/',
            '.purlin/cache/',
            '/purlin-report.html',
            '.purlin/report-data.js',
        ]
        for entry in required_entries:
            assert entry in content, \
                f"init SKILL.md missing required .gitignore entry: '{entry}'"

    @pytest.mark.proof("skill_init", "PROOF-28", "RULE-28")
    def test_documents_reinit_does_not_duplicate_gitignore(self):
        content = _read('init')
        # Must use 'Ensure .gitignore contains' idempotent language (not blind append)
        assert re.search(r'(?i)ensure.*\.gitignore|\.gitignore.*contain', content), \
            "init SKILL.md missing 'Ensure .gitignore contains' idempotent language"
        # Step 5 (gitignore step) must be present
        assert 'Step 5' in content, \
            "init SKILL.md missing Step 5 (Update .gitignore)"

    @pytest.mark.proof("skill_init", "PROOF-29", "RULE-29")
    def test_documents_pre_push_hook_installation(self):
        content = _read('init')
        assert '.git/hooks/pre-push' in content, \
            "init SKILL.md missing .git/hooks/pre-push hook path"
        assert re.search(r'chmod\s*\+x', content), \
            "init SKILL.md missing chmod +x to make hook executable"
        assert re.search(r'(?i)purlin.*hook|hook.*purlin|contains.*purlin', content), \
            "init SKILL.md missing documentation that hook contains purlin"

    @pytest.mark.proof("skill_init", "PROOF-30", "RULE-30")
    def test_documents_existing_hook_preservation(self):
        content = _read('init')
        # Must document that an existing non-purlin hook is NOT overwritten
        assert re.search(r'(?i)(existing|different).*hook|hook.*(existing|different)',
                         content), \
            "init SKILL.md missing documentation about existing non-purlin hook"
        assert re.search(r'(?i)(skip|do not overwrite|warn.*skip|skipping)', content), \
            "init SKILL.md missing skip/preserve instruction for existing non-purlin hooks"

    @pytest.mark.proof("skill_init", "PROOF-31", "RULE-31")
    def test_documents_report_html_toggle(self):
        content = _read('init')
        # report:true must create purlin-report.html
        assert re.search(r'(?i)on.*purlin-report\.html|purlin-report\.html.*on|'
                         r'report.*true.*purlin-report|purlin-report.*report.*true',
                         content), \
            "init SKILL.md missing report:on/true -> purlin-report.html documentation"
        # report:false/off must document that the file is not created
        assert re.search(r'(?i)(off|false).*do not|do not.*html', content), \
            "init SKILL.md missing report:off/false -> do-not-copy documentation"

    @pytest.mark.proof("skill_init", "PROOF-32", "RULE-32", tier="e2e")
    def test_full_lifecycle_init_spec_proof_passing(self, tmp_path):
        """Full lifecycle: init structure -> spec -> proof plugin -> sync_status PASSING."""
        # 1. Create init-equivalent directory structure
        purlin_dir = tmp_path / '.purlin'
        (purlin_dir / 'plugins').mkdir(parents=True)
        config = {
            'version': '0.9.0',
            'test_framework': 'pytest',
            'spec_dir': 'specs',
            'pre_push': 'warn',
            'report': False,
        }
        (purlin_dir / 'config.json').write_text(json.dumps(config))
        (tmp_path / 'specs' / '_anchors').mkdir(parents=True)

        # 2. Scaffold pytest plugin (byte-identical copy from scripts/proof/)
        src = os.path.join(PROJECT_ROOT, 'scripts', 'proof', 'pytest_purlin.py')
        shutil.copy(src, str(purlin_dir / 'plugins' / 'pytest_purlin.py'))

        # 3. Create a spec
        spec_dir = tmp_path / 'specs' / 'auth'
        spec_dir.mkdir(parents=True)
        (spec_dir / 'login.md').write_text(
            "# Feature: login\n\n> Scope: src/auth.py\n\n"
            "## Rules\n- RULE-1: Returns 200 on valid credentials\n\n"
            "## Proof\n- PROOF-1 (RULE-1): POST valid creds returns 200\n"
        )

        # 4. Run proof plugin to emit proofs
        plugins_dir = purlin_dir / 'plugins'

        # conftest.py registers the plugin at pytest session start
        conftest = tmp_path / 'conftest.py'
        conftest.write_text(
            "import sys\n"
            f"sys.path.insert(0, r'{str(plugins_dir)}')\n"
            "from pytest_purlin import pytest_configure\n"
        )

        test_file = tmp_path / 'test_login.py'
        test_file.write_text(
            "import pytest\n"
            "@pytest.mark.proof('login', 'PROOF-1', 'RULE-1')\n"
            "def test_valid_credentials():\n"
            "    assert 200 == 200\n"
        )

        result = subprocess.run(
            [sys.executable, '-m', 'pytest', str(test_file), '-v', '--tb=short'],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"pytest run failed:\n{result.stdout}\n{result.stderr}"

        # 5. Verify proofs were emitted
        proof_files = list((tmp_path / 'specs').rglob('*.proofs-unit.json'))
        assert proof_files, "No proof files emitted after running pytest"

        # 6. sync_status reports PASSING
        status_output = purlin_server.sync_status(str(tmp_path))
        assert 'PASSING' in status_output, \
            f"Expected PASSING after full lifecycle run, got:\n{status_output}"

    @pytest.mark.proof("skill_init", "PROOF-35", "RULE-33", tier="e2e")
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

    @pytest.mark.proof("skill_init", "PROOF-36", "RULE-34", tier="e2e")
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

    @pytest.mark.proof("skill_init", "PROOF-37", "RULE-35", tier="e2e")
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

    @pytest.mark.proof("skill_init", "PROOF-38", "RULE-36", tier="e2e")
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

    @pytest.mark.proof("skill_init", "PROOF-39", "RULE-37", tier="e2e")
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


# ── skill_unit_test ───────────────────────────────────────────────────

class TestSkillUnitTest:

    @pytest.mark.proof("skill_unit_test", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        content = _read('unit-test')
        assert '---' in content, "unit-test SKILL.md must have YAML frontmatter delimiters"
        _assert_frontmatter(content, 'unit-test')

    @pytest.mark.proof("skill_unit_test", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        content = _read('unit-test')
        assert '## Usage' in content, "unit-test SKILL.md must have a ## Usage section"
        _assert_usage(content, 'unit-test')

    @pytest.mark.proof("skill_unit_test", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        content = _read('unit-test')
        assert 'name:' in content, "unit-test SKILL.md must have a name: field"
        _assert_name_matches(content, 'unit-test')

    @pytest.mark.proof("skill_unit_test", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        content = _read('unit-test')
        assert re.search(r'(?i)(git commit|commit the|create.*commit|commit.*change)', content), \
            "unit-test skill missing positive commit instruction"
        _assert_commit_instructions(content, 'unit-test')

    @pytest.mark.proof("skill_unit_test", "PROOF-5", "RULE-5")
    def test_requires_sync_status_not_optional(self):
        content = _read('unit-test')
        assert 'sync_status' in content, \
            "unit-test skill doesn't reference sync_status"
        assert 'not optional' in content, \
            "unit-test skill doesn't state sync_status is not optional"


# ── skill_verify ──────────────────────────────────────────────────────

class TestSkillVerify:

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
