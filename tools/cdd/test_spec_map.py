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
    with open(status_file, 'w') as f:
        json.dump({
            "status": status,
            "tests": result.testsRun,
            "failures": len(result.failures) + len(result.errors),
            "tool": "cdd_spec_map",
            "runner": "unittest"
        }, f)
    print(f"\n{status_file}: {status}")

    sys.exit(0 if result.wasSuccessful() else 1)
