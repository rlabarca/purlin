"""Tests for pre_push_hook, RULE-1 through RULE-16.

Each test creates an isolated temp git project, manipulates proof files, then
runs scripts/hooks/pre-push.sh (or the gate it delegates the verdict to)
directly. Tests are tagged @integration because they spawn subprocesses and
write to temp directories.

Proof markers use tier="integration" to match the @integration tier declared in
the spec's Proof section.
"""

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOOK_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "hooks", "pre-push.sh")
GATE_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "hooks", "pre_push_gate.py")
SERVER_PY = os.path.join(PROJECT_ROOT, "scripts", "mcp", "purlin_server.py")
SERVER_DIR = os.path.join(PROJECT_ROOT, "scripts", "mcp")

if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Box drawing and block elements. The verdict is read from the structured
# payload, so no glyph of the rendered table may appear in either hook file.
BOX_DRAWING_RE = re.compile(r"[─-╿]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: str, data: object) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)


def _copy_plugin(tmpdir: str, with_gate: bool = True) -> None:
    """Copy the pieces of the framework a temp project needs to be checkable.

    A project carrying scripts/mcp/purlin_server.py and
    scripts/hooks/pre_push_gate.py is what the hook calls a dev checkout: the
    last plugin-root candidate it tries, and the one an installed copy of the
    hook in .git/hooks has to fall back to.
    """
    os.makedirs(os.path.join(tmpdir, "scripts", "mcp"), exist_ok=True)
    for fname in ("purlin_server.py", "config_engine.py", "__init__.py"):
        src = os.path.join(PROJECT_ROOT, "scripts", "mcp", fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(tmpdir, "scripts", "mcp", fname))
    if with_gate:
        os.makedirs(os.path.join(tmpdir, "scripts", "hooks"), exist_ok=True)
        shutil.copy2(GATE_SCRIPT,
                     os.path.join(tmpdir, "scripts", "hooks",
                                  "pre_push_gate.py"))


def _git(tmpdir: str, *args: str) -> None:
    subprocess.run(["git"] + list(args), cwd=tmpdir, check=True,
                   capture_output=True)


def _commit(tmpdir: str, message: str) -> None:
    _git(tmpdir, "add", "-A")
    _git(tmpdir, "commit", "-q", "-m", message, "--allow-empty")


def _spec_text(feature: str, num_rules: int, tags: dict | None = None) -> str:
    tags = tags or {}
    lines = [
        f"# Feature: {feature}",
        "",
        "## What it does",
        "",
        "A test feature for pre-push hook testing.",
        "",
        "## Rules",
        "",
    ]
    for i in range(1, num_rules + 1):
        lines.append(f"- RULE-{i}: Test rule {i} must hold")
    lines += ["", "## Proof", ""]
    for i in range(1, num_rules + 1):
        tag = tags.get(f"PROOF-{i}", "")
        suffix = f" {tag}" if tag else ""
        lines.append(
            f"- PROOF-{i} (RULE-{i}): Run the {feature} code path {i} and "
            f"verify it returns 1{suffix}")
    return "\n".join(lines) + "\n"


def _create_test_project(tmpdir: str, num_rules: int = 3,
                         with_gate: bool = True,
                         feature: str = "test_feature",
                         spec_subdir: str = "specs/hooks",
                         config_extra: dict | None = None,
                         proof_tags: dict | None = None) -> None:
    """Initialise a minimal Purlin project with a single feature spec."""
    os.makedirs(os.path.join(tmpdir, ".purlin"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, *spec_subdir.split("/")), exist_ok=True)

    config = {
        "version": "0.9.0",
        "test_framework": "auto",
        "spec_dir": "specs",
        "pre_push": "warn",
    }
    config.update(config_extra or {})
    _write_json(os.path.join(tmpdir, ".purlin", "config.json"), config)

    _copy_plugin(tmpdir, with_gate=with_gate)

    spec_path = os.path.join(tmpdir, *spec_subdir.split("/"),
                             f"{feature}.md")
    with open(spec_path, "w") as fh:
        fh.write(_spec_text(feature, num_rules, proof_tags))

    subprocess.run(["git", "init", "-q"], cwd=tmpdir, check=True,
                   capture_output=True)
    _commit(tmpdir, "init")


def _write_proof_file(tmpdir: str, feature: str,
                      entries: list, spec_subdir: str = "specs/hooks") -> None:
    """Write a proofs-unit.json file.

    entries: list of (proof_id, rule_id, status) tuples, e.g.
        [("PROOF-1", "RULE-1", "pass"), ("PROOF-2", "RULE-2", "fail")]
    """
    proofs = []
    for proof_id, rule_id, status in entries:
        proofs.append({
            "feature": feature,
            "id": proof_id,
            "rule": rule_id,
            "test_file": "dev/test_example.sh",
            "test_name": f"test {proof_id}",
            "status": status,
            "tier": "unit",
        })
    out_path = os.path.join(tmpdir, *spec_subdir.split("/"),
                            f"{feature}.proofs-unit.json")
    _write_json(out_path, {"tier": "unit", "proofs": proofs})


def _clean_env() -> dict:
    """os.environ without the plugin-root hints, so a test controls them."""
    env = dict(os.environ)
    env.pop("PURLIN_PLUGIN_ROOT", None)
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    return env


def _run_hook(tmpdir: str, script: str = HOOK_SCRIPT,
              env: dict | None = None) -> tuple:
    """Run the hook inside tmpdir, return (exit_code, combined_output)."""
    result = subprocess.run(
        ["bash", script], cwd=tmpdir, capture_output=True, text=True,
        env=env if env is not None else _clean_env(),
    )
    return result.returncode, result.stdout + result.stderr


def _run_gate(tmpdir: str, *args: str) -> tuple:
    """Run the gate directly, return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        ["python3", GATE_SCRIPT] + list(args), cwd=tmpdir,
        capture_output=True, text=True, env=_clean_env(),
    )
    return result.returncode, result.stdout, result.stderr


def _set_config_field(tmpdir: str, key: str, value) -> None:
    cfg_path = os.path.join(tmpdir, ".purlin", "config.json")
    with open(cfg_path) as fh:
        cfg = json.load(fh)
    cfg[key] = value
    _write_json(cfg_path, cfg)


def _issue_receipts(tmpdir: str) -> None:
    """Receipt a temp project through the real issuer.

    Through the issuer, never by hand: a hand-written receipt shape is free to
    drift from the one purlin:verify writes, and then the test proves the hook
    agrees with a fiction.
    """
    import issue_receipts

    issue_receipts.write_run_marker(tmpdir)
    issue_receipts.main(tmpdir, quiet=True)


# ---------------------------------------------------------------------------
# RULE-1: FAILING blocks the push
# ---------------------------------------------------------------------------

class TestRule1FailingBlocks:

    @pytest.mark.proof("pre_push_hook", "PROOF-1", "RULE-1", tier="integration")
    def test_fail_proof_blocks_with_exit_1(self, tmp_path):
        """One FAIL entry in a proof file blocks the push: exit 1 and
        PUSH BLOCKED in the output."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "fail"),
            ("PROOF-3", "RULE-3", "pass"),
        ])
        _commit(tmpdir, "failing proof")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, (
            f"Expected exit 1 on a FAIL proof, got {exit_code}\n{output}")
        assert "PUSH BLOCKED" in output, (
            f"Expected 'PUSH BLOCKED' in output:\n{output}")

    @pytest.mark.proof("pre_push_hook", "PROOF-8", "RULE-1", tier="integration")
    def test_lifecycle_fail_then_partial_then_complete(self, tmp_path):
        """Full lifecycle in one project: a FAIL blocks with exit 1; fixing it
        to pass while one rule stays unproved allows the push with a partial
        coverage line; proving the last rule allows it with the feature listed
        PASSING (3/3 rules proved) and no PUSH BLOCKED anywhere."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)

        # Phase 1: one FAIL, one PASS, one unproved.
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "fail"),
        ])
        _commit(tmpdir, "one failing proof")
        ec1, out1 = _run_hook(tmpdir)
        assert ec1 == 1, f"Phase 1 expected exit 1, got {ec1}\n{out1}"
        assert "PUSH BLOCKED" in out1, f"Phase 1 output:\n{out1}"

        # Phase 2: FAIL fixed, RULE-3 still unproved.
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "pass"),
        ])
        _commit(tmpdir, "fix the failing proof")
        ec2, out2 = _run_hook(tmpdir)
        assert ec2 == 0, f"Phase 2 expected exit 0, got {ec2}\n{out2}"
        assert "PUSH BLOCKED" not in out2, f"Phase 2 output:\n{out2}"
        assert "partial coverage" in out2.lower(), f"Phase 2 output:\n{out2}"
        assert "PARTIAL (2/3 rules proved)" in out2, f"Phase 2 output:\n{out2}"

        # Phase 3: every rule proved.
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "pass"),
            ("PROOF-3", "RULE-3", "pass"),
        ])
        _commit(tmpdir, "prove the last rule")
        ec3, out3 = _run_hook(tmpdir)
        assert ec3 == 0, f"Phase 3 expected exit 0, got {ec3}\n{out3}"
        assert "PUSH BLOCKED" not in out3, f"Phase 3 output:\n{out3}"
        assert "PASSING (3/3 rules proved)" in out3, f"Phase 3 output:\n{out3}"


# ---------------------------------------------------------------------------
# RULE-2: partial coverage allows push with warning
# ---------------------------------------------------------------------------

class TestRule2PartialAllows:

    @pytest.mark.proof("pre_push_hook", "PROOF-2", "RULE-2", tier="integration")
    def test_partial_coverage_exits_0_with_warning(self, tmp_path):
        """Proof file covers 2 of 3 rules (no FAIL): the hook must exit 0 with
        a 'partial coverage' warning in stdout."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "pass"),
        ])

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, (
            f"Expected exit 0 (partial coverage allowed in warn mode), "
            f"got {exit_code}\n{output}")
        assert "partial coverage" in output.lower(), (
            f"Expected 'partial coverage' in output, got:\n{output}")
        assert "PUSH BLOCKED" not in output, (
            f"Unexpected PUSH BLOCKED in output:\n{output}")


