"""Tests for pre_commit_hook, RULE-1 through RULE-6.

Each test builds an isolated temp git project, points the hook at this
checkout with PURLIN_PLUGIN_ROOT or CLAUDE_PLUGIN_ROOT, and runs
scripts/hooks/pre-commit.sh through bash. Tests are tagged @integration
because they spawn subprocesses and write to temp directories.

Proof markers use tier="integration" to match the @integration tier declared
in the spec's Proof section.
"""

import datetime
import json
import os
import shutil
import subprocess

import pytest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HOOK_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "hooks", "pre-commit.sh")

SPEC_TEXT = """# Feature: sample_feature

> Description: A single feature so the digest generator has something to scan.

## Rules

- RULE-1: Returns 1 when called with no arguments

## Proof

- PROOF-1 (RULE-1): Call the sample entry point with no arguments and verify it returns 1
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git(cwd, *args):
    subprocess.run(["git"] + list(args), cwd=cwd, check=True,
                   capture_output=True)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def _make_project(tmpdir, digest="auto"):
    """A temp Purlin project: config, one spec, one commit, no plugin inside.

    The project deliberately carries no scripts/mcp/purlin_server.py, so the
    last plugin-root candidate misses and the test controls which candidate
    the hook actually finds.
    """
    _write(os.path.join(tmpdir, ".purlin", "config.json"),
           json.dumps({"version": "0.9.0", "spec_dir": "specs",
                       "test_framework": "pytest", "digest": digest},
                      indent=2))
    _write(os.path.join(tmpdir, "specs", "hooks", "sample_feature.md"),
           SPEC_TEXT)
    _git(tmpdir, "init", "-q")
    _git(tmpdir, "config", "user.email", "test@example.com")
    _git(tmpdir, "config", "user.name", "Purlin Test")
    _git(tmpdir, "config", "commit.gpgsign", "false")
    _git(tmpdir, "add", "-A")
    _git(tmpdir, "commit", "-q", "-m", "init")


def _set_digest(tmpdir, value):
    cfg_path = os.path.join(tmpdir, ".purlin", "config.json")
    with open(cfg_path) as fh:
        cfg = json.load(fh)
    cfg["digest"] = value
    _write(cfg_path, json.dumps(cfg, indent=2))


def _env(**overrides):
    """os.environ without the plugin hints, plus whatever the test wants."""
    env = dict(os.environ)
    for key in ("PURLIN_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT",
                "PURLIN_SKIP_DIGEST"):
        env.pop(key, None)
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def _run_hook(tmpdir, script=HOOK_SCRIPT, env=None):
    """Run the hook inside tmpdir, return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        ["bash", script], cwd=tmpdir, capture_output=True, text=True,
        env=env if env is not None else _env(),
    )
    return result.returncode, result.stdout, result.stderr


def _staged(tmpdir):
    result = subprocess.run(["git", "diff", "--cached", "--name-only"],
                            cwd=tmpdir, capture_output=True, text=True,
                            check=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def _nonempty_lines(text):
    return [line for line in text.splitlines() if line.strip()]


def _copy_hook_outside_plugin(tmpdir):
    """The hook at <tmp>/copy/scripts/hooks, whose own-dir candidate misses.

    An installed hook resolves its plugin root from where the script lives.
    Copying it under a directory tree that carries no scripts/mcp makes that
    first candidate miss, which is the only way a test can reach the later
    candidates at all.
    """
    dest_dir = os.path.join(tmpdir, "copy", "scripts", "hooks")
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, "pre-commit.sh")
    shutil.copy2(HOOK_SCRIPT, dest)
    return dest, os.path.join(tmpdir, "copy")


def _break_digest_generation(tmpdir):
    """Replace the project's only spec with a directory of the same name.

    purlin_server._scan_specs globs specs/**/*.md and opens every hit with no
    guard, so a directory named sample_feature.md makes generate_digest raise
    IsADirectoryError. That is a real failure inside the generator, not a
    failure the test staged at the hook's boundary.
    """
    spec_path = os.path.join(tmpdir, "specs", "hooks", "sample_feature.md")
    os.remove(spec_path)
    os.makedirs(spec_path)


