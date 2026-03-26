#!/usr/bin/env python3
"""Tests for the /pl-anchor skill command file.

Covers all 4 unit test scenarios from features/pl_anchor.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-anchor.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonArchitect(unittest.TestCase):
    """Scenario: Role gate rejects non-PM/Architect invocation

    Given a Builder agent session
    When the agent invokes /pl-anchor
    Then the command responds with a redirect message

    Structural test: the command file declares Architect ownership and
    contains a redirect message for non-Architect agents.
    """

    def test_declares_architect_command_owner(self):
        """The first line establishes Architect-only ownership."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Architect", first_line)

    def test_contains_role_gate_redirect(self):
        """Contains a redirect message for non-Architect agents."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(not operating as|ask your.*architect)",
        )

    def test_redirect_mentions_architect(self):
        """Redirect message specifically names the Architect role."""
        content = read_command_file()
        # Find the redirect/rejection line
        lines = content.splitlines()
        redirect_lines = [l for l in lines if "stop" in l.lower() or "instead" in l.lower()]
        combined = " ".join(redirect_lines)
        self.assertIn("Architect", combined)


class TestPMRestrictedFromArchPrefix(unittest.TestCase):
    """Scenario: PM restricted from arch_ prefix

    Given a PM agent session
    When the PM attempts to create an arch_data_layer.md anchor
    Then the command responds that arch_ anchors are Architect-only

    Structural test: the command file documents the three anchor prefix
    types and associates arch_* exclusively with the Technical domain.
    """

    def test_arch_prefix_documented(self):
        """The arch_ prefix is listed in the anchor node types table."""
        content = read_command_file()
        self.assertIn("arch_", content)

    def test_design_prefix_documented(self):
        """The design_ prefix is listed in the anchor node types table."""
        content = read_command_file()
        self.assertIn("design_", content)

    def test_policy_prefix_documented(self):
        """The policy_ prefix is listed in the anchor node types table."""
        content = read_command_file()
        self.assertIn("policy_", content)

    def test_arch_prefix_associated_with_technical(self):
        """arch_* is associated with the Technical domain (Architect-only)."""
        content = read_command_file()
        # The arch_ row should be on the same line as Technical
        arch_lines = [l for l in content.splitlines() if "arch_" in l]
        combined = " ".join(arch_lines)
        self.assertIn("Technical", combined)


class TestNewAnchorUsesTemplateStructure(unittest.TestCase):
    """Scenario: New anchor uses template structure

    Given no anchor node exists for the topic
    When /pl-anchor creates a new anchor node
    Then the file contains purpose and invariants sections
    And the heading prefix matches the anchor type

    Structural test: the command file includes a template with
    required Purpose and Invariants section headings.
    """

    def test_template_contains_purpose_section(self):
        """The anchor template includes a Purpose section heading."""
        content = read_command_file()
        self.assertRegex(content, r"(?im)^#+\s+purpose")

    def test_template_contains_invariants_section(self):
        """The anchor template includes an Invariants section heading."""
        content = read_command_file()
        self.assertRegex(content, r"(?im)invariants")

    def test_required_headings_documented(self):
        """The command file documents that purpose and invariants are required."""
        content = read_command_file()
        lower = content.lower()
        self.assertIn("purpose", lower)
        self.assertIn("invariants", lower)
        # Both should appear in context of "required" checks
        self.assertRegex(content, r"(?i)required.*section.*heading")

    def test_template_includes_heading_prefix_guidance(self):
        """Template shows heading prefix like 'Policy:', 'Architecture:', or 'Design:'."""
        content = read_command_file()
        self.assertIn("Policy:", content)
        self.assertRegex(content, r"(?i)(architecture|design):")


class TestCascadeWarningShowsDependentFeatures(unittest.TestCase):
    """Scenario: Cascade warning shows dependent features

    Given arch_api.md has 3 dependent features
    When /pl-anchor modifies arch_api.md
    Then the agent presents the list of features that will reset to TODO
    And asks for confirmation before committing

    Structural test: the command file documents cascade awareness --
    editing an anchor resets dependents and the agent must verify intent.
    """

    def test_cascade_reset_documented(self):
        """The command file documents that editing resets dependent features."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(reset.*dependent|dependent.*reset|reset.*todo)",
        )

    def test_cascade_awareness_section_present(self):
        """A cascade awareness section or instruction is present."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)cascade")

    def test_impact_verification_before_commit(self):
        """The command instructs the agent to verify impact before committing."""
        content = read_command_file()
        # Should mention verifying or identifying impact before commit
        self.assertRegex(
            content,
            r"(?i)(verify.*intended|identify.*dependent|impact.*list|intended)",
        )

    def test_scan_run_after_edit(self):
        """After editing, the command runs scan.sh to propagate resets."""
        content = read_command_file()
        self.assertIn("scan.sh", content)


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_anchor")
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
                    "test_file": "tools/test_support/test_pl_anchor.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