# ---------------------------------------------------------------------------
# RULE-3: no specs means a silent exit 0
# ---------------------------------------------------------------------------

class TestRule3NoSpecsSilent:

    @pytest.mark.proof("pre_push_hook", "PROOF-3", "RULE-3", tier="integration")
    def test_no_specs_dir_exits_0_silently(self, tmp_path):
        """When no specs/ directory exists the hook must exit 0 with empty
        stdout: it has nothing to check."""
        tmpdir = str(tmp_path)
        os.makedirs(os.path.join(tmpdir, ".purlin"))
        _write_json(os.path.join(tmpdir, ".purlin", "config.json"),
                    {"version": "0.9.0", "test_framework": "auto"})
        subprocess.run(["git", "init", "-q"], cwd=tmpdir, check=True,
                       capture_output=True)
        _commit(tmpdir, "init")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, f"Expected exit 0 (no specs), got {exit_code}\n{output}"
        assert output.strip() == "", (
            f"Expected empty output when no specs exist, got:\n{output!r}")


# ---------------------------------------------------------------------------
# RULE-4: all rules proved means exit 0
# ---------------------------------------------------------------------------

class TestRule4AllPassingAllows:

    @pytest.mark.proof("pre_push_hook", "PROOF-4", "RULE-4", tier="integration")
    def test_all_pass_exits_0(self, tmp_path):
        """All 3 rules proved with pass status: the hook exits 0 and never
        prints PUSH BLOCKED."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "pass"),
            ("PROOF-3", "RULE-3", "pass"),
        ])

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, (
            f"Expected exit 0 (all passing), got {exit_code}\n{output}")
        assert "PUSH BLOCKED" not in output, (
            f"Unexpected PUSH BLOCKED in output:\n{output}")

    @pytest.mark.proof("pre_push_hook", "PROOF-12", "RULE-4", tier="integration")
    def test_fail_keyword_in_rule_description_does_not_block(self, tmp_path):
        """A rule description containing the word FAIL must not cause a
        false-positive block when all proofs actually pass. This guards against
        naive string matching on rule text rather than status fields."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=0)

        spec_content = "\n".join([
            "# Feature: test_feature",
            "",
            "## Rules",
            "",
            "- RULE-1: FAIL status badge is solid red pill with white text",
            "- RULE-2: PASSING badge is green pill",
            "",
            "## Proof",
            "",
            "- PROOF-1 (RULE-1): Render the badge for a failed rule and verify "
            "the pill background is #d13438",
            "- PROOF-2 (RULE-2): Render the badge for a passing rule and verify "
            "the pill background is #107c10",
            "",
        ])
        with open(os.path.join(tmpdir, "specs", "hooks", "test_feature.md"),
                  "w") as fh:
            fh.write(spec_content)

        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "pass"),
        ])
        _commit(tmpdir, "spec-with-FAIL-in-desc")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, (
            f"Rule description containing 'FAIL' caused a false-positive block "
            f"(exit {exit_code}):\n{output}")
        assert "PUSH BLOCKED" not in output, (
            f"False-positive PUSH BLOCKED:\n{output}")


