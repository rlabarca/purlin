#!/usr/bin/env python3
"""Write the approvals a person or CI attests, and commit a person's signed.

    approve.py <feature> [RULE-N ...] [--batch] [--project-root DIR]

An approval is one named person's attestation that a rule, its proof and its
test belong together. It is one file, so two approvals never conflict:

    specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.<approver-slug>.json
    specs/<category>/<feature>.approvals/<RULE-N>.<hash8>.ci.json

`hash8` is the first eight characters of the triple the approval binds, and the
slug is the approver's email local part, lowercased, with every non-alphanumeric
character replaced by `-`. CI writes the `.ci.json` form for low-risk rules and
nothing else.

`references/formats/approval_format.md` holds the file shape field by field.
The three hashes come from the payload, which is the one place they are
computed, so an approval this script writes is current the moment it lands.

Exit codes: 0 the approvals were written and committed, 1 nothing could be
approved or the commit is not signed, 2 the command line was wrong.
"""

import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
for _path in (_MCP_DIR, _HERE):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from purlin import (approvals as approvals_module,             # noqa: E402
                    console as console_module, gate as gate_module,
                    payload as payload_module, specs as specs_module)

SCHEMA = 'purlin-approval/1'
USAGE = ('Usage: approve.py <feature> [RULE-N ...] [--batch] '
         '[--project-root DIR]')

EXIT_OK = 0
EXIT_NOTHING = 1
EXIT_BAD_INVOCATION = 2

# The one-time setup A5 prints, in the order a person runs it.
SIGNING_SETUP = (
    'git config gpg.format ssh',
    'git config user.signingkey ~/.ssh/id_ed25519.pub',
    'git config commit.gpgsign true',
)


# ---------------------------------------------------------------------------
# The payload, and one rule in it
# ---------------------------------------------------------------------------

def load_payload(project_root, payload=None):
    """The payload to read, built when the caller did not hand one over."""
    if payload is not None:
        return payload
    return payload_module.build_payload(project_root, generated_by='approve')


def rule_entry(payload, feature, rule):
    """The rule dict for `<feature> <rule>`, or None.

    A feature entry lists the rules it must prove, which includes the ones it
    requires from an anchor. The rule that belongs to `feature` is the one
    whose own `feature` field names it, so approving a required rule approves
    it where it lives and not once per consumer.
    """
    for entry in (payload or {}).get('features') or ():
        for item in entry.get('rules') or ():
            if item.get('feature') == feature and item.get('id') == rule:
                return item
    return None


def rule_proof_test_hashes(project_root, feature, rule, payload=None):
    """`(rule_hash, proof_hash, test_hash, test_hash_kind, design_hash)`.

    R is the rule text with its tags stripped and its whitespace normalised,
    P the proof descriptions in order, T the test files backing them and D the
    pinned design a `origin: design` rule rests on. A rule that is not in the
    payload has no hashes and every element is None.
    """
    entry = rule_entry(load_payload(project_root, payload), feature, rule)
    if entry is None:
        return (None, None, None, None, None)
    return (entry.get('rule_hash'), entry.get('proof_hash'),
            entry.get('test_hash'), entry.get('test_hash_kind'),
            entry.get('design_hash'))


def triple_for(entry):
    """The triple hash of one rule entry."""
    return approvals_module.triple_hash(
        entry.get('rule_hash'), entry.get('proof_hash'), entry.get('test_hash'))


# ---------------------------------------------------------------------------
# Writing one approval
# ---------------------------------------------------------------------------

def approval_path(project_root, feature, rule, triple, approver_slug):
    """Where the approval for one rule goes, beside the spec that holds it."""
    info = specs_module.scan_specs(project_root).get(feature)
    directory = approvals_module.approvals_dir(project_root, info or {})
    if not directory:
        return None
    return os.path.join(directory,
                        '%s.%s.%s.json' % (rule, str(triple)[:8], approver_slug))


def write_approval(project_root, feature, rule, approver_email, brief_path,
                   record_path, gate, risk, payload=None, entry=None):
    """Write one approval file and return its project-relative path.

    `approver_email` is `ci` for an auto-approval, which is the one approval
    no person signs: what bounds it is the auto-approval rule, not a signature.
    """
    entry = entry or rule_entry(load_payload(project_root, payload), feature, rule)
    if entry is None:
        return None
    is_ci = str(approver_email).lower() == 'ci'
    slug = 'ci' if is_ci else approvals_module.approver_slug(approver_email)
    triple = triple_for(entry)
    path = approval_path(project_root, feature, rule, triple, slug)
    if not path:
        return None

    body = {
        'schema': SCHEMA,
        'feature': feature,
        'rule': rule,
        'triple': triple[:16],
        'rule_hash': entry.get('rule_hash'),
        'proof_hash': entry.get('proof_hash'),
        'test_hash': entry.get('test_hash'),
        'test_hash_kind': entry.get('test_hash_kind'),
        'design_hash': entry.get('design_hash'),
        'risk': risk if risk is not None else entry.get('risk'),
        'approver': 'ci' if is_ci else str(approver_email),
        'timestamp': payload_module.now_iso(),
        'gate': gate,
        'brief': brief_path,
        'record': record_path,
    }
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(body, handle, indent=2, sort_keys=True)
        handle.write('\n')
    return os.path.relpath(path, project_root).replace(os.sep, '/')


