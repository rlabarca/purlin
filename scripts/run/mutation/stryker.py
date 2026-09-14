"""Stryker: the engine that breaks jest and vitest code.

One run per feature, over that feature's scope files alone, with a generated
config in a temporary directory:

    {"mutate": ["src/login.js"], "coverageAnalysis": "perTest",
     "disableBail": true, "reporters": ["json"], "testRunner": "jest",
     "jsonReporter": {"fileName": "<temp>/login.json"}}

`coverageAnalysis: perTest` is what makes the report say which test caught
which break; `disableBail: true` keeps the run going after the first failure,
so a break that two tests catch is credited to both.

The report is the schema Stryker writes for every language:

    {"files": {"src/login.js": {"mutants": [{"id", "status", "coveredBy",
                                             "killedBy"}]}},
     "testFiles": {"test/login.test.js": {"tests": [{"id", "name"}]}}}

A test's `name` is the name the test framework saw, so it carries the proof
marker the plugin reads. Intersecting the report's `killedBy` and `coveredBy`
ids with the ids of a rule's own tests is what turns a file total into a
number beside a rule.
"""

import json
import os
import re
import shutil
import tempfile

from . import (execute, feature_tests, none, result, rule_entry,
               rules_by_feature, scope_entry)

# What the statuses mean for test strength. A timeout is a catch: the break
# made the test hang, and the test noticed. A break no test covers is a miss
# for the scope score. Everything else (`CompileError`, `RuntimeError`,
# `Ignored`) is a break that never reached a test, so it counts for neither.
KILLED_STATUSES = ('killed', 'timeout')
SURVIVED_STATUSES = ('survived', 'nocoverage')

# The proof marker a plugin writes into a test name, e.g.
# `[proof:login:PROOF-1:RULE-1]`. When both names carry one, the marker is the
# match, so a test name that is a prefix of another never claims its breaks.
_MARKER_RE = re.compile(r'\[proof:[^\]]+\]')


def binary(project_root):
    """The command that runs Stryker, or None when it is not installed.

    The project's own `node_modules/.bin/stryker` wins over one on PATH: a
    project pins the version it generates its config for.
    """
    local = os.path.join(project_root or '.', 'node_modules', '.bin', 'stryker')
    if os.path.isfile(local):
        return [local]
    found = shutil.which('stryker')
    if found:
        return [found]
    return None


def test_runner(project_root):
    """`vitest` when the project declares vitest, else `jest`."""
    path = os.path.join(project_root or '.', 'package.json')
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError, UnicodeDecodeError):
        return 'jest'
    if isinstance(data, dict):
        for section in ('dependencies', 'devDependencies'):
            deps = data.get(section)
            if isinstance(deps, dict) and 'vitest' in deps:
                return 'vitest'
    return 'jest'


def build_config(scope_files, runner, report_path):
    """The config one feature's run is given."""
    return {
        'mutate': [str(path) for path in scope_files],
        'coverageAnalysis': 'perTest',
        'disableBail': True,
        'reporters': ['json'],
        'testRunner': runner,
        'jsonReporter': {'fileName': report_path},
    }


def _clean_name(text):
    return ' '.join(str(text or '').split())


def _same_file(report_path, test_file):
    """True when the report's test file and the plugin's are the same file."""
    if not test_file:
        return True
    left = str(report_path or '').replace('\\', '/').lstrip('./')
    right = str(test_file).replace('\\', '/').lstrip('./')
    if not left or not right:
        return True
    return left.endswith(right) or right.endswith(left)


def _same_test(report_name, test_name):
    """True when the report's test and the plugin's test are the same test."""
    left, right = _clean_name(report_name), _clean_name(test_name)
    if not left or not right:
        return False
    left_marker = _MARKER_RE.search(left)
    right_marker = _MARKER_RE.search(right)
    if left_marker and right_marker:
        return left_marker.group(0) == right_marker.group(0)
    return left == right or right in left or left in right


def test_ids_by_rule(report, tests_for_feature):
    """`{RULE-N: set of report test ids}` for one feature's rules."""
    listed = []
    for path, entry in sorted((report.get('testFiles') or {}).items()):
        for test in (entry or {}).get('tests') or []:
            listed.append((path, str(test.get('id')), test.get('name')))
    found = {}
    for rule, tests in (tests_for_feature or {}).items():
        ids = set()
        for test in tests or ():
            name = test.get('name') if isinstance(test, dict) else None
            path = test.get('file') if isinstance(test, dict) else None
            for report_path, test_id, report_name in listed:
                if _same_file(report_path, path) and _same_test(report_name, name):
                    ids.add(test_id)
        found[rule] = ids
    return found


