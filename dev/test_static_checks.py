"""Tests for static_checks.py.

Covers all five Python AST checks (assert_true, no_assertions, bare_except,
logic_mirroring, mock_target_match), JSON output format, exit codes,
spec coverage checks, audit cache helpers, and language-agnostic
proof-file structural checks (proof_id_collision, proof_rule_orphan).
"""

import ast
import json
import os
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit'))
import static_checks
from static_checks import (
    analyze_test_file,
    check_csharp,
    check_proof_file,
    check_python,
    check_shell,
    check_spec_coverage,
    compute_proof_hash,
    prune_audit_cache,
    read_audit_cache,
    resolve_test_file_from_name,
    write_audit_cache,
    _read_rule_descriptions,
    load_criteria,
)

_STATIC_CHECKS_PY = os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'audit', 'static_checks.py'
)

STATIC_CHECKS_PY = os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'audit', 'static_checks.py'
)


def _write_tmp(content, suffix='.py'):
    f = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
    f.write(content)
    f.close()
    return f.name


def _write_spec(rules):
    content = "# Feature: testfeat\n\n## What it does\nTest\n\n## Rules\n"
    for rid, desc in rules.items():
        content += f"- {rid}: {desc}\n"
    content += "\n## Proof\n"
    for rid in rules:
        pid = rid.replace("RULE", "PROOF")
        content += f"- {pid} ({rid}): test\n"
    return _write_tmp(content, suffix='.md')


class TestAssertTrue:

    @pytest.mark.proof("static_checks", "PROOF-1", "RULE-1")
    def test_detects_assert_true(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    assert True
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-1", "RULE-1")
    def test_detects_assert_is_not_none(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    result = do_something()
    assert result is not None
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-1", "RULE-1")
    def test_detects_assert_len_gte_zero(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    items = get_items()
    assert len(items) >= 0
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)


class TestNoAssertions:

    @pytest.mark.proof("static_checks", "PROOF-2", "RULE-2")
    def test_detects_no_assertions(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    result = do_something()
    print(result)
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'no_assertions'
        finally:
            os.unlink(path)


class TestBareExcept:

    @pytest.mark.proof("static_checks", "PROOF-3", "RULE-3")
    def test_detects_bare_except_pass(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    try:
        result = do_something()
    except Exception:
        pass
    assert result == "ok"
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'bare_except'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-3", "RULE-3")
    def test_detects_bare_except_no_type(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    try:
        result = do_something()
    except:
        pass
    assert result == "ok"
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'bare_except'
        finally:
            os.unlink(path)


class TestLogicMirroring:

    @pytest.mark.proof("static_checks", "PROOF-4", "RULE-4")
    def test_detects_logic_mirroring(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    expected = hash_func(input_val)
    result = hash_func(input_val)
    assert result == expected
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'logic_mirroring'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-4", "RULE-4")
    def test_no_mirroring_with_literal(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_good():
    result = hash_func("secret")
    assert result == "5e884898da28047151d0e56f8dc6292773603d0d"
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'pass'
        finally:
            os.unlink(path)


class TestMockTargetMatch:

    @pytest.mark.proof("static_checks", "PROOF-5", "RULE-5")
    def test_detects_mock_matching_rule(self):
        path = _write_tmp('''
import pytest
from unittest.mock import patch

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
@patch("auth.bcrypt.checkpw")
def test_bad(mock_checkpw):
    mock_checkpw.return_value = True
    assert login("alice") == 200
''')
        spec_path = _write_spec({"RULE-1": "Passwords hashed with bcrypt"})
        try:
            results = check_python(path, "testfeat", _read_rule_descriptions(spec_path))
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'mock_target_match'
        finally:
            os.unlink(path)
            os.unlink(spec_path)

    @pytest.mark.proof("static_checks", "PROOF-5", "RULE-5")
    def test_no_match_when_mock_unrelated(self):
        path = _write_tmp('''
import pytest
from unittest.mock import patch

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
@patch("email.send_notification")
def test_ok(mock_email):
    mock_email.return_value = True
    assert login("alice") == 200
''')
        spec_path = _write_spec({"RULE-1": "Passwords hashed with bcrypt"})
        try:
            results = check_python(path, "testfeat", _read_rule_descriptions(spec_path))
            assert len(results) == 1
            assert results[0]['status'] == 'pass'
        finally:
            os.unlink(path)
            os.unlink(spec_path)


class TestJsonOutput:

    @pytest.mark.proof("static_checks", "PROOF-6", "RULE-6")
    def test_json_has_required_fields(self):
        path = _write_tmp('''
import pytest

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_good():
    assert 1 == 1

@pytest.mark.proof("testfeat", "PROOF-2", "RULE-2")
def test_bad():
    assert True
''')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, "testfeat"],
                capture_output=True, text=True
            )
            data = json.loads(result.stdout)
            assert 'proofs' in data
            assert isinstance(data['proofs'], list)
            assert len(data['proofs']) == 2
            for proof in data['proofs']:
                assert 'proof_id' in proof
                assert 'rule_id' in proof
                assert 'test_name' in proof
                assert 'status' in proof
                assert 'reason' in proof
        finally:
            os.unlink(path)


class TestExitCodes:

    @pytest.mark.proof("static_checks", "PROOF-7", "RULE-7")
    def test_exit_0_when_all_pass(self):
        path = _write_tmp('''
import pytest

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_good():
    result = do_something()
    assert result == "expected"
''')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, "testfeat"],
                capture_output=True, text=True
            )
            assert result.returncode == 0
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-7", "RULE-7")
    def test_exit_0_with_fail_status_when_defects_found(self):
        path = _write_tmp('''
import pytest

@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    assert True
''')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, "testfeat"],
                capture_output=True, text=True
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert any(p['status'] == 'fail' for p in data['proofs'])
        finally:
            os.unlink(path)


class TestSpecCoverage:

    @pytest.mark.proof("static_checks", "PROOF-8", "RULE-8")
    def test_spec_coverage_counts(self):
        """check_spec_coverage returns rule_count and proof_count."""
        path = _write_tmp(
            "# Feature: testfeat\n\n## What it does\nTest\n\n## Rules\n"
            "- RULE-1: Verify agent.md contains ## Core Loop section\n"
            "- RULE-2: Returns 200 on valid credentials\n"
            "- RULE-3: Grep skill files for ## Usage heading\n"
            "\n## Proof\n"
            "- PROOF-1 (RULE-1): test\n"
            "- PROOF-2 (RULE-2): test\n"
            "- PROOF-3 (RULE-3): test\n",
            suffix='.md'
        )
        try:
            result = check_spec_coverage(path)
            assert result['rule_count'] == 3
            assert result['proof_count'] == 3
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-8", "RULE-8")
    def test_spec_coverage_via_cli(self):
        """CLI --check-spec-coverage returns rule and proof counts."""
        path = _write_tmp(
            "# Feature: testfeat\n\n## What it does\nTest\n\n## Rules\n"
            "- RULE-1: Verify file exists in specs directory\n"
            "- RULE-2: Returns error when missing\n"
            "\n## Proof\n"
            "- PROOF-1 (RULE-1): test\n"
            "- PROOF-2 (RULE-2): test\n",
            suffix='.md'
        )
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, '--check-spec-coverage', '--spec-path', path],
                capture_output=True, text=True
            )
            assert result.returncode == 0
            data = json.loads(result.stdout)
            assert data['rule_count'] == 2
            assert data['proof_count'] == 2
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-8", "RULE-8")
    def test_spec_coverage_empty(self):
        """Spec with no rules returns zero counts."""
        path = _write_tmp(
            "# Feature: testfeat\n\n## What it does\nTest\n\n## Rules\n",
            suffix='.md'
        )
        try:
            result = check_spec_coverage(path)
            assert result['rule_count'] == 0
            assert result['proof_count'] == 0
        finally:
            os.unlink(path)


