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
    failing = page.eval_on_selector_all(
        '.tile', "els => els.map(e => [e.querySelector('.tile-l').textContent,"
        " e.querySelector('.tile-v').textContent])")
    assert dict(failing)['Failing'] == '2', failing
    # The stale count is the flag card's and the `Signed` hover's; the cell
    # states the share alone.
    signed = count_cells(page)['login']['Signed']
    assert signed == '1 of 3' and 'stale' not in signed
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
    """Text under 13 pixels is unreadable in the dark theme."""
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
def test_every_column_fits_from_1024_up_and_no_value_breaks(browser,  # noqa: F811
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
        assert page.evaluate(WRAPPED) == 0, width
        page.close()
        # A spec that proves an anchor's rules reads `1 (+1 shared)`, and
        # that value is one line too.
        team = open_board(browser, tmp_path / ('team%d' % width),
                          payload_named('team'),
                          viewport={'width': width, 'height': 1000})
        assert '1 (+1 shared)' in team.inner_text('.tbl')
        assert team.evaluate(WRAPPED) == 0, width
        team.close()


# The five widths a person opens the board at, from a wide screen to a phone.
EVERY_WIDTH = (1500, 1280, 1024, 768, 390)

# Every element that holds one value, and how many lines its own text takes:
# the distinct tops of the line boxes a range over its content gives. A value
# broken inside itself has two.
BROKEN_VALUES = """() => {
  const sel = ['.trio', '.tr > div[data-label]', '.chip', '.tag', '.pill',
               '.rule .rid', '.more', '.tile-l', '.flag-l', '.name .n',
               '.rev > [data-label]', '.fresh', '.group .gt'];
  const out = [];
  document.querySelectorAll(sel.join(',')).forEach(el => {
    if (!el.textContent.trim() || !el.getClientRects().length) { return; }
    const near = parseFloat(getComputedStyle(el).fontSize) * 0.6;
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const tops = [];
    while (walker.nextNode()) {
      if (!walker.currentNode.textContent.trim()) { continue; }
      const range = document.createRange();
      range.selectNodeContents(walker.currentNode);
      Array.from(range.getClientRects()).forEach(r => {
        if (r.width < 1) { return; }
        if (!tops.some(t => Math.abs(t - r.top) < near)) { tops.push(r.top); }
      });
    }
    if (tops.length > 1) { out.push(el.textContent.trim()); }
  });
  return out;
}"""

SIDEWAYS = """() => document.documentElement.scrollWidth
  - document.documentElement.clientWidth"""

# How many tiles and flag cards share the first tile's row.
FIRST_ROW = """() => {
  const tiles = Array.from(document.querySelectorAll('.tile, .flag'));
  const top = tiles[0].getBoundingClientRect().top;
  return tiles.filter(t => Math.abs(t.getBoundingClientRect().top - top) < 2)
    .length;
}"""


def _every_screen(page):
    """Open login and one rule's proofs; then the rule screen; then the queue.

    Returns what each screen showed: `(screen, sideways pixels, broken values)`.
    """
    seen = []
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('[data-act="proofs"][data-feature="login"][data-rule="RULE-4"]')
    seen.append(('board', page.evaluate(SIDEWAYS), page.evaluate(BROKEN_VALUES)))
    page.click('.rule[data-feature="login"][data-rule="RULE-1"] .rt')
    seen.append(('rule', page.evaluate(SIDEWAYS), page.evaluate(BROKEN_VALUES)))
    page.click('[data-screen="queue"]')
    seen.append(('queue', page.evaluate(SIDEWAYS), page.evaluate(BROKEN_VALUES)))
    return seen


# purlin: purlin_report PROOF-75
def test_every_screen_fits_every_width_and_no_value_breaks(browser, tmp_path):  # noqa: F811
    for width in EVERY_WIDTH:
        for theme in ('dark', 'light'):
            page = open_board(browser, tmp_path / ('%d%s' % (width, theme)),
                              payload_named('regulated'),
                              viewport={'width': width, 'height': 900})
            if theme == 'light':
                page.click('[data-act="theme"]')
            assert page.get_attribute('html', 'data-theme') == theme
            for screen, sideways, broken in _every_screen(page):
                assert sideways == 0, (width, theme, screen, sideways)
                assert broken == [], (width, theme, screen, broken)
            page.close()
        # The team board holds a spec that proves an anchor's rule.
        team = open_board(browser, tmp_path / ('team%d' % width),
                          payload_named('team'),
                          viewport={'width': width, 'height': 900})
        assert '1 (+1 shared)' in team.inner_text('.tr[data-feature="receipt"]')
        assert team.evaluate(SIDEWAYS) == 0, width
        assert team.evaluate(BROKEN_VALUES) == [], width
        team.close()


# purlin: purlin_report PROOF-76
def test_a_narrow_board_is_blocks_of_labelled_pairs(browser, tmp_path):  # noqa: F811
    rows = {}
    for width, expected in ((1024, 6), (768, 4), (390, 2)):
        page = open_board(browser, tmp_path / str(width),
                          payload_named('team' if width == 390 else 'regulated'),
                          viewport={'width': width, 'height': 900})
        rows[width] = page.evaluate(FIRST_ROW)
        if width == 390:
            receipt = page.inner_text('.tr[data-feature="receipt"]')
            rows['receipt'] = ' '.join(receipt.split())
            rows['label'] = page.eval_on_selector(
                '.tr[data-feature="receipt"] > div:nth-child(2)',
                "el => getComputedStyle(el, '::before').content")
            rows['heads'] = page.is_visible('.th')
        page.close()
    assert (rows[768], rows[390]) == (4, 2), rows
    assert rows[1024] >= 6, rows
    assert rows['heads'] is False, rows
    assert rows['receipt'].startswith('▶ receipt 1 (+1 shared)'), rows
    assert rows['label'] == '"Rules"', rows
