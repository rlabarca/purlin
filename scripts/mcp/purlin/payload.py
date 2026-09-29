"""The structured project payload, schema 10.

One reader assembles specs, evidence and signatures into the cells of every
rule, and every surface renders that: the
status table, the dashboard, the evidence package and the drift report. A surface
that parsed the rendered table would be coupled to a layout; this is the shape
they all read instead.

    {
      "schema_version": 10,
      "generated_at": "2026-09-13T12:00:00Z",
      "generated_by": "sync_status",
      "project": "purlin",
      "version": "<the VERSION file>",
      "commit": "<sha>",
      "dirty": false,
      "gate": {"gate": "strong", "min_strength": 70, ...},
      "summary": {"rules": 8, "features": 4, "failing": 0,
                  "partial": 1, "untested": 2, "passed": 4, "strong": 1,
                  "signed": 1, "manual": 0, "not_audited": 0,
                  "incomplete": 0,
                  "steps": {"passed": 4, "strong": 2, "signed": 1},
                  "sentence": "8 rules. 4 pass their tests. 2 are strong. 1 is signed."},
      "features": [
        {"name": "login", "category": "auth", "spec_path": "specs/auth/login.md",
         "is_anchor": false, "requires": [], "source": null, "pinned": null,
         "scope": ["src/auth/"], "incomplete": false,
         "incomplete_reason": null,
         "rollup": {..., "proofs": 6, "proofs_without_test": 1,
                    "proofs_without_test_ids": ["PROOF-4"],
                    "incomplete": false},
         "test_strength": 86,
         "current": true,
         "evidence": {"local": {"path": ".purlin/evidence/local/login.json",
                                "committed": true,
                                "platforms": {"macos": {"commit": ..., "at": ...,
                                                        "current": true}}},
                      "ci": null},
         "signatures": [...],
         "rules": [
           {"id": "RULE-1", "feature": "login", "applies_to": "login",
            "label": "own",
            "text": "...",
            "audit_hash": "<sha256>", "code_hash": "<sha256>",
            "machines": {"macos": "jane-laptop"},
            "left": "to_sign", "hand_checked": false,
            "audit": {"verdict": "strong", "findings": [], "notes": [],
                      "strength": 86,
                      "model": "<model>", "at": "...", "commit": "<sha>",
                      "path": ".purlin/evidence/local/login.json"},
            "bucket": "signed", "flags": {...},
            "cells": {"passed": {...}, "strong": {...}, "signed": {...}},
            "proofs": [{"id": "PROOF-1", "manual": false, "env": null,
                        "text": "...", "result": "passed",
                        "tests": [{"file": "tests/test_login.py",
                                   "name": "test_sign_in",
                                   "result": "pass"}]}],
            "tests": []}
         ]}
      ],
      "left": [{"kind": "to_audit", "count": 2,
                "text": "2 rules to audit", "command": "purlin:audit"},
               {"kind": "to_sign", "count": 1,
                "text": "1 rule to sign", "command": "purlin:sign"}],
      "finished": false,
      "last_line": null,
      "os_words": {"windows": {"word": "Windows", "short": "Win"},
                   "macos": {"word": "macOS", "short": "Mac"},
                   "linux": {"word": "Linux/Unix", "short": "Lin"}},
      "evidence": {"login": {"local": {"macos": {"commit": ..., "at": ...,
                                                 "result": "pass",
                                                 "current": true,
                                                 "path": ...}}}},
      "tag": {"name": "signed/1.4.0", "commit": "<sha>"},
      "remote_url": "https://github.com/acme/ledger.git",
      "warnings": ["..."]
    }

`rules[].tests` lists the tests marked with the rule's own id, which is how
a rule with no proof names its tests: `[{"file": "tests/test_login.py",
"name": "test_locks", "result": "pass"}]`, where `result` is `pass`, `fail`,
`missing` or `not run`. A rule whose tests carry its proofs' ids lists them
under each proof and an empty `tests`.

Each proof carries its own `result`, `passed`, `failed`, `not run`, `no test`
or `hand check`, as `states.proof_result` reads it, and each of its tests the
`result` a current run gave it, `pass` or `fail`, or `not run` where no
current run lists it.

A feature's `rules` holds its own rules, `label` `own`, then every rule it
must prove from an anchor it requires, `required`, or from a global anchor,
`global`. Each carries `feature`, the name of the spec that owns it, so a
rule is always addressed by its owner and its id: two features' `RULE-1` are
two rules.

Every rule carries every cell up to the gate: `passed` always, `strong` at the
gate `strong` and above, `signed` at `signed`. A cell above the gate is
absent, not empty, so a `passed` project carries one cell per rule.

A feature spec that names no files, with no `> Scope:` line or a scope that
reaches no tracked file, carries `incomplete: true` and `incomplete_reason`
(`no > Scope: line` or `> Scope: names nothing that exists`), its rollup
carries `incomplete: true`, and `summary.incomplete` counts such specs. An
anchor is never incomplete. Every cell reads as usual, except that at the
gate `signed` such a spec's rules read `unsigned` in the signed cell, and at
`strong` and `signed`, with mutation testing on and no strength measured,
`weak` in the strong cell.

`summary.steps` counts the rules that reached each step up to the gate, each
step containing the next, and `summary.sentence` says it in one line.
`left` is the work left, one entry per kind in the order it is done, each
with its count, its text and the command that clears it, `to_correct`
counting the comments above tests that name something no spec has or a rule
that has proofs; `finished` is true
when `left` is empty, and `last_line` is then the line said in its place.
Each rule carries its own `left`, the one kind it is counted under, or null.
`scripts/mcp/purlin/summary.py` is the one place those words are written.

A rule carries `applies_to`, the feature it is listed under, `code_hash`,
`fingerprint.code_hash` over that feature's `> Scope:`, `machines`, `{os:
machine}` over the current sections that speak for it, and `hand_checked`,
true when it has a `@manual` proof and a signature that counts still binds
it, with or without a note. Those are what a signature is made over. An
anchor's rule listed under the anchor itself is signed when every feature it
applies to has signed it.

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
                    markers as markers_module,
                    signatures as signatures_module,
                    specs as specs_module, states,
                    summary as summary_module)

SCHEMA_VERSION = 10
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
            lines = ('1 line' if len(unnumbered) == 1
                     else '%d lines' % len(unnumbered))
            verb = 'is' if len(unnumbered) == 1 else 'are'
            warnings.append(
                'WARNING: %s under ## Rules in %s %s not numbered; a rule is '
                '`- RULE-N: <text>`. Run purlin:spec %s.'
                % (lines, features[name]['spec_path'], verb, name))
    for line in specs_module.spec_mistakes(project_root, features):
        warnings.append(line)

    # Every feature's evidence, checked against a fingerprint taken now. A
    # section decides a cell only while it is current, so this is read once
    # here rather than once per rule.
    evidence = _read_evidence(project_root, features, warnings)
    # Why each feature spec names no files, where it names none. Its rules'
    # cells are read as usual but for the signed cell at `signed`, and the
    # strong cell where mutation testing is on and measured nothing.
    incomplete = {name: fingerprint_module.incomplete_reason(
        project_root, name, features) for name in sorted(features)}
    could_not_run = evidence_module.could_not_run(project_root)
    all_signatures = signatures_module.load_signatures(project_root, features)
    head = head_sha(project_root)
    here_os = evidence_module.host_os()
    # Only a project at `signed` is ever tagged, so below it the payload
    # names no tag, even one left from when the gate was higher.
    tag = (signed_tag(project_root, head)
           if cfg.gate == gate_module.GATES[-1] else None)

    blob_cache = {}
    counted_cache = {}
    # The code each feature's signatures are made over, and, for each
    # anchor's rule, the features it applies to.
    code_hashes = {name: fingerprint_module.code_hash(
        project_root, features[name].get('scope') or [])
        for name in sorted(features)}
    consumers = _consumers(features)
    feature_entries = []
    rollups = {}
    # The project summary counts each rule once, under the feature that owns
    # it. A feature's own rollup counts what that feature must prove, which
    # includes the rules it requires and the global anchors', so summing the
    # feature rollups would count a global anchor's rules once per feature.
    own_results = {}
    # Which proofs have a test is read from the markers in the test files,
    # not from the evidence: a marked test that has not run yet is a test.
    suites = markers_module.read_suites(project_root, config)[0]
    scanned = markers_module.scan(project_root, suites)
    tied = markers_module.tied_ids(project_root, scanned)
    # Every comment above a test that names nothing a spec has, or names a
    # rule that has proofs, fails the run, so `Left to do` counts it too.
    corrections = len(markers_module.marker_problems(scanned, features))

    for name in sorted(features):
        info = features[name]
        entry, rollup = _feature_entry(
            project_root, name, info, features, evidence, all_signatures,
            cfg, blob_cache, own_results, counted_cache, could_not_run,
            incomplete, tied, here_os, code_hashes, consumers)
        feature_entries.append(entry)
        rollups[name] = rollup

    summary = states.project_rollup(
        {'': states.feature_rollup(own_results, cfg.gate)}, cfg.gate)
    summary['features'] = len(features)
    summary['incomplete'] = sum(1 for reason in incomplete.values() if reason)
    # The project's proofs are each feature's own, counted once: a rule an
    # anchor declares is proved by every feature that requires it, and its
    # proofs belong to the anchor.
    own_rules = [rule for entry in feature_entries for rule in entry['rules']
                 if rule.get('label') == 'own']
    summary.update(proof_counts(own_rules, tied))
    summary['steps'] = summary_module.steps(own_rules, cfg.gate)
    summary['sentence'] = summary_module.sentence(summary, cfg.gate)
    left = summary_module.left(feature_entries, cfg.gate, here_os, tag,
                               corrections)

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
        'left': left,
        'finished': not left,
        'last_line': summary_module.last_line(left, cfg.gate, tag),
        'os_words': {name: {'word': evidence_module.os_word(name),
                            'short': evidence_module.os_short(name)}
                     for name in evidence_module.PLATFORMS},
        'evidence': _evidence_map(evidence),
        'tag': tag,
        'remote_url': _remote_url(project_root),
        'warnings': warnings,
    }
    return payload


def proof_counts(rule_entries, tied=None):
    """`{proofs, proofs_without_test, proofs_without_test_ids}` over some rules.

    A proof with no marked test is the gap between what a spec claims to
    observe and what anything actually runs, so the count is carried beside
    the proof total rather than worked out again by each surface. Each proof
    is counted once under the rule that writes it, so a rule an anchor
    declares is not counted twice in the one row that proves it.

    A `@manual` proof is left out of the count: it declares that no test is
    written for it, so naming it as a gap would report the spec's own answer
    as a fault. A proof has a test when a marker naming it is tied to a test
    declaration, `tied` being `markers.tied_ids`' answer, so a marked test
    that has not run yet is a test and its rule reads `not run`.
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
            if proof.get('manual'):
                continue
            if (rule.get('feature'), proof.get('id')) not in (tied or ()):
                without.append(proof.get('id'))
    return {'proofs': total, 'proofs_without_test': len(without),
            'proofs_without_test_ids': without}


