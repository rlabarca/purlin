#!/usr/bin/env python3
"""Automated tests for the /pl-design-audit skill.

Verifies the underlying operations: inventory scanning, reference integrity,
staleness detection, anchor consistency, unprocessed artifact detection, and
clean audit path.

Produces tests/pl_design_audit/tests.json at project root.
"""

import calendar
import json
import os
import re
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'critic'))

from critic import parse_visual_spec, validate_visual_references


# ---------------------------------------------------------------------------
# Anchor consistency helpers — scan descriptions for hardcoded values
# ---------------------------------------------------------------------------

def extract_anchor_tokens(anchor_content):
    """Extract design token name-value pairs from a design anchor file.

    Parses tables with | Token | Value | rows and extracts --token-name → value
    mappings.  Also extracts font family names from font token values.
    """
    tokens = {}  # token_name -> value (e.g. "--purlin-accent" -> "#38BDF8")
    fonts = {}   # font_name -> token_name (e.g. "Montserrat" -> "--font-display")

    # Match table rows: | `--token-name` | `#HEX` | or | `--token` | `'Font', sans-serif` |
    token_re = re.compile(
        r'\|\s*`(--[\w-]+)`\s*\|\s*`([^`]+)`'
    )
    for m in token_re.finditer(anchor_content):
        token_name = m.group(1)
        token_value = m.group(2).strip()
        tokens[token_name] = token_value

        # Extract font family names from font values like "'Montserrat', sans-serif"
        font_match = re.match(r"'([A-Za-z ]+)'", token_value)
        if font_match:
            fonts[font_match.group(1)] = token_name

    return tokens, fonts


def scan_description_for_hardcoded_values(description, tokens, fonts):
    """Scan a description string for hardcoded hex colors and font names.

    Returns a list of dicts: {"literal": str, "suggestion": str, "type": str}.
    """
    warnings = []

    # Check for hardcoded hex colors that match a token value
    hex_re = re.compile(r'#[0-9A-Fa-f]{6}\b')
    for hex_match in hex_re.finditer(description):
        hex_val = hex_match.group(0).upper()
        for token_name, token_value in tokens.items():
            if token_value.upper() == hex_val:
                warnings.append({
                    "literal": hex_match.group(0),
                    "suggestion": f"var({token_name})",
                    "type": "color",
                })

    # Check for hardcoded font family names
    for font_name, token_name in fonts.items():
        if font_name in description:
            warnings.append({
                "literal": font_name,
                "suggestion": f"var({token_name})",
                "type": "font",
            })

    return warnings


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


class TestInventoryScanDiscoversAllVisualSpecs(unittest.TestCase):
    """Scenario: Inventory Scan Discovers All Visual Specs"""

    def test_scans_features_with_visual_specs(self):
        """Given three feature files with Visual Spec sections and one without,
        parse_visual_spec finds the sections in the three and returns empty for the fourth."""
        with_spec = """## Visual Specification
### Screen: Dashboard
- **Reference:** features/design/test/dash.png
- **Processed:** 2025-01-15
- **Description:** A dashboard layout.
- [ ] Check layout
"""
        without_spec = """## Requirements
Some requirements here.
"""
        result_with = parse_visual_spec(with_spec)
        result_without = parse_visual_spec(without_spec)

        self.assertTrue(result_with["present"])
        self.assertEqual(result_with["screens"], 1)
        self.assertFalse(result_without["present"])
        self.assertEqual(result_without["screens"], 0)

    def test_multiple_features_inventory(self):
        """Inventory scan discovers visual specs across multiple feature files."""
        features = {
            "feature_a.md": "## Visual Specification\n### Screen: A\n- [ ] Check",
            "feature_b.md": "## Visual Specification\n### Screen: B\n- [ ] Check",
            "feature_c.md": "## 4. Visual Specification\n### Screen: C\n- [ ] Check",
            "feature_d.md": "## Requirements\nNo visual spec here.",
        }
        found = []
        for name, content in features.items():
            vs = parse_visual_spec(content)
            if vs["present"]:
                found.append(name)

        self.assertEqual(len(found), 3)
        self.assertNotIn("feature_d.md", found)


class TestMissingLocalReferenceDetected(unittest.TestCase):
    """Scenario: Missing Local Reference Detected"""

    def test_missing_local_file_reported(self):
        """Local reference to a non-existent file produces a missing_design_reference item."""
        content = """## Visual Specification
### Screen: Main
- **Reference:** features/design/my_feature/mockup.png
- **Processed:** 2025-01-15
- **Description:** Layout description.
- [ ] Verify layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            # No mockup.png exists in tmpdir
            items = validate_visual_references(vs, project_root=tmpdir)

        missing = [i for i in items if i["category"] == "missing_design_reference"]
        self.assertEqual(len(missing), 1)
        self.assertEqual(missing[0]["priority"], "MEDIUM")

    def test_existing_local_file_no_missing_item(self):
        """Local reference to an existing file does not produce a missing item."""
        content = """## Visual Specification
