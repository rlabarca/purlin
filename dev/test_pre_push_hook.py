"""Tests for pre_push_hook — RULE-2 through RULE-9.

Each test creates an isolated temp git project, manipulates proof files, then
runs scripts/hooks/pre-push.sh directly. Tests are tagged @integration because
they spawn subprocess and write to temp directories.

Proof markers use tier="integration" to match the @integration tier declared in
the spec's Proof section.
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOOK_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "hooks", "pre-push.sh")
SERVER_PY = os.path.join(PROJECT_ROOT, "scripts", "mcp", "purlin_server.py")
SERVER_DIR = os.path.join(PROJECT_ROOT, "scripts", "mcp")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_project(tmpdir: str, num_rules: int = 3) -> None:
    """Initialise a minimal Purlin project with a single feature spec."""
    os.makedirs(os.path.join(tmpdir, ".purlin"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "specs", "hooks"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "scripts", "mcp"), exist_ok=True)

    config = {
        "version": "0.9.0",
        "test_framework": "auto",
        "spec_dir": "specs",
        "pre_push": "warn",
    }
    _write_json(os.path.join(tmpdir, ".purlin", "config.json"), config)

    # Copy MCP server so sync_status works inside the temp project.
    for fname in ("purlin_server.py", "config_engine.py"):
        src = os.path.join(PROJECT_ROOT, "scripts", "mcp", fname)
        dst = os.path.join(tmpdir, "scripts", "mcp", fname)
        if os.path.exists(src):
            shutil.copy2(src, dst)
    init_py = os.path.join(PROJECT_ROOT, "scripts", "mcp", "__init__.py")
    if os.path.exists(init_py):
        shutil.copy2(init_py, os.path.join(tmpdir, "scripts", "mcp", "__init__.py"))

    # Write spec.
    spec_lines = [
        "# Feature: test_feature",
        "",
        "## What it does",
        "",
        "A test feature for pre-push hook testing.",
        "",
        "## Rules",
        "",
    ]
    for i in range(1, num_rules + 1):
        spec_lines.append(f"- RULE-{i}: Test rule {i} must hold")
    spec_lines += ["", "## Proof", ""]
    for i in range(1, num_rules + 1):
        spec_lines.append(f"- PROOF-{i} (RULE-{i}): Verify rule {i} holds")

    spec_path = os.path.join(tmpdir, "specs", "hooks", "test_feature.md")
    with open(spec_path, "w") as fh:
        fh.write("\n".join(spec_lines) + "\n")

    # Init git repo so git rev-parse works.
    subprocess.run(
        ["git", "init", "-q"],
        cwd=tmpdir, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "add", "-A"],
        cwd=tmpdir, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-q", "-m", "init", "--allow-empty"],
        cwd=tmpdir, check=True, capture_output=True,
    )


def _write_json(path: str, data: object) -> None:
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
    fh.close()


def _write_proof_file(
    tmpdir: str,
    feature: str,
    entries: list[tuple[str, str, str]],
) -> None:
    """Write a proofs-unit.json file.

    entries: list of (proof_id, rule_id, status) tuples, e.g.
        [("PROOF-1", "RULE-1", "pass"), ("PROOF-2", "RULE-2", "fail")]
    """
    proofs = []
    for proof_id, rule_id, status in entries:
        proofs.append(
            {
                "feature": feature,
                "id": proof_id,
                "rule": rule_id,
                "test_file": "dev/test_example.sh",
                "test_name": f"test {proof_id}",
                "status": status,
                "tier": "unit",
            }
        )

    # Locate spec dir for the feature.
    spec_dir = tmpdir + "/specs/hooks"
    out_path = os.path.join(spec_dir, f"{feature}.proofs-unit.json")
    _write_json(out_path, {"tier": "unit", "proofs": proofs})


def _run_hook(tmpdir: str) -> tuple[int, str]:
    """Run pre-push.sh inside tmpdir, return (exit_code, combined_output)."""
    result = subprocess.run(
        ["bash", HOOK_SCRIPT],
        cwd=tmpdir,
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    return result.returncode, output


def _set_config_field(tmpdir: str, key: str, value: str) -> None:
    cfg_path = os.path.join(tmpdir, ".purlin", "config.json")
    with open(cfg_path) as fh:
        cfg = json.load(fh)
    cfg[key] = value
    _write_json(cfg_path, cfg)


# ---------------------------------------------------------------------------
# RULE-2: partial coverage allows push with warning
# ---------------------------------------------------------------------------

class TestRule2PartialAllows:

    @pytest.mark.proof("pre_push_hook", "PROOF-2", "RULE-2", tier="integration")
    def test_partial_coverage_exits_0_with_warning(self, tmp_path):
        """Proof file covers 2 of 3 rules (no FAIL) — hook must exit 0 with
        a 'partial coverage' warning in stdout."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        # Only 2 of 3 rules have proofs — RULE-3 is uncovered.
        _write_proof_file(
            tmpdir,
            "test_feature",
            [("PROOF-1", "RULE-1", "pass"), ("PROOF-2", "RULE-2", "pass")],
        )

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, (
            f"Expected exit 0 (partial coverage allowed in warn mode), got {exit_code}\n{output}"
        )
        assert "partial coverage" in output.lower(), (
            f"Expected 'partial coverage' in output, got:\n{output}"
        )
        assert "PUSH BLOCKED" not in output, (
            f"Unexpected PUSH BLOCKED in output:\n{output}"
        )


