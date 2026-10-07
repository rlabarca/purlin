"""The board page: how it is built, and what it shows.

Two halves. The first reads the built file as text and holds it to the design
system: one token block, no colour written anywhere else, no shadow, no
gradient, no request to anything outside the file. The second opens
it in a headless browser over `file://` with a fixture payload beside it, one
fixture per process, and reads what a person would see.

The samples under `dev/fixtures/report/` are payloads at schema 20, written on
the branch `main` at the commit `a1b2c3d` and stamped `2026-10-01T10:42:13Z`:
solo, which no audit has read and no one has signed, with one rule failing
its tests; team, with an audit, one spec to repair, which writes a proof
number twice, and one spec whose scope names a file not written yet;
regulated, signed as `0.1.0` four commits ago, with a rule whose audit found
a gap and a planted bug its test missed, a rule no audit has run on, a hand
check no sign-off has noted, a rule that passed on one system and failed on
another, and a rule of a remote anchor with no test. No rule of regulated
reads `failed`; one of solo's and two of team's do. A fourth, prompts, is a
project that tests a prompt: six rules of AI proofs, two of them reading
`graded`, one that failed a run on one model, one whose grader refused a
run, one with a model that gave no answer, and the warning that names that
model.

    python3 -m pytest dev/test_purlin_report.py -q
"""

import datetime
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
PAGE = os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html')
BUILD = os.path.join(DEV, 'build_report.py')
FIXTURES = os.path.join(DEV, 'fixtures', 'report')
PROCESSES = ('solo', 'team', 'regulated')
# Every sample the page's readability is measured over: the three, and the
# one whose rules have AI proofs.
WALKED = PROCESSES + ('prompts',)

sys.path.insert(0, DEV)

def read(path):
    with open(path, 'r', encoding='utf-8') as handle:
        return handle.read()


def build_page():
    """Run the build and return the page it wrote."""
    result = subprocess.run([sys.executable, BUILD], capture_output=True,
                            text=True, cwd=ROOT, timeout=120)
    assert result.returncode == 0, result.stderr
    return read(PAGE)


def token_block(page):
    """`(inside the token block, everything outside it)`."""
    start = page.index('id="purlin-tokens"')
    end = page.index('</style>', start)
    return page[start:end], page[:start] + page[end:]


def payload_named(name):
    return json.loads(read(os.path.join(FIXTURES, name + '.json')))


def without_proof_lines(payload):
    """The payload of the same project with every proof line taken out.

    A rule whose proof had a test keeps that test, marked with the rule's own
    id, so its passed cell reads as it did; a rule whose proof had none reads
    `no test` for the reason `sync_status` gives a rule no proof line names.
    The counts of proof lines go to zero with them.
    """
    for feature in payload['features']:
        for rule in feature['rules']:
            proofs = rule['proofs']
            rule['proofs'] = []
            rule['tests'] = [dict(test, result='pass') for proof in proofs
                             for test in proof['tests']]
            rule['flags']['no_proof'] = True
            if proofs and not any(proof['tests'] for proof in proofs):
                rule['cells']['passed'].update(
                    {'word': 'no test', 'reasons': ['no proof written']})
        for counted in (feature['rollup'], payload['summary']):
            counted.update({'proofs': 0, 'proofs_without_test': 0,
                            'proofs_without_test_ids': []})
    return payload


def with_export_rule_2_unproved(payload):
    """The regulated payload with export `RULE-2`'s one proof taken out.

    The rule's tests pass, so the payload gives it the kind `no_proof`,
    whose line of what is left comes first.
    """
    export = next(f for f in payload['features'] if f['name'] == 'export')
    rule = next(r for r in export['rules'] if r['id'] == 'RULE-2')
    assert rule['left'] is None
    rule['proofs'] = []
    rule['left'] = 'no_proof'
    payload['left'].insert(0, {'kind': 'no_proof', 'count': 1,
                               'text': '1 rule to write a proof for',
                               'command': 'purlin:spec'})
    return payload


@pytest.fixture(scope='module')
def page_text():
    return build_page()


@pytest.fixture(scope='module')
def browser():
    playwright = pytest.importorskip('playwright.sync_api')
    from browser_launch import launch_browser
    with playwright.sync_playwright() as driver:
        instance = launch_browser(driver, headless=True)
        yield instance
        instance.close()


def open_board(browser, tmp_path, payload, viewport=None, clock_at=None,
               timezone='UTC'):
    """The page, opened over file:// with this payload beside it.

    The browser's timezone is `timezone`, never the machine's own, since the
    page shows each time as the person looking at it reads the clock.

    `clock_at` hands the page a clock stopped at that moment, so a test can
    advance it and read what the page makes of the time passing.
    """
    root = str(tmp_path)
    os.makedirs(root, exist_ok=True)
    shutil.copyfile(PAGE, os.path.join(root, 'purlin-report.html'))
    os.makedirs(os.path.join(root, '.purlin'), exist_ok=True)
    with open(os.path.join(root, '.purlin', 'report-data.js'), 'w',
              encoding='utf-8') as handle:
        handle.write('const PURLIN_DATA = ' + json.dumps(payload) + ';\n')
    page = browser.new_page(viewport=viewport or {'width': 1440,
                                                  'height': 1000},
                            timezone_id=timezone)
    if clock_at is not None:
        page.clock.install(time=clock_at)
    page.goto('file://' + os.path.join(root, 'purlin-report.html'))
    page.wait_for_selector('.topbar', timeout=10000)
    return page


def open_sample(browser, tmp_path, name, change=None, **options):
    """One sample's board, after `change(payload)` where the proof alters it."""
    payload = payload_named(name)
    if change is not None:
        change(payload)
    return open_board(browser, tmp_path, payload, **options)


def rule_of(payload, feature, rule_id):
    """One rule of a payload, by the spec that owns it and its id."""
    owner = next(f for f in payload['features'] if f['name'] == feature)
    return next(r for r in owner['rules'] if r['id'] == rule_id)


def texts(page, selector):
    return page.eval_on_selector_all(
        selector, 'els => els.map(e => e.textContent.trim())')


def feature_names(page):
    return texts(page, '.tr .name .n')


def head_labels(page):
    """The spec table's column headings, in the order they are drawn."""
    return texts(page, '[data-table="specs"] .th > div')


def open_rule(page, feature, rule_id):
    """Open a spec on the board and then one of its rules' screens."""
    page.click('[data-act="feature"][data-feature="%s"]' % feature)
    page.click('.rule[data-feature="%s"][data-rule="%s"]' % (feature, rule_id))


# How many step boxes each sample draws: `No proof`, since all three write
# proof lines, `Passing`, `Failing` where a rule's passed cell reads `failed`,
# and `Strong` where the audit read the project.
TILES = {'solo': 3, 'team': 4, 'regulated': 3}


def rule_ids(page):
    return texts(page, '.rule .rid')


# Each piece of text under the elements `selector` names that a person does
# not see: its element, or one around it, is not displayed, is hidden, is
# drawn through an opacity, is clipped, has no room, is cut off by a box
# that hides what runs past it, or is set in no size or in no colour.
UNDRAWN = r"""(selector) => {
  const drawn = el => {
    let through = 1;
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (s.display === 'none' || s.visibility !== 'visible') return false;
      if (s.clipPath !== 'none') return false;
      through *= Number(s.opacity);
      const r = n.getBoundingClientRect();
      if (r.width <= 1 || r.height <= 1) return false;
      if ((s.overflowX === 'hidden' || s.overflowX === 'clip')
          && n.scrollWidth > n.clientWidth + 1) return false;
      if ((s.overflowY === 'hidden' || s.overflowY === 'clip')
          && n.scrollHeight > n.clientHeight + 1) return false;
    }
    const s = getComputedStyle(el);
    if (parseFloat(s.fontSize) < 1) return false;
    if (s.color === 'transparent' || /^rgba\(.*, 0\)$/.test(s.color)) {
      return false;
    }
    return through === 1;
  };
  const out = [];
  document.querySelectorAll(selector).forEach(root => {
    const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    for (let node = walk.nextNode(); node; node = walk.nextNode()) {
      if (node.textContent.trim() && !drawn(node.parentElement)) {
        out.push(node.textContent);
      }
    }
  });
  return out;
}"""
# The two marks a notice keeps for a reader of the page's text and does not
# draw: the one after its name and the one after its kind.
NOT_DRAWN_IN_A_NOTICE = (': ', '. ')


def undrawn(page, selector):
    """Each piece of text under `selector` that is not drawn."""
    return page.evaluate(UNDRAWN, selector)


def boxes(page):
    """Each box on the strip: its label, its count and the colour it is in."""
    return page.eval_on_selector_all(
        '.tile', "els => els.map(e => ["
        "e.querySelector('.tile-l').textContent.trim(),"
        "e.querySelector('.tile-v').textContent.trim(),"
        "getComputedStyle(e.querySelector('.tile-v')).color])")


# Every operating-system box on the open rule screen: its label, its tone and
# the hover it carries.
PLATFORM_BOXES = """() => Array.from(document.querySelectorAll('.kv .os')).map(
  s => ({os: s.textContent.trim(),
         tone: s.classList.contains('pass') ? 'pass'
           : s.classList.contains('fail') ? 'fail' : 'none',
         title: s.getAttribute('title'),
         colour: getComputedStyle(s).color}))"""

# Every cell of every spec row, keyed by the spec name, as the `title` the
# hover carries rather than the text under it.
HOVERS = """els => {
  return els.map(e => {
    const head = Array.from(e.closest('.tbl').querySelectorAll('.th > div'))
      .map(d => d.textContent.trim());
    const row = {name: e.querySelector('.name .n').textContent.trim()};
    head.forEach((label, i) => {
      const node = e.children[i].querySelector('[title]');
      row[label] = node ? node.getAttribute('title') : null;
    });
    return row;
  });
}"""


def hovers(page):
    """The hover of each cell of each spec row, keyed by the spec name."""
    return {row['name']: row
            for row in page.eval_on_selector_all('.tr', HOVERS)}


# Every panel on the open screen that carries a heading: the heading and each
# paragraph under it, as a person reads them.
PANELS = """() => Array.from(document.querySelectorAll('.panel')).filter(
  p => p.querySelector('h2')).map(p => ({
    head: p.querySelector('h2').textContent.trim(),
    lines: Array.from(p.querySelectorAll('p')).map(
      e => e.innerText.trim().replace(/\\s+/g, ' '))}))"""


def panel_lines(page, head):
    """The lines of the one panel headed `head` on the open screen."""
    found = [panel['lines'] for panel in page.evaluate(PANELS)
             if panel['head'] == head]
    assert len(found) == 1, (head, page.evaluate(PANELS))
    return found[0]


# ---------------------------------------------------------------------------
# The built file
# ---------------------------------------------------------------------------

# purlin: purlin_report PROOF-122
def test_the_page_at_the_project_root_is_the_built_page(page_text):
    assert os.path.isfile(os.path.join(ROOT, 'purlin-report.html'))
    built = read(os.path.join(ROOT, *'scripts/report/purlin-report.html'.split('/')))
    assert read(os.path.join(ROOT, 'purlin-report.html')) == built == page_text
    # Character for character, the ends of the lines included: the two
    # files hold the same bytes.
    with open(os.path.join(ROOT, 'purlin-report.html'), 'rb') as handle:
        at_root = handle.read()
    with open(os.path.join(ROOT, 'scripts', 'report', 'purlin-report.html'),
              'rb') as handle:
        assert at_root == handle.read()


# purlin: purlin_report PROOF-3
def test_no_colour_is_written_as_hex_outside_the_token_block(browser,
                                                             tmp_path):
    inside, outside = token_block(build_page())
    assert re.search(r'--canvas\s*:', inside)
    assert re.findall(r'#[0-9a-fA-F]{3,8}\b', outside) == []
    # A script can write a colour in two halves, `'#' + 'C0793F'`: read the
    # page again with each join of two quoted strings closed up, whichever
    # quotation mark each half is in.
    joined = re.sub(r'''['"]\s*\+\s*['"]''', '', outside)
    assert re.findall(r'#[0-9a-fA-F]{3,8}\b', joined) == []
    # However a script puts one together, a colour it writes is on the page
    # once the page is drawn: each sample's board, every spec open, holds
    # none outside the token block either.
    for name in WALKED:
        page = open_board(browser, tmp_path / name, payload_named(name))
        for spec in feature_names(page):
            page.click('[data-act="feature"][data-feature="%s"]' % spec)
        drawn = page.evaluate(
            "() => { const copy = document.documentElement.cloneNode(true);"
            " copy.querySelectorAll('#purlin-tokens, script').forEach("
            "e => e.remove()); return copy.outerHTML; }")
        page.close()
        assert len(drawn) > 1000, name
        assert re.findall(r'#[0-9a-fA-F]{3,8}\b', drawn) == [], name


# purlin: purlin_report PROOF-4
def test_no_shadow_and_no_gradient(page_text, browser, tmp_path):
    _inside, outside = token_block(page_text)
    # A stylesheet reads a property at any casing, so the page is read so too.
    assert 'box-shadow' not in outside.lower()
    assert 'gradient' not in page_text.lower()
    # A stylesheet also reads a name written with an escape, `box\-shadow`:
    # the page is read as the browser read it. No style rule outside the
    # token block sets a shadow or holds a gradient, and no element's own
    # style does.
    assert 'box-shadow' not in outside.lower().replace('\\', '')
    page = open_board(browser, tmp_path, payload_named('regulated'))
    rules, found = page.evaluate("""() => {
      const found = [];
      let count = 0;
      const read = rules => { for (const rule of rules) {
        if (rule.cssRules) { read(rule.cssRules); }
        if (!rule.style) { continue; }
        count += 1;
        if (rule.style.getPropertyValue('box-shadow')
            || /gradient/i.test(rule.cssText)) { found.push(rule.cssText); }
      } };
      for (const sheet of document.styleSheets) {
        if (sheet.ownerNode && sheet.ownerNode.id === 'purlin-tokens') {
          continue;
        }
        read(sheet.cssRules);
      }
      document.querySelectorAll('[style]').forEach(e => {
        if (e.style.boxShadow || /gradient/i.test(e.getAttribute('style'))) {
          found.push(e.outerHTML.slice(0, 120));
        }
      });
      return [count, found];
    }""")
    page.close()
    assert rules > 50, rules
    assert found == []


# purlin: purlin_report PROOF-5
def test_no_request_to_anything_outside_the_page(page_text, browser,
                                                 tmp_path):
    """The page opens from a disk with no network behind it."""
    # Nothing is fetched: no stylesheet link, no remote script or image, no
    # request of any kind. The page is the whole page.
    assert '<link' not in page_text
    assert '@import' not in page_text
    assert 'fetch(' not in page_text
    # An address in double quotes, in single quotes or in none, at any casing.
    assert re.findall(r'''(?:src|href)\s*=\s*["']?\s*https?:''', page_text,
                      re.I) == []
    # An address a script sets is one the page asks for once it is open:
    # opened beside its data, the page asks for nothing but files on the
    # disk, and no element it drew holds an address on another host.
    root = str(tmp_path)
    shutil.copyfile(PAGE, os.path.join(root, 'purlin-report.html'))
    os.makedirs(os.path.join(root, '.purlin'))
    with open(os.path.join(root, '.purlin', 'report-data.js'), 'w',
              encoding='utf-8') as handle:
        handle.write('const PURLIN_DATA = '
                     + json.dumps(payload_named('regulated')) + ';\n')
    page = browser.new_page()
    asked = []
    page.on('request', lambda request: asked.append(request.url))
    page.route(re.compile(r'^(?!file:|data:)'), lambda route: route.abort())
    page.goto('file://' + os.path.join(root, 'purlin-report.html'))
    page.wait_for_selector('.topbar', timeout=10000)
    page.wait_for_timeout(500)
    addresses = page.evaluate(
        "() => [...document.querySelectorAll('[src], [href]')].map("
        "e => e.getAttribute('src') || e.getAttribute('href'))")
    page.close()
    assert [url for url in asked if url.startswith('file:')] != [], asked
    assert [url for url in asked
            if not url.startswith(('file:', 'data:'))] == [], asked
    assert [address for address in addresses
            if re.match(r'\s*(?:https?:|//)', address, re.I)] == []


# The characters a page could draw as an affordance: arrows, geometric
# shapes, the symbols and dingbats blocks, and the emoji planes.
GLYPH_RANGES = ((0x2190, 0x21FF), (0x2300, 0x23FF), (0x25A0, 0x25FF),
                (0x2600, 0x27BF), (0x2900, 0x297F), (0x2B00, 0x2BFF),
                (0x1F000, 0x1FAFF))
ALLOWED_GLYPHS = (u'\u25b6', u'\u25bc', u'\u25b2', u'\u2192', u'\u25d0',
                  u'\u25d1')


def glyphs_in(text):
    """Every affordance character the text holds, whether written as itself
    or as a `\\uXXXX` escape inside a script."""
    found = set(ch for ch in text if any(
        low <= ord(ch) <= high for low, high in GLYPH_RANGES))
    for code in re.findall(r'\\u([0-9a-fA-F]{4})', text):
        if any(low <= int(code, 16) <= high for low, high in GLYPH_RANGES):
            found.add(chr(int(code, 16)))
    return found


# purlin: purlin_report PROOF-6
def test_affordances_are_unicode_glyphs_not_an_icon_set(page_text, browser,
                                                        tmp_path):
    """The system ships no icon set, so the page draws none, and the glyphs
    it draws are the six the design allows."""
    found = glyphs_in(page_text)
    assert {u'\u25b6', u'\u25bc', u'\u25d0', u'\u25d1'} <= found, found
    assert found - set(ALLOWED_GLYPHS) == set(), found
    # A browser reads a tag at any casing, so `<SVG` is an element too.
    assert page_text.lower().count('<svg') == 0
    assert 'icon' not in page_text.lower()
    # A script can make a character from its number, so the page is read as
    # it is drawn too: each sample's board, with every spec closed and then
    # every spec open, draws no shape but the six.
    for name in WALKED:
        page = open_board(browser, tmp_path / name, payload_named(name))
        drawn = page.evaluate('document.body.innerText')
        for spec in feature_names(page):
            page.click('[data-act="feature"][data-feature="%s"]' % spec)
        drawn += page.evaluate('document.body.innerText')
        page.close()
        assert u'\u25b6' in drawn and u'\u25bc' in drawn, name
        assert glyphs_in(drawn) - set(ALLOWED_GLYPHS) == set(), (
            name, glyphs_in(drawn))


# ---------------------------------------------------------------------------
# What a person sees
# ---------------------------------------------------------------------------

def headings_of(browser, tmp_path, payload):
    page = open_board(browser, tmp_path, payload)
    found = head_labels(page)
    page.close()
    return found


# purlin: purlin_report PROOF-9
def test_proof_lines_and_no_audit_show_four_columns(browser, tmp_path):
    payload = payload_named('solo')
    assert payload['summary']['proofs'] > 0
    assert payload['summary']['audit']['strong'] == 0
    assert payload['summary']['audit']['weak'] == 0
    assert headings_of(browser, tmp_path, payload) == [
        'Spec', 'Rules', 'Proofs', 'Tests']


