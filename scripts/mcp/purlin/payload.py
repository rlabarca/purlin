"""The structured project payload, schema 9.

One reader assembles specs, evidence and signatures into the level and the
cells of every rule, and every surface renders that: the
status table, the dashboard, the gate check and the drift report. A surface
that parsed the rendered table would be coupled to a layout; this is the shape
they all read instead.

    {
      "schema_version": 9,
      "generated_at": "2026-09-13T12:00:00Z",
      "generated_by": "sync_status",
      "project": "purlin",
      "version": "<the VERSION file>",
      "commit": "<sha>",
      "dirty": false,
      "gate": {"gate": "strong", "min_strength": 70, "trust": "local", ...},
      "summary": {"rules": 8, "features": 4, "met": 1, "failing": 0,
                  "partial": 1, "untested": 2, "passed": 4, "strong": 1,
                  "signed": 1, "stale": 1, "held": 1, "manual": 0,
                  "unsettled": 1, "not_audited": 0, "signable": 2},
      "features": [
        {"name": "login", "category": "auth", "spec_path": "specs/auth/login.md",
         "is_anchor": false, "requires": [], "source": null, "pinned": null,
         "rollup": {..., "proofs": 6, "proofs_without_test": 1,
                    "proofs_without_test_ids": ["PROOF-4"]},
         "test_strength": 86,
         "current": true,
         "evidence": {"local": {"path": ".purlin/evidence/local/login.json",
                                "committed": true,
                                "platforms": {"macos": {"commit": ..., "at": ...,
                                                        "current": true}}},
                      "ci": null},
         "signatures": [...],
         "rules": [
           {"id": "RULE-1", "feature": "login", "label": "own",
            "text": "...", "level": "signed", "level_marked": null,
            "audit_hash": "<sha256>",
            "bucket": "signed", "meets_gate": true, "signable": false,
            "blocked_by": null, "flags": {...},
            "cells": {"passed": {...}, "strong": {...}, "signed": {...}},
            "proofs": [{"id": "PROOF-1", "manual": false, "env": null,
                        "text": "...", "tests": [...]}]}
         ]}
      ],
      "review_list": [{"feature": ..., "owner": ..., "rule": ..., "level": ...,
                       "cell": "strong", "kind": "unsettled",
                       "why": ["unsettled"]}],
      "sign_list": [{"feature": ..., "owner": ..., "rule": ..., "level": ...,
                     "cell": "signed", "kind": "stale", "why": ["stale"]}],
      "evidence": {"login": {"local": {"macos": {"commit": ..., "at": ...,
                                                 "result": "pass",
                                                 "current": true,
                                                 "path": ...}}}},
      "tag": {"name": "signed/1.4.0", "commit": "<sha>"},
      "remote_url": "https://github.com/acme/ledger.git",
      "warnings": ["..."]
    }

A cell above the project's gate is absent, not empty: a `passed` project
carries one cell per rule, a `signed` project carries three.

`write_report_data` writes the payload to `.purlin/report-data.js` as
`const PURLIN_DATA = {...};`, which is gitignored and is what the local
dashboard page loads.
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys

_MCP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from config_engine import resolve_config
from purlin import (PURLIN_VERSION,
                    evidence as evidence_module,
                    fingerprint as fingerprint_module,
                    gate as gate_module,
                    signatures as signatures_module,
                    specs as specs_module, states)

SCHEMA_VERSION = 9
REPORT_DATA_PATH = os.path.join('.purlin', 'report-data.js')
_PREFIX = 'const PURLIN_DATA = '


def now_iso():
    """The current time, ISO 8601 UTC with `Z`, the one format used anywhere."""
    return datetime.datetime.now(
        datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def build_payload(project_root, generated_by='sync_status', config=None):
    """The whole payload for a project root."""
    config = resolve_config(project_root) if config is None else config
    cfg = gate_module.resolve_gate(config)
    warnings = list(cfg.warnings)

    features = specs_module.scan_specs(project_root)
    tag_warning = specs_module.unknown_tag_warning(features)
    if tag_warning:
        warnings.append(tag_warning)
    for name in sorted(features):
        unnumbered = features[name].get('unnumbered_lines') or []
        if unnumbered:
            warnings.append(
                'WARNING: %d lines under ## Rules in %s are not numbered; a '
                'rule is `- RULE-N: <text>`.'
                % (len(unnumbered), features[name]['spec_path']))

    # Every feature's evidence, checked against a fingerprint taken now. A
    # section decides a cell only while it is current, so this is read once
    # here rather than once per rule.
    evidence = _read_evidence(project_root, features, warnings)
    all_signatures = signatures_module.load_signatures(project_root, features)
    all_holds = signatures_module.load_holds(project_root, features)
    head = head_sha(project_root)

    blob_cache = {}
    counted_cache = {}
    feature_entries = []
    review_list = []
    sign_list = []
    rollups = {}
    # The project summary counts each rule once, under the feature that owns
    # it. A feature's own rollup counts what that feature must prove, which
    # includes the rules it requires and the global anchors', so summing the
    # feature rollups would count a global anchor's rules once per feature.
    own_results = {}

    for name in sorted(features):
        info = features[name]
        entry, rollup = _feature_entry(
            project_root, name, info, features, evidence, all_signatures,
            cfg, blob_cache, review_list, own_results, all_holds,
            counted_cache, sign_list)
        feature_entries.append(entry)
        rollups[name] = rollup

    summary = states.project_rollup(
        {'': states.feature_rollup(own_results, cfg.gate)}, cfg.gate)
    summary['features'] = len(features)
    # The project's proofs are each feature's own, counted once: a rule an
    # anchor declares is proved by every feature that requires it, and its
    # proofs belong to the anchor.
    summary.update(proof_counts(
        [rule for entry in feature_entries for rule in entry['rules']
         if rule.get('label') == 'own']))

    payload = {
        'schema_version': SCHEMA_VERSION,
        'generated_at': now_iso(),
        'generated_by': generated_by,
        'project': config.get('project_name') or os.path.basename(
            os.path.abspath(project_root)),
        'version': PURLIN_VERSION,
        'commit': head,
        'dirty': _is_dirty(project_root),
        'gate': cfg.as_dict(),
        'summary': summary,
        'features': feature_entries,
        'review_list': _sorted_list(review_list),
        'sign_list': _sorted_list(sign_list),
        'evidence': _evidence_map(evidence),
        'tag': signed_tag(project_root, head),
        'remote_url': _remote_url(project_root),
        'warnings': warnings,
    }
    return payload


def proof_counts(rule_entries):
    """`{proofs, proofs_without_test, proofs_without_test_ids}` over some rules.

    A proof with no tagged test is the gap between what a spec claims to
    observe and what anything actually runs, so the count is carried beside
    the proof total rather than worked out again by each surface. Each proof
    is counted once under the rule that writes it, so a rule an anchor
    declares is not counted twice in the one row that proves it.

    A `@manual` proof is left out of the count: it declares that no test is
    written for it, so naming it as a gap would report the spec's own answer
    as a fault. Which tests back a proof is read from the evidence, so a
    project whose tests have never run reads every proof as one without a
    test, which is what it is until something runs.
    """
    seen = set()
    total = 0
    without = []
    for rule in rule_entries or ():
        for proof in rule.get('proofs') or ():
            key = (rule.get('feature'), proof.get('id'))
            if key in seen:
                continue
            seen.add(key)
            total += 1
            if not proof.get('tests') and not proof.get('manual'):
                without.append(proof.get('id'))
    return {'proofs': total, 'proofs_without_test': len(without),
            'proofs_without_test_ids': without}


# The one order both lists are read in: the rules whose level asks the most
# first, then the feature that owns them, then the rule number.
_LEVEL_ORDER = {'signed': 0, 'strong': 1, 'passed': 2}


def _sorted_list(entries):
    def key(entry):
        return (_LEVEL_ORDER.get(entry['level'], 3), entry['owner'],
                _rule_number(entry['rule']))
    return sorted(entries, key=key)


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def _feature_entry(project_root, name, info, features, evidence,
                   all_signatures, cfg, blob_cache, review_list,
                   own_results=None, all_holds=None, counted_cache=None,
                   sign_list=None):
    own = evidence.get(name) or _no_evidence(name)
    mutation = evidence_module.mutation(own['loaded'])
    test_strength = mutation.get('score') if mutation else None

    rule_entries = []
    rule_results = {}
    for owner, rule_id, label in specs_module.rule_refs(name, features):
        owner_info = features.get(owner)
        if not owner_info:
            continue
        owner_evidence = evidence.get(owner) or _no_evidence(owner)
        owner_mutation = evidence_module.mutation(owner_evidence['loaded'])
        result = _rule_entry(
            project_root, owner, owner_info, rule_id, label, owner_evidence,
            all_signatures, cfg, blob_cache,
            owner_mutation.get('score') if owner_mutation else None,
            all_holds, counted_cache)
        rule_entries.append(result)
        summary = {'bucket': result['bucket'], 'flags': result['flags'],
                   'meets_gate': result['meets_gate'],
                   'signable': result['signable'], 'level': result['level']}
        rule_results[(owner, rule_id)] = summary
        if label == 'own' and own_results is not None:
            own_results[(owner, rule_id)] = summary
        # Each list names a rule once, under its owner, as the summary counts
        # it; a required or global rule is read where it is written, not once
        # per feature that proves it.
        if label != 'own':
            continue
        entry = _review_entry(name, owner, result, cfg)
        if entry is not None:
            review_list.append(entry)
        entry = _sign_entry(name, owner, result, cfg)
        if entry is not None and sign_list is not None:
            sign_list.append(entry)

    rollup = states.feature_rollup(rule_results, cfg.gate,
                                   test_strength=test_strength)
    rollup.update(proof_counts(rule_entries))

    entry = {
        'name': name,
        'category': info.get('category', ''),
        'spec_path': info.get('spec_path', ''),
        'is_anchor': bool(info.get('is_anchor')),
        'is_global': bool(info.get('is_global')),
        'description': info.get('description'),
        'requires': info.get('requires', []),
        'scope': info.get('scope', []),
        'source': info.get('source'),
        'source_path': info.get('source_path'),
        'pinned': info.get('pinned'),
        'rollup': rollup,
        'test_strength': test_strength,
        'current': own['current'],
        'evidence': own['summary'],
        'signatures': sorted(
            signature['path']
            for key, entries in all_signatures.items() if key[0] == name
            for signature in entries),
        'rules': rule_entries,
    }
    return entry, rollup


# ---------------------------------------------------------------------------
# The evidence
# ---------------------------------------------------------------------------

def _read_evidence(project_root, features, warnings):
    """`{feature: {loaded, sections, current, summary}}` for every spec.

    `sections` is every section of the feature's two files, each checked
    against a fingerprint taken now; `current` says the newest of them is
    current; `summary` is the `features[].evidence` object. A file the
    reader ignores adds its warning once.
    """
    markers = fingerprint_module.marker_index(project_root)
    uncommitted = _uncommitted_evidence(project_root)
    out = {}
    for name in sorted(features):
        loaded = evidence_module.load(project_root, name)
        for warning in loaded['warnings']:
            if warning not in warnings:
                warnings.append(warning)
        sections = []
        if any(loaded['files'].values()):
            now = fingerprint_module.fingerprint(project_root, name, features,
                                                 markers)
            sections = evidence_module.checked_sections(loaded, now)
        newest = None
        for entry in sections:
            if newest is None or str(entry['section'].get('at') or '') > str(
                    newest['section'].get('at') or ''):
                newest = entry
        summary = {}
        for source in evidence_module.SOURCES:
            if loaded['files'].get(source) is None:
                summary[source] = None
                continue
            path = loaded['paths'][source]
            summary[source] = {
                'path': path,
                'committed': path not in uncommitted,
                'platforms': {
                    entry['os']: {'commit': entry['section'].get('commit'),
                                  'at': entry['section'].get('at'),
                                  'current': entry['current']}
                    for entry in sections if entry['source'] == source},
            }
        out[name] = {'loaded': loaded, 'sections': sections,
                     'current': bool(newest and newest['current']),
                     'summary': summary}
    return out


def _no_evidence(name):
    """What `_read_evidence` answers for a feature that has no spec of its own."""
    return {'loaded': {'feature': name, 'files': {'local': None, 'ci': None},
                       'paths': {}, 'warnings': []},
            'sections': [], 'current': False,
            'summary': {'local': None, 'ci': None}}


def _uncommitted_evidence(project_root):
    """The evidence paths whose file is not tracked or differs from HEAD.

    One `git status` answers every file: a path it lists is not committed as
    it stands, and a path it does not list is tracked and matches HEAD.
    Outside a repository nothing is committed, so every path counts as not.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain', '--untracked-files=all', '--',
             evidence_module.EVIDENCE_DIR],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return _AllPaths()
    if result.returncode != 0:
        return _AllPaths()
    listed = set()
    for line in result.stdout.splitlines():
        if len(line) > 3:
            listed.add(line[3:].strip('"').split(' -> ')[-1])
    return listed