def _write_digest(tmpdir, age_seconds):
    """Write .purlin/report-data.js with a timestamp age_seconds in the past."""
    stamp = (datetime.datetime.now(datetime.timezone.utc)
             - datetime.timedelta(seconds=age_seconds)).isoformat()
    path = os.path.join(tmpdir, ".purlin", "report-data.js")
    with open(path, "w") as fh:
        fh.write("const PURLIN_DATA = "
                 + json.dumps({"timestamp": stamp, "features": []})
                 + ";\n")
    return path


# ---------------------------------------------------------------------------
# RULE-1: the hook never blocks, and the two opt-out paths each say one thing
# ---------------------------------------------------------------------------

class TestRule1NeverBlocks:

    @pytest.mark.proof("pre_commit_hook", "PROOF-1", "RULE-1",
                       tier="integration")
    def test_skip_digest_env_prints_one_line_and_does_nothing(self, tmp_path):
        """PURLIN_SKIP_DIGEST=1 skips everything, says so in exactly one line,
        writes no digest and stages nothing."""
        tmpdir = str(tmp_path)
        _make_project(tmpdir, digest="auto")

        code, out, err = _run_hook(tmpdir, env=_env(
            PURLIN_SKIP_DIGEST="1", PURLIN_PLUGIN_ROOT=PROJECT_ROOT))

        assert code == 0, f"Expected exit 0, got {code}\n{out}\n{err}"
        lines = _nonempty_lines(out + err)
        assert len(lines) == 1, (
            f"Expected exactly 1 line of output, got {len(lines)}: {lines}")
        assert "PURLIN_SKIP_DIGEST" in lines[0], (
            "the PURLIN_SKIP_DIGEST opt-out path went silent about why it "
            f"skipped; the line was: {lines[0]!r}")
        assert not os.path.exists(
            os.path.join(tmpdir, ".purlin", "report-data.js")), (
            "PURLIN_SKIP_DIGEST=1 still generated .purlin/report-data.js")
        assert _staged(tmpdir) == [], (
            f"PURLIN_SKIP_DIGEST=1 staged files: {_staged(tmpdir)}")

    @pytest.mark.proof("pre_commit_hook", "PROOF-2", "RULE-1",
                       tier="integration")
    def test_off_mode_prints_one_line_and_does_nothing(self, tmp_path):
        """digest=off prints exactly one line naming the mode, writes no
        digest and stages nothing."""
        tmpdir = str(tmp_path)
        _make_project(tmpdir, digest="off")

        code, out, err = _run_hook(
            tmpdir, env=_env(PURLIN_PLUGIN_ROOT=PROJECT_ROOT))

        assert code == 0, f"Expected exit 0, got {code}\n{out}\n{err}"
        lines = _nonempty_lines(out + err)
        assert len(lines) == 1, (
            f"Expected exactly 1 line of output, got {len(lines)}: {lines}")
        assert '"off"' in lines[0], (
            "the digest=off path went silent about the mode it honoured; "
            f"the line was: {lines[0]!r}")
        assert not os.path.exists(
            os.path.join(tmpdir, ".purlin", "report-data.js")), (
            "digest=off still generated .purlin/report-data.js")
        assert _staged(tmpdir) == [], (
            f"digest=off staged files: {_staged(tmpdir)}")


# ---------------------------------------------------------------------------
# RULE-2: plugin-root resolution order, and the fail-open line when it misses
# ---------------------------------------------------------------------------

