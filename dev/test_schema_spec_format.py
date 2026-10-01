"""Tests for schema_spec_format: the two sections, the rule and proof
grammar, the metadata fields and the proof tags.

One test per proof. Where several proofs share a starting spec, the spec is
written by a helper in this file and each test reads one case from it.
"""

import os
import re
import subprocess
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
from purlin import fingerprint as purlin_fingerprint  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402
from purlin import specs as purlin_specs  # noqa: E402
from purlin import status as purlin_status  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _project(tmp_path):
    """A project root with `.purlin/` and an empty `specs/test/`."""
    root = tmp_path / 'project'
    (root / '.purlin').mkdir(parents=True)
    (root / 'specs' / 'test').mkdir(parents=True)
    return root


def _write(root, rel_path, text):
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _feature(root, name):
    """The feature `name` as the dashboard's data carries it."""
    data = purlin_payload.build_payload(str(root))
    return next(f for f in data['features'] if f['name'] == name)


def _read(desc):
    """One proof text read into its text, manual mark, environment and the
    tags it does not read."""
    text, manual, env, unknown, _slow = purlin_specs.split_proof_tags(desc)
    return {'text': text, 'manual': manual, 'env': env, 'unknown': unknown}


def _git_project(root, *tracked):
    """Make `root` a git repository that tracks exactly `tracked`."""
    subprocess.run(['git', 'init', '-q'], cwd=str(root), check=True)
    if tracked:
        subprocess.run(['git', 'add', '--'] + list(tracked), cwd=str(root),
                       check=True)


def _login(root, first_line='# Feature: login', scope=None, rules=None,
           proofs=None):
    """`specs/test/login.md`, with the lines given and one rule by default."""
    text = first_line + '\n\n'
    if scope is not None:
        text += '> Scope: %s\n\n' % scope
    text += '## Rules\n\n' + (rules or '- RULE-1: One\n')
    text += '\n## Proof\n\n' + (proofs or '- PROOF-1 (RULE-1): Test one\n')
    _write(root, 'specs/test/login.md', text)


# ---------------------------------------------------------------------------
# RULE-1 and RULE-15: two sections, and a heading the format does not name
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-1
def test_the_format_reference_names_two_sections_and_no_third():
    with open(os.path.join(PROJECT_ROOT, 'references', 'formats',
                           'spec_format.md'), encoding='utf-8') as f:
        content = f.read()
    req_match = re.search(
        r'## Required [Ss]ections\s*\n(.*?)(?=^## |\Z)', content,
        re.MULTILINE | re.DOTALL)
    assert req_match, "No '## Required sections' heading in spec_format.md"
    named = re.findall(r'`(## [^`]+)`', req_match.group(1))
    assert named == ['## Rules', '## Proof'], (
        f"the format names exactly two sections and no third: {named}")


# purlin: schema_spec_format PROOF-13
def test_a_spec_with_a_heading_the_format_does_not_name_is_read_and_nothing_is_reported(
        tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/extra_heading.md',
           '# Feature: extra_heading\n\n'
           '> Description: A spec carrying a heading the format does not name\n\n'
           '## What it does\n\nIt does one thing.\n\n'
           '## Rules\n- RULE-1: The rule still counts\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test the rule\n')
    result = purlin_status.sync_status(str(root))
    assert 'extra_heading' in result, (
        f"a spec carrying `## What it does` was not read at all:\n{result}")
    assert not [line for line in result.splitlines()
                if 'is not numbered' in line], (
        f"an ignored heading must not be reported as a defect:\n{result}")
    assert 'What it does' not in result, (
        f"the report mentions the extra heading:\n{result}")
    rules = _feature(root, 'extra_heading')['rules']
    assert [r['id'] for r in rules] == ['RULE-1'], rules


# ---------------------------------------------------------------------------
# RULE-38, RULE-41 and RULE-39: unnumbered lines, gaps and doubled rule ids
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-2
def test_a_rule_line_with_no_id_is_reported_as_not_numbered(tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/test_feat.md',
           '# Feature: test_feat\n\n'
           '## Rules\n'
           '- some constraint without RULE-N prefix\n'
           '- RULE-1: A proper rule\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n')
    result = purlin_status.sync_status(str(root))
    assert ('test_feat: 1 line under ## Rules '
            'is not numbered; a rule is `- RULE-N: <text>`. '
            'Run purlin:spec test_feat.') in result.splitlines(), (
        f"the warning must name the spec, count its one line, give the "
        f"form and name the fix: {result}")


