#!/usr/bin/env python3
"""Unit tests for version_detector.py.

Tests version detection against synthetic project directories —
no fixture repo required.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from version_detector import detect_version


class TestVersionDetector(unittest.TestCase):
    """Test detect_version against synthetic project states."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix='purlin-detect-test-')

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_json(self, relpath, data):
        path = os.path.join(self.tmpdir, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            json.dump(data, f)

    def _write_file(self, relpath, content=''):
        path = os.path.join(self.tmpdir, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)

    # --- Model detection ---

    def test_none_model_empty_dir(self):
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['model'], 'none')

    def test_fresh_model_purlin_dir_only(self):
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['model'], 'fresh')

    def test_plugin_model_detected(self):
        self._write_json('.claude/settings.json', {
            'enabledPlugins': {'purlin@purlin': True}
        })
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {'_migration_version': 2})
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['model'], 'plugin')
        self.assertEqual(fp['era'], 'plugin')
        self.assertEqual(fp['migration_version'], 2)

    def test_submodule_model_detected(self):
        self._write_file('.gitmodules',
                         '[submodule "purlin"]\n\tpath = purlin\n\turl = git@github.com:org/purlin.git\n')
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {
            'agents': {'purlin': {'model': 'opus', 'effort': 'high', 'find_work': True}}
        })
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['model'], 'submodule')
        self.assertEqual(fp['submodule_path'], 'purlin')

    def test_plugin_takes_priority_over_submodule(self):
        """If both plugin and submodule signals exist, plugin wins."""
        self._write_json('.claude/settings.json', {
            'enabledPlugins': {'purlin@purlin': True}
        })
        self._write_file('.gitmodules',
                         '[submodule "purlin"]\n\tpath = purlin\n\turl = git@github.com:org/purlin.git\n')
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {})
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['model'], 'plugin')

    # --- Submodule era detection ---

    def test_era_pre_unified_legacy_v07x(self):
        self._write_file('.gitmodules',
                         '[submodule "purlin"]\n\tpath = purlin\n\turl = x\n')
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {
            'agents': {
                'architect': {
                    'model': 'opus',
                    'startup_sequence': ['scan', 'status']
                }
            }
        })
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['era'], 'pre-unified-legacy')
        self.assertEqual(fp['version_hint'], 'v0.7.x')

    def test_era_pre_unified_modern_v080_083(self):
        self._write_file('.gitmodules',
                         '[submodule "purlin"]\n\tpath = purlin\n\turl = x\n')
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {
            'agents': {
                'architect': {
                    'model': 'opus',
                    'find_work': True
                }
            }
        })
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['era'], 'pre-unified-modern')
        self.assertEqual(fp['version_hint'], 'v0.8.0-v0.8.3')

    def test_era_pre_unified_with_pm_v084(self):
        self._write_file('.gitmodules',
                         '[submodule "purlin"]\n\tpath = purlin\n\turl = x\n')
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {
            'agents': {
                'architect': {'model': 'opus'},
                'pm': {'model': 'sonnet'}
            }
        })
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['era'], 'pre-unified-with-pm')
        self.assertEqual(fp['version_hint'], 'v0.8.4')

    def test_era_unified_v085(self):
        self._write_file('.gitmodules',
                         '[submodule "purlin"]\n\tpath = purlin\n\turl = x\n')
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {
            '_migration_version': 1,
            'agents': {
                'purlin': {
                    'model': 'opus',
                    'effort': 'high',
                    'find_work': True,
                    'auto_start': False,
                    'default_mode': None
                }
            }
        })
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['era'], 'unified')
        self.assertEqual(fp['version_hint'], 'v0.8.5')
        self.assertEqual(fp['migration_version'], 1)

    def test_era_unified_partial_v084_gap(self):
        self._write_file('.gitmodules',
                         '[submodule "purlin"]\n\tpath = purlin\n\turl = x\n')
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {
            'agents': {
                'purlin': {'model': 'opus', 'effort': 'high'},
                'builder': {'model': 'opus'}
            }
        })
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['era'], 'unified-partial')
        self.assertEqual(fp['version_hint'], 'v0.8.4')
        self.assertIsNone(fp['migration_version'])

    # --- Config precedence ---

    def test_local_config_takes_precedence(self):
        self._write_json('.claude/settings.json', {
            'enabledPlugins': {'purlin@purlin': True}
        })
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {'_migration_version': 2})
        self._write_json('.purlin/config.local.json', {'_migration_version': 3})
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['migration_version'], 3)

    # --- Fresh project variants ---

    def test_fresh_with_config(self):
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {'fixture_repo_url': 'git@github.com:org/fix.git'})
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['model'], 'fresh')
        self.assertIsNone(fp['migration_version'])

    def test_fresh_with_migration_version(self):
        """Fresh project that has a migration_version — e.g., initialized by plugin but plugin not declared."""
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {'_migration_version': 3})
        fp = detect_version(self.tmpdir)
        self.assertEqual(fp['model'], 'fresh')
        self.assertEqual(fp['migration_version'], 3)

    # --- CLI interface ---

    def test_cli_outputs_valid_json(self):
        os.makedirs(os.path.join(self.tmpdir, '.purlin'))
        self._write_json('.purlin/config.json', {})
        script_path = os.path.join(os.path.dirname(__file__), 'version_detector.py')
        result = subprocess.run(
            ['python3', script_path, '--project-root', self.tmpdir],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        fp = json.loads(result.stdout)
        self.assertIn('model', fp)
        self.assertIn('era', fp)
        self.assertIn('migration_version', fp)


if __name__ == '__main__':
    unittest.main()
