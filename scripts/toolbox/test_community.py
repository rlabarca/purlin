"""Unit tests for the Agentic Toolbox community lifecycle operations.

Tests add, pull, push helpers per features/toolbox_community.md.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))

from tools.toolbox import community


def _make_git_repo(path, tool_json=None, extra_files=None):
    """Create a bare-minimum git repo with optional tool.json."""
    os.makedirs(path, exist_ok=True)
    subprocess.run(["git", "init", path], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", path, "config", "user.email", "test@test.com"],
        capture_output=True, check=True
    )
    subprocess.run(
        ["git", "-C", path, "config", "user.name", "Test"],
        capture_output=True, check=True
    )

    if tool_json is not None:
        with open(os.path.join(path, "tool.json"), 'w') as f:
            json.dump(tool_json, f)

    if extra_files:
        for name, content in extra_files.items():
            with open(os.path.join(path, name), 'w') as f:
                f.write(content)

    subprocess.run(["git", "-C", path, "add", "-A"], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", path, "commit", "-m", "initial"],
        capture_output=True, check=True
    )


class TestNormalizeId(unittest.TestCase):
    def test_adds_prefix(self):
        self.assertEqual(community._normalize_id("deploy"), "community.deploy")

    def test_preserves_existing_prefix(self):
        self.assertEqual(
            community._normalize_id("community.deploy"), "community.deploy"
        )


class TestCmdAdd(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create a mock source repo
        self.source_repo = os.path.join(self.tmpdir, "source_repo")
        self.tool_def = {
            "id": "deploy_vercel",
            "friendly_name": "Deploy to Vercel",
            "description": "Deploy via Vercel CLI",
            "code": "vercel deploy",
            "version": "1.0.0",
            "metadata": {"author": "dev@example.com"},
        }
        _make_git_repo(self.source_repo, self.tool_def)

        # Override module-level paths for testing
        self._orig_community_path = community.COMMUNITY_TOOLS_PATH
        self._orig_community_dir = community.COMMUNITY_DIR
        self._orig_project_path = community.PROJECT_TOOLS_PATH
        self._orig_purlin_path = community.PURLIN_TOOLS_PATH

        community.COMMUNITY_TOOLS_PATH = os.path.join(self.tmpdir, "community_tools.json")
        community.COMMUNITY_DIR = os.path.join(self.tmpdir, "community")
        community.PROJECT_TOOLS_PATH = os.path.join(self.tmpdir, "project_tools.json")
        community.PURLIN_TOOLS_PATH = os.path.join(self.tmpdir, "purlin_tools.json")

        # Create empty registries
        for path in (community.COMMUNITY_TOOLS_PATH, community.PROJECT_TOOLS_PATH,
                      community.PURLIN_TOOLS_PATH):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump({"schema_version": "2.0", "tools": []}, f)

    def tearDown(self):
        community.COMMUNITY_TOOLS_PATH = self._orig_community_path
        community.COMMUNITY_DIR = self._orig_community_dir
        community.PROJECT_TOOLS_PATH = self._orig_project_path
        community.PURLIN_TOOLS_PATH = self._orig_purlin_path
        shutil.rmtree(self.tmpdir)

    def test_add_valid_repo(self):
        result = community.cmd_add(self.source_repo)
        self.assertEqual(result["status"], "added")
        self.assertEqual(result["tool_id"], "community.deploy_vercel")
        self.assertEqual(result["version"], "1.0.0")

        # Verify tool directory created
        tool_dir = os.path.join(community.COMMUNITY_DIR, "community.deploy_vercel")
        self.assertTrue(os.path.exists(os.path.join(tool_dir, "tool.json")))

        # Verify registry updated
        with open(community.COMMUNITY_TOOLS_PATH) as f:
            reg = json.load(f)
        self.assertEqual(len(reg["tools"]), 1)
        self.assertEqual(reg["tools"][0]["id"], "community.deploy_vercel")

    def test_add_auto_prefixes_id(self):
        result = community.cmd_add(self.source_repo)
        self.assertEqual(result["tool_id"], "community.deploy_vercel")
        self.assertIn("renamed_from", result)

    def test_add_missing_tool_json(self):
        # Create repo without tool.json
        empty_repo = os.path.join(self.tmpdir, "empty_repo")
        _make_git_repo(empty_repo, extra_files={"README.md": "hello"})
        result = community.cmd_add(empty_repo)
        self.assertEqual(result["status"], "error")
        self.assertIn("tool.json", result["message"])

    def test_add_missing_required_fields(self):
        bad_repo = os.path.join(self.tmpdir, "bad_repo")
        _make_git_repo(bad_repo, {"id": "test"})  # missing friendly_name, description
        result = community.cmd_add(bad_repo)
        self.assertEqual(result["status"], "error")
        self.assertIn("missing required fields", result["message"])

    def test_add_id_collision(self):
        # Add once
        community.cmd_add(self.source_repo)
        # Add again — collision
        result = community.cmd_add(self.source_repo)
        self.assertEqual(result["status"], "error")
        self.assertIn("already exists", result["message"])

    def test_add_dry_run(self):
        result = community.cmd_add(self.source_repo, dry_run=True)
        self.assertEqual(result["status"], "dry_run")
        # Verify no files created
        self.assertFalse(os.path.exists(os.path.join(
            community.COMMUNITY_DIR, "community.deploy_vercel"
        )))

    def test_add_invalid_url(self):
        result = community.cmd_add("/nonexistent/repo/path")
        self.assertEqual(result["status"], "error")
        self.assertIn("Failed to clone", result["message"])


class TestCmdPull(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

        self._orig_community_path = community.COMMUNITY_TOOLS_PATH
        self._orig_community_dir = community.COMMUNITY_DIR
        self._orig_project_path = community.PROJECT_TOOLS_PATH
        self._orig_purlin_path = community.PURLIN_TOOLS_PATH

        community.COMMUNITY_TOOLS_PATH = os.path.join(self.tmpdir, "community_tools.json")
        community.COMMUNITY_DIR = os.path.join(self.tmpdir, "community")
        community.PROJECT_TOOLS_PATH = os.path.join(self.tmpdir, "project_tools.json")
        community.PURLIN_TOOLS_PATH = os.path.join(self.tmpdir, "purlin_tools.json")

        for path in (community.PROJECT_TOOLS_PATH, community.PURLIN_TOOLS_PATH):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump({"schema_version": "2.0", "tools": []}, f)

    def tearDown(self):
        community.COMMUNITY_TOOLS_PATH = self._orig_community_path
        community.COMMUNITY_DIR = self._orig_community_dir
        community.PROJECT_TOOLS_PATH = self._orig_project_path
        community.PURLIN_TOOLS_PATH = self._orig_purlin_path
        shutil.rmtree(self.tmpdir)

    def test_pull_empty_registry(self):
        with open(community.COMMUNITY_TOOLS_PATH, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": []}, f)
        result = community.cmd_pull()
        self.assertEqual(result["status"], "empty")

    def test_pull_up_to_date(self):
        # Create source repo and add tool
        source = os.path.join(self.tmpdir, "source")
        tool_def = {
            "id": "community.test",
            "friendly_name": "Test",
            "description": "test",
        }
        _make_git_repo(source, tool_def)

        head_sha = subprocess.run(
            ["git", "-C", source, "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        # Set up local tool
        tool_dir = os.path.join(community.COMMUNITY_DIR, "community.test")
        os.makedirs(tool_dir, exist_ok=True)
        with open(os.path.join(tool_dir, "tool.json"), 'w') as f:
            json.dump(tool_def, f)

        with open(community.COMMUNITY_TOOLS_PATH, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [{
                "id": "community.test",
                "source_dir": "community/community.test",
                "version": "1.0.0",
                "source_repo": source,
                "last_pull_sha": head_sha,
            }]}, f)

        result = community.cmd_pull("community.test")
        self.assertIn("community.test", result["up_to_date"])

    def test_pull_not_found(self):
        with open(community.COMMUNITY_TOOLS_PATH, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": []}, f)
        result = community.cmd_pull("community.nonexistent")
        self.assertEqual(result["status"], "error")

    def test_pull_updates_when_changed(self):
        # Create source repo
        source = os.path.join(self.tmpdir, "source")
        tool_def = {
            "id": "community.test",
            "friendly_name": "Test",
            "description": "test",
        }
        _make_git_repo(source, tool_def)
        old_sha = subprocess.run(
            ["git", "-C", source, "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        # Set up local tool matching old SHA
        tool_dir = os.path.join(community.COMMUNITY_DIR, "community.test")
        os.makedirs(tool_dir, exist_ok=True)
        with open(os.path.join(tool_dir, "tool.json"), 'w') as f:
            json.dump(tool_def, f)

        with open(community.COMMUNITY_TOOLS_PATH, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [{
                "id": "community.test",
                "source_dir": "community/community.test",
                "version": "1.0.0",
                "source_repo": source,
                "last_pull_sha": old_sha,
            }]}, f)

        # Make a new commit in source
        updated_def = dict(tool_def)
        updated_def["description"] = "updated test"
        with open(os.path.join(source, "tool.json"), 'w') as f:
            json.dump(updated_def, f)
        subprocess.run(["git", "-C", source, "add", "-A"], capture_output=True, check=True)
        subprocess.run(
            ["git", "-C", source, "commit", "-m", "update"],
            capture_output=True, check=True
        )

        result = community.cmd_pull("community.test")
        self.assertEqual(len(result["updated"]), 1)

        # Verify local file was updated
        with open(os.path.join(tool_dir, "tool.json")) as f:
            local = json.load(f)
        self.assertEqual(local["description"], "updated test")


class TestCmdPush(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

        self._orig_community_path = community.COMMUNITY_TOOLS_PATH
        self._orig_community_dir = community.COMMUNITY_DIR
        self._orig_project_path = community.PROJECT_TOOLS_PATH
        self._orig_purlin_path = community.PURLIN_TOOLS_PATH

        community.COMMUNITY_TOOLS_PATH = os.path.join(self.tmpdir, "community_tools.json")
        community.COMMUNITY_DIR = os.path.join(self.tmpdir, "community")
        community.PROJECT_TOOLS_PATH = os.path.join(self.tmpdir, "project_tools.json")
        community.PURLIN_TOOLS_PATH = os.path.join(self.tmpdir, "purlin_tools.json")

        for path in (community.COMMUNITY_TOOLS_PATH, community.PURLIN_TOOLS_PATH):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as f:
                json.dump({"schema_version": "2.0", "tools": []}, f)

    def tearDown(self):
        community.COMMUNITY_TOOLS_PATH = self._orig_community_path
        community.COMMUNITY_DIR = self._orig_community_dir
        community.PROJECT_TOOLS_PATH = self._orig_project_path
        community.PURLIN_TOOLS_PATH = self._orig_purlin_path
        shutil.rmtree(self.tmpdir)

    def test_push_purlin_tool_blocked(self):
        with open(community.PURLIN_TOOLS_PATH, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "purlin.test", "friendly_name": "T", "description": "d"}
            ]}, f)
        result = community.cmd_push("purlin.test")
        self.assertEqual(result["status"], "error")
        self.assertIn("cannot be pushed", result["message"])

    def test_push_project_without_url_errors(self):
        with open(community.PROJECT_TOOLS_PATH, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "my_tool", "friendly_name": "T", "description": "d"}
            ]}, f)
        result = community.cmd_push("my_tool")
        self.assertEqual(result["status"], "error")
        self.assertIn("Specify a git URL", result["message"])

    def test_push_project_dry_run(self):
        with open(community.PROJECT_TOOLS_PATH, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "my_tool", "friendly_name": "T", "description": "d"}
            ]}, f)
        result = community.cmd_push("my_tool", "git@example.com:user/tool.git",
                                    version="1.0.0", dry_run=True)
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["action"], "promote")
        self.assertEqual(result["new_id"], "community.my_tool")

    def test_push_not_found(self):
        result = community.cmd_push("nonexistent")
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["message"])


if __name__ == "__main__":
    unittest.main()
