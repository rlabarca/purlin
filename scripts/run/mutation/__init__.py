"""The engines that break the code, so a run can report test strength.

Test strength is the share of the deliberate breaks made to the code that the
tests caught, as an integer percent:

    test_strength = killed / (killed + survived)

A break that made a test hang counts killed: the test noticed. A break no test
covers counts survived for the scope score: nothing observed it.

Four engines ship, one per language family, and every one of them answers in
the same shape:

    {"engine": str, "available": bool, "reason": str,
     "features": {feature: {"scope_score": {"score", "killed", "survived"},
                            "rules": {"RULE-N": {"engine", "score", "killed",
                                                 "survived", "attribution"}}}},
     "log": str}

`attribution` says how much the number is worth:

`per_test`     the engine reported which test caught which break, so the
               number beside a rule is that rule's own tests
`per_scope`    the engine reported only totals for the files, so every rule in
               the feature carries the same number
`unavailable`  no engine ran, so nothing was measured

`score` is an integer percent, or None when no break ran at all. A caller
displaying None writes `n/a`.

`select_engine` picks the engine and `run_breaks` runs it. Selection never
touches the filesystem or a binary: it answers from the config and the
detected frameworks alone, so a caller can print the plan before anything
runs. The install check happens in `run_breaks`, which answers
`engine: none` with the reason in words when the binary is absent.
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

ATTRIBUTIONS = ('per_test', 'per_scope', 'unavailable')

# Which engine breaks the code a framework's tests cover. jest and vitest are
# both Stryker; xunit is Stryker.NET; pytest is mutmut. shell and sql have no
# engine, so those rules carry `attribution: unavailable`.
ENGINE_BY_FRAMEWORK = {
    'jest': 'stryker',
    'vitest': 'stryker',
    'xunit': 'stryker_net',
    'pytest': 'mutmut',
    'shell': 'none',
    'sql': 'none',
}


def select_engine(config, frameworks):
    """The engine name for a project, one of `ENGINES`.

    `config` is the project's `.purlin/config.json` dict, where
    `mutation_engine` is `auto` or an engine name. A name outside `ENGINES` is
    read as `none` rather than guessed at: a typo must not silently run an
    engine nobody asked for.

    Under `auto` the frameworks decide, in the order they were detected, so a
    project carrying pytest for the server and jest for the client runs the
    engine of whichever was detected first.
    """
    raw = (config or {}).get('mutation_engine', 'auto')
    name = str(raw or 'auto').strip().lower()
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
        process = subprocess.Popen(command, cwd=cwd or '.',
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
        process.kill()
        output = process.communicate()[0] or ''
        return TIMED_OUT, output + ('\nthe engine timed out after %d s'
                                    % cap)
    return process.returncode, output or ''


def scope_entry(killed=0, survived=0):
    """One feature's `scope_score`: the whole of its scope files."""
    return {'score': score_percent(killed, survived),
            'killed': int(killed), 'survived': int(survived)}


def rule_entry(engine, attribution, killed=0, survived=0):
    """One rule's entry under a feature."""
    return {'engine': engine, 'score': score_percent(killed, survived),
            'killed': int(killed), 'survived': int(survived),
            'attribution': attribution}


def _rule_order(rule):
    tail = str(rule).rsplit('-', 1)[-1]
    return (0, int(tail)) if tail.isdigit() else (1, 0)


def rules_by_feature(tests_by_rule):
    """`{feature: [RULE-N, ...]}` from the `{(feature, rule): tests}` mapping."""
    found = {}
    for key in tests_by_rule or {}:
        try:
            feature, rule = key
        except (TypeError, ValueError):
            continue
        rules = found.setdefault(feature, [])
        if rule not in rules:
            rules.append(rule)
    for rules in found.values():
        rules.sort(key=_rule_order)
    return found


def feature_tests(feature, rules, tests_by_rule):
    """`{RULE-N: [test entries]}` for one feature."""
    return dict((rule, list(tests_by_rule.get((feature, rule), ())))
                for rule in rules)


def empty_features(scope_by_feature, tests_by_rule, engine, attribution):
    """Every feature and rule the caller named, with nothing measured yet."""
    rules = rules_by_feature(tests_by_rule)
    names = set(scope_by_feature or ()) | set(rules)
    features = {}
    for feature in sorted(names):
        features[feature] = {
            'scope_score': scope_entry(),
            'rules': dict((rule, rule_entry(engine, attribution))
                          for rule in rules.get(feature, ())),
        }
    return features


def result(engine, available, reason, features, log=''):
    """The answer shape every engine returns."""
    return {'engine': engine, 'available': bool(available),
            'reason': reason or '', 'features': features or {},
            'log': log or ''}


def run_breaks(project_root, engine, scope_by_feature, tests_by_rule, tier=None):
    """Break the scope files of every feature and report what the tests caught.

    `scope_by_feature` is `{feature: [scope file paths]}` and `tests_by_rule`
    is `{(feature, "RULE-N"): [{"file", "name", "plugin"}]}`. `tier` is the
    tier the run covered; it is recorded in the log and changes nothing else,
    because every engine selects its tests from its own config rather than
    from a tier.

    An engine name outside `ENGINES`, or a binary that is not installed,
    answers `engine: none` with the reason in words rather than raising.

    Every invocation the engine makes is capped at `ARM_TIMEOUT` seconds,
    which the caller sets on this module before calling.
    """
    scope_by_feature = dict(scope_by_feature or {})
    tests_by_rule = dict(tests_by_rule or {})
    name = str(engine or 'none').strip().lower()
    module = importlib.import_module('.none', __name__)
    if name not in ENGINES:
        answer = module.run(project_root, scope_by_feature, tests_by_rule, tier,
                            reason='unknown engine "%s": no breaks were made'
                                   % engine)
    elif name == 'none':
        answer = module.run(project_root, scope_by_feature, tests_by_rule, tier)
    else:
        engine_module = importlib.import_module('.' + name, __name__)
        answer = engine_module.run(project_root, scope_by_feature,
                                   tests_by_rule, tier)
    return normalise(answer, scope_by_feature, tests_by_rule)


def normalise(answer, scope_by_feature, tests_by_rule):
    """Fill in what an engine left out, so every caller reads one shape."""
    answer = dict(answer or {})
    engine = answer.get('engine') or 'none'
    available = bool(answer.get('available'))
    # A rule the engine never reported measured nothing, whether or not the
    # engine ran, so the placeholder says `unavailable` rather than claiming
    # an attribution no number stands behind.
    filled = empty_features(scope_by_feature, tests_by_rule, engine,
                            'unavailable')
    for feature, entry in (answer.get('features') or {}).items():
        target = filled.setdefault(feature,
                                   {'scope_score': scope_entry(), 'rules': {}})
        if isinstance(entry, dict):
            if entry.get('scope_score'):
                target['scope_score'] = entry['scope_score']
            for rule, rule_score in (entry.get('rules') or {}).items():
                target['rules'][rule] = rule_score
    return result(engine, available, answer.get('reason'), filled,
                  answer.get('log'))