def _consumers(features):
    """`{(anchor, rule_id): [feature, ...]}`: the features each anchor rule applies to.

    A global anchor's rules apply to every feature, and any other anchor's
    to each feature that requires it.
    """
    found = {}
    for name in sorted(features):
        for owner, rule_id, label in specs_module.rule_refs(name, features):
            if label == 'own' or not features.get(owner, {}).get('is_anchor'):
                continue
            found.setdefault((owner, rule_id), []).append(name)
    return found


def _feature_entry(project_root, name, info, features, evidence,
                   all_signatures, cfg, blob_cache, own_results=None, counted_cache=None, could_not_run=None,
                   incomplete=None, tied=None, here_os=None, code_hashes=None,
                   consumers=None):
    incomplete = incomplete or {}
    code_hashes = code_hashes or {}
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
            owner_mutation,
            counted_cache, could_not_run, incomplete.get(owner),
            {marked for feature, marked in (tied or ()) if feature == owner},
            name, code_hashes, here_os,
            (consumers or {}).get((owner, rule_id)) if owner == name else None)
        rule_entries.append(result)
        summary = {'bucket': result['bucket'], 'flags': result['flags']}
        rule_results[(owner, rule_id)] = summary
        if label == 'own' and own_results is not None:
            own_results[(owner, rule_id)] = summary

    rollup = states.feature_rollup(rule_results, cfg.gate,
                                   test_strength=test_strength)
    rollup.update(proof_counts(rule_entries, tied))
    rollup['incomplete'] = bool(incomplete.get(name))

    entry = {
        'name': name,
        'category': info.get('category', ''),
        'spec_path': info.get('spec_path', ''),
        'is_anchor': bool(info.get('is_anchor')),
        'is_global': bool(info.get('is_global')),
        'description': info.get('description'),
        'requires': info.get('requires', []),
        'scope': info.get('scope', []),
        'incomplete': bool(incomplete.get(name)),
        'incomplete_reason': incomplete.get(name),
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


def _rule_entry(project_root, owner, owner_info, rule_id, label,
                owner_evidence, all_signatures, cfg, blob_cache,
                mutation=None, counted_cache=None, could_not_run=None,
                incomplete=None, marked=None, applies_to=None,
                code_hashes=None, here_os=None, consumers=None):
    text = owner_info['rules'].get(rule_id, '')
    test_strength = (mutation or {}).get('score')
    applies_to = applies_to or owner
    code_hashes = code_hashes or {}
    proof_ids = owner_info.get('proofs_by_rule', {}).get(rule_id, [])
    sections = owner_evidence['sections']

    proof_dicts = []
    for proof_id in proof_ids:
        proof = owner_info['proofs'][proof_id]
        ran = _current_results(sections, proof_id, proof['env'])
        entry = {
            'id': proof_id,
            'manual': proof['manual'],
            'env': proof['env'],
            'text': proof['text'],
            'tests': [{'file': f, 'name': n,
                       'result': ran.get((f, n), 'not run')}
                      for f, n in _backing_tests(sections, proof_id)],
        }
        entry['result'] = states.proof_result(entry, sections, marked)
        proof_dicts.append(entry)

    rule_hash = specs_module.rule_text_hash(text)
    proof_hash = specs_module.proof_text_hash(
        '\n'.join('%s %s' % (p['id'], p['text']) for p in proof_dicts))
    test_hash = _test_hash(project_root, proof_dicts, blob_cache)
    test_hash_kind = signatures_module.test_hash_kind(proof_dicts)
    # What a signature is made over besides the rule, its proof and its
    # test: the code the feature it is listed under names, and the machine
    # each system's results came from.
    code_hash = code_hashes.get(applies_to)
    machines = _machines(sections, proof_dicts, rule_id)

    signatures = [_counted(project_root, signature, cfg, counted_cache)
                  for signature in all_signatures.get((owner, rule_id), [])]

    # The audit entry for this rule's current hashes, in either source. An
    # entry taken over other text, another proof or another test does not
    # answer, which is what keeps the strong cell honest.
    audit = evidence_module.audit_entry(owner_evidence['loaded'], rule_id,
                                        rule_hash, proof_hash, test_hash)
    audit_hash = signatures_module.audit_hash(audit, test_strength)
    result = states.rule_cells({
        # What a signature is made over, what the audit found among it.
        'applies_to': applies_to,
        'code_hash': code_hash,
        'machines': machines,
        'audit_hash': audit_hash,
        # The features an anchor's own rule applies to, each of which signs
        # it, with the code each is signed over.
        'consumers': [{'applies_to': feature,
                       'code_hash': code_hashes.get(feature)}
                      for feature in consumers or ()],
        'proofs': proof_dicts,
        'rule_id': rule_id,
        'sections': sections,
        'signatures': signatures,
        'rule_hash': rule_hash,
        'proof_hash': proof_hash,
        'test_hash': test_hash,
        'audit': audit,
        # Why the last audit could not reach the model for these hashes,
        # which is what the strong cell says while it reads `not audited`.
        'could_not_run': evidence_module.why_not_audited(
            could_not_run, owner, rule_id, rule_hash, proof_hash, test_hash),
        # The feature's strength stands for every rule in it: a break engine
        # measures a scope, not one rule, and the strong cell compares what
        # was measured rather than assuming nothing was.
        'test_strength': test_strength,
        # Why the engine the settings chose measured nothing for the
        # feature, where it said.
        'strength_missing': (mutation or {}).get('missing') or '',
        'feature': owner,
        # Why the rule's own spec names no files, or None.
        'incomplete': incomplete,
        # The owner's proof and rule ids a marker ties to a test declaration,
        # so a marked test that has not run reads `not run`, not `no test`.
        'marked': marked or set(),
    }, cfg)

    entry = {
        'id': rule_id,
        'feature': owner,
        'applies_to': applies_to,
        'label': label,
        'text': text,
        'rule_hash': rule_hash,
        'proof_hash': proof_hash,
        'test_hash': test_hash,
        'test_hash_kind': test_hash_kind,
        'code_hash': code_hash,
        'audit_hash': audit_hash,
        'machines': machines,
        'audit': audit_summary(audit, test_strength),
        'cells': result['cells'],
        'bucket': result['bucket'],
        'flags': result['flags'],
        # A person checked a `@manual` proof by hand: a signature that
        # counts still binds the rule.
        'hand_checked': result['hand_checked'],
        'proofs': proof_dicts,
        'tests': _rule_tests(sections, rule_id),
    }
    entry['left'] = summary_module.rule_kind(entry, cfg.gate, here_os,
                                             incomplete)
    return entry


def _machines(sections, proofs, rule_id):
    """`{os: machine}` over the current sections that speak for the rule.

    A section speaks for the rule when one of the rule's proofs ran there,
    passing or failing, read from its own system only where the proof names
    one, or for the rule's own id where it has no proof. Each section's `machine`
    names where it ran; a section that names none is left out, and where
    both sources hold one for a system the newer answers.
    """
    wanted = [(proof['id'], proof.get('env')) for proof in proofs
              if not proof.get('manual')] or [(rule_id, None)]
    found = {}
    for entry in sections or ():
        if not entry.get('current'):
            continue
        section = entry['section']
        machine = section.get('machine')
        if not machine:
            continue
        results = evidence_module.proof_results(section)
        if not any(results.get(proof_id) in ('pass', 'fail')
                   and (not env or env == entry['os'])
                   for proof_id, env in wanted):
            continue
        at = str(section.get('at') or '')
        known = found.get(entry['os'])
        if known is None or at > known[0]:
            found[entry['os']] = (at, machine)
    return {name: found[name][1] for name in sorted(found)}


def audit_summary(audit, strength):
    """`rules[].audit`: what the audit found for the current hashes, or None.

    The `verdict` and the findings, the feature's test strength, the model
    that read the rule, when and at which commit, and the evidence file the
    entry sits in. Present at every gate, so a surface reads when the audit
    ran without working it out.
    """
    if not audit:
        return None
    return {'verdict': audit.get('verdict'),
            'findings': [str(line) for line in audit.get('findings') or ()],
            'notes': [str(line) for line in audit.get('notes') or ()],
            'strength': strength,
            'model': audit.get('model') or 'unknown',
            'at': audit.get('at'),
            'commit': audit.get('commit'),
            'path': audit.get('path')}


def _counted(project_root, signature, cfg, cache):
    """One signature plus whether it counts under the gate, and why not.

    Reading git for each signature is the expensive part, and the answer is a
    property of the committed file rather than of the rule asking, so it is
    cached on the path.
    """
    cache = cache if cache is not None else {}
    key = signature.get('path')
    if key not in cache:
        ok, reason = signatures_module.counts(project_root, signature)
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
    change which tests back the proof, and the test hash moves only when a
    test does.
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


def _current_results(sections, proof_id, env=None):
    """`{(file, name): result}` for one proof's tests, over current sections.

    A proof's test reads what a current run found, `fail` where either source
    failed it and `pass` where one passed it, so a test and the proof above it
    never disagree. A test no current section lists is not in the map, and
    reads `not run`. A proof that names an operating system is read from that
    system's sections alone, as its own result is.
    """
    results = {}
    for entry in sections or ():
        if not entry.get('current') or (env and entry.get('os') != env):
            continue
        for item in (entry['section'].get('proofs') or ()):
            if not isinstance(item, dict) or item.get('id') != proof_id:
                continue
            path, _, name = (item.get('test') or '').partition('::')
            result = item.get('result')
            if not path or result not in ('pass', 'fail'):
                continue
            if results.get((path, name)) != 'fail':
                results[(path, name)] = result
    return results


def _rule_tests(sections, rule_id):
    """`[{file, name, result}]` for the tests marked with the rule's own id.

    Read from the same sections as `_backing_tests`, current ones first. A
    test two sections list reads `fail` where either failed, then `pass`
    where either passed, and otherwise the first word a section wrote.
    """
    for wanted in (True, False):
        order = []
        results = {}
        for entry in sections or ():
            if wanted and not entry.get('current'):
                continue
            for item in (entry['section'].get('proofs') or ()):
                if not isinstance(item, dict) or item.get('id') != rule_id:
                    continue
                path, _, name = (item.get('test') or '').partition('::')
                if not path:
                    continue
                key = (path, name)
                result = item.get('result')
                if key not in results:
                    order.append(key)
                    results[key] = result
                elif result == 'fail' or (result == 'pass'
                                          and results[key] != 'fail'):
                    results[key] = result
        if order:
            return [{'file': path, 'name': name, 'result': results[(path, name)]}
                    for path, name in order]
    return []


def _test_hash(project_root, proof_dicts, blob_cache):
    """The test hash: the blob ids of the test files, with their names.

    Reading the file's blob id rather than one function's body is coarse on
    purpose: a test file is the unit version control tracks, and a hash over it
    ends a signature whenever the test that backs a rule changes, which is
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

    The payload asks only at the gate `signed`; below it its `tag` is null.

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


def write_report_data(project_root, payload):
    """Write the payload as `const PURLIN_DATA = {...};`. Returns the path."""
    path = report_data_path(project_root)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = json.dumps(payload, indent=2, sort_keys=True, default=str)
    text = _PREFIX + body + ';\n'

    tmp_path = path + '.tmp'
    # `newline='\n'` keeps every line ending a line feed on Windows too.
    with open(tmp_path, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(text)
    os.replace(tmp_path, path)
    return path
