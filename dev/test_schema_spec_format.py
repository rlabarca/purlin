"""Tests for schema_spec_format: the two sections, the rule and proof
grammar, the metadata fields and the proof tags.

One test per proof. Where several proofs share a starting spec, the spec is
written by a helper in this file and each test reads one case from it.
"""

import json
import os
import re
import subprocess
import sys

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'scripts', 'mcp'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from purlin import fingerprint as purlin_fingerprint  # noqa: E402
from purlin import payload as purlin_payload  # noqa: E402
from purlin import specs as purlin_specs  # noqa: E402
from purlin import status as purlin_status  # noqa: E402
import suites  # noqa: E402

RUN_SCRIPT = os.path.join(PROJECT_ROOT, 'scripts', 'run', 'purlin_run.py')


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


def _rule(root, name, rule_id):
    return next(r for r in _feature(root, name)['rules'] if r['id'] == rule_id)


def _read(desc):
    """One proof text read into its text, manual mark, environment and the
    tags it does not read."""
    text, manual, env, unknown = purlin_specs.split_proof_tags(desc)
    return {'text': text, 'manual': manual, 'env': env, 'unknown': unknown}


def _read_spec(tmp_path, line):
    """The spec `lock` whose `## Proof` holds `line`, read through a scan of
    the project."""
    root = _project(tmp_path)
    _write(root, 'specs/files/lock.md',
           '# Feature: lock\n\n## Rules\n\n'
           '- RULE-1: An open file cannot be deleted\n\n'
           '## Proof\n\n- PROOF-1 (RULE-1): ' + line + '\n')
    return purlin_specs.scan_specs(str(root))['lock']


def _read_spec_proof(tmp_path, line):
    """The one proof of a spec whose `## Proof` holds `line`, read from the
    spec file."""
    return _read_spec(tmp_path, line)['proofs']['PROOF-1']


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
# RULE-1 and RULE-15: two sections and no third
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
# RULE-2, RULE-16 and RULE-17: rule ids, gaps, unnumbered and doubled lines
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


# purlin: schema_spec_format PROOF-45
def test_two_rule_lines_with_no_id_are_counted_in_the_plural(tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/test_feat.md',
           '# Feature: test_feat\n\n'
           '## Rules\n'
           '- the first constraint without an id\n'
           '- RULE-1: A proper rule\n'
           '- the second constraint without an id\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n')
    result = purlin_status.sync_status(str(root))
    assert ('test_feat: 2 lines under ## Rules '
            'are not numbered; a rule is `- RULE-N: <text>`. '
            'Run purlin:spec test_feat.') in result.splitlines(), result


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
# RULE-3 and RULE-18: the proof line
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


# purlin: schema_spec_format PROOF-15
def test_a_proof_line_naming_one_rule_is_a_proof_of_that_rule_alone(tmp_path):
    info = _flow_spec(tmp_path)
    assert info['proofs']['PROOF-1']['rules'] == ['RULE-1'], info['proofs']
    assert info['proofs_by_rule']['RULE-1'] == ['PROOF-1'], \
        info['proofs_by_rule']


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


# purlin: schema_spec_format PROOF-47
def test_a_proof_line_that_cannot_be_read_is_warned_of(tmp_path):
    root = _project(tmp_path)
    _login(root, proofs='- PROOF-1 (RULE-1): Test one\n'
                        '- PROOF-7 shows the lockout\n')
    result = purlin_status.sync_status(str(root))
    assert ('login: a line under ## Proof cannot be read: '
            '- PROOF-7 shows the lockout. Run purlin:spec login.') \
        in result.splitlines(), result


