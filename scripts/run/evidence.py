"""Write the evidence a run leaves behind, render the table, and commit both.

    .purlin/evidence/<source>/<feature>.json   one file per feature per source
    .purlin/tests.md                          one table for the whole project

`references/formats/evidence_format.md` is the shape of the file and the one
home of the merge rules this module follows:

- A test run reads the file from disk and replaces `platforms[<this os>]`
  whole. Every other section and `audit` stay as they are.
- An audit run makes the same test-run write, then replaces
  `audit.rules[<rule>]` for each rule it read and `audit.mutation` when
  mutation testing ran.
- Every write drops the `rules` and `audit.rules` entries of rules the spec
  no longer carries.
- Every run deletes the files under `local/` and `ci/` whose feature has no
  spec.

A run that saw the same thing over the same fingerprint on the same machine
leaves the file as it was, so running the tests twice has nothing new to
commit.

**Written, and committed when asked.** `purlin:test` and `purlin:audit`
write the files and do not commit them. `--commit` makes two commits under
the person's own identity, and nothing here pushes: first the specs, the
marked tests and the settings the results describe, as
`purlin: specs, tests and settings for <feature>, ...`, then the `local/`
files and the table as `purlin: evidence at <sha7>`, naming the first. A
remote runner is the one writer that always commits, through the git host's
API, because its evidence exists nowhere else; `host.py` makes that commit
and hands each file back here to be merged into what its parent holds.
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

SCHEMA = reader.SCHEMA
EVIDENCE_DIR = reader.EVIDENCE_DIR
TABLE_PATH = '.purlin/tests.md'

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

TABLE_HEADING = '# Tests at %s'
TABLE_COLUMNS = ('Feature', 'Rules', 'Passed', 'Failing', 'No test',
                 'Last run')
TABLE_NOTE = ('Each row is the newest run of that feature, whoever made it; '
              'the source in the last column says whose run it was.')
TABLE_EMPTY = 'No feature has been run yet.'

def now_iso():
    """The current time, ISO 8601 UTC with `Z`."""
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def runner_slug(email):
    """The `runner` a person's section carries: the email's local part, `-` safe."""
    local = str(email or '').split('@')[0].lower()
    slug = re.sub(r'[^a-z0-9]+', '-', local).strip('-')
    return slug or 'unknown'


def local_machine():
    """The `machine` a person's section carries: the host's name, or `unknown`."""
    return platform.node() or 'unknown'


def full_path(project_root, rel):
    return os.path.join(project_root, *rel.split('/'))


# ---------------------------------------------------------------------------
# One section
# ---------------------------------------------------------------------------

def rule_word(proof_ids, proofs, observed, host_os):
    """The word one rule reads in a section, from this run alone.

    `observed` holds each proof's worst test: `fail`, then `not run`, then
    `pass`, so a rule reads `passed` only when every test tied to every
    proof that could run here ran and passed. A `@manual` proof declares
    that no test is written for it, so a rule whose proofs are all manual
    has nothing for a run to observe and reads `passed`, as its passed cell
    does. A proof another operating system owns was not run here, so the
    rule reads `not run` rather than claiming there is no test.
    """
    written = list(proof_ids or ())
    if not written:
        return 'no test'
    runnable = [pid for pid in written
                if not (proofs.get(pid) or {}).get('manual')]
    if not runnable:
        return 'passed'
    foreign = [pid for pid in runnable
               if (proofs.get(pid) or {}).get('env')
               and (proofs.get(pid) or {}).get('env') != host_os]
    here = [pid for pid in runnable if pid not in foreign]
    # A test tied to a proof another system owns proves nothing here,
    # whatever it did, so only a proof that could run here can fail the rule.
    if any(observed.get(pid) == 'fail' for pid in here):
        return 'failed'
    if here and all(observed.get(pid) == 'pass' for pid in here):
        return 'passed' if not foreign else 'not run'
    if any(observed.get(pid) for pid in runnable):
        return 'not run'
    return 'no test'


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


def build_section(info, entries_by_proof, host_os, commit, dirty, runner,
                  fingerprint, at=None, machine=None, hostname=None,
                  only=None):
    """One platform section for one feature this run covered.

    `entries_by_proof` is `{id: [entry, ...]}`, what the run tied to each
    marker of this feature, where `id` is a `PROOF-N`, or a `RULE-N` for a
    rule with no proof whose test is marked by the rule's own id. One
    `proofs` entry is written per (id, test) pair, and one with an empty
    `test` for a proof nothing observed. A tied test that neither passed
    nor failed is `missing`, and a proof tagged for another operating
    system reads `not run` whatever its tied test did here.

    `only`, on a remote runner, is the proofs tagged for its system: the
    section then lists those proofs alone and the rules they prove, and
    each rule is read from those proofs alone.

    `machine` is where the tests ran: the host's name on a person's machine,
    `remote runner, <system>` on a remote runner. `hostname` is the host's
    own name, kept and never compared. Each defaults to this host.
    """
    proofs = info.get('proofs') or {}
    by_rule = info.get('proofs_by_rule') or {}
    observed = _observed(entries_by_proof)
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
            for entry in seen:
                status = entry.get('status')
                # A test carrying a Mac proof's marker and a Windows proof's
                # marker runs on the Mac and proves the Mac proof alone.
                listed.append(dict(base, result=(
                    status if status in ('pass', 'fail') and not foreign
                    else unseen),
                    test='%s::%s' % (entry.get('test_file', ''),
                                     entry.get('test_name', ''))))
            if not seen:
                listed.append(dict(base, result=unseen, test=''))
    return {
        'commit': commit or '',
        'dirty': bool(dirty),
        'at': at or now_iso(),
        'runner': runner,
        'machine': machine or local_machine(),
        'hostname': platform.node() if hostname is None else hostname,
        'fingerprint': dict(fingerprint),
        'rules': rules,
        'proofs': listed,
    }


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
    """True when two sections saw the same thing over the same fingerprint.

    `commit`, `dirty` and `at` say when a run happened, not what it saw, and
    `hostname` is kept and never compared, so a run that repeats the last
    one on the same machine leaves the file as it was. A run on another
    `machine` replaces the section.
    """
    def seen(section):
        return {key: value for key, value in (section or {}).items()
                if key not in ('commit', 'dirty', 'at', 'hostname')}
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
                  rule_ids):
    """`data` with `platforms[os_name]` replaced and removed rules dropped.

    A section that repeats the one already there over the same fingerprint
    is left as it was, `at` and `commit` included. Returns a new dict.
    """
    merged = json.loads(json.dumps(data)) if data else empty_file(
        source, feature, spec_path)
    merged['spec'] = spec_path or merged.get('spec') or ''
    platforms = merged.get('platforms')
    if not isinstance(platforms, dict):
        platforms = {}
    kept = platforms.get(os_name)
    if not (isinstance(kept, dict) and _same_observation(kept, section)):
        platforms[os_name] = section
    merged['platforms'] = platforms
    return drop_removed_rules(merged, rule_ids)


def merge_audit(data, source, feature, spec_path, entries, mutation,
                mutation_ran, rule_ids):
    """`data` with `audit.rules[R]` replaced for each entry given.

    `audit.mutation` is replaced when mutation testing ran; a file with no
    `audit` yet gets one whose `mutation` is null otherwise. An entry that
    repeats the one there over the same three hashes keeps its `at` and
    `commit`, so reading a rule again finds nothing new to commit.
    """
    merged = json.loads(json.dumps(data)) if data else empty_file(
        source, feature, spec_path)
    audit = merged.get('audit')
    if not isinstance(audit, dict):
        audit = {'mutation': None, 'rules': {}}
    rules = audit.get('rules')
    if not isinstance(rules, dict):
        rules = {}
    for rule_id, entry in (entries or {}).items():
        kept = rules.get(rule_id)
        if isinstance(kept, dict) and _same_audit(kept, entry):
            continue
        rules[rule_id] = entry
    audit['rules'] = rules
    if mutation_ran:
        kept = audit.get('mutation')
        if not (isinstance(kept, dict)
                and (kept.get('engine'), kept.get('score'))
                == ((mutation or {}).get('engine'),
                    (mutation or {}).get('score'))):
            audit['mutation'] = mutation
    elif 'mutation' not in audit:
        audit['mutation'] = None
    merged['audit'] = audit
    return drop_removed_rules(merged, rule_ids)


def audit_entry(rule, found, commit, at=None):
    """The `audit.rules` entry for one rule the audit read.

    `rule` is the payload's rule entry, whose three hashes key the entry, and
    `found` what the AI audit answered for it: its `verdict` (`strong`,
    `weak` or `undecided`), its `findings`, the `model` that answered, the
    sha256 of the `criteria` it was sent, and any `notes`, the sentences
    about a proof longer than the standard or holding two cases, which enter
    no hash and are written only when there are some.
    """
    entry = {'rule_hash': rule.get('rule_hash'),
             'proof_hash': rule.get('proof_hash'),
             'test_hash': rule.get('test_hash'),
             'verdict': found.get('verdict'),
             'findings': [str(line) for line in found.get('findings') or ()],
             'model': found.get('model') or 'unknown',
             'criteria': found.get('criteria') or '',
             'at': at or now_iso(), 'commit': commit or ''}
    notes = [str(line) for line in found.get('notes') or ()]
    if notes:
        entry['notes'] = notes
    return entry


def _same_audit(one, other):
    keys = ('rule_hash', 'proof_hash', 'test_hash', 'verdict', 'findings',
            'model', 'criteria')
    return all(one.get(key) == other.get(key) for key in keys)


def write_could_not_run(project_root, failures, cleared):
    """Record the rules whose model call failed, for the strong cell to name.

    `failures` is `{(feature, rule): {rule_hash, proof_hash, test_hash,
    why}}` from this audit, and `cleared` the `(feature, rule)` pairs it
    read. What an earlier audit left there stays for every other rule. The
    file sits under `.purlin/runtime/`, which is never committed: nothing
    about a rule the model could not read goes into the evidence.
    """
    table = reader.could_not_run(project_root)
    for feature, rule in cleared or ():
        (table.get(feature) or {}).pop(rule, None)
    for (feature, rule), entry in (failures or {}).items():
        table.setdefault(feature, {})[rule] = dict(entry)
    table = {feature: rules for feature, rules in table.items() if rules}
    path = full_path(project_root, reader.COULD_NOT_RUN_PATH)
    if not table:
        try:
            os.remove(path)
        except OSError:
            pass
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(dump(table))


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
    """Write one file when its text changed. Its project-relative path."""
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
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return rel


def write_section(project_root, source, feature, info, os_name, section):
    """Merge one section into the feature's file on disk. The path."""
    merged = merge_section(read_file(project_root, source, feature), source,
                           feature, info.get('spec_path', ''), os_name,
                           section, info.get('rule_order') or ())
    return write_file(project_root, source, feature, merged)


