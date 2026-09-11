"""Tests for purlin_teammate_definitions — 3 rules.

Structural verification of the independent auditor agent definition. The definition
lives in the plugin's agents/ directory so it ships to consumer projects; definitions
under .claude/agents/ are project-local and reach nobody who installs Purlin.
"""

import glob
import os
import re

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
AGENTS_DIR = os.path.join(PROJECT_ROOT, 'agents')
LOCAL_AGENTS_DIR = os.path.join(PROJECT_ROOT, '.claude', 'agents')


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
        assert os.path.isfile(path), "agents/purlin-auditor.md not found"
        content = _read(path)
        fm = _extract_frontmatter(content)
        assert fm, "No YAML frontmatter found in purlin-auditor.md"
        assert 'name: purlin-auditor' in fm
        assert 'description:' in fm
        assert 'model:' in fm

    @pytest.mark.proof("purlin_teammate_definitions", "PROOF-4", "RULE-4")
    def test_auditor_ships_with_plugin_not_project_local(self):
        shipped = sorted(
            os.path.basename(f)
            for f in glob.glob(os.path.join(AGENTS_DIR, 'purlin-*.md'))
        )
        assert shipped == ['purlin-auditor.md'], (
            f"Expected only purlin-auditor.md in agents/, found {shipped}"
        )
        stragglers = sorted(
            os.path.basename(f)
            for f in glob.glob(os.path.join(LOCAL_AGENTS_DIR, 'purlin-*.md'))
        )
        assert stragglers == [], (
            "Agent definitions under .claude/agents/ are project-local and do not ship "
            f"with the plugin; found {stragglers}"
        )

    @pytest.mark.proof("purlin_teammate_definitions", "PROOF-5", "RULE-5")
    def test_auditor_routes_remediation_to_build_not_a_spawned_agent(self):
        content = _read(os.path.join(AGENTS_DIR, 'purlin-auditor.md'))
        assert 'purlin-builder' not in content, \
            "purlin-builder is retired — it was never a spawnable type in consumer projects"
        assert not re.search(r'(?i)spawn', content), \
            "auditor must not instruct spawning another agent; the audit is read-only"
        assert 'purlin:build' in content, \
            "auditor must route remediation to purlin:build"
