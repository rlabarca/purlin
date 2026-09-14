"""mutmut: the engine that breaks pytest code.

mutmut breaks the whole project in one run rather than one feature at a time,
and it reports a break by the name of the function it changed, never by the
test that caught it. So this engine runs once and groups what it reads by
source file, and every rule of a feature carries that feature's scope number
with `attribution: per_scope`. A rule of a pytest project is never credited
with its own tests' catches; the number beside it is the number for the files
its spec scopes.

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

The dotted name before the mutant is the module mutmut imported, which is
rarely the repository path: a file at `src/login/session.py` is imported as
`login.session`. So a break is attributed to the scope entry whose last path
segments match the most of the name's first segments.
"""

import os
import re
import shutil

from . import (execute, none, result, rule_entry, rules_by_feature,
               scope_entry)

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


def _segments(entry):
    """A scope entry as the module segments it covers.

    `src/login/session.py` is `['src', 'login', 'session']`; a directory keeps
    its segments as they are.
    """
    path = str(entry or '').replace('\\', '/').strip()
    while path.startswith('./'):
        path = path[2:]
    if path.endswith('.py'):
        path = path[:-3]
    return [part for part in path.strip('/').split('/') if part]


def _overlap(key_parts, scope_parts):
    """How many segments of a break's name the scope entry's tail matches.

    mutmut names a break by the module it imported, and a project's import
    root is rarely the repository root: a file at `src/login/session.py` is
    imported as `login.session`, so the scope entry's last segments are
    matched against the name's first segments and the longest match wins.
    """
    limit = min(len(key_parts), len(scope_parts))
    for length in range(limit, 0, -1):
        if scope_parts[-length:] == key_parts[:length]:
            return length
    return 0


def source_file(key, scope_entries):
    """The scope entry a break belongs to, or None when none covers it.

    The longest match wins, so `src/login/session.py` beats `src` for a break
    in the session module.
    """
    key_parts = [part for part in str(key or '').split('.') if part]
    best, best_length = None, 0
    for entry in scope_entries or ():
        length = _overlap(key_parts, _segments(entry))
        if length > best_length:
            best, best_length = entry, length
    return best


def group_by_file(entries, scope_entries):
    """`{scope entry: {"killed", "survived"}}` for the breaks it covers."""
    counts = {}
    for entry in entries or ():
        owner = source_file(entry['key'], scope_entries)
        if owner is None:
            continue
        pair = counts.setdefault(owner, {'killed': 0, 'survived': 0})
        if entry['status'] in KILLED_STATUSES:
            pair['killed'] += 1
        elif entry['status'] in SURVIVED_STATUSES:
            pair['survived'] += 1
    return counts


def score_by_feature(entries, scope_by_feature):
    """`{feature: {"killed", "survived"}}` from one project-wide run."""
    totals = {}
    for feature in scope_by_feature or {}:
        files = [path for path in scope_by_feature[feature] or () if path]
        counts = group_by_file(entries, files)
        killed = sum(pair['killed'] for pair in counts.values())
        survived = sum(pair['survived'] for pair in counts.values())
        totals[feature] = {'killed': killed, 'survived': survived}
    return totals


def run(project_root, scope_by_feature, tests_by_rule, tier=None):
    """Break the project once and report each feature's scope number."""
    if binary(project_root) is None:
        return none.run(project_root, scope_by_feature, tests_by_rule, tier,
                        reason='mutmut is not installed: run '
                               '"pip install mutmut"')
    path, _, section = config_target(project_root)
    if not has_config(project_root):
        return none.run(
            project_root, scope_by_feature, tests_by_rule, tier,
            reason='%s carries no %s block, so mutmut would break files no '
                   'spec scopes: run "purlin:init" to write it'
                   % (path, section))
    lines = ['engine mutmut, config %s in %s, tier %s'
             % (section, path, tier or 'all')]
    code = execute(RUN_COMMAND, project_root)[0]
    lines.append('mutmut run exited %d' % code)
    listing = execute(RESULTS_COMMAND, project_root)[1]
    entries = parse_results(listing)
    lines.append('%d breaks read' % len(entries))
    totals = score_by_feature(entries, scope_by_feature)
    rules = rules_by_feature(tests_by_rule)
    features = {}
    for feature in sorted(scope_by_feature or {}):
        pair = totals.get(feature, {'killed': 0, 'survived': 0})
        entry = scope_entry(pair['killed'], pair['survived'])
        features[feature] = {
            'scope_score': entry,
            'rules': dict((rule, rule_entry('mutmut', 'per_scope',
                                            pair['killed'], pair['survived']))
                          for rule in rules.get(feature, ())),
        }
        lines.append('%s: %d breaks, %d%% caught'
                     % (feature, pair['killed'] + pair['survived'],
                        entry['score'] or 0))
    return result('mutmut', True, '', features, '\n'.join(lines))
