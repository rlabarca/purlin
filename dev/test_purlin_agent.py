"""Tests for purlin_agent — 8 rules.

Structural verification of the Purlin agent definition at agents/purlin.md.
All tests are grep-based checks on the agent file content.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prose_lint import _heading_slugs  # noqa: E402

AGENT_PATH = os.path.join(os.path.dirname(__file__), '..', 'agents', 'purlin.md')


def _read():
    with open(AGENT_PATH) as f:
        return f.read()


def _shipped_framework_ids():
    """The first column of the shipped-plugin table of the contract."""
    path = os.path.join(os.path.dirname(AGENT_PATH), '..', 'references',
                        'proof_plugin_contract.md')
    with open(path, encoding='utf-8') as f:
        lines = f.read().splitlines()
    ids, inside = [], False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('### What the eight shipped plugins'):
            inside = True
            continue
        if inside and stripped.startswith('#'):
            break
        if not (inside and stripped.startswith('|')):
            continue
        cell = stripped.strip('|').split('|')[0].strip()
        if cell in ('Framework', '') or set(cell) <= set('-: '):
            continue
        ids.append(cell)
    return ids


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
    def test_core_loop_is_four_unnumbered_moves(self):
        """RULE-2: numbering is a claim about order that the subsection
        underneath denies, and the agent reads the numbers first."""
        content = _read()
        assert '## Core Loop' in content
        loop_match = re.search(r'## Core Loop\n(.*?)(?=^## |\Z)', content,
                               re.MULTILINE | re.DOTALL)
        assert loop_match, "agents/purlin.md has no ## Core Loop section"
        loop = loop_match.group(1)

        labels = ('Do the work', 'sync_status', 'Follow', 'Ship')
        for label in labels:
            assert label in loop, f"the Core Loop lost the move {label!r}"

        numbered = [l for l in loop.splitlines() if re.match(r'^\d+\.', l)]
        assert not numbered, (
            "the Core Loop must number nothing: a numbered list is a fixed "
            "order, and the subsection below it says there is none:\n"
            + "\n".join(numbered))

        denial = loop.find('There is no fixed order')
        assert denial != -1, (
            "the Core Loop must state that there is no fixed order")
        first_label = min(loop.find(label) for label in labels)
        assert denial < first_label, (
            f"the no-fixed-order statement is at offset {denial} and the "
            f"first move at {first_label}; an agent reading top to bottom "
            f"meets the moves before the statement that they are not a "
            f"sequence")

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
    def test_proof_markers_section_names_no_framework(self):
        """RULE-4: a list of three of eight is a list that goes stale."""
        content = _read()
        match = re.search(r'^##\s+Proof Markers\s*$(.*?)(?=^##\s|\Z)',
                          content, re.MULTILINE | re.DOTALL)
        assert match, "agents/purlin.md carries no `## Proof Markers` section"
        section = match.group(1).strip()
        assert section, "the Proof Markers section is empty"
        assert 'references/formats/proofs_format.md' in section, (
            "the section must link the reference that documents every "
            f"framework's marker:\n{section}")
        ids = _shipped_framework_ids()
        assert len(ids) >= 8, (
            f"read {len(ids)} framework ids from the contract's table; the "
            f"scan would pass on an empty list")
        named = [i for i in ids
                 if re.search(rf'\b{re.escape(i)}\b', section, re.I)]
        assert not named, (
            f"the section names {named}; a list of some frameworks is a list "
            f"a reader trusts for all of them:\n{section}")


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
        # The ceiling arithmetic, so a target request is answered before work
        # starts. The agent routes to it; it does not carry a copy: this file
        # is read on every turn.
        assert 'references/audit_criteria.md' in content, \
            "the integrity-target route must name the file holding the arithmetic"
        assert re.search(r'(?i)reaching a target integrity score', content), \
            "and must name the section, not just the file"
        assert not re.search(r'\(1\s*[−-]\s*T\)', content), (
            "the agent carries its own copy of the reachability formula; "
            "references/audit_criteria.md is its one home")

        criteria = os.path.join(os.path.dirname(AGENT_PATH), '..',
                                'references', 'audit_criteria.md')
        with open(criteria) as f:
            section = f.read()
        section = section[section.index('### Reaching a target Integrity score'):]
        section = section[:section.index('\n## ')]
        assert re.search(r'ceiling\s*=', section), \
            "the reference must state the ceiling"
        assert re.search(r'(?i)reachable\s+\*\*iff\*\*.*\(1\s*[−-]\s*T\)',
                         section), \
            "the reference must state the reachability condition"
        assert re.search(r'(?i)must be rewritten|rewritten\s*=', section), \
            "the reference must say how many proofs have to be rewritten"

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

    @pytest.mark.proof("purlin_agent", "PROOF-13", "RULE-13")
    def test_the_no_verify_never_names_layer_one_not_a_safety_gate(self):
        """RULE-13: the NEVER entry agrees with references/hard_gates.md."""
        content = _read()
        entries = [l for l in content.splitlines()
                   if l.lstrip().startswith('- **NEVER')
                   and '--no-verify' in l]
        assert len(entries) == 1, (
            f"expected exactly one NEVER entry naming --no-verify, "
            f"got {len(entries)}: {entries}")
        entry = entries[0]
        assert 'references/hard_gates.md' in entry, (
            "the entry must point at the reference that records the layers, "
            f"so the claim can be checked: {entry}")
        assert 'Layer 1' in entry, (
            f"the entry must say which layer the hook is: {entry}")
        banned = [phrase for phrase in
                  ('safety gate', 'no legitimate reason',
                   'defeats proof enforcement')
                  if phrase in entry]
        assert not banned, (
            f"the entry still carries {banned}, which references/"
            f"hard_gates.md contradicts: the hook is bypassable, `off` "
            f"blocks nothing, and this repository runs pre_push: off\n{entry}")

        gates_path = os.path.join(os.path.dirname(__file__), '..',
                                  'references', 'hard_gates.md')
        with open(gates_path) as f:
            gates = f.read()
        layer_one = [l for l in gates.splitlines()
                     if l.startswith('|') and 'Layer 1' in l]
        assert len(layer_one) == 1, (
            f"expected one Layer 1 row in hard_gates.md, got {layer_one}")
        assert '--no-verify' in layer_one[0] and '`off`' in layer_one[0], (
            "the Layer 1 row must still name the bypass and the off mode, or "
            f"the agent cites a reference that no longer says it:\n"
            f"{layer_one[0]}")

    @pytest.mark.proof("purlin_agent", "PROOF-14", "RULE-14")
    def test_skills_are_optional_for_the_user_and_mandatory_for_the_agent(self):
        """RULE-14: an unqualified `optional` is permission to ignore the
        NEVER list two screens above it."""
        content = _read()
        heading = '## Skills (optional for the user, mandatory for you)'
        assert heading in content, (
            "the Skills heading must name both audiences; an agent that "
            "reads `optional tools` has been told its own NEVER list is "
            "advice")
        body = content[content.index(heading) + len(heading):]
        body = re.split(r'(?m)^## ', body)[0]

        paras = [b.strip() for b in body.split('\n\n')
                 if 'optional' in b and not b.strip().startswith('|')]
        assert len(paras) == 1, (
            f"expected one paragraph below the Skills table saying optional, "
            f"got {len(paras)}: {paras}")
        para = paras[0]
        for token in ('optional', 'mandatory', 'user', 'hand',
                      'references/hard_gates.md', 'NEVER'):
            assert token in para, (
                f"the paragraph below the table does not carry {token!r}; it "
                f"must name both audiences, say the user may write by hand, "
                f"cite the NEVER list as the agent's contract and link "
                f"hard_gates.md:\n{para}")
        assert 'Skills are tools, not gatekeepers' not in content, (
            "the unqualified closing line is back, and it is false of the "
            "agent reading it")

        gates_path = os.path.join(os.path.dirname(__file__), '..',
                                  'references', 'hard_gates.md')
        with open(gates_path) as f:
            gates = f.read()
        assert 'Skills are optional tools, not gatekeepers.' not in gates, (
            "references/hard_gates.md carries the unqualified claim again, "
            "so the two files can be read against each other")
        gate_lines = [l for l in gates.splitlines()
                      if 'Skills are optional' in l]
        assert len(gate_lines) == 1, (
            f"expected one `Skills are optional` line in hard_gates.md, got "
            f"{gate_lines}")
        sentence = gate_lines[0].split('. ')[0]
        assert 'mandatory' in sentence, (
            "the qualifier must sit in the same sentence as `optional`, or a "
            f"reader takes the first half and stops:\n{sentence}")
        assert 'agents/purlin.md' in gate_lines[0], (
            "the reference must name where the agent's obligation is "
            f"written:\n{gate_lines[0]}")

    @pytest.mark.proof("purlin_agent", "PROOF-15", "RULE-15")
    def test_path_resolution_names_all_five_plugin_directories(self):
        """RULE-15: the section covered one of the five it had to cover."""
        content = _read()
        match = re.search(r'^##\s+Path Resolution\s*$(.*?)(?=^##\s|\Z)',
                          content, re.MULTILINE | re.DOTALL)
        assert match, "agents/purlin.md carries no `## Path Resolution`"
        section = match.group(1).strip()
        assert section, "the Path Resolution section is empty"
        for token in ('`references/`', '`templates/`', '`hooks/`',
                      '`scripts/`', '`agents/`'):
            assert token in section, (
                f"the section must name {token} as resolving against the "
                f"plugin root:\n{section}")
        assert '${CLAUDE_PLUGIN_ROOT}' in section, section
        assert 'project root' in section, section
        assert 'references/purlin_commands.md#path-resolution' in section, (
            "the section must point at the full statement")

        commands = os.path.join(os.path.dirname(AGENT_PATH), '..',
                                'references', 'purlin_commands.md')
        with open(commands, encoding='utf-8') as f:
            body = f.read()
        assert 'path-resolution' in _heading_slugs(body), (
            "references/purlin_commands.md carries no heading whose slug is "
            "path-resolution, so the pointer resolves to nothing")
