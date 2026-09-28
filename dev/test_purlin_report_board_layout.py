"""The board's stale card and the spec table's columns, in a browser.

The page and the fixtures are `dev/test_purlin_report.py`'s, opened the same way.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DEV)

from test_purlin_report import (browser, count_cells,  # noqa: E402,F401
                                flag_cards, open_board, payload_named)

# The widths a reader opens the board at: a laptop, two desktops and a wide
# screen. At 1024 every column the gate reaches is on screen; the page's own
# content stops widening at 1360, so 1440 and 1920 read the same table.
WIDTHS = (1920, 1440, 1280, 1024)

# For every spec row, how far each cell's left edge sits from its heading's.
OFFSETS = """() => {
  const heads = Array.from(document.querySelectorAll('.th > div'))
    .map(d => d.getBoundingClientRect().left);
  return Array.from(document.querySelectorAll('.tr')).map(row =>
    Array.from(row.children).map((cell, i) =>
      Math.abs(cell.getBoundingClientRect().left - heads[i])));
}"""


# purlin: purlin_report PROOF-33
def test_every_heading_starts_where_its_cells_start(browser, tmp_path):  # noqa: F811
    for width in WIDTHS:
        page = open_board(browser, tmp_path / str(width),
                          payload_named('regulated'),
                          viewport={'width': width, 'height': 1000})
        offsets = page.evaluate(OFFSETS)
        assert offsets, 'no spec row rendered'
        worst = max(max(row) for row in offsets)
        assert worst <= 1, (width, offsets)
        page.close()


# purlin: purlin_report PROOF-34
def test_the_stale_card_carries_the_count(browser, tmp_path):  # noqa: F811
    payload = payload_named('regulated')
    payload['summary']['stale'] = 3
    payload['summary']['failing'] = 2
    page = open_board(browser, tmp_path / 'three', payload)
    assert flag_cards(page)['Stale'] == '3'
    assert 'on' in page.get_attribute('.flag:last-child', 'class')
    fail = page.evaluate(
        "getComputedStyle(document.documentElement)"
        ".getPropertyValue('--state-fail').trim()")
    colour = page.eval_on_selector(
        '.flag:last-child .flag-v', 'el => getComputedStyle(el).color')
    probe = page.evaluate(
        "c => { const s = document.createElement('span'); s.style.color = c;"
        " document.body.appendChild(s); const v = getComputedStyle(s).color;"
        " s.remove(); return v; }", fail)
    assert colour == probe, (colour, probe)
    assert len(page.query_selector_all('.tile')) == 6
    assert '2 failing' in page.inner_text('h1')
    # The stale count is the flag card's and the `Signed` hover's; the cell
    # states the share alone.
    signed = count_cells(page)['login']['Signed']
    assert signed == '1 of 4' and 'stale' not in signed
    page.close()

    payload['summary']['stale'] = 0
    page = open_board(browser, tmp_path / 'none', payload)
    assert flag_cards(page)['Stale'] == '0'
    assert 'on' not in page.get_attribute('.flag:last-child', 'class').split()
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


# purlin: purlin_report PROOF-41
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


# The right edge of the last column heading, which at the `signed` gate is
# `Signed`: the column a reader on a laptop never saw while the floors added
# up to more than a 1100-wide window gives the table. Seven columns fit it.
LAST_HEADING = """() => {
  const heads = document.querySelectorAll('.th > div');
  return heads[heads.length - 1].getBoundingClientRect().right;
}"""

# How many count cells draw their parts on more than one line: zero where
# every part of every cell shares a top edge with the first.
WRAPPED = """() => Array.from(document.querySelectorAll('.tr > div')).filter(
  cell => new Set(Array.from(cell.querySelectorAll('.trio b')).map(
    b => Math.round(b.getBoundingClientRect().top))).size > 1).length"""

# Anything on the table that is set to the right of its own box. Two bare
# number columns twelve pixels apart read as one number, so nothing is.
RIGHT_ALIGNED = """() => Array.from(document.querySelectorAll('.tbl *')).filter(
  el => getComputedStyle(el).textAlign === 'right').length"""


# purlin: purlin_report PROOF-42
def test_a_column_keeps_its_floor_and_the_table_scrolls_instead(browser,  # noqa: F811
                                                                tmp_path):
    """`SIGNED` sat off the right of a 1024-wide window with eight columns."""
    for width in WIDTHS:
        page = open_board(browser, tmp_path / str(width),
                          payload_named('regulated'),
                          viewport={'width': width, 'height': 1000})
        assert [h for h in page.evaluate(HEADINGS) if h['over'] > 0] == []
        assert page.eval_on_selector(
            '.tbl', 'el => el.scrollWidth - el.clientWidth') == 0
        assert page.evaluate(LAST_HEADING) <= width
        assert page.evaluate(RIGHT_ALIGNED) == 0
        if width >= 1280:
            assert page.evaluate(WRAPPED) == 0, width
        page.close()

    narrow = open_board(browser, tmp_path / 'narrow',
                        payload_named('regulated'),
                        viewport={'width': 700, 'height': 1000})
    assert [h for h in narrow.evaluate(HEADINGS) if h['over'] > 0] == []
    assert narrow.eval_on_selector(
        '.tbl', 'el => el.scrollWidth - el.clientWidth') > 0
    narrow.close()
