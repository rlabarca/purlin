"""E2E tests for the audit → cache → status → dashboard pipeline.

Tests verify that audit results are written correctly, that sync_status reads
the cache to produce integrity summaries, and that report-data.js reflects
audit state accurately.

Run with: python3 -m pytest dev/test_e2e_audit_cache_pipeline.py -v
"""

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit'))

from purlin_server import (
    sync_status,
    _build_report_data,
    _read_audit_summary,
    _read_audit_cache_by_feature,
    _build_feature_audit,
    _scan_specs,
    _read_proofs,
    _write_report_data,
)
from static_checks import write_audit_cache, read_audit_cache
from config_engine import resolve_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_dir, with_git=True, with_report=False):
    """Create a minimal Purlin project in tmp_dir."""
    purlin_dir = os.path.join(tmp_dir, '.purlin')
    os.makedirs(os.path.join(purlin_dir, 'cache'), exist_ok=True)
    config = {"version": "0.9.0", "test_framework": "auto", "spec_dir": "specs"}
    if with_report:
        config["report"] = True
    with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
        json.dump(config, f)

    # Create a spec with 3 behavioral rules
    spec_dir = os.path.join(tmp_dir, 'specs', 'auth')
    os.makedirs(spec_dir)
    with open(os.path.join(spec_dir, 'login.md'), 'w') as f:
        f.write("""# Feature: login

> Scope: src/auth/login.py

## What it does
Login.

## Rules
- RULE-1: Returns 200 on valid credentials
- RULE-2: Returns 401 on invalid credentials
- RULE-3: Rate limits after 5 failed attempts

## Proof
- PROOF-1 (RULE-1): POST valid creds returns 200
- PROOF-2 (RULE-2): POST bad creds returns 401
- PROOF-3 (RULE-3): Submit 6 bad passwords, verify 429
""")

    # Create proof file with 3 passing proofs
    with open(os.path.join(spec_dir, 'login.proofs-unit.json'), 'w') as f:
        json.dump({"tier": "unit", "proofs": [
            {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test_login.py", "test_name": "test_valid",
             "status": "pass", "tier": "unit"},
            {"feature": "login", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "tests/test_login.py", "test_name": "test_invalid",
             "status": "pass", "tier": "unit"},
            {"feature": "login", "id": "PROOF-3", "rule": "RULE-3",
             "test_file": "tests/test_login.py", "test_name": "test_rate_limit",
             "status": "pass", "tier": "unit"},
        ]}, f)

    if with_git:
        subprocess.run(['git', 'init'], cwd=tmp_dir, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=tmp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                       cwd=tmp_dir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test'],
                       cwd=tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'], cwd=tmp_dir, capture_output=True)


def _make_cache_entries(feature='login', strong=2, weak=1, hollow=0, minutes_ago=5):
    """Create audit cache entries with timestamps."""
    ts = (datetime.datetime.now(datetime.timezone.utc)
          - datetime.timedelta(minutes=minutes_ago)).isoformat()
    cache = {}
    idx = 0
    for _i in range(strong):
        idx += 1
        cache[f'hash_s{idx}'] = {
            'assessment': 'STRONG', 'criterion': 'matches rule intent', 'why': 'good test',
            'fix': 'none', 'feature': feature, 'proof_id': f'PROOF-{idx}',
            'rule_id': f'RULE-{idx}', 'priority': 'LOW', 'cached_at': ts,
        }
    for _i in range(weak):
        idx += 1
        cache[f'hash_w{idx}'] = {
            'assessment': 'WEAK', 'criterion': 'missing negative test', 'why': 'only happy path',
            'fix': 'add error case', 'feature': feature, 'proof_id': f'PROOF-{idx}',
            'rule_id': f'RULE-{idx}', 'priority': 'HIGH', 'cached_at': ts,
        }
    for _i in range(hollow):
        idx += 1
        cache[f'hash_h{idx}'] = {
            'assessment': 'HOLLOW', 'criterion': 'assert True', 'why': 'proves nothing',
            'fix': 'add real assertion', 'feature': feature, 'proof_id': f'PROOF-{idx}',
            'rule_id': f'RULE-{idx}', 'priority': 'CRITICAL', 'cached_at': ts,
        }
    return cache


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAuditCachePipeline:

    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmp_dir)

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-1", "RULE-1", tier="e2e")
    def test_write_cache_creates_file(self):
        """RULE-1: write_audit_cache writes audit_cache.json with entries keyed by proof hash."""
        _make_project(self.tmp_dir, with_git=False)
        cache = _make_cache_entries(strong=2, weak=1)

        write_audit_cache(self.tmp_dir, cache)

        cache_path = os.path.join(self.tmp_dir, '.purlin', 'cache', 'audit_cache.json')
        assert os.path.isfile(cache_path), "audit_cache.json was not created"
        with open(cache_path) as f:
            data = json.load(f)
        assert len(data) == 3, f"Expected 3 cache entries, got {len(data)}"

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-2", "RULE-2", tier="e2e")
    def test_cache_entry_required_fields(self):
        """RULE-2: Each cache entry contains all required fields including valid ISO 8601 cached_at."""
        _make_project(self.tmp_dir, with_git=False)
        cache = _make_cache_entries(strong=1, weak=1, hollow=1)

        write_audit_cache(self.tmp_dir, cache)
        data = read_audit_cache(self.tmp_dir)

        required_fields = {
            'assessment', 'criterion', 'why', 'fix',
            'feature', 'proof_id', 'rule_id', 'priority', 'cached_at',
        }
        for key, entry in data.items():
            missing = required_fields - set(entry.keys())
            assert not missing, f"Entry {key} missing fields: {missing}"
            # Validate cached_at is parseable as ISO 8601
            ts = entry['cached_at']
            parsed = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
            assert parsed is not None, f"cached_at '{ts}' is not valid ISO 8601"

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-3", "RULE-3", tier="e2e")
    def test_sync_status_shows_integrity_line(self):
        """RULE-3: sync_status reads audit cache and shows integrity percentage and relative time."""
        _make_project(self.tmp_dir, with_git=True)
        cache = _make_cache_entries(strong=2, weak=1, minutes_ago=5)
        write_audit_cache(self.tmp_dir, cache)

        output = sync_status(self.tmp_dir)

        # 2 STRONG / 3 behavioral = 66.67 → 67%
        assert 'Integrity: 67%' in output, (
            f"Expected 'Integrity: 67%' in output, got:\n{output}"
        )
        assert 'last purlin:audit:' in output, (
            f"Expected 'last purlin:audit:' in output, got:\n{output}"
        )
        assert 'minutes ago' in output, (
            f"Expected 'minutes ago' in output, got:\n{output}"
        )

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-4", "RULE-4", tier="e2e")
    def test_sync_status_no_cache_shows_no_audit_data(self):
        """RULE-4: sync_status shows 'No audit data' when cache does not exist."""
        _make_project(self.tmp_dir, with_git=True)
        # No cache written — cache file must not exist
        cache_path = os.path.join(self.tmp_dir, '.purlin', 'cache', 'audit_cache.json')
        assert not os.path.exists(cache_path)

        output = sync_status(self.tmp_dir)

        assert 'No audit data' in output, (
            f"Expected 'No audit data' in output, got:\n{output}"
        )
        assert 'purlin:audit' in output, (
            f"Expected 'purlin:audit' in output, got:\n{output}"
        )

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-5", "RULE-5", tier="e2e")
    def test_sync_status_stale_cache_warns(self):
        """RULE-5: sync_status shows 'consider re-auditing' when cache is older than 24 hours."""
        _make_project(self.tmp_dir, with_git=True)
        # 3 days = 4320 minutes
        cache = _make_cache_entries(strong=2, weak=1, minutes_ago=4320)
        write_audit_cache(self.tmp_dir, cache)

        output = sync_status(self.tmp_dir)

        assert 'consider re-auditing' in output, (
            f"Expected 'consider re-auditing' in output, got:\n{output}"
        )

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-6", "RULE-6", tier="e2e")
    def test_report_data_audit_summary_fields(self):
        """RULE-6: report-data.js includes audit_summary with required fields when cache exists."""
        _make_project(self.tmp_dir, with_git=True, with_report=True)
        # Create the HTML file that triggers report-data.js writing
        with open(os.path.join(self.tmp_dir, 'purlin-report.html'), 'w') as f:
            f.write('<html></html>')
        cache = _make_cache_entries(strong=2, weak=1, minutes_ago=5)
        write_audit_cache(self.tmp_dir, cache)

        sync_status(self.tmp_dir)

        report_data_path = os.path.join(self.tmp_dir, '.purlin', 'report-data.js')
        assert os.path.isfile(report_data_path), "report-data.js was not written"
        with open(report_data_path) as f:
            raw = f.read()
        # Strip 'const PURLIN_DATA = ' prefix and trailing ';\n'
        json_str = raw.removeprefix('const PURLIN_DATA = ').removesuffix(';\n')
        data = json.loads(json_str)

        audit_summary = data.get('audit_summary')
        assert audit_summary is not None, "audit_summary should not be null"
        assert audit_summary['integrity'] == 67, (
            f"Expected integrity 67, got {audit_summary['integrity']}"
        )
        assert audit_summary['strong'] == 2, (
            f"Expected strong=2, got {audit_summary['strong']}"
        )
        assert audit_summary['weak'] == 1, (
            f"Expected weak=1, got {audit_summary['weak']}"
        )
        assert audit_summary['stale'] is False, (
            f"Expected stale=False, got {audit_summary['stale']}"
        )
        assert audit_summary['last_audit'] is not None, "last_audit should not be null"

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-7", "RULE-7", tier="e2e")
    def test_report_data_audit_summary_null_when_no_cache(self):
        """RULE-7: report-data.js audit_summary is null when no cache exists."""
        _make_project(self.tmp_dir, with_git=True, with_report=True)
        with open(os.path.join(self.tmp_dir, 'purlin-report.html'), 'w') as f:
            f.write('<html></html>')
        # No cache written

        sync_status(self.tmp_dir)

        report_data_path = os.path.join(self.tmp_dir, '.purlin', 'report-data.js')
        assert os.path.isfile(report_data_path), "report-data.js was not written"
        with open(report_data_path) as f:
            raw = f.read()
        json_str = raw.removeprefix('const PURLIN_DATA = ').removesuffix(';\n')
        data = json.loads(json_str)

        assert data.get('audit_summary') is None, (
            f"Expected audit_summary to be null, got: {data.get('audit_summary')}"
        )

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-8", "RULE-8", tier="e2e")
    def test_report_data_per_feature_audit_data(self):
        """RULE-8: report-data.js per-feature audit data populated from cache with correct integrity."""
        _make_project(self.tmp_dir, with_git=True)
        cache = _make_cache_entries(feature='login', strong=2, weak=1, minutes_ago=5)
        write_audit_cache(self.tmp_dir, cache)

        features = _scan_specs(self.tmp_dir)
        all_proofs = _read_proofs(self.tmp_dir)
        config = resolve_config(self.tmp_dir)
        global_anchors = {k: v for k, v in features.items()
                         if v.get('is_anchor') and v.get('is_global')}
        audit_summary = _read_audit_summary(self.tmp_dir)

        report_data = _build_report_data(
            self.tmp_dir, features, all_proofs, config, global_anchors, audit_summary
        )

        login_feature = next(
            (f for f in report_data['features'] if f['name'] == 'login'), None
        )
        assert login_feature is not None, "login feature not found in report data"
        audit = login_feature.get('audit')
        assert audit is not None, "login feature audit should not be null"
        assert audit['integrity'] == 67, (
            f"Expected login integrity=67, got {audit['integrity']}"
        )
        assert audit['strong'] == 2, f"Expected strong=2, got {audit['strong']}"
        assert audit['weak'] == 1, f"Expected weak=1, got {audit['weak']}"
        findings = audit.get('findings', [])
        assert len(findings) == 1, f"Expected 1 finding (WEAK), got {len(findings)}"
        assert findings[0]['level'] == 'WEAK', (
            f"Expected finding level WEAK, got {findings[0]['level']}"
        )

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-9", "RULE-9", tier="e2e")
    def test_cache_entries_without_feature_excluded_from_per_feature_but_counted_globally(self):
        """RULE-9: Entries missing 'feature' field excluded from per-feature but in project summary."""
        _make_project(self.tmp_dir, with_git=True)

        # One entry with feature, one without
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cache = {
            'hash_with_feature': {
                'assessment': 'STRONG', 'criterion': 'matches rule intent', 'why': 'good test',
                'fix': 'none', 'feature': 'login', 'proof_id': 'PROOF-1', 'rule_id': 'RULE-1',
                'priority': 'LOW', 'cached_at': ts,
            },
            'hash_no_feature': {
                'assessment': 'WEAK', 'criterion': 'missing negative test', 'why': 'only happy path',
                'fix': 'add error case',
                # Intentionally no 'feature' key
                'proof_id': 'PROOF-2', 'rule_id': 'RULE-2',
                'priority': 'HIGH', 'cached_at': ts,
            },
        }
        write_audit_cache(self.tmp_dir, cache)

        # Per-feature grouping should only see the 'login' entry
        by_feature = _read_audit_cache_by_feature(self.tmp_dir)
        assert 'login' in by_feature, "login should appear in per-feature grouping"
        assert len(by_feature['login']) == 1, (
            f"login should have 1 entry, got {len(by_feature['login'])}"
        )

        # Project-wide summary counts all entries (both the STRONG and the WEAK)
        summary = _read_audit_summary(self.tmp_dir)
        assert summary is not None, "audit summary should not be None"
        assert summary['strong'] == 1, f"Expected strong=1 globally, got {summary['strong']}"
        assert summary['weak'] == 1, f"Expected weak=1 globally, got {summary['weak']}"
        assert summary['behavioral_total'] == 2, (
            f"Expected behavioral_total=2 globally, got {summary['behavioral_total']}"
        )

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-10", "RULE-10", tier="e2e")
    def test_deleting_cache_reverts_to_no_audit_state(self):
        """RULE-10: Deleting cache causes sync_status and report-data.js to revert to no-audit state."""
        _make_project(self.tmp_dir, with_git=True, with_report=True)
        with open(os.path.join(self.tmp_dir, 'purlin-report.html'), 'w') as f:
            f.write('<html></html>')
        cache = _make_cache_entries(strong=2, weak=1, minutes_ago=5)
        write_audit_cache(self.tmp_dir, cache)

        # First run — cache present, integrity line should appear
        output_before = sync_status(self.tmp_dir)
        assert 'Integrity:' in output_before, (
            f"Expected 'Integrity:' in first sync_status output, got:\n{output_before}"
        )

        # Delete cache file
        cache_path = os.path.join(self.tmp_dir, '.purlin', 'cache', 'audit_cache.json')
        os.remove(cache_path)

        # Second run — no cache, must show "No audit data"
        output_after = sync_status(self.tmp_dir)
        assert 'No audit data' in output_after, (
            f"Expected 'No audit data' after deleting cache, got:\n{output_after}"
        )

        # report-data.js audit_summary must be null
        report_data_path = os.path.join(self.tmp_dir, '.purlin', 'report-data.js')
        assert os.path.isfile(report_data_path), "report-data.js should still exist"
        with open(report_data_path) as f:
            raw = f.read()
        json_str = raw.removeprefix('const PURLIN_DATA = ').removesuffix(';\n')
        data = json.loads(json_str)
        assert data.get('audit_summary') is None, (
            f"Expected audit_summary null after deleting cache, got: {data.get('audit_summary')}"
        )

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-11", "RULE-11", tier="e2e")
    def test_integrity_penalizes_own_no_proof_rules(self):
        """RULE-11: Own behavioral rules with NO_PROOF inflate the denominator.

        Setup: Feature 'payments' has 5 behavioral rules (RULE-1..5).
        Proofs exist for RULE-1, RULE-2, RULE-3 only. RULE-4 and RULE-5 have NO_PROOF.
        Audit cache: PROOF-1 STRONG, PROOF-2 STRONG, PROOF-3 WEAK.
        Expected: integrity = 2 STRONG / (3 audited + 2 no_proof) = 2/5 = 40%
        """
        _make_project(self.tmp_dir, with_git=True)

        # Overwrite the default login spec with a 5-rule feature
        spec_dir = os.path.join(self.tmp_dir, 'specs', 'billing')
        os.makedirs(spec_dir, exist_ok=True)
        with open(os.path.join(spec_dir, 'payments.md'), 'w') as f:
            f.write("""# Feature: payments

> Scope: src/billing/payments.py

## What it does
Process payments.

## Rules
- RULE-1: Charges the correct amount
- RULE-2: Returns a receipt ID
- RULE-3: Validates card number format
- RULE-4: Sends confirmation email
- RULE-5: Logs transaction to audit trail

## Proof
- PROOF-1 (RULE-1): Charge $10, verify amount
- PROOF-2 (RULE-2): Process payment, verify receipt ID returned
- PROOF-3 (RULE-3): Submit invalid card, verify rejection
- PROOF-4 (RULE-4): Process payment, verify email sent
- PROOF-5 (RULE-5): Process payment, verify audit log entry
""")

        # Only 3 of 5 rules have proofs — RULE-4 and RULE-5 are NO_PROOF
        with open(os.path.join(spec_dir, 'payments.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "payments", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test_pay.py", "test_name": "test_charge",
                 "status": "pass", "tier": "unit"},
                {"feature": "payments", "id": "PROOF-2", "rule": "RULE-2",
                 "test_file": "tests/test_pay.py", "test_name": "test_receipt",
                 "status": "pass", "tier": "unit"},
                {"feature": "payments", "id": "PROOF-3", "rule": "RULE-3",
                 "test_file": "tests/test_pay.py", "test_name": "test_card",
                 "status": "pass", "tier": "unit"},
            ]}, f)

        # Audit cache: 2 STRONG, 1 WEAK for the 3 proofs that exist
        cache = _make_cache_entries(feature='payments', strong=2, weak=1, minutes_ago=5)
        write_audit_cache(self.tmp_dir, cache)

        # Rebuild git index
        subprocess.run(['git', 'add', '.'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'add payments'],
                       cwd=self.tmp_dir, capture_output=True)

        features = _scan_specs(self.tmp_dir)
        all_proofs = _read_proofs(self.tmp_dir)
        config = resolve_config(self.tmp_dir)
        global_anchors = {k: v for k, v in features.items()
                         if v.get('is_anchor') and v.get('is_global')}
        audit_summary = _read_audit_summary(self.tmp_dir)

        report_data = _build_report_data(
            self.tmp_dir, features, all_proofs, config, global_anchors, audit_summary
        )

        payments = next(
            (f for f in report_data['features'] if f['name'] == 'payments'), None
        )
        assert payments is not None, "payments feature not found"
        audit = payments.get('audit')
        assert audit is not None, "payments audit should not be null"

        # 2 STRONG / (2 STRONG + 1 WEAK + 0 HOLLOW + 2 NO_PROOF) = 2/5 = 40%
        assert audit['integrity'] == 40, (
            f"Expected integrity=40% (2 STRONG / 5 denominator), got {audit['integrity']}%\n"
            f"  strong={audit['strong']}, weak={audit['weak']}, hollow={audit['hollow']}"
        )
        assert audit['strong'] == 2
        assert audit['weak'] == 1

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-12", "RULE-12", tier="e2e")
    def test_integrity_excludes_required_anchor_rules_from_no_proof_penalty(self):
        """RULE-12: Required anchor rules don't inflate the NO_PROOF denominator.

        Setup: Feature 'checkout' has 2 own behavioral rules (both proved, both STRONG).
        It requires anchor 'tax_rules' with 3 rules (no proofs under 'checkout').
        Expected: integrity = 2/2 = 100% (anchor rules excluded from NO_PROOF count)
        NOT: 2/5 = 40% (which would happen if anchor rules were in the denominator)
        """
        _make_project(self.tmp_dir, with_git=True)

        # Remove default login spec
        login_spec = os.path.join(self.tmp_dir, 'specs', 'auth', 'login.md')
        login_proof = os.path.join(self.tmp_dir, 'specs', 'auth', 'login.proofs-unit.json')
        if os.path.exists(login_spec):
            os.remove(login_spec)
        if os.path.exists(login_proof):
            os.remove(login_proof)

        # Create anchor with 3 rules
        anchor_dir = os.path.join(self.tmp_dir, 'specs', 'schema')
        os.makedirs(anchor_dir, exist_ok=True)
        with open(os.path.join(anchor_dir, 'tax_rules.md'), 'w') as f:
            f.write("""# Anchor: tax_rules

## What it does
Tax calculation rules.

## Rules
- RULE-1: Calculate state tax
- RULE-2: Calculate federal tax
- RULE-3: Apply exemptions

## Proof
- PROOF-1 (RULE-1): Verify state tax
- PROOF-2 (RULE-2): Verify federal tax
- PROOF-3 (RULE-3): Verify exemptions
""")

        # Create feature requiring the anchor, with 2 own rules
        feat_dir = os.path.join(self.tmp_dir, 'specs', 'cart')
        os.makedirs(feat_dir, exist_ok=True)
        with open(os.path.join(feat_dir, 'checkout.md'), 'w') as f:
            f.write("""# Feature: checkout

> Requires: tax_rules
> Scope: src/cart/checkout.py

## What it does
Checkout flow.

## Rules
- RULE-1: Calculates total with tax
- RULE-2: Creates order record

## Proof
- PROOF-1 (RULE-1): Add items, verify total includes tax
- PROOF-2 (RULE-2): Complete checkout, verify order created
""")

        # Proofs for both own rules
        with open(os.path.join(feat_dir, 'checkout.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "checkout", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test_checkout.py", "test_name": "test_total",
                 "status": "pass", "tier": "unit"},
                {"feature": "checkout", "id": "PROOF-2", "rule": "RULE-2",
                 "test_file": "tests/test_checkout.py", "test_name": "test_order",
                 "status": "pass", "tier": "unit"},
            ]}, f)

        # Audit cache: 2 STRONG for checkout's own proofs
        cache = _make_cache_entries(feature='checkout', strong=2, weak=0, minutes_ago=5)
        write_audit_cache(self.tmp_dir, cache)

        subprocess.run(['git', 'add', '.'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'add checkout + anchor'],
                       cwd=self.tmp_dir, capture_output=True)

        features = _scan_specs(self.tmp_dir)
        all_proofs = _read_proofs(self.tmp_dir)
        config = resolve_config(self.tmp_dir)
        global_anchors = {k: v for k, v in features.items()
                         if v.get('is_anchor') and v.get('is_global')}
        audit_summary = _read_audit_summary(self.tmp_dir)

        report_data = _build_report_data(
            self.tmp_dir, features, all_proofs, config, global_anchors, audit_summary
        )

        checkout = next(
            (f for f in report_data['features'] if f['name'] == 'checkout'), None
        )
        assert checkout is not None, "checkout feature not found"

        # Verify the feature does require the anchor (5 total rules: 2 own + 3 required)
        assert checkout['total'] == 5, (
            f"Expected 5 total rules (2 own + 3 required), got {checkout['total']}"
        )

        audit = checkout.get('audit')
        assert audit is not None, "checkout audit should not be null"

        # Integrity should be 2/2 = 100% (only own rules in denominator)
        # NOT 2/5 = 40% (which would happen if anchor rules inflated it)
        assert audit['integrity'] == 100, (
            f"Expected integrity=100% (2 STRONG / 2 own rules), got {audit['integrity']}%\n"
            f"  strong={audit['strong']}, weak={audit['weak']}, hollow={audit['hollow']}\n"
            f"  If this is 40%, anchor rules are incorrectly inflating the denominator"
        )

    @pytest.mark.proof("e2e_audit_cache_pipeline", "PROOF-13", "RULE-13", tier="e2e")
    def test_global_integrity_includes_no_proof_from_all_features(self):
        """RULE-13: Global integrity sums NO_PROOF penalties across all features.

        Setup: Two features, each with 3 behavioral rules.
        Feature A: 2 STRONG proofs, 1 NO_PROOF rule.
        Feature B: 2 STRONG proofs, 1 NO_PROOF rule.
        Cache: 4 STRONG total.
        Global: 4 STRONG / (4 audited + 2 NO_PROOF) = 4/6 = 67%
        """
        _make_project(self.tmp_dir, with_git=True)

        # Remove default login spec
        login_spec = os.path.join(self.tmp_dir, 'specs', 'auth', 'login.md')
        login_proof = os.path.join(self.tmp_dir, 'specs', 'auth', 'login.proofs-unit.json')
        if os.path.exists(login_spec):
            os.remove(login_spec)
        if os.path.exists(login_proof):
            os.remove(login_proof)

        # Feature A: 3 rules, 2 with proofs
        dir_a = os.path.join(self.tmp_dir, 'specs', 'feat_a')
        os.makedirs(dir_a, exist_ok=True)
        with open(os.path.join(dir_a, 'alpha.md'), 'w') as f:
            f.write("""# Feature: alpha

> Scope: src/alpha.py

## What it does
Alpha feature.

## Rules
- RULE-1: Does A
- RULE-2: Does B
- RULE-3: Does C

## Proof
- PROOF-1 (RULE-1): Test A
- PROOF-2 (RULE-2): Test B
- PROOF-3 (RULE-3): Test C
""")
        with open(os.path.join(dir_a, 'alpha.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "alpha", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test_a.py", "test_name": "test_a1",
                 "status": "pass", "tier": "unit"},
                {"feature": "alpha", "id": "PROOF-2", "rule": "RULE-2",
                 "test_file": "tests/test_a.py", "test_name": "test_a2",
                 "status": "pass", "tier": "unit"},
                # RULE-3 has NO proof — intentionally missing
            ]}, f)

        # Feature B: 3 rules, 2 with proofs
        dir_b = os.path.join(self.tmp_dir, 'specs', 'feat_b')
        os.makedirs(dir_b, exist_ok=True)
        with open(os.path.join(dir_b, 'beta.md'), 'w') as f:
            f.write("""# Feature: beta

> Scope: src/beta.py

## What it does
Beta feature.

## Rules
- RULE-1: Does X
- RULE-2: Does Y
- RULE-3: Does Z

## Proof
- PROOF-1 (RULE-1): Test X
- PROOF-2 (RULE-2): Test Y
- PROOF-3 (RULE-3): Test Z
""")
        with open(os.path.join(dir_b, 'beta.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "beta", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test_b.py", "test_name": "test_b1",
                 "status": "pass", "tier": "unit"},
                {"feature": "beta", "id": "PROOF-2", "rule": "RULE-2",
                 "test_file": "tests/test_b.py", "test_name": "test_b2",
                 "status": "pass", "tier": "unit"},
                # RULE-3 has NO proof — intentionally missing
            ]}, f)

        # Audit cache: 2 STRONG for alpha, 2 STRONG for beta
        ts = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(minutes=5)).isoformat()
        cache = {}
        for feat, idx_start in [('alpha', 1), ('beta', 5)]:
            for i in range(2):
                cache[f'hash_{feat}_{i}'] = {
                    'assessment': 'STRONG', 'criterion': 'matches rule intent',
                    'why': 'test exercises rule correctly', 'fix': 'none',
                    'feature': feat, 'proof_id': f'PROOF-{i+1}',
                    'rule_id': f'RULE-{i+1}', 'priority': 'LOW', 'cached_at': ts,
                }
        write_audit_cache(self.tmp_dir, cache)

        subprocess.run(['git', 'add', '.'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'add alpha + beta'],
                       cwd=self.tmp_dir, capture_output=True)

        output = sync_status(self.tmp_dir)

        # Global: 4 STRONG / (4 audited + 2 NO_PROOF) = 4/6 = 67%
        assert 'Integrity: 67%' in output, (
            f"Expected global 'Integrity: 67%' (4 STRONG / 6 denominator), "
            f"got:\n{output}"
        )
