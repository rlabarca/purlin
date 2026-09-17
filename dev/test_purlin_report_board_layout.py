"""The board's stale card and the spec table's column alignment, in a browser.

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
def test_the_stale_card_carries_the_count(browser, tmp_path):  # noqa: F811
    payload = payload_named('regulated')
    payload['summary']['stale'] = 3
    payload['summary']['failing'] = 2
    page = open_board(browser, tmp_path / 'three', payload)
    assert page.inner_text('.flag-v').strip() == '3'
    assert 'on' in page.get_attribute('.flag', 'class')
    fail = page.evaluate(
        "getComputedStyle(document.documentElement)"
        ".getPropertyValue('--state-fail').trim()")
    colour = page.eval_on_selector('.flag-v', 'el => getComputedStyle(el).color')
    probe = page.evaluate(
        "c => { const s = document.createElement('span'); s.style.color = c;"
        " document.body.appendChild(s); const v = getComputedStyle(s).color;"
        " s.remove(); return v; }", fail)
    assert colour == probe, (colour, probe)
    assert len(page.query_selector_all('.tile')) == 5
    assert '2 failing' in page.inner_text('h1')
    page.close()

    payload['summary']['stale'] = 0
    page = open_board(browser, tmp_path / 'none', payload)
    assert page.inner_text('.flag-v').strip() == '0'
    assert 'on' not in page.get_attribute('.flag', 'class').split()
    page.close()


# Every element on the board that carries text of its own, and the size that
# text computes to. An element with no text node of its own is skipped: it
# inherits a size but draws nothing at it.
FONT_SIZES = """() => Array.from(document.querySelectorAll('#app *'))
  .filter(el => Array.from(el.childNodes).some(
    node => node.nodeType === 3 && node.textContent.trim()))
  .map(el => ({
    what: el.className || el.tagName,
    size: parseFloat(getComputedStyle(el).fontSize)
  }))"""


@pytest.mark.proof("purlin_report", "PROOF-41", "RULE-34", tier="e2e")
def test_no_text_on_the_board_is_set_under_thirteen_pixels(browser, tmp_path):  # noqa: F811
    """The dark theme's smallest text was 11 pixels and unreadable."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert page.get_attribute('html', 'data-theme') == 'dark'
    page.click('.tr')
    sizes = page.evaluate(FONT_SIZES)
    assert sizes, 'nothing on the board carries text'
    smallest = min(sizes, key=lambda item: item['size'])
    assert smallest['size'] >= 13, smallest
    page.close()


# Each column heading, its box and whether its own text fits inside that box.
HEADINGS = """() => Array.from(document.querySelectorAll('.th > div'))
  .map(el => ({
    label: el.textContent.trim(),
    over: el.scrollWidth - el.clientWidth
  }))"""


@pytest.mark.proof("purlin_report", "PROOF-42", "RULE-35", tier="e2e")
def test_a_column_keeps_its_floor_and_the_table_scrolls_instead(browser,  # noqa: F811
                                                                tmp_path):
    """`STRENGTH` ran into `STRONG` where the track was narrower than the word."""
    wide = open_board(browser, tmp_path / 'wide', payload_named('regulated'),
                      viewport={'width': 1440, 'height': 1000})
    assert [h for h in wide.evaluate(HEADINGS) if h['over'] > 0] == []
    assert wide.eval_on_selector(
        '.tbl', 'el => el.scrollWidth - el.clientWidth') == 0
    wide.close()

    narrow = open_board(browser, tmp_path / 'narrow',
                        payload_named('regulated'),
                        viewport={'width': 1100, 'height': 1000})
    assert [h for h in narrow.evaluate(HEADINGS) if h['over'] > 0] == []
    assert narrow.eval_on_selector(
        '.tbl', 'el => el.scrollWidth - el.clientWidth') > 0
    narrow.close()
