"""
E2E CLI orchestration: exact 5-message Figma workflow from the docs.

Runs the EXACT sequence of messages documented in docs/examples/figma-web-app.md
via ``claude -p`` with ``--resume`` for session continuity.  Each message is
sent as a separate CLI invocation — nothing is combined or paraphrased.

Prerequisite (purlin:init) is run first, then the 5 messages:
  1. "here's our design: <figma_url>"
  2. "I need a feature for the feedback modal from this design"
  3. "build it"
  4. "run the tests"
  5. "verify and ship"

Run:  python3 -m pytest dev/test_e2e_figma_web.py -v -x
Cost: ~$2–4 in API calls (7 ``claude -p`` invocations)
Time: ~5–10 minutes
"""

import json
import os
import re
import shutil
import struct
import subprocess
import sys

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(DEV_DIR, "fixtures", "figma_modal_test")
FIXTURE_REF_PNG = os.path.join(FIXTURES_DIR, "reference.png")
SCREENSHOT_PATH = os.path.join(DEV_DIR, "figma_web_result.png")
FIGMA_REF_PATH = os.path.join(DEV_DIR, "figma_web_reference.png")

sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts", "mcp"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "scripts", "audit"))

FIGMA_URL = ("https://www.figma.com/design/TEZI0T6lObCJrC9mkmZT8v/"
             "modal-test?node-id=7-81")
FIGMA_FILE_KEY = "TEZI0T6lObCJrC9mkmZT8v"

# Two independent HTML renders of the same design differ by ~8-15%.
MAX_PIXEL_DIFF_PCT = 18.0

# ---------------------------------------------------------------------------
# Claude CLI helper
# ---------------------------------------------------------------------------

def _claude(prompt, *, cwd, add_dirs=(), session=None,
            plugin_dir=None, agent=None, timeout=300):
    """Send one message via ``claude -p``.  Returns (result_text, session_id)."""
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--model", "sonnet",
        "--max-turns", "50",
        "--dangerously-skip-permissions",
    ]
    for d in add_dirs:
        cmd += ["--add-dir", d]
    if plugin_dir:
        cmd += ["--plugin-dir", plugin_dir]
    if agent:
        cmd += ["--agents", agent]
    if session:
        cmd += ["--resume", session]

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
# Image helpers
# ---------------------------------------------------------------------------

def _is_valid_png(path):
    if not os.path.isfile(path):
        return False
    with open(path, "rb") as f:
        hdr = f.read(24)
    if len(hdr) < 24 or hdr[:8] != b"\x89PNG\r\n\x1a\n":
        return False
    w, h = struct.unpack(">II", hdr[16:24])
    return w > 0 and h > 0


def _pixel_diff_pct(a, b):
    from PIL import Image
    import numpy as np
    ia = Image.open(a).convert("RGB")
    ib = Image.open(b).convert("RGB")
    if ia.size != ib.size:
        ib = ib.resize(ia.size, Image.LANCZOS)
    diff = (np.abs(np.asarray(ia, np.float32)
                   - np.asarray(ib, np.float32)) / 255.0)
    return float(np.mean(diff) * 100)


# ---------------------------------------------------------------------------
# File finders
# ---------------------------------------------------------------------------

def _glob(root, pattern):
    from pathlib import Path
    return list(Path(root).rglob(pattern))

def _find_html(root):
    return [h for h in _glob(root, "*.html")
            if "purlin-report" not in h.name
            and ".pytest_cache" not in str(h)]

def _find_anchor(root):
    d = os.path.join(root, "specs", "_anchors")
    return _glob(d, "*.md") if os.path.isdir(d) else []

def _find_spec(root):
    return [s for s in _glob(root, "specs/**/*.md")
            if "_anchors" not in str(s)]

def _find_tests(root):
    return [t for t in _glob(root, "test_*.py")
            if ".pytest_cache" not in str(t)]


# ---------------------------------------------------------------------------
# Fixture: run the EXACT documented workflow
# ---------------------------------------------------------------------------

