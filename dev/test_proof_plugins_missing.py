"""Supplementary proof-plugin coverage: the edges the behavioural suite skips.

`dev/test_multilang_proof_plugins.py` proves the contract one arm per plugin.
This file covers what is left: the marker signatures each plugin accepts and
refuses, the tier defaults, the status mapping, the harness's own lifecycle,
and what happens when there is nothing to write.

  the shared contract  file naming, the no-marker no-op, purge on re-run
  pytest               marker arity, the registered markers, relative paths
  jest                 the title marker, the ignored title, status mapping
  shell                the five-argument call, the tier variable, BASH_SOURCE,
                       writing only at finish, clearing after finish
  sql                  the comment marker and the engine it runs against
"""

import json
import os
import shutil
import subprocess
import sys
import textwrap

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROOF_SCRIPTS = os.path.join(PROJECT_ROOT, "scripts", "proof")
JEST_REPORTER = os.path.join(PROOF_SCRIPTS, "jest_purlin.js")
SHELL_HARNESS = os.path.join(PROOF_SCRIPTS, "shell_purlin.sh")
SQL_HARNESS = os.path.join(PROOF_SCRIPTS, "sql_purlin.sh")
PROOF_REL = os.path.join(".purlin", "runtime", "proofs")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project(tmp_path, feature="feat", subdir="a"):
    """A project root with `specs/` and `.purlin/`."""
    (tmp_path / "specs" / subdir).mkdir(parents=True, exist_ok=True)
    (tmp_path / ".purlin").mkdir(parents=True, exist_ok=True)
    (tmp_path / "specs" / subdir / ("%s.md" % feature)).write_text(
        "# %s\n\n## Rules\n- RULE-1: a\n- RULE-2: b\n\n"
        "## Proof\n- PROOF-1 (RULE-1): t\n" % feature, encoding="utf-8")
    return tmp_path


def _proofs(root, feature, tier="unit"):
    path = os.path.join(str(root), PROOF_REL, "%s.%s.json" % (feature, tier))
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _proof_files(root):
    directory = os.path.join(str(root), PROOF_REL)
    try:
        return sorted(os.listdir(directory))
    except OSError:
        return []


def _run_pytest_with_plugin(tmp_path, test_code, allow_failure=False):
    """Run pytest with `pytest_purlin` loaded, in `tmp_path`."""
    test_file = tmp_path / "test_s.py"
    test_file.write_text(textwrap.dedent(test_code), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file),
         "-p", "pytest_purlin",
         "--override-ini=pythonpath=%s" % PROOF_SCRIPTS,
         "-q", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(tmp_path))
    if not allow_failure and result.returncode not in (0, 1):
        pytest.fail("pytest internal error:\n%s\n%s"
                    % (result.stdout, result.stderr))
    return result


def _jest_run_in_process(tmp_path, test_file_rel, test_results):
    """Invoke the jest reporter directly through node.

    Nothing is mocked: the reporter has no dependency outside node's own
    builtins, so it loads as shipped.
    """
    script = (
        "const path = require('path');\n"
        "const Reporter = require(%s);\n"
        "const r = new Reporter({rootDir: %s}, {});\n"
        "r.onTestResult(null, {testFilePath: path.join(%s, %s),"
        " testResults: %s});\n"
        "r.onRunComplete();\n"
        % (json.dumps(JEST_REPORTER), json.dumps(str(tmp_path)),
           json.dumps(str(tmp_path)), json.dumps(test_file_rel),
           json.dumps(test_results)))
    return subprocess.run(["node", "-e", script], capture_output=True,
                          text=True, cwd=str(tmp_path))


def _run_shell_proof(tmp_path, feature, proofs, tier=None, name="run_proof.sh"):
    """Call `purlin_proof` for each `(id, rule, status, name)`, then finish."""
    calls = "\n".join(
        'purlin_proof "%s" "%s" "%s" %s "%s"' % (feature, pid, rid, status, n)
        for pid, rid, status, n in proofs)
    script = textwrap.dedent("""\
        #!/usr/bin/env bash
        set -euo pipefail
        source %s
        %s
        %s
        purlin_proof_finish
    """) % (SHELL_HARNESS,
            "export PURLIN_PROOF_TIER=%s" % tier if tier else "",
            calls)
    path = tmp_path / name
    path.write_text(script, encoding="utf-8")
    return subprocess.run(["bash", str(path)], capture_output=True, text=True,
                          cwd=str(tmp_path))


