"""Tests for purlin_skills — 15 rules.

Structural verification of the 12 skill definition files under skills/.
"""

import glob
import os
import re

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
SKILLS_DIR = os.path.join(PROJECT_ROOT, 'skills')


def _skill_files():
    return sorted(glob.glob(os.path.join(SKILLS_DIR, '*', 'SKILL.md')))


def _read(path):
    with open(path) as f:
        return f.read()


class TestPurlinSkills:

    @pytest.mark.proof("purlin_skills", "PROOF-1", "RULE-1")
    def test_each_skill_has_frontmatter(self):
        for path in _skill_files():
            content = _read(path)
            m = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
            assert m, f"No frontmatter in {path}"
            fm = m.group(1)
            assert 'name:' in fm, f"Missing name: in {path}"
            assert 'description:' in fm, f"Missing description: in {path}"

    @pytest.mark.proof("purlin_skills", "PROOF-2", "RULE-2")
    def test_exactly_twelve_skill_files(self):
        files = _skill_files()
        assert len(files) == 12, f"Expected 12 skills, found {len(files)}: {[os.path.basename(os.path.dirname(f)) for f in files]}"

    @pytest.mark.proof("purlin_skills", "PROOF-3", "RULE-3")
    def test_each_skill_has_usage_section(self):
        for path in _skill_files():
            content = _read(path)
            assert '## Usage' in content, \
                f"No ## Usage section in {path}"

    @pytest.mark.proof("purlin_skills", "PROOF-4", "RULE-4")
    def test_skill_name_matches_directory(self):
        for path in _skill_files():
            content = _read(path)
            m = re.search(r'^name:\s*(.+)', content, re.MULTILINE)
            assert m, f"No name: field in {path}"
            name = m.group(1).strip()
            dirname = os.path.basename(os.path.dirname(path))
            assert name == dirname, f"name '{name}' != dir '{dirname}' in {path}"

    @pytest.mark.proof("purlin_skills", "PROOF-5", "RULE-5")
    def test_modify_skills_have_commit_instructions(self):
        # Skills listed in PROOF-5 description (config excluded — modifies local-only file)
        for skill in ('build', 'spec', 'test', 'verify', 'init', 'anchor'):
            path = os.path.join(SKILLS_DIR, skill, 'SKILL.md')
            content = _read(path)
            # Assert a positive commit instruction, not just the word "commit"
            assert re.search(r'(?i)(git commit|commit the|create.*commit|commit.*change)', content), \
                f"{skill} skill missing positive commit instruction"

    @pytest.mark.proof("purlin_skills", "PROOF-6", "RULE-6")
    def test_mcp_skills_reference_tools(self):
        checks = {
            'status': 'sync_status',
            'drift': 'drift',
            'find': 'sync_status',
        }
        for skill, tool_name in checks.items():
            path = os.path.join(SKILLS_DIR, skill, 'SKILL.md')
            content = _read(path)
            assert tool_name in content, \
                f"{skill} skill doesn't reference MCP tool '{tool_name}'"

    @pytest.mark.proof("purlin_skills", "PROOF-7", "RULE-7")
    def test_build_and_unittest_require_sync_status(self):
        for skill in ('build', 'test'):
            path = os.path.join(SKILLS_DIR, skill, 'SKILL.md')
            content = _read(path)
            assert 'sync_status' in content, \
                f"{skill} skill doesn't reference sync_status"
        for skill_name in ('build', 'test'):
            content = _read(os.path.join(SKILLS_DIR, skill_name, 'SKILL.md'))
            assert 'not optional' in content, \
                f"{skill_name} skill doesn't state sync_status is not optional"

    @pytest.mark.proof("purlin_skills", "PROOF-8", "RULE-8")
    def test_verify_prohibits_modifying_files(self):
        content = _read(os.path.join(SKILLS_DIR, 'verify', 'SKILL.md'))
        assert 'NEVER modify' in content, \
            "verify skill missing 'NEVER modify' read-only constraint"

    @pytest.mark.proof("purlin_skills", "PROOF-9", "RULE-9")
    def test_build_has_failure_diagnosis_guidance(self):
        content = _read(os.path.join(SKILLS_DIR, 'build', 'SKILL.md'))
        assert 'diagnose' in content, \
            "build skill missing test failure diagnosis guidance"
        assert 'Never weaken' in content, \
            "build skill missing 'Never weaken' assertion guardrail"

    @pytest.mark.proof("purlin_skills", "PROOF-10", "RULE-10")
    def test_drift_requires_reading_diffs(self):
        content = _read(os.path.join(SKILLS_DIR, 'drift', 'SKILL.md'))
        assert 'git diff' in content, \
            "drift skill missing git diff requirement"

    @pytest.mark.proof("purlin_skills", "PROOF-11", "RULE-11")
    def test_spec_has_delta_report_structure(self):
        content = _read(os.path.join(SKILLS_DIR, 'spec', 'SKILL.md'))
        for keyword in ('KEEPING', 'ADDING', 'UPDATING', 'REMOVING'):
            assert keyword in content, \
                f"spec skill missing '{keyword}' in delta report structure"

    @pytest.mark.proof("purlin_skills", "PROOF-12", "RULE-12")
    def test_proof_writing_skills_review_both_the_tier_and_the_platform(self):
        for skill in ('build', 'spec', 'spec-from-code'):
            path = os.path.join(SKILLS_DIR, skill, 'SKILL.md')
            content = _read(path)
            # Must contain a tier-related instruction as a step or heading
            assert re.search(r'(?i)(tier\s+(assign|review|tag)|review.*tier|assign.*tier)', content), \
                f"{skill} skill missing tier review step/instruction"
            # Must also reference the actual tier tags
            assert re.search(r'@integration|@e2e|unit.*tier|tier.*unit', content), \
                f"{skill} skill missing tier tag references (@integration/@e2e/unit)"
            # A tier is not a platform. The same pass must review @on(...).
            assert re.search(r'(?i)platform[ -]tag review|platform review',
                             content), \
                (f"{skill} skill has no platform review step; a tier says what "
                 f"kind of test a proof is, never where it must run")
            assert '@on(' in content or 'platforms=' in content, \
                (f"{skill} skill never names the platform tag it is supposed "
                 f"to review")
            assert re.search(r'(?i)(coverage\s+denominator|AWAITING\s+RUNNER)',
                             content), \
                (f"{skill} skill states no consequence for a stray @on(...); "
                 f"without it the review has no bar to apply")

    @pytest.mark.proof("purlin_skills", "PROOF-13", "RULE-13")
    def test_init_add_plugin_validates_by_language(self):
        content = _read(os.path.join(SKILLS_DIR, 'init', 'SKILL.md'))
        for lang in ('Python', 'JavaScript', 'Shell', 'Java'):
            assert lang in content, \
                f"init skill missing validation entry for {lang}"
        assert "doesn't look like a standard proof plugin" in content, \
            "init skill missing validation warning text"

    @pytest.mark.proof("purlin_skills", "PROOF-14", "RULE-14")
    def test_init_add_plugin_supports_file_and_git(self):
        content = _read(os.path.join(SKILLS_DIR, 'init', 'SKILL.md'))
        assert 'local file path' in content, \
            "init skill missing local file path source docs"
        assert 'git URL' in content, \
            "init skill missing git URL source docs"
        # Verify distinct handling: each source type has its own conditional step
        assert re.search(r'(?i)if source is a local file path', content), \
            "init skill missing conditional step for local file path handling"
        assert re.search(r'(?i)if source is a git URL', content), \
            "init skill missing conditional step for git URL handling"

    @pytest.mark.proof("purlin_skills", "PROOF-15", "RULE-15")
    def test_init_list_plugins_labels_builtin_and_custom(self):
        content = _read(os.path.join(SKILLS_DIR, 'init', 'SKILL.md'))
        # Verify pytest pair appears on the same line or table row
        assert re.search(r'pytest_purlin\.py.*Python/pytest|Python/pytest.*pytest_purlin\.py',
                         content), \
            "init skill missing pytest_purlin.py → Python/pytest association on same line"
        assert re.search(r'jest_purlin\.js.*JavaScript/Jest|JavaScript/Jest.*jest_purlin\.js',
                         content), \
            "init skill missing jest_purlin.js → JavaScript/Jest association on same line"
        assert 'custom' in content, \
            "init skill missing 'custom' label for non-built-in plugins"

    @pytest.mark.proof("purlin_skills", "PROOF-16", "RULE-16")
    def test_every_skill_points_at_the_pending_migrations_section(self):
        """RULE-16: one anchor in all 12 skills, not twelve paraphrases."""
        anchor = 'purlin_commands.md#pending-migrations'
        files = _skill_files()
        assert len(files) == 12, f"expected 12 skills, scanned {len(files)}"
        missing = [p for p in files if anchor not in _read(p)]
        assert not missing, f"skills with no {anchor} pointer: {missing}"
        # The six that do not display sync_status output must say they call it.
        for name in ('spec', 'spec-from-code', 'audit', 'anchor', 'find',
                     'rename'):
            content = _read(os.path.join(SKILLS_DIR, name, 'SKILL.md'))
            line = [l for l in content.splitlines() if anchor in l]
            assert line, f"{name}: no pointer line"
            assert 'sync_status' in line[0] and 'first' in line[0], \
                f"{name} must say it calls sync_status first: {line[0]}"

    @pytest.mark.proof("purlin_skills", "PROOF-17", "RULE-17")
    def test_build_branches_on_mutation_checks_and_test_links_the_section(self):
        """RULE-17: one definition of the practice, linked from both skills."""
        anchor = 'spec_quality_guide.md#mutation-check'
        build = _read(os.path.join(SKILLS_DIR, 'build', 'SKILL.md'))
        assert 'mutation_checks' in build, "build skill does not name the field"
        assert anchor in build, f"build skill does not link {anchor}"
        assert re.search(r'`mutation_checks` is `true`', build), \
            "build skill has no true branch"
        assert re.search(r'`mutation_checks` is `false`', build), \
            "build skill has no false branch"
        assert 'purlin:init --mutation-checks on' in build, \
            "build skill does not say how to turn the check on"
        assert 'commit body' in build, \
            "build skill does not record the mutation in the commit body"
        test_skill = _read(os.path.join(SKILLS_DIR, 'test', 'SKILL.md'))
        assert anchor in test_skill, f"test skill does not link {anchor}"