# ---------------------------------------------------------------------------
# RULE-3: no specs → silent exit 0
# ---------------------------------------------------------------------------

class TestRule3NoSpecsSilent:

    @pytest.mark.proof("pre_push_hook", "PROOF-3", "RULE-3", tier="integration")
    def test_no_specs_dir_exits_0_silently(self, tmp_path):
        """When no specs/ directory exists the hook must exit 0 with empty
        stdout — it has nothing to check."""
        tmpdir = str(tmp_path)
        os.makedirs(os.path.join(tmpdir, ".purlin"))
        _write_json(
            os.path.join(tmpdir, ".purlin", "config.json"),
            {"version": "0.9.0", "test_framework": "auto"},
        )
        subprocess.run(["git", "init", "-q"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "init", "--allow-empty"],
            cwd=tmpdir, check=True, capture_output=True,
        )

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, (
            f"Expected exit 0 (no specs), got {exit_code}\n{output}"
        )
        assert output.strip() == "", (
            f"Expected empty output when no specs exist, got:\n{output!r}"
        )


# ---------------------------------------------------------------------------
# RULE-4: all PASSING → exit 0
# ---------------------------------------------------------------------------

class TestRule4AllPassingAllows:

    @pytest.mark.proof("pre_push_hook", "PROOF-4", "RULE-4", tier="integration")
    def test_all_pass_exits_0(self, tmp_path):
        """All rules proved with pass status → hook exits 0 without blocking
        or partial-coverage warnings."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        _write_proof_file(
            tmpdir,
            "test_feature",
            [
                ("PROOF-1", "RULE-1", "pass"),
                ("PROOF-2", "RULE-2", "pass"),
                ("PROOF-3", "RULE-3", "pass"),
            ],
        )

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, (
            f"Expected exit 0 (all passing), got {exit_code}\n{output}"
        )
        assert "PUSH BLOCKED" not in output, (
            f"Unexpected PUSH BLOCKED in output:\n{output}"
        )

    @pytest.mark.proof("pre_push_hook", "PROOF-12", "RULE-4", tier="integration")
    def test_fail_keyword_in_rule_description_does_not_block(self, tmp_path):
        """A rule description that contains the word FAIL must not cause a
        false-positive block when all proofs actually pass.  This guards
        against naive string-matching on rule text rather than status fields."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=0)

        # Overwrite spec with a rule whose description contains 'FAIL'.
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
            "- PROOF-1 (RULE-1): Verify FAIL badge renders correctly",
            "- PROOF-2 (RULE-2): Verify PASSING badge renders correctly",
            "",
        ])
        spec_path = os.path.join(tmpdir, "specs", "hooks", "test_feature.md")
        with open(spec_path, "w") as fh:
            fh.write(spec_content)

        _write_proof_file(
            tmpdir,
            "test_feature",
            [("PROOF-1", "RULE-1", "pass"), ("PROOF-2", "RULE-2", "pass")],
        )
        subprocess.run(["git", "add", "-A"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "spec-with-FAIL-in-desc"],
            cwd=tmpdir, check=True, capture_output=True,
        )

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 0, (
            f"Rule description containing 'FAIL' caused false-positive block "
            f"(exit {exit_code}):\n{output}"
        )
        assert "PUSH BLOCKED" not in output, (
            f"False-positive PUSH BLOCKED:\n{output}"
        )