class _AllPaths(object):
    """A set that holds every path: outside git, nothing is committed."""

    def __contains__(self, _path):
        return True


def _evidence_map(evidence):
    """`{feature: {source: {os: {commit, at, result, current, path}}}}`.

    `result` is `fail` where any proof the section observed failed and `pass`
    otherwise, so two sections with nothing but their operating system to
    tell them apart still say which one failed.
    """
    out = {}
    for name in sorted(evidence):
        for entry in evidence[name]['sections']:
            results = evidence_module.proof_results(entry['section'])
            out.setdefault(name, {}).setdefault(entry['source'], {})[
                entry['os']] = {
                    'commit': entry['section'].get('commit'),
                    'at': entry['section'].get('at'),
                    'result': 'fail' if 'fail' in results.values() else 'pass',
                    'current': entry['current'],
                    'path': entry['path'],
                }
    return out


def _review_entry(feature, owner, rule, cfg):
    """One Review row for a rule the machine could not settle, or None.

    The Review list holds exactly the rules whose strong cell reads `manual
    test`, `unsettled` or `held`: the three words that name work only a
    person can do. `not audited` is not among them, because what that rule
    waits for is `purlin:audit`, not a reader. The list exists at `strong`
    and above.
    """
    if cfg.gate == 'passed':
        return None
    word = ((rule.get('cells') or {}).get('strong') or {}).get('word')
    if word not in states.REVIEW_WORDS:
        return None
    return {'feature': feature, 'owner': owner, 'rule': rule['id'],
            'level': rule['level'], 'cell': 'strong', 'kind': word,
            'why': [word]}


