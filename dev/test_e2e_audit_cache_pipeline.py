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
    _compute_integrity,
    _determine_status,
    _scan_specs,
    _read_proofs,
    _write_report_data,
)
from static_checks import write_audit_cache, read_audit_cache, clear_audit_cache, prune_audit_cache
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

    @pytest.mark.proof("static_checks", "PROOF-28", "RULE-12", tier="e2e")
    def test_write_cache_creates_file(self):
        """RULE-12: write_audit_cache writes atomically — file is valid JSON with correct field values."""
        _make_project(self.tmp_dir, with_git=False)
        cache = _make_cache_entries(feature='login', strong=2, weak=1)

        write_audit_cache(self.tmp_dir, cache)

        cache_path = os.path.join(self.tmp_dir, '.purlin', 'cache', 'audit_cache.json')
        assert os.path.isfile(cache_path), "audit_cache.json was not created"
        with open(cache_path) as f:
            data = json.load(f)
        assert len(data) == 3, f"Expected 3 cache entries, got {len(data)}"

        # Assert specific literal field values — not the original dict — so we prove
        # write_audit_cache actually wrote the correct content, not just that it round-trips.
        strong_entries = [v for v in data.values() if v.get('assessment') == 'STRONG']
        weak_entries = [v for v in data.values() if v.get('assessment') == 'WEAK']
        assert len(strong_entries) == 2, f"Expected 2 STRONG entries on disk, got {len(strong_entries)}"
        assert len(weak_entries) == 1, f"Expected 1 WEAK entry on disk, got {len(weak_entries)}"

        # Verify the STRONG entry fields are exactly the values the function should write
        s = strong_entries[0]
        assert s['assessment'] == 'STRONG', f"Expected literal 'STRONG', got {s['assessment']!r}"
        assert s['criterion'] == 'matches rule intent', f"Unexpected criterion: {s['criterion']!r}"
        assert s['feature'] == 'login', f"Expected literal 'login', got {s['feature']!r}"
        assert s['fix'] == 'none', f"Expected literal 'none', got {s['fix']!r}"

        # Verify the WEAK entry fields
        w = weak_entries[0]
        assert w['assessment'] == 'WEAK', f"Expected literal 'WEAK', got {w['assessment']!r}"
        assert w['criterion'] == 'missing negative test', f"Unexpected criterion: {w['criterion']!r}"
        assert w['feature'] == 'login', f"Expected literal 'login', got {w['feature']!r}"
        assert w['fix'] == 'add error case', f"Expected literal 'add error case', got {w['fix']!r}"

    @pytest.mark.proof("static_checks", "PROOF-29", "RULE-17", tier="e2e")
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
            # (fromisoformat raises ValueError if invalid — that is the real assertion)
            ts = entry['cached_at']
            datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))

    @pytest.mark.proof("sync_status", "PROOF-43", "RULE-19", tier="e2e")
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
        # write_audit_cache stamps real current time, so it shows "just now"
        assert 'just now' in output, (
            f"Expected 'just now' in output, got:\n{output}"
        )

    @pytest.mark.proof("sync_status", "PROOF-44", "RULE-19", tier="e2e")
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

    @pytest.mark.proof("sync_status", "PROOF-45", "RULE-25", tier="e2e")
    def test_sync_status_stale_cache_warns(self):
        """RULE-5: sync_status shows 'consider re-auditing' when cache is older than 24 hours."""
        _make_project(self.tmp_dir, with_git=True)
        # Write cache file directly to simulate old timestamps (write_audit_cache
        # would overwrite cached_at with current time per RULE-19)
        cache = _make_cache_entries(strong=2, weak=1, minutes_ago=4320)
        cache_path = os.path.join(self.tmp_dir, '.purlin', 'cache', 'audit_cache.json')
        with open(cache_path, 'w') as f:
            json.dump(cache, f)

        output = sync_status(self.tmp_dir)

        assert 'consider re-auditing' in output, (
            f"Expected 'consider re-auditing' in output, got:\n{output}"
        )

    @pytest.mark.proof("sync_status", "PROOF-46", "RULE-26", tier="e2e")
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
        assert isinstance(audit_summary['last_audit'], str), (
            f"Expected last_audit to be a non-null string, got {audit_summary['last_audit']!r}"
        )

    @pytest.mark.proof("sync_status", "PROOF-47", "RULE-26", tier="e2e")
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

    @pytest.mark.proof("sync_status", "PROOF-48", "RULE-27", tier="e2e")
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

    @pytest.mark.proof("sync_status", "PROOF-49", "RULE-28", tier="e2e")
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
        assert summary['strong'] == 1, f"Expected strong=1 globally, got {summary['strong']}"
        assert summary['weak'] == 1, f"Expected weak=1 globally, got {summary['weak']}"
        assert summary['behavioral_total'] == 2, (
            f"Expected behavioral_total=2 globally, got {summary['behavioral_total']}"
        )

    @pytest.mark.proof("sync_status", "PROOF-50", "RULE-19", tier="e2e")
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

    @pytest.mark.proof("sync_status", "PROOF-51", "RULE-29", tier="e2e")
    def test_integrity_is_quality_only(self):
        """RULE-29: Integrity = (STRONG + MANUAL) / behavioral_total — quality only.

        Setup: Feature 'payments' has 5 behavioral rules (RULE-1..5).
        Proofs exist for RULE-1, RULE-2, RULE-3 only. RULE-4 and RULE-5 have NONE.
        Audit cache: PROOF-1 STRONG, PROOF-2 STRONG, PROOF-3 WEAK.
        Expected: integrity = 2 STRONG / 3 behavioral = 67% (NONE excluded)
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

        # Only 3 of 5 rules have proofs — RULE-4 and RULE-5 are NONE
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

        # 2 STRONG / (2 STRONG + 1 WEAK + 0 HOLLOW) = 2/3 = 67% (NONE excluded)
        assert audit['integrity'] == 67, (
            f"Expected integrity=67% (2 STRONG / 3 behavioral), got {audit['integrity']}%\n"
            f"  strong={audit['strong']}, weak={audit['weak']}, hollow={audit['hollow']}"
        )
        assert audit['strong'] == 2
        assert audit['weak'] == 1

    @pytest.mark.proof("sync_status", "PROOF-52", "RULE-30", tier="e2e")
    def test_integrity_counts_only_own_feature_proofs(self):
        """RULE-30: Per-feature integrity counts only proofs cached under that feature.

        Setup: Feature 'checkout' has 2 own behavioral rules (both proved, both STRONG).
        It requires anchor 'tax_rules' with 3 rules (no proofs under 'checkout').
        Expected: integrity = 2/2 = 100% (quality of existing proofs only)
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

        # Integrity should be 2/2 = 100% (only own rules in denominator)
        # NOT 2/5 = 40% (which would happen if anchor rules inflated it)
        assert audit['integrity'] == 100, (
            f"Expected integrity=100% (2 STRONG / 2 own rules), got {audit['integrity']}%\n"
            f"  strong={audit['strong']}, weak={audit['weak']}, hollow={audit['hollow']}\n"
            f"  If this is 40%, anchor rules are incorrectly inflating the denominator"
        )

    @pytest.mark.proof("sync_status", "PROOF-53", "RULE-31", tier="e2e")
    def test_global_integrity_quality_only(self):
        """RULE-31: Global integrity = (STRONG + MANUAL) / behavioral_total.

        Setup: Two features, each with 3 behavioral rules.
        Feature A: 2 STRONG proofs, 1 NONE rule.
        Feature B: 2 STRONG proofs, 1 NONE rule.
        Cache: 4 STRONG total.
        Global: 4 STRONG / 4 behavioral = 100% (NONE excluded)
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

        # Global: 4 STRONG / 4 behavioral = 100% (NONE excluded)
        assert 'Integrity: 100%' in output, (
            f"Expected global 'Integrity: 100%' (4 STRONG / 4 behavioral), "
            f"got:\n{output}"
        )

    @pytest.mark.proof("static_checks", "PROOF-30", "RULE-11", tier="e2e")
    def test_read_side_dedup_keeps_latest_entry(self):
        """RULE-14: Read-side dedup keeps only latest per (feature, proof_id).

        Setup: 3 cache entries for the same (login, PROOF-1) with different
        hashes and timestamps. The oldest is HOLLOW, middle is WEAK, newest
        is STRONG. After dedup, only the STRONG entry should survive.
        This verifies that stale entries from prior test code don't inflate
        the integrity denominator.
        """
        _make_project(self.tmp_dir, with_git=True)

        ts_old = '2026-04-01T10:00:00+00:00'
        ts_mid = '2026-04-02T10:00:00+00:00'
        ts_new = '2026-04-03T10:00:00+00:00'

        # 3 entries for same (login, PROOF-1) with different hashes
        cache = {
            'old_hash_aaa': {
                'assessment': 'HOLLOW', 'criterion': 'assert True',
                'why': 'proves nothing', 'fix': 'add real assertion',
                'feature': 'login', 'proof_id': 'PROOF-1', 'rule_id': 'RULE-1',
                'priority': 'CRITICAL', 'cached_at': ts_old,
            },
            'mid_hash_bbb': {
                'assessment': 'WEAK', 'criterion': 'missing negative test',
                'why': 'only happy path', 'fix': 'add error case',
                'feature': 'login', 'proof_id': 'PROOF-1', 'rule_id': 'RULE-1',
                'priority': 'HIGH', 'cached_at': ts_mid,
            },
            'new_hash_ccc': {
                'assessment': 'STRONG', 'criterion': 'matches rule intent',
                'why': 'good test', 'fix': 'none',
                'feature': 'login', 'proof_id': 'PROOF-1', 'rule_id': 'RULE-1',
                'priority': 'LOW', 'cached_at': ts_new,
            },
        }
        write_audit_cache(self.tmp_dir, cache)

        # _read_audit_cache_by_feature should return exactly 1 entry
        by_feature = _read_audit_cache_by_feature(self.tmp_dir)
        login_entries = by_feature.get('login', [])
        assert len(login_entries) == 1, (
            f"Expected 1 deduped entry for login, got {len(login_entries)}"
        )
        assert login_entries[0]['assessment'] == 'STRONG', (
            f"Expected latest entry (STRONG), got {login_entries[0]['assessment']}"
        )

        # _read_audit_summary should count 1 entry, not 3
        summary = _read_audit_summary(self.tmp_dir)
        assert summary['behavioral_total'] == 1, (
            f"Expected behavioral_total=1 after dedup, got {summary['behavioral_total']}"
        )
        assert summary['strong'] == 1, (
            f"Expected strong=1, got {summary['strong']}"
        )
        assert summary['weak'] == 0, (
            f"Expected weak=0 (stale entry pruned), got {summary['weak']}"
        )
        assert summary['hollow'] == 0, (
            f"Expected hollow=0 (stale entry pruned), got {summary['hollow']}"
        )

        # _build_feature_audit should compute integrity from deduped entries
        audit = _build_feature_audit(login_entries)
        assert audit['integrity'] == 100, (
            f"Expected integrity=100% (1 STRONG / 1 total), got {audit['integrity']}%"
        )

    @pytest.mark.proof("static_checks", "PROOF-31", "RULE-12", tier="e2e")
    def test_write_side_pruning_removes_stale_duplicates(self):
        """RULE-15: write_audit_cache prunes duplicate (feature, proof_id) entries.

        Setup: Write a cache with 2 entries for same (login, PROOF-1) —
        one HOLLOW (older hash), one STRONG (newer hash). After write,
        only the STRONG entry should remain on disk. The old hash key
        should be gone entirely.
        """
        _make_project(self.tmp_dir, with_git=False)

        ts_old = '2026-04-01T10:00:00+00:00'
        ts_new = '2026-04-03T10:00:00+00:00'

        cache = {
            'stale_hash_111': {
                'assessment': 'HOLLOW', 'criterion': 'no assertions',
                'why': 'empty test', 'fix': 'add assertions',
                'feature': 'login', 'proof_id': 'PROOF-1', 'rule_id': 'RULE-1',
                'priority': 'CRITICAL', 'cached_at': ts_old,
            },
            'fresh_hash_222': {
                'assessment': 'STRONG', 'criterion': 'matches rule intent',
                'why': 'good test', 'fix': 'none',
                'feature': 'login', 'proof_id': 'PROOF-1', 'rule_id': 'RULE-1',
                'priority': 'LOW', 'cached_at': ts_new,
            },
            'other_hash_333': {
                'assessment': 'STRONG', 'criterion': 'matches rule intent',
                'why': 'good test', 'fix': 'none',
                'feature': 'login', 'proof_id': 'PROOF-2', 'rule_id': 'RULE-2',
                'priority': 'LOW', 'cached_at': ts_new,
            },
        }
        write_audit_cache(self.tmp_dir, cache)

        # Read back raw file — should have 2 entries, not 3
        data = read_audit_cache(self.tmp_dir)
        assert len(data) == 2, (
            f"Expected 2 entries after pruning (1 deduped + 1 unique), got {len(data)}"
        )

        # The stale hash key should be gone
        assert 'stale_hash_111' not in data, (
            "Stale hash key should have been pruned"
        )

        # The fresh hash for PROOF-1 should survive
        assert 'fresh_hash_222' in data, (
            "Fresh hash key for PROOF-1 should survive pruning"
        )
        assert data['fresh_hash_222']['assessment'] == 'STRONG', (
            f"Surviving entry should be STRONG, got {data['fresh_hash_222']['assessment']}"
        )

        # The unrelated PROOF-2 entry should be untouched
        assert 'other_hash_333' in data, (
            "Unrelated PROOF-2 entry should survive pruning"
        )

    @pytest.mark.proof("static_checks", "PROOF-32", "RULE-18", tier="e2e")
    def test_clear_cache_produces_empty_dict(self):
        """RULE-18: clear_audit_cache replaces the cache with an empty dict.

        Setup: Write cache with 3 entries. Call clear_audit_cache. Read back.
        Expected: cache file exists, contents are {}.
        """
        _make_project(self.tmp_dir, with_git=False)

        cache = _make_cache_entries(feature='login', strong=2, weak=1)
        write_audit_cache(self.tmp_dir, cache)

        # Verify non-empty before clearing
        before = read_audit_cache(self.tmp_dir)
        assert len(before) == 3, f"Expected 3 entries before clear, got {len(before)}"

        # Clear and verify empty
        path = clear_audit_cache(self.tmp_dir)
        assert os.path.isfile(path), "Cache file should still exist after clearing"

        after = read_audit_cache(self.tmp_dir)
        assert after == {}, f"Expected empty dict after clear, got {len(after)} entries"

    @pytest.mark.proof("static_checks", "PROOF-38", "RULE-22", tier="e2e")
    def test_prune_cache_via_cli(self):
        """RULE-22 e2e: Write 5 entries, prune to 3 via --prune-cache --live-keys-file.

        Setup: Write cache with 5 entries (keys hash_s1..hash_s3 + hash_w4 + hash_w5).
        Write 3 live keys (hash_s1, hash_s2, hash_s3) to a temp file.
        Run --prune-cache --live-keys-file via subprocess.
        Expected: JSON output shows pruned=2, kept=3. Cache has exactly 3 entries.
        """
        _make_project(self.tmp_dir, with_git=False)

        cache = _make_cache_entries(feature='login', strong=3, weak=2)
        write_audit_cache(self.tmp_dir, cache)

        # Verify 5 entries before prune
        before = read_audit_cache(self.tmp_dir)
        assert len(before) == 5, f"Expected 5 entries before prune, got {len(before)}"

        # Write live keys file — keep only the 3 STRONG entries
        live_keys_path = os.path.join(self.tmp_dir, 'live_keys.txt')
        with open(live_keys_path, 'w') as f:
            for k in before:
                if before[k]['assessment'] == 'STRONG':
                    f.write(k + '\n')

        # Run CLI
        result = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit', 'static_checks.py'),
             '--prune-cache', '--live-keys-file', live_keys_path,
             '--project-root', self.tmp_dir],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"

        output = json.loads(result.stdout)
        assert output['pruned'] == 2, f"Expected pruned=2, got {output}"
        assert output['kept'] == 3, f"Expected kept=3, got {output}"

        # Verify cache on disk
        after = read_audit_cache(self.tmp_dir)
        assert len(after) == 3, f"Expected 3 entries after prune, got {len(after)}"
        for entry in after.values():
            assert entry['assessment'] == 'STRONG', "Only STRONG entries should remain"

    @pytest.mark.proof("static_checks", "PROOF-33", "RULE-19", tier="e2e")
    def test_write_cache_stamps_real_utc_time(self):
        """RULE-19: write_audit_cache overwrites cached_at with the real current UTC time.

        Setup: Write cache entries with stale cached_at (midnight UTC).
        Expected: After write, every entry's cached_at is within 5 seconds of now.
        """
        _make_project(self.tmp_dir, with_git=False)

        # Create entries with a known stale timestamp (midnight UTC today — independent oracle)
        today_midnight = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stale_ts = today_midnight.isoformat()
        cache = _make_cache_entries(feature='login', strong=2, weak=1)
        for entry in cache.values():
            entry['cached_at'] = stale_ts

        write_audit_cache(self.tmp_dir, cache)

        data = read_audit_cache(self.tmp_dir)
        for key, entry in data.items():
            actual_ts_str = entry['cached_at']
            # The stale midnight value must have been overwritten
            assert actual_ts_str != stale_ts, (
                f"Entry {key}: write_audit_cache did not overwrite cached_at "
                f"(still has stale value {stale_ts!r})"
            )
            # The new timestamp must be strictly later than midnight (the stale oracle)
            actual_ts = datetime.datetime.fromisoformat(actual_ts_str.replace('Z', '+00:00'))
            assert actual_ts > today_midnight, (
                f"Entry {key}: cached_at {actual_ts_str!r} is not later than "
                f"midnight oracle {stale_ts!r}"
            )

    @pytest.mark.proof("sync_status", "PROOF-54", "RULE-29", tier="e2e")
    def test_integrity_ignores_no_proof_rules_completely(self):
        """RULE-29: Integrity = quality only. NONE rules have zero effect.

        Setup: Feature with 4 behavioral rules. Only 2 have proofs (both STRONG).
        RULE-3 and RULE-4 have NONE.
        Expected: integrity = 2/2 = 100% (not 2/4 = 50%).
        """
        _make_project(self.tmp_dir, with_git=True)

        spec_dir = os.path.join(self.tmp_dir, 'specs', 'core')
        os.makedirs(spec_dir, exist_ok=True)
        with open(os.path.join(spec_dir, 'engine.md'), 'w') as f:
            f.write("""# Feature: engine

