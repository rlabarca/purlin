"""Capture the board screenshots the docs embed.

Two images, from the same fixture payloads `dev/test_purlin_report.py`
renders (`dev/fixtures/report/`) rather than from whatever this checkout
happens to hold: a screenshot taken from live data is out of date the moment
the data moves, and shows one project's names to every reader.

    python3 dev/build_report.py && python3 dev/capture_doc_screenshots.py

    dashboard-board.png   the board: the two facts in the top bar, the
                          `No proof`, `Passing` and `Strong` boxes, every
                          column, and login open with its description and
                          its rules
    dashboard-rule.png    one rule the audit found weak: its cells, what the
                          audit found, the planted bug its test missed and
                          its proofs

Each is the dark theme at 1440 wide, captured at 2x so the type stays crisp.
Uses dev/browser_launch.py, so it drives an installed Google Chrome when the
bundled Chromium cannot be downloaded. Writes only to docs/images/.
"""

import json
import os
import shutil
import sys
import tempfile

DEV = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)

from browser_launch import launch_browser  # noqa: E402

IMAGES_DIR = os.path.join(PROJECT_ROOT, 'docs', 'images')
PAGE = os.path.join(PROJECT_ROOT, 'scripts', 'report', 'purlin-report.html')
FIXTURES = os.path.join(DEV, 'fixtures', 'report')
VIEWPORT = {'width': 1440, 'height': 1000}
SCALE = 2

# name -> (fixture, the clicks that reach the screen)
SHOTS = (
    # login open: its description and its four rules with their badges.
    ('dashboard-board.png', 'regulated',
     ('[data-act="feature"][data-feature="login"]',)),
    # RULE-3 passes on two systems and the audit found it weak: its cells,
    # the findings, the explanation and the planted bug its test missed.
    ('dashboard-rule.png', 'regulated',
     ('[data-act="feature"][data-feature="login"]', '.rule[data-rule="RULE-3"]')),
)


def stage(root, fixture):
    """A directory holding the page with one fixture payload beside it."""
    shutil.copyfile(PAGE, os.path.join(root, 'purlin-report.html'))
    os.makedirs(os.path.join(root, '.purlin'), exist_ok=True)
    with open(os.path.join(FIXTURES, fixture + '.json'),
              encoding='utf-8') as handle:
        payload = json.load(handle)
    with open(os.path.join(root, '.purlin', 'report-data.js'), 'w',
              encoding='utf-8') as handle:
        handle.write('const PURLIN_DATA = ' + json.dumps(payload) + ';\n')
    return 'file://' + os.path.join(root, 'purlin-report.html')


def main():
    from playwright.sync_api import sync_playwright

    if not os.path.isfile(PAGE):
        sys.exit('No built page. Run python3 dev/build_report.py first.')
    os.makedirs(IMAGES_DIR, exist_ok=True)

    with sync_playwright() as driver:
        browser = launch_browser(driver, headless=True)
        for name, fixture, clicks in SHOTS:
            root = tempfile.mkdtemp(prefix='purlin-report-')
            url = stage(root, fixture)
            page = browser.new_page(viewport=VIEWPORT,
                                    device_scale_factor=SCALE)
            page.goto(url)
            page.wait_for_selector('.topbar', timeout=10000)
            for selector in clicks:
                page.click(selector)
            # The pointer leaves the page, so no row is caught mid-hover.
            page.mouse.move(0, 0)
            page.wait_for_timeout(300)
            page.screenshot(path=os.path.join(IMAGES_DIR, name),
                            full_page=True)
            page.close()
            shutil.rmtree(root, ignore_errors=True)
        browser.close()

    for name, _, _ in SHOTS:
        path = os.path.join(IMAGES_DIR, name)
        print('  %-28s %9d bytes' % (name, os.path.getsize(path)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
