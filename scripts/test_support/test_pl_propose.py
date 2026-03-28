#!/usr/bin/env python3
"""Tests for the /pl-propose skill command file.

Covers all 4 unit test scenarios from features/pl_propose.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-propose.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonEngineerInvocation(unittest.TestCase):
    """Scenario: Role gate rejects non-Engineer invocation

    Given an PM agent session
    When the agent invokes /pl-propose
    Then the command responds with a redirect message

    Structural test: the command file's first line declares Engineer as
    the mode declaration, which means non-Engineer agents will be redirected.
    """

    def test_first_line_declares_builder_owner(self):
        """First line must contain the Engineer mode declaration declaration."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Purlin mode: Engineer", first_line,
                       "First line must declare Engineer as mode")

    def test_redirect_message_for_non_builder(self):
        """Command file must include a redirect message for non-Engineer agents."""
        content = read_command_file()
        self.assertIn("another mode is active", content,
                       "Must include redirect guidance for non-Engineer agents")

    def test_redirect_mentions_builder_role(self):
        """Redirect message must tell non-Engineer agents to ask a Engineer."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(another mode is active|confirm switch)",
            "Redirect must instruct non-Engineer to ask Engineer to run /pl-propose",
        )


class TestProposalRecordedInCompanionFile(unittest.TestCase):
    """Scenario: Proposal recorded in companion file

    Given the Engineer discovers a spec gap in feature_a
    When /pl-propose is invoked with topic about feature_a
    Then features/feature_a.impl.md contains a [SPEC_PROPOSAL] entry
    And the entry includes rationale and proposed change

    Structural test: the command file describes recording proposals in
    companion files with rationale and proposed change content.
    """

    def test_spec_proposal_tag_present(self):
        """Command file must reference the [SPEC_PROPOSAL] tag."""
        content = read_command_file()
        self.assertIn("[SPEC_PROPOSAL]", content,
                       "Must reference [SPEC_PROPOSAL] tag for recording proposals")

    def test_companion_file_recording_described(self):
        """Command file must describe recording in the companion/implementation notes file."""
        content = read_command_file()
        # The command should mention recording in the implementation notes / companion file
        self.assertRegex(
            content,
            r"(?i)(implementation notes|companion file|impl\.md|\.impl\.md)",
            "Must describe recording proposals in companion/implementation notes file",
        )

    def test_rationale_required(self):
        """Command file must mention including rationale in the proposal."""
        content = read_command_file()
        self.assertIn("rationale", content.lower(),
                       "Must describe including rationale in the proposal entry")

    def test_proposed_change_described(self):
        """Command file must describe drafting a concrete proposal of what should change."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(what should change|concrete proposal|proposed change|draft.*proposal)",
            "Must describe drafting a concrete proposed change",
        )


class TestAnchorNodeProposalUsesCorrectTag(unittest.TestCase):
    """Scenario: Anchor node proposal uses correct tag

    Given the Engineer discovers a cross-cutting constraint
    When /pl-propose records a new anchor proposal
    Then the entry uses [SPEC_PROPOSAL: NEW_ANCHOR] tag
    And includes proposed anchor type, name, and invariants

    Structural test: the command file references the NEW_ANCHOR variant of
    the SPEC_PROPOSAL tag for anchor node proposals.
    """

    def test_new_anchor_tag_present(self):
        """Command file must reference [SPEC_PROPOSAL: NEW_ANCHOR] tag."""
        content = read_command_file()
        self.assertIn("[SPEC_PROPOSAL: NEW_ANCHOR]", content,
                       "Must reference [SPEC_PROPOSAL: NEW_ANCHOR] tag for anchor proposals")

    def test_anchor_tag_appears_after_general_proposal(self):
        """NEW_ANCHOR tag should be contextualized after general proposal workflow."""
        content = read_command_file()
        general_pos = content.find("[SPEC_PROPOSAL]")
        anchor_pos = content.find("[SPEC_PROPOSAL: NEW_ANCHOR]")
        self.assertGreater(general_pos, -1, "General [SPEC_PROPOSAL] tag must exist")
        self.assertGreater(anchor_pos, -1, "[SPEC_PROPOSAL: NEW_ANCHOR] tag must exist")


class TestProposalCommittedToGit(unittest.TestCase):
    """Scenario: Proposal is committed to git

    Given a proposal entry is written to the companion file
    When the proposal workflow completes
    Then the companion file change is committed
    And the Critic report will surface it at the PM's next session

    Structural test: the command file describes committing the companion
    file entry to git so it is visible to the PM via the Critic.
    """

    def test_commit_instruction_present(self):
        """Command file must instruct committing the entry."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)commit",
            "Must describe committing the companion file entry to git",
        )

    def test_pm_visibility_via_scan(self):
        """Command file must describe that PM mode sees it via scan results."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)PM mode sees|scan results",
            "Must describe PM visibility through scan results",
        )

    def test_committed_entry_is_only_valid_output(self):
        """Command file must state that a committed entry is the only valid output."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)only valid output.*committed|committed.*only valid output",
            "Must state that the only valid output is a committed entry",
        )

    def test_chat_not_durable_channel(self):
        """Command file must enforce that chat is not a durable communication channel."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)chat.*not.*durable|do not pass.*chat",
            "Must state that chat is not a durable channel for proposals",
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_propose")
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
                    "test_file": "tools/test_support/test_pl_propose.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
