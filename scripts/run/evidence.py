"""Write the evidence a run leaves behind, and commit it.

    .purlin/evidence/<source>/<feature>.json   one file per feature per source

`references/formats/evidence_format.md` is the shape of the file and the one
home of the merge rules this module follows:

- A test run reads the file from disk and replaces `platforms[<this os>]`
  whole. Every other section and `audit` stay as they are.
- An audit run makes the same test-run write, then replaces
  `audit.rules[<rule>]` for each rule it read.
- Every write drops the `rules` and `audit.rules` entries of rules the spec
  no longer carries.
- Every run deletes the files under `local/` and `ci/` whose feature has no
  spec.

A run that saw the same thing over the same fingerprint on the same machine,
with the same `dirty`, leaves the file as it was where every commit since the one its section names
changes only paths under `.purlin/`, so running the tests twice has nothing
new to commit.

**Written, and committed when asked.** `purlin:test` and `purlin:audit`
write the files and do not commit them. `--commit` makes two commits under
the person's own identity, and nothing here pushes: first the specs, the
marked tests and the settings the results describe, as
`purlin: specs, tests and settings for <feature>, ...`, then the `local/`
files as `purlin: evidence at <sha7>`, naming the first. A project's own run
on another system, `--ci`, writes that system's section of the `ci/` files
the same way and, with `--commit`, makes one commit of those files alone,
under the git identity set in that checkout.
"""

import json
import os
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone

_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_RUN_DIR), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import evidence as reader                           # noqa: E402
from purlin import specs as spec_reader                          # noqa: E402
from purlin import states as states_module                      # noqa: E402

SCHEMA = reader.SCHEMA
EVIDENCE_DIR = reader.EVIDENCE_DIR
_EXPORT_DIR = os.path.join(os.path.dirname(_RUN_DIR), 'export')

COMMIT_SUBJECT = 'purlin: evidence at %s'
WORK_SUBJECT = 'purlin: specs, tests and settings for %s'
WORK_COMMITTED = 'Committed %s, the work these results describe:'
WRITTEN_ONE = 'Evidence written to %s.'
WRITTEN_MANY = 'Evidence written to %s/%s/ for %d features.'
COMMITTED = 'Evidence committed.'
UNCHANGED = 'Evidence unchanged.'
NO_REPOSITORY = ('Evidence written; there is no git repository to commit it '
                 'to.')
REMOVED = 'Removed %s: no spec defines %s.'


def now_iso():
    """The current time, ISO 8601 UTC with `Z`."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def runner_slug(email):
    """The `runner` a section carries: the email's local part, `-` safe."""
    local = str(email or '').split('@')[0].lower()
    slug = re.sub(r'[^a-z0-9]+', '-', local).strip('-')
    return slug or 'unknown'


def local_machine():
    """The `machine` a section carries: the host's name, or `unknown`."""
    return platform.node() or 'unknown'


def git_email(project_root):
    """The `email` a section carries: `git config user.email`, or `unknown`."""
    return (_git(project_root, ['config', 'user.email']) or '').strip() or 'unknown'


def full_path(project_root, rel):
    return os.path.join(project_root, *rel.split('/'))


# ---------------------------------------------------------------------------
# One section
# ---------------------------------------------------------------------------

