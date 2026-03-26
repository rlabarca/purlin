#!/usr/bin/env python3
"""Tests for the /pl-qa-report skill command file.

Covers all 4 unit test scenarios from features/pl_qa_report.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-qa-report.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonQAInvocation(unittest.TestCase):
    """Scenario: Role gate rejects non-QA invocation

    Given a Engineer agent session
    When the agent invokes /pl-qa-report
    Then the command responds with a redirect message

    Structural test: the command file declares QA ownership and contains
    a redirect message for non-QA agents.
    """

    def test_first_line_declares_qa_ownership(self):
        """The command file must declare QA as the mode declaration."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("QA", first_line,
                       "First line must declare QA role ownership")

    def test_role_gate_pattern_present(self):
        """Command file must contain a role gate check for QA."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(mode declaration|purlin mode declaration).*QA",
            "Must contain a mode declaration declaration for QA",
        )

    def test_redirect_message_for_non_qa(self):
        """Command file must contain a redirect message for non-QA agents."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(another mode is active|confirm switch|purlin mode.*QA)",
            "Must contain a redirect message directing non-QA agents to QA",
        )

    def test_redirect_references_command_name(self):
        """The redirect message must reference the /pl-qa-report command."""
        content = read_command_file()
        self.assertIn("pl-qa-report", content,
                       "Redirect message must reference the command name")


class TestReportShowsTestingFeaturesWithCounts(unittest.TestCase):
    """Scenario: Report shows TESTING features with counts

    Given 3 features are in TESTING state
    When /pl-qa-report is invoked
    Then all 3 features are listed with manual item counts and scopes

    Structural test: the command file defines a TESTING Features table
    with columns for manual items, scope, and discovery counts.
    """

    def test_testing_features_section_present(self):
        """Output template must include a TESTING Features section."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)TESTING\s+Features",
            "Must contain a 'TESTING Features' section heading",
        )

    def test_manual_items_column_present(self):
        """The TESTING Features table must include a Manual Items column."""
        content = read_command_file()
        self.assertIn("Manual Items", content,
                       "Table must include 'Manual Items' column")

    def test_scope_column_present(self):
        """The TESTING Features table must include a Scope column."""
        content = read_command_file()
        self.assertIn("Scope", content,
                       "Table must include 'Scope' column")

    def test_open_discoveries_column_present(self):
        """The TESTING Features table must include an Open Discoveries column."""
        content = read_command_file()
        self.assertIn("Open Discoveries", content,
                       "Table must include 'Open Discoveries' column")


class TestOpenDiscoveriesGroupedByType(unittest.TestCase):
    """Scenario: Open discoveries grouped by type

    Given 2 BUG and 1 SPEC_DISPUTE discoveries are open
    When /pl-qa-report is invoked
    Then the Open Discoveries section shows BUG (2) and SPEC_DISPUTE (1)

    Structural test: the command file defines an Open Discoveries section
    that groups discoveries by type (BUG, SPEC_DISPUTE, etc.).
    """

    def test_open_discoveries_section_present(self):
        """Output template must include an Open Discoveries section."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)Open\s+Discoveries",
            "Must contain an 'Open Discoveries' section heading",
        )

    def test_bug_type_grouping(self):
        """The Open Discoveries section must support BUG type grouping."""
        content = read_command_file()
        self.assertIn("BUG", content,
                       "Must reference BUG discovery type")

    def test_spec_dispute_type_grouping(self):
        """The Open Discoveries section must support SPEC_DISPUTE type grouping."""
        content = read_command_file()
        self.assertIn("SPEC_DISPUTE", content,
                       "Must reference SPEC_DISPUTE discovery type")

    def test_type_count_pattern_in_template(self):
        """Template must show type-grouped counts like 'TYPE (N):'."""
        content = read_command_file()
        # Look for the pattern TYPE (N): in the output template
        self.assertRegex(
            content,
            r"BUG\s*\(N\)",
            "Template must show count pattern like 'BUG (N)'",
        )


class TestDeliveryPlanGatingShown(unittest.TestCase):
    """Scenario: Delivery plan gating shown

    Given feature_a is phase-gated in Phase 2
    When /pl-qa-report is invoked
    Then feature_a is listed as phase-gated in Completion Blockers

    Structural test: the command file defines a Completion Blockers section
    that includes phase-gated status and references the delivery plan.
    """

    def test_completion_blockers_section_present(self):
        """Output template must include a Completion Blockers section."""
        content = read_command_file()
        self.assertIn("Completion Blockers", content,
                       "Must contain a 'Completion Blockers' section")

    def test_phase_gated_reference(self):
        """Completion Blockers must reference phase-gated features."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)phase.gated",
            "Must reference 'phase-gated' in completion blockers",
        )

    def test_delivery_plan_context_section(self):
        """Output must include a Delivery Plan Context section."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)delivery\s+plan",
            "Must contain Delivery Plan reference for context",
        )

    def test_delivery_plan_file_referenced(self):
        """Command file must reference the delivery_plan.md file path."""
        content = read_command_file()
        self.assertIn("delivery_plan.md", content,
                       "Must reference the delivery_plan.md file")


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_qa_report")
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
                    "test_file": "tools/test_support/test_pl_qa_report.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