# purlin: schema_spec_format PROOF-48
def test_a_long_proof_line_that_cannot_be_read_is_quoted_to_60_characters(
        tmp_path):
    root = _project(tmp_path)
    line = ('- PROOF-8 shows that a locked account stays locked for fifteen '
            'minutes after the fifth try')
    assert len(line) == 90
    _login(root, proofs='- PROOF-1 (RULE-1): Test one\n' + line + '\n')
    result = purlin_status.sync_status(str(root))
    assert ('login: a line under ## Proof cannot be read: '
            '- PROOF-8 shows that a locked account stays locked for fifte. '
            'Run purlin:spec login.') in result.splitlines(), result


# ---------------------------------------------------------------------------
# RULE-4: a rule no proof line names
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-4
def test_a_rule_with_no_proof_line_and_no_test_reads_no_proof_written(tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/test_feat.md',
           '# Feature: test_feat\n\n'
           '## Rules\n- RULE-1: Must work\n\n'
           '## Proof\n')
    rule = _rule(root, 'test_feat', 'RULE-1')
    assert rule['proofs'] == [], f"RULE-1 has no proof line: {rule}"
    cell = rule['cells']['passed']
    assert (cell['word'], cell['reasons']) == (
        'no test', ['no proof written']), cell


# purlin: schema_spec_format PROOF-18
def test_a_rule_with_a_proof_line_and_no_test_reads_no_test_without_the_reason(
        tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/test_feat.md',
           '# Feature: test_feat\n\n'
           '## Rules\n- RULE-1: Must work\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n')
    rule = _rule(root, 'test_feat', 'RULE-1')
    assert [p['id'] for p in rule['proofs']] == ['PROOF-1'], rule
    cell = rule['cells']['passed']
    assert cell['word'] == 'no test', cell
    assert 'no proof written' not in cell['reasons'], cell


# purlin: schema_spec_format PROOF-19
def test_a_rule_with_no_proof_line_is_answered_by_a_passing_test_marked_with_its_id(
        tmp_path):
    # The run starts pytest on the project's one test file and nothing else:
    # a test run at the gate `passed` reaches no model and no network.
    root = _project(tmp_path)
    _write(root, '.purlin/config.json', json.dumps(
        {'gate': 'passed', 'tests': [suites.pytest_suite()]}))
    _write(root, 'specs/a/feat.md',
           '# Feature: feat\n\n> Scope: src/\n\n'
           '## Rules\n\n- RULE-1: One\n\n## Proof\n\n')
    _write(root, 'src/a.py', 'x = 1\n')
    _write(root, 'tests/test_feat.py',
           '# purlin: feat RULE-1\n'
           'def test_ok():\n'
           '    assert 1 + 1 == 2\n')
    for command in (['git', 'init', '-q'], ['git', 'add', '-A'],
                    ['git', '-c', 'user.name=t', '-c', 'user.email=t@example.com',
                     'commit', '-qm', 'start']):
        subprocess.run(command, cwd=str(root), check=True)
    run = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', str(root),
         '--test', '--all'],
        capture_output=True, encoding='utf-8', cwd=str(root))
    assert run.returncode == 0, run.stdout + run.stderr
    rule = _rule(root, 'feat', 'RULE-1')
    assert rule['proofs'] == [], rule
    cell = rule['cells']['passed']
    assert (cell['word'], cell['reasons']) == ('passed', []), cell


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


# purlin: schema_spec_format PROOF-22
def test_the_scope_keeps_the_order_written_and_is_not_sorted(tmp_path):
    scope = _scope_of(tmp_path, 'src/zeta.py, src/alpha.py')
    assert scope == ['src/zeta.py', 'src/alpha.py'], scope


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


# purlin: schema_spec_format PROOF-50
def test_a_first_line_of_neither_form_is_read_by_the_file_name_and_not_warned_of(
        tmp_path):
    root = _project(tmp_path)
    _login(root, first_line='Login rules')
    result = purlin_status.sync_status(str(root))
    assert 'first line' not in result, result
    assert 'Login rules' not in result, result
    names = [f['name'] for f in
             purlin_payload.build_payload(str(root))['features']]
    assert names == ['login'], names


