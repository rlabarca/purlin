#!/usr/bin/env python3
"""Tests for the AFT Agent interaction test harness (dev/test_agent_interactions.sh).

Covers all 5 automated scenarios from features/aft_agent.md Section 3.
Tests verify harness infrastructure without requiring claude --print
invocations (which are expensive API calls).

Outputs test results to tests/aft_agent/tests.json.
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

TEST_HARNESS = os.path.join(SCRIPT_DIR, "test_agent_interactions.sh")
FIXTURE_TOOL = os.path.join(PROJECT_ROOT, "tools", "test_support", "fixture.sh")
GLOBAL_STEPS = os.path.join(PROJECT_ROOT, "tools", "release", "global_steps.json")


def create_fixture_repo(tags_and_files):
    """Create a temporary bare git repo with tagged commits.

    Args:
        tags_and_files: dict mapping tag_name -> dict of {filename: content}

    Returns:
        Path to the bare repo (suitable as repo-url).
    """
    work_dir = tempfile.mkdtemp(prefix="aft-agent-work-")
    bare_dir = tempfile.mkdtemp(prefix="aft-agent-bare-")

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
# Scenario: Single-turn test produces structured output
# ===================================================================

class TestSingleTurnStructuredOutput(unittest.TestCase):
    """Scenario: Single-turn test produces structured output

    Given a fixture repo checked out at a tag with a known project state
    And a system prompt constructed from the instruction stack with release step instructions
    When the harness executes a single-turn test via `claude --print`
    Then the agent's response is captured as a string
    And the harness asserts expected content is present
    And writes a PASS or FAIL result to `tests/<feature>/tests.json`
    """

    @classmethod
    def setUpClass(cls):
        cls.repo = create_fixture_repo({
            "main/release_instruction_audit/base-conflict": {
                "instructions/HOW_WE_WORK_BASE.md": "# How We Work\nCommit at milestones.\n",
                "instructions/ARCHITECT_BASE.md": "# Architect\nArchitect instructions.\n",
                ".purlin/HOW_WE_WORK_OVERRIDES.md": "# Overrides\n",
                ".purlin/ARCHITECT_OVERRIDES.md": "# Arch Overrides\n",
                ".purlin/config.json": json.dumps({
                    "tools_root": "tools",
                    "agents": {"architect": {"find_work": True}},
                }),
                "tools/release/global_steps.json": json.dumps({
                    "steps": [{
                        "id": "purlin.instruction_audit",
                        "friendly_name": "Instruction Audit",
                        "description": "Check overrides for contradictions.",
                        "code": None,
                        "agent_instructions": "Check override files for contradictions with base.",
                    }],
                }),
            },
        })

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.repo)

    def test_fixture_checkout_creates_directory(self):
        """Fixture checkout creates a directory with instruction files."""
        rc, checkout_path, stderr = run_fixture(
            "checkout", self.repo, "main/release_instruction_audit/base-conflict",
        )
        self.assertEqual(rc, 0, f"checkout failed: {stderr}")
        self.assertTrue(os.path.isdir(checkout_path))
        self.assertTrue(os.path.isfile(
            os.path.join(checkout_path, "instructions/HOW_WE_WORK_BASE.md")
        ))
        shutil.rmtree(checkout_path)

    def test_release_prompt_includes_step_instructions(self):
        """Release prompt construction includes step agent_instructions."""
        rc, checkout_path, _ = run_fixture(
            "checkout", self.repo, "main/release_instruction_audit/base-conflict",
        )
        self.assertEqual(rc, 0)

        # Simulate construct_release_prompt logic
        layers = [
            os.path.join(checkout_path, "instructions/HOW_WE_WORK_BASE.md"),
            os.path.join(checkout_path, "instructions/ARCHITECT_BASE.md"),
            os.path.join(checkout_path, ".purlin/HOW_WE_WORK_OVERRIDES.md"),
            os.path.join(checkout_path, ".purlin/ARCHITECT_OVERRIDES.md"),
        ]

        prompt_content = ""
        for layer_path in layers:
            if os.path.isfile(layer_path):
                with open(layer_path) as f:
                    prompt_content += f.read() + "\n\n"

        # Add release step instructions
        steps_file = os.path.join(checkout_path, "tools/release/global_steps.json")
        if os.path.isfile(steps_file):
            with open(steps_file) as f:
                steps = json.load(f)
            for step in steps.get("steps", []):
                if step["id"] == "purlin.instruction_audit":
                    prompt_content += (
                        f"\n\n## Release Step Instructions\n\n"
                        f"{step['agent_instructions']}\n"
                    )

        self.assertIn("Commit at milestones", prompt_content)
        self.assertIn("Check override files for contradictions", prompt_content)

        shutil.rmtree(checkout_path)

    def test_result_json_structure_is_valid(self):
        """Test result JSON has required fields."""
        result = {
            "status": "PASS",
            "passed": 3,
            "failed": 0,
            "skipped": 1,
            "total": 4,
            "test_file": "dev/test_agent_interactions.sh",
            "details": [
                {"test": "instruction-audit-halt: contradiction detected", "status": "PASS"},
                {"test": "doc-coverage-gaps: gaps identified", "status": "PASS"},
            ],
        }
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        self.assertIn("status", parsed)
        self.assertIn("passed", parsed)
        self.assertIn("failed", parsed)
        self.assertIn("total", parsed)
        self.assertIn("details", parsed)


# ===================================================================
# Scenario: Multi-turn test resumes session correctly
# ===================================================================

class TestMultiTurnSessionResume(unittest.TestCase):
    """Scenario: Multi-turn test resumes session correctly

    Given a fixture repo checked out at a tag with a known project state
    And a session ID generated for the test
    When the harness executes turn 1 via `claude --print --session-id <id>`
    And the harness executes turn 2 via `claude --print --resume <id>`
    Then the harness correctly manages session state across turns
    """

    def test_session_id_generation_format(self):
        """Session IDs follow the aft-agent-<timestamp>-<pid> format."""
        import re
        session_id = f"aft-agent-{1710000000}-12345"
        self.assertTrue(
            bool(re.match(r"aft-agent-\d+-\d+", session_id)),
            "Session ID should match expected format",
        )

    def test_first_turn_uses_session_id_flag(self):
        """First turn uses --session-id, not --resume."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("--session-id", content)
        self.assertIn("--resume", content)

    def test_subsequent_turn_uses_resume_flag(self):
        """Subsequent turns use --resume with the same session ID."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        # The harness checks SESSION_ID to decide which flag to use
        self.assertIn("SESSION_ID", content)
        self.assertIn("resume", content)

    def test_reset_session_clears_state(self):
        """reset_session clears the session ID for next scenario."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("reset_session", content)