def brief_for(project_root, feature, rule, triple):
    """The brief written for this triple, or None when nobody wrote one."""
    path = approval_path(project_root, feature, rule, triple, 'brief')
    if path and os.path.isfile(path):
        return os.path.relpath(path, project_root).replace(os.sep, '/')
    return None


# ---------------------------------------------------------------------------
# CI auto-approval
# ---------------------------------------------------------------------------

def auto_approve(project_root, payload=None, record_path=None):
    """Write the `.ci.json` approvals a CI run may write. Returns their paths.

    Low risk only, and only with a passing record and test strength at or above
    `min_strength` (or with no engine to measure it and every free check on the
    proof text clear). A `@manual` proof is never auto-approved: its evidence
    is a person's note, which is the one thing CI cannot write. A rule that
    already carries a current approval is left alone.
    """
    payload = load_payload(project_root, payload)
    gate = (payload.get('gate') or {}).get('gate') or gate_module.DEFAULT_GATE
    written = []
    for feature_entry in payload.get('features') or ():
        latest = feature_entry.get('latest_record') or {}
        for entry in feature_entry.get('rules') or ():
            if entry.get('feature') != feature_entry.get('name'):
                continue
            if not _may_auto_approve(entry):
                continue
            triple = triple_for(entry)
            path = write_approval(
                project_root, entry['feature'], entry['id'], 'ci',
                brief_for(project_root, entry['feature'], entry['id'], triple),
                record_path or latest.get('path'), gate, entry.get('risk'),
                entry=entry)
            if path:
                written.append(path)
    return written


def _may_auto_approve(entry):
    if (entry.get('risk') or 'low') != 'low':
        return False
    if entry.get('state') == 'Approved':
        return False
    if not (entry.get('flags') or {}).get('auto_approvable'):
        return False
    for proof in entry.get('proofs') or ():
        if proof.get('tier') == 'manual':
            return False
    return True


# ---------------------------------------------------------------------------
# A person's signed commit
# ---------------------------------------------------------------------------

def signing_configured(project_root):
    """True when this checkout is set up to sign a commit."""
    key = _config(project_root, 'user.signingkey')
    return bool(key)


def _config(project_root, name):
    try:
        result = subprocess.run(['git', 'config', '--get', name],
                                capture_output=True, text=True,
                                cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def signing_help():
    """The lines to print when a person has no signing set up yet."""
    lines = ['Commit signing is not configured, so an approval you make would '
             'not count. Run:']
    lines.extend('  %s' % command for command in SIGNING_SETUP)
    lines.append('Then upload the public key to the git host, under signing '
                 'keys, so it shows the commit as verified.')
    return lines


def commit_message(targets):
    """The subject for one approval commit, from `references/commit_conventions.md`."""
    features = []
    for feature, rule in targets:
        if feature not in features:
            features.append(feature)
    if len(features) == 1:
        rules = [rule for _feature, rule in targets]
        return 'approve(%s): %s' % (features[0], ' '.join(rules))
    parts = []
    for feature in features:
        rules = [rule for name, rule in targets if name == feature]
        parts.append('%s %s' % (feature, ' '.join(rules)))
    return 'approve(batch): %s' % ', '.join(parts)


def approve_and_commit(project_root, targets, approver_email, batch=False):
    """Write every approval in `targets` and commit them once, signed.

    `targets` is `[(feature, rule), ...]`. One invocation is one commit whether
    it carries one rule or forty, so `batch` says only that the caller
    collected the list rather than naming it. Returns the commit sha, or None
    when nothing was written.
    """
    payload = load_payload(project_root)
    gate = (payload.get('gate') or {}).get('gate') or gate_module.DEFAULT_GATE
    paths = []
    written = []
    for feature, rule in targets:
        entry = rule_entry(payload, feature, rule)
        if entry is None:
            continue
        triple = triple_for(entry)
        latest = _latest_record(payload, feature)
        path = write_approval(
            project_root, feature, rule, approver_email,
            brief_for(project_root, feature, rule, triple), latest, gate,
            entry.get('risk'), entry=entry)
        if path:
            paths.append(path)
            written.append((feature, rule))
    if not paths:
        return None
    return _commit(project_root, paths, commit_message(written))


def _latest_record(payload, feature):
    for entry in (payload or {}).get('features') or ():
        if entry.get('name') == feature:
            return (entry.get('latest_record') or {}).get('path')
    return None


def _commit(project_root, paths, message):
    add = subprocess.run(['git', 'add', '--'] + list(paths),
                         capture_output=True, text=True, cwd=project_root,
                         timeout=30)
    if add.returncode != 0:
        return None
    commit = subprocess.run(['git', 'commit', '-S', '-m', message],
                            capture_output=True, text=True, cwd=project_root,
                            timeout=60)
    if commit.returncode != 0:
        return None
    head = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True,
                          text=True, cwd=project_root, timeout=10)
    return head.stdout.strip() if head.returncode == 0 else None


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------

