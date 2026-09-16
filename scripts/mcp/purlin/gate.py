"""The one project setting, and what it derives.

A project sets `gate` in `.purlin/config.json` and nothing else has to be
decided. The gate names the deepest evidence level CI requires before a change
can merge, and every level above it is not asked for at all:

`passed`  every rule's passed cell is met: the tagged tests pass, from any
          source
`strong`  every rule's strong cell is met too: a record CI wrote, test
          strength at or above the project minimum, no finding standing
          against the proof text or the test body, and nobody holding the rule
`signed`  every rule's signed cell is met too: a person on the signer list
          signed the rule, proof and test hashes

Everything else has a default derived from the gate, and every default can be
overridden by naming the key:

    {"gate": "strong", "ai_review_at": "high", "min_strength": 70,
     "mutation_engine": "auto", "sql_engine": null, "ci": "github",
     "signers": []}

Keys this release no longer reads are ignored with one warning naming
`purlin:init --update`.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

GATES = ('passed', 'strong', 'signed')
DEFAULT_GATE = 'passed'

# gate -> (ai_review_at, min_strength, sign_at, breaks)
#
# `min_strength` is None under `passed`: nothing measures test strength there,
# so there is no number to compare and the record writes `n/a`.
_DERIVED = {
    'passed': ('never', None, None, False),
    'strong': ('high', 70, None, True),
    'signed': ('medium', 80, 'medium', True),
}

RETIRED_KEYS = (
    'remote_verification', 'mutation_checks', 'quality_gate', 'platforms',
    'spec_dir', 'audit_criteria', 'audit_mode', 'audit_threshold',
    'approvers',                                                  # retired
)

# `pre_push` survives as on or off. Any other value named a policy this
# release no longer has.
_PRE_PUSH_VALUES = ('on', 'off', True, False)


class GateConfig(object):
    """The resolved settings one run reads, plus the warnings resolving raised."""

    __slots__ = ('gate', 'ai_review_at', 'min_strength', 'sign_at', 'breaks',
                 'mutation_engine', 'sql_engine', 'ci', 'signers',
                 'test_framework', 'pre_push', 'warnings')

    # What a surface reads is the settings a project can name. `breaks` and
    # `warnings` are derived from the gate alone, so neither is written out.
    _PRIVATE = ('warnings', 'breaks')

    def __init__(self, **kwargs):
        for name in self.__slots__:
            setattr(self, name, kwargs.get(name))

    def as_dict(self):
        return {name: getattr(self, name) for name in self.__slots__
                if name not in self._PRIVATE}

    def __repr__(self):
        return 'GateConfig(%r)' % (self.as_dict(),)


def resolve_gate(config):
    """`GateConfig` for a merged `.purlin/config.json`.

    An unrecognised `gate` falls back to `passed` with a warning: a typo must
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

    ai_review_at, min_strength, sign_at, breaks = _DERIVED[gate]

    if 'ai_review_at' in config:
        ai_review_at = config['ai_review_at']
    if 'sign_at' in config:
        sign_at = config['sign_at']
    if 'min_strength' in config:
        try:
            min_strength = int(config['min_strength'])
        except (TypeError, ValueError):
            warnings.append('"min_strength" is not a number; using %s'
                            % ('n/a' if min_strength is None else min_strength))

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

    signers = config.get('signers') or []
    if not isinstance(signers, list):
        warnings.append('"signers" is not a list; reading it as empty')
        signers = []

    resolved = GateConfig(
        gate=gate,
        ai_review_at=ai_review_at,
        min_strength=min_strength,
        sign_at=sign_at,
        breaks=breaks,
        mutation_engine=config.get('mutation_engine', 'auto'),
        sql_engine=config.get('sql_engine'),
        ci=config.get('ci'),
        signers=[str(s).strip().lower() for s in signers if str(s).strip()],
        test_framework=config.get('test_framework', 'auto'),
        pre_push=pre_push,
        warnings=warnings,
    )
    return resolved


def risk_at_or_above(risk, threshold):
    """True when `risk` is at or above `threshold` on low < medium < high.

    `never` is above every risk, so nothing ever reaches it, and `None` is the
    same answer written the way a gate that does not ask the question writes
    it.
    """
    order = {'low': 0, 'medium': 1, 'high': 2}
    if threshold in (None, 'never') or threshold not in order:
        return False
    return order.get(risk, 0) >= order[threshold]


def one_level_lower(threshold):
    """The threshold one step down, for a project with no breaks engine.

    With nothing measuring test strength there is less evidence per rule, so
    the review net widens by one level rather than staying where a measured
    project leaves it.
    """
    order = ['high', 'medium', 'low']
    if threshold is None:
        return None
    if threshold == 'never':
        return 'high'
    if threshold in order:
        index = order.index(threshold)
        return order[min(index + 1, len(order) - 1)]
    return threshold
