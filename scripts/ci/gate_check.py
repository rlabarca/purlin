#!/usr/bin/env python3
"""The gate CI runs before a change may merge.

    python3 scripts/ci/gate_check.py --check [--json] [--project-root DIR]

One project setting decides what this job requires. The gate is read from
`.purlin/config.json` and nothing else has to be configured:

    passed  every rule's passed cell is met: the tagged tests pass, from any
            source
    strong  every rule's strong cell is met too: a record CI wrote, test
            strength at or above the project minimum, no finding standing
            against the proof text or the test body, no manual test and no
            manual audit outstanding, and nobody holding the rule
    signed  every rule's signed cell is met too: a person on the signer list
            signed the rule, proof and test hashes

**The setting is the declaration, not the enforcement.** `.purlin/config.json`
is a file in the repository that an agent can edit. What enforces the gate is
the git host: a branch rule marking this job a required check, a rule
restricting who may push `.purlin/records/**` and `.purlin/briefs/**`, and a
rule blocking force pushes. `purlin:init` prints all three when it writes the
workflow.

What this job reads is the structured payload, which has already worked out
every rule's cells. A rule meets the gate when `meets_gate` is true, and
`blocked_by` names the lowest cell that is not met, so this job groups the
rules by that one field and prints the cell's own reasons. It never parses a
rendered table, because a table's columns are presentation and move with the
dashboard. It writes nothing: a gate that can edit the evidence it grades is
not a gate.

Exit codes: 0 the gate is met, 1 the gate is not met, 2 the invocation was
wrong or the evidence could not be read. It fails closed, so an error reading
the evidence is never a pass.
"""

import argparse
import json
import os
import sys

_CI_DIR = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_CI_DIR), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import console as console_module                  # noqa: E402

EXIT_OK = 0
EXIT_GATE_FAILED = 1
EXIT_BAD_INVOCATION = 2

PREFIX = 'gate:'

# How many rules each section names before it counts the rest. A job log a
# person scrolls past names nothing; twenty is a screen.
SHOWN = 20

_ENFORCEMENT_NOTE = (
    'the gate is declared in .purlin/config.json, which an agent can edit. '
    'The enforcement is the git host: this job is a required check and '
    '.purlin/records/** and .purlin/briefs/** are restricted to the build '
    'identity.')

_SIGNER_LIST_MISSING = (
    '→ signer list missing: run purlin:init --gate signed')

# The strong cell's words for work only a person can do. A rule blocked on one
# of them is not weak: nothing a build would change moves it.
_WAITING_WORDS = ('manual test', 'manual audit', 'held')

# One section per cell a rule can be blocked at, in the order the chain reads
# them. The spec status blocks before the passed cell does, and both mean the
# same thing to a branch: the rule is not passed. The strong cell fills two
# sections, because `weak` is build work and the three waiting words are not.
_SECTIONS = (('not_passed', 'Not passed', ('spec', 'passed')),
             ('weak', 'Weak', ('strong',)),
             ('waiting', 'Waiting on a person', ()),
             ('not_signed', 'Not signed', ('signed',)))


def _package():
    """The reader package, or None when this is not a Purlin checkout."""
    try:
        from purlin import gate, payload
    except ImportError:
        return None
    return {'gate': gate, 'payload': payload}


def check(project_root, payload=None, out=None, as_json=False):
    """Run the gate. Returns an exit code and writes nothing but its report."""
    out = sys.stdout if out is None else out
    package = _package()
    if package is None or not os.path.isdir(
            os.path.join(project_root, '.purlin')):
        _say(out, 'cannot read a Purlin project at %r.' % project_root)
        _say(out, 'failing closed. A gate that cannot read the evidence does '
                  'not pass the branch.')
        return EXIT_BAD_INVOCATION

    if payload is None:
        try:
            payload = package['payload'].build_payload(
                project_root, generated_by='gate_check')
        except (OSError, ValueError):
            _say(out, 'the evidence in %r could not be read.' % project_root)
            _say(out, 'failing closed. A gate that cannot read the evidence '
                      'does not pass the branch.')
            return EXIT_BAD_INVOCATION

    settings = payload.get('gate') or {}
    gate = settings.get('gate') or package['gate'].DEFAULT_GATE
    min_strength = settings.get('min_strength')
    signers = [str(name).lower() for name in settings.get('signers') or ()]

    result = {
        'gate': gate,
        'min_strength': min_strength,
        'commit': payload.get('commit'),
        'rules': 0,
        'met': 0,
        'not_passed': [],
        'weak': [],
        'waiting': [],
        'not_signed': [],
        'result': 'pass',
    }

    _say(out, 'gate = %s' % gate)
    _say(out, _ENFORCEMENT_NOTE)

    if gate == 'signed' and not signers:
        _say(out, _SIGNER_LIST_MISSING)
        result['result'] = 'fail'
        result['signer_list'] = 'missing'
        if as_json:
            _dump(out, result, EXIT_GATE_FAILED)
        return EXIT_GATE_FAILED

    _collect(payload, result)

    # Nothing measures a test strength under `passed`, so naming a minimum
    # there would print a number the gate never reads.
    if gate == package['gate'].GATES[0] or min_strength is None:
        _say(out, '%d rules across %d features.'
                  % (result['rules'], len(payload.get('features') or ())))
    else:
        _say(out, '%d rules across %d features; minimum test strength %d.'
                  % (result['rules'], len(payload.get('features') or ()),
                     min_strength))

    _report(out, result)

    short = sum(len(result[key]) for key, _title, _cells in _SECTIONS)
    if short:
        result['result'] = 'fail'
        _say(out, 'FAIL. %d of %d rules do not meet %s.'
                  % (short, result['rules'], gate))
        if as_json:
            _dump(out, result, EXIT_GATE_FAILED)
        return EXIT_GATE_FAILED

    _say(out, 'PASS. Every rule meets %s.' % gate)
    if as_json:
        _dump(out, result, EXIT_OK)
    return EXIT_OK


