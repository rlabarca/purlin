"""
Playwright e2e tests for the purlin_report dashboard feature.

Each test loads scripts/report/purlin-report.html via file:// in a real
Chromium browser with synthetic PURLIN_DATA, then verifies DOM state.
"""

import datetime
import json
import os
import shutil

import pytest
from playwright.sync_api import sync_playwright


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HTML_SRC = os.path.join(os.path.dirname(__file__), "..", "scripts", "report", "purlin-report.html")
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots")

os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Synthetic data helpers
# ---------------------------------------------------------------------------

def make_data(overrides=None):
    """Generate minimal valid PURLIN_DATA."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data = {
        "timestamp": now,
        "project": "test-project",
        "version": "0.9.0",
        "docs_url": "https://example.com/docs",
        "summary": {
            "total_features": 3,
            "verified": 1,
            "partial": 1,
            "failing": 0,
            "untested": 1,
        },
        "features": [
            {
                "name": "auth_login",
                "category": "auth",
                "type": "feature",
                "is_global": False,
                "description": "Handles user login with session tokens and secure cookies.",
                "source_url": None,
                "proved": 3,
                "total": 3,
                "deferred": 0,
                "status": "VERIFIED",

                "vhash": "a1b2c3d4",
                "receipt": {"commit": "abc123", "timestamp": now, "stale": False},
                "rules": [
                    {
                        "id": "RULE-1",
                        "description": "Returns 200",
                        "label": "own",
                        "source": None,
                        "is_deferred": False,
                        "is_assumed": False,
                        "status": "PASS",
                        "proofs": [
                            {
                                "id": "PROOF-1",
                                "description": "POST valid creds returns 200 + session token",
                                "test_file": "tests/test_login.py",
                                "test_name": "test_valid",
                                "tier": "unit",
                                "status": "pass",
                            },
                            {
                                "id": "PROOF-4",
                                "description": "POST valid creds sets session cookie with httponly flag",
                                "test_file": "tests/test_login.py",
                                "test_name": "test_cookie",
                                "tier": "unit",
                                "status": "pass",
                            },
                        ],
                    },
                    {
                        "id": "RULE-2",
                        "description": "Returns 401 on bad creds",
                        "label": "own",
                        "source": None,
                        "is_deferred": False,
                        "is_assumed": False,
                        "status": "PASS",
                        "proofs": [{
                            "id": "PROOF-2",
                            "description": "POST bad creds returns 401 with error message",
                            "test_file": "tests/test_login.py",
                            "test_name": "test_invalid",
                            "tier": "unit",
                            "status": "pass",
                        }],
                    },
                    {
                        "id": "security/RULE-1",
                        "description": "No eval()",
                        "label": "global",
                        "source": "security",
                        "is_deferred": False,
                        "is_assumed": False,
                        "status": "PASS",
                        "proofs": [{
                            "id": "PROOF-1",
                            "description": "Grep src/ for eval(); verify zero matches",
                            "test_file": "tests/test_sec.py",
                            "test_name": "test_no_eval",
                            "tier": "unit",
                            "status": "pass",
                        }],
                    },
                ],
                "audit": {
                    "integrity": 85,
                    "strong": 2,
                    "weak": 1,
                    "hollow": 0,
                    "manual": 0,
                    "findings": [
                        {
                            "proof_id": "PROOF-2",
                            "rule_id": "RULE-2",
                            "level": "WEAK",
                            "priority": "HIGH",
                            "criterion": "missing negative test",
                            "fix": "add error case",
                        }
                    ],
                },
            },
            {
                "name": "checkout",
                "category": "commerce",
                "type": "feature",
                "is_global": False,
                "description": None,
                "source_url": None,
                "proved": 1,
                "total": 2,
                "deferred": 0,
                "status": "PARTIAL",

                "vhash": None,
                "receipt": None,
                "rules": [
                    {
                        "id": "RULE-1",
                        "description": "Calculates total",
                        "label": "own",
                        "source": None,
                        "is_deferred": False,
                        "is_assumed": False,
                        "status": "PASS",
                        "proofs": [{
                            "id": "PROOF-1",
                            "description": "Sum item prices times quantities; verify total",
                            "test_file": "tests/test_checkout.py",
                            "test_name": "test_total",
                            "tier": "unit",
                            "status": "pass",
                        }],
                    },
                    {
                        "id": "RULE-2",
                        "description": "Sends confirmation email",
                        "label": "own",
                        "source": None,
                        "is_deferred": False,
                        "is_assumed": False,
                        "status": "NO_PROOF",
                        "proofs": [],
                    },
                ],
                "audit": None,
            },
            {
                "name": "security_policy",
                "category": "_anchors",
                "type": "anchor",
                "is_global": True,
                "description": "Enforces the absence of dangerous code patterns across all scripts.",
                "source_url": "git@github.com:acme/policies.git",
                "proved": 2,
                "total": 2,
                "deferred": 0,
                "status": "VERIFIED",

                "vhash": "e5f6a7b8",
                "receipt": {"commit": "def456", "timestamp": now, "stale": False},
                "rules": [
                    {
                        "id": "RULE-1",
                        "description": "No eval()",
                        "label": "own",
                        "source": None,
                        "is_deferred": False,
                        "is_assumed": False,
                        "status": "PASS",
                        "proofs": [{
                            "id": "PROOF-1",
                            "description": "Grep src/ for eval(); verify zero matches",
                            "test_file": "tests/test_sec.py",
                            "test_name": "test_no_eval",
                            "tier": "unit",
                            "status": "pass",
                        }],
                    },
                    {
                        "id": "RULE-2",
                        "description": "No exec()",
                        "label": "own",
                        "source": None,
                        "is_deferred": False,
                        "is_assumed": False,
                        "status": "PASS",
                        "proofs": [{
                            "id": "PROOF-2",
                            "description": "Grep src/ for exec(); verify zero matches",
                            "test_file": "tests/test_sec.py",
                            "test_name": "test_no_exec",
                            "tier": "unit",
                            "status": "pass",
                        }],
                    },
                ],
                "audit": None,
            },
        ],
        "anchors_summary": {"total": 1, "with_source": 1, "global": 1},
        "audit_summary": {
            "integrity": 85,
            "strong": 4,
            "weak": 1,
            "hollow": 0,
            "manual": 0,
            "behavioral_total": 5,
            "last_audit": now,
            "last_audit_relative": "just now",
            "stale": False,
        },
        "drift": None,
    }
    if overrides:
        data.update(overrides)
    return data


def write_data(tmp_dir, data):
    """Write report-data.js to a .purlin subdir in tmp_dir."""
    purlin_dir = os.path.join(tmp_dir, ".purlin")
    os.makedirs(purlin_dir, exist_ok=True)
    with open(os.path.join(purlin_dir, "report-data.js"), "w") as f:
        f.write("const PURLIN_DATA = ")
        json.dump(data, f)
        f.write(";\n")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def page(browser):
    pg = browser.new_page(viewport={"width": 1920, "height": 1080})
    yield pg
    pg.close()


@pytest.fixture
def dashboard(tmp_path):
    """Copy the HTML file into a temp directory and return the temp path."""
    shutil.copy(HTML_SRC, tmp_path / "purlin-report.html")
    return tmp_path


def load_dashboard(page, dashboard_dir, data=None, expand_categories=True):
    """Write data and navigate to the dashboard."""
    if data is not None:
        write_data(str(dashboard_dir), data)
    url = f"file://{dashboard_dir}/purlin-report.html"
    page.goto(url)
    page.wait_for_load_state("networkidle")
    if expand_categories and data is not None:
        # Set category open state in localStorage, then reload so the
        # page picks it up on init.
        cats = list({f.get("category", "other") for f in data.get("features", [])})
        if cats:
            cat_state = {c: True for c in cats}
            page.evaluate(
                "s => localStorage.setItem('purlin-categories', JSON.stringify(s))",
                cat_state,
            )
            page.reload()
            page.wait_for_load_state("networkidle")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPurlinReport:

    @pytest.mark.proof("purlin_report", "PROOF-1", "RULE-1")
    def test_script_tag_loads_data_js(self, page, dashboard):
        """PROOF-1: HTML loads .purlin/report-data.js dynamically."""
        load_dashboard(page, dashboard, data=make_data())
        # The data is loaded dynamically with cache-busting query param
        # Verify PURLIN_DATA is available in the page context
        has_data = page.evaluate("() => typeof PURLIN_DATA !== 'undefined'")
        assert has_data, "Expected PURLIN_DATA to be loaded from .purlin/report-data.js"
        # Verify the script element was injected
        src = page.evaluate("""() => {
            const scripts = document.querySelectorAll('script[src*="report-data.js"]');
            return scripts.length > 0 ? scripts[0].src : null;
        }""")
        assert src and 'report-data.js' in src, (
            f"Expected a script tag loading report-data.js, got: {src}"
        )

    @pytest.mark.proof("purlin_report", "PROOF-2", "RULE-2")
    def test_no_data_message(self, page, dashboard):
        """PROOF-2: Without report-data.js, dashboard shows a no-data message."""
        # Do NOT write report-data.js — navigate without data
        load_dashboard(page, dashboard, data=None)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof2_no_data.png"))
        body_text = page.inner_text("body")
        assert "No dashboard data" in body_text, (
            "Expected 'No dashboard data' message when PURLIN_DATA is undefined"
        )
        assert "purlin:status" in body_text, (
            "Expected 'purlin:status' instruction in no-data message"
        )

    @pytest.mark.proof("purlin_report", "PROOF-3", "RULE-3")
    def test_summary_strip_counts(self, page, dashboard):
        """PROOF-3: Summary strip shows Incomplete card combining partial + untested."""
        data = make_data({
            "summary": {
                "total_features": 10,
                "verified": 4,
                "passing": 2,
                "partial": 2,
                "failing": 1,
                "untested": 1,
            }
        })
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof3_summary.png"))
        cards = page.query_selector_all(".summary-card")
        assert len(cards) == 6, f"Expected 6 summary cards (incl. integrity), got {len(cards)}"
        strip_text = page.inner_text(".summary-strip")
        assert "10" in strip_text, "Expected total_features=10 in summary strip"
        assert "4" in strip_text, "Expected verified=4 in summary strip"
        # Incomplete card: 2 partial + 1 untested = 3
        incomplete_card = page.query_selector(".sc-partial")
        assert incomplete_card is not None, "Incomplete card (.sc-partial) not found"
        incomplete_text = incomplete_card.inner_text()
        assert "3" in incomplete_text, "Expected incomplete count=3 (2 partial + 1 untested)"
        assert "incomplete" in incomplete_text.lower(), "Expected label 'Incomplete'"
        assert "2 partial" in incomplete_text, "Expected subtitle '2 partial'"
        assert "1 untested" in incomplete_text, "Expected subtitle '1 untested'"

    @pytest.mark.proof("purlin_report", "PROOF-4", "RULE-4")
    def test_feature_table_row_count(self, page, dashboard):
        """PROOF-4: Feature table renders one row per feature."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        def make_feature(name, status, proved, total, category="test"):
            return {
                "name": name,
                "category": category,
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": proved,
                "total": total,
                "deferred": 0,
                "status": status,

                "vhash": None,
                "receipt": None,
                "rules": [],
                "audit": None,
            }

        features = [
            make_feature("alpha", "VERIFIED", 3, 3),
            make_feature("beta", "PARTIAL", 1, 2),
            make_feature("gamma", "VERIFIED", 2, 2),
            make_feature("delta", "PARTIAL", 0, 1),
            make_feature("epsilon", "VERIFIED", 4, 4),
            make_feature("zeta", "PARTIAL", 2, 3),
            make_feature("eta", "VERIFIED", 1, 1),
            make_feature("theta", "PARTIAL", 0, 2),
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 8, "verified": 4, "partial": 4, "failing": 0, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
        })
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof4_table_rows.png"))
        rows = page.query_selector_all("tr.fr")
        assert len(rows) == 8, f"Expected 8 feature rows (.fr), got {len(rows)}"

    @pytest.mark.proof("purlin_report", "PROOF-5", "RULE-5")
    def test_row_expand_shows_detail(self, page, dashboard):
        """PROOF-5: Clicking a feature row expands it to show per-rule detail."""
        load_dashboard(page, dashboard, data=make_data())
        # No detail rows should exist before clicking
        detail_rows_before = page.query_selector_all("tr.dr")
        assert len(detail_rows_before) == 0, "Expected no expanded rows initially"
        # Click the first feature row
        first_row = page.query_selector("tr.fr")
        assert first_row is not None, "Expected at least one feature row"
        first_row.click()
        page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof5_expanded.png"))
        # A .dr detail row should now be visible
        detail_rows = page.query_selector_all("tr.dr")
        assert len(detail_rows) > 0, "Expected at least one detail row (.dr) after clicking"
        # The detail row should contain a rules table (.rt)
        rules_table = detail_rows[0].query_selector("table.rt")
        assert rules_table is not None, "Expected a rules table (.rt) inside the expanded detail row"

    @pytest.mark.proof("purlin_report", "PROOF-6", "RULE-6")
    def test_expanded_rule_sources_and_multi_proof_stacking(self, page, dashboard):
        """PROOF-6: Own rules show empty Source; global rules show 'global';
        rules with multiple proofs stack them in a single td with .rprf-sep dividers."""
        load_dashboard(page, dashboard, data=make_data())
        page.click("tr.fr[data-name='auth_login']")
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof6_rule_sources.png"))

        # Verify source labels via JS (avoids first-detail-row ambiguity)
        texts = page.evaluate("""() => {
            const row = document.querySelector("tr.fr[data-name='auth_login']");
            const detail = row ? row.nextElementSibling : null;
            if (!detail || !detail.classList.contains('dr')) return [];
            return Array.from(detail.querySelectorAll('td.rlbl'))
                .map(c => c.textContent.trim().toLowerCase());
        }""")
        assert len(texts) >= 3, f"Expected >=3 source cells, got {len(texts)}"
        assert "" in texts, "Expected empty source cell for own rules"
        assert "global" in texts, f"Expected 'global' in source cells, got {texts}"

        # Verify multi-proof stacking: RULE-1 has 2 proofs in a single td
        multi_proof = page.evaluate("""() => {
            const row = document.querySelector("tr.fr[data-name='auth_login']");
            const detail = row ? row.nextElementSibling : null;
            if (!detail) return { seps: 0, proofIds: [], cellCount: 0 };
            // Find the first .rprf cell (RULE-1's proof cell)
            const cells = detail.querySelectorAll('td.rprf');
            const firstCell = cells[0];
            const seps = firstCell ? firstCell.querySelectorAll('.rprf-sep').length : 0;
            const proofIds = firstCell
                ? Array.from(firstCell.querySelectorAll('.fid')).map(e => e.textContent.trim())
                : [];
            return { seps: seps, proofIds: proofIds, cellCount: cells.length };
        }""")
        assert multi_proof["seps"] >= 1, \
            f"Expected >=1 .rprf-sep divider in multi-proof cell, got {multi_proof['seps']}"
        assert len(multi_proof["proofIds"]) >= 2, \
            f"Expected >=2 proof IDs in stacked cell, got {multi_proof['proofIds']}"
        # Verify table rows match rule count (no extra rowspan rows)
        assert multi_proof["cellCount"] == 3, \
            f"Expected 3 proof cells (one per rule), got {multi_proof['cellCount']}"

    @pytest.mark.proof("purlin_report", "PROOF-7", "RULE-7")
    def test_theme_toggle_persists(self, page, dashboard):
        """PROOF-7: Toggling dark/light mode persists preference to localStorage."""
        load_dashboard(page, dashboard, data=make_data())
        # Initial theme should be dark (default)
        initial_theme = page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        )
        assert initial_theme == "dark", f"Expected initial theme 'dark', got '{initial_theme}'"
        # Click the theme toggle
        page.click("#theme-btn")
        page.wait_for_timeout(200)
        new_theme = page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        )
        assert new_theme == "light", f"Expected theme to become 'light', got '{new_theme}'"
        # Verify localStorage was set
        stored = page.evaluate("() => localStorage.getItem('purlin-theme')")
        assert stored == "light", f"Expected localStorage 'purlin-theme'='light', got '{stored}'"
        # Reload the page — theme should persist
        page.reload()
        page.wait_for_load_state("networkidle")
        persisted_theme = page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')"
        )
        assert persisted_theme == "light", (
            f"Expected persisted theme 'light' after reload, got '{persisted_theme}'"
        )

    @pytest.mark.proof("purlin_report", "PROOF-8", "RULE-8")
    def test_staleness_warning_amber(self, page, dashboard):
        """PROOF-8: Staleness indicator shows amber warning when data is older than 1 hour."""
        two_hours_ago = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=2)
        ).isoformat()
        data = make_data({"timestamp": two_hours_ago})
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof8_stale_warning.png"))
        staleness_text = page.query_selector(".staleness-text")
        assert staleness_text is not None, "Expected .staleness-text element"
        text_content = staleness_text.inner_text()
        assert "ago" in text_content, f"Expected 'ago' in staleness text, got: '{text_content}'"
        css_class = staleness_text.get_attribute("class")
        assert "warning" in css_class, (
            f"Expected 'warning' CSS class on staleness text for 2h old data, got: '{css_class}'"
        )

    @pytest.mark.proof("purlin_report", "PROOF-9", "RULE-9")
    def test_staleness_stale_red(self, page, dashboard):
        """PROOF-9: Staleness indicator shows red warning when data is older than 24 hours."""
        two_days_ago = (
            datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(days=2)
        ).isoformat()
        data = make_data({"timestamp": two_days_ago})
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof9_stale_red.png"))
        staleness_text = page.query_selector(".staleness-text")
        assert staleness_text is not None, "Expected .staleness-text element"
        css_class = staleness_text.get_attribute("class")
        assert "stale" in css_class, (
            f"Expected 'stale' CSS class on staleness text for 2-day-old data, got: '{css_class}'"
        )

    @pytest.mark.proof("purlin_report", "PROOF-10", "RULE-10")
    def test_anchor_type_pills(self, page, dashboard):
        """PROOF-10: Anchor features display type pills (tp-global, tp-anchor)."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data = make_data()
        # Add a local (non-global) anchor feature
        data["features"].append({
            "name": "local_policy",
            "type": "anchor",
            "is_global": False,
            "source_url": None,
            "proved": 1,
            "total": 1,
            "deferred": 0,
            "status": "VERIFIED",

            "vhash": None,
            "receipt": None,
            "rules": [],
            "audit": None,
        })
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof10_anchor_pills.png"))
        # security_policy is type=anchor, is_global=True => tp-global
        global_pills = page.query_selector_all(".tp-global")
        assert len(global_pills) > 0, "Expected at least one .tp-global pill for global anchor"
        # local_policy is type=anchor, is_global=False => tp-anchor
        anchor_pills = page.query_selector_all(".tp-anchor")
        assert len(anchor_pills) > 0, "Expected at least one .tp-anchor pill for local anchor"

    @pytest.mark.proof("purlin_report", "PROOF-11", "RULE-11")
    def test_anchor_external_link_icon(self, page, dashboard):
        """PROOF-11: Anchors with source_url display an external link icon with URL as tooltip."""
        load_dashboard(page, dashboard, data=make_data())
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof11_ext_icon.png"))
        ext_icons = page.query_selector_all(".ext-icon")
        assert len(ext_icons) > 0, "Expected at least one .ext-icon element for anchors with source_url"
        icon = ext_icons[0]
        title_attr = icon.get_attribute("title")
        assert title_attr is not None, "Expected .ext-icon to have a 'title' attribute"
        assert "git@github.com:acme/policies.git" in title_attr, (
            f"Expected source_url in title attribute, got: '{title_attr}'"
        )

    @pytest.mark.proof("purlin_report", "PROOF-12", "RULE-12")
    def test_table_sorting(self, page, dashboard):
        """PROOF-12: Clicking a column header changes the table row sort order."""
        # Use data where default status sort != coverage sort, guaranteeing a row-order change.
        # Default sort is by status (FAIL=0, PARTIAL=1, VERIFIED=2).
        # "alpha" is VERIFIED (order 2) with coverage 0/3 = 0.
        # "beta"  is PARTIAL (order 1) with coverage 3/3 = 1.
        # Default sort: beta first (PARTIAL), then alpha (VERIFIED).
        # Coverage-ascending sort: alpha first (0/3=0%), then beta (3/3=100%).
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        features = [
            {
                "name": "alpha", "category": "test", "type": "feature", "is_global": False, "source_url": None,
                "proved": 0, "total": 3, "deferred": 0, "status": "VERIFIED",
                "vhash": None, "receipt": None, "rules": [], "audit": None,
            },
            {
                "name": "beta", "category": "test", "type": "feature", "is_global": False, "source_url": None,
                "proved": 3, "total": 3, "deferred": 0, "status": "PARTIAL",
                "vhash": None, "receipt": None, "rules": [], "audit": None,
            },
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 2, "verified": 1, "partial": 1, "failing": 0, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
            "audit_summary": {
                "integrity": None, "strong": 0, "weak": 0, "hollow": 0, "manual": 0,
                "behavioral_total": 0, "last_audit": None, "last_audit_relative": None, "stale": False,
            },
        })
        load_dashboard(page, dashboard, data=data)
        # Default sort (by status): beta (PARTIAL) comes first
        rows_before = page.query_selector_all("tr.fr")
        assert len(rows_before) == 2, f"Expected 2 feature rows, got {len(rows_before)}"
        first_name_before = rows_before[0].get_attribute("data-name")
        assert first_name_before == "beta", (
            f"Expected 'beta' (PARTIAL) to be first under default status sort, got '{first_name_before}'"
        )
        # Click the "Coverage" column header — ascending coverage sort: alpha (0%) first
        coverage_header = page.query_selector("th[data-col='coverage']")
        assert coverage_header is not None, "Expected th[data-col='coverage'] to exist"
        coverage_header.click()
        page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof12_sorted.png"))
        rows_after = page.query_selector_all("tr.fr")
        first_name_after = rows_after[0].get_attribute("data-name")
        assert first_name_after == "alpha", (
            f"Expected 'alpha' (0% coverage) to be first after coverage-ascending sort, got '{first_name_after}'"
        )
        assert first_name_before != first_name_after, (
            f"Expected row order to change after clicking Coverage header. "
            f"First row was '{first_name_before}' before and '{first_name_after}' after."
        )

    @pytest.mark.proof("purlin_report", "PROOF-13", "RULE-13")
    def test_footer_docs_url(self, page, dashboard):
        """PROOF-13: Footer docs link uses docs_url from PURLIN_DATA, not hardcoded."""
        data = make_data({"docs_url": "https://example.com/docs"})
        load_dashboard(page, dashboard, data=data)
        footer_link = page.query_selector("footer a")
        assert footer_link is not None, "Expected a link in the footer"
        href = footer_link.get_attribute("href")
        assert href == "https://example.com/docs", (
            f"Expected footer link href='https://example.com/docs', got '{href}'"
        )

    @pytest.mark.proof("purlin_report", "PROOF-14", "RULE-14")
    def test_integrity_card_display(self, page, dashboard):
        """PROOF-14: Summary strip shows integrity %, or dash + 'run purlin:audit' when null."""
        # Case 1: integrity=85 — expect "85%" in summary strip
        data = make_data()
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof14_integrity_present.png"))
        strip_text = page.inner_text(".summary-strip")
        assert "85%" in strip_text, f"Expected '85%' in summary strip when integrity=85, got: '{strip_text}'"

        # Case 2: audit_summary with integrity=null (no audit)
        data_no_audit = make_data()
        data_no_audit["audit_summary"] = {
            "integrity": None,
            "strong": 0,
            "weak": 0,
            "hollow": 0,
            "manual": 0,
            "behavioral_total": 0,
            "last_audit": None,
            "last_audit_relative": None,
            "stale": False,
        }
        load_dashboard(page, dashboard, data=data_no_audit)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof14_integrity_null.png"))
        strip_text_null = page.inner_text(".summary-strip")
        assert "run purlin:audit" in strip_text_null, (
            f"Expected 'run purlin:audit' when integrity is null, got: '{strip_text_null}'"
        )

    @pytest.mark.proof("purlin_report", "PROOF-15", "RULE-15")
    def test_audit_time_stale_class(self, page, dashboard):
        """PROOF-15: Header shows last audit time with amber warning when stale."""
        data = make_data()
        data["audit_summary"]["stale"] = True
        data["audit_summary"]["last_audit_relative"] = "3h ago"
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof15_audit_stale.png"))
        stale_el = page.query_selector(".audit-time.stale")
        assert stale_el is not None, (
            "Expected element with class 'audit-time stale' when audit_summary.stale=true"
        )

    @pytest.mark.proof("purlin_report", "PROOF-16", "RULE-16")
    def test_status_column_centered_at_multiple_widths(self, page, dashboard):
        """PROOF-16: Status column centered in feature table and rules sub-table at different widths."""
        for width in [1920, 1280]:
            page.set_viewport_size({"width": width, "height": 1080})
            load_dashboard(page, dashboard, data=make_data())

            # Check feature table status badge centering
            feature_status_align = page.evaluate("""() => {
                const td = document.querySelector('td.col-status');
                return td ? getComputedStyle(td).textAlign : null;
            }""")
            assert feature_status_align == "center", \
                f"Feature table status not centered at {width}px: got '{feature_status_align}'"

            # Ensure auth_login is expanded (click only if collapsed)
            is_expanded = page.evaluate("""() => {
                const row = document.querySelector("tr.fr[data-name='auth_login']");
                return row && row.classList.contains('expanded');
            }""")
            if not is_expanded:
                page.click("tr.fr[data-name='auth_login']")
            page.wait_for_timeout(200)

            # Check rules sub-table status centering
            rule_status_align = page.evaluate("""() => {
                const td = document.querySelector('td.rst');
                return td ? getComputedStyle(td).textAlign : null;
            }""")
            assert rule_status_align == "center", \
                f"Rules sub-table status not centered at {width}px: got '{rule_status_align}'"

            page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"proof16_centered_{width}.png"))

    @pytest.mark.proof("purlin_report", "PROOF-17", "RULE-17")
    def test_responsive_layout(self, page, dashboard):
        """PROOF-17: Dashboard uses full width up to 2400px and reflows at 1100px."""
        # Wide viewport: 2400px — verify container max-width is 2400px
        page.set_viewport_size({"width": 2400, "height": 1080})
        load_dashboard(page, dashboard, data=make_data())
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof17_wide.png"))
        # Check computed max-width of the .dashboard element
        max_width = page.evaluate(
            "() => getComputedStyle(document.querySelector('.dashboard')).maxWidth"
        )
        assert max_width == "2400px", (
            f"Expected .dashboard max-width=2400px at wide viewport, got '{max_width}'"
        )

        # Narrow viewport: 600px — verify summary strip reflows to 3 columns
        # CSS breakpoint: @media (max-width:700px) { repeat(3,1fr) }
        page.set_viewport_size({"width": 600, "height": 900})
        page.reload()
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof17_narrow.png"))
        grid_cols = page.evaluate(
            "() => getComputedStyle(document.querySelector('.summary-strip')).gridTemplateColumns"
        )
        col_count = len(grid_cols.split())
        assert col_count == 3, (
            f"Expected 3 columns in summary-strip at 600px viewport, "
            f"got gridTemplateColumns='{grid_cols}' ({col_count} values)"
        )


# ---------------------------------------------------------------------------
# TestDashboardVisual — visual constants (anchor: dashboard_visual)
# ---------------------------------------------------------------------------

def rgb_to_hex(rgb_str):
    """Convert 'rgb(34, 197, 94)' or 'rgba(...)' to '#22c55e'."""
    import re
    m = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', rgb_str)
    if m:
        return '#{:02x}{:02x}{:02x}'.format(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return rgb_str


def make_fail_feature(name):
    """Return a minimal feature dict with FAIL status."""
    return {
        "name": name,
        "category": "test",
        "type": "feature",
        "is_global": False,
        "source_url": None,
        "proved": 0,
        "total": 1,
        "deferred": 0,
        "status": "FAILING",

        "vhash": None,
        "receipt": None,
        "rules": [],
        "audit": None,
    }


def make_integrity_feature(name, integrity):
    """Return a feature with a specific audit integrity value."""
    return {
        "name": name,
        "category": "test",
        "type": "feature",
        "is_global": False,
        "source_url": None,
        "proved": 2,
        "total": 2,
        "deferred": 0,
        "status": "VERIFIED",

        "vhash": None,
        "receipt": None,
        "rules": [],
        "audit": {
            "integrity": integrity,
            "strong": 1,
            "weak": 0,
            "hollow": 0,
            "manual": 0,
            "findings": [],
        },
    }


class TestRulePadding:
    """Test that rule ID and description columns have visible spacing for all rule types."""

    @pytest.mark.proof("purlin_report", "PROOF-18", "RULE-6")
    def test_rule_id_padding_with_long_anchor_ids(self, page, dashboard):
        """Rule IDs from required anchors (e.g. security_policy/RULE-1) must have
        visible gap before the description column at both narrow and wide viewports."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data = make_data({
            "features": [{
                "name": "config_engine", "category": "mcp", "type": "feature", "is_global": False,
                "source_url": None, "proved": 2, "total": 4, "deferred": 0,
                "status": "PARTIAL", "vhash": None,
                "receipt": None,
                "rules": [
                    {"id": "RULE-1", "description": "Reads config files", "label": "own",
                     "source": None, "is_deferred": False, "is_assumed": False,
                     "status": "PASS", "proofs": [{"id": "PROOF-1", "description": "Read config",
                     "test_file": "tests/test_config.py", "test_name": "test_read",
                     "tier": "unit", "status": "pass"}]},
                    {"id": "security_no_dangerous_patterns/RULE-1",
                     "description": "FORBIDDEN — No eval() or exec() calls",
                     "label": "required", "source": "security_no_dangerous_patterns",
                     "is_deferred": False, "is_assumed": False,
                     "status": "PASS", "proofs": []},
                    {"id": "security_no_dangerous_patterns/RULE-2",
                     "description": "FORBIDDEN — No subprocess calls with shell=True",
                     "label": "required", "source": "security_no_dangerous_patterns",
                     "is_deferred": False, "is_assumed": False,
                     "status": "PASS", "proofs": []},
                    {"id": "security_no_dangerous_patterns/RULE-3",
                     "description": "FORBIDDEN — No os.system() calls",
                     "label": "required", "source": "security_no_dangerous_patterns",
                     "is_deferred": False, "is_assumed": False,
                     "status": "PASS", "proofs": [{"id": "PROOF-3", "description": "Grep for os.system",
                     "test_file": "tests/test_sec.py", "test_name": "test_no_ossystem",
                     "tier": "unit", "status": "pass"}]},
                ],
                "audit": None,
            }],
            "summary": {"total_features": 1, "verified": 0, "partial": 1, "failing": 0, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
            "audit_summary": None,
        })

        for width in [1920, 1280]:
            page.set_viewport_size({"width": width, "height": 1080})
            load_dashboard(page, dashboard, data=data)
            # Click to expand only if not already expanded
            is_expanded = page.evaluate("""() => {
                const row = document.querySelector("tr.fr[data-name='config_engine']");
                return row && row.classList.contains('expanded');
            }""")
            if not is_expanded:
                page.click("tr.fr[data-name='config_engine']")
            page.wait_for_timeout(300)
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"proof18_padding_{width}.png"))

            # For each rule row, verify the right edge of the rule ID cell
            # doesn't overlap with the left edge of the description cell
            gaps = page.evaluate("""() => {
                const detail = document.querySelector('tr.dr');
                if (!detail) return [];
                const rows = detail.querySelectorAll('tr');
                const results = [];
                for (const row of rows) {
                    const rid = row.querySelector('td.rid');
                    const rdesc = row.querySelector('td.rdesc');
                    if (!rid || !rdesc) continue;
                    const ridRect = rid.getBoundingClientRect();
                    const rdescRect = rdesc.getBoundingClientRect();
                    const gap = rdescRect.left - ridRect.right;
                    results.push({
                        id: rid.textContent.trim(),
                        gap: Math.round(gap),
                        ridPaddingRight: parseFloat(getComputedStyle(rid).paddingRight),
                    });
                }
                return results;
            }""")

            assert len(gaps) >= 3, f"Expected >=3 rule rows at {width}px, got {len(gaps)}"
            for g in gaps:
                assert g["ridPaddingRight"] >= 24, \
                    f"Rule '{g['id']}' padding-right is {g['ridPaddingRight']}px at {width}px viewport (need >=24)"
                assert g["gap"] >= 0, \
                    f"Rule '{g['id']}' overlaps description by {abs(g['gap'])}px at {width}px viewport"


