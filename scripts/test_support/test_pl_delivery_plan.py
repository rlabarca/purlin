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


class TestRoleGateRejectsNonEngineer(unittest.TestCase):
    """Scenario: Role gate rejects non-Engineer invocation

    Given a non-Engineer agent (PM, QA, or PM)
    When the agent invokes /pl-delivery-plan
    Then the skill displays a role rejection message and stops

    Structural test: the command file's first line declares 'Engineer'
    as the mode declaration, which triggers the standard role gate.
    """

    def test_first_line_declares_builder_owner(self):
        """First line must declare Engineer as mode."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Engineer", first_line)
        self.assertIn("purlin mode", first_line.lower())

    def test_role_rejection_message_present(self):
        """A rejection message for non-Engineer agents must be present."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(activates Engineer mode|another mode is active|confirm switch)",
        )

    def test_rejection_stops_execution(self):
        """The rejection message must instruct the agent to confirm switch."""
        content = read_command_file()
        # Find the rejection block (first few lines)
        lines = content.splitlines()[:10]
        rejection_block = "\n".join(lines).lower()
        self.assertIn("confirm switch", rejection_block)


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

    Given the Engineer's model resolves to a context tier with max_features_per_phase of N
    And N+1 features assigned to a single phase
    When /pl-delivery-plan validates the plan
    Then the phase is split to respect the tier-derived max features per phase

    Structural test: the command file describes tier-derived per-phase caps.
    """

    def test_tier_derived_max_features_per_phase(self):
        """Command must describe tier-derived max features per phase (Standard: 2, Extended: 5)."""
        content = read_command_file()
        # The tier defaults table must list both Standard and Extended caps
        self.assertRegex(
            content,
            r"Standard.*2|2.*Standard",
        )
        self.assertRegex(
            content,
            r"Extended.*5|5.*Extended",
        )

    def test_high_complexity_phase_cap(self):
        """Command must limit phases with HIGH-complexity features per tier."""
        content = read_command_file()
        # Tier table has Standard: 1, Extended: 2 for HIGH-complexity
        self.assertIn("Max HIGH-complexity per phase", content)

    def test_dedicated_phase_for_large_features(self):
        """A single HIGH-complexity feature with tier-dependent threshold gets its own phase."""
        content = read_command_file()
        # Standard: 5+, Extended: 8+
        self.assertRegex(
            content,
            r"(?i)5\+.*Standard|Standard.*5\+",
        )
        self.assertRegex(
            content,
            r"(?i)8\+.*Extended|Extended.*8\+",
        )


class TestExtendedContextTierIncreasesPhaseCapacity(unittest.TestCase):
    """Scenario: Extended context tier increases phase capacity

    Given the Engineer's model is "claude-opus-4-6[1m]" with context_window_tokens 1000000
    And 5 features in TODO state with no HIGH-complexity features
    When /pl-delivery-plan creates a plan
    Then the plan uses the Extended tier defaults
    And all 5 features fit in a single phase

    Structural test: the command file describes context tier resolution and
    the Extended tier with higher caps.
    """

    def test_context_tier_resolution_described(self):
        """Command must describe how to resolve context tier from model config."""
        content = read_command_file()
        self.assertIn("context_window_tokens", content)
        self.assertRegex(
            content,
            r"(?i)context\s+tier\s+resolution",
        )

    def test_extended_tier_has_higher_caps(self):
        """Extended tier must allow more features per phase than Standard."""
        content = read_command_file()
        # Extended tier allows 5 features per phase vs Standard's 2
        self.assertIn("Extended", content)
        self.assertRegex(
            content,
            r"Extended.*>200K|>200K.*Extended",
        )

    def test_tier_resolution_uses_model_lookup(self):
        """Tier resolution must look up the Engineer model in the models array."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)model\s+ID\s+in.*models",
        )


class TestPhaseSizingOverrideTakesPrecedence(unittest.TestCase):
    """Scenario: Phase sizing override takes precedence

    Given the Engineer's model resolves to the Extended tier
    And the agent config contains phase_sizing with max_features_per_phase of 3
    When /pl-delivery-plan creates a plan with 4 features
    Then the plan splits into phases of at most 3 features each
    And the override value takes precedence over the Extended tier default of 5

    Structural test: the command file describes the phase_sizing override mechanism.
    """

    def test_phase_sizing_override_described(self):
        """Command must describe the phase_sizing override block."""
        content = read_command_file()
        self.assertIn("phase_sizing", content)
        self.assertRegex(
            content,
            r"(?i)(override|precedence|take[s]?\s+precedence)",
        )

    def test_override_keys_listed(self):
        """Command must list override keys (max_features_per_phase, etc.)."""
        content = read_command_file()
        self.assertIn("max_features_per_phase", content)


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
