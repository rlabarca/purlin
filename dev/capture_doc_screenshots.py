"""Regenerate the dashboard screenshots embedded in docs/dashboard-guide.md.

The three images under docs/images/ are hand-captured artifacts that go stale
silently: they sat at the June six-card summary strip long after the Proof
Design card shipped, because nothing regenerates them and nothing checks them.
A third file, dashboard-features.png, was a byte-identical copy of
dashboard-summary.png referenced by no markdown at all, and is gone.

Run after `purlin:status` (or any sync_status call) has refreshed
`.purlin/report-data.js`, so the capture reflects committed state:

    python3 dev/capture_doc_screenshots.py

Uses dev/browser_launch.py, so it drives an installed Google Chrome when the
bundled Chromium cannot be downloaded. Writes only to docs/images/.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))

from browser_launch import launch_browser  # noqa: E402

IMAGES_DIR = os.path.join(PROJECT_ROOT, 'docs', 'images')
DASHBOARD = 'file://' + os.path.join(PROJECT_ROOT, 'purlin-report.html')

# 1600px wide is the guide's reading width, and 2x keeps text crisp on retina
# without doubling the committed file size the way a 3200px viewport would.
VIEWPORT = {'width': 1600, 'height': 1200}
SCALE = 2


def main():
    from playwright.sync_api import sync_playwright

    if not os.path.isfile(os.path.join(PROJECT_ROOT, '.purlin', 'report-data.js')):
        sys.exit('No .purlin/report-data.js. Run purlin:status first.')

    os.makedirs(IMAGES_DIR, exist_ok=True)

    with sync_playwright() as pw:
        browser = launch_browser(pw, headless=True)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=SCALE)
        page.goto(DASHBOARD)
        page.wait_for_function(
            'typeof PURLIN_DATA !== "undefined" && '
            'document.querySelectorAll("tr.fr").length > 0'
        )

        # dashboard-categories.png first, while categories are still in their
        # default expanded state: the feature table cropped to the first
        # screenful of rows, so coverage bars and status badges stay legible.
        box = page.query_selector('.table-container').bounding_box()
        page.screenshot(
            path=os.path.join(IMAGES_DIR, 'dashboard-categories.png'),
            clip={
                'x': box['x'],
                'y': box['y'],
                'width': box['width'],
                'height': min(box['height'], 900),
            },
        )

        # dashboard-platforms.png: the Verified card's per-platform table,
        # captured before anything is collapsed. Only when the project
        # actually declares a platform; with none the card is inert and there
        # is nothing to photograph.
        if page.evaluate('!!(PURLIN_DATA && PURLIN_DATA.platform_testing)'):
            page.click('.sc-verified')
            page.wait_for_selector('#modal')
            modal = page.query_selector('.modal').bounding_box()
            page.screenshot(
                path=os.path.join(IMAGES_DIR, 'dashboard-platforms.png'),
                clip=modal,
            )
            page.keyboard.press('Escape')
            page.wait_for_function('!document.getElementById("modal")')

        # dashboard-summary.png: every category collapsed, then the whole page.
        # Expanded, the table runs 5,400px tall and nothing is readable at the
        # width the guide renders it; collapsed, one frame carries what the alt
        # text claims (summary strip, every category, and the anchors section,
        # which renders last and is off-screen in any top clip).
        page.eval_on_selector_all(
            'tr.cat-header.expanded', 'rows => rows.forEach(r => r.click())'
        )
        page.wait_for_function(
            'document.querySelectorAll("tr.cat-header.expanded").length === 0'
        )
        # Clip to the collapsed content rather than full_page: the viewport is
        # taller than the collapsed dashboard, and full_page pads the rest with
        # empty background.
        dash = page.query_selector('.dashboard').bounding_box()
        page.screenshot(
            path=os.path.join(IMAGES_DIR, 'dashboard-summary.png'),
            clip={
                'x': dash['x'],
                'y': dash['y'],
                'width': dash['width'],
                'height': dash['height'],
            },
        )
        browser.close()

    for name in ('dashboard-summary.png', 'dashboard-categories.png',
                 'dashboard-platforms.png'):
        path = os.path.join(IMAGES_DIR, name)
        if not os.path.isfile(path):
            print(f'  {name:28s} not captured (no platform declared)')
            continue
        print(f'  {name:28s} {os.path.getsize(path):>9,} bytes')


if __name__ == '__main__':
    main()
