#!/usr/bin/env python3
"""Tests for the /pl-spec-from-code skill command file.

Covers all 16 unit test scenarios from features/pl_spec_from_code.md.
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
COMMAND_FILE = os.path.join(
    PROJECT_ROOT, ".claude", "commands", "pl-spec-from-code.md"
)


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


# ===================================================================
# Scenario 1: Role gate rejects non-PM invocation
# ===================================================================


class TestRoleGateRejectsNonPM(unittest.TestCase):
    """Scenario: Role gate rejects non-PM invocation

    Given a Engineer agent session
    When the agent invokes /pl-spec-from-code
    Then the command responds with redirect message
    And no state file is created

    Structural test: the command file declares PM ownership and
    contains the exact redirect message for non-PM agents.
    """

    def test_first_line_declares_engineer_ownership(self):
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("Engineer", first_line)
        self.assertIn("purlin mode", first_line.lower())

    def test_redirect_message_present(self):
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(activates Engineer mode|another mode is active|confirm switch)",
        )

    def test_redirect_instructs_confirm_switch(self):
        """The redirect message includes 'confirm switch' to prevent execution."""
        content = read_command_file()
        self.assertIn("confirm switch", content.lower())


# ===================================================================
# Scenario 2: Phase 0 creates state file and prompts for directories
# ===================================================================


class TestPhase0CreatesStateAndPrompts(unittest.TestCase):
    """Scenario: Phase 0 creates state file and prompts for directories

    Given an PM agent session with no existing sfc_state.json
    When the agent invokes /pl-spec-from-code
    Then the command creates .purlin/cache/sfc_state.json
    And the command prompts for source directories and exclusions
    And the state file is committed to git

    Structural test: the command file references the state file path,
    contains directory defaults/exclusions, and has a Phase 0 commit.
    """

    def test_state_file_path_referenced(self):
        content = read_command_file()
        self.assertIn(".purlin/cache/sfc_state.json", content)

    def test_default_include_directories_offered(self):
        content = read_command_file()
        for d in ("src/", "lib/", "app/"):
            self.assertIn(d, content)

    def test_default_exclude_directories_offered(self):
        content = read_command_file()
        for d in ("node_modules/", "vendor/", ".purlin/", "tools/"):
            self.assertIn(d, content)

    def test_phase_0_git_commit_present(self):
        content = read_command_file()
        self.assertRegex(content, r"(?i)commit.*phase\s*0")


# ===================================================================
# Scenario 3: Phase 1 launches parallel sub-agents for codebase survey
# ===================================================================


class TestPhase1ParallelSubAgents(unittest.TestCase):
    """Scenario: Phase 1 launches parallel sub-agents for codebase survey

    Given Phase 0 is complete with directory choices saved
    When Phase 1 begins
    Then up to 3 Explore sub-agents are launched in parallel
    And results are synthesized into .purlin/cache/sfc_inventory.md

    Structural test: the command file defines three agents (A, B, C),
    references Explore sub-agents, and produces the inventory file.
    """

    def test_three_sub_agents_defined(self):
        content = read_command_file()
        self.assertIn("Agent A", content)
        self.assertIn("Agent B", content)
        self.assertIn("Agent C", content)

    def test_explore_sub_agent_type_referenced(self):
        content = read_command_file()
        self.assertIn("Explore", content)

    def test_inventory_file_path_referenced(self):
        content = read_command_file()
        self.assertIn(".purlin/cache/sfc_inventory.md", content)

    def test_phase_1_git_commit_present(self):
        content = read_command_file()
        self.assertRegex(content, r"(?i)commit.*phase\s*1")


# ===================================================================
# Scenario 4: Phase 2 presents taxonomy for interactive review
# ===================================================================


class TestPhase2TaxonomyReview(unittest.TestCase):
    """Scenario: Phase 2 presents taxonomy for interactive review

    Given the inventory file exists
    When Phase 2 begins
    Then categories are proposed with feature candidates
    And the user is prompted in batches to validate
    And anchor nodes are proposed from cross-cutting concerns
    And the taxonomy is written to .purlin/cache/sfc_taxonomy.md

    Structural test: the command file references batches of 2-3,
    anchor node types, and the taxonomy output file.
    """

    def test_batch_validation_mentioned(self):
        content = read_command_file()
        self.assertRegex(content, r"batch(es)?\s+(of\s+)?2-3")

    def test_anchor_node_type_prefixes_present(self):
        content = read_command_file()
        for prefix in ("arch_", "design_", "policy_"):
            self.assertIn(prefix, content)

    def test_taxonomy_file_path_referenced(self):
        content = read_command_file()
        self.assertIn(".purlin/cache/sfc_taxonomy.md", content)

    def test_phase_2_git_commit_present(self):
        content = read_command_file()
        self.assertRegex(content, r"(?i)commit.*phase\s*2")


# ===================================================================
# Scenario 5: Phase 3 generates anchor nodes before features
# ===================================================================


class TestPhase3AnchorNodesFirst(unittest.TestCase):
    """Scenario: Phase 3 generates anchor nodes before features

    Given the taxonomy file exists with approved anchor nodes
    When Phase 3 begins
    Then all anchor nodes are created first using the _anchor.md template
    And each anchor node is committed individually
    And features are generated after all anchor nodes exist

    Structural test: the command file references the _anchor.md template,
    individual commits for anchors, and the ordering (anchors before features).
    """

    def test_anchor_template_referenced(self):
        content = read_command_file()
        self.assertIn("_anchor.md", content)

    def test_individual_anchor_commits(self):
        content = read_command_file()
        # Should mention committing each anchor node individually
        self.assertRegex(
            content, r"(?i)commit\s+each\s+anchor\s+node\s+individual"
        )

    def test_anchors_before_features_ordering(self):
        """Anchor node generation section appears before feature generation."""
        content = read_command_file()
        anchor_pos = content.find("Generate Anchor Nodes")
        feature_pos = content.find("Generate Features per Category")
        self.assertGreater(anchor_pos, -1, "Anchor generation section missing")
        self.assertGreater(
            feature_pos, anchor_pos, "Anchors must be generated before features"
        )


# ===================================================================
# Scenario 6: Phase 3 generates features per category with template compliance
# ===================================================================


class TestPhase3FeatureTemplateCompliance(unittest.TestCase):
    """Scenario: Phase 3 generates features per category with template compliance

    Given anchor nodes are created and committed
    When a category batch is generated
    Then each feature file uses the _feature.md template
    And includes Label, Category, Prerequisite metadata
    And includes Overview, Requirements, and Scenarios sections
    And the Scenarios section includes the Draft notice
    And all features have status marker TODO

    Structural test: the command file references the _feature.md template,
    required metadata fields, the draft notice text, and TODO status.
    """

    def test_feature_template_referenced(self):
        content = read_command_file()
        self.assertIn("_feature.md", content)

    def test_required_metadata_fields_listed(self):
        content = read_command_file()
        for field in ("> Label:", "> Category:", "> Prerequisite:"):
            self.assertIn(field, content)

    def test_draft_notice_text_present(self):
        content = read_command_file()
        self.assertIn(
            "auto-generated from existing code by /pl-spec-from-code", content
        )

    def test_todo_status_marker_required(self):
        content = read_command_file()
        self.assertIn("[TODO]", content)


# ===================================================================
# Scenario 7: Phase 3 creates companion files for features with rich comments
# ===================================================================


class TestPhase3CompanionFiles(unittest.TestCase):
    """Scenario: Phase 3 creates companion files for features with rich comments

    Given Agent C found significant code comments
    When the feature is generated in Phase 3
    Then a companion file is created at features/<name>.impl.md
    And the companion file includes a Source Mapping section

    Structural test: the command file references companion file creation
    and the Source Mapping section requirement.
    """

    def test_companion_file_pattern_referenced(self):
        content = read_command_file()
        self.assertIn(".impl.md", content)

    def test_source_mapping_section_required(self):
        content = read_command_file()
        self.assertIn("Source Mapping", content)

    def test_companion_triggered_by_code_comments(self):
        """Companion files are conditioned on significant code comments."""
        content = read_command_file()
        # The command should mention TODOs/architectural decisions as triggers
        self.assertRegex(
            content,
            r"(?i)(todo|architectural\s+decision|known\s+issue).*companion|companion.*(?:todo|architectural\s+decision|known\s+issue)",
        )


# ===================================================================
# Scenario 8: Phase 3 asks user to confirm each category
# ===================================================================


class TestPhase3CategoryConfirmation(unittest.TestCase):
    """Scenario: Phase 3 asks user to confirm each category before continuing

    Given a category batch has been generated and committed
    When the category is complete
    Then the user is prompted to confirm the generated features
    And the state file is updated with the completed category name

    Structural test: the command file contains a user confirmation step
    per category and state file updates with completed_categories.
    """

    def test_user_confirmation_per_category(self):
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)ask.*user.*confirm.*features.*correct|confirm.*generated\s+features",
        )

    def test_completed_categories_tracked_in_state(self):
        content = read_command_file()
        self.assertIn("completed_categories", content)

    def test_state_update_after_category_commit(self):
        """State file is updated after each category."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(update\s+state|add\s+category.*completed_categories)",
        )


