#!/usr/bin/env python3
"""Tests for config resolution, mode get/set, and classify_file in config_engine.py.

Each test creates an isolated temp directory, sets PURLIN_PROJECT_ROOT, and
resets module-level globals to prevent cross-test contamination.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

# ---------------------------------------------------------------------------
# Path setup: derive PLUGIN_ROOT from __file__ and add scripts/mcp/ to path.
# Walk up from this file's directory looking for scripts/mcp/config_engine.py.
# This supports both the main repo layout and git worktree checkouts.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


def _find_plugin_root():
    """Walk up from __file__ to find a directory containing scripts/mcp/config_engine.py."""
    candidate = os.path.dirname(_THIS_DIR)  # dev/ -> project root
    for _ in range(10):
        if os.path.isfile(os.path.join(candidate, 'scripts', 'mcp', 'config_engine.py')):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    # Worktree fallback: resolve the main repo via the git common dir.
    # In a worktree, .git is a file (not a directory) containing a gitdir pointer
    # like "gitdir: /main-repo/.git/worktrees/<name>".  Walk up 3 levels from
    # that absolute path to reach the main repo root.
    git_dir = os.path.join(os.path.dirname(_THIS_DIR), '.git')
    if os.path.isfile(git_dir):
        with open(git_dir, 'r') as f:
            content = f.read().strip()
        if content.startswith('gitdir:'):
            real_git = os.path.abspath(content.split(':', 1)[1].strip())
            # /main-repo/.git/worktrees/<name> -> up 3 -> /main-repo
            main_repo = os.path.dirname(os.path.dirname(os.path.dirname(real_git)))
            if os.path.isfile(os.path.join(main_repo, 'scripts', 'mcp', 'config_engine.py')):
                return main_repo
    return os.path.dirname(_THIS_DIR)


PLUGIN_ROOT = _find_plugin_root()
_MCP_DIR = os.path.join(PLUGIN_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

import config_engine


class TestPluginConfig(unittest.TestCase):
    """Tests for resolve_config, sync_config, get_mode, set_mode, and classify_file."""

    def setUp(self):
        """Create a temp directory and reset module-level state."""
        self.tmpdir = tempfile.mkdtemp(prefix='purlin_test_')
        self.purlin_dir = os.path.join(self.tmpdir, '.purlin')
        os.makedirs(self.purlin_dir, exist_ok=True)

        # Save original env and set PURLIN_PROJECT_ROOT to our temp directory
        self._orig_env = os.environ.get('PURLIN_PROJECT_ROOT')
        os.environ['PURLIN_PROJECT_ROOT'] = self.tmpdir

        # Reset module-level caches so each test starts clean
        config_engine._current_mode = None

    def tearDown(self):
        """Clean up temp directory and environment."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

        # Restore original env
        if self._orig_env is not None:
            os.environ['PURLIN_PROJECT_ROOT'] = self._orig_env
        else:
            os.environ.pop('PURLIN_PROJECT_ROOT', None)

        # Reset module state again to be safe
        config_engine._current_mode = None

    # ----- Helper methods -----

    def _write_json(self, filename, data):
        """Write a JSON file into .purlin/ directory."""
        path = os.path.join(self.purlin_dir, filename)
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        return path

    def _write_raw(self, filename, content):
        """Write raw text into .purlin/ directory."""
        path = os.path.join(self.purlin_dir, filename)
        with open(path, 'w') as f:
            f.write(content)
        return path

    # ----- resolve_config tests -----

    def test_resolve_local_wins(self):
        """When both config files exist, config.local.json is returned."""
        shared_data = {'source': 'shared', 'key': 'shared_value'}
        local_data = {'source': 'local', 'key': 'local_value'}
        self._write_json('config.json', shared_data)
        self._write_json('config.local.json', local_data)

        result = config_engine.resolve_config(self.tmpdir)
        self.assertEqual(result['source'], 'local')
        self.assertEqual(result['key'], 'local_value')

    def test_resolve_shared_fallback(self):
        """When only config.json exists, its contents are returned."""
        shared_data = {'source': 'shared', 'team': 'defaults'}
        self._write_json('config.json', shared_data)

        result = config_engine.resolve_config(self.tmpdir)
        self.assertEqual(result['source'], 'shared')
        self.assertEqual(result['team'], 'defaults')

    def test_copy_on_first_access(self):
        """When only config.json exists, config.local.json is created as a copy."""
        shared_data = {'copy_test': True, 'value': 42}
        self._write_json('config.json', shared_data)

        local_path = os.path.join(self.purlin_dir, 'config.local.json')
        self.assertFalse(os.path.exists(local_path))

        config_engine.resolve_config(self.tmpdir)

        self.assertTrue(os.path.exists(local_path))
        with open(local_path, 'r') as f:
            local_data = json.load(f)
        self.assertEqual(local_data['copy_test'], True)
        self.assertEqual(local_data['value'], 42)

    def test_malformed_local_fallback(self):
        """Malformed config.local.json falls back to config.json."""
        shared_data = {'source': 'shared', 'fallback': True}
        self._write_json('config.json', shared_data)
        self._write_raw('config.local.json', '{invalid json!!!}')

        result = config_engine.resolve_config(self.tmpdir)
        self.assertEqual(result['source'], 'shared')
        self.assertTrue(result['fallback'])

    def test_neither_exists(self):
        """When no config files exist, returns an empty dict."""
        # .purlin/ exists but has no config files
        result = config_engine.resolve_config(self.tmpdir)
        self.assertEqual(result, {})

    # ----- get_mode / set_mode tests -----

    def test_set_mode_persists(self):
        """set_mode() creates the mode file on disk."""
        config_engine.set_mode('engineer')

        mode_path = os.path.join(self.purlin_dir, 'runtime', 'current_mode')
        self.assertTrue(os.path.isfile(mode_path))
        with open(mode_path, 'r') as f:
            content = f.read().strip()
        self.assertEqual(content, 'engineer')

    def test_get_mode_none(self):
        """get_mode() returns None when no mode file exists."""
        result = config_engine.get_mode()
        self.assertIsNone(result)

    def test_get_mode_reads_file(self):
        """get_mode() reads mode from the persisted file."""
        # Write mode file manually (simulating another process setting it)
        runtime_dir = os.path.join(self.purlin_dir, 'runtime')
        os.makedirs(runtime_dir, exist_ok=True)
        mode_path = os.path.join(runtime_dir, 'current_mode')
        with open(mode_path, 'w') as f:
            f.write('qa')

        result = config_engine.get_mode()
        self.assertEqual(result, 'qa')

    def test_mode_persistence_across_resets(self):
        """Mode persists on disk even after resetting the in-memory global."""
        config_engine.set_mode('pm')

        # Simulate a fresh process by clearing the in-memory cache
        config_engine._current_mode = None

        result = config_engine.get_mode()
        self.assertEqual(result, 'pm')

    def test_set_mode_all_valid_modes(self):
        """set_mode/get_mode round-trip for all valid mode values."""
        for mode in ('engineer', 'pm', 'qa'):
            config_engine._current_mode = None
            config_engine.set_mode(mode)
            config_engine._current_mode = None  # Force re-read from file
            self.assertEqual(config_engine.get_mode(), mode)

    # ----- classify_file basic test -----

    def test_classify_from_config_engine(self):
        """Basic classification test via the imported config_engine module."""
        self.assertEqual(config_engine.classify_file('features/login.md'), 'SPEC')
        self.assertEqual(config_engine.classify_file('src/main.py'), 'CODE')
        self.assertEqual(config_engine.classify_file('features/i_audit.md'), 'INVARIANT')
        self.assertEqual(config_engine.classify_file('app.discoveries.md'), 'QA')

    # ----- Edge cases -----

    def test_empty_config_dirs(self):
        """Empty .purlin/ directory returns empty config and None mode."""
        # .purlin/ already exists from setUp but is empty
        result = config_engine.resolve_config(self.tmpdir)
        self.assertEqual(result, {})

        config_engine._current_mode = None
        mode = config_engine.get_mode()
        self.assertIsNone(mode)


if __name__ == '__main__':
    unittest.main()
