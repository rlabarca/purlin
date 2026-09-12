"""Tests for MCP server specs: mcp_transport (7 rules), sync_status (15 rules), drift (11 rules), purlin_config (1 rule)."""

import hashlib
import json
import os
import re
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
        assert 'login: PASSING' in result
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
        # Structural proofs count toward VERIFIED
        assert 'refs: PASSING' in result

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
                # Version 2: a version 1 receipt is stale because the formula
                # changed, and sync_status says so instead of explaining an
                # anchor change that is not why (RULE-55).
                "vhash_version": 2,
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
        # Add proof for the new anchor RULE-2 so feature passes all rules
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
        assert 'PASSING' in result
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
    def test_all_proof_types_count_equally(self):
        """RULE-7: Grep-based and behavioral proofs both earn PASSING equally."""
        # Grep-based proof description
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
        # All proofs count equally — grep-based proofs earn PASSING
        assert 'refs: PASSING' in result

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
        # Feature 1: fully proved (PASSING — no receipt, so not VERIFIED)
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

        # Summary line — no receipts exist so 0 features VERIFIED
        assert '0/3 features VERIFIED' in result

        # Verify table contains all features
        assert '\u2502 alpha' in result
        assert '\u2502 beta' in result
        assert '\u2502 gamma' in result

        # Verify sort order: PARTIAL before PASSING before —
        beta_idx = result.index('\u2502 beta')
        alpha_idx = result.index('\u2502 alpha')
        gamma_idx = result.index('\u2502 gamma')
        assert beta_idx < alpha_idx < gamma_idx, \
            "Table should sort: PARTIAL, PASSING, \u2014"

        # Detail section follows after table
        lines = result.split('\n')
        table_end = None
        for i, line in enumerate(lines):
            if line.startswith('\u2514'):
                table_end = i
                break
        # After └... line, summary line, blank line, then detail
        # (table_end must be set — if not, lines[table_end + 3:] will TypeError immediately)
        detail_text = '\n'.join(lines[table_end + 3:])
        assert 'alpha: PASSING' in detail_text
        assert 'beta: 1/2 rules proved' in detail_text
        assert 'gamma: 0/2 rules proved' in detail_text

    @pytest.mark.proof("sync_status", "PROOF-20", "RULE-20")
    def test_untested_status_for_zero_proofs(self):
        """RULE-20: Features with zero behavioral proofs show UNTESTED."""
        self._write_spec('empty', (
            '# Feature: empty\n\n'
            '## What it does\nEmpty feature.\n\n'
            '## Rules\n- RULE-1: Does X\n- RULE-2: Does Y\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test X\n'
            '- PROOF-2 (RULE-2): Test Y\n'
        ))
        # No proof file — zero proofs
        result = purlin_server.sync_status(self.project_root)
        # Summary table should show UNTESTED status
        assert 'UNTESTED' in result, (
            f"Expected UNTESTED in summary table for zero-proof feature, got:\n{result}"
        )

    @pytest.mark.proof("sync_status", "PROOF-21", "RULE-21")
    def test_partial_status_when_not_all_rules_proved(self):
        """RULE-21: Partial coverage = PARTIAL, not PASSING, even when all existing proofs pass."""
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Validate creds\n- RULE-2: Return token\n'
            '- RULE-3: Log attempt\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
            '- PROOF-2 (RULE-2): Check token\n'
            '- PROOF-3 (RULE-3): Check logs\n'
        ))
        # Only 2 of 3 rules have proofs — both passing
        self._write_proofs('login', [
            {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_creds",
             "status": "pass", "tier": "unit"},
            {"feature": "login", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "tests/test.py", "test_name": "test_token",
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        # Feature should be PARTIAL, NOT PASSING — incomplete coverage
        assert 'PASSING' not in result, (
            f"Feature with 2/3 rules proved should NOT be PASSING:\n{result}"
        )
        assert 'login' in result
        # Detail should show partial coverage
        assert '2/3 rules proved' in result, (
            f"Expected '2/3 rules proved' in output:\n{result}"
        )


    @pytest.mark.proof("sync_status", "PROOF-62", "RULE-36")
    def test_scan_specs_parses_stack(self):
        """RULE-36: _scan_specs parses > Stack: metadata."""
        self._write_spec('login', (
            '# Feature: login\n\n'
            '> Stack: python/stdlib, json, hashlib\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        features = purlin_server._scan_specs(self.project_root)
        assert features['login']['stack'] == 'python/stdlib, json, hashlib'

    @pytest.mark.proof("sync_status", "PROOF-62", "RULE-36")
    def test_scan_specs_stack_absent(self):
        """RULE-36: stack is None when not present."""
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        features = purlin_server._scan_specs(self.project_root)
        assert features['login']['stack'] is None

    @pytest.mark.proof("sync_status", "PROOF-63", "RULE-37")
    def test_no_rule_count_warning_for_few_rules(self):
        """RULE-37: No rule-count warning for features with few rules."""
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n'
            '- RULE-1: Return 200\n'
            '- RULE-2: Return 401\n'
            '- RULE-3: Log errors\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): POST valid creds\n'
            '- PROOF-2 (RULE-2): POST invalid creds\n'
            '- PROOF-3 (RULE-3): Check logs\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'aim for' not in result.lower()
        assert '5–10' not in result

    @pytest.mark.proof("sync_status", "PROOF-63", "RULE-37")
    def test_no_rule_count_warning_for_many_rules(self):
        """RULE-37: No rule-count warning for features with many rules."""
        rules = '\n'.join(f'- RULE-{i}: Constraint {i}' for i in range(1, 13))
        proofs = '\n'.join(f'- PROOF-{i} (RULE-{i}): Test {i}' for i in range(1, 13))
        self._write_spec('login', (
            f'# Feature: login\n\n'
            f'## What it does\nHandles login.\n\n'
            f'## Rules\n{rules}\n\n'
            f'## Proof\n{proofs}\n'
        ))
        result = purlin_server.sync_status(self.project_root)
        assert 'aim for' not in result.lower()
        assert '5–10' not in result

    @pytest.mark.proof("sync_status", "PROOF-63", "RULE-37")
    def test_no_rule_count_warning_for_anchors(self):
        """RULE-37: No rule-count warning for anchors."""
        self._write_spec('security', (
            '# Anchor: security\n\n'
            '## What it does\nSecurity.\n\n'
            '## Rules\n- RULE-1: No eval\n- RULE-2: No exec\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Grep eval\n- PROOF-2 (RULE-2): Grep exec\n'
        ), subdir='_anchors')
        result = purlin_server.sync_status(self.project_root)
        assert 'aim for' not in result.lower()

    @pytest.mark.proof("sync_status", "PROOF-63", "RULE-37")
    def test_no_rule_count_warning_for_instructions(self):
        """RULE-37: No rule-count warning for instruction specs."""
        self._write_spec('agent_spec', (
            '# Feature: agent_spec\n\n'
            '## What it does\nAgent instructions.\n\n'
            '## Rules\n- RULE-1: Has frontmatter\n- RULE-2: Has usage\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Grep for ---\n- PROOF-2 (RULE-2): Grep for Usage\n'
        ), subdir='instructions')
        result = purlin_server.sync_status(self.project_root)
        assert 'aim for' not in result.lower()

    @pytest.mark.proof("sync_status", "PROOF-64", "RULE-17")
    def test_proof_types_display_uniformly(self):
        """RULE-17: Grep-based and behavioral proofs both show PASS/FAIL with no visual distinction."""
        # One spec covered by a "grep-based" proof description, one by a behavioral proof description
        self._write_spec('grep_feature', (
            '# Feature: grep_feature\n\n'
            '## What it does\nGrep feature.\n\n'
            '## Rules\n- RULE-1: File contains header\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Grep README.md for # header; verify section exists\n'
        ))
        self._write_proofs('grep_feature', [
            {"feature": "grep_feature", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test_grep.py", "test_name": "test_header_exists",
             "status": "pass", "tier": "unit"},
        ])
        self._write_spec('behavior_feature', (
            '# Feature: behavior_feature\n\n'
            '## What it does\nBehavioral feature.\n\n'
            '## Rules\n- RULE-1: Returns 200 on valid input\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid request; assert status 200\n'
        ))
        self._write_proofs('behavior_feature', [
            {"feature": "behavior_feature", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test_behavior.py", "test_name": "test_valid_input",
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        # Both features should show PASSING — no special label distinguishing proof type
        assert 'grep_feature: PASSING' in result
        assert 'behavior_feature: PASSING' in result
        # Neither feature should show any "(grep)" or "(structural)" type distinctions in the
        # per-feature coverage line (both just show PASSING, same as any other proof)
        grep_idx = result.index('grep_feature: PASSING')
        behavior_idx = result.index('behavior_feature: PASSING')
        # Both statuses appear identically formatted — the substring "PASSING" appears for both
        assert 'PASSING' in result[grep_idx:grep_idx + 30]
        assert 'PASSING' in result[behavior_idx:behavior_idx + 30]

    @pytest.mark.proof("sync_status", "PROOF-65", "RULE-22")
    def test_anchor_detail_shows_source_path_and_pinned(self):
        """RULE-22: Anchor detail shows Source URL, Path (if present), and Pinned value truncated to 7 chars."""
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        full_sha = 'abcdef1234567890abcdef1234567890abcdef12'
        with open(os.path.join(anchor_dir, 'ext_security.md'), 'w') as f:
            f.write(
                '# Anchor: ext_security\n\n'
                '> Source: https://github.com/example/repo\n'
                '> Path: specs/security/no_eval.md\n'
                f'> Pinned: {full_sha}\n\n'
                '## What it does\nExternal security rules.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        result = purlin_server.sync_status(self.project_root)
        assert 'Source: https://github.com/example/repo' in result
        assert 'Path: specs/security/no_eval.md' in result
        # Pinned value truncated to 7 chars
        assert 'Pinned: abcdef1' in result

    @pytest.mark.proof("sync_status", "PROOF-66", "RULE-23")
    def test_anchor_unpinned_warning(self):
        """RULE-23: Shows unpinned warning for anchors with Source but no Pinned."""
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        with open(os.path.join(anchor_dir, 'ext_security.md'), 'w') as f:
            f.write(
                '# Anchor: ext_security\n\n'
                '> Source: https://github.com/example/repo\n\n'
                '## What it does\nExternal security rules.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        result = purlin_server.sync_status(self.project_root)
        assert 'Unpinned' in result
        assert 'purlin:anchor sync ext_security' in result

    @pytest.mark.proof("sync_status", "PROOF-67", "RULE-24")
    def test_report_data_includes_pinned_and_source_path(self):
        """RULE-24: report-data.js feature entries include pinned and source_path for anchors with those fields."""
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        full_sha = 'deadbeef1234567890abcdef1234567890abcdef'
        with open(os.path.join(anchor_dir, 'ext_security.md'), 'w') as f:
            f.write(
                '# Anchor: ext_security\n\n'
                '> Source: https://github.com/example/repo\n'
                '> Path: specs/security/constraints.md\n'
                f'> Pinned: {full_sha}\n\n'
                '## What it does\nExternal security rules.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        # Write config with report=True so _build_report_data is invoked
        config_path = os.path.join(self.project_root, '.purlin', 'config.json')
        with open(config_path, 'w') as f:
            json.dump({'version': '0.9.0', 'test_framework': 'auto',
                       'spec_dir': 'specs', 'report': True}, f)

        features = purlin_server._scan_specs(self.project_root)
        all_proofs = purlin_server._read_proofs(self.project_root)
        config = purlin_server.resolve_config(self.project_root)
        global_anchors = {k: v for k, v in features.items() if v.get('is_global')}

        data = purlin_server._build_report_data(
            self.project_root, features, all_proofs, config, global_anchors, None
        )

        anchor_entry = next(
            (f for f in data['features'] if f['name'] == 'ext_security'), None
        )
        assert anchor_entry is not None, "ext_security should appear in report data features"
        assert anchor_entry['pinned'] == full_sha
        assert anchor_entry['source_path'] == 'specs/security/constraints.md'

    @pytest.mark.proof("sync_status", "PROOF-68", "RULE-38")
    def test_legacy_mcp_entry_is_one_pending_migration(self):
        """RULE-38: the legacy entry reports as the `legacy-mcp` migration with
        the shared `--update` directive, not as an advisory of its own with a
        `--mcp` directive nobody else prints."""
        self._write_spec('login', (
            '# Feature: login\n\n'
            '## What it does\nHandles login.\n\n'
            '## Rules\n- RULE-1: Return 200\n\n'
            '## Proof\n- PROOF-1 (RULE-1): POST valid creds\n'
        ))
        mcp_path = os.path.join(self.project_root, '.mcp.json')

        # Case 1: version-pinned plugin-cache path -> one migration entry
        cache_path = '/Users/dev/.claude/plugins/cache/purlin/purlin/0.9.1/scripts/mcp/purlin_server.py'
        with open(mcp_path, 'w') as f:
            json.dump({'mcpServers': {'purlin': {
                'command': 'python3', 'args': [cache_path]}}}, f)
        result = purlin_server.sync_status(self.project_root)
        assert 'legacy-mcp' in result, \
            f'Expected the legacy-mcp migration entry, got: {result[:400]}'
        assert cache_path in result, 'The entry must show the pinned path'
        assert '\u2192 Run: purlin:init --update' in result, \
            'The advisory must close with the shared --update directive'
        assert '\u2192 Run: purlin:init --mcp' not in result, \
            'The --mcp directive must not be printed as a second advisory'
        preamble_section = result.split('login')[0]
        assert 'legacy-mcp' in preamble_section, \
            'The entry must appear in the preamble, before feature output'

        # Case 2: non-cache path (dev checkout) -> no entry
        with open(mcp_path, 'w') as f:
            json.dump({'mcpServers': {'purlin': {
                'command': 'python3',
                'args': ['/Users/dev/LocalCode/purlin/scripts/mcp/purlin_server.py']}}}, f)
        result = purlin_server.sync_status(self.project_root)
        assert 'legacy-mcp' not in result, \
            'Dev-checkout path must not report a migration'

        # Case 3: no .mcp.json -> no entry
        os.remove(mcp_path)
        result = purlin_server.sync_status(self.project_root)
        assert 'legacy-mcp' not in result, \
            'Absent .mcp.json must not report a migration'


class TestPlatformProofs:
    """sync_status RULE-47/48/52/53: a proof waiting for a platform is not a
    missing proof, and only a result that satisfies the platform clears it.

    A @windows proof that had never run reported nothing at all. Its rule read
    PASS off a local proof, so every surface was silent about a platform the
    project claims to support.
    """

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'audit')
        os.makedirs(self.spec_dir)
        self._config()

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, tag2, tag1='@unit', rules=2):
        lines = ['# Feature: locking', '', '## What it does', 'File locking.', '',
                 '## Rules', '- RULE-1: Locks on POSIX']
        proofs = [f'- PROOF-1 (RULE-1): fcntl path locks {tag1}']
        if rules == 2:
            lines.append('- RULE-2: Locks on Windows')
            proofs.append(f'- PROOF-2 (RULE-2): msvcrt path locks on a real runner {tag2}')
        with open(os.path.join(self.spec_dir, 'locking.md'), 'w') as f:
            f.write('\n'.join(lines + ['', '## Proof'] + proofs) + '\n')

    def _write_proofs(self, tier, proofs, platform=None):
        suffix = f'@{platform}' if platform else ''
        data = {"tier": tier, "proofs": proofs}
        if platform:
            data["platform"] = platform
            for p in proofs:
                p["platform"] = platform
        with open(os.path.join(self.spec_dir, f'locking.proofs-{tier}{suffix}.json'), 'w') as f:
            json.dump(data, f)

    def _remove_proofs(self, tier, platform=None):
        suffix = f'@{platform}' if platform else ''
        os.remove(os.path.join(self.spec_dir, f'locking.proofs-{tier}{suffix}.json'))

    def _config(self, platforms=None, **extra):
        cfg = {'report': False}
        cfg.update(extra)
        if platforms is not None:
            cfg['platforms'] = platforms
        with open(os.path.join(self.project_root, '.purlin', 'config.json'), 'w') as f:
            json.dump(cfg, f)

    def _entry(self, pid, rule, status='pass'):
        return {"feature": "locking", "id": pid, "rule": rule,
                "test_file": "dev/test_locking.py", "test_name": f"test_{pid.lower()}",
                "status": status, "tier": "unit"}

    def _seed_unit(self):
        self._write_proofs('unit', [self._entry("PROOF-1", "RULE-1")])

    def _payload(self):
        by_name = {f['name']: f for f in
                   purlin_server.read_report_payload(self.project_root)['features']}
        return by_name['locking']

    @pytest.mark.proof("sync_status", "PROOF-91", "RULE-35", tier="integration")
    def test_a_held_feature_reads_passing_and_the_header_decides_nothing(self):
        """RULE-35: a current receipt does not make a feature VERIFIED while a
        declared platform has never run, and `_report_feature` no longer picks
        the word with a ternary of its own."""
        import ast
        self._config({'windows-2022': {'os': 'windows'}})
        self._write_spec('@unit @on(windows-2022)', rules=2)
        self._write_proofs('unit', [self._entry("PROOF-1", "RULE-1")])

        feat = self._payload()
        receipt = {'feature': 'locking', 'vhash': feat['vhash'],
                   'commit': 'abc1234', 'timestamp': '2026-01-01T00:00:00Z',
                   'vhash_version': 2, 'rules': ['RULE-1']}
        receipt_path = os.path.join(self.spec_dir, 'locking.receipt.json')
        with open(receipt_path, 'w') as f:
            json.dump(receipt, f)

        out = purlin_server.sync_status(self.project_root)
        assert 'locking: PASSING' in out, (
            f"a current receipt must not earn VERIFIED while windows-2022 has "
            f"never run:\n{out}")
        assert 'locking: VERIFIED' not in out and 'locking: PARTIAL' not in out, out
        row = next(l for l in out.splitlines()
                   if l.startswith('\u2502 locking'))
        assert 'PASSING' in row and 'VERIFIED' not in row, row
        assert 'Receipt stale' not in out, (
            f"the receipt is current; only the platform is missing:\n{out}")
        feat = self._payload()
        assert feat['status'] == 'PASSING' and feat['receipt']['stale'] is False, feat

        # Prove the platform: the same receipt now earns VERIFIED.
        self._write_proofs('unit', [self._entry("PROOF-2", "RULE-2")],
                           platform='windows-2022')
        feat = self._payload()
        with open(receipt_path, 'w') as f:
            json.dump({**receipt, 'vhash': feat['vhash']}, f)
        out = purlin_server.sync_status(self.project_root)
        assert 'locking: VERIFIED' in out, out

        # The header may not contain a VERIFIED literal of its own.
        server = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                              'scripts', 'mcp', 'purlin_server.py')
        with open(server) as f:
            tree = ast.parse(f.read())
        report_feature = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == '_report_feature')
        literals = [n.value for n in ast.walk(report_feature)
                    if isinstance(n, ast.Constant) and n.value == 'VERIFIED']
        assert not literals, (
            "_report_feature must route its header through _determine_status, "
            f"not decide VERIFIED itself; found {len(literals)} literal(s)")

        platform_status = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == '_platform_status')
        returned = {c.value for r in ast.walk(platform_status)
                    if isinstance(r, ast.Return)
                    for c in ast.walk(r)
                    if isinstance(c, ast.Constant) and isinstance(c.value, str)}
        assert returned == {'FAILING', 'AWAITING', 'PASSING', 'VERIFIED'}, (
            f"the record vocabulary must be exactly four words, got {sorted(returned)}")

    @pytest.mark.proof("sync_status", "PROOF-79", "RULE-47", tier="integration")
    def test_awaiting_names_the_platform_and_only_a_satisfying_result_clears_it(self):
        self._config({'windows-2022': {'os': 'windows'}, 'macos-14': {'os': 'macos'}})
        self._write_spec('@unit @on(windows-2022)')
        self._seed_unit()
        out = purlin_server.sync_status(self.project_root)

        assert 'windows-2022: awaiting runner' in out, out
        assert 'PROOF-2' in out, "the awaiting line must name the proof id"
        assert 'NO PROOF' not in out, (
            "a platform proof that has not run there is waiting, not missing; "
            f"reporting NO PROOF sends someone to write a test that exists:\n{out}")
        # RULE-2's only declared proof is awaiting on every platform it
        # declares, so it leaves the denominator: 1 of 1, and the feature is
        # not dragged to PARTIAL.
        assert '1/1 rules proved' in out, (
            f"the platform-only rule must leave the coverage denominator:\n{out}")
        assert 'locking: PASSING' in out or 'locking: VERIFIED' in out, (
            f"an absent runner must not turn a covered feature PARTIAL:\n{out}")
        assert 'PARTIAL' not in out and 'FAILING' not in out, out

        # A result scoped to the declared id itself clears it (R == D).
        self._write_proofs('unit', [self._entry("PROOF-2", "RULE-2")], platform='windows-2022')
        out2 = purlin_server.sync_status(self.project_root)
        assert 'awaiting runner' not in out2, out2
        assert '2/2 rules proved' in out2, (
            f"the rule must rejoin the denominator once proved:\n{out2}")

        # Declared on the family instead: the same windows-2022 file satisfies
        # it, because the registry says windows-2022 is a windows.
        self._write_spec('@unit @on(windows)')
        out3 = purlin_server.sync_status(self.project_root)
        assert 'awaiting runner' not in out3, (
            f"a registered id of the declared family must satisfy the family:\n{out3}")
        assert '2/2 rules proved' in out3, out3

        # And a macos-14 file does not: the family rule is os equality, not
        # "any scoped result".
        self._remove_proofs('unit', 'windows-2022')
        self._write_proofs('unit', [self._entry("PROOF-2", "RULE-2")], platform='macos-14')
        out4 = purlin_server.sync_status(self.project_root)
        assert 'windows: awaiting runner' in out4, (
            f"a result from another family must not satisfy windows:\n{out4}")
        assert '1/1 rules proved' in out4, out4

        # The satisfaction rule itself, so the family clause is pinned directly.
        registry, _ = purlin_server._platform_registry(
            {'platforms': {'windows-2022': {'os': 'windows'}, 'macos-14': {'os': 'macos'}}})
        sat = purlin_server._result_satisfies
        assert sat('windows-2022', 'windows-2022', registry), "R == D"
        assert sat('windows-2022', 'windows', registry), "registry[R].os == D"
        assert not sat('macos-14', 'windows', registry), "another family"
        assert not sat('windows', 'windows-2022', registry), (
            "a family result never satisfies a specific id")
        assert not sat('ubuntu-24', 'linux', registry), (
            "an unregistered id satisfies nothing but itself")
        assert not sat(None, 'windows', registry), "an agnostic result satisfies nothing"

    @pytest.mark.proof("sync_status", "PROOF-80", "RULE-48", tier="integration")
    def test_provenance_comes_from_the_scoped_files_commit_not_the_proof_file(self):
        """Proof entries carry no timestamp, which is what keeps a CI
        commit-back idempotent. So 'last proved remotely' is read from git."""
        self._write_spec('@unit @on(windows)')
        self._seed_unit()
        self._write_proofs('unit', [self._entry("PROOF-2", "RULE-2")], platform='windows')
        env = dict(os.environ,
                   GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@e',
                   GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@e')

        def git(*args):
            return subprocess.run(['git'] + list(args), cwd=self.project_root,
                                  capture_output=True, text=True, env=env)

        git('init', '-q')
        git('add', '-A')
        git('commit', '-q', '-m', 'test(locking): windows proofs\n\n'
            'Purlin-Runner: github-actions/windows-latest\n'
            'Purlin-Platform: windows')

        out = purlin_server.sync_status(self.project_root)
        assert 'windows: 1/1 proved remotely' in out, f"no provenance line:\n{out}"
        assert 'github-actions/windows-latest' in out, (
            f"the runner must come from the commit trailer:\n{out}")
        assert 'trailer says' not in out, (
            f"a trailer that agrees with the filename must not be flagged:\n{out}")
        prov = purlin_server._platform_provenance(
            self.project_root, 'specs/audit/locking.md', 'locking', 'unit', 'windows')
        assert prov['commit'] == git('rev-parse', 'HEAD').stdout.strip()
        assert prov['runner'] == 'github-actions/windows-latest'
        assert prov['trailer_platform'] == 'windows'

        # No timestamp field was added to the proof entries to achieve it:
        # exactly the eight fields a scoped entry carries.
        with open(os.path.join(self.spec_dir, 'locking.proofs-unit@windows.json')) as f:
            entry = json.load(f)['proofs'][0]
        assert set(entry) == {'feature', 'id', 'rule', 'test_file', 'test_name',
                              'status', 'tier', 'platform'}, (
            f"provenance must not add a field to the proof entry, got {sorted(entry)}")

        # A trailer naming a different platform than the filename is reported,
        # not trusted and not hidden.
        git('commit', '-q', '--allow-empty', '--amend', '-m',
            'test(locking): windows proofs\n\n'
            'Purlin-Runner: github-actions/windows-latest\nPurlin-Platform: other')
        out2 = purlin_server.sync_status(self.project_root)
        assert 'trailer says other' in out2, (
            f"a filename/trailer mismatch must be named:\n{out2}")

        # No trailer at all still reports, runner unrecorded.
        git('commit', '-q', '--allow-empty', '--amend', '-m', 'test(locking): windows proofs')
        out3 = purlin_server.sync_status(self.project_root)
        assert 'proved remotely' in out3, (
            f"a missing trailer must not drop the line:\n{out3}")
        assert 'runner not recorded' in out3, out3
        assert 'trailer says' not in out3, out3

    @pytest.mark.proof("sync_status", "PROOF-85", "RULE-52", tier="integration")
    def test_platforms_block_says_where_each_declared_platform_can_be_proved(self, monkeypatch):
        monkeypatch.delenv('PURLIN_PLATFORM', raising=False)
        monkeypatch.setattr(purlin_server.platform, 'system', lambda: 'Darwin')
        monkeypatch.setattr(purlin_server.platform, 'mac_ver',
                            lambda: ('14.7.1', ('', '', ''), ''))
        monkeypatch.setattr(purlin_server.platform, 'machine', lambda: 'arm64')

        self._write_spec('@unit @on(windows-2022)', tag1='@unit @on(macos-14)')
        self._seed_unit()
        runner = {'provider': 'github', 'workflow': 'purlin-windows-proofs.yml'}
        self._config({'macos-14': {'os': 'macos', 'version': '14'},
                      'windows-2022': {'os': 'windows', 'runner': runner}})

        def block(out):
            lines = out.splitlines()
            start = next(i for i, l in enumerate(lines) if l.startswith('Platforms:'))
            end = start + 1
            while end < len(lines) and lines[end].startswith('  '):
                end += 1
            return lines[start:end], lines, start

        out = purlin_server.sync_status(self.project_root)
        lines, all_lines, start = block(out)
        assert lines[0] == 'Platforms: host macos 14.7.1 arm64', lines
        assert '  local:  macos-14 (1 proof); run with PURLIN_PLATFORM=macos-14' in lines, lines
        assert ('  runner: windows-2022 (1 proof; github workflow '
                'purlin-windows-proofs.yml)') in lines, lines
        assert not any('macos-14' in l and l.startswith('  runner') for l in lines), lines
        # After the mode line, before the first feature block.
        mode_idx = next(i for i, l in enumerate(all_lines)
                        if l.startswith('Remote verification:'))
        feat_idx = next(i for i, l in enumerate(all_lines) if l.startswith('locking:'))
        assert mode_idx < start < feat_idx, (mode_idx, start, feat_idx)

        # No runner block: said so, never silently dropped.
        self._config({'macos-14': {'os': 'macos', 'version': '14'},
                      'windows-2022': {'os': 'windows'}})
        lines, _, _ = block(purlin_server.sync_status(self.project_root))
        assert '  runner: windows-2022 (1 proof; no runner configured)' in lines, lines

        # A provider purlin:test cannot dispatch.
        self._config({'macos-14': {'os': 'macos', 'version': '14'},
                      'windows-2022': {'os': 'windows', 'runner': {'provider': 'ado'}}})
        lines, _, _ = block(purlin_server.sync_status(self.project_root))
        assert ('  runner: windows-2022 (1 proof; runner provider ado is not one '
                'purlin:test can dispatch)') in lines, lines

        # An id nobody registered is listed, not dropped.
        self._write_spec('@unit @on(foo)', tag1='@unit @on(macos-14)')
        lines, _, _ = block(purlin_server.sync_status(self.project_root))
        assert '  runner: foo (1 proof; unregistered)' in lines, lines

        # A project with no @on has no Platforms line at all.
        self._write_spec('@unit', tag1='@unit')
        out = purlin_server.sync_status(self.project_root)
        assert 'Platforms:' not in out, out

    @pytest.mark.proof("sync_status", "PROOF-86", "RULE-53", tier="integration")
    def test_an_undeclared_platform_result_is_named_and_counts_toward_nothing(self):
        self._config({'ubuntu-24': {'os': 'linux'}})
        # PROOF-2 is proved on macos, so RULE-2 stays in the denominator and
        # its status is visible: a failing result that reached the rule
        # lookup would turn the feature FAILING.
        self._write_spec('@unit @on(macos, windows)')
        self._seed_unit()
        self._write_proofs('unit', [self._entry("PROOF-2", "RULE-2")], platform='macos')
        before = purlin_server.sync_status(self.project_root)
        assert '2/2 rules proved' in before and 'locking: PASSING' in before, before
        vhash_before = next(l for l in before.splitlines() if 'vhash=' in l)

        # A failing result under a platform the proof does not declare. If it
        # counted toward anything, a fail is what would show.
        self._write_proofs('unit', [self._entry("PROOF-2", "RULE-2", status='fail')],
                           platform='ubuntu-24')
        out = purlin_server.sync_status(self.project_root)
        assert 'Undeclared platform result' in out, out
        assert 'locking.proofs-unit@ubuntu-24.json' in out and 'PROOF-2' in out, (
            f"the advisory must name the file and the proof:\n{out}")
        assert 'windows: awaiting runner' in out and 'PROOF-2' in out, (
            f"the undeclared result must not satisfy the declared platform:\n{out}")
        assert '2/2 rules proved' in out, f"coverage must be unchanged:\n{out}"
        assert 'locking: PASSING' in out, (
            f"a result that counts toward nothing cannot fail a rule:\n{out}")
        assert 'FAILING' not in out and 'FAIL (' not in out, out
        assert next(l for l in out.splitlines() if 'vhash=' in l) == vhash_before, (
            "a result that counts toward nothing must not move the vhash")

        feat = self._payload()
        assert feat['undeclared'] == [
            {'id': 'PROOF-2', 'tier': 'unit', 'platform': 'ubuntu-24'}], feat['undeclared']
        assert feat['awaiting_runner'] == [
            {'id': 'PROOF-2', 'tier': 'unit', 'platform': 'windows'}], feat['awaiting_runner']
        assert feat['platforms']['windows']['awaiting'] == ['PROOF-2'], feat['platforms']
        assert feat['platforms']['macos']['status'] in ('PASSING', 'VERIFIED'), \
            feat['platforms']
        assert 'ubuntu-24' not in feat['platforms'], feat['platforms']
        assert feat['status'] in ('PASSING', 'VERIFIED'), feat['status']
        rule2 = next(r for r in feat['rules'] if r['id'] == 'RULE-2')
        assert rule2['status'] == 'PASS', rule2
        assert all(p['status'] != 'fail' for p in rule2['proofs']), (
            f"the undeclared result must not be listed under the rule: {rule2['proofs']}")

        # Delete the file: the advisory goes with it.
        self._remove_proofs('unit', 'ubuntu-24')
        out2 = purlin_server.sync_status(self.project_root)
        assert 'Undeclared platform result' not in out2, out2
        assert self._payload()['undeclared'] == []

    @pytest.mark.proof("sync_status", "PROOF-87", "RULE-47", tier="integration")
    def test_a_rule_with_one_platform_proved_stays_in_and_counts(self):
        # RULE-1: one proof declared on two platforms, proved on one.
        self._write_spec(None, tag1='@unit @on(macos, windows)', rules=1)
        self._write_proofs('unit', [self._entry("PROOF-1", "RULE-1")], platform='macos')
        out = purlin_server.sync_status(self.project_root)

        assert 'locking: PASSING' in out, (
            f"a rule proved on one declared platform counts what it proved:\n{out}")
        assert '1/1 rules proved' in out, (
            f"the rule has a result, so it stays in the denominator:\n{out}")
        assert 'PARTIAL' not in out and '0/0' not in out, out
        assert 'windows: awaiting runner, 1 proof (PROOF-1)' in out, (
            f"the unproved platform must still be reported:\n{out}")
        assert 'left the coverage denominator' not in out, (
            f"nothing left the denominator, so the line must not claim it:\n{out}")

        feat = self._payload()
        assert feat['proved'] == 1 and feat['total'] == 1, (feat['proved'], feat['total'])
        assert feat['awaiting_runner'] == [
            {'id': 'PROOF-1', 'tier': 'unit', 'platform': 'windows'}], feat['awaiting_runner']
        assert feat['platforms']['macos']['status'] in ('PASSING', 'VERIFIED'), \
            feat['platforms']
        assert feat['platforms']['windows']['status'] == 'AWAITING', feat['platforms']

        # RULE-2: two proofs, one awaiting on every platform it declares and
        # one agnostic and passing. The rule leaves the denominator only when
        # EVERY declared proof is awaiting, so this one stays: 2/2.
        with open(os.path.join(self.spec_dir, 'locking.md'), 'a') as f:
            f.write('- PROOF-3 (RULE-2): agnostic path @unit\n')
        spec = open(os.path.join(self.spec_dir, 'locking.md')).read().replace(
            '- RULE-1: Locks on POSIX\n',
            '- RULE-1: Locks on POSIX\n- RULE-2: Locks elsewhere\n').replace(
            '## Proof\n', '## Proof\n- PROOF-2 (RULE-2): scoped path @unit @on(windows)\n')
        with open(os.path.join(self.spec_dir, 'locking.md'), 'w') as f:
            f.write(spec)
        self._write_proofs('unit', [self._entry("PROOF-3", "RULE-2")])
        out2 = purlin_server.sync_status(self.project_root)
        assert '2/2 rules proved' in out2 and 'locking: PASSING' in out2, (
            f"a rule with one awaiting proof and one proved proof stays in:\n{out2}")
        assert 'left the coverage denominator' not in out2, out2
        assert 'windows: awaiting runner, 2 proofs (PROOF-1, PROOF-2)' in out2, out2


class TestRemoteVerificationMode:
    """sync_status RULE-49: report the declared mode, and say it is a declaration.

    Builds its own fixture rather than subclassing TestRunnerGatedProofs:
    inheriting would re-run every parent test under this class's name, and one
    of those asserts `awaiting runner` is absent, which this line can contain.
    """

    SPEC = (
        '# Feature: locking\n\n'
        '## Rules\n'
        '- RULE-1: Locks on POSIX\n'
        '- RULE-2: Locks on Windows\n\n'
        '## Proof\n'
        '- PROOF-1 (RULE-1): fcntl path locks @unit\n'
        '- PROOF-2 (RULE-2): msvcrt path locks on a real windows runner @windows\n'
    )

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'audit')
        os.makedirs(self.spec_dir)
        with open(os.path.join(self.spec_dir, 'locking.md'), 'w') as f:
            f.write(self.SPEC)
        self._write_proofs('unit', [
            {"feature": "locking", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "dev/test_locking.py", "test_name": "test_fcntl",
             "status": "pass", "tier": "unit"},
        ])

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_proofs(self, tier, proofs):
        with open(os.path.join(self.spec_dir, f'locking.proofs-{tier}.json'), 'w') as f:
            json.dump({"tier": tier, "proofs": proofs}, f)

    def _config(self, mode=None):
        cfg = {'report': False}
        if mode is not None:
            cfg['remote_verification'] = mode
        with open(os.path.join(self.project_root, '.purlin', 'config.json'), 'w') as f:
            json.dump(cfg, f)

    def _mode_line(self):
        out = purlin_server.sync_status(self.project_root)
        line = next((l for l in out.splitlines()
                     if l.startswith('Remote verification:')), None)
        return line, out

    @pytest.mark.proof("sync_status", "PROOF-81", "RULE-49", tier="integration")
    def test_mode_is_reported_as_a_declaration_not_as_the_gate(self):
        # required and optional: the mode, plus the declaration/enforcement
        # split. The field is editable in the tree, so presenting it as the
        # gate would misreport where the trust boundary is.
        for mode in ('required', 'optional'):
            self._config(mode)
            line, out = self._mode_line()
            assert line, f"no remote-verification line for mode {mode!r}:\n{out}"
            assert mode in line, f"the line must name the mode: {line!r}"
            assert 'branch protection' in line, (
                f"the line must name the enforcement, not just the mode: {line!r}")
            assert 'Declared in config' in line, (
                f"the line must say the field is a declaration: {line!r}")

        # off, with a proof actually awaiting: say how many and where to go.
        # Silence here leaves a proof that can never fill in looking like one
        # that simply has not run yet.
        self._config('off')
        line, out = self._mode_line()
        assert line, f"an off project with a waiting proof must report:\n{out}"
        assert 'off' in line and '1 proof' in line, line
        assert 'purlin:test' in line, (
            f"the off line must point at the skill that sets a runner up: {line!r}")

        # A typo must not silently disable the declaration.
        self._config('requried')
        line, out = self._mode_line()
        assert line, f"an unrecognized mode must be reported, not dropped:\n{out}"
        assert 'not a recognized mode' in line, line
        for valid in ('required', 'optional', 'off'):
            assert valid in line, (
                f"the error must name the valid modes so the typo is fixable: {line!r}")

        # off, and the runner already proved it: nothing is stuck, so the line
        # must go. Keyed on declared rather than awaiting, this branch told a
        # fully proved project its proofs "will stay awaiting".
        self._write_proofs('windows', [
            {"feature": "locking", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "dev/test_windows.py", "test_name": "test_msvcrt",
             "status": "pass", "tier": "windows"},
        ])
        self._config('off')
        line, out = self._mode_line()
        assert line is None, (
            "an off project whose runner-gated proofs are already proved has "
            f"nothing stuck and must print no mode line:\n{out}")

        # And with no runner-gated proof declared at all, still silent: a
        # project that never opted in gains nothing from the line.
        os.remove(os.path.join(self.spec_dir, 'locking.proofs-windows.json'))
        with open(os.path.join(self.spec_dir, 'locking.md'), 'w') as f:
            f.write('# Feature: locking\n\n'
                    '## Rules\n- RULE-1: Locks on POSIX\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): fcntl path locks @unit\n')
        line, out = self._mode_line()
        assert line is None, (
            f"an off project with nothing gated must print no mode line:\n{out}")


class TestIntegrityFormula:
    """sync_status RULE-33: integrity formula consistency."""

    @pytest.mark.proof("sync_status", "PROOF-56", "RULE-33")
    def test_integrity_formula_consistent_across_files(self):
        """The integrity formula is identical in audit_criteria, audit SKILL, and sync_status spec."""
        root = os.path.join(os.path.dirname(__file__), '..')
        files_to_check = [
            os.path.join(root, 'references', 'audit_criteria.md'),
            os.path.join(root, 'skills', 'audit', 'SKILL.md'),
            os.path.join(root, 'specs', 'mcp', 'sync_status.md'),
        ]
        formula = '(STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL)'
        for path in files_to_check:
            with open(path) as f:
                content = f.read()
            assert formula in content, (
                f"File {os.path.basename(path)} missing integrity formula: {formula}"
            )
            # NONE must NOT appear in the formula's denominator expression
            # The formula is: (STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL)
            # NONE should be excluded from both numerator and denominator
            import re
            # Find all formula-like expressions (ratio with parenthesized terms)
            formulas_found = re.findall(
                r'\([A-Z+\s]+\)\s*/\s*\(([A-Z+\s]+)\)', content
            )
            for denom in formulas_found:
                assert 'NONE' not in denom, (
                    f"File {os.path.basename(path)} includes NONE in formula denominator: {denom}"
                )



    @pytest.mark.proof("sync_status", "PROOF-75", "RULE-43")
    def test_design_formula_consistent_across_the_same_three_files(self):
        """RULE-43: the Design formula is pinned where RULE-33 pins Integrity's.

        RULE-33 kept the integrity formula identical across three files. Design
        had no equivalent, so its formula could drift between the criteria
        reference, the audit skill and this spec without anything noticing.
        """
        formula = 'PROVABLE / (PROVABLE + LOOSE + UNPROVABLE)'
        root = os.path.join(os.path.dirname(__file__), '..')
        for rel in ('references/audit_criteria.md',
                    'skills/audit/SKILL.md',
                    'specs/mcp/sync_status.md'):
            with open(os.path.join(root, rel), encoding='utf-8') as f:
                body = f.read()
            assert formula in body, \
                f"{rel} does not carry the design formula {formula!r}"
            # STRUCTURAL is excluded from the denominator, never counted in it.
            for line in body.splitlines():
                if formula in line:
                    denom = line.split(formula, 1)[0] + formula
                    assert 'STRUCTURAL +' not in denom, \
                        f"{rel} includes STRUCTURAL in the design denominator: {line}"
class TestPurlinConfig:
    """purlin_config RULE-1: config read/write."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("purlin_config", "PROOF-1", "RULE-1")
    def test_read_write(self):
        # Write a key — returns the exact confirmation string
        result = purlin_server.handle_purlin_config(
            self.project_root,
            {"action": "write", "key": "test_key", "value": "test_val"}
        )
        assert result == 'Set \'test_key\' = "test_val"', \
            f"Write should return exact confirmation, got: {result!r}"

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

        # Error paths: invalid action and write without a key must not silently succeed.
        invalid = purlin_server.handle_purlin_config(
            self.project_root, {"action": "delete", "key": "test_key"}
        )
        assert "Unknown action" in invalid, f"Invalid action should error, got: {invalid!r}"
        # The rejected action must not have mutated the config.
        after = json.loads(purlin_server.handle_purlin_config(
            self.project_root, {"action": "read"}))
        assert after == {"test_key": "test_val"}, f"Invalid action mutated config: {after}"

        no_key = purlin_server.handle_purlin_config(
            self.project_root, {"action": "write", "value": "x"}
        )
        assert "key" in no_key.lower() and "required" in no_key.lower(), \
            f"Write without key should error, got: {no_key!r}"


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
        assert data['proof_status']['refs']['proved'] == 1
        assert data['proof_status']['refs']['total'] == 1


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
    def test_coverage_gap_drift_flag(self):
        """CHANGED_BEHAVIOR file gets behavioral_gap when spec has zero proved rules."""
        # Create a spec with rules but NO proof file
        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write('# Feature: login\n\n> Scope: src/login.py\n\n'
                    '## What it does\nLogin.\n\n'
                    '## Rules\n- RULE-1: Verify config contains auth section\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Grep config for auth section; verify present\n')
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
        assert login_entry, "src/login.py not in drift files"
        assert login_entry['category'] == 'CHANGED_BEHAVIOR'
        assert login_entry.get('behavioral_gap') is True, \
            f"Expected behavioral_gap=True, got {login_entry}"

    @pytest.mark.proof("drift", "PROOF-9", "RULE-9")
    def test_drift_flags_array(self):
        """drift_flags array contains features with coverage gap and changed files."""
        # Create spec with rules but NO proof file
        with open(os.path.join(self.project_root, 'specs', 'auth', 'login.md'), 'w') as f:
            f.write('# Feature: login\n\n> Scope: src/login.py\n\n'
                    '## What it does\nLogin.\n\n'
                    '## Rules\n- RULE-1: Verify config contains auth section\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Grep config for auth section; verify present\n')
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
        assert login_drift, f"No drift flag for login, got {data['drift_flags']}"
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

    @pytest.mark.proof("drift", "PROOF-17", "RULE-15")
    def test_unpinned_anchor_detected(self):
        """Anchor with Source but no Pinned returns external_anchor_drift with status=unpinned."""
        # Create an anchor spec with > Source: but no > Pinned:
        anchor_dir = os.path.join(self.project_root, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        with open(os.path.join(anchor_dir, 'security_policy.md'), 'w') as f:
            f.write(
                '# Anchor: security_policy\n\n'
                '> Source: https://github.com/acme/policies.git\n\n'
                '## What it does\nSecurity.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add unpinned anchor'],
                       cwd=self.project_root, capture_output=True, check=True)

        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)
        assert 'external_anchor_drift' in data, \
            f"Expected external_anchor_drift key in drift result, got keys: {list(data.keys())}"
        unpinned_entries = [
            e for e in data['external_anchor_drift']
            if e.get('anchor') == 'security_policy'
        ]
        assert len(unpinned_entries) == 1, \
            f"Expected 1 external_anchor_drift entry for security_policy, got: {unpinned_entries}"
        assert unpinned_entries[0]['status'] == 'unpinned', \
            f"Expected status=unpinned, got: {unpinned_entries[0]}"


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


class TestDriftRuleDetails:
    """drift RULE-16: rule_details in drift output."""

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        subprocess.run(['git', 'init'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                       cwd=self.project_root, capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                       cwd=self.project_root, capture_output=True, check=True)

        # Create a source file in scope
        os.makedirs(os.path.join(self.project_root, 'src', 'api'))
        with open(os.path.join(self.project_root, 'src', 'api', 'handler.py'), 'w') as f:
            f.write('def handle(): return 200\n')

        # Create a spec with 3 rules scoped to the source file
        os.makedirs(os.path.join(self.project_root, 'specs', 'api'))
        with open(os.path.join(self.project_root, 'specs', 'api', 'handler.md'), 'w') as f:
            f.write(
                '# Feature: handler\n\n'
                '> Description: API request handler\n'
                '> Scope: src/api/handler.py\n\n'
                '## Rules\n'
                '- RULE-1: Returns 200 on valid input\n'
                '- RULE-2: Returns 400 on invalid input\n'
                '- RULE-3: Logs request duration\n\n'
                '## Proof\n'
                '- PROOF-1 (RULE-1): POST valid input; verify 200\n'
                '- PROOF-2 (RULE-2): POST invalid input; verify 400\n'
                '- PROOF-3 (RULE-3): POST request; verify duration logged\n'
            )

        # Create proof file with 2 of 3 rules proved
        with open(os.path.join(self.project_root, 'specs', 'api',
                               'handler.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "handler", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test.py", "test_name": "test_valid",
                 "status": "pass", "tier": "unit"},
                {"feature": "handler", "id": "PROOF-2", "rule": "RULE-2",
                 "test_file": "tests/test.py", "test_name": "test_invalid",
                 "status": "pass", "tier": "unit"},
            ]}, f)

        # Initial commit with verify prefix
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'verify: initial'],
                       cwd=self.project_root, capture_output=True, check=True)

        # Now modify the scope file to create a CHANGED_BEHAVIOR entry
        with open(os.path.join(self.project_root, 'src', 'api', 'handler.py'), 'w') as f:
            f.write('def handle(): return 200\ndef batch(): return 201\n')
        subprocess.run(['git', 'add', '.'], cwd=self.project_root,
                       capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'feat: add batch endpoint'],
                       cwd=self.project_root, capture_output=True, check=True)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    @pytest.mark.proof("drift", "PROOF-19", "RULE-16", tier="integration")
    def test_rule_details_for_changed_behavior(self):
        """drift returns rule_details with per-rule proof status for changed specs."""
        result_text = purlin_server.drift(self.project_root)
        data = json.loads(result_text)

        # rule_details should exist and contain the handler spec
        assert 'rule_details' in data, (
            f"Missing rule_details in drift output. Keys: {list(data.keys())}"
        )
        assert 'handler' in data['rule_details'], (
            f"handler not in rule_details. Specs: {list(data['rule_details'].keys())}"
        )

        details = data['rule_details']['handler']

        # Should have 3 rule entries
        assert details['total_rules'] == 3, (
            f"Expected 3 total_rules, got {details['total_rules']}"
        )
        assert details['proved_rules'] == 2, (
            f"Expected 2 proved_rules, got {details['proved_rules']}"
        )

        # Check individual rules
        rules = {r['rule_id']: r for r in details['rules']}
        assert 'RULE-1' in rules
        assert 'RULE-2' in rules
        assert 'RULE-3' in rules

        # RULE-1 and RULE-2 have passing proofs, RULE-3 does not
        assert rules['RULE-1']['proof_status'] == 'pass', (
            f"RULE-1 should be pass, got {rules['RULE-1']['proof_status']}"
        )
        assert rules['RULE-2']['proof_status'] == 'pass', (
            f"RULE-2 should be pass, got {rules['RULE-2']['proof_status']}"
        )
        assert rules['RULE-3']['proof_status'] == 'unproved', (
            f"RULE-3 should be unproved, got {rules['RULE-3']['proof_status']}"
        )

        # Rule descriptions should be present
        assert 'Returns 200' in rules['RULE-1']['description']
        assert 'Returns 400' in rules['RULE-2']['description']
        assert 'Logs request duration' in rules['RULE-3']['description']

        # Changed files should include the scope file
        assert 'src/api/handler.py' in details['changed_files'], (
            f"Expected handler.py in changed_files, got {details['changed_files']}"
        )


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
    def test_vhash_v2_binds_rule_text_test_identity_and_feature(self):
        """RULE-6: what the vhash binds, one binding at a time.

        The pinned literal is the mutation check for the formula itself: any
        change to the segment order, the field list, the sort key or the
        separator moves it.
        """
        def _proof(**over):
            base = {"feature": "locking", "id": "PROOF-1", "rule": "RULE-1",
                    "status": "pass", "tier": "unit", "platform": None,
                    "test_file": "tests/test_lock.py",
                    "test_name": "test_fcntl"}
            base.update(over)
            return base

        rules = {"RULE-1": "Locks on POSIX", "security/RULE-1": "No eval"}
        proofs = [
            _proof(),
            _proof(feature="security", platform="windows-2022",
                   test_file="tests/test_sec.py", test_name="test_no_eval"),
        ]
        vhash = purlin_server._compute_vhash(rules, proofs)

        assert len(vhash) == 8
        assert all(c in '0123456789abcdef' for c in vhash)
        # Pinned from the v2 formula: sha256("\x00".join(
        #   ["purlin-vhash/2"] + R segments + P segments))[:8]
        assert vhash == 'c92b8ee3', (
            f"vhash v2 algorithm mismatch: expected c92b8ee3, got {vhash}. "
            "The segment order, field list, sort key or separator moved.")

        # Rule text is bound, so a reworded rule stales the receipt.
        reworded = dict(rules, **{"RULE-1": "Locks on POSIX systems"})
        assert purlin_server._compute_vhash(reworded, proofs) != vhash

        # ...but whitespace is normalised, so a reflow does not.
        reflowed = dict(rules, **{"RULE-1": "Locks\n   on   POSIX"})
        assert purlin_server._compute_vhash(reflowed, proofs) == vhash, \
            "reflowing a rule must not invalidate a receipt"

        # Test identity is bound: a renamed or rewritten test stales it.
        swapped = [proofs[0], dict(proofs[1], test_name="test_eval_banned")]
        assert purlin_server._compute_vhash(rules, swapped) != vhash

        # `feature` is bound, so the same PROOF id under a feature and under a
        # required anchor no longer collide.
        same_id = [_proof(), _proof(feature="security")]
        collide = [_proof(), _proof()]
        assert purlin_server._compute_vhash(rules, same_id) != \
            purlin_server._compute_vhash(rules, collide), \
            "PROOF-1 under two features must not hash like one proof twice"

        # No value can forge a field boundary. These two inputs are
        # byte-identical once the segments are joined with ':' and differ only
        # in where the ':' falls between test_file and test_name.
        forged_a = [_proof(test_file="a:b", test_name="c")]
        forged_b = [_proof(test_file="a", test_name="b:c")]
        assert purlin_server._compute_vhash(rules, forged_a) != \
            purlin_server._compute_vhash(rules, forged_b), \
            "a ':' inside a field must not be able to forge a field boundary"


class TestCoverageReportUsability:
    """RULE-40/41/42 — the report must be legible and route by observable state.

    All three defects hit a spec-first project hardest: every row is UNTESTED, so
    every row had a broken border; the proof descriptions the user just wrote were
    not shown at all; and the only directive offered was purlin:test, which
    collects nothing when no code exists.
    """

    @pytest.mark.proof("sync_status", "PROOF-70", "RULE-40")
    def test_table_borders_align_for_every_status(self):
        from purlin_server import _build_summary_table
        rows = [
            ("feat_failing", 0, 2, "FAILING"),
            ("feat_partial", 1, 2, "PARTIAL"),
            ("feat_passing", 2, 2, "PASSING"),
            ("feat_verified", 2, 2, "VERIFIED"),
            ("feat_untested", 0, 2, "UNTESTED"),
        ]
        lines = [l for l in _build_summary_table(rows)
                 if l.startswith(('┌', '│', '├', '└'))]
        widths = {len(l) for l in lines}
        assert len(widths) == 1, (
            f"table lines have differing widths {sorted(widths)} — the status column "
            f"overflows for 8-character statuses:\n" + "\n".join(lines))

        # And the longest status is actually present, not truncated.
        assert any('UNTESTED' in l for l in lines)
        assert any('VERIFIED' in l for l in lines)

    def _spec_project(self, tmpdir, scope='src/auth.py'):
        d = os.path.join(tmpdir, 'specs', 'auth')
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, 'login.md'), 'w') as f:
            f.write(
                '# Feature: login\n\n'
                f'> Scope: {scope}\n\n'
                '## Rules\n\n'
                '- RULE-1: Returns 401 on a wrong password\n\n'
                '## Proof\n\n'
                '- PROOF-7 (RULE-1): POST a wrong password for "alice"; verify 401\n')
        return tmpdir

    @pytest.mark.proof("sync_status", "PROOF-71", "RULE-41")
    def test_reports_declared_proof_ids_and_descriptions(self):
        from purlin_server import sync_status
        with tempfile.TemporaryDirectory() as tmpdir:
            self._spec_project(tmpdir)
            out = sync_status(tmpdir)
            assert 'PROOF-7' in out, \
                "the declared proof id must appear; the report showed none of it"
            assert 'POST a wrong password' in out, \
                "the proof description the user wrote must be surfaced"
            assert '"PROOF-N"' not in out, \
                "the suggested marker must name the real declared id, not the placeholder"

    @pytest.mark.proof("sync_status", "PROOF-72", "RULE-42")
    def test_directive_routes_on_whether_code_exists(self):
        from purlin_server import sync_status
        with tempfile.TemporaryDirectory() as tmpdir:
            self._spec_project(tmpdir)

            # Scope file absent: nothing is built, so building is the next step.
            out = sync_status(tmpdir)
            assert 'purlin:build login' in out, \
                "a spec whose scope files do not exist must route to purlin:build"
            assert out.count('→ Run: purlin:build login') == 1, \
                f"the directive must appear once, got:\n{out}"
            assert 'Run: purlin:test' not in out, \
                "purlin:test collects nothing when no code exists"

            # Scope file present: the gap is tests, not code.
            os.makedirs(os.path.join(tmpdir, 'src'), exist_ok=True)
            with open(os.path.join(tmpdir, 'src', 'auth.py'), 'w') as f:
                f.write('def auth(): pass\n')
            out = sync_status(tmpdir)
            assert 'Run: purlin:test' in out
            assert 'purlin:build' not in out


class TestPlatformRegistry:
    """sync_status RULE-50/51: the `platforms` registry and the host it runs on.

    A malformed entry is dropped and named, never silently: a typo that
    vanished would leave a proof matching every host of its family.
    """

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'audit')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, tag):
        # Two rules: RULE-1 proved by an agnostic unit result, RULE-2 declared
        # under the tag with no result on it. Since 6.4 every `@on` proof is
        # platform-scoped, so a feature whose only rule waits on a platform
        # reads 0/0; the advisory's "no demotion" claim needs a rule that is
        # proved here to be visible against.
        with open(os.path.join(self.spec_dir, 'locking.md'), 'w') as f:
            f.write('# Feature: locking\n\n'
                    '## Rules\n- RULE-1: Locks on POSIX\n- RULE-2: Locks elsewhere\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): fcntl path locks @unit\n'
                    f'- PROOF-2 (RULE-2): locks on the declared platform {tag}\n')
        with open(os.path.join(self.spec_dir, 'locking.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "locking", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "dev/test_locking.py", "test_name": "test_fcntl",
                 "status": "pass", "tier": "unit"},
            ]}, f)

    def _config(self, platforms=None):
        cfg = {'report': False}
        if platforms is not None:
            cfg['platforms'] = platforms
        with open(os.path.join(self.project_root, '.purlin', 'config.json'), 'w') as f:
            json.dump(cfg, f)

    MIXED = {
        'win-2022': {'os': 'windows', 'version': '>=10.0.20348', 'arch': 'AMD64',
                     'runner': {'provider': 'github', 'runs_on': 'windows-2022'}},
        'windows': {'os': 'windows',
                    'runner': {'provider': 'github', 'workflow': 'purlin-windows-proofs.yml'}},
        'mac-typo': {'os': 'macos', 'vresion': '14'},
        'iphone': {'os': 'ios'},
        'mac-tilde': {'os': 'macos', 'version': '~14'},
        'Bad_Id': {'os': 'linux'},
    }

    @pytest.mark.proof("sync_status", "PROOF-82", "RULE-50", tier="integration")
    def test_registry_keeps_valid_entries_and_names_every_dropped_one(self):
        registry, errors = purlin_server._platform_registry({'platforms': self.MIXED})

        assert sorted(registry) == ['linux', 'macos', 'win-2022', 'windows'], (
            f"the four malformed entries must be dropped and the family ids kept: "
            f"{sorted(registry)}")
        assert registry['windows']['runner']['workflow'] == 'purlin-windows-proofs.yml', (
            "a config entry must replace the built-in of the same id")
        assert registry['windows']['os'] == 'windows'
        assert registry['win-2022']['arch'] == 'x86_64', (
            f"AMD64 must normalise to x86_64: {registry['win-2022']}")
        assert registry['win-2022']['_id'] == 'win-2022'
        assert registry['win-2022']['version'] == '>=10.0.20348'
        for pid in ('linux', 'macos'):
            assert registry[pid] == {'_id': pid, 'os': pid}, registry[pid]

        assert len(errors) == 4, errors
        by_id = {e.split(':', 1)[0]: e for e in errors}
        assert set(by_id) == {'mac-typo', 'iphone', 'mac-tilde', 'Bad_Id'}, errors
        assert 'vresion' in by_id['mac-typo'], (
            f"an unknown key must be named, or the typo vanishes: {by_id['mac-typo']}")
        assert 'not yet supported' in by_id['iphone'], by_id['iphone']
        assert 'version' in by_id['mac-tilde'] and '~14' in by_id['mac-tilde'], by_id['mac-tilde']
        assert 'id' in by_id['Bad_Id'], by_id['Bad_Id']

        # The preamble carries the same four, with the fix.
        self._write_spec('@unit')
        self._config(self.MIXED)
        out = purlin_server.sync_status(self.project_root)
        assert 'Platform registry: 4 entries ignored' in out, out
        for pid in ('mac-typo', 'iphone', 'mac-tilde', 'Bad_Id'):
            assert pid in out, f"the preamble must name the dropped id {pid}:\n{out}"
        assert 'edit "platforms" in .purlin/config.json' in out, out
        head = out.split('locking:', 1)[0]
        assert 'Platform registry' in head, (
            f"the registry block must be in the preamble, before the features:\n{out}")

        # No `platforms` key: no line at all.
        self._config()
        out2 = purlin_server.sync_status(self.project_root)
        assert 'Platform registry' not in out2, out2

    @pytest.mark.proof("sync_status", "PROOF-83", "RULE-50", tier="integration")
    def test_unregistered_platform_id_is_a_feature_advisory_not_a_verdict(self):
        self._write_spec('@unit @on(foo)')
        self._config()
        out = purlin_server.sync_status(self.project_root)
        assert 'WARNING: PROOF-2 names platform "foo"' in out, out
        assert 'not a family id (windows, macos, linux)' in out, out
        assert 'add it under platforms, or use a family id' in out, out
        assert 'locking: PASSING' in out or 'locking: VERIFIED' in out, (
            f"an unregistered id is an advisory, not a demotion:\n{out}")

        # Registering the id silences it.
        self._config({'foo': {'os': 'linux'}})
        out2 = purlin_server.sync_status(self.project_root)
        assert 'names platform "foo"' not in out2, out2

        # A family id needs no registration.
        self._write_spec('@unit @on(macos)')
        self._config()
        out3 = purlin_server.sync_status(self.project_root)
        assert 'names platform' not in out3, out3

    @pytest.mark.proof("sync_status", "PROOF-84", "RULE-51", tier="integration")
    def test_host_detection_and_satisfaction(self, monkeypatch):
        sat = purlin_server._platform_satisfied_by_host

        def host_is(system, mac='', win_build='', release=None, machine='x86_64',
                    raise_release=False):
            monkeypatch.setattr(purlin_server.platform, 'system', lambda: system)
            monkeypatch.setattr(purlin_server.platform, 'mac_ver',
                                lambda: (mac, ('', '', ''), ''))
            monkeypatch.setattr(purlin_server.platform, 'win32_ver',
                                lambda: ('10', win_build, 'SP0', 'Multiprocessor Free'))

            def os_release():
                if raise_release:
                    raise OSError('no os-release')
                return dict(release or {})
            monkeypatch.setattr(purlin_server.platform, 'freedesktop_os_release',
                                os_release, raising=False)
            monkeypatch.setattr(purlin_server.platform, 'machine', lambda: machine)
            return purlin_server._detect_host_platform()

        monkeypatch.delenv('PURLIN_PLATFORM', raising=False)

        # macOS 14.7.1 on Apple silicon.
        host = host_is('Darwin', mac='14.7.1', machine='aarch64')
        assert host == {'os': 'macos', 'version': '14.7.1', 'distro': '',
                        'arch': 'arm64', 'id': None}, host
        assert sat({'_id': 'macos', 'os': 'macos'}, host), "family match"
        assert not sat({'_id': 'linux', 'os': 'linux'}, host), "family mismatch"
        for version in ('14', '14.7', '14.7.1', '>=13', '>=14.7', '>=14.7.1'):
            assert sat({'_id': 'm', 'os': 'macos', 'version': version}, host), version
        for version in ('14.8', '15', '13', '>=14.8', '>=15', '>=14.7.2'):
            assert not sat({'_id': 'm', 'os': 'macos', 'version': version}, host), version
        assert sat({'_id': 'm', 'os': 'macos', 'arch': 'arm64'}, host)
        assert not sat({'_id': 'm', 'os': 'macos', 'arch': 'x86_64'}, host), "arch mismatch"
        # A shorter host version against a longer >= bound pads with zeros.
        assert purlin_server._version_satisfies('>=14.0', '14')
        assert not purlin_server._version_satisfies('>=14.0.1', '14')

        # Ubuntu 24.04.
        host = host_is('Linux', release={'ID': 'ubuntu', 'VERSION_ID': '24.04'})
        assert host['os'] == 'linux' and host['distro'] == 'ubuntu', host
        assert host['version'] == '24.04' and host['arch'] == 'x86_64', host
        assert sat({'_id': 'u', 'os': 'linux', 'distro': 'ubuntu'}, host)
        assert not sat({'_id': 'd', 'os': 'linux', 'distro': 'debian'}, host), "distro mismatch"
        assert sat({'_id': 'u', 'os': 'linux', 'version': '24'}, host)
        assert sat({'_id': 'u', 'os': 'linux', 'version': '>=22.04'}, host)
        assert not sat({'_id': 'u', 'os': 'linux', 'version': '>=24.10'}, host)

        # os-release unreadable: distro and version unknown, family still holds.
        host = host_is('Linux', raise_release=True)
        assert host['distro'] == '' and host['version'] == '', host
        assert sat({'_id': 'linux', 'os': 'linux'}, host)
        assert not sat({'_id': 'u', 'os': 'linux', 'version': '24'}, host), (
            "an unknown host version must not satisfy a version constraint")
        assert not sat({'_id': 'u', 'os': 'linux', 'distro': 'ubuntu'}, host)

        # Windows Server 2022 build.
        host = host_is('Windows', win_build='10.0.20348', machine='AMD64')
        assert host['os'] == 'windows' and host['version'] == '10.0.20348', host
        assert host['arch'] == 'x86_64', host
        assert sat({'_id': 'w', 'os': 'windows', 'version': '>=10.0.20348'}, host)
        assert not sat({'_id': 'w', 'os': 'windows', 'version': '>=10.0.20349'}, host)
        assert sat({'_id': 'w', 'os': 'windows', 'version': '10.0'}, host)

        # PURLIN_PLATFORM claims an id detection cannot prove.
        registry, _ = purlin_server._platform_registry({'platforms': {
            'win-2022': {'os': 'windows', 'version': '>=10.0.20348'}}})
        monkeypatch.setenv('PURLIN_PLATFORM', 'win-2022')
        host = host_is('Darwin', mac='14.7.1', machine='arm64')
        assert host['id'] == 'win-2022', host
        assert sat(registry['win-2022'], host), "the env id short-circuits detection"
        assert purlin_server._host_platform_ids(registry, host) == ['macos', 'win-2022']
        monkeypatch.delenv('PURLIN_PLATFORM')
        host = host_is('Darwin', mac='14.7.1', machine='arm64')
        assert host['id'] is None
        assert not sat(registry['win-2022'], host)
        assert purlin_server._host_platform_ids(registry, host) == ['macos']


class TestPendingMigrationsAdvisory:
    """sync_status RULE-55: everything `purlin:init --update` owns, in one
    advisory with one directive.

    The legacy tier name is assembled rather than written out, for the reason
    dev/test_init_update.py gives: the detector under test scans the repository
    for exactly those literals.
    """

    WIN = 'win' + 'dows'

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin', 'plugins'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'app')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root, ignore_errors=True)

    def _write(self, rel, text):
        path = os.path.join(self.project_root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(text)

    def _build_legacy(self):
        win = self.WIN
        self._write('.purlin/config.json', json.dumps({
            'version': '0.9.0', 'test_framework': 'pytest',
            'spec_dir': 'specs', 'pre_push': 'warn', 'report': False,
            'digest': 'auto'}, indent=2))
        self._write('specs/app/demo.md',
                    '# Feature: demo\n\n'
                    '> Description: Demo.\n\n'
                    '## Rules\n'
                    '- RULE-1: does the thing\n'
                    '- RULE-2: does it on the platform\n\n'
                    '## Proof\n'
                    '- PROOF-1 (RULE-1): assert the thing @unit\n'
                    f'- PROOF-2 (RULE-2): assert it on the platform @{win}\n')
        self._write('specs/app/demo.proofs-unit.json', json.dumps({
            'tier': 'unit', 'proofs': [
                {'feature': 'demo', 'id': 'PROOF-1', 'rule': 'RULE-1',
                 'test_file': 'dev/t_demo.py', 'test_name': 'test_thing',
                 'status': 'pass', 'tier': 'unit'}]}))
        self._write(f'specs/app/demo.proofs-{win}.json', json.dumps({
            'tier': win, 'proofs': [
                {'feature': 'demo', 'id': 'PROOF-2', 'rule': 'RULE-2',
                 'test_file': 'dev/t_demo.py', 'test_name': 'test_platform',
                 'status': 'pass', 'tier': win}]}))
        self._write('tests/t_demo.py',
                    '@pytest.mark.proof("demo", "PROOF-2", "RULE-2", '
                    f'tier="{win}")\ndef test_platform():\n    assert 1\n')
        shutil.copyfile(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'scripts', 'proof', 'pytest_purlin.py'),
            os.path.join(self.project_root, '.purlin', 'plugins',
                         'pytest_purlin.py'))
        with open(os.path.join(self.project_root, '.purlin', 'plugins',
                               'pytest_purlin.py'), 'a') as f:
            f.write('\n# drift\n')
        self._write('specs/app/demo.receipt.json', json.dumps({
            'feature': 'demo', 'vhash': 'deadbeef', 'commit': 'x',
            'timestamp': '2025-01-01T00:00:00+00:00',
            'rules': ['RULE-1', 'RULE-2'], 'proofs': []}, indent=2))

    @pytest.mark.proof("sync_status", "PROOF-89", "RULE-55", tier="integration")
    def test_advisory_names_every_pending_migration_once(self):
        """RULE-55: one line per id with its count and a file, one directive,
        and a version 1 receipt explained as a version 1 receipt."""
        win = self.WIN
        self._build_legacy()
        result = purlin_server.sync_status(self.project_root)
        preamble = result.split('demo:')[0]

        expected = {
            'legacy-tier-windows': 'specs/app/demo.md',
            'legacy-proof-file': f'specs/app/demo.proofs-{win}.json',
            'legacy-marker': 'tests/t_demo.py',
            'plugin-copies-stale': '.purlin/plugins/pytest_purlin.py',
            'config-fields-missing': '.purlin/config.json',
            'receipt-v1': 'specs/app/demo.receipt.json',
        }
        for mid, rel in expected.items():
            lines = [l for l in preamble.splitlines()
                     if l.strip().startswith(f'{mid} (')]
            assert len(lines) == 1, f'{mid}: expected one line, got {lines}'
            assert re.search(rf'{re.escape(mid)} \(\d+\):', lines[0]), lines[0]
            assert rel in preamble, f'{mid}: {rel} is not named in the advisory'
        assert result.count('→ Run: purlin:init --update') == 1, result[:800]

        # The version 1 receipt is explained as such, not as a proof change.
        feature_block = result[result.index('demo:'):]
        assert 'Receipt is version 1' in feature_block, feature_block[:600]
        assert 'the vhash formula changed' in feature_block
        assert 'Proof statuses changed since last verification' not in feature_block

        # Repair all six; the advisory goes away entirely.
        self._write('specs/app/demo.md',
                    '# Feature: demo\n\n'
                    '> Description: Demo.\n\n'
                    '## Rules\n'
                    '- RULE-1: does the thing\n'
                    '- RULE-2: does it on the platform\n\n'
                    '## Proof\n'
                    '- PROOF-1 (RULE-1): assert the thing @unit\n'
                    '- PROOF-2 (RULE-2): assert it on the platform '
                    '@unit @on(windows)\n')
        os.rename(os.path.join(self.spec_dir, f'demo.proofs-{win}.json'),
                  os.path.join(self.spec_dir, 'demo.proofs-unit@windows.json'))
        self._write('tests/t_demo.py',
                    '@pytest.mark.proof("demo", "PROOF-2", "RULE-2", '
                    'tier="unit", platforms=("windows",))\n'
                    'def test_platform():\n    assert 1\n')
        shutil.copyfile(
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'scripts', 'proof', 'pytest_purlin.py'),
            os.path.join(self.project_root, '.purlin', 'plugins',
                         'pytest_purlin.py'))
        config = dict(json.load(open(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'templates', 'config.json'))))
        config['version'] = purlin_server._read_version()
        config['report'] = False
        self._write('.purlin/config.json', json.dumps(config, indent=2))
        receipt = json.load(open(os.path.join(self.spec_dir,
                                              'demo.receipt.json')))
        receipt['vhash_version'] = 2
        self._write('specs/app/demo.receipt.json',
                    json.dumps(receipt, indent=2))

        result = purlin_server.sync_status(self.project_root)
        assert 'Pending migration' not in result, result[:800]
        for mid in expected:
            assert mid not in result, f'{mid} still reported: {result[:800]}'


class TestPlatformsLineAndDetailLines:
    """sync_status RULE-57/58 and the RULE-18/40 marker.

    The per-platform detail used to print an awaiting block, a denominator
    note, a directive and one provenance line per satisfying file. Forty
    features of that is not a report, and nothing said where the project stood
    per platform at all.
    """

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        self.spec_dir = os.path.join(self.project_root, 'specs', 'app')
        os.makedirs(self.spec_dir)

    def teardown_method(self):
        shutil.rmtree(self.project_root, ignore_errors=True)

    def _config(self, platforms=None, **extra):
        cfg = {'report': False, 'remote_verification': 'optional',
               'version': '0.10.0', 'test_framework': 'pytest',
               'spec_dir': 'specs', 'pre_push': 'off', 'mutation_checks': True,
               'digest': 'auto'}
        cfg.update(extra)
        if platforms is not None:
            cfg['platforms'] = platforms
        with open(os.path.join(self.project_root, '.purlin', 'config.json'), 'w') as f:
            json.dump(cfg, f)

    def _spec(self, proofs, rules):
        lines = ['# Feature: locking', '', '## What it does', 'Locks.', '', '## Rules']
        lines += [f'- RULE-{i}: Rule {i}' for i in range(1, rules + 1)]
        lines += ['', '## Proof'] + proofs
        with open(os.path.join(self.spec_dir, 'locking.md'), 'w') as f:
            f.write('\n'.join(lines) + '\n')

    def _entry(self, pid, rule, status='pass'):
        return {'feature': 'locking', 'id': pid, 'rule': rule,
                'test_file': 'dev/test_locking.py', 'test_name': f'test_{pid.lower()}',
                'status': status, 'tier': 'unit'}

    def _proofs(self, entries, platform=None):
        suffix = f'@{platform}' if platform else ''
        data = {'tier': 'unit', 'proofs': entries}
        if platform:
            data['platform'] = platform
            for e in entries:
                e['platform'] = platform
        with open(os.path.join(self.spec_dir,
                               f'locking.proofs-unit{suffix}.json'), 'w') as f:
            json.dump(data, f)

    def _host(self, monkeypatch, os_name='macos', version='14.7.1', arch='arm64'):
        monkeypatch.delenv('PURLIN_PLATFORM', raising=False)
        monkeypatch.setattr(purlin_server, '_detect_host_platform', lambda: {
            'os': os_name, 'version': version, 'distro': '', 'arch': arch,
            'id': None})

    @pytest.mark.proof("sync_status", "PROOF-92", "RULE-57", tier="integration")
    def test_one_platforms_line_with_the_segment_grammar(self, monkeypatch):
        self._host(monkeypatch)
        self._config({'macos-14': {'os': 'macos', 'version': '14'},
                      'windows-2022': {'os': 'windows'}})
        self._spec(['- PROOF-1 (RULE-1): a @unit @on(macos-14)',
                    '- PROOF-2 (RULE-2): b @unit @on(windows-2022)',
                    '- PROOF-3 (RULE-3): c @unit @on(windows-2022)'], rules=3)
        self._proofs([self._entry('PROOF-1', 'RULE-1')], platform='macos-14')

        lines = purlin_server.sync_status(self.project_root).splitlines()
        heads = [i for i, l in enumerate(lines) if l.startswith('Platforms (host: ')]
        assert len(heads) == 1, f"exactly one Platforms line, got {len(heads)}"
        line = lines[heads[0]]
        assert line.startswith('Platforms (host: macos-14): '), line
        mac, _, win = line.partition(' | ')
        assert '(host)' in mac and 'verified' in mac, mac
        assert '(host)' not in win, win
        assert '2 proofs awaiting runner' in win, win
        for zero in ('0 passing', '0 failing', '0 proofs awaiting runner'):
            assert zero not in line, f"a zero clause must be omitted: {line}"
        assert 'proved ' not in win, (
            f"a platform never proved must carry no proved clause: {win}")

        summary = next(i for i, l in enumerate(lines) if 'features VERIFIED' in l)
        mode = next(i for i, l in enumerate(lines)
                    if l.startswith('Remote verification:'))
        assert heads[0] == summary + 1 and heads[0] == mode - 1, (
            f"summary at {summary}, Platforms at {heads[0]}, mode at {mode}")

        # Integrity appears once a grade exists for one of that platform's
        # executed entries, with its measurement coverage beside it.
        cache_dir = os.path.join(self.project_root, '.purlin', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(cache_dir, 'audit_cache.json'), 'w') as f:
            json.dump({'k1': {'feature': 'locking', 'proof_id': 'PROOF-1',
                              'rule_id': 'RULE-1', 'assessment': 'STRONG',
                              'criterion': 'c', 'why': 'w', 'fix': 'f',
                              'priority': 'LOW',
                              'cached_at': '2026-01-01T00:00:00Z'}}, f)
        line = next(l for l in purlin_server.sync_status(self.project_root).splitlines()
                    if l.startswith('Platforms (host: '))
        assert 'Integrity 100% (1 of 1 measured)' in line.partition(' | ')[0], line

        # Nothing declared: no line at all.
        self._spec(['- PROOF-1 (RULE-1): a @unit'], rules=1)
        os.remove(os.path.join(self.spec_dir, 'locking.proofs-unit@macos-14.json'))
        self._proofs([self._entry('PROOF-1', 'RULE-1')])
        out = purlin_server.sync_status(self.project_root)
        assert 'Platforms (host: ' not in out, out

    @pytest.mark.proof("sync_status", "PROOF-93", "RULE-58", tier="integration")
    def test_one_detail_line_per_platform_in_four_forms(self, monkeypatch):
        self._host(monkeypatch)
        self._config({'macos-14': {'os': 'macos', 'version': '14'},
                      'windows-2022': {'os': 'windows'}})
        self._spec(['- PROOF-1 (RULE-1): a @unit @on(macos-14)',
                    '- PROOF-2 (RULE-2): b @unit @on(windows-2022)',
                    '- PROOF-3 (RULE-3): c @unit @on(windows-2022)',
                    '- PROOF-4 (RULE-4): d @unit @on(linux)'], rules=4)
        self._proofs([self._entry('PROOF-1', 'RULE-1')], platform='macos-14')
        self._proofs([self._entry('PROOF-2', 'RULE-2'),
                      self._entry('PROOF-3', 'RULE-3', 'fail')],
                     platform='windows-2022')

        def block(out):
            lines = out.splitlines()
            start = next(i for i, l in enumerate(lines) if l.startswith('locking:'))
            end = next((i for i in range(start + 1, len(lines))
                        if lines[i] == ''), len(lines))
            return lines[start:end]

        got = [l for l in block(purlin_server.sync_status(self.project_root))
               if l[:4] in ('  ✓ ', '  ⚠ ', '  ✗ ')]
        assert got == [
            '  ✓ macos-14 (host): 1/1 proved',
            '  ⚠ linux: awaiting runner, 1 proof (PROOF-4)',
            '  ✗ windows-2022: 1/2 proved, 1 failing (PROOF-3)',
        ], got

        # A passing windows-2022 file turns its line into the remote form.
        self._proofs([self._entry('PROOF-2', 'RULE-2'),
                      self._entry('PROOF-3', 'RULE-3')], platform='windows-2022')
        subprocess.run(['git', 'init', '-q'], cwd=self.project_root, capture_output=True)
        for args in (['config', 'user.email', 't@t.com'], ['config', 'user.name', 'T'],
                     ['add', '-A']):
            subprocess.run(['git'] + args, cwd=self.project_root, capture_output=True)
        subprocess.run(['git', 'commit', '-q', '-m',
                        'test(locking): windows proofs\n\n'
                        'Purlin-Runner: github-actions/windows-2022\n'
                        'Purlin-Platform: windows-2022'],
                       cwd=self.project_root, capture_output=True)
        got = [l for l in block(purlin_server.sync_status(self.project_root))
               if l.startswith('  ✓ windows-2022:')]
        assert len(got) == 1 and 'proved remotely' in got[0] and \
            'github-actions/windows-2022' in got[0] and got[0].startswith(
                '  ✓ windows-2022: 2/2 proved remotely'), got

        # Nothing awaiting: no directive, no platform-partial line.
        self._spec(['- PROOF-1 (RULE-1): a @unit @on(macos-14)',
                    '- PROOF-2 (RULE-2): b @unit @on(windows-2022)',
                    '- PROOF-3 (RULE-3): c @unit @on(windows-2022)'], rules=3)
        payload = purlin_server.read_report_payload(self.project_root)
        vhash = payload['features'][0]['vhash']
        with open(os.path.join(self.spec_dir, 'locking.receipt.json'), 'w') as f:
            json.dump({'feature': 'locking', 'vhash': vhash, 'commit': 'abc1234',
                       'timestamp': '2026-01-01T00:00:00Z', 'vhash_version': 2,
                       'rules': ['RULE-1', 'RULE-2', 'RULE-3']}, f)
        lines = block(purlin_server.sync_status(self.project_root))
        assert not any('purlin:test' in l for l in lines), lines
        assert not any('platform-partial' in l for l in lines), lines

        # Restore the awaiting platform: both lines return.
        self._spec(['- PROOF-1 (RULE-1): a @unit @on(macos-14)',
                    '- PROOF-2 (RULE-2): b @unit @on(windows-2022)',
                    '- PROOF-3 (RULE-3): c @unit @on(windows-2022)',
                    '- PROOF-4 (RULE-4): d @unit @on(linux)'], rules=4)
        payload = purlin_server.read_report_payload(self.project_root)
        with open(os.path.join(self.spec_dir, 'locking.receipt.json'), 'w') as f:
            json.dump({'feature': 'locking', 'vhash': payload['features'][0]['vhash'],
                       'commit': 'abc1234', 'timestamp': '2026-01-01T00:00:00Z',
                       'vhash_version': 2,
                       'rules': ['RULE-1', 'RULE-2', 'RULE-3']}, f)
        lines = block(purlin_server.sync_status(self.project_root))
        assert any('purlin:test' in l for l in lines), lines
        partial = [l for l in lines if 'platform-partial' in l]
        assert len(partial) == 1 and partial[0].endswith('not on linux'), partial

        # A feature declaring nothing prints none of these lines.
        self._spec(['- PROOF-1 (RULE-1): a @unit'], rules=1)
        for stale in ('locking.proofs-unit@macos-14.json',
                      'locking.proofs-unit@windows-2022.json',
                      'locking.receipt.json'):
            os.remove(os.path.join(self.spec_dir, stale))
        self._proofs([self._entry('PROOF-1', 'RULE-1')])
        lines = block(purlin_server.sync_status(self.project_root))
        assert not [l for l in lines if l[:4] in ('  ✓ ', '  ⚠ ', '  ✗ ')], lines

    @pytest.mark.proof("sync_status", "PROOF-94", "RULE-18", tier="integration")
    def test_the_marker_and_its_legend_render_and_vanish(self):
        rows = [('alpha', 2, 2, 'PASSING'), ('beta', 2, 2, 'PASSING'),
                ('gamma', 3, 3, 'VERIFIED'), ('delta', 1, 2, 'PARTIAL'),
                ('epsilon', 0, 0, 'UNTESTED')]
        marked = purlin_server._build_summary_table(
            rows, platform_partial=frozenset({'beta', 'epsilon'}))
        plain = purlin_server._build_summary_table(rows)

        body = [l for l in marked if l.startswith('│')]
        assert any('PASSING*' in l for l in body), body
        assert any('UNTESTED*' in l for l in body), body
        names = [l.split('│')[1].strip() for l in body[1:]]
        assert names.index('beta') < names.index('alpha'), (
            f"a held row must lead its status group: {names}")

        legend = '* proved here, awaiting a declared platform. VERIFIED needs ' \
                 'every declared platform proved and receipted'
        assert marked.count(legend) == 1, marked
        bottom = next(i for i, l in enumerate(marked) if l.startswith('└'))
        assert marked[bottom + 1] == legend, marked[bottom:bottom + 2]

        # Nothing marked: byte-identical to the pre-platform rendering.
        assert not any('*' in l for l in plain if l.startswith('│')), plain
        assert legend not in plain, plain
        marked_box = [l for l in marked if l and l[0] in '┌│├└']
        plain_box = [l for l in plain if l and l[0] in '┌│├└']
        assert len(marked_box) == len(plain_box)

    @pytest.mark.proof("sync_status", "PROOF-95", "RULE-40", tier="integration")
    def test_the_status_column_is_ruled_from_the_tokens_rendered(self):
        rows = [('alpha', 2, 2, 'PASSING'), ('beta', 2, 2, 'PASSING'),
                ('gamma', 3, 3, 'VERIFIED'), ('delta', 1, 2, 'PARTIAL'),
                ('epsilon', 0, 0, 'UNTESTED')]

        def box(lines):
            return [l for l in lines if l and l[0] in '┌│├└']

        # `UNTESTED*` is 9 characters, one wider than any word in the status
        # vocabulary. A column ruled from the vocabulary would push it through
        # the right border, which is exactly how UNTESTED once overflowed.
        marked = box(purlin_server._build_summary_table(
            rows, platform_partial=frozenset({'epsilon'})))
        assert len({len(l) for l in marked}) == 1, (
            f"every rendered line must share a width: "
            f"{sorted({len(l) for l in marked})}")
        for line in [l for l in marked if l.startswith('│')]:
            assert len(line.split('│')[3]) == 11, (
                f"the status cell must be 9 wide plus its two spaces: {line!r}")

        plain = box(purlin_server._build_summary_table(rows))
        assert len({len(l) for l in plain}) == 1, (
            f"{sorted({len(l) for l in plain})}")
        for line in [l for l in plain if l.startswith('│')]:
            assert len(line.split('│')[3]) == 10, (
                f"the status cell must stay 8 wide plus its two spaces: {line!r}")


class TestManualStampsCount:
    """sync_status RULE-5 and RULE-59: a current stamp is coverage, and the
    stamp is bound into the vhash.

    Every case runs against a real git repository, because the whole question
    is what git says changed since the sha the stamp names.
    """

    def setup_method(self):
        self.project_root = os.path.realpath(tempfile.mkdtemp())
        os.makedirs(os.path.join(self.project_root, '.purlin'))
        os.makedirs(os.path.join(self.project_root, 'specs', 'auth'))
        os.makedirs(os.path.join(self.project_root, 'src'))
        self._git('init')
        self._git('config', 'user.email', 'test@test.com')
        self._git('config', 'user.name', 'Test')

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _git(self, *args):
        return subprocess.run(['git'] + list(args), cwd=self.project_root,
                              capture_output=True, text=True, check=True)

    def _commit(self, message):
        self._git('add', '-A')
        self._git('commit', '-m', message)
        return self._git('rev-parse', '--short', 'HEAD').stdout.strip()

    def _write(self, rel, text):
        path = os.path.join(self.project_root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(text)

    def _spec(self, stamp_sha, stamp_date='2026-04-01', scope='> Scope: src/app.py\n'):
        self._write('specs/auth/login.md',
                    '# Feature: login\n\n'
                    f'{scope}\n'
                    '## What it does\nHandles login.\n\n'
                    '## Rules\n'
                    '- RULE-1: Valid credentials return a session token\n'
                    '- RULE-2: The login screen matches the design\n\n'
                    '## Proof\n'
                    '- PROOF-1 (RULE-1): POST valid creds; verify a token comes back\n'
                    '- PROOF-2 (RULE-2): Compare the rendered screen to the design '
                    f'@manual(dev@test.com, {stamp_date}, {stamp_sha})\n')
        self._write('specs/auth/login.proofs-unit.json', json.dumps({
            'tier': 'unit',
            'proofs': [{'feature': 'login', 'id': 'PROOF-1', 'rule': 'RULE-1',
                        'test_file': 'dev/test_login.py',
                        'test_name': 'test_valid_creds', 'status': 'pass',
                        'tier': 'unit'}],
        }, indent=2) + '\n')

    @pytest.mark.proof("sync_status", "PROOF-96", "RULE-5", tier="integration")
    def test_a_current_stamp_counts_and_a_scope_change_takes_it_back(self):
        """One automated pass plus one current stamp is full coverage; a
        committed change to the scope takes the stamp's rule back out."""
        self._write('src/app.py', 'v1\n')
        sha = self._commit('initial')
        self._spec(sha)
        self._commit('stamp PROOF-2 at HEAD')

        current = purlin_server.sync_status(self.project_root)
        assert 'login: PASSING' in current, current
        assert '2/2 rules proved' in current, current
        assert '│ login   │      2/2 │' in current, current
        assert re.search(r'vhash=[0-9a-f]{8}', current), current
        assert 'MANUAL PROOF STALE' not in current, current

        # The scope changes in a commit of its own. The stamp still names the
        # earlier sha, so it no longer says anything about this code.
        self._write('src/app.py', 'v2\n')
        self._commit('change the scope')

        after = purlin_server.sync_status(self.project_root)
        assert 'login: 1/2 rules proved' in after, after
        assert 'login: PASSING' not in after, after
        assert 'MANUAL PROOF STALE' in after, after
        rows = [l for l in after.splitlines() if '│ login' in l]
        assert rows and 'PARTIAL' in rows[0], (rows, after)

    @pytest.mark.proof("sync_status", "PROOF-97", "RULE-59", tier="integration")
    def test_re_stamping_after_a_receipt_stales_that_receipt(self):
        """The stamp is in the vhash, so re-stamping the same rule with a new
        date moves the hash and the receipt issued against the old one is
        stale. Without the M segment the two hashes are equal and a re-stamp
        is invisible."""
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        import issue_receipts

        self._write('src/app.py', 'v1\n')
        sha = self._commit('initial')
        self._spec(sha, stamp_date='2026-04-01')
        self._commit('stamp PROOF-2 at HEAD')

        issued, _ = issue_receipts.main(self.project_root, quiet=True,
                                        run_check=False)
        assert [name for name, _, _ in issued] == ['login'], issued
        first_vhash = issued[0][1]
        self._commit('receipt login')
        verified = purlin_server.sync_status(self.project_root)
        assert 'login: VERIFIED' in verified, verified

        # Same rule, same scope, same sha: only the human and the date change.
        self._spec(sha, stamp_date='2026-04-02')
        self._commit('re-stamp PROOF-2')

        after = purlin_server.sync_status(self.project_root)
        assert 'Receipt stale (vhash mismatch)' in after, after
        assert 'login: VERIFIED' not in after, after
        second = re.search(r'vhash=([0-9a-f]{8})', after)
        assert second and second.group(1) != first_vhash, (first_vhash, after)

    @pytest.mark.proof("sync_status", "PROOF-98", "RULE-5", tier="integration")
    def test_a_stamp_without_scope_is_uncountable(self):
        """No `> Scope:` means nothing to compare the stamp's sha against, so
        the stamp cannot be shown to be out of date and does not count."""
        self._write('src/app.py', 'v1\n')
        sha = self._commit('initial')
        self._spec(sha, scope='')
        self._commit('stamp PROOF-2 with no Scope')

        result = purlin_server.sync_status(self.project_root)
        assert 'login: 1/2 rules proved' in result, result
        assert 'login: PASSING' not in result, result
        assert ('Manual proof without > Scope:' in result
                and 'does not count toward coverage' in result), result


class TestEvidenceOlderThanCode:
    """sync_status RULE-60 and report_data RULE-38: a VERIFIED feature whose
    scope moved since the tests behind its receipt ran says so, and never
    blocks."""

    def setup_method(self):
        self.project_root = os.path.realpath(tempfile.mkdtemp())
        os.makedirs(os.path.join(self.project_root, '.purlin', 'runtime'))
        os.makedirs(os.path.join(self.project_root, 'specs', 'auth'))
        os.makedirs(os.path.join(self.project_root, 'src'))
        with open(os.path.join(self.project_root, '.purlin', 'config.json'), 'w') as f:
            json.dump({'version': '0.9.0', 'test_framework': 'auto',
                       'spec_dir': 'specs', 'report': True}, f)
        self._git('init')
        self._git('config', 'user.email', 'test@test.com')
        self._git('config', 'user.name', 'Test')

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _git(self, *args):
        return subprocess.run(['git'] + list(args), cwd=self.project_root,
                              capture_output=True, text=True, check=True)

    def _commit(self, message):
        self._git('add', '-A')
        self._git('commit', '-m', message)
        return self._git('rev-parse', 'HEAD').stdout.strip()

    def _write(self, rel, text):
        path = os.path.join(self.project_root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(text)

    def _payload(self):
        features = purlin_server._scan_specs(self.project_root)
        all_proofs = purlin_server._read_proofs(self.project_root)
        config = purlin_server.resolve_config(self.project_root)
        data = purlin_server._build_report_data(
            self.project_root, features, all_proofs, config, {}, None)
        return {f['name']: f for f in data['features']}

    def _receipt_at_head(self):
        """Receipt the feature through the real issuer, with a run marker
        naming HEAD so the receipt records a real `evidence.test_run`."""
        sys.path.insert(0, os.path.dirname(__file__))
        import issue_receipts
        self._write('.purlin/runtime/test_run.json', json.dumps({
            'at': '2026-09-12T00:00:00+00:00',
            'commit': self._git('rev-parse', 'HEAD').stdout.strip(),
            'sweep': 'dev/run_tests.sh', 'suites': ['All Pytest Tests'],
            'test_files': ['dev/test_login.py'],
            'passed': 1, 'failed': 0, 'skipped': 0, 'ok': True,
        }))
        issued, skipped = issue_receipts.main(self.project_root, quiet=True)
        assert [n for n, _, _ in issued] == ['login'], (issued, skipped)
        return issued[0][1]

    def _setup_verified_feature(self):
        self._write('src/app.py', 'v1\n')
        self._write('other/notes.md', 'v1\n')
        self._write('specs/auth/login.md',
                    '# Feature: login\n\n'
                    '> Scope: src/app.py\n\n'
                    '## What it does\nHandles login.\n\n'
                    '## Rules\n- RULE-1: Valid credentials return a token\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): POST valid creds; verify a '
                    'token comes back\n')
        self._write('specs/auth/login.proofs-unit.json', json.dumps({
            'tier': 'unit',
            'proofs': [{'feature': 'login', 'id': 'PROOF-1', 'rule': 'RULE-1',
                        'test_file': 'dev/test_login.py',
                        'test_name': 'test_valid_creds', 'status': 'pass',
                        'tier': 'unit'}],
        }, indent=2) + '\n')
        c1 = self._commit('the code, the spec and its proof')
        self._receipt_at_head()
        self._commit('receipt login')
        assert 'login: VERIFIED' in purlin_server.sync_status(self.project_root)
        return c1

    @pytest.mark.proof("sync_status", "PROOF-99", "RULE-60", tier="integration")
    def test_a_commit_to_the_scope_warns_and_one_outside_it_does_not(self):
        c1 = self._setup_verified_feature()

        # A commit inside the scope.
        self._write('src/app.py', 'v2\n')
        self._commit('change the scope')

        out = purlin_server.sync_status(self.project_root)
        warning = [l for l in out.splitlines() if 'EVIDENCE OLDER THAN CODE' in l]
        assert len(warning) == 1, out
        assert '1 commits' in warning[0], warning
        assert c1[:7] in warning[0], (c1[:7], warning)
        assert '→ Run: purlin:test login' in out, out
        # It warns and never blocks: the feature is still VERIFIED.
        assert 'login: VERIFIED' in out, out

    @pytest.mark.proof("report_data", "PROOF-39", "RULE-38", tier="integration")
    def test_the_payload_carries_evidence_stale_both_ways(self):
        self._setup_verified_feature()

        # Nothing has moved yet.
        assert self._payload()['login']['evidence_stale'] is False

        # A commit outside the scope is not evidence that the code moved.
        self._write('other/notes.md', 'v2\n')
        self._commit('change something outside the scope')
        out = purlin_server.sync_status(self.project_root)
        assert 'EVIDENCE OLDER THAN CODE' not in out, out
        assert self._payload()['login']['evidence_stale'] is False

        # A commit inside it is.
        self._write('src/app.py', 'v2\n')
        self._commit('change the scope')
        assert self._payload()['login']['evidence_stale'] is True
