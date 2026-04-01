#!/usr/bin/env python3
"""Tests for the Purlin v2 MCP server.

Tests the JSON-RPC transport, tool listing, sync_status with empty and
fixture specs, and purlin_config read/write.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

# Import the server module directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import purlin_server


class TestMCPTransport(unittest.TestCase):
    """Test JSON-RPC protocol handling."""

    def setUp(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))

    def tearDown(self):
        shutil.rmtree(self.project_root)

    def _call(self, method, params=None, req_id=1):
        request = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params:
            request["params"] = params
        return purlin_server.handle_request(request, self.project_root)

    def test_initialize(self):
        resp = self._call("initialize")
        self.assertEqual(resp["jsonrpc"], "2.0")
        self.assertEqual(resp["id"], 1)
        result = resp["result"]
        self.assertEqual(result["protocolVersion"], "2024-11-05")
        self.assertIn("tools", result["capabilities"])
        self.assertEqual(result["serverInfo"]["name"], "purlin")
        self.assertEqual(result["serverInfo"]["version"], "0.9.0")

    def test_initialized_notification(self):
        request = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = purlin_server.handle_request(request, self.project_root)
        self.assertIsNone(resp)

    def test_tools_list(self):
        resp = self._call("tools/list")
        tools = resp["result"]["tools"]
        names = [t["name"] for t in tools]
        self.assertIn("sync_status", names)
        self.assertIn("purlin_config", names)
        self.assertEqual(len(tools), 2)

    def test_unknown_method(self):
        resp = self._call("nonexistent/method")
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)

    def test_unknown_tool(self):
        resp = self._call("tools/call", {"name": "nonexistent", "arguments": {}})
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32601)


class TestSyncStatusEmpty(unittest.TestCase):
    """Test sync_status with no specs."""

    def setUp(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))

    def tearDown(self):
        shutil.rmtree(self.project_root)

    def test_no_specs_dir(self):
        result = purlin_server.sync_status(self.project_root)
        self.assertIn("No specs found", result)

    def test_empty_specs_dir(self):
        os.makedirs(os.path.join(self.project_root, 'specs'))
        result = purlin_server.sync_status(self.project_root)
        self.assertIn("No specs found", result)


class TestSyncStatusWithSpec(unittest.TestCase):
    """Test sync_status with fixture specs and proofs."""

    def setUp(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'auth')
        os.makedirs(self.spec_dir)

    def tearDown(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, name, content):
        path = os.path.join(self.spec_dir, f'{name}.md')
        with open(path, 'w') as f:
            f.write(content)

    def _write_proofs(self, name, proofs, tier='default'):
        path = os.path.join(self.spec_dir, f'{name}.proofs-{tier}.json')
        with open(path, 'w') as f:
            json.dump({"tier": tier, "proofs": proofs}, f)

    def test_spec_no_rules(self):
        self._write_spec('login', '# Feature: login\n\n## What it does\nHandles login.\n')
        result = purlin_server.sync_status(self.project_root)
        self.assertIn('login', result)
        self.assertIn('no rules defined', result)

    def test_spec_with_rules_no_proofs(self):
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n'
            '- RULE-1: Return 200 on valid creds\n'
            '- RULE-2: Return 401 on invalid creds\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): POST valid creds returns 200\n'
            '- PROOF-2 (RULE-2): POST bad creds returns 401\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        self.assertIn('login: 0/2 rules proved', result)
        self.assertIn('RULE-1: NO PROOF', result)
        self.assertIn('RULE-2: NO PROOF', result)

    def test_spec_with_all_proofs_passing(self):
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n'
            '- RULE-1: Return 200 on valid creds\n'
            '- RULE-2: Return 401 on invalid creds\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): POST valid creds returns 200\n'
            '- PROOF-2 (RULE-2): POST bad creds returns 401\n'
        ))
        self._write_proofs('login', [
            {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test_login.py", "test_name": "test_valid",
             "status": "pass", "tier": "default"},
            {"feature": "login", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "tests/test_login.py", "test_name": "test_invalid",
             "status": "pass", "tier": "default"},
        ])
        result = purlin_server.sync_status(self.project_root)
        self.assertIn('login: READY', result)
        self.assertIn('2/2 rules proved', result)
        self.assertIn('vhash=', result)

    def test_spec_with_failing_proof(self):
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n'
            '- RULE-1: Return 200 on valid creds\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): POST valid creds returns 200\n'
        ))
        self._write_proofs('login', [
            {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test_login.py", "test_name": "test_valid",
             "status": "fail", "tier": "default"},
        ])
        result = purlin_server.sync_status(self.project_root)
        self.assertIn('RULE-1: FAIL', result)

    def test_invariant_reporting(self):
        inv_dir = os.path.join(self.project_root, 'specs', '_invariants')
        os.makedirs(inv_dir)
        inv_path = os.path.join(inv_dir, 'i_colors.md')
        with open(inv_path, 'w') as f:
            f.write(
                '# Invariant: i_colors\n\n'
                '## What it does\nColor rules.\n\n'
                '## Rules\n'
                '- RULE-1: Primary is blue\n'
                '- RULE-2: Error is red\n'
            )
        result = purlin_server.sync_status(self.project_root)
        self.assertIn('i_colors', result)
        self.assertIn('2 rules (global', result)

    def test_unnumbered_rules_warning(self):
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n'
            '- Return 200 on valid creds\n'
            '- Return 401 on invalid creds\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        self.assertIn('WARNING', result)
        self.assertIn('not numbered', result)


class TestPurlinConfig(unittest.TestCase):
    """Test purlin_config MCP tool."""

    def setUp(self):
        self.project_root = tempfile.mkdtemp()
        self.purlin_dir = os.path.join(self.project_root, '.purlin')
        os.makedirs(self.purlin_dir)

    def tearDown(self):
        shutil.rmtree(self.project_root)

    def _call_config(self, arguments):
        return purlin_server.handle_purlin_config(self.project_root, arguments)

    def test_read_empty(self):
        result = self._call_config({"action": "read"})
        self.assertEqual(json.loads(result), {})

    def test_read_with_config(self):
        config_path = os.path.join(self.purlin_dir, 'config.json')
        with open(config_path, 'w') as f:
            json.dump({"version": "2.0.0", "test_framework": "auto"}, f)
        result = self._call_config({"action": "read"})
        data = json.loads(result)
        self.assertEqual(data["version"], "2.0.0")

    def test_read_specific_key(self):
        config_path = os.path.join(self.purlin_dir, 'config.json')
        with open(config_path, 'w') as f:
            json.dump({"version": "2.0.0", "test_framework": "pytest"}, f)
        result = self._call_config({"action": "read", "key": "test_framework"})
        data = json.loads(result)
        self.assertEqual(data["test_framework"], "pytest")

    def test_read_missing_key(self):
        result = self._call_config({"action": "read", "key": "nonexistent"})
        self.assertIn("not found", result)

    def test_write_and_read_back(self):
        self._call_config({"action": "write", "key": "test_framework", "value": "jest"})
        result = self._call_config({"action": "read", "key": "test_framework"})
        data = json.loads(result)
        self.assertEqual(data["test_framework"], "jest")

    def test_write_missing_key(self):
        result = self._call_config({"action": "write", "value": "something"})
        self.assertIn("Error", result)

    def test_unknown_action(self):
        result = self._call_config({"action": "delete"})
        self.assertIn("Unknown action", result)


if __name__ == '__main__':
    unittest.main()
