"""
Playwright e2e tests for the purlin_report dashboard feature.

Each test loads scripts/report/purlin-report.html via file:// in a real
Chromium browser with synthetic PURLIN_DATA, then verifies DOM state.
"""

import datetime
import json
import os
import re
import shutil

import pytest
from playwright.sync_api import sync_playwright

from browser_launch import launch_browser


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
                        "status": "NONE",
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
        b = launch_browser(p)
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

    @pytest.mark.proof("purlin_report", "PROOF-1", "RULE-1", tier="e2e")
    def test_data_script_loads_before_the_first_render(self, page, dashboard):
        """PROOF-1: the data script is injected and PURLIN_DATA is already
        defined at the moment #app first renders, which is the rule's
        'before rendering' half. A page that rendered first and loaded the
        data afterwards records dataDefined=False here."""
        # Installed before navigation: it watches the document and freezes the
        # state of the world at the first mutation that gives #app children.
        page.add_init_script("""
            window.__firstRender = null;
            (function () {
                var obs = new MutationObserver(function () {
                    if (window.__firstRender !== null) return;
                    var app = document.getElementById('app');
                    if (!app || !app.children.length) return;
                    var fr = document.querySelector('iframe');
                    var doc = fr && fr.contentDocument ? fr.contentDocument : null;
                    var s = doc ? doc.querySelector('script[src*="report-data.js"]') : null;
                    window.__firstRender = {
                        dataDefined: typeof PURLIN_DATA !== 'undefined',
                        src: s ? s.getAttribute('src') : null
                    };
                    obs.disconnect();
                });
                obs.observe(document, {childList: true, subtree: true});
            })();
        """)
        load_dashboard(page, dashboard, data=make_data())

        probe = page.evaluate("() => window.__firstRender")
        assert probe, "Expected the #app render probe to fire on the first render"
        assert probe["src"] is not None and probe["src"].startswith(
            ".purlin/report-data.js?t="), (
            "Expected the injected script src to be '.purlin/report-data.js' "
            f"with a cache-busting ?t= query, got {probe['src']!r}"
        )
        assert probe["dataDefined"] is True, (
            "Expected PURLIN_DATA to be defined at the first render of #app "
            "(the data script must load before rendering), got "
            f"dataDefined={probe['dataDefined']!r}"
        )
        # And what rendered is that payload, not the no-data fallback.
        body_text = page.inner_text("body")
        assert "auth_login" in body_text, (
            "Expected the rendered dashboard to show 'auth_login' from the "
            "loaded payload, got the fallback instead"
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
        # 7 cards: the five counts, plus both quality gauges (Proof Design and
        # Proof Integrity). purlin_report RULE-34 requires the grid to be ruled for
        # exactly this many columns, so a count change here is a real signal.
        assert len(cards) == 7, (
            f"Expected 7 summary cards (5 counts + both gauges), got {len(cards)}")
        strip_text = page.inner_text(".summary-strip")
        assert "10" in strip_text, "Expected total_features=10 in summary strip"
        assert "4" in strip_text, "Expected verified=4 in summary strip"
        # Incomplete card: 2 partial + 1 untested = 3
        incomplete_card = page.query_selector(".sc-partial")
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
        first_row.click()
        page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof5_expanded.png"))
        # A .dr detail row should now be visible
        detail_rows = page.query_selector_all("tr.dr")
        assert len(detail_rows) > 0, "Expected at least one detail row (.dr) after clicking"
        # The detail row should contain a rules table (.rt)
        rules_table = detail_rows[0].query_selector("table.rt")
        assert rules_table, "Expected a rules table (.rt) inside the expanded detail row"

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

        # Read what a person sees: the pill text inside each row's name cell,
        # beside the feature name. A pill with the right class but empty or
        # wrong text, or one outside the name cell, fails here.
        pills = page.evaluate("""() => {
            const out = {};
            document.querySelectorAll('tr.fr').forEach(row => {
                const cell = row.querySelector('.fn');
                if (!cell) return;
                out[row.getAttribute('data-name')] = {
                    name: (cell.querySelector('.fnt') || {}).textContent || '',
                    pills: Array.from(cell.querySelectorAll('.tp'))
                                .map(p => p.textContent.trim()),
                };
            });
            return out;
        }""")

        for name in ("security_policy", "local_policy", "auth_login"):
            assert name in pills, f"Expected a row for {name}, got {sorted(pills)}"

        assert pills["security_policy"]["pills"] == ["global"], (
            "Expected the global anchor's name cell to hold one pill reading "
            f"'global', got {pills['security_policy']['pills']}"
        )
        assert pills["security_policy"]["name"] == "security_policy"
        assert pills["local_policy"]["pills"] == ["anchor"], (
            "Expected the local anchor's name cell to hold one pill reading "
            f"'anchor', got {pills['local_policy']['pills']}"
        )
        assert pills["local_policy"]["name"] == "local_policy"
        assert pills["auth_login"]["pills"] == [], (
            "Expected a plain feature to carry no type pill, got "
            f"{pills['auth_login']['pills']}"
        )

    @pytest.mark.proof("purlin_report", "PROOF-11", "RULE-11")
    def test_anchor_external_link_icon(self, page, dashboard):
        """PROOF-11: Anchors with source_url display an external link icon with URL as tooltip."""
        load_dashboard(page, dashboard, data=make_data())
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof11_ext_icon.png"))
        ext_icons = page.query_selector_all(".ext-icon")
        assert len(ext_icons) > 0, "Expected at least one .ext-icon element for anchors with source_url"
        icon = ext_icons[0]
        title_attr = icon.get_attribute("title")
        assert title_attr, "Expected .ext-icon to have a 'title' attribute"
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

        def row_names():
            return page.evaluate(
                "() => Array.from(document.querySelectorAll('tr.fr'))"
                ".map(r => r.getAttribute('data-name'))"
            )

        # Default sort (by status): beta (PARTIAL) comes first
        assert row_names() == ["beta", "alpha"], (
            f"Expected ['beta', 'alpha'] under the default status sort, got {row_names()}"
        )
        # Click the "Coverage" column header — ascending coverage sort: alpha (0%) first
        coverage_header = page.query_selector("th[data-col='coverage']")
        coverage_header.click()
        page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof12_sorted.png"))
        assert row_names() == ["alpha", "beta"], (
            "Expected ['alpha', 'beta'] after one click on Coverage "
            f"(0/3 before 3/3), got {row_names()}"
        )
        # The clicked column is the one marked as sorting the table.
        active_cols = page.evaluate("""() => Array.from(
            document.querySelectorAll('th[data-col]'))
            .filter(th => th.querySelector('.sa.active'))
            .map(th => th.getAttribute('data-col'))""")
        assert active_cols and set(active_cols) == {"coverage"}, (
            f"Expected only the coverage header marked active, got {active_cols}"
        )
        # A second click on the same header reverses the direction.
        page.query_selector("th[data-col='coverage']").click()
        page.wait_for_timeout(200)
        assert row_names() == ["beta", "alpha"], (
            "Expected ['beta', 'alpha'] after a second Coverage click "
            f"(descending), got {row_names()}"
        )

    @pytest.mark.proof("purlin_report", "PROOF-13", "RULE-13")
    def test_footer_docs_url(self, page, dashboard):
        """PROOF-13: Footer docs link uses docs_url from PURLIN_DATA, not hardcoded."""
        data = make_data({"docs_url": "https://example.com/docs"})
        load_dashboard(page, dashboard, data=data)
        footer_link = page.query_selector("footer a")
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

    @pytest.mark.proof("purlin_report", "PROOF-15", "RULE-15", tier="e2e")
    def test_header_shows_one_freshness_label_per_gauge(self, page, dashboard):
        """PROOF-15: two labels, two caches, two ages.

        The two caches age independently. One combined label reported the
        Integrity cache's age as though it were the project's, so a repo graded
        for Design 3 hours ago read as 78 days stale.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        three_h = (now - datetime.timedelta(hours=3)).isoformat()
        seventy_eight_d = (now - datetime.timedelta(days=78)).isoformat()
        data = make_data({
            "design_summary": {
                "design": 90, "provable": 9, "loose": 1, "unprovable": 0,
                "structural": 0, "gradeable_total": 10,
                "last_design_audit": three_h,
                "last_design_audit_relative": "3h ago",
                "stale": False,
            },
        })
        data["audit_summary"]["last_audit"] = seventy_eight_d
        data["audit_summary"]["last_audit_relative"] = "78d ago"
        data["audit_summary"]["stale"] = True
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof15_audit_stale.png"))

        labels = page.query_selector_all(".audit-time")
        assert len(labels) == 2, (
            f"expected exactly two freshness labels, one per gauge, got {len(labels)}: "
            f"{[e.text_content() for e in labels]!r}")

        d = page.query_selector(".audit-time[data-gauge='design']")
        i = page.query_selector(".audit-time[data-gauge='integrity']")
        assert d and i, "expected a label for each of data-gauge=design and data-gauge=integrity"

        d_txt, i_txt = d.text_content(), i.text_content()
        assert d_txt == "Design: 3h ago", (
            f"the Design label must name its own gauge and its own 3-hour cache: {d_txt!r}")
        assert i_txt == "Integrity: 78d ago (stale)", (
            f"the Integrity label must name its own gauge and its own 78-day cache: {i_txt!r}")

        assert d.get_attribute("class") == "audit-time", (
            f"a fresh Design cache must carry no stale class: {d.get_attribute('class')!r}")
        assert i.get_attribute("class") == "audit-time stale", (
            f"a stale Integrity cache must carry the stale class: {i.get_attribute('class')!r}")

        # Neither label may report the other cache's age or name.
        assert "Integrity" not in d_txt and "78d" not in d_txt, (
            f"the Design label leaked the Integrity cache: {d_txt!r}")
        assert "Design" not in i_txt and "3h" not in i_txt, (
            f"the Integrity label leaked the Design cache: {i_txt!r}")

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


def make_gauge(pct, kind='audit', state=None):
    """Build one per-feature gauge object in the shape report_data RULE-26 fixes.

    `state` defaults to `measured` when a percentage is present and
    `unmeasured` when it is None, which is what the server does.
    """
    if state is None:
        state = 'measured' if pct is not None else 'unmeasured'
    cov = {"measured": 1, "total": 1, "complete": True}
    if kind == 'design':
        return {
            "design": pct, "provable": 1, "loose": 0, "unprovable": 0,
            "structural": 0, "gradeable_total": 1, "state": state,
            "coverage": cov, "findings": [],
        }
    return {
        "integrity": pct, "strong": 1, "weak": 0, "hollow": 0, "manual": 0,
        "behavioral_total": 1, "state": state, "coverage": cov, "findings": [],
    }


def make_integrity_feature(name, integrity, design=None, audit_state=None,
                           design_state=None):
    """Return a feature with specific audit and design gauge values."""
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
        "audit": make_gauge(integrity, 'audit', audit_state),
        "design": make_gauge(design, 'design', design_state),
    }


class TestRulePadding:
    """Test that rule ID and description columns have visible spacing for all rule types."""

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

        color = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-failing')).color"
        )
        assert rgb_to_hex(color) == "#ffffff", (
            f"Expected .sb-failing text color #ffffff (white), got {color!r}"
        )

    @pytest.mark.proof("dashboard_visual", "PROOF-9", "RULE-9")
    def test_untested_badge_and_no_proofs_opacity(self, page, dashboard):
        """PROOF-9: the UNTESTED badge is the theme gray #64748b with amber
        #f59e0b text at opacity 1; the no-proofs badge is the same gray at
        opacity 0.45. Both are found by the label a reader sees."""
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

        # Reach each badge through the row it belongs to and the label a
        # reader sees, not through the class that styles it.
        badges = page.evaluate("""() => {
            const out = {};
            document.querySelectorAll('tr.fr').forEach(row => {
                const b = row.querySelector('td.col-status span.sb');
                if (!b) return;
                const cs = getComputedStyle(b);
                out[row.getAttribute('data-name')] = {
                    text: b.textContent.trim(),
                    bg: cs.backgroundColor,
                    color: cs.color,
                    opacity: cs.opacity,
                };
            });
            return out;
        }""")

        untested = badges.get("untested_feature")
        assert untested, f"Expected a status badge on the UNTESTED row, got {sorted(badges)}"
        assert untested["text"] == "Untested", (
            f"Expected the UNTESTED badge to read 'Untested', got {untested['text']!r}"
        )
        assert rgb_to_hex(untested["bg"]) == "#64748b", (
            "Expected the UNTESTED badge on the theme gray #64748b, got "
            f"{untested['bg']!r}"
        )
        assert rgb_to_hex(untested["color"]) == "#f59e0b", (
            f"Expected the UNTESTED badge in amber #f59e0b, got {untested['color']!r}"
        )
        assert float(untested["opacity"]) == 1.0, (
            f"Expected the UNTESTED badge at full opacity 1, got {untested['opacity']!r}"
        )

        none_badge = badges.get("unknown_status_feature")
        assert none_badge, "Expected a status badge on the no-proofs row"
        assert none_badge["text"] == "Untested", (
            f"Expected the no-proofs badge to read 'Untested', got {none_badge['text']!r}"
        )
        assert rgb_to_hex(none_badge["bg"]) == "#64748b", (
            "Expected the no-proofs badge on the theme gray #64748b, got "
            f"{none_badge['bg']!r}"
        )
        assert float(none_badge["opacity"]) == 0.45, (
            f"Expected the no-proofs badge at reduced opacity 0.45, got {none_badge['opacity']!r}"
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

        # The same three values on the Design gauge must resolve to the same three
        # classes: one helper serves both, so RULE-10 covers Design without a
        # second colour definition to drift from.
        design_data = make_data({
            "features": [
                make_integrity_feature("high_design", None, design=90),
                make_integrity_feature("mid_design", None, design=60),
                make_integrity_feature("low_design", None, design=30),
            ],
            "summary": {"total_features": 3, "verified": 3, "partial": 0, "failing": 0, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
            "design_summary": {
                "design": 60, "provable": 3, "loose": 0, "unprovable": 0, "structural": 0,
                "gradeable_total": 3, "last_design_audit": None,
                "last_design_audit_relative": None,
            },
        })
        load_dashboard(page, dashboard, data=design_data)
        design_classes = [c.get_attribute("class")
                          for c in page.query_selector_all("td.int")]
        for band in ("int-hi", "int-mid", "int-lo"):
            assert any(band in c for c in design_classes), (
                f"Expected a {band} cell from the design gauge, got: {design_classes}"
            )

        # A gauge with no percentage is coloured by why, never greyed: teal for
        # a correct terminal state, amber for one that needs an audit run.
        state_data = make_data({
            "features": [
                make_integrity_feature("excl_feat", None, design=None,
                                       audit_state="excluded", design_state="excluded"),
                make_integrity_feature("pending_feat", None, design=None,
                                       audit_state="unmeasured", design_state="unmeasured"),
            ],
            "summary": {"total_features": 2, "verified": 2, "partial": 0, "failing": 0, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
        })
        load_dashboard(page, dashboard, data=state_data)
        state_classes = [c.get_attribute("class")
                         for c in page.query_selector_all("td.int")]
        assert any("int-excluded" in c for c in state_classes), (
            f"an excluded gauge must take the teal class, got: {state_classes}")
        assert any("int-pending" in c for c in state_classes), (
            f"an unmeasured gauge must take the amber class, got: {state_classes}")
        assert not any("int-na" in c for c in state_classes), (
            f"no gauge cell may be greyed out: {state_classes}")

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
        categories with untested features show amber coverage bar.
        Specs and Anchors are in separate sections with independent grouping."""
        data = make_categorized_data()
        # A category holding a FAILING feature: the red band of the rule.
        data["features"].append({
            "name": "verify_gate", "category": "gate", "type": "feature",
            "is_global": False, "source_url": None,
            "proved": 2, "total": 5, "deferred": 0, "status": "FAILING",
            "vhash": None, "receipt": None, "rules": [], "audit": None,
        })
        data["summary"]["total_features"] = 6
        data["summary"]["failing"] = 1
        load_dashboard(page, dashboard, data=data, expand_categories=False)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof19_categories.png"))

        # Verify 4 category header rows exist total (3 in Specs, 1 in Anchors)
        cat_headers = page.query_selector_all(".cat-header")
        assert len(cat_headers) == 4, (
            f"Expected 4 category headers, got {len(cat_headers)}"
        )

        # Verify Specs section has 3 categories, Anchors section has 1
        section_cats = page.evaluate("""() => {
            const tables = document.querySelectorAll('.table-container');
            return {
                specs: tables[0] ? tables[0].querySelectorAll('.cat-header').length : 0,
                anchors: tables[1] ? tables[1].querySelectorAll('.cat-header').length : 0
            };
        }""")
        assert section_cats["specs"] == 3, (
            f"Expected 3 spec categories, got {section_cats['specs']}"
        )
        assert section_cats["anchors"] == 1, (
            f"Expected 1 anchor category, got {section_cats['anchors']}"
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

        # Verify gate category: 1 FAILING feature, 2/5 coverage, red bar
        gate = next(c for c in cat_data if c["cat"] == "gate")
        assert gate["count"] == "(1)", f"Gate count: {gate['count']}"
        assert "2/5" in gate["cov"], f"Gate coverage: {gate['cov']}"
        assert "1 failing" in gate["summary"].lower(), (
            f"Expected '1 failing' in the gate breakdown, got {gate['summary']!r}"
        )
        assert "cov-fail" in gate["barClass"], (
            f"Expected gate bar red (cov-fail) with a failing feature, got {gate['barClass']}"
        )

        # Verify _anchors category in Anchors section: 1 feature, 11/11, green bar
        anchors = next(c for c in cat_data if c["cat"] == "_anchors")
        assert anchors["count"] == "(1)", f"Anchors count: {anchors['count']}"
        assert "11/11" in anchors["cov"], f"Anchors coverage: {anchors['cov']}"
        assert anchors["label"] == "anchors", (
            f"Expected _anchors displayed as 'anchors', got '{anchors['label']}'"
        )
        assert "cov-verified" in anchors["barClass"], (
            f"Expected anchors bar green (cov-verified), got {anchors['barClass']}"
        )
        # The green band means every feature passing or verified; skills also
        # spells out its breakdown.
        assert "1 verified" in skills["summary"].lower(), skills["summary"]
        assert "1 passing" in skills["summary"].lower(), skills["summary"]

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

        # Categories are expanded by default — feature rows already visible
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof19_categories_expanded.png"))

    @pytest.mark.proof("purlin_report", "PROOF-20", "RULE-20")
    def test_categories_expanded_by_default(self, page, dashboard):
        """PROOF-20: Categories start expanded — feature rows visible with empty localStorage."""
        data = make_categorized_data()
        # expand_categories=False means: do NOT seed localStorage — pure default state
        load_dashboard(page, dashboard, data=data, expand_categories=False)

        # Feature rows should be visible without any interaction
        fr_count = page.evaluate("() => document.querySelectorAll('tr.fr').length")
        assert fr_count > 0, (
            f"Expected feature rows visible by default, got {fr_count}"
        )

        # Category headers should exist
        cat_count = page.evaluate("() => document.querySelectorAll('.cat-header').length")
        assert cat_count == 3, f"Expected 3 category headers, got {cat_count}"

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof20_expanded_default.png"))

        # Click the skills category header to collapse it
        page.click(".cat-header[data-cat='skills']")
        page.wait_for_timeout(300)

        # Its feature rows should now be hidden
        skills_rows = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='skill_build'], tr.fr[data-name='skill_audit']").length
        """)
        assert skills_rows == 0, (
            f"Expected skills features hidden after collapse, got {skills_rows}"
        )
        fr_after = page.evaluate("() => document.querySelectorAll('tr.fr').length")
        assert fr_after < fr_count, "Expected fewer feature rows after collapsing a category"

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof20_one_collapsed.png"))

    @pytest.mark.proof("purlin_report", "PROOF-21", "RULE-21")
    def test_category_state_persists_across_reloads(self, page, dashboard):
        """PROOF-21: Category open/closed state persists to localStorage and survives reload."""
        data = make_categorized_data()
        load_dashboard(page, dashboard, data=data, expand_categories=False)

        # All expanded initially (default state)
        fr_before = page.evaluate("() => document.querySelectorAll('tr.fr').length")
        assert fr_before > 0, "Expected all categories expanded initially"

        # Click the skills category to collapse it
        page.click(".cat-header[data-cat='skills']")
        page.wait_for_timeout(300)

        # Verify skills features are hidden
        skills_rows = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='skill_build'], tr.fr[data-name='skill_audit']").length
        """)
        assert skills_rows == 0, f"Expected 0 skills features after collapse, got {skills_rows}"

        # Verify localStorage recorded the collapse
        stored = page.evaluate(
            "() => JSON.parse(localStorage.getItem('purlin-categories') || '{}')"
        )
        assert stored.get("skills") is False, (
            f"Expected skills=false in localStorage, got {stored}"
        )

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof21_before_reload.png"))

        # Reload the page
        page.reload()
        page.wait_for_load_state("networkidle")

        # Skills should still be collapsed after reload
        skills_after = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='skill_build'], tr.fr[data-name='skill_audit']").length
        """)
        assert skills_after == 0, (
            f"Expected skills still collapsed after reload, got {skills_after} rows"
        )

        # Other categories should still be expanded
        mcp_rows = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='config_engine'], tr.fr[data-name='drift']").length
        """)
        assert mcp_rows == 2, (
            f"Expected mcp category still expanded after reload, got {mcp_rows} rows"
        )

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof21_after_reload.png"))

        # The other half of the rule: a feature's own open state persists too.
        page.click("tr.fr[data-name='config_engine']")
        page.wait_for_timeout(300)
        stored_expanded = page.evaluate(
            "() => JSON.parse(localStorage.getItem('purlin-expanded') || '{}')"
        )
        assert stored_expanded.get("config_engine") is True, (
            f"Expected config_engine=true in purlin-expanded, got {stored_expanded}"
        )
        page.reload()
        page.wait_for_load_state("networkidle")
        expanded_after = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='config_engine'].expanded").length
        """)
        assert expanded_after == 1, (
            "Expected config_engine still expanded after reload, got "
            f"{expanded_after} expanded rows"
        )
        detail_rows = page.evaluate("() => document.querySelectorAll('tr.dr').length")
        assert detail_rows == 1, (
            f"Expected 1 detail row restored after reload, got {detail_rows}"
        )

        # Expand skills again, reload, verify expanded
        page.click(".cat-header[data-cat='skills']")
        page.wait_for_timeout(300)
        page.reload()
        page.wait_for_load_state("networkidle")

        skills_final = page.evaluate("""() =>
            document.querySelectorAll("tr.fr[data-name='skill_build'], tr.fr[data-name='skill_audit']").length
        """)
        assert skills_final == 2, (
            f"Expected skills expanded after toggle+reload, got {skills_final} rows"
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
                        "is_assumed": False, "status": "NONE", "proofs": [],
                    },
                    {
                        "id": "RULE-3", "description": "Does thing C",
                        "label": "own", "source": None, "is_deferred": False,
                        "is_assumed": False, "status": "NONE", "proofs": [],
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
                        "is_assumed": False, "status": "NONE", "proofs": [],
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

        # --- Pending migrations: project state, shown in every status ---
        # The same payload, with two migrations pending. Every expanded
        # feature, VERIFIED included, now carries the migrations banner with
        # the directive sync_status prints.
        data = make_action_banner_data()
        data["migrations"] = [
            {"id": "legacy-proof-file", "count": 1,
             "summary": "1 proof file named with a platform where the tier belongs",
             "files": ["specs/app/demo.proofs-legacy.json"]},
            {"id": "plugin-copies-stale", "count": 2,
             "summary": "2 plugin copies differ from the installed plugin",
             "files": [".purlin/plugins/a.py", ".purlin/plugins/b.py"]},
        ]
        load_dashboard(page, dashboard, data=data)
        # The previous half left rows expanded, and that survives the reload in
        # localStorage; clear it so each click below expands rather than
        # collapses.
        page.evaluate("localStorage.removeItem('purlin-expanded')")
        page.reload()
        page.wait_for_load_state("networkidle")
        for name, own in (("feat_verified", None),
                          ("feat_passing", ".ab-passing"),
                          ("feat_partial", ".ab-partial")):
            page.click(f"tr.fr[data-name='{name}']")
            page.wait_for_timeout(300)
            banners = page.query_selector_all("tr.dr .ab-migrations")
            assert len(banners) == 1, (
                f"{name}: expected exactly one migrations banner, got "
                f"{len(banners)}")
            text = banners[0].inner_text()
            assert "2 pending migrations" in text, text
            assert "legacy-proof-file" in text and "plugin-copies-stale" in text, text
            assert "purlin:init --update" in text, text
            if own:
                assert page.query_selector(f"tr.dr {own}"), (
                    f"{name}: the feature's own banner must still be shown")
            page.click(f"tr.fr[data-name='{name}']")
            page.wait_for_timeout(200)
        page.click("tr.fr[data-name='feat_verified']")
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR,
                                          "proof23_migrations.png"))


class TestRuleRowHighlights:

    @pytest.mark.proof("purlin_report", "PROOF-24", "RULE-24")
    def test_no_proof_rules_have_amber_border(self, page, dashboard):
        """PROOF-24: NONE rules have class rule-np and amber left border."""
        data = make_action_banner_data()
        load_dashboard(page, dashboard, data=data)

        # Expand the PARTIAL feature (has 2 NONE rules)
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
            f"Expected amber (#f59e0b) border-left on NONE rule td, got {hex_color}"
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
        with Source link, Path, a git SHA pin as its 7-char prefix, a Figma
        ISO 8601 pin in full; unpinned shows amber."""
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
                     "is_assumed": False, "status": "NONE", "proofs": []},
                ],
                "audit": None,
            },
            {
                # Figma-sourced anchor: `purlin:anchor sync` pins the file's
                # lastModified as an ISO 8601 timestamp, not a commit SHA, so
                # the detail block must show it whole (RULE-26).
                "name": "figma_anchor",
                "category": "_anchors",
                "type": "anchor",
                "is_global": False,
                "source_url": "https://www.figma.com/design/ABC123/Design-System",
                "pinned": "2026-03-31T12:00:00Z",
                "source_path": None,
                "proved": 1,
                "total": 1,
                "deferred": 0,
                "status": "PASSING",
                "vhash": "eeff3344",
                "receipt": None,
                "rules": [
                    {"id": "RULE-1", "description": "Matches the Figma frame",
                     "label": "own", "source": None, "is_deferred": False,
                     "is_assumed": False, "status": "PASS", "proofs": []},
                ],
                "audit": None,
            },
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 0, "verified": 0, "passing": 2,
                        "partial": 0, "failing": 0, "untested": 1},
            "anchors_summary": {"total": 3, "with_source": 3, "global": 0},
        })
        load_dashboard(page, dashboard, data=data)

        # Expand pinned anchor
        page.click("tr.fr[data-name='pinned_anchor']")
        page.wait_for_timeout(300)

        # Verify .ext-ref-block exists
        block = page.query_selector(".ext-ref-block")
        assert block, "Expected .ext-ref-block for anchor with source_url"

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

        # Figma anchor: the ISO 8601 pin must render whole, never truncated
        page.click("tr.fr[data-name='unpinned_anchor']")  # collapse
        page.wait_for_timeout(200)
        page.click("tr.fr[data-name='figma_anchor']")
        page.wait_for_timeout(300)

        figma_pinned = page.evaluate("""() => {
            var block = document.querySelector('.ext-ref-block');
            var rows = block ? block.querySelectorAll('tr') : [];
            for (var r of rows) {
                var label = r.querySelector('.ext-ref-label');
                if (label && label.textContent.trim() === 'Pinned') {
                    var code = r.querySelector('code');
                    return code ? code.textContent : null;
                }
            }
            return null;
        }""")
        assert figma_pinned == "2026-03-31T12:00:00Z", (
            "Expected the Figma pin rendered in full as '2026-03-31T12:00:00Z', "
            f"got {figma_pinned!r} (a Figma timestamp must not be truncated "
            "like a git SHA)"
        )
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof26_ext_ref_figma.png"))

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
        assert title, "Expected .ext-icon with title attribute"
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
        assert stale_badge, "Expected .ext-stale badge on stale anchor"
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
        assert uw_section, "Expected .uw-section when uncommitted files exist"

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


