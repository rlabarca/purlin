"""Unit tests for tools/cdd/invariant.py.

Tests cover:
  a. Invariant file detection (is_invariant_node) with all type prefixes
  b. Prefix stripping and anchor type extraction
  c. Metadata extraction with early termination
  d. Content hash computation and comparison
  e. Format validation (missing fields, missing sections, type-specific checks)
  f. Prodbrief section detection (User Stories + Success Criteria)
"""

import os
import shutil
import tempfile
import unittest

from tools.cdd.invariant import (
    ANCHOR_PREFIXES,
    INVARIANT_PREFIX,
    compute_content_hash,
    extract_metadata,
    get_anchor_type,
    is_anchor_node,
    is_invariant_node,
    strip_invariant_prefix,
    validate_invariant,
)


class TestIsInvariantNode(unittest.TestCase):
    """Tests for is_invariant_node()."""

    def test_all_invariant_prefixes(self):
        """Each anchor type with i_ prefix is detected as invariant."""
        for prefix in ANCHOR_PREFIXES:
            filename = f"i_{prefix}example.md"
            self.assertTrue(
                is_invariant_node(filename),
                f"Expected {filename} to be an invariant node",
            )

    def test_regular_anchors_are_not_invariants(self):
        """Regular anchor files (no i_ prefix) are not invariants."""
        for prefix in ANCHOR_PREFIXES:
            filename = f"{prefix}example.md"
            self.assertFalse(
                is_invariant_node(filename),
                f"Expected {filename} to NOT be an invariant node",
            )

    def test_regular_features_are_not_invariants(self):
        """Normal feature files are not invariants."""
        self.assertFalse(is_invariant_node("my_feature.md"))
        self.assertFalse(is_invariant_node("pl_build.md"))

    def test_invalid_invariant_prefix(self):
        """i_ followed by a non-anchor prefix is not an invariant."""
        self.assertFalse(is_invariant_node("i_unknown_thing.md"))
        self.assertFalse(is_invariant_node("i_my_feature.md"))

    def test_companion_files_not_invariants(self):
        """Companion and discovery files are not invariants."""
        self.assertFalse(is_invariant_node("i_arch_api.impl.md"))
        self.assertFalse(is_invariant_node("i_policy_sec.discoveries.md"))


class TestStripInvariantPrefix(unittest.TestCase):
    """Tests for strip_invariant_prefix()."""

    def test_strips_prefix(self):
        self.assertEqual(strip_invariant_prefix("i_arch_api.md"), "arch_api.md")
        self.assertEqual(strip_invariant_prefix("i_policy_gdpr.md"), "policy_gdpr.md")
        self.assertEqual(strip_invariant_prefix("i_ops_cicd.md"), "ops_cicd.md")
        self.assertEqual(strip_invariant_prefix("i_prodbrief_q2.md"), "prodbrief_q2.md")
        self.assertEqual(strip_invariant_prefix("i_design_visual.md"), "design_visual.md")

    def test_no_strip_for_non_invariant(self):
        self.assertEqual(strip_invariant_prefix("arch_api.md"), "arch_api.md")
        self.assertEqual(strip_invariant_prefix("my_feature.md"), "my_feature.md")


class TestGetAnchorType(unittest.TestCase):
    """Tests for get_anchor_type()."""

    def test_invariant_types(self):
        self.assertEqual(get_anchor_type("i_arch_api.md"), "arch_")
        self.assertEqual(get_anchor_type("i_policy_gdpr.md"), "policy_")
        self.assertEqual(get_anchor_type("i_ops_cicd.md"), "ops_")
        self.assertEqual(get_anchor_type("i_prodbrief_q2.md"), "prodbrief_")
        self.assertEqual(get_anchor_type("i_design_visual.md"), "design_")

    def test_regular_anchor_types(self):
        self.assertEqual(get_anchor_type("arch_data.md"), "arch_")
        self.assertEqual(get_anchor_type("design_visual.md"), "design_")
        self.assertEqual(get_anchor_type("policy_security.md"), "policy_")
        self.assertEqual(get_anchor_type("ops_deploy.md"), "ops_")
        self.assertEqual(get_anchor_type("prodbrief_goals.md"), "prodbrief_")

    def test_non_anchor_returns_none(self):
        self.assertIsNone(get_anchor_type("my_feature.md"))
        self.assertIsNone(get_anchor_type("pl_build.md"))


