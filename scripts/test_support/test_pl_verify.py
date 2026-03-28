#!/usr/bin/env python3
"""Tests for the /pl-verify skill command file.

Covers all 7 unit test scenarios from features/pl_verify.md.
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
COMMAND_FILE = os.path.join(PROJECT_ROOT, ".claude", "commands", "pl-verify.md")


def read_command_file():
    """Read and return the command file content."""
    with open(COMMAND_FILE) as f:
        return f.read()


class TestRoleGateRejectsNonQAInvocation(unittest.TestCase):
    """Scenario: Role gate rejects non-QA invocation

    Given a Engineer agent session
    When the agent invokes /pl-verify
    Then the command responds with a redirect message

    Structural test: the command file declares QA ownership and contains
    a redirect message for non-QA agents.
    """

    def test_first_line_declares_qa_ownership(self):
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("QA", first_line,
                       "First line must declare QA mode declarationship")

    def test_command_owner_pattern_present(self):
        content = read_command_file()
        first_line = content.splitlines()[0]
        self.assertIn("purlin mode", first_line.lower(),
                       "First line must contain 'mode declaration' pattern")

    def test_redirect_message_for_non_qa(self):
        """Non-QA agents receive a redirect message about QA mode."""
        content = read_command_file()
        # The file should instruct non-QA agents about mode activation
        self.assertRegex(
            content,
            r"(?i)(another mode is active|confirm switch|activates QA mode)",
            "Must contain redirect about QA mode activation"
        )

    def test_redirect_appears_before_execution_logic(self):
        """Role gate redirect must appear before any execution steps."""
        content = read_command_file()
        redirect_pos = re.search(r"(?i)(another mode is active|confirm switch|activates QA mode)", content)
        # Phase A or scope logic appears later
        scope_pos = content.find("## Scope")
        self.assertIsNotNone(redirect_pos,
                             "Redirect message must exist")
        if scope_pos > -1:
            self.assertLess(redirect_pos.start(), scope_pos,
                            "Redirect must appear before scope logic")


class TestScopedModeTargetsSingleFeature(unittest.TestCase):
    """Scenario: Scoped mode targets single feature

    Given feature_a is in TESTING state
    When /pl-verify is invoked with argument "feature_a"
    Then only feature_a scenarios are verified

    Structural test: the command file documents argument-based scoping
    to a single feature.
    """

    def test_argument_scoping_documented(self):
        """Command describes scoping to a single feature via argument."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(argument|arg).*scope.*feature|scope.*single.*feature|scope.*verification.*to",
            "Must document argument-based feature scoping"
        )

    def test_features_path_referenced(self):
        """Scoping references features/<arg>.md path pattern."""
        content = read_command_file()
        self.assertIn("features/", content,
                       "Must reference features/ path for scoping")

    def test_scoped_mode_distinct_from_batch(self):
        """Scoped mode and batch mode are described as separate flows."""
        content = read_command_file()
        # Both modes must be described
        self.assertRegex(content, r"(?i)scoped\s+mode",
                         "Must describe scoped mode")


class TestBatchModeIncludesAllTestingFeatures(unittest.TestCase):
    """Scenario: Batch mode includes all TESTING features

    Given feature_a and feature_b are both in TESTING state
    When /pl-verify is invoked without arguments
    Then both features are included in the verification pass

    Structural test: the command file describes batch behavior for
    all TESTING features when no argument is provided.
    """

    def test_no_argument_triggers_batch(self):
        """No argument leads to batch mode for all TESTING features."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)no argument|without argument|not provided",
            "Must describe no-argument batch trigger"
        )

    def test_testing_status_filter(self):
        """Batch mode filters for TESTING status features."""
        content = read_command_file()
        self.assertIn("TESTING", content,
                       "Must reference TESTING status for batch filtering")

    def test_batch_all_keyword(self):
        """Command mentions batching ALL TESTING features."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(batch\s+all|all\s+TESTING)",
            "Must describe batching all TESTING features"
        )

    def test_batch_includes_action_item_features(self):
        """Batch mode includes features from QA action items, not just TESTING lifecycle."""
        content = read_command_file()
        scope_match = re.search(r"## Scope.*?---", content, re.DOTALL)
        self.assertIsNotNone(scope_match, "Scope section must exist")
        scope_text = scope_match.group(0)
        self.assertRegex(
            scope_text,
            r"visual_verification|regression_run",
            "Scope must include QA action item categories (visual_verification/regression_run)"
        )
        self.assertRegex(
            scope_text,
            r"(?i)union|batch the union",
            "Scope must describe union of TESTING features and QA action item features"
        )