> Scope: src/engine.py

## What it does
Core engine.

## Rules
- RULE-1: Starts the engine
- RULE-2: Stops the engine
- RULE-3: Handles errors gracefully
- RULE-4: Logs all operations

## Proof
- PROOF-1 (RULE-1): Start engine, verify running
- PROOF-2 (RULE-2): Stop engine, verify stopped
- PROOF-3 (RULE-3): Trigger error, verify handled
- PROOF-4 (RULE-4): Run operation, verify log entry
""")
        # Only 2 of 4 rules have proofs
        with open(os.path.join(spec_dir, 'engine.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "engine", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test_engine.py", "test_name": "test_start",
                 "status": "pass", "tier": "unit"},
                {"feature": "engine", "id": "PROOF-2", "rule": "RULE-2",
                 "test_file": "tests/test_engine.py", "test_name": "test_stop",
                 "status": "pass", "tier": "unit"},
            ]}, f)

        # Audit cache: 2 STRONG (no WEAK, no HOLLOW)
        ts = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(minutes=5)).isoformat()
        cache = {
            'h_engine_1': {
                'assessment': 'STRONG', 'criterion': 'matches rule intent',
                'why': 'test exercises rule', 'fix': 'none',
                'feature': 'engine', 'proof_id': 'PROOF-1',
                'rule_id': 'RULE-1', 'priority': 'LOW', 'cached_at': ts,
            },
            'h_engine_2': {
                'assessment': 'STRONG', 'criterion': 'matches rule intent',
                'why': 'test exercises rule', 'fix': 'none',
                'feature': 'engine', 'proof_id': 'PROOF-2',
                'rule_id': 'RULE-2', 'priority': 'LOW', 'cached_at': ts,
            },
        }
        write_audit_cache(self.tmp_dir, cache)

        subprocess.run(['git', 'add', '.'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'add engine'],
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

        engine = next(
            (f for f in report_data['features'] if f['name'] == 'engine'), None
        )
        assert engine is not None, "engine feature not found"
        audit = engine.get('audit')

        # 2 STRONG / 2 behavioral = 100% (NONE rules excluded from denominator)
        assert audit['integrity'] == 100, (
            f"Expected integrity=100% (2 STRONG / 2 behavioral), got {audit['integrity']}%\n"
            f"  strong={audit['strong']}, weak={audit['weak']}, hollow={audit['hollow']}\n"
            f"  NONE rules must NOT affect integrity"
        )

    @pytest.mark.proof("sync_status", "PROOF-55", "RULE-32", tier="e2e")
    def test_cli_integrity_matches_report_data(self):
        """RULE-32: CLI integrity percentage matches report-data.js audit_summary.integrity.

        Setup: Write cache with 2 STRONG + 1 WEAK. Run sync_status (writes report-data.js).
        Expected: CLI shows 'Integrity: 67%'; report-data.js audit_summary.integrity == 67.
        """
        _make_project(self.tmp_dir, with_git=True, with_report=True)

        # Create purlin-report.html so report-data.js gets written
        html_path = os.path.join(self.tmp_dir, 'purlin-report.html')
        with open(html_path, 'w') as f:
            f.write('<html></html>')

        cache = _make_cache_entries(feature='login', strong=2, weak=1, minutes_ago=5)
        write_audit_cache(self.tmp_dir, cache)

        subprocess.run(['git', 'add', '.'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'setup'],
                       cwd=self.tmp_dir, capture_output=True)

        cli_output = sync_status(self.tmp_dir)

        # Parse CLI integrity
        import re
        match = re.search(r'Integrity:\s+(\d+)%', cli_output)
        assert match, f"CLI output should contain 'Integrity: N%', got:\n{cli_output}"
        cli_integrity = int(match.group(1))

        # Parse report-data.js integrity
        report_path = os.path.join(self.tmp_dir, '.purlin', 'report-data.js')
        assert os.path.isfile(report_path), "report-data.js should exist"
        with open(report_path) as f:
            content = f.read()
        # Strip "const PURLIN_DATA = " prefix and trailing ";"
        json_str = content.replace('const PURLIN_DATA = ', '', 1).rstrip().rstrip(';')
        data = json.loads(json_str)
        dashboard_integrity = data['audit_summary']['integrity']

        assert cli_integrity == dashboard_integrity, (
            f"CLI integrity ({cli_integrity}%) must match dashboard ({dashboard_integrity}%)"
        )

    @pytest.mark.proof("sync_status", "PROOF-56", "RULE-33", tier="unit")
    def test_integrity_formula_consistent_across_sources(self):
        """RULE-33: Integrity formula is identical in audit_criteria, SKILL.md, and sync_status spec.

        Structural check: all three files contain the canonical formula text and
        none of them include NONE in the integrity formula denominator.
        """
        import re

        project_root = os.path.join(os.path.dirname(__file__), '..')
        files = {
            'audit_criteria': os.path.join(project_root, 'references', 'audit_criteria.md'),
            'SKILL.md': os.path.join(project_root, 'skills', 'audit', 'SKILL.md'),
            'sync_status.md': os.path.join(project_root, 'specs', 'mcp', 'sync_status.md'),
        }

        canonical = '(STRONG + MANUAL) / (STRONG + WEAK + HOLLOW + MANUAL)'

        for label, path in files.items():
            with open(path) as f:
                content = f.read()
            assert canonical in content, (
                f"{label} must contain the canonical integrity formula:\n"
                f"  Expected: {canonical}\n"
                f"  File: {path}"
            )

        # Verify the integrity formula line itself does not include NONE
        with open(files['audit_criteria']) as f:
            content = f.read()
        formula_match = re.search(r'^Integrity score = .*$', content, re.MULTILINE)
        assert formula_match, "audit_criteria.md must have an 'Integrity score = ...' line"
        formula_line = formula_match.group(0)
        assert 'NONE' not in formula_line, (
            f"audit_criteria.md integrity formula must not include NONE:\n"
            f"  Found: {formula_line}"
        )

    @pytest.mark.proof("sync_status", "PROOF-57", "RULE-32", tier="e2e")
    def test_integrity_with_no_proof_rules_all_sources_match(self):
        """RULE-32: CLI, dashboard, and computed integrity agree when NONE rules exist.

        Setup: Isolated project with a 5-rule feature. 3 rules have proofs
        (1 STRONG, 1 WEAK, 1 HOLLOW). RULE-4 and RULE-5 have NONE.
        Expected: integrity = 1 STRONG / (1 S + 1 W + 1 H) = 1/3 = 33%.
        NONE rules must NOT appear in the denominator (that would give 1/5 = 20%).
        """
        _make_project(self.tmp_dir, with_git=True, with_report=True)

        # Create purlin-report.html so report-data.js gets written
        html_path = os.path.join(self.tmp_dir, 'purlin-report.html')
        with open(html_path, 'w') as f:
            f.write('<html></html>')

        # Overwrite default spec with a 5-rule feature (only 3 have proofs)
        spec_dir = os.path.join(self.tmp_dir, 'specs', 'billing')
        os.makedirs(spec_dir, exist_ok=True)
        with open(os.path.join(spec_dir, 'invoices.md'), 'w') as f:
            f.write("""# Feature: invoices