class TestRule2PluginRoot:

    @pytest.mark.proof("pre_commit_hook", "PROOF-3", "RULE-2",
                       tier="integration")
    def test_empty_candidate_does_not_end_the_search(self, tmp_path):
        """A candidate that carries no server is stepped over: with the
        own-directory candidate and PURLIN_PLUGIN_ROOT both empty, the hook
        still finds the server through CLAUDE_PLUGIN_ROOT and stages the
        digest."""
        tmpdir = str(tmp_path)
        _make_project(tmpdir, digest="auto")
        script, _copy_root = _copy_hook_outside_plugin(tmpdir)
        empty = os.path.join(tmpdir, "empty")
        os.makedirs(empty, exist_ok=True)

        code, out, err = _run_hook(tmpdir, script=script, env=_env(
            PURLIN_PLUGIN_ROOT=empty, CLAUDE_PLUGIN_ROOT=PROJECT_ROOT))

        assert code == 0, f"Expected exit 0, got {code}\n{out}\n{err}"
        assert ".purlin/report-data.js" in _staged(tmpdir), (
            "an empty PURLIN_PLUGIN_ROOT ended the plugin-root search instead "
            "of being stepped over, so CLAUDE_PLUGIN_ROOT was never tried.\n"
            f"staged: {_staged(tmpdir)}\n{out}\n{err}")

    @pytest.mark.proof("pre_commit_hook", "PROOF-4", "RULE-2",
                       tier="integration")
    def test_no_candidate_carries_the_server_names_every_path(self, tmp_path):
        """When no candidate carries purlin_server.py the hook warns, names
        every path it searched, stages nothing and exits 0."""
        tmpdir = str(tmp_path)
        _make_project(tmpdir, digest="auto")
        script, copy_root = _copy_hook_outside_plugin(tmpdir)
        empty = os.path.join(tmpdir, "empty")
        os.makedirs(empty, exist_ok=True)

        code, out, err = _run_hook(tmpdir, script=script, env=_env(
            PURLIN_PLUGIN_ROOT=empty, CLAUDE_PLUGIN_ROOT=None))
        output = out + err

        assert code == 0, f"Expected exit 0, got {code}\n{output}"
        assert "WARNING" in output, (
            "the plugin-not-found fail-open path was silent: no candidate "
            "carried scripts/mcp/purlin_server.py and the hook printed no "
            f"WARNING, so the skipped digest is invisible.\n{output!r}")
        assert "the Purlin plugin was not found" in output, (
            "the plugin-not-found fail-open path was silent: the hook skipped "
            "the digest without saying the plugin was missing.\n"
            f"{output!r}")
        assert "scripts/mcp/purlin_server.py" in output, (
            "the plugin-not-found line does not say what it searched for.\n"
            f"{output!r}")
        for path in (copy_root, empty, os.path.realpath(tmpdir)):
            assert path in output, (
                f"the plugin-not-found line does not name {path}, so the "
                f"developer cannot see where to install the plugin.\n{output!r}")
        assert _staged(tmpdir) == [], (
            f"a missing plugin still staged files: {_staged(tmpdir)}")


# ---------------------------------------------------------------------------
# RULE-3: not a Purlin project is silent, an unusable config falls back to auto
# ---------------------------------------------------------------------------

