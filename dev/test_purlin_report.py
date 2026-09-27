"""The board page: how it is built, and what it shows.

Two halves. The first reads the built file as text and holds it to the design
system: one token block, no colour written anywhere else, no shadow, no
gradient, no emoji, no request to anything outside the file. The second opens
it in a headless browser over `file://` with a fixture payload beside it, one
fixture per process, and reads what a person would see.

The fixtures under `dev/fixtures/report/` are payloads at schema 7, one for
each of the three processes: solo at the `passed` gate with no record at all,
team at `strong` with strength and one rule the AI audit could not settle,
regulated at `signed` with signatures, a stale rule, a held rule, a rule no
audit has run on, a rule that passed on one platform and failed on another,
and a design anchor.

    python3 -m pytest dev/test_purlin_report.py -q
"""

import base64
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

# A 1x1 image, so the design file a spec names resolves beside the page and
# the thumbnail is a real load rather than a broken one.
PIXEL = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmM'
    'IQAAAABJRU5ErkJggg==')


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


# The levels the board's tiles count, lowest first. A payload counts a rule
# once, in the highest bucket it reached; a tile asks how many rules got at
# least that far, so it adds that bucket to every bucket above it.
LEVELS = ('passed', 'strong', 'signed')


def reached(counted, name):
    """How many rules a payload's counts put at this level or above it."""
    if name not in LEVELS:
        return counted.get(name, 0)
    return sum(counted.get(above, 0)
               for above in LEVELS[LEVELS.index(name):])


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


def stamp_ago(seconds):
    """An ISO stamp that many seconds old, as a payload carries it."""
    when = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(seconds=seconds))
    return when.strftime('%Y-%m-%dT%H:%M:%SZ')


def open_board(browser, tmp_path, payload, viewport=None, clock_at=None):
    """The page, opened over file:// with this payload beside it.

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
    designs = os.path.join(root, 'designs', 'checkout')
    os.makedirs(designs, exist_ok=True)
    with open(os.path.join(designs, 'cart.png'), 'wb') as handle:
        handle.write(PIXEL)
    page = browser.new_page(viewport=viewport or {'width': 1440,
                                                  'height': 1000})
    if clock_at is not None:
        page.clock.install(time=clock_at)
    page.goto('file://' + os.path.join(root, 'purlin-report.html'))
    page.wait_for_selector('.topbar', timeout=10000)
    return page


def texts(page, selector):
    return page.eval_on_selector_all(
        selector, 'els => els.map(e => e.textContent.trim())')


def feature_names(page):
    return texts(page, '.tr .name .n')


def chip_labels(page):
    """The filter pills' labels, without the count each one carries."""
    return page.eval_on_selector_all(
        '.chip', 'els => els.map(e => e.firstChild.textContent.trim())')


def chip_counts(page):
    """Each filter pill's label and the count it carries, as an integer."""
    return dict(zip(chip_labels(page), [
        int(value) for value in texts(page, '.chip b')]))


def chip_for(label):
    return '.chip[data-filter="%s"]' % {
        'To review': 'to-review', 'To sign': 'to-sign'}.get(label,
                                                            label.lower())


def head_labels(page):
    """The spec table's column headings, in the order they are drawn."""
    return texts(page, '.th > div')


# How many tiles the strip carries at each gate: four buckets always, the
# strong bucket at `strong`, the signed bucket at `signed`.
TILES = {'solo': 4, 'team': 5, 'regulated': 6}


def rule_ids(page):
    return texts(page, '.rule .rid')


def list_cells(page):
    """Each row of the Review or Sign tab as its six cells, heading aside.

    Review reads feature, id, text, bar, the strong cell's word and why; Sign
    reads feature, id, text, bar, the signed cell's word and the command.
    """
    return page.eval_on_selector_all(
        '.rev:not(.th)',
        'els => els.map(e => Array.from(e.children)'
        '.map(c => c.textContent.trim()))')


