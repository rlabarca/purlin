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

    def _write_proofs(self, name, proofs, tier='unit', subdir='test'):
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
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        assert 'foo: passing' in result

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
            '## Rules\n- RULE-1: Must work\n- RULE-2: Must also work\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n- PROOF-2 (RULE-2): Test\n'
        ))
        # "error" is invalid — should not count as pass
        self._write_proofs('bar', [
            {"feature": "bar", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t",
             "status": "error", "tier": "unit"},
            {"feature": "bar", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "t.py", "test_name": "t2",
             "status": "pass", "tier": "unit"},
        ])
        result = purlin_server.sync_status(self.project_root)
        assert 'bar: READY' not in result, "Invalid status 'error' should not yield READY"
        assert '1/2 rules proved' in result, \
            "'pass' should count, 'error' should not"
        # Also verify that "fail" is a valid (non-passing) status distinct from invalid
        self._write_proofs('bar', [
            {"feature": "bar", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t",
             "status": "fail", "tier": "unit"},
            {"feature": "bar", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "t.py", "test_name": "t2",
             "status": "pass", "tier": "unit"},
        ])
        result2 = purlin_server.sync_status(self.project_root)
        assert 'bar: READY' not in result2, "'fail' status should not yield READY"
        assert '1/2 rules proved' in result2, \
            "'fail' is valid but non-passing — only 'pass' should count"

    @pytest.mark.proof("schema_proof_format", "PROOF-5", "RULE-5")
    def test_feature_scoped_overwrite(self):
        import subprocess
        self._write_spec('feat_a', (
            '# Feature: feat_a\n\n'
            '## What it does\nA.\n\n'
            '## Rules\n- RULE-1: Must work\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n'
        ))
        # Pre-populate proof file with feat_b entries
        self._write_proofs('feat_a', [
            {"feature": "feat_b", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "t.py", "test_name": "t_b",
             "status": "pass", "tier": "unit"},
        ])
        # Create a test file with a proof marker for feat_a
        test_file = os.path.join(self.project_root, 'test_feat_a.py')
        with open(test_file, 'w') as f:
            f.write(
                'import pytest\n'
                '@pytest.mark.proof("feat_a", "PROOF-1", "RULE-1")\n'
                'def test_a():\n'
                '    assert True\n'
            )
        # Create conftest that loads the real proof plugin
        plugin_path = os.path.join(PROJECT_ROOT, 'scripts', 'proof')
        conftest = os.path.join(self.project_root, 'conftest.py')
        with open(conftest, 'w') as f:
            f.write(
                f'import sys\n'
                f'sys.path.insert(0, r"{plugin_path}")\n'
                f'from pytest_purlin import pytest_configure  # noqa\n'
            )
        # Run the real pytest plugin via subprocess
        result = subprocess.run(
            ['python3', '-m', 'pytest', test_file, '-q'],
            cwd=self.project_root,
            capture_output=True, text=True
        )
        # Verify feat_b preserved and feat_a added by the real plugin
        proof_path = os.path.join(self.project_root, 'specs', 'test',
                                  'feat_a.proofs-unit.json')
        assert os.path.exists(proof_path), \
            f"Proof file not written. stdout={result.stdout} stderr={result.stderr}"
        with open(proof_path) as f:
            data = json.load(f)
        features = [p['feature'] for p in data['proofs']]
        assert 'feat_b' in features, "feat_b entries were not preserved by plugin"
        assert 'feat_a' in features, "feat_a entries were not added by plugin"


class TestProofFormatConventions:

    @pytest.mark.proof("schema_proof_format", "PROOF-4", "RULE-4")
    def test_standard_tiers_documented(self):
        valid_tiers = {'unit', 'integration', 'e2e'}
        # Verify all existing proof files only use valid tiers
        proof_files = glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**',
                                             '*.proofs-*.json'), recursive=True)
        assert len(proof_files) > 0, "No proof files found"
        for path in proof_files:
            with open(path) as f:
                data = json.load(f)
            file_tier = data.get('tier', '')
            assert file_tier in valid_tiers, \
                f"Invalid top-level tier '{file_tier}' in {path}"
            for entry in data.get('proofs', []):
                entry_tier = entry.get('tier', '')
                assert entry_tier in valid_tiers, \
                    f"Invalid entry tier '{entry_tier}' in {entry.get('id')} of {path}"

        # Verify format reference documents all 3 standard tiers
        with open(os.path.join(PROJECT_ROOT, 'references', 'formats',
                               'spec_format.md')) as f:
            fmt = f.read()
        assert '@integration' in fmt
        assert '@e2e' in fmt

    @pytest.mark.proof("schema_proof_format", "PROOF-6", "RULE-6")
    def test_proof_files_not_gitignored(self):
        import subprocess
        with open(os.path.join(PROJECT_ROOT, '.gitignore')) as f:
            gitignore = f.read()
        # Verify no exact pattern would exclude proof files
        assert '*.proofs-' not in gitignore
        assert 'proofs-*.json' not in gitignore
        assert '.proofs' not in gitignore
        # Verify no broad wildcards that would catch proof files
        for line in gitignore.splitlines():
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            assert line not in ('*.json', 'specs/', 'specs/**'), \
                f"Broad gitignore pattern '{line}' would exclude proof files"
        # Use git check-ignore to verify a proof file path is not ignored
        result = subprocess.run(
            ['git', 'check-ignore', '-q', 'specs/test/foo.proofs-unit.json'],
            cwd=PROJECT_ROOT, capture_output=True
        )
        assert result.returncode != 0, \
            "git check-ignore says proof files ARE ignored"

    @pytest.mark.proof("schema_proof_format", "PROOF-7", "RULE-7")
    def test_manual_stamp_format_documented(self):
        with open(os.path.join(PROJECT_ROOT, 'references', 'formats',
                               'proofs_format.md')) as f:
            content = f.read()
        assert '@manual' in content
        # Verify format: @manual(<email>, <date>, <commit_sha>)
        assert re.search(r'@manual\(.*email.*date.*commit', content,
                         re.IGNORECASE | re.DOTALL), \
            "Manual stamp format must document email, date, and commit fields"
