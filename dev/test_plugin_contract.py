"""The proof-plugin contract is complete and current.

`references/proof_plugin_contract.md` is the reader-facing checklist for a
proof plugin. It is useful only while three things hold, and each is checked
here:

  1. its wiring list names every file a new framework has to be wired into, and
     every path it names still exists;
  2. `references/formats/proofs_format.md` documents the runtime proof file the
     plugins actually write, and says which fields it no longer carries;
  3. every framework its per-framework table registers reaches a free-check
     reader, so no shipped language is a hole in the quality gate.

A checklist that has drifted from the tree is worse than none: it reads as
authoritative and sends the next author to a file that moved.
"""

import os
import re
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'review'))
import static_checks  # noqa: E402
from static_checks import analyze_test_file  # noqa: E402

CONTRACT = os.path.join(PROJECT_ROOT, 'references', 'proof_plugin_contract.md')
PROOFS_FORMAT = os.path.join(
    PROJECT_ROOT, 'references', 'formats', 'proofs_format.md')
FRAMEWORKS_REF = os.path.join(
    PROJECT_ROOT, 'references', 'supported_frameworks.md')

# Every file a framework has to be named in before a project can select it, a
# run can execute it and the free checks can grade it. Each entry is a site a
# half-wired framework breaks.
WIRING_SITES = (
    'scripts/proof/',
    'references/supported_frameworks.md',
    'scripts/mcp/purlin/frameworks.py',
    'scripts/run/purlin_run.py',
    'scripts/init/scaffold.py',
    'skills/init/SKILL.md',
    'skills/test/SKILL.md',
    'docs/running-and-records.md',
    'references/formats/proofs_format.md',
    'scripts/review/static_checks.py',
)

# The seven fields a proof entry carries, and the three it no longer does.
PROOF_FIELDS = ('feature', 'id', 'rule', 'test_file', 'test_name', 'status',
                'tier')

# The six plugins Purlin ships. A framework quietly dropped from the contract's
# per-framework table would otherwise take its checker requirement with it, so
# the set is pinned here rather than read from the table it grades.
SHIPPED_FRAMEWORKS = ('pytest', 'jest', 'vitest', 'shell', 'xunit', 'sql')

# The feature name every fixture below marks. Short and unique, so a marker
# cannot match some other fixture in the same temp project.
FIXTURE_FEATURE = 'contractfeat'

# One JS/TS body serves every extension the two JS plugins emit: the checker is
# the same, and the point is that each extension reaches it.
_JS_FIXTURE = ('it("a tautology [proof:contractfeat:PROOF-1:RULE-1]", () => {\n'
               '  expect(true).toBe(true);\n'
               '});\n')

# A marked, tautological test per extension: the marker is the one the
# framework's own plugin reads, and the body is a tautology that language's
# checker is documented to catch.
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
    '.sql': ('-- @purlin contractfeat PROOF-1 RULE-1 unit\n'
             '-- Test: a tautology\n'
             "SELECT CASE WHEN 1 = 1 THEN 'PASS' ELSE 'FAIL' END;\n"),
}


def _read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def _sections(text):
    """`{heading: body}` for every `## ` heading in a markdown file."""
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
        'expected exactly one section headed %r, found %s' % (prefix, matches))
    return sections[matches[0]]


def _framework_table(section):
    """The per-framework table, as `{framework: row cells}`.

    The one table in the section whose header names the extension column.
    Cells are returned stripped, with backticks left in place so the extension
    column can be split on them.
    """
    rows = [line.strip() for line in section.split('\n')
            if line.strip().startswith('|')]
    header = next((r for r in rows if 'Test extensions' in r), None)
    assert header is not None, (
        'the contract carries no per-framework table: no row names a '
        '`Test extensions` column, so there is nothing saying which language '
        'each shipped plugin registered')
    start = rows.index(header)
    parsed = {}
    for row in rows[start + 1:]:
        cells = [c.strip() for c in row.strip('|').split('|')]
        if len(cells) < 4 or set(cells[0]) <= set('- :'):
            continue
        parsed[cells[0].strip('`')] = cells
    return parsed


def framework_table():
    """The contract's per-framework table, as `{framework: cells}`."""
    return _framework_table(_section_starting(_sections(_read(CONTRACT)), 'B.'))


