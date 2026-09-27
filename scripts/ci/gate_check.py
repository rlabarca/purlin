#!/usr/bin/env python3
"""The gate, checked as the last step of every CI run.

    python3 scripts/ci/gate_check.py --check [--verify] [--json]
                                     [--project-root DIR]

One project setting decides what this job requires. The gate is read from
`.purlin/config.json` and nothing else has to be configured:

    passed  every rule's passed cell is met: the tagged tests pass, from any
            source, on every operating system a counting run covered
    strong  every rule whose bar is `strong` has a strong cell that is met:
            a record an audit wrote, from either source, test strength at or
            above the project minimum, nothing unsettled and nobody holding
            the rule
    signed  every rule that needs a signature has one: a person on the signer
            list signed the rule, proof, test, bar and audit hashes.
            `sign_at` says which rules need one, `strong` (the rules whose
            bar is `strong`) or `all`

`--verify` is what the tag run adds, and it asks two more questions of the
evidence already in the tree. Every signature and every hold must still bind
the rule, proof, test, bar and audit it names, so a tag cannot stand over code
that changed after it was signed. Every file under `.purlin/records/ci/**` and
`.purlin/briefs/ci/**` must have been committed by the runner's own identity,
read off the commit that added it, so a person cannot write a record as CI's.
A file that fails either is named and the job fails.

**The setting is the declaration, not the enforcement.** `.purlin/config.json`
is a file in the repository that an agent can edit. What enforces it is the
tag run: `purlin:sign` writes `signed/<version>` only when every rule meets
the gate, a person pushes the tag, and this job reruns the tests on a clean
machine and verifies the evidence against the tagged code.

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
    'What stands behind it is the tag: purlin:sign writes signed/<version> '
    'only when every rule meets the gate, and this run checks the evidence '
    'against the tagged code.')

_SIGNER_LIST_MISSING = (
    '→ signer list missing: run purlin:init --gate signed')

# One section per kind of work, in the order the chain reads it. The spec
# status blocks before the passed cell does, and both mean the same thing to
# a branch: the rule is not passed. The passed cell fills two sections,
# because a rule that passes on one operating system and not on another is a
# different piece of work from one that passes nowhere. The strong cell fills
# three, because `weak` is build work, `not audited` is a run and the review
# words are a person's.
_SECTIONS = (('not_passed', 'Not passed', ('spec', 'passed')),
             ('partial', 'Partial', ()),
             ('weak', 'Weak', ('strong',)),
             ('not_audited', 'Not audited', ()),
             ('to_review', 'To review', ()),
             ('to_sign', 'To sign', ('signed',)),
             ('evidence', 'Evidence', ()))


def _package():
    """The reader package, or None when this is not a Purlin checkout."""
    try:
        from purlin import gate, payload
    except ImportError:
        return None
    return {'gate': gate, 'payload': payload}


def verify(project_root, payload):
    """What `--verify` found wrong with the evidence already in the tree.

    Two questions. Does every signature and hold still bind the rule, proof,
    test, bar and audit it names? And was every file under the `ci/` folders
    committed by the runner itself? Each answer that is no is one line naming
    the file, and any line at all fails the job.
    """
    from purlin import signatures as signatures_module, specs as specs_module

    by_rule = {}
    for feature in payload.get('features') or ():
        for entry in feature.get('rules') or ():
            by_rule[(entry.get('feature'), entry.get('id'))] = entry

    problems = []
    features = specs_module.scan_specs(project_root)
    bound = [(key, files, True) for key, files
             in sorted(signatures_module.load_signatures(
                 project_root, features).items())]
    bound += [(key, files, False) for key, files
              in sorted(signatures_module.load_holds(
                  project_root, features).items())]
    for key, files, is_signature in bound:
        entry = by_rule.get(key)
        for attestation in files:
            path = attestation.get('path') or '%s %s' % key
            if entry is None:
                problems.append('%s: no rule %s %s is in this project'
                                % (path, key[0], key[1]))
                continue
            # A hold says the test does not prove the proof, which is a
            # statement about the rule, the proof and the test; a re-audit
            # does not answer it, so the audit hash is not bound into one.
            audit = entry.get('audit_hash') if is_signature else None
            if not signatures_module.is_current(
                    attestation, entry.get('rule_hash'),
                    entry.get('proof_hash'), entry.get('test_hash'),
                    entry.get('bar'), entry.get('design_hash'), audit):
                problems.append('%s: what it binds is not this code' % path)
    return problems + _provenance(project_root)


def _provenance(project_root):
    """Every file under a `ci/` folder the runner itself did not commit.

    The folder is the source, and this is what keeps it honest: the commit
    that added each file, and whether its identity is the runner's own. No
    branch rule stands behind the folder, so a file a person wrote into it is
    found here and nowhere else.
    """
    from purlin import records as records_module

    problems = []
    for base in (records_module.RECORDS_DIR, records_module.BRIEFS_DIR):
        root = os.path.join(project_root, base, 'ci')
        for current, _dirs, names in os.walk(root):
            for name in sorted(names):
                if not name.endswith('.json'):
                    continue
                rel = os.path.relpath(os.path.join(current, name),
                                      project_root).replace(os.sep, '/')
                if records_module.record_label(project_root, rel) != 'ci':
                    problems.append(
                        '%s: the commit that added it is not the runner\'s'
                        % rel)
    return problems


def check(project_root, payload=None, out=None, as_json=False,
          verify_evidence=False):
    """Run the gate. Returns an exit code and writes nothing but its report."""
    out = sys.stdout if out is None else out
    package = _package()
    if package is None or not os.path.isdir(
            os.path.join(project_root, '.purlin')):
        _say(out, 'cannot read a Purlin project at %r.' % project_root)
        _say(out, 'failing closed. A gate that cannot read the evidence '
                  'does not say the gate was met.')
        return EXIT_BAD_INVOCATION

    if payload is None:
        try:
            payload = package['payload'].build_payload(
                project_root, generated_by='gate_check')
        except (OSError, ValueError):
            _say(out, 'the evidence in %r could not be read.' % project_root)
            _say(out, 'failing closed. A gate that cannot read the evidence '
                      'does not say the gate was met.')
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
        'partial': [],
        'weak': [],
        'not_audited': [],
        'to_review': [],
        'to_sign': [],
        'evidence': [],
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
    if verify_evidence:
        result['evidence'] = verify(project_root, payload)

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
    from purlin import states

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
            word = _cell_word(entry, 'strong')
            if key is None:
                # A rule that meets no cell and names none is still short of
                # the gate, and the passed section is where a reader looks
                # first.
                key = 'not_passed'
            elif key == 'not_passed' and _cell_word(entry, 'passed') == 'partial':
                key = 'partial'
            elif key == 'weak' and word in states.REVIEW_WORDS:
                # Work only a person can do. A rule blocked on one of these
                # is not weak: nothing a build would change moves it.
                key = 'to_review'
            elif key == 'weak' and word == states.NOT_AUDITED:
                # Not weak and not a person's either: running `purlin:audit`
                # settles it, so it gets a section naming that one command.
                key = 'not_audited'
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
        reasons = ['no proof names this rule']
    else:
        cell = (entry.get('cells') or {}).get(blocked) or {}
        word = cell.get('word') or 'not met'
        reasons = list(cell.get('reasons') or ())
    if not reasons:
        return word
    return '%s (%s)' % (word, '; '.join(reasons))


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
        description='The gate, checked as the last step of every CI run.')
    parser.add_argument('--check', action='store_true',
                        help='Run the gate and exit 0 (met) or 1 (not met).')
    parser.add_argument('--verify', action='store_true',
                        help='Also check the committed evidence against this '
                             'code and the runner\'s own identity.')
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

    return check(args.project_root, as_json=args.json,
                 verify_evidence=args.verify)


if __name__ == '__main__':
    sys.exit(main())
