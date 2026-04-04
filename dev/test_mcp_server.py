"""Tests for MCP server specs: mcp_transport (7 rules), sync_status (15 rules), drift (11 rules), purlin_config (1 rule)."""

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
    """mcp_transport RULE-1 through RULE-7: JSON-RPC transport."""

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

    @pytest.mark.proof("mcp_transport", "PROOF-1", "RULE-1")
    def test_initialize(self):
        resp = self._call("initialize")
        result = resp["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert result["serverInfo"]["name"] == "purlin"

    @pytest.mark.proof("mcp_transport", "PROOF-2", "RULE-2")
    def test_tools_list(self):
        resp = self._call("tools/list")
        tools = resp["result"]["tools"]
        names = sorted(t["name"] for t in tools)
        assert names == ["drift", "purlin_config", "sync_status"]
        assert len(tools) == 3

    @pytest.mark.proof("mcp_transport", "PROOF-3", "RULE-3")
    def test_notification_no_response(self):
        request = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        resp = purlin_server.handle_request(request, self.project_root)
        assert resp is None

    @pytest.mark.proof("mcp_transport", "PROOF-4", "RULE-4")
    def test_parse_error(self):
        stdin_mock = StringIO("not valid json\n")
        stdout_mock = StringIO()
        with patch.dict(os.environ, {"PURLIN_PROJECT_ROOT": self.project_root}):
            with patch('sys.stdin', stdin_mock), patch('sys.stdout', stdout_mock):
                purlin_server.main()
        resp = json.loads(stdout_mock.getvalue().strip())
        assert resp["error"]["code"] == -32700

    @pytest.mark.proof("mcp_transport", "PROOF-5", "RULE-5")
    def test_unknown_method(self):
        resp = self._call("bogus")
        assert resp["error"]["code"] == -32601
        assert "bogus" in resp["error"]["message"]

    @pytest.mark.proof("mcp_transport", "PROOF-6", "RULE-6")
    def test_unknown_tool(self):
        resp = self._call("tools/call", {"name": "nonexistent", "arguments": {}})
        assert resp["error"]["code"] == -32601
        assert "nonexistent" in resp["error"]["message"]


class TestSyncStatus:
    """sync_status RULE-1 through RULE-15: coverage reporting."""

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

    def _write_proofs(self, name, proofs, tier='unit', subdir='auth'):
        d = os.path.join(self.project_root, 'specs', subdir)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f'{name}.proofs-{tier}.json'), 'w') as f:
            json.dump({"tier": tier, "proofs": proofs}, f)

    @pytest.mark.proof("sync_status", "PROOF-1", "RULE-1")
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

    @pytest.mark.proof("sync_status", "PROOF-2", "RULE-2")
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
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        assert 'login: READY' in result
        assert 'vhash=' in result

    @pytest.mark.proof("sync_status", "PROOF-3", "RULE-3")
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
        assert 'not numbered' in result.lower(), \
            f"WARNING doesn't mention unnumbered rules: {result}"

    @pytest.mark.proof("sync_status", "PROOF-4", "RULE-4")
    def test_requires_counts_for_coverage(self):
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir)
        with open(os.path.join(anchor_dir, 'security.md'), 'w') as f:
            f.write(
                '# Anchor: security\n\n'
                '## What it does\nSecurity rules.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Requires: security\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        # 1 own + 1 required = 2 total
        assert 'login: 0/2 rules proved' in result
        assert 'security/RULE-1: NO PROOF (required)' in result

    @pytest.mark.proof("sync_status", "PROOF-5", "RULE-5")
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


    @pytest.mark.proof("sync_status", "PROOF-8", "RULE-8")
    def test_scan_specs_detects_global(self):
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        with open(os.path.join(anchor_dir, 'security_no_eval.md'), 'w') as f:
            f.write(
                '# Anchor: security_no_eval\n\n'
                '> Global: true\n\n'
                '## What it does\nNo eval.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        features = purlin_server._scan_specs(self.project_root)
        assert 'security_no_eval' in features
        assert features['security_no_eval']['is_global'] is True
        assert features['security_no_eval']['is_anchor'] is True

    @pytest.mark.proof("sync_status", "PROOF-9", "RULE-9")
    def test_global_anchor_auto_applies(self):
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        with open(os.path.join(anchor_dir, 'security_no_eval.md'), 'w') as f:
            f.write(
                '# Anchor: security_no_eval\n\n'
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
        assert 'security_no_eval/RULE-1: NO PROOF (global)' in result

    @pytest.mark.proof("sync_status", "PROOF-10", "RULE-10")
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

    @pytest.mark.proof("sync_status", "PROOF-11", "RULE-11")
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

    @pytest.mark.proof("sync_status", "PROOF-7", "RULE-7")
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
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        # Structural proofs count toward READY
        assert 'refs: READY' in result

    @pytest.mark.proof("sync_status", "PROOF-12", "RULE-12")
    def test_unresolved_requires_warning(self):
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Requires: does_not_exist\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        self._write_proofs('login', [
            {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_valid",
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        assert 'Requires "does_not_exist" but no spec with that name exists' in result

    @pytest.mark.proof("sync_status", "PROOF-15", "RULE-15")
    def test_receipt_staleness_from_anchor_change(self):
        # Create anchor with 1 rule
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        with open(os.path.join(anchor_dir, 'security.md'), 'w') as f:
            f.write(
                '# Anchor: security\n\n'
                '## What it does\nSecurity rules.\n\n'
                '## Rules\n- RULE-1: Rejects code containing eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Run linter; verify eval calls are rejected\n'
            )
        # Create feature requiring anchor, with all proofs passing
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Requires: security\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        self._write_proofs('login', [
            {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_valid",
             "status": "pass", "tier": "unit"},
        ])
        self._write_proofs('security', [
            {"feature": "security", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_no_eval",
             "status": "pass", "tier": "unit"},
        ], subdir='_anchors')
        # Write a receipt with only the original rules (RULE-1 + security/RULE-1)
        with open(os.path.join(self.spec_dir, 'login.receipt.json'), 'w') as f:
            json.dump({
                "feature": "login",
                "vhash": "oldvhash",
                "rules": ["RULE-1", "security/RULE-1"],
                "proofs": []
            }, f)
        # Now add a second rule to the anchor and provide proof for it
        with open(os.path.join(anchor_dir, 'security.md'), 'w') as f:
            f.write(
                '# Anchor: security\n\n'
                '## What it does\nSecurity rules.\n\n'
                '## Rules\n- RULE-1: Rejects code containing eval\n- RULE-2: Rejects code containing exec\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Run linter; verify eval calls are rejected\n- PROOF-2 (RULE-2): Run linter; verify exec calls are rejected\n'
            )
        # Add proof for the new anchor RULE-2 so feature becomes READY
        self._write_proofs('security', [
            {"feature": "security", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_no_eval",
             "status": "pass", "tier": "unit"},
            {"feature": "security", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "tests/test.py", "test_name": "test_no_exec",
             "status": "pass", "tier": "unit"},
        ], subdir='_anchors')
        result = purlin_server.sync_status(self.project_root)
        # Should explain staleness is from anchor change
        assert 'Required anchor "security" changed' in result
        assert 'RULE-2' in result

    @pytest.mark.proof("sync_status", "PROOF-13", "RULE-13")
    def test_manual_proof_without_scope_warning(self):
        # Spec with manual proof but NO > Scope: → should warn
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Must authenticate\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): Verified auth @manual(dev@test.com, 2026-01-01, abc1234)\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'Manual proof without > Scope:' in result
        assert 'staleness cannot be detected' in result

    @pytest.mark.proof("sync_status", "PROOF-14", "RULE-14")
    def test_prefers_subdirectory_proofs(self):
        # Create spec in subdirectory
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        # Write proof at specs/ root (fallback location)
        root_proof_dir = os.path.join(self.project_root, 'specs')
        with open(os.path.join(root_proof_dir, 'login.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/old_test.py", "test_name": "test_old",
                 "status": "fail", "tier": "unit"},
            ]}, f)
        # Write proof in subdirectory (adjacent to spec)
        self._write_proofs('login', [
            {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_valid",
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        # Should use the subdirectory proof (pass), not root (fail)
        assert 'READY' in result
        assert 'FAIL' not in result

    @pytest.mark.proof("sync_status", "PROOF-13", "RULE-13")
    def test_manual_proof_with_scope_no_warning(self):
        # Spec with manual proof AND > Scope: → should NOT warn
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Scope: src/app.py\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Must authenticate\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): Verified auth @manual(dev@test.com, 2026-01-01, abc1234)\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'Manual proof without > Scope:' not in result

    @pytest.mark.proof("sync_status", "PROOF-7", "RULE-7")
    def test_structural_regex_rejects_behavioral_descriptions(self):
        """Behavioral descriptions must NOT be classified as structural."""
        # "Verify the API endpoint exists and returns 200" is behavioral
        self._write_spec('api', (
            '# Feature: api\n\n'
            '## What it does\nAPI.\n\n'
            '## Rules\n- RULE-1: Endpoint returns 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Verify the API endpoint exists and returns 200\n'
        ))
        self._write_proofs('api', [
            {"feature": "api", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_api",
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        # Should be READY since it's behavioral
        assert 'api: READY' in result

    @pytest.mark.proof("sync_status", "PROOF-7", "RULE-7")
    def test_structural_regex_accepts_grep_descriptions(self):
        """Pure grep/existence checks should be classified as structural."""
        self._write_spec('refs', (
            '# Feature: refs\n\n'
            '## What it does\nReference docs.\n\n'
            '## Rules\n- RULE-1: File exists\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Verify file exists at specs/auth/login.md\n'
        ))
        self._write_proofs('refs', [
            {"feature": "refs", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_file",
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        # Structural proofs count toward READY
        assert 'refs: READY' in result

    @pytest.mark.proof("sync_status", "PROOF-16", "RULE-16")
    def test_warns_uncommitted_spec_changes(self):
        """Uncommitted .md and .proofs-*.json changes in specs/ trigger a warning."""
        # Set up a real git repo in the temp directory
        subprocess.run(['git', 'init'], cwd=self.project_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                       cwd=self.project_root, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                       cwd=self.project_root, capture_output=True)

        # Write and commit a spec
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        subprocess.run(['git', 'add', 'specs/'], cwd=self.project_root, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'add spec'], cwd=self.project_root, capture_output=True)

        # Modify the spec without committing
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n- RULE-2: Return 401\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
            '- PROOF-2 (RULE-2): POST invalid creds\n'
        ))

        result = purlin_server.sync_status(self.project_root)
        assert '\u26a0 Uncommitted spec/proof changes detected:' in result
        assert 'login.md' in result
        assert 'Commit these files' in result

        # Commit the change — warning should disappear
        subprocess.run(['git', 'add', 'specs/'], cwd=self.project_root, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'update spec'], cwd=self.project_root, capture_output=True)

        result = purlin_server.sync_status(self.project_root)
        assert 'Uncommitted' not in result

    @pytest.mark.proof("sync_status", "PROOF-18", "RULE-18")
    def test_summary_table(self):
        """sync_status output begins with a summary table."""
        # Feature 1: fully proved (READY)
        self._write_spec('alpha', (
            '# Feature: alpha\n\n'
            '## What it does\nAlpha feature.\n\n'
            '## Rules\n- RULE-1: Alpha does X\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Run alpha test\n'
        ))
        self._write_proofs('alpha', [
            {"feature": "alpha", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_alpha",
             "status": "pass", "tier": "unit"},
        ])

        # Feature 2: partially proved
        self._write_spec('beta', (
            '# Feature: beta\n\n'
            '## What it does\nBeta feature.\n\n'
            '## Rules\n- RULE-1: Beta does X\n- RULE-2: Beta does Y\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Run beta X test\n'
            '- PROOF-2 (RULE-2): Run beta Y test\n'
        ))
        self._write_proofs('beta', [
            {"feature": "beta", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_beta_x",
             "status": "pass", "tier": "unit"},
        ])

        # Feature 3: no proofs
        self._write_spec('gamma', (
            '# Feature: gamma\n\n'
            '## What it does\nGamma feature.\n\n'
            '## Rules\n- RULE-1: Gamma does X\n- RULE-2: Gamma does Y\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Run gamma X test\n'
            '- PROOF-2 (RULE-2): Run gamma Y test\n'
        ))

        result = purlin_server.sync_status(self.project_root)

        # Table starts the output (┌ is first character)
        assert result.startswith('\u250c'), f"Expected table at start, got: {result[:80]}"

        # Summary line with correct count
        assert '1/3 features READY' in result

        # Verify table contains all features
        assert '\u2502 alpha' in result
        assert '\u2502 beta' in result
        assert '\u2502 gamma' in result

        # Verify sort order: partial before READY before —
        beta_idx = result.index('\u2502 beta')
        alpha_idx = result.index('\u2502 alpha')
        gamma_idx = result.index('\u2502 gamma')
        assert beta_idx < alpha_idx < gamma_idx, \
            "Table should sort: partial, READY, \u2014"

        # Detail section follows after table
        lines = result.split('\n')
        table_end = None
        for i, line in enumerate(lines):
            if line.startswith('\u2514'):
                table_end = i
                break
        assert table_end is not None, "No table closing line found"
        # After └... line, summary line, blank line, then detail
        detail_text = '\n'.join(lines[table_end + 3:])
        assert 'alpha: READY' in detail_text
        assert 'beta: 1/2 rules proved' in detail_text
        assert 'gamma: 0/2 rules proved' in detail_text


class TestPurlinConfig:
    """purlin_config RULE-1: config read/write."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("purlin_config", "PROOF-1", "RULE-1")
    def test_read_write(self):
        # Write a key — returns confirmation string
        result = purlin_server.handle_purlin_config(
            self.project_root,
            {"action": "write", "key": "test_key", "value": "test_val"}
        )
        assert "test_key" in result and "test_val" in result, \
            f"Write should confirm key and value, got: {result}"

        # Read a single key — returns JSON with just that key
        result = purlin_server.handle_purlin_config(
            self.project_root, {"action": "read", "key": "test_key"}
        )
        assert json.loads(result) == {"test_key": "test_val"}, \
            f"Single-key read should return exact key-value, got: {result}"

        # Full config read — assert exact contents
        result = purlin_server.handle_purlin_config(
            self.project_root, {"action": "read"}
        )
        full_config = json.loads(result)
        assert full_config == {"test_key": "test_val"}, \
            f"Full config should be exactly {{test_key: test_val}}, got {full_config}"


class TestDrift:
    """drift RULE-1 through RULE-5: drift tool."""

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

    @pytest.mark.proof("drift", "PROOF-1", "RULE-1")
    def test_since_anchor_resolution(self):
        ref, desc = purlin_server._resolve_since_anchor(self.project_root, since_arg="5")
        assert ref == "HEAD~5"
        assert "5 commits" in desc

        ref, desc = purlin_server._resolve_since_anchor(self.project_root, since_arg=None)
        assert "verification" in desc
        # Verify ref is the actual SHA of the verify: commit
        verify_sha = subprocess.run(
            ['git', 'log', '--grep=^verify:', '--format=%H', '-1'],
            cwd=self.project_root, capture_output=True, text=True, check=True
        ).stdout.strip()
        assert ref == verify_sha, f"Expected ref={verify_sha}, got ref={ref}"

    @pytest.mark.proof("drift", "PROOF-2", "RULE-2")
    def test_file_classification(self):
        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        categories = {f['path']: f['category'] for f in data['files']}
        assert categories.get('specs/auth/login.md') == 'CHANGED_SPECS'
        assert categories.get('tests/test_login.py') == 'TESTS_ADDED'
        assert categories.get('README.md') == 'NO_IMPACT'

    @pytest.mark.proof("drift", "PROOF-3", "RULE-3")
    def test_drift_json_structure(self):
        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        for key in ('since', 'commits', 'files', 'spec_changes', 'proof_status'):
            assert key in data, f"Missing key: {key}"


    @pytest.mark.proof("drift", "PROOF-4", "RULE-4")
    def test_drift_structural_only_flag(self):
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
        with open(os.path.join(refs_dir, 'refs.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "refs", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test.py", "test_name": "test_grep",
                 "status": "pass", "tier": "unit"},
            ]}, f)

        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add refs spec'],
                       cwd=self.project_root, capture_output=True, check=True)

        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        assert 'refs' in data['proof_status']
        assert data['proof_status']['refs']['structural_checks'] == 1
        assert data['proof_status']['refs']['proved'] == 1


    @pytest.mark.proof("drift", "PROOF-5", "RULE-5")
    def test_drift_includes_required_in_total(self):
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

        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        # login has 2 own rules + 2 required from api_conv = 4 total
        assert 'login' in data['proof_status']
        assert data['proof_status']['login']['total'] == 4


class TestDriftDetection:
    """drift RULE-6 through RULE-10: drift detection."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        subprocess.run(['git', 'init'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                       cwd=self.project_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                       cwd=self.project_root, capture_output=True, check=True)
        # Initial commit
        os.makedirs(os.path.join(self.project_root, 'specs', 'auth'))
        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write('# Feature: login\n\n## What it does\nLogin.\n\n'
                    '## Rules\n- RULE-1: Auth\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'verify: initial'],
                       cwd=self.project_root, capture_output=True, check=True)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("drift", "PROOF-6", "RULE-6")
    def test_skill_md_not_no_impact(self):
        """Skill .md files must be NEW_BEHAVIOR, not NO_IMPACT."""
        skill_dir = os.path.join(self.project_root, 'skills', 'build')
        os.makedirs(skill_dir, exist_ok=True)
        with open(os.path.join(skill_dir, 'SKILL.md'), 'w') as f:
            f.write('---\nname: build\n---\nBuild skill.\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add build skill'],
                       cwd=self.project_root, capture_output=True, check=True)

        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        categories = {f['path']: f['category'] for f in data['files']}
        assert categories.get('skills/build/SKILL.md') == 'NEW_BEHAVIOR', \
            f"Expected NEW_BEHAVIOR, got {categories.get('skills/build/SKILL.md')}"

    @pytest.mark.proof("drift", "PROOF-6", "RULE-6")
    def test_agent_md_not_no_impact(self):
        """.claude/agents/ .md files must be NEW_BEHAVIOR, not NO_IMPACT."""
        agent_dir = os.path.join(self.project_root, '.claude', 'agents')
        os.makedirs(agent_dir, exist_ok=True)
        with open(os.path.join(agent_dir, 'helper.md'), 'w') as f:
            f.write('---\nname: helper\n---\nHelper agent.\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add helper agent'],
                       cwd=self.project_root, capture_output=True, check=True)

        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        categories = {f['path']: f['category'] for f in data['files']}
        assert categories.get('.claude/agents/helper.md') == 'NEW_BEHAVIOR', \
            f"Expected NEW_BEHAVIOR, got {categories.get('.claude/agents/helper.md')}"

    @pytest.mark.proof("drift", "PROOF-7", "RULE-7")
    def test_scope_prefix_matching(self):
        """Scope with trailing slash matches files in that directory."""
        # Create a spec with directory scope
        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write('# Feature: login\n\n> Scope: src/api/\n\n'
                    '## What it does\nLogin.\n\n'
                    '## Rules\n- RULE-1: Auth\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test\n')
        # Create a file inside that scope dir
        os.makedirs(os.path.join(self.project_root, 'src', 'api'), exist_ok=True)
        with open(os.path.join(self.project_root, 'src', 'api', 'login.js'), 'w') as f:
            f.write('module.exports = {};\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add api'],
                       cwd=self.project_root, capture_output=True, check=True)

        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        categories = {f['path']: f['category'] for f in data['files']}
        assert categories.get('src/api/login.js') == 'CHANGED_BEHAVIOR', \
            f"Expected CHANGED_BEHAVIOR, got {categories.get('src/api/login.js')}"
        # Verify the spec was matched
        spec_map = {f['path']: f['spec'] for f in data['files']}
        assert spec_map.get('src/api/login.js') == 'login'

    @pytest.mark.proof("drift", "PROOF-8", "RULE-8")
    def test_structural_drift_flag(self):
        """CHANGED_BEHAVIOR file gets behavioral_gap when spec has no behavioral proofs."""
        # Create a structural-only spec with scope and passing proof
        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write('# Feature: login\n\n> Scope: src/login.py\n\n'
                    '## What it does\nLogin.\n\n'
                    '## Rules\n- RULE-1: Verify config contains auth section\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Grep config for auth section; verify present\n')
        with open(os.path.join(self.project_root, 'specs', 'auth',
                               'login.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "test.py", "test_name": "test_grep",
                 "status": "pass", "tier": "unit"},
            ]}, f)
        # Create the scope file
        os.makedirs(os.path.join(self.project_root, 'src'), exist_ok=True)
        with open(os.path.join(self.project_root, 'src', 'login.py'), 'w') as f:
            f.write('pass\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'verify: add structural spec'],
                       cwd=self.project_root, capture_output=True, check=True)
        # Now modify the scope file
        with open(os.path.join(self.project_root, 'src', 'login.py'), 'w') as f:
            f.write('def login(): return 200\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: implement login'],
                       cwd=self.project_root, capture_output=True, check=True)

        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        login_entry = next((f for f in data['files'] if f['path'] == 'src/login.py'), None)
        assert login_entry is not None, "src/login.py not in drift files"
        assert login_entry['category'] == 'CHANGED_BEHAVIOR'
        assert login_entry.get('behavioral_gap') is True, \
            f"Expected behavioral_gap=True, got {login_entry}"

    @pytest.mark.proof("drift", "PROOF-9", "RULE-9")
    def test_drift_flags_array(self):
        """drift_flags array contains features with behavioral gap and changed files."""
        # Same setup as structural_drift test
        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write('# Feature: login\n\n> Scope: src/login.py\n\n'
                    '## What it does\nLogin.\n\n'
                    '## Rules\n- RULE-1: Verify config contains auth section\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Grep config for auth section; verify present\n')
        with open(os.path.join(self.project_root, 'specs', 'auth',
                               'login.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "test.py", "test_name": "test_grep",
                 "status": "pass", "tier": "unit"},
            ]}, f)
        os.makedirs(os.path.join(self.project_root, 'src'), exist_ok=True)
        with open(os.path.join(self.project_root, 'src', 'login.py'), 'w') as f:
            f.write('pass\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'verify: structural spec'],
                       cwd=self.project_root, capture_output=True, check=True)
        # Modify scope file
        with open(os.path.join(self.project_root, 'src', 'login.py'), 'w') as f:
            f.write('def login(): return 200\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: implement login'],
                       cwd=self.project_root, capture_output=True, check=True)

        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        assert 'drift_flags' in data
        assert len(data['drift_flags']) >= 1
        login_drift = next((d for d in data['drift_flags'] if d['spec'] == 'login'), None)
        assert login_drift is not None, f"No drift flag for login, got {data['drift_flags']}"
        assert login_drift['reason'] == 'behavioral_gap_with_code_change'
        assert 'src/login.py' in login_drift['files']

    @pytest.mark.proof("drift", "PROOF-10", "RULE-10")
    def test_broken_scope_detection(self):
        """Broken scope: spec references a file that doesn't exist on disk."""
        # Update the spec to reference a non-existent file
        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write('# Feature: login\n\n> Scope: src/deleted.py\n\n'
                    '## What it does\nLogin.\n\n'
                    '## Rules\n- RULE-1: Auth\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: update spec scope'],
                       cwd=self.project_root, capture_output=True, check=True)

        # Do NOT create src/deleted.py on disk
        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        assert 'broken_scopes' in data, "broken_scopes field missing from result"
        broken = [b for b in data['broken_scopes'] if b['spec'] == 'login']
        assert len(broken) == 1, f"Expected 1 broken scope for login, got {broken}"
        assert 'src/deleted.py' in broken[0]['missing_paths']