# purlin: schema_spec_format PROOF-51
def test_an_anchor_first_line_makes_a_spec_an_anchor_outside_the_anchors_folder(
        tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/base.md',
           '# Anchor: base\n\n## Rules\n- RULE-1: Base rule\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n')
    assert _feature(root, 'base')['is_anchor'] is True


# ---------------------------------------------------------------------------
# RULE-8: the description's continuation lines
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-8
def test_the_description_takes_its_continuation_and_not_the_next_field(tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/test_feat.md',
           '# Feature: test_feat\n\n'
           '> Description: First line\n'
           '>   second line\n'
           '> Scope: src/\n\n'
           '## Rules\n- RULE-1: Must work\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n')
    info = purlin_specs.scan_specs(str(root))['test_feat']
    desc = info.get('description') or ''
    assert 'First line' in desc, desc
    assert 'second line' in desc, desc
    assert 'src/' not in desc, (
        f"the description must not take the Scope field's value: {desc!r}")
    assert info.get('scope') == ['src/'], info.get('scope')


# ---------------------------------------------------------------------------
# RULE-9: the two tags, read off the end
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-9
def test_a_trailing_manual_tag_is_read():
    assert _read('Check it by hand @manual') == {
        'text': 'Check it by hand', 'manual': True, 'env': None,
        'unknown': []}


# purlin: schema_spec_format PROOF-25
def test_manual_then_env_is_read_as_manual_on_that_system():
    assert _read('Lock the file @manual @env(windows)') == {
        'text': 'Lock the file', 'manual': True, 'env': 'windows',
        'unknown': []}


# purlin: schema_spec_format PROOF-26
def test_env_then_manual_reads_the_same_as_the_other_order():
    assert _read('Lock the file @env(windows) @manual') == \
        _read('Lock the file @manual @env(windows)') == {
            'text': 'Lock the file', 'manual': True, 'env': 'windows',
            'unknown': []}


# purlin: schema_spec_format PROOF-56
def test_a_spec_proof_ending_manual_and_env_is_read_as_both(tmp_path):
    info = _read_spec(tmp_path, 'Lock a file; verify a second open fails '
                                '@manual @env(windows)')
    proof = info['proofs']['PROOF-1']
    assert proof['manual'] is True, proof
    assert proof['env'] == 'windows', proof
    assert proof['text'] == 'Lock a file; verify a second open fails', proof
    assert info['proof_env'] == {'PROOF-1': 'windows'}, info['proof_env']


# ---------------------------------------------------------------------------
# RULE-20 to RULE-23: two tags of a kind, and at-words that are no tag
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-57
def test_a_spec_proof_ending_in_a_word_that_is_not_a_tag_keeps_it(tmp_path):
    info = _read_spec(tmp_path, 'Call login and verify 200 @smoke')
    proof = info['proofs']['PROOF-1']
    assert proof['text'] == 'Call login and verify 200 @smoke', proof
    assert proof['manual'] is False, proof
    assert info['unknown_tags'] == [], info['unknown_tags']


# purlin: schema_spec_format PROOF-27
def test_a_trailing_at_word_that_is_not_a_tag_is_left_in_the_text():
    desc = 'Grep the file; verify present @smoke'
    assert _read(desc) == {'text': desc, 'manual': False, 'env': None,
                           'unknown': []}


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


# purlin: schema_spec_format PROOF-30
def test_an_at_word_after_or_is_prose():
    desc = 'Accepts either @env or @manual'
    assert _read(desc) == {'text': desc, 'manual': False, 'env': None,
                           'unknown': []}


# purlin: schema_spec_format PROOF-31
def test_an_at_word_after_and_is_prose():
    desc = 'Check the format lists @manual, @env and @windows'
    assert _read(desc) == {'text': desc, 'manual': False, 'env': None,
                           'unknown': []}


# purlin: schema_spec_format PROOF-32
def test_of_two_env_tags_the_last_written_is_the_system():
    assert _read('Lock the file @env(linux) @env(macos)') == {
        'text': 'Lock the file', 'manual': False, 'env': 'macos',
        'unknown': ['@env(linux)']}