# ---------------------------------------------------------------------------
# RULE-5: framework list and auto-detection
# ---------------------------------------------------------------------------

class TestRule5FrameworkDetection:

    @pytest.mark.proof("pre_push_hook", "PROOF-5", "RULE-5", tier="integration")
    def test_framework_from_config_and_auto(self, tmp_path):
        """`pre_push_gate.py config` prints frameworks=pytest for
        {"test_framework": "pytest"}, frameworks=jest for "jest", and
        frameworks=pytest for "auto" once conftest.py exists."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=1)

        _set_config_field(tmpdir, "test_framework", "pytest")
        rc, out, _err = _run_gate(tmpdir, "config", "--project-root", tmpdir)
        assert rc == 0, out
        assert "frameworks=pytest" in out, out

        _set_config_field(tmpdir, "test_framework", "jest")
        rc, out, _err = _run_gate(tmpdir, "config", "--project-root", tmpdir)
        assert rc == 0, out
        assert "frameworks=jest" in out, out

        _set_config_field(tmpdir, "test_framework", "auto")
        open(os.path.join(tmpdir, "conftest.py"), "w").close()
        rc, out, _err = _run_gate(tmpdir, "config", "--project-root", tmpdir)
        assert rc == 0, out
        assert "frameworks=pytest" in out, out

    @pytest.mark.proof("pre_push_hook", "PROOF-25", "RULE-5", tier="integration")
    def test_comma_list_deduped_unknown_reported_on_stderr(self, tmp_path):
        """test_framework "pytest, bogus ,pytest,shell" resolves to
        frameworks=pytest,shell on stdout: split on commas, trimmed, deduped,
        order kept. "bogus" is named on stderr and appears nowhere in the
        frameworks line, so no runner arm is selected for it."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=1)
        _set_config_field(tmpdir, "test_framework", "pytest, bogus ,pytest,shell")

        rc, out, err = _run_gate(tmpdir, "config", "--project-root", tmpdir)
        assert rc == 0, f"{out}\n{err}"
        assert "frameworks=pytest,shell" in out, out
        assert "bogus" in err, f"Expected 'bogus' named on stderr, got:\n{err}"
        assert "bogus" not in out, out


