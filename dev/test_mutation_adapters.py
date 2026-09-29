"""Tests for the engines behind test strength.

Covers engine selection for every framework and for an engine named in the
config, the arithmetic of test strength, what Stryker, Stryker.NET and mutmut
are started with and how what they report is counted, the missing-program
and missing-config answers, the one shape every answer takes, and an engine
that runs past `--arm-timeout`.

The fixtures under `dev/fixtures/mutation/` are captured output, not invented:
`stryker_report.json` is what StrykerJS 10 with the jest runner wrote for a
two-test project, with one `Timeout` and one `CompileError` mutant added by
hand so both statuses are covered; `mutmut_results_smoke.txt` is what
`mutmut results --all true` printed for a mutmut 3.8 run; `mutmut_results.txt`
is the same grammar over a project laid out under `src/`.

No real engine is ever started. Each run test puts a stand-in program where
the real one would be found, `node_modules/.bin/stryker`, or `dotnet` or
`mutmut` in a folder that is the whole of PATH beside `/usr/bin` and `/bin`.
The stand-in writes the captured report where it is told, records how it was
started, and, when asked, sleeps past the limit so the real stop is
observed. Everything between the engine's answer and the program is the
code under test.
"""

import json
import os
import subprocess
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'run'))
import mutation
from mutation import mutmut, stryker, stryker_net

FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures', 'mutation')
RUN_SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'run',
                          'purlin_run.py')


def read_fixture(name):
    with open(os.path.join(FIXTURES, name), 'r', encoding='utf-8') as handle:
        if name.endswith('.json'):
            return json.load(handle)
        return handle.read()


CALC_TESTS = {
    'RULE-1': [{'file': 'test/calc.test.js',
                'name': 'adds two numbers'}],
    'RULE-2': [{'file': 'test/calc.test.js',
                'name': 'leaves small values alone'}],
}

SESSION_TESTS = {
    'RULE-1': [{'file': 'tests/Login/SessionTests.cs',
                'name': 'LoginTests.LocksAfterFiveFailures'}],
    'RULE-2': [{'file': 'tests/Login/SessionTests.cs',
                'name': 'LoginTests.UnlocksAfterFifteenMinutes'}],
}

TIMEOUT_REASON = ('the engine timed out after %d s, so the breaks it made are '
                  'partial and measure nothing: raise --arm-timeout to give it '
                  'longer')


# ---------------------------------------------------------------------------
# Stand-in engine programs
# ---------------------------------------------------------------------------

_PRELUDE = r'''
import json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
NAME = os.path.basename(__file__)
with open(os.path.join(HERE, NAME + '.setup.json'), encoding='utf-8') as handle:
    SETUP = json.load(handle)


def record(**extra):
    extra['argv'] = sys.argv[1:]
    with open(os.path.join(HERE, NAME + '.calls'), 'a', encoding='utf-8') as log:
        log.write(json.dumps(extra) + '\n')


def write_report(path, report):
    if report is None:
        return
    with open(path, 'w', encoding='utf-8') as handle:
        if isinstance(report, str):
            handle.write(report)
        else:
            json.dump(report, handle)
'''

# `stryker run <config>`: writes the report where the config says. The
# feature is the config's file name, `<feature>.conf.json`.
_STRYKER = r'''
config_path = sys.argv[-1]
with open(config_path, encoding='utf-8') as handle:
    config = json.load(handle)
feature = os.path.basename(config_path).split('.')[0]
record(config=config)
report = SETUP.get('reports', {}).get(feature, SETUP.get('report'))
write_report(config['jsonReporter']['fileName'], report)
sys.stdout.write(SETUP.get('print', ''))
sys.stdout.flush()
if feature in SETUP.get('slow', []):
    time.sleep(60)
sys.exit(SETUP.get('exit', 0))
'''

# `dotnet stryker --version`, and `dotnet stryker ... --output <folder>`,
# which writes `mutation-report.json` under the folder. The feature is the
# folder's name.
_DOTNET = r'''
argv = sys.argv[1:]
record()
if argv == ['stryker', '--version']:
    sys.exit(SETUP.get('version_exit', 0))
output = argv[argv.index('--output') + 1]
feature = os.path.basename(output)
report = SETUP.get('reports', {}).get(feature, SETUP.get('report'))
if report is not None:
    folder = os.path.join(output, *SETUP.get('folder', ['reports']))
    os.makedirs(folder, exist_ok=True)
    write_report(os.path.join(folder, 'mutation-report.json'), report)
if feature in SETUP.get('slow', []):
    time.sleep(60)
sys.exit(0)
'''

# `mutmut run` and `mutmut results --all true`; anything else prints nothing.
_MUTMUT = r'''
argv = sys.argv[1:]
record()
if argv[:1] == ['run']:
    print('started')
    sys.stdout.flush()
    if SETUP.get('slow'):
        time.sleep(60)
    sys.exit(0)
if argv == ['results', '--all', 'true']:
    sys.stdout.write(SETUP.get('listing', ''))
sys.exit(0)
'''


def install_program(where, name, body, **setup):
    """Write an executable stand-in `name` into the folder `where`. Its path."""
    where.mkdir(parents=True, exist_ok=True)
    (where / (name + '.setup.json')).write_text(json.dumps(setup),
                                                 encoding='utf-8')
    program = where / name
    program.write_text('#!%s\n%s\n%s' % (sys.executable, _PRELUDE, body),
                       encoding='utf-8')
    program.chmod(0o755)
    return program


def calls(program):
    """What the stand-in at `program` was started with, one dict per start."""
    path = str(program) + '.calls'
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


@pytest.fixture(autouse=True)
def tools(tmp_path, monkeypatch):
    """A folder that, beside `/usr/bin` and `/bin`, is the whole of PATH.

    Neither of those holds an engine or `claude`, so in every test here a
    program is found only when the test puts its stand-in in this folder.
    """
    folder = tmp_path / 'bin'
    folder.mkdir()
    monkeypatch.setenv('PATH', os.pathsep.join([str(folder), '/usr/bin',
                                                '/bin']))
    return folder


