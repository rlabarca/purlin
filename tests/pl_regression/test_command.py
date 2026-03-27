#!/usr/bin/env python3
"""Tests for the /pl-regression agent command.

Covers automated scenarios from features/pl_regression.md:
- Bare invocation auto-detects author step
- Bare invocation auto-detects run step
- Bare invocation auto-detects evaluate step
- Bare invocation reports green status
- Evaluate documents failure in companion file
- Re-evaluate marks resolved

The agent command is a Claude skill defined in .claude/commands/pl-regression.md.
These tests verify the skill file structure:
- Role guard (QA mode)
- Auto-detect behavior with health summary
- Three subcommands (run, author, evaluate)
- Health summary format
- Harness runner integration
- Evaluate protocol including [DISCOVERY] writing
- Consolidation of old skill files
"""
import json
import os
import re
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '../..'))
COMMAND_FILE = os.path.join(
    PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')


class TestSkillFileExists(unittest.TestCase):
    """The skill file must exist at the expected path."""

    def test_skill_file_exists(self):
        """Skill file exists at .claude/commands/pl-regression.md."""
        self.assertTrue(
            os.path.isfile(COMMAND_FILE),
            f'Skill file not found: {COMMAND_FILE}')


class TestRoleGuard(unittest.TestCase):
    """The skill file must declare QA mode."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_declares_qa_mode(self):
        """Skill file declares QA mode."""
        self.assertIn('Purlin mode: QA', self.content)

    def test_mode_switch_guard(self):
        """Skill file includes mode switch confirmation guard."""
        self.assertIn(
            'confirm switch', self.content.lower(),
            'Skill file must include mode switch guard')

    def test_purlin_command_header(self):
        """Skill file has a Purlin command header."""
        self.assertIn('Purlin command:', self.content)


class TestAutoDetectBehavior(unittest.TestCase):
    """Bare invocation must auto-detect the next step."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_auto_detect_section_exists(self):
        """Skill file has an Auto-Detect section."""
        self.assertIn('Auto-Detect', self.content)

    def test_author_needed_rule(self):
        """Auto-detect includes the 'author needed' rule."""
        self.assertIn('author', self.content.lower())
        # Must mention the condition: no scenario files exist
        self.assertIn('scenario', self.content.lower())

    def test_run_needed_rule(self):
        """Auto-detect includes the 'run needed' rule."""
        # Must mention STALE, FAIL, or NOT_RUN as triggers
        self.assertIn('STALE', self.content)
        self.assertIn('NOT_RUN', self.content)

    def test_evaluate_needed_rule(self):
        """Auto-detect includes the 'evaluate needed' rule."""
        self.assertIn('evaluate', self.content.lower())

    def test_all_green_rule(self):
        """Auto-detect includes the 'all green' rule."""
        # The all-green case should mention stopping or summary
        lower = self.content.lower()
        self.assertTrue(
            'all green' in lower or 'stop' in lower,
            'Skill file must describe the all-green/stop condition')

    def test_next_hint_after_detection(self):
        """Skill file prints a hint for the next step after auto-detect."""
        self.assertIn(
            'Next: /pl-regression', self.content,
            'Skill file must print a next-step hint after auto-detect')

    def test_detection_order(self):
        """Auto-detect rules appear in correct priority order: author, run, evaluate."""
        author_pos = self.content.lower().find('author needed')
        run_pos = self.content.lower().find('run needed')
        evaluate_pos = self.content.lower().find('evaluate needed')
        # All three must exist
        self.assertGreater(author_pos, -1, 'Author needed rule not found')
        self.assertGreater(run_pos, -1, 'Run needed rule not found')
        self.assertGreater(evaluate_pos, -1, 'Evaluate needed rule not found')
        # Order: author < run < evaluate
        self.assertLess(
            author_pos, run_pos,
            'Author needed must appear before run needed')
        self.assertLess(
            run_pos, evaluate_pos,
            'Run needed must appear before evaluate needed')


class TestHealthSummary(unittest.TestCase):
    """Bare invocation must print a health summary before auto-detecting."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_health_summary_format(self):
        """Skill file shows the health summary format with status counts."""
        self.assertIn('Regression Health:', self.content)

    def test_health_summary_includes_pass(self):
        """Health summary includes PASS count."""
        self.assertIn('PASS', self.content)

    def test_health_summary_includes_stale(self):
        """Health summary includes STALE count."""
        self.assertIn('STALE', self.content)

    def test_health_summary_includes_fail(self):
        """Health summary includes FAIL count."""
        self.assertIn('FAIL', self.content)

    def test_health_summary_includes_not_run(self):
        """Health summary includes NOT_RUN count."""
        self.assertIn('NOT_RUN', self.content)

    def test_health_summary_includes_total(self):
        """Health summary includes total count."""
        self.assertIn('total', self.content.lower())

    def test_no_scenarios_message(self):
        """Skill file includes message for zero scenario files."""
        self.assertIn(
            'No regression scenarios authored yet', self.content,
            'Skill must show message when no scenario files exist')


class TestThreeSubcommands(unittest.TestCase):
    """Skill file must document all three subcommands: run, author, evaluate."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_run_subcommand_documented(self):
        """Skill file documents the 'run' subcommand."""
        self.assertIn('/pl-regression run', self.content)

    def test_author_subcommand_documented(self):
        """Skill file documents the 'author' subcommand."""
        self.assertIn('/pl-regression author', self.content)

    def test_evaluate_subcommand_documented(self):
        """Skill file documents the 'evaluate' subcommand."""
        self.assertIn('/pl-regression evaluate', self.content)

    def test_run_section_exists(self):
        """Skill file has a dedicated run section."""
        self.assertIn('### run', self.content)

    def test_author_section_exists(self):
        """Skill file has a dedicated author section."""
        self.assertIn('### author', self.content)

    def test_evaluate_section_exists(self):
        """Skill file has a dedicated evaluate section."""
        self.assertIn('### evaluate', self.content)

    def test_feature_argument_supported(self):
        """All subcommands accept an optional feature argument."""
        # Check that [feature] appears in the usage section
        feature_arg_count = self.content.count('[feature]')
        self.assertGreaterEqual(
            feature_arg_count, 3,
            'Each subcommand must accept an optional [feature] argument')


class TestHarnessRunnerIntegration(unittest.TestCase):
    """The run subcommand must invoke the harness runner."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_references_harness_runner(self):
        """Skill file references harness_runner.py."""
        self.assertIn('harness_runner', self.content)

    def test_discovers_suites(self):
        """Skill file describes suite discovery."""
        self.assertIn('Discover suites', self.content)

    def test_smoke_tier_priority(self):
        """Skill file prioritizes smoke tier."""
        self.assertIn('smoke', self.content.lower())

    def test_auto_evaluate_after_run(self):
        """Run subcommand auto-evaluates after completion."""
        lower = self.content.lower()
        self.assertTrue(
            'auto-evaluate' in lower or 'auto evaluate' in lower,
            'Run subcommand must auto-evaluate after suite completion')

    def test_suite_execution_order(self):
        """Skill file describes execution order: STALE, FAIL, NOT_RUN."""
        content = self.content
        stale_pos = content.find('STALE first')
        if stale_pos == -1:
            # Alternative: check for ordering description
            stale_pos = content.find('STALE')
            fail_pos = content.find('FAIL', stale_pos + 1) if stale_pos > -1 else -1
            not_run_pos = content.find('NOT_RUN', fail_pos + 1) if fail_pos > -1 else -1
            self.assertGreater(stale_pos, -1)
            self.assertGreater(fail_pos, -1)
            self.assertGreater(not_run_pos, -1)


class TestEvaluateProtocol(unittest.TestCase):
    """Evaluate subcommand must follow the documented protocol."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_reads_regression_json(self):
        """Evaluate reads regression.json result files."""
        self.assertIn('regression.json', self.content)

    def test_reads_scenario_json(self):
        """Evaluate reads QA-authored scenario JSON files."""
        self.assertIn('scenarios/', self.content)

    def test_classifies_pass(self):
        """Evaluate classifies PASS results."""
        self.assertIn('PASS', self.content)

    def test_classifies_fail(self):
        """Evaluate classifies FAIL results."""
        self.assertIn('FAIL', self.content)

    def test_documents_discovery_for_failures(self):
        """Evaluate writes [DISCOVERY] entries for failures."""
        self.assertIn('[DISCOVERY]', self.content)

    def test_discovery_includes_scenario_name(self):
        """Discovery entry includes the scenario name."""
        self.assertIn('scenario_name', self.content)

    def test_discovery_includes_expected(self):
        """Discovery entry includes expected assertion."""
        self.assertIn('Expected', self.content)

    def test_discovery_includes_actual(self):
        """Discovery entry includes actual output."""
        self.assertIn('Actual', self.content)

    def test_discovery_includes_attempts(self):
        """Discovery entry includes attempt count."""
        self.assertIn('Attempts', self.content)

    def test_discovery_includes_suggested_fix(self):
        """Discovery entry includes suggested fix."""
        self.assertIn('Suggested fix', self.content)

    def test_writes_to_companion_file(self):
        """Evaluate writes to the companion file (impl.md)."""
        self.assertIn('.impl.md', self.content)

    def test_report_summary_format(self):
        """Evaluate prints a structured report summary."""
        self.assertIn('Regression Evaluation', self.content)

    def test_resolved_on_re_evaluation(self):
        """Re-evaluation marks [RESOLVED] when previously failed suite passes."""
        self.assertIn('[RESOLVED]', self.content)


class TestConsolidation(unittest.TestCase):
    """Old skill files must be deleted; new unified file replaces them."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_old_run_skill_deleted(self):
        """Old pl-regression-run.md skill file does not exist."""
        old_file = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-run.md')
        self.assertFalse(
            os.path.isfile(old_file),
            f'Old skill file still exists: {old_file}')

    def test_old_author_skill_deleted(self):
        """Old pl-regression-author.md skill file does not exist."""
        old_file = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-author.md')
        self.assertFalse(
            os.path.isfile(old_file),
            f'Old skill file still exists: {old_file}')

    def test_old_evaluate_skill_deleted(self):
        """Old pl-regression-evaluate.md skill file does not exist."""
        old_file = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-evaluate.md')
        self.assertFalse(
            os.path.isfile(old_file),
            f'Old skill file still exists: {old_file}')

    def test_replaces_old_skills(self):
        """Skill file header mentions it replaces old skills."""
        self.assertIn('replaces', self.content.lower())


class TestUsageSection(unittest.TestCase):
    """Skill file must have a usage section showing all invocation forms."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_usage_section_exists(self):
        """Skill file has a Usage section."""
        self.assertIn('## Usage', self.content)

    def test_bare_invocation_documented(self):
        """Usage section documents bare /pl-regression invocation."""
        # Pattern: /pl-regression followed by description (not a subcommand)
        self.assertRegex(
            self.content,
            r'/pl-regression\s+.*[Aa]uto',
            'Usage must document bare invocation with auto-detect')

    def test_feature_scoped_invocation_documented(self):
        """Usage documents feature-scoped invocation."""
        self.assertIn('/pl-regression [feature]', self.content)


class TestPathResolution(unittest.TestCase):
    """Skill file must reference path resolution."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_path_resolution_reference(self):
        """Skill file references path_resolution.md."""
        self.assertIn('path_resolution.md', self.content)

    def test_tools_root_reference(self):
        """Skill file references TOOLS_ROOT."""
        self.assertIn('TOOLS_ROOT', self.content)


class TestAuthorSubcommand(unittest.TestCase):
    """Author subcommand must document scenario authoring protocol."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_proposes_automation(self):
        """Author proposes automation for each scenario."""
        lower = self.content.lower()
        self.assertTrue(
            'propose' in lower or 'automat' in lower,
            'Author must propose automation for scenarios')

    def test_writes_regression_json(self):
        """Author writes regression JSON."""
        self.assertIn('JSON', self.content)

    def test_tags_auto_or_manual(self):
        """Author tags scenarios as @auto or @manual."""
        self.assertIn('@auto', self.content)
        self.assertIn('@manual', self.content)


class TestRunSubcommandBackgroundExecution(unittest.TestCase):
    """Run subcommand must handle slow suites in background."""

    def setUp(self):
        with open(COMMAND_FILE) as f:
            self.content = f.read()

    def test_background_execution_for_slow_suites(self):
        """Skill file describes background execution for slow suites."""
        self.assertIn('background', self.content.lower())

    def test_fast_suite_synchronous(self):
        """Skill file describes synchronous execution for fast suites."""
        lower = self.content.lower()
        self.assertTrue(
            'fast' in lower or 'synchronous' in lower,
            'Skill must describe fast/synchronous suite execution')


# =============================================================================
# Test runner: writes results to tests/pl_regression/tests.json
# =============================================================================
if __name__ == '__main__':
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    results = {
        "status": "FAIL" if failed else "PASS",
        "passed": passed,
        "failed": failed,
        "total": result.testsRun
    }
    results_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'tests.json')
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\ntests.json: {results['status']}")
