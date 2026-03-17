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

    def test_discoveries_md_excluded(self):
        """Discovery sidecar .discoveries.md files must not appear as graph nodes."""
        self._write_feature("cdd_status_monitor.md", (
            '# CDD Status Monitor\n'
            '> Label: "CDD Monitor"\n'
            '> Category: "CDD Dashboard"\n'
        ))
        self._write_feature("cdd_status_monitor.discoveries.md", (
            '# User Testing Discoveries: CDD Monitor\n'
        ))
        features = parse_features(self.test_dir)
        self.assertEqual(len(features), 1)
        self.assertIn("cdd_status_monitor", features)
        filenames = [f["filename"] for f in features.values()]
        self.assertNotIn("cdd_status_monitor.discoveries.md", filenames)

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

    def test_neighborhood_used_for_prerequisites_and_dependents(self):
        """Hover uses neighborhood() to find direct prerequisites and dependents."""
        self.assertIn('.neighborhood()', self.content)


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

    Given the user clicks or double-clicks on an edge
    When the event fires
    Then the event passes through to the element below (canvas background or category bounding box)
    And no edge selection, tooltip, or modal is triggered
    And double-clicking an edge over a category bounding box triggers the category zoom
    And edge hover highlighting during node hover still functions normally

    Test: Verifies edges have events disabled so clicks and double-clicks
    pass through to nodes or background underneath.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_edge_events_disabled(self):
        """Edge style sets events to 'no' for click/double-click pass-through."""
        self.assertIn("'events': 'no'", self.content)

    def test_tap_only_on_nodes(self):
        """Tap event registered only for feature nodes, not edges."""
        self.assertIn("'tap', 'node[!isCategory]'", self.content)

    def test_no_edge_tap_handler(self):
        """No tap event handler registered for edges."""
        self.assertNotIn("'tap', 'edge'", self.content)

    def test_no_edge_dbltap_handler(self):
        """No dbltap event handler registered for edges."""
        self.assertNotIn("'dbltap', 'edge'", self.content)

    def test_node_tap_opens_modal(self):
        """Node tap opens feature detail modal."""
        self.assertIn('openModal', self.content)

    def test_category_dbltap_receives_passthrough(self):
        """Category dbltap handler exists to receive passed-through double-clicks."""
        self.assertIn("'dbltap', 'node[?isCategory]'", self.content)


class TestDoubleClickCategoryZoomsToFit(unittest.TestCase):
    """Scenario: Double-Click Category Zooms to Fit

    Given the User is viewing the Spec Map view
    When the User double-clicks on a category bounding box
    Then the graph animates a zoom that maximizes the view of that category
    And the interaction state is set to modified so auto-refresh preserves zoom
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_dbltap_handler_registered_on_category_nodes(self):
        """dbltap event registered for category nodes."""
        self.assertIn("'dbltap', 'node[?isCategory]'", self.content)

    def test_dbltap_animates_fit(self):
        """Double-click triggers animated fit to the category node."""
        self.assertIn('instance.animate', self.content)
        self.assertIn('fit:', self.content)

    def test_dbltap_sets_modified_view(self):
        """Double-click sets userModifiedView to preserve zoom on refresh."""
        # The dbltap handler must set userModifiedView = true
        self.assertIn('userModifiedView = true', self.content)


class TestSpecMapCanvasDoesNotOverflowViewport(unittest.TestCase):
    """Scenario: Spec Map Canvas Does Not Overflow Viewport

    Given the User is viewing the Spec Map view
    When the graph is rendered with any number of nodes
    Then the Cytoscape canvas fills exactly the available viewport area below the header
    And no page-level scrollbars appear on the body or html elements
    And changing the browser zoom level causes the canvas to resize
    And the Cytoscape canvas never extends beyond the visible screen area
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_map_view_overflow_hidden(self):
        """#map-view uses overflow:hidden to prevent content escaping."""
        self.assertIn('#map-view', self.content)
        # Check that overflow:hidden is on the map-view rule
        self.assertRegex(self.content, r'#map-view\{[^}]*overflow:\s*hidden')

    def test_cy_uses_absolute_inset(self):
        """#cy uses position:absolute;inset:0 instead of width/height percentages."""
        self.assertRegex(self.content, r'#cy\{[^}]*position:\s*absolute')
        self.assertRegex(self.content, r'#cy\{[^}]*inset:\s*0')

    def test_content_area_min_height_zero(self):
        """.content-area has min-height:0 for flex containment."""
        self.assertRegex(self.content, r'\.content-area\{[^}]*min-height:\s*0')

    def test_view_panel_min_height_zero(self):
        """.view-panel has min-height:0 for flex containment."""
        self.assertRegex(self.content, r'\.view-panel\{[^}]*min-height:\s*0')

    def test_map_view_min_height_zero(self):
        """#map-view has min-height:0 for flex containment."""
        self.assertRegex(self.content, r'#map-view\{[^}]*min-height:\s*0')

    def test_body_overflow_hidden(self):
        """html,body have overflow:hidden to prevent page scrollbars."""
        self.assertRegex(self.content, r'html,body\{[^}]*overflow:\s*hidden')

    def test_window_resize_triggers_cy_resize(self):
        """Window resize event calls cy.resize() to sync canvas size."""
        self.assertIn('cy.resize()', self.content)
        self.assertIn("'resize'", self.content)


