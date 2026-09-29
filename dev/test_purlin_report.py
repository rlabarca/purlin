"""The board page: how it is built, and what it shows.

Two halves. The first reads the built file as text and holds it to the design
system: one token block, no colour written anywhere else, no shadow, no
gradient, no emoji, no request to anything outside the file. The second opens
it in a headless browser over `file://` with a fixture payload beside it, one
fixture per process, and reads what a person would see.

The fixtures under `dev/fixtures/report/` are payloads at schema 10, one for
each of the three processes: solo at the `passed` gate, team at `strong` with
strength and one rule the AI audit could not decide, regulated at `signed`
with a signed rule, a signature that no longer matches, a rule whose audit
found a gap, a rule no audit has run on, a rule to test by hand, and a rule
that passed on one system and failed on another.

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


def with_invoice_rule_2_unproved(payload):
    """The team payload with invoice `RULE-2`'s one proof taken out.

    From `strong` up every rule needs a proof, so the payload gives the rule
    the kind `no_proof`, the first kind of what is left to do, and its line
    of what is left moves from `to write a test for` to that kind.
    """
    invoice = next(f for f in payload['features'] if f['name'] == 'invoice')
    rule = next(r for r in invoice['rules'] if r['id'] == 'RULE-2')
    assert rule['left'] == 'no_test'
    rule['proofs'] = []
    rule['left'] = 'no_proof'
    assert payload['left'][0]['kind'] == 'no_test'
    payload['left'][0] = {'kind': 'no_proof', 'count': 1,
                          'text': '1 rule to write a proof for',
                          'command': 'purlin:spec'}
    return payload


def with_only_the_version_left(payload):
    """The payload with its one line of what is left the version to tag."""
    payload['left'] = [{'kind': 'to_tag', 'count': 1,
                        'text': 'the version to tag', 'command': 'purlin:sign'}]
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


# The kind of work each filter button stands for, by the name it reads.
KINDS = {'To fix': 'to_fix', 'To test': 'to_test',
         'To test by hand': 'to_test_by_hand', 'To audit': 'to_audit',
         'To strengthen': 'to_strengthen', 'To sign': 'to_sign',
         'To write a test for': 'no_test', 'To write a proof for': 'no_proof',
         'To tag': 'to_tag'}


def chip_for(label):
    return '.chip[data-filter="%s"]' % KINDS[label]


def pressed(page):
    """The labels of the filter buttons that read as pressed."""
    return page.eval_on_selector_all(
        '.chip[aria-pressed="true"]',
        'els => els.map(e => e.firstChild.textContent.trim())')


def head_labels(page):
    """The spec table's column headings, in the order they are drawn."""
    return texts(page, '.th > div')


def open_rule(page, feature, rule_id):
    """Open a spec on the board and then one of its rules' screens."""
    page.click('[data-act="feature"][data-feature="%s"]' % feature)
    page.click('.rule[data-feature="%s"][data-rule="%s"]' % (feature, rule_id))


# How many boxes the strip carries at each gate: one per step the gate
# reaches, and from `strong` up the `No proof` box.
TILES = {'solo': 1, 'team': 3, 'regulated': 4}


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


# purlin: purlin_report PROOF-122
def test_the_page_at_the_project_root_is_the_built_page(page_text):
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
def test_no_shadow_no_gradient_and_no_emoji(page_text):
    _inside, outside = token_block(page_text)
    assert 'box-shadow' not in outside
    assert 'gradient' not in page_text
    assert not re.search(u'[\U0001F300-\U0001FAFF☀-➿]', page_text)


# purlin: purlin_report PROOF-5
def test_no_request_to_anything_outside_the_page(page_text):
    """The page opens from a disk with no network behind it."""
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

# purlin: purlin_report PROOF-7
def test_the_board_opens_on_the_boxes_under_the_gate(browser, tmp_path):
    payload = payload_named('regulated')
    page = open_board(browser, tmp_path, payload)
    bar = page.inner_text('.topbar')
    assert texts(page, '.topbar .tag')[0] == 'gate: signed', bar
    assert 'Data:' in bar
    first = page.evaluate(
        "() => { const s = document.querySelector('.strip');"
        " const sec = s.closest('section');"
        " return sec.parentElement.querySelector('section') === sec; }")
    assert first, 'the board does not open on the boxes'
    assert set(feature_names(page)) == set(
        f['name'] for f in payload['features'])
    assert len(feature_names(page)) == 4
    page.close()


BASE_COLUMNS = ['Spec', 'Rules', 'Proofs', 'Tests']


def headings_of(browser, tmp_path, payload):
    page = open_board(browser, tmp_path, payload)
    found = head_labels(page)
    page.close()
    return found


# purlin: purlin_report PROOF-9
def test_a_passed_project_with_proof_lines_shows_four_columns(browser,
                                                             tmp_path):
    assert headings_of(browser, tmp_path, payload_named('solo')) == \
        BASE_COLUMNS


# purlin: purlin_report PROOF-123
def test_a_passed_project_with_no_proof_line_shows_no_proofs_column(
        browser, tmp_path):
    """Proofs are optional at `passed`: a project there that writes none is
    shown no column for them."""
    assert headings_of(browser, tmp_path, without_proof_lines(
        payload_named('solo'))) == ['Spec', 'Rules', 'Tests']


# purlin: purlin_report PROOF-124
def test_a_strong_project_adds_the_strong_column(browser, tmp_path):
    assert headings_of(browser, tmp_path, payload_named('team')) == \
        BASE_COLUMNS + ['Strong']


# purlin: purlin_report PROOF-125
def test_a_strong_project_keeps_proofs_with_no_proof_line(browser, tmp_path):
    """From `strong` up every rule needs a proof, so the column stays."""
    assert headings_of(browser, tmp_path, without_proof_lines(
        payload_named('team'))) == BASE_COLUMNS + ['Strong']


# purlin: purlin_report PROOF-126
def test_a_signed_project_shows_six_columns(browser, tmp_path):
    found = headings_of(browser, tmp_path, payload_named('regulated'))
    assert found == BASE_COLUMNS + ['Strong', 'Signed']
    assert len(found) == 6


# purlin: purlin_report PROOF-32
def test_the_rule_screen_says_what_each_system_found(browser, tmp_path):
    """A rule can pass on one operating system and fail on another.

    The systems are the rule's business, so they live on its screen, drawn
    from the platforms its passed cell carries, in the payload's words.
    """
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-4')
    found = page.evaluate(PLATFORM_BOXES)
    assert [b['os'] for b in found] == ['Lin', 'Win']
    assert [b['tone'] for b in found] == ['pass', 'fail']
    assert found[0]['colour'] == page.evaluate(RESOLVE_TOKEN, '--state-pass')
    assert found[1]['colour'] == page.evaluate(RESOLVE_TOKEN, '--state-fail')
    assert found[1]['title'].startswith('Windows · failed · ci · ')
    last = page.inner_text('.kv').splitlines()
    assert any(line.startswith('ci · ') and 'old' in line for line in last)
    page.close()


# purlin: purlin_report PROOF-91
def test_a_rule_that_ran_on_linux_and_macos_shows_both(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'invoice', 'RULE-1')
    assert [b['os'] for b in page.evaluate(PLATFORM_BOXES)] == ['Lin', 'Mac']
    page.close()


