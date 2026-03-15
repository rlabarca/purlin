#!/usr/bin/env python3
"""Automated tests for the /pl-design-audit skill.

Verifies the underlying operations: inventory scanning, reference integrity,
staleness detection, anchor consistency, unprocessed artifact detection,
brief staleness detection, missing brief warning,
Figma MCP staleness detection, design-spec conflict detection, and
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
from datetime import datetime, date, timezone
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'critic'))

from critic import parse_visual_spec, validate_visual_references


# ---------------------------------------------------------------------------
# Anchor consistency helpers — scan Token Map entries for hardcoded values
# ---------------------------------------------------------------------------

def extract_anchor_tokens(anchor_content):
    """Extract design token name-value pairs from a design anchor file.

    Parses tables with | Token | Value | rows and extracts --token-name -> value
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


def scan_content_for_hardcoded_values(content, tokens, fonts):
    """Scan content (Token Map entries or checklists) for hardcoded hex colors and font names.

    Returns a list of dicts: {"literal": str, "suggestion": str, "type": str}.
    """
    warnings = []

    # Check for hardcoded hex colors that match a token value
    hex_re = re.compile(r'#[0-9A-Fa-f]{6}\b')
    for hex_match in hex_re.finditer(content):
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
        if font_name in content:
            warnings.append({
                "literal": font_name,
                "suggestion": f"var({token_name})",
                "type": "font",
            })

    return warnings


# ---------------------------------------------------------------------------
# Figma MCP helpers — staleness and design-spec conflict detection
# ---------------------------------------------------------------------------

def check_figma_staleness(figma_last_modified, processed_date_str):
    """Check whether a Figma design was modified after the processed date.

    Args:
        figma_last_modified: ISO 8601 datetime string from Figma MCP
            (e.g. "2026-02-20T14:30:00Z").
        processed_date_str: YYYY-MM-DD date string from the Visual Spec's
            ``- **Processed:**`` line.

    Returns:
        dict with keys:
            "stale" (bool): True if Figma was modified after the processed date.
            "figma_date" (str): The Figma last-modified date as YYYY-MM-DD.
            "processed_date" (str): The processed date as-is.
    """
    # Parse the Figma ISO timestamp (may have timezone info)
    figma_dt = datetime.fromisoformat(figma_last_modified.replace("Z", "+00:00"))
    figma_date = figma_dt.date()

    processed_date = date.fromisoformat(processed_date_str)

    return {
        "stale": figma_date > processed_date,
        "figma_date": figma_date.isoformat(),
        "processed_date": processed_date_str,
    }


def detect_design_conflicts(figma_variables, token_map_entries, anchor_tokens):
    """Detect conflicts between Figma design variables and Token Map entries.

    Compares design variable names from Figma MCP against the Token Map
    entries in the Visual Specification.  Flags discrepancies as
    DESIGN_CONFLICT items.

    Args:
        figma_variables: dict of {variable_name: resolved_value} from Figma MCP.
        token_map_entries: dict of {figma_token_name: project_token} from the
            Token Map in the Visual Specification.
        anchor_tokens: dict of {token_name: token_value} from the design anchor.

    Returns:
        list of dicts: {"property": str, "figma_value": str,
                        "spec_value": str, "type": "DESIGN_CONFLICT"}.
    """
    conflicts = []

    # Check for token name mismatches: Token Map references a Figma variable
    # that no longer exists in the Figma design (renamed/removed)
    for map_key, map_value in token_map_entries.items():
        if map_key not in figma_variables:
            conflicts.append({
                "property": f"token ({map_key})",
                "figma_value": "<missing>",
                "spec_value": map_value,
                "type": "DESIGN_CONFLICT",
            })

    # Check for value drift: Figma variable exists but resolved value differs
    # from what the anchor token maps to
    hex_to_token = {}
    for token_name, token_value in anchor_tokens.items():
        if token_value.startswith("#"):
            hex_to_token[token_value.upper()] = token_name

    for var_name, var_value in figma_variables.items():
        if var_name in token_map_entries:
            mapped_project_token = token_map_entries[var_name]
            # Extract the anchor token name from var(--token-name)
            token_match = re.match(r'var\((--[\w-]+)\)', mapped_project_token)
            if token_match:
                anchor_name = token_match.group(1)
                if anchor_name in anchor_tokens:
                    anchor_val = anchor_tokens[anchor_name].upper()
                    figma_val = var_value.upper() if isinstance(var_value, str) else str(var_value)
                    if figma_val.startswith("#") and anchor_val != figma_val:
                        conflicts.append({
                            "property": f"token ({var_name})",
                            "figma_value": var_value,
                            "spec_value": mapped_project_token,
                            "type": "DESIGN_CONFLICT",
                        })

    return conflicts


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
- **Token Map:** `surface` -> `var(--purlin-bg)`
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
- **Token Map:** `surface` -> `var(--purlin-bg)`
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
- **Token Map:** `surface` -> `var(--purlin-bg)`
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


