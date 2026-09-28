"""The one project setting, and what it derives.

A project sets `gate` in `.purlin/config.json` and nothing else has to be
decided. The gate names the deepest evidence level a version has to reach
before it is proven, and every level above it is not asked for at all:

`passed`  every rule's passed cell is met: the tagged tests pass, from any
          source
`strong`  every rule's strong cell is met too: the AI audit read the
          rule's current text, proof and test and found nothing, and where
          mutation testing is on, the test strength reaches the minimum
`signed`  every rule has a counting signature too: a person signed the
          rule, proof, test and audit hashes in a signed commit. Who signed
          is logged, not policed

A rule may ask for less than the gate with a `[level: ...]` tag, which takes
the gate's own three words. The gate is the ceiling: a rule's level is the
lower of its tag and the gate, and a rule with no tag takes the gate.

One setting is not derived from the gate: `trust`, which `purlin:init` asks
for once. `local`, the default, is a project that trusts this machine for
the tests and the signing. `remote` is one that does not, and there
`purlin:sign` refuses a rule whose tests have no `ci` run current for the
code being signed.

Everything else has a default, and every default can be overridden by naming
the key:

    {"gate": "strong", "min_strength": 70, "mutation_engine": "auto",
     "audit_parallel": 4, "ci": "github", "trust": "local"}

The test suites, under `tests`, are read where the tests run, by
`markers.read_suites`, and are not part of the gate.

Mutation testing is optional. `mutation_engine` set to `none` turns it off:
no breaks run and `min_strength` is not applied, so the AI audit alone
decides the strong cell. `auto` or an engine's name turns it on, and a key
that is absent reads as `auto`. Under the gate `passed` nothing compares a
strength, so no breaks run there either.
`audit_parallel` is how many model calls `purlin:audit` makes at once, an
integer from 1 to 16; any other value is read as 4 with one warning.

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

# gate -> min_strength
#
# `min_strength` is None under `passed`: nothing compares test strength there,
# so there is no number to compare and the audit reads `n/a`.
_DERIVED = {
    'passed': None,
    'strong': 70,
    'signed': 80,
}

# What an absent `mutation_engine` reads as. `none` turns mutation testing off.
DEFAULT_MUTATION_ENGINE = 'auto'

# How many model calls the audit makes at once, and the range it may take.
DEFAULT_AUDIT_PARALLEL = 4
AUDIT_PARALLEL_RANGE = (1, 16)

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

    __slots__ = ('gate', 'min_strength', 'breaks',
                 'mutation_engine', 'audit_parallel', 'ci', 'trust',
                 'warnings')

    # What a surface reads is the settings a project can name. `breaks` is
    # derived from `mutation_engine` and `warnings` from resolving, so
    # neither is written out.
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

    min_strength = _DERIVED[gate]

    if config.get('min_strength') is None and 'min_strength' in config:
        # Written as null where mutation testing is off: no mark applies.
        min_strength = None
    elif 'min_strength' in config:
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

    mutation_engine = config.get('mutation_engine') or DEFAULT_MUTATION_ENGINE
    audit_parallel = _audit_parallel(config, warnings)

    retired = sorted(key for key in RETIRED_KEYS if key in config)
    if retired:
        warnings.append(
            '.purlin/config.json still carries %s, which this release does not '
            'read. Run purlin:init --update.' % ', '.join(retired))

    resolved = GateConfig(
        gate=gate,
        min_strength=min_strength,
        breaks=(gate != 'passed'
                and str(mutation_engine).strip().lower() != 'none'),
        mutation_engine=mutation_engine,
        audit_parallel=audit_parallel,
        ci=config.get('ci'),
        trust=trust,
        warnings=warnings,
    )
    return resolved


def _audit_parallel(config, warnings):
    """`audit_parallel` as an integer from 1 to 16, else 4 with one warning."""
    if 'audit_parallel' not in config:
        return DEFAULT_AUDIT_PARALLEL
    value = config['audit_parallel']
    low, high = AUDIT_PARALLEL_RANGE
    if isinstance(value, int) and not isinstance(value, bool) \
            and low <= value <= high:
        return value
    warnings.append('"audit_parallel" is %r, which is not a whole number from '
                    '%d to %d; reading it as %d'
                    % (value, low, high, DEFAULT_AUDIT_PARALLEL))
    return DEFAULT_AUDIT_PARALLEL


def level_of(marked, gate):
    """A rule's level: the lower of its `[level: ...]` tag and the gate.

    A rule with no tag, or with a value that is not one of the three words,
    takes the gate. The gate is the ceiling, so a tag above it is read as
    the gate.
    """
    gate = gate if gate in GATES else DEFAULT_GATE
    if marked not in GATES:
        return gate
    return GATES[min(GATES.index(marked), GATES.index(gate))]