def _sign_entry(feature, owner, rule, cfg):
    """One Sign row for a signable rule, or None.

    A rule is signable when its level is `signed`, its passed and strong
    cells are met and it does not have a counting signature, so the Sign
    list is the rules a signer can act on now. It exists at the gate
    `signed`.
    """
    if cfg.gate != 'signed' or not rule.get('signable'):
        return None
    word = ((rule.get('cells') or {}).get('signed') or {}).get('word')
    return {'feature': feature, 'owner': owner, 'rule': rule['id'],
            'level': rule['level'], 'cell': 'signed', 'kind': word,
            'why': [word]}


def _rule_entry(project_root, owner, owner_info, rule_id, label,
                owner_evidence, all_signatures, cfg, blob_cache,
                test_strength=None, all_holds=None, counted_cache=None):
    text = owner_info['rules'].get(rule_id, '')
    meta = owner_info.get('rule_meta', {}).get(rule_id, {})
    proof_ids = owner_info.get('proofs_by_rule', {}).get(rule_id, [])
    sections = owner_evidence['sections']

    proof_dicts = []
    for proof_id in proof_ids:
        proof = owner_info['proofs'][proof_id]
        proof_dicts.append({
            'id': proof_id,
            'manual': proof['manual'],
            'env': proof['env'],
            'text': proof['text'],
            'tests': [{'file': f, 'name': n}
                      for f, n in _backing_tests(sections, proof_id)],
        })

    rule_hash = specs_module.rule_text_hash(text)
    proof_hash = specs_module.proof_text_hash(
        '\n'.join('%s %s' % (p['id'], p['text']) for p in proof_dicts))
    test_hash = _test_hash(project_root, proof_dicts, blob_cache)
    test_hash_kind = signatures_module.test_hash_kind(proof_dicts)
    # The tag as the spec wrote it, where it is one of the three words. A
    # rule with no tag, or with a value that is not a level, is unmarked.
    level_marked = meta.get('level')
    if level_marked not in gate_module.GATES:
        level_marked = None

    signatures = [_counted(project_root, signature, cfg, counted_cache)
                  for signature in all_signatures.get((owner, rule_id), [])]

    # The audit entry for this rule's current hashes, in either source. An
    # entry taken over other text, another proof or another test does not
    # answer, which is what keeps the strong cell honest.
    audit = evidence_module.audit_entry(owner_evidence['loaded'], rule_id,
                                        rule_hash, proof_hash, test_hash)
    audit_hash = signatures_module.audit_hash(audit, test_strength)
    result = states.rule_cells({
        # What the signature locks beside the triple: what the audit found,
        # so a re-audit that finds something different stales it.
        'audit_hash': audit_hash,
        'proofs': proof_dicts,
        'sections': sections,
        # Whether the feature's evidence holds any audit at all. With none,
        # nothing measured how good the tests are and the strong cell says
        # so rather than passing the rule on nothing at all.
        'audited': evidence_module.audited(owner_evidence['loaded']),
        'signatures': signatures,
        'holds': (all_holds or {}).get((owner, rule_id), []),
        'rule_hash': rule_hash,
        'proof_hash': proof_hash,
        'test_hash': test_hash,
        'level_marked': level_marked,
        'audit': audit,
        # The feature's strength stands for every rule in it: a break engine
        # measures a scope, not one rule, and the strong cell compares what
        # was measured rather than assuming nothing was.
        'test_strength': test_strength,
    }, cfg)

    return {
        'id': rule_id,
        'feature': owner,
        'label': label,
        'text': text,
        'level': result['level'],
        'level_marked': level_marked,
        'rule_hash': rule_hash,
        'proof_hash': proof_hash,
        'test_hash': test_hash,
        'test_hash_kind': test_hash_kind,
        'audit_hash': audit_hash,
        'cells': result['cells'],
        'bucket': result['bucket'],
        'meets_gate': result['meets_gate'],
        'signable': result['signable'],
        'blocked_by': result['blocked_by'],
        'flags': result['flags'],
        'proofs': proof_dicts,
    }


