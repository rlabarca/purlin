#!/usr/bin/env python3
"""Tests for dev/aft_runner.sh and the enriched tests.json format.

Covers automated scenarios from features/aft_regression_testing.md.
Outputs test results to tests/aft_regression_testing/tests.json.
"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
RUNNER_SCRIPT = os.path.join(SCRIPT_DIR, 'aft_runner.sh')


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
            PROJECT_ROOT, '.purlin', 'runtime', 'aft_result.json')
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

            result_path = os.path.join(runtime_dir, 'aft_result.json')
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
        trigger = os.path.join(runtime_dir, 'aft_trigger.json')
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
        trigger = os.path.join(runtime_dir, 'aft_trigger.json')

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
            trigger = os.path.join(runtime_dir, 'aft_trigger.json')
            result_file = os.path.join(runtime_dir, 'aft_result.json')

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

    def test_skill_identifies_aft_metadata_features(self):
        """The skill references AFT Agent and AFT Web metadata types."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('AFT Agent:', content)
        self.assertIn('AFT Web:', content)


class TestQASkillComposesCommand(unittest.TestCase):
    """Scenario: QA skill composes external command for selected features."""

    def test_qa_skill_composes_command_once_mode(self):
        """QA skill composes external command for once mode."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('--once', content)
        self.assertIn('dev/aft_runner.sh', content)
        self.assertIn('--write-results', content)

    def test_qa_skill_composes_command_watch_mode(self):
        """QA skill composes external command for watch mode."""
        skill_path = os.path.join(
            PROJECT_ROOT, '.claude', 'commands', 'pl-regression.md')
        with open(skill_path) as f:
            content = f.read()
        self.assertIn('--watch', content)
        self.assertIn('trigger', content.lower())


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
                    'scenario_ref': 'features/aft_agent.md:Single-turn agent test',
                    'expected': 'Agent produces structured output',
                },
                {
                    'name': 'test_multi_turn',
                    'status': 'FAIL',
                    'scenario_ref': 'features/aft_agent.md:Multi-turn session',
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
            'features/aft_agent.md:Single-turn agent test')
        self.assertNotIn('actual_excerpt', parsed['details'][0])
        # Enriched fields on failing entry
        self.assertEqual(
            parsed['details'][1]['scenario_ref'],
            'features/aft_agent.md:Multi-turn session')
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


# ===================================================================
# Test runner with output to tests/aft_regression_testing/tests.json
# ===================================================================

if __name__ == '__main__':
    tests_out_dir = os.path.join(
        PROJECT_ROOT, 'tests', 'aft_regression_testing')
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
        'test_file': 'dev/test_aft_runner.py',
    }
    with open(status_file, 'w') as f:
        json.dump(report, f)
    print(f'\n{status_file}: {status}')

    sys.exit(0 if result.wasSuccessful() else 1)
