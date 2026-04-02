"""Tests for purlin_teammate_definitions — 4 rules.

Structural verification of the three teammate agent definitions in .claude/agents/.
"""

import glob
import os
import re

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
AGENTS_DIR = os.path.join(PROJECT_ROOT, '.claude', 'agents')


def _read(path):
    with open(path) as f:
        return f.read()


def _extract_frontmatter(content):
    m = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
    return m.group(1) if m else None


class TestPurlinTeammateDefinitions:

    @pytest.mark.proof("purlin_teammate_definitions", "PROOF-1", "RULE-1")
    def test_auditor_frontmatter(self):
        path = os.path.join(AGENTS_DIR, 'purlin-auditor.md')
        assert os.path.isfile(path), "purlin-auditor.md not found"
        content = _read(path)
        fm = _extract_frontmatter(content)
        assert fm, "No YAML frontmatter found in purlin-auditor.md"
        assert 'name: purlin-auditor' in fm
        assert 'description:' in fm
        assert 'model:' in fm

    @pytest.mark.proof("purlin_teammate_definitions", "PROOF-2", "RULE-2")
    def test_builder_frontmatter(self):
        path = os.path.join(AGENTS_DIR, 'purlin-builder.md')
        assert os.path.isfile(path), "purlin-builder.md not found"
        content = _read(path)
        fm = _extract_frontmatter(content)
        assert fm, "No YAML frontmatter found in purlin-builder.md"
        assert 'name: purlin-builder' in fm
        assert 'description:' in fm
        assert 'model:' in fm

    @pytest.mark.proof("purlin_teammate_definitions", "PROOF-3", "RULE-3")
    def test_reviewer_frontmatter(self):
        path = os.path.join(AGENTS_DIR, 'purlin-reviewer.md')
        assert os.path.isfile(path), "purlin-reviewer.md not found"
        content = _read(path)
        fm = _extract_frontmatter(content)
        assert fm, "No YAML frontmatter found in purlin-reviewer.md"
        assert 'name: purlin-reviewer' in fm
        assert 'description:' in fm
        assert 'model:' in fm

    @pytest.mark.proof("purlin_teammate_definitions", "PROOF-4", "RULE-4")
    def test_all_three_in_agents_directory(self):
        files = sorted(glob.glob(os.path.join(AGENTS_DIR, 'purlin-*.md')))
        names = [os.path.basename(f) for f in files]
        assert len(files) == 3, f"Expected 3 purlin-*.md files, found {len(files)}: {names}"
        expected = {'purlin-auditor.md', 'purlin-builder.md', 'purlin-reviewer.md'}
        assert set(names) == expected, f"Expected {expected}, found {set(names)}"