### Screen: Main
- **Reference:** features/design/my_feature/mockup.png
- **Processed:** 2025-01-15
- **Description:** Layout description.
- [ ] Verify layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = os.path.join(tmpdir, "features", "design", "my_feature")
            os.makedirs(art_dir)
            with open(os.path.join(art_dir, "mockup.png"), "w") as f:
                f.write("fake image")
            items = validate_visual_references(vs, project_root=tmpdir)

        missing = [i for i in items if i["category"] == "missing_design_reference"]
        self.assertEqual(len(missing), 0)


class TestStaleDescriptionDetected(unittest.TestCase):
    """Scenario: Stale Description Detected"""

    def test_artifact_newer_than_processed_date(self):
        """Artifact modified after processed date produces stale_design_description item."""
        content = """## Visual Specification
### Screen: Dashboard
- **Reference:** features/design/my_feature/dashboard-layout.png
- **Processed:** 2025-01-15
- **Description:** Layout description.
- [ ] Verify layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = os.path.join(tmpdir, "features", "design", "my_feature")
            os.makedirs(art_dir)
            art_path = os.path.join(art_dir, "dashboard-layout.png")
            with open(art_path, "w") as f:
                f.write("fake image")
            # Set mtime to Feb 1, 2025 (after Jan 15, 2025)
            feb_ts = calendar.timegm(datetime(2025, 2, 1, tzinfo=timezone.utc).timetuple())
            os.utime(art_path, (feb_ts, feb_ts))

            items = validate_visual_references(vs, project_root=tmpdir)

        stale = [i for i in items if i["category"] == "stale_design_description"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["priority"], "LOW")

    def test_artifact_older_than_processed_date_not_stale(self):
        """Artifact modified before processed date does not produce stale item."""
        content = """## Visual Specification
### Screen: Dashboard
- **Reference:** features/design/my_feature/dashboard-layout.png
- **Processed:** 2025-03-01
- **Description:** Layout description.
- [ ] Verify layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = os.path.join(tmpdir, "features", "design", "my_feature")
            os.makedirs(art_dir)
            art_path = os.path.join(art_dir, "dashboard-layout.png")
            with open(art_path, "w") as f:
                f.write("fake image")
            # Set mtime to Jan 15, 2025 (before Mar 1, 2025)
            jan_ts = calendar.timegm(datetime(2025, 1, 15, tzinfo=timezone.utc).timetuple())
            os.utime(art_path, (jan_ts, jan_ts))

            items = validate_visual_references(vs, project_root=tmpdir)

        stale = [i for i in items if i["category"] == "stale_design_description"]
        self.assertEqual(len(stale), 0)


class TestUnprocessedArtifactDetected(unittest.TestCase):
    """Scenario: Unprocessed Artifact Detected"""

    def test_reference_without_description_flagged(self):
        """Screen with reference but no description produces unprocessed_artifact item."""
        content = """## Visual Specification
### Screen: Settings
- **Reference:** features/design/my_feature/settings.png
- **Processed:** N/A
- [ ] Check settings layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = os.path.join(tmpdir, "features", "design", "my_feature")
            os.makedirs(art_dir)
            with open(os.path.join(art_dir, "settings.png"), "w") as f:
                f.write("fake image")
            items = validate_visual_references(vs, project_root=tmpdir)

        unprocessed = [i for i in items if i["category"] == "unprocessed_artifact"]
        self.assertEqual(len(unprocessed), 1)
        self.assertEqual(unprocessed[0]["priority"], "HIGH")

    def test_reference_with_description_not_flagged(self):
        """Screen with reference AND description does not produce unprocessed item."""
        content = """## Visual Specification
### Screen: Settings
- **Reference:** features/design/my_feature/settings.png
- **Processed:** 2025-01-15
- **Description:** Settings panel with form fields.
- [ ] Check settings layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = os.path.join(tmpdir, "features", "design", "my_feature")
            os.makedirs(art_dir)
            with open(os.path.join(art_dir, "settings.png"), "w") as f:
                f.write("fake image")
            items = validate_visual_references(vs, project_root=tmpdir)

        unprocessed = [i for i in items if i["category"] == "unprocessed_artifact"]
        self.assertEqual(len(unprocessed), 0)