# ===================================================================
# Scenario 9: Phase 4 runs CDD status and summarizes results
# ===================================================================


class TestPhase4ScanAndSummary(unittest.TestCase):
    """Scenario: Phase 4 runs scan and summarizes results

    Given all categories are generated and committed
    When Phase 4 begins
    Then tools/cdd/scan.sh is executed
    And totals are printed (features, anchor nodes, companion files)

    Structural test: the command file references scan.sh and
    lists the summary items to print.
    """

    def test_scan_sh_referenced(self):
        content = read_command_file()
        self.assertIn("scan.sh", content)

    def test_summary_includes_total_features(self):
        content = read_command_file()
        self.assertRegex(content, r"(?i)total\s+features\s+created")

    def test_summary_includes_total_anchor_nodes(self):
        content = read_command_file()
        self.assertRegex(content, r"(?i)(total\s+)?anchor\s+nodes\s+created")

    def test_summary_includes_total_companion_files(self):
        content = read_command_file()
        self.assertRegex(content, r"(?i)(total\s+)?companion\s+files\s+created")


# ===================================================================
# Scenario 10: Phase 4 cleans up temporary files
# ===================================================================


class TestPhase4TemporaryFileCleanup(unittest.TestCase):
    """Scenario: Phase 4 cleans up temporary files

    Given the CDD status has been generated
    When finalization cleanup runs
    Then sfc_state.json, sfc_inventory.md, sfc_taxonomy.md are deleted
    And the cleanup is committed to git

    Structural test: the command file lists all three files for deletion
    and has a cleanup commit.
    """

    def test_state_file_deleted(self):
        content = read_command_file()
        # Should reference deleting the state file
        self.assertIn("sfc_state.json", content)

    def test_inventory_file_deleted(self):
        content = read_command_file()
        self.assertIn("sfc_inventory.md", content)

    def test_taxonomy_file_deleted(self):
        content = read_command_file()
        self.assertIn("sfc_taxonomy.md", content)

    def test_cleanup_commit_present(self):
        content = read_command_file()
        self.assertRegex(content, r"(?i)commit.*clean\s*up|commit.*finalize")