@pytest.fixture
def project(tmp_path):
    root = tmp_path / 'project'
    root.mkdir()
    return root


def install_stryker(project, **setup):
    """The project's own Stryker, answering the captured report by default."""
    setup.setdefault('report', read_fixture('stryker_report.json'))
    return install_program(project / 'node_modules' / '.bin', 'stryker',
                           _STRYKER, **setup)


def install_dotnet(tools, **setup):
    setup.setdefault('report', read_fixture('stryker_net_report.json'))
    return install_program(tools, 'dotnet', _DOTNET, **setup)


def install_mutmut(tools, **setup):
    return install_program(tools, 'mutmut', _MUTMUT, **setup)


def with_block(project):
    (project / 'pyproject.toml').write_text(
        '[project]\n' + mutmut.mutmut_config_block(['src'], ['tests']),
        encoding='utf-8')


def feature_tests(feature, tests):
    return dict(((feature, rule), value) for rule, value in tests.items())


def calc_run(project, report, tests):
    """One Stryker run of `calc`, scoped to `src/calc.js`, over `report`."""
    install_stryker(project, report=report)
    return stryker.run(str(project), {'calc': ['src/calc.js']},
                       feature_tests('calc', tests))


def login_run(tools, project, report, tests, **setup):
    """One Stryker.NET run of `login`, scoped to `src/Login/Session.cs`."""
    install_dotnet(tools, report=report, **setup)
    return stryker_net.run(str(project), {'login': ['src/Login/Session.cs']},
                           feature_tests('login', tests))


def mutmut_run(tools, project, listing, scope_by_feature, tests_by_rule):
    with_block(project)
    install_mutmut(tools, listing=listing)
    return mutmut.run(str(project), scope_by_feature, tests_by_rule)


def one_break_report(mutants, tests):
    """A Stryker report of breaks to `src/a.js` and tests in `test/a.test.js`."""
    return {'files': {'src/a.js': {'mutants': mutants}},
            'testFiles': {'test/a.test.js': {'tests': [
                {'id': str(index), 'name': name}
                for index, name in enumerate(tests)]}}}


def a_test(name, path='test/a.test.js'):
    return [{'file': path, 'name': name}]


# ---------------------------------------------------------------------------
# Engine selection
# ---------------------------------------------------------------------------

AUTO = {'mutation_engine': 'auto'}


@pytest.mark.parametrize('framework,engine', [
    ('jest', 'stryker'),
    ('vitest', 'stryker'),
    ('dotnet', 'stryker_net'),
    ('pytest', 'mutmut'),
])
# purlin: mutation PROOF-1
def test_auto_picks_the_engine_of_the_one_framework(framework, engine):
    assert mutation.select_engine(AUTO, [framework]) == engine


@pytest.mark.parametrize('framework', ['go', 'shell', 'sql'])
# purlin: mutation PROOF-23
def test_auto_picks_no_engine_for_go_shell_or_sql(framework):
    assert mutation.select_engine(AUTO, [framework]) == 'none'


# purlin: mutation PROOF-24
def test_auto_with_pytest_first_picks_mutmut():
    assert mutation.select_engine(AUTO, ['pytest', 'jest']) == 'mutmut'


# purlin: mutation PROOF-25
def test_auto_with_jest_first_picks_stryker():
    assert mutation.select_engine(AUTO, ['jest', 'pytest']) == 'stryker'


# purlin: mutation PROOF-26
def test_auto_passes_over_a_framework_with_no_engine():
    assert mutation.select_engine(AUTO, ['shell', 'dotnet']) == 'stryker_net'


# purlin: mutation PROOF-27
def test_auto_with_no_framework_picks_no_engine():
    assert mutation.select_engine(AUTO, []) == 'none'


# purlin: mutation PROOF-2
def test_an_engine_named_in_the_settings_wins_over_the_framework():
    assert mutation.select_engine({'mutation_engine': 'mutmut'},
                                  ['jest']) == 'mutmut'


# purlin: mutation PROOF-28
def test_none_named_in_the_settings_turns_the_breaks_off():
    assert mutation.select_engine({'mutation_engine': 'none'},
                                  ['pytest']) == 'none'


# purlin: mutation PROOF-29
def test_an_engine_name_nobody_ships_reads_as_none():
    assert mutation.select_engine({'mutation_engine': 'cosmic-ray'},
                                  ['pytest']) == 'none'


@pytest.mark.parametrize('config', [{'gate': 'strong'}, {}, None])
# purlin: mutation PROOF-30
def test_settings_that_name_no_engine_read_as_none(config):
    assert mutation.select_engine(config, ['pytest']) == 'none'
    assert mutation.select_engine(config, ['jest']) == 'none'
    # The same project turned on picks its engine, so the key decided.
    assert mutation.select_engine(AUTO, ['pytest']) == 'mutmut'


# ---------------------------------------------------------------------------
# Test strength arithmetic
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('killed,survived,score', [
    (1, 1, 50),
    (2, 1, 67),
    (1, 2, 33),
    (5, 2, 71),
    (7, 4, 64),
    (1, 0, 100),
    (0, 1, 0),
])
# purlin: mutation PROOF-3
def test_strength_is_the_caught_share_as_an_integer_percent(killed, survived,
                                                            score):
    assert mutation.score_percent(killed, survived) == score


@pytest.mark.parametrize('killed,survived,score', [(1, 7, 13), (3, 5, 38)])
# purlin: mutation PROOF-31
def test_a_split_exactly_on_a_half_rounds_up(killed, survived, score):
    assert mutation.score_percent(killed, survived) == score


# purlin: mutation PROOF-32
def test_no_break_counted_reads_none_not_zero():
    assert mutation.score_percent(0, 0) is None


