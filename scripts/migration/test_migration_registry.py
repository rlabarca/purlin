#!/usr/bin/env python3
"""Unit tests for migration_registry.py.

Tests path computation, step preconditions, plan output, and CLI interface.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from migration_registry import (
    CURRENT_MIGRATION_VERSION,
    STEPS,
    Step1UnifiedAgentModel,
    Step2SubmoduleToPlugin,
    Step3PluginRefresh,
    compute_path,
    format_plan,
)


class TestComputePath(unittest.TestCase):
    """Test compute_path against various fingerprints."""

    def test_v07x_to_current(self):
        """Spec: v0.7.x -> steps [1, 2, 3]."""
        fp = {
            'model': 'submodule',
            'era': 'pre-unified-legacy',
            'version_hint': 'v0.7.x',
            'migration_version': None,
            'submodule_path': 'purlin',
        }
        path = compute_path(fp)
        self.assertEqual([s.step_id for s in path], [1, 2, 3])

    def test_v084_to_current(self):
        """v0.8.4 -> steps [1, 2, 3]."""
        fp = {
            'model': 'submodule',
            'era': 'pre-unified-with-pm',
            'version_hint': 'v0.8.4',
            'migration_version': None,
            'submodule_path': 'purlin',
        }
        path = compute_path(fp)
        self.assertEqual([s.step_id for s in path], [1, 2, 3])

    def test_v085_to_current(self):
        """Spec: v0.8.5 (migration_version=1) -> steps [2, 3]."""
        fp = {
            'model': 'submodule',
            'era': 'unified',
            'version_hint': 'v0.8.5',
            'migration_version': 1,
            'submodule_path': 'purlin',
        }
        path = compute_path(fp)
        self.assertEqual([s.step_id for s in path], [2, 3])

    def test_plugin_v090_to_current(self):
        """Spec: plugin v0.9.0 (migration_version=2) -> steps [3]."""
        fp = {
            'model': 'plugin',
            'era': 'plugin',
            'version_hint': 'v0.9.x',
            'migration_version': 2,
            'submodule_path': None,
        }
        path = compute_path(fp)
        self.assertEqual([s.step_id for s in path], [3])

    def test_already_current_empty_path(self):
        """Spec: migration_version=3 -> empty path."""
        fp = {
            'model': 'plugin',
            'era': 'plugin',
            'version_hint': 'v0.9.x',
            'migration_version': 3,
            'submodule_path': None,
        }
        path = compute_path(fp)
        self.assertEqual(path, [])

    def test_partial_migration_computes_full_path(self):
        """Spec: unified-partial (migration_version=None) -> steps [1, 2, 3]."""
        fp = {
            'model': 'submodule',
            'era': 'unified-partial',
            'version_hint': 'v0.8.4',
            'migration_version': None,
            'submodule_path': 'purlin',
        }
        path = compute_path(fp)
        self.assertEqual([s.step_id for s in path], [1, 2, 3])

    def test_none_model_returns_empty(self):
        """Non-Purlin project -> empty path."""
        fp = {
            'model': 'none',
            'era': None,
            'version_hint': None,
            'migration_version': None,
            'submodule_path': None,
        }
        path = compute_path(fp)
        self.assertEqual(path, [])

    def test_fresh_no_version_returns_empty(self):
        """Spec: fresh project with no migration_version -> empty (needs init)."""
        fp = {
            'model': 'fresh',
            'era': None,
            'version_hint': None,
            'migration_version': None,
            'submodule_path': None,
        }
        path = compute_path(fp)
        self.assertEqual(path, [])

    def test_fresh_with_version_computes_remaining(self):
        """Fresh project that has migration_version=2 -> step [3]."""
        fp = {
            'model': 'fresh',
            'era': None,
            'version_hint': None,
            'migration_version': 2,
            'submodule_path': None,
        }
        path = compute_path(fp)
        self.assertEqual([s.step_id for s in path], [3])

    def test_custom_target_version(self):
        """Compute path to specific target, not current."""
        fp = {
            'model': 'submodule',
            'era': 'pre-unified-legacy',
            'version_hint': 'v0.7.x',
            'migration_version': None,
            'submodule_path': 'purlin',
        }
        path = compute_path(fp, target_migration_version=1)
        self.assertEqual([s.step_id for s in path], [1])

    def test_v080_v083_to_current(self):
        """v0.8.0-v0.8.3 -> steps [1, 2, 3]."""
        fp = {
            'model': 'submodule',
            'era': 'pre-unified-modern',
            'version_hint': 'v0.8.0-v0.8.3',
            'migration_version': None,
            'submodule_path': 'purlin',
        }
        path = compute_path(fp)
        self.assertEqual([s.step_id for s in path], [1, 2, 3])


class TestFormatPlan(unittest.TestCase):
    """Test format_plan output."""

    def test_empty_steps_already_up_to_date(self):
        self.assertEqual(format_plan([], {}, '/tmp'), 'Already up to date.')

    def test_plan_contains_step_names(self):
        fp = {
            'model': 'submodule', 'era': 'unified',
            'migration_version': 1, 'submodule_path': 'purlin',
        }
        steps = compute_path(fp)
        text = format_plan(steps, fp, '/tmp')
        self.assertIn('Submodule to Plugin', text)
        self.assertIn('Plugin Refresh', text)
        self.assertNotIn('Unified Agent Model', text)


class TestStep1Preconditions(unittest.TestCase):
    """Test Step 1 preconditions."""

    def setUp(self):
        self.step = Step1UnifiedAgentModel()

    def test_rejects_non_submodule(self):
        fp = {'model': 'plugin', 'migration_version': None, 'era': 'plugin'}
        ok, reason = self.step.preconditions(fp, '/tmp')
        self.assertFalse(ok)

    def test_rejects_already_migrated(self):
        fp = {'model': 'submodule', 'migration_version': 1, 'era': 'unified'}
        ok, reason = self.step.preconditions(fp, '/tmp')
        self.assertFalse(ok)

    def test_accepts_pre_unified_legacy(self):
        fp = {'model': 'submodule', 'migration_version': None, 'era': 'pre-unified-legacy'}
        ok, reason = self.step.preconditions(fp, '/tmp')
        self.assertTrue(ok)

    def test_accepts_unified_partial(self):
        fp = {'model': 'submodule', 'migration_version': None, 'era': 'unified-partial'}
        ok, reason = self.step.preconditions(fp, '/tmp')
        self.assertTrue(ok)


class TestStep1Plan(unittest.TestCase):
    """Test Step 1 plan output."""

    def setUp(self):
        self.step = Step1UnifiedAgentModel()

    def test_partial_plan_mentions_repair(self):
        fp = {'era': 'unified-partial', 'migration_version': None}
        actions = self.step.plan(fp, '/tmp')
        self.assertTrue(any('Repair' in a or 'repair' in a for a in actions))

    def test_full_plan_mentions_consolidate(self):
        fp = {'era': 'pre-unified-legacy', 'migration_version': None}
        actions = self.step.plan(fp, '/tmp')
        self.assertTrue(any('Consolidate' in a or 'consolidate' in a for a in actions))


class TestStep1Execute(unittest.TestCase):
    """Test Step 1 execution with synthetic project dirs."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='purlin-step1-test-')
        self.step = Step1UnifiedAgentModel()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_json(self, relpath, data):
        path = os.path.join(self.tmpdir, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f)

    def test_consolidates_four_role_config(self):
        """Full consolidation: 4 roles -> agents.purlin."""
        self._write_json('.purlin/config.json', {
            'agents': {
                'architect': {'model': 'opus', 'startup_sequence': ['scan']},
                'builder': {'model': 'opus'},
                'qa': {'model': 'sonnet'},
                'pm': {'model': 'sonnet'},
            }
        })
        fp = {'model': 'submodule', 'era': 'pre-unified-legacy', 'migration_version': None}
        result = self.step.execute(fp, self.tmpdir)
        self.assertTrue(result)

        config = json.load(open(os.path.join(self.tmpdir, '.purlin', 'config.json')))
        self.assertIn('purlin', config['agents'])
        self.assertEqual(config['agents']['purlin']['model'], 'opus')
        self.assertNotIn('architect', config['agents'])
        self.assertNotIn('builder', config['agents'])
        self.assertNotIn('qa', config['agents'])
        self.assertNotIn('pm', config['agents'])
        self.assertEqual(config['_migration_version'], 1)

    def test_repairs_partial_migration(self):
        """Partial: adds missing keys to agents.purlin."""
        self._write_json('.purlin/config.json', {
            'agents': {
                'purlin': {'model': 'opus', 'effort': 'high'},
                'builder': {'model': 'opus'},
            }
        })
        fp = {'model': 'submodule', 'era': 'unified-partial', 'migration_version': None}
        result = self.step.execute(fp, self.tmpdir)
        self.assertTrue(result)

        config = json.load(open(os.path.join(self.tmpdir, '.purlin', 'config.json')))
        purlin = config['agents']['purlin']
        self.assertIn('find_work', purlin)
        self.assertIn('auto_start', purlin)
        self.assertIn('default_mode', purlin)
        self.assertNotIn('builder', config['agents'])
        self.assertEqual(config['_migration_version'], 1)

    def test_cleans_old_launchers(self):
        """Removes role-specific launcher scripts."""
        for name in ['pl-run-architect.sh', 'pl-run-builder.sh', 'run_qa.sh']:
            with open(os.path.join(self.tmpdir, name), 'w') as f:
                f.write('#!/bin/bash\n')
        self._write_json('.purlin/config.json', {
            'agents': {'architect': {'model': 'opus', 'startup_sequence': ['scan']}}
        })
        fp = {'model': 'submodule', 'era': 'pre-unified-legacy', 'migration_version': None}
        self.step.execute(fp, self.tmpdir)

        remaining = [f for f in os.listdir(self.tmpdir)
                     if f.endswith('.sh') and f != '.purlin']
        self.assertEqual(remaining, [])