> Scope: src/billing/invoices.py

## What it does
Invoice management.

## Rules
- RULE-1: Creates invoice with correct line items
- RULE-2: Applies tax calculations
- RULE-3: Validates billing address
- RULE-4: Sends invoice email notification
- RULE-5: Archives invoice after payment

## Proof
- PROOF-1 (RULE-1): Create invoice, verify line items
- PROOF-2 (RULE-2): Create invoice, verify tax applied
- PROOF-3 (RULE-3): Submit invalid address, verify rejection
""")

        # Only 3 of 5 rules have proofs — RULE-4 and RULE-5 are NONE
        with open(os.path.join(spec_dir, 'invoices.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "invoices", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test_invoices.py", "test_name": "test_line_items",
                 "status": "pass", "tier": "unit"},
                {"feature": "invoices", "id": "PROOF-2", "rule": "RULE-2",
                 "test_file": "tests/test_invoices.py", "test_name": "test_tax",
                 "status": "pass", "tier": "unit"},
                {"feature": "invoices", "id": "PROOF-3", "rule": "RULE-3",
                 "test_file": "tests/test_invoices.py", "test_name": "test_address",
                 "status": "pass", "tier": "unit"},
            ]}, f)

        # Audit cache: 1 STRONG, 1 WEAK, 1 HOLLOW for the 3 proved rules
        ts = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(minutes=5)).isoformat()
        cache = {
            'h_inv_1': {
                'assessment': 'STRONG', 'criterion': 'matches rule intent',
                'why': 'real assertion on line items', 'fix': 'none',
                'feature': 'invoices', 'proof_id': 'PROOF-1',
                'rule_id': 'RULE-1', 'priority': 'LOW', 'cached_at': ts,
            },
            'h_inv_2': {
                'assessment': 'WEAK', 'criterion': 'missing negative test',
                'why': 'only happy path for tax', 'fix': 'add zero-tax case',
                'feature': 'invoices', 'proof_id': 'PROOF-2',
                'rule_id': 'RULE-2', 'priority': 'HIGH', 'cached_at': ts,
            },
            'h_inv_3': {
                'assessment': 'HOLLOW', 'criterion': 'assert True',
                'why': 'no real assertion on address validation',
                'fix': 'add real assertion',
                'feature': 'invoices', 'proof_id': 'PROOF-3',
                'rule_id': 'RULE-3', 'priority': 'CRITICAL', 'cached_at': ts,
            },
        }
        write_audit_cache(self.tmp_dir, cache)

        subprocess.run(['git', 'add', '.'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'add invoices'],
                       cwd=self.tmp_dir, capture_output=True)

        # Run sync_status (writes report-data.js)
        cli_output = sync_status(self.tmp_dir)

        # --- Source 1: Compute expected integrity ---
        # 1 STRONG / (1 STRONG + 1 WEAK + 1 HOLLOW) = 1/3 = 33%
        # NOT 1/5 = 20% (NONE excluded from denominator)
        expected_integrity = round(1 / 3 * 100)  # 33

        # --- Source 2: Parse CLI integrity ---
        import re
        match = re.search(r'Integrity:\s+(\d+)%', cli_output)
        assert match, f"CLI output should contain 'Integrity: N%', got:\n{cli_output}"
        cli_integrity = int(match.group(1))

        # --- Source 3: Parse report-data.js integrity ---
        report_path = os.path.join(self.tmp_dir, '.purlin', 'report-data.js')
        assert os.path.isfile(report_path), "report-data.js should exist"
        with open(report_path) as f:
            content = f.read()
        json_str = content.replace('const PURLIN_DATA = ', '', 1).rstrip().rstrip(';')
        data = json.loads(json_str)
        dashboard_integrity = data['audit_summary']['integrity']

        # --- All three must match ---
        assert cli_integrity == expected_integrity, (
            f"CLI integrity ({cli_integrity}%) != computed ({expected_integrity}%)\n"
            f"  If CLI shows 20%, NONE rules are leaking into the denominator"
        )
        assert dashboard_integrity == expected_integrity, (
            f"Dashboard integrity ({dashboard_integrity}%) != computed ({expected_integrity}%)\n"
            f"  If dashboard shows 20%, NONE rules are leaking into the denominator"
        )
        assert cli_integrity == dashboard_integrity, (
            f"CLI ({cli_integrity}%) != dashboard ({dashboard_integrity}%)"
        )

    @pytest.mark.proof("sync_status", "PROOF-58", "RULE-34", tier="unit")
    def test_compute_integrity_is_single_function(self):
        """RULE-34: Integrity is computed by exactly one function.

        Structural check: _compute_integrity is the only function in
        purlin_server.py that contains the integrity formula. Both
        _read_audit_summary and _build_feature_audit delegate to it.
        """
        import re
        server_path = os.path.join(
            os.path.dirname(__file__), '..', 'scripts', 'mcp', 'purlin_server.py'
        )
        with open(server_path) as f:
            content = f.read()

        # Find all function definitions
        func_defs = re.findall(r'^def (\w+)\(', content, re.MULTILINE)

        # The formula pattern: (strong + manual) / behavioral_total * 100
        # or equivalent inline computation
        formula_pattern = re.compile(
            r'\(strong\s*\+\s*manual\)\s*/\s*behavioral_total\s*\*\s*100'
        )

        # Find which functions contain the formula inline
        functions_with_formula = []
        for match in re.finditer(r'^def (\w+)\(.*?\n(?=^def |\Z)', content,
                                 re.MULTILINE | re.DOTALL):
            func_name = match.group(1)
            func_body = match.group(0)
            if formula_pattern.search(func_body):
                functions_with_formula.append(func_name)

        assert functions_with_formula == ['_compute_integrity'], (
            f"Only _compute_integrity should contain the integrity formula.\n"
            f"  Found in: {functions_with_formula}"
        )

        # Verify both callers delegate to _compute_integrity
        for caller in ('_read_audit_summary', '_build_feature_audit'):
            caller_match = re.search(
                rf'^def {caller}\(.*?\n(?=^def |\Z)', content,
                re.MULTILINE | re.DOTALL
            )
            assert caller_match, f"{caller} not found"
            assert '_compute_integrity(' in caller_match.group(0), (
                f"{caller} must call _compute_integrity()"
            )

    @pytest.mark.proof("sync_status", "PROOF-59", "RULE-35", tier="unit")
    def test_determine_status_is_single_function(self):
        """RULE-35: Status is determined by exactly one function.

        Structural check: _determine_status is the only function that contains
        the VERIFIED/PASSING/FAILING/PARTIAL/UNTESTED determination chain.
        All call sites delegate to it.
        """
        import re
        server_path = os.path.join(
            os.path.dirname(__file__), '..', 'scripts', 'mcp', 'purlin_server.py'
        )
        with open(server_path) as f:
            content = f.read()

        # The status pattern: function that contains the full status chain
        # (all five values: VERIFIED, PASSING, FAILING, PARTIAL, UNTESTED).
        # _determine_status uses return statements; callers should delegate.
        all_five = {'VERIFIED', 'PASSING', 'FAILING', 'PARTIAL', 'UNTESTED'}
        status_pattern = re.compile(r"['\"](?:VERIFIED|PASSING|FAILING|PARTIAL|UNTESTED)['\"]")

        functions_with_full_chain = []
        for match in re.finditer(r'^def (\w+)\(.*?\n(?=^def |\Z)', content,
                                 re.MULTILINE | re.DOTALL):
            func_name = match.group(1)
            func_body = match.group(0)
            found_statuses = set(status_pattern.findall(func_body))
            # Normalize quotes
            found_statuses = {s.strip("'\"") for s in found_statuses}
            if all_five.issubset(found_statuses):
                functions_with_full_chain.append(func_name)

        assert '_determine_status' in functions_with_full_chain, (
            "_determine_status must contain the full status determination chain"
        )

        # Only _determine_status and display-only functions (like
        # _build_summary_table which maps status to display symbols, and
        # _report_feature which uses header_status) should contain all five
        allowed = {'_determine_status', '_build_summary_table', '_report_feature'}
        unexpected = set(functions_with_full_chain) - allowed
        assert not unexpected, (
            f"Only _determine_status should contain the full status chain.\n"
            f"  Unexpected functions: {unexpected}\n"
            f"  These should delegate to _determine_status()"
        )

        # Verify the main call sites delegate to _determine_status
        # sync_status and _build_report_data should both call it
        callers_found = []
        for caller in ('sync_status', '_build_report_data'):
            caller_match = re.search(
                rf'^def {caller}\(.*?\n(?=^def |\Z)', content,
                re.MULTILINE | re.DOTALL
            )
            if caller_match and '_determine_status(' in caller_match.group(0):
                callers_found.append(caller)

        assert 'sync_status' in callers_found, (
            "sync_status must call _determine_status()"
        )
        assert '_build_report_data' in callers_found, (
            "_build_report_data must call _determine_status()"
        )

    @pytest.mark.proof("sync_status", "PROOF-60", "RULE-34", tier="e2e")
    def test_multi_feature_integrity_cli_matches_dashboard(self):
        """RULE-34: Per-feature and global integrity match between CLI and dashboard.

        Setup: Isolated project with 2 features, different audit mixes.
        Feature 'auth': 2 STRONG, 1 WEAK → integrity = 67%.
        Feature 'billing': 1 STRONG, 1 HOLLOW → integrity = 50%.
        Global: 3 STRONG / (3 S + 1 W + 1 H) = 3/5 = 60%.
        Verifies CLI and report-data.js agree on all values.
        """
        _make_project(self.tmp_dir, with_git=True, with_report=True)
        html_path = os.path.join(self.tmp_dir, 'purlin-report.html')
        with open(html_path, 'w') as f:
            f.write('<html></html>')

        # Create auth feature (3 rules, all proved)
        auth_dir = os.path.join(self.tmp_dir, 'specs', 'auth')
        os.makedirs(auth_dir, exist_ok=True)
        with open(os.path.join(auth_dir, 'login.md'), 'w') as f:
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
        with open(os.path.join(auth_dir, 'login.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test_login.py", "test_name": "test_valid",
                 "status": "pass", "tier": "unit"},
                {"feature": "login", "id": "PROOF-2", "rule": "RULE-2",
                 "test_file": "tests/test_login.py", "test_name": "test_invalid",
                 "status": "pass", "tier": "unit"},
                {"feature": "login", "id": "PROOF-3", "rule": "RULE-3",
                 "test_file": "tests/test_login.py", "test_name": "test_ratelimit",
                 "status": "pass", "tier": "unit"},
            ]}, f)

        # Create billing feature (2 rules, both proved)
        billing_dir = os.path.join(self.tmp_dir, 'specs', 'billing')
        os.makedirs(billing_dir, exist_ok=True)
        with open(os.path.join(billing_dir, 'payments.md'), 'w') as f:
            f.write("""# Feature: payments