# purlin: mutation PROOF-4
def test_a_features_rules_are_answered_in_number_order(project):
    answer = mutation.run_breaks(
        str(project), 'none', {'f': ['f.sh']},
        {('f', 'RULE-10'): [], ('f', 'RULE-2'): [], ('f', 'RULE-1'): []})
    assert list(answer['features']['f']['rules']) == [
        'RULE-1', 'RULE-2', 'RULE-10']


# ---------------------------------------------------------------------------
# Stryker: how it is started
# ---------------------------------------------------------------------------

# purlin: mutation PROOF-5
def test_stryker_is_given_a_config_scoped_to_the_features_files(project):
    program = install_stryker(project)
    stryker.run(str(project), {'calc': ['src/calc.js', 'src/util.js']},
                feature_tests('calc', CALC_TESTS))
    config = calls(program)[0]['config']
    report_path = config['jsonReporter']['fileName']
    assert os.path.isabs(report_path)
    assert config == {
        'mutate': ['src/calc.js', 'src/util.js'],
        'coverageAnalysis': 'perTest',
        'disableBail': True,
        'reporters': ['json'],
        'testRunner': 'jest',
        'jsonReporter': {'fileName': report_path},
    }


# purlin: mutation PROOF-33
def test_a_stryker_run_reads_the_report_its_config_names(project):
    program = install_stryker(project)
    answer = stryker.run(str(project), {'calc': ['src/calc.js']},
                         feature_tests('calc', CALC_TESTS))
    started = calls(program)
    assert len(started) == 1
    assert started[0]['argv'][0] == 'run'
    assert len(started[0]['argv']) == 2
    assert started[0]['config']['mutate'] == ['src/calc.js']
    assert answer['engine'] == 'stryker'
    assert answer['available'] is True
    assert answer['features']['calc']['scope_score']['score'] == 64
    assert answer['features']['calc']['rules']['RULE-2']['score'] == 71
    assert 'calc' in answer['log']


# purlin: mutation PROOF-34
def test_a_run_over_two_features_starts_stryker_once_for_each(project):
    program = install_stryker(project)
    stryker.run(str(project), {'calc': ['src/calc.js'],
                               'util': ['src/util.js', 'src/fmt.js']},
                {('calc', 'RULE-1'): CALC_TESTS['RULE-1'],
                 ('util', 'RULE-1'): CALC_TESTS['RULE-1']})
    assert [call['config']['mutate'] for call in calls(program)] == [
        ['src/calc.js'], ['src/util.js', 'src/fmt.js']]


def runner_for(project, manifest):
    if manifest is not None:
        (project / 'package.json').write_text(json.dumps(manifest),
                                              encoding='utf-8')
    program = install_stryker(project)
    stryker.run(str(project), {'calc': ['src/calc.js']},
                feature_tests('calc', CALC_TESTS))
    return calls(program)[0]['config']['testRunner']


# purlin: mutation PROOF-6
def test_vitest_under_dev_dependencies_runs_stryker_with_vitest(project):
    assert runner_for(project, {'devDependencies': {'vitest': '^2.0.0'}}) \
        == 'vitest'


# purlin: mutation PROOF-35
def test_vitest_under_dependencies_runs_stryker_with_vitest(project):
    assert runner_for(project, {'dependencies': {'vitest': '^2.0.0'}}) \
        == 'vitest'


# purlin: mutation PROOF-36
def test_a_jest_project_runs_stryker_with_jest(project):
    assert runner_for(project, {'devDependencies': {'jest': '^30.0.0'}}) \
        == 'jest'


# purlin: mutation PROOF-37
def test_a_project_with_no_package_json_runs_stryker_with_jest(project):
    assert runner_for(project, None) == 'jest'


# purlin: mutation PROOF-7
def test_the_projects_own_stryker_is_started_over_one_on_the_path(tools,
                                                                    project):
    own = install_stryker(project)
    on_path = install_program(tools, 'stryker', _STRYKER,
                              report=read_fixture('stryker_report.json'))
    stryker.run(str(project), {'calc': ['src/calc.js']},
                feature_tests('calc', CALC_TESTS))
    assert len(calls(own)) == 1
    assert calls(on_path) == []


# purlin: mutation PROOF-38
def test_no_stryker_anywhere_leaves_no_engine_and_says_what_to_install(
        tools, project):
    answer = stryker.run(str(project), {'calc': ['src/calc.js']},
                         {('calc', 'RULE-1'): CALC_TESTS['RULE-1']})
    assert answer['engine'] == 'none'
    assert answer['available'] is False
    assert answer['reason'] == ('stryker is not installed: run '
                                '"npm install --save-dev @stryker-mutator/core"')
    rule = answer['features']['calc']['rules']['RULE-1']
    assert rule['attribution'] == 'unavailable'
    assert rule['score'] is None


# ---------------------------------------------------------------------------
# What counts caught and missed
# ---------------------------------------------------------------------------

# purlin: mutation PROOF-8
def test_a_compile_error_counts_neither_caught_nor_missed(project):
    report = read_fixture('stryker_report.json')
    statuses = sorted(m['status'] for m in report['files']['src/calc.js']['mutants'])
    assert statuses == ['CompileError'] + ['Killed'] * 6 + ['NoCoverage'] * 2 \
        + ['Survived'] * 2 + ['Timeout']
    entry = calc_run(project, report, CALC_TESTS)['features']['calc']
    assert entry['scope_score'] == {'score': 64, 'killed': 7, 'survived': 4}


