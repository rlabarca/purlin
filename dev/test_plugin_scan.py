#!/usr/bin/env python3
"""Comprehensive test suite for the Purlin scan engine.

Exercises run_scan() and its constituent scan_* functions against the
plugin fixture at /tmp/purlin-plugin-fixture. The fixture must be
provisioned before running these tests (e.g., via the Phase 6 upgrade
fixture script). If the fixture directory is absent, all tests are
skipped automatically.

Run with:
    python3 -m pytest dev/test_plugin_scan.py -v
    # or
    python3 dev/test_plugin_scan.py
"""

import os
import sys
import unittest

# ---------------------------------------------------------------------------
# Environment setup -- must happen BEFORE importing scan_engine so that
# detect_project_root() picks up the fixture path.
# ---------------------------------------------------------------------------
FIXTURE_ROOT = "/tmp/purlin-plugin-fixture"
os.environ["PURLIN_PROJECT_ROOT"] = FIXTURE_ROOT

# Locate the scan_engine module.  In the plugin model the scanner lives at
# scripts/mcp/scan_engine.py.  Older tree layouts use tools/cdd/scan.py.
# We try scripts/mcp first (canonical path) then fall back to tools/cdd.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_THIS_DIR)

_MCP_DIR = os.path.join(_PROJECT_DIR, "scripts", "mcp")
_SCRIPTS_DIR = os.path.join(_PROJECT_DIR, "scripts")
_CDD_DIR = os.path.join(_PROJECT_DIR, "tools", "cdd")
_TOOLS_DIR = _PROJECT_DIR  # tools/ imports as a package

_scan_module_found = False
if os.path.isfile(os.path.join(_MCP_DIR, "scan_engine.py")):
    # Plugin model (scripts/mcp/scan_engine.py)
    if _MCP_DIR not in sys.path:
        sys.path.insert(0, _MCP_DIR)
    if _SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _SCRIPTS_DIR)
    _scan_module_found = True
elif os.path.isfile(os.path.join(_CDD_DIR, "scan.py")):
    # Legacy tree layout (tools/cdd/scan.py) -- import as scan_engine alias
    if _CDD_DIR not in sys.path:
        sys.path.insert(0, _CDD_DIR)
    if _TOOLS_DIR not in sys.path:
        sys.path.insert(0, _TOOLS_DIR)
    _scan_module_found = True

# Import the scanner module.  Under the plugin model the module is named
# scan_engine; in the legacy layout it is scan.  We import whichever is
# available under the canonical name ``scan_engine``.
scan_engine = None
if _scan_module_found:
    try:
        import scan_engine as _se  # noqa: E402
        scan_engine = _se
    except ImportError:
        pass
    if scan_engine is None:
        try:
            import scan as _se_legacy  # type: ignore[import-not-found]  # noqa: E402
            scan_engine = _se_legacy
        except ImportError:
            pass

if scan_engine is None:
    # Allow collection to succeed -- tests will skip individually.
    pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_scan_engine_globals():
    """Reset all module-level caches and path globals in scan_engine.

    scan_engine computes PROJECT_ROOT and derived paths at import time,
    then builds per-scan caches lazily. Between tests we must clear
    everything so each test gets a clean slate.
    """
    if scan_engine is None:
        return

    # Reset lazy caches (rebuilt on next scan).
    scan_engine._status_commit_cache = None
    scan_engine._spec_mod_cache = None
    if hasattr(scan_engine, "_exemption_index"):
        scan_engine._exemption_index = None

    # Re-derive paths from the (possibly updated) environment variable.
    root = scan_engine.detect_project_root(scan_engine.SCRIPT_DIR)
    scan_engine.PROJECT_ROOT = root
    scan_engine.FEATURES_DIR = os.path.join(root, "features")
    scan_engine.TESTS_DIR = os.path.join(root, "tests")
    scan_engine.CACHE_DIR = os.path.join(root, ".purlin", "cache")
    scan_engine.CACHE_FILE = os.path.join(scan_engine.CACHE_DIR, "scan.json")
    scan_engine.DELIVERY_PLAN = os.path.join(root, ".purlin", "delivery_plan.md")
    scan_engine.DEP_GRAPH_FILE = os.path.join(
        scan_engine.CACHE_DIR, "dependency_graph.json"
    )


def _has_invariants_support():
    """Return True if the scan engine supports the invariants section."""
    return hasattr(scan_engine, "scan_invariant_integrity")