class TestDoubleClickBackgroundRecentersGraph(unittest.TestCase):
    """Scenario: Double-Click Background Recenters Graph

    Given the User is viewing the Spec Map view
    And the User has zoomed or panned the graph away from the default fit
    When the User double-clicks on the canvas background (not on a node or category box)
    Then the graph recenters and zooms to fit all nodes in the viewable area
    And all manually-moved node positions are reset to the packed layout positions
    And the interaction state is reset to unmodified
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_dbltap_core_handler_registered(self):
        """dbltap handler registered on core (background)."""
        # The handler checks evt.target === instance for background clicks
        self.assertIn('evt.target === instance', self.content)

    def test_background_dbltap_calls_recenter(self):
        """Background double-click calls recenterGraph()."""
        self.assertIn('recenterGraph()', self.content)

    def test_background_dbltap_distinct_from_category(self):
        """Background dbltap is separate from category dbltap handler."""
        # Both handlers must exist: one for categories, one for background
        self.assertIn("'dbltap', 'node[?isCategory]'", self.content)
        # The core handler uses evt.target === instance check
        self.assertIn('evt.target === instance', self.content)


class TestFeatureDetailModalViaGraphNode(unittest.TestCase):
    """Scenario: Feature Detail Modal via Graph Node

    Given the User is viewing the Spec Map view
    When the User clicks a feature node
    Then the shared feature detail modal opens showing the rendered markdown content
    And the modal occupies 70% of the viewport width
    And metadata tags are displayed in a dedicated area above the markdown body
    And a font size adjustment control is visible in the modal header
    And the modal has an X button in the top-right corner
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_node_tap_opens_modal(self):
        """Node tap on feature node calls openModal."""
        self.assertIn('openModal', self.content)
        self.assertIn("'tap', 'node[!isCategory]'", self.content)

    def test_modal_width_70vw(self):
        """Feature detail modal uses 70vw width via .modal-content."""
        self.assertRegex(self.content, r'\.modal-content\{[^}]*width:\s*70vw')

    def test_metadata_area_above_body(self):
        """modal-metadata div exists before modal-body in the feature modal."""
        meta_pos = self.content.find('id="modal-metadata"')
        body_pos = self.content.find('id="modal-body"')
        self.assertGreater(meta_pos, -1)
        self.assertGreater(body_pos, -1)
        self.assertLess(meta_pos, body_pos)

    def test_font_size_control_in_modal_header(self):
        """Font size control (slider, minus, plus) present in feature modal header."""
        # Find the feature modal's header section
        modal_start = self.content.find('id="modal-overlay"')
        modal_end = self.content.find('</div>\n</div>', modal_start + 100)
        modal_html = self.content[modal_start:modal_end]
        self.assertIn('modal-font-controls', modal_html)
        self.assertIn('modal-font-slider', modal_html)

    def test_close_button_present(self):
        """X close button present in feature detail modal header."""
        self.assertIn('id="modal-close"', self.content)


