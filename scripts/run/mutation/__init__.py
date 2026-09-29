"""The engines that break the code, so a run can report test strength.

Test strength is the share of the deliberate breaks made to a feature's code
that the tests caught, as an integer percent, one share per feature:

    test_strength = killed / (killed + survived)

A break that made a test hang counts killed: the test noticed. A break no test
covers counts survived: nothing observed it.

Four engines ship, one per language family, and every one of them answers in
the same shape:

    {"engine": str, "available": bool, "reason": str,
     "features": {feature: {"scope_score": {"score", "killed", "survived"},
                            "missing": str}},
     "log": str}

`score` is an integer percent, or None when no break ran at all. `missing` is
the sentence saying why the selected engine measured nothing for that
feature, and empty otherwise: the engine is not installed, it ran past
`ARM_TIMEOUT`, or it ran and wrote no report. An engine that cannot run on
this system answers `engine: none` with every `missing` empty: it counts as
no engine.

`select_engine` picks the engine and `run_breaks` runs it. Selection never
touches the filesystem or a binary: it answers from the config and the
detected frameworks alone, so a caller can print the plan before anything
runs. The install check happens in `run_breaks`, which answers with the
reason in words when the binary is absent.
"""

import importlib
import os
import subprocess

ENGINES = ('stryker', 'stryker_net', 'mutmut', 'none')

# How long one engine invocation may take before it is killed. The run
# script sets it from `--arm-timeout`; an engine that is still going after
# it is stopped, its output kept, and `TIMED_OUT` returned so the caller
# reports missing evidence rather than waiting for a job limit.
ARM_TIMEOUT = 3600
TIMED_OUT = 124

# Which engine breaks the code a framework's tests cover. jest and vitest are
# both Stryker; dotnet is Stryker.NET; pytest is mutmut. go, shell and sql
# have no engine.
ENGINE_BY_FRAMEWORK = {
    'jest': 'stryker',
    'vitest': 'stryker',
    'dotnet': 'stryker_net',
    'pytest': 'mutmut',
    'go': 'none',
    'shell': 'none',
    'sql': 'none',
}


def select_engine(config, frameworks):
    """The engine name for a project, one of `ENGINES`.

    `config` is the project's `.purlin/config.json` dict, where
    `mutation_engine` is `none`, `auto` or an engine name, and a missing key
    reads as `none`: mutation testing is off until a project turns it on. A
    name outside `ENGINES` is read as `none` rather than guessed at: a typo
    must not silently run an engine nobody asked for.

    Under `auto` the frameworks decide, in the order they were detected, so a
    project carrying pytest for the server and jest for the client runs the
    engine of whichever was detected first.
    """
    raw = (config or {}).get('mutation_engine') or 'none'
    name = str(raw).strip().lower()
    if name and name != 'auto':
        return name if name in ENGINES else 'none'
    for framework in frameworks or ():
        engine = ENGINE_BY_FRAMEWORK.get(str(framework).strip().lower())
        if engine and engine != 'none':
            return engine
    return 'none'


def score_percent(killed, survived):
    """`killed / (killed + survived)` as an integer percent, None when neither.

    Rounded half up by integer arithmetic, so one of two is 50 and two of
    three is 67 on every Python this ships on.
    """
    killed = max(int(killed or 0), 0)
    survived = max(int(survived or 0), 0)
    total = killed + survived
    if total == 0:
        return None
    return (killed * 200 + total) // (total * 2)


def execute(command, cwd, report_path=None, timeout=None):
    """Run `command` in `cwd` and return `(exit code, output)`.

    Output is the two streams together, because an engine writes its progress
    to one and its complaints to the other and the log wants both in order.
    `report_path` is where the engine's reporter writes; the real run never
    reads it, and it is an argument so a test can stand in for the binary.

    The child never reads this process's stdin and never asks git for a
    password: an engine that stops for an answer nobody is there to give
    holds the whole run until the job limit. `timeout` defaults to
    `ARM_TIMEOUT`; past it the child is killed, what it printed is kept, and
    the code is `TIMED_OUT`.
    """
    cap = ARM_TIMEOUT if timeout is None else timeout
    environment = dict(os.environ)
    environment['GIT_TERMINAL_PROMPT'] = '0'
    try:
        process = subprocess.Popen([*command], cwd=cwd or '.',
                                   stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT,
                                   env=environment,
                                   universal_newlines=True)
    except (IOError, OSError) as error:
        return 127, str(error)
    try:
        output = process.communicate(timeout=cap)[0]
    except subprocess.TimeoutExpired:
        _stop(process)
        output = process.communicate()[0] or ''
        return TIMED_OUT, output + ('\nthe engine timed out after %d s'
                                    % cap)
    return process.returncode, output or ''