class TestDashboardVisual:

    @pytest.mark.proof("dashboard_visual", "PROOF-1", "RULE-1")
    def test_dark_theme_backgrounds(self, page, dashboard):
        """PROOF-1: Dark theme body bg=#0f172a, card bg=#1e293b."""
        load_dashboard(page, dashboard, data=make_data())
        # Ensure dark theme is active (it is the default, but be explicit)
        page.evaluate('document.documentElement.setAttribute("data-theme", "dark")')
        page.wait_for_timeout(100)

        body_bg = page.evaluate(
            "() => getComputedStyle(document.body).backgroundColor"
        )
        assert rgb_to_hex(body_bg) == "#0f172a", (
            f"Expected dark body bg #0f172a, got {body_bg!r}"
        )

        card_bg = page.evaluate(
            "() => getComputedStyle(document.querySelector('.summary-card')).backgroundColor"
        )
        assert rgb_to_hex(card_bg) == "#1e293b", (
            f"Expected dark card bg #1e293b, got {card_bg!r}"
        )

    @pytest.mark.proof("dashboard_visual", "PROOF-2", "RULE-2")
    def test_light_theme_backgrounds(self, page, dashboard):
        """PROOF-2: Light theme body bg=#f1f5f9, card bg=#ffffff."""
        load_dashboard(page, dashboard, data=make_data())
        page.evaluate('document.documentElement.setAttribute("data-theme", "light")')
        # Wait for the 0.2s CSS transition on background to fully resolve
        page.wait_for_timeout(300)

        body_bg = page.evaluate(
            "() => getComputedStyle(document.body).backgroundColor"
        )
        assert rgb_to_hex(body_bg) == "#f1f5f9", (
            f"Expected light body bg #f1f5f9, got {body_bg!r}"
        )

        card_bg = page.evaluate(
            "() => getComputedStyle(document.querySelector('.summary-card')).backgroundColor"
        )
        assert rgb_to_hex(card_bg) == "#ffffff", (
            f"Expected light card bg #ffffff, got {card_bg!r}"
        )

    @pytest.mark.proof("dashboard_visual", "PROOF-3", "RULE-3")
    def test_status_colors_in_css(self):
        """PROOF-3: CSS defines --green #22c55e, --amber #f59e0b, --red #ef4444, --teal #2dd4bf."""
        with open(HTML_SRC, encoding="utf-8") as f:
            source = f.read()
        assert "--green: #22c55e" in source, "Expected --green: #22c55e in CSS"
        assert "--amber: #f59e0b" in source, "Expected --amber: #f59e0b in CSS"
        assert "--red: #ef4444" in source, "Expected --red: #ef4444 in CSS"
        assert "--teal: #2dd4bf" in source, "Expected --teal: #2dd4bf in CSS"

    @pytest.mark.proof("dashboard_visual", "PROOF-4", "RULE-4")
    def test_sans_serif_font_stack(self):
        """PROOF-4: Sans-serif font stack includes -apple-system and Roboto."""
        with open(HTML_SRC, encoding="utf-8") as f:
            source = f.read()
        assert "-apple-system" in source, "Expected -apple-system in font stack"
        assert "Roboto" in source, "Expected Roboto in font stack"

    @pytest.mark.proof("dashboard_visual", "PROOF-5", "RULE-5")
    def test_mono_font_stack(self):
        """PROOF-5: Monospace font stack includes 'SF Mono' and Consolas."""
        with open(HTML_SRC, encoding="utf-8") as f:
            source = f.read()
        assert "SF Mono" in source, "Expected 'SF Mono' in monospace font stack"
        assert "Consolas" in source, "Expected Consolas in monospace font stack"

    @pytest.mark.proof("dashboard_visual", "PROOF-6", "RULE-6")
    def test_ready_badge_style(self, page, dashboard):
        """PROOF-6: .sb-verified has solid green background and white text."""
        load_dashboard(page, dashboard, data=make_data())

        bg = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-verified')).backgroundColor"
        )
        assert rgb_to_hex(bg) == "#22c55e", (
            f"Expected .sb-verified background #22c55e (green), got {bg!r}"
        )

        color = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-verified')).color"
        )
        assert rgb_to_hex(color) == "#ffffff", (
            f"Expected .sb-verified text color #ffffff (white), got {color!r}"
        )

    @pytest.mark.proof("dashboard_visual", "PROOF-7", "RULE-7")
    def test_partial_badge_style(self, page, dashboard):
        """PROOF-7: .sb-partial has transparent background and amber border."""
        load_dashboard(page, dashboard, data=make_data())

        bg = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-partial')).backgroundColor"
        )
        # transparent resolves to rgba(0,0,0,0) in computed styles
        assert bg in ("rgba(0, 0, 0, 0)", "transparent"), (
            f"Expected .sb-partial background transparent, got {bg!r}"
        )

        border_color = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-partial')).borderColor"
        )
        assert rgb_to_hex(border_color) == "#f59e0b", (
            f"Expected .sb-partial border color #f59e0b (amber), got {border_color!r}"
        )

    @pytest.mark.proof("dashboard_visual", "PROOF-8", "RULE-8")
    def test_fail_badge_style(self, page, dashboard):
        """PROOF-8: .sb-fail has solid red background."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        data = make_data({
            "features": [make_fail_feature("broken_feature")],
            "summary": {"total_features": 1, "verified": 0, "partial": 0, "failing": 1, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
            "audit_summary": {
                "integrity": None, "strong": 0, "weak": 0, "hollow": 0, "manual": 0,
                "behavioral_total": 0, "last_audit": None, "last_audit_relative": None, "stale": False,
            },
        })
        load_dashboard(page, dashboard, data=data)

        bg = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-failing')).backgroundColor"
        )
        assert rgb_to_hex(bg) == "#ef4444", (
            f"Expected .sb-failing background #ef4444 (red), got {bg!r}"
        )

    @pytest.mark.proof("dashboard_visual", "PROOF-9", "RULE-9")
    def test_untested_badge_and_no_proofs_opacity(self, page, dashboard):
        """PROOF-9: UNTESTED badge is gray pill with amber text (.sb-untested);
        generic .sb-none has reduced opacity."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        features = [
            {
                "name": "untested_feature",
                "category": "test",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 0,
                "total": 1,
                "deferred": 0,
                "status": "UNTESTED",
                "vhash": None,
                "receipt": None,
                "rules": [],
                "audit": None,
            },
            {
                "name": "unknown_status_feature",
                "category": "test",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 0,
                "total": 1,
                "deferred": 0,
                "status": "some_unknown",
                "vhash": None,
                "receipt": None,
                "rules": [],
                "audit": None,
            },
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 2, "verified": 0, "partial": 0, "failing": 0, "untested": 2},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
            "audit_summary": {
                "integrity": None, "strong": 0, "weak": 0, "hollow": 0, "manual": 0,
                "behavioral_total": 0, "last_audit": None, "last_audit_relative": None, "stale": False,
            },
        })
        load_dashboard(page, dashboard, data=data)

        # Verify UNTESTED badge has .sb-untested class with amber text
        untested_badge = page.query_selector(".sb-untested")
        assert untested_badge is not None, "Expected .sb-untested badge for UNTESTED feature"
        untested_color = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-untested')).color"
        )
        # Amber is #f59e0b = rgb(245, 158, 11)
        assert "245" in untested_color and "158" in untested_color, (
            f"Expected .sb-untested to have amber text color, got {untested_color!r}"
        )

        # Verify generic .sb-none (unknown status) has reduced opacity
        none_badge = page.query_selector(".sb-none")
        assert none_badge is not None, "Expected .sb-none badge for unknown status"
        opacity = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-none')).opacity"
        )
        assert float(opacity) < 1.0, (
            f"Expected .sb-none opacity < 1.0 (reduced), got {opacity!r}"
        )

    @pytest.mark.proof("dashboard_visual", "PROOF-10", "RULE-10")
    def test_integrity_color_coding(self, page, dashboard):
        """PROOF-10: Integrity color coding: green at 90%, amber at 60%, red at 30%."""
        features = [
            make_integrity_feature("high_integrity", 90),
            make_integrity_feature("mid_integrity", 60),
            make_integrity_feature("low_integrity", 30),
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 3, "verified": 3, "partial": 0, "failing": 0, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
            "audit_summary": {
                "integrity": 60, "strong": 3, "weak": 0, "hollow": 0, "manual": 0,
                "behavioral_total": 3, "last_audit": None, "last_audit_relative": None, "stale": False,
            },
        })
        load_dashboard(page, dashboard, data=data)

        # Integrity cells are rendered with intClass(): int-hi, int-mid, int-lo
        int_cells = page.query_selector_all("td.int")
        assert len(int_cells) >= 3, f"Expected at least 3 integrity cells, got {len(int_cells)}"

        classes_list = [cell.get_attribute("class") for cell in int_cells]
        assert any("int-hi" in c for c in classes_list), (
            f"Expected an int-hi cell for 90% integrity, got classes: {classes_list}"
        )
        assert any("int-mid" in c for c in classes_list), (
            f"Expected an int-mid cell for 60% integrity, got classes: {classes_list}"
        )
        assert any("int-lo" in c for c in classes_list), (
            f"Expected an int-lo cell for 30% integrity, got classes: {classes_list}"
        )

    @pytest.mark.proof("dashboard_visual", "PROOF-11", "RULE-11")
    def test_no_hardcoded_hex_outside_custom_properties(self):
        """PROOF-11: No hardcoded hex colors appear outside CSS custom property definitions."""
        import re
        with open(HTML_SRC, encoding="utf-8") as f:
            source = f.read()

        # Extract only the <style>...</style> block
        style_match = re.search(r'<style>(.*?)</style>', source, re.DOTALL)
        assert style_match, "Expected a <style> block in the HTML"
        css = style_match.group(1)

        hex_pattern = re.compile(r'#[0-9a-fA-F]{3,8}\b')
        # Pure white (#fff, #ffffff) and pure black (#000, #000000) are universal
        # constants that don't require theming — exempt them from this check.
        universal_constants = {"#fff", "#ffffff", "#000", "#000000"}
        violations = []
        for line in css.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Skip lines that define CSS custom properties (--name: value)
            if re.search(r'--[\w-]+\s*:', stripped):
                continue
            # Find any hex color literals on non-custom-property lines
            for match in hex_pattern.finditer(stripped):
                hex_val = match.group(0).lower()
                if hex_val in universal_constants:
                    continue
                violations.append(f"Line: {stripped!r}  ->  {hex_val}")

        assert len(violations) == 0, (
            f"Found {len(violations)} hardcoded hex color(s) outside CSS custom property definitions:\n"
            + "\n".join(violations[:20])
        )

    @pytest.mark.proof("purlin_report", "PROOF-18", "RULE-18")
    def test_coverage_bar_width_matches_fraction(self, page, dashboard):
        """PROOF-18: Coverage bar fill width matches proved/total fraction."""
        features = [
            {
                "name": "low_coverage",
                "category": "test",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 2,
                "total": 6,
                "deferred": 0,
                "status": "PARTIAL",

                "vhash": None,
                "receipt": None,
                "rules": [],
                "audit": None,
            },
            {
                "name": "full_coverage",
                "category": "test",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 5,
                "total": 5,
                "deferred": 0,
                "status": "PASSING",

                "vhash": "abcd1234",
                "receipt": None,
                "rules": [],
                "audit": None,
            },
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 2, "verified": 0, "passing": 1,
                        "partial": 1, "failing": 0, "untested": 0},
        })
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof18_coverage_bars.png"))

        # Measure fill width as percentage of bar width via JS
        bar_widths = page.evaluate("""() => {
            const rows = document.querySelectorAll('tr.fr');
            const results = {};
            rows.forEach(row => {
                const name = row.getAttribute('data-name');
                const bar = row.querySelector('.cov-bar');
                const fill = row.querySelector('.cov-fill');
                if (bar && fill) {
                    const barW = bar.getBoundingClientRect().width;
                    const fillW = fill.getBoundingClientRect().width;
                    results[name] = Math.round(fillW / barW * 100);
                }
            });
            return results;
        }""")

        # 2/6 = 33%
        assert 30 <= bar_widths.get('low_coverage', 0) <= 37, (
            f"Expected low_coverage bar ~33%, got {bar_widths.get('low_coverage')}%"
        )
        # 5/5 = 100%
        assert bar_widths.get('full_coverage', 0) == 100, (
            f"Expected full_coverage bar 100%, got {bar_widths.get('full_coverage')}%"
        )