def rule_word(proof_ids, proofs, observed, host_os):
    """The word one rule reads in a section, from this run alone.

    `observed` holds each proof's worst test: `fail`, then `not run`, then
    `pass`, so a rule reads `passed` only when every test tied to every
    proof that could run here ran and passed. In order: `failed` where a
    test of a proof that could run here failed; `no test` where a proof that
    is not `@manual`, tagged or not, has no test tied to it; `not run` where
    a tied test did not run or a proof another operating system owns waits
    on it; else `passed`. A `@manual` proof declares that no test is written
    for it, so a rule whose proofs are all manual has nothing for a run to
    observe and reads `checked at sign-off`, as its passed cell does until a
    sign-off notes it.
    """
    written = list(proof_ids or ())
    if not written:
        return 'no test'
    runnable = [pid for pid in written
                if not (proofs.get(pid) or {}).get('manual')]
    if not runnable:
        return states_module.CHECKED_AT_SIGNOFF
    foreign = [pid for pid in runnable
               if (proofs.get(pid) or {}).get('env')
               and (proofs.get(pid) or {}).get('env') != host_os]
    here = [pid for pid in runnable if pid not in foreign]
    # A test tied to a proof another system owns proves nothing here,
    # whatever it did, so only a proof that could run here can fail the rule.
    if any(observed.get(pid) == 'fail' for pid in here):
        return 'failed'
    # A proof with no test tied to it, here or on another system, waits on
    # a test to be written, and running again never clears it.
    if any(pid not in observed for pid in runnable):
        return 'no test'
    if here and all(observed.get(pid) == 'pass' for pid in here):
        return 'passed' if not foreign else 'not run'
    return 'not run'


_WORST = {'fail': 2, 'not run': 1, 'pass': 0}


def _observed(entries_by_id):
    """`{id: 'fail' | 'not run' | 'pass'}`, the worst test tied to each id.

    A tied test that neither passed nor failed reads `not run`.
    """
    observed = {}
    for marker_id, entries in entries_by_id.items():
        for entry in entries:
            status = entry.get('status')
            word = status if status in ('pass', 'fail') else 'not run'
            known = observed.get(marker_id)
            if known is None or _WORST[word] > _WORST[known]:
                observed[marker_id] = word
    return observed


def _nothing_to_check(seen):
    """The reasons, one per tied test, where every test tied to a proof
    skipped with a reason starting `nothing to check:`; else None."""
    reasons = [reader.nothing_reason(entry.get('reason'))
               if entry.get('status') not in ('pass', 'fail') else None
               for entry in seen]
    if seen and all(reason is not None for reason in reasons):
        return reasons
    return None


