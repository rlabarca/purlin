#!/usr/bin/env python3
"""Tests for the /pl-spec skill command file.

Covers all 5 unit test scenarios from features/pl_spec.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-spec.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonPMInvocation(unittest.TestCase):
    """Scenario: Role gate rejects non-PM/PM invocation

    Given a Engineer agent session
    When the agent invokes /pl-spec
    Then the command responds with a redirect message
    And no spec file is created or modified

    Structural test: the command file declares PM and PM as owners
    and includes a redirect message for other roles.
    """

    def test_first_line_declares_pm_architect_owner(self):
        """First line must declare PM, PM as modes."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("PM", first_line,
                       "First line must declare PM as a mode declaration")
        self.assertIn("PM", first_line,
                       "First line must declare PM as a mode declaration")

    def test_redirect_message_for_non_owner(self):
        """Command file must include a redirect message for non-PM/PM agents."""
        content = read_command_file()
        self.assertIn("another mode is active", content,
                       "Must include redirect guidance for non-PM/PM agents")

    def test_redirect_mentions_correct_roles(self):
        """Redirect message must mention PM mode activation."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(activates PM mode|another mode is active|confirm switch)",
            "Redirect must instruct non-owner about PM mode activation",
        )


class TestTopicDiscoveryFindsExistingSpec(unittest.TestCase):
    """Scenario: Topic discovery finds existing spec

    Given a feature spec exists at features/my_feature.md
    When /pl-spec is invoked with argument "my_feature"
    Then the existing spec is opened for review
    And gaps are identified and proposed to the user

    Structural test: the command file instructs running /pl-find first
    and describes the update workflow for existing specs.
    """

    def test_runs_pl_find_first(self):
        """Command file must instruct running /pl-find before authoring."""
        content = read_command_file()
        self.assertIn("/pl-find", content,
                       "Must instruct running /pl-find to discover existing specs")

    def test_describes_update_workflow(self):
        """Command file must describe updating an existing spec."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("updating", content_lower,
                       "Must describe the updating workflow for existing specs")

    def test_identifies_gaps(self):
        """Command file must instruct identifying gaps in existing specs."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("gaps", content_lower,
                       "Must instruct identifying gaps in the existing spec")

    def test_requires_user_confirmation(self):
        """Command file must require user confirmation before applying changes."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("user confirmation", content_lower,
                       "Must require user confirmation before applying changes")


class TestNewSpecUsesTemplateStructure(unittest.TestCase):
    """Scenario: New spec uses template structure

    Given no feature spec exists for the topic
    When /pl-spec creates a new feature file
    Then the file contains overview, requirements, and scenarios sections
    And scenario headings use four-hash format
    And a lifecycle tag is present

    Structural test: the command file's template contains the required
    sections and uses the four-hash scenario heading format.
    """

    def test_template_has_overview_section(self):
        """Command file template must include an overview section heading."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)##.*overview",
            "Template must include an overview section heading",
        )

    def test_template_has_requirements_section(self):
        """Command file template must include a requirements section heading."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)##.*requirements",
            "Template must include a requirements section heading",
        )

    def test_template_has_scenarios_section(self):
        """Command file template must include a scenarios section heading."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)##.*scenarios",
            "Template must include a scenarios section heading",
        )

    def test_scenario_headings_use_four_hash(self):
        """Command file must enforce four-hash scenario heading format."""
        content = read_command_file()
        self.assertIn("#### Scenario:", content,
                       "Template must use four-hash #### for scenario headings")


class TestCategoryScanPreventsDuplicateCategories(unittest.TestCase):
    """Scenario: Category scan prevents duplicate categories

    Given dependency_graph.json contains category "Agent Skills"
    When /pl-spec creates a spec for a slash command feature
    Then the spec uses category "Agent Skills"
    And no new category is invented

    Structural test: the command file instructs scanning
    dependency_graph.json for existing categories and has rules
    about preferring existing categories.
    """

    def test_scans_dependency_graph_for_categories(self):
        """Command file must instruct scanning dependency_graph.json."""
        content = read_command_file()
        self.assertIn("dependency_graph.json", content,
                       "Must instruct scanning dependency_graph.json for existing categories")

    def test_agent_skills_category_for_slash_commands(self):
        """Command file must specify Agent Skills for slash command features."""
        content = read_command_file()
        self.assertIn("Agent Skills", content,
                       "Must specify Agent Skills category for slash command features")

    def test_prefers_existing_categories(self):
        """Command file must state preference for existing categories."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("prefer existing categories", content_lower,
                       "Must instruct preferring existing categories over new ones")


class TestPrerequisiteChecklistEnforcedForUIFeatures(unittest.TestCase):
    """Scenario: Prerequisite checklist enforced for UI features

    Given the new feature renders HTML/CSS output
    When /pl-spec creates the spec
    Then relevant design_*.md anchors are declared as prerequisites

    Structural test: the command file includes a prerequisite checklist
    that maps UI/HTML/CSS features to design_*.md anchor prerequisites.
    """

    def test_prerequisite_checklist_present(self):
        """Command file must contain a prerequisite checklist section."""
        content = read_command_file()
        self.assertIn("Prerequisite Checklist", content,
                       "Must contain a Prerequisite Checklist section")

    def test_ui_features_map_to_design_anchors(self):
        """Command file must map UI/HTML/CSS features to design_*.md anchors."""
        content = read_command_file()
        self.assertIn("design_*.md", content,
                       "Must reference design_*.md anchors for UI features")

    def test_html_css_triggers_design_prerequisite(self):
        """Command file must mention HTML/CSS as triggers for design prerequisites."""
        content = read_command_file()
        content_lower = content.lower()
        self.assertIn("html", content_lower,
                       "Must mention HTML as a trigger for design prerequisites")
        self.assertIn("css", content_lower,
                       "Must mention CSS as a trigger for design prerequisites")

    def test_arch_anchors_for_data_features(self):
        """Command file must also map data features to arch_*.md anchors."""
        content = read_command_file()
        self.assertIn("arch_*.md", content,
                       "Must reference arch_*.md anchors for data features")


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_spec")
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
                    "test_file": "tools/test_support/test_pl_spec.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
