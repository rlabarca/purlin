"""Tests for Purlin migration module — detection, config migration, and orchestrator."""

import json
import os
import tempfile
import unittest

from tools.migration.migrate import (
    detect_migration_needed,
    migrate_config,
    run_migration,
    _stamp_migration_version,
)


class _TempProject:
    """Helper to create a temporary project directory with .purlin/ config."""

    def __init__(self):
        self.tmpdir = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.tmpdir, '.purlin')
        os.makedirs(self.purlin_dir, exist_ok=True)

    def write_config(self, name, data):
        path = os.path.join(self.purlin_dir, name)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)

    def read_config(self, name):
        path = os.path.join(self.purlin_dir, name)
        with open(path, 'r') as f:
            return json.load(f)

    def cleanup(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestDetectMigrationNeeded(unittest.TestCase):

    def setUp(self):
        self.proj = _TempProject()

    def tearDown(self):
        self.proj.cleanup()

    def test_fresh_no_config(self):
        """No config files at all → fresh."""
        self.assertEqual(detect_migration_needed(self.proj.tmpdir), 'fresh')

    def test_needed_old_agents_no_purlin(self):
        """Old agents exist, no agents.purlin → needed."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'builder': {'model': 'claude-opus-4-6', 'effort': 'high'},
                'architect': {'model': 'claude-opus-4-6', 'effort': 'high'},
            }
        })
        self.assertEqual(detect_migration_needed(self.proj.tmpdir), 'needed')

    def test_complete_with_marker(self):
        """_migration_version present → complete (fast path)."""
        self.proj.write_config('config.local.json', {
            '_migration_version': 1,
            'agents': {
                'purlin': {'model': 'claude-opus-4-6', 'effort': 'high'},
            }
        })
        self.assertEqual(detect_migration_needed(self.proj.tmpdir), 'complete')

    def test_partial_missing_fields(self):
        """agents.purlin with only model+effort, no marker → partial."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {'model': 'claude-opus-4-6', 'effort': 'high'},
                'builder': {'model': 'claude-opus-4-6', 'effort': 'high'},
            }
        })
        self.assertEqual(detect_migration_needed(self.proj.tmpdir), 'partial')

    def test_partial_old_not_deprecated(self):
        """agents.purlin full but old agents not deprecated → partial."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {
                    'model': 'claude-opus-4-6', 'effort': 'high',
                    'bypass_permissions': True, 'find_work': True,
                    'auto_start': False, 'default_mode': None,
                },
                'builder': {'model': 'claude-opus-4-6', '_deprecated': False},
            }
        })
        self.assertEqual(detect_migration_needed(self.proj.tmpdir), 'partial')

    def test_complete_heuristic_full_config(self):
        """Full agents.purlin + deprecated old agents, no marker → complete."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {
                    'model': 'claude-opus-4-6', 'effort': 'high',
                    'bypass_permissions': True, 'find_work': True,
                    'auto_start': False, 'default_mode': None,
                },
                'builder': {'model': 'claude-opus-4-6', '_deprecated': True},
            }
        })
        self.assertEqual(detect_migration_needed(self.proj.tmpdir), 'complete')

    def test_complete_purlin_only_no_old_agents(self):
        """agents.purlin with full keys, no old agents at all → complete."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {
                    'model': 'claude-opus-4-6', 'effort': 'high',
                    'bypass_permissions': True, 'find_work': True,
                    'auto_start': False, 'default_mode': None,
                },
            }
        })
        self.assertEqual(detect_migration_needed(self.proj.tmpdir), 'complete')

    def test_partial_only_model_effort_no_old(self):
        """agents.purlin with only model+effort, no old agents → partial (missing fields)."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {'model': 'claude-opus-4-6', 'effort': 'high'},
            }
        })
        self.assertEqual(detect_migration_needed(self.proj.tmpdir), 'partial')