class TestRule3ConfigFailOpen:

    @pytest.mark.proof("pre_commit_hook", "PROOF-5", "RULE-3",
                       tier="integration")
    def test_no_purlin_dir_silent_then_unusable_config_assumes_auto(
            self, tmp_path):
        """Three phases in one project: no .purlin/ is a silent exit 0; a
        non-string digest value prints one fallback line naming the config and
        then runs auto; a truncated config.json prints the same line."""
        tmpdir = str(tmp_path)
        _git(tmpdir, "init", "-q")
        _git(tmpdir, "config", "user.email", "test@example.com")
        _git(tmpdir, "config", "user.name", "Purlin Test")
        _git(tmpdir, "config", "commit.gpgsign", "false")

        # Phase 1: no .purlin/ at all.
        code, out, err = _run_hook(
            tmpdir, env=_env(PURLIN_PLUGIN_ROOT=PROJECT_ROOT))
        assert code == 0, f"Phase 1 expected exit 0, got {code}\n{out}\n{err}"
        assert out + err == "", (
            f"Phase 1 expected zero bytes of output, got {(out + err)!r}")

        # Phase 2: a digest value that is not a mode name.
        shutil.rmtree(os.path.join(tmpdir, ".git"))
        _make_project(tmpdir, digest="auto")
        _set_digest(tmpdir, 7)
        cfg_path = os.path.join(tmpdir, ".purlin", "config.json")

        code, out, err = _run_hook(
            tmpdir, env=_env(PURLIN_PLUGIN_ROOT=PROJECT_ROOT))
        output = out + err
        assert code == 0, f"Phase 2 expected exit 0, got {code}\n{output}"
        assert cfg_path in output, (
            "the unusable-config fail-open path did not name the file it "
            f"could not read.\n{output!r}")
        assert 'assuming "auto"' in output, (
            "the unusable-config fail-open path did not say it was assuming "
            f"auto.\n{output!r}")
        assert ".purlin/report-data.js" in _staged(tmpdir), (
            "the hook said it was assuming auto but did not run auto: the "
            f"digest was never staged.\nstaged: {_staged(tmpdir)}\n{output}")

        # Phase 3: config.json truncated mid-object.
        with open(cfg_path, "w") as fh:
            fh.write('{"digest":')
        code, out, err = _run_hook(
            tmpdir, env=_env(PURLIN_PLUGIN_ROOT=PROJECT_ROOT))
        output = out + err
        assert code == 0, f"Phase 3 expected exit 0, got {code}\n{output}"
        assert cfg_path in output and 'assuming "auto"' in output, (
            "an unparseable config.json did not produce the fallback line "
            f"naming the file.\n{output!r}")


# ---------------------------------------------------------------------------
# RULE-4: auto regenerates and stages, and a raise inside the generator is
# reported rather than swallowed
# ---------------------------------------------------------------------------

class TestRule4AutoStages:

    @pytest.mark.proof("pre_commit_hook", "PROOF-6", "RULE-4",
                       tier="integration")
    def test_auto_stages_digest_then_survives_a_generator_raise(self,
                                                               tmp_path):
        """Auto mode stages exactly .purlin/report-data.js and says so; once
        generate_digest raises, the hook reports the failure, exits 0 and
        leaves the digest on disk byte-identical."""
        tmpdir = str(tmp_path)
        _make_project(tmpdir, digest="auto")
        digest_path = os.path.join(tmpdir, ".purlin", "report-data.js")

        code, out, err = _run_hook(
            tmpdir, env=_env(PURLIN_PLUGIN_ROOT=PROJECT_ROOT))
        output = out + err

        assert code == 0, f"Expected exit 0, got {code}\n{output}"
        assert "digest updated and staged: .purlin/report-data.js" in output, (
            f"auto mode did not report the staged digest.\n{output!r}")
        assert _staged(tmpdir) == [".purlin/report-data.js"], (
            "auto mode must stage exactly the digest and nothing else, "
            f"staged: {_staged(tmpdir)}")
        with open(digest_path, "rb") as fh:
            before = fh.read()
        assert before.startswith(b"const PURLIN_DATA = "), (
            f"digest does not start with the expected prefix: {before[:40]!r}")

        # Now make generate_digest raise.
        _break_digest_generation(tmpdir)
        code, out, err = _run_hook(
            tmpdir, env=_env(PURLIN_PLUGIN_ROOT=PROJECT_ROOT))
        output = out + err

        assert code == 0, (
            f"a raise inside generate_digest must not block the commit, "
            f"got exit {code}\n{output}")
        assert "digest generation failed" in output, (
            "the generation-failed fail-open path was silent about the "
            f"failure.\n{output!r}")
        with open(digest_path, "rb") as fh:
            after = fh.read()
        assert after == before, (
            "a failed generation rewrote .purlin/report-data.js instead of "
            "leaving it as it was")


