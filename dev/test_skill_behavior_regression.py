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
# Print-Mode Context Augmentation Tests
# ===================================================================

class TestScanFixtureFeatures(unittest.TestCase):
    """Tests scan_fixture_features() with realistic fixture directories."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.features_dir = os.path.join(self.tmpdir, 'features')
        os.makedirs(self.features_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_feature(self, name, content):
        with open(os.path.join(self.features_dir, name), 'w') as f:
            f.write(content)

    def test_classifies_todo_testing_complete(self):
        """Features are classified by their lifecycle tag."""
        self._write_feature('auth.md',
                            '# Feature: Auth\n> Label: "Authentication"\n[TODO]\n')
        self._write_feature('dashboard.md',
                            '# Feature: Dashboard\n> Label: "Dashboard UI"\n[TESTING]\n')
        self._write_feature('login.md',
                            '# Feature: Login\n> Label: "Login Flow"\n[COMPLETE]\n')

        result = harness_runner.scan_fixture_features(self.tmpdir)

        self.assertEqual(result['todo'], ['Authentication'])
        self.assertEqual(result['testing'], ['Dashboard UI'])
        self.assertEqual(result['complete'], ['Login Flow'])

    def test_uses_filename_when_no_label(self):
        """Falls back to filename stem when no Label declaration exists."""
        self._write_feature('my_feature.md', '# Feature: My Feature\n[TODO]\n')

        result = harness_runner.scan_fixture_features(self.tmpdir)

        self.assertEqual(result['todo'], ['my_feature'])

    def test_skips_companion_files(self):
        """Companion files (.impl.md) are excluded from scanning."""
        self._write_feature('auth.md',
                            '# Feature: Auth\n> Label: "Auth"\n[TODO]\n')
        self._write_feature('auth.impl.md',
                            '## Implementation Notes\n[TODO]\n')

        result = harness_runner.scan_fixture_features(self.tmpdir)

        self.assertEqual(len(result['todo']), 1)
        self.assertEqual(result['todo'], ['Auth'])

    def test_skips_discovery_sidecars(self):
        """Discovery sidecar files (.discoveries.md) are excluded."""
        self._write_feature('auth.md',
                            '# Feature: Auth\n> Label: "Auth"\n[COMPLETE]\n')
        self._write_feature('auth.discoveries.md',
                            '### [BUG] Something\n[TODO]\n')

        result = harness_runner.scan_fixture_features(self.tmpdir)

        self.assertEqual(len(result['complete']), 1)
        self.assertEqual(result['todo'], [])

    def test_skips_anchor_nodes(self):
        """Anchor nodes (arch_*, design_*, policy_*) are excluded."""
        self._write_feature('arch_data_layer.md',
                            '# Architecture: Data Layer\n[TODO]\n')
        self._write_feature('design_visual.md',
                            '# Design: Visual\n[TODO]\n')
        self._write_feature('policy_release.md',
                            '# Policy: Release\n[TODO]\n')
        self._write_feature('real_feature.md',
                            '# Feature: Real\n> Label: "Real Feature"\n[TODO]\n')

        result = harness_runner.scan_fixture_features(self.tmpdir)

        self.assertEqual(len(result['todo']), 1)
        self.assertEqual(result['todo'], ['Real Feature'])

    def test_empty_features_directory(self):
        """Returns empty lists when features directory is empty."""
        result = harness_runner.scan_fixture_features(self.tmpdir)

        self.assertEqual(result['todo'], [])
        self.assertEqual(result['testing'], [])
        self.assertEqual(result['complete'], [])

    def test_missing_features_directory(self):
        """Returns empty lists when features directory does not exist."""
        empty_dir = tempfile.mkdtemp()
        try:
            result = harness_runner.scan_fixture_features(empty_dir)
            self.assertEqual(result['todo'], [])
            self.assertEqual(result['testing'], [])
            self.assertEqual(result['complete'], [])
        finally:
            shutil.rmtree(empty_dir)

    def test_multiple_features_per_status(self):
        """Multiple features can share the same lifecycle status."""
        self._write_feature('a.md', '# Feature: A\n> Label: "Feature A"\n[TODO]\n')
        self._write_feature('b.md', '# Feature: B\n> Label: "Feature B"\n[TODO]\n')
        self._write_feature('c.md', '# Feature: C\n> Label: "Feature C"\n[TODO]\n')

        result = harness_runner.scan_fixture_features(self.tmpdir)

        self.assertEqual(len(result['todo']), 3)
        self.assertIn('Feature A', result['todo'])
        self.assertIn('Feature B', result['todo'])
        self.assertIn('Feature C', result['todo'])


class TestBuildPrintModeContext(unittest.TestCase):
    """Tests build_print_mode_context() with realistic fixture structures."""

    def setUp(self):
        self.fixture_dir = tempfile.mkdtemp()
        self.project_root = tempfile.mkdtemp()

        # Create fixture features directory with mixed lifecycle
        features_dir = os.path.join(self.fixture_dir, 'features')
        os.makedirs(features_dir)
        with open(os.path.join(features_dir, 'auth.md'), 'w') as f:
            f.write('# Feature: Auth\n> Label: "Authentication"\n[TODO]\n')
        with open(os.path.join(features_dir, 'login.md'), 'w') as f:
            f.write('# Feature: Login\n> Label: "Login Flow"\n[TESTING]\n')
        with open(os.path.join(features_dir, 'signup.md'), 'w') as f:
            f.write('# Feature: Signup\n> Label: "User Signup"\n[COMPLETE]\n')

        # Create command table in fixture
        refs_dir = os.path.join(
            self.fixture_dir, 'instructions', 'references')
        os.makedirs(refs_dir)
        self.architect_table = (
            '## Main Branch Variant\n\n```\n'
            'Purlin Architect — Ready\n'
            '━━━━━━━━━━━━━━━━━━━━━━━━\n'
            '  /pl-spec    Create specs\n'
            '  /pl-anchor  Create anchors\n'
            '━━━━━━━━━━━━━━━━━━━━━━━━\n```\n')
        with open(os.path.join(refs_dir, 'architect_commands.md'), 'w') as f:
            f.write(self.architect_table)

        # Create skill file in fixture
        commands_dir = os.path.join(self.fixture_dir, '.claude', 'commands')
        os.makedirs(commands_dir)
        self.help_skill = (
            '## Section 1: Role Detection\n'
            'Search for "Role Definition: The <Role>" in system prompt.\n')
        with open(os.path.join(commands_dir, 'pl-help.md'), 'w') as f:
            f.write(self.help_skill)

    def tearDown(self):
        shutil.rmtree(self.fixture_dir)
        shutil.rmtree(self.project_root)

    def test_includes_command_table(self):
        """Command table content is included in the context."""
        ctx = harness_runner.build_print_mode_context(
            self.fixture_dir, self.project_root, 'ARCHITECT', 'Begin session.')

        self.assertIn('━━━━━━━━━━━━━━━━━━━━━━━━', ctx)
        self.assertIn('/pl-spec', ctx)
        self.assertIn('/pl-anchor', ctx)

    def test_includes_feature_status(self):
        """Feature status summary is included with correct counts."""
        ctx = harness_runner.build_print_mode_context(
            self.fixture_dir, self.project_root, 'ARCHITECT', 'Begin session.')

        self.assertIn('TODO (1)', ctx)
        self.assertIn('Authentication', ctx)
        self.assertIn('TESTING (1)', ctx)
        self.assertIn('Login Flow', ctx)
        self.assertIn('COMPLETE (1)', ctx)
        self.assertIn('User Signup', ctx)

    def test_includes_skill_content_for_slash_commands(self):
        """Skill file content is included when prompt is a slash command."""
        ctx = harness_runner.build_print_mode_context(
            self.fixture_dir, self.project_root, 'ARCHITECT', '/pl-help')

        self.assertIn('Role Detection', ctx)
        self.assertIn('Role Definition', ctx)

    def test_no_skill_content_for_regular_prompts(self):
        """Skill content is NOT included for non-slash-command prompts."""
        ctx = harness_runner.build_print_mode_context(
            self.fixture_dir, self.project_root, 'ARCHITECT',
            'Edit main.py and fix the import.')

        self.assertNotIn('Role Detection', ctx)
        self.assertNotIn('Skill Content', ctx)

    def test_architect_role_enforcement(self):
        """Architect role enforcement mentions NEVER write code."""
        ctx = harness_runner.build_print_mode_context(
            self.fixture_dir, self.project_root, 'ARCHITECT', 'Begin session.')

        self.assertIn('NEVER write, edit, or create code files', ctx)
        self.assertIn('REFUSE', ctx)

    def test_builder_role_enforcement(self):
        """Builder role enforcement mentions spec files are Architect-owned."""
        # Create builder command table
        refs_dir = os.path.join(
            self.fixture_dir, 'instructions', 'references')
        with open(os.path.join(refs_dir, 'builder_commands.md'), 'w') as f:
            f.write('## Main Branch Variant\n\n```\n'
                    'Purlin Builder — Ready\n'
                    '━━━━━━━━━━━━━━━━━━━━━━━━\n'
                    '  /pl-build   Build features\n'
                    '━━━━━━━━━━━━━━━━━━━━━━━━\n```\n')

        ctx = harness_runner.build_print_mode_context(
            self.fixture_dir, self.project_root, 'BUILDER', 'Begin session.')

        self.assertIn('NEVER write, edit, or create feature spec files', ctx)
        self.assertIn('Architect-owned', ctx)

    def test_qa_role_enforcement(self):
        """QA role enforcement mentions NEVER write application code."""
        refs_dir = os.path.join(
            self.fixture_dir, 'instructions', 'references')
        with open(os.path.join(refs_dir, 'qa_commands.md'), 'w') as f:
            f.write('## Main Branch Variant\n\n```\n'
                    'Purlin QA — Ready\n'
                    '━━━━━━━━━━━━━━━━━━━━━━━━\n'
                    '  /pl-verify  Verify features\n'
                    '━━━━━━━━━━━━━━━━━━━━━━━━\n```\n')

        ctx = harness_runner.build_print_mode_context(
            self.fixture_dir, self.project_root, 'QA', 'Begin session.')

        self.assertIn('NEVER write, edit, or create application code', ctx)
        self.assertIn('Builder-owned', ctx)

    def test_falls_back_to_project_root_for_command_table(self):
        """Falls back to project_root when fixture has no command table."""
        # Remove fixture command table
        fixture_refs = os.path.join(
            self.fixture_dir, 'instructions', 'references')
        shutil.rmtree(fixture_refs)

        # Create command table in project root instead
        proj_refs = os.path.join(
            self.project_root, 'instructions', 'references')
        os.makedirs(proj_refs)
        with open(os.path.join(proj_refs, 'architect_commands.md'), 'w') as f:
            f.write('## Main Branch Variant\n\n```\n'
                    'Purlin Architect — Ready\n'
                    '━━━━━━━━━━━━━━━━━━━━━━━━\n'
                    '  /pl-spec    From project root\n'
                    '━━━━━━━━━━━━━━━━━━━━━━━━\n```\n')

        ctx = harness_runner.build_print_mode_context(
            self.fixture_dir, self.project_root, 'ARCHITECT', 'Begin session.')

        self.assertIn('From project root', ctx)
        self.assertIn('━━━━━━━━━━━━━━━━━━━━━━━━', ctx)

    def test_returns_empty_string_when_no_data(self):
        """Returns empty string when fixture has no relevant data."""
        empty_fixture = tempfile.mkdtemp()
        empty_project = tempfile.mkdtemp()
        try:
            ctx = harness_runner.build_print_mode_context(
                empty_fixture, empty_project, 'ARCHITECT', 'Begin session.')
            # Should still have role enforcement even without other data
            self.assertIn('CRITICAL: Role Enforcement', ctx)
        finally:
            shutil.rmtree(empty_fixture)
            shutil.rmtree(empty_project)


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