# ---------------------------------------------------------------------------
# RULE-15: what the gate writes to stderr reaches the developer
# ---------------------------------------------------------------------------

class TestRule15StderrReachesTheUser:

    @pytest.mark.proof("pre_push_hook", "PROOF-24", "RULE-15", tier="integration")
    def test_gate_stderr_is_not_swallowed_by_the_hook(self, tmp_path):
        """The hook captures only the gate's stdout, so the gate's warning
        about the unknown framework "bogus" reaches the caller: assert exit 0
        and 'bogus' in the hook's combined output, and assert the script
        contains zero occurrences of 2>/dev/null."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=1)
        _set_config_field(tmpdir, "test_framework", "bogus,shell")
        _write_proof_file(tmpdir, "test_feature",
                          [("PROOF-1", "RULE-1", "pass")])
        _commit(tmpdir, "unknown framework named in config")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, f"{exit_code}\n{output}"
        assert "bogus" in output, (
            f"The gate's stderr did not reach the caller:\n{output}")

        with open(HOOK_SCRIPT, encoding="utf-8") as fh:
            script = fh.read()
        assert "2>/dev/null" not in script, (
            "pre-push.sh redirects stderr to /dev/null, which hides the "
            "reason a push was allowed or blocked")


# ---------------------------------------------------------------------------
# RULE-6: only unit-tier tests run, and a crashed runner blocks
# ---------------------------------------------------------------------------

class TestRule6UnitTierOnly:

    @pytest.mark.proof("pre_push_hook", "PROOF-6", "RULE-6", tier="integration")
    def test_unit_test_runs_integration_skipped(self, tmp_path):
        """The hook invokes pytest with -m 'not integration'. A plain test
        function must run (sentinel created); a function marked @integration
        must be skipped (no sentinel)."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=1)
        _write_proof_file(tmpdir, "test_feature",
                          [("PROOF-1", "RULE-1", "pass")])

        # auto plus conftest.py resolves to pytest.
        _set_config_field(tmpdir, "test_framework", "auto")
        open(os.path.join(tmpdir, "conftest.py"), "w").close()

        sentinel_unit = os.path.join(tmpdir, ".sentinel_unit")
        sentinel_int = os.path.join(tmpdir, ".sentinel_integration")

        with open(os.path.join(tmpdir, "test_unit_tier.py"), "w") as fh:
            fh.write(f'def test_unit_runs():\n'
                     f'    open("{sentinel_unit}", "w").close()\n')
        with open(os.path.join(tmpdir, "test_integration_tier.py"), "w") as fh:
            fh.write(f'import pytest\n\n'
                     f'@pytest.mark.integration\n'
                     f'def test_integration_skipped():\n'
                     f'    open("{sentinel_int}", "w").close()\n')

        for p in (sentinel_unit, sentinel_int):
            if os.path.exists(p):
                os.remove(p)

        _run_hook(tmpdir)

        assert os.path.exists(sentinel_unit), (
            "Unit test did not run: the hook should invoke pytest -m 'not integration'")
        assert not os.path.exists(sentinel_int), (
            "Integration-marked test ran: the hook should have excluded it")

    @pytest.mark.proof("pre_push_hook", "PROOF-21", "RULE-6", tier="integration")
    def test_crashed_runner_blocks_even_with_all_pass_proofs(self, tmp_path):
        """A conftest.py that raises at import makes pytest exit non-zero. With
        an all-pass proof file already on disk the status alone would exit 0,
        so the block has to come from the runner: assert exit 1 and output
        naming pytest and its exit code."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=1)
        # Stale evidence: the proof file says everything passed.
        _write_proof_file(tmpdir, "test_feature",
                          [("PROOF-1", "RULE-1", "pass")])
        _set_config_field(tmpdir, "test_framework", "pytest")
        with open(os.path.join(tmpdir, "conftest.py"), "w") as fh:
            fh.write('raise RuntimeError("conftest import blew up")\n')
        _commit(tmpdir, "broken conftest")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, (
            f"A crashed runner must block the push, got exit {exit_code}\n{output}")
        assert "pytest" in output, (
            f"The block must name the runner that crashed:\n{output}")
        assert "PUSH BLOCKED" in output, f"{output}"


# ---------------------------------------------------------------------------
# RULE-7: output shows what passed, what is partial, what is blocked
# ---------------------------------------------------------------------------

class TestRule7OutputFormat:

    @pytest.mark.proof("pre_push_hook", "PROOF-7", "RULE-7", tier="integration")
    def test_output_shows_blocked_and_recovery_on_fail(self, tmp_path):
        """When a proof has FAIL status the output must contain PUSH BLOCKED,
        the failing feature's name, and RECOVERY STEPS."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "fail"),
        ])

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, f"Expected exit 1 on FAIL proof, got {exit_code}\n{output}"
        assert "PUSH BLOCKED" in output, f"{output}"
        assert "test_feature" in output, f"{output}"
        assert "RECOVERY STEPS" in output, f"{output}"

    @pytest.mark.proof("pre_push_hook", "PROOF-13", "RULE-7", tier="integration")
    def test_recovery_message_lists_feature_specific_commands(self, tmp_path):
        """The recovery message must include /purlin:test <feature_name>,
        /purlin:status and /purlin:build so the developer knows exactly which
        commands to run."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=2)
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "fail"),
            ("PROOF-2", "RULE-2", "pass"),
        ])
        _commit(tmpdir, "failing-proof")

        _, output = _run_hook(tmpdir)

        assert "/purlin:test test_feature" in output, f"{output}"
        assert "/purlin:status" in output, f"{output}"
        assert "/purlin:build" in output, f"{output}"


# ---------------------------------------------------------------------------
# RULE-8: strict mode blocks everything that is not VERIFIED
# ---------------------------------------------------------------------------

class TestRule8StrictMode:

    @pytest.mark.proof("pre_push_hook", "PROOF-9", "RULE-8", tier="integration")
    def test_strict_mode_blocks_partial_coverage(self, tmp_path):
        """Strict mode: partial coverage (2 of 3 rules proved, no FAIL) blocks
        the push with exit 1 and 'strict mode' in the output."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        _set_config_field(tmpdir, "pre_push", "strict")
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "pass"),
        ])

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, (
            f"Expected exit 1 in strict mode with partial coverage, "
            f"got {exit_code}\n{output}")
        assert "strict mode" in output.lower(), f"{output}"

    @pytest.mark.proof("pre_push_hook", "PROOF-10", "RULE-8", tier="integration")
    def test_strict_mode_blocks_passing_until_receipted(self, tmp_path):
        """Strict mode's boundary is the receipt, not the coverage. With both
        rules proved and no receipt the feature is PASSING: assert exit 1 and
        'strict mode'. Commit, issue receipts through dev/issue_receipts.py,
        and the same project exits 0."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=2)
        _set_config_field(tmpdir, "pre_push", "strict")
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "pass"),
        ])
        _commit(tmpdir, "all rules proved, no receipt")

        exit_passing, out_passing = _run_hook(tmpdir)
        assert exit_passing == 1, (
            f"Strict mode must block a PASSING feature with no receipt, "
            f"got exit {exit_passing}\n{out_passing}")
        assert "strict mode" in out_passing.lower(), f"{out_passing}"
        assert "PASSING (2/2 rules proved)" in out_passing, f"{out_passing}"

        _issue_receipts(tmpdir)
        exit_verified, out_verified = _run_hook(tmpdir)
        assert exit_verified == 0, (
            f"Strict mode must allow a VERIFIED feature, got exit "
            f"{exit_verified}\n{out_verified}")
        assert "PUSH BLOCKED" not in out_verified, f"{out_verified}"

    @pytest.mark.proof("pre_push_hook", "PROOF-14", "RULE-8", tier="integration")
    def test_strict_mode_recovery_includes_verify_command(self, tmp_path):
        """When strict mode blocks a push the recovery steps must include
        RECOVERY STEPS, /purlin:verify and /purlin:test so the developer knows
        how to reach VERIFIED."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        _set_config_field(tmpdir, "pre_push", "strict")
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "pass"),
        ])
        _commit(tmpdir, "partial-strict")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, f"Expected exit 1 in strict mode, got {exit_code}\n{output}"
        assert "RECOVERY STEPS" in output, f"{output}"
        assert "/purlin:verify" in output, f"{output}"
        assert "/purlin:test" in output, f"{output}"

    @pytest.mark.proof("pre_push_hook", "PROOF-27", "RULE-8", tier="integration")
    def test_awaiting_runner_is_one_advisory_line_and_never_blocks(self, tmp_path):
        """A proof tagged @on(win11) with no result on win11 prints one
        advisory line naming win11 and never changes the verdict: exit 0 in
        warn mode, and exit 0 in strict mode once the feature is receipted,
        with the advisory line still printed."""
        tmpdir = str(tmp_path)
        _create_test_project(
            tmpdir, num_rules=2,
            config_extra={"platforms": {"win11": {"os": "windows",
                                                  "version": "11"}}},
            proof_tags={"PROOF-2": "@on(win11)"})
        _write_proof_file(tmpdir, "test_feature",
                          [("PROOF-1", "RULE-1", "pass")])
        _commit(tmpdir, "one proof awaiting a runner")

        exit_warn, out_warn = _run_hook(tmpdir)
        assert exit_warn == 0, (
            f"awaiting_runner must never block, got exit {exit_warn}\n{out_warn}")
        advisory = [ln for ln in out_warn.splitlines()
                    if "win11" in ln and "advisory only" in ln]
        assert len(advisory) == 1, (
            f"Expected exactly 1 advisory line naming win11, got "
            f"{len(advisory)}:\n{out_warn}")

        _issue_receipts(tmpdir)
        _set_config_field(tmpdir, "pre_push", "strict")
        exit_strict, out_strict = _run_hook(tmpdir)
        assert exit_strict == 0, (
            f"awaiting_runner must never block in strict mode either, got "
            f"exit {exit_strict}\n{out_strict}")
        assert "advisory only" in out_strict, f"{out_strict}"


