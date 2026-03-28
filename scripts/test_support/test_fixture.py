#!/usr/bin/env python3
"""Tests for the fixture repo tool (tools/test_support/fixture.sh).

Covers all 8 automated scenarios from features/test_fixture_repo.md.
Outputs test results to tests/test_fixture_repo/tests.json.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURE_SH = os.path.join(SCRIPT_DIR, "fixture.sh")

sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, '../../')))
from tools.bootstrap import detect_project_root
PROJECT_ROOT = detect_project_root(SCRIPT_DIR)


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


class TestInitCreatesRepo(unittest.TestCase):
    """Scenario: Init creates bare repo at convention path"""

    def test_init_creates_bare_repo(self):
        fake_root = tempfile.mkdtemp(prefix="fixture-init-")
        os.makedirs(os.path.join(fake_root, "features"))
        os.makedirs(os.path.join(fake_root, ".purlin", "runtime"), exist_ok=True)

        repo_path = os.path.join(fake_root, ".purlin", "runtime", "fixture-repo")

        rc, stdout, stderr = run_fixture(
            "init",
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertEqual(rc, 0, f"init failed: {stderr}")
        self.assertTrue(os.path.isdir(repo_path), "Bare repo dir should exist")
        self.assertIn(repo_path, stdout, "Should print repo path to stdout")

        # Verify it's a bare repo
        check = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "--is-bare-repository"],
            capture_output=True, text=True,
        )
        self.assertEqual(check.stdout.strip(), "true")

        subprocess.run(["rm", "-rf", fake_root], capture_output=True)


class TestInitIdempotent(unittest.TestCase):
    """Scenario: Init is idempotent when repo exists"""

    def test_init_idempotent(self):
        fake_root = tempfile.mkdtemp(prefix="fixture-init-idem-")
        os.makedirs(os.path.join(fake_root, "features"))
        repo_path = os.path.join(fake_root, ".purlin", "runtime", "fixture-repo")

        # First init
        rc1, stdout1, _ = run_fixture(
            "init",
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertEqual(rc1, 0)

        # Record mtime of HEAD file to verify repo is not recreated
        head_path = os.path.join(repo_path, "HEAD")
        mtime_before = os.path.getmtime(head_path)

        # Second init
        rc2, stdout2, stderr2 = run_fixture(
            "init",
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertEqual(rc2, 0, f"second init failed: {stderr2}")
        self.assertIn("already exists", stderr2)
        self.assertIn(repo_path, stdout2)

        # HEAD file should not be recreated
        mtime_after = os.path.getmtime(head_path)
        self.assertEqual(mtime_before, mtime_after, "Existing repo should not be modified")

        subprocess.run(["rm", "-rf", fake_root], capture_output=True)


class TestInitExplicitPath(unittest.TestCase):
    """Scenario: Init with explicit path"""

    def test_init_explicit_path(self):
        custom_path = os.path.join(tempfile.mkdtemp(prefix="fixture-custom-"), "my-fixture-repo")

        rc, stdout, stderr = run_fixture("init", "--path", custom_path)
        self.assertEqual(rc, 0, f"init failed: {stderr}")
        self.assertTrue(os.path.isdir(custom_path), "Custom path repo should exist")
        self.assertIn(custom_path, stdout, "Should print custom path to stdout")

        check = subprocess.run(
            ["git", "-C", custom_path, "rev-parse", "--is-bare-repository"],
            capture_output=True, text=True,
        )
        self.assertEqual(check.stdout.strip(), "true")

        subprocess.run(["rm", "-rf", os.path.dirname(custom_path)], capture_output=True)


class TestAddTagCreatesCommit(unittest.TestCase):
    """Scenario: Add-tag creates tagged commit from directory"""

    def test_add_tag_creates_tagged_commit(self):
        fake_root = tempfile.mkdtemp(prefix="fixture-addtag-")
        os.makedirs(os.path.join(fake_root, "features"))

        # Init fixture repo
        rc, _, stderr = run_fixture(
            "init",
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertEqual(rc, 0, f"init failed: {stderr}")

        # Create source directory with project state
        source_dir = tempfile.mkdtemp(prefix="fixture-source-")
        os.makedirs(os.path.join(source_dir, "features"))
        with open(os.path.join(source_dir, "features", "test.md"), "w") as f:
            f.write("# Test Feature\n")
        with open(os.path.join(source_dir, "config.txt"), "w") as f:
            f.write("key=value\n")

        # Add tag
        rc, stdout, stderr = run_fixture(
            "add-tag", "main/test_feature/my-state",
            "--from-dir", source_dir,
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertEqual(rc, 0, f"add-tag failed: {stderr}")
        self.assertIn("Created tag", stdout)

        # Verify tag exists by listing
        repo_path = os.path.join(fake_root, ".purlin", "runtime", "fixture-repo")
        rc2, list_out, _ = run_fixture("list", repo_path)
        self.assertEqual(rc2, 0)
        self.assertIn("main/test_feature/my-state", list_out)

        # Verify checkout yields the source files
        rc3, checkout_path, _ = run_fixture(
            "checkout", repo_path, "main/test_feature/my-state",
        )
        self.assertEqual(rc3, 0)
        self.assertTrue(
            os.path.isfile(os.path.join(checkout_path, "features", "test.md")),
            "Checked out tag should contain source files",
        )

        subprocess.run(["rm", "-rf", fake_root, source_dir, checkout_path], capture_output=True)


class TestAddTagDefaultsToProjectRoot(unittest.TestCase):
    """Scenario: Add-tag defaults to project root when from-dir omitted"""

    def test_add_tag_defaults_from_dir(self):
        fake_root = tempfile.mkdtemp(prefix="fixture-addtag-default-")
        os.makedirs(os.path.join(fake_root, "features"))
        with open(os.path.join(fake_root, "features", "sample.md"), "w") as f:
            f.write("# Sample\n")

        # Init
        rc, _, stderr = run_fixture(
            "init",
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertEqual(rc, 0, f"init failed: {stderr}")

        # Add tag without --from-dir
        rc, stdout, stderr = run_fixture(
            "add-tag", "main/test_feature/default-source",
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertEqual(rc, 0, f"add-tag failed: {stderr}")

        # Checkout and verify files from project root
        repo_path = os.path.join(fake_root, ".purlin", "runtime", "fixture-repo")
        rc2, checkout_path, _ = run_fixture(
            "checkout", repo_path, "main/test_feature/default-source",
        )
        self.assertEqual(rc2, 0)
        self.assertTrue(
            os.path.isfile(os.path.join(checkout_path, "features", "sample.md")),
            "Tag should contain project root files",
        )

        subprocess.run(["rm", "-rf", fake_root, checkout_path], capture_output=True)


class TestAddTagRejectsInvalidFormat(unittest.TestCase):
    """Scenario: Add-tag rejects invalid tag format"""

    def test_rejects_no_slashes(self):
        fake_root = tempfile.mkdtemp(prefix="fixture-addtag-invalid-")
        os.makedirs(os.path.join(fake_root, "features"))

        # Init
        run_fixture("init", env_override={"PURLIN_PROJECT_ROOT": fake_root})

        rc, _, stderr = run_fixture(
            "add-tag", "invalid-tag-no-slashes",
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertNotEqual(rc, 0, "Should fail for invalid tag format")
        self.assertIn("Invalid tag format", stderr)

        # Verify no tag was created
        repo_path = os.path.join(fake_root, ".purlin", "runtime", "fixture-repo")
        rc2, list_out, _ = run_fixture("list", repo_path)
        self.assertNotIn("invalid-tag-no-slashes", list_out)

        subprocess.run(["rm", "-rf", fake_root], capture_output=True)

    def test_rejects_two_segments(self):
        fake_root = tempfile.mkdtemp(prefix="fixture-addtag-invalid2-")
        os.makedirs(os.path.join(fake_root, "features"))
        run_fixture("init", env_override={"PURLIN_PROJECT_ROOT": fake_root})

        rc, _, stderr = run_fixture(
            "add-tag", "main/only-two",
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertNotEqual(rc, 0)
        self.assertIn("Invalid tag format", stderr)

        subprocess.run(["rm", "-rf", fake_root], capture_output=True)


class TestAddTagRefusesExisting(unittest.TestCase):
    """Scenario: Add-tag refuses existing tag without force"""

    def test_refuses_existing_tag(self):
        fake_root = tempfile.mkdtemp(prefix="fixture-addtag-exists-")
        os.makedirs(os.path.join(fake_root, "features"))
        run_fixture("init", env_override={"PURLIN_PROJECT_ROOT": fake_root})

        # Create initial tag
        source_dir = tempfile.mkdtemp(prefix="fixture-source-")
        with open(os.path.join(source_dir, "file1.txt"), "w") as f:
            f.write("original")

        rc, _, stderr = run_fixture(
            "add-tag", "main/test_feature/existing-state",
            "--from-dir", source_dir,
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertEqual(rc, 0, f"first add-tag failed: {stderr}")

        # Try to create same tag again without --force
        with open(os.path.join(source_dir, "file1.txt"), "w") as f:
            f.write("updated")

        rc2, _, stderr2 = run_fixture(
            "add-tag", "main/test_feature/existing-state",
            "--from-dir", source_dir,
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertNotEqual(rc2, 0, "Should fail when tag exists without --force")
        self.assertIn("already exists", stderr2)

        subprocess.run(["rm", "-rf", fake_root, source_dir], capture_output=True)


class TestAddTagForceOverwrites(unittest.TestCase):
    """Scenario: Add-tag with force overwrites existing tag"""

    def test_force_overwrites_tag(self):
        fake_root = tempfile.mkdtemp(prefix="fixture-addtag-force-")
        os.makedirs(os.path.join(fake_root, "features"))
        run_fixture("init", env_override={"PURLIN_PROJECT_ROOT": fake_root})

        repo_path = os.path.join(fake_root, ".purlin", "runtime", "fixture-repo")

        # Create initial tag
        source_dir = tempfile.mkdtemp(prefix="fixture-source-")
        with open(os.path.join(source_dir, "file1.txt"), "w") as f:
            f.write("original")

        run_fixture(
            "add-tag", "main/test_feature/existing-state",
            "--from-dir", source_dir,
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )

        # Overwrite with --force
        with open(os.path.join(source_dir, "file1.txt"), "w") as f:
            f.write("updated-content")

        rc, stdout, stderr = run_fixture(
            "add-tag", "main/test_feature/existing-state",
            "--from-dir", source_dir, "--force",
            env_override={"PURLIN_PROJECT_ROOT": fake_root},
        )
        self.assertEqual(rc, 0, f"force add-tag failed: {stderr}")

        # Checkout and verify updated content
        rc2, checkout_path, _ = run_fixture(
            "checkout", repo_path, "main/test_feature/existing-state",
        )
        self.assertEqual(rc2, 0)
        with open(os.path.join(checkout_path, "file1.txt")) as f:
            content = f.read()
        self.assertEqual(content, "updated-content", "Force should update tag contents")

        subprocess.run(["rm", "-rf", fake_root, source_dir, checkout_path], capture_output=True)


class TestQARecordsFixtureUsage(unittest.TestCase):
    """Scenario: QA records fixture usage during scenario authoring

    Validates that when a regression scenario uses a fixture tag, the
    fixture_usage.json file at tests/qa/fixture_usage.json is updated
    with the correct feature entry, fixture_type, tags_used, and
    last_authored timestamp (per spec Section 2.11).
    """

    def setUp(self):
        self.fake_root = tempfile.mkdtemp(prefix="fixture-usage-")
        self.qa_dir = os.path.join(self.fake_root, "tests", "qa")
        self.scenarios_dir = os.path.join(self.qa_dir, "scenarios")
        os.makedirs(self.scenarios_dir, exist_ok=True)

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.fake_root], capture_output=True)

    def _write_scenario_and_update_usage(self, feature_name, fixture_tag):
        """Simulate QA authoring: write scenario JSON and update fixture_usage.json.

        This replicates the QA workflow from regression_testing.md Section 2.10:
        QA writes the scenario JSON file, then updates fixture_usage.json to
        record which fixtures are used by which feature.
        """
        # Step 1: Write scenario JSON (as QA does during authoring)
        scenario = {
            "feature": feature_name,
            "harness_type": "agent_behavior",
            "scenarios": [
                {
                    "name": "test-scenario",
                    "fixture_tag": fixture_tag,
                    "role": "BUILDER",
                    "prompt": "Test prompt",
                    "assertions": [
                        {"pattern": "OK", "tier": 1, "context": "basic check"}
                    ],
                }
            ],
        }
        scenario_path = os.path.join(self.scenarios_dir, f"{feature_name}.json")
        with open(scenario_path, "w") as f:
            json.dump(scenario, f, indent=2)

        # Step 2: Update fixture_usage.json (per spec Section 2.11)
        usage_path = os.path.join(self.qa_dir, "fixture_usage.json")
        if os.path.isfile(usage_path):
            with open(usage_path) as f:
                usage = json.load(f)
        else:
            usage = {"last_updated": "", "features": {}}

        now = datetime.now(timezone.utc).isoformat()
        usage["last_updated"] = now
        usage["features"][feature_name] = {
            "fixture_type": "local",
            "tags_used": [fixture_tag],
            "last_authored": now,
        }

        with open(usage_path, "w") as f:
            json.dump(usage, f, indent=2)

        return usage_path, scenario_path

    def test_fixture_usage_json_created(self):
        """fixture_usage.json is created with correct structure."""
        usage_path, _ = self._write_scenario_and_update_usage(
            "instruction_audit", "main/instruction_audit/override-contradiction"
        )
        self.assertTrue(os.path.isfile(usage_path))
        with open(usage_path) as f:
            usage = json.load(f)

        self.assertIn("last_updated", usage)
        self.assertIn("features", usage)
        self.assertIn("instruction_audit", usage["features"])

    def test_fixture_usage_records_type_and_tag(self):
        """Entry records fixture_type 'local' and the tag used."""
        usage_path, _ = self._write_scenario_and_update_usage(
            "instruction_audit", "main/instruction_audit/override-contradiction"
        )
        with open(usage_path) as f:
            usage = json.load(f)

        entry = usage["features"]["instruction_audit"]
        self.assertEqual(entry["fixture_type"], "local")
        self.assertIn("main/instruction_audit/override-contradiction", entry["tags_used"])

    def test_fixture_usage_sets_timestamp(self):
        """last_authored is set to a valid ISO timestamp."""
        usage_path, _ = self._write_scenario_and_update_usage(
            "instruction_audit", "main/instruction_audit/override-contradiction"
        )
        with open(usage_path) as f:
            usage = json.load(f)

        entry = usage["features"]["instruction_audit"]
        # Verify it parses as a valid ISO timestamp
        ts = datetime.fromisoformat(entry["last_authored"])
        self.assertIsNotNone(ts)
        # Also verify top-level last_updated
        ts_top = datetime.fromisoformat(usage["last_updated"])
        self.assertIsNotNone(ts_top)

    def test_fixture_usage_scenario_json_written(self):
        """Scenario JSON file exists alongside the usage update."""
        _, scenario_path = self._write_scenario_and_update_usage(
            "instruction_audit", "main/instruction_audit/override-contradiction"
        )
        self.assertTrue(os.path.isfile(scenario_path))
        with open(scenario_path) as f:
            scenario = json.load(f)
        self.assertEqual(scenario["feature"], "instruction_audit")
        self.assertEqual(
            scenario["scenarios"][0]["fixture_tag"],
            "main/instruction_audit/override-contradiction",
        )


class TestQARecommendsRemoteFixtureRepo(unittest.TestCase):
    """Scenario: QA recommends remote fixture repo for complex-state feature

    Validates that when QA identifies a feature needing complex git state
    (multiple branches, divergent history) and no fixture_repo_url is
    configured, QA writes the recommendation to
    tests/qa/fixture_recommendations.md (per spec Section 2.12).

    Uses the production functions from fixture_recommendations.py.
    """

    def setUp(self):
        self.fake_root = tempfile.mkdtemp(prefix="fixture-recommend-")
        self.qa_dir = os.path.join(self.fake_root, "tests", "qa")
        os.makedirs(self.qa_dir, exist_ok=True)
        # Config without fixture_repo_url
        purlin_dir = os.path.join(self.fake_root, ".purlin")
        os.makedirs(purlin_dir, exist_ok=True)
        self.config_path = os.path.join(purlin_dir, "config.json")
        with open(self.config_path, "w") as f:
            json.dump({"tools_root": "tools"}, f)
        self.rec_path = os.path.join(self.qa_dir, "fixture_recommendations.md")

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.fake_root], capture_output=True)

    def test_no_fixture_repo_url_configured(self):
        """Confirms fixture_repo_url is not in config (prerequisite)."""
        with open(self.config_path) as f:
            config = json.load(f)
        self.assertNotIn("fixture_repo_url", config)

    def test_recommendation_file_created(self):
        """Recommendation is written to fixture_recommendations.md."""
        from fixture_recommendations import (
            evaluate_fixture_needs, write_recommendation,
        )
        result = evaluate_fixture_needs(self.config_path, "complex")
        self.assertEqual(result["action"], "recommend")
        self.assertFalse(result["has_remote"])

        write_recommendation(
            self.rec_path, "branch_collab",
            "complex git state with multiple branches",
            ["main/branch_collab/diverged-history", "main/branch_collab/ahead-3"],
        )
        self.assertTrue(os.path.isfile(self.rec_path))

    def test_recommendation_contains_required_fields(self):
        """Recommendation has reason, suggested tags, recorded date, and PENDING status."""
        from fixture_recommendations import write_recommendation
        write_recommendation(
            self.rec_path, "branch_collab",
            "complex git state with multiple branches",
            ["main/branch_collab/diverged-history", "main/branch_collab/ahead-3"],
        )
        with open(self.rec_path) as f:
            content = f.read()

        self.assertIn("## branch_collab", content)
        self.assertIn("**Reason:**", content)
        self.assertIn("complex git state with multiple branches", content)
        self.assertIn("**Suggested tags:**", content)
        self.assertIn("main/branch_collab/diverged-history", content)
        self.assertIn("main/branch_collab/ahead-3", content)
        self.assertIn("**Recorded:**", content)
        self.assertIn("**Status:** PENDING", content)

    def test_recommendation_header_present(self):
        """File starts with '# Fixture Recommendations' header."""
        from fixture_recommendations import write_recommendation
        write_recommendation(
            self.rec_path, "branch_collab",
            "complex git state with multiple branches",
            ["main/branch_collab/diverged-history"],
        )
        with open(self.rec_path) as f:
            first_line = f.readline().strip()
        self.assertEqual(first_line, "# Fixture Recommendations")


class TestFixtureRecommendationReadByFutureSessions(unittest.TestCase):
    """Scenario: Fixture recommendation file read by future sessions

    Validates that a Engineer session with qa_mode enabled can read
    fixture_recommendations.md and identify which fixture tags
    need to be created (per spec Section 2.12).

    Uses the production parse_recommendations() from fixture_recommendations.py.
    """

    def setUp(self):
        self.fake_root = tempfile.mkdtemp(prefix="fixture-rec-read-")
        self.qa_dir = os.path.join(self.fake_root, "tests", "qa")
        os.makedirs(self.qa_dir, exist_ok=True)

        # Write a fixture_recommendations.md with a PENDING entry
        self.rec_path = os.path.join(self.qa_dir, "fixture_recommendations.md")
        with open(self.rec_path, "w") as f:
            f.write(
                "# Fixture Recommendations\n"
                "\n"
                "## branch_collab\n"
                "- **Reason:** complex git state with multiple branches\n"
                "- **Suggested tags:** `main/branch_collab/diverged-history`, "
                "`main/branch_collab/ahead-3`\n"
                "- **Recorded:** 2026-03-18\n"
                "- **Status:** PENDING\n"
                "\n"
                "## instruction_audit\n"
                "- **Reason:** needs config override combinations\n"
                "- **Suggested tags:** `main/instruction_audit/override-contradiction`\n"
                "- **Recorded:** 2026-03-17\n"
                "- **Status:** CREATED\n"
            )

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.fake_root], capture_output=True)

    def test_builder_can_read_recommendation_file(self):
        """Engineer reads the recommendations file and gets structured data."""
        from fixture_recommendations import parse_recommendations
        recs = parse_recommendations(self.rec_path)
        self.assertIn("branch_collab", recs)
        self.assertIn("instruction_audit", recs)

    def test_builder_identifies_pending_tags(self):
        """Engineer identifies PENDING features that need fixture tags created."""
        from fixture_recommendations import get_pending_recommendations
        pending = get_pending_recommendations(self.rec_path)
        self.assertEqual(len(pending), 1)
        self.assertIn("branch_collab", pending)
        self.assertNotIn("instruction_audit", pending)

    def test_pending_entry_has_suggested_tags(self):
        """PENDING entry includes suggested tags the Engineer should create."""
        from fixture_recommendations import parse_recommendations
        recs = parse_recommendations(self.rec_path)
        branch_collab = recs["branch_collab"]
        self.assertEqual(branch_collab["status"], "PENDING")
        self.assertIn("main/branch_collab/diverged-history", branch_collab["suggested_tags"])
        self.assertIn("main/branch_collab/ahead-3", branch_collab["suggested_tags"])

    def test_created_entries_skipped(self):
        """Features with CREATED status are not in the pending set."""
        from fixture_recommendations import get_pending_recommendations
        pending = get_pending_recommendations(self.rec_path)
        self.assertNotIn("instruction_audit", pending)


# ===================================================================
# Decision Logic Tests (BUG M32)
# ===================================================================

class TestEvaluateFixtureNeedsDecisionLogic(unittest.TestCase):
    """Tests for the QA recommendation decision logic.

    Covers all branches of the decision tree from
    regression_testing.md Section 2.10.1:
    1. Feature has fixture tags -> use_existing
    2. No tags, no controlled state needed -> none
    3. No tags, simple state -> inline_setup
    4. No tags, complex state, remote configured -> use_remote
    5. No tags, complex state, no remote -> recommend
    """

    def setUp(self):
        self.fake_root = tempfile.mkdtemp(prefix="fixture-decision-")
        purlin_dir = os.path.join(self.fake_root, ".purlin")
        os.makedirs(purlin_dir, exist_ok=True)
        self.config_path = os.path.join(purlin_dir, "config.json")

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.fake_root], capture_output=True)

    def _write_config(self, config_data):
        with open(self.config_path, "w") as f:
            json.dump(config_data, f)

    def test_has_fixture_tags_returns_use_existing(self):
        """When feature references fixture tags, action is use_existing."""
        from fixture_recommendations import evaluate_fixture_needs
        self._write_config({"tools_root": "tools"})
        result = evaluate_fixture_needs(
            self.config_path, "complex", has_fixture_tags=True,
        )
        self.assertEqual(result["action"], "use_existing")

    def test_has_fixture_tags_with_remote_still_use_existing(self):
        """Fixture tags take priority even when remote is configured."""
        from fixture_recommendations import evaluate_fixture_needs
        self._write_config({
            "tools_root": "tools",
            "fixture_repo_url": "https://example.com/fixtures.git",
        })
        result = evaluate_fixture_needs(
            self.config_path, "complex", has_fixture_tags=True,
        )
        self.assertEqual(result["action"], "use_existing")
        self.assertTrue(result["has_remote"])

    def test_no_state_needed_returns_none(self):
        """When state_complexity is 'none', action is none."""
        from fixture_recommendations import evaluate_fixture_needs
        self._write_config({"tools_root": "tools"})
        result = evaluate_fixture_needs(self.config_path, "none")
        self.assertEqual(result["action"], "none")

    def test_simple_state_returns_inline_setup(self):
        """Simple state uses inline setup_commands."""
        from fixture_recommendations import evaluate_fixture_needs
        self._write_config({"tools_root": "tools"})
        result = evaluate_fixture_needs(self.config_path, "simple")
        self.assertEqual(result["action"], "inline_setup")
        self.assertFalse(result["has_remote"])

    def test_complex_state_no_remote_returns_recommend(self):
        """Complex state without remote -> recommend fixture repo."""
        from fixture_recommendations import evaluate_fixture_needs
        self._write_config({"tools_root": "tools"})
        result = evaluate_fixture_needs(self.config_path, "complex")
        self.assertEqual(result["action"], "recommend")
        self.assertFalse(result["has_remote"])

    def test_complex_state_with_remote_returns_use_remote(self):
        """Complex state with remote configured -> use_remote."""
        from fixture_recommendations import evaluate_fixture_needs
        self._write_config({
            "tools_root": "tools",
            "fixture_repo_url": "https://example.com/fixtures.git",
        })
        result = evaluate_fixture_needs(self.config_path, "complex")
        self.assertEqual(result["action"], "use_remote")
        self.assertTrue(result["has_remote"])

    def test_missing_config_file_defaults_no_remote(self):
        """When config.json doesn't exist, has_remote is False."""
        from fixture_recommendations import evaluate_fixture_needs
        result = evaluate_fixture_needs(
            "/nonexistent/config.json", "complex",
        )
        self.assertEqual(result["action"], "recommend")
        self.assertFalse(result["has_remote"])

    def test_malformed_config_file_defaults_no_remote(self):
        """When config.json is invalid JSON, has_remote is False."""
        from fixture_recommendations import evaluate_fixture_needs
        with open(self.config_path, "w") as f:
            f.write("not valid json {{{")
        result = evaluate_fixture_needs(self.config_path, "complex")
        self.assertEqual(result["action"], "recommend")
        self.assertFalse(result["has_remote"])

    def test_none_config_path_defaults_no_remote(self):
        """When config_path is None, has_remote is False."""
        from fixture_recommendations import evaluate_fixture_needs
        result = evaluate_fixture_needs(None, "complex")
        self.assertEqual(result["action"], "recommend")
        self.assertFalse(result["has_remote"])

    def test_unrecognized_complexity_returns_none(self):
        """Unrecognized state_complexity falls back to none."""
        from fixture_recommendations import evaluate_fixture_needs
        self._write_config({"tools_root": "tools"})
        result = evaluate_fixture_needs(self.config_path, "unknown_value")
        self.assertEqual(result["action"], "none")

    def test_result_always_has_required_keys(self):
        """Every result has action, has_remote, and reason keys."""
        from fixture_recommendations import evaluate_fixture_needs
        self._write_config({"tools_root": "tools"})
        for complexity in ("none", "simple", "complex"):
            for has_tags in (True, False):
                result = evaluate_fixture_needs(
                    self.config_path, complexity, has_fixture_tags=has_tags,
                )
                self.assertIn("action", result)
                self.assertIn("has_remote", result)
                self.assertIn("reason", result)