# purlin: purlin_report PROOF-92
def test_a_rule_that_ran_nowhere_shows_no_system(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'invoice', 'RULE-3')
    assert page.evaluate(PLATFORM_BOXES) == []
    page.close()


# purlin: purlin_report PROOF-93
def test_the_board_draws_no_system_box(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    assert len(rule_ids(page)) == 4
    assert page.query_selector_all('.wrap .os') == []
    page.close()


@pytest.mark.parametrize('process', PROCESSES)
# purlin: purlin_report PROOF-12
def test_the_board_opens_in_the_dark_theme(browser, tmp_path, process):
    page = open_board(browser, tmp_path, payload_named(process))
    assert page.get_attribute('html', 'data-theme') == 'dark'
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


@pytest.mark.parametrize('process', PROCESSES)
# purlin: purlin_report PROOF-129
def test_the_theme_button_swaps_back_to_dark(browser, tmp_path, process):
    page = open_board(browser, tmp_path, payload_named(process))
    _dark_then_toggled(page)
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


# ---------------------------------------------------------------------------
# The step boxes
# ---------------------------------------------------------------------------

# purlin: purlin_report PROOF-8
def test_a_step_box_counts_the_rules_that_reached_it(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['summary']['steps'] == {'passed': 7, 'strong': 2,
                                           'signed': 1}
    page = open_board(browser, tmp_path, payload)
    found = boxes(page)
    assert [(label, count) for label, count, _ in found] == [
        ('Passing', '7'), ('Strong', '2'), ('Signed', '1'),
        ('No proof', '0')], found
    assert page.eval_on_selector(
        '.tile-l', 'el => getComputedStyle(el).textTransform') == 'uppercase'
    warn = page.evaluate(RESOLVE_TOKEN, '--state-warn')
    assert [colour for _, _, colour in found[:3]] == [warn] * 3, found
    page.close()


# purlin: purlin_report PROOF-80
def test_the_passed_gate_has_one_box(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('solo'))
    assert [(label, count) for label, count, _ in boxes(page)] == [
        ('Passing', '3')]
    page.close()


# purlin: purlin_report PROOF-81
def test_a_step_every_rule_reached_is_green(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['summary']['rules'] == 10
    payload['summary']['steps'] = {'passed': 10, 'strong': 10, 'signed': 10}
    page = open_board(browser, tmp_path, payload)
    found = boxes(page)[:3]
    passed = page.evaluate(RESOLVE_TOKEN, '--state-pass')
    assert [(count, colour) for _, count, colour in found] == [
        ('10', passed)] * 3, found
    page.close()


# purlin: purlin_report PROOF-121
def test_the_summary_sentence_stands_above_the_boxes(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    above = page.evaluate(
        "() => { const s = document.querySelector('.sentence');"
        " const box = document.querySelector('.tile');"
        " return [s.innerText, !!(s.compareDocumentPosition(box)"
        " & Node.DOCUMENT_POSITION_FOLLOWING)]; }")
    assert above == ['10 rules. 7 pass their tests. 2 are strong. 1 is signed.',
                     True], above
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
    assert cells['login']['Strong'] == '2 of 4 · 86%'
    assert cells['login']['Signed'] == '1 of 4'
    # One of export's two rules is behind changed code: it passed nothing
    # and failed nothing, so the share alone reads it.
    assert cells['export']['Tests'] == '1 of 2'
    # invoice's third proof is `@manual`, which declares that no test is
    # written for it, so the rollup counts no gap and the cell reads the
    # total alone.
    assert cells['invoice']['Proofs'] == '3'
    page.close()


# purlin: purlin_report PROOF-84
def test_a_proof_no_test_runs_is_named_beside_the_total(browser, tmp_path):
    team = open_board(browser, tmp_path, payload_named('team'))
    assert count_cells(team)['invoice']['Proofs'] == (
        '2 · 1 no test')
    team.close()


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
    assert len(strong) == 2, strong
    assert strong[0].startswith('audit · ci · ')
    assert strong[1] == 'minimum strength 80%'
    assert login['Signed'] == 'jane@acme.com · 2026-09-12'


# purlin: purlin_report PROOF-97
def test_a_proofs_hover_names_the_proof_no_test_runs(browser, tmp_path):
    team = open_board(browser, tmp_path, payload_named('team'))
    assert hovers(team)['invoice']['Proofs'] == 'no test · PROOF-2'
    team.close()


def box_hovers(page):
    """Each box's label and the hover it carries."""
    return dict(page.eval_on_selector_all(
        '.tile', "els => els.map(e => [e.querySelector('.tile-l')"
        ".textContent.trim(), e.getAttribute('title')])"))


# purlin: purlin_report PROOF-45
def test_every_step_box_carries_its_hover(browser, tmp_path):
    """A box says for the project what its column says for one spec."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    titles = box_hovers(page)
    page.close()
    assert titles['Passing'].split('\n')[0].startswith(
        'Windows · ci · '), titles
    assert titles['Strong'].split('\n')[0].startswith(
        'audit · ci · '), titles
    assert titles['Signed'].split('\n')[0] == (
        'jane@acme.com · 2026-09-12'), titles


# purlin: purlin_report PROOF-98
def test_the_no_proof_box_names_the_specs_it_counts(browser, tmp_path):
    page = open_board(browser, tmp_path,
                      with_invoice_rule_2_unproved(payload_named('team')))
    assert box_hovers(page)['No proof'] == 'invoice · 1'
    page.close()


# purlin: purlin_report PROOF-114
def test_a_rule_with_no_proof_is_counted_in_its_own_box(browser, tmp_path):
    page = open_board(browser, tmp_path,
                      with_invoice_rule_2_unproved(payload_named('team')))
    found = boxes(page)
    assert [label for label, _, _ in found] == ['Passing', 'Strong',
                                                'No proof'], found
    assert found[-1][1:] == ['1', page.evaluate(RESOLVE_TOKEN,
                                                '--state-warn')], found
    page.close()


# purlin: purlin_report PROOF-115
def test_the_no_proof_box_at_zero_is_green(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('team'))
    found = boxes(page)
    assert found[-1] == ['No proof', '0',
                         page.evaluate(RESOLVE_TOKEN, '--state-pass')], found
    page.close()


# purlin: purlin_report PROOF-116
def test_the_write_a_proof_filter_leaves_the_rules_with_no_proof(browser,
                                                                 tmp_path):
    page = open_board(browser, tmp_path,
                      with_invoice_rule_2_unproved(payload_named('team')))
    page.click(chip_for('To write a proof for'))
    assert feature_names(page) == ['invoice']
    page.click('[data-act="feature"][data-feature="invoice"]')
    assert rule_ids(page) == ['RULE-2']
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
                     '▼ BILLING 2 specs 4 of 5 rules pass',
                     '▼ _ANCHORS 1 spec 1 of 1 rule passes']
    page.close()


# Each band's two ends and its bar: where each sits, and how wide the bar is.
BAND_ENDS = r"""els => els.map(e => {
  const l = e.querySelector('.gl').getBoundingClientRect();
  const r = e.querySelector('.gr').getBoundingClientRect();
  const bar = e.querySelector('.bar').getBoundingClientRect();
  const gap = e.querySelector('.gs').getBoundingClientRect().left
    - e.querySelector('.gt').getBoundingClientRect().right;
  return {sameLine: Math.abs(l.top - r.top) < 4, rightEdge: r.right,
          boxRight: e.getBoundingClientRect().right, leftOfRight: r.left,
          leftOfLeft: l.left, barWidth: bar.width, barRight: bar.right,
          gap: gap, count: parseInt(e.querySelector('.gc b').textContent
            .split(' of ')[1], 10)};
})"""


# purlin: purlin_report PROOF-77
def test_a_band_has_two_ends_on_one_line(browser, tmp_path):
    payload = payload_named('regulated')
    page = open_board(browser, tmp_path, payload,
                      viewport={'width': 1500, 'height': 900})
    ends = page.eval_on_selector_all('.group', BAND_ENDS)
    page.close()
    assert sum(end['count'] for end in ends) == payload['summary']['rules']
    assert payload['summary']['rules'] == 10
    for end in ends:
        assert end['sameLine'], end
        assert abs(end['boxRight'] - end['rightEdge']) <= 40, end
        assert end['gap'] >= 16, end
        assert end['barWidth'] == ends[0]['barWidth'], ends
        assert abs(end['barRight'] - ends[0]['barRight']) < 1, ends


# purlin: purlin_report PROOF-94
def test_a_band_counts_a_shared_rule_once(browser, tmp_path):
    payload = payload_named('team')
    page = open_board(browser, tmp_path, payload,
                      viewport={'width': 1500, 'height': 900})
    ends = page.eval_on_selector_all('.group', BAND_ENDS)
    page.close()
    assert payload['summary']['rules'] == 7
    assert sum(end['count'] for end in ends) == 7, ends


# purlin: purlin_report PROOF-95
def test_a_narrow_band_puts_its_count_beneath_its_name(browser, tmp_path):
    narrow = open_board(browser, tmp_path, payload_named('regulated'),
                        viewport={'width': 390, 'height': 900})
    for end in narrow.eval_on_selector_all('.group', BAND_ENDS):
        assert not end['sameLine'], end
        assert abs(end['leftOfRight'] - end['leftOfLeft']) < 2, end
    narrow.close()


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


# purlin: purlin_report PROOF-143
def test_a_folded_band_opens_again_on_space(browser, tmp_path):
    narrow = _auth_band_closed_by_enter(browser, tmp_path)
    narrow.keyboard.press(' ')
    assert narrow.get_attribute(AUTH_BAND, 'aria-expanded') == 'true'
    narrow.close()


# purlin: purlin_report PROOF-10
def test_a_feature_row_expands_to_its_rules(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert rule_ids(page) == []
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4']
    assert 'SIGNED' in page.inner_text('.rule')
    page.close()


# purlin: purlin_report PROOF-127
def test_an_open_feature_row_closes_on_the_next_press(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page)
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == []
    page.close()


# purlin: purlin_report PROOF-117
def test_an_open_spec_shows_its_description(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    after = page.eval_on_selector(
        '.tr[data-feature="login"]',
        "el => { const d = el.nextElementSibling; return [d.className,"
        " d.textContent.trim(), d.nextElementSibling.getAttribute('data-rule')];"
        " }")
    page.close()
    assert after == ['desc', 'Signing in with an email address and a '
                     'password, and locking an account after repeated '
                     'failures.', 'RULE-1'], after


# purlin: purlin_report PROOF-118
def test_a_spec_with_no_description_shows_none(browser, tmp_path):
    payload = payload_named('regulated')
    assert next(f for f in payload['features']
                if f['name'] == 'checkout_design')['description'] is None
    page = open_board(browser, tmp_path, payload)
    page.click('[data-act="feature"][data-feature="checkout_design"]')
    after = page.eval_on_selector(
        '.tr[data-feature="checkout_design"]',
        'el => el.nextElementSibling.className')
    page.close()
    assert after == 'rule', after


# purlin: purlin_report PROOF-13
def test_to_strengthen_leaves_the_rules_to_strengthen(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click(chip_for('To strengthen'))
    assert page.get_attribute(chip_for('To strengthen'),
                              'aria-pressed') == 'true'
    assert feature_names(page) == ['login', 'invoice', 'checkout_design']
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == ['RULE-3']
    page.close()


# purlin: purlin_report PROOF-85
def test_to_audit_leaves_the_rules_to_audit(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click(chip_for('To audit'))
    assert feature_names(page) == ['export']
    page.click('[data-act="feature"][data-feature="export"]')
    assert rule_ids(page) == ['RULE-2']
    page.close()


# purlin: purlin_report PROOF-14
def test_choosing_another_button_moves_the_choice(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click(chip_for('To strengthen'))
    page.click(chip_for('To audit'))
    assert pressed(page) == ['To audit']
    assert feature_names(page) == ['export']
    page.close()


# purlin: purlin_report PROOF-87
def test_choosing_the_chosen_button_again_shows_every_rule(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click(chip_for('To strengthen'))
    page.click(chip_for('To strengthen'))
    assert pressed(page) == []
    assert len(feature_names(page)) == 4
    page.close()


# purlin: purlin_report PROOF-133
def test_choosing_to_tag_leaves_every_rule_showing(browser, tmp_path):
    page = open_board(browser, tmp_path,
                      with_only_the_version_left(payload_named('regulated')))
    page.click(chip_for('To tag'))
    assert pressed(page) == ['To tag']
    assert len(feature_names(page)) == 4
    page.close()


# purlin: purlin_report PROOF-35
def test_the_buttons_are_the_lines_of_what_is_left(browser, tmp_path):
    reg = open_board(browser, tmp_path, payload_named('regulated'))
    assert chip_labels(reg) == ['To fix', 'To test', 'To test by hand',
                                'To audit', 'To strengthen', 'To sign']
    assert [int(value) for value in texts(reg, '.chip b')] == [
        1, 1, 1, 1, 4, 1]
    reg.close()


# purlin: purlin_report PROOF-86
def test_the_passed_gate_offers_its_one_line_as_a_button(browser, tmp_path):
    payload = payload_named('solo')
    assert [item['text'] for item in payload['left']] == [
        '2 rules to write a test for']
    solo = open_board(browser, tmp_path, payload)
    assert chip_counts(solo) == {'To write a test for': 2}
    solo.close()


# purlin: purlin_report PROOF-130
def test_a_buttons_count_is_the_payloads_not_the_pages(browser, tmp_path):
    payload = payload_named('regulated')
    line = next(item for item in payload['left'] if item['kind'] == 'to_audit')
    line['count'] = 9
    assert sum(rule['left'] == 'to_audit' for feature in payload['features']
               for rule in feature['rules']) == 1
    page = open_board(browser, tmp_path, payload)
    assert chip_counts(page)['To audit'] == 9
    page.close()


# purlin: purlin_report PROOF-131
def test_the_version_to_tag_reads_to_tag(browser, tmp_path):
    page = open_board(browser, tmp_path,
                      with_only_the_version_left(payload_named('regulated')))
    assert chip_counts(page) == {'To tag': 1}
    page.close()


# purlin: purlin_report PROOF-83
def test_with_nothing_left_the_last_line_stands_above_the_table(browser,
                                                                tmp_path):
    payload = payload_named('team')
    payload['left'] = []
    payload['last_line'] = 'Nothing left to do.'
    page = open_board(browser, tmp_path, payload)
    assert page.query_selector_all('.chip') == []
    found = page.evaluate(
        "() => { const line = Array.from(document.querySelectorAll('p')).find("
        "p => p.textContent.trim() === 'Nothing left to do.');"
        " const table = document.querySelector('.tbl');"
        " return !!line && !!(line.compareDocumentPosition(table)"
        " & Node.DOCUMENT_POSITION_FOLLOWING); }")
    assert found, 'the last line is not above the table'
    page.close()


# purlin: purlin_report PROOF-46
def test_a_button_leaves_as_many_rules_as_its_count(browser, tmp_path):
    """The number on the button is the number of rules it leaves."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    for name in feature_names(page):
        page.click('[data-act="feature"][data-feature="%s"]' % name)
    counts = chip_counts(page)
    assert len(counts) == 6, counts
    for label, count in counts.items():
        page.click(chip_for(label))
        assert len(page.query_selector_all('.rule')) == count, label
        page.click(chip_for(label))
    page.close()


# The line under the buttons that names the command, or None.
COMMAND_LINE = """() => { const line = document.querySelector('.cmdline');
  return line ? line.textContent.trim().replace(/\\s+/g, ' ') : null; }"""


# purlin: purlin_report PROOF-119
def test_a_chosen_button_names_its_command(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click(chip_for('To audit'))
    assert page.evaluate(COMMAND_LINE) == 'Type purlin:audit in Claude Code.'
    assert 'courier' in page.eval_on_selector(
        '.cmdline .cmd', 'el => getComputedStyle(el).fontFamily').lower()
    page.close()


# purlin: purlin_report PROOF-120
def test_the_command_line_is_text(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click(chip_for('To fix'))
    assert page.query_selector_all('.cmdline button') == []
    assert page.query_selector_all('.cmdline input') == []
    before = page.inner_text('body')
    page.click('.cmdline')
    assert page.inner_text('body') == before
    page.close()


# purlin: purlin_report PROOF-134
def test_with_no_button_chosen_no_command_line_shows(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert page.evaluate(COMMAND_LINE) is None
    assert 'Type ' not in page.inner_text('.wrap')
    page.close()


# purlin: purlin_report PROOF-15
def test_the_rule_screen_shows_proof_test_and_evidence(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-1')
    body = page.inner_text('.wrap')
    assert 'RULE-1' in page.inner_text('h1')
    assert 'A person signs in with an email address and a password.' in body
    assert 'PROOF-1' in body
    assert 'tests/test_login.py :: test_sign_in' in body
    assert 'PASSED' in body and 'STRONG' in body and 'SIGNED' in body
    # The signer is named once: the cell's own `by <signer>` reason would
    # have said it again beside the date.
    assert 'SIGNED jane@acme.com · 2026-09-12' in page.eval_on_selector_all(
        '.kv dd', r'els => els.map(e => e.innerText.trim().replace(/\s+/g, " "))')
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
def test_the_rule_screen_has_one_row_per_cell_the_gate_reaches(browser,
                                                               tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-1')
    # The whole row set, so a row the model dropped cannot come back.
    assert list(page.evaluate(KV_ROWS)) == [
        'Passed', 'Strong', 'Signed', 'Spec', 'Last run', 'Signatures']
    page.close()


# purlin: purlin_report PROOF-16
def test_the_rule_screen_links_to_the_git_host(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-1')
    href = page.get_attribute('a[href*="specs/auth/login.md"]', 'href')
    assert href.startswith('https://github.com/acme/ledger/blob/')
    assert page.query_selector('a[href*="RULE-1.1a2b3c4d.jane-doe.json"]')
    page.close()


# purlin: purlin_report PROOF-136
def test_a_rule_with_no_remote_has_no_links(browser, tmp_path):
    """The solo fixture names no remote, so paths stay plain text."""
    page = open_board(browser, tmp_path, payload_named('solo'))
    open_rule(page, 'login', 'RULE-1')
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
    open_rule(page, 'login', 'RULE-4')
    body = page.inner_text('.wrap')
    assert 'windows: no run yet' in body
    assert 'NOT RUN' in body
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


# purlin: purlin_report PROOF-88
def test_the_working_tree_notice_shows_on_the_board(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['dirty'] is True and len(payload['warnings']) == 1
    page = open_board(browser, tmp_path, payload)
    assert len(page.query_selector_all('.notice')) == 2
    page.close()


# purlin: purlin_report PROOF-22
def test_the_working_tree_notice_is_not_on_a_rule_screen(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-1')
    assert 'RULE-1' in page.inner_text('h1')
    assert page.query_selector_all('.notice') == []
    page.close()


# purlin: purlin_report PROOF-24
def test_the_open_rule_is_the_last_tab(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-1')
    assert texts(page, '.tabs button') == ['Board', 'login RULE-1']
    page.close()


# purlin: purlin_report PROOF-137
def test_the_open_rules_tab_stays_clickable(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-1')
    page.click('.tabs button:last-child')
    assert 'RULE-1' in page.inner_text('h1')
    assert len(texts(page, '.tabs button')) == 2
    page.close()


# purlin: purlin_report PROOF-25
def test_the_link_back_reads_board(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-1')
    assert page.inner_text('[data-act="close"]') == u'← Board'
    page.close()


# purlin: purlin_report PROOF-138
def test_the_link_back_closes_the_rule(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-1')
    page.click('[data-act="close"]')
    assert len(feature_names(page)) == 4
    assert texts(page, '.tabs button') == ['Board']
    page.close()


# purlin: purlin_report PROOF-26
def test_the_rule_screen_names_the_sign_command(browser, tmp_path):
    """The page cannot sign a commit, so it names the command that does."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-2')
    assert panel_heads(page) == ['Audit', 'Signature']
    lines = panel_lines(page, 'Signature')
    assert lines[0].startswith('purlin:sign login RULE-2'), lines
    assert lines[1] == ('A signature is a signed commit that names its '
                        'signer; the page shows it once it is committed.'), lines
    assert 'courier' in page.eval_on_selector(
        '.cmd', 'el => getComputedStyle(el).fontFamily').lower()
    page.close()


# purlin: purlin_report PROOF-89
def test_a_rule_to_test_by_hand_names_the_hand_check(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'invoice', 'RULE-3')
    assert 'Hand check' in panel_heads(page)
    assert page.inner_text('.cmd') == 'purlin:sign invoice RULE-3'
    page.close()


# purlin: purlin_report PROOF-90
def test_a_signed_rule_names_its_signer_key_and_machines(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-1')
    lines = panel_lines(page, 'Signed')
    signed = page.inner_text('.wrap')
    page.close()
    assert lines[:3] == [
        'Signed by Jane Doe, jane@acme.com, on 2026-09-12 10:02 UTC with the '
        'key ending ...Xy4Q.',
        'On Linux/Unix the tests ran on remote runner, Linux/Unix.',
        'On Windows the tests ran on remote runner, Windows.'], lines
    assert 'purlin:sign' not in signed


# purlin: purlin_report PROOF-39
def test_the_sign_panel_is_absent_below_the_signed_gate(browser, tmp_path):
    """Under `strong` no signature is read, so none is asked for."""
    page = open_board(browser, tmp_path, payload_named('team'))
    open_rule(page, 'login', 'RULE-1')
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
    open_rule(page, 'login', 'RULE-1')
    page.evaluate('window.purlinMark = 1')
    page.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    page.wait_for_function('() => window.purlinMark === undefined',
                           timeout=10000)
    page.wait_for_selector('h1', timeout=10000)
    assert 'RULE-1' in page.inner_text('h1')
    page.close()


# purlin: purlin_report PROOF-28
def test_the_freshness_line_is_a_button_styled_as_the_theme_button(
        browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    node = page.query_selector('.topbar [data-act="reload"]')
    assert node.evaluate('el => el.tagName') == 'BUTTON'
    assert 'Data:' in node.inner_text()
    assert 'btn' in node.get_attribute('class').split()
    assert 'btn' in page.get_attribute('[data-act="theme"]', 'class').split()
    assert page.eval_on_selector(
        '.topbar [data-act="reload"]',
        'el => getComputedStyle(el).borderTopWidth') == page.eval_on_selector(
        '[data-act="theme"]', 'el => getComputedStyle(el).borderTopWidth')
    page.close()


# purlin: purlin_report PROOF-139
def test_pressing_the_freshness_line_reloads(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    # A mark on the window survives a render and not a reload.
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
    # The page reads the data file through a frame of its own, one frame per
    # read, so one frame means one read.
    assert page.evaluate(
        "() => document.querySelectorAll('iframe').length") == 1
    page.close()

# ---------------------------------------------------------------------------
# The screenshots the docs embed
# ---------------------------------------------------------------------------

# purlin: purlin_report PROOF-23
def test_the_docs_screenshots_come_from_the_fixtures():
    """Two images, each from a fixture payload, written to docs/images/.

    A screenshot taken from whatever this checkout happens to hold is out of
    date the moment the data moves and shows one project's names to every reader,
    so the capture names a fixture for every shot it takes.
    """
    import capture_doc_screenshots as capture

    assert [(name, fixture) for name, fixture, _clicks in capture.SHOTS] == [
        ('dashboard-board.png', 'regulated'),
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


def audit_lines(browser, tmp_path, payload, feature, rule_id):
    """The lines of the `Audit` panel on one rule's screen."""
    page = open_board(browser, tmp_path, payload)
    open_rule(page, feature, rule_id)
    lines = panel_lines(page, 'Audit')
    page.close()
    return lines


# purlin: purlin_report PROOF-54
def test_the_audit_panel_reads_an_undecided_audit(browser, tmp_path):
    """The answer, each finding on its own line, the strength, the model."""
    lines = audit_lines(browser, tmp_path, payload_named('regulated'),
                        'checkout_design', 'RULE-1')
    assert lines[0].startswith('Undecided. '), lines
    assert lines[1].startswith('The test reads the text "Total"'), lines
    assert lines[2] == 'Test strength 90%, against a minimum of 80%.', lines
    assert lines[3] == ('Read by example-model-1 on 2026-09-12 '
                        '09:14 UTC'), lines


# purlin: purlin_report PROOF-144
def test_the_audit_panel_reads_a_weak_audit(browser, tmp_path):
    lines = audit_lines(browser, tmp_path, payload_named('regulated'),
                        'invoice', 'RULE-2')
    assert lines[0] == 'Weak.', lines
    assert lines[1].startswith('No proof of this rule names a rejection'), lines
    assert lines[2] == 'Test strength 64%, against a minimum of 80%.', lines


# purlin: purlin_report PROOF-145
def test_the_audit_panel_reads_a_strong_audit(browser, tmp_path):
    lines = audit_lines(browser, tmp_path, payload_named('regulated'),
                        'login', 'RULE-1')
    assert lines[0] == 'Strong. It found nothing.', lines


# purlin: purlin_report PROOF-146
def test_the_audit_panel_with_no_strength_measured(browser, tmp_path):
    payload = payload_named('team')
    payload['features'][0]['rules'][1]['cells']['strong']['strength'] = None
    lines = audit_lines(browser, tmp_path, payload, 'login', 'RULE-2')
    assert 'no mutation score measured' in lines, lines


# purlin: purlin_report PROOF-147
def test_the_audit_panel_of_a_rule_no_audit_read(browser, tmp_path):
    lines = audit_lines(browser, tmp_path, payload_named('regulated'),
                        'export', 'RULE-2')
    assert lines[0] == (
        'No audit has read this rule’s text, proof and test yet.'), lines


def top_bar(browser, tmp_path, payload):
    page = open_board(browser, tmp_path, payload)
    bar = page.inner_text('.topbar')
    page.close()
    return bar


# purlin: purlin_report PROOF-55
def test_the_top_bar_states_the_signed_tag(browser, tmp_path):
    payload = payload_named('regulated')
    assert payload['gate']['gate'] == 'signed'
    assert payload['tag']['name'] == 'signed/1.4.0'
    bar = top_bar(browser, tmp_path, payload)
    assert 'signed/1.4.0 · a1b2c3d' in bar, bar
    assert 'no signed tag' not in bar


# purlin: purlin_report PROOF-148
def test_the_top_bar_names_no_signed_tag(browser, tmp_path):
    payload = payload_named('regulated')
    payload['tag'] = None
    assert 'no signed tag' in top_bar(browser, tmp_path, payload)


def _no_tag_below_signed(browser, tmp_path, name, gate):
    payload = payload_named(name)
    assert payload['gate']['gate'] == gate
    bar = top_bar(browser, tmp_path, payload)
    assert 'no signed tag' not in bar, bar
    assert 'signed/' not in bar, bar
    assert 'gate: ' + gate in bar, bar


# purlin: purlin_report PROOF-149
def test_the_top_bar_at_strong_shows_no_tag(browser, tmp_path):
    _no_tag_below_signed(browser, tmp_path, 'team', 'strong')


# purlin: purlin_report PROOF-150
def test_the_top_bar_at_passed_shows_no_tag(browser, tmp_path):
    _no_tag_below_signed(browser, tmp_path, 'solo', 'passed')


# purlin: purlin_report PROOF-62
def test_a_spec_that_names_no_files_says_so(browser, tmp_path):
    """The team fixture's invoice spec has no `> Scope:` line."""
    page = open_board(browser, tmp_path, payload_named('team'))
    names = dict(zip(feature_names(page), page.eval_on_selector_all(
        '.tr .name', 'els => els.map(e => Array.from(e.querySelectorAll('
        '".n, .ns")).map(s => s.textContent.trim()).join(" "))')))
    assert names['invoice'] == 'invoice · no scope', names
    assert page.get_attribute('.tr[data-feature="invoice"] .ns',
                              'title') == 'no > Scope: line'
    assert names['login'] == 'login', names
    page.close()


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


# The words of a higher step than `passed`, which a project at that gate is
# never shown: the requirement names them, so the test does too.
HIGHER_WORDS = re.compile(
    r'\b(strong|signed|audit|signature|hand check)', re.I)
# Proofs are optional at `passed`, so a project there that writes no proof
# line is not shown the word either.
HIGHER_WORDS_NO_PROOFS = re.compile(
    r'\b(strong|signed|audit|signature|hand check|proof)', re.I)
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


def _higher_words(browser, tmp_path, payload, words=HIGHER_WORDS):
    """Walk every screen of a `passed` board: the words of a higher step it
    showed, and each rule's status in the order the rules were opened."""
    assert payload['gate']['gate'] == 'passed'
    page = open_board(browser, tmp_path, payload)
    seen, statuses = _walk_everything(page)
    page.close()
    found = sorted({match.group(0) for text in seen if text
                    for match in words.finditer(text)})
    assert len(statuses) == 5, statuses
    assert all(status in STATUSES for status in statuses), statuses
    return found, statuses


def _login_rule_1_reads(word, reasons):
    """The solo payload with login `RULE-1`'s passed cell reading `word`."""
    payload = payload_named('solo')
    cell = payload['features'][0]['rules'][0]['cells']['passed']
    cell['word'] = word
    cell['reasons'] = reasons
    return payload


# purlin: purlin_report PROOF-63
def test_the_passed_gate_shows_no_word_of_a_higher_level(browser, tmp_path):
    found, _statuses = _higher_words(browser, tmp_path, payload_named('solo'))
    assert found == [], found


# purlin: purlin_report PROOF-99
def test_a_failed_rule_at_passed_shows_no_higher_word(browser, tmp_path):
    found, statuses = _higher_words(browser, tmp_path, _login_rule_1_reads(
        'failed', ['failing: tests/test_login.py']))
    assert found == [], found
    assert statuses[0] == 'failed', statuses


# purlin: purlin_report PROOF-100
def test_a_partial_rule_at_passed_shows_no_higher_word(browser, tmp_path):
    found, statuses = _higher_words(browser, tmp_path, _login_rule_1_reads(
        'partial', ['passed on macos', 'linux: failed']))
    assert found == [], found
    assert statuses[0] == 'partial', statuses


# purlin: purlin_report PROOF-101
def test_a_rule_not_run_at_passed_shows_no_higher_word(browser, tmp_path):
    found, statuses = _higher_words(browser, tmp_path, _login_rule_1_reads(
        'not run', ['linux: no run yet']))
    assert found == [], found
    assert statuses[0] == 'not run', statuses


# purlin: purlin_report PROOF-102
def test_a_rule_out_of_date_at_passed_shows_no_higher_word(browser,
                                                           tmp_path):
    found, statuses = _higher_words(browser, tmp_path, _login_rule_1_reads(
        'out of date', ['code changed since 9f8e7d6']))
    assert found == [], found
    assert statuses[0] == 'out of date', statuses


# purlin: purlin_report PROOF-103
def test_a_passed_project_with_no_proof_line_never_reads_proof(browser,
                                                               tmp_path):
    payload = without_proof_lines(payload_named('solo'))
    assert payload['summary']['proofs'] == 0
    found, _statuses = _higher_words(browser, tmp_path, payload,
                                     HIGHER_WORDS_NO_PROOFS)
    assert found == [], found


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
    seen = list(page.evaluate(SEEN))
    page.close()
    word = 'PASSED' if passing else 'FAILED'
    assert lines == ['tests/test_lock.py :: test_five_wrong_passwords_lock '
                     + word], lines
    found = sorted({match.group(0) for text in seen if text
                    for match in HIGHER_WORDS_NO_PROOFS.finditer(text)})
    assert found == [], found


# purlin: purlin_report PROOF-65
def test_a_passing_test_marked_with_the_rules_id_shows_passed(browser,
                                                             tmp_path):
    _rule_marked_with_its_id(browser, tmp_path, True)


# purlin: purlin_report PROOF-152
def test_a_failing_test_marked_with_the_rules_id_shows_failed(browser,
                                                             tmp_path):
    _rule_marked_with_its_id(browser, tmp_path, False)


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


def _contrast_in(browser, tmp_path, theme):
    """Every fixture in one theme, on the board with its first spec and that
    spec's first rule's proofs open, then on that rule's screen: how many
    neutral texts were measured, and those under 7:1."""
    checked = 0
    low = []
    for process in PROCESSES:
        page = open_in_theme(browser, tmp_path / process,
                             payload_named(process), theme)
        page.click('.tr')
        page.click('[data-act="proofs"]')
        assert page.query_selector('.rule-proofs'), process
        found = neutral_text(page)
        page.click('.rule')
        page.wait_for_selector('h1', timeout=10000)
        found += neutral_text(page)
        page.close()
        low += [(process, item) for item in found if item[3] < 7]
        checked += len(found)
    return checked, low


# purlin: purlin_report PROOF-66
def test_neutral_text_measures_7_to_1_in_the_dark_theme(browser, tmp_path):
    checked, low = _contrast_in(browser, tmp_path, 'dark')
    assert low == [], low
    assert checked > 100, checked


# purlin: purlin_report PROOF-104
def test_neutral_text_measures_7_to_1_in_the_light_theme(browser, tmp_path):
    checked, low = _contrast_in(browser, tmp_path, 'light')
    assert low == [], low
    assert checked > 100, checked


# purlin: purlin_report PROOF-105
def test_the_contrast_check_names_a_text_under_7_to_1(browser, tmp_path):
    page = open_in_theme(browser, tmp_path, payload_named('team'), 'dark')
    page.evaluate("document.documentElement.style.setProperty("
                  "'--state-idle', '#94A2B8')")
    assert [item for item in neutral_text(page) if item[3] < 7]
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


def proof_lines(page, selector='.rule-proofs .proof'):
    """What the open proofs beneath the rows read, one line per row."""
    return page.eval_on_selector_all(
        selector + ' .kv > *',
        r'els => els.map(e => e.textContent.trim().replace(/\s+/g, " "))')


def why_lines(page):
    """What an unfolded rule reads before its proofs, one line per row."""
    return page.eval_on_selector_all(
        '.rule-proofs .why .kv > *',
        r'els => els.map(e => (e.tagName === "DT" ? e.textContent'
        r' : e.innerText).trim().replace(/\s+/g, " "))')


def login_open(browser, tmp_path, payload=None):
    """The regulated sample's board with login open."""
    page = open_board(browser, tmp_path, payload or payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    return page


def unfolded(browser, tmp_path, feature, rule, name='regulated'):
    """The board of one sample with one spec open and one rule unfolded."""
    page = open_board(browser, tmp_path, payload_named(name))
    page.click('[data-act="feature"][data-feature="%s"]' % feature)
    page.click(toggle_for(feature, rule))
    return page


def toggle_for(feature, rule):
    return '[data-act="proofs"][data-feature="%s"][data-rule="%s"]' % (
        feature, rule)


# purlin: purlin_report PROOF-68
def test_every_rule_opens_folded(browser, tmp_path):
    page = login_open(browser, tmp_path)
    found = toggles(page)
    assert [found[r]['label'] for r in ('RULE-1', 'RULE-2', 'RULE-3',
                                        'RULE-4')] == [
        '1 proof', '1 proof', '1 proof', '2 proofs'], found
    assert all(item['tag'] == 'BUTTON' and item['open'] == 'false'
               and item['glyph'] == '▶' for item in found.values())
    assert 'no cookie is set' not in page.inner_text('.wrap')
    page.close()


# purlin: purlin_report PROOF-153
def test_a_failed_proof_draws_its_rules_count_in_the_warn_tone(browser,
                                                               tmp_path):
    page = login_open(browser, tmp_path)
    found = toggles(page)
    warn = resolved(page, '--state-warn')
    assert found['RULE-4']['colour'] == warn
    assert found['RULE-1']['colour'] != warn
    page.close()


# purlin: purlin_report PROOF-154
def test_enter_unfolds_a_rule_and_keeps_the_focus(browser, tmp_path):
    page = login_open(browser, tmp_path)
    page.focus(toggle_for('login', 'RULE-4'))
    page.keyboard.press('Enter')
    found = toggles(page)
    assert found['RULE-4']['open'] == 'true', found['RULE-4']
    assert found['RULE-4']['glyph'] == '▼'
    assert found['RULE-1']['open'] == 'false'
    assert page.query_selector('h1') is None, 'the board is not showing'
    assert page.evaluate(
        "document.activeElement.getAttribute('data-rule')") == 'RULE-4'
    page.close()


# purlin: purlin_report PROOF-155
def test_an_unfolded_rule_reads_each_proof(browser, tmp_path):
    page = unfolded(browser, tmp_path, 'login', 'RULE-4')
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
    page.close()


# purlin: purlin_report PROOF-156
def test_enter_again_folds_the_rule(browser, tmp_path):
    page = unfolded(browser, tmp_path, 'login', 'RULE-4')
    page.focus(toggle_for('login', 'RULE-4'))
    page.keyboard.press('Enter')
    assert proof_lines(page) == []
    page.close()


# purlin: purlin_report PROOF-157
def test_reopening_a_spec_folds_its_rules(browser, tmp_path):
    page = unfolded(browser, tmp_path, 'login', 'RULE-4')
    assert proof_lines(page) != []
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('[data-act="feature"][data-feature="login"]')
    assert proof_lines(page) == []
    assert toggles(page)['RULE-4']['open'] == 'false'
    page.close()


# purlin: purlin_report PROOF-69
def test_a_proof_with_no_test_says_so_under_its_row(browser, tmp_path):
    payload = payload_named('solo')
    login = payload['features'][0]
    page = open_board(browser, tmp_path, payload)
    page.click('[data-act="feature"][data-feature="login"]')
    found = toggles(page)
    assert found['RULE-2']['label'] == '1 proof'
    assert found['RULE-2']['colour'] == resolved(page, '--state-warn')
    page.click(toggle_for('login', 'RULE-2'))
    assert proof_lines(page) == [
        'PROOF-2', login['rules'][1]['proofs'][0]['text'], 'Result',
        'NO TEST', 'Tests', 'No test yet.']
    page.close()


# purlin: purlin_report PROOF-158
def test_a_rule_with_no_proof_shows_the_test_marked_with_its_id(browser,
                                                                tmp_path):
    payload = payload_named('solo')
    payload['features'][0]['rules'][2]['tests'] = [
        {'file': 'tests/test_login.py', 'name': 'test_locks', 'result': 'pass'}]
    page = open_board(browser, tmp_path, payload)
    page.click('[data-act="feature"][data-feature="login"]')
    assert toggles(page)['RULE-3']['label'] == 'no proof'
    page.click(toggle_for('login', 'RULE-3'))
    assert proof_lines(page) == [
        'Tests', 'tests/test_login.py :: test_locks PASSED']
    page.close()


def _bare_login_toggles(browser, tmp_path):
    bare = open_board(browser, tmp_path,
                      without_proof_lines(payload_named('solo')))
    bare.click('[data-act="feature"][data-feature="login"]')
    found = toggles(bare)
    bare.close()
    return found


# purlin: purlin_report PROOF-159
def test_with_no_proof_line_the_button_counts_tests(browser, tmp_path):
    found = _bare_login_toggles(browser, tmp_path)
    assert not [item for item in found.values() if 'proof' in item['label']]
    assert found['RULE-1']['label'] == '1 test'


# purlin: purlin_report PROOF-160
def test_with_no_proof_line_a_rule_with_no_test_has_no_button(browser,
                                                              tmp_path):
    found = _bare_login_toggles(browser, tmp_path)
    assert 'RULE-1' in found
    assert 'RULE-3' not in found


# purlin: purlin_report PROOF-70
def test_a_filter_that_hides_a_rule_hides_its_proofs(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click(toggle_for('login', 'RULE-4'))
    assert 'PROOF-4' in proof_lines(page)
    page.click(chip_for('To strengthen'))
    assert rule_ids(page) == ['RULE-3']
    assert proof_lines(page) == []
    page.close()


# purlin: purlin_report PROOF-106
def test_the_rule_screen_draws_the_proofs_the_board_drew(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click(toggle_for('login', 'RULE-4'))
    board = proof_lines(page)
    page.click('.rule[data-feature="login"][data-rule="RULE-4"]')
    screen = page.eval_on_selector_all(
        'section .stack .panel .kv > *',
        r'els => els.map(e => e.textContent.trim().replace(/\s+/g, " "))')
    page.close()
    assert board and screen == board, (screen, board)


# purlin: purlin_report PROOF-71
def test_a_shared_rule_counts_toward_the_spec_that_proves_it(browser,
                                                             tmp_path):
    page = open_board(browser, tmp_path, payload_named('team'))
    cells = count_cells(page)
    assert cells['receipt']['Rules'] == '1 (+1 shared)'
    assert cells['login']['Rules'] == '3'
    assert hovers(page)['receipt']['Rules'] == 'checkout_design · 1'
    page.close()


ANCHOR_TEXT = 'The cart page shows the order total above the pay button.'
RECEIPT_TEXT = 'A receipt names the order number and the total paid.'


# purlin: purlin_report PROOF-107
def test_a_shared_rule_is_listed_once_under_its_owner(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('team'))
    for name in feature_names(page):
        page.click('[data-act="feature"][data-feature="%s"]' % name)
    assert texts(page, '.rule[data-feature="receipt"] .rid') == ['RULE-1']
    assert texts(page, '.rule .rt').count(ANCHOR_TEXT) == 1
    assert texts(page, '.rule[data-feature="checkout_design"] .rt') == [
        ANCHOR_TEXT]
    page.close()


# purlin: purlin_report PROOF-108
def test_a_features_own_rule_opens_its_own_screen(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('team'))
    open_rule(page, 'receipt', 'RULE-1')
    assert texts(page, '.tabs button')[-1] == 'receipt RULE-1'
    body = page.inner_text('.wrap')
    page.close()
    assert RECEIPT_TEXT in body
    assert ANCHOR_TEXT not in body


# purlin: purlin_report PROOF-109
def test_an_anchors_rule_opens_the_anchors_screen(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('team'))
    open_rule(page, 'checkout_design', 'RULE-1')
    assert texts(page, '.tabs button')[-1] == 'checkout_design RULE-1'
    body = page.inner_text('.wrap')
    page.close()
    assert ANCHOR_TEXT in body
    assert RECEIPT_TEXT not in body


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


@pytest.fixture(scope='module')
def shared_payload(tmp_path_factory):
    """The payload a real project with a global anchor writes once its tests
    have run: `lock` of 2 rules, and `security` of 6 that every feature
    proves."""
    root = tmp_path_factory.mktemp('shared') / 'project'
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
    return payload


# purlin: purlin_report PROOF-72
def test_a_real_projects_shared_rules_count_toward_it(browser, tmp_path,
                                                      shared_payload):
    page = open_board(browser, tmp_path, shared_payload)
    rules = count_cells(page)['lock']['Rules']
    rules_hover = hovers(page)['lock']['Rules']
    found = boxes(page)
    page.close()
    assert rules == '2 (+6 shared)'
    assert rules_hover == 'security · 6'
    assert [(label, count) for label, count, _ in found] == [
        ('Passing', '8')], found


# purlin: purlin_report PROOF-110
def test_a_real_projects_shared_rules_are_listed_once(browser, tmp_path,
                                                      shared_payload):
    page = open_board(browser, tmp_path, shared_payload)
    page.click('[data-act="feature"][data-feature="lock"]')
    assert rule_ids(page) == ['RULE-1', 'RULE-2']
    page.click('[data-act="feature"][data-feature="security"]')
    assert len(rule_ids(page)) == 8
    assert texts(page, '.rule[data-feature="security"] .rid') == [
        'RULE-%d' % n for n in range(1, 7)]
    page.close()


# purlin: purlin_report PROOF-111
def test_a_real_projects_two_rule_1s_open_their_own_screens(browser,
                                                            tmp_path,
                                                            shared_payload):
    page = open_board(browser, tmp_path, shared_payload)
    page.click('[data-act="feature"][data-feature="security"]')
    open_rule(page, 'lock', 'RULE-1')
    own = page.inner_text('.wrap')
    page.click('[data-act="close"]')
    page.click('.rule[data-feature="security"][data-rule="RULE-1"]')
    shared = page.inner_text('.wrap')
    page.close()
    assert 'A wrong password five times locks the account' in own
    assert 'Security pattern 1 is absent' not in own
    assert 'Security pattern 1 is absent' in shared
    assert 'A wrong password' not in shared


# purlin: purlin_report PROOF-79
def test_a_waiting_row_beneath_a_rule_is_neutral(browser, tmp_path):
    page = unfolded(browser, tmp_path, 'login', 'RULE-4')
    pills = page.eval_on_selector_all(
        '.rule-proofs .why .pill',
        'els => els.map(e => [e.innerText.trim(), getComputedStyle(e).color])')
    assert [text for text, _ in pills] == ['PARTIAL', 'WAITING', 'WAITING']
    neutral = resolved(page, '--state-neutral')
    assert neutral != resolved(page, '--state-warn')
    assert [colour for _, colour in pills[1:]] == [neutral, neutral], pills
    page.close()


# purlin: purlin_report PROOF-164
def test_a_waiting_cell_says_what_it_waits_for(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    open_rule(page, 'login', 'RULE-4')
    rows = page.eval_on_selector_all(
        '.kv dd', r'els => els.map(e => e.innerText.trim().replace(/\s+/g, " "))')
    assert 'WAITING waiting for its tests to pass' in rows, rows
    assert 'WAITING waiting for the audit' in rows, rows
    page.close()


# ---------------------------------------------------------------------------
# A rule folded and unfolded
# ---------------------------------------------------------------------------

def row_badges(page, feature):
    """Each rule of an open spec and the badges its folded row carries."""
    return dict(page.eval_on_selector_all(
        '.rule[data-feature="%s"]' % feature,
        "els => els.map(e => [e.getAttribute('data-rule'), Array.from("
        "e.querySelectorAll('.rp .pill')).map(p => p.innerText.trim())"
        ".join(' ')])"))


# purlin: purlin_report PROOF-165
def test_a_folded_rule_carries_the_steps_it_reached(browser, tmp_path):
    page = login_open(browser, tmp_path)
    assert row_badges(page, 'login') == {
        'RULE-1': 'PASSED STRONG SIGNED', 'RULE-2': 'PASSED STRONG',
        'RULE-3': 'PASSED', 'RULE-4': 'FAILED'}
    page.close()


# purlin: purlin_report PROOF-166
def test_a_rule_that_reached_no_step_carries_no_badge(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="export"]')
    page.click('[data-act="feature"][data-feature="invoice"]')
    assert row_badges(page, 'export')['RULE-1'] == ''
    assert row_badges(page, 'invoice')['RULE-3'] == ''
    page.close()


# purlin: purlin_report PROOF-167
def test_the_badges_add_up_to_the_step_boxes(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    for name in feature_names(page):
        page.click('[data-act="feature"][data-feature="%s"]' % name)
    seen = texts(page, '.rule .rp .pill')
    found = boxes(page)
    page.close()
    assert [seen.count(word) for word in ('PASSED', 'STRONG', 'SIGNED')] == [
        7, 2, 1], seen
    assert [int(count) for _, count, _ in found[:3]] == [7, 2, 1]


# purlin: purlin_report PROOF-168
def test_a_failed_rule_at_passed_carries_failed_alone(browser, tmp_path):
    payload = _login_rule_1_reads('failed', ['failing: tests/test_login.py'])
    page = open_board(browser, tmp_path, payload)
    page.click('[data-act="feature"][data-feature="login"]')
    assert row_badges(page, 'login')['RULE-1'] == 'FAILED'
    page.close()


# purlin: purlin_report PROOF-169
def test_a_folded_rule_shows_no_reason(browser, tmp_path):
    page = login_open(browser, tmp_path)
    row = page.inner_text('.rule[data-rule="RULE-3"]')
    page.close()
    assert 'WEAK' not in row and 'WAITING' not in row, row
    assert 'reads the status code alone' not in row, row


# purlin: purlin_report PROOF-170
def test_an_unfolded_weak_rule_says_why_and_what_the_audit_found(browser,
                                                                  tmp_path):
    page = unfolded(browser, tmp_path, 'login', 'RULE-3')
    assert why_lines(page) == [
        'Strong', 'WEAK', 'Signed', 'WAITING waiting for the audit',
        'Audit', 'Weak. PROOF-3 reads the status code alone; no test reads '
        'when the lock expires.']
    assert proof_lines(page)[0] == 'PROOF-3'
    page.close()


# purlin: purlin_report PROOF-171
def test_an_unfolded_rule_that_reached_every_step_reads_the_audit(browser,
                                                                   tmp_path):
    page = unfolded(browser, tmp_path, 'login', 'RULE-1')
    assert why_lines(page) == ['Audit', 'Strong. It found nothing.']
    assert proof_lines(page)[0] == 'PROOF-1'
    page.close()


# purlin: purlin_report PROOF-172
def test_an_unfolded_rule_no_audit_read_says_so(browser, tmp_path):
    page = unfolded(browser, tmp_path, 'export', 'RULE-2')
    assert why_lines(page) == [
        'Strong', 'NOT AUDITED no audit has run on this code',
        'Signed', 'WAITING waiting for the audit',
        'Audit', 'No audit has read this rule’s text, proof and test yet.']
    page.close()


# purlin: purlin_report PROOF-132
def test_an_unfolded_rule_at_passed_has_no_audit_row(browser, tmp_path):
    page = unfolded(browser, tmp_path, 'login', 'RULE-2', name='solo')
    assert why_lines(page) == ['Passed', 'NO TEST']
    page.close()