# purlin: purlin_report PROOF-124
def test_an_audit_that_found_strong_and_weak_adds_the_strong_column(
        browser, tmp_path):
    payload = payload_named('team')
    assert payload['summary']['audit']['strong'] > 0
    assert payload['summary']['audit']['weak'] > 0
    assert headings_of(browser, tmp_path, payload) == [
        'Spec', 'Rules', 'Proofs', 'Tests', 'Strong']


# purlin: purlin_report PROOF-32
def test_the_rule_screen_says_what_each_system_found(browser, tmp_path):
    """A rule can pass on one operating system and fail on another.

    The systems are the rule's business, so they live on its screen, drawn
    from the platforms its passed cell carries, in the payload's words.
    """
    page = open_sample(browser, tmp_path, 'regulated')
    open_rule(page, 'login', 'RULE-4')
    found = page.evaluate(PLATFORM_BOXES)
    last_run = page.evaluate(KV_ROWS)['Last run']
    assert [(b['os'], b['tone']) for b in found] == [('Lin', 'pass'),
                                                     ('Win', 'fail')]
    assert found[0]['colour'] == page.evaluate(RESOLVE_TOKEN, '--state-pass')
    assert found[1]['colour'] == page.evaluate(RESOLVE_TOKEN, '--state-fail')
    assert found[1]['title'].startswith('Windows · failed · ci · ')
    assert re.match(r'ci · (\d+ (minutes|hours|days) old|less than a minute '
                    r'old)$', last_run), last_run
    page.close()


# purlin: purlin_report PROOF-92
def test_a_manual_proof_that_ran_nowhere_draws_no_system_box(browser,
                                                             tmp_path):
    payload = payload_named('regulated')
    assert hand_check_rule(payload)['cells']['passed']['platforms'] == {}
    page = open_board(browser, tmp_path, payload)
    open_rule(page, 'invoice', 'RULE-3')
    assert 'RULE-3' in page.inner_text('h1')
    assert page.evaluate(PLATFORM_BOXES) == []
    page.close()


def _dark_then_toggled(page):
    """The ground, the ink and the mark in the dark theme, then the theme
    button pressed once: `(dark, light)`, each `(ground, ink, mark)`."""
    def look():
        return (page.evaluate('getComputedStyle(document.body).backgroundColor'),
                page.evaluate('getComputedStyle(document.body).color'),
                page.get_attribute('#brand-mark', 'src'))
    assert page.get_attribute('html', 'data-theme') == 'dark'
    dark = look()
    page.click('[data-act="theme"]')
    return dark, look()


@pytest.mark.parametrize('process', PROCESSES)
# purlin: purlin_report PROOF-128
def test_the_theme_button_swaps_to_light(browser, tmp_path, process):
    page = open_board(browser, tmp_path, payload_named(process))
    dark, light = _dark_then_toggled(page)
    assert page.get_attribute('html', 'data-theme') == 'light'
    assert [one != two for one, two in zip(dark, light)] == [True] * 3, (
        dark, light)
    tiles = page.query_selector_all('.tile')
    assert len(tiles) == TILES[process]
    # Drawn, not only in the page: each box takes up room on the screen.
    assert [tile.is_visible() for tile in tiles] == [True] * TILES[process]
    assert [bool(tile.bounding_box()) and tile.bounding_box()['width'] > 0
            and tile.bounding_box()['height'] > 0 for tile in tiles] == [
                True] * TILES[process]
    # And seen: no part of a box, its label or its count is drawn through an
    # opacity, clipped or cut off.
    assert undrawn(page, '.tile') == []
    assert len(texts(page, '.tile .tile-v')) == TILES[process]
    page.close()


def theme_button(page):
    """The theme button's glyph, its hover and its accessible name."""
    button = page.locator('[data-act="theme"]')
    return [button.inner_text(), button.get_attribute('title'),
            page.get_by_role('button', name=button.get_attribute('aria-label'),
                             exact=True).get_attribute('aria-label')]