def _stop(process):
    """Stop `process` and, on Windows, every program it started.

    On Windows an engine is often a `.cmd` file, which runs under `cmd.exe`:
    killing `cmd.exe` alone leaves the engine running and holding the output
    pipe, so the wait for its output would last as long as the engine does.
    `taskkill /T` stops the whole tree first.
    """
    if os.name == 'nt':
        taskkill = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'),
                                'System32', 'taskkill.exe')
        try:
            subprocess.run([taskkill, '/F', '/T', '/PID', str(process.pid)],
                           stdin=subprocess.DEVNULL,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
        except (IOError, OSError, subprocess.TimeoutExpired):
            pass
    process.kill()


def scope_entry(killed=0, survived=0):
    """One feature's `scope_score`: the whole of its scope files."""
    return {'score': score_percent(killed, survived),
            'killed': int(killed), 'survived': int(survived)}


def feature_entry(killed=0, survived=0, missing=''):
    """One feature's entry: its share, and why nothing was measured."""
    return {'scope_score': scope_entry(killed, survived),
            'missing': missing or ''}


def empty_features(scope_by_feature, missing=''):
    """Every feature the caller named, with nothing measured."""
    return dict((feature, feature_entry(missing=missing))
                for feature in sorted(scope_by_feature or ()))


def result(engine, available, reason, features, log=''):
    """The answer shape every engine returns."""
    return {'engine': engine, 'available': bool(available),
            'reason': reason or '', 'features': features or {},
            'log': log or ''}


def not_installed(engine, scope_by_feature, reason):
    """The answer of a selected engine whose program is not installed.

    It names the engine, is not available, and every feature carries the
    reason as its `missing`, so each rule reads why nothing was measured.
    """
    return result(engine, False, reason,
                  empty_features(scope_by_feature, reason), '')


def timeout_reason():
    """The sentence for an engine invocation that ran past `ARM_TIMEOUT`."""
    return ('the engine timed out after %d s, so the breaks it made measure '
            'nothing: run purlin:audit --arm-timeout <seconds> to give it '
            'longer' % ARM_TIMEOUT)


def no_report_reason(program):
    """The sentence for an engine that ran and wrote no report.

    `program` is how a person starts it: `mutmut`, `stryker` or
    `dotnet stryker`.
    """
    return '%s ran and wrote no report: run purlin:audit again' % program


def runs_here(engine, os_name=None):
    """Whether `engine` can run on this operating system.

    False only for `mutmut` on Windows: `os_name == 'windows'`, or, with no
    `os_name` given, `os.name == 'nt'`. True for every other engine and
    system.
    """
    if engine != 'mutmut':
        return True
    if os_name is None:
        return os.name != 'nt'
    return os_name != 'windows'


def run_breaks(project_root, engine, scope_by_feature):
    """Break the scope files of every feature and report what the tests caught.

    `scope_by_feature` is `{feature: [scope entries]}`. The answer carries
    one share per feature, `scope_score`, and its `missing`.

    An engine name outside `ENGINES` answers `engine: none` with the reason
    in words rather than raising.

    Every invocation the engine makes is capped at `ARM_TIMEOUT` seconds,
    which the caller sets on this module before calling.
    """
    scope_by_feature = dict(scope_by_feature or {})
    name = str(engine or 'none').strip().lower()
    module = importlib.import_module('.none', __name__)
    if name not in ENGINES:
        answer = module.run(project_root, scope_by_feature,
                            reason='unknown engine "%s": no breaks were made'
                                   % engine)
    elif name == 'none':
        answer = module.run(project_root, scope_by_feature)
    else:
        engine_module = importlib.import_module('.' + name, __name__)
        answer = engine_module.run(project_root, scope_by_feature)
    return normalise(answer, scope_by_feature)


def normalise(answer, scope_by_feature):
    """Fill in what an engine left out, so every caller reads one shape."""
    answer = dict(answer or {})
    engine = answer.get('engine') or 'none'
    available = bool(answer.get('available'))
    filled = empty_features(scope_by_feature)
    for feature, entry in (answer.get('features') or {}).items():
        target = filled.setdefault(feature, feature_entry())
        if isinstance(entry, dict):
            if entry.get('scope_score'):
                target['scope_score'] = entry['scope_score']
            target['missing'] = entry.get('missing') or ''
    return result(engine, available, answer.get('reason'), filled,
                  answer.get('log'))
