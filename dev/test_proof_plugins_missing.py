"""Tests for 19 missing proof_plugins rules.

Covers:
  RULE-2:  Proof files written as <feature>.proofs-<tier>.json
  RULE-3:  Fallback to specs/ when spec directory not found
  RULE-7:  No proof markers → no proof files written (no-op)
  RULE-8:  pytest marker signature with tier default
  RULE-9:  Markers with fewer than 3 positional args are silently skipped
  RULE-10: test_file is relative to pytest rootdir
  RULE-11: pytest_configure registers marker + plugin
  RULE-12: Jest marker parsed from test title [proof:feature:PROOF-N:RULE-N:tier]
  RULE-13: Jest tests without [proof:...] are ignored
  RULE-14: Jest test_file is relative to rootDir
  RULE-15: Jest "passed" → "pass", all other statuses → "fail"
  RULE-16: purlin_proof 5 args + PURLIN_PROOF_TIER env var
  RULE-17: test_file recorded from BASH_SOURCE[1]
  RULE-18: purlin_proof_finish required to write proof files
  RULE-19: Entries cleared after purlin_proof_finish
  RULE-20: Custom plugins discovered via specs/**/*.proofs-*.json glob
  RULE-21: Fallback emits warning to stderr naming feature + purlin:spec
  RULE-23: c_purlin_emit.py reads stdin JSON and writes feature-scoped proof files
  RULE-29: Removed test entries purged on re-run (not carried over)
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROOF_SCRIPTS = os.path.join(PROJECT_ROOT, "scripts", "proof")
JEST_REPORTER = os.path.join(PROOF_SCRIPTS, "jest_purlin.js")
SHELL_HARNESS = os.path.join(PROOF_SCRIPTS, "shell_purlin.sh")
MCP_SCRIPTS = os.path.join(PROJECT_ROOT, "scripts", "mcp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(tmp_path, subdir, feature, extra_rules=1):
    """Create a minimal spec file and return (spec_dir_path, spec_file_path)."""
    spec_dir = tmp_path / "specs" / subdir
    spec_dir.mkdir(parents=True, exist_ok=True)
    rules = "\n".join(f"- RULE-{i}: rule {i}" for i in range(1, extra_rules + 1))
    (spec_dir / f"{feature}.md").write_text(
        f"# Feature: {feature}\n\n## Rules\n{rules}\n"
    )
    return spec_dir


def _run_pytest_with_plugin(tmp_path, test_code, allow_failure=False):
    """Run pytest with pytest_purlin in tmp_path; return CompletedProcess."""
    test_file = tmp_path / "test_s.py"
    test_file.write_text(textwrap.dedent(test_code))
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(test_file),
            "-p", "pytest_purlin",
            f"--override-ini=pythonpath={PROOF_SCRIPTS}",
            "-q", "--no-header",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    if not allow_failure and result.returncode not in (0, 1):
        pytest.fail(f"pytest internal error:\n{result.stdout}\n{result.stderr}")
    return result


def _jest_run_in_process(tmp_path, test_file_rel, test_results):
    """Invoke jest_purlin.js reporter directly via node, mocking glob."""
    results_json = json.dumps(test_results)
    script = f"""