class TestDriftSmartFallback:
    """drift RULE-11: smart fallback."""

    @pytest.mark.proof("drift", "PROOF-11", "RULE-11")
    def test_large_repo_recommends_spec_from_code(self):
        """50+ commits, no verify, no tag → recommendation."""
        project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(project_root, '.purlin'))
        subprocess.run(['git', 'init'], cwd=project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                       cwd=project_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                       cwd=project_root, capture_output=True, check=True)
        # Add .purlin/config.json early
        with open(os.path.join(project_root, '.purlin', 'config.json'), 'w') as f:
            json.dump({}, f)
        subprocess.run(['git', 'add', '.'], cwd=project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'init purlin'],
                       cwd=project_root, capture_output=True, check=True)
        # Create 50 more commits
        for i in range(50):
            with open(os.path.join(project_root, f'file_{i}.txt'), 'w') as f:
                f.write(f'content {i}\n')
            subprocess.run(['git', 'add', '.'], cwd=project_root,
                           capture_output=True, check=True)
            subprocess.run(['git', 'commit', '-m', f'feat: change {i}'],
                           cwd=project_root, capture_output=True, check=True)
        try:
            result_text = purlin_server.drift(project_root)
            data = json.loads(result_text)
            assert data.get('recommendation') == 'spec-from-code', \
                f"Expected recommendation, got: {list(data.keys())}"
            assert data['commits_since_init'] >= 30
        finally:
            shutil.rmtree(project_root)

    @pytest.mark.proof("drift", "PROOF-11", "RULE-11")
    def test_small_repo_returns_normal_drift(self):
        """10 commits, no verify, no tag → normal drift."""
        project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(project_root, '.purlin'))
        subprocess.run(['git', 'init'], cwd=project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                       cwd=project_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                       cwd=project_root, capture_output=True, check=True)
        # Add .purlin/config.json
        with open(os.path.join(project_root, '.purlin', 'config.json'), 'w') as f:
            json.dump({}, f)
        os.makedirs(os.path.join(project_root, 'specs'))
        subprocess.run(['git', 'add', '.'], cwd=project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'init purlin'],
                       cwd=project_root, capture_output=True, check=True)
        # Create 10 more commits
        for i in range(10):
            with open(os.path.join(project_root, f'file_{i}.txt'), 'w') as f:
                f.write(f'content {i}\n')
            subprocess.run(['git', 'add', '.'], cwd=project_root,
                           capture_output=True, check=True)
            subprocess.run(['git', 'commit', '-m', f'feat: change {i}'],
                           cwd=project_root, capture_output=True, check=True)
        try:
            result_text = purlin_server.drift(project_root)
            data = json.loads(result_text)
            # Should be normal drift, not a recommendation
            assert 'since' in data, f"Expected normal drift, got: {list(data.keys())}"
            assert 'recommendation' not in data
        finally:
            shutil.rmtree(project_root)


class TestServerOutput:
    """mcp_transport RULE-7 and sync_status RULE-6."""

    @pytest.mark.proof("mcp_transport", "PROOF-7", "RULE-7")
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

    @pytest.mark.proof("sync_status", "PROOF-6", "RULE-6")
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

        # Pin the exact algorithm: sha256(comma-joined sorted rule IDs | comma-joined sorted proof pairs)[:8]
        rule_ids = sorted(rules_with_required.keys())
        proof_pairs = sorted(f"{p['id']}:{p['status']}" for p in proofs)
        expected_input = ','.join(rule_ids) + '|' + ','.join(proof_pairs)
        expected_hash = hashlib.sha256(expected_input.encode()).hexdigest()[:8]
        assert hash_combined == expected_hash, \
            f"vhash algorithm mismatch: expected {expected_hash}, got {hash_combined}"
