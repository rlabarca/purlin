#!/usr/bin/env python3
"""Automated tests for the /pl-design-ingest skill.

Verifies the underlying operations: artifact storage, Visual Specification
section creation/update, anchor token reading, re-processing detection,
token mapping, and no-anchor fallback behavior.

Produces tests/pl_design_ingest/tests.json at project root.
"""

import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'critic'))

from critic import parse_visual_spec


# ---------------------------------------------------------------------------
# Ingest operation helpers — simulate the operations /pl-design-ingest performs
# ---------------------------------------------------------------------------

def store_local_artifact(source_path, feature_stem, project_root):
    """Copy a local artifact to features/design/<feature_stem>/.

    Returns the stored path relative to project root.
    """
    target_dir = os.path.join(project_root, "features", "design", feature_stem)
    os.makedirs(target_dir, exist_ok=True)
    filename = os.path.basename(source_path)
    target_path = os.path.join(target_dir, filename)
    shutil.copy2(source_path, target_path)
    return os.path.join("features", "design", feature_stem, filename)


def create_visual_spec_section(feature_content, screen_name, reference, description,
                               processed_date=None, design_anchor=None, checklist=None):
    """Insert or update a Visual Specification section in a feature file.

    Returns the updated feature content string.
    """
    if processed_date is None:
        processed_date = date.today().isoformat()
    if checklist is None:
        checklist = []

    screen_block = f"### Screen: {screen_name}\n"
    screen_block += f"- **Reference:** {reference}\n"
    screen_block += f"- **Processed:** {processed_date}\n"
    screen_block += f"- **Description:** {description}\n"
    for item in checklist:
        screen_block += f"- [ ] {item}\n"

    if "## Visual Specification" in feature_content:
        # Update existing section — append screen block before end of section
        # Find next ## heading or end of file
        vs_start = feature_content.index("## Visual Specification")
        rest = feature_content[vs_start:]
        next_heading = re.search(r'\n## (?!Visual Specification)', rest)
        if next_heading:
            insert_pos = vs_start + next_heading.start()
            return feature_content[:insert_pos] + "\n" + screen_block + "\n" + feature_content[insert_pos:]
        else:
            return feature_content.rstrip() + "\n\n" + screen_block
    else:
        # Create new section
        anchor_line = ""
        if design_anchor:
            anchor_line = f'\n> **Design Anchor:** {design_anchor}\n> **Inheritance:** Colors, typography, and theme switching per anchor.\n'

        section = f"\n## Visual Specification\n{anchor_line}\n{screen_block}"
        return feature_content.rstrip() + "\n" + section


def read_design_anchors(features_dir):
    """Read all design_*.md anchor files from features/ and extract token mappings.

    Returns a dict of {token_name: token_value} and {font_name: token_name}.
    """
    tokens = {}
    fonts = {}

    if not os.path.isdir(features_dir):
        return tokens, fonts

    for fname in os.listdir(features_dir):
        if fname.startswith("design_") and fname.endswith(".md"):
            fpath = os.path.join(features_dir, fname)
            with open(fpath, 'r') as f:
                content = f.read()

            token_re = re.compile(r'\|\s*`(--[\w-]+)`\s*\|\s*`([^`]+)`')
            for m in token_re.finditer(content):
                token_name = m.group(1)
                token_value = m.group(2).strip()
                tokens[token_name] = token_value

                font_match = re.match(r"'([A-Za-z ]+)'", token_value)
                if font_match:
                    fonts[font_match.group(1)] = token_name

    return tokens, fonts


def map_color_to_token(hex_color, tokens):
    """Map a hex color to its token name if it matches. Returns token name or None."""
    hex_upper = hex_color.upper()
    for token_name, token_value in tokens.items():
        if token_value.upper() == hex_upper:
            return token_name
    return None


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


