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
SKILL_AUDIT = os.path.join(PROJECT_ROOT, 'skills', 'audit', 'SKILL.md')

# The prohibition the skill used to carry while the definition required the
# opposite. Either file alone can be made to read correctly while the pair
# still disagrees, so PROOF-6 asserts on both.
FORBIDS_SUBAGENT_WRITE = re.compile(
    r'(?i)\bsub-?agents?\b[^.\n]{0,80}?'
    r'\b(must not|may not|cannot|can not|never|do not|does not|should not|don\'t)\b'
    r'[^.\n]{0,60}?\bwrit'
)


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

    @pytest.mark.proof("purlin_teammate_definitions", "PROOF-6", "RULE-6")
    def test_auditor_and_skill_agree_the_auditor_writes_its_own_cache(self):
        """The definition requires the auditor to write through the locked flag,
        and the skill must not forbid what the definition requires."""
        auditor = ' '.join(_read(os.path.join(AGENTS_DIR, 'purlin-auditor.md')).split())
        skill = ' '.join(_read(SKILL_AUDIT).split())

        assert '--write-cache' in auditor, \
            "the auditor definition must name --write-cache"
        assert re.search(
            r'(?i)never write[^.]{0,40}\.purlin/cache/audit_cache\.json`?[^.]{0,40}directly',
            auditor), \
            "the definition must forbid writing .purlin/cache/audit_cache.json directly"
        assert re.search(r'(?i)exclusive (file )?lock', auditor), \
            "the definition must give the exclusive lock as the reason"
        assert re.search(r'(?i)(several auditors run at once|parallel|at once)', auditor), \
            "the definition must say the lock is what lets several auditors run at once"

        # The skill must carry the same division, not its opposite.
        assert '--write-cache' in skill, \
            "skills/audit/SKILL.md must name --write-cache"
        hit = FORBIDS_SUBAGENT_WRITE.search(skill)
        assert not hit, (
            "skills/audit/SKILL.md forbids a subagent from writing the cache while "
            f"agents/purlin-auditor.md requires it: {hit.group(0)!r}")
        assert re.search(r'(?i)writes its own assessments through[^\n]{0,40}--write-cache',
                         skill), \
            "the skill must say each auditor writes its own assessments through --write-cache"
        assert re.search(r'(?i)read(?:ing|s)?\s+(?:the cache|it)\s+back', skill), \
            "the skill must state the lead reads the cache back"
        assert re.search(r'(?i)land(?:ed|s)?', skill), \
            "the read-back exists to verify the entries landed"
