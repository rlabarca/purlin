"""Tests for schema_spec_format — 7 rules.

Validates the spec format contract: required sections, rule numbering,
proof references, metadata fields, and heading conventions.
"""

import glob
import json
import os
import re
import shutil
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
import purlin_server


class TestSpecFormatReference:

    @pytest.mark.proof("schema_spec_format", "PROOF-1", "RULE-1")
    def test_format_documents_two_sections(self):
        with open(os.path.join(PROJECT_ROOT, 'references', 'formats', 'spec_format.md')) as f:
            content = f.read()
        # Find the Required Sections area specifically
        req_match = re.search(
            r'## Required Sections\s*\n(.*?)(?=^## |\Z)', content,
            re.MULTILINE | re.DOTALL
        )
        assert req_match, "No '## Required Sections' heading in spec_format.md"
        req_section = req_match.group(1)
        assert '## Rules' in req_section, \
            "'## Rules' not listed in Required Sections"
        assert '## Proof' in req_section, \
            "'## Proof' not listed in Required Sections"


class TestSpecFormatEnforcement:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'test')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, name, content):
        with open(os.path.join(self.spec_dir, f'{name}.md'), 'w') as f:
            f.write(content)

    @pytest.mark.proof("schema_spec_format", "PROOF-2", "RULE-2")
    def test_unnumbered_rule_triggers_warning(self):
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n'
            '- some constraint without RULE-N prefix\n'
            '- RULE-1: A proper rule\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'WARNING' in result
        assert 'not numbered' in result, \
            f"WARNING doesn't mention unnumbered rules: {result}"

    @pytest.mark.proof("schema_spec_format", "PROOF-4", "RULE-4")
    def test_rule_without_proof_shows_uncovered(self):
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n- RULE-1: Must work\n\n'
            '## Proof\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'RULE-1: NO PROOF' in result

    @pytest.mark.proof("schema_spec_format", "PROOF-5", "RULE-5")
    def test_requires_includes_referenced_rules(self):
        # Create an anchor spec
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir)
        with open(os.path.join(anchor_dir, 'base.md'), 'w') as f:
            f.write(
                '# Anchor: base\n\n'
                '## What it does\nBase rules.\n\n'
                '## Rules\n- RULE-1: Base rule\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Test\n'
            )
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '> Requires: base\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n- RULE-1: Own rule\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'base/RULE-1' in result, \
            f"Required spec's rules not included in coverage: {result}"

    @pytest.mark.proof("schema_spec_format", "PROOF-6", "RULE-6")
    def test_scope_metadata_parsed(self):
        # Create a feature with Scope and an anchor with overlapping scope
        # so sync_status exercises the scope in its overlap suggestion
        self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '> Scope: scripts/mcp/purlin_server.py, src/app.py\n\n'
            '## What it does\nTesting.\n\n'
            '## Rules\n- RULE-1: Must work\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        self._write_spec('api_conv', (
            '# Anchor: api_conv\n\n'
            '> Scope: scripts/\n\n'
            '## What it does\nConventions.\n\n'
            '## Rules\n- RULE-1: Conv\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Check\n'
        ), )
        # Verify the scope was correctly parsed as a comma-separated list
        features = purlin_server._scan_specs(self.project_root)
        assert 'test_feat' in features
        scope = features['test_feat']['scope']
        assert scope == ['scripts/mcp/purlin_server.py', 'src/app.py'], \
            f"Scope should be parsed as comma-separated list, got: {scope}"
        # Verify sync_status uses the parsed scope in its output (overlap suggestion)
        result = purlin_server.sync_status(self.project_root)
        assert 'test_feat' in result, "Feature should appear in sync_status output"
        assert 'api_conv' in result and 'scope' in result.lower(), \
            f"sync_status should use scope for overlap suggestion. Got: {result}"


class TestSpecFormatMultilineDescription:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'test')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, name, content):
        path = os.path.join(self.spec_dir, f'{name}.md')
        with open(path, 'w') as f:
            f.write(content)
        return path

    @pytest.mark.proof("schema_spec_format", "PROOF-8", "RULE-8")
    def test_multiline_description_continuation(self):
        """PROOF-8: Description continuation lines joined; Scope not included."""
        spec_path = self._write_spec('test_feat', (
            '# Feature: test_feat\n\n'
            '> Description: First line\n'
            '>   second line\n'
            '> Scope: src/\n\n'
            '## Rules\n'
            '- RULE-1: Must work\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): Test\n'
        ))
        features = purlin_server._scan_specs(self.project_root)
        assert 'test_feat' in features, \
            "test_feat not found in scanned specs"
        desc = features['test_feat'].get('description', '')
        # Description must contain both continuation lines
        assert 'First line' in desc, \
            f"Description missing 'First line': {desc!r}"
        assert 'second line' in desc, \
            f"Description missing 'second line': {desc!r}"
        # Description must NOT contain the Scope field value
        assert 'src/' not in desc, \
            f"Description must not include Scope field value 'src/': {desc!r}"
        # Scope must be parsed independently as its own field
        scope = features['test_feat'].get('scope', [])
        assert scope == ['src/'], \
            f"Scope should be parsed as ['src/'], got: {scope!r}"


