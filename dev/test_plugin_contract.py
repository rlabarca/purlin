"""purlin_references: the proof-plugin contract is complete and current.

`references/proof_plugin_contract.md` is the reader-facing checklist for a proof
plugin. It is useful only while three things hold, and each is checked here:

  1. its wiring list names every file a new framework has to be wired into, and
     every path it names still exists;
  2. `references/formats/proofs_format.md` documents the run marker, which is
     the one part of the plugin contract the format file used to omit;
  3. every framework its per-framework table registers reaches a Pass 1 checker
     and a cache-key extractor, so no shipped language is a hole in the
     deterministic quality gate.

The behavioural requirements themselves are not checked here: they are the
rules of `specs/_anchors/proof_common.md`, the contract cites them rather than
restating them, and `purlin_prose` RULE-15 is what keeps that one home.

A checklist that has drifted from the tree is worse than none: it reads as
authoritative and sends the next author to a file that moved.
"""

import os
import re
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'audit'))
import static_checks  # noqa: E402
from static_checks import analyze_test_file  # noqa: E402
CONTRACT = os.path.join(PROJECT_ROOT, 'references', 'proof_plugin_contract.md')
PROOFS_FORMAT = os.path.join(
    PROJECT_ROOT, 'references', 'formats', 'proofs_format.md')
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

# The eight plugins Purlin ships. A framework quietly dropped from the
# contract's per-framework table would otherwise take its checker requirement
# with it, so the set is pinned here rather than read from the table it grades.
SHIPPED_FRAMEWORKS = ('pytest', 'jest', 'vitest', 'shell',
                      'xunit', 'phpunit', 'sql', 'c')

# The feature name every fixture below marks. Short and unique, so a marker
# cannot match some other fixture in the same temp project.
FIXTURE_FEATURE = 'contractfeat'

# One JS/TS body serves every extension the two JS plugins emit: the checker is
# the same, and the point is that each extension reaches it.
_JS_FIXTURE = ('it("a tautology [proof:contractfeat:PROOF-1:RULE-1]", () => {\n'
               '  expect(true).toBe(true);\n'
               '});\n')

# A marked, tautological test per extension: the marker is the one the
# framework's own plugin reads (proofs_format.md), and the body is a tautology
# that language's checker is documented to catch (audit_criteria.md). Anything
# a checker cannot read shows up here as a missing `assert_true`.
TAUTOLOGY_FIXTURES = {
    '.py': ('import pytest\n'
            '\n'
            '\n'
            '@pytest.mark.proof("contractfeat", "PROOF-1", "RULE-1")\n'
            'def test_tautology():\n'
            '    assert True\n'),
    '.js': _JS_FIXTURE,
    '.jsx': _JS_FIXTURE,
    '.mjs': _JS_FIXTURE,
    '.cjs': _JS_FIXTURE,
    '.ts': _JS_FIXTURE,
    '.tsx': _JS_FIXTURE,
    # No test logic before the marker, which is what check_shell reads as a
    # hardcoded pass. Nothing above the marker may carry `test`, `[`, `grep`,
    # `diff` or `||`, or the checker sees an assertion that is not there.
    '.sh': ('#!/bin/sh\n'
            'purlin_proof "contractfeat" "PROOF-1" "RULE-1" pass\n'),
    '.cs': ('using Xunit;\n'
            'namespace Demo {\n'
            '  public class Tests {\n'
            '    [Fact]\n'
            '    [Trait("PurlinProof", "contractfeat:PROOF-1:RULE-1:unit")]\n'
            '    public void TheTest() { Assert.True(true); }\n'
            '  }\n'
            '}\n'),
    '.php': ('<?php\n'
             'class DemoTest {\n'
             '  /** @purlin contractfeat PROOF-1 RULE-1 unit */\n'
             '  public function testTautology() {\n'
             '    $this->assertTrue(true);\n'
             '  }\n'
             '}\n'),
    '.sql': ('-- @purlin contractfeat PROOF-1 RULE-1 unit\n'
             '-- Test: a tautology\n'
             "SELECT CASE WHEN 1 = 1 THEN 'PASS' ELSE 'FAIL' END;\n"),
    '.c': ('#include "c_purlin.h"\n'
           'int main(void) {\n'
           '    purlin_proof("contractfeat", "PROOF-1", "RULE-1", 1,\n'
           '                 "test_tautology", __FILE__, "unit");\n'
           '    return 0;\n'
           '}\n'),
    '.h': ('#include "c_purlin.h"\n'
           'void suite(void) {\n'
           '    purlin_proof("contractfeat", "PROOF-1", "RULE-1", 1,\n'
           '                 "test_tautology", __FILE__, "unit");\n'
           '}\n'),
}


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


