import unittest
import os
import sys
import json
import tempfile
import shutil

# Add the tool directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))
from generate_tree import (
    parse_features, detect_cycles, find_orphans,
    build_features_json, generate_mermaid_content,
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
        self._write_feature("root.md", '# Root\n> Label: "Root Feature"\n> Category: "Core"\n')
        features = parse_features(self.test_dir)
        self.assertEqual(features["root"]["prerequisites"], [])

    def test_parse_nonexistent_dir(self):
        features = parse_features("/nonexistent/path")
        self.assertEqual(features, {})

    def test_ignores_non_md_files(self):
        self._write_feature("notes.txt", "some notes")
        self._write_feature("real.md", '# Real\n> Label: "Real"\n> Category: "Core"\n')
        features = parse_features(self.test_dir)
        self.assertEqual(len(features), 1)
        self.assertIn("real", features)


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
        """Update the feature graph: add a feature with prerequisites and verify output."""
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
        """Agent reads dependency_graph.json and validates its schema."""
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
            "z_feat": {"filename": "z_feat.md", "label": "Z", "category": "Cat", "prerequisites": []},
            "a_feat": {"filename": "a_feat.md", "label": "A", "category": "Cat", "prerequisites": ["z_feat"]},
        }
        r1 = json.dumps(build_features_json(features, self.test_dir), sort_keys=True)
        r2 = json.dumps(build_features_json(features, self.test_dir), sort_keys=True)
        self.assertEqual(r1, r2)


class TestMermaidGeneration(unittest.TestCase):
    def test_generates_valid_mermaid(self):
        features = {
            "a": {"id": "a", "filename": "a.md", "label": "Feature A", "category": "Core", "prerequisites": []},
        }
        content = generate_mermaid_content(features)
        self.assertTrue(content.startswith("flowchart TD"))
        self.assertIn("Feature A", content)


if __name__ == '__main__':
    import sys

    # Run tests and produce tests/software_map_generator/tests.json
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
    tests_out_dir = os.path.join(project_root, "tests", "software_map_generator")
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
            "tool": "software_map",
            "runner": "unittest"
        }, f)
    print(f"\n{status_file}: {status}")

    sys.exit(0 if result.wasSuccessful() else 1)
