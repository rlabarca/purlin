"""The board page: how it is built, and what it shows.

Two halves. The first reads the built file as text and holds it to the design
system: one token block, no colour written anywhere else, no shadow, no
gradient, no emoji, no request to anything outside the file. The second opens
it in a headless browser over `file://` with a fixture payload beside it, one
fixture per process, and reads what a person would see.

The fixtures under `dev/fixtures/report/` are payloads at schema 9, one for
each of the three processes: solo at the `passed` gate with no evidence at all,
team at `strong` with strength and one rule the AI audit could not decide,
regulated at `signed` with signatures, a stale rule, a rule whose audit found
a gap, a rule no audit has run on, and a rule that passed on one platform and failed on
another.

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
    return '.chip[data-filter="%s"]' % label.lower().replace(' ', '-')


def head_labels(page):
    """The spec table's column headings, in the order they are drawn."""
    return texts(page, '.th > div')


# How many tiles the strip carries at each gate: four buckets always, the
# strong bucket at `strong`, the signed bucket at `signed`.
TILES = {'solo': 4, 'team': 5, 'regulated': 6}


def rule_ids(page):
    return texts(page, '.rule .rid')


def list_cells(page):
    """Each row of the Queue tab as its six cells, heading aside: feature,
    id, text, level, what it needs and the command."""
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


# Every panel on the open screen that carries a heading: the heading and each
# paragraph under it, as a person reads them.
PANELS = """() => Array.from(document.querySelectorAll('.panel')).filter(
  p => p.querySelector('h2')).map(p => ({
    head: p.querySelector('h2').textContent.trim(),
    lines: Array.from(p.querySelectorAll('p')).map(
      e => e.innerText.trim().replace(/\\s+/g, ' '))}))"""


def panel_heads(page):
    return [panel['head'] for panel in page.evaluate(PANELS)]


def panel_lines(page, head):
    """The lines of the one panel headed `head` on the open screen."""
    found = [panel['lines'] for panel in page.evaluate(PANELS)
             if panel['head'] == head]
    assert len(found) == 1, (head, page.evaluate(PANELS))
    return found[0]


# ---------------------------------------------------------------------------
# The built file
# ---------------------------------------------------------------------------

# purlin: purlin_report PROOF-1
def test_the_build_is_reproducible():
    """Two builds of the same parts give the same bytes."""
    first = build_page()
    second = build_page()
    assert first == second


# purlin: purlin_report PROOF-2
def test_the_page_is_one_file_under_the_line_budget(page_text):
    assert len(page_text.splitlines()) <= 1200
    assert os.path.isfile(os.path.join(ROOT, 'purlin-report.html'))
    assert read(os.path.join(ROOT, 'purlin-report.html')) == page_text


# purlin: purlin_report PROOF-3
def test_every_colour_is_a_token(page_text):
    """The only place a colour is written is the inlined token block."""
    inside, outside = token_block(page_text)
    assert '--canvas' in inside
    written = [match for match in re.findall(r'#[0-9a-fA-F]{3,8}\b', outside)
               if not match.lower().startswith('#purlin')]
    assert written == [], written


# purlin: purlin_report PROOF-4
# purlin: purlin_report PROOF-5
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


# purlin: purlin_report PROOF-6
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
# purlin: purlin_report PROOF-7
def test_the_board_renders_for_each_process(browser, tmp_path, process):
    payload = payload_named(process)
    summary = payload['summary']
    gate = payload['gate']['gate']
    page = open_board(browser, tmp_path, payload)
    bar = page.inner_text('.topbar')
    assert 'gate: %s \u00b7 %d of %d' % (
        gate, summary['met'], summary['rules']) in bar, bar
    assert 'Data:' in bar
    assert page.query_selector('.strip') is not None
    first = page.evaluate(
        "() => { const s = document.querySelector('.strip');"
        " const sec = s.closest('section');"
        " return sec.parentElement.querySelector('section') === sec; }")
    assert first, 'the board does not open on the tiles'
    text = page.inner_text('body')
    assert 'rules pass their tests' not in text
    assert 'rules meet the gate' not in text
    assert len(page.query_selector_all('.tile')) == TILES[process]
    assert set(feature_names(page)) == set(
        f['name'] for f in payload['features'])
    page.close()
    if process == 'regulated':
        payload['summary']['met'] = 3
        page = open_board(browser, tmp_path, payload)
        assert 'gate: signed \u00b7 3 of %d' % summary['rules'] in \
            page.inner_text('.topbar')
        page.close()


BASE_COLUMNS = ['Spec', 'Rules', 'Proofs', 'Tests']


# purlin: purlin_report PROOF-9
def test_the_columns_scale_with_the_gate(browser, tmp_path):
    """A gate asks for what it asks for, and the board asks no more."""
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    assert head_labels(solo) == BASE_COLUMNS
    solo.close()

    # Proofs are optional at `passed`: a project there that writes none is
    # shown no column for them.
    bare = open_board(browser, tmp_path / 'bare',
                      without_proof_lines(payload_named('solo')))
    assert head_labels(bare) == ['Spec', 'Rules', 'Tests']
    bare.close()

    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert head_labels(team) == BASE_COLUMNS + ['Strong']
    team.close()

    # From `strong` up every rule needs a proof, so the column stays.
    team = open_board(browser, tmp_path / 'team-bare',
                      without_proof_lines(payload_named('team')))
    assert head_labels(team) == BASE_COLUMNS + ['Strong']
    team.close()

    reg = open_board(browser, tmp_path / 'reg', payload_named('regulated'))
    assert head_labels(reg) == BASE_COLUMNS + ['Strong', 'Signed']
    assert len(head_labels(reg)) == 6
    reg.close()


