#!/usr/bin/env python3
"""The gate, checked as the last step of every CI run.

    python3 scripts/ci/gate_check.py --check [--verify] [--json]
                                     [--project-root DIR]

One project setting decides what this job requires. The gate is read from
`.purlin/config.json` and nothing else has to be configured:

    passed  every rule's passed cell is met: the marked tests pass, from any
            source, on every operating system a counting run covered
    strong  every rule whose level is `strong` or `signed` has a strong cell
            that is met: the AI audit, from either source, read the current
            text, proof and test and found nothing, and where mutation testing
            is on the test strength reaches the project minimum
    signed  every rule whose level is `signed` has a counting signature: a
            person signed the rule, proof, test and audit hashes in a signed
            commit

A rule's level is its `[level: ...]` tag, or the gate where it has none, and
never more than the gate.

At the gate `signed` a feature spec that names no files in `> Scope:` fails
the job too, listed under `Incomplete (<n>)` with why: no signature can be
tied to the code it governs. Below `signed` it blocks nothing here.

`--verify` is what the tag run adds, and it asks two more questions of the
evidence already in the tree. Every signature must still bind the rule, proof, test and audit it names, so a tag cannot stand over code
that changed after it was signed. Every file under `.purlin/evidence/ci/`
must have been committed by the runner's own identity, read off the commit
that last changed it, so a person cannot write evidence as CI's: on GitHub
from the commit's signature and committer, on Azure DevOps from who the host
says pushed it (`scripts/mcp/purlin/provenance.py`). A file that fails either
is named and the job fails. Off a runner an Azure DevOps project's `ci/`
files cannot be asked about, so they are counted as not checked.

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
_RUN_DIR = os.path.join(os.path.dirname(_CI_DIR), 'run')
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

# One section per kind of work, in the order the chain reads it. The passed
# cell fills two sections, because a rule that passes on one operating system
# and not on another is a different piece of work from one that passes
# nowhere. The strong cell fills three, because `weak` is build work, `not
# audited` is a run and a hand check is a person's. A hand check and a
# missing signature are both the queue, the one list a person works from.
_SECTIONS = (('not_passed', 'Not passed', ('passed',)),
             ('partial', 'Partial', ()),
             ('weak', 'Weak', ('strong',)),
             ('not_audited', 'Not audited', ()),
             ('queue', 'Queue', ('signed',)),
             ('evidence', 'Evidence', ()))

# The one section that lists features rather than rules: at the gate
# `signed`, each feature spec that names no files in `> Scope:`, which no
# signature can be tied to. Its rules that wait only on a signature are
# counted short of the gate and listed here, under their feature, instead of
# in the queue, because no person can sign them.
_INCOMPLETE = ('incomplete', 'Incomplete')


def _package():
    """The reader package, or None when this is not a Purlin checkout."""
    try:
        from purlin import gate, payload
    except ImportError:
        return None
    return {'gate': gate, 'payload': payload}


def verify(project_root, payload):
    """`(problems, not_checked, notice)` for the evidence already in the tree.

    Two questions. Does every signature still bind the rule, proof, test and
    audit it names? And was every file under the `ci/` folders
    committed by the runner itself? Each answer that is no is one line naming
    the file, and any line at all fails the job. `not_checked` lists the
    `ci/` files this machine could not ask about and `notice` says why.
    """
    from purlin import signatures as signatures_module, specs as specs_module

    by_rule = {}
    for feature in payload.get('features') or ():
        for entry in feature.get('rules') or ():
            by_rule[(entry.get('feature'), entry.get('id'))] = entry

    problems = []
    features = specs_module.scan_specs(project_root)
    for key, files in sorted(signatures_module.load_signatures(
            project_root, features).items()):
        entry = by_rule.get(key)
        for signature in files:
            path = signature.get('path') or '%s %s' % key
            if entry is None:
                problems.append('%s: no rule %s %s is in this project'
                                % (path, key[0], key[1]))
                continue
            if not signatures_module.is_current(
                    signature, entry.get('rule_hash'),
                    entry.get('proof_hash'), entry.get('test_hash'),
                    entry.get('audit_hash')):
                problems.append('%s: what it binds is not this code' % path)
    found, not_checked, notice = _provenance(project_root)
    return problems + found, not_checked, notice


def _provenance(project_root):
    """`(problems, not_checked, notice)` for every file under `ci/`.

    The folder is the source, and this is what keeps it honest: the commit
    that last changed each file, and whether the runner's own identity made
    it. No branch rule stands behind the folder, so a file a person wrote
    into it is found here and nowhere else.
    """
    from purlin import evidence as evidence_module, provenance

    folder = os.path.join(project_root,
                          *evidence_module.EVIDENCE_DIR.split('/'))
    folder = os.path.join(folder, 'ci')
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return [], [], None
    rels = ['%s/ci/%s' % (evidence_module.EVIDENCE_DIR, name)
            for name in names if name.endswith('.json')]
    problems, not_checked, notice = provenance.check(
        project_root, rels, _git_host(project_root))
    return (['%s: %s' % (rel, reason) for rel, reason in problems],
            not_checked, notice)


def _git_host(project_root):
    """`azure` or `github`: the runner's own variables first, then `origin`.

    A project whose remote is neither is read as GitHub's, whose check needs
    nothing but git.
    """
    if _RUN_DIR not in sys.path:
        sys.path.insert(0, _RUN_DIR)
    import host as host_module
    import workflow

    return (host_module.detect_host() or workflow.host_of(project_root)
            or 'github')


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
        'queue': [],
        'incomplete': [],
        'evidence': [],
        'not_checked': [],
        'result': 'pass',
    }

    _say(out, 'gate = %s' % gate)
    _say(out, _ENFORCEMENT_NOTE)

    _collect(payload, result)
    if verify_evidence:
        result['evidence'], result['not_checked'], notice = verify(
            project_root, payload)
        if notice:
            count = len(result['not_checked'])
            _say(out, notice)
            _say(out, '%d %s under .purlin/evidence/ci/ %s not checked.'
                      % (count, 'file' if count == 1 else 'files',
                         'is' if count == 1 else 'are'))

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

    short = (result['rules'] - result['met']) + len(result['evidence'])
    if short or result['incomplete']:
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
    signed = (payload.get('gate') or {}).get('gate') == 'signed'
    for feature in payload.get('features') or ():
        untied = signed and feature.get('incomplete')
        if untied:
            result['incomplete'].append('%s: %s' % (
                feature.get('name'), feature.get('incomplete_reason')
                or 'names no files'))
        for entry in feature.get('rules') or ():
            if entry.get('feature') != feature.get('name'):
                continue
            result['rules'] += 1
            if entry.get('meets_gate'):
                result['met'] += 1
                continue
            key = by_cell.get(entry.get('blocked_by'))
            word = _cell_word(entry, 'strong')
            if untied and key == 'queue':
                # Counted short above, and named under its feature in the
                # Incomplete section: no signature can be tied to it.
                continue
            if key is None:
                # A rule that meets no cell and names none is still short of
                # the gate, and the passed section is where a reader looks
                # first.
                key = 'not_passed'
            elif key == 'not_passed' and _cell_word(entry, 'passed') == 'partial':
                key = 'partial'
            elif key == 'weak' and word in states.HAND_CHECK_WORDS:
                # A hand check, which only a person can do. A rule blocked on
                # one is not weak: nothing a build would change moves it.
                key = 'queue'
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
    cell = (entry.get('cells') or {}).get(entry.get('blocked_by')) or {}
    word = cell.get('word') or 'not met'
    reasons = list(cell.get('reasons') or ())
    if not reasons:
        return word
    return '%s (%s)' % (word, '; '.join(reasons))


def _report(out, result):
    order = ([(key, title) for key, title, _cells in _SECTIONS[:-1]]
             + [_INCOMPLETE]
             + [(key, title) for key, title, _cells in _SECTIONS[-1:]])
    for key, title in order:
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
