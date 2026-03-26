"""Unit tests for the Agentic Toolbox management CLI."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))

from tools.toolbox import manage


class TestManageCLI(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_path = os.path.join(self.tmpdir, "project_tools.json")
        self.purlin_path = os.path.join(self.tmpdir, "purlin_tools.json")

        # Write empty project tools
        with open(self.project_path, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": []}, f)

        # Write minimal purlin tools
        with open(self.purlin_path, 'w') as f:
            json.dump({"schema_version": "2.0", "tools": [
                {"id": "purlin.test", "friendly_name": "Test", "description": "d"}
            ]}, f)

        # Patch paths
        self._orig_project = manage.PROJECT_TOOLS_PATH
        self._orig_purlin = manage.PURLIN_TOOLS_PATH
        manage.PROJECT_TOOLS_PATH = self.project_path
        manage.PURLIN_TOOLS_PATH = self.purlin_path

    def tearDown(self):
        manage.PROJECT_TOOLS_PATH = self._orig_project
        manage.PURLIN_TOOLS_PATH = self._orig_purlin
        import shutil
        shutil.rmtree(self.tmpdir)

    def _load_project_tools(self):
        with open(self.project_path) as f:
            return json.load(f)["tools"]

    def _make_args(self, **kwargs):
        """Create a mock args object."""
        class Args:
            pass
        a = Args()
        for k, v in kwargs.items():
            setattr(a, k, v)
        return a

    # --- Create tests ---

    def test_create_valid(self):
        args = self._make_args(
            id="my_tool", name="My Tool", desc="A description",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        result = manage.cmd_create(args)
        self.assertEqual(result, 0)
        tools = self._load_project_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["id"], "my_tool")
        self.assertEqual(tools[0]["tags"], [])

    def test_create_with_tags(self):
        args = self._make_args(
            id="tagged", name="Tagged", desc="desc",
            code=None, agent_instructions=None, tags="release,audit", dry_run=False,
        )
        result = manage.cmd_create(args)
        self.assertEqual(result, 0)
        tools = self._load_project_tools()
        self.assertEqual(tools[0]["tags"], ["release", "audit"])

    def test_create_empty_id(self):
        args = self._make_args(
            id="", name="Name", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        result = manage.cmd_create(args)
        self.assertEqual(result, 1)

    def test_create_reserved_purlin_prefix(self):
        args = self._make_args(
            id="purlin.bad", name="Bad", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        result = manage.cmd_create(args)
        self.assertEqual(result, 1)

    def test_create_reserved_community_prefix(self):
        args = self._make_args(
            id="community.bad", name="Bad", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        result = manage.cmd_create(args)
        self.assertEqual(result, 1)

    def test_create_duplicate_project(self):
        # Create first
        args = self._make_args(
            id="dup", name="Dup", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        manage.cmd_create(args)
        # Try duplicate
        result = manage.cmd_create(args)
        self.assertEqual(result, 1)

    def test_create_duplicate_purlin(self):
        args = self._make_args(
            id="purlin.test", name="Test", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        # This should fail on reserved prefix, not duplicate check
        result = manage.cmd_create(args)
        self.assertEqual(result, 1)

    def test_create_dry_run(self):
        args = self._make_args(
            id="dry", name="Dry", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=True,
        )
        result = manage.cmd_create(args)
        self.assertEqual(result, 0)
        # File should still be empty
        tools = self._load_project_tools()
        self.assertEqual(len(tools), 0)

    def test_create_with_code_and_instructions(self):
        args = self._make_args(
            id="full", name="Full", desc="desc",
            code="echo hello", agent_instructions="Run the command",
            tags="test", dry_run=False,
        )
        result = manage.cmd_create(args)
        self.assertEqual(result, 0)
        tools = self._load_project_tools()
        self.assertEqual(tools[0]["code"], "echo hello")
        self.assertEqual(tools[0]["agent_instructions"], "Run the command")

    def test_create_sets_metadata(self):
        args = self._make_args(
            id="meta", name="Meta", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        manage.cmd_create(args)
        tools = self._load_project_tools()
        self.assertIn("metadata", tools[0])
        self.assertIn("last_updated", tools[0]["metadata"])

    # --- Modify tests ---

    def test_modify_name(self):
        # Create first
        args = self._make_args(
            id="mod", name="Original", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        manage.cmd_create(args)

        args = self._make_args(
            id="mod", name="Updated", desc=None, code=None,
            agent_instructions=None, tags=None,
            clear_code=False, clear_agent_instructions=False, dry_run=False,
        )
        result = manage.cmd_modify(args)
        self.assertEqual(result, 0)
        tools = self._load_project_tools()
        self.assertEqual(tools[0]["friendly_name"], "Updated")

    def test_modify_no_flags(self):
        args = self._make_args(
            id="mod", name=None, desc=None, code=None,
            agent_instructions=None, tags=None,
            clear_code=False, clear_agent_instructions=False, dry_run=False,
        )
        result = manage.cmd_modify(args)
        self.assertEqual(result, 1)

    def test_modify_nonexistent(self):
        args = self._make_args(
            id="nope", name="New", desc=None, code=None,
            agent_instructions=None, tags=None,
            clear_code=False, clear_agent_instructions=False, dry_run=False,
        )
        result = manage.cmd_modify(args)
        self.assertEqual(result, 1)

    def test_modify_mutual_exclusion(self):
        args = self._make_args(
            id="mod", name=None, desc=None, code="echo",
            agent_instructions=None, tags=None,
            clear_code=True, clear_agent_instructions=False, dry_run=False,
        )
        result = manage.cmd_modify(args)
        self.assertEqual(result, 1)

    # --- Delete tests ---

    def test_delete_existing(self):
        # Create first
        args = self._make_args(
            id="del_me", name="Delete", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        manage.cmd_create(args)

        args = self._make_args(id="del_me", dry_run=False)
        result = manage.cmd_delete(args)
        self.assertEqual(result, 0)
        tools = self._load_project_tools()
        self.assertEqual(len(tools), 0)

    def test_delete_nonexistent(self):
        args = self._make_args(id="nope", dry_run=False)
        result = manage.cmd_delete(args)
        self.assertEqual(result, 1)

    def test_delete_dry_run(self):
        args = self._make_args(
            id="keep", name="Keep", desc="desc",
            code=None, agent_instructions=None, tags=None, dry_run=False,
        )
        manage.cmd_create(args)

        args = self._make_args(id="keep", dry_run=True)
        result = manage.cmd_delete(args)
        self.assertEqual(result, 0)
        # Should still exist
        tools = self._load_project_tools()
        self.assertEqual(len(tools), 1)

    def test_delete_preserves_other_tools(self):
        for i in range(3):
            args = self._make_args(
                id=f"tool_{i}", name=f"Tool {i}", desc="desc",
                code=None, agent_instructions=None, tags=None, dry_run=False,
            )
            manage.cmd_create(args)

        args = self._make_args(id="tool_1", dry_run=False)
        manage.cmd_delete(args)

        tools = self._load_project_tools()
        self.assertEqual(len(tools), 2)
        ids = [t["id"] for t in tools]
        self.assertIn("tool_0", ids)
        self.assertIn("tool_2", ids)
        self.assertNotIn("tool_1", ids)


if __name__ == "__main__":
    unittest.main()