# ---------------------------------------------------------------------------
# The shared contract
# ---------------------------------------------------------------------------

@pytest.mark.proof("proof_common", "PROOF-1", "RULE-1")
def test_proof_file_naming(tmp_path):
    """One file per feature and tier, under the runtime directory."""
    root = _project(tmp_path)
    _run_shell_proof(root, "feat", [("PROOF-1", "RULE-1", "pass", "a")])
    _run_shell_proof(root, "feat", [("PROOF-2", "RULE-2", "pass", "b")],
                     tier="integration", name="second.sh")
    _run_shell_proof(root, "other", [("PROOF-1", "RULE-1", "pass", "c")],
                     name="third.sh")
    assert _proof_files(root) == ["feat.integration.json", "feat.unit.json",
                                  "other.unit.json"]


@pytest.mark.proof("proof_common", "PROOF-9", "RULE-9")
def test_no_markers_no_proof_files(tmp_path):
    """A run that collected no marker writes nothing at all."""
    root = _project(tmp_path)
    _run_pytest_with_plugin(root, """
        def test_plain():
            assert 1 == 1
    """)
    assert _proof_files(root) == []


@pytest.mark.proof("proof_common", "PROOF-6", "RULE-6")
def test_removed_test_entry_purged_on_rerun(tmp_path):
    """A marker taken out of a file that runs again is reaped on that run."""
    root = _project(tmp_path)
    _run_pytest_with_plugin(root, """
        import pytest

        @pytest.mark.proof("feat", "PROOF-1", "RULE-1")
        def test_one():
            assert True

        @pytest.mark.proof("feat", "PROOF-2", "RULE-2")
        def test_two():
            assert True
    """)
    assert {e["id"] for e in _proofs(root, "feat")["proofs"]} == {"PROOF-1",
                                                                 "PROOF-2"}
    _run_pytest_with_plugin(root, """
        import pytest

        @pytest.mark.proof("feat", "PROOF-1", "RULE-1")
        def test_one():
            assert True
    """)
    assert {e["id"] for e in _proofs(root, "feat")["proofs"]} == {"PROOF-1"}


def test_removed_test_entry_purged_in_shell_plugin(tmp_path):
    root = _project(tmp_path)
    _run_shell_proof(root, "feat", [("PROOF-1", "RULE-1", "pass", "a"),
                                    ("PROOF-2", "RULE-2", "pass", "b")])
    assert len(_proofs(root, "feat")["proofs"]) == 2
    _run_shell_proof(root, "feat", [("PROOF-1", "RULE-1", "pass", "a")])
    assert [e["id"] for e in _proofs(root, "feat")["proofs"]] == ["PROOF-1"]


def test_a_feature_with_no_spec_still_records(tmp_path):
    """The runtime location needs no spec: nothing is scanned to find it."""
    root = _project(tmp_path)
    _run_shell_proof(root, "nospec", [("PROOF-1", "RULE-1", "pass", "a")])
    assert _proofs(root, "nospec") is not None


# ---------------------------------------------------------------------------
# pytest
# ---------------------------------------------------------------------------

def test_pytest_marker_signature_defaults_to_unit_tier(tmp_path):
    root = _project(tmp_path)
    _run_pytest_with_plugin(root, """
        import pytest

        @pytest.mark.proof("feat", "PROOF-1", "RULE-1")
        def test_one():
            assert True
    """)
    assert _proofs(root, "feat", "unit") is not None
    assert _proofs(root, "feat", "unit")["proofs"][0]["tier"] == "unit"


def test_pytest_marker_explicit_tier(tmp_path):
    root = _project(tmp_path)
    _run_pytest_with_plugin(root, """
        import pytest

        @pytest.mark.proof("feat", "PROOF-1", "RULE-1", tier="e2e")
        def test_one():
            assert True
    """)
    assert _proofs(root, "feat", "e2e") is not None


def test_pytest_marker_with_too_few_arguments_is_ignored(tmp_path):
    """A marker missing feature, id or rule names no proof, so it writes none."""
    root = _project(tmp_path)
    for args in ('"feat", "PROOF-1"', '"feat"'):
        _run_pytest_with_plugin(root, """
            import pytest

            @pytest.mark.proof(%s)
            def test_one():
                assert True
        """ % args)
        assert _proof_files(root) == []


