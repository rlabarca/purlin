#!/usr/bin/env python3
"""Tests for the /pl-release-step skill command file.

Covers all 11 unit test scenarios from features/pl_release_step.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-release-step.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestCreateValidLocalStep(unittest.TestCase):
    """Scenario: Create valid local step

    Given local_steps.json is absent and config.json is absent,
    When manage_step.py create --id "my_step" --name "My Step" --desc "Does something" is run,
    Then the tool exits with code 0,
    And local_steps.json contains the new step,
    And config.json contains the new entry.

    Structural test: the command file delegates create operations to
    manage_step.py with all required flags, and writes to both files.
    """

    def test_create_operation_documented(self):
        """The command file documents the create operation."""
        content = read_command_file()
        self.assertIn("create", content.lower())

    def test_create_delegates_to_manage_step(self):
        """The create flow invokes manage_step.py create."""
        content = read_command_file()
        self.assertRegex(content, r"manage_step\.py\s+create")

    def test_create_passes_id_name_desc_flags(self):
        """The create invocation includes --id, --name, and --desc flags."""
        content = read_command_file()
        self.assertIn("--id", content)
        self.assertIn("--name", content)
        self.assertIn("--desc", content)

    def test_create_writes_to_both_files(self):
        """The create operation references both local_steps.json and config.json."""
        content = read_command_file()
        self.assertIn("local_steps.json", content)
        self.assertIn("config.json", content)


class TestRejectPurlinPrefixOnCreate(unittest.TestCase):
    """Scenario: Reject purlin. prefix on create

    Given local_steps.json is absent,
    When manage_step.py create --id "purlin.custom" is run,
    Then the tool exits with code 1 and stderr identifies the reserved prefix.

    Structural test: validation is enforced by the CLI tool which the command
    file delegates to. The command file must invoke the tool (not bypass it).
    """

    def test_delegates_to_cli_tool_not_direct_json(self):
        """Command file invokes the CLI tool rather than writing JSON directly."""
        content = read_command_file()
        self.assertRegex(content, r"manage_step\.py")
        # Should NOT contain raw JSON write instructions
        self.assertNotIn("json.dump", content)

    def test_tool_path_uses_tools_root(self):
        """The tool path uses TOOLS_ROOT variable for correct resolution."""
        content = read_command_file()
        self.assertIn("TOOLS_ROOT", content)


class TestRejectDuplicateLocalIdOnCreate(unittest.TestCase):
    """Scenario: Reject duplicate local ID on create

    Given local_steps.json contains a step with id: "existing_step",
    When manage_step.py create --id "existing_step" is run,
    Then the tool exits with code 1 and stderr identifies the conflict as local.

    Structural test: the command file delegates all validation to the CLI tool,
    which handles duplicate detection internally.
    """

    def test_all_create_flows_go_through_cli(self):
        """Every create path calls manage_step.py, ensuring validation is centralized."""
        content = read_command_file()
        # The create section must reference the CLI tool
        create_section = content[content.lower().find("**create"):content.lower().find("**modify")]
        self.assertIn("manage_step.py", create_section)

    def test_dry_run_before_actual_write(self):
        """Create flow runs --dry-run first for user preview."""
        content = read_command_file()
        self.assertIn("--dry-run", content)


class TestRejectDuplicateGlobalIdOnCreate(unittest.TestCase):
    """Scenario: Reject duplicate global ID on create

    Given global_steps.json contains a step with id: "purlin.push_to_remote",
    When manage_step.py create --id "purlin.push_to_remote" is run,
    Then the tool exits with code 1.

    Structural test: global step conflict detection is handled by the CLI tool.
    The command file must not bypass the tool for any create operation.
    """

    def test_no_direct_json_manipulation_in_create(self):
        """The command file does not manipulate JSON directly for create."""
        content = read_command_file()
        # No patterns suggesting direct file writing
        self.assertNotIn("open(", content)
        self.assertNotIn("write(", content)

    def test_create_section_references_cli_execution(self):
        """The create section uses the CLI tool path with create subcommand."""
        content = read_command_file()
        self.assertRegex(content, r"manage_step\.py\s+create\s+--dry-run")


class TestModifyExistingStepName(unittest.TestCase):
    """Scenario: Modify existing step name

    Given local_steps.json contains a step with id: "my_step",
    When manage_step.py modify my_step --name "New Name" is run,
    Then the tool exits with code 0 and local_steps.json is updated.

    Structural test: the command file documents the modify operation and
    delegates to the CLI tool with field-specific flags.
    """

    def test_modify_operation_documented(self):
        """The command file documents the modify operation."""
        content = read_command_file()
        self.assertIn("modify", content.lower())

    def test_modify_delegates_to_manage_step(self):
        """The modify flow invokes manage_step.py modify."""
        content = read_command_file()
        self.assertRegex(content, r"manage_step\.py\s+modify")

    def test_modify_walks_through_each_field(self):
        """The modify flow prompts for each field individually."""
        content = read_command_file()
        lower = content.lower()
        self.assertIn("friendly name", lower)
        self.assertIn("description", lower)
        self.assertIn("code", lower)
        self.assertIn("agent instructions", lower)

    def test_modify_preserves_unchanged_fields(self):
        """The modify section instructs keeping existing values when Enter is pressed."""
        content = read_command_file()
        # Should mention keeping/unchanged for fields not modified
        self.assertRegex(content, r"(?i)(keep|unchanged|enter)")


class TestModifyClearsOptionalField(unittest.TestCase):
    """Scenario: Modify clears optional field

    Given local_steps.json contains a step with code: "echo hello",
    When manage_step.py modify my_step --clear-code is run,
    Then the tool exits with code 0 and code is set to null.

    Structural test: the command file documents the "clear to null" option
    for code and agent_instructions fields.
    """

    def test_clear_to_null_option_documented(self):
        """The modify section offers a 'clear to null' option."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)clear.*null")

    def test_clear_option_for_code_and_agent_instructions(self):
        """Both code and agent_instructions have clear options."""
        content = read_command_file()
        lower = content.lower()
        # The modify section should mention clearing for both optional fields
        self.assertIn("code", lower)
        self.assertIn("agent_instructions", lower) or self.assertIn("agent instructions", lower)


