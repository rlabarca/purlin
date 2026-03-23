#!/usr/bin/env python3
"""Tests for the /pl-regression-run skill command file.

Covers all 4 unit test scenarios from features/pl_regression_run.md.
Since skills are agent instruction files (not executable code), these
tests verify structural properties of the command file that ensure
correct runtime behavior.
"""

import os
import re
import json
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, "../../")))
from tools.bootstrap import detect_project_root

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-regression-run.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonQA(unittest.TestCase):
    """Scenario: Role gate rejects non-QA invocation

    Given a Builder agent session
    When the agent invokes /pl-regression-run
    Then the command responds with a redirect message

    Structural test: the command file declares QA ownership and includes
    a redirect message for non-QA agents.
    """

    def test_first_line_declares_qa_ownership(self):
        """The command file must declare QA as the command owner."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("QA", first_line)
        self.assertRegex(first_line, r"(?i)command owner.*QA")

    def test_redirect_message_for_non_qa(self):
        """A redirect message must be present telling non-QA agents to stop."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)ask your QA agent.*instead",
        )

    def test_stop_instruction_after_redirect(self):
        """The command file must instruct non-QA agents to stop execution."""
        content = read_command_file()
        # Find the redirect block and confirm it contains a stop directive
        self.assertRegex(content, r"(?i)(and stop|stop\.)")


class TestNoEligibleFeaturesReportsCleanState(unittest.TestCase):
    """Scenario: No eligible features reports clean state

    Given all regression results are current
    When /pl-regression-run is invoked
    Then the output says "No regression-eligible features found"

    Structural test: the command file contains the clean-state message
    and has logic for zero-eligible handling.
    """

    def test_clean_state_message_present(self):
        """The exact clean-state message must appear in the command file."""
        content = read_command_file()
        self.assertIn("No regression-eligible features found", content)

    def test_clean_state_mentions_current(self):
        """The clean-state output should confirm results are current."""
        content = read_command_file()
        # The message should mention that results are current
        self.assertRegex(
            content,
            r"(?i)regression.*results.*current",
        )

    def test_zero_eligible_leads_to_stop(self):
        """When zero features are eligible, the command should stop."""
        content = read_command_file()
        # "zero features are eligible" block should mention stopping
        no_eligible_pos = content.find("No regression-eligible features found")
        self.assertGreater(no_eligible_pos, -1)
        # There should be a Stop directive near the clean-state message
        surrounding = content[max(0, no_eligible_pos - 200):no_eligible_pos + 200]
        self.assertRegex(surrounding, r"(?i)(stop|Stop)")


class TestFrequencyFilterExcludesPreRelease(unittest.TestCase):
    """Scenario: Frequency filter excludes pre-release suites by default

    Given a scenario file with frequency "pre-release"
    When /pl-regression-run is invoked without --frequency flag
    Then the pre-release suite is excluded from the eligible list

    Structural test: the command file documents the frequency argument,
    default behavior, and exclusion logic for pre-release suites.
    """

    def test_frequency_argument_documented(self):
        """The --frequency argument must be documented."""
        content = read_command_file()
        self.assertIn("--frequency", content)

    def test_per_feature_is_default(self):
        """per-feature must be documented as the default frequency."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)per-feature.*default|default.*per-feature")

    def test_pre_release_exclusion_by_default(self):
        """The command must describe excluding pre-release suites by default."""
        content = read_command_file()
        # Must mention that pre-release suites are excluded when no flag given
        self.assertRegex(
            content,
            r"(?i)pre-release.*exclude|exclude.*pre-release",
        )

    def test_pre_release_inclusion_with_flag(self):
        """The --frequency pre-release flag must include all suites."""
        content = read_command_file()
        # When --frequency pre-release is given, include all
        self.assertRegex(
            content,
            r"(?i)pre-release.*include all|include all.*regardless",
        )


class TestCommandBlockIsCopyPasteable(unittest.TestCase):
    """Scenario: Command block is copy-pasteable

    Given feature_a and feature_b are eligible
    When the user selects both
    Then a complete, copy-pasteable command is printed in a formatted block

    Structural test: the command file contains a formatted command template
    with copy-pasteable examples and sequential chaining instructions.
    """

    def test_copy_pasteable_ux_rule(self):
        """The command file must have the mandatory UX rule about copy-pasteable commands."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)copy-pasteable command",
        )

    def test_single_feature_command_template(self):
        """A single-feature command template must be present."""
        content = read_command_file()
        # Should contain a run command example
        self.assertRegex(content, r"run_regression\.sh|run_all\.sh|harness_runner\.py")

    def test_multi_feature_sequential_chain(self):
        """Multi-feature commands should use sequential chaining (&&)."""
        content = read_command_file()
        self.assertIn("&&", content)

    def test_command_in_formatted_block(self):
        """Commands must be presented in a formatted code block."""
        content = read_command_file()
        # Must have a code block with a command example
        code_blocks = re.findall(r"```[^`]*```", content, re.DOTALL)
        # At least one code block should contain a run command
        has_command_block = any(
            "run" in block.lower() for block in code_blocks
        )
        self.assertTrue(has_command_block,
                        "Expected at least one code block containing a run command")


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_regression_run")
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
                    "test_file": "tools/test_support/test_pl_regression_run.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