# ---------------------------------------------------------------------------
# RULE-5: framework detection from config + auto-detection
# ---------------------------------------------------------------------------

class TestRule5FrameworkDetection:

    @pytest.mark.proof("pre_push_hook", "PROOF-5", "RULE-5", tier="integration")
    def test_detects_framework_from_config_and_auto(self, tmp_path):
        """Hook reads test_framework from .purlin/config.json and selects the
        right runner.  Also verifies auto-detection when config is absent and
        conftest.py is present (→ pytest)."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=1)
        _write_proof_file(tmpdir, "test_feature", [("PROOF-1", "RULE-1", "pass")])

        # 1. Explicit pytest from config.
        _set_config_field(tmpdir, "test_framework", "pytest")
        _, out_pytest = _run_hook(tmpdir)
        assert "(pytest)" in out_pytest, (
            f"Expected '(pytest)' in output when test_framework=pytest, got:\n{out_pytest}"
        )

        # 2. Explicit jest from config.
        _set_config_field(tmpdir, "test_framework", "jest")
        _, out_jest = _run_hook(tmpdir)
        assert "(jest)" in out_jest, (
            f"Expected '(jest)' in output when test_framework=jest, got:\n{out_jest}"
        )

        # 3. Auto-detection via conftest.py (no config key).
        _set_config_field(tmpdir, "test_framework", "auto")
        conftest = os.path.join(tmpdir, "conftest.py")
        open(conftest, "w").close()
        _, out_auto = _run_hook(tmpdir)
        assert "(pytest)" in out_auto, (
            f"Expected '(pytest)' via auto-detect from conftest.py, got:\n{out_auto}"
        )


# ---------------------------------------------------------------------------
# RULE-6: only unit-tier tests run (pytest -m "not integration")
# ---------------------------------------------------------------------------

class TestRule6UnitTierOnly:

    @pytest.mark.proof("pre_push_hook", "PROOF-6", "RULE-6", tier="integration")
    def test_unit_test_runs_integration_skipped(self, tmp_path):
        """Hook invokes pytest with -m 'not integration'.  A plain test
        function must run (sentinel created); a function marked @integration
        must be skipped (no sentinel)."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=1)
        _write_proof_file(tmpdir, "test_feature", [("PROOF-1", "RULE-1", "pass")])

        # Remove config so auto-detection fires; add conftest.py to trigger pytest.
        os.remove(os.path.join(tmpdir, ".purlin", "config.json"))
        open(os.path.join(tmpdir, "conftest.py"), "w").close()

        sentinel_unit = os.path.join(tmpdir, ".sentinel_unit")
        sentinel_int = os.path.join(tmpdir, ".sentinel_integration")

        # Unit test — no markers — should run.
        unit_test = os.path.join(tmpdir, "test_unit_tier.py")
        with open(unit_test, "w") as fh:
            fh.write(
                f'def test_unit_runs():\n'
                f'    open("{sentinel_unit}", "w").close()\n'
            )

        # Integration test — marked @integration — must NOT run.
        int_test = os.path.join(tmpdir, "test_integration_tier.py")
        with open(int_test, "w") as fh:
            fh.write(
                f'import pytest\n\n'
                f'@pytest.mark.integration\n'
                f'def test_integration_skipped():\n'
                f'    open("{sentinel_int}", "w").close()\n'
            )

        # Remove sentinels before running.
        for p in (sentinel_unit, sentinel_int):
            if os.path.exists(p):
                os.remove(p)

        _run_hook(tmpdir)

        assert os.path.exists(sentinel_unit), (
            "Unit test did not run — hook should invoke pytest -m 'not integration'"
        )
        assert not os.path.exists(sentinel_int), (
            "Integration-marked test ran — hook should have excluded it with -m 'not integration'"
        )


# ---------------------------------------------------------------------------
# RULE-7: output format — passing / partial / blocked sections + recovery
# ---------------------------------------------------------------------------

