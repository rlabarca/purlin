#!/usr/bin/env python3
"""Automated tests for the /pl-design-ingest skill.

Verifies the underlying operations: artifact storage, Visual Specification
section creation/update, anchor token reading, re-processing detection,
token mapping, brief.json generation, and no-anchor fallback behavior.

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
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))
from tools.bootstrap import detect_project_root
PROJECT_ROOT = detect_project_root(os.path.join(SCRIPT_DIR, 'config'))
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


def create_visual_spec_section(feature_content, screen_name, reference, token_map,
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
    screen_block += f"- **Token Map:** {token_map}\n"
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


def generate_token_map(observed_tokens, anchor_tokens):
    """Generate Token Map entries mapping observed tokens to project tokens.

    Args:
        observed_tokens: dict of {figma_var_name: resolved_value}
        anchor_tokens: dict of {project_token_name: token_value}

    Returns:
        dict of {figma_var_name: project_token_reference_or_literal}
    """
    # Build reverse map: hex value -> anchor token name
    hex_to_anchor = {}
    for token_name, token_value in anchor_tokens.items():
        if token_value.startswith("#"):
            hex_to_anchor[token_value.upper()] = token_name

    token_map = {}
    for var_name, var_value in observed_tokens.items():
        if isinstance(var_value, str) and var_value.startswith("#"):
            anchor_name = hex_to_anchor.get(var_value.upper())
            if anchor_name:
                token_map[var_name] = f"var({anchor_name})"
            else:
                token_map[var_name] = var_value
        else:
            token_map[var_name] = str(var_value)

    return token_map


def generate_brief_json(figma_url, figma_last_modified, screens, tokens,
                        feature_stem, project_root, code_connect=None,
                        figma_dev_status=None, figma_version_id=None):
    """Generate brief.json at features/design/<feature_stem>/brief.json.

    Args:
        figma_url: The source Figma URL.
        figma_last_modified: ISO 8601 datetime string from MCP.
        screens: dict of screen data.
        tokens: dict of Figma design variable names and resolved values.
        feature_stem: feature filename without extension.
        project_root: project root path.
        code_connect: optional dict of component Code Connect data.
        figma_dev_status: optional dev mode status string
            (e.g. "ready_for_dev", "completed"), or None.
        figma_version_id: optional Figma file version ID string.

    Returns:
        Path to the generated brief.json relative to project root.
    """
    brief = {
        "figma_url": figma_url,
        "figma_last_modified": figma_last_modified,
        "screens": screens,
        "tokens": tokens,
    }
    if code_connect:
        brief["code_connect"] = code_connect
    brief["figma_dev_status"] = figma_dev_status
    if figma_version_id is not None:
        brief["figma_version_id"] = figma_version_id
    brief_dir = os.path.join(project_root, "features", "design", feature_stem)
    os.makedirs(brief_dir, exist_ok=True)
    brief_path = os.path.join(brief_dir, "brief.json")
    with open(brief_path, 'w') as f:
        json.dump(brief, f, indent=2, sort_keys=True)
    return os.path.join("features", "design", feature_stem, "brief.json")


# ---------------------------------------------------------------------------
# Figma MCP helpers — availability detection, setup instructions, extraction
# ---------------------------------------------------------------------------

FIGMA_MCP_SETUP_CMD = "claude mcp add --transport http figma https://mcp.figma.com/mcp"
FIGMA_MCP_FALLBACK_NOTE = (
    "For higher fidelity, install Figma MCP: " + FIGMA_MCP_SETUP_CMD
)


def is_figma_mcp_available(available_tools):
    """Check whether Figma MCP tools are available in the current session.

    Args:
        available_tools: list of tool name strings available in the session.

    Returns:
        True if any tool name contains 'figma' (case-insensitive).
    """
    return any("figma" in t.lower() for t in available_tools)


def generate_figma_no_mcp_token_map(figma_url):
    """Generate a placeholder Token Map when Figma MCP is not available.

    Returns a dict with the token_map text, the MCP setup note, and a flag
    indicating manual processing is needed.
    """
    return {
        "token_map": "Placeholder -- manual processing needed. "
                     "Provide an exported image or screenshot to generate "
                     "a full Token Map.",
        "mcp_note": FIGMA_MCP_FALLBACK_NOTE,
        "needs_manual_processing": True,
    }


def generate_figma_mcp_token_map(mcp_metadata, tokens, fonts):
    """Generate a Token Map from Figma MCP-extracted metadata.

    Args:
        mcp_metadata: dict with keys "layout" (str), "components" (list of str),
            "colors" (dict of {var_name: hex_value}),
            "fonts" (dict of {var_name: font_family}),
            "variables" (dict of variable_name -> value).
        tokens: dict of {token_name: token_value} from design anchors.
        fonts: dict of {font_name: token_name} from design anchors.

    Returns:
        dict with "token_map" (dict) and "auto_generated" (bool).
    """
    token_map = {}

    # Build reverse maps for matching
    hex_to_token = {}
    for tn, tv in tokens.items():
        if tv.startswith("#"):
            hex_to_token[tv.upper()] = tn

    # Map color variables
    for var_name, hex_value in mcp_metadata.get("colors", {}).items():
        mapped = hex_to_token.get(hex_value.upper())
        if mapped:
            token_map[var_name] = f"var({mapped})"
        else:
            token_map[var_name] = hex_value

    # Map font variables
    for var_name, font_family in mcp_metadata.get("fonts", {}).items():
        mapped = fonts.get(font_family)
        if mapped:
            token_map[var_name] = f"var({mapped})"
        else:
            token_map[var_name] = font_family

    return {
        "token_map": token_map,
        "auto_generated": True,
    }


def _normalize_token_name(name):
    """Normalize a token name by stripping var() wrapper and -- prefix.

    Examples:
        "var(--app-bg)" -> "app-bg"
        "--app-bg"      -> "app-bg"
        "app-bg"        -> "app-bg"
    """
    s = name.strip()
    m = re.match(r'^var\((.+)\)$', s)
    if m:
        s = m.group(1).strip()
    s = s.lstrip('-')
    return s


def detect_identity_tokens(figma_variables, anchor_tokens):
    """Detect identity mappings between Figma variable names and project tokens.

    An identity mapping occurs when a Figma variable name matches a project
    token name after normalization (stripping ``var()`` and ``--`` prefix).

    Args:
        figma_variables: dict of {variable_name: resolved_value} from Figma MCP.
        anchor_tokens: dict of {token_name: token_value} from design anchors.
            Token names include the ``--`` prefix (e.g. ``--app-bg``).

    Returns:
        dict with keys:
            "identity_entries": dict mapping figma_name -> "var(--token-name)"
                for each identity match.
            "manual_entries": list of figma variable names requiring manual mapping.
            "identity_count": int count of identity matches.
            "manual_count": int count of variables needing manual mapping.
            "total": int total Figma variables inspected.
    """
    normalized_anchor = {}
    for token_name in anchor_tokens:
        norm = _normalize_token_name(token_name)
        normalized_anchor[norm] = token_name  # norm -> original token name

    identity_entries = {}
    manual_entries = []

    for figma_name in figma_variables:
        norm_figma = _normalize_token_name(figma_name)
        if norm_figma in normalized_anchor:
            original_token = normalized_anchor[norm_figma]
            identity_entries[figma_name] = f"var({original_token})"
        else:
            manual_entries.append(figma_name)

    return {
        "identity_entries": identity_entries,
        "manual_entries": manual_entries,
        "identity_count": len(identity_entries),
        "manual_count": len(manual_entries),
        "total": len(figma_variables),
    }


def _extract_design_anchor(feature_content):
    """Extract the current Design Anchor declaration from a feature file.

    Returns the anchor path string (e.g. "features/design_visual_standards.md")
    or None if no declaration exists.
    """
    m = re.search(r'>\s*\*\*Design Anchor:\*\*\s*(.+)', feature_content)
    if m:
        return m.group(1).strip()
    return None


def _best_matching_anchor(token_map_entries, features_dir):
    """Determine which design anchor best matches the token mappings used.

    Scores each anchor by how many of its tokens appear in the token map entries
    (as var(--token) references). Returns the filename of the best-matching anchor,
    or None if no anchors exist.

    Args:
        token_map_entries: dict of {figma_name: mapped_value} where mapped_value
            may be "var(--token-name)" or a literal.
        features_dir: path to the features/ directory.

    Returns:
        Filename of the best-matching anchor (e.g. "features/design_visual_standards.md"),
        or None.
    """
    if not os.path.isdir(features_dir):
        return None

    # Extract all var(--token) references from the token map
    used_tokens = set()
    for val in token_map_entries.values():
        m = re.match(r'^var\((--[\w-]+)\)$', str(val))
        if m:
            used_tokens.add(m.group(1))

    if not used_tokens:
        return None

    best_anchor = None
    best_score = 0

    for fname in sorted(os.listdir(features_dir)):
        if fname.startswith("design_") and fname.endswith(".md"):
            fpath = os.path.join(features_dir, fname)
            with open(fpath, 'r') as f:
                content = f.read()

            # Count how many used tokens appear in this anchor
            token_re = re.compile(r'\|\s*`(--[\w-]+)`\s*\|')
            anchor_tokens = set(m.group(1) for m in token_re.finditer(content))
            score = len(used_tokens & anchor_tokens)

            if score > best_score:
                best_score = score
                best_anchor = f"features/{fname}"

    return best_anchor


def verify_design_anchor(feature_content, token_map_entries, features_dir):
    """Verify and potentially update the Design Anchor on re-ingestion.

    On re-processing, checks whether the current anchor declaration still matches
    the tokens used. If a different anchor is more appropriate, returns an update.

    Args:
        feature_content: the full feature file content string.
        token_map_entries: dict of {figma_name: mapped_value}.
        features_dir: path to the features/ directory.

    Returns:
        dict with keys:
            "current_anchor": str or None (existing declaration).
            "best_anchor": str or None (best matching anchor).
            "needs_update": bool (True if anchor should change).
            "report": str or None (report message if anchor changed).
    """
    current = _extract_design_anchor(feature_content)
    best = _best_matching_anchor(token_map_entries, features_dir)

    if best is None:
        return {
            "current_anchor": current,
            "best_anchor": None,
            "needs_update": False,
            "report": None,
        }

    if current is None:
        return {
            "current_anchor": None,
            "best_anchor": best,
            "needs_update": True,
            "report": None,  # Adding new anchor, not updating
        }

    if current != best:
        return {
            "current_anchor": current,
            "best_anchor": best,
            "needs_update": True,
            "report": f"Updated design anchor from `{current}` to `{best}`.",
        }

    return {
        "current_anchor": current,
        "best_anchor": best,
        "needs_update": False,
        "report": None,
    }


def update_design_anchor_in_content(feature_content, old_anchor, new_anchor):
    """Replace the Design Anchor declaration in feature content.

    If old_anchor is None (no existing declaration), inserts a new one
    after the Visual Specification heading.

    Returns the updated feature content string.
    """
    if old_anchor is not None:
        return feature_content.replace(
            f"> **Design Anchor:** {old_anchor}",
            f"> **Design Anchor:** {new_anchor}",
        )
    else:
        # Insert after ## Visual Specification heading
        vs_heading = "## Visual Specification\n"
        if vs_heading in feature_content:
            anchor_block = (
                f'\n> **Design Anchor:** {new_anchor}\n'
                f'> **Inheritance:** Colors, typography, and theme switching per anchor.\n'
            )
            return feature_content.replace(vs_heading, vs_heading + anchor_block)
        return feature_content


def extract_annotations(figma_annotations):
    """Extract behavioral notes from Figma annotations.

    Annotations that describe behavior (states, interactions, edge cases)
    are extracted and categorized.  Non-behavioral annotations (style notes,
    developer handoff details) are excluded.

    Args:
        figma_annotations: list of dicts, each with at least a "label" key
            (the annotation text).  May also contain "type" (str).

    Returns:
        dict with keys:
            "behavioral_notes": list of annotation text strings containing
                behavioral keywords (state, interaction, edge case, etc.).
            "scenario_drafts": list of dicts with "title" and "outline" keys
                for each behavioral note that can be turned into a scenario.
            "topics_covered": list of topic keywords found in the annotations.
            "count": int total annotations inspected.
    """
    BEHAVIORAL_KEYWORDS = [
        "empty", "loading", "error", "hover", "click", "submit",
        "disabled", "enabled", "hidden", "visible", "state",
        "interaction", "edge case", "fallback", "timeout",
        "validation", "overflow", "collapse", "expand",
    ]

    behavioral_notes = []
    scenario_drafts = []
    topics_covered = set()

    for ann in figma_annotations:
        text = ann.get("label", "")
        text_lower = text.lower()

        matched_keywords = [kw for kw in BEHAVIORAL_KEYWORDS if kw in text_lower]
        if matched_keywords:
            behavioral_notes.append(text)
            topics_covered.update(matched_keywords)

            # Generate a draft scenario outline from the annotation
            title = text.split(".")[0].strip()
            if len(title) > 60:
                title = title[:57] + "..."
            scenario_drafts.append({
                "title": title,
                "outline": f"Given the feature is in the described state\n"
                           f"When the user triggers the behavior\n"
                           f"Then {text}",
            })

    return {
        "behavioral_notes": behavioral_notes,
        "scenario_drafts": scenario_drafts,
        "topics_covered": sorted(topics_covered),
        "count": len(figma_annotations),
    }


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
        """Feature file is updated with a Visual Specification section containing Token Map."""
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
            token_map="`surface` -> `var(--purlin-bg)`, `accent` -> `var(--purlin-accent)`",
            design_anchor="features/design_visual_standards.md",
            checklist=["Verify sidebar placement", "Check color tokens"],
        )

        vs = parse_visual_spec(updated)
        self.assertTrue(vs["present"])
        self.assertEqual(vs["screens"], 1)
        self.assertIn("## Visual Specification", updated)
        self.assertIn("### Screen: Main Dashboard", updated)
        self.assertIn("**Reference:** features/design/my_feature/mockup.png", updated)
        self.assertIn("**Token Map:**", updated)
        self.assertIn("surface", updated)
        self.assertIn("- [ ] Verify sidebar placement", updated)
        self.assertIn("Design Anchor:", updated)
        # Must NOT contain Description field
        self.assertNotIn("**Description:**", updated)

    def test_processed_date_set_to_today(self):
        """Processed date is set to today's date."""
        feature_content = "# Feature: Test\n## Requirements\nStuff.\n"
        updated = create_visual_spec_section(
            feature_content,
            screen_name="Screen A",
            reference="features/design/test/img.png",
            token_map="`primary` -> `var(--purlin-accent)`",
        )
        today_str = date.today().isoformat()
        self.assertIn(f"**Processed:** {today_str}", updated)

    def test_token_map_generated_not_description(self):
        """Token Map is generated, not a prose Description."""
        feature_content = "# Feature: Test\n## Requirements\nStuff.\n"
        updated = create_visual_spec_section(
            feature_content,
            screen_name="Screen A",
            reference="features/design/test/img.png",
            token_map="`surface` -> `var(--purlin-bg)`",
            checklist=["Background uses --purlin-bg token"],
        )
        self.assertIn("**Token Map:**", updated)
        self.assertNotIn("**Description:**", updated)
        self.assertIn("- [ ] Background uses --purlin-bg token", updated)


