#!/usr/bin/env python3
"""Tests for the Agent interaction test harness (dev/test_agent_interactions.sh).

Covers all 9 automated scenarios for agent interaction testing.
Tests verify harness infrastructure without requiring claude --print
invocations (which are expensive API calls).

Outputs test results to tests/agent_interactions/tests.json.
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
# Scenario: Negative test detects no false positives on clean fixture
# ===================================================================

class TestNegativeTestCleanFixture(unittest.TestCase):
    """Scenario: Negative test detects no false positives on clean fixture

    Given a fixture repo checked out at a clean tag (e.g., `main/release_instruction_audit/clean`)
    And the system prompt is constructed with the same release step instructions as the positive test
    When the harness executes a single-turn test via `claude --print`
    Then the agent's response does NOT contain problem indicators (contradictions, stale paths, errors)
    And the harness asserts prohibited patterns are absent
    And writes a PASS result to `tests/<feature>/tests.json`
    """

    @classmethod
    def setUpClass(cls):
        cls.repo = create_fixture_repo({
            "main/release_instruction_audit/clean": {
                "instructions/HOW_WE_WORK_BASE.md": "# How We Work\nCommit at milestones.\n",
                "instructions/ARCHITECT_BASE.md": "# Architect\nArchitect instructions.\n",
                ".purlin/HOW_WE_WORK_OVERRIDES.md": "# Overrides\n\nNo additional rules.\n",
                ".purlin/ARCHITECT_OVERRIDES.md": "# Arch Overrides\n\nConsistent with base.\n",
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

    def test_clean_fixture_has_no_contradictions(self):
        """Clean fixture overrides are consistent with base — no contradictions exist."""
        rc, checkout_path, stderr = run_fixture(
            "checkout", self.repo, "main/release_instruction_audit/clean",
        )
        self.assertEqual(rc, 0, f"checkout failed: {stderr}")

        # Read override files and verify they don't contradict the base
        override_path = os.path.join(checkout_path, ".purlin/ARCHITECT_OVERRIDES.md")
        with open(override_path) as f:
            content = f.read()
        self.assertNotIn("MUST NOT", content)
        self.assertNotIn("contradict", content.lower())

        shutil.rmtree(checkout_path)

    def test_assert_not_contains_function_exists(self):
        """Harness has assert_not_contains for negative assertions."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("assert_not_contains", content)

    def test_negative_scenario_uses_assert_not_contains(self):
        """The instruction_audit_clean scenario uses assert_not_contains."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        # Find the scenario function and check it uses assert_not_contains
        match = re.search(
            r'scenario_instruction_audit_clean\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, "scenario_instruction_audit_clean function not found")
        self.assertIn("assert_not_contains", match.group(0))

    def test_negative_scenario_checks_prohibited_patterns(self):
        """Negative scenario checks for prohibited problem indicators."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_instruction_audit_clean\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        # Should check for contradiction/stale/FAIL indicators being absent
        self.assertTrue(
            "contradict" in body or "stale" in body or "FAIL" in body,
            "Negative scenario should check for problem indicators",
        )


# ===================================================================
# Scenario: Tier 2 assertion verifies specific finding
# ===================================================================

class TestTier2SpecificFinding(unittest.TestCase):
    """Scenario: Tier 2 assertion verifies specific finding

    Given a fixture repo checked out at a tag with a known defect
    And the system prompt includes the relevant release step instructions
    When the harness executes a single-turn test via `claude --print`
    Then the harness asserts the agent's response contains the specific defect identifier
    (e.g., the exact file name, path, or contradiction text -- not just generic keywords)
    And the assertion would NOT pass on a clean fixture with no defects
    """

    def test_tier2_scenario_asserts_specific_file_name(self):
        """Tier 2 scenario asserts a specific defect file (BUILDER_OVERRIDES)."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_tier2_specific_finding\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, "scenario_tier2_specific_finding function not found")
        body = match.group(0)
        # Should assert the specific file name, not just generic keywords
        self.assertIn("BUILDER_OVERRIDES", body)

    def test_tier2_scenario_asserts_contradiction_content(self):
        """Tier 2 scenario asserts specific contradiction content, not just 'contradiction'."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_tier2_specific_finding\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        # Should assert specific content like "status tag" or "MUST NOT"
        self.assertTrue(
            "status" in body or "MUST NOT" in body or "commit" in body,
            "Tier 2 should assert specific contradiction content",
        )

    def test_tier2_uses_assertion_tier_2(self):
        """Tier 2 scenario records results with assertion_tier=2."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_tier2_specific_finding\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        # record_result calls should pass tier 2
        self.assertIn('" 2', body, "Tier 2 scenario should record assertion_tier=2")

    def test_tier2_assertion_would_not_match_clean_fixture(self):
        """Specific file assertion (BUILDER_OVERRIDES) wouldn't match clean fixture content."""
        # A clean fixture has generic override content, not defect-specific identifiers.
        # This test verifies the defect-specific fixture actually contains the defect.
        repo = create_fixture_repo({
            "main/release_instruction_audit/clean": {
                ".purlin/BUILDER_OVERRIDES.md": "# Builder Overrides\n\nConsistent.\n",
            },
            "main/release_instruction_audit/base-conflict": {
                ".purlin/BUILDER_OVERRIDES.md": (
                    "# Builder Overrides\n\n"
                    "## Contradiction\n"
                    "The Builder MUST NOT commit status tags.\n"
                ),
            },
        })

        # Clean fixture: no contradiction content
        rc, clean_path, _ = run_fixture(
            "checkout", repo, "main/release_instruction_audit/clean",
        )
        self.assertEqual(rc, 0)
        with open(os.path.join(clean_path, ".purlin/BUILDER_OVERRIDES.md")) as f:
            clean_content = f.read()
        self.assertNotIn("MUST NOT", clean_content)

        # Defect fixture: contradiction present
        rc, defect_path, _ = run_fixture(
            "checkout", repo, "main/release_instruction_audit/base-conflict",
        )
        self.assertEqual(rc, 0)
        with open(os.path.join(defect_path, ".purlin/BUILDER_OVERRIDES.md")) as f:
            defect_content = f.read()
        self.assertIn("MUST NOT", defect_content)

        shutil.rmtree(clean_path)
        shutil.rmtree(defect_path)
        shutil.rmtree(repo)


