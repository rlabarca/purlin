"""Stryker.NET: the engine that breaks xunit code.

One run per feature, over that feature's scope files alone:

    dotnet stryker --mutate <file> --coverage-analysis perTest
                   --disable-bail --reporter json --output <temp>

The report is the same schema Stryker writes for jest and vitest, so
`stryker.parse_report` reads it unchanged. The difference
is attribution: Stryker.NET names the test that caught a break only when the
test runner reported it, so the answer is per test when `killedBy` is
populated and per scope when it is not, and the result says which.
"""

import os
import shutil
import tempfile

from . import (execute, feature_tests, none, result, rule_entry,
               rules_by_feature, scope_entry, stryker)

REPORT_NAME = 'mutation-report.json'


def binary(project_root=None):
    """The command that runs Stryker.NET, or None when dotnet is absent."""
    found = shutil.which('dotnet')
    if not found:
        return None
    return [found, 'stryker']


def available(project_root):
    """`(installed, reason)`: whether `dotnet stryker` answers."""
    command = binary(project_root)
    if command is None:
        return False, 'dotnet is not installed, so no engine breaks C# code'
    code, output = execute(command + ['--version'], project_root)
    if code == 0:
        return True, ''
    return False, ('dotnet stryker is not installed: run '
                   '"dotnet tool install -g dotnet-stryker"')


def build_command(command, scope_files, output_dir):
    """The whole command line for one feature's run."""
    args = list(command)
    for path in scope_files:
        args += ['--mutate', str(path)]
    args += ['--coverage-analysis', 'perTest', '--disable-bail',
             '--reporter', 'json', '--output', output_dir]
    return args


def find_report(output_dir):
    """The report under `output_dir`, or None when the run wrote none.

    Stryker.NET writes `mutation-report.json` into a `reports` directory it
    names after the run, so the tree is walked rather than one path guessed.
    """
    best = None
    for dirpath, dirnames, filenames in os.walk(output_dir or '.'):
        dirnames[:] = sorted(dirnames)
        for name in sorted(filenames):
            if name != REPORT_NAME and not name.endswith('.json'):
                continue
            path = os.path.join(dirpath, name)
            if name == REPORT_NAME:
                return path
            if best is None:
                best = path
    return best


def run(project_root, scope_by_feature, tests_by_rule, tier=None):
    """Break every feature's scope files and report what the tests caught."""
    installed, reason = available(project_root)
    if not installed:
        return none.run(project_root, scope_by_feature, tests_by_rule, tier,
                        reason=reason)
    command = binary(project_root)
    rules = rules_by_feature(tests_by_rule)
    lines = ['engine stryker_net, tier %s' % (tier or 'all')]
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
            output_dir = os.path.join(work, feature)
            os.makedirs(output_dir)
            code, output = execute(
                build_command(command, files, output_dir),
                project_root, output_dir)
            path = find_report(output_dir)
            report = stryker.read_report(path) if path else None
            if report is None:
                features[feature] = _nothing(tests_for_feature)
                lines.append('%s: dotnet stryker exited %d and wrote no report'
                             % (feature, code))
                continue
            entry = stryker.parse_report(report, tests_for_feature,
                                         engine='stryker_net')
            features[feature] = entry
            attribution = 'per_scope'
            for rule_score in entry['rules'].values():
                attribution = rule_score['attribution']
                break
            lines.append('%s: %d files broken, %d%% caught, attribution %s'
                         % (feature, len(files),
                            entry['scope_score']['score'] or 0, attribution))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return result('stryker_net', True, '', features, '\n'.join(lines))


def _nothing(tests_for_feature):
    return {'scope_score': scope_entry(),
            'rules': dict((rule, rule_entry('stryker_net', 'per_scope'))
                          for rule in tests_for_feature or {})}
