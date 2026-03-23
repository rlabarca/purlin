#!/usr/bin/env python3
"""Tests for the /pl-fixture skill command file.

Covers 3 unit test scenarios for the pl_fixture feature.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-fixture.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestAllRolesCanInvokeCommand(unittest.TestCase):
    """Scenario: All roles can invoke the command

    Given any agent role (Architect, Builder, QA, or PM)
    When the user invokes /pl-fixture
    Then the skill executes without a role authorization error

    Structural test: the command file's first line declares 'shared' access
    and does not contain a single-role gate.
    """

    def test_first_line_declares_shared_access(self):
        """First line should declare shared (all roles) access."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("shared", first_line.lower())

    def test_no_single_role_gate(self):
        """No single-role ownership pattern like 'command owner: Builder'."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertNotIn("command owner:", first_line.lower())

    def test_all_roles_mentioned_in_first_line(self):
        """First line should reference 'all roles'."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("all roles", first_line.lower())


class TestContentCoversFixtureLifecycle(unittest.TestCase):
    """Scenario: Content covers fixture lifecycle

    Given the /pl-fixture command file
    When the content is examined
    Then it covers the definition, setup, use, and cleanup phases
    of the fixture lifecycle.

    Structural test: the command file addresses all four lifecycle phases.
    """

    def test_definition_phase_covered(self):
        """Fixture definition guidance is present (tag sections, slug convention)."""
        content = read_command_file()
        # Definition involves how to declare fixture tags in feature specs
        self.assertIn("Fixture Tag", content)
        self.assertIn("Slug Convention", content)

    def test_setup_phase_covered(self):
        """Fixture setup guidance is present (init, add-tag, setup script)."""
        content = read_command_file()
        self.assertIn("fixture init", content)
        self.assertIn("add-tag", content)
        self.assertIn("setup script", content.lower())

    def test_use_phase_covered(self):
        """Fixture usage guidance is present (checkout, detection, resolve)."""
        content = read_command_file()
        # Use phase involves detecting fixture tags and resolving the repo
        self.assertIn("fixture list", content)
        self.assertIn("Fixture Detection", content)

    def test_cleanup_or_immutability_documented(self):
        """Fixture state management is addressed (immutable tags, state construction)."""
        content = read_command_file()
        self.assertIn("immutable", content.lower())
        self.assertIn("State Construction", content)


class TestRoleSpecificSectionsPresented(unittest.TestCase):
    """Scenario: Role-specific sections presented

    Given the /pl-fixture command file
    When each role reads the command
    Then role-specific guidance is presented (Builder sees pre-flight and
    setup workflow, Architect sees design guidance, QA sees awareness).

    Structural test: the command file contains clearly labeled sections
    for each role with relevant content.
    """

    def test_builder_section_with_preflight_and_setup(self):
        """Builder section covers pre-flight detection and setup workflow."""
        content = read_command_file()
        self.assertIn("For Builders", content)
        self.assertIn("Pre-Flight", content)
        self.assertIn("Setup Workflow", content)

    def test_architect_section_with_design_guidance(self):
        """Architect section covers fixture-aware feature design."""
        content = read_command_file()
        self.assertIn("For Architects", content)
        self.assertIn("When to Use Fixtures", content)

    def test_qa_section_with_awareness(self):
        """QA section covers fixture awareness for verification."""
        content = read_command_file()
        self.assertIn("For QA", content)
        self.assertIn("Fixture Awareness", content)

    def test_sections_are_role_headed(self):
        """Each role section uses a heading pattern '## For <Role>:'."""
        content = read_command_file()
        # Verify all three role headings exist as H2 sections
        self.assertRegex(content, r"(?m)^## For Architects:")
        self.assertRegex(content, r"(?m)^## For Builders:")
        self.assertRegex(content, r"(?m)^## For QA:")


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_fixture")
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
                    "test_file": "tools/test_support/test_pl_fixture.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