class TestIsAnchorNode(unittest.TestCase):
    """Tests for is_anchor_node() — covers all prefixes including invariants."""

    def test_all_anchor_types(self):
        for prefix in ANCHOR_PREFIXES:
            self.assertTrue(is_anchor_node(f"{prefix}example.md"))
            self.assertTrue(is_anchor_node(f"i_{prefix}example.md"))

    def test_non_anchors(self):
        self.assertFalse(is_anchor_node("my_feature.md"))
        self.assertFalse(is_anchor_node("pl_build.md"))


class TestExtractMetadata(unittest.TestCase):
    """Tests for extract_metadata()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_invariant_meta_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, filename, content):
        path = os.path.join(self.tmpdir, filename)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_full_metadata_extraction(self):
        path = self._write("i_arch_api.md", """\
# Architecture: API Standards

> Label: "Architecture: API Standards"
> Category: "Architecture"
> Format-Version: 1.0
> Invariant: true
> Version: 2.1.0
> Source: https://github.com/org/standards
> Source-Path: features/arch_api.md
> Source-SHA: abc123def456
> Synced-At: 2026-03-28T14:00:00Z
> Scope: global

## Purpose

Defines API standards.
""")
        meta = extract_metadata(path)
        self.assertEqual(meta["Label"], "Architecture: API Standards")
        self.assertEqual(meta["Format-Version"], "1.0")
        self.assertEqual(meta["Invariant"], "true")
        self.assertEqual(meta["Version"], "2.1.0")
        self.assertEqual(meta["Source"], "https://github.com/org/standards")
        self.assertEqual(meta["Scope"], "global")

    def test_early_termination(self):
        """Metadata extraction stops at first non-metadata content line."""
        path = self._write("i_policy_sec.md", """\
# Policy: Security

> Invariant: true
> Version: 1.0.0

## Purpose

This is body text.
> This line should NOT be extracted.
""")
        meta = extract_metadata(path)
        self.assertIn("Invariant", meta)
        self.assertIn("Version", meta)
        # Body lines should not appear.
        self.assertNotIn("This line should NOT be extracted.", meta.values())

    def test_missing_file(self):
        meta = extract_metadata("/nonexistent/path.md")
        self.assertEqual(meta, {})


class TestComputeContentHash(unittest.TestCase):
    """Tests for compute_content_hash()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_invariant_hash_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_consistent_hash(self):
        path = os.path.join(self.tmpdir, "test.md")
        with open(path, "w") as f:
            f.write("Hello, invariant!")
        h1 = compute_content_hash(path)
        h2 = compute_content_hash(path)
        self.assertIsNotNone(h1)
        self.assertEqual(h1, h2)

    def test_different_content_different_hash(self):
        path1 = os.path.join(self.tmpdir, "a.md")
        path2 = os.path.join(self.tmpdir, "b.md")
        with open(path1, "w") as f:
            f.write("content A")
        with open(path2, "w") as f:
            f.write("content B")
        self.assertNotEqual(compute_content_hash(path1), compute_content_hash(path2))

    def test_missing_file_returns_none(self):
        self.assertIsNone(compute_content_hash("/nonexistent/file.md"))


class TestValidateInvariant(unittest.TestCase):
    """Tests for validate_invariant()."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_invariant_validate_")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, filename, content):
        path = os.path.join(self.tmpdir, filename)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_valid_arch_invariant(self):
        path = self._write("i_arch_api.md", """\
# Architecture: API Standards

> Format-Version: 1.0
> Invariant: true
> Version: 2.1.0
> Source: https://github.com/org/repo
> Source-Path: features/arch_api.md
> Source-SHA: abc123
> Synced-At: 2026-03-28T14:00:00Z
> Scope: global

## Purpose

API standards.

## Architecture Invariants

- INV-1 All APIs use REST.
""")
        issues = validate_invariant(path)
        self.assertEqual(issues, [])

    def test_missing_metadata(self):
        path = self._write("i_policy_sec.md", """\
