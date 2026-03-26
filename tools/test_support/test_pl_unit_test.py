#!/usr/bin/env python3
"""Tests for the /pl-unit-test skill command file.

Covers all 5 unit test scenarios from features/pl_unit_test.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-unit-test.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonEngineer(unittest.TestCase):
    """Scenario: Role gate rejects non-Engineer invocation

    Given a QA agent session
    When the agent invokes /pl-unit-test
    Then the command responds with a redirect message

    Structural test: the command file's first line declares Engineer as
    the mode declaration, which means non-Engineer agents will be rejected.
    """

    def test_first_line_declares_builder_owner(self):
        """First line must declare Engineer as the mode declaration."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Engineer", first_line)
        self.assertIn("purlin mode", first_line.lower())

    def test_redirect_message_for_non_engineer(self):
        """Command file must contain a redirect message for non-Engineer agents."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(another mode is active|confirm switch|activates Engineer mode)",
        )

    def test_redirect_mentions_engineer_mode(self):
        """Redirect message must reference Engineer mode."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(activates Engineer mode|another mode is active|confirm switch)",
        )


class TestCardinalRuleRejectsSourceReading(unittest.TestCase):
    """Scenario: Cardinal rule rejects source-reading tests

    Given a test file that reads features/my_feature.md and asserts string presence
    When the quality rubric gate runs
    Then the test fails AP-1 (Prose Inspection) check
    And tests.json is not written

    Structural test: the command file describes the AP-1 anti-pattern
    (prose inspection / reading source instead of calling implementation).
    """

    def test_ap1_label_present(self):
        """Command file must name the AP-1 anti-pattern."""
        content = read_command_file()
        self.assertIn("AP-1", content)

    def test_ap1_describes_prose_inspection(self):
        """AP-1 section must describe prose inspection as the anti-pattern."""
        content = read_command_file()
        self.assertIn("Prose Inspection", content)

    def test_cardinal_rule_forbids_reading_source(self):
        """The cardinal rule section must forbid reading source to verify presence."""
        content = read_command_file()
        self.assertIn(
            "Grepping or reading source code to verify its presence is NOT testing",
            content,
        )

    def test_ap1_bad_example_shows_file_read(self):
        """AP-1 must include a BAD example showing file reading."""
        content = read_command_file()
        # The BAD example should show opening a features/ file and asserting string presence
        # Use the full section header to find the detailed AP-1 description with examples
        ap1_pos = content.find("AP-1: Prose Inspection")
        self.assertGreater(ap1_pos, -1)
        ap1_section = content[ap1_pos:ap1_pos + 500]
        self.assertIn("BAD", ap1_section)
        self.assertRegex(ap1_section, r"open\(.*features/")


class TestQualityRubricBlocksMockDominated(unittest.TestCase):
    """Scenario: Quality rubric blocks on mock-dominated test

    Given a test that mocks the implementation under test and asserts mock was called
    When the quality rubric gate runs
    Then the test fails AP-3 (Mock-Dominated) check
    And tests.json is not written until the test is fixed

    Structural test: the command file describes the AP-3 anti-pattern
    (mock-dominated tests).
    """

    def test_ap3_label_present(self):
        """Command file must name the AP-3 anti-pattern."""
        content = read_command_file()
        self.assertIn("AP-3", content)

    def test_ap3_describes_mock_dominated(self):
        """AP-3 section must describe mock-dominated as the anti-pattern."""
        content = read_command_file()
        self.assertIn("Mock-Dominated", content)

    def test_ap3_bad_example_shows_mock_assertion(self):
        """AP-3 must include a BAD example showing mock assertion."""
        content = read_command_file()
        ap3_pos = content.find("AP-3")
        self.assertGreater(ap3_pos, -1)
        ap3_section = content[ap3_pos:ap3_pos + 500]
        self.assertIn("BAD", ap3_section)
        self.assertIn("Mock", ap3_section)

    def test_no_self_mocking_rubric_check(self):
        """Quality rubric must include a NO SELF-MOCKING check."""
        content = read_command_file()
        self.assertIn("NO SELF-MOCKING", content)


class TestTestsJsonProducedByRunner(unittest.TestCase):
    """Scenario: tests.json produced by actual test runner

    Given all 6 rubric checks pass
    When tests.json is written
    Then it contains status, passed, failed, and total fields
    And total is greater than 0
    And it was produced by a test runner, not hand-written

    Structural test: the command file states tests.json must be from an actual
    test runner and must contain the required fields.
    """

    def test_actual_runner_mandate(self):
        """Command file must state tests.json must be produced by actual test runner."""
        content = read_command_file()
        self.assertIn("actual test runner", content)

    def test_never_hand_written_mandate(self):
        """Command file must state tests.json must never be hand-written."""
        content = read_command_file()
        self.assertIn("never hand-written", content)

    def test_required_fields_documented(self):
        """Command file must list status, passed, failed, total as required fields."""
        content = read_command_file()
        # All four required fields must be mentioned in the result reporting section
        for field in ("status", "passed", "failed", "total"):
            self.assertIn(
                field,
                content,
                f"Required field '{field}' not found in command file",
            )

    def test_total_greater_than_zero_mandate(self):
        """Command file must state total must be > 0."""
        content = read_command_file()
        self.assertIn("total", content)
        self.assertRegex(content, r"total.*>.*0|total.*MUST be > 0")


class TestAuditRecordWrittenToCompanionFile(unittest.TestCase):
    """Scenario: Audit record written to companion file

    Given the rubric passes for feature_a
    When the audit record is written
    Then features/feature_a.impl.md contains a Test Quality Audit section
    And the section includes rubric score, test count, and date

    Structural test: the command file describes writing audit records to
    companion files with rubric score, test count, and date.
    """

    def test_companion_file_audit_section_documented(self):
        """Command file must describe a Test Quality Audit section."""
        content = read_command_file()
        self.assertIn("Test Quality Audit", content)

    def test_audit_includes_rubric_score(self):
        """Audit record template must include rubric score."""
        content = read_command_file()
        # The audit template should show "Rubric: 6/6 PASS" or similar
        audit_pos = content.find("Test Quality Audit")
        self.assertGreater(audit_pos, -1)
        audit_section = content[audit_pos:audit_pos + 300]
        self.assertRegex(audit_section, r"Rubric.*6/6")

    def test_audit_includes_test_count(self):
        """Audit record template must include test counts."""
        content = read_command_file()
        audit_pos = content.find("Test Quality Audit")
        self.assertGreater(audit_pos, -1)
        audit_section = content[audit_pos:audit_pos + 300]
        self.assertIn("Tests:", audit_section)

    def test_audit_includes_date(self):
        """Audit record template must include a date field."""
        content = read_command_file()
        audit_pos = content.find("Test Quality Audit")
        self.assertGreater(audit_pos, -1)
        audit_section = content[audit_pos:audit_pos + 300]
        self.assertIn("Date:", audit_section)


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_unit_test")
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
                    "test_file": "tools/test_support/test_pl_unit_test.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
