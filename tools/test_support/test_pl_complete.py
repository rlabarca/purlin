#!/usr/bin/env python3
"""Tests for the /pl-complete skill command file.

Covers all 5 unit test scenarios from features/pl_complete.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-complete.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonQA(unittest.TestCase):
    """Scenario: Role gate rejects non-QA invocation

    Given a Engineer agent session
    When the agent invokes /pl-complete
    Then the command responds with a redirect message

    Structural test: the command file declares QA ownership and includes
    a redirect message for non-QA agents.
    """

    def test_declares_qa_ownership(self):
        """First line declares QA as the mode declaration."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Purlin mode:", first_line.lower())
        self.assertIn("qa", first_line.lower())

    def test_redirect_message_for_non_qa(self):
        """Contains a redirect message telling non-QA agents to use QA."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(ask your qa|qa agent|qa command)",
        )

    def test_stop_instruction_after_redirect(self):
        """The redirect message includes a stop instruction."""
        content = read_command_file()
        # After the role gate block, there should be a "stop" directive
        lines = content.splitlines()
        role_gate_region = "\n".join(lines[:10])
        self.assertIn("stop", role_gate_region.lower())


class TestAllGatesPassCreatesCompletionCommit(unittest.TestCase):
    """Scenario: All gates pass creates completion commit

    Given feature_a is in TESTING state
    And all scenarios are verified
    And zero open discoveries exist
    And feature_a is not in a PENDING delivery phase
    When /pl-complete is invoked for feature_a
    Then a commit is created with "[Complete features/feature_a.md] [Verified]"

    Structural test: the command file contains the commit template with
    [Complete] and [Verified] tags and references scan.sh for confirmation.
    """

    def test_commit_template_includes_complete_tag(self):
        """Commit template contains the [Complete features/<name>.md] pattern."""
        content = read_command_file()
        self.assertRegex(content, r"\[Complete features/")

    def test_commit_template_includes_verified_tag(self):
        """Commit template contains the [Verified] tag."""
        content = read_command_file()
        self.assertIn("[Verified]", content)

    def test_verified_tag_in_commit_command(self):
        """The git commit command includes both [Complete] and [Verified]."""
        content = read_command_file()
        # Find the git commit line and check it has both tags
        commit_match = re.search(r"git commit.*\[Complete.*\].*\[Verified\]", content)
        self.assertIsNotNone(commit_match, "git commit command must include both [Complete] and [Verified] tags")

    def test_scan_sh_confirmation_after_commit(self):
        """After the commit, scan.sh is invoked to confirm transition."""
        content = read_command_file()
        self.assertIn("scan.sh", content)


class TestOpenDiscoveriesBlockCompletion(unittest.TestCase):
    """Scenario: Open discoveries block completion

    Given feature_a has 2 OPEN discoveries
    When /pl-complete is invoked for feature_a
    Then the command reports the 2 open discoveries by title
    And no completion commit is created

    Structural test: the command file checks for OPEN and SPEC_UPDATED
    discoveries and includes failure reporting instructions.
    """

    def test_checks_open_discoveries(self):
        """Command file references OPEN discovery status."""
        content = read_command_file()
        self.assertIn("OPEN", content)

    def test_checks_spec_updated_discoveries(self):
        """Command file references SPEC_UPDATED discovery status."""
        content = read_command_file()
        self.assertIn("SPEC_UPDATED", content)

    def test_references_discoveries_file(self):
        """Command file references the discoveries sidecar file pattern."""
        content = read_command_file()
        self.assertIn("discoveries.md", content)

    def test_failure_message_for_open_discoveries(self):
        """Command file includes failure messaging for open discoveries."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(open discoveries remain|must be resolved)",
        )


class TestDeliveryPlanGatesCompletion(unittest.TestCase):
    """Scenario: Delivery plan gates completion

    Given feature_a appears in Phase 2 which is PENDING
    When /pl-complete is invoked for feature_a
    Then the command reports the feature is phase-gated
    And no completion commit is created

    Structural test: the command file checks the delivery plan for PENDING
    phases and includes phase-gating failure messaging.
    """

    def test_checks_delivery_plan(self):
        """Command file references delivery_plan.md."""
        content = read_command_file()
        self.assertIn("delivery_plan.md", content)

    def test_checks_pending_phase(self):
        """Command file references PENDING phase status."""
        content = read_command_file()
        self.assertIn("PENDING", content)

    def test_phase_gated_failure_message(self):
        """Command file includes phase-gated failure messaging."""
        content = read_command_file()
        # The spec says: "Feature X is deferred until all phases are delivered (appears in Phase N)."
        self.assertRegex(
            content,
            r"(?i)(phase|deferred|phase.*gated|appears in.*phase)",
        )


class TestNotInTestingStateBlocksCompletion(unittest.TestCase):
    """Scenario: Not in TESTING state blocks completion

    Given feature_a is in TODO state
    When /pl-complete is invoked for feature_a
    Then the command reports "Feature must be in TESTING state. Current state: TODO"

    Structural test: the command file checks TESTING state and includes
    the exact failure message template.
    """

    def test_requires_testing_state(self):
        """Command file checks that the feature is in TESTING state."""
        content = read_command_file()
        self.assertIn("TESTING", content)

    def test_failure_message_template(self):
        """Command file includes the exact failure message template for wrong state."""
        content = read_command_file()
        self.assertIn("Feature must be in TESTING state", content)

    def test_current_state_placeholder(self):
        """Failure message includes a current state indicator."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)current state",
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_complete")
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
                    "test_file": "tools/test_support/test_pl_complete.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
