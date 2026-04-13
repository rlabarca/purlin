"""
E2E agent test: Build changeset summary + exit criteria via real claude -p sessions.

Runs actual agent sessions to verify:
  - purlin:build outputs a visible changeset summary with real decisions
  - purlin:build commits with the summary in the commit body
  - purlin:spec commits the spec file before completing

The build spec is deliberately ambiguous — it says "hash passwords" without
naming an algorithm and "rate limit" without a threshold — so the agent MUST
make real judgment calls and flag them in the Decisions and Review sections.

Run:  python3 -m pytest dev/test_e2e_build_agent.py -v -x
Cost: ~$1-3 in API calls (2 claude -p invocations)
Time: ~3-8 minutes
"""

import json
import os
import re
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts", "mcp"))


# ---------------------------------------------------------------------------
# Claude CLI helper (same pattern as test_e2e_figma_web.py)
# ---------------------------------------------------------------------------

def _claude(prompt, *, cwd, timeout=300):
    """Send one message via ``claude -p``.  Returns (result_text, session_id)."""
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--model", "sonnet",
        "--max-turns", "50",
        "--dangerously-skip-permissions",
        "--plugin-dir", PROJECT_ROOT,
        "--agents", os.path.join(PROJECT_ROOT, "agents", "purlin.md"),
    ]

    result = subprocess.run(
        cmd, input=prompt, capture_output=True, text=True,
        cwd=cwd, timeout=timeout,
    )
    stdout = result.stdout.strip()
    if not stdout:
        raise AssertionError(
            f"claude empty output (exit {result.returncode})\n"
            f"stderr: {result.stderr[:500]}")

    clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', stdout)
    data = json.loads(clean)

    text = data.get("result", "")
    sid = data.get("session_id", "")
    if data.get("is_error"):
        raise AssertionError(f"Claude error:\n{text[:800]}")
    return text, sid


# ---------------------------------------------------------------------------
# Project scaffolding helpers
# ---------------------------------------------------------------------------

def _init_git(path):
    """Initialize a git repo with initial commit."""
    subprocess.run(["git", "init", "-q"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "e2e@test"],
                   cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "E2E"],
                   cwd=path, capture_output=True)


def _make_project(root):
    """Create a minimal Purlin project."""
    purlin_dir = os.path.join(root, ".purlin", "cache")
    os.makedirs(purlin_dir, exist_ok=True)
    with open(os.path.join(root, ".purlin", "config.json"), "w") as f:
        json.dump({
            "version": "0.9.0",
            "test_framework": "pytest",
            "spec_dir": "specs",
        }, f)

    # Copy proof plugin
    src_plugin = os.path.join(PROJECT_ROOT, "scripts", "proof", "pytest_purlin.py")
    dst_plugin = os.path.join(root, "conftest.py")
    with open(src_plugin) as s, open(dst_plugin, "w") as d:
        d.write(s.read())

    _init_git(root)
    subprocess.run(["git", "add", "."], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "chore: init project"],
                   cwd=root, capture_output=True)


def _git_log(root, n=1, fmt="%B"):
    """Return git log output."""
    r = subprocess.run(
        ["git", "log", f"-{n}", f"--pretty={fmt}"],
        cwd=root, capture_output=True, text=True,
    )
    return r.stdout.strip()


def _git_status(root):
    """Return git status --porcelain output."""
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root, capture_output=True, text=True,
    )
    return r.stdout.strip()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="class")
def build_project(tmp_path_factory):
    """Run purlin:build in a temp project with an ambiguous spec.

    The spec deliberately omits specifics — no hashing algorithm, no rate
    limit threshold, no sanitization approach — so the agent MUST make
    real decisions and flag them.
    """
    root = str(tmp_path_factory.mktemp("build_agent"))
    _make_project(root)

    # Spec with ambiguity that forces real Decisions and Review
    spec_dir = os.path.join(root, "specs", "auth")
    os.makedirs(spec_dir)
    with open(os.path.join(spec_dir, "login.md"), "w") as f:
        f.write("""\
# Feature: login

> Scope: src/auth.py
> Stack: python

## What it does
User login endpoint that authenticates credentials and returns a session token.

## Rules
- RULE-1: authenticate(email, password) returns a session token string on valid credentials
- RULE-2: authenticate() raises AuthError with message "invalid credentials" on wrong password
- RULE-3: Passwords are hashed before comparison — never compared as plaintext
- RULE-4: Rate limits login attempts per email address after repeated failures
- RULE-5: Input is sanitized before processing — no injection via email or password fields

## Proof
- PROOF-1 (RULE-1): Call authenticate with valid creds; verify returns non-empty string token
- PROOF-2 (RULE-2): Call authenticate with wrong password; verify raises AuthError
- PROOF-3 (RULE-3): Inspect stored password; verify it is not plaintext
- PROOF-4 (RULE-4): Submit repeated failures; verify rate limit kicks in
- PROOF-5 (RULE-5): Submit email with special characters; verify no injection
""")

    subprocess.run(["git", "add", "specs/"], cwd=root, capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "spec(login): initial spec"],
                   cwd=root, capture_output=True)

    # Run purlin:build via claude -p
    prompt = f"""\
You are working in {root}. The conftest.py proof plugin is already installed.

Run purlin:build login

Write the implementation in src/auth.py and tests in tests/test_auth.py.
Follow ALL build steps including Step 5 (Changeset Summary) and Step 6 (Commit).

IMPORTANT:
- The changeset summary MUST be visible in your final response to me — print
  the full Changeset, Decisions, and Review sections so I can review them.
- The Decisions section must list the actual judgment calls you made (hashing
  algorithm choice, rate limit threshold, sanitization approach, etc.)
- The Review section must flag security-sensitive areas.
- Commit with the changeset summary as the commit message body.
"""
    text, sid = _claude(prompt, cwd=root, timeout=600)
    return {"root": root, "output": text, "session": sid}