# purlin: schema_spec_format PROOF-14
def test_a_gap_in_the_rule_numbers_is_reported_as_nothing(tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/gapped_feat.md',
           '# Feature: gapped_feat\n\n'
           '## Rules\n'
           '- RULE-1: The first rule\n'
           '- RULE-3: The rule that outlived RULE-2\n'
           '- RULE-20: The rule numbered after sixteen retirements\n\n'
           '## Proof\n'
           '- PROOF-1 (RULE-1): Test one\n'
           '- PROOF-3 (RULE-3): Test three\n'
           '- PROOF-20 (RULE-20): Test twenty\n')
    result = purlin_status.sync_status(str(root))
    assert not [line for line in result.splitlines()
                if 'is not numbered' in line], (
        "a gap in the rule numbers is legal: a retired rule leaves its "
        f"number vacant and the rest are never renumbered:\n{result}")
    ids = [r['id'] for r in _feature(root, 'gapped_feat')['rules']]
    assert ids == ['RULE-1', 'RULE-3', 'RULE-20'], ids


# purlin: schema_spec_format PROOF-46
def test_a_rule_number_written_twice_is_warned_of_and_read_once(tmp_path):
    root = _project(tmp_path)
    _login(root, rules='- RULE-1: One\n- RULE-2: Old text\n'
                       '- RULE-2: New text\n',
           proofs='- PROOF-1 (RULE-1): Test one\n')
    result = purlin_status.sync_status(str(root))
    assert ('login: RULE-2 is written twice; the second is read. '
            'Run purlin:spec login.') in result.splitlines(), result
    rules = _feature(root, 'login')['rules']
    assert [(r['id'], r['text']) for r in rules] == [
        ('RULE-1', 'One'), ('RULE-2', 'New text')], rules


# ---------------------------------------------------------------------------
# RULE-3: the proof line
# ---------------------------------------------------------------------------


def _flow_spec(tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/flow.md',
           '# Feature: flow\n\n## Rules\n- RULE-1: One\n'
           '- RULE-2: Two\n- RULE-3: Three\n\n## Proof\n'
           '- PROOF-1 (RULE-1): One rule\n'
           '- PROOF-2 (RULE-2, RULE-3): One flow drives both\n'
           '- PROOF-3: No rule named\n')
    return purlin_specs.scan_specs(str(root))['flow']


# purlin: schema_spec_format PROOF-16
def test_a_proof_line_naming_two_rules_is_a_proof_of_both(tmp_path):
    info = _flow_spec(tmp_path)
    assert info['proofs']['PROOF-2']['rules'] == ['RULE-2', 'RULE-3'], \
        info['proofs']
    assert info['proofs_by_rule']['RULE-2'] == ['PROOF-2'], \
        info['proofs_by_rule']
    assert info['proofs_by_rule']['RULE-3'] == ['PROOF-2'], \
        info['proofs_by_rule']


# purlin: schema_spec_format PROOF-17
def test_a_proof_line_naming_no_rule_is_not_read_as_a_proof(tmp_path):
    info = _flow_spec(tmp_path)
    assert 'PROOF-3' not in info['proofs'], (
        f"a line naming no rule is not read as a proof: {info['proofs']}")


# ---------------------------------------------------------------------------
# RULE-6 and RULE-19: `> Scope:` and the fingerprint
# ---------------------------------------------------------------------------

def _scope_of(tmp_path, scope):
    root = _project(tmp_path)
    _write(root, 'specs/test/test_feat.md',
           '# Feature: test_feat\n\n'
           '> Scope: %s\n\n'
           '## Rules\n- RULE-1: Must work\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n' % scope)
    return purlin_specs.scan_specs(str(root))['test_feat']['scope']


# purlin: schema_spec_format PROOF-6
def test_the_scope_is_read_as_a_list_of_its_paths(tmp_path):
    scope = _scope_of(tmp_path, 'src/alpha.py, src/zeta.py')
    assert scope == ['src/alpha.py', 'src/zeta.py'], scope