class _Args(object):
    """One parsed invocation, or the reason it could not be parsed."""

    __slots__ = ('feature', 'rules', 'batch', 'project_root', 'error', 'help')

    def __init__(self):
        self.feature = None
        self.rules = []
        self.batch = False
        self.project_root = '.'
        self.error = None
        self.help = False


def _parse(argv):
    """The parsed command line, with `error` or `help` set when it is neither."""
    args = _Args()
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ('-h', '--help'):
            args.help = True
            return args
        if item == '--batch':
            args.batch = True
        elif item == '--project-root':
            if not rest:
                args.error = '--project-root needs a directory.'
                return args
            args.project_root = rest.pop(0)
        elif item.startswith('--'):
            args.error = 'unknown option %s' % item
            return args
        elif item.startswith('RULE-'):
            args.rules.append(item)
        elif args.feature is None:
            args.feature = item
        else:
            args.error = 'unexpected argument %s' % item
            return args
    if args.feature is None and not args.batch:
        args.error = 'name a feature, or pass --batch.'
    return args


def approvable(payload, feature=None, rules=None):
    """Every `(feature, rule)` a person may approve now, in review order."""
    order = {'high': 0, 'medium': 1, 'low': 2}
    found = []
    for entry in (payload or {}).get('features') or ():
        for item in entry.get('rules') or ():
            if item.get('feature') != entry.get('name'):
                continue
            if feature and item.get('feature') != feature:
                continue
            if rules and item.get('id') not in rules:
                continue
            if item.get('state') in ('Drafted', 'Proof ready'):
                continue
            found.append((order.get(item.get('risk'), 2),
                          item['feature'], item['id']))
    found.sort()
    return [(name, rule) for _rank, name, rule in found]


def main(argv=None):
    console_module.force_utf8_stdio()
    args = _parse(sys.argv[1:] if argv is None else argv)
    if args.help:
        print(__doc__.strip())
        return EXIT_OK
    if args.error:
        print(USAGE, file=sys.stderr)
        print('approve.py: %s' % args.error, file=sys.stderr)
        return EXIT_BAD_INVOCATION
    project_root = args.project_root
    if not os.path.isdir(project_root or '.'):
        print('approve.py: not a directory: %r' % project_root, file=sys.stderr)
        return EXIT_BAD_INVOCATION

    payload = load_payload(project_root)
    resolved = gate_module.resolve_gate(
        {'gate': (payload.get('gate') or {}).get('gate')})
    email = _config(project_root, 'user.email').lower()
    approvers = (payload.get('gate') or {}).get('approvers') or []

    if resolved.gate == 'approved' and not approvers:
        print('approve: approver list missing: run purlin:init --gate approved')
        return EXIT_NOTHING
    if approvers and email not in approvers:
        print('approve: %s is not on the approver list. Add it by pull '
              'request, or ask someone on it.' % (email or 'this checkout'))
        return EXIT_NOTHING

    targets = approvable(payload, args.feature, args.rules or None)
    if not targets:
        print('approve: nothing to approve here. Run purlin:review to see what '
              'needs a look.')
        return EXIT_NOTHING

    if not signing_configured(project_root):
        for line in signing_help():
            print(line)
        return EXIT_NOTHING

    sha = approve_and_commit(project_root, targets, email, batch=args.batch)
    if not sha:
        print('approve: the approval commit was not made. Check that signing '
              'works and that the files are not already committed.')
        return EXIT_NOTHING
    print('Approved %d rule%s in %s.'
          % (len(targets), '' if len(targets) == 1 else 's', sha[:7]))
    for name, rule in targets:
        print('  %s %s' % (name, rule))
    return EXIT_OK


if __name__ == '__main__':
    sys.exit(main())
