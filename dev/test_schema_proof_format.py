"""Tests for schema_proof_format — 8 rules.

Validates the proof file schema, merge behavior, tier constraints,
platform-scoped file discovery, git tracking, and manual stamp format.
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
        assert 'foo: PASSING' in result

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
        assert 'bar: VERIFIED' not in result, "Invalid status 'error' should not yield VERIFIED"
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
        assert 'bar: VERIFIED' not in result2, "'fail' status should not yield VERIFIED"
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

    @pytest.mark.proof("schema_proof_format", "PROOF-8", "RULE-5")
    def test_merge_key_includes_test_file(self):
        """RULE-5: the merge key is (feature, tier, test_file), not (feature, tier).

        Two entries for ONE feature in one tier file, recorded against two different
        test files. Re-running only one of them must replace that one and leave the
        other alone. A merge keyed on the feature alone deletes both.
        """
        import subprocess
        self._write_spec('feat_split', (
            '# Feature: feat_split\n\n'
            '## What it does\nSplit across two test files.\n\n'
            '## Rules\n- RULE-1: first half\n- RULE-2: second half\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test\n- PROOF-2 (RULE-2): Test\n'
        ))
        # Both test files must exist on disk: an entry pointing at a vanished file is
        # reaped by design, which would mask the behaviour under test.
        for name, pid, rid in (('test_first_half.py', 'PROOF-1', 'RULE-1'),
                               ('test_second_half.py', 'PROOF-2', 'RULE-2')):
            with open(os.path.join(self.project_root, name), 'w') as f:
                f.write(
                    'import pytest\n'
                    f'@pytest.mark.proof("feat_split", "{pid}", "{rid}")\n'
                    f'def test_{pid.lower().replace("-", "_")}():\n'
                    '    assert True\n'
                )
        self._write_proofs('feat_split', [
            {"feature": "feat_split", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "test_first_half.py", "test_name": "stale_name",
             "status": "fail", "tier": "unit"},
            {"feature": "feat_split", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "test_second_half.py", "test_name": "test_proof_2",
             "status": "pass", "tier": "unit"},
        ])

        plugin_path = os.path.join(PROJECT_ROOT, 'scripts', 'proof')
        with open(os.path.join(self.project_root, 'conftest.py'), 'w') as f:
            f.write(
                'import sys\n'
                f'sys.path.insert(0, r"{plugin_path}")\n'
                'from pytest_purlin import pytest_configure  # noqa\n'
            )
        result = subprocess.run(
            ['python3', '-m', 'pytest', 'test_first_half.py', '-q'],
            cwd=self.project_root, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

        proof_path = os.path.join(self.project_root, 'specs', 'test',
                                  'feat_split.proofs-unit.json')
        with open(proof_path) as f:
            entries = json.load(f)['proofs']
        by_file = {e['test_file']: e for e in entries}

        assert 'test_second_half.py' in by_file, (
            "the test file this run did not execute must survive: the merge key includes "
            f"test_file. Got {entries}"
        )
        assert by_file['test_second_half.py']['test_name'] == 'test_proof_2', \
            "the untouched entry must be carried over verbatim"
        assert by_file['test_first_half.py']['status'] == 'pass', \
            "the re-run file's entry must be replaced with the fresh result"
        assert by_file['test_first_half.py']['test_name'] == 'test_proof_1', \
            "the re-run file's stale test_name must be replaced"
        assert len(entries) == 2, f"expected exactly 2 entries, got {entries}"


class TestScopedProofFiles(TestProofFormatEnforcement):
    """RULE-5 in a scoped file and RULE-8 discovery. Inherits the tmp project
    fixture; the parent's tests are not re-run here."""

    test_proof_file_read_by_sync_status = None
    test_proof_entry_has_all_seven_fields = None
    test_invalid_status_not_counted = None
    test_feature_scoped_overwrite = None
    test_merge_key_includes_test_file = None

    _SEVEN = {'feature', 'id', 'rule', 'test_file', 'test_name', 'status', 'tier'}

    def _write_scoped(self, name, platform, proofs, tier='unit', subdir='test'):
        d = os.path.join(self.project_root, 'specs', subdir)
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f'{name}.proofs-{tier}@{platform}.json')
        with open(path, 'w') as f:
            json.dump({"tier": tier, "platform": platform, "proofs": proofs}, f)
        return path

    def _conftest(self):
        plugin_path = os.path.join(PROJECT_ROOT, 'scripts', 'proof')
        with open(os.path.join(self.project_root, 'conftest.py'), 'w') as f:
            f.write('import sys\n'
                    f'sys.path.insert(0, r"{plugin_path}")\n'
                    'from pytest_purlin import pytest_configure  # noqa\n')

    def _pytest(self, *files, platform='p1'):
        import subprocess
        env = dict(os.environ, PURLIN_PLATFORM=platform)
        result = subprocess.run(['python3', '-m', 'pytest', *files, '-q', '-p', 'no:cacheprovider'],
                                cwd=self.project_root, capture_output=True, text=True, env=env)
        assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"

    @pytest.mark.proof("schema_proof_format", "PROOF-5", "RULE-5")
    def test_scoped_file_merge_preserves_other_feature_and_leaves_agnostic_file_alone(self):
        self._write_spec('feat_a', (
            '# Feature: feat_a\n\n## What it does\nA.\n\n'
            '## Rules\n- RULE-1: Must work\n\n## Proof\n- PROOF-1 (RULE-1): Test @unit @on(p1)\n'
        ))
        seed_b = {"feature": "feat_b", "id": "PROOF-1", "rule": "RULE-1",
                  "test_file": "t.py", "test_name": "t_b", "status": "pass", "tier": "unit"}
        scoped = self._write_scoped('feat_a', 'p1', [dict(seed_b, platform='p1')])
        self._write_proofs('feat_a', [seed_b])
        agnostic = os.path.join(self.project_root, 'specs', 'test', 'feat_a.proofs-unit.json')
        before = open(agnostic, 'rb').read()

        with open(os.path.join(self.project_root, 'test_feat_a.py'), 'w') as f:
            f.write('import pytest\n'
                    '@pytest.mark.proof("feat_a", "PROOF-1", "RULE-1", platforms=("p1",))\n'
                    'def test_a():\n    assert True\n')
        self._conftest()
        self._pytest('test_feat_a.py', platform='p1')

        data = json.load(open(scoped))
        assert data['platform'] == 'p1'
        by_feature = {p['feature']: p for p in data['proofs']}
        assert by_feature['feat_b']['test_name'] == 't_b', "feat_b must survive in the scoped file"
        assert by_feature['feat_a']['test_file'] == 'test_feat_a.py'
        assert all(p['platform'] == 'p1' and set(p) == self._SEVEN | {'platform'} for p in data['proofs']), data
        assert open(agnostic, 'rb').read() == before, (
            "a run that wrote only the scoped file must not touch the agnostic file")

    @pytest.mark.proof("schema_proof_format", "PROOF-8", "RULE-5")
    def test_scoped_file_merge_key_includes_test_file(self):
        self._write_spec('feat_split', (
            '# Feature: feat_split\n\n## What it does\nSplit.\n\n'
            '## Rules\n- RULE-1: a\n- RULE-2: b\n\n'
            '## Proof\n- PROOF-1 (RULE-1): Test @on(p1)\n- PROOF-2 (RULE-2): Test @on(p1)\n'
        ))
        for name, pid, rid in (('test_first_half.py', 'PROOF-1', 'RULE-1'),
                               ('test_second_half.py', 'PROOF-2', 'RULE-2')):
            with open(os.path.join(self.project_root, name), 'w') as f:
                f.write('import pytest\n'
                        f'@pytest.mark.proof("feat_split", "{pid}", "{rid}", platforms=("p1",))\n'
                        f'def test_{pid.lower().replace("-", "_")}():\n    assert True\n')
        scoped = self._write_scoped('feat_split', 'p1', [
            {"feature": "feat_split", "id": "PROOF-1", "rule": "RULE-1",
             "test_file": "test_first_half.py", "test_name": "stale_name",
             "status": "fail", "tier": "unit", "platform": "p1"},
            {"feature": "feat_split", "id": "PROOF-2", "rule": "RULE-2",
             "test_file": "test_second_half.py", "test_name": "test_proof_2",
             "status": "pass", "tier": "unit", "platform": "p1"},
        ])
        self._conftest()
        self._pytest('test_first_half.py', platform='p1')

        entries = json.load(open(scoped))['proofs']
        by_file = {e['test_file']: e for e in entries}
        assert by_file['test_second_half.py']['test_name'] == 'test_proof_2', entries
        assert by_file['test_first_half.py']['status'] == 'pass', entries
        assert by_file['test_first_half.py']['test_name'] == 'test_proof_1', entries
        assert len(entries) == 2, entries
        assert not os.path.exists(os.path.join(self.project_root, 'specs', 'test',
                                               'feat_split.proofs-unit.json')), (
            "declared markers write no agnostic file")

    @pytest.mark.proof("schema_proof_format", "PROOF-9", "RULE-8")
    def test_discovery_stamps_platform_skips_bad_ids_and_aliases_legacy_files(self):
        import inspect
        sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'audit'))
        import static_checks
        assert inspect.getsource(purlin_server._proof_file_parts) == \
            inspect.getsource(static_checks._proof_file_parts)
        assert purlin_server._PROOF_FILE_RE.pattern == static_checks._PROOF_FILE_RE.pattern

        spec = ('# Feature: {n}\n\n## What it does\nX.\n\n## Rules\n- RULE-1: r\n\n'
                '## Proof\n- PROOF-1 (RULE-1): t\n')
        self._write_spec('foo', spec.format(n='foo'))
        self._write_spec('bar', spec.format(n='bar'))
        entry = lambda feat, tf: {"feature": feat, "id": "PROOF-1", "rule": "RULE-1",
                                  "test_file": tf, "test_name": "t", "status": "pass", "tier": "unit"}
        self._write_proofs('foo', [entry('foo', 'agnostic.py')])
        self._write_scoped('foo', 'ok-1', [dict(entry('foo', 'scoped.py'), platform='ok-1')])
        d = os.path.join(self.project_root, 'specs', 'test')
        with open(os.path.join(d, 'foo.proofs-unit@Bad_Id.json'), 'w') as f:
            json.dump({"tier": "unit", "platform": "Bad_Id",
                       "proofs": [dict(entry('foo', 'bad.py'), platform='Bad_Id')]}, f)
        with open(os.path.join(d, 'bar.proofs-windows.json'), 'w') as f:
            json.dump({"tier": "windows", "proofs": [dict(entry('bar', 'legacy.py'), tier='windows')]}, f)

        legacy = []
        read = purlin_server._read_proofs(self.project_root, legacy=legacy)
        by_file = {e['test_file']: e for e in read['foo']}
        assert by_file['agnostic.py']['platform'] is None
        assert by_file['scoped.py']['platform'] == 'ok-1'
        assert 'bad.py' not in by_file, "a suffix outside the id charset must not be read"
        assert [(e['tier'], e['platform']) for e in read['bar']] == [('unit', 'windows')]
        assert legacy == ['specs/test/bar.proofs-windows.json']

        out = purlin_server.sync_status(self.project_root)
        assert 'specs/test/bar.proofs-windows.json' in out, out
        assert 'read as unit@windows' in out and 'bar.proofs-unit@windows.json' in out, out
        assert 'legacy-proof-file' in out, out
        assert out.count('\u2192 Run: purlin:init --update') == 1, out
        assert 'bar: PASSING' in out or 'bar: VERIFIED' in out, out

        os.remove(os.path.join(d, 'bar.proofs-windows.json'))
        legacy2 = []
        purlin_server._read_proofs(self.project_root, legacy=legacy2)
        assert legacy2 == []
        out2 = purlin_server.sync_status(self.project_root)
        assert 'read as unit@windows' not in out2, out2
        assert 'legacy-proof-file' not in out2, out2