# ---------------------------------------------------------------------------
# RULE-5: warn reports, never regenerates
# ---------------------------------------------------------------------------

class TestRule5WarnMode:

    @pytest.mark.proof("pre_commit_hook", "PROOF-7", "RULE-5",
                       tier="integration")
    def test_warn_missing_then_stale_then_fresh(self, tmp_path):
        """warn warns when the digest is missing, warns naming 3600 seconds
        when it is 7200 seconds old, says nothing when it is fresh, and never
        writes or stages the file."""
        tmpdir = str(tmp_path)
        _make_project(tmpdir, digest="warn")
        env = _env(PURLIN_PLUGIN_ROOT=PROJECT_ROOT)

        # Phase 1: missing.
        code, out, err = _run_hook(tmpdir, env=env)
        output = out + err
        assert code == 0, f"Phase 1 expected exit 0, got {code}\n{output}"
        assert "WARNING" in output and "not found" in output, (
            f"warn mode did not report a missing digest.\n{output!r}")
        assert not os.path.exists(
            os.path.join(tmpdir, ".purlin", "report-data.js")), (
            "warn mode generated a digest, which is auto mode's job")

        # Phase 2: stale.
        digest_path = _write_digest(tmpdir, age_seconds=7200)
        with open(digest_path, "rb") as fh:
            stale_bytes = fh.read()
        code, out, err = _run_hook(tmpdir, env=env)
        output = out + err
        assert code == 0, f"Phase 2 expected exit 0, got {code}\n{output}"
        assert "WARNING" in output and "3600" in output, (
            f"warn mode did not report a 7200 second old digest.\n{output!r}")
        with open(digest_path, "rb") as fh:
            assert fh.read() == stale_bytes, (
                "warn mode rewrote the stale digest instead of only warning")

        # Phase 3: fresh.
        _write_digest(tmpdir, age_seconds=0)
        with open(digest_path, "rb") as fh:
            fresh_bytes = fh.read()
        code, out, err = _run_hook(tmpdir, env=env)
        output = out + err
        assert code == 0, f"Phase 3 expected exit 0, got {code}\n{output}"
        assert _nonempty_lines(output) == [], (
            f"warn mode spoke about a fresh digest: {output!r}")
        with open(digest_path, "rb") as fh:
            assert fh.read() == fresh_bytes, (
                "warn mode rewrote the fresh digest")
        assert _staged(tmpdir) == [], (
            f"warn mode staged files: {_staged(tmpdir)}")


# ---------------------------------------------------------------------------
# RULE-6: no stderr is thrown away
# ---------------------------------------------------------------------------

class TestRule6StderrReachesTheDeveloper:

    @pytest.mark.proof("pre_commit_hook", "PROOF-8", "RULE-6",
                       tier="integration")
    def test_generator_traceback_reaches_the_caller(self, tmp_path):
        """The traceback out of generate_digest arrives on the hook's stderr,
        and the hook file redirects stderr to /dev/null nowhere."""
        tmpdir = str(tmp_path)
        _make_project(tmpdir, digest="auto")
        _break_digest_generation(tmpdir)

        code, out, err = _run_hook(
            tmpdir, env=_env(PURLIN_PLUGIN_ROOT=PROJECT_ROOT))

        assert code == 0, f"Expected exit 0, got {code}\n{out}\n{err}"
        assert "IsADirectoryError" in err, (
            "the python error out of generate_digest never reached the "
            f"caller's stderr.\nstderr was: {err!r}")
        assert "sample_feature.md" in err, (
            "the error text reached the caller but does not name the file "
            f"that broke.\nstderr was: {err!r}")

        with open(HOOK_SCRIPT) as fh:
            hook_source = fh.read()
        assert hook_source.count("2>/dev/null") == 0, (
            "scripts/hooks/pre-commit.sh redirects stderr to /dev/null, so a "
            "diagnostic the developer needs is thrown away")