def build_section(info, entries_by_proof, host_os, commit, dirty, runner,
                  fingerprint, at=None, machine=None, only=None):
    """One platform section for one feature this run covered.

    `entries_by_proof` is `{id: [entry, ...]}`, what the run tied to each
    marker of this feature, where `id` is a `PROOF-N`, or a `RULE-N` for a
    rule with no proof whose test is marked by the rule's own id. Each entry
    is `{status, test_file, test_name, line, reason}`, `reason` the text a
    skipped test's tool gave or None, and `kept` where the result is one an
    earlier run took and this run carried over: the `commit`, `at`,
    `machine` and `email` of that run, written on the entry as it is given.
    One `proofs` entry is written per
    (id, test) pair, and one with an empty `test` for a proof nothing
    observed. A tied test that neither passed nor failed is `missing`, a
    proof tagged for another operating system reads `not run` whatever its
    tied test did here, and so does a slow proof's test the run left out,
    its entry carrying `held`.

    A proof whose every tied test skipped with a reason starting `nothing to
    check:` reads `nothing to check`, each entry carrying the `reason` after
    those words; its rule reads it as passed in an anchor's section and as
    not run in any other.

    `only`, under `--ci`, is the proofs tagged for this machine's system:
    the section then lists those proofs alone and the rules they prove, and
    each rule is read from those proofs alone.

    `machine` is where the tests ran, the host's name, and defaults to this
    host's. The section's `email` is added where it is written, by
    `write_section`.
    """
    proofs = info.get('proofs') or {}
    by_rule = info.get('proofs_by_rule') or {}
    observed = _observed(entries_by_proof)
    for proof_id in proofs:
        if _nothing_to_check(entries_by_proof.get(proof_id) or []):
            observed[proof_id] = 'pass' if info.get('is_anchor') else 'not run'
    rules = {}
    listed = []
    for rule_id in info.get('rule_order') or ():
        proof_ids = by_rule.get(rule_id) or []
        if only is not None:
            proof_ids = [pid for pid in proof_ids if pid in only]
            if not proof_ids:
                continue
        if not proof_ids:
            # No proof: a test marked with the rule's own id answers for it.
            seen = entries_by_proof.get(rule_id) or []
            rules[rule_id] = _rule_marked_word(observed.get(rule_id), seen)
            for entry in seen:
                status = entry.get('status')
                listed.append({'id': rule_id, 'rule': rule_id, 'env': None,
                               'manual': False, 'result': (
                                   status if status in ('pass', 'fail')
                                   else 'missing'),
                               'test': '%s::%s' % (entry.get('test_file', ''),
                                                   entry.get('test_name', ''))})
            continue
        rules[rule_id] = rule_word(proof_ids, proofs, observed, host_os)
        for proof_id in proof_ids:
            proof = proofs.get(proof_id) or {}
            env = proof.get('env')
            seen = entries_by_proof.get(proof_id) or []
            base = {'id': proof_id, 'rule': rule_id, 'env': env,
                    'manual': bool(proof.get('manual'))}
            foreign = bool(env and env != host_os)
            unseen = 'not run' if foreign else 'missing'
            nothing = None if foreign else _nothing_to_check(seen)
            for index, entry in enumerate(seen):
                status = entry.get('status')
                test = '%s::%s' % (entry.get('test_file', ''),
                                   entry.get('test_name', ''))
                if nothing is not None:
                    listed.append(_with_kept(dict(
                        base, result=reader.NOTHING_TO_CHECK,
                        reason=nothing[index], test=test), entry))
                    continue
                # A test carrying a Mac proof's marker and a Windows proof's
                # marker runs on the Mac and proves the Mac proof alone.
                took = status in ('pass', 'fail') and not foreign
                made = dict(base, result=(
                    status if took
                    else 'not run' if entry.get('held') else unseen),
                    test=test)
                listed.append(_with_kept(made, entry) if took else made)
            if not seen:
                listed.append(dict(base, result=unseen, test=''))
    return {
        'commit': commit or '',
        'dirty': bool(dirty),
        'at': at or now_iso(),
        'runner': runner,
        'machine': machine or local_machine(),
        'fingerprint': dict(fingerprint),
        'rules': rules,
        'proofs': listed,
    }


# What a kept result's `kept` names of the run that took it.
KEPT_KEYS = ('commit', 'at', 'machine', 'email')


def _with_kept(listed, entry):
    """`listed` carrying `kept` where the run handed the entry one."""
    kept = entry.get('kept')
    if isinstance(kept, dict):
        listed['kept'] = {key: kept.get(key) or '' for key in KEPT_KEYS}
    return listed


def _rule_marked_word(status, seen):
    """The word a rule with no proof reads from the tests marked with its id."""
    if status == 'fail':
        return 'failed'
    if status == 'pass' and all(entry.get('status') == 'pass'
                                for entry in seen):
        return 'passed'
    if seen:
        return 'not run'
    return 'no test'


def _same_observation(one, other):
    """True when the section on disk, `one`, saw what the new one, `other`,
    saw over the same fingerprint.

    `commit` and `at` say when a run happened, not what it saw, and `email`
    is kept and never compared. A run on another `machine`, or over a tree
    whose `dirty` differs, replaces the section. A proof entry's `kept` is
    left out, since a result this run carried over is the result the other
    run took; but a result the new run took itself replaces one the section
    on disk holds as kept.
    """
    def seen(section):
        found = {key: value for key, value in (section or {}).items()
                 if key not in ('commit', 'at', 'email')}
        found['dirty'] = bool(found.get('dirty'))
        if isinstance(found.get('proofs'), list):
            found['proofs'] = [
                {key: value for key, value in entry.items() if key != 'kept'}
                if isinstance(entry, dict) else entry
                for entry in found['proofs']]
        return found

    def kept(section):
        return {(entry.get('id'), entry.get('test'))
                for entry in (section or {}).get('proofs') or ()
                if isinstance(entry, dict) and 'kept' in entry}
    if kept(one) - kept(other):
        return False
    return json.loads(json.dumps(seen(one))) == json.loads(json.dumps(
        seen(other)))