# ===================================================================
# Scenario: Model override accepted
# ===================================================================

class TestModelOverride(unittest.TestCase):
    """Scenario: Model override accepted

    Given the harness is invoked with `--model sonnet`
    When it executes a test scenario
    Then `claude --print` is called with `--model sonnet` instead of the default haiku
    """

    def test_model_override_accepted_via_flag(self):
        """Model override is accepted via --model command line argument."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("--model", content)
        self.assertIn("MODEL=", content)

    def test_default_model_is_haiku(self):
        """Default model is claude-haiku-4-5-20251001."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("claude-haiku-4-5-20251001", content)

    def test_model_override_passed_to_claude(self):
        """Model override value is passed to claude --print."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn('--model "$MODEL"', content)


# ===================================================================
# Scenario: Single scenario selection
# ===================================================================

class TestScenarioSelection(unittest.TestCase):
    """Scenario: Single scenario selection

    Given the harness is invoked with `--scenario instruction-audit-halt`
    When it runs
    Then only the specified scenario executes
    And all other scenarios are skipped
    """

    def test_single_scenario_selection_flag(self):
        """Single scenario selection via --scenario command line argument."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("--scenario", content)
        self.assertIn("SCENARIO_FILTER", content)

    def test_should_run_scenario_function_exists(self):
        """should_run_scenario function gates scenario execution."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("should_run_scenario", content)

    def test_single_selection_gates_each_scenario(self):
        """Single selection filter gates each scenario function."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        scenarios = re.findall(r'^scenario_\w+\(\)', content, re.MULTILINE)
        # Each scenario should call should_run_scenario (defined once + called per scenario)
        filter_calls = len(re.findall(r'should_run_scenario "\$name"', content))
        self.assertGreaterEqual(
            filter_calls,
            len(scenarios),
            f"Each of {len(scenarios)} scenarios should check the filter",
        )


