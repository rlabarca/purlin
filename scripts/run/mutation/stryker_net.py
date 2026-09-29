"""Stryker.NET: the engine that breaks the code a dotnet suite tests.

One run per feature, over that feature's scope files alone:

    dotnet stryker --mutate <file> --coverage-analysis perTest
                   --disable-bail --reporter json --output <temp>

The report is the same schema Stryker writes for jest and vitest, so
`stryker.parse_report` reads it unchanged into the feature's one share. It is
the file named `mutation-report.json` under the output folder and no other.
"""

import os
import shutil
import tempfile

from . import (TIMED_OUT, execute, feature_entry, no_report_reason,
               not_installed, result, stryker, timeout_reason)

REPORT_NAME = 'mutation-report.json'

NO_DOTNET = ('dotnet is not installed: install the .NET SDK, then run '
             '"dotnet tool install -g dotnet-stryker"')
NO_STRYKER = ('dotnet stryker is not installed: run '
              '"dotnet tool install -g dotnet-stryker"')


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
        return False, NO_DOTNET
    code, output = execute(command + ['--version'], project_root)
    if code == 0:
        return True, ''
    return False, NO_STRYKER


def build_command(command, scope_files, output_dir):
    """The whole command line for one feature's run."""
    args = list(command)
    for path in scope_files:
        args += ['--mutate', str(path)]
    args += ['--coverage-analysis', 'perTest', '--disable-bail',
             '--reporter', 'json', '--output', output_dir]
    return args


def find_report(output_dir):
    """The `mutation-report.json` under `output_dir`, or None.

    Stryker.NET writes it into a `reports` directory it names after the run,
    so the tree is walked rather than one path guessed. No other file is
    taken for it.
    """
    for dirpath, dirnames, filenames in os.walk(output_dir or '.'):
        dirnames[:] = sorted(dirnames)
        if REPORT_NAME in filenames:
            return os.path.join(dirpath, REPORT_NAME)
    return None


def run(project_root, scope_by_feature):
    """Break every feature's scope files and report what the tests caught."""
    installed, reason = available(project_root)
    if not installed:
        return not_installed('stryker_net', scope_by_feature, reason)
    command = binary(project_root)
    lines = ['engine stryker_net']
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
            output_dir = os.path.join(work, feature)
            os.makedirs(output_dir)
            code, output = execute(
                build_command(command, files, output_dir),
                project_root, output_dir)
            if code == TIMED_OUT:
                reason = timeout_reason()
                features[feature] = feature_entry(missing=reason)
                lines.append('%s: %s' % (feature, reason))
                continue
            path = find_report(output_dir)
            report = stryker.read_report(path) if path else None
            if report is None:
                features[feature] = feature_entry(
                    missing=no_report_reason('dotnet stryker'))
                lines.append('%s: dotnet stryker exited %d and wrote no report'
                             % (feature, code))
                continue
            features[feature] = stryker.parse_report(report)
            lines.append('%s: %d files broken, %d%% caught'
                         % (feature, len(files),
                            features[feature]['scope_score']['score'] or 0))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return result('stryker_net', True, reason, features, '\n'.join(lines))
