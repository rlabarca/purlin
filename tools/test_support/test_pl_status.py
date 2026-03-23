#!/usr/bin/env python3
"""Tests for the /pl-status skill command file.

Covers all 4 unit test scenarios from features/pl_status.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-status.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestAllRolesCanInvoke(unittest.TestCase):
    """Scenario: All roles can invoke the command

    Given any agent role (Architect, Builder, QA, or PM)
    When the user invokes /pl-status
    Then the skill executes without a role authorization error

    Structural test: the command file's first line declares 'shared (all roles)',
    which means no role gate check will block execution.
    """

    def test_first_line_declares_shared_all_roles(self):
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("shared (all roles)", first_line.lower())

    def test_no_role_gate_pattern(self):
        """No single-role ownership pattern like 'command owner: Builder'."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertNotIn("command owner:", first_line.lower())

    def test_first_line_is_purlin_command_declaration(self):
        """First line uses the standard Purlin command declaration format."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("purlin command", first_line.lower())


class TestOutputIncludesFeatureCountsByStatus(unittest.TestCase):
    """Scenario: Output includes feature counts by status

    Given a project with features in various lifecycle states
    When /pl-status is invoked
    Then the output includes a summary of feature counts grouped by status

    Structural test: the command file instructs running status.sh and
    summarizing feature counts (TODO / TESTING / COMPLETE).
    """

    def test_references_status_sh(self):
        content = read_command_file()
        self.assertIn("status.sh", content)

    def test_mentions_todo_status(self):
        content = read_command_file()
        self.assertIn("TODO", content)

    def test_mentions_testing_status(self):
        content = read_command_file()
        self.assertIn("TESTING", content)

    def test_mentions_complete_status(self):
        content = read_command_file()
        self.assertIn("COMPLETE", content)

    def test_feature_counts_instruction(self):
        """Command instructs summarizing feature counts by status."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)feature\s+counts\s+by\s+status",
        )


class TestRoleFilteredView(unittest.TestCase):
    """Scenario: Role-filtered view shows only relevant items

    Given a user knows their role
    When they invoke /pl-status with a role filter
    Then only items relevant to that role are displayed

    Structural test: the command file references the --role flag for
    filtered views.
    """

    def test_role_flag_present(self):
        content = read_command_file()
        self.assertIn("--role", content)

    def test_role_flag_used_with_status_sh(self):
        """The --role flag is used in the context of status.sh invocation."""
        content = read_command_file()
        # Both --role and status.sh should be present, and --role should
        # appear in a line that relates to status.sh usage
        self.assertIn("status.sh --role", content)

    def test_filtered_view_documented(self):
        """Command file explains the filtered view concept."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)filter",
        )


class TestArchitectSeesUncommittedChangesCheck(unittest.TestCase):
    """Scenario: Architect sees uncommitted changes check

    Given the invoking agent is the Architect
    When /pl-status is invoked
    Then the output includes an uncommitted changes check
    And a commit message is proposed for Architect-owned files

    Structural test: the command file contains Architect-specific
    uncommitted changes logic with commit message proposal.
    """

    def test_architect_specific_section_present(self):
        content = read_command_file()
        self.assertIn("Architect", content)
        self.assertRegex(
            content,
            r"(?i)architect.*uncommitted",
        )

    def test_git_status_check_present(self):
        """Command instructs running git status for uncommitted changes."""
        content = read_command_file()
        self.assertIn("git status", content)

    def test_git_diff_check_present(self):
        """Command instructs running git diff for change details."""
        content = read_command_file()
        self.assertIn("git diff", content)

    def test_commit_message_proposal(self):
        """Command instructs proposing a commit message for Architect-owned files."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)commit\s+message",
        )

    def test_architect_owned_files_listed(self):
        """Command lists file patterns considered Architect-owned."""
        content = read_command_file()
        # At least features/*.md should be listed as Architect-owned
        self.assertIn("features/*.md", content)


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_status")
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
                    "test_file": "tools/test_support/test_pl_status.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
