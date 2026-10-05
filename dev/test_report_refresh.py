"""The dashboard's data file and its page: which commands write them, and that
nothing else does.

`.purlin/report-data.js` is what the page reads. `purlin:status`,
`purlin:test`, `purlin:audit` and `purlin:sign` each write it as they finish,
and nothing runs in the background, so an edit made with no Purlin command
leaves it as it was. Whenever the data file is written, the page beside it,
`purlin-report.html`, is written too where it differs from the plugin's own.
Each test drives the real command against a throwaway project and reads the
files back.

    python3 -m pytest dev/test_report_refresh.py -q
"""

import json
import os
import re
import subprocess
import sys

DEV = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DEV)
sys.path.insert(0, DEV)
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'review'))
sys.path.insert(0, os.path.join(ROOT, 'scripts', 'export'))

import sign as sign_module  # noqa: E402
from purlin import report_data  # noqa: E402
from purlin import status as purlin_status  # noqa: E402
from mcp_project import SPEC, Project  # noqa: E402
from sign_project import signing_project  # noqa: E402
from test_run_script import (_setting_gains_v,  # noqa: E402
                             _touched_project)
from test_purlin_report import browser, build_page  # noqa: E402,F401

DATA = os.path.join('.purlin', 'report-data.js')
PAGE = 'purlin-report.html'


def _data(root):
    """The payload the data file holds, or None where there is no file."""
    path = os.path.join(str(root), DATA)
    if not os.path.isfile(path):
        return None
    with open(path, encoding='utf-8') as handle:
        text = handle.read()
    prefix = 'const PURLIN_DATA = '
    assert text.startswith(prefix) and text.endswith(';\n'), text[:80]
    return json.loads(text[len(prefix):-len(';\n')])


def _stamp(root, name=DATA):
    """A file's bytes and its modification time, to the nanosecond."""
    path = os.path.join(str(root), name)
    with open(path, 'rb') as handle:
        return handle.read(), os.stat(path).st_mtime_ns