class TestFontSizePersistsAcrossNodeClicks(unittest.TestCase):
    """Scenario: Font Size Persists Across Node Clicks (auto-web)

    Given the User clicks a feature node and adjusts the font size slider
    When the User closes the modal and clicks a different feature node
    Then the font size slider retains the previously set position.

    Tests that the session storage mechanism persists font size across
    different modal opens, verified via the shared font infrastructure.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_session_storage_key_used(self):
        """Font adjustment stored in sessionStorage for persistence."""
        self.assertIn('purlin-modal-font-adjust', self.content)

    def test_font_restored_on_page_load(self):
        """Font adjustment value is read from sessionStorage on page load."""
        self.assertIn('sessionStorage.getItem(MODAL_FONT_STORAGE_KEY', self.content)

    def test_all_sliders_synced_on_change(self):
        """setModalFont syncs all slider elements to the same value."""
        self.assertIn("querySelectorAll('.modal-font-slider')", self.content)

    def test_all_modal_contents_receive_css_var(self):
        """setModalFont applies --modal-font-adjust to all .modal-content elements."""
        self.assertIn("querySelectorAll('.modal-content')", self.content)
        self.assertIn("'--modal-font-adjust'", self.content)


class TestMetadataExtractionFromGraphNode(unittest.TestCase):
    """Scenario: Metadata Extraction from Graph Node (auto-web)

    Given a feature node has Label, Category, and multiple Prerequisites
    When the User clicks that feature node
    Then each metadata tag is displayed on its own row in the dedicated metadata area
    And tag names are highlighted
    And no metadata blockquotes appear in the rendered markdown body.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_extract_metadata_function_exists(self):
        """extractMetadata function parses blockquote metadata from markdown."""
        self.assertIn('function extractMetadata(md)', self.content)

    def test_extract_returns_tags_and_cleaned(self):
        """extractMetadata returns tags array and cleaned markdown without blockquotes."""
        self.assertIn('tags: tags, cleaned:', self.content)

    def test_render_metadata_generates_rows(self):
        """renderMetadata creates per-tag rows with key and value spans."""
        self.assertIn('function renderMetadata(tags)', self.content)
        self.assertIn('modal-meta-row', self.content)

    def test_metadata_displayed_in_dedicated_area(self):
        """openModal populates the modal-metadata element with rendered tags."""
        self.assertIn('renderMetadata(currentModal.specMeta)', self.content)

    def test_metadata_blockquotes_stripped_from_body(self):
        """Cleaned markdown (without blockquotes) is used for body rendering."""
        # extractMetadata strips metadata lines, openModal uses cleaned content
        self.assertIn('.specContent', self.content)
        self.assertIn('extractMetadata', self.content)


class TestSpecMapModalWidth(unittest.TestCase):
    """Scenario: Spec Map Modal Width (auto-web)

    Given the User is viewing the Spec Map view
    When the User clicks a feature node
    Then the modal width is 70% of the viewport width.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_modal_content_width_70vw(self):
        """The .modal-content CSS rule includes width:70vw."""
        self.assertRegex(self.content, r'\.modal-content\{[^}]*width:\s*70vw')

    def test_narrow_viewport_fallback(self):
        """On narrow viewports (<500px), modal falls back to 90vw."""
        self.assertIn('max-width:500px', self.content)
        self.assertIn('90vw', self.content)


class TestSpecMapModalMetadata(unittest.TestCase):
    """Scenario: Spec Map Modal Metadata (auto-web)

    Given the User is viewing the Spec Map view
    When the User clicks a feature node
    Then the metadata area displays tag names in a highlight color distinct from value text.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_meta_key_uses_accent_color(self):
        """modal-meta-key styled with --purlin-accent for highlighted tag names."""
        self.assertRegex(
            self.content,
            r'\.modal-meta-key\{[^}]*color:\s*var\(--purlin-accent\)')

    def test_meta_val_uses_muted_color(self):
        """modal-meta-val styled with --purlin-muted, distinct from key color."""
        self.assertRegex(
            self.content,
            r'\.modal-meta-val\{[^}]*color:\s*var\(--purlin-muted\)')

    def test_key_and_val_colors_differ(self):
        """Tag key (accent) and value (muted) use different color tokens."""
        # Both must be present with different tokens
        self.assertIn('--purlin-accent', self.content)
        self.assertIn('--purlin-muted', self.content)