# purlin: mutation PROOF-39
def test_mutmuts_statuses_count_caught_missed_or_neither(tools, project):
    statuses = ['killed', 'timeout', 'caught by type check', 'survived',
                'no tests', 'skipped', 'suspicious', 'not checked',
                'check was interrupted by user']
    listing = ''.join('    calc.ops.x_add__mutmut_%d: %s\n' % (index, status)
                      for index, status in enumerate(statuses, 1))
    answer = mutmut_run(tools, project, listing, {'calc': ['src/calc/ops.py']},
                        {('calc', 'RULE-1'): []})
    assert answer['features']['calc']['scope_score'] == {
        'score': 60, 'killed': 3, 'survived': 2}


# ---------------------------------------------------------------------------
# Stryker: a rule's own number
# ---------------------------------------------------------------------------

# purlin: mutation PROOF-9
def test_each_rule_carries_what_its_own_tests_caught(project):
    rules = calc_run(project, read_fixture('stryker_report.json'),
                     CALC_TESTS)['features']['calc']['rules']
    assert rules['RULE-1'] == {
        'engine': 'stryker', 'score': 100, 'killed': 3, 'survived': 0,
        'attribution': 'per_test'}
    assert rules['RULE-2'] == {
        'engine': 'stryker', 'score': 71, 'killed': 5, 'survived': 2,
        'attribution': 'per_test'}


# purlin: mutation PROOF-40
def test_a_break_another_rules_test_caught_counts_missed_for_this_one(project):
    report = one_break_report(
        [{'id': '1', 'status': 'Killed', 'coveredBy': ['0', '1'],
          'killedBy': ['0']}], ['locks', 'unlocks'])
    rules = calc_run(project, report, {'RULE-1': a_test('locks'),
                                       'RULE-2': a_test('unlocks')}
                     )['features']['calc']['rules']
    assert (rules['RULE-2']['killed'], rules['RULE-2']['survived'],
            rules['RULE-2']['score']) == (0, 1, 0)
    assert (rules['RULE-1']['killed'], rules['RULE-1']['survived']) == (1, 0)


# purlin: mutation PROOF-41
def test_a_break_that_timed_out_counts_caught_for_every_rule_that_reached_it(
        project):
    report = one_break_report(
        [{'id': '1', 'status': 'Timeout', 'coveredBy': ['0', '1'],
          'killedBy': []},
         # A break caught by name elsewhere, so the report names catchers.
         {'id': '2', 'status': 'Killed', 'coveredBy': ['2'],
          'killedBy': ['2']}], ['locks', 'unlocks', 'other'])
    rules = calc_run(project, report, {'RULE-1': a_test('locks'),
                                       'RULE-2': a_test('unlocks')}
                     )['features']['calc']['rules']
    for rule in ('RULE-1', 'RULE-2'):
        assert (rules[rule]['killed'], rules[rule]['survived']) == (1, 0)
        assert rules[rule]['attribution'] == 'per_test'


# purlin: mutation PROOF-42
def test_a_rule_whose_tests_the_report_never_lists_measures_nothing(project):
    rules = calc_run(project, read_fixture('stryker_report.json'),
                     {'RULE-9': a_test('unrelated', 'test/other.test.js')}
                     )['features']['calc']['rules']
    assert (rules['RULE-9']['score'], rules['RULE-9']['killed'],
            rules['RULE-9']['survived']) == (None, 0, 0)


# purlin: mutation PROOF-10
def test_a_name_that_begins_another_does_not_claim_its_break(project):
    report = one_break_report(
        [{'id': '1', 'status': 'Killed', 'coveredBy': ['0'],
          'killedBy': ['0']},
         {'id': '2', 'status': 'Survived', 'coveredBy': ['1'],
          'killedBy': []}], ['locks', 'locks after five'])
    rules = calc_run(project, report, {'RULE-1': a_test('locks'),
                                       'RULE-2': a_test('locks after five')}
                     )['features']['calc']['rules']
    assert (rules['RULE-1']['killed'], rules['RULE-1']['survived']) == (1, 0)
    assert (rules['RULE-2']['killed'], rules['RULE-2']['survived']) == (0, 1)


# purlin: mutation PROOF-43
def test_titles_written_with_a_separator_match_titles_joined_by_spaces(
        project):
    report = one_break_report(
        [{'id': '1', 'status': 'Killed', 'coveredBy': ['0'],
          'killedBy': ['0']}], ['login locks'])
    rules = calc_run(project, report, {'RULE-1': a_test('login > locks')}
                     )['features']['calc']['rules']
    assert (rules['RULE-1']['killed'], rules['RULE-1']['score']) == (1, 100)


# purlin: mutation PROOF-44
def test_a_test_of_the_same_name_in_another_file_is_not_this_rules_test(
        project):
    report = {'files': {'src/a.js': {'mutants': [
        {'id': '1', 'status': 'Killed', 'coveredBy': ['0'],
         'killedBy': ['0']}]}},
        'testFiles': {'test/other.test.js': {'tests': [
            {'id': '0', 'name': 'locks the account'}]}}}
    rules = calc_run(project, report,
                     {'RULE-1': a_test('locks the account',
                                       'test/login.test.js')}
                     )['features']['calc']['rules']
    assert rules['RULE-1']['killed'] == 0


# ---------------------------------------------------------------------------
# Stryker.NET
# ---------------------------------------------------------------------------

# purlin: mutation PROOF-11
def test_a_dotnet_report_naming_no_catcher_gives_every_rule_the_scope_number(
        tools, project):
    answer = login_run(tools, project, read_fixture('stryker_net_report.json'),
                       SESSION_TESTS)
    entry = answer['features']['login']
    assert entry['scope_score'] == {'score': 60, 'killed': 3, 'survived': 2}
    for rule in ('RULE-1', 'RULE-2'):
        assert entry['rules'][rule] == {
            'engine': 'stryker_net', 'score': 60, 'killed': 3, 'survived': 2,
            'attribution': 'per_scope'}
    assert 'attribution per_scope' in answer['log']