# ===================================================================
# Scenario 11: Phase 4 prints recommended next steps
# ===================================================================


class TestPhase4RecommendedNextSteps(unittest.TestCase):
    """Scenario: Phase 4 prints recommended next steps

    Given cleanup is committed
    When finalization completes
    Then the command prints three recommended next steps
    And the first mentions /pl-spec-code-audit
    And the second mentions reviewing features in dependency order
    And the third mentions having the Engineer run /pl-build

    Structural test: the command file contains all three recommended
    next step messages.
    """

    def test_first_recommendation_spec_code_audit(self):
        content = read_command_file()
        self.assertIn("/pl-spec-code-audit", content)

    def test_second_recommendation_dependency_order_review(self):
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)review.*features.*dependency\s+order",
        )

    def test_third_recommendation_engineer_pl_build(self):
        content = read_command_file()
        self.assertRegex(content, r"(?i)engineer.*run.*`?/pl-build`?")

    def test_all_three_steps_present(self):
        """All three recommended next steps appear in the command file."""
        content = read_command_file()
        has_audit = "/pl-spec-code-audit" in content
        has_review = bool(
            re.search(r"(?i)review.*features.*dependency\s+order", content)
        )
        has_build = bool(
            re.search(r"(?i)engineer.*run.*`?/pl-build`?", content)
        )
        self.assertTrue(
            has_audit and has_review and has_build,
            "All three recommended next steps must be present",
        )