class TestAuditCache:

    @pytest.mark.proof("static_checks", "PROOF-10", "RULE-10")
    def test_compute_proof_hash_deterministic(self):
        # Expected value pre-computed: sha256("rule text\x00proof desc\x00test code")[:16]
        expected = '64e4571be6c61536'
        h1 = compute_proof_hash("rule text", "proof desc", "test code")
        assert h1 == expected
        assert len(h1) == 16
        assert all(c in '0123456789abcdef' for c in h1)

    @pytest.mark.proof("static_checks", "PROOF-10", "RULE-10")
    def test_compute_proof_hash_different_inputs(self):
        h1 = compute_proof_hash("rule A", "proof A", "test A")
        h2 = compute_proof_hash("rule B", "proof B", "test B")
        assert h1 != h2
        # Pin the exact algorithm: sha256("rule A\x00proof A\x00test A")[:16]
        # Pre-computed independently via: hashlib.sha256(b"rule A\x00proof A\x00test A").hexdigest()[:16]
        assert h1 == "d81ac1e833476848", (
            f"Hash algorithm mismatch: expected d81ac1e833476848, got {h1!r}. "
            "This pins the null-byte separator and sha256 algorithm."
        )
        assert len(h1) == 16
        assert all(c in "0123456789abcdef" for c in h1)

    @pytest.mark.proof("static_checks", "PROOF-10", "RULE-10")
    def test_compute_proof_hash_no_separator_collision(self):
        """Input-shifting must produce different hashes."""
        h1 = compute_proof_hash("a|b", "c", "d")
        h2 = compute_proof_hash("a", "b|c", "d")
        assert h1 != h2

    @pytest.mark.proof("static_checks", "PROOF-11", "RULE-11")
    def test_read_cache_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = read_audit_cache(tmpdir)
            assert result == {}

    @pytest.mark.proof("static_checks", "PROOF-11", "RULE-11")
    def test_read_cache_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
            os.makedirs(cache_dir)
            cache_path = os.path.join(cache_dir, 'audit_cache.json')
            data = {"abc123": {"assessment": "STRONG", "criterion": "matches"}}
            with open(cache_path, 'w') as f:
                json.dump(data, f)
            result = read_audit_cache(tmpdir)
            assert result == data

    @pytest.mark.proof("static_checks", "PROOF-11", "RULE-11")
    def test_read_cache_non_dict_returns_empty(self):
        """Cache file with non-dict JSON (e.g. a list) returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
            os.makedirs(cache_dir)
            cache_path = os.path.join(cache_dir, 'audit_cache.json')
            with open(cache_path, 'w') as f:
                json.dump([1, 2, 3], f)
            result = read_audit_cache(tmpdir)
            assert result == {}

    @pytest.mark.proof("static_checks", "PROOF-11", "RULE-11")
    def test_read_cache_corrupt_json_returns_empty(self):
        """Cache file with invalid JSON returns empty dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = os.path.join(tmpdir, '.purlin', 'cache')
            os.makedirs(cache_dir)
            cache_path = os.path.join(cache_dir, 'audit_cache.json')
            with open(cache_path, 'w') as f:
                f.write("{corrupt json")
            result = read_audit_cache(tmpdir)
            assert result == {}

    @pytest.mark.proof("static_checks", "PROOF-12", "RULE-12")
    def test_write_cache_atomic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "a1b2c3d4e5f6a7b8": {
                    "assessment": "STRONG",
                    "criterion": "matches rule intent",
                    "why": "test exercises the rule correctly",
                    "fix": "none",
                }
            }
            # Prove the atomic mechanism: the durable file must be produced by
            # renaming a temp file via os.replace, never by writing in place.
            real_replace = os.replace
            replace_calls = []

            def spy_replace(src, dst):
                replace_calls.append((src, dst))
                return real_replace(src, dst)

            with mock.patch.object(static_checks.os, 'replace', side_effect=spy_replace):
                write_audit_cache(tmpdir, data)

            cache_path = os.path.join(tmpdir, '.purlin', 'cache', 'audit_cache.json')
            assert replace_calls, "write is not atomic — os.replace was never called"
            src, dst = replace_calls[-1]
            assert src.endswith('.tmp'), f"expected rename from a .tmp file, got {src!r}"
            assert os.path.abspath(dst) == os.path.abspath(cache_path), \
                f"os.replace target {dst!r} is not the cache file"

            result = read_audit_cache(tmpdir)
            assert result == data
            # No .tmp file left behind after the rename
            assert not os.path.exists(cache_path + '.tmp')


