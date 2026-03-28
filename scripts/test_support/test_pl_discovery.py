#!/usr/bin/env python3
"""Tests for the /pl-discovery skill command file.

Covers all 5 unit test scenarios from features/pl_discovery.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-discovery.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonQA(unittest.TestCase):
    """Scenario: Role gate rejects non-QA invocation

    Given a Engineer agent session
    When the agent invokes /pl-discovery
    Then the command responds with a redirect message

    Structural test: the command file declares QA ownership and contains
    a redirect message for non-QA agents.
    """

    def test_first_line_declares_qa_ownership(self):
        """Command file declares QA as the mode declaration."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("QA", first_line)
        self.assertIn("purlin mode", first_line.lower())

    def test_redirect_message_present(self):
        """A redirect message instructs non-QA agents to switch to QA mode."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(another mode is active|confirm switch|activates QA mode)",
        )

    def test_stop_instruction_after_redirect(self):
        """The redirect message includes a confirm-switch instruction."""
        content = read_command_file()
        # Should tell the non-QA agent to confirm switch after the redirect
        redirect_match = re.search(r"(?i)(another mode is active|confirm switch)", content)
        self.assertIsNotNone(redirect_match,
                             "Redirect message should include 'confirm switch' instruction")


class TestBugDiscoveryRoutesToBuilder(unittest.TestCase):
    """Scenario: BUG discovery routes to Engineer

    Given a verification failure contradicting an existing scenario
    When the QA agent classifies it as BUG
    Then the discovery entry has Action Required set to Engineer

    Structural test: the command file defines BUG type with routing to Engineer.
    """

    def test_bug_type_defined(self):
        """BUG discovery type is defined in the classification section."""
        content = read_command_file()
        self.assertIn("[BUG]", content)

    def test_bug_routes_to_builder(self):
        """BUG discoveries route to Engineer by default."""
        content = read_command_file()
        # Find the BUG classification and verify it mentions Engineer routing
        bug_section = content[content.find("[BUG]"):]
        # Limit to just the BUG description line/paragraph
        next_type = re.search(r"\[(?:DISCOVERY|INTENT_DRIFT|SPEC_DISPUTE)\]", bug_section[1:])
        if next_type:
            bug_section = bug_section[:next_type.start() + 1]
        self.assertIn("Engineer", bug_section)

    def test_bug_contradicts_existing_scenario(self):
        """BUG type description references contradicting an existing scenario."""
        content = read_command_file()
        bug_section = content[content.find("[BUG]"):]
        next_type = re.search(r"\[(?:DISCOVERY|INTENT_DRIFT|SPEC_DISPUTE)\]", bug_section[1:])
        if next_type:
            bug_section = bug_section[:next_type.start() + 1]
        self.assertRegex(bug_section, r"(?i)contradict")

    def test_action_required_field_in_template(self):
        """Recording format includes Action Required field."""
        content = read_command_file()
        self.assertIn("Action Required", content)


class TestSpecDisputeSuspendsScenario(unittest.TestCase):
    """Scenario: SPEC_DISPUTE suspends scenario

    Given the user disagrees with a scenario's expected behavior
    When the QA agent classifies it as SPEC_DISPUTE
    Then the discovery entry has Action Required set to PM
    And the user is informed the scenario is suspended

    Structural test: the command file defines SPEC_DISPUTE type with PM
    routing and scenario suspension messaging.
    """

    def test_spec_dispute_type_defined(self):
        """SPEC_DISPUTE discovery type is defined."""
        content = read_command_file()
        self.assertIn("[SPEC_DISPUTE]", content)

    def test_spec_dispute_routes_to_architect(self):
        """SPEC_DISPUTE routes to PM by default."""
        content = read_command_file()
        # Find the routing section for SPEC_DISPUTE
        self.assertRegex(content, r"SPEC_DISPUTE.*?PM", re.DOTALL)

    def test_scenario_suspension_mentioned(self):
        """Command instructs agent to inform user scenario is suspended."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)suspend",
        )

    def test_suspension_tied_to_spec_dispute(self):
        """Suspension instruction is specifically associated with SPEC_DISPUTE."""
        content = read_command_file()
        # Find the section after SPEC_DISPUTE is mentioned and check for suspend
        spec_dispute_pos = content.find("SPEC_DISPUTE")
        self.assertGreater(spec_dispute_pos, -1)
        after_spec_dispute = content[spec_dispute_pos:]
        self.assertRegex(after_spec_dispute, r"(?i)suspend")


class TestDiscoverySidecarCreatedWhenAbsent(unittest.TestCase):
    """Scenario: Discovery sidecar file created when absent

    Given no discoveries.md file exists for feature_a
    When a discovery is recorded for feature_a
    Then features/feature_a.discoveries.md is created
    And it contains the proper heading and discovery entry

    Structural test: the command file instructs creation of the sidecar
    file with the correct naming convention and heading format.
    """

    def test_sidecar_naming_convention(self):
        """Sidecar file uses <name>.discoveries.md naming convention."""
        content = read_command_file()
        self.assertRegex(content, r"discoveries\.md")

    def test_creates_file_if_absent(self):
        """Command instructs creation of sidecar when file does not exist."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)creat(e|ing).*?(if|when).*?(absent|not exist|doesn)",
        )

    def test_file_heading_format_specified(self):
        """Sidecar file has the specified heading format."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"#\s*User Testing Discoveries",
        )

    def test_recording_format_includes_required_fields(self):
        """Recording format includes all required entry fields."""
        content = read_command_file()
        required_fields = [
            "Scenario",
            "Observed Behavior",
            "Expected Behavior",
            "Action Required",
            "Status",
        ]
        for field in required_fields:
            self.assertIn(field, content,
                          f"Recording format missing required field: {field}")


class TestPruningMovesToCompanionFile(unittest.TestCase):
    """Scenario: Pruning moves entry to companion file

    Given a RESOLVED discovery exists in feature_a.discoveries.md
    When the discovery is pruned
    Then the entry is removed from the sidecar file
    And a one-liner summary is added to feature_a.impl.md

    Structural test: the command file defines the pruning protocol with
    removal from sidecar and one-liner addition to companion file.
    """

    def test_pruning_protocol_section_exists(self):
        """Command file has a pruning protocol section."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)prun(e|ing)\s*(protocol|section)?")

    def test_removal_from_sidecar(self):
        """Pruning instructs removal of entry from discoveries.md."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)remove.*?discoveries\.md",
            "Pruning should instruct removal from discoveries.md",
        )

    def test_one_liner_added_to_companion(self):
        """Pruning adds a one-liner summary to the companion (.impl.md) file."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(one-liner|one.liner).*?(companion|impl\.md)",
        )

    def test_lifecycle_includes_pruned_status(self):
        """Discovery lifecycle includes PRUNED as final status."""
        content = read_command_file()
        self.assertIn("PRUNED", content)

    def test_no_bracket_tags_in_pruned_entry(self):
        """Pruned entries in companion file must not use bracket tags."""
        content = read_command_file()
        # The command should explicitly mention no bracket tags
        self.assertRegex(
            content,
            r"(?i)(no|NO)\s*bracket",
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_discovery")
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
                    "test_file": "tools/test_support/test_pl_discovery.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