def _scoped_project(tmp_path):
    """A git project tracking `src/app.py` and `src/other.py`, with a spec
    scoped `src/app.py`, and the code part of its fingerprint."""
    root = _project(tmp_path)
    for name in ('app.py', 'other.py'):
        _write(root, 'src/' + name, 'x = 1\n')
    _write(root, 'specs/test/test_feat.md',
           '# Feature: test_feat\n\n> Scope: src/app.py\n\n'
           '## Rules\n- RULE-1: Must work\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n')
    subprocess.run(['git', 'init', '-q'], cwd=str(root), check=True)
    subprocess.run(['git', 'add', '-A'], cwd=str(root), check=True)
    return root, purlin_fingerprint.fingerprint(str(root), 'test_feat')['code']


# purlin: schema_spec_format PROOF-23
def test_an_edit_outside_the_scope_leaves_the_code_fingerprint_unchanged(
        tmp_path):
    root, before = _scoped_project(tmp_path)
    _write(root, 'src/other.py', 'x = 2\n')
    assert purlin_fingerprint.fingerprint(str(root), 'test_feat')['code'] \
        == before, "a file outside the scope changed the fingerprint"


# purlin: schema_spec_format PROOF-24
def test_an_edit_inside_the_scope_changes_the_code_fingerprint(tmp_path):
    root, before = _scoped_project(tmp_path)
    _write(root, 'src/app.py', 'x = 2\n')
    assert purlin_fingerprint.fingerprint(str(root), 'test_feat')['code'] \
        != before, "a file inside the scope did not change the fingerprint"


# ---------------------------------------------------------------------------
# RULE-7: the first-level heading
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-49
def test_a_first_line_naming_another_feature_is_warned_of(tmp_path):
    root = _project(tmp_path)
    _login(root, first_line='# Feature: checkout')
    result = purlin_status.sync_status(str(root))
    assert ('login: the first line names checkout, but the file is '
            'login.md, so it is read as login. Run purlin:spec login.') \
        in result.splitlines(), result
    names = [f['name'] for f in
             purlin_payload.build_payload(str(root))['features']]
    assert names == ['login'], names


# ---------------------------------------------------------------------------
# RULE-9: the two tags, read off the end
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-9
def test_a_trailing_manual_tag_is_read():
    assert _read('Check it by hand @manual') == {
        'text': 'Check it by hand', 'manual': True, 'env': None,
        'unknown': []}


# purlin: schema_spec_format PROOF-26
def test_env_then_manual_reads_the_same_as_the_other_order():
    assert _read('Lock the file @env(windows) @manual') == \
        _read('Lock the file @manual @env(windows)') == {
            'text': 'Lock the file', 'manual': True, 'env': 'windows',
            'unknown': []}


# purlin: schema_spec_format PROOF-86
def test_slow_with_env_is_read_as_slow_on_that_system():
    text, manual, env, unknown, slow = purlin_specs.split_proof_tags(
        'Check out a cart of three items @slow @env(linux)')
    assert slow is True
    assert env == 'linux'
    assert manual is False
    assert text == 'Check out a cart of three items'
    assert unknown == []


# ---------------------------------------------------------------------------
# RULE-40: at-words that are no tag
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-28
def test_an_at_word_that_is_not_a_tag_stops_the_reading():
    desc = 'Lock the file @manual @smoke'
    assert _read(desc) == {'text': desc, 'manual': False, 'env': None,
                           'unknown': []}


# purlin: schema_spec_format PROOF-29
def test_an_at_word_after_a_comma_is_prose():
    desc = 'Check the documented tags @manual, @env'
    assert _read(desc) == {'text': desc, 'manual': False, 'env': None,
                           'unknown': []}


# ---------------------------------------------------------------------------
# RULE-10: the three systems, and what is not read
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-10
def test_env_windows_is_read():
    assert _read('Lock the file @env(windows)') == {
        'text': 'Lock the file', 'manual': False, 'env': 'windows',
        'unknown': []}


# purlin: schema_spec_format PROOF-38
def test_a_runner_name_is_not_an_operating_system():
    assert _read('Lock the file @env(windows-2022)') == {
        'text': 'Lock the file', 'manual': False, 'env': None,
        'unknown': ['@env(windows-2022)']}


# ---------------------------------------------------------------------------
# RULE-13: two specs with one name
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-52
def test_two_specs_with_one_name_are_warned_of_with_the_rename(tmp_path):
    root = _project(tmp_path)
    for folder in ('auth', 'admin'):
        _write(root, 'specs/%s/login.md' % folder,
               '# Feature: login\n\n## Rules\n- RULE-1: One\n\n'
               '## Proof\n- PROOF-1 (RULE-1): Test\n')
    result = purlin_status.sync_status(str(root))
    assert ('specs/auth/login.md and specs/admin/login.md are both named '
            'login; only specs/auth/login.md is read. Rename one: git mv '
            'specs/admin/login.md specs/admin/<new name>.md') \
        in result.splitlines(), result