def write_audit(project_root, source, feature, info, entries, mutation,
                mutation_ran):
    """Merge one audit's entries into the feature's file on disk. The path."""
    merged = merge_audit(read_file(project_root, source, feature), source,
                         feature, info.get('spec_path', ''), entries,
                         mutation, mutation_ran, info.get('rule_order') or ())
    return write_file(project_root, source, feature, merged)


def merge_for_host(os_name, rule_ids_by_feature):
    """The merge a remote runner's commit applies to each file at its parent.

    The API commit is retried when the branch moved, and on each attempt the
    file the parent holds is read again. This returns the function that puts
    this runner's own section into it, so two runners on two operating
    systems do not overwrite each other. `rule_ids_by_feature` is the spec's
    rules per feature, read on the runner.
    """
    def merge(rel, local_text, parent_text):
        try:
            mine = json.loads(local_text)
        except ValueError:
            return local_text
        feature = mine.get('feature') or os.path.basename(rel)[:-len('.json')]
        section = (mine.get('platforms') or {}).get(os_name)
        if not isinstance(section, dict):
            return local_text
        parent = None
        if parent_text:
            try:
                parent = parse(json.loads(parent_text), mine.get('source'))
            except ValueError:
                parent = None
        merged = merge_section(parent, mine.get('source'), feature,
                               mine.get('spec'), os_name, section,
                               rule_ids_by_feature.get(feature) or ())
        return dump(merged)
    return merge


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