# Policy: Security

> Invariant: true

## Purpose

Security policy.

## Security Invariants

- INV-1 No eval.
""")
        issues = validate_invariant(path)
        # Should flag missing Format-Version, Version, Source, Scope.
        missing_fields = [i for i in issues if "missing required metadata" in i]
        self.assertGreaterEqual(len(missing_fields), 3)

    def test_invalid_scope(self):
        path = self._write("i_ops_cicd.md", """\
# Ops: CICD

> Format-Version: 1.0
> Invariant: true
> Version: 1.0.0
> Source: https://github.com/org/repo
> Source-Path: features/ops_cicd.md
> Source-SHA: abc123
> Synced-At: 2026-03-28T14:00:00Z
> Scope: invalid_scope

## Purpose

CICD pipeline.

## Operational Invariants

- INV-1 All deploys pass CI.
""")
        issues = validate_invariant(path)
        scope_issues = [i for i in issues if "Scope" in i and "must be" in i]
        self.assertEqual(len(scope_issues), 1)

    def test_format_version_too_new(self):
        path = self._write("i_arch_data.md", """\
# Architecture: Data

> Format-Version: 99.0
> Invariant: true
> Version: 1.0.0
> Source: https://github.com/org/repo
> Source-Path: features/arch_data.md
> Source-SHA: abc123
> Synced-At: 2026-03-28T14:00:00Z
> Scope: scoped

## Purpose

Data standards.

## Data Invariants

- INV-1 Use schemas.
""")
        issues = validate_invariant(path)
        version_issues = [i for i in issues if "Format-Version" in i and "exceeds" in i]
        self.assertEqual(len(version_issues), 1)

    def test_prodbrief_sections(self):
        """Prodbrief invariants need Purpose + User Stories + Success Criteria."""
        path = self._write("i_prodbrief_q2.md", """\
# Product Brief: Q2 Goals

> Format-Version: 1.0
> Invariant: true
> Version: 1.0.0
> Source: https://github.com/org/briefs
> Source-Path: features/prodbrief_q2.md
> Source-SHA: abc123
> Synced-At: 2026-03-28T14:00:00Z
> Scope: global

## Purpose

Q2 product goals.

## User Stories

- As a user, I want to...

## Success Criteria

- KPI-1 Onboarding < 2 minutes
""")
        issues = validate_invariant(path)
        self.assertEqual(issues, [], f"Expected no issues, got: {issues}")

    def test_prodbrief_missing_sections(self):
        """Prodbrief without User Stories or Success Criteria should fail."""
        path = self._write("i_prodbrief_q3.md", """\
# Product Brief: Q3 Goals

> Format-Version: 1.0
> Invariant: true
> Version: 1.0.0
> Source: https://github.com/org/briefs
> Source-Path: features/prodbrief_q3.md
> Source-SHA: abc123
> Synced-At: 2026-03-28T14:00:00Z
> Scope: scoped

## Purpose

Q3 goals.
""")
        issues = validate_invariant(path)
        section_issues = [i for i in issues if "missing required section" in i]
        self.assertGreaterEqual(len(section_issues), 1)

    def test_figma_sourced_invariant(self):
        """Figma-sourced invariant needs Figma-URL and Synced-At."""
        path = self._write("i_design_visual.md", """\
# Design: Visual Standards

> Format-Version: 1.0
> Invariant: true
> Version: v456
> Source: figma
> Figma-URL: https://figma.com/file/abc123
> Synced-At: 2026-03-28T14:00:00Z
> Scope: global

## Purpose

Design system.

## Figma Source

This invariant is governed by the Figma document linked above.
""")
        issues = validate_invariant(path)
        self.assertEqual(issues, [], f"Expected no issues, got: {issues}")

    def test_non_invariant_file(self):
        """A file without i_ prefix or invalid anchor type returns an error."""
        path = self._write("my_feature.md", "# Feature\n")
        issues = validate_invariant(path)
        self.assertEqual(len(issues), 1)
        self.assertIn("not an invariant file", issues[0])


if __name__ == "__main__":
    unittest.main()
