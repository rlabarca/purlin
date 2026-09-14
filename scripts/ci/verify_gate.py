#!/usr/bin/env python3
"""The gate CI runs before a change may merge.

    python3 scripts/ci/verify_gate.py --check [--json] [--project-root DIR]

One project setting decides what this job requires. The gate is read from
`.purlin/config.json` and nothing else has to be configured:

    tested     every rule has a passing tagged test, in a record CI or the
               developer committed
    recorded   every rule has a record CI wrote for this commit, with the test
               strength at or above `min_strength`
    approved   `recorded`, plus a current approval on every high and medium
               rule, signed by someone on the approver list and already on the
               protected branch; low risk is auto-approved by CI

**The setting is the declaration, not the enforcement.** `.purlin/config.json`
is a file in the repository that an agent can edit. What enforces the gate is
the git host: a branch rule marking this job a required check, a rule
restricting who may push `.purlin/records/**`, and a rule blocking force pushes.
`purlin:init` prints all three when it writes the workflow.

What this job reads is the structured payload, built from the specs, the
records and the approvals in the checkout in front of it. It never parses a
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

PREFIX = 'verify-gate:'

# How many rules each section names before it counts the rest. A job log a
# person scrolls past names nothing; twenty is a screen.
SHOWN = 20

_ENFORCEMENT_NOTE = (
    'the gate is declared in .purlin/config.json, which an agent can edit. '
    'The enforcement is the git host: this job is a required check and '
    '.purlin/records/** is restricted to the build identity.')

_APPROVER_LIST_MISSING = (
    '→ approver list missing: run purlin:init --gate approved')

# What each gate needs a rule to have reached, from `states.STATE_ORDER`.
_REQUIRED_STATE = {
    'tested': 'Tested',
    'recorded': 'Recorded',
    'approved': 'Recorded',
}


def _package():
    """The reader package, or None when this is not a Purlin checkout."""
    try:
        from purlin import (approvals, gate, payload, records, specs, states)
    except ImportError:
        return None
    return {'approvals': approvals, 'gate': gate, 'payload': payload,
            'records': records, 'specs': specs, 'states': states}


def _rank(states_module, state):
    try:
        return states_module.STATE_ORDER.index(state)
    except ValueError:
        return 0


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
                project_root, generated_by='verify_gate')
        except (OSError, ValueError):
            _say(out, 'the evidence in %r could not be read.' % project_root)
            _say(out, 'failing closed. A gate that cannot read the evidence '
                      'does not pass the branch.')
            return EXIT_BAD_INVOCATION

    settings = payload.get('gate') or {}
    gate = settings.get('gate') or package['gate'].DEFAULT_GATE
    min_strength = settings.get('min_strength') or 0
    approvers = [str(a).lower() for a in settings.get('approvers') or ()]

    result = {
        'gate': gate,
        'min_strength': min_strength,
        'commit': payload.get('commit'),
        'rules': 0,
        'met': 0,
        'below_state': [],
        'below_strength': [],
        'unapproved': [],
        'verdict': 'pass',
    }

    _say(out, 'gate = %s' % gate)
    _say(out, _ENFORCEMENT_NOTE)

    if gate == 'approved' and not approvers:
        _say(out, _APPROVER_LIST_MISSING)
        result['verdict'] = 'fail'
        result['approver_list'] = 'missing'
        if as_json:
            _dump(out, result, EXIT_GATE_FAILED)
        return EXIT_GATE_FAILED

    _collect(project_root, package, payload, gate, min_strength, approvers,
             result)

    _say(out, '%d rules across %d features; minimum test strength %d.'
              % (result['rules'], len(payload.get('features') or ()),
                 min_strength))

    _report(out, gate, result)

    failing = (result['below_state'] or result['below_strength']
               or result['unapproved'])
    if failing:
        result['verdict'] = 'fail'
        _say(out, 'FAIL. %d of %d rules do not meet %s.'
                  % (len(failing), result['rules'], gate))
        if as_json:
            _dump(out, result, EXIT_GATE_FAILED)
        return EXIT_GATE_FAILED

    _say(out, 'PASS. Every rule meets %s.' % gate)
    if as_json:
        _dump(out, result, EXIT_OK)
    return EXIT_OK


def _collect(project_root, package, payload, gate, min_strength, approvers,
             result):
    """Fill `result` with the rules that fall short, and why."""
    states_module = package['states']
    needed = _rank(states_module, _REQUIRED_STATE.get(gate, 'Tested'))

    all_approvals = None
    branch = None
    if gate == 'approved':
        all_approvals = package['approvals'].load_approvals(
            project_root, package['specs'].scan_specs(project_root))
        branch = _protected_branch(project_root, package)

    for feature in payload.get('features') or ():
        strength = feature.get('test_strength')
        for entry in feature.get('rules') or ():
            if entry.get('feature') != feature.get('name'):
                continue          # counted once, under the feature that owns it
            result['rules'] += 1
            rule = '%s %s' % (entry['feature'], entry['id'])
            state = entry.get('state')

            if _rank(states_module, state) < needed:
                result['below_state'].append(
                    '%s: %s%s' % (rule, state,
                                  _why(entry, gate)))
                continue

            if gate in ('recorded', 'approved') and strength is not None \
                    and strength < min_strength:
                result['below_strength'].append(
                    '%s: test strength %d percent, below %d'
                    % (rule, strength, min_strength))
                continue

            if gate == 'approved':
                missing = _approval_gap(project_root, package, entry,
                                        all_approvals, approvers, branch)
                if missing:
                    result['unapproved'].append('%s: %s' % (rule, missing))
                    continue

            result['met'] += 1


def _why(entry, gate):
    """One clause naming what the rule is short of, from what the state says."""
    reasons = list(entry.get('reasons') or ())
    if entry.get('state') == 'Stale':
        reasons.append('the rule, the proof or the test changed after the '
                       'approval')
    elif gate != 'tested':
        reasons.append('no record CI wrote covers this commit')
    if not reasons:
        return ''
    return ' (%s)' % '; '.join(reasons)


def _approval_gap(project_root, package, entry, all_approvals, approvers,
                  branch):
    """Why a high or medium rule is not approved, or `''` when it is.

    Low risk is auto-approved by CI, so it needs nothing beyond the record it
    already has.
    """
    risk = entry.get('risk') or 'low'
    if risk == 'low':
        return ''
    approvals_module = package['approvals']
    found = all_approvals.get((entry['feature'], entry['id'])) or []
    reasons = []
    for approval in found:
        if approval.get('is_ci'):
            reasons.append('the only approval is a CI auto-approval, which '
                           'does not count for %s risk' % risk)
            continue
        if not approvals_module.is_current(
                approval, entry.get('rule_hash'), entry.get('proof_hash'),
                entry.get('test_hash'), risk, entry.get('design_hash')):
            reasons.append('the approval is stale')
            continue
        counted, reason = approvals_module.counts(
            project_root, approval, approvers, _test_paths(entry))
        if not counted:
            reasons.append(reason)
            continue
        if branch and not approvals_module.is_ancestor(
                project_root, approval['path'], branch):
            reasons.append('the approval commit is not on %s yet' % branch)
            continue
        return ''
    return reasons[0] if reasons else 'no approval'


def _test_paths(entry):
    paths = []
    for proof in entry.get('proofs') or ():
        for test in proof.get('tests') or ():
            if test.get('file') and test['file'] not in paths:
                paths.append(test['file'])
    return paths


def _protected_branch(project_root, package):
    """The branch an approval has to have reached, `origin/` when there is one."""
    name = package['records'].default_branch(project_root)
    import subprocess
    for candidate in ('origin/%s' % name, name):
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--verify', '--quiet',
                 '--end-of-options', candidate],
                capture_output=True, text=True, cwd=project_root, timeout=10)
        except (subprocess.SubprocessError, OSError):
            return None
        if result.returncode == 0:
            return candidate
    return None


def _report(out, gate, result):
    sections = (
        ('Not %s' % _REQUIRED_STATE.get(gate, 'tested').lower(),
         result['below_state']),
        ('Below the minimum test strength', result['below_strength']),
        ('Not approved', result['unapproved']),
    )
    for title, lines in sections:
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
        prog='verify_gate.py',
        description='The gate CI runs before a change may merge.')
    parser.add_argument('--check', action='store_true',
                        help='Run the gate and exit 0 (met) or 1 (not met).')
    parser.add_argument('--json', action='store_true',
                        help='Print the verdict as JSON after the report.')
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
        print('verify_gate.py: --check is required.', file=sys.stderr)
        return EXIT_BAD_INVOCATION

    if not os.path.isdir(args.project_root):
        print('verify_gate.py: not a directory: %r' % args.project_root,
              file=sys.stderr)
        return EXIT_BAD_INVOCATION

    return check(args.project_root, as_json=args.json)


if __name__ == '__main__':
    sys.exit(main())