# ---------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------

def counts(section):
    """`(rules, passed, failing, no_test)` for one section.

    A rule is `passed` only where the section reads it so, which is only
    when every test tied to it ran and passed. `No test` is every rule that
    is neither `passed` nor `failed`, so a rule waiting on another operating
    system, or on a test that did not run, is counted there rather than
    dropped from the row.
    """
    words = list(((section or {}).get('rules') or {}).values())
    passed = sum(1 for word in words if word == 'passed')
    failing = sum(1 for word in words if word == 'failed')
    return len(words), passed, failing, len(words) - passed - failing


def newest_sections(project_root):
    """`{feature: entry}`, the newest section of each feature in either source."""
    rows = {}
    for feature in reader.feature_names(project_root):
        found = reader.newest(reader.load(project_root, feature))
        if found is not None:
            rows[feature] = found
    return rows


def render_table(rows):
    """`.purlin/tests.md` from `{feature: newest section entry}`."""
    newest = None
    for entry in rows.values():
        at = str(entry['section'].get('at') or '')
        if newest is None or at > str(newest['section'].get('at') or ''):
            newest = entry
    commit = str(((newest or {}).get('section') or {}).get('commit') or '')
    lines = [TABLE_HEADING % (commit[:7] or 'an unknown commit'), '']
    if not rows:
        lines.extend([TABLE_EMPTY, '', TABLE_NOTE])
        return '\n'.join(lines) + '\n'
    lines.append('| %s |' % ' | '.join(TABLE_COLUMNS))
    lines.append('|%s|' % '|'.join('---' for _ in TABLE_COLUMNS))
    for feature in sorted(rows):
        entry = rows[feature]
        section = entry['section']
        rules, passed, failing, no_test = counts(section)
        last = ' · '.join([str(section.get('commit') or '')[:7] or '-',
                           str(section.get('at') or '-'),
                           reader.os_word(entry['os']), entry['source']])
        lines.append('| %s | %d | %d | %d | %d | %s |'
                     % (feature, rules, passed, failing, no_test, last))
    lines.extend(['', TABLE_NOTE])
    return '\n'.join(lines) + '\n'


