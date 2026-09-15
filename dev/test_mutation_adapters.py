"""Tests for the engines behind test strength.

Covers engine selection for every framework and for an engine named in the
config, the arithmetic of test strength, the Stryker report parser (per test
and the per-scope fallback), the Stryker.NET command and report hunt, the
mutmut config block and results parser, the missing-binary and missing-config
paths, and the one shape `run_breaks` answers in.

The fixtures under `dev/fixtures/mutation/` are recorded output, not invented:
`stryker_report.json` is what StrykerJS 10 with the jest runner wrote for a
two-test project, with one `Timeout` and one `CompileError` mutant added by
hand so both statuses are covered; `mutmut_results_smoke.txt` is what
`mutmut results --all true` printed for a mutmut 3.8 run; `mutmut_results.txt`
is the same grammar over a project laid out under `src/`. No engine binary is
installed for these tests: every run is a stand-in that returns a recorded
report.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'run'))
import mutation
from mutation import mutmut, none, stryker, stryker_net

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures', 'mutation')


def read_fixture(name):
    with open(os.path.join(FIXTURES, name), 'r', encoding='utf-8') as handle:
        if name.endswith('.json'):
            return json.load(handle)
        return handle.read()


CALC_TESTS = {
    'RULE-1': [{'file': 'test/calc.test.js',
                'name': 'adds two numbers [proof:calc:PROOF-1:RULE-1]',
                'plugin': 'jest'}],
    'RULE-2': [{'file': 'test/calc.test.js',
                'name': 'leaves small values alone [proof:calc:PROOF-2:RULE-2]',
                'plugin': 'jest'}],
}

SESSION_TESTS = {
    'RULE-1': [{'file': 'tests/Login/SessionTests.cs',
                'name': 'LoginTests.LocksAfterFiveFailures '
                        '[proof:login:PROOF-1:RULE-1]',
                'plugin': 'xunit'}],
    'RULE-2': [{'file': 'tests/Login/SessionTests.cs',
                'name': 'LoginTests.UnlocksAfterFifteenMinutes '
                        '[proof:login:PROOF-2:RULE-2]',
                'plugin': 'xunit'}],
}


# ---------------------------------------------------------------------------
# Engine selection
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('framework,engine', [
    ('pytest', 'mutmut'),
    ('jest', 'stryker'),
    ('vitest', 'stryker'),
    ('xunit', 'stryker_net'),
    ('shell', 'none'),
    ('sql', 'none'),
])
@pytest.mark.proof("mutation", "PROOF-1", "RULE-1")
def test_auto_picks_the_engine_for_each_framework(framework, engine):
    assert mutation.select_engine({'mutation_engine': 'auto'},
                                  [framework]) == engine


@pytest.mark.proof("mutation", "PROOF-1", "RULE-1")
def test_auto_reads_the_first_framework_that_has_an_engine():
    assert mutation.select_engine({'mutation_engine': 'auto'},
                                  ['pytest', 'jest']) == 'mutmut'
    assert mutation.select_engine({'mutation_engine': 'auto'},
                                  ['jest', 'pytest']) == 'stryker'


@pytest.mark.proof("mutation", "PROOF-1", "RULE-1")
def test_auto_skips_a_framework_with_no_engine():
    assert mutation.select_engine({'mutation_engine': 'auto'},
                                  ['shell', 'xunit']) == 'stryker_net'


@pytest.mark.proof("mutation", "PROOF-1", "RULE-1")
def test_no_framework_leaves_no_engine():
    assert mutation.select_engine({'mutation_engine': 'auto'}, []) == 'none'
    assert mutation.select_engine({}, ['shell']) == 'none'


@pytest.mark.proof("mutation", "PROOF-2", "RULE-2")
def test_a_config_that_names_an_engine_wins_over_the_frameworks():
    assert mutation.select_engine({'mutation_engine': 'mutmut'},
                                  ['jest']) == 'mutmut'
    assert mutation.select_engine({'mutation_engine': 'none'},
                                  ['pytest']) == 'none'


@pytest.mark.proof("mutation", "PROOF-2", "RULE-2")
def test_an_engine_name_nobody_ships_reads_as_none():
    assert mutation.select_engine({'mutation_engine': 'cosmic-ray'},
                                  ['pytest']) == 'none'


@pytest.mark.proof("mutation", "PROOF-2", "RULE-2")
def test_a_missing_key_is_read_as_auto():
    assert mutation.select_engine({}, ['pytest']) == 'mutmut'
    assert mutation.select_engine(None, ['jest']) == 'stryker'


# ---------------------------------------------------------------------------
# Test strength arithmetic
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('killed,survived,score', [
    (0, 0, None),
    (1, 0, 100),
    (0, 1, 0),
    (1, 1, 50),
    (1, 2, 33),
    (2, 1, 67),
    (5, 2, 71),
    (7, 4, 64),
])
@pytest.mark.proof("mutation", "PROOF-3", "RULE-3")
def test_score_is_an_integer_percent(killed, survived, score):
    assert mutation.score_percent(killed, survived) == score


@pytest.mark.proof("mutation", "PROOF-4", "RULE-4")
def test_rules_are_listed_in_number_order():
    tests_by_rule = {('login', 'RULE-10'): [], ('login', 'RULE-2'): [],
                     ('reports', 'RULE-1'): []}
    assert mutation.rules_by_feature(tests_by_rule) == {
        'login': ['RULE-2', 'RULE-10'], 'reports': ['RULE-1']}


# ---------------------------------------------------------------------------
# Stryker: config, binary, runner
# ---------------------------------------------------------------------------

@pytest.mark.proof("mutation", "PROOF-5", "RULE-5")
def test_the_generated_config_scopes_the_run_to_the_spec_files():
    config = stryker.build_config(['src/calc.js', 'src/util.js'], 'jest',
                                  '/tmp/report.json')
    assert config == {
        'mutate': ['src/calc.js', 'src/util.js'],
        'coverageAnalysis': 'perTest',
        'disableBail': True,
        'reporters': ['json'],
        'testRunner': 'jest',
        'jsonReporter': {'fileName': '/tmp/report.json'},
    }


@pytest.mark.proof("mutation", "PROOF-6", "RULE-6")
def test_the_runner_is_vitest_when_the_project_declares_vitest(tmp_path):
    manifest = {'devDependencies': {'vitest': '^2.0.0'}}
    (tmp_path / 'package.json').write_text(json.dumps(manifest),
                                           encoding='utf-8')
    assert stryker.test_runner(str(tmp_path)) == 'vitest'


@pytest.mark.proof("mutation", "PROOF-6", "RULE-6")
def test_the_runner_is_jest_for_everything_else(tmp_path):
    manifest = {'devDependencies': {'jest': '^30.0.0'}}
    (tmp_path / 'package.json').write_text(json.dumps(manifest),
                                           encoding='utf-8')
    assert stryker.test_runner(str(tmp_path)) == 'jest'
    assert stryker.test_runner(str(tmp_path / 'nothing-here')) == 'jest'


@pytest.mark.proof("mutation", "PROOF-7", "RULE-7")
def test_the_project_binary_wins_over_one_on_the_path(tmp_path, monkeypatch):
    local = tmp_path / 'node_modules' / '.bin'
    local.mkdir(parents=True)
    (local / 'stryker').write_text('#!/bin/sh\n', encoding='utf-8')
    monkeypatch.setattr(stryker.shutil, 'which', lambda name: '/usr/bin/stryker')
    assert stryker.binary(str(tmp_path)) == [str(local / 'stryker')]


@pytest.mark.proof("mutation", "PROOF-7", "RULE-7")
def test_the_binary_is_none_when_stryker_is_not_installed(tmp_path, monkeypatch):
    monkeypatch.setattr(stryker.shutil, 'which', lambda name: None)
    assert stryker.binary(str(tmp_path)) is None


# ---------------------------------------------------------------------------
# Stryker: the report
# ---------------------------------------------------------------------------

@pytest.mark.proof("mutation", "PROOF-8", "RULE-8")
def test_the_scope_score_counts_timeouts_killed_and_uncovered_survived():
    entry = stryker.parse_report(read_fixture('stryker_report.json'),
                                 CALC_TESTS)
    assert entry['scope_score'] == {'score': 64, 'killed': 7, 'survived': 4}


@pytest.mark.proof("mutation", "PROOF-8", "RULE-8")
def test_a_break_that_never_reached_a_test_counts_for_neither():
    report = read_fixture('stryker_report.json')
    statuses = [m['status'] for m in report['files']['src/calc.js']['mutants']]
    assert 'CompileError' in statuses and len(statuses) == 12
    entry = stryker.parse_report(report, CALC_TESTS)
    counted = entry['scope_score']['killed'] + entry['scope_score']['survived']
    assert counted == 11


@pytest.mark.proof("mutation", "PROOF-9", "RULE-9")
def test_each_rule_carries_what_its_own_tests_caught():
    entry = stryker.parse_report(read_fixture('stryker_report.json'),
                                 CALC_TESTS)
    assert entry['rules']['RULE-1'] == {
        'engine': 'stryker', 'score': 100, 'killed': 3, 'survived': 0,
        'attribution': 'per_test'}
    assert entry['rules']['RULE-2'] == {
        'engine': 'stryker', 'score': 71, 'killed': 5, 'survived': 2,
        'attribution': 'per_test'}


@pytest.mark.proof("mutation", "PROOF-9", "RULE-9")
def test_a_break_another_rules_test_caught_counts_survived_for_this_one():
    report = read_fixture('stryker_report.json')
    entry = stryker.parse_report(report, {'RULE-2': CALC_TESTS['RULE-2']})
    # Mutants 4 and 5 are covered by RULE-2's test and killed by nothing.
    assert entry['rules']['RULE-2']['survived'] == 2


@pytest.mark.proof("mutation", "PROOF-9", "RULE-9")
def test_a_rule_whose_tests_the_report_never_saw_measures_nothing():
    tests = {'RULE-9': [{'file': 'test/other.test.js',
                         'name': 'unrelated [proof:calc:PROOF-9:RULE-9]',
                         'plugin': 'jest'}]}
    entry = stryker.parse_report(read_fixture('stryker_report.json'), tests)
    assert entry['rules']['RULE-9']['score'] is None
    assert entry['rules']['RULE-9']['killed'] == 0
    assert entry['rules']['RULE-9']['survived'] == 0


@pytest.mark.proof("mutation", "PROOF-10", "RULE-10")
def test_the_proof_marker_keeps_two_similar_test_names_apart():
    report = {
        'files': {'src/a.js': {'mutants': [
            {'id': '1', 'status': 'Killed', 'coveredBy': ['0'],
             'killedBy': ['0']},
            {'id': '2', 'status': 'Survived', 'coveredBy': ['1'],
             'killedBy': []},
        ]}},
        'testFiles': {'test/a.test.js': {'tests': [
            {'id': '0', 'name': 'locks [proof:login:PROOF-1:RULE-1]'},
            {'id': '1', 'name': 'locks after five [proof:login:PROOF-2:RULE-2]'},
        ]}},
    }
    tests = {
        'RULE-1': [{'file': 'test/a.test.js',
                    'name': 'locks [proof:login:PROOF-1:RULE-1]',
                    'plugin': 'jest'}],
        'RULE-2': [{'file': 'test/a.test.js',
                    'name': 'locks after five [proof:login:PROOF-2:RULE-2]',
                    'plugin': 'jest'}],
    }
    entry = stryker.parse_report(report, tests)
    assert entry['rules']['RULE-1']['killed'] == 1
    assert entry['rules']['RULE-1']['survived'] == 0
    assert entry['rules']['RULE-2']['killed'] == 0
    assert entry['rules']['RULE-2']['survived'] == 1


@pytest.mark.proof("mutation", "PROOF-10", "RULE-10")
def test_a_test_in_another_file_of_the_same_name_is_not_this_rules_test():
    report = {
        'files': {'src/a.js': {'mutants': [
            {'id': '1', 'status': 'Killed', 'coveredBy': ['0'],
             'killedBy': ['0']}]}},
        'testFiles': {'test/other.test.js': {'tests': [
            {'id': '0', 'name': 'locks the account'}]}},
    }
    tests = {'RULE-1': [{'file': 'test/login.test.js',
                         'name': 'locks the account', 'plugin': 'jest'}]}
    entry = stryker.parse_report(report, tests)
    assert entry['rules']['RULE-1']['killed'] == 0


@pytest.mark.proof("mutation", "PROOF-11", "RULE-11")
def test_a_report_that_names_no_killer_falls_back_to_the_scope_number():
    entry = stryker.parse_report(read_fixture('stryker_net_report.json'),
                                 SESSION_TESTS, engine='stryker_net')
    assert entry['scope_score'] == {'score': 60, 'killed': 3, 'survived': 2}
    for rule in ('RULE-1', 'RULE-2'):
        assert entry['rules'][rule] == {
            'engine': 'stryker_net', 'score': 60, 'killed': 3, 'survived': 2,
            'attribution': 'per_scope'}


@pytest.mark.proof("mutation", "PROOF-11", "RULE-11")
def test_a_named_killer_gives_stryker_net_per_test_attribution():
    entry = stryker.parse_report(read_fixture('stryker_report.json'),
                                 CALC_TESTS, engine='stryker_net')
    assert entry['rules']['RULE-1']['attribution'] == 'per_test'
    assert entry['rules']['RULE-1']['engine'] == 'stryker_net'


@pytest.mark.proof("mutation", "PROOF-12", "RULE-12")
def test_an_unreadable_report_is_not_a_report(tmp_path):
    path = tmp_path / 'report.json'
    path.write_text('not json', encoding='utf-8')
    assert stryker.read_report(str(path)) is None
    assert stryker.read_report(str(tmp_path / 'missing.json')) is None


# ---------------------------------------------------------------------------
# Stryker: the run
# ---------------------------------------------------------------------------

def fake_stryker_run(report_name):
    """A stand-in for the binary that writes `report_name` where asked."""
    seen = {}

    def execute(command, cwd, report_path=None):
        config_path = command[-1]
        with open(config_path, 'r', encoding='utf-8') as handle:
            config = json.load(handle)
        seen['config'] = config
        seen['command'] = command
        with open(config['jsonReporter']['fileName'], 'w',
                  encoding='utf-8') as handle:
            json.dump(read_fixture(report_name), handle)
        return 0, 'Done in 1 second.'

    return execute, seen


@pytest.mark.proof("mutation", "PROOF-5", "RULE-5")
def test_a_run_writes_the_scoped_config_and_reads_the_report(monkeypatch):
    execute, seen = fake_stryker_run('stryker_report.json')
    monkeypatch.setattr(stryker, 'binary', lambda root: ['stryker'])
    monkeypatch.setattr(stryker, 'test_runner', lambda root: 'jest')
    monkeypatch.setattr(stryker, 'execute', execute)
    answer = stryker.run('/project', {'calc': ['src/calc.js']},
                         {('calc', 'RULE-1'): CALC_TESTS['RULE-1'],
                          ('calc', 'RULE-2'): CALC_TESTS['RULE-2']}, 'unit')
    assert seen['config']['mutate'] == ['src/calc.js']
    assert seen['config']['coverageAnalysis'] == 'perTest'
    assert seen['config']['disableBail'] is True
    assert seen['config']['reporters'] == ['json']
    assert seen['command'][:2] == ['stryker', 'run']
    assert answer['engine'] == 'stryker'
    assert answer['available'] is True
    assert answer['features']['calc']['scope_score']['score'] == 64
    assert answer['features']['calc']['rules']['RULE-2']['score'] == 71
    assert 'calc' in answer['log']


@pytest.mark.proof("mutation", "PROOF-12", "RULE-12")
def test_a_feature_with_no_scope_files_measures_nothing(monkeypatch):
    execute, _ = fake_stryker_run('stryker_report.json')
    monkeypatch.setattr(stryker, 'binary', lambda root: ['stryker'])
    monkeypatch.setattr(stryker, 'test_runner', lambda root: 'jest')
    monkeypatch.setattr(stryker, 'execute', execute)
    answer = stryker.run('/project', {'calc': []},
                         {('calc', 'RULE-1'): CALC_TESTS['RULE-1']}, None)
    assert answer['features']['calc']['scope_score']['score'] is None
    assert answer['features']['calc']['rules']['RULE-1']['score'] is None
    assert 'no scope files' in answer['log']


@pytest.mark.proof("mutation", "PROOF-12", "RULE-12")
def test_a_run_that_wrote_no_report_says_so(monkeypatch):
    monkeypatch.setattr(stryker, 'binary', lambda root: ['stryker'])
    monkeypatch.setattr(stryker, 'test_runner', lambda root: 'jest')
    monkeypatch.setattr(stryker, 'execute',
                        lambda command, cwd, report_path=None: (1, 'boom'))
    answer = stryker.run('/project', {'calc': ['src/calc.js']},
                         {('calc', 'RULE-1'): CALC_TESTS['RULE-1']}, None)
    assert answer['features']['calc']['rules']['RULE-1']['score'] is None
    assert 'wrote no report' in answer['log']
    assert 'boom' in answer['log']


@pytest.mark.proof("mutation", "PROOF-7", "RULE-7")
def test_a_missing_binary_leaves_no_engine_and_says_what_to_install(monkeypatch):
    monkeypatch.setattr(stryker, 'binary', lambda root: None)
    answer = stryker.run('/project', {'calc': ['src/calc.js']},
                         {('calc', 'RULE-1'): CALC_TESTS['RULE-1']}, None)
    assert answer['engine'] == 'none'
    assert answer['available'] is False
    assert 'stryker is not installed' in answer['reason']
    rule = answer['features']['calc']['rules']['RULE-1']
    assert rule['attribution'] == 'unavailable'
    assert rule['score'] is None


# ---------------------------------------------------------------------------
# Stryker.NET
# ---------------------------------------------------------------------------

@pytest.mark.proof("mutation", "PROOF-13", "RULE-13")
def test_the_dotnet_command_scopes_the_run_and_asks_for_json():
    command = stryker_net.build_command(['dotnet', 'stryker'],
                                        ['src/Login/Session.cs', 'src/Api.cs'],
                                        '/tmp/out')
    assert command == ['dotnet', 'stryker',
                       '--mutate', 'src/Login/Session.cs',
                       '--mutate', 'src/Api.cs',
                       '--coverage-analysis', 'perTest', '--disable-bail',
                       '--reporter', 'json', '--output', '/tmp/out']


@pytest.mark.proof("mutation", "PROOF-14", "RULE-14")
def test_no_dotnet_means_no_engine(monkeypatch):
    monkeypatch.setattr(stryker_net.shutil, 'which', lambda name: None)
    installed, reason = stryker_net.available('/project')
    assert installed is False
    assert 'dotnet is not installed' in reason


@pytest.mark.proof("mutation", "PROOF-14", "RULE-14")
def test_dotnet_without_the_tool_says_how_to_install_it(monkeypatch):
    monkeypatch.setattr(stryker_net.shutil, 'which', lambda name: '/usr/bin/dotnet')
    monkeypatch.setattr(stryker_net, 'execute',
                        lambda command, cwd, report_path=None: (1, 'no such tool'))
    installed, reason = stryker_net.available('/project')
    assert installed is False
    assert 'dotnet tool install -g dotnet-stryker' in reason


@pytest.mark.proof("mutation", "PROOF-14", "RULE-14")
def test_the_tool_answering_its_version_is_the_install_check(monkeypatch):
    seen = {}

    def execute(command, cwd, report_path=None):
        seen['command'] = command
        return 0, '4.0.0'

    monkeypatch.setattr(stryker_net.shutil, 'which', lambda name: '/usr/bin/dotnet')
    monkeypatch.setattr(stryker_net, 'execute', execute)
    assert stryker_net.available('/project') == (True, '')
    assert seen['command'] == ['/usr/bin/dotnet', 'stryker', '--version']


@pytest.mark.proof("mutation", "PROOF-13", "RULE-13")
def test_the_report_is_found_under_the_output_directory(tmp_path):
    reports = tmp_path / 'reports'
    reports.mkdir()
    (reports / 'mutation-report.json').write_text('{}', encoding='utf-8')
    assert stryker_net.find_report(str(tmp_path)) == str(
        reports / 'mutation-report.json')


@pytest.mark.proof("mutation", "PROOF-13", "RULE-13")
def test_no_report_under_the_output_directory_is_none(tmp_path):
    assert stryker_net.find_report(str(tmp_path)) is None


@pytest.mark.proof("mutation", "PROOF-11", "RULE-11")
def test_a_dotnet_run_reports_per_scope_when_no_killer_is_named(monkeypatch):
    def execute(command, cwd, report_path=None):
        output_dir = command[command.index('--output') + 1]
        reports = os.path.join(output_dir, 'reports')
        os.makedirs(reports)
        with open(os.path.join(reports, 'mutation-report.json'), 'w',
                  encoding='utf-8') as handle:
            json.dump(read_fixture('stryker_net_report.json'), handle)
        return 0, ''

    monkeypatch.setattr(stryker_net, 'available', lambda root: (True, ''))
    monkeypatch.setattr(stryker_net, 'binary', lambda root=None: ['dotnet', 'stryker'])
    monkeypatch.setattr(stryker_net, 'execute', execute)
    answer = stryker_net.run('/project', {'login': ['src/Login/Session.cs']},
                             {('login', 'RULE-1'): SESSION_TESTS['RULE-1'],
                              ('login', 'RULE-2'): SESSION_TESTS['RULE-2']},
                             'unit')
    assert answer['engine'] == 'stryker_net'
    assert answer['features']['login']['scope_score']['score'] == 60
    rules = answer['features']['login']['rules']
    assert rules['RULE-1']['attribution'] == 'per_scope'
    assert rules['RULE-2']['score'] == 60
    assert 'attribution per_scope' in answer['log']


@pytest.mark.proof("mutation", "PROOF-14", "RULE-14")
def test_a_dotnet_run_with_no_tool_installed_leaves_no_engine(monkeypatch):
    monkeypatch.setattr(stryker_net, 'available',
                        lambda root: (False, 'dotnet is not installed'))
    answer = stryker_net.run('/project', {'login': ['src/Login/Session.cs']},
                             {('login', 'RULE-1'): SESSION_TESTS['RULE-1']},
                             None)
    assert answer['engine'] == 'none'
    assert answer['reason'] == 'dotnet is not installed'


# ---------------------------------------------------------------------------
# mutmut
# ---------------------------------------------------------------------------

@pytest.mark.proof("mutation", "PROOF-15", "RULE-15")
def test_the_config_block_for_pyproject_is_toml():
    block = mutmut.mutmut_config_block(['src'], ['tests'])
    assert block == ('[tool.mutmut]\n'
                     'source_paths = ["src"]\n'
                     'pytest_add_cli_args_test_selection = ["tests"]\n')


@pytest.mark.proof("mutation", "PROOF-15", "RULE-15")
def test_the_config_block_for_setup_cfg_is_one_value_a_line():
    block = mutmut.mutmut_config_block(['src', 'lib'], ['tests', '-q'],
                                       style='cfg')
    assert block == ('[mutmut]\n'
                     'source_paths =\n'
                     '    src\n'
                     '    lib\n'
                     'pytest_add_cli_args_test_selection =\n'
                     '    tests\n'
                     '    -q\n')


@pytest.mark.proof("mutation", "PROOF-15", "RULE-15")
def test_pyproject_holds_the_block_when_it_exists(tmp_path):
    (tmp_path / 'pyproject.toml').write_text('[project]\n', encoding='utf-8')
    assert mutmut.config_target(str(tmp_path)) == (
        'pyproject.toml', 'toml', '[tool.mutmut]')


@pytest.mark.proof("mutation", "PROOF-15", "RULE-15")
def test_setup_cfg_holds_the_block_when_there_is_no_pyproject(tmp_path):
    assert mutmut.config_target(str(tmp_path)) == (
        'setup.cfg', 'cfg', '[mutmut]')


@pytest.mark.proof("mutation", "PROOF-15", "RULE-15")
def test_the_block_is_found_once_it_is_written(tmp_path):
    path = tmp_path / 'pyproject.toml'
    path.write_text('[project]\nname = "demo"\n', encoding='utf-8')
    assert mutmut.has_config(str(tmp_path)) is False
    path.write_text('[project]\nname = "demo"\n\n'
                    + mutmut.mutmut_config_block(['src'], ['tests']),
                    encoding='utf-8')
    assert mutmut.has_config(str(tmp_path)) is True


@pytest.mark.proof("mutation", "PROOF-16", "RULE-16")
def test_the_results_of_a_real_run_are_read():
    entries = mutmut.parse_results(read_fixture('mutmut_results_smoke.txt'))
    assert len(entries) == 5
    assert entries[0] == {'key': 'calc.ops.x_add__mutmut_1', 'status': 'killed'}
    killed = [e for e in entries if e['status'] in mutmut.KILLED_STATUSES]
    assert len(killed) == 1


@pytest.mark.proof("mutation", "PROOF-16", "RULE-16")
def test_the_noise_around_the_results_is_not_a_break():
    text = ('2 files mutated, 0 ignored, 0 unmodified\n'
            '244.79 mutations/second\n'
            '    login.session.x_lock_account__mutmut_1: killed\n'
            'Error: something else entirely\n')
    entries = mutmut.parse_results(text)
    assert entries == [{'key': 'login.session.x_lock_account__mutmut_1',
                        'status': 'killed'}]


@pytest.mark.proof("mutation", "PROOF-17", "RULE-17")
def test_a_break_is_owned_by_the_scope_entry_that_matches_deepest():
    scope = ['src', 'src/login/session.py']
    assert mutmut.source_file('login.session.x_lock__mutmut_1',
                              scope) == 'src/login/session.py'
    assert mutmut.source_file('login.session.Session.x_reset__mutmut_1',
                              ['src/login/session.py']) == 'src/login/session.py'
    assert mutmut.source_file('calc.ops.x_add__mutmut_1', ['calc']) == 'calc'
    assert mutmut.source_file('other.thing.x_go__mutmut_1',
                              ['src/login/session.py']) is None


@pytest.mark.proof("mutation", "PROOF-21", "RULE-21")
def test_a_break_in_a_package_init_belongs_to_that_init():
    scope = ['scripts/run/mutation/__init__.py',
             'scripts/run/mutation/mutmut.py']
    assert mutmut.source_file(
        'scripts.run.mutation.x_score_percent__mutmut_1',
        scope) == 'scripts/run/mutation/__init__.py'
    assert mutmut.source_file(
        'scripts.run.mutation.mutmut.x_binary__mutmut_2',
        scope) == 'scripts/run/mutation/mutmut.py'


@pytest.mark.proof("mutation", "PROOF-21", "RULE-21")
def test_a_glob_scope_entry_covers_the_files_it_matches():
    assert mutmut.source_file('scripts.run.records.x_commit__mutmut_1',
                              ['scripts/**/*.py']) == 'scripts/**/*.py'
    assert mutmut.source_file('scripts.mcp.purlin.x_read__mutmut_1',
                              ['scripts/**/*.py']) == 'scripts/**/*.py'
    assert mutmut.source_file('dev.build_report.x_build__mutmut_1',
                              ['scripts/**/*.py']) is None
    assert mutmut.source_file(
        'scripts.run.records.x_commit__mutmut_1',
        ['scripts/**/*.py', 'scripts/run/records.py']) == \
        'scripts/run/records.py'


@pytest.mark.proof("mutation", "PROOF-17", "RULE-17")
def test_breaks_are_grouped_by_the_file_they_changed():
    entries = mutmut.parse_results(read_fixture('mutmut_results.txt'))
    counts = mutmut.group_by_file(entries, ['src/login/session.py',
                                            'src/reports/render.py'])
    assert counts['src/login/session.py'] == {'killed': 4, 'survived': 2}
    assert counts['src/reports/render.py'] == {'killed': 0, 'survived': 1}


@pytest.mark.proof("mutation", "PROOF-17", "RULE-17")
def test_a_break_outside_every_scope_is_left_out():
    entries = mutmut.parse_results(read_fixture('mutmut_results.txt'))
    counts = mutmut.group_by_file(entries, ['src/login/session.py'])
    assert list(counts) == ['src/login/session.py']
    assert sum(pair['killed'] + pair['survived']
               for pair in counts.values()) == 6


@pytest.mark.proof("mutation", "PROOF-17", "RULE-17")
def test_each_feature_gets_the_total_for_its_own_files():
    entries = mutmut.parse_results(read_fixture('mutmut_results.txt'))
    totals = mutmut.score_by_feature(entries,
                                     {'login': ['src/login/session.py'],
                                      'reports': ['src/reports/render.py']})
    assert totals == {'login': {'killed': 4, 'survived': 2},
                      'reports': {'killed': 0, 'survived': 1}}


@pytest.mark.proof("mutation", "PROOF-17", "RULE-17")
def test_a_mutmut_run_scores_every_rule_of_a_feature_the_same(tmp_path, monkeypatch):
    (tmp_path / 'pyproject.toml').write_text(
        '[project]\n' + mutmut.mutmut_config_block(['src'], ['tests']),
        encoding='utf-8')
    seen = []

    def execute(command, cwd, report_path=None):
        seen.append(command)
        if command[1] == 'results':
            return 0, read_fixture('mutmut_results.txt')
        return 0, 'done'

    monkeypatch.setattr(mutmut, 'binary', lambda root=None: '/usr/bin/mutmut')
    monkeypatch.setattr(mutmut, 'execute', execute)
    answer = mutmut.run(str(tmp_path),
                        {'login': ['src/login/session.py'],
                         'reports': ['src/reports/render.py']},
                        {('login', 'RULE-1'): [],
                         ('login', 'RULE-2'): [],
                         ('reports', 'RULE-1'): []}, 'unit')
    assert seen[0] == ['mutmut', 'run']
    assert seen[1] == ['mutmut', 'results', '--all', 'true']
    assert answer['engine'] == 'mutmut'
    assert answer['available'] is True
    login = answer['features']['login']
    assert login['scope_score'] == {'score': 67, 'killed': 4, 'survived': 2}
    for rule in ('RULE-1', 'RULE-2'):
        assert login['rules'][rule] == {
            'engine': 'mutmut', 'score': 67, 'killed': 4, 'survived': 2,
            'attribution': 'per_scope'}
    assert answer['features']['reports']['rules']['RULE-1']['score'] == 0


@pytest.mark.proof("mutation", "PROOF-18", "RULE-18")
def test_mutmut_missing_leaves_no_engine(monkeypatch):
    monkeypatch.setattr(mutmut, 'binary', lambda root=None: None)
    answer = mutmut.run('/project', {'login': ['src/login/session.py']},
                        {('login', 'RULE-1'): []}, None)
    assert answer['engine'] == 'none'
    assert 'pip install mutmut' in answer['reason']
    assert answer['features']['login']['rules']['RULE-1'][
        'attribution'] == 'unavailable'


@pytest.mark.proof("mutation", "PROOF-15", "RULE-15")
def test_a_project_with_no_config_block_is_not_broken(tmp_path, monkeypatch):
    (tmp_path / 'pyproject.toml').write_text('[project]\n', encoding='utf-8')
    monkeypatch.setattr(mutmut, 'binary', lambda root=None: '/usr/bin/mutmut')
    called = []
    monkeypatch.setattr(mutmut, 'execute',
                        lambda *args, **kwargs: called.append(args) or (0, ''))
    answer = mutmut.run(str(tmp_path), {'login': ['src/login/session.py']},
                        {('login', 'RULE-1'): []}, None)
    assert called == []
    assert answer['engine'] == 'none'
    assert '[tool.mutmut]' in answer['reason']
    assert 'pyproject.toml' in answer['reason']


# ---------------------------------------------------------------------------
# No engine, and the shape everything answers in
# ---------------------------------------------------------------------------

@pytest.mark.proof("mutation", "PROOF-19", "RULE-19")
def test_no_engine_measures_nothing_and_says_why():
    answer = none.run('/project', {'deploy': ['deploy.sh']},
                      {('deploy', 'RULE-1'): []})
    assert answer['engine'] == 'none'
    assert answer['available'] is False
    assert 'shell or sql' in answer['reason']
    assert answer['features']['deploy']['scope_score'] == {
        'score': None, 'killed': 0, 'survived': 0}
    assert answer['features']['deploy']['rules']['RULE-1'][
        'attribution'] == 'unavailable'


def assert_answer_shape(answer, scope_by_feature, tests_by_rule):
    assert set(answer) == {'engine', 'available', 'reason', 'features', 'log'}
    assert answer['engine'] in mutation.ENGINES
    assert isinstance(answer['available'], bool)
    assert isinstance(answer['reason'], str)
    assert isinstance(answer['log'], str)
    assert set(answer['features']) >= set(scope_by_feature)
    for feature, rule in tests_by_rule:
        entry = answer['features'][feature]
        assert set(entry['scope_score']) == {'score', 'killed', 'survived'}
        rule_score = entry['rules'][rule]
        assert set(rule_score) == {'engine', 'score', 'killed', 'survived',
                                   'attribution'}
        assert rule_score['attribution'] in mutation.ATTRIBUTIONS


@pytest.mark.proof("mutation", "PROOF-20", "RULE-20")
def test_run_breaks_answers_one_shape_for_no_engine():
    scope = {'deploy': ['deploy.sh']}
    tests = {('deploy', 'RULE-1'): []}
    answer = mutation.run_breaks('/project', 'none', scope, tests, None)
    assert_answer_shape(answer, scope, tests)
    assert answer['engine'] == 'none'


@pytest.mark.proof("mutation", "PROOF-20", "RULE-20")
def test_run_breaks_answers_one_shape_for_a_real_engine(tmp_path, monkeypatch):
    (tmp_path / 'pyproject.toml').write_text(
        '[project]\n' + mutmut.mutmut_config_block(['src'], ['tests']),
        encoding='utf-8')
    monkeypatch.setattr(mutmut, 'binary', lambda root=None: '/usr/bin/mutmut')
    monkeypatch.setattr(
        mutmut, 'execute',
        lambda command, cwd, report_path=None: (
            0, read_fixture('mutmut_results.txt') if command[1] == 'results'
            else 'done'))
    scope = {'login': ['src/login/session.py']}
    tests = {('login', 'RULE-1'): [], ('login', 'RULE-2'): []}
    answer = mutation.run_breaks(str(tmp_path), 'mutmut', scope, tests, 'unit')
    assert_answer_shape(answer, scope, tests)
    assert answer['features']['login']['rules']['RULE-1']['score'] == 67


@pytest.mark.proof("mutation", "PROOF-20", "RULE-20")
def test_an_engine_nobody_ships_is_not_run():
    scope = {'login': ['src/login/session.py']}
    tests = {('login', 'RULE-1'): []}
    answer = mutation.run_breaks('/project', 'cosmic-ray', scope, tests, None)
    assert_answer_shape(answer, scope, tests)
    assert answer['engine'] == 'none'
    assert 'unknown engine' in answer['reason']


@pytest.mark.proof("mutation", "PROOF-20", "RULE-20")
def test_a_rule_an_engine_forgot_is_filled_in():
    answer = mutation.normalise(
        {'engine': 'stryker', 'available': True, 'reason': '',
         'features': {'calc': {'scope_score': mutation.scope_entry(3, 1),
                               'rules': {}}},
         'log': ''},
        {'calc': ['src/calc.js']},
        {('calc', 'RULE-1'): [], ('calc', 'RULE-2'): []})
    assert answer['features']['calc']['rules']['RULE-1']['score'] is None
    assert answer['features']['calc']['rules']['RULE-1'][
        'attribution'] == 'unavailable'
    assert answer['features']['calc']['scope_score']['score'] == 75


@pytest.mark.proof("mutation", "PROOF-20", "RULE-20")
def test_a_feature_an_engine_never_reached_is_still_listed():
    answer = mutation.normalise(
        {'engine': 'mutmut', 'available': True, 'features': {}},
        {'login': ['src/login/session.py'], 'reports': []},
        {('login', 'RULE-1'): []})
    assert sorted(answer['features']) == ['login', 'reports']
    assert answer['features']['login']['rules']['RULE-1']['killed'] == 0