# ---------------------------------------------------------------------------
# RULE-9: after purlin:init the installed hook exists and is executable
# ---------------------------------------------------------------------------

class TestRule9HookInstalled:

    @pytest.mark.proof("pre_push_hook", "PROOF-11", "RULE-9", tier="integration")
    def test_installed_hook_exists_is_executable_and_blocks(self, tmp_path):
        """Simulates what purlin:init does: copies pre-push.sh to
        .git/hooks/pre-push and makes it executable. The installed hook must be
        present, executable, and actually intercept a push carrying a FAIL
        proof (exit 1 and PUSH BLOCKED)."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)

        git_hooks_dir = os.path.join(tmpdir, ".git", "hooks")
        os.makedirs(git_hooks_dir, exist_ok=True)
        installed_hook = os.path.join(git_hooks_dir, "pre-push")
        shutil.copy2(HOOK_SCRIPT, installed_hook)
        os.chmod(installed_hook, os.stat(installed_hook).st_mode
                 | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        assert os.path.isfile(installed_hook), (
            ".git/hooks/pre-push does not exist after install")
        assert os.access(installed_hook, os.X_OK), (
            ".git/hooks/pre-push is not executable after install")

        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "fail"),
            ("PROOF-3", "RULE-3", "pass"),
        ])
        _commit(tmpdir, "failing-proofs")

        exit_code, output = _run_hook(tmpdir, script=installed_hook)

        assert exit_code == 1, (
            f"Expected the installed hook to exit 1 on a FAIL proof, got "
            f"{exit_code}\n{output}")
        assert "PUSH BLOCKED" in output, f"{output}"


# ---------------------------------------------------------------------------
# RULE-10: the verdict comes from the payload, never the rendered table
# ---------------------------------------------------------------------------

class TestRule10PayloadNotTable:

    @pytest.mark.proof("pre_push_hook", "PROOF-18", "RULE-10", tier="integration")
    def test_table_shaped_rule_text_does_not_change_the_verdict(self, tmp_path):
        """A rule whose description is itself a rendered table row reading
        FAILING, with every proof passing, exits 0 with no PUSH BLOCKED: the
        verdict came from the payload. Both hook files also contain zero
        characters in the box drawing range U+2500 to U+257F, so there is no
        table left to parse."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=0)

        row = "│ test_feature │ 0/3 │ FAILING │"
        spec_content = "\n".join([
            "# Feature: test_feature",
            "",
            "## Rules",
            "",
            f"- RULE-1: The summary row renders as `{row}`",
            "",
            "## Proof",
            "",
            "- PROOF-1 (RULE-1): Render the summary table for a 0/3 feature "
            f"and verify the row equals `{row}`",
            "",
        ])
        with open(os.path.join(tmpdir, "specs", "hooks", "test_feature.md"),
                  "w") as fh:
            fh.write(spec_content)
        _write_proof_file(tmpdir, "test_feature",
                          [("PROOF-1", "RULE-1", "pass")])
        _commit(tmpdir, "table-shaped rule text")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, (
            f"Table-shaped rule text changed the verdict (exit {exit_code}):\n"
            f"{output}")
        assert "PUSH BLOCKED" not in output, f"{output}"

        for path in (HOOK_SCRIPT, GATE_SCRIPT):
            with open(path, encoding="utf-8") as fh:
                found = BOX_DRAWING_RE.findall(fh.read())
            assert found == [], (
                f"{os.path.basename(path)} still carries box drawing glyphs: "
                f"{sorted(set(found))}")


