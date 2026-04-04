"""Tests for report_data feature: 16 rules covering .purlin/report-data.js generation."""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'mcp'))
import purlin_server


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_project(tmp_dir, report_enabled=True):
    """Set up a minimal project with .purlin/ dir and config."""
    purlin_dir = os.path.join(tmp_dir, '.purlin')
    os.makedirs(purlin_dir, exist_ok=True)
    config = {}
    if report_enabled:
        config['report'] = True
    with open(os.path.join(purlin_dir, 'config.json'), 'w') as f:
        json.dump(config, f)
    return purlin_dir


def _write_spec(tmp_dir, name, content, subdir='app'):
    spec_dir = os.path.join(tmp_dir, 'specs', subdir)
    os.makedirs(spec_dir, exist_ok=True)
    path = os.path.join(spec_dir, f'{name}.md')
    with open(path, 'w') as f:
        f.write(content)
    return path


def _write_proofs(tmp_dir, name, proofs, tier='unit', subdir='app'):
    spec_dir = os.path.join(tmp_dir, 'specs', subdir)
    os.makedirs(spec_dir, exist_ok=True)
    path = os.path.join(spec_dir, f'{name}.proofs-{tier}.json')
    with open(path, 'w') as f:
        json.dump({'tier': tier, 'proofs': proofs}, f)
    return path


def _write_receipt(tmp_dir, name, commit, timestamp, vhash, subdir='app'):
    spec_dir = os.path.join(tmp_dir, 'specs', subdir)
    os.makedirs(spec_dir, exist_ok=True)
    path = os.path.join(spec_dir, f'{name}.receipt.json')
    with open(path, 'w') as f:
        json.dump({'commit': commit, 'timestamp': timestamp, 'vhash': vhash}, f)
    return path


def _write_audit_cache(tmp_dir, entries):
    """Write audit_cache.json to .purlin/cache/."""
    cache_dir = os.path.join(tmp_dir, '.purlin', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, 'audit_cache.json')
    with open(path, 'w') as f:
        json.dump(entries, f)
    return path


def _read_report(tmp_dir):
    """Read and parse report-data.js, stripping the JS wrapper."""
    report_path = os.path.join(tmp_dir, '.purlin', 'report-data.js')
    with open(report_path) as f:
        content = f.read()
    # Strip: "const PURLIN_DATA = " prefix and trailing ";\n"
    json_str = re.sub(r'^const PURLIN_DATA = ', '', content).rstrip(';\n')
    return json.loads(json_str)


def _minimal_spec_content(name='feature'):
    return (
        f'# Feature: {name}\n\n'
        '## What it does\nDoes stuff.\n\n'
        '## Rules\n'
        '- RULE-1: Returns correct output\n\n'
        '## Proof\n'
        '- PROOF-1 (RULE-1): Call function, assert output\n'
    )


def _minimal_proofs(feature='feature'):
    return [{
        'feature': feature,
        'id': 'PROOF-1',
        'rule': 'RULE-1',
        'test_file': 'tests/test_app.py',
        'test_name': 'test_returns_output',
        'status': 'pass',
        'tier': 'unit',
    }]


def _git_init(tmp_dir):
    """Initialize a git repo in tmp_dir with a minimal commit."""
    subprocess.run(['git', 'init'], cwd=tmp_dir, capture_output=True, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@test.com'],
                   cwd=tmp_dir, capture_output=True, check=True)
    subprocess.run(['git', 'config', 'user.name', 'Test'],
                   cwd=tmp_dir, capture_output=True, check=True)
    # Need at least one commit for sync_status git calls to succeed
    marker = os.path.join(tmp_dir, '.gitkeep')
    with open(marker, 'w') as f:
        f.write('')
    subprocess.run(['git', 'add', '.'], cwd=tmp_dir, capture_output=True, check=True)
    subprocess.run(['git', 'commit', '-m', 'init'],
                   cwd=tmp_dir, capture_output=True, check=True)


# ---------------------------------------------------------------------------
# Integration tests (require git init)
# ---------------------------------------------------------------------------