def flag_cards(page):
    """The flag cards beside the tiles, as `{label: count}`."""
    return dict(zip(texts(page, '.flag-l'), texts(page, '.flag-v')))


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
  const head = Array.from(document.querySelectorAll('.th > div'))
    .map(d => d.textContent.trim());
  return els.map(e => {
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


# ---------------------------------------------------------------------------
# The built file
# ---------------------------------------------------------------------------

@pytest.mark.proof("purlin_report", "PROOF-1", "RULE-1")
def test_the_build_is_reproducible():
    """Two builds of the same parts give the same bytes."""
    first = build_page()
    second = build_page()
    assert first == second


@pytest.mark.proof("purlin_report", "PROOF-2", "RULE-2")
def test_the_page_is_one_file_under_the_line_budget(page_text):
    assert len(page_text.splitlines()) <= 1200
    assert os.path.isfile(os.path.join(ROOT, 'purlin-report.html'))
    assert read(os.path.join(ROOT, 'purlin-report.html')) == page_text


@pytest.mark.proof("purlin_report", "PROOF-3", "RULE-3")
def test_every_colour_is_a_token(page_text):
    """The only place a colour is written is the inlined token block."""
    inside, outside = token_block(page_text)
    assert '--canvas' in inside
    written = [match for match in re.findall(r'#[0-9a-fA-F]{3,8}\b', outside)
               if not match.lower().startswith('#purlin')]
    assert written == [], written


@pytest.mark.proof("purlin_report", "PROOF-4", "RULE-4")
@pytest.mark.proof("purlin_report", "PROOF-5", "RULE-5")
def test_no_shadow_no_gradient_no_emoji_and_no_outside_request(page_text):
    """The page opens from a disk with no network behind it."""
    inside, outside = token_block(page_text)
    assert 'box-shadow' not in outside
    assert 'gradient' not in page_text
    assert not re.search(u'[\U0001F300-\U0001FAFF☀-➿]', page_text)
    # Nothing is fetched: no stylesheet link, no remote script or image, no
    # request of any kind. The page is the whole page.
    assert '<link' not in page_text
    assert '@import' not in page_text
    assert 'fetch(' not in page_text
    assert not re.search(r'(?:src|href)\s*=\s*"https?:', page_text)


@pytest.mark.proof("purlin_report", "PROOF-6", "RULE-6")
def test_affordances_are_unicode_glyphs_not_an_icon_set(page_text):
    """The system ships no icon set, so the page draws none."""
    for glyph in (u'▶', u'▼', u'←'):
        assert glyph in page_text
    assert page_text.count('<svg') == 0
    assert 'icon' not in page_text.lower()


# ---------------------------------------------------------------------------
# What a person sees
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('process', PROCESSES)
@pytest.mark.proof("purlin_report", "PROOF-7", "RULE-7", tier="e2e")
def test_the_board_renders_for_each_process(browser, tmp_path, process):
    payload = payload_named(process)
    summary = payload['summary']
    page = open_board(browser, tmp_path, payload)
    heading = page.inner_text('h1')
    assert '%d of %d rules pass their tests' % (
        reached(summary, 'passed'), summary['rules']) in heading
    assert '%d failing' % summary['failing'] in heading
    assert '%d partial' % summary['partial'] in heading
    assert '%d untested' % summary['untested'] in heading
    # The second line is `board.headline`, which the status table's summary
    # opens on: the same sentence, down to the full stop.
    assert '%d of %d rules meet the gate %s.' % (
        summary['met'], summary['rules'],
        payload['gate']['gate']) in page.inner_text('.ledger')
    assert len(page.query_selector_all('.tile')) == TILES[process]
    assert 'gate: ' + payload['gate']['gate'] in page.inner_text('.topbar')
    assert 'Data:' in page.inner_text('.topbar')
    assert set(feature_names(page)) == set(
        f['name'] for f in payload['features'])
    page.close()


BASE_COLUMNS = ['Spec', 'Rules', 'Proofs', 'Tests']

# The three the board dropped: every when, who and platform detail is in a
# hover now, which is what let the columns fit a 1024-wide window.
GONE_COLUMNS = ('Spec status', 'Strength', 'Last run')


@pytest.mark.proof("purlin_report", "PROOF-9", "RULE-9", tier="e2e")
def test_the_columns_scale_with_the_gate(browser, tmp_path):
    """A gate asks for what it asks for, and the board asks no more."""
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    assert head_labels(solo) == BASE_COLUMNS
    assert solo.query_selector_all('table.grid') == []
    solo.close()

    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert head_labels(team) == BASE_COLUMNS + ['Strong']
    team.close()

    reg = open_board(browser, tmp_path / 'reg', payload_named('regulated'))
    assert head_labels(reg) == BASE_COLUMNS + ['Strong', 'Signable', 'Signed']
    for gone in GONE_COLUMNS:
        assert gone not in head_labels(reg)
    reg.close()


@pytest.mark.proof("purlin_report", "PROOF-32", "RULE-31", tier="e2e")
def test_the_rule_screen_says_what_each_platform_found(browser, tmp_path):
    """A rule can pass on one operating system and fail on another.

    The board used to spend a whole column on three boxes and a source word.
    The boxes are the rule's business, so they live on its screen, drawn from
    the platforms its passed cell carries rather than from the records.
    """
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert page.query_selector_all('.tr .os') == []

    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-4"]')
    boxes = page.evaluate(PLATFORM_BOXES)
    assert [b['os'] for b in boxes] == ['lin', 'win']
    assert [b['tone'] for b in boxes] == ['pass', 'fail']
    assert boxes[0]['colour'] == page.evaluate(RESOLVE_TOKEN, '--state-pass')
    assert boxes[1]['colour'] == page.evaluate(RESOLVE_TOKEN, '--state-fail')
    assert boxes[1]['title'].startswith('windows \u00b7 failed \u00b7 ci \u00b7 ')
    assert 'PARTIAL' in page.inner_text('.kv')
    last = page.inner_text('.kv').splitlines()
    assert any(line.startswith('ci \u00b7 ') and 'old' in line for line in last)

    # The boxes come from the rule's own passed cell: invoice ran on a
    # different pair of systems, and its manual rule ran on none.
    page.click('[data-act="close"]')
    page.click('[data-act="feature"][data-feature="invoice"]')
    page.click('.rule[data-feature="invoice"][data-rule="RULE-1"]')
    assert [b['os'] for b in page.evaluate(PLATFORM_BOXES)] == ['lin', 'mac']
    page.click('[data-act="close"]')
    page.click('.rule[data-feature="invoice"][data-rule="RULE-3"]')
    assert page.evaluate(PLATFORM_BOXES) == []
    page.close()


@pytest.mark.parametrize('process', PROCESSES)
@pytest.mark.proof("purlin_report", "PROOF-12", "RULE-12", tier="e2e")
def test_both_themes_render_through_the_tokens(browser, tmp_path, process):
    page = open_board(browser, tmp_path, payload_named(process))
    dark = page.evaluate(
        'getComputedStyle(document.body).backgroundColor')
    dark_ink = page.evaluate('getComputedStyle(document.body).color')
    dark_logo = page.get_attribute('#brand-mark', 'src')
    assert page.get_attribute('html', 'data-theme') == 'dark'

    page.click('[data-act="theme"]')
    assert page.get_attribute('html', 'data-theme') == 'light'
    light = page.evaluate('getComputedStyle(document.body).backgroundColor')
    light_ink = page.evaluate('getComputedStyle(document.body).color')
    assert light != dark and light_ink != dark_ink
    assert page.get_attribute('#brand-mark', 'src') != dark_logo
    assert len(page.query_selector_all('.tile')) == TILES[process]

    page.click('[data-act="theme"]')
    assert page.get_attribute('html', 'data-theme') == 'dark'
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


@pytest.mark.proof("purlin_report", "PROOF-30", "RULE-12", tier="e2e")
def test_the_board_sits_on_the_brand_navy(browser, tmp_path, page_text):
    """No surface override, so the ground is the brand's own navy."""
    assert 'data-surface' not in page_text
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert page.get_attribute('html', 'data-surface') is None
    ground = page.evaluate('getComputedStyle(document.body).backgroundColor')
    assert ground == page.evaluate(RESOLVE_TOKEN, '--purlin-navy-800')
    page.close()


BUCKETS = ('untested', 'failing', 'partial', 'passed', 'strong',
           'signed')


@pytest.mark.proof("purlin_report", "PROOF-8", "RULE-8", tier="e2e")
def test_the_tiles_scale_with_the_gate(browser, tmp_path):
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    assert texts(solo, '.tile-l') == ['Untested', 'Failing', 'Partial',
                                      'Passing']
    assert solo.query_selector_all('.flag') == []
    assert solo.eval_on_selector(
        '.tile-l', 'el => getComputedStyle(el).textTransform') == 'uppercase'
    solo.close()

    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert texts(team, '.tile-l') == ['Untested', 'Failing', 'Partial',
                                      'Passing', 'Strong']
    assert team.query_selector_all('.flag') == []
    team.close()

    payload = payload_named('regulated')
    page = open_board(browser, tmp_path / 'reg', payload)
    assert texts(page, '.tile-l') == ['Untested', 'Failing', 'Partial',
                                      'Passing', 'Strong', 'Signed']
    # The three level tiles are cumulative: the regulated fixture's one signed
    # rule is counted again under `Strong` and again under `Passing`. The
    # three below them count their own bucket alone.
    assert texts(page, '.tile-v') == [str(reached(payload['summary'], name))
                                      for name in BUCKETS]
    assert texts(page, '.tile-v') == ['1', '0', '1', '8', '2', '1']
    assert flag_cards(page) == {'To sign': str(payload['summary']['signable']),
                                'Stale': str(payload['summary']['stale'])}
    page.close()


# Every count cell of every spec row, keyed by the spec name, as the text a
# person reads rather than the markup under it.
COUNT_CELLS = r"""els => {
  const head = Array.from(document.querySelectorAll('.th > div'))
    .map(d => d.textContent.trim());
  return els.map(e => {
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


@pytest.mark.proof("purlin_report", "PROOF-40", "RULE-9", tier="e2e")
def test_every_count_carries_the_word_it_counts(browser, tmp_path):
    """`24 \u00b7 0 \u00b7 0` left the reader to work out which number was which."""
    payload = payload_named('regulated')
    payload['features'][0]['rules'][1]['cells']['passed']['word'] = 'failed'
    page = open_board(browser, tmp_path / 'reg', payload)
    cells = count_cells(page)
    # The first part is drawn even at zero, and a later part only above it.
    assert cells['login']['Tests'] == (
        '2 of 4 \u00b7 1 partial \u00b7 1 failing')
    # One of export's two rules is behind changed code: it passed nothing
    # and failed nothing, so the share alone reads it and `Untested` counts it.
    assert cells['export']['Tests'] == '1 of 2'
    assert cells['login']['Proofs'] == '5'
    # invoice's third proof is `@manual`, which declares that no test is
    # written for it, so the rollup counts no gap and the cell reads the
    # total alone.
    assert cells['invoice']['Proofs'] == '3'
    assert cells['login']['Strong'] == '2 of 4 \u00b7 86%'
    assert cells['checkout_design']['Strong'] == '0 of 1 \u00b7 90%'
    assert cells['login']['Signed'] == '1 of 4'
    assert cells['invoice']['Signed'] == '0 of 3'
    page.close()

    # The team board is where a proof has no test at all, and the cell names
    # the gap in the warn tone beside the total.
    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert count_cells(team)['invoice']['Proofs'] == (
        '2 \u00b7 1 without a test')
    team.close()


@pytest.mark.proof("purlin_report", "PROOF-44", "RULE-37", tier="e2e")
def test_every_cell_of_a_spec_row_carries_its_hover(browser, tmp_path):
    """The columns the board dropped became the hovers the cells carry."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    rows = hovers(page)
    assert rows['login']['Spec'] == 'specs/auth/login.md'
    assert rows['login']['Proofs'] == 'every proof has a tagged test'
    assert rows['invoice']['Proofs'] == 'every proof has a tagged test'

    # Newest run first: windows ran after linux, and one of its four rules
    # failed there.
    tests = rows['login']['Tests'].split('\n')
    assert len(tests) == 2, tests
    assert tests[0].startswith('windows \u00b7 ci \u00b7 ')
    assert tests[0].endswith('\u00b7 3 passed \u00b7 1 failed')
    assert tests[1].startswith('linux \u00b7 ci \u00b7 ')
    assert tests[1].endswith('\u00b7 4 passed')

    strong = rows['login']['Strong'].split('\n')
    assert strong[0].startswith('audit \u00b7 ci \u00b7 ')
    assert strong[1] == 'minimum strength 80%'

    assert rows['login']['Signed'].split('\n') == [
        'jane@acme.com \u00b7 2026-09-12', 'sam@acme.com \u00b7 2026-09-08',
        '1 stale']
    assert rows['invoice']['Signed'] == 'Nobody has signed a rule here.'
    page.close()

    # The gap the regulated board has nowhere: the team board's invoice
    # writes a proof no tagged test runs, and the hover names it.
    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert hovers(team)['invoice']['Proofs'] == (
        'no tagged test \u00b7 PROOF-2')
    team.close()


@pytest.mark.proof("purlin_report", "PROOF-47", "RULE-9", tier="e2e")
@pytest.mark.proof("purlin_report", "PROOF-48", "RULE-37", tier="e2e")
def test_the_signable_column_counts_the_rules_a_signer_can_act_on(
        browser, tmp_path):
    """Cleared its bar, needs a signature, and none counts for it yet."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    cells = count_cells(page)
    assert cells['login']['Signable'] == '1 of 4'
    assert cells['invoice']['Signable'] == '0 of 3'
    assert cells['checkout_design']['Signable'] == '0 of 1'
    rows = hovers(page)
    assert rows['login']['Signable'] == 'to sign \u00b7 RULE-2'
    assert rows['invoice']['Signable'] == (
        'no rule here is waiting for a signature')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-49", "RULE-32", tier="e2e")
def test_the_to_sign_card_counts_the_rules_waiting_for_a_signature(browser,
                                                                   tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert flag_cards(page) == {'To sign': '1', 'Stale': '1'}
    titles = page.eval_on_selector_all(
        '.flag', 'els => els.map(e => e.getAttribute("title"))')
    assert titles[0] == 'login \u00b7 1'
    page.close()

    payload = payload_named('regulated')
    payload['summary']['signable'] = 0
    payload['sign_list'] = []
    none = open_board(browser, tmp_path / 'none', payload)
    assert none.eval_on_selector_all(
        '.flag', 'els => els.map(e => e.getAttribute("title"))')[0] == (
        'No rule is waiting for a signature.')
    assert 'on' not in none.get_attribute('.flag', 'class').split()
    none.close()


@pytest.mark.proof("purlin_report", "PROOF-45", "RULE-37", tier="e2e")
def test_every_tile_carries_its_hover(browser, tmp_path):
    """A tile says for the project what its column says for one spec."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    titles = page.eval_on_selector_all(
        '.tile', 'els => els.map(e => e.getAttribute("title"))')
    assert len(titles) == 6
    for title in titles[:3]:
        assert '\n' not in title and title.endswith('.'), title
    assert titles[3].split('\n')[0].startswith('windows \u00b7 ci \u00b7 ')
    assert titles[4].split('\n')[0].startswith('audit \u00b7 ci \u00b7 ')
    assert titles[5].split('\n')[0] == 'jane@acme.com \u00b7 2026-09-12'
    page.close()


# The band over each category: its name, how many specs it holds, and how many
# of their rules pass their tests.
@pytest.mark.proof("purlin_report", "PROOF-43", "RULE-36", tier="e2e")
def test_the_group_band_says_what_its_numbers_are(browser, tmp_path):
    """`AUTH (1) 3 of 4` named neither number."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    bands = page.eval_on_selector_all(
        '.group',
        r'els => els.map(e => e.innerText.replace(/\s+/g, " ").trim())')
    assert bands == ['\u25bc AUTH \u00b7 1 spec \u00b7 3 of 4 pass',
                     '\u25bc BILLING \u00b7 2 specs \u00b7 4 of 5 pass',
                     '\u25bc _ANCHORS \u00b7 1 spec \u00b7 1 of 1 pass']
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-10", "RULE-10", tier="e2e")
def test_a_feature_row_expands_to_its_rules(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert rule_ids(page) == []
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4']
    assert 'SIGNED' in page.inner_text('.rule')
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == []
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-11", "RULE-11", tier="e2e")
def test_a_design_anchor_row_shows_its_thumbnail(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    thumbs = page.query_selector_all('.tr img.thumb')
    assert len(thumbs) == 1
    assert thumbs[0].get_attribute('src') == 'designs/checkout/cart.png'
    assert page.evaluate(
        'document.querySelector(".tr img.thumb").naturalWidth') == 1
    page.close()


FILTER_CASES = [
    ('untested', ['export'], []),
    ('failing', [], []),
    ('partial', ['login'], ['RULE-4']),
    # `weak` is the audit's own two words: measured and not proved, or not
    # measured yet. The three words that wait for a person are `to-review`.
    ('weak', ['login', 'invoice', 'export'], ['RULE-4']),  # 5 rules
    ('to-review', ['login', 'invoice', 'checkout_design'], ['RULE-3']),
    ('to-sign', ['login'], ['RULE-2']),
    ('stale', ['login'], ['RULE-2']),
]


@pytest.mark.parametrize('filter_id,features,login_rules', FILTER_CASES)
@pytest.mark.proof("purlin_report", "PROOF-13", "RULE-13", tier="e2e")
def test_each_filter_narrows_the_board(browser, tmp_path, filter_id,
                                       features, login_rules):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-filter="' + filter_id + '"]')
    assert page.get_attribute('[data-filter="' + filter_id + '"]',
                              'aria-pressed') == 'true'
    assert feature_names(page) == features
    if login_rules:
        page.click('[data-act="feature"][data-feature="login"]')
        assert rule_ids(page) == login_rules
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-14", "RULE-14", tier="e2e")
def test_filters_compose_and_clear(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-filter="stale"]')
    page.click('[data-filter="untested"]')
    assert feature_names(page) == []
    assert 'No rule matches every filter you set.' in page.inner_text('.empty')
    page.click('[data-filter="stale"]')
    page.click('[data-filter="untested"]')
    assert len(feature_names(page)) == 4
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-35", "RULE-13", tier="e2e")
def test_a_filter_above_the_gate_is_not_offered(browser, tmp_path):
    """A project at `passed` is never asked about strength or signatures."""
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    assert chip_labels(solo) == ['Untested', 'Failing', 'Partial']
    solo.close()

    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert chip_labels(team) == ['Untested', 'Failing', 'Partial', 'Weak',
                                 'To review']
    team.close()

    reg = open_board(browser, tmp_path / 'reg', payload_named('regulated'))
    assert chip_labels(reg) == ['Untested', 'Failing', 'Partial', 'Weak',
                                'To review', 'To sign', 'Stale']
    assert chip_counts(reg) == {'Untested': 1, 'Failing': 0, 'Partial': 1,
                                'Weak': 5, 'To review': 3, 'To sign': 1,
                                'Stale': 1}
    reg.close()


@pytest.mark.parametrize('process', PROCESSES)
@pytest.mark.proof("purlin_report", "PROOF-46", "RULE-13", tier="e2e")
def test_a_filter_pill_counts_what_it_leaves(browser, tmp_path, process):
    """A pill that said nothing left the reader to press it to find out.

    The number on the pill is the number of rules it leaves, so it and the
    tile it mirrors state the same thing before anything is pressed.
    """
    payload = payload_named(process)
    page = open_board(browser, tmp_path, payload)
    for name in feature_names(page):
        page.click('[data-act="feature"][data-feature="%s"]' % name)
    tiles = dict(zip(texts(page, '.tile-l'), texts(page, '.tile-v')))
    for label, count in chip_counts(page).items():
        page.click(chip_for(label))
        assert len(page.query_selector_all('.rule')) == count, label
        page.click(chip_for(label))
        if label in ('Untested', 'Failing', 'Partial'):
            assert tiles[label] == str(count), label
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-15", "RULE-15", tier="e2e")
def test_the_rule_screen_shows_proof_test_and_evidence(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    body = page.inner_text('.wrap')
    assert 'RULE-1' in page.inner_text('h1')
    assert 'A person signs in with an email address and a password.' in body
    assert 'PROOF-1' in body
    assert 'tests/test_login.py :: test_sign_in' in body
    assert 'PASSED' in body and 'STRONG' in body and 'SIGNED' in body
    # The signer is named once: the cell's own `by <signer>` reason would
    # have said it again beside the date.
    assert 'SIGNED jane@acme.com \u00b7 2026-09-12' in page.eval_on_selector_all(
        '.kv dd', r'els => els.map(e => e.innerText.trim().replace(/\s+/g, " "))')
    assert 'Test strength 86%, against a minimum of 80%.' in body
    assert 'The AI audit settled the question.' in body
    page.click('[data-act="close"]')
    page.click('.rule[data-rule="RULE-3"]')
    held = page.inner_text('.wrap')
    assert 'PROOF-3' in held
    assert 'held by sam@acme.com: the lock expiry is never read' in held
    # No check name reaches the screen: the audit's own sentence is what
    # shows.
    assert 'Free checks' not in held
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


@pytest.mark.proof("purlin_report", "PROOF-53", "RULE-15", tier="e2e")
def test_the_rule_screen_names_the_bar_and_where_it_came_from(browser,
                                                              tmp_path):
    """A rule has a bar, from its own tag or from the project's gate."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    rows = page.evaluate(KV_ROWS)
    # The whole row set, so a row the model dropped cannot come back.
    assert list(rows) == ['Spec status', 'Passed', 'Strong', 'Signed', 'Bar',
                          'Origin', 'Spec', 'Last run', 'Signatures']
    assert rows['Bar'] == 'strong from the tag'

    page.click('[data-act="close"]')
    page.click('[data-act="feature"][data-feature="export"]')
    page.click('.rule[data-feature="export"][data-rule="RULE-1"]')
    assert page.evaluate(KV_ROWS)['Bar'] == 'strong from the gate'

    # Under `passed` no rule is audited and none is signed, so the bar is not
    # a question the board puts to the reader.
    page.close()
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    solo.click('[data-act="feature"][data-feature="login"]')
    solo.click('.rule[data-rule="RULE-1"]')
    assert 'Bar' not in solo.evaluate(KV_ROWS)
    solo.close()


@pytest.mark.proof("purlin_report", "PROOF-16", "RULE-16", tier="e2e")
def test_the_rule_screen_links_to_the_git_host(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    href = page.get_attribute('a[href*="specs/auth/login.md"]', 'href')
    assert href.startswith('https://github.com/acme/ledger/blob/')
    assert page.query_selector('a[href*="RULE-1.1a2b3c4d.jane-doe.json"]')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-16", "RULE-16", tier="e2e")
def test_a_rule_with_no_remote_has_no_links(browser, tmp_path):
    """The solo fixture names no remote, so paths stay plain text."""
    page = open_board(browser, tmp_path, payload_named('solo'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    assert page.query_selector_all('.wrap a') == []
    assert 'specs/auth/login.md' in page.inner_text('.wrap')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-17", "RULE-17", tier="e2e")
def test_a_rule_waiting_on_an_operating_system_says_so(browser, tmp_path):
    """The fixture's RULE-4 ran on Windows and failed; this one never ran."""
    payload = payload_named('regulated')
    cell = payload['features'][0]['rules'][3]['cells']['passed']
    cell['word'] = 'not run'
    cell['missing_env'] = ['windows']
    cell['reasons'] = ['windows: no record yet']
    cell['platforms'] = {'linux': cell['platforms']['linux']}
    page = open_board(browser, tmp_path, payload)
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-4"]')
    body = page.inner_text('.wrap')
    assert 'windows: no record yet' in body
    assert 'NOT RUN' in body
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-18", "RULE-18", tier="e2e")
def test_the_review_tab_groups_by_what_a_person_must_do(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert 'Review (3)' in page.inner_text('.tabs')
    page.click('[data-screen="review"]')
    assert '3 rules need a person' in page.inner_text('h1')
    # The three words the strong cell reads when the work left is a person's,
    # in the order the tab groups them. `not audited` is on no tab: it waits
    # for `purlin:audit`, not for anyone.
    assert texts(page, '.group .gt') == ['manual test', 'unsettled', 'held']
    assert texts(page, '.group .muted') == ['(1)', '(1)', '(1)']
    cells = list_cells(page)
    assert [(row[0], row[1]) for row in cells] == [
        ('invoice', 'RULE-3'), ('checkout_design', 'RULE-1'),
        ('login', 'RULE-3')]
    assert cells[2][2] == 'A locked account sends one notification email.'
    assert cells[2][3] == 'passed'
    assert cells[2][4] == 'HELD'
    page.click('.rev:not(.th)')
    assert 'RULE-3' in page.inner_text('h1')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-36", "RULE-18", tier="e2e")
def test_both_tabs_name_their_six_columns(browser, tmp_path):
    """A row of six cells with no headings left the reader to guess them."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-screen="review"]')
    assert texts(page, '.rev.th > span') == [
        'Spec', 'Rule', 'What it claims', 'Bar', 'Reads', 'Why']
    page.click('[data-screen="sign"]')
    assert texts(page, '.rev.th > span') == [
        'Spec', 'Rule', 'What it claims', 'Bar', 'Signed', 'Command']
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-37", "RULE-18", tier="e2e")
def test_a_tab_above_the_gate_is_not_offered(browser, tmp_path):
    """Nothing asks a person under `passed`, and nothing signs under `strong`."""
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    assert texts(solo, '.tabs button') == ['Board']
    solo.close()

    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert texts(team, '.tabs button') == ['Board', 'Review (1)']
    team.close()


@pytest.mark.proof("purlin_report", "PROOF-31", "RULE-30", tier="e2e")
def test_a_review_row_states_the_bar_the_word_and_the_reasons(browser,
                                                              tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-screen="review"]')
    rows = {(row[0], row[1]): row for row in list_cells(page)}
    assert rows[('checkout_design', 'RULE-1')][3] == 'strong'
    assert rows[('checkout_design', 'RULE-1')][4] == 'UNSETTLED'
    assert rows[('checkout_design', 'RULE-1')][5] == (
        'the AI audit could not settle')
    assert rows[('invoice', 'RULE-3')][4] == 'MANUAL TEST'
    assert rows[('login', 'RULE-3')][4] == 'HELD'
    assert rows[('login', 'RULE-3')][5] == (
        'held by sam@acme.com: the lock expiry is never read')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-38", "RULE-30", tier="e2e")
def test_a_row_with_no_reason_of_its_own_reads_its_word_as_a_sentence(
        browser, tmp_path):
    """The payload's cell carries a word; a person reads a sentence."""
    payload = payload_named('regulated')
    for feature in payload['features']:
        for rule in feature['rules']:
            if feature['name'] == 'invoice' and rule['id'] == 'RULE-3':
                rule['cells']['strong']['reasons'] = []
    page = open_board(browser, tmp_path, payload)
    page.click('[data-screen="review"]')
    rows = {(row[0], row[1]): row for row in list_cells(page)}
    assert rows[('invoice', 'RULE-3')][5] == (
        'Its proof is @manual, so a person runs the test and states what '
        'they saw.')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-19", "RULE-19", tier="e2e")
def test_an_empty_review_tab_says_what_puts_a_rule_on_it(browser, tmp_path):
    payload = payload_named('team')
    payload['review_list'] = []
    page = open_board(browser, tmp_path, payload)
    page.click('[data-screen="review"]')
    assert 'No rule is waiting for a person' in page.inner_text('.empty')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-50", "RULE-38", tier="e2e")
def test_the_sign_tab_lists_the_rules_waiting_for_a_signature(browser,
                                                              tmp_path):
    """A rule reaches it once it has cleared its bar and nobody signed it."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert 'Sign (1)' in page.inner_text('.tabs')
    page.click('[data-screen="sign"]')
    assert '1 rule to sign' in page.inner_text('h1')
    rows = list_cells(page)
    assert len(rows) == 1
    assert rows[0][0] == 'login' and rows[0][1] == 'RULE-2'
    assert rows[0][3] == 'strong'
    assert rows[0][4] == 'STALE'
    assert rows[0][5] == 'purlin:sign login RULE-2'
    page.click('.rev:not(.th)')
    assert 'RULE-2' in page.inner_text('h1')
    assert page.inner_text('[data-act="close"]') == u'\u2190 Sign'
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-51", "RULE-38", tier="e2e")
def test_an_empty_sign_tab_says_what_puts_a_rule_on_it(browser, tmp_path):
    payload = payload_named('regulated')
    payload['sign_list'] = []
    page = open_board(browser, tmp_path, payload)
    page.click('[data-screen="sign"]')
    assert 'No rule is waiting for a signature' in page.inner_text('.empty')
    assert 'cleared its bar' in page.inner_text('.empty')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-20", "RULE-20", tier="e2e")
def test_an_older_payload_shows_one_notice_and_nothing_else(browser,
                                                            tmp_path):
    payload = payload_named('team')
    payload['schema_version'] = 3
    page = open_board(browser, tmp_path, payload)
    notices = page.query_selector_all('.notice')
    assert len(notices) == 1
    assert 'purlin:status' in notices[0].inner_text()
    assert page.query_selector_all('.tile') == []
    assert page.query_selector_all('.tbl') == []
    assert page.query_selector_all('.tabs') == []
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-21", "RULE-21", tier="e2e")
def test_no_data_at_all_names_the_command_that_writes_it(browser, tmp_path):
    root = str(tmp_path)
    shutil.copyfile(PAGE, os.path.join(root, 'purlin-report.html'))
    page = browser.new_page(viewport={'width': 1200, 'height': 800})
    page.goto('file://' + os.path.join(root, 'purlin-report.html'))
    page.wait_for_selector('.empty', timeout=10000)
    assert 'purlin:status' in page.inner_text('.empty')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-22", "RULE-22", tier="e2e")
def test_the_working_tree_notice_only_shows_on_the_board(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert len(page.query_selector_all('.notice')) == 2
    page.click('[data-screen="review"]')
    assert page.query_selector_all('.notice') == []
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-24", "RULE-24", tier="e2e")
def test_the_open_rule_is_the_last_tab(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert texts(page, '.tabs button') == ['Board', 'Review (3)', 'Sign (1)']
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    assert texts(page, '.tabs button') == ['Board', 'Review (3)', 'Sign (1)',
                                           'login RULE-1']
    page.click('.tabs button:last-child')
    assert 'RULE-1' in page.inner_text('h1')
    assert len(texts(page, '.tabs button')) == 4
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-25", "RULE-25", tier="e2e")
def test_the_link_back_closes_the_rule_where_it_was_opened(browser, tmp_path):
    """One rule, opened twice, closes back to the screen it came from."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-screen="review"]')
    page.click('.rev:not(.th)')
    assert page.inner_text('[data-act="close"]') == u'\u2190 Review'
    page.click('[data-act="close"]')
    assert '3 rules need a person' in page.inner_text('h1')
    assert texts(page, '.tabs button') == ['Board', 'Review (3)', 'Sign (1)']

    page.click('[data-screen="board"]')
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    assert page.inner_text('[data-act="close"]') == u'\u2190 Board'
    page.click('[data-act="close"]')
    assert len(feature_names(page)) == 4
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-26", "RULE-26", tier="e2e")
def test_the_rule_screen_names_the_sign_command(browser, tmp_path):
    """The page cannot sign a commit, so it names the command that does."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-2"]')
    body = page.inner_text('.wrap')
    assert 'purlin:sign login RULE-2' in body
    assert 'A signature is a signed commit that names its signer' in body
    assert 'courier' in page.eval_on_selector(
        '.cmd', 'el => getComputedStyle(el).fontFamily').lower()

    page.click('[data-act="close"]')
    page.click('.rule[data-rule="RULE-1"]')
    signed = page.inner_text('.wrap')
    assert 'Signed by jane@acme.com' in signed
    assert 'purlin:sign' not in signed
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-52", "RULE-26", tier="e2e")
def test_a_rule_that_needs_no_signature_says_why(browser, tmp_path):
    """This project signs from `strong`, and invoice RULE-1's bar is `passed`."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="invoice"]')
    page.click('.rule[data-feature="invoice"][data-rule="RULE-1"]')
    body = page.inner_text('.wrap')
    assert 'purlin:sign invoice RULE-1' in body
    assert 'this rule\u2019s bar is passed, so no signature is required' in body
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-39", "RULE-26", tier="e2e")
def test_the_sign_panel_is_absent_below_the_signed_gate(browser, tmp_path):
    """Under `strong` no signature is read, so none is asked for."""
    page = open_board(browser, tmp_path, payload_named('team'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    body = page.inner_text('.wrap')
    assert 'purlin:sign' not in body
    assert 'Brief' in body
    assert 'could not settle' in body
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-27", "RULE-27", tier="e2e")
def test_coming_back_to_an_old_tab_reloads_it(browser, tmp_path):
    """A mark on the window survives a render and not a reload."""
    payload = payload_named('regulated')
    payload['generated_at'] = stamp_ago(120)
    page = open_board(browser, tmp_path, payload)
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    page.evaluate('window.purlinMark = 1')
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_function('() => window.purlinMark === undefined',
                           timeout=10000)
    page.wait_for_selector('h1', timeout=10000)
    assert 'RULE-1' in page.inner_text('h1')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-28", "RULE-28", tier="e2e")
def test_the_freshness_line_is_a_button_that_reloads(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    node = page.query_selector('.topbar [data-act="reload"]')
    assert node.evaluate('el => el.tagName') == 'BUTTON'
    assert 'Data:' in node.inner_text()
    assert 'btn' in node.get_attribute('class').split()
    assert page.eval_on_selector(
        '.topbar [data-act="reload"]',
        'el => getComputedStyle(el).borderTopWidth') == page.eval_on_selector(
        '[data-act="theme"]', 'el => getComputedStyle(el).borderTopWidth')

    page.evaluate('window.purlinMark = 1')
    page.click('.topbar [data-act="reload"]')
    page.wait_for_function('() => window.purlinMark === undefined',
                           timeout=10000)
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-29", "RULE-29", tier="e2e")
def test_the_age_recomputes_every_minute_from_the_same_payload(browser,
                                                               tmp_path):
    """The stamp does not move; the clock does, and the top bar follows."""
    when = datetime.datetime(2026, 1, 1, 12, 0, 0,
                             tzinfo=datetime.timezone.utc)
    payload = payload_named('regulated')
    payload['generated_at'] = (
        when - datetime.timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
    page = open_board(browser, tmp_path, payload, clock_at=when)
    assert 'Data: less than a minute old' in page.inner_text('.topbar .fresh')
    page.clock.run_for(90000)
    assert 'Data: 2 minutes old' in page.inner_text('.topbar .fresh')
    page.close()

# ---------------------------------------------------------------------------
# The screenshots the docs embed
# ---------------------------------------------------------------------------

@pytest.mark.proof("purlin_report", "PROOF-23", "RULE-23")
def test_the_docs_screenshots_come_from_the_fixtures():
    """Six images, each from a fixture payload, written to docs/images/.

    A screenshot taken from whatever this checkout happens to hold goes stale
    the moment the data moves and shows one project's names to every reader,
    so the capture names a fixture for every shot it takes.
    """
    import capture_doc_screenshots as capture

    assert len(capture.SHOTS) == 6, capture.SHOTS
    assert capture.FIXTURES == FIXTURES, capture.FIXTURES
    assert capture.IMAGES_DIR == os.path.join(ROOT, 'docs', 'images'), \
        capture.IMAGES_DIR
    for name, fixture, _clicks in capture.SHOTS:
        payload = os.path.join(FIXTURES, fixture + '.json')
        assert os.path.isfile(payload), \
            '%s names the payload %s, which does not exist' % (name, payload)
        image = os.path.join(capture.IMAGES_DIR, name)
        assert os.path.isfile(image), \
            'the docs embed %s and it is absent' % image
        assert os.path.getsize(image) > 0, '%s is empty' % image


FREE_CHECK_NAMES = ('happy_path_only', 'no_expected_value', 'vague_verb',
                    'missing_trigger', 'tier_mismatch',
                    'implementation_coupling', 'no_assertion', 'tautology',
                    'no negative case')


@pytest.mark.proof("purlin_report", "PROOF-54", "RULE-39", tier="e2e")
def test_the_brief_panel_reads_sentences_and_names_no_check(browser, tmp_path):
    """The audit writes what it observed, in sentences."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="checkout_design"]')
    page.click('.rule[data-rule="RULE-1"]')
    body = page.inner_text('.wrap')
    assert 'The test reads the text "Total"' in body
    assert 'The AI audit could not settle the question' in body
    page.click('[data-act="close"]')
    page.click('[data-act="feature"][data-feature="invoice"]')
    page.click('.rule[data-rule="RULE-2"]')
    body = page.inner_text('.wrap')
    assert 'Test strength 64%, against a minimum of 80%.' in body
    assert 'No proof of this rule names a rejection' in body
    assert 'The AI audit settled the question.' in body
    labels = page.eval_on_selector_all(
        '.kv dt', 'els => els.map(e => e.innerText.trim())')
    assert 'Free checks' not in labels
    for name in FREE_CHECK_NAMES:
        assert name not in body, name
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-55", "RULE-40", tier="e2e")
def test_the_top_bar_states_the_signed_tag(browser, tmp_path):
    """The payload names the tag on HEAD, or names none."""
    payload = payload_named('regulated')
    page = open_board(browser, tmp_path, payload)
    bar = page.inner_text('.topbar')
    assert payload['tag']['name'] in bar
    assert payload['tag']['commit'][:7] in bar
    assert 'no signed tag' not in bar
    page.close()
    for process in ('solo', 'team'):
        payload = payload_named(process)
        assert payload['tag'] is None
        page = open_board(browser, tmp_path, payload)
        bar = page.inner_text('.topbar')
        assert 'no signed tag' in bar
        assert 'signed/' not in bar
        page.close()