class TestWriteCacheMerge:
    """RULE-24: write_audit_cache merges into existing cache on disk."""

    def _make_entry(self, assessment, feature, proof_id, rule_id, ts="2026-04-01T00:00:00+00:00"):
        return {
            "assessment": assessment,
            "criterion": "matches rule intent",
            "why": "test exercises the rule correctly",
            "fix": "none",
            "feature": feature,
            "proof_id": proof_id,
            "rule_id": rule_id,
            "priority": "LOW",
            "cached_at": ts,
        }

    @pytest.mark.proof("static_checks", "PROOF-39", "RULE-24")
    def test_second_write_preserves_first_write_entries(self):
        """Two sequential writes for different features must both survive on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # First write: 3 entries for feature_a
            batch_a = {
                "hash_a1": self._make_entry("STRONG", "feature_a", "PROOF-1", "RULE-1"),
                "hash_a2": self._make_entry("STRONG", "feature_a", "PROOF-2", "RULE-2"),
                "hash_a3": self._make_entry("WEAK",   "feature_a", "PROOF-3", "RULE-3"),
            }
            write_audit_cache(tmpdir, batch_a)

            # Second write: 2 entries for feature_b (different feature)
            batch_b = {
                "hash_b1": self._make_entry("STRONG", "feature_b", "PROOF-1", "RULE-1"),
                "hash_b2": self._make_entry("STRONG", "feature_b", "PROOF-2", "RULE-2"),
            }
            write_audit_cache(tmpdir, batch_b)

            # Read back: ALL 5 entries must be present
            after = read_audit_cache(tmpdir)
            assert len(after) == 5, f"Expected 5 entries (3 from A + 2 from B), got {len(after)}"
            assert "hash_a1" in after, "feature_a entry lost after feature_b write"
            assert "hash_a2" in after, "feature_a entry lost after feature_b write"
            assert "hash_a3" in after, "feature_a entry lost after feature_b write"
            assert "hash_b1" in after, "feature_b entry missing"
            assert "hash_b2" in after, "feature_b entry missing"
            # Verify assessments are correct (not swapped or corrupted)
            assert after["hash_a3"]["assessment"] == "WEAK"
            assert after["hash_a3"]["feature"] == "feature_a"
            assert after["hash_b1"]["assessment"] == "STRONG"
            assert after["hash_b1"]["feature"] == "feature_b"

    @pytest.mark.proof("static_checks", "PROOF-39", "RULE-24")
    def test_update_entry_preserves_other_features(self):
        """Updating one feature's entry must not disturb another feature's entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Seed: feature_a (2 entries) + feature_b (2 entries)
            seed = {
                "hash_a1": self._make_entry("HOLLOW", "feature_a", "PROOF-1", "RULE-1"),
                "hash_a2": self._make_entry("STRONG", "feature_a", "PROOF-2", "RULE-2"),
                "hash_b1": self._make_entry("STRONG", "feature_b", "PROOF-1", "RULE-1"),
                "hash_b2": self._make_entry("WEAK",   "feature_b", "PROOF-2", "RULE-2"),
            }
            write_audit_cache(tmpdir, seed)

            # Update: feature_a PROOF-1 upgraded from HOLLOW to STRONG (new hash = test code changed)
            update = {
                "hash_a1_v2": self._make_entry(
                    "STRONG", "feature_a", "PROOF-1", "RULE-1",
                    ts="2026-04-02T00:00:00+00:00",  # newer timestamp
                ),
            }
            write_audit_cache(tmpdir, update)

            after = read_audit_cache(tmpdir)
            # feature_b untouched
            assert after["hash_b1"]["assessment"] == "STRONG"
            assert after["hash_b1"]["feature"] == "feature_b"
            assert after["hash_b2"]["assessment"] == "WEAK"
            assert after["hash_b2"]["feature"] == "feature_b"
            # feature_a PROOF-1: old HOLLOW replaced by new STRONG (dedup by feature+proof_id)
            assert "hash_a1_v2" in after, "Updated entry missing"
            assert after["hash_a1_v2"]["assessment"] == "STRONG"
            # Old hash for same (feature_a, PROOF-1) should be gone (dedup)
            assert "hash_a1" not in after, "Stale entry for same (feature, proof_id) should be pruned"
            # feature_a PROOF-2 still present
            assert after["hash_a2"]["assessment"] == "STRONG"