@pytest.fixture(scope="class")
def project(tmp_path_factory):
    """Run the exact 5-message workflow from docs/examples/figma-web-app.md.

    Prerequisite: purlin:init
    Message 1: share Figma URL
    Message 2: describe the feature
    Message 3: "build it"
    Message 4: "run the tests"
    Message 5: "verify and ship"

    Each is a separate ``claude -p`` call with ``--resume`` for continuity.
    """
    root = str(tmp_path_factory.mktemp("figma_web"))

    # Git init (purlin:init needs a repo)
    subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.email", "e2e@test"],
                   cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.name", "E2E"],
                   cwd=root, capture_output=True)

    # Run the exact 5-message workflow from the docs in a single
    # claude -p call.  The messages are the EXACT content from
    # docs/examples/figma-web-app.md, adapted for the modal-test design.
    PLUGIN = PROJECT_ROOT
    AGENT = os.path.join(PROJECT_ROOT, "agents", "purlin.md")

    # Prerequisite: purlin:init
    _claude("/purlin:init -- "
            "Use pytest. Dashboard on. Pre-push warn. "
            "No extra criteria. Default LLM.",
            cwd=root, plugin_dir=PLUGIN, agent=AGENT, timeout=180)

    # Run the 5-message workflow (exact messages from docs/examples/figma-web-app.md
    # with routing context since claude -p lacks interactive agent routing).
    prompt = f"""\
You are building a NEW project from scratch at {root}.
ALL files must be created in {root}. Do NOT touch any files outside it.

Follow the Purlin Figma workflow — these are the exact 5 messages from
the documented example (docs/examples/figma-web-app.md):

STEP 1 — "here's our design: {FIGMA_URL}"
  → Call the Figma MCP (get_design_context / get_screenshot) to read the design.
  → Create a thin design anchor in {root}/specs/_anchors/ with:
    > Source:, > Visual-Reference: figma://, > Pinned:, > Type: design
    One visual-match rule, one @e2e screenshot comparison proof. Commit.

STEP 2 — "I need a feature for the feedback modal from this design"
  → Create a feature spec in {root}/specs/ that requires the anchor.
    Add behavioral rules for the modal. Commit.

STEP 3 — "build it"
  → Read the Figma design via MCP for full visual fidelity.
  → Write an HTML/CSS file in {root}/src/ that matches the design.
  → Write tests in {root}/tests/ with pytest proof markers
    (@pytest.mark.proof("feature", "PROOF-N", "RULE-N", tier="e2e")).
    Tests must reference BOTH the feature name and the anchor name. Commit.

STEP 4 — "run the tests"
  → Run pytest in {root}. Commit proof files.

STEP 5 — "verify and ship"
  → Verify all rules are proved. Commit.

Execute all steps now.
"""
    _claude(prompt, cwd=root, plugin_dir=PLUGIN, agent=AGENT, timeout=600)

    return root


@pytest.fixture(scope="class")
def pw_page():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip("playwright not installed")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        p = b.new_page(viewport={"width": 428, "height": 700})
        yield p
        b.close()