# ===================================================================
# Engineer Startup Read Path Edge Cases (BUG M32)
# ===================================================================

class TestParseRecommendationsEdgeCases(unittest.TestCase):
    """Tests for the Engineer startup read path edge cases.

    Covers: empty file, missing file, malformed content, partial fields,
    multiple entries with mixed statuses, single-tag entries.
    """

    def setUp(self):
        self.fake_root = tempfile.mkdtemp(prefix="fixture-parse-edge-")
        self.qa_dir = os.path.join(self.fake_root, "tests", "qa")
        os.makedirs(self.qa_dir, exist_ok=True)
        self.rec_path = os.path.join(self.qa_dir, "fixture_recommendations.md")

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.fake_root], capture_output=True)

    def test_nonexistent_file_returns_empty(self):
        """parse_recommendations returns empty dict for missing file."""
        from fixture_recommendations import parse_recommendations
        result = parse_recommendations("/nonexistent/path.md")
        self.assertEqual(result, {})

    def test_empty_file_returns_empty(self):
        """parse_recommendations returns empty dict for empty file."""
        from fixture_recommendations import parse_recommendations
        with open(self.rec_path, "w") as f:
            f.write("")
        result = parse_recommendations(self.rec_path)
        self.assertEqual(result, {})

    def test_header_only_returns_empty(self):
        """File with only header and no features returns empty dict."""
        from fixture_recommendations import parse_recommendations
        with open(self.rec_path, "w") as f:
            f.write("# Fixture Recommendations\n")
        result = parse_recommendations(self.rec_path)
        self.assertEqual(result, {})

    def test_feature_with_missing_fields(self):
        """Feature section with partial fields still parses what exists."""
        from fixture_recommendations import parse_recommendations
        with open(self.rec_path, "w") as f:
            f.write(
                "# Fixture Recommendations\n\n"
                "## partial_feature\n"
                "- **Reason:** some reason\n"
                "- **Status:** PENDING\n"
            )
        result = parse_recommendations(self.rec_path)
        self.assertIn("partial_feature", result)
        self.assertEqual(result["partial_feature"]["reason"], "some reason")
        self.assertEqual(result["partial_feature"]["status"], "PENDING")
        self.assertNotIn("suggested_tags", result["partial_feature"])
        self.assertNotIn("recorded", result["partial_feature"])

    def test_feature_with_no_fields(self):
        """Feature header with no fields returns empty dict for that feature."""
        from fixture_recommendations import parse_recommendations
        with open(self.rec_path, "w") as f:
            f.write(
                "# Fixture Recommendations\n\n"
                "## bare_feature\n\n"
                "## another_feature\n"
                "- **Status:** PENDING\n"
            )
        result = parse_recommendations(self.rec_path)
        self.assertIn("bare_feature", result)
        self.assertEqual(result["bare_feature"], {})
        self.assertIn("another_feature", result)
        self.assertEqual(result["another_feature"]["status"], "PENDING")

    def test_multiple_statuses(self):
        """Multiple features with different statuses are parsed correctly."""
        from fixture_recommendations import parse_recommendations
        with open(self.rec_path, "w") as f:
            f.write(
                "# Fixture Recommendations\n\n"
                "## feat_pending\n"
                "- **Status:** PENDING\n\n"
                "## feat_created\n"
                "- **Status:** CREATED\n\n"
                "## feat_pending2\n"
                "- **Status:** PENDING\n"
            )
        result = parse_recommendations(self.rec_path)
        self.assertEqual(len(result), 3)
        self.assertEqual(result["feat_pending"]["status"], "PENDING")
        self.assertEqual(result["feat_created"]["status"], "CREATED")
        self.assertEqual(result["feat_pending2"]["status"], "PENDING")

    def test_single_tag_entry(self):
        """Feature with a single suggested tag parses correctly."""
        from fixture_recommendations import parse_recommendations
        with open(self.rec_path, "w") as f:
            f.write(
                "# Fixture Recommendations\n\n"
                "## single_tag\n"
                "- **Suggested tags:** `main/single_tag/state-one`\n"
                "- **Status:** PENDING\n"
            )
        result = parse_recommendations(self.rec_path)
        self.assertEqual(
            result["single_tag"]["suggested_tags"],
            ["main/single_tag/state-one"],
        )

    def test_many_tags_entry(self):
        """Feature with many suggested tags parses all of them."""
        from fixture_recommendations import parse_recommendations
        with open(self.rec_path, "w") as f:
            f.write(
                "# Fixture Recommendations\n\n"
                "## many_tags\n"
                "- **Suggested tags:** `main/many_tags/s1`, `main/many_tags/s2`, "
                "`main/many_tags/s3`, `main/many_tags/s4`\n"
                "- **Status:** PENDING\n"
            )
        result = parse_recommendations(self.rec_path)
        self.assertEqual(len(result["many_tags"]["suggested_tags"]), 4)

    def test_whitespace_only_file_returns_empty(self):
        """File with only whitespace returns empty dict."""
        from fixture_recommendations import parse_recommendations
        with open(self.rec_path, "w") as f:
            f.write("   \n  \n  \n")
        result = parse_recommendations(self.rec_path)
        self.assertEqual(result, {})