# ---------------------------------------------------------------------------
# Reading and merging one file
# ---------------------------------------------------------------------------

def read_file(project_root, source, feature):
    """The file on disk for one source, when it is one this writer may merge into.

    A file that is not JSON, is not an object, carries another schema or
    names another source is not merged into: the reader ignores it, so the
    writer starts that file afresh rather than carrying what nobody reads.
    """
    path = full_path(project_root, reader.evidence_path(source, feature))
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (IOError, OSError, UnicodeDecodeError, ValueError):
        return None
    return parse(data, source)


def conflict_sides(text):
    """The two sides of a file a merge left conflicted, as their two texts.

    The lines outside every hunk belong to both sides. Within a hunk the
    lines after `<<<<<<<` make one side and those after `=======` the
    other; a `|||||||` base belongs to neither. [] when the text holds no
    conflict line.
    """
    ours, theirs = [], []
    where = 'both'
    seen = False
    for line in text.splitlines():
        if spec_reader.CONFLICT_RE.match(line):
            seen = True
            where = {'<': 'ours', '|': 'base', '=': 'theirs',
                     '>': 'both'}[line[0]]
            continue
        if where in ('both', 'ours'):
            ours.append(line)
        if where in ('both', 'theirs'):
            theirs.append(line)
    return ['\n'.join(ours), '\n'.join(theirs)] if seen else []


def read_conflicted(project_root, source, feature):
    """Each side of the feature's file that parses, where a merge left it
    conflicted; [] for a file that reads as JSON or holds no conflict."""
    path = full_path(project_root, reader.evidence_path(source, feature))
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            text = handle.read()
        json.loads(text)
        return []
    except (IOError, OSError, UnicodeDecodeError):
        return []
    except ValueError:
        pass
    sides = []
    for side in conflict_sides(text):
        try:
            data = parse(json.loads(side), source)
        except ValueError:
            continue
        if data is not None:
            sides.append(data)
    return sides


def kept_audits(sides, current):
    """The entries a write over a conflicted file keeps: `{rule: entry}`.

    `sides` are the file's parsed sides, `current` is `{rule: (rule_hash,
    proof_hash, test_hash)}` for the rule as it stands. Every `audit.rules`
    entry whose three hashes equal the current ones is kept, the newer `at`
    where both sides hold one.
    """
    entries = {}
    for side in sides:
        audit = side.get('audit')
        if not isinstance(audit, dict):
            continue
        rules = audit.get('rules')
        for rule_id, entry in (rules.items() if isinstance(rules, dict)
                               else ()):
            if not isinstance(entry, dict) or rule_id not in current:
                continue
            if (entry.get('rule_hash'), entry.get('proof_hash'),
                    entry.get('test_hash')) != tuple(current[rule_id]):
                continue
            kept = entries.get(rule_id)
            if kept is None or str(entry.get('at') or '') > str(
                    kept.get('at') or ''):
                entries[rule_id] = entry
    return entries


def parse(data, source):
    """`data` when it is a file of this format and this source, else None."""
    if (isinstance(data, dict) and data.get('schema') == SCHEMA
            and data.get('source') == source):
        return data
    return None


def empty_file(source, feature, spec_path):
    return {'schema': SCHEMA, 'feature': feature, 'source': source,
            'spec': spec_path or '', 'platforms': {}}