class TestSpecFormatConventions:

    @pytest.mark.proof("schema_spec_format", "PROOF-3", "RULE-3")
    def test_all_proof_lines_match_pattern(self):
        spec_files = glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**', '*.md'),
                               recursive=True)
        pattern = re.compile(r'^-\s+PROOF-\d+\s+\(RULE-\d+\)')
        for path in spec_files:
            with open(path) as f:
                content = f.read()
            proof_section = re.search(
                r'^## Proof\s*\n(.*?)(?=^## |\Z)', content,
                re.MULTILINE | re.DOTALL
            )
            if not proof_section:
                continue
            for line in proof_section.group(1).strip().splitlines():
                line = line.strip()
                if line.startswith('- '):
                    assert pattern.match(line), \
                        f"Bad proof line in {path}: {line}"

    @pytest.mark.proof("schema_spec_format", "PROOF-7", "RULE-7")
    def test_spec_headings_use_correct_prefix(self):
        spec_files = glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**', '*.md'),
                               recursive=True)
        valid = re.compile(r'^# (Feature|Anchor): ')
        for path in spec_files:
            with open(path) as f:
                content = f.read()
            headings = re.findall(r'^# .+', content, re.MULTILINE)
            for h in headings:
                assert valid.match(h), \
                    f"Invalid heading in {path}: {h}"


