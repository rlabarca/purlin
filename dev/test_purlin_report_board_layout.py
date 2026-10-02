"""The page at every width: no sideways scroll and no value on two lines, in
a browser.

The page and the samples are `dev/test_purlin_report.py`'s, opened the same way.
"""

import os
import sys

DEV = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DEV)

from test_purlin_report import (browser, open_board,  # noqa: E402,F401
                                payload_named)

# The five widths a person opens the page at, from a wide screen to a phone.
EVERY_WIDTH = (1500, 1280, 1024, 768, 390)

# Every element that holds one count, label, box or rule id, and how many
# lines its own text takes: the distinct tops of the line boxes a range over
# its content gives. A value broken inside itself has two.
BROKEN_VALUES = """() => {
  const sel = ['.trio', '.tr > div[data-label]', '.fact-l', '.fact b', '.stamp',
               '.tag',
               '.pill', '.os', '.rule .rid', 'h1', '.tile-v', '.tile-l',
               '.name .n', '.group .gt', '.group .gs', '.group .gc',
               '.kv dt', '.th > div', '.eyebrow', '.btn'];
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

# How far the page, or any table on it, scrolls sideways.
SIDEWAYS = """() => Math.max(document.documentElement.scrollWidth
  - document.documentElement.clientWidth, ...Array.from(
    document.querySelectorAll('.tbl')).map(t => t.scrollWidth - t.clientWidth))"""

# How many values the selector above measures on the open screen, so a screen
# that drew nothing cannot pass.
MEASURED = """() => document.querySelectorAll(
  '.fact b, .stamp, .pill, .tile-v, .rule .rid, h1, .kv dt').length"""


# purlin: purlin_report PROOF-75
def test_both_screens_fit_every_width_in_the_dark_theme(browser, tmp_path):  # noqa: F811
    wrong = []
    for width in EVERY_WIDTH:
        page = open_board(browser, tmp_path / str(width),
                          payload_named('regulated'),
                          viewport={'width': width, 'height': 900})
        assert page.get_attribute('html', 'data-theme') == 'dark'
        page.click('[data-act="feature"][data-feature="login"]')
        assert page.evaluate(MEASURED) > 10, width
        seen = [('board', page.evaluate(SIDEWAYS),
                 page.evaluate(BROKEN_VALUES))]
        page.click('.rule[data-feature="login"][data-rule="RULE-1"] .rt')
        assert page.inner_text('h1') == 'RULE-1', width
        seen.append(('rule', page.evaluate(SIDEWAYS),
                     page.evaluate(BROKEN_VALUES)))
        page.close()
        wrong += [(width, screen, sideways, broken)
                  for screen, sideways, broken in seen if sideways or broken]
    assert wrong == [], wrong


# Where the top bar's theme button and its two boxes stand, against the
# mark: the button's distance from the bar's right edge, whether its middle is
# on the mark's line, and how many boxes stand below the mark's line.
TOP_BAR = """() => {
  const bar = document.querySelector('.topbar').getBoundingClientRect();
  const mark = document.querySelector('.brand').getBoundingClientRect();
  const btn = document.querySelector('.topbar [data-act="theme"]')
    .getBoundingClientRect();
  const boxes = Array.from(document.querySelectorAll('.topbar .fact')).map(
    f => f.getBoundingClientRect());
  const middle = btn.top + btn.height / 2;
  return {
    gap: Math.round(bar.right - btn.right),
    onMarkLine: middle > mark.top && middle < mark.bottom,
    clear: boxes.every(b => b.right <= btn.left || b.top >= btn.bottom),
    boxes: boxes.length,
    below: boxes.filter(b => b.top >= mark.bottom).length,
  };
}"""


# purlin: purlin_report PROOF-248
def test_the_theme_button_keeps_the_top_right_and_the_boxes_move_whole(browser, tmp_path):  # noqa: F811
    seen = {}
    for width in (1500, 1280, 1120, 1024, 768, 390):
        page = open_board(browser, tmp_path / str(width),
                          payload_named('regulated'),
                          viewport={'width': width, 'height': 900})
        seen[width] = page.evaluate(TOP_BAR)
        page.close()
    for width, bar in seen.items():
        assert bar['boxes'] == 2, (width, bar)
        assert bar['onMarkLine'] and bar['clear'], (width, bar)
        assert bar['gap'] == (32 if width >= 1024 else 20), (width, bar)
        assert bar['below'] in (0, 2), (width, bar)
    assert seen[1500]['below'] == 0, seen[1500]
    assert seen[390]['below'] == 2, seen[390]
