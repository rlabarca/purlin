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
            "ready": 1,
            "partial": 1,
            "failing": 0,
            "no_proofs": 1,
        },
        "features": [
            {
                "name": "auth_login",
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 3,
                "total": 3,
                "deferred": 0,
                "status": "READY",
                "structural_checks": 0,
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
                        "proofs": [{
                            "id": "PROOF-1",
                            "test_file": "tests/test_login.py",
                            "test_name": "test_valid",
                            "tier": "unit",
                            "status": "pass",
                        }],
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
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": 1,
                "total": 2,
                "deferred": 0,
                "status": "partial",
                "structural_checks": 0,
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
                "type": "anchor",
                "is_global": True,
                "source_url": "git@github.com:acme/policies.git",
                "proved": 2,
                "total": 2,
                "deferred": 0,
                "status": "READY",
                "structural_checks": 0,
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


def load_dashboard(page, dashboard_dir, data=None):
    """Write data and navigate to the dashboard."""
    if data is not None:
        write_data(str(dashboard_dir), data)
    url = f"file://{dashboard_dir}/purlin-report.html"
    page.goto(url)
    page.wait_for_load_state("networkidle")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPurlinReport:

    @pytest.mark.proof("purlin_report", "PROOF-1", "RULE-1")
    def test_script_tag_loads_data_js(self, page, dashboard):
        """PROOF-1: HTML loads .purlin/report-data.js via a script tag."""
        load_dashboard(page, dashboard, data=make_data())
        content = page.content()
        assert 'src=".purlin/report-data.js"' in content, (
            "Expected <script src=\".purlin/report-data.js\"> in page source"
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
        """PROOF-3: Summary strip shows correct counts from PURLIN_DATA.summary."""
        data = make_data({
            "summary": {
                "total_features": 10,
                "ready": 5,
                "partial": 3,
                "failing": 1,
                "no_proofs": 1,
            }
        })
        load_dashboard(page, dashboard, data=data)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof3_summary.png"))
        cards = page.query_selector_all(".summary-card")
        assert len(cards) == 5, f"Expected 5 summary cards, got {len(cards)}"
        strip_text = page.inner_text(".summary-strip")
        assert "10" in strip_text, "Expected total_features=10 in summary strip"
        assert "5" in strip_text, "Expected ready=5 in summary strip"
        assert "3" in strip_text, "Expected partial=3 in summary strip"
        assert "1" in strip_text, "Expected failing=1 in summary strip"

    @pytest.mark.proof("purlin_report", "PROOF-4", "RULE-4")
    def test_feature_table_row_count(self, page, dashboard):
        """PROOF-4: Feature table renders one row per feature."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        def make_feature(name, status, proved, total):
            return {
                "name": name,
                "type": "feature",
                "is_global": False,
                "source_url": None,
                "proved": proved,
                "total": total,
                "deferred": 0,
                "status": status,
                "structural_checks": 0,
                "vhash": None,
                "receipt": None,
                "rules": [],
                "audit": None,
            }

        features = [
            make_feature("alpha", "READY", 3, 3),
            make_feature("beta", "partial", 1, 2),
            make_feature("gamma", "READY", 2, 2),
            make_feature("delta", "partial", 0, 1),
            make_feature("epsilon", "READY", 4, 4),
            make_feature("zeta", "partial", 2, 3),
            make_feature("eta", "READY", 1, 1),
            make_feature("theta", "partial", 0, 2),
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 8, "ready": 4, "partial": 4, "failing": 0, "no_proofs": 0},
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
    def test_expanded_rule_sources(self, page, dashboard):
        """PROOF-6: Own rules show empty Source; global rules show 'global'."""
        # auth_login feature has 2 own rules and 1 global rule
        load_dashboard(page, dashboard, data=make_data())
        # The default sort is by status; click the feature row for auth_login specifically
        # by matching data-name attribute
        auth_row = page.query_selector("tr.fr[data-name='auth_login']")
        assert auth_row is not None, "Expected a feature row for auth_login"
        auth_row.click()
        page.wait_for_timeout(200)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof6_rule_sources.png"))
        # Collect all rule source cells (.rlbl) within the expanded detail
        detail_row = page.query_selector("tr.dr")
        assert detail_row is not None, "Expected a detail row to be present after expanding"
        source_cells = detail_row.query_selector_all("td.rlbl")
        assert len(source_cells) >= 3, f"Expected at least 3 source cells in auth_login detail, got {len(source_cells)}"
        texts = [cell.inner_text().strip() for cell in source_cells]
        # Own rules have empty source
        assert "" in texts, "Expected at least one empty source cell for own rules"
        # Global rule shows 'global' (may be uppercase due to CSS text-transform)
        lower_texts = [t.lower() for t in texts]
        assert "global" in lower_texts, (
            f"Expected 'global' text in source cell for global rules, got: {texts}"
        )

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
            "status": "READY",
            "structural_checks": 0,
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
        # Default sort is by status (FAIL=0, partial=1, READY=2).
        # "alpha" is READY (order 2) with coverage 0/3 = 0.
        # "beta"  is partial (order 1) with coverage 3/3 = 1.
        # Default sort: beta first (partial), then alpha (READY).
        # Coverage-ascending sort: alpha first (0/3=0%), then beta (3/3=100%).
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        features = [
            {
                "name": "alpha", "type": "feature", "is_global": False, "source_url": None,
                "proved": 0, "total": 3, "deferred": 0, "status": "READY",
                "structural_checks": 0, "vhash": None, "receipt": None, "rules": [], "audit": None,
            },
            {
                "name": "beta", "type": "feature", "is_global": False, "source_url": None,
                "proved": 3, "total": 3, "deferred": 0, "status": "partial",
                "structural_checks": 0, "vhash": None, "receipt": None, "rules": [], "audit": None,
            },
        ]
        data = make_data({
            "features": features,
            "summary": {"total_features": 2, "ready": 1, "partial": 1, "failing": 0, "no_proofs": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
            "audit_summary": {
                "integrity": None, "strong": 0, "weak": 0, "hollow": 0, "manual": 0,
                "behavioral_total": 0, "last_audit": None, "last_audit_relative": None, "stale": False,
            },
        })
        load_dashboard(page, dashboard, data=data)
        # Default sort (by status): beta (partial) comes first
        rows_before = page.query_selector_all("tr.fr")
        assert len(rows_before) == 2, f"Expected 2 feature rows, got {len(rows_before)}"
        first_name_before = rows_before[0].get_attribute("data-name")
        assert first_name_before == "beta", (
            f"Expected 'beta' (partial) to be first under default status sort, got '{first_name_before}'"
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
    def test_refresh_button_navigates(self, page, dashboard):
        """PROOF-16: Clicking the staleness indicator triggers page navigation."""
        load_dashboard(page, dashboard, data=make_data())
        url_before = page.url
        # Listen for navigation events
        navigated = []
        page.on("framenavigated", lambda frame: navigated.append(frame.url))
        refresh_btn = page.query_selector("#refresh-btn")
        assert refresh_btn is not None, "Expected element with id='refresh-btn'"
        refresh_btn.click()
        page.wait_for_load_state("networkidle")
        assert len(navigated) > 0, "Expected page navigation to occur after clicking #refresh-btn"

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

        # Narrow viewport: 1100px — verify summary strip reflows to 3 columns
        page.set_viewport_size({"width": 1100, "height": 900})
        page.reload()
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "proof17_narrow.png"))
        grid_cols = page.evaluate(
            "() => getComputedStyle(document.querySelector('.summary-strip')).gridTemplateColumns"
        )
        # At 1100px width, the @media rule sets repeat(3,1fr)
        # getComputedStyle returns the resolved value, e.g. "3 columns" as pixel widths
        # We verify it is NOT 5 equal columns by checking the column count
        col_count = len(grid_cols.split())
        # 5 columns would give 5 pixel values; 3 columns gives 3 pixel values
        assert col_count == 3, (
            f"Expected 3 columns in summary-strip at 1100px viewport, "
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
        "type": "feature",
        "is_global": False,
        "source_url": None,
        "proved": 0,
        "total": 1,
        "deferred": 0,
        "status": "FAIL",
        "structural_checks": 0,
        "vhash": None,
        "receipt": None,
        "rules": [],
        "audit": None,
    }


def make_integrity_feature(name, integrity):
    """Return a feature with a specific audit integrity value."""
    return {
        "name": name,
        "type": "feature",
        "is_global": False,
        "source_url": None,
        "proved": 2,
        "total": 2,
        "deferred": 0,
        "status": "READY",
        "structural_checks": 0,
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
        """PROOF-6: .sb-ready has solid green background and white text."""
        load_dashboard(page, dashboard, data=make_data())

        bg = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-ready')).backgroundColor"
        )
        assert rgb_to_hex(bg) == "#22c55e", (
            f"Expected .sb-ready background #22c55e (green), got {bg!r}"
        )

        color = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-ready')).color"
        )
        assert rgb_to_hex(color) == "#ffffff", (
            f"Expected .sb-ready text color #ffffff (white), got {color!r}"
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
            "summary": {"total_features": 1, "ready": 0, "partial": 0, "failing": 1, "no_proofs": 0},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
            "audit_summary": {
                "integrity": None, "strong": 0, "weak": 0, "hollow": 0, "manual": 0,
                "behavioral_total": 0, "last_audit": None, "last_audit_relative": None, "stale": False,
            },
        })
        load_dashboard(page, dashboard, data=data)

        bg = page.evaluate(
            "() => getComputedStyle(document.querySelector('.sb-fail')).backgroundColor"
        )
        assert rgb_to_hex(bg) == "#ef4444", (
            f"Expected .sb-fail background #ef4444 (red), got {bg!r}"
        )

    @pytest.mark.proof("dashboard_visual", "PROOF-9", "RULE-9")
    def test_no_proofs_badge_opacity(self, page, dashboard):
        """PROOF-9: .sb-none has reduced opacity (< 1)."""
        # The default make_data() has a 'checkout' feature with status 'partial',
        # which doesn't give us .sb-none. We need a feature with no proofs.
        # Status 'no_proofs' doesn't exist in badgeClass — unrecognized status
        # falls through to sb-none. Use a custom status value.
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        no_proof_feature = {
            "name": "unproved_feature",
            "type": "feature",
            "is_global": False,
            "source_url": None,
            "proved": 0,
            "total": 1,
            "deferred": 0,
            "status": "no_proofs",
            "structural_checks": 0,
            "vhash": None,
            "receipt": None,
            "rules": [],
            "audit": None,
        }
        data = make_data({
            "features": [no_proof_feature],
            "summary": {"total_features": 1, "ready": 0, "partial": 0, "failing": 0, "no_proofs": 1},
            "anchors_summary": {"total": 0, "with_source": 0, "global": 0},
            "audit_summary": {
                "integrity": None, "strong": 0, "weak": 0, "hollow": 0, "manual": 0,
                "behavioral_total": 0, "last_audit": None, "last_audit_relative": None, "stale": False,
            },
        })
        load_dashboard(page, dashboard, data=data)

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
            "summary": {"total_features": 3, "ready": 3, "partial": 0, "failing": 0, "no_proofs": 0},
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
