#!/usr/bin/env python3
"""Tests for the /pl-regression-author skill command file.

Covers all 4 unit test scenarios from features/pl_regression_author.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-regression-author.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonQAInvocation(unittest.TestCase):
    """Scenario: Role gate rejects non-QA invocation

    Given a Builder agent session
    When the agent invokes /pl-regression-author
    Then the command responds with a redirect message

    Structural test: the command file's first line declares QA as
    the command owner, which means non-QA agents will be redirected.
    """

    def test_first_line_declares_qa_owner(self):
        """First line must contain the QA command owner declaration."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("command owner: QA", first_line,
                       "First line must declare QA as command owner")

    def test_redirect_message_for_non_qa(self):
        """Command file must include a redirect message for non-QA agents."""
        content = read_command_file()
        self.assertIn("not operating as the Purlin QA", content,
                       "Must include redirect guidance for non-QA agents")

    def test_redirect_mentions_qa_role(self):
        """Redirect message must tell non-QA agents to ask a QA agent."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)ask.*qa.*run.*pl-regression-author",
            "Redirect must instruct non-QA to ask QA to run /pl-regression-author",
        )


class TestMissingHarnessRunnerBlocksAuthoring(unittest.TestCase):
    """Scenario: Missing harness runner blocks authoring

    Given harness_runner.py does not exist
    When /pl-regression-author is invoked
    Then a handoff message is printed directing to launch Builder
    And no scenario files are created

    Structural test: the command file checks for the harness runner
    and includes a handoff message when it is missing.
    """

    def test_harness_runner_check_present(self):
        """Command file must check for harness_runner.py existence."""
        content = read_command_file()
        self.assertIn("harness_runner.py", content,
                       "Must check for harness_runner.py")

    def test_handoff_message_directs_to_builder(self):
        """When harness runner is missing, must direct the user to launch Builder."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)launch builder",
            "Handoff message must direct user to launch Builder",
        )

    def test_stop_instruction_on_missing_harness(self):
        """Command file must instruct to STOP when harness runner is missing."""
        content = read_command_file()
        # The prerequisite section should contain a STOP instruction
        harness_pos = content.find("harness_runner.py")
        self.assertGreater(harness_pos, -1)
        # Find STOP after the harness runner check
        after_harness = content[harness_pos:]
        self.assertRegex(
            after_harness,
            r"(?i)stop",
            "Must instruct to STOP when harness runner is missing",
        )

    def test_harness_check_before_authoring_steps(self):
        """Harness runner check must appear before authoring steps."""
        content = read_command_file()
        harness_pos = content.find("harness_runner.py")
        # Step 1 (Discover) or Step 3 (Author) should come after the check
        step1_pos = content.find("Step 1")
        self.assertGreater(step1_pos, harness_pos,
                           "Harness runner check must precede authoring steps")


class TestFeatureDiscoveryIdentifiesEligibleFeatures(unittest.TestCase):
    """Scenario: Feature discovery identifies eligible features

    Given feature_a has Builder DONE status and Regression Guidance section
    And no tests/qa/scenarios/feature_a.json exists
    When /pl-regression-author discovers features
    Then feature_a is listed as needing scenario authoring

    Structural test: the command file references status.sh --role qa
    and describes the eligibility criteria for feature discovery.
    """

    def test_status_sh_role_qa_invoked(self):
        """Command file must invoke status.sh --role qa for discovery."""
        content = read_command_file()
        self.assertIn("status.sh --role qa", content,
                       "Must invoke status.sh --role qa for feature discovery")

    def test_regression_section_criteria(self):
        """Command file must check for Regression Testing or Regression Guidance sections."""
        content = read_command_file()
        self.assertIn("Regression Testing", content,
                       "Must reference Regression Testing section as eligibility criterion")
        self.assertIn("Regression Guidance", content,
                       "Must reference Regression Guidance section as eligibility criterion")

    def test_builder_done_status_criteria(self):
        """Command file must require Builder DONE status for eligibility."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)builder.*done|done.*status",
            "Must require Builder DONE status for feature eligibility",
        )

    def test_scenarios_dir_path_referenced(self):
        """Command file must reference the scenarios output path."""
        content = read_command_file()
        self.assertIn("tests/qa/scenarios/", content,
                       "Must reference tests/qa/scenarios/ output path")


class TestScenarioJSONFollowsRegressionSchema(unittest.TestCase):
    """Scenario: Scenario JSON follows regression schema

    Given feature_a is selected for authoring
    When the scenario JSON is composed
    Then it includes harness_type, scenario entries with assertions
    And it is written to tests/qa/scenarios/feature_a.json

    Structural test: the command file describes composing scenario JSON
    with the required schema fields and writing to the correct path.
    """

    def test_harness_type_field_described(self):
        """Command file must describe the harness_type field."""
        content = read_command_file()
        self.assertIn("harness_type", content,
                       "Must describe the harness_type field in scenario JSON")

    def test_harness_type_values_listed(self):
        """Command file must list the valid harness_type values."""
        content = read_command_file()
        self.assertIn("agent_behavior", content,
                       "Must list agent_behavior as a harness_type value")
        self.assertIn("web_test", content,
                       "Must list web_test as a harness_type value")
        self.assertIn("custom_script", content,
                       "Must list custom_script as a harness_type value")

    def test_scenario_json_write_path(self):
        """Command file must describe writing to tests/qa/scenarios/<feature_name>.json."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"tests/qa/scenarios/.*\.json",
            "Must describe writing scenario JSON to tests/qa/scenarios/<feature_name>.json",
        )

    def test_commit_per_feature(self):
        """Command file must describe committing per feature after writing."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)commit.*qa\(|git commit",
            "Must describe committing after writing each scenario file",
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_regression_author")
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
                    "test_file": "tools/test_support/test_pl_regression_author.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