class TestSpecMapModalFontSlider(unittest.TestCase):
    """Scenario: Spec Map Modal Font Slider (auto-web)

    Given the User clicks a feature node and opens the modal
    When the User adjusts the font size slider
    Then all text elements in the modal body scale together.
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_modal_body_font_uses_calc_with_adjust(self):
        """Modal body font-size uses calc() with --modal-font-adjust variable."""
        self.assertRegex(
            self.content,
            r'\.modal-body\{[^}]*font-size:\s*calc\([^)]*--modal-font-adjust')

    def test_headings_scale_with_adjust(self):
        """Modal body h1, h2, h3 use calc() with --modal-font-adjust."""
        for tag in ('h1', 'h2', 'h3'):
            pattern = rf'\.modal-body {tag}\{{{{font-size:calc\([^)]*--modal-font-adjust'
            self.assertRegex(self.content, pattern,
                             f'.modal-body {tag} missing font-size calc with --modal-font-adjust')

    def test_code_scales_with_adjust(self):
        """Code blocks in modal body scale with --modal-font-adjust."""
        # .modal-body code has multi-line CSS; check both selector and calc exist
        self.assertIn('.modal-body code', self.content)
        self.assertIn('calc(11px + var(--modal-font-adjust)', self.content)


class TestReactiveUpdateOnFeatureChange(unittest.TestCase):
    """Scenario: Reactive Update on Feature Change

    Given the CDD Dashboard server is running
    And the Spec Map view is active
    When a feature file is created, modified, or deleted
    Then the tool automatically regenerates the Mermaid exports
    And the tool automatically regenerates dependency_graph.json
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_file_watcher_function_exists(self):
        """_file_watcher function polls for feature file changes."""
        self.assertIn('def _file_watcher()', self.content)

    def test_poll_interval_set(self):
        """File watcher polls at 2-second intervals."""
        self.assertIn('POLL_INTERVAL = 2', self.content)

    def test_watcher_runs_in_daemon_thread(self):
        """File watcher runs as a daemon thread."""
        self.assertIn('daemon=True', self.content)
        self.assertIn('start_file_watcher', self.content)

    def test_watcher_calls_graph_generation(self):
        """File watcher triggers run_full_generation on changes."""
        self.assertIn('_run_graph_generation', self.content)


class TestZoomPreservedOnRefreshWhenModified(unittest.TestCase):
    """Scenario: Zoom Preserved on Refresh When Modified

    Given the User has zoomed or panned the graph in the Spec Map view
    When the dashboard auto-refreshes
    Then the current zoom level and pan position are preserved
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_user_modified_view_flag_exists(self):
        """userModifiedView flag tracks zoom/pan changes."""
        self.assertIn('var userModifiedView = false', self.content)

    def test_viewport_event_sets_flag(self):
        """Viewport events set userModifiedView when not programmatic."""
        self.assertIn('userModifiedView = true', self.content)

    def test_programmatic_guard_prevents_false_positive(self):
        """programmaticViewport flag prevents auto-fit from setting userModifiedView."""
        self.assertIn('var programmaticViewport = false', self.content)
        self.assertIn('if (!programmaticViewport)', self.content)

    def test_modified_view_preserves_zoom_on_refresh(self):
        """When userModifiedView is true, renderGraph preserves zoom/pan."""
        self.assertIn('if (userModifiedView)', self.content)


class TestZoomResetsOnRefreshWhenUnmodified(unittest.TestCase):
    """Scenario: Zoom Resets on Refresh When Unmodified

    Given the User has not modified zoom or pan since the last fit
    When the dashboard auto-refreshes
    Then the graph is re-fitted to the viewable area
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_user_modified_view_defaults_false(self):
        """userModifiedView starts as false for auto-fit behavior."""
        self.assertIn('var userModifiedView = false', self.content)

    def test_fit_called_in_render(self):
        """cy.fit() called during renderGraph for auto-fit."""
        self.assertIn('cy.fit(undefined, 40)', self.content)