# purlin: purlin_report PROOF-32
def test_the_rule_screen_says_what_each_platform_found(browser, tmp_path):
    """A rule can pass on one operating system and fail on another.

    The platforms are the rule's business, so they live on its screen, drawn
    from the platforms its passed cell carries.
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
# purlin: purlin_report PROOF-12
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


# purlin: purlin_report PROOF-30
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


# purlin: purlin_report PROOF-8
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
    assert flag_cards(page) == {'Queue': str(payload['summary']['queue']),
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


# purlin: purlin_report PROOF-40
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
    # login's RULE-3 and invoice's RULE-1 are marked `[level: passed]`, so
    # the Strong and Signed shares are read over the other rules alone.
    assert cells['login']['Strong'] == '2 of 3 \u00b7 86%'
    assert cells['checkout_design']['Strong'] == '0 of 1 \u00b7 90%'
    assert cells['login']['Signed'] == '1 of 3'
    assert cells['invoice']['Signed'] == '0 of 2'
    page.close()

    # The team board is where a proof has no test at all, and the cell names
    # the gap in the warn tone beside the total.
    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert count_cells(team)['invoice']['Proofs'] == (
        '2 \u00b7 1 no test')
    team.close()


# purlin: purlin_report PROOF-44
def test_every_cell_of_a_spec_row_carries_its_hover(browser, tmp_path):
    """The columns the board dropped became the hovers the cells carry."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    rows = hovers(page)
    assert rows['login']['Spec'] == 'specs/auth/login.md'
    assert rows['login']['Proofs'] == 'every proof has a test'
    assert rows['invoice']['Proofs'] == 'every proof has a test'

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
    # writes a proof no marked test runs, and the hover names it.
    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert hovers(team)['invoice']['Proofs'] == (
        'no test \u00b7 PROOF-2')
    team.close()