# ---------------------------------------------------------------------------
# TestCategorySections — foldable category grouping
# ---------------------------------------------------------------------------

def make_categorized_data():
    """Generate PURLIN_DATA with features across multiple categories."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def feat(name, category, status, proved, total, vhash=None, receipt=None):
        return {
            "name": name,
            "category": category,
            "type": "anchor" if category == "_anchors" else "feature",
            "is_global": False,
            "source_url": None,
            "proved": proved,
            "total": total,
            "deferred": 0,
            "status": status,

            "vhash": vhash,
            "receipt": receipt,
            "rules": [],
            "audit": None,
        }

    features = [
        feat("skill_build", "skills", "VERIFIED", 7, 7,
             vhash="abc1", receipt={"commit": "x", "timestamp": now, "stale": False}),
        feat("skill_audit", "skills", "PASSING", 3, 3, vhash="abc2"),
        feat("config_engine", "mcp", "PARTIAL", 11, 15),
        feat("drift", "mcp", "VERIFIED", 23, 23,
             vhash="abc3", receipt={"commit": "y", "timestamp": now, "stale": False}),
        feat("transport", "mcp", "UNTESTED", 0, 4),
        feat("dashboard_visual", "_anchors", "PASSING", 11, 11, vhash="abc4"),
    ]
    return {
        "timestamp": now,
        "project": "test-project",
        "version": "0.9.0",
        "docs_url": None,
        "summary": {
            "total_features": 5,
            "verified": 2,
            "passing": 1,
            "partial": 1,
            "failing": 0,
            "untested": 1,
        },
        "features": features,
        "anchors_summary": {"total": 1, "with_source": 0, "global": 0},
        "audit_summary": None,
        "drift": None,
    }


class TestCategorySections:

    @pytest.mark.proof("purlin_report", "PROOF-19", "RULE-19")
    def test_category_headers_with_rolled_up_summaries(self, page, dashboard):
        """PROOF-19: Category headers show correct rolled-up counts and breakdowns;
        categories with untested features show amber coverage bar."""
        data = make_categorized_data()
        load_dashboard(page, dashboard, data=data, expand_categories=False)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof19_categories_collapsed.png"))

        # Verify 3 category header rows exist
        cat_headers = page.query_selector_all(".cat-header")
        assert len(cat_headers) == 3, (
            f"Expected 3 category headers, got {len(cat_headers)}"
        )

        # Extract category data
        cat_data = page.evaluate("""() => {
            const headers = document.querySelectorAll('.cat-header');
            return Array.from(headers).map(h => ({
                cat: h.getAttribute('data-cat'),
                label: h.querySelector('.cat-label')?.textContent,
                count: h.querySelector('.cat-count')?.textContent,
                cov: h.querySelector('.cat-cov')?.textContent?.trim(),
                summary: h.querySelector('.cat-summary')?.textContent?.trim(),
                barClass: h.querySelector('.cat-cov-fill')?.className || '',
            }));
        }""")

        # Verify skills category: 2 features, 10/10 coverage, green bar
        skills = next(c for c in cat_data if c["cat"] == "skills")
        assert skills["count"] == "(2)", f"Skills count: {skills['count']}"
        assert "10/10" in skills["cov"], f"Skills coverage: {skills['cov']}"
        assert "verified" in skills["summary"].lower()
        assert "passing" in skills["summary"].lower()
        assert "cov-verified" in skills["barClass"], (
            f"Expected skills bar green (cov-verified), got {skills['barClass']}"
        )

        # Verify mcp category: 3 features (1 PARTIAL + 1 VERIFIED + 1 UNTESTED),
        # 34/42 coverage, amber bar (untested makes it incomplete)
        mcp = next(c for c in cat_data if c["cat"] == "mcp")
        assert mcp["count"] == "(3)", f"MCP count: {mcp['count']}"
        assert "34/42" in mcp["cov"], f"MCP coverage: {mcp['cov']}"
        assert "partial" in mcp["summary"].lower()
        assert "untested" in mcp["summary"].lower()
        assert "cov-partial" in mcp["barClass"], (
            f"Expected mcp bar amber (cov-partial) due to untested feature, got {mcp['barClass']}"
        )

        # Verify _anchors category: 1 feature, 11/11, green bar
        anchors = next(c for c in cat_data if c["cat"] == "_anchors")
        assert anchors["count"] == "(1)", f"Anchors count: {anchors['count']}"
        assert "11/11" in anchors["cov"], f"Anchors coverage: {anchors['cov']}"
        assert anchors["label"] == "anchors", (
            f"Expected _anchors displayed as 'anchors', got '{anchors['label']}'"
        )

        # Verify category coverage bar fills are visible (have a background color)
        bar_fills = page.evaluate("""() => {
            const fills = document.querySelectorAll('.cat-cov-fill');
            return Array.from(fills).map(el => ({
                width: el.style.width,
                bg: getComputedStyle(el).backgroundColor
            }));
        }""")
        for fill in bar_fills:
            assert fill["bg"] != "rgba(0, 0, 0, 0)", (
                f"Category coverage bar fill has no background color (width={fill['width']})"
            )

        # Verify specific bar widths match expected percentages
        cat_bar_widths = page.evaluate("""() => {
            const headers = document.querySelectorAll('.cat-header');
            const results = {};
            headers.forEach(h => {
                const cat = h.getAttribute('data-cat');
                const bar = h.querySelector('.cat-cov-bar');
                const fill = h.querySelector('.cat-cov-fill');
                if (bar && fill) {
                    const barW = bar.getBoundingClientRect().width;
                    const fillW = fill.getBoundingClientRect().width;
                    results[cat] = barW > 0 ? Math.round(fillW / barW * 100) : 0;
                }
            });
            return results;
        }""")
        # skills: 10/10 = 100%
        assert cat_bar_widths.get("skills", 0) == 100, (
            f"Expected skills bar 100%, got {cat_bar_widths.get('skills')}%"
        )
        # mcp: 34/42 = 81%
        assert 78 <= cat_bar_widths.get("mcp", 0) <= 84, (
            f"Expected mcp bar ~81%, got {cat_bar_widths.get('mcp')}%"
        )

        # Expand all categories (re-query after each click since render rebuilds DOM)
        for i in range(3):
            headers = page.query_selector_all(".cat-header:not(.expanded)")
            if not headers:
                break
            headers[0].click()
            page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof19_categories_expanded.png"))

    @pytest.mark.proof("purlin_report", "PROOF-20", "RULE-20")
    def test_categories_collapsed_by_default(self, page, dashboard):
        """PROOF-20: Categories start collapsed — no feature rows visible initially."""
        data = make_categorized_data()
        load_dashboard(page, dashboard, data=data, expand_categories=False)

        # No feature rows should be visible
        fr_count = page.evaluate("() => document.querySelectorAll('tr.fr').length")
        assert fr_count == 0, (
            f"Expected 0 feature rows when categories collapsed, got {fr_count}"
        )

        # Category headers should exist
        cat_count = page.evaluate("() => document.querySelectorAll('.cat-header').length")
        assert cat_count == 3, f"Expected 3 category headers, got {cat_count}"

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof20_collapsed.png"))

        # Click the first category header to expand it
        page.click(".cat-header")
        page.wait_for_timeout(300)

        # Now some feature rows should be visible
        fr_after = page.evaluate("() => document.querySelectorAll('tr.fr').length")
        assert fr_after > 0, "Expected feature rows after expanding a category"

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof20_one_expanded.png"))

    @pytest.mark.proof("purlin_report", "PROOF-21", "RULE-21")
    def test_category_state_persists_across_reloads(self, page, dashboard):
        """PROOF-21: Category open/closed state persists to localStorage and survives reload."""
        data = make_categorized_data()
        load_dashboard(page, dashboard, data=data, expand_categories=False)

        # All collapsed initially
        fr_before = page.evaluate("() => document.querySelectorAll('tr.fr').length")
        assert fr_before == 0, "Expected all categories collapsed initially"

        # Click the skills category to expand it
        page.click(".cat-header[data-cat='skills']")
        page.wait_for_timeout(300)

        # Verify skills features are visible
        skills_rows = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='skill_build'], tr.fr[data-name='skill_audit']").length
        """)
        assert skills_rows == 2, f"Expected 2 skills features after expand, got {skills_rows}"

        # Verify localStorage was updated
        stored = page.evaluate(
            "() => JSON.parse(localStorage.getItem('purlin-categories') || '{}')"
        )
        assert stored.get("skills") is True, (
            f"Expected skills=true in localStorage, got {stored}"
        )

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof21_before_reload.png"))

        # Reload the page
        page.reload()
        page.wait_for_load_state("networkidle")

        # Skills should still be expanded after reload
        skills_after = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='skill_build'], tr.fr[data-name='skill_audit']").length
        """)
        assert skills_after == 2, (
            f"Expected skills still expanded after reload, got {skills_after} rows"
        )

        # Other categories should still be collapsed
        mcp_rows = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='config_engine'], tr.fr[data-name='drift']").length
        """)
        assert mcp_rows == 0, (
            f"Expected mcp category still collapsed after reload, got {mcp_rows} rows"
        )

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof21_after_reload.png"))

        # Collapse skills, reload, verify collapsed
        page.click(".cat-header[data-cat='skills']")
        page.wait_for_timeout(300)
        page.reload()
        page.wait_for_load_state("networkidle")

        skills_final = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='skill_build'], tr.fr[data-name='skill_audit']").length
        """)
        assert skills_final == 0, (
            f"Expected skills collapsed after toggle+reload, got {skills_final} rows"
        )


# ---------------------------------------------------------------------------
# TestAuditTagVisibility — audit tags gated on audit_summary
# ---------------------------------------------------------------------------

def make_audit_data(audit_summary=None):
    """Generate data with per-feature audit info and proof-level audit tags."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "timestamp": now,
        "project": "test-project",
        "version": "0.9.0",
        "docs_url": None,
        "summary": {"total_features": 1, "verified": 1, "partial": 0, "failing": 0, "untested": 0},
        "features": [{
            "name": "auth_login",
            "category": "auth",
            "type": "feature",
            "is_global": False,
            "source_url": None,
            "proved": 2,
            "total": 2,
            "deferred": 0,
            "status": "VERIFIED",

            "vhash": "a1b2c3d4",
            "receipt": {"commit": "abc", "timestamp": now, "stale": False},
            "rules": [
                {
                    "id": "RULE-1", "description": "Validates credentials",
                    "label": "own", "source": None, "is_deferred": False,
                    "is_assumed": False, "status": "PASS",
                    "proofs": [{
                        "id": "PROOF-1", "description": "POST valid creds",
                        "test_file": "tests/test.py", "test_name": "test_valid",
                        "tier": "unit", "status": "pass", "audit": "STRONG",
                    }],
                },
                {
                    "id": "RULE-2", "description": "Returns 401 on bad creds",
                    "label": "own", "source": None, "is_deferred": False,
                    "is_assumed": False, "status": "PASS",
                    "proofs": [{
                        "id": "PROOF-2", "description": "POST bad creds",
                        "test_file": "tests/test.py", "test_name": "test_bad",
                        "tier": "unit", "status": "pass", "audit": "HOLLOW",
                    }],
                },
            ],
            "audit": {
                "integrity": 50, "strong": 1, "weak": 0, "hollow": 1, "manual": 0,
                "findings": [],
            },
        }],
        "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
        "audit_summary": audit_summary,
        "drift": None,
    }