class TestStep2Preconditions(unittest.TestCase):
    """Test Step 2 preconditions."""

    def setUp(self):
        self.step = Step2SubmoduleToPlugin()

    def test_rejects_non_submodule(self):
        fp = {'model': 'plugin', 'migration_version': 1, 'era': 'plugin'}
        ok, _ = self.step.preconditions(fp, '/tmp')
        self.assertFalse(ok)

    def test_rejects_step1_not_done(self):
        fp = {'model': 'submodule', 'migration_version': None, 'era': 'pre-unified-legacy'}
        ok, reason = self.step.preconditions(fp, '/tmp')
        self.assertFalse(ok)
        self.assertIn('Step 1', reason)

    def test_accepts_after_step1(self):
        fp = {'model': 'submodule', 'migration_version': 1, 'era': 'unified',
              'submodule_path': 'purlin'}
        # Need a real git repo for uncommitted changes check
        tmpdir = tempfile.mkdtemp()
        try:
            subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True, timeout=5)
            subprocess.run(['git', 'commit', '--allow-empty', '-m', 'init'],
                          cwd=tmpdir, capture_output=True, timeout=5)
            ok, _ = self.step.preconditions(fp, tmpdir)
            self.assertTrue(ok)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestStep3Preconditions(unittest.TestCase):
    """Test Step 3 preconditions."""

    def setUp(self):
        self.step = Step3PluginRefresh()

    def test_rejects_submodule(self):
        fp = {'model': 'submodule', 'migration_version': 2, 'era': 'unified'}
        ok, _ = self.step.preconditions(fp, '/tmp')
        self.assertFalse(ok)

    def test_accepts_plugin(self):
        fp = {'model': 'plugin', 'migration_version': 2, 'era': 'plugin'}
        ok, _ = self.step.preconditions(fp, '/tmp')
        self.assertTrue(ok)

    def test_accepts_fresh(self):
        fp = {'model': 'fresh', 'migration_version': 2, 'era': None}
        ok, _ = self.step.preconditions(fp, '/tmp')
        self.assertTrue(ok)

    def test_rejects_already_current(self):
        fp = {'model': 'plugin', 'migration_version': 3, 'era': 'plugin'}
        ok, _ = self.step.preconditions(fp, '/tmp')
        self.assertFalse(ok)


