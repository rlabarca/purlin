"""The board's layout at every width: the spec table's columns, the boxes and
what a narrow screen draws, in a browser.

The page and the fixtures are `dev/test_purlin_report.py`'s, opened the same way.
"""

import os
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DEV)

from test_purlin_report import (browser, open_board,  # noqa: E402,F401
                                payload_named)

# The widths a reader opens the board at: a laptop, two desktops and a wide
# screen. At 1024 every column the gate reaches is on screen; the page's own
# content stops widening at 1360, so 1440 and 1920 read the same table.
WIDTHS = (1920, 1440, 1280, 1024)

# For every spec row, how far each cell's left edge sits from its own
# table's heading's.
OFFSETS = """() => Array.from(document.querySelectorAll('.tr')).map(row => {
  const heads = Array.from(row.closest('.tbl').querySelectorAll('.th > div'))
    .map(d => d.getBoundingClientRect().left);
  return Array.from(row.children).map((cell, i) =>
    Math.abs(cell.getBoundingClientRect().left - heads[i]));
})"""


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


def _at_every_width(browser, tmp_path, name, look):
    """`{width: look(page)}` for the board of one sample at each width."""
    found = {}
    for width in WIDTHS:
        page = open_board(browser, tmp_path / ('%s%d' % (name, width)),
                          payload_named(name),
                          viewport={'width': width, 'height': 1000})
        found[width] = look(page)
        page.close()
    return found


# purlin: purlin_report PROOF-42
def test_every_column_fits_from_1024_up(browser, tmp_path):  # noqa: F811
    """`SIGNED` sat off the right of a 1024-wide window with eight columns."""
    found = _at_every_width(browser, tmp_path, 'regulated', lambda page: (
        page.evaluate(SIDEWAYS), page.evaluate(LAST_HEADING)))
    for width, (sideways, last) in found.items():
        assert sideways == 0, (width, sideways)
        assert last <= width, (width, last)


# purlin: purlin_report PROOF-140
def test_no_heading_overflows_and_no_count_breaks(browser,  # noqa: F811
                                                  tmp_path):
    found = _at_every_width(browser, tmp_path, 'regulated', lambda page: (
        [h for h in page.evaluate(HEADINGS) if h['over'] > 0],
        page.evaluate(WRAPPED)))
    assert found == {width: ([], 0) for width in WIDTHS}, found


# purlin: purlin_report PROOF-141
def test_nothing_on_the_table_is_aligned_right(browser,  # noqa: F811
                                               tmp_path):
    found = _at_every_width(browser, tmp_path, 'regulated',
                            lambda page: page.evaluate(RIGHT_ALIGNED))
    assert found == {width: 0 for width in WIDTHS}, found


# purlin: purlin_report PROOF-142
def test_a_long_tests_value_is_one_line_from_1024_up(browser,  # noqa: F811
                                                     tmp_path):
    """The widest value in the sample, `1 of 1 · 1 does not apply`, is one
    line like every other."""
    found = _at_every_width(browser, tmp_path, 'regulated', lambda page: (
        DOES_NOT_APPLY in _tests_value(page), page.evaluate(WRAPPED)))
    assert found == {width: (True, 0) for width in WIDTHS}, found


DOES_NOT_APPLY = '1 of 1 · 1 does not apply'


def _tests_value(page):
    """security_baseline's `Tests` value, as its one line reads."""
    return ' '.join(page.inner_text(
        '.tr[data-feature="security_baseline"] > div[data-label="Tests"]'
        ' .trio').split())


# The five widths a person opens the board at, from a wide screen to a phone.
EVERY_WIDTH = (1500, 1280, 1024, 768, 390)

# Every element that holds one value, and how many lines its own text takes:
# the distinct tops of the line boxes a range over its content gives. A value
# broken inside itself has two.
BROKEN_VALUES = """() => {
  const sel = ['.trio', '.tr > div[data-label]', '.chip', '.tag', '.pill',
               '.rule .rid', '.more', '.tile-l', '.name .n', '.fresh',
               '.group .gt'];
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

SIDEWAYS = """() => Math.max(document.documentElement.scrollWidth
  - document.documentElement.clientWidth, ...Array.from(
    document.querySelectorAll('.tbl')).map(t => t.scrollWidth - t.clientWidth))"""

# How many boxes share the first box's row.
FIRST_ROW = """() => {
  const tiles = Array.from(document.querySelectorAll('.tile'));
  const top = tiles[0].getBoundingClientRect().top;
  return tiles.filter(t => Math.abs(t.getBoundingClientRect().top - top) < 2)
    .length;
}"""


def _every_screen(page):
    """Open login and one rule's proofs; then the rule screen.

    Returns what each screen showed: `(screen, sideways pixels, broken values)`.
    """
    seen = []
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('[data-act="proofs"][data-feature="login"][data-rule="RULE-4"]')
    seen.append(('board', page.evaluate(SIDEWAYS), page.evaluate(BROKEN_VALUES)))
    page.click('.rule[data-feature="login"][data-rule="RULE-1"] .rt')
    seen.append(('rule', page.evaluate(SIDEWAYS), page.evaluate(BROKEN_VALUES)))
    return seen


def _long_rule_payload():
    """The regulated payload with a rule whose words run far past any window,
    as this repository's own do, open beneath its spec: it must not widen the
    table's columns."""
    payload = payload_named('regulated')
    payload['features'][0]['rules'][3]['text'] += ' ' + ' '.join(
        ['The cookie carries the Secure flag on every response.'] * 8)
    return payload