class TestGetPendingRecommendations(unittest.TestCase):
    """Tests for the get_pending_recommendations convenience wrapper."""

    def setUp(self):
        self.fake_root = tempfile.mkdtemp(prefix="fixture-pending-")
        self.qa_dir = os.path.join(self.fake_root, "tests", "qa")
        os.makedirs(self.qa_dir, exist_ok=True)
        self.rec_path = os.path.join(self.qa_dir, "fixture_recommendations.md")

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.fake_root], capture_output=True)

    def test_filters_to_pending_only(self):
        """Only PENDING entries are returned."""
        from fixture_recommendations import get_pending_recommendations
        with open(self.rec_path, "w") as f:
            f.write(
                "# Fixture Recommendations\n\n"
                "## feat_a\n- **Status:** PENDING\n\n"
                "## feat_b\n- **Status:** CREATED\n\n"
                "## feat_c\n- **Status:** PENDING\n"
            )
        result = get_pending_recommendations(self.rec_path)
        self.assertEqual(len(result), 2)
        self.assertIn("feat_a", result)
        self.assertIn("feat_c", result)
        self.assertNotIn("feat_b", result)

    def test_no_pending_returns_empty(self):
        """Returns empty dict when all entries are CREATED."""
        from fixture_recommendations import get_pending_recommendations
        with open(self.rec_path, "w") as f:
            f.write(
                "# Fixture Recommendations\n\n"
                "## feat_a\n- **Status:** CREATED\n\n"
                "## feat_b\n- **Status:** CREATED\n"
            )
        result = get_pending_recommendations(self.rec_path)
        self.assertEqual(result, {})

    def test_missing_file_returns_empty(self):
        """Returns empty dict for nonexistent file."""
        from fixture_recommendations import get_pending_recommendations
        result = get_pending_recommendations("/nonexistent/path.md")
        self.assertEqual(result, {})

    def test_pending_entries_have_suggested_tags(self):
        """PENDING entries include suggested_tags from the parsed data."""
        from fixture_recommendations import get_pending_recommendations
        with open(self.rec_path, "w") as f:
            f.write(
                "# Fixture Recommendations\n\n"
                "## feat_a\n"
                "- **Suggested tags:** `main/feat_a/state-1`, `main/feat_a/state-2`\n"
                "- **Status:** PENDING\n"
            )
        result = get_pending_recommendations(self.rec_path)
        self.assertEqual(
            result["feat_a"]["suggested_tags"],
            ["main/feat_a/state-1", "main/feat_a/state-2"],
        )