def merge_section(data, source, feature, spec_path, os_name, section,
                  rule_ids, same_code=None):
    """`data` with `platforms[os_name]` replaced and removed rules dropped.

    A section that saw the same results over the same fingerprint on the
    same machine, with the same `dirty`, as the one already there is left
    as it was, `at` and
    `commit` included, where it names the same commit or `same_code(<its
    commit>, <the new commit>)` holds: every commit between them changes
    only Purlin's own records. Returns a new dict.
    """
    merged = json.loads(json.dumps(data)) if data else empty_file(
        source, feature, spec_path)
    merged['spec'] = spec_path or merged.get('spec') or ''
    platforms = merged.get('platforms')
    if not isinstance(platforms, dict):
        platforms = {}
    kept = platforms.get(os_name)
    if not (isinstance(kept, dict) and _same_observation(kept, section)
            and _same_code(kept.get('commit'), section.get('commit'),
                           same_code)):
        platforms[os_name] = section
    merged['platforms'] = platforms
    return drop_removed_rules(merged, rule_ids)


def _same_code(older, newer, same_code):
    if older == newer:
        return True
    return bool(older and newer and same_code is not None
                and same_code(older, newer))


def same_code_in(project_root):
    """The `same_code` test a write in this checkout applies:
    `package.only_records_between`, which the sign-off reads as well."""
    def between(older, newer):
        if _EXPORT_DIR not in sys.path:
            sys.path.insert(0, _EXPORT_DIR)
        import package
        return package.only_records_between(project_root, older, newer)
    return between


def merge_audit(data, source, feature, spec_path, entries, rule_ids):
    """`data` with `audit.rules[R]` replaced for each entry given.

    `audit` holds `rules` alone. An entry that repeats the one there, with
    the same four hashes, `verdict`, `findings`, `no_bug`, `model` and
    `criteria`, keeps its `at` and `commit`, so reading a rule again finds
    nothing new to commit.
    """
    merged = json.loads(json.dumps(data)) if data else empty_file(
        source, feature, spec_path)
    audit = merged.get('audit')
    rules = audit.get('rules') if isinstance(audit, dict) else None
    if not isinstance(rules, dict):
        rules = {}
    for rule_id, entry in (entries or {}).items():
        kept = rules.get(rule_id)
        if isinstance(kept, dict) and _same_audit(kept, entry):
            continue
        rules[rule_id] = entry
    merged['audit'] = {'rules': rules}
    return drop_removed_rules(merged, rule_ids)


def audit_entry(rule, found, commit, at=None):
    """The `audit.rules` entry for one rule the audit read.

    `rule` is the payload's rule entry, whose three hashes key the entry
    with `found`'s `code_hash`, the `code` part of the feature's fingerprint
    when the audit read the rule. `found` holds code_hash, verdict, findings,
    no_bug, breaks, explanation, model, criteria, notes: the `verdict`
    (`strong`, `weak` or `spot-checked`), the `findings`, under `no_bug` one
    sentence for each proof no bug was caught for, the `breaks`, one per
    proof a bug was planted for, the model's reading as `explanation`, the
    `model` that answered, the sha256 of the `criteria` it was sent, and any
    `notes`, which enter no comparison and are written only when there are
    some.
    """
    entry = {'rule_hash': rule.get('rule_hash'),
             'proof_hash': rule.get('proof_hash'),
             'test_hash': rule.get('test_hash'),
             'code_hash': found.get('code_hash') or '',
             'verdict': found.get('verdict'),
             'findings': [str(line) for line in found.get('findings') or ()],
             'no_bug': [str(line) for line in found.get('no_bug') or ()],
             'breaks': {str(proof): dict(made) for proof, made
                        in (found.get('breaks') or {}).items()},
             'explanation': [str(line)
                             for line in found.get('explanation') or ()],
             'model': found.get('model') or 'unknown',
             'criteria': found.get('criteria') or '',
             'at': at or now_iso(), 'commit': commit or ''}
    notes = [str(line) for line in found.get('notes') or ()]
    if notes:
        entry['notes'] = notes
    return entry