# purlin: mutation PROOF-45
def test_a_dotnet_report_naming_its_catchers_is_read_per_test(tools, project):
    answer = login_run(tools, project, read_fixture('stryker_report.json'),
                       CALC_TESTS)
    rule = answer['features']['login']['rules']['RULE-1']
    assert (rule['engine'], rule['attribution'], rule['score']) == (
        'stryker_net', 'per_test', 100)


# purlin: mutation PROOF-13
def test_stryker_net_is_started_with_the_scoped_command_line(tools, project):
    program = install_dotnet(tools)
    stryker_net.run(str(project),
                    {'login': ['src/Login/Session.cs', 'src/Api.cs']},
                    feature_tests('login', SESSION_TESTS))
    started = calls(program)
    assert started[0]['argv'] == ['stryker', '--version']
    argv = started[1]['argv']
    assert argv[:-1] == ['stryker',
                         '--mutate', 'src/Login/Session.cs',
                         '--mutate', 'src/Api.cs',
                         '--coverage-analysis', 'perTest', '--disable-bail',
                         '--reporter', 'json', '--output']
    assert os.path.basename(argv[-1]) == 'login'
    assert len(started) == 2


# purlin: mutation PROOF-46
def test_a_report_in_a_reports_folder_under_the_output_is_read(tools, project):
    answer = login_run(tools, project, read_fixture('stryker_net_report.json'),
                       SESSION_TESTS, folder=['reports'])
    assert answer['features']['login']['scope_score']['score'] == 60


# purlin: mutation PROOF-47
def test_a_report_several_folders_down_is_read(tools, project):
    answer = login_run(tools, project, read_fixture('stryker_net_report.json'),
                       SESSION_TESTS,
                       folder=['StrykerOutput', '2026-09-28', 'reports'])
    assert answer['features']['login']['scope_score']['score'] == 60


# purlin: mutation PROOF-48
def test_an_empty_output_folder_measures_nothing(tools, project):
    answer = login_run(tools, project, None, SESSION_TESTS)
    entry = answer['features']['login']
    assert entry['scope_score']['score'] is None
    assert entry['rules']['RULE-1']['score'] is None
    assert 'login: dotnet stryker exited 0 and wrote no report' in answer['log']


# purlin: mutation PROOF-14
def test_no_dotnet_on_the_path_leaves_no_engine(tools, project):
    answer = stryker_net.run(str(project), {'login': ['src/Login/Session.cs']},
                             feature_tests('login', SESSION_TESTS))
    assert (answer['engine'], answer['available']) == ('none', False)
    assert answer['reason'] == ('dotnet is not installed, so no engine breaks '
                                'C# code')


# purlin: mutation PROOF-49
def test_dotnet_without_stryker_net_says_how_to_install_it(tools, project):
    program = install_dotnet(tools, version_exit=1)
    answer = stryker_net.run(str(project), {'login': ['src/Login/Session.cs']},
                             feature_tests('login', SESSION_TESTS))
    assert (answer['engine'], answer['available']) == ('none', False)
    assert answer['reason'] == ('dotnet stryker is not installed: run '
                                '"dotnet tool install -g dotnet-stryker"')
    assert [call['argv'] for call in calls(program)] == [
        ['stryker', '--version']]


# purlin: mutation PROOF-50
def test_stryker_net_answering_its_version_is_installed(tools, project):
    program = install_dotnet(tools)
    answer = stryker_net.run(str(project), {'login': ['src/Login/Session.cs']},
                             feature_tests('login', SESSION_TESTS))
    started = calls(program)
    assert started[0]['argv'] == ['stryker', '--version']
    assert '--mutate' in started[1]['argv']
    assert (answer['engine'], answer['available'], answer['reason']) == (
        'stryker_net', True, '')


# ---------------------------------------------------------------------------
# Stryker: a run that measures nothing
# ---------------------------------------------------------------------------

# purlin: mutation PROOF-12
def test_a_report_that_is_not_json_measures_nothing(project):
    answer = calc_run(project, 'not json', CALC_TESTS)
    assert answer['features']['calc']['scope_score']['score'] is None
    assert answer['features']['calc']['rules']['RULE-1']['score'] is None
    assert 'calc: stryker exited 0 and wrote no report' in answer['log']


# purlin: mutation PROOF-51
def test_a_run_that_failed_and_wrote_no_report_says_so(project):
    install_stryker(project, report=None, exit=1, print='boom\n')
    answer = stryker.run(str(project), {'calc': ['src/calc.js']},
                         {('calc', 'RULE-1'): CALC_TESTS['RULE-1']})
    assert answer['features']['calc']['scope_score']['score'] is None
    assert answer['features']['calc']['rules']['RULE-1']['score'] is None
    assert 'calc: stryker exited 1 and wrote no report' in answer['log']
    assert 'boom' in answer['log']


# purlin: mutation PROOF-52
def test_a_feature_with_no_scope_files_is_not_broken(project):
    program = install_stryker(project)
    answer = stryker.run(str(project), {'calc': []},
                         {('calc', 'RULE-1'): CALC_TESTS['RULE-1']})
    assert calls(program) == []
    assert answer['features']['calc']['scope_score']['score'] is None
    assert answer['features']['calc']['rules']['RULE-1']['score'] is None
    assert 'calc: no scope files, nothing to break' in answer['log']


# ---------------------------------------------------------------------------
# mutmut
# ---------------------------------------------------------------------------

# purlin: mutation PROOF-15
def test_a_project_with_pyproject_gets_the_toml_block(project):
    (project / 'pyproject.toml').write_text('[project]\n', encoding='utf-8')
    path, style, _section = mutmut.config_target(str(project))
    assert path == 'pyproject.toml'
    assert mutmut.mutmut_config_block(['src'], ['tests'], style) == (
        '[tool.mutmut]\n'
        'source_paths = ["src"]\n'
        'pytest_add_cli_args_test_selection = ["tests"]\n')


