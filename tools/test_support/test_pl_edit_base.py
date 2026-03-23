#!/usr/bin/env python3
"""Tests for the /pl-edit-base skill command file.

Covers all 4 unit test scenarios from features/pl_edit_base.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-edit-base.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestConsumerProjectReceivesRedirect(unittest.TestCase):
    """Scenario: Consumer project receives redirect

    Given a consumer project with purlin/ submodule directory
    When /pl-edit-base is invoked
    Then the command redirects to /pl-override-edit

    Structural test: the command file checks for purlin/ submodule directory
    and redirects consumer projects to /pl-override-edit.
    """

    def test_purlin_submodule_check_present(self):
        """Command file checks for purlin/ submodule directory."""
        content = read_command_file()
        self.assertIn("purlin/", content,
                       "Command must check for purlin/ submodule directory")

    def test_redirect_to_override_edit(self):
        """Command file directs consumer projects to /pl-override-edit."""
        content = read_command_file()
        self.assertIn("/pl-override-edit", content,
                       "Command must redirect consumer projects to /pl-override-edit")

    def test_consumer_project_stop_instruction(self):
        """Command file instructs the agent to stop for consumer projects."""
        content = read_command_file()
        # The command should contain both the redirect and a stop instruction
        self.assertRegex(
            content,
            r"(?i)(and stop|stop\b)",
            "Command must instruct agent to stop after redirect",
        )

    def test_redirect_appears_before_protocol(self):
        """The consumer redirect appears before the editing protocol steps."""
        content = read_command_file()
        redirect_pos = content.find("/pl-override-edit")
        # The protocol section should come after the redirect guard
        protocol_pos = content.find("Protocol:")
        self.assertGreater(protocol_pos, redirect_pos,
                           "Consumer redirect must appear before protocol steps")


class TestProtocolDetailRoutedToSkillFile(unittest.TestCase):
    """Scenario: Protocol detail routed to skill file

    Given the proposed addition is a multi-step workflow
    When context budget classification runs
    Then the content is classified as protocol detail
    And the user is advised to put it in a skill file instead

    Structural test: the command file contains context budget classification
    logic that distinguishes bright-line rules from protocol detail.
    """

    def test_context_budget_classification_section(self):
        """Command file has a context budget classification section."""
        content = read_command_file()
        self.assertIn("Context Budget Classification", content,
                       "Command must include context budget classification")

    def test_bright_line_rule_category(self):
        """Command file defines bright-line rule as a category."""
        content = read_command_file()
        self.assertIn("Bright-line rule", content,
                       "Command must define bright-line rule category")

    def test_protocol_detail_category(self):
        """Command file defines protocol detail as a category."""
        content = read_command_file()
        self.assertIn("Protocol detail", content,
                       "Command must define protocol detail category")

    def test_skill_file_routing_instruction(self):
        """Command file routes protocol detail to skill files."""
        content = read_command_file()
        # Should instruct that protocol detail goes to skill files
        self.assertRegex(
            content,
            r"(?i)skill.file",
            "Command must route protocol detail to skill files",
        )


class TestOverrideConflictScanRunsBeforeEdit(unittest.TestCase):
    """Scenario: Override conflict scan runs before edit

    Given a proposed change to BUILDER_BASE.md
    When /pl-edit-base processes the edit
    Then BUILDER_OVERRIDES.md is scanned for conflicts
    And any conflicts are presented before proceeding

    Structural test: the command file instructs running /pl-override-edit
    --scan-only on override files before applying changes.
    """

    def test_scan_only_flag_present(self):
        """Command file uses --scan-only flag for override scanning."""
        content = read_command_file()
        self.assertIn("--scan-only", content,
                       "Command must use --scan-only flag for override conflict scan")

    def test_override_scan_references_override_edit(self):
        """Override scan uses /pl-override-edit command."""
        content = read_command_file()
        self.assertIn("/pl-override-edit --scan-only", content,
                       "Command must invoke /pl-override-edit --scan-only")

    def test_conflict_surfacing_before_proceeding(self):
        """Conflicts are surfaced before proceeding with the edit."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(surface|conflict).*(before|prior)",
            "Command must surface conflicts before proceeding",
        )

    def test_scan_step_before_apply_step(self):
        """The override scan step appears before the apply/write step."""
        content = read_command_file()
        scan_pos = content.find("--scan-only")
        # The actual writing/applying step should come after scanning
        apply_pos = content.find("apply and commit")
        self.assertGreater(apply_pos, scan_pos,
                           "Override scan must happen before applying changes")


class TestAdditiveOnlyPrincipleEnforced(unittest.TestCase):
    """Scenario: Additive-only principle enforced

    Given the edit attempts to delete existing content
    When /pl-edit-base validates the change
    Then explicit user confirmation is required for revisionary changes

    Structural test: the command file enforces additive-only editing and
    requires explicit confirmation for revisionary changes.
    """

    def test_additive_only_principle_stated(self):
        """Command file states the additive-only principle."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)additive.only",
            "Command must state the additive-only principle",
        )

    def test_revisionary_changes_require_confirmation(self):
        """Revisionary changes require explicit user confirmation."""
        content = read_command_file()
        # Should mention revisionary changes and confirmation
        self.assertRegex(
            content,
            r"(?i)revisionary",
            "Command must address revisionary changes",
        )

    def test_explicit_confirmation_required(self):
        """Command file requires explicit confirmation before writing."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(explicit.*confirmation|confirmation.*before|ask.*confirmation|user confirmation)",
            "Command must require explicit confirmation for changes",
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_edit_base")
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
                    "test_file": "tools/test_support/test_pl_edit_base.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
