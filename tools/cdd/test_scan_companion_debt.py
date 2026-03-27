"""Unit tests for scan_companion_debt() in tools/cdd/scan.py.

Tests cover:
  a. Missing companion file (debt_type "missing")
  b. Stale companion file (debt_type "stale")
  c. Up-to-date companion (no debt)
  d. Feature without code (no test directory -> no debt)
  e. Anchor features skipped (arch_*, design_*, policy_*)
"""

import os
import shutil
import subprocess
import tempfile
import time
import unittest


class TestScanCompanionDebt(unittest.TestCase):
    """Tests for scan_companion_debt() using a temporary git repository."""

    @classmethod
    def setUpClass(cls):
        """Create a temporary git repo with controlled directory structure."""
        cls.tmpdir = tempfile.mkdtemp(prefix="test_companion_debt_")
        cls.features_dir = os.path.join(cls.tmpdir, "features")
        cls.tests_dir = os.path.join(cls.tmpdir, "tests")
        cls.purlin_dir = os.path.join(cls.tmpdir, ".purlin")
        os.makedirs(cls.features_dir)
        os.makedirs(cls.tests_dir)
        os.makedirs(cls.purlin_dir)

        # Initialize a git repo.
        subprocess.run(
            ["git", "init"], cwd=cls.tmpdir,
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=cls.tmpdir,
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=cls.tmpdir,
            capture_output=True, check=True,
        )

    @classmethod
    def tearDownClass(cls):
        """Remove the temporary directory."""
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _commit_file(self, relpath, content="placeholder"):
        """Create a file at relpath (relative to tmpdir), add, and commit it."""
        filepath = os.path.join(self.tmpdir, relpath)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        subprocess.run(
            ["git", "add", relpath], cwd=self.tmpdir,
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"add {relpath}"], cwd=self.tmpdir,
            capture_output=True, check=True,
        )

    def _write_file(self, relpath, content="placeholder"):
        """Create a file at relpath without committing it."""
        filepath = os.path.join(self.tmpdir, relpath)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        return filepath

    def _set_mtime(self, relpath, timestamp):
        """Set the modification time of a file."""
        filepath = os.path.join(self.tmpdir, relpath)
        os.utime(filepath, (timestamp, timestamp))

    def _get_code_commit_ts(self, stem):
        """Get the latest commit timestamp for tests/<stem>/."""
        test_dir = os.path.join(self.tests_dir, stem)
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", test_dir],
            capture_output=True, text=True, timeout=5,
            cwd=self.tmpdir,
        )
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        return None

    def _call_scan_companion_debt(self):
        """Call scan_companion_debt() with module constants patched to tmpdir."""
        import tools.cdd.scan as scan_mod

        orig_project_root = scan_mod.PROJECT_ROOT
        orig_features_dir = scan_mod.FEATURES_DIR
        orig_tests_dir = scan_mod.TESTS_DIR

        scan_mod.PROJECT_ROOT = self.tmpdir
        scan_mod.FEATURES_DIR = self.features_dir
        scan_mod.TESTS_DIR = self.tests_dir

        try:
            return scan_mod.scan_companion_debt()
        finally:
            scan_mod.PROJECT_ROOT = orig_project_root
            scan_mod.FEATURES_DIR = orig_features_dir
            scan_mod.TESTS_DIR = orig_tests_dir

    # ------------------------------------------------------------------
    # a. Missing companion file
    # ------------------------------------------------------------------
    def test_missing_companion_file_produces_missing_debt(self):
        """Feature with committed code but no .impl.md -> debt_type 'missing'."""
        stem = "feat_missing_companion"

        # Create feature spec.
        self._write_file(f"features/{stem}.md", "# Feature Spec\n")
        # Create test directory with committed code.
        self._commit_file(f"tests/{stem}/test_example.py", "assert True\n")

        # Ensure no companion file exists.
        companion = os.path.join(self.features_dir, f"{stem}.impl.md")
        if os.path.exists(companion):
            os.remove(companion)

        debt = self._call_scan_companion_debt()
        matching = [d for d in debt if d["feature"] == stem]

        self.assertEqual(len(matching), 1, f"Expected 1 debt item for {stem}")
        self.assertEqual(matching[0]["debt_type"], "missing")
        self.assertEqual(matching[0]["file"], f"features/{stem}.impl.md")
        self.assertIn("latest_code_commit", matching[0])

    # ------------------------------------------------------------------
    # b. Stale companion file
    # ------------------------------------------------------------------
    def test_stale_companion_file_produces_stale_debt(self):
        """Feature with .impl.md older than code commits -> debt_type 'stale'."""
        stem = "feat_stale_companion"

        # Create feature spec.
        self._write_file(f"features/{stem}.md", "# Feature Spec\n")
        # Create companion file with old timestamp.
        self._write_file(f"features/{stem}.impl.md", "# Companion\n")
        # Set companion mtime to the past (one hour ago).
        old_time = time.time() - 3600
        self._set_mtime(f"features/{stem}.impl.md", old_time)

        # Sleep briefly so commit timestamp is guaranteed newer.
        time.sleep(1)

        # Commit code in the test directory (this creates a newer commit).
        self._commit_file(
            f"tests/{stem}/test_example.py", "assert True  # stale\n"
        )

        # Verify the code commit is indeed newer than the companion mtime.
        code_ts = self._get_code_commit_ts(stem)
        self.assertIsNotNone(code_ts)
        self.assertGreater(code_ts, old_time)

        debt = self._call_scan_companion_debt()
        matching = [d for d in debt if d["feature"] == stem]

        self.assertEqual(len(matching), 1, f"Expected 1 debt item for {stem}")
        self.assertEqual(matching[0]["debt_type"], "stale")
        self.assertIn("latest_code_commit", matching[0])
        self.assertIn("companion_mtime", matching[0])

    # ------------------------------------------------------------------
    # c. Up-to-date companion (no debt)
    # ------------------------------------------------------------------
    def test_up_to_date_companion_produces_no_debt(self):
        """Feature with .impl.md newer than code commits -> no debt."""
        stem = "feat_uptodate_companion"

        # Create feature spec.
        self._write_file(f"features/{stem}.md", "# Feature Spec\n")
        # Commit code FIRST.
        self._commit_file(
            f"tests/{stem}/test_example.py", "assert True  # uptodate\n"
        )

        # Now create/update the companion file with a timestamp in the future.
        self._write_file(
            f"features/{stem}.impl.md", "# Companion (updated)\n"
        )
        future_time = time.time() + 3600
        self._set_mtime(f"features/{stem}.impl.md", future_time)

        debt = self._call_scan_companion_debt()
        matching = [d for d in debt if d["feature"] == stem]

        self.assertEqual(
            len(matching), 0,
            f"Expected no debt for {stem} but got: {matching}",
        )

    # ------------------------------------------------------------------
    # d. Feature without code (no test directory)
    # ------------------------------------------------------------------
    def test_feature_without_code_produces_no_debt(self):
        """Feature spec exists but no tests/<stem>/ directory -> no debt."""
        stem = "feat_no_code"

        # Create feature spec only -- no test directory.
        self._write_file(f"features/{stem}.md", "# Feature Spec (no code)\n")

        # Ensure test directory does NOT exist.
        test_dir = os.path.join(self.tests_dir, stem)
        if os.path.isdir(test_dir):
            shutil.rmtree(test_dir)

        debt = self._call_scan_companion_debt()
        matching = [d for d in debt if d["feature"] == stem]

        self.assertEqual(
            len(matching), 0,
            f"Expected no debt for spec-only feature {stem} but got: {matching}",
        )

    # ------------------------------------------------------------------
    # e. Anchor features are skipped
    # ------------------------------------------------------------------
    def test_anchor_features_are_skipped(self):
        """Features with arch_*, design_*, policy_* prefixes are skipped."""
        for prefix in ("arch_", "design_", "policy_"):
            stem = f"{prefix}some_anchor"

            # Create spec and test directory with committed code.
            self._write_file(
                f"features/{stem}.md", f"# {prefix} anchor spec\n"
            )
            self._commit_file(
                f"tests/{stem}/test_anchor.py",
                f"# anchor test for {prefix}\n",
            )

        debt = self._call_scan_companion_debt()
        anchor_debt = [
            d
            for d in debt
            if d["feature"].startswith(("arch_", "design_", "policy_"))
        ]

        self.assertEqual(
            len(anchor_debt), 0,
            f"Expected anchors to be skipped but got: {anchor_debt}",
        )

    # ------------------------------------------------------------------
    # Additional: empty features directory
    # ------------------------------------------------------------------
    def test_empty_features_dir_returns_empty_list(self):
        """When FEATURES_DIR has no .md files, returns empty list."""
        import tools.cdd.scan as scan_mod

        empty_dir = tempfile.mkdtemp(prefix="test_empty_features_")
        try:
            orig = scan_mod.FEATURES_DIR
            scan_mod.FEATURES_DIR = empty_dir
            # Also patch PROJECT_ROOT and TESTS_DIR for consistency.
            orig_root = scan_mod.PROJECT_ROOT
            orig_tests = scan_mod.TESTS_DIR
            scan_mod.PROJECT_ROOT = self.tmpdir
            scan_mod.TESTS_DIR = self.tests_dir
            try:
                debt = scan_mod.scan_companion_debt()
                self.assertEqual(debt, [])
            finally:
                scan_mod.FEATURES_DIR = orig
                scan_mod.PROJECT_ROOT = orig_root
                scan_mod.TESTS_DIR = orig_tests
        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Additional: discoveries and impl files are not treated as specs
    # ------------------------------------------------------------------
    def test_discoveries_and_impl_files_not_treated_as_specs(self):
        """Files ending in .impl.md or .discoveries.md are not feature specs."""
        stem = "feat_impl_only"

        # Create ONLY an impl.md and discoveries.md -- no plain .md spec.
        self._write_file(
            f"features/{stem}.impl.md", "# Companion only\n"
        )
        self._write_file(
            f"features/{stem}.discoveries.md", "# Discoveries\n"
        )
        # Create test directory with committed code.
        self._commit_file(
            f"tests/{stem}/test_impl.py", "# test\n"
        )

        debt = self._call_scan_companion_debt()
        matching = [d for d in debt if d["feature"] == stem]

        self.assertEqual(
            len(matching), 0,
            f"impl/discoveries files should not be treated as specs: {matching}",
        )

    # ------------------------------------------------------------------
    # Additional: return structure validation
    # ------------------------------------------------------------------
    def test_debt_item_has_expected_fields_for_missing(self):
        """Verify the dict structure for a 'missing' debt item."""
        stem = "feat_fields_missing"
        self._write_file(f"features/{stem}.md", "# Spec\n")
        self._commit_file(f"tests/{stem}/test_f.py", "pass\n")

        # Remove companion if exists.
        companion = os.path.join(self.features_dir, f"{stem}.impl.md")
        if os.path.exists(companion):
            os.remove(companion)

        debt = self._call_scan_companion_debt()
        matching = [d for d in debt if d["feature"] == stem]
        self.assertEqual(len(matching), 1)

        item = matching[0]
        self.assertIn("feature", item)
        self.assertIn("file", item)
        self.assertIn("debt_type", item)
        self.assertIn("latest_code_commit", item)
        self.assertEqual(item["debt_type"], "missing")
        # Missing items should NOT have companion_mtime.
        self.assertNotIn("companion_mtime", item)

    def test_debt_item_has_expected_fields_for_stale(self):
        """Verify the dict structure for a 'stale' debt item."""
        stem = "feat_fields_stale"
        self._write_file(f"features/{stem}.md", "# Spec\n")
        self._write_file(f"features/{stem}.impl.md", "# Companion\n")
        old_time = time.time() - 7200
        self._set_mtime(f"features/{stem}.impl.md", old_time)

        time.sleep(1)
        self._commit_file(f"tests/{stem}/test_f.py", "pass  # stale fields\n")

        debt = self._call_scan_companion_debt()
        matching = [d for d in debt if d["feature"] == stem]
        self.assertEqual(len(matching), 1)

        item = matching[0]
        self.assertIn("feature", item)
        self.assertIn("file", item)
        self.assertIn("debt_type", item)
        self.assertIn("latest_code_commit", item)
        self.assertIn("companion_mtime", item)
        self.assertEqual(item["debt_type"], "stale")
        # Timestamps should be ISO-8601 formatted.
        self.assertRegex(item["latest_code_commit"], r"\d{4}-\d{2}-\d{2}T")
        self.assertRegex(item["companion_mtime"], r"\d{4}-\d{2}-\d{2}T")


if __name__ == "__main__":
    unittest.main()