class TestRule7OutputFormat:

    @pytest.mark.proof("pre_push_hook", "PROOF-7", "RULE-7", tier="integration")
    def test_output_shows_blocked_and_recovery_on_fail(self, tmp_path):
        """When a proof has FAIL status the output must contain PUSH BLOCKED,
        a failing-features section, and RECOVERY STEPS."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        # RULE-2 fails, RULE-3 has no proof (partial).
        _write_proof_file(
            tmpdir,
            "test_feature",
            [("PROOF-1", "RULE-1", "pass"), ("PROOF-2", "RULE-2", "fail")],
        )

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, (
            f"Expected exit 1 on FAIL proof, got {exit_code}\n{output}"
        )
        assert "PUSH BLOCKED" in output, (
            f"Expected 'PUSH BLOCKED' in output:\n{output}"
        )
        # Failing features detail — the feature name or "Failing" label.
        has_fail_section = (
            "Failing" in output or "FAILING" in output or "test_feature" in output
        )
        assert has_fail_section, (
            f"Expected failing-features detail in output:\n{output}"
        )
        assert "RECOVERY STEPS" in output, (
            f"Expected 'RECOVERY STEPS' in output:\n{output}"
        )

    @pytest.mark.proof("pre_push_hook", "PROOF-13", "RULE-7", tier="integration")
    def test_recovery_message_lists_feature_specific_commands(self, tmp_path):
        """Recovery message must include /purlin:unit-test <feature_name>,
        /purlin:status, and /purlin:build so the developer knows exactly
        which commands to run."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=2)
        _write_proof_file(
            tmpdir,
            "test_feature",
            [("PROOF-1", "RULE-1", "fail"), ("PROOF-2", "RULE-2", "pass")],
        )
        subprocess.run(["git", "add", "-A"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "failing-proof"],
            cwd=tmpdir, check=True, capture_output=True,
        )

        _, output = _run_hook(tmpdir)

        assert "/purlin:unit-test test_feature" in output, (
            f"Expected '/purlin:unit-test test_feature' in recovery output:\n{output}"
        )
        assert "/purlin:status" in output, (
            f"Expected '/purlin:status' in recovery output:\n{output}"
        )
        assert "/purlin:build" in output, (
            f"Expected '/purlin:build' in recovery output:\n{output}"
        )


# ---------------------------------------------------------------------------
# RULE-8: strict mode blocks non-VERIFIED features
# ---------------------------------------------------------------------------

class TestRule8StrictMode:

    @pytest.mark.proof("pre_push_hook", "PROOF-9", "RULE-8", tier="integration")
    def test_strict_mode_blocks_partial_coverage(self, tmp_path):
        """Strict mode: partial coverage (2 of 3 rules proved, no FAIL) must
        block the push with exit 1 and mention 'strict mode' in output."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        _set_config_field(tmpdir, "pre_push", "strict")
        # Prove only 2 of 3 rules → PARTIAL status.
        _write_proof_file(
            tmpdir,
            "test_feature",
            [("PROOF-1", "RULE-1", "pass"), ("PROOF-2", "RULE-2", "pass")],
        )

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, (
            f"Expected exit 1 in strict mode with partial coverage, got {exit_code}\n{output}"
        )
        assert "strict mode" in output.lower(), (
            f"Expected 'strict mode' in output:\n{output}"
        )

    @pytest.mark.proof("pre_push_hook", "PROOF-10", "RULE-8", tier="integration")
    def test_strict_mode_allows_passing_blocks_partial(self, tmp_path):
        """Strict mode enforcement boundary: PASSING (all rules proved, no
        FAIL) is allowed in strict mode; PARTIAL (incomplete coverage) is
        blocked.

        The hook routes PASSING → $PASSES only, and PARTIAL → $NON_READY,
        so strict mode blocks PARTIAL but not PASSING.  This test exercises
        both sides of that boundary to confirm the distinction is enforced.
        """
        tmpdir = str(tmp_path)

        # --- Side A: PASSING in strict mode → exit 0 ---
        _create_test_project(tmpdir, num_rules=2)
        _set_config_field(tmpdir, "pre_push", "strict")
        # All rules proved → PASSING status.
        _write_proof_file(
            tmpdir,
            "test_feature",
            [("PROOF-1", "RULE-1", "pass"), ("PROOF-2", "RULE-2", "pass")],
        )

        exit_code_passing, output_passing = _run_hook(tmpdir)

        assert exit_code_passing == 0, (
            f"Strict mode must allow PASSING features (all rules proved), "
            f"got exit {exit_code_passing}\n{output_passing}"
        )
        assert "PUSH BLOCKED" not in output_passing, (
            f"Strict mode must not block PASSING features:\n{output_passing}"
        )

        # --- Side B: PARTIAL in strict mode → exit 1 + strict mode message ---
        # Overwrite proof file so only 1 of 2 rules is covered → PARTIAL.
        _write_proof_file(
            tmpdir,
            "test_feature",
            [("PROOF-1", "RULE-1", "pass")],
        )

        exit_code_partial, output_partial = _run_hook(tmpdir)

        assert exit_code_partial == 1, (
            f"Strict mode must block PARTIAL coverage, got exit {exit_code_partial}\n{output_partial}"
        )
        assert "strict mode" in output_partial.lower(), (
            f"Expected 'strict mode' in output for blocked PARTIAL:\n{output_partial}"
        )

    @pytest.mark.proof("pre_push_hook", "PROOF-14", "RULE-8", tier="integration")
    def test_strict_mode_recovery_includes_verify_command(self, tmp_path):
        """When strict mode blocks a push the recovery steps must include
        /purlin:verify and /purlin:unit-test so the developer knows how to
        reach VERIFIED status."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)
        _set_config_field(tmpdir, "pre_push", "strict")
        # Partial proofs → not VERIFIED.
        _write_proof_file(
            tmpdir,
            "test_feature",
            [("PROOF-1", "RULE-1", "pass"), ("PROOF-2", "RULE-2", "pass")],
        )
        subprocess.run(["git", "add", "-A"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "partial-strict"],
            cwd=tmpdir, check=True, capture_output=True,
        )

        exit_code, output = _run_hook(tmpdir)

        assert exit_code == 1, (
            f"Expected exit 1 in strict mode, got {exit_code}\n{output}"
        )
        assert "RECOVERY STEPS" in output, (
            f"Expected 'RECOVERY STEPS' in strict mode output:\n{output}"
        )
        assert "/purlin:verify" in output, (
            f"Expected '/purlin:verify' in strict mode recovery output:\n{output}"
        )
        assert "/purlin:unit-test" in output, (
            f"Expected '/purlin:unit-test' in strict mode recovery output:\n{output}"
        )


