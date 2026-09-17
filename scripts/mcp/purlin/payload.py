"""The structured project payload, schema 5.

One reader assembles specs, runtime proofs, records and signatures into the
spec status and the cells of every rule, and every surface renders that: the
status table, the dashboard, the gate check and the drift report. A surface
that parsed the rendered table would be coupled to a layout; this is the shape
they all read instead.

    {
      "schema_version": 5,
      "generated_at": "2026-09-13T12:00:00Z",
      "generated_by": "sync_status",
      "project": "purlin",
      "version": "<the VERSION file>",
      "commit": "<sha>",
      "dirty": false,
      "gate": {"gate": "strong", "min_strength": 70, "sign_at": null, ...},
      "summary": {"rules": 8, "features": 4, "met": 1, "failing": 0,
                  "untested": 2, "passed": 4, "strong": 1, "signed": 1,
                  "stale": 1, "held": 1, "manual": 0, "audit": 1},
      "features": [
        {"name": "login", "category": "auth", "spec_path": "specs/auth/login.md",
         "is_anchor": false, "requires": [], "source": null, "pinned": null,
         "rollup": {...}, "test_strength": 86,
         "latest_record": {"path": ..., "label": "ci", "timestamp": ..., "os": null},
         "signatures": [...],
         "rules": [
           {"id": "RULE-1", "feature": "login", "label": "own",
            "text": "...", "risk": "low", "origin": "eng", "criterion": null,
            "spec": "ready", "bucket": "signed", "meets_gate": true,
            "blocked_by": null, "flags": {...},
            "cells": {"passed": {...}, "strong": {...}, "signed": {...}},
            "proofs": [{"id": "PROOF-1", "tier": "unit", "env": null,
                        "text": "...", "findings": [], "tests": [...]}]}
         ]}
      ],
      "review_list": [{"feature": ..., "owner": ..., "rule": ..., "risk": ...,
                       "cell": "signed", "why": ["stale"]}],
      "records": {"login": {"": {..., "label": "ci", "result": "pass"}}},
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
from purlin import (PURLIN_VERSION, checks,
                    gate as gate_module, proofs as proofs_module,
                    records as records_module,
                    signatures as signatures_module,
                    specs as specs_module, states)

SCHEMA_VERSION = 5
REPORT_DATA_PATH = os.path.join('.purlin', 'report-data.js')
BRIEFS_DIR = os.path.join('.purlin', 'briefs')
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

    runtime_proofs = proofs_module.load_proofs(project_root)
    all_records = records_module.load_records(project_root)
    all_signatures = signatures_module.load_signatures(project_root, features)
    all_holds = signatures_module.load_holds(project_root, features)
    head = records_module.head_sha(project_root)

    blob_cache = {}
    scope_cache = {}
    counted_cache = {}
    branch = (records_module.default_branch(project_root)
              if cfg.gate == 'signed' and all_signatures else None)
    feature_entries = []
    review_list = []
    rollups = {}
    # The project summary counts each rule once, under the feature that owns
    # it. A feature's own rollup counts what that feature must prove, which
    # includes the rules it requires and the global anchors', so summing the
    # feature rollups would count a global anchor's rules once per feature.
    own_results = {}

    for name in sorted(features):
        info = features[name]
        entry, rollup = _feature_entry(
            project_root, name, info, features, runtime_proofs, all_records,
            all_signatures, cfg, head, blob_cache, scope_cache, review_list,
            own_results, all_holds, counted_cache, branch)
        feature_entries.append(entry)
        rollups[name] = rollup

    summary = states.project_rollup(
        {'': states.feature_rollup(own_results, cfg.gate)}, cfg.gate)
    summary['features'] = len(features)

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
        'review_list': _sorted_review_list(review_list),
        'records': {feature: {(os_name or ''): _with_result(record)
                              for os_name, record in by_os.items()}
                    for feature, by_os in all_records.items()},
        'warnings': warnings,
    }
    return payload


# The one order the review list is read in: the highest risk first, and within
# one risk the rules a person already wrote something about before the rest.
_RISK_ORDER = {'high': 0, 'medium': 1, 'low': 2}


def _sorted_review_list(entries):
    def key(entry):
        first = 0 if set(entry['why']) & {'stale', 'held'} else 1
        return (_RISK_ORDER.get(entry['risk'], 3), first, entry['owner'],
                _rule_number(entry['rule']))
    return sorted(entries, key=key)


def _rule_number(rule_id):
    digits = str(rule_id).rsplit('-', 1)[-1]
    return int(digits) if digits.isdigit() else 0


def _feature_entry(project_root, name, info, features, runtime_proofs,
                   all_records, all_signatures, cfg, head, blob_cache,
                   scope_cache, review_list, own_results=None, all_holds=None,
                   counted_cache=None, branch=None):
    counting = _counting(all_records, name, cfg)
    latest = _latest(all_records.get(name) or {})
    test_strength = latest.get('test_strength') if latest else None

    rule_entries = []
    rule_results = {}
    for owner, rule_id, label in specs_module.rule_refs(name, features):
        owner_info = features.get(owner)
        if not owner_info:
            continue
        result = _rule_entry(
            project_root, name, owner, owner_info, rule_id, label,
            runtime_proofs, counting, all_signatures, cfg, head,
            blob_cache, scope_cache, test_strength, all_holds,
            _counting(all_records, owner, cfg),
            _uncounted(all_records, owner, cfg), counted_cache, branch)
        rule_entries.append(result)
        summary = {'bucket': result['bucket'], 'flags': result['flags'],
                   'meets_gate': result['meets_gate'],
                   'risk': result['risk']}
        rule_results[(owner, rule_id)] = summary
        if label == 'own' and own_results is not None:
            own_results[(owner, rule_id)] = summary
        # The review list names each rule once, under its owner, as the
        # summary counts it; a required or global rule is read where it is
        # written, not once per feature that proves it.
        entry = _review_entry(name, owner, result, cfg)
        if label == 'own' and entry is not None:
            review_list.append(entry)

    rollup = states.feature_rollup(
        rule_results, cfg.gate,
        latest_record=_record_summary(latest),
        test_strength=test_strength)

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
        'source_globs': info.get('source_globs', []),
        'pinned': info.get('pinned'),
        'rollup': rollup,
        'test_strength': test_strength,
        'latest_record': _record_summary(latest),
        'signatures': sorted(
            signature['path']
            for key, entries in all_signatures.items() if key[0] == name
            for signature in entries),
        'rules': rule_entries,
    }
    return entry, rollup


# The closed set of words a review row carries, one per thing that put the
# rule in front of a person. The token is the blocking cell's own word, so a
# row says the same thing the cell does.
_WHY_AT_STRONG = ('manual test', 'manual audit', 'held')
_WHY_AT_SIGNED = ('unsigned', 'stale', 'held')


def _review_entry(feature, owner, rule, cfg):
    """One review row for a rule whose next step is a person, or None.

    The list holds exactly the rules blocked at the strong cell by a question
    the machine could not settle, and the rules blocked at the signed cell. A
    rule blocked at `spec` or `passed` is build work and stays on the board.
    """
    if cfg.gate == 'passed':
        return None
    blocked = rule.get('blocked_by')
    if blocked not in ('strong', 'signed'):
        return None
    cell = (rule.get('cells') or {}).get(blocked) or {}
    word = cell.get('word')
    allowed = _WHY_AT_STRONG if blocked == 'strong' else _WHY_AT_SIGNED
    if word not in allowed:
        return None
    return {'feature': feature, 'owner': owner, 'rule': rule['id'],
            'risk': rule['risk'], 'cell': blocked, 'why': [word]}


def _rule_entry(project_root, feature, owner, owner_info, rule_id, label,
                runtime_proofs, counting, all_signatures, cfg, head,
                blob_cache, scope_cache, test_strength=None, all_holds=None,
                owner_counting=None, uncounted=None, counted_cache=None,
                branch=None):
    text = owner_info['rules'].get(rule_id, '')
    meta = owner_info.get('rule_meta', {}).get(rule_id, {})
    proof_ids = owner_info.get('proofs_by_rule', {}).get(rule_id, [])
    entries = runtime_proofs.get(owner, [])
    local_status = {}
    for key, status in proofs_module.status_by_proof(entries).items():
        local_status[key[1]] = status

    proof_dicts = []
    proof_texts = []
    for proof_id in proof_ids:
        proof = owner_info['proofs'][proof_id]
        findings = checks.proof_findings(proof['text'], proof['tier'])
        proof_texts.append(proof['text'])
        proof_dicts.append({
            'id': proof_id,
            'tier': proof['tier'],
            'env': proof['env'],
            'text': proof['text'],
            'findings': findings,
            'tests': [{'file': f, 'name': n}
                      for f, n in _backing_tests(entries, owner_counting,
                                                 proof_id)],
        })
    rule_level = checks.rule_findings(proof_texts)
    for finding in rule_level:
        for proof in proof_dicts:
            proof['findings'] = list(proof['findings']) + [finding]

    rule_hash = specs_module.rule_text_hash(text)
    proof_hash = specs_module.proof_text_hash(
        '\n'.join('%s %s' % (p['id'], p['text']) for p in proof_dicts))
    test_hash = _test_hash(project_root, proof_dicts, blob_cache)
    test_hash_kind = signatures_module.test_hash_kind(proof_dicts)
    risk = meta.get('risk', specs_module.DEFAULT_RISK)
    design_hash = signatures_module.design_hash(
        owner_info, meta.get('origin', specs_module.DEFAULT_ORIGIN))
    scope_key = owner
    if scope_key not in scope_cache:
        scope_cache[scope_key] = specs_module.scope_tree(
            project_root, owner_info.get('scope', []))

    test_paths = sorted({test['file'] for proof in proof_dicts
                         for test in proof['tests'] if test.get('file')})
    signatures = [_counted(project_root, signature, cfg, test_paths,
                           counted_cache, branch)
                  for signature in all_signatures.get((owner, rule_id), [])]

    brief, brief_path = _read_brief(project_root, owner, rule_id, rule_hash,
                                    proof_hash, test_hash)
    result = states.rule_cells({
        'proofs': proof_dicts,
        'local_status': local_status,
        'records': counting,
        'uncounted': uncounted or {},
        'head': head,
        'scope_tree': scope_cache[scope_key],
        'signatures': signatures,
        'holds': (all_holds or {}).get((owner, rule_id), []),
        'rule_hash': rule_hash,
        'proof_hash': proof_hash,
        'test_hash': test_hash,
        'design_hash': design_hash,
        'risk': risk,
        'brief': brief,
        'brief_path': brief_path,
        # The feature's strength stands for every rule in it: a break engine
        # measures a scope, not one rule, and the strong cell compares what
        # was measured rather than assuming nothing was.
        'test_strength': test_strength,
        'mutation_engine_available': cfg.mutation_engine not in (None, 'none'),
    }, cfg)

    return {
        'id': rule_id,
        'feature': owner,
        'label': label,
        'text': text,
        'risk': risk,
        'origin': meta.get('origin', specs_module.DEFAULT_ORIGIN),
        'criterion': meta.get('criterion'),
        'rule_hash': rule_hash,
        'proof_hash': proof_hash,
        'test_hash': test_hash,
        'test_hash_kind': test_hash_kind,
        'design_hash': design_hash,
        'spec': result['spec'],
        'cells': result['cells'],
        'bucket': result['bucket'],
        'meets_gate': result['meets_gate'],
        'blocked_by': result['blocked_by'],
        'flags': result['flags'],
        'proofs': proof_dicts,
    }


def _counted(project_root, signature, cfg, test_paths, cache, branch):
    """One signature plus whether it counts under the gate, and why not.

    Reading git for each signature is the expensive part, and the answer is a
    property of the committed file rather than of the rule asking, so it is
    cached on the path and the tests it is compared against.
    """
    cache = cache if cache is not None else {}
    key = (signature.get('path'), cfg.gate, tuple(test_paths))
    if key not in cache:
        ok, reason = signatures_module.counts(
            project_root, signature, cfg.signers or [], test_paths, cfg.gate)
        if ok and cfg.gate == 'signed' and branch:
            if not signatures_module.is_ancestor(
                    project_root, signature.get('path'), branch):
                ok = False
                reason = 'the signing commit is not on %s' % branch
        cache[key] = (ok, reason)
    ok, reason = cache[key]
    entry = dict(signature)
    entry['counts'] = ok
    entry['count_reason'] = reason
    return entry


def _counting(all_records, feature, cfg):
    """`{os: record}`, the latest records of one feature that count under the gate."""
    return {os_name: record
            for os_name, record in (all_records.get(feature) or {}).items()
            if records_module.counts_under(cfg.gate, record.get('label'))}


def _uncounted(all_records, feature, cfg):
    """`{os: record}`, the latest records the gate does not read.

    The passed cell names them anyway. A developer's record under `strong` is
    not evidence, but "no test" would be a different and wrong answer, so the
    cell says whose record it found and why it does not count.
    """
    return {os_name: record
            for os_name, record in (all_records.get(feature) or {}).items()
            if not records_module.counts_under(cfg.gate, record.get('label'))}


def _backing_tests(runtime_entries, records, proof_id):
    """`[(test_file, test_name), ...]` backing one proof, the same on every machine.

    The tests a committed record observed for the proof come first, across every
    operating system's latest counting record, because a record is the one list
    every checkout reads alike. This machine's runtime proofs answer only for a
    proof no record has observed yet. Reading the runtime first made T depend on
    which tests this machine could run: a checkout with no `dotnet` ran no xUnit
    test, listed fewer tests, and read a current signature as stale.
    """
    observed = []
    for os_name in sorted(records or {}, key=lambda name: name or ''):
        for pair in proofs_module.tests_for(
                (records[os_name] or {}).get('proofs'), proof_id):
            if pair not in observed:
                observed.append(pair)
    return observed or proofs_module.tests_for(runtime_entries, proof_id)


def _test_hash(project_root, proof_dicts, blob_cache):
    """The T of the triple: the blob ids of the test files, with their names.

    Reading the file's blob id rather than one function's body is coarse on
    purpose: a test file is the unit version control tracks, and a hash over it
    stales a signature whenever the test that backs a rule changes, which is
    the behaviour the signature is meant to have. `signatures.test_hash_kind`
    names what was read beside the hash, so a signature says so on its face.
    Which tests back each proof is `_backing_tests`'s answer, read from the
    records so it does not depend on the machine.
    """
    parts = []
    for proof in proof_dicts:
        for test in proof['tests']:
            path = test['file']
            if path not in blob_cache:
                blob_cache[path] = specs_module._blob_id(project_root, path)
            parts.append('%s %s %s' % (path, test['name'], blob_cache[path]))
    digest = hashlib.sha256()
    digest.update('\n'.join(sorted(parts)).encode('utf-8'))
    return digest.hexdigest()


def _read_brief(project_root, feature, rule_id, rule_hash, proof_hash,
                test_hash):
    """`(brief, path)` for a rule's current text, or `(None, None)`.

    A brief is named for the triple it was built from, so a brief for text
    that has since changed is simply not found: that is what keeps the strong
    cell honest. CI commits them under `.purlin/briefs/<feature>/`, beside the
    records and under the same branch rule.
    """
    triple = signatures_module.triple_hash(rule_hash, proof_hash, test_hash)
    rel = '%s/%s/%s.%s.brief.json' % (
        BRIEFS_DIR.replace(os.sep, '/'), feature, rule_id, triple[:8])
    path = os.path.join(project_root, BRIEFS_DIR, feature,
                        '%s.%s.brief.json' % (rule_id, triple[:8]))
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            brief = json.load(handle)
    except (json.JSONDecodeError, IOError, OSError, UnicodeDecodeError):
        return None, None
    if not isinstance(brief, dict):
        return None, None
    return brief, rel


def _with_result(record):
    """One record plus `result`: `fail` where a proof it observed failed.

    A record's existence is not its result. The map is keyed by operating
    system, and a reader holding two records with nothing but their labels to
    tell them apart cannot see that the Linux job failed every proof while
    the Windows job passed them. `fail` where any observation reads `fail`,
    `pass` otherwise, which is how the run script reads a rule's own
    observations. The label is already on the record, read from git.
    """
    entry = dict(record)
    statuses = records_module.proof_statuses(record).values()
    entry['result'] = 'fail' if 'fail' in statuses else 'pass'
    return entry


def _latest(by_os):
    latest = None
    for record in by_os.values():
        if latest is None or str(record.get('timestamp', '')) > str(
                latest.get('timestamp', '')):
            latest = record
    return latest or {}


def _record_summary(record):
    if not record:
        return None
    return {
        'path': record.get('path'),
        'label': record.get('label'),
        'timestamp': record.get('timestamp'),
        'os': record.get('os') or (record.get('environment') or {}).get('os'),
        'commit': record.get('commit'),
        'test_strength': record.get('test_strength'),
    }


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