def _fits_every_width(browser, tmp_path, theme):
    """Every width, in one theme: `(width, screen, sideways, broken)` for
    each screen that scrolled sideways or broke a value."""
    wrong = []
    for width in EVERY_WIDTH:
        page = open_board(browser, tmp_path / ('%d%s' % (width, theme)),
                          _long_rule_payload(),
                          viewport={'width': width, 'height': 900})
        if theme == 'light':
            page.click('[data-act="theme"]')
        assert page.get_attribute('html', 'data-theme') == theme
        for screen, sideways, broken in _every_screen(page):
            if sideways or broken:
                wrong.append((width, screen, sideways, broken))
        page.close()
    return wrong


# purlin: purlin_report PROOF-75
def test_every_screen_fits_every_width_in_the_dark_theme(browser, tmp_path):  # noqa: F811
    assert _fits_every_width(browser, tmp_path, 'dark') == []


# purlin: purlin_report PROOF-112
def test_every_screen_fits_every_width_in_the_light_theme(browser, tmp_path):  # noqa: F811
    assert _fits_every_width(browser, tmp_path, 'light') == []


# purlin: purlin_report PROOF-113
def test_a_long_tests_value_is_one_line_at_every_width(browser, tmp_path):  # noqa: F811
    for width in EVERY_WIDTH:
        page = open_board(browser, tmp_path / ('regulated%d' % width),
                          payload_named('regulated'),
                          viewport={'width': width, 'height': 900})
        assert _tests_value(page) == DOES_NOT_APPLY, width
        assert page.evaluate(SIDEWAYS) == 0, width
        assert page.evaluate(BROKEN_VALUES) == [], width
        page.close()


def _board_at(browser, tmp_path, name, width):
    return open_board(browser, tmp_path / ('%s%d' % (name, width)),
                      payload_named(name),
                      viewport={'width': width, 'height': 900})


# purlin: purlin_report PROOF-76
def test_four_boxes_to_a_row_at_768(browser, tmp_path):  # noqa: F811
    page = _board_at(browser, tmp_path, 'regulated', 768)
    assert len(page.query_selector_all('.tile')) == 4
    assert page.evaluate(FIRST_ROW) == 4
    page.close()


# purlin: purlin_report PROOF-161
def test_every_box_on_one_row_at_1024(browser, tmp_path):  # noqa: F811
    page = _board_at(browser, tmp_path, 'regulated', 1024)
    assert len(page.query_selector_all('.tile')) == 4
    assert page.evaluate(FIRST_ROW) == 4
    page.close()


# purlin: purlin_report PROOF-162
def test_two_boxes_to_a_row_at_390(browser, tmp_path):  # noqa: F811
    page = _board_at(browser, tmp_path, 'team', 390)
    assert len(page.query_selector_all('.tile')) == 3
    assert page.evaluate(FIRST_ROW) == 2
    page.close()


# purlin: purlin_report PROOF-163
def test_a_narrow_board_is_blocks_of_labelled_pairs(browser, tmp_path):  # noqa: F811
    page = _board_at(browser, tmp_path, 'team', 390)
    heads = page.is_visible('.th')
    receipt = ' '.join(page.inner_text('.tr[data-feature="receipt"]').split())
    label = page.eval_on_selector(
        '.tr[data-feature="receipt"] > div:nth-child(2)',
        "el => getComputedStyle(el, '::before').content")
    page.close()
    assert heads is False
    assert receipt.startswith('▶ receipt 1 '), receipt
    assert label == '"Rules"', label


# Each row of boxes, by the top of its boxes: the height of every box in it.
BOX_ROWS = """() => {
  const rows = {};
  document.querySelectorAll('.tile').forEach(t => {
    const box = t.getBoundingClientRect();
    const top = Math.round(box.top);
    (rows[top] = rows[top] || []).push(Math.round(box.height));
  });
  return Object.values(rows);
}"""


# purlin: purlin_report PROOF-175
def test_the_boxes_in_a_row_are_one_height(browser, tmp_path):  # noqa: F811
    for width in EVERY_WIDTH:
        page = _board_at(browser, tmp_path, 'regulated', width)
        rows = page.evaluate(BOX_ROWS)
        page.close()
        assert rows and all(len(set(row)) == 1 for row in rows), (width, rows)


# How many lines the `Passing` box's second line takes, counted as in
# `BROKEN_VALUES`, and its text as a person reads it.
TOTAL_LINE = """() => {
  const el = document.querySelector('.tile-t');
  const range = document.createRange();
  range.selectNodeContents(el);
  const tops = new Set(Array.from(range.getClientRects())
    .filter(r => r.width >= 1).map(r => Math.round(r.top)));
  return [el.innerText.trim(), tops.size];
}"""


# purlin: purlin_report PROOF-173
def test_the_total_is_one_line_at_every_width(browser, tmp_path):  # noqa: F811
    for width in EVERY_WIDTH:
        payload = payload_named('regulated')
        payload['summary']['rules'] = 563
        page = open_board(browser, tmp_path / ('total%d' % width), payload,
                          viewport={'width': width, 'height': 900})
        found = page.evaluate(TOTAL_LINE)
        page.close()
        assert found == ['563 RULES TOTAL', 1], (width, found)


# purlin: purlin_report PROOF-208
def test_a_narrow_anchors_section_is_blocks_of_labelled_pairs(browser,  # noqa: F811
                                                             tmp_path):
    page = _board_at(browser, tmp_path, 'team', 390)
    heads = page.is_visible('[data-table="anchors"] .th')
    block = ' '.join(page.inner_text(
        '[data-table="anchors"] .tr[data-feature="checkout_design"]').split())
    label = page.eval_on_selector(
        '[data-table="anchors"] .tr[data-feature="checkout_design"]'
        ' > div:nth-child(2)', "el => getComputedStyle(el, '::before').content")
    page.close()
    assert heads is False
    assert block.startswith('▶ checkout_design 1 '), block
    assert label == '"Rules"', label
