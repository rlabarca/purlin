"""Structural checks on the dashboard markup — no browser required.

dev/test_purlin_report.py drives the real dashboard through Playwright, which
needs a Chromium download. These checks assert the data bindings and rendering
branches directly from the HTML source, so the dashboard's contract still has an
executable proof on a machine with no browser.

They emit at the `integration` tier deliberately. Two test files emitting the same
feature at the same tier collide under feature-scoped overwrite: whichever runs
last purges the other's entries, and the Playwright file cannot run without a
browser to restore them.
"""

import os
import re

import pytest

HTML_SRC = os.path.join(
    os.path.dirname(__file__), '..', 'scripts', 'report', 'purlin-report.html')


def _html():
    with open(HTML_SRC, encoding='utf-8') as f:
        return f.read()


class TestSummaryStripGauges:

    @pytest.mark.proof("purlin_report", "PROOF-35", "RULE-34", tier="integration")
    def test_renders_both_gauges_with_shared_styling(self):
        html = _html()

        # The design gauge must be bound from PURLIN_DATA.
        assert re.search(r'var\s+G\s*=\s*D\.design_summary', html), \
            "dashboard must bind design_summary from PURLIN_DATA"

        # A card labelled Proof Design, whose headline comes from the shared
        # helper rather than straight off .design. The helper returns the
        # coverage-weighted figure (RULE-36), so reading .design directly is
        # what put a 100% assessed score on the card beside 39 feature rows
        # reading "not audited".
        assert 'Proof Design' in html, "no Proof Design card label"
        assert re.search(r"gaugeHeadline\(G, 'design'\)", html), \
            "the design card must take its headline from gaugeHeadline"
        assert re.search(r"gaugeHeadline\(A, 'integrity'\)", html), \
            "the integrity card must take its headline from the same helper"
        hm = re.search(r'function gaugeHeadline\(summary, which\) \{(.*?)\n  \}',
                       html, re.DOTALL)
        assert hm, "gaugeHeadline helper not found"
        assert 'summary.weighted' in hm.group(1), \
            "gaugeHeadline must prefer the coverage-weighted figure"
        assert re.search(r'summary\.design', hm.group(1)), \
            "gaugeHeadline must fall back to the assessed score"

        # Both cards are built by one helper, which is what keeps their colour
        # bands identical without a second definition to drift from.
        m = re.search(r'function gaugeCard\(summary, label, pct, counts, attrs\) \{(.*?)\n  \}',
                      html, re.DOTALL)
        assert m, "gaugeCard helper not found"
        block = m.group(1)
        assert 'int-mid' in block and 'int-lo' in block, \
            "the gauge card must reuse the integrity colour classes"
        assert 'cov.complete' not in block, (
            "the card must not override its band on incomplete coverage: the "
            "headline is already coverage-weighted, so forcing amber promotes a "
            "genuinely red gauge (RULE-36)")
        assert 'pct >= 80' in block and 'pct >= 50' in block, \
            "the gauge card must use the same 80/50 thresholds as integrity"
        assert 'sc-integrity' in block, \
            "the gauge card must reuse the sc-integrity card class"

        # Null gauge renders an em dash rather than a stale or zero number.
        assert '&mdash;' in block, "a null gauge card must render an em dash"

        # Per-level counts reach the card as its `counts` argument.
        design_call = re.search(r"gaugeCard\(G, 'Proof Design'.*?\);", html, re.DOTALL)
        assert design_call, "no gaugeCard call for Proof Design"
        for field in ('G.provable', 'G.loose', 'G.unprovable'):
            assert field in design_call.group(0), \
                f"design card sub-label missing {field}"
        integrity_call = re.search(r"gaugeCard\(A, 'Proof Integrity'.*?\);", html, re.DOTALL)
        assert integrity_call, "no gaugeCard call for Proof Integrity"
        for field in ('A.strong', 'A.weak', 'A.hollow'):
            assert field in integrity_call.group(0), \
                f"integrity card sub-label missing {field}"

    @pytest.mark.proof("purlin_report", "PROOF-35", "RULE-34", tier="integration")
    def test_integrity_null_label_distinguishes_untested(self):
        """"No tests yet" and "never audited" are different states and used to
        render identically, which made a spec-first project look neglected."""
        html = _html()
        assert re.search(
            r"S\.untested\s*===\s*S\.total_features\s*\?\s*'no tests yet'", html), \
            ("the integrity card's null sub-label must read 'no tests yet' when every "
             "feature is UNTESTED, and 'run purlin:audit' otherwise")
        assert "'run purlin:audit'" in html

    @pytest.mark.proof("purlin_report", "PROOF-35", "RULE-34", tier="integration")
    def test_summary_grid_holds_every_card_without_orphaning(self):
        """The grid column count must match the number of cards. It was pinned at
        6 while 7 cards were emitted, so the last one wrapped onto a row alone."""
        html = _html()

        strip = html.split("h += '<div class=\"summary-strip\">'", 1)
        assert len(strip) == 2, "could not locate the summary strip render block"
        block = strip[1].split('/* Uncommitted work section */', 1)[0]
        # Five cards are emitted inline; the two gauge cards come from gaugeCard,
        # which takes its label as an argument. Count both spellings.
        labels = set(re.findall(r'summary-card-label">([^<\']+)', block))
        labels |= set(re.findall(r"gaugeCard\([AG], '([^']+)'", block))
        cards = len(labels)
        assert cards >= 7, f"expected at least 7 summary cards, found {cards}: {sorted(labels)}"

        m = re.search(r'\.summary-strip\{[^}]*grid-template-columns:repeat\((\d+),', html)
        assert m, "summary-strip has no default repeat(N,1fr) column count"
        cols = int(m.group(1))
        assert cols == cards, (
            f"the summary grid is ruled for {cols} columns but {cards} cards are "
            f"rendered; the remainder orphans onto its own row")

        # Desktop breakpoints must not leave a single card stranded on its own row.
        # Below 900px a trailing card is ordinary responsive wrapping, and the
        # 3-column rule there is depended on by PROOF-17.
        for bp in re.findall(
                r'@media \(max-width:(\d+)px\) \{\s*\.summary-strip\{grid-template-columns:repeat\((\d+),',
                html):
            width, n = int(bp[0]), int(bp[1])
            if width < 900:
                continue
            assert cards % n != 1, (
                f"at max-width:{width}px the grid is {n} columns, which leaves a "
                f"single orphaned card out of {cards}")


