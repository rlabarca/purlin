#!/usr/bin/env python3
"""Tests for config engine edge cases (tools/config/resolve_config.py).

Covers: missing .purlin/ directory, malformed config.json, empty config.json,
nested key writes via set_agent_config, config.local.json precedence,
copy-on-first-access behavior, CLI role output, and sync_config edge cases.
"""

import json
import os
import sys
import tempfile
import unittest
from io import StringIO
from unittest.mock import patch

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, PROJECT_ROOT)

from tools.config.resolve_config import (
    resolve_config,
    sync_config,
    _cli_set_agent_config,
    _cli_key,
    _cli_role,
    _cli_has_agent_config,
    _collect_all_keys,
)


class TestMissingPurlinDirectory(unittest.TestCase):
    """resolve_config should return {} when .purlin/ directory is absent."""

    def test_returns_empty_dict_no_purlin_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = resolve_config(tmpdir)
            self.assertEqual(result, {})

    def test_does_not_crash_on_nonexistent_root(self):
        fake_root = os.path.join(tempfile.gettempdir(), 'nonexistent_purlin_test_root')
        # Ensure it does not exist
        if os.path.exists(fake_root):
            os.rmdir(fake_root)
        result = resolve_config(fake_root)
        self.assertEqual(result, {})


class TestMalformedConfigJson(unittest.TestCase):
    """Invalid JSON in config files should be handled gracefully."""

    def test_malformed_config_json_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                f.write('{not valid json!!!')
            result = resolve_config(tmpdir)
            self.assertEqual(result, {})

    def test_malformed_local_falls_back_to_shared(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"key": "from_shared"}, f)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                f.write('totally broken {{{')
            result = resolve_config(tmpdir)
            self.assertEqual(result.get('key'), 'from_shared')

    def test_malformed_local_emits_warning(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"ok": True}, f)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                f.write('nope')
            stderr = StringIO()
            with patch('sys.stderr', stderr):
                resolve_config(tmpdir)
            self.assertIn('malformed', stderr.getvalue().lower())

    def test_both_malformed_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                f.write('bad')
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                f.write('also bad')
            result = resolve_config(tmpdir)
            self.assertEqual(result, {})


class TestEmptyConfigJson(unittest.TestCase):
    """Empty config files should not crash."""

    def test_empty_config_json_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                f.write('')
            result = resolve_config(tmpdir)
            self.assertEqual(result, {})

    def test_empty_local_falls_back_to_shared(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"fallback": True}, f)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                f.write('')
            result = resolve_config(tmpdir)
            self.assertEqual(result.get('fallback'), True)


class TestNestedKeyWrites(unittest.TestCase):
    """set_agent_config creates nested agents.<role>.<key> structures."""

    def test_creates_nested_agent_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            _cli_set_agent_config(tmpdir, 'purlin', 'model', 'claude-opus-4-20250514')
            local_path = os.path.join(purlin_dir, 'config.local.json')
            with open(local_path) as f:
                config = json.load(f)
            self.assertEqual(config['agents']['purlin']['model'], 'claude-opus-4-20250514')

    def test_creates_purlin_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _cli_set_agent_config(tmpdir, 'builder', 'effort', 'high')
            local_path = os.path.join(tmpdir, '.purlin', 'config.local.json')
            self.assertTrue(os.path.exists(local_path))
            with open(local_path) as f:
                config = json.load(f)
            self.assertEqual(config['agents']['builder']['effort'], 'high')

    def test_preserves_existing_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                json.dump({"project_name": "myproj", "agents": {"pm": {"model": "x"}}}, f)
            _cli_set_agent_config(tmpdir, 'purlin', 'model', 'y')
            with open(os.path.join(purlin_dir, 'config.local.json')) as f:
                config = json.load(f)
            self.assertEqual(config['project_name'], 'myproj')
            self.assertEqual(config['agents']['pm']['model'], 'x')
            self.assertEqual(config['agents']['purlin']['model'], 'y')

    def test_boolean_coercion_bypass_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            _cli_set_agent_config(tmpdir, 'purlin', 'bypass_permissions', 'true')
            with open(os.path.join(purlin_dir, 'config.local.json')) as f:
                config = json.load(f)
            self.assertIs(config['agents']['purlin']['bypass_permissions'], True)

    def test_boolean_coercion_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            _cli_set_agent_config(tmpdir, 'purlin', 'find_work', 'false')
            with open(os.path.join(purlin_dir, 'config.local.json')) as f:
                config = json.load(f)
            self.assertIs(config['agents']['purlin']['find_work'], False)

    def test_overwrite_existing_agent_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            _cli_set_agent_config(tmpdir, 'purlin', 'model', 'old')
            _cli_set_agent_config(tmpdir, 'purlin', 'model', 'new')
            with open(os.path.join(purlin_dir, 'config.local.json')) as f:
                config = json.load(f)
            self.assertEqual(config['agents']['purlin']['model'], 'new')