class TestReportFileGeneration:
    """RULE-1, RULE-2, RULE-14: File writing via sync_status."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmp)

    @pytest.mark.proof("report_data", "PROOF-1", "RULE-1")
    def test_report_written_when_enabled(self):
        """When config has report=true, sync_status writes .purlin/report-data.js."""
        _git_init(self.tmp)
        _make_project(self.tmp, report_enabled=True)
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        _write_proofs(self.tmp, 'feature', _minimal_proofs())

        purlin_server.sync_status(self.tmp)

        report_path = os.path.join(self.tmp, '.purlin', 'report-data.js')
        assert os.path.isfile(report_path), \
            f'Expected .purlin/report-data.js to be written, but it was not found at {report_path}'

    @pytest.mark.proof("report_data", "PROOF-2", "RULE-2")
    def test_no_report_written_when_disabled(self):
        """When config lacks report or it is false, no report-data.js is written."""
        _git_init(self.tmp)
        _make_project(self.tmp, report_enabled=False)
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        _write_proofs(self.tmp, 'feature', _minimal_proofs())

        purlin_server.sync_status(self.tmp)

        report_path = os.path.join(self.tmp, '.purlin', 'report-data.js')
        assert not os.path.isfile(report_path), \
            'Expected no report-data.js when report=false, but file was written'

    @pytest.mark.proof("report_data", "PROOF-14", "RULE-14")
    def test_dashboard_url_in_output_when_html_exists(self):
        """When purlin-report.html exists at project root, sync_status output includes file:// URL."""
        _git_init(self.tmp)
        _make_project(self.tmp, report_enabled=True)
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        _write_proofs(self.tmp, 'feature', _minimal_proofs())

        # Place purlin-report.html at project root
        html_path = os.path.join(self.tmp, 'purlin-report.html')
        with open(html_path, 'w') as f:
            f.write('<html></html>')

        result = purlin_server.sync_status(self.tmp)

        assert 'file://' in result, \
            f'Expected file:// URL in sync_status output, got: {result}'
        assert 'purlin-report.html' in result, \
            f'Expected purlin-report.html in sync_status output, got: {result}'


# ---------------------------------------------------------------------------
# Unit tests using _build_report_data directly (no git needed)
# ---------------------------------------------------------------------------