class TestFeatureTableColumns:

    @pytest.mark.proof("purlin_report", "PROOF-36", "RULE-4", tier="integration")
    def test_design_and_integrity_are_separate_columns(self):
        """RULE-4: six columns, Design before Integrity, colspans sized for six.

        The table carried one Integrity column while the summary strip carried
        two gauge cards, so the dashboard presented two concepts at the top and
        one underneath. Adding a column also moves two colspans that were ruled
        for five, which is the kind of off-by-one that only shows up visually.
        """
        html = _html()

        # The shared column list drives the head, the per-category header row and
        # the colgroup, so asserting on it covers all three.
        m = re.search(r'var cols = \[(.*?)\];', html, re.DOTALL)
        assert m, "shared column list not found"
        keys = re.findall(r"key:'(\w+)'", m.group(1))
        assert keys == ['name', 'coverage', 'status', 'design', 'integrity', 'verified'], \
            f"expected six columns with design before integrity, got {keys}"

        labels = re.findall(r"label:'([^']+)'", m.group(1))
        assert 'Design' in labels and 'Integrity' in labels, \
            f"both gauges need a column label, got {labels}"

        # Sorting is wired generically off data-col, so a `design` comparator
        # case is what makes the new header actually sortable.
        assert re.search(r"case 'design':", html), \
            "sort comparator has no 'design' case, so the header would not sort"

        # Colspans: category header spans everything but name+coverage (4), the
        # expanded detail row spans all six.
        assert re.search(r'colspan="4"><div class="cat-summary"', html), \
            "category header colspan must be 4 for a six-column table"
        assert re.search(r'class="dr cat-child"><td colspan="6"', html), \
            "expanded detail row colspan must be 6 for a six-column table"

        # One helper serves both gauges, which is what keeps dashboard_visual
        # RULE-10's colour bands true for Design without a second definition.
        assert html.count('bh += gaugeCell(') == 2, \
            "both gauge cells must route through the one gaugeCell helper"
        assert re.search(r'function gaugeCell\(pct, gauge, label, which\)', html), \
            "gaugeCell helper not found"
        # Each gauge names its unscorable state in its own vocabulary: STRUCTURAL
        # describes a description, EXCLUDED describes a test (RULE-35).
        assert re.search(r"which === 'design' \? 'structural' : 'excluded'", html), \
            "the unscorable token must come from each gauge's own vocabulary"
        assert "gaugeCell(dsnVal, f.design, 'Proof Design', 'design')" in html
        assert "gaugeCell(intVal, f.audit, 'Proof Integrity', 'integrity')" in html