def test_pytest_test_file_is_relative(tmp_path):
    root = _project(tmp_path)
    _run_pytest_with_plugin(root, """
        import pytest

        @pytest.mark.proof("feat", "PROOF-1", "RULE-1")
        def test_one():
            assert True
    """)
    recorded = _proofs(root, "feat")["proofs"][0]["test_file"]
    assert recorded == "test_s.py"
    assert not os.path.isabs(recorded)


def test_pytest_registers_the_proof_marker_and_the_tier_markers(tmp_path):
    """`-m` selects on the tier, which means the tier is a real marker."""
    root = _project(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--markers",
         "-p", "pytest_purlin",
         "--override-ini=pythonpath=%s" % PROOF_SCRIPTS,
         "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(root))
    for marker in ("proof(feature, proof_id, rule_id", "@pytest.mark.unit",
                   "@pytest.mark.integration", "@pytest.mark.e2e"):
        assert marker in result.stdout, marker

    _run_pytest_with_plugin(root, """
        import pytest

        @pytest.mark.proof("feat", "PROOF-1", "RULE-1")
        def test_unit_one():
            assert True

        @pytest.mark.proof("feat", "PROOF-2", "RULE-2", tier="e2e")
        def test_e2e_one():
            assert True
    """)
    deselected = subprocess.run(
        [sys.executable, "-m", "pytest", str(root / "test_s.py"),
         "-p", "pytest_purlin",
         "--override-ini=pythonpath=%s" % PROOF_SCRIPTS,
         "-m", "not e2e", "-q", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True, text=True, cwd=str(root))
    assert "1 deselected" in deselected.stdout


# ---------------------------------------------------------------------------
# jest
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not shutil.which("node"), reason="node not available")
class TestJest:

    def test_marker_parsed_from_title(self, tmp_path):
        root = _project(tmp_path)
        (root / "a.test.js").write_text("// marked\n", encoding="utf-8")
        self._ran(root, [{"title": "does it "
                                   "[proof:feat:PROOF-1:RULE-1:integration]",
                          "status": "passed"}])
        entry = _proofs(root, "feat", "integration")["proofs"][0]
        assert (entry["feature"], entry["id"], entry["rule"], entry["tier"]) \
            == ("feat", "PROOF-1", "RULE-1", "integration")

    def test_tier_defaults_to_unit(self, tmp_path):
        root = _project(tmp_path)
        (root / "a.test.js").write_text("// marked\n", encoding="utf-8")
        self._ran(root, [{"title": "does it [proof:feat:PROOF-1:RULE-1]",
                          "status": "passed"}])
        assert _proofs(root, "feat", "unit") is not None

    def test_a_title_with_no_marker_is_ignored(self, tmp_path):
        root = _project(tmp_path)
        (root / "a.test.js").write_text("// marked\n", encoding="utf-8")
        self._ran(root, [{"title": "does it", "status": "passed"},
                         {"title": "[proof:feat:PROOF-1:RULE-1]",
                          "status": "passed"}])
        entries = _proofs(root, "feat")["proofs"]
        assert len(entries) == 1

    def test_status_mapping(self, tmp_path):
        root = _project(tmp_path)
        (root / "a.test.js").write_text("// marked\n", encoding="utf-8")
        self._ran(root, [{"title": "ok [proof:feat:PROOF-1:RULE-1]",
                          "status": "passed"},
                         {"title": "no [proof:feat:PROOF-2:RULE-2]",
                          "status": "failed"}])
        by_id = {e["id"]: e["status"] for e in _proofs(root, "feat")["proofs"]}
        assert by_id == {"PROOF-1": "pass", "PROOF-2": "fail"}

    def test_the_test_file_is_relative_to_the_project_root(self, tmp_path):
        root = _project(tmp_path)
        (root / "src").mkdir()
        (root / "src" / "a.test.js").write_text("// marked\n",
                                                encoding="utf-8")
        self._ran(root, [{"title": "ok [proof:feat:PROOF-1:RULE-1]",
                          "status": "passed"}], rel="src/a.test.js")
        assert _proofs(root, "feat")["proofs"][0]["test_file"] \
            == "src/a.test.js"

    def _ran(self, root, results, rel="a.test.js"):
        result = _jest_run_in_process(root, rel, results)
        assert result.returncode == 0, result.stderr
        return result


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------

def test_shell_proof_uses_purlin_proof_tier_env(tmp_path):
    root = _project(tmp_path)
    _run_shell_proof(root, "feat", [("PROOF-1", "RULE-1", "pass", "a")],
                     tier="integration")
    assert _proofs(root, "feat", "integration") is not None
    assert _proofs(root, "feat", "unit") is None


def test_shell_proof_defaults_tier_to_unit(tmp_path):
    root = _project(tmp_path)
    _run_shell_proof(root, "feat", [("PROOF-1", "RULE-1", "pass", "a")])
    assert _proofs(root, "feat", "unit") is not None


def test_shell_test_file_reflects_the_calling_script(tmp_path):
    """`BASH_SOURCE[1]` is the caller, not the harness."""
    root = _project(tmp_path)
    _run_shell_proof(root, "feat", [("PROOF-1", "RULE-1", "pass", "a")],
                     name="my_suite.sh")
    assert _proofs(root, "feat")["proofs"][0]["test_file"] == "my_suite.sh"


@pytest.mark.proof("run_script", "PROOF-47", "RULE-38")
def test_shell_proof_not_written_before_finish(tmp_path):
    """`purlin_proof` buffers; only `purlin_proof_finish` writes."""
    root = _project(tmp_path)
    script = textwrap.dedent("""\
        #!/usr/bin/env bash
        set -euo pipefail
        source %s
        purlin_proof "feat" "PROOF-1" "RULE-1" pass "a"
    """) % SHELL_HARNESS
    (root / "buffered.sh").write_text(script, encoding="utf-8")
    subprocess.run(["bash", str(root / "buffered.sh")], cwd=str(root),
                   capture_output=True, text=True)
    assert _proof_files(root) == []


@pytest.mark.proof("run_script", "PROOF-47", "RULE-38")
def test_shell_entries_cleared_after_finish(tmp_path):
    """A second finish with nothing buffered rewrites nothing."""
    root = _project(tmp_path)
    script = textwrap.dedent("""\
        #!/usr/bin/env bash
        set -euo pipefail
        source %s
        purlin_proof "feat" "PROOF-1" "RULE-1" pass "a"
        purlin_proof_finish
        purlin_proof "feat" "PROOF-2" "RULE-2" pass "b"
        purlin_proof_finish
    """) % SHELL_HARNESS
    (root / "twice.sh").write_text(script, encoding="utf-8")
    subprocess.run(["bash", str(root / "twice.sh")], cwd=str(root),
                   capture_output=True, text=True)
    # The second finish carried only PROOF-2, which replaced the first write
    # for the same (feature, tier, test_file): the buffer was cleared, so
    # PROOF-1 was not written a second time.
    ids = [e["id"] for e in _proofs(root, "feat")["proofs"]]
    assert ids == ["PROOF-2"]


@pytest.mark.proof("run_script", "PROOF-47", "RULE-38")
def test_shell_finish_with_nothing_buffered_writes_nothing(tmp_path):
    root = _project(tmp_path)
    _run_shell_proof(root, "feat", [])
    assert _proof_files(root) == []


# ---------------------------------------------------------------------------
# sql
# ---------------------------------------------------------------------------

@pytest.mark.skipif(shutil.which("sqlite3") is None,
                    reason="sqlite3 not available")
class TestSql:

    def test_a_failing_block_records_fail(self, tmp_path):
        root = _project(tmp_path)
        self._run(root, "-- @purlin feat PROOF-1 RULE-1 unit\n"
                        "-- Test: it fails\n"
                        "SELECT 'FAIL';\n")
        assert _proofs(root, "feat")["proofs"][0]["status"] == "fail"

    def test_a_file_with_no_marker_writes_nothing(self, tmp_path):
        root = _project(tmp_path)
        result = self._run(root, "SELECT 1;\n")
        assert result.returncode == 0
        assert _proof_files(root) == []

    @pytest.mark.proof("run_script", "PROOF-4", "RULE-4")
    def test_the_engine_comes_from_the_config(self, tmp_path):
        """`sql_engine` names the command; a bad one fails every block."""
        root = _project(tmp_path)
        (root / ".purlin" / "config.json").write_text(
            json.dumps({"sql_engine": "no-such-engine"}), encoding="utf-8")
        self._run(root, "-- @purlin feat PROOF-1 RULE-1 unit\n"
                        "SELECT 'PASS';\n")
        assert _proofs(root, "feat")["proofs"][0]["status"] == "fail"

    def _run(self, root, body):
        (root / "tests").mkdir(exist_ok=True)
        (root / "tests" / "test_x.sql").write_text(body, encoding="utf-8")
        return subprocess.run(
            ["bash", SQL_HARNESS, "tests/test_x.sql"],
            capture_output=True, text=True, cwd=str(root))
