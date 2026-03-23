#!/usr/bin/env python3
"""Tests for the /pl-regression-evaluate skill command file.

Covers all 4 unit test scenarios from features/pl_regression_evaluate.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-regression-evaluate.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonQA(unittest.TestCase):
    """Scenario: Role gate rejects non-QA invocation

    Given a Builder agent session
    When the agent invokes /pl-regression-evaluate
    Then the command responds with a redirect message

    Structural test: the command file declares QA ownership and includes
    a redirect message for non-QA agents.
    """

    def test_first_line_declares_qa_ownership(self):
        """The command file must declare QA as the command owner."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("QA", first_line)

    def test_command_owner_pattern_present(self):
        """The file uses the standard 'command owner' role gate pattern."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)command owner.*QA")

    def test_redirect_message_for_non_qa(self):
        """Non-QA agents receive a redirect message mentioning QA."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(ask your QA|this is a QA command)",
        )

    def test_redirect_references_command_name(self):
        """The redirect message references /pl-regression-evaluate."""
        content = read_command_file()
        self.assertIn("/pl-regression-evaluate", content)


class TestNoUnprocessedResultsReportsCleanState(unittest.TestCase):
    """Scenario: No unprocessed results reports clean state

    Given no recently updated tests.json files exist
    When /pl-regression-evaluate is invoked
    Then the output says "No unprocessed regression results found"

    Structural test: the command file contains the exact clean-state message
    and describes the condition for triggering it.
    """

    def test_clean_state_message_present(self):
        """The exact clean-state message must appear in the command file."""
        content = read_command_file()
        self.assertIn("No unprocessed regression results found", content)

    def test_checks_for_recently_updated_results(self):
        """The command file describes checking for recently updated results."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)recently updated")

    def test_reads_tests_json(self):
        """The command file references tests.json as the result source."""
        content = read_command_file()
        self.assertIn("tests.json", content)


class TestFailuresCreateBugDiscoveries(unittest.TestCase):
    """Scenario: Failures create BUG discoveries

    Given feature_a has 2 failed scenarios in tests.json
    When /pl-regression-evaluate processes results
    Then 2 BUG discoveries are created in feature_a.discoveries.md

    Structural test: the command file describes creating [BUG] entries in
    discovery sidecar files with the required enriched fields.
    """

    def test_bug_discovery_tag_present(self):
        """The command file uses the [BUG] discovery tag."""
        content = read_command_file()
        self.assertIn("[BUG]", content)

    def test_discovery_sidecar_path_pattern(self):
        """The command file references the discovery sidecar file pattern."""
        content = read_command_file()
        self.assertIn(".discoveries.md", content)

    def test_enriched_field_scenario_ref(self):
        """The command file references the scenario_ref enriched field."""
        content = read_command_file()
        self.assertIn("scenario_ref", content)

    def test_enriched_field_expected_and_actual(self):
        """The command file references expected and actual_excerpt fields."""
        content = read_command_file()
        self.assertIn("expected", content)
        self.assertIn("actual_excerpt", content)


class TestShallowSuiteFlaggedAbove50PercentTier1(unittest.TestCase):
    """Scenario: Shallow suite flagged when more than 50 percent Tier 1

    Given a suite with 6 Tier 1 and 4 Tier 2 assertions
    When tier distribution is computed
    Then the suite is flagged as [SHALLOW]

    Structural test: the command file describes tier distribution computation,
    the 50% threshold, and the [SHALLOW] flag.
    """

    def test_shallow_flag_present(self):
        """The command file uses the [SHALLOW] flag."""
        content = read_command_file()
        self.assertIn("[SHALLOW]", content)

    def test_fifty_percent_threshold_documented(self):
        """The command file documents the 50% threshold for Tier 1."""
        content = read_command_file()
        self.assertRegex(content, r"50%")

    def test_tier_distribution_section_exists(self):
        """The command file has a tier distribution section."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)tier distribution")

    def test_assertion_tier_field_referenced(self):
        """The command file references the assertion_tier field."""
        content = read_command_file()
        self.assertIn("assertion_tier", content)


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_regression_evaluate")
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
                    "test_file": "tools/test_support/test_pl_regression_evaluate.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
