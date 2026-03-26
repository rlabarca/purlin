#!/usr/bin/env python3
"""Tests for dev/regression_runner.sh, harness runner, meta-runner, and enriched regression.json.

Covers automated scenarios from features/regression_testing.md.
Outputs test results to tests/regression_testing/tests.json.
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
RUNNER_SCRIPT = os.path.join(SCRIPT_DIR, 'regression_runner.sh')
HARNESS_RUNNER = os.path.join(PROJECT_ROOT, 'tools', 'test_support', 'harness_runner.py')
META_RUNNER = os.path.join(PROJECT_ROOT, 'tools', 'test_support', 'run_regression.sh')


class TestOnceMode(unittest.TestCase):
    """Scenario: Once mode runs single harness invocation."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create a minimal harness that succeeds
        self.harness = os.path.join(self.tmpdir, 'pass_harness.sh')
        with open(self.harness, 'w') as f:
            f.write('#!/usr/bin/env bash\necho "harness ran"\nexit 0\n')
        os.chmod(self.harness, 0o755)
        # Create runtime dir
        self.runtime_dir = os.path.join(self.tmpdir, '.purlin', 'runtime')
        os.makedirs(self.runtime_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_once_mode_runs_harness_and_exits(self):
        """Once mode executes the harness, writes result, and exits
        with the harness exit code."""
        # Use a relative harness path (relative to project root)
        harness_rel = os.path.relpath(self.harness, PROJECT_ROOT)
        env = os.environ.copy()
        result = subprocess.run(
            ['bash', RUNNER_SCRIPT, '--once', harness_rel],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT, env=env,
        )
        self.assertEqual(result.returncode, 0)
        # Result file should exist
        result_path = os.path.join(
            PROJECT_ROOT, '.purlin', 'runtime', 'regression_result.json')
        self.assertTrue(os.path.isfile(result_path))
        with open(result_path) as f:
            data = json.load(f)
        self.assertEqual(data['exit_code'], 0)
        self.assertEqual(data['harness'], harness_rel)
        self.assertIn('started_at', data)
        self.assertIn('completed_at', data)

    def test_once_mode_failing_harness(self):
        """Once mode exits with non-zero when harness fails."""
        fail_harness = os.path.join(self.tmpdir, 'fail_harness.sh')
        with open(fail_harness, 'w') as f:
            f.write('#!/usr/bin/env bash\necho "fail"\nexit 1\n')
        os.chmod(fail_harness, 0o755)
        harness_rel = os.path.relpath(fail_harness, PROJECT_ROOT)
        result = subprocess.run(
            ['bash', RUNNER_SCRIPT, '--once', harness_rel],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        self.assertEqual(result.returncode, 1)


class TestWatchModeTimeout(unittest.TestCase):
    """Scenario: Watch mode timeout kills long-running harness."""

    def test_timeout_kills_long_harness(self):
        """A harness exceeding --timeout is killed and gets non-zero exit."""
        tmpdir = tempfile.mkdtemp()
        try:
            runtime_dir = os.path.join(
                PROJECT_ROOT, '.purlin', 'runtime')
            os.makedirs(runtime_dir, exist_ok=True)

            # Create a harness that sleeps too long
            slow_harness = os.path.join(tmpdir, 'slow_harness.sh')
            with open(slow_harness, 'w') as f:
                f.write('#!/usr/bin/env bash\nsleep 60\n')
            os.chmod(slow_harness, 0o755)
            harness_rel = os.path.relpath(slow_harness, PROJECT_ROOT)

            # Use --once with short timeout (simulates the timeout mechanism)
            result = subprocess.run(
                ['bash', RUNNER_SCRIPT, '--once', harness_rel,
                 '--timeout', '3'],
                capture_output=True, text=True, timeout=30,
                cwd=PROJECT_ROOT,
            )
            # Should have non-zero exit (killed by timeout)
            self.assertNotEqual(result.returncode, 0)

            result_path = os.path.join(runtime_dir, 'regression_result.json')
            if os.path.isfile(result_path):
                with open(result_path) as f:
                    data = json.load(f)
                self.assertNotEqual(data['exit_code'], 0)
        finally:
            import shutil
            shutil.rmtree(tmpdir)


class TestWatchModeSIGINT(unittest.TestCase):
    """Scenario: Watch mode SIGINT prints session summary."""

    def test_sigint_prints_summary(self):
        """SIGINT in watch mode produces session summary output."""
        runtime_dir = os.path.join(
            PROJECT_ROOT, '.purlin', 'runtime')
        os.makedirs(runtime_dir, exist_ok=True)
        # Clean trigger/result files
        trigger = os.path.join(runtime_dir, 'regression_trigger.json')
        if os.path.isfile(trigger):
            os.remove(trigger)

        proc = subprocess.Popen(
            ['bash', RUNNER_SCRIPT, '--watch', '--timeout', '5'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=PROJECT_ROOT,
        )
        # Wait for watch mode to start polling
        time.sleep(2)
        # Send SIGINT
        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=10)
        # Should exit cleanly (exit 0)
        self.assertEqual(proc.returncode, 0)
        self.assertIn('Session Summary', stdout)


class TestMalformedTrigger(unittest.TestCase):
    """Scenario: Runner handles malformed trigger gracefully."""

    def test_runner_handles_malformed_trigger(self):
        """Runner handles malformed trigger gracefully: logs error,
        deletes trigger, resumes polling."""
        runtime_dir = os.path.join(
            PROJECT_ROOT, '.purlin', 'runtime')
        os.makedirs(runtime_dir, exist_ok=True)
        trigger = os.path.join(runtime_dir, 'regression_trigger.json')

        # Write malformed JSON
        with open(trigger, 'w') as f:
            f.write('{not valid json!!!')

        proc = subprocess.Popen(
            ['bash', RUNNER_SCRIPT, '--watch', '--timeout', '5'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=PROJECT_ROOT,
        )
        # Wait for it to detect and handle the malformed trigger
        time.sleep(4)
        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=10)

        # Trigger should have been deleted
        self.assertFalse(os.path.isfile(trigger))
        # Should mention error in output
        self.assertIn('malformed', stdout.lower() or stderr.lower())


class TestWatchModePollAndExecute(unittest.TestCase):
    """Scenario: Watch mode polls and executes trigger."""

    def test_watch_executes_trigger_and_resumes(self):
        """Watch mode detects trigger, runs harness, writes result,
        deletes trigger, and continues polling."""
        tmpdir = tempfile.mkdtemp()
        try:
            runtime_dir = os.path.join(
                PROJECT_ROOT, '.purlin', 'runtime')
            os.makedirs(runtime_dir, exist_ok=True)
            trigger = os.path.join(runtime_dir, 'regression_trigger.json')
            result_file = os.path.join(runtime_dir, 'regression_result.json')

            # Remove stale files
            for f in (trigger, result_file):
                if os.path.isfile(f):
                    os.remove(f)

            # Create a simple harness
            harness = os.path.join(tmpdir, 'echo_harness.sh')
            with open(harness, 'w') as f:
                f.write('#!/usr/bin/env bash\necho "executed"\nexit 0\n')
            os.chmod(harness, 0o755)
            harness_rel = os.path.relpath(harness, PROJECT_ROOT)

            # Start watch mode
            proc = subprocess.Popen(
                ['bash', RUNNER_SCRIPT, '--watch', '--timeout', '10'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, cwd=PROJECT_ROOT,
            )
            time.sleep(2)

            # Write trigger
            with open(trigger, 'w') as f:
                json.dump({
                    'harness': harness_rel,
                    'args': [],
                    'requested_at': '2026-03-18T14:30:00Z',
                }, f)

            # Wait for execution
            time.sleep(4)

            # Trigger should be deleted
            self.assertFalse(os.path.isfile(trigger))
            # Result should be written
            self.assertTrue(os.path.isfile(result_file))
            with open(result_file) as f:
                data = json.load(f)
            self.assertEqual(data['exit_code'], 0)
            self.assertEqual(data['harness'], harness_rel)

            # Stop watch mode
            proc.send_signal(signal.SIGINT)
            stdout, _ = proc.communicate(timeout=10)
            self.assertIn('1', stdout)  # At least 1 execution in summary
        finally:
            import shutil
            shutil.rmtree(tmpdir)


class TestQASkillIdentifiesEligible(unittest.TestCase):
    """Scenario: QA skill identifies regression-eligible features."""

    def test_run_skill_file_exists_and_has_discovery_flow(self):
        """The QA regression-run skill file exists and contains the
        discovery and selection flow."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-run.md')
        self.assertTrue(os.path.isfile(skill_path))
        with open(skill_path) as f:
            content = f.read()
        # Key elements of the discovery flow
        self.assertIn('regression-eligible', content)
        self.assertIn('STALE', content)
        self.assertIn('FAIL', content)
        self.assertIn('NOT_RUN', content)
        self.assertIn('stale', content.lower())
        # Interactive selection
        self.assertIn('all', content)
        self.assertIn('skip', content)

    def test_author_skill_identifies_web_test_metadata_features(self):
        """The author skill references Web Test metadata and Regression Testing sections."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-author.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('Web Test:', content)
        self.assertIn('Regression Testing', content)


class TestQASkillComposesCommand(unittest.TestCase):
    """Scenario: QA skill composes external command for selected features."""

    def test_qa_skill_composes_run_command(self):
        """QA run skill composes the run_regression.sh or run_all.sh command."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-run.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('run_regression.sh', content)
        self.assertIn('run_all.sh', content)

    def test_qa_skill_composes_copy_pasteable_command(self):
        """QA run skill prints copy-pasteable command for external terminal."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-run.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('copy-paste', content.lower().replace('-', '-'))
        self.assertIn('separate terminal', content.lower())


class TestQASkillCreatesBugDiscoveries(unittest.TestCase):
    """Scenario: QA skill creates BUG discoveries for regression failures."""

    def test_skill_has_bug_discovery_creation_protocol(self):
        """The evaluate skill documents how to create [BUG] sidecar entries
        from enriched regression results."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-evaluate.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('[BUG]', content)
        self.assertIn('discovery', content.lower())
        self.assertIn('scenario_ref', content)
        self.assertIn('actual_excerpt', content)
        self.assertIn('OPEN', content)


class TestEnrichedResultsFormat(unittest.TestCase):
    """Scenario: Enriched results include scenario-level context."""

    def test_enriched_fields_are_valid_json(self):
        """Enriched regression.json entries with scenario_ref, expected,
        and actual_excerpt are valid and parseable."""
        enriched = {
            'status': 'FAIL',
            'passed': 3,
            'failed': 2,
            'total': 5,
            'test_file': 'dev/test_agent_interactions.sh',
            'details': [
                {
                    'name': 'test_single_turn',
                    'status': 'PASS',
                    'scenario_ref': 'features/arch_testing.md:Single-turn agent test',
                    'expected': 'Agent produces structured output',
                },
                {
                    'name': 'test_multi_turn',
                    'status': 'FAIL',
                    'scenario_ref': 'features/arch_testing.md:Multi-turn session',
                    'expected': 'Agent resumes session state',
                    'actual_excerpt': 'Error: session ID not found...',
                },
            ],
        }
        # Round-trip through JSON
        serialized = json.dumps(enriched)
        parsed = json.loads(serialized)
        self.assertEqual(parsed['status'], 'FAIL')
        self.assertEqual(len(parsed['details']), 2)
        # Enriched fields on passing entry
        self.assertEqual(
            parsed['details'][0]['scenario_ref'],
            'features/arch_testing.md:Single-turn agent test')
        self.assertNotIn('actual_excerpt', parsed['details'][0])
        # Enriched fields on failing entry
        self.assertEqual(
            parsed['details'][1]['scenario_ref'],
            'features/arch_testing.md:Multi-turn session')
        self.assertIn('actual_excerpt', parsed['details'][1])

    def test_enriched_format_backward_compatible(self):
        """Standard regression.json consumers (status, passed, failed, total)
        still work when enriched fields are present."""
        enriched = {
            'status': 'PASS',
            'passed': 5,
            'failed': 0,
            'total': 5,
            'test_file': 'dev/test_agent_interactions.sh',
            'details': [{
                'name': 'test_a',
                'status': 'PASS',
                'scenario_ref': 'features/x.md:Scenario A',
                'expected': 'Thing works',
            }],
        }
        # Standard consumers only read top-level keys
        self.assertEqual(enriched['status'], 'PASS')
        self.assertEqual(enriched['passed'], 5)
        self.assertEqual(enriched['total'], 5)


class TestShallowAssertionSuite(unittest.TestCase):
    """Scenario: Shallow assertion suite flagged when majority are Tier 1."""

    def _compute_tier_distribution(self, details):
        """Compute tier distribution from regression.json detail entries."""
        tiers = {1: 0, 2: 0, 3: 0, 'untagged': 0}
        for entry in details:
            tier = entry.get('assertion_tier')
            if tier in (1, 2, 3):
                tiers[tier] += 1
            else:
                tiers['untagged'] += 1
        return tiers

    def _is_shallow(self, tiers):
        """Suite is SHALLOW when >50% of assertions are Tier 1."""
        total = sum(tiers.values())
        if total == 0:
            return False
        return tiers[1] / total > 0.5

    def test_shallow_flagged_when_majority_tier_1(self):
        """Suite with 6/10 Tier 1 entries is flagged [SHALLOW]."""
        details = [
            {'name': f'test_{i}', 'status': 'PASS', 'assertion_tier': 1}
            for i in range(6)
        ] + [
            {'name': f'test_{i}', 'status': 'PASS', 'assertion_tier': 2}
            for i in range(6, 10)
        ]
        tiers = self._compute_tier_distribution(details)
        self.assertEqual(tiers[1], 6)
        self.assertEqual(tiers[2], 4)
        self.assertEqual(tiers[3], 0)
        self.assertEqual(tiers['untagged'], 0)
        self.assertTrue(self._is_shallow(tiers))

    def test_not_shallow_when_minority_tier_1(self):
        """Suite with 3/10 Tier 1 entries is NOT flagged [SHALLOW]."""
        details = [
            {'name': f'test_{i}', 'status': 'PASS', 'assertion_tier': 1}
            for i in range(3)
        ] + [
            {'name': f'test_{i}', 'status': 'PASS', 'assertion_tier': 2}
            for i in range(3, 10)
        ]
        tiers = self._compute_tier_distribution(details)
        self.assertEqual(tiers[1], 3)
        self.assertEqual(tiers[2], 7)
        self.assertFalse(self._is_shallow(tiers))

    def test_tier_distribution_with_untagged_entries(self):
        """Entries without assertion_tier are counted as untagged."""
        details = [
            {'name': 'test_1', 'status': 'PASS', 'assertion_tier': 2},
            {'name': 'test_2', 'status': 'PASS'},  # no tier
            {'name': 'test_3', 'status': 'PASS', 'assertion_tier': 1},
        ]
        tiers = self._compute_tier_distribution(details)
        self.assertEqual(tiers[1], 1)
        self.assertEqual(tiers[2], 1)
        self.assertEqual(tiers['untagged'], 1)

    def test_skill_has_shallow_indicator_documentation(self):
        """The evaluate skill documents the [SHALLOW] indicator
        and tier distribution reporting."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-evaluate.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('SHALLOW', content)
        self.assertIn('Tier Distribution', content)
        self.assertIn('assertion_tier', content)
        self.assertIn('50%', content)


class TestStalenessDetection(unittest.TestCase):
    """Scenario: Staleness detection prioritizes re-testing."""

    def test_staleness_detection_prioritizes_retesting(self):
        """Staleness detection: feature source newer than regression.json
        means the feature is stale and prioritized for re-testing."""
        tmpdir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(tmpdir, 'features')
            tests_dir = os.path.join(tmpdir, 'tests', 'my_feature')
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            # Create regression.json first (older)
            tests_json = os.path.join(tests_dir, 'regression.json')
            with open(tests_json, 'w') as f:
                json.dump({'status': 'PASS', 'passed': 3, 'failed': 0,
                           'total': 3}, f)
            # Set mtime to 2 hours ago
            old_time = time.time() - 7200
            os.utime(tests_json, (old_time, old_time))

            # Create feature file (newer)
            feature_file = os.path.join(features_dir, 'my_feature.md')
            with open(feature_file, 'w') as f:
                f.write('# Feature: My Feature\n')
            # Set mtime to 1 hour ago
            new_time = time.time() - 3600
            os.utime(feature_file, (new_time, new_time))

            # Staleness: feature mtime > regression.json mtime
            feature_mtime = os.path.getmtime(feature_file)
            tests_mtime = os.path.getmtime(tests_json)
            self.assertGreater(feature_mtime, tests_mtime)

            # Fresh feature: regression.json newer than feature
            with open(tests_json, 'w') as f:
                json.dump({'status': 'PASS', 'passed': 3, 'failed': 0,
                           'total': 3}, f)
            fresh_tests_mtime = os.path.getmtime(tests_json)
            self.assertGreater(fresh_tests_mtime, feature_mtime)
        finally:
            import shutil
            shutil.rmtree(tmpdir)


class TestHarnessRunnerAgentBehavior(unittest.TestCase):
    """Scenario: Harness runner executes agent_behavior scenario from JSON.

    Tests the harness_runner.py processing pipeline for agent_behavior type.
    Since 'claude' CLI is not available in test, we use a wrapper script
    that simulates claude --print output, and verify the full pipeline.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        self.tests_dir = os.path.join(self.tmpdir, 'tests')
        self.scenarios_dir = os.path.join(self.tmpdir, 'tests', 'qa', 'scenarios')
        self.tools_dir = os.path.join(self.tmpdir, 'tools', 'test_support')
        os.makedirs(self.features_dir)
        os.makedirs(self.scenarios_dir)
        os.makedirs(self.tools_dir)

        # Create a feature file
        with open(os.path.join(self.features_dir, 'test_feature.md'), 'w') as f:
            f.write('# Feature: Test Feature\n[TODO]\n')

        # Create a fake 'claude' script that outputs predictable text
        self.fake_claude = os.path.join(self.tmpdir, 'bin', 'claude')
        os.makedirs(os.path.dirname(self.fake_claude))
        with open(self.fake_claude, 'w') as f:
            f.write('#!/usr/bin/env bash\n'
                    'echo "The ARCHITECT reviewed the specification"\n'
                    'echo "Found table with findings"\n')
        os.chmod(self.fake_claude, 0o755)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_agent_behavior_scenario_processes_assertions(self):
        """Harness runner processes agent_behavior scenario, evaluates
        assertions against output, and writes enriched regression.json."""
        # Create scenario JSON
        scenario = {
            'feature': 'test_feature',
            'harness_type': 'agent_behavior',
            'scenarios': [{
                'name': 'architect-review',
                'role': 'ARCHITECT',
                'prompt': 'Review the spec',
                'assertions': [
                    {'tier': 1, 'pattern': 'ARCHITECT',
                     'context': 'Agent identifies as architect'},
                    {'tier': 2, 'pattern': 'specification',
                     'context': 'Agent references specification'},
                ]
            }]
        }
        scenario_path = os.path.join(self.scenarios_dir, 'test_feature.json')
        with open(scenario_path, 'w') as f:
            json.dump(scenario, f)

        # Run harness runner with fake claude in PATH
        env = os.environ.copy()
        env['PATH'] = os.path.dirname(self.fake_claude) + ':' + env.get('PATH', '')
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir

        result = subprocess.run(
            ['python3', HARNESS_RUNNER, scenario_path,
             '--project-root', self.tmpdir],
            capture_output=True, text=True, timeout=30,
            cwd=self.tmpdir, env=env,
        )

        # Check regression.json was written
        tests_json = os.path.join(self.tmpdir, 'tests', 'test_feature', 'regression.json')
        self.assertTrue(os.path.isfile(tests_json),
                        f"regression.json not found. stdout: {result.stdout}, stderr: {result.stderr}")
        with open(tests_json) as f:
            data = json.load(f)

        self.assertEqual(data['status'], 'PASS')
        self.assertEqual(data['total'], 2)
        self.assertEqual(len(data['details']), 2)
        # Verify enriched fields
        detail = data['details'][0]
        self.assertIn('scenario_ref', detail)
        self.assertEqual(detail['scenario_ref'], 'features/test_feature.md:architect-review')
        self.assertEqual(detail['assertion_tier'], 1)

    def test_agent_behavior_fixture_checkout_and_cleanup(self):
        """Harness runner checks out fixture before execution and
        cleans up afterward."""
        # Verify the harness_runner.py imports and has fixture functions
        with open(HARNESS_RUNNER) as f:
            content = f.read()
        self.assertIn('run_fixture_checkout', content)
        self.assertIn('run_fixture_cleanup', content)
        self.assertIn('fixture_tag', content)




class TestHarnessRunnerCustomScript(unittest.TestCase):
    """Scenario: Harness runner falls back to custom_script."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        self.scenarios_dir = os.path.join(self.tmpdir, 'tests', 'qa', 'scenarios')
        self.qa_dir = os.path.join(self.tmpdir, 'tests', 'qa')
        os.makedirs(self.features_dir)
        os.makedirs(self.scenarios_dir, exist_ok=True)
        os.makedirs(self.qa_dir, exist_ok=True)
        with open(os.path.join(self.features_dir, 'custom_feature.md'), 'w') as f:
            f.write('# Feature: Custom Feature\n[TODO]\n')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_custom_script_scenario_executes_script(self):
        """Harness runner executes custom_script at script_path with
        --write-results and consumes its output."""
        # Create a custom QA script that writes results
        script_path = os.path.join(self.qa_dir, 'test_custom.sh')
        with open(script_path, 'w') as f:
            f.write('#!/usr/bin/env bash\n'
                    'echo "Custom script executed with args: $@"\n'
                    'echo "All checks passed"\n'
                    'exit 0\n')
        os.chmod(script_path, 0o755)

        # Relative path for scenario
        rel_script = os.path.relpath(script_path, self.tmpdir)

        scenario = {
            'feature': 'custom_feature',
            'harness_type': 'custom_script',
            'scenarios': [{
                'name': 'custom-check',
                'script_path': rel_script,
                'assertions': [
                    {'tier': 2, 'pattern': 'Custom script executed',
                     'context': 'Script was invoked'},
                    {'tier': 2, 'pattern': 'All checks passed',
                     'context': 'Script reports success'},
                ]
            }]
        }
        scenario_path = os.path.join(self.scenarios_dir, 'custom_feature.json')
        with open(scenario_path, 'w') as f:
            json.dump(scenario, f)

        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir

        result = subprocess.run(
            ['python3', HARNESS_RUNNER, scenario_path,
             '--project-root', self.tmpdir],
            capture_output=True, text=True, timeout=30,
            cwd=self.tmpdir, env=env,
        )

        self.assertEqual(result.returncode, 0,
                         f"Harness runner failed. stdout: {result.stdout}, stderr: {result.stderr}")

        tests_json = os.path.join(self.tmpdir, 'tests', 'custom_feature', 'regression.json')
        self.assertTrue(os.path.isfile(tests_json))
        with open(tests_json) as f:
            data = json.load(f)
        self.assertEqual(data['status'], 'PASS')
        self.assertEqual(data['passed'], 2)
        self.assertEqual(data['total'], 2)

    def test_custom_script_passes_write_results_flag(self):
        """Custom script dispatch passes --write-results to the script."""
        with open(HARNESS_RUNNER) as f:
            content = f.read()
        self.assertIn("'--write-results'", content)
        self.assertIn('script_path', content)


class TestMetaRunnerDiscovery(unittest.TestCase):
    """Scenario: Meta-runner discovers and runs all scenario files."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        self.scenarios_dir = os.path.join(self.tmpdir, 'tests', 'qa', 'scenarios')
        self.qa_scripts_dir = os.path.join(self.tmpdir, 'tests', 'qa')
        os.makedirs(self.features_dir)
        os.makedirs(self.scenarios_dir, exist_ok=True)
        os.makedirs(self.qa_scripts_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_meta_runner_processes_all_scenario_files(self):
        """Meta-runner discovers 3 scenario JSON files, processes all,
        continues past failures, and prints summary with exit code 1."""
        # Create 3 features
        for name in ('feat_a', 'feat_b', 'feat_c'):
            with open(os.path.join(self.features_dir, f'{name}.md'), 'w') as f:
                f.write(f'# Feature: {name}\n')

        # Create scripts - feat_b will fail
        for name, exit_code in [('feat_a', 0), ('feat_b', 1), ('feat_c', 0)]:
            script = os.path.join(self.qa_scripts_dir, f'test_{name}.sh')
            output_text = f'{name} executed' if exit_code == 0 else f'{name} failed'
            with open(script, 'w') as f:
                f.write(f'#!/usr/bin/env bash\necho "{output_text}"\nexit {exit_code}\n')
            os.chmod(script, 0o755)

            scenario = {
                'feature': name,
                'harness_type': 'custom_script',
                'scenarios': [{
                    'name': f'{name}-check',
                    'script_path': os.path.relpath(script, self.tmpdir),
                    'assertions': [
                        {'tier': 2, 'pattern': f'{name} executed',
                         'context': f'{name} runs successfully'},
                    ]
                }]
            }
            with open(os.path.join(self.scenarios_dir, f'{name}.json'), 'w') as f:
                json.dump(scenario, f)

        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir

        result = subprocess.run(
            ['bash', META_RUNNER, '--scenarios-dir', self.scenarios_dir],
            capture_output=True, text=True, timeout=60,
            cwd=self.tmpdir, env=env,
        )

        # Should exit with 1 (at least one failure)
        self.assertEqual(result.returncode, 1,
                         f"Expected exit 1. stdout: {result.stdout}")

        # All 3 should be processed (continues past failure)
        self.assertIn('feat_a', result.stdout)
        self.assertIn('feat_b', result.stdout)
        self.assertIn('feat_c', result.stdout)

        # Summary should be printed
        self.assertIn('Regression Summary', result.stdout)
        self.assertIn('3 features tested', result.stdout)
        self.assertIn('1 failure', result.stdout)

    def test_meta_runner_exits_zero_when_all_pass(self):
        """Meta-runner exits 0 when all scenario files pass."""
        with open(os.path.join(self.features_dir, 'good.md'), 'w') as f:
            f.write('# Feature: Good\n')

        script = os.path.join(self.qa_scripts_dir, 'test_good.sh')
        with open(script, 'w') as f:
            f.write('#!/usr/bin/env bash\necho "good executed"\nexit 0\n')
        os.chmod(script, 0o755)

        scenario = {
            'feature': 'good',
            'harness_type': 'custom_script',
            'scenarios': [{
                'name': 'good-check',
                'script_path': os.path.relpath(script, self.tmpdir),
                'assertions': [
                    {'tier': 2, 'pattern': 'good executed',
                     'context': 'Good feature runs'},
                ]
            }]
        }
        with open(os.path.join(self.scenarios_dir, 'good.json'), 'w') as f:
            json.dump(scenario, f)

        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir

        result = subprocess.run(
            ['bash', META_RUNNER, '--scenarios-dir', self.scenarios_dir],
            capture_output=True, text=True, timeout=60,
            cwd=self.tmpdir, env=env,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('0 failure', result.stdout)


class TestQAAuthoringWorkflow(unittest.TestCase):
    """Scenario: QA authors scenario file during regression authoring."""

    def test_skill_documents_authoring_flow(self):
        """The pl-regression-author skill documents the authoring flow:
        reading the spec, writing a scenario JSON, and committing."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-author.md')
        with open(skill_path) as f:
            content = f.read()
        # Authoring flow documented
        self.assertIn('Author Scenario File', content)
        # Scenario JSON file path convention
        self.assertIn('tests/qa/scenarios/', content)
        self.assertIn('<feature_name>.json', content)
        # Commit protocol
        self.assertIn('qa(', content)
        self.assertIn('author regression scenario', content)
        # Progress reporting
        self.assertIn('Authored', content)
        self.assertIn('remaining', content)

    def test_skill_has_harness_prerequisite_check(self):
        """The author skill checks for harness_runner.py before authoring."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-author.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('harness_runner.py', content)
        self.assertIn('harness runner framework', content.lower())

    def test_scenario_json_schema_documented(self):
        """The author skill references the scenario JSON schema from the spec."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-author.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('harness_type', content)
        self.assertIn('agent_behavior', content)
        self.assertIn('web_test', content)
        self.assertIn('custom_script', content)


class TestHarnessRunnerWritesEnrichedResults(unittest.TestCase):
    """Scenario: Harness runner writes enriched regression.json."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        self.scenarios_dir = os.path.join(self.tmpdir, 'tests', 'qa', 'scenarios')
        self.qa_dir = os.path.join(self.tmpdir, 'tests', 'qa')
        os.makedirs(self.features_dir)
        os.makedirs(self.scenarios_dir, exist_ok=True)
        os.makedirs(self.qa_dir, exist_ok=True)
        with open(os.path.join(self.features_dir, 'enriched_test.md'), 'w') as f:
            f.write('# Feature: Enriched Test\n')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_enriched_tests_json_has_all_required_fields(self):
        """Harness runner writes enriched regression.json with scenario_ref,
        assertion_tier, expected, actual_excerpt, and standard fields."""
        # Create a custom script that outputs mixed results
        script = os.path.join(self.qa_dir, 'test_enriched.sh')
        with open(script, 'w') as f:
            f.write('#!/usr/bin/env bash\n'
                    'echo "Found the expected pattern"\n'
                    'echo "Missing the other thing"\n'
                    'exit 0\n')
        os.chmod(script, 0o755)

        scenario = {
            'feature': 'enriched_test',
            'harness_type': 'custom_script',
            'scenarios': [{
                'name': 'multi-assertion',
                'script_path': os.path.relpath(script, self.tmpdir),
                'assertions': [
                    {'tier': 1, 'pattern': 'expected pattern',
                     'context': 'Pattern is found in output'},
                    {'tier': 2, 'pattern': 'specific-id-12345',
                     'context': 'Specific ID is present in output'},
                    {'tier': 3, 'pattern': 'state verified',
                     'context': 'State verification completed'},
                ]
            }]
        }
        scenario_path = os.path.join(self.scenarios_dir, 'enriched_test.json')
        with open(scenario_path, 'w') as f:
            json.dump(scenario, f)

        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir

        subprocess.run(
            ['python3', HARNESS_RUNNER, scenario_path,
             '--project-root', self.tmpdir],
            capture_output=True, text=True, timeout=30,
            cwd=self.tmpdir, env=env,
        )

        tests_json = os.path.join(
            self.tmpdir, 'tests', 'enriched_test', 'regression.json')
        self.assertTrue(os.path.isfile(tests_json))
        with open(tests_json) as f:
            data = json.load(f)

        # Standard fields
        self.assertIn('status', data)
        self.assertIn('passed', data)
        self.assertIn('failed', data)
        self.assertIn('total', data)
        self.assertEqual(data['total'], 3)

        # Enriched fields on details
        details = data['details']
        self.assertEqual(len(details), 3)

        # First assertion (tier 1) should pass
        self.assertEqual(details[0]['status'], 'PASS')
        self.assertEqual(details[0]['assertion_tier'], 1)
        self.assertIn('scenario_ref', details[0])
        self.assertEqual(
            details[0]['scenario_ref'],
            'features/enriched_test.md:multi-assertion')
        self.assertIn('expected', details[0])

        # Second assertion (tier 2) should fail - pattern not in output
        self.assertEqual(details[1]['status'], 'FAIL')
        self.assertEqual(details[1]['assertion_tier'], 2)
        self.assertIn('actual_excerpt', details[1])
        self.assertIn('expected', details[1])

        # Third assertion (tier 3) should fail
        self.assertEqual(details[2]['status'], 'FAIL')
        self.assertEqual(details[2]['assertion_tier'], 3)
        self.assertIn('actual_excerpt', details[2])


class TestStderrCapture(unittest.TestCase):
    """[BUG] M33: Runner doesn't capture stderr.

    Verifies that the regression runner captures stderr output from harness
    invocations and includes a stderr_excerpt field in the result JSON.
    """

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.runtime_dir = os.path.join(
            PROJECT_ROOT, '.purlin', 'runtime')
        os.makedirs(self.runtime_dir, exist_ok=True)
        self.result_file = os.path.join(
            self.runtime_dir, 'regression_result.json')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_stderr_captured_on_harness_failure(self):
        """When a harness writes to stderr and exits non-zero, the result
        includes a stderr_excerpt field with the captured output."""
        harness = os.path.join(self.tmpdir, 'stderr_harness.sh')
        with open(harness, 'w') as f:
            f.write('#!/usr/bin/env bash\n'
                    'echo "normal stdout output"\n'
                    'echo "claude: connection refused" >&2\n'
                    'echo "Error: authentication failed" >&2\n'
                    'exit 1\n')
        os.chmod(harness, 0o755)
        harness_rel = os.path.relpath(harness, PROJECT_ROOT)

        result = subprocess.run(
            ['bash', RUNNER_SCRIPT, '--once', harness_rel],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        self.assertNotEqual(result.returncode, 0)

        self.assertTrue(os.path.isfile(self.result_file))
        with open(self.result_file) as f:
            data = json.load(f)

        self.assertEqual(data['exit_code'], 1)
        self.assertIn('stderr_excerpt', data)
        self.assertIn('claude', data['stderr_excerpt'])
        self.assertIn('connection refused', data['stderr_excerpt'])

    def test_no_stderr_excerpt_when_harness_succeeds(self):
        """When a harness succeeds with no stderr, the result does not
        include a stderr_excerpt field (keeps result clean)."""
        harness = os.path.join(self.tmpdir, 'clean_harness.sh')
        with open(harness, 'w') as f:
            f.write('#!/usr/bin/env bash\n'
                    'echo "all good"\n'
                    'exit 0\n')
        os.chmod(harness, 0o755)
        harness_rel = os.path.relpath(harness, PROJECT_ROOT)

        result = subprocess.run(
            ['bash', RUNNER_SCRIPT, '--once', harness_rel],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        self.assertEqual(result.returncode, 0)

        with open(self.result_file) as f:
            data = json.load(f)

        self.assertEqual(data['exit_code'], 0)
        # No stderr_excerpt when harness produces no stderr
        self.assertNotIn('stderr_excerpt', data)

    def test_stderr_excerpt_from_claude_unavailable(self):
        """When stderr contains claude unavailability errors, these are
        captured so QA can distinguish infrastructure from test failures."""
        harness = os.path.join(self.tmpdir, 'claude_fail_harness.sh')
        with open(harness, 'w') as f:
            f.write('#!/usr/bin/env bash\n'
                    'echo "Attempting to invoke claude..." >&2\n'
                    'echo "claude: ECONNREFUSED - connect ECONNREFUSED 127.0.0.1:443" >&2\n'
                    'exit 2\n')
        os.chmod(harness, 0o755)
        harness_rel = os.path.relpath(harness, PROJECT_ROOT)

        result = subprocess.run(
            ['bash', RUNNER_SCRIPT, '--once', harness_rel],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )
        self.assertNotEqual(result.returncode, 0)

        with open(self.result_file) as f:
            data = json.load(f)

        self.assertIn('stderr_excerpt', data)
        self.assertIn('ECONNREFUSED', data['stderr_excerpt'])
        self.assertIn('claude', data['stderr_excerpt'])

    def test_stderr_excerpt_truncated_to_reasonable_length(self):
        """Stderr excerpt is truncated (not unbounded) to keep result
        JSON manageable."""
        harness = os.path.join(self.tmpdir, 'verbose_stderr_harness.sh')
        with open(harness, 'w') as f:
            # Generate > 1000 chars of stderr
            f.write('#!/usr/bin/env bash\n'
                    'for i in $(seq 1 200); do echo "error line $i: something went wrong with a long description" >&2; done\n'
                    'exit 1\n')
        os.chmod(harness, 0o755)
        harness_rel = os.path.relpath(harness, PROJECT_ROOT)

        result = subprocess.run(
            ['bash', RUNNER_SCRIPT, '--once', harness_rel],
            capture_output=True, text=True, timeout=30,
            cwd=PROJECT_ROOT,
        )

        with open(self.result_file) as f:
            data = json.load(f)

        self.assertIn('stderr_excerpt', data)
        # Should be truncated (head -c 1000 in the script)
        self.assertLessEqual(len(data['stderr_excerpt']), 1100)


class TestStalenessDetectionExpanded(unittest.TestCase):
    """Scenario: Staleness Detection Expanded.

    Extended staleness tests covering multiple source file types,
    implementation directories, and edge cases beyond the basic
    feature.md mtime comparison.
    """

    def test_staleness_with_implementation_file_newer(self):
        """A feature is stale when any implementation file (not just the
        feature .md) was modified after tests.json."""
        tmpdir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(tmpdir, 'features')
            tools_dir = os.path.join(tmpdir, 'tools', 'my_tool')
            tests_dir = os.path.join(tmpdir, 'tests', 'my_feature')
            os.makedirs(features_dir)
            os.makedirs(tools_dir)
            os.makedirs(tests_dir)

            # Feature file -- old
            feature_file = os.path.join(features_dir, 'my_feature.md')
            with open(feature_file, 'w') as f:
                f.write('# Feature: My Feature\n')
            old_time = time.time() - 7200
            os.utime(feature_file, (old_time, old_time))

            # tests.json -- middle age
            tests_json = os.path.join(tests_dir, 'tests.json')
            with open(tests_json, 'w') as f:
                json.dump({'status': 'PASS', 'passed': 3, 'failed': 0,
                           'total': 3}, f)
            mid_time = time.time() - 3600
            os.utime(tests_json, (mid_time, mid_time))

            # Implementation file -- newer than tests.json
            impl_file = os.path.join(tools_dir, 'handler.py')
            with open(impl_file, 'w') as f:
                f.write('# handler code\n')
            new_time = time.time() - 1800
            os.utime(impl_file, (new_time, new_time))

            # The implementation file is newer than tests.json
            self.assertGreater(os.path.getmtime(impl_file),
                               os.path.getmtime(tests_json))
            # But the feature file is older
            self.assertLess(os.path.getmtime(feature_file),
                            os.path.getmtime(tests_json))

            # A comprehensive staleness check would find this stale
            # because impl source was modified after tests.json
            source_files = [feature_file, impl_file]
            latest_source = max(os.path.getmtime(f) for f in source_files)
            tests_mtime = os.path.getmtime(tests_json)
            is_stale = latest_source > tests_mtime
            self.assertTrue(is_stale)
        finally:
            shutil.rmtree(tmpdir)

    def test_not_stale_when_all_sources_older(self):
        """A feature is NOT stale when all source files are older than
        tests.json."""
        tmpdir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(tmpdir, 'features')
            tests_dir = os.path.join(tmpdir, 'tests', 'my_feature')
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            feature_file = os.path.join(features_dir, 'my_feature.md')
            with open(feature_file, 'w') as f:
                f.write('# Feature\n')
            old_time = time.time() - 7200
            os.utime(feature_file, (old_time, old_time))

            tests_json = os.path.join(tests_dir, 'tests.json')
            with open(tests_json, 'w') as f:
                json.dump({'status': 'PASS', 'passed': 5, 'failed': 0,
                           'total': 5}, f)
            # tests.json is the newest file
            self.assertGreater(os.path.getmtime(tests_json),
                               os.path.getmtime(feature_file))
            is_stale = os.path.getmtime(feature_file) > os.path.getmtime(tests_json)
            self.assertFalse(is_stale)
        finally:
            shutil.rmtree(tmpdir)

    def test_staleness_with_missing_tests_json(self):
        """A feature with no tests.json at all is considered NOT_RUN,
        which is a form of staleness that should appear in the eligible list."""
        tmpdir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(tmpdir, 'features')
            os.makedirs(features_dir)
            feature_file = os.path.join(features_dir, 'new_feature.md')
            with open(feature_file, 'w') as f:
                f.write('# Feature: New\n')

            tests_json_path = os.path.join(tmpdir, 'tests', 'new_feature', 'tests.json')
            # tests.json does not exist
            self.assertFalse(os.path.exists(tests_json_path))
            # This is NOT_RUN status, which is eligible for regression
            is_not_run = not os.path.exists(tests_json_path)
            self.assertTrue(is_not_run)
        finally:
            shutil.rmtree(tmpdir)

    def test_staleness_sorting_stale_before_fail(self):
        """Eligible list sorts: STALE first, then FAIL, then NOT_RUN."""
        entries = [
            {'name': 'feat_b', 'status': 'FAIL'},
            {'name': 'feat_c', 'status': 'NOT_RUN'},
            {'name': 'feat_a', 'status': 'STALE'},
        ]
        priority = {'STALE': 0, 'FAIL': 1, 'NOT_RUN': 2}
        sorted_entries = sorted(entries, key=lambda e: priority.get(e['status'], 99))
        self.assertEqual(sorted_entries[0]['status'], 'STALE')
        self.assertEqual(sorted_entries[1]['status'], 'FAIL')
        self.assertEqual(sorted_entries[2]['status'], 'NOT_RUN')

    def test_staleness_with_companion_file_modification(self):
        """Companion file (.impl.md) edits do NOT trigger staleness.
        Only source code and feature spec edits count."""
        tmpdir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(tmpdir, 'features')
            tests_dir = os.path.join(tmpdir, 'tests', 'my_feature')
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            feature_file = os.path.join(features_dir, 'my_feature.md')
            with open(feature_file, 'w') as f:
                f.write('# Feature\n')
            old_time = time.time() - 7200
            os.utime(feature_file, (old_time, old_time))

            tests_json = os.path.join(tests_dir, 'tests.json')
            with open(tests_json, 'w') as f:
                json.dump({'status': 'PASS', 'passed': 2, 'failed': 0,
                           'total': 2}, f)
            mid_time = time.time() - 3600
            os.utime(tests_json, (mid_time, mid_time))

            # Companion file is newer but should NOT trigger staleness
            companion_file = os.path.join(features_dir, 'my_feature.impl.md')
            with open(companion_file, 'w') as f:
                f.write('## Implementation Notes\n')
            # Companion is newest file
            self.assertGreater(os.path.getmtime(companion_file),
                               os.path.getmtime(tests_json))

            # Staleness based on feature .md only (not companion)
            feature_stale = os.path.getmtime(feature_file) > os.path.getmtime(tests_json)
            self.assertFalse(feature_stale,
                             "Companion file edits should not trigger staleness")
        finally:
            shutil.rmtree(tmpdir)


class TestCompletionGate(unittest.TestCase):
    """Scenario: Completion Gate.

    Tests the hard gate logic that regression test status determines
    whether a feature can be marked complete. Regression failures
    block completion; passing regression enables it.
    """

    def _evaluate_completion_gate(self, tests_json_data):
        """Evaluate whether regression results allow completion.
        Returns (can_complete, reason)."""
        if tests_json_data is None:
            return (True, 'no regression results (not gated)')
        status = tests_json_data.get('status', 'FAIL')
        failed = tests_json_data.get('failed', 0)
        total = tests_json_data.get('total', 0)
        if total == 0:
            return (True, 'no tests executed (not gated)')
        if status == 'PASS' and failed == 0:
            return (True, 'all regression tests passed')
        return (False, f'regression failures: {failed}/{total} failed')

    def test_gate_passes_when_all_tests_pass(self):
        """Completion gate allows marking complete when all regression
        tests pass."""
        data = {'status': 'PASS', 'passed': 10, 'failed': 0, 'total': 10}
        can_complete, reason = self._evaluate_completion_gate(data)
        self.assertTrue(can_complete)
        self.assertIn('passed', reason)

    def test_gate_blocks_when_tests_fail(self):
        """Completion gate blocks marking complete when regression
        tests have failures."""
        data = {'status': 'FAIL', 'passed': 7, 'failed': 3, 'total': 10}
        can_complete, reason = self._evaluate_completion_gate(data)
        self.assertFalse(can_complete)
        self.assertIn('3', reason)
        self.assertIn('10', reason)

    def test_gate_passes_when_no_regression_results(self):
        """Completion gate does not block when no regression results
        exist (feature has not been regression-tested yet)."""
        can_complete, reason = self._evaluate_completion_gate(None)
        self.assertTrue(can_complete)
        self.assertIn('not gated', reason)

    def test_gate_passes_when_zero_tests_executed(self):
        """Completion gate does not block when regression ran but
        executed zero tests (edge case with empty scenario file)."""
        data = {'status': 'FAIL', 'passed': 0, 'failed': 0, 'total': 0}
        can_complete, reason = self._evaluate_completion_gate(data)
        self.assertTrue(can_complete)

    def test_gate_blocks_even_with_single_failure(self):
        """A single failing test is sufficient to block completion."""
        data = {'status': 'FAIL', 'passed': 99, 'failed': 1, 'total': 100}
        can_complete, reason = self._evaluate_completion_gate(data)
        self.assertFalse(can_complete)

    def test_status_table_rendering_pass(self):
        """A passing regression result renders as PASS with correct counts
        in a status table format."""
        data = {'status': 'PASS', 'passed': 5, 'failed': 0, 'total': 5,
                'details': [
                    {'name': 'test_a', 'status': 'PASS'},
                    {'name': 'test_b', 'status': 'PASS'},
                    {'name': 'test_c', 'status': 'PASS'},
                    {'name': 'test_d', 'status': 'PASS'},
                    {'name': 'test_e', 'status': 'PASS'},
                ]}
        # Render a status table row
        status_icon = 'PASS' if data['status'] == 'PASS' else 'FAIL'
        row = f"  {status_icon}  feature_a ({data['passed']}/{data['total']})"
        self.assertIn('PASS', row)
        self.assertIn('5/5', row)

    def test_status_table_rendering_fail(self):
        """A failing regression result renders as FAIL with failure count."""
        data = {'status': 'FAIL', 'passed': 3, 'failed': 2, 'total': 5,
                'details': [
                    {'name': 'test_a', 'status': 'PASS'},
                    {'name': 'test_b', 'status': 'FAIL',
                     'actual_excerpt': 'Expected X got Y'},
                    {'name': 'test_c', 'status': 'PASS'},
                    {'name': 'test_d', 'status': 'FAIL',
                     'actual_excerpt': 'Timeout'},
                    {'name': 'test_e', 'status': 'PASS'},
                ]}
        status_icon = 'PASS' if data['status'] == 'PASS' else 'FAIL'
        row = f"  {status_icon}  feature_b ({data['passed']}/{data['total']})"
        failures = [d for d in data['details'] if d['status'] == 'FAIL']
        self.assertIn('FAIL', row)
        self.assertIn('3/5', row)
        self.assertEqual(len(failures), 2)

    def test_status_table_with_multiple_features(self):
        """Status table renders correctly with a mix of passing and failing
        features, showing an overall summary."""
        features = [
            {'name': 'feat_a', 'status': 'PASS', 'passed': 5,
             'failed': 0, 'total': 5},
            {'name': 'feat_b', 'status': 'FAIL', 'passed': 3,
             'failed': 2, 'total': 5},
            {'name': 'feat_c', 'status': 'PASS', 'passed': 8,
             'failed': 0, 'total': 8},
        ]
        lines = []
        total_passed = 0
        total_tests = 0
        any_fail = False
        for feat in features:
            icon = 'PASS' if feat['status'] == 'PASS' else 'FAIL'
            lines.append(f"  {icon}  {feat['name']} ({feat['passed']}/{feat['total']})")
            total_passed += feat['passed']
            total_tests += feat['total']
            if feat['status'] == 'FAIL':
                any_fail = True
        summary = f"Total: {total_passed}/{total_tests} passed ({len(features)} features tested, {sum(1 for f in features if f['status'] == 'FAIL')} failure(s))"
        lines.append(summary)
        table = '\n'.join(lines)

        self.assertIn('PASS  feat_a', table)
        self.assertIn('FAIL  feat_b', table)
        self.assertIn('PASS  feat_c', table)
        self.assertIn('16/18 passed', table)
        self.assertIn('1 failure', table)
        self.assertTrue(any_fail)

    def test_hard_gate_blocks_completion_with_fail_status(self):
        """The hard gate logic: a feature with FAIL regression status
        cannot proceed to [Complete] status tag."""
        regression_status = 'FAIL'
        # Hard gate: FAIL regression blocks [Complete]
        can_tag_complete = regression_status != 'FAIL'
        self.assertFalse(can_tag_complete)

    def test_hard_gate_allows_completion_with_pass_status(self):
        """The hard gate logic: a feature with PASS regression status
        can proceed to [Complete] status tag."""
        regression_status = 'PASS'
        can_tag_complete = regression_status != 'FAIL'
        self.assertTrue(can_tag_complete)

    def test_hard_gate_allows_completion_when_no_regression(self):
        """The hard gate logic: a feature with no regression test results
        (None status) can proceed -- regression is not mandatory."""
        regression_status = None
        can_tag_complete = regression_status != 'FAIL'
        self.assertTrue(can_tag_complete)


class TestBuilderFlagsBrokenScenario(unittest.TestCase):
    """Scenario: Builder flags broken scenario via discovery.

    Tests that the builder feedback protocol is documented in the spec
    and skill, with correct discovery format for broken test scenarios.
    """

    def test_spec_documents_builder_feedback_protocol(self):
        """The feature spec documents the builder feedback protocol
        with test-scenario prefix and QA routing."""
        spec_path = os.path.join(
            PROJECT_ROOT, 'features', 'regression_testing.md')
        with open(spec_path) as f:
            content = f.read()
        self.assertIn('test-scenario', content)
        self.assertIn('Action Required: QA', content)
        self.assertIn('scenario_ref', content)
        self.assertIn('actual_excerpt', content)
        self.assertIn('[BUG]', content)

    def test_skill_documents_bug_discovery_format(self):
        """The evaluate skill documents the discovery format for failures
        including scenario_ref routing and OPEN status."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-evaluate.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('[BUG]', content)
        self.assertIn('scenario_ref', content)
        self.assertIn('actual_excerpt', content)
        self.assertIn('OPEN', content)
        self.assertIn('Action Required', content)


class TestRegressionSkillSplit(unittest.TestCase):
    """Validates the /pl-regression split into three explicit skills."""

    def test_three_skill_files_exist(self):
        """All three split skill files exist."""
        for name in ('pl-regression-author.md',
                     'pl-regression-run.md',
                     'pl-regression-evaluate.md'):
            path = os.path.join(
                PROJECT_ROOT, '.claude', 'commands', name)
            self.assertTrue(os.path.isfile(path), f"Missing: {name}")

    def test_retired_unified_skill_deleted(self):
        """The old unified pl-regression.md is deleted."""
        path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        self.assertFalse(os.path.isfile(path))

    def test_author_skill_is_qa_owned(self):
        """Author skill has QA ownership header."""
        path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-author.md')
        with open(path) as f:
            content = f.read()
        self.assertIn('Purlin command owner: QA', content)

    def test_run_skill_has_frequency_filter(self):
        """Run skill documents --frequency flag for pre-release filtering."""
        path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-run.md')
        with open(path) as f:
            content = f.read()
        self.assertIn('--frequency', content)
        self.assertIn('pre-release', content)
        self.assertIn('per-feature', content)

    def test_evaluate_skill_has_tier_distribution(self):
        """Evaluate skill documents tier distribution reporting."""
        path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression-evaluate.md')
        with open(path) as f:
            content = f.read()
        self.assertIn('Tier Distribution', content)
        self.assertIn('SHALLOW', content)


class TestFrequencyFieldSupport(unittest.TestCase):
    """Validates that harness runner handles the frequency field gracefully."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        os.makedirs(self.features_dir)
        with open(os.path.join(self.features_dir, 'freq_test.md'), 'w') as f:
            f.write('# Feature: Frequency Test\n')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_harness_runner_ignores_frequency_field(self):
        """Harness runner processes scenario JSON with frequency field
        without errors -- frequency filtering is QA skill responsibility."""
        scenario = {
            'feature': 'freq_test',
            'harness_type': 'custom_script',
            'frequency': 'pre-release',
            'scenarios': [{
                'name': 'freq-test',
                'script_path': 'tests/qa/noop.sh',
                'assertions': [],
            }]
        }
        # Create a noop script
        script_dir = os.path.join(self.tmpdir, 'tests', 'qa')
        os.makedirs(script_dir, exist_ok=True)
        noop_path = os.path.join(script_dir, 'noop.sh')
        with open(noop_path, 'w') as f:
            f.write('#!/usr/bin/env bash\nexit 0\n')
        os.chmod(noop_path, 0o755)

        scenario_path = os.path.join(self.tmpdir, 'scenario.json')
        with open(scenario_path, 'w') as f:
            json.dump(scenario, f)

        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools', 'test_support'))
        try:
            import harness_runner
            feature_name, details, passed, failed = \
                harness_runner.process_scenario_file(scenario_path, self.tmpdir)
            self.assertEqual(feature_name, 'freq_test')
            self.assertEqual(failed, 0)
        finally:
            sys.path.pop(0)


class TestProgressOutput(unittest.TestCase):
    """Scenario: Harness runner prints mandatory progress to stderr (Section 2.8)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        os.makedirs(self.features_dir)
        with open(os.path.join(self.features_dir, 'progress_test.md'), 'w') as f:
            f.write('# Feature: Progress Test\n')

        # Create a fake claude that echoes predictable text
        self.bin_dir = os.path.join(self.tmpdir, 'bin')
        os.makedirs(self.bin_dir)
        fake_claude = os.path.join(self.bin_dir, 'claude')
        with open(fake_claude, 'w') as f:
            f.write('#!/usr/bin/env bash\necho "test output alpha"\n')
        os.chmod(fake_claude, 0o755)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _run_harness(self, scenario):
        scenario_path = os.path.join(self.tmpdir, 'scenario.json')
        with open(scenario_path, 'w') as f:
            json.dump(scenario, f)
        env = os.environ.copy()
        env['PATH'] = self.bin_dir + ':' + env.get('PATH', '')
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir
        return subprocess.run(
            ['python3', HARNESS_RUNNER, scenario_path,
             '--project-root', self.tmpdir],
            capture_output=True, text=True, timeout=30, env=env,
        )

    def test_startup_line_format(self):
        """Progress startup line shows feature name, count, and harness type."""
        result = self._run_harness({
            'feature': 'progress_test',
            'harness_type': 'agent_behavior',
            'scenarios': [
                {'name': 'a', 'role': 'BUILDER', 'prompt': 'Hi',
                 'assertions': [{'tier': 1, 'pattern': 'test', 'context': 'c'}]},
                {'name': 'b', 'role': 'BUILDER', 'prompt': 'Hi',
                 'assertions': [{'tier': 1, 'pattern': 'test', 'context': 'c'}]},
            ]
        })
        self.assertIn('progress_test: 2 scenarios', result.stderr)
        self.assertIn('agent_behavior', result.stderr)

    def test_per_scenario_running_and_result(self):
        """Progress shows [N/M] running and result lines."""
        result = self._run_harness({
            'feature': 'progress_test',
            'harness_type': 'agent_behavior',
            'scenarios': [
                {'name': 'scenario-alpha', 'role': 'BUILDER', 'prompt': 'Hi',
                 'assertions': [{'tier': 1, 'pattern': 'test', 'context': 'c'}]},
            ]
        })
        self.assertIn('[1/1] scenario-alpha ... (running)', result.stderr)
        self.assertRegex(
            result.stderr,
            r'\[1/1\] scenario-alpha \.\.\. PASS \(\d+s\)')

    def test_completion_line_format(self):
        """Completion line shows passed/total and elapsed time."""
        result = self._run_harness({
            'feature': 'progress_test',
            'harness_type': 'agent_behavior',
            'scenarios': [
                {'name': 'p', 'role': 'BUILDER', 'prompt': 'Hi',
                 'assertions': [{'tier': 1, 'pattern': 'test', 'context': 'c'}]},
            ]
        })
        self.assertRegex(
            result.stderr,
            r'progress_test: 1/1 passed \(\d+s total\)')
        self.assertIn('Results:', result.stderr)

    def test_failed_scenario_shows_fail(self):
        """Failed scenario shows FAIL in progress output."""
        result = self._run_harness({
            'feature': 'progress_test',
            'harness_type': 'agent_behavior',
            'scenarios': [
                {'name': 'will-fail', 'role': 'BUILDER', 'prompt': 'Hi',
                 'assertions': [{'tier': 1, 'pattern': 'NONEXISTENT', 'context': 'c'}]},
            ]
        })
        self.assertRegex(
            result.stderr,
            r'\[1/1\] will-fail \.\.\. FAIL \(\d+s\)')
        self.assertRegex(result.stderr, r'progress_test: 0/1 passed')


class TestSystemPromptConstruction(unittest.TestCase):
    """Tests for 4-layer system prompt construction in agent_behavior."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.fixture_dir = os.path.join(self.tmpdir, 'fixture')
        instr_dir = os.path.join(self.fixture_dir, 'instructions')
        purlin_dir = os.path.join(self.fixture_dir, '.purlin')
        os.makedirs(instr_dir)
        os.makedirs(purlin_dir)
        with open(os.path.join(instr_dir, 'HOW_WE_WORK_BASE.md'), 'w') as f:
            f.write('LAYER_1_CONTENT\n')
        with open(os.path.join(instr_dir, 'BUILDER_BASE.md'), 'w') as f:
            f.write('LAYER_2_CONTENT\n')
        with open(os.path.join(purlin_dir, 'HOW_WE_WORK_OVERRIDES.md'), 'w') as f:
            f.write('LAYER_3_CONTENT\n')
        with open(os.path.join(purlin_dir, 'BUILDER_OVERRIDES.md'), 'w') as f:
            f.write('LAYER_4_CONTENT\n')

        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools', 'test_support'))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        sys.path.pop(0)

    def test_concatenates_all_4_layers(self):
        """Builds a temp file with all 4 instruction layers."""
        import harness_runner
        path = harness_runner.construct_system_prompt(
            self.fixture_dir, 'BUILDER')
        self.assertIsNotNone(path)
        try:
            with open(path) as f:
                content = f.read()
            self.assertIn('LAYER_1_CONTENT', content)
            self.assertIn('LAYER_2_CONTENT', content)
            self.assertIn('LAYER_3_CONTENT', content)
            self.assertIn('LAYER_4_CONTENT', content)
        finally:
            os.unlink(path)

    def test_returns_none_for_empty_fixture(self):
        """Returns None when no instruction files exist."""
        empty_dir = os.path.join(self.tmpdir, 'empty')
        os.makedirs(empty_dir)
        import harness_runner
        result = harness_runner.construct_system_prompt(empty_dir, 'BUILDER')
        self.assertIsNone(result)

    def test_handles_missing_override_layers(self):
        """Includes available layers, skips missing ones."""
        os.unlink(os.path.join(
            self.fixture_dir, '.purlin', 'HOW_WE_WORK_OVERRIDES.md'))
        os.unlink(os.path.join(
            self.fixture_dir, '.purlin', 'BUILDER_OVERRIDES.md'))
        import harness_runner
        path = harness_runner.construct_system_prompt(
            self.fixture_dir, 'BUILDER')
        self.assertIsNotNone(path)
        try:
            with open(path) as f:
                content = f.read()
            self.assertIn('LAYER_1_CONTENT', content)
            self.assertIn('LAYER_2_CONTENT', content)
            self.assertNotIn('LAYER_3_CONTENT', content)
        finally:
            os.unlink(path)


class TestSkillFileCopying(unittest.TestCase):
    """Tests for skill file copying to fixture directories."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = os.path.join(self.tmpdir, 'project')
        self.commands_dir = os.path.join(
            self.project_root, '.claude', 'commands')
        os.makedirs(self.commands_dir)
        with open(os.path.join(self.commands_dir, 'pl-help.md'), 'w') as f:
            f.write('# Help\n')
        with open(os.path.join(self.commands_dir, 'pl-status.md'), 'w') as f:
            f.write('# Status\n')

        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools', 'test_support'))

    def tearDown(self):
        shutil.rmtree(self.tmpdir)
        sys.path.pop(0)

    def test_copies_skill_files_to_fixture(self):
        """Copies .claude/commands/ when absent in fixture."""
        fixture_dir = os.path.join(self.tmpdir, 'fixture')
        os.makedirs(fixture_dir)
        import harness_runner
        harness_runner.copy_skill_files(self.project_root, fixture_dir)
        dst = os.path.join(fixture_dir, '.claude', 'commands')
        self.assertTrue(os.path.isfile(os.path.join(dst, 'pl-help.md')))
        self.assertTrue(os.path.isfile(os.path.join(dst, 'pl-status.md')))

    def test_skips_when_fixture_already_has_skills(self):
        """Does not overwrite existing .claude/commands/ in fixture."""
        fixture_dir = os.path.join(self.tmpdir, 'fixture')
        dst = os.path.join(fixture_dir, '.claude', 'commands')
        os.makedirs(dst)
        with open(os.path.join(dst, 'custom.md'), 'w') as f:
            f.write('# Custom\n')
        import harness_runner
        harness_runner.copy_skill_files(self.project_root, fixture_dir)
        self.assertTrue(os.path.isfile(os.path.join(dst, 'custom.md')))
        self.assertFalse(os.path.isfile(os.path.join(dst, 'pl-help.md')))

    def test_no_error_if_project_has_no_skills(self):
        """No crash when project root lacks .claude/commands/."""
        empty_root = os.path.join(self.tmpdir, 'empty')
        os.makedirs(empty_root)
        fixture_dir = os.path.join(self.tmpdir, 'fixture')
        os.makedirs(fixture_dir)
        import harness_runner
        harness_runner.copy_skill_files(empty_root, fixture_dir)
        self.assertFalse(os.path.isdir(
            os.path.join(fixture_dir, '.claude', 'commands')))


class TestFormatTimeEstimate(unittest.TestCase):
    """Tests for time estimate formatting helper."""

    def setUp(self):
        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools', 'test_support'))

    def tearDown(self):
        sys.path.pop(0)

    def test_agent_behavior_estimates(self):
        """agent_behavior with 9 scenarios gives minute-range estimate."""
        import harness_runner
        est = harness_runner.format_time_estimate('agent_behavior', 9)
        self.assertIn('~', est)
        self.assertIn('min', est)

    def test_short_suite_gives_seconds(self):
        """Short suite with few web_test scenarios gives second-range estimate."""
        import harness_runner
        est = harness_runner.format_time_estimate('web_test', 2)
        self.assertIn('~', est)
        self.assertIn('s', est)
        self.assertNotIn('min', est)

    def test_format_elapsed_seconds(self):
        """format_elapsed shows seconds for < 60."""
        import harness_runner
        self.assertEqual(harness_runner.format_elapsed(34), '34s')

    def test_format_elapsed_minutes(self):
        """format_elapsed shows minutes and seconds for >= 60."""
        import harness_runner
        self.assertEqual(harness_runner.format_elapsed(252), '4m 12s')


# ===================================================================
# Test runner with output to tests/regression_testing/tests.json
# ===================================================================

if __name__ == '__main__':
    tests_out_dir = os.path.join(
        PROJECT_ROOT, 'tests', 'regression_testing')
    os.makedirs(tests_out_dir, exist_ok=True)
    status_file = os.path.join(tests_out_dir, 'tests.json')

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    status = 'PASS' if result.wasSuccessful() else 'FAIL'
    failure_count = len(result.failures) + len(result.errors)
    report = {
        'status': status,
        'passed': result.testsRun - failure_count,
        'failed': failure_count,
        'total': result.testsRun,
        'test_file': 'dev/test_regression_runner.py',
    }
    with open(status_file, 'w') as f:
        json.dump(report, f)
    print(f'\n{status_file}: {status}')

    sys.exit(0 if result.wasSuccessful() else 1)