# ---------------------------------------------------------------------------
# RULE-42: `> Highest-Rule:` and `> Stack:` change no fingerprint
# ---------------------------------------------------------------------------

def _three_rules(root, meta):
    """`specs/test/login.md` with `meta` above rules 1 to 3."""
    _write(root, 'specs/test/login.md',
           '# Feature: login\n\n' + meta + '\n## Rules\n- RULE-1: One\n'
           '- RULE-2: Two\n- RULE-3: Three\n\n## Proof\n'
           '- PROOF-1 (RULE-1): Test one\n')


# purlin: schema_spec_format PROOF-62
def test_a_highest_rule_line_changes_no_fingerprint(tmp_path):
    root = _project(tmp_path)
    _write(root, 'src/app.py', 'x = 1\n')
    _three_rules(root, '> Scope: src/app.py\n')
    _git_project(root, 'src/app.py')
    without = purlin_fingerprint.fingerprint(str(root), 'login')
    _three_rules(root, '> Scope: src/app.py\n> Highest-Rule: 12\n')
    assert purlin_fingerprint.fingerprint(str(root), 'login') == without


# purlin: schema_spec_format PROOF-66
def test_a_rewritten_stack_changes_no_fingerprint(tmp_path):
    root = _project(tmp_path)
    _write(root, 'src/app.py', 'x = 1\n')
    _three_rules(root, '> Scope: src/app.py\n> Stack: python/stdlib\n')
    _git_project(root, 'src/app.py')
    before = purlin_fingerprint.fingerprint(str(root), 'login')
    _three_rules(root, '> Scope: src/app.py\n> Stack: node/express\n')
    assert purlin_fingerprint.fingerprint(str(root), 'login') == before


# ---------------------------------------------------------------------------
# RULE-27: the format page's version line
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-64
def test_the_format_page_opens_with_its_version_line():
    with open(os.path.join(PROJECT_ROOT, 'references', 'formats',
                           'spec_format.md'), encoding='utf-8') as f:
        first = f.readline().rstrip('\r\n')
    assert re.fullmatch(r'> Format-Version: [0-9]+', first), first


# ---------------------------------------------------------------------------
# RULE-41: the next proof number
# ---------------------------------------------------------------------------


def _proof_format_sentences():
    """The sentences of the spec format page's `## Proof format` section,
    each read across its line breaks."""
    with open(os.path.join(PROJECT_ROOT, 'references', 'formats',
                           'spec_format.md'), encoding='utf-8') as f:
        page = f.read()
    section = re.search(r'^## Proof format\n(.*?)(?=^## )', page,
                        re.S | re.M)
    assert section, 'the spec format page has no section Proof format'
    return [' '.join(s.split()) for s in
            re.split(r'(?<=\.)\s+', section.group(1))]


# purlin: schema_spec_format PROOF-69
def test_a_new_proof_after_the_highest_is_deleted_takes_the_next_number():
    sentences = _proof_format_sentences()
    assert any('`> Highest-Proof:` reads `12`' in s
               and '`PROOF-10` to `PROOF-12` were deleted' in s
               and s.endswith('gives its next proof `PROOF-13`.')
               for s in sentences), sentences


# ---------------------------------------------------------------------------
# RULE-38 and RULE-32: the fields Purlin does not read
# ---------------------------------------------------------------------------

def _anchor_spec(root, name, meta, source=None):
    """The anchor `name` under `specs/_anchors/`, carrying `meta` and, for a
    remote anchor's copy, its `> Source:`."""
    lines = '# Anchor: %s\n\n' % name
    if source:
        lines += '> Source: %s\n> Pinned: abc1234def\n' % source
    lines += meta + '\n\n'
    lines += ('## Rules\n- RULE-1: No eval anywhere\n\n'
              '## Proof\n- PROOF-1 (RULE-1): Every file is searched\n')
    _write(root, 'specs/_anchors/%s.md' % name, lines)