class TestIngestLocalImageArtifact(unittest.TestCase):
    """Scenario: Ingest Local Image Artifact"""

    def test_image_copied_to_design_directory(self):
        """Local image is copied to features/design/<feature_stem>/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source image
            src_img = os.path.join(tmpdir, "mockup.png")
            with open(src_img, "wb") as f:
                f.write(b"PNG_FAKE_DATA")

            project_root = os.path.join(tmpdir, "project")
            os.makedirs(os.path.join(project_root, "features"))

            stored_path = store_local_artifact(src_img, "my_feature", project_root)

            self.assertEqual(stored_path, "features/design/my_feature/mockup.png")
            self.assertTrue(os.path.exists(os.path.join(project_root, stored_path)))

    def test_visual_spec_section_created(self):
        """Feature file is updated with a Visual Specification section."""
        feature_content = """# Feature: My Feature
## 1. Overview
A test feature.
## 2. Requirements
Some requirements.
"""
        updated = create_visual_spec_section(
            feature_content,
            screen_name="Main Dashboard",
            reference="features/design/my_feature/mockup.png",
            description="A dashboard layout with navigation sidebar.",
            design_anchor="features/design_visual_standards.md",
            checklist=["Verify sidebar placement", "Check color tokens"],
        )

        vs = parse_visual_spec(updated)
        self.assertTrue(vs["present"])
        self.assertEqual(vs["screens"], 1)
        self.assertIn("Main Dashboard", vs.get("screen_names", [updated]))
        self.assertIn("## Visual Specification", updated)
        self.assertIn("### Screen: Main Dashboard", updated)
        self.assertIn("**Reference:** features/design/my_feature/mockup.png", updated)
        self.assertIn("**Description:** A dashboard layout", updated)
        self.assertIn("- [ ] Verify sidebar placement", updated)
        self.assertIn("Design Anchor:", updated)

    def test_processed_date_set_to_today(self):
        """Processed date is set to today's date."""
        feature_content = "# Feature: Test\n## Requirements\nStuff.\n"
        updated = create_visual_spec_section(
            feature_content,
            screen_name="Screen A",
            reference="features/design/test/img.png",
            description="Test description.",
        )
        today_str = date.today().isoformat()
        self.assertIn(f"**Processed:** {today_str}", updated)


class TestIngestFigmaURL(unittest.TestCase):
    """Scenario: Ingest Figma URL"""

    def test_figma_url_recorded_in_reference(self):
        """Figma URL is recorded in the Reference line."""
        feature_content = "# Feature: Test\n## Requirements\nStuff.\n"
        figma_url = "https://www.figma.com/file/abc123/My-Design"

        updated = create_visual_spec_section(
            feature_content,
            screen_name="Settings Panel",
            reference=f"[Figma]({figma_url})",
            description="Placeholder — manual processing needed.",
        )

        self.assertIn(f"[Figma]({figma_url})", updated)
        self.assertIn("### Screen: Settings Panel", updated)

    def test_figma_reference_type_detected(self):
        """parse_visual_spec detects Figma URL references correctly."""
        content = """## Visual Specification
### Screen: Design
- **Reference:** [Figma](https://figma.com/file/xyz)
- **Processed:** 2025-01-15
- **Description:** Design from Figma.
- [ ] Check layout
"""
        vs = parse_visual_spec(content)
        refs = vs.get("references", [])
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["reference_type"], "figma")


class TestIngestLiveWebPageURL(unittest.TestCase):
    """Scenario: Ingest Live Web Page URL"""

    def test_live_url_recorded_in_reference(self):
        """Live web page URL is recorded as [Live](<url>) in the Reference line."""
        feature_content = "# Feature: Test\n## Requirements\nStuff.\n"
        live_url = "https://example.com/dashboard"

        updated = create_visual_spec_section(
            feature_content,
            screen_name="Current UI",
            reference=f"[Live]({live_url})",
            description="Current production dashboard with sidebar navigation.",
        )

        self.assertIn(f"[Live]({live_url})", updated)
        self.assertIn("### Screen: Current UI", updated)

    def test_live_reference_type_detected(self):
        """parse_visual_spec detects Live URL references correctly."""
        content = """## Visual Specification
### Screen: Live View
- **Reference:** [Live](https://example.com/page)
- **Processed:** 2025-02-01
- **Description:** Live page with components.
- [ ] Check components
"""
        vs = parse_visual_spec(content)
        refs = vs.get("references", [])
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["reference_type"], "live")