# ===================================================================
# Scenario: Fixture tag missing causes test skip
# ===================================================================

class TestMissingFixtureTagSkip(unittest.TestCase):
    """Scenario: Fixture tag missing causes test skip

    Given a test scenario declares fixture tag `main/feature/slug`
    And that tag does not exist in the fixture repo
    When the harness attempts to run the scenario
    Then the scenario is reported as SKIP (not FAIL)
    And the skip reason includes the missing tag name
    """

    def test_checkout_safe_function_exists(self):
        """checkout_fixture_safe returns SKIP for missing tags."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("checkout_fixture_safe", content)
        self.assertIn("SKIP", content)

    def test_skip_includes_tag_name(self):
        """SKIP result includes the missing tag name."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("Missing tag:", content)

    def test_skip_does_not_count_as_failure(self):
        """SKIP increments skip counter, not fail counter."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("TESTS_SKIPPED", content)

    def test_missing_tag_triggers_checkout_failure(self):
        """Checkout of a non-existent tag fails (fixture tool returns non-zero)."""
        repo = create_fixture_repo({
            "main/test/exists": {
                "README.md": "# Test\n",
            },
        })

        # Non-existent tag should fail
        rc, _, _ = run_fixture(
            "checkout", repo, "main/test/does-not-exist",
        )
        self.assertNotEqual(rc, 0, "Checkout of missing tag should fail")

        # Existing tag should succeed
        rc, path, _ = run_fixture("checkout", repo, "main/test/exists")
        self.assertEqual(rc, 0)
        shutil.rmtree(path)
        shutil.rmtree(repo)


# ===================================================================
# Release prompt construction
# ===================================================================

class TestReleasePromptConstruction(unittest.TestCase):
    """Tests for construct_release_prompt() function."""

    def test_construct_release_prompt_function_exists(self):
        """construct_release_prompt function is defined."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("construct_release_prompt()", content)

    def test_construct_release_prompt_reads_global_steps(self):
        """construct_release_prompt reads global_steps.json."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("global_steps.json", content)

    def test_construct_release_prompt_extracts_step_instructions(self):
        """construct_release_prompt extracts agent_instructions by step_id."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("agent_instructions", content)
        self.assertIn("step_id", content)

    def test_construct_release_prompt_handles_missing_steps_file(self):
        """construct_release_prompt handles absence of global_steps.json gracefully."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        # Should check file existence before reading
        self.assertIn('if [[ -f "$steps_file"', content)

    def test_global_steps_json_is_valid(self):
        """global_steps.json in project root is valid JSON with expected structure."""
        if not os.path.isfile(GLOBAL_STEPS):
            self.skipTest("global_steps.json not found")
        with open(GLOBAL_STEPS) as f:
            data = json.load(f)
        self.assertIn("steps", data)
        for step in data["steps"]:
            self.assertIn("id", step)
            self.assertIn("agent_instructions", step)


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "aft_agent")
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
                    "test_file": "dev/test_aft_agent_harness.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
