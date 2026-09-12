"""purlin_references: the proof-plugin contract is complete and current.

`references/proof_plugin_contract.md` is the reader-facing checklist for a proof
plugin. It is useful only while three things hold, and each is checked here:

  1. its wiring list names every file a new framework has to be wired into, and
     every path it names still exists;
  2. every behavioural row cites a rule `specs/_anchors/proof_common.md`
     actually carries, and every rule the anchor carries has a row;
  3. `references/formats/proofs_format.md` documents the run marker, which is
     the one part of the plugin contract the format file used to omit.

A checklist that has drifted from the tree is worse than none: it reads as
authoritative and sends the next author to a file that moved.
"""

import os
import re

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CONTRACT = os.path.join(PROJECT_ROOT, 'references', 'proof_plugin_contract.md')
PROOFS_FORMAT = os.path.join(
    PROJECT_ROOT, 'references', 'formats', 'proofs_format.md')
ANCHOR = os.path.join(
    PROJECT_ROOT, 'specs', '_anchors', 'proof_common.md')

# Every file a framework has to be named in before a project can select it, a
# hook can run it, the quality gate can grade it and the sweep can regenerate
# its evidence. Each entry is a site a half-wired framework breaks.
WIRING_SITES = (
    'scripts/proof/',
    'references/supported_frameworks.md',
    'scripts/init/scaffold.py',
    'scripts/hooks/pre_push_gate.py',
    'scripts/hooks/pre-push.sh',
    'skills/init/SKILL.md',
    'skills/test/SKILL.md',
    'docs/testing-workflow-guide.md',
    'references/formats/proofs_format.md',
    'references/audit_criteria.md',
    'scripts/audit/static_checks.py',
    'specs/proof/',
    'dev/test_multilang_proof_plugins.py',
    'dev/run_tests.sh',
    'specs/instructions/purlin_references.md',
    'specs/skills/skill_init.md',
    'specs/hooks/pre_push_hook.md',
    'specs/instructions/purlin_agent.md',
    'specs/instructions/purlin_skills.md',
)

# The nine top-level keys proof_common RULE-19 names for the run marker.
RUN_MARKER_FIELDS = ('at', 'commit', 'sweep', 'test_files',
                     'passed', 'failed', 'skipped', 'ok', 'runs')

# The shape of one `skipped_proofs` object (proof_common RULE-20).
SKIPPED_PROOF_FIELDS = ('feature', 'id', 'test_file', 'test_name', 'reason')


def _read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def _sections(text):
    """{heading: body} for every `## ` heading in a markdown file."""
    found = {}
    heading = None
    body = []
    for line in text.split('\n'):
        if line.startswith('## '):
            if heading is not None:
                found[heading] = '\n'.join(body)
            heading = line[3:].strip()
            body = []
        elif heading is not None:
            body.append(line)
    if heading is not None:
        found[heading] = '\n'.join(body)
    return found


def _section_starting(sections, prefix):
    """The body of the one section whose heading starts with `prefix`."""
    matches = [h for h in sections if h.startswith(prefix)]
    assert len(matches) == 1, (
        f"expected exactly one section headed {prefix!r}, found {matches}")
    return sections[matches[0]]


def _repo_paths(text):
    """Backticked tokens that name a repository path, template tokens aside.

    A token carrying `<`, `>` or `*` is a template or a glob (for instance
    `proof_plugins_<framework>.md`) and names no single file, so it is not a
    path the checklist can be held to.
    """
    named = set()
    for token in re.findall(r'`([^`\n]+)`', text):
        if '/' not in token:
            continue
        if set('<>*') & set(token):
            continue
        if re.fullmatch(r'[A-Za-z0-9_./-]+', token):
            named.add(token)
    return named