class TestReProcessUpdatedArtifact(unittest.TestCase):
    """Scenario: Re-Process Updated Artifact"""

    def test_reprocess_updates_description_and_date(self):
        """Re-processing replaces the description and updates the processed date."""
        original = """# Feature: My Feature
## Visual Specification
### Screen: Main Dashboard
- **Reference:** features/design/my_feature/dashboard-layout.png
- **Processed:** 2025-01-15
- **Description:** Original layout description.
- [ ] Check layout
"""
        # Simulate re-processing by creating new section content
        # In real usage, the agent re-reads the artifact and generates a new description
        new_description = "Updated layout with new sidebar component."
        today_str = date.today().isoformat()

        # The reprocess workflow detects the existing screen and replaces it
        # Here we test the replacement mechanism
        updated = original.replace(
            "- **Description:** Original layout description.",
            f"- **Description:** {new_description}",
        ).replace(
            "- **Processed:** 2025-01-15",
            f"- **Processed:** {today_str}",
        )

        vs = parse_visual_spec(updated)
        refs = vs.get("references", [])
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["processed_date"], today_str)
        self.assertTrue(refs[0]["has_description"])


class TestAnchorInheritanceTokenMapping(unittest.TestCase):
    """Scenario: Anchor Inheritance Token Mapping"""

    def test_color_mapped_to_token(self):
        """Hex color matching an anchor token maps to the token name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            os.makedirs(features_dir)

            anchor_content = """# Design: Visual Standards
## Invariants
### Color Tokens
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links, focus rings |
| `--purlin-bg` | `#0B131A` | Page background |
### Typography
| Token | Value | Usage |
|-------|-------|-------|
| `--font-display` | `'Montserrat', sans-serif` | Titles |
"""
            with open(os.path.join(features_dir, "design_visual_standards.md"), "w") as f:
                f.write(anchor_content)

            tokens, fonts = read_design_anchors(features_dir)

            # Map a hex color to its token
            result = map_color_to_token("#38BDF8", tokens)
            self.assertEqual(result, "--purlin-accent")

            # Font mapping
            self.assertIn("Montserrat", fonts)
            self.assertEqual(fonts["Montserrat"], "--font-display")

    def test_unknown_color_returns_none(self):
        """Hex color not in anchor tokens returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            os.makedirs(features_dir)

            anchor_content = """# Design: Standards
| Token | Value | Usage |
|-------|-------|-------|
| `--purlin-accent` | `#38BDF8` | Links |
"""
            with open(os.path.join(features_dir, "design_test.md"), "w") as f:
                f.write(anchor_content)

            tokens, fonts = read_design_anchors(features_dir)
            result = map_color_to_token("#FF00FF", tokens)
            self.assertIsNone(result)


class TestNoDesignAnchorFallback(unittest.TestCase):
    """Scenario: No Design Anchor Fallback"""

    def test_no_anchor_files_returns_empty(self):
        """When no design_*.md anchors exist, token discovery returns empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            os.makedirs(features_dir)
            # No design_*.md files

            tokens, fonts = read_design_anchors(features_dir)
            self.assertEqual(len(tokens), 0)
            self.assertEqual(len(fonts), 0)

    def test_no_anchor_literal_observations_used(self):
        """Without anchors, colors cannot be mapped and should use literal values."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            os.makedirs(features_dir)

            tokens, fonts = read_design_anchors(features_dir)

            # With empty tokens, mapping returns None — agent uses literal
            result = map_color_to_token("#38BDF8", tokens)
            self.assertIsNone(result)

    def test_nonexistent_features_dir_returns_empty(self):
        """When features/ directory does not exist, returns empty tokens."""
        tokens, fonts = read_design_anchors("/nonexistent/path/features")
        self.assertEqual(len(tokens), 0)
        self.assertEqual(len(fonts), 0)


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

    outdir = os.path.join(PROJECT_ROOT, 'tests', 'pl_design_ingest')
    os.makedirs(outdir, exist_ok=True)
    status = "PASS" if failed == 0 else "FAIL"
    results = {"status": status, "passed": passed, "failed": failed, "total": total}
    outpath = os.path.join(outdir, 'tests.json')
    with open(outpath, 'w') as f:
        json.dump(results, f)

    print(f"\n{outpath}: {status}")
    sys.exit(0 if failed == 0 else 1)
