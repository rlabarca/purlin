"""Windows-native proofs for static_checks (RULE-29/30).

These verify the real Windows code paths — the native `msvcrt.locking` file lock and
UTF-8 text I/O under the native console codec — on an actual `windows-latest` runner,
not the host simulations (PROOF-50 fake msvcrt, PROOF-52 simulated ASCII locale).

They are gated to Windows and emit the dedicated `windows` proof tier
(`specs/audit/static_checks.proofs-windows.json`). The tier keeps host runs — where
these tests are skipped — from clobbering the CI-emitted proof file, since the pytest
proof plugin overwrites per (feature, tier) only for tiers it actually collected.

Run on Windows: python -m pytest dev/test_windows_native.py
"""

import os
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'audit'))

import static_checks
from static_checks import write_audit_cache, read_audit_cache

_STATIC_CHECKS_PY = os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'audit', 'static_checks.py'
)
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows-native proofs run only on a windows-latest CI runner",
)


def _scaffold(root, feature, pairs):
    """Write a spec and a proof file so `(feature, proof_id)` resolves.

    `write_audit_cache` re-keys every entry from project state (static_checks
    RULE-38), so a cache entry for a proof the project does not declare is
    rejected. A bare temp directory is no longer a project a grade can be
    written into, which is the point of the rule.
    """
    spec_dir = os.path.join(root, 'specs', 'app')
    os.makedirs(spec_dir, exist_ok=True)
    rules = ''.join(f'- {rid}: {feature} rule {rid}\n' for _pid, rid in pairs)
    proofs = ''.join(
        f'- {pid} ({rid}): Call {feature}() and verify it returns 0 @unit\n'
        for pid, rid in pairs)
    with open(os.path.join(spec_dir, f'{feature}.md'), 'w', encoding='utf-8') as f:
        f.write(f'# Feature: {feature}\n\n> Scope: src/{feature}.py\n\n'
                f'## Rules\n{rules}\n## Proof\n{proofs}')
    return spec_dir


def _audit_entry(assessment, feature, proof_id, rule_id):
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


@pytest.mark.proof("static_checks", "PROOF-53", "RULE-29", tier="unit", platforms=("windows-2022",))
def test_real_msvcrt_lock_path():
    """On real Windows, fcntl is genuinely absent so write_audit_cache uses the native
    msvcrt.locking path with no fake. The cache must round-trip and the adjacent
    audit_cache.json.lock must be created."""
    assert static_checks._HAS_FCNTL is False, (
        "expected fcntl unavailable on Windows — the native msvcrt path would not be exercised"
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        _scaffold(tmpdir, "feat_a", [("PROOF-1", "RULE-1"), ("PROOF-2", "RULE-2")])
        write_audit_cache(tmpdir, {
            "h1": _audit_entry("STRONG", "feat_a", "PROOF-1", "RULE-1"),
            "h2": _audit_entry("WEAK", "feat_a", "PROOF-2", "RULE-2"),
        })
        after = read_audit_cache(tmpdir)
        assert len(after) == 2, f"entries lost on native Windows lock path: {list(after)}"
        # The supplied keys are discarded and recomputed from the project, so the
        # round-trip is checked against the keys the project produces.
        expected = {static_checks.cache_key_for(tmpdir, "feat_a", pid)[0]
                    for pid in ("PROOF-1", "PROOF-2")}
        assert set(after) == expected, f"re-keyed entries not found: {list(after)}"
        lock_path = os.path.join(tmpdir, '.purlin', 'cache', 'audit_cache.json.lock')
        assert os.path.exists(lock_path), "msvcrt lock file was not created adjacent to the cache"


@pytest.mark.proof("static_checks", "PROOF-54", "RULE-30", tier="unit", platforms=("windows-2022",))
def test_load_criteria_native_console():
    """Under the native Windows console codec (no PYTHONUTF8/LC_ALL/LANG overrides),
    --load-criteria must read the tool's own non-ASCII audit_criteria.md and print it
    without UnicodeDecodeError (read) or UnicodeEncodeError (stdout)."""
    env = dict(os.environ)
    for var in ('PYTHONUTF8', 'PYTHONIOENCODING', 'LC_ALL', 'LANG'):
        env.pop(var, None)
    with tempfile.TemporaryDirectory() as tmpdir:
        r = subprocess.run(
            [sys.executable, _STATIC_CHECKS_PY, '--load-criteria', '--project-root', tmpdir],
            cwd=_REPO_ROOT, env=env, capture_output=True, text=True, encoding='utf-8',
        )
    assert r.returncode == 0, f"--load-criteria failed under native console codec: {r.stderr}"
    assert any(ord(ch) > 127 for ch in r.stdout), "no non-ASCII glyph in --load-criteria output"