# purlin: mutation PROOF-53
def test_a_project_without_pyproject_gets_the_setup_cfg_block(project):
    path, style, _section = mutmut.config_target(str(project))
    assert path == 'setup.cfg'
    assert mutmut.mutmut_config_block(['src', 'lib'], ['tests', '-q'],
                                      style) == (
        '[mutmut]\n'
        'source_paths =\n'
        '    src\n'
        '    lib\n'
        'pytest_add_cli_args_test_selection =\n'
        '    tests\n'
        '    -q\n')


# purlin: mutation PROOF-54
def test_a_pyproject_without_the_block_is_not_broken(tools, project):
    (project / 'pyproject.toml').write_text('[project]\nname = "demo"\n',
                                            encoding='utf-8')
    program = install_mutmut(tools)
    answer = mutmut.run(str(project), {'login': ['src/login/session.py']},
                        {('login', 'RULE-1'): []})
    assert calls(program) == []
    assert answer['engine'] == 'none'
    assert answer['reason'] == (
        'pyproject.toml carries no [tool.mutmut] block, so mutmut would break '
        'files no spec scopes: run "purlin:init" to write it')


# purlin: mutation PROOF-55
def test_a_setup_cfg_without_the_block_is_not_broken(tools, project):
    (project / 'setup.cfg').write_text('[metadata]\nname = demo\n',
                                       encoding='utf-8')
    program = install_mutmut(tools)
    answer = mutmut.run(str(project), {'login': ['src/login/session.py']},
                        {('login', 'RULE-1'): []})
    assert calls(program) == []
    assert answer['engine'] == 'none'
    assert answer['reason'] == (
        'setup.cfg carries no [mutmut] block, so mutmut would break files no '
        'spec scopes: run "purlin:init" to write it')


# purlin: mutation PROOF-16
def test_the_listing_read_is_what_mutmut_results_all_prints(tools, project):
    program = install_mutmut(tools,
                             listing=read_fixture('mutmut_results_smoke.txt'))
    with_block(project)
    answer = mutmut.run(str(project), {'calc': ['calc/ops.py']},
                        {('calc', 'RULE-1'): []})
    assert [call['argv'] for call in calls(program)] == [
        ['run'], ['results', '--all', 'true']]
    assert '5 breaks read' in answer['log']
    assert answer['features']['calc']['scope_score'] == {
        'score': 20, 'killed': 1, 'survived': 4}


# purlin: mutation PROOF-56
def test_the_lines_around_the_breaks_are_not_breaks(tools, project):
    listing = ('2 files mutated, 0 ignored, 0 unmodified\n'
               '244.79 mutations/second\n'
               '    login.session.x_lock_account__mutmut_1: killed\n'
               'Error: something else entirely\n'
               '    login.session.x_lock_account__mutmut_2: survived\n')
    answer = mutmut_run(tools, project, listing,
                        {'login': ['src/login/session.py']},
                        {('login', 'RULE-1'): []})
    assert '2 breaks read' in answer['log']
    assert answer['features']['login']['scope_score'] == {
        'score': 50, 'killed': 1, 'survived': 1}


# purlin: mutation PROOF-17
def test_a_mutmut_run_gives_every_rule_its_features_number(tools, project):
    with_block(project)
    program = install_mutmut(tools, listing=read_fixture('mutmut_results.txt'))
    answer = mutmut.run(str(project),
                        {'login': ['src/login/session.py'],
                         'reports': ['src/reports/render.py']},
                        {('login', 'RULE-1'): [],
                         ('login', 'RULE-2'): [],
                         ('reports', 'RULE-1'): []})
    assert [call['argv'] for call in calls(program)] == [
        ['run'], ['results', '--all', 'true']]
    assert (answer['engine'], answer['available']) == ('mutmut', True)
    login = answer['features']['login']
    assert login['scope_score'] == {'score': 67, 'killed': 4, 'survived': 2}
    for rule in ('RULE-1', 'RULE-2'):
        assert login['rules'][rule] == {
            'engine': 'mutmut', 'score': 67, 'killed': 4, 'survived': 2,
            'attribution': 'per_scope'}
    assert answer['features']['reports']['rules']['RULE-1'] == {
        'engine': 'mutmut', 'score': 0, 'killed': 0, 'survived': 1,
        'attribution': 'per_scope'}


# purlin: mutation PROOF-57
def test_a_break_no_scope_entry_covers_counts_for_no_feature(tools, project):
    answer = mutmut_run(tools, project,
                        '    unrelated.tool.x_main__mutmut_1: survived\n',
                        {'login': ['src/login/session.py']},
                        {('login', 'RULE-1'): []})
    assert answer['features']['login']['scope_score'] == {
        'score': None, 'killed': 0, 'survived': 0}


# purlin: mutation PROOF-58
def test_a_folder_scope_covers_the_modules_mutmut_names_under_it(tools,
                                                                   project):
    answer = mutmut_run(tools, project,
                        read_fixture('mutmut_results_smoke.txt'),
                        {'calc': ['calc']}, {('calc', 'RULE-1'): []})
    assert answer['features']['calc']['scope_score'] == {
        'score': 20, 'killed': 1, 'survived': 4}


# purlin: mutation PROOF-21
def test_a_break_in_a_package_init_counts_for_the_scope_naming_it(tools,
                                                                   project):
    answer = mutmut_run(
        tools, project,
        '    scripts.run.mutation.x_score_percent__mutmut_1: killed\n',
        {'core': ['scripts/run/mutation/__init__.py']},
        {('core', 'RULE-1'): []})
    assert answer['features']['core']['scope_score'] == {
        'score': 100, 'killed': 1, 'survived': 0}