class TestAnchorConsistencyHardcodedColorWarning(unittest.TestCase):
    """Scenario: Anchor Consistency Hardcoded Color Warning"""

    def test_hardcoded_hex_matches_anchor_token(self):
        """Hardcoded hex color matching an anchor token produces a warning."""
        anchor_content = """## 2. Invariants
### 2.2 Color Token System
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links, focus rings |
| `--purlin-bg` | `#0B131A` | Page background |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        description = "The button uses color #38BDF8 for the accent."

        warnings = scan_description_for_hardcoded_values(description, tokens, fonts)

        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["literal"], "#38BDF8")
        self.assertEqual(warnings[0]["suggestion"], "var(--purlin-accent)")
        self.assertEqual(warnings[0]["type"], "color")

    def test_hardcoded_font_name_matches_anchor_token(self):
        """Hardcoded font name matching an anchor token produces a warning."""
        anchor_content = """## Typography
| Token | Value | Usage |
|-------|-------|-------|
| `--font-display` | `'Montserrat', sans-serif` | Titles |
| `--font-body` | `'Inter', sans-serif` | Body text |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        description = "The heading uses Montserrat at 32px weight 200."

        warnings = scan_description_for_hardcoded_values(description, tokens, fonts)

        font_warnings = [w for w in warnings if w["type"] == "font"]
        self.assertEqual(len(font_warnings), 1)
        self.assertEqual(font_warnings[0]["literal"], "Montserrat")
        self.assertEqual(font_warnings[0]["suggestion"], "var(--font-display)")

    def test_no_hardcoded_values_clean(self):
        """Description with no hardcoded values produces no warnings."""
        anchor_content = """## Color Token System
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        description = "The button uses var(--purlin-accent) for highlighting."

        warnings = scan_description_for_hardcoded_values(description, tokens, fonts)
        self.assertEqual(len(warnings), 0)

    def test_hex_color_not_in_anchor_no_warning(self):
        """Hex color that does NOT match any anchor token produces no warning."""
        anchor_content = """## Color Token System
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        description = "The custom element uses #FF00FF for emphasis."

        warnings = scan_description_for_hardcoded_values(description, tokens, fonts)
        self.assertEqual(len(warnings), 0)

    def test_multiple_hardcoded_values(self):
        """Description with multiple hardcoded values produces multiple warnings."""
        anchor_content = """## Token System
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links |
| `--purlin-bg` | `#0B131A` | Background |
| `--font-display` | `'Montserrat', sans-serif` | Titles |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        description = "Uses #38BDF8 accent on #0B131A background with Montserrat headings."

        warnings = scan_description_for_hardcoded_values(description, tokens, fonts)
        self.assertTrue(len(warnings) >= 3)


class TestCleanAuditReport(unittest.TestCase):
    """Scenario: Clean Audit Report"""

    def test_all_valid_references_no_issues(self):
        """All features with valid references, current descriptions, and no literals
        produce zero action items."""
        content = """## Visual Specification
### Screen: Dashboard
- **Reference:** features/design/test/dash.png
- **Processed:** 2099-12-31
- **Description:** Dashboard uses var(--purlin-accent) for links.
- [ ] Check layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = os.path.join(tmpdir, "features", "design", "test")
            os.makedirs(art_dir)
            art_path = os.path.join(art_dir, "dash.png")
            with open(art_path, "w") as f:
                f.write("fake image")
            # Set mtime well before processed date
            old_ts = calendar.timegm(datetime(2025, 1, 1, tzinfo=timezone.utc).timetuple())
            os.utime(art_path, (old_ts, old_ts))

            items = validate_visual_references(vs, project_root=tmpdir)

        self.assertEqual(len(items), 0, f"Expected zero issues but got: {items}")

    def test_url_references_no_integrity_issues(self):
        """Features with only URL references (Figma, Live) produce no integrity issues."""
        content = """## Visual Specification
### Screen: Figma Screen
- **Reference:** [Figma](https://www.figma.com/file/abc123)
- **Processed:** 2025-01-15
- **Description:** Component layout from Figma.
- [ ] Check component
### Screen: Live Screen
- **Reference:** [Live](https://example.com/dashboard)
- **Processed:** 2025-02-01
- **Description:** Current production view.
- [ ] Check live view
"""
        vs = parse_visual_spec(content)
        items = validate_visual_references(vs)

        missing = [i for i in items if i["category"] == "missing_design_reference"]
        self.assertEqual(len(missing), 0)


# ---------------------------------------------------------------------------
# Test runner and results output
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    total = result.testsRun

    outdir = os.path.join(PROJECT_ROOT, 'tests', 'pl_design_audit')
    os.makedirs(outdir, exist_ok=True)
    status = "PASS" if failed == 0 else "FAIL"
    results = {"status": status, "passed": passed, "failed": failed, "total": total}
    outpath = os.path.join(outdir, 'tests.json')
    with open(outpath, 'w') as f:
        json.dump(results, f)

    print(f"\n{outpath}: {status}")
    sys.exit(0 if failed == 0 else 1)