class TestAuditTagVisibility:

    @pytest.mark.proof("purlin_report", "PROOF-22", "RULE-22")
    def test_audit_tags_visible_with_audit_data_hidden_without(self, page, dashboard):
        """PROOF-22: Audit tags on proofs only render when audit_summary has data."""
        # Case 1: audit_summary has integrity — tags should appear
        data_with_audit = make_audit_data(audit_summary={
            "integrity": 85, "strong": 4, "weak": 1, "hollow": 1, "manual": 0,
            "behavioral_total": 6, "last_audit": datetime.datetime.now(
                datetime.timezone.utc).isoformat(),
            "last_audit_relative": "just now", "stale": False,
        })
        load_dashboard(page, dashboard, data=data_with_audit)

        # Expand the feature to see proofs
        page.click("tr.fr[data-name='auth_login']")
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof22_with_audit.png"))

        tags_with = page.query_selector_all(".atag")
        assert len(tags_with) >= 2, (
            f"Expected at least 2 audit tags (.atag) when audit_summary has data, "
            f"got {len(tags_with)}"
        )

        # Verify one is STRONG and one is HOLLOW
        tag_texts = page.evaluate("""() =>
            Array.from(document.querySelectorAll('.atag')).map(el => el.textContent.trim())
        """)
        assert "Strong" in tag_texts, f"Expected a 'Strong' tag, got {tag_texts}"
        assert "Hollow" in tag_texts, f"Expected a 'Hollow' tag, got {tag_texts}"

        # Case 2: audit_summary is null — tags must NOT appear
        data_no_audit = make_audit_data(audit_summary=None)
        load_dashboard(page, dashboard, data=data_no_audit)

        # Expand the feature
        page.click("tr.fr[data-name='auth_login']")
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof22_no_audit.png"))

        tags_without = page.query_selector_all(".atag")
        assert len(tags_without) == 0, (
            f"Expected 0 audit tags when audit_summary is null, "
            f"got {len(tags_without)}: {page.evaluate('''() => Array.from(document.querySelectorAll('.atag')).map(e => e.textContent)''')}"
        )