class TestProofFormatConventions:

    @pytest.mark.proof("schema_proof_format", "PROOF-4", "RULE-4")
    def test_standard_tiers_documented(self):
        """RULE-4: the tier vocabulary is unit, integration, e2e; nothing is
        runner-gated by tier. A committed legacy `<feature>.proofs-windows.json`
        is tolerated for one release only through the server's alias, which
        reads it as unit@windows; every `@` suffix is a platform id."""
        valid_tiers = {'unit', 'integration', 'e2e'}
        proof_files = sorted(glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**',
                                                    '*.proofs-*.json'), recursive=True))
        assert len(proof_files) > 0, "No proof files found"
        legacy = []
        for path in proof_files:
            parts = purlin_server._proof_file_parts(os.path.basename(path))
            assert parts is not None, f"{path} matches no proof-file pattern"
            _stem, file_tier, platform, is_legacy = parts
            assert file_tier in valid_tiers, f"Invalid tier '{file_tier}' in the name of {path}"
            if platform is not None:
                assert purlin_server._PLATFORM_ID_RE.match(platform), (
                    f"the @ suffix of {path} is not a platform id")
            with open(path) as f:
                data = json.load(f)
            if is_legacy:
                legacy.append(os.path.relpath(path, PROJECT_ROOT))
                continue
            assert data.get('tier') == file_tier, (
                f"top-level tier {data.get('tier')!r} disagrees with the filename of {path}")
            assert data.get('platform') == platform, (
                f"top-level platform {data.get('platform')!r} disagrees with the filename of {path}")
            for entry in data.get('proofs', []):
                assert entry.get('tier') == file_tier, (
                    f"Invalid entry tier '{entry.get('tier')}' in {entry.get('id')} of {path}")
                assert entry.get('platform') == platform, (
                    f"entry platform {entry.get('platform')!r} in {entry.get('id')} of {path}")

        # The legacy file is read through the alias as unit@windows, on every entry.
        read = purlin_server._read_proofs(PROJECT_ROOT)
        for rel in legacy:
            with open(os.path.join(PROJECT_ROOT, rel)) as f:
                ids = {e['id'] for e in json.load(f)['proofs']}
            stem = os.path.basename(rel).split('.proofs-')[0]
            seen = [e for e in read.get(stem, []) if e['id'] in ids]
            assert seen and all(e['tier'] == 'unit' and e['platform'] == 'windows' for e in seen), (
                f"{rel} must be read as unit@windows, got "
                f"{[(e['id'], e['tier'], e['platform']) for e in seen]}")

        # Verify the spec format documents the tiers and the platform tag.
        with open(os.path.join(PROJECT_ROOT, 'references', 'formats',
                               'spec_format.md')) as f:
            fmt = f.read()
        assert '@integration' in fmt
        assert '@e2e' in fmt
        assert '@on(' in fmt

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