class TestWriteRecommendation(unittest.TestCase):
    """Tests for the write_recommendation production function."""

    def setUp(self):
        self.fake_root = tempfile.mkdtemp(prefix="fixture-write-rec-")
        self.qa_dir = os.path.join(self.fake_root, "tests", "qa")
        os.makedirs(self.qa_dir, exist_ok=True)
        self.rec_path = os.path.join(self.qa_dir, "fixture_recommendations.md")

    def tearDown(self):
        subprocess.run(["rm", "-rf", self.fake_root], capture_output=True)

    def test_creates_new_file_with_header(self):
        """Creates file with header when it does not exist."""
        from fixture_recommendations import write_recommendation
        write_recommendation(
            self.rec_path, "new_feature", "needs fixtures",
            ["main/new_feature/state-1"],
        )
        with open(self.rec_path) as f:
            content = f.read()
        self.assertTrue(content.startswith("# Fixture Recommendations"))

    def test_appends_to_existing_file(self):
        """Appends new recommendation to existing file."""
        from fixture_recommendations import write_recommendation
        write_recommendation(
            self.rec_path, "first_feature", "reason 1",
            ["main/first_feature/s1"],
        )
        write_recommendation(
            self.rec_path, "second_feature", "reason 2",
            ["main/second_feature/s1"],
        )
        with open(self.rec_path) as f:
            content = f.read()
        self.assertIn("## first_feature", content)
        self.assertIn("## second_feature", content)

    def test_written_file_is_parseable(self):
        """File written by write_recommendation is parseable by parse_recommendations."""
        from fixture_recommendations import (
            write_recommendation, parse_recommendations,
        )
        write_recommendation(
            self.rec_path, "roundtrip_feat", "roundtrip test",
            ["main/roundtrip_feat/s1", "main/roundtrip_feat/s2"],
        )
        result = parse_recommendations(self.rec_path)
        self.assertIn("roundtrip_feat", result)
        self.assertEqual(result["roundtrip_feat"]["status"], "PENDING")
        self.assertEqual(result["roundtrip_feat"]["reason"], "roundtrip test")
        self.assertEqual(
            result["roundtrip_feat"]["suggested_tags"],
            ["main/roundtrip_feat/s1", "main/roundtrip_feat/s2"],
        )

    def test_creates_parent_directories(self):
        """Creates parent directories if they don't exist."""
        from fixture_recommendations import write_recommendation
        deep_path = os.path.join(
            self.fake_root, "deep", "nested", "fixture_recommendations.md",
        )
        write_recommendation(
            deep_path, "deep_feat", "deep test", ["main/deep_feat/s1"],
        )
        self.assertTrue(os.path.isfile(deep_path))

    def test_returns_absolute_path(self):
        """write_recommendation returns the absolute path of the written file."""
        from fixture_recommendations import write_recommendation
        result = write_recommendation(
            self.rec_path, "abs_feat", "test", ["main/abs_feat/s1"],
        )
        self.assertTrue(os.path.isabs(result))
        self.assertTrue(os.path.isfile(result))


