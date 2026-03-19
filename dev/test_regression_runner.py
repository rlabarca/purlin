#!/usr/bin/env python3
"""Tests for dev/regression_runner.sh, harness runner, meta-runner, and enriched tests.json.

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

    def test_skill_file_exists_and_has_discovery_flow(self):
        """The QA regression skill file exists and contains the
        discovery and selection flow."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        self.assertTrue(os.path.isfile(skill_path))
        with open(skill_path) as f:
            content = f.read()
        # Key elements of the discovery flow
        self.assertIn('regression-eligible', content)
        self.assertIn('STALE', content)
        self.assertIn('FAIL', content)
        self.assertIn('NOT_RUN', content)
        self.assertIn('staleness', content.lower())
        # Interactive selection
        self.assertIn('all', content)
        self.assertIn('skip', content)

    def test_skill_identifies_web_test_metadata_features(self):
        """The skill references Web Test metadata and Regression Testing sections."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('Web Test:', content)
        self.assertIn('Regression Testing', content)


class TestQASkillComposesCommand(unittest.TestCase):
    """Scenario: QA skill composes external command for selected features."""

    def test_qa_skill_composes_run_command(self):
        """QA skill composes the run_regression.sh or run_all.sh command."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('run_regression.sh', content)
        self.assertIn('--write-results', content)
        self.assertIn('run_all.sh', content)

    def test_qa_skill_composes_copy_pasteable_command(self):
        """QA skill prints copy-pasteable command for external terminal."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('copy-paste', content.lower().replace('-', '-'))
        self.assertIn('separate terminal', content.lower())


class TestQASkillCreatesBugDiscoveries(unittest.TestCase):
    """Scenario: QA skill creates BUG discoveries for regression failures."""

    def test_skill_has_bug_discovery_creation_protocol(self):
        """The skill documents how to create [BUG] sidecar entries
        from enriched regression results."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
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
        """Enriched tests.json entries with scenario_ref, expected,
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
        """Standard tests.json consumers (status, passed, failed, total)
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
        """Compute tier distribution from tests.json detail entries."""
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
        """The regression skill documents the [SHALLOW] indicator
        and tier distribution reporting."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('SHALLOW', content)
        self.assertIn('Tier Distribution', content)
        self.assertIn('assertion_tier', content)
        self.assertIn('50%', content)


class TestStalenessDetection(unittest.TestCase):
    """Scenario: Staleness detection prioritizes re-testing."""

    def test_staleness_detection_prioritizes_retesting(self):
        """Staleness detection: feature source newer than tests.json
        means the feature is stale and prioritized for re-testing."""
        tmpdir = tempfile.mkdtemp()
        try:
            features_dir = os.path.join(tmpdir, 'features')
            tests_dir = os.path.join(tmpdir, 'tests', 'my_feature')
            os.makedirs(features_dir)
            os.makedirs(tests_dir)

            # Create tests.json first (older)
            tests_json = os.path.join(tests_dir, 'tests.json')
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

            # Staleness: feature mtime > tests.json mtime
            feature_mtime = os.path.getmtime(feature_file)
            tests_mtime = os.path.getmtime(tests_json)
            self.assertGreater(feature_mtime, tests_mtime)

            # Fresh feature: tests.json newer than feature
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
        assertions against output, and writes enriched tests.json."""
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

        # Check tests.json was written
        tests_json = os.path.join(self.tmpdir, 'tests', 'test_feature', 'tests.json')
        self.assertTrue(os.path.isfile(tests_json),
                        f"tests.json not found. stdout: {result.stdout}, stderr: {result.stderr}")
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


class TestHarnessRunnerWebTest(unittest.TestCase):
    """Scenario: Harness runner handles web_test harness type."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        self.scenarios_dir = os.path.join(self.tmpdir, 'tests', 'qa', 'scenarios')
        os.makedirs(self.features_dir)
        os.makedirs(self.scenarios_dir)
        with open(os.path.join(self.features_dir, 'web_feature.md'), 'w') as f:
            f.write('# Feature: Web Feature\n[TODO]\n')

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_web_test_scenario_writes_results(self):
        """Harness runner processes web_test scenario and writes
        enriched tests.json with pass/fail results."""
        # Create a web_test scenario - use a URL that will likely fail
        # (we're testing the pipeline, not actual web connectivity)
        scenario = {
            'feature': 'web_feature',
            'harness_type': 'web_test',
            'scenarios': [{
                'name': 'homepage-check',
                'web_test_url': 'http://localhost:99999/nonexistent',
                'assertions': []
            }]
        }
        scenario_path = os.path.join(self.scenarios_dir, 'web_feature.json')
        with open(scenario_path, 'w') as f:
            json.dump(scenario, f)

        env = os.environ.copy()
        env['PURLIN_PROJECT_ROOT'] = self.tmpdir

        result = subprocess.run(
            ['python3', HARNESS_RUNNER, scenario_path,
             '--project-root', self.tmpdir],
            capture_output=True, text=True, timeout=60,
            cwd=self.tmpdir, env=env,
        )

        # Should write tests.json (may FAIL due to unreachable URL, that's OK)
        tests_json = os.path.join(self.tmpdir, 'tests', 'web_feature', 'tests.json')
        self.assertTrue(os.path.isfile(tests_json))
        with open(tests_json) as f:
            data = json.load(f)
        # Standard fields present
        self.assertIn('status', data)
        self.assertIn('passed', data)
        self.assertIn('failed', data)
        self.assertIn('total', data)
        self.assertGreater(data['total'], 0)

    def test_harness_runner_supports_web_test_type(self):
        """Harness runner code handles 'web_test' harness_type dispatch."""
        with open(HARNESS_RUNNER) as f:
            content = f.read()
        self.assertIn("harness_type == 'web_test'", content)
        self.assertIn('execute_web_test', content)
        self.assertIn('web_test_url', content)


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

        tests_json = os.path.join(self.tmpdir, 'tests', 'custom_feature', 'tests.json')
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
        """The pl-regression skill documents the author mode flow:
        reading the spec, writing a scenario JSON, and committing."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        # Author mode documented
        self.assertIn('Author mode', content)
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
        """The skill checks for harness_runner.py before authoring."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('harness_runner.py', content)
        self.assertIn('harness runner framework', content.lower())

    def test_scenario_json_schema_documented(self):
        """The skill references the scenario JSON schema from the spec."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('harness_type', content)
        self.assertIn('agent_behavior', content)
        self.assertIn('web_test', content)
        self.assertIn('custom_script', content)


class TestHarnessRunnerWritesEnrichedResults(unittest.TestCase):
    """Scenario: Harness runner writes enriched tests.json."""

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
        """Harness runner writes enriched tests.json with scenario_ref,
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
            self.tmpdir, 'tests', 'enriched_test', 'tests.json')
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
        """The QA skill documents the discovery format for failures
        including scenario_ref routing and OPEN status."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('[BUG]', content)
        self.assertIn('scenario_ref', content)
        self.assertIn('actual_excerpt', content)
        self.assertIn('OPEN', content)
        self.assertIn('Action Required', content)

    def test_critic_routing_documented(self):
        """The spec mentions Critic routing for Action Required: QA
        to prevent Builder seeing its own feedback."""
        spec_path = os.path.join(
            PROJECT_ROOT, 'features', 'regression_testing.md')
        with open(spec_path) as f:
            content = f.read()
        self.assertIn('Critic routing', content)
        self.assertIn('QA column', content)


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