# purlin: schema_spec_format PROOF-33
def test_a_doubled_manual_tag_reads_as_one():
    assert _read('Lock the file @manual @manual') == {
        'text': 'Lock the file', 'manual': True, 'env': None, 'unknown': []}


# purlin: schema_spec_format PROOF-34
def test_a_spec_proof_with_commas_in_its_prose_keeps_its_trailing_env_tag(
        tmp_path):
    proof = _read_spec_proof(
        tmp_path, 'Open the file, delete it, and read the refusal, '
                  'one line each @env(linux)')
    assert proof['env'] == 'linux', proof
    assert proof['manual'] is False, proof
    assert proof['text'] == ('Open the file, delete it, and read the '
                             'refusal, one line each'), proof


# purlin: schema_spec_format PROOF-35
def test_a_spec_proof_quoting_tags_mid_sentence_carries_no_tag(tmp_path):
    line = ('Read `Lock the file @env(macos) @manual` aloud and compare the '
            'two readings')
    proof = _read_spec_proof(tmp_path, line)
    assert proof['manual'] is False, proof
    assert proof['env'] is None, proof
    assert proof['text'] == line, proof


# ---------------------------------------------------------------------------
# RULE-10 and RULE-24: the three systems, and what is not read
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-10
def test_env_windows_is_read():
    assert _read('Lock the file @env(windows)') == {
        'text': 'Lock the file', 'manual': False, 'env': 'windows',
        'unknown': []}


# purlin: schema_spec_format PROOF-36
def test_env_macos_is_read():
    assert _read('Lock the file @env(macos)') == {
        'text': 'Lock the file', 'manual': False, 'env': 'macos',
        'unknown': []}


# purlin: schema_spec_format PROOF-37
def test_env_linux_is_read():
    assert _read('Lock the file @env(linux)') == {
        'text': 'Lock the file', 'manual': False, 'env': 'linux',
        'unknown': []}


# purlin: schema_spec_format PROOF-38
def test_a_runner_name_is_not_an_operating_system():
    assert _read('Lock the file @env(windows-2022)') == {
        'text': 'Lock the file', 'manual': False, 'env': None,
        'unknown': ['@env(windows-2022)']}


# purlin: schema_spec_format PROOF-39
def test_a_distribution_name_is_not_an_operating_system():
    assert _read('Lock the file @env(ubuntu-24.04)') == {
        'text': 'Lock the file', 'manual': False, 'env': None,
        'unknown': ['@env(ubuntu-24.04)']}


# purlin: schema_spec_format PROOF-40
def test_a_capitalised_system_name_is_not_read():
    assert _read('Lock the file @env(Windows)') == {
        'text': 'Lock the file', 'manual': False, 'env': None,
        'unknown': ['@env(Windows)']}


# purlin: schema_spec_format PROOF-41
def test_a_bare_windows_tag_sets_no_system():
    assert _read('Lock the file @windows') == {
        'text': 'Lock the file', 'manual': False, 'env': None,
        'unknown': ['@windows']}


# purlin: schema_spec_format PROOF-42
def test_a_manual_tag_carrying_a_value_still_reads_as_manual():
    assert _read('Lock the file @manual(2024-01-01)') == {
        'text': 'Lock the file', 'manual': True, 'env': None,
        'unknown': ['@manual(...)']}


# purlin: schema_spec_format PROOF-43
def test_another_at_word_carrying_a_value_is_not_read():
    assert _read('Lock the file @smoke(x)') == {
        'text': 'Lock the file', 'manual': False, 'env': None,
        'unknown': ['@smoke(...)']}