class TestIngestFigmaURLWithoutMCP(unittest.TestCase):
    """Scenario: Ingest Figma URL Without MCP"""

    def test_figma_url_recorded_in_reference(self):
        """Figma URL is recorded in the Reference line as [Figma](<url>)."""
        feature_content = "# Feature: Test\n## Requirements\nStuff.\n"
        figma_url = "https://www.figma.com/file/abc123/My-Design"

        updated = create_visual_spec_section(
            feature_content,
            screen_name="Settings Panel",
            reference=f"[Figma]({figma_url})",
            token_map="Placeholder -- manual processing needed.",
        )

        self.assertIn(f"[Figma]({figma_url})", updated)
        self.assertIn("### Screen: Settings Panel", updated)

    def test_figma_reference_type_detected(self):
        """parse_visual_spec detects Figma URL references correctly."""
        content = """## Visual Specification
### Screen: Design
- **Reference:** [Figma](https://figma.com/file/xyz)
- **Processed:** 2025-01-15
- **Token Map:** `primary` -> `var(--purlin-accent)`
- [ ] Check layout
"""
        vs = parse_visual_spec(content)
        refs = vs.get("references", [])
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["reference_type"], "figma")

    def test_no_mcp_produces_placeholder_token_map(self):
        """When MCP is unavailable, Token Map notes manual processing is needed."""
        figma_url = "https://www.figma.com/file/abc123"
        result = generate_figma_no_mcp_token_map(figma_url)

        self.assertTrue(result["needs_manual_processing"])
        self.assertIn("manual processing needed", result["token_map"].lower())

    def test_no_mcp_suggests_figma_mcp_install(self):
        """When MCP is unavailable, a note suggests installing Figma MCP."""
        result = generate_figma_no_mcp_token_map("https://figma.com/file/x")

        self.assertIn("Figma MCP", result["mcp_note"])
        self.assertIn(FIGMA_MCP_SETUP_CMD, result["mcp_note"])


