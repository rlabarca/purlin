"""Tests for purlin_skills — 6 rules.

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
            assert '## Usage' in content or '## Step' in content, \
                f"No ## Usage or ## Steps section in {path}"

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
        for skill in ('build', 'verify', 'init'):
            path = os.path.join(SKILLS_DIR, skill, 'SKILL.md')
            content = _read(path)
            assert re.search(r'(?i)commit', content), \
                f"{skill} skill missing commit instructions"

    @pytest.mark.proof("purlin_skills", "PROOF-6", "RULE-6")
    def test_mcp_skills_reference_tools(self):
        checks = {
            'status': 'sync_status',
            'changelog': 'changelog',
            'config': 'purlin_config',
        }
        for skill, tool_name in checks.items():
            path = os.path.join(SKILLS_DIR, skill, 'SKILL.md')
            content = _read(path)
            assert tool_name in content, \
                f"{skill} skill doesn't reference MCP tool '{tool_name}'"