# ---------------------------------------------------------------------------
# RULE-11: `> Note:`
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-11
def test_note_lines_are_ignored_by_the_parser(tmp_path):
    root = _project(tmp_path)
    notes = ('Ask the security lead before the first sync',
             'The second note is ignored too')
    _write(root, 'specs/_anchors/policy.md',
           '# Anchor: policy\n\n'
           '> Description: Local policy\n'
           '> Note: %s\n'
           '> Note: %s\n'
           '> Source: ./vendor/policy.git\n'
           '> Pinned: d1e2816\n\n'
           '## Rules\n- RULE-1: No eval\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Grep src/ for eval(; verify zero '
           'matches\n' % notes)
    features = purlin_specs.scan_specs(str(root))
    assert 'policy' in features, f"the anchor was not read: {list(features)}"
    info = features['policy']
    assert info.get('description') == 'Local policy', info.get('description')
    assert info.get('source') == './vendor/policy.git', info.get('source')
    assert list(info.get('rules', {})) == ['RULE-1'], info.get('rules')
    read = json.dumps(info)
    for note in notes:
        assert note not in read, f"the note {note!r} reached what is read: {info}"


# ---------------------------------------------------------------------------
# RULE-12: the section headings, in any case
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-12
def test_the_section_headings_are_read_in_any_case(tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/shouty.md',
           '# Feature: shouty\n\n'
           '## rules\n- RULE-1: Headings read in any case\n\n'
           '## PROOF\n- PROOF-1 (RULE-1): Scan the spec; verify '
           'RULE-1 has PROOF-1\n')
    info = purlin_specs.scan_specs(str(root))['shouty']
    assert info['has_rules_section'] is True, info
    assert list(info['rules']) == ['RULE-1'], info['rules']
    assert info['proofs_by_rule'] == {'RULE-1': ['PROOF-1']}, info


# purlin: schema_spec_format PROOF-44
def test_a_heading_one_letter_off_is_neither_section(tmp_path):
    root = _project(tmp_path)
    _write(root, 'specs/test/near.md',
           '# Feature: near\n\n'
           '## Rule\n- RULE-1: A heading one letter short\n\n'
           '## Proofs\n- PROOF-1 (RULE-1): A heading one letter long\n')
    near = purlin_specs.scan_specs(str(root))['near']
    assert near['has_rules_section'] is False, near
    assert (near['rules'], near['proofs']) == ({}, {}), near


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
# RULE-14: a scope entry that finds no file
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-53
def test_a_scope_entry_that_finds_nothing_is_warned_of(tmp_path):
    root = _project(tmp_path)
    _write(root, 'src/app.py', 'x = 1\n')
    _login(root, scope='src/app.py, src/gone.py')
    _git_project(root, 'src/app.py')
    result = purlin_status.sync_status(str(root))
    assert ('login: > Scope: names src/gone.py, which finds no file in git. '
            'Run purlin:spec login.') in result.splitlines(), result


# purlin: schema_spec_format PROOF-54
def test_a_scope_entry_naming_an_untracked_file_is_warned_of(tmp_path):
    root = _project(tmp_path)
    _write(root, 'src/app.py', 'x = 1\n')
    _write(root, 'src/new.py', 'x = 2\n')
    _login(root, scope='src/app.py, src/new.py')
    _git_project(root, 'src/app.py')
    result = purlin_status.sync_status(str(root))
    assert ('login: > Scope: names src/new.py, which finds no file in git. '
            'Run purlin:spec login.') in result.splitlines(), result


# purlin: schema_spec_format PROOF-55
def test_a_scope_whose_every_entry_finds_nothing_gets_only_the_existing_line(
        tmp_path):
    root = _project(tmp_path)
    _write(root, 'src/app.py', 'x = 1\n')
    _login(root, scope='src/gone.py')
    _git_project(root, 'src/app.py')
    result = purlin_status.sync_status(str(root))
    assert ('1 spec names no files, so its tests run every time: login. '
            'Run purlin:spec login to add its > Scope: line.'
            in result.splitlines()), result
    assert 'which finds no file in git' not in result, result


# ---------------------------------------------------------------------------
# RULE-26: `> Highest-Rule:`
# ---------------------------------------------------------------------------

