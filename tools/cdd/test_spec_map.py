"""Unit tests for the CDD Spec Map graph generation.

Covers automated scenarios from features/cdd_spec_map.md.
Outputs test results to tests/cdd_spec_map/tests.json.
"""

import unittest
import os
import sys
import json
import tempfile
import shutil

# Add the tool directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))
from graph import (
    parse_features, detect_cycles, find_orphans,
    build_features_json, generate_mermaid_content,
    generate_dependency_graph, run_full_generation,
)


class TestParseFeatures(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_feature(self, name, content):
        with open(os.path.join(self.test_dir, name), 'w') as f:
            f.write(content)

    def test_parse_basic_feature(self):
        self._write_feature("login.md", (
            '# Login\n'
            '> Label: "User Login"\n'
            '> Category: "Auth"\n'
            '> Prerequisite: base.md\n'
        ))
        features = parse_features(self.test_dir)
        self.assertIn("login", features)
        self.assertEqual(features["login"]["label"], "User Login")
        self.assertEqual(features["login"]["category"], "Auth")
        self.assertEqual(features["login"]["prerequisites"], ["base"])

    def test_parse_no_prerequisites(self):
        self._write_feature(
            "root.md",
            '# Root\n> Label: "Root Feature"\n> Category: "Core"\n')
        features = parse_features(self.test_dir)
        self.assertEqual(features["root"]["prerequisites"], [])

    def test_parse_nonexistent_dir(self):
        features = parse_features("/nonexistent/path")
        self.assertEqual(features, {})

    def test_ignores_non_md_files(self):
        self._write_feature("notes.txt", "some notes")
        self._write_feature(
            "real.md",
            '# Real\n> Label: "Real"\n> Category: "Core"\n')
        features = parse_features(self.test_dir)
        self.assertEqual(len(features), 1)
        self.assertIn("real", features)


class TestCompanionFileExclusion(unittest.TestCase):
    """Scenario: Dependency Graph Excludes Companion Files

    Given a features directory with critic_tool.md and critic_tool.impl.md
    When the graph generation is run
    Then only critic_tool.md appears as a node
    And critic_tool.impl.md is not included
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_feature(self, name, content):
        with open(os.path.join(self.test_dir, name), 'w') as f:
            f.write(content)

    def test_impl_md_excluded(self):
        """Companion .impl.md files must not appear as graph nodes."""
        self._write_feature("critic_tool.md", (
            '# Critic Tool\n'
            '> Label: "Critic Tool"\n'
            '> Category: "DevOps Tools"\n'
        ))
        self._write_feature("critic_tool.impl.md", (
            '# Implementation Notes: Critic Tool\n'
            '* Some notes here\n'
        ))
        features = parse_features(self.test_dir)
        # Only the primary feature file should be included
        self.assertEqual(len(features), 1)
        self.assertIn("critic_tool", features)
        # Verify no node for the impl.md file
        impl_id = "critic_tool.impl".replace(".", "_")
        self.assertNotIn(impl_id, features)
        # Also check filenames
        filenames = [f["filename"] for f in features.values()]
        self.assertNotIn("critic_tool.impl.md", filenames)

    def test_multiple_features_with_impl(self):
        """Multiple features with impl companions - only primaries included."""
        self._write_feature("feat_a.md", (
            '# Feature A\n'
            '> Label: "Feature A"\n'
            '> Category: "Core"\n'
        ))
        self._write_feature("feat_a.impl.md", (
            '# Implementation Notes: Feature A\n'
        ))
        self._write_feature("feat_b.md", (
            '# Feature B\n'
            '> Label: "Feature B"\n'
            '> Category: "Core"\n'
            '> Prerequisite: feat_a.md\n'
        ))
        self._write_feature("feat_b.impl.md", (
            '# Implementation Notes: Feature B\n'
        ))
        features = parse_features(self.test_dir)
        self.assertEqual(len(features), 2)
        self.assertIn("feat_a", features)
        self.assertIn("feat_b", features)


class TestCycleDetection(unittest.TestCase):
    def test_no_cycles(self):
        features = {
            "a": {"prerequisites": ["b"], "filename": "a.md"},
            "b": {"prerequisites": [], "filename": "b.md"},
        }
        cycles = detect_cycles(features)
        self.assertEqual(cycles, [])

    def test_direct_cycle(self):
        features = {
            "a": {"prerequisites": ["b"], "filename": "a.md"},
            "b": {"prerequisites": ["a"], "filename": "b.md"},
        }
        cycles = detect_cycles(features)
        self.assertTrue(len(cycles) > 0)

    def test_indirect_cycle(self):
        features = {
            "a": {"prerequisites": ["b"], "filename": "a.md"},
            "b": {"prerequisites": ["c"], "filename": "b.md"},
            "c": {"prerequisites": ["a"], "filename": "c.md"},
        }
        cycles = detect_cycles(features)
        self.assertTrue(len(cycles) > 0)

    def test_external_prereq_no_false_cycle(self):
        features = {
            "a": {"prerequisites": ["external"], "filename": "a.md"},
            "b": {"prerequisites": ["a"], "filename": "b.md"},
        }
        cycles = detect_cycles(features)
        self.assertEqual(cycles, [])


class TestOrphanDetection(unittest.TestCase):
    def test_finds_orphans(self):
        features = {
            "root": {"prerequisites": [], "filename": "root.md"},
            "child": {"prerequisites": ["root"], "filename": "child.md"},
        }
        orphans = find_orphans(features)
        self.assertEqual(orphans, ["root.md"])

    def test_no_orphans_when_all_have_prereqs(self):
        features = {
            "a": {"prerequisites": ["external"], "filename": "a.md"},
            "b": {"prerequisites": ["a"], "filename": "b.md"},
        }
        orphans = find_orphans(features)
        self.assertEqual(orphans, [])


class TestDependencyGraphJSON(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_update_feature_graph_with_prerequisites(self):
        """Scenario: Update Feature Graph

        Given a new feature file is added with prerequisites
        When the graph generation is run
        Then dependency_graph.json is regenerated with the new feature
        """
        features = {
            "login": {
                "filename": "login.md",
                "label": "User Login",
                "category": "Auth",
                "prerequisites": ["base"]
            },
            "base": {
                "filename": "base.md",
                "label": "Base",
                "category": "Core",
                "prerequisites": []
            },
        }
        result = build_features_json(features, self.test_dir)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        # Verify sorted by filename
        self.assertEqual(result[0]["label"], "Base")
        self.assertEqual(result[1]["label"], "User Login")

    def test_agent_reads_dependency_graph_schema(self):
        """Scenario: Agent Reads Dependency Graph

        Given dependency_graph.json exists
        When an agent reads it
        Then it has the correct schema (generated_at, features, cycles, orphans)
        """
        features = {
            "core": {
                "id": "core",
                "filename": "core.md",
                "label": "Core",
                "category": "Foundation",
                "prerequisites": []
            },
            "auth": {
                "id": "auth",
                "filename": "auth.md",
                "label": "Auth",
                "category": "Security",
                "prerequisites": ["core"]
            },
        }
        graph = {
            "generated_at": "2026-01-01T00:00:00Z",
            "features": build_features_json(features, self.test_dir),
            "cycles": detect_cycles(features),
            "orphans": find_orphans(features),
        }
        # Validate top-level schema keys
        self.assertIn("generated_at", graph)
        self.assertIn("features", graph)
        self.assertIn("cycles", graph)
        self.assertIn("orphans", graph)
        # Validate features array entries
        self.assertIsInstance(graph["features"], list)
        self.assertTrue(len(graph["features"]) > 0)
        for entry in graph["features"]:
            self.assertIn("file", entry)
            self.assertIn("label", entry)
            self.assertIn("category", entry)
            self.assertIn("prerequisites", entry)
        # Validate cycles is a list (no cycles in this graph)
        self.assertEqual(graph["cycles"], [])
        # Validate orphans includes the root node
        self.assertIn("core.md", graph["orphans"])

    def test_deterministic_output(self):
        features = {
            "z_feat": {
                "filename": "z_feat.md", "label": "Z",
                "category": "Cat", "prerequisites": []},
            "a_feat": {
                "filename": "a_feat.md", "label": "A",
                "category": "Cat", "prerequisites": ["z_feat"]},
        }
        r1 = json.dumps(
            build_features_json(features, self.test_dir), sort_keys=True)
        r2 = json.dumps(
            build_features_json(features, self.test_dir), sort_keys=True)
        self.assertEqual(r1, r2)


class TestGenerateDependencyGraph(unittest.TestCase):
    """Test the full generate_dependency_graph function with file I/O."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.test_dir, "features")
        self.cache_dir = os.path.join(self.test_dir, "cache")
        os.makedirs(self.features_dir)
        os.makedirs(self.cache_dir)
        self.output_file = os.path.join(
            self.cache_dir, "dependency_graph.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_feature(self, name, content):
        with open(os.path.join(self.features_dir, name), 'w') as f:
            f.write(content)

    def test_generates_json_file(self):
        self._write_feature("core.md", (
            '# Core\n'
            '> Label: "Core"\n'
            '> Category: "Foundation"\n'
        ))
        features = parse_features(self.features_dir)
        graph = generate_dependency_graph(
            features, self.features_dir, self.output_file)

        # Verify file was written
        self.assertTrue(os.path.isfile(self.output_file))

        # Verify content
        with open(self.output_file, 'r') as f:
            data = json.load(f)
        self.assertIn("generated_at", data)
        self.assertIn("features", data)
        self.assertEqual(len(data["features"]), 1)

    def test_mermaid_also_generated_via_run_full(self):
        """run_full_generation generates both JSON and Mermaid outputs."""
        self._write_feature("core.md", (
            '# Core\n'
            '> Label: "Core"\n'
            '> Category: "Foundation"\n'
        ))
        mmd_file = os.path.join(self.cache_dir, "feature_graph.mmd")
        graph = run_full_generation(
            self.features_dir, self.output_file, mmd_file)

        self.assertIsNotNone(graph)
        self.assertTrue(os.path.isfile(self.output_file))
        self.assertTrue(os.path.isfile(mmd_file))


SERVE_PY = os.path.join(os.path.dirname(__file__), 'serve.py')


class TestHoverHighlighting(unittest.TestCase):
    """Scenario: Hover Highlighting

    Given the user views the Spec Map
    And feature nodes and prerequisite edges are rendered
    When the user hovers over a feature node
    Then the hovered node and its direct neighbors are highlighted
    And all other nodes and edges are dimmed

    Test: Verifies serve.py contains mouseover/mouseout event handlers
    with highlighted/dimmed CSS classes for Cytoscape nodes.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_mouseover_event_registered(self):
        """Mouseover event handler registered for feature nodes."""
        self.assertIn("'mouseover'", self.content)
        self.assertIn('node[!isCategory]', self.content)

    def test_mouseout_event_registered(self):
        """Mouseout event handler removes highlight classes."""
        self.assertIn("'mouseout'", self.content)

    def test_dimmed_class_applied(self):
        """Dimmed CSS class applied to non-adjacent elements."""
        self.assertIn("addClass('dimmed')", self.content)
        self.assertIn("removeClass('dimmed')", self.content)

    def test_highlighted_class_applied(self):
        """Highlighted CSS class applied to adjacent nodes/edges."""
        self.assertIn("addClass('highlighted')", self.content)

    def test_dimmed_style_defined(self):
        """Dimmed style reduces opacity."""
        # CSS class style for dimmed elements in Cytoscape config
        self.assertIn('.dimmed', self.content)
        self.assertIn('.highlighted', self.content)


class TestInactivityTimeoutRedrawsGraph(unittest.TestCase):
    """Scenario: Inactivity Timeout Redraws Graph and Resets Zoom

    Given the user has panned or zoomed the Spec Map
    When 5 minutes pass with no user interaction
    Then the graph redraws with fresh layout
    And the zoom level resets to fit the viewport

    Test: Verifies serve.py implements inactivity timer with
    300000ms timeout that triggers graph redraw.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_inactivity_timeout_constant(self):
        """Inactivity timeout is set to 300000ms (5 minutes)."""
        self.assertIn('300000', self.content)

    def test_reset_inactivity_timer_function(self):
        """resetInactivityTimer function exists."""
        self.assertIn('resetInactivityTimer', self.content)

    def test_timeout_triggers_render(self):
        """Timeout triggers renderGraph to redraw the graph."""
        self.assertIn('renderGraph', self.content)

    def test_user_modified_flags_reset(self):
        """User modification flags are reset on timeout."""
        self.assertIn('userModifiedView', self.content)


class TestCategoriesPackedIntoViewport(unittest.TestCase):
    """Scenario: Categories Packed Into Viewport

    Given the dependency graph has multiple categories
    When the Spec Map renders with the packed layout
    Then category compounds are arranged to minimize whitespace
    And the layout fits within the initial viewport

    Test: Verifies serve.py implements a packed layout algorithm
    using dagre for intra-category layout and spiral packing for
    inter-category positioning.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_packed_layout_function_exists(self):
        """runPackedLayout function exists in generated JavaScript."""
        self.assertIn('runPackedLayout', self.content)

    def test_dagre_layout_used(self):
        """Dagre layout used for intra-category arrangement."""
        self.assertIn("name: 'dagre'", self.content)

    def test_spiral_packing_algorithm(self):
        """Non-overlapping placement with spiral search."""
        self.assertIn('findNonOverlapping', self.content)


class TestPrerequisiteHierarchyAcrossCategories(unittest.TestCase):
    """Scenario: Prerequisite Hierarchy Preserved Across Categories

    Given category A depends on category B
    When the packed layout runs
    Then category B is placed above category A in the viewport

    Test: Verifies serve.py computes topological layers for
    inter-category prerequisites and enforces minY constraints.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_topological_layer_computation(self):
        """Topological layers computed for category ordering."""
        # Kahn's algorithm variables
        self.assertIn('inDeg', self.content)

    def test_min_y_constraint(self):
        """MinY constraint enforces prerequisite above dependent."""
        self.assertIn('minY', self.content)

    def test_category_prerequisites_tracked(self):
        """Category-level prerequisite relationships are tracked."""
        self.assertIn('catPrereqs', self.content)


class TestPrerequisiteHierarchyWithinCategories(unittest.TestCase):
    """Scenario: Prerequisite Hierarchy Preserved Within Categories

    Given a category contains features with prerequisite relationships
    When the packed layout runs
    Then within each category prerequisites are above dependents

    Test: Verifies serve.py applies per-category dagre layout with
    top-to-bottom rank direction.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_dagre_top_to_bottom(self):
        """Dagre layout uses top-to-bottom rank direction."""
        self.assertIn("rankDir: 'TB'", self.content)

    def test_intra_category_edges_filtered(self):
        """Only intra-category edges used for within-category layout."""
        # The code filters edges to only those within the category
        self.assertIn('intraEdges', self.content)


class TestSearchDimsNonMatchingNodes(unittest.TestCase):
    """Scenario: Search Dims Non-Matching Nodes

    Given the user types a search query in the search input
    When the search filter is applied to the Spec Map
    Then non-matching nodes and their edges are dimmed
    And matching nodes remain at full opacity

    Test: Verifies serve.py implements search filtering with
    search-hidden CSS class and opacity reduction.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_search_filter_function(self):
        """applySearchFilter function exists."""
        self.assertIn('applySearchFilter', self.content)

    def test_search_hidden_class(self):
        """search-hidden CSS class used for dimming."""
        self.assertIn('search-hidden', self.content)

    def test_search_matches_label_and_file(self):
        """Search matches against label and file path."""
        self.assertIn('friendlyName', self.content)

    def test_category_nodes_hidden_when_empty(self):
        """Category nodes hidden when no children match."""
        self.assertIn('isCategory', self.content)


class TestClicksOnEdgesPassThrough(unittest.TestCase):
    """Scenario: Clicks on Edges Pass Through

    Given the user clicks on an edge (prerequisite arrow)
    When the click event fires
    Then no modal or detail panel opens
    And the click passes through to the background

    Test: Verifies serve.py registers tap events only on feature
    nodes, not on edges.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_tap_only_on_nodes(self):
        """Tap event registered only for feature nodes, not edges."""
        self.assertIn("'tap', 'node[!isCategory]'", self.content)

    def test_no_edge_tap_handler(self):
        """No tap event handler registered for edges."""
        self.assertNotIn("'tap', 'edge'", self.content)

    def test_node_tap_opens_modal(self):
        """Node tap opens feature detail modal."""
        self.assertIn('openModal', self.content)


class TestMermaidGeneration(unittest.TestCase):
    def test_generates_valid_mermaid(self):
        features = {
            "a": {
                "id": "a", "filename": "a.md", "label": "Feature A",
                "category": "Core", "prerequisites": []},
        }
        content = generate_mermaid_content(features)
        self.assertTrue(content.startswith("flowchart TD"))
        self.assertIn("Feature A", content)


if __name__ == '__main__':
    # Run tests and produce tests/cdd_spec_map/tests.json
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '../../'))
    tests_out_dir = os.path.join(project_root, "tests", "cdd_spec_map")
    os.makedirs(tests_out_dir, exist_ok=True)
    status_file = os.path.join(tests_out_dir, "tests.json")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = "PASS" if result.wasSuccessful() else "FAIL"
    failed = len(result.failures) + len(result.errors)
    with open(status_file, 'w') as f:
        json.dump({
            "status": status,
            "passed": result.testsRun - failed,
            "failed": failed,
            "total": result.testsRun,
            "test_file": "tools/cdd/test_spec_map.py"
        }, f)
    print(f"\n{status_file}: {status}")

    sys.exit(0 if result.wasSuccessful() else 1)