# purlin: mutation PROOF-59
def test_a_glob_scope_covers_the_files_it_matches(tools, project):
    listing = ('    scripts.run.host.x_commit__mutmut_1: killed\n'
               '    scripts.mcp.purlin.x_read__mutmut_1: killed\n'
               '    dev.build_report.x_build__mutmut_1: survived\n')
    answer = mutmut_run(tools, project, listing,
                        {'scripts': ['scripts/**/*.py']},
                        {('scripts', 'RULE-1'): []})
    assert answer['features']['scripts']['scope_score'] == {
        'score': 100, 'killed': 2, 'survived': 0}


# purlin: mutation PROOF-18
def test_no_mutmut_on_the_path_leaves_no_engine(tools, project):
    with_block(project)
    answer = mutmut.run(str(project), {'login': ['src/login/session.py']},
                        {('login', 'RULE-1'): []})
    assert (answer['engine'], answer['available']) == ('none', False)
    assert answer['reason'] == 'mutmut is not installed: run "pip install mutmut"'
    assert answer['features']['login']['rules']['RULE-1'][
        'attribution'] == 'unavailable'


# ---------------------------------------------------------------------------
# No engine, and the shape everything answers in
# ---------------------------------------------------------------------------

# purlin: mutation PROOF-19
def test_the_empty_engine_measures_nothing_and_says_why(project):
    answer = mutation.run_breaks(
        str(project), 'none', {'deploy': ['deploy.sh']},
        {('deploy', 'RULE-1'): [], ('deploy', 'RULE-2'): []})
    assert (answer['engine'], answer['available']) == ('none', False)
    assert answer['reason'] == ('no engine breaks go, shell or sql code, so '
                                'test strength is not measured for these rules')
    assert answer['features']['deploy']['scope_score'] == {
        'score': None, 'killed': 0, 'survived': 0}
    for rule in ('RULE-1', 'RULE-2'):
        assert answer['features']['deploy']['rules'][rule] == {
            'engine': 'none', 'score': None, 'killed': 0, 'survived': 0,
            'attribution': 'unavailable'}


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
        assert rule_score['attribution'] in ('per_test', 'per_scope',
                                             'unavailable')


# purlin: mutation PROOF-20
def test_the_empty_engine_answers_the_one_shape(project):
    scope = {'deploy': ['deploy.sh'], 'infra': ['infra.sql']}
    tests = {('deploy', 'RULE-1'): [], ('infra', 'RULE-1'): []}
    answer = mutation.run_breaks(str(project), 'none', scope, tests)
    assert_answer_shape(answer, scope, tests)
    assert sorted(answer['features']) == ['deploy', 'infra']


# purlin: mutation PROOF-60
def test_the_mutmut_engine_answers_the_one_shape(tools, project):
    with_block(project)
    install_mutmut(tools, listing=read_fixture('mutmut_results.txt'))
    scope = {'login': ['src/login/session.py']}
    tests = {('login', 'RULE-1'): [], ('login', 'RULE-2'): []}
    answer = mutation.run_breaks(str(project), 'mutmut', scope, tests)
    assert_answer_shape(answer, scope, tests)
    assert answer['features']['login']['rules']['RULE-1']['score'] == 67


# purlin: mutation PROOF-61
def test_an_engine_nobody_ships_is_not_run(tools, project):
    # Every engine is installed, so a name mapped to any of them would start it.
    with_block(project)
    started = [install_mutmut(tools, listing=read_fixture('mutmut_results.txt')),
               install_dotnet(tools), install_stryker(project)]
    scope = {'login': ['src/login/session.py']}
    tests = {('login', 'RULE-1'): []}
    answer = mutation.run_breaks(str(project), 'cosmic-ray', scope, tests)
    assert [calls(program) for program in started] == [[], [], []]
    assert_answer_shape(answer, scope, tests)
    assert answer['engine'] == 'none'
    assert answer['reason'] == ('unknown engine "cosmic-ray": no breaks were '
                                'made')


# purlin: mutation PROOF-62
def test_a_rule_an_engine_answer_left_out_is_filled_in():
    answer = mutation.normalise(
        {'engine': 'stryker', 'available': True, 'reason': '',
         'features': {'calc': {'scope_score': mutation.scope_entry(3, 1),
                               'rules': {}}},
         'log': ''},
        {'calc': ['src/calc.js']},
        {('calc', 'RULE-1'): [], ('calc', 'RULE-2'): []})
    assert answer['features']['calc']['scope_score']['score'] == 75
    for rule in ('RULE-1', 'RULE-2'):
        assert answer['features']['calc']['rules'][rule]['score'] is None
        assert answer['features']['calc']['rules'][rule][
            'attribution'] == 'unavailable'


# purlin: mutation PROOF-63
def test_a_feature_the_engine_never_reached_is_still_listed(tools, project):
    with_block(project)
    install_mutmut(tools, listing=read_fixture('mutmut_results.txt'))
    answer = mutation.run_breaks(str(project), 'mutmut',
                                 {'login': ['src/login/session.py']},
                                 {('login', 'RULE-1'): [],
                                  ('audit', 'RULE-1'): []})
    audit = answer['features']['audit']
    assert audit['scope_score']['score'] is None
    assert audit['rules']['RULE-1'] == {
        'engine': 'mutmut', 'score': None, 'killed': 0, 'survived': 0,
        'attribution': 'unavailable'}


# ---------------------------------------------------------------------------
# An engine that runs past --arm-timeout
# ---------------------------------------------------------------------------

def assert_unmeasured(entry, engine, rules):
    assert entry['scope_score']['score'] is None
    for rule in rules:
        assert entry['rules'][rule] == {
            'engine': engine, 'score': None, 'killed': 0, 'survived': 0,
            'attribution': 'unavailable'}


def slow_mutmut_run(tools, project, monkeypatch):
    """A mutmut run over `login` and `reports` still going at a 1 s limit."""
    monkeypatch.setattr(mutation, 'ARM_TIMEOUT', 1)
    with_block(project)
    program = install_mutmut(tools, slow=True,
                             listing=read_fixture('mutmut_results.txt'))
    answer = mutmut.run(str(project),
                        {'login': ['src/login/session.py'],
                         'reports': ['src/reports/render.py']},
                        {('login', 'RULE-1'): [],
                         ('login', 'RULE-2'): [],
                         ('reports', 'RULE-1'): []})
    return answer, program