def _three_rules(root, meta):
    """`specs/test/login.md` with `meta` above rules 1 to 3."""
    _write(root, 'specs/test/login.md',
           '# Feature: login\n\n' + meta + '\n## Rules\n- RULE-1: One\n'
           '- RULE-2: Two\n- RULE-3: Three\n\n## Proof\n'
           '- PROOF-1 (RULE-1): Test one\n')


# purlin: schema_spec_format PROOF-61
def test_a_highest_rule_line_adds_no_rule(tmp_path):
    root = _project(tmp_path)
    _three_rules(root, '> Highest-Rule: 12\n')
    info = purlin_specs.scan_specs(str(root))['login']
    assert info['rule_order'] == ['RULE-1', 'RULE-2', 'RULE-3'], info


# purlin: schema_spec_format PROOF-62
def test_a_highest_rule_line_changes_no_fingerprint(tmp_path):
    root = _project(tmp_path)
    _write(root, 'src/app.py', 'x = 1\n')
    _three_rules(root, '> Scope: src/app.py\n')
    _git_project(root, 'src/app.py')
    without = purlin_fingerprint.fingerprint(str(root), 'login')
    _three_rules(root, '> Scope: src/app.py\n> Highest-Rule: 12\n')
    assert purlin_fingerprint.fingerprint(str(root), 'login') == without


# purlin: schema_spec_format PROOF-63
def test_a_highest_rule_line_leaves_the_description_above_it_whole(tmp_path):
    root = _project(tmp_path)
    _three_rules(root, '> Description: Signing in.\n')
    without = purlin_specs.scan_specs(str(root))['login']['description']
    _three_rules(root, '> Description: Signing in.\n> Highest-Rule: 12\n')
    info = purlin_specs.scan_specs(str(root))['login']
    assert (without, info['description']) == ('Signing in.', 'Signing in.')


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
# RULE-28: `> Stack:`
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-65
def test_the_stack_is_read_as_its_one_line(tmp_path):
    root = _project(tmp_path)
    _three_rules(root, '> Stack: python/stdlib, re, hashlib\n> Scope: src/\n')
    info = purlin_specs.scan_specs(str(root))['login']
    assert info['stack'] == 'python/stdlib, re, hashlib', info['stack']


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
# RULE-29: `> Highest-Proof:`
# ---------------------------------------------------------------------------

def _three_proofs(root, meta):
    """`specs/test/login.md` with `meta` above one rule and proofs 1 to 3."""
    _write(root, 'specs/test/login.md',
           '# Feature: login\n\n' + meta + '\n## Rules\n- RULE-1: One\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test one\n'
           '- PROOF-2 (RULE-1): Test two\n- PROOF-3 (RULE-1): Test three\n')


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


# purlin: schema_spec_format PROOF-67
def test_a_highest_proof_line_adds_no_proof(tmp_path):
    root = _project(tmp_path)
    _three_proofs(root, '> Highest-Proof: 12\n')
    info = purlin_specs.scan_specs(str(root))['login']
    assert sorted(info['proofs']) == ['PROOF-1', 'PROOF-2', 'PROOF-3'], info


# purlin: schema_spec_format PROOF-68
def test_a_highest_proof_line_changes_no_fingerprint(tmp_path):
    root = _project(tmp_path)
    _write(root, 'src/app.py', 'x = 1\n')
    _three_proofs(root, '> Scope: src/app.py\n')
    _git_project(root, 'src/app.py')
    without = purlin_fingerprint.fingerprint(str(root), 'login')
    _three_proofs(root, '> Scope: src/app.py\n> Highest-Proof: 12\n')
    assert purlin_fingerprint.fingerprint(str(root), 'login') == without


# purlin: schema_spec_format PROOF-69
def test_a_new_proof_after_the_highest_is_deleted_takes_the_next_number():
    sentences = _proof_format_sentences()
    assert any('`> Highest-Proof:` reads `12`' in s
               and '`PROOF-10` to `PROOF-12` were deleted' in s
               and s.endswith('gives its next proof `PROOF-13`.')
               for s in sentences), sentences