def _same_audit(one, other):
    keys = ('rule_hash', 'proof_hash', 'test_hash', 'code_hash', 'verdict',
            'findings', 'no_bug', 'model', 'criteria')
    return all(one.get(key) == other.get(key) for key in keys)


def drop_removed_rules(data, rule_ids):
    """Drop the `rules` and `audit.rules` entries of rules the spec no longer has."""
    keep = set(rule_ids or ())
    for section in (data.get('platforms') or {}).values():
        if isinstance(section, dict) and isinstance(section.get('rules'), dict):
            section['rules'] = {rule: word for rule, word
                                in section['rules'].items() if rule in keep}
    audit = data.get('audit')
    if isinstance(audit, dict) and isinstance(audit.get('rules'), dict):
        audit['rules'] = {rule: entry for rule, entry
                          in audit['rules'].items() if rule in keep}
    return data


def dump(data):
    """The text a file holds: sorted keys, two-space indent, one newline."""
    return json.dumps(data, indent=2, sort_keys=True) + '\n'


def write_file(project_root, source, feature, data):
    """Write one file when its text changed. Its project-relative path.

    Every line ends in `\\n` on every system: a file written as text on
    Windows would otherwise end each line in `\\r\\n`, and the sections
    another system wrote would no longer be the bytes they were.
    """
    rel = reader.evidence_path(source, feature)
    path = full_path(project_root, rel)
    text = dump(data)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            if handle.read() == text:
                return rel
    except (IOError, OSError, UnicodeDecodeError):
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
    return rel


def write_section(project_root, source, feature, info, os_name, section):
    """Merge one section into the feature's file on disk. The path.

    A section given no `email` is written with `git_email`'s, whatever
    the source.
    """
    if 'email' not in section:
        section = dict(section, email=git_email(project_root))
    merged = merge_section(read_file(project_root, source, feature), source,
                           feature, info.get('spec_path', ''), os_name,
                           section, info.get('rule_order') or (),
                           same_code_in(project_root))
    return write_file(project_root, source, feature, merged)


def write_audit(project_root, source, feature, info, entries):
    """Merge one audit's entries into the feature's file on disk. The path."""
    merged = merge_audit(read_file(project_root, source, feature), source,
                         feature, info.get('spec_path', ''), entries,
                         info.get('rule_order') or ())
    return write_file(project_root, source, feature, merged)


# ---------------------------------------------------------------------------
# Removing the files whose feature has no spec
# ---------------------------------------------------------------------------

def prune(project_root, features):
    """Delete every evidence file whose feature no spec defines. The paths."""
    removed = []
    for source in reader.SOURCES:
        folder = full_path(project_root, '%s/%s' % (EVIDENCE_DIR, source))
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            if not name.endswith('.json'):
                continue
            feature = name[:-len('.json')]
            if feature in features:
                continue
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                continue
            removed.append(reader.evidence_path(source, feature))
    return removed


def written_line(paths, source='local'):
    """The one line naming what a run wrote: the file, or the folder and a count."""
    paths = [path for path in paths or ()]
    if len(paths) == 1:
        return WRITTEN_ONE % paths[0]
    return WRITTEN_MANY % (EVIDENCE_DIR, source, len(paths))


# ---------------------------------------------------------------------------
# The commits
# ---------------------------------------------------------------------------

