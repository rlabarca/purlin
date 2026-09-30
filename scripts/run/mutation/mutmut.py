"""mutmut: the engine that breaks pytest code.

mutmut breaks the whole project in one run rather than one feature at a time,
and it reports a break by the name of the function it changed. So this engine
runs once and counts each break for every feature whose scope reaches the
file the break is in: test strength is one share per feature.

mutmut does not run on Windows, so there it is no engine: the answer is
`engine: none`, and the AI audit alone decides.

The config mutmut reads is a block in the project's own config file, which
`purlin:init` writes with the developer's consent:

    [tool.mutmut]
    source_paths = ["src"]
    pytest_add_cli_args_test_selection = ["tests"]

`pyproject.toml` holds it when that file exists, otherwise `setup.cfg` holds a
`[mutmut]` section with the same two keys, one value per line. Without the
block mutmut guesses where the code is, so the engine answers unavailable and
names the block rather than breaking the wrong files.

`mutmut results --all true` prints one line per break:

        calc.ops.x_scale__mutmut_1: survived

The dotted name before the function's `x_` is the module mutmut imported,
`calc.ops` here. The module `a.b` is the file `a/b.py` or `a/b/__init__.py`,
looked for at the project root and then under `src/`, the root winning where
both are in git. A module that is no file git tracks counts for no feature.
"""

import os
import re
import shutil
import sys

from . import (TIMED_OUT, empty_features, execute, feature_entry,
               no_report_reason, none, not_installed, result, runs_here,
               timeout_reason)

NOT_INSTALLED = 'mutmut is not installed: run "pip install mutmut"'
NOT_HERE = ('mutmut does not run on Windows, so test strength is not measured '
            'here and the AI audit alone decides')

# What mutmut's statuses mean for test strength. `no tests` is mutmut's name
# for a break no test covers, which counts survived the way `NoCoverage` does
# for Stryker. `skipped`, `suspicious`, `not checked` and an interrupted check
# count for neither: no test ever judged them.
KILLED_STATUSES = ('killed', 'timeout', 'caught by type check')
SURVIVED_STATUSES = ('survived', 'no tests')

# `    calc.ops.x_scale__mutmut_1: survived`
_RESULT_LINE = re.compile(r'^\s*([\w.]+):\s*(.+?)\s*$')

RUN_COMMAND = ['mutmut', 'run']
RESULTS_COMMAND = ['mutmut', 'results', '--all', 'true']


def binary(project_root=None):
    """The path to mutmut, or None when it is not installed."""
    return shutil.which('mutmut')


def config_target(project_root):
    """`(relative path, style, section)` where the config block belongs."""
    if os.path.isfile(os.path.join(project_root or '.', 'pyproject.toml')):
        return 'pyproject.toml', 'toml', '[tool.mutmut]'
    return 'setup.cfg', 'cfg', '[mutmut]'


def mutmut_config_block(source_paths, test_args, style='toml'):
    """The config block `purlin:init` writes, as text ending in a newline.

    `style` is `toml` for `pyproject.toml` and `cfg` for `setup.cfg`, where a
    list is one value per line.
    """
    source_paths = [str(path) for path in source_paths or ()]
    test_args = [str(arg) for arg in test_args or ()]
    if style == 'cfg':
        lines = ['[mutmut]',
                 'source_paths ='] + ['    %s' % path for path in source_paths]
        lines.append('pytest_add_cli_args_test_selection =')
        lines += ['    %s' % arg for arg in test_args]
    else:
        lines = ['[tool.mutmut]',
                 'source_paths = %s' % _toml_list(source_paths),
                 'pytest_add_cli_args_test_selection = %s' % _toml_list(test_args)]
    return '\n'.join(lines) + '\n'


def _toml_list(values):
    return '[%s]' % ', '.join('"%s"' % value.replace('"', '\\"')
                              for value in values)


def has_config(project_root):
    """True when the project already carries the config block."""
    path, _, section = config_target(project_root)
    try:
        with open(os.path.join(project_root or '.', path), 'r',
                  encoding='utf-8') as handle:
            text = handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return False
    return section in text


def parse_results(text):
    """`[{"key", "status"}]` from the output of `mutmut results --all true`.

    A line whose status is not one mutmut writes is not a break, so the
    progress and error lines a run prints are left out rather than counted.
    """
    known = set(KILLED_STATUSES) | set(SURVIVED_STATUSES) | set(
        ('skipped', 'suspicious', 'not checked',
         'check was interrupted by user'))
    found = []
    for line in str(text or '').splitlines():
        match = _RESULT_LINE.match(line)
        if not match:
            continue
        status = match.group(2).strip().lower()
        if status not in known:
            continue
        found.append({'key': match.group(1), 'status': status})
    return found


