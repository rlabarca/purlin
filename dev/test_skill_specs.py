"""Tests for individual skill specs — one spec per skill.

Structural verification of each skill definition file under skills/.
"""

import os
import re

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
SKILLS_DIR = os.path.join(PROJECT_ROOT, 'skills')


def _read(skill_name):
    path = os.path.join(SKILLS_DIR, skill_name, 'SKILL.md')
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
        _assert_frontmatter(_read('anchor'), 'anchor')

    @pytest.mark.proof("skill_anchor", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('anchor'), 'anchor')

    @pytest.mark.proof("skill_anchor", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('anchor'), 'anchor')

    @pytest.mark.proof("skill_anchor", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        _assert_commit_instructions(_read('anchor'), 'anchor')


# ── skill_audit ───────────────────────────────────────────────────────

class TestSkillAudit:

    @pytest.mark.proof("skill_audit", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        _assert_frontmatter(_read('audit'), 'audit')

    @pytest.mark.proof("skill_audit", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('audit'), 'audit')

    @pytest.mark.proof("skill_audit", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('audit'), 'audit')


# ── skill_build ───────────────────────────────────────────────────────

class TestSkillBuild:

    @pytest.mark.proof("skill_build", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        _assert_frontmatter(_read('build'), 'build')

    @pytest.mark.proof("skill_build", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('build'), 'build')

    @pytest.mark.proof("skill_build", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('build'), 'build')

    @pytest.mark.proof("skill_build", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        _assert_commit_instructions(_read('build'), 'build')

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


# ── skill_drift ───────────────────────────────────────────────────────

class TestSkillDrift:

    @pytest.mark.proof("skill_drift", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        _assert_frontmatter(_read('drift'), 'drift')

    @pytest.mark.proof("skill_drift", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('drift'), 'drift')

    @pytest.mark.proof("skill_drift", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('drift'), 'drift')

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
        _assert_frontmatter(_read('find'), 'find')

    @pytest.mark.proof("skill_find", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('find'), 'find')

    @pytest.mark.proof("skill_find", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('find'), 'find')

    @pytest.mark.proof("skill_find", "PROOF-4", "RULE-4")
    def test_references_sync_status_mcp_tool(self):
        content = _read('find')
        assert 'sync_status' in content, \
            "find skill doesn't reference MCP tool 'sync_status'"


# ── skill_init ────────────────────────────────────────────────────────

class TestSkillInit:

    @pytest.mark.proof("skill_init", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        _assert_frontmatter(_read('init'), 'init')

    @pytest.mark.proof("skill_init", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('init'), 'init')

    @pytest.mark.proof("skill_init", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('init'), 'init')

    @pytest.mark.proof("skill_init", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        _assert_commit_instructions(_read('init'), 'init')

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
        assert re.search(r'pytest_purlin\.py.*Python/pytest|Python/pytest.*pytest_purlin\.py',
                         content), \
            "init skill missing pytest_purlin.py → Python/pytest association"
        assert re.search(r'jest_purlin\.js.*JavaScript/Jest|JavaScript/Jest.*jest_purlin\.js',
                         content), \
            "init skill missing jest_purlin.js → JavaScript/Jest association"
        assert 'custom' in content, \
            "init skill missing 'custom' label for non-built-in plugins"


# ── skill_rename ──────────────────────────────────────────────────────

class TestSkillRename:

    @pytest.mark.proof("skill_rename", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        _assert_frontmatter(_read('rename'), 'rename')

    @pytest.mark.proof("skill_rename", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('rename'), 'rename')

    @pytest.mark.proof("skill_rename", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('rename'), 'rename')


# ── skill_spec ────────────────────────────────────────────────────────

class TestSkillSpec:

    @pytest.mark.proof("skill_spec", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        _assert_frontmatter(_read('spec'), 'spec')

    @pytest.mark.proof("skill_spec", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('spec'), 'spec')

    @pytest.mark.proof("skill_spec", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('spec'), 'spec')

    @pytest.mark.proof("skill_spec", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        _assert_commit_instructions(_read('spec'), 'spec')

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
        _assert_frontmatter(_read('spec-from-code'), 'spec-from-code')

    @pytest.mark.proof("skill_spec_from_code", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('spec-from-code'), 'spec-from-code')

    @pytest.mark.proof("skill_spec_from_code", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('spec-from-code'), 'spec-from-code')

    @pytest.mark.proof("skill_spec_from_code", "PROOF-4", "RULE-4")
    def test_has_tier_review(self):
        content = _read('spec-from-code')
        assert re.search(r'(?i)(tier\s+(assign|review|tag)|review.*tier|assign.*tier)', content), \
            "spec-from-code skill missing tier review step/instruction"
        assert re.search(r'@integration|@e2e|unit.*tier|tier.*unit', content), \
            "spec-from-code skill missing tier tag references (@integration/@e2e/unit)"


# ── skill_status ──────────────────────────────────────────────────────

class TestSkillStatus:

    @pytest.mark.proof("skill_status", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        _assert_frontmatter(_read('status'), 'status')

    @pytest.mark.proof("skill_status", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('status'), 'status')

    @pytest.mark.proof("skill_status", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('status'), 'status')

    @pytest.mark.proof("skill_status", "PROOF-4", "RULE-4")
    def test_references_sync_status_mcp_tool(self):
        content = _read('status')
        assert 'sync_status' in content, \
            "status skill doesn't reference MCP tool 'sync_status'"


# ── skill_unit_test ───────────────────────────────────────────────────

class TestSkillUnitTest:

    @pytest.mark.proof("skill_unit_test", "PROOF-1", "RULE-1")
    def test_has_frontmatter(self):
        _assert_frontmatter(_read('unit-test'), 'unit-test')

    @pytest.mark.proof("skill_unit_test", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('unit-test'), 'unit-test')

    @pytest.mark.proof("skill_unit_test", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('unit-test'), 'unit-test')

    @pytest.mark.proof("skill_unit_test", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        _assert_commit_instructions(_read('unit-test'), 'unit-test')

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
        _assert_frontmatter(_read('verify'), 'verify')

    @pytest.mark.proof("skill_verify", "PROOF-2", "RULE-2")
    def test_has_usage_section(self):
        _assert_usage(_read('verify'), 'verify')

    @pytest.mark.proof("skill_verify", "PROOF-3", "RULE-3")
    def test_name_matches_directory(self):
        _assert_name_matches(_read('verify'), 'verify')

    @pytest.mark.proof("skill_verify", "PROOF-4", "RULE-4")
    def test_has_commit_instructions(self):
        _assert_commit_instructions(_read('verify'), 'verify')

    @pytest.mark.proof("skill_verify", "PROOF-5", "RULE-5")
    def test_verify_prohibits_modifying_files(self):
        content = _read('verify')
        assert 'NEVER modify' in content, \
            "verify skill missing 'NEVER modify' read-only constraint"