# ---------------------------------------------------------------------------
# RULE-11: off
# ---------------------------------------------------------------------------

class TestRule11OffMode:

    @pytest.mark.proof("pre_push_hook", "PROOF-19", "RULE-11", tier="integration")
    def test_off_prints_one_line_and_exits_0(self, tmp_path):
        """With "pre_push": "off" and a FAIL proof on disk the hook exits 0 and
        prints exactly 1 line, and that line contains "off" so a developer can
        tell a disabled hook from a hook that found nothing."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=2)
        _set_config_field(tmpdir, "pre_push", "off")
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "fail"),
            ("PROOF-2", "RULE-2", "pass"),
        ])
        _commit(tmpdir, "off with a failing proof")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, f"Expected exit 0 when off, got {exit_code}\n{output}"
        lines = [ln for ln in output.splitlines() if ln.strip()]
        assert len(lines) == 1, f"Expected exactly 1 line, got {lines}"
        assert '"off"' in lines[0], f"The line must name the mode: {lines[0]!r}"


# ---------------------------------------------------------------------------
# RULE-12: an unknown mode fails closed
# ---------------------------------------------------------------------------

class TestRule12UnknownModeFailsClosed:

    @pytest.mark.proof("pre_push_hook", "PROOF-20", "RULE-12", tier="integration")
    def test_unknown_mode_blocks_and_names_the_valid_modes(self, tmp_path):
        """With "pre_push": "blocky" and every proof passing the hook exits 1
        rather than assuming warn, and the message names 'blocky' along with
        warn, strict and off."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=1)
        _set_config_field(tmpdir, "pre_push", "blocky")
        _write_proof_file(tmpdir, "test_feature",
                          [("PROOF-1", "RULE-1", "pass")])
        _commit(tmpdir, "unknown mode")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, (
            f"An unknown mode must fail closed, got exit {exit_code}\n{output}")
        assert "blocky" in output, f"The message must name the value:\n{output}"
        for mode in ("warn", "strict", "off"):
            assert mode in output, f"The message must name {mode}:\n{output}"


