"""The board page: how it is built, and what it shows.

Two halves. The first reads the built file as text and holds it to the design
system: one token block, no colour written anywhere else, no shadow, no
gradient, no emoji, no request to anything outside the file. The second opens
it in a headless browser over `file://` with a fixture payload beside it, one
fixture per process, and reads what a person would see.

The fixtures under `dev/fixtures/report/` are payloads at schema 4, one for
each of the three processes: solo at the `tested` gate with nothing recorded,
team at `recorded`, regulated at `approved` with approvals, a stale rule and a
design anchor.

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


def rule_ids(page):
    return texts(page, '.rule .rid')


def review_cells(page):
    """Each review row as its five cells: feature, id, text, state, reason."""
    return page.eval_on_selector_all(
        '.rev',
        'els => els.map(e => Array.from(e.children)'
        '.map(c => c.textContent.trim()))')


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
    page = open_board(browser, tmp_path, payload)
    heading = page.inner_text('h1')
    assert str(payload['project_rollup']['rules']) in heading
    assert str(payload['project_rollup']['features']) in heading
    assert len(page.query_selector_all('.tile')) == 7
    assert 'gate: ' + payload['gate']['gate'] in page.inner_text('.topbar')
    assert 'Data:' in page.inner_text('.topbar')
    assert set(feature_names(page)) == set(
        f['name'] for f in payload['features'])
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-9", "RULE-9", tier="e2e")
def test_columns_appear_only_where_their_artifacts_do(browser, tmp_path):
    """A project that has never recorded shows no record column."""
    solo = open_board(browser, tmp_path / 'solo', payload_named('solo'))
    head = solo.inner_text('.th')
    assert 'LATEST RECORD' not in head
    assert 'APPROVALS' not in head
    assert 'RISK' not in head
    assert solo.query_selector_all('table.grid') == []
    solo.close()

    team = open_board(browser, tmp_path / 'team', payload_named('team'))
    head = team.inner_text('.th')
    assert 'LATEST RECORD' in head and 'STRENGTH' in head
    assert 'RE-VERIFY' in head and 'RISK' in head
    assert 'APPROVALS' not in head
    assert len(team.query_selector_all('table.grid')) == 1
    team.close()

    reg = open_board(browser, tmp_path / 'reg', payload_named('regulated'))
    assert 'APPROVALS' in reg.inner_text('.th')
    reg.close()


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
    assert len(page.query_selector_all('.tile')) == 7

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


@pytest.mark.proof("purlin_report", "PROOF-8", "RULE-8", tier="e2e")
def test_the_seven_states_each_have_a_tile(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    labels = texts(page, '.tile-l')
    assert labels == ['Drafted', 'Proof ready', 'Tested', 'Recorded',
                      'Reviewed', 'Approved', 'Stale']
    assert page.eval_on_selector(
        '.tile-l', 'el => getComputedStyle(el).textTransform') == 'uppercase'
    counts = payload_named('regulated')['states']
    values = texts(page, '.tile-v')
    assert values[6] == str(counts['Stale'])
    assert values[5] == str(counts['Approved'])
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-10", "RULE-10", tier="e2e")
def test_a_feature_row_expands_to_its_rules(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert rule_ids(page) == []
    page.click('[data-act="feature"][data-feature="login"]')
    assert rule_ids(page) == ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4']
    assert 'APPROVED' in page.inner_text('.rule')
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
    ('high-open', ['login'], ['RULE-4']),
    ('stale', ['login'], ['RULE-2']),
    ('no-negative', ['login', 'invoice'], ['RULE-3']),
    ('low-strength', ['invoice'], []),
    ('open', ['login', 'invoice'],
     ['RULE-1', 'RULE-2', 'RULE-3', 'RULE-4']),
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
    page.click('[data-filter="low-strength"]')
    assert feature_names(page) == []
    assert 'No rule matches every filter you set.' in page.inner_text('.empty')
    page.click('[data-filter="stale"]')
    page.click('[data-filter="low-strength"]')
    assert len(feature_names(page)) == 3
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
    assert 'APPROVED' in body
    assert '86%' in body
    assert 'Its risk is high, so a person looks before it can be approved.' \
        in body
    assert 'risk high' not in body
    page.click('[data-act="close"]')
    page.click('.rule[data-rule="RULE-3"]')
    review = page.inner_text('.wrap')
    assert 'PROOF-3' in review
    assert 'No proof of this rule names a rejection, an error or a boundary.' \
        in review
    page.close()


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
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-4"]')
    body = page.inner_text('.wrap')
    assert 'windows: no record yet' in body
    assert 'no negative case' not in body
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-18", "RULE-18", tier="e2e")
def test_the_review_list_is_ordered_by_risk(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    assert 'Review list (4)' in page.inner_text('.tabs')
    page.click('[data-screen="review"]')
    assert '4 rules need a look' in page.inner_text('h1')
    assert texts(page, '.group .gt') == ['high risk', 'medium risk',
                                         'low risk']
    assert texts(page, '.group .muted') == ['(2)', '(1)', '(1)']
    rows = texts(page, '.rev')
    assert len(rows) == 4
    first = review_cells(page)[0]
    assert first[0] == 'login'
    assert first[1] == 'RULE-1'
    assert first[2] == 'A person signs in with an email address and a password.'
    assert first[3] == 'APPROVED'
    page.click('.rev')
    assert 'RULE-1' in page.inner_text('h1')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-31", "RULE-30", tier="e2e")
def test_a_row_whose_only_reason_is_its_risk_states_none(browser, tmp_path):
    """The group header already said `high risk`; the row adds nothing."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-screen="review"]')
    assert review_cells(page)[0][4] == ''
    assert page.query_selector_all('.rev .tag') == []
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-31", "RULE-30", tier="e2e")
def test_a_row_states_every_reason_the_group_does_not(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-screen="review"]')
    cells = review_cells(page)
    reasons = {(row[0], row[1]): row[4] for row in cells}
    assert reasons[('login', 'RULE-4')] == 'windows: no record yet'
    assert reasons[('login', 'RULE-2')] == 'stale'
    assert reasons[('invoice', 'RULE-2')] == (
        'strength 64% under 80%; no negative case')
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-19", "RULE-19", tier="e2e")
def test_an_empty_review_list_says_what_puts_a_rule_on_it(browser, tmp_path):
    page = open_board(browser, tmp_path, payload_named('solo'))
    page.click('[data-screen="review"]')
    assert 'Nothing is waiting for a look' in page.inner_text('.empty')
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
    assert texts(page, '.tabs button') == ['Board', 'Review list (4)']
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    assert texts(page, '.tabs button') == ['Board', 'Review list (4)',
                                           'login RULE-1']
    page.click('.tabs button:last-child')
    assert 'RULE-1' in page.inner_text('h1')
    assert len(texts(page, '.tabs button')) == 3
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-25", "RULE-25", tier="e2e")
def test_the_link_back_closes_the_rule_where_it_was_opened(browser, tmp_path):
    """One rule, opened twice, closes back to the screen it came from."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-screen="review"]')
    page.click('.rev')
    assert page.inner_text('[data-act="close"]') == u'\u2190 Review list'
    page.click('[data-act="close"]')
    assert '4 rules need a look' in page.inner_text('h1')
    assert texts(page, '.tabs button') == ['Board', 'Review list (4)']

    page.click('[data-screen="board"]')
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-1"]')
    assert page.inner_text('[data-act="close"]') == u'\u2190 Board'
    page.click('[data-act="close"]')
    assert len(feature_names(page)) == 3
    page.close()


@pytest.mark.proof("purlin_report", "PROOF-26", "RULE-26", tier="e2e")
def test_the_rule_screen_names_the_approve_command(browser, tmp_path):
    """The page cannot sign a commit, so it names the command that does."""
    page = open_board(browser, tmp_path, payload_named('regulated'))
    page.click('[data-act="feature"][data-feature="login"]')
    page.click('.rule[data-rule="RULE-2"]')
    body = page.inner_text('.wrap')
    assert 'purlin:approve login RULE-2' in body
    assert 'signed commit by someone on the approver list' in body
    assert 'courier' in page.eval_on_selector(
        '.cmd', 'el => getComputedStyle(el).fontFamily').lower()

    page.click('[data-act="close"]')
    page.click('.rule[data-rule="RULE-1"]')
    approved = page.inner_text('.wrap')
    assert 'Approved by jane-doe' in approved
    assert 'purlin:approve' not in approved
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
    """Five images, each from a fixture payload, written to docs/images/.

    A screenshot taken from whatever this checkout happens to hold goes stale
    the moment the data moves and shows one project's names to every reader,
    so the capture names a fixture for every shot it takes.
    """
    import capture_doc_screenshots as capture

    assert len(capture.SHOTS) == 5, capture.SHOTS
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