class TestReportDataStructure:
    """RULE-3 through RULE-13, RULE-15, RULE-16: Data contract tests."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        _make_project(self.tmp, report_enabled=True)

    def teardown_method(self):
        shutil.rmtree(self.tmp)

    def _build(self, features=None, proofs=None, config=None, audit_summary=None):
        """Call _build_report_data with sensible defaults."""
        if features is None:
            _write_spec(self.tmp, 'feature', _minimal_spec_content())
            features = purlin_server._scan_specs(self.tmp)
        if proofs is None:
            _write_proofs(self.tmp, 'feature', _minimal_proofs())
            proofs = purlin_server._read_proofs(self.tmp)
        if config is None:
            config = {'report': True}
        global_anchors = {k: v for k, v in features.items() if v.get('is_global')}
        return purlin_server._build_report_data(
            self.tmp, features, proofs, config, global_anchors, audit_summary
        )

    @pytest.mark.proof("report_data", "PROOF-3", "RULE-3")
    def test_report_file_is_valid_js_with_json(self):
        """report-data.js contains 'const PURLIN_DATA = {...};' that parses as valid JSON."""
        features = purlin_server._scan_specs(self.tmp) or {}
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        features = purlin_server._scan_specs(self.tmp)
        _write_proofs(self.tmp, 'feature', _minimal_proofs())
        proofs = purlin_server._read_proofs(self.tmp)
        global_anchors = {}
        config = {'report': True}

        path = purlin_server._write_report_data(
            self.tmp, features, proofs, config, global_anchors
        )
        assert path is not None, 'Expected _write_report_data to return a path'

        with open(path) as f:
            content = f.read()

        # Must start with "const PURLIN_DATA = "
        assert content.startswith('const PURLIN_DATA = '), \
            f'Expected JS variable declaration, got: {content[:60]}'

        # Strip wrapper and parse
        json_str = re.sub(r'^const PURLIN_DATA = ', '', content).rstrip(';\n')
        data = json.loads(json_str)  # must not raise
        assert isinstance(data, dict), 'Parsed data must be a dict'

    @pytest.mark.proof("report_data", "PROOF-4", "RULE-4")
    def test_summary_counts_sum_to_total(self):
        """PURLIN_DATA.summary counts sum to total_features."""
        # Add two features: one READY, one with no proofs
        _write_spec(self.tmp, 'feature_a', _minimal_spec_content('feature_a'))
        _write_spec(self.tmp, 'feature_b', _minimal_spec_content('feature_b'))
        _write_proofs(self.tmp, 'feature_a', _minimal_proofs('feature_a'))
        # feature_b gets no proofs
        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)

        data = self._build(features=features, proofs=proofs)
        s = data['summary']

        total = s['total_features']
        components = s['verified'] + s.get('passing', 0) + s['partial'] + s['failing'] + s['untested']
        assert components == total, (
            f'Summary counts do not sum to total: '
            f"verified={s['verified']} + passing={s.get('passing', 0)} + partial={s['partial']} "
            f"+ failing={s['failing']} + untested={s['untested']} = {components}, "
            f"expected total={total}"
        )

    @pytest.mark.proof("report_data", "PROOF-5", "RULE-5")
    def test_every_feature_has_required_fields(self):
        """Every feature entry has all required fields."""
        required_fields = {
            'name', 'type', 'is_global', 'proved', 'total', 'deferred',
            'status', 'structural_checks', 'vhash', 'receipt', 'rules', 'audit',
        }
        data = self._build()
        for feat in data['features']:
            missing = required_fields - set(feat.keys())
            assert not missing, \
                f"Feature '{feat.get('name', '?')}' missing fields: {missing}"

    @pytest.mark.proof("report_data", "PROOF-6", "RULE-6")
    def test_passing_features_have_vhash_others_do_not(self):
        """Features with all proofs passing have non-null vhash; others have null."""
        _write_spec(self.tmp, 'feature_ready', _minimal_spec_content('feature_ready'))
        _write_spec(self.tmp, 'feature_noproof',
                    '# Feature: feature_noproof\n\n'
                    '## What it does\nDoes nothing.\n\n'
                    '## Rules\n- RULE-1: Something\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test something\n')
        _write_proofs(self.tmp, 'feature_ready', _minimal_proofs('feature_ready'))

        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        for feat in data['features']:
            if feat['status'] in ('VERIFIED', 'PASSING'):
                assert feat['vhash'] is not None, \
                    f"Passing feature '{feat['name']}' should have non-null vhash"
            else:
                assert feat['vhash'] is None, \
                    f"Non-passing feature '{feat['name']}' (status={feat['status']}) should have null vhash"

    @pytest.mark.proof("report_data", "PROOF-7", "RULE-7")
    def test_receipt_fields_present_when_receipt_file_exists(self):
        """Features with receipt files include commit, timestamp, and stale fields."""
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        _write_proofs(self.tmp, 'feature', _minimal_proofs())
        _write_receipt(
            self.tmp, 'feature',
            commit='abc1234',
            timestamp='2024-01-01T00:00:00+00:00',
            vhash='deadbeef',
        )

        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        feature_entry = next(
            (f for f in data['features'] if f['name'] == 'feature'), None
        )
        assert feature_entry is not None, "Expected 'feature' in features list"
        receipt = feature_entry['receipt']
        assert receipt is not None, "Expected receipt to be non-null"
        assert 'commit' in receipt, "receipt missing 'commit' field"
        assert 'timestamp' in receipt, "receipt missing 'timestamp' field"
        assert 'stale' in receipt, "receipt missing 'stale' field"
        assert receipt['commit'] == 'abc1234'
        assert receipt['timestamp'] == '2024-01-01T00:00:00+00:00'
        # vhash won't match (deadbeef vs computed), so stale should be True
        assert isinstance(receipt['stale'], bool)

    @pytest.mark.proof("report_data", "PROOF-8", "RULE-8")
    def test_every_rule_entry_has_required_fields(self):
        """Every rule entry has id, description, label, source, is_deferred, is_assumed, status, proofs."""
        required_fields = {
            'id', 'description', 'label', 'source', 'is_deferred',
            'is_assumed', 'status', 'proofs',
        }
        data = self._build()
        for feat in data['features']:
            for rule in feat['rules']:
                missing = required_fields - set(rule.keys())
                assert not missing, \
                    f"Rule '{rule.get('id', '?')}' in feature '{feat['name']}' missing fields: {missing}"

    @pytest.mark.proof("report_data", "PROOF-9", "RULE-9")
    def test_all_rule_statuses_are_valid(self):
        """All rule statuses are one of: PASS, FAIL, NO_PROOF, CHECK, or DEFERRED."""
        valid_statuses = {'PASS', 'FAIL', 'NO_PROOF', 'CHECK', 'DEFERRED'}
        # Build with both passing and no-proof rules
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        _write_proofs(self.tmp, 'feature', _minimal_proofs())
        # Also a feature with no proofs
        _write_spec(self.tmp, 'feature2',
                    '# Feature: feature2\n\n'
                    '## What it does\nDoes stuff.\n\n'
                    '## Rules\n- RULE-1: Something\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test something\n')
        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        for feat in data['features']:
            for rule in feat['rules']:
                assert rule['status'] in valid_statuses, \
                    (f"Rule '{rule['id']}' in feature '{feat['name']}' has invalid "
                     f"status '{rule['status']}'; expected one of {valid_statuses}")

    @pytest.mark.proof("report_data", "PROOF-10", "RULE-10")
    def test_all_rule_labels_are_valid(self):
        """All rule labels are one of: own, required, or global."""
        valid_labels = {'own', 'required', 'global'}
        # Set up a spec that requires an anchor (to get 'required' label)
        anchor_dir = os.path.join(self.tmp, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        with open(os.path.join(anchor_dir, 'security.md'), 'w') as f:
            f.write(
                '# Anchor: security\n\n'
                '## What it does\nSecurity constraints.\n\n'
                '## Rules\n- RULE-1: No eval\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Grep for eval\n'
            )
        _write_spec(self.tmp, 'feature',
                    '# Feature: feature\n\n'
                    '> Requires: security\n\n'
                    '## What it does\nDoes stuff.\n\n'
                    '## Rules\n- RULE-1: Returns correct output\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Call function, assert output\n')
        _write_proofs(self.tmp, 'feature', _minimal_proofs())
        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        for feat in data['features']:
            for rule in feat['rules']:
                assert rule['label'] in valid_labels, \
                    (f"Rule '{rule['id']}' in feature '{feat['name']}' has invalid "
                     f"label '{rule['label']}'; expected one of {valid_labels}")

    @pytest.mark.proof("report_data", "PROOF-11", "RULE-11")
    def test_docs_url_derived_from_git_remote(self):
        """_get_plugin_docs_url returns a URL derived from the git remote."""
        url = purlin_server._get_plugin_docs_url()
        # The Purlin repo has a git remote; url should be non-None and be a URL string
        if url is not None:
            assert url.startswith('https://'), \
                f"Expected docs_url to start with https://, got: {url}"
            assert 'docs' in url or 'blob' in url, \
                f"Expected docs_url to reference docs path, got: {url}"

        # Also verify it appears in report data
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        _write_proofs(self.tmp, 'feature', _minimal_proofs())
        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        # docs_url key must exist in report data (may be None if no remote)
        assert 'docs_url' in data, "Expected 'docs_url' field in report data"
        # If _get_plugin_docs_url returns a value, it must match
        assert data['docs_url'] == url, \
            f"Report data docs_url {data['docs_url']!r} != _get_plugin_docs_url() {url!r}"

    @pytest.mark.proof("report_data", "PROOF-12", "RULE-12")
    def test_anchor_with_source_includes_source_url(self):
        """Anchor features have type 'anchor' and include source_url when > Source: is present."""
        anchor_dir = os.path.join(self.tmp, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        with open(os.path.join(anchor_dir, 'ext_anchor.md'), 'w') as f:
            f.write(
                '# Anchor: ext_anchor\n\n'
                '> Source: https://example.com/anchor-spec.md\n\n'
                '## What it does\nExternal anchor.\n\n'
                '## Rules\n- RULE-1: Follows spec\n\n'
                '## Proof\n- PROOF-1 (RULE-1): Verify compliance\n'
            )
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        anchor_feat = next(
            (f for f in data['features'] if f['name'] == 'ext_anchor'), None
        )
        assert anchor_feat is not None, "Expected ext_anchor in features list"
        assert anchor_feat['type'] == 'anchor', \
            f"Expected type='anchor', got '{anchor_feat['type']}'"
        assert anchor_feat['source_url'] == 'https://example.com/anchor-spec.md', \
            f"Expected source_url from spec > Source:, got {anchor_feat['source_url']!r}"

    @pytest.mark.proof("report_data", "PROOF-13", "RULE-13")
    def test_anchors_summary_total_matches_anchor_count(self):
        """anchors_summary.total matches the count of features with type 'anchor'."""
        # Create two anchors
        anchor_dir = os.path.join(self.tmp, 'specs', '_anchors')
        os.makedirs(anchor_dir, exist_ok=True)
        for anchor_name in ('anchor_a', 'anchor_b'):
            with open(os.path.join(anchor_dir, f'{anchor_name}.md'), 'w') as f:
                f.write(
                    f'# Anchor: {anchor_name}\n\n'
                    '## What it does\nAnchor.\n\n'
                    '## Rules\n- RULE-1: Does something\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test\n'
                )
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        anchor_count = sum(1 for f in data['features'] if f['type'] == 'anchor')
        assert data['anchors_summary']['total'] == anchor_count, (
            f"anchors_summary.total={data['anchors_summary']['total']} "
            f"but counted {anchor_count} anchor-type features"
        )

    @pytest.mark.proof("report_data", "PROOF-15", "RULE-15")
    def test_audit_summary_fields_present_and_null_when_no_cache(self):
        """audit_summary has required fields when cache exists; null when no cache."""
        # First: verify null when no cache
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        _write_proofs(self.tmp, 'feature', _minimal_proofs())
        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)

        data_no_cache = self._build(features=features, proofs=proofs, audit_summary=None)
        assert data_no_cache['audit_summary'] is None, \
            f"Expected audit_summary=null when no cache, got: {data_no_cache['audit_summary']}"

        # Now: write an audit cache and verify fields
        cache_entries = {
            'feature::PROOF-1::RULE-1': {
                'feature': 'feature',
                'proof_id': 'PROOF-1',
                'rule_id': 'RULE-1',
                'assessment': 'STRONG',
                'criterion': 'Tests real behavior',
                'fix': '',
                'priority': 'LOW',
                'cached_at': '2024-01-01T12:00:00+00:00',
            },
            'feature::PROOF-1::RULE-2': {
                'feature': 'feature',
                'proof_id': 'PROOF-2',
                'rule_id': 'RULE-2',
                'assessment': 'WEAK',
                'criterion': 'Missing assertion',
                'fix': 'Add assertion',
                'priority': 'HIGH',
                'cached_at': '2024-01-01T12:00:00+00:00',
            },
        }
        _write_audit_cache(self.tmp, cache_entries)
        audit_summary = purlin_server._read_audit_summary(self.tmp)
        data_with_cache = self._build(
            features=features, proofs=proofs, audit_summary=audit_summary
        )

        summary = data_with_cache['audit_summary']
        assert summary is not None, "Expected non-null audit_summary when cache exists"
        required_fields = {'integrity', 'strong', 'weak', 'hollow', 'manual',
                           'last_audit', 'last_audit_relative', 'stale'}
        missing = required_fields - set(summary.keys())
        assert not missing, f"audit_summary missing fields: {missing}"
        assert isinstance(summary['integrity'], (int, float)), \
            f"integrity should be numeric, got {type(summary['integrity'])}"
        assert isinstance(summary['stale'], bool), \
            f"stale should be bool, got {type(summary['stale'])}"

    @pytest.mark.proof("report_data", "PROOF-16", "RULE-16")
    def test_per_feature_audit_populated_from_cache(self):
        """Per-feature audit is populated from audit cache when entries exist for that feature."""
        _write_spec(self.tmp, 'feature', _minimal_spec_content())
        _write_proofs(self.tmp, 'feature', _minimal_proofs())

        cache_entries = {
            'feature::PROOF-1::RULE-1': {
                'feature': 'feature',
                'proof_id': 'PROOF-1',
                'rule_id': 'RULE-1',
                'assessment': 'HOLLOW',
                'criterion': 'No real assertion',
                'fix': 'Add assert on return value',
                'priority': 'CRITICAL',
                'cached_at': '2024-01-01T12:00:00+00:00',
            },
            'feature::PROOF-2::RULE-2': {
                'feature': 'feature',
                'proof_id': 'PROOF-2',
                'rule_id': 'RULE-2',
                'assessment': 'STRONG',
                'criterion': 'Direct assertion',
                'fix': '',
                'priority': 'LOW',
                'cached_at': '2024-01-01T12:00:00+00:00',
            },
        }
        _write_audit_cache(self.tmp, cache_entries)

        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        feature_entry = next(
            (f for f in data['features'] if f['name'] == 'feature'), None
        )
        assert feature_entry is not None, "Expected 'feature' in features"
        audit = feature_entry['audit']
        assert audit is not None, \
            "Expected feature audit to be non-null when cache entries exist"

        # Should have integrity percentage
        assert 'integrity' in audit, "feature audit missing 'integrity'"
        assert isinstance(audit['integrity'], (int, float))

        # Should reflect the HOLLOW and STRONG entries
        assert audit['hollow'] == 1, f"Expected hollow=1, got {audit['hollow']}"
        assert audit['strong'] == 1, f"Expected strong=1, got {audit['strong']}"

        # Findings should contain the HOLLOW entry
        assert 'findings' in audit, "feature audit missing 'findings'"
        assert len(audit['findings']) >= 1, "Expected at least one finding (HOLLOW)"
        hollow_findings = [fn for fn in audit['findings'] if fn['level'] == 'HOLLOW']
        assert hollow_findings, "Expected HOLLOW-level finding in audit findings"
        finding = hollow_findings[0]
        assert finding['criterion'] == 'No real assertion'
        assert finding['fix'] == 'Add assert on return value'

    @pytest.mark.proof("report_data", "PROOF-17", "RULE-17")
    def test_proved_count_excludes_structural_checks(self):
        """RULE-17: Feature proved count excludes structural checks.

        Setup: Feature with 3 rules — 2 behavioral, 1 structural (grep-based).
        All 3 have passing proofs. The structural proof should count as a
        structural_check but NOT toward the proved count.
        Expected: proved==2, structural_checks==1, total==3
        """
        _make_project(self.tmp)

        # Create a feature with mixed behavioral + structural rules
        _write_spec(self.tmp, 'mixed', (
            '# Feature: mixed\n\n'
            '> Scope: src/mixed.py\n\n'
            '## What it does\nMixed feature.\n\n'
            '## Rules\n'
            '- RULE-1: Returns correct output on valid input\n'
            '- RULE-2: Raises error on invalid input\n'
            '- RULE-3: Config file contains the required section\n\n'
            '## Proof\n'
            '- PROOF-1 (RULE-1): Call with valid input, assert output matches expected\n'
            '- PROOF-2 (RULE-2): Call with invalid input, assert ValueError raised\n'
            '- PROOF-3 (RULE-3): Grep config.yaml for required_section; verify present\n'
        ))

        # All 3 proofs pass
        _write_proofs(self.tmp, 'mixed', [
            {"feature": "mixed", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test_mixed.py", "test_name": "test_valid",
             "status": "pass", "tier": "unit"},
            {"feature": "mixed", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "tests/test_mixed.py", "test_name": "test_invalid",
             "status": "pass", "tier": "unit"},
            {"feature": "mixed", "id": "PROOF-3", "rule": "RULE-3",
             "test_file": "tests/test_mixed.py", "test_name": "test_config",
             "status": "pass", "tier": "unit"},
        ])

        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        mixed = next(f for f in data['features'] if f['name'] == 'mixed')

        # proved should count only behavioral proofs (2), not structural (1)
        assert mixed['proved'] == 2, (
            f"Expected proved=2 (behavioral only), got {mixed['proved']}. "
            f"Structural checks should NOT inflate the proved count."
        )
        assert mixed['structural_checks'] == 1, (
            f"Expected structural_checks=1, got {mixed['structural_checks']}"
        )
        assert mixed['total'] == 3, (
            f"Expected total=3 (all rules), got {mixed['total']}"
        )

    @pytest.mark.proof("report_data", "PROOF-18", "RULE-18")
    def test_partial_coverage_gets_partial_status_not_passing(self):
        """RULE-18: Features with partial behavioral coverage get PARTIAL, not PASSING."""
        # Create a feature with 3 behavioral rules but only 2 passing proofs
        _write_spec(self.tmp, 'login',
                    '# Feature: login\n\n'
                    '## What it does\nHandles login.\n\n'
                    '## Rules\n- RULE-1: Validate creds\n'
                    '- RULE-2: Return token\n'
                    '- RULE-3: Log attempt\n\n'
                    '## Proof\n- PROOF-1 (RULE-1): Test creds\n'
                    '- PROOF-2 (RULE-2): Test token\n'
                    '- PROOF-3 (RULE-3): Test logs\n')
        _write_proofs(self.tmp, 'login', [
            {"feature": "login", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test.py", "test_name": "test_creds",
             "status": "pass", "tier": "unit"},
            {"feature": "login", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "tests/test.py", "test_name": "test_token",
             "status": "pass", "tier": "unit"},
        ])

        features = purlin_server._scan_specs(self.tmp)
        proofs = purlin_server._read_proofs(self.tmp)
        data = self._build(features=features, proofs=proofs)

        login = next(f for f in data['features'] if f['name'] == 'login')
        assert login['status'] == 'PARTIAL', (
            f"Expected status='PARTIAL' for 2/3 rules proved, got '{login['status']}'. "
            f"Incomplete behavioral coverage must never be PASSING."
        )
        assert login['proved'] == 2, f"Expected proved=2, got {login['proved']}"
        assert login['total'] == 3, f"Expected total=3, got {login['total']}"