# purlin: purlin_report PROOF-49
def test_the_queue_card_counts_the_rules_waiting_for_a_person(browser,
                                                              tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert flag_cards(page) == {'Queue': '2', 'Stale': '1'}
    titles = page.eval_on_selector_all(
        '.flag', 'els => els.map(e => e.getAttribute("title"))')
    assert titles[0].split('\n') == ['invoice \u00b7 1', 'login \u00b7 1']
    page.close()

    payload = payload_named('regulated')
    payload['summary']['queue'] = 0
    payload['queue'] = []
    none = open_board(browser, tmp_path / 'none', payload)
    assert none.eval_on_selector_all(
        '.flag', 'els => els.map(e => e.getAttribute("title"))')[0] == (
        'No rule is waiting for a person.')
    assert 'on' not in none.get_attribute('.flag', 'class').split()
    none.close()


# purlin: purlin_report PROOF-45
def test_every_tile_carries_its_hover(browser, tmp_path):
    """A tile says for the project what its column says for one spec."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    titles = page.eval_on_selector_all(
        '.tile', 'els => els.map(e => e.getAttribute("title"))')
    assert len(titles) == 6
    for title in titles[1:3]:
        assert '\n' not in title and title.endswith('.'), title
    # The `Untested` tile's sentence, then one line per word its rules read.
    untested = titles[0].split('\n')
    assert untested[0].endswith('.'), untested
    assert untested[1:] == ['out of date \u00b7 1'], untested
    assert titles[3].split('\n')[0].startswith('windows \u00b7 ci \u00b7 ')
    assert titles[4].split('\n')[0].startswith('audit \u00b7 ci \u00b7 ')
    assert titles[5].split('\n')[0] == 'jane@acme.com \u00b7 2026-09-12'
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
    assert bands == ['\u25bc AUTH \u00b7 1 spec \u00b7 3 of 4 pass',
                     '\u25bc BILLING \u00b7 2 specs \u00b7 4 of 5 pass',
                     '\u25bc _ANCHORS \u00b7 1 spec \u00b7 1 of 1 pass']
    page.close()


# purlin: purlin_report PROOF-10
def test_a_feature_row_expands_to_its_rules(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert rule_ids(page) == []
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4']
    assert 'SIGNED' in page.inner_text('.rule')
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == []
    page.close()


FILTER_CASES = [
    ('untested', ['export'], []),
    ('failing', [], []),
    ('partial', ['login'], ['RULE-4']),
    # A pill counts the rules whose strong cell reads its word.
    # checkout_design's audit could not decide, which is build work and reads
    # `weak`. The rules that wait for a person are `queue`. login's RULE-3 is
    # marked `[level: passed]`, so it has no strong cell to read.
    ('weak', ['login', 'invoice', 'export', 'checkout_design'],
     ['RULE-4']),  # 4 rules
    ('not-audited', ['export'], []),
    ('queue', ['login', 'invoice'], ['RULE-2']),
    ('stale', ['login'], ['RULE-2']),
]


@pytest.mark.parametrize('filter_id,features,login_rules', FILTER_CASES)
# purlin: purlin_report PROOF-13
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


# purlin: purlin_report PROOF-14
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


# purlin: purlin_report PROOF-35
def test_a_filter_above_the_gate_is_not_offered(browser, tmp_path):
    """A project at `passed` is never asked about strength or signatures."""
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    assert chip_labels(solo) == ['Untested', 'Failing', 'Partial']
    solo.close()

    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert chip_labels(team) == ['Untested', 'Failing', 'Partial', 'Weak',
                                 'Not audited', 'Queue']
    team.close()

    reg = open_board(browser, tmp_path / 'reg', payload_named('regulated'))
    assert chip_labels(reg) == ['Untested', 'Failing', 'Partial', 'Weak',
                                'Not audited', 'Queue', 'Stale']
    assert chip_counts(reg) == {'Untested': 1, 'Failing': 0, 'Partial': 1,
                                'Weak': 4, 'Not audited': 1, 'Queue': 2,
                                'Stale': 1}
    reg.close()


@pytest.mark.parametrize('process', PROCESSES)
# purlin: purlin_report PROOF-46
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


# purlin: purlin_report PROOF-15
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
    page.click('[data-act="close"]')
    page.click('.rule[data-rule="RULE-3"]')
    third = page.inner_text('.wrap')
    assert 'PROOF-3' in third
    # RULE-3 is marked `[level: passed]`: it is asked for its tests alone,
    # so its screen reads its passed cell and nothing the audit found.
    assert list(page.evaluate(KV_ROWS))[:2] == ['Passed', 'Level'], third
    assert ('PROOF-3 reads the status code alone; no test reads when the '
            'lock expires.') not in third
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


# purlin: purlin_report PROOF-53
def test_the_rule_screen_names_the_level_and_where_it_came_from(browser,
                                                                tmp_path):
    """A rule has a level, from its own tag or from the project's gate."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    rows = page.evaluate(KV_ROWS)
    # The whole row set, so a row the model dropped cannot come back.
    assert list(rows) == ['Passed', 'Strong', 'Signed', 'Level', 'Spec',
                          'Last run', 'Signatures']
    assert rows['Level'] == 'signed (the gate)'

    page.click('[data-act="close"]')
    page.click('[data-act="feature"][data-feature="invoice"]')
    page.click('.rule[data-feature="invoice"][data-rule="RULE-1"]')
    assert page.evaluate(KV_ROWS)['Level'] == 'passed (marked)'

    # Under `passed` no rule is audited and none is signed, so the level is
    # not a question the board puts to the reader.
    page.close()
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    solo.click('[data-act="feature"][data-feature="login"]')
    solo.click('.rule[data-rule="RULE-1"]')
    assert 'Level' not in solo.evaluate(KV_ROWS)
    solo.close()


# purlin: purlin_report PROOF-16
def test_the_rule_screen_links_to_the_git_host(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    href = page.get_attribute('a[href*="specs/auth/login.md"]', 'href')
    assert href.startswith('https://github.com/acme/ledger/blob/')
    assert page.query_selector('a[href*="RULE-1.1a2b3c4d.jane-doe.json"]')
    page.close()


# purlin: purlin_report PROOF-16
def test_a_rule_with_no_remote_has_no_links(browser, tmp_path):
    """The solo fixture names no remote, so paths stay plain text."""
    page = open_board(browser, tmp_path, payload_named('solo'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    assert page.query_selector_all('.wrap a') == []
    assert 'specs/auth/login.md' in page.inner_text('.wrap')
    page.close()


# purlin: purlin_report PROOF-17
def test_a_rule_waiting_on_an_operating_system_says_so(browser, tmp_path):
    """The fixture's RULE-4 ran on Windows and failed; this one never ran."""
    payload = payload_named('regulated')
    cell = payload['features'][0]['rules'][3]['cells']['passed']
    cell['word'] = 'not run'
    cell['missing_env'] = ['windows']
    cell['reasons'] = ['windows: no run yet']
    cell['platforms'] = {'linux': cell['platforms']['linux']}
    page = open_board(browser, tmp_path, payload)
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-4"]')
    body = page.inner_text('.wrap')
    assert 'windows: no run yet' in body
    assert 'NOT RUN' in body
    page.close()


# purlin: purlin_report PROOF-18
def test_the_queue_tab_lists_what_each_rule_needs(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert 'Queue (2)' in page.inner_text('.tabs')
    page.click('[data-screen="queue"]')
    assert '2 rules need a person' in page.inner_text('h1')
    assert 'Hand checks 1 \u00b7 Signatures 1' in page.inner_text('.wrap')
    cells = list_cells(page)
    assert [(row[0], row[1]) for row in cells] == [
        ('invoice', 'RULE-3'), ('login', 'RULE-2')]
    assert cells[1][2] == (
        'Five failed attempts lock the account for fifteen minutes.'), cells[1]
    assert cells[1][3:] == ['signed', 'signature',
                            'purlin:sign login RULE-2'], cells[1]
    page.click('.rev:not(.th) >> nth=1')
    assert 'RULE-2' in page.inner_text('h1')
    page.close()


# purlin: purlin_report PROOF-36
def test_the_queue_tab_names_its_six_columns(browser, tmp_path):
    """A row of six cells with no headings left the reader to guess them."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-screen="queue"]')
    assert texts(page, '.rev.th > span') == [
        'Spec', 'Rule', 'What it claims', 'Level', 'Needs', 'Command']
    page.close()


# purlin: purlin_report PROOF-37
def test_a_tab_above_the_gate_is_not_offered(browser, tmp_path):
    """Nothing asks a person under `passed`."""
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    assert texts(solo, '.tabs button') == ['Board']
    solo.close()

    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    assert texts(team, '.tabs button') == ['Board', 'Queue (0)']
    team.close()


# The hover the `Needs` cell of each queue row carries.
NEED_HOVERS = """els => els.map(e => e.children[4].getAttribute('title'))"""


# purlin: purlin_report PROOF-31
def test_a_queue_row_states_the_level_the_need_and_the_command(browser,
                                                               tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-screen="queue"]')
    rows = {(row[0], row[1]): row for row in list_cells(page)}
    invoice = rows[('invoice', 'RULE-3')]
    assert invoice[3:] == [
        'signed', 'hand check',
        'purlin:sign invoice RULE-3 --note "<what you saw>"'], invoice
    assert rows[('login', 'RULE-2')][4] == 'signature'
    assert ('checkout_design', 'RULE-1') not in rows, (
        'an audit that could not decide is build work, not a hand check')
    titles = page.eval_on_selector_all('.rev:not(.th)', NEED_HOVERS)
    assert titles[0].startswith('manual test'), titles[0]
    assert titles[1] == 'stale \u00b7 hashes changed after the signature'
    page.close()


# purlin: purlin_report PROOF-19
def test_an_empty_queue_tab_says_what_puts_a_rule_on_it(browser, tmp_path):
    """What arrives on the tab depends on the gate the project has."""
    expected = {
        'team': 'No rule is waiting for a person. A rule arrives here when '
                'its level is strong and its proof is @manual.',
        'regulated': 'No rule is waiting for a person. A rule arrives here '
                     'when its proof is @manual, or when its level is signed '
                     'and it has passed its tests and its audit.'}
    for name, text in expected.items():
        payload = payload_named(name)
        payload['queue'] = []
        page = open_board(browser, tmp_path / name, payload)
        page.click('[data-screen="queue"]')
        assert page.inner_text('.empty').strip() == text
        page.close()


# purlin: purlin_report PROOF-20
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


# purlin: purlin_report PROOF-21
def test_no_data_at_all_names_the_command_that_writes_it(browser, tmp_path):
    root = str(tmp_path)
    shutil.copyfile(PAGE, os.path.join(root, 'purlin-report.html'))
    page = browser.new_page(viewport={'width': 1200, 'height': 800})
    page.goto('file://' + os.path.join(root, 'purlin-report.html'))
    page.wait_for_selector('.empty', timeout=10000)
    assert 'purlin:status' in page.inner_text('.empty')
    page.close()


# purlin: purlin_report PROOF-22
def test_the_working_tree_notice_only_shows_on_the_board(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert len(page.query_selector_all('.notice')) == 2
    page.click('[data-screen="queue"]')
    assert page.query_selector_all('.notice') == []
    page.close()


# purlin: purlin_report PROOF-24
def test_the_open_rule_is_the_last_tab(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert texts(page, '.tabs button') == ['Board', 'Queue (2)']
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    assert texts(page, '.tabs button') == ['Board', 'Queue (2)',
                                           'login RULE-1']
    page.click('.tabs button:last-child')
    assert 'RULE-1' in page.inner_text('h1')
    assert len(texts(page, '.tabs button')) == 3
    page.close()


# purlin: purlin_report PROOF-25
def test_the_link_back_closes_the_rule_where_it_was_opened(browser, tmp_path):
    """One rule, opened twice, closes back to the screen it came from."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-screen="queue"]')
    page.click('.rev:not(.th)')
    assert page.inner_text('[data-act="close"]') == u'\u2190 Queue'
    page.click('[data-act="close"]')
    assert '2 rules need a person' in page.inner_text('h1')
    assert texts(page, '.tabs button') == ['Board', 'Queue (2)']

    page.click('[data-screen="board"]')
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    assert page.inner_text('[data-act="close"]') == u'\u2190 Board'
    page.click('[data-act="close"]')
    assert len(feature_names(page)) == 4
    page.close()


# purlin: purlin_report PROOF-26
def test_the_rule_screen_names_the_sign_command(browser, tmp_path):
    """The page cannot sign a commit, so it names the command that does."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-2"]')
    body = page.inner_text('.wrap')
    assert 'Signature' in panel_heads(page)
    assert 'purlin:sign login RULE-2' in body
    assert 'A signature is a signed commit that names its signer' in body
    assert 'courier' in page.eval_on_selector(
        '.cmd', 'el => getComputedStyle(el).fontFamily').lower()

    page.click('[data-act="close"]')
    page.click('[data-act="feature"][data-feature="invoice"]')
    page.click('.rule[data-feature="invoice"][data-rule="RULE-3"]')
    assert 'Hand check' in panel_heads(page)
    assert ('purlin:sign invoice RULE-3 --note "<what you saw>"'
            in page.inner_text('.wrap'))

    page.click('[data-act="close"]')
    page.click('.rule[data-feature="login"][data-rule="RULE-1"]')
    signed = page.inner_text('.wrap')
    assert ('Signed by jane@acme.com on 2026-09-12 10:02 UTC, on jane-laptop '
            '(macos)') in signed
    assert 'purlin:sign' not in signed
    page.close()


# purlin: purlin_report PROOF-52
def test_a_rule_that_needs_no_signature_shows_none(browser, tmp_path):
    """Invoice RULE-1 is marked `[level: passed]`, so it asks for none."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="invoice"]')
    page.click('.rule[data-feature="invoice"][data-rule="RULE-1"]')
    body = page.inner_text('.wrap')
    assert 'purlin:sign' not in body, body
    assert panel_heads(page) == [], panel_heads(page)
    assert list(page.evaluate(KV_ROWS)) == ['Passed', 'Level', 'Spec',
                                            'Last run'], body
    page.close()


# purlin: purlin_report PROOF-39
def test_the_sign_panel_is_absent_below_the_signed_gate(browser, tmp_path):
    """Under `strong` no signature is read, so none is asked for."""
    page = open_board(browser, tmp_path, payload_named('team'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    body = page.inner_text('.wrap')
    assert 'purlin:sign' not in body
    assert panel_lines(page, 'Audit')[0].startswith('Undecided.')
    page.close()


# purlin: purlin_report PROOF-27
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


# purlin: purlin_report PROOF-28
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


# purlin: purlin_report PROOF-29
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

# purlin: purlin_report PROOF-23
def test_the_docs_screenshots_come_from_the_fixtures():
    """Three images, each from a fixture payload, written to docs/images/.

    A screenshot taken from whatever this checkout happens to hold goes stale
    the moment the data moves and shows one project's names to every reader,
    so the capture names a fixture for every shot it takes.
    """
    import capture_doc_screenshots as capture

    assert [(name, fixture) for name, fixture, _clicks in capture.SHOTS] == [
        ('dashboard-board.png', 'regulated'),
        ('dashboard-queue.png', 'regulated'),
        ('dashboard-rule.png', 'regulated')], capture.SHOTS
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
    assert sorted(os.listdir(capture.IMAGES_DIR)) == sorted(
        name for name, _fixture, _clicks in capture.SHOTS)


# purlin: purlin_report PROOF-54
def test_the_audit_panel_reads_what_the_audit_found(browser, tmp_path):
    """The answer, each finding on its own line, the strength, the model."""
    page = open_board(browser, tmp_path / 'reg', payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="checkout_design"]')
    page.click('.rule[data-rule="RULE-1"]')
    lines = panel_lines(page, 'Audit')
    assert lines[0].startswith('Undecided. '), lines
    assert lines[1].startswith('The test reads the text "Total"'), lines
    assert lines[2] == 'Test strength 90%, against a minimum of 80%.', lines
    assert lines[3] == ('Read by example-model-1 on 2026-09-12 '
                        '09:14 UTC'), lines

    page.click('[data-act="close"]')
    page.click('[data-act="feature"][data-feature="invoice"]')
    page.click('.rule[data-feature="invoice"][data-rule="RULE-2"]')
    lines = panel_lines(page, 'Audit')
    assert lines[0] == 'Weak.', lines
    assert lines[1].startswith('No proof of this rule names a rejection'), lines
    assert lines[2] == 'Test strength 64%, against a minimum of 80%.', lines

    page.click('[data-act="close"]')
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-feature="login"][data-rule="RULE-1"]')
    assert panel_lines(page, 'Audit')[0] == 'Strong. It found nothing.'

    page.click('[data-act="close"]')
    page.click('[data-act="feature"][data-feature="export"]')
    page.click('.rule[data-feature="export"][data-rule="RULE-2"]')
    assert panel_lines(page, 'Audit')[0] == (
        'No audit has read this rule\u2019s text, proof and test yet.')
    page.close()

    payload = payload_named('team')
    payload['features'][0]['rules'][1]['cells']['strong']['strength'] = None
    team = open_board(browser, tmp_path / 'team', payload)
    team.click('[data-act="feature"][data-feature="login"]')
    team.click('.rule[data-rule="RULE-2"]')
    assert 'no mutation score measured' in panel_lines(team, 'Audit')
    team.close()


# purlin: purlin_report PROOF-55
def test_the_top_bar_states_the_signed_tag(browser, tmp_path):
    """At `signed` the payload names the tag on HEAD, or names none; below
    `signed` the top bar shows no tag at all."""
    payload = payload_named('regulated')
    assert payload['gate']['gate'] == 'signed'
    page = open_board(browser, tmp_path, payload)
    bar = page.inner_text('.topbar')
    assert payload['tag']['name'] in bar
    assert payload['tag']['commit'][:7] in bar
    assert 'no signed tag' not in bar
    page.close()
    payload['tag'] = None
    page = open_board(browser, tmp_path, payload)
    assert 'no signed tag' in page.inner_text('.topbar')
    page.close()
    for name, gate in (('team', 'strong'), ('solo', 'passed')):
        payload = payload_named(name)
        assert payload['gate']['gate'] == gate
        page = open_board(browser, tmp_path, payload)
        bar = page.inner_text('.topbar')
        assert 'no signed tag' not in bar, (name, bar)
        assert 'signed/' not in bar, (name, bar)
        assert 'gate: ' + gate in bar, (name, bar)
        page.close()


# purlin: purlin_report PROOF-62
def test_a_spec_that_names_no_files_says_so(browser, tmp_path):
    """The team fixture's invoice spec has no `> Scope:` line."""
    page = open_board(browser, tmp_path, payload_named('team'))
    names = dict(zip(feature_names(page), page.eval_on_selector_all(
        '.tr .name', 'els => els.map(e => Array.from(e.querySelectorAll('
        '".n, .ns")).map(s => s.textContent.trim()).join(" "))')))
    assert names['invoice'] == 'invoice \u00b7 no scope', names
    assert page.get_attribute('.tr[data-feature="invoice"] .ns',
                              'title') == 'no > Scope: line'
    assert names['login'] == 'login', names
    page.close()


# purlin: purlin_report PROOF-64
def test_no_proof_and_out_of_date_read_their_reasons(browser, tmp_path):
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    solo.click('[data-act="feature"][data-feature="login"]')
    solo.click('.rule[data-rule="RULE-3"]')
    passed = solo.evaluate(KV_ROWS)['Passed']
    assert passed.startswith('NO TEST') and 'no proof written' in passed
    assert 'No proof written.' in solo.inner_text('.wrap')
    solo.close()

    reg = open_board(browser, tmp_path / 'reg', payload_named('regulated'))
    reg.click('[data-act="feature"][data-feature="export"]')
    reg.click('.rule[data-feature="export"][data-rule="RULE-1"]')
    passed = reg.evaluate(KV_ROWS)['Passed']
    assert passed.startswith('OUT OF DATE'), passed
    assert 'code changed since 9f8e7d6' in passed
    reg.close()


# The words of a higher level than `passed`, which a project at that gate is
# never shown: the requirement names them, so the test does too.
HIGHER_WORDS = re.compile(
    r'\b(strong|signed|audit|queue|signature|level|hand check)', re.I)
# Proofs are optional at `passed`, so a project there that writes no proof
# line is not shown the word either.
HIGHER_WORDS_NO_PROOFS = re.compile(
    r'\b(strong|signed|audit|queue|signature|level|hand check|proof)', re.I)
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
    for label in chip_labels(page):
        page.click(chip_for(label))
        seen.extend(page.evaluate(SEEN))
        page.click(chip_for(label))
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


@pytest.mark.parametrize('proof_lines', (True, False))
@pytest.mark.parametrize('word', (None, 'failed', 'partial', 'not run',
                                  'out of date'))
# purlin: purlin_report PROOF-63
def test_the_passed_gate_shows_no_word_of_a_higher_level(browser, tmp_path,
                                                         word, proof_lines):
    payload = payload_named('solo')
    assert payload['gate']['gate'] == 'passed'
    if not proof_lines:
        payload = without_proof_lines(payload)
        assert payload['summary']['proofs'] == 0
    if word:
        cell = payload['features'][0]['rules'][0]['cells']['passed']
        cell['word'] = word
        cell['reasons'] = {'failed': ['failing: tests/test_login.py'],
                           'partial': ['passed on macos', 'linux: failed'],
                           'not run': ['linux: no run yet'],
                           'out of date': ['code changed since 9f8e7d6']}[word]
    page = open_board(browser, tmp_path, payload)
    seen, statuses = _walk_everything(page)
    page.close()
    words = HIGHER_WORDS if proof_lines else HIGHER_WORDS_NO_PROOFS
    found = sorted({match.group(0) for text in seen if text
                    for match in words.finditer(text)})
    assert found == [], found
    assert len(statuses) == 5, statuses
    assert all(status in STATUSES for status in statuses), statuses
    if word:
        assert statuses[0] == word, statuses


def _marked_project(root, passing):
    """A project at the gate `passed`: one rule, no proof line, one pytest
    test marked with the rule's own id, passing or failing as asked."""
    import suites
    (root / 'specs' / 'a').mkdir(parents=True)
    (root / 'tests').mkdir()
    (root / '.purlin').mkdir()
    (root / '.purlin' / 'config.json').write_text(json.dumps(
        {'gate': 'passed', 'tests': [suites.pytest_suite()]}),
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


@pytest.mark.parametrize('passing', (True, False))
# purlin: purlin_report PROOF-65
def test_a_rule_with_no_proof_shows_the_tests_marked_with_its_id(
        browser, tmp_path, passing):
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
    page.click('[data-act="feature"][data-feature="lock"]')
    page.click('.rule[data-feature="lock"][data-rule="RULE-1"]')
    lines = texts(page, '.tests p')
    seen = list(page.evaluate(SEEN))
    page.close()
    word = 'PASSED' if passing else 'FAILED'
    assert lines == ['tests/test_lock.py :: test_five_wrong_passwords_lock '
                     + word], lines
    found = sorted({match.group(0) for text in seen if text
                    for match in HIGHER_WORDS_NO_PROOFS.finditer(text)})
    assert found == [], found


# Every element that draws a text node of its own, its colour, the ground under
# it composited through each translucent background up to the page, and the
# WCAG contrast ratio of the two. Text in one of the four state colours or the
# accent, and text on a solid badge filled with a state colour, is left out:
# its colour is its meaning.
NEUTRAL_CONTRAST = """() => {
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
  const root = getComputedStyle(document.documentElement);
  const probe = document.createElement('span');
  document.body.appendChild(probe);
  const resolve = name => { probe.style.color = root.getPropertyValue(name).trim();
    return getComputedStyle(probe).color; };
  const states = new Set(['--state-pass', '--state-warn', '--state-fail',
    '--state-neutral'].map(resolve));
  const coloured = new Set([...states, resolve('--accent'),
    resolve('--text-accent')]);
  probe.remove();
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
    if (coloured.has(style.color)) { continue; }
    const under = ground(el);
    const fill = 'rgb(' + under.slice(0, 3).map(Math.round).join(', ') + ')';
    if (states.has(fill)) { continue; }
    let ink = parse(style.color);
    if (ink[3] < 1) { ink = over(ink, under); }
    out.push([node.textContent.trim().slice(0, 40), style.color, fill,
              ratio(ink, under)]);
  }
  return out;
}"""


def neutral_text(page):
    """`[(text, colour, ground, ratio)]` for every neutral text on screen."""
    return page.evaluate(NEUTRAL_CONTRAST)


def open_in_theme(browser, tmp_path, payload, theme):
    page = open_board(browser, tmp_path, payload)
    page.evaluate("t => { localStorage.setItem('purlin-theme', t); }", theme)
    page.reload()
    page.wait_for_selector('.topbar', timeout=10000)
    assert page.get_attribute('html', 'data-theme') == theme
    return page


# purlin: purlin_report PROOF-66
def test_neutral_text_measures_7_to_1_in_both_themes(browser, tmp_path):
    checked = 0
    for process in PROCESSES:
        payload = payload_named(process)
        for theme in ('dark', 'light'):
            for screen in ('board', 'queue', 'rule'):
                page = open_in_theme(browser, tmp_path / process, payload,
                                     theme)
                if screen == 'board':
                    # The first spec open, with its first rule's proofs
                    # open beneath it, so what they draw is measured too.
                    page.click('.tr')
                    page.click('[data-act="proofs"]')
                    assert page.query_selector('.rule-proofs'), process
                elif screen == 'queue':
                    if page.query_selector('[data-screen="queue"]') is None:
                        page.close()
                        continue
                    page.click('[data-screen="queue"]')
                elif screen == 'rule':
                    page.click('.tr')
                    page.click('.rule')
                    page.wait_for_selector('h1', timeout=10000)
                found = neutral_text(page)
                low = [item for item in found if item[3] < 7]
                assert low == [], (process, theme, screen, low)
                checked += len(found)
                page.close()
    assert checked > 100, checked

    page = open_in_theme(browser, tmp_path / 'old', payload_named('team'),
                         'dark')
    page.evaluate("document.documentElement.style.setProperty("
                  "'--state-idle', '#94A2B8')")
    assert [item for item in neutral_text(page) if item[3] < 7]
    page.close()


# purlin: purlin_report PROOF-67
def test_the_untested_tile_says_which_have_no_test_and_which_have_not_run(
        browser, tmp_path):
    payload = payload_named('regulated')
    words = iter(['no test', 'not run'])
    for feature in payload['features']:
        for rule in feature['rules']:
            if feature['name'] == 'invoice' and rule.get('label') == 'own' \
                    and rule['bucket'] != 'untested':
                word = next(words, None)
                if word is None:
                    continue
                rule['bucket'] = 'untested'
                rule['cells']['passed']['word'] = word
    page = open_board(browser, tmp_path, payload)
    title = page.eval_on_selector_all(
        '.tile', "els => els.filter(e => e.querySelector('.tile-l')"
        ".textContent === 'Untested').map(e => e.getAttribute('title'))")[0]
    assert title.split('\n') == [
        'No test, no current run, or no proof written.',
        'no test \u00b7 1', 'not run \u00b7 1', 'out of date \u00b7 1'], title
    page.close()


# ---------------------------------------------------------------------------
# A rule's proofs, under its row
# ---------------------------------------------------------------------------

# Each proofs button on the board: the rule it belongs to, the glyph, the
# count it reads, whether a screen reader is told it is open, and the colour
# the count is drawn in.
TOGGLES = """() => Array.from(document.querySelectorAll('[data-act="proofs"]')).map(
  b => ({rule: b.getAttribute('data-rule'), tag: b.tagName,
         glyph: b.firstChild.textContent,
         label: b.lastChild.textContent,
         open: b.getAttribute('aria-expanded'),
         colour: getComputedStyle(b.lastChild).color}))"""


def toggles(page):
    return {item['rule']: item for item in page.evaluate(TOGGLES)}


def resolved(page, token):
    """The computed colour a token resolves to on this page."""
    return page.evaluate(
        "n => { const s = document.createElement('span');"
        " s.style.color = getComputedStyle(document.documentElement)"
        ".getPropertyValue(n).trim(); document.body.appendChild(s);"
        " const v = getComputedStyle(s).color; s.remove(); return v; }", token)


def proof_lines(page, selector='.rule-proofs'):
    """What the open proofs beneath the rows read, one line per row."""
    return page.eval_on_selector_all(
        selector + ' .kv > *',
        r'els => els.map(e => e.textContent.trim().replace(/\s+/g, " "))')


def toggle_for(feature, rule):
    return '[data-act="proofs"][data-feature="%s"][data-rule="%s"]' % (
        feature, rule)


# purlin: purlin_report PROOF-68
def test_a_rules_proofs_open_beneath_its_row(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    found = toggles(page)
    assert [found[r]['label'] for r in ('RULE-1', 'RULE-2', 'RULE-3',
                                        'RULE-4')] == [
        '1 proof', '1 proof', '1 proof', '2 proofs'], found
    assert all(item['tag'] == 'BUTTON' and item['open'] == 'false'
               and item['glyph'] == '▶' for item in found.values())
    warn = resolved(page, '--state-warn')
    assert found['RULE-4']['colour'] == warn
    assert found['RULE-1']['colour'] != warn
    assert 'no cookie is set' not in page.inner_text('.wrap')

    page.focus(toggle_for('login', 'RULE-4'))
    page.keyboard.press('Enter')
    found = toggles(page)
    assert found['RULE-4']['open'] == 'true', found['RULE-4']
    assert found['RULE-4']['glyph'] == '▼'
    assert found['RULE-1']['open'] == 'false'
    assert page.query_selector('h1') is None, 'the board is still showing'
    assert proof_lines(page) == [
        'PROOF-4',
        'On Windows, open http://localhost/session and read that no cookie '
        'is set.',
        'Result', 'FAILED', 'Tags', '@env(windows)',
        'Tests', 'tests/test_login.py :: test_no_cookie FAILED',
        'PROOF-5',
        'Read the Set-Cookie header of a 200 response and verify it carries '
        'Secure.',
        'Result', 'PASSED',
        'Tests', 'tests/test_login.py :: test_secure_flag PASSED']
    # The keyboard keeps its place on the button it pressed.
    assert page.evaluate(
        "document.activeElement.getAttribute('data-rule')") == 'RULE-4'
    page.keyboard.press('Enter')
    assert proof_lines(page) == []

    page.click(toggle_for('login', 'RULE-4'))
    assert proof_lines(page) != []
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('[data-act="feature"][data-feature="login"]')
    assert proof_lines(page) == []
    assert toggles(page)['RULE-4']['open'] == 'false'
    page.close()


# purlin: purlin_report PROOF-69
def test_a_rule_with_no_test_or_no_proof_says_so_under_its_row(browser,
                                                               tmp_path):
    payload = payload_named('solo')
    login = payload['features'][0]
    login['rules'][2]['tests'] = [{'file': 'tests/test_login.py',
                                   'name': 'test_locks', 'result': 'pass'}]
    page = open_board(browser, tmp_path / 'solo', payload)
    page.click('[data-act="feature"][data-feature="login"]')
    found = toggles(page)
    assert found['RULE-2']['label'] == '1 proof'
    assert found['RULE-2']['colour'] == resolved(page, '--state-warn')
    assert found['RULE-3']['label'] == 'no proof'
    page.click(toggle_for('login', 'RULE-2'))
    assert proof_lines(page) == [
        'PROOF-2', login['rules'][1]['proofs'][0]['text'], 'Result',
        'NO TEST', 'Tests', 'No test yet.']
    page.click(toggle_for('login', 'RULE-2'))
    page.click(toggle_for('login', 'RULE-3'))
    assert proof_lines(page) == [
        'Tests', 'tests/test_login.py :: test_locks PASSED']
    page.close()

    bare = open_board(browser, tmp_path / 'bare',
                      without_proof_lines(payload_named('solo')))
    bare.click('[data-act="feature"][data-feature="login"]')
    found = toggles(bare)
    assert not [item for item in found.values() if 'proof' in item['label']]
    assert found['RULE-1']['label'] == '1 test'
    assert 'RULE-3' not in found
    bare.close()


# purlin: purlin_report PROOF-70
def test_a_filter_hides_a_rules_proofs_and_the_rule_screen_agrees(browser,
                                                                   tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click(toggle_for('login', 'RULE-4'))
    board = proof_lines(page)
    page.click(chip_for('Partial'))
    assert 'PROOF-4' in proof_lines(page)
    page.click(chip_for('Partial'))
    page.click(chip_for('Stale'))
    assert rule_ids(page) == ['RULE-2']
    assert proof_lines(page) == []
    page.click(chip_for('Stale'))
    page.click('.rule[data-feature="login"][data-rule="RULE-4"]')
    screen = page.eval_on_selector_all(
        'section .stack .panel .kv > *',
        r'els => els.map(e => e.textContent.trim().replace(/\s+/g, " "))')
    assert screen == board, (screen, board)
    page.close()


# purlin: purlin_report PROOF-71
def test_a_shared_rule_is_listed_once_under_its_owner(browser, tmp_path):
    payload = payload_named('team')
    page = open_board(browser, tmp_path, payload)
    cells = count_cells(page)
    assert cells['receipt']['Rules'] == '1 · plus 1 shared'
    assert cells['login']['Rules'] == '3'
    assert hovers(page)['receipt']['Rules'] == 'checkout_design · 1'
    assert '4 of 7' in page.inner_text('.topbar')
    for name in feature_names(page):
        page.click('[data-act="feature"][data-feature="%s"]' % name)
    assert texts(page, '.rule[data-feature="receipt"] .rid') == ['RULE-1']
    anchor = 'The cart page shows the order total above the pay button.'
    assert texts(page, '.rule .rt').count(anchor) == 1
    assert texts(page, '.rule[data-feature="checkout_design"] .rt') == [anchor]

    page.click('.rule[data-feature="receipt"][data-rule="RULE-1"]')
    assert texts(page, '.tabs button')[-1] == 'receipt RULE-1'
    assert 'A receipt names the order number and the total paid.' in (
        page.inner_text('.wrap'))
    assert anchor not in page.inner_text('.wrap')
    page.click('[data-act="close"]')
    page.click('.rule[data-feature="checkout_design"][data-rule="RULE-1"]')
    assert texts(page, '.tabs button')[-1] == 'checkout_design RULE-1'
    assert anchor in page.inner_text('.wrap')
    assert 'A receipt names' not in page.inner_text('.wrap')
    page.close()


def _shared_project(root):
    """A project at the gate `passed`: a global anchor `security` of six
    rules and a feature `lock` of two, each rule with one proof and one
    passing pytest test marked with it."""
    import suites
    (root / 'specs' / '_anchors').mkdir(parents=True)
    (root / 'specs' / 'a').mkdir(parents=True)
    (root / 'tests').mkdir()
    (root / '.purlin').mkdir()
    (root / '.purlin' / 'config.json').write_text(json.dumps(
        {'gate': 'passed', 'tests': [suites.pytest_suite()]}),
        encoding='utf-8')
    (root / 'specs' / '_anchors' / 'security.md').write_text(
        '# Anchor: security\n\n> Global: true\n\n## Rules\n\n'
        + ''.join('- RULE-%d: Security pattern %d is absent\n' % (n, n)
                  for n in range(1, 7))
        + '\n## Proof\n\n'
        + ''.join('- PROOF-%d (RULE-%d): Grep for pattern %d; verify 0 '
                  'matches\n' % (n, n, n) for n in range(1, 7)),
        encoding='utf-8')
    (root / 'specs' / 'a' / 'lock.md').write_text(
        '# Feature: lock\n\n> Scope: tests/\n\n## Rules\n\n'
        '- RULE-1: A wrong password five times locks the account\n'
        '- RULE-2: A locked account opens again after fifteen minutes\n\n'
        '## Proof\n\n'
        '- PROOF-1 (RULE-1): Sign in wrong five times; verify 423\n'
        '- PROOF-2 (RULE-2): Wait fifteen minutes; verify 200\n',
        encoding='utf-8')
    (root / 'tests' / 'test_shared.py').write_text(
        ''.join('# purlin: %s PROOF-%d\ndef test_%s_%d():\n    assert True\n\n'
                % (feature, n, feature, n)
                for feature, count in (('lock', 2), ('security', 6))
                for n in range(1, count + 1)),
        encoding='utf-8')


# purlin: purlin_report PROOF-72
def test_a_real_projects_shared_rules_are_listed_once(browser, tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    _shared_project(root)
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, 'scripts', 'run', 'purlin_run.py'),
         '--test', '--project-root', str(root)],
        capture_output=True, encoding='utf-8', cwd=str(root))
    assert 'Markers: 8 tied to a test, 0 not tied.' in result.stdout, (
        result.stdout + result.stderr)
    sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
    from purlin import report_data
    assert report_data.refresh(str(root))
    text = read(os.path.join(str(root), '.purlin', 'report-data.js'))
    payload = json.loads(
        text[len('const PURLIN_DATA = '):].rstrip().rstrip(';'))
    lock = next(f for f in payload['features'] if f['name'] == 'lock')
    assert [(r['feature'], r['label']) for r in lock['rules']] == (
        [('lock', 'own')] * 2 + [('security', 'global')] * 6)

    page = open_board(browser, tmp_path / 'page', payload)
    assert count_cells(page)['lock']['Rules'] == '2 · plus 6 shared'
    assert hovers(page)['lock']['Rules'] == 'security · 6'
    assert 'of 8' in page.inner_text('.topbar')
    assert sum(int(value) for value in texts(page, '.tile-v')) == 8
    page.click('[data-act="feature"][data-feature="lock"]')
    assert rule_ids(page) == ['RULE-1', 'RULE-2']
    page.click('[data-act="feature"][data-feature="security"]')
    assert len(rule_ids(page)) == 8
    assert texts(page, '.rule[data-feature="security"] .rid') == [
        'RULE-%d' % n for n in range(1, 7)]
    page.click('.rule[data-feature="lock"][data-rule="RULE-1"]')
    own = page.inner_text('.wrap')
    page.click('[data-act="close"]')
    page.click('.rule[data-feature="security"][data-rule="RULE-1"]')
    shared = page.inner_text('.wrap')
    page.close()
    assert 'A wrong password five times locks the account' in own
    assert 'Security pattern 1 is absent' not in own
    assert 'Security pattern 1 is absent' in shared
    assert 'A wrong password' not in shared


# The badges each open rule row draws, keyed by the rule's id.
ROW_PILLS = """els => Object.fromEntries(els.map(e => [
  e.querySelector('.rid').textContent.trim(),
  Array.from(e.querySelectorAll('.rp .pill')).map(p => p.textContent.trim())]))"""


def _levels_payload():
    """A project at the gate `signed` holding a rule at each level, a rule at
    `passed` and one at `strong` whose tests fail, and a second spec whose one
    rule is marked `[level: passed]`, as the payload builder writes it."""
    from test_mcp_server import ONE_PASSED_SPEC, _levels_project
    made = _levels_project()
    try:
        made.spec(ONE_PASSED_SPEC, name='notes', category='notes')
        return made.payload()
    finally:
        made.close()


# purlin: purlin_report PROOF-73
def test_a_rule_row_draws_only_the_badges_its_level_asks_for(browser,
                                                             tmp_path):
    page = open_board(browser, tmp_path, _levels_payload())
    cells = count_cells(page)
    assert (cells['login']['Strong'], cells['login']['Signed']) == (
        '2 of 3 · 90%', '0 of 1'), cells['login']
    assert (cells['notes']['Strong'], cells['notes']['Signed']) == (
        '', ''), cells['notes']
    counts = chip_counts(page)
    assert (counts['Weak'], counts['Not audited']) == (1, 0), counts
    tiles = dict(zip(texts(page, '.tile-l'), texts(page, '.tile-v')))
    assert (tiles['Strong'], tiles['Signed']) == ('2', '0'), tiles
    page.click('[data-act="feature"][data-feature="login"]')
    pills = page.eval_on_selector_all('.rule', ROW_PILLS)
    assert pills == {'RULE-1': ['PASSED'],
                     'RULE-2': ['PASSED', 'STRONG'],
                     'RULE-3': ['PASSED', 'STRONG', 'UNSIGNED'],
                     'RULE-4': ['FAILED'],
                     'RULE-5': ['FAILED', 'WEAK']}, pills
    page.close()


# purlin: purlin_report PROOF-74
def test_a_rule_screen_shows_only_what_its_level_asks_for(browser, tmp_path):
    page = open_board(browser, tmp_path, _levels_payload())
    page.click('[data-act="feature"][data-feature="login"]')
    seen = {}
    for rule_id in ('RULE-1', 'RULE-2', 'RULE-3', 'RULE-4'):
        page.click('.rule[data-feature="login"][data-rule="%s"]' % rule_id)
        seen[rule_id] = (list(page.evaluate(KV_ROWS))[:3], panel_heads(page),
                         'purlin:sign' in page.inner_text('.wrap'))
        page.click('[data-act="close"]')
    page.close()
    assert seen['RULE-1'] == (['Passed', 'Level', 'Spec'], [], False), seen
    assert seen['RULE-2'] == (['Passed', 'Strong', 'Level'], ['Audit'],
                              False), seen
    assert seen['RULE-3'] == (['Passed', 'Strong', 'Signed'],
                              ['Audit', 'Signature'], True), seen
    assert seen['RULE-4'] == (['Passed', 'Level', 'Spec'], [], False), seen