# ---------------------------------------------------------------------------
# TestActionBanners — status-colored action banners in expanded detail
# ---------------------------------------------------------------------------

def make_action_banner_data():
    """Generate data with features in all five statuses for action banner testing."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "timestamp": now,
        "project": "test-project",
        "version": "0.9.0",
        "docs_url": None,
        "summary": {
            "total_features": 5, "verified": 1, "passing": 1,
            "partial": 1, "failing": 1, "untested": 1,
        },
        "features": [
            {
                "name": "feat_partial",
                "category": "test",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 1,
                "total": 3,
                "deferred": 0,
                "status": "PARTIAL",

                "vhash": None,
                "receipt": None,
                "rules": [
                    {
                        "id": "RULE-1", "description": "Does thing A",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "PASS",
                        "proofs": [{"id": "PROOF-1", "description": "Test A",
                                    "test_file": "t.py", "test_name": "test_a",
                                    "tier": "unit", "status": "pass"}],
                    },
                    {
                        "id": "RULE-2", "description": "Does thing B",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "NO_PROOF", "proofs": [],
                    },
                    {
                        "id": "RULE-3", "description": "Does thing C",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "NO_PROOF", "proofs": [],
                    },
                ],
                "audit": None,
            },
            {
                "name": "feat_failing",
                "category": "test",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 0,
                "total": 2,
                "deferred": 0,
                "status": "FAILING",

                "vhash": None,
                "receipt": None,
                "rules": [
                    {
                        "id": "RULE-1", "description": "Returns 200",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "FAIL",
                        "proofs": [{"id": "PROOF-1", "description": "Test 200",
                                    "test_file": "t.py", "test_name": "test_ok",
                                    "tier": "unit", "status": "fail"}],
                    },
                    {
                        "id": "RULE-2", "description": "Logs request",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "PASS",
                        "proofs": [{"id": "PROOF-2", "description": "Test log",
                                    "test_file": "t.py", "test_name": "test_log",
                                    "tier": "unit", "status": "pass"}],
                    },
                ],
                "audit": None,
            },
            {
                "name": "feat_passing",
                "category": "test",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 2,
                "total": 2,
                "deferred": 0,
                "status": "PASSING",

                "vhash": "abcd1234",
                "receipt": None,
                "rules": [
                    {
                        "id": "RULE-1", "description": "Works",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "PASS",
                        "proofs": [{"id": "PROOF-1", "description": "Test works",
                                    "test_file": "t.py", "test_name": "test_w",
                                    "tier": "unit", "status": "pass"}],
                    },
                    {
                        "id": "RULE-2", "description": "Also works",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "PASS",
                        "proofs": [{"id": "PROOF-2", "description": "Test also",
                                    "test_file": "t.py", "test_name": "test_a",
                                    "tier": "unit", "status": "pass"}],
                    },
                ],
                "audit": None,
            },
            {
                "name": "feat_untested",
                "category": "test",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 0,
                "total": 1,
                "deferred": 0,
                "status": "UNTESTED",

                "vhash": None,
                "receipt": None,
                "rules": [
                    {
                        "id": "RULE-1", "description": "Something",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "NO_PROOF", "proofs": [],
                    },
                ],
                "audit": None,
            },
            {
                "name": "feat_verified",
                "category": "test",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 1,
                "total": 1,
                "deferred": 0,
                "status": "VERIFIED",

                "vhash": "ef567890",
                "receipt": {"commit": "abc", "timestamp": now, "stale": False},
                "rules": [
                    {
                        "id": "RULE-1", "description": "Verified thing",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "PASS",
                        "proofs": [{"id": "PROOF-1", "description": "Test verified",
                                    "test_file": "t.py", "test_name": "test_v",
                                    "tier": "unit", "status": "pass"}],
                    },
                ],
                "audit": None,
            },
        ],
        "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
        "audit_summary": None,
        "drift": None,
    }


class TestActionBanners:

    @pytest.mark.proof("purlin_report", "PROOF-23", "RULE-23")
    def test_action_banners_per_status(self, page, dashboard):
        """PROOF-23: Each status shows the correct action banner with guidance text."""
        data = make_action_banner_data()
        load_dashboard(page, dashboard, data=data)

        # --- PARTIAL: should say "2 rules need proofs" ---
        page.click("tr.fr[data-name='feat_partial']")
        page.wait_for_timeout(300)
        banner = page.query_selector("tr.dr .ab-partial")
        assert banner, "Expected .ab-partial banner for PARTIAL feature"
        text = banner.inner_text()
        assert "2 rules need proofs" in text, (
            f"PARTIAL banner should mention '2 rules need proofs', got: {text}"
        )
        assert "PASSING" in text, (
            f"PARTIAL banner should mention reaching PASSING, got: {text}"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof23_partial.png"))

        # Collapse and re-render for next feature
        page.click("tr.fr[data-name='feat_partial']")
        page.wait_for_timeout(200)

        # --- FAILING: should say "1 test failing" ---
        page.click("tr.fr[data-name='feat_failing']")
        page.wait_for_timeout(300)
        banner = page.query_selector("tr.dr .ab-failing")
        assert banner, "Expected .ab-failing banner for FAILING feature"
        text = banner.inner_text()
        assert "1 test" in text and "failing" in text, (
            f"FAILING banner should mention '1 test failing', got: {text}"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof23_failing.png"))

        page.click("tr.fr[data-name='feat_failing']")
        page.wait_for_timeout(200)

        # --- PASSING: should mention purlin:verify ---
        page.click("tr.fr[data-name='feat_passing']")
        page.wait_for_timeout(300)
        banner = page.query_selector("tr.dr .ab-passing")
        assert banner, "Expected .ab-passing banner for PASSING feature"
        text = banner.inner_text()
        assert "purlin:verify" in text, (
            f"PASSING banner should mention 'purlin:verify', got: {text}"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof23_passing.png"))

        page.click("tr.fr[data-name='feat_passing']")
        page.wait_for_timeout(200)

        # --- UNTESTED: should say "write tests" ---
        page.click("tr.fr[data-name='feat_untested']")
        page.wait_for_timeout(300)
        banner = page.query_selector("tr.dr .ab-untested")
        assert banner, "Expected .ab-untested banner for UNTESTED feature"
        text = banner.inner_text()
        assert "write tests" in text.lower(), (
            f"UNTESTED banner should mention 'write tests', got: {text}"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof23_untested.png"))

        page.click("tr.fr[data-name='feat_untested']")
        page.wait_for_timeout(200)

        # --- VERIFIED: should have NO banner ---
        page.click("tr.fr[data-name='feat_verified']")
        page.wait_for_timeout(300)
        banner = page.query_selector("tr.dr .ab")
        assert banner is None, (
            "VERIFIED feature should have no action banner (.ab element)"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof23_verified.png"))


class TestRuleRowHighlights:

    @pytest.mark.proof("purlin_report", "PROOF-24", "RULE-24")
    def test_no_proof_rules_have_amber_border(self, page, dashboard):
        """PROOF-24: NO_PROOF rules have class rule-np and amber left border."""
        data = make_action_banner_data()
        load_dashboard(page, dashboard, data=data)

        # Expand the PARTIAL feature (has 2 NO_PROOF rules)
        page.click("tr.fr[data-name='feat_partial']")
        page.wait_for_timeout(300)

        np_rows = page.query_selector_all("tr.rule-np")
        assert len(np_rows) == 2, (
            f"Expected 2 rule-np rows for PARTIAL feature, got {len(np_rows)}"
        )

        # Verify amber border on the first td
        border_color = page.evaluate("""() => {
            var row = document.querySelector('tr.rule-np');
            var td = row.querySelector('td');
            return getComputedStyle(td).borderLeftColor;
        }""")
        hex_color = rgb_to_hex(border_color)
        assert hex_color == "#f59e0b", (
            f"Expected amber (#f59e0b) border-left on NO_PROOF rule td, got {hex_color}"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof24_no_proof_border.png"))

    @pytest.mark.proof("purlin_report", "PROOF-25", "RULE-25")
    def test_fail_rules_have_red_border(self, page, dashboard):
        """PROOF-25: FAIL rules have class rule-fail and red left border."""
        data = make_action_banner_data()
        load_dashboard(page, dashboard, data=data)

        # Expand the FAILING feature (has 1 FAIL rule)
        page.click("tr.fr[data-name='feat_failing']")
        page.wait_for_timeout(300)

        fail_rows = page.query_selector_all("tr.rule-fail")
        assert len(fail_rows) == 1, (
            f"Expected 1 rule-fail row for FAILING feature, got {len(fail_rows)}"
        )

        # Verify red border on the first td
        border_color = page.evaluate("""() => {
            var row = document.querySelector('tr.rule-fail');
            var td = row.querySelector('td');
            return getComputedStyle(td).borderLeftColor;
        }""")
        hex_color = rgb_to_hex(border_color)
        assert hex_color == "#ef4444", (
            f"Expected red (#ef4444) border-left on FAIL rule td, got {hex_color}"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof25_fail_border.png"))


class TestExternalReferenceBlock:

    @pytest.mark.proof("purlin_report", "PROOF-26", "RULE-26")
    def test_external_reference_block(self, page, dashboard):
        """PROOF-26: Expanded anchor with source_url shows External Reference block
        with Source link, Path, and Pinned (truncated); unpinned shows amber."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        features = [
            {
                "name": "pinned_anchor",
                "category": "_anchors",
                "type": "anchor",
                "is_global": False,
                "source_url": "git@github.com:acme/api-spec.git",
                "pinned": "abc1234def5678901234567890abcdef12345678",
                "source_path": "docs/contract.md",
                "proved": 2,
                "total": 2,
                "deferred": 0,
                "status": "PASSING",
                "vhash": "aabb1122",
                "receipt": None,
                "rules": [
                    {"id": "RULE-1", "description": "All responses include Content-Type",
                     "label": "own", "source": None, "is_deferred": False,
                     "is_assumed": False, "status": "PASS", "proofs": []},
                ],
                "audit": None,
            },
            {
                "name": "unpinned_anchor",
                "category": "_anchors",
                "type": "anchor",
                "is_global": False,
                "source_url": "git@github.com:acme/loose.git",
                "pinned": None,
                "source_path": None,
                "proved": 0,
                "total": 1,
                "deferred": 0,
                "status": "UNTESTED",
                "vhash": None,
                "receipt": None,
                "rules": [
                    {"id": "RULE-1", "description": "Some constraint",
                     "label": "own", "source": None, "is_deferred": False,
                     "is_assumed": False, "status": "NO_PROOF", "proofs": []},
                ],
                "audit": None,
            },
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 0, "verified": 0, "passing": 1,
                        "partial": 0, "failing": 0, "untested": 1},
            "anchors_summary": {"total": 2, "with_source": 2, "global": 0},
        })
        load_dashboard(page, dashboard, data=data)

        # Expand pinned anchor
        page.click("tr.fr[data-name='pinned_anchor']")
        page.wait_for_timeout(300)

        # Verify .ext-ref-block exists
        block = page.query_selector(".ext-ref-block")
        assert block is not None, "Expected .ext-ref-block for anchor with source_url"

        # Verify Source link
        source_link = page.evaluate("""() => {
            var block = document.querySelector('.ext-ref-block');
            var link = block ? block.querySelector('a') : null;
            return link ? link.href : null;
        }""")
        assert source_link and "acme/api-spec" in source_link, (
            f"Expected Source link containing acme/api-spec, got {source_link}"
        )

        # Verify Path in code element
        path_code = page.evaluate("""() => {
            var block = document.querySelector('.ext-ref-block');
            var codes = block ? block.querySelectorAll('code') : [];
            for (var c of codes) {
                if (c.textContent.includes('contract.md')) return c.textContent;
            }
            return null;
        }""")
        assert path_code and "contract.md" in path_code, (
            f"Expected Path code containing contract.md, got {path_code}"
        )

        # Verify Pinned truncated to 7 chars
        pinned_code = page.evaluate("""() => {
            var block = document.querySelector('.ext-ref-block');
            var codes = block ? block.querySelectorAll('code') : [];
            for (var c of codes) {
                if (c.textContent.match(/^[a-f0-9]{7}$/)) return c.textContent;
            }
            return null;
        }""")
        assert pinned_code == "abc1234", (
            f"Expected pinned 'abc1234' (7 chars), got {pinned_code}"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof26_ext_ref_pinned.png"))

        # Now expand unpinned anchor — verify amber Unpinned text
        page.click("tr.fr[data-name='pinned_anchor']")  # collapse
        page.wait_for_timeout(200)
        page.click("tr.fr[data-name='unpinned_anchor']")
        page.wait_for_timeout(300)

        unpinned_text = page.evaluate("""() => {
            var warns = document.querySelectorAll('.ext-ref-warn');
            for (var w of warns) {
                if (w.textContent.includes('Unpinned')) return w.textContent;
            }
            return null;
        }""")
        assert unpinned_text and "Unpinned" in unpinned_text, (
            f"Expected 'Unpinned' in amber, got {unpinned_text}"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof26_ext_ref_unpinned.png"))

    @pytest.mark.proof("purlin_report", "PROOF-27", "RULE-27")
    def test_ext_icon_tooltip_includes_pinned(self, page, dashboard):
        """PROOF-27: ext-icon tooltip includes Source, Path, and Pinned."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        features = [
            {
                "name": "tooltip_anchor",
                "category": "_anchors",
                "type": "anchor",
                "is_global": False,
                "source_url": "git@github.com:acme/policies.git",
                "pinned": "deadbeef12345678",
                "source_path": "security/policy.md",
                "proved": 1,
                "total": 1,
                "deferred": 0,
                "status": "PASSING",
                "vhash": "1234abcd",
                "receipt": None,
                "rules": [],
                "audit": None,
            },
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 0, "verified": 0, "passing": 0,
                        "partial": 0, "failing": 0, "untested": 0},
            "anchors_summary": {"total": 1, "with_source": 1, "global": 0},
        })
        load_dashboard(page, dashboard, data=data)

        title = page.evaluate("""() => {
            var icon = document.querySelector('.ext-icon');
            return icon ? icon.getAttribute('title') : null;
        }""")
        assert title is not None, "Expected .ext-icon with title attribute"
        assert "acme/policies" in title, f"Expected source URL in tooltip, got {title}"
        assert "security/policy.md" in title, f"Expected path in tooltip, got {title}"
        assert "deadbee" in title, f"Expected pinned SHA in tooltip, got {title}"

    @pytest.mark.proof("purlin_report", "PROOF-28", "RULE-28")
    def test_stale_badge_on_stale_anchor(self, page, dashboard):
        """PROOF-28: Stale anchor shows amber STALE badge; current anchor does not."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        features = [
            {
                "name": "stale_anchor",
                "category": "_anchors",
                "type": "anchor",
                "is_global": False,
                "source_url": "git@github.com:acme/stale.git",
                "pinned": "oldsha1234567",
                "source_path": "spec.md",
                "ext_status": "stale",
                "proved": 1, "total": 1, "deferred": 0,
                "status": "PASSING",
                "vhash": "aabb", "receipt": None, "rules": [], "audit": None,
            },
            {
                "name": "current_anchor",
                "category": "_anchors",
                "type": "anchor",
                "is_global": False,
                "source_url": "git@github.com:acme/current.git",
                "pinned": "currentsha789",
                "source_path": "spec.md",
                "ext_status": "current",
                "proved": 1, "total": 1, "deferred": 0,
                "status": "PASSING",
                "vhash": "ccdd", "receipt": None, "rules": [], "audit": None,
            },
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 0, "verified": 0, "passing": 0,
                        "partial": 0, "failing": 0, "untested": 0},
            "anchors_summary": {"total": 2, "with_source": 2, "global": 0},
        })
        load_dashboard(page, dashboard, data=data)

        # Stale anchor should have .ext-stale badge
        stale_badge = page.evaluate("""() => {
            var row = document.querySelector('tr.fr[data-name="stale_anchor"]');
            var badge = row ? row.querySelector('.ext-stale') : null;
            return badge ? { text: badge.textContent, title: badge.getAttribute('title') } : null;
        }""")
        assert stale_badge is not None, "Expected .ext-stale badge on stale anchor"
        assert "STALE" in stale_badge["text"].upper(), f"Expected 'STALE' text, got {stale_badge['text']}"
        assert "sync" in stale_badge["title"].lower(), f"Expected sync in tooltip, got {stale_badge['title']}"

        # Current anchor should NOT have .ext-stale badge
        current_badge = page.evaluate("""() => {
            var row = document.querySelector('tr.fr[data-name="current_anchor"]');
            return row ? row.querySelector('.ext-stale') : 'no_row';
        }""")
        assert current_badge is None, f"Expected no .ext-stale on current anchor, got {current_badge}"
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof28_stale_badge.png"))


