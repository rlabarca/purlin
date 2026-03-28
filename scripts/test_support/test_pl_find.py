#!/usr/bin/env python3
"""Tests for the /pl-find skill command file.

Covers all 3 unit test scenarios from features/pl_find.md.
Since skills are agent instruction files (not executable code), these
tests verify structural properties of the command file that ensure
correct runtime behavior.
"""

import os
import json
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(SCRIPT_DIR, "../../")))
from tools.bootstrap import detect_project_root

PROJECT_ROOT = detect_project_root(SCRIPT_DIR)
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-find.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestTopicFoundInExistingFeatureSpec(unittest.TestCase):
    """Scenario: Topic found in existing feature spec

    Given features/auth_flow.md contains scenarios about authentication
    When /pl-find is invoked with topic "authentication"
    Then the output identifies features/auth_flow.md as covering the topic

    Structural test: the command file instructs the agent to search the
    features/ directory and report which file, section, and scenario cover
    the topic.
    """

    def test_searches_features_directory(self):
        """Command file instructs searching features/ directory."""
        content = read_command_file()
        self.assertIn("features/", content)

    def test_reports_file_section_scenario(self):
        """Command file instructs reporting file, section, and scenario."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("file", content_lower)
        self.assertIn("section", content_lower)
        self.assertIn("scenario", content_lower)

    def test_identifies_existing_feature_spec_coverage(self):
        """Command file describes identifying when a feature spec covers the topic."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("existing feature spec", content_lower)


class TestTopicFoundOnlyInInstructionFiles(unittest.TestCase):
    """Scenario: Topic found only in instruction files

    Given instructions/BUILDER_BASE.md mentions "commit discipline"
    And no feature spec covers commit discipline
    When /pl-find is invoked with topic "commit discipline"
    Then the output notes coverage is in instruction files only
    And recommends whether a feature spec is needed

    Structural test: the command file instructs the agent to search
    instruction files and provide a recommendation about next action.
    """

    def test_searches_instructions_directory(self):
        """Command file instructs searching instructions/ directory."""
        content = read_command_file()
        self.assertIn("instructions/", content)

    def test_describes_instruction_file_only_coverage(self):
        """Command file has logic for when topic is only in instruction files."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("instruction file", content_lower)

    def test_provides_recommendation(self):
        """Command file instructs providing a recommendation for next steps."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("recommendation", content_lower)


class TestTopicNotFoundAnywhere(unittest.TestCase):
    """Scenario: Topic not found anywhere

    Given no files mention "quantum computing"
    When /pl-find is invoked with topic "quantum computing"
    Then the output reports no coverage found
    And recommends creating a new spec if applicable

    Structural test: the command file describes a "not found" path and
    recommends creating a new spec when appropriate.
    """

    def test_mentions_new_spec_creation(self):
        """Command file mentions creating a new spec as a possible recommendation."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("new spec", content_lower)

    def test_covers_already_covered_case(self):
        """Command file includes 'already covered' as a possible outcome."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("already covered", content_lower)

    def test_mentions_anchor_node_update(self):
        """Command file includes anchor node update as a possible recommendation."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("anchor node", content_lower)

    def test_uses_search_tools(self):
        """Command file instructs using Glob and Grep for searching."""
        content = read_command_file()
        self.assertIn("Glob", content)
        self.assertIn("Grep", content)


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_find")
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
                    "test_file": "tools/test_support/test_pl_find.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