class TestFigmaMCPAutoSetupWhenProcessingFigmaURL(unittest.TestCase):
    """Scenario: Figma MCP Auto-Setup When Processing Figma URL"""

    def test_mcp_not_available_detected(self):
        """When no Figma tools are in the tool list, MCP is not available."""
        tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
        self.assertFalse(is_figma_mcp_available(tools))

    def test_mcp_available_detected(self):
        """When Figma tools are in the tool list, MCP is available."""
        tools = ["Read", "Write", "figma_get_file", "figma_get_components"]
        self.assertTrue(is_figma_mcp_available(tools))

    def test_setup_instructions_include_install_command(self):
        """MCP installation instructions include the claude mcp add command."""
        self.assertIn("claude mcp add", FIGMA_MCP_SETUP_CMD)
        self.assertIn("figma", FIGMA_MCP_SETUP_CMD)

    def test_fallback_to_tier1_when_no_mcp(self):
        """Without MCP, falls back to Tier 1/2 processing (prompt for export)."""
        result = generate_figma_no_mcp_token_map("https://figma.com/file/x")
        # Fallback produces a placeholder that prompts for an exported image
        self.assertIn("manual processing needed", result["token_map"].lower())
        self.assertTrue(result["needs_manual_processing"])


class TestFigmaMCPExtractsDesignContextDirectly(unittest.TestCase):
    """Scenario: Figma MCP Extracts Design Context Directly"""

    def test_mcp_metadata_generates_token_map(self):
        """Design metadata extracted via MCP produces an auto-generated Token Map."""
        mcp_metadata = {
            "colors": {"accent": "#38BDF8", "background": "#0B131A"},
            "fonts": {"heading": "Montserrat", "body": "Inter"},
            "variables": {},
        }
        tokens = {"--purlin-accent": "#38BDF8", "--purlin-bg": "#0B131A"}
        fonts = {"Montserrat": "--font-display", "Inter": "--font-body"}

        result = generate_figma_mcp_token_map(mcp_metadata, tokens, fonts)

        self.assertTrue(result["auto_generated"])
        self.assertIn("accent", result["token_map"])
        self.assertIn("background", result["token_map"])

    def test_colors_mapped_to_tokens(self):
        """MCP-extracted colors are mapped to design anchor tokens in Token Map."""
        mcp_metadata = {
            "colors": {"primary": "#38BDF8"},
            "fonts": {},
            "variables": {},
        }
        tokens = {"--purlin-accent": "#38BDF8"}
        fonts = {}

        result = generate_figma_mcp_token_map(mcp_metadata, tokens, fonts)
        self.assertEqual(result["token_map"]["primary"], "var(--purlin-accent)")

    def test_fonts_mapped_to_tokens(self):
        """MCP-extracted fonts are mapped to design anchor font tokens in Token Map."""
        mcp_metadata = {
            "colors": {},
            "fonts": {"body-font": "Inter"},
            "variables": {},
        }
        tokens = {}
        fonts = {"Inter": "--font-body"}

        result = generate_figma_mcp_token_map(mcp_metadata, tokens, fonts)
        self.assertEqual(result["token_map"]["body-font"], "var(--font-body)")

    def test_reference_preserves_original_figma_url(self):
        """The Reference line preserves the original Figma URL after MCP extraction."""
        figma_url = "https://www.figma.com/file/abc123/My-Design"
        feature_content = "# Feature: Test\n## Requirements\nStuff.\n"

        mcp_result = generate_figma_mcp_token_map(
            {"colors": {"accent": "#38BDF8"}, "fonts": {}, "variables": {}},
            {"--purlin-accent": "#38BDF8"}, {},
        )

        # Format token map as string for the Visual Spec
        map_str = ", ".join(
            f"`{k}` -> `{v}`" for k, v in mcp_result["token_map"].items())

        updated = create_visual_spec_section(
            feature_content,
            screen_name="Dashboard",
            reference=f"[Figma]({figma_url})",
            token_map=map_str,
        )

        self.assertIn(f"[Figma]({figma_url})", updated)
        self.assertIn("Token Map:", updated)

    def test_brief_json_generated(self):
        """brief.json is generated at features/design/<feature_stem>/brief.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            figma_url = "https://www.figma.com/file/abc123"
            brief_path = generate_brief_json(
                figma_url=figma_url,
                figma_last_modified="2026-03-01T12:00:00Z",
                screens={"Dashboard": {"node_id": "123", "dimensions": {"width": 1440, "height": 900}}},
                tokens={"primary": "#38BDF8", "background": "#0B131A"},
                feature_stem="my_feature",
                project_root=tmpdir,
            )

            self.assertEqual(brief_path, "features/design/my_feature/brief.json")
            full_path = os.path.join(tmpdir, brief_path)
            self.assertTrue(os.path.exists(full_path))

            with open(full_path, 'r') as f:
                brief_data = json.load(f)

            self.assertEqual(brief_data["figma_url"], figma_url)
            self.assertEqual(brief_data["figma_last_modified"], "2026-03-01T12:00:00Z")
            self.assertIn("Dashboard", brief_data["screens"])
            self.assertIn("primary", brief_data["tokens"])


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
            token_map="`surface` -> `var(--purlin-bg)`, `accent` -> `var(--purlin-accent)`",
            checklist=["Background matches --purlin-bg", "Links use --purlin-accent"],
        )

        self.assertIn(f"[Live]({live_url})", updated)
        self.assertIn("### Screen: Current UI", updated)
        self.assertIn("Token Map:", updated)
        self.assertIn("- [ ] Background matches --purlin-bg", updated)

    def test_live_reference_type_detected(self):
        """parse_visual_spec detects Live URL references correctly."""
        content = """## Visual Specification
