#!/usr/bin/env python3
"""Tests for the /pl-release-check skill command file.

Covers all 4 unit test scenarios from features/pl_release_check.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-release-check.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonArchitect(unittest.TestCase):
    """Scenario: Role gate rejects non-Architect invocation

    Given a Builder agent session
    When the agent invokes /pl-release-check
    Then the command responds with a redirect message

    Structural test: the command file declares Architect ownership and
    contains a redirect message for non-Architect agents.
    """

    def test_command_owner_is_architect(self):
        """The command file declares 'Purlin command owner: Architect'."""
        content = read_command_file()
        self.assertIn("command owner: Architect", content)

    def test_redirect_message_present(self):
        """Non-Architect agents receive a redirect message."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)ask your architect.*(/pl-release-check|run)",
        )

    def test_role_gate_appears_before_instructions(self):
        """The role gate block appears before the operational instructions."""
        content = read_command_file()
        gate_pos = content.lower().find("command owner: architect")
        # The operational content starts after the horizontal rule separator
        instruction_pos = content.find("Execute the CDD release checklist")
        self.assertGreater(gate_pos, -1, "Role gate must exist")
        self.assertGreater(instruction_pos, gate_pos,
                           "Role gate must appear before operational instructions")


class TestZeroQueueMandateListsBlockingFeatures(unittest.TestCase):
    """Scenario: Zero-Queue Mandate lists blocking features

    Given feature_a has builder status TODO
    When the Zero-Queue Mandate is checked
    Then feature_a is listed as a release blocker

    Structural test: the command file specifies the Zero-Queue Mandate
    verification with explicit status requirements for all three roles.
    """

    def test_zero_queue_mandate_mentioned(self):
        """The command file references the Zero-Queue Mandate."""
        content = read_command_file()
        self.assertIn("Zero-Queue Mandate", content)

    def test_architect_done_required(self):
        """Architect status must be DONE for release readiness."""
        content = read_command_file()
        self.assertIn('architect', content.lower())
        self.assertIn('"DONE"', content)

    def test_builder_done_required(self):
        """Builder status must be DONE for release readiness."""
        content = read_command_file()
        self.assertIn('builder', content.lower())
        # "DONE" already asserted; verify builder is explicitly checked
        self.assertRegex(content, r'(?i)builder.*"DONE"')

    def test_blocking_features_listed(self):
        """The command file instructs listing blocking features."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(list.*blocking|blocking.*feature)",
        )


class TestCycleDetectionFlagsCircularDependencies(unittest.TestCase):
    """Scenario: Cycle detection flags circular dependencies

    Given the dependency graph contains a cycle
    When the graph is checked
    Then the cycle is reported as a release blocker

    Structural test: the command file references the dependency graph
    file and includes cycle-checking instructions.
    """

    def test_dependency_graph_file_referenced(self):
        """The command file references dependency_graph.json."""
        content = read_command_file()
        self.assertIn("dependency_graph.json", content)

    def test_cycle_check_instruction_present(self):
        """The command file instructs checking for cycles."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)cycle")

    def test_graph_check_after_zero_queue(self):
        """Cycle check appears after Zero-Queue Mandate verification."""
        content = read_command_file()
        zq_pos = content.find("Zero-Queue Mandate")
        cycle_pos = content.find("dependency_graph.json")
        self.assertGreater(zq_pos, -1, "Zero-Queue Mandate must be mentioned")
        self.assertGreater(cycle_pos, zq_pos,
                           "Dependency graph check must come after Zero-Queue Mandate")


class TestStepsExecutedInConfiguredOrder(unittest.TestCase):
    """Scenario: Steps executed in configured order

    Given config.json defines steps A, B, C in that order
    When /pl-release-check runs
    Then step A is presented first, then B, then C

    Structural test: the command file references the release config file
    and instructs working through steps in configured sequence order.
    """

    def test_release_config_referenced(self):
        """The command file references the release config file."""
        content = read_command_file()
        self.assertRegex(content, r"release/config\.json")

    def test_step_sequence_instruction(self):
        """The command file instructs processing steps in order."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(in order|in.*sequence|step.*order|each.*step)",
        )

    def test_interactive_confirmation_present(self):
        """Each step requires confirmation before proceeding."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(confirm|ask.*before.*proceed|proceed.*next)",
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_release_check")
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
                    "test_file": "tools/test_support/test_pl_release_check.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
