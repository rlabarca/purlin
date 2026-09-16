"""The board's failing card and the spec table's column alignment, in a browser.

The page and the fixtures are `dev/test_purlin_report.py`'s, opened the same way.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DEV)

from test_purlin_report import (browser, open_board,  # noqa: E402,F401
                                payload_named)

# For every spec row, how far each cell's left edge sits from its heading's.
OFFSETS = """() => {
  const heads = Array.from(document.querySelectorAll('.th > div'))
    .map(d => d.getBoundingClientRect().left);
  return Array.from(document.querySelectorAll('.tr')).map(row =>
    Array.from(row.children).map((cell, i) =>
      Math.abs(cell.getBoundingClientRect().left - heads[i])));
}"""


@pytest.mark.proof("purlin_report", "PROOF-33", "RULE-33", tier="e2e")
def test_every_heading_starts_where_its_cells_start(browser, tmp_path):  # noqa: F811
    for width in (1440, 1024):
        page = open_board(browser, tmp_path / str(width),
                          payload_named('regulated'),
                          viewport={'width': width, 'height': 1000})
        offsets = page.evaluate(OFFSETS)
        assert offsets, 'no spec row rendered'
        worst = max(max(row) for row in offsets)
        assert worst <= 1, (width, offsets)
        page.close()


@pytest.mark.proof("purlin_report", "PROOF-34", "RULE-32", tier="e2e")
def test_the_failing_card_carries_the_count(browser, tmp_path):  # noqa: F811
    payload = payload_named('regulated')
    payload['project_rollup']['failing'] = 3
    page = open_board(browser, tmp_path / 'three', payload)
    assert page.inner_text('.failing-v').strip() == '3'
    assert 'on' in page.get_attribute('.failing', 'class')
    fail = page.evaluate(
        "getComputedStyle(document.documentElement)"
        ".getPropertyValue('--state-fail').trim()")
    colour = page.eval_on_selector('.failing-v', 'el => getComputedStyle(el).color')
    probe = page.evaluate(
        "c => { const s = document.createElement('span'); s.style.color = c;"
        " document.body.appendChild(s); const v = getComputedStyle(s).color;"
        " s.remove(); return v; }", fail)
    assert colour == probe, (colour, probe)
    assert len(page.query_selector_all('.tile')) == 7
    assert '3 failing' in page.inner_text('h1')
    page.close()

    payload['project_rollup']['failing'] = 0
    page = open_board(browser, tmp_path / 'none', payload)
    assert page.inner_text('.failing-v').strip() == '0'
    assert 'on' not in page.get_attribute('.failing', 'class').split()
    page.close()