class TestLocalTakesPrecedence(unittest.TestCase):
    """config.local.json should win over config.json."""

    def test_local_overrides_shared(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"key": "shared_value", "other": "shared"}, f)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                json.dump({"key": "local_value"}, f)
            result = resolve_config(tmpdir)
            self.assertEqual(result['key'], 'local_value')
            # Local does NOT merge; "other" key from shared is absent
            self.assertNotIn('other', result)

    def test_local_is_not_merged_with_shared(self):
        """Resolution is winner-take-all, not a merge."""
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"a": 1, "b": 2}, f)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                json.dump({"a": 99}, f)
            result = resolve_config(tmpdir)
            self.assertEqual(result, {"a": 99})


class TestCopyOnFirstAccess(unittest.TestCase):
    """When config.local.json does not exist, it should be copied from config.json."""

    def test_creates_local_from_shared(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            shared_data = {"project_name": "test", "agents": {"purlin": {"model": "opus"}}}
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump(shared_data, f)
            result = resolve_config(tmpdir)
            self.assertEqual(result, shared_data)
            # config.local.json should now exist
            local_path = os.path.join(purlin_dir, 'config.local.json')
            self.assertTrue(os.path.exists(local_path))
            with open(local_path) as f:
                local_data = json.load(f)
            self.assertEqual(local_data, shared_data)

    def test_no_copy_when_local_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"source": "shared"}, f)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                json.dump({"source": "local"}, f)
            result = resolve_config(tmpdir)
            self.assertEqual(result['source'], 'local')

    def test_copy_on_first_access_returns_shared_content(self):
        """Even though local is created, the returned data matches shared."""
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"value": 42}, f)
            result = resolve_config(tmpdir)
            self.assertEqual(result['value'], 42)


class TestSyncConfig(unittest.TestCase):
    """sync_config merges new keys from shared into local."""

    def test_adds_missing_keys_to_local(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"a": 1, "b": 2, "c": 3}, f)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                json.dump({"a": 100}, f)
            added = sync_config(tmpdir)
            self.assertIn('b', added)
            self.assertIn('c', added)
            with open(os.path.join(purlin_dir, 'config.local.json')) as f:
                local = json.load(f)
            self.assertEqual(local['a'], 100)  # preserved
            self.assertEqual(local['b'], 2)
            self.assertEqual(local['c'], 3)

    def test_creates_local_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"x": {"nested": True}}, f)
            added = sync_config(tmpdir)
            self.assertTrue(len(added) > 0)
            self.assertTrue(os.path.exists(os.path.join(purlin_dir, 'config.local.json')))

    def test_no_shared_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            added = sync_config(tmpdir)
            self.assertEqual(added, [])

    def test_nested_dict_sync(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"agents": {"purlin": {"model": "opus", "effort": "high"}}}, f)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                json.dump({"agents": {"purlin": {"model": "sonnet"}}}, f)
            added = sync_config(tmpdir)
            self.assertIn('agents.purlin.effort', added)
            with open(os.path.join(purlin_dir, 'config.local.json')) as f:
                local = json.load(f)
            self.assertEqual(local['agents']['purlin']['model'], 'sonnet')
            self.assertEqual(local['agents']['purlin']['effort'], 'high')


class TestCliKeyEdgeCases(unittest.TestCase):
    """_cli_key prints values for top-level config keys."""

    def test_missing_key_prints_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"a": 1}, f)
            with patch.dict(os.environ, {'PURLIN_PROJECT_ROOT': tmpdir}):
                out = StringIO()
                with patch('sys.stdout', out):
                    _cli_key(tmpdir, 'nonexistent')
                self.assertEqual(out.getvalue().strip(), '')

    def test_boolean_key_prints_true_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"enabled": True, "disabled": False}, f)
            out = StringIO()
            with patch('sys.stdout', out):
                _cli_key(tmpdir, 'enabled')
            self.assertEqual(out.getvalue().strip(), 'true')
            out2 = StringIO()
            with patch('sys.stdout', out2):
                _cli_key(tmpdir, 'disabled')
            self.assertEqual(out2.getvalue().strip(), 'false')

    def test_dict_key_prints_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"nested": {"a": 1}}, f)
            out = StringIO()
            with patch('sys.stdout', out):
                _cli_key(tmpdir, 'nested')
            parsed = json.loads(out.getvalue())
            self.assertEqual(parsed, {"a": 1})