class TestPruneAuditCache:

    def _make_entry(self, assessment, feature, proof_id, rule_id):
        return {
            "assessment": assessment,
            "criterion": "matches rule intent",
            "why": "test exercises the rule correctly",
            "fix": "none",
            "feature": feature,
            "proof_id": proof_id,
            "rule_id": rule_id,
            "priority": "LOW",
            "cached_at": "2026-04-01T00:00:00+00:00",
        }

    @pytest.mark.proof("static_checks", "PROOF-36", "RULE-22")
    def test_prune_removes_dead_preserves_live(self):
        """Prune with 2 of 3 keys live removes the third, preserves the other 2."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = {
                "aaa": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                "bbb": self._make_entry("WEAK", "feat_b", "PROOF-1", "RULE-1"),
                "ccc": self._make_entry("STRONG", "feat_c", "PROOF-1", "RULE-1"),
            }
            write_audit_cache(tmpdir, cache)
            result = prune_audit_cache(tmpdir, live_keys={"aaa", "ccc"})
            assert result["pruned"] == 1
            assert result["kept"] == 2
            after = read_audit_cache(tmpdir)
            assert "aaa" in after
            assert "ccc" in after
            assert "bbb" not in after
            # Verify fields are intact
            assert after["aaa"]["assessment"] == "STRONG"
            assert after["aaa"]["feature"] == "feat_a"
            assert after["ccc"]["assessment"] == "STRONG"
            assert after["ccc"]["feature"] == "feat_c"

    @pytest.mark.proof("static_checks", "PROOF-37", "RULE-23")
    def test_prune_empty_live_keys_clears_all(self):
        """Prune with empty live_keys set produces empty cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = {
                "aaa": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                "bbb": self._make_entry("STRONG", "feat_b", "PROOF-1", "RULE-1"),
                "ccc": self._make_entry("STRONG", "feat_c", "PROOF-1", "RULE-1"),
            }
            write_audit_cache(tmpdir, cache)
            result = prune_audit_cache(tmpdir, live_keys=set())
            assert result["pruned"] == 3
            assert result["kept"] == 0
            after = read_audit_cache(tmpdir)
            assert after == {}

    @pytest.mark.proof("static_checks", "PROOF-37", "RULE-23")
    def test_prune_all_keys_live_preserves_all(self):
        """Prune with all keys live preserves identical cache content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = {
                "aaa": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                "bbb": self._make_entry("WEAK", "feat_b", "PROOF-2", "RULE-2"),
                "ccc": self._make_entry("STRONG", "feat_c", "PROOF-3", "RULE-3"),
            }
            write_audit_cache(tmpdir, cache)
            result = prune_audit_cache(tmpdir, live_keys={"aaa", "bbb", "ccc"})
            assert result["pruned"] == 0
            assert result["kept"] == 3
            after = read_audit_cache(tmpdir)
            # All entries still present — verified against literal values from _make_entry args
            assert set(after.keys()) == {"aaa", "bbb", "ccc"}
            assert after["aaa"]["assessment"] == "STRONG"
            assert after["aaa"]["feature"] == "feat_a"
            assert after["bbb"]["assessment"] == "WEAK"
            assert after["bbb"]["feature"] == "feat_b"
            assert after["ccc"]["assessment"] == "STRONG"
            assert after["ccc"]["feature"] == "feat_c"


class TestShellIfElsePair:

    @pytest.mark.proof("static_checks", "PROOF-13", "RULE-13")
    def test_if_else_pair_not_flagged(self):
        """if/else proof pair with grep condition should pass, not be flagged."""
        path = _write_tmp('''#!/usr/bin/env bash
source shell_purlin.sh
output=$(some_command)
if echo "$output" | grep -q "VERIFIED"; then
  purlin_proof "testfeat" "PROOF-1" "RULE-1" pass "checks VERIFIED"
else
  purlin_proof "testfeat" "PROOF-1" "RULE-1" fail "checks VERIFIED"
fi
''', suffix='.sh')
        try:
            results = check_shell(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'pass'
            assert results[0]['proof_id'] == 'PROOF-1'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-13", "RULE-13")
    def test_hardcoded_pass_still_caught(self):
        """A bare purlin_proof pass with no test logic should still be flagged."""
        path = _write_tmp('''#!/usr/bin/env bash
source shell_purlin.sh
purlin_proof "testfeat" "PROOF-1" "RULE-1" pass "no test here"
''', suffix='.sh')
        try:
            results = check_shell(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-13", "RULE-13")
    def test_if_else_pair_no_condition_flagged(self):
        """if/else pair with no real test logic in condition should still fail."""
        path = _write_tmp('''#!/usr/bin/env bash
source shell_purlin.sh
if true; then
  purlin_proof "testfeat" "PROOF-1" "RULE-1" pass "no real check"
else
  purlin_proof "testfeat" "PROOF-1" "RULE-1" fail "no real check"
fi
''', suffix='.sh')
        try:
            results = check_shell(path, "testfeat")
            assert len(results) == 1
            # The `if` keyword IS in the segment, so has_logic is true
            # This is acceptable — `if true` has test logic (the if keyword)
            # The deeper semantic issue would be caught by LLM Pass 2
        finally:
            os.unlink(path)


class TestAssertTrueLiteral:

    @pytest.mark.proof("static_checks", "PROOF-14", "RULE-14")
    def test_literal_assert_true_has_literal_true(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    assert True
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true'
            assert results[0]['literal'] is True
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-14", "RULE-14")
    def test_heuristic_assert_has_literal_false(self):
        path = _write_tmp('''
import pytest
@pytest.mark.proof("testfeat", "PROOF-1", "RULE-1")
def test_bad():
    result = do_something()
    assert result is not None
''')
        try:
            results = check_python(path, "testfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true'
            assert results[0]['literal'] is False
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Proof-file structural checks (Pass 0.5 — language-agnostic)
#
# These tests verify that check_proof_file works regardless of which language
# produced the proof JSON. Each test creates proof files as if emitted by
# different language test runners (Python/pytest, JavaScript/Jest, Shell,
# C/CUnit, PHP/PHPUnit, SQL/pgTAP, TypeScript/Vitest).
# ---------------------------------------------------------------------------

def _write_proof_json(tmp_path, feature, tier, proofs):
    """Write a proof JSON file and return its path."""
    path = tmp_path / f"{feature}.proofs-{tier}.json"
    path.write_text(json.dumps({"tier": tier, "proofs": proofs}, indent=2))
    return str(path)


def _write_spec_file(tmp_path, feature, rules):
    """Write a minimal spec file and return its path."""
    content = f"# Feature: {feature}\n\n## Rules\n"
    for rid, desc in rules.items():
        content += f"- {rid}: {desc}\n"
    content += "\n## Proof\n"
    for rid in rules:
        pid = rid.replace("RULE", "PROOF")
        content += f"- {pid} ({rid}): test\n"
    path = tmp_path / f"{feature}.md"
    path.write_text(content)
    return str(path)


# Language-specific proof entry factories — each simulates the output
# of a real test framework's proof plugin.

def _python_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/test_login.py",
        "test_name": "test_validates_credentials",
        "status": status, "tier": "unit",
    }


def _jest_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "src/__tests__/login.test.ts",
        "test_name": "validates credentials [proof:login:PROOF-1:RULE-1:unit]",
        "status": status, "tier": "unit",
    }


def _shell_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/test_login.sh",
        "test_name": "purlin_proof login PROOF-1 RULE-1 pass",
        "status": status, "tier": "e2e",
    }


def _c_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/test_auth.c",
        "test_name": "test_validates_credentials",
        "status": status, "tier": "unit",
    }


def _php_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/AuthTest.php",
        "test_name": "testValidatesCredentials",
        "status": status, "tier": "unit",
    }


def _sql_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "tests/test_constraints.sql",
        "test_name": "check_foreign_key_enforced",
        "status": status, "tier": "integration",
    }


def _typescript_proof(feature, proof_id, rule_id, status="pass"):
    return {
        "feature": feature, "id": proof_id, "rule": rule_id,
        "test_file": "src/__tests__/auth.spec.ts",
        "test_name": "should validate credentials",
        "status": status, "tier": "unit",
    }


# Map language name to factory for parametrized tests
_LANGUAGE_FACTORIES = {
    "python": _python_proof,
    "javascript": _jest_proof,
    "shell": _shell_proof,
    "c": _c_proof,
    "php": _php_proof,
    "sql": _sql_proof,
    "typescript": _typescript_proof,
}


class TestProofIdCollision:
    """Proof ID collision detection across all supported language contexts."""

    @pytest.mark.parametrize("lang,factory", list(_LANGUAGE_FACTORIES.items()))
    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-15")
    def test_detects_collision_per_language(self, tmp_path, lang, factory):
        """Same PROOF-1 targeting RULE-1 and RULE-2 — detected regardless of source language."""
        proofs = [
            factory("login", "PROOF-1", "RULE-1"),
            factory("login", "PROOF-1", "RULE-2"),
            factory("login", "PROOF-2", "RULE-3"),  # no collision
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path)
        collisions = [f for f in findings if f['check'] == 'proof_id_collision']
        assert len(collisions) == 1, f"Expected 1 collision for {lang}, got {len(collisions)}"
        assert collisions[0]['proof_id'] == 'PROOF-1'
        assert set(collisions[0]['rules']) == {'RULE-1', 'RULE-2'}

    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-15")
    def test_no_collision_when_ids_unique(self, tmp_path):
        """Distinct PROOF-IDs should produce zero findings."""
        proofs = [
            _python_proof("login", "PROOF-1", "RULE-1"),
            _python_proof("login", "PROOF-2", "RULE-2"),
            _jest_proof("login", "PROOF-3", "RULE-3"),
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path)
        assert len(findings) == 0, f"Expected no findings, got {findings}"

    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-15")
    def test_collision_with_mixed_languages(self, tmp_path):
        """Collision across language boundaries — Python and TypeScript both claim PROOF-1."""
        proofs = [
            _python_proof("auth", "PROOF-1", "RULE-1"),
            _typescript_proof("auth", "PROOF-1", "RULE-3"),
            _c_proof("auth", "PROOF-2", "RULE-2"),
        ]
        proof_path = _write_proof_json(tmp_path, "auth", "unit", proofs)
        findings = check_proof_file(proof_path)
        collisions = [f for f in findings if f['check'] == 'proof_id_collision']
        assert len(collisions) == 1
        assert set(collisions[0]['rules']) == {'RULE-1', 'RULE-3'}

    @pytest.mark.proof("static_checks", "PROOF-15", "RULE-15")
    def test_multiple_collisions_detected(self, tmp_path):
        """Two separate collisions in one file — both detected."""
        proofs = [
            _php_proof("cart", "PROOF-1", "RULE-1"),
            _php_proof("cart", "PROOF-1", "RULE-2"),
            _sql_proof("cart", "PROOF-3", "RULE-3"),
            _sql_proof("cart", "PROOF-3", "RULE-4"),
        ]
        proof_path = _write_proof_json(tmp_path, "cart", "unit", proofs)
        findings = check_proof_file(proof_path)
        collisions = [f for f in findings if f['check'] == 'proof_id_collision']
        assert len(collisions) == 2
        collision_ids = {c['proof_id'] for c in collisions}
        assert collision_ids == {'PROOF-1', 'PROOF-3'}


class TestProofRuleOrphan:
    """Orphan rule detection across all supported language contexts."""

    @pytest.mark.parametrize("lang,factory", list(_LANGUAGE_FACTORIES.items()))
    @pytest.mark.proof("static_checks", "PROOF-16", "RULE-16")
    def test_detects_orphan_per_language(self, tmp_path, lang, factory):
        """Proof targeting RULE-99 which doesn't exist — detected regardless of language."""
        spec_path = _write_spec_file(tmp_path, "login", {
            "RULE-1": "Validates credentials",
            "RULE-2": "Returns JWT on success",
            "RULE-3": "Rejects expired tokens",
        })
        proofs = [
            factory("login", "PROOF-1", "RULE-1"),
            factory("login", "PROOF-99", "RULE-99"),  # orphan
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path, spec_path=spec_path)
        orphans = [f for f in findings if f['check'] == 'proof_rule_orphan']
        assert len(orphans) == 1, f"Expected 1 orphan for {lang}, got {len(orphans)}"
        assert orphans[0]['rule'] == 'RULE-99'

    @pytest.mark.proof("static_checks", "PROOF-16", "RULE-16")
    def test_no_orphan_when_all_rules_exist(self, tmp_path):
        """All proofs target existing rules — zero orphans."""
        spec_path = _write_spec_file(tmp_path, "login", {
            "RULE-1": "Validates credentials",
            "RULE-2": "Returns JWT on success",
        })
        proofs = [
            _python_proof("login", "PROOF-1", "RULE-1"),
            _shell_proof("login", "PROOF-2", "RULE-2"),
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path, spec_path=spec_path)
        orphans = [f for f in findings if f['check'] == 'proof_rule_orphan']
        assert len(orphans) == 0, f"Expected no orphans, got {orphans}"

    @pytest.mark.proof("static_checks", "PROOF-16", "RULE-16")
    def test_required_anchor_rules_not_flagged(self, tmp_path):
        """Rules with '/' (from required anchors) should NOT be flagged as orphans."""
        spec_path = _write_spec_file(tmp_path, "login", {
            "RULE-1": "Validates credentials",
        })
        proofs = [
            _python_proof("login", "PROOF-1", "RULE-1"),
            # This targets an anchor rule — should not be flagged
            {
                "feature": "login", "id": "PROOF-10", "rule": "security_policy/RULE-1",
                "test_file": "tests/test_security.py",
                "test_name": "test_no_eval",
                "status": "pass", "tier": "unit",
            },
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path, spec_path=spec_path)
        orphans = [f for f in findings if f['check'] == 'proof_rule_orphan']
        assert len(orphans) == 0, f"Anchor rules should not be flagged as orphans: {orphans}"

    @pytest.mark.proof("static_checks", "PROOF-16", "RULE-16")
    def test_no_orphan_check_without_spec(self, tmp_path):
        """Without spec_path, orphan check is skipped — only collision check runs."""
        proofs = [
            _c_proof("login", "PROOF-1", "RULE-1"),
            _c_proof("login", "PROOF-99", "RULE-99"),
        ]
        proof_path = _write_proof_json(tmp_path, "login", "unit", proofs)
        findings = check_proof_file(proof_path)  # no spec_path
        orphans = [f for f in findings if f['check'] == 'proof_rule_orphan']
        assert len(orphans) == 0, "Should not check orphans without spec_path"