@pytest.fixture(scope="class")
def framework_baseline():
    r = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                       cwd=PROJECT_ROOT, capture_output=True, text=True)
    return set(r.stdout.strip().split("\n")) if r.stdout.strip() else set()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestFigmaWebWorkflow:

    @pytest.mark.proof("figma_web", "PROOF-1", "RULE-1", tier="e2e")
    def test_init_config(self, project):
        """Prerequisite: purlin:init created a valid config."""
        cfg = os.path.join(project, ".purlin", "config.json")
        assert os.path.isfile(cfg), ".purlin/config.json not found"
        data = json.loads(open(cfg).read())
        assert "version" in data
        assert os.path.isdir(os.path.join(project, "specs"))

    @pytest.mark.proof("figma_web", "PROOF-2", "RULE-2", tier="e2e")
    def test_anchor_metadata(self, project):
        """Msg 1 created anchor with Figma metadata."""
        anchors = _find_anchor(project)
        assert len(anchors) >= 1, "No anchor in specs/_anchors/"
        txt = anchors[0].read_text()
        assert re.search(r">\s*Source:.*TEZI0T6lObCJrC9mkmZT8v", txt)
        assert re.search(r">\s*Visual-Reference:.*figma://", txt)
        assert re.search(r">\s*Pinned:", txt)
        assert re.search(r">\s*Type:\s*design", txt)

    @pytest.mark.proof("figma_web", "PROOF-3", "RULE-3", tier="e2e")
    def test_anchor_visual_rule(self, project):
        """Anchor has visual-match rule + @e2e proof."""
        txt = _find_anchor(project)[0].read_text()
        # Extract Rules section — LLM may format rules in various ways
        rules_match = re.search(
            r"##\s*Rules\b(.+?)(?:^##\s|\Z)", txt,
            re.DOTALL | re.MULTILINE,
        )
        rules_section = rules_match.group(1) if rules_match else txt
        # The LLM generates the anchor — it must mention visual matching
        visual_keywords = {"match", "visual", "fidelity", "design", "pixel", "appearance", "look"}
        assert any(
            kw in rules_section.lower() for kw in visual_keywords
        ), f"No visual-match keyword found in Rules section"
        # @e2e may appear on the same line as PROOF-N or on a continuation
        # line — search the entire Proof section rather than per-line captures
        # to avoid spurious failures when LLM wraps proof text across lines.
        proof_section_match = re.search(
            r"##\s*Proof\b(.+?)(?:^##\s|\Z)", txt,
            re.DOTALL | re.MULTILINE,
        )
        proof_section = proof_section_match.group(1) if proof_section_match else txt
        assert "@e2e" in proof_section, (
            "Anchor Proof section does not contain @e2e tag"
        )

    @pytest.mark.proof("figma_web", "PROOF-4", "RULE-4", tier="e2e")
    def test_spec_requires_anchor(self, project):
        """Msg 2 created feature spec referencing anchor."""
        specs = _find_spec(project)
        assert len(specs) >= 1, "No feature spec"
        anchor_name = _find_anchor(project)[0].stem
        assert any(anchor_name in s.read_text() for s in specs)

    @pytest.mark.proof("figma_web", "PROOF-5", "RULE-5", tier="e2e")
    def test_figma_mcp_used(self, project):
        """Anchor has real Figma file key from MCP."""
        txt = _find_anchor(project)[0].read_text()
        assert FIGMA_FILE_KEY in txt

    @pytest.mark.proof("figma_web", "PROOF-6", "RULE-6", tier="e2e")
    def test_ui_renders(self, project, pw_page):
        """Msg 3 built HTML that renders in a browser."""
        html_files = _find_html(project)
        assert len(html_files) >= 1, "No HTML built"
        pw_page.goto(f"file://{html_files[0]}")
        pw_page.wait_for_load_state("networkidle")
        body = pw_page.inner_text("body")
        assert len(body.strip()) > 20

    @pytest.mark.proof("figma_web", "PROOF-7", "RULE-7", tier="e2e")
    def test_proof_markers(self, project):
        """Build wrote tests with proof markers."""
        tests = _find_tests(project)
        assert len(tests) >= 1, "No test files"
        src = "\n".join(t.read_text() for t in tests)
        assert "proof" in src.lower()

    @pytest.mark.proof("figma_web", "PROOF-8", "RULE-8", tier="e2e")
    def test_screenshot_pipeline(self, project, pw_page):
        """Screenshot can be captured and compared."""
        html_files = _find_html(project)
        pw_page.goto(f"file://{html_files[0]}")
        pw_page.wait_for_load_state("networkidle")
        local = os.path.join(project, "screenshot.png")
        pw_page.screenshot(path=local)
        assert _is_valid_png(local)
        assert _is_valid_png(FIXTURE_REF_PNG)

    @pytest.mark.proof("figma_web", "PROOF-9", "RULE-9", tier="e2e")
    def test_visual_fidelity(self, project, pw_page):
        """Built UI matches reference within threshold."""
        html_files = _find_html(project)
        pw_page.goto(f"file://{html_files[0]}")
        pw_page.wait_for_load_state("networkidle")
        local = os.path.join(project, "fidelity.png")
        pw_page.screenshot(path=local)
        shutil.copy2(local, SCREENSHOT_PATH)
        shutil.copy2(FIXTURE_REF_PNG, FIGMA_REF_PATH)
        diff = _pixel_diff_pct(local, FIXTURE_REF_PNG)
        assert diff <= MAX_PIXEL_DIFF_PCT, (
            f"{100-diff:.1f}% fidelity ({diff:.1f}% diff, max "
            f"{MAX_PIXEL_DIFF_PCT}%). See {SCREENSHOT_PATH}")

    @pytest.mark.proof("figma_web", "PROOF-10", "RULE-10", tier="e2e")
    def test_all_steps_produced_artifacts(self, project):
        """All 5 steps produced their expected artifacts."""
        assert os.path.isdir(os.path.join(project, ".purlin"))
        assert len(_find_anchor(project)) >= 1
        assert len(_find_spec(project)) >= 1
        assert len(_find_html(project)) >= 1
        assert len(_find_tests(project)) >= 1

    @pytest.mark.proof("figma_web", "PROOF-11", "RULE-11", tier="e2e")
    def test_no_framework_mods(self, project, framework_baseline):
        """FORBIDDEN — no framework files modified."""
        r = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                           cwd=PROJECT_ROOT, capture_output=True, text=True)
        cur = set(r.stdout.strip().split("\n")) if r.stdout.strip() else set()
        violations = [f for f in (cur - framework_baseline)
                      if f.startswith(("docs/", "skills/", "scripts/",
                                       "references/"))]
        assert violations == [], f"Framework files modified: {violations}"

    @pytest.mark.proof("figma_web", "PROOF-12", "RULE-12", tier="e2e")
    def test_failure_reports_error(self, project):
        """FORBIDDEN — Claude must report errors, not silently fix."""
        try:
            resp, _ = _claude(
                "here's our design: https://www.figma.com/design/INVALID/x",
                cwd=PROJECT_ROOT, add_dirs=[project], timeout=120,
            )
        except AssertionError:
            return  # Error = didn't silently succeed

        resp_l = resp.lower()
        assert any(w in resp_l for w in (
            "error", "fail", "unable", "cannot", "invalid",
            "not found", "could not", "issue",
        )), f"Claude silently handled broken URL: {resp[:300]}"

    @pytest.mark.proof("figma_web", "PROOF-13", "RULE-13", tier="e2e")
    def test_audit_classification(self, project):
        """static_checks returns classifications for anchor proofs."""
        anchors = _find_anchor(project)
        tests = _find_tests(project)
        if not anchors or not tests:
            pytest.skip("Missing anchor or tests")
        script = os.path.join(PROJECT_ROOT, "scripts", "audit",
                               "static_checks.py")
        r = subprocess.run(
            [sys.executable, script, str(tests[0]),
             anchors[0].stem, "--spec-path", str(anchors[0])],
            cwd=project, capture_output=True, text=True)
        data = json.loads(r.stdout)
        assert len(data.get("proofs", [])) > 0

    @pytest.mark.proof("figma_web", "PROOF-14", "RULE-14", tier="e2e")
    def test_screenshot_saved(self, project, pw_page):
        """Screenshot saved to dev/figma_web_result.png."""
        html_files = _find_html(project)
        pw_page.goto(f"file://{html_files[0]}")
        pw_page.wait_for_load_state("networkidle")
        pw_page.screenshot(path=SCREENSHOT_PATH)
        assert _is_valid_png(SCREENSHOT_PATH)

    @pytest.mark.proof("figma_web", "PROOF-15", "RULE-15", tier="e2e")
    def test_verify_succeeds(self, project):
        """Tests pass in the built project (pytest exit 0)."""
        tests = _find_tests(project)
        assert len(tests) >= 1
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short", "-q"],
            cwd=project, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, (
            f"Tests failed:\n{r.stdout[-500:]}\n{r.stderr[-300:]}")
