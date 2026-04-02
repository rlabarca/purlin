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
        assert 'model:' in fm

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
        assert 'Ship' in loop or 'verify' in loop

    @pytest.mark.proof("purlin_agent", "PROOF-3", "RULE-3")
    def test_specs_section_template(self):
        content = _read()
        assert '## Specs' in content
        # Extract between ## Specs and ## Proof Markers (next real section)
        # Simple index-based extraction avoids regex matching headings inside code blocks
        start = content.index('## Specs')
        end = content.index('## Proof Markers')
        section = content[start:end]
        assert '## What it does' in section
        assert '## Rules' in section
        assert '## Proof' in section

    @pytest.mark.proof("purlin_agent", "PROOF-4", "RULE-4")
    def test_proof_markers_three_frameworks(self):
        content = _read()
        assert '## Proof Markers' in content
        markers_match = re.search(r'## Proof Markers\n(.*?)(?=^## |\Z)', content,
                                  re.MULTILINE | re.DOTALL)
        assert markers_match
        section = markers_match.group(1)
        assert 'pytest' in section.lower() or 'pytest:' in section
        assert 'Jest' in section or 'jest:' in section
        assert 'Shell' in section or 'shell:' in section

    @pytest.mark.proof("purlin_agent", "PROOF-5", "RULE-5")
    def test_hard_gates_exactly_two(self):
        content = _read()
        assert '## Hard Gates' in content
        gates_match = re.search(r'## Hard Gates.*?\n(.*?)(?=^## |\Z)', content,
                                re.MULTILINE | re.DOTALL)
        assert gates_match
        section = gates_match.group(1)
        assert 'only 2' in content or 'only 2' in section
        assert re.search(r'[Ii]nvariant\s+[Pp]rotection', section)
        assert re.search(r'[Pp]roof\s+[Cc]overage', section)

    @pytest.mark.proof("purlin_agent", "PROOF-6", "RULE-6")
    def test_implicit_routing(self):
        content = _read()
        assert '## Implicit Routing' in content
        routing_match = re.search(r'## Implicit Routing\n(.*?)(?=^## |\Z)', content,
                                  re.MULTILINE | re.DOTALL)
        assert routing_match
        section = routing_match.group(1)
        for keyword in ('test', 'status', 'changelog', 'spec', 'verify',
                        'engineer', 'qa', 'team'):
            assert keyword.lower() in section.lower(), \
                f"Missing routing for: {keyword}"

    @pytest.mark.proof("purlin_agent", "PROOF-7", "RULE-7")
    def test_skills_table_twelve_entries(self):
        content = _read()
        assert '## Skills' in content
        skills_match = re.search(r'## Skills.*?\n(.*?)(?=^## |\Z)', content,
                                 re.MULTILINE | re.DOTALL)
        assert skills_match
        section = skills_match.group(1)
        # Count table rows with purlin: skills (excluding header/separator)
        rows = re.findall(r'^\|.*`purlin:\w[\w-]*`.*\|', section, re.MULTILINE)
        assert len(rows) == 13, f"Expected 13 skill rows, found {len(rows)}"

    @pytest.mark.proof("purlin_agent", "PROOF-8", "RULE-8")
    def test_references_table_eight_entries(self):
        content = _read()
        assert '## References' in content
        refs_match = re.search(r'## References\n(.*?)(?=^## |\Z)', content,
                               re.MULTILINE | re.DOTALL)
        assert refs_match
        section = refs_match.group(1)
        # Count data rows (exclude header and separator)
        rows = [l for l in section.strip().splitlines()
                if l.startswith('|') and '---' not in l and 'Document' not in l]
        assert len(rows) == 11, f"Expected 11 reference rows, found {len(rows)}"
