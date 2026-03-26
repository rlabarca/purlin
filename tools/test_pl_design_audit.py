#!/usr/bin/env python3
"""Automated tests for the /pl-design-audit skill.

Verifies the underlying operations: Figma MCP staleness detection,
design-spec conflict detection, Figma dev status drift detection,
and version ID staleness detection.

Produces tests/pl_design_audit/tests.json at project root.
"""

import json
import os
import re
import sys
import unittest
from datetime import datetime, date

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '..')))
from tools.bootstrap import detect_project_root
PROJECT_ROOT = detect_project_root(os.path.join(SCRIPT_DIR, 'config'))

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


def check_figma_dev_status_drift(spec_status, current_status):
    """Check whether the spec's Figma Status matches the current dev status.

    Args:
        spec_status: The ``> Figma Status:`` value from the feature spec
            (e.g. ``"Design"``, ``"Ready for Dev"``, ``"Completed"``),
            or ``None`` if absent.
        current_status: The current dev mode status from Figma MCP
            (e.g. ``"Ready for Dev"``), or ``None`` if unavailable.

    Returns:
        dict with keys:
            "drift" (bool): True if the statuses differ.
            "spec_status" (str | None): The spec value.
            "current_status" (str | None): The live value.
            "verdict" (str): "CURRENT", "DRIFT", or "N/A".
    """
    if spec_status is None or current_status is None:
        return {
            "drift": False,
            "spec_status": spec_status,
            "current_status": current_status,
            "verdict": "N/A",
        }
    is_drift = spec_status.strip().lower() != current_status.strip().lower()
    return {
        "drift": is_drift,
        "spec_status": spec_status,
        "current_status": current_status,
        "verdict": "DRIFT" if is_drift else "CURRENT",
    }


def check_version_id_staleness(brief_version_id, current_version_id):
    """Check whether the brief's Figma version ID matches the current one.

    Version ID comparison is more precise than timestamp comparison for
    detecting design changes.

    Args:
        brief_version_id: The ``figma_version_id`` value from ``brief.json``,
            or ``None`` if absent.
        current_version_id: The current file version from Figma MCP,
            or ``None`` if MCP is unavailable.

    Returns:
        dict with keys:
            "stale" (bool): True if version IDs differ.
            "brief_version" (str | None): The brief value.
            "current_version" (str | None): The live value.
    """
    if brief_version_id is None or current_version_id is None:
        return {
            "stale": False,
            "brief_version": brief_version_id,
            "current_version": current_version_id,
        }
    return {
        "stale": brief_version_id != current_version_id,
        "brief_version": brief_version_id,
        "current_version": current_version_id,
    }


# ---------------------------------------------------------------------------
# Test Classes
# ---------------------------------------------------------------------------


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


class TestFigmaDevStatusDriftDetected(unittest.TestCase):
    """Scenario: Figma Dev Status Drift Detected"""

    def test_drift_when_statuses_differ(self):
        """Spec says Design, Figma says Ready for Dev -> DRIFT."""
        result = check_figma_dev_status_drift(
            spec_status="Design",
            current_status="Ready for Dev",
        )
        self.assertTrue(result["drift"])
        self.assertEqual(result["verdict"], "DRIFT")
        self.assertEqual(result["spec_status"], "Design")
        self.assertEqual(result["current_status"], "Ready for Dev")

    def test_no_drift_when_statuses_match(self):
        """Spec and Figma both say Ready for Dev -> CURRENT."""
        result = check_figma_dev_status_drift(
            spec_status="Ready for Dev",
            current_status="Ready for Dev",
        )
        self.assertFalse(result["drift"])
        self.assertEqual(result["verdict"], "CURRENT")

    def test_na_when_spec_status_absent(self):
        """No Figma Status in spec -> N/A."""
        result = check_figma_dev_status_drift(
            spec_status=None,
            current_status="Ready for Dev",
        )
        self.assertFalse(result["drift"])
        self.assertEqual(result["verdict"], "N/A")

    def test_na_when_mcp_unavailable(self):
        """MCP unavailable (current_status=None) -> N/A."""
        result = check_figma_dev_status_drift(
            spec_status="Design",
            current_status=None,
        )
        self.assertFalse(result["drift"])
        self.assertEqual(result["verdict"], "N/A")

    def test_case_insensitive_comparison(self):
        """Status comparison is case-insensitive."""
        result = check_figma_dev_status_drift(
            spec_status="design",
            current_status="Design",
        )
        self.assertFalse(result["drift"])
        self.assertEqual(result["verdict"], "CURRENT")


class TestVersionIdStalenessDetected(unittest.TestCase):
    """Scenario: Version ID Staleness Detected"""

    def test_different_version_ids_flag_stale(self):
        """brief.json v123 vs Figma v456 -> stale."""
        result = check_version_id_staleness(
            brief_version_id="v123",
            current_version_id="v456",
        )
        self.assertTrue(result["stale"])
        self.assertEqual(result["brief_version"], "v123")
        self.assertEqual(result["current_version"], "v456")

    def test_same_version_ids_not_stale(self):
        """Matching version IDs -> not stale."""
        result = check_version_id_staleness(
            brief_version_id="v123",
            current_version_id="v123",
        )
        self.assertFalse(result["stale"])

    def test_missing_brief_version_not_stale(self):
        """No figma_version_id in brief -> not stale (N/A)."""
        result = check_version_id_staleness(
            brief_version_id=None,
            current_version_id="v456",
        )
        self.assertFalse(result["stale"])

    def test_mcp_unavailable_not_stale(self):
        """MCP unavailable (current=None) -> not stale."""
        result = check_version_id_staleness(
            brief_version_id="v123",
            current_version_id=None,
        )
        self.assertFalse(result["stale"])


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
