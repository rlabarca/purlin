#!/usr/bin/env python3
"""Tests for the /pl-release-run skill command file.

Covers all 4 unit test scenarios from features/pl_release_run.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-release-run.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonArchitect(unittest.TestCase):
    """Scenario: Role gate rejects non-Architect invocation

    Given a Builder agent session
    When the agent invokes /pl-release-run
    Then the command responds with a redirect message

    Structural test: the command file declares Architect ownership and
    contains a redirect message for non-Architect agents.
    """

    def test_first_line_declares_architect_owner(self):
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Architect", first_line)
        self.assertIn("command owner", first_line.lower())

    def test_redirect_message_present(self):
        """Non-Architect agents receive a redirect message."""
        content = read_command_file()
        self.assertIn("not operating as the Purlin Architect", content)

    def test_redirect_mentions_architect_role(self):
        """The redirect message tells the user to ask the Architect."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)ask your architect agent to run /pl-release-run",
        )


class TestPartialNameMatchSelectsStep(unittest.TestCase):
    """Scenario: Partial name match selects correct step

    Given a step with friendly_name "Push to Remote Repository"
    When /pl-release-run is invoked with argument "push"
    Then that step is selected for execution

    Structural test: the command file describes case-insensitive partial
    matching against friendly_name values.
    """

    def test_friendly_name_matching_described(self):
        content = read_command_file()
        self.assertIn("friendly_name", content)

    def test_case_insensitive_matching(self):
        content = read_command_file()
        self.assertIn("case-insensitive", content.lower())

    def test_partial_match_supported(self):
        content = read_command_file()
        self.assertIn("partial match", content.lower())

    def test_exactly_one_match_proceeds(self):
        """When exactly one step matches, execution proceeds."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)exactly one match.*proceed",
        )


class TestMultipleMatchesPromptsChoice(unittest.TestCase):
    """Scenario: Multiple matches prompts user choice

    Given steps "Push to Remote" and "Push to Wiki" both exist
    When /pl-release-run is invoked with argument "push"
    Then both matches are listed and user is asked to choose

    Structural test: the command file instructs listing multiple matches
    and asking the user to choose.
    """

    def test_multiple_matches_handled(self):
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)multiple match",
        )

    def test_lists_matches_for_user(self):
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)list.*match",
        )

    def test_asks_user_to_choose(self):
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(ask.*choose|choose.*one)",
        )


class TestDisabledStepShowsWarning(unittest.TestCase):
    """Scenario: Disabled step shows warning

    Given step "sync_docs" has enabled: false
    When /pl-release-run selects that step
    Then a warning about disabled status is shown
    And explicit confirmation is required before execution

    Structural test: the command file contains the disabled step warning
    text and requires confirmation before proceeding.
    """

    def test_enabled_false_check(self):
        content = read_command_file()
        self.assertIn("enabled: false", content)

    def test_disabled_warning_text(self):
        content = read_command_file()
        self.assertIn(
            "This step is currently disabled in the release checklist",
            content,
        )

    def test_confirmation_required(self):
        """Explicit confirmation is required before executing a disabled step."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(explicit confirmation|confirm.*before.*continu)",
        )

    def test_warning_appears_before_execute(self):
        """The disabled warning appears before the execute step."""
        content = read_command_file()
        warn_pos = content.find("Warn if disabled")
        exec_pos = content.find("Execute the step")
        self.assertGreater(warn_pos, -1, "Warn if disabled section must exist")
        self.assertGreater(exec_pos, -1, "Execute the step section must exist")
        self.assertLess(warn_pos, exec_pos,
                        "Disabled warning must come before execution")


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_release_run")
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
                    "test_file": "tools/test_support/test_pl_release_run.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