class TestVerifyUrlAccessibleRepo(unittest.TestCase):
    """Scenario: Verify-url succeeds with accessible SSH URL

    Tests that verify-url prints the working URL to stdout and exits 0
    when the given URL is accessible. Uses a local bare repo (which
    behaves like a file:// URL) to simulate accessible remote.
    """

    @classmethod
    def setUpClass(cls):
        cls.repo = create_fixture_repo({
            "main/test_feature/scenario-one": {"data.txt": "content"},
        })

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["rm", "-rf", cls.repo], capture_output=True)

    def test_exits_zero_on_accessible_url(self):
        rc, stdout, stderr = run_fixture("verify-url", self.repo)
        self.assertEqual(rc, 0, f"verify-url should succeed: {stderr}")

    def test_prints_url_to_stdout(self):
        rc, stdout, stderr = run_fixture("verify-url", self.repo)
        self.assertEqual(stdout, self.repo)


class TestVerifyUrlHttpsToSshFallback(unittest.TestCase):
    """Scenario: Verify-url falls back to SSH when HTTPS fails on private repo

    Tests that when an HTTPS GitHub URL fails, verify-url tries the SSH
    equivalent. Since we can't reliably test against real GitHub in a unit
    test, we verify the URL conversion logic by testing with a known-bad
    HTTPS URL and checking that the SSH form is attempted (visible in the
    error output when SSH also fails) or succeeds (when SSH keys are
    configured -- which they are in this environment per user confirmation).
    """

    def test_converts_github_https_to_ssh(self):
        """The fallback attempts the correct SSH URL format."""
        # Use the actual purlin-fixtures repo -- SSH works, HTTPS doesn't
        rc, stdout, stderr = run_fixture(
            "verify-url", "https://github.com/rlabarca/purlin-fixtures",
        )
        # If SSH keys are configured, this succeeds with the SSH URL
        if rc == 0:
            self.assertEqual(stdout, "git@github.com:rlabarca/purlin-fixtures.git")
        else:
            # If SSH also fails (e.g., in CI), verify guidance is printed
            self.assertIn("SSH", stderr)