def _mutants(report):
    for _, entry in sorted((report.get('files') or {}).items()):
        for mutant in (entry or {}).get('mutants') or []:
            yield mutant


def parse_report(report, tests_for_feature, engine='stryker', attribution=None):
    """One feature's entry, from one report.

    `attribution` defaults to `per_test` when any break names the test that
    caught it, and to `per_scope` when none does, in which case every rule
    carries the scope number. Stryker.NET is the engine that needs the
    fallback; StrykerJS with `perTest` coverage always names the test.
    """
    report = report or {}
    ids_by_rule = test_ids_by_rule(report, tests_for_feature)
    counts = dict((rule, [0, 0]) for rule in (tests_for_feature or {}))
    killed = survived = 0
    named_killer = False
    for mutant in _mutants(report):
        status = str(mutant.get('status') or '').strip().lower()
        covered = set(str(x) for x in (mutant.get('coveredBy') or ()))
        killers = set(str(x) for x in (mutant.get('killedBy') or ()))
        if killers:
            named_killer = True
        if status in KILLED_STATUSES:
            killed += 1
        elif status in SURVIVED_STATUSES:
            survived += 1
        else:
            continue
        for rule, rule_ids in ids_by_rule.items():
            if killers & rule_ids or (status == 'timeout' and covered & rule_ids):
                counts[rule][0] += 1
            elif covered & rule_ids:
                counts[rule][1] += 1
    if attribution is None:
        attribution = 'per_test' if named_killer else 'per_scope'
    rules = {}
    for rule, pair in counts.items():
        if attribution == 'per_scope':
            rules[rule] = rule_entry(engine, attribution, killed, survived)
        else:
            rules[rule] = rule_entry(engine, attribution, pair[0], pair[1])
    return {'scope_score': scope_entry(killed, survived), 'rules': rules}


def read_report(path):
    """The report at `path`, or None when the run wrote none."""
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError, UnicodeDecodeError):
        return None


def run(project_root, scope_by_feature, tests_by_rule, tier=None):
    """Break every feature's scope files and report what the tests caught."""
    command = binary(project_root)
    if command is None:
        return none.run(project_root, scope_by_feature, tests_by_rule, tier,
                        reason='stryker is not installed: run '
                               '"npm install --save-dev @stryker-mutator/core"')
    runner = test_runner(project_root)
    rules = rules_by_feature(tests_by_rule)
    lines = ['engine stryker, test runner %s, tier %s'
             % (runner, tier or 'all')]
    features = {}
    work = tempfile.mkdtemp(prefix='purlin-breaks-')
    try:
        for feature in sorted(scope_by_feature or {}):
            tests_for_feature = feature_tests(feature, rules.get(feature, ()),
                                              tests_by_rule)
            files = [path for path in scope_by_feature[feature] or () if path]
            if not files:
                features[feature] = _nothing(tests_for_feature)
                lines.append('%s: no scope files, nothing to break' % feature)
                continue
            report_path = os.path.join(work, '%s.report.json' % feature)
            config_path = os.path.join(work, '%s.conf.json' % feature)
            with open(config_path, 'w', encoding='utf-8') as handle:
                json.dump(build_config(files, runner, report_path), handle)
            code, output = execute(command + ['run', config_path],
                                   project_root, report_path)
            report = read_report(report_path)
            if report is None:
                features[feature] = _nothing(tests_for_feature)
                lines.append('%s: stryker exited %d and wrote no report'
                             % (feature, code))
                lines.append(_tail(output))
                continue
            features[feature] = parse_report(report, tests_for_feature)
            lines.append('%s: %d files broken, %d%% caught'
                         % (feature, len(files),
                            features[feature]['scope_score']['score'] or 0))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return result('stryker', True, '', features, '\n'.join(lines))


def _nothing(tests_for_feature):
    return {'scope_score': scope_entry(),
            'rules': dict((rule, rule_entry('stryker', 'per_test'))
                          for rule in tests_for_feature or {})}


def _tail(output, limit=20):
    lines = [line for line in str(output or '').splitlines() if line.strip()]
    return '\n'.join(lines[-limit:])