class TestStaleTokenMapDetected(unittest.TestCase):
    """Scenario: Stale Description Detected (now Token Map staleness)"""

    def test_artifact_newer_than_processed_date(self):
        """Artifact modified after processed date produces stale_token_map item."""
        content = """## Visual Specification
### Screen: Dashboard
- **Reference:** features/design/my_feature/dashboard-layout.png
- **Processed:** 2025-01-15
- **Token Map:** `surface` -> `var(--purlin-bg)`
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

        stale = [i for i in items if i["category"] == "stale_token_map"]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0]["priority"], "LOW")

    def test_artifact_older_than_processed_date_not_stale(self):
        """Artifact modified before processed date does not produce stale item."""
        content = """## Visual Specification
### Screen: Dashboard
- **Reference:** features/design/my_feature/dashboard-layout.png
- **Processed:** 2025-03-01
- **Token Map:** `surface` -> `var(--purlin-bg)`
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

        stale = [i for i in items if i["category"] == "stale_token_map"]
        self.assertEqual(len(stale), 0)


class TestUnprocessedArtifactDetected(unittest.TestCase):
    """Scenario: Unprocessed Artifact Detected"""

    def test_reference_without_token_map_flagged(self):
        """Screen with reference but no Token Map produces unprocessed_artifact item."""
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

    def test_reference_with_token_map_not_flagged(self):
        """Screen with reference AND Token Map does not produce unprocessed item."""
        content = """## Visual Specification
### Screen: Settings
- **Reference:** features/design/my_feature/settings.png
- **Processed:** 2025-01-15
- **Token Map:** `surface` -> `var(--purlin-bg)`
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

    def test_hardcoded_hex_in_token_map(self):
        """Token Map entry with hardcoded hex matching an anchor token produces a warning."""
        anchor_content = """## 2. Invariants
### 2.2 Color Token System
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links, focus rings |
| `--purlin-bg` | `#0B131A` | Page background |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        # Token Map entry with literal hex instead of var(--purlin-accent)
        token_map_text = "`accent` -> `#38BDF8`"

        warnings = scan_content_for_hardcoded_values(token_map_text, tokens, fonts)

        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["literal"], "#38BDF8")
        self.assertEqual(warnings[0]["suggestion"], "var(--purlin-accent)")
        self.assertEqual(warnings[0]["type"], "color")

    def test_hardcoded_font_name_in_checklist(self):
        """Checklist item with hardcoded font name matching an anchor token produces a warning."""
        anchor_content = """## Typography
| Token | Value | Usage |
|-------|-------|-------|
| `--font-display` | `'Montserrat', sans-serif` | Titles |
| `--font-body` | `'Inter', sans-serif` | Body text |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        checklist_text = "- [ ] Title uses Montserrat at 32px weight 200"

        warnings = scan_content_for_hardcoded_values(checklist_text, tokens, fonts)

        font_warnings = [w for w in warnings if w["type"] == "font"]
        self.assertEqual(len(font_warnings), 1)
        self.assertEqual(font_warnings[0]["literal"], "Montserrat")
        self.assertEqual(font_warnings[0]["suggestion"], "var(--font-display)")

    def test_no_hardcoded_values_clean(self):
        """Token Map entries with proper token references produce no warnings."""
        anchor_content = """## Color Token System
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        token_map_text = "`accent` -> `var(--purlin-accent)`"

        warnings = scan_content_for_hardcoded_values(token_map_text, tokens, fonts)
        self.assertEqual(len(warnings), 0)

    def test_hex_color_not_in_anchor_no_warning(self):
        """Hex color that does NOT match any anchor token produces no warning."""
        anchor_content = """## Color Token System
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        token_map_text = "`custom` -> `#FF00FF`"

        warnings = scan_content_for_hardcoded_values(token_map_text, tokens, fonts)
        self.assertEqual(len(warnings), 0)

    def test_multiple_hardcoded_values(self):
        """Content with multiple hardcoded values produces multiple warnings."""
        anchor_content = """## Token System
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links |
| `--purlin-bg` | `#0B131A` | Background |
| `--font-display` | `'Montserrat', sans-serif` | Titles |
"""
        tokens, fonts = extract_anchor_tokens(anchor_content)
        content = ("`accent` -> `#38BDF8`\n"
                   "`bg` -> `#0B131A`\n"
                   "- [ ] Title uses Montserrat headings")

        warnings = scan_content_for_hardcoded_values(content, tokens, fonts)
        self.assertTrue(len(warnings) >= 3)


class TestBriefStalenessDetected(unittest.TestCase):
    """Scenario: Brief Staleness Detected"""

    def test_brief_newer_than_processed_flags_stale(self):
        """brief.json with figma_last_modified newer than Processed date flags STALE."""
        content = """## Visual Specification