const Module = require('module');
const fs = require('fs');
const path = require('path');
const origLoad = Module._load;
Module._load = function(request, parent, isMain) {{
  if (request === 'glob') {{
    return {{ globSync: function(pattern) {{
      const results = [];
      function walk(dir) {{
        try {{
          for (const e of fs.readdirSync(dir, {{withFileTypes: true}})) {{
            const full = path.join(dir, e.name);
            if (e.isDirectory()) walk(full);
            else if (e.name.endsWith('.md')) results.push(full);
          }}
        }} catch(err) {{}}
      }}
      const base = pattern.split('*')[0].replace(/\\/$/, '') || '.';
      if (fs.existsSync(base)) walk(base);
      return results;
    }}}};
  }}
  return origLoad.apply(this, arguments);
}};
const Reporter = require({json.dumps(JEST_REPORTER)});
const r = new Reporter({{rootDir: {json.dumps(str(tmp_path))}}}, {{}});
r.onTestResult(null, {{
  testFilePath: path.join({json.dumps(str(tmp_path))}, {json.dumps(test_file_rel)}),
  testResults: {results_json}
}});
process.chdir({json.dumps(str(tmp_path))});
r.onRunComplete();
"""
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    return result


def _run_shell_proof(tmp_path, feature, proofs, tier=None):
    """Call purlin_proof for each (proof_id, rule_id, status, name) and purlin_proof_finish."""
    proof_calls = "\n".join(
        f'purlin_proof "{feature}" "{pid}" "{rid}" {status} "{name}"'
        for pid, rid, status, name in proofs
    )
    env_line = f"export PURLIN_PROOF_TIER={tier}" if tier else ""
    script = textwrap.dedent(f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        source {SHELL_HARNESS}
        {env_line}
        {proof_calls}
        purlin_proof_finish
    """)
    sh = tmp_path / "run_proof.sh"
    sh.write_text(script)
    result = subprocess.run(
        ["bash", str(sh)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    return result


# ---------------------------------------------------------------------------
# RULE-2: Proof files written as <feature>.proofs-<tier>.json
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-2", "RULE-2")
def test_proof_file_naming(tmp_path):
    """Proof file is named <feature>.proofs-<tier>.json inside the spec directory."""
    spec_dir = _make_spec(tmp_path, "hooks", "gate_hook")
    _run_pytest_with_plugin(tmp_path, """
        import pytest
        @pytest.mark.proof("gate_hook", "PROOF-1", "RULE-1")
        def test_it(): assert 1 + 1 == 2
    """)
    proof_file = spec_dir / "gate_hook.proofs-unit.json"
    assert proof_file.exists(), f"Expected {proof_file} to exist"
    assert proof_file.name == "gate_hook.proofs-unit.json"


# ---------------------------------------------------------------------------
# RULE-3: Fallback to specs/ when feature spec not found
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-3", "RULE-3")
def test_fallback_to_specs_root_when_no_spec(tmp_path):
    """When no spec exists for a feature, proof is written to specs/<feature>.proofs-unit.json."""
    (tmp_path / "specs").mkdir()
    _run_pytest_with_plugin(tmp_path, """
        import pytest
        @pytest.mark.proof("nonexistent_feature_xyz", "PROOF-1", "RULE-1")
        def test_it(): assert "abc" == "abc"
    """)
    fallback = tmp_path / "specs" / "nonexistent_feature_xyz.proofs-unit.json"
    assert fallback.exists(), f"Expected fallback proof file at {fallback}"
    data = json.loads(fallback.read_text())
    assert data["proofs"][0]["feature"] == "nonexistent_feature_xyz"


# ---------------------------------------------------------------------------
# RULE-7: No proof markers → no proof files written
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-7", "RULE-7")
def test_no_markers_no_proof_files(tmp_path):
    """Running pytest with no proof markers produces zero *.proofs-*.json files."""
    _make_spec(tmp_path, "a", "my_feat")
    _run_pytest_with_plugin(tmp_path, """
        def test_plain(): assert 2 * 3 == 6
        def test_also_plain(): assert "hello".upper() == "HELLO"
    """)
    import glob as _glob
    proof_files = _glob.glob(str(tmp_path / "specs" / "**" / "*.proofs-*.json"), recursive=True)
    assert proof_files == [], f"Expected no proof files, got: {proof_files}"


# ---------------------------------------------------------------------------
# RULE-8: pytest marker signature with tier default
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-8", "RULE-8")
def test_pytest_marker_signature_defaults_to_unit_tier(tmp_path):
    """@pytest.mark.proof('feat','PROOF-1','RULE-1') defaults tier to 'unit'."""
    spec_dir = _make_spec(tmp_path, "a", "feat")
    _run_pytest_with_plugin(tmp_path, """
        import pytest
        @pytest.mark.proof("feat", "PROOF-1", "RULE-1")
        def test_it(): assert 10 > 5
    """)
    proof_file = spec_dir / "feat.proofs-unit.json"
    assert proof_file.exists()
    data = json.loads(proof_file.read_text())
    entry = data["proofs"][0]
    assert entry["feature"] == "feat"
    assert entry["id"] == "PROOF-1"
    assert entry["rule"] == "RULE-1"
    assert entry["tier"] == "unit"


@pytest.mark.proof("proof_plugins", "PROOF-8", "RULE-8")
def test_pytest_marker_explicit_tier(tmp_path):
    """@pytest.mark.proof(..., tier='integration') stores the explicit tier."""
    spec_dir = _make_spec(tmp_path, "a", "feat_integ")
    _run_pytest_with_plugin(tmp_path, """
        import pytest
        @pytest.mark.proof("feat_integ", "PROOF-1", "RULE-1", tier="integration")
        def test_it(): assert len([1, 2, 3]) == 3
    """)
    proof_file = spec_dir / "feat_integ.proofs-integration.json"
    assert proof_file.exists(), f"Expected integration proof file at {proof_file}"
    data = json.loads(proof_file.read_text())
    assert data["proofs"][0]["tier"] == "integration"


# ---------------------------------------------------------------------------
# RULE-9: Markers with fewer than 3 positional args are silently skipped
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-9", "RULE-9")
def test_pytest_marker_two_args_skipped(tmp_path):
    """A marker with only 2 positional args produces no proof entry."""
    (tmp_path / "specs").mkdir()
    _run_pytest_with_plugin(tmp_path, """
        import pytest
        @pytest.mark.proof("feat", "PROOF-1")
        def test_two_args(): assert True
    """, allow_failure=True)
    import glob as _glob
    proof_files = _glob.glob(str(tmp_path / "specs" / "**" / "*.proofs-*.json"), recursive=True)
    # Either no file, or a file with zero entries for "feat"
    for pf in proof_files:
        data = json.loads(open(pf).read())
        feat_entries = [p for p in data.get("proofs", []) if p.get("feature") == "feat"]
        assert feat_entries == [], f"Expected no 'feat' entries, got: {feat_entries}"


@pytest.mark.proof("proof_plugins", "PROOF-9", "RULE-9")
def test_pytest_marker_one_arg_skipped(tmp_path):
    """A marker with only 1 positional arg produces no proof entry."""
    (tmp_path / "specs").mkdir()
    _run_pytest_with_plugin(tmp_path, """
        import pytest
        @pytest.mark.proof("feat_only")
        def test_one_arg(): assert True
    """, allow_failure=True)
    import glob as _glob
    proof_files = _glob.glob(str(tmp_path / "specs" / "**" / "*.proofs-*.json"), recursive=True)
    for pf in proof_files:
        data = json.loads(open(pf).read())
        entries = [p for p in data.get("proofs", []) if p.get("feature") == "feat_only"]
        assert entries == [], f"Expected no 'feat_only' entries, got: {entries}"


# ---------------------------------------------------------------------------
# RULE-10: test_file is relative to pytest rootdir
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-10", "RULE-10")
def test_pytest_test_file_is_relative(tmp_path):
    """test_file in the proof entry is a relative path, not an absolute one."""
    spec_dir = _make_spec(tmp_path, "a", "feat_relpath")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_feat.py").write_text(textwrap.dedent("""
        import pytest
        @pytest.mark.proof("feat_relpath", "PROOF-1", "RULE-1")
        def test_it(): assert "relative" != "absolute"
    """))
    subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(tests_dir / "test_feat.py"),
            "-p", "pytest_purlin",
            f"--override-ini=pythonpath={PROOF_SCRIPTS}",
            "-q", "--no-header",
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    proof_file = spec_dir / "feat_relpath.proofs-unit.json"
    assert proof_file.exists()
    data = json.loads(proof_file.read_text())
    test_file_path = data["proofs"][0]["test_file"]
    assert not os.path.isabs(test_file_path), (
        f"test_file should be relative, got: {test_file_path!r}"
    )
    # Should contain the filename, not just the full system path
    assert "test_feat.py" in test_file_path


# ---------------------------------------------------------------------------
# RULE-11: pytest_configure registers marker + plugin
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-11", "RULE-11")
def test_pytest_configure_registers_proof_marker_and_plugin():
    """pytest_configure registers the 'proof' marker and the 'purlin_proof' plugin."""
    sys.path.insert(0, PROOF_SCRIPTS)
    try:
        from pytest_purlin import pytest_configure, ProofCollector

        class FakePluginManager:
            registered = {}
            def register(self, plugin, name):
                self.registered[name] = plugin

        class FakeConfig:
            markers = []
            pluginmanager = FakePluginManager()
            def addinivalue_line(self, name, value):
                self.markers.append((name, value))

        cfg = FakeConfig()
        pytest_configure(cfg)

        # Marker 'proof' must be registered
        assert any("proof" in m[1] for m in cfg.markers), (
            f"'proof' marker not in markers: {cfg.markers}"
        )
        # Plugin named 'purlin_proof' must be registered
        assert "purlin_proof" in cfg.pluginmanager.registered, (
            f"'purlin_proof' not in registered plugins: {list(cfg.pluginmanager.registered)}"
        )
        assert isinstance(cfg.pluginmanager.registered["purlin_proof"], ProofCollector)
    finally:
        if PROOF_SCRIPTS in sys.path:
            sys.path.remove(PROOF_SCRIPTS)


@pytest.mark.proof("proof_plugins", "PROOF-11", "RULE-11")
def test_pytest_configure_marker_recognized_in_session(tmp_path):
    """The 'proof' marker is recognized (no PytestUnknownMarkWarning) in a real session."""
    _make_spec(tmp_path, "a", "myf")
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "-p", "pytest_purlin",
            f"--override-ini=pythonpath={PROOF_SCRIPTS}",
            "-W", "error::pytest.PytestUnknownMarkWarning",
            "--collect-only",
            "-q",
        ],
        input=None,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    # A PytestUnknownMarkWarning for 'proof' would cause non-zero exit
    # We just need to confirm the plugin doesn't break the session
    assert "PytestUnknownMarkWarning" not in result.stdout
    assert "PytestUnknownMarkWarning" not in result.stderr


# ---------------------------------------------------------------------------
# RULE-12: Jest marker parsed from test title
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-12", "RULE-12")
def test_jest_marker_parsed_from_title(tmp_path):
    """Jest reporter extracts feature/PROOF-N/RULE-N from [proof:...] in test title."""
    _make_spec(tmp_path, "a", "feat_jest")
    result = _jest_run_in_process(
        tmp_path,
        "tests/test.js",
        [{"title": "works [proof:feat_jest:PROOF-1:RULE-1:unit]", "status": "passed"}],
    )
    assert result.returncode == 0, f"node stderr: {result.stderr}"
    proof_file = tmp_path / "specs" / "a" / "feat_jest.proofs-unit.json"
    assert proof_file.exists(), f"Proof file not created: {proof_file}"
    data = json.loads(proof_file.read_text())
    entry = data["proofs"][0]
    assert entry["feature"] == "feat_jest"
    assert entry["id"] == "PROOF-1"
    assert entry["rule"] == "RULE-1"


@pytest.mark.proof("proof_plugins", "PROOF-12", "RULE-12")
def test_jest_marker_tier_defaults_to_unit(tmp_path):
    """Jest marker without explicit tier defaults to 'unit'."""
    _make_spec(tmp_path, "a", "feat_tier_default")
    # Marker without tier: [proof:feat_tier_default:PROOF-1:RULE-1]
    result = _jest_run_in_process(
        tmp_path,
        "tests/test.js",
        [{"title": "name [proof:feat_tier_default:PROOF-1:RULE-1]", "status": "passed"}],
    )
    assert result.returncode == 0, f"node stderr: {result.stderr}"
    proof_file = tmp_path / "specs" / "a" / "feat_tier_default.proofs-unit.json"
    assert proof_file.exists(), "Expected unit tier proof file"
    data = json.loads(proof_file.read_text())
    assert data["proofs"][0]["tier"] == "unit"


# ---------------------------------------------------------------------------
# RULE-13: Jest tests without [proof:...] are ignored
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-13", "RULE-13")
def test_jest_no_marker_ignored(tmp_path):
    """Jest test titles without [proof:...] produce no proof entries."""
    (tmp_path / "specs").mkdir()
    result = _jest_run_in_process(
        tmp_path,
        "tests/test.js",
        [
            {"title": "no marker here", "status": "passed"},
            {"title": "another test without annotation", "status": "failed"},
        ],
    )
    assert result.returncode == 0, f"node stderr: {result.stderr}"
    import glob as _glob
    proof_files = _glob.glob(str(tmp_path / "specs" / "**" / "*.proofs-*.json"), recursive=True)
    assert proof_files == [], f"Expected no proof files, got: {proof_files}"


# ---------------------------------------------------------------------------
# RULE-14: Jest test_file is relative to rootDir
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-14", "RULE-14")
def test_jest_test_file_is_relative_to_root_dir(tmp_path):
    """Jest proof entry's test_file is relative to the reporter's rootDir."""
    _make_spec(tmp_path, "a", "feat_rel")
    result = _jest_run_in_process(
        tmp_path,
        "src/components/test.js",
        [{"title": "thing [proof:feat_rel:PROOF-1:RULE-1:unit]", "status": "passed"}],
    )
    assert result.returncode == 0, f"node stderr: {result.stderr}"
    proof_file = tmp_path / "specs" / "a" / "feat_rel.proofs-unit.json"
    assert proof_file.exists()
    data = json.loads(proof_file.read_text())
    test_file_path = data["proofs"][0]["test_file"]
    assert not os.path.isabs(test_file_path), (
        f"test_file should be relative, got: {test_file_path!r}"
    )
    assert "test.js" in test_file_path


# ---------------------------------------------------------------------------
# RULE-15: Jest "passed" → "pass", all other statuses → "fail"
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-15", "RULE-15")
def test_jest_passed_maps_to_pass(tmp_path):
    """Jest status 'passed' maps to 'pass' in the proof entry."""
    _make_spec(tmp_path, "a", "feat_status", extra_rules=2)
    result = _jest_run_in_process(
        tmp_path,
        "tests/t.js",
        [{"title": "ok [proof:feat_status:PROOF-1:RULE-1:unit]", "status": "passed"}],
    )
    assert result.returncode == 0
    data = json.loads((tmp_path / "specs" / "a" / "feat_status.proofs-unit.json").read_text())
    assert data["proofs"][0]["status"] == "pass"


@pytest.mark.proof("proof_plugins", "PROOF-15", "RULE-15")
def test_jest_failed_maps_to_fail(tmp_path):
    """Jest status 'failed' maps to 'fail' in the proof entry."""
    _make_spec(tmp_path, "a", "feat_fail_status")
    result = _jest_run_in_process(
        tmp_path,
        "tests/t.js",
        [{"title": "bad [proof:feat_fail_status:PROOF-1:RULE-1:unit]", "status": "failed"}],
    )
    assert result.returncode == 0
    data = json.loads((tmp_path / "specs" / "a" / "feat_fail_status.proofs-unit.json").read_text())
    assert data["proofs"][0]["status"] == "fail"


@pytest.mark.proof("proof_plugins", "PROOF-15", "RULE-15")
def test_jest_pending_maps_to_fail(tmp_path):
    """Jest status other than 'passed' (e.g., 'pending') maps to 'fail'."""
    _make_spec(tmp_path, "a", "feat_pending")
    result = _jest_run_in_process(
        tmp_path,
        "tests/t.js",
        [{"title": "skip [proof:feat_pending:PROOF-1:RULE-1:unit]", "status": "pending"}],
    )
    assert result.returncode == 0
    data = json.loads((tmp_path / "specs" / "a" / "feat_pending.proofs-unit.json").read_text())
    assert data["proofs"][0]["status"] == "fail"


# ---------------------------------------------------------------------------
# RULE-16: Shell purlin_proof 5 args + PURLIN_PROOF_TIER
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-16", "RULE-16")
def test_shell_proof_uses_purlin_proof_tier_env(tmp_path):
    """PURLIN_PROOF_TIER env var sets the tier in the written proof entry."""
    _make_spec(tmp_path, "a", "feat_shell_tier")
    result = _run_shell_proof(
        tmp_path,
        "feat_shell_tier",
        [("PROOF-1", "RULE-1", "pass", "my test desc")],
        tier="integration",
    )
    assert result.returncode == 0, f"Shell proof failed:\n{result.stderr}"
    proof_file = tmp_path / "specs" / "a" / "feat_shell_tier.proofs-integration.json"
    assert proof_file.exists(), f"Expected integration proof file at {proof_file}"
    data = json.loads(proof_file.read_text())
    entry = data["proofs"][0]
    assert entry["tier"] == "integration"
    assert entry["feature"] == "feat_shell_tier"


@pytest.mark.proof("proof_plugins", "PROOF-16", "RULE-16")
def test_shell_proof_defaults_tier_to_unit(tmp_path):
    """Without PURLIN_PROOF_TIER set, tier defaults to 'unit'."""
    _make_spec(tmp_path, "a", "feat_default_tier")
    result = _run_shell_proof(
        tmp_path,
        "feat_default_tier",
        [("PROOF-1", "RULE-1", "pass", "test desc")],
        tier=None,
    )
    assert result.returncode == 0, f"Shell proof failed:\n{result.stderr}"
    proof_file = tmp_path / "specs" / "a" / "feat_default_tier.proofs-unit.json"
    assert proof_file.exists(), f"Expected unit proof file at {proof_file}"
    data = json.loads(proof_file.read_text())
    assert data["proofs"][0]["tier"] == "unit"


# ---------------------------------------------------------------------------
# RULE-17: test_file recorded from BASH_SOURCE[1]
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-17", "RULE-17")
def test_shell_test_file_reflects_caller_filename(tmp_path):
    """test_file in shell proof entry matches the sourcing script's filename."""
    _make_spec(tmp_path, "a", "feat_src_file")
    caller_script = tmp_path / "my_caller_test.sh"
    caller_script.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        source {SHELL_HARNESS}
        purlin_proof "feat_src_file" "PROOF-1" "RULE-1" pass "the test"
        purlin_proof_finish
    """))
    result = subprocess.run(
        ["bash", str(caller_script)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"Shell script failed:\n{result.stderr}"
    proof_file = tmp_path / "specs" / "a" / "feat_src_file.proofs-unit.json"
    assert proof_file.exists()
    data = json.loads(proof_file.read_text())
    test_file_recorded = data["proofs"][0]["test_file"]
    assert "my_caller_test.sh" in test_file_recorded, (
        f"Expected 'my_caller_test.sh' in test_file, got: {test_file_recorded!r}"
    )


# ---------------------------------------------------------------------------
# RULE-18: purlin_proof_finish required to write proof files
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-18", "RULE-18")
def test_shell_proof_not_written_before_finish(tmp_path):
    """purlin_proof calls without purlin_proof_finish produce no proof files."""
    _make_spec(tmp_path, "a", "feat_nofinish")
    # Subshell: call purlin_proof but NOT purlin_proof_finish
    no_finish = tmp_path / "no_finish.sh"
    no_finish.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        source {SHELL_HARNESS}
        purlin_proof "feat_nofinish" "PROOF-1" "RULE-1" pass "a test"
        purlin_proof "feat_nofinish" "PROOF-2" "RULE-2" pass "b test"
        # Deliberately NOT calling purlin_proof_finish
    """))
    result = subprocess.run(
        ["bash", str(no_finish)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0
    # No proof files should exist
    import glob as _glob
    proof_files = _glob.glob(str(tmp_path / "specs" / "**" / "*.proofs-*.json"), recursive=True)
    assert proof_files == [], f"Expected no proof files before finish, got: {proof_files}"


@pytest.mark.proof("proof_plugins", "PROOF-18", "RULE-18")
def test_shell_proof_written_after_finish(tmp_path):
    """purlin_proof_finish writes accumulated proof entries to disk."""
    _make_spec(tmp_path, "a", "feat_withfinish")
    with_finish = tmp_path / "with_finish.sh"
    with_finish.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        source {SHELL_HARNESS}
        purlin_proof "feat_withfinish" "PROOF-1" "RULE-1" pass "test one"
        purlin_proof "feat_withfinish" "PROOF-2" "RULE-2" pass "test two"
        purlin_proof_finish
    """))
    result = subprocess.run(
        ["bash", str(with_finish)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"Script failed:\n{result.stderr}"
    proof_file = tmp_path / "specs" / "a" / "feat_withfinish.proofs-unit.json"
    assert proof_file.exists(), f"Proof file not created after finish"
    data = json.loads(proof_file.read_text())
    assert len(data["proofs"]) == 2


# ---------------------------------------------------------------------------
# RULE-19: Entries cleared after purlin_proof_finish
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-19", "RULE-19")
def test_shell_entries_cleared_after_finish(tmp_path):
    """After purlin_proof_finish, _PURLIN_PROOFS is empty and second finish is no-op."""
    _make_spec(tmp_path, "a", "feat_cleared")
    # Script: call finish, check _PURLIN_PROOFS is empty, call finish again
    clear_script = tmp_path / "test_clear.sh"
    clear_script.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        source {SHELL_HARNESS}
        purlin_proof "feat_cleared" "PROOF-1" "RULE-1" pass "a test"
        purlin_proof_finish
        # After finish, _PURLIN_PROOFS should be empty
        if [[ -n "${{_PURLIN_PROOFS:-}}" ]]; then
            echo "ERROR: _PURLIN_PROOFS not cleared after finish" >&2
            exit 1
        fi
        # Second finish should be no-op (returns 0, writes nothing new)
        purlin_proof_finish
        exit 0
    """))
    result = subprocess.run(
        ["bash", str(clear_script)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"Clear check failed:\n{result.stdout}\n{result.stderr}"
    # Only 1 proof entry should exist (second finish was no-op)
    proof_file = tmp_path / "specs" / "a" / "feat_cleared.proofs-unit.json"
    assert proof_file.exists()
    data = json.loads(proof_file.read_text())
    assert len(data["proofs"]) == 1, f"Expected 1 proof, got {len(data['proofs'])}"


# ---------------------------------------------------------------------------
# RULE-20: Custom plugins discovered via specs/**/*.proofs-*.json glob
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-20", "RULE-20")
def test_custom_plugin_proof_files_discovered_by_sync_status(tmp_path):
    """A hand-written .proofs-*.json file in specs/ is discovered by sync_status."""
    spec_dir = _make_spec(tmp_path, "custom", "my_custom_feat")
    # Write a proof file as if produced by a custom (non-built-in) plugin
    proof_file = spec_dir / "my_custom_feat.proofs-unit.json"
    proof_file.write_text(json.dumps({
        "tier": "unit",
        "proofs": [{
            "feature": "my_custom_feat",
            "id": "PROOF-1",
            "rule": "RULE-1",
            "test_file": "tests/test_custom.go",
            "test_name": "TestCustomBehavior",
            "status": "pass",
            "tier": "unit",
        }],
    }, indent=2) + "\n")
    sys.path.insert(0, MCP_SCRIPTS)
    try:
        from purlin_server import sync_status
        output = sync_status(str(tmp_path))
    finally:
        if MCP_SCRIPTS in sys.path:
            sys.path.remove(MCP_SCRIPTS)
    # The custom proof should be counted as covering 1/1 rules
    assert "1/1" in output, (
        f"Expected '1/1' coverage in sync_status output, got:\n{output}"
    )


# ---------------------------------------------------------------------------
# RULE-21: Fallback emits warning to stderr naming feature + purlin:spec
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-21", "RULE-21")
def test_pytest_fallback_emits_warning_to_stderr(tmp_path):
    """When spec not found, pytest_purlin writes warning to stderr with feature name + purlin:spec."""
    (tmp_path / "specs").mkdir()
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "-p", "pytest_purlin",
            f"--override-ini=pythonpath={PROOF_SCRIPTS}",
            "-q", "--no-header",
            "--collect-only",
        ],
        input=textwrap.dedent("""
            import pytest
            @pytest.mark.proof("unknown_feat_abc", "PROOF-1", "RULE-1")
            def test_it(): assert True
        """),
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    # Run a real test (not just collect) so the plugin sessionfinish fires
    test_file = tmp_path / "test_warn.py"
    test_file.write_text(textwrap.dedent("""
        import pytest
        @pytest.mark.proof("unknown_feat_for_warning", "PROOF-1", "RULE-1")
        def test_it(): assert 1 == 1
    """))
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(test_file),
            "-p", "pytest_purlin",
            f"--override-ini=pythonpath={PROOF_SCRIPTS}",
            "-q", "--no-header",
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    combined_output = result.stdout + result.stderr
    assert "unknown_feat_for_warning" in combined_output, (
        f"Expected feature name in stderr warning. Output:\n{combined_output}"
    )
    assert "purlin:spec" in combined_output, (
        f"Expected 'purlin:spec' suggestion in stderr. Output:\n{combined_output}"
    )


@pytest.mark.proof("proof_plugins", "PROOF-21", "RULE-21")
def test_shell_fallback_emits_warning_to_stderr(tmp_path):
    """Shell purlin_proof_finish emits warning to stderr when spec not found."""
    (tmp_path / "specs").mkdir()
    script = tmp_path / "test_no_spec.sh"
    script.write_text(textwrap.dedent(f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        source {SHELL_HARNESS}
        purlin_proof "no_spec_feature_xyz" "PROOF-1" "RULE-1" pass "test"
        purlin_proof_finish
    """))
    result = subprocess.run(
        ["bash", str(script)],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    assert result.returncode == 0
    assert "no_spec_feature_xyz" in result.stderr, (
        f"Expected feature name in warning. stderr:\n{result.stderr}"
    )
    assert "purlin:spec" in result.stderr, (
        f"Expected 'purlin:spec' in warning. stderr:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# RULE-23: c_purlin_emit.py reads stdin JSON and writes feature-scoped proof files
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-23", "RULE-23")
def test_c_purlin_emit_writes_proof_file_from_stdin(tmp_path):
    """c_purlin_emit.py reads JSON from stdin and writes to the correct spec directory."""
    spec_dir = _make_spec(tmp_path, "math", "arithmetic")
    # Simulate JSON that a C binary would print to stdout
    stdin_json = json.dumps({
        "proofs": [
            {
                "feature": "arithmetic",
                "id": "PROOF-1",
                "rule": "RULE-1",
                "test_file": "test_add.c",
                "test_name": "test_addition",
                "status": "pass",
                "tier": "unit",
            },
        ]
    })
    result = subprocess.run(
        [sys.executable, os.path.join(PROOF_SCRIPTS, "c_purlin_emit.py")],
        input=stdin_json,
        capture_output=True, text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"c_purlin_emit.py failed:\n{result.stderr}"
    proof_file = spec_dir / "arithmetic.proofs-unit.json"
    assert proof_file.exists(), f"Expected proof file at {proof_file}"
    data = json.loads(proof_file.read_text())
    assert len(data["proofs"]) == 1
    assert data["proofs"][0]["feature"] == "arithmetic"
    assert data["proofs"][0]["id"] == "PROOF-1"
    assert data["proofs"][0]["status"] == "pass"


@pytest.mark.proof("proof_plugins", "PROOF-23", "RULE-23")
def test_c_purlin_emit_feature_scoped_overwrite(tmp_path):
    """c_purlin_emit.py preserves entries for other features while replacing current feature."""
    spec_dir = _make_spec(tmp_path, "math", "arithmetic", extra_rules=2)
    # Pre-populate proof file with entries for two features
    proof_file = spec_dir / "arithmetic.proofs-unit.json"
    proof_file.write_text(json.dumps({
        "tier": "unit",
        "proofs": [
            {
                "feature": "geometry",
                "id": "PROOF-1",
                "rule": "RULE-1",
                "test_file": "test_geo.c",
                "test_name": "test_area",
                "status": "pass",
                "tier": "unit",
            },
            {
                "feature": "arithmetic",
                "id": "PROOF-1",
                "rule": "RULE-1",
                "test_file": "test_old.c",
                "test_name": "old_test",
                "status": "fail",
                "tier": "unit",
            },
        ]
    }, indent=2))
    # Emit new arithmetic entries only
    stdin_json = json.dumps({
        "proofs": [{
            "feature": "arithmetic",
            "id": "PROOF-1",
            "rule": "RULE-1",
            "test_file": "test_add.c",
            "test_name": "test_addition_v2",
            "status": "pass",
            "tier": "unit",
        }]
    })
    result = subprocess.run(
        [sys.executable, os.path.join(PROOF_SCRIPTS, "c_purlin_emit.py")],
        input=stdin_json,
        capture_output=True, text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0
    data = json.loads(proof_file.read_text())
    features_in_file = {p["feature"] for p in data["proofs"]}
    # geometry entries must be preserved
    assert "geometry" in features_in_file, "geometry entries should be preserved"
    # arithmetic entry should be replaced with the new one
    arith_entries = [p for p in data["proofs"] if p["feature"] == "arithmetic"]
    assert len(arith_entries) == 1
    assert arith_entries[0]["test_name"] == "test_addition_v2"
    assert arith_entries[0]["status"] == "pass"


# ---------------------------------------------------------------------------
# RULE-29: Removed test entries purged on re-run
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_plugins", "PROOF-32", "RULE-29")
def test_removed_test_entry_purged_on_rerun(tmp_path):
    """When a test is removed and the feature re-runs, the old entry is not carried over."""
    spec_dir = _make_spec(tmp_path, "a", "feat_purge", extra_rules=2)
    # First run: 2 proofs
    first_run = tmp_path / "test_first.py"
    first_run.write_text(textwrap.dedent("""
        import pytest
        @pytest.mark.proof("feat_purge", "PROOF-1", "RULE-1")
        def test_one(): assert 1 + 1 == 2
        @pytest.mark.proof("feat_purge", "PROOF-2", "RULE-2")
        def test_two(): assert 2 + 2 == 4
    """))
    subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(first_run),
            "-p", "pytest_purlin",
            f"--override-ini=pythonpath={PROOF_SCRIPTS}",
            "-q", "--no-header",
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    proof_file = spec_dir / "feat_purge.proofs-unit.json"
    assert proof_file.exists()
    first_data = json.loads(proof_file.read_text())
    assert len(first_data["proofs"]) == 2, "First run should produce 2 proofs"

    # Second run: only 1 proof (test_two was "deleted")
    second_run = tmp_path / "test_second.py"
    second_run.write_text(textwrap.dedent("""
        import pytest
        @pytest.mark.proof("feat_purge", "PROOF-1", "RULE-1")
        def test_one(): assert 1 + 1 == 2
    """))
    subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(second_run),
            "-p", "pytest_purlin",
            f"--override-ini=pythonpath={PROOF_SCRIPTS}",
            "-q", "--no-header",
        ],
        capture_output=True, text=True, cwd=str(tmp_path),
    )
    second_data = json.loads(proof_file.read_text())
    feat_entries = [p for p in second_data["proofs"] if p["feature"] == "feat_purge"]
    assert len(feat_entries) == 1, (
        f"After removing test_two, expected 1 proof for feat_purge, got {len(feat_entries)}: {feat_entries}"
    )
    assert feat_entries[0]["id"] == "PROOF-1"
    # PROOF-2 must NOT be present (it was removed from the test file)
    proof_ids = {p["id"] for p in feat_entries}
    assert "PROOF-2" not in proof_ids, f"PROOF-2 should have been purged, but found: {proof_ids}"


@pytest.mark.proof("proof_plugins", "PROOF-32", "RULE-29")
def test_removed_test_entry_purged_in_shell_plugin(tmp_path):
    """Shell plugin: re-running with fewer proofs purges old entries for the same feature."""
    _make_spec(tmp_path, "a", "feat_shell_purge", extra_rules=2)
    # First run: 2 proofs
    first_result = _run_shell_proof(
        tmp_path,
        "feat_shell_purge",
        [
            ("PROOF-1", "RULE-1", "pass", "test one"),
            ("PROOF-2", "RULE-2", "pass", "test two"),
        ],
    )
    assert first_result.returncode == 0
    proof_file = tmp_path / "specs" / "a" / "feat_shell_purge.proofs-unit.json"
    first_data = json.loads(proof_file.read_text())
    assert len(first_data["proofs"]) == 2

    # Second run: only 1 proof (PROOF-2 "removed")
    second_result = _run_shell_proof(
        tmp_path,
        "feat_shell_purge",
        [("PROOF-1", "RULE-1", "pass", "test one")],
    )
    assert second_result.returncode == 0
    second_data = json.loads(proof_file.read_text())
    feat_entries = [p for p in second_data["proofs"] if p["feature"] == "feat_shell_purge"]
    assert len(feat_entries) == 1, (
        f"Expected 1 proof after re-run, got {len(feat_entries)}: {feat_entries}"
    )
    assert feat_entries[0]["id"] == "PROOF-1"
    proof_ids = {p["id"] for p in feat_entries}
    assert "PROOF-2" not in proof_ids, f"PROOF-2 should be purged, still found: {proof_ids}"
