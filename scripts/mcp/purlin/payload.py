"""The structured project payload, schema 4.

One reader assembles specs, runtime proofs, records and approvals into the
state of every rule, and every surface renders that: the status table, the
dashboard, the gates and the drift report. A surface that parsed the rendered
table would be coupled to a layout; this is the shape they all read instead.

    {
      "schema_version": 4,
      "generated_at": "2026-09-13T12:00:00Z",
      "generated_by": "sync_status",
      "project": "purlin",
      "version": "<the VERSION file>",
      "commit": "<sha>",
      "dirty": false,
      "gate": {"gate": "recorded", "min_strength": 70, ...},
      "states": {"Drafted": 12, "Recorded": 214, ...},
      "features": [
        {"name": "login", "category": "auth", "spec_path": "specs/auth/login.md",
         "is_anchor": false, "requires": [], "source": null, "pinned": null,
         "rollup": {...}, "test_strength": 71,
         "latest_record": {"path": ..., "label": "ci", "timestamp": ..., "os": null},
         "approvals": [...],
         "rules": [
           {"id": "RULE-1", "feature": "login", "label": "own",
            "text": "...", "risk": "low", "origin": "eng", "criterion": null,
            "state": "Recorded", "flags": {...}, "missing_env": [],
            "proofs": [{"id": "PROOF-1", "tier": "unit", "env": null,
                        "text": "...", "findings": [], "tests": [...]}]}
         ]}
      ],
      "review_list": [{"feature": ..., "rule": ..., "risk": ..., "reason": ...}],
      "records": {"login": {"": {...}}},
      "warnings": ["..."]
    }

`write_report_data` writes it to `.purlin/report-data.js` as
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
from purlin import (PURLIN_VERSION, approvals as approvals_module, checks,
                    gate as gate_module, proofs as proofs_module,
                    records as records_module, specs as specs_module, states)

SCHEMA_VERSION = 4
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

    runtime_proofs = proofs_module.load_proofs(project_root)
    all_records = records_module.load_records(project_root)
    all_approvals = approvals_module.load_approvals(project_root, features)
    head = records_module.head_sha(project_root)

    blob_cache = {}
    scope_cache = {}
    feature_entries = []
    review_list = []
    rollups = {}
    # The project rollup counts each rule once, under the feature that owns
    # it. A feature's own rollup counts what that feature must prove, which
    # includes the rules it requires and the global anchors', so summing the
    # feature rollups would count a global anchor's rules once per feature.
    own_results = {}

    for name in sorted(features):
        info = features[name]
        entry, rollup = _feature_entry(
            project_root, name, info, features, runtime_proofs, all_records,
            all_approvals, cfg, head, blob_cache, scope_cache, review_list,
            own_results)
        feature_entries.append(entry)
        rollups[name] = rollup

    project_rollup = states.project_rollup({'': states.feature_rollup(own_results)})
    project_rollup['features'] = len(features)
    state_counts = dict(project_rollup['counts'])

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
        'states': state_counts,
        'project_rollup': project_rollup,
        'features': feature_entries,
        'review_list': review_list,
        'records': {feature: {(os_name or ''): record
                              for os_name, record in by_os.items()}
                    for feature, by_os in all_records.items()},
        'warnings': warnings,
    }
    return payload


def _feature_entry(project_root, name, info, features, runtime_proofs,
                   all_records, all_approvals, cfg, head, blob_cache,
                   scope_cache, review_list, own_results=None):
    counting = {os_name: record
                for os_name, record in (all_records.get(name) or {}).items()
                if records_module.counts_under(cfg.gate, record.get('label'))}
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
            runtime_proofs, counting, all_approvals, cfg, head,
            blob_cache, scope_cache)
        rule_entries.append(result)
        summary = {'state': result['state'], 'flags': result['flags'],
                   'risk': result['risk'],
                   'missing_env': result['missing_env']}
        rule_results[(owner, rule_id)] = summary
        if label == 'own' and own_results is not None:
            own_results[(owner, rule_id)] = summary
        if result['flags'].get('needs_ai_review') or result['state'] == states.STALE:
            review_list.append({
                'feature': name, 'owner': owner, 'rule': rule_id,
                'risk': result['risk'],
                'reason': ('the approval is stale' if result['state'] == states.STALE
                           else 'risk %s needs a look' % result['risk']),
            })

    rollup = states.feature_rollup(
        rule_results,
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
        'approvals': sorted(
            approval['path']
            for key, entries in all_approvals.items() if key[0] == name
            for approval in entries),
        'rules': rule_entries,
    }
    return entry, rollup


def _rule_entry(project_root, feature, owner, owner_info, rule_id, label,
                runtime_proofs, counting, all_approvals, cfg, head,
                blob_cache, scope_cache):
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
                      for f, n in proofs_module.tests_for(entries, proof_id)],
        })
    rule_level = checks.rule_findings(proof_texts)
    for finding in rule_level:
        for proof in proof_dicts:
            proof['findings'] = list(proof['findings']) + [finding]

    rule_hash = specs_module.rule_text_hash(text)
    proof_hash = specs_module.proof_text_hash(
        '\n'.join('%s %s' % (p['id'], p['text']) for p in proof_dicts))
    test_hash = _test_hash(project_root, proof_dicts, blob_cache)
    test_hash_kind = approvals_module.test_hash_kind(proof_dicts)
    design_hash = approvals_module.design_hash(
        owner_info, meta.get('origin', specs_module.DEFAULT_ORIGIN))
    scope_key = owner
    if scope_key not in scope_cache:
        scope_cache[scope_key] = specs_module.scope_tree(
            project_root, owner_info.get('scope', []))

    result = states.rule_state({
        'proofs': proof_dicts,
        'local_status': local_status,
        'records': counting,
        'head': head,
        'scope_tree': scope_cache[scope_key],
        'approvals': all_approvals.get((owner, rule_id), []),
        'rule_hash': rule_hash,
        'proof_hash': proof_hash,
        'test_hash': test_hash,
        'design_hash': design_hash,
        'risk': meta.get('risk', specs_module.DEFAULT_RISK),
        'brief': _read_brief(project_root, owner_info, rule_id,
                             rule_hash, proof_hash, test_hash),
        'test_strength': None,
        'mutation_engine_available': cfg.mutation_engine not in (None, 'none'),
    }, cfg)

    return {
        'id': rule_id,
        'feature': owner,
        'label': label,
        'text': text,
        'risk': meta.get('risk', specs_module.DEFAULT_RISK),
        'origin': meta.get('origin', specs_module.DEFAULT_ORIGIN),
        'criterion': meta.get('criterion'),
        'rule_hash': rule_hash,
        'proof_hash': proof_hash,
        'test_hash': test_hash,
        'test_hash_kind': test_hash_kind,
        'design_hash': design_hash,
        'state': result['state'],
        'flags': result['flags'],
        'missing_env': result['missing_env'],
        'reasons': result['reasons'],
        'proofs': proof_dicts,
    }


def _test_hash(project_root, proof_dicts, blob_cache):
    """The T of the triple: the blob ids of the test files, with their names.

    Reading the file's blob id rather than one function's body is coarse on
    purpose: a test file is the unit version control tracks, and a hash over it
    stales an approval whenever the test that backs a rule changes, which is
    the behaviour the approval is meant to have. `approvals.test_hash_kind`
    names what was read beside the hash, so an approval says so on its face.
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


def _read_brief(project_root, owner_info, rule_id, rule_hash, proof_hash,
                test_hash):
    """The review brief written for a rule's current text, or None.

    A brief sits beside the approval it informs and is named for the triple it
    was built from, so a brief for text that has since changed is simply not
    found: that is what keeps Reviewed honest.
    """
    directory = approvals_module.approvals_dir(project_root, owner_info)
    if not directory:
        return None
    triple = approvals_module.triple_hash(rule_hash, proof_hash, test_hash)
    path = os.path.join(directory, '%s.%s.brief.json' % (rule_id, triple[:8]))
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            brief = json.load(handle)
    except (json.JSONDecodeError, IOError, OSError, UnicodeDecodeError):
        return None
    return brief if isinstance(brief, dict) else None


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
        'os': record.get('os'),
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
