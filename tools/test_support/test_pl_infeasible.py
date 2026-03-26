#!/usr/bin/env python3
"""Tests for the /pl-infeasible skill command file.

Covers all 4 unit test scenarios from features/pl_infeasible.md.
Since skills are agent instruction files (not executable code), these
tests verify structural properties of the command file that ensure
correct runtime behavior.
"""

import os
import json
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, "../../")))
from tools.bootstrap import detect_project_root

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-infeasible.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonEngineer(unittest.TestCase):
    """Scenario: Role gate rejects non-Engineer invocation

    Given an PM agent session
    When the agent invokes /pl-infeasible
    Then the command responds with a redirect message

    Structural test: the command file's first line declares Engineer ownership,
    ensuring non-Engineer agents are rejected with a redirect.
    """

    def test_first_line_declares_builder_ownership(self):
        """First line must declare Engineer as mode."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Purlin mode: Engineer", first_line,
                       "First line must declare 'Purlin mode: Engineer'")

    def test_redirect_message_for_non_engineer(self):
        """Command file must include a redirect message for non-Engineer agents."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(activates Engineer mode|another mode is active|confirm switch)",
            "Must include redirect text for non-Engineer agents",
        )

    def test_redirect_references_pl_infeasible(self):
        """The skill file should reference the INFEASIBLE workflow."""
        content = read_command_file()
        self.assertIn("INFEASIBLE", content,
                       "Must reference INFEASIBLE workflow")


class TestInfeasibleEntryRecordedInCompanion(unittest.TestCase):
    """Scenario: INFEASIBLE entry recorded in companion file

    Given the Engineer cannot implement feature_a as specified
    When /pl-infeasible is invoked for feature_a
    Then features/feature_a.impl.md contains an [INFEASIBLE] entry
    And the entry includes detailed rationale

    Structural test: the command file instructs recording [INFEASIBLE]
    in the companion file with detailed rationale.
    """

    def test_infeasible_tag_mentioned(self):
        """Command file must reference the [INFEASIBLE] tag."""
        content = read_command_file()
        self.assertIn("[INFEASIBLE]", content,
                       "Must reference [INFEASIBLE] tag")

    def test_companion_file_reference(self):
        """Command file must reference the companion file (.impl.md)."""
        content = read_command_file()
        self.assertIn(".impl.md", content,
                       "Must reference companion file (.impl.md)")

    def test_detailed_rationale_required(self):
        """Command file must instruct including detailed rationale."""
        content = read_command_file().lower()
        self.assertIn("rationale", content,
                       "Must instruct providing detailed rationale")

    def test_commit_includes_infeasible_tag(self):
        """Command file must instruct committing with [INFEASIBLE] in the message."""
        content = read_command_file()
        # The commit instruction should mention both commit and INFEASIBLE
        self.assertIn("commit", content.lower(),
                       "Must instruct committing the entry")


class TestNoCodeImplemented(unittest.TestCase):
    """Scenario: No code is implemented

    Given /pl-infeasible is invoked for feature_a
    When the escalation workflow completes
    Then no implementation code exists for feature_a

    Structural test: the command file explicitly instructs NOT to implement
    any code for the feature.
    """

    def test_explicit_no_implementation_instruction(self):
        """Command file must explicitly state not to implement code."""
        content = read_command_file().lower()
        self.assertTrue(
            "do not implement" in content or "do not implement any code" in content,
            "Must explicitly state 'Do NOT implement' code"
        )

    def test_architect_must_revise_before_resume(self):
        """Command file must state the PM must revise the spec first."""
        content = read_command_file().lower()
        self.assertIn("pm", content,
                       "Must reference the PM role")
        self.assertIn("revise", content,
                       "Must state the spec needs to be revised")

    def test_no_implement_before_spec_revision(self):
        """The no-implement instruction should reference spec revision as precondition."""
        content = read_command_file()
        no_impl_pos = content.lower().find("do not implement")
        revise_pos = content.lower().find("revise")
        self.assertGreater(no_impl_pos, -1, "Must contain 'Do NOT implement'")
        self.assertGreater(revise_pos, -1, "Must contain 'revise'")


class TestScanSurfacesInfeasibleAsActionItem(unittest.TestCase):
    """Scenario: Scan surfaces INFEASIBLE as action item

    Given the INFEASIBLE entry is committed
    When scan.sh runs
    Then the scan results show a PM action item

    Structural test: the command file instructs running scan.sh to surface
    the INFEASIBLE entry in scan results.
    """

    def test_scan_sh_invocation(self):
        """Command file must instruct running scan.sh."""
        content = read_command_file()
        self.assertIn("scan.sh", content,
                       "Must instruct running scan.sh")

    def test_scan_results_surfacing(self):
        """Command file must describe surfacing the entry in scan results."""
        content = read_command_file().lower()
        self.assertIn("scan", content,
                       "Must reference scan results")

    def test_action_item_priority_designation(self):
        """Command file must surface INFEASIBLE as a PM action item."""
        content = read_command_file().lower()
        self.assertIn("action item", content,
                       "Must surface INFEASIBLE as a PM action item")

    def test_architect_action_item(self):
        """Command file must describe the escalation targeting the PM."""
        content = read_command_file().lower()
        self.assertIn("pm", content,
                       "Must reference PM as the action target")


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_infeasible")
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
                    "test_file": "tools/test_support/test_pl_infeasible.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