def _module(key):
    """The module a break's name names: the segments before the `x_` one."""
    parts = [part for part in str(key or '').split('.') if part]
    for index, part in enumerate(parts):
        if part.startswith('x_') or part.startswith(u'xǁ'):
            return '.'.join(parts[:index])
    return '.'.join(parts[:-1])


def module_files(module):
    """The files the module `a.b` may be, in the order they are looked for."""
    path = module.replace('.', '/')
    return [path + '.py', path + '/__init__.py',
            'src/' + path + '.py', 'src/' + path + '/__init__.py']


def _fingerprint():
    here = os.path.dirname(os.path.abspath(__file__))
    mcp = os.path.join(os.path.dirname(os.path.dirname(here)), 'mcp')
    if mcp not in sys.path:
        sys.path.insert(0, mcp)
    from purlin import fingerprint
    return fingerprint


def file_by_module(project_root, modules):
    """`{module: tracked file}` for each module that is a file git tracks."""
    modules = sorted(set(module for module in modules if module))
    if not modules:
        return {}
    wanted = [path for module in modules for path in module_files(module)]
    tracked = set(_fingerprint().expand_scope(project_root, wanted)[0])
    found = {}
    for module in modules:
        for path in module_files(module):
            if path in tracked:
                found[module] = path
                break
    return found


def score_by_feature(project_root, entries, scope_by_feature):
    """`{feature: {"killed", "survived"}}` from one project-wide run.

    A break counts for every feature whose scope reaches its file.
    """
    files = file_by_module(project_root,
                           [_module(entry['key']) for entry in entries or ()])
    expand = _fingerprint().expand_scope
    totals = {}
    for feature in scope_by_feature or {}:
        scope = [path for path in scope_by_feature[feature] or () if path]
        reached = set(expand(project_root, scope)[0]) if scope else set()
        pair = {'killed': 0, 'survived': 0}
        for entry in entries or ():
            if files.get(_module(entry['key'])) not in reached:
                continue
            if entry['status'] in KILLED_STATUSES:
                pair['killed'] += 1
            elif entry['status'] in SURVIVED_STATUSES:
                pair['survived'] += 1
        totals[feature] = pair
    return totals


def run(project_root, scope_by_feature, os_name=None):
    """Break the project once and report each feature's share.

    `os_name` is the system as `runs_here` reads it, this one when None.
    """
    if not runs_here('mutmut', os_name):
        return none.run(project_root, scope_by_feature, reason=NOT_HERE)
    if binary(project_root) is None:
        return not_installed('mutmut', scope_by_feature, NOT_INSTALLED)
    path, _, section = config_target(project_root)
    if not has_config(project_root):
        return none.run(
            project_root, scope_by_feature,
            reason='%s carries no %s block, so mutmut would break files no '
                   'spec scopes: run purlin:init to write it'
                   % (path, section))
    lines = ['engine mutmut, config %s in %s' % (section, path)]
    code = execute(RUN_COMMAND, project_root)[0]
    lines.append('mutmut run exited %d' % code)
    if code == TIMED_OUT:
        # One run breaks the whole project, so what it left is partial for
        # every feature alike.
        reason = timeout_reason()
        lines.append(reason)
        return result('mutmut', True, reason,
                      empty_features(scope_by_feature, reason),
                      '\n'.join(lines))
    listing = execute(RESULTS_COMMAND, project_root)[1]
    entries = parse_results(listing)
    lines.append('%d breaks read' % len(entries))
    if not entries:
        return result('mutmut', True, '',
                      empty_features(scope_by_feature,
                                     no_report_reason('mutmut')),
                      '\n'.join(lines))
    totals = score_by_feature(project_root, entries, scope_by_feature)
    features = {}
    for feature in sorted(scope_by_feature or {}):
        pair = totals.get(feature, {'killed': 0, 'survived': 0})
        features[feature] = feature_entry(pair['killed'], pair['survived'])
        lines.append('%s: %d breaks, %d%% caught'
                     % (feature, pair['killed'] + pair['survived'],
                        features[feature]['scope_score']['score'] or 0))
    return result('mutmut', True, '', features, '\n'.join(lines))