# purlin: schema_spec_format PROOF-70
def test_a_spec_with_no_highest_proof_line_counts_from_its_proofs():
    sentences = _proof_format_sentences()
    assert ('A spec with no `> Highest-Proof:` line whose proofs run to '
            '`PROOF-9` gives its next proof `PROOF-10`.') in sentences, \
        sentences


# ---------------------------------------------------------------------------
# RULE-30 to RULE-34: the fields Purlin does not read
# ---------------------------------------------------------------------------

def _anchor_spec(root, name, meta, source=None):
    """The anchor `name` under `specs/_anchors/`, carrying `meta` and, for a
    pinned copy, its `> Source:`."""
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


def _mistakes(root):
    """Every spec warning of the project, as the status report prints them."""
    return purlin_specs.spec_mistakes(
        str(root), purlin_specs.scan_specs(str(root)))


# purlin: schema_spec_format PROOF-71
def test_a_requires_line_is_warned_of(tmp_path):
    root = _project(tmp_path)
    _anchor_spec(root, 'api', '> Description: The api.')
    _login_carrying(root, '> Requires: api')
    result = purlin_status.sync_status(str(root))
    assert ('login: > Requires: is not read, because every anchor covers the '
            'whole project. Run purlin:spec login.') \
        in result.splitlines(), result


# purlin: schema_spec_format PROOF-72
def test_a_requires_line_adds_no_rule_of_the_anchor_it_names(tmp_path):
    root = _project(tmp_path)
    _anchor_spec(root, 'api', '> Description: The api.')
    _login_carrying(root, '> Requires: api')
    rules = [(r['feature'], r['id']) for r in _feature(root, 'login')['rules']]
    assert rules == [('login', 'RULE-1'), ('login', 'RULE-2')], rules


# purlin: schema_spec_format PROOF-73
def test_a_global_line_on_an_anchor_is_warned_of(tmp_path):
    root = _project(tmp_path)
    _anchor_spec(root, 'security', '> Global: true')
    assert ('security: > Global: is not read, because every anchor covers the '
            'whole project. Run purlin:spec security.') in _mistakes(root)


# purlin: schema_spec_format PROOF-74
def test_a_global_line_on_a_feature_is_warned_of(tmp_path):
    root = _project(tmp_path)
    _login_carrying(root, '> Global: true')
    assert ('login: > Global: is not read, because every anchor covers the '
            'whole project. Run purlin:spec login.') in _mistakes(root)


# purlin: schema_spec_format PROOF-75
def test_a_scope_line_on_an_anchor_is_warned_of(tmp_path):
    root = _project(tmp_path)
    _anchor_spec(root, 'security', '> Scope: src/')
    assert ('security: > Scope: is not read on an anchor, because an anchor '
            'covers the whole project. Run purlin:spec security.') \
        in _mistakes(root)


# purlin: schema_spec_format PROOF-76
def test_a_scope_line_on_an_anchor_is_not_read(tmp_path):
    root = _project(tmp_path)
    _anchor_spec(root, 'security', '> Scope: src/app.py, src/db.py')
    scope = purlin_specs.scan_specs(str(root))['security']['scope']
    assert scope == [], scope


# purlin: schema_spec_format PROOF-77
def test_an_anchor_scope_entry_is_never_warned_of_as_finding_no_file(
        tmp_path):
    root = _project(tmp_path)
    _write(root, 'src/app.py', 'x = 1\n')
    _anchor_spec(root, 'security', '> Scope: src/app.py, src/gone.py')
    _git_project(root, 'src/app.py')
    result = purlin_status.sync_status(str(root))
    assert ('security: > Scope: is not read on an anchor, because an anchor '
            'covers the whole project. Run purlin:spec security.') \
        in result.splitlines(), result
    assert 'which finds no file in git' not in result, result