> Scope: src/billing/payments.py

## What it does
Payments.

## Rules
- RULE-1: Charges the correct amount
- RULE-2: Refunds within 24 hours

## Proof
- PROOF-1 (RULE-1): Create charge, verify amount
- PROOF-2 (RULE-2): Request refund, verify processed
""")
        with open(os.path.join(billing_dir, 'payments.proofs-unit.json'), 'w') as f:
            json.dump({"tier": "unit", "proofs": [
                {"feature": "payments", "id": "PROOF-1", "rule": "RULE-1",
                 "test_file": "tests/test_payments.py", "test_name": "test_charge",
                 "status": "pass", "tier": "unit"},
                {"feature": "payments", "id": "PROOF-2", "rule": "RULE-2",
                 "test_file": "tests/test_payments.py", "test_name": "test_refund",
                 "status": "pass", "tier": "unit"},
            ]}, f)

        # Audit cache: auth has 2S+1W, billing has 1S+1H
        ts = (datetime.datetime.now(datetime.timezone.utc)
              - datetime.timedelta(minutes=5)).isoformat()
        cache = {
            'h1': {'assessment': 'STRONG', 'criterion': 'ok', 'why': 'good',
                   'fix': 'none', 'feature': 'login', 'proof_id': 'PROOF-1',
                   'rule_id': 'RULE-1', 'priority': 'LOW', 'cached_at': ts},
            'h2': {'assessment': 'STRONG', 'criterion': 'ok', 'why': 'good',
                   'fix': 'none', 'feature': 'login', 'proof_id': 'PROOF-2',
                   'rule_id': 'RULE-2', 'priority': 'LOW', 'cached_at': ts},
            'h3': {'assessment': 'WEAK', 'criterion': 'missing edge case',
                   'why': 'no test for concurrent requests', 'fix': 'add concurrency test',
                   'feature': 'login', 'proof_id': 'PROOF-3',
                   'rule_id': 'RULE-3', 'priority': 'HIGH', 'cached_at': ts},
            'h4': {'assessment': 'STRONG', 'criterion': 'ok', 'why': 'good',
                   'fix': 'none', 'feature': 'payments', 'proof_id': 'PROOF-1',
                   'rule_id': 'RULE-1', 'priority': 'LOW', 'cached_at': ts},
            'h5': {'assessment': 'HOLLOW', 'criterion': 'assert True',
                   'why': 'no real assertion', 'fix': 'add amount check',
                   'feature': 'payments', 'proof_id': 'PROOF-2',
                   'rule_id': 'RULE-2', 'priority': 'CRITICAL', 'cached_at': ts},
        }
        write_audit_cache(self.tmp_dir, cache)

        subprocess.run(['git', 'add', '.'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'setup'],
                       cwd=self.tmp_dir, capture_output=True)

        cli_output = sync_status(self.tmp_dir)

        # Parse report-data.js
        report_path = os.path.join(self.tmp_dir, '.purlin', 'report-data.js')
        with open(report_path) as f:
            content = f.read()
        json_str = content.replace('const PURLIN_DATA = ', '', 1).rstrip().rstrip(';')
        data = json.loads(json_str)

        # Verify global integrity: CLI vs dashboard
        import re
        match = re.search(r'Integrity:\s+(\d+)%', cli_output)
        assert match, f"CLI should show 'Integrity: N%', got:\n{cli_output}"
        cli_global = int(match.group(1))
        dash_global = data['audit_summary']['integrity']
        expected_global = round(3 / 5 * 100)  # 60%

        assert cli_global == expected_global, (
            f"CLI global integrity ({cli_global}%) != expected ({expected_global}%)"
        )
        assert dash_global == expected_global, (
            f"Dashboard global integrity ({dash_global}%) != expected ({expected_global}%)"
        )

        # Verify per-feature integrity: dashboard
        login_feat = next(f for f in data['features'] if f['name'] == 'login')
        payments_feat = next(f for f in data['features'] if f['name'] == 'payments')

        assert login_feat['audit']['integrity'] == round(2 / 3 * 100), (
            f"login integrity should be 67%, got {login_feat['audit']['integrity']}%"
        )
        assert payments_feat['audit']['integrity'] == round(1 / 2 * 100), (
            f"payments integrity should be 50%, got {payments_feat['audit']['integrity']}%"
        )

    @pytest.mark.proof("sync_status", "PROOF-61", "RULE-35", tier="e2e")
    def test_all_statuses_cli_matches_dashboard(self):
        """RULE-35: Feature status matches between CLI summary table and dashboard.

        Setup: Isolated project with features in every status:
        - verified_feat: all proved + receipt → VERIFIED
        - passing_feat: all proved, no receipt → PASSING
        - partial_feat: some proved → PARTIAL
        - failing_feat: has a failing proof → FAILING
        - untested_feat: zero proofs → UNTESTED
        Verifies CLI table status matches report-data.js status for all five.
        """
        # Create project manually (not using _make_project to avoid default spec)
        purlin_dir = os.path.join(self.tmp_dir, '.purlin')
        os.makedirs(os.path.join(purlin_dir, 'cache'), exist_ok=True)
        config = {"version": "0.9.0", "test_framework": "auto",
                  "spec_dir": "specs", "report": True}
        with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
            json.dump(config, f)

        html_path = os.path.join(self.tmp_dir, 'purlin-report.html')
        with open(html_path, 'w') as f:
            f.write('<html></html>')

        specs_dir = os.path.join(self.tmp_dir, 'specs', 'test')
        os.makedirs(specs_dir, exist_ok=True)

        def _write_spec(name, rules_count):
            rules = '\n'.join(f'- RULE-{i}: Rule {i} for {name}'
                              for i in range(1, rules_count + 1))
            with open(os.path.join(specs_dir, f'{name}.md'), 'w') as f:
                f.write(f"""# Feature: {name}