class TestRecenterGraphButtonResetsViewAndInteractionState(unittest.TestCase):
    """Scenario: Recenter Graph Button Resets View and Interaction State

    Given the User has zoomed or panned the graph
    When the User clicks the Recenter Graph button
    Then the zoom and pan are reset to fit the graph in the viewable area
    And the interaction state is reset to unmodified
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_recenter_function_exists(self):
        """recenterGraph function is defined."""
        self.assertIn('function recenterGraph()', self.content)

    def test_recenter_resets_user_modified_view(self):
        """recenterGraph resets userModifiedView to false."""
        # Find recenterGraph function and verify it resets the flag
        idx = self.content.find('function recenterGraph()')
        block = self.content[idx:idx + 500]
        self.assertIn('userModifiedView = false', block)

    def test_recenter_calls_fit(self):
        """recenterGraph calls cy.fit() to zoom-to-fit."""
        idx = self.content.find('function recenterGraph()')
        block = self.content[idx:idx + 500]
        self.assertIn('cy.fit(undefined, 40)', block)

    def test_recenter_button_in_html(self):
        """Recenter Graph button exists in the Spec Map view."""
        self.assertIn('id="recenter-btn"', self.content)
        self.assertIn('recenterGraph()', self.content)


class TestNodePositionPreservedOnRefreshWhenManuallyMoved(unittest.TestCase):
    """Scenario: Node Position Preserved on Refresh When Manually Moved

    Given the User has dragged one or more nodes to new positions
    When the dashboard auto-refreshes and the graph has not changed substantively
    Then each moved node is restored to its saved position
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_user_modified_nodes_flag_exists(self):
        """userModifiedNodes flag tracks manual node drags."""
        self.assertIn('var userModifiedNodes = false', self.content)

    def test_dragfree_sets_modified_nodes(self):
        """Cytoscape dragfree event sets userModifiedNodes flag."""
        self.assertIn("'dragfree'", self.content)
        self.assertIn('userModifiedNodes = true', self.content)

    def test_save_node_positions_function(self):
        """saveNodePositions persists positions to localStorage."""
        self.assertIn('function saveNodePositions(key)', self.content)
        self.assertIn('localStorage.setItem', self.content)

    def test_restore_node_positions_function(self):
        """restoreNodePositions reads positions from localStorage."""
        self.assertIn('function restoreNodePositions(key)', self.content)
        self.assertIn('localStorage.getItem', self.content)

    def test_positions_restored_when_nodes_modified_and_hash_unchanged(self):
        """restoreNodePositions called when userModifiedNodes and hash unchanged."""
        self.assertIn('if (userModifiedNodes && !hashChanged)', self.content)
        self.assertIn('restoreNodePositions(newHash)', self.content)


class TestNodePositionsDiscardedWhenGraphChangesSubstantively(unittest.TestCase):
    """Scenario: Node Positions Discarded When Graph Changes Substantively

    Given the User has manually moved one or more nodes
    When a feature file is added, removed, or a node's category changes
    Then the saved node positions are discarded
    And the graph re-runs the full packed layout algorithm
    And the position interaction state resets to unmodified
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_content_hash_function_exists(self):
        """computeContentHash derives key from node file:category pairs."""
        self.assertIn('function computeContentHash(features)', self.content)

    def test_hash_change_clears_saved_positions(self):
        """When content hash changes, localStorage positions are removed."""
        self.assertIn('localStorage.removeItem(lastContentHash)', self.content)

    def test_hash_change_resets_modified_nodes(self):
        """userModifiedNodes reset to false when hash changes."""
        idx = self.content.find('var hashChanged')
        block = self.content[idx:idx + 300]
        self.assertIn('userModifiedNodes = false', block)

    def test_last_content_hash_tracked(self):
        """lastContentHash tracks the previous render's hash for comparison."""
        self.assertIn('var lastContentHash = null', self.content)
        self.assertIn('lastContentHash = newHash', self.content)