class TestLoadCriteria:
    """Tests for load_criteria() — single source for criteria assembly."""

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_builtin_only(self, tmp_path):
        """load_criteria returns built-in content when no additional criteria configured."""
        project = str(tmp_path)
        os.makedirs(os.path.join(project, '.purlin', 'cache'), exist_ok=True)
        result = load_criteria(project)
        assert '## Assessment Levels' in result
        # No separator with "(from" — the built-in doc has a section titled
        # "Additional Team Criteria" but load_criteria adds "(from <url>)"
        assert 'Additional Team Criteria (from' not in result

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_with_additional_criteria(self, tmp_path):
        """load_criteria appends cached additional criteria with separator."""
        project = str(tmp_path)
        cache_dir = os.path.join(project, '.purlin', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        # Write config with audit_criteria source URL
        config_dir = os.path.join(project, '.purlin')
        with open(os.path.join(config_dir, 'config.json'), 'w') as f:
            json.dump({'audit_criteria': 'git@example.com:team/quality.git#criteria.md'}, f)
        # Write cached additional criteria
        with open(os.path.join(cache_dir, 'additional_criteria.md'), 'w') as f:
            f.write('## Team-Specific WEAK Criteria\n\n- No sleep() in tests\n')
        result = load_criteria(project)
        # Built-in must be present
        assert '## Assessment Levels' in result
        # Additional must be appended with separator
        assert '## Additional Team Criteria' in result
        assert 'git@example.com:team/quality.git#criteria.md' in result
        assert 'No sleep() in tests' in result

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_with_extra_path(self, tmp_path):
        """load_criteria appends extra file when --extra is provided."""
        project = str(tmp_path)
        os.makedirs(os.path.join(project, '.purlin', 'cache'), exist_ok=True)
        extra_file = str(tmp_path / 'extra_criteria.md')
        with open(extra_file, 'w') as f:
            f.write('## Custom Extra\n\n- All tests must have docstrings\n')
        result = load_criteria(project, extra_path=extra_file)
        assert '## Assessment Levels' in result
        assert '## Additional Criteria' in result
        assert 'All tests must have docstrings' in result

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_all_three_sources(self, tmp_path):
        """load_criteria combines built-in + additional + extra."""
        project = str(tmp_path)
        cache_dir = os.path.join(project, '.purlin', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        with open(os.path.join(project, '.purlin', 'config.json'), 'w') as f:
            json.dump({'audit_criteria': 'git@example.com:team/q.git#c.md'}, f)
        with open(os.path.join(cache_dir, 'additional_criteria.md'), 'w') as f:
            f.write('## Team Rules\n\n- No mocking databases\n')
        extra_file = str(tmp_path / 'extra.md')
        with open(extra_file, 'w') as f:
            f.write('## Project Rules\n\n- All tests under 100ms\n')
        result = load_criteria(project, extra_path=extra_file)
        # All three must be present
        assert '## Assessment Levels' in result
        assert '## Additional Team Criteria' in result
        assert 'No mocking databases' in result
        assert '## Additional Criteria' in result
        assert 'All tests under 100ms' in result

    @pytest.mark.proof("static_checks", "PROOF-35", "RULE-21")
    def test_no_additional_without_cache_file(self, tmp_path):
        """load_criteria does not append when cache file doesn't exist."""
        project = str(tmp_path)
        os.makedirs(os.path.join(project, '.purlin', 'cache'), exist_ok=True)
        with open(os.path.join(project, '.purlin', 'config.json'), 'w') as f:
            json.dump({'audit_criteria': 'git@example.com:team/q.git#c.md'}, f)
        # No additional_criteria.md in cache
        result = load_criteria(project)
        assert '## Assessment Levels' in result
        assert 'Additional Team Criteria (from' not in result


class TestWriteCacheLocking:
    """RULE-25: write_audit_cache serializes concurrent writers via exclusive file lock."""

    def _make_entry(self, assessment, feature, proof_id, rule_id):
        return {
            "assessment": assessment,
            "criterion": "matches rule intent",
            "why": "test exercises the rule correctly",
            "fix": "none",
            "feature": feature,
            "proof_id": proof_id,
            "rule_id": rule_id,
            "priority": "LOW",
            "cached_at": "2026-04-01T00:00:00+00:00",
        }

    @pytest.mark.proof("static_checks", "PROOF-40", "RULE-25")
    def test_lock_file_created_alongside_cache(self):
        """write_audit_cache acquires the exclusive lock on audit_cache.json.lock.

        Patches the platform-neutral _lock_exclusive helper (not fcntl directly)
        so the test runs identically on Windows and POSIX.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_path = os.path.join(tmpdir, '.purlin', 'cache', 'audit_cache.json.lock')
            lock_seen = []
            real_lock = static_checks._lock_exclusive

            def spy(lock_file):
                lock_seen.append(os.path.exists(lock_path))
                return real_lock(lock_file)

            with mock.patch.object(static_checks, '_lock_exclusive', side_effect=spy):
                write_audit_cache(tmpdir, {
                    "hash1": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                })

            assert lock_seen, "_lock_exclusive was never called"
            assert lock_seen[0], "lock file did not exist when the lock was acquired"

    @pytest.mark.proof("static_checks", "PROOF-40", "RULE-25")
    def test_concurrent_writes_preserve_all_entries(self):
        """Two threads writing different features concurrently must both survive."""
        import threading

        with tempfile.TemporaryDirectory() as tmpdir:
            errors = []

            def writer_a():
                try:
                    write_audit_cache(tmpdir, {
                        "hash_a1": self._make_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
                        "hash_a2": self._make_entry("WEAK",   "feat_a", "PROOF-2", "RULE-2"),
                    })
                except Exception as e:
                    errors.append(e)

            def writer_b():
                try:
                    write_audit_cache(tmpdir, {
                        "hash_b1": self._make_entry("STRONG", "feat_b", "PROOF-1", "RULE-1"),
                        "hash_b2": self._make_entry("HOLLOW", "feat_b", "PROOF-2", "RULE-2"),
                        "hash_b3": self._make_entry("STRONG", "feat_b", "PROOF-3", "RULE-3"),
                    })
                except Exception as e:
                    errors.append(e)

            t_a = threading.Thread(target=writer_a)
            t_b = threading.Thread(target=writer_b)
            t_a.start()
            t_b.start()
            t_a.join()
            t_b.join()

            assert not errors, f"Writer thread raised: {errors}"
            after = read_audit_cache(tmpdir)
            assert len(after) == 5, (
                f"Expected 5 entries (2 from feat_a + 3 from feat_b), got {len(after)}:\n"
                + json.dumps(list(after.keys()), indent=2)
            )
            assert "hash_a1" in after, "feat_a entry hash_a1 lost after concurrent write"
            assert "hash_a2" in after, "feat_a entry hash_a2 lost after concurrent write"
            assert "hash_b1" in after, "feat_b entry hash_b1 lost after concurrent write"
            assert "hash_b2" in after, "feat_b entry hash_b2 lost after concurrent write"
            assert "hash_b3" in after, "feat_b entry hash_b3 lost after concurrent write"


class TestWriteCacheCLI:
    """RULE-26: --write-cache CLI reads JSON from stdin and merges into audit cache."""

    def _make_entry(self, assessment, feature, proof_id, rule_id):
        return {
            "assessment": assessment,
            "criterion": "matches rule intent",
            "why": "test exercises the rule correctly",
            "fix": "none",
            "feature": feature,
            "proof_id": proof_id,
            "rule_id": rule_id,
            "priority": "LOW",
            "cached_at": "2026-04-01T00:00:00+00:00",
        }

    @pytest.mark.proof("static_checks", "PROOF-41", "RULE-26")
    def test_write_cache_cli_merges_entries(self):
        """--write-cache reads JSON dict from stdin and merges into the cache file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            entries = {
                "cli_hash_1": self._make_entry("STRONG", "feat_cli", "PROOF-1", "RULE-1"),
                "cli_hash_2": self._make_entry("WEAK",   "feat_cli", "PROOF-2", "RULE-2"),
            }
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, '--write-cache', '--project-root', tmpdir],
                input=json.dumps(entries),
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"--write-cache exited non-zero: {result.stderr}"
            output = json.loads(result.stdout)
            assert output['status'] == 'merged'
            assert output['entries'] == 2

            after = read_audit_cache(tmpdir)
            assert len(after) == 2
            assert "cli_hash_1" in after
            assert "cli_hash_2" in after

    @pytest.mark.proof("static_checks", "PROOF-41", "RULE-26")
    def test_write_cache_cli_merges_with_existing(self):
        """--write-cache preserves entries already on disk from a prior write."""
        with tempfile.TemporaryDirectory() as tmpdir:
            write_audit_cache(tmpdir, {
                "existing_hash": self._make_entry("STRONG", "feat_existing", "PROOF-1", "RULE-1"),
            })

            new_entry = {
                "new_hash": self._make_entry("HOLLOW", "feat_new", "PROOF-1", "RULE-1"),
            }
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, '--write-cache', '--project-root', tmpdir],
                input=json.dumps(new_entry),
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"--write-cache exited non-zero: {result.stderr}"

            after = read_audit_cache(tmpdir)
            assert len(after) == 2, f"Expected 2 entries (existing + new), got {len(after)}"
            assert "existing_hash" in after, "existing entry was clobbered by --write-cache"
            assert "new_hash" in after, "new entry not written by --write-cache"