def _counted(project_root, signature, cfg, cache):
    """One signature plus whether it counts under the gate, and why not.

    Reading git for each signature is the expensive part, and the answer is a
    property of the committed file rather than of the rule asking, so it is
    cached on the path.
    """
    cache = cache if cache is not None else {}
    key = (signature.get('path'), cfg.gate)
    if key not in cache:
        ok, reason = signatures_module.counts(project_root, signature,
                                              cfg.gate)
        cache[key] = (ok, reason, signatures_module.commit_date(
            project_root, signature.get('path')))
    ok, reason, committed_at = cache[key]
    entry = dict(signature)
    entry['counts'] = ok
    entry['count_reason'] = reason
    entry['committed_at'] = committed_at
    return entry


def _backing_tests(sections, proof_id):
    """`[(test_file, test_name), ...]` backing one proof, the same on every machine.

    The tests the current sections list come first, every operating system
    and both sources together, because a section is the one list every
    checkout reads alike. Where no current section lists one, every section
    answers, so a code change that leaves a section out of date does not
    change which tests back the proof: the signature binds the tests, and a
    code change alone stales nothing.
    """
    for wanted in (True, False):
        observed = []
        for entry in sections or ():
            if wanted and not entry.get('current'):
                continue
            for pair in evidence_module.proof_tests(entry['section'],
                                                    proof_id):
                if pair not in observed:
                    observed.append(pair)
        if observed:
            return observed
    return []