def _git(root, *args):
    result = subprocess.run(['git'] + list(args), cwd=str(root),
                            capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _rule_ids(data):
    return [rule['id'] for feature in data['features']
            for rule in feature['rules']]


# purlin: purlin_report PROOF-59
def test_a_sign_off_writes_the_data_file_naming_the_sign_off(capsys):
    made = signing_project()
    try:
        purlin_status.sync_status(made.root)
        os.remove(os.path.join(made.root, DATA))
        answers = os.path.join(made.root, '.purlin', 'runtime',
                               'signoff-answers.json')
        os.makedirs(os.path.dirname(answers), exist_ok=True)
        with open(answers, 'w', encoding='utf-8') as handle:
            json.dump({'audit': 'go on', 'stops': {},
                       'sign': 'jane@acme.com'}, handle)
        code = sign_module.main(['--answers', answers, '--version', '1.0.0',
                                 '--project-root', made.root])
        assert code == 0, capsys.readouterr().out
        tagged = _git(made.root, 'rev-list', '-n', '1', 'signed/1.0.0')
        data = _data(made.root)
        assert data is not None, 'purlin:sign wrote no data file'
        assert _rule_ids(data) == ['RULE-1', 'RULE-2']
        assert data['met'] is True
        assert data['signoff']['word'] == 'signed 1.0.0 at %s' % tagged[:7], \
            data['signoff']
    finally:
        made.close()


EXTRA_RULE = ('- RULE-3: A locked account reads 423 until fifteen minutes '
              'pass\n')


# purlin: purlin_report PROOF-60
def test_an_edit_with_no_command_leaves_the_data_file_alone():
    made = Project()
    try:
        purlin_status.sync_status(made.root)
        before = _stamp(made.root)
        assert len(_rule_ids(_data(made.root))) == 2
        spec = os.path.join(made.root, 'specs', 'auth', 'login.md')
        with open(spec, encoding='utf-8') as handle:
            text = handle.read()
        with open(spec, 'w', encoding='utf-8') as handle:
            handle.write(text.replace('\n\n## Proof', '\n' + EXTRA_RULE
                                      + '\n## Proof'))
        with open(os.path.join(made.root, 'src', 'login.py'), 'a',
                  encoding='utf-8') as handle:
            handle.write('# edited\n')
        _git(made.root, 'add', '-A')
        _git(made.root, 'commit', '-q', '-m', 'an edit by hand')
        assert _stamp(made.root) == before
        assert len(_rule_ids(_data(made.root))) == 2
    finally:
        made.close()


# purlin: purlin_report PROOF-61
def test_a_directory_with_no_settings_file_gets_no_data_file(tmp_path):
    os.makedirs(os.path.join(str(tmp_path), 'specs', 'auth'))
    with open(os.path.join(str(tmp_path), 'specs', 'auth', 'login.md'), 'w',
              encoding='utf-8') as handle:
        handle.write(SPEC)
    assert not os.path.exists(os.path.join(str(tmp_path), '.purlin',
                                           'config.json'))
    purlin_status.sync_status(str(tmp_path))
    assert not os.path.exists(os.path.join(str(tmp_path), DATA))
    assert os.listdir(str(tmp_path)) == ['specs']


# purlin: purlin_report PROOF-233
def test_status_names_the_branch_and_the_commit_it_ran_on():
    made = Project()
    try:
        _git(made.root, 'checkout', '-q', '-b', 'feature/login')
        purlin_status.sync_status(made.root)
        data = _data(made.root)
        head = _git(made.root, 'rev-parse', 'HEAD')
        assert data['branch'] == 'feature/login'
        assert len(head) == 40 and data['commit'][:7] == head[:7]
    finally:
        made.close()


def _write_page(root, text):
    with open(os.path.join(root, PAGE), 'w', encoding='utf-8',
              newline='') as handle:
        handle.write(text)


# purlin: purlin_report PROOF-230
def test_status_replaces_an_older_page_with_the_plugins_own(browser,  # noqa: F811
                                                            tmp_path):
    shipped = build_page()
    older = shipped.replace('var SCHEMA = 17;', 'var SCHEMA = 11;')
    assert older != shipped
    made = Project()
    try:
        _write_page(made.root, older)
        purlin_status.sync_status(made.root)
        with open(report_data.SHIPPED_PAGE, 'rb') as handle:
            own = handle.read()
        assert _stamp(made.root, PAGE)[0] == own
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.goto('file://' + os.path.join(made.root, PAGE))
        page.wait_for_selector('.topbar', timeout=10000)
        notices = page.eval_on_selector_all(
            '.notice', 'els => els.map(e => e.textContent)')
        boxes = len(page.query_selector_all('.tile'))
        rows = page.eval_on_selector_all(
            '.tr .name .n', 'els => els.map(e => e.textContent.trim())')
        page.close()
        assert not [line for line in notices if 'schema' in line], notices
        assert boxes >= 2 and rows == ['login'], (boxes, rows)
    finally:
        made.close()


# purlin: purlin_report PROOF-231
def test_status_leaves_a_page_that_is_the_plugins_own():
    made = Project()
    try:
        with open(report_data.SHIPPED_PAGE, encoding='utf-8',
                  newline='') as handle:
            _write_page(made.root, handle.read())
        long_ago = 1700000000
        os.utime(os.path.join(made.root, PAGE), (long_ago, long_ago))
        before = _stamp(made.root, PAGE)
        purlin_status.sync_status(made.root)
        assert _data(made.root) is not None
        assert _stamp(made.root, PAGE) == before
        assert before[1] == long_ago * 10 ** 9
    finally:
        made.close()


# ---------------------------------------------------------------------------
# The lines the status prints between its table and its sentence
# ---------------------------------------------------------------------------

def _between(text):
    """The lines a status report prints after its table's closing rule and
    before its summary sentence, the empty ones left out."""
    lines = text.splitlines()
    closing = [index for index, line in enumerate(lines)
               if line.startswith('─')][1]
    sentence = next(index for index, line in enumerate(lines)
                    if index > closing and re.match(r'\d+ rules?\. ', line))
    return [line for line in lines[closing + 1:sentence] if line]


NO_SCOPE_SPEC = SPEC.replace('> Scope: src/login.py\n', '')
NO_FILES = ('1 spec names no files, so its tests run every time: login. Run '
            'purlin:spec login to add its > Scope: line.')


# purlin: purlin_report PROOF-270
def test_the_data_file_carries_the_line_for_a_spec_that_names_no_files():
    assert '> Scope:' not in NO_SCOPE_SPEC
    made = Project(spec=NO_SCOPE_SPEC)
    try:
        text = purlin_status.sync_status(made.root)
        assert _between(text)[0] == NO_FILES, text
        assert text.count(NO_FILES) == 1, text
        data = _data(made.root)
        assert data['information'] == [NO_FILES], data['information']
    finally:
        made.close()


# purlin: purlin_report PROOF-271
def test_the_data_file_carries_an_anchor_rule_with_nothing_to_check():
    made = Project()
    try:
        made.spec('# Anchor: screens\n\n## Rules\n\n- RULE-1: Every screen in '
                  'the project names its page\n\n## Proof\n\n- PROOF-1 '
                  '(RULE-1): Open each screen and read its title\n',
                  name='screens', category='_anchors')
        _git(made.root, 'add', '-A')
        _git(made.root, 'commit', '-q', '-m', 'anchor(screens): create')
        rel = made.evidence([{'id': 'PROOF-1', 'rule': 'RULE-1',
                              'status': 'pass'}], feature='screens',
                            commit_it=False)
        path = os.path.join(made.root, *rel.split('/'))
        with open(path, encoding='utf-8') as handle:
            file = json.load(handle)
        for section in file['platforms'].values():
            section['proofs'][0].update(result='nothing to check',
                                        reason='this project has no screens')
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(file, handle)
        line = ('screens RULE-1 passes with nothing to check here: this '
                'project has no screens.')
        text = purlin_status.sync_status(made.root)
        assert _between(text)[0] == line, text
        assert _data(made.root)['information'] == [line]
    finally:
        made.close()


# purlin: purlin_report PROOF-272
def test_the_data_file_carries_a_changed_tests_setting_first(tmp_path):
    root, _sha = _touched_project(tmp_path)
    _setting_gains_v(root)
    said = 'The tests setting changed, so every result is out of date.'
    text = purlin_status.sync_status(str(root))
    assert said in _between(text), text
    assert _data(root)['warnings'][0] == said, _data(root)['warnings']


def _anchor_source(folder):
    """A git repository holding an anchor, with two commits: `(old, new)`."""
    os.makedirs(folder)
    shas = []
    for body in ('v1', 'v2'):
        with open(os.path.join(folder, 'policy.md'), 'w',
                  encoding='utf-8') as handle:
            handle.write('# Anchor: policy\n\n%s\n' % body)
        if not shas:
            _git(folder, 'init', '-q')
            _git(folder, 'config', 'user.email', 'dev@example.com')
            _git(folder, 'config', 'user.name', 'Dev')
        _git(folder, 'add', '-A')
        _git(folder, 'commit', '-q', '-m', body)
        shas.append(_git(folder, 'rev-parse', 'HEAD'))
    return shas


# purlin: purlin_report PROOF-273
def test_the_data_file_carries_an_anchor_whose_pin_is_behind(tmp_path):
    source = str(tmp_path / 'policy-source')
    old, new = _anchor_source(source)
    made = Project()
    try:
        made.spec('# Anchor: policy\n\n> Source: %s\n> Pinned: %s\n\n'
                  '## Rules\n\n- RULE-1: Every answer is JSON\n\n## Proof\n\n'
                  '- PROOF-1 (RULE-1): An answer parses as JSON\n'
                  % (source, old), name='policy', category='_anchors')
        _git(made.root, 'add', '-A')
        _git(made.root, 'commit', '-q', '-m', 'anchor(policy): create')
        line = ('policy: the pin %s is behind its source, now %s. Run '
                'purlin:anchor sync policy.' % (old[:7], new[:7]))
        text = purlin_status.sync_status(made.root)
        assert line in _between(text), text
        warnings = _data(made.root)['warnings']
        assert line in warnings, warnings
        assert 'Anchors:' not in warnings, warnings
    finally:
        made.close()


# purlin: purlin_report PROOF-274
def test_the_data_file_carries_the_uncommitted_spec_files_on_one_line():
    made = Project()
    try:
        with open(os.path.join(made.root, 'specs', 'auth', 'login.md'), 'a',
                  encoding='utf-8') as handle:
            handle.write('\n')
        made.spec(SPEC.replace('login', 'logout'), name='logout')
        text = purlin_status.sync_status(made.root)
        between = _between(text)
        assert between[between.index('Uncommitted spec changes:') + 1:][:2] == [
            '   M specs/auth/login.md', '  ?? specs/auth/logout.md'], text
        warnings = _data(made.root)['warnings']
        assert ('Uncommitted spec changes: M specs/auth/login.md, '
                '?? specs/auth/logout.md') in warnings, warnings
    finally:
        made.close()


# purlin: purlin_report PROOF-277
def test_the_data_file_names_no_update_once_the_page_is_replaced():
    made = Project()
    try:
        with open(os.path.join(made.root, '.gitignore'), 'a',
                  encoding='utf-8') as handle:
            handle.write('.purlin/report-data.js\npurlin-report.html\n')
        os.makedirs(os.path.join(made.root, '.purlin', 'evidence'))
        with open(os.path.join(made.root, '.purlin', 'evidence', 'README.md'),
                  'w', encoding='utf-8') as handle:
            handle.write('What a run leaves behind.\n')
        _git(made.root, 'add', '-A')
        _git(made.root, 'commit', '-q', '-m', 'chore: set up')
        _write_page(made.root, 'an older page\n')
        text = purlin_status.sync_status(made.root)
        assert _between(text) == [], text
        data = _data(made.root)
        assert data['warnings'] == [] and data['information'] == [], data
    finally:
        made.close()