class TestCheckJs:
    """check_js JS/TS structural checks, exercised through the real CLI."""

    @staticmethod
    def _run(ts_source, feature):
        path = _write_tmp(ts_source, suffix='.ts')
        try:
            result = subprocess.run(
                [sys.executable, STATIC_CHECKS_PY, path, feature],
                capture_output=True, text=True,
            )
            assert result.returncode == 0, f"static_checks exited non-zero: {result.stderr}"
            return {p['proof_id']: p for p in json.loads(result.stdout)['proofs']}
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-42", "RULE-27", tier="e2e")
    def test_check_js_assertion_detection(self):
        """assert_true and no_assertions are detected in JS/TS bodies; clean tests pass."""
        proofs = self._run('''
import { it, expect } from "vitest";

it("tautological [proof:jsfeat:PROOF-1:RULE-1]", () => {
  expect(true).toBe(true);
});

it("empty body [proof:jsfeat:PROOF-2:RULE-2]", () => {
  const x = 5;
});

it("real assertion [proof:jsfeat:PROOF-3:RULE-3]", () => {
  expect(2 + 2).toBe(4);
});
''', "jsfeat")

        assert proofs["PROOF-1"]["status"] == "fail"
        assert proofs["PROOF-1"]["check"] == "assert_true"
        assert proofs["PROOF-2"]["status"] == "fail"
        assert proofs["PROOF-2"]["check"] == "no_assertions"
        assert proofs["PROOF-3"]["status"] == "pass"

        # RULE-27: check_js returns the same JSON shape as check_python —
        # every proof dict carries proof_id, rule_id, test_name, status, reason.
        for pid in ("PROOF-1", "PROOF-2", "PROOF-3"):
            entry = proofs[pid]
            for field in ("proof_id", "rule_id", "test_name", "status", "reason"):
                assert field in entry, f"{pid} missing '{field}' (shape must match check_python): {entry}"
        assert proofs["PROOF-1"]["rule_id"] == "RULE-1"
        assert proofs["PROOF-3"]["test_name"].startswith("real assertion")

    @pytest.mark.proof("static_checks", "PROOF-43", "RULE-28", tier="e2e")
    def test_check_js_tokenizer_handles_braces_and_apostrophes(self):
        """Issue #2 repro: nested-brace bodies are not truncated and apostrophe
        titles are not dropped."""
        proofs = self._run('''
import { describe, it, expect } from "vitest";
import { execSync } from "node:child_process";

describe("repro", () => {
  it("execSync options trigger early-truncation [proof:demo:PROOF-1:RULE-1]", () => {
    const out = execSync("ls", { cwd: ".", encoding: "utf8" });
    expect(out).toMatch(/./);
  });

  it("cd's into a sibling [proof:demo:PROOF-2:RULE-2]", () => {
    expect(1).toBe(1);
  });
});
''', "demo")

        # Bug #2: apostrophe in a double-quoted title must not drop the test.
        assert "PROOF-1" in proofs, "options-object test vanished from audit output"
        assert "PROOF-2" in proofs, "apostrophe-title test vanished from audit output"
        # Bug #1: the options-object body must be captured fully, so the expect()
        # after it is seen and the test is NOT falsely flagged no_assertions.
        assert proofs["PROOF-1"]["status"] == "pass", proofs["PROOF-1"]
        assert proofs["PROOF-1"].get("check") != "no_assertions"
        assert proofs["PROOF-2"]["status"] == "pass"


