"""The one project setting, and what it derives.

A project sets `gate` in `.purlin/config.json` and nothing else has to be
decided. The gate says what CI must see before a change can merge:

`tested`    every rule has a passing tagged test
`recorded`  every rule has a record CI wrote at this commit, at or above the
            project's minimum test strength
`approved`  `recorded`, plus a current approval on every high and medium rule

Everything else has a default derived from the gate, and every default can be
overridden by naming the key:

    {"gate": "recorded", "ai_review_at": "high", "min_strength": 70,
     "mutation_engine": "auto", "sql_engine": null, "ci": "github",
     "approvers": []}

Keys this release no longer reads are ignored with one warning naming
`purlin:init --update`.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

GATES = ('tested', 'recorded', 'approved')
DEFAULT_GATE = 'tested'

# gate -> (ai_review_at, min_strength, tags required)
_DERIVED = {
    'tested': ('never', 50, False),
    'recorded': ('high', 70, False),
    'approved': ('medium', 80, True),
}

RETIRED_KEYS = (
    'remote_verification', 'mutation_checks', 'quality_gate', 'platforms',
    'spec_dir', 'audit_criteria', 'audit_mode', 'audit_threshold',
)

# `pre_push` survives as on or off. Any other value named a policy this
# release no longer has.
_PRE_PUSH_VALUES = ('on', 'off', True, False)


class GateConfig(object):
    """The resolved settings one run reads, plus the warnings resolving raised."""

    __slots__ = ('gate', 'ai_review_at', 'min_strength', 'mutation_engine',
                 'sql_engine', 'ci', 'approvers', 'tags_required',
                 'test_framework', 'pre_push', 'warnings')

    def __init__(self, **kwargs):
        for name in self.__slots__:
            setattr(self, name, kwargs.get(name))

    def as_dict(self):
        return {name: getattr(self, name) for name in self.__slots__
                if name != 'warnings'}

    def __repr__(self):
        return 'GateConfig(%r)' % (self.as_dict(),)


def resolve_gate(config):
    """`GateConfig` for a merged `.purlin/config.json`.

    An unrecognised `gate` falls back to `tested` with a warning: a typo must
    lower what CI enforces loudly, never raise it silently.
    """
    config = config or {}
    warnings = []

    gate = config.get('gate', DEFAULT_GATE)
    if gate not in GATES:
        if 'gate' in config:
            warnings.append(
                '"gate" is %r, which is not one of %s; reading it as %r'
                % (gate, ', '.join(GATES), DEFAULT_GATE))
        gate = DEFAULT_GATE

    ai_review_at, min_strength, tags_required = _DERIVED[gate]

    if 'ai_review_at' in config:
        ai_review_at = config['ai_review_at']
    if 'min_strength' in config:
        try:
            min_strength = int(config['min_strength'])
        except (TypeError, ValueError):
            warnings.append('"min_strength" is not a number; using %d'
                            % min_strength)

    pre_push = config.get('pre_push', 'off')
    if pre_push not in _PRE_PUSH_VALUES:
        warnings.append(
            '"pre_push" is %r; this release reads it as on or off only. '
            'Run purlin:init --update.' % (pre_push,))
        pre_push = 'on'
    pre_push = 'on' if pre_push in ('on', True) else 'off'

    retired = sorted(key for key in RETIRED_KEYS if key in config)
    if retired:
        warnings.append(
            '.purlin/config.json still carries %s, which this release does not '
            'read. Run purlin:init --update.' % ', '.join(retired))

    approvers = config.get('approvers') or []
    if not isinstance(approvers, list):
        warnings.append('"approvers" is not a list; reading it as empty')
        approvers = []

    resolved = GateConfig(
        gate=gate,
        ai_review_at=ai_review_at,
        min_strength=min_strength,
        mutation_engine=config.get('mutation_engine', 'auto'),
        sql_engine=config.get('sql_engine'),
        ci=config.get('ci'),
        approvers=[str(a).strip().lower() for a in approvers if str(a).strip()],
        tags_required=tags_required,
        test_framework=config.get('test_framework', 'auto'),
        pre_push=pre_push,
        warnings=warnings,
    )
    return resolved


def risk_at_or_above(risk, threshold):
    """True when `risk` is at or above `threshold` on low < medium < high.

    `never` is above every risk, so nothing ever reaches it.
    """
    order = {'low': 0, 'medium': 1, 'high': 2}
    if threshold == 'never' or threshold not in order:
        return False
    return order.get(risk, 0) >= order[threshold]


def one_level_lower(threshold):
    """The threshold one step down, for a project with no breaks engine.

    With nothing measuring test strength there is less evidence per rule, so
    the review net widens by one level rather than staying where a measured
    project leaves it.
    """
    order = ['high', 'medium', 'low']
    if threshold == 'never':
        return 'high'
    if threshold in order:
        index = order.index(threshold)
        return order[min(index + 1, len(order) - 1)]
    return threshold
