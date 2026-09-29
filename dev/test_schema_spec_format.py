"""Tests for schema_spec_format: the two sections, the rule and proof
grammar, the metadata fields and the proof tags.

One test per proof. Where several proofs share a starting spec, the spec is
written by a helper in this file and each test reads one case from it.
"""

import glob
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


def _read_spec_proof(tmp_path, line):
    """The one proof of a spec whose `## Proof` holds `line`, read from the
    spec file."""
    root = _project(tmp_path)
    _write(root, 'specs/files/lock.md',
           '# Feature: lock\n\n## Rules\n\n'
           '- RULE-1: An open file cannot be deleted\n\n'
           '## Proof\n\n- PROOF-1 (RULE-1): ' + line + '\n')
    return purlin_specs.scan_specs(str(root))['lock']['proofs']['PROOF-1']


def _proof_section_items(content):
    section = re.search(r'^## Proof\s*\n(.*?)(?=^## |\Z)', content,
                        re.MULTILINE | re.DOTALL)
    if not section:
        return []
    return [line.strip() for line in section.group(1).strip().splitlines()
            if line.strip().startswith('- ')]


def _this_projects_specs():
    return sorted(glob.glob(os.path.join(PROJECT_ROOT, 'specs', '**', '*.md'),
                            recursive=True))


# ---------------------------------------------------------------------------
# RULE-1: two sections and no third
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
    assert 'WARNING' not in result, (
        f"an ignored heading must not be reported as a defect:\n{result}")
    assert 'What it does' not in result, (
        f"the report mentions the extra heading:\n{result}")
    rules = _feature(root, 'extra_heading')['rules']
    assert [r['id'] for r in rules] == ['RULE-1'], rules


# ---------------------------------------------------------------------------
# RULE-2: rule ids, gaps and unnumbered lines
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
    assert ('WARNING: 1 lines under ## Rules in specs/test/test_feat.md '
            'are not numbered; a rule is `- RULE-N: <text>`.') in result, (
        f"the warning must name the spec, count its one line and give the "
        f"form: {result}")


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
    assert 'WARNING' not in result, (
        "a gap in the rule numbers is legal: a retired rule leaves its "
        f"number vacant and the rest are never renumbered:\n{result}")
    ids = [r['id'] for r in _feature(root, 'gapped_feat')['rules']]
    assert ids == ['RULE-1', 'RULE-3', 'RULE-20'], ids


# ---------------------------------------------------------------------------
# RULE-3: the proof line
# ---------------------------------------------------------------------------

# purlin: schema_spec_format PROOF-3
def test_every_proof_line_of_this_project_names_a_proof_and_its_rule():
    pattern = re.compile(r'^-\s+PROOF-\d+\s+\(RULE-\d+\)')
    for path in _this_projects_specs():
        with open(path, encoding='utf-8') as f:
            content = f.read()
        for line in _proof_section_items(content):
            assert pattern.match(line), f"Bad proof line in {path}: {line}"


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
# RULE-5: `> Requires:`
# ---------------------------------------------------------------------------

def _anchors(root):
    _write(root, 'specs/_anchors/base.md',
           '# Anchor: base\n\n'
           '## Rules\n- RULE-1: Base rule\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n')
    _write(root, 'specs/_anchors/other.md',
           '# Anchor: other\n\n## Rules\n- RULE-1: Other rule\n'
           '- RULE-2: Second other rule\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n'
           '- PROOF-2 (RULE-2): Test\n')


def _requiring(root, requires):
    _write(root, 'specs/test/test_feat.md',
           '# Feature: test_feat\n\n'
           '> Requires: %s\n\n'
           '## Rules\n- RULE-1: Own rule\n\n'
           '## Proof\n- PROOF-1 (RULE-1): Test\n' % requires)
    return [(r['feature'], r['id'], r['label'])
            for r in _feature(root, 'test_feat')['rules']]


# purlin: schema_spec_format PROOF-5
def test_the_rules_of_a_required_anchor_are_labelled_required(tmp_path):
    root = _project(tmp_path)
    _anchors(root)
    rules = _requiring(root, 'base')
    required = [(f, r) for f, r, label in rules if label == 'required']
    assert required == [('base', 'RULE-1')], (
        f"the required spec's rules are not counted with the feature's own: "
        f"{rules}")


# purlin: schema_spec_format PROOF-20
def test_two_required_names_are_read_in_the_order_written_after_the_own_rules(
        tmp_path):
    root = _project(tmp_path)
    _anchors(root)
    assert _requiring(root, 'other, base') == [
        ('test_feat', 'RULE-1', 'own'),
        ('other', 'RULE-1', 'required'), ('other', 'RULE-2', 'required'),
        ('base', 'RULE-1', 'required')]


# purlin: schema_spec_format PROOF-21
def test_a_required_name_no_spec_carries_adds_no_rule(tmp_path):
    root = _project(tmp_path)
    _anchors(root)
    assert _requiring(root, 'base, ghost') == [
        ('test_feat', 'RULE-1', 'own'), ('base', 'RULE-1', 'required')]


# ---------------------------------------------------------------------------
# RULE-6: `> Scope:` and the fingerprint
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

# purlin: schema_spec_format PROOF-7
def test_every_first_level_heading_of_this_project_names_a_feature_or_an_anchor():
    valid = re.compile(r'^# (Feature|Anchor): ')
    for path in _this_projects_specs():
        with open(path, encoding='utf-8') as f:
            content = f.read()
        for heading in re.findall(r'^# .+', content, re.MULTILINE):
            assert valid.match(heading), \
                f"Invalid heading in {path}: {heading}"


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
# RULE-10: the three systems, and what is not read
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
