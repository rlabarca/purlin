#!/usr/bin/env python3
"""Tests for the /pl-tombstone skill command file.

Covers all 4 unit test scenarios from features/pl_tombstone.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-tombstone.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonPMInvocation(unittest.TestCase):
    """Scenario: Role gate rejects non-PM invocation

    Given a Engineer agent session
    When the agent invokes /pl-tombstone
    Then the command responds with a redirect message

    Structural test: the command file's first line declares PM as
    the mode declaration, which means non-PM agents will be redirected.
    """

    def test_first_line_declares_engineer_owner(self):
        """First line must contain the Engineer mode declaration."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Purlin mode: Engineer", first_line,
                       "First line must declare Engineer as mode")

    def test_redirect_message_for_non_architect(self):
        """Command file must include a redirect message for non-PM agents."""
        content = read_command_file()
        self.assertIn("another mode is active", content,
                       "Must include redirect guidance for non-PM agents")

    def test_redirect_mentions_architect_role(self):
        """Redirect message must tell non-PM agents to ask an PM."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(another mode is active|confirm switch)",
            "Redirect must instruct non-PM to ask PM to run /pl-tombstone",
        )


class TestImpactAnalysisShowsDependentFeatures(unittest.TestCase):
    """Scenario: Impact analysis shows dependent features

    Given feature_a is a prerequisite for feature_b and feature_c
    When /pl-tombstone is invoked for feature_a
    Then feature_b and feature_c are listed as impacted

    Structural test: the command file references the dependency graph
    and describes identifying features that list the retiring feature
    as a prerequisite.
    """

    def test_dependency_graph_referenced(self):
        """Command file must reference the dependency graph for impact analysis."""
        content = read_command_file()
        self.assertIn("dependency_graph.json", content,
                       "Must reference dependency_graph.json for impact analysis")

    def test_prerequisite_impact_described(self):
        """Command file must describe identifying features that depend on the retiring feature."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)prerequisite",
            "Must describe checking for prerequisite dependencies",
        )

    def test_impact_list_presented_to_user(self):
        """Command file must describe presenting the impact list before proceeding."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)present.*impact|impact.*list.*user",
            "Must describe presenting the impact list to the user",
        )

    def test_user_confirmation_required(self):
        """Command file must require user confirmation before proceeding."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(user confirmation|after.*confirm)",
            "Must require user confirmation before creating the tombstone",
        )


class TestTombstoneCreatedBeforeFeatureDeletion(unittest.TestCase):
    """Scenario: Tombstone created before feature deletion

    Given the user confirms retirement of feature_a
    When the tombstone workflow executes
    Then features/tombstones/feature_a.md is created first
    And features/feature_a.md is deleted second

    Structural test: the command file enforces tombstone-before-deletion
    ordering and includes the canonical tombstone format.
    """

    def test_tombstone_before_deletion_rule(self):
        """Command file must state that tombstones are created before the feature file is moved."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)tombstone.*MUST.*created.*before.*moved|MUST.*created before.*feature file.*moved",
            "Must enforce tombstone-before-move ordering",
        )

    def test_tombstone_path_is_tombstones_directory(self):
        """Command file must specify the features/tombstones/ directory for tombstone files."""
        content = read_command_file()
        self.assertIn("features/tombstones/", content,
                       "Must specify features/tombstones/ as the tombstone location")

    def test_canonical_tombstone_format_present(self):
        """Command file must include the canonical tombstone format template."""
        content = read_command_file()
        self.assertIn("# TOMBSTONE:", content,
                       "Must include the canonical tombstone format heading")
        self.assertIn("## Files to Delete", content,
                       "Must include Files to Delete section in tombstone format")
        self.assertIn("## Dependencies to Check", content,
                       "Must include Dependencies to Check section in tombstone format")

    def test_workflow_order_create_then_move(self):
        """In the numbered workflow, tombstone creation must precede feature move."""
        content = read_command_file()
        create_pos = content.find("create the tombstone content at")
        move_pos = content.find("Move feature")
        self.assertGreater(create_pos, -1, "Tombstone creation step must exist")
        self.assertGreater(move_pos, create_pos,
                           "Move step must come after tombstone creation step")


class TestUnimplementedFeatureDeletedWithoutTombstone(unittest.TestCase):
    """Scenario: Unimplemented feature deleted without tombstone

    Given feature_a was specced but no implementation code exists
    When /pl-tombstone is invoked for feature_a
    Then the feature file is deleted directly
    And no tombstone file is created

    Structural test: the command file describes the special case where
    unimplemented features skip tombstone creation.
    """

    def test_no_code_shortcut_described(self):
        """Command file must describe the shortcut for features with no implementation."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)specced but never implemented|no code exists",
            "Must describe the shortcut path for unimplemented features",
        )

    def test_tombstone_unnecessary_for_unimplemented(self):
        """Command file must state tombstone is unnecessary when no code exists."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)tombstone.*unnecessary|delete.*directly",
            "Must state tombstone is unnecessary for unimplemented features",
        )

    def test_not_implemented_noted_in_commit(self):
        """Command file must describe noting 'not implemented' in the commit message."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)not implemented.*commit",
            "Must note 'not implemented' in the commit message for this case",
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_tombstone")
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
                    "test_file": "tools/test_support/test_pl_tombstone.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
