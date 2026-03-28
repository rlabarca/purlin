"""Unit tests for the Agentic Toolbox resolver.

Tests the three-source resolution algorithm and fuzzy matching.
"""
import json
import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))

from tools.toolbox.resolve import (
    _extract_tools,
    _make_resolved_entry,
    load_purlin_tools,
    load_project_tools,
    load_community_tools,
    resolve_toolbox,
    fuzzy_match,
)


class TestExtractTools(unittest.TestCase):
    def test_new_format(self):
        data = {"schema_version": "2.0", "tools": [{"id": "a"}]}
        self.assertEqual(_extract_tools(data), [{"id": "a"}])

    def test_old_format(self):
        data = {"steps": [{"id": "a"}]}
        self.assertEqual(_extract_tools(data), [{"id": "a"}])

    def test_none(self):
        self.assertEqual(_extract_tools(None), [])

    def test_empty(self):
        self.assertEqual(_extract_tools({}), [])


class TestLoadPurlinTools(unittest.TestCase):
    def test_load_valid(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "purlin.test", "friendly_name": "Test", "description": "d"}
            ]}, f)
            f.flush()
            tools = load_purlin_tools(f.name)
        os.unlink(f.name)
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["id"], "purlin.test")

    def test_load_missing(self):
        tools = load_purlin_tools("/nonexistent/path.json")
        self.assertEqual(tools, [])

    def test_load_old_format(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"steps": [
                {"id": "purlin.old", "friendly_name": "Old", "description": "d"}
            ]}, f)
            f.flush()
            tools = load_purlin_tools(f.name)
        os.unlink(f.name)
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["id"], "purlin.old")


class TestLoadProjectTools(unittest.TestCase):
    def test_valid_tools(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "my_tool", "friendly_name": "My Tool", "description": "d"}
            ]}, f)
            f.flush()
            tools, errors = load_project_tools(f.name)
        os.unlink(f.name)
        self.assertEqual(len(tools), 1)
        self.assertEqual(len(errors), 0)

    def test_reserved_purlin_prefix(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "purlin.bad", "friendly_name": "Bad", "description": "d"}
            ]}, f)
            f.flush()
            tools, errors = load_project_tools(f.name)
        os.unlink(f.name)
        self.assertEqual(len(tools), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("purlin.", errors[0])

    def test_reserved_community_prefix(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "community.bad", "friendly_name": "Bad", "description": "d"}
            ]}, f)
            f.flush()
            tools, errors = load_project_tools(f.name)
        os.unlink(f.name)
        self.assertEqual(len(tools), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("community.", errors[0])

    def test_missing_file(self):
        tools, errors = load_project_tools("/nonexistent/path.json")
        self.assertEqual(tools, [])
        self.assertEqual(errors, [])


class TestLoadCommunityTools(unittest.TestCase):
    def test_valid_community_tool(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create community directory structure
            tool_dir = os.path.join(tmpdir, "community", "community.test_tool")
            os.makedirs(tool_dir)
            tool_json = {
                "id": "community.test_tool",
                "friendly_name": "Test Tool",
                "description": "A test",
                "code": None,
                "agent_instructions": "Do something",
            }
            with open(os.path.join(tool_dir, "tool.json"), 'w') as f:
                json.dump(tool_json, f)

            # Create index
            index = {
                "schema_version": "2.0",
                "tools": [{
                    "id": "community.test_tool",
                    "source_dir": "community/community.test_tool",
                    "version": "1.0.0",
                    "source_repo": "git@example.com:user/tool.git",
                    "author": "test@example.com",
                    "last_pull_sha": "abc123",
                }]
            }
            index_path = os.path.join(tmpdir, "community_tools.json")
            with open(index_path, 'w') as f:
                json.dump(index, f)

            tools, warnings = load_community_tools(index_path, os.path.join(tmpdir, "community"))
            self.assertEqual(len(tools), 1)
            self.assertEqual(len(warnings), 0)
            self.assertEqual(tools[0]["id"], "community.test_tool")
            self.assertEqual(tools[0]["version"], "1.0.0")
            self.assertEqual(tools[0]["metadata"]["source_repo"], "git@example.com:user/tool.git")

    def test_missing_tool_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            index = {
                "schema_version": "2.0",
                "tools": [{
                    "id": "community.missing",
                    "source_dir": "community/community.missing",
                    "version": "1.0.0",
                    "source_repo": "git@example.com:user/tool.git",
                    "author": "test@example.com",
                    "last_pull_sha": "abc123",
                }]
            }
            index_path = os.path.join(tmpdir, "community_tools.json")
            with open(index_path, 'w') as f:
                json.dump(index, f)

            tools, warnings = load_community_tools(index_path, os.path.join(tmpdir, "community"))
            self.assertEqual(len(tools), 0)
            self.assertEqual(len(warnings), 1)
            self.assertIn("not found", warnings[0])

    def test_missing_index(self):
        tools, warnings = load_community_tools("/nonexistent.json", "/nonexistent")
        self.assertEqual(tools, [])
        self.assertEqual(warnings, [])


class TestResolveToolbox(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

        # Purlin tools
        self.purlin_path = os.path.join(self.tmpdir, "purlin_tools.json")
        with open(self.purlin_path, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "purlin.audit", "friendly_name": "Audit", "description": "d"},
                {"id": "purlin.push", "friendly_name": "Push", "description": "d"},
            ]}, f)

        # Project tools
        self.project_path = os.path.join(self.tmpdir, "project_tools.json")
        with open(self.project_path, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "my_check", "friendly_name": "My Check", "description": "d"},
            ]}, f)

        # Community setup
        self.community_dir = os.path.join(self.tmpdir, "community")
        tool_dir = os.path.join(self.community_dir, "community.ext_tool")
        os.makedirs(tool_dir)
        with open(os.path.join(tool_dir, "tool.json"), 'w') as f:
            json.dump({
                "id": "community.ext_tool",
                "friendly_name": "External Tool",
                "description": "d",
            }, f)
        self.community_index_path = os.path.join(self.tmpdir, "community_tools.json")
        with open(self.community_index_path, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [{
                "id": "community.ext_tool",
                "source_dir": "community/community.ext_tool",
                "version": "1.0.0",
                "source_repo": "git@example.com:user/tool.git",
                "author": "a@b.com",
                "last_pull_sha": "abc",
            }]}, f)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_all_three_sources(self):
        resolved, warnings, errors = resolve_toolbox(
            self.purlin_path, self.project_path,
            self.community_index_path, self.community_dir,
        )
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(resolved), 4)
        categories = [t["category"] for t in resolved]
        self.assertEqual(categories.count("purlin"), 2)
        self.assertEqual(categories.count("project"), 1)
        self.assertEqual(categories.count("community"), 1)

    def test_empty_registries(self):
        empty = os.path.join(self.tmpdir, "empty.json")
        with open(empty, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": []}, f)
        resolved, warnings, errors = resolve_toolbox(
            empty, "/nonexistent", "/nonexistent", "/nonexistent",
        )
        self.assertEqual(len(resolved), 0)
        self.assertEqual(len(errors), 0)

    def test_project_reserved_prefix_error(self):
        bad_project = os.path.join(self.tmpdir, "bad_project.json")
        with open(bad_project, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "purlin.bad", "friendly_name": "Bad", "description": "d"},
            ]}, f)
        resolved, warnings, errors = resolve_toolbox(
            self.purlin_path, bad_project,
            self.community_index_path, self.community_dir,
        )
        self.assertTrue(any("purlin." in e for e in errors))

    def test_unrecognized_fields_preserved(self):
        with open(self.purlin_path, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "purlin.x", "friendly_name": "X", "description": "d",
                 "custom_field": "value"},
            ]}, f)
        resolved, warnings, errors = resolve_toolbox(
            self.purlin_path, "/nonexistent", "/nonexistent", "/nonexistent",
        )
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0].get("custom_field"), "value")
        # Spec 2.1: unrecognized fields must produce a warning
        self.assertTrue(
            any("unrecognized field" in w for w in warnings),
            f"Expected an unrecognized-field warning, got: {warnings}",
        )

    def test_unrecognized_fields_warning(self):
        """Verify warning message content for unrecognized fields (spec 2.1)."""
        with open(self.purlin_path, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "purlin.warn_test", "friendly_name": "W", "description": "d",
                 "extra_a": 1, "extra_b": 2},
            ]}, f)
        resolved, warnings, errors = resolve_toolbox(
            self.purlin_path, "/nonexistent", "/nonexistent", "/nonexistent",
        )
        # Two unrecognized fields should produce two warnings
        unrecognized_warnings = [w for w in warnings if "unrecognized field" in w]
        self.assertEqual(len(unrecognized_warnings), 2)
        # Each warning must identify the tool and the field name
        self.assertTrue(any("'extra_a'" in w and "'purlin.warn_test'" in w for w in unrecognized_warnings))
        self.assertTrue(any("'extra_b'" in w and "'purlin.warn_test'" in w for w in unrecognized_warnings))
        # Fields are still preserved in the resolved output
        self.assertEqual(resolved[0]["extra_a"], 1)
        self.assertEqual(resolved[0]["extra_b"], 2)

    def test_corrupt_purlin_json(self):
        corrupt = os.path.join(self.tmpdir, "corrupt.json")
        with open(corrupt, 'w') as f:
            f.write("{invalid json")
        resolved, warnings, errors = resolve_toolbox(
            corrupt, "/nonexistent", "/nonexistent", "/nonexistent",
        )
        self.assertEqual(len(resolved), 0)
        self.assertTrue(any("invalid JSON" in e for e in errors))


