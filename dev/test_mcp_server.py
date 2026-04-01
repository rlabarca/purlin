"""Tests for the Purlin MCP server.

Tests the JSON-RPC transport, tool listing, sync_status with empty and
fixture specs, and purlin_config read/write.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import purlin_server


# ---------------------------------------------------------------------------
# Transport tests (RULE-1 through RULE-5)
# ---------------------------------------------------------------------------

class TestMCPTransport:
    """Test JSON-RPC protocol handling."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _call(self, method, params=None, req_id=1):
        request = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params:
            request["params"] = params
        return purlin_server.handle_request(request, self.project_root)

    @pytest.mark.proof("mcp-server", "PROOF-1", "RULE-1")
    def test_initialize(self):
        resp = self._call("initialize")
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        result = resp["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert "tools" in result["capabilities"]
        assert result["serverInfo"]["name"] == "purlin"
        assert result["serverInfo"]["version"] == "0.9.0"

    @pytest.mark.proof("mcp-server", "PROOF-2", "RULE-2")
    def test_initialized_notification(self):
        request = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = purlin_server.handle_request(request, self.project_root)
        assert resp is None

    @pytest.mark.proof("mcp-server", "PROOF-3", "RULE-3")
    def test_tools_list(self):
        resp = self._call("tools/list")
        tools = resp["result"]["tools"]
        names = sorted(t["name"] for t in tools)
        assert names == ["changelog", "purlin_config", "sync_status"]
        assert len(tools) == 3

    @pytest.mark.proof("mcp-server", "PROOF-4", "RULE-4")
    def test_unknown_method_and_tool(self):
        resp = self._call("nonexistent/method")
        assert resp["error"]["code"] == -32601

        resp = self._call("tools/call", {"name": "nonexistent", "arguments": {}})
        assert resp["error"]["code"] == -32601

    @pytest.mark.proof("mcp-server", "PROOF-5", "RULE-5")
    def test_parse_error(self):
        """Malformed JSON line produces response with error code -32700."""
        from io import StringIO
        from unittest.mock import patch

        bad_json = "this is not valid json\n"
        stdin_mock = StringIO(bad_json)
        stdout_mock = StringIO()

        with patch.dict(os.environ, {"PURLIN_PROJECT_ROOT": self.project_root}):
            with patch('sys.stdin', stdin_mock), patch('sys.stdout', stdout_mock):
                purlin_server.main()

        output = stdout_mock.getvalue().strip()
        resp = json.loads(output)
        assert resp["error"]["code"] == -32700


# ---------------------------------------------------------------------------
# sync_status tests (RULE-6 through RULE-10)
# ---------------------------------------------------------------------------

class TestSyncStatus:
    """Test sync_status with fixture specs and proofs."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'auth')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, name, content):
        path = os.path.join(self.spec_dir, f'{name}.md')
        with open(path, 'w') as f:
            f.write(content)

    def _write_proofs(self, name, proofs, tier='default'):
        path = os.path.join(self.spec_dir, f'{name}.proofs-{tier}.json')
        with open(path, 'w') as f:
            json.dump({"tier": tier, "proofs": proofs}, f)

    @pytest.mark.proof("mcp-server", "PROOF-6", "RULE-6")
    def test_spec_with_rules_no_proofs(self):
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n'
            '- RULE-1: Return 200 on valid creds\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): POST valid creds returns 200\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'login: 0/1 rules proved' in result
        assert 'RULE-1: NO PROOF' in result

    @pytest.mark.proof("mcp-server", "PROOF-7", "RULE-7")
    def test_all_rules_proved_shows_ready_and_vhash(self):
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
        assert 'login: READY' in result
        assert '2/2 rules proved' in result
        assert 'vhash=' in result

    @pytest.mark.proof("mcp-server", "PROOF-8", "RULE-8")
    def test_fail_takes_precedence_over_pass(self):
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
             "status": "pass", "tier": "default"},
            {"feature": "login", "id": "PROOF-1b", "rule": "RULE-1",
             "test_file": "tests/test_login.py", "test_name": "test_edge",
             "status": "fail", "tier": "default"},
        ])
        result = purlin_server.sync_status(self.project_root)
        assert 'RULE-1: FAIL' in result

    @pytest.mark.proof("mcp-server", "PROOF-9", "RULE-9")
    def test_manual_stamp_stale(self):
        """Manual stamp with outdated commit reports MANUAL PROOF STALE."""
        # Initialize a git repo in the temp dir
        subprocess.run(['git', 'init'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                       cwd=self.project_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                       cwd=self.project_root, capture_output=True, check=True)

        # Create a scope file and commit
        scope_dir = os.path.join(self.project_root, 'src')
        os.makedirs(scope_dir)
        scope_file = os.path.join(scope_dir, 'app.py')
        with open(scope_file, 'w') as f:
            f.write('v1')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'initial'],
                       cwd=self.project_root, capture_output=True, check=True)
        old_sha = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=self.project_root, capture_output=True, text=True, check=True
        ).stdout.strip()

        # Modify the scope file and commit again
        with open(scope_file, 'w') as f:
            f.write('v2')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'modify scope file'],
                       cwd=self.project_root, capture_output=True, check=True)

        # Write spec with manual stamp pointing to old SHA
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Scope: src/app.py\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n'
            '- RULE-1: Must authenticate\n\n'
            '## Proof\n'
            f'- PROOF-1 (RULE-1): Verified auth works @manual(dev@test.com, 2026-01-01, {old_sha})\n'
        ))

        result = purlin_server.sync_status(self.project_root)
        assert 'MANUAL PROOF STALE' in result

    @pytest.mark.proof("mcp-server", "PROOF-10", "RULE-10")
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
        assert 'i_colors' in result
        assert '2 rules (global' in result
