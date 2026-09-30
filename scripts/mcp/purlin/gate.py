"""The one project setting, and what it derives.

A project sets `gate` in `.purlin/config.json` and nothing else has to be
decided. The gate says what a release asks for:

`passed`  every rule's tests pass on the evidence committed at the release
          commit
`signed`  the same, and at least one person signs the evidence package.
          Who signed is logged, not policed

Every rule is asked what the gate asks.

Everything else has a default, and every default can be overridden by naming
the key:

    {"gate": "signed", "mutation_engine": "none", "audit_parallel": 4,
     "ci": "github"}

The test suites, under `tests`, are read where the tests run, by
`markers.read_suites`, and are not part of the gate.

The AI audit and mutation testing are tools a person runs with
`purlin:audit`, at either gate, and nothing waits on them.
`mutation_engine` set to `none` turns the breaks off; `auto` or an engine's
name turns them on, and a key that is absent reads as `none`, since mutation
testing is off until a project turns it on.
`audit_parallel` is how many model calls `purlin:audit` makes at once, an
integer from 1 to 16; any other value is read as 4 with one warning.

The keys an earlier release wrote that this release does not read are
ignored with one warning naming `purlin:init --update`, and a `gate` of
`strong` reads as `passed` with one warning naming the same command.
"""

import json
import os
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

GATES = ('passed', 'signed')
DEFAULT_GATE = 'passed'
RETIRED_KEYS = ('spec_dir', 'audit_criteria', 'pre_push', 'min_strength')

# What an absent `mutation_engine` reads as: mutation testing is off until a
# project turns it on.
DEFAULT_MUTATION_ENGINE = 'none'

# How many model calls the audit makes at once, and the range it may take.
DEFAULT_AUDIT_PARALLEL = 4
AUDIT_PARALLEL_RANGE = (1, 16)

# The lines a value the settings file holds and this release does not accept
# prints beside the status table. The value is written as JSON writes it.
NOT_A_GATE = ('%s is not accepted for gate in .purlin/config.json; it takes '
              'passed or signed. Reading it as passed; set it with '
              'purlin:init --gate <gate>.')
STRONG_RETIRED = ('"strong" is no longer a gate: it reads as passed, and the '
                  'audit stays a tool you run. Run purlin:init --update.')
NOT_A_PARALLEL = ('%s is not accepted for audit_parallel in '
                  '.purlin/config.json; it takes a whole number from %d to '
                  '%d. Reading it as %d; fix the file by hand.')
RETIRED_LINE = ('.purlin/config.json still carries %s, which this release '
                'does not read. Run purlin:init --update.')


class GateConfig(object):
    """The resolved settings one run reads, plus the warnings resolving raised."""

    __slots__ = ('gate', 'breaks', 'mutation_engine', 'audit_parallel', 'ci',
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
        if gate == 'strong':
            warnings.append(STRONG_RETIRED)
        elif 'gate' in config:
            warnings.append(NOT_A_GATE % json.dumps(gate))
        gate = DEFAULT_GATE

    mutation_engine = config.get('mutation_engine') or DEFAULT_MUTATION_ENGINE
    audit_parallel = _audit_parallel(config, warnings)

    retired = sorted(key for key in RETIRED_KEYS if key in config)
    if retired:
        warnings.append(RETIRED_LINE % ', '.join(retired))

    return GateConfig(
        gate=gate,
        breaks=str(mutation_engine).strip().lower() != 'none',
        mutation_engine=mutation_engine,
        audit_parallel=audit_parallel,
        ci=config.get('ci'),
        warnings=warnings,
    )


def _audit_parallel(config, warnings):
    """`audit_parallel` as an integer from 1 to 16, else 4 with one warning."""
    if 'audit_parallel' not in config:
        return DEFAULT_AUDIT_PARALLEL
    value = config['audit_parallel']
    low, high = AUDIT_PARALLEL_RANGE
    if isinstance(value, int) and not isinstance(value, bool) \
            and low <= value <= high:
        return value
    warnings.append(NOT_A_PARALLEL % (json.dumps(value), low, high,
                                      DEFAULT_AUDIT_PARALLEL))
    return DEFAULT_AUDIT_PARALLEL