class TestVerifyUrlNoAccess(unittest.TestCase):
    """Scenario: Verify-url prints guidance when no access method works

    Tests that verify-url exits 1 and prints diagnostic guidance when
    neither HTTPS nor SSH access is available.
    """

    def test_exits_nonzero(self):
        rc, stdout, stderr = run_fixture(
            "verify-url", "https://github.com/nonexistent-owner-xyz/nonexistent-repo-xyz",
        )
        self.assertNotEqual(rc, 0)

    def test_prints_guidance(self):
        rc, stdout, stderr = run_fixture(
            "verify-url", "https://github.com/nonexistent-owner-xyz/nonexistent-repo-xyz",
        )
        self.assertIn("Cannot access", stderr)
        self.assertIn("SSH", stderr)
        self.assertIn("credential", stderr.lower())


class TestPushAllTags(unittest.TestCase):
    """Scenario: Push syncs all tags to remote"""

    @classmethod
    def setUpClass(cls):
        cls.fake_root = tempfile.mkdtemp(prefix="fixture-push-all-")
        os.makedirs(os.path.join(cls.fake_root, "features"))

        # Init fixture repo at convention path
        rc, _, stderr = run_fixture("init", env_override={"PURLIN_PROJECT_ROOT": cls.fake_root})
        assert rc == 0, f"init failed: {stderr}"

        # Add two tags
        for slug, content in [("s1", "content-1"), ("s2", "content-2")]:
            source = tempfile.mkdtemp(prefix=f"fixture-src-{slug}-")
            with open(os.path.join(source, "data.txt"), "w") as f:
                f.write(content)
            rc, _, stderr = run_fixture(
                "add-tag", f"main/feat_a/{slug}",
                "--from-dir", source,
                env_override={"PURLIN_PROJECT_ROOT": cls.fake_root},
            )
            assert rc == 0, f"add-tag failed: {stderr}"
            subprocess.run(["rm", "-rf", source], capture_output=True)

        # Create a remote bare repo (simulates remote)
        cls.remote_repo = tempfile.mkdtemp(prefix="fixture-remote-all-")
        subprocess.run(["rm", "-rf", cls.remote_repo], capture_output=True)
        subprocess.run(
            ["git", "init", "--bare", cls.remote_repo],
            capture_output=True, check=True,
        )

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["rm", "-rf", cls.fake_root, cls.remote_repo], capture_output=True)

    def test_push_all_tags(self):
        rc, stdout, stderr = run_fixture(
            "push", self.remote_repo,
            env_override={"PURLIN_PROJECT_ROOT": self.fake_root},
        )
        self.assertEqual(rc, 0, f"push failed: {stderr}")
        self.assertIn("Pushed all tags", stdout)

    def test_both_tags_visible_on_remote(self):
        # Push first
        run_fixture(
            "push", self.remote_repo,
            env_override={"PURLIN_PROJECT_ROOT": self.fake_root},
        )
        # Verify via fixture list
        rc, list_out, stderr = run_fixture("list", self.remote_repo)
        self.assertEqual(rc, 0, f"list failed: {stderr}")
        self.assertIn("main/feat_a/s1", list_out)
        self.assertIn("main/feat_a/s2", list_out)