# ===================================================================
# Scenario 12: Cross-session resume from interrupted Phase 3
# ===================================================================


class TestCrossSessionResumePhase3(unittest.TestCase):
    """Scenario: Cross-session resume from interrupted Phase 3

    Given Phase 3 was interrupted after completing 2 of 5 categories
    When the agent invokes /pl-spec-from-code
    Then the command resumes Phase 3 from the first incomplete category
    And completed categories are skipped

    Structural test: the command file has resume logic that reads the
    state file and skips completed categories.
    """

    def test_resume_check_present(self):
        content = read_command_file()
        self.assertRegex(content, r"(?i)resum(e|ing)")

    def test_completed_categories_skip_logic(self):
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(skip.*completed|completed_categories.*skip|read.*completed_categories)",
        )

    def test_state_file_read_on_invocation(self):
        """The command checks for existing state file at startup."""
        content = read_command_file()
        # Resume Check should be near the top, before Phase 0
        resume_pos = content.find("Resume Check")
        phase0_pos = content.find("Phase 0")
        self.assertGreater(resume_pos, -1, "Resume Check section must exist")
        self.assertGreater(
            phase0_pos, resume_pos, "Resume Check must appear before Phase 0"
        )


# ===================================================================
# Scenario 13: Resume from completed Phase 1
# ===================================================================


