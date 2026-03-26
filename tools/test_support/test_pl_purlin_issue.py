#!/usr/bin/env python3
"""Tests for the /pl-purlin-issue skill command file.

Covers all 5 unit test scenarios from features/pl_purlin_issue.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-purlin-issue.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestSkillAvailableToAllRoles(unittest.TestCase):
    """Scenario: Skill is available to all roles

    Given any agent role (PM, Engineer, QA, or PM)
    When the user invokes /pl-purlin-issue
    Then the skill executes without a role authorization error

    Structural test: the command file's first line declares 'shared (all roles)',
    which means no role gate check will block execution.
    """

    def test_first_line_declares_shared_all_roles(self):
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("shared (all roles)", first_line.lower())

    def test_no_role_restriction_pattern(self):
        """No single-role ownership pattern like 'command owner: Engineer'."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertNotIn("command owner:", first_line.lower())


class TestDeploymentModeDetection(unittest.TestCase):
    """Scenario: Report includes deployment mode detection

    Given a consumer project with .purlin/.upstream_sha present
    When /pl-purlin-issue is invoked
    Then the report Deployment field shows 'consumer'
    And the report includes Consumer Project and Consumer HEAD fields

    Structural test: the command file contains logic for detecting
    .upstream_sha and producing consumer-mode fields.
    """

    def test_upstream_sha_detection_present(self):
        content = read_command_file()
        self.assertIn(".upstream_sha", content)

    def test_consumer_mode_documented(self):
        content = read_command_file()
        self.assertIn("consumer", content.lower())

    def test_consumer_project_field_present(self):
        content = read_command_file()
        self.assertIn("Consumer Project", content)

    def test_consumer_head_field_present(self):
        content = read_command_file()
        self.assertIn("Consumer HEAD", content)


class TestPurlinVersionInfo(unittest.TestCase):
    """Scenario: Report includes Purlin version info

    Given any Purlin deployment
    When /pl-purlin-issue is invoked
    Then the report includes Purlin SHA, Purlin Version, and Purlin Remote fields

    Structural test: the report template includes all three version fields.
    """

    def test_purlin_sha_field(self):
        content = read_command_file()
        self.assertIn("Purlin SHA", content)

    def test_purlin_version_field(self):
        content = read_command_file()
        self.assertIn("Purlin Version", content)

    def test_purlin_remote_field(self):
        content = read_command_file()
        self.assertIn("Purlin Remote", content)


class TestReportBoundedByCopyDividers(unittest.TestCase):
    """Scenario: Report is bounded by copy dividers

    Given any Purlin deployment
    When /pl-purlin-issue is invoked
    Then the output contains the opening and closing dividers
    And the report content between dividers is valid Markdown

    Structural test: the command file template includes both divider strings
    and the content between them is a Markdown table.
    """

    def test_opening_divider_present(self):
        content = read_command_file()
        self.assertIn("-------- PURLIN ISSUE REPORT (COPY THIS) ---------", content)

    def test_closing_divider_present(self):
        content = read_command_file()
        self.assertIn("-------- END PURLIN ISSUE REPORT ---------", content)

    def test_markdown_table_between_dividers(self):
        content = read_command_file()
        start = content.find("-------- PURLIN ISSUE REPORT (COPY THIS) ---------")
        end = content.find("-------- END PURLIN ISSUE REPORT ---------")
        self.assertGreater(start, -1)
        self.assertGreater(end, start)
        between = content[start:end]
        # Should contain a Markdown table with | Field | Value | pattern
        self.assertRegex(between, r"\|\s*Field\s*\|\s*Value\s*\|")


class TestPromptsForDescriptionWhenNoArguments(unittest.TestCase):
    """Scenario: Skill prompts for description when no arguments given

    Given no $ARGUMENTS are provided
    When /pl-purlin-issue is invoked
    Then the agent asks the user to describe the Purlin framework issue
    And the agent does not generate the report until a description is provided

    Structural test: the command file checks $ARGUMENTS and has a prompt
    step before report generation.
    """

    def test_arguments_check_present(self):
        content = read_command_file()
        self.assertIn("$ARGUMENTS", content)

    def test_prompts_user_for_description(self):
        content = read_command_file()
        # The command should ask the user for a description
        self.assertRegex(
            content,
            r"(?i)(ask|describe|what.*issue|issue.*describe)",
        )

    def test_description_step_before_report(self):
        """Description collection step appears before report composition."""
        content = read_command_file()
        desc_pos = content.find("$ARGUMENTS")
        report_pos = content.find("PURLIN ISSUE REPORT (COPY THIS)")
        self.assertGreater(report_pos, desc_pos,
                           "Description check must come before report template")


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_purlin_issue")
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
                    "test_file": "tools/test_support/test_pl_purlin_issue.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