class TestTierTagParsing:
    """RULE-9 / RULE-10: the tag grammar, parsed identically by both modules.

    A trailing @word is only a tag when it is metadata: schema_proof_format
    PROOF-4's description ends "...documents @integration, @e2e, and @windows".
    Both parsers read that as tier=windows and truncated the description at the
    final clause, so a host-runnable proof was classified as platform-gated.

    The grammar has since gained `@on(<platform-id>[, ...])`. purlin_server and
    static_checks each carry `_split_proof_tags` and cannot share it (the MCP
    server does not import the CLI), so every case below runs through both and
    the tuples must agree.
    """

    def _patterns(self):
        import importlib.util, os
        mods = {}
        for name, rel in (('server', 'scripts/mcp/purlin_server.py'),
                          ('checks', 'scripts/audit/static_checks.py')):
            path = os.path.join(os.path.dirname(__file__), '..', rel)
            spec = importlib.util.spec_from_file_location(f'_tt_{name}', path)
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            mods[name] = m
        return mods

    @pytest.mark.proof("schema_spec_format", "PROOF-9", "RULE-9")
    def test_prose_ending_in_at_word_is_not_a_tier_tag(self):
        mods = self._patterns()

        # The two modules are independent and cannot share an import, so the
        # pattern must be character-identical or they will disagree.
        assert mods['server']._TIER_TAG_BODY == mods['checks']._TIER_TAG_BODY, (
            "purlin_server and static_checks must use an identical tier-tag pattern")

        import re as _re
        pat = _re.compile(mods['server']._TIER_TAG_BODY)

        cases = [
            ('Grep the file; verify present @e2e', 'e2e'),
            ('Run it against a database @integration', 'integration'),
            ('Visual layout matches design @manual(dev@example.com, 2026-03-31, a1b2c3d)', 'manual'),
            # Prose that merely ends in an @word — these must NOT be tier tags.
            ('verify `spec_format.md` documents @integration, @e2e, and @windows', None),
            ('Check the documented tiers @integration, @e2e', None),
            ('Accepts either @e2e or @integration', None),
        ]
        for desc, expected in cases:
            m = pat.search(desc)
            got = m.group(1) if m else None
            assert got == expected, f"{desc!r}: tier {got!r}, expected {expected!r}"

        # And the description must survive intact when there is no tag.
        prose = 'verify `spec_format.md` documents @integration, @e2e, and @windows'
        assert pat.sub('', prose).strip() == prose, \
            "a description with no tier tag must not be truncated"

    @pytest.mark.proof("schema_spec_format", "PROOF-9", "RULE-9")
    def test_tier_and_platform_tags_split_identically_in_both_modules(self):
        mods = self._patterns()
        split_srv = mods['server']._split_proof_tags
        split_chk = mods['checks']._split_proof_tags

        # (description, expected tier, expected platforms, expected warning count)
        cases = [
            ('Lock the file @unit @on(windows-2022)', 'unit', ['windows-2022'], 0),
            ('Lock the file @on(windows-2022, macos-14) @integration',
             'integration', ['windows-2022', 'macos-14'], 0),
            # @on alone: the tier defaults to unit.
            ('Lock the file @on(windows)', 'unit', ['windows'], 0),
            # A human stamp is not a platform result: platforms dropped, warned.
            ('Review the layout @manual @on(x)', 'manual', [], 1),
            # Legacy alias: one release of compatibility, with the rewrite named.
            ('Lock the file @windows', 'unit', ['windows'], 1),
            # Prose ending in an @word after a connector is not a tag at all.
            ('verify `spec_format.md` documents @integration, @e2e, and @windows',
             'unit', [], 0),
            # A stamped manual proof keeps working; its args are not platforms.
            ('Visual layout matches design @manual(dev@example.com, 2026-03-31, a1b2c3d)',
             'manual', [], 0),
        ]
        for desc, tier, platforms, n_warnings in cases:
            got = split_srv(desc)
            assert got == split_chk(desc), (
                f"{desc!r}: purlin_server returned {got!r}, "
                f"static_checks returned {split_chk(desc)!r}")
            clean, got_tier, got_platforms, warnings = got
            assert got_tier == tier, f"{desc!r}: tier {got_tier!r}, expected {tier!r}"
            assert got_platforms == platforms, (
                f"{desc!r}: platforms {got_platforms!r}, expected {platforms!r}")
            assert len(warnings) == n_warnings, f"{desc!r}: warnings {warnings!r}"
            if platforms or tier != 'unit' or n_warnings:
                assert ' @' not in clean, (
                    f"{desc!r}: both tags must be stripped, got {clean!r}")

        # The alias warning names the rewrite, so the fix is copy-pasteable.
        _, _, _, warnings = split_srv('Lock the file @windows')
        assert 'write @unit @on(windows)' in warnings[0], warnings

        # The prose case is untouched: no tag, no truncation.
        prose = 'verify `spec_format.md` documents @integration, @e2e, and @windows'
        assert split_srv(prose)[0] == prose, "a description with no tag must not be truncated"

        # Either order is one grammar: the tuple must not depend on tag order.
        assert (split_srv('Lock the file @unit @on(windows-2022)')
                == split_srv('Lock the file @on(windows-2022) @unit'))

    @pytest.mark.proof("schema_spec_format", "PROOF-10", "RULE-10")
    def test_platform_id_charset_rejects_dots_underscores_and_upper_case(self):
        mods = self._patterns()
        split_srv = mods['server']._split_proof_tags
        split_chk = mods['checks']._split_proof_tags

        # windows_2022 violates the charset only by its underscore, so this case
        # is what fails if the pattern is widened to admit `_`.
        for bad in ('Windows_2022', 'ubuntu-24.04', 'windows_2022'):
            desc = f'Lock the file @unit @on({bad})'
            got = split_srv(desc)
            assert got == split_chk(desc), (
                f"{desc!r}: purlin_server returned {got!r}, "
                f"static_checks returned {split_chk(desc)!r}")
            clean, tier, platforms, warnings = got
            assert platforms == [], (
                f"{bad!r} is not [a-z0-9][a-z0-9-]* and must be dropped, got {platforms!r}")
            assert len(warnings) == 1 and bad in warnings[0], (
                f"the warning must name the rejected id: {warnings!r}")
            assert tier == 'unit' and clean == 'Lock the file', got

        # The positive control: a well-formed id passes with no warning, so the
        # rejections above are the charset and not a broken parser.
        desc = 'Lock the file @unit @on(ubuntu-24)'
        assert split_srv(desc) == split_chk(desc) == ('Lock the file', 'unit', ['ubuntu-24'], [])

    @pytest.mark.proof("schema_spec_format", "PROOF-9", "RULE-9")
    def test_real_spec_is_parsed_correctly(self):
        """The spec that exposed this must now parse as untagged."""
        import importlib.util, os
        path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp', 'purlin_server.py')
        spec = importlib.util.spec_from_file_location('_tt_srv2', path)
        srv = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(srv)

        root = os.path.join(os.path.dirname(__file__), '..')
        info = srv._scan_specs(root)['schema_proof_format']
        assert info['proof_tier_by_id'].get('PROOF-4') == 'unit', (
            "PROOF-4 has no tier tag; its prose merely ends in '@windows'")
        assert info['proof_desc_by_id']['PROOF-4'].rstrip().endswith('@windows'), (
            "the description's final clause must not be truncated")
