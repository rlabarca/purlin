#!/usr/bin/env python3
"""Tests for the /pl-override-edit skill command file.

Covers all 4 unit test scenarios from features/pl_override_edit.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-override-edit.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestBuilderCannotEditQAOverrides(unittest.TestCase):
    """Scenario: Builder cannot edit QA overrides

    Given a Builder agent session
    When the Builder attempts to edit QA_OVERRIDES.md
    Then the command declines and names the QA role as the owner

    Structural test: the command file contains role-scoping rules that
    restrict Builder to BUILDER_OVERRIDES.md only and name the owning
    role for other override files.
    """

    def test_builder_restricted_to_builder_overrides(self):
        """Builder role instruction limits editing to BUILDER_OVERRIDES.md only."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)builder.*edit\s+only.*BUILDER_OVERRIDES",
            "Must state Builder may edit ONLY BUILDER_OVERRIDES.md",
        )

    def test_builder_decline_names_owner(self):
        """Builder instruction says to decline other targets and name the owner."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)decline.*name.*owner",
            "Must instruct Builder to decline non-own targets and name the owner",
        )

    def test_qa_overrides_has_qa_owner(self):
        """QA_OVERRIDES.md is explicitly scoped to the QA role."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)QA.*edit\s+only.*QA_OVERRIDES",
            "Must state QA may edit ONLY QA_OVERRIDES.md",
        )

    def test_role_scoped_declaration_in_first_line(self):
        """First line declares the command as role-scoped."""
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("role-scoped", first_line.lower(),
                       "First line must declare the command as role-scoped")


class TestConflictScanDetectsContradiction(unittest.TestCase):
    """Scenario: Conflict scan detects contradiction

    Given BUILDER_OVERRIDES.md contains a rule contradicting BUILDER_BASE.md
    When /pl-override-edit runs the conflict scan
    Then a CONFLICT finding is reported with cited text from both files

    Structural test: the command file defines a three-level classification
    system (CONFLICT, WARNING, INFO) with citation requirements for each finding.
    """

    def test_conflict_classification_present(self):
        """Command file must define the [CONFLICT] classification level."""
        content = read_command_file()
        self.assertIn("[CONFLICT]", content,
                       "Must define [CONFLICT] classification for contradictions")

    def test_warning_classification_present(self):
        """Command file must define the [WARNING] classification level."""
        content = read_command_file()
        self.assertIn("[WARNING]", content,
                       "Must define [WARNING] classification for same-concern overlap")

    def test_info_classification_present(self):
        """Command file must define the [INFO] classification level."""
        content = read_command_file()
        self.assertIn("[INFO]", content,
                       "Must define [INFO] classification for cosmetic overlap")

    def test_citation_requirement(self):
        """Findings must cite text from both the override and the base file."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)cite.*override.*base|override.*text.*base.*section",
            "Must require citation of both override text and base section for findings",
        )

    def test_base_override_file_pairs_defined(self):
        """Command file must define the base/override file pairs mapping."""
        content = read_command_file()
        self.assertIn("BUILDER_OVERRIDES.md", content)
        self.assertIn("BUILDER_BASE.md", content)
        self.assertIn("QA_OVERRIDES.md", content)
        self.assertIn("QA_BASE.md", content)


class TestScanOnlyModeDoesNotModifyFiles(unittest.TestCase):
    """Scenario: Scan-only mode does not modify files

    Given /pl-override-edit is invoked with --scan-only
    When the conflict scan completes
    Then no files are modified

    Structural test: the command file defines --scan-only mode that stops
    after the conflict scan step without proceeding to edit steps.
    """

    def test_scan_only_flag_documented(self):
        """Command file must document the --scan-only flag."""
        content = read_command_file()
        self.assertIn("--scan-only", content,
                       "Must document the --scan-only flag")

    def test_scan_only_stops_after_conflict_scan(self):
        """In --scan-only mode, execution stops after the conflict scan."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)scan-only.*stop|scan-only.*mode.*stop",
            "Must state that --scan-only mode stops after the conflict scan",
        )

    def test_scan_only_no_edits(self):
        """In --scan-only mode, no edits are made."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)no\s+edits\s+(are\s+)?made",
            "Must state that no edits are made in --scan-only mode",
        )

    def test_scan_only_appears_before_edit_steps(self):
        """The --scan-only gate must appear before the apply/edit steps."""
        content = read_command_file()
        scan_only_pos = content.find("--scan-only")
        # The additive-only / apply step should come after the scan-only gate
        apply_pos = content.lower().find("additive only")
        self.assertGreater(scan_only_pos, -1, "--scan-only must be present")
        self.assertGreater(apply_pos, -1, "Additive-only constraint must be present")
        self.assertGreater(apply_pos, scan_only_pos,
                           "Edit constraints must come after --scan-only gate")


class TestAdditiveOnlyConstraintEnforced(unittest.TestCase):
    """Scenario: Additive-only constraint enforced

    Given a proposed edit that deletes existing content
    When /pl-override-edit validates the edit
    Then the edit is rejected as non-additive

    Structural test: the command file defines additive-only constraints that
    prohibit deletion and restructuring of existing content.
    """

    def test_additive_only_constraint_present(self):
        """Command file must state the additive-only constraint."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)additive\s+only",
            "Must state the additive-only constraint for edits",
        )

    def test_no_delete_instruction(self):
        """Command file must prohibit deleting existing content."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)do\s+not\s+delete|not\s+delete|no.*delet",
            "Must prohibit deleting existing content",
        )

    def test_no_restructure_instruction(self):
        """Command file must prohibit restructuring existing content."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)do\s+not\s+restructure|not\s+restructure|no.*restructur",
            "Must prohibit restructuring existing content",
        )

    def test_no_executable_content(self):
        """Command file must prohibit code, scripts, JSON config, or executable content."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)no\s+code.*script.*json|no\s+code.*script.*executable",
            "Must prohibit code, scripts, JSON config, or executable content",
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_override_edit")
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
                    "test_file": "tools/test_support/test_pl_override_edit.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
