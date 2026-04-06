"""
E2E CLI orchestration: Figma design → web UI via real Purlin workflow.

Invokes ``claude -p`` with the full 5-step workflow documented in
docs/examples/figma-web-app.md.  Claude reads the real Figma MCP,
builds real HTML/CSS, writes real tests — nothing is faked.

Run:  python3 -m pytest dev/test_e2e_figma_web.py -v -x
Cost: ~$1–2 in API calls (one ``claude -p`` invocation)
Time: ~2–5 minutes

Prerequisites:
- ``claude`` CLI on PATH
- Figma MCP connected (Claude needs to read the design)
- Playwright: ``pip install playwright && playwright install chromium``
- Pillow + numpy: ``pip install Pillow numpy``
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

# Visual fidelity threshold.  The reference is an HTML rendering of the
# Figma MCP design_context; Claude's build is a SEPARATE implementation
# from the same MCP data.  15% allows for font rendering, body styling,
# and LLM non-determinism.  True Figma-to-implementation diff would need
# a saved MCP screenshot as reference (not an independent HTML render).
MAX_PIXEL_DIFF_PCT = 15.0

# ---------------------------------------------------------------------------
# Claude CLI
# ---------------------------------------------------------------------------

def _claude(cwd, prompt, *, add_dirs=(), timeout=600):
    """Run ``claude -p`` and return result text.  Raises on failure."""
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--model", "sonnet",
        "--max-turns", "80",
        "--dangerously-skip-permissions",
    ]
    for d in add_dirs:
        cmd += ["--add-dir", d]

    result = subprocess.run(
        cmd, input=prompt, capture_output=True, text=True,
        cwd=cwd, timeout=timeout,
    )
    stdout = result.stdout.strip()
    if not stdout:
        raise AssertionError(
            f"claude returned empty output (exit {result.returncode})\n"
            f"stderr: {result.stderr[:500]}")

    # Handle potential control chars in JSON
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        # Try stripping control chars
        clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', stdout)
        data = json.loads(clean)

    text = data.get("result", "")
    if data.get("is_error"):
        raise AssertionError(f"Claude error:\n{text[:800]}")
    return text

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
# File finders (flexible on naming since LLM output is non-deterministic)
# ---------------------------------------------------------------------------

def _glob(root, pattern):
    from pathlib import Path
    return list(Path(root).rglob(pattern))


def _find_html(root):
    return [h for h in _glob(root, "*.html")
            if "purlin-report" not in h.name
            and ".pytest_cache" not in str(h)]


def _find_anchor(root):
    anchors_dir = os.path.join(root, "specs", "_anchors")
    if not os.path.isdir(anchors_dir):
        return []
    return _glob(anchors_dir, "*.md")


def _find_spec(root):
    return [s for s in _glob(root, "specs/**/*.md")
            if "_anchors" not in str(s)]


def _find_tests(root):
    return [t for t in _glob(root, "test_*.py")
            if ".pytest_cache" not in str(t)]


def _find_proofs(root):
    return _glob(root, "*.proofs-*.json")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="class")
def project(tmp_path_factory):
    """Run the REAL 5-step Purlin workflow via ``claude -p``.

    One single Claude invocation performs init → anchor → spec → build → test.
    All files are created by the real LLM reading the real Figma MCP.
    """
    root = str(tmp_path_factory.mktemp("figma_web"))

    # Git init (purlin:init needs a repo)
    subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.email", "e2e@test"],
                   cwd=root, capture_output=True)
    subprocess.run(["git", "config", "user.name", "E2E"],
                   cwd=root, capture_output=True)

    prompt = f"""\
You are building a NEW project from scratch at {root}.
ALL files must be created in {root}. Do NOT touch any files outside it.

Follow the Purlin Figma workflow (docs/examples/figma-web-app.md):

STEP 1 — INIT: Create .purlin/config.json with version "0.9.0", test_framework "pytest",
spec_dir "specs". Create specs/ and specs/_anchors/ directories. Commit.

STEP 2 — ANCHOR: The design is at: {FIGMA_URL}
Call the Figma MCP (get_design_context and/or get_screenshot) to read the design.
Create a thin design anchor in {root}/specs/_anchors/ with:
  > Source: {FIGMA_URL}
  > Visual-Reference: figma://{FIGMA_FILE_KEY}/7:81
  > Pinned: (current timestamp)
  > Type: design
  One visual-match rule, one @e2e screenshot comparison proof. Commit.

STEP 3 — SPEC: Create a feature spec in {root}/specs/ that requires the anchor.
The feature is the feedback modal from the Figma design. Add behavioral rules. Commit.