def _test_hash(project_root, proof_dicts, blob_cache):
    """The T of the triple: the blob ids of the test files, with their names.

    Reading the file's blob id rather than one function's body is coarse on
    purpose: a test file is the unit version control tracks, and a hash over it
    stales a signature whenever the test that backs a rule changes, which is
    the behaviour the signature is meant to have. `signatures.test_hash_kind`
    names what was read beside the hash, so a signature says so on its face.
    Which tests back each proof is `_backing_tests`'s answer, read from the
    evidence so it does not depend on the machine.
    """
    parts = []
    for proof in proof_dicts:
        for test in proof['tests']:
            path = test['file']
            if path not in blob_cache:
                blob_cache[path] = fingerprint_module.blob_id(
                    project_root, path)
            parts.append('%s %s %s' % (path, test['name'], blob_cache[path]))
    digest = hashlib.sha256()
    digest.update('\n'.join(sorted(parts)).encode('utf-8'))
    return digest.hexdigest()


def signed_tag(project_root, head=None):
    """`{name, commit}` for the `signed/*` tag on HEAD, or None where there is none.

    The tag is the marker of proven code, so a surface that shows one commit's
    standing shows whether that commit carries it. Only a tag pointing at HEAD
    counts: a tag two commits back says nothing about this code. Where several
    point at the same commit the newest version wins, read as numbers where
    the name is numeric and as text where it is not, so `signed/1.10.0` sorts
    after `signed/1.9.0`.
    """
    try:
        result = subprocess.run(
            ['git', 'tag', '--points-at', 'HEAD', 'signed/*'],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    names = [line.strip() for line in result.stdout.splitlines()
             if line.strip()]
    if not names:
        return None
    names.sort(key=_tag_order)
    return {'name': names[-1], 'commit': head or head_sha_of(project_root)}


def _tag_order(name):
    """A sort key for a tag name: its numeric parts first, then the name."""
    parts = str(name).split('/', 1)[-1].replace('-', '.').split('.')
    numbers = []
    for part in parts:
        if not part.isdigit():
            break
        numbers.append(int(part))
    return (len(numbers) > 0, numbers, str(name))


def head_sha_of(project_root):
    """The sha at HEAD, read once more where the caller had none to hand."""
    return head_sha(project_root)


def head_sha(project_root):
    """The full sha at HEAD, or None outside a git checkout."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, cwd=project_root, timeout=10)
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _remote_url(project_root):
    """The `origin` remote, or `None` when the project has no remote.

    The dashboard turns this into a link to each file on the git host. A
    project with no remote, or a checkout where git cannot answer, gets
    plain text instead of a broken link.
    """
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _is_dirty(project_root):
    """True when the working tree differs from the commit the payload names.

    `.purlin/` is excluded. What Purlin writes about a project is not a change
    to the project, and counting it would make the answer depend on whether
    the report had been written yet: two builds of one unchanged tree would
    then disagree.
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True, cwd=project_root, timeout=15)
    except (subprocess.SubprocessError, OSError):
        return False
    if result.returncode != 0:
        return False
    for line in result.stdout.splitlines():
        if len(line) > 3 and not line[3:].strip('"').startswith('.purlin/'):
            return True
    return False


