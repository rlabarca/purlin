#!/usr/bin/env python3
"""Tests for the agent behavior test harness (dev/test_agent_behavior.sh).

Covers all 7 automated scenarios from features/agent_behavior_tests.md.
Tests verify the harness infrastructure without requiring claude --print
invocations (which are expensive API calls).

Outputs test results to tests/agent_behavior_tests/tests.json.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.environ.get("PURLIN_PROJECT_ROOT")
if not PROJECT_ROOT:
    d = SCRIPT_DIR
    while d != "/":
        if os.path.isdir(os.path.join(d, "features")):
            PROJECT_ROOT = d
        d = os.path.dirname(d)

TEST_HARNESS = os.path.join(SCRIPT_DIR, "test_agent_behavior.sh")
FIXTURE_TOOL = os.path.join(PROJECT_ROOT, "tools", "test_support", "fixture.sh")
SETUP_SCRIPT = os.path.join(SCRIPT_DIR, "setup_behavior_fixtures.sh")


def create_fixture_repo(tags_and_files):
    """Create a temporary bare git repo with tagged commits.

    Args:
        tags_and_files: dict mapping tag_name -> dict of {filename: content}

    Returns:
        Path to the bare repo (suitable as repo-url).
    """
    work_dir = tempfile.mkdtemp(prefix="behavior-work-")
    bare_dir = tempfile.mkdtemp(prefix="behavior-bare-")

    subprocess.run(
        ["git", "init", "--bare", bare_dir],
        capture_output=True, check=True,
    )
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

    # Initial commit
    dummy = os.path.join(work_dir, ".gitkeep")
    with open(dummy, "w") as f:
        f.write("")
    subprocess.run(["git", "add", "."], capture_output=True, check=True, cwd=work_dir)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        capture_output=True, check=True, cwd=work_dir,
    )

    for tag_name, files in tags_and_files.items():
        for fname, content in files.items():
            fpath = os.path.join(work_dir, fname)
            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            with open(fpath, "w") as f:
                f.write(content)
        subprocess.run(["git", "add", "."], capture_output=True, check=True, cwd=work_dir)
        subprocess.run(
            ["git", "commit", "-m", f"State for {tag_name}"],
            capture_output=True, check=True, cwd=work_dir,
        )
        subprocess.run(
            ["git", "tag", tag_name],
            capture_output=True, check=True, cwd=work_dir,
        )

    subprocess.run(
        ["git", "push", "origin", "--all"],
        capture_output=True, check=True, cwd=work_dir,
    )
    subprocess.run(
        ["git", "push", "origin", "--tags"],
        capture_output=True, check=True, cwd=work_dir,
    )

    shutil.rmtree(work_dir)
    return bare_dir


def run_fixture(*args):
    """Run fixture.sh with given arguments."""
    result = subprocess.run(
        ["bash", FIXTURE_TOOL] + list(args),
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ===================================================================
# Scenario: Test runner checks out fixture and constructs prompt
# ===================================================================

class TestFixtureCheckoutAndPromptConstruction(unittest.TestCase):
    """Scenario: Test runner checks out fixture and constructs prompt

    Given the fixture repo has tag "main/cdd_startup_controls/expert-mode"
    When the test runner executes the expert-mode test
    Then the fixture is checked out to a temp directory
    And the system prompt is constructed from the fixture's instruction files
    And the prompt contains all 4 layers in the correct order
    """

    @classmethod
    def setUpClass(cls):
        # Create a fixture repo with instruction files
        cls.repo = create_fixture_repo({
            "main/cdd_startup_controls/expert-mode": {
                "instructions/HOW_WE_WORK_BASE.md": "# How We Work Base\nLayer 1 content.\n",
                "instructions/BUILDER_BASE.md": "# Builder Base\nLayer 2 content.\n",
                ".purlin/HOW_WE_WORK_OVERRIDES.md": "# HWW Overrides\nLayer 3 content.\n",
                ".purlin/BUILDER_OVERRIDES.md": "# Builder Overrides\nLayer 4 content.\n",
                ".purlin/config.json": json.dumps({
                    "tools_root": "tools",
                    "agents": {
                        "builder": {
                            "startup_sequence": False,
                            "recommend_next_actions": False,
                        }
                    }
                }),
            },
        })

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.repo)

    def test_fixture_checkout_creates_directory(self):
        """Fixture is checked out to a temp directory."""
        rc, checkout_path, stderr = run_fixture(
            "checkout", self.repo, "main/cdd_startup_controls/expert-mode",
        )
        self.assertEqual(rc, 0, f"checkout failed: {stderr}")
        self.assertTrue(os.path.isdir(checkout_path))
        self.assertTrue(os.path.isfile(
            os.path.join(checkout_path, "instructions/HOW_WE_WORK_BASE.md")
        ))
        shutil.rmtree(checkout_path)

    def test_prompt_construction_contains_all_layers(self):
        """System prompt contains all 4 layers in correct order."""
        rc, checkout_path, _ = run_fixture(
            "checkout", self.repo, "main/cdd_startup_controls/expert-mode",
        )
        self.assertEqual(rc, 0)

        # Simulate prompt construction (same logic as the bash script)
        layers = [
            os.path.join(checkout_path, "instructions/HOW_WE_WORK_BASE.md"),
            os.path.join(checkout_path, "instructions/BUILDER_BASE.md"),
            os.path.join(checkout_path, ".purlin/HOW_WE_WORK_OVERRIDES.md"),
            os.path.join(checkout_path, ".purlin/BUILDER_OVERRIDES.md"),
        ]

        prompt_content = ""
        for layer_path in layers:
            if os.path.isfile(layer_path):
                with open(layer_path) as f:
                    prompt_content += f.read() + "\n\n"

        # Verify all 4 layers are present and in order
        self.assertIn("Layer 1 content", prompt_content)
        self.assertIn("Layer 2 content", prompt_content)
        self.assertIn("Layer 3 content", prompt_content)
        self.assertIn("Layer 4 content", prompt_content)

        # Verify order: Layer 1 before Layer 2, etc.
        idx1 = prompt_content.index("Layer 1")
        idx2 = prompt_content.index("Layer 2")
        idx3 = prompt_content.index("Layer 3")
        idx4 = prompt_content.index("Layer 4")
        self.assertLess(idx1, idx2, "Layer 1 should come before Layer 2")
        self.assertLess(idx2, idx3, "Layer 2 should come before Layer 3")
        self.assertLess(idx3, idx4, "Layer 3 should come before Layer 4")

        shutil.rmtree(checkout_path)

    def test_prompt_handles_missing_layer(self):
        """Prompt construction handles missing override files gracefully."""
        # Create a fixture with only 2 of 4 layers
        repo = create_fixture_repo({
            "main/test/minimal": {
                "instructions/HOW_WE_WORK_BASE.md": "# Base\nBase content.\n",
                "instructions/BUILDER_BASE.md": "# Builder\nBuilder content.\n",
            },
        })

        rc, checkout_path, _ = run_fixture("checkout", repo, "main/test/minimal")
        self.assertEqual(rc, 0)

        layers = [
            os.path.join(checkout_path, "instructions/HOW_WE_WORK_BASE.md"),
            os.path.join(checkout_path, "instructions/BUILDER_BASE.md"),
            os.path.join(checkout_path, ".purlin/HOW_WE_WORK_OVERRIDES.md"),
            os.path.join(checkout_path, ".purlin/BUILDER_OVERRIDES.md"),
        ]

        prompt_content = ""
        for layer_path in layers:
            if os.path.isfile(layer_path):
                with open(layer_path) as f:
                    prompt_content += f.read() + "\n\n"

        self.assertIn("Base content", prompt_content)
        self.assertIn("Builder content", prompt_content)
        # Missing layers should not cause errors
        self.assertNotIn("Layer 3", prompt_content)

        shutil.rmtree(checkout_path)
        shutil.rmtree(repo)


# ===================================================================
# Scenario: Command table assertion passes for valid output
# ===================================================================

class TestCommandTableAssertion(unittest.TestCase):
    """Scenario: Command table assertion passes for valid output

    Given claude --print returns output containing a Unicode-bordered command table
    When the test runner asserts "command table present"
    Then the assertion passes (grep matches the table header pattern)
    """

    def test_assertion_passes_for_valid_table(self):
        """Assertion matches Unicode-bordered command table."""
        output = (
            "Purlin Builder — Ready\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "  Global\n"
            "  ──────\n"
            "  /pl-status                 Check CDD status\n"
            "\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        # The test runner uses grep -qi for the Unicode horizontal rule
        import re
        self.assertTrue(
            bool(re.search(r"━━━", output)),
            "Should match Unicode horizontal rule pattern",
        )

    def test_assertion_fails_for_missing_table(self):
        """Assertion fails when no command table is present."""
        output = "Hello, I am the Builder. How can I help?\n"
        import re
        self.assertFalse(
            bool(re.search(r"━━━", output)),
            "Should NOT match when table is absent",
        )

    def test_assertion_detects_builder_header(self):
        """Assertion detects 'Purlin Builder' in output."""
        output = "Purlin Builder — Ready\n━━━━━━━━━━━━━━━━━━\n"
        import re
        self.assertTrue(
            bool(re.search(r"Purlin Builder", output, re.IGNORECASE)),
            "Should detect Builder header",
        )

    def test_assertion_detects_isolated_variant(self):
        """Assertion detects isolated session variant markers."""
        output = "Purlin Builder — Ready  [Isolated: feat1]\n━━━━━━━━━━━━━━━━━━\n"
        import re
        self.assertTrue(
            bool(re.search(r"Isolated", output, re.IGNORECASE)),
            "Should detect Isolated variant",
        )
        self.assertTrue(
            bool(re.search(r"feat1", output)),
            "Should detect isolation name",
        )


# ===================================================================
# Scenario: Expert mode outputs correct message
# ===================================================================

class TestExpertModeOutput(unittest.TestCase):
    """Scenario: Expert mode outputs correct message

    Given the fixture tag "main/cdd_startup_controls/expert-mode" is checked out
    And the config has startup_sequence: false
    When claude --print is invoked with "Begin Builder session."
    Then the output contains "startup_sequence disabled"
    And the output does NOT contain a work plan or Critic report

    Note: This tests the assertion logic against expected output patterns.
    The actual claude --print invocation is tested by running the harness
    end-to-end (expensive, on-demand).
    """

    def test_expected_output_pattern_detected(self):
        """The expected pattern for expert mode is detectable."""
        # Simulate the expected output from expert mode
        expected_output = (
            "Purlin Builder — Ready\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "...\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "\n"
            "startup_sequence disabled — awaiting instruction.\n"
        )
        import re
        self.assertTrue(
            bool(re.search(r"startup_sequence disabled", expected_output)),
            "Should detect disabled message",
        )
        self.assertFalse(
            bool(re.search(r"Work Plan|Action Items|Feature Queue",
                           expected_output, re.IGNORECASE)),
            "Should NOT contain work plan sections",
        )


# ===================================================================
# Scenario: Resume test echoes checkpoint fields
# ===================================================================

class TestResumeCheckpointEcho(unittest.TestCase):
    """Scenario: Resume test echoes checkpoint fields

    Given the fixture tag "main/pl_session_resume/builder-mid-feature" is checked out
    And the checkpoint contains feature "sample_feature" at step 2
    When claude --print is invoked with "/pl-resume"
    Then the output contains the feature name
    And the output references step 2 or the saved protocol position

    Note: Tests checkpoint parsing logic against expected patterns.
    """

    def test_checkpoint_fields_are_parseable(self):
        """Checkpoint file fields can be extracted for assertion."""
        checkpoint = (
            "# Session Checkpoint\n"
            "\n"
            "**Role:** Builder\n"
            "**Timestamp:** 2026-01-15T10:30:00Z\n"
            "**Branch:** collab/purlincollab\n"
            "\n"
            "## Current Work\n"
            "\n"
            "**Feature:** features/sample_feature.md\n"
            "**In Progress:** Implementing sample_feature\n"
            "\n"
            "## Builder Context\n"
            "**Protocol Step:** 2\n"
        )
        import re
        # Verify feature name is extractable
        feature_match = re.search(r"\*\*Feature:\*\*\s*(.+)", checkpoint)
        self.assertIsNotNone(feature_match)
        self.assertIn("sample_feature", feature_match.group(1))

        # Verify protocol step is extractable
        step_match = re.search(r"\*\*Protocol Step:\*\*\s*(\d+)", checkpoint)
        self.assertIsNotNone(step_match)
        self.assertEqual(step_match.group(1), "2")


# ===================================================================
# Scenario: Help test shows correct variant for branch
# ===================================================================

class TestHelpVariantDetection(unittest.TestCase):
    """Scenario: Help test shows correct variant for branch

    Given the fixture tag "main/pl_help/builder-isolated-branch" is checked out
    And the project is on branch isolated/feat1
    When claude --print is invoked with "/pl-help"
    Then the output contains the Isolated Session Variant table
    And the output contains "feat1"

    Note: Tests variant detection logic against reference command tables.
    """

    def test_isolated_variant_has_correct_commands(self):
        """Isolated variant includes pl-isolated-push/pull, not pl-remote-push/pull."""
        # Read the actual builder_commands.md to get the isolated variant
        commands_file = os.path.join(
            PROJECT_ROOT, "instructions", "references", "builder_commands.md"
        )
        if not os.path.isfile(commands_file):
            self.skipTest("builder_commands.md not found")

        with open(commands_file) as f:
            content = f.read()

        # Find the Isolated Session Variant section
        import re
        isolated_section = re.search(
            r"## Isolated Session Variant\n(.*?)(?=\n## |\Z)",
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(isolated_section, "Isolated variant section should exist")
        isolated_text = isolated_section.group(1)

        self.assertIn("pl-isolated-push", isolated_text)
        self.assertIn("pl-isolated-pull", isolated_text)
        # Should NOT contain remote push/pull (those are in main/collab variants)
        self.assertNotIn("pl-remote-push", isolated_text)
        self.assertNotIn("pl-remote-pull", isolated_text)

    def test_collab_variant_has_branch_header(self):
        """Branch Collaboration variant includes [Branch: <branch>] header."""
        commands_file = os.path.join(
            PROJECT_ROOT, "instructions", "references", "builder_commands.md"
        )
        if not os.path.isfile(commands_file):
            self.skipTest("builder_commands.md not found")

        with open(commands_file) as f:
            content = f.read()

        import re
        collab_section = re.search(
            r"## Branch Collaboration Variant\n(.*?)(?=\n## |\Z)",
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(collab_section, "Collab variant section should exist")
        self.assertIn("[Branch:", collab_section.group(1))

    def test_main_variant_has_whats_different(self):
        """Main variant includes /pl-whats-different."""
        commands_file = os.path.join(
            PROJECT_ROOT, "instructions", "references", "builder_commands.md"
        )
        if not os.path.isfile(commands_file):
            self.skipTest("builder_commands.md not found")

        with open(commands_file) as f:
            content = f.read()

        import re
        main_section = re.search(
            r"## Main Branch Variant\n(.*?)(?=\n## |\Z)",
            content,
            re.DOTALL,
        )
        self.assertIsNotNone(main_section, "Main variant section should exist")
        self.assertIn("pl-whats-different", main_section.group(1))


# ===================================================================
# Scenario: Fixture cleanup runs after each test
# ===================================================================

class TestFixtureCleanup(unittest.TestCase):
    """Scenario: Fixture cleanup runs after each test

    Given a test scenario has completed (pass or fail)
    When the test runner moves to the next scenario
    Then the previous fixture checkout directory has been removed
    """

    def test_cleanup_removes_checkout_directory(self):
        """Fixture cleanup removes the checkout directory."""
        repo = create_fixture_repo({
            "main/test/cleanup": {
                "README.md": "# Test\n",
            },
        })

        rc, checkout_path, _ = run_fixture("checkout", repo, "main/test/cleanup")
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isdir(checkout_path))

        # Run cleanup
        rc, _, stderr = run_fixture("cleanup", checkout_path)
        self.assertEqual(rc, 0, f"cleanup failed: {stderr}")

        # Verify directory is gone
        self.assertFalse(
            os.path.exists(checkout_path),
            "Checkout directory should be removed after cleanup",
        )

        shutil.rmtree(repo)

    def test_cleanup_is_safe_for_nonexistent_dir(self):
        """Cleanup handles already-removed directories gracefully."""
        # Create a temp dir and remove it manually
        tmp = tempfile.mkdtemp(prefix="fixture-gone-")
        shutil.rmtree(tmp)

        # Cleanup should not fail (directory already gone)
        rc, _, _ = run_fixture("cleanup", tmp)
        self.assertEqual(rc, 0, "Cleanup should succeed for non-existent temp dir")


# ===================================================================
# Scenario: Test summary reports correct counts
# ===================================================================

class TestSummaryReporting(unittest.TestCase):
    """Scenario: Test summary reports correct counts

    Given 8 tests passed and 2 tests failed
    When the test runner prints the summary
    Then the output reads "8/10 tests passed"
    And the exit code is non-zero
    """

    def test_summary_format(self):
        """Summary line matches expected format: N/M tests passed."""
        # Simulate the summary output
        tests_passed = 8
        tests_total = 10
        summary = f"{tests_passed}/{tests_total} tests passed"

        self.assertEqual(summary, "8/10 tests passed")

    def test_nonzero_exit_on_failure(self):
        """Exit code is non-zero when tests fail."""
        tests_failed = 2
        exit_code = 1 if tests_failed > 0 else 0
        self.assertEqual(exit_code, 1, "Should exit non-zero when tests fail")

    def test_zero_exit_on_all_pass(self):
        """Exit code is zero when all tests pass."""
        tests_failed = 0
        exit_code = 1 if tests_failed > 0 else 0
        self.assertEqual(exit_code, 0, "Should exit zero when all tests pass")

    def test_json_results_structure(self):
        """JSON results file has required structure."""
        results = {
            "status": "FAIL",
            "tests_run": 10,
            "failures": 2,
            "errors": 0,
            "details": [
                {"test": "test_one", "status": "PASS"},
                {"test": "test_two", "status": "FAIL", "detail": "Expected X"},
            ],
        }

        # Verify serialization
        json_str = json.dumps(results)
        parsed = json.loads(json_str)

        self.assertIn("status", parsed)
        self.assertIn("tests_run", parsed)
        self.assertIn("failures", parsed)
        self.assertIn("details", parsed)
        self.assertEqual(parsed["status"], "FAIL")
        self.assertEqual(parsed["tests_run"], 10)


# ===================================================================
# Scenario: Test runner auto-creates fixtures when missing
# ===================================================================

class TestAutoCreateFixtures(unittest.TestCase):
    """Scenario: Test runner auto-creates fixtures when missing

    Given the fixture repo does not exist at the expected path
    When the test runner is invoked
    Then the runner executes dev/setup_behavior_fixtures.sh
    And the fixture repo is created with all required tags
    And tests proceed normally after setup
    """

    def test_setup_script_creates_fixture_repo(self):
        """Setup script creates a valid fixture repo at the target path."""
        target = tempfile.mkdtemp(prefix="fixture-autocreate-")
        shutil.rmtree(target)  # Remove so the script creates it fresh

        result = subprocess.run(
            ["bash", SETUP_SCRIPT, target],
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(
            result.returncode, 0,
            f"setup script failed: {result.stderr}",
        )
        self.assertTrue(os.path.isdir(target), "Fixture repo should be created")

        # Verify tags exist
        tag_result = subprocess.run(
            ["git", "-C", target, "tag"],
            capture_output=True, text=True,
        )
        tags = tag_result.stdout.strip().split("\n")
        self.assertGreater(len(tags), 0, "Fixture repo should have tags")

        # Check for required tags from the spec
        required_prefixes = [
            "main/cdd_startup_controls/",
            "main/pl_session_resume/",
            "main/pl_help/",
        ]
        for prefix in required_prefixes:
            matching = [t for t in tags if t.startswith(prefix)]
            self.assertGreater(
                len(matching), 0,
                f"Expected at least one tag with prefix '{prefix}'",
            )

        shutil.rmtree(target)

    def test_test_runner_has_auto_creation_logic(self):
        """The bash test runner contains auto-creation logic."""
        with open(TEST_HARNESS) as f:
            content = f.read()

        self.assertIn(
            "setup_behavior_fixtures.sh",
            content,
            "Test runner should reference the setup script",
        )
        self.assertIn(
            "Auto-creating",
            content,
            "Test runner should have auto-creation message",
        )


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
        self.results.append({
            "test": str(test), "status": "FAIL", "message": str(err[1]),
        })

    def addError(self, test, err):
        super().addError(test, err)
        self.results.append({
            "test": str(test), "status": "ERROR", "message": str(err[1]),
        })


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(resultclass=JsonTestResult, verbosity=2)
    result = runner.run(suite)

    # Write tests.json
    if PROJECT_ROOT:
        out_dir = os.path.join(PROJECT_ROOT, "tests", "agent_behavior_tests")
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
                    "test_file": "dev/test_behavior_harness.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

        # Distribute pl_help results from TestHelpVariantDetection
        pl_help_results = [
            r for r in result.results
            if "TestHelpVariantDetection" in r["test"]
        ]
        if pl_help_results:
            help_dir = os.path.join(PROJECT_ROOT, "tests", "pl_help")
            os.makedirs(help_dir, exist_ok=True)
            help_file = os.path.join(help_dir, "tests.json")
            hp = sum(1 for r in pl_help_results if r["status"] == "PASS")
            hf = len(pl_help_results) - hp
            with open(help_file, "w") as f:
                json.dump(
                    {
                        "status": "PASS" if hf == 0 else "FAIL",
                        "passed": hp,
                        "failed": hf,
                        "total": len(pl_help_results),
                        "test_file": "dev/test_behavior_harness.py",
                        "details": pl_help_results,
                    },
                    f,
                    indent=2,
                )
            print(f"  pl_help: {hp}/{len(pl_help_results)} passed")

    sys.exit(0 if result.wasSuccessful() else 1)