class TestDeleteStepRemovesFromBothFiles(unittest.TestCase):
    """Scenario: Delete step removes from both files

    Given local_steps.json contains a step with id: "my_step",
    And config.json contains the corresponding entry,
    When manage_step.py delete my_step is run,
    Then both files have the entry removed.

    Structural test: the command file documents the delete operation and
    warns about removal from both files.
    """

    def test_delete_operation_documented(self):
        """The command file documents the delete operation."""
        content = read_command_file()
        self.assertIn("delete", content.lower())

    def test_delete_delegates_to_manage_step(self):
        """The delete flow invokes manage_step.py delete."""
        content = read_command_file()
        self.assertRegex(content, r"manage_step\.py\s+delete")

    def test_delete_warns_about_both_files(self):
        """The delete section warns about removal from both files."""
        content = read_command_file()
        self.assertIn("local_steps.json", content)
        self.assertIn("config.json", content)
        self.assertRegex(content, r"(?i)remove.*both.*local_steps\.json.*config\.json|remove.*local_steps\.json.*config\.json")

    def test_delete_requires_exact_id_confirmation(self):
        """The delete section asks user to type the step ID exactly."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)confirm.*typing.*step\s*ID\s*exactly")


class TestModifyNonExistentStep(unittest.TestCase):
    """Scenario: Modify non-existent step

    Given local_steps.json does not contain a step with id: "ghost_step",
    When manage_step.py modify ghost_step --name "New Name" is run,
    Then the tool exits with code 1 and stderr contains "step not found".

    Structural test: the command file delegates to the CLI tool which
    handles the not-found error. The command file lists steps for selection
    when no ID is provided.
    """

    def test_modify_lists_steps_when_no_id(self):
        """When no step ID is provided, the modify flow lists current steps."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)list.*step|step.*list|read.*local_steps")

    def test_modify_error_handled_by_cli(self):
        """The modify flow delegates to manage_step.py which reports errors."""
        content = read_command_file()
        self.assertRegex(content, r"manage_step\.py\s+modify")