def _collect(payload, result):
    """Fill `result` with the rules that fall short, and why.

    A rule is counted once, under the feature that owns it: a rule an anchor
    declares is proved by every feature that requires it, and counting it once
    per consumer would report one gap several times.
    """
    by_cell = {cell: key for key, _title, cells in _SECTIONS for cell in cells}
    for feature in payload.get('features') or ():
        for entry in feature.get('rules') or ():
            if entry.get('feature') != feature.get('name'):
                continue
            result['rules'] += 1
            if entry.get('meets_gate'):
                result['met'] += 1
                continue
            key = by_cell.get(entry.get('blocked_by'))
            if key is None:
                # A rule that meets no cell and names none is still short of
                # the gate, and the passed section is where a reader looks
                # first.
                key = 'not_passed'
            elif key == 'weak' and _cell_word(entry, 'strong') in _WAITING_WORDS:
                key = 'waiting'
            result[key].append('%s %s: %s'
                               % (entry['feature'], entry['id'],
                                  _why(entry)))


def _cell_word(entry, name):
    """One cell's word, or the empty string where the cell does not exist."""
    return ((entry.get('cells') or {}).get(name) or {}).get('word') or ''


def _why(entry):
    """The blocking cell's word and its reasons, as one clause."""
    blocked = entry.get('blocked_by')
    if blocked == 'spec':
        word = entry.get('spec') or 'drafted'
        reasons = _blocking_findings(entry)
    else:
        cell = (entry.get('cells') or {}).get(blocked) or {}
        word = cell.get('word') or 'not met'
        reasons = list(cell.get('reasons') or ())
    if not reasons:
        return word
    return '%s (%s)' % (word, '; '.join(reasons))


def _blocking_findings(entry):
    """The free-check findings that hold a rule's spec status at `drafted`."""
    from purlin import checks

    found = []
    for proof in entry.get('proofs') or ():
        for finding in proof.get('findings') or ():
            if finding in checks.BLOCKING and finding not in found:
                found.append(finding)
    if not found and not (entry.get('proofs') or ()):
        return ['no proof names this rule']
    return found


def _report(out, result):
    for key, title, _cells in _SECTIONS:
        lines = result[key]
        if not lines:
            continue
        print('', file=out)
        print('%s (%d):' % (title, len(lines)), file=out)
        for line in lines[:SHOWN]:
            print('  %s' % line, file=out)
        if len(lines) > SHOWN:
            print('  and %d more; --json prints every one.'
                  % (len(lines) - SHOWN), file=out)
    print('', file=out)


def _say(out, line):
    print('%s %s' % (PREFIX, line), file=out)


def _dump(out, result, code):
    result['exit'] = code
    print(json.dumps(result, indent=2, sort_keys=True), file=out)


def main(argv=None):
    console_module.force_utf8_stdio()
    parser = argparse.ArgumentParser(
        prog='gate_check.py',
        description='The gate CI runs before a change may merge.')
    parser.add_argument('--check', action='store_true',
                        help='Run the gate and exit 0 (met) or 1 (not met).')
    parser.add_argument('--json', action='store_true',
                        help='Print the result as JSON after the report.')
    parser.add_argument('--project-root', default='.',
                        help='Project root to check (default: cwd).')
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # argparse exits 2 on a usage error, which is already this script's
        # bad-invocation code. Keep it rather than letting it surface as 0.
        return EXIT_BAD_INVOCATION

    if not args.check:
        parser.print_usage(sys.stderr)
        print('gate_check.py: --check is required.', file=sys.stderr)
        return EXIT_BAD_INVOCATION

    if not os.path.isdir(args.project_root):
        print('gate_check.py: not a directory: %r' % args.project_root,
              file=sys.stderr)
        return EXIT_BAD_INVOCATION

    return check(args.project_root, as_json=args.json)


if __name__ == '__main__':
    sys.exit(main())
