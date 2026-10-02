"""The board page: how it is built, and what it shows.

Two halves. The first reads the built file as text and holds it to the design
system: one token block, no colour written anywhere else, no shadow, no
gradient, no request to anything outside the file. The second opens
it in a headless browser over `file://` with a fixture payload beside it, one
fixture per process, and reads what a person would see.

The samples under `dev/fixtures/report/` are payloads at schema 16, written on
the branch `main` at the commit `a1b2c3d` and stamped `2026-10-01T10:42:13Z`:
solo, which no audit has read and no one has signed, with one rule failing
its tests; team, with an audit, one spec to repair, which writes a proof
number twice, and one spec whose scope names a file not written yet;
regulated, signed as `0.1.0` four commits ago, with a rule whose audit found
a gap and a planted bug its test missed, a rule no audit has run on, a hand
check no sign-off has noted, a rule that passed on one system and failed on
another, and a rule of a remote anchor with no test.

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
# proof lines, `Passing`, and `Strong` where the audit read the project.
TILES = {'solo': 2, 'team': 3, 'regulated': 3}


def rule_ids(page):
    return texts(page, '.rule .rid')


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


# purlin: purlin_report PROOF-3
def test_no_colour_is_written_as_hex_outside_the_token_block():
    inside, outside = token_block(build_page())
    assert re.search(r'--canvas\s*:', inside)
    assert re.findall(r'#[0-9a-fA-F]{3,8}\b', outside) == []


# purlin: purlin_report PROOF-4
def test_no_shadow_and_no_gradient(page_text):
    _inside, outside = token_block(page_text)
    assert 'box-shadow' not in outside
    assert 'gradient' not in page_text


# purlin: purlin_report PROOF-5
def test_no_request_to_anything_outside_the_page(page_text):
    """The page opens from a disk with no network behind it."""
    # Nothing is fetched: no stylesheet link, no remote script or image, no
    # request of any kind. The page is the whole page.
    assert '<link' not in page_text
    assert '@import' not in page_text
    assert 'fetch(' not in page_text
    assert not re.search(r'(?:src|href)\s*=\s*"https?:', page_text)


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
def test_affordances_are_unicode_glyphs_not_an_icon_set(page_text):
    """The system ships no icon set, so the page draws none, and the glyphs
    it draws are the six the design allows."""
    found = glyphs_in(page_text)
    assert {u'\u25b6', u'\u25bc', u'\u25d0', u'\u25d1'} <= found, found
    assert found - set(ALLOWED_GLYPHS) == set(), found
    assert page_text.count('<svg') == 0
    assert 'icon' not in page_text.lower()


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
    assert len(page.query_selector_all('.tile')) == TILES[process]
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
    assert payload['summary']['steps'] == {'passed': 7, 'by_hand': 1}
    assert payload['summary']['audit']['strong'] == 3
    page = open_board(browser, tmp_path, payload)
    found = boxes(page)
    assert [(label, count) for label, count, _ in found] == [
        ('No proof', '0'), ('Passing', '7'), ('Strong', '3')], found
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
    assert payload['summary']['steps'] == {'passed': 10, 'by_hand': 1}
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
    page.close()


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
    page = open_board(browser, tmp_path, payload_named('regulated'))
    login = hovers(page)['login']
    page.close()
    assert login['Spec'] == 'specs/auth/login.md'
    assert login['Proofs'] == 'every proof has a test'
    # Newest run first: Windows ran after Linux, and one of its four rules
    # failed there.
    tests = login['Tests'].split('\n')
    assert len(tests) == 2, tests
    assert tests[0].startswith('Windows · ci · ')
    assert tests[0].endswith('· 3 passed · 1 failed')
    assert tests[1].startswith('Linux/Unix · ci · ')
    assert tests[1].endswith('· 4 passed')
    strong = login['Strong'].split('\n')
    assert len(strong) == 1, strong
    assert strong[0].startswith('audit · ci · ')
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
    assert 'login' not in narrow.inner_text('.tbl')
    narrow.close()


# purlin: purlin_report PROOF-10
def test_a_feature_row_expands_to_its_rules(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert rule_ids(page) == []
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4']
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
    page.close()
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
    # The row's own word, not its label: the label `Passed` is drawn in capitals too.
    assert rows['Passed'].startswith('PASSED'), rows
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
        'This data was written for schema 3 and this page reads schema 16. '
        'Run purlin:status to write it again.']
    assert page.query_selector_all('.tile') == []
    assert page.query_selector_all('.fact') == []
    assert page.query_selector_all('.tbl') == []
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
    page.close()


# purlin: purlin_report PROOF-198
def test_each_warning_is_a_notice_after_the_working_tree_one(browser,
                                                             tmp_path):
    payload = payload_named('regulated')
    [warning] = payload['warnings']
    page = open_board(browser, tmp_path, payload)
    assert texts(page, '.notice-text') == [
        'The working tree has uncommitted changes, so what is on this board '
        'is not what a commit would carry.', warning]
    lowest_notice = max(box['y'] + box['height'] for box in (
        notice.bounding_box() for notice in page.query_selector_all('.notice')))
    first_box = page.query_selector('.tile').bounding_box()
    page.close()
    assert lowest_notice <= first_box['y']


# purlin: purlin_report PROOF-22
def test_a_rule_screen_draws_no_notice(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['dirty'] is True
    page = open_board(browser, tmp_path, payload)
    assert len(page.query_selector_all('.notice')) == 2
    open_rule(page, 'login', 'RULE-1')
    assert 'RULE-1' in page.inner_text('h1')
    assert len(page.query_selector_all('.notice')) == 0
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
                explanation=[EXPLANATION], breaks={})
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
    given_audit(payload, 'invoice', 'RULE-2', breaks={'PROOF-2': {
        'file': 'src/billing/invoice.py', 'line': 12,
        'before': '    return total\n', 'after': '    return 0\n',
        'result': 'survived', 'why': '', 'break_key': 'b' * 64}})


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
        rule_of(payload, 'invoice', 'RULE-2')['audit']['breaks']['PROOF-2'][
            'result'] = 'caught'
    page = open_sample(browser, tmp_path, 'regulated', caught)
    open_rule(page, 'invoice', 'RULE-2')
    lines, bugs = panel_lines(page, 'Audit'), page.evaluate(BUGS)
    page.close()
    assert lines[0] == 'Weak.', lines
    assert bugs == [], bugs
    assert not [line for line in lines if 'planted' in line], lines


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
        'breaks': {}, 'model': 'claude-opus-5-5',
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
    assert lines[0].startswith('Out of date:'), lines
    assert lines[1] == 'Strong. It found nothing.', lines


# purlin: purlin_report PROOF-64
def test_a_rule_with_no_proof_reads_its_reason(browser, tmp_path):
    solo = open_board(browser, tmp_path, payload_named('solo'))
    open_rule(solo, 'login', 'RULE-3')
    passed = solo.evaluate(KV_ROWS)['Passed']
    assert passed.startswith('NO TEST') and 'no proof written' in passed
    assert 'No proof written.' in solo.inner_text('.wrap')
    solo.close()


# purlin: purlin_report PROOF-135
def test_a_rule_out_of_date_reads_what_changed(browser, tmp_path):
    reg = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(reg, 'export', 'RULE-1')
    passed = reg.evaluate(KV_ROWS)['Passed']
    assert passed.startswith('OUT OF DATE'), passed
    assert 'code changed since 9f8e7d6' in passed
    reg.close()


# The pill of the open rule's passed row: its text and the colour it is in.
PASSED_PILL = """() => {
  const row = Array.from(document.querySelectorAll('.kv dt')).find(
    dt => dt.textContent.trim() === 'Passed');
  const pill = row.nextElementSibling.querySelector('.pill');
  return [pill.innerText.trim(), getComputedStyle(pill).color];
}"""


# purlin: purlin_report PROOF-244
def test_a_hand_check_no_sign_off_noted_reads_checked_at_sign_off_as_passed(
        browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="invoice"]')
    badges = row_badges(page, 'invoice')
    page.click('.rule[data-feature="invoice"][data-rule="RULE-3"]')
    passed = page.evaluate(KV_ROWS)['Passed']
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
    passed = reg.evaluate(KV_ROWS)['Passed']
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
    found, statuses = words_shown(browser, tmp_path, payload, AUDIT_WORDS)
    assert found == [], found
    assert len(statuses) == 5, statuses
    assert set(statuses) <= set(STATUSES), statuses


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
# WCAG contrast ratio of the two. Every text is measured, whatever its colour.
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
    let ink = parse(style.color);
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
    for process in PROCESSES:
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
    """The three samples, each on the board with its first spec open and
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
    """The three samples, each on the board with its first spec open and
    then on the screen of each of that spec's rules; every text node's
    computed colour against the ground under it, state colours and the
    accent included."""
    checked, low, tones, measured = _every_text_in(browser, tmp_path, 'light')
    assert low == [], low
    assert checked > 300, checked
    assert tones & measured == tones, (tones, measured)


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
    assert ('The working tree has uncommitted changes, so what is on this '
            'board is not what a commit would carry.') in texts(
                page, '.notice-text')
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
    page.close()
    assert below
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
    row = page.evaluate(CELL_ROW, 'Passed')
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
    row = page.evaluate(CELL_ROW, 'Passed')
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
    heads = head_labels(page)
    page.close()
    assert list(found) == ['Tests', 'Sign-off'], found
    assert found['Sign-off']['word'] == 'not signed'
    assert found['Sign-off']['color'] == border == plain
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
        'notes': [], 'explanation': [], 'breaks': {}, 'model': 'unknown',
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
    page = open_sample(browser, tmp_path, 'team')
    found = hovers(page)
    page.close()
    lines = found['checkout_design']['Strong'].split('\n')
    assert len(lines) == 2, lines
    assert lines[0] == NO_ANCHOR_BUG, lines
    assert lines[1].startswith('audit · local · '), lines
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