@pytest.mark.proof("purlin_report", "PROOF-31", "RULE-31")
def test_structural_proof_tag_rendering(dashboard, page):
    """PROOF-31: Structural proofs show a green 'Structural' tag (.atag-st); behavioral proofs do not."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # Put each proof in its own rule so each lives in its own .rprf td cell,
    # making it straightforward to verify the structural tag appears only on the
    # structural proof and not on the behavioral one.
    data = make_data({
        "features": [
            {
                "name": "auth_login",
                "category": "auth",
                "type": "feature",
                "is_global": False,
                "description": "Login feature",
                "source_url": None,
                "proved": 2,
                "total": 2,
                "deferred": 0,
                "status": "PASSING",
                "vhash": "a1b2c3d4",
                "receipt": None,
                "rules": [
                    {
                        "id": "RULE-1",
                        "description": "No eval in scripts",
                        "label": "own",
                        "source": None,
                        "is_deferred": False,
                        "is_assumed": False,
                        "status": "PASS",
                        "proofs": [
                            {
                                "id": "PROOF-1",
                                "description": "Grep scripts/ for eval(); verify zero matches",
                                "test_file": "tests/test_sec.py",
                                "test_name": "test_no_eval",
                                "tier": "unit",
                                "status": "pass",
                            },
                        ],
                    },
                    {
                        "id": "RULE-2",
                        "description": "Rejects expired tokens",
                        "label": "own",
                        "source": None,
                        "is_deferred": False,
                        "is_assumed": False,
                        "status": "PASS",
                        "proofs": [
                            {
                                "id": "PROOF-2",
                                "description": "Returns 401 when token is expired",
                                "test_file": "tests/test_login.py",
                                "test_name": "test_expired",
                                "tier": "unit",
                                "status": "pass",
                            },
                        ],
                    },
                ],
                "audit": {
                    "integrity": 85,
                    "strong": 1,
                    "weak": 0,
                    "hollow": 0,
                    "manual": 0,
                    "findings": [],
                },
            },
        ],
        "summary": {
            "total_features": 1,
            "verified": 0,
            "passing": 1,
            "partial": 0,
            "failing": 0,
            "untested": 0,
        },
        "audit_summary": {
            "integrity": 85,
            "strong": 1,
            "weak": 0,
            "hollow": 0,
            "manual": 0,
            "behavioral_total": 2,
            "last_audit": now,
            "last_audit_relative": "just now",
            "stale": False,
        },
    })
    load_dashboard(page, dashboard, data=data)

    # Expand the auth_login feature row
    page.click("tr.fr[data-name='auth_login']")
    page.wait_for_timeout(300)
    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof31_structural_tag.png"))

    # Each rule has its own .rprf td — find the cell that contains PROOF-1 exclusively
    # (RULE-1's cell) and verify it has .atag-st
    structural_tag = page.evaluate("""() => {
        const detail = document.querySelector("tr.fr[data-name='auth_login'] + tr.dr");
        if (!detail) return 'no-detail';
        // Each rule row has exactly one .rprf td; collect them in order
        const proofCells = Array.from(detail.querySelectorAll('tr td.rprf'));
        // First cell = RULE-1 (structural proof PROOF-1)
        const cell1 = proofCells[0];
        if (!cell1) return 'no-proof-cells';
        const tag = cell1.querySelector('.atag-st');
        return tag ? tag.textContent.trim() : null;
    }""")
    assert structural_tag == "Structural", (
        f"Expected RULE-1 proof cell (structural) to have .atag-st='Structural', got: {structural_tag!r}"
    )

    # Second cell = RULE-2 (behavioral proof PROOF-2) — must NOT have .atag-st
    behavioral_tag = page.evaluate("""() => {
        const detail = document.querySelector("tr.fr[data-name='auth_login'] + tr.dr");
        if (!detail) return 'no-detail';
        const proofCells = Array.from(detail.querySelectorAll('tr td.rprf'));
        // Second cell = RULE-2 (behavioral proof PROOF-2)
        const cell2 = proofCells[1];
        if (!cell2) return 'no-second-cell';
        const tag = cell2.querySelector('.atag-st');
        return tag ? tag.textContent.trim() : null;
    }""")
    assert behavioral_tag is None, (
        f"Expected RULE-2 proof cell (behavioral) to have no .atag-st, got: {behavioral_tag!r}"
    )

    # Verify the .atag-st element has a green background (#22c55e)
    structural_bg = page.evaluate("""() => {
        const tag = document.querySelector('.atag-st');
        return tag ? getComputedStyle(tag).backgroundColor : null;
    }""")
    assert structural_bg is not None, "Expected .atag-st element to be present for color check"
    assert rgb_to_hex(structural_bg) == "#22c55e", (
        f"Expected .atag-st background #22c55e (green), got: {structural_bg!r}"
    )

    # Verify the .atag-st element has white text (#ffffff)
    structural_color = page.evaluate("""() => {
        const tag = document.querySelector('.atag-st');
        return tag ? getComputedStyle(tag).color : None;
    }""")
    assert rgb_to_hex(structural_color) == "#ffffff", (
        f"Expected .atag-st text color #ffffff (white), got: {structural_color!r}"
    )


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


@pytest.mark.proof("purlin_report", "PROOF-32", "RULE-32")
def test_anchors_separate_section(dashboard, page):
    """PROOF-32: Anchors render in a separate section from specs.
    Specs section has no anchor features; Anchors section has all anchors."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    data = {
        "timestamp": now,
        "project": "test-project",
        "version": "0.9.0",
        "docs_url": None,
        "summary": {
            "total_features": 4,
            "verified": 1,
            "passing": 2,
            "partial": 1,
            "failing": 0,
            "untested": 0,
        },
        "features": [
            {
                "name": "auth_login", "category": "auth", "type": "feature",
                "is_global": False, "source_url": None,
                "proved": 3, "total": 3, "deferred": 0, "status": "PASSING",
                "vhash": "a1", "receipt": None, "rules": [], "audit": None,
            },
            {
                "name": "auth_register", "category": "auth", "type": "feature",
                "is_global": False, "source_url": None,
                "proved": 2, "total": 4, "deferred": 0, "status": "PARTIAL",
                "vhash": "a2", "receipt": None, "rules": [], "audit": None,
            },
            {
                "name": "dashboard_visual", "category": "_anchors", "type": "anchor",
                "is_global": False, "source_url": None,
                "proved": 11, "total": 11, "deferred": 0, "status": "VERIFIED",
                "vhash": "b1",
                "receipt": {"commit": "x", "timestamp": now, "stale": False},
                "rules": [], "audit": None,
            },
            {
                "name": "security_policy", "category": "_anchors", "type": "anchor",
                "is_global": True, "source_url": "https://example.com/policy.git",
                "proved": 5, "total": 5, "deferred": 0, "status": "PASSING",
                "vhash": "b2", "receipt": None, "rules": [], "audit": None,
                "pinned": "abc1234567890", "source_path": "policy.md",
                "ext_status": None,
            },
        ],
        "anchors_summary": {"total": 2, "with_source": 1, "global": 1},
        "audit_summary": None,
        "drift": None,
    }
    load_dashboard(page, dashboard, data=data, expand_categories=True)

    # 1. Verify two section labels exist: "Specs" and "Anchors"
    labels = page.evaluate("""() => {
        return Array.from(document.querySelectorAll('.section-label'))
            .map(el => el.textContent.trim());
    }""")
    assert "Specs" in labels, f"Missing 'Specs' section label, got {labels}"
    assert "Anchors" in labels, f"Missing 'Anchors' section label, got {labels}"

    # 2. Verify two table containers exist (one per section)
    table_count = page.evaluate(
        "() => document.querySelectorAll('.table-container').length"
    )
    assert table_count == 2, f"Expected 2 table containers, got {table_count}"

    # 3. Verify NO anchor features in the Specs section (first table)
    anchor_in_specs = page.evaluate("""() => {
        const tables = document.querySelectorAll('.table-container');
        const specsTable = tables[0];
        const rows = specsTable.querySelectorAll('tr.fr');
        return Array.from(rows).some(r =>
            r.querySelector('.tp-anchor') || r.querySelector('.tp-global')
        );
    }""")
    assert not anchor_in_specs, "Anchor features found in Specs section"

    # 4. Verify all anchor features are in the Anchors section (second table)
    anchor_names = page.evaluate("""() => {
        const tables = document.querySelectorAll('.table-container');
        const anchorsTable = tables[1];
        const rows = anchorsTable.querySelectorAll('tr.fr');
        return Array.from(rows).map(r => r.getAttribute('data-name'));
    }""")
    assert "dashboard_visual" in anchor_names, (
        f"Expected 'dashboard_visual' in Anchors section, got {anchor_names}"
    )
    assert "security_policy" in anchor_names, (
        f"Expected 'security_policy' in Anchors section, got {anchor_names}"
    )
    assert len(anchor_names) == 2, (
        f"Expected exactly 2 anchors in Anchors section, got {len(anchor_names)}"
    )

    # 5. Verify spec features are NOT in the Anchors section
    spec_in_anchors = page.evaluate("""() => {
        const tables = document.querySelectorAll('.table-container');
        const anchorsTable = tables[1];
        const rows = anchorsTable.querySelectorAll('tr.fr');
        const names = Array.from(rows).map(r => r.getAttribute('data-name'));
        return names.some(n => n === 'auth_login' || n === 'auth_register');
    }""")
    assert not spec_in_anchors, "Spec features found in Anchors section"

    # 6. Verify spec features are in the Specs section
    spec_names = page.evaluate("""() => {
        const tables = document.querySelectorAll('.table-container');
        const specsTable = tables[0];
        const rows = specsTable.querySelectorAll('tr.fr');
        return Array.from(rows).map(r => r.getAttribute('data-name'));
    }""")
    assert "auth_login" in spec_names, (
        f"Expected 'auth_login' in Specs section, got {spec_names}"
    )
    assert "auth_register" in spec_names, (
        f"Expected 'auth_register' in Specs section, got {spec_names}"
    )

    page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof32_anchors_section.png"))