def commit_work(project_root, paths):
    """Commit the work a run's results describe. The sha the evidence names.

    `paths` are the specs of the features run, the test files carrying
    their markers and `.purlin/config.json`. Those that changed are
    committed under the person's own identity as
    `purlin: specs, tests and settings for <feature>, ...`, the features
    being the specs named, and the commit and each path it changed are
    printed. Returns the new commit's full sha, HEAD's when none of `paths`
    changed, and `''` outside a git repository.
    """
    if _git(project_root, ['rev-parse', '--git-dir']) is None:
        return ''
    head = (_git(project_root, ['rev-parse', '--verify', '-q', 'HEAD'])
            or '').strip()
    paths = [path for path in _unique(paths) if _known(project_root, path)]
    if not paths:
        return head
    listed = _git(project_root, ['status', '--porcelain', '--'] + paths)
    if not (listed or '').strip():
        return head
    features = _unique(_feature_of(path) for path in paths
                       if _feature_of(path))
    if (_git(project_root, ['add', '--all', '--'] + paths) is None
            or _git(project_root, ['commit', '-m', WORK_SUBJECT
                                   % ', '.join(features), '--'] + paths)
            is None):
        return head
    sha = (_git(project_root, ['rev-parse', 'HEAD']) or '').strip()
    changed = _git(project_root, ['show', '--no-renames', '--name-only',
                                  '--format=', sha]) or ''
    print(WORK_COMMITTED % sha[:7])
    for path in changed.splitlines():
        if path.strip():
            print('  %s' % path.strip())
    return sha


def _feature_of(path):
    """The feature a spec path names, `specs/<category>/<feature>.md`, or None."""
    parts = str(path).split('/')
    if len(parts) >= 2 and parts[0] == 'specs' and parts[-1].endswith('.md'):
        return parts[-1][:-len('.md')]
    return None


def _unique(items):
    out = []
    for item in items or ():
        if item not in out:
            out.append(item)
    return out


def commit_local(project_root, work_sha, removed=()):
    """Commit the `local/` files and what the run removed.

    The second of a run's two commits. Its subject names `work_sha`, the
    commit `commit_work` made, or HEAD when it made none. The commit is the
    person's own, under their own identity, and nothing here pushes. A file
    a run removed from `ci/` because its feature has no spec is committed as
    that removal; nothing else under `ci/` is staged, because that folder is
    a `--ci` run's. Prints `Evidence committed.`, `Evidence unchanged.`, or
    that there is no git repository to commit to.
    """
    print(commit_paths(
        project_root,
        ['%s/local' % EVIDENCE_DIR] + list(removed or ()),
        COMMIT_SUBJECT % (str(work_sha or '')[:7] or 'an unknown commit')))


def commit_ci(project_root, head_sha, removed=()):
    """Commit the `ci/` files and what the run removed, as
    `purlin: evidence at <sha7 of head_sha>`. Prints COMMITTED or UNCHANGED.

    The one commit of a `--ci --commit` run, under the git identity set in
    that checkout. `head_sha` is HEAD when the run started. Nothing else is
    staged, and nothing here pushes. Outside a git repository it prints that
    there is none to commit to.
    """
    print(commit_paths(
        project_root,
        ['%s/ci' % EVIDENCE_DIR] + list(removed or ()),
        COMMIT_SUBJECT % (str(head_sha or '')[:7] or 'an unknown commit')))


def commit_paths(project_root, paths, message):
    """Commit `paths` under the checkout's git identity. The line to print."""
    paths = [path for path in paths if _known(project_root, path)]
    if not paths:
        return UNCHANGED
    listed = _git(project_root, ['status', '--porcelain', '--'] + paths)
    if listed is None:
        return NO_REPOSITORY
    if not listed.strip():
        return UNCHANGED
    if _git(project_root, ['add', '--all', '--'] + paths) is None:
        return NO_REPOSITORY
    if _git(project_root, ['commit', '-m', message, '--'] + paths) is None:
        return NO_REPOSITORY
    return COMMITTED


def _known(project_root, path):
    """True when git can be handed this pathspec without refusing it.

    A pathspec naming nothing on disk and nothing in the index makes git
    exit non-zero, which would read as "there is no repository here".
    """
    if os.path.exists(full_path(project_root, path)):
        return True
    listed = _git(project_root, ['ls-files', '--', path])
    return bool((listed or '').strip())


def _git(project_root, args):
    """One git command's stdout, or None when git could not do it."""
    try:
        result = subprocess.run(['git'] + list(args), capture_output=True,
                                text=True, cwd=project_root, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None
