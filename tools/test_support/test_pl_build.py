#!/usr/bin/env python3
"""Tests for the /pl-build skill command file.

Covers all 7 unit test scenarios from features/pl_build.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-build.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonBuilder(unittest.TestCase):
    """Scenario: Role gate rejects non-Builder invocation

    Given a non-Builder agent session
    When the agent invokes /pl-build
    Then the command responds with a redirect message to use the Builder agent
    And no implementation work is performed

    Structural test: the command file's first line declares 'Builder' as the
    command owner, and a redirect message is present for non-Builder agents.
    """

    def test_first_line_declares_builder_owner(self):
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Builder", first_line)
        self.assertIn("command owner", first_line.lower())

    def test_redirect_message_for_non_builder(self):
        """Non-Builder agents receive a redirect message."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)not.*operat.*builder.*respond",
        )

    def test_redirect_mentions_builder_agent(self):
        """Redirect message tells the user to use the Builder agent."""
        content = read_command_file()
        self.assertIn("Builder command", content)


class TestNamedFeatureArgumentScopes(unittest.TestCase):
    """Scenario: Named feature argument scopes to specific feature

    Given a Builder agent session
    When /pl-build is invoked with argument "my_feature"
    Then the Builder reads features/my_feature.md
    And implementation targets only that feature

    Structural test: the command file references reading features/<arg>.md
    when an argument is provided.
    """

    def test_references_features_arg_md(self):
        content = read_command_file()
        self.assertRegex(content, r"features/<arg>\.md")

    def test_argument_provided_branch(self):
        """Command has conditional logic for when an argument is provided."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)if.*argument.*provided",
        )

    def test_named_feature_implementation(self):
        """Command instructs to implement the named feature."""
        content = read_command_file()
        self.assertIn("implement the named feature", content.lower())


class TestNoArgumentSelectsHighestPriority(unittest.TestCase):
    """Scenario: No-argument mode selects highest-priority action item

    Given a Builder agent session with no argument
    And /pl-status lists feature_a as highest-priority Builder action
    When /pl-build is invoked
    Then the Builder selects feature_a for implementation

    Structural test: the command file references status.sh or /pl-status
    for finding the highest-priority work item.
    """

    def test_references_status_sh(self):
        content = read_command_file()
        self.assertIn("status.sh", content)

    def test_highest_priority_selection(self):
        """Command mentions selecting the highest-priority item."""
        content = read_command_file()
        self.assertIn("highest-priority", content.lower())

    def test_no_argument_branch(self):
        """Command has conditional logic for when no argument is provided."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)if.*no.*argument.*provided",
        )


class TestTombstonesProcessedFirst(unittest.TestCase):
    """Scenario: Tombstones processed before regular features

    Given features/tombstones/old_feature.md exists
    And features/new_feature.md is in TODO state
    When /pl-build is invoked without arguments
    Then old_feature tombstone is processed before new_feature implementation begins

    Structural test: the command file mentions tombstones and instructs
    to process them before regular feature work.
    """

    def test_references_tombstones_directory(self):
        content = read_command_file()
        self.assertIn("features/tombstones/", content)

    def test_tombstones_before_regular_work(self):
        """Tombstones must be processed before regular features."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)tombstones.*before.*regular",
        )

    def test_tombstone_check_precedes_implementation(self):
        """Tombstone check appears before the implementation protocol section."""
        content = read_command_file()
        tombstone_pos = content.find("tombstones")
        impl_pos = content.find("Per-Feature Implementation Protocol")
        self.assertGreater(impl_pos, tombstone_pos,
                           "Tombstone check must come before implementation protocol")


class TestDeliveryPlanScopesToCurrentPhase(unittest.TestCase):
    """Scenario: Delivery plan scopes to current phase

    Given .purlin/delivery_plan.md exists with Phase 1 IN_PROGRESS containing feature_a
    And Phase 2 PENDING contains feature_b
    When /pl-build is invoked
    Then only feature_a is implemented
    And feature_b is not started

    Structural test: the command file references delivery_plan.md and
    instructs to scope work to the current phase only.
    """

    def test_references_delivery_plan(self):
        content = read_command_file()
        self.assertIn("delivery_plan.md", content)

    def test_scope_to_current_phase(self):
        """Command instructs to scope work to the current phase."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)scope.*current phase",
        )

    def test_phase_completion_halts_session(self):
        """Command instructs to halt after completing a phase."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(halt|stop).*complet.*phase",
        )


class TestStatusTagIsSeparateCommit(unittest.TestCase):
    """Scenario: Status tag is a separate commit

    Given the Builder completes implementation of a feature
    When the status tag commit is created
    Then the status tag commit is separate from the implementation commit
    And the implementation commit does not contain lifecycle tags

    Structural test: the command file explicitly states that the status tag
    must be in a SEPARATE commit.
    """

    def test_step4_heading_says_separate_commit(self):
        content = read_command_file()
        self.assertIn("SEPARATE COMMIT", content)

    def test_step4_has_separate_commit_instruction(self):
        """Step 4 includes a commit command separate from implementation."""
        content = read_command_file()
        self.assertIn("status(scope):", content)

    def test_implementation_commit_no_status_tag(self):
        """Implementation commit explicitly excludes status tags."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)no status tag.*commit|no status tag in this commit",
        )

    def test_separate_commit_after_implementation(self):
        """Status tag step appears after implementation step."""
        content = read_command_file()
        step2_pos = content.find("Step 2 -- Implement")
        step4_pos = content.find("Step 4 -- Status Tag")
        self.assertGreater(step2_pos, -1, "Step 2 heading must exist")
        self.assertGreater(step4_pos, step2_pos,
                           "Step 4 (status tag) must come after Step 2 (implement)")


class TestReVerificationSkipsReImplementation(unittest.TestCase):
    """Scenario: Re-verification skips re-implementation

    Given a feature with has_passing_tests true and no scenario diff
    When /pl-build processes the feature
    Then existing tests are run without re-implementing code
    And the feature is re-tagged upon test passage

    Structural test: the command file references re-verification detection
    with has_passing_tests, scenario_diff, and skip-to-retag logic.
    """

    def test_references_has_passing_tests(self):
        content = read_command_file()
        self.assertIn("has_passing_tests", content)

    def test_references_scenario_diff(self):
        content = read_command_file()
        self.assertIn("scenario_diff", content)

    def test_do_not_re_implement(self):
        """Command explicitly says not to re-implement existing code."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)do not re-implement",
        )

    def test_re_tag_instruction(self):
        """Command instructs to re-tag after tests pass."""
        content = read_command_file()
        self.assertIn("re-tag", content.lower())


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_build")
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
                    "test_file": "tools/test_support/test_pl_build.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