class TestTheChecklistNamesEveryWiringSite:
    """purlin_references RULE-30."""

    @pytest.mark.proof("purlin_references", "PROOF-30", "RULE-30")
    def test_wiring_list_names_every_site_and_every_path_exists(self):
        wiring = _section_starting(_sections(_read(CONTRACT)), 'B.')
        named = _repo_paths(wiring)

        missing = sorted(site for site in WIRING_SITES if site not in named)
        assert not missing, (
            "the contract's wiring list does not name "
            f"{missing}. A framework is wired into that site from memory or "
            "not at all, which is how a plugin ships half wired: selectable "
            "in one file and unknown to the hook that runs it")

        gone = sorted(p for p in named
                      if not os.path.exists(os.path.join(PROJECT_ROOT, p)))
        assert not gone, (
            f"the wiring list names paths that do not exist: {gone}. A "
            "checklist that outlived the tree it describes sends the next "
            "author to a file that moved")

        # The scan read a real list, not an empty one.
        assert len(named) >= len(WIRING_SITES), (
            f"only {sorted(named)} were read out of section B; the parser is "
            "not seeing the checklist it claims to check")


class TestEveryRequirementRowCitesARealRule:
    """purlin_references RULE-31."""

    @pytest.mark.proof("purlin_references", "PROOF-31", "RULE-31")
    def test_requirement_rows_and_anchor_rules_are_the_same_set(self):
        requirements = _section_starting(_sections(_read(CONTRACT)), 'A.')
        cited = set()
        for line in requirements.split('\n'):
            if not line.startswith('|'):
                continue
            first_cell = line.strip('|').split('|')[0].strip().strip('`')
            if re.fullmatch(r'RULE-\d+', first_cell):
                cited.add(first_cell)

        anchored = set(re.findall(r'^- (RULE-\d+):', _read(ANCHOR), re.M))

        assert len(anchored) >= 25, (
            f"only {len(anchored)} rules were read from {ANCHOR}; the anchor "
            "parser is not seeing the contract it grades against")

        uncovered = sorted(anchored - cited,
                           key=lambda r: int(r.split('-')[1]))
        assert not uncovered, (
            f"proof_common carries {uncovered} with no row in the contract's "
            "requirement table. A rule the checklist does not mention is one "
            "a plugin author never reads")

        invented = sorted(cited - anchored,
                          key=lambda r: int(r.split('-')[1]))
        assert not invented, (
            f"the requirement table cites {invented}, which "
            "specs/_anchors/proof_common.md does not carry. A row citing no "
            "rule is a requirement nothing proves")


class TestProofsFormatDocumentsTheRunMarker:
    """purlin_references RULE-32."""

    @pytest.mark.proof("purlin_references", "PROOF-32", "RULE-32")
    def test_run_marker_section_names_the_rule_19_fields(self):
        text = _read(PROOFS_FORMAT)
        first_line = text.split('\n', 1)[0]
        assert first_line.startswith('> Format-Version: '), (
            "proofs_format.md must open with a > Format-Version: line, got "
            f"{first_line!r}")
        version = int(first_line.split(':', 1)[1].strip())
        assert version >= 6, (
            "the run-marker section is a structural addition, so "
            f"proofs_format.md is at least Format-Version 6, not {version}")

        sections = _sections(text)
        assert 'Run marker' in sections, (
            "proofs_format.md must carry a `## Run marker` section: a "
            f"consumer reading only {sorted(sections)} concludes a plugin "
            "writes proof files and nothing else, and every receipt issued "
            "in that project records evidence.test_run as null")
        body = sections['Run marker']

        assert '.purlin/runtime/test_run.json' in body, \
            "the run-marker section must name the marker's path"

        absent = [f for f in RUN_MARKER_FIELDS if f'`{f}`' not in body]
        assert not absent, (
            f"the run-marker section does not name {absent} as fields. A "
            "field a plugin author cannot read here is one every plugin "
            "spells differently")

        assert '`skipped_proofs`' in body, \
            "the run-marker section must document the skipped_proofs key"
        shape = '{' + ', '.join(SKIPPED_PROOF_FIELDS) + '}'
        assert shape in body, (
            f"the section must give a skipped_proofs object its shape, {shape}"
            ": a reader who has to guess the field names writes a marker no "
            "other plugin can merge with")

        assert 'merged into it' in body and 'starts a new marker' in body, (
            "the section must state the merge rule: a run at the same commit "
            "merges into the existing marker, any other commit starts a new "
            "one, because a count carried across commits describes two trees")
        assert 'temp file' in body and 'replac' in body and 'process' in body, (
            "the section must state that the marker is written through a temp "
            "file named for the writing process and replaced in one operation")