### Screen: Figma Screen
- **Reference:** [Figma](https://www.figma.com/file/abc123)
- **Processed:** 2026-01-15
- **Token Map:** `primary` -> `var(--purlin-accent)`
- [ ] Check layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create brief.json with figma_last_modified newer than processed date
            brief_dir = os.path.join(tmpdir, "features", "design", "test_feature")
            os.makedirs(brief_dir)
            brief_data = {
                "figma_url": "https://www.figma.com/file/abc123",
                "figma_last_modified": "2026-02-20T14:30:00Z",
                "screens": {},
                "tokens": {}
            }
            with open(os.path.join(brief_dir, "brief.json"), "w") as f:
                json.dump(brief_data, f)

            items = validate_visual_references(
                vs, project_root=tmpdir, feature_stem="test_feature")

        stale = [i for i in items if i["category"] == "stale_token_map"]
        self.assertTrue(len(stale) >= 1)
        # Verify the staleness is from brief.json comparison
        brief_stale = [i for i in stale if "brief.json" in i.get("description", "")]
        self.assertTrue(len(brief_stale) >= 1)

    def test_brief_older_than_processed_not_stale(self):
        """brief.json with figma_last_modified older than Processed date is not stale."""
        content = """## Visual Specification
### Screen: Figma Screen
- **Reference:** [Figma](https://www.figma.com/file/abc123)
- **Processed:** 2026-03-01
- **Token Map:** `primary` -> `var(--purlin-accent)`
- [ ] Check layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_dir = os.path.join(tmpdir, "features", "design", "test_feature")
            os.makedirs(brief_dir)
            brief_data = {
                "figma_url": "https://www.figma.com/file/abc123",
                "figma_last_modified": "2026-01-15T14:30:00Z",
                "screens": {},
                "tokens": {}
            }
            with open(os.path.join(brief_dir, "brief.json"), "w") as f:
                json.dump(brief_data, f)

            items = validate_visual_references(
                vs, project_root=tmpdir, feature_stem="test_feature")

        stale = [i for i in items
                 if i["category"] == "stale_token_map"
                 and "brief.json" in i.get("description", "")]
        self.assertEqual(len(stale), 0)

    def test_brief_staleness_suggests_reprocess(self):
        """Stale brief.json detection provides remediation data."""
        result = check_figma_staleness(
            figma_last_modified="2026-02-20T14:30:00Z",
            processed_date_str="2026-01-15",
        )
        self.assertTrue(result["stale"])
        self.assertIn("figma_date", result)
        self.assertIn("processed_date", result)


class TestMissingBriefWarning(unittest.TestCase):
    """Scenario: Missing Brief Warning"""

    def test_missing_brief_for_figma_feature_produces_warning(self):
        """Missing brief.json for a Figma-referenced feature produces a warning."""
        content = """## Visual Specification
### Screen: Figma Screen
- **Reference:** [Figma](https://www.figma.com/file/abc123)
- **Processed:** 2026-01-15
- **Token Map:** `primary` -> `var(--purlin-accent)`
- [ ] Check layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            # No brief.json created — it's missing
            items = validate_visual_references(
                vs, project_root=tmpdir, feature_stem="test_feature")

        missing_brief = [i for i in items if i["category"] == "missing_brief"]
        self.assertTrue(len(missing_brief) >= 1)
        self.assertIn("brief.json", missing_brief[0]["description"])

    def test_no_missing_brief_when_brief_exists(self):
        """No missing_brief warning when brief.json exists."""
        content = """## Visual Specification
### Screen: Figma Screen
- **Reference:** [Figma](https://www.figma.com/file/abc123)
- **Processed:** 2026-01-15
- **Token Map:** `primary` -> `var(--purlin-accent)`
- [ ] Check layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_dir = os.path.join(tmpdir, "features", "design", "test_feature")
            os.makedirs(brief_dir)
            brief_data = {
                "figma_url": "https://www.figma.com/file/abc123",
                "figma_last_modified": "2026-01-10T14:30:00Z",
                "screens": {},
                "tokens": {}
            }
            with open(os.path.join(brief_dir, "brief.json"), "w") as f:
                json.dump(brief_data, f)

            items = validate_visual_references(
                vs, project_root=tmpdir, feature_stem="test_feature")

        missing_brief = [i for i in items if i["category"] == "missing_brief"]
        self.assertEqual(len(missing_brief), 0)

    def test_no_missing_brief_for_non_figma_feature(self):
        """Non-Figma features do not produce missing_brief warnings."""
        content = """## Visual Specification
### Screen: Local Screen
- **Reference:** features/design/my_feature/mockup.png
- **Processed:** 2026-01-15
- **Token Map:** `surface` -> `var(--purlin-bg)`
- [ ] Check layout
"""
        vs = parse_visual_spec(content)
        with tempfile.TemporaryDirectory() as tmpdir:
            art_dir = os.path.join(tmpdir, "features", "design", "my_feature")
            os.makedirs(art_dir)
            with open(os.path.join(art_dir, "mockup.png"), "w") as f:
                f.write("fake image")
            # Set mtime before processed date to avoid stale artifact
            old_ts = calendar.timegm(datetime(2025, 1, 1, tzinfo=timezone.utc).timetuple())
            os.utime(os.path.join(art_dir, "mockup.png"), (old_ts, old_ts))

            items = validate_visual_references(
                vs, project_root=tmpdir, feature_stem="my_feature")

        missing_brief = [i for i in items if i["category"] == "missing_brief"]
        self.assertEqual(len(missing_brief), 0)


class TestCleanAuditReport(unittest.TestCase):
    """Scenario: Clean Audit Report"""

    def test_all_valid_references_no_issues(self):
        """All features with valid references, current Token Maps, and no literals
        produce zero action items."""
        content = """## Visual Specification
### Screen: Dashboard
- **Reference:** features/design/test/dash.png
- **Processed:** 2099-12-31
- **Token Map:** `surface` -> `var(--purlin-bg)`
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
- **Token Map:** `primary` -> `var(--purlin-accent)`
- [ ] Check component
### Screen: Live Screen
- **Reference:** [Live](https://example.com/dashboard)
- **Processed:** 2025-02-01
- **Token Map:** `surface` -> `var(--purlin-bg)`
- [ ] Check live view
"""
        vs = parse_visual_spec(content)
        items = validate_visual_references(vs)

        missing = [i for i in items if i["category"] == "missing_design_reference"]
        self.assertEqual(len(missing), 0)


class TestFigmaModificationDetectedAsStaleViaMCP(unittest.TestCase):
    """Scenario: Figma Modification Detected as Stale via MCP"""

    def test_figma_modified_after_processed_date_is_stale(self):
        """Figma lastModified after Processed date flags screen as STALE."""
        result = check_figma_staleness(
            figma_last_modified="2026-02-20T14:30:00Z",
            processed_date_str="2026-01-15",
        )
        self.assertTrue(result["stale"])
        self.assertEqual(result["figma_date"], "2026-02-20")
        self.assertEqual(result["processed_date"], "2026-01-15")

    def test_figma_modified_before_processed_date_not_stale(self):
        """Figma lastModified before Processed date is not stale."""
        result = check_figma_staleness(
            figma_last_modified="2026-01-10T08:00:00Z",
            processed_date_str="2026-01-15",
        )
        self.assertFalse(result["stale"])

    def test_figma_modified_same_day_as_processed_not_stale(self):
        """Figma lastModified on the same day as Processed is not stale."""
        result = check_figma_staleness(
            figma_last_modified="2026-01-15T23:59:59Z",
            processed_date_str="2026-01-15",
        )
        self.assertFalse(result["stale"])

    def test_stale_result_suggests_reprocess(self):
        """Stale Figma detection result contains data needed for remediation."""
        result = check_figma_staleness(
            figma_last_modified="2026-03-01T12:00:00Z",
            processed_date_str="2026-01-15",
        )
        self.assertTrue(result["stale"])
        # Remediation needs both dates to display in the report
        self.assertIn("figma_date", result)
        self.assertIn("processed_date", result)


class TestDesignSpecConflictDetectedViaMCP(unittest.TestCase):
    """Scenario: Design-Spec Conflict Detected via MCP"""

    def test_figma_variable_renamed_produces_conflict(self):
        """Token Map maps 'primary' to var(--accent) but Figma variable 'primary'
        has been renamed to 'brand-primary' — produces a DESIGN_CONFLICT."""
        anchor_tokens = {
            "--accent": "#0284C7",
            "--bg": "#F5F6F0",
        }
        # Token Map says primary -> var(--accent)
        token_map_entries = {
            "primary": "var(--accent)",
        }
        # But Figma no longer has "primary" — it's been renamed
        figma_variables = {
            "brand-primary": "#0284C7",
        }

        conflicts = detect_design_conflicts(
            figma_variables, token_map_entries, anchor_tokens)

        self.assertTrue(len(conflicts) >= 1)
        # Should flag that "primary" is missing from Figma
        primary_conflict = [c for c in conflicts if "primary" in c["property"]]
        self.assertTrue(len(primary_conflict) >= 1)
        self.assertEqual(primary_conflict[0]["type"], "DESIGN_CONFLICT")

    def test_figma_value_drift_produces_conflict(self):
        """Figma variable value changed but Token Map still points to old anchor token."""
        anchor_tokens = {
            "--accent": "#0284C7",
        }
        token_map_entries = {
            "primary": "var(--accent)",
        }
        # Figma "primary" now resolves to a different color
        figma_variables = {
            "primary": "#FF0000",
        }

        conflicts = detect_design_conflicts(
            figma_variables, token_map_entries, anchor_tokens)

        self.assertTrue(len(conflicts) >= 1)
        self.assertEqual(conflicts[0]["type"], "DESIGN_CONFLICT")
        self.assertEqual(conflicts[0]["figma_value"], "#FF0000")

    def test_no_conflict_when_figma_matches_anchor(self):
        """No DESIGN_CONFLICT when Figma variables match the anchor tokens."""
        anchor_tokens = {
            "--accent": "#0284C7",
            "--font-body": "'Inter', sans-serif",
        }
        token_map_entries = {
            "primary": "var(--accent)",
        }
        figma_variables = {
            "primary": "#0284C7",
        }

        conflicts = detect_design_conflicts(
            figma_variables, token_map_entries, anchor_tokens)
        self.assertEqual(len(conflicts), 0)

    def test_conflict_identifies_specific_token_mismatch(self):
        """DESIGN_CONFLICT warning identifies the specific token name mismatch."""
        anchor_tokens = {
            "--accent": "#0284C7",
        }
        token_map_entries = {
            "primary": "var(--accent)",
        }
        figma_variables = {
            "brand-primary": "#0284C7",
        }

        conflicts = detect_design_conflicts(
            figma_variables, token_map_entries, anchor_tokens)

        self.assertTrue(len(conflicts) >= 1)
        conflict = conflicts[0]
        self.assertIn("property", conflict)
        self.assertIn("figma_value", conflict)
        self.assertIn("spec_value", conflict)
        self.assertEqual(conflict["type"], "DESIGN_CONFLICT")


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
    results = {"status": status, "passed": passed, "failed": failed, "total": total, "test_file": "tools/test_pl_design_audit.py"}
    outpath = os.path.join(outdir, 'tests.json')
    with open(outpath, 'w') as f:
        json.dump(results, f)

    print(f"\n{outpath}: {status}")
    sys.exit(0 if failed == 0 else 1)