BASELINE_SOURCE = 'https://github.com/acme/policies.git'


# purlin: schema_spec_format PROOF-78
def test_a_pinned_anchor_carrying_a_scope_line_names_its_source(tmp_path):
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


# purlin: schema_spec_format PROOF-79
def test_a_pinned_anchor_carrying_two_lines_gets_the_one_plural_line(
        tmp_path):
    root = _project(tmp_path)
    _anchor_spec(root, 'security_baseline', '> Global: true\n> Scope: src/',
                 source=BASELINE_SOURCE)
    lines = [line for line in _mistakes(root)
             if line.startswith('security_baseline:')]
    assert lines == [
        'security_baseline: its source, https://github.com/acme/policies.git, '
        'carries > Global: and > Scope:, which Purlin does not read on an '
        'anchor, so the lines are read as nothing. Ask the owners of '
        'https://github.com/acme/policies.git to take them out, then run '
        'purlin:anchor sync security_baseline.'], lines


# purlin: schema_spec_format PROOF-80
def test_the_pinned_anchor_line_starts_no_process(tmp_path, monkeypatch):
    root = _project(tmp_path)
    _anchor_spec(root, 'security_baseline', '> Scope: src/',
                 source=BASELINE_SOURCE)

    def refused(*args, **kwargs):
        raise AssertionError('a process was started: %r' % (args,))

    monkeypatch.setattr(subprocess, 'Popen', refused)
    monkeypatch.setattr(subprocess, 'run', refused)
    monkeypatch.setattr(os, 'system', refused)
    lines = _mistakes(root)
    assert any(line.startswith('security_baseline: its source, '
                               + BASELINE_SOURCE + ', carries > Scope:')
               for line in lines), lines


# ---------------------------------------------------------------------------
# RULE-35 to RULE-37: a proof number written twice, a merge conflict line,
# and the reasons a spec's rules fail
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


# purlin: schema_spec_format PROOF-83
def test_a_conflict_hunk_is_warned_of_in_one_line_naming_its_first_line(
        tmp_path):
    root = _project(tmp_path)
    _numbered(root, ['# Feature: login', '', '## Rules', '',
                     '- RULE-1: One', '', '## Proof', '',
                     '<<<<<<< HEAD', '- PROOF-1 (RULE-1): Test one',
                     '=======', '- PROOF-1 (RULE-1): Test the first',
                     '>>>>>>> main'])
    result = purlin_status.sync_status(str(root))
    lines = [line for line in result.splitlines()
             if 'left from a merge conflict' in line]
    assert lines == [
        'login: 3 lines are left from a merge conflict, the first at line 9: '
        '<<<<<<< HEAD. Run purlin:spec login.'], result


# purlin: schema_spec_format PROOF-84
def test_a_line_of_eight_equals_signs_is_not_a_conflict_line(tmp_path):
    root = _project(tmp_path)
    _numbered(root, ['# Feature: login', '', '## Rules', '',
                     '- RULE-1: One', '', '========', '', '## Proof', '',
                     '- PROOF-1 (RULE-1): Test one'])
    result = purlin_status.sync_status(str(root))
    assert 'left from a merge conflict' not in result, result


# purlin: schema_spec_format PROOF-85
def test_the_reasons_a_broken_spec_fails_are_named_in_order(tmp_path):
    root = _project(tmp_path)
    _numbered(root, ['# Feature: login', '', '## Rules', '',
                     '- RULE-1: One', '- RULE-2: Two', '- RULE-2: Deux', '',
                     '## Proof', '', '- PROOF-4 (RULE-1): Test one',
                     '=======', '- PROOF-4 (RULE-2): Test two'])
    info = purlin_specs.scan_specs(str(root))['login']
    assert purlin_specs.broken_reasons(info) == [
        'RULE-2 is written twice in the spec',
        'PROOF-4 is written twice in the spec',
        'the spec holds a line left from a merge conflict']
