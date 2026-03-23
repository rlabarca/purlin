#!/usr/bin/env python3
"""Tests for the /pl-delivery-plan skill command file.

Covers all 5 unit test scenarios from features/pl_delivery_plan.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-delivery-plan.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonBuilder(unittest.TestCase):
    """Scenario: Role gate rejects non-Builder invocation

    Given a non-Builder agent (Architect, QA, or PM)
    When the agent invokes /pl-delivery-plan
    Then the skill displays a role rejection message and stops

    Structural test: the command file's first line declares 'Builder'
    as the command owner, which triggers the standard role gate.
    """

    def test_first_line_declares_builder_owner(self):
        """First line must declare Builder as command owner."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Builder", first_line)
        self.assertIn("command owner", first_line.lower())

    def test_role_rejection_message_present(self):
        """A rejection message for non-Builder agents must be present."""
        content = read_command_file()
        self.assertIn("Builder command", content)
        self.assertRegex(
            content,
            r"(?i)(not operating as|ask your builder)",
        )

    def test_rejection_stops_execution(self):
        """The rejection message must instruct the agent to stop."""
        content = read_command_file()
        # Find the rejection block (first few lines)
        lines = content.splitlines()[:10]
        rejection_block = "\n".join(lines).lower()
        self.assertIn("stop", rejection_block)


class TestExistingPlanDisplaysCurrentState(unittest.TestCase):
    """Scenario: Existing plan displays current state

    Given a delivery plan exists at .purlin/delivery_plan.md
    When /pl-delivery-plan is invoked
    Then the skill reads the existing plan and displays phase status
    And shows completion commits for completed phases

    Structural test: the command file describes reading an existing
    delivery_plan.md and showing phase status/completion commits.
    """

    def test_reads_existing_delivery_plan(self):
        """Command must reference reading an existing delivery_plan.md."""
        content = read_command_file()
        self.assertIn("delivery_plan.md", content)
        self.assertRegex(
            content,
            r"(?i)(already exists|plan already|if.*delivery plan.*exists)",
        )

    def test_displays_phase_status(self):
        """Command must describe showing phase status."""
        content = read_command_file()
        # Should mention showing current/completed/remaining phases
        self.assertRegex(
            content,
            r"(?i)(current phase|completed phase|remaining phase)",
        )

    def test_shows_completion_commits(self):
        """Command must reference completion commits for completed phases."""
        content = read_command_file()
        self.assertIn("Completion Commit", content)

    def test_shows_implementation_status(self):
        """Command must describe feature implementation status within phases."""
        content = read_command_file()
        # Should reference TODO / TESTING / COMPLETE status indicators
        has_status_refs = ("TODO" in content and "COMPLETE" in content)
        self.assertTrue(
            has_status_refs,
            "Command file must reference TODO and COMPLETE status indicators",
        )


class TestScopeAssessmentRecommendsPhasing(unittest.TestCase):
    """Scenario: Scope assessment recommends phasing for complex work

    Given a set of features with mixed complexity
    When /pl-delivery-plan assesses scope
    Then it recommends phasing when 3+ features are present
    And it recommends phasing when 2+ HIGH-complexity features are present

    Structural test: the command file describes scope heuristics
    for 3+ features and 2+ HIGH-complexity triggers.
    """

    def test_three_plus_features_heuristic(self):
        """Command must describe the 3+ features phasing trigger."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"3\+\s*features",
        )

    def test_high_complexity_heuristic(self):
        """Command must describe 2+ HIGH-complexity phasing trigger."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"2\+\s*HIGH[- ]complexity",
        )

    def test_scope_assessment_section_present(self):
        """Command must have a scope assessment section with heuristics."""
        content = read_command_file()
        self.assertIn("Scope Assessment Heuristics", content)

    def test_recommends_phasing(self):
        """Command must recommend phasing based on heuristics."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)recommend\s+phasing",
        )


class TestDependencyValidationCatchesCycles(unittest.TestCase):
    """Scenario: Dependency validation catches cycles

    Given a proposed delivery plan with feature dependencies
    When /pl-delivery-plan validates the plan before committing
    Then it runs dependency validation to detect cycles
    And it blocks committing if cycles are detected

    Structural test: the command file describes dependency validation
    and cycle detection before committing.
    """

    def test_validation_gate_present(self):
        """Command must describe a validation gate before committing."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)validation\s+gate",
        )

    def test_cycle_detection_described(self):
        """Command must reference dependency cycle detection."""
        content = read_command_file()
        # The command file must mention cycles in the context of dependencies
        self.assertRegex(
            content,
            r"(?i)(dependency\s+cycles|creates\s+a\s+cycle|cycle)",
        )

    def test_dependency_graph_used_for_validation(self):
        """Command must use dependency_graph.json for validation."""
        content = read_command_file()
        self.assertIn("dependency_graph.json", content)

    def test_blocks_commit_on_cycle(self):
        """Command must describe blocking the commit when cycles are found."""
        content = read_command_file()
        # Validation gate should mention fixing before committing
        self.assertRegex(
            content,
            r"(?i)(fix.*before|only commit after|resolve.*before)",
        )


class TestPhaseSizingCapEnforced(unittest.TestCase):
    """Scenario: Phase sizing cap enforced

    Given a proposed phase breakdown
    When /pl-delivery-plan validates phase sizes
    Then no phase exceeds 2 features

    Structural test: the command file describes the max 2 features
    per phase cap.
    """

    def test_max_two_features_per_phase(self):
        """Command must state max 2 features per phase."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)max\s+\**2\s+features\s+per\s+phase",
        )

    def test_high_complexity_phase_cap(self):
        """Command must limit phases with HIGH-complexity features."""
        content = read_command_file()
        # Max 1 HIGH-complexity feature per phase if another feature is present
        self.assertRegex(
            content,
            r"(?i)max\s+\**1\s+HIGH[- ]complexity",
        )

    def test_dedicated_phase_for_large_features(self):
        """A single HIGH-complexity feature with 5+ scenarios gets its own phase."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)5\+\s*scenarios.*dedicated\s+phase",
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_delivery_plan")
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
                    "test_file": "tools/test_support/test_pl_delivery_plan.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
