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

        # A card labelled Proof Design, reading .design.
        assert 'Proof Design' in html, "no Proof Design card label"
        assert re.search(r'G\.design', html), "the card must read design_summary.design"

        # Same colour bands as integrity, so dashboard_visual RULE-10 still holds.
        design_block = html.split('Proof Design card', 1)
        assert len(design_block) == 2, "expected the Proof Design card block"
        block = design_block[1][:900]
        assert 'int-mid' in block and 'int-lo' in block, \
            "the design card must reuse the integrity colour classes"
        assert '>= 80' in block and '>= 50' in block, \
            "the design card must use the same 80/50 thresholds as integrity"
        assert 'sc-integrity' in block, \
            "the design card must reuse the sc-integrity card class"

        # Per-level counts in the sub-label.
        for field in ('G.provable', 'G.loose', 'G.unprovable'):
            assert field in block, f"design card sub-label missing {field}"

        # Null gauge renders an em dash rather than a stale or zero number.
        assert '&mdash;' in block, "a null design gauge must render an em dash"

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
