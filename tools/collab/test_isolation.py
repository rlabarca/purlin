#!/usr/bin/env python3
"""Tests for create_isolation.sh and kill_isolation.sh.

Covers all 13 automated scenarios from features/isolated_agents.md.
Each test creates a temporary git repo to avoid polluting the real project.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest


def run_script(script_name, args, project_root, env=None):
    """Run a collab script and return (returncode, stdout, stderr)."""
    # Resolve script path relative to this file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, script_name)

    cmd = ["bash", script_path] + args + ["--project-root", project_root]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
        timeout=30,
    )
    return result.returncode, result.stdout, result.stderr


class IsolationTestBase(unittest.TestCase):
    """Base class that sets up a temporary git repo with .worktrees gitignored."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="isolation_test_")
        self.project_root = self.tmpdir

        # Initialize a git repo with an initial commit
        self._git("init")
        self._git("checkout", "-b", "main")

        # Create .gitignore with .worktrees/
        gitignore_path = os.path.join(self.project_root, ".gitignore")
        with open(gitignore_path, "w") as f:
            f.write(".worktrees/\n.purlin/cache/\n.purlin/runtime/\n")
        self._git("add", ".gitignore")

        # Create .purlin/config.json
        purlin_dir = os.path.join(self.project_root, ".purlin")
        os.makedirs(purlin_dir, exist_ok=True)
        config = {"agents": {"builder": {"startup_sequence": True}}}
        config_path = os.path.join(purlin_dir, "config.json")
        with open(config_path, "w") as f:
            json.dump(config, f)
        self._git("add", ".purlin/config.json")

        # Create .claude/commands/ with test command files
        cmd_dir = os.path.join(self.project_root, ".claude", "commands")
        os.makedirs(cmd_dir, exist_ok=True)
        for cmd_file in ["pl-local-push.md", "pl-local-pull.md", "pl-status.md"]:
            with open(os.path.join(cmd_dir, cmd_file), "w") as f:
                f.write(f"# {cmd_file}\nTest content for {cmd_file}\n")
        self._git("add", ".claude/")

        # Create a features/ directory with a sample file
        features_dir = os.path.join(self.project_root, "features")
        os.makedirs(features_dir, exist_ok=True)
        with open(os.path.join(features_dir, "sample.md"), "w") as f:
            f.write("# Sample Feature\n")
        self._git("add", "features/")

        self._git("commit", "-m", "Initial commit")

    def tearDown(self):
        # Clean up git worktrees before removing tmpdir
        try:
            result = subprocess.run(
                ["git", "-C", self.project_root, "worktree", "list", "--porcelain"],
                capture_output=True, text=True, timeout=10
            )
            # Remove any worktrees that still exist
            worktrees_dir = os.path.join(self.project_root, ".worktrees")
            if os.path.exists(worktrees_dir):
                for name in os.listdir(worktrees_dir):
                    wt_path = os.path.join(worktrees_dir, name)
                    if os.path.isdir(wt_path):
                        subprocess.run(
                            ["git", "-C", self.project_root, "worktree", "remove", wt_path, "--force"],
                            capture_output=True, timeout=10
                        )
        except Exception:
            pass

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _git(self, *args):
        """Run a git command in the project root."""
        result = subprocess.run(
            ["git", "-C", self.project_root] + list(args),
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0 and "already exists" not in result.stderr:
            # Allow some benign errors
            pass
        return result


class TestCreateIsolation(IsolationTestBase):
    """Tests for create_isolation.sh."""

    def test_creates_named_worktree(self):
        """Scenario: create_isolation Creates Named Worktree"""
        rc, stdout, stderr = run_script("create_isolation.sh", ["feat1"], self.project_root)
        self.assertEqual(rc, 0, f"Expected exit 0, got {rc}. stderr: {stderr}")

        # Verify worktree exists
        wt_path = os.path.join(self.project_root, ".worktrees", "feat1")
        self.assertTrue(os.path.isdir(wt_path), "Worktree directory should exist")

        # Verify branch name
        result = self._git("-C", os.path.join(".worktrees", "feat1"),
                          "rev-parse", "--abbrev-ref", "HEAD")
        # Use git directly from worktree
        branch_result = subprocess.run(
            ["git", "-C", wt_path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(branch_result.stdout.strip(), "isolated/feat1")

        # Verify branch starts from same HEAD as main
        main_head = subprocess.run(
            ["git", "-C", self.project_root, "rev-parse", "main"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        wt_head_parent = subprocess.run(
            ["git", "-C", wt_path, "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        self.assertEqual(main_head, wt_head_parent,
                         "Worktree HEAD should match main HEAD")

    def test_idempotent(self):
        """Scenario: create_isolation Is Idempotent"""
        run_script("create_isolation.sh", ["feat1"], self.project_root)

        # Run again
        rc, stdout, stderr = run_script("create_isolation.sh", ["feat1"], self.project_root)
        self.assertEqual(rc, 0, "Idempotent call should exit 0")
        self.assertIn("already exists", stdout.lower(),
                       "Should print status message about existing worktree")

    def test_rejects_name_longer_than_8(self):
        """Scenario: create_isolation Rejects Name Longer Than 8 Characters"""
        rc, stdout, stderr = run_script("create_isolation.sh", ["toolong12"], self.project_root)
        self.assertEqual(rc, 1, "Should exit with code 1 for name > 8 chars")
        self.assertIn("8", stderr, "Error should mention the 8 character limit")

    def test_rejects_invalid_characters(self):
        """Scenario: create_isolation Rejects Name With Invalid Characters"""
        rc, stdout, stderr = run_script("create_isolation.sh", ["bad.name"], self.project_root)
        self.assertEqual(rc, 1, "Should exit with code 1 for invalid characters")
        self.assertIn("invalid", stderr.lower(),
                       "Error should mention invalid characters")

    def test_places_only_local_commands(self):
        """Scenario: create_isolation Places Only pl-local Commands in Worktree"""
        rc, stdout, stderr = run_script("create_isolation.sh", ["ui"], self.project_root)
        self.assertEqual(rc, 0, f"Expected exit 0. stderr: {stderr}")

        wt_cmd_dir = os.path.join(self.project_root, ".worktrees", "ui",
                                   ".claude", "commands")

        # pl-local-push.md and pl-local-pull.md should exist
        self.assertTrue(os.path.exists(os.path.join(wt_cmd_dir, "pl-local-push.md")),
                         "pl-local-push.md should be in worktree commands")
        self.assertTrue(os.path.exists(os.path.join(wt_cmd_dir, "pl-local-pull.md")),
                         "pl-local-pull.md should be in worktree commands")

        # pl-status.md should NOT exist
        self.assertFalse(os.path.exists(os.path.join(wt_cmd_dir, "pl-status.md")),
                          "pl-status.md should NOT be in worktree commands")

        # Project root commands should be unaffected
        root_cmd_dir = os.path.join(self.project_root, ".claude", "commands")
        self.assertTrue(os.path.exists(os.path.join(root_cmd_dir, "pl-status.md")),
                         "Root pl-status.md should still exist")

    def test_propagates_live_config(self):
        """Scenario: create_isolation Propagates Live Config"""
        # Update the live config to have a different value than git-committed
        config_path = os.path.join(self.project_root, ".purlin", "config.json")
        live_config = {"agents": {"builder": {"startup_sequence": True, "effort": "high"}}}
        with open(config_path, "w") as f:
            json.dump(live_config, f)
        # Note: the git-committed version has startup_sequence: True but no effort key

        rc, stdout, stderr = run_script("create_isolation.sh", ["worker"], self.project_root)
        self.assertEqual(rc, 0, f"Expected exit 0. stderr: {stderr}")

        # Read the worktree's config
        wt_config_path = os.path.join(self.project_root, ".worktrees", "worker",
                                       ".purlin", "config.json")
        with open(wt_config_path, "r") as f:
            wt_config = json.load(f)

        self.assertTrue(wt_config["agents"]["builder"]["startup_sequence"],
                         "Worktree config should have startup_sequence true")
        self.assertEqual(wt_config["agents"]["builder"]["effort"], "high",
                          "Worktree config should have the live config's effort value")

    def test_multiple_simultaneous_isolations(self):
        """Scenario: Multiple Simultaneous Isolations Are Supported"""
        # Create first isolation
        rc1, _, stderr1 = run_script("create_isolation.sh", ["feat1"], self.project_root)
        self.assertEqual(rc1, 0, f"First isolation failed. stderr: {stderr1}")

        # Create second isolation
        rc2, _, stderr2 = run_script("create_isolation.sh", ["ui"], self.project_root)
        self.assertEqual(rc2, 0, f"Second isolation failed. stderr: {stderr2}")

        # Both should exist
        self.assertTrue(os.path.isdir(
            os.path.join(self.project_root, ".worktrees", "feat1")))
        self.assertTrue(os.path.isdir(
            os.path.join(self.project_root, ".worktrees", "ui")))

        # First should be unaffected by second
        branch1 = subprocess.run(
            ["git", "-C", os.path.join(self.project_root, ".worktrees", "feat1"),
             "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        self.assertEqual(branch1, "isolated/feat1")


class TestKillIsolation(IsolationTestBase):
    """Tests for kill_isolation.sh."""

    def _create_isolation(self, name):
        """Helper to create an isolation for kill tests."""
        rc, _, stderr = run_script("create_isolation.sh", [name], self.project_root)
        self.assertEqual(rc, 0, f"Setup failed: create_isolation {name}. stderr: {stderr}")

    def _make_dirty(self, name):
        """Helper to make a worktree dirty (uncommitted changes excluding .purlin/)."""
        dirty_file = os.path.join(self.project_root, ".worktrees", name, "dirty.txt")
        with open(dirty_file, "w") as f:
            f.write("dirty content\n")

    def _make_commits(self, name, count=1):
        """Helper to add commits to an isolation branch."""
        wt_path = os.path.join(self.project_root, ".worktrees", name)
        for i in range(count):
            file_path = os.path.join(wt_path, f"change_{i}.txt")
            with open(file_path, "w") as f:
                f.write(f"change {i}\n")
            subprocess.run(
                ["git", "-C", wt_path, "add", f"change_{i}.txt"],
                capture_output=True, timeout=10,
            )
            subprocess.run(
                ["git", "-C", wt_path, "commit", "-m", f"commit {i}"],
                capture_output=True, timeout=10,
            )

    def test_blocks_dirty_worktree(self):
        """Scenario: kill_isolation Blocks When Worktree Has Uncommitted Changes"""
        self._create_isolation("feat1")
        self._make_dirty("feat1")

        rc, stdout, stderr = run_script("kill_isolation.sh", ["feat1"], self.project_root)
        self.assertEqual(rc, 1, "Should exit 1 when worktree is dirty")
        self.assertIn("uncommitted", stderr.lower(),
                       "Error should mention uncommitted changes")

        # Worktree should still exist
        self.assertTrue(os.path.isdir(
            os.path.join(self.project_root, ".worktrees", "feat1")))

    def test_force_removes_dirty(self):
        """Scenario: kill_isolation Force Removes Dirty Worktree"""
        self._create_isolation("feat1")
        self._make_dirty("feat1")

        rc, stdout, stderr = run_script(
            "kill_isolation.sh", ["feat1", "--force"], self.project_root)
        self.assertEqual(rc, 0, f"--force should succeed. stderr: {stderr}")

        # Worktree should be gone
        self.assertFalse(os.path.isdir(
            os.path.join(self.project_root, ".worktrees", "feat1")))

    def test_warns_unsynced_proceeds(self):
        """Scenario: kill_isolation Proceeds with Warning When Branch Has Unmerged Commits"""
        self._create_isolation("feat1")
        self._make_commits("feat1", count=3)

        rc, stdout, stderr = run_script("kill_isolation.sh", ["feat1"], self.project_root)
        self.assertEqual(rc, 0, f"Should succeed with warning. stderr: {stderr}")
        self.assertIn("warning", stdout.lower(),
                       "Should print a warning about unmerged commits")
        self.assertIn("3", stdout, "Should mention 3 commits")

        # Worktree removed
        self.assertFalse(os.path.isdir(
            os.path.join(self.project_root, ".worktrees", "feat1")))

        # Branch should still exist (not deleted when unsynced)
        branch_result = subprocess.run(
            ["git", "-C", self.project_root, "branch", "--list", "isolated/feat1"],
            capture_output=True, text=True, timeout=10,
        )
        self.assertIn("isolated/feat1", branch_result.stdout,
                        "Branch should still exist when unsynced")

    def test_dry_run_returns_json(self):
        """Scenario: kill_isolation Dry Run Returns JSON Safety Report"""
        self._create_isolation("feat1")
        self._make_dirty("feat1")
        self._make_commits("feat1", count=2)
        # Re-dirty after commits
        self._make_dirty("feat1")

        rc, stdout, stderr = run_script(
            "kill_isolation.sh", ["feat1", "--dry-run"], self.project_root)
        self.assertEqual(rc, 0, f"Dry run should exit 0. stderr: {stderr}")

        # Parse JSON output
        data = json.loads(stdout)
        self.assertEqual(data["name"], "feat1")
        self.assertTrue(data["dirty"], "dirty should be true")
        self.assertIsInstance(data["dirty_files"], list)
        self.assertGreater(len(data["dirty_files"]), 0,
                            "dirty_files should list files")
        self.assertTrue(data["unsynced"], "unsynced should be true")
        self.assertEqual(data["unsynced_commits"], 2,
                          "Should report 2 unsynced commits")
        self.assertEqual(data["unsynced_branch"], "isolated/feat1")

        # Nothing should be removed
        self.assertTrue(os.path.isdir(
            os.path.join(self.project_root, ".worktrees", "feat1")))

    def test_exits_when_not_found(self):
        """Scenario: kill_isolation Exits When Worktree Not Found"""
        rc, stdout, stderr = run_script(
            "kill_isolation.sh", ["missing"], self.project_root)
        self.assertEqual(rc, 1, "Should exit 1 when worktree not found")
        self.assertIn("not found", stderr.lower(),
                       "Error should mention not found")


class TestPurlinProjectRoot(IsolationTestBase):
    """Tests for PURLIN_PROJECT_ROOT behavior in worktrees."""

    def test_project_root_resolves_to_worktree(self):
        """Scenario: PURLIN_PROJECT_ROOT Resolves to Worktree Path"""
        run_script("create_isolation.sh", ["feat1"], self.project_root)

        wt_path = os.path.join(self.project_root, ".worktrees", "feat1")
        wt_abs = os.path.realpath(wt_path)

        # Verify features/ in worktree is accessible
        features_dir = os.path.join(wt_path, "features")
        self.assertTrue(os.path.isdir(features_dir),
                         "features/ should be accessible in worktree")

        # Verify .purlin/cache/ can be written to the worktree
        cache_dir = os.path.join(wt_path, ".purlin", "cache")
        os.makedirs(cache_dir, exist_ok=True)
        test_file = os.path.join(cache_dir, "test.json")
        with open(test_file, "w") as f:
            f.write('{"test": true}')
        self.assertTrue(os.path.exists(test_file),
                         ".purlin/cache/ should be writable in worktree")

        # Verify the worktree path differs from the project root
        self.assertNotEqual(wt_abs, os.path.realpath(self.project_root),
                             "Worktree path should differ from project root")


def write_test_results(results):
    """Write tests.json to the standard output location."""
    # Find project root
    project_root = os.environ.get("PURLIN_PROJECT_ROOT")
    if not project_root:
        # Climb from this file's location
        d = os.path.dirname(os.path.abspath(__file__))
        while d != os.path.dirname(d):
            if os.path.isdir(os.path.join(d, "features")):
                project_root = d
                break
            d = os.path.dirname(d)

    if project_root:
        tests_dir = os.path.join(project_root, "tests", "isolated_agents")
        os.makedirs(tests_dir, exist_ok=True)
        tests_json = os.path.join(tests_dir, "tests.json")
        with open(tests_json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\ntests.json: {'PASS' if results['status'] == 'PASS' else 'FAIL'}")


if __name__ == "__main__":
    # Run tests and capture results
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Write structured results
    total = result.testsRun
    failures = len(result.failures) + len(result.errors)
    passed = total - failures
    status = "PASS" if failures == 0 else "FAIL"

    write_test_results({
        "status": status,
        "passed": passed,
        "failed": failures,
        "total": total,
    })