class TestStep3Execute(unittest.TestCase):
    """Test Step 3 execution."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='purlin-step3-test-')
        self.step = Step3PluginRefresh()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_stamps_version(self):
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        with open(os.path.join(self.tmpdir, '.purlin', 'config.json'), 'w') as f:
            json.dump({'_migration_version': 2}, f)
        fp = {'model': 'plugin', 'migration_version': 2, 'era': 'plugin'}
        result = self.step.execute(fp, self.tmpdir)
        self.assertTrue(result)

        config = json.load(open(os.path.join(self.tmpdir, '.purlin', 'config.json')))
        self.assertEqual(config['_migration_version'], 3)

    def test_cleans_stale_artifacts(self):
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        with open(os.path.join(self.tmpdir, '.purlin', 'config.json'), 'w') as f:
            json.dump({}, f)
        # Create stale artifact
        with open(os.path.join(self.tmpdir, 'pl-run.sh'), 'w') as f:
            f.write('#!/bin/bash\n')
        fp = {'model': 'plugin', 'migration_version': 2, 'era': 'plugin'}
        self.step.execute(fp, self.tmpdir)
        self.assertFalse(os.path.exists(os.path.join(self.tmpdir, 'pl-run.sh')))


class TestStepRegistry(unittest.TestCase):
    """Test the STEPS registry itself."""

    def test_steps_are_ordered(self):
        ids = [s.step_id for s in STEPS]
        self.assertEqual(ids, [1, 2, 3])

    def test_current_version_matches_last_step(self):
        self.assertEqual(CURRENT_MIGRATION_VERSION, STEPS[-1].step_id)

    def test_all_steps_have_required_attrs(self):
        for step in STEPS:
            self.assertIsInstance(step.step_id, int)
            self.assertIsInstance(step.name, str)
            self.assertIsInstance(step.from_era, str)
            self.assertIsInstance(step.to_era, str)


class TestCLI(unittest.TestCase):
    """Test CLI interface."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='purlin-registry-cli-')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_cli_dry_run_plugin(self):
        """CLI with plugin project at mv=2 shows step 3."""
        os.makedirs(os.path.join(self.tmpdir, '.claude'))
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        with open(os.path.join(self.tmpdir, '.claude', 'settings.json'), 'w') as f:
            json.dump({'enabledPlugins': {'purlin@purlin': True}}, f)
        with open(os.path.join(self.tmpdir, '.purlin', 'config.json'), 'w') as f:
            json.dump({'_migration_version': 2}, f)

        script = os.path.join(os.path.dirname(__file__), 'migration_registry.py')
        result = subprocess.run(
            ['python3', script, '--project-root', self.tmpdir, '--dry-run'],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('Plugin Refresh', result.stdout)

    def test_cli_already_current(self):
        """CLI with already-current project shows up to date."""
        os.makedirs(os.path.join(self.tmpdir, '.claude'))
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        with open(os.path.join(self.tmpdir, '.claude', 'settings.json'), 'w') as f:
            json.dump({'enabledPlugins': {'purlin@purlin': True}}, f)
        with open(os.path.join(self.tmpdir, '.purlin', 'config.json'), 'w') as f:
            json.dump({'_migration_version': 3}, f)

        script = os.path.join(os.path.dirname(__file__), 'migration_registry.py')
        result = subprocess.run(
            ['python3', script, '--project-root', self.tmpdir, '--dry-run'],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn('Already up to date', result.stdout)

    def test_cli_none_project_exits_1(self):
        """CLI with non-Purlin directory exits with code 1."""
        script = os.path.join(os.path.dirname(__file__), 'migration_registry.py')
        result = subprocess.run(
            ['python3', script, '--project-root', self.tmpdir, '--dry-run'],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn('Not a Purlin project', result.stdout)


if __name__ == '__main__':
    unittest.main()