class TestRecenterGraphButtonResetsNodePositions(unittest.TestCase):
    """Scenario: Recenter Graph Button Resets Node Positions

    Given the User has manually moved one or more nodes
    When the User clicks the Recenter Graph button
    Then all node positions are reset to the packed layout positions
    And the position interaction state resets to unmodified
    And subsequent auto-refresh cycles re-layout rather than restore saved positions
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_recenter_resets_user_modified_nodes(self):
        """recenterGraph resets userModifiedNodes to false."""
        idx = self.content.find('function recenterGraph()')
        block = self.content[idx:idx + 500]
        self.assertIn('userModifiedNodes = false', block)

    def test_recenter_clears_local_storage(self):
        """recenterGraph removes saved positions from localStorage."""
        idx = self.content.find('function recenterGraph()')
        block = self.content[idx:idx + 500]
        self.assertIn('localStorage.removeItem', block)

    def test_recenter_reruns_packed_layout(self):
        """recenterGraph re-runs runPackedLayout for fresh positions."""
        idx = self.content.find('function recenterGraph()')
        block = self.content[idx:idx + 500]
        self.assertIn('runPackedLayout()', block)


class TestCategoryLabelsReadableAtOverviewZoom(unittest.TestCase):
    """Scenario: Category Labels Readable at Overview Zoom

    Given the User is viewing the Spec Map with all nodes visible
    When the zoom level is approximately 0.15 (typical fit-all)
    Then category group labels render at approximately 12 screen pixels
    And when zoomed in to 1.0 or higher labels remain at 12px model coords
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_label_base_font_constant(self):
        """LABEL_BASE_FONT constant defines base size for scaling."""
        self.assertIn('var LABEL_BASE_FONT = 12', self.content)

    def test_update_category_label_sizes_function(self):
        """updateCategoryLabelSizes function exists."""
        self.assertIn('function updateCategoryLabelSizes()', self.content)

    def test_font_size_clamped(self):
        """Font size clamped to [12, 80] range."""
        self.assertIn('Math.min(80, Math.max(12,', self.content)

    def test_scaling_inversely_with_zoom(self):
        """Font size scales as LABEL_BASE_FONT / zoom."""
        self.assertIn('LABEL_BASE_FONT / zoom', self.content)

    def test_labels_updated_on_zoom_event(self):
        """Label sizes update via rAF-debounced zoom handler."""
        self.assertIn('scheduleUpdateCategoryLabels', self.content)
        self.assertIn('requestAnimationFrame', self.content)


class TestUniformNodeAppearanceWithAnchorBorderDistinction(unittest.TestCase):
    """Scenario: Uniform Node Appearance with Anchor Border Distinction

    Given the User is viewing the Spec Map view
    When the graph renders all feature nodes
    Then all nodes have the same background color (--purlin-surface at low opacity)
    And all regular (non-anchor) nodes have the same border color (--purlin-border)
    And anchor nodes (arch_*, design_*, policy_*) have a green border (--purlin-status-good)
    """

    def setUp(self):
        with open(SERVE_PY) as f:
            self.content = f.read()

    def test_is_anchor_detected_by_filename_prefix(self):
        """isAnchor boolean derived from arch_/design_/policy_ filename prefix."""
        self.assertIn("isAnchor = /^(arch_|design_|policy_)/.test(filename)",
                       self.content)

    def test_is_anchor_stored_as_node_data(self):
        """isAnchor boolean stored as Cytoscape node data property."""
        self.assertIn('isAnchor: isAnchor', self.content)

    def test_anchor_style_selector(self):
        """Cytoscape style selector targets anchor nodes via [?isAnchor]."""
        self.assertIn("selector: 'node[?isAnchor]'", self.content)

    def test_anchor_border_uses_status_good(self):
        """Anchor nodes use c.statusGood (--purlin-status-good) border color."""
        self.assertIn("'border-color': c.statusGood", self.content)

    def test_anchor_border_width_thicker(self):
        """Anchor nodes have 3px border width (vs 2px regular)."""
        # Find the anchor style block
        idx = self.content.find("selector: 'node[?isAnchor]'")
        block = self.content[idx:idx + 200]
        self.assertIn("'border-width': 3", block)

    def test_regular_nodes_use_border_token(self):
        """Regular (non-anchor) nodes use c.border for border color."""
        self.assertIn("'border-color': c.border", self.content)

    def test_status_good_in_theme_colors(self):
        """getThemeColors includes statusGood from --purlin-status-good."""
        self.assertIn('statusGood', self.content)
        self.assertIn('--purlin-status-good', self.content)


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