class TestDryRunDoesNotModifyFiles(unittest.TestCase):
    """Scenario: Dry-run does not modify files

    Given local_steps.json is absent,
    When manage_step.py create --id "my_step" --name "My Step" --desc "Desc" --dry-run is run,
    Then local_steps.json is not created and stdout contains [DRY RUN].

    Structural test: the command file uses --dry-run for user preview before
    the actual write, and asks for confirmation.
    """

    def test_dry_run_flag_used_in_create(self):
        """The create flow uses --dry-run for preview."""
        content = read_command_file()
        self.assertIn("--dry-run", content)

    def test_confirmation_before_actual_write(self):
        """The command file asks for user confirmation after dry-run."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)confirm")

    def test_dry_run_precedes_actual_execution(self):
        """The --dry-run call appears before the non-dry-run execution in create."""
        content = read_command_file()
        # Find the create section
        create_start = content.lower().find("**create")
        modify_start = content.lower().find("**modify")
        if create_start > -1 and modify_start > create_start:
            create_section = content[create_start:modify_start]
            dry_pos = create_section.find("--dry-run")
            confirm_pos = create_section.lower().find("confirm")
            self.assertGreater(dry_pos, -1, "--dry-run not found in create section")
            self.assertGreater(confirm_pos, dry_pos,
                               "Confirmation must come after --dry-run preview")


class TestModifyWithNoFieldFlagsFails(unittest.TestCase):
    """Scenario: Modify with no field flags fails

    Given local_steps.json contains a step with id: "my_step",
    When manage_step.py modify my_step is run with no field flags,
    Then the tool exits with code 1.

    Structural test: the command file's modify flow walks through each field,
    checks if anything changed, and only proceeds if changes were made.
    """

    def test_no_changes_detection(self):
        """The modify flow detects when no fields changed."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)no\s*(fields\s*)?change")

    def test_modify_only_sends_changed_fields(self):
        """The modify flow passes only changed fields to the CLI tool."""
        content = read_command_file()
        self.assertRegex(content, r"(?i)changed\s*fields\s*only")


class TestMutuallyExclusiveFlagsRejected(unittest.TestCase):
    """Scenario: Mutually exclusive flags rejected

    Given local_steps.json contains a step with code: "echo hi",
    When manage_step.py modify my_step --code "echo bye" --clear-code is run,
    Then the tool exits with code 1.

    Structural test: mutual exclusivity is enforced by the CLI tool. The
    command file's modify flow separates set-value and clear-value as
    distinct choices, making it structurally unlikely to produce both flags.
    """

    def test_clear_is_separate_option_from_set(self):
        """The modify flow presents 'clear to null' as a distinct option."""
        content = read_command_file()
        # The modify section should have clear as a separate option
        self.assertRegex(content, r"(?i)clear\s*(to\s*)?null")

    def test_validation_delegated_to_cli(self):
        """All validation (including mutual exclusivity) runs through the CLI tool."""
        content = read_command_file()
        # The command file should reference the tool, not implement validation
        self.assertRegex(content, r"manage_step\.py")
        # No argparse or validation logic in the markdown
        self.assertNotIn("argparse", content)


class TestCommandFileRoleAndStructure(unittest.TestCase):
    """Additional structural tests for command file integrity.

    These verify the command file is properly owned by the Architect role
    and follows the expected Purlin command structure.
    """

    def test_architect_role_ownership(self):
        """The command file is owned by the Architect role."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Architect", first_line)

    def test_path_resolution_section_present(self):
        """The command file includes the standard Path Resolution section."""
        content = read_command_file()
        self.assertIn("Path Resolution", content)

    def test_tools_root_resolution(self):
        """The command file resolves TOOLS_ROOT from config.json."""
        content = read_command_file()
        self.assertIn("tools_root", content)
        self.assertIn(".purlin/config.json", content)

    def test_all_three_operations_present(self):
        """All three operations (create, modify, delete) are documented."""
        content = read_command_file()
        self.assertIn("**create", content.lower())
        self.assertIn("**modify", content.lower())
        self.assertIn("**delete", content.lower())


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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_release_step")
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
                    "test_file": "tools/test_support/test_pl_release_step.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