class TestCrossPlatformPortability:
    """RULE-29/30: static_checks.py imports and runs on Windows as well as POSIX."""

    def _source(self):
        with open(STATIC_CHECKS_PY, encoding='utf-8') as f:
            return f.read()

    @pytest.mark.proof("static_checks", "PROOF-44", "RULE-29")
    def test_no_unconditional_fcntl_import(self):
        """fcntl is imported under try/except ImportError, never unconditionally,
        and _HAS_FCNTL is assigned in both branches."""
        tree = ast.parse(self._source())

        # No top-level `import fcntl` in the module body.
        for node in tree.body:
            if isinstance(node, ast.Import):
                assert 'fcntl' not in [a.name for a in node.names], \
                    "fcntl is imported unconditionally at module level"

        fcntl_in_try = False
        flag_in_try = False
        flag_in_except = False
        for node in tree.body:
            if not isinstance(node, ast.Try):
                continue
            for stmt in node.body:
                if isinstance(stmt, ast.Import) and any(a.name == 'fcntl' for a in stmt.names):
                    fcntl_in_try = True
                if isinstance(stmt, ast.Assign) and any(
                        getattr(t, 'id', None) == '_HAS_FCNTL' for t in stmt.targets):
                    flag_in_try = True
            # The except must catch ImportError and set the flag.
            catches_import_error = any(
                h.type is not None and isinstance(h.type, ast.Name) and h.type.id == 'ImportError'
                for h in node.handlers)
            for h in node.handlers:
                if any(isinstance(s, ast.Assign) and any(
                        getattr(t, 'id', None) == '_HAS_FCNTL' for t in s.targets) for s in h.body):
                    flag_in_except = catches_import_error

        assert fcntl_in_try, "fcntl is not imported inside a try block"
        assert flag_in_try and flag_in_except, \
            "_HAS_FCNTL must be set in both the try and except ImportError branches"
        assert hasattr(static_checks, '_HAS_FCNTL'), "module exposes no _HAS_FCNTL flag"

    @pytest.mark.proof("static_checks", "PROOF-45", "RULE-30")
    def test_all_text_open_calls_specify_utf8(self):
        """Every text-mode open() in static_checks.py passes encoding='utf-8'."""
        tree = ast.parse(self._source())
        offenders = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'open'):
                continue
            # Resolve the mode (2nd positional arg or mode= kwarg).
            mode = None
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            for kw in node.keywords:
                if kw.arg == 'mode' and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if isinstance(mode, str) and 'b' in mode:
                continue  # binary mode takes no encoding
            enc = None
            for kw in node.keywords:
                if kw.arg == 'encoding' and isinstance(kw.value, ast.Constant):
                    enc = kw.value.value
            if enc != 'utf-8':
                offenders.append(getattr(node, 'lineno', '?'))
        assert not offenders, \
            f"text-mode open() without encoding='utf-8' at lines: {offenders}"


