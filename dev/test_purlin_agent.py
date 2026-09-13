"""Tests for purlin_agent — 8 rules.

Structural verification of the Purlin agent definition at agents/purlin.md.
All tests are grep-based checks on the agent file content.
"""

import os
import re

import pytest

AGENT_PATH = os.path.join(os.path.dirname(__file__), '..', 'agents', 'purlin.md')


def _read():
    with open(AGENT_PATH) as f:
        return f.read()


class TestPurlinAgent:

    @pytest.mark.proof("purlin_agent", "PROOF-1", "RULE-1")
    def test_yaml_frontmatter(self):
        content = _read()
        # Find YAML frontmatter between --- delimiters
        m = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
        assert m, "No YAML frontmatter found"
        fm = m.group(1)
        assert 'name:' in fm
        assert 'description:' in fm
        pinned = [ln for ln in fm.splitlines()
                  if re.match(r'\s*model\s*:', ln)]
        assert not pinned, (
            f"agents/purlin.md pins a model {pinned}; a shipped agent "
            f"overrides every host that installs the plugin, and the pin goes "
            f"stale the moment that model is superseded")

    @pytest.mark.proof("purlin_agent", "PROOF-2", "RULE-2")
    def test_core_loop_four_steps(self):
        content = _read()
        assert '## Core Loop' in content
        # Find the 4 numbered steps
        loop_match = re.search(r'## Core Loop\n(.*?)(?=^## |\Z)', content,
                               re.MULTILINE | re.DOTALL)
        assert loop_match
        loop = loop_match.group(1)
        steps = re.findall(r'^\d+\.', loop, re.MULTILINE)
        assert len(steps) == 4
        assert 'Do the work' in loop
        assert 'sync_status' in loop
        assert 'Follow' in loop
        assert 'Ship' in loop

    @pytest.mark.proof("purlin_agent", "PROOF-3", "RULE-3")
    def test_specs_section_template(self):
        content = _read()
        assert '## Specs' in content
        # Extract between ## Specs and ## Proof Markers (next real section)
        start = content.index('## Specs')
        end = content.index('## Proof Markers')
        section = content[start:end]
        # Find template inside a fenced code block (``` block)
        code_blocks = re.findall(r'```[^\n]*\n(.*?)```', section, re.DOTALL)
        template_text = '\n'.join(code_blocks)
        assert '> Description:' in template_text, \
            "'> Description:' not found inside a code block template"
        assert '## Rules' in template_text, \
            "'## Rules' not found inside a code block template"
        assert '## Proof' in template_text, \
            "'## Proof' not found inside a code block template"

    @pytest.mark.proof("purlin_agent", "PROOF-4", "RULE-4")
    def test_proof_markers_three_frameworks(self):
        content = _read()
        assert '## Proof Markers' in content
        markers_match = re.search(r'## Proof Markers\n(.*?)(?=^## |\Z)', content,
                                  re.MULTILINE | re.DOTALL)
        assert markers_match
        section = markers_match.group(1)
        # Proof markers delegate to reference file for all three frameworks
        assert 'proofs_format.md' in section, \
            "Proof Markers section must reference proofs_format.md"
        for fw in ('pytest', 'Jest', 'Shell'):
            assert fw in section, \
                f"Missing framework mention for {fw} in ## Proof Markers"

    @pytest.mark.proof("purlin_agent", "PROOF-5", "RULE-5")
    def test_hard_gates_exactly_one(self):
        content = _read()
        assert '## Hard Gates' in content
        gates_match = re.search(r'## Hard Gates.*?\n(.*?)(?=^## |\Z)', content,
                                re.MULTILINE | re.DOTALL)
        assert gates_match
        section = gates_match.group(1)
        assert re.search(r'[Pp]roof\s+[Cc]overage', section), \
            "Hard Gates section missing 'Proof coverage'"
        gates = re.findall(r'^\d+\.', section, re.MULTILINE)
        assert len(gates) == 1, \
            f"Expected exactly 1 gate, found {len(gates)}"

    @pytest.mark.proof("purlin_agent", "PROOF-6", "RULE-6")
    def test_implicit_routing(self):
        content = _read()
        assert '## Implicit Routing' in content
        routing_match = re.search(r'## Implicit Routing\n(.*?)(?=^## |\Z)', content,
                                  re.MULTILINE | re.DOTALL)
        assert routing_match
        section = routing_match.group(1)
        # Extract routing entry lines (bullets with → or ->)
        routing_lines = [l for l in section.splitlines()
                         if '\u2192' in l or '->' in l]
        # Each keyword must appear as a source term (before the arrow) in a routing line
        for keyword in ('test', 'status', 'drift', 'spec', 'verify',
                        'engineer', 'qa', 'team'):
            found = any(keyword.lower() in l.lower().split('\u2192')[0].split('->')[0]
                        for l in routing_lines)
            assert found, \
                f"Missing routing source for: {keyword} (must appear before → arrow)"

    @pytest.mark.proof("purlin_agent", "PROOF-7", "RULE-7")
    def test_every_skills_row_names_a_skill_that_exists(self):
        """RULE-7: the table and skills/ are the same set, both ways.

        The old proof counted 12 rows, which passed on a thirteenth row
        (`purlin:init --update`) the row regex could not see, and would pass
        just as well on a row naming a skill that had been deleted.
        """
        content = _read()
        assert '## Skills' in content
        skills_match = re.search(r'## Skills.*?\n(.*?)(?=^## |\Z)', content,
                                 re.MULTILINE | re.DOTALL)
        assert skills_match
        section = skills_match.group(1)

        rows = re.findall(r'^\|\s*`purlin:([\w-]+)`\s*\|(.*)\|\s*$',
                          section, re.MULTILINE)
        listed = {name for name, _ in rows}
        assert len(listed) >= 10, (
            f"the skills table did not parse: {listed}")

        skills_dir = os.path.join(os.path.dirname(AGENT_PATH), '..', 'skills')
        shipped = {d for d in os.listdir(skills_dir)
                   if os.path.isfile(os.path.join(skills_dir, d, 'SKILL.md'))}

        assert listed == shipped, (
            f"the table and skills/ disagree: rows with no skill file "
            f"{sorted(listed - shipped)}, skills with no row "
            f"{sorted(shipped - listed)}")

        for name, purpose in rows:
            assert purpose.strip(), f"row for purlin:{name} has no purpose"

        # Every table row is one the comparison above could see. A row whose
        # first cell carries a flag (`purlin:init --update`) is invisible to
        # it, which is how a thirteenth row once hid inside a count of 12.
        unseen = [l for l in section.splitlines()
                  if l.startswith('|') and 'purlin:' in l
                  and not re.match(r'^\|\s*`purlin:[\w-]+`\s*\|', l)]
        assert not unseen, (
            f"these rows name a skill the set comparison cannot read: "
            f"{unseen}; a flag belongs in the row of its own skill")

    @pytest.mark.proof("purlin_agent", "PROOF-8", "RULE-8")
    def test_every_references_row_leads_somewhere(self):
        """RULE-8: a row count says nothing about whether the row resolves."""
        content = _read()
        assert '## References' in content
        refs_match = re.search(r'## References\n(.*?)(?=^## |\Z)', content,
                               re.MULTILINE | re.DOTALL)
        assert refs_match
        section = refs_match.group(1)

        rows = [l for l in section.strip().splitlines()
                if l.startswith('|') and '---' not in l
                and 'Document' not in l]
        assert rows, "the references table did not parse"

        root = os.path.join(os.path.dirname(AGENT_PATH), '..')
        paths = []
        for row in rows:
            cells = [c.strip() for c in row.split('|') if c.strip()]
            assert len(cells) >= 2, f"row missing topic column: {row}"
            assert len(cells[1]) > 5, f"topic too short in row: {row}"
            m = re.search(r'`([^`]+\.md)`', cells[0])
            if not m or '/' not in m.group(1):
                continue
            paths.append(m.group(1))
            assert os.path.isfile(os.path.join(root, m.group(1))), (
                f"the references table sends the agent to {m.group(1)}, "
                f"which does not exist")

        assert len(paths) >= 8, (
            f"only {paths} resolved as repository paths; the scan is not "
            f"seeing the table it claims to check")