class TestPluginScan(unittest.TestCase):
    """Tests for scan_engine.run_scan() against the plugin fixture."""

    @classmethod
    def setUpClass(cls):
        if scan_engine is None:
            raise unittest.SkipTest(
                "Could not import scan_engine (or scan) module. "
                "Ensure scripts/mcp/ or tools/cdd/ is on the Python path."
            )
        if not os.path.isdir(FIXTURE_ROOT):
            raise unittest.SkipTest(
                f"Fixture directory {FIXTURE_ROOT} does not exist. "
                "Provision it before running these tests."
            )
        if not os.path.isdir(os.path.join(FIXTURE_ROOT, ".purlin")):
            raise unittest.SkipTest(
                f"Fixture directory {FIXTURE_ROOT} exists but has no .purlin/ "
                "-- not a valid Purlin project fixture."
            )
        # Ensure env var points to fixture.
        os.environ["PURLIN_PROJECT_ROOT"] = FIXTURE_ROOT
        _reset_scan_engine_globals()

    def setUp(self):
        """Reset caches before every test so results are independent."""
        os.environ["PURLIN_PROJECT_ROOT"] = FIXTURE_ROOT
        _reset_scan_engine_globals()

    # ------------------------------------------------------------------
    # Full Scan Structure
    # ------------------------------------------------------------------

    def test_full_scan_returns_dict(self):
        """run_scan() returns a dict."""
        result = scan_engine.run_scan()
        self.assertIsInstance(result, dict)

    def test_full_scan_has_scanned_at(self):
        """Result contains a 'scanned_at' ISO timestamp."""
        result = scan_engine.run_scan()
        self.assertIn("scanned_at", result)
        ts = result["scanned_at"]
        self.assertIsInstance(ts, str)
        # Rough format check: 2026-03-28T12:00:00Z
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

    def test_full_scan_has_features(self):
        """Result has a 'features' key containing a list."""
        result = scan_engine.run_scan()
        self.assertIn("features", result)
        self.assertIsInstance(result["features"], list)

    # ------------------------------------------------------------------
    # Feature Lifecycle
    # ------------------------------------------------------------------

    def test_todo_features(self):
        """At least 3 features have TODO lifecycle status."""
        result = scan_engine.run_scan(only={"features"})
        todos = [
            f for f in result["features"]
            if f.get("lifecycle") == "TODO"
        ]
        self.assertGreaterEqual(
            len(todos), 3,
            f"Expected >= 3 TODO features, got {len(todos)}: "
            f"{[f['name'] for f in todos]}",
        )

    def test_testing_features(self):
        """At least 2 features have TESTING lifecycle status."""
        result = scan_engine.run_scan(only={"features"})
        testing = [
            f for f in result["features"]
            if f.get("lifecycle") == "TESTING"
        ]
        self.assertGreaterEqual(
            len(testing), 2,
            f"Expected >= 2 TESTING features, got {len(testing)}: "
            f"{[f['name'] for f in testing]}",
        )

    def test_complete_features(self):
        """At least 3 features have COMPLETE lifecycle status."""
        result = scan_engine.run_scan(only={"features"})
        complete = [
            f for f in result["features"]
            if f.get("lifecycle") == "COMPLETE"
        ]
        self.assertGreaterEqual(
            len(complete), 3,
            f"Expected >= 3 COMPLETE features, got {len(complete)}: "
            f"{[f['name'] for f in complete]}",
        )

    # ------------------------------------------------------------------
    # Section Filtering
    # ------------------------------------------------------------------

    def test_only_features(self):
        """run_scan(only={'features'}) returns only features + scanned_at."""
        result = scan_engine.run_scan(only={"features"})
        self.assertIn("scanned_at", result)
        self.assertIn("features", result)
        # Should NOT contain other sections.
        for key in ("open_discoveries", "unacknowledged_deviations",
                     "companion_debt", "delivery_plan", "dependency_graph",
                     "git_state", "smoke_candidates"):
            self.assertNotIn(
                key, result,
                f"Section '{key}' should be absent when only={{'features'}}",
            )

    def test_only_git(self):
        """run_scan(only={'git'}) returns only git_state + scanned_at."""
        result = scan_engine.run_scan(only={"git"})
        self.assertIn("scanned_at", result)
        self.assertIn("git_state", result)
        self.assertNotIn("features", result)
        self.assertNotIn("delivery_plan", result)

    def test_only_multiple(self):
        """run_scan(only={'features', 'git'}) returns both sections."""
        result = scan_engine.run_scan(only={"features", "git"})
        self.assertIn("scanned_at", result)
        self.assertIn("features", result)
        self.assertIn("git_state", result)
        # Should not contain sections not requested.
        self.assertNotIn("delivery_plan", result)
        self.assertNotIn("open_discoveries", result)

    # ------------------------------------------------------------------
    # Discoveries
    # ------------------------------------------------------------------

    def test_open_discoveries_present(self):
        """open_discoveries section has entries."""
        result = scan_engine.run_scan(only={"discoveries"})
        self.assertIn("open_discoveries", result)
        self.assertIsInstance(result["open_discoveries"], list)
        self.assertGreater(
            len(result["open_discoveries"]), 0,
            "Expected at least one open discovery in fixture",
        )

    def test_open_discoveries_are_open(self):
        """All entries in open_discoveries have OPEN status."""
        result = scan_engine.run_scan(only={"discoveries"})
        for entry in result["open_discoveries"]:
            self.assertEqual(
                entry.get("status"), "OPEN",
                f"Discovery in {entry.get('feature')} has status "
                f"'{entry.get('status')}', expected 'OPEN'",
            )

    # ------------------------------------------------------------------
    # Deviations
    # ------------------------------------------------------------------

    def test_unacknowledged_deviations(self):
        """unacknowledged_deviations has at least 1 entry."""
        result = scan_engine.run_scan(only={"deviations"})
        self.assertIn("unacknowledged_deviations", result)
        self.assertIsInstance(result["unacknowledged_deviations"], list)
        self.assertGreaterEqual(
            len(result["unacknowledged_deviations"]), 1,
            "Expected at least one unacknowledged deviation in fixture",
        )

    def test_deviation_from_api_endpoints(self):
        """Check that deviation entries include expected fields and valid tags.

        Each deviation entry must have feature, file, tag, line, and text.
        The tag must be one of the recognized deviation types.
        """
        result = scan_engine.run_scan(only={"deviations"})
        deviations = result.get("unacknowledged_deviations", [])
        if not deviations:
            self.skipTest("No deviations found in fixture to verify structure")
        for dev in deviations:
            self.assertIn("feature", dev)
            self.assertIn("file", dev)
            self.assertIn("tag", dev)
            self.assertIn("line", dev)
            self.assertIn("text", dev)
            # Tag must be one of the recognized types from the scan engine.
            self.assertIn(
                dev["tag"],
                ("DEVIATION", "DISCOVERY", "INFEASIBLE",
                 "SPEC_PROPOSAL", "PM_PENDING"),
                f"Unexpected deviation tag: {dev['tag']}",
            )

    # ------------------------------------------------------------------
    # Delivery Plan
    # ------------------------------------------------------------------

    def test_delivery_plan_present(self):
        """delivery_plan key exists in scan output."""
        result = scan_engine.run_scan(only={"plan"})
        self.assertIn("delivery_plan", result)
        self.assertIsNotNone(
            result["delivery_plan"],
            "delivery_plan should not be None -- fixture needs "
            ".purlin/delivery_plan.md",
        )

    def test_delivery_plan_has_phases(self):
        """delivery_plan.phases list has 3 entries."""
        result = scan_engine.run_scan(only={"plan"})
        plan = result.get("delivery_plan")
        self.assertIsNotNone(plan, "delivery_plan is None")
        self.assertIn("phases", plan)
        phases = plan["phases"]
        self.assertIsInstance(phases, list)
        self.assertEqual(
            len(phases), 3,
            f"Expected 3 phases, got {len(phases)}: "
            f"{[p.get('number') for p in phases]}",
        )

    # ------------------------------------------------------------------
    # Git State
    # ------------------------------------------------------------------

    def test_git_state_present(self):
        """git_state key exists in scan output."""
        result = scan_engine.run_scan(only={"git"})
        self.assertIn("git_state", result)
        self.assertIsInstance(result["git_state"], dict)

    def test_git_branch(self):
        """git_state has a branch key with a non-empty string."""
        result = scan_engine.run_scan(only={"git"})
        git = result["git_state"]
        self.assertIn("branch", git)
        self.assertIsInstance(git["branch"], str)
        self.assertTrue(
            len(git["branch"]) > 0, "Branch name should not be empty"
        )

    def test_git_clean(self):
        """git_state.clean is True (no uncommitted changes in fixture)."""
        result = scan_engine.run_scan(only={"git"})
        git = result["git_state"]
        self.assertIn("clean", git)
        self.assertTrue(
            git["clean"],
            f"Fixture should have a clean working tree, but dirty_files "
            f"were detected. git_state: {git}",
        )

    # ------------------------------------------------------------------
    # Dependency Graph
    # ------------------------------------------------------------------

    def test_graph_present(self):
        """dependency_graph section is present with expected structure."""
        result = scan_engine.run_scan(only={"deps"})
        self.assertIn("dependency_graph", result)
        graph = result["dependency_graph"]
        self.assertIsInstance(graph, dict)
        # Must have total, cycles, blocked keys per scan_dependency_graph().
        self.assertIn("total", graph)
        self.assertIn("cycles", graph)
        self.assertIn("blocked", graph)

    # ------------------------------------------------------------------
    # Invariants & Anchors
    # ------------------------------------------------------------------

    def test_feature_with_invariant_flag(self):
        """At least one feature has the invariant marker set to True.

        Invariant files are named i_<type>_<name>.md. The scan engine
        (scripts/mcp/scan_engine.py) sets feature_entry['invariant'] = True
        for these. The legacy scan.py module does not support this field.
        """
        # The invariant flag requires the plugin-model scan_engine, not
        # the legacy tools/cdd/scan.py.
        if not hasattr(scan_engine, "scan_invariant_integrity"):
            self.skipTest(
                "Invariant support requires scripts/mcp/scan_engine.py "
                "(not available in legacy tools/cdd/scan.py)"
            )
        result = scan_engine.run_scan(only={"features"})
        invariants = [
            f for f in result["features"]
            if f.get("invariant") is True
        ]
        self.assertGreater(
            len(invariants), 0,
            "Expected at least one feature with invariant=True "
            "(i_*.md files in features/)",
        )

    def test_prerequisite_parsing(self):
        """At least one feature has a non-empty prerequisites list.

        Features declare dependencies via '> Prerequisite: features/X.md'
        lines. The scan engine extracts these into the 'prerequisites'
        list on each feature entry.
        """
        result = scan_engine.run_scan(only={"features"})
        with_prereqs = [
            f for f in result["features"]
            if f.get("prerequisites")
        ]
        self.assertGreater(
            len(with_prereqs), 0,
            "Expected at least one feature with non-empty prerequisites",
        )

    # ------------------------------------------------------------------
    # Tombstones
    # ------------------------------------------------------------------

    def test_tombstone_excluded_by_default(self):
        """No tombstone entries appear in a default scan.

        run_scan() includes tombstone entries in its raw output (they
        have tombstone=True and lifecycle=TOMBSTONE). The main() CLI
        path strips them via _filter_tombstones() unless --tombstones
        is given. When calling run_scan() directly the raw data may
        include them; this test verifies that if any tombstone entries
        exist they carry the correct lifecycle tag for filtering.
        """
        result = scan_engine.run_scan(only={"features"})
        for f in result["features"]:
            if f.get("tombstone"):
                # Tombstones in raw output must have TOMBSTONE lifecycle
                # so callers can filter them reliably.
                self.assertEqual(f.get("lifecycle"), "TOMBSTONE")

    def test_tombstone_present(self):
        """Verify _tombstones/ directory handling.

        If features/_tombstones/ (or legacy tombstones/) exists in the
        fixture, the scan engine should have appended entries with
        tombstone=True. If neither exists, no tombstone entries should
        appear.
        """
        tombstones_dir = os.path.join(FIXTURE_ROOT, "features", "_tombstones")
        if not os.path.isdir(tombstones_dir):
            tombstones_dir = os.path.join(
                FIXTURE_ROOT, "features", "tombstones")
        result = scan_engine.run_scan(only={"features"})
        tombstone_entries = [
            f for f in result["features"] if f.get("tombstone")
        ]

        if os.path.isdir(tombstones_dir):
            # Count .md files in tombstones/ (excluding companions and sidecars).
            md_files = [
                fn for fn in os.listdir(tombstones_dir)
                if fn.endswith(".md")
                and not fn.endswith(".impl.md")
                and not fn.endswith(".discoveries.md")
            ]
            self.assertEqual(
                len(tombstone_entries), len(md_files),
                f"Expected {len(md_files)} tombstone entries, got "
                f"{len(tombstone_entries)}",
            )
        else:
            self.assertEqual(
                len(tombstone_entries), 0,
                "No tombstones/ directory, so no tombstone entries expected",
            )


if __name__ == "__main__":
    unittest.main()