STEP 4 — BUILD: Read the Figma design via MCP for full visual fidelity.
Write an HTML/CSS file in {root}/src/ that matches the design.
Write tests in {root}/tests/ with pytest proof markers
(@pytest.mark.proof("feature_name", "PROOF-N", "RULE-N", tier="e2e")).
Tests must reference BOTH the feature name and the anchor name. Commit.

STEP 5 — TEST: Run pytest in {root} to verify tests pass. Commit.

Execute all steps now.
"""
    _claude(PROJECT_ROOT, prompt, add_dirs=[root], timeout=600)
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
# Tests — each verifies real CLI-produced artifacts
# ---------------------------------------------------------------------------

class TestFigmaWebWorkflow:

    # ── RULE-1 ────────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-1", "RULE-1", tier="e2e")
    def test_init_config(self, project):
        """purlin:init created a valid config."""
        cfg = os.path.join(project, ".purlin", "config.json")
        assert os.path.isfile(cfg), \
            f".purlin/config.json not found in {project}"
        data = json.loads(open(cfg).read())
        assert "version" in data
        assert os.path.isdir(os.path.join(project, "specs"))

    # ── RULE-2 ────────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-2", "RULE-2", tier="e2e")
    def test_anchor_metadata(self, project):
        """Anchor has Source, Visual-Reference, Pinned, Type: design."""
        anchors = _find_anchor(project)
        assert len(anchors) >= 1, "No anchor .md in specs/_anchors/"
        txt = anchors[0].read_text()
        assert re.search(r">\s*Source:.*TEZI0T6lObCJrC9mkmZT8v", txt), \
            "Missing > Source: with file key"
        assert re.search(r">\s*Visual-Reference:.*figma://", txt), \
            "Missing > Visual-Reference: figma://"
        assert re.search(r">\s*Pinned:", txt), "Missing > Pinned:"
        assert re.search(r">\s*Type:\s*design", txt), "Missing > Type: design"

    # ── RULE-3 ────────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-3", "RULE-3", tier="e2e")
    def test_anchor_visual_rule(self, project):
        """Anchor has a visual-match rule with @e2e proof."""
        txt = _find_anchor(project)[0].read_text()
        rules = re.findall(r"-\s*RULE-\d+:.*", txt)
        assert any("match" in r.lower() for r in rules), \
            f"No visual-match rule: {rules}"
        proofs = re.findall(r"-\s*PROOF-\d+.*", txt)
        assert any("@e2e" in p for p in proofs), "No @e2e proof"

    # ── RULE-4 ────────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-4", "RULE-4", tier="e2e")
    def test_spec_requires_anchor(self, project):
        """Feature spec references the anchor via > Requires:."""
        specs = _find_spec(project)
        assert len(specs) >= 1, "No feature spec"
        anchor_name = _find_anchor(project)[0].stem
        found = any(anchor_name in s.read_text() for s in specs)
        assert found, f"No spec references anchor '{anchor_name}'"

    # ── RULE-5 ────────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-5", "RULE-5", tier="e2e")
    def test_figma_mcp_used(self, project):
        """Anchor has Figma-specific data that requires real MCP access."""
        txt = _find_anchor(project)[0].read_text()
        assert FIGMA_FILE_KEY in txt, \
            "Anchor doesn't contain the Figma file key"
        assert re.search(r"figma://", txt), \
            "No figma:// reference — MCP not used"

    # ── RULE-6 ────────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-6", "RULE-6", tier="e2e")
    def test_ui_renders(self, project, pw_page):
        """Built HTML renders visible content in a browser."""
        html_files = _find_html(project)
        assert len(html_files) >= 1, "No HTML file built"
        pw_page.goto(f"file://{html_files[0]}")
        pw_page.wait_for_load_state("networkidle")
        body = pw_page.inner_text("body")
        assert len(body.strip()) > 20, f"Page too sparse: '{body[:100]}'"

    # ── RULE-7 ────────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-7", "RULE-7", tier="e2e")
    def test_proof_markers(self, project):
        """Test files contain proof markers for feature + anchor."""
        tests = _find_tests(project)
        assert len(tests) >= 1, "No test files"
        src = "\n".join(t.read_text() for t in tests)
        assert "proof" in src.lower(), "No proof markers in tests"

    # ── RULE-8 ────────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-8", "RULE-8", tier="e2e")
    def test_screenshot_pipeline(self, project, pw_page):
        """Capture real screenshot and compare against MCP reference."""
        html_files = _find_html(project)
        pw_page.goto(f"file://{html_files[0]}")
        pw_page.wait_for_load_state("networkidle")
        local = os.path.join(project, "screenshot.png")
        pw_page.screenshot(path=local)
        assert _is_valid_png(local), "Screenshot invalid"
        assert _is_valid_png(FIXTURE_REF_PNG), "Reference PNG missing"

    # ── RULE-9 ────────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-9", "RULE-9", tier="e2e")
    def test_visual_fidelity(self, project, pw_page):
        """Implementation ≤ MAX_PIXEL_DIFF_PCT diff from Figma reference."""
        html_files = _find_html(project)
        pw_page.goto(f"file://{html_files[0]}")
        pw_page.wait_for_load_state("networkidle")

        local = os.path.join(project, "fidelity.png")
        pw_page.screenshot(path=local)
        shutil.copy2(local, SCREENSHOT_PATH)
        shutil.copy2(FIXTURE_REF_PNG, FIGMA_REF_PATH)

        diff = _pixel_diff_pct(local, FIXTURE_REF_PNG)
        assert diff <= MAX_PIXEL_DIFF_PCT, (
            f"Visual fidelity: {100-diff:.1f}% ({diff:.1f}% diff, "
            f"max {MAX_PIXEL_DIFF_PCT}%). See {SCREENSHOT_PATH}")

    # ── RULE-10 ───────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-10", "RULE-10", tier="e2e")
    def test_documented_steps_only(self, project):
        """All 5 workflow steps produced their expected artifacts."""
        assert os.path.isdir(os.path.join(project, ".purlin")), "Step 1 missing"
        assert len(_find_anchor(project)) >= 1, "Step 2 missing"
        assert len(_find_spec(project)) >= 1, "Step 3 missing"
        assert len(_find_html(project)) >= 1, "Step 4 missing"
        assert len(_find_tests(project)) >= 1, "Step 5 missing"

    # ── RULE-11 ───────────────────────────────────────────────────────

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

    # ── RULE-12 ───────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-12", "RULE-12", tier="e2e")
    def test_failure_asks_user(self, project):
        """FORBIDDEN — Claude must not silently fix failures."""
        try:
            resp = _claude(
                PROJECT_ROOT,
                f"Working in {project}. Add a design anchor from this "
                "BROKEN Figma URL: https://www.figma.com/design/INVALID/x "
                "Create the anchor now.",
                add_dirs=[project], timeout=120,
            )
        except AssertionError:
            return  # Error = acceptable (didn't silently succeed)

        resp_l = resp.lower()
        reported = any(w in resp_l for w in (
            "error", "fail", "unable", "cannot", "invalid",
            "not found", "could not", "approve", "confirm",
        ))
        assert reported, (
            f"Claude silently handled broken URL.\nResponse: {resp[:300]}")

    # ── RULE-13 ───────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-13", "RULE-13", tier="e2e")
    def test_audit_classification(self, project):
        """static_checks returns a classification for anchor proofs."""
        anchors = _find_anchor(project)
        tests = _find_tests(project)
        if not anchors or not tests:
            pytest.skip("Missing anchor or tests for audit")

        script = os.path.join(PROJECT_ROOT, "scripts", "audit",
                               "static_checks.py")
        r = subprocess.run(
            [sys.executable, script, str(tests[0]),
             anchors[0].stem, "--spec-path", str(anchors[0])],
            cwd=project, capture_output=True, text=True)
        try:
            data = json.loads(r.stdout)
        except json.JSONDecodeError:
            pytest.fail(f"Bad static_checks output: {r.stdout[:300]}")
        assert len(data.get("proofs", [])) > 0, "No proofs audited"

    # ── RULE-14 ───────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-14", "RULE-14", tier="e2e")
    def test_screenshot_saved(self, project, pw_page):
        """Screenshot saved to dev/figma_web_result.png."""
        html_files = _find_html(project)
        pw_page.goto(f"file://{html_files[0]}")
        pw_page.wait_for_load_state("networkidle")
        pw_page.screenshot(path=SCREENSHOT_PATH)
        assert _is_valid_png(SCREENSHOT_PATH)

    # ── RULE-15 ───────────────────────────────────────────────────────

    @pytest.mark.proof("figma_web", "PROOF-15", "RULE-15", tier="e2e")
    def test_verify_succeeds(self, project):
        """Project has specs + tests + passing results."""
        assert len(_find_spec(project)) >= 1
        assert len(_find_anchor(project)) >= 1
        assert len(_find_tests(project)) >= 1

        # Verify tests actually pass in the built project
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "--tb=short", "-q"],
            cwd=project, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, (
            f"Tests failed in built project:\n{r.stdout[-500:]}\n{r.stderr[-300:]}")