class TestMigrateConfig(unittest.TestCase):

    def setUp(self):
        self.proj = _TempProject()

    def tearDown(self):
        self.proj.cleanup()

    def test_full_migration(self):
        """Full migration creates agents.purlin and removes old entries."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'builder': {'model': 'opus', 'effort': 'high', 'bypass_permissions': True},
                'architect': {'model': 'opus', 'effort': 'high'},
            }
        })
        changes = migrate_config(self.proj.tmpdir)
        self.assertTrue(any('Created agents.purlin' in c for c in changes))

        config = self.proj.read_config('config.local.json')
        self.assertIn('purlin', config['agents'])
        self.assertTrue(config['agents']['purlin']['find_work'])
        self.assertFalse(config['agents']['purlin']['auto_start'])
        self.assertIsNone(config['agents']['purlin']['default_mode'])
        # Old entries removed, not just deprecated
        self.assertNotIn('builder', config['agents'])
        self.assertNotIn('architect', config['agents'])

    def test_enrichment_backfills_missing_keys(self):
        """Enrichment backfills missing keys from defaults."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {'model': 'opus', 'effort': 'high'},
                'builder': {'model': 'opus', 'effort': 'high', 'bypass_permissions': True},
            }
        })
        changes = migrate_config(self.proj.tmpdir)
        self.assertTrue(any('Enriched partial' in c for c in changes))

        config = self.proj.read_config('config.local.json')
        purlin = config['agents']['purlin']
        self.assertTrue(purlin['find_work'])
        self.assertFalse(purlin['auto_start'])
        self.assertIsNone(purlin['default_mode'])
        # bypass_permissions backfilled from builder
        self.assertTrue(purlin['bypass_permissions'])
        # Old agents removed
        self.assertNotIn('builder', config['agents'])

    def test_enrichment_uses_defaults_when_no_builder(self):
        """Enrichment uses hardcoded defaults when builder is absent."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {'model': 'opus', 'effort': 'high'},
            }
        })
        changes = migrate_config(self.proj.tmpdir)
        self.assertTrue(any('Enriched partial' in c or 'backfilled' in c for c in changes))

        config = self.proj.read_config('config.local.json')
        purlin = config['agents']['purlin']
        self.assertFalse(purlin['bypass_permissions'])  # default
        self.assertTrue(purlin['find_work'])

    def test_enrichment_removes_old_when_purlin_full(self):
        """Old entries removed even when agents.purlin has all keys."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {
                    'model': 'opus', 'effort': 'high',
                    'bypass_permissions': True, 'find_work': True,
                    'auto_start': False, 'default_mode': None,
                },
                'builder': {'model': 'opus'},
            }
        })
        changes = migrate_config(self.proj.tmpdir)
        self.assertTrue(any('Removed agents.builder' in c for c in changes))

        config = self.proj.read_config('config.local.json')
        self.assertNotIn('builder', config['agents'])

    def test_noop_when_only_purlin(self):
        """No changes when only agents.purlin exists with all keys."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {
                    'model': 'opus', 'effort': 'high',
                    'bypass_permissions': True, 'find_work': True,
                    'auto_start': False, 'default_mode': None,
                },
            }
        })
        changes = migrate_config(self.proj.tmpdir)
        self.assertEqual(changes, [])

    def test_dry_run_no_writes(self):
        """Dry run reports changes but writes nothing."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {'model': 'opus', 'effort': 'high'},
                'builder': {'model': 'opus'},
            }
        })
        changes = migrate_config(self.proj.tmpdir, dry_run=True)
        self.assertTrue(len(changes) > 0)

        # Config unchanged — old entries still present, purlin not enriched
        config = self.proj.read_config('config.local.json')
        self.assertNotIn('find_work', config['agents']['purlin'])
        self.assertIn('builder', config['agents'])


class TestStampMigrationVersion(unittest.TestCase):

    def setUp(self):
        self.proj = _TempProject()

    def tearDown(self):
        self.proj.cleanup()

    def test_stamps_marker(self):
        """Writes _migration_version to config."""
        self.proj.write_config('config.local.json', {'agents': {}})
        result = _stamp_migration_version(self.proj.tmpdir)
        self.assertIn('_migration_version', result)

        config = self.proj.read_config('config.local.json')
        self.assertEqual(config['_migration_version'], 1)

    def test_noop_when_already_stamped(self):
        """No-op when marker already exists."""
        self.proj.write_config('config.local.json', {'_migration_version': 1, 'agents': {}})
        result = _stamp_migration_version(self.proj.tmpdir)
        self.assertIsNone(result)

    def test_dry_run_no_write(self):
        """Dry run returns description but doesn't write."""
        self.proj.write_config('config.local.json', {'agents': {}})
        result = _stamp_migration_version(self.proj.tmpdir, dry_run=True)
        self.assertIn('_migration_version', result)

        config = self.proj.read_config('config.local.json')
        self.assertNotIn('_migration_version', config)


class TestRunMigrationPartial(unittest.TestCase):

    def setUp(self):
        self.proj = _TempProject()
        # Create features/ dir so override/spec steps don't fail
        os.makedirs(os.path.join(self.proj.tmpdir, 'features'), exist_ok=True)

    def tearDown(self):
        self.proj.cleanup()

    def test_partial_triggers_repair(self):
        """Partial state triggers repair pass and stamps marker."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {'model': 'opus', 'effort': 'high'},
                'builder': {'model': 'opus', 'effort': 'high'},
            }
        })
        result = run_migration(self.proj.tmpdir)
        self.assertEqual(result['status'], 'migrated')
        self.assertTrue(any('Partial migration' in c for c in result['changes']))
        self.assertTrue(any('_migration_version' in c for c in result['changes']))

        config = self.proj.read_config('config.local.json')
        self.assertEqual(config['_migration_version'], 1)
        self.assertTrue(config['agents']['purlin']['find_work'])
        # Old entries removed, not just deprecated
        self.assertNotIn('builder', config['agents'])

    def test_complete_stamps_marker_backfill(self):
        """Already-complete migration gets marker stamped on first check."""
        self.proj.write_config('config.local.json', {
            'agents': {
                'purlin': {
                    'model': 'opus', 'effort': 'high',
                    'bypass_permissions': True, 'find_work': True,
                    'auto_start': False, 'default_mode': None,
                },
                'builder': {'model': 'opus', '_deprecated': True},
            }
        })
        result = run_migration(self.proj.tmpdir)
        self.assertEqual(result['status'], 'complete')
        self.assertTrue(any('_migration_version' in c for c in result['changes']))

        config = self.proj.read_config('config.local.json')
        self.assertEqual(config['_migration_version'], 1)

    def test_complete_with_marker_skips_all(self):
        """Config with _migration_version skips everything."""
        self.proj.write_config('config.local.json', {
            '_migration_version': 1,
            'agents': {
                'purlin': {
                    'model': 'opus', 'effort': 'high',
                    'bypass_permissions': True, 'find_work': True,
                    'auto_start': False, 'default_mode': None,
                },
            }
        })
        result = run_migration(self.proj.tmpdir)
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['changes'], ['Migration already complete'])


if __name__ == '__main__':
    unittest.main()