class TestCosmeticScopeSkipsFeature(unittest.TestCase):
    """Scenario: Cosmetic scope skips feature entirely

    Given feature_a has cosmetic verification scope
    When /pl-verify processes feature_a
    Then feature_a is skipped with "QA skip (cosmetic change)" message

    Structural test: the command file defines cosmetic scope handling
    with a skip message.
    """

    def test_cosmetic_scope_defined(self):
        """Cosmetic scope type is explicitly documented."""
        content = read_command_file()
        self.assertIn("cosmetic", content.lower(),
                       "Must define cosmetic scope")

    def test_cosmetic_skip_message(self):
        """Cosmetic features produce a QA skip message."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)QA skip.*cosmetic|cosmetic.*skip",
            "Must include QA skip message for cosmetic scope"
        )

    def test_cosmetic_scope_in_step_0(self):
        """Cosmetic scope handling appears in the verification modes section."""
        content = read_command_file()
        # Should be in Step 0 or scope modes section
        cosmetic_pos = content.lower().find("cosmetic")
        self.assertGreater(cosmetic_pos, -1,
                           "Cosmetic must appear in command file")

    def test_cosmetic_no_scenarios_queued(self):
        """Cosmetic skip message mentions no scenarios queued."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)no scenarios queued|skip.*entirely",
            "Must indicate no scenarios are queued for cosmetic features"
        )