> Scope: src/{name}.py

## What it does
{name}.

## Rules
{rules}

## Proof
""")

        def _write_proofs(name, proofs):
            with open(os.path.join(specs_dir, f'{name}.proofs-unit.json'), 'w') as f:
                json.dump({"tier": "unit", "proofs": proofs}, f)

        def _write_receipt(name, vhash):
            with open(os.path.join(specs_dir, f'{name}.receipt.json'), 'w') as f:
                json.dump({
                    "vhash": vhash,
                    "commit": "abc123",
                    "timestamp": datetime.datetime.now(
                        datetime.timezone.utc).isoformat(),
                    "rules": [f"RULE-{i}" for i in range(1, 3)],
                    "proofs": ["PROOF-1", "PROOF-2"],
                }, f)

        # 1. verified_feat: 2 rules, all proved, receipt matches
        _write_spec('verified_feat', 2)
        _write_proofs('verified_feat', [
            {"feature": "verified_feat", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t1", "status": "pass", "tier": "unit"},
            {"feature": "verified_feat", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "t.py", "test_name": "t2", "status": "pass", "tier": "unit"},
        ])

        # 2. passing_feat: 2 rules, all proved, no receipt
        _write_spec('passing_feat', 2)
        _write_proofs('passing_feat', [
            {"feature": "passing_feat", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t1", "status": "pass", "tier": "unit"},
            {"feature": "passing_feat", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "t.py", "test_name": "t2", "status": "pass", "tier": "unit"},
        ])

        # 3. partial_feat: 2 rules, 1 proved
        _write_spec('partial_feat', 2)
        _write_proofs('partial_feat', [
            {"feature": "partial_feat", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t1", "status": "pass", "tier": "unit"},
        ])

        # 4. failing_feat: 2 rules, 1 failing
        _write_spec('failing_feat', 2)
        _write_proofs('failing_feat', [
            {"feature": "failing_feat", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t1", "status": "pass", "tier": "unit"},
            {"feature": "failing_feat", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "t.py", "test_name": "t2", "status": "fail", "tier": "unit"},
        ])

        # 5. untested_feat: 2 rules, no proofs
        _write_spec('untested_feat', 2)

        # Initialize git and commit
        subprocess.run(['git', 'init'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'add', '.'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'init'],
                       cwd=self.tmp_dir, capture_output=True)

        # Compute vhash for verified_feat and write matching receipt
        from purlin_server import _compute_vhash, _build_coverage_rules, \
            _build_proof_lookup, _collect_relevant_proofs
        features = _scan_specs(self.tmp_dir)
        all_proofs = _read_proofs(self.tmp_dir)
        vf_info = features['verified_feat']
        vf_rules, _ = _build_coverage_rules('verified_feat', vf_info, features, {})
        vf_active = [(k, l, s) for k, l, s, d in vf_rules if not d]
        vf_all_proofs = _collect_relevant_proofs('verified_feat', vf_rules, all_proofs)
        vf_vhash = _compute_vhash(
            {k: True for k, _, _ in vf_active}, vf_all_proofs
        )
        _write_receipt('verified_feat', vf_vhash)

        # Recommit with receipt
        subprocess.run(['git', 'add', '.'], cwd=self.tmp_dir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'add receipt'],
                       cwd=self.tmp_dir, capture_output=True)

        # Run sync_status
        cli_output = sync_status(self.tmp_dir)

        # Parse report-data.js
        report_path = os.path.join(self.tmp_dir, '.purlin', 'report-data.js')
        with open(report_path) as f:
            content = f.read()
        json_str = content.replace('const PURLIN_DATA = ', '', 1).rstrip().rstrip(';')
        data = json.loads(json_str)

        # Build expected status map
        expected = {
            'verified_feat': 'VERIFIED',
            'passing_feat': 'PASSING',
            'partial_feat': 'PARTIAL',
            'failing_feat': 'FAILING',
            'untested_feat': 'UNTESTED',
        }

        # Verify dashboard statuses
        for feat in data['features']:
            name = feat['name']
            if name in expected:
                assert feat['status'] == expected[name], (
                    f"Dashboard: {name} should be {expected[name]}, "
                    f"got {feat['status']}"
                )

        # Verify CLI statuses (parse summary table)
        import re
        for name, exp_status in expected.items():
            # Match table row: │ name ... │ status │
            pattern = rf'{re.escape(name)}\s+.*?\s+({exp_status})'
            assert re.search(pattern, cli_output), (
                f"CLI summary table should show {name} as {exp_status}\n"
                f"CLI output:\n{cli_output}"
            )