class TestFuzzyMatch(unittest.TestCase):
    def setUp(self):
        self.tools = [
            {"id": "purlin.verify_dependency_integrity", "friendly_name": "Verify Dependency Integrity", "category": "purlin"},
            {"id": "my_audit", "friendly_name": "My Custom Audit", "category": "project"},
            {"id": "purlin.doc_consistency_check", "friendly_name": "Documentation Consistency", "category": "purlin"},
            {"id": "doc_consistency_framework", "friendly_name": "Framework Doc Consistency", "category": "project"},
        ]

    def test_exact_id_match(self):
        matches = fuzzy_match("purlin.verify_dependency_integrity", self.tools)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "purlin.verify_dependency_integrity")

    def test_partial_id_match(self):
        matches = fuzzy_match("dependency", self.tools)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "purlin.verify_dependency_integrity")

    def test_friendly_name_match(self):
        matches = fuzzy_match("Custom", self.tools)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "my_audit")

    def test_ambiguous_match(self):
        matches = fuzzy_match("doc", self.tools)
        self.assertEqual(len(matches), 2)
        ids = {m["id"] for m in matches}
        self.assertIn("purlin.doc_consistency_check", ids)
        self.assertIn("doc_consistency_framework", ids)

    def test_no_match(self):
        matches = fuzzy_match("nonexistent_xyz", self.tools)
        self.assertEqual(len(matches), 0)

    def test_case_insensitive(self):
        matches = fuzzy_match("DEPENDENCY", self.tools)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "purlin.verify_dependency_integrity")

    def test_exact_match_wins_over_substring(self):
        matches = fuzzy_match("my_audit", self.tools)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["id"], "my_audit")


if __name__ == "__main__":
    unittest.main()
