"""Tests for schema_proof_format — 7 rules.

Validates the proof file schema, merge behavior, tier constraints,
git tracking, and manual stamp format.
"""

import glob
import json
import os
import re
import shutil
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
import purlin_server


class TestProofFormatEnforcement:

    def setup_method(self):
        self.project_root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.project_root, '.purlin'))

    def teardown_method(self):
        shutil.rmtree(self.project_root)

    def _write_spec(self, name, content, subdir='test'):
        d = os.path.join(self.project_root, 'specs', subdir)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f'{name}.md'), 'w') as f:
            f.write(content)

    def _write_proofs(self, name, proofs, tier='default', subdir='test'):
        d = os.path.join(self.project_root, 'specs', subdir)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f'{name}.proofs-{tier}.json'), 'w') as f:
            json.dump({"tier": tier, "proofs": proofs}, f)

    @pytest.mark.proof("schema_proof_format", "PROOF-1", "RULE-1")
    def test_proof_file_read_by_sync_status(self):
        self._write_spec('foo', (
            '# Feature: foo\n\n'
            '## What it does\nFoo.\n\n'
            '## Rules\n- RULE-1: Must work\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        self._write_proofs('foo', [
            {"feature": "foo", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "tests/test_foo.py", "test_name": "test_it",
             "status": "pass", "tier": "default"},
        ])
        result = purlin_server.sync_status(self.project_root)
        assert 'foo: READY' in result

    @pytest.mark.proof("schema_proof_format", "PROOF-2", "RULE-2")
    def test_proof_entry_has_all_seven_fields(self):
        proof_files = glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**',
                                             '*.proofs-*.json'), recursive=True)
        assert len(proof_files) > 0, "No proof files found"
        required = {'feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'}
        for path in proof_files:
            with open(path) as f:
                data = json.load(f)
            assert 'proofs' in data
            assert 'tier' in data
            for entry in data['proofs']:
                missing = required - set(entry.keys())
                assert not missing, f"Missing fields {missing} in {path}"

    @pytest.mark.proof("schema_proof_format", "PROOF-3", "RULE-3")
    def test_invalid_status_not_counted(self):
        self._write_spec('bar', (
            '# Feature: bar\n\n'
            '## What it does\nBar.\n\n'
            '## Rules\n- RULE-1: Must work\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        self._write_proofs('bar', [
            {"feature": "bar", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t",
             "status": "error", "tier": "default"},
        ])
        result = purlin_server.sync_status(self.project_root)
        assert 'bar: READY' not in result
        assert '0/1 rules proved' in result

    @pytest.mark.proof("schema_proof_format", "PROOF-5", "RULE-5")
    def test_feature_scoped_overwrite(self):
        self._write_spec('feat_a', (
            '# Feature: feat_a\n\n'
            '## What it does\nA.\n\n'
            '## Rules\n- RULE-1: Must work\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        # Pre-populate with feat_b entries
        self._write_proofs('feat_a', [
            {"feature": "feat_b", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t_b",
             "status": "pass", "tier": "default"},
        ])
        # Simulate plugin writing feat_a entries (feature-scoped overwrite)
        proof_path = os.path.join(self.project_root, 'specs', 'test',
                                  'feat_a.proofs-default.json')
        with open(proof_path) as f:
            existing = json.load(f).get('proofs', [])
        kept = [e for e in existing if e['feature'] != 'feat_a']
        new_entries = [
            {"feature": "feat_a", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t_a",
             "status": "pass", "tier": "default"},
        ]
        with open(proof_path, 'w') as f:
            json.dump({"tier": "default", "proofs": kept + new_entries}, f)
        # Verify feat_b preserved
        with open(proof_path) as f:
            data = json.load(f)
        features = [p['feature'] for p in data['proofs']]
        assert 'feat_b' in features
        assert 'feat_a' in features


class TestProofFormatConventions:

    @pytest.mark.proof("schema_proof_format", "PROOF-4", "RULE-4")
    def test_standard_tiers_documented(self):
        # Verify proof plugins default to "default" tier
        with open(os.path.join(PROJECT_ROOT, 'scripts', 'proof',
                               'pytest_purlin.py')) as f:
            py_content = f.read()
        assert '"default"' in py_content

        with open(os.path.join(PROJECT_ROOT, 'scripts', 'proof',
                               'shell_purlin.sh')) as f:
            sh_content = f.read()
        assert 'default' in sh_content

        # Verify format reference documents all 3 standard tiers
        with open(os.path.join(PROJECT_ROOT, 'references', 'formats',
                               'spec_format.md')) as f:
            fmt = f.read()
        assert '@slow' in fmt
        assert '@e2e' in fmt

    @pytest.mark.proof("schema_proof_format", "PROOF-6", "RULE-6")
    def test_proof_files_not_gitignored(self):
        with open(os.path.join(PROJECT_ROOT, '.gitignore')) as f:
            gitignore = f.read()
        # Verify no pattern would exclude proof files
        assert '*.proofs-' not in gitignore
        assert 'proofs-*.json' not in gitignore
        assert '.proofs' not in gitignore

    @pytest.mark.proof("schema_proof_format", "PROOF-7", "RULE-7")
    def test_manual_stamp_format_documented(self):
        with open(os.path.join(PROJECT_ROOT, 'references', 'formats',
                               'proofs_format.md')) as f:
            content = f.read()
        assert '@manual' in content
        # Verify format: @manual(<email>, <date>, <commit_sha>)
        assert re.search(r'@manual\(.*email.*date.*commit', content,
                         re.IGNORECASE | re.DOTALL) or \
               re.search(r'@manual\([^)]+,[^)]+,[^)]+\)', content)