@pytest.fixture(scope="class")
def spec_project(tmp_path_factory):
    """Run purlin:spec in a temp project and return the root path + agent output."""
    root = str(tmp_path_factory.mktemp("spec_agent"))
    _make_project(root)

    prompt = f"""\
You are working in {root}.
Run purlin:spec calculator

The feature is: a calculator module with add, subtract, multiply, divide.
Division by zero should raise ValueError.

IMPORTANT: This is an automated test. Do NOT use AskUserQuestion or wait
for approval. Auto-approve the draft and proceed immediately through ALL
steps. Write the spec file to specs/, then commit it with
git add specs/ && git commit -m "spec(calculator): initial spec".
The spec MUST be committed before you finish.
"""
    text, sid = _claude(prompt, cwd=root, timeout=300)
    return {"root": root, "output": text, "session": sid}


# ---------------------------------------------------------------------------
# Build tests
# ---------------------------------------------------------------------------

class TestBuildAgentSession:

    @pytest.mark.proof("skill_build", "PROOF-17", "RULE-9", tier="e2e")
    def test_changeset_summary_visible_with_real_decisions(self, build_project):
        """Agent output contains a visible changeset summary with substantive
        Decisions (not the empty placeholder) and Review items."""
        output = build_project["output"]
        root = build_project["root"]
        log = _git_log(root, n=5)
        combined = output + "\n" + log

        # All 3 sections must appear somewhere visible
        assert re.search(r"(?i)changeset", combined), \
            "Neither output nor git log contains 'Changeset'"
        assert re.search(r"(?i)decision", combined), \
            "Neither output nor git log contains 'Decisions'"
        assert re.search(r"(?i)review", combined), \
            "Neither output nor git log contains 'Review'"

        # RULE references must be present
        assert re.search(r"RULE-[1-5]", combined), \
            "No RULE references in changeset"

        # Decisions must NOT be the empty placeholder — the spec is ambiguous
        # enough that real judgment calls are required
        empty_decisions = re.search(
            r"(?i)no judgment calls|all rules had unambiguous", combined)
        assert not empty_decisions, (
            "Decisions section used empty placeholder despite ambiguous spec. "
            "Agent should have reported choices for hashing algorithm, "
            "rate limit threshold, and sanitization approach."
        )

        # Review must NOT be the empty placeholder — security-sensitive code
        empty_review = re.search(
            r"(?i)no notable risk|straightforward implementation", combined)
        assert not empty_review, (
            "Review section used empty placeholder despite security-sensitive "
            "code (hashing, rate limiting, input sanitization)."
        )

    @pytest.mark.proof("skill_build", "PROOF-18", "RULE-10", tier="e2e")
    def test_build_commit_has_changeset_body(self, build_project):
        """Git commit message body contains the changeset summary."""
        root = build_project["root"]
        log = _git_log(root, n=5)
        assert re.search(r"feat\(login\):", log), \
            f"No feat(login): commit found in:\n{log}"
        assert re.search(r"RULE-[1-5]", log), \
            f"Build commit body missing RULE references:\n{log}"

    @pytest.mark.proof("skill_build", "PROOF-19", "RULE-12", tier="e2e")
    def test_build_exit_criteria_met(self, build_project):
        """After build, git status is clean and proof files are committed."""
        root = build_project["root"]
        status = _git_status(root)

        # No uncommitted proof files
        proof_lines = [l for l in status.splitlines()
                       if ".proofs-" in l and l.strip()]
        assert not proof_lines, \
            f"Uncommitted proof files after build:\n{''.join(proof_lines)}"

        # Proof files exist and are tracked
        r = subprocess.run(
            ["git", "ls-files", "--", "specs/"],
            cwd=root, capture_output=True, text=True,
        )
        proof_files = [f for f in r.stdout.splitlines() if ".proofs-" in f]
        assert proof_files, "No proof files tracked in git after build"

        # Source files committed
        src_lines = [l for l in status.splitlines()
                     if re.search(r"\.(py|js|ts)$", l) and "conftest" not in l]
        assert not src_lines, \
            f"Uncommitted source files after build:\n{''.join(src_lines)}"


# ---------------------------------------------------------------------------
# Spec tests
# ---------------------------------------------------------------------------

class TestSpecAgentSession:

    @pytest.mark.proof("skill_spec", "PROOF-8", "RULE-7", tier="e2e")
    def test_spec_committed(self, spec_project):
        """After spec creation, the spec file is committed."""
        root = spec_project["root"]
        status = _git_status(root)

        # No uncommitted spec files
        spec_lines = [l for l in status.splitlines()
                      if "specs/" in l and l.endswith(".md")]
        assert not spec_lines, \
            f"Uncommitted spec files after spec creation:\n{''.join(spec_lines)}"

        # Spec file exists in git
        r = subprocess.run(
            ["git", "ls-files", "--", "specs/"],
            cwd=root, capture_output=True, text=True,
        )
        spec_files = [f for f in r.stdout.splitlines() if f.endswith(".md")]
        assert spec_files, "No spec .md files tracked in git"

        # Git log shows a spec commit
        log = _git_log(root, n=5)
        assert re.search(r"spec\(calculator\):", log), \
            f"No spec(calculator): commit found in:\n{log}"
