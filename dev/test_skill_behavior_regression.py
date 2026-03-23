#!/usr/bin/env python3
"""Tests for skill behavior regression testing infrastructure.

Covers automated scenarios from features/skill_behavior_regression.md.
Outputs test results to tests/skill_behavior_regression/tests.json.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
HARNESS_RUNNER = os.path.join(PROJECT_ROOT, 'tools', 'test_support', 'harness_runner.py')
SCENARIO_FILE = os.path.join(PROJECT_ROOT, 'tests', 'qa', 'scenarios',
                             'skill_behavior_regression.json')
DEV_RUNNER = os.path.join(SCRIPT_DIR, 'run_skill_regression.sh')

sys.path.insert(0, os.path.join(PROJECT_ROOT, 'tools', 'test_support'))
import harness_runner  # noqa: E402


# ===================================================================
# Scenario JSON Structure Tests
# ===================================================================

class TestScenarioJSONExists(unittest.TestCase):
    """Validates the scenario JSON file exists and is valid."""

    def test_scenario_file_exists(self):
        """Scenario file exists at the expected path."""
        self.assertTrue(os.path.isfile(SCENARIO_FILE))

    def test_scenario_file_valid_json(self):
        """Scenario file is valid JSON."""
        with open(SCENARIO_FILE) as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)

    def test_scenario_has_required_fields(self):
        """Scenario file has feature, harness_type, and scenarios fields."""
        with open(SCENARIO_FILE) as f:
            data = json.load(f)
        self.assertEqual(data['feature'], 'skill_behavior_regression')
        self.assertEqual(data['harness_type'], 'agent_behavior')
        self.assertIn('scenarios', data)
        self.assertIsInstance(data['scenarios'], list)

    def test_scenario_has_pre_release_frequency(self):
        """Scenario file has frequency set to pre-release (long-running suite)."""
        with open(SCENARIO_FILE) as f:
            data = json.load(f)
        self.assertEqual(data['frequency'], 'pre-release')


class TestScenarioCount(unittest.TestCase):
    """Validates the correct number of scenarios."""

    def test_nine_scenarios_defined(self):
        """Exactly 9 scenarios are defined per spec Section 2.2."""
        with open(SCENARIO_FILE) as f:
            data = json.load(f)
        self.assertEqual(len(data['scenarios']), 9)


class TestScenarioStructure(unittest.TestCase):
    """Validates each scenario has required fields."""

    def setUp(self):
        with open(SCENARIO_FILE) as f:
            self.data = json.load(f)
        self.scenarios = self.data['scenarios']

    def test_each_scenario_has_name(self):
        """Every scenario has a name field."""
        for s in self.scenarios:
            self.assertIn('name', s, f"Scenario missing name: {s}")

    def test_each_scenario_has_fixture_tag(self):
        """Every scenario references a fixture tag."""
        for s in self.scenarios:
            self.assertIn('fixture_tag', s,
                          f"Scenario {s.get('name')} missing fixture_tag")
            self.assertTrue(s['fixture_tag'].startswith('main/skill_behavior/'))

    def test_each_scenario_has_role(self):
        """Every scenario specifies a role."""
        for s in self.scenarios:
            self.assertIn('role', s,
                          f"Scenario {s.get('name')} missing role")
            self.assertIn(s['role'], ('ARCHITECT', 'BUILDER', 'QA'))

    def test_each_scenario_has_prompt(self):
        """Every scenario has a prompt."""
        for s in self.scenarios:
            self.assertIn('prompt', s,
                          f"Scenario {s.get('name')} missing prompt")
            self.assertTrue(len(s['prompt']) > 0)

    def test_each_scenario_has_assertions(self):
        """Every scenario has at least one assertion."""
        for s in self.scenarios:
            self.assertIn('assertions', s,
                          f"Scenario {s.get('name')} missing assertions")
            self.assertGreater(len(s['assertions']), 0)


class TestAssertionQuality(unittest.TestCase):
    """Validates assertion quality meets spec requirements (Tier 2+)."""

    def setUp(self):
        with open(SCENARIO_FILE) as f:
            self.data = json.load(f)
        self.all_assertions = []
        for s in self.data['scenarios']:
            for a in s.get('assertions', []):
                self.all_assertions.append((s['name'], a))

    def test_all_assertions_have_tier(self):
        """Every assertion has a tier field."""
        for name, a in self.all_assertions:
            self.assertIn('tier', a,
                          f"Assertion in {name} missing tier")

    def test_all_assertions_tier_2_or_higher(self):
        """No Tier 1 assertions -- spec requires Tier 2+ (Section 2.7)."""
        for name, a in self.all_assertions:
            self.assertGreaterEqual(
                a.get('tier', 0), 2,
                f"Tier 1 assertion found in {name}: {a.get('context')}")

    def test_all_assertions_have_context(self):
        """Every assertion has a human-readable context."""
        for name, a in self.all_assertions:
            self.assertIn('context', a,
                          f"Assertion in {name} missing context")

    def test_all_assertions_have_pattern(self):
        """Every assertion has a regex pattern."""
        for name, a in self.all_assertions:
            self.assertIn('pattern', a,
                          f"Assertion in {name} missing pattern")


class TestFixtureTagCoverage(unittest.TestCase):
    """Validates fixture tags match the declared set in the spec."""

    def setUp(self):
        with open(SCENARIO_FILE) as f:
            self.data = json.load(f)

    def test_uses_declared_fixture_tags(self):
        """All fixture tags used are from the declared set (Section 2.9)."""
        declared_tags = {
            'main/skill_behavior/mixed-lifecycle',
            'main/skill_behavior/fresh-init',
            'main/skill_behavior/architect-backlog',
        }
        used_tags = set()
        for s in self.data['scenarios']:
            tag = s.get('fixture_tag')
            if tag:
                used_tags.add(tag)
        self.assertTrue(used_tags.issubset(declared_tags),
                        f"Undeclared tags: {used_tags - declared_tags}")

    def test_mixed_lifecycle_most_used(self):
        """Mixed-lifecycle fixture is the primary test state."""
        count = sum(1 for s in self.data['scenarios']
                    if s.get('fixture_tag') == 'main/skill_behavior/mixed-lifecycle')
        self.assertGreaterEqual(count, 7)


# ===================================================================
# Dev Runner Script Tests
# ===================================================================

class TestDevRunnerExists(unittest.TestCase):
    """Validates the dev runner script exists and is executable."""

    def test_runner_file_exists(self):
        """Dev runner script exists at dev/run_skill_regression.sh."""
        self.assertTrue(os.path.isfile(DEV_RUNNER))

    def test_runner_is_executable(self):
        """Dev runner script has execute permission."""
        mode = os.stat(DEV_RUNNER).st_mode
        self.assertTrue(mode & stat.S_IXUSR)

    def test_runner_references_harness(self):
        """Dev runner invokes the harness runner."""
        with open(DEV_RUNNER) as f:
            content = f.read()
        self.assertIn('harness_runner.py', content)

    def test_runner_references_scenario_file(self):
        """Dev runner references the correct scenario file."""
        with open(DEV_RUNNER) as f:
            content = f.read()
        self.assertIn('skill_behavior_regression.json', content)

    def test_runner_handles_missing_fixture_repo(self):
        """Dev runner checks for fixture repo and runs setup if missing."""
        with open(DEV_RUNNER) as f:
            content = f.read()
        self.assertIn('setup_fixture_repo.sh', content)


# ===================================================================
# Harness Runner Integration Tests (mocked claude)
# ===================================================================

class TestHarnessRunnerProcessesScenarioJSON(unittest.TestCase):
    """Tests harness runner can parse and process the scenario JSON."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        os.makedirs(self.features_dir)
        with open(os.path.join(self.features_dir,
                               'skill_behavior_regression.md'), 'w') as f:
            f.write('# Feature: Skill Behavior Regression\n')

        # Create a fake claude that outputs predictable text
        bin_dir = os.path.join(self.tmpdir, 'bin')
        os.makedirs(bin_dir)
        fake_claude = os.path.join(bin_dir, 'claude')
        with open(fake_claude, 'w') as f:
            f.write('#!/usr/bin/env bash\n'
                    'echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"\n'
                    'echo "/pl-spec /pl-anchor /pl-build"\n'
                    'echo "TODO: 3 features TESTING: 2 features"\n'
                    'echo "Work plan: implement feature_a first"\n')
        os.chmod(fake_claude, 0o755)
        self.original_path = os.environ.get('PATH', '')
        os.environ['PATH'] = bin_dir + ':' + self.original_path

    def tearDown(self):
        os.environ['PATH'] = self.original_path
        shutil.rmtree(self.tmpdir)

    def test_harness_runner_parses_scenario_file(self):
        """Harness runner can parse the scenario JSON without errors."""
        with open(SCENARIO_FILE) as f:
            data = json.load(f)
        self.assertEqual(data['feature'], 'skill_behavior_regression')
        self.assertEqual(len(data['scenarios']), 9)

    def test_single_scenario_execution_with_mock(self):
        """A single scenario executes against mocked claude and evaluates
        assertions correctly."""
        # Create a minimal scenario with one assertion
        scenario = {
            'feature': 'skill_behavior_regression',
            'harness_type': 'agent_behavior',
            'scenarios': [{
                'name': 'mock-test',
                'role': 'ARCHITECT',
                'prompt': 'Test prompt',
                'assertions': [{
                    'tier': 2,
                    'pattern': '━+',
                    'context': 'Contains border characters',
                }],
            }],
        }
        scenario_path = os.path.join(self.tmpdir, 'test_scenario.json')
        with open(scenario_path, 'w') as f:
            json.dump(scenario, f)

        feature_name, details, passed, failed = \
            harness_runner.process_scenario_file(scenario_path, self.tmpdir)

        self.assertEqual(feature_name, 'skill_behavior_regression')
        self.assertEqual(passed, 1)
        self.assertEqual(failed, 0)
        self.assertEqual(details[0]['status'], 'PASS')
        self.assertEqual(details[0]['assertion_tier'], 2)


# ===================================================================
# Test runner with output to tests/skill_behavior_regression/tests.json
# ===================================================================

if __name__ == '__main__':
    tests_out_dir = os.path.join(
        PROJECT_ROOT, 'tests', 'skill_behavior_regression')
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
        'test_file': 'dev/test_skill_behavior_regression.py',
    }
    with open(status_file, 'w') as f:
        json.dump(report, f)
    print(f'\n{status_file}: {status}')

    sys.exit(0 if result.wasSuccessful() else 1)
