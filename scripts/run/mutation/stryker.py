"""Stryker: the engine that breaks jest and vitest code.

One run per feature, over that feature's scope files alone, with a generated
config in a temporary directory:

    {"mutate": ["src/login.js"], "coverageAnalysis": "perTest",
     "disableBail": true, "reporters": ["json"], "testRunner": "jest",
     "jsonReporter": {"fileName": "<temp>/login.json"}}

`coverageAnalysis: perTest` runs only the tests that reach a break against
it; `disableBail: true` keeps the run going after the first failure.

The report is the schema Stryker writes for every language:

    {"files": {"src/login.js": {"mutants": [{"id", "status"}]}}}

Every break in it counts toward the feature's one share: test strength is
one share per feature, whichever tests caught the break.
"""

import json
import os
import shutil
import tempfile

from . import (TIMED_OUT, execute, feature_entry, no_report_reason,
               not_installed, result, timeout_reason)

# What the statuses mean for test strength. A timeout is a catch: the break
# made the test hang, and the test noticed. A break no test covers is a miss
# for the scope score. Everything else (`CompileError`, `RuntimeError`,
# `Ignored`) is a break that never reached a test, so it counts for neither.
KILLED_STATUSES = ('killed', 'timeout')
SURVIVED_STATUSES = ('survived', 'nocoverage')

NOT_INSTALLED = ('stryker is not installed: run '
                 '"npm install --save-dev @stryker-mutator/core"')


def binary(project_root):
    """The command that runs Stryker, or None when it is not installed.

    The project's own `node_modules/.bin/stryker` wins over one on PATH: a
    project pins the version it generates its config for. On Windows npm
    writes that copy as `stryker.cmd`, so that name is the one looked for.
    """
    name = 'stryker.cmd' if os.name == 'nt' else 'stryker'
    local = os.path.join(project_root or '.', 'node_modules', '.bin', name)
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


def _mutants(report):
    for _, entry in sorted((report.get('files') or {}).items()):
        for mutant in (entry or {}).get('mutants') or []:
            yield mutant


def parse_report(report):
    """One feature's entry, from one report: the share of its breaks caught."""
    killed = survived = 0
    for mutant in _mutants(report or {}):
        status = str(mutant.get('status') or '').strip().lower()
        if status in KILLED_STATUSES:
            killed += 1
        elif status in SURVIVED_STATUSES:
            survived += 1
    return feature_entry(killed, survived)


def read_report(path):
    """The report at `path`, or None when the run wrote none."""
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except (IOError, OSError, ValueError, UnicodeDecodeError):
        return None


def run(project_root, scope_by_feature):
    """Break every feature's scope files and report what the tests caught."""
    command = binary(project_root)
    if command is None:
        return not_installed('stryker', scope_by_feature, NOT_INSTALLED)
    runner = test_runner(project_root)
    lines = ['engine stryker, test runner %s' % runner]
    features = {}
    reason = ''
    work = tempfile.mkdtemp(prefix='purlin-breaks-')
    try:
        for feature in sorted(scope_by_feature or {}):
            files = [path for path in scope_by_feature[feature] or () if path]
            if not files:
                features[feature] = feature_entry()
                lines.append('%s: no scope files, nothing to break' % feature)
                continue
            report_path = os.path.join(work, '%s.report.json' % feature)
            config_path = os.path.join(work, '%s.conf.json' % feature)
            with open(config_path, 'w', encoding='utf-8') as handle:
                json.dump(build_config(files, runner, report_path), handle)
            code, output = execute(command + ['run', config_path],
                                   project_root, report_path)
            if code == TIMED_OUT:
                # A partial run's number would read as a measurement it is
                # not, whatever report the engine left behind.
                reason = timeout_reason()
                features[feature] = feature_entry(missing=reason)
                lines.append('%s: %s' % (feature, reason))
                continue
            report = read_report(report_path)
            if report is None:
                features[feature] = feature_entry(
                    missing=no_report_reason('stryker'))
                lines.append('%s: stryker exited %d and wrote no report'
                             % (feature, code))
                lines.append(_tail(output))
                continue
            features[feature] = parse_report(report)
            lines.append('%s: %d files broken, %d%% caught'
                         % (feature, len(files),
                            features[feature]['scope_score']['score'] or 0))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return result('stryker', True, reason, features, '\n'.join(lines))


def _tail(output, limit=20):
    lines = [line for line in str(output or '').splitlines() if line.strip()]
    return '\n'.join(lines[-limit:])