### Screen: Live View
- **Reference:** [Live](https://example.com/page)
- **Processed:** 2025-02-01
- **Token Map:** `surface` -> `var(--purlin-bg)`
- [ ] Check components
"""
        vs = parse_visual_spec(content)
        refs = vs.get("references", [])
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["reference_type"], "live")


class TestReProcessUpdatedArtifact(unittest.TestCase):
    """Scenario: Re-Process Updated Artifact"""

    def test_reprocess_updates_token_map_and_date(self):
        """Re-processing replaces the Token Map and updates the processed date."""
        original = """# Feature: My Feature
## Visual Specification
### Screen: Main Dashboard
- **Reference:** features/design/my_feature/dashboard-layout.png
- **Processed:** 2025-01-15
- **Token Map:** `surface` -> `var(--purlin-bg)`
- [ ] Check layout
"""
        # Simulate re-processing by replacing Token Map content
        new_token_map = "`surface` -> `var(--purlin-bg)`, `accent` -> `var(--purlin-accent)`"
        today_str = date.today().isoformat()

        updated = original.replace(
            "- **Token Map:** `surface` -> `var(--purlin-bg)`",
            f"- **Token Map:** {new_token_map}",
        ).replace(
            "- **Processed:** 2025-01-15",
            f"- **Processed:** {today_str}",
        )

        vs = parse_visual_spec(updated)
        refs = vs.get("references", [])
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["processed_date"], today_str)
        self.assertTrue(refs[0]["has_token_map"])

    def test_reprocess_updates_checklist(self):
        """Re-processing updates checklist items to reflect the new design."""
        original = """# Feature: My Feature
## Visual Specification
### Screen: Main Dashboard
- **Reference:** features/design/my_feature/dashboard-layout.png
- **Processed:** 2025-01-15
- **Token Map:** `surface` -> `var(--purlin-bg)`
- [ ] Old checklist item
"""
        today_str = date.today().isoformat()
        updated = original.replace(
            "- [ ] Old checklist item",
            "- [ ] New sidebar placement check\n- [ ] Updated color token verification",
        ).replace(
            "- **Processed:** 2025-01-15",
            f"- **Processed:** {today_str}",
        )

        self.assertIn("- [ ] New sidebar placement check", updated)
        self.assertIn("- [ ] Updated color token verification", updated)
        self.assertNotIn("- [ ] Old checklist item", updated)


class TestReProcessAnchorVerification(unittest.TestCase):
    """Section 2.6: Re-ingestion verifies and updates anchor declaration."""

    def test_matching_anchor_no_update(self):
        """Re-processing with tokens matching current anchor triggers no update."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            os.makedirs(features_dir)
            with open(os.path.join(features_dir, "design_visual_standards.md"), "w") as f:
                f.write("# Design\n| Token | Value |\n| `--purlin-accent` | `#38BDF8` |\n")

            feature_content = (
                "# Feature: Test\n"
                "> Prerequisite: features/design_artifact_pipeline.md\n"
                "\n## Visual Specification\n"
                "> **Design Anchor:** features/design_visual_standards.md\n"
                "### Screen: Main\n"
                "- **Reference:** img.png\n"
                "- **Token Map:** `accent` -> `var(--purlin-accent)`\n"
            )
            token_map = {"accent": "var(--purlin-accent)"}

            result = verify_design_anchor(feature_content, token_map, features_dir)

            self.assertFalse(result["needs_update"])
            self.assertIsNone(result["report"])
            self.assertEqual(result["current_anchor"], "features/design_visual_standards.md")

    def test_different_anchor_triggers_update(self):
        """Re-processing detects a better anchor and reports the change."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            os.makedirs(features_dir)
            # Old anchor has no matching tokens
            with open(os.path.join(features_dir, "design_old_standards.md"), "w") as f:
                f.write("# Design Old\n| Token | Value |\n| `--old-color` | `#000000` |\n")
            # New anchor matches the tokens used
            with open(os.path.join(features_dir, "design_new_standards.md"), "w") as f:
                f.write("# Design New\n| Token | Value |\n| `--new-accent` | `#38BDF8` |\n")

            feature_content = (
                "## Visual Specification\n"
                "> **Design Anchor:** features/design_old_standards.md\n"
                "### Screen: Main\n"
                "- **Token Map:** `accent` -> `var(--new-accent)`\n"
            )
            token_map = {"accent": "var(--new-accent)"}

            result = verify_design_anchor(feature_content, token_map, features_dir)

            self.assertTrue(result["needs_update"])
            self.assertEqual(result["best_anchor"], "features/design_new_standards.md")
            self.assertIn("Updated design anchor from", result["report"])
            self.assertIn("design_old_standards", result["report"])
            self.assertIn("design_new_standards", result["report"])

    def test_no_anchor_adds_one(self):
        """Re-processing when no anchor exists adds the best matching one."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            os.makedirs(features_dir)
            with open(os.path.join(features_dir, "design_visual_standards.md"), "w") as f:
                f.write("# Design\n| Token | Value |\n| `--purlin-bg` | `#0B131A` |\n")

            feature_content = (
                "## Visual Specification\n"
                "### Screen: Main\n"
                "- **Token Map:** `surface` -> `var(--purlin-bg)`\n"
            )
            token_map = {"surface": "var(--purlin-bg)"}

            result = verify_design_anchor(feature_content, token_map, features_dir)

            self.assertTrue(result["needs_update"])
            self.assertIsNone(result["current_anchor"])
            self.assertEqual(result["best_anchor"], "features/design_visual_standards.md")
            # No report for new addition (not an update)
            self.assertIsNone(result["report"])

    def test_update_anchor_in_content(self):
        """update_design_anchor_in_content replaces the declaration."""
        feature_content = (
            "## Visual Specification\n"
            "> **Design Anchor:** features/design_old.md\n"
            "> **Inheritance:** Colors, typography, and theme switching per anchor.\n"
        )
        updated = update_design_anchor_in_content(
            feature_content, "features/design_old.md", "features/design_new.md"
        )
        self.assertIn("> **Design Anchor:** features/design_new.md", updated)
        self.assertNotIn("design_old.md", updated)

    def test_insert_anchor_when_missing(self):
        """update_design_anchor_in_content inserts when no declaration exists."""
        feature_content = (
            "## Visual Specification\n"
            "### Screen: Main\n"
            "- **Reference:** img.png\n"
        )
        updated = update_design_anchor_in_content(
            feature_content, None, "features/design_visual_standards.md"
        )
        self.assertIn("> **Design Anchor:** features/design_visual_standards.md", updated)

    def test_no_anchors_exist_no_update(self):
        """When no design anchors exist in the project, no update is needed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            os.makedirs(features_dir)
            # No design_*.md files

            feature_content = (
                "## Visual Specification\n"
                "### Screen: Main\n"
                "- **Token Map:** `primary` -> `#38BDF8`\n"
            )
            token_map = {"primary": "#38BDF8"}

            result = verify_design_anchor(feature_content, token_map, features_dir)

            self.assertFalse(result["needs_update"])

    def test_literal_values_no_anchor_match(self):
        """Token map with only literal values (no var() refs) produces no anchor match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            features_dir = os.path.join(tmpdir, "features")
            os.makedirs(features_dir)
            with open(os.path.join(features_dir, "design_visual_standards.md"), "w") as f:
                f.write("# Design\n| Token | Value |\n| `--purlin-bg` | `#0B131A` |\n")

            feature_content = (
                "## Visual Specification\n"
                "### Screen: Main\n"
                "- **Token Map:** `primary` -> `#FF0000`\n"
            )
            token_map = {"primary": "#FF0000"}

            result = verify_design_anchor(feature_content, token_map, features_dir)

            self.assertFalse(result["needs_update"])


class TestAnchorInheritanceTokenMapping(unittest.TestCase):
    """Scenario: Anchor Inheritance Token Mapping"""

    def test_color_mapped_to_token(self):
        """Figma variable value matching an anchor token maps to the token name."""
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

    def test_token_map_uses_var_not_literal(self):
        """Token Map maps Figma variable to var(--token) not literal hex value."""
        tokens = {"--purlin-accent": "#38BDF8", "--purlin-bg": "#0B131A"}
        observed = {"primary": "#38BDF8", "surface": "#0B131A"}

        token_map = generate_token_map(observed, tokens)

        self.assertEqual(token_map["primary"], "var(--purlin-accent)")
        self.assertEqual(token_map["surface"], "var(--purlin-bg)")

    def test_unknown_color_uses_literal(self):
        """Figma variable with value not in anchor tokens uses literal value."""
        tokens = {"--purlin-accent": "#38BDF8"}
        observed = {"custom": "#FF00FF"}

        token_map = generate_token_map(observed, tokens)

        self.assertEqual(token_map["custom"], "#FF00FF")


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

    def test_no_anchor_token_map_uses_literals(self):
        """Without anchors, Token Map uses literal values for token mappings."""
        tokens = {}  # No anchor tokens
        observed = {"primary": "#38BDF8", "surface": "#0B131A"}

        token_map = generate_token_map(observed, tokens)

        # With no anchor tokens, values should be literal hex
        self.assertEqual(token_map["primary"], "#38BDF8")
        self.assertEqual(token_map["surface"], "#0B131A")

    def test_nonexistent_features_dir_returns_empty(self):
        """When features/ directory does not exist, returns empty tokens."""
        tokens, fonts = read_design_anchors("/nonexistent/path/features")
        self.assertEqual(len(tokens), 0)
        self.assertEqual(len(fonts), 0)


class TestIdentityTokenAutoDetectionDuringFigmaIngestion(unittest.TestCase):
    """Scenario: Identity Token Auto-Detection During Figma Ingestion"""

    def test_identity_mappings_detected(self):
        """Figma variables matching project tokens produce identity entries."""
        figma_variables = {"--app-bg": "#0B131A", "--app-text": "#E2E8F0"}
        anchor_tokens = {"--app-bg": "#0B131A", "--app-text": "#E2E8F0"}

        result = detect_identity_tokens(figma_variables, anchor_tokens)

        self.assertEqual(result["identity_count"], 2)
        self.assertEqual(result["manual_count"], 0)
        self.assertIn("--app-bg", result["identity_entries"])
        self.assertIn("--app-text", result["identity_entries"])

    def test_identity_entries_use_var_format(self):
        """Identity entries map Figma name to its var() equivalent."""
        figma_variables = {"--app-bg": "#0B131A"}
        anchor_tokens = {"--app-bg": "#0B131A"}

        result = detect_identity_tokens(figma_variables, anchor_tokens)

        self.assertEqual(result["identity_entries"]["--app-bg"], "var(--app-bg)")

    def test_non_matching_variables_listed_as_manual(self):
        """Figma variables not matching any project token are listed as manual."""
        figma_variables = {"--app-bg": "#0B131A", "custom-color": "#FF00FF"}
        anchor_tokens = {"--app-bg": "#0B131A"}

        result = detect_identity_tokens(figma_variables, anchor_tokens)

        self.assertEqual(result["identity_count"], 1)
        self.assertEqual(result["manual_count"], 1)
        self.assertIn("custom-color", result["manual_entries"])

    def test_normalization_strips_var_wrapper(self):
        """Normalization handles var() wrapper differences."""
        # Figma uses bare name, anchor uses -- prefix
        figma_variables = {"app-bg": "#0B131A"}
        anchor_tokens = {"--app-bg": "#0B131A"}

        result = detect_identity_tokens(figma_variables, anchor_tokens)

        self.assertEqual(result["identity_count"], 1)
        self.assertEqual(result["manual_count"], 0)

    def test_report_format(self):
        """Report includes identity_count, manual_count, and total."""
        figma_variables = {"--app-bg": "#0B131A", "--app-text": "#E2E8F0"}
        anchor_tokens = {"--app-bg": "#0B131A", "--app-text": "#E2E8F0"}

        result = detect_identity_tokens(figma_variables, anchor_tokens)

        self.assertEqual(result["total"], 2)
        self.assertEqual(result["identity_count"], 2)
        self.assertEqual(result["manual_count"], 0)
        # Verify the report message can be constructed
        msg = (f"{result['identity_count']} of {result['total']} Figma variables "
               f"match project tokens (identity mappings). "
               f"{result['manual_count']} require manual mapping.")
        self.assertIn("2 of 2", msg)
        self.assertIn("0 require manual mapping", msg)


class TestAnnotationExtractionPrePopulatesBehavioralContext(unittest.TestCase):
    """Scenario: Annotation Extraction Pre-Populates Behavioral Context"""

    def test_behavioral_annotations_extracted(self):
        """Annotations describing empty state and loading behavior are extracted."""
        annotations = [
            {"label": "Empty state shows a placeholder illustration"},
            {"label": "Loading state displays a spinner overlay"},
            {"label": "Logo uses brand colors"},  # non-behavioral
        ]

        result = extract_annotations(annotations)

        self.assertEqual(len(result["behavioral_notes"]), 2)
        self.assertIn("Empty state shows a placeholder illustration",
                       result["behavioral_notes"])
        self.assertIn("Loading state displays a spinner overlay",
                       result["behavioral_notes"])

    def test_scenario_drafts_generated(self):
        """Draft Gherkin scenario outlines are generated from behavioral annotations."""
        annotations = [
            {"label": "Empty state shows a placeholder illustration"},
        ]

        result = extract_annotations(annotations)

        self.assertEqual(len(result["scenario_drafts"]), 1)
        draft = result["scenario_drafts"][0]
        self.assertIn("title", draft)
        self.assertIn("outline", draft)
        self.assertIn("Given", draft["outline"])
        self.assertIn("When", draft["outline"])
        self.assertIn("Then", draft["outline"])

    def test_topics_covered_populated(self):
        """Topics covered by annotations are tracked for probing skip."""
        annotations = [
            {"label": "Empty state shows a placeholder illustration"},
            {"label": "Loading state displays a spinner overlay"},
        ]

        result = extract_annotations(annotations)

        self.assertIn("empty", result["topics_covered"])
        self.assertIn("loading", result["topics_covered"])

    def test_non_behavioral_annotations_excluded(self):
        """Non-behavioral annotations (style notes) are excluded."""
        annotations = [
            {"label": "Uses 16px padding on left side"},
            {"label": "Brand color is blue #38BDF8"},
        ]

        result = extract_annotations(annotations)

        self.assertEqual(len(result["behavioral_notes"]), 0)
        self.assertEqual(len(result["scenario_drafts"]), 0)

    def test_probing_skip_count(self):
        """Topics covered by annotations reduce probing questions."""
        annotations = [
            {"label": "Empty state shows a placeholder illustration"},
            {"label": "Error state displays a retry button"},
            {"label": "Hover on card reveals action buttons"},
        ]

        result = extract_annotations(annotations)

        # Three behavioral annotations covering three topics
        self.assertTrue(len(result["topics_covered"]) >= 3)
        # Probing questions skip topics already covered
        self.assertIn("empty", result["topics_covered"])
        self.assertIn("error", result["topics_covered"])
        self.assertIn("hover", result["topics_covered"])

    def test_empty_annotations_list(self):
        """Empty annotations list produces empty results."""
        result = extract_annotations([])

        self.assertEqual(result["count"], 0)
        self.assertEqual(len(result["behavioral_notes"]), 0)
        self.assertEqual(len(result["scenario_drafts"]), 0)
        self.assertEqual(len(result["topics_covered"]), 0)

    def test_annotation_count_reported(self):
        """Total annotation count is reported regardless of behavioral filtering."""
        annotations = [
            {"label": "Empty state shows a placeholder"},
            {"label": "Brand color is blue"},
            {"label": "Font size is 14px"},
        ]

        result = extract_annotations(annotations)

        self.assertEqual(result["count"], 3)


class TestCodeConnectDataExtractedIntoBrief(unittest.TestCase):
    """Scenario: Code Connect Data Extracted Into Brief"""

    def test_code_connect_included_in_brief(self):
        """brief.json contains a code_connect key when data is provided."""
        tmpdir = tempfile.mkdtemp()
        try:
            code_connect = {
                "Card": {
                    "source_file": "src/components/Card.tsx",
                    "props": {"variant": "outlined", "size": "large"},
                    "figma_node_id": "42:123",
                },
            }
            generate_brief_json(
                figma_url="https://figma.com/design/abc",
                figma_last_modified="2026-03-10T10:00:00Z",
                screens={"Main": {"node_id": "1:2", "dimensions": {}}},
                tokens={"primary": "#0284C7"},
                feature_stem="my_feature",
                project_root=tmpdir,
                code_connect=code_connect,
            )
            brief_path = os.path.join(
                tmpdir, "features", "design", "my_feature", "brief.json")
            with open(brief_path) as f:
                brief = json.load(f)
            self.assertIn("code_connect", brief)
            self.assertIn("Card", brief["code_connect"])
            card = brief["code_connect"]["Card"]
            self.assertEqual(card["source_file"], "src/components/Card.tsx")
            self.assertEqual(card["props"]["variant"], "outlined")
            self.assertEqual(card["figma_node_id"], "42:123")
        finally:
            shutil.rmtree(tmpdir)

    def test_code_connect_omitted_when_absent(self):
        """brief.json has no code_connect key when data is not provided."""
        tmpdir = tempfile.mkdtemp()
        try:
            generate_brief_json(
                figma_url="https://figma.com/design/abc",
                figma_last_modified="2026-03-10T10:00:00Z",
                screens={},
                tokens={},
                feature_stem="my_feature",
                project_root=tmpdir,
            )
            brief_path = os.path.join(
                tmpdir, "features", "design", "my_feature", "brief.json")
            with open(brief_path) as f:
                brief = json.load(f)
            self.assertNotIn("code_connect", brief)
        finally:
            shutil.rmtree(tmpdir)


class TestFigmaDevStatusExtractedDuringIngestion(unittest.TestCase):
    """Scenario: Figma Dev Status Extracted During Ingestion"""

    def test_dev_status_in_brief(self):
        """brief.json contains figma_dev_status when provided."""
        tmpdir = tempfile.mkdtemp()
        try:
            generate_brief_json(
                figma_url="https://figma.com/design/abc",
                figma_last_modified="2026-03-10T10:00:00Z",
                screens={},
                tokens={},
                feature_stem="my_feature",
                project_root=tmpdir,
                figma_dev_status="ready_for_dev",
                figma_version_id="v789",
            )
            brief_path = os.path.join(
                tmpdir, "features", "design", "my_feature", "brief.json")
            with open(brief_path) as f:
                brief = json.load(f)
            self.assertEqual(brief["figma_dev_status"], "ready_for_dev")
            self.assertEqual(brief["figma_version_id"], "v789")
        finally:
            shutil.rmtree(tmpdir)

    def test_version_id_included(self):
        """brief.json contains figma_version_id for staleness detection."""
        tmpdir = tempfile.mkdtemp()
        try:
            generate_brief_json(
                figma_url="https://figma.com/design/abc",
                figma_last_modified="2026-03-10T10:00:00Z",
                screens={},
                tokens={},
                feature_stem="my_feature",
                project_root=tmpdir,
                figma_version_id="v456",
            )
            brief_path = os.path.join(
                tmpdir, "features", "design", "my_feature", "brief.json")
            with open(brief_path) as f:
                brief = json.load(f)
            self.assertIn("figma_version_id", brief)
            self.assertEqual(brief["figma_version_id"], "v456")
        finally:
            shutil.rmtree(tmpdir)


class TestDevStatusNotAvailableSilentlyOmitted(unittest.TestCase):
    """Scenario: Dev Status Not Available Silently Omitted"""

    def test_dev_status_null_when_unavailable(self):
        """brief.json contains figma_dev_status: null when not available."""
        tmpdir = tempfile.mkdtemp()
        try:
            generate_brief_json(
                figma_url="https://figma.com/design/abc",
                figma_last_modified="2026-03-10T10:00:00Z",
                screens={},
                tokens={},
                feature_stem="my_feature",
                project_root=tmpdir,
                figma_dev_status=None,
            )
            brief_path = os.path.join(
                tmpdir, "features", "design", "my_feature", "brief.json")
            with open(brief_path) as f:
                brief = json.load(f)
            self.assertIn("figma_dev_status", brief)
            self.assertIsNone(brief["figma_dev_status"])
        finally:
            shutil.rmtree(tmpdir)

    def test_no_version_id_when_unavailable(self):
        """brief.json omits figma_version_id when not provided."""
        tmpdir = tempfile.mkdtemp()
        try:
            generate_brief_json(
                figma_url="https://figma.com/design/abc",
                figma_last_modified="2026-03-10T10:00:00Z",
                screens={},
                tokens={},
                feature_stem="my_feature",
                project_root=tmpdir,
            )
            brief_path = os.path.join(
                tmpdir, "features", "design", "my_feature", "brief.json")
            with open(brief_path) as f:
                brief = json.load(f)
            self.assertNotIn("figma_version_id", brief)
        finally:
            shutil.rmtree(tmpdir)


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
    results = {"status": status, "passed": passed, "failed": failed, "total": total, "test_file": "tools/test_pl_design_ingest.py"}
    outpath = os.path.join(outdir, 'tests.json')
    with open(outpath, 'w') as f:
        json.dump(results, f)

    print(f"\n{outpath}: {status}")
    sys.exit(0 if failed == 0 else 1)