def _framework_table(section):
    """The per-framework table of section B, as {framework: row cells}.

    The one table in the section whose header names the extension column. Cells
    are returned stripped, with backticks left in place so the extension column
    can be split on them.
    """
    rows = [line.strip() for line in section.split('\n') if line.strip().startswith('|')]
    header = next((r for r in rows if 'Test extensions' in r), None)
    assert header is not None, (
        "section B carries no per-framework table: no row names a "
        "`Test extensions` column, so there is nothing saying which language "
        "each shipped plugin registered")
    start = rows.index(header)
    parsed = {}
    for row in rows[start + 1:]:
        cells = [c.strip() for c in row.strip('|').split('|')]
        if len(cells) < 5 or set(cells[0]) <= set('- :'):
            continue
        parsed[cells[0].strip('`')] = cells
    return parsed


def framework_table():
    """The contract's section B per-framework table, as {framework: cells}.

    One parser for the shipped set: a proof about which frameworks exist reads
    the same table the checker proof grades, so the two cannot disagree.
    """
    return _framework_table(_section_starting(_sections(_read(CONTRACT)), 'B.'))


def _extensions(cell):
    """The backticked `.ext` tokens of a Test extensions cell, in order."""
    return [t for t in re.findall(r'`([^`\n]+)`', cell) if t.startswith('.')]


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


class TestEveryFrameworkHasACheckerAndAnExtractor:
    """purlin_references RULE-33."""

    @pytest.mark.proof("purlin_references", "PROOF-33", "RULE-33")
    def test_every_registered_extension_is_graded_and_extractable(self):
        table = framework_table()

        assert set(table) == set(SHIPPED_FRAMEWORKS), (
            f"the per-framework table lists {sorted(table)}, not "
            f"{sorted(SHIPPED_FRAMEWORKS)}. A framework dropped from the table "
            "takes its checker requirement with it, and this proof would then "
            "grade a language Purlin no longer claims to cover instead of "
            "failing")

        listed = {}
        for framework, cells in sorted(table.items()):
            exts = _extensions(cells[2])
            assert exts, (
                f"{framework}: the table names no test extension, so nothing "
                "says which files its checker has to read")
            checker_name = cells[3].strip('`')
            checker = getattr(static_checks, checker_name, None)
            assert callable(checker), (
                f"{framework}: the table names {checker_name!r} as its Pass 1 "
                "checker and scripts/audit/static_checks.py defines no such "
                "function")
            for ext in exts:
                assert static_checks._CHECKERS.get(ext) is checker, (
                    f"{framework}: {ext} is not dispatched to {checker_name} by "
                    "the _CHECKERS table, so a test in that language is graded "
                    "unmeasurable and `assert true` passes a gate that fails it "
                    "in every other language")
                listed[ext] = (framework, cells[4].strip().lower())

        assert set(listed) == set(TAUTOLOGY_FIXTURES), (
            f"the table registers {sorted(set(listed) - set(TAUTOLOGY_FIXTURES))} "
            "with no fixture here and this proof carries fixtures for "
            f"{sorted(set(TAUTOLOGY_FIXTURES) - set(listed))} the table does "
            "not register: an extension nothing drives is a checker claim "
            "nobody ran")

        exempt = sorted(ext for ext, (_fw, cell) in listed.items()
                        if not cell.startswith('yes'))
        assert exempt == ['.sh'], (
            f"the extractor column exempts {exempt}; shell is the one "
            "documented exception, and any other language without an extractor "
            "is a grade that survives an edit to the very test it graded")

        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, 'tests'))
            for ext in sorted(listed):
                framework, extractor_cell = listed[ext]
                rel = 'tests/fixture' + ext
                path = os.path.join(root, *rel.split('/'))
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(TAUTOLOGY_FIXTURES[ext])

                results = analyze_test_file(path, FIXTURE_FEATURE)
                assert len(results) == 1, (
                    f"{framework} {ext}: the checker found {len(results)} "
                    f"proofs in a file carrying one marker: {results}")
                assert results[0]['check'] == 'assert_true', (
                    f"{framework} {ext}: a marked tautology was graded "
                    f"{results[0]} rather than assert_true, so the registered "
                    "framework is a hole in the deterministic quality gate")

                body = static_checks._extract_test_code(
                    root, FIXTURE_FEATURE, 'PROOF-1', rel)
                if ext == '.sh':
                    assert body is None, (
                        "shell is the documented no-extractor exception and an "
                        "extractor appeared for it; the exception in "
                        "proof_plugin_contract.md section C is now stale")
                    assert ext not in static_checks._TEST_CODE_EXTENSIONS, \
                        "_TEST_CODE_EXTENSIONS claims shell is extractable"
                else:
                    assert body, (
                        f"{framework} {ext}: no test code entered the cache "
                        f"key (_extract_test_code returned {body!r}), so a "
                        "HOLLOW or STRONG grade for that language survives an "
                        "edit to the very test it graded")
                    assert extractor_cell.startswith('yes'), (
                        f"{framework} {ext}: the table says {extractor_cell!r} "
                        "for a language that does have an extractor")