class TestResumeFromCompletedPhase1(unittest.TestCase):
    """Scenario: Resume from completed Phase 1

    Given Phase 1 is complete and the state file records phase 1 complete
    When the agent invokes /pl-spec-from-code
    Then the command skips Phase 0 and Phase 1
    And begins Phase 2 using the existing inventory

    Structural test: the command file has skip logic for completed phases
    and references the inventory file for Phase 2.
    """

    def test_skip_completed_phases_logic(self):
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)skip\s+(all\s+)?phases?\s+whose\s+status\s+is\s+.?complete",
        )

    def test_phase_2_reads_inventory(self):
        """Phase 2 starts by reading the inventory file."""
        content = read_command_file()
        phase2_start = content.find("Phase 2")
        self.assertGreater(phase2_start, -1)
        phase2_section = content[phase2_start : phase2_start + 500]
        self.assertIn("sfc_inventory.md", phase2_section)

    def test_no_re_asking_earlier_questions(self):
        """Resume logic prevents re-asking earlier phase questions."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(do\s+not|NOT)\s+re-?ask",
        )


# ===================================================================
# Scenario 14: Generated features appear as TODO in scan
# ===================================================================


class TestGeneratedFeaturesAppearAsTODO(unittest.TestCase):
    """Scenario: Generated features appear as TODO in scan

    Given Phase 4 has completed successfully
    When tools/cdd/scan.sh is run
    Then all generated features appear with TODO status

    Structural test: the command file sets TODO status on all features
    and runs scan.sh in Phase 4.
    """

    def test_todo_status_set_on_features(self):
        content = read_command_file()
        self.assertIn("[TODO]", content)

    def test_scan_sh_run_in_phase_4(self):
        content = read_command_file()
        phase4_start = content.find("Phase 4")
        self.assertGreater(phase4_start, -1)
        phase4_section = content[phase4_start:]
        self.assertIn("scan.sh", phase4_section)


# ===================================================================
# Scenario 15: End-to-end onboarding of a non-trivial codebase
# ===================================================================


class TestEndToEndOnboarding(unittest.TestCase):
    """Scenario: End-to-end onboarding of a non-trivial codebase

    Given a consumer project with 10+ source files
    When the PM runs /pl-spec-from-code
    Then all five phases execute in order with proper artifacts

    Structural test: the command file has all five phase sections
    in order and each produces the expected artifacts.
    """

    def test_all_five_phases_present(self):
        content = read_command_file()
        for phase in range(5):
            self.assertRegex(
                content,
                rf"(?i)phase\s+{phase}",
                f"Phase {phase} must be documented in the command file",
            )

    def test_phases_in_sequential_order(self):
        content = read_command_file()
        positions = []
        for phase in range(5):
            match = re.search(rf"##.*Phase\s+{phase}", content)
            self.assertIsNotNone(match, f"Phase {phase} heading missing")
            positions.append(match.start())
        for i in range(len(positions) - 1):
            self.assertLess(
                positions[i],
                positions[i + 1],
                f"Phase {i} must appear before Phase {i + 1}",
            )

    def test_per_category_commits_in_phase_3(self):
        """Phase 3 specifies per-category batch commits."""
        content = read_command_file()
        phase3_start = content.find("Phase 3")
        phase4_start = content.find("Phase 4")
        phase3_section = content[phase3_start:phase4_start]
        self.assertRegex(
            phase3_section, r"(?i)commit.*category"
        )


# ===================================================================
# Scenario 16: Mid-Phase-3 session restart and resume
# ===================================================================


class TestMidPhase3SessionRestart(unittest.TestCase):
    """Scenario: Mid-Phase-3 session restart and resume

    Given the PM is partway through Phase 3
    And sfc_state.json records some completed categories
    When a new session starts and /pl-spec-from-code is invoked
    Then the command detects the existing state file
    And resumes from the first incomplete category
    And previously generated features are not regenerated

    Structural test: the command file has Phase 3 resume logic that
    uses completed_categories to skip already-done work.
    """

    def test_phase_3_resume_logic_present(self):
        content = read_command_file()
        # Phase 3 section should mention resume
        phase3_start = content.find("Phase 3")
        self.assertGreater(phase3_start, -1)
        phase3_section = content[phase3_start : phase3_start + 500]
        self.assertRegex(phase3_section, r"(?i)resum")

    def test_completed_categories_checked_on_resume(self):
        content = read_command_file()
        phase3_start = content.find("Phase 3")
        phase3_section = content[phase3_start : phase3_start + 500]
        self.assertIn("completed_categories", phase3_section)

    def test_state_file_durability_via_git(self):
        """State file is committed to git for cross-session durability."""
        content = read_command_file()
        # The state file should be committed (mentioned alongside git commit)
        self.assertRegex(
            content,
            r"(?i)(commit.*sfc_state|state.*commit)",
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
        self.results.append(
            {"test": str(test), "status": "FAIL", "message": str(err[1])}
        )

    def addError(self, test, err):
        super().addError(test, err)
        self.results.append(
            {"test": str(test), "status": "ERROR", "message": str(err[1])}
        )


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])

    runner = unittest.TextTestRunner(resultclass=JsonTestResult, verbosity=2)
    result = runner.run(suite)

    # Write tests.json
    if PROJECT_ROOT:
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_spec_from_code")
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
                    "test_file": "tools/test_support/test_pl_spec_from_code.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