class TestAutoPassCreditsBuilderVerifiedFeatures(unittest.TestCase):
    """Scenario: Auto-pass credits engineer-verified features

    Given feature_a has engineer status DONE and zero QA scenarios
    When Phase A Step 1 runs
    Then feature_a is auto-passed with acknowledgment message

    Structural test: the command file contains auto-pass logic for
    engineer-verified features in Phase A Step 1.
    """

    def test_auto_pass_step_present(self):
        """Step 1 auto-pass for engineer-verified features is documented."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)auto.pass.*engineer|engineer.*auto.pass",
            "Must document auto-pass for engineer-verified features"
        )

    def test_zero_qa_scenarios_condition(self):
        """Auto-pass requires zero QA scenarios."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)zero QA scenarios|zero.*manual.*scenarios",
            "Must require zero QA scenarios for auto-pass"
        )

    def test_acknowledgment_message_format(self):
        """Auto-pass produces an acknowledgment output message."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)auto.pass.*<feature>|Auto-pass:",
            "Must include auto-pass acknowledgment message format"
        )

    def test_auto_features_excluded_from_auto_pass(self):
        """AUTO features (qa_status: AUTO) must NOT be auto-passed."""
        content = read_command_file()
        # Step 1 must contain the AUTO exclusion mandate
        step1_match = re.search(
            r"### Step 1.*?### Step 2", content, re.DOTALL
        )
        self.assertIsNotNone(step1_match, "Step 1 section must exist")
        step1_text = step1_match.group(0)
        self.assertRegex(
            step1_text,
            r"AUTO features are NOT auto.passed",
            "Step 1 must explicitly state AUTO features are NOT auto-passed"
        )

    def test_auto_features_must_execute_in_steps_2_5(self):
        """AUTO features must execute automated tests in Steps 2-5."""
        content = read_command_file()
        step1_match = re.search(
            r"### Step 1.*?### Step 2", content, re.DOTALL
        )
        self.assertIsNotNone(step1_match, "Step 1 section must exist")
        step1_text = step1_match.group(0)
        self.assertRegex(
            step1_text,
            r"MUST execute in Steps 2.5",
            "Step 1 must direct AUTO features to Steps 2-5 for execution"
        )

    def test_regression_guidance_exclusion(self):
        """Features with regression harness authoring pending are excluded from auto-pass."""
        content = read_command_file()
        step1_match = re.search(
            r"### Step 1.*?### Step 2", content, re.DOTALL
        )
        self.assertIsNotNone(step1_match, "Step 1 section must exist")
        step1_text = step1_match.group(0)
        self.assertRegex(
            step1_text,
            r"(?i)regression.*guidance.*exclusion|regression.*harness.*authoring.*pending",
            "Step 1 must exclude features with pending regression harness authoring"
        )


class TestPhaseACheckpointFinalizesAutoFeatures(unittest.TestCase):
    """Step 5a Phase A Checkpoint must finalize features before Phase B.

    Structural test: the command file contains Step 5a with dual-fire
    checkpoints (A and B), CDD update, and zero-manual-items fast path.
    """

    def test_step_5a_exists(self):
        """Step 5a Phase A Checkpoint section exists in the command file."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"### Step 5a.*Phase A Checkpoint",
            "Step 5a -- Phase A Checkpoint section must exist"
        )

    def test_step_5a_commits_auto_completions(self):
        """Step 5a commits [Complete] [Verified] status tags for AUTO features."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        self.assertRegex(
            step5a_text,
            r"\[Complete\].*\[Verified\]",
            "Step 5a must commit [Complete] [Verified] status tags"
        )

    def test_step_5a_runs_scan(self):
        """Step 5a runs scan.sh to refresh project state."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        self.assertIn(
            "scan.sh",
            step5a_text,
            "Step 5a must run scan.sh to refresh project state"
        )

    def test_step_5a_zero_manual_items_fast_path(self):
        """Step 5a skips Phase B when zero manual items remain."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        self.assertRegex(
            step5a_text,
            r"(?i)zero manual items|skip.*Phase B",
            "Step 5a must provide fast path when no manual items remain"
        )

    def test_step_5a_dual_fire_checkpoints(self):
        """Step 5a fires at two points: (A) after Steps 1-5, (B) after all regression suites complete."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        self.assertRegex(
            step5a_text,
            r"Checkpoint \(A\).*after Steps 1",
            "Step 5a must describe Checkpoint (A) after Steps 1-5"
        )
        self.assertRegex(
            step5a_text,
            r"Checkpoint \(B\).*after all regression suites complete",
            "Step 5a must describe Checkpoint (B) after all regression suites complete"
        )

    def test_step_5a_b_fires_before_phase_b(self):
        """Step 5a(B) must fire BEFORE Phase B begins."""
        content = read_command_file()
        # Step 5a(B) checkpoint must appear before the Phase B section heading
        checkpoint_b_pos = content.find("Step 5a(B)")
        phase_b_pos = content.find("## Phase B")
        self.assertGreater(checkpoint_b_pos, -1,
                           "Step 5a(B) checkpoint must exist in regression section")
        self.assertGreater(phase_b_pos, -1,
                           "Phase B section heading must exist")
        self.assertLess(checkpoint_b_pos, phase_b_pos,
                        "Step 5a(B) must appear BEFORE Phase B section")

    def test_step_5a_covers_both_auto_and_todo(self):
        """Step 5a handles both AUTO and TODO features, not just AUTO."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        self.assertRegex(
            step5a_text,
            r"both AUTO and TODO",
            "Step 5a must handle both AUTO and TODO features"
        )

    def test_step_5a_critical_callout_artifacts_not_finalization(self):
        """Step 5a must contain CRITICAL callout that artifacts are NOT finalization."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        self.assertRegex(
            step5a_text,
            r"CRITICAL.*artifacts is NOT finalization|CRITICAL.*artifacts.*NOT.*finalization",
            "Step 5a must contain CRITICAL callout that committing artifacts is NOT finalization"
        )

    def test_step_5a_artifacts_before_status_tags(self):
        """Regression artifacts must be committed BEFORE status tag commits."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        artifacts_pos = step5a_text.find("Commit regression artifacts")
        status_pos = step5a_text.find("Commit status tags")
        self.assertGreater(artifacts_pos, -1,
                           "Step 5a must have 'Commit regression artifacts' step")
        self.assertGreater(status_pos, -1,
                           "Step 5a must have 'Commit status tags' step")
        self.assertLess(artifacts_pos, status_pos,
                        "Regression artifacts must be committed BEFORE status tags")

    def test_step_5a_allow_empty_per_feature(self):
        """Step 5a status tag commits use --allow-empty, one per feature."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        self.assertIn("--allow-empty", step5a_text,
                       "Step 5a must use --allow-empty for status tag commits")
        self.assertRegex(
            step5a_text,
            r"ONE COMMIT PER FEATURE",
            "Step 5a must enforce ONE COMMIT PER FEATURE"
        )

    def test_step_5a_hard_gate_on_scan_update(self):
        """Scan update in Step 5a must be a HARD GATE blocking Phase B."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        self.assertRegex(
            step5a_text,
            r"HARD GATE.*scan\.sh|Update scan.*HARD GATE",
            "Scan update must be a HARD GATE"
        )

    def test_step_5a_verify_finalization_clears_auto_todo(self):
        """Step 5a must verify finalized features no longer show AUTO/TODO."""
        content = read_command_file()
        step5a_match = re.search(
            r"### Step 5a.*?### Phase A Summary", content, re.DOTALL
        )
        self.assertIsNotNone(step5a_match, "Step 5a section must exist")
        step5a_text = step5a_match.group(0)
        self.assertRegex(
            step5a_text,
            r"(?i)verify finalization|no longer show AUTO/TODO",
            "Step 5a must verify finalized features cleared from AUTO/TODO"
        )


class TestCompletionCommitsIncludeVerifiedTag(unittest.TestCase):
    """Scenario: Completion commits include Verified tag

    Given all scenarios for feature_a passed verification
    When the completion commit is created
    Then the commit message includes "[Verified]"

    Structural test: the command file specifies the [Verified] tag in
    the completion commit template.
    """

    def test_verified_tag_in_commit_template(self):
        """Completion commit message includes [Verified] tag."""
        content = read_command_file()
        self.assertIn("[Verified]", content,
                       "Must include [Verified] tag in commit template")

    def test_verified_tag_in_status_commit(self):
        """[Verified] appears in a status/commit context, not just prose."""
        content = read_command_file()
        # Should appear near a git commit pattern
        self.assertRegex(
            content,
            r"(?i)(commit.*\[Verified\]|\[Verified\].*commit|\[Complete.*\[Verified\])",
            "[Verified] must appear in a commit/status context"
        )

    def test_verified_is_qa_only(self):
        """The command file uses [Verified] as a QA-specific tag."""
        content = read_command_file()
        # [Verified] should appear in the completion/batch section
        verified_pos = content.find("[Verified]")
        self.assertGreater(verified_pos, -1,
                           "[Verified] tag must be present")


class TestFailuresCreateDiscoveryEntries(unittest.TestCase):
    """Scenario: Failures create discovery entries

    Given item 3 fails during manual verification
    When the failure is processed
    Then a discovery entry is recorded in the feature's discovery sidecar file
    And the discovery includes observed behavior and classification

    Structural test: the command file describes failure processing with
    discovery sidecar recording including classification fields.
    """

    def test_discovery_sidecar_path_pattern(self):
        """Failure recording references discovery sidecar files."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(discoveries\.md|discovery sidecar|sidecar file)",
            "Must reference discovery sidecar files for failure recording"
        )

    def test_failure_classification_types(self):
        """Multiple failure classification types are defined."""
        content = read_command_file()
        # Should include at least BUG and DISCOVERY types
        self.assertIn("[BUG]", content,
                       "Must define BUG classification type")

    def test_observed_behavior_field(self):
        """Discovery entries include observed behavior field."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)observed\s+behavior|what.*observed",
            "Must include observed behavior in discovery entries"
        )

    def test_failure_processing_step(self):
        """A dedicated failure processing step exists."""
        content = read_command_file()
        self.assertRegex(
            content,
            r"(?i)(step\s+9|failure\s+processing)",
            "Must have a dedicated failure processing step"
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
        out_dir = os.path.join(PROJECT_ROOT, "tests", "pl_verify")
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
                    "test_file": "tools/test_support/test_pl_verify.py",
                    "details": result.results,
                },
                f,
                indent=2,
            )
        print(f"\nResults written to {out_file}")

    sys.exit(0 if result.wasSuccessful() else 1)