def _extensions(cell):
    """The backticked `.ext` tokens of a Test extensions cell, in order."""
    return [t for t in re.findall(r'`([^`\n]+)`', cell) if t.startswith('.')]


def _repo_paths(text):
    """Backticked tokens that name a repository path, template tokens aside.

    A token carrying `<`, `>` or `*` is a template or a glob and names no
    single file, so it is not a path the checklist can be held to.
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

    @pytest.mark.proof("purlin_references", "PROOF-30", "RULE-30")
    def test_wiring_list_names_every_site_and_every_path_exists(self):
        wiring = _section_starting(_sections(_read(CONTRACT)), 'B.')
        named = _repo_paths(wiring)

        missing = sorted(site for site in WIRING_SITES if site not in named)
        assert not missing, (
            "the contract's wiring list does not name %s. A framework is "
            'wired into that site from memory or not at all, which is how a '
            'plugin ships half wired: selectable in one file and unknown to '
            'the run script that executes it' % missing)

        gone = sorted(p for p in named
                      if not os.path.exists(os.path.join(PROJECT_ROOT, p)))
        assert not gone, (
            'the wiring list names paths that do not exist: %s. A checklist '
            'that outlived the tree it describes sends the next author to a '
            'file that moved' % gone)

        assert len(named) >= len(WIRING_SITES), (
            'only %s were read out of section B; the parser is not seeing the '
            'checklist it claims to check' % sorted(named))

    def test_the_contract_cites_no_path_a_consumer_checkout_lacks(self):
        """A consumer carries no `dev/` and none of this repository's specs.

        A reference that names one is an instruction nobody outside this
        checkout can follow.
        """
        text = _read(CONTRACT)
        assert 'dev/' not in text
        assert 'specs/_anchors/' not in text
        assert 'specs/proof/' not in text


class TestProofsFormatDocumentsTheRuntimeFile:

    @pytest.mark.proof("purlin_references", "PROOF-32", "RULE-32")
    @pytest.mark.proof("run_script", "PROOF-45", "RULE-36")
    def test_the_format_names_the_runtime_location_and_the_seven_fields(self):
        text = _read(PROOFS_FORMAT)
        first_line = text.split('\n', 1)[0]
        assert first_line.startswith('> Format-Version: '), (
            'proofs_format.md must open with a > Format-Version: line, got %r'
            % first_line)
        version = int(first_line.split(':', 1)[1].strip())
        assert version >= 8, (
            'moving the proof file to the runtime directory and dropping the '
            'operating-system fields is structural, so proofs_format.md is at '
            'least Format-Version 8, not %d' % version)

        sections = _sections(text)
        assert 'Location' in sections
        assert '.purlin/runtime/proofs/<feature>.<tier>.json' \
            in sections['Location']
        assert 'gitignored' in sections['Location']

        fields = sections['Fields']
        absent = [f for f in PROOF_FIELDS if '`proofs[].%s`' % f not in fields]
        assert not absent, (
            'the fields table does not name %s. A field a plugin author '
            'cannot read here is one every plugin spells differently' % absent)
        assert 'Seven fields, and no eighth' in fields

    @pytest.mark.proof("run_script", "PROOF-45", "RULE-36")
    def test_the_retired_fields_are_listed_as_retired(self):
        fields = _sections(_read(PROOFS_FORMAT))['Fields']
        assert 'Retired field' in fields
        assert 'test_run.json' in fields, (
            'the run marker is gone and the format must say so: a reader who '
            'finds no mention concludes their plugin should still write one')
        assert '@env(windows)' in fields

    @pytest.mark.proof("run_script", "PROOF-45", "RULE-36")
    def test_the_format_carries_no_run_marker_section(self):
        assert 'Run marker' not in _sections(_read(PROOFS_FORMAT))

    @pytest.mark.proof("run_script", "PROOF-45", "RULE-36")
    def test_every_shipped_framework_has_a_marker_section(self):
        text = _read(PROOFS_FORMAT)
        for framework in SHIPPED_FRAMEWORKS:
            assert '| %s |' % framework in text, (
                '%s has no row in the feature-name token table, so '
                'purlin:rename walks past its markers' % framework)
        for gone in ('phpunit', '| c |'):
            assert gone not in text, gone


class TestTheFrameworkReferenceMatchesTheDetectors:

    @pytest.mark.proof("run_script", "PROOF-46", "RULE-37")
    def test_the_reference_lists_the_six_shipped_frameworks(self):
        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
        from purlin import frameworks

        text = _read(FRAMEWORKS_REF)
        first_line = text.split('\n', 1)[0]
        assert int(first_line.split(':', 1)[1].strip()) >= 8
        assert set(frameworks.KNOWN_FRAMEWORKS) == set(SHIPPED_FRAMEWORKS)
        for framework in SHIPPED_FRAMEWORKS:
            assert 'scripts/proof/' in text
            assert framework in text.lower()
        for gone in ('phpunit_purlin', 'c_purlin'):
            assert gone not in text, gone

    @pytest.mark.proof("run_script", "PROOF-46", "RULE-37")
    def test_every_row_carries_a_runner_setup_cell(self):
        table = _sections(_read(FRAMEWORKS_REF))['Built-in Plugins']
        rows = [line for line in table.split('\n')
                if line.strip().startswith('|')]
        body = [r for r in rows[2:] if r.strip().startswith('|')]
        assert len(body) == len(SHIPPED_FRAMEWORKS), body
        for row in body:
            cells = [c.strip() for c in row.strip().strip('|').split('|')]
            assert cells[-1], (
                'a framework with no setup cell filled in is one a scaffolded '
                'workflow cannot run: %s' % row)


class TestEveryFrameworkHasAFreeCheckReader:

    @pytest.mark.proof("purlin_references", "PROOF-33", "RULE-33")
    def test_every_registered_extension_is_graded(self):
        table = framework_table()

        assert set(table) == set(SHIPPED_FRAMEWORKS), (
            'the per-framework table lists %s, not %s. A framework dropped '
            'from the table takes its checker requirement with it, and this '
            'test would then grade a language Purlin no longer claims to '
            'cover instead of failing'
            % (sorted(table), sorted(SHIPPED_FRAMEWORKS)))

        listed = {}
        for framework, cells in sorted(table.items()):
            exts = _extensions(cells[2])
            assert exts, (
                '%s: the table names no test extension, so nothing says which '
                'files its checker has to read' % framework)
            for ext in exts:
                assert static_checks._CHECKERS.get(ext) is not None, (
                    '%s: %s reaches no checker, so a test in that language is '
                    'never graded and `assert true` in it passes a gate that '
                    'fails it in every other language' % (framework, ext))
                listed[ext] = framework

        assert set(listed) == set(TAUTOLOGY_FIXTURES), (
            'the table registers %s with no fixture here, and this test '
            'carries fixtures for %s the table does not register: an '
            'extension nothing drives is a checker claim nobody ran'
            % (sorted(set(listed) - set(TAUTOLOGY_FIXTURES)),
               sorted(set(TAUTOLOGY_FIXTURES) - set(listed))))

        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, 'tests'))
            for ext in sorted(listed):
                framework = listed[ext]
                rel = 'tests/fixture' + ext
                path = os.path.join(root, *rel.split('/'))
                with open(path, 'w', encoding='utf-8') as handle:
                    handle.write(TAUTOLOGY_FIXTURES[ext])

                results = analyze_test_file(path, FIXTURE_FEATURE)
                assert len(results) == 1, (
                    '%s %s: the checker found %d proofs in a file carrying '
                    'one marker: %s' % (framework, ext, len(results), results))
                assert results[0]['status'] == 'fail', (
                    '%s %s: a marked tautology was graded %s rather than '
                    'flagged, so the registered framework is a hole in the '
                    'quality gate' % (framework, ext, results[0]))
                assert results[0]['check'], (
                    '%s %s: the flagged result names no check, so nothing '
                    'says why it failed' % (framework, ext))

    @pytest.mark.proof("run_script", "PROOF-46", "RULE-37")
    def test_shell_is_the_one_language_with_no_extractor(self):
        assert '.sh' not in static_checks._TEST_CODE_EXTENSIONS
        assert set(static_checks._TEST_CODE_EXTENSIONS) \
            == set(TAUTOLOGY_FIXTURES) - {'.sh'}
