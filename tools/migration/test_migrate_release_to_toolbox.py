"""Unit tests for the release-to-toolbox migration script."""
import json
import os
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))

from tools.migration.migrate_release_to_toolbox import migrate


class TestMigration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.release_dir = os.path.join(self.tmpdir, ".purlin", "release")
        self.toolbox_dir = os.path.join(self.tmpdir, ".purlin", "toolbox")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _write_release_file(self, filename, data):
        os.makedirs(self.release_dir, exist_ok=True)
        path = os.path.join(self.release_dir, filename)
        with open(path, 'w') as f:
            json.dump(data, f)

    def _read_toolbox_file(self, filename):
        path = os.path.join(self.toolbox_dir, filename)
        with open(path) as f:
            return json.load(f)

    # --- Detection tests ---

    def test_nothing_to_migrate(self):
        """No .purlin/release/ directory → nothing_to_migrate."""
        result = migrate(self.tmpdir)
        self.assertEqual(result["status"], "nothing_to_migrate")
        self.assertEqual(result["tools_migrated"], 0)

    def test_already_migrated(self):
        """Migration marker exists → already_migrated."""
        self._write_release_file("config.json", {"steps": []})
        os.makedirs(self.toolbox_dir, exist_ok=True)
        marker = os.path.join(self.toolbox_dir, ".migrated_from_release")
        with open(marker, 'w') as f:
            json.dump({"migrated_at": "2026-01-01T00:00:00Z"}, f)

        result = migrate(self.tmpdir)
        self.assertEqual(result["status"], "already_migrated")

    # --- Migration tests ---

    def test_default_config_only(self):
        """Config.json with global steps but no local_steps.json → empty project_tools."""
        self._write_release_file("config.json", {
            "steps": [
                {"id": "purlin.verify_dependency_integrity", "enabled": True},
                {"id": "purlin.push_to_remote", "enabled": True},
            ]
        })

        result = migrate(self.tmpdir)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["tools_migrated"], 0)

        project = self._read_toolbox_file("project_tools.json")
        self.assertEqual(project["schema_version"], "2.0")
        self.assertEqual(len(project["tools"]), 0)

        community = self._read_toolbox_file("community_tools.json")
        self.assertEqual(len(community["tools"]), 0)

        marker = self._read_toolbox_file(".migrated_from_release")
        self.assertIn("migrated_at", marker)
        self.assertEqual(marker["tools_migrated"], 0)

    def test_custom_local_tools(self):
        """local_steps.json with 3 tools → 3 project tools with metadata."""
        self._write_release_file("config.json", {"steps": []})
        self._write_release_file("local_steps.json", {
            "steps": [
                {"id": "my_audit", "friendly_name": "My Audit", "description": "d",
                 "code": None, "agent_instructions": "Run audit"},
                {"id": "my_deploy", "friendly_name": "My Deploy", "description": "d2",
                 "code": "deploy.sh", "agent_instructions": None},
                {"id": "my_check", "friendly_name": "My Check", "description": "d3",
                 "code": None, "agent_instructions": None},
            ]
        })

        result = migrate(self.tmpdir)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["tools_migrated"], 3)

        project = self._read_toolbox_file("project_tools.json")
        self.assertEqual(len(project["tools"]), 3)

        for tool in project["tools"]:
            self.assertIn("metadata", tool)
            self.assertIn("last_updated", tool["metadata"])

        # Verify fields preserved
        self.assertEqual(project["tools"][0]["id"], "my_audit")
        self.assertEqual(project["tools"][0]["agent_instructions"], "Run audit")
        self.assertEqual(project["tools"][1]["code"], "deploy.sh")

    def test_empty_local_steps(self):
        """local_steps.json with empty steps array → empty project_tools."""
        self._write_release_file("local_steps.json", {"steps": []})

        result = migrate(self.tmpdir)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["tools_migrated"], 0)

        project = self._read_toolbox_file("project_tools.json")
        self.assertEqual(len(project["tools"]), 0)

    def test_corrupt_source_json(self):
        """Corrupt local_steps.json → error logged, empty project_tools, marker written."""
        os.makedirs(self.release_dir, exist_ok=True)
        with open(os.path.join(self.release_dir, "local_steps.json"), 'w') as f:
            f.write("{invalid json")
        self._write_release_file("config.json", {"steps": []})

        result = migrate(self.tmpdir)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["tools_migrated"], 0)

        # Marker should still be written
        marker_path = os.path.join(self.toolbox_dir, ".migrated_from_release")
        self.assertTrue(os.path.exists(marker_path))

    def test_dry_run(self):
        """Dry run creates no files."""
        self._write_release_file("local_steps.json", {
            "steps": [
                {"id": "tool1", "friendly_name": "T1", "description": "d",
                 "code": None, "agent_instructions": None},
            ]
        })

        result = migrate(self.tmpdir, dry_run=True)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["tools_migrated"], 1)

        # No toolbox directory should be created
        self.assertFalse(os.path.exists(self.toolbox_dir))

    def test_partial_migration_recovery(self):
        """Toolbox dir exists but no marker → re-runs migration, preserves existing tools."""
        self._write_release_file("local_steps.json", {
            "steps": [
                {"id": "tool1", "friendly_name": "T1", "description": "d",
                 "code": None, "agent_instructions": None},
            ]
        })

        # Create toolbox dir with an existing project tool (simulating manual use)
        os.makedirs(self.toolbox_dir, exist_ok=True)
        existing = {"schema_version": "2.0", "tools": [
            {"id": "existing_tool", "friendly_name": "Existing", "description": "e",
             "code": None, "agent_instructions": None},
        ]}
        with open(os.path.join(self.toolbox_dir, "project_tools.json"), 'w') as f:
            json.dump(existing, f)

        result = migrate(self.tmpdir)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["tools_migrated"], 1)

        # Marker should now exist
        marker_path = os.path.join(self.toolbox_dir, ".migrated_from_release")
        self.assertTrue(os.path.exists(marker_path))

        # Both existing and migrated tools should be present
        project = self._read_toolbox_file("project_tools.json")
        ids = [t["id"] for t in project["tools"]]
        self.assertIn("existing_tool", ids)
        self.assertIn("tool1", ids)
        self.assertEqual(len(project["tools"]), 2)

    def test_idempotent_rerun(self):
        """Running migration twice: second run returns already_migrated."""
        self._write_release_file("local_steps.json", {
            "steps": [
                {"id": "tool1", "friendly_name": "T1", "description": "d",
                 "code": None, "agent_instructions": None},
            ]
        })

        result1 = migrate(self.tmpdir)
        self.assertEqual(result1["status"], "migrated")

        result2 = migrate(self.tmpdir)
        self.assertEqual(result2["status"], "already_migrated")

    def test_marker_contains_checksum(self):
        """Marker file has correct checksum and tool count."""
        self._write_release_file("local_steps.json", {
            "steps": [
                {"id": "t1", "friendly_name": "T1", "description": "d",
                 "code": None, "agent_instructions": None},
                {"id": "t2", "friendly_name": "T2", "description": "d",
                 "code": None, "agent_instructions": None},
            ]
        })

        migrate(self.tmpdir)

        marker = self._read_toolbox_file(".migrated_from_release")
        self.assertEqual(marker["tools_migrated"], 2)
        self.assertIsNotNone(marker["source_local_steps_checksum"])
        self.assertIn("migrated_at", marker)

    def test_community_dir_created(self):
        """Migration creates the community/ subdirectory."""
        self._write_release_file("config.json", {"steps": []})

        migrate(self.tmpdir)

        community_dir = os.path.join(self.toolbox_dir, "community")
        self.assertTrue(os.path.isdir(community_dir))

    def test_merge_preserves_existing_project_tools(self):
        """Existing project_tools.json tools are preserved, migrated tools fill gaps."""
        self._write_release_file("config.json", {"steps": []})
        self._write_release_file("local_steps.json", {
            "steps": [
                {"id": "migrated_1", "friendly_name": "M1", "description": "d",
                 "code": None, "agent_instructions": None},
                {"id": "migrated_2", "friendly_name": "M2", "description": "d",
                 "code": None, "agent_instructions": None},
            ]
        })

        # Pre-existing project tools (manually created before migration)
        os.makedirs(self.toolbox_dir, exist_ok=True)
        existing = {"schema_version": "2.0", "tools": [
            {"id": "existing_a", "friendly_name": "EA", "description": "ea",
             "code": None, "agent_instructions": "Keep me"},
            {"id": "existing_b", "friendly_name": "EB", "description": "eb",
             "code": "run.sh", "agent_instructions": None},
        ]}
        with open(os.path.join(self.toolbox_dir, "project_tools.json"), 'w') as f:
            json.dump(existing, f)

        result = migrate(self.tmpdir)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["tools_migrated"], 2)

        project = self._read_toolbox_file("project_tools.json")
        self.assertEqual(len(project["tools"]), 4)
        ids = [t["id"] for t in project["tools"]]
        # Existing tools come first, migrated tools appended
        self.assertEqual(ids, ["existing_a", "existing_b", "migrated_1", "migrated_2"])
        # Existing tool content preserved
        self.assertEqual(project["tools"][0]["agent_instructions"], "Keep me")

    def test_merge_deduplicates_by_id(self):
        """Migrated tools with IDs already in project_tools are skipped."""
        self._write_release_file("config.json", {"steps": []})
        self._write_release_file("local_steps.json", {
            "steps": [
                {"id": "shared_tool", "friendly_name": "Old Name", "description": "old",
                 "code": None, "agent_instructions": "old instructions"},
                {"id": "new_tool", "friendly_name": "New", "description": "new",
                 "code": None, "agent_instructions": None},
            ]
        })

        os.makedirs(self.toolbox_dir, exist_ok=True)
        existing = {"schema_version": "2.0", "tools": [
            {"id": "shared_tool", "friendly_name": "Current Name", "description": "current",
             "code": None, "agent_instructions": "current instructions"},
        ]}
        with open(os.path.join(self.toolbox_dir, "project_tools.json"), 'w') as f:
            json.dump(existing, f)

        result = migrate(self.tmpdir)
        self.assertEqual(result["status"], "migrated")
        self.assertEqual(result["tools_migrated"], 1)  # only new_tool added

        project = self._read_toolbox_file("project_tools.json")
        self.assertEqual(len(project["tools"]), 2)
        # Existing version wins for the duplicate
        shared = [t for t in project["tools"] if t["id"] == "shared_tool"][0]
        self.assertEqual(shared["friendly_name"], "Current Name")
        self.assertEqual(shared["agent_instructions"], "current instructions")

    def test_release_dir_preserved(self):
        """Old .purlin/release/ is NOT deleted during migration."""
        self._write_release_file("config.json", {"steps": []})
        self._write_release_file("local_steps.json", {"steps": []})

        migrate(self.tmpdir)

        self.assertTrue(os.path.isdir(self.release_dir))
        self.assertTrue(os.path.exists(
            os.path.join(self.release_dir, "config.json")
        ))


if __name__ == "__main__":
    unittest.main()