def _login_carrying(root, meta):
    """The feature `login` with two rules, carrying `meta`."""
    _write(root, 'specs/test/login.md',
           '# Feature: login\n\n%s\n\n'
           '## Rules\n- RULE-1: One\n- RULE-2: Two\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n- PROOF-2 (RULE-2): Test\n'
           % meta)


# purlin: schema_spec_format PROOF-71
def test_a_requires_line_is_warned_of(tmp_path):
    root = _project(tmp_path)
    _anchor_spec(root, 'api', '> Description: The api.')
    _login_carrying(root, '> Requires: api')
    result = purlin_status.sync_status(str(root))
    assert ('login: > Requires: is not read, because every anchor covers the '
            'whole project. Run purlin:spec login.') \
        in result.splitlines(), result


# purlin: schema_spec_format PROOF-87
def test_slow_with_manual_is_warned_of_and_read_as_manual(tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/checkout.md',
           '# Feature: checkout\n\n'
           '## Rules\n- RULE-1: The cart checks out\n'
           '- RULE-2: The receipt looks right\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Check out three items; verify 30.00\n'
           '- PROOF-2 (RULE-2): Print the receipt and read it @manual @slow\n')
    result = purlin_status.sync_status(str(root))
    assert ('checkout: PROOF-2 is tagged @slow and @manual; a hand check has '
            'no test to leave out, so it is read as @manual. Run purlin:spec '
            'checkout.') in result.splitlines(), result
    proof = purlin_specs.scan_specs(str(root))['checkout']['proofs']['PROOF-2']
    assert proof['manual'] is True
    assert proof['slow'] is False


# purlin: schema_spec_format PROOF-76
def test_a_scope_line_on_an_anchor_is_not_read(tmp_path):
    root = _project(tmp_path)
    _anchor_spec(root, 'security', '> Scope: src/app.py, src/db.py')
    scope = purlin_specs.scan_specs(str(root))['security']['scope']
    assert scope == [], scope


BASELINE_SOURCE = 'https://github.com/acme/policies.git'


# purlin: schema_spec_format PROOF-78
def test_a_remote_anchor_carrying_a_scope_line_names_its_source(tmp_path):
    root = _project(tmp_path)
    _anchor_spec(root, 'security_baseline', '> Scope: src/',
                 source=BASELINE_SOURCE + ' specs/baseline.md')
    result = purlin_status.sync_status(str(root))
    assert ('security_baseline: its source, '
            'https://github.com/acme/policies.git, carries > Scope:, which '
            'Purlin does not read on an anchor, so the line is read as '
            'nothing. Ask the owners of https://github.com/acme/policies.git '
            'to take it out, then run purlin:anchor sync security_baseline.') \
        in result.splitlines(), result


# ---------------------------------------------------------------------------
# RULE-39: a proof number written twice, and a merge conflict line
# ---------------------------------------------------------------------------

def _numbered(root, lines):
    """`specs/test/login.md` holding exactly `lines`, line 1 first, so a
    test can say on which line of the file each one stands."""
    _write(root, 'specs/test/login.md', '\n'.join(lines) + '\n')


# purlin: schema_spec_format PROOF-81
def test_a_proof_number_written_twice_is_warned_of_and_read_once(tmp_path):
    root = _project(tmp_path)
    _login(root, rules='- RULE-1: One\n- RULE-2: Two\n',
           proofs='- PROOF-4 (RULE-1): Old text\n'
                  '- PROOF-4 (RULE-2): New text\n')
    result = purlin_status.sync_status(str(root))
    assert ('login: PROOF-4 is written twice; the second is read. '
            'Run purlin:spec login.') in result.splitlines(), result
    proofs = purlin_specs.scan_specs(str(root))['login']['proofs']
    assert list(proofs) == ['PROOF-4'], proofs
    assert proofs['PROOF-4']['text'] == 'New text', proofs


# purlin: schema_spec_format PROOF-82
def test_one_line_left_from_a_merge_conflict_is_warned_of_with_its_line(
        tmp_path):
    root = _project(tmp_path)
    _numbered(root, ['# Feature: login', '', '## Rules', '',
                     '- RULE-1: One', '', '## Proof', '',
                     '- PROOF-1 (RULE-1): Test one', '', '',
                     '=======', '- PROOF-2 (RULE-1): Test two'])
    result = purlin_status.sync_status(str(root))
    assert ('login: 1 line is left from a merge conflict, at line 12: '
            '=======. Run purlin:spec login.') in result.splitlines(), result