class TestThreePathways:
    """RULE-9/10/11 — the agent must support all three authoring pathways.

    agents/purlin.md previously said "If a spec exists but code doesn't, build the
    code first", which forbade the specs-and-proofs-first pathway outright, and its
    Core Loop opened with "Do the work — write code".
    """

    @pytest.mark.proof("purlin_agent", "PROOF-9", "RULE-9")
    def test_states_the_three_questions(self):
        content = _read()
        assert 'Proof Design' in content and 'Proof Integrity' in content, \
            "the agent must know both gauges by name"
        assert re.search(r'(?i)provable', content), "missing the 'is it provable' question"
        assert re.search(r'(?i)proven', content), "missing the 'is it proven' question"
        assert re.search(r'(?i)owns pass/fail', content), \
            "must state that purlin:verify alone owns pass/fail"

    @pytest.mark.proof("purlin_agent", "PROOF-10", "RULE-10")
    def test_no_fixed_order_and_all_three_pathways(self):
        content = _read()
        assert 'build the code first' not in content, (
            "this instruction forbids the specs-first pathway; the agent must read "
            "state instead of imposing an order")
        assert re.search(r'(?i)no fixed order', content), \
            "the Core Loop must say there is no fixed order"
        # Each pathway must be discoverable.
        assert re.search(r'(?i)specs? and proofs first', content), \
            "pathway A (specs and proofs first) must be named"
        assert re.search(r'(?i)code and tests together', content), \
            "pathway B must be named"
        assert re.search(r'(?i)then tests', content), "pathway C must be named"
        # And the state table must tell the two spec-only states apart.
        assert 'Scope:' in content and re.search(r'(?i)UNTESTED', content), \
            "the agent must know how the two spec-only states are distinguished"

    @pytest.mark.proof("purlin_agent", "PROOF-11", "RULE-11")
    def test_routes_design_intent_and_integrity_targets(self):
        content = _read()
        assert '--design' in content, \
            "design-intent phrasings must route to purlin:audit --design"
        assert re.search(r'(?i)are my proofs', content), \
            "missing a design-intent trigger phrase"
        # The ceiling arithmetic, so a target request is answered before work starts.
        assert re.search(r'\(1\s*[−-]\s*T\)', content), \
            "must carry the reachability condition for an integrity target"

    @pytest.mark.proof("purlin_agent", "PROOF-12", "RULE-12")
    def test_agent_links_the_two_shared_sections(self):
        """RULE-12: the agent names the sections rather than restating them."""
        content = _read()
        assert 'spec_quality_guide.md#mutation-check' in content, \
            "agent does not link the mutation-check section"
        assert 'purlin_commands.md#pending-migrations' in content, \
            "agent does not link the pending-migrations section"
        start = content.index('## Core Loop')
        end = content.index('## ', start + 5)
        core_loop = content[start:end]
        assert 'spec_quality_guide.md#mutation-check' in core_loop, \
            "the mutation-check link must be in the core loop, not only the table"
        rows = [l for l in content.splitlines()
                if l.startswith('|') and 'spec_quality_guide.md' in l]
        assert rows, "no reference-table row for spec_quality_guide.md"
        assert any('mutation check' in r.lower() for r in rows), rows
