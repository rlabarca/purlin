"""Tests for mcp_server — 24 rules.

Covers JSON-RPC transport (initialize, tools/list, notifications, errors),
sync_status (coverage, READY/vhash, warnings, Requires, manual staleness,
structural-only detection, global invariants, rule labels, scope overlap),
purlin_config (read/write), changelog (since anchor, classification, structure,
structural_only flag, required rules in totals), server output (stderr logging),
and vhash computation.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from io import StringIO
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import purlin_server


class TestMCPProtocol:
    """RULE-1 through RULE-6: JSON-RPC transport."""

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

    @pytest.mark.proof("mcp_server", "PROOF-1", "RULE-1")
    def test_initialize(self):
        resp = self._call("initialize")
        result = resp["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert result["serverInfo"]["name"] == "purlin"

    @pytest.mark.proof("mcp_server", "PROOF-2", "RULE-2")
    def test_tools_list(self):
        resp = self._call("tools/list")
        tools = resp["result"]["tools"]
        names = sorted(t["name"] for t in tools)
        assert names == ["changelog", "purlin_config", "sync_status"]
        assert len(tools) == 3

    @pytest.mark.proof("mcp_server", "PROOF-3", "RULE-3")
    def test_notification_no_response(self):
        request = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = purlin_server.handle_request(request, self.project_root)
        assert resp is None

    @pytest.mark.proof("mcp_server", "PROOF-4", "RULE-4")
    def test_parse_error(self):
        stdin_mock = StringIO("not valid json\n")
        stdout_mock = StringIO()
        with patch.dict(os.environ, {"PURLIN_PROJECT_ROOT": self.project_root}):
            with patch('sys.stdin', stdin_mock), patch('sys.stdout', stdout_mock):
                purlin_server.main()
        resp = json.loads(stdout_mock.getvalue().strip())
        assert resp["error"]["code"] == -32700

    @pytest.mark.proof("mcp_server", "PROOF-5", "RULE-5")
    def test_unknown_method(self):
        resp = self._call("bogus")
        assert resp["error"]["code"] == -32601
        assert "bogus" in resp["error"]["message"]

    @pytest.mark.proof("mcp_server", "PROOF-6", "RULE-6")
    def test_unknown_tool(self):
        resp = self._call("tools/call", {"name": "nonexistent", "arguments": {}})
        assert resp["error"]["code"] == -32601
        assert "nonexistent" in resp["error"]["message"]


class TestSyncStatus:
    """RULE-7 through RULE-11: sync_status coverage reporting."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'auth')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, name, content, subdir='auth'):
        d = os.path.join(self.project_root, 'specs', subdir)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f'{name}.md'), 'w') as f:
            f.write(content)

    def _write_proofs(self, name, proofs, tier='default', subdir='auth'):
        d = os.path.join(self.project_root, 'specs', subdir)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f'{name}.proofs-{tier}.json'), 'w') as f:
            json.dump({"tier": tier, "proofs": proofs}, f)

    @pytest.mark.proof("mcp_server", "PROOF-7", "RULE-7")
    def test_rules_with_required_no_proofs(self):
        self._write_spec('api_conv', (
            '# Anchor: api_conv\n\n'
            '## What it does\nAPI conventions.\n\n'
            '## Rules\n- RULE-1: JSON envelope\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Check JSON\n'
        ), subdir='schema')
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Requires: api_conv\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n'
            '- RULE-1: Return 200 on valid creds\n'
            '- RULE-2: Return 401 on invalid creds\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): POST valid creds\n'
            '- PROOF-2 (RULE-2): POST invalid creds\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        # 2 own + 1 required = 3 total
        assert 'login: 0/3 rules proved' in result
        assert 'RULE-1: NO PROOF (own)' in result
        assert 'RULE-2: NO PROOF (own)' in result
        assert 'api_conv/RULE-1: NO PROOF (required)' in result

    @pytest.mark.proof("mcp_server", "PROOF-8", "RULE-8")
    def test_ready_with_vhash(self):
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        self._write_proofs('login', [
            {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_valid",
             "status": "pass", "tier": "default"},
        ])
        result = purlin_server.sync_status(self.project_root)
        assert 'login: READY' in result
        assert 'vhash=' in result

    @pytest.mark.proof("mcp_server", "PROOF-9", "RULE-9")
    def test_warns_unnumbered_rules(self):
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n'
            '- some unnumbered rule\n'
            '- RULE-1: A proper rule\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'WARNING' in result

    @pytest.mark.proof("mcp_server", "PROOF-10", "RULE-10")
    def test_requires_counts_for_coverage(self):
        inv_dir = os.path.join(self.project_root, 'specs', '_invariants')
        os.makedirs(inv_dir)
        with open(os.path.join(inv_dir, 'i_security.md'), 'w') as f:
            f.write(
                '# Invariant: i_security\n\n'
                '## What it does\nSecurity rules.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Requires: i_security\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        # 1 own + 1 required = 2 total
        assert 'login: 0/2 rules proved' in result
        assert 'i_security/RULE-1' in result
        assert '(required)' in result

    @pytest.mark.proof("mcp_server", "PROOF-11", "RULE-11")
    def test_manual_proof_staleness(self):
        subprocess.run(['git', 'init'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                       cwd=self.project_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                       cwd=self.project_root, capture_output=True, check=True)

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

        with open(scope_file, 'w') as f:
            f.write('v2')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'modify scope'],
                       cwd=self.project_root, capture_output=True, check=True)

        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Scope: src/app.py\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Must authenticate\n\n'
            '## Proof\n'
            f'- PROOF-1 (RULE-1): Verified auth @manual(dev@test.com, 2026-01-01, {old_sha})\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'MANUAL PROOF STALE' in result


    @pytest.mark.proof("mcp_server", "PROOF-20", "RULE-20")
    def test_scan_specs_detects_global(self):
        inv_dir = os.path.join(self.project_root, 'specs', '_invariants')
        os.makedirs(inv_dir, exist_ok=True)
        with open(os.path.join(inv_dir, 'i_security_no_eval.md'), 'w') as f:
            f.write(
                '# Invariant: i_security_no_eval\n\n'
                '> Global: true\n\n'
                '## What it does\nNo eval.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        features = purlin_server._scan_specs(self.project_root)
        assert 'i_security_no_eval' in features
        assert features['i_security_no_eval']['is_global'] is True
        assert features['i_security_no_eval']['is_invariant'] is True

    @pytest.mark.proof("mcp_server", "PROOF-21", "RULE-21")
    def test_global_invariant_auto_applies(self):
        inv_dir = os.path.join(self.project_root, 'specs', '_invariants')
        os.makedirs(inv_dir, exist_ok=True)
        with open(os.path.join(inv_dir, 'i_security_no_eval.md'), 'w') as f:
            f.write(
                '# Invariant: i_security_no_eval\n\n'
                '> Global: true\n\n'
                '## What it does\nNo eval.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        # 1 own + 1 global = 2 total
        assert 'login: 0/2 rules proved' in result
        assert 'i_security_no_eval/RULE-1' in result
        assert '(global)' in result

    @pytest.mark.proof("mcp_server", "PROOF-22", "RULE-22")
    def test_rule_labels(self):
        self._write_spec('api_conv', (
            '# Anchor: api_conv\n\n'
            '## What it does\nAPI rules.\n\n'
            '## Rules\n- RULE-1: JSON envelope\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Check JSON\n'
        ), subdir='schema')
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Requires: api_conv\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'RULE-1: NO PROOF (own)' in result
        assert 'api_conv/RULE-1: NO PROOF (required)' in result

    @pytest.mark.proof("mcp_server", "PROOF-23", "RULE-23")
    def test_scope_overlap_suggestion(self):
        self._write_spec('api_rest_conventions', (
            '# Anchor: api_rest_conventions\n\n'
            '> Scope: src/api/\n\n'
            '## What it does\nREST conventions.\n\n'
            '## Rules\n- RULE-1: JSON envelope\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Check JSON\n'
        ), subdir='schema')
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Scope: src/api/login.js\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert '\u26a0 Anchor api_rest_conventions' in result
        assert '\u2192 Consider: add > Requires: api_rest_conventions' in result

    @pytest.mark.proof("mcp_server", "PROOF-18", "RULE-18")
    def test_structural_only_detection(self):
        self._write_spec('refs', (
            '# Feature: refs\n\n'
            '## What it does\nReference docs.\n\n'
            '## Rules\n- RULE-1: Guide contains X section\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Grep guide.md for X; verify section exists\n'
        ))
        self._write_proofs('refs', [
            {"feature": "refs", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_grep",
             "status": "pass", "tier": "default"},
        ])
        result = purlin_server.sync_status(self.project_root)
        assert 'READY (structural only)' in result
        assert 'E2E' in result or 'behavioral' in result


class TestPurlinConfig:
    """RULE-12: purlin_config read and write."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("mcp_server", "PROOF-12", "RULE-12")
    def test_read_write(self):
        result = purlin_server.handle_purlin_config(
            self.project_root,
            {"action": "write", "key": "test_key", "value": "test_val"}
        )
        assert "test_key" in result

        result = purlin_server.handle_purlin_config(
            self.project_root, {"action": "read", "key": "test_key"}
        )
        assert json.loads(result)["test_key"] == "test_val"

        result = purlin_server.handle_purlin_config(
            self.project_root, {"action": "read"}
        )
        assert json.loads(result)["test_key"] == "test_val"


class TestChangelog:
    """RULE-13 through RULE-15: changelog tool."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        subprocess.run(['git', 'init'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                       cwd=self.project_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                       cwd=self.project_root, capture_output=True, check=True)

        os.makedirs(os.path.join(self.project_root, 'specs', 'auth'))
        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write('# Feature: login\n\n## What it does\nLogin.\n\n'
                    '## Rules\n- RULE-1: Auth\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test\n')
        with open(os.path.join(self.project_root, 'README.md'), 'w') as f:
            f.write('# Test\n')

        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'verify: initial'],
                       cwd=self.project_root, capture_output=True, check=True)

        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write('# Feature: login\n\n## What it does\nLogin.\n\n'
                    '## Rules\n- RULE-1: Auth\n- RULE-2: Lockout\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test\n- PROOF-2 (RULE-2): Test\n')
        os.makedirs(os.path.join(self.project_root, 'tests'))
        with open(os.path.join(self.project_root, 'tests', 'test_login.py'), 'w') as f:
            f.write('def test_login(): pass\n')
        with open(os.path.join(self.project_root, 'README.md'), 'w') as f:
            f.write('# Test v2\n')

        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add lockout'],
                       cwd=self.project_root, capture_output=True, check=True)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("mcp_server", "PROOF-13", "RULE-13")
    def test_since_anchor_resolution(self):
        ref, desc = purlin_server._resolve_since_anchor(self.project_root, since_arg="5")
        assert ref == "HEAD~5"
        assert "5 commits" in desc

        ref, desc = purlin_server._resolve_since_anchor(self.project_root, since_arg=None)
        assert "verification" in desc

    @pytest.mark.proof("mcp_server", "PROOF-14", "RULE-14")
    def test_file_classification(self):
        result_text = purlin_server.changelog(self.project_root)
        data = json.loads(result_text)
        categories = {f['path']: f['category'] for f in data['files']}
        assert categories.get('specs/auth/login.md') == 'CHANGED_SPECS'
        assert categories.get('tests/test_login.py') == 'TESTS_ADDED'
        assert categories.get('README.md') == 'NO_IMPACT'

    @pytest.mark.proof("mcp_server", "PROOF-15", "RULE-15")
    def test_changelog_json_structure(self):
        result_text = purlin_server.changelog(self.project_root)
        data = json.loads(result_text)
        for key in ('since', 'commits', 'files', 'spec_changes', 'proof_status'):
            assert key in data, f"Missing key: {key}"


    @pytest.mark.proof("mcp_server", "PROOF-19", "RULE-19")
    def test_changelog_structural_only_flag(self):
        # Add a structural-only spec with passing proofs
        spec_content = (
            '# Feature: refs\n\n'
            '## What it does\nReference docs.\n\n'
            '## Rules\n- RULE-1: Guide contains X section\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Grep guide.md for X; verify section exists\n'
        )
        refs_dir = os.path.join(self.project_root, 'specs', 'instructions')
        os.makedirs(refs_dir, exist_ok=True)
        with open(os.path.join(refs_dir, 'refs.md'), 'w') as f:
            f.write(spec_content)
        with open(os.path.join(refs_dir, 'refs.proofs-default.json'), 'w') as f:
            json.dump({"tier": "default", "proofs": [
                {"feature": "refs", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test.py", "test_name": "test_grep",
                 "status": "pass", "tier": "default"},
            ]}, f)

        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add refs spec'],
                       cwd=self.project_root, capture_output=True, check=True)

        result_text = purlin_server.changelog(self.project_root)
        data = json.loads(result_text)
        assert 'refs' in data['proof_status']
        assert data['proof_status']['refs']['structural_only'] is True


    @pytest.mark.proof("mcp_server", "PROOF-24", "RULE-24")
    def test_changelog_includes_required_in_total(self):
        # Add an anchor with 2 rules
        anchor_dir = os.path.join(self.project_root, 'specs', 'schema')
        os.makedirs(anchor_dir, exist_ok=True)
        with open(os.path.join(anchor_dir, 'api_conv.md'), 'w') as f:
            f.write(
                '# Anchor: api_conv\n\n'
                '## What it does\nAPI conventions.\n\n'
                '## Rules\n- RULE-1: JSON envelope\n- RULE-2: Error codes\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Check JSON\n- PROOF-2 (RULE-2): Check errors\n'
            )
        # Update the login spec to require the anchor
        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write(
                '# Feature: login\n\n'
                '> Requires: api_conv\n\n'
                '## What it does\nLogin.\n\n'
                '## Rules\n- RULE-1: Auth\n- RULE-2: Lockout\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Test\n- PROOF-2 (RULE-2): Test\n'
            )
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add anchor'],
                       cwd=self.project_root, capture_output=True, check=True)

        result_text = purlin_server.changelog(self.project_root)
        data = json.loads(result_text)
        # login has 2 own rules + 2 required from api_conv = 4 total
        assert 'login' in data['proof_status']
        assert data['proof_status']['login']['total'] == 4