class TestCliRoleEdgeCases(unittest.TestCase):
    """_cli_role prints shell variable assignments for agent settings."""

    def test_missing_role_prints_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({}, f)
            out = StringIO()
            with patch('sys.stdout', out):
                _cli_role(tmpdir, 'purlin')
            output = out.getvalue()
            self.assertIn('AGENT_MODEL=""', output)
            self.assertIn('AGENT_BYPASS="false"', output)

    def test_purlin_falls_back_to_builder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"agents": {"builder": {"model": "builder-model"}}}, f)
            out = StringIO()
            with patch('sys.stdout', out):
                _cli_role(tmpdir, 'purlin')
            self.assertIn('AGENT_MODEL="builder-model"', out.getvalue())

    def test_project_name_fallback_to_basename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({}, f)
            out = StringIO()
            with patch('sys.stdout', out):
                _cli_role(tmpdir, 'purlin')
            expected_name = os.path.basename(tmpdir)
            self.assertIn(f'PROJECT_NAME="{expected_name}"', out.getvalue())


class TestCliHasAgentConfig(unittest.TestCase):
    """_cli_has_agent_config checks for agents.<role> existence."""

    def test_returns_false_when_no_agents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({}, f)
            out = StringIO()
            with patch('sys.stdout', out):
                _cli_has_agent_config(tmpdir, 'purlin')
            self.assertEqual(out.getvalue().strip(), 'false')

    def test_returns_true_when_agent_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
                json.dump({"agents": {"purlin": {"model": "x"}}}, f)
            out = StringIO()
            with patch('sys.stdout', out):
                _cli_has_agent_config(tmpdir, 'purlin')
            self.assertEqual(out.getvalue().strip(), 'true')


class TestCollectAllKeys(unittest.TestCase):
    """_collect_all_keys collects leaf key paths in dot-notation."""

    def test_flat_dict(self):
        keys = _collect_all_keys({"a": 1, "b": 2})
        self.assertIn('a', keys)
        self.assertIn('b', keys)

    def test_nested_dict(self):
        keys = _collect_all_keys({"x": {"y": {"z": 1}}})
        self.assertEqual(keys, ['x.y.z'])

    def test_empty_dict(self):
        keys = _collect_all_keys({})
        self.assertEqual(keys, [])

    def test_mixed_nesting(self):
        keys = _collect_all_keys({"a": 1, "b": {"c": 2, "d": {"e": 3}}})
        self.assertIn('a', keys)
        self.assertIn('b.c', keys)
        self.assertIn('b.d.e', keys)
        self.assertEqual(len(keys), 3)


class TestAcknowledgeWarning(unittest.TestCase):
    """_cli_acknowledge_warning persists model IDs."""

    def test_adds_model_to_acknowledged(self):
        from tools.config.resolve_config import _cli_acknowledge_warning
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                json.dump({}, f)
            _cli_acknowledge_warning(tmpdir, 'test-model')
            with open(os.path.join(purlin_dir, 'config.local.json')) as f:
                config = json.load(f)
            self.assertIn('test-model', config['acknowledged_warnings'])

    def test_idempotent_acknowledge(self):
        from tools.config.resolve_config import _cli_acknowledge_warning
        with tempfile.TemporaryDirectory() as tmpdir:
            purlin_dir = os.path.join(tmpdir, '.purlin')
            os.makedirs(purlin_dir)
            with open(os.path.join(purlin_dir, 'config.local.json'), 'w') as f:
                json.dump({}, f)
            _cli_acknowledge_warning(tmpdir, 'test-model')
            _cli_acknowledge_warning(tmpdir, 'test-model')
            with open(os.path.join(purlin_dir, 'config.local.json')) as f:
                config = json.load(f)
            self.assertEqual(config['acknowledged_warnings'].count('test-model'), 1)


if __name__ == '__main__':
    unittest.main()