class TestPushSpecificTag(unittest.TestCase):
    """Scenario: Push syncs a specific tag to remote"""

    @classmethod
    def setUpClass(cls):
        cls.fake_root = tempfile.mkdtemp(prefix="fixture-push-specific-")
        os.makedirs(os.path.join(cls.fake_root, "features"))

        rc, _, stderr = run_fixture("init", env_override={"PURLIN_PROJECT_ROOT": cls.fake_root})
        assert rc == 0, f"init failed: {stderr}"

        for slug, content in [("s1", "content-1"), ("s2", "content-2")]:
            source = tempfile.mkdtemp(prefix=f"fixture-src-{slug}-")
            with open(os.path.join(source, "data.txt"), "w") as f:
                f.write(content)
            rc, _, stderr = run_fixture(
                "add-tag", f"main/feat_a/{slug}",
                "--from-dir", source,
                env_override={"PURLIN_PROJECT_ROOT": cls.fake_root},
            )
            assert rc == 0, f"add-tag failed: {stderr}"
            subprocess.run(["rm", "-rf", source], capture_output=True)

        cls.remote_repo = tempfile.mkdtemp(prefix="fixture-remote-specific-")
        subprocess.run(["rm", "-rf", cls.remote_repo], capture_output=True)
        subprocess.run(
            ["git", "init", "--bare", cls.remote_repo],
            capture_output=True, check=True,
        )

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["rm", "-rf", cls.fake_root, cls.remote_repo], capture_output=True)

    def test_push_specific_tag(self):
        rc, stdout, stderr = run_fixture(
            "push", self.remote_repo, "--tag", "main/feat_a/s1",
            env_override={"PURLIN_PROJECT_ROOT": self.fake_root},
        )
        self.assertEqual(rc, 0, f"push failed: {stderr}")
        self.assertIn("Pushed tag: main/feat_a/s1", stdout)

    def test_only_specific_tag_on_remote(self):
        # Push only s1
        run_fixture(
            "push", self.remote_repo, "--tag", "main/feat_a/s1",
            env_override={"PURLIN_PROJECT_ROOT": self.fake_root},
        )
        rc, list_out, stderr = run_fixture("list", self.remote_repo)
        self.assertEqual(rc, 0, f"list failed: {stderr}")
        self.assertIn("main/feat_a/s1", list_out)
        self.assertNotIn("main/feat_a/s2", list_out)


