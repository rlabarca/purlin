"""The one project setting, and what it derives.

A project sets `gate` in `.purlin/config.json` and nothing else has to be
decided. The gate names the deepest evidence level a version has to reach
before it is proven, and every level above it is not asked for at all:

`passed`  every rule's passed cell is met: the tagged tests pass, from any
          source
`strong`  every rule's strong cell is met too: a record an audit wrote
          under either source, test strength at or above the project
          minimum, a settled AI audit where the bar asks for one, and nobody
          holding the rule
`signed`  every rule that needs a signature has a counting one: a person
          signed the rule, proof, test, bar and audit hashes in a signed
          commit. Who signed is logged, not policed

One setting is not derived from the gate: `trust`, which `purlin:init` asks
for once. `local`, the default, is a project that trusts this machine for
the tests and the signing. `remote` is one that does not, and there
`purlin:sign` refuses a rule whose tests have no `ci` record for the commit
being signed.

Everything else has a default derived from the gate, and every default can be
overridden by naming the key:

    {"gate": "strong", "min_strength": 70, "mutation_engine": "auto",
     "sql_engine": null, "ci": "github", "trust": "local"}

The keys v0.9.5 wrote that this release no longer reads are ignored with one
warning naming `purlin:init --update`.
"""

import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

GATES = ('passed', 'strong', 'signed')
DEFAULT_GATE = 'passed'

# The two bars a rule can carry, weakest first. A bar is the evidence a rule
# must have before it can be signed, and a rule that names none takes the
# project's gate as its bar.
BARS = ('passed', 'strong')

# The two values `sign_at` takes: a signature on the rules whose bar is
# `strong`, or a signature on every rule.
SIGN_AT_VALUES = ('strong', 'all')
DEFAULT_SIGN_AT = 'strong'

# An older project wrote one of three levels here. The bar replaced them, so
# the two that asked for a person map onto the rules whose bar is `strong`,
# and the one that asked for nobody asks for all of them instead.
_SIGN_AT_WAS = {'high': 'strong', 'medium': 'strong', 'low': 'all'}  # retired

# gate -> (min_strength, sign_at, breaks)
#
# `min_strength` is None under `passed`: nothing measures test strength there,
# so there is no number to compare and the record writes `n/a`.
_DERIVED = {
    'passed': (None, None, False),
    'strong': (70, None, True),
    'signed': (80, DEFAULT_SIGN_AT, True),
}

# Whether a project trusts this machine for the tests and the signing.
# `purlin:init` asks once and `purlin:init --update` asks again.
TRUST_VALUES = ('local', 'remote')
DEFAULT_TRUST = 'local'

RETIRED_KEYS = (
    'spec_dir', 'audit_criteria',
    'pre_push',                                                   # retired
)


class GateConfig(object):
    """The resolved settings one run reads, plus the warnings resolving raised."""

    __slots__ = ('gate', 'min_strength', 'sign_at', 'breaks',
                 'mutation_engine', 'sql_engine', 'ci',
                 'test_framework', 'trust', 'warnings')

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

    min_strength, sign_at, breaks = _DERIVED[gate]

    if 'sign_at' in config:
        sign_at = _read_sign_at(config['sign_at'], sign_at, warnings)
    if 'min_strength' in config:
        try:
            min_strength = int(config['min_strength'])
        except (TypeError, ValueError):
            warnings.append('"min_strength" is not a number; using %s'
                            % ('n/a' if min_strength is None else min_strength))

    trust = config.get('trust', DEFAULT_TRUST)
    if trust not in TRUST_VALUES:
        if 'trust' in config:
            warnings.append(
                '"trust" is %r, which is not one of %s; reading it as %r'
                % (trust, ', '.join(TRUST_VALUES), DEFAULT_TRUST))
        trust = DEFAULT_TRUST

    retired = sorted(key for key in RETIRED_KEYS if key in config)
    if retired:
        warnings.append(
            '.purlin/config.json still carries %s, which this release does not '
            'read. Run purlin:init --update.' % ', '.join(retired))

    resolved = GateConfig(
        gate=gate,
        min_strength=min_strength,
        sign_at=sign_at,
        breaks=breaks,
        mutation_engine=config.get('mutation_engine', 'auto'),
        sql_engine=config.get('sql_engine'),
        ci=config.get('ci'),
        test_framework=config.get('test_framework', 'auto'),
        trust=trust,
        warnings=warnings,
    )
    return resolved


def _read_sign_at(value, derived, warnings):
    """`sign_at` as this release reads it, from what the config named.

    A project written before the bar named one of three levels here. The
    value is mapped rather than refused, so raising a gate never silently
    asks for fewer signatures than the project had.
    """
    if value is None:
        return derived
    named = str(value).strip().lower()
    if named in SIGN_AT_VALUES:
        return named
    if named in _SIGN_AT_WAS:
        return _SIGN_AT_WAS[named]
    warnings.append(
        '"sign_at" is %r, which is not one of %s; reading it as %r'
        % (value, ', '.join(SIGN_AT_VALUES), derived))
    return derived


def default_bar(gate):
    """The bar a rule that names none takes: the project's own gate.

    `passed` at the gate `passed`, `strong` at `strong` and at `signed`, so a
    project that asks for strong evidence asks for it on every rule until a
    rule says otherwise.
    """
    return 'passed' if gate == GATES[0] else 'strong'


def needs_signature(gate, sign_at, bar):
    """True when a rule with this bar has to carry a signature.

    Only the `signed` gate asks for one at all. There `sign_at: all` asks on
    every rule and `sign_at: strong` asks on the rules whose bar is `strong`.
    """
    if gate != 'signed':
        return False
    if str(sign_at or DEFAULT_SIGN_AT) == 'all':
        return True
    return str(bar or 'passed') == 'strong'