# purlin: purlin_report PROOF-182
def test_the_theme_button_reads_the_theme_it_turns_to(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert page.get_attribute('html', 'data-theme') == 'dark'
    assert theme_button(page) == ['\u25d0', 'Light theme', 'Light theme']
    page.close()


# purlin: purlin_report PROOF-185
def test_a_chosen_theme_survives_a_reload(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="theme"]')
    assert page.get_attribute('html', 'data-theme') == 'light'
    page.reload()
    page.wait_for_selector('.topbar', timeout=10000)
    assert page.get_attribute('html', 'data-theme') == 'light'
    assert theme_button(page) == ['\u25d1', 'Dark theme', 'Dark theme']
    page.close()


# The value a CSS colour token resolves to, read back as the browser writes
# every computed colour, so a token and a painted surface compare as strings.
RESOLVE_TOKEN = """(name) => {
  const probe = document.createElement('span');
  probe.style.color = getComputedStyle(document.documentElement)
    .getPropertyValue(name).trim();
  document.body.appendChild(probe);
  const value = getComputedStyle(probe).color;
  probe.remove();
  return value;
}"""


# ---------------------------------------------------------------------------
# The step boxes
# ---------------------------------------------------------------------------

# purlin: purlin_report PROOF-8
def test_a_step_box_counts_the_rules_that_reached_it(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['summary']['steps'] == {'passed': 7, 'graded': 0,
                                           'by_hand': 1}
    assert payload['summary']['audit']['strong'] == 3
    page = open_board(browser, tmp_path, payload)
    found = boxes(page)
    assert [(label, count) for label, count, _ in found] == [
        ('No proof', '0'), ('Passing', '7'), ('Strong', '3')], found
    # Left to right as they are drawn: each box by its left edge on screen.
    drawn = page.eval_on_selector_all(
        '.tile', "els => els.map(e => [e.getBoundingClientRect().left,"
        " e.getBoundingClientRect().top,"
        " e.querySelector('.tile-l').textContent.trim()])")
    assert [label for _, _, label in sorted(drawn)] == [
        'No proof', 'Passing', 'Strong'], drawn
    assert len({top for _, top, _ in drawn}) == 1, drawn
    assert page.eval_on_selector_all(
        '.tile-l', 'els => els.map(e => getComputedStyle(e).textTransform)'
    ) == ['uppercase'] * 4
    warn = page.evaluate(RESOLVE_TOKEN, '--state-warn')
    assert [colour for _, _, colour in found[1:]] == [warn] * 2, found
    page.close()


def every_tested_rule_passing(payload):
    """The regulated sample with every rule but invoice `RULE-3`, the hand
    check no sign-off has noted, given a passing test, as the payload
    carries it: the passed cell, the bucket, the kind of work left, and the
    counts over them."""
    for feature in payload['features']:
        for rule in feature['rules']:
            if rule['cells']['passed']['word'] == 'checked at sign-off':
                continue
            rule['cells']['passed'].update(word='passed', reasons=[])
            rule['bucket'] = 'passed'
            rule['left'] = None
            for flag in ('failing', 'partial', 'out_of_date'):
                rule['flags'][flag] = False
        rollup = feature['rollup']
        rollup.update(untested=0, failing=0, partial=0,
                      passed=rollup['rules'] - rollup['by_hand'])
    summary = payload['summary']
    summary.update(untested=0, failing=0, partial=0,
                   passed=summary['rules'] - summary['by_hand'])
    summary['steps']['passed'] = summary['passed']


# purlin: purlin_report PROOF-247
def test_passing_is_complete_once_every_other_rule_is_checked_at_sign_off(
        browser, tmp_path):
    payload = payload_named('regulated')
    every_tested_rule_passing(payload)
    assert payload['summary']['rules'] == 11
    assert payload['summary']['steps'] == {'passed': 10, 'graded': 0,
                                           'by_hand': 1}
    page = open_board(browser, tmp_path, payload)
    found = {label: (count, colour) for label, count, colour in boxes(page)}
    passing = page.evaluate(RESOLVE_TOKEN, '--state-pass')
    page.close()
    assert found['Passing'] == ('10', passing), found


def second_lines(page):
    """Each box's label and the second line under it, or None."""
    return page.eval_on_selector_all(
        '.tile', "els => els.map(e => [e.querySelector('.tile-l')"
        ".textContent.trim(), e.querySelector('.tile-t')"
        " ? e.querySelector('.tile-t').innerText.trim() : null])")


# The face, size, colour and casing an element is drawn in.
LOOK = """el => { const s = getComputedStyle(el);
  return [s.fontFamily, s.fontSize, s.color, s.textTransform,
          s.letterSpacing]; }"""


# purlin: purlin_report PROOF-170
def test_the_passing_box_carries_the_total(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['summary']['rules'] == 11
    page = open_board(browser, tmp_path, payload)
    assert second_lines(page) == [['No proof', None],
                                  ['Passing', '11 RULES TOTAL'],
                                  ['Strong', None]]
    total = page.query_selector('.tile-t')
    label = total.evaluate_handle('el => el.previousElementSibling')
    assert label.evaluate(LOOK) == total.evaluate(LOOK)
    # The face is the family and how it is set: upright or italic, its
    # weight, its width, its variant and any line through or under it.
    face = ("el => { const s = getComputedStyle(el); return [s.fontFamily,"
            " s.fontStyle, s.fontWeight, s.fontStretch, s.fontVariant,"
            " s.textDecorationLine, s.fontSize, s.color]; }")
    assert label.evaluate(face) == total.evaluate(face)
    assert label.evaluate(face)[1] == 'normal'
    assert undrawn(page, '.tile-l') == []
    # The colour as it is seen: neither line is drawn through an opacity.
    through = ("el => { let o = 1; for (let n = el; n && n.nodeType === 1;"
               " n = n.parentElement) { o *= Number(getComputedStyle(n)"
               ".opacity); } return o; }")
    assert label.evaluate(through) == total.evaluate(through) == 1
    page.close()


# ---------------------------------------------------------------------------
# A failing rule is on the first screen
# ---------------------------------------------------------------------------

def box_hovers(page):
    """Each box's label and its hover."""
    return dict(page.eval_on_selector_all(
        '.tile', "els => els.map(e => [e.querySelector('.tile-l')"
        ".textContent.trim(), e.getAttribute('title')])"))


def failed_rules(payload):
    """`[(spec, rule id)]` for each rule whose passed cell reads `failed`."""
    return [(feature['name'], rule['id']) for feature in payload['features']
            for rule in feature['rules']
            if rule['cells']['passed']['word'] == 'failed']


def given_failed(payload, feature, rule_id):
    """The payload with one more rule's passed cell reading `failed`."""
    rule = rule_of(payload, feature, rule_id)
    rule['cells']['passed'].update(word='failed', reasons=['a test failed'])


# purlin: purlin_report PROOF-263
def test_a_failing_box_counts_the_rules_that_failed(browser, tmp_path):
    payload = payload_named('solo')
    assert failed_rules(payload) == [('invoice', 'RULE-2')]
    page = open_board(browser, tmp_path, payload)
    found = boxes(page)
    fail = page.evaluate(RESOLVE_TOKEN, '--state-fail')
    hover = box_hovers(page)['Failing']
    page.close()
    assert [label for label, _, _ in found] == ['No proof', 'Passing',
                                                'Failing'], found
    assert found[2][1:] == ['1', fail], found
    assert hover == 'invoice · 1', hover


# purlin: purlin_report PROOF-264
def test_the_failing_box_stands_between_passing_and_strong(browser, tmp_path):
    payload = payload_named('team')
    given_failed(payload, 'security_baseline', 'RULE-1')
    assert failed_rules(payload) == [
        ('refund', 'RULE-1'), ('refund', 'RULE-2'),
        ('security_baseline', 'RULE-1')]
    page = open_board(browser, tmp_path, payload)
    found = boxes(page)
    hover = box_hovers(page)['Failing']
    page.close()
    assert [label for label, _, _ in found] == [
        'No proof', 'Passing', 'Failing', 'Strong'], found
    assert [(label, count) for label, count, _ in found][1:] == [
        ('Passing', str(payload['summary']['steps']['passed'])),
        ('Failing', '3'),
        ('Strong', str(payload['summary']['audit']['strong']))], found
    assert hover == 'refund · 2\nsecurity_baseline · 1', hover


# purlin: purlin_report PROOF-265
def test_no_failing_box_where_no_rule_failed(browser, tmp_path):
    payload = payload_named('regulated')
    assert failed_rules(payload) == []
    assert rule_of(payload, 'login', 'RULE-4')['cells']['passed'][
        'word'] == 'partial'
    page = open_board(browser, tmp_path, payload)
    found = boxes(page)
    specs = listed_in(page, 'specs')
    anchors = listed_in(page, 'anchors')
    bands = texts(page, '.group .gt')
    page.close()
    assert [label for label, _, _ in found] == ['No proof', 'Passing',
                                                'Strong'], found
    names = [feature['name'] for feature in payload['features']]
    assert specs == [name for name in names if name in specs] == [
        'login', 'invoice', 'export'], specs
    assert anchors == ['checkout_design', 'security_baseline'], anchors
    assert bands == ['auth', 'billing'], bands


# purlin: purlin_report PROOF-266
def test_a_spec_and_a_category_with_a_failing_rule_come_first(browser,
                                                              tmp_path):
    payload = payload_named('team')
    assert [(feature['category'], feature['name'])
            for feature in payload['features'] if not feature['is_anchor']
            ] == [('auth', 'login'), ('billing', 'invoice'),
                  ('billing', 'receipt'), ('billing', 'refund')]
    assert {name for name, _ in failed_rules(payload)} == {'refund'}
    page = open_board(browser, tmp_path, payload)
    bands = texts(page, '.group .gt')
    specs = listed_in(page, 'specs')
    page.close()
    assert bands == ['billing', 'auth'], bands
    assert specs == ['refund', 'invoice', 'receipt', 'login'], specs


# purlin: purlin_report PROOF-267
def test_an_anchor_with_a_failing_rule_comes_first(browser, tmp_path):
    payload = payload_named('team')
    given_failed(payload, 'security_baseline', 'RULE-1')
    page = open_board(browser, tmp_path, payload)
    anchors = listed_in(page, 'anchors')
    page.close()
    assert anchors == ['security_baseline', 'checkout_design'], anchors


# purlin: purlin_report PROOF-278
def test_the_spec_table_stands_first_where_a_spec_fails_and_no_anchor_does(
        browser, tmp_path):
    payload = payload_named('team')
    assert {name for name, _ in failed_rules(payload)} == {'refund'}
    page = open_board(browser, tmp_path, payload)
    labels = section_labels(page)
    order = page.evaluate(
        "() => { const top = s => document.querySelector(s)"
        ".getBoundingClientRect().top; return [top('.strip'),"
        " top('[data-table=\"specs\"]'), top('[data-table=\"anchors\"]')]; }")
    page.close()
    assert labels == ['SPECS', 'ANCHORS'], labels
    assert order == sorted(order), order


# purlin: purlin_report PROOF-279
def test_the_anchors_stand_first_where_an_anchor_fails(browser, tmp_path):
    payload = payload_named('team')
    given_failed(payload, 'security_baseline', 'RULE-1')
    assert {name for name, _ in failed_rules(payload)} == {
        'refund', 'security_baseline'}
    page = open_board(browser, tmp_path, payload)
    labels = section_labels(page)
    page.close()
    assert labels == ['ANCHORS', 'SPECS'], labels


# purlin: purlin_report PROOF-268
def test_two_failing_specs_keep_the_datas_order(browser, tmp_path):
    payload = payload_named('team')
    given_failed(payload, 'invoice', 'RULE-2')
    page = open_board(browser, tmp_path, payload)
    specs = listed_in(page, 'specs')
    page.close()
    assert specs == ['invoice', 'refund', 'receipt', 'login'], specs


def forty_passing_specs_then_one_failing(payload):
    """The regulated sample grown by 40 specs whose rules pass, 10 in each
    of the categories `gamma`, `delta`, `kappa` and `sigma`, then `zz_last`
    in the category `zeta`, whose one rule reads `failed`: the last spec of
    the last category the data lists."""
    model = next(f for f in payload['features'] if f['name'] == 'export')

    def spec(name, category, word):
        made = json.loads(json.dumps(model))
        made.update(name=name, category=category,
                    spec_path='specs/%s/%s.md' % (category, name))
        made['rules'] = made['rules'][1:]
        for rule in made['rules']:
            rule['feature'] = name
            rule['cells']['passed'].update(word=word, reasons=[])
        return made
    for category in ('gamma', 'delta', 'kappa', 'sigma'):
        payload['features'] += [spec('%s_%02d' % (category, number), category,
                                     'passed') for number in range(10)]
    payload['features'].append(spec('zz_last', 'zeta', 'failed'))


def status_sentences():
    """The modules whose sentences the status writes."""
    mcp = os.path.join(ROOT, 'scripts', 'mcp')
    if mcp not in sys.path:
        sys.path.insert(0, mcp)
    from purlin import evidence, specs, status, wording
    return specs, status, wording, evidence


def notice_module():
    status_sentences()
    from purlin import notices
    return notices


def give_lines(payload, warnings=(), information=()):
    """Give the payload these lines as the data file carries them: its
    `warnings`, its `information` and the `notices` written over both, the
    working tree's own first where the payload reads dirty."""
    status_sentences()
    from purlin import payload as payload_module, report_data
    payload['warnings'] = list(warnings)
    payload['information'] = list(information)
    payload['notices'] = payload_module.notice_entries(dict(
        payload, warnings=([report_data.TREE_DIRTY] if payload.get('dirty')
                           else []) + list(warnings)))
    return [str(line) for line in list(warnings) + list(information)]


def reworded_proof_line(name='pitch_crosscheck'):
    """The warning the status writes for a test whose proof was reworded."""
    import types
    wording = status_sentences()[2]
    marker = types.SimpleNamespace(feature=name, id='PROOF-7', line=175)
    return wording.stale_line(
        {'proofs_by_rule': {'RULE-3': ['PROOF-7']}},
        'pipeline/tests/test_%s.py' % name, marker, 'ebfe120',
        'Transcribe the reference lead with the cross-check disabled',
        'Transcribe a synthesised stem with the cross-check disabled', None)


def not_written_line(name, *files):
    """The line of information for a spec whose scope names `files`, none
    written yet."""
    status = status_sentences()[1]
    wrong = (status.NOT_WRITTEN_ONE % files[0] if len(files) == 1
             else status.NOT_WRITTEN_MANY % (len(files), files[0]))
    return notice_module().line('not_written', name, wrong,
                                status.NOT_WRITTEN_DO % (name, name),
                                feature=name)


def four_lines():
    """The four lines a real project's status printed between its table and
    its sentence: two warnings, then two lines of information."""
    status = status_sentences()[1]
    old = [('packages/web/test/parameter_lfo.test.ts', 154 + number,
            'parameter_lfo', 'RULE-4') for number in range(9)]
    return [reworded_proof_line(), status.old_marker_line(old),
            status.incomplete_line(['patch_graph']),
            not_written_line('pack_acceptance',
                             'projects/1-groovevox-13-3-samplepack2')]


# purlin: purlin_report PROOF-269
def test_the_failing_box_and_the_failing_spec_are_on_the_first_screen(
        browser, tmp_path):
    payload = payload_named('regulated')
    forty_passing_specs_then_one_failing(payload)
    assert payload['features'][-1]['name'] == 'zz_last'
    assert len(payload['features']) == 46
    payload['dirty'] = False
    lines = four_lines()
    give_lines(payload, lines[:2], lines[2:])
    page = open_board(browser, tmp_path, payload,
                      viewport={'width': 1500, 'height': 900})
    first = page.query_selector('[data-table="specs"] .tr')
    name = first.query_selector('.name .n').text_content().strip()
    row = first.bounding_box()
    tile = page.eval_on_selector_all(
        '.tile', "els => els.filter(e => e.querySelector('.tile-l')"
        ".textContent.trim() === 'Failing').map(e => "
        "e.getBoundingClientRect().bottom)")
    band = texts(page, '.group .gt')[0]
    notices = len(page.query_selector_all('.notice'))
    labels = section_labels(page)
    page.close()
    assert notices == 4
    assert labels == ['SPECS', 'ANCHORS'], labels
    assert (band, name) == ('zeta', 'zz_last'), (band, name)
    assert len(tile) == 1 and tile[0] <= 900, tile
    assert row['y'] + row['height'] <= 900, row


# Every count cell of every spec row, keyed by the spec name, as the text a
# person reads rather than the markup under it.
COUNT_CELLS = r"""els => {
  return els.map(e => {
    const head = Array.from(e.closest('.tbl').querySelectorAll('.th > div'))
      .map(d => d.textContent.trim());
    const row = {name: e.querySelector('.name .n').textContent.trim()};
    head.forEach((label, i) => {
      row[label] = e.children[i].innerText.trim().replace(/\s+/g, ' ');
    });
    return row;
  });
}"""


def count_cells(page):
    return {row['name']: row
            for row in page.eval_on_selector_all('.tr', COUNT_CELLS)}


# purlin: purlin_report PROOF-40
def test_every_count_carries_the_word_it_counts(browser, tmp_path):
    """`24 · 0 · 0` left the reader to work out which number was which."""
    payload = payload_named('regulated')
    assert payload['features'][0]['rules'][1]['id'] == 'RULE-2'
    payload['features'][0]['rules'][1]['cells']['passed']['word'] = 'failed'
    page = open_board(browser, tmp_path / 'reg', payload)
    cells = count_cells(page)
    # The first part is drawn even at zero, and a later part only above it.
    assert cells['login']['Tests'] == (
        '2 of 4 · 1 partial · 1 failing')
    assert cells['login']['Proofs'] == '5'
    assert cells['login']['Strong'] == '2 of 3'
    # One of export's two rules is behind changed code: it passed nothing
    # and failed nothing, so the share alone reads it.
    assert cells['export']['Tests'] == '1 of 2'
    # invoice's third proof is `@manual`, which declares that no test is
    # written for it, so the rollup counts no gap and the cell reads the
    # total alone.
    assert cells['invoice']['Proofs'] == '3'
    page.close()


def given_rules(payload, feature, words):
    """The payload with one rule more on `feature` for each passed-cell word
    in `words`, each a copy of its first rule numbered after its last."""
    owner = next(f for f in payload['features'] if f['name'] == feature)
    for word in words:
        made = json.loads(json.dumps(owner['rules'][0]))
        made['id'] = 'RULE-%d' % (len(owner['rules']) + 1)
        made['cells']['passed'].update(word=word, reasons=[])
        owner['rules'].append(made)


# purlin: purlin_report PROOF-280
def test_an_anchor_out_of_date_says_so_in_its_tests_cell(browser, tmp_path):
    payload = payload_named('regulated')
    rule_of(payload, 'checkout_design', 'RULE-1')['cells']['passed'].update(
        word='out of date', reasons=['code changed since a1b2c3d'])
    assert rule_of(payload, 'export', 'RULE-1')['cells']['passed'][
        'word'] == 'out of date'
    page = open_board(browser, tmp_path, payload)
    cells = count_cells(page)
    tone = page.eval_on_selector(
        '[data-table="anchors"] .tr[data-feature="checkout_design"]'
        ' [data-label="Tests"] .trio b:last-child', 'e => getComputedStyle(e).color')
    warn = page.evaluate(RESOLVE_TOKEN, '--state-warn')
    page.close()
    assert cells['checkout_design']['Tests'] == '0 of 1 · 1 out of date', cells
    assert tone == warn, (tone, warn)
    assert cells['export']['Tests'] == '1 of 2', cells


# purlin: purlin_report PROOF-281
def test_an_anchors_out_of_date_part_comes_last(browser, tmp_path):
    payload = payload_named('regulated')
    given_rules(payload, 'checkout_design', ['checked at sign-off', 'partial',
                                             'failed', 'out of date'])
    page = open_board(browser, tmp_path, payload)
    cells = count_cells(page)
    page.close()
    assert cells['checkout_design']['Tests'] == (
        '1 of 5 · 1 by hand · 1 partial · 1 failing · 1 out of date'), cells


# purlin: purlin_report PROOF-245
def test_a_hand_check_is_counted_by_hand_and_out_of_the_strong_share(
        browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    cells = count_cells(page)
    page.close()
    assert cells['invoice']['Tests'] == '2 of 3 · 1 by hand', cells
    assert cells['invoice']['Strong'] == '1 of 2', cells


# purlin: purlin_report PROOF-44
def test_every_cell_of_a_spec_row_carries_its_hover(browser, tmp_path):
    """The columns the board dropped became the hovers the cells carry."""
    # The clock stands at the moment the sample was written, 2026-10-01
    # 10:42:13 UTC, 19 days after its runs and its audit of 2026-09-12.
    page = open_board(browser, tmp_path, payload_named('regulated'),
                      clock_at='2026-10-01T10:42:13Z')
    login = hovers(page)['login']
    page.close()
    assert login['Spec'] == 'specs/auth/login.md'
    assert login['Proofs'] == 'every proof has a test'
    # Newest run first: Windows ran after Linux, and one of its four rules
    # failed there.
    assert login['Tests'].split('\n') == [
        'Windows · ci · 19 days old · 3 passed · 1 failed',
        'Linux/Unix · ci · 19 days old · 4 passed'], login
    assert login['Strong'].split('\n') == ['audit · ci · 19 days old'], login
    assert 'Signed' not in login


# purlin: purlin_report PROOF-97
def test_a_proofs_hover_names_the_proof_no_test_runs(browser, tmp_path):
    team = open_sample(browser, tmp_path, 'team')
    proofs = hovers(team)['invoice']['Proofs']
    team.close()
    assert proofs == 'no test · PROOF-2', proofs


# purlin: purlin_report PROOF-114
def test_a_rule_with_no_proof_is_counted_in_its_own_box(browser, tmp_path):
    page = open_board(browser, tmp_path,
                      with_export_rule_2_unproved(payload_named('regulated')))
    found = boxes(page)
    assert [label for label, _, _ in found] == ['No proof', 'Passing',
                                                'Strong'], found
    assert found[0][1:] == ['1', page.evaluate(RESOLVE_TOKEN,
                                               '--state-warn')], found
    page.close()


# The band over each category: its name, how many specs it holds, and how many
# of their rules pass their tests.
# purlin: purlin_report PROOF-43
def test_the_group_band_says_what_its_numbers_are(browser, tmp_path):
    """`AUTH (1) 3 of 4` named neither number."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    bands = page.eval_on_selector_all(
        '.group',
        r'els => els.map(e => e.innerText.replace(/\s+/g, " ").trim())')
    assert bands == ['▼ AUTH 1 spec 3 of 4 rules pass',
                     '▼ BILLING 2 specs 3 of 5 rules pass']
    page.close()


# How many rules each band counts: the second number of `3 of 4 rules pass`.
BAND_COUNTS = r"""els => els.map(e => parseInt(
  e.querySelector('.gc b').textContent.split(' of ')[1], 10))"""


def anchor_rule_count(page, payload):
    """How many rules the anchors listed in the anchors' section hold."""
    listed = texts(page, '[data-table="anchors"] .tr .name .n')
    return sum(len(f['rules'])
               for f in payload['features'] if f['name'] in listed)


# purlin: purlin_report PROOF-94
def test_the_bands_and_the_anchors_add_up_to_the_rules(browser, tmp_path):
    payload = payload_named('team')
    page = open_board(browser, tmp_path, payload,
                      viewport={'width': 1500, 'height': 900})
    counts = page.eval_on_selector_all('.group', BAND_COUNTS)
    anchored = anchor_rule_count(page, payload)
    page.close()
    assert payload['summary']['rules'] == 10
    assert anchored == 2
    assert sum(counts) + anchored == 10, counts


def _auth_band_closed_by_enter(browser, tmp_path):
    """The regulated board at 390 wide, its auth band closed from the
    keyboard."""
    narrow = open_board(browser, tmp_path, payload_named('regulated'),
                        viewport={'width': 390, 'height': 900})
    assert narrow.get_attribute(AUTH_BAND, 'aria-expanded') == 'true'
    narrow.focus(AUTH_BAND)
    narrow.keyboard.press('Enter')
    return narrow


AUTH_BAND = '.group[data-group="auth"]'


# purlin: purlin_report PROOF-96
def test_a_band_folds_from_the_keyboard(browser, tmp_path):
    narrow = _auth_band_closed_by_enter(browser, tmp_path)
    assert narrow.get_attribute(AUTH_BAND, 'aria-expanded') == 'false'
    assert narrow.evaluate('document.activeElement.getAttribute("data-group")') \
        == 'auth'
    # Hidden in the table that listed it, and nowhere else on the screen.
    assert listed_in(narrow, 'specs') == ['invoice', 'export']
    assert narrow.query_selector_all('[data-feature="login"]') == []
    assert 'login' not in narrow.inner_text('[data-table="specs"]')
    assert 'login' not in narrow.inner_text('body')
    narrow.close()


# purlin: purlin_report PROOF-10
def test_a_feature_row_expands_to_its_rules(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert rule_ids(page) == []
    # On screen anywhere, in any cell, not only in a rule's own row.
    assert re.findall(r'RULE-\d+', page.inner_text('body')) == []
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4']
    assert re.findall(r'RULE-\d+', page.inner_text('body')) == [
        'RULE-1', 'RULE-2', 'RULE-3', 'RULE-4']
    assert [text.count('STRONG') for text in texts(page, '.rule .rp')] == [
        1, 1, 0, 0]
    page.close()


# purlin: purlin_report PROOF-117
def test_an_open_spec_shows_its_description(browser, tmp_path):
    page = open_sample(browser, tmp_path, 'regulated')
    page.click('[data-act="feature"][data-feature="login"]')
    beneath, after = page.eval_on_selector(
        '.tr[data-feature="login"]',
        "el => { const d = el.nextElementSibling; return [d.textContent.trim(),"
        " d.nextElementSibling.getAttribute('data-rule')]; }")
    # Drawn where a person reads it: the line takes up room on the screen,
    # under the row and over `RULE-1`.
    row, line, rule = page.eval_on_selector(
        '.tr[data-feature="login"]',
        "el => [el, el.nextElementSibling,"
        " el.nextElementSibling.nextElementSibling].map(e => {"
        " const b = e.getBoundingClientRect();"
        " return {top: b.top, bottom: b.bottom, height: b.height}; })")
    shown = page.locator('.tr[data-feature="login"] + *').inner_text().strip()
    seen = page.locator('.tr[data-feature="login"] + *').is_visible()
    page.close()
    assert seen and line['height'] > 0, line
    assert row['bottom'] <= line['top'] < line['bottom'] <= rule['top'], (
        row, line, rule)
    assert shown == beneath, shown
    assert beneath == ('Signing in with an email address and a password, and '
                       'locking an account after repeated failures.'), beneath
    assert after == 'RULE-1', after


# purlin: purlin_report PROOF-15
def test_the_rule_screen_shows_the_rule_its_proof_and_its_cells(browser,
                                                               tmp_path):
    page = open_sample(browser, tmp_path, 'regulated')
    open_rule(page, 'login', 'RULE-1')
    body = page.inner_text('.wrap')
    rows = page.evaluate(KV_ROWS)
    assert 'RULE-1' in page.inner_text('h1')
    assert 'A person signs in with an email address and a password.' in body
    assert 'PROOF-1' in body
    assert 'tests/test_login.py :: test_sign_in' in body
    assert 'PASSED' in body and 'STRONG' in body
    # The row's own word, not its label, which reads `Tests`.
    assert rows['Tests'].startswith('PASSED'), rows
    assert rows['Strong'] == 'STRONG', rows
    page.close()


# Each row of the rule screen's first panel, as `label -> value`.
KV_ROWS = r"""() => {
  const list = document.querySelector('.kv');
  const out = {};
  let key = null;
  Array.from(list.children).forEach(node => {
    if (node.tagName === 'DT') { key = node.textContent.trim(); }
    else { out[key] = node.innerText.trim().replace(/\s+/g, ' '); }
  });
  return out;
}"""


# purlin: purlin_report PROOF-17
def test_a_rule_waiting_on_an_operating_system_says_so(browser, tmp_path):
    """The fixture's RULE-4 ran on Windows and failed; this one never ran."""
    payload = payload_named('regulated')
    cell = payload['features'][0]['rules'][3]['cells']['passed']
    cell['word'] = 'not run'
    cell['missing_env'] = ['windows']
    cell['reasons'] = ['Windows: no run yet']
    cell['platforms'] = {'linux': cell['platforms']['linux']}
    page = open_board(browser, tmp_path, payload)
    open_rule(page, 'login', 'RULE-4')
    body = page.inner_text('.wrap')
    assert 'Windows: no run yet' in body
    assert 'NOT RUN' in body
    page.close()


# purlin: purlin_report PROOF-20
def test_data_of_another_schema_shows_one_notice_and_nothing_else(browser,
                                                                  tmp_path):
    def marked_as_schema_3(payload):
        payload['schema_version'] = 3
    page = open_sample(browser, tmp_path, 'team', marked_as_schema_3)
    assert texts(page, '.notice') == [
        'This data was written for schema 3 and this page reads schema 20. '
        'Run purlin:status to write it again.']
    # On screen, not only in the page: the one notice is drawn.
    assert [notice.is_visible()
            for notice in page.query_selector_all('.notice')] == [True]
    assert page.locator('.notice').inner_text().strip() == (
        'This data was written for schema 3 and this page reads schema 20. '
        'Run purlin:status to write it again.')
    assert page.query_selector_all('.tile') == []
    assert page.query_selector_all('.fact') == []
    assert page.query_selector_all('.tbl') == []
    # Nothing else is drawn under the top bar: the notice is all the page's
    # body reads, with no row of a table and no spec's name beside it.
    assert page.inner_text('.wrap').strip() == (
        'This data was written for schema 3 and this page reads schema 20. '
        'Run purlin:status to write it again.')
    assert page.query_selector_all('.tr, .th, .rule, table') == []
    assert undrawn(page, '.notice') == []
    page.close()


# purlin: purlin_report PROOF-21
def test_no_data_at_all_names_the_command_that_writes_it(browser, tmp_path):
    root = str(tmp_path)
    shutil.copyfile(PAGE, os.path.join(root, 'purlin-report.html'))
    page = browser.new_page(viewport={'width': 1200, 'height': 800})
    page.goto('file://' + os.path.join(root, 'purlin-report.html'))
    page.wait_for_selector('.empty', timeout=10000)
    assert page.inner_text('.empty') == (
        'No board data yet. Run purlin:status to write '
        '.purlin/report-data.js, then reload this page.')
    # The empty screen reads that sentence and nothing more.
    assert page.inner_text('body').strip() == (
        'No board data yet. Run purlin:status to write '
        '.purlin/report-data.js, then reload this page.')
    assert undrawn(page, '.empty') == []
    page.close()


# purlin: purlin_report PROOF-198
def test_each_warning_is_a_notice_after_the_working_tree_one(browser,
                                                             tmp_path):
    payload = payload_named('regulated')
    [warning] = payload['warnings']
    page = open_board(browser, tmp_path, payload)
    assert texts(page, '.notice-text') == [
        'working tree: changes not committed. This board is not what a '
        'commit would carry. Commit them, then run purlin:status.', warning]
    # Each line is drawn whole: nothing of a notice is cut off or hidden
    # but the two marks a notice never draws.
    assert [piece for piece in undrawn(page, '.notice')
            if piece not in NOT_DRAWN_IN_A_NOTICE] == []
    assert [notice.is_visible()
            for notice in page.query_selector_all('.notice')] == [True, True]
    found = page.evaluate(STACK)
    page.close()
    assert found['tiles'] <= found['notices'][0], found
    assert found['notices'][1] <= found['anchors'], found


# Where the board's parts stand, from the top of the page: the bottom of the
# top bar, the top and the bottom of the boxes, the top and the bottom of the
# notices, the top of the anchors' section and of the spec table, and the
# bottom of the `Failing` box where there is one.
STACK = """() => {
  const rect = s => document.querySelector(s).getBoundingClientRect();
  const all = s => Array.from(document.querySelectorAll(s)).map(
    e => e.getBoundingClientRect());
  const tiles = all('.tile');
  const notes = all('.notice');
  const failing = Array.from(document.querySelectorAll('.tile')).filter(
    e => e.querySelector('.tile-l').textContent.trim() === 'Failing');
  const table = s => document.querySelector(s) ? rect(s).top : null;
  return {
    bar: rect('.topbar').bottom,
    tilesTop: Math.min(...tiles.map(r => r.top)),
    tiles: Math.max(...tiles.map(r => r.bottom)),
    notices: [Math.min(...notes.map(r => r.top)),
              Math.max(...notes.map(r => r.bottom))],
    anchors: table('[data-table="anchors"]'),
    specs: table('[data-table="specs"]'),
    failing: failing.length ? failing[0].getBoundingClientRect().bottom : null,
  };
}"""


# purlin: purlin_report PROOF-282
def test_the_boxes_stand_above_the_notices_at_every_width(browser, tmp_path):
    payload = payload_named('regulated')
    forty_passing_specs_then_one_failing(payload)
    lines = four_lines()
    give_lines(payload, lines[:2], lines[2:])
    seen = {}
    for theme in ('dark', 'light'):
        for width in (1500, 1280, 1024, 768, 390):
            page = open_board(browser, tmp_path / (theme + str(width)),
                              payload,
                              viewport={'width': width, 'height': 900})
            if theme == 'light':
                page.click('.topbar [data-act="theme"]')
                assert page.get_attribute('html', 'data-theme') == 'light'
            seen[theme, width] = (page.evaluate(STACK),
                                  len(page.query_selector_all('.notice')))
            page.close()
    for (theme, width), (found, count) in seen.items():
        where = (theme, width, found)
        assert count == 5, where
        assert found['bar'] <= found['tilesTop'], where
        assert found['tiles'] <= found['notices'][0], where
        tables = sorted(t for t in (found['specs'], found['anchors']))
        assert found['notices'][1] <= tables[0], where
        assert found['tiles'] <= 900 and found['failing'] <= 900, where


# ---------------------------------------------------------------------------
# Three or more warnings of one kind are one notice
# ---------------------------------------------------------------------------

def unread_proof_line(name, proof='PROOF-7b', rule='RULE-6'):
    """The warning the status writes for one lettered proof line of `name`."""
    specs = status_sentences()[0]
    return specs._mistake('proof_unread', name, specs.PROOF_LINE_UNREAD % (
        specs.NOT_A_PROOF_LINE, notice_module().shown(
            '- %s (%s): On a real engine, apply an edit' % (proof, rule))))


def thirty_three_specs():
    return ['piano_roll', 'sample_voice'] + [
        'spec_%02d' % number for number in range(3, 34)]


def notice_hovers(page):
    return page.eval_on_selector_all(
        '.notice', 'els => els.map(e => e.getAttribute("title"))')


# purlin: purlin_report PROOF-257
def test_thirty_three_warnings_of_one_kind_are_one_notice(browser, tmp_path):
    payload = payload_named('regulated')
    payload['dirty'] = False
    names = thirty_three_specs()
    other = reworded_proof_line()
    give_lines(payload, [unread_proof_line(name) for name in names] + [other])
    assert len(payload['warnings']) == 34
    page = open_board(browser, tmp_path, payload,
                      viewport={'width': 1500, 'height': 900})
    assert texts(page, '.notice-text') == [
        'proof line not read: 33 specs, piano_roll, sample_voice and 31 '
        'more. Run purlin:status for each.', other]
    # On screen, each whole: both are drawn, and nothing of either is
    # hidden but the two marks a notice never draws.
    assert [notice.is_visible()
            for notice in page.query_selector_all('.notice')] == [True, True]
    assert [piece for piece in undrawn(page, '.notice')
            if piece not in NOT_DRAWN_IN_A_NOTICE] == []
    assert notice_hovers(page) == ['\n'.join(names), None]
    rows = [page.query_selector('[data-table="%s"] .tr' % table).bounding_box()
            for table in ('anchors', 'specs')]
    page.close()
    assert all(row['y'] + row['height'] <= 900 for row in rows)


# purlin: purlin_report PROOF-258
def test_two_of_a_kind_and_a_warning_about_no_spec_keep_their_notices(
        browser, tmp_path):
    status_sentences()
    from purlin import facts as facts_module
    payload = payload_named('regulated')
    payload['dirty'] = False
    tags = [notice_module().line(
                'tag_not_here', 'signed/' + version,
                facts_module.TAG_NOT_HERE % sha,
                facts_module.TAG_NOT_HERE_DO)
            for version, sha in (('0.3.0', 'c3c3c3c'), ('0.2.0', 'b2b2b2b'),
                                 ('0.1.0', 'a1b2c3d'))]
    two = [unread_proof_line('login'), unread_proof_line('invoice')]
    give_lines(payload, two + tags)
    page = open_board(browser, tmp_path, payload)
    shown = texts(page, '.notice-text')
    assert shown == two + tags
    # The three lines about no one spec are the ones the proof names.
    assert [line.split('. ')[0] for line in shown[2:]] == [
        'signed/0.3.0: tag not in this checkout',
        'signed/0.2.0: tag not in this checkout',
        'signed/0.1.0: tag not in this checkout'], shown
    assert notice_hovers(page) == [None] * 5
    # On screen, each whole: all 5 are drawn, its name with each, and
    # nothing of any is hidden but the two marks a notice never draws.
    assert [notice.is_visible()
            for notice in page.query_selector_all('.notice')] == [True] * 5
    assert [piece for piece in undrawn(page, '.notice')
            if piece not in NOT_DRAWN_IN_A_NOTICE] == []
    assert [' '.join(text.split())[:13] for text in page.eval_on_selector_all(
        '.notice', 'els => els.map(e => e.innerText)')][2:] == [
            'signed/0.3.0 ', 'signed/0.2.0 ', 'signed/0.1.0 ']
    # No part of a notice has a hover either.
    assert page.eval_on_selector_all(
        '.notice, .notice *',
        'els => els.filter(e => e.hasAttribute("title")).length') == 0
    page.close()


# purlin: purlin_report PROOF-259
def test_a_grouped_notice_counts_specs_and_stands_where_the_first_stood(
        browser, tmp_path):
    payload = payload_named('regulated')
    payload['dirty'] = False
    other = reworded_proof_line()
    give_lines(payload, [
        unread_proof_line('export'), other,
        unread_proof_line('export', 'PROOF-8b'), unread_proof_line('invoice'),
        unread_proof_line('login'), unread_proof_line('login', 'PROOF-9b')])
    page = open_board(browser, tmp_path, payload)
    assert texts(page, '.notice-text') == [
        'proof line not read: 3 specs, export, invoice and 1 more. Run '
        'purlin:status for each.', other]
    page.close()


# purlin: purlin_report PROOF-260
def test_three_lines_about_one_or_two_specs_name_each_spec(browser, tmp_path):
    payload = payload_named('regulated')
    payload['dirty'] = False
    three = [unread_proof_line('login', 'PROOF-%db' % number)
             for number in (1, 2, 3)]
    give_lines(payload, three)
    page = open_board(browser, tmp_path / 'one', payload)
    assert texts(page, '.notice-text') == [
        'proof line not read: login, in 3 places. Run purlin:status login.']
    page.close()
    give_lines(payload, three[:2] + [unread_proof_line('invoice')])
    page = open_board(browser, tmp_path / 'two', payload)
    assert texts(page, '.notice-text') == [
        'proof line not read: 2 specs, login and invoice. Run purlin:status '
        'for each.']
    page.close()


# purlin: purlin_report PROOF-261
def test_lines_of_information_group_in_the_neutral_tone(browser, tmp_path):
    payload = payload_named('regulated')
    payload['dirty'] = False
    names = ['export', 'invoice', 'login', 'refund']
    give_lines(payload, [], [
        not_written_line(names[0], 'src/a.py'),
        not_written_line(names[1], 'src/b.py', 'src/c.py')] + [
        not_written_line(name, 'src/d.py') for name in names[2:]])
    page = open_board(browser, tmp_path, payload)
    assert texts(page, '.notice-text') == [
        'spec ahead of its code: 4 specs, export, invoice and 2 more. Run '
        'purlin:status for each.']
    assert notice_hovers(page) == ['\n'.join(names)]
    dot = page.eval_on_selector('.notice .dot', 'e => e.getAttribute("style")')
    # The tone as it is drawn: the dot is filled with the neutral colour.
    filled = page.eval_on_selector(
        '.notice .dot', 'e => getComputedStyle(e).backgroundColor')
    neutral = page.evaluate(RESOLVE_TOKEN, '--state-neutral')
    warn = page.evaluate(RESOLVE_TOKEN, '--state-warn')
    page.close()
    assert dot == 'color:var(--state-neutral)'
    assert filled == neutral and neutral != warn, (filled, neutral, warn)


# purlin: purlin_report PROOF-275
def test_rules_with_nothing_to_check_group_in_the_neutral_tone(browser,
                                                               tmp_path):
    status = status_sentences()[1]
    payload = payload_named('regulated')
    payload['dirty'] = False
    reason = 'this project has no screens'
    incomplete = status.incomplete_line(['export'])
    give_lines(payload, [], [
        notice_module().line(
            'nothing_to_check', 'checkout_design RULE-%d' % number,
            status.NOTHING_LINE % reason, feature='checkout_design',
            rule='RULE-%d' % number)
        for number in (1, 2, 3)] + [incomplete])
    page = open_board(browser, tmp_path, payload)
    found = texts(page, '.notice-text')
    dots = page.eval_on_selector_all(
        '.notice .dot', 'els => els.map(e => e.getAttribute("style"))')
    # The tone as it is drawn: each dot is filled with the neutral colour.
    filled = page.eval_on_selector_all(
        '.notice .dot',
        'els => els.map(e => getComputedStyle(e).backgroundColor)')
    neutral = page.evaluate(RESOLVE_TOKEN, '--state-neutral')
    warn = page.evaluate(RESOLVE_TOKEN, '--state-warn')
    page.close()
    assert filled == [neutral] * 2 and neutral != warn, (filled, neutral)
    assert found == [
        'nothing to check here: checkout_design, in 3 places. Run '
        'purlin:status checkout_design.', incomplete], found
    assert incomplete == (
        'export: spec with no scope. Its tests run every time. Run '
        'purlin:spec export to add its > Scope: line.')
    assert dots == ['color:var(--state-neutral)'] * 2, dots


def one_line_of_each_kind(name):
    """`[(the kind's words, the line the status writes about `name`)]`, one
    per kind of warning the status writes about one spec, in the order
    `notices.KINDS` lists the kinds."""
    specs, _status, _wording, evidence = status_sentences()
    notices = notice_module()
    words = notices.WORDS
    path = evidence.evidence_path('local', name)
    return [
        (words['to_correct'], reworded_proof_line(name)),
        (words['to_repair'],
         specs._mistake('to_repair', name, specs.WRITTEN_TWICE,
                        about='%s RULE-2' % name, rule='RULE-2')),
        (words['unnumbered'],
         specs._mistake('unnumbered', name, specs.UNNUMBERED_ONE)),
        (words['same_name'],
         specs._mistake('same_name', name,
                        specs.SAME_NAME % ('specs/a/%s.md' % name),
             specs.SAME_NAME_DO % ('specs/b/%s.md' % name, 'specs/b'))),
        (words['name_refused'],
         specs._mistake('name_refused', name, specs.NAME_REFUSED,
                        specs.NAME_REFUSED_DO % ('specs/a/%s.md' % name,
                                                 'specs/a/renamed.md'))),
        (words['proof_unread'],
         specs._mistake('proof_unread', name, specs.PROOF_LINE_UNREAD % (
             specs.TAG_AT_END, '- PROOF-1 @slow (RULE-1): text'))),
        (words['heading'],
         specs._mistake('heading', name,
                        specs.HEADING_NAMES_OTHER % 'other')),
        (words['tags_conflict'],
         specs._proof_mistake('tags_conflict', {}, name, 'PROOF-3',
                              specs.READ_AS_MANUAL % '@slow')),
        (words['line_unread'],
         specs._mistake('line_unread', name,
                        specs.UNREAD_FIELD % '> Requires:')),
        (words['evidence_ignored'],
         evidence._ignored(path, name, evidence.NOT_JSON,
                           evidence.rewrite_fix('local', name))),
    ]


# purlin: purlin_report PROOF-262
def test_every_kind_of_warning_about_a_spec_groups_under_its_own_words(
        browser, tmp_path):
    payload = payload_named('regulated')
    payload['dirty'] = False
    names = ['export', 'invoice', 'login']
    kinds = [one_line_of_each_kind(name) for name in names]
    give_lines(payload,
               [line for kind in zip(*kinds) for _what, line in kind])
    assert len(payload['warnings']) == 30
    page = open_board(browser, tmp_path, payload)
    assert texts(page, '.notice-text') == [
        '%s: 3 specs, export, invoice and 1 more. Run purlin:status for each.'
        % what for what, _line in kinds[0]]
    # On screen: each of the 10 is drawn with its kind's words, and nothing
    # of any is hidden but the mark after the kind, which is never drawn.
    assert [notice.is_visible()
            for notice in page.query_selector_all('.notice')] == [True] * 10
    assert undrawn(page, '.notice') == [': '] * 10
    assert [what for what, _line in kinds[0]] == [
        'test comment to correct', 'spec to repair',
        'rule line with no number', 'two specs with one name',
        'spec name not allowed', 'proof line not read',
        'first line names another spec', 'tags that conflict',
        'line not read', 'evidence file ignored']
    page.close()


# purlin: purlin_report PROOF-22
def test_a_rule_screen_draws_no_notice(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['dirty'] is True
    page = open_board(browser, tmp_path, payload)
    assert len(page.query_selector_all('.notice')) == 2
    open_rule(page, 'login', 'RULE-1')
    assert 'RULE-1' in page.inner_text('h1')
    assert len(page.query_selector_all('.notice')) == 0
    # No notice in any other dress either: the rule's screen reads neither
    # notice's line, in whole or from its label on.
    screen = ' '.join(page.inner_text('body').split())
    assert [entry['label'] for entry in payload['notices']] == [
        'changes not committed', 'rule line with no number']
    assert [entry for entry in payload['notices']
            if entry['rest'] in screen or entry['label'] in screen] == []
    assert 'This board is not what a commit would carry' not in screen
    page.close()


# purlin: purlin_report PROOF-138
def test_back_to_the_board_returns_to_the_board(browser, tmp_path):
    page = open_sample(browser, tmp_path, 'regulated')
    open_rule(page, 'login', 'RULE-1')
    assert page.inner_text('h1') == 'RULE-1'
    page.get_by_text('Back to the board', exact=True).click()
    assert len(feature_names(page)) == 5
    assert page.query_selector_all('h1') == []
    assert page.get_by_text('Back to the board', exact=True).count() == 0
    page.close()


# ---------------------------------------------------------------------------
# The audit panel
# ---------------------------------------------------------------------------

def audit_lines(browser, tmp_path, payload, feature, rule_id):
    """The lines of the `Audit` panel on one rule's screen."""
    page = open_board(browser, tmp_path, payload)
    open_rule(page, feature, rule_id)
    lines = panel_lines(page, 'Audit')
    page.close()
    return lines


FINDING = 'tests/test_invoice.py::test_total: no assertion.'
EXPLANATION = 'The test prints the total and checks nothing.'


def given_audit(payload, feature, rule_id, **fields):
    """Give one rule's audit the fields named, as the audit writes them."""
    audit = rule_of(payload, feature, rule_id)['audit']
    assert audit is not None, (feature, rule_id)
    audit.update(fields)


# purlin: purlin_report PROOF-144
def test_a_weak_audit_reads_weak_its_finding_then_its_explanation(browser,
                                                                 tmp_path):
    payload = payload_named('regulated')
    given_audit(payload, 'invoice', 'RULE-2', findings=[FINDING],
                explanation=[EXPLANATION], bugs={})
    lines = audit_lines(browser, tmp_path, payload, 'invoice', 'RULE-2')
    assert lines[:3] == ['Weak.', FINDING, EXPLANATION], lines


# purlin: purlin_report PROOF-234
def test_a_strong_audit_reads_its_explanation_under_its_answer(browser,
                                                              tmp_path):
    payload = payload_named('regulated')
    said = 'The test signs in and reads the session cookie.'
    given_audit(payload, 'login', 'RULE-1', explanation=[said])
    lines = audit_lines(browser, tmp_path, payload, 'login', 'RULE-1')
    assert lines[:2] == ['Strong. It found nothing.', said], lines


def missed_bug(payload):
    """Give the regulated sample's invoice `RULE-2` one planted bug its tests
    missed, as the audit records it."""
    given_audit(payload, 'invoice', 'RULE-2', bugs={'PROOF-2': {
        'file': 'src/billing/invoice.py', 'line': 12,
        'before': '    return total\n', 'after': '    return 0\n',
        'result': 'survived', 'why': '', 'bug_key': 'b' * 64}})


# Each planted bug the open rule's audit panel draws: its sentence, then the
# label and the lines of each row beneath it.
BUGS = """() => Array.from(document.querySelectorAll('.bug')).map(b => [
  b.querySelector('p').innerText.trim()].concat(Array.from(
    b.querySelectorAll('dt, dd')).map(e => e.textContent.trim())))"""


# purlin: purlin_report PROOF-235
def test_a_planted_bug_the_tests_missed_is_shown_with_its_lines(browser,
                                                               tmp_path):
    page = open_sample(browser, tmp_path, 'regulated', missed_bug)
    open_rule(page, 'invoice', 'RULE-2')
    lines, bugs = panel_lines(page, 'Audit'), page.evaluate(BUGS)
    page.close()
    assert ('PROOF-2: its tests missed a bug planted at '
            'src/billing/invoice.py:12.') in lines, lines
    assert bugs == [['PROOF-2: its tests missed a bug planted at '
                     'src/billing/invoice.py:12.',
                     'Before', 'return total', 'After', 'return 0']], bugs


# purlin: purlin_report PROOF-236
def test_a_planted_bug_the_tests_caught_is_not_shown(browser, tmp_path):
    def caught(payload):
        missed_bug(payload)
        rule_of(payload, 'invoice', 'RULE-2')['audit']['bugs']['PROOF-2'][
            'result'] = 'caught'
    page = open_sample(browser, tmp_path, 'regulated', caught)
    open_rule(page, 'invoice', 'RULE-2')
    lines, bugs = panel_lines(page, 'Audit'), page.evaluate(BUGS)
    page.close()
    assert lines[0] == 'Weak.', lines
    assert bugs == [], bugs
    assert not [line for line in lines if 'planted' in line], lines
    # No line names the bug in any words: none holds the word, the bug's
    # proof or the file it was planted in, and the panel reads as it does
    # with no bug recorded at all.
    assert not [line for line in lines if 'bug' in line.lower()
                or 'PROOF-2' in line or 'src/billing/invoice.py' in line], lines
    plain = open_sample(browser, tmp_path / 'no-bug', 'regulated')
    open_rule(plain, 'invoice', 'RULE-2')
    without = panel_lines(plain, 'Audit')
    plain.close()
    assert lines == without, (lines, without)


# purlin: purlin_report PROOF-147
def test_the_audit_panel_of_a_rule_no_audit_read(browser, tmp_path):
    lines = audit_lines(browser, tmp_path, payload_named('regulated'),
                        'export', 'RULE-2')
    assert lines[0] == 'No audit has read this rule yet.', lines


ANCHOR_SENTENCE = "No bug was planted: no bug is planted for an anchor's rule."


def spot_checked(payload):
    """Give the regulated sample's export `RULE-1` a current audit entry
    reading `spot-checked` with one `no_bug` sentence, as the payload
    carries one: the rule passing, its strong cell reading the word with
    its one reason, and the summary counting it."""
    rule = rule_of(payload, 'export', 'RULE-1')
    rule['cells']['passed'].update({'word': 'passed', 'reasons': []})
    rule['cells']['strong'] = {
        'word': 'spot-checked', 'findings': [],
        'evidence': '.purlin/evidence/ci/export.json',
        'reasons': ['The spot tests found nothing. ' + ANCHOR_SENTENCE]}
    rule['audit'] = {
        'verdict': 'spot-checked', 'findings': [],
        'no_bug': [ANCHOR_SENTENCE], 'notes': [], 'explanation': [],
        'bugs': {}, 'model': 'claude-opus-5-5',
        'at': '2026-09-13T12:05:00Z', 'commit': 'a1b2c3d' + '0' * 33,
        'path': '.purlin/evidence/ci/export.json', 'out_of_date': []}
    rule['flags']['spot_checked'] = True
    payload['summary']['audit']['spot_checked'] += 1


# purlin: purlin_report PROOF-239
def test_a_spot_checked_rule_reads_why_no_bug_was_caught(browser, tmp_path):
    page = open_sample(browser, tmp_path, 'regulated', spot_checked)
    open_rule(page, 'export', 'RULE-1')
    strong = page.evaluate(KV_ROWS)['Strong']
    lines = panel_lines(page, 'Audit')
    page.close()
    assert strong.startswith('SPOT-CHECKED'), strong
    # The word once, in capitals, and then the cell's one reason alone.
    assert strong == ('SPOT-CHECKED The spot tests found nothing. '
                      + ANCHOR_SENTENCE), strong
    assert strong.lower().count('spot-checked') == 1, strong
    assert lines[:2] == [
        'Spot-checked.',
        'The spot tests found nothing. ' + ANCHOR_SENTENCE], lines


OUT_OF_DATE_REASONS = ['code changed since a1b2c3d',
                       'the last audit found it strong on 2026-09-13']


def audit_out_of_date(payload):
    """Mark the audit of the regulated sample's login `RULE-1` out of date
    on `code` at `a1b2c3d`, as the payload carries it: the entry kept, its
    strong cell reading `out of date` with the two reasons."""
    rule = rule_of(payload, 'login', 'RULE-1')
    assert rule['audit']['verdict'] == 'strong'
    rule['audit'].update({'out_of_date': ['code'],
                          'commit': 'a1b2c3d' + '0' * 33,
                          'at': '2026-09-13T12:05:00Z'})
    rule['cells']['strong'].update({'word': 'out of date',
                                    'reasons': list(OUT_OF_DATE_REASONS)})
    rule['flags'].update({'strong': False, 'audit_out_of_date': True})
    payload['summary']['audit']['strong'] -= 1
    payload['summary']['audit']['out_of_date'] += 1


# purlin: purlin_report PROOF-240
def test_an_audit_out_of_date_keeps_its_last_result_on_screen(browser,
                                                             tmp_path):
    page = open_sample(browser, tmp_path, 'regulated', audit_out_of_date)
    open_rule(page, 'login', 'RULE-1')
    strong = page.evaluate(KV_ROWS)['Strong']
    lines = panel_lines(page, 'Audit')
    page.close()
    assert strong.startswith('OUT OF DATE'), strong
    for reason in OUT_OF_DATE_REASONS:
        assert reason in strong, strong
    # The word once, and the two reasons straight after it.
    assert strong == ('OUT OF DATE code changed since a1b2c3d; the last '
                      'audit found it strong on 2026-09-13'), strong
    assert lines[0].startswith('Out of date:'), lines
    assert lines[1] == 'Strong. It found nothing.', lines


# purlin: purlin_report PROOF-64
def test_a_rule_with_no_proof_reads_its_reason(browser, tmp_path):
    solo = open_board(browser, tmp_path, payload_named('solo'))
    open_rule(solo, 'login', 'RULE-3')
    passed = solo.evaluate(KV_ROWS)['Tests']
    assert passed.startswith('NO TEST') and 'no proof written' in passed
    # The whole row, and the badge alone: `NO TEST`, not a word beside it.
    assert passed == 'NO TEST no proof written', passed
    assert solo.evaluate(PASSED_PILL)[0] == 'NO TEST'
    assert 'No proof written.' in solo.inner_text('.wrap')
    solo.close()


# purlin: purlin_report PROOF-135
def test_a_rule_out_of_date_reads_what_changed(browser, tmp_path):
    reg = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(reg, 'export', 'RULE-1')
    passed = reg.evaluate(KV_ROWS)['Tests']
    assert passed.startswith('OUT OF DATE'), passed
    assert 'code changed since 9f8e7d6' in passed
    reg.close()


# The pill of the open rule's passed row: its text and the colour it is in.
PASSED_PILL = """() => {
  const row = Array.from(document.querySelectorAll('.kv dt')).find(
    dt => dt.textContent.trim() === 'Tests');
  const pill = row.nextElementSibling.querySelector('.pill');
  return [pill.innerText.trim(), getComputedStyle(pill).color];
}"""


# purlin: purlin_report PROOF-244
def test_a_hand_check_no_sign_off_noted_is_passed_as_checked_at_sign_off(
        browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="invoice"]')
    badges = row_badges(page, 'invoice')
    page.click('.rule[data-feature="invoice"][data-rule="RULE-3"]')
    passed = page.evaluate(KV_ROWS)['Tests']
    pill = page.evaluate(PASSED_PILL)
    neutral = page.evaluate(RESOLVE_TOKEN, '--state-neutral')
    page.close()
    assert passed == ('CHECKED AT SIGN-OFF no sign-off has checked it '
                      'yet'), passed
    assert pill == ['CHECKED AT SIGN-OFF', neutral], pill
    assert 'PASSED' not in badges['RULE-3'], badges
    assert 'PASSED' in badges['RULE-1'], badges


# purlin: purlin_report PROOF-238
def test_a_slow_proof_not_run_shows_its_tag_and_its_reason(browser, tmp_path):
    payload = payload_named('regulated')
    export = next(f for f in payload['features'] if f['name'] == 'export')
    rule = next(r for r in export['rules'] if r['id'] == 'RULE-1')
    assert [proof['id'] for proof in rule['proofs']] == ['PROOF-1']
    rule['proofs'][0].update(slow=True, result='not run')
    rule['cells']['passed'].update(
        word='not run', reasons=['slow: runs with purlin:test --all'])
    reg = open_board(browser, tmp_path, payload)
    open_rule(reg, 'export', 'RULE-1')
    passed = reg.evaluate(KV_ROWS)['Tests']
    assert passed.startswith('NOT RUN'), passed
    assert 'slow: runs with purlin:test --all' in passed
    proof = reg.inner_text('.panel.proof')
    assert 'PROOF-1' in proof and 'NOT RUN' in proof, proof
    assert reg.inner_text('.panel.proof .tag').strip() == '@slow'
    reg.close()


# The words a project no audit has read is never shown, and the one a
# project that writes no proof line is not shown either.
AUDIT_WORDS = re.compile(r'strong|audit', re.I)
AUDIT_AND_PROOF_WORDS = re.compile(r'proof|strong|audit', re.I)
STATUSES = ('passed', 'failed', 'partial', 'no test', 'not run',
            'out of date')

# Every text a person can see on the page and every hover it carries.
SEEN = """() => [document.body.innerText].concat(
  Array.from(document.querySelectorAll('[title]')).map(
    e => e.getAttribute('title')),
  Array.from(document.querySelectorAll('[aria-label]')).map(
    e => e.getAttribute('aria-label')))"""


def _walk_everything(page):
    """Every screen the page offers, as the texts and hovers it showed."""
    seen = list(page.evaluate(SEEN))
    names = feature_names(page)
    for name in names:
        page.click('[data-act="feature"][data-feature="%s"]' % name)
    seen.extend(page.evaluate(SEEN))
    statuses = []
    for name in names:
        ids = page.eval_on_selector_all(
            '.rule[data-feature="%s"]' % name,
            'els => els.map(e => e.getAttribute("data-rule"))')
        for rule_id in ids:
            page.click('.rule[data-feature="%s"][data-rule="%s"]'
                       % (name, rule_id))
            seen.extend(page.evaluate(SEEN))
            statuses.append(page.inner_text('.kv dd .pill').strip().lower())
            page.click('[data-act="close"]')
    page.click('[data-act="theme"]')
    seen.extend(page.evaluate(SEEN))
    return seen, statuses


def words_shown(browser, tmp_path, payload, words):
    """Walk every screen of one board: the words of `words` it showed, and
    each rule's status in the order the rules were opened."""
    page = open_board(browser, tmp_path, payload)
    seen, statuses = _walk_everything(page)
    page.close()
    return sorted({match.group(0) for text in seen if text
                   for match in words.finditer(text)}), statuses


# purlin: purlin_report PROOF-63
def test_a_project_no_audit_read_never_reads_strong_or_audit(browser,
                                                            tmp_path):
    payload = payload_named('solo')
    assert payload['summary']['audit'] == {
        'strong': 0, 'weak': 0, 'spot_checked': 0, 'out_of_date': 0,
        'not_audited': 2}
    found, statuses = words_shown(browser, tmp_path / 'wide', payload,
                                  AUDIT_WORDS)
    assert found == [], found
    assert len(statuses) == 5, statuses
    assert set(statuses) <= set(STATUSES), statuses
    # A label the stylesheet draws beside a value is text a person reads:
    # at the width of a phone, of a tablet and of a desk, with every spec
    # open and in both themes, what the page draws before and after each
    # element holds neither word, and neither does its text or a hover.
    drawn_by_style = """() => [...document.querySelectorAll('body *')]
      .flatMap(e => ['::before', '::after'].map(
        part => getComputedStyle(e, part).content))
      .filter(text => text && text !== 'none' && text !== 'normal')"""
    for width in (390, 768, 1440):
        page = open_board(browser, tmp_path / str(width), payload,
                          viewport={'width': width, 'height': 900})
        for name in feature_names(page):
            page.click('[data-act="feature"][data-feature="%s"]' % name)
        seen = page.evaluate(SEEN) + page.evaluate(drawn_by_style)
        page.click('[data-act="theme"]')
        seen += page.evaluate(SEEN) + page.evaluate(drawn_by_style)
        page.close()
        assert len(seen) > 5, (width, seen)
        assert sorted({match.group(0) for text in seen if text
                       for match in AUDIT_WORDS.finditer(text)}) == [], width


# purlin: purlin_report PROOF-103
def test_a_project_with_no_proof_line_never_reads_proof(browser, tmp_path):
    payload = without_proof_lines(payload_named('solo'))
    assert payload['summary']['proofs'] == 0
    assert all(rule['proofs'] == [] for feature in payload['features']
               for rule in feature['rules'])
    found, statuses = words_shown(browser, tmp_path, payload,
                                  AUDIT_AND_PROOF_WORDS)
    assert found == [], found
    assert len(statuses) == 5, statuses


def _marked_project(root, passing):
    """A new project: one rule, no proof line, one pytest test marked with
    the rule's own id, passing or failing as asked."""
    import suites
    (root / 'specs' / 'a').mkdir(parents=True)
    (root / 'tests').mkdir()
    (root / '.purlin').mkdir()
    (root / '.purlin' / 'config.json').write_text(json.dumps(
        {'version': '0.10.0', 'tests': [suites.pytest_suite()]}),
        encoding='utf-8')
    (root / 'specs' / 'a' / 'lock.md').write_text(
        '# lock\n\n> Scope: tests/\n\n## Rules\n\n'
        '- RULE-1: A wrong password five times locks the account\n',
        encoding='utf-8')
    (root / 'tests' / 'test_lock.py').write_text(
        '# purlin: lock RULE-1\n'
        'def test_five_wrong_passwords_lock():\n'
        '    assert %s\n' % ('True' if passing else 'False'),
        encoding='utf-8')


def _run_and_read(root):
    """Run the tests as `purlin:test` does, refresh the dashboard data as it
    does when it finishes, and return the payload the page would load."""
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, 'scripts', 'run', 'purlin_run.py'),
         '--test', '--project-root', str(root)],
        capture_output=True, encoding='utf-8', cwd=str(root))
    assert 'Markers: 1 tied to a test, 0 not tied.' in result.stdout, (
        result.stdout + result.stderr)
    sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
    from purlin import report_data
    path = report_data.refresh(str(root))
    assert path, 'no dashboard data was written'
    text = read(os.path.join(str(root), '.purlin', 'report-data.js'))
    return json.loads(text[len('const PURLIN_DATA = '):].rstrip().rstrip(';'))


def _rule_marked_with_its_id(browser, tmp_path, passing):
    root = tmp_path / 'project'
    root.mkdir()
    _marked_project(root, passing)
    payload = _run_and_read(root)
    rule = payload['features'][0]['rules'][0]
    assert rule['proofs'] == []
    result = 'pass' if passing else 'fail'
    assert rule['tests'] == [{'file': 'tests/test_lock.py',
                              'name': 'test_five_wrong_passwords_lock',
                              'result': result}], rule['tests']

    page = open_board(browser, tmp_path / 'page', payload)
    open_rule(page, 'lock', 'RULE-1')
    lines = texts(page, '.tests p')
    dots = test_dots(page, '.tests p')
    tone = resolved(page, '--state-pass' if passing else '--state-fail')
    seen = list(page.evaluate(SEEN))
    page.close()
    assert lines == ['tests/test_lock.py :: test_five_wrong_passwords_lock'], \
        lines
    assert dots == [['passed' if passing else 'failed', tone, 0]], dots
    found = sorted({match.group(0) for text in seen if text
                    for match in AUDIT_AND_PROOF_WORDS.finditer(text)})
    assert found == [], found


# purlin: purlin_report PROOF-65
def test_a_passing_test_marked_with_the_rules_id_shows_passed(browser,
                                                             tmp_path):
    """The data lists the test with `pass`; the screen reads it behind a
    pass-coloured dot whose hover is `passed`, with no word of a proof or
    of the audit."""
    _rule_marked_with_its_id(browser, tmp_path, True)


# Every element that draws a text node of its own, its colour, the ground under
# it composited through each translucent background up to the page, and the
# WCAG contrast ratio of the two. Every text is measured, whatever its colour,
# as it is seen: an `opacity` on the element or on anything it stands in
# thins the ink over the ground before the two are compared.
TEXT_CONTRAST = """() => {
  function parse(c) {
    const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) { return null; }
    const p = m[1].split(/[ ,\\/]+/).filter(Boolean).map(Number);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  }
  function over(top, under) {
    return [0, 1, 2].map(i => top[i] * top[3] + under[i] * (1 - top[3]))
      .concat([1]);
  }
  function lum(c) {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92
      : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  }
  function ratio(a, b) {
    const x = lum(a), y = lum(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
  }
  function ground(el) {
    const layers = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) { break; } }
    }
    let base = [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) { base = over(layers[i], base); }
    return base;
  }
  const out = [];
  const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.textContent.trim()) { continue; }
    const el = node.parentElement;
    if (seen.has(el)) { continue; }
    seen.add(el);
    const box = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    if (!box.width || !box.height || style.visibility === 'hidden') { continue; }
    const under = ground(el);
    const fill = 'rgb(' + under.slice(0, 3).map(Math.round).join(', ') + ')';
    let through = 1;
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      through *= Number(getComputedStyle(n).opacity);
    }
    let ink = parse(style.color);
    ink = [ink[0], ink[1], ink[2], ink[3] * through];
    if (ink[3] < 1) { ink = over(ink, under); }
    out.push([node.textContent.trim().slice(0, 40), style.color, fill,
              ratio(ink, under)]);
  }
  return out;
}"""


def every_text(page):
    """`[(text, colour, ground, ratio)]` for every text on screen, in any
    colour."""
    return page.evaluate(TEXT_CONTRAST)


def open_in_theme(browser, tmp_path, payload, theme):
    page = open_board(browser, tmp_path, payload)
    page.evaluate("t => { localStorage.setItem('purlin-theme', t); }", theme)
    page.reload()
    page.wait_for_selector('.topbar', timeout=10000)
    assert page.get_attribute('html', 'data-theme') == theme
    return page


def _every_text_in(browser, tmp_path, theme, relaxed=None):
    """Every sample in one theme, on the board with its first spec open and
    then on the screen of each of that spec's rules: how many texts were
    measured, those under their least ratio, and whether the four state
    colours and the accent are among what was measured. The least ratio is
    7:1, but `relaxed` gives a colour token its own."""
    relaxed = relaxed or {}
    checked = 0
    low = []
    tones = set()
    measured = set()
    for process in WALKED:
        page = open_in_theme(browser, tmp_path / process,
                             payload_named(process), theme)
        page.click('.tr')
        found = every_text(page)
        count = len(page.query_selector_all('.rule'))
        assert count, process
        for index in range(count):
            page.query_selector_all('.rule')[index].click()
            page.wait_for_selector('h1', timeout=10000)
            found += every_text(page)
            page.click('[data-act="close"]')
            page.wait_for_selector('.rule', timeout=10000)
        for name in ('--state-pass', '--state-warn', '--state-fail',
                     '--state-neutral', '--text-accent'):
            tones.add(resolved(page, name))
        least = {resolved(page, name): ratio
                 for name, ratio in relaxed.items()}
        page.close()
        low += [(process, item) for item in found
                if item[3] < least.get(item[1], 7)]
        checked += len(found)
        measured |= {item[1] for item in found}
    return checked, low, tones, measured


# purlin: purlin_report PROOF-66
def test_every_text_measures_7_to_1_in_the_dark_theme(browser, tmp_path):
    """The four samples, each on the board with its first spec open and
    then on the screen of each of that spec's rules; every text node's
    computed colour against the ground under it: 7:1, and 4.5:1 for text in
    the fail colour and the accent colour."""
    checked, low, tones, measured = _every_text_in(
        browser, tmp_path, 'dark',
        {'--state-fail': 4.5, '--text-accent': 4.5})
    assert low == [], low
    assert checked > 300, checked
    assert tones & measured == tones, (tones, measured)


# purlin: purlin_report PROOF-104
def test_every_text_measures_7_to_1_in_the_light_theme(browser, tmp_path):
    """The four samples, each on the board with its first spec open and
    then on the screen of each of that spec's rules; every text node's
    computed colour against the ground under it, state colours and the
    accent included."""
    checked, low, tones, measured = _every_text_in(browser, tmp_path, 'light')
    assert low == [], low
    assert checked > 300, checked
    assert tones & measured == tones, (tones, measured)
    # Each sample's board with its first spec open, measured here as it is
    # seen, through any opacity it is drawn at: nothing under 7:1, the rule
    # texts of the open spec among what was measured.
    for process in WALKED:
        payload = payload_named(process)
        page = open_in_theme(browser, tmp_path / ('board-' + process),
                             payload, 'light')
        page.click('.tr')
        rule_texts = texts(page, '.rule .rt')
        found = every_text(page)
        page.close()
        assert rule_texts, process
        assert [item for item in found if item[3] < 7] == [], (process, found)
        assert {text[:40] for text in rule_texts} <= {
            item[0] for item in found}, (process, rule_texts)


# ---------------------------------------------------------------------------
# A rule's proofs, on its screen
# ---------------------------------------------------------------------------

def resolved(page, token):
    """The computed colour a token resolves to on this page."""
    return page.evaluate(
        "n => { const s = document.createElement('span');"
        " s.style.color = getComputedStyle(document.documentElement)"
        ".getPropertyValue(n).trim(); document.body.appendChild(s);"
        " const v = getComputedStyle(s).color; s.remove(); return v; }", token)


def test_dots(page, selector='.proof .ptests p'):
    """Each test line's dot: its hover, its colour, and how many badges the
    line carries beside it."""
    return page.eval_on_selector_all(
        selector,
        "els => els.map(e => { const d = e.firstElementChild;"
        " return [d.classList.contains('dot') ? d.getAttribute('title') : null,"
        " getComputedStyle(d).backgroundColor,"
        " e.querySelectorAll('.pill').length]; })")


test_dots.__test__ = False


def proof_lines(page, selector='.proof'):
    """What the proofs on the open rule's screen read, one line per row."""
    return page.eval_on_selector_all(
        selector + ' .kv > *',
        r'els => els.map(e => e.textContent.trim().replace(/\s+/g, " "))')


def login_open(browser, tmp_path, payload=None):
    """The regulated sample's board with login open."""
    page = open_board(browser, tmp_path, payload or payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    return page


# purlin: purlin_report PROOF-155
def test_a_rules_screen_reads_each_proof(browser, tmp_path):
    page = open_sample(browser, tmp_path, 'regulated')
    open_rule(page, 'login', 'RULE-4')
    assert proof_lines(page) == [
        'PROOF-4',
        'On Windows, open http://localhost/session and read that no cookie '
        'is set.',
        'Result', 'FAILED', 'Tags', '@env(windows)',
        'Tests', 'tests/test_login.py :: test_no_cookie',
        'PROOF-5',
        'Read the Set-Cookie header of a 200 response and verify it carries '
        'Secure.',
        'Result', 'PASSED',
        'Tests', 'tests/test_login.py :: test_secure_flag']
    page.close()


# purlin: purlin_report PROOF-180
def test_a_test_line_starts_with_a_dot_in_its_results_colour(browser,
                                                             tmp_path):
    page = open_sample(browser, tmp_path, 'regulated')
    open_rule(page, 'login', 'RULE-4')
    assert texts(page, '.proof .ptests p') == [
        'tests/test_login.py :: test_no_cookie',
        'tests/test_login.py :: test_secure_flag']
    assert test_dots(page) == [
        ['failed', resolved(page, '--state-fail'), 0],
        ['passed', resolved(page, '--state-pass'), 0]]
    page.close()


# purlin: purlin_report PROOF-69
def test_a_proof_with_no_test_names_the_build(browser, tmp_path):
    payload = payload_named('solo')
    words = rule_of(payload, 'login', 'RULE-2')['proofs'][0]['text']
    page = open_board(browser, tmp_path, payload)
    open_rule(page, 'login', 'RULE-2')
    assert proof_lines(page) == [
        'PROOF-2', words, 'Result', 'NO TEST', 'Tests',
        'No test yet. Type purlin:build login in Claude Code.']
    page.close()


ANCHOR_TEXT = 'The cart page shows the order total above the pay button.'
RECEIPT_TEXT = 'A receipt names the order number and the total paid.'


# purlin: purlin_report PROOF-107
def test_an_anchors_rule_is_listed_under_the_anchor_alone(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('team'))
    for name in feature_names(page):
        page.click('[data-act="feature"][data-feature="%s"]' % name)
    assert texts(page, '.rule[data-feature="receipt"] .rid') == ['RULE-1']
    assert texts(page, '.rule .rt').count(ANCHOR_TEXT) == 1
    # Once on the whole screen, whatever element draws it.
    assert page.inner_text('body').count(ANCHOR_TEXT) == 1
    assert page.inner_text(
        '.rule[data-feature="checkout_design"]').count(ANCHOR_TEXT) == 1
    assert texts(page, '.rule[data-feature="checkout_design"] .rt') == [
        ANCHOR_TEXT]
    page.close()


# The open rule's heading: the spec that owns the rule, then the rule's id.
HEADING = """() => Array.from(document.querySelector('hgroup').children)
  .map(e => e.textContent.trim())"""


# purlin: purlin_report PROOF-108
def test_a_features_own_rule_opens_its_own_screen(browser, tmp_path):
    page = open_sample(browser, tmp_path, 'team')
    open_rule(page, 'receipt', 'RULE-1')
    heading = page.evaluate(HEADING)
    body = page.inner_text('.wrap')
    page.close()
    assert heading == ['receipt', 'RULE-1'], heading
    assert RECEIPT_TEXT in body
    assert ANCHOR_TEXT not in body


# purlin: purlin_report PROOF-109
def test_an_anchors_rule_opens_the_anchors_screen(browser, tmp_path):
    page = open_sample(browser, tmp_path, 'team')
    open_rule(page, 'checkout_design', 'RULE-1')
    heading = page.evaluate(HEADING)
    body = page.inner_text('.wrap')
    page.close()
    assert heading == ['checkout_design', 'RULE-1'], heading
    assert ANCHOR_TEXT in body
    assert RECEIPT_TEXT not in body


# ---------------------------------------------------------------------------
# The badges on a rule's row
# ---------------------------------------------------------------------------

def row_badges(page, feature):
    """Each rule of an open spec and the badges its row carries."""
    return dict(page.eval_on_selector_all(
        '.rule[data-feature="%s"]' % feature,
        "els => els.map(e => [e.getAttribute('data-rule'), Array.from("
        "e.querySelectorAll('.rp .pill')).map(p => p.innerText.trim())"
        ".join(' ')])"))


# purlin: purlin_report PROOF-165
def test_a_rules_row_carries_a_badge_for_each_count_it_is_in(browser,
                                                            tmp_path):
    payload = payload_named('regulated')
    assert rule_of(payload, 'login', 'RULE-4')['cells']['passed'][
        'platforms']['windows']['word'] == 'failed'
    page = login_open(browser, tmp_path, payload)
    assert row_badges(page, 'login') == {
        'RULE-1': 'PASSED STRONG', 'RULE-2': 'PASSED STRONG',
        'RULE-3': 'PASSED', 'RULE-4': 'FAILED'}
    page.close()


# purlin: purlin_report PROOF-167
def test_the_badges_add_up_to_the_step_boxes(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    for name in feature_names(page):
        page.click('[data-act="feature"][data-feature="%s"]' % name)
    seen = texts(page, '.rule .rp .pill')
    found = boxes(page)
    page.close()
    assert [seen.count(word) for word in ('PASSED', 'STRONG')] == [7, 3], seen
    assert [int(count) for _, count, _ in found[1:]] == [7, 3]


# ---------------------------------------------------------------------------
# The lines the page draws where there is little to show
# ---------------------------------------------------------------------------

# purlin: purlin_report PROOF-184
def test_an_uncommitted_tree_is_named_on_the_board(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['dirty'] is True
    page = open_board(browser, tmp_path, payload)
    assert ('working tree: changes not committed. This board is not what a '
            'commit would carry. Commit them, then run '
            'purlin:status.') in texts(page, '.notice-text')
    # The notice is drawn, its line whole: it is the first on the board, a
    # person sees it, and nothing of it is hidden but the two marks a
    # notice never draws.
    first = page.query_selector_all('.notice')[0]
    assert first.is_visible()
    assert first.query_selector('.notice-text').text_content().strip() == (
        'working tree: changes not committed. This board is not what a '
        'commit would carry. Commit them, then run purlin:status.')
    assert [piece for piece in undrawn(page, '.notice')
            if piece not in NOT_DRAWN_IN_A_NOTICE] == []
    page.close()


# purlin: purlin_report PROOF-189
def test_a_spec_no_run_covered_says_so_in_its_hover(browser, tmp_path):
    payload = payload_named('team')
    login = payload['features'][0]
    assert login['name'] == 'login'
    for rule in login['rules']:
        rule['cells']['passed']['platforms'] = {}
    page = open_board(browser, tmp_path, payload)
    assert hovers(page)['login']['Tests'] == (
        'No counting run has covered a platform yet.')
    page.close()


# ---------------------------------------------------------------------------
# The anchors' section
# ---------------------------------------------------------------------------

def section_labels(page):
    """Each section label on the board, as a person reads it."""
    return page.eval_on_selector_all(
        '.eyebrow', 'els => els.map(e => e.innerText.trim())')


def listed_in(page, table):
    """The specs one table lists, in order: `anchors` or `specs`."""
    return texts(page, '[data-table="%s"] .tr .name .n' % table)


# purlin: purlin_report PROOF-203
def test_the_anchors_stand_in_a_section_of_their_own(browser, tmp_path):
    page = open_sample(browser, tmp_path, 'regulated')
    assert section_labels(page) == ['ANCHORS', 'SPECS']
    below = page.evaluate(
        "() => Math.max(...Array.from(document.querySelectorAll('.tile')).map("
        "t => t.getBoundingClientRect().bottom))"
        " <= document.querySelector('[data-table=\"anchors\"]')"
        ".getBoundingClientRect().top")
    anchors = listed_in(page, 'anchors')
    heads = texts(page, '[data-table="anchors"] .th > div')
    specs = listed_in(page, 'specs')
    # Everything the section's table holds: its headings, then its rows.
    held = page.eval_on_selector(
        '[data-table="anchors"] .tbl',
        'e => Array.from(e.children).map(c => c.className)')
    opened = texts(page, '[data-table="anchors"] .rule .rid')
    page.close()
    assert below
    assert held == ['th', 'tr', 'tr'], held
    assert opened == [], opened
    assert anchors == ['checkout_design', 'security_baseline'], anchors
    assert heads == ['Spec', 'Rules', 'Proofs', 'Tests', 'Strong']
    assert specs == ['login', 'invoice', 'export'], specs


# purlin: purlin_report PROOF-204
def test_a_project_with_no_anchor_has_no_anchors_section(browser, tmp_path):
    payload = payload_named('solo')
    assert not any(f['is_anchor'] for f in payload['features'])
    page = open_board(browser, tmp_path, payload)
    labels = section_labels(page)
    page.close()
    assert labels == ['SPECS'], labels


# ---------------------------------------------------------------------------
# A spec to repair
# ---------------------------------------------------------------------------

# The word and the reasons of one row of the open rule's cells, by its label.
CELL_ROW = """name => {
  const dt = Array.from(document.querySelectorAll('.kv dt'))
    .find(e => e.textContent.trim() === name);
  const dd = dt.nextElementSibling;
  return [dd.querySelector('.pill').innerText.trim(),
          Array.from(dd.querySelectorAll(':scope > .sec'))
            .map(e => e.innerText.trim()).join(' ')];
}"""


# purlin: purlin_report PROOF-217
def test_a_rule_of_a_spec_to_repair_says_why(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('team'))
    open_rule(page, 'refund', 'RULE-2')
    row = page.evaluate(CELL_ROW, 'Tests')
    page.close()
    assert row == ['FAILED', 'PROOF-2 is written twice in the spec'], row


# ---------------------------------------------------------------------------
# A hand check, and a proof that found nothing to check
# ---------------------------------------------------------------------------

def hand_check_rule(payload):
    """The regulated sample's invoice `RULE-3`, whose `@manual` proof no
    test carries."""
    invoice = next(f for f in payload['features'] if f['name'] == 'invoice')
    rule = next(r for r in invoice['rules'] if r['id'] == 'RULE-3')
    assert rule['proofs'][0]['manual'] and rule['proofs'][0]['tests'] == []
    return rule


def hand_check_tests(page):
    """The lines under `Tests` of the open rule's one proof."""
    return texts(page, '.proof .ptests p')


# purlin: purlin_report PROOF-228
def test_a_hand_check_no_sign_off_noted_reads_checked_at_sign_off(browser,
                                                                 tmp_path):
    payload = payload_named('regulated')
    assert hand_check_rule(payload)['cells']['strong']['reasons'] == []
    page = open_board(browser, tmp_path, payload)
    open_rule(page, 'invoice', 'RULE-3')
    assert hand_check_tests(page) == ['checked at sign-off']
    page.close()


# purlin: purlin_report PROOF-229
def test_a_hand_check_reads_the_newest_sign_offs_note_beneath_it(browser,
                                                                tmp_path):
    sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
    from purlin import states

    def noted(payload):
        hand_check_rule(payload)['cells']['strong']['reasons'] = [
            states.HAND_NOTE % ('0.1.0', 'quinn.qa@labconnect.example',
                                '4 commits since', 'the tube is red')]
    page = open_sample(browser, tmp_path, 'regulated', noted)
    open_rule(page, 'invoice', 'RULE-3')
    assert hand_check_tests(page) == [
        'checked at sign-off',
        'noted at the sign-off of 0.1.0 by quinn.qa@labconnect.example, '
        '4 commits since: the tube is red']
    page.close()


# purlin: purlin_report PROOF-246
def test_a_note_written_before_the_rule_was_reworded_says_so_above_it(
        browser, tmp_path):
    sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
    from purlin import states
    note = states.HAND_NOTE % ('0.1.0', 'quinn.qa@labconnect.example',
                               '4 commits since', 'the tube is red')

    def reworded_since_its_note(payload):
        """What `states` writes for a hand check whose rule was reworded
        after the sign-off of `0.1.0` noted it."""
        reasons = [states.HAND_CHANGED['rule'], note]
        cells = hand_check_rule(payload)['cells']
        cells['passed']['reasons'] = list(reasons)
        cells['strong']['reasons'] = list(reasons)
    page = open_sample(browser, tmp_path, 'regulated', reworded_since_its_note)
    open_rule(page, 'invoice', 'RULE-3')
    lines = hand_check_tests(page)
    page.close()
    assert lines == ['checked at sign-off',
                     "the rule's wording changed since its last note",
                     note], lines


# purlin: purlin_report PROOF-227
def test_an_anchors_rule_with_nothing_to_check_says_why_it_passed(browser,
                                                                 tmp_path):
    sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
    from purlin import states
    reason = 'this project has no screens'

    def skipped_with_nothing_to_check(payload):
        """What `states` writes for an anchor's rule whose proof's one test
        skipped with `nothing to check: this project has no screens`."""
        rule = rule_of(payload, 'security_baseline', 'RULE-1')
        rule['proofs'][0].update(result='passed', tests=[
            {'file': 'tests/test_security.py', 'name': 'test_no_inline_script',
             'result': 'not run'}])
        rule['cells']['passed'].update(
            word='passed', current=True, counts=True, source='ci',
            nothing_to_check=[{'proof': 'PROOF-1', 'reason': reason}],
            reasons=[states.NOTHING_TO_CHECK % ('PROOF-1', reason)])
    page = open_sample(browser, tmp_path, 'regulated',
                       skipped_with_nothing_to_check)
    open_rule(page, 'security_baseline', 'RULE-1')
    row = page.evaluate(CELL_ROW, 'Tests')
    page.close()
    assert row == ['PASSED', 'PROOF-1: this project has no screens'], row


# ---------------------------------------------------------------------------
# The top bar: the two facts, and what the data describes
# ---------------------------------------------------------------------------

def facts(page):
    """The top bar's boxes, each as `[label, word]`."""
    return page.eval_on_selector_all(
        '.topbar .fact', "els => els.map(e => [e.firstElementChild"
        ".textContent.trim(), e.lastElementChild.textContent.trim()])")


# purlin: purlin_report PROOF-223
def test_the_top_bar_reads_met_and_the_sign_off_at_its_commit(browser,
                                                             tmp_path):
    def passing_and_signed(payload):
        payload.update(met=True, left=[], signoff={
            'word': 'signed 0.1.0 at a1b2c3d', 'version': '0.1.0',
            'commit': payload['commit'], 'since': 0})
    page = open_sample(browser, tmp_path, 'regulated', passing_and_signed)
    found = facts(page)
    page.close()
    assert found == [['Tests', 'met'],
                     ['Sign-off', 'signed 0.1.0 at a1b2c3d']], found


# purlin: purlin_report PROOF-225
def test_a_failing_rule_and_no_sign_off_read_not_met_and_not_signed(
        browser, tmp_path):
    payload = payload_named('solo')
    assert 'failed' in [rule['cells']['passed']['word']
                        for feature in payload['features']
                        for rule in feature['rules']]
    assert payload['met'] is False and payload['signoff']['version'] is None
    page = open_board(browser, tmp_path, payload)
    found = facts(page)
    page.close()
    assert found == [['Tests', 'not met'],
                     ['Sign-off', 'not signed']], found


# The top bar's boxes, each with its label, its word, the colour it is drawn
# in and its hover.
FACT_BOXES = """() => Array.from(document.querySelectorAll('.topbar .fact')).map(
  e => ({label: e.firstElementChild.textContent.trim(),
         word: e.lastElementChild.textContent.trim(),
         color: getComputedStyle(e).color,
         hover: e.getAttribute('title')}))"""


# The count boxes, each with its label, its count, the colour the count is
# drawn in and its hover.
COUNT_BOXES = """() => Array.from(document.querySelectorAll('.tile')).map(e => {
  const count = e.querySelector('.tile-v');
  return {label: e.querySelector('.tile-l').textContent.trim(),
          word: count.textContent.trim(),
          color: getComputedStyle(count).color,
          hover: e.getAttribute('title')};
})"""


# purlin: purlin_report PROOF-241
def test_no_audit_and_no_sign_off_show_two_boxes_and_not_signed_plain(
        browser, tmp_path):
    payload = payload_named('solo')
    assert not [rule for feature in payload['features']
                for rule in feature['rules'] if rule['audit']]
    page = open_board(browser, tmp_path, payload)
    found = {box['label']: box for box in page.evaluate(FACT_BOXES)}
    plain = resolved(page, '--text-secondary')
    tones = [resolved(page, '--state-' + tone)
             for tone in ('pass', 'warn', 'fail', 'neutral')]
    border = page.eval_on_selector_all(
        '.topbar .fact', 'els => getComputedStyle(els[1]).borderTopColor')
    # The colour each word of the box is drawn in, not the box's own.
    words = page.eval_on_selector_all(
        '.topbar .fact', "els => Array.from(els[1].querySelectorAll('*'))"
        ".map(e => [e.textContent.trim(), getComputedStyle(e).color])")
    heads = head_labels(page)
    page.close()
    assert list(found) == ['Tests', 'Sign-off'], found
    assert found['Sign-off']['word'] == 'not signed'
    assert found['Sign-off']['color'] == border == plain
    assert words == [['Sign-off', plain], ['not signed', plain]], words
    assert plain not in tones
    assert heads == ['Spec', 'Rules', 'Proofs', 'Tests'], heads


# purlin: purlin_report PROOF-242
def test_the_strong_box_reads_the_count_and_its_hover_the_counts(browser,
                                                                tmp_path):
    payload = payload_named('regulated')
    assert payload['summary']['audit'] == {
        'strong': 3, 'weak': 3, 'spot_checked': 0, 'out_of_date': 0,
        'not_audited': 1}
    assert max(rule['audit']['at'] for feature in payload['features']
               for rule in feature['rules'] if rule['audit']
               ).startswith('2026-09-12')
    page = open_board(browser, tmp_path, payload)
    found = {box['label']: box for box in page.evaluate(COUNT_BOXES)}
    warn = resolved(page, '--state-warn')
    page.close()
    assert found['Strong']['word'] == '3', found
    assert found['Strong']['color'] == warn
    assert found['Strong']['hover'].split('\n') == [
        '3 strong', '3 weak', '1 not audited', 'Last audit: 2026-09-12']


def only_spot_checked(payload):
    """Give the solo sample its one audit entry: login's `RULE-1`, read
    `spot-checked`, as the payload carries one."""
    rule = rule_of(payload, 'login', 'RULE-1')
    assert rule['cells']['passed']['word'] == 'passed'
    sentence = ('No bug was planted: the model could not be reached: claude '
                'is not on PATH.')
    rule['cells']['strong'] = {
        'word': 'spot-checked', 'findings': [],
        'evidence': '.purlin/evidence/local/login.json',
        'reasons': ['The spot tests found nothing. ' + sentence]}
    rule['audit'] = {
        'verdict': 'spot-checked', 'findings': [], 'no_bug': [sentence],
        'notes': [], 'explanation': [], 'bugs': {}, 'model': 'unknown',
        'at': '2026-09-12T09:14:02Z', 'commit': 'a1b2c3d' + '0' * 33,
        'path': '.purlin/evidence/local/login.json', 'out_of_date': []}
    rule['flags'].update({'not_audited': False, 'spot_checked': True})
    payload['summary']['audit'].update(spot_checked=1, not_audited=1)


# purlin: purlin_report PROOF-243
def test_one_spot_checked_result_draws_the_strong_column_and_box(
        browser, tmp_path):
    page = open_sample(browser, tmp_path, 'solo', only_spot_checked)
    heads = head_labels(page)
    cell = page.inner_text(
        '.tr[data-feature="login"] [data-label="Strong"]').strip()
    tiles = {box[0]: box[1] for box in boxes(page)}
    open_rule(page, 'login', 'RULE-1')
    lines = panel_lines(page, 'Audit')
    page.close()
    assert heads == ['Spec', 'Rules', 'Proofs', 'Tests', 'Strong'], heads
    assert cell == '0 of 1', cell
    assert tiles['Strong'] == '0', tiles
    assert lines[0] == 'Spot-checked.', lines


# ---------------------------------------------------------------------------
# An anchor is never rated strong
# ---------------------------------------------------------------------------

NO_ANCHOR_BUG = "No bug is planted for an anchor's rule."
ANCHOR_STRONG = '.tr[data-feature="checkout_design"] [data-label="Strong"]'


def anchor_rule(payload):
    """The one rule of the anchor `checkout_design`, which passes its tests
    and carries an audit entry in the team and the regulated sample."""
    rule = rule_of(payload, 'checkout_design', 'RULE-1')
    assert rule['cells']['passed']['word'] == 'passed'
    assert rule['audit']
    return rule


def anchor_entry_out_of_date(payload):
    """The team sample after the project's code changed since the entry of
    the anchor's rule was written, as the payload carries it."""
    rule = anchor_rule(payload)
    rule['audit']['out_of_date'] = ['code']
    rule['cells']['strong'].update({
        'word': 'out of date',
        'reasons': ['The code changed since the audit at a1b2c3d.',
                    'The last audit found it spot-checked on 2026-09-12.']})
    rule['flags'].update({'spot_checked': False, 'audit_out_of_date': True})
    payload['summary']['audit']['spot_checked'] -= 1
    payload['summary']['audit']['out_of_date'] += 1


def anchor_never_audited(payload):
    """The team sample with the anchor's rule passing its tests and read by
    no audit."""
    rule = anchor_rule(payload)
    rule['audit'] = None
    rule['cells']['strong'] = {
        'word': 'not audited', 'findings': [], 'evidence': None,
        'reasons': ['no audit has read this rule']}
    rule['flags'].update({'spot_checked': False, 'not_audited': True})
    payload['summary']['audit']['spot_checked'] -= 1
    payload['summary']['audit']['not_audited'] += 1


def every_feature_rule_strong(payload):
    """The team sample after login's `RULE-1`, the one rule the audit found
    weak, is found strong: every rule that passes its tests and is not an
    anchor's then reads `strong`, and the anchor's reads `spot-checked`."""
    rule = rule_of(payload, 'login', 'RULE-1')
    assert rule['cells']['strong']['word'] == 'weak'
    rule['audit'].update({'verdict': 'strong', 'findings': []})
    rule['cells']['strong'].update({'word': 'strong', 'findings': [],
                                    'reasons': []})
    rule['flags'].update({'weak': False, 'strong': True})
    rule['left'] = None
    payload['summary']['audit'].update(strong=5, weak=0)
    words = {entry['cells']['strong']['word']
             for feature in payload['features'] if not feature['is_anchor']
             for entry in feature['rules']
             if entry['cells']['passed']['word'] == 'passed'}
    assert words == {'strong'}, words
    assert anchor_rule(payload)['cells']['strong']['word'] == 'spot-checked'


# purlin: purlin_report PROOF-249
def test_an_anchor_whose_rule_is_spot_checked_reads_the_word_alone(
        browser, tmp_path):
    page = open_sample(browser, tmp_path, 'team')
    cells = count_cells(page)
    page.close()
    assert cells['checkout_design']['Strong'] == 'spot-checked', cells
    assert cells['receipt']['Strong'] == '1 of 1', cells


# purlin: purlin_report PROOF-250
def test_an_anchor_with_a_weak_rule_reads_weak_in_the_warn_tone(
        browser, tmp_path):
    payload = payload_named('regulated')
    assert anchor_rule(payload)['cells']['strong']['word'] == 'weak'
    page = open_board(browser, tmp_path, payload)
    word = page.inner_text(ANCHOR_STRONG).strip()
    colour = page.eval_on_selector(ANCHOR_STRONG + ' b',
                                   'e => getComputedStyle(e).color')
    warn = resolved(page, '--state-warn')
    page.close()
    assert word == 'weak', word
    assert colour == warn, (colour, warn)


# purlin: purlin_report PROOF-251
def test_an_anchor_whose_entry_is_out_of_date_reads_out_of_date(
        browser, tmp_path):
    page = open_sample(browser, tmp_path, 'team', anchor_entry_out_of_date)
    word = page.inner_text(ANCHOR_STRONG).strip()
    page.close()
    assert word == 'out of date', word


# purlin: purlin_report PROOF-252
def test_an_anchor_no_audit_read_has_an_empty_strong_cell(browser, tmp_path):
    page = open_sample(browser, tmp_path, 'team', anchor_never_audited)
    heads = head_labels(page)
    cells = count_cells(page)
    page.close()
    assert heads[-1] == 'Strong', heads
    assert cells['checkout_design']['Strong'] == '', cells
    assert cells['security_baseline']['Strong'] == '', cells


# purlin: purlin_report PROOF-253
def test_an_anchors_strong_hover_says_first_that_no_bug_is_planted(
        browser, tmp_path):
    # The clock stands at the moment the sample was written, 2026-10-01
    # 10:42:13 UTC, 19 days after its audit of 2026-09-12.
    page = open_sample(browser, tmp_path, 'team',
                       clock_at='2026-10-01T10:42:13Z')
    found = hovers(page)
    page.close()
    lines = found['checkout_design']['Strong'].split('\n')
    assert len(lines) == 2, lines
    assert lines[0] == NO_ANCHOR_BUG, lines
    assert lines[1].startswith('audit · local · '), lines
    assert lines == ["No bug is planted for an anchor's rule.",
                     'audit · local · 19 days old'], lines
    assert NO_ANCHOR_BUG not in found['receipt']['Strong'], found['receipt']


# purlin: purlin_report PROOF-254
def test_the_strong_box_is_complete_beside_a_spot_checked_anchor(
        browser, tmp_path):
    page = open_sample(browser, tmp_path, 'team', every_feature_rule_strong)
    found = {box['label']: box for box in page.evaluate(COUNT_BOXES)}
    passing = resolved(page, '--state-pass')
    page.close()
    assert found['Strong']['word'] == '5', found
    assert found['Strong']['color'] == passing, found
    assert found['Strong']['hover'].split('\n')[:2] == [
        '5 strong', '1 spot-checked'], found


# purlin: purlin_report PROOF-255
def test_the_strong_box_waits_on_a_weak_rule_that_is_not_an_anchors(
        browser, tmp_path):
    payload = payload_named('team')
    assert payload['summary']['audit'] == {
        'strong': 4, 'weak': 1, 'spot_checked': 1, 'out_of_date': 0,
        'not_audited': 0}
    page = open_board(browser, tmp_path, payload)
    found = {box['label']: box for box in page.evaluate(COUNT_BOXES)}
    warn = resolved(page, '--state-warn')
    page.close()
    assert found['Strong']['word'] == '4', found
    assert found['Strong']['color'] == warn, found


# purlin: purlin_report PROOF-256
def test_no_strong_box_where_the_audit_read_an_anchor_alone(browser,
                                                           tmp_path):
    def anchors_alone(payload):
        payload['features'] = [feature for feature in payload['features']
                               if feature['is_anchor']]
        payload['summary']['audit'] = {
            'strong': 0, 'weak': 0, 'spot_checked': 1, 'out_of_date': 0,
            'not_audited': 0}
    page = open_sample(browser, tmp_path, 'team', anchors_alone)
    labels = [box['label'] for box in page.evaluate(COUNT_BOXES)]
    heads = texts(page, '[data-table="anchors"] .th > div')
    cell = page.inner_text(
        '.tr[data-feature="checkout_design"] [data-label="Strong"]').strip()
    page.close()
    assert 'Passing' in labels and 'Strong' not in labels, labels
    assert heads[-1] == 'Strong', heads
    assert cell == 'spot-checked', cell


def stamp(page):
    """The top bar's line naming the checkout state, and its hover."""
    return [page.inner_text('.topbar .stamp').strip(),
            page.get_attribute('.topbar .stamp', 'title')]


# purlin: purlin_report PROOF-232
def test_the_top_bar_names_the_branch_the_commit_and_when(browser, tmp_path):
    payload = payload_named('regulated')
    assert (payload['branch'], payload['commit'][:7]) == ('main', 'a1b2c3d')
    assert payload['generated_at'] == '2026-10-01T10:42:13Z'
    opened = datetime.datetime(2026, 10, 1, 10, 45, 0,
                               tzinfo=datetime.timezone.utc)
    page = open_board(browser, tmp_path, payload, clock_at=opened,
                      timezone='America/New_York')
    first = stamp(page)
    page.clock.run_for(2 * 60 * 60 * 1000)
    later = stamp(page)
    page.close()
    assert first == ['main at a1b2c3d, written 06:42 EDT',
                     '2026-10-01 06:42 EDT (10:42 UTC)'], first
    assert later == first, later


# purlin: purlin_report PROOF-237
def test_a_browser_set_to_utc_reads_the_time_in_utc(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['generated_at'] == '2026-10-01T10:42:13Z'
    page = open_board(browser, tmp_path, payload, timezone='UTC')
    line = stamp(page)[0]
    page.close()
    assert line == 'main at a1b2c3d, written 10:42 UTC', line



# Each proof panel's rows on the rule screen, by label, and for the row
# `Carried from` how many lines each of its values is drawn on.
PROOF_ROWS = r"""() => Array.from(document.querySelectorAll('.proof .kv'))
  .map(list => {
    const out = {};
    let key = null;
    Array.from(list.children).forEach(node => {
      if (node.tagName === 'DT') { key = node.textContent.trim(); }
      else { out[key] = node.innerText.trim().replace(/\s+/g, ' '); }
    });
    out.lines = Array.from(list.querySelectorAll('.carried'))
      .map(value => value.getClientRects().length);
    return out;
  })"""


def carried_from(payload, carried):
    rule_of(payload, 'login', 'RULE-1')['proofs'][0]['carried'] = carried


# purlin: purlin_report PROOF-283
def test_a_carried_proof_names_the_system_and_the_commit(browser, tmp_path):
    seen = {}
    for width in (1500, 1280, 1024, 768, 390):
        page = open_sample(
            browser, tmp_path / str(width), 'regulated',
            change=lambda payload: carried_from(payload, {
                'windows': '9b2e7c4d' * 5, 'linux': 'a1b2c3d4' * 5}),
            viewport={'width': width, 'height': 900})
        open_rule(page, 'login', 'RULE-1')
        seen[width] = page.evaluate(PROOF_ROWS)[0]
        page.close()
    for width, rows in seen.items():
        assert rows['Carried from'] == 'Lin a1b2c3d Win 9b2e7c4', (width, rows)
        assert rows['lines'] == [1, 1], (width, rows)
        assert list(rows).index('Carried from') == list(rows).index(
            'Result') + 1, (width, rows)


# purlin: purlin_report PROOF-285
def test_the_carried_row_measures_7_to_1_in_both_themes(browser, tmp_path):
    payload = payload_named('regulated')
    carried_from(payload, {'windows': '9b2e7c4d' * 5, 'linux': 'a1b2c3d4' * 5})
    for theme in ('dark', 'light'):
        page = open_in_theme(browser, tmp_path / theme, payload, theme)
        open_rule(page, 'login', 'RULE-1')
        found = {item[0]: item[3] for item in every_text(page)
                 if item[0] in ('Carried from', 'Lin', 'a1b2c3d', 'Win',
                                '9b2e7c4')}
        assert len(found) == 5 and min(found.values()) >= 7, (theme, found)
        page.close()


# purlin: purlin_report PROOF-284
def test_a_proof_whose_run_took_its_results_has_no_such_row(browser,
                                                             tmp_path):
    page = open_sample(browser, tmp_path, 'regulated',
                       change=lambda payload: carried_from(payload, {}))
    open_rule(page, 'login', 'RULE-1')
    assert 'Carried from' not in page.evaluate(PROOF_ROWS)[0]
    page.close()
    # The same where the data names nothing carried at all: the sample as
    # it is written, whose proof holds no `carried`, and the proof given
    # `carried` as nothing.
    payload = payload_named('regulated')
    assert 'carried' not in rule_of(payload, 'login', 'RULE-1')['proofs'][0]
    for name, carried in (('absent', False), ('null', True)):
        if carried:
            carried_from(payload, None)
        page = open_board(browser, tmp_path / name, payload)
        open_rule(page, 'login', 'RULE-1')
        rows = page.evaluate(PROOF_ROWS)[0]
        shown = page.inner_text('.panel.proof')
        page.close()
        assert list(rows) == ['PROOF-1', 'Result', 'Tests', 'lines'], (
            name, rows)
        assert rows['lines'] == [], (name, rows)
        assert 'carried from' not in shown.lower(), (name, shown)


# purlin: purlin_report PROOF-286
def test_a_rule_with_no_proof_names_where_its_tests_were_carried_from(
        browser, tmp_path):
    payload = without_proof_lines(payload_named('solo'))
    rule_of(payload, 'login', 'RULE-1')['carried'] = {'macos': 'a1b2c3d4' * 5}
    page = open_board(browser, tmp_path, payload)
    open_rule(page, 'login', 'RULE-1')
    rows = page.evaluate(KV_ROWS)
    assert rows['Carried from'] == 'Mac a1b2c3d', rows
    assert list(rows)[-2:] == ['Last run', 'Carried from'], rows
    page.close()


# ---------------------------------------------------------------------------
# What a failing test's tool reported
# ---------------------------------------------------------------------------

FAILURE_TEXT = ("AssertionError: expected 'Account locked'\n\n"
                'def test_locks_after_three_bad_passwords():\n'
                ">       assert shown == 'Account locked'\n"
                "E       AssertionError: expected 'Account locked'\n\n"
                'tests/test_login.py:41: AssertionError')

# Each failure panel on the rule screen: its text, how far it runs past its
# own box sideways, and the line before it, which names the test.
FAILURE_PANELS = r"""() => Array.from(
    document.querySelectorAll('.ptests pre.failure, .tests pre.failure'))
  .map(node => ({
    text: node.textContent,
    over: node.scrollWidth - node.clientWidth,
    before: node.previousElementSibling.innerText.trim(),
  }))"""


def given_a_failure(payload, text=FAILURE_TEXT):
    """`login RULE-1`'s first proof's first test failed, with `text` as what
    its tool reported. The test's `(file, name)`."""
    test = rule_of(payload, 'login', 'RULE-1')['proofs'][0]['tests'][0]
    test['result'] = 'fail'
    if text is None:
        test.pop('failure', None)
    else:
        test['failure'] = text
    return test['file'], test['name']


# purlin: purlin_report PROOF-287
def test_a_failing_test_shows_what_its_tool_reported(browser, tmp_path):
    payload = payload_named('regulated')
    lines = FAILURE_TEXT.split('\n')
    assert (len(lines), lines.count('')) == (7, 2), lines
    assert lines[0] == "AssertionError: expected 'Account locked'"
    file, name = given_a_failure(payload)
    page = open_board(browser, tmp_path, payload)
    open_rule(page, 'login', 'RULE-1')
    panels = page.evaluate(FAILURE_PANELS)
    # The seven lines as they are drawn, one under another: the panel keeps
    # each end of a line, each empty line and the spaces that open one.
    drawn = page.eval_on_selector_all(
        '.ptests pre.failure, .tests pre.failure',
        'els => els.map(e => e.innerText)')
    hidden = undrawn(page, 'pre.failure')
    page.close()
    assert drawn == [FAILURE_TEXT], drawn
    assert hidden == []
    assert [panel['text'] for panel in panels] == [FAILURE_TEXT], panels
    assert panels[0]['before'].replace(' ', '') == (
        '%s::%s' % (file, name)).replace(' ', ''), panels


# purlin: purlin_report PROOF-288
def test_a_failing_test_with_no_text_and_a_passing_one_show_no_panel(
        browser, tmp_path):
    payload = payload_named('regulated')
    given_a_failure(payload, text=None)
    page = open_board(browser, tmp_path / 'none', payload)
    open_rule(page, 'login', 'RULE-1')
    assert page.evaluate(FAILURE_PANELS) == []
    page.close()
    # A test that passed shows none, whatever its entry holds.
    payload = payload_named('regulated')
    test = rule_of(payload, 'login', 'RULE-1')['proofs'][0]['tests'][0]
    test['result'], test['failure'] = 'pass', FAILURE_TEXT
    page = open_board(browser, tmp_path / 'passed', payload)
    open_rule(page, 'login', 'RULE-1')
    assert page.evaluate(FAILURE_PANELS) == []
    page.close()


# purlin: purlin_report PROOF-289
def test_a_long_failure_text_never_scrolls_the_page_sideways(browser,
                                                             tmp_path):
    long = 'E   ' + 'x' * 400 + '\n' + FAILURE_TEXT
    for width in (1500, 390):
        for theme in ('dark', 'light'):
            payload = payload_named('regulated')
            given_a_failure(payload, text=long)
            page = open_in_theme(browser, tmp_path / ('%d-%s' % (width, theme)),
                                 payload, theme)
            page.set_viewport_size({'width': width, 'height': 900})
            open_rule(page, 'login', 'RULE-1')
            (panel,) = page.evaluate(FAILURE_PANELS)
            sideways = page.evaluate(
                'document.documentElement.scrollWidth'
                ' - document.documentElement.clientWidth')
            ratios = [item[3] for item in every_text(page)
                      if item[0].startswith('E   xxx')]
            page.close()
            assert panel['over'] <= 0 and sideways <= 0, (width, theme, panel)
            assert ratios and min(ratios) >= 7, (width, theme, ratios)


# ---------------------------------------------------------------------------
# A notice's name and its kind stand apart from the rest
# ---------------------------------------------------------------------------

def login_reworded(payload):
    """The regulated sample, clean, given one warning: the test of login's
    `PROOF-1 (RULE-1)` was last changed before the proof gained a word."""
    import types
    wording = status_sentences()[2]
    marker = types.SimpleNamespace(feature='login', id='PROOF-1', line=12)
    line = wording.stale_line(
        {'proofs_by_rule': {'RULE-1': ['PROOF-1']}}, 'tests/test_login.py',
        marker, '82c91f6', 'the sixteen keys the rule names',
        'the seventeen keys the rule names', None)
    payload['dirty'] = False
    give_lines(payload, [line])
    return line


NOTICE_PARTS = """() => [...document.querySelectorAll('.notice')].map(n => {
  const name = n.querySelector('.notice-name');
  const kind = n.querySelector('.notice-kind');
  return {
    text: n.querySelector('.notice-text').textContent.trim(),
    name: name && name.textContent.trim(),
    nameFont: name && getComputedStyle(name).fontFamily,
    link: !!(name && name.getAttribute('role') === 'link'),
    kind: kind && kind.textContent.trim(),
    kindBorder: kind && getComputedStyle(kind).borderTopWidth,
    restFont: getComputedStyle(n.querySelector('.notice-text')).fontFamily,
  };
})"""


# purlin: purlin_report PROOF-290
def test_a_notice_sets_its_name_in_the_machine_typeface_and_its_kind_as_a_label(
        browser, tmp_path):
    payload = payload_named('regulated')
    line = login_reworded(payload)
    assert line == (
        'login PROOF-1 (RULE-1): test comment to correct. "sixteen" became '
        '"seventeen" after tests/test_login.py:12 last changed (82c91f6). '
        'Run purlin:build login.')
    page = open_board(browser, tmp_path, payload)
    (found,) = page.evaluate(NOTICE_PARTS)
    # The rest, piece by piece: no word after the name is in Courier New,
    # whatever element it stands in, and every piece of the name is.
    fonts = page.evaluate("""() => {
      const out = {name: [], rest: []};
      const root = document.querySelector('.notice .notice-text');
      const walk = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      for (let node = walk.nextNode(); node; node = walk.nextNode()) {
        if (!node.textContent.trim()) { continue; }
        const part = node.parentElement.closest('.notice-name')
          ? 'name' : 'rest';
        out[part].push([node.textContent.trim(),
          getComputedStyle(node.parentElement).fontFamily]);
      }
      return out;
    }""")
    page.close()
    assert found['text'] == line, found
    assert found['name'] == 'login PROOF-1 (RULE-1)', found
    assert found['nameFont'].startswith('"Courier New"'), found
    assert not found['restFont'].startswith('"Courier New"'), found
    assert ' '.join(text for text, _font in fonts['name']) == (
        'login PROOF-1 (RULE-1)'), fonts
    assert [text for text, font in fonts['name']
            if not font.startswith('"Courier New"')] == [], fonts
    assert 'tests/test_login.py:12' in ' '.join(
        text for text, _font in fonts['rest']), fonts
    assert [text for text, font in fonts['rest']
            if 'Courier' in font] == [], fonts
    assert found['kind'] == 'test comment to correct', found
    assert found['kindBorder'] == '1px', found


# purlin: purlin_report PROOF-291
def test_a_notice_fits_every_width_and_its_name_and_kind_measure_7_to_1(
        browser, tmp_path):
    for width in (1500, 1024, 390):
        for theme in ('dark', 'light'):
            payload = payload_named('regulated')
            login_reworded(payload)
            page = open_in_theme(browser, tmp_path / ('%d-%s' % (width, theme)),
                                 payload, theme)
            page.set_viewport_size({'width': width, 'height': 900})
            sideways = page.evaluate(
                'document.documentElement.scrollWidth'
                ' - document.documentElement.clientWidth')
            ratios = {item[0]: item[3] for item in every_text(page)
                      if item[0] in ('login', 'PROOF-1', '(RULE-1)',
                                     'test comment to correct')}
            page.close()
            assert sideways <= 0, (width, theme, sideways)
            assert len(ratios) == 4 and min(ratios.values()) >= 7, (
                width, theme, ratios)


# purlin: purlin_report PROOF-292
def test_a_notices_name_opens_the_rule_it_names(browser, tmp_path):
    payload = payload_named('regulated')
    login_reworded(payload)
    page = open_board(browser, tmp_path / 'by-name', payload)
    (found,) = page.evaluate(NOTICE_PARTS)
    assert found['link'] is True, found
    page.click('.notice-name')
    page.wait_for_selector('h1', timeout=10000)
    by_name = page.inner_text('.wrap')
    notices = len(page.query_selector_all('.notice'))
    page.close()
    page = open_board(browser, tmp_path / 'by-row', payload)
    open_rule(page, 'login', 'RULE-1')
    by_row = page.inner_text('.wrap')
    page.close()
    assert 'RULE-1' in by_name and 'specs/auth/login.md' in by_name, by_name
    assert by_name == by_row
    assert notices == 0


# purlin: purlin_report PROOF-293
def test_a_name_the_page_has_no_rule_for_is_not_a_link(browser, tmp_path):
    notices = notice_module()
    payload = payload_named('regulated')
    payload['dirty'] = False
    give_lines(payload, [
        notices.line('to_correct', 'nosuch PROOF-1',
                     'tests/test_login.py:13 names it, and no spec has it.',
                     notices.run('purlin:build'), feature='nosuch'),
        unread_proof_line('login')])
    page = open_board(browser, tmp_path, payload)
    found = page.evaluate(NOTICE_PARTS)
    # Neither name is a link of any kind: neither is inside one or holds
    # one, and nothing about either can be pressed.
    linked = page.evaluate("""() => {
      const marks = 'a, [href], [role="link"], [data-act], [tabindex], '
        + '[onclick], button';
      return [...document.querySelectorAll('.notice .notice-name')].map(
        name => [!!name.closest(marks), name.querySelectorAll(marks).length,
                 getComputedStyle(name).cursor]);
    }""")
    before = page.inner_text('.wrap')
    page.click('.notice-name')
    still = len(page.query_selector_all('.notice'))
    tables = len(page.query_selector_all('.tbl'))
    # Pressing either changes nothing on the board: no spec opens, and no
    # rule's screen.
    after_first = page.inner_text('.wrap')
    page.locator('.notice-name').nth(1).click()
    after_second = page.inner_text('.wrap')
    opened = len(page.query_selector_all('.rule, h1'))
    page.close()
    assert linked == [[False, 0, 'auto'], [False, 0, 'auto']], linked
    assert after_first == before and after_second == before
    assert opened == 0
    assert [(item['name'], item['link']) for item in found] == [
        ('nosuch PROOF-1', False), ('login', False)], found
    assert still == 2 and tables >= 1


# ---------------------------------------------------------------------------
# An AI proof: a graded rule, and a proof's models on its rule's screen
# ---------------------------------------------------------------------------

def reply_open(browser, tmp_path, change=None, **options):
    """The prompts sample's board with support_reply open."""
    page = open_sample(browser, tmp_path, 'prompts', change, **options)
    page.click('[data-act="feature"][data-feature="support_reply"]')
    return page


def open_reply_rule(page, rule_id, feature='support_reply'):
    """One rule's screen, from a board with its spec open."""
    page.click('.rule[data-feature="%s"][data-rule="%s"]' % (feature, rule_id))
    page.wait_for_selector('h1', timeout=10000)


# purlin: purlin_report PROOF-294
def test_a_graded_rule_counts_among_the_rules_that_pass(browser, tmp_path):
    payload = payload_named('prompts')
    assert payload['summary']['rules'] == 8
    assert [rule['id'] for feature in payload['features']
            for rule in feature['rules']
            if rule['cells']['passed']['word'] == 'graded'] == [
                'RULE-2', 'RULE-6']
    page = open_board(browser, tmp_path, payload)
    found = {label: count for label, count, _colour in boxes(page)}
    bands = page.eval_on_selector_all(
        '.group',
        r'els => els.map(e => e.innerText.replace(/\s+/g, " ").trim())')
    cells = count_cells(page)
    page.close()
    assert found['Passing'] == '5', found
    assert bands == ['▼ PROMPTS 1 spec 3 of 6 rules pass',
                     '▼ API 1 spec 2 of 2 rules pass'], bands
    assert cells['support_reply']['Tests'] == '3 of 6 · 2 failing', cells


# purlin: purlin_report PROOF-295
def test_a_graded_rules_badge_reads_graded_in_the_pass_tone(browser,
                                                            tmp_path):
    page = reply_open(browser, tmp_path)
    badges = row_badges(page, 'support_reply')
    colours = dict(page.eval_on_selector_all(
        '.rule .rp .pill',
        'els => els.map(e => [e.innerText.trim(), getComputedStyle(e).color])'))
    passing = resolved(page, '--state-pass')
    page.close()
    assert badges == {'RULE-1': 'PASSED', 'RULE-2': 'GRADED',
                      'RULE-3': 'FAILED', 'RULE-4': '', 'RULE-5': 'FAILED',
                      'RULE-6': 'GRADED'}, badges
    assert colours['GRADED'] == colours['PASSED'] == passing, colours


# purlin: purlin_report PROOF-296
def test_a_graded_rule_reads_graded_in_its_hovers_and_on_its_screen(browser,
                                                                    tmp_path):
    # The clock stands at the moment the sample was written, 2026-10-01
    # 10:42:13 UTC, 18 hours after its run of 2026-09-30 16:20.
    page = reply_open(browser, tmp_path, clock_at='2026-10-01T10:42:13Z')
    hover = hovers(page)['support_reply']['Tests']
    open_reply_rule(page, 'RULE-2')
    pills = texts(page, '.wrap .pill')
    (box,) = page.evaluate(PLATFORM_BOXES)
    page.close()
    assert hover == ('macOS · local · 18 hours old · 1 passed · 2 graded'
                     ' · 2 failed · 1 not run'), hover
    assert pills == ['GRADED', 'GRADED'], pills
    assert (box['os'], box['tone']) == ('Mac', 'pass'), box
    assert box['title'].startswith('macOS · graded · local · '), box


def lines_under(page):
    """Each box's label and every line under it."""
    return page.eval_on_selector_all(
        '.tile', "els => els.map(e => [e.querySelector('.tile-l')"
        ".textContent.trim(), Array.from(e.querySelectorAll('.tile-t'))"
        ".map(t => t.innerText.trim())])")


# purlin: purlin_report PROOF-297
def test_the_passing_box_says_how_many_rules_an_ai_graded(browser, tmp_path):
    payload = payload_named('prompts')
    assert payload['summary']['steps'] == {'passed': 5, 'graded': 2,
                                           'by_hand': 0}
    page = open_board(browser, tmp_path, payload)
    assert lines_under(page) == [
        ['No proof', []],
        ['Passing', ['8 RULES TOTAL', '2 GRADED BY AN AI']],
        ['Failing', []]]
    graded = page.query_selector_all('.tile-t')[1]
    label = page.query_selector_all('.tile')[1].query_selector('.tile-l')
    assert label.inner_text().strip() == 'PASSING'
    assert graded.evaluate(LOOK) == label.evaluate(LOOK)
    page.close()


# purlin: purlin_report PROOF-298
def test_no_graded_line_where_no_rule_is_graded(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['summary']['steps']['graded'] == 0
    page = open_board(browser, tmp_path, payload)
    found = dict(lines_under(page))
    page.close()
    assert found['Passing'] == ['11 RULES TOTAL'], found


# Each proof panel on the open rule's screen: its rows' labels in order, the
# lines of its `Models` row and how each is drawn, and its `Grader` row.
MODEL_ROWS = r"""() => Array.from(document.querySelectorAll('.proof .kv'))
  .map(list => {
    const labels = Array.from(list.querySelectorAll('dt')).map(
      dt => dt.textContent.trim());
    const row = label => { const dt = Array.from(list.querySelectorAll('dt'))
      .find(d => d.textContent.trim() === label);
      return dt ? dt.nextElementSibling : null; };
    const models = row('Models');
    const grader = row('Grader');
    return {labels: labels,
      lines: models ? Array.from(models.querySelectorAll('p')).map(
        p => p.innerText.trim().replace(/\s+/g, ' ')) : null,
      fonts: models ? Array.from(models.querySelectorAll('p:not(.run)')).map(
        p => getComputedStyle(p).fontFamily) : null,
      words: models ? Array.from(models.querySelectorAll('p:not(.run)')).map(
        p => [p.firstElementChild.textContent.trim(),
              getComputedStyle(p.firstElementChild).color]) : null,
      grader: grader ? grader.innerText.trim() : null};
  })"""


def models_of(browser, tmp_path, rule_id, feature='support_reply',
              change=None):
    """`MODEL_ROWS` for the one proof of a rule of the prompts sample, and
    the pass and fail tones as the page resolves them."""
    page = open_sample(browser, tmp_path, 'prompts', change)
    page.click('[data-act="feature"][data-feature="%s"]' % feature)
    open_reply_rule(page, rule_id, feature)
    (found,) = page.evaluate(MODEL_ROWS)
    found['tones'] = {name: resolved(page, '--state-' + name)
                      for name in ('pass', 'fail', 'warn')}
    page.close()
    return found


# purlin: purlin_report PROOF-299
def test_an_ai_proof_reads_one_line_per_model_and_the_run_that_failed(
        browser, tmp_path):
    proof = rule_of(payload_named('prompts'), 'support_reply',
                    'RULE-3')['proofs'][0]
    assert [[run['result'] for run in model['runs']]
            for model in proof['models']] == [['pass'] * 3,
                                              ['pass', 'fail', 'pass']]
    found = models_of(browser, tmp_path, 'RULE-3')
    assert found['labels'] == ['PROOF-3', 'Result', 'Models', 'Tests'], found
    assert found['lines'] == ['passed 3 of 3 on claude-opus-5-5',
                              'failed 2 of 3 on claude-sonnet-5-5',
                              '2 of 3 failed'], found
    assert [font.startswith('"Courier New"') for font in found['fonts']] == [
        True, True], found
    assert found['words'] == [['passed', found['tones']['pass']],
                              ['failed', found['tones']['fail']]], found


# purlin: purlin_report PROOF-300
def test_a_graded_proof_names_its_grader_and_its_reason_for_each_run(
        browser, tmp_path):
    found = models_of(browser, tmp_path, 'RULE-4')
    assert found['labels'] == ['PROOF-4', 'Result', 'Grader', 'Models',
                               'Tests'], found
    assert found['grader'] == 'claude-haiku-4-5-20251001', found
    assert found['lines'] == [
        'graded 3 of 3 on claude-opus-5-5',
        '1 of 3 graded The whole reply is in Spanish.',
        '2 of 3 graded It answers in Spanish.',
        '3 of 3 graded Spanish throughout, the greeting included.',
        'not run 0 of 3 on claude-sonnet-5-5',
        '1 of 3 not run The model gave no answer.'], found


# purlin: purlin_report PROOF-301
def test_runs_that_passed_ungraded_draw_no_line_and_a_plain_proof_no_row(
        browser, tmp_path):
    found = models_of(browser, tmp_path / 'ai', 'RULE-1')
    assert found['lines'] == ['passed 3 of 3 on claude-opus-5-5',
                              'passed 3 of 3 on claude-sonnet-5-5'], found
    assert found['labels'] == ['PROOF-1', 'Result', 'Models', 'Tests'], found
    plain = models_of(browser, tmp_path / 'plain', 'RULE-1', 'order_lookup')
    assert plain['labels'] == ['PROOF-1', 'Result', 'Tests'], plain
    assert (plain['lines'], plain['grader']) == (None, None), plain


# purlin: purlin_report PROOF-302
def test_a_models_count_is_out_of_the_runs_asked_now(browser, tmp_path):
    def five_asked(payload):
        proof = rule_of(payload, 'support_reply', 'RULE-1')['proofs'][0]
        assert (proof['runs'], [model['of'] for model in proof['models']]) == (
            3, [3, 3])
        proof['runs'] = 5
    found = models_of(browser, tmp_path, 'RULE-1', change=five_asked)
    assert found['lines'] == ['passed 3 of 5 on claude-opus-5-5',
                              'passed 3 of 5 on claude-sonnet-5-5'], found


# purlin: purlin_report PROOF-304
def test_a_model_not_reached_is_a_notice_like_any_other(browser, tmp_path):
    payload = payload_named('prompts')
    line = ('claude-sonnet-5-5: model not reached. The model gave no answer. '
            'Run purlin:test --all.')
    silent = [(model['model'], run) for model
              in rule_of(payload, 'support_reply', 'RULE-4')['proofs'][0][
                  'models']
              for run in model['runs'] if run['result'] == 'not run']
    assert silent == [('claude-sonnet-5-5', {
        'result': 'not run', 'why': 'The model gave no answer.'})], silent
    # The sample's warning is the one the payload's builder writes for the
    # sample's own rules, entry for entry.
    notices = notice_module()
    from purlin import states
    built = [notices.model_not_reached(model, why) for model, why
             in states.not_reached(payload['features'])]
    assert payload['warnings'] == built == [line], built
    assert payload['notices'] == notices.grouped(
        notices.entries(built, 'warn')), payload['notices']
    page = open_board(browser, tmp_path, payload)
    (found,) = page.evaluate(NOTICE_PARTS)
    # No link of any kind: the name is not inside one, holds none, and
    # nothing about it can be pressed or reached by the keyboard.
    linked = page.evaluate("""() => {
      const name = document.querySelector('.notice .notice-name');
      const marks = 'a, [href], [role="link"], [data-act], [tabindex], '
        + '[onclick], button';
      return [!!name.closest(marks), name.querySelectorAll(marks).length,
              getComputedStyle(name).cursor,
              getComputedStyle(name).textDecorationLine];
    }""")
    page.close()
    assert linked == [False, 0, 'auto', 'none'], linked
    assert found['text'] == line, found
    assert (found['name'], found['link']) == ('claude-sonnet-5-5', False), found
    assert found['nameFont'].startswith('"Courier New"'), found
    assert found['kind'] == 'model not reached', found
    assert found['kindBorder'] == '1px', found


# The label of each row of the open rule's first panel, as it is written and
# as it is drawn.
ROW_LABELS = """() => [...document.querySelector('.kv').children]
  .filter(node => node.tagName === 'DT')
  .map(dt => [dt.textContent.trim(), dt.innerText.trim()])"""


# purlin: purlin_report PROOF-305
def test_the_row_of_a_rules_passed_cell_is_labelled_tests(browser, tmp_path):
    graded = open_sample(browser, tmp_path / 'graded', 'prompts')
    open_rule(graded, 'support_reply', 'RULE-2')
    first = graded.evaluate(ROW_LABELS)
    word = graded.evaluate(PASSED_PILL)[0]
    graded.close()
    audited = open_sample(browser, tmp_path / 'audited', 'regulated')
    open_rule(audited, 'login', 'RULE-1')
    second = audited.evaluate(ROW_LABELS)
    audited.close()
    assert first == [['Tests', 'TESTS'], ['Spec', 'SPEC'],
                     ['Last run', 'LAST RUN']], first
    assert word == 'GRADED', word
    assert second == [['Tests', 'TESTS'], ['Strong', 'STRONG'],
                      ['Spec', 'SPEC'], ['Last run', 'LAST RUN']], second