# ---------------------------------------------------------------------------
# RULE-13: specs are discovered at any depth
# ---------------------------------------------------------------------------

class TestRule13NestedSpecs:

    @pytest.mark.proof("pre_push_hook", "PROOF-22", "RULE-13", tier="integration")
    def test_spec_four_levels_deep_is_discovered(self, tmp_path):
        """The project's only spec lives at specs/a/b/c/deep_feature.md and
        carries a FAIL proof. The hook must exit 1 with PUSH BLOCKED; a depth
        limited search finds no .md at all and exits 0 silently."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=2, feature="deep_feature",
                             spec_subdir="specs/a/b/c")
        _write_proof_file(tmpdir, "deep_feature", [
            ("PROOF-1", "RULE-1", "pass"),
            ("PROOF-2", "RULE-2", "fail"),
        ], spec_subdir="specs/a/b/c")
        _commit(tmpdir, "deep spec with a failing proof")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, (
            f"A spec 4 levels deep was not checked (exit {exit_code}):\n{output}")
        assert "PUSH BLOCKED" in output, f"{output}"
        assert "deep_feature" in output, f"{output}"


# ---------------------------------------------------------------------------
# RULE-14: no plugin means warn reports and strict refuses
# ---------------------------------------------------------------------------

class TestRule14PluginResolution:

    def _project_without_plugin(self, tmpdir: str) -> str:
        _create_test_project(tmpdir, num_rules=2, with_gate=False)
        _write_proof_file(tmpdir, "test_feature", [
            ("PROOF-1", "RULE-1", "fail"),
            ("PROOF-2", "RULE-2", "pass"),
        ])
        _commit(tmpdir, "failing proof, no plugin")
        git_hooks_dir = os.path.join(tmpdir, ".git", "hooks")
        os.makedirs(git_hooks_dir, exist_ok=True)
        installed = os.path.join(git_hooks_dir, "pre-push")
        shutil.copy2(HOOK_SCRIPT, installed)
        return installed

    @pytest.mark.proof("pre_push_hook", "PROOF-23", "RULE-14", tier="integration")
    def test_missing_plugin_warns_in_warn_and_refuses_in_strict(self, tmp_path):
        """With PURLIN_PLUGIN_ROOT and CLAUDE_PLUGIN_ROOT unset and no
        pre_push_gate.py under any candidate, warn mode exits 0 printing
        WARNING and every path it searched, while strict mode exits 1 printing
        the same paths. A FAIL proof is on disk in both runs, so warn's exit 0
        is the unchecked push it says it is."""
        tmpdir = str(tmp_path)
        installed = self._project_without_plugin(tmpdir)

        exit_warn, out_warn = _run_hook(tmpdir, script=installed)
        assert exit_warn == 0, (
            f"warn must fail open, got exit {exit_warn}\n{out_warn}")
        assert "WARNING" in out_warn, f"{out_warn}"
        assert "pre_push_gate.py" in out_warn, f"{out_warn}"
        assert tmpdir in out_warn, (
            f"The searched paths must be named:\n{out_warn}")

        _set_config_field(tmpdir, "pre_push", "strict")
        exit_strict, out_strict = _run_hook(tmpdir, script=installed)
        assert exit_strict == 1, (
            f"strict must fail closed, got exit {exit_strict}\n{out_strict}")
        assert tmpdir in out_strict, (
            f"The searched paths must be named:\n{out_strict}")


# ---------------------------------------------------------------------------
# RULE-16: features are matched by whole name
# ---------------------------------------------------------------------------

class TestRule16WholeNameMatching:

    @pytest.mark.proof("pre_push_hook", "PROOF-26", "RULE-16", tier="integration")
    def test_feature_whose_name_contains_another_still_listed(self, tmp_path):
        """Two failing features named auth_system and system: the recovery
        steps must list both /purlin:test auth_system and /purlin:test system.
        Matching by substring drops the second, because its whole name occurs
        inside the first."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=1, feature="auth_system")
        with open(os.path.join(tmpdir, "specs", "hooks", "system.md"),
                  "w") as fh:
            fh.write(_spec_text("system", 1))
        _write_proof_file(tmpdir, "auth_system",
                          [("PROOF-1", "RULE-1", "fail")])
        _write_proof_file(tmpdir, "system",
                          [("PROOF-1", "RULE-1", "fail")])
        _commit(tmpdir, "two failing features, one name inside the other")

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, f"{exit_code}\n{output}"
        assert "/purlin:test auth_system" in output, f"{output}"
        assert "/purlin:test system\n" in output, (
            f"'system' was dropped by a substring match:\n{output}")