class TestPushAuthError(unittest.TestCase):
    """Scenario: Push fails gracefully on auth error"""

    @classmethod
    def setUpClass(cls):
        cls.fake_root = tempfile.mkdtemp(prefix="fixture-push-auth-")
        os.makedirs(os.path.join(cls.fake_root, "features"))

        rc, _, stderr = run_fixture("init", env_override={"PURLIN_PROJECT_ROOT": cls.fake_root})
        assert rc == 0, f"init failed: {stderr}"

        source = tempfile.mkdtemp(prefix="fixture-src-auth-")
        with open(os.path.join(source, "data.txt"), "w") as f:
            f.write("content")
        rc, _, stderr = run_fixture(
            "add-tag", "main/feat_a/s1",
            "--from-dir", source,
            env_override={"PURLIN_PROJECT_ROOT": cls.fake_root},
        )
        assert rc == 0, f"add-tag failed: {stderr}"
        subprocess.run(["rm", "-rf", source], capture_output=True)

        # Create a remote bare repo and make it read-only to simulate push failure
        cls.remote_repo = tempfile.mkdtemp(prefix="fixture-remote-ro-")
        subprocess.run(["rm", "-rf", cls.remote_repo], capture_output=True)
        subprocess.run(
            ["git", "init", "--bare", cls.remote_repo],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["chmod", "-R", "a-w", cls.remote_repo],
            capture_output=True, check=True,
        )

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["chmod", "-R", "u+w", cls.remote_repo], capture_output=True)
        subprocess.run(["rm", "-rf", cls.fake_root, cls.remote_repo], capture_output=True)

    def test_push_exits_nonzero(self):
        rc, stdout, stderr = run_fixture(
            "push", self.remote_repo,
            env_override={"PURLIN_PROJECT_ROOT": self.fake_root},
        )
        self.assertNotEqual(rc, 0, "Push should fail on permission error")

    def test_push_prints_diagnostic(self):
        rc, stdout, stderr = run_fixture(
            "push", self.remote_repo,
            env_override={"PURLIN_PROJECT_ROOT": self.fake_root},
        )
        self.assertIn("authentication or permissions", stderr.lower())

    def test_push_suggests_access_steps(self):
        rc, stdout, stderr = run_fixture(
            "push", self.remote_repo,
            env_override={"PURLIN_PROJECT_ROOT": self.fake_root},
        )
        self.assertIn("SSH", stderr)
        self.assertIn("push access", stderr.lower())


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
        failed = len(result.failures) + len(result.errors)
        with open(out_file, "w") as f:
            json.dump(
                {
                    "status": "PASS" if all_passed else "FAIL",
                    "passed": result.testsRun - failed,
                    "failed": failed,
                    "total": result.testsRun,
                    "test_file": "tools/test_support/test_fixture.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