class TestServerOutput:
    """RULE-16 and RULE-17."""

    @pytest.mark.proof("mcp_server", "PROOF-16", "RULE-16")
    def test_startup_logs_to_stderr(self):
        project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(project_root, '.purlin'))
        try:
            stdin_mock = StringIO("")
            stdout_mock = StringIO()
            stderr_mock = StringIO()
            with patch.dict(os.environ, {"PURLIN_PROJECT_ROOT": project_root}):
                with patch('sys.stdin', stdin_mock), \
                     patch('sys.stdout', stdout_mock), \
                     patch('sys.stderr', stderr_mock):
                    purlin_server.main()
            assert "Purlin MCP server" in stderr_mock.getvalue()
            assert stdout_mock.getvalue() == ""
        finally:
            shutil.rmtree(project_root)

    @pytest.mark.proof("mcp_server", "PROOF-17", "RULE-17")
    def test_vhash_with_prefixed_keys(self):
        rules_own = {"RULE-1": "x"}
        proofs = [{"id": "PROOF-1", "status": "pass"}]
        hash_own = purlin_server._compute_vhash(rules_own, proofs)

        rules_with_required = {"RULE-1": "x", "anchor/RULE-1": "y"}
        hash_combined = purlin_server._compute_vhash(rules_with_required, proofs)

        # Hashes must differ when rule set changes
        assert hash_own != hash_combined
        # Verify format: 8 hex chars
        assert len(hash_combined) == 8
        assert all(c in '0123456789abcdef' for c in hash_combined)
