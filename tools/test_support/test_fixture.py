#!/usr/bin/env python3
"""Tests for the fixture repo tool (tools/test_support/fixture.sh).

Covers all 8 automated scenarios from features/test_fixture_repo.md.
Outputs test results to tests/test_fixture_repo/tests.json.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_SH = os.path.join(SCRIPT_DIR, "fixture.sh")

# Resolve project root for test output
PROJECT_ROOT = os.environ.get("PURLIN_PROJECT_ROOT")
if not PROJECT_ROOT:
    d = SCRIPT_DIR
    while d != "/":
        if os.path.isdir(os.path.join(d, "features")):
            PROJECT_ROOT = d
        d = os.path.dirname(d)


def run_fixture(*args, env_override=None):
    """Run fixture.sh with given arguments and return (returncode, stdout, stderr)."""
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    result = subprocess.run(
        ["bash", FIXTURE_SH] + list(args),
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def create_fixture_repo(tags_and_files):
    """Create a temporary bare git repo with tagged commits.

    Args:
        tags_and_files: dict mapping tag_name -> dict of {filename: content}

    Returns:
        Path to the bare repo (suitable as repo-url).
    """
    work_dir = tempfile.mkdtemp(prefix="fixture-work-")
    bare_dir = tempfile.mkdtemp(prefix="fixture-bare-")

    # Initialize bare repo
    subprocess.run(
        ["git", "init", "--bare", bare_dir],
        capture_output=True, check=True,
    )

    # Initialize working repo
    subprocess.run(
        ["git", "init", work_dir],
        capture_output=True, check=True, cwd=work_dir,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", bare_dir],
        capture_output=True, check=True, cwd=work_dir,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        capture_output=True, check=True, cwd=work_dir,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        capture_output=True, check=True, cwd=work_dir,
    )

    # Create an initial commit
    dummy = os.path.join(work_dir, ".gitkeep")
    with open(dummy, "w") as f:
        f.write("")
    subprocess.run(
        ["git", "add", "."],
        capture_output=True, check=True, cwd=work_dir,
    )
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        capture_output=True, check=True, cwd=work_dir,
    )

    # Create tagged commits
    for tag_name, files in tags_and_files.items():
        for fname, content in files.items():
            fpath = os.path.join(work_dir, fname)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w") as f:
                f.write(content)
        subprocess.run(
            ["git", "add", "."],
            capture_output=True, check=True, cwd=work_dir,
        )
        subprocess.run(
            ["git", "commit", "-m", f"State for {tag_name}"],
            capture_output=True, check=True, cwd=work_dir,
        )
        subprocess.run(
            ["git", "tag", tag_name],
            capture_output=True, check=True, cwd=work_dir,
        )

    # Push all to bare repo
    subprocess.run(
        ["git", "push", "origin", "--all"],
        capture_output=True, check=True, cwd=work_dir,
    )
    subprocess.run(
        ["git", "push", "origin", "--tags"],
        capture_output=True, check=True, cwd=work_dir,
    )

    # Clean up work dir
    subprocess.run(["rm", "-rf", work_dir], capture_output=True)

    return bare_dir


class TestCheckout(unittest.TestCase):
    """Scenario: Checkout creates temp directory with fixture state"""

    @classmethod
    def setUpClass(cls):
        cls.repo = create_fixture_repo({
            "main/test_feature/scenario-one": {
                "features/test_feature.md": "# Test Feature\n",
                ".purlin/config.json": '{"tools_root": "tools"}\n',
            },
        })

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["rm", "-rf", cls.repo], capture_output=True)

    def test_checkout_creates_temp_dir(self):
        rc, stdout, stderr = run_fixture(
            "checkout", self.repo, "main/test_feature/scenario-one",
        )
        self.assertEqual(rc, 0, f"checkout failed: {stderr}")
        checkout_path = stdout
        self.assertTrue(os.path.isdir(checkout_path), "Checkout path should be a directory")
        self.assertTrue(
            os.path.isfile(os.path.join(checkout_path, "features/test_feature.md")),
            "Checkout should contain fixture files",
        )
        # Cleanup
        subprocess.run(["rm", "-rf", checkout_path], capture_output=True)

    def test_checkout_prints_path_to_stdout(self):
        rc, stdout, _ = run_fixture(
            "checkout", self.repo, "main/test_feature/scenario-one",
        )
        self.assertEqual(rc, 0)
        self.assertTrue(stdout.startswith("/"), "Should print absolute path to stdout")
        subprocess.run(["rm", "-rf", stdout], capture_output=True)


class TestCheckoutExplicitDir(unittest.TestCase):
    """Scenario: Checkout with explicit directory"""

    @classmethod
    def setUpClass(cls):
        cls.repo = create_fixture_repo({
            "main/test_feature/scenario-one": {
                "features/test_feature.md": "# Test Feature\n",
            },
        })

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["rm", "-rf", cls.repo], capture_output=True)

    def test_checkout_to_explicit_dir(self):
        target = tempfile.mkdtemp(prefix="fixture-explicit-")
        subprocess.run(["rm", "-rf", target], capture_output=True)

        rc, stdout, stderr = run_fixture(
            "checkout", self.repo, "main/test_feature/scenario-one",
            "--dir", target,
        )
        self.assertEqual(rc, 0, f"checkout failed: {stderr}")
        self.assertEqual(stdout, target)
        self.assertTrue(
            os.path.isfile(os.path.join(target, "features/test_feature.md")),
            "Explicit dir should contain fixture files",
        )
        subprocess.run(["rm", "-rf", target], capture_output=True)


class TestCleanup(unittest.TestCase):
    """Scenario: Cleanup removes fixture directory"""

    def test_cleanup_removes_dir(self):
        target = tempfile.mkdtemp(prefix="fixture-cleanup-")
        dummy = os.path.join(target, "somefile.txt")
        with open(dummy, "w") as f:
            f.write("data")

        rc, _, stderr = run_fixture("cleanup", target)
        self.assertEqual(rc, 0, f"cleanup failed: {stderr}")
        self.assertFalse(os.path.exists(target), "Directory should be removed")


class TestCleanupRefusesNonTemp(unittest.TestCase):
    """Scenario: Cleanup refuses non-temp paths"""

    def test_refuses_non_temp_path(self):
        rc, _, stderr = run_fixture("cleanup", "/Users/someone/important-project")
        self.assertNotEqual(rc, 0, "Should fail for non-temp paths")
        self.assertIn("Refusing to delete", stderr)


class TestListAll(unittest.TestCase):
    """Scenario: List shows all fixture tags"""

    @classmethod
    def setUpClass(cls):
        cls.repo = create_fixture_repo({
            "main/feat_a/s1": {"a.txt": "a"},
            "main/feat_a/s2": {"b.txt": "b"},
            "main/feat_b/s1": {"c.txt": "c"},
        })

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["rm", "-rf", cls.repo], capture_output=True)

    def test_list_all_tags(self):
        rc, stdout, stderr = run_fixture("list", self.repo)
        self.assertEqual(rc, 0, f"list failed: {stderr}")
        lines = [l for l in stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 3, f"Expected 3 tags, got: {lines}")
        self.assertIn("main/feat_a/s1", lines)
        self.assertIn("main/feat_a/s2", lines)
        self.assertIn("main/feat_b/s1", lines)

    def test_list_sorted_alphabetically(self):
        rc, stdout, _ = run_fixture("list", self.repo)
        lines = [l for l in stdout.splitlines() if l.strip()]
        self.assertEqual(lines, sorted(lines))


class TestListFilter(unittest.TestCase):
    """Scenario: List filters by project ref"""

    @classmethod
    def setUpClass(cls):
        cls.repo = create_fixture_repo({
            "main/feat_a/s1": {"a.txt": "a"},
            "v2/feat_a/s1": {"b.txt": "b"},
        })

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["rm", "-rf", cls.repo], capture_output=True)

    def test_filter_by_ref(self):
        rc, stdout, stderr = run_fixture("list", self.repo, "--ref", "main")
        self.assertEqual(rc, 0, f"list failed: {stderr}")
        lines = [l for l in stdout.splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        self.assertIn("main/feat_a/s1", lines)
        self.assertNotIn("v2/feat_a/s1", stdout)


class TestPruneOrphans(unittest.TestCase):
    """Scenario: Prune identifies orphan tags"""

    @classmethod
    def setUpClass(cls):
        cls.repo = create_fixture_repo({
            "main/feat_a/s1": {"a.txt": "a"},
            "main/feat_retired/s1": {"b.txt": "b"},
        })
        # Create a temp project root with features/feat_a.md but no feat_retired.md
        cls.fake_root = tempfile.mkdtemp(prefix="fixture-prune-root-")
        os.makedirs(os.path.join(cls.fake_root, "features"))
        with open(os.path.join(cls.fake_root, "features/feat_a.md"), "w") as f:
            f.write("# Feature A\n")

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["rm", "-rf", cls.repo], capture_output=True)
        subprocess.run(["rm", "-rf", cls.fake_root], capture_output=True)

    def test_prune_identifies_orphan(self):
        rc, stdout, stderr = run_fixture(
            "prune", self.repo,
            env_override={"PURLIN_PROJECT_ROOT": self.fake_root},
        )
        self.assertEqual(rc, 0, f"prune failed: {stderr}")
        self.assertIn("main/feat_retired/s1", stdout)
        self.assertNotIn("main/feat_a/s1", stdout)


class TestPruneTombstone(unittest.TestCase):
    """Scenario: Prune detects tombstoned features"""

    @classmethod
    def setUpClass(cls):
        cls.repo = create_fixture_repo({
            "main/old_feature/s1": {"a.txt": "a"},
        })
        cls.fake_root = tempfile.mkdtemp(prefix="fixture-prune-tomb-")
        os.makedirs(os.path.join(cls.fake_root, "features/tombstones"))
        # Feature file exists but tombstone also exists
        with open(os.path.join(cls.fake_root, "features/old_feature.md"), "w") as f:
            f.write("# Old Feature\n")
        with open(os.path.join(cls.fake_root, "features/tombstones/old_feature.md"), "w") as f:
            f.write("# Tombstone\n")

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["rm", "-rf", cls.repo], capture_output=True)
        subprocess.run(["rm", "-rf", cls.fake_root], capture_output=True)

    def test_prune_detects_tombstoned(self):
        rc, stdout, stderr = run_fixture(
            "prune", self.repo,
            env_override={"PURLIN_PROJECT_ROOT": self.fake_root},
        )
        self.assertEqual(rc, 0, f"prune failed: {stderr}")
        self.assertIn("main/old_feature/s1", stdout)


# ===================================================================
# Test result output
# ===================================================================

class JsonTestResult(unittest.TextTestResult):
    """Custom result that collects pass/fail for JSON output."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.results = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.results.append({"test": str(test), "status": "PASS"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.results.append({"test": str(test), "status": "FAIL", "message": str(err[1])})

    def addError(self, test, err):
        super().addError(test, err)
        self.results.append({"test": str(test), "status": "ERROR", "message": str(err[1])})


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(resultclass=JsonTestResult, verbosity=2)
    result = runner.run(suite)

    # Write tests.json
    if PROJECT_ROOT:
        out_dir = os.path.join(PROJECT_ROOT, "tests", "test_fixture_repo")
        os.makedirs(out_dir, exist_ok=True)
        out_file = os.path.join(out_dir, "tests.json")

        all_passed = len(result.failures) == 0 and len(result.errors) == 0
        with open(out_file, "w") as f:
            json.dump(
                {
                    "status": "PASS" if all_passed else "FAIL",
                    "tests_run": result.testsRun,
                    "failures": len(result.failures),
                    "errors": len(result.errors),
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