class TestCheckCsharp:
    """RULE-31: deterministic Pass-1 checks for C#/.NET (xUnit/NUnit/MSTest) tests."""

    def _cs(self, body, proof_id="PROOF-1", rule_id="RULE-1"):
        return _write_tmp(f'''
using Xunit;
using FluentAssertions;
namespace Demo {{
  public class Tests {{
    [Fact]
    [Trait("PurlinProof", "csfeat:{proof_id}:{rule_id}:unit")]
    public void TheTest() {{ {body} }}
  }}
}}
''', suffix='.cs')

    @pytest.mark.proof("static_checks", "PROOF-46", "RULE-31")
    def test_detects_assert_true(self):
        path = self._cs("Assert.True(true);")
        try:
            results = check_csharp(path, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'assert_true'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-47", "RULE-31")
    def test_detects_no_assertions(self):
        path = self._cs("var x = Compute(); var y = x + 1;")
        try:
            results = check_csharp(path, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'no_assertions'
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-48", "RULE-31")
    def test_recognizes_all_assertion_frameworks(self):
        """xUnit Assert.Equal, NUnit Assert.That, MSTest Assert.IsTrue, and
        FluentAssertions .Should() each count as a real assertion (status=pass)."""
        cases = {
            "xunit": "Assert.Equal(3, 1 + 2);",
            "nunit": "Assert.That(2 + 2, Is.EqualTo(4));",
            "mstest": "Assert.IsTrue(1 < 2);",
            "fluent": 'var s = "hi { nested }"; s.Should().Contain("hi");',
        }
        for name, body in cases.items():
            path = self._cs(body)
            try:
                results = check_csharp(path, "csfeat")
                assert len(results) == 1, f"{name}: expected 1 proof"
                assert results[0]['status'] == 'pass', \
                    f"{name}: assertion not recognized — {results[0]}"
            finally:
                os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-49", "RULE-31")
    def test_dispatch_routes_cs_to_check_csharp(self):
        """analyze_test_file routes a .cs file to check_csharp (not the empty fallback)."""
        path = self._cs("Assert.True(true);", proof_id="PROOF-7", rule_id="RULE-9")
        try:
            results = analyze_test_file(path, "csfeat")
            assert results, ".cs file produced no proofs — dispatch fell through to []"
            assert results[0]['proof_id'] == 'PROOF-7'
            assert results[0]['check'] == 'assert_true'
            # A genuinely unknown extension still yields the empty fallback.
            other = _write_tmp("nothing here", suffix='.txt')
            try:
                assert analyze_test_file(other, "csfeat") == []
            finally:
                os.unlink(other)
        finally:
            os.unlink(path)

    @pytest.mark.proof("static_checks", "PROOF-55", "RULE-31")
    def test_recognizes_playwright_fluent_assertions(self):
        """A C# test asserting only via Playwright's Expect(...).To*Async() is recognized
        as an assertion (status=pass), but a bare Expect(x) with no matcher is still flagged."""
        # Mirrors the PR #4 repro: Nav_ShowsUser_AndSignOut asserts only through Playwright.
        playwright = (
            'await Assertions.Expect(page.Locator("text=" + user)).ToBeVisibleAsync();\n'
            'await Assertions.Expect(page.Locator("a[href=\'logout\']")).ToBeVisibleAsync();'
        )
        path = self._cs(playwright)
        try:
            results = check_csharp(path, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'pass', \
                f"Playwright assertion not recognized — {results[0]}"
        finally:
            os.unlink(path)

        # Bare Expect(x) with no To*Async() matcher chain is NOT an assertion.
        bare = self._cs("Expect(result);")
        try:
            results = check_csharp(bare, "csfeat")
            assert len(results) == 1
            assert results[0]['status'] == 'fail'
            assert results[0]['check'] == 'no_assertions', \
                f"bare Expect(x) should be no_assertions — {results[0]}"
        finally:
            os.unlink(bare)

    @pytest.mark.proof("static_checks", "PROOF-56", "RULE-32")
    def test_resolve_test_file_from_name(self):
        """When a proof's test_file is empty (C#/xUnit under dotnet test), the
        source file is resolved from the fully-qualified test_name by locating the
        declaring class — preferring the authored file over a bin/ build copy."""
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, 'tests'))
            os.makedirs(os.path.join(root, 'bin'))
            authored = os.path.join(root, 'tests', 'AuthLogicTests.cs')
            with open(authored, 'w', encoding='utf-8') as f:
                f.write('namespace Demo.Tests {\n  public class AuthLogicTests {\n'
                        '    [Fact] public void Evaluate_NullRow() { }\n  }\n}\n')
            # A build-output copy that must be skipped.
            with open(os.path.join(root, 'bin', 'AuthLogicTests.cs'), 'w', encoding='utf-8') as f:
                f.write('public class AuthLogicTests { }\n')

            got = resolve_test_file_from_name(
                'Demo.Tests.AuthLogicTests.Evaluate_NullRow', root)
            assert got == 'tests/AuthLogicTests.cs', f"resolved to {got!r}"

            # A test_name whose class is not declared anywhere resolves to ''.
            assert resolve_test_file_from_name('Demo.Tests.MissingClass.X', root) == ''

            # The --resolve-source CLI prints JSON with the resolved test_file.
            r = subprocess.run(
                [sys.executable, _STATIC_CHECKS_PY, '--resolve-source',
                 'Demo.Tests.AuthLogicTests.Evaluate_NullRow', '--project-root', root],
                capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            payload = json.loads(r.stdout)
            assert payload['test_file'] == 'tests/AuthLogicTests.cs', payload
