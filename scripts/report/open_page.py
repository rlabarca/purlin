#!/usr/bin/env python3
"""Open the dashboard page in the default browser: what `purlin:status --open`
runs once the status has written the page.

    sh "$PLUGIN_ROOT/scripts/purlin_python.sh" "$PLUGIN_ROOT/scripts/report/open_page.py" --project-root .

It hands `purlin-report.html` at the project root to the browser by its
`file:` address, the absolute path with every character a URL cannot carry
as itself percent-encoded, so a folder named with a space or a letter
outside ASCII opens the same on Windows, macOS and Linux. Python's own
`webbrowser` picks the browser: `open` on macOS, the shell's file
association on Windows, `xdg-open` and the like on Linux.

Where the browser reports it opened nothing, as over SSH or on a machine
with no desktop, and wherever the variable `CI` is set, it prints the page's
path for the person to open and exits 0: a page nobody could be shown is no
failure. With `CI` set no browser is started at all. A project with no page
gets one line naming the command that writes it, and exit 1.

The page holds its own data, so the browser needs no server and no other
file beside it.
"""

import argparse
import os
import pathlib
import sys
import webbrowser

PAGE_NAME = 'purlin-report.html'

OPENED = 'Opened %s in the default browser.'
NOT_OPENED = 'Dashboard: %s. Open it in a browser.'
NO_PAGE = ('purlin-report.html: no page yet. Run purlin:status, then '
           'purlin:status --open.')


def address(path):
    """The page's `file:` address: its absolute path, percent-encoded."""
    return pathlib.Path(os.path.abspath(path)).as_uri()


def open_page(project_root, out=print, browser=webbrowser.open):
    """Open the project's page. Returns the exit code."""
    path = os.path.abspath(os.path.join(project_root, PAGE_NAME))
    if not os.path.isfile(path):
        out(NO_PAGE)
        return 1
    if os.environ.get('CI'):
        out(NOT_OPENED % path)
        return 0
    try:
        opened = browser(address(path))
    except Exception:  # noqa: BLE001  a browser that fails opened nothing
        opened = False
    out((OPENED if opened else NOT_OPENED) % path)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Open the dashboard page in the default browser.')
    parser.add_argument('--project-root', default='.',
                        help='the top folder of the git checkout')
    args = parser.parse_args(argv)
    return open_page(args.project_root)


if __name__ == '__main__':
    sys.exit(main())