class TestModalHelper:
    """purlin_report RULE-41 — one modal helper, mounted on the body.

    `render()` rewrites `#app` on every sort, expand and theme toggle. A dialog
    mounted inside it would be destroyed mid-interaction, so the overlay lives
    on `document.body` and `render()` closes it before rebuilding.
    """

    @pytest.mark.proof("purlin_report", "PROOF-43", "RULE-41", tier="integration")
    def test_one_helper_mounted_on_the_body_with_the_aria_contract(self):
        html = _html()

        for sig in ('function openModal(title, bodyHtml, footHtml) {',
                    'function closeModal() {',
                    'function onModalKey(e) {'):
            assert html.count(sig) == 1, (
                f"expected exactly one definition of {sig!r}, got {html.count(sig)}")

        assert 'document.body.appendChild(overlay)' in html, \
            "the overlay must be appended to document.body"
        assert not re.search(r'app\.appendChild\(\s*overlay', html), \
            "the overlay must never be mounted inside #app, which render() rewrites"

        for attr in ('role="dialog"', 'aria-modal="true"', 'aria-labelledby="modal-title"'):
            assert attr in html, f"the dialog must carry {attr}"

        m = re.search(r'function render\(\) \{\s*(?:/\*.*?\*/\s*)?(.+?)\n', html, re.DOTALL)
        assert m, "render() not found"
        assert m.group(1).strip().startswith('closeModal();'), (
            "render() must begin with closeModal() so no dialog outlives the "
            f"content it described; got {m.group(1).strip()[:60]!r}")

        # Both custom properties in both theme blocks.
        for block in (r'\[data-theme="dark"\] \{(.*?)\n\}',
                      r'\[data-theme="light"\] \{(.*?)\n\}'):
            bm = re.search(block, html, re.DOTALL)
            assert bm, f"theme block {block!r} not found"
            for prop in ('--bg-overlay:', '--shadow:'):
                assert prop in bm.group(1), \
                    f"{prop} must be defined in the theme block {block!r}"

        # The overlay and the dialog reference the properties, never a literal.
        for sel in (r'\.modal-overlay\{([^}]*)\}', r'\.modal\{([^}]*)\}'):
            rm = re.search(sel, html)
            assert rm, f"{sel!r} rule not found"
            assert not re.search(r'#[0-9a-fA-F]{3,8}\b', rm.group(1)), (
                f"{sel!r} must carry no hex literal, only custom properties: "
                f"{rm.group(1)!r}")
        assert 'var(--bg-overlay)' in re.search(r'\.modal-overlay\{([^}]*)\}', html).group(1)
        assert 'var(--shadow)' in re.search(r'\.modal\{([^}]*)\}', html).group(1)