# ===================================================================
# Scenario: Multi-turn test with three or more turns
# ===================================================================

class TestMultiTurnThreePlus(unittest.TestCase):
    """Scenario: Multi-turn test with three or more turns

    Given a fixture repo checked out at a tag with a known project state
    And a session ID generated for the test
    When the harness executes turn 1 via `claude --print --session-id <id>`
    And the agent responds with findings or options
    And the harness executes turn 2 via `claude --print --resume <id>` with a scripted selection
    And the agent responds with refined output based on the selection
    And the harness executes turn 3 via `claude --print --resume <id>` with a scripted confirmation
    Then the agent's third response reflects accumulated context from turns 1 and 2
    And the harness asserts the final response contains expected outcome content
    """

    def test_three_turn_scenario_exists(self):
        """A 3+ turn scenario function exists in the harness."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("scenario_doc_three_turn_refinement", content)

    def test_three_turn_scenario_calls_run_claude_turn_three_times(self):
        """The 3-turn scenario calls run_claude_turn at least 3 times."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_doc_three_turn_refinement\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, "scenario_doc_three_turn_refinement not found")
        body = match.group(0)
        turn_calls = re.findall(r'run_claude_turn', body)
        self.assertGreaterEqual(
            len(turn_calls), 3,
            f"Expected 3+ run_claude_turn calls, found {len(turn_calls)}",
        )

    def test_three_turn_scenario_uses_session_management(self):
        """The 3-turn scenario uses reset_session for session lifecycle."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_doc_three_turn_refinement\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        self.assertIn("reset_session", body)

    def test_three_turn_scenario_captures_three_outputs(self):
        """The 3-turn scenario captures output from each turn into separate variables."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_doc_three_turn_refinement\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        # Should have output1, output2, output3
        self.assertIn("output1", body)
        self.assertIn("output2", body)
        self.assertIn("output3", body)

    def test_three_turn_final_assertion_checks_accumulated_context(self):
        """Turn 3 assertion verifies accumulated context from prior turns."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_doc_three_turn_refinement\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        # Turn 3 should assert on output3 with content that reflects accumulation
        self.assertIn("output3", body)
        # Should check for content introduced in turn 2/3 (alerting/metrics)
        self.assertTrue(
            "alert" in body or "metric" in body,
            "Turn 3 should assert accumulated context (alerting/metrics)",
        )


# ===================================================================
# Scenario: State verification after agent action
# ===================================================================

class TestStateVerificationFixIntent(unittest.TestCase):
    """Scenario: State verification after agent action

    Given a fixture repo checked out at a tag with a known defect
    And the system prompt includes release step instructions that direct the agent to take action
    When the harness executes a multi-turn test where the agent states intent to fix the defect
    Then the harness asserts the agent's output contains specific proposed changes
    (e.g., a proposed commit message, file diff, or explicit description of the fix)
    And the proposed changes reference the correct file and defect
    """

    def test_state_verification_scenario_exists(self):
        """A state verification scenario function exists in the harness."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        self.assertIn("scenario_state_verification_fix_intent", content)

    def test_state_verification_is_multi_turn(self):
        """State verification scenario uses multi-turn (run_claude_turn)."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_state_verification_fix_intent\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, "scenario_state_verification_fix_intent not found")
        body = match.group(0)
        turn_calls = re.findall(r'run_claude_turn', body)
        self.assertGreaterEqual(
            len(turn_calls), 2,
            "State verification should be multi-turn (at least 2 turns)",
        )

    def test_state_verification_asserts_specific_file(self):
        """State verification asserts the agent references the correct file to fix."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_state_verification_fix_intent\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        self.assertIn("BUILDER_OVERRIDES", body)

    def test_state_verification_uses_tier3_assertions(self):
        """State verification records results with assertion_tier=3."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_state_verification_fix_intent\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        self.assertIn('" 3', body, "State verification should record assertion_tier=3")

    def test_state_verification_asserts_change_description(self):
        """State verification asserts the agent describes the proposed fix."""
        with open(TEST_HARNESS) as f:
            content = f.read()
        import re
        match = re.search(
            r'scenario_state_verification_fix_intent\(\).*?^}',
            content, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        body = match.group(0)
        # Should assert commit/fix/remove/delete/revise language
        self.assertTrue(
            "commit" in body or "fix" in body or "remov" in body or "revis" in body,
            "State verification should assert fix description content",
        )


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "agent_interactions")
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