# ---------------------------------------------------------------------------
# RULE-9: after purlin:init, .git/hooks/pre-push exists and is executable
# ---------------------------------------------------------------------------

class TestRule9HookInstalled:

    @pytest.mark.proof("pre_push_hook", "PROOF-11", "RULE-9", tier="integration")
    def test_installed_hook_exists_is_executable_and_blocks(self, tmp_path):
        """Simulates what purlin:init does: copies pre-push.sh to
        .git/hooks/pre-push and makes it executable.  Verifies the installed
        hook is present, executable, and actually intercepts a push with a
        FAIL proof (exit 1 + PUSH BLOCKED)."""
        tmpdir = str(tmp_path)
        _create_test_project(tmpdir, num_rules=3)

        git_hooks_dir = os.path.join(tmpdir, ".git", "hooks")
        os.makedirs(git_hooks_dir, exist_ok=True)
        installed_hook = os.path.join(git_hooks_dir, "pre-push")
        shutil.copy2(HOOK_SCRIPT, installed_hook)
        os.chmod(installed_hook, os.stat(installed_hook).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        # Verify file exists and is executable.
        assert os.path.isfile(installed_hook), (
            ".git/hooks/pre-push does not exist after install"
        )
        assert os.access(installed_hook, os.X_OK), (
            ".git/hooks/pre-push is not executable after install"
        )

        # Verify the installed hook intercepts a push with a failing proof.
        _write_proof_file(
            tmpdir,
            "test_feature",
            [
                ("PROOF-1", "RULE-1", "pass"),
                ("PROOF-2", "RULE-2", "fail"),
                ("PROOF-3", "RULE-3", "pass"),
            ],
        )
        subprocess.run(["git", "add", "-A"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "failing-proofs"],
            cwd=tmpdir, check=True, capture_output=True,
        )

        result = subprocess.run(
            ["bash", installed_hook],
            cwd=tmpdir,
            capture_output=True,
            text=True,
        )
        output = result.stdout + result.stderr

        assert result.returncode == 1, (
            f"Expected installed hook to exit 1 on FAIL proof, got {result.returncode}\n{output}"
        )
        assert "PUSH BLOCKED" in output, (
            f"Expected 'PUSH BLOCKED' from installed hook:\n{output}"
        )