class TestUncommittedWork:

    @pytest.mark.proof("purlin_report", "PROOF-29", "RULE-29")
    def test_uncommitted_section(self, page, dashboard):
        """PROOF-29: Uncommitted section shows count collapsed, files expanded; hidden when empty."""
        # With uncommitted files
        data = make_data({
            "uncommitted": ["M specs/auth/login.md", "?? dev/scratch.py", "M scripts/server.py"],
        })
        load_dashboard(page, dashboard, data=data)

        # Verify section exists with count
        uw_section = page.query_selector(".uw-section")
        assert uw_section is not None, "Expected .uw-section when uncommitted files exist"

        count_text = page.inner_text(".uw-count")
        assert "3" in count_text, f"Expected count '3', got {count_text}"

        # Files should be hidden initially
        files_visible = page.evaluate("""() => {
            var el = document.getElementById('uw-files');
            return el ? getComputedStyle(el).display !== 'none' : false;
        }""")
        assert not files_visible, "Expected files hidden when collapsed"

        # Click to expand
        page.click("#uw-toggle")
        page.wait_for_timeout(200)

        files_visible_after = page.evaluate("""() => {
            var el = document.getElementById('uw-files');
            return el ? getComputedStyle(el).display !== 'none' : false;
        }""")
        assert files_visible_after, "Expected files visible after clicking"

        files_text = page.inner_text("#uw-files")
        assert "login.md" in files_text, f"Expected file list content, got {files_text}"
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof29_uncommitted.png"))

        # Without uncommitted files — section should not exist
        data_clean = make_data({"uncommitted": []})
        load_dashboard(page, dashboard, data=data_clean)
        uw_section_clean = page.query_selector(".uw-section")
        assert uw_section_clean is None, "Expected no .uw-section when uncommitted is empty"


@pytest.mark.proof("purlin_report", "PROOF-30", "RULE-30")
def test_description_block_rendering(dashboard, page):
    """Description block renders above rules when present, absent when null."""
    data = make_data()
    load_dashboard(page, dashboard, data=data)

    # Click the auth_login feature row (categories already expanded by load_dashboard)
    page.click("tr.fr[data-name='auth_login']")
    page.wait_for_timeout(300)

    # Should show .desc-block with the description text
    desc_block = page.query_selector("tr.fr[data-name='auth_login'] + tr.dr .desc-block")
    assert desc_block is not None, "Expected .desc-block when feature has description"
    desc_text = desc_block.inner_text()
    assert "Handles user login" in desc_text, (
        f"Expected description text, got: {desc_text}"
    )
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof30_description.png"))

    # Expand checkout (which has description=None)
    page.click("tr.fr[data-name='checkout']")
    page.wait_for_timeout(300)

    # The detail row for checkout should not have a .desc-block
    detail = page.query_selector("tr.fr[data-name='checkout'] + tr.dr .desc-block")
    assert detail is None, "Expected no .desc-block when description is null"