def write_table(project_root):
    """Render the table from every evidence file on disk. Its path."""
    path = full_path(project_root, TABLE_PATH)
    text = render_table(newest_sections(project_root))
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            if handle.read() == text:
                return TABLE_PATH
    except (IOError, OSError, UnicodeDecodeError):
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return TABLE_PATH


def written_line(paths, source='local'):
    """The one line naming what a run wrote: the file, or the folder and a count."""
    paths = [path for path in paths or ()]
    if len(paths) == 1:
        return WRITTEN_ONE % paths[0]
    return WRITTEN_MANY % (EVIDENCE_DIR, source, len(paths))


# ---------------------------------------------------------------------------
# The person's own two commits
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
    """Commit the `local/` files, the table and what the run removed.

    The second of a run's two commits. Its subject names `work_sha`, the
    commit `commit_work` made, or HEAD when it made none. The commit is the
    person's own, under their own identity, and nothing here pushes. A file
    a run removed from `ci/` because its feature has no spec is committed as
    that removal; nothing else under `ci/` is staged, because that folder is
    the runner's. Prints `Evidence committed.`, `Evidence unchanged.`, or
    that there is no git repository to commit to.
    """
    print(commit_paths(
        project_root,
        ['%s/local' % EVIDENCE_DIR, TABLE_PATH] + list(removed or ()),
        COMMIT_SUBJECT % (str(work_sha or '')[:7] or 'an unknown commit')))


def commit_paths(project_root, paths, message):
    """Commit `paths` under the person's identity. The line to print."""
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