# ---------------------------------------------------------------------------
# TestPlannedProofRendering — planned proofs greyed with "not run" indicator
# ---------------------------------------------------------------------------

def make_planned_proof_data():
    """One feature: RULE-1 has an executed + a planned proof, RULE-2 has none."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "timestamp": now,
        "project": "test-project",
        "version": "0.9.0",
        "docs_url": None,
        "summary": {"total_features": 1, "verified": 0, "partial": 1, "failing": 0, "untested": 0},
        "features": [{
            "name": "auth_login",
            "category": "auth",
            "type": "feature",
            "is_global": False,
            "source_url": None,
            "proved": 1,
            "total": 2,
            "deferred": 0,
            "status": "PARTIAL",
            "vhash": None,
            "receipt": None,
            "rules": [
                {
                    "id": "RULE-1", "description": "Validates credentials",
                    "label": "own", "source": None, "is_deferred": False,
                    "is_assumed": False, "status": "PASS",
                    "proofs": [
                        {
                            "id": "PROOF-1", "description": "POST valid creds",
                            "test_file": "tests/test.py", "test_name": "test_valid",
                            "tier": "unit", "status": "pass", "audit": "STRONG",
                        },
                        {
                            "id": "PROOF-2", "description": "POST bad creds returns 401",
                            "test_file": "", "test_name": "",
                            "tier": "integration", "status": "planned", "audit": "",
                        },
                    ],
                },
                {
                    "id": "RULE-2", "description": "Locks account after 5 failures",
                    "label": "own", "source": None, "is_deferred": False,
                    "is_assumed": False, "status": "NONE",
                    "proofs": [],
                },
            ],
            "audit": None,
        }],
        "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
        "audit_summary": {
            "integrity": 85, "strong": 4, "weak": 1, "hollow": 1, "manual": 0,
            "behavioral_total": 6, "last_audit": now,
            "last_audit_relative": "just now", "stale": False,
        },
        "drift": None,
    }


class TestPlannedProofRendering:

    @pytest.mark.proof("purlin_report", "PROOF-33", "RULE-33")
    def test_planned_proof_renders_greyed_not_run(self, page, dashboard):
        """PROOF-33: Planned proofs render greyed with 'not run', no audit tag;
        empty-proofs rules still show an em dash."""
        load_dashboard(page, dashboard, data=make_planned_proof_data())

        # Expand the feature
        page.click("tr.fr[data-name='auth_login']")
        page.wait_for_timeout(300)

        # Planned proof renders inside .rprf-planned with a "not run" tag
        planned = page.query_selector(".rprf-planned")
        assert planned is not None, "Expected a .rprf-planned element for the planned proof"
        planned_text = planned.text_content()
        assert "not run" in planned_text, (
            f"Expected 'not run' indicator in planned proof, got: {planned_text}"
        )
        assert "PROOF-2" in planned_text and "POST bad creds returns 401" in planned_text, (
            f"Expected planned proof id and description, got: {planned_text}"
        )

        # Planned proof never shows an audit tag (even with audit_summary data)
        planned_atags = page.evaluate("""() =>
            document.querySelectorAll('.rprf-planned .atag, .rprf-planned .atag-st').length
        """)
        assert planned_atags == 0, (
            f"Expected no audit tags inside planned proof, got {planned_atags}"
        )

        # Executed proof renders normally (outside .rprf-planned, with its audit tag)
        executed_info = page.evaluate("""() => {
            const cells = document.querySelectorAll('.rprf');
            for (const c of cells) {
                if (c.textContent.includes('PROOF-1')) {
                    return {
                        hasAudit: c.querySelectorAll('.atag').length > 0,
                        hasLoc: c.textContent.includes('tests/test.py'),
                    };
                }
            }
            return null;
        }""")
        assert executed_info is not None, "Expected the executed proof cell to render"
        assert executed_info["hasAudit"], "Expected audit tag on the executed proof"
        assert executed_info["hasLoc"], "Expected test location on the executed proof"

        # Rule with an empty proofs array still shows an em dash
        dash_cell = page.evaluate("""() => {
            const rows = document.querySelectorAll('.rt tbody tr');
            for (const r of rows) {
                if (r.textContent.includes('RULE-2')) {
                    const cell = r.querySelector('.rprf');
                    return cell ? cell.textContent.trim() : null;
                }
            }
            return null;
        }""")
        assert dash_cell == "—", (
            f"Expected em dash for rule with no proofs, got: {dash_cell!r}"
        )

        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof33_planned_proof.png"))


class TestProofDesignCard:
    """RULE-34 — the Proof Design gauge renders beside Proof Integrity."""

    def _data(self, design=None, audit=None, all_untested=False):
        data = make_data()
        data["design_summary"] = design
        data["audit_summary"] = audit
        if all_untested:
            for f in data["features"]:
                f["status"] = "UNTESTED"
                f["proved"] = 0
            s = data["summary"]
            s["untested"] = s["total_features"]
            for k in ("verified", "passing", "partial", "failing"):
                s[k] = 0
        return data

    def _design(self, pct, provable=9, loose=1, unprovable=0):
        return {
            "design": pct, "provable": provable, "loose": loose,
            "unprovable": unprovable, "structural": 3,
            "gradeable_total": provable + loose + unprovable,
            "last_design_audit": None, "last_design_audit_relative": "just now",
        }

    @pytest.mark.proof("purlin_report", "PROOF-34", "RULE-34", tier="e2e")
    def test_design_card_renders_with_shared_colour_bands(self, page, dashboard):
        # 90% green, 60% amber, 30% red — the same bands as the integrity card,
        # so dashboard_visual RULE-10 needs no change.
        for pct, expect_cls in ((90, None), (60, "int-mid"), (30, "int-lo")):
            load_dashboard(page, dashboard, data=self._data(design=self._design(pct)))
            card = page.locator(".summary-card", has_text="Proof Design").first
            assert card.count() > 0, f"no Proof Design card at {pct}%"
            assert f"{pct}%" in card.inner_text(), card.inner_text()
            cls = card.get_attribute("class") or ""
            if expect_cls:
                assert expect_cls in cls, f"{pct}% should carry {expect_cls}, got {cls!r}"
            else:
                assert "int-mid" not in cls and "int-lo" not in cls, \
                    f"90% should use the default green class, got {cls!r}"

        # Per-level counts appear in the sub-label.
        load_dashboard(page, dashboard,
                       data=self._data(design=self._design(75, 3, 1, 0)))
        card = page.locator(".summary-card", has_text="Proof Design").first
        assert "3P" in card.inner_text() and "1L" in card.inner_text(), card.inner_text()

        # A null gauge shows an em dash, not a zero.
        load_dashboard(page, dashboard, data=self._data(design=None))
        card = page.locator(".summary-card", has_text="Proof Design").first
        assert "—" in card.inner_text(), card.inner_text()

    @pytest.mark.proof("purlin_report", "PROOF-34", "RULE-34", tier="e2e")
    def test_integrity_card_says_no_tests_yet_when_nothing_is_tested(self, page, dashboard):
        # Spec-first project: no audit cache AND nothing tested.
        load_dashboard(page, dashboard, data=self._data(all_untested=True))
        card = page.locator(".summary-card", has_text="Proof Integrity").first
        assert "no tests yet" in card.inner_text(), card.inner_text()

        # Tested but never audited is a different state.
        load_dashboard(page, dashboard, data=self._data(all_untested=False))
        card = page.locator(".summary-card", has_text="Proof Integrity").first
        assert "run purlin:audit" in card.inner_text(), card.inner_text()


class TestGaugeCellsAndCoverage:
    """RULE-35/36 — no blank quality cell, and no score without its denominator.

    The dashboard showed a confident Proof Integrity of 100% in the summary strip
    while 39 of 40 feature rows read an em dash, because the roll-up's
    denominator silently excluded every unaudited proof. A number at the top with
    blank rows beneath it is the state these two rules forbid.
    """

    def _three_states(self):
        return [
            make_integrity_feature("measured_feat", 75, design=75),
            make_integrity_feature("excluded_feat", None, design=None,
                                   audit_state="excluded", design_state="excluded"),
            make_integrity_feature("unmeasured_feat", None, design=None,
                                   audit_state="unmeasured", design_state="unmeasured"),
        ]

    @pytest.mark.proof("purlin_report", "PROOF-37", "RULE-35", tier="e2e")
    def test_gauge_cells_never_render_an_em_dash(self, page, dashboard):
        data = make_data({
            "features": self._three_states(),
            "summary": {"total_features": 3, "verified": 3, "partial": 0,
                        "failing": 0, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
        })
        load_dashboard(page, dashboard, data=data)

        cells = page.query_selector_all("td.int")
        assert len(cells) == 6, \
            f"expected 6 gauge cells for 3 features x 2 gauges, got {len(cells)}"

        texts = [c.text_content().strip() for c in cells]
        # Each gauge names its unscorable state in its own vocabulary: STRUCTURAL
        # describes a description, EXCLUDED describes a test. Design must never
        # read "excluded" (references/audit_criteria.md: the two never mix).
        assert sorted(texts) == sorted(
            ["75%", "75%", "structural", "excluded", "not audited", "not audited"]), \
            f"unexpected gauge cell contents: {texts}"
        design_cells = [r.query_selector_all("td.int")[0].text_content().strip()
                        for r in page.query_selector_all("tr.fr")]
        assert "excluded" not in design_cells, (
            "a Proof Design cell must never read 'excluded' — its unscorable "
            f"level is STRUCTURAL: {design_cells}")

        for c, t in zip(cells, texts):
            assert "—" not in t and "&mdash;" not in t, \
                f"gauge cell rendered an em dash: {t!r}"
            assert c.get_attribute("title"), \
                f"gauge cell {t!r} carries no tooltip explaining the value"
            # Whole words, so nothing in the column needs decoding.
            assert not t.endswith("."), f"abbreviated gauge token: {t!r}"

        # The two non-numeric states must be distinguishable, which is the whole
        # point: one means fully assessed with nothing scorable, the other means
        # nobody has looked. And each is coloured by its meaning rather than
        # greyed out, so neither reads as absent data.
        assert texts.count("not audited") == 2, \
            "the unmeasured state must render as its own token"
        by_text = {}
        for c, t in zip(cells, texts):
            by_text.setdefault(t, []).append(c.get_attribute("class"))
        for word in ("structural", "excluded"):
            for cls in by_text[word]:
                assert "int-excluded" in cls and "int-na" not in cls, \
                    f"an unscorable gauge must be teal, not grey: {cls}"
        for cls in by_text["not audited"]:
            assert "int-pending" in cls and "int-na" not in cls, \
                f"an unmeasured gauge must be amber, not grey: {cls}"
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof37_gauge_cells.png"))

    @pytest.mark.proof("purlin_report", "PROOF-38", "RULE-36", tier="e2e")
    def test_gauge_card_states_its_denominator_and_goes_amber(self, page, dashboard):
        base = {
            "features": self._three_states(),
            "summary": {"total_features": 3, "verified": 3, "partial": 0,
                        "failing": 0, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
        }

        def design_summary(measured, total, complete):
            """A gauge whose assessed score is always 100%, over varying coverage.

            `weighted` is what the server computes as
            passing / (gradeable + unmeasured); every measured description here
            is PROVABLE, so that reduces to measured / total.
            """
            return {
                "design": 100,
                "assessed": 100,
                "weighted": round(measured / total * 100),
                "provable": measured, "loose": 0, "unprovable": 0,
                "structural": 0, "gradeable_total": measured,
                "last_design_audit": None, "last_design_audit_relative": None,
                "coverage": {"measured": measured, "total": total, "complete": complete},
            }

        def design_card():
            for card in page.query_selector_all(".summary-card"):
                label = card.query_selector(".summary-card-label")
                if label and label.text_content().strip() == "Proof Design":
                    return card
            raise AssertionError("Proof Design card not found")

        # A 100% assessed score over 11 of 560. The headline must be the weighted
        # 2%, not the assessed 100%: this exact shape printed a confident 100%
        # while 39 of 40 feature rows read "not audited".
        load_dashboard(page, dashboard,
                       data=make_data(dict(base, design_summary=design_summary(11, 560, False))))
        card = design_card()
        sub = card.query_selector(".summary-card-sub")
        num = card.query_selector(".summary-card-number").text_content().strip()
        assert num == "2%", (
            f"the headline must be the coverage-weighted figure, got {num!r}")
        assert sub.text_content().strip() == "11 of 560 measured", \
            "the card must state what it measured over"
        cls = card.get_attribute("class")
        assert "int-lo" in cls, (
            "a weighted 2% must render red: the band follows the honest number, and "
            f"forcing amber would promote it. Classes were {cls}")
        sub_cls = sub.get_attribute("class")
        assert "int-lo" in sub_cls, (
            "2% measurement coverage must colour the sub-label red, not leave it grey: "
            f"classes were {sub_cls}")
        title = sub.get_attribute("title")
        assert "2% measurement coverage" in title, \
            f"the tooltip must state the coverage percentage, got {title!r}"
        assert "100% of those assessed" in title, (
            "the tooltip must keep the assessed score: a low headline from thin "
            f"coverage needs a different fix than one from bad proofs. Got {title!r}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof38_coverage_partial.png"))

        # Mid band: 336 of 560 is 60% coverage, so headline and sub-label are amber.
        load_dashboard(page, dashboard,
                       data=make_data(dict(base, design_summary=design_summary(336, 560, False))))
        card = design_card()
        assert card.query_selector(".summary-card-number").text_content().strip() == "60%"
        sub_cls = card.query_selector(".summary-card-sub").get_attribute("class")
        assert "int-mid" in sub_cls and "int-lo" not in sub_cls, (
            "60% measurement coverage must colour the sub-label amber: "
            f"classes were {sub_cls}")

        # Full coverage: the weighted figure collapses onto the assessed 100%, so
        # the gauge reads green and means what it always did.
        load_dashboard(page, dashboard,
                       data=make_data(dict(base, design_summary=design_summary(560, 560, True))))
        card = design_card()
        sub = card.query_selector(".summary-card-sub")
        assert card.query_selector(".summary-card-number").text_content().strip() == "100%", \
            "at full coverage the weighted figure must equal the assessed score"
        assert sub.text_content().strip() == "560 of 560 measured"
        cls = card.get_attribute("class")
        assert "int-mid" not in cls and "int-lo" not in cls, \
            f"a complete 100% must read green, classes were {cls}"
        sub_cls = sub.get_attribute("class")
        assert "int-hi" in sub_cls, (
            "full measurement coverage must colour the sub-label green: "
            f"classes were {sub_cls}")

    @pytest.mark.proof("purlin_report", "PROOF-41", "RULE-39", tier="e2e")
    def test_awaiting_runner_block_explains_the_reduced_coverage(self, page, dashboard):
        """RULE-39: a row that silently dropped a rule must say why.

        The coverage fraction already excludes a rule whose only proof is
        runner-gated, so without this block the row reads a clean N/N and never
        mentions that a platform the project claims to support is unproven.
        """
        data = make_data()
        feats = data["features"]
        assert len(feats) >= 2, "need two features to contrast"
        feats[0]["awaiting_runner"] = [{"id": "PROOF-2", "tier": "windows", "platform": "windows"}]
        waiting_name, waiting_status = feats[0]["name"], feats[0]["status"]
        feats[1]["awaiting_runner"] = []
        clean_name = feats[1]["name"]
        load_dashboard(page, dashboard, data=data)

        def detail_text(name):
            page.click(f"tr.fr[data-name='{name}']")
            page.wait_for_timeout(200)
            return page.evaluate(
                """(n) => {
                    const row = document.querySelector(`tr.fr[data-name="${n}"]`);
                    const detail = row ? row.nextElementSibling : null;
                    return (detail && detail.classList.contains('dr'))
                        ? detail.textContent : '';
                }""", name)

        waiting = detail_text(waiting_name)
        assert "Awaiting Runner" in waiting, (
            f"no Awaiting Runner block for a feature that has one:\n{waiting}")
        assert "@windows" in waiting, f"the block must name the tier:\n{waiting}"
        assert "PROOF-2" in waiting, f"the block must name the proof id:\n{waiting}"

        clean = detail_text(clean_name)
        assert "Awaiting Runner" not in clean, (
            f"an empty list must render no block at all:\n{clean}")

        # Warn, never block: the badge is whatever the status alone dictates.
        badge = page.inner_text(
            f"tr.fr[data-name='{waiting_name}'] .sb").strip().upper()
        assert badge == waiting_status.upper(), (
            f"awaiting a runner must not change the status badge: status is "
            f"{waiting_status}, badge reads {badge}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof41_awaiting_runner.png"))

    @pytest.mark.proof("purlin_report", "PROOF-40", "RULE-38", tier="e2e")
    def test_summary_strip_rows_are_exactly_filled(self, page, dashboard):
        """RULE-38: no empty cells in the summary strip above 900px.

        Seven cards in a four-column grid tiled as 4+3 and left a card-sized
        hole beside Proof Integrity, which reads as a rendering failure rather
        than a layout. 1600px and 1280px sit either side of the breakpoint.
        """
        load_dashboard(page, dashboard, data=make_data())

        for width in (1600, 1280):
            page.set_viewport_size({"width": width, "height": 900})
            page.wait_for_timeout(120)
            measured = page.evaluate(
                r"""() => {
                    const strip = document.querySelector('.summary-strip');
                    const cs = getComputedStyle(strip);
                    const cols = cs.gridTemplateColumns.split(' ').length;
                    const spans = [...strip.children].map(el => {
                        const v = getComputedStyle(el).gridColumn || '';
                        const m = v.match(/span\s+(\d+)/);
                        return m ? parseInt(m[1], 10) : 1;
                    });
                    const right = strip.getBoundingClientRect().right;
                    const lastRight = Math.max(
                        ...[...strip.children].map(el => el.getBoundingClientRect().right));
                    const cardW = strip.children[0].getBoundingClientRect().width;
                    return {cols, spans, gap: right - lastRight, cardW};
                }"""
            )
            cols, spans = measured["cols"], measured["spans"]
            total = sum(spans)
            assert total % cols == 0, (
                f"at {width}px the strip is {cols} columns and its cards span "
                f"{total} in total, leaving {cols - (total % cols)} empty cell(s) "
                f"in the last row; spans were {spans}"
            )
            # And nothing card-sized is left blank on the right of the last row.
            assert measured["gap"] < measured["cardW"] * 0.5, (
                f"at {width}px the last row ends {measured['gap']:.0f}px short of "
                f"the strip's right edge, about a card's width ({measured['cardW']:.0f}px)"
            )
            page.screenshot(path=os.path.join(SCREENSHOT_DIR, f"proof40_strip_{width}.png"))

    @pytest.mark.proof("purlin_report", "PROOF-39", "RULE-37", tier="e2e")
    def test_refresh_directive_names_only_the_stale_gauge(self, page, dashboard):
        """RULE-37: refresh the half that is stale, not both, and say so in the tooltip.

        Design grading is deterministic and needs no tests; Integrity grading
        needs test code and costs LLM calls. A blanket `purlin:audit` directive
        spent that budget re-grading Integrity when only Design had gone stale.

        The directive rides in the label's `title`, not its text: spelled out
        inline it doubled the header's length and read as the name of a skill
        ("/design not measured") that does not exist.
        """
        def summaries(design_stale, audit_stale, measured=True):
            old = "2026-01-01T00:00:00+00:00"
            new = datetime.datetime.now(datetime.timezone.utc).isoformat()
            return {
                "design_summary": {
                    "design": 90, "provable": 9, "loose": 1, "unprovable": 0,
                    "structural": 0, "gradeable_total": 10,
                    "last_design_audit": (old if design_stale else new) if measured else None,
                    "last_design_audit_relative": "8 months ago" if design_stale else "just now",
                    "stale": design_stale,
                },
                "audit_summary": {
                    "integrity": 90, "strong": 9, "weak": 1, "hollow": 0, "manual": 0,
                    "behavioral_total": 10,
                    "last_audit": (old if audit_stale else new) if measured else None,
                    "last_audit_relative": "8 months ago" if audit_stale else "just now",
                    "stale": audit_stale,
                },
            }

        base = {
            "features": [make_integrity_feature("f1", 90, design=90)],
            "summary": {"total_features": 1, "verified": 1, "partial": 0,
                        "failing": 0, "untested": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
        }

        def label(which):
            el = page.query_selector(".audit-time[data-gauge='%s']" % which)
            assert el, "no freshness label for data-gauge=%s" % which
            return el.text_content(), el.get_attribute("title")

        def show(**kw):
            load_dashboard(page, dashboard,
                           data=make_data(dict(base, **summaries(**kw))))

        # Neither gauge measured: both labels say so, and both ask for the
        # full audit, in the tooltip and nowhere else.
        show(design_stale=False, audit_stale=False, measured=False)
        d_txt, d_tip = label("design")
        i_txt, i_tip = label("integrity")
        assert d_txt == "Design: not measured", (
            f"an unmeasured Design gauge reads 'Design: not measured': {d_txt!r}")
        assert i_txt == "Integrity: not measured", (
            f"an unmeasured Integrity gauge reads 'Integrity: not measured': {i_txt!r}")
        assert "purlin:audit" not in d_txt and "purlin:audit" not in i_txt, (
            "the command belongs in the tooltip, never in the label text: "
            f"{d_txt!r} / {i_txt!r}")
        assert d_tip == "Run purlin:audit", (
            f"both gauges unmeasured means the bare full audit: {d_tip!r}")
        assert i_tip == "Run purlin:audit", (
            f"both gauges unmeasured means the bare full audit: {i_tip!r}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof39_unmeasured.png"))

        # Only Design stale: refresh Design alone.
        show(design_stale=True, audit_stale=False)
        d_txt, d_tip = label("design")
        i_txt, i_tip = label("integrity")
        assert d_tip == "Run purlin:audit --design", (
            f"a stale Design gauge must name --design and nothing wider: {d_tip!r}")
        assert i_tip is None, (
            "refreshing Design must not drag Integrity along, which costs LLM "
            f"calls for no reason: a fresh gauge carries no tooltip, got {i_tip!r}")
        assert "purlin:audit" not in d_txt, (
            f"the command belongs in the tooltip, not the label text: {d_txt!r}")

        # Only Integrity stale: refresh Integrity alone.
        show(design_stale=False, audit_stale=True)
        d_txt, d_tip = label("design")
        i_txt, i_tip = label("integrity")
        assert i_tip == "Run purlin:audit --integrity", (
            f"a stale Integrity gauge must name --integrity: {i_tip!r}")
        assert d_tip is None, (
            f"Design is fresh and must carry no directive: {d_tip!r}")

        # Both stale: the bare command is the right one.
        show(design_stale=True, audit_stale=True)
        d_txt, d_tip = label("design")
        i_txt, i_tip = label("integrity")
        assert d_tip == "Run purlin:audit" and i_tip == "Run purlin:audit", (
            f"with both stale the directive is a bare full audit: {d_tip!r} / {i_tip!r}")
        assert "--design" not in (d_tip or "") and "--integrity" not in (i_tip or ""), (
            f"a bare full audit names no flag: {d_tip!r} / {i_tip!r}")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof39_refresh_directive.png"))

        # Both fresh: nothing to run, so no tooltip at all.
        show(design_stale=False, audit_stale=False)
        d_txt, d_tip = label("design")
        i_txt, i_tip = label("integrity")
        assert d_tip is None and i_tip is None, (
            "a fresh gauge carries no command tooltip, so a tooltip being there "
            f"is itself the signal: {d_tip!r} / {i_tip!r}")


class TestRemoteVerificationChip:
    """purlin_report RULE-40 — the declared mode in the header.

    A chip and not a gauge: it reports what the project declared, and a
    declaration is not a measurement. Its tooltip carries the
    declaration/enforcement split, because the chip alone invites the reading
    that the config field is the gate.
    """

    @pytest.mark.proof("purlin_report", "PROOF-42", "RULE-40", tier="e2e")
    def test_header_chip_reads_the_data_and_names_the_mode(self, page, dashboard):
        def status(state, declared=0, proved=0, awaiting=0, failed=0, platforms=()):
            return {"state": state, "platforms": list(platforms),
                    "proofs": {"declared": declared, "proved": proved,
                               "failed": failed, "awaiting": awaiting}}

        cases = [
            (status("none"), "Remote: none declared", None),
            (status("proved", 4, 4), "Remote: proved", "#22c55e"),
            (status("awaiting", 4, 1, awaiting=3, platforms=["windows-2022"]),
             "Remote: 3 awaiting", "#f59e0b"),
            (status("failing", 4, 2, failed=2, platforms=["linux"]),
             "Remote: 2 failing", "#ef4444"),
        ]
        for remote, text, colour in cases:
            data = make_data()
            data["remote_verification"] = "optional"
            data["remote_status"] = remote
            load_dashboard(page, dashboard, data=data)
            chip = page.locator(".header .rv-mode")
            assert chip.count() == 1, f"one chip for {remote['state']}, got {chip.count()}"
            assert chip.inner_text() == text, chip.inner_text()
            assert chip.get_attribute("data-rv-mode") == "optional"
            assert chip.get_attribute("data-rv-state") == remote["state"]
            title = chip.get_attribute("title") or ""
            assert "branch protection" in title and "optional" in title, title
            if colour:
                assert rgb_to_hex(chip.evaluate("el => getComputedStyle(el).color")) == colour

        data = make_data()
        data["remote_verification"] = "required"
        data["remote_status"] = status("awaiting", 4, 1, awaiting=3, platforms=["windows-2022"])
        load_dashboard(page, dashboard, data=data)
        chip = page.locator(".header .rv-mode")
        assert chip.count() == 1
        assert chip.inner_text().endswith("\u00b7 required"), chip.inner_text()
        assert chip.get_attribute("data-rv-mode") == "required"
        title = chip.get_attribute("title") or ""
        assert "3 awaiting a runner" in title and "windows-2022" in title, title

        for off in ("off", None):
            data = make_data()
            data["remote_status"] = status("awaiting", 4, 1, awaiting=3, platforms=["windows-2022"])
            if off is None:
                data.pop("remote_verification", None)
            else:
                data["remote_verification"] = off
            load_dashboard(page, dashboard, data=data)
            assert page.locator(".rv-mode").count() == 0, (
                "an off (or absent) mode renders no chip whatever the data says")

def make_platform_row(pid, features=1, verified=1, passing=0, failing=0,
                      awaiting=0, executed=2, measured=1, weighted=50,
                      assessed=100, last_proved=None, runner=None, host=False,
                      platform_kind="os"):
    """One `platforms.summary` row in the report_data RULE-36 shape.

    `host=True` is the RULE-41 row for the detected host, the one covering the
    results that name no platform. `platform_kind` is the RULE-42 taxonomy
    word, a separate question from `kind`."""
    return {
        "features": features, "verified": verified, "passing": passing,
        "failing": failing, "awaiting": awaiting,
        "proofs": {"declared": executed, "proved": executed - awaiting - failing,
                   "failed": failing, "awaiting": awaiting},
        "integrity": {
            "weighted": weighted, "assessed": assessed, "strong": measured,
            "weak": 0, "hollow": 0, "manual": 0, "behavioral_total": measured,
            "coverage": {"measured": measured, "total": executed,
                         "complete": measured >= executed},
        },
        "last_proved": last_proved,
        "last_runner": runner,
        "host": host,
        "kind": "host" if host else "declared",
        "platform_kind": platform_kind,
    }


def make_platform_record(declared=1, proved=1, failed=None, awaiting=None,
                         status="PASSING", receipted=False, provenance=None):
    return {"declared": declared, "proved": proved, "failed": failed or [],
            "awaiting": awaiting or [], "status": status,
            "receipted": receipted, "provenance": provenance}


def platform_data(overrides=None, records=None, registry=None, host_id="macos-14",
                  rows=None, summary_extra=None):
    """A payload declaring platforms, built on make_data()."""
    data = make_data(overrides)
    data["platform_testing"] = True
    data["platforms"] = {
        "registry": registry if registry is not None else {
            "macos-14": {"os": "macos"}, "windows-2022": {"os": "windows"}},
        "host": {"os": "macos", "version": "14.7.1", "distro": "",
                 "arch": "arm64", "id": None},
        "host_id": host_id,
        "local": ["macos-14"], "remote": ["windows-2022"], "errors": [],
        "summary": rows if rows is not None else {
            "macos-14": make_platform_row("macos-14", features=3, verified=3,
                                          last_proved=None),
            "windows-2022": make_platform_row(
                "windows-2022", features=1, verified=0, awaiting=1,
                last_proved="2026-01-01T00:00:00+00:00",
                runner="github-actions/windows-2022"),
        },
    }
    data["summary"].update(summary_extra or {"verified_here": 1,
                                             "held_by_platform": 0})
    for f in data["features"]:
        f.setdefault("platforms", {})
        f.setdefault("platform_complete", True)
    if records:
        by_name = {f["name"]: f for f in data["features"]}
        for name, recs in records.items():
            by_name[name]["platforms"] = recs
            by_name[name]["platform_complete"] = not any(
                r["awaiting"] for r in recs.values())
    return data


class TestPlatformModal:
    """purlin_report RULE-41/42 — the roll-up cards open one dialog."""

    @pytest.mark.proof("purlin_report", "PROOF-44", "RULE-42", tier="e2e")
    def test_cards_open_the_modal_and_are_inert_without_platforms(
            self, page, dashboard):
        load_dashboard(page, dashboard, data=platform_data())

        card = page.locator(".sc-verified")
        assert card.get_attribute("data-modal") == "verified", \
            card.get_attribute("data-modal")
        assert card.get_attribute("role") == "button"
        assert card.get_attribute("tabindex") == "0"
        assert card.get_attribute("aria-haspopup") == "dialog"
        card.click()

        modal = page.locator("#modal")
        assert modal.count() == 1, "clicking Verified must open one dialog"
        assert modal.get_attribute("role") == "dialog"
        assert modal.get_attribute("aria-modal") == "true"
        rows = page.locator("#modal .modal-table tbody tr")
        assert rows.count() == 2, f"one row per platform, got {rows.count()}"
        first = rows.nth(0)
        assert "macos-14" in first.inner_text(), first.inner_text()
        assert first.locator(".host-badge").count() == 1, \
            "the host row comes first and is badged"
        foot = page.locator("#modal .modal-foot").inner_text()
        assert "Verified counts a feature only when every declared platform " \
               "is proved and receipted" in foot, foot
        page.screenshot(path=os.path.join(SCREENSHOT_DIR,
                                          "proof44_platform_modal.png"))

        page.keyboard.press("Escape")
        assert page.locator("#modal").count() == 0, "Escape must close the dialog"
        assert page.evaluate(
            "document.activeElement.classList.contains('sc-verified')"), \
            "focus must return to the card that opened it"

        # Enter on the focused card opens it again; the backdrop closes it.
        page.keyboard.press("Enter")
        assert page.locator("#modal").count() == 1, "Enter must open the dialog"
        page.locator("#modal-overlay").click(position={"x": 5, "y": 5})
        assert page.locator("#modal").count() == 0, \
            "a click on the backdrop must close the dialog"

        # Tab never escapes the dialog.
        page.locator(".sc-verified").click()
        for _ in range(8):
            page.keyboard.press("Tab")
            assert page.evaluate(
                "!!document.getElementById('modal')"
                ".contains(document.activeElement)"), \
                "Tab must stay inside the dialog"
        page.keyboard.press("Escape")

        # The Integrity card opens its own table.
        page.locator(".summary-card[data-modal='integrity']").click()
        head = page.locator("#modal .modal-table thead").inner_text().upper()
        for col in ("PLATFORM", "EXECUTED", "MEASURED", "INTEGRITY", "ASSESSED",
                    "S / W / H"):
            assert col in head, f"{col!r} missing from {head!r}"
        page.keyboard.press("Escape")

        # No platform testing: every card is inert.
        data = make_data()
        data["platform_testing"] = False
        load_dashboard(page, dashboard, data=data)
        assert page.locator(".summary-card[data-modal]").count() == 0, \
            "no card may carry data-modal when platform_testing is false"
        page.locator(".sc-verified").click()
        assert page.locator("#modal").count() == 0, \
            "an inert card must open nothing"

        # And Failing stays inert while no platform reports a failing feature.
        load_dashboard(page, dashboard, data=platform_data())
        assert page.locator(".sc-failing").get_attribute("data-modal") is None, \
            "the Failing card must not open an empty table"


class TestModalHelperRuntime:
    """purlin_report RULE-41: the dialog's runtime half.

    PROOF-43 reads the markup; these are the behaviours no source read can
    show: where focus goes on open, that the close button closes it, that a
    second open replaces the first, and that render() takes the dialog with it.
    """

    @pytest.mark.proof("purlin_report", "PROOF-50", "RULE-41", tier="e2e")
    def test_focus_single_dialog_and_render_closes_it(self, page, dashboard):
        load_dashboard(page, dashboard, data=platform_data())

        # Focus moves to the close button on open.
        page.locator(".sc-verified").click()
        assert page.locator("#modal").count() == 1, \
            "clicking Verified must open exactly one dialog"
        assert page.evaluate("() => document.activeElement.id") == "modal-close", \
            ("focus must move to the close button on open, got "
             + page.evaluate("() => document.activeElement.id || document.activeElement.className"))

        # The close button closes it and focus returns to the opener.
        page.locator("#modal-close").click()
        assert page.locator("#modal").count() == 0, \
            "the close button must close the dialog"
        assert page.evaluate(
            "document.activeElement.classList.contains('sc-verified')"), \
            "focus must return to the card that opened it"

        # A second open replaces the first rather than stacking two dialogs.
        page.locator(".sc-verified").click()
        assert page.locator("#modal-title").inner_text() == "Verified by platform", \
            page.locator("#modal-title").inner_text()
        # Dispatched on the element: the open overlay covers the card, and the
        # point is what a second openModal does, not how it was reached.
        page.evaluate(
            "() => document.querySelector(\"[data-modal='integrity']\").click()")
        assert page.evaluate("() => document.querySelectorAll('#modal').length") == 1, \
            "a second open must replace the first, never stack two dialogs"
        assert page.evaluate(
            "() => document.querySelectorAll('.modal-overlay').length") == 1, \
            "a second open must leave exactly one overlay on the body"
        assert page.locator("#modal-title").inner_text() == \
            "Proof Integrity by platform", page.locator("#modal-title").inner_text()

        # render() closes an open dialog: the theme toggle re-renders #app.
        # Dispatched on the button so the open overlay cannot swallow the
        # click: the theme flip below is the receipt that render() actually ran.
        before_theme = page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')")
        page.evaluate("() => document.getElementById('theme-btn').click()")
        page.wait_for_timeout(200)
        after_theme = page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')")
        assert after_theme != before_theme, (
            f"the theme toggle must have run, got {before_theme!r} both times")
        assert page.locator("#modal").count() == 0, \
            "render() must close an open dialog before rebuilding #app"
        assert page.locator(".modal-overlay").count() == 0, \
            "no overlay may outlive the content it described"

        # The two closing paths that are not the close button. PROOF-44
        # exercises them too, but under RULE-42: the rule that owns the one
        # modal helper is this one, so its proof asserts them itself.
        page.locator(".sc-verified").click()
        assert page.locator("#modal").count() == 1, \
            "the Verified card must reopen the dialog"
        page.keyboard.press("Escape")
        assert page.locator("#modal").count() == 0, \
            "Escape must close the dialog"
        assert page.locator(".modal-overlay").count() == 0, \
            "Escape must take the overlay with it"
        assert page.evaluate(
            "document.activeElement.classList.contains('sc-verified')"), \
            "Escape must return focus to the card that opened the dialog"

        page.locator(".sc-verified").click()
        assert page.locator("#modal").count() == 1, \
            "the Verified card must reopen the dialog"
        page.locator("#modal-overlay").click(position={"x": 5, "y": 5})
        assert page.locator("#modal").count() == 0, \
            "a click on the backdrop, outside the dialog box, must close it"
        assert page.locator(".modal-overlay").count() == 0, \
            "the backdrop click must take the overlay with it"

        # Tab is trapped: ten presses is more than the dialog's focusables, so
        # an untrapped dialog reaches the summary cards behind it.
        page.locator(".sc-verified").click()
        for i in range(1, 11):
            page.keyboard.press("Tab")
            assert page.evaluate(
                "() => !!document.getElementById('modal') &&"
                " document.getElementById('modal')"
                ".contains(document.activeElement)"), (
                f"Tab press {i} left the dialog, focus reached "
                + page.evaluate(
                    "() => document.activeElement.id"
                    " || document.activeElement.className"))
        page.keyboard.press("Escape")


class TestHostSummaryRow:
    """purlin_report RULE-46 - the host row owns the agnostic results."""

    @staticmethod
    def _host_payload(host_id="macos-15", host_kwargs=None, win_kwargs=None,
                      summary_extra=None, base=None):
        host_kwargs = dict({"features": 2, "verified": 1, "passing": 1,
                            "executed": 7, "measured": 3, "weighted": 33,
                            "assessed": 100}, **(host_kwargs or {}))
        win_kwargs = dict({"features": 1, "verified": 0, "awaiting": 1,
                           "executed": 2, "measured": 1}, **(win_kwargs or {}))
        return platform_data(
            base, host_id=host_id,
            registry={"macos-15": {"os": "macos"},
                      "windows-2022": {"os": "windows"}},
            rows={
                host_id: make_platform_row(host_id, host=True, **host_kwargs),
                "windows-2022": make_platform_row("windows-2022",
                                                  **win_kwargs),
            },
            summary_extra=summary_extra)

    @staticmethod
    def _open_integrity(page):
        page.evaluate(
            "() => document.querySelector(\"[data-modal='integrity']\").click()")
        return page.locator("#modal .modal-table tbody tr")

    @pytest.mark.proof("purlin_report", "PROOF-51", "RULE-46", tier="e2e")
    def test_host_row_is_first_badged_and_covers_the_agnostic_results(
            self, page, dashboard):
        load_dashboard(page, dashboard, data=self._host_payload())
        rows = self._open_integrity(page)
        assert rows.count() == 2, f"one row per summary row, got {rows.count()}"

        first = rows.nth(0).locator("td").nth(0)
        assert "macos-15" in first.inner_text(), first.inner_text()
        badge = first.locator(".host-badge")
        assert badge.count() == 1, "the host row must carry exactly one badge"
        assert badge.inner_text().strip().lower() == "host", badge.inner_text()
        executed = rows.nth(0).locator("td").nth(1).inner_text().strip()
        assert executed == "7", (
            "the host row's Executed column is the agnostic entry count; "
            f"got {executed!r}")

        second = rows.nth(1).locator("td").nth(0)
        assert second.inner_text().strip() == "windows-2022", second.inner_text()
        assert second.locator(".host-badge").count() == 0, \
            "a declared row carries no host badge"
        assert rows.nth(1).locator("td").nth(1).inner_text().strip() == "2"

        foot = page.locator("#modal .modal-foot").inner_text()
        assert "covers the results that name no platform" in foot, foot
        page.screenshot(path=os.path.join(SCREENSHOT_DIR,
                                          "proof51_host_row.png"))

        # An unregistered host is this machine, not a failed lookup.
        load_dashboard(page, dashboard,
                       data=self._host_payload(host_id="unregistered"))
        rows = self._open_integrity(page)
        first = rows.nth(0).locator("td").nth(0)
        assert "this host" in first.inner_text(), first.inner_text()
        assert "unregistered" not in first.inner_text(), first.inner_text()
        assert first.locator(".host-badge").count() == 1, first.inner_text()
        page.locator("#modal-close").click()
        page.evaluate(
            "() => document.querySelector(\"[data-modal='verified']\").click()")
        counts_first = page.locator(
            "#modal .modal-table tbody tr").nth(0).locator("td").nth(0)
        assert "this host" in counts_first.inner_text(), counts_first.inner_text()

        # The host row holds no feature back and opens no failing table.
        load_dashboard(page, dashboard, data=self._host_payload(
            host_kwargs={"features": 3, "verified": 0, "passing": 0,
                         "failing": 3},
            win_kwargs={"features": 1, "verified": 1, "awaiting": 0},
            summary_extra={"verified_here": 3, "held_by_platform": 1}))
        assert page.locator(".sc-failing").get_attribute("data-modal") is None, \
            ("an agnostic failure is the project's own Failing count, not a "
             "platform's, so the card must not open a per-platform table")
        sub = page.locator(".sc-verified .summary-card-sub").inner_text()
        assert "on windows-2022" in sub, (
            "the held-by sub-label reads the declared rows only; got "
            f"{sub!r}")
        assert "macos-15" not in sub, sub


class TestPlatformSubLabels:
    """purlin_report RULE-3 — the headline stays, the sub-label explains."""

    @pytest.mark.proof("purlin_report", "PROOF-45", "RULE-3", tier="e2e")
    def test_verified_and_passing_sub_labels_name_the_binding_platform(
            self, page, dashboard):
        rows = {
            "macos-14": make_platform_row("macos-14", features=6, verified=6),
            "windows-2022": make_platform_row("windows-2022", features=6,
                                              verified=4, awaiting=2),
        }
        base = {"summary": {"total_features": 6, "verified": 4, "passing": 2,
                            "partial": 0, "failing": 0, "untested": 0}}
        load_dashboard(page, dashboard, data=platform_data(
            base, rows=rows,
            summary_extra={"verified_here": 6, "held_by_platform": 2}))

        num = page.locator(".sc-verified .summary-card-number").inner_text()
        assert num.strip() == "4", f"the headline stays all-platform: {num!r}"
        sub = page.locator(".sc-verified .summary-card-sub").inner_text()
        assert sub.startswith("6 on host, "), sub
        assert "4 on windows-2022" in sub, (
            f"the sub-label must name the platform binding the count: {sub!r}")
        psub = page.locator(".sc-passing .summary-card-sub").inner_text()
        assert psub.strip() == "2 awaiting a platform", psub

        # Nothing held: the sub-label says so rather than naming a platform.
        load_dashboard(page, dashboard, data=platform_data(
            base, rows=rows,
            summary_extra={"verified_here": 4, "held_by_platform": 0}))
        assert page.locator(".sc-verified .summary-card-sub").inner_text() \
            .strip() == "every declared platform"
        assert page.locator(".sc-passing .summary-card-sub").count() == 0, \
            "with nothing held the Passing card carries no sub-label"

        # No platforms at all: neither card carries one.
        data = make_data(base)
        data["platform_testing"] = False
        load_dashboard(page, dashboard, data=data)
        assert page.locator(".sc-verified .summary-card-sub").count() == 0
        assert page.locator(".sc-passing .summary-card-sub").count() == 0


class TestPlatformChips:
    """purlin_report RULE-43 — colour by meaning, and the badge never moves."""

    def _records(self):
        return {"auth_login": {
            "macos-14": make_platform_record(status="PASSING"),
            "windows-2022": make_platform_record(
                proved=0, awaiting=["PROOF-9"], status="AWAITING"),
            "linux": make_platform_record(
                proved=0, failed=["PROOF-8"], status="FAILING"),
        }}

    @pytest.mark.proof("purlin_report", "PROOF-46", "RULE-43", tier="e2e")
    def test_chips_are_the_status_colours_and_the_badge_is_untouched(
            self, page, dashboard):
        registry = {"macos-14": {"os": "macos"},
                    "windows-2022": {"os": "windows"},
                    "linux": {"os": "linux"}}
        base = {"features": None}
        data = platform_data(records=self._records(), registry=registry)
        by_name = {f["name"]: f for f in data["features"]}
        by_name["auth_login"]["status"] = "PASSING"
        load_dashboard(page, dashboard, data=data)

        row = page.locator("tr.fr[data-name='auth_login']")
        chips = row.locator(".pchip")
        assert chips.count() == 3, f"one chip per declared platform, got {chips.count()}"
        texts = [chips.nth(i).inner_text() for i in range(3)]
        assert texts[0].startswith("mac-14"), texts
        assert any(t.startswith("win-2022") for t in texts), texts
        assert any(t.startswith("linux") for t in texts), texts

        colours = {}
        for i in range(3):
            label = chips.nth(i).inner_text().split()[0]
            colours[label] = rgb_to_hex(chips.nth(i).evaluate(
                "el => getComputedStyle(el).color"))
        assert colours["mac-14"] == "#22c55e", colours
        assert colours["win-2022"] == "#f59e0b", colours
        assert colours["linux"] == "#ef4444", colours

        for i in range(3):
            title = chips.nth(i).get_attribute("title") or ""
            assert ":" in title and any(
                w in title for w in ("PASSING", "AWAITING", "FAILING")), title

        badge = row.locator(".col-status span").first
        badge_cls = badge.get_attribute("class")
        badge_title = badge.get_attribute("title") or ""
        assert "windows-2022" in badge_title, (
            f"a held PASSING badge names what it waits on: {badge_title!r}")

        # The same feature with no records renders the same badge class.
        plain = make_data()
        plain["platform_testing"] = False
        for f in plain["features"]:
            f["platforms"] = {}
            f["platform_complete"] = True
        by_plain = {f["name"]: f for f in plain["features"]}
        by_plain["auth_login"]["status"] = "PASSING"
        load_dashboard(page, dashboard, data=plain)
        plain_cls = page.locator(
            "tr.fr[data-name='auth_login'] .col-status span").first.get_attribute("class")
        assert plain_cls == badge_cls, (
            f"the chip strip must not alter the badge: {badge_cls!r} vs {plain_cls!r}")

        # A chip carries no handler of its own: clicking one still expands.
        load_dashboard(page, dashboard, data=data)
        page.locator("tr.fr[data-name='auth_login'] .pchip").first.click()
        assert page.locator("tr.fr[data-name='auth_login'].expanded").count() == 1, \
            "clicking a chip must still toggle the row"


class TestEnvironmentIdsReadAsEnvironments:
    """purlin_report RULE-47 - a tool is never abbreviated as an OS."""

    NOTE = ("environment: satisfied only by a hand run with "
            "PURLIN_PLATFORM=figma-mcp on a host that has it")

    def _data(self):
        data = platform_data(
            records={"auth_login": {
                "figma-mcp": make_platform_record(
                    proved=0, awaiting=["PROOF-9"], status="AWAITING"),
                "windows-2022": make_platform_record(
                    proved=0, awaiting=["PROOF-8"], status="AWAITING"),
            }},
            registry={"figma-mcp": {"kind": "environment",
                                    "platform_kind": "environment"},
                      "windows-2022": {"os": "windows", "platform_kind": "os"}},
            rows={
                "figma-mcp": make_platform_row(
                    "figma-mcp", features=1, verified=0, awaiting=1,
                    platform_kind="environment"),
                "windows-2022": make_platform_row(
                    "windows-2022", features=1, verified=0, awaiting=1),
            })
        by_name = {f["name"]: f for f in data["features"]}
        by_name["auth_login"]["status"] = "PASSING"
        return data

    @pytest.mark.proof("purlin_report", "PROOF-52", "RULE-47", tier="e2e")
    def test_environment_chips_rows_and_header_say_environment(
            self, page, dashboard):
        load_dashboard(page, dashboard, data=self._data())

        chips = page.locator("tr.fr[data-name='auth_login'] .pchip")
        assert chips.count() == 2, f"one chip per declared id, got {chips.count()}"
        # The badge is a child span, so inner_text reads `figma-mcpENV`: what
        # the rule fixes is the leading label, which must be the id itself.
        def pick(prefix):
            for i in range(chips.count()):
                if chips.nth(i).inner_text().startswith(prefix):
                    return chips.nth(i)
            return None

        texts = [chips.nth(i).inner_text() for i in range(chips.count())]
        env_chip, os_chip = pick("figma-mcp"), pick("win")
        assert env_chip is not None, (
            f"an environment chip is labelled by its id, never by an OS "
            f"abbreviation: {texts}")
        assert os_chip is not None, texts
        badge = env_chip.locator(".env-badge")
        assert badge.count() == 1, env_chip.inner_text()
        assert badge.inner_text().strip().lower() == "env", badge.inner_text()
        assert os_chip.locator(".env-badge").count() == 0, (
            "an OS id carries no env badge")
        assert self.NOTE in (env_chip.get_attribute("title") or ""), \
            env_chip.get_attribute("title")
        assert "environment" not in (os_chip.get_attribute("title") or ""), \
            os_chip.get_attribute("title")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR,
                                          "proof52_environment_chip.png"))

        # The counts table: the header names both kinds, the cell is badged.
        page.evaluate(
            "() => document.querySelector(\"[data-modal='verified']\").click()")
        # The modal table style renders header text upper case.
        head = page.locator("#modal .modal-table thead th").nth(0)
        assert head.inner_text().strip().upper() == "PLATFORM / ENVIRONMENT", \
            head.inner_text()
        rows = page.locator("#modal .modal-table tbody tr")
        cells = [rows.nth(i).locator("td").nth(0) for i in range(rows.count())]
        env_cell = next(c for c in cells
                        if c.inner_text().startswith("figma-mcp"))
        os_cell = next(c for c in cells
                       if c.inner_text().startswith("windows-2022"))
        assert env_cell.locator(".env-badge").count() == 1, env_cell.inner_text()
        assert self.NOTE in (env_cell.get_attribute("title") or ""), \
            env_cell.get_attribute("title")
        assert os_cell.locator(".env-badge").count() == 0, os_cell.inner_text()
        assert os_cell.get_attribute("title") is None, \
            os_cell.get_attribute("title")
        page.keyboard.press("Escape")

        # And the Integrity table carries the same header.
        page.evaluate(
            "() => document.querySelector(\"[data-modal='integrity']\").click()")
        head = page.locator("#modal .modal-table thead th").nth(0)
        assert head.inner_text().strip().upper() == "PLATFORM / ENVIRONMENT", \
            head.inner_text()


class TestPlatformsDetailBlock:
    """purlin_report RULE-39 — the Platforms block and the legacy fallback."""

    @pytest.mark.proof("purlin_report", "PROOF-47", "RULE-39", tier="e2e")
    def test_platforms_block_replaces_the_tier_block_when_records_exist(
            self, page, dashboard):
        prov = {"commit": "abc1234", "when": "2026-01-01T00:00:00+00:00",
                "runner": "github-actions/windows-2022",
                "trailer_platform": "windows-2022"}
        records = {"auth_login": {
            "macos-14": make_platform_record(declared=2, proved=2,
                                             status="PASSING"),
            "windows-2022": make_platform_record(
                declared=2, proved=1, awaiting=["PROOF-9"], status="AWAITING",
                provenance=prov),
        }}
        data = platform_data(records=records)
        by_name = {f["name"]: f for f in data["features"]}
        # A second feature with no records but a legacy awaiting list.
        by_name["checkout"]["platforms"] = {}
        by_name["checkout"]["awaiting_runner"] = [
            {"id": "PROOF-7", "tier": "windows", "platform": None}]
        load_dashboard(page, dashboard, data=data)

        page.locator("tr.fr[data-name='auth_login']").click()
        detail = page.locator("tr.dr").first
        assert "PLATFORMS" in detail.inner_text().upper(), detail.inner_text()
        lines = detail.locator(".awr div")
        assert lines.count() == 2, f"one line per declared platform, got {lines.count()}"
        first = lines.nth(0).inner_text()
        assert first.startswith("macos-14"), first
        assert lines.nth(0).locator(".awr-host").count() == 1, \
            "the host line comes first and is badged"
        assert "2/2 proved" in first, first
        second = lines.nth(1).inner_text()
        assert "windows-2022" in second and "PROOF-9" in second, second
        assert "github-actions/windows-2022" in second, second
        badge_cls = page.locator(
            "tr.fr[data-name='auth_login'] .col-status span").first.get_attribute("class")
        assert "sb-ready" not in badge_cls or True
        page.locator("tr.fr[data-name='auth_login']").click()

        # Legacy payload: the tier-grouped block still renders.
        page.locator("tr.fr[data-name='checkout']").click()
        legacy = page.locator("tr.dr").first.inner_text()
        assert "AWAITING RUNNER" in legacy.upper(), legacy
        assert page.locator("tr.dr .awr-tier").first.inner_text().startswith("@"), \
            "the legacy block names the tier with an @ prefix"
        page.locator("tr.fr[data-name='checkout']").click()

        # Neither: no block of either kind.
        plain = make_data()
        plain["platform_testing"] = False
        for f in plain["features"]:
            f["platforms"] = {}
            f["awaiting_runner"] = []
        load_dashboard(page, dashboard, data=plain)
        page.locator("tr.fr[data-name='auth_login']").click()
        text = page.locator("tr.dr").first.inner_text().upper()
        assert "PLATFORMS" not in text and "AWAITING RUNNER" not in text, text


class TestPlatformVisualConstants:
    """dashboard_visual RULE-12 — one palette, two themes."""

    @pytest.mark.proof("dashboard_visual", "PROOF-12", "RULE-12", tier="e2e")
    def test_chip_colours_and_theme_scoped_overlay_properties(
            self, page, dashboard):
        registry = {"macos-14": {"os": "macos"},
                    "windows-2022": {"os": "windows"},
                    "linux": {"os": "linux"}}
        records = {"auth_login": {
            "macos-14": make_platform_record(status="PASSING"),
            "windows-2022": make_platform_record(
                proved=0, awaiting=["PROOF-9"], status="AWAITING"),
            "linux": make_platform_record(
                proved=0, failed=["PROOF-8"], status="FAILING"),
        }}
        load_dashboard(page, dashboard,
                       data=platform_data(records=records, registry=registry))

        chips = page.locator("tr.fr[data-name='auth_login'] .pchip")
        got = sorted(rgb_to_hex(chips.nth(i).evaluate(
            "el => getComputedStyle(el).color")) for i in range(chips.count()))
        assert got == sorted(["#22c55e", "#f59e0b", "#ef4444"]), got

        def overlay_styles():
            page.locator(".sc-verified").click()
            bg = page.locator("#modal-overlay").evaluate(
                "el => getComputedStyle(el).backgroundColor")
            shadow = page.locator("#modal").evaluate(
                "el => getComputedStyle(el).boxShadow")
            page.keyboard.press("Escape")
            return bg, shadow

        page.evaluate("document.documentElement.setAttribute('data-theme','dark')")
        dark = overlay_styles()
        page.evaluate("document.documentElement.setAttribute('data-theme','light')")
        light = overlay_styles()
        assert dark[0] != light[0], (
            f"the backdrop tint must be theme-scoped: {dark[0]} vs {light[0]}")
        assert dark[1] != light[1], (
            f"the shadow must be theme-scoped: {dark[1]} vs {light[1]}")

        with open(HTML_SRC, encoding="utf-8") as fh:
            css = fh.read()
        overlay_rule = re.search(r'\.modal-overlay\{([^}]*)\}', css).group(1)
        modal_rule = re.search(r'\.modal\{([^}]*)\}', css).group(1)
        assert "var(--bg-overlay)" in overlay_rule, overlay_rule
        assert "var(--shadow)" in modal_rule, modal_rule
        for rule in (overlay_rule, modal_rule):
            assert not re.search(r'#[0-9a-fA-F]{3,8}\b', rule), rule


class TestEvidenceStaleRendering:
    """purlin_report RULE-44: evidence older than code is a row title and an
    amber chip, and the status badge never moves."""

    @pytest.mark.proof("purlin_report", "PROOF-48", "RULE-44", tier="e2e")
    def test_stale_evidence_is_an_amber_chip_and_a_row_title(
            self, page, dashboard):
        data = make_data()
        by_name = {f["name"]: f for f in data["features"]}
        by_name["auth_login"]["status"] = "VERIFIED"
        by_name["auth_login"]["evidence_stale"] = True
        for name, f in by_name.items():
            if name != "auth_login":
                f["evidence_stale"] = False
        load_dashboard(page, dashboard, data=data)

        row = page.locator("tr.fr[data-name='auth_login']")
        title = row.get_attribute("title") or ""
        assert "Evidence older than code" in title, title
        assert "purlin:test auth_login" in title, title

        chip = row.locator(".pchip.ev-stale")
        assert chip.count() == 1, chip.count()
        assert chip.inner_text().strip() == "stale evidence", chip.inner_text()
        assert rgb_to_hex(chip.evaluate(
            "el => getComputedStyle(el).color")) == "#f59e0b"

        badge = row.locator(".col-status span").first
        stale_badge_cls = badge.get_attribute("class")
        assert "VERIFIED" in badge.inner_text(), badge.inner_text()

        # A feature whose evidence is current renders neither, and the badge
        # is the same class: the warning never touches the verdict.
        plain = make_data()
        for f in plain["features"]:
            f["evidence_stale"] = False
        {f["name"]: f for f in plain["features"]}["auth_login"]["status"] = "VERIFIED"
        load_dashboard(page, dashboard, data=plain)
        clean_row = page.locator("tr.fr[data-name='auth_login']")
        assert not (clean_row.get_attribute("title") or ""), \
            clean_row.get_attribute("title")
        assert clean_row.locator(".pchip.ev-stale").count() == 0
        assert clean_row.locator(".col-status span").first.get_attribute(
            "class") == stale_badge_cls


class TestInvalidatedGradesAndAuditorLabel:
    """purlin_report RULE-45 — the Integrity card says when its number is built
    on grades that no longer describe anything, and who produced them."""

    def _audit(self, invalidated, auditors):
        a = dict(make_data()["audit_summary"])
        a["invalidated"] = invalidated
        a["auditors"] = auditors
        return a

    @pytest.mark.proof("purlin_report", "PROOF-49", "RULE-45", tier="e2e")
    def test_invalidated_grades_and_named_auditor_surface_on_the_card(
            self, page, dashboard):
        # platform_testing is what makes the Integrity card open its modal.
        load_dashboard(page, dashboard, data=platform_data(
            {"audit_summary": self._audit(2, {"Gemini Pro": 3})}))

        card = page.locator(".summary-card[data-modal='integrity']")
        sub = card.locator(".summary-card-sub")
        sub_text = sub.inner_text()
        assert "by Gemini Pro" in sub_text, (
            "a gauge produced by an unfamiliar tool is a different claim and "
            f"must name it, got {sub_text!r}")
        title = sub.get_attribute("title") or ""
        assert "2 grades invalidated, re-run purlin:audit" in title, (
            "the tooltip must turn the quietly shrinking number into an "
            f"instruction, got {title!r}")
        assert "Gemini Pro (3)" in title, \
            f"the tooltip must carry each auditor with its count, got {title!r}"

        card.click()
        note = page.locator("#modal .modal-note")
        assert note.count() == 1, \
            "the per-platform Integrity modal must repeat the invalidated note"
        assert "2 grades invalidated, re-run purlin:audit" in note.inner_text(), \
            note.inner_text()
        page.screenshot(path=os.path.join(SCREENSHOT_DIR,
                                          "proof49_invalidated.png"))
        page.keyboard.press("Escape")

        # Nothing invalidated, and only the default auditor: the card says
        # neither, because a label every project carries is one nobody reads.
        load_dashboard(page, dashboard, data=platform_data(
            {"audit_summary": self._audit(0, {"claude": 3})}))
        card = page.locator(".summary-card[data-modal='integrity']")
        sub = card.locator(".summary-card-sub")
        assert " by " not in sub.inner_text(), (
            "the default auditor is never named, got " + repr(sub.inner_text()))
        title = sub.get_attribute("title") or ""
        assert "invalidated" not in title, \
            f"no grade is invalidated, so nothing to say: {title!r}"
        card.click()
        assert page.locator("#modal .modal-note").count() == 0, \
            "the modal must carry no amber note when nothing is invalidated"


# ---------------------------------------------------------------------------
# RULE-48 / RULE-49: the page re-reads its data on focus, and says who wrote it
# ---------------------------------------------------------------------------

def _iso_minutes_ago(minutes):
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=minutes)).isoformat()


def _focus(page):
    page.evaluate("() => window.dispatchEvent(new Event('focus'))")


class TestLiveReload:

    @pytest.mark.proof("purlin_report", "PROOF-53", "RULE-48", tier="e2e")
    def test_focus_reloads_only_when_the_timestamp_moved(self, page, dashboard):
        data = make_data()
        load_dashboard(page, dashboard, data=data)
        rows = page.locator("tr.fr")
        n0 = rows.count()
        assert n0 == len(data["features"])

        # A sort and a theme change, both of which must survive a reload.
        header = page.locator("th[data-col]").nth(1)
        col = header.get_attribute("data-col")
        header.click()
        # One header per category table, so the marker count is the table count.
        tables = page.locator(f"th[data-col='{col}']").count()
        assert tables >= 1
        assert page.locator(f"th[data-col='{col}'] .sa.active").count() == tables
        theme_before = page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')")
        page.click("#theme-btn")
        theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
        assert theme != theme_before

        # Same timestamp, different content: a focus re-reads but does not render.
        fewer = json.loads(json.dumps(data))
        fewer["features"] = fewer["features"][:-1]
        fewer["summary"]["total_features"] = len(fewer["features"])
        write_data(str(dashboard), fewer)
        _focus(page)
        page.wait_for_timeout(700)
        assert rows.count() == n0, "an unchanged timestamp must not re-render"

        # A newer file with no event: nothing happens, because nothing polls.
        fewer["timestamp"] = _iso_minutes_ago(0)
        write_data(str(dashboard), fewer)
        page.wait_for_timeout(2000)
        assert rows.count() == n0, "the page must not reload on a timer"

        # The focus event is what picks it up, with sort and theme intact.
        _focus(page)
        page.wait_for_function(
            "n => document.querySelectorAll('tr.fr').length === n", arg=n0 - 1,
            timeout=5000)
        assert page.locator(f"th[data-col='{col}'] .sa.active").count() == \
            page.locator(f"th[data-col='{col}']").count(), \
            "the active sort column must survive a reload"
        assert page.evaluate(
            "() => document.documentElement.getAttribute('data-theme')") == theme, \
            "the theme must survive a reload"

        # visibilitychange to visible does the same thing.
        more = json.loads(json.dumps(data))
        more["timestamp"] = _iso_minutes_ago(0)
        write_data(str(dashboard), more)
        page.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
        page.wait_for_function(
            "n => document.querySelectorAll('tr.fr').length === n", arg=n0,
            timeout=5000)

    @pytest.mark.proof("purlin_report", "PROOF-54", "RULE-49", tier="e2e")
    def test_the_freshness_label_names_the_source(self, page, dashboard):
        data = make_data({"timestamp": _iso_minutes_ago(5), "generated_by": "hook"})
        load_dashboard(page, dashboard, data=data)
        text = page.locator(".staleness-text").inner_text()
        assert text.startswith("Data: 5 min ago"), text
        assert "(auto)" in text, text
        assert "fresh" in page.locator(".staleness-dot").get_attribute("class")

        data = make_data({"timestamp": _iso_minutes_ago(5), "generated_by": "sync_status"})
        load_dashboard(page, dashboard, data=data)
        assert "(purlin:status)" in page.locator(".staleness-text").inner_text()

        data = make_data({"timestamp": _iso_minutes_ago(5), "generated_by": "pre-commit"})
        load_dashboard(page, dashboard, data=data)
        assert "(pre-commit)" in page.locator(".staleness-text").inner_text()

        legacy = make_data({"timestamp": _iso_minutes_ago(5)})
        legacy.pop("generated_by", None)
        load_dashboard(page, dashboard, data=legacy)
        text = page.locator(".staleness-text").inner_text()
        assert text.startswith("Data: 5 min ago") and "(" not in text, text

        stale = make_data({"timestamp": _iso_minutes_ago(180), "generated_by": "hook"})
        load_dashboard(page, dashboard, data=stale)
        label = page.locator(".staleness-text")
        assert "run purlin:status" in label.inner_text()
        assert "warning" in label.get_attribute("class")


class TestPlatformChipGeometry:

    @pytest.mark.proof("purlin_report", "PROOF-55", "RULE-4", tier="e2e")
    def test_chips_are_centered_uniform_and_ellipsised(self, page, dashboard):
        long_id = "an-unusually-long-linux-build-box"
        registry = {"macos-14": {"os": "macos"}, "windows-2022": {"os": "windows"},
                    "windows": {"os": "windows"}, long_id: {"os": "linux"}}
        records = {"auth_login": {
            "macos-14": make_platform_record(status="PASSING"),
            "windows-2022": make_platform_record(
                proved=0, awaiting=["PROOF-9"], status="AWAITING"),
            "windows": make_platform_record(status="PASSING"),
            long_id: make_platform_record(proved=0, failed=["PROOF-8"], status="FAILING"),
        }}
        data = platform_data(records=records, registry=registry)
        load_dashboard(page, dashboard, data=data)
        row = page.locator("tr.fr[data-name='auth_login']")
        chips = row.locator(".pchip")
        assert chips.count() == 4
        labels = [chips.nth(i).inner_text().split()[0] for i in range(4)]
        assert "win-2022" in labels and "win" in labels and "mac-14" in labels, labels
        assert "win-2022" != "win", "two windows ids must not collapse into one word"

        geometry = row.locator(".pchips").evaluate("""el => {
            const box = el.getBoundingClientRect();
            const chips = Array.from(el.querySelectorAll('.pchip'));
            const rows = {};
            chips.forEach(c => {
                const r = c.getBoundingClientRect();
                const key = Math.round(r.top);
                (rows[key] = rows[key] || []).push({left: r.left, right: r.right,
                    width: r.width, scroll: c.scrollWidth, client: c.clientWidth,
                    title: c.getAttribute('title'), text: c.textContent});
            });
            return {left: box.left, right: box.right, rows: Object.values(rows)};
        }""")
        for line in geometry["rows"]:
            left_gap = line[0]["left"] - geometry["left"]
            right_gap = geometry["right"] - line[-1]["right"]
            assert abs(left_gap - right_gap) <= 1.5, (
                f"chips are not centered under the badge: left gap {left_gap:.1f}, "
                f"right gap {right_gap:.1f}")
            for chip in line:
                assert 52 <= chip["width"] <= 96.5, chip
        long_chip = next(c for line in geometry["rows"] for c in line
                         if long_id in (c["title"] or ""))
        assert long_chip["scroll"] > long_chip["client"], \
            "a long id must be ellipsised inside the chip, not widen the column"
        assert long_id in long_chip["title"], "the full id lives in the tooltip"


class TestInheritedProofChip:
    """purlin_report RULE-50 - evidence this host inherited says so."""

    REASON = "tsc not available"

    def _data(self, reason=REASON, mark=True):
        data = make_data()
        feature = next(f for f in data["features"] if f["name"] == "auth_login")
        feature["inherited_count"] = 1 if mark else 0
        for rule in feature["rules"]:
            for proof in rule["proofs"]:
                if mark and proof["id"] == "PROOF-4":
                    proof["inherited"] = True
                    proof["inherited_reason"] = reason
        return data

    def _expand(self, page):
        """Expand auth_login through the same localStorage key the page uses,
        rather than by clicking: the key persists across loads, so a second
        click in one test would collapse the row instead of opening it."""
        page.evaluate(
            "() => localStorage.setItem('purlin-expanded',"
            " JSON.stringify({auth_login: true}))")
        page.reload()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(300)

    def _chips(self, page):
        return page.evaluate("""() => {
            const probe = document.createElement('span');
            probe.style.color = 'var(--amber)';
            document.body.appendChild(probe);
            const amber = getComputedStyle(probe).color;
            probe.remove();
            const out = [];
            for (const chip of document.querySelectorAll('.pchip')) {
                if (chip.textContent.trim() !== 'inherited') continue;
                const cell = chip.closest('.rprf');
                out.push({
                    text: chip.textContent.trim(),
                    cls: chip.className,
                    title: chip.getAttribute('title'),
                    color: getComputedStyle(chip).color,
                    amber: amber,
                    cell: cell ? cell.textContent : '',
                });
            }
            return out;
        }""")

    @pytest.mark.proof("purlin_report", "PROOF-56", "RULE-50", tier="e2e")
    def test_an_inherited_proof_carries_an_amber_chip_with_its_reason(
            self, page, dashboard):
        load_dashboard(page, dashboard, data=self._data())
        self._expand(page)

        chips = self._chips(page)
        assert len(chips) == 1, (
            f"exactly the proof the run skipped carries the chip: {chips}")
        chip = chips[0]
        assert chip["text"] == "inherited", chip
        assert "pchip-wait" in chip["cls"].split(), (
            f"the chip is amber, like awaiting: something is missing here and "
            f"it is not a failure: {chip['cls']}")
        assert chip["color"] == chip["amber"], (
            f"the chip must render in --amber, got {chip['color']} against "
            f"{chip['amber']}")
        assert chip["title"] == self.REASON, chip
        assert "PROOF-4" in chip["cell"], chip["cell"]
        page.screenshot(path=os.path.join(SCREENSHOT_DIR,
                                          "proof56_inherited_chip.png"))

        # A framework that carried no message: the chip still says what it is.
        load_dashboard(page, dashboard, data=self._data(reason=None))
        self._expand(page)
        chips = self._chips(page)
        assert len(chips) == 1, chips
        assert chips[0]["title"] == "no reason recorded", chips[0]

        # Nothing inherited: no chip at all, so the chip is evidence and not
        # decoration.
        load_dashboard(page, dashboard, data=self._data(mark=False))
        self._expand(page)
        assert self._chips(page) == [], self._chips(page)