# ---------------------------------------------------------------------------
# The dashboard's data file
# ---------------------------------------------------------------------------

def report_data_path(project_root):
    return os.path.join(project_root, REPORT_DATA_PATH)


def read_report_payload(project_root):
    """The payload the last write left in `.purlin/report-data.js`, or None."""
    path = report_data_path(project_root)
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            content = handle.read()
    except (IOError, OSError, UnicodeDecodeError):
        return None
    if not content.startswith(_PREFIX):
        return None
    try:
        return json.loads(content[len(_PREFIX):].rstrip().rstrip(';'))
    except ValueError:
        return None


def write_report_data(project_root, payload, only_if_changed=False):
    """Write the payload as `const PURLIN_DATA = {...};`. Returns the path.

    With `only_if_changed`, a payload that differs from the file only by its
    `generated_at` stamp touches the file instead of rewriting it: the file is
    gitignored, but a background refresh that rewrote it on every tool call
    would still churn the disk and every watcher on it.
    """
    path = report_data_path(project_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = json.dumps(payload, indent=2, sort_keys=True, default=str)
    text = _PREFIX + body + ';\n'

    if only_if_changed:
        previous = read_report_payload(project_root)
        if previous is not None and _same(previous, payload):
            os.utime(path, None)
            return path

    tmp_path = path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    os.replace(tmp_path, path)
    return path


_VOLATILE = ('generated_at', 'generated_by')


def _same(left, right):
    left = {k: v for k, v in left.items() if k not in _VOLATILE}
    right = {k: v for k, v in right.items() if k not in _VOLATILE}
    return json.dumps(left, sort_keys=True, default=str) == json.dumps(
        right, sort_keys=True, default=str)