# purlin: mutation PROOF-22
def test_a_mutmut_run_that_timed_out_measures_nothing(tools, project,
                                                      monkeypatch):
    answer, program = slow_mutmut_run(tools, project, monkeypatch)
    assert (answer['engine'], answer['available']) == ('mutmut', True)
    assert_unmeasured(answer['features']['login'], 'mutmut',
                      ('RULE-1', 'RULE-2'))
    assert_unmeasured(answer['features']['reports'], 'mutmut', ('RULE-1',))
    assert [call['argv'] for call in calls(program)] == [['run']]


# purlin: mutation PROOF-64
def test_a_mutmut_run_that_timed_out_says_so(tools, project, monkeypatch):
    answer, _program = slow_mutmut_run(tools, project, monkeypatch)
    assert answer['reason'] == TIMEOUT_REASON % 1
    assert TIMEOUT_REASON % 1 in answer['log'].splitlines()


# purlin: mutation PROOF-65
def test_a_stryker_feature_that_timed_out_measures_nothing(project,
                                                           monkeypatch):
    monkeypatch.setattr(mutation, 'ARM_TIMEOUT', 3)
    install_stryker(project, slow=['slow'])
    answer = stryker.run(str(project),
                         {'calc': ['src/calc.js'], 'slow': ['src/calc.js']},
                         {('calc', 'RULE-1'): CALC_TESTS['RULE-1'],
                          ('calc', 'RULE-2'): CALC_TESTS['RULE-2'],
                          ('slow', 'RULE-1'): CALC_TESTS['RULE-1']})
    assert answer['features']['calc']['scope_score']['score'] == 64
    assert_unmeasured(answer['features']['slow'], 'stryker', ('RULE-1',))
    for text in (answer['reason'], answer['log']):
        assert 'timed out after 3 s' in text
        assert '--arm-timeout' in text


# purlin: mutation PROOF-66
def test_a_dotnet_feature_that_timed_out_measures_nothing(tools, project,
                                                          monkeypatch):
    monkeypatch.setattr(mutation, 'ARM_TIMEOUT', 3)
    install_dotnet(tools, slow=['slow'])
    answer = stryker_net.run(str(project),
                             {'login': ['src/Login/Session.cs'],
                              'slow': ['src/Login/Session.cs']},
                             {('login', 'RULE-1'): SESSION_TESTS['RULE-1'],
                              ('slow', 'RULE-1'): SESSION_TESTS['RULE-1']})
    assert answer['features']['login']['scope_score']['score'] == 60
    assert_unmeasured(answer['features']['slow'], 'stryker_net', ('RULE-1',))
    for text in (answer['reason'], answer['log']):
        assert 'timed out after 3 s' in text
        assert '--arm-timeout' in text


def audit_project(root):
    """A project at the gate `strong`, breaks on through mutmut, one passing
    rule in the feature `login`, scoped to `src/login/session.py`."""
    (root / '.purlin').mkdir()
    (root / 'specs' / 'auth').mkdir(parents=True)
    (root / 'src' / 'login').mkdir(parents=True)
    (root / 'tests').mkdir()
    (root / '.purlin' / 'config.json').write_text(json.dumps({
        'gate': 'strong', 'mutation_engine': 'mutmut',
        'tests': [{'name': 'pytest',
                   'run': '%s -m pytest -q -p no:cacheprovider {files} '
                          '--junitxml={report}' % sys.executable,
                   'report': '.purlin/runtime/reports/pytest.xml',
                   'format': 'junit', 'files': ['tests/test_*.py']}]}),
        encoding='utf-8')
    with_block(root)
    (root / 'src' / 'login' / '__init__.py').write_text('', encoding='utf-8')
    (root / 'src' / 'login' / 'session.py').write_text(
        'def locked(tries):\n    return tries >= 5\n', encoding='utf-8')
    (root / 'specs' / 'auth' / 'login.md').write_text(
        '# Feature: login\n\n> Scope: src/login/session.py\n\n## Rules\n\n'
        '- RULE-1: Five wrong passwords lock the account\n\n## Proof\n\n'
        '- PROOF-1 (RULE-1): Five wrong tries lock the account and four '
        'do not\n', encoding='utf-8')
    (root / 'tests' / 'test_login.py').write_text(
        'import os, sys\n'
        'sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", '
        '"src"))\n'
        'from login.session import locked\n\n\n'
        '# purlin: login PROOF-1\n'
        'def test_five_tries_lock():\n'
        '    assert locked(5) and not locked(4)\n', encoding='utf-8')


# purlin: mutation PROOF-67
def test_an_audit_given_arm_timeout_stops_a_running_engine(
        tools, project, monkeypatch, no_real_model):
    # The model the audit asks is the session's stand-in, first on PATH.
    monkeypatch.setenv('PATH', os.pathsep.join(
        [str(tools), no_real_model, '/usr/bin', '/bin']))
    program = install_mutmut(tools, slow=True)
    audit_project(project)
    began = time.time()
    result = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', str(project), '--all',
         '--audit', '--arm-timeout', '1'],
        capture_output=True, encoding='utf-8', cwd=str(project))
    output = result.stdout + result.stderr
    assert time.time() - began < 30, output
    assert [call['argv'] for call in calls(program)] == [['run']], output
    assert 'purlin: ' + TIMEOUT_REASON % 1 in output.splitlines(), output
    evidence = json.loads((project / '.purlin' / 'evidence' / 'local'
                           / 'login.json').read_text(encoding='utf-8'))
    mutation_entry = evidence['audit']['mutation']
    assert (mutation_entry['engine'], mutation_entry['score']) == ('mutmut',
                                                                   None)
