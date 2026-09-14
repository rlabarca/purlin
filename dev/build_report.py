#!/usr/bin/env python3
"""Assemble the board page from its parts.

`scripts/report/src/` holds the page as a person edits it: one HTML shell, one
stylesheet, and one script per screen. This joins them into the single file a
project opens from disk and CI attaches to a pull request:

    python3 dev/build_report.py

Four substitutions, in this order:

`/*PURLIN:TOKENS*/`   every file in `design/tokens/`, in the order
                      `design/styles.css` imports them, inside the one
                      `<style id="purlin-tokens">` block. Every colour on the
                      page resolves here, which is why the block is named: the
                      page's own acceptance check reads it to prove no raw
                      colour was written anywhere else.
`/*PURLIN:STYLES*/`   `src/styles.css`.
`/*PURLIN:LOGO*/`     the mark from `design/assets/logo-datauri.js` in both
                      colourways. The light one is the dark one with the two
                      colours the design system already pairs them by, so the
                      page carries one copy of the geometry rather than two
                      hand-maintained data URIs.
`/*PURLIN:SCRIPTS*/`  the scripts, concatenated into one block so that the
                      functions one screen declares are in scope for the rest.

Comment lines and blank lines are dropped on the way in, from the CSS and the
JavaScript alike: the shipped page is one artifact to scroll and the parts
under `src/` are where the reasoning lives. Nothing else is rewritten, so a
line in the page is a line someone wrote. The output is a pure function of the
inputs: building twice gives the same bytes.

The page is also copied to the project root, where `.purlin/report-data.js`
sits beside it and the design files a spec names resolve.
"""

import os
import re
import shutil
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SRC = os.path.join(PROJECT_ROOT, 'scripts', 'report', 'src')
TOKENS = os.path.join(PROJECT_ROOT, 'design', 'tokens')
OUTPUT = os.path.join(PROJECT_ROOT, 'scripts', 'report', 'purlin-report.html')
ROOT_COPY = os.path.join(PROJECT_ROOT, 'purlin-report.html')

# The order design/styles.css imports them: raw palette, then the themes that
# alias it, then the scales, then the base element rules.
TOKEN_FILES = ('palette.css', 'theme-dark.css', 'theme-light.css',
               'typography.css', 'spacing.css', 'radii.css', 'elevation.css',
               'motion.css', 'base.css')

# app.js last: it is the only one that runs anything, and by then every
# function the screens declare has been hoisted.
SCRIPT_FILES = ('theme.js', 'filters.js', 'board.js', 'rule.js', 'review.js',
                'app.js')

# The two colours that separate the cream-on-navy mark from the navy-on-paper
# one, as design/assets/logo-light.svg pairs them.
LOGO_SWAPS = (('%23C0793F', '%238F5626'), ('%23E4DDD4', '%230C3444'))

_COMMENT_RE = re.compile(r'/\*.*?\*/', re.DOTALL)


def read(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()


def strip_css(text):
    """CSS with its comments and blank lines removed, one rule per line."""
    lines = [line.rstrip() for line in _COMMENT_RE.sub('', text).splitlines()]
    return '\n'.join(line for line in lines if line.strip())


def strip_js(text):
    """JavaScript with its comment lines and blank lines removed.

    Line by line rather than by one regular expression over the whole file: a
    `/*` inside a string literal is a comment to a regular expression and code
    to the browser, and a build that guesses wrong there deletes working code.
    """
    kept = []
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if in_block:
            if '*/' in stripped:
                in_block = False
            continue
        if stripped.startswith('/*'):
            if '*/' not in stripped:
                in_block = True
            continue
        if not stripped or stripped.startswith('//'):
            continue
        kept.append(line.rstrip())
    return '\n'.join(kept)


def token_block():
    return '\n'.join(strip_css(read(os.path.join(TOKENS, name)))
                     for name in TOKEN_FILES)


def logo_block():
    """Both colourways of the mark, as one JavaScript object."""
    source = read(os.path.join(PROJECT_ROOT, 'design', 'assets',
                               'logo-datauri.js'))
    match = re.search(r'"(data:image/svg\+xml,[^"]+)"', source)
    if not match:
        raise SystemExit('design/assets/logo-datauri.js names no data URI')
    dark = match.group(1)
    light = dark
    for old, new in LOGO_SWAPS:
        light = light.replace(old, new)
    return ('var PURLIN_LOGO = {dark: "%s",\n  light: "%s"};'
            % (dark, light))


def script_block():
    return '\n'.join(strip_js(read(os.path.join(SRC, name)))
                     for name in SCRIPT_FILES)


def build():
    page = read(os.path.join(SRC, 'page.html'))
    for marker, body in (
            ('/*PURLIN:TOKENS*/', token_block()),
            ('/*PURLIN:STYLES*/', strip_css(read(os.path.join(SRC,
                                                              'styles.css')))),
            ('/*PURLIN:LOGO*/', logo_block()),
            ('/*PURLIN:SCRIPTS*/', script_block())):
        if marker not in page:
            raise SystemExit('src/page.html has no %s marker' % marker)
        page = page.replace(marker, body)
    return page


def main():
    page = build()
    with open(OUTPUT, 'w', encoding='utf-8') as handle:
        handle.write(page)
    shutil.copyfile(OUTPUT, ROOT_COPY)
    lines = page.count('\n') + 1
    print('scripts/report/purlin-report.html  %d lines  %d bytes'
          % (lines, len(page.encode('utf-8'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
